# sessions

Uma linha por sessão legislativa.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `sessions.parquet` e `sessions.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `session_number` | INTEGER | Número da sessão dentro da legislatura. |
| `start_date` | DATE | Primeiro dia da sessão. |
| `end_date` | DATE | Último dia da sessão. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### stg_informacao_base__sessions

InformacaoBase SessoesLegislativas, uma linha por sessão legislativa.

| Coluna | Tipo | Descrição |
|---|---|---|
| `session_number` | INTEGER | Número da sessão dentro da legislatura (numSessao). |
| `start_date` | DATE | Primeiro dia da sessão (dataInicio). |
| `end_date` | DATE | Último dia da sessão (dataFim). |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
