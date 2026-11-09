"""initiative_events mart and the phase_codes seed (#72).

Like test_committee_votes, PARLAMENTO_DATA_DIR points the data checks at a full data/ folder.
"""

import os
from pathlib import Path

import pytest

from parlamento_aberto.build import build
from parlamento_aberto.checks import unknown_phase_codes

FIXTURES = Path(__file__).parent / "fixtures" / "data"
DATA_DIR = Path(os.environ.get("PARLAMENTO_DATA_DIR", FIXTURES))
data_only = pytest.mark.skipif(DATA_DIR == FIXTURES, reason="needs the full data")

# Events per legislature. On the fixtures they must not move. On the full data they are the
# 9 November 2026 checkout, and the AR only adds events, so the counts must not drop below them.
FIXTURE_COUNTS = {"I-B": 4, "XIV": 22, "XVI": 14, "XVII": 44}
DATA_COUNTS = {
    "I-A": 4008,
    "I-B": 2016,
    "II": 2953,
    "III": 1785,
    "IV": 5802,
    "V": 13601,
    "VI": 12225,
    "VII": 16943,
    "VIII": 10761,
    "IX": 12338,
    "X": 20696,
    "XI": 12289,
    "XII": 31262,
    "XIII": 32323,
    "XIV": 15628,
    "XV": 18888,
    "XVI": 12874,
    "XVII": 16797,
}
OUTCOMES = {
    "in_progress",
    "approved_published",
    "rejected",
    "lapsed",
    "withdrawn",
    "prejudiced",
    "vetoed",
}


@pytest.fixture(scope="module")
def con():
    return build(DATA_DIR)


def test_events_per_legislature_are_pinned(con):
    counts = dict(
        con.sql("select legislature, count(*) from initiative_events group by 1").fetchall()
    )
    if DATA_DIR == FIXTURES:
        assert counts == FIXTURE_COUNTS
    else:
        assert set(counts) == set(DATA_COUNTS)
        assert {k: v for k, v in counts.items() if v < DATA_COUNTS[k]} == {}


def test_every_event_links_to_an_initiative(con):
    (n,) = con.sql(
        """
        select count(*) from initiative_events e
        where not exists (
            select 1 from initiatives i
            where i.legislature = e.legislature and i.initiative_id = e.initiative_id
        )
        """
    ).fetchone()
    assert n == 0


def test_oev_id_is_unique(con):
    rows, ids = con.sql("select count(*), count(distinct oev_id) from initiative_events").fetchone()
    assert rows == ids


def test_every_event_has_a_date(con):
    (n,) = con.sql("select count(*) from initiative_events where phase_date is null").fetchone()
    assert n == 0


def test_every_phase_code_is_in_the_seed(con):
    assert unknown_phase_codes(con) == []


def test_an_unknown_phase_code_is_reported():
    c = build(FIXTURES)
    c.execute("update initiative_events set phase_code = '9999' where event_order = 1")
    assert [code for code, _ in unknown_phase_codes(c)] == ["9999"]


def test_event_order_follows_date_then_oev_id(con):
    rows = con.sql(
        """
        select legislature, initiative_id, event_order,
            row_number() over (
                partition by legislature, initiative_id order by phase_date, oev_id
            ) as expected
        from initiative_events
        """
    ).fetchall()
    assert [r for r in rows if r[2] != r[3]] == []


def test_seed_has_one_row_per_code_and_known_outcomes(con):
    rows, codes = con.sql(
        "select count(*), count(distinct phase_code) from seed_phase_codes"
    ).fetchone()
    assert rows == codes
    outcomes = {o for (o,) in con.sql("select distinct outcome from seed_phase_codes").fetchall()}
    assert outcomes <= OUTCOMES


def test_final_phases_have_their_outcome(con):
    outcomes = dict(con.sql("select phase_code, outcome from seed_phase_codes").fetchall())
    assert outcomes["580"] == "approved_published"  # Lei (Publicação DR)
    assert outcomes["600"] == "approved_published"  # Resolução da AR (Publicação DR)
    assert outcomes["649"] == "lapsed"  # Iniciativa Caducada
    assert outcomes["648"] == "withdrawn"  # Retirada da iniciativa
    assert outcomes["650"] == "prejudiced"  # Iniciativa Prejudicada
    assert outcomes["250"] == "in_progress"  # Votação na generalidade


@data_only
def test_only_the_two_xvii_events_have_no_phase_code(con):
    rows = con.sql(
        "select legislature, phase from initiative_events where phase_code is null"
    ).fetchall()
    assert rows == [("XVII", "Anúncio de conclusão")] * 2


def test_phase_codes_are_published_with_initiative_events(con):
    from parlamento_aberto.release import marts

    assert {"initiative_events", "phase_codes"} <= set(marts())
    seed = con.sql("select * from seed_phase_codes order by phase_code").fetchall()
    assert con.sql("select * from phase_codes order by phase_code").fetchall() == seed
