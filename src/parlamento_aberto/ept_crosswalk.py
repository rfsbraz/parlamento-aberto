"""EpT holder to AR cadastro_id crosswalk (#47).

The Entidade para a Transparência (docs/sources/ept.md) has no AR id, so each EpT holder who
is a Deputado or Deputada is matched to a cadastro_id by normalised full name against
InformacaoBase: XVII for entity 4508, XIV to XVI for entity 510 (titularidades before XVII,
from 2021). RegistoBiografico XVI repeats the XVII register, so it is not used.

A holder with no name match, or with more than one candidate, must be listed in
models/seeds/ept_holder_overrides.csv, with a cadastro_id or with it empty (unmatched) and a
note. The result is written to models/seeds/ept_holders.csv, ids only:

    python -m parlamento_aberto.ept_crosswalk --titularidades 4508.json 510.json --data data

Each --titularidades file is a /publicquery response (or its items list). Names are only
read in memory; nothing but ids and the match kind is written.
"""

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from collections.abc import Iterable
from pathlib import Path

SEEDS = Path(__file__).parent / "models" / "seeds"
SEED_NAME = "ept_holders.csv"
OVERRIDES_NAME = "ept_holder_overrides.csv"
# EpT role ids: 8 Deputado, 232 Deputada.
DEPUTY_ROLES = {8, 232}
# EpT entity id -> AR legislatures its titularidades cover.
ENTITY_LEGISLATURES = {4508: ("XVII",), 510: ("XIV", "XV", "XVI")}
FIELDS = ("ept_holder_id", "cadastro_id", "match")
NINE_DIGITS = re.compile(r"(?<!\d)\d{9}(?!\d)")
PRIVATE_KEY = re.compile(r"nif|nipc", re.IGNORECASE)


class CrosswalkError(ValueError):
    pass


def normalise_name(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z]+", " ", s).split())


def find_leaks(text: str, label: str) -> list[str]:
    """Where text holds a nif/nipc key or column, or a 9-digit value. Never echoes a value."""
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        if NINE_DIGITS.search(line):
            found.append(f"{label} line {n}: 9-digit value")
    keys: list[str] = []
    try:
        _collect_keys(json.loads(text), keys)
    except ValueError:
        first = text.splitlines()[0] if text else ""
        keys = next(csv.reader(io.StringIO(first)), [])
    found += [f"{label}: key {k!r}" for k in sorted(set(keys)) if PRIVATE_KEY.search(k)]
    return found


def _collect_keys(value, keys: list[str]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            keys.append(str(k))
            _collect_keys(v, keys)
    elif isinstance(value, list):
        for v in value:
            _collect_keys(v, keys)


def match_holders(
    titularidades: Iterable[dict],
    deputies: Iterable[dict],
    overrides: dict[int, int | None],
) -> list[dict]:
    """One row per EpT deputy holder: name match, override or unmatched.

    titularidades: EpT items with holderId, holder, entityId and roleId.
    deputies: AR rows with cadastro_id, full_name and legislature.
    overrides: holder id -> cadastro_id, or None for a holder with no AR deputy.
    """
    by_name: dict[tuple[str, str], set[int]] = {}
    for dep in deputies:
        if dep.get("full_name"):
            key = (dep["legislature"], normalise_name(dep["full_name"]))
            by_name.setdefault(key, set()).add(int(dep["cadastro_id"]))

    holders: dict[int, tuple[set[str], set[int]]] = {}
    for t in titularidades:
        if t["roleId"] not in DEPUTY_ROLES:
            continue
        if t["entityId"] not in ENTITY_LEGISLATURES:
            raise CrosswalkError(f"holder {t['holderId']}: unknown entity {t['entityId']}")
        names, entities = holders.setdefault(int(t["holderId"]), (set(), set()))
        names.add(normalise_name(t["holder"]))
        entities.add(t["entityId"])

    rows, problems = [], []
    for holder in sorted(set(holders) | set(overrides)):
        if holder not in holders:
            problems.append(f"holder {holder}: override for a holder who is not an EpT deputy")
            continue
        if holder in overrides:
            cadastro_id = overrides[holder]
            match = "unmatched" if cadastro_id is None else "override"
            rows.append({"ept_holder_id": holder, "cadastro_id": cadastro_id, "match": match})
            continue
        names, entities = holders[holder]
        legislatures = {leg for e in entities for leg in ENTITY_LEGISLATURES[e]}
        candidates = set().union(
            *(by_name.get((leg, n), set()) for leg in legislatures for n in names)
        )
        if len(candidates) == 1:
            rows.append({"ept_holder_id": holder, "cadastro_id": candidates.pop(), "match": "name"})
        elif candidates:
            ids = ", ".join(str(c) for c in sorted(candidates))
            problems.append(f"holder {holder}: {len(candidates)} candidates ({ids})")
        else:
            problems.append(f"holder {holder}: no match")
    if problems:
        raise CrosswalkError(f"add these to {OVERRIDES_NAME}:\n" + "\n".join(problems))
    return rows


def read_overrides(path: Path) -> dict[int, int | None]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out: dict[int, int | None] = {}
    for r in rows:
        if not r.get("note", "").strip():
            raise CrosswalkError(f"holder {r['ept_holder_id']}: override without a note")
        out[int(r["ept_holder_id"])] = int(r["cadastro_id"]) if r["cadastro_id"].strip() else None
    return out


def read_deputies(data_dir: Path) -> list[dict]:
    legislatures = sorted({leg for legs in ENTITY_LEGISLATURES.values() for leg in legs})
    out = []
    for leg in legislatures:
        path = data_dir / "informacao_base" / leg / "deputados.ndjson"
        for line in path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            out.append(
                {
                    "cadastro_id": int(r["DepCadId"]),
                    "full_name": r.get("DepNomeCompleto"),
                    "legislature": leg,
                }
            )
    return out


def read_titularidades(paths: Iterable[Path]) -> list[dict]:
    out = []
    for path in paths:
        body = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(body, dict):
            data = body["data"]
            if data.get("total") is not None and data["total"] != len(data["items"]):
                raise CrosswalkError(f"{path.name}: {len(data['items'])} of {data['total']} rows")
            body = data["items"]
        out += body
    return out


def write_seed(rows: list[dict], seeds_dir: Path) -> Path:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: "" if r[k] is None else r[k] for k in FIELDS})
    text = buf.getvalue()
    leaks = find_leaks(text, SEED_NAME)
    if leaks:
        raise CrosswalkError("refusing to write the seed: " + "; ".join(leaks))
    path = seeds_dir / SEED_NAME
    path.write_text(text, encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m parlamento_aberto.ept_crosswalk")
    p.add_argument("--titularidades", type=Path, nargs="+", required=True)
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--seeds", type=Path, default=SEEDS)
    a = p.parse_args(argv)
    try:
        rows = match_holders(
            read_titularidades(a.titularidades),
            read_deputies(a.data),
            read_overrides(a.seeds / OVERRIDES_NAME),
        )
        write_seed(rows, a.seeds)
    except CrosswalkError as e:
        print(e, file=sys.stderr)
        return 1
    kinds = {m: sum(r["match"] == m for r in rows) for m in ("name", "override", "unmatched")}
    print(f"{len(rows)} holders: " + ", ".join(f"{v} {k}" for k, v in kinds.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
