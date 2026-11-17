"""Stage A single-axis acoustic A/B: identity gate and sequential runner (no optimizer).

Arms
  a0  the incumbent geometry (blend 0, bit-identical to ``klangfilm-lame-v1``)
  a1  H-plane throat angle only   theta_H 9.4631 -> 14.0 deg, theta_V pinned at its measured base
  a2  V-plane throat angle only   theta_V 9.4378 -> 5.0 deg,  theta_H pinned at its measured base

Everything except the intended angle key is identical between arms (same genes, blend 1, join 0.65,
gains 0), and every config carries the same brief/mesh/solve blocks, so the frequency grid, source
cap, mesh policy and solver settings are shared by construction.

The a0 arm is reused from the cached run ONLY when the identity gate passes: same geometry arrays,
same driver/brief, same mesh block, same solve block, same library SHAs. Otherwise a0 is solved.

``run`` takes the process-wide GPU lock itself; this runner sets ``HORNLAB_GPU_LOCK=refuse`` in the
child environment so an arm can never overlap another lane's GPU job. Arms run strictly one at a time.

Usage
  .venv\\Scripts\\python.exe tools/geometry/klangfilm_hv_ab.py --check
  .venv\\Scripts\\python.exe tools/geometry/klangfilm_hv_ab.py --execute
  .venv\\Scripts\\python.exe tools/geometry/klangfilm_hv_ab.py --wait-minutes 240 --execute
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

#: Path overrides let a measurement run from a pinned snapshot while runs/cache/dataset and the
#: evidence folder stay in the real checkout (shared GPU lock, shared solve cache).
RUNS = Path(os.environ.get("HORNLAB_HV_RUNS", ROOT / "runs"))
CONFIG_DIR = ROOT / "examples/typologies/klangfilm_hv_2026-11-16/configs"
A0_CONFIG = CONFIG_DIR / "a0.yaml"
ARMS = {"a1": CONFIG_DIR / "a1_h_only_single_axis.yaml",
        "a2": CONFIG_DIR / "a2_v_only_single_axis.yaml"}
CACHED = {"run_dir": RUNS / "20261116T205942Z-screen-8b22b5", "design_hash": "786caa6b08d7"}
EVIDENCE = Path(os.environ.get("HORNLAB_HV_EVIDENCE", ROOT / "docs/evidence/klangfilm_hv_2026-11-16"))
MANIFEST = EVIDENCE / "ab_manifest.json"

GEOMETRY_KEYS = ("mesh", "solve", "target", "weights", "objective", "grid", "driver", "envelope")


def _rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(Path(path).resolve())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gpu_state() -> dict:
    lock_path = RUNS / ".gpu.lock"
    state = {"lock_path": str(lock_path), "held": False, "holder": None, "live": False}
    if lock_path.is_file():
        try:
            holder = json.loads(lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            holder = None
        state["holder"] = holder
        state["held"] = holder is not None
        if holder:
            from hornlab_search.search.gpulock import _pid_alive
            state["live"] = bool(_pid_alive(int(holder.get("pid", -1))))
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu",
                              "--format=csv,noheader"], capture_output=True, text=True, timeout=20)
        state["nvidia_smi"] = out.stdout.strip() or out.stderr.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        state["nvidia_smi"] = f"unavailable: {exc}"
    return state


def identity_gate() -> dict:
    """Prove that the cached a0 response is reusable for this comparison."""
    from hornlab_search.config import load_config
    from hornlab_search.design.generators import klangfilm_lame_hv_family as hv
    from hornlab_search.design.generators import klangfilm_lame_family as legacy
    from hornlab_search.search.evaluate import collect_lib_shas

    cfg = load_config(A0_CONFIG)
    block = cfg.generator
    knobs = {k: float(v) for k, v in cfg.seed_params.items()}
    grid_keys = {k: float(block[k]) for k in ("n_phi", "n_s", "wall_thickness_mm")}

    hv_shape = {k[2:]: v for k, v in knobs.items()}
    hv_shape.update(grid_keys)
    legacy_shape = {k: v for k, v in hv_shape.items() if k in legacy.kernel.SHAPE_KEYS}
    brief_raw = cfg.brief or {}
    driver = brief_raw.get("driver") or {}
    brief = {"driver": {"exit_radius_mm": float(driver["exit_radius_mm"]),
                        "exit_angle_deg": float(driver["exit_angle_deg"])}}
    hv_pts, hv_meta = hv.kernel.make_grid(hv_shape, brief)
    legacy_pts, _ = legacy.kernel.make_grid(legacy_shape, brief)

    cached_cfg = yaml.safe_load((CACHED["run_dir"] / "config.yaml").read_text(encoding="utf-8"))
    cached_run = json.loads((CACHED["run_dir"] / "run.json").read_text(encoding="utf-8"))
    raw_cfg = yaml.safe_load(A0_CONFIG.read_text(encoding="utf-8"))
    blocks = {}
    for key in GEOMETRY_KEYS:
        a = _plain(raw_cfg.get(key))
        b = _plain(cached_cfg.get(key))
        if key in ("target", "weights", "objective", "grid"):
            a = _plain(brief_raw.get(key))
        blocks[key] = a == b
    # The run-directory config.yaml is a copy; its brief_file is relative to the ORIGINAL config path
    # recorded in run.json, not to runs/<id>/. Resolving it beside the copy is wrong.
    brief_paths = {}
    for cfg_path in (A0_CONFIG, ROOT / str(cached_run.get("config_path"))):
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        brief_paths[str(cfg_path)] = str((cfg_path.parent / raw["brief_file"]).resolve())
    lib_now = collect_lib_shas()
    return {
        "a0_config": _rel(A0_CONFIG),
        "cached_run": _rel(CACHED["run_dir"]),
        "cached_design": CACHED["design_hash"],
        "geometry_array_equal": bool(np.array_equal(hv_pts, legacy_pts)),
        "grid_sha256": hashlib.sha256(hv_pts.tobytes()).hexdigest(),
        "hv_meta_core_mode": hv_meta["core_mode"],
        "same_brief_path": len(set(brief_paths.values())) == 1,
        "brief_paths": brief_paths,
        "block_equal": blocks,
        "lib_shas_now": lib_now,
        "lib_shas_cached": cached_run.get("lib_shas"),
        "lib_shas_equal": lib_now == cached_run.get("lib_shas"),
        "cached_status": cached_run.get("status"),
        "reuse_a0": bool(np.array_equal(hv_pts, legacy_pts) and len(set(brief_paths.values())) == 1
                         and all(blocks.values()) and lib_now == cached_run.get("lib_shas")),
    }


def _plain(obj):
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    return obj


def _dirs_flags() -> list[str]:
    out = []
    for flag, key in (("--runs-dir", "HORNLAB_HV_RUNS"), ("--cache-dir", "HORNLAB_HV_CACHE"),
                      ("--dataset-dir", "HORNLAB_HV_DATASET")):
        value = os.environ.get(key)
        if value:
            out += [flag, value]
    return out


def _run_dir_set() -> set[str]:
    return {p.name for p in RUNS.iterdir() if p.is_dir()} if RUNS.is_dir() else set()


def run_arm(name: str, config: Path, timeout_s: int) -> dict:
    before = _run_dir_set()
    env = dict(os.environ, HORNLAB_GPU_LOCK="refuse", HORNLAB_BEAT_WORKER_DIR=str(RUNS / "lanes/gpu/workers"))
    t0 = time.time()
    proc = subprocess.run([sys.executable, "-m", "hornlab_search.cli", "run",
                           "--config", str(config), "--mode", "screen", *_dirs_flags()],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout_s)
    elapsed = time.time() - t0
    new = sorted(_run_dir_set() - before)
    out = {"arm": name, "config": str(config.resolve()), "config_sha256": _sha(config),
           "exit_code": proc.returncode, "elapsed_s": round(elapsed, 1),
           "stdout_tail": proc.stdout.strip().splitlines()[-4:],
           "stderr_tail": proc.stderr.strip().splitlines()[-4:], "run_dirs": new}
    if proc.returncode != 0 or len(new) != 1:
        out["ok"] = False
        return out
    run_dir = RUNS / new[0]
    best_path = run_dir / "best.json"
    if not best_path.is_file():
        out["ok"] = False
        out["error"] = "no best.json"
        return out
    best = json.loads(best_path.read_text(encoding="utf-8"))
    hash_ = best.get("design_hash")
    design_dir = run_dir / "designs" / str(hash_)
    resp = design_dir / "response.npz"
    meta = {}
    if resp.is_file():
        with np.load(resp, allow_pickle=False) as z:
            meta = json.loads(str(z["meta"])) if "meta" in z.files else {}
    out.update({
        "ok": bool(best.get("ok")),
        "run_dir": str(run_dir.resolve()),
        "design_hash": hash_,
        "objective": best.get("objective"),
        "terms": best.get("terms"),
        "has_response": resp.is_file(),
        "has_metrics": (design_dir / "metrics.json").is_file(),
        "n_dof": meta.get("n_dof") or meta.get("n_dof_source"),
        "n_triangles": meta.get("n_triangles"),
        "quadrants": meta.get("quadrants"),
        "mesh_scale": meta.get("mesh_scale"),
        "backend": meta.get("backend"),
        "angle_count": meta.get("angle_count"),
        "balloon_grid": meta.get("balloon_grid"),
        "solve_seconds": meta.get("solve_seconds"),
    })
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="identity gate + GPU state only (default)")
    ap.add_argument("--execute", action="store_true", help="run the arms sequentially")
    ap.add_argument("--wait-minutes", type=float, default=0.0,
                    help="poll until the GPU lock is free (or the deadline) before executing")
    ap.add_argument("--timeout-s", type=int, default=1800, help="per-arm wall timeout")
    ap.add_argument("--arms", nargs="+", default=None, metavar="NAME=PATH",
                    help="override the arm set, e.g. b1=examples/.../b1_balanced.yaml")
    ap.add_argument("--baseline", default=None, metavar="NAME=RUN:DESIGN:CONFIG",
                    help="reuse an already-solved baseline arm instead of re-solving A0")
    ap.add_argument("--manifest", default=None, help="override the manifest path")
    args = ap.parse_args(argv)
    global ARMS, MANIFEST
    if args.arms:
        ARMS = {item.split("=", 1)[0]: (ROOT / item.split("=", 1)[1]) for item in args.arms}
    if args.manifest:
        MANIFEST = Path(args.manifest)
    baseline = None
    if args.baseline:
        name, spec = args.baseline.split("=", 1)
        run, design, cfg = spec.split(":")
        baseline = (name, (ROOT / run).resolve(), design, (ROOT / cfg).resolve())
    if not args.execute:
        args.check = True

    gate = identity_gate()
    state = gpu_state()
    print("GPU state:", json.dumps({k: state[k] for k in ("held", "live", "nvidia_smi")}, ensure_ascii=False))
    if state["holder"]:
        print("  holder:", state["holder"].get("command"), "pid", state["holder"].get("pid"))
    print("A0 identity gate:")
    for key in ("geometry_array_equal", "grid_sha256", "same_brief_path", "lib_shas_equal",
                "cached_status", "reuse_a0"):
        print(f"  {key}: {gate[key]}")
    print("  blocks:", {k: v for k, v in gate["block_equal"].items()})
    if not gate["lib_shas_equal"]:
        print("  lib_shas changed since the cached run; a0 will be re-solved.")

    if args.check:
        print("\nArms:")
        for name, cfg_path in ARMS.items():
            raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            print(f"  {name}: {cfg_path.name} theta_H={raw['seed_params']['g_theta_h0_deg']} "
                  f"theta_V={raw['seed_params']['g_theta_v0_deg']}")
        print("\nNot executed. Run with --execute when the GPU is free.")
        return 0

    deadline = time.time() + args.wait_minutes * 60.0
    while state["live"]:
        if time.time() >= deadline:
            print("GPU still busy at the deadline; nothing launched.")
            return 3
        time.sleep(30)
        state = gpu_state()
    if state["live"]:
        print("GPU lock held by a live process; refusing to overlap.")
        return 3

    manifest = {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "identity_gate": gate, "gpu_state_at_start": state, "arms": {}}
    planned = list(ARMS.items())
    if baseline is not None:
        name, run_dir, design, cfg_path = baseline
        manifest["arms"][name] = {
            "arm": name, "reused": True, "reused_from": "explicit --baseline",
            "config": str(cfg_path), "run_dir": str(run_dir), "design_hash": design,
            "objective": json.loads((run_dir / "best.json").read_text(encoding="utf-8"))["objective"],
        }
        print(f"baseline {name} reused from {run_dir.name} / {design}")
    elif not gate["reuse_a0"]:
        planned.insert(0, ("a0", A0_CONFIG))
    else:
        manifest["arms"]["a0"] = {
            "arm": "a0", "reused": True,
            "config": str(A0_CONFIG.resolve()),
            "run_dir": str(CACHED["run_dir"].resolve()),
            "design_hash": CACHED["design_hash"],
            "objective": json.loads((CACHED["run_dir"] / "best.json").read_text())["objective"],
        }
    for name, cfg_path in planned:
        print(f"running {name} ({cfg_path.name}) ...", flush=True)
        result = run_arm(name, cfg_path, args.timeout_s)
        manifest["arms"][name] = result
        print(f"  exit={result['exit_code']} ok={result.get('ok')} dir={result.get('run_dir')}")
        if not result.get("ok"):
            manifest["stopped_on"] = name
            break
        MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST}")
    return 0 if all(a.get("ok") or a.get("reused") for a in manifest["arms"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
