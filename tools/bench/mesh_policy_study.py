"""WP4 mesh-sizing study: baseline vs opt-in curvature policy, no solve required.

Meshes ONE design (the config's seed, or ``--design-json``) once per ``--curvature`` value, with
the production ``build_mesh`` (so every guard, the dof cap and the symmetry pairing apply), and
reports per arm: triangles (E), vertices (N, = P1 dofs), edge-length min / mean / p95 / max, and
build seconds, plus the ratios against the baseline arm (curvature 0 = today's mesh exactly).

The policy only exists on the CAD route (``mesh/step_build.py``: designs whose params carry
``"cad"``, e.g. the MEH seed). A formula or grid design ignores it; the report says so
(``policy_effective: false``) instead of pretending a comparison.

``--solve`` additionally runs one production solve per arm (same SolveSpec path as evaluate) and
compares the complex-free SPL / on-axis arrays against the baseline arm. A smaller mesh is only an
improvement if that comparison holds against a finer converged reference (packet §5.2); this tool
reports the numbers, it does not decide.

    .venv\\Scripts\\python.exe tools\\bench\\mesh_policy_study.py --config examples\\<meh config>.yaml ^
        --curvature 0,8,12,20 --out runs\\mesh_policy_study_1
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402


def edge_stats(xyz: np.ndarray, tri: np.ndarray) -> dict:
    """Unique-edge length statistics (metres -> millimetres) of a triangle mesh."""
    tri = np.asarray(tri, dtype=np.int64).reshape(-1, 3)
    xyz = np.asarray(xyz, dtype=float)
    e = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
    e.sort(axis=1)
    e = np.unique(e, axis=0)
    length_mm = np.linalg.norm(xyz[e[:, 0]] - xyz[e[:, 1]], axis=1) * 1000.0
    return {"n_edges": int(len(e)), "edge_min_mm": float(length_mm.min()),
            "edge_mean_mm": float(length_mm.mean()),
            "edge_p95_mm": float(np.percentile(length_mm, 95)),
            "edge_max_mm": float(length_mm.max())}


def compare_to_baseline(arms: list[dict]) -> list[dict]:
    """Add ratios against the first arm (the baseline): N, E, build time. Pure."""
    if not arms:
        return arms
    b = arms[0]
    for a in arms:
        for k, name in (("n_vertices", "N_ratio"), ("n_triangles", "E_ratio"),
                        ("build_s", "build_time_ratio")):
            a[name] = (a[k] / b[k]) if b.get(k) else None
    return arms


def parse_curvatures(text: str) -> list[float]:
    vals = [float(p) for p in str(text).split(",") if p.strip()]
    if not vals:
        raise ValueError("--curvature needs at least one value")
    if vals[0] != 0.0:
        vals.insert(0, 0.0)                    # the baseline arm is always first
    if any(v < 0 or v > 100 for v in vals):
        raise ValueError("curvature values must be in [0, 100]")
    return vals


def mesh_arm(design, cfg, mode: str, npts: float, out_dir: Path) -> dict:
    from hornlab_search import config as config_mod
    from hornlab_search.mesh import build
    mspec = dataclasses.replace(config_mod.mesh_spec(mode, cfg), curvature_npts=float(npts))
    t0 = time.perf_counter()
    res = build.build_mesh(design, mspec, cfg, out_dir, mode=mode)
    build_s = time.perf_counter() - t0
    summary, xyz, tri = build.read_msh_summary(Path(res.path), return_arrays=True)
    row = {"curvature_npts": float(npts), "mesh_hash": mspec.hash(), "build_s": build_s,
           "n_triangles": int(summary["n_triangles"]), "n_vertices": int(summary["n_nodes_used"]),
           "est_dofs": int(summary["n_nodes_used"]), "mesh_path": res.path,
           "res_mm": json.dumps(res.res_mm), **edge_stats(xyz, tri)}
    return row


def solve_arm(design, cfg, mode: str, mesh_path: str, freqs) -> dict:
    sys.path.insert(0, str(Path(__file__).parent))
    import throughput_matrix as tm
    from hornlab_search.solve import worker
    mesh = tm.mesh_from_msh(Path(mesh_path), cfg)
    spec = tm.production_solve_spec(cfg, mode, freqs)
    backend = tm.make_backend(cfg, None)
    worker.warm(backend)
    t0 = time.perf_counter()
    out = backend.solve(mesh, spec)
    row = {"solve_ok": bool(out.ok), "solve_wall_s": time.perf_counter() - t0}
    if out.ok:
        r = out.response
        row["on_axis_h_db"] = [float(x) for x in np.asarray(r.spl_h_db)[:, r.axis_index]]
        row["n_dof_solver"] = r.n_dof
    else:
        row["solve_error"] = (out.message or "")[:300]
    return row


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Mesh sizing policy study (WP4): baseline vs curvature")
    p.add_argument("--config", required=True)
    p.add_argument("--mode", default="screen", choices=("screen", "verify", "final"))
    p.add_argument("--curvature", default="0,12", help="comma list of Mesh.MeshSizeFromCurvature values")
    p.add_argument("--design-json", default=None, help="designs/<hash>/design.json instead of the seed")
    p.add_argument("--solve", action="store_true", help="also solve each arm (GPU; one at a time)")
    p.add_argument("--freq-set", default="12")
    p.add_argument("--out", default=None)
    a = p.parse_args(argv)

    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.types import Design
    cfg = load_config(a.config)
    if a.design_json:
        d = json.loads(Path(a.design_json).read_text(encoding="utf-8"))
        design = Design(d["family"], d["params"])
    else:
        design = DesignSpace.from_config(cfg).seed
    effective = isinstance(design.params, dict) and "cad" in design.params
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(a.out) if a.out else ROOT / "runs" / f"mesh_policy_study_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    if not effective:
        print("NOTE: this design has no 'cad' block; the curvature policy only applies to the CAD "
              "route, so every arm will equal the baseline (policy_effective = false).", flush=True)

    arms = []
    for npts in parse_curvatures(a.curvature):
        label = f"curv{npts:g}"
        print(f"meshing arm {label} ...", flush=True)
        try:
            row = mesh_arm(design, cfg, a.mode, npts, out / label)
        except Exception as exc:  # noqa: BLE001 - report the failure as an arm result
            row = {"curvature_npts": npts, "error": f"{type(exc).__name__}: {exc}"[:400]}
        row["policy_effective"] = effective
        arms.append(row)
    ok_arms = [r for r in arms if "error" not in r]
    compare_to_baseline(ok_arms)
    if a.solve and ok_arms:
        from throughput_matrix import resolve_freq_set
        freqs = resolve_freq_set(a.freq_set, cfg)
        from hornlab_search.search.gpulock import gpu_lock
        try:
            with gpu_lock("tools/bench/mesh_policy_study.py --solve"):
                for r in ok_arms:
                    r.update(solve_arm(design, cfg, a.mode, r["mesh_path"], freqs))
                    base = ok_arms[0].get("on_axis_h_db")
                    if base and r.get("on_axis_h_db"):
                        r["max_abs_on_axis_diff_db"] = float(np.max(np.abs(
                            np.asarray(base) - np.asarray(r["on_axis_h_db"]))))
        finally:
            from hornlab_search.solve import worker
            try:
                worker.shutdown(verify=True)
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: worker.shutdown failed: {exc!r}")
    (out / "mesh_policy_study.json").write_text(json.dumps({"config": a.config, "arms": arms},
                                                           indent=1, default=str), encoding="utf-8")
    keys = list(dict.fromkeys(k for r in arms for k in r if k != "on_axis_h_db"))
    with open(out / "mesh_policy_study.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(arms)
    for r in arms:
        if "error" in r:
            print(f"  curvature {r['curvature_npts']:g}: ERROR {r['error']}")
        else:
            print(f"  curvature {r['curvature_npts']:g}: N={r['n_vertices']} E={r['n_triangles']} "
                  f"edge p95={r['edge_p95_mm']:.2f} mm max={r['edge_max_mm']:.2f} mm "
                  f"build={r['build_s']:.2f}s  N/N0={r.get('N_ratio'):.3f}")
    print(f"wrote {out}")
    return 0 if all("error" not in r for r in arms) else 1


if __name__ == "__main__":
    raise SystemExit(main())
