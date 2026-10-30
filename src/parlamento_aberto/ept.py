"""Fetch the EpT register of interests for XVI and XVII (#44): metadata and tab 4 only.

The Entidade para a Transparência (EpT) publishes the declarations of the Assembleia da
República deputies through an unauthenticated JSON API (https://api.entidadetransparencia.pt):

- ``POST /publicquery`` lists the titularidades (holder, role) of an entity, paged;
- ``POST /publicquery/search`` lists the declarations of one holder in an entity, paged,
  with every state (Published, Replaced, Modified and so on);
- ``POST /publicquery/getdeclaration`` returns one declaration.

A declaration carries the holder's full NIF in a top-level ``nif`` field, personal data,
income and assets in other tabs, attachments, and the entity NIF/NIPC in one tab 4 column.
``strip`` keeps an allow-list of metadata keys and the known tab 4 columns only, and
replaces any 9-digit number left in a value. In the entity NIF/NIPC column it keeps only a
valid company NIPC (see ``is_company_nipc``) and drops anything else, such as a sole
trader's personal NIF. The associations section (memberships) is dropped whole, without
reading a cell: Reg. EpT 258/2024, art. 15.º, n.º 1, al. b) keeps it out of public access.
Nothing is written before ``assert_clean`` passes, and the raw response is never stored
or logged.

Requests go one at a time, at most one per second. The run is incremental: a declaration
is fetched again only when it is new or its state changed. Replaced and modified versions
are kept, since each has its own id.

Layout under ``data/ept_registo_interesses/``:

- ``titularidades.ndjson``: one line per titularidade (entity, role, holder), by id;
- ``declarations.ndjson``: one line per declaration from the search, by id;
- ``<entityId>/<id // 1000>/<id>.json``: one stripped declaration.
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable
from pathlib import Path

API = "https://api.entidadetransparencia.pt"
ORIGIN = "https://entidadetransparencia.pt"
USER_AGENT = (
    "parlamento-aberto/0.1 (+https://github.com/rfsbraz/parlamento-aberto; "
    "sequential requests, 1 per second)"
)
DATASET = "ept_registo_interesses"
# 510 is "Assembleia da República" (XVI and earlier titularidades), 4508 is
# "Assembleia da República - XVII Legislatura".
ENTITIES = (510, 4508)
INTERVAL = 1.0
PAGE_SIZE = 500

TAB4 = "1483a8d1-adca-4f39-8038-98cc6f728fcb"
TAB4_GROUP = "88ff2a6e-3702-4687-9f05-2738f70ccbd0"
# Tab 4 sections that are never read, stored or parsed. Their cells are not looked at.
DROPPED_SECTIONS = {
    # Filiação ou funções em entidades de natureza associativa: not public under
    # Reg. EpT 258/2024, art. 15.º, n.º 1, al. b).
    "cd0e811a-d9bb-49ee-b0f0-1dae0680eb22": "association",
}
# section GUID -> (category, entity NIF/NIPC column or None, other columns kept)
SECTIONS = {
    "2c6d9562-dea5-488b-9afe-42519c636daf": (
        "activity",
        "col9",
        ("col1", "col2", "col3", "col4", "col5", "col6", "col7"),
    ),
    "62fb0107-a68d-4ba2-822b-bc8adc54369b": (
        "support",
        "col6",
        ("col1", "col2", "col3", "col4", "col5", "col7", "col8", "col9"),
    ),
    "b1f8c095-fe0c-4bb3-b493-902dc0c31232": (
        "service",
        "col6",
        ("col1", "col2", "col3", "col4", "col5", "col7", "col8"),
    ),
    "9b58c917-b14c-4eed-9b3c-40c3d99d45da": (
        "society",
        "col7",
        ("col1", "col2", "col3", "col4", "col5", "col6", "col8"),
    ),
    "fd85f91f-2803-41bc-b315-ede3a4a66d4e": (
        "other_situation",
        None,
        ("col1", "col2", "col3", "col4", "col6"),
    ),
}
for _cat, _nif, _cols in SECTIONS.values():
    assert _nif not in _cols
assert not set(SECTIONS) & set(DROPPED_SECTIONS)

META_KEYS = (
    "id",
    "natureType",
    "stateType",
    "relatedDeclarationId",
    "year",
    "entity",
    "entityId",
    "board",
    "boardId",
    "role",
    "roleId",
    "holder",
    "holderId",
    "startDate",
    "endDate",
    "submitedDate",
    "unavailableSections",
)
TITULARIDADE_KEYS = (
    "id",
    "entityId",
    "entity",
    "roleId",
    "role",
    "holderId",
    "holder",
    "beginDate",
    "endDate",
)
SEARCH_KEYS = (
    "id",
    "natureType",
    "stateType",
    "relatedDeclarationId",
    "year",
    "creationDate",
    "deliveryDate",
    "startDate",
    "endDate",
)

# Nine digits not part of a longer number, also split as 3+3+3 by a space, dot or dash.
NINE = re.compile(r"(?<!\d)\d{3}[ .-]?\d{3}[ .-]?\d{3}(?!\d)")
NIF_KEY = re.compile(r"nif|nipc", re.IGNORECASE)
# What the strip drops before anything is stored, and how the reuse note names it. The note
# in release.EPT_TERMS and the docs is built from this, and a test keeps them in step.
STRIPPED = {"nif": "o NIF dos titulares"}
REMOVED = "[removido]"
# Company NIPC ranges kept: 5 (legal persons), 6 (public bodies), 71, 72 and 79. Every
# other prefix can identify a person and is dropped like a personal NIF (Lei 52/2019,
# art. 17.º, n.º 2, al. a); Reg. EpT 258/2024, art. 15.º, n.º 2, al. a)): 1 to 4 are
# people, 8 is the old sole-trader range, 9x covers condominiums, irregular companies and
# sole traders' estates, and the other 7x prefixes, 77 included, are estates and the like.
# Keep in step with privacy.COMPANY_PREFIXES.
NIPC_PREFIX = re.compile(r"^(?:[56]|7[129])")
NIPC_SEPARATORS = re.compile(r"[\s.-]")


def check_digit_ok(digits: str) -> bool:
    """Portuguese NIF/NIPC mod-11 check digit."""
    total = sum(int(d) * w for d, w in zip(digits[:8], range(9, 1, -1), strict=True))
    r = total % 11
    return int(digits[8]) == (0 if r < 2 else 11 - r)


def is_company_nipc(v) -> bool:
    """True for a 9-digit string in a company range with a valid check digit."""
    return (
        isinstance(v, str)
        and len(v) == 9
        and v.isascii()
        and v.isdigit()
        and bool(NIPC_PREFIX.match(v))
        and check_digit_ok(v)
    )


def company_nipc(v) -> str | None:
    """The NIPC column value: a valid company NIPC, or None (dropped)."""
    if not isinstance(v, str):
        return None
    s = NIPC_SEPARATORS.sub("", v.strip())
    if s[:2].upper() == "PT":
        s = s[2:]
    return s if is_company_nipc(s) else None


class LeakError(ValueError):
    """A nif key or a 9-digit value is about to be written. Never carries the value."""


class ShapeError(ValueError):
    """The declaration does not have the tab 4 shape this module knows."""


def clean(v):
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return NINE.sub(REMOVED, v)
    if isinstance(v, int | float):
        return v if not NINE.search(str(v)) else REMOVED
    if isinstance(v, list):
        return [clean(x) for x in v]
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items() if not NIF_KEY.search(str(k))}
    return v


def _assert_tab4(tab4, path: str) -> None:
    """A valid company NIPC is allowed only in the NIPC column of a known section."""
    if not isinstance(tab4, dict):
        return assert_clean(tab4, path, _top=False)
    for guid, rows in tab4.items():
        here = f"{path}.{guid}"
        if guid in DROPPED_SECTIONS:
            raise LeakError(f"{DROPPED_SECTIONS[guid]} section at {here}")
        nif_col = SECTIONS[guid][1] if guid in SECTIONS else None
        if nif_col is None or not isinstance(rows, list):
            assert_clean({guid: rows}, path, _top=False)
            continue
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                assert_clean(row, f"{here}[{i}]", _top=False)
                continue
            for col, v in row.items():
                if col == nif_col and v is not None:
                    if not is_company_nipc(v):
                        raise LeakError(f"not a company NIPC at {here}[{i}].{col}")
                else:
                    assert_clean({col: v}, f"{here}[{i}]", _top=False)


def assert_clean(obj, path: str = "", *, _top: bool = True) -> None:
    """Raise LeakError on any nif/nipc key or 9-digit value. The message names the path only.

    The one exception is a valid company NIPC in the NIPC column of a known tab 4 section,
    in a stored declaration (a top-level dict with a ``tab4`` key).
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = f"{path}.{k}" if path else str(k)
            if _top and k == "tab4" and not NINE.search(str(k)):
                _assert_tab4(v, here)
                continue
            if NIF_KEY.search(str(k)):
                raise LeakError(f"nif key at {here}")
            if NINE.search(str(k)):
                raise LeakError(f"9-digit key under {path or '<root>'}")
            assert_clean(v, here, _top=False)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            assert_clean(v, f"{path}[{i}]", _top=False)
    elif isinstance(obj, bool) or obj is None:
        return
    elif NINE.search(str(obj)):
        raise LeakError(f"9-digit value at {path or '<root>'}")


def _tab4(sections: list) -> dict:
    out = {}
    for sec in sections:
        key = sec.get("key")
        if key in DROPPED_SECTIONS:
            continue
        if key not in SECTIONS:
            raise ShapeError(f"unknown tab 4 section {key}")
        _, nif_col, cols = SECTIONS[key]
        rows = []
        for row in sec.get("value") or []:
            vals = {}
            for cell in row.get("value") or []:
                col = str(cell.get("key", "")).rsplit("-", 1)[-1]
                if not cell.get("isVisible"):
                    continue
                if col == nif_col:
                    nipc = company_nipc(cell.get("value"))
                    if nipc is not None:
                        vals[col] = nipc
                elif col in cols:
                    vals[col] = clean(cell.get("value"))
            if any(v is not None for v in vals.values()):
                rows.append(vals)
        out[key] = rows
    return out


def strip(data: dict) -> dict:
    """Keep the metadata allow-list and tab 4. Everything else, including nif, is dropped."""
    out = {k: clean(data.get(k)) for k in META_KEYS}
    out["id"] = data["id"]
    out["tab4"] = None
    tabs = [t for t in (data.get("data") or {}).get("value") or [] if t.get("key") == TAB4]
    if tabs:
        groups = tabs[0].get("value") or []
        for g in groups:
            if g.get("key") != TAB4_GROUP:
                raise ShapeError(f"unknown tab 4 group {g.get('key')}")
        out["tab4"] = _tab4(groups[0].get("value") or []) if groups else {}
    return out


def pick(item: dict, keys) -> dict:
    return {k: clean(item.get(k)) for k in keys}


class Throttle:
    """At most one request per ``interval`` seconds."""

    def __init__(
        self,
        interval: float = INTERVAL,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.interval, self.clock, self.sleep = interval, clock, sleep
        self.last: float | None = None

    def wait(self) -> None:
        if self.last is not None:
            gap = self.last + self.interval - self.clock()
            if gap > 0:
                self.sleep(gap)
        self.last = self.clock()


class ApiError(RuntimeError):
    pass


def http_post(path: str, body: dict, timeout: float = 120) -> dict:
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Origin": ORIGIN, "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # The body is not read: it can echo the request or the record.
        raise ApiError(f"{path}: HTTP {e.code}") from None


class Client:
    def __init__(
        self,
        post: Callable[[str, dict], dict] = http_post,
        throttle: Throttle | None = None,
        page_size: int = PAGE_SIZE,
        attempts: int = 3,
        backoff: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.post, self.throttle, self.page_size = post, throttle, page_size
        self.attempts, self.backoff, self.sleep = attempts, backoff, sleep

    def call(self, path: str, body: dict) -> dict:
        for attempt in range(1, self.attempts + 1):
            if self.throttle:
                self.throttle.wait()
            try:
                resp = self.post(path, body)
            except (OSError, ApiError):
                if attempt == self.attempts:
                    raise
                self.sleep(self.backoff * attempt)
                continue
            if resp.get("code") != 0:
                raise ApiError(f"{path}: code {resp.get('code')}")
            return resp["data"]
        raise AssertionError("unreachable")

    def paged(self, path: str, body: dict) -> list[dict]:
        items, n = [], 1
        while True:
            data = self.call(
                path, {**body, "pageNumber": n, "sortBy": None, "pageSize": self.page_size}
            )
            items += data.get("items") or []
            if n >= (data.get("pageCount") or 1):
                return items
            n += 1

    def titularidades(self, entity_id: int) -> list[dict]:
        return self.paged("/publicquery", {"EntityId": entity_id})

    def declarations(self, entity_id: int, holder_id: int) -> list[dict]:
        return self.paged("/publicquery/search", {"HolderId": holder_id, "EntityId": [entity_id]})

    def declaration(self, decl_id: int) -> dict:
        return self.call("/publicquery/getdeclaration", {"Id": decl_id, "isDraft": False})


def write_json(path: Path, obj) -> None:
    assert_clean(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=1) + "\n")


def write_ndjson(path: Path, rows: list[dict]) -> None:
    assert_clean(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows)
    path.write_text(text)


def read_index(root: Path) -> dict[int, dict]:
    path = root / "declarations.ndjson"
    if not path.exists():
        return {}
    return {r["id"]: r for r in map(json.loads, path.read_text().splitlines()) if r}


def decl_path(root: Path, entity_id: int, decl_id: int) -> Path:
    return root / str(entity_id) / str(decl_id // 1000) / f"{decl_id}.json"


def run(
    client: Client,
    data_dir: Path,
    *,
    entities=ENTITIES,
    dry_run: bool = False,
    limit: int | None = None,
    log: Callable[[str], None] = print,
) -> dict:
    """Sync the dataset into ``data_dir``. Logs and the report carry counts and ids only."""
    root = data_dir / DATASET
    tits, pairs = [], []
    by_entity = {}
    for e in entities:
        rows = client.titularidades(e)
        by_entity[str(e)] = len(rows)
        tits += [pick(r, TITULARIDADE_KEYS) for r in rows]
        for h in sorted({r["holderId"] for r in rows}):
            pairs.append((e, h))
        log(f"entity {e}: {len(rows)} titularidades")
    if limit is not None:
        pairs = pairs[:limit]
    log(f"{len(pairs)} entity/holder pairs to search")

    old = read_index(root)
    index = dict(old)
    todo = []
    for n, (e, h) in enumerate(pairs, 1):
        for item in client.declarations(e, h):
            row = {**pick(item, SEARCH_KEYS), "entityId": e, "holderId": h}
            prev = old.get(row["id"])
            index[row["id"]] = row
            if (
                prev is None
                or prev.get("stateType") != row["stateType"]
                or not decl_path(root, e, row["id"]).exists()
            ):
                todo.append(row)
        if n % 50 == 0:
            log(f"searched {n}/{len(pairs)}")
    wanted = set(pairs)
    seen = {r["id"] for r in index.values() if (r["entityId"], r["holderId"]) in wanted}
    report = {
        "titularidades": len(tits),
        "by_entity": by_entity,
        "pairs": len(pairs),
        "declarations": len(seen),
        "states": dict(sorted(Counter(index[i]["stateType"] for i in seen).items())),
        "to_fetch": len(todo),
        "fetched": 0,
        "failed": [],
    }
    log(f"{report['declarations']} declarations, {len(todo)} new or changed")
    if dry_run:
        return report

    for n, row in enumerate(todo, 1):
        try:
            rec = strip(client.declaration(row["id"]))
        except ApiError as err:
            report["failed"].append({"id": row["id"], "error": str(err)})
            index[row["id"]] = old.get(row["id"], {**row, "stateType": None})
            continue
        if rec["id"] != row["id"]:
            raise ShapeError(f"asked for {row['id']}, got another id")
        write_json(decl_path(root, row["entityId"], row["id"]), rec)
        report["fetched"] += 1
        if n % 50 == 0:
            log(f"fetched {n}/{len(todo)}")
    if limit is None:
        write_ndjson(root / "titularidades.ndjson", sorted(tits, key=lambda r: r["id"]))
    write_ndjson(root / "declarations.ndjson", [index[i] for i in sorted(index)])
    log(f"fetched {report['fetched']}, failed {len(report['failed'])}")
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="parlamento_aberto.ept")
    p.add_argument("cmd", choices=["fetch", "dry-run"])
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--entity", type=int, action="append", help="EpT entity id (default 510, 4508)")
    p.add_argument("--limit", type=int, help="only the first N entity/holder pairs")
    p.add_argument("--report", type=Path, help="write the run report as JSON")
    a = p.parse_args(argv)
    report = run(
        Client(throttle=Throttle()),
        a.data,
        entities=tuple(a.entity or ENTITIES),
        dry_run=a.cmd == "dry-run",
        limit=a.limit,
        log=lambda line: print(line, file=sys.stderr, flush=True),
    )
    assert_clean(report)
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if a.report:
        a.report.write_text(text + "\n")
    print(text)
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
