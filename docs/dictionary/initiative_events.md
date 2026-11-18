# initiative_events

Uma linha por evento (fase) de uma iniciativa, a partir de IniEventos, com a ordem dos eventos dentro da iniciativa. Para saber a fase atual, use o evento com o maior event_order. Para o desfecho, junte phase_code a phase_codes.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `initiative_events.parquet` e `initiative_events.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura da iniciativa. |
| `initiative_id` | BIGINT | Iniciativa, liga a initiatives. |
| `event_id` | BIGINT | Id do evento dentro da iniciativa (EvtId), como em initiative_votes. Não é único. |
| `oev_id` | BIGINT | Id único do evento na AR (OevId). |
| `phase_code` | VARCHAR | Código da fase (CodigoFase), liga a phase_codes. Nulo quando a AR não o publica. |
| `phase` | VARCHAR | Nome da fase (Fase), sem espaços nem quebras de linha no fim, por exemplo Votação na generalidade. |
| `phase_date` | DATE | Data da fase (DataFase). |
| `event_order` | BIGINT | Posição do evento na iniciativa, a partir de 1, por phase_date e depois por oev_id. |
| `observation` | VARCHAR | Observação da fase (ObsFase) tal como publicada, nula quando não há. |

## Particularidades conhecidas

- O último evento não chega para saber o desfecho: uma iniciativa rejeitada fica normalmente em Votação na generalidade. O desfecho é a categoria em phase_codes da última fase final da iniciativa (Lei ou Resolução publicada no Diário da República, Caducada, Retirada, Prejudicada) e, quando não há nenhuma, uma votação em plenário com result Rejeitado em votes, ligada por initiative_votes a um evento de votação da própria iniciativa (phase_code 250, 315, 320, 330 ou 335). Votações de recursos, requerimentos ou em comissão não contam. Com esta regra há desfecho para 97% a 99,8% das iniciativas da VII à XVI, 89,5% na VI, 62% na XVII (em curso) e só 22% a 60% da I-A à V, segundo os dados de 9 de novembro de 2026.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### stg_iniciativas__initiatives

Iniciativas, uma linha por registo de iniciativa.

| Coluna | Tipo | Descrição |
|---|---|---|
| `initiative_id` | BIGINT | Id da iniciativa na AR (IniId). |
| `number` | INTEGER | Número da iniciativa dentro do seu tipo e legislatura (IniNr). |
| `type_code` | VARCHAR | Código do tipo de iniciativa (IniTipo), por exemplo J. |
| `type` | VARCHAR | Tipo de iniciativa (IniDescTipo), por exemplo Projeto de Lei. |
| `session_number` | INTEGER | Sessão legislativa em que a iniciativa deu entrada (IniSel). |
| `title` | VARCHAR | Título (IniTitulo). |
| `text_url` | VARCHAR | Ligação para o texto da iniciativa (IniLinkTexto). |
| `author_kind_code` | VARCHAR | Código do tipo de autor (IniAutorOutros.sigla), por exemplo D, G ou V. |
| `author_kind` | VARCHAR | Tipo de autor (IniAutorOutros.nome), por exemplo Deputados, Grupos Parlamentares ou Governo. |
| `author_committee` | VARCHAR | Comissão autora da iniciativa, quando o autor é uma comissão (IniAutorOutros.iniAutorComissao). |
| `author_deputies` | STRUCT(cadastro_id BIGINT, "name" VARCHAR, group_acronym VARCHAR)[] | Deputados autores (IniAutorDeputados) como cadastro_id, name, group_acronym. |
| `author_groups` | VARCHAR[] | Grupos autores (IniAutorGruposParlamentares) como siglas de grupos. |
| `events` | STRUCT(event_id BIGINT, oev_id BIGINT, phase_code VARCHAR, phase VARCHAR, phase_date DATE, observation VARCHAR, votes STRUCT(id VARCHAR, "data" VARCHAR, resultado VARCHAR, reuniao VARCHAR, tipoReuniao VARCHAR, unanime VARCHAR, descricao VARCHAR, detalhe VARCHAR, ausencias VARCHAR[])[], committees STRUCT(committee_id BIGINT, committee_name VARCHAR, votes STRUCT(id VARCHAR, "data" VARCHAR, resultado VARCHAR, reuniao VARCHAR, unanime VARCHAR, descricao VARCHAR, detalhe VARCHAR, ausencias VARCHAR[])[])[])[] | Eventos (IniEventos) como event_id, oev_id, phase_code, phase, phase_date, observation, as votações em plenário em bruto (Votacao) e as comissões (Comissao) como committee_id, committee_name e as suas votações em bruto. |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
