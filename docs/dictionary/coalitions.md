# coalitions

Uma linha por legislatura, lista da coligação e grupo parlamentar, a partir de seed_coalitions. Serve para ler resultados por grupo: por exemplo, a AD na XVII senta-se como PSD e CDS-PP, e a CDU como PCP (e PEV até à XIV). Os partidos que concorreram sozinhos não constam.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `coalitions.parquet` e `coalitions.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `coalition` | VARCHAR | Nome curto pelo qual a coligação é conhecida, por exemplo AD ou CDU. |
| `ballot_acronym` | VARCHAR | Sigla da lista no boletim de voto. |
| `coalition_name` | VARCHAR | Nome da lista da coligação. |
| `group_code` | VARCHAR | Grupo parlamentar, liga a parliamentary_groups por legislature e group_acronym. |
| `group_name` | VARCHAR | Nome desse grupo em parliamentary_groups. |
| `source_url` | VARCHAR | Referência para a composição da coligação. |
| `election_url` | VARCHAR | Página da CNE sobre a eleição, com o mapa oficial de resultados. |
| `note` | VARCHAR | Exceções, por exemplo círculos onde os partidos concorreram separados. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [parliamentary_groups](parliamentary_groups.md).

### seed_coalitions

Lista mantida à mão das coligações eleitorais que elegeram deputados, uma linha por legislatura, lista da coligação e grupo parlamentar correspondente, cada linha com a sua fonte. Partiu do antigo coalition_detector.py, mantendo só as coligações que elegeram deputados e os grupos que existem em parliamentary_groups.

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana (o nome da pasta de dados) preenchida pela eleição. |
| `coalition` | VARCHAR | Nome curto pelo qual a coligação é conhecida, por exemplo AD ou CDU. |
| `ballot_acronym` | VARCHAR | Sigla da lista no boletim de voto, por exemplo PCP-PEV ou PPD/PSD.CDS-PP. |
| `coalition_name` | VARCHAR | Nome da lista da coligação. |
| `group_code` | VARCHAR | Grupo parlamentar onde os seus deputados se sentaram, como listado em parliamentary_groups nessa legislatura. |
| `source_url` | VARCHAR | Referência para a composição da coligação. |
| `election_url` | VARCHAR | Página da CNE sobre a eleição, com o mapa oficial de resultados. |
| `note` | VARCHAR | Exceções, por exemplo círculos onde os partidos concorreram separados. |
