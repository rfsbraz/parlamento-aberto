# Data dictionary

One page per mart in the data release, with column types and descriptions, known
quirks, and the staging models each mart is built from. Staging column descriptions
name the AR source field in parentheses, for example `(dtini)`.

Generated from `src/parlamento_aberto/models/schema.yml` by `uv run python -m parlamento_aberto.dictionary`. Do not edit by hand.

How to query a release: [querying.md](../querying.md).

## Marts

| Mart | Description |
|---|---|
| [legislatures](legislatures.md) | One row per legislature. |
| [sessions](sessions.md) | One row per legislative session. |
| [electoral_circles](electoral_circles.md) | One row per electoral circle per legislature. |
| [parliamentary_groups](parliamentary_groups.md) | One row per parliamentary group per legislature. |
| [coalitions](coalitions.md) | One row per legislature, coalition list and parliamentary group, from seed_coalitions. |
| [deputies](deputies.md) | One row per person (cadastro_id) who appears on any list, elected or not. |
| [mandates](mandates.md) | One row per deputy, legislature and situation period (DepSituacao), as published. |
| [group_memberships](group_memberships.md) | One row per deputy, legislature and parliamentary group period (DepGP). |
| [initiatives](initiatives.md) | One row per initiative. |
| [initiative_authors](initiative_authors.md) | One row per author of an initiative. |
| [votes](votes.md) | One row per vote id, from the Votacao arrays of Iniciativas events (plenary), of their Comissao entries (committee) and the VotacaoDebate arrays of Atividades (plenary). |
| [initiative_votes](initiative_votes.md) | Links plenary and committee votes to the initiatives and events they are published on. |
| [vote_group_positions](vote_group_positions.md) | One row per vote, group and position, from the parsed detail. |
| [vote_deputy_dissents](vote_deputy_dissents.md) | One row per deputy named in a vote detail, usually for voting apart from their group, or named as absent in the ausencias field of a vote without a detail. |
| [interventions](interventions.md) | One row per intervention in plenary, with debate, speaker and diary reference. |
| [questions](questions.md) | One row per pergunta or requerimento a deputy sent to government or another public body. |
| [question_authors](question_authors.md) | One row per question and author. |
| [question_recipients](question_recipients.md) | One row per question and recipient body. |
| [interest_declarations](interest_declarations.md) | One row per declaration in the register of interests, XI to XV. |
| [interests](interests.md) | One row per declared interest: activities and offices, social positions, societies, supports, services and other situations. |

## Licence and attribution

The data is published under CC BY 4.0 (`LICENSE-DATA`). The AR allows free reuse of
its open data as long as the source is credited. Credit it as:

> Fonte: Assembleia da República, dados abertos.

Terms: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx

Every CSV in a release starts with that line, and `manifest.json` carries it too.

Biographies, birth dates and interest registers are personal data. The marts carry
only what the AR publishes. See the main README to report wrong data.
