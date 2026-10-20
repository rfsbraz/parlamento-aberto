# Fiscaliza restart: open data pipeline and site

Status: approved 20 Oct 2026 (layout and merge policy).

## Why we are restarting

The old ingestion is the root problem. It parses the XML copy of the parlamento.pt dumps, runs 23 hand-written mappers, writes row by row through the ORM into 230 tables, and is driven by three different orchestrators on a heavy AWS stack. Every change in the source format breaks it, and the live site showed wrong numbers: 1,446 deputies for the XVII legislature, which has 230 seats.

The data itself is small. All JSON is 1.7 GB, and DuckDB reads it in seconds. Converting all initiatives and interventions (about 1 GB of JSON) to Parquet took 5 seconds and produced 33 MB. This is a batch problem, and we will treat it as one.

## Goals

- A public, versioned, documented set of clean datasets about the Assembleia da República, rebuilt daily from the official dumps, with the raw source in git so every AR change is a reviewable diff.
- Numbers you can defend. Every published table has tests that tie it back to the source and to known facts, such as 230 seats.
- Everything driven by CI/CD, with no server or database. Fiscaliza is one consumer. Running cost of zero, or close to it.

## Non-goals

- No live API in v1. People who want to query can point DuckDB, pandas or R at the Parquet files.
- No XML. The JSON and XML dumps carry the same content, and JSON is simpler to load.
- No historical correctness beyond what the source provides. Where the source is incomplete we flag it rather than patch it by hand, except for small seed tables that cite their source.
- DAR (the Diário) is out of v1. See the DAR section.

## Repo split

**Open data repo: `rfsbraz/parlamento-aberto`.** Created 20 Oct 2026 as a private repo. It goes public with the first data release, and that step needs Rodrigo's OK. It holds the pipeline code, the SQL models, the tests, the docs, the data dictionary and the normalised raw AR data. It starts with fresh history. CI runs gitleaks on every PR.

**Site repo.** The Fiscaliza site lives in a separate repo and only consumes the data releases.

**How the site consumes data.** The site never talks to parlamento.pt. Its build step downloads the latest data release, checks that the manifest's schema major version is one it supports, and generates static pages and per-legislature JSON shards from the Parquet files. A scheduled site workflow rebuilds once a day after the data run. If the schema check fails, the build fails and the previous deploy stays live. No cross-repo token is needed.

## Raw data in git

Raw AR files are stored in git as extracted, normalised text, never as ZIPs, so a data PR shows the records that changed. A sizing study (20 Oct 2026) settled the layout:

- Iniciativas XIII and IX are over GitHub's 100 MiB limit, and XVII is 94 MiB one year in, so one file per legislature fails.
- AR record order is unstable, and one NDJSON line per initiative can be 1.1 MB, which GitHub will not render.
- The per-record layout grew 22 to 43 KB per day over 25 replayed days. Estimate: 100 to 210 MB packed after a year, far below GitHub's 5 GB guidance. Git LFS is not needed and would hide diffs.
- Soft 404s are temporary (all 8 seen recovered within an hour). The server throttles between about 04:00 and 06:00 Lisbon time and serves gzip at about 10% of the size.

**Layout.** Everything lives under `data/`, keyed by dataset and legislature, with keys sorted and UTF-8 kept as is.

- **Nested, record-heavy datasets** (Iniciativas, and likely AtividadeDeputado and Peticoes): one pretty-printed, key-sorted JSON file per record, in folders bucketed by id, for example `data/iniciativas/XVII/377/377352.json`. A new vote on an initiative shows up in the PR as the vote fields.
- **Flat datasets** (Intervencoes, PerguntasRequerimentos, Agenda, InformacaoBase tables and similar): NDJSON with sorted keys, records in natural-id order, split into fixed id or year ranges so a record never moves between files. Each file stays under 50 MB.
- No file may get near 100 MB. CI fails any PR that adds a file over 50 MB.
- `data/_meta/sources.lock.json` records, per source file: the SHA-256 of the last good download, its fetch date, record count, top-level key fingerprint and stale status. It is what the change report and the validation rules compare against.

Fetches of unchanged files produce byte-identical output, so they add nothing to history. The DAR ZIPs and 67 smaller files still need sizing; the fetch PR measures them first.

## Where the published data lives

Decision: **GitHub Releases on the open data repo**, one release per merge that changes data, tagged `data-YYYY-MM-DD` (with a suffix if there are two in a day).

Reasoning: free with no egress charge, next to the code and data that produced it, immutable and citable, and "latest release" is a stable entry point. All marts in Parquet are estimated under 200 MB. While private, the nightly run fits in the 2,000 free Actions minutes a month.

Each release contains:
- one Parquet file per mart, plus a gzipped CSV of each mart for spreadsheet users;
- `manifest.json` with schema version, build time, the data commit SHA it was built from, row counts per mart and per legislature, and the SHA-256 and fetch date of every source file used;
- a `CHANGELOG.md` excerpt for schema changes.

Raw snapshots are no longer archived as release assets. Git history is the archive, and the commit SHA in the manifest is enough to rebuild any release. R2 and Hugging Face are not used in v1; Hugging Face can be added later as a mirror in one small PR.

The site goes on Cloudflare Pages (free tier, 20,000 files per deploy), pre-rendering deputies, parties and legislatures and loading initiatives and votes client-side from shards.

## Licences

**Source terms.** The parlamento.pt open data page says the data "podem ser livremente reutilizados por qualquer instituição ou pessoa para a criação de novos conteúdos, devendo apenas ser mencionada a fonte (Assembleia da República)". Source: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx (checked 17 Oct 2026). The only condition is attribution.

**Data: CC BY 4.0**, for both the normalised raw files in `data/` and the published marts, with the attribution passed through ("Fonte: Assembleia da República, dados abertos") in the README, the manifest and every CSV header comment.

**Code: MIT**, since AGPL discourages reuse of a small pipeline. The site repo keeps AGPL-3.0.

**Personal data.** Biographies, birth dates and interest registers are personal data. We republish only what the AR publishes and give a correction contact in the README. A cost of raw data in git: once public, removing a record from history needs a rewrite. If the AR drops a record we delete it going forward, and rewrite history only if a request requires it.

## Pipeline

One Python package, run with `uv`, using DuckDB. Models are plain SQL files run in order by a small runner, with column descriptions in YAML that also generate the data dictionary. No dbt: about 20 models do not need it.

1. **Fetch.** `sources.yaml` lists every dataset URL per legislature. Requests are sequential, ask for gzip, send a clear User-Agent and retry with backoff. A soft 404 is retried within the run; if it persists, the last good copy stays and the file is marked stale.
2. **Validate.** There is no ETag or Last-Modified, so every download is hashed. A file is rejected, keeping its last good copy and marked stale, if it is HTML, fails to parse, or is `[]` or `null` where the last good copy had records. Accepted files are checked against the lock: a record-count drop over 5% or a changed top-level key set is allowed through but puts the PR on hold.
3. **Normalise.** Accepted files are written into the layout above. Records that disappear from the source are deleted and counted as removed.
4. **Data PR.** If anything under `data/` changed, the workflow commits to the `data/nightly` branch and opens or updates one PR. The body carries the change report: per dataset and legislature, records added, removed and changed, plus stale files and how long they have been stale.
5. **Merge policy.** Data PRs auto-merge when all checks pass. A PR with a row drop over 5%, a schema or key-set change, a new dataset or legislature, or an older snapshot of the XVII register that now holds an id outside XVII (`hold: source-changed`, #23) gets a `hold:` label, auto-merge is not enabled, and Rodrigo merges it. While a held PR is open, later runs add commits to the same branch and refresh the report, so nothing is force-pushed.
6. **Stage and marts on merge.** Merging to main triggers the build: one staging model per dataset reading the normalised files with an explicit column list, so type drift between legislatures cannot change the schema; then the marts; then all data tests.
7. **Publish.** If the tests pass, write Parquet and CSV, build the manifest and create the release. If a test fails, no release is made and the previous one stays latest.

The run fails, which emails Rodrigo, if a current-legislature core file (InformacaoBase, Iniciativas, Atividades, Intervencoes) has been stale for more than 7 days.

**Bot identity.** PRs opened with the default `GITHUB_TOKEN` do not trigger CI, and merges made with it do not trigger the publish workflow. The workflows need a GitHub App installed on the repo (or a fine-grained token) stored as a repository secret. Rodrigo creates and stores it; the value never goes into git or chat.

**Schedules (Europe/Lisbon, all after the AR's 04:00 to 06:00 slow window).**
- Nightly run: daily after 06:00. Only the current legislature, which is always the newest in `sources.yaml` (XVII today), so a new one becomes current with no code change.
- Full sync: monthly on the 3rd at 06:30 Lisbon, every legislature, with hashing skipping unchanged files. The nightly run skips the 3rd.
- Manual: a `workflow_dispatch` input runs the full sync by hand, optionally limited to one dataset or one legislature.
- Catch-up run: about 09:30, re-fetching only files marked stale.
- Discover: weekly, Monday 08:00. New links become a held PR to `sources.yaml`, or an issue if they need a decision.
- Site rebuild: daily at 11:00.

The nightly run and the full sync share the same branch, PR, change report and merge rules. A full-sync PR that changes past legislatures also gets an informational `historical-change` label, which does not hold it on its own.

## First marts

The old mappers in `scripts/data_processing/mappers/` and the two analysis docs are the field spec. Where they disagree with the JSON, the JSON wins and we note it in the dictionary.

- **legislatures**, **sessions**, **electoral_circles**: from InformacaoBase.
- **deputies**: one row per person (`cadastro_id`), names and biography from RegistoBiografico.
- **mandates**: one row per deputy per legislature per situation period (Efetivo, Suplente, Suspenso and so on), from `DepSituacao`. "Seated on date D" is a query on this table, not a column.
- **parliamentary_groups** and **group_memberships**: from `GruposParlamentares` and `DepGP`. Open memberships carry the extract date as their end date rather than null, so staging treats an end date on or after the extract date as open.
- **coalitions**: a hand-kept seed CSV (AD, CDU, PàF and so on) mapping electoral coalitions to the groups that sit in parliament, each row citing a source. The old `coalition_detector.py` is the starting list.
- **initiatives** and **initiative_authors**: from Iniciativas.
- **votes**: one row per vote id, from the `Votacao` arrays in Iniciativas events and in Atividades, with result, date, meeting and a `unanimous` flag. Vote ids repeat across events (30,708 records, 30,700 distinct ids), so we deduplicate by id.
- **vote_group_positions**: parsed from the `detalhe` string, one row per vote, group and position (favour, against, abstention, absent). The strings look like `A Favor: <I>PS</I>, <I> PSD</I><BR>Contra:<I>PCP</I>`, and newer ones add dissenters as `2-PS, Carlos Silva (PS), Fátima Correia Pinto (PS)`. The parser strips the markup, splits on `<BR>`, and emits group rows plus a dissent count. Where a vote is unanimous and has no detail, we emit favour rows for every group seated that day and mark them `inferred = true`.
- **vote_deputy_dissents**: the named individuals from the same strings, matched to `cadastro_id` by parliamentary name and group within the legislature. Unmatched names stay with a null id and are counted in tests.
- **interventions**: from Intervencoes, with debate, speaker and publication reference.
- **questions**: perguntas and requerimentos, from PerguntasRequerimentos.
- **interests**: from RegistoInteresses, in the versions the old mapper handles (v1 to v3).

## Testing and proving the counts

Unit tests run on committed fixtures in the layout above, so code PRs never depend on live downloads. Data tests run on every build and block the release if they fail.

- **Seats.** A seed table holds the seat count of each legislature with its source. For every legislature and sampled date, deputies with an open Efetivo situation must be at or below the seat count, and at the extract date of the current legislature it must equal it.
- **Known results.** For XVII at the 2026-10-16 extract, the seated split must be PSD 89, CH 60, PS 58, IL 9, L 6, PCP 3, CDS-PP 2, BE 1, PAN 1, JPP 1. This matches the 2025 election.
- **Parser coverage.** Every `detalhe` string is fully consumed by the vote parser, and every group code it finds exists in that legislature's groups.
- **Joins.** Every author, speaker and dissenter id resolves to a deputy, and unmatched names stay under a small threshold per legislature.
- **Drift.** Row counts per mart per legislature are compared with the previous release, and a drop over 5% blocks publishing unless it is acknowledged in the changelog.

**Verified** (17 Oct download, 20 Oct sizing study): InformacaoBase XVII has 1,446 deputy records, of which 230 have an open Efetivo situation with the split above, so the old site counted every candidate. 28,941 of 30,708 vote records have a `detalhe` string, using only A Favor, Contra, Abstenção and Ausência. Iniciativas XVII (soft 404) and Intervencoes XVII (`[]`) on 17 Oct had both recovered by 20 Oct. There is no RegistoInteresses file for XVI or XVII.

## DAR later

The Diário (from XI on, as ZIPs) is the richest source and the most work, so it comes after v1: a monthly workflow extracting text per sitting into `dar_sittings` and `dar_pages`, after a spike on size and format.
