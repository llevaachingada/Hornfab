"""B1 selection inputs: read-only scan of stored runs (no solve, no mesh).

  best-per-design-hash under the kept home brief ``room_landscape_80x50_700_hf1440_v7``
  plus a mesh-size estimate at the finalist tier (2x screen DOF cap).

Everything here only reads ``runs/**`` and the config loader. Nothing is written under runs/.

Run:  .venv\\Scripts\\python.exe scratch/fable_architecture/.b1/b1_compute.py [--json out]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from hornlab_search.config import load_config, mesh_spec  # noqa: E402

HOME_BRIEF = "room_landscape_80x50_700_hf1440_v7.yaml"


def read_json_loose(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def ndjson_rows(path: Path):
    out = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except OSError:
        return []
    return out


def brief_name(run_json: dict) -> str:
    cfg = run_json.get("config") or {}
    bf = cfg.get("brief_file")
    if not bf:
        return ""
    return Path(str(bf).replace("\\", "/")).name


def scan() -> list[dict]:
    """One record per (run dir, design hash): lowest J ok row, only ok rows."""
    recs = []
    for run_dir in sorted(p for p in (REPO / "runs").iterdir() if p.is_dir()):
        rj = read_json_loose(run_dir / "run.json")
        if not rj:
            continue
        nd = run_dir / "search.ndjson"
        if not nd.exists():
            continue
        best: dict[str, dict] = {}
        for r in ndjson_rows(nd):
            if not r.get("ok") or r.get("objective") is None:
                continue
            h = r.get("design_hash")
            if not h:
                continue
            j = float(r["objective"])
            cur = best.get(h)
            if cur is None or j < cur["objective"]:
                best[h] = {
                    "design_hash": h,
                    "objective": j,
                    "objective_version": r.get("objective_version"),
                    "mode": r.get("mode"),
                    "n_dof": r.get("n_dof"),
                    "n_triangles": r.get("n_triangles"),
                    "peak_vram_mb": r.get("peak_vram_mb"),
                    "seconds": r.get("seconds"),
                    "res_mm": r.get("res_mm"),
                    "family": r.get("family"),
                    "params": r.get("params"),
                    "mesh_hash": r.get("mesh_hash"),
                    "solve_hash": r.get("solve_hash"),
                    "n": r.get("n"),
                    "terms": r.get("terms"),
                }
        for h, rec in best.items():
            rec.update({
                "run": run_dir.name,
                "run_dir": run_dir.as_posix(),
                "config_name": rj.get("config_name"),
                "brief": brief_name(rj),
                "run_objective_version": rj.get("objective_version"),
                "backend": rj.get("backend"),
                "status": rj.get("status"),
            })
            recs.append(rec)
    return recs


def finalist_estimate(rec: dict) -> dict:
    """Finalist-tier mesh estimate from the run's own config.yaml (no meshing)."""
    cfg_path = REPO / "runs" / rec["run"] / "config.yaml"
    out: dict = {"cfg_ok": False}
    if not cfg_path.exists():
        return out
    try:
        cfg = load_config(cfg_path)
    except Exception as exc:  # brief-relative paths / generator routes can refuse
        out["cfg_error"] = f"{type(exc).__name__}: {exc}"
        return out
    m = cfg.mesh
    cap_screen = int(m.dof_cap("screen"))
    cap_fin = int(m.dof_cap("finalist"))
    ms = mesh_spec("finalist", cfg)
    # ``max_triangles`` is a FULL-DOMAIN-EQUIVALENT ceiling (01_CONTRACTS s6); the solved quarter
    # mesh gets at most max_triangles / quadrant_factor, and solved DOFs = that * dof_per_triangle.
    from hornlab_search.mesh import sizing  # local: keeps the offline import surface small
    tri_ceiling_full = int(ms.max_triangles)
    qf = sizing.QUADRANT_FACTOR[str(m.quadrants)]
    tri_ceiling_solved = tri_ceiling_full / qf
    dof_ceiling_solved = tri_ceiling_solved * float(m.dof_per_triangle)
    res = sizing.res_mm_for(float(m.epw), float(ms.f_max_hz))
    out.update({
        "cfg_ok": True,
        "dof_cap_screen": cap_screen,
        "dof_cap_finalist": cap_fin,
        "epw": float(m.epw),
        "quadrants": str(m.quadrants),
        "max_triangles_finalist_full_equiv": tri_ceiling_full,
        "triangles_ceiling_solved": round(tri_ceiling_solved, 1),
        "dof_ceiling_solved": round(dof_ceiling_solved, 1),
        "dof_per_triangle": float(m.dof_per_triangle),
        "res_mm_mouth": round(res["mouth"], 4),
        "f_max_finalist": float(ms.f_max_hz),
        "n_freqs_finalist": len(__import__(
            "hornlab_search.config", fromlist=["mode_freqs"]).mode_freqs("finalist", cfg)),
        "backend": cfg.solve.backend,
        "balloon_points_finalist": cfg.solve.balloon_points("finalist"),
        "config_name": cfg.name,
        "brief": Path(str(cfg.raw.get("brief_file", ""))).name,
    })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", metavar="PATH")
    args = ap.parse_args()
    recs = scan()
    home = [r for r in recs if r["brief"] == HOME_BRIEF]
    home.sort(key=lambda r: r["objective"])
    report = {"home_brief": HOME_BRIEF, "n_home_rows": len(home), "rows": home}
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"ok design-hash rows under {HOME_BRIEF}: {len(home)} from "
          f"{len({r['run'] for r in home})} run dirs")
    print(f"{'rank':>4} {'J':>9} {'design':>13} {'run':>34} {'cfg':>34} {'tri':>8} {'dof':>8}")
    for i, r in enumerate(home[:25], 1):
        fe = finalist_estimate(r)
        print(f"{i:>4} {r['objective']:9.4f} {r['design_hash']:>13} {r['run']:>34} "
              f"{str(r['config_name'])[:34]:>34} {str(r.get('n_triangles')):>8} {str(r.get('n_dof')):>8}")
        print(f"      finalist: {json.dumps(fe, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
