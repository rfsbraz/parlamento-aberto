"""Write models/seeds/ballot_list_elected.csv from the CNE results PDFs (#109).

For each election from 1979 to 1991 the Comissão Nacional de Eleições (CNE) publishes
resultados_ar_YEAR.pdf, a scan of the Diário da República with the "relação dos deputados
eleitos": every deputy elected, by electoral circle and ballot list, in list order. This
script reads those names as published and keeps nothing else from the pages.

The scans have no text layer. Each page is rendered at 300 dpi (pdftoppm, poppler), split
into its two columns at the gutter and read with Tesseract 5.5.0 (language por, --psm 6).
Another Tesseract version may read some names differently; the checks below then stop.

Checks, all of which stop the script:
- every list has as many names as its heading says, and every circle as many as its heading;
- every list has the seats ballot_list_seats gives it (same circles, lists and counts);
- every name reads as a name (name_problems). Misreads are corrected in
  scripts/cne_elected_fixes.csv, each checked by eye against the scan; a fix that is not
  used stops the script.

List acronyms take the ballot_list_seats spelling, from the list's name as published.

Each name is then matched to an AR cadastro_id from InformacaoBase (deputados.ndjson):
- exact: the normalised full name is one deputy's (homonyms narrowed to the legislature);
- fuzzy: one deputy of the same legislature, circle and a parliamentary group the list
  elects (coalitions seed, or Indep), with first and last names spelt alike (difflib
  ratio 0.75 per word, for Vitor/Victor or Queirós/Queiroz) and either a similar name
  (difflib ratio 0.8) or all the words of one name in the other;
- otherwise models/seeds/ballot_list_elected_overrides.csv must give the row a cadastro_id,
  or none, with a note. Overrides win over the rules. A deputy elected twice in one election
  stops the script.

It also writes models/seeds/ballot_list_elected.sources.json with, for each PDF, its
publisher, the date it was downloaded and the date the PDF says it was last saved.

Usage: uv run --with pillow python scripts/cne_elected.py [--cache DIR] [--data DIR]
"""

import argparse
import csv
import datetime as dt
import difflib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parents[1]
SEEDS = ROOT / "src" / "parlamento_aberto" / "models" / "seeds"
SEED = SEEDS / "ballot_list_elected.csv"
SOURCES = SEED.with_suffix(".sources.json")
OVERRIDES = SEEDS / "ballot_list_elected_overrides.csv"
FIXES = Path(__file__).with_name("cne_elected_fixes.csv")
LISBON = ZoneInfo("Europe/Lisbon")
CNE_DL = "https://www.cne.pt/sites/default/files/dl/"

# legislature, results PDF. 1976 (I-A) is left out: its map has no list acronyms and a
# separate correction, and ballot_list_seats has no 1976 rows to check it against.
ELECTIONS = [
    (leg, f"{CNE_DL}resultados_ar_{year}.pdf")
    for leg, year in (("I-B", 1979), ("II", 1980), ("III", 1983), ("IV", 1985), ("V", 1987),
                      ("VI", 1991))
]  # fmt: skip
COLUMNS = [
    "legislature",
    "election_date",
    "circle_code",
    "circle_name",
    "ballot_acronym",
    "list_position",
    "published_name",
    "cadastro_id",
    "match",
    "source_url",
]
TESSERACT = ["tesseract", "-", "-", "-l", "por", "--psm", "6"]


class ElectedError(ValueError):
    pass


# --- reading the scans --------------------------------------------------------------------


def _column_ink(ink, box) -> int:
    from PIL import ImageStat

    return int(ImageStat.Stat(ink.crop(box)).sum[0] // 255)


def split_page(path: Path, first: bool) -> list:
    """The two text columns of a portrait page, cut at the widest blank gutter near the middle.

    The first page opens with the full-width summary, so its columns start below the lowest
    ink in the gutter in the top 60% of the page. Landscape pages and pages with no gutter
    (the result map, in 1987 printed upright) are skipped; the circle and list counts catch a
    text page lost this way.
    """
    from PIL import Image

    im = Image.open(path).convert("L")
    w, h = im.size
    if w > h:
        return []
    ink = im.point(lambda v: 255 if v < 128 else 0)
    top, bottom = (int(h * 0.5) if first else int(h * 0.08)), int(h * 0.97)
    threshold = max(3, int((bottom - top) * 0.004))
    best, run = (0, 0), 0
    for x in range(int(w * 0.35), int(w * 0.65)):
        run = run + 1 if _column_ink(ink, (x, top, x + 1, bottom)) <= threshold else 0
        if run > best[0]:
            best = (run, x)
    gutter = best[1] - best[0] // 2
    if gutter <= 0:
        return []
    y0 = 0
    if first:
        inked = [
            y
            for y in range(int(h * 0.6))
            if _column_ink(ink, (gutter - 8, y, gutter + 8, y + 1)) > 0
        ]
        y0 = max(inked) + 5 if inked else 0
    return [im.crop((0, y0, gutter, h)), im.crop((gutter, y0, w, h))]


def ocr_pdf(data: bytes) -> list[str]:
    """Text lines of every portrait page of a scanned PDF, left column before right."""
    lines: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "in.pdf"
        pdf.write_bytes(data)
        subprocess.run(["pdftoppm", "-r", "300", "-png", pdf, Path(tmp) / "p"], check=True)
        pages = sorted(Path(tmp).glob("p-*.png"), key=lambda p: int(p.stem.split("-")[1]))
        for i, page in enumerate(pages):
            for column in split_page(page, first=i == 0):
                out = Path(tmp) / "column.png"
                column.save(out)
                text = subprocess.run(
                    TESSERACT, input=out.read_bytes(), check=True, capture_output=True
                ).stdout.decode("utf-8")
                lines += text.splitlines()
    return lines


# --- parsing the relação dos deputados eleitos --------------------------------------------

CIRCLE = re.compile(
    r"^[\W_]{0,3}\S{0,3}\s*[—\-–.]*\s*\(?[CG][íi]r[cе]u[l1iI]o\s+(?:[Ee]leitora\S*\s+)?d[aeo]s?\s+"
    r"(.+?)\s*[\(\[{](\d+)[\)\]}]"
)
LIST = re.compile(
    r"^\W*([A-Z][A-Za-z/\-\.]*(?:\s?[/\-]\s?[A-Z][A-Za-z]*)*)?\s*[—\-–]+\.?\s*"
    r"((?:Partido|Alian|Frente|Coliga|Uni|Centro).+?)\s*[\(\[{«](\S{1,3}?)[\):;]+\W*$"
)
SIGNATURE = re.compile(r"^Comiss.o Nacional de Elei..es,")
TRAILING_DEBRIS = re.compile(r"([.,])\s+\S{1,2}$")
NOISE = re.compile(r"\d|S[ÉE]RIE|DI[ÁA]RIO|^\W*$")
# Words in the list's normalised published name -> its ballot_list_seats acronym, first
# match wins.
LIST_NAMES = [
    ("republicana", "FRS"),
    ("renovador", "PRD"),
    ("solidariedade", "PSN"),
    ("unitaria", "CDU"),
    ("povo unido", "APU"),
    ("alianca democr", "AD"),
    ("social democrata", "PPD/PSD"),
    ("centro democr", "CDS"),
    ("democratica popular", "UDP"),
    ("socialista", "PS"),
]


def normalise(text: str) -> str:
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z]+", " ", s).split())


# Acronyms as printed -> the ballot_list_seats spelling, used when the name does not read.
ACRONYMS = {
    "PSD": "PPD/PSD",
    "PPD/PSD": "PPD/PSD",
    "PS": "PS",
    "CDS": "CDS",
    "PRD": "PRD",
    "APU": "APU",
    "AD": "AD",
    "FRS": "FRS",
    "UDP": "UDP",
    "PSN": "PSN",
}


def list_acronym(acronym: str | None, name: str, legislature: str) -> str:
    """The ballot_list_seats acronym of a list from its published name.

    The CDU of 1991 is PCP-PEV in the SGMAI spelling ballot_list_seats follows."""
    for words, found in LIST_NAMES:
        if words in normalise(name):
            return "PCP-PEV" if found == "CDU" and legislature == "VI" else found
    # A name the OCR garbled keeps a clean acronym, for example "Partido Social 1 'emocrata".
    if acronym in ACRONYMS:
        return ACRONYMS[acronym]
    raise ElectedError(f"{legislature}: unknown list {acronym!r} {name!r}")


def parse(lines: list[str], legislature: str, circles: dict[str, tuple[str, int]]) -> list[dict]:
    """Elected names in list order. circles: code -> (name, seats) from ballot_list_seats."""
    by_name = {normalise(name): code for code, (name, _seats) in circles.items()}
    rows: list[dict] = []
    seen: set[str] = set()
    state: dict = {"code": None, "list": None, "want": 0, "names": [], "buf": "", "lists": 0}

    def where() -> str:
        return f"{legislature} {circles[state['code']][0]} {state['list']}"

    def add_name() -> None:
        name = clean_name(state["buf"])
        state["buf"] = ""
        if name:
            state["names"].append(name)
        if len(state["names"]) == state["want"]:
            close_list()

    def close_list() -> None:
        if state["list"] is None:
            return
        if state["buf"].strip():
            add_name()
            return
        if state["want"] is not None and len(state["names"]) != state["want"]:
            n, want = len(state["names"]), state["want"]
            raise ElectedError(f"{where()}: {n} names, the heading says {want}")
        for i, name in enumerate(state["names"], 1):
            rows.append(
                {
                    "legislature": legislature,
                    "circle_code": state["code"],
                    "circle_name": circles[state["code"]][0],
                    "ballot_acronym": state["list"],
                    "list_position": i,
                    "published_name": name,
                }
            )
        state.update({"list": None, "names": [], "buf": ""})

    def close_circle() -> None:
        close_list()
        code = state["code"]
        if code is None:
            return
        got = sum(1 for r in rows if r["circle_code"] == code)
        if got != state["declared"] or got != circles[code][1]:
            raise ElectedError(
                f"{legislature} {circles[code][0]}: {got} names, the heading says "
                f"{state['declared']} and ballot_list_seats {circles[code][1]}"
            )

    for raw in lines:
        s = " ".join(raw.replace("’", "'").split())
        if state["code"] is not None and SIGNATURE.match(s):
            break
        m = CIRCLE.match(s)
        if m:
            close_circle()
            found = difflib.get_close_matches(normalise(m.group(1)), list(by_name), 1, 0.6)
            if not found:
                raise ElectedError(f"{legislature}: unknown circle {m.group(1)!r}")
            code = by_name[found[0]]
            if code in seen:
                raise ElectedError(f"{legislature}: circle {circles[code][0]} twice")
            seen.add(code)
            state.update({"code": code, "declared": int(m.group(2))})
            continue
        if state["code"] is None:
            continue
        m = LIST.match(s)
        if m:
            close_list()
            acronym = list_acronym(m.group(1), m.group(2), legislature)
            # An unreadable count, for example "(i;:", leaves the list open up to the next
            # heading; the circle total and ballot_list_seats still check it.
            want = int(m.group(3)) if m.group(3).isdigit() else None
            state.update({"list": acronym, "want": want, "names": [], "buf": ""})
            continue
        if state["list"] is None or NOISE.search(s):
            continue
        # Ink from the gutter after a name's full stop, for example "Coissoró. ]".
        s = TRAILING_DEBRIS.sub(r"\1", s)
        buf = state["buf"]
        state["buf"] = buf[:-1] + s if buf.endswith("-") else f"{buf} {s}".strip()
        if s.endswith((".", ",")):
            add_name()
    close_circle()
    missing = sorted(set(circles) - seen)
    if missing:
        raise ElectedError(f"{legislature}: no heading for circles {missing}")
    return rows


# Specks the OCR reads before a name: punctuation, or a lone lowercase letter ("o António").
LEADING_DEBRIS = re.compile(r"^(?:[^\w]+|[a-z]\s+(?=[A-ZÁÉÍÓÚÂ]))+")


def clean_name(text: str) -> str:
    return LEADING_DEBRIS.sub("", " ".join(text.split())).rstrip(".,").strip()


PARTICLES = {"da", "de", "do", "das", "dos", "e"}
UPPER = "A-ZÁÉÍÓÚÂÊÔÃÕÀÇÜ"
LOWER = "a-záéíóúâêôãõàçüïèëö"
WORD = re.compile(rf"^(?:[dD]')?[{UPPER}][{LOWER}]+(?:-[{UPPER}][{LOWER}]+)*$")
INITIAL = re.compile(rf"^[{UPPER}]\.$")


def name_problems(name: str) -> list[str]:
    """Words that do not read as a name word, a particle or an initial."""
    words = name.split()
    bad = [w for w in words if not (WORD.match(w) or INITIAL.match(w) or w in PARTICLES)]
    if len(words) < 2 or words[0] in PARTICLES or words[-1] in PARTICLES:
        bad.append(name)
    return bad


FIX_KINDS = ("line", "name")
Fixes = dict[tuple[str, str, str, str], str]


def read_fixes(path: Path = FIXES) -> Fixes:
    """(legislature, circle_name, kind, ocr_text) -> published_text. A line fix replaces a whole
    OCR line inside that circle (a misread list count); a name fix replaces a parsed name."""
    out: Fixes = {}
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key = (r["legislature"], r["circle_name"], r["kind"], r["ocr_text"])
            if r["kind"] not in FIX_KINDS or key in out:
                raise ElectedError(f"{path.name}: bad or repeated fix {key}")
            out[key] = r["published_text"]
    return out


def _circle_of(line: str, circles: dict[str, tuple[str, int]]) -> str | None:
    m = CIRCLE.match(" ".join(line.split()))
    if not m:
        return None
    names = {normalise(name): name for name, _seats in circles.values()}
    found = difflib.get_close_matches(normalise(m.group(1)), list(names), 1, 0.6)
    return names[found[0]] if found else None


def fix_lines(
    lines: list[str], legislature: str, circles: dict[str, tuple[str, int]], fixes: Fixes
) -> tuple[list[str], set]:
    """The OCR lines with the line fixes applied, and the fixes used."""
    used, out, circle = set(), [], None
    for line in lines:
        circle = _circle_of(line, circles) or circle
        key = (legislature, circle, "line", line.strip())
        if key in fixes:
            used.add(key)
            line = fixes[key]
        out.append(line)
    return out, used


def apply_fixes(rows: list[dict], fixes: Fixes, used_lines: set = frozenset()) -> list[dict]:
    """The rows with the name fixes applied. Every fix must have been used."""
    used = set(used_lines)
    out = []
    for r in rows:
        key = (r["legislature"], r["circle_name"], "name", r["published_name"])
        if key in fixes:
            used.add(key)
            r = {**r, "published_name": fixes[key]}
        out.append(r)
    unused = sorted(set(fixes) - used)
    if unused:
        raise ElectedError("unused fixes: " + "; ".join(f"{k[0]} {k[1]} {k[3]!r}" for k in unused))
    return out


# --- matching to cadastro_id --------------------------------------------------------------

# Groups a single-party list elects, beyond its own acronym.
LIST_GROUPS = {"PPD/PSD": {"PSD", "PPD"}, "CDS": {"CDS", "CDS-PP"}}
GROUP_ALIASES = {"PSD": {"PPD"}, "CDS": {"CDS-PP"}}


def read_groups(path: Path) -> dict[tuple[str, str], set[str]]:
    """(legislature, ballot_acronym) -> group codes of a coalition list, from coalitions.csv."""
    out: dict[tuple[str, str], set[str]] = defaultdict(set)
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out[(r["legislature"], r["ballot_acronym"])].add(r["group_code"])
    return dict(out)


def allowed_groups(legislature: str, acronym: str, groups: dict) -> set[str]:
    base = groups.get((legislature, acronym)) or LIST_GROUPS.get(acronym) or {acronym}
    return set(base).union(*(GROUP_ALIASES.get(g, set()) for g in base), {"Indep"})


# The AR publishes one deputados.ndjson for the whole legislature I in both the I-A and I-B
# folders (docs/known-gaps.md, #85). A deputy counts in a part only through group periods
# that overlap its dates.
PART_DATES = {"I-A": ("1976-06-03", "1980-01-02"), "I-B": ("1980-01-03", "1980-11-12")}


def _groups(record: dict, legislature: str) -> set[str]:
    start, end = PART_DATES.get(legislature, ("", "9999"))
    return {
        g["gpSigla"]
        for g in record.get("DepGP") or []
        if g.get("gpSigla")
        and (g.get("gpDtInicio") or "") <= end
        and (g.get("gpDtFim") or "9999") >= start
    }


def read_deputies(data_dir: Path) -> list[dict]:
    """One row per deputy and InformacaoBase legislature, with circle and group codes."""
    out = []
    for path in sorted((data_dir / "informacao_base").glob("*/deputados.ndjson")):
        legislature = path.parent.name
        for line in path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            groups = _groups(r, legislature)
            if legislature in PART_DATES and not groups:
                continue
            out.append(
                {
                    "cadastro_id": int(r["DepCadId"]),
                    "full_name": r.get("DepNomeCompleto") or "",
                    "legislature": legislature,
                    "circle": r.get("DepCPDes") or "",
                    "groups": groups,
                }
            )
    return out


def _words(name: str) -> list[str]:
    return [w for w in normalise(name).split() if w not in PARTICLES and w != "d"]


def _alike(a: str, b: str) -> bool:
    return a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


def similar_name(published: str, full: str) -> bool:
    """First and last names spelt alike, and a close spelling or one name inside the other."""
    p, q = _words(published), _words(full)
    if not p or not q or not (_alike(p[0], q[0]) and _alike(p[-1], q[-1])):
        return False
    if difflib.SequenceMatcher(None, " ".join(p), " ".join(q)).ratio() >= 0.8:
        return True
    pw = {w for w in p if len(w) > 1}
    initials = [w for w in p if len(w) == 1]
    if not all(any(x.startswith(i) for x in q) for i in initials):
        return False
    return pw <= set(q) or set(q) <= pw


def match_rows(
    rows: list[dict],
    deputies: list[dict],
    overrides: dict[tuple, int | None],
    groups: dict[tuple[str, str], set[str]],
) -> list[dict]:
    by_name: dict[str, set[int]] = defaultdict(set)
    sat: dict[int, set[str]] = defaultdict(set)
    for d in deputies:
        by_name[normalise(d["full_name"])].add(d["cadastro_id"])
        sat[d["cadastro_id"]].add(d["legislature"])
    out, problems, used = [], [], set()
    for r in rows:
        key = (r["legislature"], r["circle_name"], r["ballot_acronym"], r["published_name"])
        label = " ".join(key)
        if key in overrides:
            used.add(key)
            cid = overrides[key]
            out.append(
                {**r, "cadastro_id": cid, "match": "unmatched" if cid is None else "override"}
            )
            continue
        found = by_name.get(normalise(r["published_name"]), set())
        if len(found) > 1:
            found = {c for c in found if r["legislature"] in sat[c]}
        kind = "exact"
        if not found:
            kind = "fuzzy"
            ok = allowed_groups(r["legislature"], r["ballot_acronym"], groups)
            found = {
                d["cadastro_id"]
                for d in deputies
                if d["legislature"] == r["legislature"]
                and normalise(d["circle"]) == normalise(r["circle_name"])
                and d["groups"] & ok
                and similar_name(r["published_name"], d["full_name"])
            }
        if len(found) == 1:
            out.append({**r, "cadastro_id": next(iter(found)), "match": kind})
        elif found:
            ids = ", ".join(str(c) for c in sorted(found))
            problems.append(f"{label}: {len(found)} candidates ({ids})")
        else:
            problems.append(f"{label}: no match")
    for key in sorted(set(overrides) - used):
        problems.append(f"{' '.join(key)}: override for no elected row")
    count: dict[tuple[str, int], int] = defaultdict(int)
    for r in out:
        if r["cadastro_id"] is not None:
            count[(r["legislature"], r["cadastro_id"])] += 1
    problems += [f"{leg}: {cid} elected twice" for (leg, cid), n in count.items() if n > 1]
    if problems:
        raise ElectedError(f"add these to {OVERRIDES.name}:\n" + "\n".join(problems))
    return out


def read_overrides(path: Path = OVERRIDES) -> dict[tuple, int | None]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out: dict[tuple, int | None] = {}
    for r in rows:
        key = (r["legislature"], r["circle_name"], r["ballot_acronym"], r["published_name"])
        if not (r.get("note") or "").strip():
            raise ElectedError(f"{' '.join(key)}: override without a note")
        if key in out:
            raise ElectedError(f"{' '.join(key)}: override twice")
        out[key] = int(r["cadastro_id"]) if r["cadastro_id"].strip() else None
    return out


# --- files --------------------------------------------------------------------------------


def read_seats(path: Path = SEEDS / "ballot_list_seats.csv") -> dict[str, dict]:
    """legislature -> election date, circles (code -> name, seats) and seats per list."""
    out: dict[str, dict] = {}
    legislatures = {leg for leg, _url in ELECTIONS}
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["legislature"] not in legislatures:
                continue
            e = out.setdefault(r["legislature"], {"date": r["election_date"], "circles": {},
                                                  "lists": {}})  # fmt: skip
            name, seats = e["circles"].get(r["circle_code"], (r["circle_name"], 0))
            e["circles"][r["circle_code"]] = (name, seats + int(r["seats"]))
            e["lists"][(r["circle_code"], r["ballot_acronym"])] = int(r["seats"])
    return out


def check_lists(rows: list[dict], lists: dict[tuple[str, str], int], legislature: str) -> None:
    got: dict[tuple[str, str], int] = defaultdict(int)
    for r in rows:
        got[(r["circle_code"], r["ballot_acronym"])] += 1
    if dict(got) != lists:
        diff = sorted(k for k in set(got) | set(lists) if got.get(k) != lists.get(k))
        raise ElectedError(f"{legislature}: lists differ from ballot_list_seats at {diff}")


def fetch(url: str, cache: Path | None) -> tuple[bytes, str]:
    """The PDF and the Lisbon date it was downloaded (a cached copy keeps its own)."""
    path = cache / url.rsplit("/", 1)[-1] if cache is not None else None
    if path is not None and path.exists():
        when = dt.datetime.fromtimestamp(path.stat().st_mtime, LISBON)
        return path.read_bytes(), when.date().isoformat()
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return data, dt.datetime.now(LISBON).date().isoformat()


def file_modified(data: bytes) -> str | None:
    """Date the PDF says it was last saved (UTC, YYYY-MM-DD), from pdfinfo, or None."""
    info = subprocess.run(
        ["pdfinfo", "-isodates", "-"], input=data, check=True, capture_output=True
    ).stdout.decode("utf-8", "replace")
    found = re.search(r"^ModDate:\s+(\S+)", info, re.MULTILINE)
    if not found:
        return None
    stamp = re.sub(r"([+-]\d\d)$", r"\1:00", found.group(1).replace("Z", "+00:00"))
    return dt.datetime.fromisoformat(stamp).astimezone(dt.UTC).date().isoformat()


def ocr_cached(url: str, data: bytes, cache: Path | None) -> list[str]:
    path = cache / (url.rsplit("/", 1)[-1] + ".txt") if cache is not None else None
    if path is not None and path.exists():
        return path.read_text(encoding="utf-8").splitlines()
    lines = ocr_pdf(data)
    if path is not None:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def write(rows: list[dict], path: Path = SEED) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: "" if r[k] is None else r[k] for k in COLUMNS})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, help="folder for the PDFs and their OCR text")
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    args = parser.parse_args(argv)
    seats = read_seats()
    rows, files, problems, used = [], [], [], set()
    fixes = read_fixes()
    try:
        for legislature, url in ELECTIONS:
            data, downloaded = fetch(url, args.cache)
            files.append(
                {"publisher": "CNE", "url": url, "downloaded": downloaded,
                 "file_modified": file_modified(data)}
            )  # fmt: skip
            e = seats[legislature]
            lines, fixed = fix_lines(
                ocr_cached(url, data, args.cache), legislature, e["circles"], fixes
            )
            used |= fixed
            try:
                election = parse(lines, legislature, e["circles"])
                check_lists(election, e["lists"], legislature)
            except ElectedError as err:
                problems.append(str(err))
                continue
            rows += [{**r, "election_date": e["date"], "source_url": url} for r in election]
            print(f"{legislature}: {len(election)} names")
        if problems:
            raise ElectedError("\n".join(problems))
        rows = apply_fixes(rows, fixes, used)
        bad = [f"{r['legislature']} {r['published_name']!r}" for r in rows
               if name_problems(r["published_name"])]  # fmt: skip
        if bad:
            raise ElectedError(f"names to fix in {FIXES.name}:\n" + "\n".join(bad))
        rows = match_rows(
            rows, read_deputies(args.data), read_overrides(), read_groups(SEEDS / "coalitions.csv")
        )
    except ElectedError as e:
        print(e, file=sys.stderr)
        return 1
    write(rows)
    meta = json.dumps({"files": files}, ensure_ascii=False, indent=1) + "\n"
    SOURCES.write_text(meta, encoding="utf-8")
    kinds = defaultdict(int)
    for r in rows:
        kinds[r["match"]] += 1
    print(f"Wrote {len(rows)} rows to {SEED.relative_to(ROOT)}: {dict(kinds)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
