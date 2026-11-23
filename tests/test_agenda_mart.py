"""Agenda mart from data/agenda_parlamentar (#73).

Runs on the committed fixtures. Set PA_DATA_DIR to a full data/ folder to run the
same checks on a real sync; the fixture-only checks skip then.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, time
from pathlib import Path

import pytest

from parlamento_aberto.build import build

FIXTURES = Path(__file__).parent / "fixtures" / "data"
DATA = Path(os.environ.get("PA_DATA_DIR", FIXTURES))
ON_FIXTURES = DATA.resolve() == FIXTURES.resolve()
fixture_only = pytest.mark.skipif(not ON_FIXTURES, reason="fixture content only")

HTML_TAG = re.compile(r"<[^>]+>")
HTML_ENTITY = re.compile(r"&[#a-zA-Z0-9]+;")


def _current_legislature(con) -> str:
    rows = con.sql("select legislature from legislatures where end_date is null").fetchall()
    assert len(rows) == 1
    return rows[0][0]


def _source_rows(legislature: str) -> list[dict]:
    path = DATA / "agenda_parlamentar" / legislature / "records.ndjson"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%d/%m/%Y").date()


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    return datetime.strptime(value, "%H:%M:%S").time()


@pytest.fixture(scope="module")
def con():
    return build(DATA)


def test_only_the_current_legislature_is_in_the_mart(con):
    current = _current_legislature(con)
    legislatures = [row[0] for row in con.sql("select distinct legislature from agenda").fetchall()]
    assert legislatures == [current]
    ids = {row[0] for row in con.sql("select event_id from agenda").fetchall()}
    for legislature in ("XV", "XVI"):
        if legislature == current:
            continue
        leftover = {row["Id"] for row in _source_rows(legislature)}
        assert leftover and leftover.isdisjoint(ids)


def test_row_count_matches_the_lock(con):
    lock = json.loads((DATA / "_meta" / "sources.lock.json").read_text(encoding="utf-8"))
    current = _current_legislature(con)
    expected = lock[f"agenda_parlamentar/{current}"]["records"]
    (actual,) = con.sql("select count(*) from agenda").fetchone()
    assert actual == expected
    staging = dict(
        con.sql(
            "select legislature, count(*) from stg_agenda_parlamentar__events group by 1"
        ).fetchall()
    )
    for key, entry in lock.items():
        dataset, _, legislature = key.partition("/")
        if dataset != "agenda_parlamentar":
            continue
        assert staging[legislature] == entry["records"]


def test_text_has_no_html_tags_or_entities(con):
    rows = con.sql("select event_id, text from agenda").fetchall()
    assert rows
    for event_id, text in rows:
        assert text is not None, event_id
        assert HTML_TAG.search(text) is None, (event_id, text)
        assert HTML_ENTITY.search(text) is None, (event_id, text)


def test_dates_are_read_and_missing_times_are_null(con):
    current = _current_legislature(con)
    mart = {
        row[0]: row[1:]
        for row in con.sql(
            """
            select event_id, start_date, start_time, end_date, end_time, all_day
            from agenda
            """
        ).fetchall()
    }
    source = _source_rows(current)
    assert {row["Id"] for row in source} == set(mart)
    assert source
    for row in source:
        start_date, start_time, end_date, end_time, all_day = mart[row["Id"]]
        assert start_date == _parse_date(row["EventStartDate"])
        assert end_date == _parse_date(row["EventEndDate"])
        assert start_time == _parse_time(row["EventStartTime"])
        assert end_time == _parse_time(row["EventEndTime"])
        assert all_day is bool(row["AllDayEvent"])


@fixture_only
def test_fixture_plain_text_and_columns(con):
    rows = con.sql(
        """
        select event_id, start_date, start_time, end_date, end_time, all_day,
               section, body, group_code, title, subtitle, location, text, link,
               meeting_number
        from agenda
        order by event_id
        """
    ).fetchall()
    assert rows == [
        (
            30001,
            date(2026, 11, 18),
            time(10, 0, 0),
            date(2026, 11, 18),
            time(13, 0, 0),
            False,
            "Plenário",
            "Plenário",
            0,
            "Reunião plenária de teste",
            "Reunião n.º 10",
            "Sala de teste",
            "",
            None,
            "10",
        ),
        (
            30002,
            date(2026, 11, 19),
            None,
            date(2026, 11, 19),
            None,
            False,
            "Grupos Parlamentares / Partidos / DURP / Ninsc",
            None,
            9001,
            "Audiência de teste do grupo sintético",
            None,
            None,
            "10h00 - Entidade Sintética & Associados",
            "https://app.parlamento.pt/fixture/agenda/30002",
            None,
        ),
        (
            30003,
            date(2026, 11, 23),
            None,
            date(2026, 11, 23),
            None,
            True,
            "Resumo da Calendarização",
            None,
            0,
            "Calendário sintético",
            None,
            None,
            "Dia 23\nReunião plenária de teste",
            None,
            None,
        ),
    ]


@fixture_only
def test_fixture_text_is_synthetic(con):
    texts = [row[0] for row in con.sql("select title from agenda").fetchall()]
    assert texts
    assert all("teste" in title.lower() or "sintético" in title.lower() for title in texts)
    urls = [row[0] for row in con.sql("select link from agenda where link is not null").fetchall()]
    assert urls
    assert all(url.startswith("https://app.parlamento.pt/fixture/") for url in urls)
