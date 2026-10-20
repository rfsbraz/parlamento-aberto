import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_file_size.py"


def run_check(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(repo)], capture_output=True, text=True)


def make_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "small.json").write_text("{}\n")
    subprocess.run(["git", "add", "small.json"], cwd=tmp_path, check=True)
    return tmp_path


def test_passes_without_large_file(tmp_path):
    result = run_check(make_repo(tmp_path))
    assert result.returncode == 0, result.stdout


def test_fails_on_file_over_50_mb(tmp_path):
    repo = make_repo(tmp_path)
    big = repo / "big.ndjson"
    with big.open("wb") as f:  # sparse file, no real disk use
        f.truncate(50_000_001)
    subprocess.run(["git", "add", "-N", "big.ndjson"], cwd=repo, check=True)
    result = run_check(repo)
    assert result.returncode == 1
    assert "big.ndjson: 50,000,001 bytes" in result.stdout
