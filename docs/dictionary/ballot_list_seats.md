# ballot_list_seats

Uma linha por eleição, círculo eleitoral e lista que ganhou pelo menos um lugar, com os lugares tal como publicados pela CNE, de 1979 (I-B) a 2005 (X), e pela SGMAI, de 2009 (XI) a 2025 (XVII). Nada é calculado aqui. Liga a coalitions por legislature e ballot_acronym.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `ballot_list_seats.parquet` e `ballot_list_seats.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura que a eleição abriu, em numeração romana. |
| `election_date` | DATE | Data da eleição. |
| `circle_code` | VARCHAR | Código do círculo no ficheiro de origem, com dois dígitos até 2009 (01 a 22 na CNE) e seis de 2011 em diante. Para comparar círculos entre eleições, use circle_name. |
| `circle_name` | VARCHAR | Nome do círculo tal como publicado. |
| `ballot_acronym` | VARCHAR | Sigla da lista na grafia da SGMAI, liga a coalitions.ballot_acronym. |
| `seats` | INTEGER | Lugares ganhos pela lista nesse círculo. |
| `source_url` | VARCHAR | Ficheiro da CNE ou da SGMAI de onde vem a linha. |

## Particularidades conhecidas

- Os ficheiros publicados pela SGMAI dizem "Escrutínio provisório". Em todas as eleições incluídas, a soma dos lugares é a de seed_seats (250 até 1987 e 230 desde 1991), e as listas de cada círculo somam o total de lugares publicado para esse círculo.
- De 1979 a 2005 os lugares vêm dos mapas da CNE, que têm os 22 círculos; os ficheiros da SGMAI desses anos não têm os círculos da emigração até 1991. Em cada círculo, o método de Hondt aplicado aos votos publicados dá os lugares publicados, e nos círculos do território nacional os lugares por lista coincidem com os ficheiros da SGMAI.
- As siglas dos mapas da CNE seguem a grafia da SGMAI e de coalitions: PSD (1979 e 1980) passa a PPD/PSD, CDS/PP (1995 a 2002) a CDS-PP e PCP/PEV (1991 a 2002) a PCP-PEV.
- Em 1983, no círculo Fora da Europa (2 lugares), o mapa da CNE dá também um lugar ao PS. O mapa publicado no Diário da República (I série, n.º 121, de 26 de maio de 1983, suplemento) elegeu um deputado do PPD/PSD e um do CDS, e é esse que aqui se segue.
- Em 2022 a votação no círculo da Europa foi repetida. A linha vem do ficheiro com a repetição (AR_2022_Globais_REPEU.xlsx), cujo resultado elegeu os deputados da Europa.
- As listas sem lugares não constam. A Assembleia Constituinte (1975) e a I-A (1976) ficam de fora.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

### seed_ballot_list_seats

Lugares ganhos por cada lista em cada círculo eleitoral nas eleições para a Assembleia da República, de 1979 a 2005 tal como publicados pela CNE nos mapas de resultados, e de 2009 a 2025 tal como publicados pela SGMAI nos ficheiros de resultados. Escrito por scripts/mai_list_seats.py a partir das colunas "Md" da CNE e "mandatos" da SGMAI; não é editado à mão.

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura que a eleição abriu, em numeração romana. |
| `election_date` | DATE | Data da eleição. |
| `circle_code` | VARCHAR | Código do círculo no ficheiro de origem. Até 2005 é o número do círculo no mapa da CNE, com dois dígitos (01 a 22). Na SGMAI, em 2009 tem dois dígitos (por exemplo 01, 81); de 2011 em diante tem seis (010000, 800000). |
| `circle_name` | VARCHAR | Nome do círculo tal como publicado. |
| `ballot_acronym` | VARCHAR | Sigla da lista tal como publicada, por exemplo PPD/PSD.CDS-PP ou PCP-PEV. As siglas da CNE seguem a grafia da SGMAI (PSD passa a PPD/PSD, CDS/PP a CDS-PP e PCP/PEV a PCP-PEV). |
| `seats` | BIGINT | Lugares ganhos pela lista nesse círculo. |
| `source_url` | VARCHAR | Ficheiro da CNE ou da SGMAI de onde vem a linha. |
