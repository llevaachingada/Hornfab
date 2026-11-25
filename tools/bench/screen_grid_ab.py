"""SCREEN-grid A/B: frequency resolution and 12 kHz cost for hornlab-search.

The HF-screen pass (2026-11-23) asks a narrow question: does a SCREEN evaluation that actually
solves through 12 kHz identify better high-frequency designs, and what does it cost?  This tool
answers it with the PRODUCTION pipeline: every arm is a real config, every score is
``search.evaluate.evaluate`` (same objective, same metrics, same cache keys), and every solved
frequency is the config's resolved ``SolveSpec.freqs_hz``.

Subcommands
-----------
``plan``    build the probe briefs (band extended to 12 kHz as a NEW identity), the per-arm
            configs, and ``manifest.json``.  No solver, no GPU.
``measure`` run one cohort (or all) through the arms, appending one CSV row per evaluation.
            GPU; takes the GPU lock with ``HORNLAB_GPU_LOCK`` policy.
``measure-epw``  re-solve one arm at several ``mesh.epw`` values (mesh-convergence check).
``analyze`` CPU-only: cost table, frequency-reference table, J/ranking agreement against the
            dense reference arm, and high-frequency defect detection.

Arms (exact lists are frozen into the manifest at plan time)
-----------------------------------------------------------
F0   frozen screen grid (500-10000 Hz, 12 points)  [status quo, 10 kHz mesh]
F0M  F0's frequencies + 12 kHz  [mesh-isolation control: 12 kHz mesh, F0 sampling]
F1   uniform 500-12000 Hz, ~4 points/octave (19 points)
F2   uniform 500-12000 Hz, ~6 points/octave (29 points)
FA   additive: F0 plus a ~14/octave comb from 8 to 12 kHz (19 points)
FB   hybrid: F1 plus the same 8-12 kHz comb (25 points)
F3   dense reference: F1 u F2 u an 8-12 kHz comb (53 points), independently solved

Why the additive arms: a uniform log grid puts only two or three samples above 10 kHz at 4/6
points per octave, so "29 points" buys mid-band density, not HF resolution.  FA/FB test whether
spending the SAME budget on the HF band is what actually improves selection.

Nothing here changes the mesh generator.  Meshes come from the production ``mesh.build`` at the
arm's own ``f_max_hz``; ``plan`` reports triangle counts, ``measure`` records dofs and VRAM.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hornlab_search.config import (  # noqa: E402
    freq_grid,
    load_brief,
    load_config,
    mesh_spec,
    mode_freqs,
    solve_spec,
)

ARMS = ("F0", "F0M", "F1", "F2", "FA", "FB", "F3")
HF_COMB_8K_12K = 9          # 8 points/octave over 8-12 kHz
MEASURE_FIELDS = (
    "cohort", "design_hash", "design_label", "arm", "n_freqs", "f_max_hz", "n_dof",
    "n_triangles", "mesh_s", "solve_s", "metrics_s", "score_s", "total_s",
    "peak_vram_mb_proc", "gpu_used_peak_mib", "gpu_baseline_mib", "cached", "ok", "error",
    "J", "term_total", "term_cov_profile", "term_rip", "term_flat", "term_dislope",
    "term_di_roughness", "term_load", "term_flat_cv", "term_hf_floor", "term_cd_lw",
    "term_cd_di_std", "term_cd_nacc", "term_offaxis_smooth", "n_in_band", "di_source",
    "bw_h_mean_deg", "bw_v_mean_deg", "di_mean_db", "di_slope_db_per_dec", "ripple_mean_db",
    "f_break_h_hz", "f_break_v_hz", "f11_hz", "spdi_mean_db", "spdi_range_db",
    "response", "config", "error_kind", "wall_s",
)


# ------------------------------------------------------------------ arm definitions

def arm_freqs() -> dict[str, tuple[float, ...] | None]:
    """The frozen frequency lists of the experiment (None = the config's frozen grid)."""
    f0 = tuple(float(f) for f in freq_grid(500.0, 10_000.0, 12))
    f1 = tuple(float(f) for f in freq_grid(500.0, 12_000.0, 19))
    f2 = tuple(float(f) for f in freq_grid(500.0, 12_000.0, 29))
    comb = tuple(float(f) for f in np.round(np.geomspace(8_000.0, 12_000.0,
                                                         HF_COMB_8K_12K), 2))
    fa = tuple(sorted(set(f0) | set(comb)))
    fb = tuple(sorted(set(f1) | set(comb)))
    f3 = tuple(sorted(set(f1) | set(f2) | set(comb)))
    return {
        "F0": None,
        "F0M": tuple(sorted(set(f0) | {12_000.0})),
        "F1": f1,
        "F2": f2,
        "FA": fa,
        "FB": fb,
        "F3": f3,
    }


def arm_blocks() -> dict[str, dict | None]:
    """The ``solve.screen_grid`` block per arm (None = absent)."""
    freqs = arm_freqs()
    blocks: dict[str, dict | None] = {"F0": None}
    for name, fs in freqs.items():
        if name == "F0":
            continue
        blocks[name] = {"freqs_hz": [round(float(f), 2) for f in fs]}
    return blocks


# ------------------------------------------------------------------ plan

def _cohort_spec(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh) if path.suffix == ".json" else _yaml(fh)


def _yaml(fh):
    import yaml
    return yaml.safe_load(fh)


def _write_yaml(path: Path, data: dict) -> None:
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _probe_brief(brief: dict, tag: str, band_hi: float) -> dict:
    """Extend a brief's scored band and CD bands to ``band_hi`` as a NEW identity.

    Only the band edges and the coverage-profile end anchors move; targets, weights, envelope,
    mounting and driver are untouched.  ``grid.screen_extra_hz`` is dropped so the F0 arm is the
    frozen 12-point screen exactly (the additive arms carry their own explicit lists).
    """
    b = json.loads(json.dumps(brief))            # deep copy, JSON-safe brief payloads
    for injected in ("path", "config", "brief"):  # loader provenance, not brief schema
        b.pop(injected, None)
    b["name"] = f"{b.get('name', tag)}__12kprobe_{tag}"
    b["description"] = (str(b.get("description", "")) +
                        f" | 12k HF-screen probe ({tag}): band and CD bands extended to "
                        f"{band_hi:g} Hz; screen grid supplied by the experiment arm.")
    t = b["target"]
    t["band_hi_hz"] = float(band_hi)
    prof = t.get("coverage_profile")
    if isinstance(prof, dict):
        for plane in ("h", "v"):
            rows = prof.get(plane)
            if isinstance(rows, list) and rows:
                last = json.loads(json.dumps(rows[-1]))
                last["hz"] = float(band_hi)
                rows.append(last)
    obj = b.get("objective") or {}
    cd = obj.get("cd") or {}
    for key in ("band_hz",):
        band = cd.get(key)
        if isinstance(band, list) and len(band) == 2:
            cd[key] = [float(band[0]), float(band_hi)]
    off = cd.get("offaxis")
    if isinstance(off, dict) and isinstance(off.get("band_hz"), list) and len(off["band_hz"]) == 2:
        off["band_hz"] = [float(off["band_hz"][0]), float(band_hi)]
    grid = b.get("grid")
    if isinstance(grid, dict):
        grid.pop("screen_extra_hz", None)
    return b


def _designs_from_run(run_dir: Path, n: int) -> list[dict]:
    """Pick ``n`` designs spread over a run's valid J range (deterministic quantiles)."""
    rows = []
    nd = run_dir / "search.ndjson"
    for line in nd.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("ok") and isinstance(r.get("params"), dict) and r.get("design_hash"):
            rows.append(r)
    seen, best = set(), {}
    for r in rows:
        h = r["design_hash"]
        if h not in seen:
            seen.add(h)
            best[h] = r
    ranked = sorted(best.values(), key=lambda r: float(r["objective"]))
    if not ranked:
        raise SystemExit(f"{run_dir}: no valid rows to sample designs from")
    if n >= len(ranked):
        picks = ranked
    else:
        idx = sorted({round(i * (len(ranked) - 1) / (n - 1)) for i in range(n)})
        picks = [ranked[i] for i in idx]
    out = []
    for r in picks:
        out.append({
            "design_hash": r["design_hash"],
            "label": f"n{r.get('n')}",
            "seed_objective": float(r["objective"]),
            "family": r["family"],
            "params": r["params"],
        })
    return out


def cmd_plan(args) -> int:
    spec = _cohort_spec(Path(args.cohorts))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    band_hi = float(spec.get("band_hi_hz", 12_000.0))
    manifest = {"band_hi_hz": band_hi, "arms": {}, "cohorts": []}
    for arm, block in arm_blocks().items():
        manifest["arms"][arm] = {
            "screen_grid": block,
            "freqs_hz": None if block is None else block["freqs_hz"],
        }
    for c in spec["cohorts"]:
        cfg_path = Path(c["config"])
        cfg_base = load_config(cfg_path)                 # resolves extends + brief
        cfgr = json.loads(json.dumps(cfg_base.raw))      # flattened, loader-normalized
        cfgr.pop("brief", None)                          # keep brief_file as the only source
        cfgr.pop("extends", None)
        brief_path = _read_yaml(cfg_path).get("brief_file")
        if not brief_path:
            raise SystemExit(f"{c['id']}: config has no brief_file; the probe brief is required")
        brief = load_brief((cfg_path.parent / brief_path).resolve())
        probe = _probe_brief(brief, c["id"], band_hi)
        probe_path = (out / "briefs" / f"{c['id']}__12kprobe.yaml").resolve()
        _write_yaml(probe_path, probe)
        designs = _designs_from_run(Path(c["run"]), int(c.get("designs", 6)))
        cohort = {
            "id": c["id"], "class": c.get("class", ""), "config": str(cfg_path),
            "run": c["run"], "brief": str(probe_path), "designs": designs,
            "arm_configs": {},
        }
        for arm, block in arm_blocks().items():
            raw = json.loads(json.dumps(cfgr))
            raw["name"] = f"{raw.get('name', c['id'])}__screen12k_{arm}"
            raw["brief_file"] = str(probe_path)
            raw["description"] = (f"HF-screen experiment arm {arm} for cohort {c['id']} "
                                  f"(see tools/bench/screen_grid_ab.py)")
            solve = raw.setdefault("solve", {})
            solve.pop("freq_grid", None)
            solve.pop("screen_grid", None)
            if block is not None:
                solve["screen_grid"] = block
            cfg_out = (out / "configs" / f"{c['id']}__{arm}.yaml").resolve()
            _write_yaml(cfg_out, raw)
            cohort["arm_configs"][arm] = str(cfg_out)
        manifest["cohorts"].append(cohort)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"plan: {len(manifest['cohorts'])} cohorts x {len(manifest['arms'])} arms -> {out}")
    for c in manifest["cohorts"]:
        print(f"  {c['id']:<12} designs={len(c['designs'])} class={c['class']}")
    return 0


def _read_yaml(path: Path) -> dict:
    import yaml
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ------------------------------------------------------------------ GPU sampling

class GpuSampler(threading.Thread):
    """Device-wide dedicated VRAM sampler (``nvidia-smi``), not a process probe.

    WDDM "shared GPU memory" is not exposed per process on Windows; this records dedicated
    ``memory.used`` only and the analysis labels it as such.
    """

    def __init__(self, period_s: float = 1.0):
        super().__init__(daemon=True)
        self.period_s = float(period_s)
        self._halt = threading.Event()
        self.baseline_mib: float | None = None
        self.peak_mib: float | None = None
        self.samples = 0

    def _read(self) -> float | None:
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10)
        except Exception:
            return None
        if out.returncode != 0:
            return None
        try:
            return float(out.stdout.strip().splitlines()[0])
        except (ValueError, IndexError):
            return None

    def run(self):
        self.baseline_mib = self._read()
        self.peak_mib = self.baseline_mib
        while not self._halt.wait(self.period_s):
            v = self._read()
            if v is None:
                continue
            self.samples += 1
            self.peak_mib = v if self.peak_mib is None else max(self.peak_mib, v)

    def stop(self):
        self._halt.set()
        self.join(timeout=10)


# ------------------------------------------------------------------ measurement

def _stage_times(design_dir: Path) -> dict:
    p = design_dir / "stage_timing.ndjson"
    out: dict[str, float] = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        stage = r.get("stage")
        if stage in ("mesh_build", "solve", "metrics", "score", "persist"):
            out[stage] = out.get(stage, 0.0) + float(r.get("seconds", 0.0))
    return out


def _row_from_eval(cohort: dict, design: dict, arm: str, ev, cfg, sampler: GpuSampler,
                   run_dir: Path) -> dict:
    from hornlab_search.search.evaluate import metrics_to_json
    m = ev.metrics
    ms = m if m is not None else None
    terms = ev.terms or {}
    dd = run_dir / "designs" / ev.design_hash
    stage = _stage_times(dd)
    row = {
        "cohort": cohort["id"], "design_hash": ev.design_hash, "design_label": design["label"],
        "arm": arm,
        "n_freqs": len(solve_spec("screen", cfg).freqs_hz),
        "f_max_hz": mesh_spec("screen", cfg).f_max_hz,
        "n_dof": (ev.mesh.n_dof if ev.mesh is not None else None),
        "n_triangles": (ev.mesh.n_triangles if ev.mesh is not None else None),
        "mesh_s": (float(ev.mesh.seconds) if ev.mesh is not None else 0.0),
        "solve_s": (float(ev.outcome.seconds) if ev.outcome is not None else 0.0),
        "metrics_s": stage.get("metrics", 0.0),
        "score_s": stage.get("score", 0.0),
        "total_s": stage.get("mesh_build", 0.0) + stage.get("solve", 0.0)
        + stage.get("metrics", 0.0) + stage.get("score", 0.0),
        "peak_vram_mb_proc": (ev.outcome.peak_vram_mb if ev.outcome is not None else None),
        "gpu_used_peak_mib": sampler.peak_mib,
        "gpu_baseline_mib": sampler.baseline_mib,
        "cached": bool(ev.cached), "ok": not bool(ev.error), "error": ev.error[:300],
        "J": float(ev.objective),
        "response": str(dd / "response.npz") if (dd / "response.npz").exists() else "",
        "config": str(Path(cfg.path) if getattr(cfg, "path", None) else ""),
        "error_kind": (ev.error.split(":")[0] if ev.error else ""),
    }
    for key in ("total", "cov_profile", "rip", "flat", "dislope", "di_roughness", "load",
                "flat_cv", "hf_floor", "cd_lw", "cd_di_std", "cd_nacc", "offaxis_smooth"):
        row[f"term_{key}"] = terms.get(key)
    row["n_in_band"] = terms.get("n_in_band")
    if ms is not None:
        row["di_source"] = m.di_source
        for key in ("bw_h_mean_deg", "bw_v_mean_deg", "di_mean_db", "di_slope_db_per_dec",
                    "ripple_mean_db", "f_break_h_hz", "f_break_v_hz", "f11_hz",
                    "spdi_mean_db", "spdi_range_db"):
            row[key] = getattr(m, key, None)
    else:
        row["di_source"] = ""
    return row


def _append_row(path: Path, row: dict) -> None:
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MEASURE_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def _existing(path: Path) -> set[tuple[str, str, str]]:
    done = set()
    if not path.exists():
        return done
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            done.add((r["cohort"], r["design_hash"], r["arm"]))
    return done


def _backend_for(cfg):
    from hornlab_search.solve.base import get_backend
    kw = {"timeout_s": float(cfg.solve.timeout_s)}
    if str(cfg.solve.backend) == "beat_cuda":
        kw["cuda_fused"] = bool(getattr(cfg.solve, "cuda_fused", False))
    threads = getattr(cfg.solve, "julia_threads", None)
    if threads is not None:
        kw["julia_threads"] = int(threads)
    return get_backend(cfg.solve.backend, **kw)


def _run_measure(args, *, epw_arms: bool = False) -> int:
    from hornlab_search.dataset.store import DatasetStore
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.search.evaluate import evaluate, make_context
    from hornlab_search.search.gpulock import GpuBusyError, gpu_lock
    from hornlab_search.types import Design
    from hornlab_search.solve import worker

    out = Path(args.out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    cohorts = [c for c in manifest["cohorts"]
               if not args.cohorts or c["id"] in args.cohorts]
    arms = [a for a in (args.arms or ARMS)]
    rows_path = out / ("epw_measurements.csv" if epw_arms else "measurements.csv")
    done = set() if args.force else _existing(rows_path)
    store = DatasetStore(out / "dataset")
    command = "tools/bench/screen_grid_ab.py " + " ".join(sys.argv[1:])
    rc = 0
    try:
        with gpu_lock(command, REPO_ROOT / "runs"):
            backend = None
            for cohort in cohorts:
                for arm in arms:
                    if arm not in cohort["arm_configs"]:
                        continue
                    cfg = load_config(cohort["arm_configs"][arm])
                    space = DesignSpace.from_config(cfg)
                    run_dir = (out / "runs" / cohort["id"] / arm).resolve()
                    run_dir.mkdir(parents=True, exist_ok=True)
                    ctx = make_context(cfg, store, cache_dir=out / "cache",
                                       ndjson=run_dir / "search.ndjson")
                    if backend is None:
                        backend = _backend_for(cfg)
                        worker.install_handlers()
                        worker.warm(backend)
                    for design in cohort["designs"]:
                        key = (cohort["id"], design["design_hash"], arm)
                        if key in done:
                            continue
                        sampler = GpuSampler()
                        sampler.start()
                        t0 = time.perf_counter()
                        ev = evaluate(Design(design["family"], design["params"]), space, cfg,
                                      "screen", run_dir, store, backend, ctx=ctx)
                        wall = time.perf_counter() - t0
                        sampler.stop()
                        row = _row_from_eval(cohort, design, arm, ev, cfg, sampler, run_dir)
                        row["wall_s"] = wall
                        _append_row(rows_path, row)
                        done.add(key)
                        print(f"  {cohort['id']:<10} {design['label']:<6} {arm:<4} "
                              f"J={ev.objective:<9.5g} dof={row['n_dof']} "
                              f"freqs={row['n_freqs']} solve={row['solve_s']:.1f}s "
                              f"wall={wall:.1f}s", flush=True)
            if backend is not None:
                worker.shutdown()
    except GpuBusyError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    return rc


def cmd_measure(args) -> int:
    return _run_measure(args)


def _write_epw_configs(manifest: dict, cohort_ids: list[str], epw_dir: Path,
                       epws=(5.0, 6.0, 8.0)) -> list[tuple[dict, str, float, Path]]:
    """Write the mesh-convergence variants of the dense arm (production mesh options only)."""
    epw_dir.mkdir(parents=True, exist_ok=True)
    variants = []
    for c in manifest["cohorts"]:
        if c["id"] not in cohort_ids:
            continue
        for arm in ("F3",):
            base = _read_yaml(Path(c["arm_configs"][arm]))
            for epw in epws:
                raw = json.loads(json.dumps(base))
                raw.setdefault("mesh", {})["epw"] = float(epw)
                raw["name"] = f"{raw['name']}__epw{epw:g}"
                p = (epw_dir / f"{c['id']}__{arm}__epw{epw:g}.yaml").resolve()
                _write_yaml(p, raw)
                variants.append((c, arm, float(epw), p))
    return variants


def cmd_measure_epw(args) -> int:
    """Mesh convergence: same F3 arm at mesh.epw 5/6/8 (12 kHz mesh, existing mesh options)."""
    out = Path(args.out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    variants = _write_epw_configs(manifest, list(args.cohorts_design or []),
                                  out / "configs_epw")
    if not variants:
        raise SystemExit("measure-epw: no cohort matched --cohorts-design")
    # direct loop: the epw arms differ only by mesh.epw, so the CSV `arm` column is the epw value
    from hornlab_search.dataset.store import DatasetStore
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.search.evaluate import evaluate, make_context
    from hornlab_search.search.gpulock import GpuBusyError, gpu_lock
    from hornlab_search.types import Design
    from hornlab_search.solve import worker

    rows_path = out / "epw_measurements.csv"
    done = set() if args.force else _existing(rows_path)
    store = DatasetStore(out / "dataset")
    try:
        with gpu_lock("tools/bench/screen_grid_ab.py measure-epw", REPO_ROOT / "runs"):
            backend = None
            for c, arm, epw, p in variants:
                cfg = load_config(p)
                space = DesignSpace.from_config(cfg)
                run_dir = (out / "runs_epw" / c["id"] / f"epw{epw:g}").resolve()
                run_dir.mkdir(parents=True, exist_ok=True)
                ctx = make_context(cfg, store, cache_dir=out / "cache",
                                   ndjson=run_dir / "search.ndjson")
                if backend is None:
                    backend = _backend_for(cfg)
                    worker.install_handlers()
                    worker.warm(backend)
                for design in c["designs"][: int(args.designs_per_cohort)]:
                    key = (c["id"], design["design_hash"], f"epw{epw:g}")
                    if key in done:
                        continue
                    sampler = GpuSampler()
                    sampler.start()
                    ev = evaluate(Design(design["family"], design["params"]), space, cfg,
                                  "screen", run_dir, store, backend, ctx=ctx)
                    sampler.stop()
                    row = _row_from_eval(c, design, f"epw{epw:g}", ev, cfg, sampler, run_dir)
                    _append_row(rows_path, row)
                    done.add(key)
                    print(f"  {c['id']:<10} {design['label']:<6} epw{epw:g} J={ev.objective:.6g} "
                          f"dof={row['n_dof']} solve={row['solve_s']:.1f}s", flush=True)
            if backend is not None:
                worker.shutdown()
    except GpuBusyError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    return 0


# ------------------------------------------------------------------ analysis

def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _num(row: dict, key: str, default=None):
    v = row.get(key)
    if v in (None, "", "None", "nan"):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3:
        return float("nan")
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    if np.std(ra) == 0 or np.std(rb) == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def _load_response(path: Path):
    if not path or not path.exists():
        return None
    from hornlab_search.types import Response
    z = np.load(path, allow_pickle=True)
    get = lambda k: z[k] if k in z.files else None  # noqa: E731
    return Response(
        freqs_hz=get("freqs_hz"), h_angles_deg=get("h_angles_deg"),
        v_angles_deg=get("v_angles_deg"), spl_h_db=get("spl_h_db"), spl_v_db=get("spl_v_db"),
        balloon_dirs=get("balloon_dirs"), spl_balloon_db=get("spl_balloon_db"),
        z_throat=get("z_throat"), p_h=get("p_h"), p_v=get("p_v"), p_balloon=get("p_balloon"),
        backend=str(get("backend")) if get("backend") is not None else "",
        n_dof=None, meta={})


def _metric_arrays(resp, target) -> dict[str, np.ndarray]:
    """Per-solved-frequency metric arrays via the production metric code."""
    from hornlab_search.search.evaluate import metrics_from_response
    m = metrics_from_response(resp, target)
    out = {"f": np.asarray(m.freqs_hz, dtype=float)}
    for k in ("bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db"):
        v = getattr(m, k, None)
        if isinstance(v, np.ndarray) and v.shape == out["f"].shape:
            out[k] = v.astype(float)
    # on-axis SPL from the response (absolute dB, H and V cuts)
    ax = int(np.argmin(np.abs(resp.h_angles_deg)))
    out["oa_h"] = np.asarray(resp.spl_h_db[:, ax], dtype=float)
    axv = int(np.argmin(np.abs(resp.v_angles_deg)))
    out["oa_v"] = np.asarray(resp.spl_v_db[:, axv], dtype=float)
    # throat impedance (normalised by rho*c): a throat resonance is a |Z| swing between the
    # solved samples, so a coarse grid can miss it for exactly the same reason as a polar notch.
    z = getattr(resp, "z_throat", None)
    if z is not None and np.asarray(z).shape == out["f"].shape:
        z = np.asarray(z)
        out["z_abs"] = np.abs(z).astype(float)
        out["z_real"] = z.real.astype(float)
        out["z_imag"] = z.imag.astype(float)
    return out


def _pchip(x: np.ndarray, y: np.ndarray, xq: np.ndarray) -> np.ndarray:
    from scipy.interpolate import PchipInterpolator
    lx = np.log10(x)
    lq = np.log10(xq)
    return PchipInterpolator(lx, y, extrapolate=False)(lq)


def _band_mask(f: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return (f >= lo) & (f <= hi)


def _hf_flags(arrs: dict, f_band=(8000.0, 12000.0)) -> dict:
    """Grid-independent HF defect flags measured from the DENSE reference response."""
    f = arrs["f"]
    m = _band_mask(f, *f_band)
    out = {"n_hf": int(m.sum())}
    if m.sum() < 3:
        return out
    oa = arrs["oa_h"][m]
    out["hf_ripple_db"] = float(np.max(oa) - np.min(oa))
    # local dip: each point against the mean of its immediate neighbours
    if len(oa) >= 3:
        inner = oa[1:-1] - 0.5 * (oa[:-2] + oa[2:])
        out["hf_notch_db"] = float(-np.min(inner)) if np.min(inner) < 0 else 0.0
    if "bw_h_deg" in arrs:
        bw = arrs["bw_h_deg"]
        hf = bw[m]
        lf = bw[_band_mask(f, 1000.0, 4000.0)]
        if len(hf) and len(lf) and np.median(lf) > 0:
            out["hf_bw_ratio"] = float(np.min(hf) / np.median(lf))
    if "di_db" in arrs:
        di = arrs["di_db"][m]
        out["hf_di_range_db"] = float(np.max(di) - np.min(di))
        out["hf_di_slope_db_dec"] = float(
            np.polyfit(np.log10(f[m] / 1000.0), di, 1)[0]) if m.sum() >= 2 else float("nan")
    if "bw_v_deg" in arrs:
        bwv = arrs["bw_v_deg"]
        hf = bwv[m]
        lf = bwv[_band_mask(f, 1000.0, 4000.0)]
        if len(hf) and len(lf) and np.median(lf) > 0:
            out["hf_bw_ratio_v"] = float(np.min(hf) / np.median(lf))
    if "z_abs" in arrs:
        # reported, NOT folded into the defect boolean: a |Z| swing has no validated threshold
        # for these typologies, so it is evidence, not a verdict.
        z = arrs["z_abs"][m]
        out["hf_z_abs_range"] = float(np.max(z) - np.min(z))
    return out


def cmd_analyze(args) -> int:
    manifest = json.loads((Path(args.out) / "manifest.json").read_text(encoding="utf-8"))
    ev_dir = Path(args.evidence)
    rows = _read_csv(Path(args.out) / "measurements.csv")
    if not rows:
        raise SystemExit("no measurements.csv rows yet")
    arms = [a for a in ARMS if any(r["arm"] == a for r in rows)]
    ref = "F3" if "F3" in arms else arms[-1]

    # ---- frequency reference table (from the resolved configs, never from the YAML intent)
    freq_rows = []
    for c in manifest["cohorts"]:
        for arm in arms:
            p = c["arm_configs"].get(arm)
            if not p:
                continue
            cfg = load_config(p)
            freqs = mode_freqs("screen", cfg)
            f_ = np.array(freqs)
            freq_rows.append({
                "cohort": c["id"], "arm": arm, "n_freqs": len(freqs),
                "lo_hz": freqs[0], "hi_hz": freqs[-1],
                "mesh_f_max_hz": mesh_spec("screen", cfg).f_max_hz,
                "n_5_8k": int(_band_mask(f_, 5000, 8000).sum()),
                "n_8_10k": int(_band_mask(f_, 8000, 10000).sum()),
                "n_10_12k": int(_band_mask(f_, 10000, 12000).sum()),
                "n_12k_plus": int((f_ > 12000).sum()),
                "freqs_hz": " ".join(f"{x:g}" for x in freqs),
            })
    _write_csv(ev_dir / "FREQUENCY_REFERENCE.csv", freq_rows,
               ["cohort", "arm", "n_freqs", "lo_hz", "hi_hz", "mesh_f_max_hz", "n_5_8k",
                "n_8_10k", "n_10_12k", "n_12k_plus", "freqs_hz"])

    # ---- cost table
    cost_rows = []
    for arm in sorted({r["arm"] for r in rows}):
        sel = [r for r in rows if r["arm"] == arm and r["ok"] == "True"]
        if not sel:
            continue
        wall = [(_num(r, "wall_s") or 0.0) for r in sel]
        solve = [(_num(r, "solve_s") or 0.0) for r in sel]
        mesh = [(_num(r, "mesh_s") or 0.0) for r in sel]
        vram = [(_num(r, "gpu_used_peak_mib") or 0.0) for r in sel]
        base = [(_num(r, "gpu_baseline_mib") or 0.0) for r in sel]
        nose = [w for w in wall if w > 0]
        cost_rows.append({
            "arm": arm, "n": len(sel),
            "n_freqs": statistics.median([_num(r, "n_freqs") or 0 for r in sel]),
            "mesh_f_max_hz": statistics.median([_num(r, "f_max_hz") or 0 for r in sel]),
            "median_dof": statistics.median([_num(r, "n_dof") or 0 for r in sel]),
            "median_tri": statistics.median([_num(r, "n_triangles") or 0 for r in sel]),
            "median_mesh_s": round(statistics.median(mesh), 2),
            "median_solve_s": round(statistics.median(solve), 2),
            "p90_wall_s": round(float(np.percentile(nose, 90)), 2) if nose else "",
            "median_wall_s": round(statistics.median(nose), 2) if nose else "",
            "candidates_per_hour": round(3600.0 / statistics.median(nose), 2) if nose else "",
            "median_gpu_peak_mib": round(statistics.median(vram), 0),
            "median_gpu_delta_mib": round(statistics.median(vram) - statistics.median(base), 0),
            "max_gpu_delta_mib": round(max(v - b for v, b in zip(vram, base)), 0),
            "cache_hits": sum(1 for r in sel if r["cached"] == "True"),
            "refusals": sum(1 for r in rows if r["arm"] == arm and r["ok"] != "True"),
        })
    _write_csv(ev_dir / "GPU_BENCHMARK.csv", cost_rows,
               ["arm", "n", "n_freqs", "mesh_f_max_hz", "median_dof", "median_tri",
                "median_mesh_s", "median_solve_s", "median_wall_s", "p90_wall_s",
                "candidates_per_hour", "median_gpu_peak_mib", "median_gpu_delta_mib",
                "max_gpu_delta_mib", "cache_hits", "refusals"])

    # ---- per-arm J vs reference, ranking, and HF flags
    from hornlab_search.targets.spec import Target
    ranking_rows, hf_rows = [], []
    per_cohort: dict[str, dict[str, dict]] = {}
    for r in rows:
        if r["ok"] != "True":
            continue
        per_cohort.setdefault(r["cohort"], {}).setdefault(r["arm"], {})[r["design_hash"]] = r
    # ---- the per-design A/B table (one row per cohort x design x arm)
    ab_rows = []
    for cid, by_arm in per_cohort.items():
        ref_j = {h: _num(r, "J") for h, r in by_arm.get(ref, {}).items()}
        for arm, by_design in by_arm.items():
            for h, r in by_design.items():
                j = _num(r, "J")
                d = (j - ref_j[h]) if h in ref_j and j is not None else None
                ab_rows.append({
                    "cohort": cid, "design_hash": h, "design_label": r.get("design_label"),
                    "arm": arm, "n_freqs": r.get("n_freqs"), "f_max_hz": r.get("f_max_hz"),
                    "n_dof": r.get("n_dof"), "J": j, "dJ_vs_ref": round(d, 6) if d is not None else "",
                    "solve_s": r.get("solve_s"), "wall_s": r.get("wall_s"),
                    "gpu_delta_mib": (round(float(_num(r, "gpu_used_peak_mib") or 0.0)
                                            - float(_num(r, "gpu_baseline_mib") or 0.0), 0)),
                    "cached": r.get("cached"),
                })
    _write_csv(ev_dir / "FREQUENCY_GRID_AB.csv", ab_rows,
               ["cohort", "design_hash", "design_label", "arm", "n_freqs", "f_max_hz", "n_dof",
                "J", "dJ_vs_ref", "solve_s", "wall_s", "gpu_delta_mib", "cached"])

    spearman_by_arm: dict[str, list[float]] = {}
    for cid, by_arm in per_cohort.items():
        if ref not in by_arm:
            continue
        ref_j = {h: _num(r, "J") for h, r in by_arm[ref].items()}
        ref_top3 = {h for h, _ in sorted(ref_j.items(), key=lambda kv: kv[1])[:3]}
        ref_top5 = {h for h, _ in sorted(ref_j.items(), key=lambda kv: kv[1])[:5]}
        for arm, by_design in by_arm.items():
            common = [h for h in by_design if h in ref_j]
            if not common:
                continue
            j_arm = np.array([_num(by_design[h], "J") for h in common])
            j_ref = np.array([ref_j[h] for h in common])
            rho = _spearman(j_arm, j_ref)
            if arm != ref and np.isfinite(rho):
                spearman_by_arm.setdefault(arm, []).append(rho)
            arm_top3 = {h for h, _ in sorted(zip(common, j_arm), key=lambda kv: kv[1])[:3]}
            arm_top5 = {h for h, _ in sorted(zip(common, j_arm), key=lambda kv: kv[1])[:5]}
            err = j_arm - j_ref
            ranking_rows.append({
                "cohort": cid, "arm": arm, "n": len(common),
                "spearman_vs_ref": round(rho, 4) if np.isfinite(rho) else "",
                "mean_dJ": round(float(np.mean(err)), 5),
                "median_abs_dJ": round(float(np.median(np.abs(err))), 5),
                "max_abs_dJ": round(float(np.max(np.abs(err))), 5),
                "top3_overlap": len(arm_top3 & ref_top3),
                "top5_overlap": len(arm_top5 & ref_top5),
                "top3_recall": round(len(arm_top3 & ref_top3) / max(1, len(ref_top3)), 3),
                "false_negatives_top3": len(ref_top3 - arm_top5),
                "missed_hf_flags": "", "caught_hf_flags": "",
            })

    # ---- HF defect detection: dense reference flags vs what the arm's own samples show
    for c in manifest["cohorts"]:
        for design in c["designs"]:
            ref_row = per_cohort.get(c["id"], {}).get(ref, {}).get(design["design_hash"])
            if not ref_row:
                continue
            ref_path = Path(ref_row["response"])
            if not ref_path.exists():
                continue
            try:
                cfg_ref = load_config(c["arm_configs"][ref])
                target = Target.from_dict(cfg_ref.target_raw)
                arrs_ref = _metric_arrays(_load_response(ref_path), target)
            except Exception as exc:  # noqa: BLE001 - diagnostics only
                print(f"  analysis: {c['id']}/{design['design_hash']}: {exc}", file=sys.stderr)
                continue
            flags = _hf_flags(arrs_ref)
            notch, ripple = flags.get("hf_notch_db", 0.0), flags.get("hf_ripple_db", 0.0)
            bw_ratio = flags.get("hf_bw_ratio", 1.0)
            bw_ratio_v = flags.get("hf_bw_ratio_v", 1.0)
            di_range = flags.get("hf_di_range_db", 0.0)
            z_range = flags.get("hf_z_abs_range", 0.0)
            truth_hf = bool(notch >= 6.0 or ripple >= 6.0 or bw_ratio <= 0.6 or di_range >= 4.0)
            for arm in arms:
                row = per_cohort.get(c["id"], {}).get(arm, {}).get(design["design_hash"])
                p = Path(row["response"]) if row and row.get("response") else None
                sees = ""
                agrees = ""
                detail = ""
                if p is not None and p.exists():
                    try:
                        cfg_arm = load_config(c["arm_configs"][arm])
                        arrs = _metric_arrays(_load_response(p), Target.from_dict(cfg_arm.target_raw))
                        fl = _hf_flags(arrs)
                        if fl.get("n_hf", 0) < 3:
                            # fewer than 3 solved samples in 8-12 kHz: the arm cannot see the
                            # defect at all. Distinct from "looked and cleared it".
                            sees = ""
                            agrees = ""
                        else:
                            sees = bool(fl.get("hf_notch_db", 0.0) >= 6.0
                                        or fl.get("hf_ripple_db", 0.0) >= 6.0
                                        or fl.get("hf_bw_ratio", 1.0) <= 0.6
                                        or fl.get("hf_di_range_db", 0.0) >= 4.0)
                            agrees = bool(sees == truth_hf)
                        detail = (f"notch={fl.get('hf_notch_db', float('nan')):.1f};"
                                  f"rip={fl.get('hf_ripple_db', float('nan')):.1f};"
                                  f"bw={fl.get('hf_bw_ratio', float('nan')):.2f};"
                                  f"bwv={fl.get('hf_bw_ratio_v', float('nan')):.2f};"
                                  f"di={fl.get('hf_di_range_db', float('nan')):.1f};"
                                  f"z={fl.get('hf_z_abs_range', float('nan')):.2f}")
                    except Exception:  # noqa: BLE001
                        sees = ""
                        agrees = ""
                hf_rows.append({
                    "cohort": c["id"], "design_hash": design["design_hash"],
                    "design_label": design["label"], "arm": arm,
                    "truth_hf_defect": truth_hf,
                    "truth_notch_db": round(notch, 2), "truth_ripple_db": round(ripple, 2),
                    "truth_bw_ratio": round(float(bw_ratio), 3),
                    "truth_bw_ratio_v": round(float(bw_ratio_v), 3),
                    "truth_di_range_db": round(float(di_range), 2),
                    "truth_z_abs_range": round(float(z_range), 3),
                    "arm_sees_defect": sees, "arm_agrees_with_truth": agrees,
                    "arm_detail": detail,
                })
            print(f"  hf: {c['id']}/{design['design_hash']} notch={notch:.1f} "
                  f"rip={ripple:.1f} bw={bw_ratio:.2f} di={di_range:.1f} hf={truth_hf}",
                  flush=True)

    _write_csv(ev_dir / "SCREEN_RANKING.csv", ranking_rows,
               ["cohort", "arm", "n", "spearman_vs_ref", "mean_dJ", "median_abs_dJ",
                "max_abs_dJ", "top3_overlap", "top5_overlap", "top3_recall",
                "false_negatives_top3", "missed_hf_flags", "caught_hf_flags"])
    _write_csv(ev_dir / "HF_FAILURES.csv", hf_rows,
               ["cohort", "design_hash", "design_label", "arm", "truth_hf_defect",
                "truth_notch_db", "truth_ripple_db", "truth_bw_ratio", "truth_bw_ratio_v",
                "truth_di_range_db", "truth_z_abs_range", "arm_sees_defect",
                "arm_agrees_with_truth", "arm_detail"])

    # ---- summary
    summary = {
        "arms": arms, "ref": ref,
        "mean_spearman_vs_ref": {a: round(float(np.mean(v)), 4)
                                 for a, v in spearman_by_arm.items() if v},
        "cost": {r["arm"]: r for r in cost_rows},
        "ranking_rows": ranking_rows,
    }
    (ev_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"analysis -> {ev_dir} (rows={len(rows)}, cohorts={len(per_cohort)})")
    return 0


def rows_arms(rows: list[dict]) -> list[str]:
    return sorted({r["arm"] for r in rows})


def cmd_baseline(args) -> int:
    """Audit what the DEPLOYED screen actually solves: effective grid, f_max, dof, cost.

    Reads the dataset's compact index to pick recent shards, then the full records for those
    shards (no GPU). Grouped by (config, mode, n_freqs, mesh f_max, backend) so a config that
    overrides the grid cannot hide inside a median.
    """
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=float(args.since_days))
    root = Path(args.dataset)
    shards: set[int] = set()
    with open(root / "index.jsonl", encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
                ts = datetime.fromisoformat(str(r["created_utc"]).replace("Z", "+00:00"))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
            if r.get("mode") in ("screen", "verify", "final", "finalist") and ts >= cutoff:
                shards.add(int(r["shard"]))
    groups: dict[tuple, dict] = {}
    for sh in sorted(shards):
        p = root / f"shard-{sh:04d}.jsonl"
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                ts = datetime.fromisoformat(str(r["created_utc"]).replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if ts < cutoff:
                continue
            solve = r.get("solve") or {}
            freqs = solve.get("freqs_hz") or []
            mesh = r.get("mesh") or {}
            if not freqs:
                continue
            key = (r.get("config_name") or "?", solve.get("mode") or "?",
                   len(freqs), round(float(max(freqs)), 1), solve.get("backend") or "?",
                   int(r.get("objective_version", 1)))
            g = groups.setdefault(key, {"n": 0, "ok": 0, "solve_s": [], "mesh_s": [],
                                        "dof": [], "tri": [], "vram": [], "J": [],
                                        "lo": float(min(freqs))})
            g["n"] += 1
            if r.get("ok"):
                g["ok"] += 1
                for dst, src in (("solve_s", solve.get("seconds")),
                                 ("mesh_s", mesh.get("seconds")),
                                 ("dof", mesh.get("n_dof")),
                                 ("tri", mesh.get("n_triangles")),
                                 ("vram", solve.get("peak_vram_mb")),
                                 ("J", r.get("objective"))):
                    if isinstance(src, (int, float)):
                        g[dst].append(float(src))
    rows = []
    for (cfgname, mode, nf, fmax, backend, ver), g in sorted(groups.items()):
        med = lambda xs: round(statistics.median(xs), 3) if xs else ""  # noqa: E731
        rows.append({
            "config_name": cfgname, "mode": mode, "objective_version": ver,
            "n_freqs": nf, "lo_hz": g["lo"], "f_max_hz": fmax, "backend": backend,
            "n_rows": g["n"], "n_ok": g["ok"], "median_J": med(g["J"]),
            "median_dof": med(g["dof"]), "median_triangles": med(g["tri"]),
            "median_mesh_s": med(g["mesh_s"]), "median_solve_s": med(g["solve_s"]),
            "median_peak_vram_mb": med(g["vram"]),
            "f_max_over_10k": bool(fmax > 10_000.0),
        })
    _write_csv(Path(args.out), rows,
               ["config_name", "mode", "objective_version", "n_freqs", "lo_hz", "f_max_hz",
                "backend", "n_rows", "n_ok", "median_J", "median_dof", "median_triangles",
                "median_mesh_s", "median_solve_s", "median_peak_vram_mb", "f_max_over_10k"])
    over = [r for r in rows if r["f_max_over_10k"]]
    print(f"baseline: {len(rows)} groups from {len(shards)} shards; "
          f"{sum(r['n_rows'] for r in rows)} rows; {len(over)} groups solve above 10 kHz")
    for r in over:
        print(f"  >10k: {r['config_name']:<34} {r['mode']:<8} n={r['n_freqs']:>3} "
              f"fmax={r['f_max_hz']:>7.0f} rows={r['n_rows']}")
    return 0


def cmd_preflight(args) -> int:
    """CPU-only: mesh every sampled design at the F0 (10 kHz) and F3 (12 kHz) specs.

    Answers, without the GPU lane: which designs refuse at 12 kHz (dof cap / mesher), what the
    real triangle/DOF envelope is, and what the calibrated fused-CUDA model predicts against the
    card's budget. Uses the production ``mesh.build`` — no mesher change, no solve.
    """
    import shutil
    import tempfile

    from hornlab_search.design.space import DesignSpace
    from hornlab_search.mesh import build
    from hornlab_search.solve.feasibility import assess
    from hornlab_search.types import Design, BackendUnavailableError  # noqa: F401

    out = Path(args.out)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    rows = [] if args.force else _read_csv(out / "preflight.csv")
    done = {(r["cohort"], r["design_hash"], r["arm"]) for r in rows}
    for c in manifest["cohorts"]:
        if args.cohorts and c["id"] not in args.cohorts:
            continue
        for arm in ("F0", "F3"):
            cfg = load_config(c["arm_configs"][arm])
            space = DesignSpace.from_config(cfg)
            ms = mesh_spec("screen", cfg)
            backend = str(cfg.solve.backend)
            fused = bool(getattr(cfg.solve, "cuda_fused", False))
            cap = int(cfg.mesh.dof_cap("screen"))
            for d in c["designs"]:
                if (c["id"], d["design_hash"], arm) in done:
                    continue
                design = Design(d["family"], d["params"])
                work = Path(tempfile.mkdtemp(prefix="screen12k-preflight-"))
                row = {"cohort": c["id"], "design_hash": d["design_hash"],
                       "design_label": d["label"], "arm": arm,
                       "f_max_hz": ms.f_max_hz, "epw": ms.epw, "cap": cap,
                       "quadrants": ms.quadrants}
                try:
                    mesh = build.build_mesh(design, ms, cfg, work, mode="screen")
                    summ = build.read_msh_summary(Path(mesh.path))
                    dofs = int(summ["n_nodes_used"])
                    fa = assess(dofs, backend, cuda_fused=fused)
                    row.update({
                        "ok": True, "note": "", "n_dof": dofs,
                        "n_triangles": int(mesh.n_triangles),
                        "mesh_s": round(float(mesh.seconds), 2),
                        "dof_over_cap": dofs > cap,
                        "feasibility_verdict": fa["verdict"],
                        "feasibility_need_gib": fa["need_gib"],
                        "feasibility_basis": fa["basis"],
                        "res_throat_mm": round(float(mesh.res_mm.get("throat", 0.0)), 3),
                        "res_mouth_mm": round(float(mesh.res_mm.get("mouth", 0.0)), 3),
                    })
                except Exception as exc:  # noqa: BLE001 - a refusal is a result here
                    row.update({"ok": False, "note": f"{type(exc).__name__}: {str(exc)[:220]}",
                                "n_dof": "", "n_triangles": "", "mesh_s": "",
                                "dof_over_cap": True, "feasibility_verdict": "refused-by-mesher",
                                "feasibility_need_gib": "", "feasibility_basis": "",
                                "res_throat_mm": "", "res_mouth_mm": ""})
                finally:
                    shutil.rmtree(work, ignore_errors=True)
                rows.append(row)
                print(f"  {c['id']:<8} {d['label']:<5} {arm:<3} "
                      f"{'ok dof=' + str(row['n_dof']) if row['ok'] else 'REFUSED'} "
                      f"cap={cap} pred={row['feasibility_verdict']}", flush=True)
    _write_csv(out / "preflight.csv", rows,
               ["cohort", "design_hash", "design_label", "arm", "f_max_hz", "epw", "cap",
                "quadrants", "ok", "n_dof", "n_triangles", "mesh_s", "dof_over_cap",
                "feasibility_verdict", "feasibility_need_gib", "feasibility_basis",
                "res_throat_mm", "res_mouth_mm", "note"])
    ok12 = [r for r in rows if r["arm"] == "F3" and r["ok"]]
    ref = [r for r in rows if r["arm"] == "F3" and not r["ok"]]
    print(f"preflight: {len(rows)} meshes; 12 kHz ok={len(ok12)} refused={len(ref)}")
    if ok12:
        print(f"  12 kHz dof range {min(r['n_dof'] for r in ok12)}..{max(r['n_dof'] for r in ok12)}"
              f" (cap {ok12[0]['cap']}); max model need "
              f"{max((r['feasibility_need_gib'] or 0) for r in ok12):.2f} GiB")
    for r in ref:
        print(f"  refused: {r['cohort']}/{r['design_hash']} {r['note']}")
    return 0


def cmd_identity(args) -> int:
    """Record the source identity the evidence applies to (HEAD, lib SHAs, file hashes, toolchain).

    ``collect_lib_shas()`` reports the INSTALLED package commits and this repo's HEAD; uncommitted
    edits to the search package are not part of that SHA, so the changed files are hashed here.
    """
    import hashlib
    import platform
    import subprocess as sp

    from hornlab_search.search.evaluate import collect_lib_shas

    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _git(*argv) -> str:
        try:
            return sp.run(["git", *argv], cwd=REPO_ROOT, capture_output=True, text=True,
                          timeout=30).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""

    def _smi(field: str) -> str:
        try:
            return sp.run(["nvidia-smi", f"--query-gpu={field}", "--format=csv,noheader"],
                          capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""

    gmsh_version = ""
    try:
        import gmsh
        gmsh_version = str(gmsh.__version__)
    except Exception:  # noqa: BLE001
        pass
    files = ["hornlab_search/config.py", "hornlab_search/search/warmstart.py",
             "tools/bench/screen_grid_ab.py", "tests/test_config_screen_grid.py",
             "tests/test_bench_screen_grid_ab.py"]
    doc = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_head": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_status_porcelain": _git("status", "--porcelain").splitlines(),
        "file_sha256": {f: _sha(REPO_ROOT / f) for f in files if (REPO_ROOT / f).exists()},
        "lib_shas": collect_lib_shas(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "gmsh": gmsh_version,
        "gpu": _smi("name"),
        "gpu_memory_total_mib": _smi("memory.total"),
        "driver": _smi("driver_version"),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"identity -> {out} (head {doc['git_head'][:12]}, beat {doc['lib_shas'].get('hornlab_beat_bem','?')[:12]})")
    return 0


def cmd_report(args) -> int:
    """Apply the PRE-REGISTERED decision rule to the measured CSVs (CPU, reproducible).

    Prints a per-arm verdict table and the cheapest passing arm. It does not choose; it reports
    each criterion against its stated threshold so the decision document can quote it verbatim.
    """
    out = Path(args.out)
    ev = Path(args.evidence)
    rows = [r for r in _read_csv(out / "measurements.csv") if r["ok"] == "True"]
    if not rows:
        raise SystemExit("report: no successful measurements yet")
    arms = [a for a in ARMS if any(r["arm"] == a for r in rows)]
    ref = "F3" if "F3" in arms else arms[-1]
    per: dict[str, dict[str, dict]] = {}
    for r in rows:
        per.setdefault(r["cohort"], {}).setdefault(r["arm"], {})[r["design_hash"]] = r

    # criterion 1: ranking vs the dense reference
    rank: dict[str, dict] = {}
    for cid, by_arm in per.items():
        ref_j = {h: _num(r, "J") for h, r in by_arm.get(ref, {}).items()}
        if not ref_j:
            continue
        ref_top3 = {h for h, _ in sorted(ref_j.items(), key=lambda kv: kv[1])[:3]}
        for arm, ds in by_arm.items():
            common = [h for h in ds if h in ref_j]
            if len(common) < 3:
                continue
            j = np.array([_num(ds[h], "J") for h in common])
            rj = np.array([ref_j[h] for h in common])
            rho = _spearman(j, rj)
            top3 = {h for h, _ in sorted(zip(common, j), key=lambda kv: kv[1])[:3]}
            st = rank.setdefault(arm, {"rho": [], "recall": {}, "fn": 0})
            if np.isfinite(rho):
                st["rho"].append(float(rho))
            st["recall"][cid] = len(top3 & ref_top3) / max(1, len(ref_top3))
            st["fn"] += len(ref_top3 - top3)

    # criterion 2: HF defects the F0 grid misses
    hf = _read_csv(ev / "HF_FAILURES.csv")
    hf_stat: dict[str, dict] = {}
    for r in hf:
        st = hf_stat.setdefault(r["arm"], {"defects": 0, "caught": 0, "missed": 0,
                                           "unassessable": 0, "false_pos": 0})
        truth = r["truth_hf_defect"] == "True"
        sees = r["arm_sees_defect"]
        if truth:
            st["defects"] += 1
            if sees == "True":
                st["caught"] += 1
            elif sees == "":
                st["unassessable"] += 1
            else:
                st["missed"] += 1
        elif sees == "True":
            st["false_pos"] += 1
    f0_missed = {r["design_hash"] for r in hf
                 if r["arm"] == "F0" and r["truth_hf_defect"] == "True"
                 and r["arm_sees_defect"] != "True"}

    # criterion 3: cost
    cost = {}
    for arm in arms:
        sel = [r for r in rows if r["arm"] == arm]
        wall = [_num(r, "wall_s") or 0.0 for r in sel]
        d = [(_num(r, "gpu_used_peak_mib") or 0.0) - (_num(r, "gpu_baseline_mib") or 0.0)
             for r in sel]
        cost[arm] = {"n": len(sel), "wall": statistics.median(wall) if wall else float("nan"),
                     "vram": max(d) if d else float("nan"),
                     "refusals": sum(1 for r in _read_csv(out / "measurements.csv")
                                     if r["arm"] == arm and r["ok"] != "True")}
    base = cost.get("F0", {}).get("wall") or float("nan")

    # criterion 4: epw 6 vs 8 at the dense arm
    epw_stat = {"max_d_oa_db": float("nan"), "max_d_bw_deg": float("nan"), "designs": 0}
    epw_rows = _read_csv(out / "epw_measurements.csv")
    if epw_rows:
        from hornlab_search.targets.spec import Target
        by_design: dict[tuple, dict] = {}
        for r in epw_rows:
            if r["ok"] == "True" and r.get("response") and Path(r["response"]).exists():
                by_design.setdefault((r["cohort"], r["design_hash"]), {})[r["arm"]] = r
        d_oa, d_bw = [], []
        for (cid, dh), v in by_design.items():
            if "epw6" not in v or "epw8" not in v:
                continue
            try:
                # the epw configs are named deterministically at measure-epw time
                cfg_path = out / "configs_epw" / f"{cid}__F3__epw6.yaml"
                cfg = load_config(cfg_path)
                t = Target.from_dict(cfg.target_raw)
                a6 = _metric_arrays(_load_response(Path(v["epw6"]["response"])), t)
                a8 = _metric_arrays(_load_response(Path(v["epw8"]["response"])), t)
            except Exception:  # noqa: BLE001
                continue
            f = a6["f"]
            common = np.intersect1d(f, a8["f"])
            hf_band = common[(common >= 10_000.0) & (common <= 12_000.0)]
            if len(hf_band) < 2:
                continue
            i6 = np.searchsorted(f, hf_band)
            i8 = np.searchsorted(a8["f"], hf_band)
            d_oa.append(float(np.max(np.abs(a6["oa_h"][i6] - a8["oa_h"][i8]))))
            if "bw_h_deg" in a6 and "bw_h_deg" in a8:
                d_bw.append(float(np.max(np.abs(a6["bw_h_deg"][i6] - a8["bw_h_deg"][i8]))))
            epw_stat["designs"] += 1
        if d_oa:
            epw_stat["max_d_oa_db"] = round(max(d_oa), 3)
        if d_bw:
            epw_stat["max_d_bw_deg"] = round(max(d_bw), 3)

    # verdicts
    verdicts = {}
    f0_rank = rank.get("F0", {})
    f0_rho = float(np.mean(f0_rank.get("rho", [np.nan])))
    for arm in arms:
        st = rank.get(arm, {})
        rho = float(np.mean(st["rho"])) if st.get("rho") else float("nan")
        c1_gain = rho - f0_rho if np.isfinite(rho) and np.isfinite(f0_rho) else float("nan")
        c1_recall_ok = all(st.get("recall", {}).get(cid, 0.0) >=
                           f0_rank.get("recall", {}).get(cid, 0.0) for cid in per)
        hs = hf_stat.get(arm, {})
        caught_of_missed = (sum(1 for r in hf if r["arm"] == arm and r["truth_hf_defect"] == "True"
                                and r["design_hash"] in f0_missed
                                and r["arm_sees_defect"] == "True") / len(f0_missed)
                            if f0_missed else float("nan"))
        cw = cost.get(arm, {})
        wall_ratio = (cw.get("wall", float("nan")) / base) if base else float("nan")
        verdicts[arm] = {
            "c1_pooled_spearman": round(rho, 4) if np.isfinite(rho) else "",
            "c1_gain_vs_F0": round(c1_gain, 4) if np.isfinite(c1_gain) else "",
            "c1_recall_not_worse": bool(c1_recall_ok),
            "c1_pass": bool(np.isfinite(c1_gain) and c1_gain >= 0.10 and c1_recall_ok),
            "c2_caught_of_F0_missed": (round(caught_of_missed, 3)
                                       if np.isfinite(caught_of_missed) else ""),
            "c2_false_positives": hs.get("false_pos", 0),
            "c2_pass": bool(np.isfinite(caught_of_missed) and caught_of_missed >= 0.5
                            and hs.get("false_pos", 0) == 0),
            "c3_wall_ratio_vs_F0": round(wall_ratio, 3) if np.isfinite(wall_ratio) else "",
            "c3_max_vram_delta_mib": round(cw.get("vram", float("nan")), 0)
            if np.isfinite(cw.get("vram", float("nan"))) else "",
            "c3_refusals": cw.get("refusals", 0),
            "c3_pass": bool(np.isfinite(wall_ratio) and wall_ratio <= 2.0
                            and (cw.get("vram") or 0) <= 4096 and cw.get("refusals", 0) == 0),
            "c4_epw_max_d_oa_db": epw_stat["max_d_oa_db"],
            "c4_epw_max_d_bw_deg": epw_stat["max_d_bw_deg"],
            "c4_pass": bool(epw_stat["designs"] > 0
                            and (not np.isfinite(epw_stat["max_d_oa_db"])
                                 or epw_stat["max_d_oa_db"] <= 0.5)
                            and (not np.isfinite(epw_stat["max_d_bw_deg"])
                                 or epw_stat["max_d_bw_deg"] <= 2.0)),
        }
        verdicts[arm]["all_pass"] = bool(verdicts[arm]["c1_pass"] and verdicts[arm]["c2_pass"]
                                         and verdicts[arm]["c3_pass"] and verdicts[arm]["c4_pass"])
    eligible = [(cost[a]["wall"], a) for a in arms
                if verdicts[a]["all_pass"] and a != "F0"]
    eligible.sort()
    report = {"ref": ref, "arms": arms, "cost": cost, "rank": rank, "hf": hf_stat,
              "epw": epw_stat, "verdicts": verdicts,
              "cheapest_passing_arm": eligible[0][1] if eligible else None}
    (ev / "DECISION_REPORT.json").write_text(json.dumps(report, indent=1, default=str),
                                             encoding="utf-8")
    _write_csv(ev / "DECISION_TABLE.csv",
               [{"arm": a, **v} for a, v in verdicts.items()],
               ["arm", "c1_pooled_spearman", "c1_gain_vs_F0", "c1_recall_not_worse", "c1_pass",
                "c2_caught_of_F0_missed", "c2_false_positives", "c2_pass",
                "c3_wall_ratio_vs_F0", "c3_max_vram_delta_mib", "c3_refusals", "c3_pass",
                "c4_epw_max_d_oa_db", "c4_epw_max_d_bw_deg", "c4_pass", "all_pass"])
    print(f"{'arm':<4} {'rho':>7} {'gain':>6} {'rec':>3} {'c1':>4} {'hf':>5} {'fp':>2} "
          f"{'wall':>5} {'MiB':>5} {'c3':>4} {'c4':>4} {'ALL':>4}")
    for a in arms:
        v = verdicts[a]
        print(f"{a:<4} {str(v['c1_pooled_spearman']):>7} {str(v['c1_gain_vs_F0']):>6} "
              f"{'ok' if v['c1_recall_not_worse'] else 'NO':>3} {'P' if v['c1_pass'] else '-':>4} "
              f"{str(v['c2_caught_of_F0_missed']):>5} {v['c2_false_positives']:>2} "
              f"{str(v['c3_wall_ratio_vs_F0']):>5} {str(v['c3_max_vram_delta_mib']):>5} "
              f"{'P' if v['c3_pass'] else '-':>4} {'P' if v['c4_pass'] else '-':>4} "
              f"{'YES' if v['all_pass'] else '-':>4}")
    print(f"cheapest passing arm: {report['cheapest_passing_arm']}")
    print(f"report -> {ev / 'DECISION_REPORT.json'} and {ev / 'DECISION_TABLE.csv'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="build probe briefs, arm configs and manifest (CPU only)")
    p.add_argument("--cohorts", required=True, help="cohort spec YAML/JSON")
    p.add_argument("--out", required=True, help="experiment output dir")
    p.set_defaults(func=cmd_plan)
    m = sub.add_parser("measure", help="run the arms (GPU, takes the lock)")
    m.add_argument("--out", required=True)
    m.add_argument("--cohorts", nargs="*", default=None)
    m.add_argument("--arms", nargs="*", default=None, choices=list(ARMS))
    m.add_argument("--force", action="store_true", help="re-run rows already in the CSV")
    m.set_defaults(func=cmd_measure)
    e = sub.add_parser("measure-epw", help="mesh convergence at the dense arm (GPU)")
    e.add_argument("--out", required=True)
    e.add_argument("--cohorts", required=True, help="cohort spec YAML/JSON (for ids)")
    e.add_argument("--cohorts-design", nargs="*", required=True, help="cohort ids to re-mesh")
    e.add_argument("--designs-per-cohort", type=int, default=2)
    e.add_argument("--force", action="store_true")
    e.set_defaults(func=cmd_measure_epw)
    a = sub.add_parser("analyze", help="CPU analysis -> evidence CSVs")
    a.add_argument("--out", required=True)
    a.add_argument("--evidence", required=True)
    a.set_defaults(func=cmd_analyze)
    b = sub.add_parser("baseline", help="audit the DEPLOYED screen grids/cost from the dataset")
    b.add_argument("--dataset", default="dataset")
    b.add_argument("--since-days", type=float, default=10.0)
    b.add_argument("--out", required=True)
    b.set_defaults(func=cmd_baseline)
    pf = sub.add_parser("preflight", help="CPU-only mesh/DOF/VRAM preflight of the sampled designs")
    pf.add_argument("--out", required=True)
    pf.add_argument("--cohorts", nargs="*", default=None)
    pf.add_argument("--force", action="store_true")
    pf.set_defaults(func=cmd_preflight)
    sid = sub.add_parser("identity", help="record HEAD/lib SHAs/file hashes the evidence applies to")
    sid.add_argument("--out", required=True)
    sid.set_defaults(func=cmd_identity)
    rep = sub.add_parser("report", help="apply the pre-registered decision rule to the CSVs")
    rep.add_argument("--out", required=True)
    rep.add_argument("--evidence", required=True)
    rep.set_defaults(func=cmd_report)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
