"""I-A and I-B share one deputies list (#85).

The AR publishes the same deputados file in the I-A and I-B InformacaoBase folders, with
every situation of legislature I. mandates and group_memberships keep, for each part, only
the periods that overlap the part's own dates, with the dates as published.

The fixture tests build a copy of tests/fixtures/data with a synthetic list (Pessoa
Sintética, ids from 9900001) written to both folders. Set PARLAMENTO_DATA_DIR to a full
data/ folder to run the data checks on a real sync.
"""

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from parlamento_aberto.build import build

FIXTURES = Path(__file__).parent / "fixtures" / "data"
_data = os.environ.get("PARLAMENTO_DATA_DIR")
DATA = Path(_data) if _data else None
fixture_only = pytest.mark.skipif(DATA is not None, reason="pinned to the fixtures")
data_only = pytest.mark.skipif(DATA is None, reason="needs the full data")

PARTS = ("I-A", "I-B")
# DetalheLegislatura dates of each part, as published.
PART_DATES = {
    "I-A": {"dtfim": "1980-01-02", "dtini": "1976-06-03", "id": "32", "sigla": "I"},
    "I-B": {"dtfim": "1980-11-12", "dtini": "1980-01-03", "id": "33", "sigla": "I"},
}


def _deputy(cad, situations, groups):
    return {
        "DepCPDes": "Círculo Sintético",
        "DepCPId": 1.0,
        "DepCadId": float(cad),
        "DepGP": [
            {"gpDtFim": end, "gpDtInicio": start, "gpId": 1.0, "gpSigla": "GS"}
            for start, end in groups
        ],
        "DepId": float(cad),
        "DepNomeCompleto": f"Pessoa Sintética {cad}",
        "DepNomeParlamentar": f"Pessoa Sintética {cad}",
        "DepSituacao": [
            {"sioDes": sio, "sioDtFim": end, "sioDtInicio": start} for sio, start, end in situations
        ],
    }


# One list for legislature I, written to both folders.
SHARED_LIST = [
    # Only in I-A: ends before I-B starts.
    _deputy(9900001, [("Efetivo", "1976-06-03", "1978-08-28")], [("1976-06-03", "1978-08-28")]),
    # Only in I-B: starts after I-A ends.
    _deputy(9900002, [("Efetivo", "1980-02-01", "1980-11-12")], [("1980-02-01", "1980-11-12")]),
    # Across the change of part: in both, dates as published.
    _deputy(9900003, [("Efetivo", "1979-06-01", "1980-03-01")], [("1979-06-01", "1980-03-01")]),
    # Two periods, one per part, and a period ending on the last day of I-A.
    _deputy(
        9900004,
        [("Efetivo", "1976-06-03", "1980-01-02"), ("Suspenso(Eleito)", "1980-01-03", None)],
        [("1976-06-03", "1980-01-02"), ("1980-01-03", "1980-11-12")],
    ),
]


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("constituinte_parts")
    shutil.copytree(FIXTURES, tmp, dirs_exist_ok=True)
    for part in PARTS:
        folder = tmp / "informacao_base" / part
        folder.mkdir(parents=True, exist_ok=True)
        lines = "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in SHARED_LIST)
        (folder / "deputados.ndjson").write_text(lines, encoding="utf-8")
        (folder / "detalhe_legislatura.ndjson").write_text(
            json.dumps(PART_DATES[part]) + "\n", encoding="utf-8"
        )
    return build(tmp)


def _rows(con, mart):
    return con.sql(
        f"""
        select legislature, cadastro_id, start_date::varchar, end_date::varchar from {mart}
        where legislature in ('I-A', 'I-B') order by all
        """
    ).fetchall()


@fixture_only
def test_mandates_keep_only_periods_overlapping_the_part(con):
    assert _rows(con, "mandates") == [
        ("I-A", 9900001, "1976-06-03", "1978-08-28"),
        ("I-A", 9900003, "1979-06-01", "1980-03-01"),
        ("I-A", 9900004, "1976-06-03", "1980-01-02"),
        ("I-B", 9900002, "1980-02-01", "1980-11-12"),
        ("I-B", 9900003, "1979-06-01", "1980-03-01"),
        ("I-B", 9900004, "1980-01-03", None),
    ]


@fixture_only
def test_group_memberships_keep_only_periods_overlapping_the_part(con):
    assert _rows(con, "group_memberships") == [
        ("I-A", 9900001, "1976-06-03", "1978-08-28"),
        ("I-A", 9900003, "1979-06-01", "1980-03-01"),
        ("I-A", 9900004, "1976-06-03", "1980-01-02"),
        ("I-B", 9900002, "1980-02-01", "1980-11-12"),
        ("I-B", 9900003, "1979-06-01", "1980-03-01"),
        ("I-B", 9900004, "1980-01-03", "1980-11-12"),
    ]


@fixture_only
def test_other_legislatures_keep_every_published_period(con):
    for mart, field in (("mandates", "situations"), ("group_memberships", "groups")):
        published = con.sql(
            f"""
            select legislature, count(*) from stg_informacao_base__deputies, unnest({field})
            where legislature not in ('I-A', 'I-B') group by all order by all
            """
        ).fetchall()
        kept = con.sql(
            f"""
            select legislature, count(*) from {mart}
            where legislature not in ('I-A', 'I-B') group by all order by all
            """
        ).fetchall()
        assert published and kept == published


@data_only
def test_i_a_and_i_b_deputies_files_are_identical():
    # The rule in mandates and group_memberships relies on this. If the AR starts
    # publishing a list per part, revisit the rule.
    digests = {
        hashlib.sha256((DATA / "informacao_base" / p / "deputados.ndjson").read_bytes()).digest()
        for p in PARTS
    }
    assert len(digests) == 1


@data_only
@pytest.mark.parametrize("mart", ["mandates", "group_memberships"])
def test_no_i_a_or_i_b_row_outside_its_part_on_full_data(mart):
    con = build(DATA)
    outside, kept = con.sql(
        f"""
        select
            count(*) filter (
                where m.start_date > l.end_date or m.end_date < l.start_date
            ),
            count(*)
        from {mart} m join legislatures l using (legislature)
        where m.legislature in ('I-A', 'I-B')
        """
    ).fetchone()
    assert outside == 0
    # Both parts keep their own deputies.
    parts = con.sql(f"select distinct legislature from {mart} where legislature in ('I-A', 'I-B')")
    assert kept > 0 and sorted(r[0] for r in parts.fetchall()) == ["I-A", "I-B"]
