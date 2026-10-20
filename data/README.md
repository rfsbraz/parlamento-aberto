# data/

Normalised raw data from the Assembleia da República open data dumps.

Licença: estes ficheiros são dados abertos da Assembleia da República, reutilizados nos termos da AR e não sob CC BY. Quem os reutilizar deve mencionar a fonte e a data da última atualização (Lei n.º 26/2016, art. 19.º, n.º 5), que está em `_meta/sources.lock.json` (`fetched`). `ept_*/` são dados da Entidade para a Transparência e ficam fora de qualquer licença nossa. Ver `LICENSE-DATA`. Fonte: Assembleia da República, dados abertos.

Layout (see `docs/design.md`):

- Everything is keyed by dataset and legislature, with JSON keys sorted and UTF-8 kept as is.
- Nested, record-heavy datasets (such as Iniciativas): one pretty-printed JSON file per record, in folders bucketed by id, for example `iniciativas/XVII/377/377352.json`.
- Flat datasets (such as Intervencoes): NDJSON with sorted keys, records in natural-id order, split into fixed id or year ranges so a record never moves between files.
- `_meta/sources.lock.json`: per source file, the SHA-256 of the last good download, fetch date, record count, top-level key fingerprint and stale status.

No file may be over 50 MB. CI rejects any tracked file above that.
