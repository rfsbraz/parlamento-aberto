"""Python model: read the EpT register of interests (#46) into declarations and items.

Input is the fetcher's output (#44), data/ept_registo_interesses/<entity>/<id // 1000>/<id>.json,
already stripped to metadata and tab 4. Rows line up with the XI to XV staging tables in
interests.py (same column names where the meaning is the same), plus the EpT-only columns.

- Only Deputado (8) and Deputada (232) declarations are read. Presidente da Assembleia da
  República, Vice-Presidente, Vogal and Presidente declarations are other offices.
- The legislature comes from the office start date (the submitted date when there is none),
  as the Europe/Lisbon day, against the legislatures mart. Entity 510 holds XIV to XVI.
- UTC dates become the Lisbon day; the published value stays in the _raw columns.
- Replaced and modified versions are kept. relatedDeclarationId links a version to the one it
  replaces or modifies; each row gets the version that supersedes it, the first version of
  its chain, and is_current for the newest published, unsuperseded declaration of a holder
  in an office.
- The tab 4 entity NIF/NIPC column carries through as entity_nipc, which holds only valid
  company NIPCs (the fetcher drops the rest). Input and output go through the fetcher's
  leak guard.
"""

import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

from . import ept
from .interests import _write_table

LISBON = ZoneInfo("Europe/Lisbon")
ROLES = {8: "Deputado", 232: "Deputada"}
NATURE = {
    1: "initial",
    2: "modification",
    4: "cessation",
    8: "final",
    16: "replace",
    32: "reElection",
}
STATE = {
    1: "draft",
    2: "pendingVerification",
    4: "notPublished",
    8: "published",
    16: "canceled",
    32: "modified",
    64: "replaced",
}

# Section GUID -> source_list (the label EpT shows) and {column: field}.
SECTION_FIELDS = {
    "2c6d9562-dea5-488b-9afe-42519c636daf": (
        "Atividades profissionais, cargos públicos, privados e sociais",
        {
            "col1": "description",
            "col2": "entity",
            "col3": "activity_area",
            "col4": "location",
            "col5": "paid_raw",
            "col6": "start_date_raw",
            "col7": "end_date_raw",
        },
    ),
    "cd0e811a-d9bb-49ee-b0f0-1dae0680eb22": (
        "Filiação ou funções em entidades de natureza associativa",
        {
            "col1": "description",
            "col2": "entity",
            "col3": "activity_area",
            "col4": "location",
            "col5": "paid_raw",
            "col6": "start_date_raw",
            "col7": "end_date_raw",
        },
    ),
    "62fb0107-a68d-4ba2-822b-bc8adc54369b": (
        "Apoios ou benefícios",
        {
            "col1": "description",
            "col2": "entity",
            "col3": "activity_area",
            "col4": "nature",
            "col5": "start_date_raw",
            "col7": "end_date_raw",
            "col8": "beneficiary",
            "col9": "beneficiary_company",
        },
    ),
    "b1f8c095-fe0c-4bb3-b493-902dc0c31232": (
        "Serviços prestados",
        {
            "col1": "description",
            "col2": "entity",
            "col3": "activity_area",
            "col4": "location",
            "col5": "start_date_raw",
            "col7": "end_date_raw",
            "col8": "is_professional_secrecy",
        },
    ),
    "9b58c917-b14c-4eed-9b3c-40c3d99d45da": (
        "Sociedades",
        {
            "col1": "entity",
            "col2": "activity_area",
            "col3": "location",
            "col4": "share_value_eur",
            "col5": "share_pct",
            "col6": "nature",
            "col8": "share_holder",
        },
    ),
    "fd85f91f-2803-41bc-b315-ede3a4a66d4e": (
        "Outras situações",
        {
            "col1": "description",
            "col2": "date_raw",
            "col3": "paid_raw",
            "col4": "observation",
            "col6": "is_professional_secrecy",
        },
    ),
}
assert set(SECTION_FIELDS) == set(ept.SECTIONS)
for _guid, (_label, _fields) in SECTION_FIELDS.items():
    assert set(_fields) == set(ept.SECTIONS[_guid][2])

# Columns of stg_registo_interesses__* (XI to XV), so the marts can union both sources.
AR_DECLARATION_COLUMNS = {
    "declaration_key": "VARCHAR",
    "cadastro_id": "BIGINT",
    "format_version": "VARCHAR",
    "declaration_id": "BIGINT",
    "declared_legislature": "VARCHAR",
    "position": "VARCHAR",
    "position_start_raw": "VARCHAR",
    "position_changed_raw": "VARCHAR",
    "position_end_raw": "VARCHAR",
    "version_date_raw": "VARCHAR",
    "is_exclusive": "BOOLEAN",
    "items": "INTEGER",
    "legislature": "VARCHAR",
    "source_file": "VARCHAR",
}
DECLARATION_COLUMNS = {
    **AR_DECLARATION_COLUMNS,
    "source": "VARCHAR",
    "source_format": "VARCHAR",
    "source_declaration_id": "BIGINT",
    "ept_holder_id": "BIGINT",
    "ept_entity_id": "BIGINT",
    "ept_role_id": "BIGINT",
    "position_start_date": "DATE",
    "position_changed_date": "DATE",
    "position_end_date": "DATE",
    "version_date": "DATE",
    "declaration_nature": "VARCHAR",
    "declaration_state": "VARCHAR",
    "supersedes_declaration_id": "BIGINT",
    "superseded_by_declaration_id": "BIGINT",
    "chain_root_declaration_id": "BIGINT",
    "submitted_at": "VARCHAR",
    "submitted_date": "DATE",
    "is_current": "BOOLEAN",
}
AR_ITEM_COLUMNS = {
    "declaration_key": "VARCHAR",
    "item_number": "INTEGER",
    "category": "VARCHAR",
    "source_list": "VARCHAR",
    "item_id": "BIGINT",
    "type_code": "INTEGER",
    "description": "VARCHAR",
    "entity": "VARCHAR",
    "nature": "VARCHAR",
    "activity_area": "VARCHAR",
    "location": "VARCHAR",
    "share": "VARCHAR",
    "paid_raw": "VARCHAR",
    "start_date_raw": "VARCHAR",
    "end_date_raw": "VARCHAR",
    "date_raw": "VARCHAR",
    "legislature": "VARCHAR",
    "source_file": "VARCHAR",
}
ITEM_COLUMNS = {
    **AR_ITEM_COLUMNS,
    "source": "VARCHAR",
    "is_paid": "BOOLEAN",
    "start_date": "DATE",
    "end_date": "DATE",
    "entity_nipc": "VARCHAR",
    "beneficiary": "VARCHAR",
    "beneficiary_company": "VARCHAR",
    "share_value_eur": "VARCHAR",
    "share_pct": "VARCHAR",
    "share_holder": "VARCHAR",
    "is_professional_secrecy": "BOOLEAN",
    "observation": "VARCHAR",
}
# The keys of the unified rows in the #42 example (cadastro_id comes from #47 in #48).
EXAMPLE_DECLARATION_KEYS = (
    "declaration_key",
    "source",
    "source_format",
    "source_declaration_id",
    "ept_holder_id",
    "legislature",
    "position",
    "position_start_date",
    "position_end_date",
    "position_changed_date",
    "declaration_nature",
    "declaration_state",
    "supersedes_declaration_id",
    "submitted_at",
    "is_exclusive",
    "version_date",
    "items",
)
EXAMPLE_ITEM_KEYS = (
    "declaration_key",
    "item_number",
    "legislature",
    "source",
    "category",
    "source_list",
    "item_id",
    "type_code",
    "description",
    "entity",
    "activity_area",
    "location",
    "paid_raw",
    "is_paid",
    "start_date",
    "start_date_raw",
    "end_date",
    "end_date_raw",
)
BOOLEAN_FIELDS = {"is_professional_secrecy"}

Ranges = list[tuple[str, dt.date, dt.date | None]]


class EptParseError(ValueError):
    pass


def _text(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _bool(v) -> bool | None:
    if isinstance(v, bool):
        return v
    return {"true": True, "false": False}.get((_text(v) or "").lower())


def lisbon_day(v) -> str | None:
    """The Europe/Lisbon day of an ISO date or datetime. A value with no zone is Lisbon time."""
    s = _text(v)
    if not s:
        return None
    try:
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        return t.date().isoformat()
    return t.astimezone(LISBON).date().isoformat()


def legislature_on(day: str | None, ranges: Ranges) -> str | None:
    if not day:
        return None
    d = dt.date.fromisoformat(day)
    for leg, start, end in ranges:
        if start and start <= d and (end is None or d <= end):
            return leg
    return None


def _enum(table: dict, value, what: str) -> str:
    if value not in table:
        raise EptParseError(f"declaration: unknown {what} {value}")
    return table[value]


def _items(tab4: dict | None, key: str, legislature: str | None, source_file: str) -> list[dict]:
    items = []
    for guid, rows in (tab4 or {}).items():
        if guid not in SECTION_FIELDS:
            raise EptParseError(f"declaration {key}: unknown tab 4 section {guid}")
        category, nif_col, _ = ept.SECTIONS[guid]
        label, fields = SECTION_FIELDS[guid]
        for row in rows:
            item = {
                "category": category,
                "source_list": label,
                "entity_nipc": row.get(nif_col) if nif_col else None,
            }
            for col, field in fields.items():
                v = row.get(col)
                item[field] = _bool(v) if field in BOOLEAN_FIELDS else _text(v)
            item["start_date"] = lisbon_day(item.get("start_date_raw"))
            item["end_date"] = lisbon_day(item.get("end_date_raw"))
            items.append(item)
    out = []
    for n, item in enumerate(items, 1):
        row = {k: None for k in ITEM_COLUMNS}
        row.update(item)
        row.update(
            declaration_key=key,
            item_number=n,
            legislature=legislature,
            source="ept",
            is_paid=None,  # EpT publishes Remuneração as 1 or 0 without saying what it means
            source_file=source_file,
        )
        out.append(row)
    return out


def parse_declaration(rec: dict, ranges: Ranges, source_file: str) -> tuple[dict, list[dict]]:
    """(declaration row, item rows) for one stored declaration."""
    ept.assert_clean(rec)
    decl_id = rec["id"]
    key = f"ept:{decl_id}"
    start = lisbon_day(rec.get("startDate"))
    submitted = lisbon_day(rec.get("submitedDate"))
    legislature = legislature_on(start or submitted, ranges)
    items = _items(rec.get("tab4"), key, legislature, source_file)
    decl = {k: None for k in DECLARATION_COLUMNS}
    decl.update(
        declaration_key=key,
        format_version="EPT",
        declaration_id=decl_id,
        position=_text(rec.get("role")),
        position_start_raw=_text(rec.get("startDate")),
        position_end_raw=_text(rec.get("endDate")),
        items=len(items),
        legislature=legislature,
        source_file=source_file,
        source="ept",
        source_format="EPT",
        source_declaration_id=decl_id,
        ept_holder_id=rec.get("holderId"),
        ept_entity_id=rec.get("entityId"),
        ept_role_id=rec.get("roleId"),
        position_start_date=start,
        position_end_date=lisbon_day(rec.get("endDate")),
        declaration_nature=_enum(NATURE, rec.get("natureType"), "natureType"),
        declaration_state=_enum(STATE, rec.get("stateType"), "stateType"),
        supersedes_declaration_id=rec.get("relatedDeclarationId"),
        submitted_at=_text(rec.get("submitedDate")),
        submitted_date=submitted,
    )
    return decl, items


def resolve_chains(decls: list[dict]) -> list[dict]:
    """Fill superseded_by_declaration_id, chain_root_declaration_id and is_current."""
    by_id = {d["source_declaration_id"]: d for d in decls}

    def order(d):
        return (d["submitted_at"] or "", d["source_declaration_id"])

    for d in sorted(decls, key=order):
        d["superseded_by_declaration_id"] = None
    for d in sorted(decls, key=order):
        parent = by_id.get(d["supersedes_declaration_id"])
        if parent is not None:
            parent["superseded_by_declaration_id"] = d["source_declaration_id"]
    for d in decls:
        seen, cur = {d["source_declaration_id"]}, d
        while cur["supersedes_declaration_id"] in by_id:
            cur = by_id[cur["supersedes_declaration_id"]]
            if cur["source_declaration_id"] in seen:
                raise EptParseError(f"declaration {d['declaration_key']}: cycle in the chain")
            seen.add(cur["source_declaration_id"])
        d["chain_root_declaration_id"] = cur["source_declaration_id"]
    newest: dict[tuple, dict] = {}
    for d in decls:
        d["is_current"] = False
        if d["declaration_state"] != "published" or d["superseded_by_declaration_id"]:
            continue
        group = (d["ept_holder_id"], d["ept_entity_id"], d["ept_role_id"])
        if group not in newest or order(d) > order(newest[group]):
            newest[group] = d
    for d in newest.values():
        d["is_current"] = True
    return decls


def assert_rows_clean(decls: list[dict], items: list[dict]) -> None:
    """No nif, no personal-range value, no 9 digits outside entity_nipc."""
    ept.assert_clean([{k: str(v) if v is not None else None for k, v in d.items()} for d in decls])
    for i, row in enumerate(items):
        nipc = row.get("entity_nipc")
        if nipc is not None and not ept.is_company_nipc(nipc):
            raise ept.LeakError(f"not a company NIPC at items[{i}].entity_nipc")
        rest = {k: str(v) if v is not None else None for k, v in row.items() if k != "entity_nipc"}
        ept.assert_clean(rest, f"items[{i}]")


def read_all(data_dir: Path | str, ranges: Ranges) -> tuple[list[dict], list[dict]]:
    data_dir = Path(data_dir)
    root = data_dir / ept.DATASET
    decls, items = [], []
    for path in sorted(root.glob("*/*/*.json"), key=lambda p: int(p.stem)):
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec.get("roleId") not in ROLES:
            continue
        d, i = parse_declaration(rec, ranges, path.relative_to(data_dir).as_posix())
        decls.append(d)
        items += i
    resolve_chains(decls)
    assert_rows_clean(decls, items)
    return decls, items


def build_ept_tables(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    """Writes stg_ept_registo_interesses__declarations and __items."""
    ranges = [
        (leg, start, end)
        for leg, start, end in con.execute(
            "select legislature, start_date, end_date from legislatures order by start_date"
        ).fetchall()
    ]
    decls, items = read_all(data_dir, ranges)
    _write_table(con, "stg_ept_registo_interesses__declarations", decls, DECLARATION_COLUMNS)
    _write_table(con, "stg_ept_registo_interesses__items", items, ITEM_COLUMNS)
