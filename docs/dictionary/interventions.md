# interventions

Uma linha por intervenção em plenário, com debate, orador e referência no Diário. O orador é um deputado (cadastro_id), um membro do Governo ou um convidado. Os registos que a AR publica com todas as chaves a nulo são excluídos.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `interventions.parquet` e `interventions.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `intervention_id` | BIGINT | Id da intervenção na AR. |
| `session_number` | INTEGER | Número da sessão legislativa. |
| `meeting_date` | DATE | Data da reunião plenária. |
| `intervention_type` | VARCHAR | Tipo de intervenção tal como publicado, por exemplo Intervenção ou Pedido de esclarecimento. |
| `session_phase` | VARCHAR | Parte da sessão tal como publicada, POD (ordem do dia), PAOD (antes da ordem do dia) ou Outras. |
| `debate_id` | BIGINT | Id do debate na AR. |
| `debate` | VARCHAR | Título do debate, muitas vezes nulo. |
| `debate_phase` | VARCHAR | Fase do debate tal como publicada, por exemplo GENERALIDADE, muitas vezes nula. |
| `activity_id` | BIGINT | Id na AR da atividade parlamentar a que a intervenção pertence. |
| `summary` | VARCHAR | Sumário da intervenção. |
| `abstract` | VARCHAR | Resumo mais longo, muitas vezes nulo. |
| `speaker_kind` | VARCHAR | deputy (deputado) quando cadastro_id está preenchido, senão government (Governo) quando é indicado um membro do Governo, senão guest (convidado) quando é indicado um convidado, senão nulo. |
| `cadastro_id` | BIGINT | Id da pessoa do deputado que falou, liga a deputies. Nulo quando quem falou não é deputado. |
| `speaker_name` | VARCHAR | Nome parlamentar do deputado tal como publicado na intervenção. |
| `group_acronym` | VARCHAR | Grupo do deputado quando falou, liga a parliamentary_groups. |
| `speaker_role` | VARCHAR | Qualidade em que a pessoa falou, tal como publicada, por exemplo Deputado, P.A.R. ou Sec. Mesa. |
| `government_member_name` | VARCHAR | Nome do membro do Governo que falou. |
| `government_member_role` | VARCHAR | Cargo do membro do Governo. |
| `government` | VARCHAR | Governo a que o membro pertencia. |
| `guest_name` | VARCHAR | Nome de um orador convidado. |
| `guest_role` | VARCHAR | Cargo do orador convidado. |
| `publication_type` | VARCHAR | Série do Diário, por exemplo DAR I série. |
| `publication_number` | INTEGER | Número do Diário. |
| `publication_date` | DATE | Data do Diário. |
| `pages` | VARCHAR[] | Páginas do Diário tal como publicadas, texto com zeros à esquerda. |
| `diary_url` | VARCHAR | Ligação para o número do Diário. |

## Particularidades conhecidas

- A AR publica alguns registos de Intervencoes com todas as chaves a nulo. São excluídos aqui, pelo que as contagens de linhas ficam abaixo das contagens de registos em sources.lock.json, com as quais o modelo de staging bate.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### stg_intervencoes__interventions

Intervencoes, uma linha por registo da fonte, incluindo os registos que a AR publica com todas as chaves a nulo. As contagens de linhas por legislatura batem com sources.lock.json.

| Coluna | Tipo | Descrição |
|---|---|---|
| `intervention_id` | BIGINT | Id da intervenção na AR (Id). Nulo nos registos vazios. |
| `session_number` | INTEGER | Número da sessão legislativa (Sessao). |
| `meeting_date` | DATE | Data da reunião plenária (DataReuniaoPlenaria). |
| `intervention_type` | VARCHAR | Tipo de intervenção tal como publicado (TipoIntervencao), por exemplo Intervenção ou Pedido de esclarecimento. |
| `session_phase` | VARCHAR | Parte da sessão tal como publicada (FaseSessao), POD (ordem do dia), PAOD (antes da ordem do dia) ou Outras. |
| `debate_id` | BIGINT | Id do debate na AR (IdDebate). |
| `debate` | VARCHAR | Título do debate (Debate), muitas vezes nulo. |
| `debate_phase` | VARCHAR | Fase do debate tal como publicada (FaseDebate), por exemplo GENERALIDADE, muitas vezes nula. |
| `activity_id` | BIGINT | Id na AR da atividade parlamentar a que a intervenção pertence (ActividadeId). |
| `summary` | VARCHAR | Sumário da intervenção (Sumario). |
| `abstract` | VARCHAR | Resumo mais longo (Resumo), muitas vezes nulo. |
| `cadastro_id` | BIGINT | Id da pessoa do deputado que falou (Deputados.idCadastro), nulo quando quem falou não é deputado. |
| `speaker_name` | VARCHAR | Nome parlamentar do deputado (Deputados.nome). |
| `group_acronym` | VARCHAR | Grupo do deputado quando falou (Deputados.GP). |
| `speaker_role` | VARCHAR | Qualidade em que a pessoa falou, tal como publicada (Qualidade), por exemplo Deputado, P.A.R. ou Sec. Mesa. |
| `government_member_name` | VARCHAR | Nome do membro do Governo que falou (MembrosGoverno.nome). |
| `government_member_role` | VARCHAR | Cargo do membro do Governo (MembrosGoverno.cargo). |
| `government` | VARCHAR | Governo a que o membro pertencia (MembrosGoverno.governo). |
| `guest_name` | VARCHAR | Nome de um orador convidado (Convidados.nome). |
| `guest_role` | VARCHAR | Cargo do orador convidado (Convidados.cargo). |
| `publication_count` | BIGINT | Número de referências de publicação (Publicacao); 1 em todos os registos até agora. |
| `publication_type` | VARCHAR | Série do Diário da publicação (Publicacao.pubTipo), por exemplo DAR I série. |
| `publication_number` | INTEGER | Número do Diário (Publicacao.pubNr). |
| `publication_date` | DATE | Data do Diário (Publicacao.pubdt). |
| `pages` | VARCHAR[] | Páginas do Diário tal como publicadas (Publicacao.pag), texto com zeros à esquerda. |
| `diary_url` | VARCHAR | Ligação para o número do Diário (Publicacao.URLDiario). |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
