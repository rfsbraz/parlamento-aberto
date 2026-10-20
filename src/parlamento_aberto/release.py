"""Build a data release: one Parquet and one gzipped CSV per mart, manifest.json and a
CHANGELOG.md excerpt, after checking row counts against the previous release.

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

from parlamento_aberto.build import MODELS, build, load_schema

ATTRIBUTION = "Fonte: Assembleia da República, dados abertos"
LICENCE = "CC BY 4.0"
REPO = "https://github.com/rfsbraz/parlamento-aberto"
MAX_DROP = 0.05
ACK = re.compile(r"^\s*[-*]\s*drift:\s*(\S+)\s+([^\s:]+)", re.MULTILINE)


def schema_version() -> str:
    raw = yaml.safe_load((MODELS / "schema.yml").read_text(encoding="utf-8"))
    return str(raw["schema_version"])


def marts() -> list[str]:
    """Published tables: the models with a SQL file in models/marts, in run order."""
    return [name for name in load_schema() if (MODELS / "marts" / f"{name}.sql").exists()]


def next_tag(date: str, existing: list[str]) -> str:
    base = f"data-{date}"
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


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
        plain = Path(tmp) / f"{mart}.csv"
        con.execute(f"copy {mart} to '{plain.as_posix()}' (format csv, header true)")
        with plain.open("rb") as src, gzip.GzipFile(path, "wb", mtime=0) as dst:
            dst.write(f"# {header}\n".encode())
            shutil.copyfileobj(src, dst)


def export(con, out: Path, tag: str, sha: str) -> dict:
    entries = {}
    for mart in marts():
        parquet = out / f"{mart}.parquet"
        con.execute(f"copy {mart} to '{parquet.as_posix()}' (format parquet, compression zstd)")
        csv_gz = out / f"{mart}.csv.gz"
        header = f"{ATTRIBUTION}. {LICENCE}. {REPO} {tag}, data commit {sha}, mart {mart}."
        write_csv_gz(con, mart, csv_gz, header)
        total, by = row_counts(con, mart)
        entries[mart] = {
            "rows": total,
            "rows_by_legislature": by,
            "files": {
                "parquet": {"name": parquet.name, "sha256": _sha256(parquet)},
                "csv": {"name": csv_gz.name, "sha256": _sha256(csv_gz)},
            },
        }
    return entries


def sources(data: Path) -> dict:
    lock = json.loads((data / "_meta" / "sources.lock.json").read_text(encoding="utf-8"))
    return {
        k: {"sha256": v.get("sha256"), "fetched": v.get("fetched")} for k, v in sorted(lock.items())
    }


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
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        manifest = {
            "tag": tag,
            "schema_version": schema_version(),
            "built_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data_commit": a.sha,
            "attribution": ATTRIBUTION,
            "licence": LICENCE,
            "marts": export(con, staging, tag, a.sha),
            "sources": sources(data),
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
