#!/usr/bin/env python3
"""Build GitHub profile cards from GitHub's API, using the authenticated gh CLI.

Run from any directory: python3 scripts/update_metrics.py
GITHUB_USERNAME defaults to jasilmeledath. GH_TOKEN is consumed by gh, never read
or printed by this script. No third-party Python packages are required.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, time, timedelta, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any


UTC = timezone.utc
PAGE_SIZE = 100
PALETTES = {
    "light": {"bg": "#f7f5f0", "border": "#ddd9d0", "text": "#17201f", "muted": "#57645f", "accent": "#137b66"},
    "dark": {"bg": "#101917", "border": "#2b3c35", "text": "#eff5ef", "muted": "#9caea4", "accent": "#68dab0"},
}
LANGUAGE_COLORS = {
    "JavaScript": "#cbb747", "TypeScript": "#3178c6", "Python": "#5689ba",
    "HTML": "#e36a46", "CSS": "#9a72d1", "SCSS": "#cc6699", "Java": "#bb8447",
    "C++": "#db7096", "C": "#718096", "Go": "#38a9bd", "Rust": "#b98b71",
    "Shell": "#7cac56", "Ruby": "#bf5151", "PHP": "#888bc1", "Dart": "#35a7bd",
    "Vue": "#42b883", "Svelte": "#eb7049", "Kotlin": "#a77aff", "Swift": "#e67d53",
    "Jupyter Notebook": "#d99b46", "MDX": "#c6a541", "Other": "#82968a",
}

CONTRIBUTIONS_QUERY = """
query ProfileMetrics($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
      totalCommitContributions
      totalPullRequestContributions
    }
  }
}
"""


class MetricsError(RuntimeError):
    """A failed or incomplete API response; previously generated cards remain."""


def validate_username(username: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", username):
        raise MetricsError("GITHUB_USERNAME must be a valid GitHub username.")
    return username


def utc_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def contribution_window(now: datetime) -> tuple[datetime, datetime]:
    """Today and the previous 364 UTC dates; the current date is partial."""
    if now.tzinfo is None:
        raise MetricsError("A timezone-aware timestamp is required.")
    end = now.astimezone(UTC).replace(microsecond=0)
    start = datetime.combine(end.date() - timedelta(days=364), time.min, tzinfo=UTC)
    return start, end


def nonnegative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise MetricsError(f"GitHub returned an invalid {field} count.")
    return value


class GitHubAPI:
    def _request(self, arguments: list[str], label: str) -> Any:
        try:
            completed = subprocess.run(
                ["gh", "api", *arguments], check=False, capture_output=True,
                text=True, timeout=90,
            )
        except FileNotFoundError as exc:
            raise MetricsError("GitHub CLI (gh) is required. Install it and authenticate before running.") from exc
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MetricsError(f"GitHub request failed or timed out ({label}).") from exc
        if completed.returncode != 0:
            # Do not forward stderr: it can include auth details or private context.
            raise MetricsError(f"GitHub request failed ({label}); check authentication and API rate limits.")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise MetricsError(f"GitHub returned invalid JSON ({label}).") from exc

    def rest(self, endpoint: str) -> Any:
        return self._request([
            "--hostname", "github.com", endpoint,
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: 2022-11-28",
        ], "REST API")

    def contributions(self, username: str, start: datetime, end: datetime) -> dict[str, int]:
        result = self._request([
            "--hostname", "github.com", "graphql", "-f", f"query={CONTRIBUTIONS_QUERY}",
            "-f", f"login={username}", "-f", f"from={utc_timestamp(start)}",
            "-f", f"to={utc_timestamp(end)}",
        ], "contribution collection")
        if not isinstance(result, dict) or result.get("errors"):
            raise MetricsError("GitHub could not return the complete contribution collection.")
        try:
            collection = result["data"]["user"]["contributionsCollection"]
            calendar = collection["contributionCalendar"]
            total = nonnegative_int(calendar["totalContributions"], "contribution")
            day_sum = 0
            seen_dates: set[str] = set()
            for week in calendar["weeks"]:
                for day in week["contributionDays"]:
                    date = day["date"]
                    parsed = datetime.strptime(date, "%Y-%m-%d").date()
                    count = nonnegative_int(day["contributionCount"], "daily contribution")
                    if date in seen_dates:
                        raise MetricsError("GitHub returned duplicate contribution dates.")
                    seen_dates.add(date)
                    if not start.date() <= parsed <= end.date() and count:
                        raise MetricsError("GitHub returned contributions outside the requested UTC window.")
                    day_sum += count
            if day_sum != total:
                raise MetricsError("GitHub's daily contribution counts do not match its reported total; retry later.")
            return {
                "total": total,
                "commits": nonnegative_int(collection["totalCommitContributions"], "commit contribution"),
                "pull_requests": nonnegative_int(collection["totalPullRequestContributions"], "pull request contribution"),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise MetricsError("GitHub returned an incomplete contribution collection.") from exc


def public_owned_repositories(api: GitHubAPI, username: str) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    page = 1
    while True:
        items = api.rest(f"/users/{username}/repos?type=owner&per_page={PAGE_SIZE}&page={page}")
        if not isinstance(items, list):
            raise MetricsError("GitHub returned an invalid repository page.")
        for repo in items:
            if not isinstance(repo, dict) or not isinstance(repo.get("private"), bool) or not isinstance(repo.get("fork"), bool):
                raise MetricsError("GitHub returned incomplete repository visibility information.")
            if repo["private"] or repo["fork"]:
                continue
            owner_data = repo.get("owner")
            owner = owner_data.get("login") if isinstance(owner_data, dict) else None
            if not isinstance(owner, str):
                raise MetricsError("GitHub returned incomplete repository ownership information.")
            if owner.casefold() != username.casefold():
                continue
            full_name = repo.get("full_name")
            if not isinstance(full_name, str) or not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", full_name):
                raise MetricsError("GitHub returned an invalid repository identifier.")
            if full_name.split("/", 1)[0].casefold() != username.casefold():
                raise MetricsError("GitHub returned inconsistent repository ownership information.")
            identity = full_name.casefold()
            if identity in seen:
                # Repository names can move between pages during an update. Abort
                # rather than publishing a possibly incomplete snapshot.
                raise MetricsError("Repository pages changed during collection; retry the update.")
            seen.add(identity)
            selected.append({"full_name": full_name, "stars": nonnegative_int(repo.get("stargazers_count"), "star")})
        if len(items) < PAGE_SIZE:
            return selected
        page += 1


def collect_metrics(api: GitHubAPI, username: str, now: datetime) -> dict[str, Any]:
    username = validate_username(username)
    start, end = contribution_window(now)
    repositories = public_owned_repositories(api, username)
    language_bytes: Counter[str] = Counter()
    for repo in repositories:
        languages = api.rest(f"/repos/{repo['full_name']}/languages")
        if not isinstance(languages, dict):
            raise MetricsError("GitHub returned invalid language data.")
        for language, count in languages.items():
            if not isinstance(language, str) or not language.strip():
                raise MetricsError("GitHub returned an invalid language name.")
            byte_count = nonnegative_int(count, "language byte")
            if byte_count:
                language_bytes[language] += byte_count
    contributions = api.contributions(username, start, end)
    # The only persisted data is aggregate data. No repo names, API responses,
    # authentication details, or private repository language data are persisted.
    return {
        "schema_version": 1,
        "username": username,
        "updated_at": utc_timestamp(end),
        "window": {
            "from": utc_timestamp(start), "to": utc_timestamp(end), "utc_calendar_dates": 365,
            "definition": "Today and the previous 364 UTC dates; today is partial.",
        },
        "contributions": contributions,
        "repositories": {
            "scope": "Public repositories owned by this user, excluding forks; archived repositories included.",
            "count": len(repositories), "stars": sum(repo["stars"] for repo in repositories),
        },
        "languages": {
            "unit": "GitHub Linguist source-code bytes",
            "total_bytes": sum(language_bytes.values()),
            "bytes": dict(sorted(language_bytes.items(), key=lambda item: (-item[1], item[0]))),
        },
        "sources": {
            "contributions": "GitHub GraphQL contributionsCollection; GitHub contribution eligibility and visibility rules apply.",
            "repositories": "GitHub REST user repositories, with pagination; private repositories and forks excluded.",
            "languages": "GitHub REST languages endpoint for every included repository; shares use all returned source bytes.",
        },
    }


def language_shares(metrics: dict[str, Any], limit: int = 5) -> list[tuple[str, int, float]]:
    languages = sorted(metrics["languages"]["bytes"].items(), key=lambda item: (-item[1], item[0]))
    total = metrics["languages"]["total_bytes"]
    if total == 0:
        return []
    top = languages[:limit]
    remainder = sum(count for _, count in languages[limit:])
    if remainder:
        top.append(("Other", remainder))
    return [(name, count, count / total * 100) for name, count in top]


def svg_text(x: float, y: float, value: str, color: str, size: int = 15, weight: int = 400, anchor: str = "start") -> str:
    return f'<text x="{x:g}" y="{y:g}" fill="{color}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(value)}</text>'


def svg_shell(title: str, description: str, palette: dict[str, str], content: list[str], height: int = 235, width: int = 920) -> str:
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(title)}</title>',
        f'<desc id="desc">{html.escape(description)}</desc>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="22" fill="{palette["bg"]}" stroke="{palette["border"]}"/>',
        '<g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif">',
        *content, '</g>', '</svg>', '',
    ])


def friendly_timestamp(timestamp: str) -> str:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M UTC")


def activity_svg(metrics: dict[str, Any], theme: str) -> str:
    p = PALETTES[theme]
    window = metrics["window"]
    start = datetime.fromisoformat(window["from"].replace("Z", "+00:00")).strftime("%d %b %Y")
    end = datetime.fromisoformat(window["to"].replace("Z", "+00:00")).strftime("%d %b %Y")
    values = [
        (metrics["contributions"]["total"], "Contributions", "Past 365 UTC days"),
        (metrics["contributions"]["commits"], "Commit contributions", "Past 365 UTC days"),
        (metrics["contributions"]["pull_requests"], "Pull requests", "Contribution count"),
        (metrics["repositories"]["stars"], "Public repo stars", "Current total · owned repos"),
    ]
    parts = [svg_text(32, 40, "GITHUB ACTIVITY", p["accent"], 16, 700)]
    for index, (number, label, detail) in enumerate(values):
        x = 32 + index * 222
        if index:
            parts.append(f'<path d="M{x - 17} 74 V169" stroke="{p["border"]}"/>')
        parts.extend([
            svg_text(x, 111, f"{number:,}", p["text"], 37, 700),
            svg_text(x, 141, label, p["text"], 15, 600),
            svg_text(x, 163, detail, p["muted"], 12),
        ])
    parts.append(f'<path d="M32 187 H888" stroke="{p["border"]}"/>')
    parts.append(svg_text(32, 213, f"{start} – {end} · Today is partial", p["muted"], 12))
    parts.append(svg_text(888, 213, f"Updated {friendly_timestamp(metrics['updated_at'])}", p["muted"], 12, anchor="end"))
    description = "; ".join(f"{label}: {number:,}" for number, label, _ in values)
    description += f". Contributions cover {start} through {end}, UTC, with today partial. Stars cover owned public non-fork repositories. Updated {metrics['updated_at']}."
    return svg_shell("GitHub activity for " + metrics["username"], description, p, parts)


def language_color(name: str) -> str:
    if name in LANGUAGE_COLORS:
        return LANGUAGE_COLORS[name]
    colors = ["#5d9f97", "#a18acc", "#bd9362", "#7aa1cc", "#bb7d94"]
    return colors[int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8], 16) % len(colors)]


def languages_svg(metrics: dict[str, Any], theme: str) -> str:
    p = PALETTES[theme]
    shares = language_shares(metrics)
    count = metrics["repositories"]["count"]
    parts = [
        svg_text(32, 40, "LANGUAGE MIX", p["accent"], 16, 700),
        svg_text(888, 40, "SHARE OF SOURCE BYTES", p["muted"], 12, 600, "end"),
        svg_text(32, 65, f"Across {count:,} public, owned repositories · Forks excluded", p["muted"], 13),
    ]
    if shares:
        parts.append('<defs><clipPath id="bar"><rect x="32" y="84" width="856" height="17" rx="8.5"/></clipPath></defs>')
        parts.append('<g clip-path="url(#bar)">')
        x = 32.0
        for name, _, share in shares:
            width = 856 * share / 100
            parts.append(f'<rect x="{x:.4f}" y="84" width="{width:.4f}" height="17" fill="{language_color(name)}"/>')
            x += width
        parts.append('</g>')
        for index, (name, _, share) in enumerate(shares):
            x = 32 + (index % 3) * 291
            y = 134 + (index // 3) * 34
            percentage = "<0.1%" if share < 0.1 else f"{share:.1f}%"
            # Keep full names in the accessible SVG description and metrics.json.
            label = name if len(name) <= 20 else name[:19] + "…"
            parts.append(f'<circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{language_color(name)}"/>')
            parts.append(svg_text(x + 18, y, label, p["text"], 15, 600))
            parts.append(svg_text(x + 260, y, percentage, p["muted"], 14, anchor="end"))
    else:
        parts.append(svg_text(32, 130, "GitHub reports no source-language bytes for these repositories.", p["muted"], 15))
    parts.append(f'<path d="M32 187 H888" stroke="{p["border"]}"/>')
    parts.append(svg_text(32, 213, "GitHub Linguist · Byte share, not proficiency", p["muted"], 12))
    parts.append(svg_text(888, 213, f"Updated {friendly_timestamp(metrics['updated_at'])}", p["muted"], 12, anchor="end"))
    description = "; ".join(f"{name}: {share:.2f}% ({byte_count:,} bytes)" for name, byte_count, share in shares)
    description = f"Language mix from {count} public owned non-fork repositories. {description}. Percentages use all {metrics['languages']['total_bytes']:,} source bytes, not a subset. Updated {metrics['updated_at']}."
    return svg_shell("Repository language mix for " + metrics["username"], description, p, parts)


def activity_mobile_svg(metrics: dict[str, Any], theme: str) -> str:
    p = PALETTES[theme]
    start = datetime.fromisoformat(metrics["window"]["from"].replace("Z", "+00:00")).strftime("%d %b %Y")
    end = datetime.fromisoformat(metrics["window"]["to"].replace("Z", "+00:00")).strftime("%d %b %Y")
    values = [
        (metrics["contributions"]["total"], "Contributions", "Past 365 UTC days"),
        (metrics["contributions"]["commits"], "Commit contributions", "Past 365 UTC days"),
        (metrics["contributions"]["pull_requests"], "Pull requests", "Contribution count"),
        (metrics["repositories"]["stars"], "Public repo stars", "Current total · owned repos"),
    ]
    parts = [svg_text(28, 40, "GITHUB ACTIVITY", p["accent"], 18, 700)]
    parts.append(f'<path d="M300 73 V305 M28 198 H572" stroke="{p["border"]}"/>')
    for index, (number, label, detail) in enumerate(values):
        x = 28 + (index % 2) * 294
        y = 112 + (index // 2) * 136
        parts.extend([
            svg_text(x, y, f"{number:,}", p["text"], 42, 700),
            svg_text(x, y + 32, label, p["text"], 18, 600),
            svg_text(x, y + 57, detail, p["muted"], 14),
        ])
    parts.append(f'<path d="M28 329 H572" stroke="{p["border"]}"/>')
    parts.append(svg_text(28, 355, f"{start} – {end} · UTC", p["muted"], 16))
    parts.append(svg_text(28, 379, "Today is partial", p["muted"], 14))
    parts.append(svg_text(28, 401, f"Updated {friendly_timestamp(metrics['updated_at'])}", p["muted"], 14))
    description = "; ".join(f"{label}: {number:,}" for number, label, _ in values)
    description += f". Contributions cover {start} through {end}, UTC, with today partial. Stars cover owned public non-fork repositories. Updated {metrics['updated_at']}."
    return svg_shell("GitHub activity for " + metrics["username"], description, p, parts, height=420, width=600)


def languages_mobile_svg(metrics: dict[str, Any], theme: str) -> str:
    p = PALETTES[theme]
    shares = language_shares(metrics)
    count = metrics["repositories"]["count"]
    parts = [
        svg_text(28, 40, "LANGUAGE MIX", p["accent"], 18, 700),
        svg_text(28, 65, f"Across {count:,} public, owned repos · Forks excluded", p["muted"], 14),
    ]
    if shares:
        parts.append('<defs><clipPath id="bar"><rect x="28" y="87" width="544" height="18" rx="9"/></clipPath></defs>')
        parts.append('<g clip-path="url(#bar)">')
        x = 28.0
        for name, _, share in shares:
            width = 544 * share / 100
            parts.append(f'<rect x="{x:.4f}" y="87" width="{width:.4f}" height="18" fill="{language_color(name)}"/>')
            x += width
        parts.append('</g>')
        for index, (name, _, share) in enumerate(shares):
            x = 28 + (index % 2) * 282
            y = 141 + (index // 2) * 39
            percentage = "<0.1%" if share < 0.1 else f"{share:.1f}%"
            label = name if len(name) <= 18 else name[:17] + "…"
            parts.append(f'<circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{language_color(name)}"/>')
            parts.append(svg_text(x + 18, y, label, p["text"], 16, 600))
            parts.append(svg_text(x + 252, y, percentage, p["muted"], 15, anchor="end"))
    else:
        parts.append(svg_text(28, 151, "GitHub reports no source-language bytes", p["muted"], 16))
        parts.append(svg_text(28, 177, "for these repositories.", p["muted"], 16))
    parts.append(f'<path d="M28 245 H572" stroke="{p["border"]}"/>')
    parts.append(svg_text(28, 273, "Source-byte share · Not proficiency", p["muted"], 16))
    parts.append(svg_text(28, 300, f"Updated {friendly_timestamp(metrics['updated_at'])}", p["muted"], 14))
    description = "; ".join(f"{name}: {share:.2f}% ({byte_count:,} bytes)" for name, byte_count, share in shares)
    description = f"Language mix from {count} public owned non-fork repositories. {description}. Percentages use all {metrics['languages']['total_bytes']:,} source bytes, not a subset. Updated {metrics['updated_at']}."
    return svg_shell("Repository language mix for " + metrics["username"], description, p, parts, height=320, width=600)


def render_assets(metrics: dict[str, Any]) -> dict[str, str]:
    assets = {"metrics.json": json.dumps(metrics, indent=2, ensure_ascii=False) + "\n"}
    for theme in PALETTES:
        assets[f"activity-{theme}.svg"] = activity_svg(metrics, theme)
        assets[f"languages-{theme}.svg"] = languages_svg(metrics, theme)
        assets[f"activity-mobile-{theme}.svg"] = activity_mobile_svg(metrics, theme)
        assets[f"languages-mobile-{theme}.svg"] = languages_mobile_svg(metrics, theme)
    return assets


def write_assets_atomic(output_dir: Path, assets: dict[str, str]) -> None:
    """Stage all output before replacing each file atomically on its filesystem."""
    output_dir.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    try:
        for name, text in assets.items():
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_dir, prefix=".metrics-", delete=False) as handle:
                temporary = Path(handle.name)
                staged.append((temporary, output_dir / name))
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(0o644)
        for temporary, destination in staged:
            os.replace(temporary, destination)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def generate(output_dir: Path, username: str, api: GitHubAPI | None = None, now: datetime | None = None) -> dict[str, Any]:
    metrics = collect_metrics(api or GitHubAPI(), username, now or datetime.now(UTC))
    assets = render_assets(metrics)
    write_assets_atomic(output_dir, assets)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent.parent / "assets")
    parser.add_argument("--username", default=os.environ.get("GITHUB_USERNAME", "jasilmeledath"))
    args = parser.parse_args()
    try:
        metrics = generate(args.output_dir, args.username)
    except (MetricsError, OSError) as exc:
        print(f"Metrics update failed: {exc}", file=sys.stderr)
        return 1
    print(f"Updated GitHub metrics for {metrics['username']} at {metrics['updated_at']} ({metrics['repositories']['count']} public owned non-fork repositories).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
