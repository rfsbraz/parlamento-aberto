"""Python model: parse every distinct vote `detalhe` string into one row per item.

SQL cannot call the parser, so build() runs this between the SQL models. It reads the
detail strings from the vote staging models and writes stg_votes__detail_items.
"""

import json
import tempfile
from pathlib import Path

import duckdb

from parlamento_aberto.votes import VoteDetailError, parse_detalhe

SOURCES = ("stg_iniciativas__votes", "stg_atividades__votes")
COLUMNS = {
    "detail": "VARCHAR",
    "item_number": "INTEGER",
    "kind": "VARCHAR",
    "group_acronym": "VARCHAR",
    "position": "VARCHAR",
    "deputies": "INTEGER",
    "name": "VARCHAR",
    "error": "VARCHAR",
}


def detail_items(detail: str) -> list[dict]:
    """One row per group, count or named deputy in the string, or one error row."""
    try:
        parsed = parse_detalhe(detail)
    except VoteDetailError as e:
        return [{"detail": detail, "item_number": 0, "error": str(e)}]
    rows = [
        {"kind": "group", "group_acronym": g.group, "position": g.position} for g in parsed.groups
    ]
    rows += [
        {"kind": "count", "group_acronym": c.group, "position": c.position, "deputies": c.count}
        for c in parsed.counts
    ]
    rows += [
        {"kind": "deputy", "group_acronym": d.group, "position": d.position, "name": d.name}
        for d in parsed.deputies
    ]
    return [{"detail": detail, "item_number": n, **row} for n, row in enumerate(rows, 1)]


def build_detail_items(con: duckdb.DuckDBPyConnection) -> None:
    union = " union ".join(f"select detail from {t} where detail is not null" for t in SOURCES)
    details = [
        d for (d,) in con.sql(f"select distinct detail from ({union}) order by 1").fetchall()
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "items.ndjson"
        with path.open("w", encoding="utf-8") as f:
            for detail in details:
                for row in detail_items(detail):
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        columns = ", ".join(f"{k}: '{v}'" for k, v in COLUMNS.items())
        source = path.as_posix().replace("'", "''")
        con.execute(
            "create or replace table stg_votes__detail_items as "
            f"select {', '.join(COLUMNS)} from read_json('{source}', "
            f"format = 'newline_delimited', columns = {{{columns}}}) "
            "order by detail, item_number"
        )
