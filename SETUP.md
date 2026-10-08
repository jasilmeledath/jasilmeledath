# Install your updated GitHub profile

This package contains the updated README, custom light and dark banners, real GitHub metric snapshots, and the workflow that refreshes them. The latest portfolio and contact details were checked on 8 October 2026.

## Activate the profile

1. Copy the **contents** of this folder into the root of your public [jasilmeledath/jasilmeledath repository](https://github.com/jasilmeledath/jasilmeledath), replacing its README. Include the hidden `.github` folder, `assets`, `scripts`, and `tests`. Keep any unrelated existing repository files.
2. Commit the files to `main`, the repository's current default branch. A push containing the workflow or generator starts the first refresh automatically.
3. Open **Actions → Refresh profile metrics** and check for a successful run. You can also select **Run workflow** to refresh manually.

No Vercel deployment, paid service, or personal access token is required. The workflow uses GitHub's built-in repository token. The refresh job has permission to commit generated assets. If your organization or branch rules block automated pushes, use its approved publishing process rather than disabling protections.

**Copying the README alone is not enough:** the banner and metric images are local repository assets, and automatic updates need the workflow and generator.

## What refreshes automatically

The schedule is daily at **08:47 IST / 03:17 UTC**, with additional manual runs and runs after changes to the generator, tests, or workflow. GitHub can delay scheduled jobs. Public-repository schedules can be disabled after 60 days without activity; check Actions if a timestamp stops advancing.

- Contributions, commit contributions, and pull request contributions: a moving window covering 365 UTC calendar dates, ending at the time of the refresh. The current day is partial.
- Stars received: current sum across all public repositories you own, excluding forks.
- Repository languages: bytes returned by GitHub across the same public, owned, non-fork repository set. Archived repositories remain included. All reported languages contribute to the denominator, including those grouped under “Other.”
- Both color themes, desktop and mobile cards, and the source-data file update from the same successful fetch. Every card displays its refresh time. Failed API calls stop the workflow before publication and leave the previous cards visible.

Your professional bio, selected projects, and working stack are deliberately curated text. They reflect the supplied portfolio at the time of this update; changing the portfolio will not automatically rewrite these sections.

## Why some GitHub numbers differ

Contributions are not the same as commits. GitHub counts several qualifying activities, applies attribution and branch rules, and may take time to process changes. The generator uses GitHub's contribution-calendar total directly; it does not add commit or pull request counts a second time.

The contribution cards reflect what GitHub exposes to the credentials used for the refresh. The included workflow uses `GITHUB_TOKEN`; a local run through an owner-authenticated `gh` session can see a different contribution scope. Compare the visible dates and credentials before comparing totals. The included initial snapshot was generated through the locally authenticated GitHub CLI; the first workflow run will replace it with workflow-visible data.

To show anonymized private activity on your native GitHub profile, use the profile's **Contribution settings → Private contributions** option. This does not make private source code public. A README cannot recover work that GitHub does not attribute or expose, and this package does not automatically grant access to private repositories. Stars and language statistics always exclude private repositories, even during an owner-authenticated local run.

The old “rank,” streak card, and profile-view counter were removed. A rank is a service-specific score; a proxy-hit counter is not a unique visitor count; streaks can differ by date boundaries and visibility. The native contribution history is linked for deeper inspection.

## Optional profile polish

- Set your GitHub website field to `https://jasil-portfolio-nu.vercel.app/`. The existing GitHub profile still points to the old domain, which did not resolve during this review.
- Suggested GitHub bio: **Full-stack + cloud engineer. Building web products, backend systems, and AWS infrastructure. Creator of TracePanel.**
- Pin `trace-panel-npm`, `ghost-memory-daemon`, the Picbox application, `uniwayin-ums-api`, and another project you want people to inspect. Woobe is linked through the public portfolio because no public Woobe repository was verified.
- Keep project READMEs useful: a short description, a screenshot or demo, your contribution, and clear setup instructions.

## Research and sources

- [Your current portfolio](https://jasil-portfolio-nu.vercel.app/) — role, location, email, projects, and stack.
- [Your public repositories](https://github.com/jasilmeledath?tab=repositories) — verified source-code destinations.
- [GitHub: using your profile to enhance your resume](https://docs.github.com/en/account-and-profile/tutorials/using-your-github-profile-to-enhance-your-resume) — brief positioning, project context, and selective repository pins.
- [Awesome GitHub Profile README](https://github.com/abhisheknaiidu/awesome-github-profile-readme) and [profile README templates](https://github.com/kautukkundan/Awesome-Profile-README-templates) — explored layout and automation patterns.
- [Simon Willison's profile repository](https://github.com/simonw/simonw) — example of a useful profile maintained through automation.
- [Original GitHub Readme Stats project](https://github.com/anuraghazra/github-readme-stats) — current maintenance notice and shared-service reliability limitations.
- [GitHub Readme Stats Action](https://github.com/stats-organization/github-readme-stats-action) — researched as an alternative; this package uses a small direct-API generator for explicit definitions and custom styling.
- [GitHub contribution rules](https://docs.github.com/en/account-and-profile/reference/profile-contributions-reference), [GraphQL object reference](https://docs.github.com/en/graphql/reference/objects), and [repository language API](https://docs.github.com/en/rest/repos/repos#list-repository-languages) — counting and visibility definitions.
- [Scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) — scheduling limitations.
- [Profile view counter documentation](https://github.com/antonkomarev/github-profile-views-counter#why-does-the-counter-increase-every-time-the-page-is-reloaded) — why request hits were removed.

## Local verification

The package needs Python 3.10+ and the GitHub CLI, both available on the selected GitHub-hosted runner. No Python packages are installed.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update_metrics.py
```

The second command uses the current GitHub CLI login locally. Never paste a token into the README, command arguments, or committed files.
