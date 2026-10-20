# vote_deputy_dissents

Uma linha por deputado nomeado no detalhe de uma votação, normalmente por votar de forma diferente do seu grupo, ou nomeado como ausente no campo ausencias de uma votação sem detalhe. Associado ao cadastro_id pelo nome parlamentar (ignorando maiúsculas e espaços) e pelo grupo dentro da legislatura da votação, ou só pelo nome para Indep e Ninsc.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `vote_deputy_dissents.parquet` e `vote_deputy_dissents.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `vote_id` | BIGINT | Votação, liga a votes. |
| `legislature` | VARCHAR | Legislatura da votação. |
| `body` | VARCHAR | Onde decorreu a votação, plenary (plenário) ou o nome da comissão. |
| `position` | VARCHAR | favour, against, abstention ou absent (a favor, contra, abstenção ou ausente). |
| `name` | VARCHAR | Nome tal como escrito no detalhe. |
| `group_code` | VARCHAR | Código do grupo depois de seed_group_aliases. |
| `group_code_raw` | VARCHAR | Código do grupo tal como escrito no detalhe. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. Nulo quando nenhum deputado corresponde ou corresponde mais do que um. |
| `candidates` | INTEGER | Número de deputados que correspondem ao nome e ao grupo. 0 é sem correspondência, mais de 1 é ambíguo. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [deputies](deputies.md), [votes](votes.md).

### stg_informacao_base__deputies

InformacaoBase Deputados, uma linha por pessoa nas listas de uma legislatura, eleita ou não.

| Coluna | Tipo | Descrição |
|---|---|---|
| `cadastro_id` | BIGINT | Id da pessoa, comum a todas as legislaturas e conjuntos de dados (DepCadId). |
| `deputy_id` | BIGINT | Id desta pessoa nesta legislatura (DepId). |
| `full_name` | VARCHAR | Nome completo (DepNomeCompleto). |
| `parliamentary_name` | VARCHAR | Nome usado no parlamento (DepNomeParlamentar). |
| `circle_id` | INTEGER | Círculo eleitoral por onde a pessoa concorreu (DepCPId). |
| `circle_name` | VARCHAR | Nome desse círculo eleitoral (DepCPDes). |
| `situations` | STRUCT(situation VARCHAR, start_date DATE, end_date DATE)[] | Períodos de situação (DepSituacao) como situation, start_date, end_date. |
| `groups` | STRUCT(group_id BIGINT, group_acronym VARCHAR, start_date DATE, end_date DATE)[] | Filiações em grupos (DepGP) como group_id, group_acronym, start_date, end_date. |
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
