"""README and docs (#59): internal links and anchors resolve, and no em dashes."""

import re
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
DOCS = sorted(
    [ROOT / "README.md", ROOT / "tests" / "fixtures" / "README.md"]
    + list((ROOT / "docs").rglob("*.md"))
    + [ROOT / ".github" / "pull_request_template.md"]
)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def slug(heading: str) -> str:
    """GitHub's anchor for a heading: lower case, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"[`*_]", "", heading.strip().lower())
    text = "".join(c for c in text if c in " -" or unicodedata.category(c)[0] in "LN")
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    return {slug(h) for h in re.findall(r"^#+ (.+)$", text, flags=re.M)}


def test_slug_matches_github():
    assert slug("NIPC de empresas") == "nipc-de-empresas"
    law = "Limites legais: Lei n.º 52/2019, art. 17.º"
    assert slug(law) == "limites-legais-lei-nº-522019-art-17º"
    assert slug("Separador 4: registo de interesses") == "separador-4-registo-de-interesses"


@pytest.mark.parametrize("path", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_internal_links_resolve(path):
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    broken = []
    for target in LINK.findall(text):
        if re.match(r"[a-z]+:", target):
            continue
        file, _, anchor = target.partition("#")
        dest = (path.parent / file).resolve() if file else path
        if not dest.is_relative_to(ROOT):
            continue  # a GitHub page such as ../../issues/new
        if not dest.exists():
            broken.append(target)
        elif anchor and dest.suffix == ".md" and anchor not in anchors(dest):
            broken.append(target)
    assert broken == []


@pytest.mark.parametrize("path", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_em_dashes(path):
    assert "\u2014" not in path.read_text(encoding="utf-8")
