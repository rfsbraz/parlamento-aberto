"""A drop of more than 5% keeps the last good copy (#135). Only rolling-window sources,
like the agenda, accept it and flag it."""

import datetime as dt
import json
from pathlib import Path

import pytest

from parlamento_aberto import datapr, sources, sync
from parlamento_aberto.fetch import Response

ROOT = Path(__file__).resolve().parents[1]
URL = "https://ar.test/intervencoes-XVII"
AGENDA = "https://ar.test/agenda-XVII"

SOURCES = f"""
datasets:
  intervencoes:
    layout: tables
    ids:
      records: Id
    files:
      - {{legislature: XVII, url: "{URL}"}}
  agenda_parlamentar:
    layout: tables
    rolling: true
    ids:
      records: Id
    files:
      - {{legislature: XVII, url: "{AGENDA}"}}
"""


def ok(data) -> Response:
    return Response(200, "application/json", json.dumps(data).encode())


def rows(n):
    return [{"Id": str(500000 + i), "Resumo": f"r{i}"} for i in range(n)]


@pytest.fixture
def srcs(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text(SOURCES)
    return sources.load(p)


def run(src, data_dir, routes, today):
    return sync.run(
        src, data_dir, get=lambda url: routes[url], today=today, fetch_kwargs={"attempts": 1}
    )


def tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def lock(data_dir):
    return json.loads((data_dir / sync.LOCK).read_text())


def test_81_over_7984_writes_nothing_and_marks_the_source_stale(srcs, tmp_path):
    src = sources.select(srcs, dataset="intervencoes")
    run(src, tmp_path, {URL: ok(rows(7984))}, "2026-10-22")
    before, entry = tree(tmp_path / "intervencoes/XVII"), lock(tmp_path)["intervencoes/XVII"]

    (r,) = run(src, tmp_path, {URL: ok(rows(81))}, "2026-10-23")

    assert tree(tmp_path / "intervencoes/XVII") == before
    after = lock(tmp_path)["intervencoes/XVII"]
    assert {k: after[k] for k in ("sha256", "records", "fetched")} == {
        k: entry[k] for k in ("sha256", "records", "fetched")
    }
    assert after["stale"] is True
    assert after["stale_since"] == "2026-10-23"
    assert after["stale_reason"] == "row drop 7984 to 81"
    assert r["status"] == "stale" and r["reason"] == "row drop 7984 to 81"
    body = datapr.render_body(
        {}, [r], lock(tmp_path), ["data"], mode="nightly", today=dt.date(2026, 10, 27)
    )
    assert "- intervencoes/XVII: stale for 4 days since 2026-10-23 (row drop 7984 to 81)" in body


def test_the_short_file_stays_stale_and_a_full_one_clears_it(srcs, tmp_path):
    src = sources.select(srcs, dataset="intervencoes")
    run(src, tmp_path, {URL: ok(rows(7984))}, "2026-10-22")
    run(src, tmp_path, {URL: ok(rows(81))}, "2026-10-23")
    (r,) = run(src, tmp_path, {URL: ok(rows(81))}, "2026-10-24")
    assert r["status"] == "stale"
    assert lock(tmp_path)["intervencoes/XVII"]["stale_since"] == "2026-10-23"
    (r,) = run(src, tmp_path, {URL: ok(rows(7990))}, "2026-10-25")
    assert r["status"] == "updated" and r["records"] == 7990
    assert lock(tmp_path)["intervencoes/XVII"]["stale"] is False


def test_a_drop_under_5_percent_is_written(srcs, tmp_path):
    src = sources.select(srcs, dataset="intervencoes")
    run(src, tmp_path, {URL: ok(rows(100))}, "2026-10-22")
    (r,) = run(src, tmp_path, {URL: ok(rows(96))}, "2026-10-23")
    assert r["status"] == "updated" and r["removed"] == 4 and r["flags"] == []


def test_a_rolling_source_writes_the_drop_and_flags_it(srcs, tmp_path):
    src = sources.select(srcs, dataset="agenda_parlamentar")
    run(src, tmp_path, {AGENDA: ok(rows(75))}, "2026-10-22")
    (r,) = run(src, tmp_path, {AGENDA: ok(rows(20))}, "2026-10-23")
    assert r["status"] == "updated" and r["records"] == 20
    assert r["flags"] == ["row drop 75 to 20"]
    assert lock(tmp_path)["agenda_parlamentar/XVII"]["stale"] is False


def test_only_the_agenda_is_rolling_in_sources_yaml():
    rolling = {s.dataset for s in sources.load(ROOT / "sources.yaml") if s.rolling}
    assert rolling == {"agenda_parlamentar"}
