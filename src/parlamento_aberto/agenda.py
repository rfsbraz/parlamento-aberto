"""Staging for AgendaParlamentar: parse dates and turn InternetText into plain text."""

from __future__ import annotations

import html
import json
import re
import tempfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import duckdb

_BREAK_BEFORE = frozenset({"br", "p", "div", "tr", "li", "h1", "h2", "h3", "td", "th"})
_BREAK_AFTER = frozenset({"p", "div", "tr", "li", "h1", "h2", "h3", "table"})

COLUMNS = {
    "event_id": "BIGINT",
    "start_date": "DATE",
    "start_time": "TIME",
    "end_date": "DATE",
    "end_time": "TIME",
    "all_day": "BOOLEAN",
    "section": "VARCHAR",
    "theme": "VARCHAR",
    "body": "VARCHAR",
    "group_code": "BIGINT",
    "title": "VARCHAR",
    "subtitle": "VARCHAR",
    "location": "VARCHAR",
    "internet_text": "VARCHAR",
    "text": "VARCHAR",
    "link": "VARCHAR",
    "meeting_number": "VARCHAR",
    "legislature": "VARCHAR",
    "source_file": "VARCHAR",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"style", "script"}:
            self._skip += 1
            return
        if not self._skip and tag in _BREAK_BEFORE:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"style", "script"} and self._skip:
            self._skip -= 1
            return
        if not self._skip and tag in _BREAK_AFTER:
            self.parts.append("\n")


def plain_text(raw: str | None) -> str:
    """Decode HTML entities, drop tags, and return readable plain text."""
    if not raw:
        return ""
    parser = _TextExtractor()
    parser.feed(html.unescape(raw))
    parser.close()
    text = html.unescape("".join(parser.parts)).replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    return datetime.strptime(value, "%d/%m/%Y").date().isoformat()


def _parse_time(value: str | None) -> str | None:
    if not value:
        return None
    return datetime.strptime(value, "%H:%M:%S").time().isoformat()


def _rows(data_dir: Path) -> list[dict]:
    rows = []
    for path in sorted((data_dir / "agenda_parlamentar").glob("*/records.ndjson")):
        legislature = path.parent.name
        source_file = path.relative_to(data_dir).as_posix()
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            record = json.loads(line)
            internet_text = record.get("InternetText")
            rows.append(
                {
                    "event_id": record.get("Id"),
                    "start_date": _parse_date(record.get("EventStartDate")),
                    "start_time": _parse_time(record.get("EventStartTime")),
                    "end_date": _parse_date(record.get("EventEndDate")),
                    "end_time": _parse_time(record.get("EventEndTime")),
                    "all_day": bool(record.get("AllDayEvent")),
                    "section": record.get("Section"),
                    "theme": record.get("Theme"),
                    "body": record.get("OrgDes"),
                    "group_code": record.get("ParlamentGroup"),
                    "title": record.get("Title"),
                    "subtitle": record.get("Subtitle"),
                    "location": record.get("Local"),
                    "internet_text": internet_text,
                    "text": plain_text(internet_text),
                    "link": record.get("Link"),
                    "meeting_number": record.get("ReuNumero"),
                    "legislature": legislature,
                    "source_file": source_file,
                }
            )
    return rows


def build_agenda_events(con: duckdb.DuckDBPyConnection, data_dir: str) -> None:
    rows = _rows(Path(data_dir))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "events.ndjson"
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        columns = ", ".join(f"{k}: '{v}'" for k, v in COLUMNS.items())
        source = path.as_posix().replace("'", "''")
        names = ", ".join(COLUMNS)
        con.execute(
            "create or replace table stg_agenda_parlamentar__events as "
            f"select {names} from read_json('{source}', "
            f"format = 'newline_delimited', columns = {{{columns}}})"
        )
