"""EpT sync (#45): checks and PR body for the weekly job in .github/workflows/ept-sync.yml.

The job fetches the dataset with ``parlamento_aberto.ept fetch`` on the ``data/ept`` branch,
runs ``check`` before anything is committed, and opens or updates one draft PR, held with
``hold: new-dataset`` and ``hold: ept``. data-merge.yml only merges ``data/nightly``, so this
PR is never merged automatically. The PR body is in pt-PT and carries counts and ids only.

    python -m parlamento_aberto.ept_sync check --data data --counts counts.json
    python -m parlamento_aberto.ept_sync body --report report.json --counts counts.json \\
        --base origin/main --body body.md
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from . import ept

DECLARATION = re.compile(r"^(\d+)/(\d+)/(\d+)\.json$")
INDEX_FILES = ("declarations.ndjson", "titularidades.ndjson")


class LayoutError(ValueError):
    """A file in the dataset folder that the fetcher does not write."""


def _ndjson(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def check(data_dir: Path) -> dict:
    """Run the leak guard on every stored file and count them. Fails on any unexpected file."""
    root = Path(data_dir) / ept.DATASET
    by_entity: Counter = Counter()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel in INDEX_FILES:
            ept.assert_clean(_ndjson(path), rel)
            continue
        m = DECLARATION.match(rel)
        if not m:
            raise LayoutError(f"unexpected file {rel}")
        entity, bucket, decl_id = (int(x) for x in m.groups())
        rec = json.loads(path.read_text(encoding="utf-8"))
        ept.assert_clean(rec)
        if rec.get("id") != decl_id or rec.get("entityId") != entity or decl_id // 1000 != bucket:
            raise LayoutError(f"{rel} does not match its id or entity")
        by_entity[str(entity)] += 1
    index = _ndjson(root / "declarations.ndjson")
    return {
        "declaration_files": sum(by_entity.values()),
        "by_entity": dict(sorted(by_entity.items())),
        "titularidades": len(_ndjson(root / "titularidades.ndjson")),
        "index_rows": len(index),
        "states": dict(sorted(Counter(r.get("stateType") for r in index).items())),
    }


def diff_summary(name_status: str) -> dict:
    """Files added, changed and removed under the dataset, from git diff --name-status."""
    out = {"added": 0, "changed": 0, "removed": 0}
    prefix = f"data/{ept.DATASET}/"
    for line in name_status.splitlines():
        status, _, path = line.partition("\t")
        if path.startswith(prefix):
            out[{"A": "added", "D": "removed"}.get(status[:1], "changed")] += 1
    return out


def render_body(report: dict, counts: dict, summary: dict, *, today: str) -> str:
    lines = [
        "Atualização semanal do registo de interesses da EpT (Entidade para a Transparência), "
        "XVI e XVII, para `data/ept_registo_interesses/` (#42, #45).",
        "",
        f"Última execução: {today} (Lisboa).",
        "",
        "**Não fazer merge.** É um dataset novo e a publicação ainda está por decidir: "
        "este PR fica em rascunho, com `hold: new-dataset` e `hold: ept`. Um merge põe estes "
        "dados no `main`.",
        "",
        "Cada declaração foi reduzida em memória antes de ser escrita: só metadados e o "
        "separador 4. Não há NIF do titular, nem separadores 2 e 3, nem anexos. Da coluna "
        "NIF/NIPC da entidade só ficam NIPC de empresas válidos.",
        "",
        "## Contagens",
        "",
        "| | |",
        "|---|---:|",
        f"| Titularidades | {report['titularidades']} |",
        f"| Pares entidade e titular pesquisados | {report['pairs']} |",
        f"| Declarações na pesquisa | {report['declarations']} |",
        f"| Declarações novas ou alteradas nesta execução | {report['to_fetch']} |",
        f"| Declarações obtidas nesta execução | {report['fetched']} |",
        f"| Declarações guardadas | {counts['declaration_files']} |",
        "",
        "Por entidade (declarações guardadas):",
        "",
        "| Entidade | Declarações |",
        "|---|---:|",
    ]
    lines += [f"| {e} | {n} |" for e, n in counts["by_entity"].items()] or ["| nenhuma | 0 |"]
    lines += ["", "Por estado (índice):", "", "| Estado | Declarações |", "|---|---:|"]
    lines += [f"| {s} | {n} |" for s, n in counts["states"].items()] or ["| nenhum | 0 |"]
    lines += [
        "",
        "## Alterações face ao main",
        "",
        f"Ficheiros: {summary['added']} novos, {summary['changed']} alterados, "
        f"{summary['removed']} removidos.",
        "",
        "## Falhas",
        "",
    ]
    failed = [f"- declaração {f['id']}: {f['error']}" for f in report.get("failed") or []]
    lines += failed or ["Nenhuma."]
    lines += ["", "Fonte: Entidade para a Transparência."]
    body = "\n".join(lines) + "\n"
    ept.assert_clean(body)
    return body


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="parlamento_aberto.ept_sync")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="leak guard and counts for the stored dataset")
    c.add_argument("--data", type=Path, default=Path("data"))
    c.add_argument("--counts", type=Path, help="write the counts as JSON")
    b = sub.add_parser("body", help="render the draft PR body")
    b.add_argument("--report", type=Path, required=True)
    b.add_argument("--counts", type=Path, required=True)
    b.add_argument("--base", default="origin/main")
    b.add_argument("--body", type=Path, required=True)
    a = p.parse_args(argv)
    if a.cmd == "check":
        counts = check(a.data)
        text = json.dumps(counts, ensure_ascii=False, indent=1)
        if a.counts:
            a.counts.write_text(text + "\n")
        print(text)
        return 0
    name_status = subprocess.run(
        ["git", "diff", "--name-status", a.base, "--", f"data/{ept.DATASET}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    body = render_body(
        json.loads(a.report.read_text()),
        json.loads(a.counts.read_text()),
        diff_summary(name_status),
        today=ept.lisbon_today(),
    )
    a.body.write_text(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
