"""Interests and coalitions marts (#8).

Runs on the committed fixtures. Set PA_DATA_DIR (or PARLAMENTO_DATA_DIR) to a full data/
folder to run the same checks on a real sync; the fixture-only checks skip then.
"""

import csv
import datetime as dt
import os
from pathlib import Path

import pytest

from parlamento_aberto.build import MODELS, build
from parlamento_aberto.interests import InterestsError, parse_record

FIXTURES = Path(__file__).parent / "fixtures" / "data"
_data = os.environ.get("PA_DATA_DIR") or os.environ.get("PARLAMENTO_DATA_DIR")
DATA = Path(_data) if _data else FIXTURES
ON_FIXTURES = DATA.resolve() == FIXTURES.resolve()
fixture_only = pytest.mark.skipif(not ON_FIXTURES, reason="pinned to the fixtures")
data_only = pytest.mark.skipif(ON_FIXTURES, reason="needs the full data")


@pytest.fixture(scope="module")
def con():
    return build(DATA)


def rows(con, sql):
    return con.sql(sql).fetchall()


# --- interests -------------------------------------------------------------------------


@fixture_only
def test_fixture_declarations_per_version(con):
    # One fixture file per published format: V1 (XI), V2 (XII), V3 and V5 (XIV), V5 (XV).
    # Constituinte only lists people, with nothing declared, like Constituinte to X.
    assert rows(
        con,
        """
        select legislature, format_version, count(*), sum(items)
        from interest_declarations where source = 'ar_open_data' group by all order by 1, 2
        """,
    ) == [
        ("XI", "V1", 1, 4),
        ("XII", "V2", 3, 15),
        ("XIV", "V3", 1, 7),
        ("XIV", "V5", 1, 6),
        ("XV", "V5", 1, 0),
    ]


@fixture_only
def test_fixture_items_per_category(con):
    assert rows(
        con,
        """
        select format_version, category, count(*)
        from interests join interest_declarations using (declaration_key)
        where interests.source = 'ar_open_data'
        group by all order by 1, 2
        """,
    ) == [
        ("V1", "activity", 1),
        ("V1", "social_position", 1),
        ("V1", "society", 1),
        ("V1", "support", 1),
        ("V2", "activity", 4),
        ("V2", "other_situation", 3),
        ("V2", "service", 3),
        ("V2", "social_position", 1),
        ("V2", "society", 1),
        ("V2", "support", 3),
        ("V3", "activity", 2),
        ("V3", "other_situation", 1),
        ("V3", "service", 1),
        ("V3", "social_position", 1),
        ("V3", "society", 1),
        ("V3", "support", 1),
        ("V5", "activity", 2),
        ("V5", "other_situation", 1),
        ("V5", "service", 1),
        ("V5", "society", 1),
        ("V5", "support", 1),
    ]


@fixture_only
def test_fixture_dates_paid_and_exclusivity(con):
    # Dates are parsed only when published as a full ISO date; the published text stays.
    assert rows(
        con,
        """
        select start_date_raw, start_date, end_date_raw, end_date, is_paid
        from interests where category = 'activity' and legislature in ('XII', 'XIV')
        order by legislature, cadastro_id, declaration_key, item_number
        """,
    ) == [
        ("2010", None, None, None, True),
        ("2008-03-01", dt.date(2008, 3, 1), "2011-06-19", dt.date(2011, 6, 19), False),
        ("2005", None, None, None, True),
        ("2005", None, "2012", None, True),
        ("2015-02-01", dt.date(2015, 2, 1), None, None, None),
        ("01-02-2012", None, "2014", None, None),
        ("2018-01-01", dt.date(2018, 1, 1), None, None, False),
        ("2010-01-01", dt.date(2010, 1, 1), "2015-12-31", dt.date(2015, 12, 31), None),
    ]
    assert rows(
        con,
        """
        select legislature, format_version, cadastro_id, is_exclusive, position_start_date
        from interest_declarations where format_version in ('V3', 'V5') order by 1, 2
        """,
    ) == [
        ("XIV", "V3", 77, True, dt.date(2019, 10, 25)),
        ("XIV", "V5", 209, True, dt.date(2022, 3, 29)),
        ("XV", "V5", 162, False, dt.date(2022, 3, 29)),
    ]


@fixture_only
def test_fixture_interest_text_is_synthetic(con):
    for col in ("description", "entity"):
        values = [v for (v,) in rows(con, f"select {col} from interests") if v]
        assert values, col
        assert all(
            "sintétic" in v or v in ("Vogal", "Presidente", "Nada a declarar") for v in values
        )


def test_marts_leave_out_family_and_contact_fields(con):
    # Names come from deputies; spouse, marital status, property regime, tax and
    # contact fields are not republished.
    cols = {
        c for t in ("interest_declarations", "interests") for (c, *_) in rows(con, f"describe {t}")
    }
    for banned in ("full_name", "spouse_name", "marital_status", "matrimonial_regime", "tax_id"):
        assert banned not in cols


def test_declarations_match_their_file(con):
    # Every file lists the same people; a declaration must carry the legislature of the
    # file it is in, or the file is a copy of another legislature.
    assert (
        rows(
            con,
            """
        select legislature, declared_legislature, count(*)
        from stg_registo_interesses__declarations
        where declared_legislature is distinct from legislature group by all
        """,
        )
        == []
    )
    (dupes,) = rows(
        con,
        """
        select count(*) from (
            select declaration_key from interest_declarations group by 1 having count(*) > 1
        )
        """,
    )[0]
    assert dupes == 0


def test_every_declarant_is_a_deputy(con):
    assert (
        rows(
            con,
            """
        select d.legislature, d.cadastro_id from interest_declarations d
        anti join deputies using (cadastro_id)
        -- An EpT holder without a seed_ept_holders match has no cadastro_id (#47).
        where d.source = 'ar_open_data' or d.cadastro_id is not null
        """,
        )
        == []
    )


def test_every_item_belongs_to_a_declaration(con):
    assert (
        rows(
            con,
            """
        select i.declaration_key from interests i
        anti join interest_declarations using (declaration_key)
        """,
        )
        == []
    )
    assert (
        rows(
            con,
            """
        select d.declaration_key from interest_declarations d
        where d.items <> (
            select count(*) from interests i where i.declaration_key = d.declaration_key
        )
        """,
        )
        == []
    )


# Declarations, items and people per legislature and format, from the 20 Oct 2026 sync.
# XVI and XVII are not in the dump (declarations moved to the Entidade para a
# Transparência). V3 in XIV has several declarations for some people (111 for 56).
EXPECTED_FULL = [
    ("XI", "V1", 24, 76, 24),
    ("XII", "V2", 43, 402, 43),
    ("XIII", "V2", 61, 556, 61),
    ("XIV", "V3", 111, 905, 56),
    ("XIV", "V5", 15, 165, 15),
    ("XV", "V5", 98, 678, 98),
]


@data_only
def test_full_data_declarations_are_pinned(con):
    got = rows(
        con,
        """
        select legislature, format_version, count(*), sum(items), count(distinct cadastro_id)
        from interest_declarations group by all order by 1, 2
        """,
    )
    assert got == EXPECTED_FULL


@data_only
def test_full_data_every_file_parses(con):
    # Every RegistoInteresses file in data/ is read, including the ones with no declaration.
    files = sorted(p.parent.name for p in (DATA / "registo_interesses").glob("*/records*.ndjson"))
    assert files
    staged = [
        f
        for (f,) in rows(
            con, "select distinct legislature from stg_registo_interesses__files order by 1"
        )
    ]
    assert sorted(staged) == files


def test_unknown_version_fails():
    with pytest.raises(InterestsError, match="RegistoInteressesV9"):
        parse_record({"RegistoInteressesV9": {"x": 1}}, "XV")


def test_unknown_list_fails():
    # A list the parser does not know would be silently dropped, so it fails instead.
    body = {
        "IdCadastroGODE": 1.0,
        "Legislatura": "XV",
        "FactoDeclaracao": {"Id": 1},
        "GenNovaLista": [{"Id": 2}],
    }
    with pytest.raises(InterestsError, match="GenNovaLista"):
        parse_record({"RegistoInteressesV5": body}, "XV")


# --- coalitions ------------------------------------------------------------------------


def seed_rows():
    path = MODELS / "seeds" / "coalitions.csv"
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_every_coalition_row_cites_a_source():
    seed = seed_rows()
    assert seed
    for row in seed:
        assert row["source_url"].startswith("https://"), row
        assert row["election_url"].startswith("https://www.cne.pt/"), row


def test_coalition_rows_are_unique():
    keys = [(r["legislature"], r["ballot_acronym"], r["group_code"]) for r in seed_rows()]
    assert len(keys) == len(set(keys))


# Coalition parties that won no seat on the list (#89, #119), as (legislature, coalition,
# ballot_acronym, group_code). Their group_code is the party's acronym. CDS-PP on the
# Madeira list in the XVI and the Açores list in the XVII won no seat there, though it
# had a group from its seats elsewhere.
WITHOUT_SEATS = [
    ("XV", "AD", "PPD/PSD.CDS-PP.PPM", "CDS-PP"),
    ("XV", "AD", "PPD/PSD.CDS-PP.PPM", "PPM"),
    ("XV", "CDU", "PCP-PEV", "PEV"),
    ("XV", "Madeira Primeiro", "PPD/PSD.CDS-PP", "CDS-PP"),
    ("XVI", "AD", "PPD/PSD.CDS-PP.PPM", "PPM"),
    ("XVI", "CDU", "PCP-PEV", "PEV"),
    ("XVI", "Madeira Primeiro", "PPD/PSD.CDS-PP", "CDS-PP"),
    ("XVII", "AD", "PPD/PSD.CDS-PP.PPM", "CDS-PP"),
    ("XVII", "AD", "PPD/PSD.CDS-PP.PPM", "PPM"),
    ("XVII", "CDU", "PCP-PEV", "PEV"),
]


# Lists that ran in a single regional circle and won seats there (#92), as in the CNE
# official maps 1/2022, 2-A/2024 and 2025: (legislature, ballot_acronym) -> coalition, list
# name and {group_code: has_seats}. Every seat on these lists sat with PSD (#119).
REGIONAL_LISTS = {
    ("XV", "PPD/PSD.CDS-PP"): (
        "Madeira Primeiro",
        "Madeira Primeiro",
        {"PSD": "true", "CDS-PP": "false"},
    ),
    ("XV", "PPD/PSD.CDS-PP.PPM"): (
        "AD",
        "AD/Aliança Democrática",
        {"PSD": "true", "CDS-PP": "false", "PPM": "false"},
    ),
    ("XVI", "PPD/PSD.CDS-PP"): (
        "Madeira Primeiro",
        "Madeira Primeiro",
        {"PSD": "true", "CDS-PP": "false"},
    ),
    ("XVII", "PPD/PSD.CDS-PP.PPM"): (
        "AD",
        "Aliança Democrática",
        {"PSD": "true", "CDS-PP": "false", "PPM": "false"},
    ),
}


def test_regional_coalition_lists_are_in_the_seed():
    found = {}
    for r in seed_rows():
        key = (r["legislature"], r["ballot_acronym"])
        if key in REGIONAL_LISTS:
            coalition, name, groups = found.setdefault(
                key, (r["coalition"], r["coalition_name"], {})
            )
            assert (r["coalition"], r["coalition_name"]) == (coalition, name), r
            groups[r["group_code"]] = r["has_seats"]
    assert found == REGIONAL_LISTS


def test_has_seats_is_a_boolean_on_every_row():
    assert {r["has_seats"] for r in seed_rows()} == {"true", "false"}


def test_parties_without_seats_are_pinned():
    seatless = [
        (r["legislature"], r["coalition"], r["ballot_acronym"], r["group_code"])
        for r in seed_rows()
        if r["has_seats"] == "false"
    ]
    assert sorted(seatless) == sorted(WITHOUT_SEATS)


def test_parties_without_seats_have_no_group(con):
    # A party with no seat on the list has no group name there. It may still have a group
    # in that legislature, but only from seats on another of its lists.
    grouped = rows(
        con,
        """
        select c.legislature, c.ballot_acronym, c.group_code, c.group_name from coalitions c
        where not c.has_seats
        and (c.group_name is not null or (
            exists (
                select 1 from parliamentary_groups g
                where g.legislature = c.legislature and g.group_acronym = c.group_code
            )
            and not exists (
                select 1 from coalitions o
                where o.legislature = c.legislature and o.group_code = c.group_code
                and o.has_seats
            )
        ))
        """,
    )
    assert grouped == []


@data_only
def test_has_seats_matches_who_sat_for_the_list(con):
    # has_seats is per list (#119): true when someone elected in a circle where the list won
    # seats sat in that group. Substitutes who never sat do not count.
    wrong = rows(
        con,
        """
        with sat as (
            select distinct s.legislature, s.ballot_acronym, g.group_acronym
            from ballot_list_seats s
            join electoral_circles e on e.legislature = s.legislature and e.name = s.circle_name
            join mandates m on m.legislature = e.legislature and m.circle_id = e.circle_id
            join group_memberships g
                on g.legislature = m.legislature and g.cadastro_id = m.cadastro_id
            where s.seats > 0
            and m.situation not in ('Suplente', 'Suspenso(Não Eleito)', 'Desistência')
        )
        select c.legislature, c.ballot_acronym, c.group_code, c.has_seats from coalitions c
        where c.has_seats != exists (
            select 1 from sat
            where sat.legislature = c.legislature and sat.ballot_acronym = c.ballot_acronym
            and sat.group_acronym = c.group_code
        )
        """,
    )
    assert wrong == []


def test_cdu_note_since_2022_is_the_pev_note():
    # PEV has had no seats since the 2022 election. The XVI row once carried the AD note.
    notes = {
        r["legislature"]: r["note"]
        for r in seed_rows()
        if r["coalition"] == "CDU"
        and r["legislature"] in ("XV", "XVI", "XVII")
        and r["has_seats"] == "true"
    }
    assert notes == dict.fromkeys(
        ("XV", "XVI", "XVII"), "PEV has had no seats since 2022, so PCP is the only group."
    )
    assert not [r for r in seed_rows() if r["coalition"] == "CDU" and "PPM" in r["note"]]


def test_coalition_groups_exist_in_the_groups_mart(con):
    # On the fixtures only some legislatures have a group list; on full data, all do.
    missing = rows(
        con,
        """
        select c.legislature, c.coalition, c.group_code from coalitions c
        where c.has_seats
        and c.legislature in (select legislature from parliamentary_groups)
        and not exists (
            select 1 from parliamentary_groups g
            where g.legislature = c.legislature and g.group_acronym = c.group_code
        )
        """,
    )
    assert missing == []


@data_only
def test_every_coalition_legislature_has_groups(con):
    assert (
        rows(
            con,
            """
        select distinct legislature from coalitions
        except select legislature from parliamentary_groups
        """,
        )
        == []
    )


@fixture_only
def test_fixture_coalitions(con):
    # XVII: AD ran as PPD/PSD.CDS-PP, and with PPM only in the Açores. CDU seats only PCP,
    # since PEV lost its seats in 2022. PPM and PEV are on the lists but won no seat.
    assert rows(
        con,
        "select coalition, ballot_acronym, group_code, group_name is not null, has_seats "
        "from coalitions where legislature = 'XVII' order by 1, 2, 3",
    ) == [
        ("AD", "PPD/PSD.CDS-PP", "CDS-PP", True, True),
        ("AD", "PPD/PSD.CDS-PP", "PSD", True, True),
        ("AD", "PPD/PSD.CDS-PP.PPM", "CDS-PP", False, False),
        ("AD", "PPD/PSD.CDS-PP.PPM", "PPM", False, False),
        ("AD", "PPD/PSD.CDS-PP.PPM", "PSD", True, True),
        ("CDU", "PCP-PEV", "PCP", True, True),
        ("CDU", "PCP-PEV", "PEV", False, False),
    ]
