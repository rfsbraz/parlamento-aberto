# sessions

One row per legislative session.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `sessions.parquet` and `sessions.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals. |
| `session_number` | INTEGER | Session number within the legislature. |
| `start_date` | DATE | First day of the session. |
| `end_date` | DATE | Last day of the session. |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

### stg_informacao_base__sessions

InformacaoBase SessoesLegislativas, one row per legislative session.

| Column | Type | Description |
|---|---|---|
| `session_number` | INTEGER | Session number within the legislature (numSessao). |
| `start_date` | DATE | First day of the session (dataInicio). |
| `end_date` | DATE | Last day of the session (dataFim). |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |
