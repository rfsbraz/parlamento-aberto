# interest_declarations

Uma linha por declaração no registo de interesses, XI a XV. A XVI e a XVII não estão nos dados abertos da AR (as declarações passaram para a Entidade para a Transparência). Só estão cobertas as pessoas das listas da XVII, porque todos os ficheiros listam essas pessoas. Ficam de fora nomes, cônjuge, estado civil, regime de bens e campos fiscais e de contacto; para os nomes, faça join com deputies.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `interest_declarations.parquet` e `interest_declarations.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do ficheiro. |
| `declaration_key` | VARCHAR | Chave da declaração, liga a interests. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. |
| `format_version` | VARCHAR | Formato publicado, V1 (XI), V2 (XII, XIII), V3 (XIV) ou V5 (XIV, XV). |
| `declaration_id` | BIGINT | Id da declaração na AR. Nulo para a V3, que não publica nenhum. |
| `position` | VARCHAR | Cargo declarado, por exemplo Deputado. |
| `position_start_date` | DATE | Início do cargo, quando publicado como data completa. |
| `position_changed_date` | DATE | Data de alteração do cargo, quando publicada como data completa. |
| `position_end_date` | DATE | Fim do cargo, quando publicado como data completa. |
| `position_start_raw` | VARCHAR | Início do cargo tal como publicado. A V1 e a V2 publicam um ano. |
| `version_date` | DATE | Data desta versão da declaração, só V1 e V2. |
| `is_exclusive` | BOOLEAN | Cargo exercido em exclusividade. Nulo para V1 e V2. |
| `items` | INTEGER | Número de linhas em interests para esta declaração. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### stg_registo_interesses__declarations

Declarações do RegistoInteresses, uma linha cada, a partir de cadRgi (V1, V2), RecordInterests (V3) ou do formulário V5. As datas estão tal como publicadas.

| Coluna | Tipo | Descrição |
|---|---|---|
| `declaration_key` | VARCHAR | Chave construída como legislature-cadastro_id-n, em que n conta as declarações da pessoa no ficheiro. |
| `cadastro_id` | BIGINT | Id da pessoa (cadId, RecordId ou IdCadastroGODE). |
| `format_version` | VARCHAR | Formato do registo, V1, V2, V3 ou V5. |
| `declaration_id` | BIGINT | Id da declaração na AR (rgiId ou FactoDeclaracao.Id). A V3 não publica nenhum. |
| `declared_legislature` | VARCHAR | Legislatura indicada na declaração (rgiLegDes ou Legislatura). A V3 não indica nenhuma, por isso é a do ficheiro. |
| `position` | VARCHAR | Cargo declarado (rgiCargoDes, PositionDesignation ou CargoFuncao). |
| `position_start_raw` | VARCHAR | Início do cargo tal como publicado (rgiCargoData, um ano, PositionBeginDate ou DataInicioFuncao). |
| `position_changed_raw` | VARCHAR | Data de alteração do cargo tal como publicada (PositionChangedDate ou DataAlteracaoFuncao). |
| `position_end_raw` | VARCHAR | Fim do cargo tal como publicado (PositionEndDate ou DataCessacaoFuncao). |
| `version_date_raw` | VARCHAR | Data desta versão da declaração (rgiDataVersao), só V1 e V2. |
| `is_exclusive` | BOOLEAN | Cargo exercido em exclusividade (V3 Exclusivity, V5 Exclusividade). Nulo para V1 e V2. |
| `items` | INTEGER | Número de itens declarados, uma linha cada em stg_registo_interesses__items. |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
