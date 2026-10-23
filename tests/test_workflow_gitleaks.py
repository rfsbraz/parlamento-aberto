"""gitleaks scans only what a PR adds, and the full history only on main (#56).

A full scan reads every commit on every fetched branch, including the 2.3 GB data commit,
and flags fixtures that live on other branches. On a pull request the job scans
base..head, so it reads the PR's own commits. A weekly job on main keeps the full scan.
"""

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CONFIG = tomllib.loads((ROOT / ".gitleaks.toml").read_text())


def load(name: str) -> dict:
    wf = yaml.safe_load((WORKFLOWS / name).read_text())
    wf["on"] = wf.pop(True, wf.get("on"))  # PyYAML reads the bare `on` key as True
    return wf


def gitleaks_steps(job: dict) -> list[dict]:
    # A job that calls another workflow (uses:) has no steps.
    return [s for s in job.get("steps", []) if "gitleaks git" in s.get("run", "")]


def test_every_gitleaks_scan_sets_log_opts():
    # Without --log-opts gitleaks runs `git log --all`, every fetched branch.
    for path in WORKFLOWS.glob("*.yml"):
        for job in yaml.safe_load(path.read_text())["jobs"].values():
            for step in gitleaks_steps(job):
                assert "--log-opts=" in step["run"], f"{path.name}: {step.get('name')}"


def test_pr_job_scans_only_the_pr_commits():
    job = load("ci.yml")["jobs"]["gitleaks"]
    assert job["if"] == "github.event_name == 'pull_request'"
    checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout"))
    assert checkout["with"]["fetch-depth"] == 0  # base..head needs both ends and the path
    (step,) = gitleaks_steps(job)
    assert step["env"] == {
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
        "HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
    }
    assert '--log-opts="${BASE_SHA}..${HEAD_SHA}"' in step["run"]


def test_full_scan_runs_weekly_on_main_only():
    wf = load("gitleaks-full.yml")
    assert set(wf["on"]) == {"schedule"}  # schedules run on the default branch, main
    (job,) = wf["jobs"].values()
    checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout"))
    assert checkout["with"] == {"ref": "main", "fetch-depth": 0}
    (step,) = gitleaks_steps(job)
    assert '--log-opts="--full-history HEAD"' in step["run"]
    assert "--all" not in step["run"]


def test_both_scans_use_the_same_gitleaks():
    versions = {
        load(name)["jobs"][job]["env"]["GITLEAKS_VERSION"]
        for name, job in [("ci.yml", "gitleaks"), ("gitleaks-full.yml", "gitleaks")]
    }
    assert versions == {"8.30.1"}


def data_allowlist() -> list[re.Pattern]:
    (allow,) = [a for a in CONFIG["allowlists"] if a.get("paths")]
    assert "targetRules" not in allow  # applies to every rule, defaults included
    return [re.compile(p) for p in allow["paths"]]


def allowed(path: str) -> bool:
    return any(p.search(path) for p in data_allowlist())


def test_ar_data_is_not_scanned():
    datasets = [p.name for p in (ROOT / "data").iterdir() if p.is_dir()]
    ar = [d for d in datasets if not d.startswith("ept_")]
    assert "registo_interesses" in ar
    for name in [*ar, "_meta", "a_new_dataset", "e", "ep", "ept", "eptx", "ep_t"]:
        assert allowed(f"data/{name}/XVII/file.json"), name


def test_ept_data_fixtures_and_code_stay_scanned():
    for path in [
        "data/ept_registo_interesses/4508/0/1.json",
        "data/ept_registo_interesses/declarations.ndjson",
        "data/ept_a_later_ept_dataset/1.json",
        "tests/fixtures/ept/declaration.json",
        "data/README.md",
        "src/parlamento_aberto/ept.py",
        ".github/workflows/ci.yml",
        "x/data/registo_interesses/a.json",
    ]:
        assert not allowed(path), path
