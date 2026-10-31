"""EpT fetcher (#44, #148): metadata, tabs 2 to 4 and attachment metadata, stripped in memory.

Every input here is synthetic. The holder NIF and the entity NIF/NIPC values are planted
at runtime, never stored in a fixture, so the fixture scan below stays clean.
"""

import copy
import json
from pathlib import Path

import pytest

from parlamento_aberto import ept

FIX = Path(__file__).parent / "fixtures" / "ept"
RAW = json.loads((FIX / "getdeclaration.json").read_text())
# Built at runtime so no fixture or source line holds a 9-digit literal. Every number
# here is synthetic: a repeated digit pattern, with the check digit computed.
PLANTED = "".join(str(d) for d in (1, 2, 3, 4, 5, 6, 7, 8, 9))
ACT = "2c6d9562-dea5-488b-9afe-42519c636daf"
SUP = "62fb0107-a68d-4ba2-822b-bc8adc54369b"
SER = "b1f8c095-fe0c-4bb3-b493-902dc0c31232"
SOC = "9b58c917-b14c-4eed-9b3c-40c3d99d45da"
ASSOC = "cd0e811a-d9bb-49ee-b0f0-1dae0680eb22"


def with_check(base8: str) -> str:
    total = sum(int(d) * w for d, w in zip(base8, range(9, 1, -1), strict=True))
    r = total % 11
    return base8 + str(0 if r < 2 else 11 - r)


def bad_check(base8: str) -> str:
    good = with_check(base8)
    return good[:8] + str((int(good[8]) + 1) % 10)


VALID = {p: with_check(p + "0" * (8 - len(p))) for p in ("5", "6", "71", "72", "79")}
# 8 (old sole-trader range), 9x (condominiums, irregular companies, sole traders' estates)
# and 77 can identify a person: never kept.
WIDER = {p: with_check(p + "1" * (8 - len(p))) for p in ("8", "90", "91", "98", "77")}
PERSONAL = {p: with_check(p + "0" * (8 - len(p))) for p in ("1", "2", "3", "4")}
OTHER_7X = {p: with_check(p + "0" * 6) for p in ("70", "73", "74", "75", "76", "77", "78")}
WRONG_CHECK = bad_check("5" + "1" * 7)


def raw_with_leaks():
    raw = copy.deepcopy(RAW)
    raw["data"]["nif"] = PLANTED
    for tab in raw["data"]["data"]["value"]:
        if tab["key"] == ept.TAB4:
            for sec in tab["value"][0]["value"]:
                if sec["key"] not in ept.SECTIONS:
                    continue
                for row in sec["value"]:
                    for cell in row["value"]:
                        col = cell["key"].rsplit("-", 1)[-1]
                        if col == ept.SECTIONS[sec["key"]][1]:
                            cell["value"] = PERSONAL["1"]
                        if sec["key"] == ACT and col == "col1" and row["key"].endswith("_0"):
                            cell["value"] = f"Cargo sintético, contribuinte {PLANTED}"
    return raw


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


# Leak guard


@pytest.mark.parametrize(
    "bad",
    [
        {"nif": "x"},
        {"a": [{"b": {"NIF": None}}]},
        {"entityNipc": "x"},
        {"a": PLANTED},
        {"a": int(PLANTED)},
        {"a": f"PT{PLANTED}"},
        {"a": f"tel {PLANTED[:3]} {PLANTED[3:6]} {PLANTED[6:]}"},
        {"a": [f"x{PLANTED}y"]},
        {PLANTED: "x"},
    ],
)
def test_leak_guard_fails_on_planted_values(bad):
    with pytest.raises(ept.LeakError):
        ept.assert_clean(bad)


def test_leak_guard_message_does_not_echo_the_value():
    with pytest.raises(ept.LeakError) as e:
        ept.assert_clean({"a": {"b": PLANTED}})
    assert PLANTED not in str(e.value)
    assert "a.b" in str(e.value)


def test_leak_guard_passes_dates_ids_and_short_numbers():
    ept.assert_clean(
        {
            "id": 12718,
            "startDate": "2025-06-03T13:42:00",
            "submitedDate": "2026-01-30T12:19:04.5",
            "share": "12345678",
            "big": "1234567890",
            "key": ept.TAB4,
        }
    )


def test_the_raw_response_fails_the_guard():
    with pytest.raises(ept.LeakError):
        ept.assert_clean(raw_with_leaks())


# Strip


def test_strip_keeps_metadata_tabs_and_attachment_metadata():
    out = ept.strip(raw_with_leaks()["data"])
    ept.assert_clean(out)
    text = dumps(out)
    assert PLANTED not in text
    assert "nif" not in text.lower()
    assert "sintético, contribuinte [removido]" in text
    for gone in ("oppositionKeys", "alreadyPublished", "internalStateTypeId"):
        assert gone not in text
    assert set(out) == set(ept.META_KEYS) | set(ept.STORED_KEYS)
    assert out["id"] == 902 and out["holderId"] == 7001 and out["relatedDeclarationId"] == 901
    assert list(out["tab4"]) == list(ept.SECTIONS)
    acts = out["tab4"][ACT]
    assert len(acts) == 2
    assert set(acts[0]) == {"col1", "col2", "col3", "col4", "col5", "col6", "col7"}
    assert acts[1]["col7"] is None
    assert ASSOC not in out["tab4"]


def test_strip_drops_personal_range_values_from_the_nipc_column():
    out = ept.strip(raw_with_leaks()["data"])
    assert PERSONAL["1"] not in dumps(out)
    for guid, (_, nif_col, _) in ept.SECTIONS.items():
        for row in out["tab4"][guid]:
            assert nif_col not in row


def nipc_raw(values):
    """The fixture with the NIPC column of each filled row set from ``values`` in turn."""
    raw = copy.deepcopy(RAW)["data"]
    it = iter(values)
    tab4 = next(t for t in raw["data"]["value"] if t["key"] == ept.TAB4)
    cells = []
    for sec in tab4["value"][0]["value"]:
        if sec["key"] not in ept.SECTIONS:
            continue
        nif_col = ept.SECTIONS[sec["key"]][1]
        for row in sec["value"]:
            if row["isEmpty"]:
                continue
            for cell in row["value"]:
                if cell["key"].endswith(f"-{nif_col}"):
                    cell["value"] = next(it)
                    cells.append((sec["key"], int(row["key"].rsplit("_", 1)[1])))
    return raw, cells


@pytest.mark.parametrize("prefix", sorted(VALID))
def test_strip_keeps_a_valid_company_nipc(prefix):
    raw, cells = nipc_raw([VALID[prefix], f" PT {VALID[prefix]} ", VALID[prefix], VALID[prefix]])
    out = ept.strip(raw)
    ept.assert_clean(out)
    for guid, i in cells:
        assert out["tab4"][guid][i][ept.SECTIONS[guid][1]] == VALID[prefix]


@pytest.mark.parametrize(
    "value",
    [
        *PERSONAL.values(),
        *OTHER_7X.values(),
        *WIDER.values(),
        WRONG_CHECK,
        "NIPC sintético",
        "5" * 8,
        "5" * 10,
    ],
)
def test_strip_drops_anything_else_in_the_nipc_column(value):
    raw, cells = nipc_raw([value] * 4)
    out = ept.strip(raw)
    ept.assert_clean(out)
    assert len(cells) == 4
    for guid, i in cells:
        assert ept.SECTIONS[guid][1] not in out["tab4"][guid][i]


def test_is_company_nipc():
    assert all(ept.is_company_nipc(v) for v in VALID.values())
    assert not any(ept.is_company_nipc(v) for v in PERSONAL.values())
    assert not any(ept.is_company_nipc(v) for v in OTHER_7X.values())
    assert not any(ept.is_company_nipc(v) for v in WIDER.values())
    assert not ept.is_company_nipc(WRONG_CHECK)
    assert not ept.is_company_nipc(int(VALID["5"]))


def stored(guid, col, value):
    return {"id": 1, "tab4": {guid: [{"col1": "x", col: value}]}}


@pytest.mark.parametrize("guid", [ACT, SUP, SER, SOC])
def test_guard_allows_a_valid_nipc_only_in_the_nipc_column(guid):
    nif_col = ept.SECTIONS[guid][1]
    ept.assert_clean(stored(guid, nif_col, VALID["5"]))
    other = "col1" if nif_col != "col1" else "col2"
    with pytest.raises(ept.LeakError):
        ept.assert_clean(stored(guid, other, VALID["5"]))


@pytest.mark.parametrize(
    "value", [*PERSONAL.values(), OTHER_7X["70"], WRONG_CHECK, int(VALID["5"]), f"PT{VALID['5']}"]
)
def test_guard_fails_on_anything_but_a_valid_nipc_in_the_nipc_column(value):
    with pytest.raises(ept.LeakError):
        ept.assert_clean(stored(ACT, "col9", value))


@pytest.mark.parametrize("value", [VALID["5"], PERSONAL["2"]])
def test_guard_fails_on_any_nine_digits_outside_the_nipc_column(value):
    for obj in (
        {"id": 1, "holder": value},
        {"tab4": {"00000000-0000-4000-8000-000000000000": [{"col9": value}]}},
        [{"nested": {"tab4": {ACT: [{"col9": value}]}}}],
        {"a": {"tab4": {ACT: [{"col9": value}]}}},
    ):
        with pytest.raises(ept.LeakError):
            ept.assert_clean(obj)


def test_strip_drops_hidden_cells():
    raw = copy.deepcopy(RAW)["data"]
    tab4 = next(t for t in raw["data"]["value"] if t["key"] == ept.TAB4)
    tab4["value"][0]["value"][0]["value"][0]["value"][1]["isVisible"] = False
    out = ept.strip(raw)
    assert "col2" not in out["tab4"][ACT][0]


def test_strip_fails_on_unknown_section_guid():
    raw = copy.deepcopy(RAW)["data"]
    tab4 = next(t for t in raw["data"]["value"] if t["key"] == ept.TAB4)
    tab4["value"][0]["value"][0]["key"] = "00000000-0000-4000-8000-000000000000"
    with pytest.raises(ept.ShapeError, match="unknown tab 4 section"):
        ept.strip(raw)


def test_strip_fails_on_unknown_tab4_group():
    raw = copy.deepcopy(RAW)["data"]
    tab4 = next(t for t in raw["data"]["value"] if t["key"] == ept.TAB4)
    tab4["value"][0]["key"] = "00000000-0000-4000-8000-000000000000"
    with pytest.raises(ept.ShapeError, match="unknown tab 4 group"):
        ept.strip(raw)


def test_strip_without_tab4_keeps_metadata():
    raw = copy.deepcopy(RAW)["data"]
    raw["data"]["value"] = [t for t in raw["data"]["value"] if t["key"] != ept.TAB4]
    out = ept.strip(raw)
    assert out["tab4"] is None and out["id"] == 902


# Fixtures


def test_fixtures_are_clean_and_synthetic():
    files = sorted(FIX.rglob("*.json"))
    assert files
    for f in files:
        text = f.read_text()
        ept.assert_clean(json.loads(text))
        # titularidades.json has no names. A fixture with a holder name uses a made-up one.
        if '"holder"' in text:
            assert "Pessoa Sintética" in text, f.name


# Throttle


class Clock:
    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def time(self):
        return self.now

    def sleep(self, s):
        self.slept.append(s)
        self.now += s


def test_throttle_spaces_requests_one_second_apart():
    c = Clock()
    t = ept.Throttle(clock=c.time, sleep=c.sleep)
    starts = []
    for i in range(5):
        t.wait()
        starts.append(c.now)
        c.now += 0.2 if i % 2 else 1.5
    gaps = [b - a for a, b in zip(starts, starts[1:], strict=False)]
    assert min(gaps) >= 1.0
    assert ept.Throttle().interval == 1.0


class FakeApi:
    """Synthetic EpT: titularidades, search and getdeclaration."""

    def __init__(self, decls, clock=None):
        self.decls = decls  # id -> (entityId, holderId, stateType string, raw data)
        self.calls = []
        self.clock = clock

    def __call__(self, path, body):
        self.calls.append((self.clock.now if self.clock else None, path, dict(body)))
        if path == "/publicquery":
            eid = body["EntityId"]
            seen = {}
            for _, (e, h, _, d) in sorted(self.decls.items()):
                if e == eid:
                    seen.setdefault((h, d["roleId"]), d)
            items = [
                {
                    "id": 100 * e + h,
                    "entityId": e,
                    "roleId": r,
                    "holderId": h,
                    "entity": "Entidade",
                    "role": "Deputada",
                    "holder": f"Pessoa Sintética {h}",
                    "beginDate": None,
                    "endDate": None,
                }
                for (h, r), _ in seen.items()
                for e in [eid]
            ]
            return page(items, body)
        if path == "/publicquery/search":
            items = [
                {
                    "id": i,
                    "natureType": "Initial",
                    "stateType": s,
                    "relatedDeclarationId": d.get("relatedDeclarationId"),
                    "year": 2026,
                    "holder": f"Pessoa Sintética {h}",
                    "entity": "Entidade",
                    "role": "Deputada",
                    "board": "Órgão",
                    "creationDate": "2026-01-30T12:19:04.5",
                    "deliveryDate": "2026-01-30T12:19:04.5",
                    "startDate": "2025-06-03T13:42:00",
                    "endDate": None,
                    "canReplace": False,
                }
                for i, (e, h, s, d) in sorted(self.decls.items())
                if e in body["EntityId"] and h == body["HolderId"]
            ]
            return page(items, body)
        if path == "/publicquery/getdeclaration":
            e, h, s, d = self.decls[body["Id"]]
            return {"code": 0, "data": copy.deepcopy(d)}
        raise AssertionError(path)


def page(items, body):
    size = body.get("pageSize", 20)
    n = body["pageNumber"]
    chunk = items[(n - 1) * size : n * size]
    pages = max(1, -(-len(items) // size))
    return {
        "code": 0,
        "data": {
            "items": chunk,
            "pageNumber": n,
            "pageSize": size,
            "pageCount": pages,
            "total": len(items),
        },
    }


def decl(i, entity, holder, related=None, state=8):
    d = copy.deepcopy(raw_with_leaks()["data"])
    d.update(id=i, entityId=entity, holderId=holder, relatedDeclarationId=related, stateType=state)
    d["holder"] = f"Pessoa Sintética {holder}"
    return d


def api_fixture(clock=None):
    return FakeApi(
        {
            10: (510, 1, "Replaced", decl(10, 510, 1, state=64)),
            11: (510, 1, "Published", decl(11, 510, 1, related=10)),
            20: (510, 2, "Published", decl(20, 510, 2)),
            30: (4508, 1, "Published", decl(30, 4508, 1)),
            40: (4508, 3, "Published", decl(40, 4508, 3)),
        },
        clock,
    )


def written_text(root: Path) -> str:
    return "\n".join(p.read_text() for p in sorted(root.rglob("*")) if p.is_file())


def test_client_sends_every_request_through_the_throttle():
    c = Clock()
    api = api_fixture(c)
    client = ept.Client(post=api, throttle=ept.Throttle(clock=c.time, sleep=c.sleep))
    client.titularidades(510)
    client.declarations(510, 1)
    client.declaration(11)
    times = [t for t, _, _ in api.calls]
    assert len(times) == 3
    assert all(b - a >= 1.0 for a, b in zip(times, times[1:], strict=False))


def test_run_writes_stripped_layout_and_keeps_replaced_versions(tmp_path):
    api = api_fixture()
    logs = []
    report = ept.run(ept.Client(post=api, throttle=None), tmp_path, log=logs.append)
    root = tmp_path / ept.DATASET
    assert report["titularidades"] == 4
    assert report["declarations"] == 5
    assert report["fetched"] == 5
    for i, e in [(10, 510), (11, 510), (20, 510), (30, 4508), (40, 4508)]:
        assert (root / str(e) / "0" / f"{i}.json").exists()
    rec = json.loads((root / "510" / "0" / "11.json").read_text())
    assert rec["relatedDeclarationId"] == 10 and rec["tab4"][ACT]
    idx = [json.loads(line) for line in (root / "declarations.ndjson").read_text().splitlines()]
    assert [r["id"] for r in idx] == [10, 11, 20, 30, 40]
    assert idx[0]["stateType"] == "Replaced" and idx[0]["entityId"] == 510
    assert "holder" not in idx[0]
    tits = (root / "titularidades.ndjson").read_text().splitlines()
    assert len(tits) == 4
    text = written_text(tmp_path)
    assert PLANTED not in text and '"nif"' not in text.lower()
    for p in root.rglob("*.json"):
        ept.assert_clean(json.loads(p.read_text()))
    log = "\n".join(logs)
    assert "Pessoa" not in log and PLANTED not in log


def test_run_is_incremental_by_id_and_state(tmp_path):
    api = api_fixture()
    ept.run(ept.Client(post=api, throttle=None), tmp_path, log=lambda _: None)
    api.calls.clear()
    report = ept.run(ept.Client(post=api, throttle=None), tmp_path, log=lambda _: None)
    assert report["fetched"] == 0
    assert not [c for c in api.calls if c[1] == "/publicquery/getdeclaration"]

    e, h, _, d = api.decls[11]
    api.decls[11] = (e, h, "Replaced", {**d, "stateType": 64})
    api.decls[12] = (e, h, "Published", decl(12, 510, 1, related=11))
    api.calls.clear()
    report = ept.run(ept.Client(post=api, throttle=None), tmp_path, log=lambda _: None)
    got = sorted(c[2]["Id"] for c in api.calls if c[1] == "/publicquery/getdeclaration")
    assert got == [11, 12]
    assert report["fetched"] == 2
    root = tmp_path / ept.DATASET
    assert json.loads((root / "510" / "0" / "11.json").read_text())["stateType"] == 64
    assert (root / "510" / "0" / "10.json").exists()


def test_run_refuses_to_write_a_leak(tmp_path, monkeypatch):
    monkeypatch.setattr(ept, "strip", lambda d: {"id": d["id"], "nif": d["nif"]})
    with pytest.raises(ept.LeakError):
        ept.run(ept.Client(post=api_fixture(), throttle=None), tmp_path, log=lambda _: None)
    assert PLANTED not in written_text(tmp_path)


def test_dry_run_counts_without_fetching_or_writing(tmp_path):
    api = api_fixture()
    logs = []
    report = ept.run(ept.Client(post=api, throttle=None), tmp_path, dry_run=True, log=logs.append)
    assert report["titularidades"] == 4
    assert report["by_entity"] == {"510": 2, "4508": 2}
    assert report["declarations"] == 5
    assert report["states"] == {"Published": 4, "Replaced": 1}
    assert report["fetched"] == 0
    assert not [c for c in api.calls if c[1] == "/publicquery/getdeclaration"]
    assert not any(tmp_path.iterdir())
    assert "Pessoa" not in "\n".join(logs)


def test_search_is_paged(tmp_path):
    api = api_fixture()
    client = ept.Client(post=api, throttle=None, page_size=1)
    assert [d["id"] for d in client.declarations(510, 1)] == [10, 11]
    assert len(client.titularidades(510)) == 2


@pytest.mark.parametrize("value", [*WIDER.values(), *PERSONAL.values()])
def test_guard_fails_on_a_sole_trader_condominium_or_77_number_in_the_nipc_column(value):
    with pytest.raises(ept.LeakError) as e:
        ept.assert_clean(stored(ACT, ept.SECTIONS[ACT][1], value))
    assert value not in str(e.value)


def test_nipc_prefixes_match_privacy():
    from parlamento_aberto import privacy

    for d in range(100):
        prefix = f"{d:02d}"
        assert bool(ept.NIPC_PREFIX.match(prefix)) == prefix.startswith(privacy.COMPANY_PREFIXES)


# Associations (#148): their own key, so they can be dropped on their own


def raw_with_association():
    """The fixture with every association cell visible and filled with synthetic text."""
    raw = copy.deepcopy(RAW)
    tab4 = next(t for t in raw["data"]["data"]["value"] if t["key"] == ept.TAB4)
    sec = next(s for s in tab4["value"][0]["value"] if s["key"] == ASSOC)
    for row in sec["value"]:
        row["isEmpty"] = False
        for cell in row["value"]:
            cell["isVisible"] = True
            col = cell["key"].rsplit("-", 1)[-1]
            cell["value"] = VALID["5"] if col == "col8" else f"Associação sintética {col} {PLANTED}"
    return raw


def test_strip_keeps_associations_apart_from_tab4():
    out = ept.strip(raw_with_association()["data"])
    ept.assert_clean(out)
    assert ASSOC not in out["tab4"]
    assert ASSOC not in dumps(out)
    assert out["associations"]
    row = out["associations"][0]
    assert row["col8"] == VALID["5"]
    assert row["col1"] == "Associação sintética col1 [removido]"
    assert PLANTED not in dumps(out)
    assert ept.ASSOCIATION_NIPC == "col8"


@pytest.mark.parametrize("value", [PERSONAL["1"], WIDER["8"], WRONG_CHECK, "x"])
def test_strip_drops_anything_but_a_company_nipc_from_the_association_nipc(value):
    raw = raw_with_association()
    tab4 = next(t for t in raw["data"]["data"]["value"] if t["key"] == ept.TAB4)
    sec = next(s for s in tab4["value"][0]["value"] if s["key"] == ASSOC)
    for row in sec["value"]:
        for cell in row["value"]:
            if cell["key"].endswith("-col8"):
                cell["value"] = value
    out = ept.strip(raw["data"])
    assert all("col8" not in r for r in out["associations"])


def test_guard_allows_a_company_nipc_only_in_the_association_nipc_column():
    ept.assert_clean({"id": 1, "associations": [{"col8": VALID["5"]}]})
    with pytest.raises(ept.LeakError):
        ept.assert_clean({"id": 1, "associations": [{"col8": PERSONAL["1"]}]})
    with pytest.raises(ept.LeakError):
        ept.assert_clean({"id": 1, "associations": [{"col1": VALID["5"]}]})


def test_guard_fails_on_an_association_section_inside_tab4():
    with pytest.raises(ept.LeakError):
        ept.assert_clean({"id": 1, "tab4": {ASSOC: []}})


# Tabs 2 and 3 (#148): every cell the EpT shows, by position, without a 9-digit number

# Real EpT keys whose digits read as a 9-digit number. They must never reach a stored file.
GUID_NINE = "7bf6ccdd-f797-4339-8c76-18a248882016"
TAB3_SECTION = "112c6561-4a51-4f79-b637-bbd8d2c0c74c"


def cell(key, value, visible=True, **extra):
    return {"key": key, "value": value, "isVisible": visible, **extra}


def raw_with_tabs():
    raw = copy.deepcopy(RAW)["data"]
    tabs = {t["key"]: t for t in raw["data"]["value"]}
    tabs[ept.TAB2]["value"] = [
        cell(
            "56786e7c-a8bb-43aa-9250-eaf8fa82002f",
            [
                cell("c0a2f813-fb84-4923-b7a1-55cef0c5fc1b", "Pessoa Sintética"),
                cell("97ac10fd-3e8e-4fa8-a7f2-991bb3d13a0e", None, visible=False, reason=1),
                cell("d155af2b-21e9-475f-be81-8e42bc5a5641", "Morada oculta", visible=False),
                cell("a5bf96eb-8af0-4c05-bb76-a15f57f8490d", f"contribuinte {PLANTED}"),
                cell(GUID_NINE, 3),
            ],
        )
    ]
    row = f"{TAB3_SECTION}_0"
    empty_row = cell(f"{TAB3_SECTION}_1", [cell(f"{TAB3_SECTION}-col1", "x")], isEmpty=True)
    fund = cell(GUID_NINE, [cell(f"{GUID_NINE}_0", [cell(f"{GUID_NINE}-col2", "Fundo")])])
    deleted = cell("e516635f-aeb6-4e1f-aa9c-d77bf888ec36", [cell("x", "apagado")], isDeleted=True)
    tabs[ept.TAB3]["value"] = [
        cell(
            "45b8a3d2-374f-4531-b167-ac62b950ad6b",
            [
                cell(
                    TAB3_SECTION,
                    [
                        cell(
                            row,
                            [
                                cell(f"{TAB3_SECTION}-col1", "Urbano"),
                                cell(f"{TAB3_SECTION}-col5", 125000.5),
                                cell(f"{TAB3_SECTION}-col6", PERSONAL["2"]),
                                cell(f"{TAB3_SECTION}-col7", VALID["5"]),
                                cell(f"{TAB3_SECTION}-col9", "oculto", visible=False),
                            ],
                            isEmpty=False,
                        ),
                        empty_row,
                    ],
                    isDeleted=False,
                ),
                fund,
                deleted,
            ],
        )
    ]
    return raw


def test_strip_keeps_the_visible_cells_of_tabs_2_and_3():
    out = ept.strip(raw_with_tabs())
    ept.assert_clean(out)
    assert out["tab2"] == [
        {
            "path": "0.0",
            "section": None,
            "column": None,
            "label": "Nome Completo",
            "value": "Pessoa Sintética",
        },
        {
            "path": "0.3",
            "section": None,
            "column": None,
            "label": "Naturalidade",
            "value": "contribuinte [removido]",
        },
        {"path": "0.4", "section": None, "column": None, "label": None, "value": 3},
    ]
    sec = "real_estate_portugal"
    assert out["tab3"] == [
        {"path": "0.0.0.0", "section": sec, "column": "col1", "label": None, "value": "Urbano"},
        {"path": "0.0.0.1", "section": sec, "column": "col5", "label": None, "value": 125000.5},
        {"path": "0.0.0.2", "section": sec, "column": "col6", "label": None, "value": "[removido]"},
        {"path": "0.0.0.3", "section": sec, "column": "col7", "label": None, "value": "[removido]"},
        {
            "path": "0.1.0.0",
            "section": "financial_investments_portugal",
            "column": "col2",
            "label": None,
            "value": "Fundo",
        },
    ]


def test_strip_never_stores_a_guid_or_hidden_cell_from_tabs_2_and_3():
    text = dumps(ept.strip(raw_with_tabs()))
    for gone in (GUID_NINE, TAB3_SECTION, "Morada oculta", "oculto", "apagado", PLANTED):
        assert gone not in text
    for gone in (PERSONAL["2"], VALID["5"]):
        assert gone not in text


def test_strip_fails_on_an_object_value_in_tabs_2_and_3():
    raw = raw_with_tabs()
    tab2 = next(t for t in raw["data"]["value"] if t["key"] == ept.TAB2)
    tab2["value"][0]["value"][0]["value"] = {"a": "b"}
    with pytest.raises(ept.ShapeError, match="tab2"):
        ept.strip(raw)


def test_hidden_tab_keeps_nothing():
    raw = raw_with_tabs()
    for t in raw["data"]["value"]:
        if t["key"] in (ept.TAB2, ept.TAB3):
            t["isVisible"] = False
    out = ept.strip(raw)
    assert out["tab2"] == [] and out["tab3"] == []


def test_field_labels_are_the_form_labels_and_never_hold_nine_digits():
    assert ept.FIELD_LABELS["c0a2f813-fb84-4923-b7a1-55cef0c5fc1b"] == "Nome Completo"
    assert len(ept.FIELD_LABELS) == 63
    for key, label in ept.FIELD_LABELS.items():
        assert not ept.NINE.search(label), key


def test_table_section_names_never_hold_nine_digits():
    for name in ept.TAB3_SECTIONS.values():
        assert not ept.NINE.search(name)


# Attachments (#148): the EpT API serves no file, so only the metadata is kept


def test_strip_keeps_attachment_metadata_only():
    raw = copy.deepcopy(RAW)["data"]
    raw["attachments"] = [
        {
            "name": f"anexo {PLANTED}.pdf",
            "size": 2048,
            "format": "pdf",
            "sectionType": 3,
            "observations": f"NIF {PLANTED}",
            "content": "ZmFrZQ==",
            "url": "https://example.invalid/f",
            "holderNif": PLANTED,
        },
        "not an object",
    ]
    out = ept.strip(raw)
    ept.assert_clean(out)
    assert out["attachments"] == [
        {
            "name": "anexo [removido].pdf",
            "size": 2048,
            "format": "pdf",
            "sectionType": 3,
            "observations": "NIF [removido]",
        }
    ]
    assert set(ept.ATTACHMENT_KEYS) == {"name", "size", "format", "sectionType", "observations"}


def test_strip_without_attachments_keeps_an_empty_list():
    raw = copy.deepcopy(RAW)["data"]
    raw.pop("attachments")
    assert ept.strip(raw)["attachments"] == []


def test_run_refetches_a_file_stored_before_tabs_2_and_3(tmp_path):
    api = api_fixture()
    ept.run(ept.Client(post=api, throttle=None), tmp_path, log=lambda _: None)
    path = tmp_path / ept.DATASET / "510" / "0" / "11.json"
    old = json.loads(path.read_text())
    for key in ("tab2", "tab3", "attachments", "associations"):
        old.pop(key)
    path.write_text(json.dumps(old))
    api.calls.clear()
    report = ept.run(ept.Client(post=api, throttle=None), tmp_path, log=lambda _: None)
    got = [c[2]["Id"] for c in api.calls if c[1] == "/publicquery/getdeclaration"]
    assert got == [11]
    assert report["fetched"] == 1
    assert "tab2" in json.loads(path.read_text())


def test_strip_drops_the_holder_nif_cell_of_tab_2_even_when_shown():
    raw = raw_with_tabs()
    tab2 = next(t for t in raw["data"]["value"] if t["key"] == ept.TAB2)
    nif_cell = tab2["value"][0]["value"][2]
    assert nif_cell["key"] in ept.HOLDER_NIF_CELLS
    nif_cell.update(isVisible=True, value=f"PT {PLANTED}")
    paths = [r["path"] for r in ept.strip(raw)["tab2"]]
    assert "0.2" not in paths
