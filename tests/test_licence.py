"""The data licence split (LICENSE-DATA).

- Raw AR files in data/ are AR data reused under the AR's terms (Lei 26/2016, art. 19.º,
  n.º 5: cite the source and the update date). They are not ours to license.
- CC BY 4.0 covers only our derived marts and the data dictionary, crediting the AR.
- data/ept_* and anything built from EpT data are outside CC BY (Lei 52/2019, art. 17.º).

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


def test_only_ballot_list_seats_credits_the_mai(built):
    # The SGMAI election results are credited to the MAI, not the AR (LICENSE-DATA, point 4).
    assert [m for m in release.marts() if release.mai_derived(m)] == ["ballot_list_seats"]
    m = json.loads((built / "manifest.json").read_text())
    entry = m["marts"]["ballot_list_seats"]
    assert entry["attribution"].startswith(release.MAI_ATTRIBUTION)
    assert "Assembleia da República" not in entry["attribution"]
    text = (ROOT / "LICENSE-DATA").read_text()
    assert release.MAI_ATTRIBUTION in text and "ballot_list_seats" in text


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


def test_only_the_interest_marts_are_ept_derived_and_their_ept_rows_stay_out_of_cc_by(built):
    # Republishing EpT data waits on the EpT's reply. A new EpT-derived mart fails here on
    # purpose so its release licence is looked at again.
    ept_marts = ["interest_declarations", "interests"]
    assert [m for m in release.marts() if release.ept_derived(m)] == ept_marts
    m = json.loads((built / "manifest.json").read_text())
    excluded = m["excluded_sources"]["ept"]
    assert sorted(excluded["rows"]) == ept_marts
    assert "CC BY" not in excluded["licence"]
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
