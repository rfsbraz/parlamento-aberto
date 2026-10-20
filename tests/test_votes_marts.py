"""Initiatives and votes marts (#6).

By default the tests build the committed fixtures. Point PARLAMENTO_DATA_DIR at a full data/
folder to run the data checks on real files; fixture-specific tests are skipped then.
"""

import os
from pathlib import Path

import pytest

from parlamento_aberto.build import build

FIXTURES = Path(__file__).parent / "fixtures" / "data"
DATA_DIR = Path(os.environ.get("PARLAMENTO_DATA_DIR", FIXTURES))
fixture_only = pytest.mark.skipif(DATA_DIR != FIXTURES, reason="pinned to the fixtures")

# Codes the AR uses in vote details for deputies outside any group. They are not groups.
NON_GROUP_CODES = {"Indep", "Ninsc"}
# Codes found in a legislature's votes but missing from its InformacaoBase groups, left as
# published until someone decides what to do with them. PPD: I-B lists the party as PSD.
# PSN: 6 votes dated in VII on VI initiatives list PSN, which had no seat in VII.
KNOWN_UNLISTED_CODES = {("I-B", "PPD"), ("VII", "PSN")}
# Share of named dissenters per legislature allowed to stay without a cadastro_id.
MAX_UNMATCHED_DISSENTER_SHARE = 0.01


@pytest.fixture(scope="module")
def con():
    return build(DATA_DIR)


def test_every_detail_string_is_fully_parsed(con):
    errors = con.sql(
        "select detail, error from stg_votes__detail_items where error is not null"
    ).fetchall()
    assert errors == []
    unparsed = con.sql(
        """
        select v.vote_id from votes v
        where v.detail is not null
          and not exists (select 1 from stg_votes__detail_items i where i.detail = v.detail)
        """
    ).fetchall()
    assert unparsed == []


def test_every_group_code_exists_in_its_legislature(con):
    rows = con.sql(
        """
        select distinct c.legislature, c.group_acronym
        from (
            select legislature, group_acronym from vote_group_positions
            union all
            select legislature, group_acronym from vote_deputy_dissents
        ) c
        left join parliamentary_groups g using (legislature, group_acronym)
        where g.group_acronym is null
        """
    ).fetchall()
    unknown = {r for r in rows if r[1] not in NON_GROUP_CODES}
    assert unknown <= KNOWN_UNLISTED_CODES


def test_one_row_per_vote_id(con):
    rows, ids = con.sql("select count(*), count(distinct vote_id) from votes").fetchone()
    assert rows > 0
    assert rows == ids


def test_every_vote_falls_in_a_legislature(con):
    assert con.sql("select vote_id from votes where legislature is null").fetchall() == []


def test_one_position_per_vote_group_and_position(con):
    rows, keys = con.sql(
        """
        select count(*), count(distinct (vote_id, group_acronym, position))
        from vote_group_positions
        """
    ).fetchone()
    assert rows == keys


def test_every_author_id_resolves_to_a_deputy(con):
    missing = con.sql(
        """
        select a.initiative_id, a.cadastro_id from initiative_authors a
        left join deputies d using (cadastro_id)
        where a.author_type = 'deputy' and d.cadastro_id is null
        """
    ).fetchall()
    assert missing == []


def test_every_matched_dissenter_resolves_to_a_deputy(con):
    missing = con.sql(
        """
        select x.vote_id, x.cadastro_id from vote_deputy_dissents x
        left join deputies d using (cadastro_id)
        where x.cadastro_id is not null and d.cadastro_id is null
        """
    ).fetchall()
    assert missing == []


def test_unmatched_dissenters_stay_under_the_threshold(con):
    rows = con.sql(
        """
        select legislature, count(*) filter (where cadastro_id is null) / count(*) as share
        from vote_deputy_dissents group by all having share > ?
        """,
        params=[MAX_UNMATCHED_DISSENTER_SHARE],
    ).fetchall()
    assert rows == []


def test_inferred_positions_are_the_groups_seated_that_day(con):
    # Inferred rows must be exactly the groups seated_on(date) gives, minus groups the vote
    # already lists (for example as absent).
    votes = con.sql(
        """
        select distinct p.vote_id, p.legislature, v.date
        from vote_group_positions p join votes v using (vote_id)
        where p.inferred
        """
    ).fetchall()
    assert votes
    for vote_id, legislature, day in votes:
        seated = con.execute(
            """
            select distinct g.group_acronym
            from seated_on(?::date) s
            join group_memberships g
              on g.legislature = s.legislature
             and g.cadastro_id = s.cadastro_id
             and g.start_date <= ?::date
             and (g.end_date is null or g.end_date >= ?::date)
            where s.legislature = ?
            """,
            [day, day, day, legislature],
        ).fetchall()
        listed = con.execute(
            "select group_acronym from vote_group_positions where vote_id = ? and not inferred",
            [vote_id],
        ).fetchall()
        inferred = con.execute(
            "select group_acronym from vote_group_positions where vote_id = ? and inferred",
            [vote_id],
        ).fetchall()
        assert set(inferred) == set(seated) - set(listed), vote_id


def test_inferred_rows_are_favour_on_unanimous_votes(con):
    rows = con.sql(
        """
        select distinct p.position, v.unanimous
        from vote_group_positions p join votes v using (vote_id)
        where p.inferred
        """
    ).fetchall()
    assert rows == [("favour", True)]


@fixture_only
def test_vote_published_on_two_initiatives_is_one_vote(con):
    assert con.sql(
        "select legislature, source_records from votes where vote_id = 90081"
    ).fetchall() == [("XIV", 2)]
    linked = con.sql(
        "select initiative_id from initiative_votes where vote_id = 90081 order by 1"
    ).fetchall()
    assert linked == [(45634,), (45682,)]


@fixture_only
def test_vote_takes_the_legislature_of_its_date(con):
    # Initiative 314565 is from XVI and was voted in XVII, where JPP sits.
    assert con.sql(
        """
        select v.legislature, i.initiative_legislature
        from votes v join initiative_votes i using (vote_id)
        where vote_id = 171495
        """
    ).fetchall() == [("XVII", "XVI")]


@fixture_only
def test_counts_and_named_dissenters(con):
    rows = con.sql(
        """
        select group_acronym, position, deputies, inferred from vote_group_positions
        where vote_id = 171494 and group_acronym = 'PS' order by position
        """
    ).fetchall()
    assert rows == [("PS", "abstention", None, False), ("PS", "against", 2, False)]
    dissents = con.sql(
        """
        select x.name, x.position, x.cadastro_id is not null, x.candidates
        from vote_deputy_dissents x where vote_id = 171494 order by name
        """
    ).fetchall()
    assert dissents == [
        ("Pedro Delgado Alves", "against", True, 1),
        ("Pedro Vaz", "against", True, 1),
    ]


@fixture_only
def test_unanimous_vote_without_detail_infers_every_seated_group(con):
    rows = con.sql(
        """
        select group_acronym, position, inferred from vote_group_positions
        where vote_id = 171953 order by group_acronym
        """
    ).fetchall()
    groups = [r[0] for r in rows]
    assert groups == ["BE", "CDS-PP", "CH", "IL", "JPP", "L", "PAN", "PCP", "PS", "PSD"]
    assert {(r[1], r[2]) for r in rows} == {("favour", True)}


@fixture_only
def test_unanimous_vote_with_an_absent_group_infers_the_rest(con):
    # Vote 150525 is unanimous and its detail only says JPP was absent.
    rows = dict(
        con.sql(
            """
            select group_acronym, position || ':' || inferred from vote_group_positions
            where vote_id = 150525
            """
        ).fetchall()
    )
    assert rows.pop("JPP") == "absent:false"
    assert len(rows) == 9
    assert set(rows.values()) == {"favour:true"}


@fixture_only
def test_activity_votes_are_included(con):
    rows = con.sql("select source, count(*) from votes group by all order by 1").fetchall()
    assert rows == [("atividades", 5), ("iniciativas", 8)]


@fixture_only
def test_initiative_authors(con):
    rows = con.sql(
        """
        select author_type, count(*) from initiative_authors
        where initiative_id = 356774 group by all order by 1
        """
    ).fetchall()
    assert rows == [("other", 1)]
    kinds = con.sql("select distinct author_type from initiative_authors order by 1").fetchall()
    assert kinds == [("deputy",), ("group",), ("other",)]


@fixture_only
def test_non_inscribed_dissenters_match_on_name(con):
    rows = con.sql(
        """
        select name, group_acronym, cadastro_id is not null from vote_deputy_dissents
        where vote_id = 90081 order by name
        """
    ).fetchall()
    assert rows == [
        ("Cristina Rodrigues", "Ninsc", True),
        ("Joacine Katar Moreira", "Ninsc", True),
    ]
