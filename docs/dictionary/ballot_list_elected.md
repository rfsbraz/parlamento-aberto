# ballot_list_elected

Uma linha por deputado eleito, por eleição, círculo eleitoral e lista, de 1979 (I-B) a 1991 (VI), com o nome tal como publicado no Diário da República e o cadastro_id da AR. Liga a ballot_list_seats por legislature, circle_name e ballot_acronym, a coalitions por legislature e ballot_acronym, e a deputies por cadastro_id. Serve para contar quem foi eleito por cada lista, incluindo as coligações (AD, APU, FRS, CDU), qualquer que seja o grupo parlamentar em que a pessoa se sentou depois.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `ballot_list_elected.parquet` e `ballot_list_elected.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura que a eleição abriu, em numeração romana. |
| `election_date` | DATE | Data da eleição. |
| `circle_code` | VARCHAR | Número do círculo no mapa da CNE, com dois dígitos (01 a 22). Para comparar círculos entre eleições, use circle_name. |
| `circle_name` | VARCHAR | Nome do círculo, como em ballot_list_seats. |
| `ballot_acronym` | VARCHAR | Sigla da lista na grafia da SGMAI, como em ballot_list_seats; liga a coalitions.ballot_acronym. |
| `list_position` | INTEGER | Ordem do nome na relação da lista nesse círculo, a partir de 1. |
| `published_name` | VARCHAR | Nome tal como publicado na relação, depois das correções de leitura. |
| `cadastro_id` | BIGINT | Id de cadastro do deputado na AR, liga a deputies. Nulo quando não há correspondência. |
| `match` | VARCHAR | Como o cadastro_id foi encontrado, exact (nome completo igual), fuzzy (nome parecido, com círculo, lista e legislatura iguais), override (seed_ballot_list_elected_overrides) ou unmatched (sem deputado da AR atribuído). |
| `source_url` | VARCHAR | Ficheiro da CNE de onde vem a linha. |

## Particularidades conhecidas

- Em cada eleição, círculo e lista, o número de linhas é igual a ballot_list_seats.seats, sem exceções; o teste test_every_list_has_the_seats_of_ballot_list_seats confirma-o.
- Os nomes são lidos por OCR das digitalizações da CNE e publicados tal como na relação. As leituras erradas são corrigidas uma a uma em scripts/cne_elected_fixes.csv, conferidas com a digitalização. Os nomes da relação não são sempre os do cadastro da AR (nomes abreviados, apelidos em ordem diferente ou grafias antigas).
- O cadastro_id vem do nome completo da InformacaoBase de todas as legislaturas, sem acentos nem maiúsculas (match exact). Se não houver, aceita-se um nome parecido (primeiro e último nome com a mesma grafia ou uma grafia próxima) só quando o círculo, o partido ou a coligação e a legislatura coincidem com um deputado da AR (match fuzzy). Os restantes estão em seed_ballot_list_elected_overrides (match override, ou unmatched com cadastro_id nulo).
- Três eleitos não têm cadastro_id, porque o apelido impresso não é o do deputado da AR mais provável (ver a nota de cada um em seed_ballot_list_elected_overrides). Os eleitos não são os deputados em funções: quem foi para o governo continua aqui, e substituições, suspensões e renúncias estão em mandates.
- Na I-B, só contam os períodos dos grupos parlamentares entre 1980-01-03 e 1980-11-12, porque a AR publica a mesma lista para a I-A e a I-B (#85).
- A I-A (1976) fica de fora: o mapa da CNE de 1976 não tem siglas das listas, tem uma correção num ficheiro à parte, os círculos de então somam 263 lugares e não há linhas em ballot_list_seats com que comparar. Em 1976 nenhuma coligação elegeu deputados, só PS, PPD, CDS, PCP e UDP. Depois de 1991 não há relação de eleitos neste mart.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### seed_ballot_list_elected

Deputados eleitos por cada lista em cada círculo eleitoral nas eleições para a Assembleia da República de 1979 a 1991, tal como publicados no Diário da República (relação dos deputados eleitos), nas cópias publicadas pela CNE. Escrito por scripts/cne_elected.py, que lê os PDF por OCR, aplica as correções de leitura de scripts/cne_elected_fixes.csv e associa cada nome a um cadastro_id; não é editado à mão.

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura que a eleição abriu, em numeração romana. |
| `election_date` | DATE | Data da eleição. |
| `circle_code` | VARCHAR | Número do círculo no mapa da CNE, com dois dígitos (01 a 22), como em seed_ballot_list_seats. |
| `circle_name` | VARCHAR | Nome do círculo como em seed_ballot_list_seats. |
| `ballot_acronym` | VARCHAR | Sigla da lista como em seed_ballot_list_seats. |
| `list_position` | BIGINT | Ordem do nome na relação da lista nesse círculo, a partir de 1. |
| `published_name` | VARCHAR | Nome tal como publicado na relação. |
| `cadastro_id` | BIGINT | Id de cadastro do deputado na AR, nulo quando não há correspondência. |
| `match` | VARCHAR | Como o cadastro_id foi encontrado, exact, fuzzy, override ou unmatched. |
| `source_url` | VARCHAR | Ficheiro da CNE de onde vem a linha. |
