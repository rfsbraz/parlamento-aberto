# interventions

One row per intervention in plenary, with debate, speaker and diary reference. The speaker is a deputy (cadastro_id), a government member or an invited guest. Records AR publishes with every key null are dropped.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `interventions.parquet` and `interventions.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals. |
| `intervention_id` | BIGINT | AR id of the intervention. |
| `session_number` | INTEGER | Legislative session number. |
| `meeting_date` | DATE | Date of the plenary meeting. |
| `intervention_type` | VARCHAR | Type of intervention as published, for example Intervenção or Pedido de esclarecimento. |
| `session_phase` | VARCHAR | Part of the sitting as published, POD (ordem do dia), PAOD (antes da ordem do dia) or Outras. |
| `debate_id` | BIGINT | AR id of the debate. |
| `debate` | VARCHAR | Debate title, often null. |
| `debate_phase` | VARCHAR | Phase of the debate as published, for example GENERALIDADE, often null. |
| `activity_id` | BIGINT | AR id of the parliamentary activity the intervention belongs to. |
| `summary` | VARCHAR | Summary of the intervention. |
| `abstract` | VARCHAR | Longer abstract, often null. |
| `speaker_kind` | VARCHAR | deputy when cadastro_id is set, otherwise government when a government member is named, otherwise guest when a guest is named, otherwise null. |
| `cadastro_id` | BIGINT | Person id of the deputy who spoke, joins to deputies. Null when the speaker is not a deputy. |
| `speaker_name` | VARCHAR | Parliamentary name of the deputy as published on the intervention. |
| `group_acronym` | VARCHAR | Group of the deputy when speaking, joins to parliamentary_groups. |
| `speaker_role` | VARCHAR | Capacity the person spoke in as published, for example Deputado, P.A.R. or Sec. Mesa. |
| `government_member_name` | VARCHAR | Name of the government member who spoke. |
| `government_member_role` | VARCHAR | Office of the government member. |
| `government` | VARCHAR | Government the member belonged to. |
| `guest_name` | VARCHAR | Name of an invited speaker. |
| `guest_role` | VARCHAR | Office of the invited speaker. |
| `publication_type` | VARCHAR | Diary series, for example DAR I série. |
| `publication_number` | INTEGER | Diary issue number. |
| `publication_date` | DATE | Diary issue date. |
| `pages` | VARCHAR[] | Diary pages as published, zero-padded strings. |
| `diary_url` | VARCHAR | Link to the diary issue. |

## Known quirks

- AR publishes some Intervencoes records with every key null. They are dropped here, so row counts are below the record counts in sources.lock.json, which the staging model matches.
- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

### stg_intervencoes__interventions

Intervencoes, one row per source record, including the records AR publishes with every key null. Row counts per legislature match sources.lock.json.

| Column | Type | Description |
|---|---|---|
| `intervention_id` | BIGINT | AR id of the intervention (Id). Null on the empty records. |
| `session_number` | INTEGER | Legislative session number (Sessao). |
| `meeting_date` | DATE | Date of the plenary meeting (DataReuniaoPlenaria). |
| `intervention_type` | VARCHAR | Type of intervention as published (TipoIntervencao), for example Intervenção or Pedido de esclarecimento. |
| `session_phase` | VARCHAR | Part of the sitting as published (FaseSessao), POD (ordem do dia), PAOD (antes da ordem do dia) or Outras. |
| `debate_id` | BIGINT | AR id of the debate (IdDebate). |
| `debate` | VARCHAR | Debate title (Debate), often null. |
| `debate_phase` | VARCHAR | Phase of the debate as published (FaseDebate), for example GENERALIDADE, often null. |
| `activity_id` | BIGINT | AR id of the parliamentary activity the intervention belongs to (ActividadeId). |
| `summary` | VARCHAR | Summary of the intervention (Sumario). |
| `abstract` | VARCHAR | Longer abstract (Resumo), often null. |
| `cadastro_id` | BIGINT | Person id of the deputy who spoke (Deputados.idCadastro), null when the speaker is not a deputy. |
| `speaker_name` | VARCHAR | Parliamentary name of the deputy (Deputados.nome). |
| `group_acronym` | VARCHAR | Group of the deputy when speaking (Deputados.GP). |
| `speaker_role` | VARCHAR | Capacity the person spoke in as published (Qualidade), for example Deputado, P.A.R. or Sec. Mesa. |
| `government_member_name` | VARCHAR | Name of the government member who spoke (MembrosGoverno.nome). |
| `government_member_role` | VARCHAR | Office of the government member (MembrosGoverno.cargo). |
| `government` | VARCHAR | Government the member belonged to (MembrosGoverno.governo). |
| `guest_name` | VARCHAR | Name of an invited speaker (Convidados.nome). |
| `guest_role` | VARCHAR | Office of the invited speaker (Convidados.cargo). |
| `publication_count` | BIGINT | Number of publication references (Publicacao); 1 on every record so far. |
| `publication_type` | VARCHAR | Diary series of the publication (Publicacao.pubTipo), for example DAR I série. |
| `publication_number` | INTEGER | Diary issue number (Publicacao.pubNr). |
| `publication_date` | DATE | Diary issue date (Publicacao.pubdt). |
| `pages` | VARCHAR[] | Diary pages as published (Publicacao.pag), zero-padded strings. |
| `diary_url` | VARCHAR | Link to the diary issue (Publicacao.URLDiario). |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |
