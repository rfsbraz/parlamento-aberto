# initiative_votes

Liga as votações em plenário e em comissão às iniciativas e eventos em que são publicadas.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `initiative_votes.parquet` e `initiative_votes.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `vote_id` | BIGINT | Votação, liga a votes. |
| `initiative_id` | BIGINT | Iniciativa, liga a initiatives. |
| `initiative_legislature` | VARCHAR | Legislatura da iniciativa. |
| `body` | VARCHAR | Onde decorreu a votação, plenary (plenário) ou o nome da comissão. |
| `event_id` | BIGINT | Evento da iniciativa que contém a votação. |
| `phase` | VARCHAR | Fase desse evento, por exemplo Votação na generalidade. |
| `phase_date` | DATE | Data desse evento. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [votes](votes.md).

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
