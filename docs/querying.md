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

## Licence and attribution

The data is CC BY 4.0 (`LICENSE-DATA`). The AR allows free reuse of its open data as long as
the source is credited, so credit anything built on it with:

> Fonte: Assembleia da República, dados abertos.

Terms: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx. The same line is in
every CSV and in `manifest.json`. Each release names the data commit it was built from, so
you can cite a tag and rebuild it from git.
