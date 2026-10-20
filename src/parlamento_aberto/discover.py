"""Weekly discover job: compare the AR open data pages with sources.yaml.

The open data page (DadosAbertos.aspx) links one page per dataset type. Each of those
lists one folder per legislature, and each folder lists the files. The scan reads those
pages one at a time with a pause between requests, and the diff compares every JSON
file link with sources.yaml:

- a new link for a known dataset in a legislature folder is an addition, which the
  workflow commits to sources.yaml on data/discover and opens as a held PR;
- anything that needs a decision is a problem, which the workflow reports in an issue:
  a listed link that is gone (removed), a file that matches no dataset (new dataset), a
  file for a dataset and legislature already listed with another link (changed), or a
  page the scan cannot read (layout).

XML, XSD and PDF links are twins of the JSON files and are not compared. The
`discover` block of sources.yaml lists pages and links that are left out on purpose.
"""

import argparse
import datetime as dt
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from . import sources as sources_mod
from .fetch import USER_AGENT

LISBON = ZoneInfo("Europe/Lisbon")
SITE = "https://www.parlamento.pt"
TOP = SITE + "/Cidadania/Paginas/DadosAbertos.aspx"
SECTION = re.compile(r"^/Cidadania/Paginas/(DA\w+)\.aspx$")
DELAY = 2.0
ATTEMPTS = 4
BACKOFF = 30.0
MAX_DEPTH = 3

# Cron strings, exactly as written in discover.yml (GitHub cron is UTC).
SUMMER = "0 7 * * 1"  # Monday 08:00 Lisbon when Lisbon is UTC+1
WINTER = "0 8 * * 1"  # Monday 08:00 Lisbon when Lisbon is UTC+0

HOLD_NEW = "hold: new-dataset"
STEM = re.compile(r"^(?P<stem>.*?)(?P<part>\d{4}[A-Z][a-z])?(?P<leg>Cons|[IVX]+[AB]?)?_json\.txt$")
FOLDER = re.compile(r"^(?P<leg>[IVX]+) Legislatura$")


class ScanError(RuntimeError):
    """A page could not be fetched after every retry. The run fails; no issue is opened."""


def config(sources_path: Path) -> dict:
    raw = yaml.safe_load(Path(sources_path).read_text(encoding="utf-8")) or {}
    spec = raw.get("discover") or {}
    return {
        "ignore_pages": dict(spec.get("ignore_pages") or {}),
        "ignore_links": list(spec.get("ignore_links") or []),
    }


class _Items(HTMLParser):
    """Links of the page: every <a href>, and the first link in each div.archive-item."""

    def __init__(self):
        super().__init__()
        self.items, self.links = [], []
        self._depth = 0
        self._href = None
        self._text = []
        self._taken = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            if self._depth:
                self._depth += 1
            elif "archive-item" in (attrs.get("class") or "").split():
                self._depth, self._taken = 1, False
        elif tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
            if self._depth and not self._taken:
                self._href, self._text = attrs["href"], []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.items.append((self._href, " ".join("".join(self._text).split())))
            self._href, self._taken = None, True
        elif tag == "div" and self._depth:
            self._depth -= 1


def _parse(html: str) -> _Items:
    p = _Items()
    p.feed(html)
    p.close()
    return p


def http_get(url: str, timeout: float = 120) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        if r.status != 200:
            raise OSError(f"HTTP {r.status} for {url}")
        if r.headers.get("Content-Encoding", "").lower() == "gzip":
            body = gzip.decompress(body)
        return body.decode("utf-8", "replace")


def _page(get: Callable[[str], str], sleep: Callable[[float], None], url: str) -> str:
    for attempt in range(ATTEMPTS):
        sleep(DELAY)
        try:
            return get(url)
        except (OSError, urllib.error.URLError) as e:
            last = e
            if attempt < ATTEMPTS - 1:
                sleep(BACKOFF * 2**attempt)
    raise ScanError(f"could not fetch {url}: {last}")


def _fich(url: str) -> str | None:
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("fich")
    return values[0] if values else None


def scan(get=http_get, sleep=time.sleep, ignore_pages=()) -> dict:
    """Read the open data pages. Returns the dataset pages, every file link and the
    pages it could not read."""
    out = {"top_ok": True, "pages": [], "links": [], "problems": []}
    top = _parse(_page(get, sleep, TOP))
    names = []
    for href in top.links:
        path = urllib.parse.urlsplit(urllib.parse.urljoin(TOP, href))
        match = SECTION.match(path.path) if path.netloc == "www.parlamento.pt" else None
        if match and not path.query and match.group(1) not in names:
            names.append(match.group(1))
    if not names:
        out["top_ok"] = False
        out["problems"].append(
            {"kind": "layout", "detail": f"{TOP} links no dataset page (Paginas/DA*.aspx)."}
        )
        return out
    seen = set()
    for name in names:
        if name in ignore_pages:
            continue
        out["pages"].append(name)
        _crawl(get, sleep, name, f"{SITE}/Cidadania/Paginas/{name}.aspx", None, 0, seen, out)
    return out


def _crawl(get, sleep, name, url, folder, depth, seen, out):
    seen.add(url)
    items = _parse(_page(get, sleep, url)).items
    where = f"{name} / {folder}" if folder else name
    if not items:
        # Some legislature folders are empty on the AR site; an empty dataset page is not.
        if folder is None:
            detail = f"{where}: no folders or files ({url})."
            out["problems"].append({"kind": "layout", "detail": detail})
        return
    for href, text in items:
        target = urllib.parse.urljoin(url, href)
        parts = urllib.parse.urlsplit(target)
        if "/webutils/docs/doc." in parts.path:
            link = {"page": name, "folder": folder, "url": target, "file": _fich(target)}
            out["links"].append(link)
        elif parts.path == f"/Cidadania/Paginas/{name}.aspx" and parts.query:
            if target in seen or depth >= MAX_DEPTH:
                continue
            if folder is None and not _legislature(text):
                out["problems"].append(
                    {"kind": "layout", "detail": f"{name}: folder {text!r} is not a legislature."}
                )
            _crawl(get, sleep, name, target, folder or text, depth + 1, seen, out)


def _legislature(folder: str | None) -> str | None:
    if folder == "Constituinte":
        return folder
    match = FOLDER.match(folder or "")
    return match.group("leg") if match else None


def stem(file: str) -> tuple[str, str | None, str | None] | None:
    """(stem, part, legislature token) of a JSON file name, or None if it is not one."""
    match = STEM.match(file or "")
    if not match:
        return None
    return match.group("stem"), match.group("part"), match.group("leg")


def _token_legislature(token: str | None) -> str | None:
    if token is None:
        return None
    if token == "Cons":
        return "Constituinte"
    return token[:-1] if token[-1] in "AB" and len(token) > 1 else token


def diff(sources_path: Path, scan_result: dict) -> dict:
    srcs = sources_mod.load(sources_path)
    cfg = config(sources_path)
    problems = list(scan_result["problems"])
    if not scan_result.get("top_ok", True):
        return {"added": [], "problems": problems}
    # AR renders a new path token in every link on every page view, so a file is
    # identified by the legislature folder it is listed in and its file name.
    known = {(s.listed_on or s.legislature, _fich(s.url)): s for s in srcs}
    keys = {s.key for s in srcs}
    datasets: dict[str, set] = {}
    for s in srcs:
        parsed = stem(_fich(s.url) or "")
        if parsed:
            datasets.setdefault(parsed[0], set()).add(s.dataset)
    ignored = {(i["page"], i.get("folder"), i["file"]) for i in cfg["ignore_links"]}
    found = {(_legislature(link["folder"]), link["file"]) for link in scan_result["links"]}
    for ident, s in known.items():
        if ident not in found:
            detail = f"{s.key}: {ident[1]} is no longer listed under {ident[0]}."
            problems.append({"kind": "removed", "detail": detail})
    added = []
    for link in scan_result["links"]:
        url, file = link["url"], link["file"]
        ident = (_legislature(link["folder"]), file)
        if ident in known or (link["page"], link["folder"], file) in ignored:
            continue
        parsed = stem(file)
        if parsed is None:
            continue  # XML, XSD and PDF twins
        where = f"{link['page']} / {link['folder']}" if link["folder"] else link["page"]
        name, part, token = parsed
        matches = datasets.get(name, set())
        legislature = _legislature(link["folder"])
        if len(matches) != 1:
            problems.append(
                {"kind": "new dataset", "detail": f"{where}: {file} matches no dataset ({url})."}
            )
            continue
        if legislature is None:
            continue  # already reported as a layout problem
        dataset = next(iter(matches))
        named = _token_legislature(token)
        if part is None and token and len(token) > 1 and token[-1] in "AB":
            part = token[-1]  # I-A and I-B, as in sources.yaml
        key = f"{dataset}/{legislature}-{part}" if part else f"{dataset}/{legislature}"
        if named and named != legislature:
            detail = f"{where}: {file} is named for {named} but listed under {legislature} ({url})."
            problems.append({"kind": "changed", "detail": detail})
        elif key in keys or key in {_key(a) for a in added}:
            problems.append(
                {"kind": "changed", "detail": f"{key} is already listed; new link {file} ({url})."}
            )
        else:
            added.append({"dataset": dataset, "legislature": legislature, "part": part, "url": url})
    order = sources_mod.legislature_number
    added.sort(key=lambda a: (a["dataset"], order(a["legislature"]), a["part"] or ""))
    unique = []
    for p in problems:
        if p not in unique:
            unique.append(p)
    return {"added": added, "problems": unique}


def _key(added: dict) -> str:
    leg = added["legislature"]
    leg = f"{leg}-{added['part']}" if added.get("part") else leg
    return f"{added['dataset']}/{leg}"


def apply(sources_path: Path, report: dict) -> int:
    """Add the new links to sources.yaml, keeping every existing line. Idempotent."""
    path = Path(sources_path)
    count = 0
    for entry in report["added"]:
        if _key(entry) in {s.key for s in sources_mod.load(path)}:
            continue
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        start = next(
            (i for i, line in enumerate(lines) if line.rstrip() == f"  {entry['dataset']}:"), None
        )
        if start is None:
            raise ValueError(f"dataset {entry['dataset']} not in {path}")
        end = start + 1
        while end < len(lines) and not re.match(r"^ {0,2}\S", lines[end]):
            end += 1
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        new = [f"      - legislature: {entry['legislature']}\n"]
        if entry.get("part"):
            new.append(f"        part: {entry['part']}\n")
        new.append(f'        url: "{entry["url"]}"\n')
        lines[end:end] = new
        path.write_text("".join(lines), encoding="utf-8")
        if _key(entry) not in {s.key for s in sources_mod.load(path)}:
            raise ValueError(f"could not add {_key(entry)} to {path}")
        count += 1
    return count


def pr_body(report: dict) -> str:
    lines = [
        "New links on the AR open data pages for datasets already in `sources.yaml`, found by",
        "the weekly discover job (`.github/workflows/discover.yml`).",
        "",
    ]
    lines += [f"- `{_key(a)}`: {a['url']}" for a in report["added"]]
    lines += [
        "",
        f"Held with `{HOLD_NEW}`, so it never merges on its own. Check the files and merge by",
        "hand. Once a new legislature is merged, the nightly run treats it as current, and",
        "the monthly full sync keeps refreshing the previous one.",
    ]
    return "\n".join(lines) + "\n"


def issue_body(report: dict, *, token: bool) -> str:
    titles = {
        "removed": "Links in sources.yaml no longer listed",
        "new dataset": "Files that match no dataset in sources.yaml",
        "changed": "Files for a dataset and legislature that need a decision",
        "layout": "Pages the scan could not read",
    }
    lines = [
        "The weekly discover job found changes on the AR open data pages that need a decision.",
        f"Pages: {TOP}",
        "",
    ]
    for kind, title in titles.items():
        items = [p["detail"] for p in report["problems"] if p["kind"] == kind]
        if items:
            lines += [f"## {title}", ""] + [f"- {d}" for d in items] + [""]
    if report["added"] and not token:
        lines += [
            "## New links (no PR opened: DATA_BOT_TOKEN is not set)",
            "",
            *[f"- `{_key(a)}`: {a['url']}" for a in report["added"]],
            "",
            "See docs/repo-settings.md for the token.",
            "",
        ]
    lines.append("Nothing was changed. This issue is updated by later runs while it is open.")
    return "\n".join(lines) + "\n"


def plan(event: str, schedule: str | None, *, now: dt.datetime) -> dict:
    if event == "workflow_dispatch":
        return {"run": True, "reason": "manual run"}
    if event != "schedule":
        raise ValueError(f"unexpected event {event!r}")
    if schedule not in (SUMMER, WINTER):
        raise ValueError(f"unknown schedule {schedule!r}")
    # Two UTC crons cover summer and winter time; only the one that lands on 08:00
    # Lisbon today runs. Checking the offset copes with late crons.
    offset = now.astimezone(LISBON).utcoffset() / dt.timedelta(hours=1)
    if offset != (1 if schedule == SUMMER else 0):
        return {"run": False, "reason": "the other cron covers this season"}
    return {"run": True, "reason": "Monday 08:00 Lisbon"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="parlamento_aberto.discover")
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--event", required=True)
    pl.add_argument("--schedule", default="")
    for name in ("scan", "diff", "apply", "bodies"):
        s = sub.add_parser(name)
        s.add_argument("--sources", type=Path, default=Path("sources.yaml"))
        if name in ("scan", "diff"):
            s.add_argument("--scan", type=Path, required=True)
        if name != "scan":
            s.add_argument("--report", type=Path, required=True)
        if name == "bodies":
            s.add_argument("--token", choices=("true", "false"), required=True)
            s.add_argument("--pr", type=Path, required=True)
            s.add_argument("--issue", type=Path, required=True)
    a = p.parse_args(argv)
    if a.cmd == "plan":
        result = plan(a.event, a.schedule or None, now=dt.datetime.now(dt.UTC))
        print(f"run={'true' if result['run'] else 'false'}")
        print(f"reason={result['reason']}")
        return 0
    if a.cmd == "scan":
        result = scan(ignore_pages=config(a.sources)["ignore_pages"])
        a.scan.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"pages={len(result['pages'])}")
        print(f"links={len(result['links'])}")
        return 0
    if a.cmd == "diff":
        report = diff(a.sources, json.loads(a.scan.read_text(encoding="utf-8")))
        text = json.dumps(report, indent=1, ensure_ascii=False) + "\n"
        a.report.write_text(text, encoding="utf-8")
        print(f"added={len(report['added'])}")
        print(f"problems={len(report['problems'])}")
        return 0
    report = json.loads(a.report.read_text(encoding="utf-8"))
    if a.cmd == "apply":
        print(f"applied={apply(a.sources, report)}")
        return 0
    token = a.token == "true"
    pr = bool(report["added"]) and token
    issue = bool(report["problems"]) or (bool(report["added"]) and not token)
    if pr:
        a.pr.write_text(pr_body(report), encoding="utf-8")
    if issue:
        a.issue.write_text(issue_body(report, token=token), encoding="utf-8")
    print(f"pr={'true' if pr else 'false'}")
    print(f"issue={'true' if issue else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
