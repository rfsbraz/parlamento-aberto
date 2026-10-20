# interests

One row per declared interest: activities and offices, social positions, societies, supports, services and other situations. Text is as published, so free-text items can read "Nada a declarar". The JSON wins over the old mapper: V1 publishes activities as one free-text field, and V5 is read too (XIV, XV), since the dump has it.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `interests.parquet` and `interests.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals. |
| `declaration_key` | VARCHAR | Declaration, joins to interest_declarations. |
| `item_number` | INTEGER | Position of the item within the declaration. |
| `cadastro_id` | BIGINT | Person id, joins to deputies. |
| `category` | VARCHAR | activity, social_position, society, support, service or other_situation. |
| `source_list` | VARCHAR | Published list or field the item comes from, for example GenCargosMaisTresAnos. |
| `item_id` | BIGINT | AR id of the item, when published. |
| `type_code` | INTEGER | V3 Type code as published (0, 1 or 2), undocumented by the AR. |
| `description` | VARCHAR | Activity, office, support, service or situation as written. |
| `entity` | VARCHAR | Entity, company or body named. |
| `nature` | VARCHAR | Nature of the entity or benefit, V5 only. |
| `activity_area` | VARCHAR | Area of activity. |
| `location` | VARCHAR | Head office or place. |
| `share` | VARCHAR | Shareholding as written, for societies. |
| `is_paid` | BOOLEAN | True for S, false for N. Null otherwise, including the 0 V5 publishes. |
| `start_date` | DATE | Start date, when published as a full date. |
| `end_date` | DATE | End date, when published as a full date. |
| `start_date_raw` | VARCHAR | Start date as published, a year, a month or a day. |
| `end_date_raw` | VARCHAR | End date as published. |
| `date_raw` | VARCHAR | Single date or period as published for V5 supports and services. |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

### stg_registo_interesses__declarations

RegistoInteresses declarations, one row each, from cadRgi (V1, V2), RecordInterests (V3) or the V5 form. Dates are as published.

| Column | Type | Description |
|---|---|---|
| `declaration_key` | VARCHAR | Key built as legislature-cadastro_id-n, n counting the person's declarations in the file. |
| `cadastro_id` | BIGINT | Person id (cadId, RecordId or IdCadastroGODE). |
| `format_version` | VARCHAR | Format of the record, V1, V2, V3 or V5. |
| `declaration_id` | BIGINT | AR id of the declaration (rgiId or FactoDeclaracao.Id). V3 publishes none. |
| `declared_legislature` | VARCHAR | Legislature the declaration names (rgiLegDes or Legislatura). V3 names none, so it is the file's. |
| `position` | VARCHAR | Office declared (rgiCargoDes, PositionDesignation or CargoFuncao). |
| `position_start_raw` | VARCHAR | Start of the office as published (rgiCargoData, a year, PositionBeginDate or DataInicioFuncao). |
| `position_changed_raw` | VARCHAR | Date the office changed as published (PositionChangedDate or DataAlteracaoFuncao). |
| `position_end_raw` | VARCHAR | End of the office as published (PositionEndDate or DataCessacaoFuncao). |
| `version_date_raw` | VARCHAR | Date of this version of the declaration (rgiDataVersao), V1 and V2 only. |
| `is_exclusive` | BOOLEAN | Office held in exclusivity (V3 Exclusivity, V5 Exclusividade). Null for V1 and V2. |
| `items` | INTEGER | Number of declared items, one row each in stg_registo_interesses__items. |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |

### stg_registo_interesses__items

One row per declared item, as published. Free-text fields of V1 and V2 (and V1 activities) become one item each.

| Column | Type | Description |
|---|---|---|
| `declaration_key` | VARCHAR | Declaration the item belongs to. |
| `item_number` | INTEGER | Position of the item within the declaration. |
| `category` | VARCHAR | activity, social_position, society, support, service or other_situation. |
| `source_list` | VARCHAR | Published list or field the item comes from, for example rgiCargosSociais or GenCargosMenosTresAnos. |
| `item_id` | BIGINT | AR id of the item, when published. |
| `type_code` | INTEGER | V3 Type code as published (0, 1 or 2), undocumented by the AR. |
| `description` | VARCHAR | Activity, office, support, service or situation as written. |
| `entity` | VARCHAR | Entity, company or body named. |
| `nature` | VARCHAR | Nature of the entity or benefit (V5 Natureza, NaturezaBeneficio). |
| `activity_area` | VARCHAR | Area of activity. |
| `location` | VARCHAR | Head office or place. |
| `share` | VARCHAR | Shareholding as written, for societies. |
| `paid_raw` | VARCHAR | Paid flag as published (S, N, or 0 in V5). |
| `start_date_raw` | VARCHAR | Start date as published, a year, a month or a day. |
| `end_date_raw` | VARCHAR | End date as published. |
| `date_raw` | VARCHAR | Single date or period as published for V5 supports and services. |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |
