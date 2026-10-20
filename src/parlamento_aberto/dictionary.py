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
    "Gerado a partir de `src/parlamento_aberto/models/schema.yml` por "
    "`uv run python -m parlamento_aberto.dictionary`. Não editar à mão."
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
    lines = ["| Coluna | Tipo | Descrição |", "|---|---|---|"]
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
    lines += [f"Ficheiros da publicação: `{model}.parquet` e `{model}.csv.gz`.", ""]
    lines += ["## Colunas", ""] + _columns(con, model, spec["columns"]) + [""]
    lines += ["## Particularidades conhecidas", ""]
    lines += [f"- {_text(q)}" for q in spec.get("quirks", [])]
    gaps = "[lacunas conhecidas](../known-gaps.md)"
    lines += [f"- As lacunas da própria fonte da AR estão em {gaps}.", ""]
    lines += ["## Construído a partir de", ""]
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
        "# Dicionário de dados",
        "",
        "Uma página por mart da publicação de dados, com os tipos e as descrições das colunas,",
        "as particularidades conhecidas e os modelos de staging a partir dos quais cada mart é",
        "construído. As descrições das colunas de staging indicam entre parênteses o campo da",
        "fonte da AR, por exemplo `(dtini)`.",
        "",
        GENERATED,
        "",
        "Como consultar uma publicação: [querying.md](../querying.md).",
        "",
        "## Marts",
        "",
        "| Mart | Descrição |",
        "|---|---|",
    ]
    lines += [f"| [{m}]({m}.md) | {_first_sentence(schema[m]['description'])} |" for m in marts()]
    lines += [
        "",
        "## Licença e atribuição",
        "",
        "Os dados são publicados sob CC BY 4.0 (`LICENSE-DATA`). A AR permite a reutilização",
        "livre dos seus dados abertos, desde que a fonte seja mencionada. Indique-a assim:",
        "",
        f"> {ATTRIBUTION}",
        "",
        "Termos: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx",
        "",
        "Todos os CSV de uma publicação começam com essa linha, que também consta do",
        "`manifest.json`.",
        "",
        "Biografias, datas de nascimento e registos de interesses são dados pessoais. Os marts",
        "contêm apenas o que a AR publica. Para reportar dados errados, veja o README principal.",
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
