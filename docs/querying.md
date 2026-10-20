# Consultar uma publicação

Cada publicação de dados tem um ficheiro Parquet e um CSV comprimido com gzip por mart, mais o
`macros.sql` com a regra de quem tem lugar num dia, o `manifest.json` (tag, commit de dados,
número de linhas e hashes dos ficheiros) e o `CHANGELOG.md`. A publicação mais recente está sempre em:

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

## Quem tem lugar num dia

A regra de quem tem lugar num dia vem em cada publicação, no `macros.sql`, igual à usada nos
marts. O `manifest.json` lista-o na chave `macros`, com o SHA-256. Com o pacote `duckdb` do
Python, carregue o `mandates.parquet` e o `macros.sql` da mesma publicação:

```python
import hashlib
import json
import urllib.request

import duckdb

base = "https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/"


def get(name):
    with urllib.request.urlopen(base + name) as r:
        return r.read()


manifest = json.loads(get("manifest.json"))
macros = get("macros.sql")
assert hashlib.sha256(macros).hexdigest() == manifest["macros"]["sha256"]

con = duckdb.connect()
con.execute(f"create table mandates as select * from '{base}mandates.parquet'")
con.execute(macros.decode("utf-8"))
day = con.sql("select max(start_date) from mandates").fetchone()[0]
print(con.sql("select legislature, count(*) from seated_on(?) group by 1", params=[day]))
```

Para contar lugares numa tag fixa, troque `latest/download` por `download/<tag>`. O
`macros.sql` cria `seated_on(d)`, `seated_during(d0, d1)` e `seated_by_period_during(d0, d1)`,
que só precisam da tabela `mandates`. É código, sob a licença MIT do repositório.

## Licença e atribuição

Os marts das publicações estão sob CC BY 4.0 (`LICENSE-DATA`), com a Assembleia da República
como fonte. A AR permite a reutilização livre dos seus dados abertos desde que se mencione
a fonte, e a Lei n.º 26/2016, art. 19.º, n.º 5, pede também a data da última atualização.
Cite o que construir com estes dados assim, com a data `source_updated` do `manifest.json`:

> Fonte: Assembleia da República, dados abertos, atualizados a AAAA-MM-DD.

Termos da AR: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx. A mesma linha,
já com a data, abre cada CSV, e o `manifest.json` traz a licença de cada mart. Os dados
brutos em `data/` não estão sob CC BY: são dados da AR, reutilizados nos termos da AR. Os
dados da Entidade para a Transparência ficam fora da CC BY e não entram nas publicações. Cada
publicação indica o commit de dados de onde foi construída, por isso pode citar uma tag e
reconstruí-la a partir do git.
