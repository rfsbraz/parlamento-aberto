# Known gaps in the source

What the AR publishes, as of the full sync on 20 Oct 2026. These are gaps in the source, not in the pipeline, and we do not patch them by hand. `test_intervention_coverage_is_pinned` in `tests/test_interventions_questions.py` pins the first and last meeting date per legislature, so when AR fills a gap the test fails. Update the pin and this page together.

## Deputies and biographies

RegistoBiografico and AtividadeDeputado are listed on every legislature page, but most of those files are not that legislature's data (#23):

- RegistoBiografico: the files for Constituinte, I-A, I-B and IV to XVI, JSON and XML alike, repeat the current register of 339 people (335 in `RegistoBiograficoI`). Only II and III have real files, the older XML-shaped `RegistoBiograficoII/III_json.txt` listed on the I Legislatura page, with 432 and 454 people. XVII is the current register.
- AtividadeDeputado: every file holds the 1,446 people on the XVII list, tagged XVII. II and III come from `AtividadeDeputadoII/III_json.txt` on the I Legislatura page. IV to IX carry some activity dated in their own period; Constituinte, I-A and I-B carry none.
- The II and III files on their own pages are fetched and hashed but not stored (`copy_of: XVII` in `sources.yaml`). If one ever holds a record that is not in XVII, the data PR gets `hold: source-changed`.

The `deputies` mart takes biography fields from the latest legislature with a record for the person and names it in `biography_legislature`. People on the lists of each legislature (InformacaoBase) with a biography, from the 20 Oct 2026 data:

| Legislature | People | With a biography |
|---|---:|---:|
| Constituinte | 313 | 94 |
| I-A, I-B | 565 | 278 |
| II | 440 | 435 |
| III | 459 | 457 |
| IV | 417 | 243 |
| V | 417 | 165 |
| VI to XVI | 459 to 1,513 | 55 to 263 |
| XVII | 1,446 | 339 |

Not used yet: the Constituinte page lists a second `RegistoBiograficoConstituinte.xml` (530,619 bytes) in the older shape, with 313 people, 312 of them on the Constituinte lists. It is the only Constituinte biography source found. `AtividadeDeputadoCons.xml` on the same page is not readable XML.

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

## Votes

1,130 plenary votes are not unanimous and have no detail (`detalhe`), so the published record does not say how each group voted. 791 come from Iniciativas and 339 from Atividades, spread across every legislature from I to XVII. 445 have no description either. They stay in `votes` with their result, but have no rows in `vote_group_positions` or `vote_deputy_dissents`, and nothing is inferred for them. `test_non_unanimous_votes_without_detail_are_pinned` in `tests/test_committee_votes.py` pins this count.

4,705 committee votes (48% of the 9,723) are not unanimous and have no detail either, across 111 committees in VIII to XVII, most of them in XII (1,504) and XIII (1,691). 2,562 have no description. 638 say "sem votos contra" (no votes against) in the description, which does not say which groups voted for or abstained, so nothing is inferred from it. They stay in `votes` with no group rows. The same test pins this count.

Committee 8331 (Comissão de Agricultura e Pescas, XV) has 27 votes between 2022-04-26 and 2024-01-04. ComposicaoOrgaos XV publishes the committee and its 116 meetings, but its member history (`HistoricoComposicao`) is empty. None of the 27 votes needs inferred rows: 23 have a detail and 4 are not unanimous. `test_unanimous_committee_votes_have_a_composition` fails, naming the committee and vote, if a unanimous committee vote that needs inferred rows lands on a committee with no members.

## Seat counts

Per-day seat counts for Constituinte to VI are overstated. On some days `seated_on(d)` returns more deputies than the legislature has seats, because the source does not close some stand-in periods (#27). If you count deputies by date in those legislatures, expect too many.

- Constituinte to IV record no suspensions, and V and VI record only some. When a deputy comes back, often nothing ends the stand-in's period, so both stay effective until the stand-in's published end date, sometimes the end of the legislature.
- At the start of a legislature or a new government, some deputies keep an Efetivo period alongside the stand-ins seated for them on day one, with no suspension recorded.

Nothing is inferred to fix this: the source does not say which stand-in replaced whom. VII to XVII never pass the seats seed once swap days are handled. `test_seated_never_exceeds_seats_on_full_data` in `tests/test_seats.py` checks every day of every legislature, strictly for VII to XVII, and pins the maximum and the days over for Constituinte to VI, from the 20 Oct 2026 data:

| Legislature | Seats | Max seated | Days over |
|---|---:|---:|---:|
| Constituinte | no seed | 250 | |
| I-A | 263 | 271 | 1,178 |
| I-B | 250 | 254 | 249 |
| II | 250 | 257 | 891 |
| III | 250 | 258 | 887 |
| IV | 250 | 256 | 639 |
| V | 250 | 254 | 1,346 |
| VI | 230 | 232 | 746 |

If AR closes those periods, the test fails. Update the pin and this table together.
