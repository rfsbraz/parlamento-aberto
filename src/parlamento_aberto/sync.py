"""Fetch, validate and normalise the selected sources into data/."""

import datetime as dt
import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from .fetch import Response, fetch, is_soft_404
from .normalise import LayoutError, as_int, dump_line, get_path, normalise, records_at
from .sources import Source
from .validate import validate

LOCK = "_meta/sources.lock.json"


def read_lock(data_dir: Path) -> dict:
    p = data_dir / LOCK
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def write_lock(data_dir: Path, lock: dict) -> None:
    p = data_dir / LOCK
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(lock, sort_keys=True, ensure_ascii=False, indent=1) + "\n"
    if not p.exists() or p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")


def record_ids(path: str, body: bytes) -> dict[str, bytes]:
    """Split a written file into records keyed by identity, to count changes."""
    if path.endswith(".json"):
        return {path: body}
    return {f"{path}:{line}": b"" for line in body.decode().splitlines()}


def diff_counts(old: dict[str, bytes], new: dict[str, bytes]) -> dict[str, int]:
    """Records added, removed and changed. A changed NDJSON line counts as one
    removed and one added, since lines carry no id of their own here."""
    o, n = {}, {}
    for p, b in old.items():
        o.update(record_ids(p, b))
    for p, b in new.items():
        n.update(record_ids(p, b))
    return {
        "added": len(n.keys() - o.keys()),
        "removed": len(o.keys() - n.keys()),
        "changed": sum(1 for k in n.keys() & o.keys() if n[k] != o[k]),
    }


def read_tree(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def write_tree(root: Path, old: dict[str, bytes], new: dict[str, bytes]) -> None:
    for path in old.keys() - new.keys():
        (root / path).unlink()
    for path, body in new.items():
        if old.get(path) != body:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes(body)
    for d in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()


def run_order(src: Source) -> bool:
    """Copies of another legislature run last, so that one is on disk to compare."""
    return src.copy_of is not None


def stored_ids(root: Path) -> set[int] | None:
    """Record ids of a records-layout folder, from the <bucket>/<id>.json names."""
    if not root.is_dir():
        return None
    return {int(p.stem) for p in root.glob("*/*.json")}


def copy_flags(src: Source, data, data_dir: Path) -> list[str]:
    """A copy_of file is expected to hold only records of that legislature.

    A record outside it means the AR now publishes real data for this
    legislature, so the data PR is held for review.
    """
    theirs = stored_ids(data_dir / src.dataset / src.copy_of)
    if not theirs:
        return [f"copy not checked: no stored {src.copy_of} copy"]
    ours = {as_int(get_path(r, src.id_key), src.id_key) for r in records_at(data, src.path)}
    extra = len(ours - theirs)
    if not extra:
        return []
    return [f"copy differs from {src.copy_of}: {extra} records not in {src.copy_of}"]


def sync_source(
    src: Source,
    data_dir: Path,
    lock: dict,
    *,
    get: Callable[[str], Response],
    today: str,
    fetch_kwargs: dict | None = None,
    raw_dir: Path | None = None,
) -> dict:
    last = lock.get(src.key)
    resp, attempts = fetch(src.url, get=get, **(fetch_kwargs or {}))
    report = {"source": src.key, "attempts": attempts, "flags": []}

    if raw_dir is not None and resp is not None and resp.status == 200 and not is_soft_404(resp):
        raw = raw_dir / f"{src.key}.json"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(resp.body)

    sha = hashlib.sha256(resp.body).hexdigest() if resp is not None else None
    if last and sha == last["sha256"]:
        if last.get("stale"):
            lock[src.key] = {**last, "stale": False, "stale_since": None, "stale_reason": None}
        return {**report, "status": "unchanged", "records": last["records"]}

    verdict = validate(resp, last, src.path)
    files = None
    if verdict.ok:
        try:
            if src.copy_of:
                verdict.flags += copy_flags(src, verdict.data, data_dir)
            else:
                files = normalise(
                    verdict.data, src.layout, src.id_key, src.ids, src.bucket, src.names, src.path
                )
        except LayoutError as e:
            verdict.ok, verdict.reason = False, f"layout: {e}"

    if not verdict.ok:
        entry = (
            dict(last) if last else {"sha256": None, "fetched": None, "records": 0, "keys": None}
        )
        entry["stale"] = True
        entry["stale_since"] = entry.get("stale_since") or today
        entry["stale_reason"] = verdict.reason
        lock[src.key] = entry
        return {
            **report,
            "status": "stale",
            "reason": verdict.reason,
            "stale_since": entry["stale_since"],
        }

    entry = {
        "sha256": sha,
        "bytes": len(resp.body),
        "fetched": today,
        "records": verdict.records,
        "keys": verdict.keys,
        "stale": False,
        "stale_since": None,
        "stale_reason": None,
    }
    status = "new" if last is None else "updated"
    if src.copy_of:
        # Fetched and hashed only: the records are the other legislature's.
        lock[src.key] = {**entry, "stored": False}
        return {**report, "status": status, "records": verdict.records, "flags": verdict.flags}

    root = data_dir / src.key
    old = read_tree(root)
    write_tree(root, old, files)
    lock[src.key] = entry
    return {
        **report,
        "status": status,
        "records": verdict.records,
        "files": len(files),
        "largest_file": max((len(b) for b in files.values()), default=0),
        "flags": verdict.flags,
        **diff_counts(old, files),
    }


def run(
    sources: list[Source],
    data_dir: Path,
    *,
    get: Callable[[str], Response],
    today: str | None = None,
    fetch_kwargs: dict | None = None,
    raw_dir: Path | None = None,
    log: Callable[[str], None] = lambda s: None,
) -> list[dict]:
    """Sources are processed one at a time, so requests to AR are sequential."""
    today = today or dt.date.today().isoformat()
    lock = read_lock(data_dir)
    reports = []
    for src in sorted(sources, key=run_order):
        r = sync_source(
            src, data_dir, lock, get=get, today=today, fetch_kwargs=fetch_kwargs, raw_dir=raw_dir
        )
        reports.append(r)
        write_lock(data_dir, lock)
        log(dump_line(r))
    return reports
