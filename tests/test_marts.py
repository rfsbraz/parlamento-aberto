import json
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
    days = con.sql(
        """
        select l.legislature, x.seats, unnest(generate_series(
            l.start_date, coalesce(l.end_date, l.extract_date), interval 1 day
        ))::date as day
        from legislatures l join seed_seats x using (legislature)
        """
    ).fetchall()
    assert days
    over = []
    for legislature, seats, day in days:
        (n,) = con.execute(
            "select count(*) from seated_on(?::date) where legislature = ?", [day, legislature]
        ).fetchone()
        if n > seats:
            over.append((legislature, day, n))
    assert over == []


def test_current_legislature_is_full_at_extract_date(con):
    rows = con.sql(
        """
        select l.legislature, x.seats, l.extract_date
        from legislatures l join seed_seats x using (legislature)
        where l.end_date is null
        """
    ).fetchall()
    assert [r[0] for r in rows] == ["XVII"]
    for legislature, seats, extract_date in rows:
        (n,) = con.execute(
            "select count(*) from seated_on(?::date) where legislature = ?",
            [extract_date, legislature],
        ).fetchone()
        assert n == seats


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
    if day == "extract":
        sql = "select extract_date from legislatures where legislature = 'XVII'"
        (day,) = con.sql(sql).fetchone()
    rows = con.execute(
        """
        select g.group_acronym, count(*)
        from seated_on(?::date) s
        join group_memberships g
          on g.legislature = s.legislature
         and g.cadastro_id = s.cadastro_id
         and g.start_date <= ?::date
         and (g.end_date is null or g.end_date >= ?::date)
        where s.legislature = 'XVII'
        group by all
        """,
        [day, day, day],
    ).fetchall()
    assert dict(rows) == EXPECTED_XVII


def test_open_group_memberships_have_no_end_date(con):
    n_open, n_end = con.sql(
        """
        select
            count(*) filter (where is_open),
            count(*) filter (where is_open and end_date is not null)
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


# Pinned so a change in the source shows up in the PR diff instead of silently
# moving the seat count through the seated_on tie rule.
EXPECTED_EFFECTIVE_SUSPENDED_OVERLAPS = {"XVII": 2}


def test_overlapping_effective_and_suspended_periods_are_pinned(con):
    rows = con.sql(
        """
        select a.legislature, count(*)
        from mandates a
        join mandates b
          on a.legislature = b.legislature
         and a.cadastro_id = b.cadastro_id
         and a.is_effective
         and b.situation like 'Suspenso%'
         and a.start_date <= coalesce(b.end_date, date '9999-12-31')
         and b.start_date <= coalesce(a.end_date, date '9999-12-31')
        group by all
        """
    ).fetchall()
    assert dict(rows) == EXPECTED_EFFECTIVE_SUSPENDED_OVERLAPS


def test_fixture_biographies_are_synthetic():
    # Real biographies and birth dates must not be committed as fixtures.
    paths = sorted((FIXTURES / "registo_biografico").glob("*/*/*.json"))
    assert paths
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        # II and III use the older shape with camelCase keys.
        name = record.get("CadNomeCompleto") or record.get("cadNomeCompleto")
        born = record.get("CadDtNascimento", record.get("cadDtNascimento"))
        assert name.startswith("Pessoa Sintética"), path
        assert born is None or born.startswith("1900-"), path


def test_old_shape_biographies_are_read(con):
    rows = con.sql(
        """
        select legislature, count(*), count(sex), count(birth_date)
        from stg_registo_biografico__biographies group by 1 order by 1
        """
    ).fetchall()
    assert rows == [("II", 2, 2, 1), ("XVII", 5, 5, 5)]


def test_ii_deputies_get_their_ii_biographies(con):
    rows = con.sql(
        """
        select d.cadastro_id, x.biography_legislature, x.full_name like 'Pessoa Sintética%'
        from stg_informacao_base__deputies d join deputies x using (cadastro_id)
        where d.legislature = 'II' order by 1
        """
    ).fetchall()
    # 312 is one of the 8 II deputies the AR file has no biography for.
    assert rows == [(4, "II", True), (5, "II", True), (312, None, False)]


def test_biography_legislature_is_the_latest_record(con):
    rows = con.sql(
        "select biography_legislature, count(*) from deputies group by 1 order by 1"
    ).fetchall()
    assert rows == [("II", 2), ("XVII", 5), (None, 294)]
