"""EpT holder to cadastro_id crosswalk seed (#47).

The seed maps every EpT holder who is a Deputado or Deputada at entity 4508 (XVII) or 510
(before XVII) to one AR cadastro_id, or lists them as unmatched in the overrides seed.
tests/fixtures/ept/titularidades.json is the EpT titularidade list of 20 Oct 2026 for both
entities, scrubbed to ids, roles and dates (no names). The matcher tests use made-up names.
"""

import csv
import json
import os
from pathlib import Path

import pytest

from parlamento_aberto import ept_crosswalk as xw
from parlamento_aberto.build import MODELS, build

FIXTURES = Path(__file__).parent / "fixtures" / "data"
TITULARIDADES = Path(__file__).parent / "fixtures" / "ept" / "titularidades.json"
SEED = MODELS / "seeds" / "ept_holders.csv"
OVERRIDES = MODELS / "seeds" / "ept_holder_overrides.csv"
_data = os.environ.get("PA_DATA_DIR") or os.environ.get("PARLAMENTO_DATA_DIR")
DATA = Path(_data) if _data else FIXTURES
data_only = pytest.mark.skipif(DATA.resolve() == FIXTURES.resolve(), reason="needs the full data")
NINE = "1" * 9  # built here so no 9-digit value is written in the repo


@pytest.fixture(scope="module")
def con():
    return build(DATA)


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def ept_deputies():
    """EpT holder id -> entity ids where the holder is a Deputado or Deputada."""
    out = {}
    for t in json.loads(TITULARIDADES.read_text(encoding="utf-8")):
        if t["roleId"] in xw.DEPUTY_ROLES:
            out.setdefault(t["holderId"], set()).add(t["entityId"])
    return out


# --- the committed seed ----------------------------------------------------------------


def test_seeds_load_with_integer_ids(con):
    cols = {r[0]: r[1] for r in con.sql("describe seed_ept_holders").fetchall()}
    assert cols == {"ept_holder_id": "BIGINT", "cadastro_id": "BIGINT", "match": "VARCHAR"}
    n = con.sql("select count(*), count(distinct ept_holder_id) from seed_ept_holders").fetchone()
    assert n == (len(csv_rows(SEED)), len(csv_rows(SEED)))
    o = con.sql("select count(*) from seed_ept_holder_overrides").fetchone()[0]
    assert o == len(csv_rows(OVERRIDES))


def test_fixture_has_every_ar_deputy_titularidade():
    holders = ept_deputies()
    assert len([h for h, e in holders.items() if 4508 in e]) == 263
    assert len([h for h, e in holders.items() if 510 in e]) == 427
    assert len(holders) == 506


def test_every_ept_deputy_maps_to_one_cadastro_id_or_is_unmatched(con):
    holders = ept_deputies()
    seed = con.sql("select ept_holder_id, cadastro_id, match from seed_ept_holders").fetchall()
    assert sorted(h for h, _, _ in seed) == sorted(holders)
    unmatched = {
        int(r["ept_holder_id"]) for r in csv_rows(OVERRIDES) if not r["cadastro_id"].strip()
    }
    for holder, cadastro_id, match in seed:
        if match == "unmatched":
            assert cadastro_id is None and holder in unmatched, holder
        else:
            assert match in ("name", "override") and cadastro_id is not None, holder
    assert {h for h, _, m in seed if m == "unmatched"} == unmatched


def test_overrides_are_applied_as_written():
    seed = {int(r["ept_holder_id"]): r for r in csv_rows(SEED)}
    overrides = csv_rows(OVERRIDES)
    assert overrides
    for r in overrides:
        assert r["note"].strip(), r["ept_holder_id"]
        row = seed[int(r["ept_holder_id"])]
        assert row["cadastro_id"] == r["cadastro_id"]
        assert row["match"] == ("override" if r["cadastro_id"] else "unmatched")
    assert sum(r["match"] != "name" for r in seed.values()) == len(overrides)


def test_two_holders_share_a_cadastro_id_only_across_bodies():
    # EpT can file one person under a new holder id at 4508. On 20 Oct 2026 one deputy has
    # one holder id at 510 and another at 4508; two holders at the same body is an error.
    holders = ept_deputies()
    by_cadastro = {}
    for r in csv_rows(SEED):
        if r["cadastro_id"]:
            by_cadastro.setdefault(r["cadastro_id"], []).append(int(r["ept_holder_id"]))
    shared = {c: hs for c, hs in by_cadastro.items() if len(hs) > 1}
    assert len(shared) == 1
    for hs in shared.values():
        bodies = [e for h in hs for e in holders[h]]
        assert len(bodies) == len(set(bodies)), hs


def test_xvii_holders_map_to_xvii_deputies(con):
    # Every seated XVII deputy is in the trimmed fixture, so this holds on both.
    holders = ept_deputies()
    xvii = {
        r[0]
        for r in con.sql(
            "select cadastro_id from stg_informacao_base__deputies where legislature = 'XVII'"
        ).fetchall()
    }
    seed = {int(r["ept_holder_id"]): r["cadastro_id"] for r in csv_rows(SEED)}
    missing = [h for h, e in holders.items() if 4508 in e and seed[h] and int(seed[h]) not in xvii]
    assert missing == []


@data_only
def test_every_cadastro_id_is_an_ar_deputy(con):
    missing = con.sql(
        """
        select s.ept_holder_id from seed_ept_holders s
        where s.cadastro_id is not null
          and s.cadastro_id not in (select cadastro_id from stg_informacao_base__deputies)
        """
    ).fetchall()
    assert missing == []


# --- nothing private in the seed -------------------------------------------------------


def test_seeds_and_fixture_hold_no_nif_or_nine_digit_value():
    for path in (SEED, OVERRIDES, TITULARIDADES):
        assert xw.find_leaks(path.read_text(encoding="utf-8"), path.name) == [], path.name


def test_leak_check_catches_a_nif_key_and_a_nine_digit_value():
    assert xw.find_leaks(json.dumps([{"id": 1, "nif": None}]), "a.json")
    assert xw.find_leaks(json.dumps({"x": {"holderNIF": 1}}), "a.json")
    assert xw.find_leaks("ept_holder_id,cadastro_id,nipc\n1,2,3\n", "a.csv")
    found = xw.find_leaks(f"ept_holder_id,cadastro_id,note\n1,2,ref {NINE}\n", "a.csv")
    assert found == ["a.csv line 2: 9-digit value"]
    assert NINE not in " ".join(found)
    # Longer digit runs (dates, GUID parts) are not 9-digit values.
    assert xw.find_leaks("20261020T1234567890,2025-06-03", "a.csv") == []


def test_writing_a_seed_with_a_nine_digit_value_fails(tmp_path):
    with pytest.raises(xw.CrosswalkError, match="9-digit"):
        xw.write_seed([{"ept_holder_id": int(NINE), "cadastro_id": 1, "match": "name"}], tmp_path)
    assert not (tmp_path / "ept_holders.csv").exists()


# --- the matcher, on made-up names -----------------------------------------------------


def t(holder_id, name, entity=4508, role=8, tid=None):
    return {
        "id": tid or holder_id,
        "entityId": entity,
        "roleId": role,
        "holderId": holder_id,
        "holder": name,
    }


def d(cadastro_id, name, legislature="XVII"):
    return {"cadastro_id": cadastro_id, "full_name": name, "legislature": legislature}


def test_normalised_name_ignores_case_accents_and_spacing():
    assert xw.normalise_name("  Pessoa  Sintética  DA Conceição-Ávila ") == (
        "pessoa sintetica da conceicao avila"
    )


def test_matches_on_the_normalised_name():
    rows = xw.match_holders(
        [t(1, "PESSOA SINTÉTICA UM"), t(2, "Pessoa Sintetica Dois", entity=510, role=232)],
        [d(10, "Pessoa Sintética Um"), d(20, "Pessoa Sintética Dois", "XVI")],
        {},
    )
    assert rows == [
        {"ept_holder_id": 1, "cadastro_id": 10, "match": "name"},
        {"ept_holder_id": 2, "cadastro_id": 20, "match": "name"},
    ]


def test_only_deputies_are_matched():
    rows = xw.match_holders(
        [t(1, "Pessoa Sintética Um"), t(3, "Pessoa Sintética Três", role=12)],
        [d(10, "Pessoa Sintética Um"), d(30, "Pessoa Sintética Três")],
        {},
    )
    assert [r["ept_holder_id"] for r in rows] == [1]


def test_names_are_matched_within_the_entity_legislatures():
    # Entity 510 covers XIV to XVI, so a namesake in XI is not a candidate.
    rows = xw.match_holders(
        [t(1, "Pessoa Sintética Um", entity=510)],
        [d(10, "Pessoa Sintética Um", "XI"), d(11, "Pessoa Sintética Um", "XV")],
        {},
    )
    assert rows == [{"ept_holder_id": 1, "cadastro_id": 11, "match": "name"}]
    # An XVII holder is only matched against XVII.
    with pytest.raises(xw.CrosswalkError, match="holder 1: no match"):
        xw.match_holders([t(1, "Pessoa Sintética Um")], [d(11, "Pessoa Sintética Um", "XV")], {})


def test_a_holder_at_both_entities_is_one_row():
    rows = xw.match_holders(
        [t(1, "Pessoa Sintética Um", tid=7), t(1, "Pessoa Sintética Um", entity=510, tid=8)],
        [d(10, "Pessoa Sintética Um"), d(10, "Pessoa Sintética Um", "XVI")],
        {},
    )
    assert rows == [{"ept_holder_id": 1, "cadastro_id": 10, "match": "name"}]


def test_ambiguous_and_missing_names_need_an_override():
    tits = [t(1, "Pessoa Sintética Um", entity=510), t(2, "Pessoa Sintética Dois")]
    deps = [d(10, "Pessoa Sintética Um", "XV"), d(11, "Pessoa Sintética Um", "XVI")]
    with pytest.raises(xw.CrosswalkError) as e:
        xw.match_holders(tits, deps, {})
    assert "holder 1: 2 candidates" in str(e.value)
    assert "holder 2: no match" in str(e.value)
    rows = xw.match_holders(tits, deps, {1: 11, 2: None})
    assert rows == [
        {"ept_holder_id": 1, "cadastro_id": 11, "match": "override"},
        {"ept_holder_id": 2, "cadastro_id": None, "match": "unmatched"},
    ]


def test_an_override_for_an_unknown_holder_fails():
    with pytest.raises(xw.CrosswalkError, match="holder 9: override for a holder"):
        xw.match_holders([t(1, "Pessoa Sintética Um")], [d(10, "Pessoa Sintética Um")], {9: 10})


def test_cli_regenerates_the_seed(tmp_path):
    data = tmp_path / "data"
    people = {"XVII": [(10, "Pessoa Sintética Um")], "XVI": [(20, "Pessoa Sintética Dois")]}
    for leg in ("XIV", "XV", "XVI", "XVII"):
        rows = people.get(leg, [])
        p = data / "informacao_base" / leg / "deputados.ndjson"
        p.parent.mkdir(parents=True)
        p.write_text(
            "".join(
                json.dumps({"DepCadId": float(c), "DepNomeCompleto": n}) + "\n" for c, n in rows
            ),
            encoding="utf-8",
        )
    tits = tmp_path / "t.json"
    tits.write_text(
        json.dumps(
            {
                "code": 0,
                "data": {
                    "items": [
                        t(1, "Pessoa Sintética Um"),
                        t(2, "Pessoa Sintética Dois", entity=510),
                        t(3, "Pessoa Sintética Três", entity=510),
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    seeds = tmp_path / "seeds"
    seeds.mkdir()
    (seeds / "ept_holder_overrides.csv").write_text(
        "ept_holder_id,cadastro_id,note\n3,,No AR deputy with this name.\n", encoding="utf-8"
    )
    assert xw.main(["--titularidades", str(tits), "--data", str(data), "--seeds", str(seeds)]) == 0
    assert (seeds / "ept_holders.csv").read_text(encoding="utf-8") == (
        "ept_holder_id,cadastro_id,match\n1,10,name\n2,20,name\n3,,unmatched\n"
    )
