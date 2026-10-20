"""Committee votes in the votes marts (#21).

Like test_votes_marts, PARLAMENTO_DATA_DIR points the data checks at a full data/ folder.
"""

import json
import os
import shutil
from pathlib import Path

import pytest

from parlamento_aberto.build import build
from parlamento_aberto.checks import committee_votes_without_composition

FIXTURES = Path(__file__).parent / "fixtures" / "data"
DATA_DIR = Path(os.environ.get("PARLAMENTO_DATA_DIR", FIXTURES))
fixture_only = pytest.mark.skipif(DATA_DIR != FIXTURES, reason="pinned to the fixtures")
data_only = pytest.mark.skipif(DATA_DIR == FIXTURES, reason="needs the full data")

BODY_MARTS = ("votes", "initiative_votes", "vote_group_positions", "vote_deputy_dissents")
# Plenary row counts before committee votes were added (#20). They must not move.
PLENARY_FIXTURE_COUNTS = {
    "votes": 14,
    "initiative_votes": 10,
    "vote_group_positions": 120,
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


# Known gaps in the source, decided to stay as published (#24). If a pin moves, check the
# new rows, then update the pin here and the note in docs/known-gaps.md.
NO_DETAIL_NON_UNANIMOUS = {"plenary": 1_130, "committee": 4_705}


@data_only
@pytest.mark.parametrize("body", sorted(NO_DETAIL_NON_UNANIMOUS))
def test_non_unanimous_votes_without_detail_are_pinned(con, body):
    (votes,) = con.sql(
        f"""
        select count(*) from votes
        where not unanimous and detail is null
          and {"body = 'plenary'" if body == "plenary" else "body <> 'plenary'"}
        """
    ).fetchone()
    assert votes == NO_DETAIL_NON_UNANIMOUS[body], (
        f"{body} votes that are not unanimous and have no detail: {votes:,}, pinned at "
        f"{NO_DETAIL_NON_UNANIMOUS[body]:,}. Check the new rows, then update the pin in "
        "tests/test_committee_votes.py and the note in docs/known-gaps.md."
    )


@data_only
def test_non_unanimous_committee_votes_without_detail_have_no_group_rows(con):
    # Decided: no inference from wording such as "sem votos contra".
    (rows,) = con.sql(
        """
        select count(*) from vote_group_positions p join votes v using (vote_id)
        where v.body <> 'plenary' and not v.unanimous and v.detail is null
          and p.position <> 'absent'
        """
    ).fetchone()
    assert rows == 0


def test_unanimous_committee_votes_have_a_composition(con):
    missing = committee_votes_without_composition(con)
    assert missing == [], "; ".join(
        f"unanimous committee vote {vote_id} needs inferred rows but committee "
        f"{committee_id} has no members in ComposicaoOrgaos"
        for committee_id, vote_id in missing
    )


SYNTHETIC_COMMITTEE_VOTE = {
    "IniAutorOutros": {"iniAutorComissao": None, "nome": "Governo", "sigla": "V"},
    "IniDescTipo": "Proposta de Lei",
    "IniEventos": [
        {
            "Comissao": [
                {
                    "IdComissao": "999999",
                    "Nome": "Comissão sintética sem composição",
                    "Votacao": [
                        {
                            "ausencias": None,
                            "data": "2026-10-13",
                            "descricao": None,
                            "detalhe": None,
                            "id": "999999001",
                            "resultado": "Aprovado",
                            "reuniao": "1",
                            "unanime": "unanime",
                        }
                    ],
                }
            ],
            "DataFase": "2026-10-13",
            "EvtId": "1",
            "Fase": "Votação na especialidade",
        }
    ],
    "IniId": "999999",
    "IniLinkTexto": "https://example.invalid/synthetic",
    "IniNr": "1",
    "IniSel": "1",
    "IniTipo": "P",
    "IniTitulo": "Iniciativa sintética",
}


def test_missing_composition_check_fires(tmp_path):
    # A synthetic unanimous committee vote, with no detail, in a committee that has no
    # members in ComposicaoOrgaos.
    data = tmp_path / "data"
    shutil.copytree(FIXTURES, data)
    path = data / "iniciativas" / "XVII" / "999" / "999999.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(SYNTHETIC_COMMITTEE_VOTE, ensure_ascii=False), encoding="utf-8")
    con = build(data)
    assert committee_votes_without_composition(con) == [(999999, 999999001)]
