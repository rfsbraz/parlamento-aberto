# question_recipients

Uma linha por pergunta e organismo destinatário.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `question_recipients.parquet` e `question_recipients.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `question_id` | BIGINT | Id da pergunta na AR, liga a questions. |
| `recipient` | VARCHAR | Nome do organismo destinatário tal como publicado, por exemplo um ministério ou uma câmara municipal. |
| `sent_date` | DATE | Data de envio a este destinatário. |
| `is_extended` | BOOLEAN | Verdadeiro quando o prazo de resposta foi prorrogado. |
| `is_returned` | BOOLEAN | Verdadeiro quando o destinatário a devolveu. |
| `is_withdrawn` | BOOLEAN | Verdadeiro quando foi retirada. |
| `answer_count` | BIGINT | Respostas recebidas deste destinatário. |
| `first_answer_date` | DATE | Data da primeira resposta, nula se não houver nenhuma. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### stg_perguntas_requerimentos__questions

PerguntasRequerimentos, uma linha por registo da fonte. As contagens de linhas por legislatura batem com sources.lock.json.

| Coluna | Tipo | Descrição |
|---|---|---|
| `question_id` | BIGINT | Id da pergunta ou requerimento na AR (Id). |
| `question_type` | VARCHAR | Pergunta ou Requerimento (Tipo). |
| `recipient_category` | VARCHAR | Código da categoria do destinatário tal como publicado (ReqTipo). Pelos destinatários de cada código, AC é a administração central, AL a administração local, EI entidades independentes e outros organismos públicos, RA as regiões autónomas e AR a própria Assembleia. |
| `number` | VARCHAR | Número da pergunta ou requerimento dentro do seu tipo e sessão (Nr), tal como publicado. |
| `session_number` | INTEGER | Número da sessão legislativa (Sessao). |
| `subject` | VARCHAR | Assunto (Assunto). |
| `entry_date` | DATE | Data de registo (DtEntrada). |
| `sent_date_raw` | VARCHAR | Data de envio (DataEnvio), tal como publicada. Algumas são implausíveis, por exemplo o ano 0024 ou 2909; o mart questions assinala-as. |
| `document_url` | VARCHAR | Ligação para o documento da pergunta ou requerimento (Ficheiro). |
| `authors` | STRUCT(cadastro_id BIGINT, "name" VARCHAR, group_acronym VARCHAR)[] | Autores (Autores) como cadastro_id, name, group_acronym. |
| `recipients` | STRUCT(recipient VARCHAR, sent_date DATE, is_extended BOOLEAN, is_returned BOOLEAN, is_withdrawn BOOLEAN, answer_dates DATE[])[] | Destinatários (Destinatarios) como recipient, sent_date, is_extended, is_returned, is_withdrawn, answer_dates. |
| `question_level_answers` | BIGINT | Número de respostas publicadas na pergunta e não por destinatário (RespostasSPerguntas), usado em legislaturas mais antigas. |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
