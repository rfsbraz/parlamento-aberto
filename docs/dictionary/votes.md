# votes

One row per vote id, from the Votacao arrays of Iniciativas events (plenary), of their Comissao entries (committee) and the VotacaoDebate arrays of Atividades (plenary). A vote on several initiatives voted together is published on each of them with the same content, so it is kept once.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `votes.parquet` and `votes.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `vote_id` | BIGINT | AR id of the vote. |
| `legislature` | VARCHAR | Legislature the vote date falls in. Can differ from the initiative's legislature. |
| `date` | DATE | Date of the vote. |
| `body` | VARCHAR | Where the vote was held, plenary or the committee name. Filter on plenary for plenary votes only. |
| `committee_id` | BIGINT | For a committee vote, the AR id of the committee; null for plenary votes. |
| `source` | VARCHAR | iniciativas or atividades. |
| `result` | VARCHAR | Result as published, for example Aprovado or Rejeitado. |
| `unanimous` | BOOLEAN | True when the AR marks the vote unanimous. |
| `meeting` | VARCHAR | Meeting number (of the plenary or of the committee). |
| `meeting_type` | VARCHAR | Meeting type code, RP for a plenary meeting. Null for committee votes. |
| `description` | VARCHAR | Description of what was voted. |
| `detail` | VARCHAR | Who voted which way, as published. Null when the AR gives no detail. |
| `absent_groups` | VARCHAR[] | Groups listed as absent, as published. |
| `source_records` | BIGINT | Number of source records with this vote id. |

## Known quirks

- A vote on several initiatives is published on each of them with the same content, so vote ids repeat in the source. The old mapper stored one row per event the vote was published on. Here it is one row per vote id, and initiative_votes links it to every initiative and event.
- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

Marts: [legislatures](legislatures.md), [initiatives](initiatives.md).

### stg_iniciativas__votes

One row per vote record (Votacao) in an initiative event. A vote on several initiatives appears once per initiative.

| Column | Type | Description |
|---|---|---|
| `vote_id` | BIGINT | AR id of the vote (id). |
| `initiative_id` | BIGINT | Initiative the record is published on. |
| `event_id` | BIGINT | Event the vote belongs to (EvtId). |
| `phase` | VARCHAR | Phase of that event (Fase), for example Votação na generalidade. |
| `phase_date` | DATE | Date of that event (DataFase). |
| `date` | DATE | Date of the vote (data). |
| `result` | VARCHAR | Result as published (resultado), for example Aprovado or Rejeitado. |
| `meeting` | VARCHAR | Meeting number (reuniao). |
| `meeting_type` | VARCHAR | Meeting type code (tipoReuniao), RP for a plenary meeting. |
| `unanimous` | BOOLEAN | True when the AR marks the vote unanimous (unanime), otherwise false. |
| `description` | VARCHAR | Description of what was voted (descricao). |
| `detail` | VARCHAR | Who voted which way (detalhe), null when absent or empty. |
| `absent_groups` | VARCHAR[] | Groups listed as absent (ausencias). |
| `legislature` | VARCHAR | Legislature of the initiative, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |

### stg_atividades__votes

One row per vote record (VotacaoDebate) on an activity in Atividades AtividadesGerais, such as a vote of condolence or a motion.

| Column | Type | Description |
|---|---|---|
| `vote_id` | BIGINT | AR id of the vote (id). |
| `activity_type` | VARCHAR | Activity type code (Tipo), for example VOT or MOC. |
| `activity_type_description` | VARCHAR | Activity type (DescTipo). |
| `activity_number` | VARCHAR | Activity number (Numero). |
| `activity_subject` | VARCHAR | Activity subject (Assunto). |
| `date` | DATE | Date of the vote (data). |
| `result` | VARCHAR | Result as published (resultado). |
| `meeting` | VARCHAR | Meeting number (reuniao). |
| `meeting_type` | VARCHAR | Meeting type code (tipoReuniao). |
| `unanimous` | BOOLEAN | True when the AR marks the vote unanimous (unanime), otherwise false. |
| `description` | VARCHAR | Description of what was voted (descricao). |
| `detail` | VARCHAR | Who voted which way (detalhe), null when absent or empty. |
| `absent_groups` | VARCHAR[] | Groups listed as absent (ausencias). |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |

### stg_iniciativas__committee_votes

One row per committee vote record (Votacao inside IniEventos[].Comissao[]).

| Column | Type | Description |
|---|---|---|
| `vote_id` | BIGINT | AR id of the vote (id). Committee vote ids do not overlap plenary ones. |
| `initiative_id` | BIGINT | Initiative the record is published on. |
| `event_id` | BIGINT | Event the committee entry belongs to (EvtId). |
| `phase` | VARCHAR | Phase of that event (Fase). |
| `phase_date` | DATE | Date of that event (DataFase). |
| `committee_id` | BIGINT | AR id of the committee (IdComissao), the same id as idOrgao in ComposicaoOrgaos. |
| `committee_name` | VARCHAR | Committee name (Nome), trimmed. |
| `date` | DATE | Date of the vote (data). |
| `result` | VARCHAR | Result as published (resultado). |
| `meeting` | VARCHAR | Committee meeting number (reuniao). |
| `unanimous` | BOOLEAN | True when the AR marks the vote unanimous (unanime), otherwise false. |
| `description` | VARCHAR | Description of what was voted (descricao), for example MAIORIA or ARTIGO A ARTIGO. |
| `detail` | VARCHAR | Who voted which way (detalhe), null when absent or empty. |
| `absent_groups` | VARCHAR[] | Groups listed as absent (ausencias). |
| `legislature` | VARCHAR | Legislature of the initiative, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |
