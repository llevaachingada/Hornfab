"""WP3 pilot: one CPU-BEM lane and one CUDA lane solving DISTINCT candidates at the same time.

BENCH ONLY, not a production scheduler. Question answered: does aggregate valid candidates/hour
rise when a CPU BEM lane runs next to the GPU lane, with identical outputs and no CUDA regression?

Isolation (packet §3 WP3 "critical host isolation"):
  * each lane is its OWN PROCESS (own PID tree, own environment, own Julia host);
  * each lane gets its own ``HORNLAB_BEAT_WORKER_DIR`` (``<out>/lane_<name>/workers``);
  * the CPU lane gets ``JULIA_NUM_THREADS`` / BLAS thread limits (``--cpu-threads``);
  * lanes call ``BeatBackend.solve_raw`` directly, NOT ``worker.warm`` / ``worker.recover_after_failure``
    (those clear or kill EVERY BEAT host on the machine and would take the other lane down);
  * cleanup kills only host trees that descend from the lane's own process (never by image name).
  * a start barrier (``go`` file) makes both lanes begin solving together after both are warm.

Phases: (1) CUDA lane alone, (2) CPU lane alone (serial references + parity fixtures), (3) both
together. ``report.json`` carries per-lane time, slowdown vs alone, aggregate candidates/hour vs
the GPU alone and vs the ideal sum, and a parity check (concurrent vs serial arrays, per candidate).

    .venv\\Scripts\\python.exe tools\\bench\\cpu_gpu_concurrent.py --config examples\\osse_baseline_fusedcuda.yaml ^
        --mesh-gpu runs\\a\\mesh.msh --mesh-cpu runs\\b\\mesh.msh --n-per-lane 3 --freq-set 12 --cpu-threads 4
    .venv\\Scripts\\python.exe tools\\bench\\cpu_gpu_concurrent.py --config examples\\osse_baseline.yaml --fake --n-per-lane 3
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np  # noqa: E402

import throughput_matrix as tm  # noqa: E402

PARITY_TOL_DB = 0.05      # concurrent vs serial of the SAME lane/backend: expected ~0 (same arithmetic)


# ------------------------------------------------------------------ pure helpers (offline-tested)


def descends_from(procs, pid: int, root_pid: int) -> bool:
    """True when ``pid`` is ``root_pid`` or one of its descendants in the process table."""
    ppid = {p.pid: p.ppid for p in procs}
    seen = set()
    while pid in ppid and pid not in seen:
        if pid == root_pid:
            return True
        seen.add(pid)
        pid = ppid[pid]
    return pid == root_pid


def own_host_roots(procs, my_pid: int) -> list:
    """BEAT host roots in ``procs`` that belong to ``my_pid``'s tree (and nobody else's)."""
    from hornlab_search.solve import worker
    return [r for r in worker.beat_host_roots(procs) if descends_from(procs, r.pid, my_pid)]


def lane_env(name: str, out_dir: Path, *, cpu_threads: int | None, base: dict | None = None) -> dict:
    """The environment of one lane process: own worker registry, CPU thread limits."""
    env = dict(os.environ if base is None else base)
    env["HORNLAB_BEAT_WORKER_DIR"] = str(Path(out_dir) / f"lane_{name}" / "workers")
    if name == "cpu" and cpu_threads:
        for k in ("JULIA_NUM_THREADS", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
            env[k] = str(int(cpu_threads))
    return env


def summarize_lane(result: dict) -> dict:
    secs = [c["seconds"] for c in result["candidates"] if c["ok"]]
    s = tm.summarize_values(secs)
    return {"lane": result["lane"], "n": len(result["candidates"]), "failures": sum(
        1 for c in result["candidates"] if not c["ok"]), "median_s": s["median"],
        "start": result["t_start"], "end": result["t_end"], "wall_s": result["t_end"] - result["t_start"]}


def aggregate_report(serial: dict, concurrent: dict, tol_db: float = PARITY_TOL_DB) -> dict:
    """serial / concurrent: ``{lane: lane_result}``. Pure: derives every number from lane results."""
    ser = {k: summarize_lane(v) for k, v in serial.items()}
    con = {k: summarize_lane(v) for k, v in concurrent.items()}
    n_total = sum(s["n"] - s["failures"] for s in con.values())
    window = (max(s["end"] for s in con.values()) - min(s["start"] for s in con.values())) if con else None
    agg_cph = tm.candidates_per_hour(window / n_total) if window and n_total else None
    cph_alone = {k: (3600.0 * (s["n"] - s["failures"]) / s["wall_s"]) if s["wall_s"] else None
                 for k, s in ser.items()}
    ideal = sum(v for v in cph_alone.values() if v)
    per_lane = {}
    for k, s in con.items():
        base = ser.get(k, {}).get("median_s")
        per_lane[k] = {"concurrent_median_s": s["median_s"], "alone_median_s": base,
                       "slowdown": (s["median_s"] / base) if base and s["median_s"] else None,
                       "failures": s["failures"]}
    parity = {}
    for k in concurrent:
        diffs = []
        for cs, cc in zip(serial.get(k, {}).get("fingerprints", []), concurrent[k].get("fingerprints", [])):
            p = tm.parity(cs, cc)
            diffs.append(max(p.get("max_abs_spl_h_db", float("inf")), p.get("max_abs_spl_v_db", float("inf")))
                         if p.get("freqs_equal") and p.get("shape_equal") else float("inf"))
        parity[k] = {"n_compared": len(diffs), "max_abs_spl_db": max(diffs) if diffs else None,
                     "ok": bool(diffs) and max(diffs) <= tol_db}
    gpu_alone = cph_alone.get("cuda")
    gain = (agg_cph / gpu_alone) if agg_cph and gpu_alone else None
    cuda_slow = per_lane.get("cuda", {}).get("slowdown")
    failures = sum(v["failures"] for v in per_lane.values())
    return {
        "serial_per_lane": ser, "concurrent_per_lane": per_lane, "window_s": window,
        "aggregate_candidates_per_hour": agg_cph, "candidates_per_hour_alone": cph_alone,
        "ideal_sum_candidates_per_hour": ideal or None, "gain_vs_gpu_alone": gain,
        "efficiency_vs_ideal": (agg_cph / ideal) if agg_cph and ideal else None,
        "cuda_slowdown": cuda_slow, "parity": parity,
        "adopt_hint": bool(gain and gain > 1.05 and failures == 0 and all(p["ok"] for p in parity.values())),
        "adopt_hint_note": "hint only: needs gain > 1.05, zero failures, parity ok, AND a repeat run "
                           "(RUNBOOK gate); CPU contention can wipe the gain",
    }


# ------------------------------------------------------------------ one lane


def release_own_hosts() -> list[int]:
    """End this lane's Julia host: library call first (scoped by this process's worker dir), then
    kill only host trees that descend from THIS process. Never by image name."""
    killed: list[int] = []
    try:
        import hornlab_beat_bem as beat
        beat.shutdown_workers()
    except Exception as exc:  # noqa: BLE001
        print(f"[lane] shutdown_workers: {exc!r}", flush=True)
    try:
        from hornlab_search.solve import worker
        time.sleep(1.0)
        for r in own_host_roots(worker.list_processes(), os.getpid()):
            worker.kill_tree(r.pid)
            killed.append(r.pid)
    except Exception as exc:  # noqa: BLE001
        print(f"[lane] own-host cleanup: {exc!r}", flush=True)
    return killed


def run_lane(spec: dict) -> dict:
    """Solve ``n`` candidates (cycling through ``meshes``) on one backend. ``spec`` keys: lane,
    device, config, mode, freq_set, meshes, n, out, fake, go_file, ready_file."""
    from hornlab_search.config import load_config
    cfg = load_config(spec["config"])
    freqs = tm.resolve_freq_set(spec["freq_set"], cfg)
    sspec = tm.production_solve_spec(cfg, spec["mode"], freqs)
    device = spec["device"]
    extra = {k: v for k, v in dict(sspec.extra or {}).items() if k != "worker_restart_every"}
    if device != "cuda":
        extra.pop("cuda_fused", None)
    sspec = __import__("dataclasses").replace(sspec, backend=f"beat_{device}", extra=extra)
    from hornlab_search.types import MeshResult
    meshes = [tm.mesh_from_msh(Path(p), cfg) if not spec["fake"] else
              MeshResult(path=str(p), n_triangles=1000, n_dof=1234, quadrants=cfg.mesh.quadrants,
                         symmetry_plane="yz+xz", res_mm={}, bbox_m=(0.0, 0.0, 0.0, 0.3, 0.2, 0.25),
                         seconds=0.0) for p in spec["meshes"]]
    if spec["fake"]:
        backend = tm.FakeBackend(None, per_freq_s=0.02 if device == "cuda" else 0.05)
    else:
        from hornlab_search.solve.beat import BeatBackend
        kw = {"cuda_fused": bool(getattr(cfg.solve, "cuda_fused", False))} if device == "cuda" else {}
        backend = BeatBackend(device, timeout_s=float(cfg.solve.timeout_s), track_vram=False, **kw)
    t_warm = time.perf_counter()
    backend.warm()
    warm_s = time.perf_counter() - t_warm
    if spec.get("ready_file"):
        Path(spec["ready_file"]).write_text("ready", encoding="utf-8")
    go = spec.get("go_file")
    if go:                                          # start barrier: wait until the parent says go
        while not Path(go).exists():
            time.sleep(0.05)
    out_dir = Path(spec["out"])
    out_dir.mkdir(parents=True, exist_ok=True)
    cands, fps = [], []
    t_start = time.time()
    try:
        for i in range(int(spec["n"])):
            mesh = meshes[i % len(meshes)]
            t0 = time.perf_counter()
            try:
                if spec["fake"]:
                    out = backend.solve(mesh, sspec)
                    resp = out.response
                else:
                    from hornlab_search.solve import beat as beat_mod
                    raw = backend.solve_raw(mesh, sspec)           # no worker.* recovery: lane-safe
                    resp = beat_mod._to_response(raw, sspec, mesh)
                ok, err = True, ""
            except Exception as exc:  # noqa: BLE001
                resp, ok, err = None, False, f"{type(exc).__name__}: {exc}"[:400]
            cands.append({"i": i, "mesh": str(spec["meshes"][i % len(meshes)]), "ok": ok, "error": err,
                          "seconds": time.perf_counter() - t0})
            if ok:
                fp = tm.fingerprint(resp)
                fps.append(fp)
                np.savez(out_dir / f"cand_{i}.npz", **{k: v for k, v in fp.items() if v is not None})
            print(f"[lane {spec['lane']}] candidate {i}: {'OK' if ok else 'FAIL ' + err} "
                  f"{cands[-1]['seconds']:.2f}s", flush=True)
            if not ok:
                break                                          # a failed lane stops; no host recovery here
    finally:
        t_end = time.time()
        killed = [] if spec["fake"] else release_own_hosts()
    return {"lane": spec["lane"], "device": device, "warm_s": warm_s, "candidates": cands,
            "t_start": t_start, "t_end": t_end, "killed_own_hosts": killed, "fingerprints": fps}


def load_lane_result(out_dir: Path, n: int) -> dict:
    res = json.loads((out_dir / "lane_result.json").read_text(encoding="utf-8"))
    res["fingerprints"] = []
    for i in range(n):
        f = out_dir / f"cand_{i}.npz"
        if f.exists():
            z = np.load(f, allow_pickle=False)
            res["fingerprints"].append({k: (z[k] if k in z.files else None) for k in
                                        ("freqs_hz", "spl_h_db", "spl_v_db", "spl_balloon_db", "z_throat")})
    return res


def save_lane_result(res: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    slim = {k: v for k, v in res.items() if k != "fingerprints"}
    (out_dir / "lane_result.json").write_text(json.dumps(slim, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ orchestration


def launch_lanes(specs: list[dict], *, executor: str, out_dir: Path, cpu_threads: int | None,
                 barrier: bool) -> dict:
    """Run lane specs together. ``executor`` 'process' (real runs) or 'thread' (offline/fake)."""
    go_file = out_dir / f"go_{int(time.time() * 1e3)}"
    for s in specs:
        s["ready_file"] = str(out_dir / f"ready_{s['lane']}_{os.getpid()}_{id(s)}")
        s["go_file"] = str(go_file) if barrier and len(specs) > 1 else None
    results: dict = {}
    handles = []
    for s in specs:
        lane_dir = Path(s["out"])
        lane_dir.mkdir(parents=True, exist_ok=True)
        if executor == "thread":
            def target(spec=s):
                results[spec["lane"]] = run_lane(spec)
            th = threading.Thread(target=target, name=f"lane-{s['lane']}")
            th.start()
            handles.append(th)
        else:
            sp = lane_dir / "spec.json"
            sp.write_text(json.dumps(s), encoding="utf-8")
            env = lane_env(s["lane"], out_dir, cpu_threads=cpu_threads)
            proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--lane-child", str(sp)],
                                    env=env, cwd=str(ROOT))
            handles.append(proc)
    if go_file and specs[0]["go_file"]:
        deadline = time.time() + 900
        while time.time() < deadline and not all(Path(s["ready_file"]).exists() for s in specs):
            time.sleep(0.1)
        go_file.write_text("go", encoding="utf-8")
    for h in handles:
        if isinstance(h, threading.Thread):
            h.join()
        else:
            h.wait()
    if executor != "thread":
        for s in specs:
            results[s["lane"]] = load_lane_result(Path(s["out"]), int(s["n"]))
    return results


def lane_spec(name: str, device: str, a, meshes: list[str], out_dir: Path, phase: str) -> dict:
    return {"lane": name, "device": device, "config": a.config, "mode": a.mode, "freq_set": a.freq_set,
            "meshes": meshes, "n": int(a.n_per_lane), "out": str(out_dir / phase / f"lane_{name}"),
            "fake": bool(a.fake)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="CPU lane + CUDA lane concurrent pilot (WP3, bench only)")
    p.add_argument("--config", required=False)
    p.add_argument("--mode", default="screen", choices=("screen", "verify", "final"))
    p.add_argument("--mesh-gpu", action="append", default=[])
    p.add_argument("--mesh-cpu", action="append", default=[])
    p.add_argument("--n-per-lane", type=int, default=3)
    p.add_argument("--freq-set", default="12")
    p.add_argument("--cpu-threads", type=int, default=4)
    p.add_argument("--out", default=None)
    p.add_argument("--fake", action="store_true", help="fake solver in threads: offline check, no GPU")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--lane-child", default=None, help="internal: run one lane from a spec.json")
    a = p.parse_args(argv)
    if a.lane_child:                                   # child process entry point
        spec = json.loads(Path(a.lane_child).read_text(encoding="utf-8"))
        res = run_lane(spec)
        for i, fp in enumerate(res["fingerprints"]):
            pass                                       # fingerprints already saved per candidate
        save_lane_result(res, Path(spec["out"]))
        return 0 if all(c["ok"] for c in res["candidates"]) else 1
    if not a.config:
        p.error("--config is required")
    if a.fake and not a.mesh_gpu:
        a.mesh_gpu, a.mesh_cpu = ["fake_gpu.msh"], ["fake_cpu.msh"]
    if not a.mesh_gpu:
        print("Pass --mesh-gpu PATH (and --mesh-cpu PATH; repeat for several candidates).", file=sys.stderr)
        return 2
    a.mesh_cpu = a.mesh_cpu or list(a.mesh_gpu)
    if a.mesh_cpu == a.mesh_gpu:
        print("NOTE: both lanes use the same mesh list; contention is measured but 'distinct "
              "candidates' is not - pass different --mesh-cpu for the real pilot.", flush=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(a.out) if a.out else ROOT / "runs" / f"bench_cpu_gpu_concurrent_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = {"phases": ["cuda_alone", "cpu_alone", "concurrent"], "n_per_lane": a.n_per_lane,
            "freq_set": a.freq_set, "cpu_threads": a.cpu_threads, "mesh_gpu": a.mesh_gpu,
            "mesh_cpu": a.mesh_cpu, "isolation": "separate processes, own HORNLAB_BEAT_WORKER_DIR, "
            "no worker.* global kills, own-tree cleanup only"}
    print(json.dumps(plan, indent=1))
    if a.dry_run:
        return 0
    executor = "thread" if a.fake else "process"
    if not a.fake:
        from hornlab_search.search.gpulock import gpu_lock
        lock = gpu_lock("tools/bench/cpu_gpu_concurrent.py")
    else:
        import contextlib
        lock = contextlib.nullcontext()
    with lock:
        serial = {}
        serial.update(launch_lanes([lane_spec("cuda", "cuda", a, a.mesh_gpu, out_dir, "serial")],
                                   executor=executor, out_dir=out_dir, cpu_threads=None, barrier=False))
        serial.update(launch_lanes([lane_spec("cpu", "cpu", a, a.mesh_cpu, out_dir, "serial")],
                                   executor=executor, out_dir=out_dir, cpu_threads=a.cpu_threads, barrier=False))
        conc = launch_lanes([lane_spec("cuda", "cuda", a, a.mesh_gpu, out_dir, "concurrent"),
                             lane_spec("cpu", "cpu", a, a.mesh_cpu, out_dir, "concurrent")],
                            executor=executor, out_dir=out_dir, cpu_threads=a.cpu_threads, barrier=True)
    report = aggregate_report(serial, conc)
    report["plan"] = plan
    (out_dir / "report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(f"wrote {out_dir / 'report.json'}")
    print(f"aggregate {report['aggregate_candidates_per_hour']} cand/h vs GPU alone "
          f"{report['candidates_per_hour_alone'].get('cuda')} (gain {report['gain_vs_gpu_alone']}); "
          f"CUDA slowdown {report['cuda_slowdown']}; parity ok "
          f"{ {k: v['ok'] for k, v in report['parity'].items()} }; adopt_hint {report['adopt_hint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
