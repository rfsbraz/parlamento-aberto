"""EpT fetcher (#44): metadata and tab 4 only, stripped in memory, 1 request per second.

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
# Built at runtime so no fixture or source line holds a 9-digit literal.
PLANTED = "".join(str(d) for d in (1, 2, 3, 4, 5, 6, 7, 8, 9))
ACT = "2c6d9562-dea5-488b-9afe-42519c636daf"


def raw_with_leaks():
    raw = copy.deepcopy(RAW)
    raw["data"]["nif"] = PLANTED
    for tab in raw["data"]["data"]["value"]:
        if tab["key"] == ept.TAB4:
            for sec in tab["value"][0]["value"]:
                for row in sec["value"]:
                    for cell in row["value"]:
                        col = cell["key"].rsplit("-", 1)[-1]
                        if col == ept.SECTIONS[sec["key"]][1]:
                            cell["value"] = PLANTED
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


def test_strip_keeps_metadata_and_tab4_only():
    out = ept.strip(raw_with_leaks()["data"])
    ept.assert_clean(out)
    text = dumps(out)
    assert PLANTED not in text
    assert "nif" not in text.lower()
    assert "sintético, contribuinte [removido]" in text
    for gone in ("Morada", "Rendimento", "Imóvel", "anexo", "oppositionKeys", "attachments"):
        assert gone not in text
    assert set(out) == set(ept.META_KEYS) | {"tab4"}
    assert out["id"] == 902 and out["holderId"] == 7001 and out["relatedDeclarationId"] == 901
    assert list(out["tab4"]) == list(ept.SECTIONS)
    acts = out["tab4"][ACT]
    assert len(acts) == 2
    assert set(acts[0]) == {"col1", "col2", "col3", "col4", "col5", "col6", "col7"}
    assert acts[1]["col7"] is None
    assert out["tab4"]["cd0e811a-d9bb-49ee-b0f0-1dae0680eb22"] == []


def test_strip_drops_every_entity_nif_column():
    out = ept.strip(raw_with_leaks()["data"])
    for guid, (_, nif_col, _) in ept.SECTIONS.items():
        for row in out["tab4"][guid]:
            assert nif_col not in row


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
        data = json.loads(f.read_text())
        ept.assert_clean(data)
        assert "Pessoa Sintética" in f.read_text()


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
