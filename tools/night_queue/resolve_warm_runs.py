"""Resolve ``@design:<hash>`` warm-start placeholders to real run dirs, then check every warm start.

Night configs written off the owner box (no ``runs/``) may name a warm-start run by the DESIGN it
holds: ``search.warm_start.from_runs: ["runs/@design:a23763f1c6fc"]``. On the owner box this tool
replaces each placeholder with the newest ``runs/<run>`` (or ``runs/<study>/<mode>``) whose
``designs/<hash>`` exists and that has a ``search.ndjson``, and reports any ``from_runs`` path that
does not exist. Text replacement only (the YAML layout and comments are kept). CPU, no GPU, safe
during a live night.

    .venv\\Scripts\\python.exe tools/night_queue/resolve_warm_runs.py examples/typologies/scout40_2026-11-19 [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
TOKEN = re.compile(r"runs[\\/]+@design:([0-9a-f]{6,64})")


def _candidates(runs_root: Path, design_hash: str) -> list[Path]:
    """Run dirs holding ``designs/<hash>`` with a ``search.ndjson``.

    Two layouts exist on the owner box: the classic ``runs/<run>/designs/<hash>`` and the
    study layout ``runs/<study>/<screen|verify>/designs/<hash>`` (the rescore records those
    subdirs as the run name "screen", 2026-11-18). The one-level glob missed the latter.
    """
    hits = []
    for pattern in (f"*/designs/{design_hash}", f"*/*/designs/{design_hash}"):
        for p in runs_root.glob(pattern):
            run = p.parent.parent
            if (run / "search.ndjson").is_file():
                hits.append(run)
    return hits


def find_run(runs_root: Path, design_hash: str) -> Path | None:
    """Newest candidate: by run-dir mtime (a verify/solve dir is written after screen), path tiebreak."""
    hits = _candidates(runs_root, design_hash)
    if not hits:
        return None
    return sorted(hits, key=lambda r: (r.stat().st_mtime, str(r)))[-1]


def resolve_file(path: Path, runs_root: Path, *, write: bool = True) -> dict:
    text = path.read_text(encoding="utf-8")
    out = {"config": path.name, "resolved": {}, "unresolved": [], "missing": []}

    def sub(m):
        run = find_run(runs_root, m.group(1))
        if run is None:
            out["unresolved"].append(m.group(1))
            return m.group(0)
        rel = "runs/" + run.relative_to(runs_root).as_posix()
        out["resolved"][m.group(1)] = rel
        return rel
    new = TOKEN.sub(sub, text)
    if write and new != text:
        path.write_text(new, encoding="utf-8")
    ws = ((yaml.safe_load(new) or {}).get("search") or {}).get("warm_start") or {}
    for r in ws.get("from_runs") or []:
        if TOKEN.search(r):
            continue
        if not (runs_root.parent / r).is_dir() and not Path(r).is_dir():
            out["missing"].append(r)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("--runs-root", type=Path, default=REPO / "runs")
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    a = ap.parse_args(argv)
    bad = 0
    for p in sorted(a.folder.glob("*.yaml")):
        r = resolve_file(p, a.runs_root, write=not a.check)
        bad += len(r["unresolved"]) + len(r["missing"])
        print(f"{r['config']}: resolved={r['resolved']} unresolved={r['unresolved']} missing={r['missing']}")
    print("OK" if not bad else f"{bad} problem(s): fix before launch")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
