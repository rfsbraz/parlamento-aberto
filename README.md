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

## Fetching AR data

```sh
uv run python -m parlamento_aberto fetch                         # current legislature
uv run python -m parlamento_aberto fetch --all                   # every legislature
uv run python -m parlamento_aberto fetch --dataset iniciativas --legislature XVI
```

`sources.yaml` lists every file. The newest legislature in it is the current one. Requests go one at a time, with gzip, and retry the AR's temporary "Recurso Não Encontrado" pages with backoff. Run it after 06:00 Lisbon time; the AR server is slow between 04:00 and 06:00. Files whose download hash matches `data/_meta/sources.lock.json` are skipped. A download that is HTML, does not parse, or is empty where the last copy had records keeps the last good copy and is marked stale in the lock. `--raw-dir DIR` keeps the downloads outside the repo, and `--offline` replays them.

Design: `docs/design.md`. Repo settings: `docs/repo-settings.md`.
