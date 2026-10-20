"""#28: the older RegistoBiograficoConstituinte.xml, read as XML."""

import json
from pathlib import Path

import pytest

from parlamento_aberto import sources, sync
from parlamento_aberto.fetch import Response
from parlamento_aberto.validate import validate

ROOT = Path(__file__).parent.parent
BIO_PATH = "RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb"
ITEM = "pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb"
LEGIS = "pt_ar_wsgode_objectos_DadosDeputadoLegis"


def person(cad_id, legis=("Cons",), born=True):
    rows = "".join(
        f"<{LEGIS}><legDes>{leg}</legDes><gpSigla>PS</gpSigla></{LEGIS}>" for leg in legis
    )
    birth = "<cadDtNascimento>1900-01-02</cadDtNascimento>" if born else ""
    return (
        f"<{ITEM}><cadId>{cad_id}</cadId><cadNomeCompleto>Pessoa Sintética {cad_id}"
        f"</cadNomeCompleto>{birth}<cadSexo>F</cadSexo>"
        f"<cadDeputadoLegis>{rows}</cadDeputadoLegis><cadActividadeOrgaos /></{ITEM}>"
    )


def old_xml(*people: str) -> bytes:
    """The shape of the older RegistoBiograficoConstituinte.xml, with synthetic people."""
    return (
        '<?xml version="1.0"?><RegistoBiografico '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema">'
        f"<RegistoBiograficoList>{''.join(people)}</RegistoBiograficoList>"
        "<RegistoInteressesList /></RegistoBiografico>"
    ).encode()


def xml(body: bytes) -> Response:
    return Response(200, "text/xml", body)


# Shape


def test_xml_reads_as_the_json_shape_of_the_older_files():
    body = old_xml(person(5, ("Cons", "IA")), person(6, born=False))
    v = validate(xml(body), None, BIO_PATH, "xml")
    assert v.ok and v.records == 2
    first, second = v.data["RegistoBiografico"]["RegistoBiograficoList"][ITEM]
    assert first == {
        "cadId": "5",
        "cadNomeCompleto": "Pessoa Sintética 5",
        "cadDtNascimento": "1900-01-02",
        "cadSexo": "F",
        "cadDeputadoLegis": {
            LEGIS: [{"legDes": "Cons", "gpSigla": "PS"}, {"legDes": "IA", "gpSigla": "PS"}]
        },
        "cadActividadeOrgaos": None,
    }
    # One child is an object, as in the _json.txt files.
    assert second["cadDeputadoLegis"] == {LEGIS: {"legDes": "Cons", "gpSigla": "PS"}}
    assert "cadDtNascimento" not in second
    assert v.data["RegistoBiografico"]["RegistoInteressesList"] is None


def test_a_single_person_is_one_record():
    v = validate(xml(old_xml(person(5))), None, BIO_PATH, "xml")
    assert v.ok and v.records == 1


@pytest.mark.parametrize(
    "body", [b"\xc6\xa9oz\xeb\xa2\xa25\xd0\x8a", b"<RegistoBiografico><open>", b""]
)
def test_body_that_is_not_xml_does_not_parse(body):
    v = validate(xml(body), None, BIO_PATH, "xml")
    assert not v.ok and v.reason.startswith("does not parse")


def test_json_stays_the_default():
    body = json.dumps([{"CadId": 1.0}]).encode()
    v = validate(Response(200, "application/json", body), None)
    assert v.ok and v.records == 1


# Sync


SOURCES = """
datasets:
  registo_biografico:
    layout: records
    id: CadId
    files:
      - {legislature: Constituinte, format: xml, path: "BIO", id: cadId, url: "https://ar.test/cons.xml"}
      - {legislature: XVII, url: "https://ar.test/bio-XVII"}
""".replace("BIO", BIO_PATH)


def test_format_option(tmp_path):
    (tmp_path / "sources.yaml").write_text(SOURCES)
    srcs = {s.key: s for s in sources.load(tmp_path / "sources.yaml")}
    assert srcs["registo_biografico/Constituinte"].format == "xml"
    assert srcs["registo_biografico/XVII"].format == "json"


def test_xml_source_is_stored_as_records(tmp_path):
    (tmp_path / "sources.yaml").write_text(SOURCES)
    srcs = sources.load(tmp_path / "sources.yaml")
    data = tmp_path / "data"
    routes = {
        "https://ar.test/cons.xml": xml(old_xml(person(5), person(1203))),
        "https://ar.test/bio-XVII": Response(200, "application/json", b'[{"CadId": 7.0}]'),
    }
    reports = sync.run(
        srcs,
        data,
        get=lambda u: routes[u],
        today="2026-10-20",
        fetch_kwargs={"sleep": lambda s: None},
    )
    assert {r["source"]: r["status"] for r in reports}["registo_biografico/Constituinte"] == "new"
    root = data / "registo_biografico" / "Constituinte"
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*.json")) == [
        "0/5.json",
        "1/1203.json",
    ]
    assert json.loads((root / "0" / "5.json").read_text())["cadSexo"] == "F"
    assert sync.read_lock(data)["registo_biografico/Constituinte"]["records"] == 2


# The real sources.yaml


@pytest.fixture(scope="module")
def real():
    return {s.key: s for s in sources.load(ROOT / "sources.yaml")}


def test_constituinte_biographies_come_from_the_older_xml(real):
    cons = real["registo_biografico/Constituinte"]
    assert (cons.format, cons.path, cons.id_key, cons.copy_of) == ("xml", BIO_PATH, "cadId", None)
    assert "doc.xml?" in cons.url and "&fich=RegistoBiograficoConstituinte.xml&" in cons.url
    copy = real["registo_biografico/Constituinte-xvii-copy"]
    assert (copy.format, copy.copy_of) == ("json", "XVII")
    assert "fich=RegistoBiograficoCons_json.txt" in copy.url


def test_only_that_one_file_is_read_as_xml(real):
    only = ["registo_biografico/Constituinte"]
    assert [k for k, s in real.items() if s.format == "xml"] == only
    assert [k for k, s in real.items() if "/doc.xml?" in s.url] == only
