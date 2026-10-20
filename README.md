# parlamento-aberto

Clean, versioned, documented open data about the Assembleia da República, rebuilt from the official open data dumps. The raw source lives in git under `data/`, so every change the AR makes shows up as a reviewable diff, and each data release publishes Parquet and CSV tables built from it.

Fonte: Assembleia da República, dados abertos.

The AR allows free reuse of its open data as long as the source is credited. Terms: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx

## Licences

- Code: MIT (`LICENSE`).
- Data: CC BY 4.0 (`LICENSE-DATA`), for everything under `data/` and the published marts.

## Personal data

Biographies, birth dates and interest registers are personal data. This repo republishes only what the AR publishes.

To report wrong data, open an issue with the [Correção de dados](../../issues/new?template=correcao-de-dados.yml) form. Personal-data removal requests can use the same form, or GitHub private vulnerability reporting once the repo is public. Please do not paste the personal data itself into a public issue.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python scripts/check_file_size.py
```

## Data releases

Each push to `main` that changes data or code builds the marts, runs every data test on `data/` and, if they pass, publishes a GitHub Release tagged `data-YYYY-MM-DD` (`-2`, `-3` for a second or third that day). Each release has one Parquet file and one gzipped CSV per mart, `manifest.json` and a `CHANGELOG.md` excerpt from `docs/data-changelog.md`. The first line of every CSV is a `#` comment with the attribution, so skip one line when reading (`skiprows=1` in pandas, `skip = 1` in R or DuckDB). A mart that loses more than 5% of its rows in a legislature against the previous release blocks the release unless `docs/data-changelog.md` acknowledges it. Publishing is off until the repo goes public (see `docs/repo-settings.md`).

To build the same assets locally:

```sh
uv run python -m parlamento_aberto.release build --data data --out dist --sha "$(git rev-parse HEAD)" --date "$(date +%F)"
```

## Fetching AR data

```sh
uv run python -m parlamento_aberto fetch                         # current legislature
uv run python -m parlamento_aberto fetch --all                   # every legislature
uv run python -m parlamento_aberto fetch --dataset iniciativas --legislature XVI
```

`sources.yaml` lists every file. The newest legislature in it is the current one. Requests go one at a time, with gzip, and retry the AR's temporary "Recurso Não Encontrado" pages with backoff. Run it after 06:00 Lisbon time; the AR server is slow between 04:00 and 06:00. Files whose download hash matches `data/_meta/sources.lock.json` are skipped. A download that is HTML, does not parse, or is empty where the last copy had records keeps the last good copy and is marked stale in the lock. `--raw-dir DIR` keeps the downloads outside the repo, and `--offline` replays them.

## Fetching the EpT register of interests

AR open data has the register of interests only up to XV. XVI and XVII declarations are at the Entidade para a Transparência (EpT), which has a public JSON API (#42). This is a private build: nothing from it is published yet.

```sh
uv run python -m parlamento_aberto.ept dry-run            # counts only, writes nothing
uv run python -m parlamento_aberto.ept fetch              # into data/ept_registo_interesses
uv run python -m parlamento_aberto.ept fetch --limit 5    # first 5 holders, for a quick check
```

It reads EpT entities 510 (Assembleia da República) and 4508 (Assembleia da República - XVII Legislatura): the titularidades, then each holder's declarations in every state, then each new or changed declaration. Requests go one at a time, at most one per second. On 20 Oct 2026 that was 881 titularidades, 695 holder searches and 1,424 declarations, so a full first run takes about an hour. A declaration is fetched again only when its state changes, and replaced or modified versions are kept under their own ids.

Each declaration is stripped in memory before anything is written. Only the metadata (ids, entity, role, holder, nature, state, related declaration, dates) and tab 4 (activities, associations, supports, services, societies, other situations) are kept. The holder's NIF, personal data, income and assets, and attachments are dropped, and any 9-digit number left in a value becomes `[removido]`.

The entity NIF/NIPC column of tab 4 keeps only a valid company NIPC: 9 digits (after dropping spaces, dots, dashes and a `PT` prefix), a valid mod-11 check digit, and a first digit of 5, 6, 8 or 9 or a prefix of 71, 72, 77 or 79. Anything else in that column is dropped: first digit 1 to 4 (people), any other 7x prefix, a failed check digit, or text.

A file with a `nif` key, a value in the personal range, or a 9-digit value outside the NIPC column is never written: the run stops instead. Two gitleaks rules in `.gitleaks.toml` check the same on `data/ept_registo_interesses/` and `tests/fixtures/ept/` (the check digit is left to the tests). Logs and the run report carry counts and ids only.

Layout: `data/ept_registo_interesses/titularidades.ndjson`, `declarations.ndjson` (the search results, by id) and `<entity id>/<id // 1000>/<id>.json` (one stripped declaration, tab 4 keyed by section GUID and column).

Sincronização semanal (#45): `.github/workflows/ept-sync.yml` corre à segunda-feira às 07:15 de Lisboa (06:15 no inverno), no ramo `data/ept`. Recolhe com `parlamento_aberto.ept fetch`, corre `python -m parlamento_aberto.ept_sync check` (falha com qualquer chave `nif`, valor da gama pessoal, valor de 9 dígitos fora da coluna NIPC ou ficheiro fora do formato) e só depois faz commit de `data/ept_registo_interesses`. Abre ou atualiza um único PR em rascunho, com `hold: new-dataset` e `hold: ept` e as contagens no corpo. O `data-merge.yml` só faz merge dos dados da AR, por isso este PR nunca entra no `main` sozinho, e um merge põe os dados da EpT no `main`. Cada declaração guarda `retrieved_at`, o dia (Lisboa) em que foi obtida; como só se volta a obter quando o estado muda, é o dia da primeira recolha desse estado.

The build reads the stored declarations into `stg_ept_registo_interesses__declarations` and `stg_ept_registo_interesses__items` (#46), with the same leading columns as the XI to XV staging tables. Only Deputado and Deputada declarations are read. The legislature comes from the Lisbon day of the office start (or of the submission when there is none), not from the EpT body, so entity 510 rows fall in XIV, XV or XVI. UTC dates become Lisbon days and the published values stay in the `_raw` columns. Replaced and modified versions stay as rows, linked by `supersedes_declaration_id`, `superseded_by_declaration_id` and `chain_root_declaration_id`, and `is_current` marks the newest published one with no successor. The NIPC column carries through as `entity_nipc`, valid company NIPCs only.

## Data dictionary

`docs/dictionary` has one page per mart, generated from `src/parlamento_aberto/models/schema.yml`. `docs/querying.md` shows how to query a release with DuckDB, pandas and R. After changing a model or its column descriptions, regenerate the pages; CI fails when they are out of date:

```sh
uv run python -m parlamento_aberto.dictionary
```

## Discover

Every Monday at 08:00 Lisbon, `.github/workflows/discover.yml` reads the AR open data pages and compares their JSON links with `sources.yaml`. New links for a known dataset, such as a new legislature, become a PR on `data/discover` labelled `hold: new-dataset`, which is never merged automatically. Removed links, files that match no dataset and pages it cannot read become one issue labelled `discover`. The `discover` block of `sources.yaml` lists what is left out on purpose. To run it locally (about 300 requests, two seconds apart):

```sh
uv run python -m parlamento_aberto.discover scan --scan scan.json
uv run python -m parlamento_aberto.discover diff --scan scan.json --report report.json
```

Design: `docs/design.md`. Repo settings: `docs/repo-settings.md`.
