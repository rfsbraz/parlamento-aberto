# interests

Uma linha por interesse declarado: atividades e cargos, cargos sociais, sociedades, apoios, serviços e outras situações. O texto está tal como publicado, por isso os itens de texto livre podem dizer "Nada a declarar". O JSON prevalece sobre o mapeador antigo: a V1 publica as atividades como um único campo de texto livre, e a V5 também é lida (XIV, XV), porque o dump a contém.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `interests.parquet` e `interests.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `declaration_key` | VARCHAR | Declaração, liga a interest_declarations. |
| `item_number` | INTEGER | Posição do item dentro da declaração. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. |
| `category` | VARCHAR | activity, social_position, society, support, service ou other_situation (atividade, cargo social, sociedade, apoio, serviço ou outra situação). |
| `source_list` | VARCHAR | Lista ou campo publicado de onde vem o item, por exemplo GenCargosMaisTresAnos. |
| `item_id` | BIGINT | Id do item na AR, quando publicado. |
| `type_code` | INTEGER | Código Type da V3 tal como publicado (0, 1 ou 2), não documentado pela AR. |
| `description` | VARCHAR | Atividade, cargo, apoio, serviço ou situação tal como escrito. |
| `entity` | VARCHAR | Entidade, empresa ou organismo indicado. |
| `nature` | VARCHAR | Natureza da entidade ou do benefício, só V5. |
| `activity_area` | VARCHAR | Área de atividade. |
| `location` | VARCHAR | Sede ou local. |
| `share` | VARCHAR | Participação social tal como escrita, para sociedades. |
| `is_paid` | BOOLEAN | Verdadeiro para S, falso para N. Nulo nos outros casos, incluindo o 0 que a V5 publica. |
| `start_date` | DATE | Data de início, quando publicada como data completa. |
| `end_date` | DATE | Data de fim, quando publicada como data completa. |
| `start_date_raw` | VARCHAR | Data de início tal como publicada, um ano, um mês ou um dia. |
| `end_date_raw` | VARCHAR | Data de fim tal como publicada. |
| `date_raw` | VARCHAR | Data única ou período tal como publicado nos apoios e serviços da V5. |

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

### stg_registo_interesses__items

Uma linha por item declarado, tal como publicado. Os campos de texto livre da V1 e da V2 (e as atividades da V1) dão um item cada.

| Coluna | Tipo | Descrição |
|---|---|---|
| `declaration_key` | VARCHAR | Declaração a que o item pertence. |
| `item_number` | INTEGER | Posição do item dentro da declaração. |
| `category` | VARCHAR | activity, social_position, society, support, service ou other_situation (atividade, cargo social, sociedade, apoio, serviço ou outra situação). |
| `source_list` | VARCHAR | Lista ou campo publicado de onde vem o item, por exemplo rgiCargosSociais ou GenCargosMenosTresAnos. |
| `item_id` | BIGINT | Id do item na AR, quando publicado. |
| `type_code` | INTEGER | Código Type da V3 tal como publicado (0, 1 ou 2), não documentado pela AR. |
| `description` | VARCHAR | Atividade, cargo, apoio, serviço ou situação tal como escrito. |
| `entity` | VARCHAR | Entidade, empresa ou organismo indicado. |
| `nature` | VARCHAR | Natureza da entidade ou do benefício (V5 Natureza, NaturezaBeneficio). |
| `activity_area` | VARCHAR | Área de atividade. |
| `location` | VARCHAR | Sede ou local. |
| `share` | VARCHAR | Participação social tal como escrita, para sociedades. |
| `paid_raw` | VARCHAR | Indicação de remuneração tal como publicada (S, N, ou 0 na V5). |
| `start_date_raw` | VARCHAR | Data de início tal como publicada, um ano, um mês ou um dia. |
| `end_date_raw` | VARCHAR | Data de fim tal como publicada. |
| `date_raw` | VARCHAR | Data única ou período tal como publicado nos apoios e serviços da V5. |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
