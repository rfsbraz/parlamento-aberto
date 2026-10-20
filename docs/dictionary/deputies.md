# deputies

Uma linha por pessoa (cadastro_id) que aparece em qualquer lista, eleita ou não. Use mandates para saber quem teve lugar e quando.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `deputies.parquet` e `deputies.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `cadastro_id` | BIGINT | Id da pessoa, comum a todas as legislaturas e conjuntos de dados. |
| `full_name` | VARCHAR | Nome completo, do RegistoBiografico quando existe, senão da InformacaoBase mais recente. |
| `parliamentary_name` | VARCHAR | Nome usado no parlamento, da legislatura mais recente em que a pessoa aparece. |
| `sex` | VARCHAR | Sexo tal como publicado pela AR, M ou F. Nulo sem registo no RegistoBiografico. |
| `birth_date` | DATE | Data de nascimento. Nulo sem registo no RegistoBiografico. |
| `profession` | VARCHAR | Profissão. Nulo sem registo no RegistoBiografico. |
| `biography_legislature` | VARCHAR | Legislatura do registo do RegistoBiografico de onde vêm os campos biográficos, a mais recente para a pessoa. Só há biografias reais por legislatura para a Constituinte, a II e a III; a XVII é o registo atual. Nulo sem registo no RegistoBiografico. |

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

### stg_registo_biografico__biographies

RegistoBiografico, uma linha por registo de pessoa, só campos escalares. II e III vêm dos ficheiros mais antigos em formato XML listados na página I Legislatura da AR (chaves em camelCase), e Constituinte do RegistoBiograficoConstituinte.xml mais antigo, no mesmo formato. As outras páginas são cópias mais antigas do registo da XVII e não são guardadas, exceto a I (335 pessoas), pelo que as linhas da I não são os deputados dessa legislatura (docs/known-gaps.md).

| Coluna | Tipo | Descrição |
|---|---|---|
| `cadastro_id` | BIGINT | Id da pessoa, comum a todas as legislaturas e conjuntos de dados (CadId). |
| `full_name` | VARCHAR | Nome completo (CadNomeCompleto). |
| `birth_date` | DATE | Data de nascimento (CadDtNascimento). |
| `sex` | VARCHAR | Sexo tal como publicado pela AR, M ou F (CadSexo). |
| `profession` | VARCHAR | Profissão (CadProfissao). |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
