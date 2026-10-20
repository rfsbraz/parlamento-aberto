# legislatures

Uma linha por legislatura.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `legislatures.parquet` e `legislatures.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana, por exemplo XVII. |
| `legislature_id` | INTEGER | Id interno da legislatura na AR. |
| `start_date` | DATE | Primeiro dia da legislatura. |
| `end_date` | DATE | Último dia da legislatura, nulo enquanto está em curso. |
| `extract_date` | DATE | Data da extração da AR, tirada da data de fim que a AR escreve nas filiações em grupos ainda abertas. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### stg_informacao_base__legislatures

InformacaoBase DetalheLegislatura, uma linha por ficheiro de legislatura.

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature_id` | INTEGER | Id interno da legislatura na AR (id). |
| `start_date` | DATE | Primeiro dia da legislatura (dtini). |
| `end_date` | DATE | Último dia da legislatura (dtfim), nulo enquanto está em curso. |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |

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
