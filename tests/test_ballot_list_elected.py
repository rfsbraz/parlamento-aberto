"""Deputies elected per ballot list and circle, 1979 to 1991, from the CNE results PDFs (#109).

scripts/cne_elected.py reads the "relação dos deputados eleitos" in the scanned Diário da
República pages the CNE publishes, and matches each name to an AR cadastro_id. The parser and
matcher tests use synthetic text and deputies built here; the seed tests check the committed
seed against ballot_list_seats; the data tests rerun the matcher on the full InformacaoBase.
"""

import csv
import importlib.util
import json
import os
from collections import Counter
from pathlib import Path

import pytest

from parlamento_aberto.build import MODELS, build

ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "data"
_data = os.environ.get("PA_DATA_DIR") or os.environ.get("PARLAMENTO_DATA_DIR")
DATA = Path(_data) if _data else FIXTURES
data_only = pytest.mark.skipif(DATA.resolve() == FIXTURES.resolve(), reason="needs the full data")
SEEDS = MODELS / "seeds"
SEED = SEEDS / "ballot_list_elected.csv"
LEGISLATURES = ("I-B", "II", "III", "IV", "V", "VI")

_spec = importlib.util.spec_from_file_location("cne_elected", ROOT / "scripts" / "cne_elected.py")
cne = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cne)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def seed_rows() -> list[dict]:
    return read_csv(SEED)


# --- parser -------------------------------------------------------------------------------

CIRCLES = {"01": ("Aveiro", 3), "02": ("Beja", 1)}

TEXT = """\
SUMÁRIO
Nos termos do artigo 115.º da Lei n.º 14/79, a Comissão Nacional de Eleições faz publicar

1 — Círculo de Aveiro (3)

AD — Aliança Democrática (2):
Ana Maria da Silva.
João Carlos Pereira de Al-
meida.
DIÁRIO DA REPÚBLICA — I SÉRIE — N.º 1
PS — Partido Socialista (1):
Rui de A. Costa,
2 — Círculo de Beja (1)
APU — Aliança Povo Unido (1):
Maria José Cunha.
Mapa oficial 12 345 67 890
Comissão Nacional de Eleições, 1 de janeiro de 1980.
"""


def test_parser_reads_names_per_circle_and_list_in_order():
    rows = cne.parse(TEXT.splitlines(), "II", CIRCLES)
    assert [(r["circle_name"], r["ballot_acronym"], r["list_position"], r["published_name"])
            for r in rows] == [
        ("Aveiro", "AD", 1, "Ana Maria da Silva"),
        ("Aveiro", "AD", 2, "João Carlos Pereira de Almeida"),
        ("Aveiro", "PS", 1, "Rui de A. Costa"),
        ("Beja", "APU", 1, "Maria José Cunha"),
    ]  # fmt: skip
    assert {r["circle_code"] for r in rows} == {"01", "02"}


def test_parser_stops_a_list_at_its_published_count():
    text = TEXT.replace("Maria José Cunha.\n", "Maria José Cunha.\nVotantes 123 Brancos.\n")
    rows = cne.parse(text.splitlines(), "II", CIRCLES)
    assert [r["published_name"] for r in rows if r["circle_name"] == "Beja"] == ["Maria José Cunha"]


def test_parser_rejects_a_list_short_of_its_count():
    text = TEXT.replace("AD — Aliança Democrática (2):", "AD — Aliança Democrática (3):")
    with pytest.raises(cne.ElectedError, match="Aveiro AD"):
        cne.parse(text.splitlines(), "II", CIRCLES)


def test_parser_rejects_a_circle_whose_heading_disagrees_with_the_seats():
    with pytest.raises(cne.ElectedError, match="Beja"):
        cne.parse(TEXT.splitlines(), "II", {"01": ("Aveiro", 3), "02": ("Beja", 2)})


def test_list_names_take_the_ballot_list_seats_spelling():
    assert cne.list_acronym("PSD", "Partido Social Democrata", "I-B") == "PPD/PSD"
    assert cne.list_acronym("CDU", "Coligação Democrática Unitária", "V") == "CDU"
    assert cne.list_acronym("CDU", "Coligação Democrática Unitária", "VI") == "PCP-PEV"
    assert cne.list_acronym("FRS", "Frente Republicana e Socialista", "II") == "FRS"


def test_names_with_a_misread_word_are_rejected():
    assert cne.name_problems("Ana Maria da Silva") == []
    assert cne.name_problems("Rui de A. Costa") == []
    assert cne.name_problems("Georgette d'Oliveira Ferreira") == []
    assert cne.name_problems("José Augusto Bapt.s.a Lopes") != []
    assert cne.name_problems("Ana maria Silva") != []
    assert cne.name_problems("Ana Mar1a Silva") != []


def test_fixes_replace_misread_names_and_must_all_be_used():
    rows = [{"legislature": "II", "published_name": "Decmingos Abrantes"}]
    fixes = {("II", "Decmingos Abrantes"): "Domingos Abrantes"}
    assert cne.apply_fixes(rows, fixes)[0]["published_name"] == "Domingos Abrantes"
    with pytest.raises(cne.ElectedError, match="unused"):
        cne.apply_fixes(rows, {**fixes, ("III", "Ana Silva"): "Ana Silva"})


# --- matcher ------------------------------------------------------------------------------


def dep(cid, name, leg="II", circle="Aveiro", groups=("PSD",)):
    return {"cadastro_id": cid, "full_name": name, "legislature": leg, "circle": circle,
            "groups": set(groups)}  # fmt: skip


def elected(name, leg="II", circle="Aveiro", acronym="AD"):
    return {"legislature": leg, "circle_name": circle, "ballot_acronym": acronym,
            "published_name": name}  # fmt: skip


GROUPS = {("II", "AD"): {"PSD", "CDS", "PPM"}, ("II", "PS"): {"PS"}}


def match(rows, deputies, overrides=None):
    return cne.match_rows(rows, deputies, overrides or {}, GROUPS)


def test_exact_match_ignores_case_and_accents():
    out = match([elected("JOSE da Silva")], [dep(1, "José da Silva")])
    assert (out[0]["cadastro_id"], out[0]["match"]) == (1, "exact")


def test_exact_homonyms_are_narrowed_to_the_legislature():
    deps = [dep(1, "Ana Costa"), dep(2, "Ana Costa", leg="X")]
    assert match([elected("Ana Costa")], deps)[0]["cadastro_id"] == 1


def test_exact_homonyms_in_the_same_legislature_need_an_override():
    deps = [dep(1, "Ana Costa"), dep(2, "Ana Costa", circle="Beja")]
    with pytest.raises(cne.ElectedError, match="2 candidates"):
        match([elected("Ana Costa")], deps)


def test_fuzzy_match_needs_circle_group_legislature_and_first_and_last_names():
    row = elected("Rui Pena da Silva")
    good = dep(7, "Rui Eduardo Pena Silva")
    out = match([row], [good])
    assert (out[0]["cadastro_id"], out[0]["match"]) == (7, "fuzzy")
    for bad in (
        dep(7, "Rui Eduardo Pena Silva", circle="Beja"),
        dep(7, "Rui Eduardo Pena Silva", groups=("PS",)),
        dep(7, "Rui Eduardo Pena Silva", leg="III"),
        dep(7, "Rui Eduardo Pena Ramos"),
        dep(7, "Raul Eduardo Pena Silva"),
    ):
        with pytest.raises(cne.ElectedError, match="no match"):
            match([row], [bad])


def test_independents_pass_the_group_gate():
    out = match([elected("Rui Pena da Silva")], [dep(7, "Rui Pena Silva", groups=("Indep",))])
    assert out[0]["match"] == "fuzzy"


def test_overrides_win_and_an_empty_id_is_unmatched():
    rows = [elected("Ana Costa"), elected("Rui Sem Lugar")]
    overrides = {
        ("II", "Aveiro", "AD", "Ana Costa"): 9,
        ("II", "Aveiro", "AD", "Rui Sem Lugar"): None,
    }
    out = match(rows, [dep(1, "Ana Costa")], overrides)
    assert [(r["cadastro_id"], r["match"]) for r in out] == [(9, "override"), (None, "unmatched")]


def test_an_override_for_no_elected_row_fails():
    with pytest.raises(cne.ElectedError, match="no elected row"):
        match([elected("Ana Costa")], [dep(1, "Ana Costa")], {("II", "Beja", "AD", "X Y"): 1})


def test_one_deputy_cannot_be_elected_twice_in_one_election():
    rows = [elected("Ana Costa"), elected("Ana Costa", circle="Beja", acronym="PS")]
    with pytest.raises(cne.ElectedError, match="twice"):
        match(rows, [dep(1, "Ana Costa")])


def test_overrides_need_a_note(tmp_path):
    path = tmp_path / "o.csv"
    path.write_text(
        "legislature,circle_name,ballot_acronym,published_name,cadastro_id,note\n"
        "II,Aveiro,AD,Ana Costa,9,\n",
        encoding="utf-8",
    )
    with pytest.raises(cne.ElectedError, match="note"):
        cne.read_overrides(path)


# --- committed seed -----------------------------------------------------------------------


def test_seed_columns_and_legislatures():
    rows = seed_rows()
    assert list(rows[0]) == cne.COLUMNS
    assert {r["legislature"] for r in rows} == set(LEGISLATURES)


def test_every_list_has_the_seats_of_ballot_list_seats():
    seats = Counter()
    for r in read_csv(SEEDS / "ballot_list_seats.csv"):
        if r["legislature"] in LEGISLATURES:
            key = (r["legislature"], r["election_date"], r["circle_code"], r["circle_name"],
                   r["ballot_acronym"])  # fmt: skip
            seats[key] = int(r["seats"])
    got = Counter(
        (r["legislature"], r["election_date"], r["circle_code"], r["circle_name"],
         r["ballot_acronym"])
        for r in seed_rows()
    )  # fmt: skip
    assert got == seats


def test_list_positions_run_from_one():
    by_list: dict[tuple, list[int]] = {}
    for r in seed_rows():
        key = (r["legislature"], r["circle_code"], r["ballot_acronym"])
        by_list.setdefault(key, []).append(int(r["list_position"]))
    for key, positions in by_list.items():
        assert positions == list(range(1, len(positions) + 1)), key


def test_no_deputy_is_elected_twice_in_one_election():
    ids = Counter((r["legislature"], r["cadastro_id"]) for r in seed_rows() if r["cadastro_id"])
    assert [k for k, n in ids.items() if n > 1] == []


def test_match_kinds_and_null_ids_agree():
    for r in seed_rows():
        assert r["match"] in ("exact", "fuzzy", "override", "unmatched")
        assert (r["cadastro_id"] == "") == (r["match"] == "unmatched"), r


def test_every_published_name_reads_cleanly():
    bad = [(r["legislature"], r["published_name"]) for r in seed_rows()
           if cne.name_problems(r["published_name"])]  # fmt: skip
    assert bad == []


def test_every_override_is_applied_as_written():
    seed = {
        (r["legislature"], r["circle_name"], r["ballot_acronym"], r["published_name"]): r
        for r in seed_rows()
    }
    overrides = cne.read_overrides(SEEDS / "ballot_list_elected_overrides.csv")
    for key, cid in overrides.items():
        row = seed[key]
        assert row["cadastro_id"] == ("" if cid is None else str(cid)), key
        assert row["match"] == ("unmatched" if cid is None else "override"), key


def test_every_fix_is_used():
    fixes = cne.read_fixes(ROOT / "scripts" / "cne_elected_fixes.csv")
    names = {(r["legislature"], r["published_name"]) for r in seed_rows()}
    assert [k for k, v in fixes.items() if (k[0], v) not in names] == []


def test_sources_file_dates_every_pdf():
    meta = json.loads((SEEDS / "ballot_list_elected.sources.json").read_text(encoding="utf-8"))
    assert [f["url"] for f in meta["files"]] == [url for _leg, url in cne.ELECTIONS]
    assert {r["source_url"] for r in seed_rows()} == {url for _leg, url in cne.ELECTIONS}
    for f in meta["files"]:
        assert f["publisher"] == "CNE" and f["downloaded"] and f["file_modified"]


def test_mart_is_the_seed():
    con = build(FIXTURES)
    assert con.sql("select count(*) from ballot_list_elected").fetchone()[0] == len(seed_rows())
    cols = [c[0] for c in con.sql("describe ballot_list_elected").fetchall()]
    assert cols == cne.COLUMNS
    types = dict(con.sql("select column_name, data_type from (describe ballot_list_elected)")
                 .fetchall())  # fmt: skip
    assert types["cadastro_id"] == "BIGINT" and types["circle_code"] == "VARCHAR"


# --- full data ----------------------------------------------------------------------------


@data_only
def test_the_matcher_gives_the_committed_ids():
    rows = [{k: r[k] for k in ("legislature", "circle_name", "ballot_acronym", "published_name")}
            for r in seed_rows()]  # fmt: skip
    out = cne.match_rows(
        rows,
        cne.read_deputies(DATA),
        cne.read_overrides(SEEDS / "ballot_list_elected_overrides.csv"),
        cne.read_groups(SEEDS / "coalitions.csv"),
    )
    got = [("" if r["cadastro_id"] is None else str(r["cadastro_id"]), r["match"]) for r in out]
    assert got == [(r["cadastro_id"], r["match"]) for r in seed_rows()]


@data_only
def test_every_id_is_an_ar_deputy():
    known = {d["cadastro_id"] for d in cne.read_deputies(DATA)}
    ids = {int(r["cadastro_id"]) for r in seed_rows() if r["cadastro_id"]}
    overrides = cne.read_overrides(SEEDS / "ballot_list_elected_overrides.csv")
    ids |= {cid for cid in overrides.values() if cid is not None}
    assert ids - known == set()
