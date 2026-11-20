"""overview_snapshot_spec.py — a report_day spec built from the live Overview rollup (Overview phase 4, WP4.1).

The three-week report was a hand-maintained snapshot of 199 ``convergence`` sections, one per run
folder: it repeated continuations, counted ``_backup`` copies as work and never ran ``walls`` /
``sensitivity`` / ``term_balance``. This builder derives the spec from the same rollup the GUI
Overview uses (``hornlab_search.gui.data_overview.overview``), so the unit is the **line of work**:
per score identity, the best run of each ranked line — never one entry per run.

    .venv\\Scripts\\python.exe tools\\analysis\\overview_snapshot_spec.py --days 14 --out runs\\analysis\\overview_spec.yaml
    .venv\\Scripts\\python.exe tools\\analysis\\report_day.py --spec runs\\analysis\\overview_spec.yaml --out runs\\analysis\\overview_<date>

Rules honoured (docs/overview/OVERVIEW_IMPLEMENTATION_PLAN_2026-11-19.md §1):

* read-only over ``runs/`` (only the ``--out`` file is written, atomically);
* no GPU and no solver — pure CPU rollup plus YAML;
* the current identity filter only; legacy/diagnostic identities contribute no sections;
* probe-only lines never lead and never appear;
* J is never compared across score identities — each section's ``id`` is prefixed with its identity.

A line with at least 40 valid evaluations also gets a ``sensitivity`` section (the tool needs enough
rows to be meaningful); every chosen run gets ``convergence``, ``walls`` and ``term_balance``.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:                      # run as a script: repo root must be importable
    sys.path.insert(0, str(_REPO))

from hornlab_search.gui import data_overview as OV  # noqa: E402  (after the sys.path insert)

SENSITIVITY_MIN_VALID = 40
_SLUG = re.compile(r"[^a-z0-9]+")


def _section_id(identity_id: str, construction: str) -> str:
    """Stable, readable section id: identity first, so two identities can never collide."""
    return f"{_SLUG.sub('_', str(identity_id).lower()).strip('_')}__" \
           f"{_SLUG.sub('_', str(construction).lower()).strip('_')}"


def build_spec(*, root: Path, runs: Path, days: float = 14.0, show_legacy: bool = False) -> dict:
    """The report_day spec dict: ``{runs_root, convergence, walls, term_balance, sensitivity}``."""
    ov = OV.overview(root, runs, days=float(days), show_legacy=bool(show_legacy))
    try:
        runs_root = Path(runs).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:                                # an external runs tree: keep it absolute
        runs_root = str(Path(runs).resolve())
    spec: dict = {"runs_root": runs_root, "convergence": [], "walls": [], "term_balance": [],
                  "sensitivity": []}
    seen: set[str] = set()
    for ident in ov.get("identities") or []:
        if ident.get("status") != "current":
            continue                                  # legacy/diagnostic are not snapshot material
        for line in ident.get("lines") or []:
            if not line.get("rank") or line.get("probe_only"):
                continue                              # unranked or probe-only: never a section
            run_id = line.get("best_run_id")
            if not run_id or run_id in seen:
                continue                              # one entry per line, never per run
            if "_backup" in str(run_id):
                continue                              # provenance copies are not work
            seen.add(run_id)
            sid = _section_id(ident["id"], line.get("construction"))
            entry = {"id": sid, "run": run_id}
            spec["convergence"].append(dict(entry))
            spec["walls"].append(dict(entry))
            spec["term_balance"].append(dict(entry))
            if int(line.get("valid") or 0) >= SENSITIVITY_MIN_VALID:
                spec["sensitivity"].append(dict(entry))
    return spec


def write_spec(spec: dict, out: Path) -> Path:
    """Write the spec atomically (tmp file in the same directory + os.replace)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True), encoding="utf-8")
    os.replace(tmp, out)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build a report_day spec from the live Overview rollup.")
    ap.add_argument("--days", type=float, default=14.0, help="overview window in days (default 14)")
    ap.add_argument("--out", required=True, type=Path, help="spec YAML to write")
    ap.add_argument("--root", type=Path, default=_REPO, help=argparse.SUPPRESS)
    ap.add_argument("--runs-root", type=Path, default=None, help="runs/ override (default <root>/runs)")
    ap.add_argument("--show-legacy", action="store_true", help="include legacy identities (default off)")
    a = ap.parse_args(argv)
    if not 1 <= a.days <= 365:
        ap.error("--days must be between 1 and 365")
    root = Path(a.root)
    runs = Path(a.runs_root) if a.runs_root else root / "runs"
    spec = build_spec(root=root, runs=runs, days=a.days, show_legacy=a.show_legacy)
    path = write_spec(spec, a.out)
    counts = ", ".join(f"{k} {len(spec[k])}" for k in
                       ("convergence", "walls", "term_balance", "sensitivity"))
    print(f"wrote {path} ({counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
