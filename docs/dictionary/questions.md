# questions

One row per pergunta or requerimento a deputy sent to government or another public body.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `questions.parquet` and `questions.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals. |
| `question_id` | BIGINT | AR id of the question or request. |
| `question_type` | VARCHAR | Pergunta or Requerimento. |
| `recipient_category` | VARCHAR | Recipient category code, AC (central government), AL (local government), EI (independent and other public bodies), RA (autonomous regions) or AR (the Assembleia). |
| `number` | VARCHAR | Number within its type and session, as published. |
| `session_number` | INTEGER | Legislative session number. |
| `subject` | VARCHAR | Subject. |
| `entry_date` | DATE | Date it was registered. |
| `sent_date` | DATE | Date it was sent. Null when sent_date_invalid is true. |
| `sent_date_raw` | VARCHAR | Date it was sent (DataEnvio) exactly as published. |
| `sent_date_invalid` | BOOLEAN | True when the published date does not parse or its year is outside the years of the legislature (an open legislature runs to today), for example 2909 in X. |
| `document_url` | VARCHAR | Link to the question or request document. |
| `author_count` | BIGINT | Number of authors, one row each in question_authors. |
| `recipient_count` | BIGINT | Number of recipients, one row each in question_recipients. |
| `answer_count` | BIGINT | Answers received, per recipient plus those published on the question itself. |

## Known quirks

- Some published send dates are impossible, for example 2909-07-30 in X. The old mapper kept ISO dates as published. Here sent_date is null and sent_date_invalid is true, and sent_date_raw keeps the published text.
- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

Marts: [legislatures](legislatures.md).

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
