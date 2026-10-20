"""Data dictionary and query docs (#10).

The pages in docs/dictionary are generated from models/schema.yml and the column types of
a fixture build. PA_DATA_DIR points the type check at a full data/ folder.
"""

import gzip
import os
import re
from pathlib import Path

import duckdb
import pytest

from parlamento_aberto import dictionary
from parlamento_aberto.build import build, load_schema

ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "data"
DATA_DIR = Path(os.environ.get("PA_DATA_DIR", FIXTURES))
data_only = pytest.mark.skipif(DATA_DIR == FIXTURES, reason="needs the full data")
DOCS = ROOT / "docs" / "dictionary"
RELEASE_URL = "https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/"


@pytest.fixture(scope="module")
def con():
    return build(FIXTURES)


@pytest.fixture(scope="module")
def pages(con):
    return dictionary.render(con)


def test_marts_are_the_models_with_a_mart_sql_file():
    marts = dictionary.marts()
    assert "votes" in marts and "deputies" in marts
    assert not [m for m in marts if m.startswith(("stg_", "seed_"))]
    assert marts == [m for m in load_schema() if m in marts]


def test_every_mart_has_a_page(pages):
    assert sorted(pages) == sorted([f"{m}.md" for m in dictionary.marts()] + ["README.md"])


def test_page_has_types_descriptions_and_source_fields(pages):
    page = pages["legislatures.md"]
    assert page.startswith("# legislatures\n")
    assert "| `start_date` | DATE | First day of the legislature. |" in page
    # Built from the staging model, whose descriptions name the AR field.
    assert "stg_informacao_base__legislatures" in page
    assert "(dtini)" in page


def test_upstream_marts_and_seeds_are_listed(pages):
    page = pages["vote_group_positions.md"]
    assert "[mandates](mandates.md)" in page
    assert "seed_group_aliases" in page


def test_quirks_are_rendered(pages):
    page = pages["votes.md"]
    assert "## Known quirks" in page
    assert "old mapper" in page


def test_index_lists_every_mart_and_the_licence(pages):
    index = pages["README.md"]
    for mart in dictionary.marts():
        assert f"[{mart}]({mart}.md)" in index
    assert "CC BY 4.0" in index
    assert "Fonte: Assembleia da República, dados abertos" in index


def test_committed_dictionary_is_current(pages):
    assert dictionary.stale(DOCS, pages) == []


def test_check_reports_a_stale_page(tmp_path, pages):
    dictionary.write(tmp_path, pages)
    assert dictionary.stale(tmp_path, pages) == []
    (tmp_path / "votes.md").write_text("old\n", encoding="utf-8")
    (tmp_path / "gone.md").write_text("old\n", encoding="utf-8")
    assert dictionary.stale(tmp_path, pages) == ["gone.md", "votes.md"]


def test_cli_check_fails_on_stale_docs(tmp_path):
    assert dictionary.main(["--out", str(tmp_path), "--check"]) == 1
    assert dictionary.main(["--out", str(tmp_path)]) == 0
    assert dictionary.main(["--out", str(tmp_path), "--check"]) == 0


@data_only
def test_full_data_types_match_the_committed_pages():
    assert dictionary.stale(DOCS, dictionary.render(build(DATA_DIR))) == []


def _blocks(lang: str) -> list[str]:
    text = (ROOT / "docs" / "querying.md").read_text(encoding="utf-8")
    return re.findall(rf"```{lang}\n(.*?)```", text, flags=re.S)


@pytest.fixture(scope="module")
def fixture_release(con, tmp_path_factory):
    """The release layout from #9: <mart>.parquet and <mart>.csv.gz with one header line."""
    out = tmp_path_factory.mktemp("release")
    for mart in dictionary.marts():
        con.execute(f"copy {mart} to '{out}/{mart}.parquet' (format parquet)")
        con.execute(f"copy {mart} to '{out}/{mart}.csv' (header true)")
        body = (out / f"{mart}.csv").read_bytes()
        with gzip.open(out / f"{mart}.csv.gz", "wb") as f:
            f.write(b"# Fonte: Assembleia da Republica, dados abertos. CC BY 4.0.\n" + body)
    return out


def test_duckdb_examples_run_against_a_fixture_release(fixture_release):
    blocks = _blocks("sql")
    assert len(blocks) >= 3
    for sql in blocks:
        assert RELEASE_URL in sql
        local = sql.replace(RELEASE_URL, f"{fixture_release.as_posix()}/")
        assert duckdb.connect().sql(local).fetchall(), sql
