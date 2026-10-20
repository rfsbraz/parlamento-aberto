"""#23: the older XML-shaped files for II and III, and the copies of XVII."""

import json
from pathlib import Path

import pytest

from parlamento_aberto import datapr, sources, sync
from parlamento_aberto.fetch import Response
from parlamento_aberto.normalise import LayoutError, normalise
from parlamento_aberto.validate import validate

ROOT = Path(__file__).parent.parent
ATV_PATH = "ArrayOfAtividadeDeputado.AtividadeDeputado"
BIO_PATH = "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb"


def old_activity(*ids):
    """The shape AR publishes in AtividadeDeputadoII_json.txt on the I page."""
    return {
        "?xml": {"@version": "1.0", "@encoding": "utf-8"},
        "ArrayOfAtividadeDeputado": {
            "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "AtividadeDeputado": [
                {"AtividadeDeputadoList": None, "deputado": {"depCadId": str(i), "legDes": "II"}}
                for i in ids
            ],
        },
    }


def old_biographies(*ids):
    """The shape of RegistoBiograficoII_json.txt on the I page."""
    return {
        "?xml": {"@version": "1.0"},
        "RegistoBiografico": {
            "RegistoBiograficoList": {
                "pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb": [
                    {"cadId": str(i), "cadSexo": "M"} for i in ids
                ]
            },
            "RegistoInteressesV1List": None,
        },
    }


def ok(data) -> Response:
    return Response(200, "application/json", json.dumps(data).encode())


# Normalise


def test_records_path_and_nested_string_id():
    files = normalise(
        old_activity(1234, 77), "records", "deputado.depCadId", {}, None, path=ATV_PATH
    )
    assert sorted(files) == ["0/77.json", "1/1234.json"]
    assert json.loads(files["1/1234.json"])["deputado"]["legDes"] == "II"


def test_records_path_with_cad_id():
    files = normalise(old_biographies(5, 6001), "records", "cadId", {}, None, path=BIO_PATH)
    assert sorted(files) == ["0/5.json", "6/6001.json"]


def test_records_path_with_a_single_record():
    # XML converted to JSON turns a one-item list into an object.
    data = old_biographies(5)
    lst = data["RegistoBiografico"]["RegistoBiograficoList"]
    lst["pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb"] = {"cadId": "5"}
    assert sorted(normalise(data, "records", "cadId", {}, None, path=BIO_PATH)) == ["0/5.json"]


def test_missing_records_path_is_a_layout_error():
    with pytest.raises(LayoutError, match="RegistoBiografico"):
        normalise({"other": []}, "records", "cadId", {}, None, path=BIO_PATH)


def test_validate_counts_records_at_the_path():
    v = validate(ok(old_activity(1, 2, 3)), None, path=ATV_PATH)
    assert v.ok and v.records == 3
    assert v.keys == ["AtividadeDeputadoList", "deputado"]


# sources.yaml options


def write_sources(tmp_path, body: str) -> list[sources.Source]:
    (tmp_path / "sources.yaml").write_text(body)
    return sources.load(tmp_path / "sources.yaml")


SOURCES = """
datasets:
  registo_biografico:
    layout: records
    id: CadId
    files:
      - {legislature: II, listed_on: I, path: "BIO", id: cadId, url: "https://ar.test/old-II"}
      - {legislature: II, part: xvii-copy, copy_of: XVII, url: "https://ar.test/bio-II"}
      - {legislature: XVII, url: "https://ar.test/bio-XVII"}
""".replace("BIO", BIO_PATH)


def test_per_file_path_id_page_and_copy(tmp_path):
    srcs = {s.key: s for s in write_sources(tmp_path, SOURCES)}
    old = srcs["registo_biografico/II"]
    assert (old.path, old.id_key, old.listed_on, old.copy_of) == (BIO_PATH, "cadId", "I", None)
    copy = srcs["registo_biografico/II-xvii-copy"]
    assert (copy.path, copy.id_key, copy.copy_of) == (None, "CadId", "XVII")
    assert srcs["registo_biografico/XVII"].listed_on is None


# Copies of XVII: fetched and hashed, never stored


def bio(*ids):
    return [{"CadId": float(i), "CadSexo": "M"} for i in ids]


def run(srcs, data, routes):
    return sync.run(
        srcs,
        data,
        get=lambda u: routes[u],
        today="2026-10-20",
        fetch_kwargs={"sleep": lambda s: None},
    )


def test_copy_of_xvii_is_hashed_not_stored(tmp_path):
    srcs = write_sources(tmp_path, SOURCES)
    data = tmp_path / "data"
    routes = {
        "https://ar.test/old-II": ok(old_biographies(5, 6)),
        "https://ar.test/bio-II": ok(bio(77, 78)),
        "https://ar.test/bio-XVII": ok(bio(77, 78, 79)),
    }
    reports = {r["source"]: r for r in run(srcs, data, routes)}
    assert reports["registo_biografico/II-xvii-copy"]["flags"] == []
    assert not (data / "registo_biografico" / "II-xvii-copy").exists()
    stored = sorted(p.name for p in (data / "registo_biografico" / "II").rglob("*.json"))
    assert stored == ["5.json", "6.json"]
    entry = sync.read_lock(data)["registo_biografico/II-xvii-copy"]
    assert entry["stored"] is False and entry["records"] == 2 and entry["sha256"]


def test_copy_is_checked_after_xvii_is_written(tmp_path):
    # The copy is listed before XVII, but XVII must be on disk to compare.
    srcs = write_sources(tmp_path, SOURCES)
    order = [s.key for s in sorted(srcs, key=sync.run_order)]
    assert order[-1] == "registo_biografico/II-xvii-copy"


def test_copy_that_differs_from_xvii_is_flagged_and_held(tmp_path):
    srcs = write_sources(tmp_path, SOURCES)
    data = tmp_path / "data"
    routes = {
        "https://ar.test/old-II": ok(old_biographies(5)),
        "https://ar.test/bio-II": ok(bio(77, 501, 502)),
        "https://ar.test/bio-XVII": ok(bio(77, 78)),
    }
    reports = {r["source"]: r for r in run(srcs, data, routes)}
    flags = reports["registo_biografico/II-xvii-copy"]["flags"]
    assert flags == ["copy differs from XVII: 2 records not in XVII"]
    assert datapr.HOLD_SOURCE_CHANGED == "hold: source-changed"
    assert datapr.HOLD_SOURCE_CHANGED in datapr.labels(list(reports.values()), "XVII")
    assert not (data / "registo_biografico" / "II-xvii-copy").exists()


def test_copy_without_a_stored_xvii_is_held(tmp_path):
    srcs = [s for s in write_sources(tmp_path, SOURCES) if s.legislature != "XVII"]
    data = tmp_path / "data"
    routes = {
        "https://ar.test/old-II": ok(old_biographies(5)),
        "https://ar.test/bio-II": ok(bio(77)),
    }
    reports = {r["source"]: r for r in run(srcs, data, routes)}
    assert reports["registo_biografico/II-xvii-copy"]["flags"] == [
        "copy not checked: no stored XVII copy"
    ]
    assert datapr.HOLD_SOURCE_CHANGED in datapr.labels(list(reports.values()), "XVII")


# The real sources.yaml


@pytest.fixture(scope="module")
def real():
    return {s.key: s for s in sources.load(ROOT / "sources.yaml")}


@pytest.mark.parametrize(
    "dataset,path,id_key",
    [
        ("atividade_deputado", ATV_PATH, "deputado.depCadId"),
        ("registo_biografico", BIO_PATH, "cadId"),
    ],
)
@pytest.mark.parametrize("leg", ["II", "III"])
def test_ii_and_iii_come_from_the_files_listed_on_the_i_page(real, dataset, path, id_key, leg):
    old = real[f"{dataset}/{leg}"]
    assert (old.listed_on, old.path, old.id_key, old.copy_of) == ("I", path, id_key, None)
    copy = real[f"{dataset}/{leg}-xvii-copy"]
    assert copy.copy_of == "XVII" and copy.path is None
    assert copy.url != old.url
    assert f"fich={dataset_file(dataset)}{leg}_json.txt" in old.url
    assert f"fich={dataset_file(dataset)}{leg}_json.txt" in copy.url


def dataset_file(dataset):
    return {"atividade_deputado": "AtividadeDeputado", "registo_biografico": "RegistoBiografico"}[
        dataset
    ]


def test_orgao_composicao_extras_stay_out(real):
    assert not [k for k, s in real.items() if s.dataset == "composicao_orgaos" and s.listed_on]


def test_only_ii_and_iii_have_copies(real):
    # Plus the Constituinte biography JSON, replaced by the older XML (#28).
    copies = sorted(k for k, s in real.items() if s.copy_of)
    assert copies == [
        "atividade_deputado/II-xvii-copy",
        "atividade_deputado/III-xvii-copy",
        "registo_biografico/Constituinte-xvii-copy",
        "registo_biografico/II-xvii-copy",
        "registo_biografico/III-xvii-copy",
    ]


# Seats seed


def test_seat_rows_match_the_ar_folder_names(real):
    import csv

    seed = ROOT / "src" / "parlamento_aberto" / "models" / "seeds" / "seats.csv"
    rows = {r["legislature"]: r for r in csv.DictReader(seed.open(encoding="utf-8"))}
    folders = {s.key.split("/")[1] for s in real.values() if s.dataset == "informacao_base"}
    assert set(rows) == folders - {"Constituinte"}
    assert (rows["I-A"]["seats"], rows["I-B"]["seats"]) == ("263", "250")
    assert rows["I-A"]["source"] == rows["I-B"]["source"]
