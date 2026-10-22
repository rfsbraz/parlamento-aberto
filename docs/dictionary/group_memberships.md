# group_memberships

Uma linha por deputado, legislatura e período num grupo parlamentar (DepGP).

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `group_memberships.parquet` e `group_memberships.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. |
| `group_id` | BIGINT | Id do grupo na AR nesta legislatura (gpId). |
| `group_acronym` | VARCHAR | Sigla do grupo, liga a parliamentary_groups. |
| `start_date` | DATE | Primeiro dia no grupo. |
| `end_date` | DATE | Último dia no grupo, nulo enquanto a filiação está aberta. |
| `is_open` | BOOLEAN | Verdadeiro quando a legislatura está em curso e a data de fim da AR é igual ou posterior à data da extração. |

## Particularidades conhecidas

- A AR escreve a data da extração como data de fim de uma filiação aberta. O mapeador antigo guardava essa data tal como publicada, pelo que as filiações abertas pareciam fechadas. Aqui uma filiação aberta tem end_date nulo e is_open = true.
- Como em mandates, a I-A e a I-B partilham uma só lista publicada pela AR. Cada parte fica só com os períodos num grupo que se sobrepõem às suas datas em legislatures, com as datas tal como publicadas.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [legislatures](legislatures.md), [deputies](deputies.md), [mandates](mandates.md).

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
