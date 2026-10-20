"""Fetch, validate and normalise the selected sources into data/."""

import datetime as dt
import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from .fetch import Response, fetch, is_soft_404
from .normalise import LayoutError, dump_line, normalise
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

    verdict = validate(resp, last)
    files = None
    if verdict.ok:
        try:
            files = normalise(verdict.data, src.layout, src.id_key, src.ids, src.bucket, src.names)
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

    root = data_dir / src.key
    old = read_tree(root)
    write_tree(root, old, files)
    lock[src.key] = {
        "sha256": sha,
        "bytes": len(resp.body),
        "fetched": today,
        "records": verdict.records,
        "keys": verdict.keys,
        "stale": False,
        "stale_since": None,
        "stale_reason": None,
    }
    return {
        **report,
        "status": "new" if last is None else "updated",
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
    for src in sources:
        r = sync_source(
            src, data_dir, lock, get=get, today=today, fetch_kwargs=fetch_kwargs, raw_dir=raw_dir
        )
        reports.append(r)
        write_lock(data_dir, lock)
        log(dump_line(r))
    return reports
