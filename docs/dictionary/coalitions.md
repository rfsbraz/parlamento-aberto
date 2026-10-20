# coalitions

One row per legislature, coalition list and parliamentary group, from seed_coalitions. Use it to read results by group: for example AD in XVII sits as PSD and CDS-PP, and CDU as PCP (and PEV until XIV). Parties that ran alone are not listed.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

Release files: `coalitions.parquet` and `coalitions.csv.gz`.

## Columns

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals. |
| `coalition` | VARCHAR | Short name the coalition is known by, for example AD or CDU. |
| `ballot_acronym` | VARCHAR | Acronym of the list on the ballot. |
| `coalition_name` | VARCHAR | Name of the coalition list. |
| `group_code` | VARCHAR | Parliamentary group, joins to parliamentary_groups on legislature and group_acronym. |
| `group_name` | VARCHAR | Name of that group in parliamentary_groups. |
| `source_url` | VARCHAR | Reference for the composition of the coalition. |
| `election_url` | VARCHAR | CNE page of the election, with the official results map. |
| `note` | VARCHAR | Exceptions, for example circles where the parties ran separately. |

## Known quirks

- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).

## Built from

Marts: [parliamentary_groups](parliamentary_groups.md).

### seed_coalitions

Hand-kept list of the electoral coalitions that won seats, one row per legislature, coalition list and parliamentary group it maps to, each row citing its source. Started from the old coalition_detector.py, keeping only coalitions that elected deputies and groups that exist in parliamentary_groups.

| Column | Type | Description |
|---|---|---|
| `legislature` | VARCHAR | Legislature in Roman numerals (the data folder name) the election filled. |
| `coalition` | VARCHAR | Short name the coalition is known by, for example AD or CDU. |
| `ballot_acronym` | VARCHAR | Acronym of the list on the ballot, for example PCP-PEV or PPD/PSD.CDS-PP. |
| `coalition_name` | VARCHAR | Name of the coalition list. |
| `group_code` | VARCHAR | Parliamentary group its deputies sat in, as listed in that legislature's parliamentary_groups. |
| `source_url` | VARCHAR | Reference for the composition of the coalition. |
| `election_url` | VARCHAR | CNE page of the election, with the official results map. |
| `note` | VARCHAR | Exceptions, for example circles where the parties ran separately. |
