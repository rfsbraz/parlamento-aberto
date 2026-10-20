# group_memberships

One row per deputy, legislature and parliamentary group period (DepGP).

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `group_memberships.parquet` and `group_memberships.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals. |
| `cadastro_id` | BIGINT | Person id, joins to deputies. |
| `group_id` | BIGINT | AR id of the group in this legislature (gpId). |
| `group_acronym` | VARCHAR | Group acronym, joins to parliamentary_groups. |
| `start_date` | DATE | First day in the group. |
| `end_date` | DATE | Last day in the group, null while the membership is open. |
| `is_open` | BOOLEAN | True when the legislature is running and AR's end date is on or after the extract date. |

## Known quirks

- AR writes the extract date as the end date of an open membership. The old mapper stored that date as published, so open memberships looked closed. Here an open membership has a null end_date and is_open = true.
- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

Marts: [legislatures](legislatures.md).

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
