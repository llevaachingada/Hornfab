"""GUI bridge for the M1 research snapshot: the CPU-only ``research-snapshot`` job and its listing.

The Overview Briefing tab's "Generate research snapshot" button launches this file as a job entry
script; it runs ``hornlab_search.research.build`` (read-only over the repository, no solver, no GPU
lock: the kind is deliberately **not** in ``jobs.GPU_KINDS``) and writes
``runs/analysis/research_<cutoff-date>_<id8>/``, which the existing ``/analysis/<set>/<file>`` route
serves. ``GET /api/research/snapshots`` lists complete snapshots (``summary.json`` is written last).

Run by hand:

    .venv\\Scripts\\python.exe hornlab_search/gui/data_research.py --cutoff now
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):                       # run as a job entry script: make the repo importable
    sys.path.insert(0, str(_REPO))

PREFIX = "research_"
#: ``now`` or an ISO-8601 UTC instant (date, or date + time with Z / offset). Validated again by the builder.
_CUTOFF = re.compile(r"^(now|\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?)?)$")
_SET_ID = re.compile(r"^research_\d{4}-\d{2}-\d{2}_[0-9a-f]{8}$")


class ResearchArgError(ValueError):
    """A refused launch argument (shown to the user)."""


def normalise_cutoff(raw) -> str:
    """'' / None -> 'now'; a bare date -> end of that UTC day; otherwise the validated string."""
    if raw in (None, ""):
        return "now"
    text = str(raw).strip()
    if not _CUTOFF.match(text):
        raise ResearchArgError("cutoff must be 'now' or an ISO-8601 UTC instant such as 2026-11-25T23:59:59Z")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text + "T23:59:59Z"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?", text):   # no zone given: read as UTC
        return text + ("Z" if text.count(":") == 2 else ":00Z")
    return text


def research_argv(args: dict) -> list[str]:
    """The job's argv (the entry script supplies the interpreter and the path)."""
    return ["--cutoff", normalise_cutoff((args or {}).get("cutoff"))]


def research_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate a frozen research snapshot (CPU only, read-only).")
    ap.add_argument("--cutoff", default="now")
    ap.add_argument("--root", type=Path, default=_REPO, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    from hornlab_search.research.build import main as build_main
    print(f"research snapshot: cutoff {a.cutoff} (read-only; no solver, no GPU lock)", flush=True)
    return build_main(["build", "--root", str(a.root), "--cutoff", normalise_cutoff(a.cutoff)])


def _read(p: Path) -> dict | None:
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return v if isinstance(v, dict) else None


def snapshots(runs: Path, limit: int = 20) -> list[dict]:
    """Complete research snapshots under ``runs/analysis`` (newest cutoff first)."""
    base = Path(runs) / "analysis"
    try:
        dirs = [p for p in base.iterdir() if p.is_dir() and _SET_ID.match(p.name)]
    except OSError:
        return []
    out = []
    for d in dirs:
        s = _read(d / "summary.json")
        if not s or s.get("schema") != "hornfab-research-summary-m1":
            continue                                 # incomplete (still writing) or foreign folder
        out.append({
            "id": d.name, "snapshot_id": s.get("snapshot_id"), "cutoff_utc": s.get("cutoff_utc"),
            "source_commit": s.get("source_commit"), "generator": s.get("generator"),
            "counts": s.get("counts") or {}, "cohort_status": s.get("cohort_status") or {},
            "headlines": [h for h in (s.get("headlines") or []) if h.get("severity") in ("decision", "data_quality")][:6],
            "n_next_steps": len(s.get("next_steps") or []),
            "href": f"/analysis/{d.name}/index.html",
            "files": {k: f"/analysis/{d.name}/{k}" for k in ("summary.json", "snapshot.json", "manifest.json",
                                                             "AGENT_GUIDE.md")},
            "path": d.relative_to(Path(runs)).as_posix(),
        })
    out.sort(key=lambda x: (x.get("cutoff_utc") or "", x["id"]), reverse=True)
    return out[:limit]


if __name__ == "__main__":
    raise SystemExit(research_main())
