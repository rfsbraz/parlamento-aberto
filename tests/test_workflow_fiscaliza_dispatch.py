"""O aviso ao Fiscaliza (#93): só em push para main, sem permissões, e o token só no env."""

import re
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "fiscaliza-dispatch.yml"


def load():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def triggers():
    # O YAML 1.1 lê a chave "on" como True.
    return load()[True]


def steps():
    (job,) = load()["jobs"].values()
    return job["steps"]


def test_runs_only_on_push_to_main():
    # Nem pull_request nem pull_request_target: um PR de um fork não pode chegar ao secret.
    assert triggers() == {"push": {"branches": ["main"]}}


def test_has_no_permissions():
    assert load()["permissions"] == {}


def test_sends_data_updated_with_the_commit_to_parliament():
    (step,) = [s for s in steps() if "run" in s]
    run = step["run"]
    assert "https://api.github.com/repos/rfsbraz/parliament/dispatches" in run
    assert '"event_type":"data-updated"' in run
    assert '"client_payload":{"sha":"' in run and "$GITHUB_SHA" in run
    assert step["env"]["FISCALIZA_DISPATCH_TOKEN"] == "${{ secrets.FISCALIZA_DISPATCH_TOKEN }}"


def test_a_missing_secret_ends_with_a_notice_not_an_error():
    (step,) = [s for s in steps() if "run" in s]
    check = r'if \[ -z "\$FISCALIZA_DISPATCH_TOKEN" \]; then\n(.*?)\nfi'
    missing = re.search(check, step["run"], re.S).group(1)
    assert "::notice::" in missing and "exit 0" in missing


def test_never_prints_the_token_and_fails_on_an_http_error():
    (step,) = [s for s in steps() if "run" in s]
    run = step["run"]
    assert "${{" not in run
    assert "set -x" not in run
    assert not re.search(r"(echo|printf)[^\n]*\$FISCALIZA_DISPATCH_TOKEN", run)
    assert "curl -fsS" in run
