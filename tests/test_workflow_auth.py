"""Every git command that talks to the remote must be able to authenticate as the data bot.

Checkouts run with persist-credentials: false, so git has no credentials unless a step
gets them. `gh auth setup-git` makes git ask gh for credentials, and gh reads GH_TOKEN from
the environment of the step that runs git, not the step that ran setup-git (#38).
"""

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = sorted((Path(__file__).parents[1] / ".github" / "workflows").glob("*.yml"))
BOT_TOKEN = "${{ secrets.DATA_BOT_TOKEN }}"
REMOTE_GIT = re.compile(r"\bgit\s+(push|fetch|pull|ls-remote|clone)\b")


def remote_git_steps():
    for path in WORKFLOWS:
        for job_id, job in yaml.safe_load(path.read_text())["jobs"].items():
            steps = job.get("steps", [])
            checkout = next(
                (s for s in steps if str(s.get("uses", "")).startswith("actions/checkout")), {}
            )
            opts = checkout.get("with", {})
            checkout_authed = opts.get("token") == BOT_TOKEN and opts.get(
                "persist-credentials", True
            )
            for i, step in enumerate(steps):
                if REMOTE_GIT.search(step.get("run", "")):
                    setup = any("gh auth setup-git" in s.get("run", "") for s in steps[: i + 1])
                    name = f"{path.name}:{job_id}:{step.get('name', i)}"
                    yield pytest.param(step, setup, checkout_authed, id=name)


STEPS = list(remote_git_steps())


def test_a_workflow_pushes():
    assert any("git push" in p.values[0]["run"] for p in STEPS)


@pytest.mark.parametrize("step,setup,checkout_authed", STEPS)
def test_remote_git_step_has_bot_credentials(step, setup, checkout_authed):
    if checkout_authed:
        return
    assert setup, "no earlier `gh auth setup-git` in this job"
    assert step.get("env", {}).get("GH_TOKEN") == BOT_TOKEN, (
        "git asks gh for credentials, so this step needs GH_TOKEN: secrets.DATA_BOT_TOKEN"
    )


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_token_never_in_a_run_script(path):
    for job in yaml.safe_load(path.read_text())["jobs"].values():
        for step in job.get("steps", []):
            run = step.get("run", "")
            assert "secrets." not in run and "x-access-token" not in run
