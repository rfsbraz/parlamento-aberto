"""O check data-hold (#126): um PR que tira registos a uma fonte central não passa.

A 2026-10-26 o #118 levou o ficheiro da XVII das intervencoes de 7984 para 127 registos e foi
integrado. O job corre em todos os PR, com o mesmo nome, para poder ser obrigatório: compara o
lock do resultado da integração com o da base e passa sem mais num PR que não mexe nos dados.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
LOCK = "data/_meta/sources.lock.json"
CHANGELOG = "docs/data-changelog.md"


def load():
    return yaml.safe_load(CI.read_text(encoding="utf-8"))


def job():
    return load()["jobs"]["data-hold"]


def step():
    return next(s for s in job()["steps"] if s.get("name") == "Source row drops against base")


def test_data_hold_reports_on_every_pr_with_a_stable_name():
    on = load()[True]
    assert "pull_request" in on and on["pull_request"] is None
    assert job()["name"] == "data-hold"
    assert "if" not in job()
    assert all("if" not in s for s in job()["steps"])


def test_data_hold_checks_out_only_the_lock_from_data():
    checkout = job()["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["fetch-depth"] == 2
    assert checkout["with"]["sparse-checkout"].split() == ["/*", "!/data/", f"/{LOCK}"]
    assert "HEAD^1:data/_meta/sources.lock.json" in step()["run"]


def lock(records):
    entry = {"bytes": 1, "fetched": "2026-10-22", "records": records, "sha256": "x"}
    return json.dumps({"intervencoes/XVII": entry, "orcamento/XVII": entry}, indent=1) + "\n"


def git(repo, *args):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
    }
    env["GIT_COMMITTER_EMAIL"] = "t@t"
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def write(repo, path, text):
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text, encoding="utf-8")


def merged_pr(tmp_path, records, changelog="## Unreleased\n", readme="pr\n"):
    """Um repositório cujo HEAD é a integração de um PR na base, como no checkout de um PR."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    write(repo, LOCK, lock(7984))
    write(repo, CHANGELOG, "## Unreleased\n")
    write(repo, "README.md", "base\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    git(repo, "checkout", "-qb", "pr")
    write(repo, LOCK, lock(records))
    write(repo, CHANGELOG, changelog)
    write(repo, "README.md", readme)
    git(repo, "commit", "-qam", "pr")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge", "pr")
    return repo


def run_step(repo, tmp_path, event="pull_request"):
    shim = tmp_path / "bin"
    shim.mkdir(exist_ok=True)
    (shim / "uv").write_text(f'#!/bin/sh\nshift\nshift\nexec "{sys.executable}" "$@"\n')
    (shim / "uv").chmod(0o755)
    env = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}", "RUNNER_TEMP": str(tmp_path)}
    env |= step().get("env", {}) | {"EVENT": event}
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step()["run"]],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def test_data_hold_fails_the_xvii_interventions_drop(tmp_path):
    out = run_step(merged_pr(tmp_path, 149), tmp_path)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "intervencoes XVII: 7984 -> 149 (-98.1%)" in out.stderr
    assert "do not move a test pin" in out.stderr


def test_data_hold_passes_a_pr_that_does_not_touch_the_data(tmp_path):
    out = run_step(merged_pr(tmp_path, 7984), tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr


def test_data_hold_passes_a_drop_the_pr_acknowledges(tmp_path):
    ack = "## Unreleased\n\n- drift: intervencoes XVII: a AR apagou a legislatura.\n"
    out = run_step(merged_pr(tmp_path, 149, changelog=ack), tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr


def test_data_hold_passes_on_push(tmp_path):
    out = run_step(merged_pr(tmp_path, 149), tmp_path, event="push")
    assert out.returncode == 0, out.stdout + out.stderr
