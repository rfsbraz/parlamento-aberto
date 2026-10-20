# initiative_authors

One row per author of an initiative.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `initiative_authors.parquet` and `initiative_authors.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature of the initiative. |
| `initiative_id` | BIGINT | Initiative, joins to initiatives. |
| `author_type` | VARCHAR | deputy, group, or other for any author that is not a deputy or a group (Governo, a regional assembly, a committee, citizens). |
| `cadastro_id` | BIGINT | For a deputy, the person id, joins to deputies. |
| `group_code` | VARCHAR | For a deputy, the group listed with them; for a group, its code. After seed_group_aliases. |
| `group_code_raw` | VARCHAR | The same code as published. |
| `name` | VARCHAR | For a deputy, the name as published; for other, the author (the committee name, or the kind of author such as Governo). |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

### stg_iniciativas__initiatives

Iniciativas, one row per initiative record.

| Column | Type | Description |
|---|---|---|
| `initiative_id` | BIGINT | AR id of the initiative (IniId). |
| `number` | INTEGER | Initiative number within its type and legislature (IniNr). |
| `type_code` | VARCHAR | Initiative type code (IniTipo), for example J. |
| `type` | VARCHAR | Initiative type (IniDescTipo), for example Projeto de Lei. |
| `session_number` | INTEGER | Legislative session the initiative was submitted in (IniSel). |
| `title` | VARCHAR | Title (IniTitulo). |
| `text_url` | VARCHAR | Link to the initiative text (IniLinkTexto). |
| `author_kind_code` | VARCHAR | Code of the kind of author (IniAutorOutros.sigla), for example D, G or V. |
| `author_kind` | VARCHAR | Kind of author (IniAutorOutros.nome), for example Deputados, Grupos Parlamentares or Governo. |
| `author_committee` | VARCHAR | Committee that authored the initiative, when the author is a committee (IniAutorOutros.iniAutorComissao). |
| `author_deputies` | STRUCT(cadastro_id BIGINT, "name" VARCHAR, group_acronym VARCHAR)[] | Deputy authors (IniAutorDeputados) as cadastro_id, name, group_acronym. |
| `author_groups` | VARCHAR[] | Group authors (IniAutorGruposParlamentares) as group acronyms. |
| `events` | STRUCT(event_id BIGINT, phase VARCHAR, phase_date DATE, votes STRUCT(id VARCHAR, "data" VARCHAR, resultado VARCHAR, reuniao VARCHAR, tipoReuniao VARCHAR, unanime VARCHAR, descricao VARCHAR, detalhe VARCHAR, ausencias VARCHAR[])[], committees STRUCT(committee_id BIGINT, committee_name VARCHAR, votes STRUCT(id VARCHAR, "data" VARCHAR, resultado VARCHAR, reuniao VARCHAR, unanime VARCHAR, descricao VARCHAR, detalhe VARCHAR, ausencias VARCHAR[])[])[])[] | Events (IniEventos) as event_id, phase, phase_date, the raw plenary votes (Votacao) and the committees (Comissao) as committee_id, committee_name and their raw votes. |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |

### seed_group_aliases

Hand-kept aliases for group codes the AR writes differently within a legislature, each row citing its source. Marts keep the published code in group_code_raw and put the aliased code, or the published one when no alias applies, in group_code.

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals (the data folder name, for example I-B) the alias applies to. |
| `alias` | VARCHAR | Code as published, for example PPD. |
| `group_code` | VARCHAR | Code it maps to, as listed in that legislature's parliamentary_groups. |
| `source_url` | VARCHAR | Reference for the mapping. |
| `note` | VARCHAR | Why the alias exists. |
