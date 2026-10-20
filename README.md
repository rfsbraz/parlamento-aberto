# parlamento-aberto

Clean, versioned, documented open data about the Assembleia da República, rebuilt from the official open data dumps. The raw source lives in git under `data/`, so every change the AR makes shows up as a reviewable diff, and each data release publishes Parquet and CSV tables built from it.

Fonte: Assembleia da República, dados abertos.

The AR allows free reuse of its open data as long as the source is credited. Terms: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx

## Licences

- Code: MIT (`LICENSE`).
- Data: CC BY 4.0 (`LICENSE-DATA`), for everything under `data/` and the published marts.

## Personal data

Biographies, birth dates and interest registers are personal data. This repo republishes only what the AR publishes. To ask for a correction or removal of personal data, contact the maintainer, Rodrigo Braz, through his GitHub profile (https://github.com/rfsbraz). Please do not put the personal data itself in a public issue.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python scripts/check_file_size.py
```

Design: `docs/design.md`. Repo settings: `docs/repo-settings.md`.
