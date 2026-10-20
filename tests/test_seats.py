"""Seat counts from seated_on(d) against the seats seed (#27).

The swap-day tests build a tiny mandates table and run on every checkout. The full-data
test needs PA_DATA_DIR (or PARLAMENTO_DATA_DIR) pointing at a full data/ folder and is
skipped otherwise.
"""

import os
from pathlib import Path

import duckdb
import pytest

from parlamento_aberto.build import MODELS, build

_data = os.environ.get("PA_DATA_DIR") or os.environ.get("PARLAMENTO_DATA_DIR")
DATA_DIR = Path(_data) if _data else None
data_only = pytest.mark.skipif(DATA_DIR is None, reason="needs the full data")

# Legislatures whose seat count must never pass the seed, any day.
STRICT = ("VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII")

# Constituinte to VI: the source never closes some stand-in periods, so per-day counts are
# overstated (docs/known-gaps.md, Seat counts). Pinned exactly so any change fails loudly.
# legislature: (max seated on one day, days over the seed or None without a seed row)
PINNED_OVER = {
    "Constituinte": (250, None),
    "I-A": (271, 1178),
    "I-B": (254, 249),
    "II": (257, 891),
    "III": (258, 887),
    "IV": (256, 639),
    "V": (254, 1346),
    "VI": (232, 746),
}

MANDATE_COLUMNS = """
    legislature varchar, cadastro_id integer, deputy_id integer, circle_id integer,
    situation varchar, is_effective boolean, start_date date, end_date date
"""


def _seated(rows, day):
    con = duckdb.connect()
    con.execute(f"create table mandates ({MANDATE_COLUMNS})")
    for r in rows:
        con.execute("insert into mandates values (?, ?, ?, ?, ?, ?, ?, ?)", r)
    con.execute((MODELS / "macros.sql").read_text(encoding="utf-8"))
    sql = "select cadastro_id from seated_on(?::date) order by cadastro_id"
    return [r[0] for r in con.execute(sql, [day]).fetchall()]


def test_swap_day_counts_only_the_incoming_deputy():
    rows = [
        ("L", 1, 11, 7, "Efetivo", True, "2000-01-01", "2000-03-10"),
        ("L", 1, 11, 7, "Suspenso(Eleito)", False, "2000-03-11", None),
        ("L", 2, 12, 7, "Efetivo Temporário", True, "2000-03-10", None),
    ]
    assert _seated(rows, "2000-03-09") == [1]
    assert _seated(rows, "2000-03-10") == [2]
    assert _seated(rows, "2000-03-11") == [2]


def test_period_that_continues_next_day_still_counts():
    rows = [
        ("L", 1, 11, 7, "Efetivo", True, "2000-01-01", "2000-03-10"),
        ("L", 1, 11, 7, "Efetivo Definitivo", True, "2000-03-11", None),
        ("L", 2, 12, 7, "Efetivo Temporário", True, "2000-03-10", None),
    ]
    assert _seated(rows, "2000-03-10") == [1, 2]


def test_open_period_is_not_outgoing():
    rows = [
        ("L", 1, 11, 7, "Efetivo", True, "2000-01-01", None),
        ("L", 2, 12, 7, "Efetivo", True, "2000-01-01", "2000-03-09"),
        ("L", 3, 13, 7, "Efetivo Temporário", True, "2000-03-10", None),
    ]
    assert _seated(rows, "2000-03-10") == [1, 3]


def test_start_in_another_circle_is_not_a_swap():
    rows = [
        ("L", 1, 11, 7, "Efetivo", True, "2000-01-01", "2000-03-10"),
        ("L", 2, 12, 8, "Efetivo Temporário", True, "2000-03-10", None),
    ]
    assert _seated(rows, "2000-03-10") == [1, 2]


def test_one_day_stand_in_hands_back_to_returning_deputy():
    # The returning deputy has an Efetivo and a Suspenso period both on d only.
    rows = [
        ("L", 1, 11, 7, "Suspenso(Eleito)", False, "2000-01-01", "2000-03-09"),
        ("L", 1, 11, 7, "Efetivo", True, "2000-03-10", "2000-03-10"),
        ("L", 1, 11, 7, "Suspenso(Eleito)", False, "2000-03-10", "2000-03-10"),
        ("L", 1, 11, 7, "Efetivo", True, "2000-03-11", None),
        ("L", 2, 12, 7, "Efetivo Temporário", True, "2000-01-01", "2000-03-09"),
        ("L", 2, 12, 7, "Efetivo Temporário", True, "2000-03-10", "2000-03-10"),
    ]
    assert _seated(rows, "2000-03-09") == [2]
    assert _seated(rows, "2000-03-10") == [1]
    assert _seated(rows, "2000-03-11") == [1]


def test_filling_a_vacancy_is_not_a_swap():
    # Circle 7 is one short on d - 1. Deputy 2 fills that seat on d, while deputy 1 hands
    # over to deputy 3 the next day, so the circle never has one too many.
    rows = [
        ("L", 1, 11, 7, "Efetivo", True, "2000-01-01", "2000-03-10"),
        ("L", 1, 11, 7, "Suspenso(Eleito)", False, "2000-03-11", None),
        ("L", 2, 12, 7, "Efetivo Temporário", True, "2000-03-10", None),
        ("L", 3, 13, 7, "Efetivo Temporário", True, "2000-03-11", None),
    ]
    assert _seated(rows, "2000-03-10") == [1, 2]
    assert _seated(rows, "2000-03-11") == [2, 3]


def test_one_day_stand_ins_without_a_handover_count():
    rows = [
        ("L", 1, 11, 7, "Efetivo", True, "2000-01-01", None),
        ("L", 1, 11, 7, "Impedido", False, "2000-03-10", "2000-03-10"),
        ("L", 2, 12, 7, "Efetivo Temporário", True, "2000-03-10", "2000-03-10"),
    ]
    assert _seated(rows, "2000-03-10") == [2]


@pytest.fixture(scope="module")
def full():
    return build(DATA_DIR)


@data_only
def test_seated_never_exceeds_seats_on_full_data(full):
    days = full.sql(
        """
        select l.legislature, s.seats, unnest(generate_series(
            l.start_date, coalesce(l.end_date, l.extract_date), interval 1 day
        ))::date as day
        from legislatures l left join seed_seats s using (legislature)
        order by l.start_date, day
        """
    ).fetchall()
    peak = {}
    days_over = {}
    for legislature, seats, day in days:
        (n,) = full.execute(
            "select count(*) from seated_on(?::date) where legislature = ?", [day, legislature]
        ).fetchone()
        peak[legislature] = max(peak.get(legislature, 0), n)
        if seats is None:
            days_over[legislature] = None
        else:
            days_over[legislature] = days_over.get(legislature, 0) + (n > seats)
    strict = {leg: days_over[leg] for leg in STRICT}
    assert strict == dict.fromkeys(STRICT, 0)
    pinned = {leg: (peak[leg], days_over[leg]) for leg in PINNED_OVER}
    assert pinned == PINNED_OVER
    assert sorted(peak) == sorted(STRICT + tuple(PINNED_OVER))
