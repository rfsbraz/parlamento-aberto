"""CONTRIBUTING.md and SECURITY.md exist and stay in step with CI.

CONTRIBUTING lists the commands a contributor runs before a PR. Every `uv run` and
`python3` check in ci.yml must appear there, so a new CI check cannot be added without
telling contributors how to run it.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
SECURITY = ROOT / "SECURITY.md"


def ci_commands() -> list[str]:
    jobs = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text())["jobs"]
    commands = []
    for job in jobs.values():
        for step in job["steps"]:
            for line in step.get("run", "").splitlines():
                line = line.strip()
                if line.startswith(("uv run ", "python3 ")):
                    commands.append(line)
    return commands


def test_contributing_lists_every_ci_check():
    text = CONTRIBUTING.read_text()
    assert ci_commands(), "no checks found in ci.yml"
    for command in ci_commands():
        local = command.replace("python3 ", "uv run python ", 1)
        assert command in text or local in text, command


def test_contributing_covers_gitleaks_and_fixtures():
    text = CONTRIBUTING.read_text()
    assert "gitleaks git" in text and "origin/main..HEAD" in text
    assert "tests/fixtures/README.md" in text


def test_security_points_to_private_vulnerability_reporting():
    text = SECURITY.read_text()
    assert "Report a vulnerability" in text
    assert "/security/advisories/new" in text


def test_no_em_dashes():
    for path in (CONTRIBUTING, SECURITY):
        assert "\u2014" not in path.read_text(), path.name
