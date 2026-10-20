# deputies

One row per person (cadastro_id) who appears on any list, elected or not. Use mandates to find who sat when.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `deputies.parquet` and `deputies.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `cadastro_id` | BIGINT | Person id shared across legislatures and datasets. |
| `full_name` | VARCHAR | Full name, from RegistoBiografico when present, otherwise from the latest InformacaoBase. |
| `parliamentary_name` | VARCHAR | Name used in parliament, from the latest legislature the person appears in. |
| `sex` | VARCHAR | Sex as published by the AR, M or F. Null without a RegistoBiografico record. |
| `birth_date` | DATE | Date of birth. Null without a RegistoBiografico record. |
| `profession` | VARCHAR | Profession. Null without a RegistoBiografico record. |
| `biography_legislature` | VARCHAR | Legislature of the RegistoBiografico record the biography fields come from, the latest one for the person. Real per-legislature biographies exist only for Constituinte, II and III; XVII is the current register. Null without a RegistoBiografico record. |

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

### stg_registo_biografico__biographies

RegistoBiografico, one row per person record, scalar fields only. II and III come from the older XML-shaped files listed on the AR I Legislatura page (camelCase keys), and Constituinte from the older RegistoBiograficoConstituinte.xml in the same shape. The other pages are older snapshots of the XVII register and are not stored, except I (335 people), so I rows are not that legislature's deputies (docs/known-gaps.md).

| Column | Type | Description |
|---|---|---|
| `cadastro_id` | BIGINT | Person id shared across legislatures and datasets (CadId). |
| `full_name` | VARCHAR | Full name (CadNomeCompleto). |
| `birth_date` | DATE | Date of birth (CadDtNascimento). |
| `sex` | VARCHAR | Sex as published by the AR, M or F (CadSexo). |
| `profession` | VARCHAR | Profession (CadProfissao). |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |
