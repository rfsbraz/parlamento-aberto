# interests

Uma linha por interesse declarado, das mesmas duas fontes de interest_declarations (ar_open_data, XI a XV, e ept, XVI e XVII): atividades e cargos, cargos sociais, sociedades, apoios, serviços e outras situações. O texto está tal como publicado, por isso os itens de texto livre podem dizer "Nada a declarar". Na AR o JSON prevalece sobre o mapeador antigo: a V1 publica as atividades como um único campo de texto livre, e a V5 também é lida (XIV, XV), porque o dump a contém. Na EpT só entra o separador 4. As primeiras colunas são as de sempre; paid_raw e as colunas da EpT vêm depois. As linhas da EpT ficam fora da licença CC BY 4.0 e fora dos ficheiros publicados até haver autorização de reutilização (Lei n.º 52/2019, art. 17.º).

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `interests.parquet` e `interests.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `declaration_key` | VARCHAR | Declaração, liga a interest_declarations. |
| `item_number` | INTEGER | Posição do item dentro da declaração. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. Na EpT vem de seed_ept_holders e pode ser nulo. |
| `category` | VARCHAR | activity, social_position, society, support, service ou other_situation (atividade, cargo social, sociedade, apoio, serviço ou outra situação). Da EpT não entra a filiação em entidades de natureza associativa (Regulamento da EpT n.º 258/2024, art. 15.º, n.º 1, al. b)). |
| `source_list` | VARCHAR | Lista, campo ou secção publicada de onde vem o item, por exemplo GenCargosMaisTresAnos. |
| `item_id` | BIGINT | Id do item na AR, quando publicado. Nulo na EpT. |
| `type_code` | INTEGER | Código Type da V3 tal como publicado (0, 1 ou 2), não documentado pela AR. |
| `description` | VARCHAR | Atividade, cargo, apoio, serviço ou situação tal como escrito. |
| `entity` | VARCHAR | Entidade, empresa ou organismo indicado. |
| `nature` | VARCHAR | Natureza da entidade ou do benefício, só V5 e EpT. |
| `activity_area` | VARCHAR | Área de atividade. |
| `location` | VARCHAR | Sede ou local. |
| `share` | VARCHAR | Participação social tal como escrita, para sociedades. Nulo na EpT; ver share_value_eur e share_pct. |
| `is_paid` | BOOLEAN | Verdadeiro para S, falso para N. Nulo nos outros casos, incluindo o 0 que a V5 publica e o 1 ou 0 da EpT. |
| `start_date` | DATE | Data de início, quando publicada como data completa. Na EpT, o dia em Europe/Lisbon. |
| `end_date` | DATE | Data de fim, quando publicada como data completa. Na EpT, o dia em Europe/Lisbon. |
| `start_date_raw` | VARCHAR | Data de início tal como publicada, um ano, um mês ou um dia. Na EpT, em UTC. |
| `end_date_raw` | VARCHAR | Data de fim tal como publicada. |
| `date_raw` | VARCHAR | Data única ou período tal como publicado nos apoios e serviços da V5. |
| `source` | VARCHAR | Fonte da linha, ar_open_data ou ept. |
| `paid_raw` | VARCHAR | Remuneração tal como publicada, S ou N na AR, 1 ou 0 na EpT (não documentado pela EpT). |
| `entity_nipc` | VARCHAR | NIPC da entidade, só na EpT e só quando é um NIPC de empresa válido. Nulo nos outros casos. |
| `beneficiary` | VARCHAR | Beneficiário de um apoio ou benefício tal como escrito. Só EpT. |
| `beneficiary_company` | VARCHAR | Empresa do beneficiário, nos apoios. Só EpT. |
| `share_value_eur` | VARCHAR | Valor da participação social em euros, tal como escrito. Só EpT. |
| `share_pct` | VARCHAR | Percentagem da participação social, tal como escrita. Só EpT. |
| `share_holder` | VARCHAR | Titular da participação social tal como escrito. Só EpT. |
| `is_professional_secrecy` | BOOLEAN | Segredo profissional invocado, nos serviços e outras situações. Só EpT. |
| `observation` | VARCHAR | Observação de uma outra situação. Só EpT. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [interest_declarations](interest_declarations.md).

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

### stg_ept_registo_interesses__declarations

Registo de interesses da EpT (XVI, XVII e as declarações anteriores da entidade 510), uma linha por declaração guardada de um Deputado ou Deputada, a partir de data/ept_registo_interesses. As primeiras colunas são as de stg_registo_interesses__declarations. As versões substituídas e modificadas ficam como linhas próprias. Não publicado até a EpT responder (#42).

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

### stg_ept_registo_interesses__items

Uma linha por linha do separador 4 de uma declaração da EpT em stg_ept_registo_interesses__declarations. As primeiras colunas são as de stg_registo_interesses__items. O texto fica sem espaços nas pontas, e as datas ficam tal como publicadas nas colunas _raw e convertidas para o dia em Europe/Lisbon.

| Coluna | Tipo | Descrição |
|---|---|---|
| `declaration_key` | VARCHAR | Declaração a que o item pertence. |
| `item_number` | INTEGER | Posição do item dentro da declaração, com as secções pela ordem do separador 4. |
| `category` | VARCHAR | activity, support, service, society ou other_situation (atividade, apoio, serviço, sociedade ou outra situação). A secção de filiação em entidades de natureza associativa nunca é lida (Regulamento da EpT n.º 258/2024, art. 15.º, n.º 1, al. b)). |
| `source_list` | VARCHAR | Designação da secção do separador 4 como a EpT a mostra. |
| `item_id` | BIGINT | Nulo. As linhas da EpT não têm id. |
| `type_code` | INTEGER | Nulo. A EpT não tem código de tipo. |
| `description` | VARCHAR | Cargo, atividade, apoio, serviço ou situação tal como escrito. |
| `entity` | VARCHAR | Entidade, empresa ou organismo indicado. |
| `nature` | VARCHAR | Natureza de uma sociedade ou de um apoio ou benefício. |
| `activity_area` | VARCHAR | Natureza e área de atividade da entidade. |
| `location` | VARCHAR | Sede. |
| `share` | VARCHAR | Nulo. A EpT publica a participação como share_value_eur e share_pct. |
| `paid_raw` | VARCHAR | Remuneração tal como publicada, 1 ou 0, não documentada pela EpT. |
| `start_date_raw` | VARCHAR | Data de início tal como publicada, em UTC. |
| `end_date_raw` | VARCHAR | Data de fim tal como publicada, em UTC. |
| `date_raw` | VARCHAR | Data de uma outra situação tal como publicada. |
| `legislature` | VARCHAR | Legislatura da declaração. |
| `source_file` | VARCHAR | Ficheiro guardado de onde a linha foi lida, relativo a data/. |
| `source` | VARCHAR | Sempre ept. |
| `is_paid` | BOOLEAN | Nulo. A EpT não diz o que significam 1 e 0. |
| `start_date` | DATE | Data de início como dia em Europe/Lisbon. |
| `end_date` | DATE | Data de fim como dia em Europe/Lisbon. |
| `entity_nipc` | VARCHAR | NIPC da entidade, só quando é um NIPC de empresa válido. Nulo nos outros casos. |
| `beneficiary` | VARCHAR | Beneficiário de um apoio ou benefício tal como escrito. |
| `beneficiary_company` | VARCHAR | Empresa do beneficiário, nos apoios. |
| `share_value_eur` | VARCHAR | Valor da participação social em euros, tal como escrito. |
| `share_pct` | VARCHAR | Percentagem da participação social, tal como escrita. |
| `share_holder` | VARCHAR | Titular da participação social tal como escrito. |
| `is_professional_secrecy` | BOOLEAN | Segredo profissional invocado, nos serviços e outras situações. |
| `observation` | VARCHAR | Observação de uma outra situação. |
