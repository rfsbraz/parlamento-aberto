"""Mask private citizens' personal numbers that the AR published inside free-text fields.

Two cases, both only inside string values (never keys, never numeric fields):

- a NIF label (NIF, NIF/NIPC, número fiscal, Contribuinte n.º) followed by a 9-digit
  number (also written 3-3-3 with spaces or dots) that passes the mod-11 check and
  starts like a personal NIF (1, 2, 3, 45, 70, 74, 75 or 78). Company NIPCs
  (5, 6, 8, 9, 71, 72, 77, 79) stay.
- Beneficiário/Beneficiária n.º followed by digits.

The number becomes [removido]; the label stays. Masking is idempotent. The guard fails
the sync if a match gets through. Nothing here ever prints a matched number.

python -m parlamento_aberto.privacy [--apply] [DATA_DIR]   counts per file; --apply masks
"""

import argparse
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

from .normalise import dump_line, dump_record

MASK = "[removido]"
PERSONAL_PREFIXES = ("1", "2", "3", "45", "70", "74", "75", "78")

_NO = r"n\.?\s*[º°o]\.?"
NIF_RE = re.compile(
    r"(?P<pre>(?:\bNIF\s*/\s*NIPC\b|\bNIF\b|\bn[úu]mero\s+fiscal\b|\bcontribuinte\s+"
    + _NO
    + r")[\s:.,-]*(?:"
    + _NO
    + r"[\s:.,-]*)?)(?<!\d)(?P<num>\d{9}(?!\d)|\d{3}(?P<sep>[ .])\d{3}(?P=sep)\d{3}(?![ .]?\d))",
    re.IGNORECASE,
)
BENEFICIARY_RE = re.compile(
    r"(?P<pre>\bbenefici[áa]ri[oa]\s*" + _NO + r"[\s:]*)(?P<num>\d+)", re.IGNORECASE
)
# Cheap byte-level prefilter: a label word, then a digit within a short span. It may
# over-match (escaped text, unrelated words); the real check runs on parsed strings.
_PREFILTER = re.compile(rb"(?i)(?:nif|fiscal|contribuinte|benefici)[^0-9]{0,200}[0-9]")


class UnmaskedError(RuntimeError):
    """A personal number survived masking. The message carries paths and counts only."""


def valid_nif(digits: str) -> bool:
    if len(digits) != 9 or not digits.isdigit():
        return False
    r = sum(int(d) * w for d, w in zip(digits[:8], range(9, 1, -1), strict=True)) % 11
    return int(digits[8]) == (0 if r < 2 else 11 - r)


def personal_nif(digits: str) -> bool:
    return digits.startswith(PERSONAL_PREFIXES) and valid_nif(digits)


def mask_text(text: str) -> tuple[str, int]:
    count = 0

    def nif(m: re.Match) -> str:
        nonlocal count
        if not personal_nif(re.sub(r"\D", "", m["num"])):
            return m[0]
        count += 1
        return m["pre"] + MASK

    def beneficiary(m: re.Match) -> str:
        nonlocal count
        count += 1
        return m["pre"] + MASK

    text = NIF_RE.sub(nif, text)
    text = BENEFICIARY_RE.sub(beneficiary, text)
    return text, count


def _mask(obj) -> tuple[object, int]:
    if isinstance(obj, str):
        return mask_text(obj)
    if isinstance(obj, list):
        out, total = [], 0
        for v in obj:
            v, n = _mask(v)
            out.append(v)
            total += n
        return out, total
    if isinstance(obj, dict):
        out, total = {}, 0
        for k, v in obj.items():
            out[k], n = _mask(v)
            total += n
        return out, total
    return obj, 0


def mask_tree(obj) -> tuple[object, int]:
    """Mask every string value in a parsed JSON tree. Returns (new tree, matches)."""
    return _mask(obj)


def mask_file(path: str, body: bytes) -> tuple[bytes, int]:
    """Mask one file written by normalise (.json record or .ndjson table).

    Only a record with a match is re-serialised, in the same format normalise writes,
    so every other byte stays as it was. Other files are returned unchanged.
    """
    if not path.endswith((".json", ".ndjson")) or not _PREFILTER.search(body):
        return body, 0
    if path.endswith(".ndjson"):
        lines, total = body.decode("utf-8").split("\n"), 0
        for i, line in enumerate(lines):
            if not line or not _PREFILTER.search(line.encode()):
                continue
            rec, n = _mask(json.loads(line))
            if n:
                _same_format(path, line, dump_line(json.loads(line)))
                lines[i] = dump_line(rec)
                total += n
        return ("\n".join(lines).encode() if total else body), total
    text = body.decode("utf-8")
    rec, n = _mask(json.loads(text))
    if not n:
        return body, 0
    _same_format(path, text, dump_record(json.loads(text)).decode())
    return dump_record(rec), n


def _same_format(path: str, original: str, redumped: str) -> None:
    if original != redumped:
        raise ValueError(f"{path}: not in the normalise format, cannot mask it in place")


def guard(files: dict[str, bytes]) -> None:
    """Fail if any file still holds a match. Reports paths and counts, never values."""
    hits = {p: n for p, b in files.items() if (n := mask_file(p, b)[1])}
    if hits:
        detail = ", ".join(f"{p}: {n}" for p, n in sorted(hits.items()))
        raise UnmaskedError(f"unmasked personal numbers in {len(hits)} files ({detail})")


def data_files(data_dir: Path) -> Iterable[Path]:
    for p in sorted(data_dir.rglob("*")):
        if p.is_file() and p.suffix in (".json", ".ndjson") and "_meta" not in p.parts:
            yield p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="parlamento_aberto.privacy")
    ap.add_argument("data", type=Path, nargs="?", default=Path("data"))
    ap.add_argument("--apply", action="store_true", help="mask in place (default: check only)")
    a = ap.parse_args(argv)
    total = 0
    for p in data_files(a.data):
        rel = p.relative_to(a.data).as_posix()
        body = p.read_bytes()
        out, n = mask_file(rel, body)
        if not n:
            continue
        total += n
        print(f"{rel}: {n}")
        if a.apply:
            p.write_bytes(out)
    verb = "masked" if a.apply else "unmasked"
    print(f"{total} {verb} in data/")
    return 1 if total and not a.apply else 0


if __name__ == "__main__":
    sys.exit(main())
