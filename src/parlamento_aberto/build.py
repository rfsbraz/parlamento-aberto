"""Run the SQL models in order with DuckDB.

Each model is one SELECT in models/<layer>/<name>.sql and becomes a table called
<name>. models/schema.yml lists every model in run order with a description of
every column. Seeds are CSV files in models/seeds and load as seed_<name>.
models/macros.sql runs last and defines query helpers such as seated_on(d).
Models listed in PYTHON_MODELS are built by a Python function instead of a SQL file.
"""

from pathlib import Path

import duckdb
import yaml

from parlamento_aberto.vote_details import build_detail_items

MODELS = Path(__file__).parent / "models"
LAYERS = ("staging", "marts")
PYTHON_MODELS = {"stg_votes__detail_items": build_detail_items}


def load_schema() -> dict:
    return yaml.safe_load((MODELS / "schema.yml").read_text(encoding="utf-8"))["models"]


def _model_sql(name: str, data_dir: str) -> str:
    for layer in LAYERS:
        path = MODELS / layer / f"{name}.sql"
        if path.exists():
            source_file = f"replace(filename, '{data_dir}/', '')"
            return (
                path.read_text(encoding="utf-8")
                .replace("{source_file}", source_file)
                .replace("{legislature}", f"split_part({source_file}, '/', 2)")
                .replace("{data_dir}", data_dir)
            )
    raise FileNotFoundError(f"no SQL file for model {name}")


def build(data_dir: Path | str, database: str = ":memory:") -> duckdb.DuckDBPyConnection:
    data_dir = Path(data_dir).resolve().as_posix()
    con = duckdb.connect(database)
    for name in load_schema():
        if name in PYTHON_MODELS:
            PYTHON_MODELS[name](con)
            continue
        if name.startswith("seed_"):
            csv = (MODELS / "seeds" / f"{name.removeprefix('seed_')}.csv").as_posix()
            sql = f"select * from read_csv('{csv}', header = true)"
        else:
            sql = _model_sql(name, data_dir)
        con.execute(f"create or replace table {name} as {sql}")
    con.execute((MODELS / "macros.sql").read_text(encoding="utf-8"))
    return con
