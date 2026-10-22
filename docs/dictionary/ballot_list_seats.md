# ballot_list_seats

Uma linha por eleição, círculo eleitoral e lista que ganhou pelo menos um lugar, com os lugares tal como publicados pela SGMAI, de 2009 (XI) a 2025 (XVII). Nada é calculado aqui. Liga a coalitions por legislature e ballot_acronym.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `ballot_list_seats.parquet` e `ballot_list_seats.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura que a eleição abriu, em numeração romana. |
| `election_date` | DATE | Data da eleição. |
| `circle_code` | VARCHAR | Código do círculo no ficheiro da SGMAI, com dois dígitos em 2009 e seis de 2011 em diante. |
| `circle_name` | VARCHAR | Nome do círculo tal como publicado. |
| `ballot_acronym` | VARCHAR | Sigla da lista tal como publicada, liga a coalitions.ballot_acronym. |
| `seats` | INTEGER | Lugares ganhos pela lista nesse círculo. |
| `source_url` | VARCHAR | Ficheiro da SGMAI de onde vem a linha. |

## Particularidades conhecidas

- Os ficheiros publicados pela SGMAI dizem "Escrutínio provisório". Em todas as eleições incluídas, a soma dos lugares é 230, como em seed_seats, e as listas de cada círculo somam o total de lugares que a SGMAI publica para esse círculo.
- Em 2022 a votação no círculo da Europa foi repetida. A linha vem do ficheiro com a repetição (AR_2022_Globais_REPEU.xlsx), cujo resultado elegeu os deputados da Europa.
- As listas sem lugares não constam. As eleições antes de 2009 ficam de fora: os ficheiros da SGMAI têm os lugares por lista nos círculos do território nacional, mas em formatos diferentes, e os dos círculos da emigração só existem em ficheiros à parte de 1995 a 2005.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### seed_ballot_list_seats

Lugares ganhos por cada lista em cada círculo eleitoral, tal como publicados pela SGMAI nos ficheiros de resultados de cada eleição para a Assembleia da República, de 2009 a 2025. Escrito por scripts/mai_list_seats.py a partir das colunas "mandatos"; não é editado à mão.

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura que a eleição abriu, em numeração romana. |
| `election_date` | DATE | Data da eleição. |
| `circle_code` | VARCHAR | Código do círculo no ficheiro da SGMAI. Em 2009 tem dois dígitos (por exemplo 01, 81); de 2011 em diante tem seis (010000, 800000). |
| `circle_name` | VARCHAR | Nome do círculo tal como publicado. |
| `ballot_acronym` | VARCHAR | Sigla da lista tal como publicada, por exemplo PPD/PSD.CDS-PP ou PCP-PEV. |
| `seats` | BIGINT | Lugares ganhos pela lista nesse círculo. |
| `source_url` | VARCHAR | Ficheiro da SGMAI de onde vem a linha. |
