"""Unified interest marts (#48): AR open data XI to XV plus EpT XVI and XVII.

Runs on the committed fixtures only. The EpT fixtures are synthetic stripped declarations
(tests/fixtures/data/ept_registo_interesses); their holder ids are not in seed_ept_holders,
so cadastro_id is tested by adding a synthetic seed row in the connection.
"""

import datetime as dt
import gzip
import json
from pathlib import Path

import duckdb
import pytest

from parlamento_aberto import ept, release
from parlamento_aberto.build import _model_sql, build, load_schema

FIXTURES = Path(__file__).parent / "fixtures" / "data"
SHA = "0123456789abcdef0123456789abcdef01234567"
AR_DECLARATION_COLUMNS = [
    "legislature",
    "declaration_key",
    "cadastro_id",
    "format_version",
    "declaration_id",
    "position",
    "position_start_date",
    "position_changed_date",
    "position_end_date",
    "position_start_raw",
    "version_date",
    "is_exclusive",
    "items",
]
AR_ITEM_COLUMNS = [
    "legislature",
    "declaration_key",
    "item_number",
    "cadastro_id",
    "category",
    "source_list",
    "item_id",
    "type_code",
    "description",
    "entity",
    "nature",
    "activity_area",
    "location",
    "share",
    "is_paid",
    "start_date",
    "end_date",
    "start_date_raw",
    "end_date_raw",
    "date_raw",
]


@pytest.fixture(scope="module")
def con():
    return build(FIXTURES)


def rows(con, sql):
    return con.sql(sql).fetchall()


def cols(con, table):
    return [c for (c, *_) in rows(con, f"describe {table}")]


def test_backward_compatible_columns_come_first(con):
    d = cols(con, "interest_declarations")
    i = cols(con, "interests")
    assert d[: len(AR_DECLARATION_COLUMNS)] == AR_DECLARATION_COLUMNS
    assert i[: len(AR_ITEM_COLUMNS)] == AR_ITEM_COLUMNS
    for c in (
        "source",
        "source_format",
        "source_declaration_id",
        "ept_holder_id",
        "declaration_nature",
        "declaration_state",
        "supersedes_declaration_id",
        "superseded_by_declaration_id",
        "chain_root_declaration_id",
        "submitted_at",
        "is_current",
    ):
        assert c in d, c
    for c in (
        "source",
        "paid_raw",
        "entity_nipc",
        "beneficiary",
        "beneficiary_company",
        "share_value_eur",
        "share_pct",
        "share_holder",
        "is_professional_secrecy",
        "observation",
    ):
        assert c in i, c
    assert d == list(load_schema()["interest_declarations"]["columns"])
    assert i == list(load_schema()["interests"]["columns"])


def test_per_source_counts_are_pinned(con):
    assert rows(
        con,
        """
        select source, legislature, source_format, count(*), sum(items)
        from interest_declarations group by all order by 1, 2, 3
        """,
    ) == [
        ("ar_open_data", "XI", "V1", 1, 4),
        ("ar_open_data", "XII", "V2", 3, 15),
        ("ar_open_data", "XIV", "V3", 1, 7),
        ("ar_open_data", "XIV", "V5", 1, 6),
        ("ar_open_data", "XV", "V5", 1, 0),
        ("ept", "XVI", "EPT", 2, 5),
        ("ept", "XVII", "EPT", 2, 6),
    ]
    assert rows(con, "select source, count(*) from interests group by 1 order by 1") == [
        ("ar_open_data", 32),
        ("ept", 11),
    ]


def test_declaration_key_is_unique_across_sources(con):
    assert (
        rows(
            con,
            "select declaration_key from interest_declarations group by 1 having count(*) > 1",
        )
        == []
    )
    assert (
        rows(
            con,
            "select declaration_key, item_number from interests group by 1, 2 having count(*) > 1",
        )
        == []
    )


def test_ept_rows_only_for_xvi_and_xvii(con):
    # Entity 510 also holds XIV and XV declarations, which the AR open data already has.
    # No cross-source dedup: the marts take EpT only where the AR has no register.
    assert rows(
        con, "select distinct legislature from interest_declarations where source = 'ept'"
    ) in ([("XVI",), ("XVII",)], [("XVII",), ("XVI",)])
    assert rows(con, "select count(*) from interests where source = 'ept' and legislature "
                     "not in ('XVI', 'XVII')") == [(0,)]  # fmt: skip


def test_ar_rows_keep_their_values(con):
    assert rows(
        con,
        """
        select source_format, source_declaration_id is not distinct from declaration_id,
               declaration_nature, is_current, ept_holder_id
        from interest_declarations where source = 'ar_open_data' group by all order by 1
        """,
    ) == [("V1", True, None, None, None), ("V2", True, None, None, None),
          ("V3", True, None, None, None), ("V5", True, None, None, None)]  # fmt: skip


def test_ept_declaration_row(con):
    (row,) = rows(
        con,
        """
        select legislature, format_version, declaration_id, position, position_start_date,
               declaration_nature, declaration_state, supersedes_declaration_id,
               superseded_by_declaration_id, chain_root_declaration_id, is_current, items,
               submitted_at, ept_holder_id
        from interest_declarations where declaration_key = 'ept:902'
        """,
    )
    assert row == (
        "XVII", "EPT", 902, "Deputada", dt.date(2025, 6, 3), "replace", "published", 901,
        None, 901, True, 5, "2026-01-30T12:19:04.5", 7001,
    )  # fmt: skip
    assert rows(
        con,
        "select is_current, superseded_by_declaration_id from interest_declarations "
        "where declaration_key = 'ept:901'",
    ) == [(False, 902)]


def test_ept_items_use_the_lisbon_day(con):
    assert rows(
        con,
        """
        select item_number, category, start_date, start_date_raw, end_date, paid_raw, is_paid
        from interests where declaration_key = 'ept:902' order by 1 limit 2
        """,
    ) == [
        (1, "activity", dt.date(2021, 3, 1), "2021-03-01T00:00:00Z", dt.date(2025, 6, 2), "1",
         None),
        (2, "activity", dt.date(2001, 9, 1), "2001-08-31T23:00:00Z", dt.date(2025, 6, 2), "1",
         None),
    ]  # fmt: skip


def test_ept_only_item_columns(con):
    (soc,) = rows(
        con,
        "select share_value_eur, share_pct, share_holder, share, nature from interests "
        "where declaration_key = 'ept:502' and category = 'society'",
    )
    assert soc == ("5000", "10", "Próprio", None, "Quotas")
    (svc,) = rows(
        con,
        "select is_professional_secrecy from interests "
        "where declaration_key = 'ept:902' and category = 'service'",
    )
    assert svc == (False,)


def test_cadastro_id_comes_from_the_crosswalk_seed(con):
    con.execute("insert into seed_ept_holders values (7001, 77, 'name')")
    try:
        for mart in ("interest_declarations", "interests"):
            con.execute(f"create temp table _{mart} as {_model_sql(mart, str(FIXTURES))}")
        got = rows(
            con,
            "select distinct cadastro_id from _interest_declarations where ept_holder_id = 7001",
        )
        assert got == [(77,)]
        assert rows(
            con,
            "select distinct cadastro_id from _interests where declaration_key = 'ept:902'",
        ) == [(77,)]
        assert rows(
            con,
            "select count(*) from _interest_declarations where source = 'ept' "
            "and ept_holder_id <> 7001 and cadastro_id is not null",
        ) == [(0,)]
    finally:
        con.execute("delete from seed_ept_holders where ept_holder_id = 7001")


def test_the_nipc_column_reaches_the_mart_and_nothing_else_has_nine_digits(con):
    cur = con.execute("select * from interests where source = 'ept'")
    names = [d[0] for d in cur.description]
    for r in cur.fetchall():
        row = dict(zip(names, r, strict=True))
        nipc = row.pop("entity_nipc")
        assert nipc is None or ept.is_company_nipc(nipc)
        ept.assert_clean({k: None if v is None else str(v) for k, v in row.items()})


# Tabs 2 and 3 and the attachment metadata (#148)

EXTRA_MARTS = (
    "interest_declaration_fields",
    "interest_declaration_attachments",
    "interest_associations",
)


def test_field_and_attachment_marts_follow_schema_and_scope(con):
    for mart in EXTRA_MARTS:
        assert cols(con, mart) == list(load_schema()[mart]["columns"]), mart
        assert cols(con, mart)[:3] == ["legislature", "declaration_key", "cadastro_id"]
    assert rows(
        con,
        "select legislature, declaration_key, tab, count(*) "
        "from interest_declaration_fields group by all order by all",
    ) == [("XVII", "ept:902", "tab2", 2), ("XVII", "ept:902", "tab3", 3)]
    assert rows(
        con,
        "select legislature, declaration_key, name, size_bytes "
        "from interest_declaration_attachments",
    ) == [("XVII", "ept:902", "anexo-sintetico.pdf", 2048)]
    assert rows(
        con,
        "select legislature, declaration_key, category, entity, entity_nipc "
        "from interest_associations",
    ) == [("XVII", "ept:902", "association", "Associação Sintética", None)]


def test_field_and_attachment_marts_have_no_nine_digits(con):
    for mart in EXTRA_MARTS:
        cur = con.execute(f"select * from {mart}")
        names = [d[0] for d in cur.description]
        for r in cur.fetchall():
            row = dict(zip(names, r, strict=True))
            assert row["source"] == "ept"
            nipc = row.pop("entity_nipc", None)
            assert nipc is None or ept.is_company_nipc(nipc)
            ept.assert_clean({k: None if v is None else str(v) for k, v in row.items()})


# Release: EpT rows stay out of the CC BY assets


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("release-ept")
    changelog = out.parent / "data-changelog-ept.md"
    changelog.write_text("# Data changelog\n\n## Unreleased\n\n- schema: first release.\n")
    assert release.main(["build", "--data", str(FIXTURES), "--out", str(out), "--sha", SHA,
                         "--date", "2026-10-20", "--changelog", str(changelog),
                         "--tags", ""]) == 0  # fmt: skip
    return out


def test_release_leaves_out_ept_rows(built):
    m = json.loads((built / "manifest.json").read_text())
    assert m["excluded_sources"]["ept"]["licence"] != "CC BY 4.0"
    assert "52/2019" in m["excluded_sources"]["ept"]["terms"]
    for mart in ("interest_declarations", "interests", *EXTRA_MARTS):
        p = built / f"{mart}.parquet"
        assert duckdb.sql(f"select count(*) from '{p}' where source = 'ept'").fetchone() == (0,)
        assert m["marts"][mart]["rows"] == duckdb.sql(f"select count(*) from '{p}'").fetchone()[0]
        with gzip.open(built / f"{mart}.csv.gz", "rt", encoding="utf-8") as f:
            text = f.read()
        assert ",ept," not in text and "ept:" not in text
    assert "XVI" not in (m["marts"]["interest_declarations"]["rows_by_legislature"] or {})


def test_release_excluded_counts_are_reported(built):
    m = json.loads((built / "manifest.json").read_text())
    assert m["excluded_sources"]["ept"]["rows"] == {
        "interest_declarations": 4,
        "interests": 11,
        "interest_declaration_fields": 5,
        "interest_declaration_attachments": 1,
        "interest_associations": 1,
    }
