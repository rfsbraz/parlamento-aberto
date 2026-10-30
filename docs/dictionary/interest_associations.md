# interest_associations

Uma linha por filiação ou função em entidades de natureza associativa declarada à EpT na XVI e na XVII (Regulamento da EpT n.º 258/2024, art. 15.º, n.º 1, al. b)). Fica fora de interests para poder sair sozinha. As linhas ficam fora da licença CC BY 4.0 e citam a EpT como fonte (Lei n.º 52/2019, art. 15.º, n.º 1; LADA, art. 21.º, n.º 1).

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `interest_associations.parquet` e `interest_associations.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `declaration_key` | VARCHAR | Declaração, liga a interest_declarations. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. Vem de seed_ept_holders e pode ser nulo. |
| `item_number` | INTEGER | Posição da linha dentro da secção. |
| `category` | VARCHAR | Sempre association. |
| `source_list` | VARCHAR | Designação da secção como a EpT a mostra. |
| `description` | VARCHAR | Cargo ou função tal como escrito. |
| `entity` | VARCHAR | Entidade indicada. |
| `activity_area` | VARCHAR | Natureza e área de atividade da entidade. |
| `location` | VARCHAR | Sede. |
| `paid_raw` | VARCHAR | Remuneração tal como publicada, 1 ou 0, não documentada pela EpT. |
| `start_date` | DATE | Data de início como dia em Europe/Lisbon. |
| `end_date` | DATE | Data de fim como dia em Europe/Lisbon. |
| `start_date_raw` | VARCHAR | Data de início tal como publicada, em UTC. |
| `end_date_raw` | VARCHAR | Data de fim tal como publicada, em UTC. |
| `entity_nipc` | VARCHAR | NIPC da entidade, só quando é um NIPC de empresa válido. Nulo nos outros casos. |
| `source` | VARCHAR | Sempre ept. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [interests](interests.md).

### seed_ept_holders

Correspondência entre titulares da EpT e o cadastro_id da AR (#47), uma linha por titular da Entidade para a Transparência que é Deputado ou Deputada na entidade 4508 (XVII) ou 510 (antes da XVII). Escrito por python -m parlamento_aberto.ept_crosswalk a partir das listas de titularidades da EpT e da InformacaoBase XIV a XVII, comparando o nome completo normalizado dentro das legislaturas que o órgão cobre, e tirando todos os outros titulares de seed_ept_holder_overrides. Só ids. Dois ids de titular podem partilhar um cadastro_id quando a EpT registou a mesma pessoa com um novo id de titular no outro órgão.

| Coluna | Tipo | Descrição |
|---|---|---|
| `ept_holder_id` | BIGINT | Id do titular na EpT (holderId), único. |
| `cadastro_id` | BIGINT | Id de cadastro do deputado na AR, nulo quando não há correspondência. |
| `match` | VARCHAR | name (nome completo normalizado, um candidato), override (de seed_ept_holder_overrides) ou unmatched (nenhum deputado da AR encontrado). |

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

### stg_ept_registo_interesses__associations

Uma linha por linha da secção de filiação ou funções em entidades de natureza associativa do separador 4 de uma declaração da EpT (Regulamento da EpT n.º 258/2024, art. 15.º, n.º 1, al. b)). Tem as colunas de stg_ept_registo_interesses__items e fica numa tabela à parte para poder sair sozinha.

| Coluna | Tipo | Descrição |
|---|---|---|
| `declaration_key` | VARCHAR | Declaração a que a linha pertence. |
| `item_number` | INTEGER | Posição da linha dentro da secção. |
| `category` | VARCHAR | Sempre association. |
| `source_list` | VARCHAR | Designação da secção como a EpT a mostra. |
| `item_id` | BIGINT | Nulo. As linhas da EpT não têm id. |
| `type_code` | INTEGER | Nulo. A EpT não tem código de tipo. |
| `description` | VARCHAR | Cargo ou função tal como escrito. |
| `entity` | VARCHAR | Entidade indicada. |
| `nature` | VARCHAR | Nulo. A secção não tem natureza. |
| `activity_area` | VARCHAR | Natureza e área de atividade da entidade. |
| `location` | VARCHAR | Sede. |
| `share` | VARCHAR | Nulo. |
| `paid_raw` | VARCHAR | Remuneração tal como publicada, 1 ou 0, não documentada pela EpT. |
| `start_date_raw` | VARCHAR | Data de início tal como publicada, em UTC. |
| `end_date_raw` | VARCHAR | Data de fim tal como publicada, em UTC. |
| `date_raw` | VARCHAR | Nulo. |
| `legislature` | VARCHAR | Legislatura da declaração. |
| `source_file` | VARCHAR | Ficheiro guardado de onde a linha foi lida, relativo a data/. |
| `source` | VARCHAR | Sempre ept. |
| `is_paid` | BOOLEAN | Nulo. A EpT não diz o que significam 1 e 0. |
| `start_date` | DATE | Data de início como dia em Europe/Lisbon. |
| `end_date` | DATE | Data de fim como dia em Europe/Lisbon. |
| `entity_nipc` | VARCHAR | NIPC da entidade, só quando é um NIPC de empresa válido. Nulo nos outros casos. |
| `beneficiary` | VARCHAR | Nulo. |
| `beneficiary_company` | VARCHAR | Nulo. |
| `share_value_eur` | VARCHAR | Nulo. |
| `share_pct` | VARCHAR | Nulo. |
| `share_holder` | VARCHAR | Nulo. |
| `is_professional_secrecy` | BOOLEAN | Nulo. |
| `observation` | VARCHAR | Nulo. |
