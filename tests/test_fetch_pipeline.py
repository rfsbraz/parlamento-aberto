import json
import random
import shutil
from pathlib import Path

import pytest

from parlamento_aberto import sources, sync
from parlamento_aberto.fetch import Response, fetch, is_soft_404
from parlamento_aberto.normalise import LayoutError, normalise

FIX = Path(__file__).parent / "fixtures"
SOFT_404 = (FIX / "soft_404.html").read_bytes()
INI16 = "https://ar.test/iniciativas-XVI"
INI17 = "https://ar.test/iniciativas-XVII"
ATV17 = "https://ar.test/atividades-XVII"


def ini(n, start=377350, **extra):
    return [{"IniId": start + i, "IniTitulo": f"t{i}", "IniTipo": "P", **extra} for i in range(n)]


def ok(data) -> Response:
    return Response(200, "application/json", json.dumps(data).encode())


def html(body: bytes = SOFT_404) -> Response:
    return Response(200, "text/html; charset=utf-8", body)


class Server:
    """Fake AR: each URL maps to a list of responses served in order (last repeats)."""

    def __init__(self, routes):
        self.routes = {u: list(r) if isinstance(r, list) else [r] for u, r in routes.items()}
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        queue = self.routes[url]
        return queue.pop(0) if len(queue) > 1 else queue[0]


@pytest.fixture
def srcs():
    return sources.load(FIX / "sources.yaml")


def run(srcs, data, server, **kw):
    return sync.run(
        srcs, data, get=server, today="2026-10-20", fetch_kwargs={"sleep": lambda s: None}, **kw
    )


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def by_source(reports):
    return {r["source"]: r for r in reports}


# Scope


def test_current_is_newest_legislature_in_sources(srcs):
    assert sources.current_legislature(srcs) == "XVII"
    assert {s.key for s in sources.select(srcs)} == {"iniciativas/XVII", "atividades/XVII"}


def test_newer_legislature_in_sources_becomes_current(tmp_path):
    text = (FIX / "sources.yaml").read_text()
    text = text.replace(
        '      - {legislature: XVII, url: "https://ar.test/iniciativas-XVII"}',
        '      - {legislature: XVII, url: "https://ar.test/iniciativas-XVII"}\n'
        '      - {legislature: XVIII, url: "https://ar.test/iniciativas-XVIII"}',
    )
    (tmp_path / "sources.yaml").write_text(text)
    srcs = sources.load(tmp_path / "sources.yaml")
    assert [s.key for s in sources.select(srcs)] == ["iniciativas/XVIII"]


def test_scope_options(srcs):
    keys = lambda **kw: sorted(s.key for s in sources.select(srcs, **kw))  # noqa: E731
    assert keys(all_legislatures=True) == sorted(s.key for s in srcs)
    assert keys(dataset="iniciativas", all_legislatures=True) == [
        "iniciativas/XVI",
        "iniciativas/XVII",
    ]
    assert keys(legislature="XVI") == ["iniciativas/XVI"]
    assert keys(legislature="I") == ["atividades/I-A"]
    with pytest.raises(ValueError):
        sources.select(srcs, dataset="nope")


def test_single_legislature_run_touches_only_its_files(srcs, tmp_path):
    server = Server({INI16: ok(ini(2, 300000)), INI17: ok(ini(3)), ATV17: ok({"Audicoes": []})})
    run(sources.select(srcs, all_legislatures=True)[:3], tmp_path, server)
    before = tree(tmp_path)
    server.routes[INI16] = [ok(ini(1, 300000))]
    server.routes[INI17] = [ok(ini(9))]
    run(sources.select(srcs, legislature="XVI"), tmp_path, server)
    after = tree(tmp_path)
    changed = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    assert changed == {"iniciativas/XVI/300/300001.json", "_meta/sources.lock.json"}
    lock_before = json.loads(before["_meta/sources.lock.json"])
    lock_after = json.loads(after["_meta/sources.lock.json"])
    assert lock_before["iniciativas/XVII"] == lock_after["iniciativas/XVII"]


# Fetch


def test_real_soft_404_page_is_detected():
    assert len(SOFT_404) == 2389
    assert "Recurso Não Encontrado".encode() in SOFT_404
    assert is_soft_404(html())
    assert is_soft_404(Response(200, "application/json", SOFT_404))
    assert not is_soft_404(ok([]))


def test_soft_404_is_retried_with_backoff_then_succeeds():
    waits = []
    server = Server({INI17: [html(), html(), ok(ini(1))]})
    resp, attempts = fetch(INI17, get=server, sleep=waits.append, backoff=60)
    assert attempts == 3 and resp.status == 200
    assert waits == [60, 120]


def test_persistent_soft_404_keeps_last_good_copy_and_marks_stale(srcs, tmp_path):
    src = sources.select(srcs, dataset="iniciativas")
    run(src, tmp_path, Server({INI17: ok(ini(2))}))
    before = tree(tmp_path / "iniciativas")
    server = Server({INI17: html()})
    (r,) = sync.run(
        src, tmp_path, get=server, today="2026-10-21", fetch_kwargs={"sleep": lambda s: None}
    )
    assert len(server.calls) == 4
    assert r["status"] == "stale" and "soft 404" in r["reason"]
    assert tree(tmp_path / "iniciativas") == before
    lock = sync.read_lock(tmp_path)["iniciativas/XVII"]
    assert lock["stale"] and lock["stale_since"] == "2026-10-21" and lock["records"] == 2


def test_stale_since_keeps_first_day(srcs, tmp_path):
    src = sources.select(srcs, dataset="iniciativas")
    run(src, tmp_path, Server({INI17: ok(ini(2))}))
    for day in ("2026-10-21", "2026-10-22"):
        sync.run(
            src,
            tmp_path,
            get=Server({INI17: html()}),
            today=day,
            fetch_kwargs={"sleep": lambda s: None},
        )
    assert sync.read_lock(tmp_path)["iniciativas/XVII"]["stale_since"] == "2026-10-21"


# Validate


def test_empty_file_rejected_when_last_good_had_records(srcs, tmp_path):
    src = sources.select(srcs, dataset="iniciativas")
    run(src, tmp_path, Server({INI17: ok(ini(2))}))
    before = tree(tmp_path / "iniciativas")
    empty = Response(200, "application/json", (FIX / "empty.json").read_bytes())
    (r,) = run(src, tmp_path, Server({INI17: empty}))
    assert r["status"] == "stale" and "empty" in r["reason"]
    assert tree(tmp_path / "iniciativas") == before


def test_empty_file_accepted_when_never_had_records(srcs, tmp_path):
    src = sources.select(srcs, dataset="iniciativas")
    (r,) = run(src, tmp_path, Server({INI17: ok([])}))
    assert r["status"] == "new" and r["records"] == 0


def test_parse_failure_rejected(srcs, tmp_path):
    src = sources.select(srcs, dataset="iniciativas")
    run(src, tmp_path, Server({INI17: ok(ini(2))}))
    bad = Response(200, "application/json", (FIX / "truncated.json").read_bytes())
    (r,) = run(src, tmp_path, Server({INI17: bad}))
    assert r["status"] == "stale" and "parse" in r["reason"]
    assert len(list((tmp_path / "iniciativas/XVII").rglob("*.json"))) == 2


def test_row_drop_over_5_percent_keeps_the_last_copy(srcs, tmp_path):
    src = sources.select(srcs, dataset="iniciativas")
    run(src, tmp_path, Server({INI17: ok(ini(100))}))
    (r,) = run(src, tmp_path, Server({INI17: ok(ini(94))}))
    assert r["status"] == "stale" and r["reason"] == "row drop 100 to 94"
    assert len(list((tmp_path / "iniciativas/XVII").rglob("*.json"))) == 100
    (r,) = run(src, tmp_path, Server({INI17: ok(ini(96))}))
    assert r["status"] == "updated" and r["flags"] == []  # 4% is under the limit


def test_key_set_change_is_flagged_but_written(srcs, tmp_path):
    src = sources.select(srcs, dataset="iniciativas")
    run(src, tmp_path, Server({INI17: ok(ini(2))}))
    (r,) = run(src, tmp_path, Server({INI17: ok(ini(2, IniNova=1))}))
    assert r["status"] == "updated" and r["changed"] == 2
    assert r["flags"] == ["key set changed (added ['IniNova'], removed [])"]


# Normalise


def test_records_layout_is_one_sorted_pretty_file_per_record():
    files = normalise([{"IniTitulo": "á", "IniId": 377352}], "records", "IniId", {}, 0)
    assert files == {"377/377352.json": '{\n "IniId": 377352,\n "IniTitulo": "á"\n}\n'.encode()}


def test_unstable_source_order_gives_identical_output(srcs, tmp_path):
    src = sources.select(srcs)
    data = {"Audicoes": [{"IDAudicao": i, "b": i, "a": 1} for i in range(1500)], "Extra": {"x": 1}}
    run(src, tmp_path / "a", Server({INI17: ok(ini(50)), ATV17: ok(data)}))
    shuffled = ini(50)
    random.Random(1).shuffle(shuffled)
    random.Random(2).shuffle(data["Audicoes"])
    run(src, tmp_path / "b", Server({INI17: ok(shuffled), ATV17: ok(data)}))
    # The lock differs (it hashes the raw bytes); the data files must not.
    assert tree(tmp_path / "a/iniciativas") == tree(tmp_path / "b/iniciativas")
    assert tree(tmp_path / "a/atividades") == tree(tmp_path / "b/atividades")
    assert sorted(tree(tmp_path / "a/atividades/XVII")) == [
        "Audicoes.0-999.ndjson",
        "Audicoes.1000-1999.ndjson",
        "Extra._meta.ndjson",
    ]
    first = (tmp_path / "a/atividades/XVII/Audicoes.0-999.ndjson").read_text().splitlines()[0]
    assert first == '{"IDAudicao":0,"a":1,"b":0}'


def test_file_over_50_mb_is_refused():
    big = [{"IDAudicao": 1, "t": "x" * 50_000_001}]
    with pytest.raises(LayoutError, match="over the 50 MB limit"):
        normalise({"Audicoes": big}, "tables", None, {"Audicoes": "IDAudicao"}, 1000)


def test_duplicate_record_id_is_refused():
    with pytest.raises(LayoutError, match="duplicate"):
        normalise(ini(1) + ini(1), "records", "IniId", {}, 0)


# Hashing and idempotence


def test_second_run_is_byte_identical_and_skipped_by_hash(srcs, tmp_path, monkeypatch):
    src = sources.select(srcs)
    server = Server({INI17: ok(ini(20)), ATV17: ok({"Audicoes": [{"IDAudicao": 5}]})})
    run(src, tmp_path, server)
    before = tree(tmp_path)

    def boom(*a, **k):
        raise AssertionError("unchanged file was normalised again")

    monkeypatch.setattr(sync, "normalise", boom)
    reports = sync.run(src, tmp_path, get=server, today="2026-10-25")
    assert {r["status"] for r in reports} == {"unchanged"}
    assert tree(tmp_path) == before


def test_removed_records_are_deleted_and_counted(srcs, tmp_path):
    src = sources.select(srcs, dataset="iniciativas")
    run(src, tmp_path, Server({INI17: ok(ini(3, 377999))}))
    (r,) = run(src, tmp_path, Server({INI17: ok(ini(1, 377999))}))
    assert (r["added"], r["removed"], r["changed"]) == (0, 2, 0)
    assert sorted(tree(tmp_path / "iniciativas/XVII")) == ["377/377999.json"]
    assert not (tmp_path / "iniciativas/XVII/378").exists()


def test_lock_records_hash_date_count_keys_and_stale(srcs, tmp_path):
    src = sources.select(srcs, dataset="iniciativas")
    body = ok(ini(2))
    run(src, tmp_path, Server({INI17: body}))
    entry = sync.read_lock(tmp_path)["iniciativas/XVII"]
    import hashlib

    assert entry == {
        "sha256": hashlib.sha256(body.body).hexdigest(),
        "bytes": len(body.body),
        "fetched": "2026-10-20",
        "records": 2,
        "keys": ["IniId", "IniTipo", "IniTitulo"],
        "stale": False,
        "stale_since": None,
        "stale_reason": None,
    }


def test_offline_cli_replays_raw_dir(tmp_path):
    from parlamento_aberto.__main__ import main

    raw = tmp_path / "raw/iniciativas"
    raw.mkdir(parents=True)
    (raw / "XVII.json").write_text(json.dumps(ini(2)))
    shutil.copy(FIX / "sources.yaml", tmp_path / "sources.yaml")
    args = ["fetch", "--dataset", "iniciativas", "--offline", "--raw-dir", str(tmp_path / "raw")]
    args += ["--sources", str(tmp_path / "sources.yaml"), "--data", str(tmp_path / "data")]
    assert main(args) == 0
    assert (tmp_path / "data/iniciativas/XVII/377/377351.json").exists()


def test_id_tables_without_bucket_are_one_file_sorted_by_id_and_names_rename():
    data = {"Deputados": [{"DepId": 10}, {"DepId": 2}], "Circulos": [{"b": 1}, {"a": 1}]}
    files = normalise(
        data, "tables", None, {"Deputados": "DepId"}, None, {"Deputados": "deputados"}
    )
    assert files == {
        "deputados.ndjson": b'{"DepId":2}\n{"DepId":10}\n',
        "Circulos.ndjson": b'{"a":1}\n{"b":1}\n',
    }


def test_nested_and_float_ids():
    data = [{"Deputado": {"DepCadId": 9072.0}}, {"Deputado": {"DepCadId": "162"}}]
    files = normalise(data, "records", "Deputado.DepCadId", {}, None)
    assert sorted(files) == ["0/162.json", "9/9072.json"]
    with pytest.raises(LayoutError, match="not an integer"):
        normalise([{"IniId": 1.5}], "records", "IniId", {}, None)


def test_null_ids_sort_last_or_go_to_their_own_range_file():
    recs = [{"Id": None, "t": "b"}, {"Id": 3}, {"Id": None, "t": "a"}, {"Id": 1}]
    one = normalise(recs, "tables", None, {"records": "Id"}, None)
    assert one["records.ndjson"].decode().splitlines() == [
        '{"Id":1}',
        '{"Id":3}',
        '{"Id":null,"t":"a"}',
        '{"Id":null,"t":"b"}',
    ]
    split = normalise(recs, "tables", None, {"records": "Id"}, 10)
    assert sorted(split) == ["records.0-9.ndjson", "records.no-id.ndjson"]
