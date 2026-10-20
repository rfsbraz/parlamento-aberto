# Consultar uma publicação

Cada publicação de dados tem um ficheiro Parquet e um CSV comprimido com gzip por mart, mais o
`manifest.json` (tag, commit de dados, número de linhas e hashes dos ficheiros) e o
`CHANGELOG.md`. A publicação mais recente está sempre em:

```
https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/<mart>.parquet
https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/<mart>.csv.gz
```

Troque `latest/download` por `download/<tag>`, por exemplo `download/data-2026-10-20`, para
fixar uma publicação. O significado de cada coluna está no [dicionário de dados](dictionary/README.md).

Todos os CSV começam com uma linha de atribuição antes do cabeçalho, por isso salte uma linha
ao lê-los. Os ficheiros Parquet não têm essa linha.

## DuckDB

O DuckDB lê os ficheiros diretamente do URL; carrega a extensão `httpfs` na primeira utilização.

Votações em plenário por ano:

```sql
select year(date) as year, count(*) as votes
from 'https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/votes.parquet'
where body = 'plenary'
group by year
order by year;
```

Como votou cada grupo nas votações em plenário mais recentes da XVII:

```sql
select v.date, v.vote_id, v.result, p.group_code, p.position, p.inferred
from 'https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/votes.parquet' v
join 'https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/vote_group_positions.parquet' p
  using (vote_id)
where v.legislature = 'XVII' and v.body = 'plenary'
order by v.date desc, v.vote_id, p.group_code
limit 20;
```

Intervenções por deputado na XVII, com o nome do deputado:

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

O CSV, saltando a linha de atribuição:

```sql
select *
from read_csv('https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/questions.csv.gz', skip = 1)
limit 5;
```

## pandas

Precisa de `pandas` e `pyarrow`.

```python
import pandas as pd

base = "https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/"
votes = pd.read_parquet(base + "votes.parquet")
questions = pd.read_csv(base + "questions.csv.gz", skiprows=1)
plenary = votes[votes["body"] == "plenary"]
print(plenary.groupby(plenary["date"].astype("datetime64[ns]").dt.year).size())
```

## R

Com os pacotes `duckdb` e `DBI` para o Parquet, e `readr` para o CSV:

```r
library(DBI)
base <- "https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/"
con <- dbConnect(duckdb::duckdb())
votes <- dbGetQuery(con, paste0("select * from '", base, "votes.parquet'"))
questions <- readr::read_csv(paste0(base, "questions.csv.gz"), skip = 1)
```

## Licença e atribuição

Os dados estão sob CC BY 4.0 (`LICENSE-DATA`). A AR permite a reutilização livre dos seus
dados abertos, desde que a fonte seja mencionada, por isso indique em tudo o que construir com
eles:

> Fonte: Assembleia da República, dados abertos.

Termos: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx. A mesma linha está em
todos os CSV e no `manifest.json`. Cada publicação indica o commit de dados de onde foi
construída, por isso pode citar uma tag e reconstruí-la a partir do git.
