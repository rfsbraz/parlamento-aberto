# initiatives

Uma linha por iniciativa.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `initiatives.parquet` e `initiatives.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura da iniciativa, a partir do caminho do ficheiro. A legislatura I é publicada em dois ficheiros, I-A e I-B. |
| `initiative_id` | BIGINT | Id da iniciativa na AR. |
| `number` | INTEGER | Número da iniciativa dentro do seu tipo e legislatura. |
| `type_code` | VARCHAR | Código do tipo de iniciativa, por exemplo J. |
| `type` | VARCHAR | Tipo de iniciativa, por exemplo Projeto de Lei. |
| `session_number` | INTEGER | Sessão legislativa em que a iniciativa deu entrada. |
| `title` | VARCHAR | Título. |
| `author_kind` | VARCHAR | Tipo de autor tal como publicado, por exemplo Deputados, Grupos Parlamentares ou Governo. |
| `first_event_date` | DATE | Data do primeiro evento da iniciativa. |
| `text_url` | VARCHAR | Ligação para o texto da iniciativa. |

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
