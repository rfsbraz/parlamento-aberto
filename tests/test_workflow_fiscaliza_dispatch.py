"""O aviso ao Fiscaliza (#93): em push para main, à mão ou do data-release.yml, sem permissões, e o
token só no env."""

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "fiscaliza-dispatch.yml"
# O que o Fiscaliza lê no commit do pin: corre `uv run --locked python -m
# parlamento_aberto.release build --data data` (deploy/pages.py) e usa só o manifest.json e
# os Parquet. Os dados, o pacote (modelos, seeds, schema.yml) e o ambiente do uv.
DATA_PATHS = [
    "data/**",
    "src/parlamento_aberto/**",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
]


def load():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def triggers():
    # O YAML 1.1 lê a chave "on" como True.
    return load()[True]


def steps():
    (job,) = load()["jobs"].values()
    return job["steps"]


def matches(pattern, path):
    """Um padrão de on.push.paths como o GitHub o lê: ** passa por /, * e ? não."""
    regex = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            regex += ".*"
            i += 2
        elif pattern[i] == "*":
            regex += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            regex += "[^/]"
            i += 1
        else:
            regex += re.escape(pattern[i])
            i += 1
    return re.fullmatch(regex, path) is not None


def fires(changed):
    return any(matches(p, f) for p in triggers()["push"]["paths"] for f in changed)


def test_runs_only_on_push_to_main_when_the_data_changes_or_by_hand():
    # Nem pull_request nem pull_request_target: um PR de um fork não pode chegar ao secret.
    # O workflow_call é o data-release.yml depois de publicar (#112).
    assert {k: v for k, v in triggers().items() if k != "workflow_call"} == {
        "push": {"branches": ["main"], "paths": DATA_PATHS},
        "workflow_dispatch": {
            "inputs": {
                "sha": {
                    "description": "Commit de main a enviar, os 40 caracteres (vazio: o do ref)",
                    "required": False,
                    "type": "string",
                }
            }
        },
    }


def test_a_data_push_fires():
    assert fires(["data/_meta/sources.lock.json", "data/iniciativas/XVI/1.json"])
    assert fires(["src/parlamento_aberto/models/seeds/attendance_codes.csv"])
    assert fires(["src/parlamento_aberto/models/schema.yml"])
    assert fires(["src/parlamento_aberto/models/marts/plenary_attendance.sql"])
    assert fires(["src/parlamento_aberto/build.py"])
    assert fires(["uv.lock"])
    assert fires(["README.md", "data/peticoes/XVI.json"])


def test_docs_ci_tests_and_templates_do_not_fire():
    assert not fires(["README.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE-DATA"])
    assert not fires(["docs/data-changelog.md", "docs/dictionary/votes.md"])
    assert not fires([".github/workflows/ci.yml", ".github/workflows/fiscaliza-dispatch.yml"])
    assert not fires([".github/pull_request_template.md", ".github/ISSUE_TEMPLATE/x.yml"])
    assert not fires(["tests/test_release.py", "tests/fixtures/a.json", ".gitleaks.toml"])
    assert not fires(["scripts/x.py", "sources.yaml"])


def test_every_path_matches_a_tracked_file():
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"], check=True, capture_output=True, text=True
    ).stdout.split()
    for pattern in DATA_PATHS:
        assert any(matches(pattern, f) for f in tracked), pattern


def test_has_no_permissions():
    assert load()["permissions"] == {}


def test_sends_data_updated_with_the_commit_to_fiscaliza():
    # O repositório chama-se rfsbraz/fiscaliza. Não confio no redirect do nome antigo num POST.
    (step,) = [s for s in steps() if "run" in s]
    run = step["run"]
    assert "https://api.github.com/repos/rfsbraz/fiscaliza/dispatches" in run
    assert "rfsbraz/parliament" not in WORKFLOW.read_text(encoding="utf-8")
    assert '"event_type":"data-updated"' in run
    assert '"client_payload":{"sha":"\'"$SHA"\'"}}' in run
    assert 'SHA="${INPUT_SHA:-$GITHUB_SHA}"' in run
    assert step["env"]["FISCALIZA_DISPATCH_TOKEN"] == "${{ secrets.FISCALIZA_DISPATCH_TOKEN }}"
    assert step["env"]["INPUT_SHA"] == "${{ inputs.sha }}"


def dispatch_sha(input_sha, github_sha="a" * 40):
    """Corre a parte do passo que escolhe e valida o commit, sem o curl."""
    (step,) = [s for s in steps() if "run" in s]
    run = step["run"]
    start = run.index('SHA="')
    end = run.index("\nfi\n", start) + len("\nfi\n")
    script = run[start:end] + 'echo "$SHA"\n'
    env = {"PATH": "/usr/bin:/bin", "INPUT_SHA": input_sha, "GITHUB_SHA": github_sha}
    return subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True, text=True)


def test_a_manual_run_sends_the_sha_input_or_the_ref_commit():
    pinned = "a48c5b1d623d2e54c5f2168730518c190a81d49a"
    assert dispatch_sha(pinned).stdout.strip() == pinned
    assert dispatch_sha("").stdout.strip() == "a" * 40


def test_a_bad_sha_input_fails_before_the_dispatch():
    for bad in ["a48c5b1", "main", "A" * 40, "a" * 40 + "; echo x", "a" * 40 + "\n}}", '"}}']:
        out = dispatch_sha(bad)
        assert out.returncode != 0, bad
        assert "::error::" in out.stdout


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
