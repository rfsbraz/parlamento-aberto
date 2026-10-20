# mandates

Uma linha por deputado, legislatura e período de situação (DepSituacao), tal como publicado. Quem tinha lugar no dia D é a consulta seated_on(D), não uma coluna; seated_during(D0, D1) dá o mesmo para cada dia de um intervalo, e os marts de votações usam-na. Os períodos da AR de uma pessoa podem sobrepor-se num dia de passagem, por exemplo um período Efetivo e um Suspenso que cobrem o mesmo dia. A regra: entre os períodos de uma pessoa que cobrem D, ganha o que começa mais tarde; em caso de empate, ganha o mais longo (um fim em aberto conta como o mais longo); e, com as duas datas empatadas, ganha o efetivo. A pessoa tem lugar se esse período for Efetivo, Efetivo Temporário ou Efetivo Definitivo. Num dia de troca, quando um círculo tem mais deputados em D do que em D - 1 e em D + 1, os períodos efetivos que terminam em D (sem período efetivo da mesma pessoa a começar em D + 1) não contam, até esse excesso e ao número de pessoas que começam um lugar em D. As contagens da Constituinte à VI continuam sobrestimadas em muitos dias, ver docs/known-gaps.md.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `mandates.parquet` e `mandates.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. |
| `deputy_id` | BIGINT | Id desta pessoa nesta legislatura. |
| `circle_id` | INTEGER | Círculo eleitoral por onde a pessoa concorreu, liga a electoral_circles. |
| `situation` | VARCHAR | Situação tal como publicada, por exemplo Efetivo, Suplente, Suspenso(Eleito). |
| `is_effective` | BOOLEAN | Verdadeiro para Efetivo, Efetivo Temporário e Efetivo Definitivo, as situações que ocupam um lugar. |
| `start_date` | DATE | Primeiro dia da situação. |
| `end_date` | DATE | Último dia da situação, nulo enquanto está aberta. |

## Particularidades conhecidas

- A InformacaoBase lista todas as pessoas nas listas de uma legislatura, eleitas ou não: 1446 pessoas na XVII na sincronização de 20 de outubro de 2026, para 230 lugares. Conte os lugares a partir dos períodos is_effective que cobrem uma data, não a partir das linhas das listas. O site antigo contava cada registo como um deputado.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

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
