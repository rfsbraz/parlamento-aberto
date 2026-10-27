"""Read sources.yaml and pick the source files a run should touch."""

from dataclasses import dataclass
from pathlib import Path

import yaml

ROMAN = {"I": 1, "V": 5, "X": 10}
MERGES = ("replace", "upsert")


def legislature_number(name: str) -> int:
    """Order legislatures: Constituinte is 0, then I, II, ... XVII."""
    if name == "Constituinte":
        return 0
    total = 0
    for i, ch in enumerate(name):
        value = ROMAN[ch]
        nxt = ROMAN.get(name[i + 1]) if i + 1 < len(name) else None
        total += -value if nxt and nxt > value else value
    return total


@dataclass(frozen=True)
class Source:
    dataset: str
    legislature: str
    part: str | None
    url: str
    layout: str
    id_key: str | None
    ids: dict
    names: dict
    bucket: int | None
    path: str | None = None
    listed_on: str | None = None
    copy_of: str | None = None
    format: str = "json"
    merge: str = "replace"

    @property
    def key(self) -> str:
        """Lock key and output folder, relative to data/."""
        leg = f"{self.legislature}-{self.part}" if self.part else self.legislature
        return f"{self.dataset}/{leg}"


def load(path: Path) -> list[Source]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    out = []
    for dataset, spec in (raw.get("datasets") or {}).items():
        merge = spec.get("merge", "replace")
        if merge not in MERGES:
            raise ValueError(f"{dataset}: merge must be one of {MERGES}, not {merge!r}")
        for f in spec.get("files", []):
            out.append(
                Source(
                    dataset=dataset,
                    legislature=str(f["legislature"]),
                    part=str(f["part"]) if f.get("part") else None,
                    url=f["url"],
                    layout=spec["layout"],
                    id_key=f.get("id") or spec.get("id"),
                    ids=spec.get("ids") or {},
                    names=spec.get("names") or {},
                    bucket=int(spec["bucket"]) if spec.get("bucket") else None,
                    path=f.get("path"),
                    listed_on=str(f["listed_on"]) if f.get("listed_on") else None,
                    copy_of=str(f["copy_of"]) if f.get("copy_of") else None,
                    format=str(f.get("format") or "json"),
                    merge=merge,
                )
            )
    keys = [s.key for s in out]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        raise ValueError(f"duplicate sources: {sorted(dupes)}")
    return out


def current_legislature(sources: list[Source]) -> str:
    return max((s.legislature for s in sources), key=legislature_number)


def select(
    sources: list[Source],
    *,
    all_legislatures: bool = False,
    dataset: str | None = None,
    legislature: str | None = None,
) -> list[Source]:
    """Default is the current legislature only. --all widens to every legislature."""
    if dataset and dataset not in {s.dataset for s in sources}:
        raise ValueError(f"unknown dataset: {dataset}")
    if legislature is None and not all_legislatures:
        legislature = current_legislature(sources)
    return [
        s
        for s in sources
        if (dataset is None or s.dataset == dataset)
        and (legislature is None or s.legislature == legislature)
    ]
