# initiative_authors

Uma linha por autor de uma iniciativa.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `initiative_authors.parquet` e `initiative_authors.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura da iniciativa. |
| `initiative_id` | BIGINT | Iniciativa, liga a initiatives. |
| `author_type` | VARCHAR | deputy (deputado), group (grupo) ou other para qualquer autor que não seja deputado nem grupo (Governo, uma assembleia regional, uma comissão, cidadãos). |
| `cadastro_id` | BIGINT | Num deputado, o id da pessoa, liga a deputies. |
| `group_code` | VARCHAR | Num deputado, o grupo indicado com ele; num grupo, o seu código. Depois de seed_group_aliases. |
| `group_code_raw` | VARCHAR | O mesmo código tal como publicado. |
| `name` | VARCHAR | Num deputado, o nome tal como publicado; em other, o autor (o nome da comissão, ou o tipo de autor, como Governo). |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### stg_iniciativas__initiatives

Iniciativas, uma linha por registo de iniciativa.

| Coluna | Tipo | Descrição |
|---|---|---|
| `initiative_id` | BIGINT | Id da iniciativa na AR (IniId). |
| `number` | INTEGER | Número da iniciativa dentro do seu tipo e legislatura (IniNr). |
| `type_code` | VARCHAR | Código do tipo de iniciativa (IniTipo), por exemplo J. |
| `type` | VARCHAR | Tipo de iniciativa (IniDescTipo), por exemplo Projeto de Lei. |
| `session_number` | INTEGER | Sessão legislativa em que a iniciativa deu entrada (IniSel). |
| `title` | VARCHAR | Título (IniTitulo). |
| `text_url` | VARCHAR | Ligação para o texto da iniciativa (IniLinkTexto). |
| `author_kind_code` | VARCHAR | Código do tipo de autor (IniAutorOutros.sigla), por exemplo D, G ou V. |
| `author_kind` | VARCHAR | Tipo de autor (IniAutorOutros.nome), por exemplo Deputados, Grupos Parlamentares ou Governo. |
| `author_committee` | VARCHAR | Comissão autora da iniciativa, quando o autor é uma comissão (IniAutorOutros.iniAutorComissao). |
| `author_deputies` | STRUCT(cadastro_id BIGINT, "name" VARCHAR, group_acronym VARCHAR)[] | Deputados autores (IniAutorDeputados) como cadastro_id, name, group_acronym. |
| `author_groups` | VARCHAR[] | Grupos autores (IniAutorGruposParlamentares) como siglas de grupos. |
| `events` | STRUCT(event_id BIGINT, phase VARCHAR, phase_date DATE, votes STRUCT(id VARCHAR, "data" VARCHAR, resultado VARCHAR, reuniao VARCHAR, tipoReuniao VARCHAR, unanime VARCHAR, descricao VARCHAR, detalhe VARCHAR, ausencias VARCHAR[])[], committees STRUCT(committee_id BIGINT, committee_name VARCHAR, votes STRUCT(id VARCHAR, "data" VARCHAR, resultado VARCHAR, reuniao VARCHAR, unanime VARCHAR, descricao VARCHAR, detalhe VARCHAR, ausencias VARCHAR[])[])[])[] | Eventos (IniEventos) como event_id, phase, phase_date, as votações em plenário em bruto (Votacao) e as comissões (Comissao) como committee_id, committee_name e as suas votações em bruto. |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |

### seed_group_aliases

Aliases mantidos à mão para códigos de grupo que a AR escreve de forma diferente dentro de uma legislatura, cada linha com a sua fonte. Os marts guardam o código publicado em group_code_raw e põem em group_code o código do alias, ou o publicado quando não se aplica nenhum alias.

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana (o nome da pasta de dados, por exemplo I-B) a que o alias se aplica. |
| `alias` | VARCHAR | Código tal como publicado, por exemplo PPD. |
| `group_code` | VARCHAR | Código correspondente, como listado em parliamentary_groups nessa legislatura. |
| `source_url` | VARCHAR | Referência para a correspondência. |
| `note` | VARCHAR | Porque existe o alias. |
