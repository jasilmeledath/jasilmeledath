"""Regression tests for scope, denominators, date boundaries, and safe updates."""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_metrics.py"
SPEC = importlib.util.spec_from_file_location("update_metrics", MODULE_PATH)
metrics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metrics)
NOW = datetime(2026, 10, 8, 12, 34, 56, tzinfo=timezone.utc)


def repository(name, *, private=False, fork=False, owner="jasilmeledath", stars=2):
    return {"full_name": f"{owner}/{name}", "private": private, "fork": fork, "owner": {"login": owner}, "stargazers_count": stars}


class FakeAPI:
    def __init__(self, pages, languages=None, fail_on=None):
        self.pages = pages
        self.languages = languages or {}
        self.fail_on = fail_on
        self.calls = []

    def rest(self, endpoint):
        self.calls.append(endpoint)
        if self.fail_on and self.fail_on in endpoint:
            raise metrics.MetricsError("Simulated API failure")
        if endpoint.startswith("/users/"):
            page = int(endpoint.rsplit("page=", 1)[-1])
            return self.pages[page - 1]
        return self.languages.get(endpoint, {"TypeScript": 100})

    def contributions(self, username, start, end):
        if self.fail_on == "contributions":
            raise metrics.MetricsError("Simulated contribution API failure")
        return {"total": 123, "commits": 100, "pull_requests": 5}


class CollectionTests(unittest.TestCase):
    def test_paginates_and_excludes_private_forks_and_other_owners(self):
        page_one = [repository(f"project-{i}") for i in range(100)]
        page_two = [repository("last-project", stars=7), repository("secret", private=True), repository("fork", fork=True), repository("someone-elses", owner="another-user")]
        api = FakeAPI([page_one, page_two])
        result = metrics.collect_metrics(api, "jasilmeledath", NOW)
        self.assertEqual(result["repositories"]["count"], 101)
        self.assertEqual(result["repositories"]["stars"], 207)
        self.assertEqual(result["languages"]["total_bytes"], 10100)
        self.assertEqual(len([call for call in api.calls if call.startswith("/repos/")]), 101)
        self.assertTrue(any("page=2" in call for call in api.calls))
        self.assertFalse(any("secret" in call or "someone-elses" in call or "/fork/" in call for call in api.calls))
        serialized = json.dumps(result)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("project-", serialized)

    def test_full_page_followed_by_empty_page(self):
        api = FakeAPI([[repository(f"repo-{i}") for i in range(100)], []])
        self.assertEqual(len(metrics.public_owned_repositories(api, "jasilmeledath")), 100)
        self.assertEqual(len(api.calls), 2)

    def test_duplicates_abort_instead_of_publishing_incomplete_pagination(self):
        api = FakeAPI([[repository(f"repo-{i}") for i in range(100)], [repository("repo-0")]])
        with self.assertRaises(metrics.MetricsError):
            metrics.public_owned_repositories(api, "jasilmeledath")

    def test_language_denominator_includes_all_languages_and_repositories(self):
        api = FakeAPI([[repository("a"), repository("b")]], {
            "/repos/jasilmeledath/a/languages": {"A": 400, "B": 200, "C": 100, "D": 100, "E": 100, "F": 50, "G": 50},
            "/repos/jasilmeledath/b/languages": {"A": 1000},
        })
        result = metrics.collect_metrics(api, "jasilmeledath", NOW)
        shares = metrics.language_shares(result)
        self.assertEqual(result["languages"]["total_bytes"], 2000)
        self.assertEqual(shares[0], ("A", 1400, 70.0))
        self.assertEqual(shares[-1], ("Other", 100, 5.0))
        self.assertAlmostEqual(sum(share for _, _, share in shares), 100.0)

    def test_empty_languages_are_a_real_empty_state(self):
        result = metrics.collect_metrics(FakeAPI([[]]), "jasilmeledath", NOW)
        self.assertEqual(metrics.language_shares(result), [])
        self.assertIn("no source-language bytes", metrics.languages_svg(result, "light"))

    def test_malformed_visibility_and_counts_fail_closed(self):
        bad_visibility = repository("incomplete")
        del bad_visibility["private"]
        for repo in [bad_visibility, repository("bad-stars", stars="2")]:
            with self.subTest(repo=repo), self.assertRaises(metrics.MetricsError):
                metrics.collect_metrics(FakeAPI([[repo]]), "jasilmeledath", NOW)

    def test_language_response_error_is_not_mistaken_for_zero(self):
        api = FakeAPI([[repository("a")]], {"/repos/jasilmeledath/a/languages": {"message": "Not Found"}})
        with self.assertRaises(metrics.MetricsError):
            metrics.collect_metrics(api, "jasilmeledath", NOW)

    def test_username_cannot_inject_api_options_or_paths(self):
        for username in ["--help", "someone/repos", "$(secret)", "", "a" * 40]:
            with self.subTest(username=username), self.assertRaises(metrics.MetricsError):
                metrics.validate_username(username)


class WindowTests(unittest.TestCase):
    def test_365_utc_dates_across_leap_day(self):
        end = datetime(2024, 3, 1, 16, 10, 2, tzinfo=timezone.utc)
        start, actual_end = metrics.contribution_window(end)
        self.assertEqual(start, datetime(2023, 3, 3, tzinfo=timezone.utc))
        self.assertEqual((actual_end.date() - start.date()).days + 1, 365)
        self.assertEqual(actual_end, end)

    def test_non_utc_input_uses_utc_date(self):
        local = datetime(2026, 1, 1, 1, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        start, end = metrics.contribution_window(local)
        self.assertEqual(end, datetime(2025, 12, 31, 19, 30, tzinfo=timezone.utc))
        self.assertEqual(start, datetime(2025, 1, 1, tzinfo=timezone.utc))

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(metrics.MetricsError):
            metrics.contribution_window(datetime(2026, 1, 1))


class OutputTests(unittest.TestCase):
    def test_all_api_failures_preserve_all_old_assets(self):
        for fail_on in ["/users/", "/languages", "contributions"]:
            with self.subTest(fail_on=fail_on), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                names = ["metrics.json", "activity-light.svg", "activity-dark.svg", "languages-light.svg", "languages-dark.svg", "activity-mobile-light.svg", "activity-mobile-dark.svg", "languages-mobile-light.svg", "languages-mobile-dark.svg"]
                for name in names:
                    (output / name).write_text("previous valid asset", encoding="utf-8")
                api = FakeAPI([[repository("a")]], fail_on=fail_on)
                with self.assertRaises(metrics.MetricsError):
                    metrics.generate(output, "jasilmeledath", api, NOW)
                self.assertEqual(sorted(path.name for path in output.iterdir()), sorted(names))
                self.assertTrue(all((output / name).read_text() == "previous valid asset" for name in names))

    def test_generated_svgs_are_valid_xml_and_assets_contain_no_repo_names(self):
        api = FakeAPI([[repository("public-project"), repository("super-secret-project", private=True)]], {
            "/repos/jasilmeledath/public-project/languages": {"A&B <language>": 100, "TypeScript": 900},
        })
        with tempfile.TemporaryDirectory() as directory:
            result = metrics.generate(Path(directory), "jasilmeledath", api, NOW)
            self.assertEqual(len(list(Path(directory).iterdir())), 9)
            for path in Path(directory).iterdir():
                content = path.read_text()
                self.assertNotIn("public-project", content)
                self.assertNotIn("super-secret-project", content)
                if path.suffix == ".svg":
                    root = ET.fromstring(content)
                    expected_box = "0 0 600 420" if "activity-mobile" in path.name else "0 0 600 320" if "languages-mobile" in path.name else "0 0 920 235"
                    self.assertEqual(root.attrib["viewBox"], expected_box)
                    self.assertIn("12:34 UTC", content)
            self.assertEqual(result["updated_at"], "2026-10-08T12:34:56Z")


class APIBoundaryTests(unittest.TestCase):
    @patch.object(metrics.subprocess, "run")
    def test_graphql_errors_abort_without_exposing_response(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"errors": [{"message": "private-sensitive-context"}]}), "")
        start, end = metrics.contribution_window(NOW)
        with self.assertRaises(metrics.MetricsError) as failure:
            metrics.GitHubAPI().contributions("jasilmeledath", start, end)
        self.assertNotIn("private-sensitive-context", str(failure.exception))

    @patch.object(metrics.subprocess, "run")
    def test_failed_cli_does_not_expose_stderr(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, "", "token: do-not-print-me")
        with self.assertRaises(metrics.MetricsError) as failure:
            metrics.GitHubAPI().rest("/users/jasilmeledath/repos")
        self.assertNotIn("do-not-print-me", str(failure.exception))

    @patch.object(metrics.subprocess, "run")
    def test_graphql_uses_explicit_start_and_end(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"data": {"user": {"contributionsCollection": {"contributionCalendar": {"totalContributions": 15, "weeks": [{"contributionDays": [{"date": "2026-10-08", "contributionCount": 15}]}]}, "totalCommitContributions": 12, "totalPullRequestContributions": 1}}}}), "")
        start, end = metrics.contribution_window(NOW)
        self.assertEqual(metrics.GitHubAPI().contributions("jasilmeledath", start, end), {"total": 15, "commits": 12, "pull_requests": 1})
        args = run.call_args.args[0]
        self.assertIn("from=2025-10-09T00:00:00Z", args)
        self.assertIn("to=2026-10-08T12:34:56Z", args)

    @patch.object(metrics.subprocess, "run")
    def test_calendar_sum_must_match_total(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"data": {"user": {"contributionsCollection": {"contributionCalendar": {"totalContributions": 15, "weeks": [{"contributionDays": [{"date": "2026-10-08", "contributionCount": 12}]}]}, "totalCommitContributions": 12, "totalPullRequestContributions": 1}}}}), "")
        start, end = metrics.contribution_window(NOW)
        with self.assertRaises(metrics.MetricsError):
            metrics.GitHubAPI().contributions("jasilmeledath", start, end)


if __name__ == "__main__":
    unittest.main()
