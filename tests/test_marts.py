from pathlib import Path

import pytest

from parlamento_aberto.build import build, load_schema

FIXTURES = Path(__file__).parent / "fixtures" / "data"


@pytest.fixture(scope="module")
def con():
    return build(FIXTURES)


def test_every_seeded_legislature_has_a_source(con):
    missing = con.sql(
        """
        select l.legislature from legislatures l
        left join seed_seats s using (legislature)
        where s.seats is null or coalesce(s.source, '') = ''
        """
    ).fetchall()
    assert missing == []


def test_effective_deputies_never_exceed_seats(con):
    # Every day of every legislature, up to its end or the extract date.
    over = con.sql(
        """
        with days as (
            select l.legislature, unnest(generate_series(
                l.start_date, coalesce(l.end_date, l.extract_date), interval 1 day
            ))::date as day
            from legislatures l
        ),
        seated as (
            select d.legislature, d.day, count(distinct m.cadastro_id) as n
            from days d
            left join mandates m
              on m.legislature = d.legislature
             and m.is_effective
             and m.start_date <= d.day
             and (m.end_date is null or m.end_date >= d.day)
            group by all
        )
        select s.legislature, s.day, s.n, x.seats
        from seated s join seed_seats x using (legislature)
        where s.n > x.seats
        """
    ).fetchall()
    assert over == []


def test_current_legislature_is_full_at_extract_date(con):
    rows = con.sql(
        """
        select l.legislature, x.seats, count(distinct m.cadastro_id)
        from legislatures l
        join seed_seats x using (legislature)
        join mandates m
          on m.legislature = l.legislature
         and m.is_effective
         and m.start_date <= l.extract_date
         and (m.end_date is null or m.end_date >= l.extract_date)
        where l.end_date is null
        group by all
        """
    ).fetchall()
    assert rows == [("XVII", 230, 230)]


EXPECTED_XVII = {
    "PSD": 89,
    "CH": 60,
    "PS": 58,
    "IL": 9,
    "L": 6,
    "PCP": 3,
    "CDS-PP": 2,
    "BE": 1,
    "PAN": 1,
    "JPP": 1,
}


@pytest.mark.parametrize("day", ["2026-10-16", "extract"])
def test_xvii_seated_split(con, day):
    rows = con.sql(
        f"""
        with d as (
            select {"extract_date" if day == "extract" else f"date '{day}'"} as day
            from legislatures where legislature = 'XVII'
        )
        select g.group_acronym, count(distinct m.cadastro_id)
        from d
        join mandates m
          on m.legislature = 'XVII'
         and m.is_effective
         and m.start_date <= d.day
         and (m.end_date is null or m.end_date >= d.day)
        join group_memberships g
          on g.legislature = m.legislature
         and g.cadastro_id = m.cadastro_id
         and g.start_date <= d.day
         and (g.end_date is null or g.end_date >= d.day)
        group by all
        """
    ).fetchall()
    assert dict(rows) == EXPECTED_XVII


def test_open_group_memberships_have_no_end_date(con):
    n_open, n_end = con.sql(
        """
        select count(*) filter (where is_open), count(*) filter (where is_open and end_date is not null)
        from group_memberships where legislature = 'XVII'
        """
    ).fetchone()
    assert n_open > 0
    assert n_end == 0


def test_one_row_per_deputy(con):
    rows, ids = con.sql("select count(*), count(distinct cadastro_id) from deputies").fetchone()
    assert rows == ids
    # Candidates who never sat are still deputies (people), not mandates.
    assert rows > 230


def test_every_column_has_a_description(con):
    schema = load_schema()
    tables = {
        name: [c[0] for c in con.sql(f"describe {name}").fetchall()]
        for (name,) in con.sql("select table_name from duckdb_tables()").fetchall()
    }
    assert sorted(tables) == sorted(schema)
    for name, cols in tables.items():
        described = schema[name]["columns"]
        assert list(described) == cols, name
        assert all(str(d).strip() for d in described.values()), name
        assert str(schema[name].get("description", "")).strip(), name
