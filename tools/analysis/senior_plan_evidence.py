"""One command for every senior-plan step that needs the owner's ``runs/`` (2026-11-17).

CPU only, no solve, read-only on ``runs/``. Writes under ``--out`` (default
``scratch/fable_architecture/.evidence/<utc>``):

  1. record_shadow   - WP 3.3/3.4: records + shadow-gate disagreements for the selected runs
  2. rescore         - WP 1.4: rescore the same runs under ``--brief`` (if given)
  3. floor           - WP 1.5: frequency noise floor from ``runs/study-*`` pairs (if ``--brief``)
  4. u3_cpu          - WP 4.1: U3 record-edit variants + validity (+ point-grid meshes if gmsh
                       loads) on the best stored design of each ``--u3-lane``

    .venv\\Scripts\\python.exe tools\\analysis\\senior_plan_evidence.py --runs-glob "runs\\2026111*" ^
        --brief examples\\briefs\\home_landscape_2026-11-15\\<v9 brief>.yaml ^
        --u3-lane hl__biradial_es_style_v7 --u3-lane hl__ext_throat_hvlaw_v7
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def best_design(runs, lane: str):
    """(run_dir, design_hash, J) of the lowest stored ok objective among runs of ``lane``."""
    import yaml
    best = None
    for run in runs:
        try:
            name = yaml.safe_load((run / "config.yaml").read_text(encoding="utf-8")).get("name")
        except Exception:  # noqa: BLE001
            continue
        if name != lane or not (run / "search.ndjson").is_file():
            continue
        for line in (run / "search.ndjson").read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            j = r.get("objective")
            if r.get("ok") and isinstance(j, (int, float)) and math.isfinite(j) \
                    and (run / "designs" / str(r.get("design_hash"))).is_dir():
                if best is None or j < best[2]:
                    best = (run, str(r["design_hash"]), float(j))
    return best


def u3_cpu(runs, lanes, out: Path) -> dict:
    from hornlab_search.config import load_config, mesh_spec
    from hornlab_search.geometry import edits as E
    from hornlab_search.geometry import record as R
    from hornlab_search.types import Design
    try:
        import gmsh  # noqa: F401
        from hornlab_search.mesh.grid_build import build_grid_mesh
        can_mesh = True
    except Exception:  # noqa: BLE001
        can_mesh = False
    result = {}
    for lane in lanes:
        b = best_design(runs, lane)
        if b is None:
            result[lane] = {"error": "no stored ok design found in the selected runs"}
            continue
        run, h, j = b
        cfg = load_config(run / "config.yaml")
        d = json.loads((run / "designs" / h / "design.json").read_text(encoding="utf-8"))
        rec = R.record_for_design(Design(d["family"], d["params"]), cfg)
        env = {k: float(v) for k, v in (
            ("width_mm", (cfg.brief.get("envelope") or {}).get("max_mouth_w_mm")),
            ("height_mm", (cfg.brief.get("envelope") or {}).get("max_mouth_h_mm")),
            ("depth_mm", (cfg.brief.get("envelope") or {}).get("max_depth_mm"))) if v is not None}
        rows = {}
        for name, v in [("control", rec), *E.u3_variants(rec).items()]:
            val = E.validity(v, rec, envelope_mm=env)
            if can_mesh:
                try:
                    build_grid_mesh(E.record_to_grid(v, wall_thickness_mm=rec.wall_thickness_mm or 3.0),
                                    mesh_spec("screen", cfg), Path(tempfile.mkdtemp()) / "m.msh", cfg,
                                    mode="screen")
                    val["mesh"] = "ok"
                except Exception as exc:  # noqa: BLE001
                    val["mesh"] = f"{type(exc).__name__}: {str(exc)[:160]}"
            rows[name] = val
        result[lane] = {"run": run.name, "design_hash": h, "stored_j": j,
                        "record_digest": rec.digest(), "variants": rows}
    (out / "u3_cpu.json").write_text(json.dumps(result, indent=1, default=float), encoding="utf-8")
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-glob", required=True)
    ap.add_argument("--brief")
    ap.add_argument("--u3-lane", action="append", default=[])
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    out = a.out or REPO / "scratch" / "fable_architecture" / ".evidence" / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out.mkdir(parents=True, exist_ok=True)
    runs = sorted(Path(p) for p in glob.glob(a.runs_glob) if (Path(p) / "config.yaml").is_file())
    summary: dict = {"runs": len(runs), "out": str(out)}
    from tools.analysis import record_shadow, rescore_identity
    record_shadow.main([*map(str, runs), "--out", str(out / "record_shadow")])
    summary["record_shadow"] = json.loads((out / "record_shadow" / "summary.json").read_text())
    if a.brief:
        summary["rescore"] = rescore_identity.rescore(runs, a.brief, out / "rescore")
        studies = sorted(Path(p) for p in glob.glob(str(REPO / "runs" / "study-*")))
        summary["floor"] = rescore_identity.floor(studies, a.brief, out / "floor", 28)
    if a.u3_lane:
        summary["u3_cpu"] = {k: {kk: vv for kk, vv in v.items() if kk != "variants"}
                             for k, v in u3_cpu(runs, a.u3_lane, out).items()}
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=float)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
