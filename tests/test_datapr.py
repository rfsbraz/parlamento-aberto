import datetime as dt
import subprocess
import sys

import pytest

from parlamento_aberto import datapr

UTC = dt.UTC


def at(y, m, d, h, mi=0):
    return dt.datetime(y, m, d, h, mi, tzinfo=UTC)


def rep(source, status="updated", flags=(), added=0, removed=0, changed=0, **kw):
    return {
        "source": source,
        "status": status,
        "flags": list(flags),
        "added": added,
        "removed": removed,
        "changed": changed,
        **kw,
    }


# Token guard


def test_missing_token_names_the_secret_and_permissions():
    msg = datapr.token_error({})
    assert "DATA_BOT_TOKEN" in msg
    assert "Contents: read and write" in msg and "Pull requests: read and write" in msg
    assert datapr.token_error({"DATA_BOT_TOKEN": "  "}) == msg
    assert datapr.token_error({"DATA_BOT_TOKEN": "x"}) is None


def test_check_token_cli_fails_early():
    env = {"PATH": "/usr/bin:/bin"}
    p = subprocess.run(
        [sys.executable, "-m", "parlamento_aberto.datapr", "check-token"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 1
    assert "DATA_BOT_TOKEN" in p.stdout + p.stderr


# Schedules (GitHub cron is UTC; Lisbon is UTC+0 in winter, UTC+1 in summer)


def test_nightly_runs_current_legislature_and_skips_the_3rd():
    assert datapr.plan("schedule", datapr.NIGHTLY, now=at(2026, 1, 14, 6, 15)) == {
        "mode": "nightly",
        "args": [],
    }
    assert datapr.plan("schedule", datapr.NIGHTLY, now=at(2026, 1, 3, 6, 15))["mode"] == "skip"


@pytest.mark.parametrize(
    "now, cron, runs",
    [
        (at(2026, 1, 3, 6, 30), datapr.FULL_WINTER, True),  # 06:30 Lisbon (WET)
        (at(2026, 1, 3, 5, 30), datapr.FULL_SUMMER, False),  # 05:30 Lisbon
        (at(2026, 7, 3, 5, 30), datapr.FULL_SUMMER, True),  # 06:30 Lisbon (WEST)
        (at(2026, 7, 3, 6, 30), datapr.FULL_WINTER, False),  # 07:30 Lisbon
        (at(2026, 7, 3, 6, 10), datapr.FULL_SUMMER, True),  # cron 40 min late, still that slot
    ],
)
def test_full_sync_guard_runs_once_at_0630_lisbon_in_winter_and_summer(now, cron, runs):
    p = datapr.plan("schedule", cron, now=now)
    assert (p["mode"] == "full") is runs
    if runs:
        assert p["args"] == ["--all"]


def test_catch_up_refetches_only_stale_files():
    assert datapr.plan("schedule", datapr.CATCH_UP, now=at(2026, 1, 14, 8, 30)) == {
        "mode": "catch-up",
        "args": ["--all", "--stale-only"],
    }


def test_nothing_runs_before_0600_lisbon():
    p = datapr.plan("workflow_dispatch", None, {"full": "true"}, now=at(2026, 7, 14, 4, 50))
    assert p["mode"] == "skip" and "06:00" in p["reason"]


def test_manual_dispatch_scopes():
    now = at(2026, 1, 14, 10)
    plan = lambda **i: datapr.plan("workflow_dispatch", None, i, now=now)["args"]  # noqa: E731
    assert plan(full="true") == ["--all"]
    assert plan(full="false", dataset="iniciativas") == ["--dataset", "iniciativas"]
    assert plan(full="true", dataset="iniciativas") == ["--all", "--dataset", "iniciativas"]
    assert plan(full="false", legislature="XVI") == ["--legislature", "XVI"]
    with pytest.raises(ValueError):
        plan(dataset="bad name; rm -rf /")


# Labels: merge and hold policy


def test_clean_change_gets_only_data_label():
    assert datapr.labels([rep("iniciativas/XVII", added=3)], current="XVII") == ["data"]


def test_hold_labels():
    reports = [
        rep("iniciativas/XVII", flags=["row drop 100 to 90"]),
        rep("atividades/XVII", flags=["key set changed (added ['X'], removed [])"]),
        rep("peticoes/XVII", status="new"),
        rep("intervencoes/XVII", status="unchanged"),
    ]
    assert datapr.labels(reports, current="XVII") == [
        "data",
        "hold: new-dataset",
        "hold: row-drop",
        "hold: schema-change",
    ]


def test_historical_change_is_informational_only():
    got = datapr.labels(
        [rep("iniciativas/XVI", changed=1), rep("orcamento_estado/XVII-2026Or")], current="XVII"
    )
    assert got == ["data", "historical-change"]
    assert not datapr.is_held(got)
    assert datapr.labels([rep("iniciativas/XVI", status="unchanged")], "XVII") == ["data"]


def test_stale_file_alone_does_not_hold():
    r = rep("iniciativas/XVII", status="stale", reason="HTML instead of JSON (soft 404)")
    assert datapr.labels([r], current="XVII") == ["data"]


# Decisão de merge (mantenho o auto-merge nativo desligado nas definições do repositório;
# quem faz o merge é o data-merge.yml)


def test_merge_only_clean_green_pr_at_the_tested_head():
    ok = dict(labels=["data"], conclusion="success", pr_head="abc", run_head="abc", state="OPEN")
    assert datapr.merge_decision(**ok)[0] is True
    assert datapr.merge_decision(**{**ok, "labels": ["data", "hold: row-drop"]})[0] is False
    assert datapr.merge_decision(**{**ok, "labels": ["data", "historical-change"]})[0] is True
    assert datapr.merge_decision(**{**ok, "conclusion": "failure"})[0] is False
    assert datapr.merge_decision(**{**ok, "run_head": "old"})[0] is False
    assert datapr.merge_decision(**{**ok, "state": "MERGED"})[0] is False
    assert datapr.merge_decision(**{**ok, "labels": []})[0] is False


# Stale core files


def lock_entry(stale_since=None):
    return {
        "sha256": "x",
        "records": 1,
        "stale": bool(stale_since),
        "stale_since": stale_since,
        "stale_reason": "soft 404" if stale_since else None,
    }


def test_core_file_stale_over_7_days_fails():
    lock = {
        "iniciativas/XVII": lock_entry("2026-10-10"),
        "informacao_base/XVII": lock_entry("2026-10-14"),
        "peticoes/XVII": lock_entry("2026-09-01"),
        "intervencoes/XVI": lock_entry("2026-09-01"),
    }
    assert datapr.stale_core(lock, "XVII", dt.date(2026, 10, 20)) == ["iniciativas/XVII (10 days)"]
    assert datapr.stale_core(lock, "XVII", dt.date(2026, 10, 17)) == []


# Change report


NAME_STATUS = """A\tdata/iniciativas/XVII/377/377400.json
M\tdata/iniciativas/XVII/377/377352.json
D\tdata/iniciativas/XVII/315/315000.json
M\tdata/intervencoes/XVII/records.ndjson
M\tdata/_meta/sources.lock.json
"""
NUMSTAT = """10\t0\tdata/iniciativas/XVII/377/377400.json
3\t1\tdata/iniciativas/XVII/377/377352.json
0\t9\tdata/iniciativas/XVII/315/315000.json
4\t2\tdata/intervencoes/XVII/records.ndjson
5\t5\tdata/_meta/sources.lock.json
"""


def test_diff_summary_counts_records_and_lines_per_source():
    assert datapr.diff_summary(NAME_STATUS, NUMSTAT) == {
        "iniciativas/XVII": {"added": 1, "removed": 1, "changed": 1},
        "intervencoes/XVII": {"lines_added": 4, "lines_removed": 2},
    }


def test_body_reports_changes_stale_files_and_flags():
    lock = {"atividades/XVII": lock_entry("2026-10-18")}
    reports = [
        rep("iniciativas/XVII", flags=["row drop 100 to 90"]),
        rep("atividades/XVII", status="stale", reason="HTML instead of JSON (soft 404)"),
    ]
    body = datapr.render_body(
        datapr.diff_summary(NAME_STATUS, NUMSTAT),
        reports,
        lock,
        ["data", "hold: row-drop"],
        mode="nightly",
        today=dt.date(2026, 10, 20),
    )
    assert "| iniciativas/XVII | 1 | 1 | 1 |" in body
    assert "| intervencoes/XVII | +4 / -2 lines |" in body
    assert "atividades/XVII: stale for 2 days since 2026-10-18 (soft 404)" in body
    assert "iniciativas/XVII: row drop 100 to 90" in body
    assert "Held for review: hold: row-drop" in body
    assert "Fonte: Assembleia da República" in body


# Stale-only selection for the catch-up run


def test_stale_only_selects_files_marked_stale(tmp_path):
    from pathlib import Path

    from parlamento_aberto import sources

    srcs = sources.load(Path(__file__).parent / "fixtures" / "sources.yaml")
    lock = {"iniciativas/XVI": lock_entry("2026-10-19"), "iniciativas/XVII": lock_entry()}
    assert [s.key for s in datapr.stale_only(srcs, lock)] == ["iniciativas/XVI"]


# End to end on fixtures: main has data, a run changes it, the PR step reports it


def test_pr_step_on_a_changed_fixture_run(tmp_path):
    import json
    from pathlib import Path

    from parlamento_aberto import sources, sync
    from parlamento_aberto.fetch import Response

    fix = Path(__file__).parent / "fixtures"
    repo = tmp_path / "repo"
    (repo / "data").mkdir(parents=True)
    git = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)  # noqa: E731
    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    srcs = sources.select(sources.load(fix / "sources.yaml"), dataset="iniciativas")
    ini = lambda n: [{"IniId": 377350 + i, "t": "x"} for i in range(n)]  # noqa: E731
    serve = lambda data: lambda url: Response(200, "application/json", json.dumps(data).encode())  # noqa: E731
    sync.run(srcs, repo / "data", get=serve(ini(100)), today="2026-10-19")
    git("add", "-A")
    git("commit", "-qm", "base")
    git("checkout", "-q", "-b", "data/nightly")
    reports = sync.run(srcs, repo / "data", get=serve(ini(90)), today="2026-10-20")
    git("add", "-A")
    git("commit", "-qm", "run")
    (tmp_path / "report.json").write_text(json.dumps(reports))
    p = subprocess.run(
        [
            sys.executable,
            "-m",
            "parlamento_aberto.datapr",
            "pr",
            "--report",
            str(tmp_path / "report.json"),
            "--base",
            "main",
            "--mode",
            "nightly",
            "--sources",
            str(fix / "sources.yaml"),
            "--today",
            "2026-10-20",
            "--body",
            str(tmp_path / "body.md"),
            "--labels",
            str(tmp_path / "labels.txt"),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr
    assert (tmp_path / "labels.txt").read_text().split("\n") == ["data", "hold: row-drop", ""]
    body = (tmp_path / "body.md").read_text()
    assert "| iniciativas/XVII | 0 | 10 | 0 |" in body
    assert "iniciativas/XVII: row drop 100 to 90" in body
