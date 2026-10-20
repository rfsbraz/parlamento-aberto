# electoral_circles

Uma linha por círculo eleitoral e por legislatura.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `electoral_circles.parquet` e `electoral_circles.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `circle_id` | INTEGER | Id do círculo eleitoral na AR. |
| `name` | VARCHAR | Nome do círculo eleitoral. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### stg_informacao_base__electoral_circles

InformacaoBase CirculosEleitorais, uma linha por círculo eleitoral.

| Coluna | Tipo | Descrição |
|---|---|---|
| `circle_id` | INTEGER | Id do círculo eleitoral na AR (cpId). |
| `name` | VARCHAR | Nome do círculo eleitoral (cpDes). |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
