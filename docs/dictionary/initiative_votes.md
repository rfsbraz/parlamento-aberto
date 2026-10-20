# initiative_votes

Links plenary and committee votes to the initiatives and events they are published on.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `initiative_votes.parquet` and `initiative_votes.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `vote_id` | BIGINT | Vote, joins to votes. |
| `initiative_id` | BIGINT | Initiative, joins to initiatives. |
| `initiative_legislature` | VARCHAR | Legislature of the initiative. |
| `body` | VARCHAR | Where the vote was held, plenary or the committee name. |
| `event_id` | BIGINT | Event on the initiative that carries the vote. |
| `phase` | VARCHAR | Phase of that event, for example Votação na generalidade. |
| `phase_date` | DATE | Date of that event. |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

Marts: [votes](votes.md).

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
