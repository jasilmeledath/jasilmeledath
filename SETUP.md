# Maintaining this profile

The README uses repository-owned SVGs with light, dark, desktop, and mobile variants. The hero's decorative paths and architecture panel animate using SVG CSS. Text stays readable without animation, and `prefers-reduced-motion` disables motion. No third-party image generator or stats-card service is required.

## Metrics refresh

`.github/workflows/profile-metrics.yml` schedules a refresh at minute 17 of every hour. It also supports **Actions → Refresh profile metrics → Run workflow**, and runs after changes to the workflow, metrics generator, or tests on `main`.

The job uses the built-in `GITHUB_TOKEN` and only needs write access to this profile repository to publish its generated files. It validates the calculations before fetching data. A failed fetch preserves the last successful assets and timestamp. The README's workflow badge makes failures visible.

**Known blocker, diagnosed 1 November 2026:** GitHub rejected the refresh job before it started with: “The job was not started because your account is locked due to a billing issue.” The snapshot was refreshed locally through the owner's authenticated GitHub CLI. The repository schedule cannot resolve an account billing lock. After resolving the account issue in GitHub's billing settings, run the workflow manually and confirm success. No payment or billing settings were changed as part of this update.

A scheduled snapshot is not real-time. GitHub may delay scheduled runs, cache image responses, or take up to 24 hours to credit a contribution. The timestamp on each card is the last successful API snapshot. A public repository's schedule can also be disabled after 60 days of inactivity.

## Scope of the numbers

- Contributions: GitHub's calendar total for today and the previous 364 UTC dates; today is partial. Commit and pull request contributions are separate breakdowns and are not added again.
- Repository count and stars: public repositories owned by the user, excluding forks and including archived repositories.
- Languages: source-code bytes across that same repository set. All languages contribute to the denominator, including those grouped under “Other.”
- No private repository names, private source code, or credentials are saved in the generated files.

An owner-authenticated local run may see a different contribution scope from a workflow using the repository token. The card must be compared using the same date window and visibility. Public private-contribution counts follow the user's **Contribution settings → Private contributions** preference. The profile does not promise identical numbers across different credentials, date windows, and GitHub processing delays.

## Local refresh and checks

Requires Python 3.10+ and an authenticated GitHub CLI. No third-party Python packages are needed.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update_metrics.py
python3 scripts/build_visuals.py
```

The first command verifies counting, pagination, date boundaries, SVG output, and preservation of previous cards on API failures. The second regenerates activity and language cards plus `assets/metrics.json`. The third rebuilds the animated hero variants. Commit the generated assets with any generator changes. Never put tokens in the README, script arguments, or committed files.

The bio, selected work, and technology list are curated text, so portfolio changes do not rewrite them automatically.

## References

- [Contribution attribution and delays](https://docs.github.com/en/account-and-profile/how-tos/contribution-settings/troubleshooting-missing-contributions)
- [Scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Contribution visibility settings](https://docs.github.com/en/account-and-profile/how-tos/contribution-settings)
- [Portfolio and project background](https://jasil-portfolio-nu.vercel.app/)
