"""Write tests/fixtures/history/upsert.json from the data commits tests/test_upsert.py replays.

Keeps only what the tests assert on: the intervention ids and dates, the initiative ids and
the lock entries. Needs a clone with full history: uv run python scripts/upsert_history_fixture.py
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests/fixtures/history/upsert.json"
INTERV = {"lock": "4ecab717", "files": ["4ecab717", "ef53439a", "65a68f9e", "52f9df2b"]}
INI = {"lock": "9033f8c4", "files": ["9033f8c4", "65a68f9e"]}


def git(*args) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def lock(commit: str, key: str) -> dict:
    return json.loads(git("show", f"{commit}:data/_meta/sources.lock.json"))[key]


def interventions(commit: str) -> list:
    body = git("show", f"{commit}:data/intervencoes/XVII/records.ndjson").decode()
    rows = (json.loads(line) for line in body.splitlines())
    return [[r["Id"], r["DataReuniaoPlenaria"]] for r in rows]


def initiatives(commit: str) -> list[int]:
    names = git("ls-tree", "-r", "--name-only", commit, "data/iniciativas/XVII/").decode()
    return sorted(int(Path(n).stem) for n in names.split())


def rows(values: list) -> str:
    return "[\n" + ",\n".join(json.dumps(v, ensure_ascii=False) for v in values) + "\n]"


def main() -> None:
    parts = {
        "intervencoes/XVII": (INTERV, interventions),
        "iniciativas/XVII": (INI, initiatives),
    }
    out = []
    for key, (spec, read) in parts.items():
        files = ",\n".join(f'"{c}": {rows(read(c))}' for c in spec["files"])
        entry = json.dumps(lock(spec["lock"], key), sort_keys=True, ensure_ascii=False)
        out.append(f'"{key}": {{\n"lock": {entry},\n"files": {{\n{files}\n}}\n}}')
    OUT.write_text("{\n" + ",\n".join(out) + "\n}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
