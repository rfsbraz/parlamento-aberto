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

## Data bot token

The data workflows (`.github/workflows/data-sync.yml`, `data-merge.yml` and `discover.yml`) need a repository secret named `DATA_BOT_TOKEN`. Rodrigo creates it and stores it under Settings, Secrets and variables, Actions. The value never goes into git or chat.

It must be a GitHub App installation token or a fine-grained personal access token scoped to `rfsbraz/parlamento-aberto` only, with:

| Permission | Access | Used for |
| --- | --- | --- |
| Contents | Read and write | Push `data/nightly` and `data/discover`, and squash-merge data PRs |
| Pull requests | Read and write | Open, update and merge the data PR, and open the held discover PR |
| Issues | Read and write | Create and add the `data`, `hold:` and `historical-change` labels |
| Metadata | Read | Required by GitHub for any token |

`GITHUB_TOKEN` cannot replace it: PRs it opens do not trigger CI, and merges it makes do not trigger later workflows. If the secret is missing, data-sync and data-merge stop at their first step with an error naming `DATA_BOT_TOKEN`. The discover job still runs without it: it pushes nothing and lists any new links in its issue, which it opens with `GITHUB_TOKEN`.

Merge policy while native auto-merge is unavailable: `data-merge.yml` runs when CI finishes on the `data/nightly` PR and squash-merges it if CI passed on the PR's current head and it has no `hold:` label. Held PRs wait for Rodrigo.

## Data releases

`.github/workflows/data-release.yml` runs on every push to `main` that touches `data/`, `src/` or `docs/data-changelog.md`. It skips when `main` has no `data/_meta/sources.lock.json`. Otherwise it runs all data tests on `data/`, builds the release assets and checks row counts against the latest release. It uses `GITHUB_TOKEN` only, with `contents: write` for this job.

Publishing waits for Rodrigo's OK, since the first public release goes out with the repo going public. Until the repository variable `DATA_RELEASES` (Settings, Secrets and variables, Actions, Variables) is set to `on`, each run uploads the assets as a workflow artifact, kept for 7 days, and creates no release or tag.
