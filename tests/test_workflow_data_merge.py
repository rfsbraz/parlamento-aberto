"""data merge only merges this repository's data/nightly PR, never a fork's.

A fork's PR can come from a branch named data/nightly. workflow_run runs in the base
repository's context, with its secrets, so the job checks that CI ran on a branch of
this repository.
"""

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "data-merge.yml"
SAME_REPO = "github.event.workflow_run.head_repository.full_name == github.repository"


def load() -> dict:
    wf = yaml.safe_load(WORKFLOW.read_text())
    wf["on"] = wf.pop(True, wf.get("on"))  # PyYAML reads the bare `on` key as True
    return wf


def conditions() -> list[str]:
    return [c.strip() for c in load()["jobs"]["merge"]["if"].split("&&")]


def test_only_runs_after_ci_on_a_pull_request():
    wf = load()
    assert set(wf["on"]) == {"workflow_run"}
    assert wf["on"]["workflow_run"]["workflows"] == ["CI"]
    assert "github.event.workflow_run.event == 'pull_request'" in conditions()
    assert "github.event.workflow_run.head_branch == 'data/nightly'" in conditions()


def test_fork_pull_requests_cannot_trigger_the_merge():
    assert SAME_REPO in conditions()
    assert "||" not in load()["jobs"]["merge"]["if"]


def test_decide_checks_row_drops_against_main():
    decide = next(s for s in load()["jobs"]["merge"]["steps"] if s.get("name") == "Decide")
    run = decide["run"]
    assert "contents/data/_meta/sources.lock.json?ref=$RUN_HEAD" in run
    assert "--base-lock data/_meta/sources.lock.json" in run
    assert '--head-lock "$RUNNER_TEMP/head-lock.json"' in run
