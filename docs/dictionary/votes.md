# votes

Uma linha por id de votação, a partir dos arrays Votacao dos eventos das Iniciativas (plenário), das suas entradas Comissao (comissão) e dos arrays VotacaoDebate das Atividades (plenário). Uma votação sobre várias iniciativas votadas em conjunto é publicada em cada uma delas com o mesmo conteúdo, pelo que é guardada uma só vez.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `votes.parquet` e `votes.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `vote_id` | BIGINT | Id da votação na AR. |
| `legislature` | VARCHAR | Legislatura em que cai a data da votação. Pode ser diferente da legislatura da iniciativa. |
| `date` | DATE | Data da votação. |
| `body` | VARCHAR | Onde decorreu a votação, plenary (plenário) ou o nome da comissão. Filtre por plenary para ter só votações em plenário. |
| `committee_id` | BIGINT | Numa votação em comissão, o id da comissão na AR; nulo nas votações em plenário. |
| `source` | VARCHAR | iniciativas ou atividades. |
| `result` | VARCHAR | Resultado tal como publicado, por exemplo Aprovado ou Rejeitado. |
| `unanimous` | BOOLEAN | Verdadeiro quando a AR marca a votação como unânime. |
| `meeting` | VARCHAR | Número da reunião (do plenário ou da comissão). |
| `meeting_type` | VARCHAR | Código do tipo de reunião, RP para uma reunião plenária. Nulo nas votações em comissão. |
| `description` | VARCHAR | Descrição do que foi votado. |
| `detail` | VARCHAR | Quem votou em que sentido, tal como publicado. Nulo quando a AR não dá detalhe. |
| `absent_groups` | VARCHAR[] | Grupos indicados como ausentes, tal como publicado. |
| `source_records` | BIGINT | Número de registos da fonte com este id de votação. |

## Particularidades conhecidas

- Uma votação sobre várias iniciativas é publicada em cada uma delas com o mesmo conteúdo, pelo que os ids de votação se repetem na fonte. O mapeador antigo guardava uma linha por cada evento em que a votação era publicada. Aqui há uma linha por id de votação, e initiative_votes liga-a a todas as iniciativas e eventos.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [legislatures](legislatures.md), [initiatives](initiatives.md).

### stg_iniciativas__votes

Uma linha por registo de votação (Votacao) num evento de uma iniciativa. Uma votação sobre várias iniciativas aparece uma vez por iniciativa.

| Coluna | Tipo | Descrição |
|---|---|---|
| `vote_id` | BIGINT | Id da votação na AR (id). |
| `initiative_id` | BIGINT | Iniciativa em que o registo é publicado. |
| `event_id` | BIGINT | Evento a que a votação pertence (EvtId). |
| `phase` | VARCHAR | Fase desse evento (Fase), por exemplo Votação na generalidade. |
| `phase_date` | DATE | Data desse evento (DataFase). |
| `date` | DATE | Data da votação (data). |
| `result` | VARCHAR | Resultado tal como publicado (resultado), por exemplo Aprovado ou Rejeitado. |
| `meeting` | VARCHAR | Número da reunião (reuniao). |
| `meeting_type` | VARCHAR | Código do tipo de reunião (tipoReuniao), RP para uma reunião plenária. |
| `unanimous` | BOOLEAN | Verdadeiro quando a AR marca a votação como unânime (unanime), senão falso. |
| `description` | VARCHAR | Descrição do que foi votado (descricao). |
| `detail` | VARCHAR | Quem votou em que sentido (detalhe), nulo quando ausente ou vazio. |
| `absent_groups` | VARCHAR[] | Grupos indicados como ausentes (ausencias). |
| `legislature` | VARCHAR | Legislatura da iniciativa, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |

### stg_atividades__votes

Uma linha por registo de votação (VotacaoDebate) numa atividade em Atividades AtividadesGerais, como um voto de pesar ou uma moção.

| Coluna | Tipo | Descrição |
|---|---|---|
| `vote_id` | BIGINT | Id da votação na AR (id). |
| `activity_type` | VARCHAR | Código do tipo de atividade (Tipo), por exemplo VOT ou MOC. |
| `activity_type_description` | VARCHAR | Tipo de atividade (DescTipo). |
| `activity_number` | VARCHAR | Número da atividade (Numero). |
| `activity_subject` | VARCHAR | Assunto da atividade (Assunto). |
| `date` | DATE | Data da votação (data). |
| `result` | VARCHAR | Resultado tal como publicado (resultado). |
| `meeting` | VARCHAR | Número da reunião (reuniao). |
| `meeting_type` | VARCHAR | Código do tipo de reunião (tipoReuniao). |
| `unanimous` | BOOLEAN | Verdadeiro quando a AR marca a votação como unânime (unanime), senão falso. |
| `description` | VARCHAR | Descrição do que foi votado (descricao). |
| `detail` | VARCHAR | Quem votou em que sentido (detalhe), nulo quando ausente ou vazio. |
| `absent_groups` | VARCHAR[] | Grupos indicados como ausentes (ausencias). |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |

### stg_iniciativas__committee_votes

Uma linha por registo de votação em comissão (Votacao dentro de IniEventos[].Comissao[]).

| Coluna | Tipo | Descrição |
|---|---|---|
| `vote_id` | BIGINT | Id da votação na AR (id). Os ids das votações em comissão não se sobrepõem aos do plenário. |
| `initiative_id` | BIGINT | Iniciativa em que o registo é publicado. |
| `event_id` | BIGINT | Evento a que pertence a entrada da comissão (EvtId). |
| `phase` | VARCHAR | Fase desse evento (Fase). |
| `phase_date` | DATE | Data desse evento (DataFase). |
| `committee_id` | BIGINT | Id da comissão na AR (IdComissao), o mesmo id que idOrgao em ComposicaoOrgaos. |
| `committee_name` | VARCHAR | Nome da comissão (Nome), sem espaços nas pontas. |
| `date` | DATE | Data da votação (data). |
| `result` | VARCHAR | Resultado tal como publicado (resultado). |
| `meeting` | VARCHAR | Número da reunião da comissão (reuniao). |
| `unanimous` | BOOLEAN | Verdadeiro quando a AR marca a votação como unânime (unanime), senão falso. |
| `description` | VARCHAR | Descrição do que foi votado (descricao), por exemplo MAIORIA ou ARTIGO A ARTIGO. |
| `detail` | VARCHAR | Quem votou em que sentido (detalhe), nulo quando ausente ou vazio. |
| `absent_groups` | VARCHAR[] | Grupos indicados como ausentes (ausencias). |
| `legislature` | VARCHAR | Legislatura da iniciativa, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
