"""The EpT rules in .gitleaks.toml (#44), applied the way gitleaks applies them.

CI runs gitleaks itself on the full history. This test checks the rules on synthetic
stored declarations, so a rule change that lets a personal NIF through fails here too.
"""

import json
import re
import tomllib
from pathlib import Path

import pytest

from parlamento_aberto import ept

CONFIG = tomllib.loads((Path(__file__).parent.parent / ".gitleaks.toml").read_text())
RULES = {r["id"]: r for r in CONFIG["rules"]}
ACT = "2c6d9562-dea5-488b-9afe-42519c636daf"
STORED = "data/ept_registo_interesses/4508/0/1.json"


def with_check(base8: str) -> str:
    total = sum(int(d) * w for d, w in zip(base8, range(9, 1, -1), strict=True))
    r = total % 11
    return base8 + str(0 if r < 2 else 11 - r)


# Synthetic: repeated digit patterns with the check digit computed.
VALID = with_check("5" + "0" * 7)
PERSONAL = [with_check(d + "0" * 7) for d in "1234"]
OTHER_7X = with_check("70" + "0" * 6)
COMPANY = [with_check(p + "0" * (8 - len(p))) for p in ("5", "6", "71", "72", "79")]
WIDER = [with_check(p + "1" * (8 - len(p))) for p in ("8", "90", "91", "98", "77")]


def findings(path: str, text: str) -> list[str]:
    out = []
    for rule in RULES.values():
        if not re.search(rule["path"], path):
            continue
        allow = [
            re.compile(rx)
            for a in CONFIG["allowlists"]
            if rule["id"] in a.get("targetRules", [rule["id"]]) and a.get("regexTarget") == "line"
            for rx in a["regexes"]
        ]
        for line in text.splitlines():
            if re.search(rule["regex"], line) and not any(rx.search(line) for rx in allow):
                out.append(rule["id"])
    return out


def record(col1="Cargo sintético", col9=None) -> str:
    row = {"col1": col1}
    if col9 is not None:
        row["col9"] = col9
    return json.dumps({"id": 1, "tab4": {ACT: [row]}}, sort_keys=True, indent=1) + "\n"


def test_rules_exist():
    assert {"ept-personal-nif", "ept-nine-digits"} <= set(RULES)
    assert CONFIG["extend"]["useDefault"] is True


def test_valid_nipc_in_the_nipc_column_passes(tmp_path):
    ept.write_json(tmp_path / "1.json", json.loads(record(col9=VALID)))
    assert findings(STORED, (tmp_path / "1.json").read_text()) == []


@pytest.mark.parametrize("value", COMPANY)
def test_each_company_prefix_in_the_nipc_column_passes(value):
    assert findings(STORED, record(col9=value)) == []


@pytest.mark.parametrize("value", [*PERSONAL, OTHER_7X, *WIDER])
def test_personal_or_other_7x_in_the_nipc_column_fails(value):
    assert findings(STORED, record(col9=value))


@pytest.mark.parametrize("value", [VALID, *PERSONAL])
def test_nine_digits_outside_the_nipc_column_fail(value):
    assert findings(STORED, record(col1=f"ref {value}"))
    assert findings("data/ept_registo_interesses/declarations.ndjson", json.dumps({"a": value}))
    assert findings("tests/fixtures/ept/x.json", json.dumps({"a": value}))


@pytest.mark.parametrize("value", [PERSONAL[0], *WIDER])
def test_personal_range_fails_even_on_a_nipc_line(value):
    line = f'   "col9": "{value}"'
    assert "ept-personal-nif" in findings(STORED, line)


def test_the_association_nipc_column_is_not_allowed():
    # col8 was the association section's NIPC column, which is never stored.
    assert findings(STORED, f'   "col8": "{COMPANY[0]}"')


def test_rules_leave_the_ar_data_alone():
    assert findings("data/_meta/sources.lock.json", json.dumps({"size": PERSONAL[0]})) == []
