# interest_declarations

Uma linha por declaração no registo de interesses, de duas fontes: os dados abertos da AR (source = ar_open_data, XI a XV) e a Entidade para a Transparência (source = ept, XVI e XVII). Não há dedup entre fontes: das declarações da EpT só entram as da XVI e da XVII, que a AR já não publica; as da EpT anteriores à XVI ficam só em staging. Nos dados da AR só estão cobertas as pessoas das listas da XVII, porque todos os ficheiros listam essas pessoas. As primeiras colunas são as de sempre; as colunas da EpT vêm depois e são nulas nas linhas da AR. As linhas da EpT ficam fora da licença CC BY 4.0 e citam a EpT como fonte (Lei n.º 52/2019, art. 15.º, n.º 1; LADA, art. 21.º, n.º 1). Ficam de fora nomes, cônjuge, estado civil, regime de bens, NIF e campos de contacto; para os nomes, faça join com deputies.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `interest_declarations.parquet` e `interest_declarations.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. Na AR vem do ficheiro; na EpT, das datas da declaração. |
| `declaration_key` | VARCHAR | Chave da declaração, única nas duas fontes, liga a interests. Na EpT é ept:<id>. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. Na EpT vem de seed_ept_holders e fica nulo quando o titular não tem correspondência. |
| `format_version` | VARCHAR | Formato publicado, V1 (XI), V2 (XII, XIII), V3 (XIV), V5 (XIV, XV) ou EPT. |
| `declaration_id` | BIGINT | Id da declaração na fonte. Nulo para a V3, que não publica nenhum. |
| `position` | VARCHAR | Cargo declarado, por exemplo Deputado ou Deputada. |
| `position_start_date` | DATE | Início do cargo, quando publicado como data completa. Na EpT, o dia em Europe/Lisbon. |
| `position_changed_date` | DATE | Data de alteração do cargo, quando publicada como data completa. Nulo na EpT. |
| `position_end_date` | DATE | Fim do cargo, quando publicado como data completa. Na EpT, o dia em Europe/Lisbon. |
| `position_start_raw` | VARCHAR | Início do cargo tal como publicado. A V1 e a V2 publicam um ano. |
| `version_date` | DATE | Data desta versão da declaração, só V1 e V2. |
| `is_exclusive` | BOOLEAN | Cargo exercido em exclusividade. Nulo para V1, V2 e EpT. |
| `items` | INTEGER | Número de linhas em interests para esta declaração. |
| `source` | VARCHAR | Fonte da linha, ar_open_data ou ept. |
| `source_format` | VARCHAR | Formato na fonte, igual a format_version (V1, V2, V3, V5 ou EPT). |
| `source_declaration_id` | BIGINT | Id da declaração na fonte, igual a declaration_id. |
| `ept_holder_id` | BIGINT | Id do titular na EpT, liga a seed_ept_holders. Nulo na AR. |
| `declaration_nature` | VARCHAR | Natureza da declaração na EpT, initial, modification, cessation, final, replace ou reElection. Nulo na AR. |
| `declaration_state` | VARCHAR | Estado da declaração na EpT, por exemplo published, replaced ou modified. Nulo na AR. |
| `supersedes_declaration_id` | BIGINT | Declaração da EpT que esta substitui ou modifica. Nulo na AR. |
| `superseded_by_declaration_id` | BIGINT | Declaração da EpT que substitui ou modifica esta, se existir. Nulo na AR. |
| `chain_root_declaration_id` | BIGINT | Primeira declaração da EpT da cadeia desta. Nulo na AR. |
| `submitted_at` | VARCHAR | Hora de entrega na EpT tal como publicada. Nulo na AR. |
| `submitted_date` | DATE | Entrega na EpT como dia em Europe/Lisbon. Nulo na AR. |
| `is_current` | BOOLEAN | Verdadeiro para a declaração publicada mais recente da cadeia na EpT. Nulo na AR, que não publica versões. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### seed_ept_holders

Correspondência entre titulares da EpT e o cadastro_id da AR (#47), uma linha por titular da Entidade para a Transparência que é Deputado ou Deputada na entidade 4508 (XVII) ou 510 (antes da XVII). Escrito por python -m parlamento_aberto.ept_crosswalk a partir das listas de titularidades da EpT e da InformacaoBase XIV a XVII, comparando o nome completo normalizado dentro das legislaturas que o órgão cobre, e tirando todos os outros titulares de seed_ept_holder_overrides. Só ids. Dois ids de titular podem partilhar um cadastro_id quando a EpT registou a mesma pessoa com um novo id de titular no outro órgão.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ept_holder_id` | BIGINT | Id do titular na EpT (holderId), único. |
| `cadastro_id` | BIGINT | Id de cadastro do deputado na AR, nulo quando não há correspondência. |
| `match` | VARCHAR | name (nome completo normalizado, um candidato), override (de seed_ept_holder_overrides) ou unmatched (nenhum deputado da AR encontrado). |

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

### stg_ept_registo_interesses__declarations

Registo de interesses da EpT (XVI, XVII e as declarações anteriores da entidade 510), uma linha por declaração guardada de um Deputado ou Deputada, a partir de data/ept_registo_interesses. As primeiras colunas são as de stg_registo_interesses__declarations. As versões substituídas e modificadas ficam como linhas próprias. É staging, por isso não entra nos ficheiros publicados.

| Coluna | Tipo | Descrição |
|---|---|---|
| `declaration_key` | VARCHAR | Chave construída como ept:<id da declaração na EpT>. |
| `cadastro_id` | BIGINT | Nulo aqui; os marts preenchem-no a partir de seed_ept_holders (#47). |
| `format_version` | VARCHAR | Sempre EPT. |
| `declaration_id` | BIGINT | Id da declaração na EpT, o mesmo que source_declaration_id. |
| `declared_legislature` | VARCHAR | Nulo. As declarações da EpT indicam um órgão, não uma legislatura. |
| `position` | VARCHAR | Cargo como a EpT o designa, Deputado ou Deputada. |
| `position_start_raw` | VARCHAR | Início do cargo tal como publicado (startDate). |
| `position_changed_raw` | VARCHAR | Nulo. A EpT não publica data de alteração do cargo. |
| `position_end_raw` | VARCHAR | Fim do cargo tal como publicado (endDate). |
| `version_date_raw` | VARCHAR | Nulo. A EpT não tem data de versão; ver submitted_at. |
| `is_exclusive` | BOOLEAN | Nulo. O separador 4 não tem campo de exclusividade. |
| `items` | INTEGER | Número de linhas em stg_ept_registo_interesses__items para esta declaração. |
| `legislature` | VARCHAR | Legislatura cujas datas contêm o dia de início do cargo em Lisboa, ou o dia de entrega quando não há início. Não é tirada do órgão da EpT. |
| `source_file` | VARCHAR | Ficheiro guardado de onde a linha foi lida, relativo a data/. |
| `source` | VARCHAR | Sempre ept. |
| `source_format` | VARCHAR | Sempre EPT. |
| `source_declaration_id` | BIGINT | Id da declaração na EpT. |
| `ept_holder_id` | BIGINT | Id do titular na EpT, liga a seed_ept_holders. |
| `ept_entity_id` | BIGINT | Órgão na EpT, 510 (Assembleia da República, XIV a XVI) ou 4508 (XVII Legislatura). |
| `ept_role_id` | BIGINT | Cargo na EpT, 8 (Deputado) ou 232 (Deputada). |
| `position_start_date` | DATE | Início do cargo como dia em Europe/Lisbon. |
| `position_changed_date` | DATE | Nulo, como position_changed_raw. |
| `position_end_date` | DATE | Fim do cargo como dia em Europe/Lisbon. |
| `version_date` | DATE | Nulo, como version_date_raw. |
| `declaration_nature` | VARCHAR | initial, modification, cessation, final, replace ou reElection. |
| `declaration_state` | VARCHAR | published, replaced ou modified (e também draft, pendingVerification, notPublished ou canceled se a EpT listar alguma). |
| `supersedes_declaration_id` | BIGINT | Declaração que esta substitui ou modifica (relatedDeclarationId). |
| `superseded_by_declaration_id` | BIGINT | Declaração guardada que substitui ou modifica esta, se existir. |
| `chain_root_declaration_id` | BIGINT | Primeira declaração guardada da cadeia de substituições ou modificações desta. |
| `submitted_at` | VARCHAR | Hora de entrega tal como publicada (submitedDate). |
| `submitted_date` | DATE | Entrega como dia em Europe/Lisbon. |
| `is_current` | BOOLEAN | Verdadeiro para a declaração publicada mais recente sem sucessora, por titular, órgão e cargo. |
