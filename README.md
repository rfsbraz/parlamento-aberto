# parlamento-aberto

Clean, versioned, documented open data about the Assembleia da República, rebuilt from the official open data dumps. The raw source lives in git under `data/`, so every change the AR makes shows up as a reviewable diff, and each data release publishes Parquet and CSV tables built from it.

Fonte: Assembleia da República, dados abertos.

The AR allows free reuse of its open data as long as the source is credited. Terms: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx

## Licences

- Code: MIT (`LICENSE`).
- Data: CC BY 4.0 (`LICENSE-DATA`), for everything under `data/` and the published marts.

## Personal data

Biographies, birth dates and interest registers are personal data. This repo republishes only what the AR publishes.

To report wrong data, open an issue with the [Correção de dados](../../issues/new?template=correcao-de-dados.yml) form. Personal-data removal requests can use the same form, or GitHub private vulnerability reporting once the repo is public. Please do not paste the personal data itself into a public issue.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python scripts/check_file_size.py
```

## Data releases

Each push to `main` that changes data or code builds the marts, runs every data test on `data/` and, if they pass, publishes a GitHub Release tagged `data-YYYY-MM-DD` (`-2`, `-3` for a second or third that day). Each release has one Parquet file and one gzipped CSV per mart, `manifest.json` and a `CHANGELOG.md` excerpt from `docs/data-changelog.md`. The first line of every CSV is a `#` comment with the attribution, so skip one line when reading (`skiprows=1` in pandas, `skip = 1` in R or DuckDB). A mart that loses more than 5% of its rows in a legislature against the previous release blocks the release unless `docs/data-changelog.md` acknowledges it. Publishing is off until the repo goes public (see `docs/repo-settings.md`).

To build the same assets locally:

```sh
uv run python -m parlamento_aberto.release build --data data --out dist --sha "$(git rev-parse HEAD)" --date "$(date +%F)"
```

## Fetching AR data

```sh
uv run python -m parlamento_aberto fetch                         # current legislature
uv run python -m parlamento_aberto fetch --all                   # every legislature
uv run python -m parlamento_aberto fetch --dataset iniciativas --legislature XVI
```

`sources.yaml` lists every file. The newest legislature in it is the current one. Requests go one at a time, with gzip, and retry the AR's temporary "Recurso Não Encontrado" pages with backoff. Run it after 06:00 Lisbon time; the AR server is slow between 04:00 and 06:00. Files whose download hash matches `data/_meta/sources.lock.json` are skipped. A download that is HTML, does not parse, or is empty where the last copy had records keeps the last good copy and is marked stale in the lock. `--raw-dir DIR` keeps the downloads outside the repo, and `--offline` replays them.

## Data dictionary

`docs/dictionary` has one page per mart, generated from `src/parlamento_aberto/models/schema.yml`. `docs/querying.md` shows how to query a release with DuckDB, pandas and R. After changing a model or its column descriptions, regenerate the pages; CI fails when they are out of date:

```sh
uv run python -m parlamento_aberto.dictionary
```

## Discover

Every Monday at 08:00 Lisbon, `.github/workflows/discover.yml` reads the AR open data pages and compares their JSON links with `sources.yaml`. New links for a known dataset, such as a new legislature, become a PR on `data/discover` labelled `hold: new-dataset`, which is never merged automatically. Removed links, files that match no dataset and pages it cannot read become one issue labelled `discover`. The `discover` block of `sources.yaml` lists what is left out on purpose. To run it locally (about 300 requests, two seconds apart):

```sh
uv run python -m parlamento_aberto.discover scan --scan scan.json
uv run python -m parlamento_aberto.discover diff --scan scan.json --report report.json
```

Design: `docs/design.md`. Repo settings: `docs/repo-settings.md`.
