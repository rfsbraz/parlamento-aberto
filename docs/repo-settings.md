# Repo settings

Settings for `rfsbraz/parlamento-aberto`, applied by Rodrigo in the GitHub UI. PRs never change settings; this file lists them so they are easy to verify.

| Setting | Value |
| --- | --- |
| Allow auto-merge | On |
| Automatically delete head branches | On |
| Merge methods | Squash merge only |
| Branch protection on `main` | Require a pull request before merging |
| Required status checks on `main` | `ruff`, `pytest`, `gitleaks`, `file size` |
| Required approving reviews | None, because data PRs merge once checks pass |

## Status (20 Oct 2026)

- Squash merge only: on.
- Automatically delete head branches: on.
- Allow auto-merge and branch protection: not available while the repo is private on the current plan. Until the repo is public, the data-PR workflow (#3) must merge clean data PRs itself once all checks pass, instead of relying on GitHub native auto-merge.
