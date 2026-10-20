# Known gaps in the source

What the AR publishes, as of the full sync on 20 Oct 2026. These are gaps in the source, not in the pipeline, and we do not patch them by hand. `test_intervention_coverage_is_pinned` in `tests/test_interventions_questions.py` pins the first and last meeting date per legislature, so when AR fills a gap the test fails. Update the pin and this page together.

## Deputies and biographies

RegistoBiografico and AtividadeDeputado are listed on every legislature page, but most of those files are not that legislature's data (#23):

- RegistoBiografico: the files for Constituinte, I-A, I-B and IV to XVI, JSON and XML alike, are older snapshots of the XVII register: the same 339 people, with older content (335 people in `RegistoBiograficoI`). Only Constituinte, II and III have real files, all in the older shape: `RegistoBiograficoII/III_json.txt` listed on the I Legislatura page, with 432 and 454 people, and the older of the two `RegistoBiograficoConstituinte.xml` files on the Constituinte page (530,619 bytes, 313 people), the only file read as XML (`format: xml`, #28). XVII is the current register.
- AtividadeDeputado: every file is a snapshot of the XVII list, with the same 1,446 people tagged XVII and an older extract date than XVII. II and III come from `AtividadeDeputadoII/III_json.txt` on the I Legislatura page. IV to IX carry some activity dated in their own period; Constituinte, I-A and I-B carry none.
- These older snapshots are fetched and hashed but not stored (`copy_of: XVII` in `sources.yaml`): RegistoBiografico for Constituinte, I-A, I-B and II to XVI, and AtividadeDeputado for Constituinte, I-A, I-B, II and III. The check is on ids only, since the content is older than XVII by design. If one ever holds a record whose id is not in XVII, the data PR gets `hold: source-changed`. AtividadeDeputado IV to XVI stay stored for now.

The `deputies` mart takes biography fields from the latest legislature with a record for the person and names it in `biography_legislature`. People on the lists of each legislature (InformacaoBase) with a biography, from the 20 Oct 2026 data:

| Legislature | People | With a biography |
|---|---:|---:|
| Constituinte | 313 | 313 |
| I-A, I-B | 565 | 349 |
| II | 440 | 438 |
| III | 459 | 458 |
| IV | 417 | 249 |
| V | 417 | 172 |
| VI to XVI | 459 to 1,513 | 56 to 263 |
| XVII | 1,446 | 339 |

The older Constituinte register has birth dates for 38 of its 313 people.

Not used: `AtividadeDeputadoCons.xml` on the Constituinte page (267,833 bytes, link to `fich=AtividadeDeputadoX.xml`) is served corrupt. It comes as `text/xml` but is not XML, gzip or zip. No Constituinte activity file is read.

## Intervencoes

No file is published for the Constituinte, I (I-A, I-B) or III.

| Legislature | Legislature dates | First and last meeting with interventions | Gap |
|---|---|---|---|
| II | 1980-11-13 to 1983-05-30 | 1980-12-10 to 1982-04-25 | Only 98 records. Nothing after April 1982, and no meetings between 1981-04-25 and 1981-12-12 or between 1981-12-12 and 1982-04-01. |
| IV | 1985-11-04 to 1987-08-12 | 1985-11-04 to 1986-10-31 | Nothing for the last 9 months. |
| VII | 1995-10-27 to 1999-10-24 | 1996-10-16 to 1999-10-01 | Nothing for the first year, and no meetings between 1997-10-03 and 1998-09-16. |
| XII | 2011-06-20 to 2015-10-22 | 2013-09-16 to 2015-10-21 | Nothing before September 2013, about two years. |
| XIV | 2019-10-25 to 2022-03-28 | 2019-10-25 to 2022-03-22 | No meetings between 2020-09-10 and 2021-09-15. |
| XVII | 2025-06-03, running | 2026-09-16 to 2026-09-18 | Only 81 records, all from the 16 to 18 September 2026 sittings. |

Every other legislature (V, VI, VIII to XI, XIII, XV, XVI) runs from its first weeks to within about six weeks of its end, with no stretch over 100 days without a meeting other than VI's spring of 1992 (1992-04-09 to 1992-07-27).

AR also publishes 113 Intervencoes records with every key null, in V, XI, XIV, XV and XVI. Staging keeps them so the counts match `sources.lock.json`. The `interventions` mart drops them.

## PerguntasRequerimentos

Files start at VI. Nothing is published for earlier legislatures.

28 questions have a sent date (`DataEnvio`) whose year is outside their legislature, for example 0024, 2208 or 2909. Most are typos of the entry date. The `questions` mart keeps the published value in `sent_date_raw`, sets `sent_date` to null and `sent_date_invalid` to true. One requerimento in VII (id 16560) has no authors.

## The six extra files listed under legislature I (#18)

These are findings about files that `sources.yaml` leaves out, not gaps in the pipeline. Counts and ids only; no personal data is copied here.

The "I Legislatura" pages of three sections list six JSON files whose names say II or III. The links and sizes differ from the files of the same name on the II and III pages. On each "I Legislatura" page they sit next to `II.xml` and `III.xml` files of the same names, with no heading or note explaining them.

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

### Decision needed

Adding the four II and III files needs fetcher support that is not on main yet:

- a dotted path to the record list (`ArrayOfAtividadeDeputado.AtividadeDeputado`, `RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb`), with ids `deputado.depCadId` and `cadId`;
- a source key that does not clash with the current-shape `II` and `III` entries, for example `part: xml`, giving `atividade_deputado/II-xml`;
- and a choice on whether the current-shape II and III files, which only repeat the XVII list, stay in `sources.yaml` at all.

None of the six files has an entry in `sources.yaml`. The entries for the four (c) files, and a comment recording that the two OrgaoComposicao files stay out, go in #23.

## Votes

1,130 plenary votes are not unanimous and have no detail (`detalhe`), so the published record does not say how each group voted. 791 come from Iniciativas and 339 from Atividades, spread across every legislature from I to XVII. 445 have no description either. They stay in `votes` with their result, but have no rows in `vote_group_positions` or `vote_deputy_dissents`, and nothing is inferred for them. `test_non_unanimous_votes_without_detail_are_pinned` in `tests/test_committee_votes.py` pins this count.

4,705 committee votes (48% of the 9,723) are not unanimous and have no detail either, across 111 committees in VIII to XVII, most of them in XII (1,504) and XIII (1,691). 2,562 have no description. 638 say "sem votos contra" (no votes against) in the description, which does not say which groups voted for or abstained, so nothing is inferred from it. They stay in `votes` with no group rows. The same test pins this count.

Committee 8331 (Comissão de Agricultura e Pescas, XV) has 27 votes between 2022-04-26 and 2024-01-04. ComposicaoOrgaos XV publishes the committee and its 116 meetings, but its member history (`HistoricoComposicao`) is empty. None of the 27 votes needs inferred rows: 23 have a detail and 4 are not unanimous. `test_unanimous_committee_votes_have_a_composition` fails, naming the committee and vote, if a unanimous committee vote that needs inferred rows lands on a committee with no members.
