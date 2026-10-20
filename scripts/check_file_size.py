"""Fail if any file tracked by git is over the size limit (50 MB by default)."""

import argparse
import subprocess
import sys
from pathlib import Path

LIMIT_BYTES = 50_000_000


def tracked_files(root: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
    ).stdout
    return [root / name for name in out.decode().split("\0") if name]


def oversized(root: Path, limit: int = LIMIT_BYTES) -> list[tuple[Path, int]]:
    found = []
    for path in tracked_files(root):
        if path.is_file() and (size := path.stat().st_size) > limit:
            found.append((path.relative_to(root), size))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--limit", type=int, default=LIMIT_BYTES)
    args = parser.parse_args(argv)

    bad = oversized(args.root.resolve(), args.limit)
    for path, size in bad:
        print(f"{path}: {size:,} bytes is over the {args.limit:,} byte limit")
    if bad:
        return 1
    print(f"OK: no tracked file over {args.limit:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
