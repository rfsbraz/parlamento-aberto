"""Plenary attendance marts (#71).

The committed fixtures (tests/fixtures/data) only have meetings without an attendance list,
as published from the Constituinte to IV, so the mart is empty there. The fixture-only tests
build a copy of them with tests/fixtures/plenary_attendance on top: synthetic deputies
(Pessoa Sintética, ids from 9900001) and synthetic attendance lists for XVI and XIV, plus
fetched dates for those files in sources.lock.json.
Set PARLAMENTO_DATA_DIR to a full data/ folder to run the data checks on a real sync.
"""

import csv
import datetime as dt
import json
import os
import shutil
from pathlib import Path

import duckdb
import pytest

from parlamento_aberto import release
from parlamento_aberto.build import MODELS, build, load_schema

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "data"
OVERLAY = ROOT / "tests" / "fixtures" / "plenary_attendance"
_data = os.environ.get("PARLAMENTO_DATA_DIR")
DATA = Path(_data) if _data else None
fixture_only = pytest.mark.skipif(DATA is not None, reason="pinned to the fixtures")
data_only = pytest.mark.skipif(DATA is None, reason="needs the full data")

MARTS = ("plenary_attendance", "plenary_attendance_summary")
STAGING = "stg_composicao_orgaos__plenary_attendance"
CATEGORIES = {
    "present",
    "other_body_or_mission",
    "justified",
    "missed_quorum_vote",
    "pending",
    "unclassified",
    "unjustified",
}
SEED = MODELS / "seeds" / "attendance_codes.csv"
# The overlay's XVI file was "fetched" 60 days after the 2024-09-18 meeting.
FETCHED = {"composicao_orgaos/XVI": "2024-11-17", "composicao_orgaos/XIV": "2026-10-20"}

# Rows and meetings with an attendance list per legislature, as in the AR files of the
# 20 October 2026 sync. Constituinte to IV have none. XVII is still running, so its new
# meetings only add to its numbers.
OPEN_LEGISLATURE = "XVII"
SOURCE_COUNTS = {
    "V": (234, 1),
    "VI": (86019, 374),
    "VII": (91526, 406),
    "VIII": (51517, 224),
    "IX": (61871, 269),
    "X": (107640, 468),
    "XI": (35650, 155),
    "XII": (107868, 469),
    "XIII": (94990, 413),
    "XIV": (45310, 197),
    "XV": (44160, 192),
    "XVI": (23690, 103),
    "XVII": (28750, 125),
}


def synthetic_data(tmp: Path, extra: dict | None = None) -> Path:
    """The committed fixtures plus the overlay, with the overlay's fetched dates."""
    shutil.copytree(FIXTURES, tmp, dirs_exist_ok=True)
    shutil.copytree(OVERLAY, tmp, dirs_exist_ok=True)
    lock_path = tmp / "_meta" / "sources.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    for key, fetched in FETCHED.items():
        lock[key] = {"fetched": fetched, "stale": False}
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    for rel, line in (extra or {}).items():
        with (tmp / rel).open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return tmp


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    if DATA is not None:
        return build(DATA)
    return build(synthetic_data(tmp_path_factory.mktemp("data")))


def rows(con, sql, params=None):
    return con.execute(sql, params or []).fetchall()


def seed():
    with SEED.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --- the code seed ---------------------------------------------------------------------


def test_seed_has_one_row_per_code_with_a_category_and_a_source():
    codes = [r["code"] for r in seed()]
    assert len(codes) == len(set(codes)) == 14
    for r in seed():
        assert r["category"] in CATEGORIES - {"unclassified"}, r["code"]
        assert r["meaning"].strip() and r["source"].strip(), r["code"]
        assert "https://www.parlamento.pt/" in r["source"], r["code"]


def test_seed_categories():
    category = {r["code"]: r["category"] for r in seed()}
    assert category == {
        "PT": "present",
        "PR": "present",
        "PP": "present",
        "PNO": "other_body_or_mission",
        "CO": "other_body_or_mission",
        "ME": "other_body_or_mission",
        "MP": "other_body_or_mission",
        "FJ": "justified",
        "FIJ": "justified",
        "FAJ": "justified",
        "QVJ": "justified",
        "QV": "missed_quorum_vote",
        "FA": "pending",
        "FI": "unjustified",
    }
    # Only FA ages out of pending, and never into unjustified.
    assert {r["code"]: r["pending_days"] for r in seed() if r["pending_days"]} == {"FA": "60"}


# --- the free-text reason never enters ---------------------------------------------------


def test_no_model_has_the_absence_reason(con):
    schema = load_schema()
    for model in (STAGING, *MARTS):
        cols = [c[0].lower() for c in rows(con, f"describe {model}")]
        documented = [c.lower() for c in schema[model]["columns"]]
        for name in cols + documented:
            assert "motivo" not in name and "reason" not in name, (model, name)
    sql = (MODELS / "staging" / f"{STAGING}.sql").read_text(encoding="utf-8")
    assert "motivo" not in sql.lower()


@fixture_only
def test_the_synthetic_reason_is_nowhere_in_the_build(con):
    # The overlay sets motivoFalta to "motivo sintético" on its absences.
    raw = OVERLAY / "composicao_orgaos" / "XVI" / "Plenario.Reunioes.ndjson"
    assert "motivo sintético" in raw.read_text(encoding="utf-8")
    for model in (STAGING, *MARTS):
        cols = [c[0] for c in rows(con, f"describe {model}")]
        text = " || ".join(f"coalesce(cast({c} as varchar), '')" for c in cols)
        sql = f"select count(*) from {model} where ({text}) ilike '%motivo%'"
        assert con.execute(sql).fetchone() == (0,), model


# --- matching to deputies ------------------------------------------------------------------


def test_every_row_has_a_cadastro_id(con):
    assert rows(con, "select count(*) from plenary_attendance where cadastro_id is null") == [(0,)]


def test_each_name_and_group_is_exactly_one_person_in_its_legislature(con):
    bad = rows(
        con,
        """
        select s.legislature, s.parliamentary_name, s.group_acronym, count(distinct d.cadastro_id)
        from (
            select distinct legislature, parliamentary_name, group_acronym
            from stg_composicao_orgaos__plenary_attendance
        ) s
        left join stg_informacao_base__deputies d
          on d.legislature = s.legislature
         and d.parliamentary_name = s.parliamentary_name
         and list_contains(list_transform(d.groups, g -> g.group_acronym), s.group_acronym)
        group by all
        having count(distinct d.cadastro_id) <> 1
        """,
    )
    assert bad == []


def test_one_row_per_meeting_and_person(con):
    assert rows(
        con,
        """
        select count(*) from (
            select meeting_id, cadastro_id from plenary_attendance group by all having count(*) > 1
        )
        """,
    ) == [(0,)]


def test_mart_keeps_every_staging_row(con):
    (a,) = con.execute(f"select count(*) from {STAGING}").fetchone()
    (b,) = con.execute("select count(*) from plenary_attendance").fetchone()
    assert a == b


@fixture_only
def test_same_name_in_another_legislature_is_another_person(con):
    # "Pessoa Sintética Um" is 9900001 in XVI and 9900005 in XIV.
    assert rows(
        con,
        """
        select legislature, cadastro_id from plenary_attendance
        where parliamentary_name = 'Pessoa Sintética Um' group by all order by 1
        """,
    ) == [("XIV", 9900005), ("XVI", 9900001)]


@fixture_only
def test_same_name_in_two_groups_is_told_apart_by_group(con):
    assert rows(
        con,
        """
        select group_code, cadastro_id from plenary_attendance
        where parliamentary_name = 'Pessoa Sintética Dois' group by all order by 1
        """,
    ) == [("CH", 9900003), ("PSD", 9900002)]


# --- codes, categories and the FA cutoff -------------------------------------------------


def test_every_row_has_a_category(con):
    assert rows(con, "select distinct code from plenary_attendance where category is null") == []


def test_categories_match_the_seed_except_aged_fa(con):
    bad = rows(
        con,
        """
        select distinct p.code, p.category
        from plenary_attendance p join seed_attendance_codes s using (code)
        where p.category <> s.category
          and not (p.code = 'FA' and p.category = 'unclassified')
        """,
    )
    assert bad == []


def test_fa_is_pending_under_60_days_old_then_unclassified(con):
    bad = rows(
        con,
        """
        select count(*) from plenary_attendance
        where code = 'FA'
          and category <> case when source_updated - meeting_date < 60
                               then 'pending' else 'unclassified' end
        """,
    )
    assert bad == [(0,)]
    assert rows(
        con, "select count(*) from plenary_attendance where is_pending <> (category = 'pending')"
    ) == [(0,)]


def test_nothing_but_fi_is_unjustified(con):
    assert rows(
        con, "select distinct code from plenary_attendance where category = 'unjustified'"
    ) in ([("FI",)], [])


@fixture_only
def test_fa_cutoff_on_the_fixture(con):
    # XVI was fetched on 2024-11-17: the 2024-09-18 FA is 60 days old, the 2024-09-19 one 59.
    assert rows(
        con,
        """
        select cast(meeting_date as varchar), cast(source_updated as varchar), category, is_pending
        from plenary_attendance where code = 'FA' order by meeting_date
        """,
    ) == [
        ("2024-09-18", "2024-11-17", "unclassified", False),
        ("2024-09-19", "2024-11-17", "pending", True),
    ]


def _meeting(code):
    return {
        "Presencas": {
            "dtReuniao": "2024-10-02",
            "tipoReuniao": "Ordinária",
            "presencas": [
                {
                    "motivoFalta": None,
                    "nomeDeputado": "Pessoa Sintética Um",
                    "siglaFalta": code,
                    "siglaGrupo": "PS",
                    "siglaQualidadePresencaOrgao": None,
                }
            ],
        },
        "Reuniao": {"reuId": 900099.0, "reuNumero": 9, "selNumero": "2", "reuDataHora": None},
    }


@fixture_only
def test_an_unmapped_code_stops_the_build(tmp_path):
    rel = "composicao_orgaos/XVI/Plenario.Reunioes.ndjson"
    data = synthetic_data(tmp_path, {rel: _meeting("ZZ")})
    with pytest.raises(duckdb.Error, match="not in seed_attendance_codes: ZZ"):
        build(data)


@fixture_only
def test_fa_without_a_fetched_date_stops_the_build(tmp_path):
    data = synthetic_data(tmp_path)
    lock_path = data / "_meta" / "sources.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    del lock["composicao_orgaos/XVI"]
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(duckdb.Error, match="no fetched date"):
        build(data)


def test_ceremonial_flag(con):
    assert rows(
        con,
        """
        select count(*) from plenary_attendance
        where is_ceremonial <> (meeting_type in ('Solene', 'Comemorativa'))
        """,
    ) == [(0,)]


@fixture_only
def test_fixture_rows(con):
    assert rows(
        con,
        """
        select legislature, meeting_id, meeting_number, session_number,
               cast(meeting_date as varchar), meeting_type, is_ceremonial, cadastro_id,
               group_code, group_code_raw, code, category, is_pending
        from plenary_attendance where legislature = 'XVI' and meeting_id = 900002
        order by cadastro_id
        """,
    ) == [
        ("XVI", 900002, 2, 1, "2024-04-04", "Solene", True, 9900001, "PS", "PS", "ME",
         "other_body_or_mission", False),
        ("XVI", 900002, 2, 1, "2024-04-04", "Solene", True, 9900002, "PSD", "PSD", "QVJ",
         "justified", False),
        ("XVI", 900002, 2, 1, "2024-04-04", "Solene", True, 9900003, "CH", "CH", "FI",
         "unjustified", False),
        ("XVI", 900002, 2, 1, "2024-04-04", "Solene", True, 9900004, "PSD", "PSD", "MP",
         "other_body_or_mission", False),
    ]  # fmt: skip


@fixture_only
def test_fixture_counts_per_legislature(con):
    # XVI has a fifth meeting without a list, which adds no rows.
    assert rows(
        con,
        """
        select legislature, count(*), count(distinct meeting_id)
        from plenary_attendance group by all order by 1
        """,
    ) == [("XIV", 1, 1), ("XVI", 16, 4)]


@data_only
def test_rows_and_meetings_per_legislature_match_the_source(con):
    got = {
        leg: (n, m)
        for leg, n, m in rows(
            con,
            """
            select legislature, count(*), count(distinct meeting_id)
            from plenary_attendance group by all
            """,
        )
    }
    assert got.keys() == SOURCE_COUNTS.keys()
    for leg, (n, meetings) in SOURCE_COUNTS.items():
        if leg == OPEN_LEGISLATURE:
            assert got[leg][0] >= n and got[leg][1] >= meetings, leg
        else:
            assert got[leg] == (n, meetings), leg


@data_only
def test_xvii_fa_and_qv_are_one_per_meeting_and_person(con):
    # By the source file's legislature (composicao_orgaos/XVII): every FA and QV is in a
    # distinct meeting and person. AR justifies absences after the fact, so FA and QV shrink
    # (FA to FJ, QV to QVJ or FJ) and only the absences as a whole have a floor: 1471 rows
    # coded FA, FI, FJ, FIJ, FAJ, QV or QVJ on 20 October 2026 (34 FA, 42 QV). The 22 October
    # sync has the same 1471 (23 FA, 30 QV). Counting every row dated from 1 January 2025 adds
    # XVI's 6 FA and 1 QV of 2025, which no longer change.
    xvii = {
        code: (n, distinct)
        for code, n, distinct in rows(
            con,
            """
            select code, count(*), count(distinct (meeting_id, cadastro_id))
            from plenary_attendance where legislature = 'XVII' and code in ('FA', 'QV')
            group by 1
            """,
        )
    }
    assert xvii.keys() == {"FA", "QV"}
    assert all(n == distinct for n, distinct in xvii.values())
    absences = [
        r["code"]
        for r in seed()
        if r["category"] in {"pending", "unjustified", "justified", "missed_quorum_vote"}
    ]
    assert sorted(absences) == ["FA", "FAJ", "FI", "FIJ", "FJ", "QV", "QVJ"]
    [(total,)] = rows(
        con,
        """
        select count(*) from plenary_attendance
        where legislature = 'XVII' and list_contains(?, code)
        """,
        [absences],
    )
    assert total >= 1471
    since_2025 = dict(
        rows(
            con,
            """
            select code, count(*) from plenary_attendance
            where meeting_date >= date '2025-01-01' and code in ('FA', 'QV') group by 1
            """,
        )
    )
    assert since_2025 == {"FA": xvii["FA"][0] + 6, "QV": xvii["QV"][0] + 1}


@data_only
def test_xvii_fa_cutoff_follows_the_fetched_date(con):
    # source_updated is the fetched date of composicao_orgaos/XVII in sources.lock.json, and
    # no meeting is newer than it. An FA is pending while the meeting is less than
    # pending_days old on that date, unclassified after. The exact dates are checked on the
    # fixture (test_fa_cutoff_on_the_fixture).
    lock = json.loads((DATA / "_meta" / "sources.lock.json").read_text(encoding="utf-8"))
    fetched = dt.date.fromisoformat(lock["composicao_orgaos/XVII"]["fetched"])
    assert rows(
        con, "select distinct source_updated from plenary_attendance where legislature = 'XVII'"
    ) == [(fetched,)]
    [(last_meeting,)] = rows(
        con, "select max(meeting_date) from plenary_attendance where legislature = 'XVII'"
    )
    assert last_meeting <= fetched
    (days,) = [int(r["pending_days"]) for r in seed() if r["code"] == "FA"]
    cutoff = fetched - dt.timedelta(days=days)
    fa = rows(
        con,
        """
        select meeting_date, category from plenary_attendance
        where legislature = 'XVII' and code = 'FA'
        """,
    )
    assert fa
    assert {category for _, category in fa} <= {"pending", "unclassified"}
    assert [(d, c) for d, c in fa if (c == "pending") != (d > cutoff)] == []


# --- the per-deputy summary --------------------------------------------------------------------


def test_summary_categories_add_up_to_meetings(con):
    assert rows(
        con,
        """
        select count(*) from plenary_attendance_summary
        where meetings <> present + other_body_or_mission + justified + missed_quorum_vote
                          + pending + unclassified + unjustified
        """,
    ) == [(0,)]


def test_summary_meetings_match_the_rows(con):
    sql = "select coalesce(sum(meetings), 0) from plenary_attendance_summary"
    (a,) = con.execute(sql).fetchone()
    (b,) = con.execute("select count(*) from plenary_attendance").fetchone()
    assert a == b


@fixture_only
def test_fixture_summary(con):
    d = dt.date.fromisoformat
    assert rows(
        con,
        """
        select legislature, cadastro_id, group_code, is_ceremonial, meetings, present,
               other_body_or_mission, justified, missed_quorum_vote, pending, unclassified,
               unjustified, first_meeting_date, last_meeting_date
        from plenary_attendance_summary order by 1, 2, 3, 4
        """,
    ) == [
        ("XIV", 9900005, "PS", False, 1, 1, 0, 0, 0, 0, 0, 0, d("2020-06-03"), d("2020-06-03")),
        ("XVI", 9900001, "PS", False, 3, 1, 0, 1, 1, 0, 0, 0, d("2024-04-03"), d("2024-09-19")),
        ("XVI", 9900001, "PS", True, 1, 0, 1, 0, 0, 0, 0, 0, d("2024-04-04"), d("2024-04-04")),
        ("XVI", 9900002, "PSD", False, 3, 1, 1, 1, 0, 0, 0, 0, d("2024-04-03"), d("2024-09-19")),
        ("XVI", 9900002, "PSD", True, 1, 0, 0, 1, 0, 0, 0, 0, d("2024-04-04"), d("2024-04-04")),
        ("XVI", 9900003, "CH", False, 3, 0, 1, 1, 0, 1, 0, 0, d("2024-04-03"), d("2024-09-19")),
        ("XVI", 9900003, "CH", True, 1, 0, 0, 0, 0, 0, 0, 1, d("2024-04-04"), d("2024-04-04")),
        ("XVI", 9900004, "Ninsc", False, 2, 1, 0, 0, 0, 0, 1, 0, d("2024-09-18"), d("2024-09-19")),
        ("XVI", 9900004, "PSD", False, 1, 1, 0, 0, 0, 0, 0, 0, d("2024-04-03"), d("2024-04-03")),
        ("XVI", 9900004, "PSD", True, 1, 0, 1, 0, 0, 0, 0, 0, d("2024-04-04"), d("2024-04-04")),
    ]  # fmt: skip


# --- licence --------------------------------------------------------------------------------


def test_attendance_marts_are_ar_data_under_cc_by():
    for mart in MARTS:
        assert mart in release.marts()
        assert not release.ept_derived(mart)
        assert release.mart_licence(mart) == release.MARTS_LICENCE
