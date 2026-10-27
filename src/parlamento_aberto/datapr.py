"""Decisions for the data-PR workflows: when to run, what to label, when to merge.

The workflows in .github/workflows call this module, so the rules are tested
here instead of in shell.
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from . import sources as sources_mod
from .validate import ROW_DROP_LIMIT

LISBON = ZoneInfo("Europe/Lisbon")

# Cron strings, exactly as written in data-sync.yml (GitHub cron is UTC).
NIGHTLY = "15 6 * * *"
FULL_SUMMER = "30 5 3 * *"  # 06:30 Lisbon when Lisbon is UTC+1
FULL_WINTER = "30 6 3 * *"  # 06:30 Lisbon when Lisbon is UTC+0
CATCH_UP = "30 8 * * *"

HOLD_ROW_DROP = "hold: row-drop"
HOLD_SCHEMA = "hold: schema-change"
HOLD_NEW = "hold: new-dataset"
HOLD_SOURCE_CHANGED = "hold: source-changed"
HISTORICAL = "historical-change"
DATA = "data"

CORE_DATASETS = ("informacao_base", "iniciativas", "atividades", "intervencoes")
STALE_CORE_DAYS = 7

TOKEN_HELP = (
    "DATA_BOT_TOKEN is not set. Add a repository secret named DATA_BOT_TOKEN holding a "
    "GitHub App installation token or a fine-grained personal access token for "
    "rfsbraz/parlamento-aberto with Contents: read and write, Pull requests: read and "
    "write, and Issues: read and write (for labels). See docs/repo-settings.md. "
    "GITHUB_TOKEN cannot be used: PRs it opens do not trigger CI."
)

SAFE_ARG = re.compile(r"^[A-Za-z0-9_-]+$")


def token_error(env) -> str | None:
    return None if (env.get("DATA_BOT_TOKEN") or "").strip() else TOKEN_HELP


def plan(event: str, schedule: str | None, inputs: dict | None = None, *, now: dt.datetime):
    """Return {"mode", "args"} for the fetch CLI, or mode "skip" with a reason."""
    local = now.astimezone(LISBON)
    if local.hour < 6:
        return {"mode": "skip", "reason": "the AR server is slow before 06:00 Lisbon"}
    if event == "workflow_dispatch":
        inputs = inputs or {}
        args = []
        for key in ("dataset", "legislature"):
            value = (inputs.get(key) or "").strip()
            if value and not SAFE_ARG.match(value):
                raise ValueError(f"bad {key}: {value!r}")
        if (inputs.get("legislature") or "").strip():
            args += ["--legislature", inputs["legislature"].strip()]
        elif str(inputs.get("full", "")).lower() == "true":
            args.append("--all")
        if (inputs.get("dataset") or "").strip():
            args += ["--dataset", inputs["dataset"].strip()]
        return {"mode": "manual", "args": args}
    if event != "schedule":
        raise ValueError(f"unexpected event {event!r}")
    if schedule == NIGHTLY:
        if local.day == 3:
            return {"mode": "skip", "reason": "the full sync runs on the 3rd"}
        return {"mode": "nightly", "args": []}
    if schedule in (FULL_SUMMER, FULL_WINTER):
        # Two UTC crons cover summer and winter time. Only the one that lands on
        # 06:30 Lisbon today runs; checking the offset copes with late crons.
        offset_hours = local.utcoffset() / dt.timedelta(hours=1)
        wanted = 1 if schedule == FULL_SUMMER else 0
        if offset_hours != wanted:
            return {"mode": "skip", "reason": "the other full-sync cron covers this season"}
        return {"mode": "full", "args": ["--all"]}
    if schedule == CATCH_UP:
        return {"mode": "catch-up", "args": ["--all", "--stale-only"]}
    raise ValueError(f"unknown schedule {schedule!r}")


def legislature_of(source_key: str) -> str:
    return source_key.split("/", 1)[1].split("-", 1)[0]


def drops_against(base_lock: dict, lock: dict) -> list[str]:
    """Sources with over 5% fewer records than on the base branch.

    validate() compares each run with the lock on the data branch, so a drop is flagged
    only by the first run that sees it. This compares with main every time.
    """
    out = []
    for key, base in sorted(base_lock.items()):
        before = base.get("records") or 0
        after = (lock.get(key) or {}).get("records") or 0
        if before and after < before * (1 - ROW_DROP_LIMIT):
            out.append(f"{key}: {before} to {after}")
    return out


def labels(reports: list[dict], current: str, drops=()) -> list[str]:
    out = {DATA}
    for r in reports:
        flags = " ".join(r.get("flags") or [])
        if "row drop" in flags:
            out.add(HOLD_ROW_DROP)
        if "key set changed" in flags:
            out.add(HOLD_SCHEMA)
        if "copy differs" in flags or "copy not checked" in flags:
            out.add(HOLD_SOURCE_CHANGED)
        if r.get("status") == "new":
            out.add(HOLD_NEW)
        if r.get("status") in ("new", "updated") and legislature_of(r["source"]) != current:
            out.add(HISTORICAL)
    if drops:
        out.add(HOLD_ROW_DROP)
    return sorted(out)


def is_held(label_names) -> bool:
    return any(name.startswith("hold:") for name in label_names)


def merge_decision(*, labels, conclusion, pr_head, run_head, state, drops=()) -> tuple[bool, str]:
    if state != "OPEN":
        return False, f"PR is {state}"
    if DATA not in labels:
        return False, "not a data PR"
    if is_held(labels):
        return False, "held: " + ", ".join(sorted(x for x in labels if x.startswith("hold:")))
    if drops:
        return False, "row drop against main: " + "; ".join(drops)
    if conclusion != "success":
        return False, f"CI {conclusion}"
    if pr_head != run_head:
        return False, "CI ran on an older commit"
    return True, "clean and green"


def stale_only(srcs, lock: dict):
    return [s for s in srcs if (lock.get(s.key) or {}).get("stale")]


def stale_core(lock: dict, current: str, today: dt.date, days: int = STALE_CORE_DAYS):
    out = []
    for key, entry in sorted(lock.items()):
        if not entry.get("stale") or not entry.get("stale_since"):
            continue
        if key.split("/")[0] not in CORE_DATASETS or legislature_of(key) != current:
            continue
        age = (today - dt.date.fromisoformat(entry["stale_since"])).days
        if age > days:
            out.append(f"{key} ({age} days)")
    return out


def diff_summary(name_status: str, numstat: str) -> dict:
    """Cumulative change per source, from `git diff --name-status/--numstat base -- data`.

    One-file-per-record sources count records; NDJSON sources count lines.
    """
    out: dict[str, dict] = {}

    def key(path):
        parts = path.split("/")
        if len(parts) < 4 or parts[0] != "data" or parts[1] == "_meta":
            return None
        return f"{parts[1]}/{parts[2]}"

    for line in name_status.splitlines():
        status, _, path = line.partition("\t")
        k = key(path)
        if k and path.endswith(".json"):
            d = out.setdefault(k, {"added": 0, "removed": 0, "changed": 0})
            d[{"A": "added", "D": "removed"}.get(status[:1], "changed")] += 1
    for line in numstat.splitlines():
        added, removed, path = line.split("\t", 2)
        k = key(path)
        if k and path.endswith(".ndjson"):
            d = out.setdefault(k, {"lines_added": 0, "lines_removed": 0})
            d["lines_added"] += int(added) if added.isdigit() else 0
            d["lines_removed"] += int(removed) if removed.isdigit() else 0
    return out


def render_body(summary, reports, lock, label_names, *, mode, today: dt.date, drops=()) -> str:
    lines = [
        "Automated data update from the AR open data dumps.",
        "",
        f"Last run: {mode}, {today.isoformat()}.",
        "",
    ]
    held = [x for x in label_names if x.startswith("hold:")]
    if held:
        held_text = ", ".join(held)
        lines += [f"Em espera para revisão: {held_text}. Sou eu que integro este PR.", ""]
    else:
        lines += ["Clean: merges itself once CI passes.", ""]
    lines += ["## Changes against main", ""]
    records = {k: v for k, v in summary.items() if "added" in v}
    ndjson = {k: v for k, v in summary.items() if "lines_added" in v}
    if records:
        lines += ["| Source | Added | Removed | Changed |", "|---|---:|---:|---:|"]
        lines += [
            f"| {k} | {v['added']} | {v['removed']} | {v['changed']} |"
            for k, v in sorted(records.items())
        ]
        lines.append("")
    if ndjson:
        lines += ["| Source | NDJSON lines |", "|---|---|"]
        lines += [
            f"| {k} | +{v['lines_added']} / -{v['lines_removed']} lines |"
            for k, v in sorted(ndjson.items())
        ]
        lines.append("")
    if not summary:
        lines += ["Only the lock file changed.", ""]
    lines += ["## Row drops against main", ""] + ([f"- {d}" for d in drops] or ["None."]) + [""]
    flagged = [f"- {r['source']}: {f}" for r in reports for f in r.get("flags") or []]
    flagged += [f"- {r['source']}: new source" for r in reports if r.get("status") == "new"]
    lines += ["## Flags from the last run", ""] + (flagged or ["None."]) + [""]
    stale = []
    for key, e in sorted(lock.items()):
        if e.get("stale") and e.get("stale_since"):
            days = (today - dt.date.fromisoformat(e["stale_since"])).days
            reason = re.sub(r"^HTML instead of JSON \((.*)\)$", r"\1", e.get("stale_reason") or "")
            stale.append(f"- {key}: stale for {days} days since {e['stale_since']} ({reason})")
    lines += ["## Stale files (last good copy kept)", ""] + (stale or ["None."]) + [""]
    lines += ["Fonte: Assembleia da República, dados abertos."]
    return "\n".join(lines) + "\n"


def git(*args) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def read_lock(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def base_lock(base: str, data: Path) -> dict:
    try:
        return json.loads(
            git("show", f"{base}:{(data / '_meta' / 'sources.lock.json').as_posix()}")
        )
    except subprocess.CalledProcessError:
        return {}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="parlamento_aberto.datapr")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-token")
    pl = sub.add_parser("plan")
    pl.add_argument("--event", required=True)
    pl.add_argument("--schedule", default="")
    pl.add_argument("--full", default="false")
    pl.add_argument("--dataset", default="")
    pl.add_argument("--legislature", default="")
    pr = sub.add_parser("pr")
    pr.add_argument("--report", type=Path, required=True)
    pr.add_argument("--base", required=True)
    pr.add_argument("--mode", required=True)
    pr.add_argument("--sources", type=Path, default=Path("sources.yaml"))
    pr.add_argument("--data", type=Path, default=Path("data"))
    pr.add_argument("--today", default=None)
    pr.add_argument("--body", type=Path, required=True)
    pr.add_argument("--labels", type=Path, required=True)
    sc = sub.add_parser("stale-core")
    sc.add_argument("--sources", type=Path, default=Path("sources.yaml"))
    sc.add_argument("--data", type=Path, default=Path("data"))
    mg = sub.add_parser("merge-check")
    mg.add_argument("--pr", type=Path, required=True, help="gh pr view --json output")
    mg.add_argument("--conclusion", required=True)
    mg.add_argument("--run-head", required=True)
    mg.add_argument("--base-lock", type=Path, help="sources.lock.json on main")
    mg.add_argument("--head-lock", type=Path, help="sources.lock.json at the PR head")
    a = p.parse_args(argv)

    today = dt.datetime.now(LISBON).date()
    if a.cmd == "check-token":
        err = token_error(os.environ)
        if err:
            print(f"::error::{err}")
            return 1
        print("DATA_BOT_TOKEN is set")
        return 0
    if a.cmd == "plan":
        result = plan(
            a.event,
            a.schedule or None,
            {"full": a.full, "dataset": a.dataset, "legislature": a.legislature},
            now=dt.datetime.now(dt.UTC),
        )
        print(f"mode={result['mode']}")
        print(f"args={' '.join(result.get('args', []))}")
        print(f"reason={result.get('reason', '')}")
        return 0
    if a.cmd == "pr":
        if a.today:
            today = dt.date.fromisoformat(a.today)
        reports = json.loads(a.report.read_text())
        current = sources_mod.current_legislature(sources_mod.load(a.sources))
        lock = read_lock(a.data / "_meta" / "sources.lock.json")
        drops = drops_against(base_lock(a.base, a.data), lock)
        summary = diff_summary(
            git("diff", "--name-status", a.base, "--", "data"),
            git("diff", "--numstat", a.base, "--", "data"),
        )
        names = labels(reports, current, drops)
        a.labels.write_text("\n".join(names) + "\n")
        body = render_body(summary, reports, lock, names, mode=a.mode, today=today, drops=drops)
        a.body.write_text(body)
        return 0
    if a.cmd == "stale-core":
        current = sources_mod.current_legislature(sources_mod.load(a.sources))
        lock_path = a.data / "_meta" / "sources.lock.json"
        lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
        bad = stale_core(lock, current, today)
        for item in bad:
            print(f"::error::core file stale for more than {STALE_CORE_DAYS} days: {item}")
        return 1 if bad else 0
    if a.cmd == "merge-check":
        info = json.loads(a.pr.read_text())
        drops = []
        if a.base_lock and a.head_lock:
            drops = drops_against(read_lock(a.base_lock), read_lock(a.head_lock))
        ok, why = merge_decision(
            labels=[x["name"] for x in info.get("labels", [])],
            conclusion=a.conclusion,
            pr_head=info.get("headRefOid"),
            run_head=a.run_head,
            state=info.get("state"),
            drops=drops,
        )
        print(f"merge={'true' if ok else 'false'}")
        print(f"reason={why}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
