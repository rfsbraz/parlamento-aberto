"""Committee votes in the votes marts (#21).

Like test_votes_marts, PARLAMENTO_DATA_DIR points the data checks at a full data/ folder.
"""

import json
import os
from pathlib import Path

import pytest

from parlamento_aberto.build import build

FIXTURES = Path(__file__).parent / "fixtures" / "data"
DATA_DIR = Path(os.environ.get("PARLAMENTO_DATA_DIR", FIXTURES))
fixture_only = pytest.mark.skipif(DATA_DIR != FIXTURES, reason="pinned to the fixtures")
data_only = pytest.mark.skipif(DATA_DIR == FIXTURES, reason="needs the full data")

BODY_MARTS = ("votes", "initiative_votes", "vote_group_positions", "vote_deputy_dissents")
# Plenary row counts before committee votes were added (#20). They must not move.
PLENARY_FIXTURE_COUNTS = {
    "votes": 13,
    "initiative_votes": 9,
    "vote_group_positions": 112,
    "vote_deputy_dissents": 5,
}
PLENARY_DATA_COUNTS = {
    "votes": 36_527,
    "initiative_votes": 32_969,
    "vote_group_positions": 257_162,
    "vote_deputy_dissents": 36_029,
}
FNE = "Comissão de Negócios Estrangeiros e Comunidades Portuguesas"


@pytest.fixture(scope="module")
def con():
    return build(DATA_DIR)


@pytest.mark.parametrize("mart", BODY_MARTS)
def test_every_row_has_a_body(con, mart):
    (n,) = con.sql(f"select count(*) from {mart} where body is null or body = ''").fetchone()
    assert n == 0


def test_body_is_plenary_or_the_committee(con):
    rows = con.sql(
        """
        select vote_id from votes
        where (committee_id is null) <> (body = 'plenary')
        """
    ).fetchall()
    assert rows == []


@pytest.mark.parametrize("mart", BODY_MARTS)
def test_plenary_row_counts_do_not_change(con, mart):
    expected = PLENARY_FIXTURE_COUNTS if DATA_DIR == FIXTURES else PLENARY_DATA_COUNTS
    (n,) = con.sql(f"select count(*) from {mart} where body = 'plenary'").fetchone()
    assert n == expected[mart]


def test_committee_vote_ids_do_not_collide_with_plenary_ones(con):
    rows, ids = con.sql("select count(*), count(distinct vote_id) from votes").fetchone()
    assert rows == ids


@fixture_only
def test_committee_votes_carry_their_committee(con):
    rows = con.sql(
        """
        select vote_id, committee_id, body, source from votes
        where body <> 'plenary' order by vote_id
        """
    ).fetchall()
    assert [r[0] for r in rows] == [139868, 172545, 193101]
    assert rows[0][1:] == (8448, FNE, "iniciativas")


@fixture_only
def test_committee_vote_positions_come_from_the_detail(con):
    rows = con.sql(
        """
        select group_code, position, inferred, body from vote_group_positions
        where vote_id = 139868 order by group_code
        """
    ).fetchall()
    assert rows == [
        ("CH", "abstention", False, FNE),
        ("IL", "favour", False, FNE),
        ("L", "favour", False, FNE),
        ("PS", "favour", False, FNE),
        ("PSD", "favour", False, FNE),
    ]


@fixture_only
def test_unanimous_committee_vote_infers_the_committee_groups(con):
    # The committee had effective members from these five groups on 2026-10-13, not all
    # ten groups seated in plenary.
    rows = con.sql(
        """
        select group_code, position, inferred from vote_group_positions
        where vote_id = 193101 order by group_code
        """
    ).fetchall()
    assert [r[0] for r in rows] == ["CH", "IL", "L", "PS", "PSD"]
    assert {r[1:] for r in rows} == {("favour", True)}


def _committee_groups_on(day: str) -> dict[int, set[str]]:
    """Groups with an active effective member of each committee on day, read directly from
    the published composition files, independent of the SQL models."""
    out: dict[int, set[str]] = {}
    for path in DATA_DIR.glob("composicao_orgaos/*/Comissoes*.ndjson"):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            committee = int(record["DetalheOrgao"]["idOrgao"])
            for member in record.get("HistoricoComposicao") or []:
                covering = [
                    s
                    for s in member.get("depSituacao") or []
                    if s["sioDtInicio"] <= day and (s["sioDtFim"] or "9999-12-31") >= day
                ]
                if not covering:
                    continue
                latest = max(
                    covering, key=lambda s: (s["sioDtInicio"], s["sioDtFim"] or "9999-12-31")
                )
                if (latest["sioDes"], latest["sioTipMem"]) != ("Ativo", "Efetivo"):
                    continue
                for g in member.get("depGP") or []:
                    if g["gpDtInicio"] <= day and (g["gpDtFim"] or "9999-12-31") >= day:
                        out.setdefault(committee, set()).add(g["gpSigla"])
    return out


def test_inferred_committee_rows_match_the_published_composition(con):
    votes = con.sql(
        """
        select distinct v.vote_id, v.committee_id, v.date::varchar, v.legislature
        from votes v join vote_group_positions p using (vote_id)
        where p.inferred and v.committee_id is not null
        """
    ).fetchall()
    assert votes
    aliases = dict(
        ((leg, alias), code)
        for leg, alias, code in con.sql(
            "select legislature, alias, group_code from seed_group_aliases"
        ).fetchall()
    )
    by_day: dict[str, dict[int, set[str]]] = {}
    for vote_id, committee_id, day, legislature in votes:
        if day not in by_day:
            by_day[day] = _committee_groups_on(day)
        groups = {aliases.get((legislature, g), g) for g in by_day[day].get(committee_id, set())}
        listed = con.execute(
            "select group_code from vote_group_positions where vote_id = ? and not inferred",
            [vote_id],
        ).fetchall()
        inferred = con.execute(
            "select group_code from vote_group_positions where vote_id = ? and inferred",
            [vote_id],
        ).fetchall()
        assert {g for (g,) in inferred} == groups - {g for (g,) in listed}, vote_id


@data_only
def test_committee_vote_count(con):
    (n,) = con.sql("select count(*) from votes where body <> 'plenary'").fetchone()
    assert n == 9_723
