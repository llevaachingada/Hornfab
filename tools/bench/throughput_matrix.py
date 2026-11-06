"""Throughput matrix: warm/cold solve timing over fixture meshes x frequency sets x batch sizes.

This is the scorecard harness of the 2026-11-04 throughput packet (WP0). It uses the SAME
production path as ``search/evaluate.py``: ``config.solve_spec`` (cuda_fused flag, balloon grid,
observation, MEH source tags), the production backend from ``solve.base.get_backend`` (native
symmetry comes from the mesh, ``mesh_scale`` 1.0 inside ``BeatBackend.make_config``), and
``backend.solve`` / ``solve_traced``. Only ``freqs_hz`` is replaced per arm (12/25/36/41 sets) and,
for the WP5 A/B, ``freq_batch_size``. No frequency is ever dropped.

Examples (Windows, from the repo root; see docs/throughput/RUNBOOK.md)::

    .venv\\Scripts\\python.exe tools\\bench\\throughput_matrix.py --config examples\\osse_baseline_fusedcuda.yaml ^
        --build-seed --freq-sets 12 --batch-sizes default --warm-reps 3
    .venv\\Scripts\\python.exe tools\\bench\\throughput_matrix.py --config examples\\osse_baseline_fusedcuda.yaml ^
        --mesh runs\\some\\designs\\abc\\mesh.msh --freq-sets 12,25 --batch-sizes 1,2,4,12 --warm-reps 3
    .venv\\Scripts\\python.exe tools\\bench\\throughput_matrix.py --config examples\\osse_baseline.yaml --dry-run
    .venv\\Scripts\\python.exe tools\\bench\\throughput_matrix.py --config examples\\osse_baseline.yaml --fake

Outputs (``runs/bench_throughput_<UTC>/``): ``results.csv`` (one row per solve), ``summary.csv`` and
``summary.json`` (median/min/max per arm, speedup vs the first batch arm, parity), ``env.json``,
``gpu_samples.csv`` (nvidia-smi polled from a separate thread). Safety: takes the project GPU lock,
never kills processes by image name, one solve at a time.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

NVIDIA_QUERY = "memory.used,memory.total,utilization.gpu"
MEH_DEFAULT_GRID = (120.0, 12000.0)      # the 41-point 1/6-octave MEH sweep (docs/meh)


# ------------------------------------------------------------------ pure helpers (offline-tested)


def parse_int_list(text: str) -> list[int]:
    out = []
    for part in str(text).split(","):
        part = part.strip()
        if part:
            out.append(int(part))
    if not out:
        raise ValueError(f"empty list: {text!r}")
    return out


def parse_batch_sizes(text: str) -> list[int | None]:
    """``default`` (or ``0``/``none``) = today's grouping; integers >= 1 = WP5 batch size."""
    out: list[int | None] = []
    for part in str(text).split(","):
        p = part.strip().lower()
        if not p:
            continue
        if p in ("default", "none", "0"):
            out.append(None)
        else:
            n = int(p)
            if n < 1:
                raise ValueError(f"batch size must be >= 1, got {n}")
            out.append(n)
    if not out:
        raise ValueError(f"empty batch list: {text!r}")
    return out


def batch_label(b: int | None) -> str:
    return "default" if b is None else f"b{b}"


def resolve_freq_set(name: str, cfg=None) -> tuple[float, ...]:
    """A frequency set by name. ``12`` / ``25`` / ``36`` are the production screen / verify / final
    grids when ``cfg`` is given and its mode grid has that many points; any other N (``41``) is an
    N-point log grid over 120-12,000 Hz. ``lo:hi:n`` is an explicit log grid."""
    from hornlab_search.config import freq_grid, mode_freqs
    name = str(name).strip()
    if ":" in name:
        lo, hi, n = name.split(":")
        return tuple(freq_grid(float(lo), float(hi), int(n)))
    n = int(name)
    if cfg is not None:
        for mode in ("screen", "verify", "final"):
            f = mode_freqs(mode, cfg)
            if len(f) == n:
                return tuple(f)
    return tuple(freq_grid(MEH_DEFAULT_GRID[0], MEH_DEFAULT_GRID[1], n))


def summarize_values(values) -> dict:
    """n / median / mean / min / max / stdev / rel_spread (max-min over median) of finite floats."""
    v = [float(x) for x in values if x is not None and np.isfinite(float(x))]
    if not v:
        return {"n": 0, "median": None, "mean": None, "min": None, "max": None, "stdev": None,
                "rel_spread": None}
    med = statistics.median(v)
    return {"n": len(v), "median": med, "mean": statistics.fmean(v), "min": min(v), "max": max(v),
            "stdev": statistics.stdev(v) if len(v) > 1 else 0.0,
            "rel_spread": ((max(v) - min(v)) / med) if med else None}


def candidates_per_hour(seconds: float | None) -> float | None:
    return None if not seconds or seconds <= 0 else 3600.0 / float(seconds)


def speedup(baseline: float | None, value: float | None) -> float | None:
    """baseline / value (>1 = faster than the baseline)."""
    if not baseline or not value or value <= 0:
        return None
    return float(baseline) / float(value)


def plan_arms(meshes, freq_sets, batch_sizes) -> list[dict]:
    """Every (mesh, freq set, batch size) arm in a fixed, mesh-major order. Within a mesh/freq set the
    batch arms are rotated by one position per freq set so a systematic drift (thermal, VRAM pool)
    does not always favour or punish the same arm."""
    arms = []
    for mesh in meshes:
        for fi, fs in enumerate(freq_sets):
            k = fi % len(batch_sizes)
            for b in batch_sizes[k:] + batch_sizes[:k]:
                arms.append({"mesh": mesh, "freq_set": fs, "batch": b})
    return arms


def parity(ref: dict | None, cur: dict | None) -> dict:
    """Compare two arms' response fingerprints (arrays kept in memory): frequency grid exact,
    shapes equal, and max abs / relative difference of the SPL arrays."""
    if ref is None or cur is None:
        return {"compared": False}
    out = {"compared": True,
           "freqs_equal": bool(np.array_equal(ref["freqs_hz"], cur["freqs_hz"])),
           "shape_equal": ref["spl_h_db"].shape == cur["spl_h_db"].shape}
    if out["shape_equal"]:
        out["max_abs_spl_h_db"] = float(np.max(np.abs(ref["spl_h_db"] - cur["spl_h_db"])))
        out["max_abs_spl_v_db"] = float(np.max(np.abs(ref["spl_v_db"] - cur["spl_v_db"])))
        if ref.get("spl_balloon_db") is not None and cur.get("spl_balloon_db") is not None \
                and ref["spl_balloon_db"].shape == cur["spl_balloon_db"].shape:
            out["max_abs_spl_balloon_db"] = float(
                np.max(np.abs(ref["spl_balloon_db"] - cur["spl_balloon_db"])))
        if ref.get("z_throat") is not None and cur.get("z_throat") is not None \
                and ref["z_throat"].shape == cur["z_throat"].shape:
            denom = np.maximum(np.abs(ref["z_throat"]), 1e-30)
            out["max_rel_z_throat"] = float(np.max(np.abs(ref["z_throat"] - cur["z_throat"]) / denom))
    return out


def fingerprint(resp) -> dict:
    return {"freqs_hz": np.asarray(resp.freqs_hz, dtype=float).copy(),
            "spl_h_db": np.asarray(resp.spl_h_db, dtype=float).copy(),
            "spl_v_db": np.asarray(resp.spl_v_db, dtype=float).copy(),
            "spl_balloon_db": None if resp.spl_balloon_db is None
            else np.asarray(resp.spl_balloon_db, dtype=float).copy(),
            "z_throat": None if resp.z_throat is None else np.asarray(resp.z_throat).copy()}


def summarize_arm(rows: list[dict]) -> dict:
    """Arm summary from its rep rows (``rep`` 'cold' / 1..N): medians over the WARM reps only."""
    warm = [r for r in rows if r["rep"] != "cold" and r["ok"]]
    cold = [r for r in rows if r["rep"] == "cold"]
    n_f = rows[0]["n_freqs"] if rows else 0
    wall = summarize_values([r["wall_s"] for r in warm])
    return {
        "warm": wall,
        "warm_solve_s": summarize_values([r["solve_s"] for r in warm]),
        "cold_wall_s": cold[0]["wall_s"] if cold else None,
        "warm_start_s": cold[0].get("host_start_s") if cold else None,
        "s_per_freq_median": (wall["median"] / n_f) if wall["median"] and n_f else None,
        "candidates_per_hour_warm": candidates_per_hour(wall["median"]),
        "failures": sum(1 for r in rows if not r["ok"]),
        "peak_vram_mib_max": _max([r.get("vram_peak_mib") for r in rows]),
        "smi_peak_mib_max": _max([r.get("smi_peak_mib") for r in rows]),
    }


def _max(values):
    v = [x for x in values if x is not None]
    return max(v) if v else None


# ------------------------------------------------------------------ nvidia-smi poller


class NvidiaSmiPoller:
    """Polls ``nvidia-smi`` from its OWN thread (CLAUDE.md GPU hygiene rule 5). ``query`` is
    injectable (returns (used_mib, total_mib, util_pct) or None) so it is testable offline."""

    def __init__(self, period_s: float = 0.5, query=None):
        self.period_s = float(period_s)
        self._query = query or self._smi_query
        self.samples: list[tuple[float, int, int | None]] = []     # (t_monotonic, used, util)
        self.total_mib: int | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def _smi_query():
        exe = shutil.which("nvidia-smi")
        if not exe:
            return None
        try:
            r = subprocess.run([exe, f"--query-gpu={NVIDIA_QUERY}", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=10)
            parts = [p.strip() for p in r.stdout.strip().splitlines()[0].split(",")]
            return int(float(parts[0])), int(float(parts[1])), int(float(parts[2]))
        except Exception:  # noqa: BLE001 - a probe failure is "no sample", never an error
            return None

    def _loop(self):
        while not self._stop.is_set():
            s = self._query()
            if s is not None:
                used, total, util = s
                self.total_mib = total
                self.samples.append((time.monotonic(), int(used), util))
            self._stop.wait(self.period_s)

    def start(self):
        self._thread = threading.Thread(target=self._loop, name="nvidia-smi-poller", daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def window(self, t0: float, t1: float) -> dict:
        """Baseline (first sample at/before t0), peak and mean utilisation within [t0, t1]."""
        before = [u for (t, u, _) in self.samples if t <= t0]
        inside = [(u, g) for (t, u, g) in self.samples if t0 <= t <= t1]
        utils = [g for (_, g) in inside if g is not None]
        return {"smi_baseline_mib": before[-1] if before else None,
                "smi_peak_mib": max((u for u, _ in inside), default=None),
                "smi_util_mean_pct": (sum(utils) / len(utils)) if utils else None,
                "smi_samples": len(inside)}

    def write_csv(self, path: Path):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["t_monotonic", "used_mib", "util_pct"])
            w.writerows(self.samples)


# ------------------------------------------------------------------ environment


def _run(cmd, cwd=None, timeout=15) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def env_info(cfg_path=None, extra: dict | None = None) -> dict:
    info = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _run(["git", "rev-parse", "HEAD"], cwd=ROOT),
        "git_dirty": bool(_run(["git", "status", "--porcelain"], cwd=ROOT)),
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "nvidia_smi_gpu": _run(["nvidia-smi", f"--query-gpu=name,driver_version,{NVIDIA_QUERY}",
                                "--format=csv,noheader"]),
        "env": {k: v for k, v in os.environ.items()
                if k.startswith(("HORNLAB_", "JULIA_", "CUDA_"))},
        "config": None if cfg_path is None else str(cfg_path),
    }
    try:
        from hornlab_search.search.evaluate import collect_lib_shas
        info["lib_shas"] = collect_lib_shas()
    except Exception as exc:  # noqa: BLE001
        info["lib_shas"] = f"unavailable: {exc!r}"
    if extra:
        info.update(extra)
    return info


# ------------------------------------------------------------------ fixtures + production path


def mesh_from_msh(path: Path, cfg, quadrants: str | None = None):
    """A ``MeshResult`` for an existing .msh (metres), with the symmetry plane derived from the
    config's quadrants exactly like ``mesh.build`` does (``sizing.SYMMETRY_PLANE``)."""
    from hornlab_search.mesh import sizing
    from hornlab_search.mesh.build import read_msh_summary
    from hornlab_search.types import MeshResult
    q = quadrants or cfg.mesh.quadrants
    s = read_msh_summary(Path(path))
    return MeshResult(path=str(Path(path).resolve()), n_triangles=int(s["n_triangles"]),
                      n_dof=int(s["n_nodes_used"]), quadrants=q,
                      symmetry_plane=sizing.SYMMETRY_PLANE[q], res_mm={}, bbox_m=tuple(s["bbox_m"]),
                      seconds=0.0)


def build_seed_mesh(cfg, out_dir: Path, mode: str):
    """The config's seed design meshed by the production ``build_mesh`` (needs the mesher)."""
    from hornlab_search import config as config_mod
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.mesh.build import build_mesh
    space = DesignSpace.from_config(cfg)
    return build_mesh(space.seed, config_mod.mesh_spec(mode, cfg), cfg, out_dir, mode=mode)


def production_solve_spec(cfg, mode: str, freqs):
    """``config.solve_spec`` exactly as ``evaluate`` builds it (cuda_fused, balloon grid, MEH
    source tags), with only ``freqs_hz`` swapped for this arm's set."""
    from hornlab_search import config as config_mod
    from hornlab_search.search.evaluate import _with_meh_source_tags, meh_block_of
    spec = config_mod.solve_spec(mode, cfg)
    meh = meh_block_of(cfg)
    if meh is not None:
        spec = _with_meh_source_tags(spec, meh)
    return dataclasses.replace(spec, freqs_hz=tuple(float(f) for f in freqs))


def make_backend(cfg, batch: int | None, *, fake: bool = False):
    """The production backend (same kwargs as ``cma._prepare``), plus ``freq_batch_size`` only
    when a batch arm asks for it."""
    if fake:
        return FakeBackend(batch)
    from hornlab_search.solve.base import get_backend
    kw: dict = {"timeout_s": float(cfg.solve.timeout_s)}
    if str(cfg.solve.backend) == "beat_cuda":
        kw["cuda_fused"] = bool(getattr(cfg.solve, "cuda_fused", False))
    if batch is not None:
        kw["freq_batch_size"] = int(batch)
    return get_backend(cfg.solve.backend, **kw)


class FakeBackend:
    """Deterministic stand-in for dry runs / offline tests: sleeps a little per call group and
    returns a response that depends only on the frequencies, so every batch arm is bit-identical."""
    name = "fake"

    def __init__(self, batch=None, per_call_s: float = 0.0, per_freq_s: float = 0.0):
        self.batch = batch
        self.per_call_s, self.per_freq_s = per_call_s, per_freq_s
        self.calls = 0
        self.released = 0
        self.warmed = 0
        self.freq_batch_size = batch

    def available(self):
        return True, "fake"

    def warm(self):
        self.warmed += 1

    def release(self):
        self.released += 1

    def solve(self, mesh, spec):
        from hornlab_search.types import Response, SolveOutcome
        t0 = time.perf_counter()
        f = np.asarray(spec.freqs_hz, dtype=float)
        n_calls = len(f) if self.batch is None else -(-len(f) // int(self.batch))
        time.sleep(self.per_call_s * n_calls + self.per_freq_s * len(f))
        ang = np.linspace(-90, 90, 73)
        spl = 94.0 - 0.001 * f[:, None] * (ang[None, :] / 90.0) ** 2
        resp = Response(freqs_hz=f.copy(), h_angles_deg=ang, v_angles_deg=ang.copy(), spl_h_db=spl,
                        spl_v_db=spl.copy(), balloon_dirs=None, spl_balloon_db=None,
                        z_throat=(0.5 + 0.1j) * np.ones(len(f)), backend="fake", n_dof=1234,
                        meta={"cuda_fused": bool((spec.extra or {}).get("cuda_fused")),
                              "freq_batch_size": self.batch,
                              "timings": {"assembly": 0.1 * len(f), "solve": 0.01 * len(f)},
                              "native_diagnostics": [{"assembly_path": "fake"}] * len(f)})
        self.calls += n_calls
        return SolveOutcome(True, resp, time.perf_counter() - t0, None, "")


def cold_reset(backend) -> float:
    """Release the backend's host (project tree-kill via ``worker.shutdown``, never by image name),
    mark it cold and start it again. Returns the host start seconds."""
    from hornlab_search.solve import worker
    try:
        backend.release()
    except Exception as exc:  # noqa: BLE001 - a failed release is reported, the arm continues
        print(f"WARNING: release before the cold rep failed: {exc!r}", flush=True)
    worker.mark_cold()
    t0 = time.perf_counter()
    worker.warm(backend)
    return time.perf_counter() - t0


def run_arm(arm: dict, cfg, mode: str, *, make_backend_fn, poller: NvidiaSmiPoller | None,
            warm_reps: int, cold: bool, traces: bool, results_sink: list, fingerprints: dict) -> list[dict]:
    """Run one arm: optional cold rep (fresh host, includes JIT) then ``warm_reps`` warm reps."""
    mesh = arm["mesh"]["result"]
    freqs = resolve_freq_set(arm["freq_set"], cfg)
    spec = production_solve_spec(cfg, mode, freqs)
    backend = make_backend_fn(cfg, arm["batch"])
    rows: list[dict] = []
    host_start = None
    from hornlab_search.solve import worker
    if cold:
        host_start = cold_reset(backend)
    else:
        worker.warm(backend)
    reps = (["cold"] if cold else []) + list(range(1, int(warm_reps) + 1))
    for rep in reps:
        t0m = time.monotonic()
        t0 = time.perf_counter()
        try:
            if traces and hasattr(backend, "solve_traced"):
                outcome, _raw = backend.solve_traced(mesh, spec)
            else:
                outcome = backend.solve(mesh, spec)
            err = "" if outcome.ok else (outcome.message or "solve failed")[:400]
        except Exception as exc:  # noqa: BLE001 - one bad rep must not end the matrix
            outcome, err = None, f"{type(exc).__name__}: {exc}"[:400]
        wall = time.perf_counter() - t0
        t1m = time.monotonic()
        ok = bool(outcome is not None and outcome.ok and outcome.response is not None)
        meta = (outcome.response.meta if ok else {}) or {}
        diags = meta.get("native_diagnostics") or []
        paths = sorted({str(d.get("assembly_path")) for d in diags
                        if isinstance(d, dict) and d.get("assembly_path") is not None})
        row = {
            "mesh": arm["mesh"]["label"], "n_dof": None if not ok else outcome.response.n_dof,
            "freq_set": arm["freq_set"], "n_freqs": len(freqs), "batch": batch_label(arm["batch"]),
            "rep": rep, "ok": ok, "error": err, "wall_s": wall,
            "solve_s": None if outcome is None else float(outcome.seconds),
            "host_start_s": host_start if rep == "cold" else None,
            "backend": getattr(backend, "name", ""), "cuda_fused": bool((spec.extra or {}).get("cuda_fused")),
            "assembly_paths": "|".join(paths), "symmetry_plane": mesh.symmetry_plane,
            "balloon_points": spec.observation.balloon_points, "traces": bool(traces),
            "vram_baseline_mib": meta.get("vram_baseline_mib"), "vram_peak_mib": meta.get("vram_peak_mib"),
            "timings_json": json.dumps(meta.get("timings") or {}, sort_keys=True),
        }
        if poller is not None:
            row.update(poller.window(t0m, t1m))
        rows.append(row)
        results_sink.append(row)
        if ok and rep == reps[-1]:
            fingerprints[(arm["mesh"]["label"], arm["freq_set"], arm["batch"])] = fingerprint(
                outcome.response)
        print(f"  {row['mesh']} f={row['freq_set']} {row['batch']} rep={rep}: "
              f"{'OK' if ok else 'FAIL'} {wall:.2f}s", flush=True)
    return rows


def build_summary(all_rows: list[dict], fingerprints: dict, batch_sizes) -> dict:
    arms: dict[tuple, list[dict]] = {}
    for r in all_rows:
        arms.setdefault((r["mesh"], r["freq_set"], r["batch"]), []).append(r)
    ref_batch = batch_label(batch_sizes[0])
    out = []
    for (mesh, fs, b), rows in arms.items():
        s = summarize_arm(rows)
        base_rows = arms.get((mesh, fs, ref_batch))
        base_med = summarize_arm(base_rows)["warm"]["median"] if base_rows else None
        ref_fp = fingerprints.get((mesh, fs, batch_sizes[0]))
        cur_fp = fingerprints.get((mesh, fs, next((x for x in batch_sizes if batch_label(x) == b), None)))
        out.append({"mesh": mesh, "freq_set": fs, "batch": b, "n_freqs": rows[0]["n_freqs"],
                    "n_dof": next((r["n_dof"] for r in rows if r["n_dof"]), None),
                    **{k: v for k, v in s.items() if k not in ("warm", "warm_solve_s")},
                    "warm_median_s": s["warm"]["median"], "warm_min_s": s["warm"]["min"],
                    "warm_max_s": s["warm"]["max"], "warm_rel_spread": s["warm"]["rel_spread"],
                    "warm_n": s["warm"]["n"], "warm_solve_median_s": s["warm_solve_s"]["median"],
                    "speedup_vs_" + ref_batch: speedup(base_med, s["warm"]["median"]),
                    "parity_vs_" + ref_batch: parity(ref_fp, cur_fp) if b != ref_batch else {"compared": False}})
    return {"reference_batch": ref_batch, "arms": out}


def write_outputs(out_dir: Path, all_rows: list[dict], summary: dict, env: dict, poller) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if all_rows:
        keys = list(dict.fromkeys(k for r in all_rows for k in r))
        with open(out_dir / "results.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_rows)
    flat = []
    for a in summary["arms"]:
        flat.append({k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in a.items()})
    if flat:
        keys = list(dict.fromkeys(k for r in flat for k in r))
        with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(flat)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    (out_dir / "env.json").write_text(json.dumps(env, indent=1, default=str), encoding="utf-8")
    if poller is not None and poller.samples:
        poller.write_csv(out_dir / "gpu_samples.csv")


# ------------------------------------------------------------------ CLI


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Throughput matrix (WP0): production-path solve timing.")
    p.add_argument("--config", required=True, help="a hornlab-search YAML (e.g. a *_fusedcuda example)")
    p.add_argument("--mode", default="screen", choices=("screen", "verify", "final"))
    p.add_argument("--mesh", action="append", default=[], metavar="[LABEL=]PATH.msh",
                   help="fixture mesh in metres; repeat for several")
    p.add_argument("--build-seed", action="store_true", help="also mesh the config's seed design")
    p.add_argument("--freq-sets", default="12", help="comma list: 12,25,36,41 or lo:hi:n")
    p.add_argument("--batch-sizes", default="default",
                   help="comma list: default,1,2,4,12 (WP5 knob; 'default' = today's grouping)")
    p.add_argument("--warm-reps", type=int, default=3)
    p.add_argument("--no-cold", action="store_true", help="skip the cold (fresh host) rep per arm")
    p.add_argument("--traces", action="store_true", help="use solve_traced (surface-trace policy)")
    p.add_argument("--out", default=None, help="output dir (default runs/bench_throughput_<UTC>)")
    p.add_argument("--smi-period", type=float, default=0.5)
    p.add_argument("--no-gpu-lock", action="store_true", help="do not take runs/.gpu.lock")
    p.add_argument("--dry-run", action="store_true", help="print the plan only; solve nothing")
    p.add_argument("--fake", action="store_true", help="fake solver (no GPU/mesher): offline check")
    return p


def collect_meshes(args, cfg, out_dir: Path) -> list[dict]:
    meshes = []
    for spec in args.mesh:
        label, _, path = spec.partition("=") if "=" in spec else (Path(spec).parent.name or "mesh", "", spec)
        meshes.append({"label": label, "path": path, "result": None})
    if args.build_seed:
        meshes.append({"label": "seed", "path": None, "result": None})
    return meshes


def materialize(meshes: list[dict], cfg, mode: str, out_dir: Path, fake: bool) -> None:
    from hornlab_search.types import MeshResult
    for m in meshes:
        if fake:
            m["result"] = MeshResult(path=str(m["path"] or "fake.msh"), n_triangles=1000, n_dof=1234,
                                     quadrants=cfg.mesh.quadrants, symmetry_plane="yz+xz",
                                     res_mm={}, bbox_m=(0.0, 0.0, 0.0, 0.3, 0.2, 0.25), seconds=0.0)
        elif m["path"]:
            m["result"] = mesh_from_msh(Path(m["path"]), cfg)
        else:
            m["result"] = build_seed_mesh(cfg, out_dir / "seed_mesh", mode)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    from hornlab_search.config import load_config
    cfg = load_config(args.config)
    freq_sets = [s.strip() for s in args.freq_sets.split(",") if s.strip()]
    batches = parse_batch_sizes(args.batch_sizes)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out) if args.out else ROOT / "runs" / f"bench_throughput_{stamp}"
    meshes = collect_meshes(args, cfg, out_dir)
    if args.fake and not meshes:
        meshes = [{"label": "fake_mesh", "path": None, "result": None}]
    if not meshes:
        print("No fixture: pass --mesh PATH (repeatable) and/or --build-seed.", file=sys.stderr)
        return 2
    arms = plan_arms(meshes, freq_sets, batches)
    n_solves = len(arms) * (args.warm_reps + (0 if args.no_cold else 1))
    print(f"plan: {len(meshes)} mesh x {len(freq_sets)} freq sets x {len(batches)} batch arms = "
          f"{len(arms)} arms, {n_solves} solves, backend {cfg.solve.backend}, "
          f"cuda_fused={bool(getattr(cfg.solve, 'cuda_fused', False))}", flush=True)
    for a in arms:
        n = len(resolve_freq_set(a["freq_set"], cfg))
        print(f"  arm: mesh={a['mesh']['label']} freqs={a['freq_set']}({n}) batch={batch_label(a['batch'])}")
    if args.dry_run:
        return 0
    if args.no_cold:
        print("WARNING: --no-cold: arms share one warm host; do NOT compare VRAM across meshes "
              "(CLAUDE.md GPU hygiene rule 2).", flush=True)
    materialize(meshes, cfg, args.mode, out_dir, args.fake)
    poller = None if args.fake else NvidiaSmiPoller(args.smi_period).start()
    rows: list[dict] = []
    fps: dict = {}
    env = env_info(args.config, {"args": vars(args)})

    def go():
        for a in arms:
            run_arm(a, cfg, args.mode, make_backend_fn=lambda c, b: make_backend(c, b, fake=args.fake),
                    poller=poller, warm_reps=args.warm_reps, cold=not args.no_cold,
                    traces=args.traces, results_sink=rows, fingerprints=fps)

    try:
        if args.fake or args.no_gpu_lock:
            go()
        else:
            from hornlab_search.search.gpulock import gpu_lock
            with gpu_lock("tools/bench/throughput_matrix.py"):
                go()
    finally:
        if poller is not None:
            poller.stop()
        if not args.fake:
            try:                                  # CLAUDE.md rule 6: leave no host behind
                from hornlab_search.solve import worker
                worker.shutdown(verify=True)
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: final worker.shutdown failed: {exc!r}", flush=True)
    summary = build_summary(rows, fps, batches)
    write_outputs(out_dir, rows, summary, env, poller)
    print(f"wrote {out_dir}", flush=True)
    for a in summary["arms"]:
        print(f"  {a['mesh']} f={a['freq_set']} {a['batch']}: warm median {a['warm_median_s']} s, "
              f"cold {a['cold_wall_s']} s, failures {a['failures']}")
    return 0 if not any(a["failures"] for a in summary["arms"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
