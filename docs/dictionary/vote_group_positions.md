# vote_group_positions

Uma linha por votação, grupo e sentido de voto, a partir do detalhe lido. As votações sem detalhe tiram os grupos e deputados ausentes do campo ausencias. Uma votação unânime que não indica nenhum sentido a favor, contra ou abstenção recebe uma linha a favor, com inferred = true, para cada outro grupo presente: numa votação em plenário, os grupos com um deputado com lugar na data da votação (a regra seated_on); numa votação em comissão, os grupos com um membro efetivo ativo da comissão na data da votação, segundo a ComposicaoOrgaos.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `vote_group_positions.parquet` e `vote_group_positions.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `vote_id` | BIGINT | Votação, liga a votes. |
| `legislature` | VARCHAR | Legislatura da votação. |
| `body` | VARCHAR | Onde decorreu a votação, plenary (plenário) ou o nome da comissão. |
| `group_code` | VARCHAR | Código do grupo depois de seed_group_aliases, liga a parliamentary_groups.group_acronym. Indep e Ninsc marcam deputados fora de qualquer grupo. |
| `group_code_raw` | VARCHAR | Código do grupo tal como publicado (ou, nas linhas inferidas, como na filiação do deputado na InformacaoBase). |
| `position` | VARCHAR | favour, against, abstention ou absent (a favor, contra, abstenção ou ausente). |
| `deputies` | INTEGER | Nulo quando o grupo como um todo tomou esse sentido de voto (exceto deputados seus indicados noutro sentido). Caso contrário, o número dos seus deputados que o tomaram. |
| `inferred` | BOOLEAN | Verdadeiro quando a linha vem da regra da unanimidade e não do detalhe publicado. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [deputies](deputies.md), [mandates](mandates.md), [group_memberships](group_memberships.md), [votes](votes.md).

### stg_composicao_orgaos__committee_members

ComposicaoOrgaos Comissoes, uma linha por registo de membro de uma comissão (HistoricoComposicao).

| Coluna | Tipo | Descrição |
|---|---|---|
| `committee_id` | BIGINT | Id da comissão na AR (DetalheOrgao.idOrgao). |
| `committee_name` | VARCHAR | Nome da comissão (DetalheOrgao.nomeSigla), sem espaços nas pontas. |
| `cadastro_id` | BIGINT | Id da pessoa (depCadId), liga a deputies. |
| `situations` | STRUCT(status VARCHAR, membership VARCHAR, start_date DATE, end_date DATE)[] | Períodos como membro (depSituacao) como status (sioDes, Ativo ou Inativo), membership (sioTipMem, Efetivo ou Suplente), start_date, end_date. |
| `groups` | STRUCT(group_acronym VARCHAR, start_date DATE, end_date DATE)[] | Períodos em grupos (depGP) como group_acronym, start_date, end_date. Um período aberto tem data de fim nula. |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |

### stg_votes__detail_items

Construído em Python pelo parser das votações. Uma linha por item em cada texto de detalhe distinto, ou uma linha com um erro quando o parser rejeita o texto.

| Coluna | Tipo | Descrição |
|---|---|---|
| `detail` | VARCHAR | O texto do detalhe, liga à coluna detail dos modelos de votações. |
| `item_number` | INTEGER | Posição do item no texto, a partir de 1. 0 numa linha de erro. |
| `kind` | VARCHAR | group (um grupo inteiro), count (um número de deputados de um grupo, como em 2-PS) ou deputy (um deputado nomeado). |
| `group_acronym` | VARCHAR | Código do grupo tal como escrito no texto. |
| `position` | VARCHAR | favour, against, abstention ou absent (a favor, contra, abstenção ou ausente). |
| `deputies` | INTEGER | Num item count, o número de deputados. |
| `name` | VARCHAR | Num item deputy, o nome tal como escrito no texto. |
| `error` | VARCHAR | Porque é que o parser rejeitou o texto, nulo quando foi lido. |

### seed_group_aliases

Aliases mantidos à mão para códigos de grupo que a AR escreve de forma diferente dentro de uma legislatura, cada linha com a sua fonte. Os marts guardam o código publicado em group_code_raw e põem em group_code o código do alias, ou o publicado quando não se aplica nenhum alias.

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana (o nome da pasta de dados, por exemplo I-B) a que o alias se aplica. |
| `alias` | VARCHAR | Código tal como publicado, por exemplo PPD. |
| `group_code` | VARCHAR | Código correspondente, como listado em parliamentary_groups nessa legislatura. |
| `source_url` | VARCHAR | Referência para a correspondência. |
| `note` | VARCHAR | Porque existe o alias. |
