# Entidade para a Transparência (EpT): register of interests for XVI and XVII

The AR open data has `RegistoInteresses` files only up to XV. From XVI on, deputies file their declarations with the Entidade para a Transparência under Lei n.º 52/2019, and the AR publishes none. This page records what we decided, what the EpT API returns, and what we never store. Plan and build order: #42 (issues #43 to #49).

## Decision (Rodrigo, 20 Oct 2026)

- Build it privately. XVI and XVII declarations are normalised into the same `interest_declarations` and `interests` marts as XI to XV, with `source = 'ept'`.
- No publication. EpT rows do not go into a release, the site or any public copy of the repo until Rodrigo decides.
- No contact with the EpT beyond one email asking whether personal NIFs may be reused. Nothing else is sent until Rodrigo decides.
- Company NIPCs are stored (changed later on 20 Oct 2026). From the tab 4 entity NIF/NIPC column we keep a value only when it is a company NIPC: see [Company NIPCs](#company-nipcs). Every other value in that column is dropped.
- Personal NIFs stay out: the holder's top-level `nif` is never stored, and neither is a personal NIF in the entity column. This waits on the EpT's answer about reuse. If the EpT confirms reuse is allowed, the decision is revisited.
- The `ept_registo_interesses` data PR is held for Rodrigo (new dataset, `hold:` label) and never auto-merges.
- **Publication scope: pending Rodrigo's decision.** The legal question below has to be settled before the repo or any EpT-derived data goes public.

## Legal limits: Lei n.º 52/2019, art. 17.º

Text as consolidated after Lei n.º 58/2021 and Lei n.º 4/2022 ([pgdlisboa.pt](https://pgdlisboa.pt/leis/lei_mostra_articulado.php?nid=3192&tabela=leis)).

- n.º 1: the declarations are of public access, on the terms of the article.
- n.º 2: never public: (a) address, civil and tax identification numbers, phone numbers and email; (b) in the register of interests, the detail of services provided under professional secrecy; (c) data that identify the residence (other than the municipality) or vehicles.
- n.º 3 and n.º 5: income and assets (tab 3) can only be consulted on a reasoned, identified request, with no right to reproduce them.
- n.º 4: the register of interests fields are published on the EpT site and on the site of the body the holder belongs to.
- n.º 14: apart from n.º 4, the declaration cannot be disclosed, namely on a website or social network.

Open question: whether republishing the register of interests fields, which n.º 4 makes public, is covered by n.º 4 or barred by n.º 14. Until it is answered, everything here stays private.

## What we never store

The fetcher strips these in memory, before anything is written to disk, a log or CI output:

- the holder's NIF, the top-level `nif` field of `getdeclaration`;
- any value in the entity NIF/NIPC column of a tab 4 section that is not a company NIPC under the rule below (the column numbers are listed in the tab 4 table);
- any 9-digit number in any other kept value, replaced before writing;
- tab 2 (personal data: identification, address, contacts, spouse);
- tab 3 (income and assets);
- attachments.

The raw `getdeclaration` response is never kept. Fixtures are synthetic or scrubbed, and tests fail if a `nif` key shows up, or a 9-digit value anywhere other than a valid company NIPC in the entity NIF/NIPC column, in a fixture, a seed or a normalised file.

### Company NIPCs

A value from the entity NIF/NIPC column is kept only if all of these hold:

- it is exactly 9 digits;
- its check digit is valid (mod 11: weight the first 8 digits 9 down to 2 and sum; if the sum mod 11 is 0 or 1 the check digit is 0, otherwise it is 11 minus the remainder);
- it starts with 5, 6, 8 or 9, or with 71, 72, 77 or 79 (legal persons, public bodies and other non-individual entities).

Everything else in the column is dropped: a first digit of 1, 2, 3 or 4 (individuals), any other prefix starting with 7, an invalid check digit, and any value that is not 9 digits.

## API

Base `https://api.entidadetransparencia.pt`. Every call is an unauthenticated `POST` with a JSON body and `Content-Type: application/json`; the portal also sends `Origin: https://entidadetransparencia.pt`. Responses are an envelope `{code, description, messageId, externalMessageId, data}`, with `code` 0 on success. We poll at no more than 1 request per second.

| Path | Body | Returns |
|---|---|---|
| `/publicquery` | `{EntityId, RoleId, HolderId, pageNumber, pageSize, sortBy}` | Titularidades (holder in a role at a body): `id`, `entityId`, `roleId`, `holderId`, `entity`, `role`, `holder`, `beginDate`, `endDate`, paged with `pageNumber`, `pageSize`, `pageCount`, `total`. |
| `/publicquery/getallentities` | `{}` | Every body as `{value, label}` (4,461 on 20 Oct 2026). |
| `/publicquery/getallroles` | `{EntityId}` | Roles at a body as `{value, label}`. |
| `/publicquery/getallholders` | `{EntityId, RoleId}` | Holders as `{value, label}`; `value` is the EpT holder id. |
| `/publicquery/search` | `{HolderId, EntityId: [...], RoleId: [...], pageNumber, sortBy}` | A holder's declarations: `id`, `natureType`, `stateType`, `deliveryDate`, `relatedDeclarationId`. |
| `/publicquery/getdeclaration` | `{Id, isDraft: false}` | One declaration: metadata (`id`, `natureType`, `stateType`, `relatedDeclarationId`, `entity`, `role`, `holder`, `holderId`, `entityId`, `roleId`, `startDate`, `endDate`, `submitedDate`, `unavailableSections`), the holder's `nif`, and `data.value`, the tabs keyed by GUID. |

Bodies and roles for the AR:

| EntityId | Label | Covers | Roles |
|---|---|---|---|
| 510 | Assembleia da República | Titularidades before XVII (from 2021, so XIV to XVI) | Deputado 8, Deputada 232, Presidente da Assembleia da República 2, Vice-Presidente 13, Vogal 18 |
| 4508 | Assembleia da República - XVII Legislatura | XVII | Deputado 8, Deputada 232, Presidente 12, Presidente da Assembleia da República 2 |

On 20 Oct 2026 entity 4508 had 322 titularidades and 510 had 559; 263 and 427 distinct holders as Deputado or Deputada, 506 together. The same holder id is used at both bodies.

Enumerations, from the portal code:

- `natureType`: 1 initial, 2 modification, 4 cessation, 8 final, 16 replace, 32 reElection.
- `stateType`: 1 draft, 2 pendingVerification, 4 notPublished, 8 published, 16 canceled, 32 modified, 64 replaced.

Dates are ISO strings in UTC (`2025-06-01T23:00:00Z` is 2 June in Lisbon). We keep the raw value and convert to the Europe/Lisbon day.

The portal's declaration URLs (`entidadetransparencia.pt/titularidades/<ids>/declaracoes/<id>`) carry ids encrypted in the browser with a random salt, so there is no stable public URL to link to.

### Tab 4: register of interests

Tab 4 is the GUID `1483a8d1-adca-4f39-8038-98cc6f728fcb`. Its one group holds six sections, each a list of rows whose cells are keyed `<section GUID>-colN` and carry `value` and `isVisible`. We keep only visible cells of the columns below.

| Section GUID | Category | Label | Kept columns | NIF/NIPC column (company NIPCs kept, the rest dropped) |
|---|---|---|---|---|
| `2c6d9562-dea5-488b-9afe-42519c636daf` | activity | Atividades profissionais, cargos públicos, privados e sociais | col1 to col7 | col9 |
| `cd0e811a-d9bb-49ee-b0f0-1dae0680eb22` | association | Filiação ou funções em entidades de natureza associativa | col1 to col7 | col8 |
| `62fb0107-a68d-4ba2-822b-bc8adc54369b` | support | Apoios ou benefícios | col1 to col5, col7 to col9 | col6 |
| `b1f8c095-fe0c-4bb3-b493-902dc0c31232` | service | Serviços prestados | col1 to col5, col7, col8 | col6 |
| `9b58c917-b14c-4eed-9b3c-40c3d99d45da` | society | Sociedades | col1 to col6, col8 | col7 |
| `fd85f91f-2803-41bc-b315-ede3a4a66d4e` | other_situation | Outras situações | col1 to col4, col6 | none |

An unknown section GUID is an error, not a skip, so a change in the form is noticed. EpT publishes Remuneração as `1` or `0` without documenting it, so it is kept as `paid_raw` and `is_paid` stays null.

## Matching holders to AR deputies

EpT has no AR id. `seed_ept_holders` (#47) maps each EpT holder id to a `cadastro_id` by normalised full name against InformacaoBase (XVII for entity 4508, XIV to XVI for 510), with a hand-kept override for every holder the name match leaves unmatched or ambiguous. RegistoBiografico XVI is a copy of the XVII register (see [known-gaps](../known-gaps.md)), so it is not used for 510.

## Build order

1. #43: this page.
2. #44: fetcher for entities 510 and 4508, metadata and tab 4 only, stripped in memory.
3. #46: staging parser.
4. #45: the `ept_registo_interesses` data-sync dataset, held for Rodrigo.
5. #47: holder to `cadastro_id` crosswalk seed.
6. #48: the unified marts.
7. #49: dictionary, known-gaps and release notes.
