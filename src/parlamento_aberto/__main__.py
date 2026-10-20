"""python -m parlamento_aberto fetch [--all] [--dataset NAME] [--legislature XVII]"""

import argparse
import json
import sys
from pathlib import Path

from . import fetch, sources, sync


def offline_get(raw_dir: Path, by_url: dict[str, str]):
    def get(url: str) -> fetch.Response:
        path = raw_dir / f"{by_url[url]}.json"
        if not path.exists():
            return fetch.Response(404, "text/plain", b"")
        return fetch.Response(200, "application/json", path.read_bytes())

    return get


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="parlamento_aberto")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fetch, validate and normalise AR files into data/")
    f.add_argument("--all", action="store_true", help="every legislature (full sync)")
    f.add_argument("--dataset", help="only this dataset")
    f.add_argument("--legislature", help="only this legislature, for example XVI")
    f.add_argument("--sources", type=Path, default=Path("sources.yaml"))
    f.add_argument("--data", type=Path, default=Path("data"))
    f.add_argument("--raw-dir", type=Path, help="keep each download here (not committed)")
    f.add_argument("--offline", action="store_true", help="read inputs from --raw-dir")
    f.add_argument("--report", type=Path, help="write the run report as JSON")
    a = p.parse_args(argv)

    srcs = sources.select(
        sources.load(a.sources),
        all_legislatures=a.all,
        dataset=a.dataset,
        legislature=a.legislature,
    )
    get, kwargs = fetch.http_get, {}
    if a.offline:
        if not a.raw_dir:
            p.error("--offline needs --raw-dir")
        get = offline_get(a.raw_dir, {s.url: s.key for s in srcs})
        kwargs = {"attempts": 1}
    reports = sync.run(
        srcs,
        a.data,
        get=get,
        fetch_kwargs=kwargs,
        raw_dir=None if a.offline else a.raw_dir,
        log=lambda line: print(line, file=sys.stderr, flush=True),
    )
    if a.report:
        a.report.write_text(json.dumps(reports, ensure_ascii=False, indent=1) + "\n")
    stale = [r["source"] for r in reports if r["status"] == "stale"]
    print(f"{len(reports)} sources, {len(stale)} stale: {', '.join(stale) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
