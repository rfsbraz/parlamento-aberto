# interest_declarations

One row per declaration in the register of interests, XI to XV. XVI and XVII are not in the AR open data (declarations moved to the Entidade para a Transparência). Only people on the XVII lists are covered, since every file lists those people. Names, spouse, marital status, property regime, tax and contact fields are left out; join deputies for names.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `interest_declarations.parquet` and `interest_declarations.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file. |
| `declaration_key` | VARCHAR | Key of the declaration, joins to interests. |
| `cadastro_id` | BIGINT | Person id, joins to deputies. |
| `format_version` | VARCHAR | Published format, V1 (XI), V2 (XII, XIII), V3 (XIV) or V5 (XIV, XV). |
| `declaration_id` | BIGINT | AR id of the declaration. Null for V3, which publishes none. |
| `position` | VARCHAR | Office declared, for example Deputado. |
| `position_start_date` | DATE | Start of the office, when published as a full date. |
| `position_changed_date` | DATE | Date the office changed, when published as a full date. |
| `position_end_date` | DATE | End of the office, when published as a full date. |
| `position_start_raw` | VARCHAR | Start of the office as published. V1 and V2 publish a year. |
| `version_date` | DATE | Date of this version of the declaration, V1 and V2 only. |
| `is_exclusive` | BOOLEAN | Office held in exclusivity. Null for V1 and V2. |
| `items` | INTEGER | Number of rows in interests for this declaration. |

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
