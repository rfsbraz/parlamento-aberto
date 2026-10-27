"""Turn one parsed AR file into the text layout under data/<dataset>/<legislature>/.

records: one pretty-printed, key-sorted JSON file per record, bucketed by id,
    for example 377/377352.json. A path: in sources.yaml points at the record
    list inside an older XML-shaped file.
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


def records_at(data, path: str | None):
    """The record list, at a dotted path for the older XML-shaped files.

    XML converted to JSON turns a one-item list into an object, so an object
    found at the path is one record.
    """
    if not path:
        return data
    found = get_path(data, path)
    if found is None:
        raise LayoutError(f"no records at {path}")
    return [found] if isinstance(found, dict) else found


def records_layout(data, id_key: str, path: str | None = None) -> dict[str, bytes]:
    data = records_at(data, path)
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
    data,
    layout: str,
    id_key: str | None,
    ids: dict,
    bucket: int | None,
    names: dict | None = None,
    path: str | None = None,
) -> dict[str, bytes]:
    if layout == "records":
        files = records_layout(data, id_key, path)
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


def drop_null_ids(data, layout: str, id_key: str | None, ids: dict, path: str | None) -> int:
    """Remove records whose id is null, in place. AR publishes some all-null rows
    (Intervencoes XVII has 47). They have no id to merge by. Returns how many."""
    if layout == "records":
        found = [(records_at(data, path), id_key)]
    else:
        found = [(recs, ids[name]) for name, recs in tables(data) if ids.get(name)]
    dropped = 0
    for recs, key in found:
        if not isinstance(recs, list):
            continue
        keep = [r for r in recs if not (isinstance(r, dict) and get_path(r, key) is None)]
        dropped += len(recs) - len(keep)
        recs[:] = keep
    return dropped


def table_file_key(fname: str, ids: dict, names: dict) -> str | None:
    """The id key of the id-keyed table a tables-layout file belongs to, if any."""
    for name, key in ids.items():
        stem = names.get(name) or safe_name(name)
        if fname == f"{stem}.ndjson" or re.fullmatch(
            re.escape(stem) + r"\.(\d+-\d+|no-id)\.ndjson", fname
        ):
            return key
    return None


def upsert(
    old: dict[str, bytes], new: dict[str, bytes], layout: str, ids: dict, names: dict
) -> tuple[dict[str, bytes], int]:
    """Merge a normalised AR file into the stored files by record id.

    AR's records replace stored ones with the same id and add new ones. Stored
    records AR left out stay. Files of tables without an id are replaced.
    Returns the merged files and how many stored records AR left out.
    """
    if layout == "records":
        return {**old, **new}, len(old.keys() - new.keys())
    merged: dict[str, bytes] = {}
    kept = 0
    for fname in sorted(old.keys() | new.keys()):
        key = table_file_key(fname, ids, names)
        if key is None:
            merged[fname] = new.get(fname, old.get(fname))
            continue
        rows: dict[int, str] = {}
        from_ar: set[int] = set()
        for body, is_new in ((old.get(fname, b""), False), (new.get(fname, b""), True)):
            for line in body.decode().splitlines():
                rid = get_path(json.loads(line), key)
                if rid is None:
                    continue
                rows[rid := as_int(rid, key)] = line
                if is_new:
                    from_ar.add(rid)
        kept += len(rows.keys() - from_ar)
        if rows:
            merged[fname] = ("\n".join(rows[i] for i in sorted(rows)) + "\n").encode()
    return merged, kept


def count_lines(files: dict[str, bytes], layout: str, names: dict) -> int:
    """Records in normalised files: one per file, or one per NDJSON line outside _meta tables."""
    if layout == "records":
        return len(files)
    meta = {names.get(n) or safe_name(n) for n in names if n.endswith("_meta")}
    return sum(
        body.count(b"\n")
        for fname, body in files.items()
        if not (
            fname.removesuffix(".ndjson").endswith("_meta") or fname.removesuffix(".ndjson") in meta
        )
    )
