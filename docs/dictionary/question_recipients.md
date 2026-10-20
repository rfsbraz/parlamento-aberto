# question_recipients

One row per question and recipient body.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `question_recipients.parquet` and `question_recipients.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals. |
| `question_id` | BIGINT | AR id of the question, joins to questions. |
| `recipient` | VARCHAR | Name of the recipient body as published, for example a ministry or a câmara municipal. |
| `sent_date` | DATE | Date it was sent to this recipient. |
| `is_extended` | BOOLEAN | True when the answer deadline was extended (prorrogado). |
| `is_returned` | BOOLEAN | True when the recipient returned it (devolvido). |
| `is_withdrawn` | BOOLEAN | True when it was withdrawn (retirado). |
| `answer_count` | BIGINT | Answers received from this recipient. |
| `first_answer_date` | DATE | Date of the first answer, null without one. |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

### stg_perguntas_requerimentos__questions

PerguntasRequerimentos, one row per source record. Row counts per legislature match sources.lock.json.

| Column | Type | Description |
|---|---|---|
| `question_id` | BIGINT | AR id of the question or request (Id). |
| `question_type` | VARCHAR | Pergunta or Requerimento (Tipo). |
| `recipient_category` | VARCHAR | Recipient category code as published (ReqTipo). From the recipients under each code, AC is central government, AL local government, EI independent and other public bodies, RA the autonomous regions and AR the Assembleia itself. |
| `number` | VARCHAR | Number of the question or request within its type and session (Nr), as published. |
| `session_number` | INTEGER | Legislative session number (Sessao). |
| `subject` | VARCHAR | Subject (Assunto). |
| `entry_date` | DATE | Date it was registered (DtEntrada). |
| `sent_date_raw` | VARCHAR | Date it was sent (DataEnvio), as published. A few are implausible, for example year 0024 or 2909; the questions mart flags them. |
| `document_url` | VARCHAR | Link to the question or request document (Ficheiro). |
| `authors` | STRUCT(cadastro_id BIGINT, "name" VARCHAR, group_acronym VARCHAR)[] | Authors (Autores) as cadastro_id, name, group_acronym. |
| `recipients` | STRUCT(recipient VARCHAR, sent_date DATE, is_extended BOOLEAN, is_returned BOOLEAN, is_withdrawn BOOLEAN, answer_dates DATE[])[] | Recipients (Destinatarios) as recipient, sent_date, is_extended, is_returned, is_withdrawn, answer_dates. |
| `question_level_answers` | BIGINT | Number of answers published on the question rather than per recipient (RespostasSPerguntas), used in older legislatures. |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |
