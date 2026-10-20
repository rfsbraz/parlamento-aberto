# electoral_circles

One row per electoral circle per legislature.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `electoral_circles.parquet` and `electoral_circles.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals. |
| `circle_id` | INTEGER | AR id of the electoral circle. |
| `name` | VARCHAR | Name of the electoral circle. |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

### stg_informacao_base__electoral_circles

InformacaoBase CirculosEleitorais, one row per electoral circle.

| Column | Type | Description |
|---|---|---|
| `circle_id` | INTEGER | AR id of the electoral circle (cpId). |
| `name` | VARCHAR | Name of the electoral circle (cpDes). |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |
