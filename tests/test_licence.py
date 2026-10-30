"""The data licence split (LICENSE-DATA).

- Raw AR files in data/ are AR data reused under the AR's terms (Lei 26/2016, art. 19.º,
  n.º 5: cite the source and the update date). They are not ours to license.
- CC BY 4.0 covers only our derived marts and the data dictionary, crediting the AR.
- data/ept_* and anything built from EpT data are outside CC BY. They are reused citing the EpT
  (Lei 52/2019, art. 15.º, n.º 1; LADA, art. 21.º, n.º 1).

The release metadata, the CSV headers, the dictionary footer and LICENSE-DATA must say
the same thing.
"""

import gzip
import json
from pathlib import Path

import pytest

from parlamento_aberto import dictionary, release

ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "data"
SHA = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("release")
    args = ["build", "--data", str(FIXTURES), "--out", str(out), "--sha", SHA]
    assert release.main(args + ["--date", "2026-10-20", "--changelog", ""]) == 0
    return out


def lock_updated() -> str:
    lock = json.loads((FIXTURES / "_meta" / "sources.lock.json").read_text())
    return max(v["fetched"] for k, v in lock.items() if not k.startswith("ept_"))


def test_raw_and_ept_terms_never_claim_cc_by():
    assert release.MARTS_LICENCE == "CC BY 4.0"
    assert "CC BY" not in release.RAW_TERMS
    assert "Lei n.º 26/2016" in release.RAW_TERMS
    assert "CC BY" not in release.EPT_TERMS
    assert "Lei n.º 52/2019" in release.EPT_TERMS


def test_manifest_splits_the_licence(built):
    m = json.loads((built / "manifest.json").read_text())
    assert m["licence"] == {
        "marts": release.MARTS_LICENCE,
        "raw_data": release.RAW_TERMS,
        "ept": release.EPT_TERMS,
        "ar_terms": release.AR_TERMS_URL,
    }
    assert m["source_updated"] == lock_updated()
    for mart, entry in m["marts"].items():
        expected = release.EPT_TERMS if release.ept_derived(mart) else release.MARTS_LICENCE
        assert entry["licence"] == expected, mart


def test_csv_header_cites_source_update_date_and_mart_licence(built):
    for mart in release.marts():
        with gzip.open(built / f"{mart}.csv.gz", "rt", encoding="utf-8") as f:
            first = f.readline()
        attribution = release.mart_attribution(mart, lock_updated())
        assert first.startswith(f"# {attribution}."), mart
        assert release.mart_licence(mart) in first, mart


POINT_4 = (
    "4. Os lugares por lista e círculo (`ballot_list_seats`) vêm dos mapas de resultados das "
    "eleições de 1979 a 2005 publicados pela Comissão Nacional de Eleições (CNE) e dos "
    "ficheiros de resultados eleitorais de 2009 a 2025 publicados pela Secretaria-Geral do "
    "Ministério da Administração Interna (SGMAI), reutilizados ao abrigo dos artigos 19.º e "
    "21.º da Lei n.º 26/2016, de 22 de agosto. Os valores são publicados tal como a CNE e a "
    "SGMAI os divulgam, com duas exceções descritas no dicionário de dados: as siglas das "
    "listas nos mapas da CNE seguem a grafia da SGMAI (PSD passa a PPD/PSD, CDS/PP a CDS-PP e "
    "PCP/PEV a PCP-PEV), e no círculo Fora da Europa em 1983 segue-se o mapa publicado no "
    "Diário da República. A licença CC BY 4.0 aplica-se à compilação feita por este projeto e "
    "não implica qualquer aprovação da CNE ou da SGMAI. Fonte: CNE (1979 a 2005) e SGMAI "
    "(2009 a 2025), resultados das eleições para a Assembleia da República; data de descarga "
    "indicada no manifest.json."
)


def test_only_ballot_list_seats_credits_the_sgmai(built):
    # The election results are credited to the CNE and the SGMAI, not the AR (LICENSE-DATA, 4).
    assert [m for m in release.marts() if release.mai_derived(m)] == ["ballot_list_seats"]
    m = json.loads((built / "manifest.json").read_text())
    entry = m["marts"]["ballot_list_seats"]
    assert entry["attribution"].startswith(release.MAI_ATTRIBUTION)
    assert "Assembleia da República, dados abertos" not in entry["attribution"]
    text = " ".join((ROOT / "LICENSE-DATA").read_text(encoding="utf-8").split())
    assert release.MAI_ATTRIBUTION.removeprefix("Fonte: ") in text and "ballot_list_seats" in text


def test_licence_point_4_is_the_reviewed_text():
    text = " ".join((ROOT / "LICENSE-DATA").read_text(encoding="utf-8").split())
    assert POINT_4 in text
    # Point 4 is that paragraph, then the elected deputies, up to the code licence.
    after = text[text.index(POINT_4) + len(POINT_4) :].strip()
    assert after.startswith("Os deputados eleitos por lista e círculo de 1979 a 1991")


def test_only_ballot_list_elected_credits_the_dr_lists(built):
    # The elected deputies are credited to the CNE copies of the DR lists (LICENSE-DATA, 4).
    assert [m for m in release.marts() if release.elected_derived(m)] == ["ballot_list_elected"]
    m = json.loads((built / "manifest.json").read_text())
    entry = m["marts"]["ballot_list_elected"]
    assert entry["attribution"].startswith(release.ELECTED_ATTRIBUTION)
    text = " ".join((ROOT / "LICENSE-DATA").read_text(encoding="utf-8").split())
    assert release.ELECTED_ATTRIBUTION.removeprefix("Fonte: ") in text
    # That paragraph closes point 4, before the code licence.
    tail = text[text.index(POINT_4) :]
    assert tail.index("ballot_list_elected") < tail.index("Código")
    assert tail.index(release.ELECTED_ATTRIBUTION[8:]) < tail.index("Código")


def test_every_mart_has_its_download_date(built):
    m = json.loads((built / "manifest.json").read_text())
    for mart, entry in m["marts"].items():
        election = release.election_source(mart)
        if election:
            downloaded = max(f["downloaded"] for f in election[1])
            assert entry["downloaded"] == downloaded, mart
            assert entry["attribution"].endswith(f"descarregados a {downloaded}"), mart
            # The file date only when the file carries one; nothing is made up.
            assert entry["source_files"] == [
                {k: v for k, v in f.items() if k != "downloaded"} for f in election[1]
            ]
        else:
            assert entry["downloaded"] == lock_updated(), mart
            assert "source_files" not in entry, mart


def test_nothing_calls_the_sgmai_files_official_results():
    paths = [
        ROOT / "LICENSE-DATA",
        ROOT / "README.md",
        ROOT / "docs" / "data-changelog.md",
        ROOT / "docs" / "dictionary" / "README.md",
        ROOT / "docs" / "dictionary" / "ballot_list_seats.md",
        ROOT / "docs" / "dictionary" / "ballot_list_elected.md",
        release.MODELS / "schema.yml",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in ("resultados oficiais", "resultado oficial", "official results"):
            assert phrase not in text, (path.name, phrase)
        # The SGMAI and the CNE publish the files; they do not license them.
        for publisher in ("sgmai", "cne"):
            assert f"termos de reutilização da {publisher}" not in text, path.name
            assert f"licença da {publisher}" not in text, path.name


def test_ept_lineage_is_detected():
    reads = {
        "mart_a": {"stg_x"},
        "mart_b": {"stg_y"},
        "stg_y": {"stg_ept_registo_interesses__items"},
        "mart_c": {"seed_ept_holders"},
    }
    assert not release.ept_derived("mart_a", reads=lambda m: reads.get(m, set()))
    assert release.ept_derived("mart_b", reads=lambda m: reads.get(m, set()))
    assert release.ept_derived("mart_c", reads=lambda m: reads.get(m, set()))
    assert release.ept_derived("stg_ept_registo_interesses__declarations")


def test_only_the_interest_marts_are_ept_derived_and_carry_the_ept_terms(built):
    # A new EpT-derived mart fails here on purpose so its release licence is looked at again.
    ept_marts = ["interest_declarations", "interests"]
    assert [m for m in release.marts() if release.ept_derived(m)] == ept_marts
    m = json.loads((built / "manifest.json").read_text())
    assert m["excluded_sources"] == {}
    assert m["licence"]["ept"] == release.EPT_TERMS
    for mart in ept_marts:
        assert release.mart_licence(mart) == release.EPT_TERMS
        assert m["marts"][mart]["licence"] == release.EPT_TERMS
        with gzip.open(built / f"{mart}.csv.gz", "rt", encoding="utf-8") as f:
            first = f.readline()
        assert release.EPT_TERMS in first and "CC BY" not in first, mart


def test_dictionary_footer_matches_the_release_terms():
    index = dictionary.render_index()
    for text in (
        release.MARTS_LICENCE,
        release.RAW_TERMS,
        release.EPT_TERMS,
        release.AR_TERMS_URL,
        release.ATTRIBUTION,
    ):
        assert text in index, text


def test_license_data_states_the_split():
    text = (ROOT / "LICENSE-DATA").read_text()
    assert "Everything under data/" not in text
    assert "Lei n.º 26/2016" in text and "Lei n.º 52/2019" in text
    assert "data/ept_" in text
    assert "CC BY 4.0" in text and "docs/dictionary" in text


EPT_BASIS = ("Lei n.º 52/2019, art. 15.º, n.º 1", "Lei n.º 26/2016 (LADA), art. 21.º, n.º 1")
EPT_EXCLUDED = (
    "Ficam excluídos o NIF dos titulares, os dados pessoais, os rendimentos e património, "
    "as filiações associativas e os anexos"
)


def _ept_note_places() -> dict[str, str]:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Registo de interesses da EpT", 1)[1].split("\n## ", 1)[0]
    licence = (ROOT / "LICENSE-DATA").read_text(encoding="utf-8")
    point3 = licence.split("3. Dados da Entidade", 1)[1].split("\n4. ", 1)[0]
    return {
        "EPT_TERMS": release.EPT_TERMS,
        "README": section,
        "LICENSE-DATA": point3,
        "docs/sources/ept.md": (ROOT / "docs" / "sources" / "ept.md").read_text(encoding="utf-8"),
        "dictionary": dictionary.render_index(),
    }


def test_ept_note_cites_the_legal_basis_the_source_and_the_exclusions():
    # The same note everywhere it appears: the EpT as source, the legal basis for reuse and the
    # fields left out. Nothing still says it waits on the EpT.
    for place, text in _ept_note_places().items():
        flat = " ".join(text.split())
        assert "Entidade para a Transparência" in flat, place
        for basis in EPT_BASIS:
            assert basis in flat, (place, basis)
        assert EPT_EXCLUDED in flat, place
        assert "pendente" not in flat and "até a EpT responder" not in flat, place


def test_ept_docs_do_not_describe_the_api_fields_we_drop():
    # The docs say what is left out, never how the EpT's API carries it.
    for place, text in _ept_note_places().items():
        for word in ("getdeclaration", "`nif`", "resposta técnica"):
            assert word not in text, (place, word)
