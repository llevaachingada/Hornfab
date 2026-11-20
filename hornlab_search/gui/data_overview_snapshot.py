"""Overview phase 4 (WP4.2): the CPU-only ``overview-snapshot`` job and its snapshot listing.

The snapshot is the frozen copy of the live Overview: a ``report_day`` spec built from the same
rollup the GUI reads (``tools/analysis/overview_snapshot_spec.py``) and the report it produces
under ``runs/analysis/overview_<YYYY-MM-DD>/``. It reuses the existing analysis tools; nothing here
solves, writes into a run folder or takes the GPU lock (the kind is deliberately **not** in
``jobs.GPU_KINDS``, so it launches while a solve holds the lock).

Run as a GUI job (``jobs`` registers the entry script) or by hand:

    .venv\\Scripts\\python.exe hornlab_search/gui/data_overview_snapshot.py --days 14
"""
from __future__ import annotations

import argparse
import datetime as _dt
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):                       # run as a job entry script: make the repo importable
    sys.path.insert(0, str(_REPO))

from hornlab_search.gui import data as D            # noqa: E402

SPEC_TOOL_REL = "tools/analysis/overview_snapshot_spec.py"
REPORT_TOOL_REL = "tools/analysis/report_day.py"
SNAPSHOT_PREFIX = "overview_"


def snapshot_argv(days: float = 14.0, out_dir: str | None = None) -> list[str]:
    """The job's argv (the entry script supplies the interpreter and the path)."""
    argv = ["--days", str(float(days))]
    if out_dir:
        argv += ["--out-dir", str(out_dir)]
    return argv


def _stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def snapshot_main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    """Build the spec, then run ``report_day`` into ``runs/analysis/overview_<date>``. Returns the
    child's exit code (0 means the report was written, even if some sections errored)."""
    ap = argparse.ArgumentParser(description="Generate a frozen Overview snapshot (CPU only).")
    ap.add_argument("--days", type=float, default=14.0, help="overview window in days (default 14)")
    ap.add_argument("--out-dir", default=None, help="parent of the snapshot folder (default runs/analysis)")
    ap.add_argument("--root", type=Path, default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    base = Path(a.root) if a.root else (Path(root) if root is not None else _REPO)
    runs = base / "runs"
    out_parent = Path(a.out_dir) if a.out_dir else runs / "analysis"
    if not out_parent.is_absolute():
        out_parent = base / out_parent
    out = out_parent / f"{SNAPSHOT_PREFIX}{_stamp()}"
    n = 1
    while out.exists():                              # a second snapshot on the same day never overwrites
        n += 1
        out = out_parent / f"{SNAPSHOT_PREFIX}{_stamp()}_{n}"
    spec = out / "spec.yaml"
    print(f"overview snapshot: spec -> {spec.relative_to(base).as_posix() if base in spec.parents else spec}")
    rc = subprocess.run([sys.executable, str(base / SPEC_TOOL_REL), "--days", str(float(a.days)),
                         "--root", str(base), "--out", str(spec)],
                        cwd=str(base)).returncode
    if rc != 0:
        print(f"overview snapshot: spec builder failed (exit {rc})", file=sys.stderr)
        return rc
    print(f"overview snapshot: report_day -> {out.relative_to(base).as_posix() if base in out.parents else out}")
    rc = subprocess.run([sys.executable, str(base / REPORT_TOOL_REL), "--spec", str(spec),
                         "--out", str(out)], cwd=str(base)).returncode
    print(f"overview snapshot: report_day exit {rc}")
    return rc


def snapshots(root: Path, runs: Path) -> list[dict]:
    """Every frozen snapshot under ``runs/analysis`` (newest first), for the Overview header."""
    base = Path(runs) / "analysis"
    out: list[dict] = []
    try:
        dirs = sorted((p for p in base.iterdir() if p.is_dir() and p.name.startswith(SNAPSHOT_PREFIX)),
                      key=lambda p: p.name, reverse=True)
    except OSError:
        return []
    for d in dirs:
        rep = D._read_json(d / "report_day.json") or {}
        sections = rep.get("sections") if isinstance(rep, dict) else None
        n_errors = int(rep.get("n_errors") or 0) if isinstance(rep, dict) else 0
        if n_errors == 0 and isinstance(sections, list):
            n_errors = sum(1 for s in sections if isinstance(s, dict) and s.get("status") == "error")
        out.append({"id": d.name, "label": d.name, "path": d.relative_to(Path(runs)).as_posix(),
                    "href": f"#/analysis/{d.name}",
                    "generated_utc": rep.get("generated_utc") if isinstance(rep, dict) else None,
                    "n_sections": len(sections) if isinstance(sections, list) else None,
                    "n_errors": n_errors,
                    "spec": (d / "spec.yaml").is_file()})
    return out


if __name__ == "__main__":
    raise SystemExit(snapshot_main())
