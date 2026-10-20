# plenary_attendance

Uma linha por reunião plenária e pessoa na sua lista de presenças. As listas trazem quem tinha lugar em cada reunião, substitutos incluídos. Associado ao cadastro_id pela legislatura, pelo nome parlamentar exato e pelo grupo, que tem de ser um dos grupos da pessoa (DepGP) nessa legislatura. Nunca entre legislaturas: há nomes parlamentares de pessoas diferentes em legislaturas diferentes. O motivo da falta não é publicado, só o código. O build para se aparecer um código que não está em seed_attendance_codes.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `plenary_attendance.parquet` e `plenary_attendance.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `meeting_id` | BIGINT | Id da reunião na AR. A página da reunião é https://www.parlamento.pt/DeputadoGP/Paginas/DetalheReuniaoPlenaria.aspx?BID=<meeting_id>. |
| `meeting_number` | INTEGER | Número da reunião na legislatura. |
| `session_number` | INTEGER | Número da sessão legislativa, liga a sessions. |
| `meeting_date` | DATE | Data da reunião. |
| `meeting_type` | VARCHAR | Tipo de reunião, Ordinária, Extraordinária, Solene ou Comemorativa. |
| `is_ceremonial` | BOOLEAN | Verdadeiro numa reunião solene ou comemorativa. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. Nulo quando nenhum deputado ou mais do que um corresponde ao nome e ao grupo (os testes falham nesse caso). |
| `parliamentary_name` | VARCHAR | Nome parlamentar tal como na lista. |
| `group_code` | VARCHAR | Código do grupo depois de seed_group_aliases. Indep e Ninsc marcam deputados fora de qualquer grupo. |
| `group_code_raw` | VARCHAR | Código do grupo tal como na lista. |
| `code` | VARCHAR | Código de presença ou falta tal como publicado, liga a seed_attendance_codes. |
| `category` | VARCHAR | Categoria do código, de seed_attendance_codes: present, other_body_or_mission, justified, missed_quorum_vote, pending ou unjustified. Uma falta FA com 60 dias ou mais em source_updated passa a unclassified. |
| `is_pending` | BOOLEAN | Verdadeiro para uma falta FA com menos de 60 dias em source_updated. Não é uma falta injustificada. |
| `source_updated` | DATE | Data de atualização dos dados desta legislatura: a data em que o ficheiro da AR foi recolhido com alterações pela última vez (fetched em data/_meta/sources.lock.json). É a referência da regra dos 60 dias do FA. |

## Particularidades conhecidas

- Há listas de presenças a partir da VI (uma reunião na V) e para todas as reuniões a partir da VII. Não há listas da Constituinte à IV. Ver docs/known-gaps.md.
- Os dados abertos não têm legenda para os códigos. Os significados vêm das páginas de cada reunião no parlamento.pt, que mostram por exemplo PP e PT como Presença (P), FIJ, FAJ e QVJ como Falta Justificada (FJ) e CO como Presença em Comissão autorizada pelo PAR. A fonte de cada código está em seed_attendance_codes.
- FA é uma falta que a AR ainda não classificou. Com menos de 60 dias na data de atualização dos dados (source_updated) é pending (por justificar); a partir daí é unclassified (não classificada). Nunca é contada como injustificada.
- As listas incluem reuniões solenes, comemorativas e extraordinárias. is_ceremonial marca as solenes e as comemorativas, para as deixar de fora de uma taxa.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [legislatures](legislatures.md).

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

### seed_group_aliases

Aliases mantidos à mão para códigos de grupo que a AR escreve de forma diferente dentro de uma legislatura, cada linha com a sua fonte. Os marts guardam o código publicado em group_code_raw e põem em group_code o código do alias, ou o publicado quando não se aplica nenhum alias.

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana (o nome da pasta de dados, por exemplo I-B) a que o alias se aplica. |
| `alias` | VARCHAR | Código tal como publicado, por exemplo PPD. |
| `group_code` | VARCHAR | Código correspondente, como listado em parliamentary_groups nessa legislatura. |
| `source_url` | VARCHAR | Referência para a correspondência. |
| `note` | VARCHAR | Porque existe o alias. |

### seed_attendance_codes

Lista mantida à mão dos códigos de presença e falta (siglaFalta) das listas de presenças do Plenário, uma linha por código, cada uma com a sua fonte. Os dados abertos não têm legenda. Cada significado foi confirmado comparando o código de cada deputado nos dados abertos com o rótulo que a página dessa reunião no parlamento.pt mostra (DetalheReuniaoPlenaria.aspx?BID=<meeting_id>, páginas consultadas a 20 de outubro de 2026), e com a Resolução da AR n.º 21/2009, que aprova o regime de presenças e faltas ao Plenário.

| Coluna | Tipo | Descrição |
|---|---|---|
| `code` | VARCHAR | Código tal como publicado (siglaFalta), por exemplo PR ou FJ. |
| `meaning` | VARCHAR | Significado do código. |
| `category` | VARCHAR | present (presença), other_body_or_mission (presença noutro órgão, em comissão autorizada pelo Presidente da AR ou em missão parlamentar), justified (falta justificada), missed_quorum_vote (falta ao quórum de votação), pending (falta ainda por justificar) ou unjustified (falta injustificada). |
| `pending_days` | BIGINT | Só no FA. Uma falta FA conta como pending enquanto a reunião tiver menos destes dias na data de atualização dos dados, e como unclassified a partir daí. Nunca como unjustified. |
| `source` | VARCHAR | Página da AR e documento de onde vem o significado. |

### stg_composicao_orgaos__plenary_attendance

ComposicaoOrgaos Plenario Reunioes, uma linha por pessoa na lista de presenças de uma reunião plenária. As reuniões sem lista não dão linhas. O motivo da falta (motivoFalta), texto livre que inclui doença, parentalidade e luto, não é lido.

| Coluna | Tipo | Descrição |
|---|---|---|
| `meeting_id` | BIGINT | Id da reunião na AR (Reuniao.reuId). |
| `meeting_number` | INTEGER | Número da reunião na legislatura (Reuniao.reuNumero). |
| `session_number` | INTEGER | Número da sessão legislativa (Reuniao.selNumero). |
| `meeting_date` | DATE | Data da reunião (Presencas.dtReuniao). |
| `meeting_type` | VARCHAR | Tipo de reunião (Presencas.tipoReuniao), Ordinária, Extraordinária, Solene ou Comemorativa. |
| `parliamentary_name` | VARCHAR | Nome parlamentar tal como na lista (nomeDeputado). |
| `group_acronym` | VARCHAR | Código do grupo tal como na lista (siglaGrupo). |
| `code` | VARCHAR | Código de presença ou falta (siglaFalta). |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
