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
