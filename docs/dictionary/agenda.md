# agenda

Uma linha por evento da agenda parlamentar da legislatura atual, a partir de data/agenda_parlamentar/.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `agenda.parquet` e `agenda.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana, a atual. |
| `event_id` | BIGINT | Id do evento na AR. |
| `start_date` | DATE | Data de início. |
| `start_time` | TIME | Hora de início. Nulo quando a fonte não a publica. |
| `end_date` | DATE | Data de fim. |
| `end_time` | TIME | Hora de fim. Nulo quando a fonte não a publica. |
| `all_day` | BOOLEAN | Verdadeiro quando o evento é de dia inteiro. |
| `section` | VARCHAR | Secção da agenda. |
| `theme` | VARCHAR | Tema. |
| `body` | VARCHAR | Órgão. |
| `group_code` | BIGINT | Código do grupo parlamentar. |
| `title` | VARCHAR | Título. |
| `subtitle` | VARCHAR | Subtítulo. |
| `location` | VARCHAR | Local. |
| `text` | VARCHAR | Texto simples, a partir do InternetText, sem etiquetas HTML nem entidades por descodificar. |
| `link` | VARCHAR | Ligação. |
| `meeting_number` | VARCHAR | Número da reunião. |

## Particularidades conhecidas

- Só a legislatura atual entra. Os ficheiros da XV e da XVI são restos congelados da janela móvel da AR e ficam de fora ([lacunas conhecidas](../known-gaps.md)).
- O mart só responde a esta semana e o que já está anunciado, e só é útil com publicações diárias.
- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [legislatures](legislatures.md).

### stg_agenda_parlamentar__events

AgendaParlamentar, uma linha por evento da fonte. As contagens de linhas por legislatura batem com sources.lock.json. O ficheiro da AR é uma janela móvel, e os da XV e da XVI são restos congelados.

| Coluna | Tipo | Descrição |
|---|---|---|
| `event_id` | BIGINT | Id do evento na AR (Id). |
| `start_date` | DATE | Data de início (EventStartDate), no formato dd/mm/aaaa na fonte. |
| `start_time` | TIME | Hora de início (EventStartTime). Nulo quando a fonte não a publica. |
| `end_date` | DATE | Data de fim (EventEndDate), no formato dd/mm/aaaa na fonte. |
| `end_time` | TIME | Hora de fim (EventEndTime). Nulo quando a fonte não a publica. |
| `all_day` | BOOLEAN | Verdadeiro quando o evento é de dia inteiro (AllDayEvent). |
| `section` | VARCHAR | Secção da agenda (Section). |
| `theme` | VARCHAR | Tema (Theme). |
| `body` | VARCHAR | Órgão (OrgDes). |
| `group_code` | BIGINT | Código do grupo parlamentar (ParlamentGroup). |
| `title` | VARCHAR | Título (Title). |
| `subtitle` | VARCHAR | Subtítulo (Subtitle). |
| `location` | VARCHAR | Local (Local). |
| `internet_text` | VARCHAR | Texto da internet tal como publicado (InternetText), em HTML com entidades. |
| `text` | VARCHAR | Texto simples, a partir do InternetText, sem etiquetas HTML nem entidades por descodificar. |
| `link` | VARCHAR | Ligação (Link). |
| `meeting_number` | VARCHAR | Número da reunião (ReuNumero). |
| `legislature` | VARCHAR | Legislatura em numeração romana, a partir do caminho do ficheiro. |
| `source_file` | VARCHAR | Ficheiro normalizado de onde a linha foi lida, relativo a data/. |
