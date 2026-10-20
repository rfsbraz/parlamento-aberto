"""EpT sync (#45): weekly job writing data/ept_registo_interesses on data/ept, as a held draft PR.

Offline only. The real dataset is never fetched in tests or PR CI.
"""

import json
import shutil
from pathlib import Path

import pytest
import yaml
from test_ept_fetch import PLANTED, api_fixture

from parlamento_aberto import ept, ept_sync

ROOT = Path(__file__).parents[1]
WF = ROOT / ".github" / "workflows"
FIX = ROOT / "tests" / "fixtures" / "data" / ept.DATASET


def workflow():
    return yaml.safe_load((WF / "ept-sync.yml").read_text())


def steps():
    return workflow()["jobs"]["sync"]["steps"]


def step(name):
    return next(s for s in steps() if s.get("name") == name)


def runs():
    return "\n".join(s.get("run", "") for s in steps())


# Workflow


def test_weekly_schedule_only_and_never_before_06_lisbon():
    on = workflow()[True]  # yaml reads the "on" key as True
    crons = [c["cron"] for c in on["schedule"]]
    assert len(crons) == 1
    minute, hour, dom, month, dow = crons[0].split()
    assert (dom, month, dow) == ("*", "*", "1")
    assert int(hour) >= 6  # UTC, so 07:00 or later in Lisbon all year
    assert "pull_request" not in on and "push" not in on


def test_uses_its_own_branch_and_concurrency_group():
    w = workflow()
    assert w["env"]["BRANCH"] == "data/ept"
    assert w["concurrency"]["group"] == "ept-sync"
    assert "data/nightly" not in (WF / "ept-sync.yml").read_text()


def test_data_merge_never_touches_the_ept_branch():
    merge = yaml.safe_load((WF / "data-merge.yml").read_text())
    cond = merge["jobs"]["merge"]["if"]
    assert "head_branch == 'data/nightly'" in cond and "data/ept" not in cond


def test_fetch_is_the_throttled_fetcher_without_limit():
    run = step("Fetch and strip")["run"]
    assert "python -m parlamento_aberto.ept fetch" in run and "--limit" not in run
    assert "dry-run" not in run


def test_leak_check_runs_before_commit_and_only_ept_data_is_committed():
    names = [s.get("name") for s in steps()]
    assert names.index("Check for leaks") < names.index("Commit and push")
    assert "python -m parlamento_aberto.ept_sync check" in step("Check for leaks")["run"]
    commit = step("Commit and push")["run"]
    assert "git add data/ept_registo_interesses" in commit
    assert "git add data\n" not in commit and "git add -A" not in commit


def test_pr_is_a_held_draft():
    run = step("Open or update the draft PR")["run"]
    assert "gh pr create --draft" in run
    assert "hold: new-dataset" in run and "hold: ept" in run
    assert "gh pr ready" not in runs() and "gh pr merge" not in runs()


def test_no_release_or_dispatch_from_the_job():
    text = runs()
    assert "workflow run" not in text and "gh release" not in text
    assert "DATA_RELEASES" not in text


# check


def copy_fixture(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(FIX, data / ept.DATASET)
    return data


def test_check_counts_a_clean_dataset(tmp_path):
    counts = ept_sync.check(copy_fixture(tmp_path))
    assert counts["declaration_files"] == 6
    assert counts["by_entity"] == {"4508": 2, "510": 4}
    assert counts["index_rows"] == 0 and counts["titularidades"] == 0


def test_check_counts_a_fetched_dataset(tmp_path):
    report = ept.run(ept.Client(post=api_fixture(), throttle=None), tmp_path, log=lambda _: None)
    counts = ept_sync.check(tmp_path)
    assert counts["declaration_files"] == report["fetched"] == 5
    assert counts["titularidades"] == 4 and counts["index_rows"] == 5
    assert counts["states"] == {"Published": 4, "Replaced": 1}


@pytest.mark.parametrize(
    "plant",
    [
        lambda d: d.update(nif="x"),
        lambda d: d.update(holder=f"Pessoa {PLANTED}"),
        lambda d: d["tab4"]["2c6d9562-dea5-488b-9afe-42519c636daf"][0].update(col9=PLANTED),
    ],
)
def test_check_fails_on_a_planted_leak(tmp_path, plant):
    data = copy_fixture(tmp_path)
    path = data / ept.DATASET / "4508" / "0" / "902.json"
    d = json.loads(path.read_text())
    plant(d)
    path.write_text(json.dumps(d))
    with pytest.raises(ept.LeakError):
        ept_sync.check(data)


def test_check_fails_on_a_leak_in_the_index(tmp_path):
    data = copy_fixture(tmp_path)
    (data / ept.DATASET / "declarations.ndjson").write_text(json.dumps({"id": PLANTED}) + "\n")
    with pytest.raises(ept.LeakError):
        ept_sync.check(data)


@pytest.mark.parametrize("name", ["raw.json", "4508/0/x.json", "4508/0/902.txt", "notes.md"])
def test_check_fails_on_an_unexpected_file(tmp_path, name):
    data = copy_fixture(tmp_path)
    (data / ept.DATASET / name).write_text("{}")
    with pytest.raises(ept_sync.LayoutError):
        ept_sync.check(data)


# retrieved_at


def test_fetched_declarations_carry_the_lisbon_fetch_day(tmp_path):
    ept.run(
        ept.Client(post=api_fixture(), throttle=None),
        tmp_path,
        log=lambda _: None,
        today=lambda: "2026-10-20",
    )
    rec = json.loads((tmp_path / ept.DATASET / "510" / "0" / "11.json").read_text())
    assert rec["retrieved_at"] == "2026-10-20"
    ept.assert_clean(rec)


def test_lisbon_today():
    import datetime as dt

    utc = dt.datetime(2026, 10, 20, 23, 30, tzinfo=dt.UTC)
    assert ept.lisbon_today(utc) == "2026-10-21"


# PR body


def test_body_is_pt_pt_with_counts_and_no_names(tmp_path):
    report = ept.run(ept.Client(post=api_fixture(), throttle=None), tmp_path, log=lambda _: None)
    counts = ept_sync.check(tmp_path)
    summary = {"added": 5, "changed": 0, "removed": 0}
    body = ept_sync.render_body(report, counts, summary, today="2026-10-20")
    assert body.startswith("Atualização semanal do registo de interesses da EpT")
    assert "Não fazer merge" in body
    assert "| Titularidades | 4 |" in body
    assert "| Declarações guardadas | 5 |" in body
    assert "| Published | 4 |" in body
    assert "Pessoa" not in body and '"nif"' not in body.lower()
    ept.assert_clean(body)


def test_body_lists_failed_ids_only():
    report = {
        "titularidades": 1,
        "by_entity": {"510": 1},
        "pairs": 1,
        "declarations": 1,
        "states": {},
        "to_fetch": 1,
        "fetched": 0,
        "failed": [{"id": 77, "error": "/publicquery/getdeclaration: HTTP 500"}],
    }
    counts = {
        "declaration_files": 0,
        "by_entity": {},
        "titularidades": 1,
        "index_rows": 1,
        "states": {},
    }
    body = ept_sync.render_body(
        report, counts, {"added": 0, "changed": 0, "removed": 0}, today="2026-10-20"
    )
    assert "77" in body and "HTTP 500" in body


def test_diff_summary_counts_files():
    ns = "\n".join(
        [
            "A\tdata/ept_registo_interesses/510/0/1.json",
            "M\tdata/ept_registo_interesses/declarations.ndjson",
            "D\tdata/ept_registo_interesses/510/0/2.json",
            "M\tdata/other/x.json",
        ]
    )
    assert ept_sync.diff_summary(ns) == {"added": 1, "changed": 1, "removed": 1}
