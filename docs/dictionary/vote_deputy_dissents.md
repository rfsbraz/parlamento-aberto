# vote_deputy_dissents

One row per deputy named in a vote detail, usually for voting apart from their group, or named as absent in the ausencias field of a vote without a detail. Matched to cadastro_id by parliamentary name (ignoring case and spacing) and group within the vote's legislature, or by name alone for Indep and Ninsc.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `vote_deputy_dissents.parquet` and `vote_deputy_dissents.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `vote_id` | BIGINT | Vote, joins to votes. |
| `legislature` | VARCHAR | Legislature of the vote. |
| `body` | VARCHAR | Where the vote was held, plenary or the committee name. |
| `position` | VARCHAR | favour, against, abstention or absent. |
| `name` | VARCHAR | Name as written in the detail. |
| `group_code` | VARCHAR | Group code after seed_group_aliases. |
| `group_code_raw` | VARCHAR | Group code as written in the detail. |
| `cadastro_id` | BIGINT | Person id, joins to deputies. Null when no deputy or more than one matches. |
| `candidates` | INTEGER | Number of deputies matching the name and group. 0 is unmatched, more than 1 is ambiguous. |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

Marts: [deputies](deputies.md), [votes](votes.md).

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

### stg_votes__detail_items

Built in Python by the vote parser. One row per item in each distinct vote detail string, or one row with an error when the parser rejects the string.

| Column | Type | Description |
|---|---|---|
| `detail` | VARCHAR | The detail string, joins to the detail column of the vote models. |
| `item_number` | INTEGER | Position of the item in the string, from 1. 0 on an error row. |
| `kind` | VARCHAR | group (a whole group), count (a number of a group's deputies, as in 2-PS) or deputy (a named deputy). |
| `group_acronym` | VARCHAR | Group code as written in the string. |
| `position` | VARCHAR | favour, against, abstention or absent. |
| `deputies` | INTEGER | For a count item, the number of deputies. |
| `name` | VARCHAR | For a deputy item, the name as written in the string. |
| `error` | VARCHAR | Why the parser rejected the string, null when it was parsed. |

### seed_group_aliases

Hand-kept aliases for group codes the AR writes differently within a legislature, each row citing its source. Marts keep the published code in group_code_raw and put the aliased code, or the published one when no alias applies, in group_code.

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals (the data folder name, for example I-B) the alias applies to. |
| `alias` | VARCHAR | Code as published, for example PPD. |
| `group_code` | VARCHAR | Code it maps to, as listed in that legislature's parliamentary_groups. |
| `source_url` | VARCHAR | Reference for the mapping. |
| `note` | VARCHAR | Why the alias exists. |
