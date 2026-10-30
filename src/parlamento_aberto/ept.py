"""Fetch the EpT register of interests for XVI and XVII (#44, #148).

The Entidade para a Transparência (EpT) publishes the declarations of the Assembleia da
República deputies through an unauthenticated JSON API (https://api.entidadetransparencia.pt):

- ``POST /publicquery`` lists the titularidades (holder, role) of an entity, paged;
- ``POST /publicquery/search`` lists the declarations of one holder in an entity, paged,
  with every state (Published, Replaced, Modified and so on);
- ``POST /publicquery/getdeclaration`` returns one declaration.

A declaration carries the holder's full NIF in a top-level ``nif`` field, personal data
(tab 2), income and assets (tab 3), interests (tab 4), the entity NIF/NIPC in one tab 4
column and a list of attachments. ``strip`` keeps an allow-list of metadata keys, every
cell the EpT shows in tabs 2 and 3, the known tab 4 columns and the attachment metadata,
and replaces any 9-digit number left in a value. In the tab 4 entity NIF/NIPC column it
keeps only a valid company NIPC (see ``is_company_nipc``) and drops anything else, such as
a sole trader's personal NIF. Tabs 2 and 3 are stored by position (``0.3.1.2``) with the
table name and column, never by the EpT keys: some of those GUIDs read as 9 digits. The
API serves no attachment file, so only the name, size, format, section and observations
are kept. The associations section (memberships) of tab 4 is kept apart, under
``associations``, with the same rule for its NIF/NIPC column, so it can be dropped on its
own.
Nothing is written before ``assert_clean`` passes, and the raw response is never stored
or logged.

Requests go one at a time, at most one per second. The run is incremental: a declaration
is fetched again only when it is new, its state changed or its file was stored by an
older strip. Replaced and modified versions
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

TAB2 = "7df770a3-e06b-4448-b5ac-c1b162c80fcc"
TAB3 = "ecc58cb2-0808-4d2f-bb2b-64b87617a4ac"
TAB4 = "1483a8d1-adca-4f39-8038-98cc6f728fcb"
# Tables of tab 3, named after the EpT frontend's export functions (addTable...). Some
# GUIDs hold more than one kind of good: the row says which.
TAB3_SECTIONS = {
    "da9c415a-e950-4ce9-ab58-5ce1c1b5af53": "employment_income",
    "112c6561-4a51-4f79-b637-bbd8d2c0c74c": "real_estate_portugal",
    "252ba9e4-bbba-4660-be9e-470b263c4832": "real_estate_abroad",
    "70fdd906-58d5-4682-967d-90ae90805436": "shares_portugal",
    "cdeffda1-efd5-44c7-b256-1822dd5bafe0": "shares_abroad",
    "53168cfb-433e-41e6-9b23-33c1eac7fa6f": "vehicles_portugal",
    "05d989a9-7824-459d-aeb3-cc13f1f70c00": "vehicles_abroad",
    "1a5d2580-aaf3-4874-9e20-68ce10671263": "securities_portugal",
    "4a8f53d5-34c2-4bda-b3ea-ec2b157efe67": "securities_abroad",
    "e498015f-062e-4fcd-93a8-c5f1393f568b": "term_deposits_portugal",
    "9d7b601c-dc39-4460-a3ab-3bc1178cbae7": "term_deposits_abroad",
    "7bf6ccdd-f797-4339-8c76-18a248882016": "financial_investments_portugal",
    "5eea74fb-2cdc-4897-8f04-ce31341f7296": "financial_investments_abroad",
    "873b46af-f3a5-4329-9aa0-a04fd1114467": "demand_deposits_portugal",
    "151ea0ca-b4a5-4764-a461-67d0c300c915": "demand_deposits_abroad",
    "58adafd6-226e-4978-a48c-66f53affd3ac": "credits_portugal",
    "f4838f1a-b32e-43bd-9f3e-6de9ff72526d": "credits_abroad",
    "8a7cfdae-1d47-41f9-a366-5ba020c1b90f": "other_assets_portugal",
    "ea846529-712c-4b47-953f-5b39015c4f17": "other_assets_abroad",
    "27bb57dd-0fd8-4595-aaca-53bf1634ca87": "liabilities_portugal",
    "50117239-0a0b-427d-9c23-f33c766b2b3a": "liabilities_abroad",
    "ffd1a4f7-c19e-4e75-b722-11c6e3fae511": "guarantees_portugal",
    "3737df7d-c0e0-4a24-8bce-346a479971f5": "guarantees_abroad",
    "60c13abc-b075-475c-86c5-fa69a7cae259": "asset_changes",
}
FIELD_TABS = {"tab2": TAB2, "tab3": TAB3}
# The holder's NIF in tab 2 ("Número de Identificação Fiscal (NIF)"). Never kept, shown or not.
HOLDER_NIF_CELLS = {"d155af2b-21e9-475f-be81-8e42bc5a5641"}
COLUMN = re.compile(r"-(col\d+)$")
ATTACHMENT_KEYS = ("name", "size", "format", "sectionType", "observations")
TAB4_GROUP = "88ff2a6e-3702-4687-9f05-2738f70ccbd0"
# Filiação ou funções em entidades de natureza associativa. Stored under ``associations``,
# never inside ``tab4``. col8 is "NIF/NIPC/Tax identification number ou equivalente".
ASSOCIATION = "cd0e811a-d9bb-49ee-b0f0-1dae0680eb22"
ASSOCIATION_NIPC = "col8"
ASSOCIATION_COLS = ("col1", "col2", "col3", "col4", "col5", "col6", "col7")
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
assert ASSOCIATION not in SECTIONS

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
        if guid == ASSOCIATION:
            raise LeakError(f"association section inside tab4 at {here}")
        nif_col = SECTIONS[guid][1] if guid in SECTIONS else None
        if nif_col is None or not isinstance(rows, list):
            assert_clean({guid: rows}, path, _top=False)
            continue
        _assert_rows(rows, nif_col, here)


def _assert_rows(rows, nif_col: str, here: str) -> None:
    """A valid company NIPC is allowed in ``nif_col`` only."""
    if not isinstance(rows, list):
        return assert_clean(rows, here, _top=False)
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

    The one exception is a valid company NIPC in the NIPC column of a known tab 4 section
    or of the associations, in a stored declaration (top-level ``tab4`` or ``associations``).
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = f"{path}.{k}" if path else str(k)
            if _top and k == "tab4":
                _assert_tab4(v, here)
                continue
            if _top and k == "associations":
                _assert_rows(v, ASSOCIATION_NIPC, here)
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


def _rows(sec: dict, nif_col, cols) -> list:
    """Visible cells of a tab 4 table. The NIF/NIPC column keeps a company NIPC only."""
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
    return rows


def _tab4(sections: list) -> dict:
    out = {}
    for sec in sections:
        key = sec.get("key")
        if key == ASSOCIATION:
            continue
        if key not in SECTIONS:
            raise ShapeError(f"unknown tab 4 section {key}")
        _, nif_col, cols = SECTIONS[key]
        out[key] = _rows(sec, nif_col, cols)
    return out


def _associations(sections: list) -> list:
    sec = next((s for s in sections if s.get("key") == ASSOCIATION), None)
    return _rows(sec, ASSOCIATION_NIPC, ASSOCIATION_COLS) if sec else []


def _fields(node, tab: str, path: str, section, out: list) -> None:
    """Append every visible, non-empty leaf under ``node`` as a positional record."""
    if not isinstance(node, dict) or node.get("isVisible") is not True:
        return
    if node.get("isDeleted") is True or node.get("isEmpty") is True:
        return
    key = str(node.get("key", ""))
    if key in HOLDER_NIF_CELLS:
        return
    if tab == "tab3":
        section = TAB3_SECTIONS.get(key, section)
    v = node.get("value")
    if isinstance(v, list):
        for i, child in enumerate(v):
            _fields(child, tab, f"{path}.{i}" if path else str(i), section, out)
        return
    if isinstance(v, dict):
        raise ShapeError(f"object value in {tab} at {path}")
    v = clean(v)
    if v is None:
        return
    m = COLUMN.search(key)
    out.append({"path": path, "section": section, "column": m.group(1) if m else None, "value": v})


def _attachments(items) -> list:
    """Attachment metadata only: the public API serves no file to check for a NIF."""
    if not isinstance(items, list):
        return []
    return [{k: clean(a.get(k)) for k in ATTACHMENT_KEYS} for a in items if isinstance(a, dict)]


def strip(data: dict) -> dict:
    """Keep the metadata allow-list, tabs 2 to 4 and the attachment metadata.

    Everything else, including nif, is dropped.
    """
    out = {k: clean(data.get(k)) for k in META_KEYS}
    out["id"] = data["id"]
    tabs = (data.get("data") or {}).get("value") or []
    for name, guid in FIELD_TABS.items():
        out[name] = []
        for t in tabs:
            if t.get("key") == guid:
                _fields(t, name, "", None, out[name])
    out["attachments"] = _attachments(data.get("attachments"))
    out["tab4"] = None
    out["associations"] = []
    tabs = [t for t in tabs if t.get("key") == TAB4]
    if tabs:
        groups = tabs[0].get("value") or []
        for g in groups:
            if g.get("key") != TAB4_GROUP:
                raise ShapeError(f"unknown tab 4 group {g.get('key')}")
        sections = (groups[0].get("value") or []) if groups else []
        out["tab4"] = _tab4(sections)
        out["associations"] = _associations(sections)
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


# Keys every stored declaration has. A file without one was stored by an older strip.
STORED_KEYS = ("tab2", "tab3", "tab4", "attachments", "associations")


def is_current(path: Path) -> bool:
    if not path.exists():
        return False
    stored = json.loads(path.read_text())
    return all(k in stored for k in STORED_KEYS)


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
                or not is_current(decl_path(root, e, row["id"]))
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
