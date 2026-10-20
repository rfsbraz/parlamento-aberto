"""Generate the data dictionary in docs/dictionary from models/schema.yml.

One page per mart: description, columns with their DuckDB types and descriptions, known
quirks, and the staging models and seeds it is built from with their columns. Staging
column descriptions name the AR source field in parentheses, so those tables are the
source fields of the mart. Types come from a build of the committed fixtures, so the docs
regenerate in CI without the full data; a full-data test checks they are the same.

    uv run python -m parlamento_aberto.dictionary            # write docs/dictionary
    uv run python -m parlamento_aberto.dictionary --check    # fail if it is out of date
"""

import argparse
import re
import sys
from pathlib import Path

import duckdb

from parlamento_aberto.build import MODELS, build, load_schema

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "data"
OUT = ROOT / "docs" / "dictionary"
# Macros that read a mart, so a mart calling them is built from it too.
MACROS = {"seated_on": "mandates", "seated_during": "mandates"}
GENERATED = (
    "Generated from `src/parlamento_aberto/models/schema.yml` by "
    "`uv run python -m parlamento_aberto.dictionary`. Do not edit by hand."
)
ATTRIBUTION = "Fonte: Assembleia da República, dados abertos."


def marts() -> list[str]:
    """Models with a SQL file in models/marts, in run order."""
    return [m for m in load_schema() if (MODELS / "marts" / f"{m}.sql").exists()]


def _text(value) -> str:
    return " ".join(str(value).split()).replace("|", "\\|")


def _types(con: duckdb.DuckDBPyConnection, model: str) -> dict[str, str]:
    return {row[0]: row[1] for row in con.sql(f"describe {model}").fetchall()}


def _columns(con, model: str, columns: dict) -> list[str]:
    types = _types(con, model)
    lines = ["| Column | Type | Description |", "|---|---|---|"]
    for name, description in columns.items():
        lines.append(f"| `{name}` | {types[name]} | {_text(description)} |")
    return lines


def upstream(model: str, schema: dict) -> list[str]:
    """Models a mart's SQL reads, in run order."""
    sql = (MODELS / "marts" / f"{model}.sql").read_text(encoding="utf-8")
    words = set(re.findall(r"\b\w+\b", sql))
    found = {m for m in schema if m in words and m != model}
    found |= {mart for macro, mart in MACROS.items() if macro in words}
    return [m for m in schema if m in found]


def _page(con, model: str, schema: dict) -> str:
    spec = schema[model]
    lines = [f"# {model}", "", _text(spec["description"]), "", GENERATED, ""]
    lines += [f"Release files: `{model}.parquet` and `{model}.csv.gz`.", ""]
    lines += ["## Columns", ""] + _columns(con, model, spec["columns"]) + [""]
    lines += ["## Known quirks", ""]
    lines += [f"- {_text(q)}" for q in spec.get("quirks", [])]
    lines += ["- Gaps in the AR source itself are listed in [known gaps](../known-gaps.md).", ""]
    lines += ["## Built from", ""]
    sources = upstream(model, schema)
    linked = [m for m in sources if m in marts()]
    if linked:
        lines += ["Marts: " + ", ".join(f"[{m}]({m}.md)" for m in linked) + ".", ""]
    for name in sources:
        if name in linked:
            continue
        lines += [f"### {name}", "", _text(schema[name]["description"]), ""]
        lines += _columns(con, name, schema[name]["columns"]) + [""]
    return "\n".join(lines).rstrip() + "\n"


def _first_sentence(text: str) -> str:
    text = _text(text)
    end = text.find(". ")
    return text if end == -1 else text[: end + 1]


def _index(schema: dict) -> str:
    lines = [
        "# Data dictionary",
        "",
        "One page per mart in the data release, with column types and descriptions, known",
        "quirks, and the staging models each mart is built from. Staging column descriptions",
        "name the AR source field in parentheses, for example `(dtini)`.",
        "",
        GENERATED,
        "",
        "How to query a release: [querying.md](../querying.md).",
        "",
        "## Marts",
        "",
        "| Mart | Description |",
        "|---|---|",
    ]
    lines += [f"| [{m}]({m}.md) | {_first_sentence(schema[m]['description'])} |" for m in marts()]
    lines += [
        "",
        "## Licence and attribution",
        "",
        "The data is published under CC BY 4.0 (`LICENSE-DATA`). The AR allows free reuse of",
        "its open data as long as the source is credited. Credit it as:",
        "",
        f"> {ATTRIBUTION}",
        "",
        "Terms: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx",
        "",
        "Every CSV in a release starts with that line, and `manifest.json` carries it too.",
        "",
        "Biographies, birth dates and interest registers are personal data. The marts carry",
        "only what the AR publishes. See the main README to report wrong data.",
    ]
    return "\n".join(lines) + "\n"


def render(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """Every page, file name to content."""
    schema = load_schema()
    pages = {f"{m}.md": _page(con, m, schema) for m in marts()}
    pages["README.md"] = _index(schema)
    return pages


def write(out: Path, pages: dict[str, str]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.md"):
        if old.name not in pages:
            old.unlink()
    for name, text in pages.items():
        (out / name).write_text(text, encoding="utf-8")


def stale(out: Path, pages: dict[str, str]) -> list[str]:
    """Pages that differ from, are missing in or are extra in out, sorted."""
    have = {p.name: p.read_text(encoding="utf-8") for p in Path(out).glob("*.md")}
    names = set(have) | set(pages)
    return sorted(n for n in names if have.get(n) != pages.get(n))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", default=str(FIXTURES), help="data folder to build types from")
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--check", action="store_true", help="fail if the pages are stale")
    args = parser.parse_args(argv)
    con = build(args.data)
    pages = render(con)
    out = Path(args.out)
    if args.check:
        bad = stale(out, pages)
        if bad:
            print(f"{out} is out of date: {', '.join(bad)}", file=sys.stderr)
            print("Run: uv run python -m parlamento_aberto.dictionary", file=sys.stderr)
            return 1
        print(f"{out} is up to date ({len(pages)} pages).")
        return 0
    write(out, pages)
    print(f"Wrote {len(pages)} pages to {out}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
