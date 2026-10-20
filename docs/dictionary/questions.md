# questions

Uma linha por pergunta ou requerimento que um deputado enviou ao Governo ou a outro organismo público.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `questions.parquet` e `questions.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `question_id` | BIGINT | Id da pergunta ou requerimento na AR. |
| `question_type` | VARCHAR | Pergunta ou Requerimento. |
| `recipient_category` | VARCHAR | Código da categoria do destinatário, AC (administração central), AL (administração local), EI (entidades independentes e outros organismos públicos), RA (regiões autónomas) ou AR (a Assembleia). |
| `number` | VARCHAR | Número dentro do seu tipo e sessão, tal como publicado. |
| `session_number` | INTEGER | Número da sessão legislativa. |
| `subject` | VARCHAR | Assunto. |
| `entry_date` | DATE | Data de registo. |
| `sent_date` | DATE | Data de envio. Nulo quando sent_date_invalid é verdadeiro. |
| `sent_date_raw` | VARCHAR | Data de envio (DataEnvio) exatamente como publicada. |
| `sent_date_invalid` | BOOLEAN | Verdadeiro quando a data publicada não se lê ou o seu ano fica fora dos anos da legislatura (uma legislatura em curso vai até hoje), por exemplo 2909 na X. |
| `document_url` | VARCHAR | Ligação para o documento da pergunta ou requerimento. |
| `author_count` | BIGINT | Número de autores, uma linha cada em question_authors. |
| `recipient_count` | BIGINT | Número de destinatários, uma linha cada em question_recipients. |
| `answer_count` | BIGINT | Respostas recebidas, por destinatário, mais as publicadas na própria pergunta. |

## Particularidades conhecidas

- Algumas datas de envio publicadas são impossíveis, por exemplo 2909-07-30 na X. O mapeador antigo guardava as datas ISO tal como publicadas. Aqui sent_date é nulo, sent_date_invalid é verdadeiro e sent_date_raw guarda o texto publicado.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [legislatures](legislatures.md).

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
