"""Turn one parsed AR file into the text layout under data/<dataset>/<legislature>/.

records: one pretty-printed, key-sorted JSON file per record, bucketed by id,
    for example 377/377352.json.
tables: every list of records in the file becomes <table>.ndjson with sorted
    keys. A table with an id in sources.yaml is sorted by it; one without is
    sorted by content. If the dataset sets a bucket, id-keyed tables are split
    into fixed id ranges (<table>.<start>-<end>.ndjson), so a record never
    changes file. names: in sources.yaml renames a table's file.
"""

import json
import re
from collections.abc import Iterator

MAX_FILE_BYTES = 50_000_000


class LayoutError(ValueError):
    pass


def dump_record(record) -> bytes:
    return (json.dumps(record, sort_keys=True, ensure_ascii=False, indent=1) + "\n").encode()


def dump_line(record) -> str:
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def as_int(value, what: str) -> int:
    """AR ids come as 377352, "377352" or 377352.0."""
    try:
        f = float(value)
        if f != int(f):
            raise ValueError
        return int(f)
    except (TypeError, ValueError, OverflowError):
        raise LayoutError(f"{what}: id {value!r} is not an integer") from None


def get_path(record, dotted: str):
    """Read a possibly nested id, for example Deputado.DepCadId."""
    for part in dotted.split("."):
        record = record.get(part) if isinstance(record, dict) else None
    return record


def records_layout(data, id_key: str) -> dict[str, bytes]:
    if not isinstance(data, list):
        raise LayoutError("records layout needs a top-level list")
    files: dict[str, bytes] = {}
    for record in data:
        rid = as_int(get_path(record, id_key), id_key)
        path = f"{rid // 1000}/{rid}.json"
        if path in files:
            raise LayoutError(f"duplicate {id_key} {rid}")
        files[path] = dump_record(record)
    return files


def tables(obj, path: str = "") -> Iterator[tuple[str, list]]:
    """Yield (table name, records). Dicts are walked until lists are found."""
    if isinstance(obj, list):
        yield path or "records", obj
        return
    if isinstance(obj, dict):
        scalars = {k: v for k, v in obj.items() if not isinstance(v, (list, dict))}
        if scalars:
            yield (f"{path}._meta" if path else "_meta"), [scalars]
        for k, v in obj.items():
            if isinstance(v, (list, dict)):
                yield from tables(v, f"{path}.{k}" if path else k)


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def tables_layout(data, ids: dict, names: dict, bucket: int | None) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for name, recs in tables(data):
        recs = [r if isinstance(r, dict) else {"value": r} for r in recs]
        if not recs:
            continue
        key = ids.get(name)
        stem = names.get(name) or safe_name(name)
        if key:
            # Records with a null id (Intervencoes has a few) sort after the rest.
            rows = sorted(
                (
                    (1, 0) if get_path(r, key) is None else (0, as_int(get_path(r, key), key)),
                    dump_line(r),
                )
                for r in recs
            )
            groups: dict[str, list[str]] = {}
            for (missing, rid), line in rows:
                if not bucket:
                    fname = f"{stem}.ndjson"
                elif missing:
                    fname = f"{stem}.no-id.ndjson"
                else:
                    start = rid // bucket * bucket
                    fname = f"{stem}.{start}-{start + bucket - 1}.ndjson"
                groups.setdefault(fname, []).append(line)
        else:
            groups = {f"{stem}.ndjson": sorted(dump_line(r) for r in recs)}
        for fname, lines in groups.items():
            files[fname] = ("\n".join(lines) + "\n").encode()
    return files


def normalise(
    data, layout: str, id_key: str | None, ids: dict, bucket: int | None, names: dict | None = None
) -> dict[str, bytes]:
    if layout == "records":
        files = records_layout(data, id_key)
    elif layout == "tables":
        files = tables_layout(data, ids, names or {}, bucket)
    else:
        raise LayoutError(f"unknown layout {layout!r}")
    for path, body in files.items():
        if len(body) > MAX_FILE_BYTES:
            raise LayoutError(f"{path} would be {len(body):,} bytes, over the 50 MB limit")
    return files


def count_records(data) -> int:
    if isinstance(data, list):
        return len(data)
    return sum(len(r) for name, r in tables(data) if not name.endswith("_meta"))


def top_level_keys(data) -> list[str]:
    """The key set compared between runs: record keys for a list, top keys for a dict."""
    if isinstance(data, list):
        return sorted({k for r in data if isinstance(r, dict) for k in r})
    if isinstance(data, dict):
        return sorted(data)
    return []
