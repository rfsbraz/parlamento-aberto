# Querying a release

Each data release has one Parquet file and one gzipped CSV per mart, plus `manifest.json`
(tag, data commit, row counts and file hashes) and `CHANGELOG.md`. The latest release is
always at:

```
https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/<mart>.parquet
https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/<mart>.csv.gz
```

Swap `latest/download` for `download/<tag>`, for example `download/data-2026-10-20`, to
pin a release. What each column means is in the [data dictionary](dictionary/README.md).

Every CSV starts with one attribution line before the header, so skip one line when you
read it. Parquet files have no such line.

## DuckDB

DuckDB reads the files straight from the URL; it loads its `httpfs` extension on first use.

Plenary votes per year:

```sql
select year(date) as year, count(*) as votes
from 'https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/votes.parquet'
where body = 'plenary'
group by year
order by year;
```

How each group voted on the latest plenary votes of XVII:

```sql
select v.date, v.vote_id, v.result, p.group_code, p.position, p.inferred
from 'https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/votes.parquet' v
join 'https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/vote_group_positions.parquet' p
  using (vote_id)
where v.legislature = 'XVII' and v.body = 'plenary'
order by v.date desc, v.vote_id, p.group_code
limit 20;
```

Interventions per deputy in XVII, with the deputy's name:

```sql
select d.parliamentary_name, count(*) as interventions
from 'https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/interventions.parquet' i
join 'https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/deputies.parquet' d
  using (cadastro_id)
where i.legislature = 'XVII'
group by d.parliamentary_name
order by interventions desc
limit 10;
```

The CSV, skipping the attribution line:

```sql
select *
from read_csv('https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/questions.csv.gz', skip = 1)
limit 5;
```

## pandas

Needs `pandas` and `pyarrow`.

```python
import pandas as pd

base = "https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/"
votes = pd.read_parquet(base + "votes.parquet")
questions = pd.read_csv(base + "questions.csv.gz", skiprows=1)
plenary = votes[votes["body"] == "plenary"]
print(plenary.groupby(plenary["date"].astype("datetime64[ns]").dt.year).size())
```

## R

With the `duckdb` and `DBI` packages for Parquet, and `readr` for the CSV:

```r
library(DBI)
base <- "https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/"
con <- dbConnect(duckdb::duckdb())
votes <- dbGetQuery(con, paste0("select * from '", base, "votes.parquet'"))
questions <- readr::read_csv(paste0(base, "questions.csv.gz"), skip = 1)
```

## Licença e atribuição

Os marts das releases estão sob CC BY 4.0 (`LICENSE-DATA`), com a Assembleia da República
como fonte. A AR permite a reutilização livre dos seus dados abertos desde que se mencione
a fonte, e a Lei n.º 26/2016, art. 19.º, n.º 5, pede também a data da última atualização.
Cite o que construir com estes dados assim, com a data `source_updated` do `manifest.json`:

> Fonte: Assembleia da República, dados abertos, atualizados a AAAA-MM-DD.

Termos da AR: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx. A mesma linha,
já com a data, abre cada CSV, e o `manifest.json` traz a licença de cada mart. Os dados
brutos em `data/` não estão sob CC BY: são dados da AR, reutilizados nos termos da AR. Os
dados da Entidade para a Transparência ficam fora da CC BY e não entram nas releases. Cada
release indica o commit de dados de onde foi construída, por isso pode citar uma tag e
reconstruí-la a partir do git.
