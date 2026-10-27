"""Interventions and questions marts (#7).

Runs on the committed fixtures. Set PA_DATA_DIR to a full data/ folder to run the
same checks on a real sync; the fixture-only checks skip then.
"""

import json
import os
from pathlib import Path

import pytest

from parlamento_aberto.build import build

FIXTURES = Path(__file__).parent / "fixtures" / "data"
DATA = Path(os.environ.get("PA_DATA_DIR", FIXTURES))
ON_FIXTURES = DATA.resolve() == FIXTURES.resolve()

# Share of rows with a person id that may fail to resolve to a deputy, per legislature.
# The 20 Oct 2026 sync has none for speakers and none for authors. The same share
# bounds questions published without any author.
MAX_UNMATCHED_SHARE = 0.005


@pytest.fixture(scope="module")
def con():
    return build(DATA)


def lock_counts(dataset: str) -> dict[str, int]:
    lock = json.loads((DATA / "_meta" / "sources.lock.json").read_text(encoding="utf-8"))
    return {
        key.split("/")[1]: entry["records"]
        for key, entry in lock.items()
        if key.split("/")[0] == dataset
    }


def counts(con, sql: str) -> dict[str, int]:
    return dict(con.sql(sql).fetchall())


def test_intervention_rows_match_the_lock(con):
    expected = lock_counts("intervencoes")
    assert expected
    staged = counts(
        con, "select legislature, count(*) from stg_intervencoes__interventions group by all"
    )
    assert staged == expected
    # The mart drops the empty records AR publishes (every key null, no id) and nothing else.
    empty = counts(
        con,
        """
        select legislature, count(*) filter (where intervention_id is null)
        from stg_intervencoes__interventions group by all
        """,
    )
    mart = counts(con, "select legislature, count(*) from interventions group by all")
    assert mart == {leg: n - empty[leg] for leg, n in expected.items() if n - empty[leg]}


def test_question_rows_match_the_lock(con):
    expected = lock_counts("perguntas_requerimentos")
    assert expected
    staged = counts(
        con, "select legislature, count(*) from stg_perguntas_requerimentos__questions group by all"
    )
    assert staged == expected
    assert counts(con, "select legislature, count(*) from questions group by all") == expected


def test_ids_are_unique_per_legislature(con):
    for table, key in [("interventions", "intervention_id"), ("questions", "question_id")]:
        (dupes,) = con.sql(
            f"select count(*) - count(distinct (legislature, {key})) from {table}"
        ).fetchone()
        assert dupes == 0, table


def unmatched(con, table: str) -> list:
    return con.sql(
        f"""
        select
            t.legislature,
            count(*) as with_id,
            count(*) filter (where d.cadastro_id is null) as unmatched
        from {table} t
        left join deputies d using (cadastro_id)
        where t.cadastro_id is not null
        group by all
        order by all
        """
    ).fetchall()


@pytest.mark.parametrize("table", ["interventions", "question_authors"])
def test_people_resolve_to_deputies(con, table):
    rows = unmatched(con, table)
    assert rows
    over = [r for r in rows if r[2] > MAX_UNMATCHED_SHARE * r[1]]
    assert over == []
    if ON_FIXTURES:
        assert all(r[2] == 0 for r in rows)


def test_questions_have_authors(con):
    # AR publishes one requerimento with no authors (VII, id 16560), so this is a share too.
    rows = con.sql(
        """
        select legislature, count(*), count(*) filter (where author_count = 0)
        from questions group by all
        """
    ).fetchall()
    assert [r for r in rows if r[2] > MAX_UNMATCHED_SHARE * r[1]] == []
    if ON_FIXTURES:
        assert all(r[2] == 0 for r in rows)
    authors, summed = con.sql(
        "select (select count(*) from question_authors), (select sum(author_count) from questions)"
    ).fetchone()
    assert authors == summed


def test_recipient_and_answer_counts_add_up(con):
    rows, summed = con.sql(
        """
        select
            (select count(*) from question_recipients),
            (select sum(recipient_count) from questions)
        """
    ).fetchone()
    assert rows == summed
    (bad,) = con.sql(
        """
        select count(*) from questions q
        left join (
            select legislature, question_id, sum(answer_count) as n
            from question_recipients group by all
        ) r using (legislature, question_id)
        where q.answer_count < coalesce(r.n, 0)
        """
    ).fetchone()
    assert bad == 0


def test_speaker_kind_matches_the_speaker_fields(con):
    (bad,) = con.sql(
        """
        select count(*) from interventions
        where (speaker_kind = 'deputy') != (cadastro_id is not null)
           or (speaker_kind = 'government')
              != (cadastro_id is null and government_member_name is not null)
        """
    ).fetchone()
    assert bad == 0
    kinds = {k for (k,) in con.sql("select distinct speaker_kind from interventions").fetchall()}
    assert {"deputy", "government"} <= kinds


def test_one_publication_per_intervention(con):
    (n,) = con.sql(
        "select coalesce(max(publication_count), 0) from stg_intervencoes__interventions"
    ).fetchone()
    assert n <= 1
    (missing,) = con.sql(
        "select count(*) from interventions where publication_date is null or diary_url is null"
    ).fetchone()
    assert missing == 0


@pytest.mark.skipif(not ON_FIXTURES, reason="fixture content only")
def test_fixture_free_text_is_synthetic(con):
    # Free text can name private citizens or companies, so fixtures carry made-up text.
    for table, col in [
        ("interventions", "summary"),
        ("interventions", "debate"),
        ("questions", "subject"),
    ]:
        values = [v for (v,) in con.sql(f"select {col} from {table}").fetchall() if v]
        assert values, (table, col)
        assert all("sintétic" in v for v in values), (table, col)
    urls = [v for (v,) in con.sql("select document_url from questions").fetchall()]
    assert all(u.startswith("https://app.parlamento.pt/fixture/") for u in urls)


# First and last plenary meeting date with interventions, per legislature, as AR
# publishes them. docs/known-gaps.md explains the gaps these pin. The running
# legislature's last date is a floor, since every new sitting moves it.
COVERAGE_FULL = {
    "II": ("1980-12-10", "1982-04-25"),
    "IV": ("1985-11-04", "1986-10-31"),
    "V": ("1987-08-13", "1991-10-24"),
    "VI": ("1991-11-07", "1995-10-11"),
    "VII": ("1996-10-16", "1999-10-01"),
    "VIII": ("1999-10-25", "2002-02-20"),
    "IX": ("2002-04-05", "2005-01-26"),
    "X": ("2005-03-10", "2009-09-10"),
    "XI": ("2009-10-15", "2011-05-19"),
    "XII": ("2013-09-16", "2015-10-21"),
    "XIII": ("2015-10-23", "2019-10-09"),
    "XIV": ("2019-10-25", "2022-03-22"),
    "XV": ("2022-03-29", "2024-03-13"),
    "XVI": ("2024-03-26", "2025-04-30"),
    "XVII": ("2025-06-03", "2026-09-18"),
}
COVERAGE_FIXTURES = {"XVII": ("2026-09-16", "2026-09-16")}
COVERAGE_PINS = "tests/test_interventions_questions.py and docs/known-gaps.md"


def coverage_hint(legislature, edge, actual, pinned):
    """What a coverage change means. A later first date, an earlier last date or a missing
    legislature is data AR stopped publishing: restore it, the pin is right. An earlier
    first date, a later last date or a new legislature is a gap AR filled."""
    dropped = {
        "first": lambda: actual > pinned,
        "last": lambda: actual < pinned,
        "missing": lambda: True,
        "new": lambda: False,
    }[edge]()
    seen = f"Intervencoes {legislature} {edge}: {actual or 'none'}, pinned {pinned or 'none'}."
    if dropped:
        return (
            f"{seen} AR dropped data, do not move the pin. Restore "
            f"data/intervencoes/{legislature} from git history (see #115 and #122)."
        )
    return f"{seen} AR filled a gap: update the pin in {COVERAGE_PINS}."


def test_intervention_coverage_is_pinned(con):
    expected = COVERAGE_FIXTURES if ON_FIXTURES else COVERAGE_FULL
    rows = con.sql(
        """
        select
            i.legislature,
            strftime(min(i.meeting_date), '%Y-%m-%d'),
            strftime(max(i.meeting_date), '%Y-%m-%d'),
            any_value(l.end_date) is null
        from interventions i join legislatures l using (legislature)
        group by all
        """
    ).fetchall()
    first_dates = {r[0]: r[1] for r in rows}
    for legislature in sorted(set(expected) - set(first_dates)):
        pytest.fail(coverage_hint(legislature, "missing", None, expected[legislature][0]))
    for legislature in sorted(set(first_dates) - set(expected)):
        pytest.fail(coverage_hint(legislature, "new", first_dates[legislature], None))
    for legislature, first, last, is_open in rows:
        pinned_first, pinned_last = expected[legislature]
        assert first == pinned_first, coverage_hint(legislature, "first", first, pinned_first)
        hint = coverage_hint(legislature, "last", last, pinned_last)
        if is_open:
            assert last >= pinned_last, hint
        else:
            assert last == pinned_last, hint


def test_coverage_hint_depends_on_the_direction():
    # 2026-10-26: AR's XVII file started on 2026-09-16 instead of 2025-06-03 because AR
    # dropped 7984 records down to 149. Moving the pin would have hidden it.
    dropped = coverage_hint("XVII", "first", "2026-09-16", "2025-06-03")
    assert "AR dropped data, do not move the pin" in dropped
    assert "update the pin" not in dropped
    assert "AR dropped data" in coverage_hint("XVI", "last", "2025-01-10", "2025-04-30")
    assert "AR dropped data" in coverage_hint("XVI", "missing", None, "2024-03-26")
    filled = coverage_hint("XII", "first", "2011-06-20", "2013-09-16")
    assert "AR filled a gap" in filled and "update the pin" in filled
    assert "AR filled a gap" in coverage_hint("XVI", "last", "2025-05-02", "2025-04-30")
    assert "AR filled a gap" in coverage_hint("III", "new", "1983-06-01", None)


def test_sent_dates_outside_the_legislature_are_flagged(con):
    rows = con.sql(
        """
        select q.sent_date, q.sent_date_raw, q.sent_date_invalid,
            year(try_cast(q.sent_date_raw as date)) not between year(l.start_date)
                and year(coalesce(l.end_date, current_date)) as outside
        from questions q join legislatures l using (legislature)
        where q.sent_date_raw is not null
        """
    ).fetchall()
    assert rows
    for sent_date, raw, invalid, outside in rows:
        assert invalid == bool(outside or outside is None), raw
        if invalid:
            assert sent_date is None, raw
        else:
            assert str(sent_date) == raw, raw
    (missing,) = con.sql(
        "select count(*) from questions where sent_date_raw is null and sent_date_invalid"
    ).fetchone()
    assert missing == 0


@pytest.mark.skipif(not ON_FIXTURES, reason="fixture content only")
def test_fixture_has_an_invalid_sent_date(con):
    rows = con.sql(
        "select question_id, sent_date_raw from questions where sent_date_invalid"
    ).fetchall()
    assert rows == [(187751, "2125-06-12")]
