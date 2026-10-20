"""Build a data release: one Parquet and one gzipped CSV per mart, the seating macros
(macros.sql), manifest.json and a CHANGELOG.md excerpt, after checking row counts against the
previous release.

python -m parlamento_aberto.release build --data data --out DIR --sha SHA --date YYYY-MM-DD
    [--changelog docs/data-changelog.md] [--previous DIR] [--tags "data-2026-10-19 ..."]

--previous holds manifest.json and CHANGELOG.md of the latest release, if there is one.
Prints tag=<tag> for $GITHUB_OUTPUT. Exits 1, writing nothing, if a mart drops more than 5%
in a legislature and the drop is not acknowledged in the changelog (see drift()).
"""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import duckdb
import yaml

from parlamento_aberto.build import LAYERS, MODELS, build, load_schema

ATTRIBUTION = "Fonte: Assembleia da República, dados abertos"
AR_TERMS_URL = "https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx"
# Licence split (LICENSE-DATA): CC BY 4.0 covers only our marts and the dictionary.
MARTS_LICENCE = "CC BY 4.0"
RAW_TERMS = (
    "Dados abertos da Assembleia da República reutilizados nos termos da AR, com a fonte e a "
    "data de atualização (Lei n.º 26/2016, art. 19.º, n.º 5)"
)
EPT_TERMS = (
    "Dados da Entidade para a Transparência, fora da licença dos marts: regidos pela "
    "Lei n.º 52/2019, art. 17.º, e pelos termos da EpT; republicação pendente da resposta da EpT"
)
EPT_MODEL = re.compile(r"(?:^|_)ept_")
REPO = "https://github.com/rfsbraz/parlamento-aberto"
MAX_DROP = 0.05
# The seating rule ships as code next to the data built with it, so consumers count seats the
# same way (#78). It is code, so it carries the code licence (LICENSE), not CC BY.
MACROS = "macros.sql"
MACROS_LICENCE = "MIT"
# Sources whose rows stay in the marts but out of the published files, with the reason. The
# EpT register has no reuse authorisation yet (Lei n.º 52/2019, art. 17.º), so it is not
# covered by CC BY 4.0.
EXCLUDED_SOURCES = {
    "ept": {
        "licence": "não publicado",
        "terms": "Entidade para a Transparência, Lei n.º 52/2019, art. 17.º: sem autorização "
        "de reutilização, fora da CC BY 4.0",
    },
}
ACK = re.compile(r"^\s*[-*]\s*drift:\s*(\S+)\s+([^\s:]+)", re.MULTILINE)


def schema_version() -> str:
    raw = yaml.safe_load((MODELS / "schema.yml").read_text(encoding="utf-8"))
    return str(raw["schema_version"])


def marts() -> list[str]:
    """Published tables: the models with a SQL file in models/marts, in run order."""
    return [name for name in load_schema() if (MODELS / "marts" / f"{name}.sql").exists()]


def _reads(model: str) -> set[str]:
    """Models a staging or mart SQL file names. Python models and seeds read none here."""
    for layer in LAYERS:
        path = MODELS / layer / f"{model}.sql"
        if path.exists():
            words = set(re.findall(r"\b\w+\b", path.read_text(encoding="utf-8")))
            return {m for m in load_schema() if m in words and m != model}
    return set()


def ept_derived(model: str, reads=_reads) -> bool:
    """True if the model is, or is built from, an EpT model or seed (name with ept_)."""
    seen, todo = set(), [model]
    while todo:
        name = todo.pop()
        if EPT_MODEL.search(name):
            return True
        if name not in seen:
            seen.add(name)
            todo += reads(name)
    return False


def mart_licence(mart: str) -> str:
    return EPT_TERMS if ept_derived(mart) else MARTS_LICENCE


def next_tag(date: str, existing: list[str]) -> str:
    base = f"data-{date}"
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


def published(con: duckdb.DuckDBPyConnection, mart: str) -> str:
    """A temp view of the mart without the rows of EXCLUDED_SOURCES, and its name."""
    cols = [c[0] for c in con.execute(f"describe {mart}").fetchall()]
    view = f"_release_{mart}"
    where = ""
    if "source" in cols:
        excluded = ", ".join(f"'{k}'" for k in EXCLUDED_SOURCES)
        where = f" where source not in ({excluded})"
    con.execute(f"create or replace temp view {view} as select * from {mart}{where}")
    return view


def excluded_rows(con: duckdb.DuckDBPyConnection) -> dict:
    """Rows left out of each mart, per excluded source, for the manifest."""
    out = {}
    for source, terms in EXCLUDED_SOURCES.items():
        rows = {}
        for mart in marts():
            cols = [c[0] for c in con.execute(f"describe {mart}").fetchall()]
            if "source" in cols:
                (n,) = con.execute(
                    f"select count(*) from {mart} where source = ?", [source]
                ).fetchone()
                if n:
                    rows[mart] = n
        out[source] = {**terms, "rows": rows}
    return out


def row_counts(con: duckdb.DuckDBPyConnection, mart: str) -> tuple[int, dict | None]:
    (total,) = con.execute(f"select count(*) from {mart}").fetchone()
    cols = [c[0] for c in con.execute(f"describe {mart}").fetchall()]
    if "legislature" not in cols:
        return total, None
    by = con.execute(f"select legislature, count(*) from {mart} group by 1 order by 1").fetchall()
    return total, {str(leg): n for leg, n in by}


def changelog_excerpt(text: str) -> str:
    """The body of the ## Unreleased section."""
    m = re.search(r"^## Unreleased[^\n]*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() + "\n" if m and m.group(1).strip() else ""


def acknowledgements(excerpt: str, previous: str | None) -> set[tuple[str, str]]:
    """(mart, legislature) from '- drift: <mart> <legislature|all>: why' lines. A line the
    previous release already carried does not count again, so an old note cannot hide a
    new drop."""
    old = set(ACK.findall(previous or ""))
    return set(ACK.findall(excerpt)) - old


def drift(previous: dict, current: dict, acknowledged: set[tuple[str, str]]) -> list[str]:
    """Drops over 5% per mart and legislature (or per mart, 'all', without one)."""
    out = []
    for mart, prev in sorted(previous.get("marts", {}).items()):
        cur = current.get("marts", {}).get(mart, {"rows": 0, "rows_by_legislature": {}})
        if prev.get("rows_by_legislature") is None:
            pairs = [("all", prev["rows"], cur.get("rows", 0))]
        else:
            now = cur.get("rows_by_legislature") or {}
            pairs = [(leg, n, now.get(leg, 0)) for leg, n in prev["rows_by_legislature"].items()]
        for leg, before, after in sorted(pairs, key=lambda p: p[0]):
            if before and after < before * (1 - MAX_DROP) and (mart, leg) not in acknowledged:
                change = (after - before) / before * 100
                out.append(f"{mart} {leg}: {before} -> {after} ({change:.1f}%)")
    return out


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv_gz(con: duckdb.DuckDBPyConnection, mart: str, path: Path, header: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        plain = Path(tmp) / "mart.csv"
        con.execute(f"copy {mart} to '{plain.as_posix()}' (format csv, header true)")
        with plain.open("rb") as src, gzip.GzipFile(path, "wb", mtime=0) as dst:
            dst.write(f"# {header}\n".encode())
            shutil.copyfileobj(src, dst)


def export(con, out: Path, tag: str, sha: str, updated: str) -> dict:
    entries = {}
    for mart in marts():
        view = published(con, mart)
        parquet = out / f"{mart}.parquet"
        con.execute(f"copy {view} to '{parquet.as_posix()}' (format parquet, compression zstd)")
        csv_gz = out / f"{mart}.csv.gz"
        licence = mart_licence(mart)
        header = (
            f"{ATTRIBUTION}, atualizados a {updated}. {licence}. "
            f"{REPO} {tag}, data commit {sha}, mart {mart}."
        )
        write_csv_gz(con, view, csv_gz, header)
        total, by = row_counts(con, view)
        entries[mart] = {
            "rows": total,
            "rows_by_legislature": by,
            "licence": licence,
            "files": {
                "parquet": {"name": parquet.name, "sha256": _sha256(parquet)},
                "csv": {"name": csv_gz.name, "sha256": _sha256(csv_gz)},
            },
        }
    return entries


def export_macros(out: Path) -> dict:
    """Copy models/macros.sql into the release, byte for byte, and describe it."""
    path = out / MACROS
    shutil.copyfile(MODELS / MACROS, path)
    return {"name": MACROS, "sha256": _sha256(path), "licence": MACROS_LICENCE}


def sources(data: Path) -> dict:
    lock = json.loads((data / "_meta" / "sources.lock.json").read_text(encoding="utf-8"))
    return {
        k: {"sha256": v.get("sha256"), "fetched": v.get("fetched")} for k, v in sorted(lock.items())
    }


def source_updated(data: Path) -> str:
    """Latest fetch date of the AR sources, the update date the AR terms ask us to cite."""
    lock = json.loads((data / "_meta" / "sources.lock.json").read_text(encoding="utf-8"))
    dates = [v["fetched"] for k, v in lock.items() if v.get("fetched") and not EPT_MODEL.match(k)]
    return max(dates)


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def cmd_build(a) -> int:
    data = Path(a.data)
    if not (data / "_meta" / "sources.lock.json").exists():
        sys.exit(f"no {data}/_meta/sources.lock.json: nothing to release")
    tag = next_tag(a.date, a.tags.split())
    excerpt = changelog_excerpt(_read(Path(a.changelog)) or "") if a.changelog else ""
    previous = (
        json.loads(_read(Path(a.previous) / "manifest.json") or "null") if a.previous else None
    )
    prev_excerpt = _read(Path(a.previous) / "CHANGELOG.md") if a.previous else None

    con = build(data)
    updated = source_updated(data)
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        manifest = {
            "tag": tag,
            "schema_version": schema_version(),
            "built_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data_commit": a.sha,
            "attribution": ATTRIBUTION,
            "source_updated": updated,
            "licence": {
                "marts": MARTS_LICENCE,
                "raw_data": RAW_TERMS,
                "ept": EPT_TERMS,
                "ar_terms": AR_TERMS_URL,
            },
            "marts": export(con, staging, tag, a.sha, updated),
            "macros": export_macros(staging),
            "sources": sources(data),
            "excluded_sources": excluded_rows(con),
        }
        if previous:
            drops = drift(previous, manifest, acknowledgements(excerpt, prev_excerpt))
            if drops:
                print("Row counts dropped over 5% against the previous release:", file=sys.stderr)
                for d in drops:
                    print(f"  {d}", file=sys.stderr)
                print("Acknowledge each with '- drift: <mart> <legislature>: why' under "
                      "## Unreleased in docs/data-changelog.md.", file=sys.stderr)  # fmt: skip
                return 1
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        (staging / "CHANGELOG.md").write_text(
            f"# {tag}\n\n{excerpt or 'No schema changes.\n'}", encoding="utf-8"
        )
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        for f in staging.iterdir():
            shutil.move(f, out / f.name)
    print(f"tag={tag}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="parlamento_aberto.release")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build the release assets into --out")
    b.add_argument("--data", default="data")
    b.add_argument("--out", required=True)
    b.add_argument("--sha", required=True, help="data commit the release is built from")
    b.add_argument("--date", required=True, help="release date, YYYY-MM-DD (Lisbon)")
    b.add_argument("--changelog", default="docs/data-changelog.md")
    b.add_argument("--previous", help="folder with the latest release's manifest and changelog")
    b.add_argument("--tags", default="", help="existing release tags, space separated")
    a = p.parse_args(argv)
    return cmd_build(a)


if __name__ == "__main__":
    sys.exit(main())
