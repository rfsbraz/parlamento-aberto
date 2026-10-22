"""Seats per ballot list and electoral circle, as published by the SGMAI (#55).

scripts/mai_list_seats.py reads the "mandatos" columns of the MAI results workbooks into
models/seeds/ballot_list_seats.csv. The parser tests use a synthetic workbook built here;
the seed tests check the committed seed against the seats seed.
"""

import csv
import importlib.util
import io
from collections import Counter
from pathlib import Path

import openpyxl
import pytest

from parlamento_aberto.build import MODELS, build

ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "data"
SEED = MODELS / "seeds" / "ballot_list_seats.csv"

_spec = importlib.util.spec_from_file_location(
    "mai_list_seats", ROOT / "scripts" / "mai_list_seats.py"
)
mai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mai)

HEADER = [
    "código", "nome do território", "ano", "inscritos", "votantes", "% votantes", "brancos",
    "% brancos", "nulos", "% nulos", "mandatos",
    "LISTA A", "% votos", "mandatos", "LISTA B.C", "% votos", "mandatos",
]  # fmt: skip


def workbook(sheets: dict[str, list[list]]) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for title, rows in sheets.items():
        ws = wb.create_sheet(title)
        ws.append(["", "", "ELEIÇÃO PARA A ASSEMBLEIA DA REPÚBLICA <> 1-janeiro-2000"])
        ws.append(["", "", "Escrutínio provisório"])
        ws.append([])
        ws.append(HEADER)
        for r in rows:
            ws.append(r)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def row(code, name, total, a, b):
    return [code, name, 2000, 10, 5, 50.0, 0, 0.0, 0, 0.0, total, 3, 60.0, a, 2, 40.0, b]


SYNTHETIC = {
    "Distrito": [
        row("500000", "Território Nacional", 5, 3, 2),
        row("010000", "Círculo Sintético", 3, 2, 1),
        row("020000", "Outro Círculo", 2, 1, 1),
    ],
    "País": [
        row("600000", "Estrangeiro", 1, 1, 0),
        row("800000", "Europa", 1, 1, 0),
        # A country inside a circle: no seats of its own.
        row("810200", "País Sintético", None, None, None),
    ],
}


def test_parser_reads_seats_per_list_per_circle():
    circles = mai.parse(workbook(SYNTHETIC), "synthetic.xlsx")
    assert circles == {
        "010000": {
            "name": "Círculo Sintético",
            "total": 3,
            "seats": {"LISTA A": 2, "LISTA B.C": 1},
        },
        "020000": {"name": "Outro Círculo", "total": 2, "seats": {"LISTA A": 1, "LISTA B.C": 1}},
        "800000": {"name": "Europa", "total": 1, "seats": {"LISTA A": 1}},
    }


def test_parser_rejects_lists_that_do_not_add_up_to_the_circle():
    bad = {"Distrito": [row("010000", "Círculo Sintético", 4, 2, 1)]}
    with pytest.raises(mai.MaiError, match="add up to 3, not 4"):
        mai.parse(workbook(bad), "synthetic.xlsx")


def test_parser_rejects_sheets_that_disagree():
    bad = {
        "Distrito": [row("010000", "Círculo Sintético", 3, 2, 1)],
        "Global": [row("010000", "Círculo Sintético", 3, 1, 2)],
    }
    with pytest.raises(mai.MaiError, match="disagree"):
        mai.parse(workbook(bad), "synthetic.xlsx")


def test_rows_carry_the_election_and_source():
    rows = mai.rows_for("L", "2000-01-01", mai.BASE + "synthetic.xlsx", workbook(SYNTHETIC))
    assert [(r["circle_code"], r["ballot_acronym"], r["seats"]) for r in rows] == [
        ("010000", "LISTA A", 2),
        ("010000", "LISTA B.C", 1),
        ("020000", "LISTA A", 1),
        ("020000", "LISTA B.C", 1),
        ("800000", "LISTA A", 1),
    ]
    assert {(r["legislature"], r["election_date"], r["source_url"]) for r in rows} == {
        ("L", "2000-01-01", mai.BASE + "synthetic.xlsx")
    }


# --- the committed seed ----------------------------------------------------------------


def seed_rows():
    with SEED.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def seats_seed():
    with (MODELS / "seeds" / "seats.csv").open(encoding="utf-8", newline="") as f:
        return {r["legislature"]: int(r["seats"]) for r in csv.DictReader(f)}


def test_seed_columns_and_elections():
    rows = seed_rows()
    assert list(rows[0]) == mai.COLUMNS
    elections = sorted({(r["legislature"], r["election_date"], r["source_url"]) for r in rows})
    assert elections == sorted(mai.ELECTIONS)
    assert all(int(r["seats"]) > 0 for r in rows)


def test_seed_seats_add_up_to_the_seats_seed():
    total = Counter()
    for r in seed_rows():
        total[r["legislature"]] += int(r["seats"])
    seats = seats_seed()
    assert dict(total) == {leg: seats[leg] for leg in total}


def test_every_election_has_22_circles():
    circles = Counter()
    for leg, _code in {(r["legislature"], r["circle_code"]) for r in seed_rows()}:
        circles[leg] += 1
    assert set(circles.values()) == {22}


def test_seed_rows_are_unique():
    keys = [(r["legislature"], r["circle_code"], r["ballot_acronym"]) for r in seed_rows()]
    assert len(keys) == len(set(keys))


def test_2025_split_matches_the_result():
    # XVII: AD 91 (88 on the PSD/CDS list and 3 on the Açores list with PPM).
    total = Counter()
    for r in seed_rows():
        if r["legislature"] == "XVII":
            total[r["ballot_acronym"]] += int(r["seats"])
    assert dict(total) == {
        "PPD/PSD.CDS-PP": 88,
        "CH": 60,
        "PS": 58,
        "IL": 9,
        "L": 6,
        "PCP-PEV": 3,
        "PPD/PSD.CDS-PP.PPM": 3,
        "B.E.": 1,
        "JPP": 1,
        "PAN": 1,
    }


def test_mart_is_the_seed():
    con = build(FIXTURES)
    assert con.sql("select count(*) from ballot_list_seats").fetchone()[0] == len(seed_rows())
    cols = [c[0] for c in con.sql("describe ballot_list_seats").fetchall()]
    assert cols == mai.COLUMNS
