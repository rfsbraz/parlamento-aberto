"""Write models/seeds/ballot_list_seats.csv from the SGMAI election results files (#55).

The Secretaria-Geral do Ministério da Administração Interna (SGMAI) publishes one results
workbook per election to the Assembleia da República. From 2009 on, every workbook has the
seats won by each ballot list in each electoral circle, the two abroad circles included, in
columns headed "mandatos". This script reads those columns as published and keeps the lists
that won at least one seat.
Nothing is computed: the seat counts are the SGMAI's.

It also writes models/seeds/ballot_list_seats.sources.json with, for each workbook, the date
it was downloaded and, when the workbook's own metadata has one, the date it was last saved
(Lei n.º 26/2016, art. 19.º, n.º 5). A file with no such date gets no file_modified.

Usage: uv run python scripts/mai_list_seats.py [--cache DIR]
"""

import argparse
import csv
import datetime as dt
import io
import json
import re
import struct
import sys
import urllib.request
import zipfile
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parents[1]
SEED = ROOT / "src" / "parlamento_aberto" / "models" / "seeds" / "ballot_list_seats.csv"
SOURCES = SEED.with_suffix(".sources.json")
LISBON = ZoneInfo("Europe/Lisbon")
BASE = "https://www.sg.mai.gov.pt/pt/AdministracaoEleitoral/EleicoesReferendos/AssembleiaRepublica/Documents/"
# legislature, election date, workbook. 2022: the workbook with the repeated Europa vote,
# whose result elected the Europa deputies.
ELECTIONS = [
    ("XI", "2009-09-27", BASE + "AR2009_Globais.xls"),
    ("XII", "2011-06-05", BASE + "AR_2011_Globais.xls"),
    ("XIII", "2015-10-04", BASE + "AR_2015_Globais.xls"),
    ("XIV", "2019-10-06", BASE + "AR_2019_Globais.xlsx"),
    ("XV", "2022-01-30", BASE + "AR2022/AR_2022_Globais_REPEU.xlsx"),
    ("XVI", "2024-03-10", BASE + "AR2024/AR_2024_Globais.xlsx"),
    ("XVII", "2025-05-18", BASE + "AR2025/AR_2025_Globais.xlsx"),
]
# Rows that add up circles rather than being one.
AGGREGATES = ("território nacional", "estrangeiro", "resultados globais")
COLUMNS = [
    "legislature",
    "election_date",
    "circle_code",
    "circle_name",
    "ballot_acronym",
    "seats",
    "source_url",
]


class MaiError(ValueError):
    pass


def sheets(data: bytes, name: str):
    """(sheet name, rows as lists of cell values) for an .xls or .xlsx workbook."""
    if name.endswith(".xlsx"):
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        for ws in wb.worksheets:
            yield ws.title, [list(r) for r in ws.iter_rows(values_only=True)]
    else:
        import xlrd

        wb = xlrd.open_workbook(file_contents=data)
        for ws in wb.sheets():
            yield ws.name, [ws.row_values(i) for i in range(ws.nrows)]


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _code(value) -> str:
    if isinstance(value, float) and value.is_integer():
        n = int(value)
        return str(n).zfill(6 if n >= 10000 else 2)
    return _text(value)


def _seats(value) -> int | None:
    if value is None or _text(value) == "":
        return None
    if isinstance(value, str):
        value = float(value)
    if not float(value).is_integer() or value < 0:
        raise MaiError(f"seat count {value!r} is not a whole number")
    return int(value)


def _layout(header: list) -> tuple[int, list[tuple[int, str]]]:
    """Index of the circle's total seats and (index, list) for each list's seats column."""
    names = [_text(h).lower() for h in header]
    if "% nulos" not in names:
        raise MaiError(f"no '% nulos' column in header {header!r}")
    first_list = names.index("% nulos") + 1
    total, lists = None, []
    for j, h in enumerate(names):
        if not h.startswith("mandat") and h != "total de mandatos":
            continue
        if j - 2 >= first_list and names[j - 1].startswith("%"):
            lists.append((j, _text(header[j - 2])))
        elif total is None:
            total = j
    if total is None or not lists:
        raise MaiError(f"no seat columns in header {header!r}")
    return total, lists


def parse(data: bytes, name: str) -> dict[str, dict]:
    """Circles in one workbook: code -> name, total seats and seats per list (seats > 0)."""
    circles: dict[str, dict] = {}
    for _sheet, rows in sheets(data, name):
        layout = None
        for row in rows:
            first = _text(row[0] if row else "").lower()
            if first == "código":
                cells = [_text(c).lower() for c in row]
                has_seats = any(c.startswith("mandat") or c == "total de mandatos" for c in cells)
                layout = _layout(row) if has_seats else None
                continue
            if layout is None or first == "" or not first.replace(".", "").isdigit():
                continue
            circle_name = _text(row[1])
            total_at, lists = layout
            total = _seats(row[total_at]) if total_at < len(row) else None
            if total is None or circle_name.lower().startswith(AGGREGATES):
                continue
            seats = {}
            for j, acronym in lists:
                n = _seats(row[j]) if j < len(row) else None
                if n:
                    seats[acronym] = n
            if sum(seats.values()) != total:
                raise MaiError(
                    f"{name} {circle_name}: lists add up to {sum(seats.values())}, not {total}"
                )
            circle = {"name": circle_name, "total": total, "seats": seats}
            code = _code(row[0])
            if code in circles and circles[code] != circle:
                raise MaiError(f"{name} {circle_name}: two sheets disagree")
            circles[code] = circle
    if not circles:
        raise MaiError(f"{name}: no circle with seats")
    return circles


def rows_for(legislature: str, date: str, url: str, data: bytes) -> list[dict]:
    circles = parse(data, url.rsplit("/", 1)[-1])
    return [
        {
            "legislature": legislature,
            "election_date": date,
            "circle_code": code,
            "circle_name": c["name"],
            "ballot_acronym": acronym,
            "seats": n,
            "source_url": url,
        }
        for code, c in sorted(circles.items())
        for acronym, n in sorted(c["seats"].items())
    ]


# FILETIME: 100 ns intervals since 1601-01-01 UTC.
FILETIME_EPOCH = dt.datetime(1601, 1, 1, tzinfo=dt.UTC)
PID_LASTSAVE_DTM = 13
VT_FILETIME = 0x40


def last_saved(stream: bytes) -> str | None:
    """Last saved date (UTC, YYYY-MM-DD) in an OLE SummaryInformation stream, if there is one."""
    try:
        (offset,) = struct.unpack_from("<I", stream, 44)
        _size, count = struct.unpack_from("<II", stream, offset)
        for i in range(count):
            pid, at = struct.unpack_from("<II", stream, offset + 8 + 8 * i)
            if pid != PID_LASTSAVE_DTM:
                continue
            vtype, filetime = struct.unpack_from("<IQ", stream, offset + at)
            if vtype & 0xFFFF != VT_FILETIME or not filetime:
                return None
            return (FILETIME_EPOCH + dt.timedelta(microseconds=filetime // 10)).date().isoformat()
    except struct.error:
        return None
    return None


def file_modified(data: bytes, name: str) -> str | None:
    """Date the workbook says it was last saved (UTC, YYYY-MM-DD), or None if it says none."""
    if name.endswith(".xlsx"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if "docProps/core.xml" not in z.namelist():
                return None
            core = z.read("docProps/core.xml").decode("utf-8")
        found = re.search(r"<dcterms:modified[^>]*>(\d{4}-\d{2}-\d{2})", core)
        return found.group(1) if found else None
    from xlrd import compdoc

    try:
        doc = compdoc.CompDoc(data)
        stream = doc.get_named_stream("\x05SummaryInformation")
    except compdoc.CompDocError:
        return None
    return last_saved(stream) if stream else None


def fetch(url: str, cache: Path | None) -> tuple[bytes, str]:
    """The workbook and the Lisbon date it was downloaded (a cached copy keeps its own)."""
    if cache is not None:
        path = cache / url.rsplit("/", 1)[-1]
        if path.exists():
            when = dt.datetime.fromtimestamp(path.stat().st_mtime, LISBON)
            return path.read_bytes(), when.date().isoformat()
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return data, dt.datetime.now(LISBON).date().isoformat()


def source_entry(url: str, data: bytes, downloaded: str) -> dict:
    entry = {"url": url, "downloaded": downloaded}
    modified = file_modified(data, url.rsplit("/", 1)[-1])
    if modified:
        entry["file_modified"] = modified
    return entry


def write(rows: list[dict], path: Path = SEED) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_sources(files: list[dict], path: Path = SOURCES) -> None:
    meta = {"publisher": "SGMAI", "files": files}
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, help="folder to keep the downloaded workbooks in")
    args = parser.parse_args(argv)
    rows, files = [], []
    for legislature, date, url in ELECTIONS:
        data, downloaded = fetch(url, args.cache)
        files.append(source_entry(url, data, downloaded))
        election = rows_for(legislature, date, url, data)
        print(
            f"{legislature} {date}: {sum(r['seats'] for r in election)} seats, {len(election)} rows"
        )
        rows += election
    write(rows)
    write_sources(files)
    print(f"Wrote {len(rows)} rows to {SEED.relative_to(ROOT)} and {SOURCES.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
