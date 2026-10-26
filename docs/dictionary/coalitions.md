# coalitions

Uma linha por legislatura, lista da coligação e grupo parlamentar, a partir de seed_coalitions. Serve para ler resultados por grupo: por exemplo, a AD na XVII senta-se como PSD e CDS-PP, e a CDU como PCP (e PEV até à XIV). Os partidos da lista sem lugares também constam, com has_seats falso, por exemplo o PEV na CDU da XV à XVII. Os partidos que concorreram sozinhos não constam.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `coalitions.parquet` e `coalitions.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `coalition` | VARCHAR | Nome curto pelo qual a coligação é conhecida, por exemplo AD ou CDU. |
| `ballot_acronym` | VARCHAR | Sigla da lista no boletim de voto. |
| `coalition_name` | VARCHAR | Nome da lista da coligação. |
| `group_code` | VARCHAR | Grupo parlamentar, liga a parliamentary_groups por legislature e group_acronym. Nas linhas com has_seats falso, a sigla do partido. |
| `group_name` | VARCHAR | Nome desse grupo em parliamentary_groups. Nulo quando has_seats é falso. |
| `source_url` | VARCHAR | Referência para a composição da coligação. |
| `election_url` | VARCHAR | Página da CNE sobre a eleição, com o mapa oficial de resultados. |
| `note` | VARCHAR | Exceções, por exemplo círculos onde os partidos concorreram separados. |
| `has_seats` | BOOLEAN | Verdadeiro quando o partido elegeu deputados por esta lista; falso quando a lista não lhe deu nenhum lugar, mesmo que tenha grupo por lugares ganhos noutra lista, como o CDS-PP na lista dos Açores na XVII. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [parliamentary_groups](parliamentary_groups.md).

### seed_coalitions

Lista mantida à mão das coligações eleitorais que elegeram deputados, uma linha por legislatura, lista da coligação e grupo parlamentar correspondente, cada linha com a sua fonte. Partiu do antigo coalition_detector.py, mantendo só as coligações que elegeram deputados. Os partidos da lista que não elegeram ninguém têm a sua própria linha, com has_seats falso.

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana (o nome da pasta de dados) preenchida pela eleição. |
| `coalition` | VARCHAR | Nome curto pelo qual a coligação é conhecida, por exemplo AD ou CDU. |
| `ballot_acronym` | VARCHAR | Sigla da lista no boletim de voto, por exemplo PCP-PEV ou PPD/PSD.CDS-PP. |
| `coalition_name` | VARCHAR | Nome da lista da coligação. |
| `group_code` | VARCHAR | Grupo parlamentar onde os seus deputados se sentaram, como listado em parliamentary_groups nessa legislatura. Nas linhas com has_seats falso, a sigla do partido. |
| `source_url` | VARCHAR | Referência para a composição da coligação. |
| `election_url` | VARCHAR | Página da CNE sobre a eleição, com o mapa oficial de resultados. |
| `note` | VARCHAR | Exceções, por exemplo círculos onde os partidos concorreram separados. |
| `has_seats` | BOOLEAN | Verdadeiro quando o partido elegeu deputados por esta lista; falso quando a lista não lhe deu nenhum lugar, mesmo que tenha grupo por lugares ganhos noutra lista, como o CDS-PP na lista dos Açores na XVII. |
