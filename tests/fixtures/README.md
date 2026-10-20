# Test fixtures

`data/` follows the layout in `docs/design.md`, so the models read it the same way they read the real `data/` folder. Tests never touch the network.

## Source and extract date

- `data/informacao_base/XVII/`: InformacaoBase XVII (`InformacaoBaseXVII_json.txt`), downloaded from parlamento.pt on 20 Oct 2026. The extract date is **2026-10-19**: AR writes it as the end date of every open group membership, and `legislatures.extract_date` reads it from there.
- `data/registo_biografico/XVII/`: shape taken from RegistoBiografico XVII, downloaded the same day. The content is synthetic (see below).
- `data/informacao_base/II/` and `data/registo_biografico/II/`: InformacaoBase II and the RegistoBiograficoII file listed on the AR I Legislatura page, downloaded on 20 Oct 2026. The biographies are synthetic (see below).
- `data/intervencoes/XVII/` and `data/perguntas_requerimentos/XVII/`: Intervencoes XVII and PerguntasRequerimentos XVII from the full sync of 20 Oct 2026 (fetch date 2026-10-20 in the lock). Free text is synthetic (see below).
- `data/_meta/sources.lock.json`: the lock entries for those two files, with `records` set to the trimmed counts and the hash and size left out, since they belong to the full download.

## How they were built

1. One table per file: `CirculosEleitorais`, `DetalheLegislatura`, `GruposParlamentares`, `SessoesLegislativas` and `Deputados` each became an NDJSON file with sorted keys, records in natural-id order.
2. `deputados.ndjson` is trimmed from 1,446 to 298 people: the 288 who held any situation other than Suplente in XVII, plus the first 10 by `DepCadId` who were only ever Suplente. Every seated deputy is kept, so the seat and group counts are the real ones.
3. `registo_biografico/XVII/<id // 1000>/<id>.json`: 5 records for people in `deputados.ndjson`, scalar fields only, pretty-printed with sorted keys. The ids, the key sets (some records lack some keys), the float ids, the null fields and the sex values are as published. Names, birth dates and professions are made up: names start with `Pessoa Sintética` and birth dates are in 1900. A test enforces this.
4. `intervencoes/XVII/records.ndjson`: trimmed from 81 to 15 records: 11 deputy interventions picked for variety (type, role, with and without initiatives and audiovisual data) and 4 by government members, plus one empty record with every key null, the shape AR publishes 113 times across V, XI, XIV, XV and XVI. Every speaker is in `deputados.ndjson`.
5. `perguntas_requerimentos/XVII/records.ndjson`: trimmed from 4,076 to 24 records picked for variety: perguntas and requerimentos, recipient categories AC, AL and EI, one or many authors, one or two recipients, with and without answers and extensions. Every author is in `deputados.ndjson`.
6. In both files, ids, dates, types, deputy and government member names and ids, groups and recipient bodies are as published: they are public office data. Free text that can name private citizens or companies is made up: summaries, abstracts, debate titles, subjects, notes and related activity titles contain `sintético` or `sintética`, and document, diary, video and answer links point to `https://app.parlamento.pt/fixture/`. A test enforces this.
7. `informacao_base/II/`: `detalhe_legislatura.ndjson` as published, and `deputados.ndjson` trimmed from 440 to 3 people (`DepCadId` 4, 5 and 312), as published: public office data. 312 is one of the 8 II deputies with no record in the RegistoBiografico II file.
8. `registo_biografico/II/0/<id>.json`: records for 4 and 5 in the older XML-converted shape (camelCase keys, string `cadId`), scalar fields only. Ids and sex are as published. Names, birth dates and professions are made up as above; 5 has no birth date, as for most II records. The same test enforces this.
9. One synthetic value: question 187751 has `DataEnvio` set to `2125-06-12` (published as `2025-06-12`), a year typo of the kind AR publishes in X and XIII, so the invalid sent date rule has a case.
