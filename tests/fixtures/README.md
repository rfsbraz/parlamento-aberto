# Test fixtures

`data/` follows the layout in `docs/design.md`, so the models read it the same way they read the real `data/` folder. Tests never touch the network.

## Source and extract date

- `data/informacao_base/XVII/`: InformacaoBase XVII (`InformacaoBaseXVII_json.txt`), downloaded from parlamento.pt on 20 Oct 2026. The extract date is **2026-10-19**: AR writes it as the end date of every open group membership, and `legislatures.extract_date` reads it from there.
- `data/registo_biografico/XVII/`: shape taken from RegistoBiografico XVII, downloaded the same day. The content is synthetic (see below).

## How they were built

1. One table per file: `CirculosEleitorais`, `DetalheLegislatura`, `GruposParlamentares`, `SessoesLegislativas` and `Deputados` each became an NDJSON file with sorted keys, records in natural-id order.
2. `deputados.ndjson` is trimmed from 1,446 to 298 people: the 288 who held any situation other than Suplente in XVII, plus the first 10 by `DepCadId` who were only ever Suplente. Every seated deputy is kept, so the seat and group counts are the real ones.
3. `registo_biografico/XVII/<id // 1000>/<id>.json`: 5 records for people in `deputados.ndjson`, scalar fields only, pretty-printed with sorted keys. The ids, the key sets (some records lack some keys), the float ids, the null fields and the sex values are as published. Names, birth dates and professions are made up: names start with `Pessoa Sintética` and birth dates are in 1900. A test enforces this.
