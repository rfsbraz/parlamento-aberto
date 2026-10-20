# parliamentary_groups

One row per parliamentary group per legislature.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `parliamentary_groups.parquet` and `parliamentary_groups.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals. |
| `group_acronym` | VARCHAR | Group acronym, for example PS. |
| `name` | VARCHAR | Full name of the party or group. |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

### stg_informacao_base__parliamentary_groups

InformacaoBase GruposParlamentares, one row per parliamentary group.

| Column | Type | Description |
|---|---|---|
| `group_acronym` | VARCHAR | Group acronym (sigla), for example PS. |
| `name` | VARCHAR | Full name of the party or group (nome). |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |
