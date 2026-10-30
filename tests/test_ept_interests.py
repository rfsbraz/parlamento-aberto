"""EpT staging parser (#46): fetcher output to declaration and item rows.

The fixtures under tests/fixtures/data/ept_registo_interesses are synthetic stripped
declarations, written through ept.write_json so they pass the same leak guard. NIPC values
are built at runtime (repeated digits with the check digit computed), never stored.
"""

import copy
import datetime as dt
import json
from pathlib import Path

import pytest

from parlamento_aberto import ept, ept_interests
from parlamento_aberto.build import build, load_schema

FIX = Path(__file__).parent / "fixtures" / "data"
ROOT = FIX / ept.DATASET
ACT = "2c6d9562-dea5-488b-9afe-42519c636daf"
SER = "b1f8c095-fe0c-4bb3-b493-902dc0c31232"
SOC = "9b58c917-b14c-4eed-9b3c-40c3d99d45da"
ASSOC = "cd0e811a-d9bb-49ee-b0f0-1dae0680eb22"
RANGES = [
    ("XIV", dt.date(2019, 10, 25), dt.date(2022, 3, 28)),
    ("XV", dt.date(2022, 3, 29), dt.date(2024, 3, 25)),
    ("XVI", dt.date(2024, 3, 26), dt.date(2025, 6, 2)),
    ("XVII", dt.date(2025, 6, 3), None),
]


def with_check(base8: str) -> str:
    total = sum(int(d) * w for d, w in zip(base8, range(9, 1, -1), strict=True))
    r = total % 11
    return base8 + str(0 if r < 2 else 11 - r)


def load(i: int, entity: int) -> dict:
    return json.loads((ROOT / str(entity) / "0" / f"{i}.json").read_text())


def parse(rec, ranges=RANGES):
    return ept_interests.parse_declaration(rec, ranges, "ept_registo_interesses/x.json")


# One declaration, in the shape of the unified rows in #42 (example.md)


def test_declaration_row_matches_the_unified_shape():
    decl, _ = parse(load(902, 4508))
    assert {k: decl[k] for k in ept_interests.EXAMPLE_DECLARATION_KEYS} == {
        "declaration_key": "ept:902",
        "source": "ept",
        "source_format": "EPT",
        "source_declaration_id": 902,
        "ept_holder_id": 7001,
        "legislature": "XVII",
        "position": "Deputada",
        "position_start_date": "2025-06-03",
        "position_end_date": None,
        "position_changed_date": None,
        "declaration_nature": "replace",
        "declaration_state": "published",
        "supersedes_declaration_id": 901,
        "submitted_at": "2026-01-30T12:19:04.5",
        "is_exclusive": None,
        "version_date": None,
        "items": 5,
    }
    # The existing XI to XV staging columns are all there.
    assert set(ept_interests.AR_DECLARATION_COLUMNS) <= set(decl)
    assert decl["format_version"] == "EPT" and decl["declaration_id"] == 902
    assert decl["position_start_raw"] == "2025-06-03T13:42:00"
    assert decl["ept_entity_id"] == 4508 and decl["ept_role_id"] == 232


def test_item_rows_match_the_unified_shape():
    _, items = parse(load(902, 4508))
    assert [i["category"] for i in items] == ["activity"] * 4 + ["service"]
    first = items[0]
    assert {k: first[k] for k in ept_interests.EXAMPLE_ITEM_KEYS} == {
        "declaration_key": "ept:902",
        "item_number": 1,
        "legislature": "XVII",
        "source": "ept",
        "category": "activity",
        "source_list": "Atividades profissionais, cargos públicos, privados e sociais",
        "item_id": None,
        "type_code": None,
        "description": "Presidente sintético",
        "entity": "Fundação sintética",
        "activity_area": "Cultura sintética",
        "location": "Localidade sintética",
        "paid_raw": "1",
        "is_paid": None,
        "start_date": "2021-03-01",
        "start_date_raw": "2021-03-01T00:00:00Z",
        "end_date": "2025-06-02",
        "end_date_raw": "2025-06-01T23:00:00Z",
    }
    assert items[1]["start_date"] == "2001-09-01"
    assert items[2]["description"] == "Conselheira sintética"  # trimmed like the AR parser
    assert items[2]["end_date"] is None and items[2]["end_date_raw"] is None
    svc = items[4]
    assert svc["source_list"] == "Serviços prestados"
    assert svc["is_professional_secrecy"] is False
    assert svc["end_date"] == "2025-06-02" and svc["paid_raw"] is None
    assert set(ept_interests.AR_ITEM_COLUMNS) <= set(svc)
    assert [i["item_number"] for i in items] == [1, 2, 3, 4, 5]


def test_society_support_and_other_fields():
    _, items = parse(load(502, 510))
    by = {i["category"]: i for i in items}
    assert set(by) == {"activity", "support", "society", "other_situation"}
    soc = by["society"]
    assert soc["entity"] == "Sociedade sintética, Lda" and soc["nature"] == "Quotas"
    assert soc["share_value_eur"] == "5000" and soc["share_pct"] == "10"
    assert soc["share_holder"] == "Próprio" and soc["share"] is None
    sup = by["support"]
    assert sup["nature"] == "Natureza sintética" and sup["beneficiary"] == "Próprio"
    assert sup["start_date"] == "2023-12-31"  # 23:30 UTC in winter is still the 31st in Lisbon
    oth = by["other_situation"]
    assert oth["date_raw"] == "2024-10-26T23:00:00Z" and oth["paid_raw"] == "0"
    assert oth["observation"] == "Observação sintética" and oth["is_professional_secrecy"] is True


# Dates


@pytest.mark.parametrize(
    "raw, day",
    [
        ("2025-06-01T23:00:00Z", "2025-06-02"),  # summer, UTC+1
        ("2024-12-31T23:30:00Z", "2024-12-31"),  # winter, UTC+0
        ("2024-03-30T23:30:00Z", "2024-03-30"),  # the night before the clocks change
        ("2024-03-31T23:30:00Z", "2024-04-01"),  # after
        ("2025-06-03T13:42:00", "2025-06-03"),  # no zone: read as Lisbon
        ("2025-06-03T00:30:00+00:00", "2025-06-03"),
        ("2021-03-01", "2021-03-01"),
        ("", None),
        (None, None),
        ("ontem", None),
    ],
)
def test_lisbon_day(raw, day):
    assert ept_interests.lisbon_day(raw) == day


# Legislature from dates, roles


def test_legislature_comes_from_the_office_start_date_not_the_entity():
    rec = load(902, 4508)
    assert parse(rec)[0]["legislature"] == "XVII"
    rec = {**rec, "entityId": 510, "startDate": "2024-04-02T09:00:00"}
    assert parse(rec)[0]["legislature"] == "XVI"
    rec = {**rec, "startDate": "2025-06-02T23:30:00Z"}  # 3 June in Lisbon
    assert parse(rec)[0]["legislature"] == "XVII"
    rec = {**rec, "startDate": "2024-03-25T23:30:00Z"}  # still 25 March in Lisbon (UTC+0)
    assert parse(rec)[0]["legislature"] == "XV"
    assert parse(load(101, 510))[0]["legislature"] == "XIV"


def test_legislature_falls_back_to_the_submitted_date():
    rec = {**load(902, 4508), "startDate": None}
    assert parse(rec)[0]["legislature"] == "XVII"


def test_legislature_is_null_outside_every_range():
    rec = {**load(902, 4508), "startDate": "1990-01-01T00:00:00"}
    assert parse(rec)[0]["legislature"] is None


def test_only_deputy_roles_are_read(tmp_path):
    decls, items = ept_interests.read_all(FIX, RANGES)
    ids = sorted(d["source_declaration_id"] for d in decls)
    assert ids == [101, 501, 502, 901, 902]  # 503 is a Vogal
    assert ept_interests.ROLES == {8: "Deputado", 232: "Deputada"}


# Chains


def test_replaced_and_modified_chains_are_resolved():
    decls, _ = ept_interests.read_all(FIX, RANGES)
    by = {d["source_declaration_id"]: d for d in decls}
    assert by[901]["declaration_state"] == "replaced"
    assert by[901]["superseded_by_declaration_id"] == 902
    assert by[902]["superseded_by_declaration_id"] is None
    assert by[901]["chain_root_declaration_id"] == by[902]["chain_root_declaration_id"] == 901
    assert (by[901]["is_current"], by[902]["is_current"]) == (False, True)
    assert by[501]["declaration_state"] == "modified"
    assert by[502]["declaration_nature"] == "modification"
    assert by[501]["superseded_by_declaration_id"] == 502
    assert (by[501]["is_current"], by[502]["is_current"]) == (False, True)
    assert by[101]["is_current"] is True and by[101]["items"] == 0


def test_a_longer_chain_and_a_newer_unlinked_version():
    base = load(902, 4508)

    def v(i, rel, state, sub):
        return {
            **copy.deepcopy(base),
            "id": i,
            "relatedDeclarationId": rel,
            "stateType": state,
            "submitedDate": sub,
        }

    recs = [
        v(1, None, 32, "2025-07-01T10:00:00"),
        v(2, 1, 32, "2025-11-01T10:00:00"),
        v(3, 2, 8, "2026-04-01T10:00:00"),
        v(4, None, 8, "2026-05-01T10:00:00"),  # published later, not linked
    ]
    decls = ept_interests.resolve_chains([parse(r)[0] for r in recs])
    by = {d["source_declaration_id"]: d for d in decls}
    assert [by[i]["chain_root_declaration_id"] for i in (1, 2, 3, 4)] == [1, 1, 1, 4]
    assert [by[i]["superseded_by_declaration_id"] for i in (1, 2, 3, 4)] == [2, 3, None, None]
    assert [by[i]["is_current"] for i in (1, 2, 3, 4)] == [False, False, False, True]


def test_a_cycle_in_the_chain_fails():
    base = load(902, 4508)
    a = parse({**base, "id": 1, "relatedDeclarationId": 2})[0]
    b = parse({**base, "id": 2, "relatedDeclarationId": 1})[0]
    with pytest.raises(ept_interests.EptParseError, match="cycle"):
        ept_interests.resolve_chains([a, b])


# NIPC and leak guards


def test_the_nipc_column_carries_through():
    nipc = with_check("5" + "0" * 7)
    rec = load(902, 4508)
    rec["tab4"][ACT][0]["col9"] = nipc
    rec["tab4"][SER][0]["col6"] = nipc
    _, items = parse(rec)
    assert items[0]["entity_nipc"] == nipc and items[4]["entity_nipc"] == nipc
    assert items[1]["entity_nipc"] is None
    ept_interests.assert_rows_clean([], items)


@pytest.mark.parametrize("base8", ["1" + "0" * 7, "70" + "0" * 6])
def test_a_personal_range_value_in_the_input_fails(base8):
    rec = load(902, 4508)
    rec["tab4"][ACT][0]["col9"] = with_check(base8)
    with pytest.raises(ept.LeakError):
        parse(rec)


def test_a_nif_key_or_nine_digits_in_the_input_fails():
    planted = with_check("2" + "3" * 7)
    with pytest.raises(ept.LeakError):
        parse({**load(902, 4508), "nif": "x"})
    rec = load(902, 4508)
    rec["tab4"][ACT][0]["col1"] = f"Cargo {planted}"
    with pytest.raises(ept.LeakError):
        parse(rec)


def test_output_guard_allows_a_nipc_only_in_entity_nipc():
    nipc = with_check("5" + "0" * 7)
    ept_interests.assert_rows_clean([], [{"entity_nipc": nipc, "description": "x"}])
    with pytest.raises(ept.LeakError):
        ept_interests.assert_rows_clean([], [{"entity_nipc": None, "description": nipc}])
    with pytest.raises(ept.LeakError):
        ept_interests.assert_rows_clean([{"holder": nipc}], [])
    with pytest.raises(ept.LeakError):
        ept_interests.assert_rows_clean([], [{"entity_nipc": with_check("1" + "0" * 7)}])


def test_unknown_enum_or_section_fails():
    with pytest.raises(ept_interests.EptParseError, match="natureType"):
        parse({**load(902, 4508), "natureType": 3})
    with pytest.raises(ept_interests.EptParseError, match="stateType"):
        parse({**load(902, 4508), "stateType": 3})
    rec = load(902, 4508)
    rec["tab4"]["00000000-0000-4000-8000-000000000000"] = []
    with pytest.raises(ept_interests.EptParseError, match="section"):
        parse(rec)


def test_an_association_section_is_never_parsed():
    # Reg. EpT 258/2024, art. 15.º, n.º 1, al. b): memberships are not public.
    assert ASSOC not in ept_interests.SECTION_FIELDS
    rec = load(502, 510)
    rec["tab4"][ASSOC] = [{"col1": "Associado sintético", "col2": "Associação sintética"}]
    with pytest.raises((ept.LeakError, ept_interests.EptParseError)):
        parse(rec)
    rec["tab4"][ASSOC] = []
    with pytest.raises((ept.LeakError, ept_interests.EptParseError)):
        parse(rec)


def test_no_fixture_holds_the_association_section_inside_tab4():
    for f in sorted(ROOT.rglob("*.json")):
        assert ASSOC not in f.read_text(), f.name


@pytest.mark.parametrize("base8", ["8" + "1" * 7, "90" + "1" * 6, "91" + "1" * 6, "77" + "1" * 6])
def test_a_sole_trader_condominium_or_77_value_in_the_input_fails(base8):
    rec = load(902, 4508)
    rec["tab4"][ACT][0]["col9"] = with_check(base8)
    with pytest.raises(ept.LeakError):
        parse(rec)
    with pytest.raises(ept.LeakError):
        ept_interests.assert_rows_clean([], [{"entity_nipc": with_check(base8)}])


# Tabs 2 and 3 and the attachment metadata (#148)


def test_field_rows_keep_position_section_column_label_and_value():
    rows = ept_interests.parse_fields(load(902, 4508), "XVII", "ept_registo_interesses/x.json")
    assert [
        (r["field_number"], r["tab"], r["path"], r["section"], r["column_name"], r["label"])
        for r in rows
    ] == [
        (1, "tab2", "0.0", None, None, "Nome Completo"),
        (2, "tab2", "0.1", None, None, "Estado Civil"),
        (3, "tab3", "0.0.0.0", "real_estate_portugal", "col1", None),
        (4, "tab3", "0.0.0.1", "real_estate_portugal", "col5", None),
        (5, "tab3", "0.1.0.0", "financial_investments_portugal", "col2", None),
    ]
    assert [r["value"] for r in rows][1:4] == ["2", "Urbano sintético", "125000.5"]
    assert {r["declaration_key"] for r in rows} == {"ept:902"}
    assert {(r["source"], r["legislature"]) for r in rows} == {("ept", "XVII")}
    assert list(rows[0]) == list(ept_interests.FIELD_COLUMNS)


def test_attachment_rows_are_metadata_only():
    rows = ept_interests.parse_attachments(load(902, 4508), "XVII", "ept_registo_interesses/x.json")
    assert rows == [
        {
            "declaration_key": "ept:902",
            "attachment_number": 1,
            "name": "anexo-sintetico.pdf",
            "size_bytes": 2048,
            "format": "pdf",
            "section_type": "4",
            "observations": None,
            "legislature": "XVII",
            "source": "ept",
            "source_file": "ept_registo_interesses/x.json",
        }
    ]
    assert list(ept_interests.ATTACHMENT_COLUMNS) == list(rows[0])


def test_a_file_stored_before_148_gives_no_field_or_attachment_rows():
    rec = load(501, 510)
    assert "tab2" not in rec
    assert ept_interests.parse_fields(rec, "XVI", "x") == []
    assert ept_interests.parse_attachments(rec, "XVI", "x") == []


def test_a_nine_digit_value_in_tabs_2_and_3_fails(tmp_path):
    rec = load(902, 4508)
    rec["tab3"][0]["value"] = with_check("5" + "1" * 7)
    with pytest.raises(ept.LeakError):
        ept_interests.parse_fields(rec, "XVII", "x")
    with pytest.raises(ept.LeakError):
        ept_interests.assert_extra_rows_clean([{"value": with_check("2" + "1" * 7)}])


# Associations, kept apart so they can be dropped on their own (#148)


def test_association_rows_use_the_item_columns():
    rows = ept_interests.parse_associations(load(902, 4508), "XVII", "x")
    assert len(rows) == 1
    row = rows[0]
    assert list(row) == list(ept_interests.ITEM_COLUMNS)
    assert row["category"] == "association"
    assert row["source_list"] == "Filiação ou funções em entidades de natureza associativa"
    assert (row["description"], row["entity"], row["location"]) == (
        "Vogal sintético",
        "Associação Sintética",
        "Lisboa",
    )
    assert (row["paid_raw"], row["start_date"], row["entity_nipc"]) == ("0", "2025-06-03", None)
    assert (row["declaration_key"], row["item_number"], row["source"]) == ("ept:902", 1, "ept")


def test_an_association_keeps_a_company_nipc_and_fails_on_a_personal_nif():
    rec = load(902, 4508)
    rec["associations"][0]["col8"] = with_check("5" + "1" * 7)
    assert ept_interests.parse_associations(rec, "XVII", "x")[0]["entity_nipc"] == with_check(
        "5" + "1" * 7
    )
    rec["associations"][0]["col8"] = with_check("2" + "1" * 7)
    with pytest.raises(ept.LeakError):
        ept_interests.parse_associations(rec, "XVII", "x")


def test_the_items_never_hold_an_association():
    _, items = ept_interests.read_all(FIX, RANGES)
    assert "association" not in {i["category"] for i in items}


def test_no_dataset_folder_gives_empty_tables(tmp_path):
    assert ept_interests.read_all(tmp_path, RANGES) == ([], [])


# Build


@pytest.fixture(scope="module")
def con():
    return build(FIX)


def test_build_writes_both_staging_tables(con):
    decls = con.execute(
        "select source_declaration_id, legislature, is_current, items "
        "from stg_ept_registo_interesses__declarations order by 1"
    ).fetchall()
    assert decls == [
        (101, "XIV", True, 0),
        (501, "XVI", False, 1),
        (502, "XVI", True, 4),
        (901, "XVII", False, 1),
        (902, "XVII", True, 5),
    ]
    n = con.execute(
        "select count(*), count(distinct declaration_key || '-' || item_number) "
        "from stg_ept_registo_interesses__items"
    ).fetchone()
    assert n == (11, 11)
    types = dict(
        con.execute(
            "select column_name, data_type from information_schema.columns "
            "where table_name = 'stg_ept_registo_interesses__items'"
        ).fetchall()
    )
    assert types["start_date"] == "DATE" and types["is_professional_secrecy"] == "BOOLEAN"


EXTRA_TABLES = ("stg_ept_registo_interesses__fields", "stg_ept_registo_interesses__attachments")


def test_build_writes_the_association_table(con):
    assert con.execute(
        "select declaration_key, category, entity from stg_ept_registo_interesses__associations"
    ).fetchall() == [("ept:902", "association", "Associação Sintética")]


def test_build_writes_the_field_and_attachment_tables(con):
    fields = con.execute(
        "select declaration_key, tab, count(*) from stg_ept_registo_interesses__fields "
        "group by all order by all"
    ).fetchall()
    assert fields == [("ept:902", "tab2", 2), ("ept:902", "tab3", 3)]
    attachments = con.execute(
        "select declaration_key, size_bytes from stg_ept_registo_interesses__attachments"
    ).fetchall()
    assert attachments == [("ept:902", 2048)]


def test_staging_columns_match_schema_yml(con):
    schema = load_schema()
    for table in (
        "stg_ept_registo_interesses__declarations",
        "stg_ept_registo_interesses__items",
        "stg_ept_registo_interesses__associations",
        *EXTRA_TABLES,
    ):
        cols = [r[0] for r in con.execute(f"describe {table}").fetchall()]
        assert cols == list(schema[table]["columns"])


def test_built_tables_pass_the_leak_guard(con):
    for table in (
        "stg_ept_registo_interesses__declarations",
        "stg_ept_registo_interesses__items",
        "stg_ept_registo_interesses__associations",
    ):
        cur = con.execute(f"select * from {table}")
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r, strict=True)) for r in cur.fetchall()]
        ept_interests.assert_rows_clean(
            rows if table.endswith("declarations") else [],
            rows if table.endswith(("items", "associations")) else [],
        )
    for table in EXTRA_TABLES:
        cur = con.execute(f"select * from {table}")
        names = [d[0] for d in cur.description]
        ept_interests.assert_extra_rows_clean(
            [dict(zip(names, r, strict=True)) for r in cur.fetchall()]
        )


def test_fixtures_are_clean_and_synthetic():
    files = sorted(ROOT.rglob("*.json"))
    assert len(files) == 6
    for f in files:
        text = f.read_text()
        ept.assert_clean(json.loads(text))
        assert "Pessoa Sintética" in text and "nif" not in text.lower()
