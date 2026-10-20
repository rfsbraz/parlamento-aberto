# mandates

One row per deputy, legislature and situation period (DepSituacao), as published. Who held a seat on day D is the seated_on(D) query, not a column; seated_during(D0, D1) gives the same for every day in a range, and the vote marts use it. AR periods for one person can overlap on a handover day, for example an Efetivo and a Suspenso period that both cover the same day. The rule: among a person's periods covering D, the one that starts latest wins, on a tie the longer one (an open end counts as longest) wins, and on a tie in both dates the effective one wins. The person is seated if that period is Efetivo, Efetivo Temporário or Efetivo Definitivo. On a swap day, when a circle has more deputies on D than on both D - 1 and D + 1, effective periods that end on D (with no effective period for the same person starting on D + 1) do not count, up to that excess and the number of people starting a seat on D. Counts for Constituinte to VI are still overstated on many days, see docs/known-gaps.md.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `mandates.parquet` and `mandates.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals. |
| `cadastro_id` | BIGINT | Person id, joins to deputies. |
| `deputy_id` | BIGINT | Id of this person in this legislature. |
| `circle_id` | INTEGER | Electoral circle the person ran in, joins to electoral_circles. |
| `situation` | VARCHAR | Situation as published, for example Efetivo, Suplente, Suspenso(Eleito). |
| `is_effective` | BOOLEAN | True for Efetivo, Efetivo Temporário and Efetivo Definitivo, the situations that hold a seat. |
| `start_date` | DATE | First day of the situation. |
| `end_date` | DATE | Last day of the situation, null while it is open. |

## Known quirks

- InformacaoBase lists everyone on the lists of a legislature, elected or not: 1,446 people for XVII at the 20 Oct 2026 sync, against 230 seats. Count seats from the is_effective periods that cover a date, not from rows of the lists. The old site counted every record as a deputy.
- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

### stg_informacao_base__deputies

InformacaoBase Deputados, one row per person on the lists of a legislature, elected or not.

| Column | Type | Description |
|---|---|---|
| `cadastro_id` | BIGINT | Person id shared across legislatures and datasets (DepCadId). |
| `deputy_id` | BIGINT | Id of this person in this legislature (DepId). |
| `full_name` | VARCHAR | Full name (DepNomeCompleto). |
| `parliamentary_name` | VARCHAR | Name used in parliament (DepNomeParlamentar). |
| `circle_id` | INTEGER | Electoral circle the person ran in (DepCPId). |
| `circle_name` | VARCHAR | Name of that electoral circle (DepCPDes). |
| `situations` | STRUCT(situation VARCHAR, start_date DATE, end_date DATE)[] | Situation periods (DepSituacao) as situation, start_date, end_date. |
| `groups` | STRUCT(group_id BIGINT, group_acronym VARCHAR, start_date DATE, end_date DATE)[] | Group memberships (DepGP) as group_id, group_acronym, start_date, end_date. |
| `legislature` | VARCHAR | Legislature in Roman numerals, from the file path. |
| `source_file` | VARCHAR | Normalised file the row was read from, relative to data/. |
