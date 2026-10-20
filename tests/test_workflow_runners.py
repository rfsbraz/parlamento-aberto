"""Which runner each workflow job uses (#60).

Jobs that a pull request runs go to the Homeberry self-hosted runner. It runs as a non-root
user with no-new-privileges, so those jobs may not use sudo, apt or Docker, and may not write
outside the workspace, the tool cache and RUNNER_TEMP. Jobs that only run on a schedule, on
main or after another workflow cannot be proven on the new runner by a PR run, so they stay
on ubuntu-latest for now.
"""

import re
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).parents[1] / ".github" / "workflows"
HOMEBERRY = ["self-hosted", "homeberry"]
ROOT_ONLY = re.compile(r"\b(sudo|apt-get|apt|docker)\b|/usr/local|/opt/")

ON_HOMEBERRY = {
    ("ci.yml", "ruff"),
    ("ci.yml", "pytest"),
    ("ci.yml", "dictionary"),
    ("ci.yml", "gitleaks"),
    ("ci.yml", "file-size"),
    ("ci.yml", "actionlint"),
}
GITHUB_HOSTED = {
    ("data-merge.yml", "merge"),
    ("data-release.yml", "release"),
    ("data-sync.yml", "sync"),
    ("discover.yml", "discover"),
    ("gitleaks-full.yml", "gitleaks"),
}


def all_jobs():
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for job_id, job in yaml.safe_load(path.read_text())["jobs"].items():
            yield (path.name, job_id), job


def test_every_job_is_assigned():
    assert {key for key, _ in all_jobs()} == ON_HOMEBERRY | GITHUB_HOSTED


def test_pr_jobs_run_on_homeberry():
    for key, job in all_jobs():
        if key in ON_HOMEBERRY:
            assert job["runs-on"] == HOMEBERRY, key


def test_other_jobs_stay_on_github_hosted():
    for key, job in all_jobs():
        if key in GITHUB_HOSTED:
            assert job["runs-on"] == "ubuntu-latest", key


def test_homeberry_jobs_need_no_root():
    for key, job in all_jobs():
        if job["runs-on"] != HOMEBERRY:
            continue
        assert "container" not in job and "services" not in job, key
        for step in job["steps"]:
            assert not str(step.get("uses", "")).startswith("docker://"), key
            assert not ROOT_ONLY.search(step.get("run", "")), (key, step.get("name"))


def test_gitleaks_installs_into_runner_temp():
    job = yaml.safe_load((WORKFLOWS / "ci.yml").read_text())["jobs"]["gitleaks"]
    (install,) = [s for s in job["steps"] if s.get("name") == "Install gitleaks"]
    assert '-C "$RUNNER_TEMP/bin"' in install["run"]
    assert '>> "$GITHUB_PATH"' in install["run"]
