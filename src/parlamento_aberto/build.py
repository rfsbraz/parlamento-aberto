"""Run the SQL models in order with DuckDB.

Each model is one SELECT in models/<layer>/<name>.sql and becomes a table called
<name>. models/schema.yml lists every model in run order with a description of
every column. Seeds are CSV files in models/seeds and load as seed_<name>.
models/macros.sql holds the seating rule (seated_on, seated_during). It runs right after the
mandates table is built, so later marts can use it.
Models listed in PYTHON_MODELS are built by a Python function instead of a SQL file; it gets
the connection and the data folder, and may write the tables in BUILT_ALONGSIDE too.
"""

from pathlib import Path

import duckdb
import yaml

from parlamento_aberto.ept_interests import build_ept_tables
from parlamento_aberto.interests import build_interest_tables
from parlamento_aberto.vote_details import build_detail_items

MODELS = Path(__file__).parent / "models"
LAYERS = ("staging", "marts")
PYTHON_MODELS = {
    "stg_votes__detail_items": build_detail_items,
    "stg_registo_interesses__files": build_interest_tables,
    "stg_ept_registo_interesses__declarations": build_ept_tables,
}
# Tables a Python model above writes alongside its own.
BUILT_ALONGSIDE = {
    "stg_registo_interesses__declarations",
    "stg_registo_interesses__items",
    "stg_ept_registo_interesses__items",
    "stg_ept_registo_interesses__fields",
    "stg_ept_registo_interesses__attachments",
    "stg_ept_registo_interesses__associations",
}
# Extra read_csv options per seed, for columns the type sniffer would get wrong.
SEED_OPTIONS = {
    # CNE and SGMAI circle codes keep their leading zeros, for example 01 or 010000.
    "seed_ballot_list_seats": ", types = {'circle_code': 'VARCHAR'}",
    "seed_ballot_list_elected": ", types = {'circle_code': 'VARCHAR', 'cadastro_id': 'BIGINT'}",
    "seed_ballot_list_elected_overrides": ", types = {'cadastro_id': 'BIGINT'}",
}
# The seating macros read mandates and are created as soon as it exists.
MACROS_AFTER = "mandates"


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
            PYTHON_MODELS[name](con, data_dir)
            continue
        if name in BUILT_ALONGSIDE:
            continue
        if name.startswith("seed_"):
            csv = (MODELS / "seeds" / f"{name.removeprefix('seed_')}.csv").as_posix()
            options = SEED_OPTIONS.get(name, "")
            sql = f"select * from read_csv('{csv}', header = true{options})"
        else:
            sql = _model_sql(name, data_dir)
        con.execute(f"create or replace table {name} as {sql}")
        if name == MACROS_AFTER:
            con.execute((MODELS / "macros.sql").read_text(encoding="utf-8"))
    return con
