# initiatives

One row per initiative.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `initiatives.parquet` and `initiatives.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature of the initiative, from the file path. Legislature I is published in two files, I-A and I-B. |
| `initiative_id` | BIGINT | AR id of the initiative. |
| `number` | INTEGER | Initiative number within its type and legislature. |
| `type_code` | VARCHAR | Initiative type code, for example J. |
| `type` | VARCHAR | Initiative type, for example Projeto de Lei. |
| `session_number` | INTEGER | Legislative session the initiative was submitted in. |
| `title` | VARCHAR | Title. |
| `author_kind` | VARCHAR | Kind of author as published, for example Deputados, Grupos Parlamentares or Governo. |
| `first_event_date` | DATE | Date of the earliest event on the initiative. |
| `text_url` | VARCHAR | Link to the initiative text. |

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
