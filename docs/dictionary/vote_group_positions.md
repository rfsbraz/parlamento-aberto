# vote_group_positions

One row per vote, group and position, from the parsed detail. Votes without a detail take absent groups and deputies from the ausencias field. A unanimous vote that lists no favour, against or abstention position gets a favour row, with inferred = true, for every other group present: for a plenary vote, groups with a deputy seated on the vote date (the seated_on rule); for a committee vote, groups with an active effective member of the committee on the vote date, from ComposicaoOrgaos.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `vote_group_positions.parquet` and `vote_group_positions.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `vote_id` | BIGINT | Vote, joins to votes. |
| `legislature` | VARCHAR | Legislature of the vote. |
| `body` | VARCHAR | Where the vote was held, plenary or the committee name. |
| `group_code` | VARCHAR | Group code after seed_group_aliases, joins to parliamentary_groups.group_acronym. Indep and Ninsc mark deputies outside any group. |
| `group_code_raw` | VARCHAR | Group code as published (or, for inferred rows, as in the deputy's InformacaoBase membership). |
| `position` | VARCHAR | favour, against, abstention or absent. |
| `deputies` | INTEGER | Null when the group as a whole took the position (apart from any of its deputies listed under another position). Otherwise the number of its deputies who did. |
| `inferred` | BOOLEAN | True when the row comes from the unanimous rule rather than the published detail. |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

Marts: [deputies](deputies.md), [mandates](mandates.md), [group_memberships](group_memberships.md), [votes](votes.md).

### stg_composicao_orgaos__committee_members

ComposicaoOrgaos Comissoes, one row per committee member record (HistoricoComposicao).

| Column | Type | Description |
|---|---|---|
| `committee_id` | BIGINT | AR id of the committee (DetalheOrgao.idOrgao). |
| `committee_name` | VARCHAR | Committee name (DetalheOrgao.nomeSigla), trimmed. |
| `cadastro_id` | BIGINT | Person id (depCadId), joins to deputies. |
| `situations` | STRUCT(status VARCHAR, membership VARCHAR, start_date DATE, end_date DATE)[] | Membership periods (depSituacao) as status (sioDes, Ativo or Inativo), membership (sioTipMem, Efetivo or Suplente), start_date, end_date. |
| `groups` | STRUCT(group_acronym VARCHAR, start_date DATE, end_date DATE)[] | Group periods (depGP) as group_acronym, start_date, end_date. An open period has a null end date. |
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
