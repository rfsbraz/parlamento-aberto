"""merge: upsert (#133): a partial AR file adds and updates records by id and never
deletes the ones it leaves out. Only a --prune run deletes."""

import datetime as dt
import json
from pathlib import Path

import pytest

from parlamento_aberto import datapr, sources, sync
from parlamento_aberto.fetch import Response

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"
URL = "https://ar.test/intervencoes-XVII"
INI = "https://ar.test/iniciativas-XVII"

SOURCES = f"""
datasets:
  intervencoes:
    layout: tables
    merge: upsert
    ids:
      records: Id
    files:
      - {{legislature: XVII, url: "{URL}"}}
  iniciativas:
    layout: records
    id: IniId
    merge: upsert
    files:
      - {{legislature: XVII, url: "{INI}"}}
"""


def ok(data) -> Response:
    return Response(200, "application/json", json.dumps(data, ensure_ascii=False).encode())


def interv(ids, text="r"):
    return [
        {"Id": str(i), "DataReuniaoPlenaria": "2026-01-01", "Resumo": f"{text}{i}"} for i in ids
    ]


def ini(ids, title="t"):
    return [{"IniId": i, "IniTitulo": f"{title}{i}"} for i in ids]


NULL_ROW = {"Id": None, "DataReuniaoPlenaria": None, "Resumo": None}


@pytest.fixture
def srcs(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text(SOURCES)
    return sources.load(p)


def run(src, data_dir, routes, **kw):
    get = lambda url: routes[url]  # noqa: E731
    return sync.run(src, data_dir, get=get, today="2026-10-27", fetch_kwargs={"attempts": 1}, **kw)


def lines(data_dir, key="intervencoes/XVII"):
    path = data_dir / key / "records.ndjson"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


# Behaviour on small files


def test_partial_file_updates_and_adds_by_id_and_keeps_the_rest(srcs, tmp_path):
    src = sources.select(srcs, dataset="intervencoes")
    run(src, tmp_path, {URL: ok(interv(range(1, 101)))})
    (r,) = run(src, tmp_path, {URL: ok(interv([5], "new") + interv([200, 201]))})

    rows = {row["Id"]: row for row in lines(tmp_path)}
    assert len(rows) == 102
    assert rows["5"]["Resumo"] == "new5" and rows["6"]["Resumo"] == "r6"
    assert r["status"] == "updated" and r["records"] == 102
    assert r["missing_from_source"] == 99
    assert r["flags"] == []
    entry = sync.read_lock(tmp_path)["intervencoes/XVII"]
    assert (entry["records"], entry["source_records"]) == (102, 3)


def test_null_id_rows_are_dropped(srcs, tmp_path):
    src = sources.select(srcs, dataset="intervencoes")
    (r,) = run(src, tmp_path, {URL: ok(interv([1, 2]) + [NULL_ROW, NULL_ROW])})
    assert [row["Id"] for row in lines(tmp_path)] == ["1", "2"]
    assert r["records"] == 2 and r["null_ids_dropped"] == 2
    assert sync.read_lock(tmp_path)["intervencoes/XVII"]["source_records"] == 4


def test_null_id_rows_already_stored_are_dropped_on_the_next_merge(srcs, tmp_path):
    src = sources.select(srcs, dataset="intervencoes")
    root = tmp_path / "intervencoes/XVII"
    root.mkdir(parents=True)
    stored = interv([1, 2]) + [NULL_ROW]
    (root / "records.ndjson").write_text("".join(json.dumps(r) + "\n" for r in stored))
    run(src, tmp_path, {URL: ok(interv([3]))})
    assert [row["Id"] for row in lines(tmp_path)] == ["1", "2", "3"]


def test_records_layout_keeps_files_ar_left_out(srcs, tmp_path):
    src = sources.select(srcs, dataset="iniciativas")
    run(src, tmp_path, {INI: ok(ini(range(377000, 377100)))})
    (r,) = run(src, tmp_path, {INI: ok(ini([377001], "new"))})
    files = tree(tmp_path / "iniciativas/XVII")
    assert len(files) == 100
    assert json.loads(files["377/377001.json"])["IniTitulo"] == "new377001"
    assert (r["records"], r["missing_from_source"], r["removed"]) == (100, 99, 0)


def test_same_file_twice_gives_the_same_tree(srcs, tmp_path):
    src = sources.select(srcs, dataset="intervencoes")
    run(src, tmp_path, {URL: ok(interv(range(1, 50)))})
    partial = {URL: ok(interv([3], "new") + interv([60]) + [NULL_ROW])}
    run(src, tmp_path, partial)
    before = tree(tmp_path / "intervencoes")
    lock = sync.read_lock(tmp_path)
    # Forget the hash so the second run merges again instead of skipping.
    lock["intervencoes/XVII"]["sha256"] = None
    sync.write_lock(tmp_path, lock)
    (r,) = run(src, tmp_path, partial)
    assert tree(tmp_path / "intervencoes") == before
    assert (r["added"], r["removed"], r["changed"], r["records"]) == (0, 0, 0, 50)


def test_prune_replaces_with_the_ar_file_and_flags_the_drop(srcs, tmp_path):
    src = sources.select(srcs, dataset="intervencoes")
    run(src, tmp_path, {URL: ok(interv(range(1, 101)))})
    (r,) = run(src, tmp_path, {URL: ok(interv([1, 2]) + [NULL_ROW])}, prune=True)
    assert [row["Id"] for row in lines(tmp_path)] == ["1", "2"]
    assert r["removed"] == 98 and r["flags"] == ["row drop 100 to 2"]
    assert sync.read_lock(tmp_path)["intervencoes/XVII"]["records"] == 2


def test_sources_without_merge_still_replace(tmp_path):
    (src,) = sources.select(sources.load(FIX / "sources.yaml"), dataset="iniciativas")
    assert src.merge == "replace"
    run([src], tmp_path, {src.url: ok(ini(range(377000, 377020)))})
    run([src], tmp_path, {src.url: ok(ini(range(377000, 377019)))})
    assert len(tree(tmp_path / "iniciativas/XVII")) == 19


def test_unknown_merge_value_is_refused(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text(SOURCES.replace("merge: upsert", "merge: append", 1))
    with pytest.raises(ValueError, match="merge"):
        sources.load(p)


def test_only_intervencoes_and_iniciativas_upsert_in_sources_yaml():
    upsert = {s.dataset for s in sources.load(ROOT / "sources.yaml") if s.merge == "upsert"}
    assert upsert == {"intervencoes", "iniciativas"}


def test_cli_prune_reaches_the_sync(tmp_path):
    from parlamento_aberto.__main__ import main

    (tmp_path / "sources.yaml").write_text(SOURCES)
    raw = tmp_path / "raw/intervencoes"
    raw.mkdir(parents=True)
    args = ["fetch", "--dataset", "intervencoes", "--offline", "--raw-dir", str(tmp_path / "raw")]
    args += ["--sources", str(tmp_path / "sources.yaml"), "--data", str(tmp_path / "data")]
    (raw / "XVII.json").write_text(json.dumps(interv([1, 2, 3])))
    assert main(args) == 0
    (raw / "XVII.json").write_text(json.dumps(interv([1])))
    assert main(args) == 0
    assert len(lines(tmp_path / "data")) == 3
    (raw / "XVII.json").write_text(json.dumps(interv([2])))
    assert main([*args, "--prune"]) == 0
    assert [row["Id"] for row in lines(tmp_path / "data")] == ["2"]


# The real files, trimmed to the ids, dates and lock entries the tests assert on
# (tests/fixtures/history/upsert.json, from scripts/upsert_history_fixture.py). The
# 2026-10-27 file is not on main, so it is its own fixture (tests/fixtures/README.md, item 22).

HISTORY = json.loads((FIX / "history" / "upsert.json").read_text(encoding="utf-8"))
MAIN_7984 = "4ecab717"  # #128, the restored 7,984-record file
NIGHTLY = [  # fetched, commit on main whose data has that night's AR file
    ("2026-10-20", "ef53439a"),
    ("2026-10-21", "ef53439a"),  # 90949cee, the same file
    ("2026-10-22", "4ecab717"),  # 9033f8c4, the same file
    ("2026-10-23", "65a68f9e"),
    ("2026-10-24", "52f9df2b"),  # 10-24 and 10-26 served the same 127 records
    ("2026-10-26", "52f9df2b"),
    ("2026-10-27", None),
]


def ndjson(body: bytes) -> list[dict]:
    return [json.loads(line) for line in body.decode().splitlines()]


def interventions(commit: str) -> list[dict]:
    files = HISTORY["intervencoes/XVII"]["files"]
    return [{"Id": i, "DataReuniaoPlenaria": day} for i, day in files[commit]]


def ar_file(fetched: str, commit: str | None) -> Response:
    if commit is None:
        path = FIX / "history" / f"intervencoes-XVII-{fetched}.ndjson"
        return ok(ndjson(path.read_bytes()))
    return ok(interventions(commit))


@pytest.fixture
def real():
    return {s.dataset: s for s in sources.select(sources.load(ROOT / "sources.yaml"))}


def seed_interventions(data_dir: Path, key: str):
    sync.write_lock(data_dir, {key: HISTORY[key]["lock"]})
    root = data_dir / key
    root.mkdir(parents=True)
    rows = interventions(MAIN_7984)
    (root / "records.ndjson").write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_main_7984_plus_ar_149_gives_8005(real, tmp_path):
    src = real["intervencoes"]
    seed_interventions(tmp_path, src.key)
    before = {r["Id"]: r for r in lines(tmp_path)}
    ar = ar_file("2026-10-27", None)
    ar_rows = {r["Id"]: r for r in json.loads(ar.body)}
    assert (len(before), len(json.loads(ar.body))) == (7938, 149)  # 7,937 ids + one null

    (r,) = run([src], tmp_path, {src.url: ar})
    rows = lines(tmp_path)
    ids = [row["Id"] for row in rows]
    assert len(rows) == 8005 == len(set(ids))
    assert None not in ids
    assert len(set(ar_rows) - set(before)) == 68
    assert {i: rows[ids.index(i)] for i in ar_rows} == ar_rows
    assert rows[ids.index("505212")]["Resumo"] == "Resumo sintético 505212"
    assert min(row["DataReuniaoPlenaria"] for row in rows) == "2025-06-03"
    entry = sync.read_lock(tmp_path)[src.key]
    assert (entry["records"], entry["source_records"]) == (8005, 149)
    assert (r["missing_from_source"], r["null_ids_dropped"]) == (7856, 0)
    assert r["flags"] == []


def test_real_file_twice_is_idempotent(real, tmp_path):
    src = real["intervencoes"]
    seed_interventions(tmp_path, src.key)
    ar = ar_file("2026-10-27", None)
    run([src], tmp_path, {src.url: ar})
    once = tree(tmp_path / src.key)
    lock = sync.read_lock(tmp_path)
    lock[src.key]["sha256"] = None
    sync.write_lock(tmp_path, lock)
    (r,) = run([src], tmp_path, {src.url: ar})
    assert tree(tmp_path / src.key) == once
    assert (r["added"], r["removed"], r["changed"]) == (0, 0, 0)


def test_replaying_the_nightly_files_never_lowers_the_count(real, tmp_path):
    src = real["intervencoes"]
    counts, seen = [], set()
    for fetched, commit in NIGHTLY:
        ar = ar_file(fetched, commit)
        seen |= {r["Id"] for r in json.loads(ar.body) if r["Id"] is not None}
        (r,) = sync.run([src], tmp_path, get=lambda url, ar=ar: ar, today=fetched)
        counts.append(sync.read_lock(tmp_path)[src.key]["records"])
        assert {row["Id"] for row in lines(tmp_path)} == seen, fetched
    assert counts == sorted(counts), counts
    assert counts[-1] >= 8005


def test_iniciativas_10_23_keeps_all_2346(real, tmp_path):
    src = real["iniciativas"]
    history = HISTORY[src.key]
    sync.write_lock(tmp_path, {src.key: history["lock"]})
    for i in history["files"]["9033f8c4"]:
        path = tmp_path / src.key / str(i // 1000) / f"{i}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"IniId": str(i)}))
    before = set(tree(tmp_path / src.key))
    assert len(before) == 2346
    keys = dict.fromkeys(history["lock"]["keys"])
    partial = [{**keys, "IniId": str(i)} for i in history["files"]["65a68f9e"]]
    assert len(partial) == 2164
    (r,) = run([src], tmp_path, {src.url: ok(partial)})
    after = set(tree(tmp_path / src.key))
    assert before <= after
    assert sync.read_lock(tmp_path)[src.key]["records"] == len(after) >= 2346
    assert r["removed"] == 0 and r["flags"] == []


def test_data_pr_body_lists_records_missing_from_the_ar_file():
    reports = [
        {
            "source": "intervencoes/XVII",
            "status": "updated",
            "flags": [],
            "missing_from_source": 7856,
        },
        {"source": "iniciativas/XVII", "status": "updated", "flags": [], "missing_from_source": 0},
    ]
    body = datapr.render_body(
        {}, reports, {}, ["data"], mode="nightly", today=dt.date(2026, 10, 27)
    )
    assert (
        "## Kept, missing from AR's file\n\n"
        "- intervencoes/XVII: 7856 records kept that AR's file left out\n"
    ) in body
    assert "iniciativas/XVII: 0" not in body
    clean = datapr.render_body({}, [], {}, ["data"], mode="nightly", today=dt.date(2026, 10, 27))
    assert "## Kept, missing from AR's file\n\nNone.\n" in clean
