# legislatures

One row per legislature.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `legislatures.parquet` and `legislatures.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals, for example XVII. |
| `legislature_id` | INTEGER | AR internal id of the legislature. |
| `start_date` | DATE | First day of the legislature. |
| `end_date` | DATE | Last day of the legislature, null while it is running. |
| `extract_date` | DATE | Date of the AR extract, taken from the end date AR writes on open group memberships. |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

### stg_informacao_base__legislatures

InformacaoBase DetalheLegislatura, one row per legislature file.

| Column | Type | Description |
|---|---|---|
| `legislature_id` | INTEGER | AR internal id of the legislature (id). |
| `start_date` | DATE | First day of the legislature (dtini). |
| `end_date` | DATE | Last day of the legislature (dtfim), null while it is running. |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |

### stg_informacao_base__deputies

InformacaoBase Deputados, one row per person on the lists of a legislature, elected or not.

| Column | Type | Description |
|---|---|---|
| `cadastro_id` | BIGINT | Person id shared across legislatures and datasets (DepCadId). |
| `deputy_id` | BIGINT | Id of this person in this legislature (DepId). |
| `full_name` | VARCHAR | Full name (DepNomeCompleto). |
| `parliamentary_name` | VARCHAR | Name used in parliament (DepNomeParlamentar). |
| `circle_id` | INTEGER | Electoral circle the person ran in (DepCPId). |
| `circle_name` | VARCHAR | Name of that electoral circle (DepCPDes). |
| `situations` | STRUCT(situation VARCHAR, start_date DATE, end_date DATE)[] | Situation periods (DepSituacao) as situation, start_date, end_date. |
| `groups` | STRUCT(group_id BIGINT, group_acronym VARCHAR, start_date DATE, end_date DATE)[] | Group memberships (DepGP) as group_id, group_acronym, start_date, end_date. |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |
