# parliamentary_groups

Uma linha por grupo parlamentar e por legislatura.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `parliamentary_groups.parquet` e `parliamentary_groups.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `group_acronym` | VARCHAR | Sigla do grupo, por exemplo PS. |
| `name` | VARCHAR | Nome completo do partido ou grupo. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### stg_informacao_base__parliamentary_groups

InformacaoBase GruposParlamentares, uma linha por grupo parlamentar.

| Coluna | Tipo | Descrição |
|---|---|---|
| `group_acronym` | VARCHAR | Sigla do grupo (sigla), por exemplo PS. |
| `name` | VARCHAR | Nome completo do partido ou grupo (nome). |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
