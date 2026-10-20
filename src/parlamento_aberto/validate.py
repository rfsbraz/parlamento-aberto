"""Decide whether a download replaces the last good copy."""

import json
from dataclasses import dataclass, field

from .fetch import Response, is_soft_404
from .normalise import LayoutError, count_records, records_at, top_level_keys

ROW_DROP_LIMIT = 0.05


@dataclass
class Verdict:
    ok: bool
    reason: str | None = None
    data: object = None
    records: int = 0
    keys: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def validate(resp: Response | None, last: dict | None, path: str | None = None) -> Verdict:
    """Reject HTML, parse failures and empty files that used to have records.

    Flag, but accept, a record drop over 5% and a changed key set.
    """
    if resp is None:
        return Verdict(False, "download failed")
    if resp.status != 200:
        return Verdict(False, f"HTTP {resp.status}")
    if is_soft_404(resp):
        return Verdict(False, "HTML instead of JSON (soft 404)")
    try:
        data = json.loads(resp.body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return Verdict(False, f"does not parse: {e.__class__.__name__}")
    last_records = (last or {}).get("records", 0)
    if data in (None, [], {}) and last_records > 0:
        return Verdict(False, f"empty file, last good copy had {last_records} records")
    if not isinstance(data, (list, dict)) and data is not None:
        return Verdict(False, f"unexpected top-level {type(data).__name__}")
    if path:
        try:
            data_at_path = records_at(data, path)
        except LayoutError as e:
            return Verdict(False, f"layout: {e}")
        records, keys = len(data_at_path), top_level_keys(data_at_path)
    else:
        records = count_records(data) if data is not None else 0
        keys = top_level_keys(data)
    flags = []
    if last and last_records and records < last_records * (1 - ROW_DROP_LIMIT):
        flags.append(f"row drop {last_records} to {records}")
    if last and last.get("keys") is not None and last["keys"] != keys:
        added = sorted(set(keys) - set(last["keys"]))
        removed = sorted(set(last["keys"]) - set(keys))
        flags.append(f"key set changed (added {added}, removed {removed})")
    return Verdict(True, data=data, records=records, keys=keys, flags=flags)
