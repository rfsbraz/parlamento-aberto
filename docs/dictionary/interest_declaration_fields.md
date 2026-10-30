# interest_declaration_fields

Uma linha por campo visível dos separadores 2 (dados pessoais) e 3 (rendimentos e património) das declarações da EpT da XVI e da XVII. Só entram os campos que a EpT mostra; o NIF dos titulares nunca entra, e qualquer número de 9 dígitos no valor fica [removido], também os NIPC de empresas, porque as colunas do separador 3 não dizem qual é a do NIF. Os campos ficam pela posição na declaração, com a tabela e a coluna. As linhas ficam fora da licença CC BY 4.0 e citam a EpT como fonte (Lei n.º 52/2019, art. 15.º, n.º 1; LADA, art. 21.º, n.º 1).

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `interest_declaration_fields.parquet` e `interest_declaration_fields.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `declaration_key` | VARCHAR | Declaração, liga a interest_declarations. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. Vem de seed_ept_holders e pode ser nulo. |
| `field_number` | INTEGER | Posição do campo na declaração, separador 2 primeiro. |
| `tab` | VARCHAR | tab2 (dados pessoais) ou tab3 (rendimentos e património). |
| `path` | VARCHAR | Posição do campo na árvore do separador, por exemplo 0.3.1.2. |
| `section` | VARCHAR | Tabela do separador 3, por exemplo real_estate_portugal. Nulo no separador 2. |
| `column_name` | VARCHAR | Coluna da tabela do separador 3 (col1, col2...). Nulo fora das tabelas. |
| `label` | VARCHAR | Nome do campo no formulário da EpT, quando é conhecido. |
| `value` | VARCHAR | Valor tal como publicado, em texto. |
| `source` | VARCHAR | Sempre ept. |

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

### stg_ept_registo_interesses__fields

Uma linha por campo visível dos separadores 2 (dados pessoais) e 3 (rendimentos e património) de uma declaração da EpT em stg_ept_registo_interesses__declarations. Só entram os campos que a EpT mostra; o NIF do titular nunca é guardado. Os campos ficam pela posição na declaração, com a tabela e a coluna, e nunca pelas chaves da EpT. Qualquer número de 9 dígitos no valor fica [removido].

| Coluna | Tipo | Descrição |
|---|---|---|
| `declaration_key` | VARCHAR | Declaração a que o campo pertence. |
| `field_number` | INTEGER | Posição do campo na declaração, separador 2 primeiro. |
| `tab` | VARCHAR | tab2 (dados pessoais) ou tab3 (rendimentos e património). |
| `path` | VARCHAR | Posição do campo na árvore do separador, por exemplo 0.3.1.2. |
| `section` | VARCHAR | Tabela do separador 3, por exemplo real_estate_portugal. Nulo no separador 2. |
| `column_name` | VARCHAR | Coluna da tabela do separador 3 (col1, col2...). Nulo fora das tabelas. |
| `label` | VARCHAR | Nome do campo no formulário da EpT, quando é conhecido. |
| `value` | VARCHAR | Valor tal como publicado, em texto. |
| `legislature` | VARCHAR | Legislatura da declaração. |
| `source` | VARCHAR | Sempre ept. |
| `source_file` | VARCHAR | Ficheiro guardado de onde a linha foi lida, relativo a data/. |
