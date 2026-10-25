"""M3 GPU MEASUREMENT PACK on STORED designs (WP5a/b/c, WP7, WP8).

One job per fresh process; **importing this module starts no GPU work** (nothing runs unless
``main()`` is called). Each invocation reconstructs a stored design exactly the way the run
pipeline does (``designs/<hash>/design.json`` -> ``Design(family, params)``), re-solves it under
the stored run's own ``config.yaml`` plus an explicit override, and dumps one JSON payload with
the spec, dofs, per-frequency metrics, J and the Response meta (seam_check, source_motion,
balloon grid, timings).

Protocol (``CLAUDE.md`` "GPU / Julia hygiene" rules 1-7 + ``TOOLCHAIN.md`` M2):

* the caller clears stale Julia hosts and records the VRAM baseline BEFORE the job (the tool also
  does both, and prints them);
* one solve job per process, fresh ``--cache-dir`` (the mesh/solve caches are not keyed by library
  SHA, so an old entry would silently serve a stale response);
* ``nvidia-smi --query-gpu=memory.used`` is polled from a daemon THREAD (the M2 harness pattern),
  first sample = baseline, max = peak;
* every job ends with ``worker.shutdown(verify=True)`` in a ``finally`` and prints the outcome, so
  a surviving host is visible.

Commands
--------
``solve``
    Re-solve the stored design at the stored run's mode spec with overrides, through the normal
    ``search.evaluate.evaluate`` path (mesh cache, solve cache, metrics, objective, ndjson row,
    dataset record)::

        python tools/m3_measurement_pack.py solve \
            --run-dir runs/20261023T195300Z-verify-bdae12 --design-hash 59f57bc457cb \
            --mode verify --set solve.balloon_points_verify=2592 \
            --cache-dir scratch/m3_wp5b_axi_2592_cache \
            --out runs/m3_wp5b/axi_2592.json

``traces``
    WP5(a): ONE traced solve at the stored spec, then evaluate the exact exterior field from the
    boundary traces at r = 2, 10, 50 m (``solve/traces.py::field_from_traces``) and build a
    ``Response`` per radius (cuts at 73 angles + a balloon on the solver's theta-phi grid) so
    ``metrics_from_response`` sees ``meta['balloon_grid']`` and the sin(theta)-weighted DI path
    fires::

        python tools/m3_measurement_pack.py traces \
            --run-dir runs/20261023T195300Z-verify-bdae12 --design-hash 59f57bc457cb \
            --balloon-from runs/20261023T025720Z-screen-2002c3/designs/59f57bc457cb/response.npz \
            --cache-dir scratch/m3_wp5a_axi_cache --out runs/m3_wp5a/axi.json

``compare``
    Offline per-frequency deltas of a new job against a stored ``metrics.json`` (or another job
    JSON), with the CP-7f bars printed next to the maxima::

        python tools/m3_measurement_pack.py compare --new runs/m3_wp7/axi_rear2.0.json \
            --stored runs/20261023T025720Z-screen-2002c3/designs/59f57bc457cb/metrics.json
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Runnable as a plain script: put the repo root on sys.path (same pattern as
# tools/measure_fused_ceiling.py).
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from hornlab_search.config import load_config, mesh_spec, solve_spec  # noqa: E402
from hornlab_search.dataset.store import DatasetStore  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402
from hornlab_search.mesh.build import build_mesh  # noqa: E402
from hornlab_search.search.evaluate import (  # noqa: E402
    evaluate, make_context, metrics_from_response, metrics_to_json, read_ndjson, split_freq_bands)
from hornlab_search.search.gpulock import GpuBusyError, gpu_lock  # noqa: E402
from hornlab_search.solve import cache as solve_cache  # noqa: E402
from hornlab_search.solve import worker  # noqa: E402
from hornlab_search.solve.base import (  # noqa: E402
    balloon_dirs_from_angles, balloon_grid_shape, get_backend, spl_from_pressure)
from hornlab_search.solve.traces import cut_points, field_from_traces, package_traces  # noqa: E402
from hornlab_search.types import Design, Response  # noqa: E402

#: CP-7f A/B bars (docs/plan/09_CHECKPOINTS.md; the M2 evidence uses the same three).
BAR_ON_AXIS_DB = 0.039
BAR_BW_DEG = 1.0
BAR_DI_DB = 0.1

#: f11 of the 1-inch exit, printed with every 12 kHz number (rigid uniform-velocity cap above it
#: compares GEOMETRIES, not drivers).
F11_HZ_1IN = 7914.281563679812

VRAM_POLL_INTERVAL_S = 0.2


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _abs(path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (REPO_ROOT / p)


# ------------------------------------------------------------------ VRAM polling (M2 pattern)


class VramPoller:
    """``nvidia-smi`` from a daemon thread: first sample = baseline, max = peak.

    Mirrors ``tools/measure_fused_ceiling.py::VramPoller`` (M2): the probe is
    ``solve.worker.vram_used_mib`` (a subprocess per sample), never an in-process GPU query.
    """

    def __init__(self, interval_s: float = VRAM_POLL_INTERVAL_S) -> None:
        self.interval_s = float(interval_s)
        self.baseline_mib = None
        self.peak_mib = None
        self._stop = threading.Event()
        self._thread = None
        self._started = False

    def _sample(self):
        value = worker.vram_used_mib()
        if value is None:
            return
        value = float(value)
        if self.peak_mib is None or value > self.peak_mib:
            self.peak_mib = value

    def _run(self):
        while not self._stop.wait(self.interval_s):
            self._sample()

    def start(self) -> None:
        if self._started:
            return
        base = worker.vram_used_mib()
        self.baseline_mib = None if base is None else float(base)
        self.peak_mib = self.baseline_mib
        self._thread = threading.Thread(target=self._run, name="vram-poll", daemon=True)
        self._thread.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        self._sample()
        self._started = False

    def as_dict(self) -> dict:
        peak = self.peak_mib
        base = self.baseline_mib
        return {
            "baseline_MiB": None if base is None else int(round(base)),
            "peak_MiB": None if peak is None else int(round(peak)),
            "peak_minus_baseline_MiB": None if (base is None or peak is None)
            else int(round(max(0.0, peak - base))),
        }


# ------------------------------------------------------------------ stored run / design


def load_stored_design(run_dir: Path, design_hash: str) -> tuple[Design, dict]:
    """Reconstruct the design exactly as the run pipeline does (designs/<hash>/design.json)."""
    dj_path = run_dir / "designs" / design_hash / "design.json"
    if not dj_path.is_file():
        raise SystemExit(f"no {dj_path}")
    dj = json.loads(dj_path.read_text(encoding="utf-8"))
    design = Design(str(dj["family"]), dict(dj["params"]))
    if design.hash() != design_hash:
        raise SystemExit(
            f"{dj_path}: reconstructed hash {design.hash()} != requested {design_hash} "
            "(the stored params do not round-trip; refusing to measure a different design)")
    return design, dj


def _parse_value(text: str):
    try:
        return json.loads(text)
    except ValueError:
        pass
    try:                          # PowerShell often strips the JSON's inner double quotes
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return text


def _set_dotted(raw: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    node = raw
    for key in parts[:-1]:
        node = node.setdefault(key, {})
        if not isinstance(node, dict):
            raise SystemExit(f"--set {dotted}: {key!r} is not a mapping in the stored config")
    node[parts[-1]] = value


def variant_config(run_dir: Path, job_dir: Path, overrides: list[str],
                   cuda_fused: bool | None):
    """The stored run's config.yaml + the overrides, re-loaded through the NORMAL validator.

    Re-loading (instead of poking the dataclass) is what makes ``mesh.band_split``,
    ``mesh.rear_res_factor``, ``solve.source_motion`` and the balloon overrides pass the same
    checks a config file would, and it records the exact variant in the job dir.
    """
    raw = yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit(f"{run_dir}/config.yaml is not a mapping")
    if cuda_fused is not None:
        _set_dotted(raw, "solve.cuda_fused", bool(cuda_fused))
    for item in overrides:
        if "=" not in item:
            raise SystemExit(f"--set needs key=value, got {item!r}")
        key, _, val = item.partition("=")
        _set_dotted(raw, key.strip(), _parse_value(val.strip()))
    job_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = job_dir / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(cfg_path)


def _spec_block(cfg, mode: str) -> dict:
    sspec = solve_spec(mode, cfg)
    mspec = mesh_spec(mode, cfg)
    return {
        "mode": mode,
        "backend": cfg.solve.backend,
        "cuda_fused": bool(getattr(cfg.solve, "cuda_fused", False)),
        "source_motion": str(getattr(cfg.solve, "source_motion", "normal")),
        "rear_res_factor": float(cfg.mesh.rear_res_factor),
        "band_split": cfg.mesh.band_split,
        "distance_m": float(cfg.solve.distance_m),
        "angle_count": int(cfg.solve.angle_count),
        "balloon_points_requested": int(sspec.observation.balloon_points),
        "balloon_grid": list(balloon_grid_shape(int(sspec.observation.balloon_points)))
        if sspec.observation.balloon and sspec.observation.balloon_points else None,
        "freqs_hz": [float(f) for f in sspec.freqs_hz],
        "mesh_epw": float(mspec.epw),
        "dof_cap": int(cfg.mesh.dof_cap(mode)),
        "target_band_hz": [float(cfg.target_raw["band_lo_hz"]), float(cfg.target_raw["band_hi_hz"])],
        "weights": dict(cfg.weights),
    }


# ------------------------------------------------------------------ payload helpers


def _floats(a) -> list:
    return [None if v is None else float(v) for v in np.asarray(a, dtype=float).ravel()]


def _meta_summary(meta: dict | None) -> dict:
    """The Response.meta keys that are evidence here (native_diagnostics is reduced to paths)."""
    meta = dict(meta or {})
    paths = []
    for d in (meta.get("native_diagnostics") or []):
        if isinstance(d, dict) and d.get("assembly_path"):
            paths.append(str(d["assembly_path"]))
    keep = ("balloon_grid", "balloon_layout", "distance_m", "angle_count", "source_motion",
            "mesh_policy", "cuda_fused", "n_vertices", "n_triangles", "quadrants",
            "symmetry_plane", "timings", "requested_frequency_count", "is_partial", "cancelled",
            "seam_check", "vram_baseline_mib", "vram_peak_mib", "solve_seconds")
    out = {k: meta.get(k) for k in keep if k in meta}
    out["assembly_paths"] = sorted(set(paths))
    out["assembly_path_counts"] = {p: paths.count(p) for p in sorted(set(paths))}
    return out


def _payload_common(ev, design, cfg, mode: str, job: str, args, wall_s: float) -> dict:
    resp: Response | None = ev.outcome.response if ev.outcome is not None else None
    m = ev.metrics
    mesh = ev.mesh
    out = {
        "job": job,
        "created_utc": _utc(),
        "command": args.command_string,
        "source_run": str(Path(args.run_dir).resolve()),
        "design_hash": design.hash(),
        "family": design.family,
        "spec": _spec_block(cfg, mode),
        "ok": not bool(ev.error),
        "error": ev.error,
        "J": float(ev.objective),
        "terms": dict(ev.terms or {}),
        "dofs": None if mesh is None else mesh.n_dof,
        "triangles": None if mesh is None else mesh.n_triangles,
        "res_mm": None if mesh is None else dict(mesh.res_mm),
        "mesh_path": None if mesh is None else str(mesh.path),
        "seconds": {
            "mesh": None if mesh is None else float(mesh.seconds),
            "solve": None if ev.outcome is None else float(ev.outcome.seconds),
            "wall": float(wall_s),
        },
    }
    if m is not None:
        ax = resp.axis_index if resp is not None else None
        out["freqs_hz"] = _floats(m.freqs_hz)
        out["per_frequency"] = {
            "bw_h_deg": _floats(m.bw_h_deg),
            "bw_v_deg": _floats(m.bw_v_deg),
            "di_db": _floats(m.di_db),
            "di_source": m.di_source,
            "on_axis_db": _floats(m.on_axis_db),
            "ripple_h_db": _floats(m.ripple_h_db),
            "ripple_v_db": _floats(m.ripple_v_db),
            "spl_on_axis_db": _floats(np.asarray(resp.spl_h_db, dtype=float)[:, ax])
            if resp is not None and ax is not None else None,
        }
        out["scalars"] = dict(m.scalars)
    out["meta"] = _meta_summary(None if resp is None else resp.meta)
    return out


def _bands_payload(cfg, mode: str, design_hash: str, run_dir: Path, cache_dir: Path) -> list:
    """WP8: per-band dofs/triangles/res_mm, read back from the band dirs + the solve cache."""
    if cfg.mesh.band_split is None:
        return []
    sspec = solve_spec(mode, cfg)
    mspec = mesh_spec(mode, cfg)
    edges = [float(e) for e in cfg.mesh.band_split["edges_hz"]]
    bands = split_freq_bands(sspec.freqs_hz, edges)
    tops = edges + [float(sspec.freqs_hz[-1])]
    out = []
    for i, band in enumerate(bands):
        bmspec = dataclasses.replace(mspec, f_max_hz=tops[i])
        bsspec = dataclasses.replace(sspec, freqs_hz=tuple(band))
        bdir = run_dir / "designs" / design_hash / f"band{i}"
        meta_path = bdir / "mesh_meta.json"
        mesh_meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
        resp = solve_cache.lookup(solve_cache.key(design_hash, bmspec.hash(), bsspec.hash()),
                                  Path(cache_dir) / "solve")
        out.append({
            "band": i,
            "f_lo_hz": float(band[0]),
            "f_hi_hz": float(band[-1]),
            "n_freqs": len(band),
            "f_max_hz": tops[i],
            "dofs": None if (resp is None or resp.n_dof is None) else int(resp.n_dof),
            "triangles": (mesh_meta.get("result") or {}).get("n_triangles"),
            "res_mm": (mesh_meta.get("result") or {}).get("res_mm"),
            "solve_seconds": None if resp is None else (resp.meta or {}).get("solve_seconds"),
            "timings": None if resp is None else (resp.meta or {}).get("timings"),
        })
    return out


# ------------------------------------------------------------------ printing


def _f(v, fmt: str = ".6g") -> str:
    if v is None:
        return "MISSING"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f != f:
        return "nan"
    return format(int(round(f)), fmt) if fmt.endswith("d") else format(f, fmt)


def print_payload(p: dict) -> None:
    print(f"JOB {p['job']}", flush=True)
    print(f"SOURCE run={p['source_run']} design={p['design_hash']} family={p['family']}", flush=True)
    s = p["spec"]
    print(f"SPEC mode={s['mode']} backend={s['backend']} cuda_fused={s['cuda_fused']} "
          f"source_motion={s['source_motion']} rear_res_factor={s['rear_res_factor']:g} "
          f"band_split={s['band_split']} distance_m={s['distance_m']:g} "
          f"angles={s['angle_count']} balloon_requested={s['balloon_points_requested']} "
          f"balloon_grid={s['balloon_grid']}", flush=True)
    print(f"FREQS n={len(s['freqs_hz'])} {s['freqs_hz'][0]:g}..{s['freqs_hz'][-1]:g} Hz", flush=True)
    print(f"MESH dofs={p['dofs']} triangles={p['triangles']} res_mm={p['res_mm']} "
          f"mesh_seconds={_f(p['seconds']['mesh'], '.2f')} "
          f"solve_seconds={_f(p['seconds']['solve'], '.2f')} "
          f"wall_seconds={_f(p['seconds']['wall'], '.2f')}", flush=True)
    if not p["ok"]:
        print(f"FAILED {p['error'].splitlines()[0] if p['error'] else 'unknown'}", flush=True)
        return
    pf = p["per_frequency"]
    print(f"J {p['J']:.6f}  terms={json.dumps(p['terms'], sort_keys=True)}", flush=True)
    print(f"METRICS (DI source {pf['di_source']}; on_axis is the metric's band-mean-normalised "
          f"value)", flush=True)
    print(f"  {'f_Hz':>9} {'bw_h':>8} {'bw_v':>8} {'DI_dB':>8} {'on_ax':>8} "
          f"{'spl_ax':>8} {'rip_h':>7} {'rip_v':>7}", flush=True)
    for i, f in enumerate(p["freqs_hz"]):
        print(f"  {f:9.2f} {pf['bw_h_deg'][i]:8.3f} {pf['bw_v_deg'][i]:8.3f} "
              f"{pf['di_db'][i]:8.4f} {pf['on_axis_db'][i]:8.3f} "
              f"{_f(pf['spl_on_axis_db'][i] if pf['spl_on_axis_db'] else None, '.3f'):>8} "
              f"{_f(pf['ripple_h_db'][i], '.3f'):>7} {_f(pf['ripple_v_db'][i], '.3f'):>7}",
              flush=True)
    if p.get("bands"):
        print("BANDS", flush=True)
        print(f"  {'band':>4} {'f range':>18} {'n_f':>3} {'f_max':>7} {'dofs':>6} "
              f"{'tris':>6} res_mm", flush=True)
        for b in p["bands"]:
            print(f"  {b['band']:4d} {b['f_lo_hz']:8.0f}..{b['f_hi_hz']:8.0f} {b['n_freqs']:3d} "
                  f"{b['f_max_hz']:7.0f} {_f(b['dofs'], 'd'):>6} {_f(b['triangles'], 'd'):>6} "
                  f"{b['res_mm']}", flush=True)
    m = p["meta"]
    print(f"META balloon_grid={m.get('balloon_grid')} source_motion={m.get('source_motion')} "
          f"mesh_policy={m.get('mesh_policy')} cuda_fused={m.get('cuda_fused')} "
          f"assembly_paths={m.get('assembly_paths')}", flush=True)
    print(f"META timings={m.get('timings')} n_vertices={m.get('n_vertices')} "
          f"n_triangles={m.get('n_triangles')} symmetry={m.get('symmetry_plane')}", flush=True)
    if m.get("seam_check"):
        print("SEAM (first frequency above each edge re-solved on the LOWER band's mesh)", flush=True)
        for edge, d in m["seam_check"].items():
            print(f"  edge {edge:>6} Hz  f={d['freq_hz']:.2f} Hz  "
                  f"on_axis_delta={d['on_axis_delta_db']:+.6f} dB  "
                  f"bw_h_delta={d['bw_h_delta_deg']:+.6f} deg  "
                  f"bw_v_delta={d['bw_v_delta_deg']:+.6f} deg", flush=True)
    sc = p.get("scalars") or {}
    if sc:
        print(f"SCALARS f11_hz={_f(sc.get('f11_hz'), '.1f')} di_mean={_f(sc.get('di_mean_db'), '.4f')} "
              f"bw_h_mean={_f(sc.get('bw_h_mean_deg'), '.3f')} "
              f"bw_v_mean={_f(sc.get('bw_v_mean_deg'), '.3f')} "
              f"ripple_mean={_f(sc.get('ripple_mean_db'), '.4f')} "
              f"flatness={_f(sc.get('flatness_db'), '.4f')}", flush=True)


# ------------------------------------------------------------------ GPU plumbing


def _run_with_gpu(args, job_name: str, body) -> int:
    """GPU lock -> clear hosts -> poll VRAM -> body(payload) -> shutdown (always)."""
    runs_root = _abs(args.runs_dir)
    poller = VramPoller()
    payload: dict = {}
    code = 0
    try:
        with gpu_lock(args.command_string, runs_root=runs_root):
            try:
                killed = worker.clear_stale_hosts(force=True)
                print(f"CLEAN: stale BEAT hosts cleared (roots {killed})" if killed
                      else "CLEAN: no stale BEAT hosts", flush=True)
                poller.start()
                body(payload)
            except Exception as exc:  # noqa: BLE001 - surfaced, then exit nonzero
                print(f"JOB FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                traceback.print_exc()
                payload["ok"] = False
                payload["error"] = f"{type(exc).__name__}: {exc}"
                code = 1
            finally:
                try:
                    forced = worker.shutdown(verify=True)
                    print(f"SHUTDOWN: worker.shutdown(verify=True) ok; "
                          f"force-killed root pids: {forced}", flush=True)
                except Exception as exc:  # noqa: BLE001 - a surviving host is a failed job
                    print(f"SHUTDOWN FAILED: {type(exc).__name__}: {exc}", file=sys.stderr,
                          flush=True)
                    payload["ok"] = False
                    code = 1
                finally:
                    poller.stop()
    except GpuBusyError as exc:
        print(f"GPU BUSY: {exc}", file=sys.stderr, flush=True)
        return 3
    finally:
        poller.stop()
    payload["vram"] = poller.as_dict()
    return code, payload


def _finish(payload: dict, args, printer) -> int:
    out = _abs(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    printer(payload)
    v = payload.get("vram") or {}
    print(f"VRAM baseline={v.get('baseline_MiB')} MiB peak={v.get('peak_MiB')} MiB "
          f"peak-baseline={v.get('peak_minus_baseline_MiB')} MiB", flush=True)
    print(f"RESULT {out}", flush=True)
    return 0


# ------------------------------------------------------------------ command: solve


def _cmd_solve(args) -> int:
    run_dir = _abs(args.run_dir)
    job_dir = _abs(args.out).with_suffix("")
    cache_dir = _abs(args.cache_dir)
    design, _ = load_stored_design(run_dir, args.design_hash)
    cfg = variant_config(run_dir, job_dir, args.set or [], args.cuda_fused)
    run_out = job_dir / "run"
    if (run_out / "search.ndjson").is_file() and (run_out / "search.ndjson").stat().st_size:
        raise SystemExit(
            f"{run_out / 'search.ndjson'} already holds rows: an evaluate() on this run dir would "
            "return the in-run cache hit and silently measure nothing. Use a new --out (or delete "
            "the job dir) for a real re-solve.")
    run_out.mkdir(parents=True, exist_ok=True)
    (run_out / "config.yaml").write_text((job_dir / "config.yaml").read_text(encoding="utf-8"),
                                         encoding="utf-8")

    def body(payload: dict) -> None:
        store = DatasetStore(job_dir / "dataset")
        ctx = make_context(cfg, store, cache_dir=cache_dir, ndjson=run_out / "search.ndjson")
        space = DesignSpace.from_config(cfg)
        backend = get_backend(cfg.solve.backend,
                              cuda_fused=bool(getattr(cfg.solve, "cuda_fused", False)),
                              timeout_s=float(cfg.solve.timeout_s), track_vram=False)
        worker.warm(backend)
        t0 = time.perf_counter()
        ev = evaluate(design, space, cfg, args.mode, run_out, store, backend, ctx=ctx)
        wall = time.perf_counter() - t0
        payload.update(_payload_common(ev, design, cfg, args.mode, args.job_name or
                                       _abs(args.out).stem, args, wall))
        payload["bands"] = _bands_payload(cfg, args.mode, design.hash(), run_out, cache_dir)
        rows = read_ndjson(run_out / "search.ndjson")
        payload["ndjson_row"] = rows[-1] if rows else None
        (run_out / "run.json").write_text(json.dumps({
            "run_id": run_out.name, "mode": args.mode, "config_name": cfg.name,
            "family": cfg.family, "command": args.command_string,
            "provenance": "tools/m3_measurement_pack.py", "source_run": str(run_dir),
            "design_hash": design.hash(), "status": "finished", "finished_utc": _utc(),
            "lib_shas": ctx.lib_shas, "verify_of": {"run": str(run_dir),
                                                    "design_hash": design.hash()},
        }, indent=1, sort_keys=True), encoding="utf-8")
        if not payload["ok"]:
            raise RuntimeError(f"evaluation failed: {ev.error}")

    result = _run_with_gpu(args, args.job_name or _abs(args.out).stem, body)
    if isinstance(result, int):
        return result
    code, payload = result
    payload["job"] = args.job_name or _abs(args.out).stem
    return _finish(payload, args, print_payload) or code


# ------------------------------------------------------------------ command: traces (WP5a)


def _response_at(radius: float, traces: dict, freqs, angles, dirs, grid, z_throat, meta: dict):
    na = angles.size
    pts = np.vstack([cut_points(angles, radius, "horizontal"),
                     cut_points(angles, radius, "vertical"),
                     radius * np.asarray(dirs, dtype=float)])
    p = field_from_traces(traces, pts, freqs)                     # (nf, 2*na + nb)
    ph, pv, pb = p[:, :na], p[:, na:2 * na], p[:, 2 * na:]
    m = dict(meta)
    m.update({"distance_m": float(radius), "balloon_grid": list(grid), "trace_eval": True})
    return Response(
        freqs_hz=np.asarray(freqs, dtype=float).copy(),
        h_angles_deg=np.asarray(angles, dtype=float).copy(),
        v_angles_deg=np.asarray(angles, dtype=float).copy(),
        spl_h_db=spl_from_pressure(ph), spl_v_db=spl_from_pressure(pv),
        balloon_dirs=np.asarray(dirs, dtype=float).copy(),
        spl_balloon_db=spl_from_pressure(pb),
        z_throat=None if z_throat is None else np.asarray(z_throat).copy(),
        p_h=ph.astype(np.complex128), p_v=pv.astype(np.complex128), p_balloon=pb.astype(np.complex128),
        backend="beat_cuda+traces", n_dof=traces.get("n_dof"), meta=m)


def _cmd_traces(args) -> int:
    run_dir = _abs(args.run_dir)
    job_dir = _abs(args.out).with_suffix("")
    cache_dir = _abs(args.cache_dir)
    design, _ = load_stored_design(run_dir, args.design_hash)
    cfg = variant_config(run_dir, job_dir, args.set or [], args.cuda_fused)
    run_out = job_dir / "run"
    (run_out / "config.yaml").parent.mkdir(parents=True, exist_ok=True)
    (run_out / "config.yaml").write_text((job_dir / "config.yaml").read_text(encoding="utf-8"),
                                         encoding="utf-8")
    radii = [float(r) for r in (args.radii or "2,10,50").split(",")]
    payload: dict = {"job": args.job_name or _abs(args.out).stem, "created_utc": _utc(),
                     "command": args.command_string, "source_run": str(run_dir),
                     "design_hash": design.hash(), "family": design.family,
                     "spec": _spec_block(cfg, args.mode), "radii_m": radii}

    # balloon directions: the EXACT theta-phi grid the solver used at the baseline balloon size
    if args.balloon_from:
        z = np.load(_abs(args.balloon_from), allow_pickle=False)
        dirs = np.asarray(z["balloon_dirs"], dtype=float)
        grid = [int(round(np.sqrt(dirs.shape[0] / 2.0))),
                int(round(dirs.shape[0] / max(1, round(np.sqrt(dirs.shape[0] / 2.0)))))]
        grid = json.loads(str(z["meta"])).get("balloon_grid") or grid
        print(f"BALLOON dirs from {args.balloon_from}: n={dirs.shape[0]} grid={grid}", flush=True)
    else:
        grid = list(balloon_grid_shape(int(args.balloon_points)))
        th = np.linspace(0.0, 180.0, grid[0])
        ph = np.arange(grid[1], dtype=float) * (360.0 / grid[1])
        tt, pp = np.meshgrid(th, ph, indexing="ij")
        dirs = balloon_dirs_from_angles(tt.ravel(), pp.ravel())
        print(f"BALLOON synthesised grid={grid} n={dirs.shape[0]}", flush=True)

    def body(pl: dict) -> None:
        mspec, sspec = mesh_spec(args.mode, cfg), solve_spec(args.mode, cfg)
        design_dir = run_out / "designs" / design.hash()
        ctx = make_context(cfg, cache_dir=cache_dir, ndjson=run_out / "search.ndjson")
        backend = get_backend(cfg.solve.backend,
                              cuda_fused=bool(getattr(cfg.solve, "cuda_fused", False)),
                              timeout_s=float(cfg.solve.timeout_s), track_vram=False)
        worker.warm(backend)
        t0 = time.perf_counter()
        mesh = build_mesh(design, mspec, cfg, design_dir, mode=args.mode,
                          cache_dir=ctx.mesh_cache_root)
        outcome, raw_traces = backend.solve_traced(mesh, sspec)
        if not outcome.ok or outcome.response is None or raw_traces is None:
            raise RuntimeError(f"traced solve failed: {outcome.message}")
        mesh.n_dof = int(outcome.response.n_dof)
        traces = package_traces(mesh, sspec, raw_traces)
        traces["n_dof"] = int(mesh.n_dof)
        solve_wall = time.perf_counter() - t0
        np.savez(job_dir / "traces.npz",
                 **{k: (np.asarray(v) if not isinstance(v, str) else np.array(v))
                    for k, v in traces.items() if v is not None})
        resp_direct = outcome.response
        solve_cache.save_response(design_dir / "response.npz", resp_direct)
        metrics_direct = metrics_from_response(resp_direct, ctx.target, mesh=mesh, design=design)
        (design_dir / "metrics.json").write_text(
            json.dumps(metrics_to_json(metrics_direct), indent=1, sort_keys=True), encoding="utf-8")
        (design_dir / "design.json").write_text(json.dumps(
            {"family": design.family, "params": design.params, "design_hash": design.hash()},
            indent=1, sort_keys=True), encoding="utf-8")
        (design_dir / "status.json").write_text(json.dumps(
            {"ok": True, "error": "", "mode": args.mode, "objective": None,
             "seconds": {"solve": float(outcome.seconds),
                         "trace_eval": None}}, indent=1, sort_keys=True), encoding="utf-8")

        pl.update({
            "ok": True, "error": "", "J": None, "terms": {},
            "dofs": int(mesh.n_dof), "triangles": int(mesh.n_triangles),
            "res_mm": dict(mesh.res_mm), "mesh_path": str(mesh.path),
            "seconds": {"mesh": float(mesh.seconds), "solve": float(outcome.seconds),
                        "traced_wall": float(solve_wall)},
            "freqs_hz": [float(f) for f in sspec.freqs_hz],
            "meta": _meta_summary(resp_direct.meta),
        })
        pl["meta"]["traces_nodes"] = int(np.asarray(traces["points"]).shape[0])
        pl["meta"]["traces_faces"] = int(np.asarray(traces["face_centroids"]).shape[0])
        pl["balloon_grid_used"] = grid
        # direct r=2 solve, for the compare subcommand and the trace round-trip check
        pl["direct"] = {
            "distance_m": float(sspec.observation.distance_m),
            "freqs_hz": _floats(metrics_direct.freqs_hz),
            "per_frequency": {
                "bw_h_deg": _floats(metrics_direct.bw_h_deg),
                "bw_v_deg": _floats(metrics_direct.bw_v_deg),
                "di_db": _floats(metrics_direct.di_db),
                "di_source": metrics_direct.di_source,
                "on_axis_db": _floats(metrics_direct.on_axis_db),
                "ripple_h_db": _floats(metrics_direct.ripple_h_db),
                "ripple_v_db": _floats(metrics_direct.ripple_v_db),
                "spl_on_axis_db": _floats(np.asarray(resp_direct.spl_h_db, dtype=float)[:, 0 + (
                    int(sspec.observation.angle_count) - 1) // 2]),
            },
            "scalars": dict(metrics_direct.scalars),
        }
        print(f"TRACED solve dofs={mesh.n_dof} triangles={mesh.n_triangles} "
              f"solve_seconds={outcome.seconds:.2f} "
              f"traces pressure={np.asarray(traces['pressure']).shape} "
              f"neumann={np.asarray(traces['neumann']).shape}", flush=True)
        print("VALIDATION r=2 direct-solve vs trace-evaluated (same spec, different field path)",
              flush=True)
        base = None
        per_r = []
        for r in radii:
            t1 = time.perf_counter()
            resp = _response_at(r, traces, sspec.freqs_hz, np.asarray(resp_direct.h_angles_deg),
                                dirs, grid, resp_direct.z_throat, resp_direct.meta)
            m = metrics_from_response(resp, ctx.target, mesh=mesh, design=design)
            dt = time.perf_counter() - t1
            row = {
                "r_m": r,
                "per_frequency": {
                    "bw_h_deg": _floats(m.bw_h_deg), "bw_v_deg": _floats(m.bw_v_deg),
                    "di_db": _floats(m.di_db), "di_source": m.di_source,
                    "on_axis_db": _floats(m.on_axis_db),
                    "spl_on_axis_db": _floats(np.asarray(resp.spl_h_db, dtype=float)[:, resp.axis_index]),
                },
                "scalars": dict(m.scalars),
                "eval_seconds": float(dt),
            }
            if abs(r - float(sspec.observation.distance_m)) < 1e-9:
                base = row
                row["validation_vs_direct"] = {
                    "max_abs_spl_h_db": float(np.max(np.abs(
                        np.asarray(resp.spl_h_db, float) - np.asarray(resp_direct.spl_h_db, float)))),
                    "max_abs_di_db": float(np.max(np.abs(
                        np.asarray(m.di_db, float) - np.asarray(metrics_direct.di_db, float)))),
                    "max_abs_bw_h_deg": float(np.max(np.abs(
                        np.asarray(m.bw_h_deg, float) - np.asarray(metrics_direct.bw_h_deg, float)))),
                }
                print(f"  max|d spl_h|={row['validation_vs_direct']['max_abs_spl_h_db']:.6g} dB  "
                      f"max|d DI|={row['validation_vs_direct']['max_abs_di_db']:.6g} dB  "
                      f"max|d bw_h|={row['validation_vs_direct']['max_abs_bw_h_deg']:.6g} deg",
                      flush=True)
            per_r.append(row)
        assert base is not None, "the direct-solve distance must be one of --radii"
        print("DISTANCE TABLE (deltas vs r=2 m; the balloon is the stored screen 16x32 grid)",
              flush=True)
        print(f"  {'f_Hz':>9} {'r_m':>5} {'bw_h':>8} {'bw_v':>8} {'DI_dB':>8} "
              f"{'dBW_H':>9} {'dBW_V':>9} {'dDI':>9}", flush=True)
        worst = {"bw_h": 0.0, "bw_v": 0.0, "di": 0.0, "bw_h_at": None, "bw_v_at": None,
                 "di_at": None}
        for i, f in enumerate(sspec.freqs_hz):
            for row in per_r:
                pf, bf = row["per_frequency"], base["per_frequency"]
                dbh = pf["bw_h_deg"][i] - bf["bw_h_deg"][i]
                dbv = pf["bw_v_deg"][i] - bf["bw_v_deg"][i]
                ddi = pf["di_db"][i] - bf["di_db"][i]
                print(f"  {f:9.2f} {row['r_m']:5g} {pf['bw_h_deg'][i]:8.3f} "
                      f"{pf['bw_v_deg'][i]:8.3f} {pf['di_db'][i]:8.4f} "
                      f"{dbh:+9.4f} {dbv:+9.4f} {ddi:+9.4f}", flush=True)
                if abs(dbh) > worst["bw_h"]:
                    worst.update(bw_h=abs(dbh), bw_h_at=(f, row["r_m"]))
                if abs(dbv) > worst["bw_v"]:
                    worst.update(bw_v=abs(dbv), bw_v_at=(f, row["r_m"]))
                if abs(ddi) > worst["di"]:
                    worst.update(di=abs(ddi), di_at=(f, row["r_m"]))
        pl["per_radius"] = per_r
        pl["worst_delta_vs_r2"] = {
            "max_abs_dbw_h_deg": worst["bw_h"], "at_bw_h": worst["bw_h_at"],
            "max_abs_dbw_v_deg": worst["bw_v"], "at_bw_v": worst["bw_v_at"],
            "max_abs_ddi_db": worst["di"], "at_ddi": worst["di_at"],
        }
        print(f"WORST |dBW_H|={worst['bw_h']:.6g} deg at {worst['bw_h_at']}  "
              f"|dBW_V|={worst['bw_v']:.6g} deg at {worst['bw_v_at']}  "
              f"|dDI|={worst['di']:.6g} dB at {worst['di_at']}", flush=True)

    result = _run_with_gpu(args, payload["job"], body)
    if isinstance(result, int):
        return result
    code, pl = result
    payload.update({k: v for k, v in pl.items() if k != "vram"})
    payload["vram"] = pl.get("vram")
    out = _abs(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    v = payload.get("vram") or {}
    print(f"VRAM baseline={v.get('baseline_MiB')} MiB peak={v.get('peak_MiB')} MiB "
          f"peak-baseline={v.get('peak_minus_baseline_MiB')} MiB", flush=True)
    print(f"RESULT {out}", flush=True)
    return code


# ------------------------------------------------------------------ command: compare


def _load_curve(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    if "per_frequency" in d:
        return {"freqs_hz": d.get("freqs_hz") or d["per_frequency"].get("freqs_hz"),
                "per_frequency": d["per_frequency"], "J": d.get("J")}
    # a stored metrics.json
    return {"freqs_hz": d["freqs_hz"],
            "per_frequency": {"bw_h_deg": d["bw_h_deg"], "bw_v_deg": d["bw_v_deg"],
                              "di_db": d["di_db"], "di_source": d.get("di_source"),
                              "on_axis_db": d["on_axis_db"],
                              "ripple_h_db": d.get("ripple_h_db"),
                              "ripple_v_db": d.get("ripple_v_db"),
                              "spl_on_axis_db": None},
            "J": None}


def _cmd_compare(args) -> int:
    new_p = _abs(args.new)
    stored_p = _abs(args.stored)
    new = _load_curve(new_p)
    old = _load_curve(stored_p)
    fn = np.asarray(new["freqs_hz"], dtype=float)
    fo = np.asarray(old["freqs_hz"], dtype=float)
    if fn.shape != fo.shape or not np.allclose(fn, fo, rtol=1e-6, atol=1e-3):
        print(f"compare FAILED: frequency grids differ: {fn.tolist()} vs {fo.tolist()}")
        return 1
    above = args.above_hz
    keys = [("bw_h_deg", "deg", BAR_BW_DEG), ("bw_v_deg", "deg", BAR_BW_DEG),
            ("di_db", "dB", BAR_DI_DB), ("on_axis_db", "dB", BAR_ON_AXIS_DB),
            ("ripple_h_db", "dB", None), ("ripple_v_db", "dB", None)]
    print(f"COMPARE new={new_p}")
    print(f"        stored={stored_p}")
    print(f"  {len(fn)} frequencies {fn[0]:g}..{fn[-1]:g} Hz"
          + (f"; focus above {above:g} Hz" if above else ""))
    print(f"  {'f_Hz':>9} {'dBW_H':>10} {'dBW_V':>10} {'dDI':>10} {'dOnAx':>10} "
          f"{'dRipH':>9} {'dRipV':>9}")
    masks = np.ones(fn.size, dtype=bool) if not above else (fn > float(above))
    maxima = {k: (0.0, None) for k, _, _ in keys}
    for i, f in enumerate(fn):
        if not masks[i]:
            continue
        vals = {}
        for k, _, _ in keys:
            a = new["per_frequency"].get(k)
            b = old["per_frequency"].get(k)
            if a is None or b is None:
                vals[k] = None
                continue
            d = float(a[i]) - float(b[i])
            vals[k] = d
            if abs(d) > maxima[k][0]:
                maxima[k] = (abs(d), float(f))
        def g(k):
            return "MISSING" if vals[k] is None else f"{vals[k]:+10.5f}"
        print(f"  {f:9.2f} {g('bw_h_deg'):>10} {g('bw_v_deg'):>10} {g('di_db'):>10} "
              f"{g('on_axis_db'):>10} {g('ripple_h_db'):>9} {g('ripple_v_db'):>9}")
    print("  MAXIMA" + (f" above {above:g} Hz" if above else ""), flush=True)
    for k, unit, bar in keys:
        mx, at = maxima[k]
        verdict = ""
        if bar is not None:
            verdict = f"  bar {bar:g} {unit}: {'WITHIN' if mx <= bar else 'EXCEEDS'}"
        print(f"    {k:12s} max |diff| {mx:.6g} {unit} at {at}{verdict}")
    if new.get("J") is not None and old.get("J") is not None:
        print(f"  J new={float(new['J']):.6f} stored={float(old['J']):.6f} "
              f"delta={float(new['J']) - float(old['J']):+.6f}")
    print("compare done (report only)")
    return 0


# ------------------------------------------------------------------ CLI


def _parse_args(argv):
    p = argparse.ArgumentParser(
        description="M3 measurement pack on stored designs (WP5a/b/c, WP7, WP8). One GPU job "
                    "per invocation; never starts work on import.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--run-dir", required=True,
                        help="stored run dir holding design.json + config.yaml")
        sp.add_argument("--design-hash", required=True)
        sp.add_argument("--mode", default="verify", choices=("screen", "verify", "final"))
        sp.add_argument("--cache-dir", required=True,
                        help="FRESH cache dir (mesh+solve); the caches are not keyed by lib SHA")
        sp.add_argument("--out", required=True, help="output JSON (runs/m3_<topic>/<job>.json)")
        sp.add_argument("--job-name", default=None)
        sp.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="config override, e.g. solve.balloon_points_verify=2592")
        sp.add_argument("--cuda-fused", dest="cuda_fused", action="store_true", default=None,
                        help="force solve.cuda_fused true (default: keep the stored config's)")
        sp.add_argument("--no-cuda-fused", dest="cuda_fused", action="store_false",
                        help="force solve.cuda_fused false")
        sp.add_argument("--runs-dir", default="runs", help="GPU-lock root (default runs/)")

    sp = sub.add_parser("solve", help="re-solve the stored design at the stored mode spec")
    common(sp)
    sp.set_defaults(func=_cmd_solve)

    sp = sub.add_parser("traces", help="WP5(a): one traced solve + offline r sweep")
    common(sp)
    sp.add_argument("--radii", default="2,10,50", help="comma list, metres (default 2,10,50)")
    sp.add_argument("--balloon-from", default=None,
                    help="response.npz whose balloon_dirs are reused (exact theta-phi grid)")
    sp.add_argument("--balloon-points", type=int, default=512,
                    help="synthesise this balloon size when --balloon-from is absent (512)")
    sp.set_defaults(func=_cmd_traces)

    sp = sub.add_parser("compare", help="per-frequency deltas new vs stored")
    sp.add_argument("--new", required=True, help="job JSON or metrics.json / run dir")
    sp.add_argument("--stored", required=True, help="stored metrics.json or job JSON")
    sp.add_argument("--above-hz", type=float, default=None, help="restrict to f > this")
    sp.set_defaults(func=_cmd_compare)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    if getattr(args, "func", None) is not _cmd_compare:
        args.command_string = " ".join([Path(sys.executable).name,
                                        str(Path(__file__).resolve()), *sys.argv[1:]])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
