# Known gaps in the AR source files

Findings about the parlamento.pt open data files that affect what goes into `sources.yaml`. Counts and ids only; no personal data is copied here.

## The six extra files listed under legislature I (#18)

The "I Legislatura" pages of three sections list six JSON files whose names say II or III. The links and sizes differ from the files of the same name on the II and III pages. On each page they come after a second "Definição da estrutura dos ficheiros" and `.xsd` entry, together with the matching `II.xml` and `III.xml` files.

Downloaded on 20 Oct 2026 (one request each, sequential, gzip):

| Listed under I | Bytes | SHA-256 (first 16) |
|---|---:|---|
| `AtividadeDeputadoII_json.txt` | 1,616,466 | `bee91d796d68cc0f` |
| `AtividadeDeputadoIII_json.txt` | 2,198,748 | `a467d185b52e7b42` |
| `RegistoBiograficoII_json.txt` | 456,728 | `bd44852b3c2f0347` |
| `RegistoBiograficoIII_json.txt` | 498,226 | `1dd5ab65b203412d` |
| `OrgaoComposicaoII_json.txt` | 315,438 | `9bdd7714a6a40e02` |
| `OrgaoComposicaoIII_json.txt` | 336,853 | `0d4ac781fa337a87` |

All six use an older shape: XML converted to JSON, with a `?xml` key, a single root element (`ArrayOfAtividadeDeputado`, `RegistoBiografico`, `OrganizacaoAR`) and camelCase field names (`depCadId`, `cadId`). The files on the II and III pages, and every other JSON file in `sources.yaml`, use the current shape: a top-level list or object with PascalCase names.

### OrgaoComposicaoII and III: older copies, keep excluded

They hold legislature II and III data, the same as the files on the II and III pages, but less of it:

| | Listed under I | On the II or III page | Overlap |
|---|---:|---:|---:|
| II: plenary members (`depCadId`) | 432 | 440 | 432 |
| II: committees | 30 | 30 | |
| II: last date | 1983-05-31 | 1983-05-30 | |
| III: plenary members | 454 | 459 | 454 |
| III: committees | 32 | 32 | |

Every member id in the extra files is also in the current file, which has a few more. Outcome (b) in #18: an older export of the same data. They stay out of `sources.yaml`.

### AtividadeDeputadoII/III and RegistoBiograficoII/III: the only copy of II and III data

These hold records that are missing from the files on the II and III pages:

| | Listed under I | On the II or III page | Overlap |
|---|---:|---:|---:|
| AtividadeDeputado II: deputies | 432, all with `legDes` II | 1,446, all with `LegDes` XVII | 2 |
| AtividadeDeputado II: dates | 3,479, from 1980-11 to 1983-05 | none before June 2025 | |
| AtividadeDeputado III: deputies | 454, all `legDes` III | 1,446, all `LegDes` XVII | 4 |
| AtividadeDeputado III: dates | 6,127, from 1983-05 to 1985-11 | none before June 2025 | |
| RegistoBiografico II: people (`cadId`) | 432 | 339 | 2 |
| RegistoBiografico III: people | 454 | 339 | 4 |

Legislature II ran from November 1980 to May 1983 and III from May 1983 to November 1985, which matches the extra files. The files on the II and III pages carry the current deputy list and register instead (see below). Outcome (c) in #18: these four files are the II and III data. The `RegistoInteresses` lists inside both RegistoBiografico files are empty.

### Related: current-shape AtividadeDeputado and RegistoBiografico are not per legislature

Checked across all 20 files of each in the 20 Oct download:

- Every AtividadeDeputado file, Constituinte to XVII, has the same 1,446 records keyed by `Deputado.DepCadId`, all with `Deputado.LegDes` XVII. Only X to XVII have activity entries tagged with their own legislature. Constituinte, I-A, I-B, II and III have no dates before June 2025.
- Every RegistoBiografico file has 335 to 339 people, and the union of all 20 files is 339 ids. The register is the same small set whatever legislature page it is on.

So per-legislature deputies and biographies for old legislatures are not in the current-shape files. For II and III they are in the extra files above. For other old legislatures, the `.xml` files on each page may be the source, which has not been checked.

## Decision needed

Adding the four II and III files needs code that #15 does not have yet:

- a dotted path to the record list (`ArrayOfAtividadeDeputado.AtividadeDeputado`, `RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb`), with ids `deputado.depCadId` and `cadId`;
- a source key that does not clash with the current-shape `II` and `III` entries, for example `part: xml`, giving `atividade_deputado/II-xml`;
- and a choice on whether the current-shape II and III files, which only repeat the XVII list, stay in `sources.yaml` at all.

`sources.yaml` and the fetcher arrive with #15, so these entries and their comments belong in a follow-up on top of it.
