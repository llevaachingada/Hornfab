"""Frozen-grid acoustic A/B across saved-mesh policy arms (CPU backend by default).

Companion to ``mesh_policy_ab.py``: builds the same design under several mesh policies, solves
every arm on ONE frozen frequency grid with the SAME backend and observation spec, and writes the
convergence table the variable-mesh pass needs (on-axis, H/V polars, balloon DI, beamwidths,
normalised throat impedance, complex-pressure error).

The default backend is ``beat_cpu`` so the whole comparison can run in the CPU lane while a CUDA
queue owns the GPU.  The solver formulation is the same BEAT library; only the device differs, so
relative mesh error is meaningful.  Never mix arms from different backends.

Usage::

    .venv\\Scripts\\python.exe tools/analysis/mesh_acoustic_ab.py \\
        --run runs/<run dir> --design <hash> --out <scratch dir> \\
        --arms 1.0:1,1.5:1,2.0:1,1.5:1.5 --backend beat_cpu \\
        [--screen-grid-profile hf12k_screen_v1] [--freqs "500,630,..."]

Writes ``<out>/ACOUSTIC_CONVERGENCE.csv``, ``<out>/ARMS.json`` and per-arm
``response.npz`` / ``metrics.json``.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools" / "analysis"))

from hornlab_search.config import load_config, solve_spec  # noqa: E402
from hornlab_search.search.evaluate import metrics_to_json  # noqa: E402
from hornlab_search.search.evaluate import make_context, metrics_from_response  # noqa: E402
from hornlab_search.solve import cache as solve_cache  # noqa: E402
from hornlab_search.solve.base import get_backend  # noqa: E402

import mesh_policy_ab as policy  # noqa: E402

TOOL = "mesh_acoustic_ab"


def _max_abs(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch {a.shape} vs {b.shape}")
    m = np.abs(a - b)
    return float(np.nanmax(m)) if m.size else float("nan")


def _complex_error(ref: np.ndarray, other: np.ndarray) -> tuple[float, float]:
    """Bounded relative complex error + phase error (degrees) over a common pressure field.

    The denominator is floored at 10% of the field's own peak so a deep null cannot turn a
    meaningful complex difference into an unbounded dB claim.
    """
    ref = np.asarray(ref, dtype=complex)
    other = np.asarray(other, dtype=complex)
    denom = np.maximum(np.abs(ref), 0.1 * float(np.max(np.abs(ref))))
    rel = np.abs(ref - other) / np.maximum(denom, 1e-30)
    phase = np.degrees(np.abs(np.angle(other / np.where(np.abs(ref) > 0, ref, 1.0))))
    return float(np.nanmax(rel)), float(np.nanmax(phase))


def _null_shift_db(freqs: np.ndarray, ref_db: np.ndarray, other_db: np.ndarray) -> float:
    """Worst absolute change in a local null depth, on the SAME on-axis trace (dB)."""
    if ref_db.size < 3:
        return float("nan")
    idx = np.arange(1, ref_db.size - 1)
    nulls = idx[(ref_db[1:-1] < ref_db[:-2]) & (ref_db[1:-1] < ref_db[2:])]
    if nulls.size == 0:
        return float("nan")
    return float(np.max(np.abs(ref_db[nulls] - other_db[nulls])))


def compare_arm(arm: dict, ref: dict) -> dict:
    a = arm["response"]
    r = ref["response"]
    freqs = np.asarray(a.freqs_hz, dtype=float)
    if not np.allclose(freqs, np.asarray(r.freqs_hz, dtype=float), rtol=0, atol=1e-6):
        raise ValueError(f"{arm['arm']}: frequency grid differs from reference")
    am, rm = arm["metrics"], ref["metrics"]
    row = {
        "arm": arm["arm"],
        "reference": ref["arm"],
        "rear_res_factor": arm["rear_res_factor"],
        "epw_multiplier": arm["epw_multiplier"],
        "n_triangles": arm["n_triangles"],
        "n_vertices": arm["n_vertices"],
        "dof_estimate": arm["dof_estimate"],
        "n_dof_solved": arm["n_dof_solved"],
        "mesh_seconds": arm["mesh_seconds"],
        "solve_seconds": arm["solve_seconds"],
        "n_freqs": int(freqs.size),
        "f_lo_hz": float(freqs[0]),
        "f_hi_hz": float(freqs[-1]),
        "on_axis_max_abs_db": _max_abs(rm.on_axis_db, am.on_axis_db),
        "polar_h_max_abs_db": _max_abs(r.spl_h_db, a.spl_h_db),
        "polar_v_max_abs_db": _max_abs(r.spl_v_db, a.spl_v_db),
        "di_max_abs_db": _max_abs(rm.di_db, am.di_db),
        "bw_h_max_abs_deg": _max_abs(rm.bw_h_deg, am.bw_h_deg),
        "bw_v_max_abs_deg": _max_abs(rm.bw_v_deg, am.bw_v_deg),
        "z_real_max_abs": _max_abs(rm.z_throat_real, am.z_throat_real),
        "z_imag_max_abs": _max_abs(np.imag(r.z_throat), np.imag(a.z_throat)),
        "on_axis_null_depth_shift_db": _null_shift_db(freqs, rm.on_axis_db, am.on_axis_db),
    }
    if r.p_h is not None and a.p_h is not None:
        e, ph = _complex_error(r.p_h, a.p_h)
        row["p_h_complex_rel_p95"] = e
        row["p_h_phase_max_deg"] = ph
    if r.p_balloon is not None and a.p_balloon is not None:
        e, ph = _complex_error(r.p_balloon, a.p_balloon)
        row["p_balloon_complex_rel_p95"] = e
        row["p_balloon_phase_max_deg"] = ph
    return row


COLUMNS = [
    "arm", "reference", "rear_res_factor", "epw_multiplier", "n_triangles", "n_vertices",
    "dof_estimate", "n_dof_solved", "mesh_seconds", "solve_seconds", "n_freqs", "f_lo_hz",
    "f_hi_hz", "on_axis_max_abs_db", "polar_h_max_abs_db", "polar_v_max_abs_db",
    "di_max_abs_db", "bw_h_max_abs_deg", "bw_v_max_abs_deg", "z_real_max_abs",
    "z_imag_max_abs", "on_axis_null_depth_shift_db", "p_h_complex_rel_p95",
    "p_h_phase_max_deg", "p_balloon_complex_rel_p95", "p_balloon_phase_max_deg",
]


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        if not math.isfinite(v):
            return "nan"
        return f"{v:.6g}"
    return str(v)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--design", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arms", default="1.0:1,1.5:1,2.0:1,1.5:1.5")
    ap.add_argument("--backend", default="beat_cpu")
    ap.add_argument("--brief", default=None, help="brief YAML override (new identity; same for all arms)")
    ap.add_argument("--screen-grid-profile", default=None)
    ap.add_argument("--freqs", default=None, help="explicit comma-separated screen frequencies")
    ap.add_argument("--reference-arm", default="rear1.5_epw1.5",
                    help="arm used as the numerical reference (default M3 fine mesh)")
    ap.add_argument("--timeout-s", type=float, default=3600.0)
    ap.add_argument("--julia-threads", type=int, default=4,
                    help="CPU-lane Julia threads (leave cores for the GPU lane)")
    args = ap.parse_args(argv)

    run = Path(args.run).resolve()
    out_dir = Path(args.out).resolve()
    if args.backend in ("beat_cpu", "bempp_cpu"):
        # Two-lane rule: a CPU solve owns the CPU worker registry and never touches GPU hosts.
        os.environ.setdefault("HORNLAB_BEAT_WORKER_DIR",
                              str(REPO_ROOT / "runs" / "lanes" / "cpu" / "workers"))
    out_dir.mkdir(parents=True, exist_ok=True)
    design = policy._load_design(run, args.design)
    cfg0 = load_config(run / "config.yaml", brief=args.brief)

    arms = []
    for factor, epw_mult in policy._parse_arms(args.arms):
        name = policy._arm_name(factor, epw_mult)
        print(f"=== arm {name}: mesh", flush=True)
        arm = policy.run_arm(cfg0, design, factor, epw_mult, out_dir / "mesh")
        cfg = load_config(run / "config.yaml", backend=args.backend, brief=args.brief)
        solve_raw = cfg.raw.setdefault("solve", {})
        if args.screen_grid_profile:
            solve_raw.pop("freq_grid", None)
            solve_raw["screen_grid"] = {"profile": args.screen_grid_profile}
        elif args.freqs:
            solve_raw.pop("freq_grid", None)
            solve_raw["screen_grid"] = {
                "freqs_hz": [float(v) for v in args.freqs.split(",") if v.strip()]}
        sspec = solve_spec("screen", cfg)
        print(f"    solve {args.backend}: {len(sspec.freqs_hz)} freqs "
              f"{sspec.freqs_hz[0]:g}-{sspec.freqs_hz[-1]:g} Hz, {arm['n_triangles']} tri",
              flush=True)
        backend = get_backend(args.backend, timeout_s=float(args.timeout_s),
                              **({"julia_threads": int(args.julia_threads)}
                                 if args.backend == "beat_cpu" else {}))
        from hornlab_search.solve import worker

        worker.warm(backend)
        mr = policy.mesh_result_for(arm)
        t0 = time.perf_counter()
        outcome = backend.solve(mr, sspec)
        solve_seconds = time.perf_counter() - t0
        if not outcome.ok or outcome.response is None:
            raise RuntimeError(f"{name}: solve failed: {(outcome.message or '')[:1000]}")
        resp = outcome.response
        target = make_context(cfg).target
        metrics = metrics_from_response(resp, target, mesh=mr, design=design)
        solve_cache.save_response(Path(arm["mesh_path"]).parent / "response.npz", resp)
        (Path(arm["mesh_path"]).parent / "metrics.json").write_text(
            json.dumps(metrics_to_json(metrics), indent=1, sort_keys=True), encoding="utf-8")
        arm.update({
            "backend": args.backend,
            "freqs_hz": list(sspec.freqs_hz),
            "observation": {
                "distance_m": sspec.observation.distance_m,
                "angle_count": sspec.observation.angle_count,
                "balloon": sspec.observation.balloon,
                "balloon_points": sspec.observation.balloon_points,
            },
            "n_dof_solved": int(resp.n_dof or arm["n_vertices"]),
            "solve_seconds": float(solve_seconds),
            "response": resp,
            "metrics": metrics,
        })
        arms.append(arm)
        print(f"    solved in {solve_seconds:.1f} s, n_dof={arm['n_dof_solved']}", flush=True)


    ref = next((a for a in arms if a["arm"] == args.reference_arm), None)
    if ref is None:
        raise SystemExit(f"reference arm {args.reference_arm!r} was not built; "
                         f"built: {[a['arm'] for a in arms]}")
    rows = [compare_arm(a, ref) for a in arms]
    with (out_dir / "ACOUSTIC_CONVERGENCE.csv").open("w", newline="", encoding="utf-8") as fh:
        import csv

        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _fmt(row.get(k)) for k in COLUMNS})

    payload = {
        "tool": TOOL,
        "run": str(run),
        "design": args.design,
        "family": design.family,
        "backend": args.backend,
        "reference_arm": ref["arm"],
        "freqs_hz": list(ref["freqs_hz"]),
        "observation": ref["observation"],
        "arms": [{k: v for k, v in a.items()
                  if k not in ("response", "metrics", "report", "regions")} for a in arms],
        "comparisons": rows,
    }
    (out_dir / "ARMS.json").write_text(json.dumps(payload, indent=1, sort_keys=True, default=str),
                                       encoding="utf-8")
    if args.backend in ("beat_cpu", "bempp_cpu"):
        from hornlab_search.solve import worker

        try:
            worker.shutdown(verify=False)
        except Exception as exc:
            print(f"worker shutdown warning: {exc}", flush=True)
    print(f"wrote {out_dir / 'ACOUSTIC_CONVERGENCE.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





