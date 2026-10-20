# Test fixtures

`data/` follows the layout in `docs/design.md`, so the models read it the same way they read the real `data/` folder. Tests never touch the network.

## Source and extract date

- `data/informacao_base/XVII/`: InformacaoBase XVII (`InformacaoBaseXVII_json.txt`), downloaded from parlamento.pt on 20 Oct 2026. The extract date is **2026-10-19**: AR writes it as the end date of every open group membership, and `legislatures.extract_date` reads it from there.
- `data/registo_biografico/XVII/`: shape taken from RegistoBiografico XVII, downloaded the same day. The content is synthetic (see below).
- `data/iniciativas/`, `data/atividades/XVII/` and `data/informacao_base/XIV/`: Iniciativas XIV, XVI and XVII, Atividades XVII and InformacaoBase XIV, downloaded from parlamento.pt on 20 Oct 2026 in a full sync. These files carry no extract date; the newest vote in Iniciativas XVII is dated 2026-10-16. Used by the initiatives and votes marts.

## How they were built

1. One table per file: `CirculosEleitorais`, `DetalheLegislatura`, `GruposParlamentares`, `SessoesLegislativas` and `Deputados` each became an NDJSON file with sorted keys, records in natural-id order.
2. `deputados.ndjson` is trimmed from 1,446 to 298 people: the 288 who held any situation other than Suplente in XVII, plus the first 10 by `DepCadId` who were only ever Suplente. Every seated deputy is kept, so the seat and group counts are the real ones.
3. `registo_biografico/XVII/<id // 1000>/<id>.json`: 5 records for people in `deputados.ndjson`, scalar fields only, pretty-printed with sorted keys. The ids, the key sets (some records lack some keys), the float ids, the null fields and the sex values are as published. Names, birth dates and professions are made up: names start with `Pessoa Sintética` and birth dates are in 1900. A test enforces this.
4. `iniciativas/<legislature>/<id // 1000>/<id>.json`: 9 initiative records as published, picked for the vote cases the tests pin: named dissenters with a count (XVII 356457, 315881), a unanimous vote with no detail (XVII 356774), a unanimous vote whose detail only lists an absent group (XVII 346027), a vote with no detail (XVII 377296), a XVI initiative voted in XVII (XVI 314565), and one vote published on two initiatives (XIV 45682 and 45634, vote 90081). The two XIV records are trimmed: events carrying any other vote are removed, so no XIV vote needs the seated groups of a day.
5. `atividades/XVII/AtividadesGerais.Atividades.ndjson`: 5 of the activity records with votes, as published: two with a detail, two unanimous with no detail (one listing an absent group) and one motion with no detail.
6. `informacao_base/XIV/`: `detalhe_legislatura.ndjson` and `grupos_parlamentares.ndjson` in full, and `deputados.ndjson` trimmed to the 8 deputies who author the two XIV initiatives and the 2 non-inscribed deputies named in vote 90081. These are InformacaoBase records (names, groups, situations), not biographies.
