"""Data release (#9): assets, manifest, drift check and tag, on the fixtures."""

import csv
import gzip
import hashlib
import io
import json
import re
import shutil
from pathlib import Path

import duckdb
import pytest

from parlamento_aberto import release
from parlamento_aberto.build import MODELS, load_schema

FIXTURES = Path(__file__).parent / "fixtures" / "data"
SHA = "0123456789abcdef0123456789abcdef01234567"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("release")
    changelog = out.parent / "data-changelog.md"
    changelog.write_text("# Data changelog\n\n## Unreleased\n\n- schema: first release.\n")
    code = release.main(
        [
            "build",
            "--data", str(FIXTURES),
            "--out", str(out),
            "--sha", SHA,
            "--date", "2026-10-20",
            "--changelog", str(changelog),
            "--tags", "",
        ]
    )  # fmt: skip
    assert code == 0
    return out


def test_one_parquet_and_one_csv_per_mart(built):
    marts = release.marts()
    on_disk = sorted(p.name for p in (MODELS / "marts").glob("*.sql"))
    assert sorted(f"{m}.sql" for m in marts) == on_disk
    names = sorted(p.name for p in built.iterdir())
    expected = sorted(
        [f"{m}.parquet" for m in marts]
        + [f"{m}.csv.gz" for m in marts]
        + ["manifest.json", "CHANGELOG.md", "macros.sql"]
    )
    assert names == expected


def test_parquet_matches_the_built_mart(built):
    manifest = json.loads((built / "manifest.json").read_text())
    for mart in release.marts():
        (n,) = duckdb.sql(f"select count(*) from '{built / (mart + '.parquet')}'").fetchone()
        assert n == manifest["marts"][mart]["rows"], mart


def test_csv_has_the_attribution_header_and_every_row(built):
    manifest = json.loads((built / "manifest.json").read_text())
    for mart in release.marts():
        with gzip.open(built / f"{mart}.csv.gz", "rt", encoding="utf-8") as f:
            first = f.readline()
            body = f.read()
        assert first.startswith("# Fonte: Assembleia da República, dados abertos, atualizados a ")
        assert release.mart_licence(mart) in first and SHA in first
        rows = list(csv.reader(io.StringIO(body)))
        assert rows[0] == [c for c in load_schema()[mart]["columns"]], mart
        assert len(rows) - 1 == manifest["marts"][mart]["rows"], mart


def test_manifest(built):
    m = json.loads((built / "manifest.json").read_text())
    assert m["schema_version"] == release.schema_version()
    assert m["schema_version"].split(".")[0].isdigit()
    assert m["data_commit"] == SHA
    assert m["tag"] == "data-2026-10-20"
    assert m["built_at"].endswith("Z")
    assert m["attribution"] == "Fonte: Assembleia da República, dados abertos"
    assert m["licence"]["marts"] == "CC BY 4.0"  # the full split is in test_licence.py
    # Row counts per mart and per legislature for marts that have one.
    deputies = m["marts"]["deputies"]
    assert deputies["rows"] > 0 and deputies["rows_by_legislature"] is None
    votes = m["marts"]["votes"]
    assert sum(votes["rows_by_legislature"].values()) == votes["rows"]
    # Every file is listed with its SHA-256.
    for mart, entry in m["marts"].items():
        for kind in ("parquet", "csv"):
            f = entry["files"][kind]
            digest = hashlib.sha256((built / f["name"]).read_bytes()).hexdigest()
            assert f["sha256"] == digest, (mart, kind)
    # Every source in the lock, with its hash (null where the fixture lock leaves it out)
    # and fetch date.
    lock = json.loads((FIXTURES / "_meta" / "sources.lock.json").read_text())
    assert sorted(m["sources"]) == sorted(lock)
    for key, entry in m["sources"].items():
        assert entry == {"sha256": lock[key].get("sha256"), "fetched": lock[key]["fetched"]}


def test_macros_sql_is_published_with_its_hash(built):
    # The seating rule ships with the data it was built with, byte for byte (#78).
    source = (MODELS / "macros.sql").read_bytes()
    assert (built / "macros.sql").read_bytes() == source
    m = json.loads((built / "manifest.json").read_text())
    assert m["macros"] == {
        "name": "macros.sql",
        "sha256": hashlib.sha256(source).hexdigest(),
        "licence": "MIT",
    }


def test_published_macros_sql_runs_on_the_published_mandates(built):
    # What a consumer does: load mandates.parquet and macros.sql from the same release into
    # a fresh DuckDB and ask who is seated, with the same answer as the build.
    con = duckdb.connect()
    con.execute(f"create table mandates as select * from '{built / 'mandates.parquet'}'")
    con.execute((built / "macros.sql").read_text(encoding="utf-8"))
    (day,) = con.execute("select max(start_date) from mandates").fetchone()
    (n,) = con.execute("select count(*) from seated_on(?)", [day]).fetchone()
    assert n > 0
    ref = duckdb.connect()
    ref.execute(f"create table mandates as select * from '{built / 'mandates.parquet'}'")
    ref.execute((MODELS / "macros.sql").read_text(encoding="utf-8"))
    assert ref.execute("select count(*) from seated_on(?)", [day]).fetchone() == (n,)


def test_querying_seating_example_runs_on_a_built_release(built, capsys):
    # The Python example in docs/querying.md that checks the hash and loads macros.sql.
    text = (Path(__file__).parents[1] / "docs" / "querying.md").read_text(encoding="utf-8")
    [block] = [b for b in re.findall(r"```python\n(.*?)```", text, flags=re.S) if "macros" in b]
    url = "https://github.com/rfsbraz/parlamento-aberto/releases/latest/download/"
    assert url in block
    exec(block.replace(url, built.as_uri() + "/"), {})
    assert "count_star()" in capsys.readouterr().out


def test_changelog_excerpt(built):
    text = (built / "CHANGELOG.md").read_text()
    assert text.startswith("# data-2026-10-20")
    assert "- schema: first release." in text
    assert "## Unreleased" not in text


def manifest_with(counts):
    return {
        "marts": {m: {"rows": sum(c.values()), "rows_by_legislature": c} for m, c in counts.items()}
    }


def test_drift_blocks_a_drop_over_five_percent():
    prev = manifest_with({"votes": {"XVI": 1000, "XVII": 100}})
    assert release.drift(prev, manifest_with({"votes": {"XVI": 950, "XVII": 100}}), set()) == []
    assert release.drift(prev, manifest_with({"votes": {"XVI": 949, "XVII": 100}}), set()) == [
        "votes XVI: 1000 -> 949 (-5.1%)"
    ]
    # A legislature or a mart that disappears is a drop to zero.
    assert release.drift(prev, manifest_with({"votes": {"XVI": 1000}}), set()) == [
        "votes XVII: 100 -> 0 (-100.0%)"
    ]
    assert release.drift(prev, manifest_with({}), set()) == [
        "votes XVI: 1000 -> 0 (-100.0%)",
        "votes XVII: 100 -> 0 (-100.0%)",
    ]
    # Growth and new marts never block.
    assert (
        release.drift(prev, manifest_with({"votes": {"XVI": 2000, "XVII": 100}, "x": {}}), set())
        == []
    )


def test_drift_on_marts_without_legislature():
    prev = {"marts": {"deputies": {"rows": 100, "rows_by_legislature": None}}}
    new = {"marts": {"deputies": {"rows": 90, "rows_by_legislature": None}}}
    assert release.drift(prev, new, set()) == ["deputies all: 100 -> 90 (-10.0%)"]
    assert release.drift(prev, new, {("deputies", "all")}) == []


def test_acknowledgements_must_be_new():
    excerpt = "- drift: votes XVI: AR removed duplicated votes.\n- drift: deputies all: x\n"
    previous = "- drift: deputies all: x\n"
    assert release.acknowledgements(excerpt, previous) == {("votes", "XVI")}
    assert release.acknowledgements(excerpt, None) == {("votes", "XVI"), ("deputies", "all")}


def test_unacknowledged_drift_produces_no_release(built, tmp_path):
    prev = json.loads((built / "manifest.json").read_text())
    prev["marts"]["votes"]["rows_by_legislature"]["XVII"] *= 2
    (tmp_path / "manifest.json").write_text(json.dumps(prev))
    (tmp_path / "CHANGELOG.md").write_text("# data-2026-10-19\n")
    changelog = tmp_path / "data-changelog.md"
    changelog.write_text("## Unreleased\n\n")
    out = tmp_path / "out"
    args = [
        "build", "--data", str(FIXTURES), "--out", str(out), "--sha", SHA,
        "--date", "2026-10-20", "--changelog", str(changelog), "--tags", "data-2026-10-19",
        "--previous", str(tmp_path),
    ]  # fmt: skip
    assert release.main(args) == 1
    assert not out.exists() or not any(out.iterdir())
    # Acknowledged in the changelog, it goes through.
    changelog.write_text("## Unreleased\n\n- drift: votes XVII: test.\n")
    assert release.main(args) == 0
    assert (out / "manifest.json").exists()


def test_next_tag():
    assert release.next_tag("2026-10-20", []) == "data-2026-10-20"
    assert release.next_tag("2026-10-20", ["data-2026-10-19"]) == "data-2026-10-20"
    assert release.next_tag("2026-10-20", ["data-2026-10-20"]) == "data-2026-10-20-2"
    assert release.next_tag("2026-10-20", ["data-2026-10-20", "data-2026-10-20-2"]) == (
        "data-2026-10-20-3"
    )


def test_failing_data_tests_block_publishing():
    # The workflow runs the data tests before building, and publishes only after the build.
    text = (Path(__file__).parents[1] / ".github" / "workflows" / "data-release.yml").read_text()
    steps = [line.strip() for line in text.splitlines() if line.strip().startswith("- name:")]
    names = [s.removeprefix("- name:").strip() for s in steps]
    assert names.index("Data tests") < names.index("Build release") < names.index("Publish")


def test_no_data_means_no_release(tmp_path):
    shutil.copytree(FIXTURES, tmp_path / "data")
    (tmp_path / "data" / "_meta" / "sources.lock.json").unlink()
    with pytest.raises(SystemExit):
        release.main(["build", "--data", str(tmp_path / "data"), "--out", str(tmp_path / "o"),
                      "--sha", SHA, "--date", "2026-10-20", "--tags", ""])  # fmt: skip
