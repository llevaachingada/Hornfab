"""Fixed-design fidelity checks for the acoustic-truth ladder.

Two distinct checks live here and must never be read as one another:

**B1f - frequency fidelity (pair mode).** The same stored designs evaluated at two frequency
tiers (default ``verify`` 29 points / ``finalist`` 36 points) on the *same* mesh resolution. It
answers "does the frequency grid move the score?", not "is the mesh converged?". The stock
``hornlab-search verify`` cannot express this: its parser has no ``--mode`` and ``_verify_body``
hardcodes ``mode="verify"``; ``run``/``search`` evaluate the config seed or CMA candidates, never a
named list of hashes.

**B1 - mesh convergence (refine mode).** The reference is the design's *stored screen row* (no
re-solve). The refined pass re-solves the same design, the same brief/objective/source/mounting,
on the **same screen frequency grid**, with exactly one config change: ``mesh.epw`` multiplied by
``--refine-epw-factor``. ``mesh_spec`` derives throat ``res/2``, mouth ``res``, rear ``res`` from
``epw`` and ``f_max`` (``mesh/sizing.py``), so raising ``epw`` tightens all three at unchanged
``f_max``. The solve-spec hash must equal the stored row's (same grid, same backend, same
observation); only the mesh spec (and therefore the mesh/solve key) changes.

This tool owns ONLY selection/loop/bookkeeping and dispatches every mesh+solve+metrics+J call to
the existing ``hornlab_search.search.evaluate.evaluate`` / ``hornlab_search.mesh.build.build_mesh``
-- no solver, mesher, metric or objective code lives here.

Per (source run, tier) the output is a normal run directory (``<out>/<run_id>__<tier>/``) holding
``search.ndjson``, ``run.json`` and ``designs/<hash>/``. That is required because ``evaluate``
writes one ``response.npz`` per design hash, so two tiers must not share a design directory.

Hygiene (mesh mode, defaults on): a per-design verified BEAT-host teardown
(``worker.shutdown(verify=True)`` -- raises if a host survives), a re-warm before the next design,
and a per-design ``GpuMemPeak`` record (baseline + peak + the host tree's dedicated **and SHARED**
usage; a shared peak above ``SPILL_MIB`` means the solve paged to system RAM and the measurement is
invalid). ``run_vram=False`` disables the sampler for offline tests.

Usage::

    # B1f frequency fidelity (not mesh convergence)
    .venv\\Scripts\\python.exe tools/night_queue/fidelity_pairs.py \\
        --designs-file scratch/fable_architecture/.b1/b1_designs.csv --out runs/b1f_freq_2026-11-17

    # B1 mesh convergence: reference = stored row, refined = same grid at epw x factor
    .venv\\Scripts\\python.exe tools/night_queue/fidelity_pairs.py \\
        --designs-file scratch/fable_architecture/.b1/b1_designs.csv \\
        --refine-epw-factor 2 --out runs/b1_mesh_2026-11-17

    # CPU-only sizing dry run: build the reference and both candidate refined meshes
    .venv\\Scripts\\python.exe tools/night_queue/fidelity_pairs.py \\
        --designs-file scratch/fable_architecture/.b1/b1_designs.csv \\
        --dry-run --build-meshes --refine-factors 2,3 --out <scratch dir>

Exit codes: 0 all checks ok, 1 a solve/metric/build failed or a spill/teardown failure was seen,
2 bad or missing design input, 3 GPU busy.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import dataclasses
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MODES = ("screen", "verify", "final", "finalist")
DEFAULT_MODES = ("verify", "finalist")
PAIR_CHECK = "B1f-frequency-fidelity"
REFINE_CHECK = "B1-mesh-convergence"
REFINE_MODE = "screen"          # the stored reference row's own grid

#: TOOLCHAIN.md M2 measured quarter-domain OOM transition on the 8 GB RTX 4060.
QUARTER_OOM_ONSET_DOF = 8_900
QUARTER_OOM_UPPER_DOF = 15_700
#: report/html.py NOISE_FLOOR_INPUTS: epw 6 vs 18 (the x3 candidate) DI discretization, and the
#: two-solver floor (the largest measured input). Both are dB-level floors, not J floors.
DISCRETIZATION_FLOOR_DB = 0.028
NOISE_FLOOR_DB = 0.039

#: Weighted terms whose deltas are reported (search.ndjson stores the normalized values).
WEIGHTED_TERMS = ("cov", "rip", "di", "dislope", "flat", "load", "distd", "diag", "flat_cv",
                  "penalty")


class MissingDesignError(ValueError):
    """A requested hash has no ok row in its run's search.ndjson."""


class GridMismatchError(ValueError):
    """The stored reference row was not solved on this config's screen grid."""


# ------------------------------------------------------------------ shared helpers


def read_ndjson(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def select_rows(rows: list[dict], wanted: list[str]) -> list[dict]:
    """Lowest-J ok row per requested hash, in the requested order (verify's own dedup rule)."""
    best: dict[str, dict] = {}
    for row in sorted((r for r in rows if r.get("ok") and r.get("objective") is not None),
                      key=lambda r: float(r["objective"])):
        h = row.get("design_hash")
        if h and h not in best:
            best[h] = row
    missing = [h for h in wanted if h not in best]
    if missing:
        raise MissingDesignError(
            f"{len(missing)} design hash(es) have no ok row: {', '.join(missing)}")
    return [best[h] for h in wanted]


def parse_design_specs(specs: list[str] | None, designs_file: str | None) -> list[tuple[str, str]]:
    """``[(run_dir, design_hash), ...]`` from repeatable ``RUN:hash`` and/or a CSV (run,design)."""
    out: list[tuple[str, str]] = []
    for spec in specs or []:
        run, sep, h = spec.rpartition(":")
        if not sep or not run or not h:
            raise MissingDesignError(f"--design expects RUN_DIR:DESIGN_HASH, got {spec!r}")
        out.append((run, h))
    if designs_file:
        with open(designs_file, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            fields = set(reader.fieldnames or [])
            hcol = "design" if "design" in fields else ("hash" if "hash" in fields else None)
            if "run" not in fields or hcol is None:
                raise MissingDesignError(
                    f"{designs_file} needs 'run' and 'design' columns, has {sorted(fields)}")
            for row in reader:
                run = (row.get("run") or "").strip()
                h = (row.get(hcol) or "").strip()
                if run and h:
                    out.append((run, h))
    if not out:
        raise MissingDesignError("no designs: pass --design RUN:hash and/or --designs-file CSV")
    seen, dedup = set(), []
    for run, h in out:
        key = (Path(run).as_posix(), h)
        if key not in seen:
            seen.add(key)
            dedup.append((run, h))
    return dedup


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _design_for(row: dict):
    from hornlab_search.types import Design
    return Design(row["family"], dict(row["params"]))


def _write_mode_meta(d: Path, cfg, run_dir: Path, mode: str, rundir, extra: dict | None = None):
    """A run.json/config snapshot so the output directory is a first-class run (GUI/report)."""
    from hornlab_search.search.evaluate import collect_lib_shas

    rundir.write_config_snapshot(d, cfg)
    meta = {
        "run_id": d.name, "config_name": cfg.name, "family": cfg.family, "mode": mode,
        "config": cfg.raw, "config_sha": rundir.config_sha(cfg.raw),
        "backend": cfg.solve.backend, "lib_shas": collect_lib_shas(),
        "toolchain": rundir.toolchain_snapshot(), "runtime": rundir.runtime_provenance(),
        "command": "tools/night_queue/fidelity_pairs.py",
        "fidelity_pairs_of": {"run": str(run_dir.resolve()), "mode": mode},
        "status": "running", "started_utc": rundir.utc_now(),
    }
    meta.update(extra or {})
    rundir.write_json_atomic(d / "run.json", meta)


# ------------------------------------------------------------------ B1f pair mode


def run_pairs(pairs, out_root, *, config_for_run, evaluate_fn, make_ctx_fn, warm_fn,
              space_for_cfg, store=None, cache_dir=None, modes=DEFAULT_MODES, trace_fraction=0.0,
              dry_run=False, echo=print) -> list[dict]:
    """B1f: evaluate every (run, hash) at every frequency tier. Same mesh in every tier."""
    from hornlab_search.search import rundir

    out_root = Path(out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    states: dict[tuple[str, str], dict] = {}

    def state(run_id: str, mode: str) -> dict:
        key = (run_id, mode)
        if key not in states:
            d = out_root / f"{run_id}__{mode}"
            rows = read_ndjson(d / "search.ndjson")
            done = {r.get("design_hash") for r in rows if r.get("ok")}
            states[key] = {"dir": d, "done": done, "ctx": None}
        return states[key]

    results: list[dict] = []
    by_run: dict[str, list[str]] = {}
    for run, h in pairs:
        by_run.setdefault(str(run), []).append(h)

    for run, wanted in by_run.items():
        run_dir = Path(run)
        run_id = run_dir.name
        if not (run_dir / "search.ndjson").is_file():
            raise MissingDesignError(f"{run_dir} has no search.ndjson")
        cfg = config_for_run(run_dir)
        selected = select_rows(read_ndjson(run_dir / "search.ndjson"), wanted)
        space = space_for_cfg(cfg)
        for row, h in zip(selected, wanted):
            rec = {"run": run_dir.as_posix(), "design_hash": h,
                   "family": row.get("family"), "params": row.get("params"),
                   "stored_screen_J": float(row["objective"])}
            evals = {}
            for mode in modes:
                st = state(run_id, mode)
                if h in st["done"]:
                    echo(f"  {h} {mode}: already ok in {st['dir']}; skipped")
                    evals[mode] = None
                    continue
                if dry_run:
                    echo(f"  {h} {mode}: DRY RUN")
                    evals[mode] = None
                    continue
                if st["ctx"] is None:
                    st["dir"].mkdir(parents=True, exist_ok=True)
                    st["ctx"] = make_ctx_fn(cfg, store, cache_dir=cache_dir,
                                            trace_fraction=trace_fraction,
                                            ndjson=st["dir"] / "search.ndjson")
                    _write_mode_meta(st["dir"], cfg, run_dir, mode, rundir,
                                     {"check": PAIR_CHECK,
                                      "frequency_fidelity_not_mesh": True})
                    warm_fn(cfg.solve.backend)
                ev = evaluate_fn(_design_for(row), space, cfg, mode, st["dir"], store,
                                 cfg.solve.backend, ctx=st["ctx"])
                evals[mode] = ev
                if not ev.error:
                    st["done"].add(h)
                echo(f"  {h} {mode}: "
                     + (f"FAILED: {(ev.error or '').splitlines()[0][:90]}" if ev.error
                        else f"J={ev.objective:.5f}"))
            rec["modes"] = {m: (None if e is None else
                                {"ok": not e.error, "objective": (None if e.error else e.objective),
                                 "error": e.error or None})
                            for m, e in evals.items()}
            results.append(rec)

    if not dry_run:
        for st in states.values():
            if (st["dir"] / "run.json").is_file():
                rundir.update_run_json(st["dir"], status="finished",
                                       finished_utc=rundir.utc_now(),
                                       stop_reason=f"{PAIR_CHECK}: frequency tiers, same mesh")
        _write_json(out_root / "pairs.json", {
            "check": PAIR_CHECK,
            "warning": "FREQUENCY fidelity only: the mesh resolution is unchanged between tiers. "
                       "This is NOT mesh convergence (see --refine-epw-factor for B1).",
            "designs": results,
            "modes": list(modes),
        })
    return results


# ------------------------------------------------------------------ B1 mesh refinement


def refine_config(cfg, factor: float):
    """A copy of ``cfg`` with ONLY ``mesh.epw`` scaled. f_max, caps, grid, backend untouched."""
    if not (factor > 0):
        raise ValueError(f"refine factor must be positive, got {factor!r}")
    mesh = dataclasses.replace(cfg.mesh, epw=float(cfg.mesh.epw) * float(factor))
    return dataclasses.replace(cfg, mesh=mesh)


def refine_config_for_snapshot(cfg, factor: float):
    """The refined cfg with ``raw.mesh.epw`` updated, so the written config snapshot is truthful."""
    refined = refine_config(cfg, factor)
    raw = json.loads(json.dumps(cfg.raw))
    raw.setdefault("mesh", {})["epw"] = float(refined.mesh.epw)
    return dataclasses.replace(refined, raw=raw)


def reference_grid(cfg, row: dict, refined_cfg) -> dict:
    """Assert the refined solve uses the SAME grid/backend/observation as the stored reference."""
    from hornlab_search.config import solve_spec

    base = solve_spec(REFINE_MODE, cfg)
    base_hash = base.hash()
    if row.get("solve_hash") and str(row["solve_hash"]) != base_hash:
        raise GridMismatchError(
            f"{row.get('design_hash')}: stored solve_hash {row['solve_hash']} != this config's "
            f"{REFINE_MODE} solve_hash {base_hash}; the reference row was not solved on this grid")
    refined = solve_spec(REFINE_MODE, refined_cfg)
    if refined.hash() != base_hash or refined.freqs_hz != base.freqs_hz:
        raise GridMismatchError("the epw override changed the solve spec; refusing (same grid is "
                                "the whole point of B1)")
    return {"solve_hash": base_hash, "mode": REFINE_MODE, "same_grid": True,
            "n_freqs": len(base.freqs_hz), "freqs_hz": [float(f) for f in base.freqs_hz]}


def metric_summary(metrics: dict | None, band: tuple[float, float] = (350.0, 8000.0)) -> dict:
    """Mean in-band H/V beamwidth, DI, and ripple from a stored / metrics_to_json dict."""
    if not metrics:
        return {"present": False}
    try:
        import numpy as np
        f = np.asarray(metrics.get("freqs_hz") or [], dtype=float)
        mask = (f >= band[0]) & (f <= band[1])
        out = {"present": True, "n_in_band": int(mask.sum())}
        for key in ("bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db"):
            arr = metrics.get(key)
            if arr is None:
                out[key] = None
                continue
            vals = np.asarray(arr, dtype=float)[mask] if mask.size == len(arr) else \
                np.asarray(arr, dtype=float)
            out[key] = None if vals.size == 0 or np.all(np.isnan(vals)) else float(np.nanmean(vals))
        return out
    except Exception as exc:  # noqa: BLE001 - a malformed stored block is reported, not fatal
        return {"present": False, "error": f"{type(exc).__name__}: {exc}"}


def term_deltas(ref_terms: dict | None, new_terms: dict | None) -> dict:
    ref, new = ref_terms or {}, new_terms or {}
    out = {}
    for key in WEIGHTED_TERMS:
        a, b = ref.get(key), new.get(key)
        try:
            out[key] = None if a is None or b is None else float(b) - float(a)
        except (TypeError, ValueError):
            out[key] = None
    return out


def j_gain_threshold(rows: list[dict]) -> float | None:
    """Smallest non-degenerate adjacent J gap among the set (the claimed finalist gain).

    Gaps below 1e-4 are treated as duplicate scores (the ext_throat v7/v8 pair is one horn to
    3e-6 and would otherwise make any shift 'mesh-sensitive').
    """
    js = sorted(float(r["objective"]) for r in rows if r.get("objective") is not None)
    gaps = [b - a for a, b in zip(js, js[1:]) if (b - a) > 1e-4]
    return min(gaps) if gaps else None


def mesh_verdict(dof: int | None, cap_bound_at: int | None = None) -> str:
    if cap_bound_at is not None:
        s = f"CAP-BOUND at {cap_bound_at} DOF: not a refinement at the existing cap"
        if dof is not None:
            s += f"; true mesh {dof} DOF -> " + _feasibility(dof)
        return s
    if dof is None:
        return "unknown (no realized mesh)"
    return _feasibility(dof)


def _feasibility(dof: int) -> str:
    if dof > QUARTER_OOM_UPPER_DOF:
        return f"mesh check infeasible on this card (est. {dof} DOF)"
    if dof > QUARTER_OOM_ONSET_DOF:
        return f"borderline: {dof} DOF inside the 8.9k-15.7k quarter OOM transition"
    return f"fits: {dof} DOF below the 8.9k quarter OOM onset"


def run_refine(pairs, out_root, *, config_for_run, evaluate_fn, make_ctx_fn, warm_fn,
               space_for_cfg, factor: float, store=None, cache_dir=None, trace_fraction=0.0,
               teardown_fn=None, teardown_per_design=True, vram_factory=None,
               metrics_json_fn=None, gain_threshold: float | None = None,
               dry_run=False, echo=print) -> list[dict]:
    """B1: stored screen row (reference) vs a re-solve at the same grid with epw x factor."""
    from hornlab_search.search import rundir

    out_root = Path(out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    states: dict[tuple[str, str], dict] = {}

    def state(run_id: str, epw: float) -> dict:
        key = (run_id, f"{epw:g}")
        if key not in states:
            d = out_root / f"{run_id}__refine_epw{epw:g}"
            rows = read_ndjson(d / "search.ndjson")
            done = {r.get("design_hash") for r in rows if r.get("ok")}
            states[key] = {"dir": d, "done": done, "ctx": None}
        return states[key]

    results: list[dict] = []
    all_selected: list[dict] = []
    by_run: dict[str, list[str]] = {}
    for run, h in pairs:
        by_run.setdefault(str(run), []).append(h)

    for run, wanted in by_run.items():
        run_dir = Path(run)
        run_id = run_dir.name
        if not (run_dir / "search.ndjson").is_file():
            raise MissingDesignError(f"{run_dir} has no search.ndjson")
        cfg = config_for_run(run_dir)
        selected = select_rows(read_ndjson(run_dir / "search.ndjson"), wanted)
        all_selected.extend(selected)
        refined_cfg = refine_config(cfg, factor)
        snapshot_cfg = refine_config_for_snapshot(cfg, factor)
        space = space_for_cfg(cfg)
        threshold = gain_threshold if gain_threshold is not None else j_gain_threshold(selected)
        epw_to = float(refined_cfg.mesh.epw)
        st = state(run_id, epw_to)
        for row, h in zip(selected, wanted):
            rec: dict = {"run": run_dir.as_posix(), "design_hash": h, "factor": float(factor),
                         "epw_from": float(cfg.mesh.epw), "epw_to": epw_to,
                         "check": REFINE_CHECK}
            try:
                grid = reference_grid(cfg, row, refined_cfg)
            except GridMismatchError as exc:
                rec["flags"] = {"grid_mismatch": True}
                rec["error"] = str(exc)
                results.append(rec)
                echo(f"  {h}: REFUSED (grid): {exc}")
                continue
            rec["grid"] = {"solve_hash": grid["solve_hash"], "n_freqs": grid["n_freqs"],
                           "mode": grid["mode"], "same_grid": True}
            rec["reference"] = {
                "source": "stored screen row (search.ndjson)",
                "J": float(row["objective"]), "terms": row.get("terms") or {},
                "metrics": metric_summary(row.get("metrics")),
                "terms_stored": bool(row.get("terms")),
                "metrics_stored": bool(row.get("metrics")),
                "n_triangles": row.get("n_triangles"), "n_dof": row.get("n_dof"),
                "peak_vram_mb": row.get("peak_vram_mb"), "solve_hash": grid["solve_hash"],
            }
            if h in st["done"]:
                rec["refined"] = {"skipped": "already ok in this run dir"}
                results.append(rec)
                echo(f"  {h} epw x{factor:g}: already ok in {st['dir']}; skipped")
                continue
            if dry_run:
                rec["refined"] = {"dry_run": True}
                results.append(rec)
                echo(f"  {h} epw x{factor:g}: DRY RUN (ref J={row['objective']:.5f})")
                continue
            if st["ctx"] is None:
                st["dir"].mkdir(parents=True, exist_ok=True)
                st["ctx"] = make_ctx_fn(snapshot_cfg, store, cache_dir=cache_dir,
                                        trace_fraction=trace_fraction,
                                        ndjson=st["dir"] / "search.ndjson")
                _write_mode_meta(st["dir"], snapshot_cfg, run_dir, REFINE_MODE, rundir, {
                    "check": REFINE_CHECK,
                    "mesh_refine": {"factor": float(factor), "epw_from": float(cfg.mesh.epw),
                                    "epw_to": epw_to,
                                    "reference_solve_hash": grid["solve_hash"]},
                })
            if teardown_per_design:
                warm_fn(cfg.solve.backend)
            mem = vram_factory(period=1.0) if vram_factory else None
            t0 = time.perf_counter()
            try:
                with (mem if mem is not None else contextlib.nullcontext()):
                    ev = evaluate_fn(_design_for(row), space, snapshot_cfg, REFINE_MODE,
                                     st["dir"], store, cfg.solve.backend, ctx=st["ctx"])
            finally:
                if mem is not None:
                    rec["vram"] = mem.record()
            rec["wall_s"] = round(time.perf_counter() - t0, 2)
            if teardown_per_design and teardown_fn is not None:
                try:
                    rec["teardown_forced_pids"] = list(teardown_fn(verify=True) or [])
                    rec["teardown_verified"] = True
                except Exception as exc:  # noqa: BLE001 - reported, never swallowed
                    rec["teardown_verified"] = False
                    rec["teardown_error"] = f"{type(exc).__name__}: {exc}"
            refined = {"ok": not ev.error, "error": ev.error or None,
                       "J": None if ev.error else float(ev.objective),
                       "terms": ev.terms if not ev.error else None,
                       "n_triangles": None, "n_dof": None, "cap": int(cfg.mesh.dof_cap(REFINE_MODE))}
            if ev.mesh is not None:
                refined["n_triangles"] = int(ev.mesh.n_triangles)
                refined["n_dof"] = (int(ev.mesh.n_dof) if ev.mesh.n_dof is not None
                                    else _estimate_dofs(ev.mesh, cfg))
                refined["mesh_hash"] = ev.mesh_hash
            if ev.error:
                from hornlab_search.search.evaluate import error_kind
                refined["error_kind"] = error_kind(ev.error)
            if metrics_json_fn is not None and not ev.error:
                refined["metrics"] = metric_summary(metrics_json_fn(ev.metrics))
            if not ev.error:
                st["done"].add(h)
            rec["refined"] = refined
            rec["delta"] = {
                "J": (None if ev.error or rec["reference"]["J"] is None
                      else float(ev.objective) - rec["reference"]["J"]),
                "terms": term_deltas(rec["reference"]["terms"], ev.terms),
                "metrics": _metric_delta(rec["reference"]["metrics"], refined.get("metrics")),
            }
            flags = {"mesh_sensitive": None, "cap_bound": False, "spilled": False,
                     "grid_mismatch": False}
            if not ev.error and rec["delta"]["J"] is not None and threshold is not None:
                flags["mesh_sensitive"] = abs(rec["delta"]["J"]) > threshold
            if refined.get("error_kind") == "mesh_too_large":
                flags["cap_bound"] = True
                flags["verdict"] = mesh_verdict(None, cap_bound_at=refined["cap"])
            if rec.get("vram", {}).get("spilled"):
                flags["spilled"] = True
            rec["flags"] = flags
            results.append(rec)
            if ev.error:
                echo(f"  {h} epw x{factor:g}: FAILED ({refined.get('error_kind') or 'error'}): "
                     f"{(ev.error or '').splitlines()[0][:90]}")
            else:
                echo(f"  {h} epw x{factor:g}: ref J={rec['reference']['J']:.5f} -> "
                     f"J={ev.objective:.5f} (dJ={rec['delta']['J']:+.5f}, "
                     f"mesh_sensitive={flags['mesh_sensitive']}, "
                     f"tri={refined['n_triangles']}, dof={refined['n_dof']})")

    if not dry_run:
        for state_v in states.values():
            if (state_v["dir"] / "run.json").is_file():
                rundir.update_run_json(state_v["dir"], status="finished",
                                       finished_utc=rundir.utc_now(),
                                       stop_reason=f"{REFINE_CHECK}: stored row vs epw-refined")
        # Per-design night jobs share one out root; merge into a single record instead of letting
        # the last job overwrite the others. Re-running a design replaces its entry.
        record_path = out_root / "refine.json"
        merged: dict[tuple, dict] = {}
        if record_path.is_file():
            try:
                for old in json.loads(record_path.read_text(encoding="utf-8")).get("designs") or []:
                    merged[(str(old.get("run")), str(old.get("design_hash")))] = old
            except (OSError, ValueError):
                merged = {}
        for new in results:
            merged[(str(new.get("run")), str(new.get("design_hash")))] = new
        _write_json(record_path, {
            "check": REFINE_CHECK,
            "factor": float(factor),
            "note": "reference = stored screen row (no re-solve); refined = same screen grid, only "
                    "mesh.epw changed. delta.J > j_gain_threshold marks the design mesh-sensitive.",
            "j_gain_threshold": (gain_threshold if gain_threshold is not None
                                  else j_gain_threshold(all_selected)),
            "noise_floor_db": NOISE_FLOOR_DB,
            "discretization_floor_db": DISCRETIZATION_FLOOR_DB,
            "designs": [merged[k] for k in sorted(merged)],
        })
    return results


def _estimate_dofs(mesh, cfg) -> int:
    from hornlab_search.mesh import sizing
    return int(sizing.estimate_dofs(int(mesh.n_triangles), str(mesh.quadrants),
                                    float(cfg.mesh.dof_per_triangle)))


def _metric_delta(ref: dict | None, new: dict | None) -> dict:
    if not ref or not new or not ref.get("present") or not new.get("present"):
        return {}
    out = {}
    for key in ("bw_h_deg", "bw_v_deg", "di_db", "ripple_h_db", "ripple_v_db"):
        a, b = ref.get(key), new.get(key)
        out[key] = None if a is None or b is None else float(b) - float(a)
    return out


# ------------------------------------------------------------------ CPU mesh sizing dry run


def _lifted_cfg(cfg, factor: float):
    """Diagnostic copy with the screen cap lifted, ONLY to size a cap-bound candidate mesh."""
    import dataclasses as dc
    refined = refine_config(cfg, factor)
    cap = int(refined.mesh.dof_cap("screen"))
    lifted = max(4 * cap, 4 * int(cfg.mesh.dof_cap("screen")))
    return dc.replace(refined, mesh=dc.replace(refined.mesh,
                                               dof_cap_screen=lifted, dof_cap_verify=lifted,
                                               dof_cap_final=lifted))


def _build_one(design, cfg_v, out_dir, *, build_fn, summary_fn) -> dict:
    from hornlab_search.config import mesh_spec
    from hornlab_search.mesh import sizing
    from hornlab_search.types import GeometryInvalidError, MeshTooLargeError

    ms = mesh_spec(REFINE_MODE, cfg_v)
    t0 = time.perf_counter()
    base = {"epw": float(cfg_v.mesh.epw), "f_max_hz": float(ms.f_max_hz),
            "mesh_hash": ms.hash(), "cap": int(cfg_v.mesh.dof_cap(REFINE_MODE))}
    try:
        res = build_fn(design, ms, cfg_v, out_dir, mode=REFINE_MODE)
    except MeshTooLargeError as exc:
        return {**base, "ok": False, "cap_bound": True, "seconds": round(time.perf_counter() - t0, 2),
                "error": f"mesh_too_large: {exc}"}
    except GeometryInvalidError as exc:
        return {**base, "ok": False, "cap_bound": False,
                "seconds": round(time.perf_counter() - t0, 2),
                "error": f"invalid_geometry: {exc}"}
    summary = summary_fn(Path(res.path))
    dpt = float(cfg_v.mesh.dof_per_triangle)
    dof_est = int(sizing.estimate_dofs(int(res.n_triangles), str(res.quadrants), dpt))
    nodes = int(summary.get("n_nodes_used") or 0)
    return {**base, "ok": True, "cap_bound": False,
            "n_triangles": int(res.n_triangles), "n_nodes_used": nodes,
            "dof": max(dof_est, nodes), "res_mm": res.res_mm,
            "seconds": round(float(res.seconds), 2)}


def build_meshes(pairs, out_root, *, config_for_run, factors, build_fn=None, summary_fn=None,
                 echo=print) -> list[dict]:
    """Build the stored-resolution reference mesh and each refined candidate on CPU (no solve)."""
    from hornlab_search.mesh.build import build_mesh, read_msh_summary

    build_fn = build_fn or build_mesh
    summary_fn = summary_fn or read_msh_summary
    out_root = Path(out_root).resolve()
    meshes_root = out_root / "meshes"
    meshes_root.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for run, h in pairs:
        run_dir = Path(run)
        if not (run_dir / "search.ndjson").is_file():
            raise MissingDesignError(f"{run_dir} has no search.ndjson")
        cfg = config_for_run(run_dir)
        row = select_rows(read_ndjson(run_dir / "search.ndjson"), [h])[0]
        design = _design_for(row)
        rec = {"run": run_dir.as_posix(), "design_hash": h,
               "stored": {"n_triangles": row.get("n_triangles"), "n_dof": row.get("n_dof"),
                          "J": row.get("objective")},
               "candidates": {}}
        # factor 1.0 = the reference build at the stored epw (same as the stored screen mesh)
        ref_dof = row.get("n_dof")
        for label, factor in [("ref", 1.0)] + [(f"x{f:g}", float(f)) for f in factors]:
            cfg_v = cfg if factor == 1.0 else refine_config(cfg, factor)
            built = _build_one(design, cfg_v, meshes_root / f"{h}__{label}",
                               build_fn=build_fn, summary_fn=summary_fn)
            built["est_dof_scaled"] = (None if ref_dof is None
                                       else int(round(float(ref_dof) * factor * factor)))
            if built.get("cap_bound"):
                lifted_cfg = _lifted_cfg(cfg, factor)
                lifted = _build_one(design, lifted_cfg,
                                    meshes_root / f"{h}__{label}_lifted",
                                    build_fn=build_fn, summary_fn=summary_fn)
                built["diagnostic"] = {k: lifted.get(k) for k in
                                       ("ok", "n_triangles", "n_nodes_used", "dof", "cap",
                                        "error", "seconds", "res_mm")}
                built["diagnostic"]["cap_lifted"] = int(
                    lifted_cfg.mesh.dof_cap(REFINE_MODE))
                dof = lifted.get("dof")
                built["verdict"] = mesh_verdict(dof, cap_bound_at=built["cap"])
                if not lifted.get("ok") and dof is None:
                    est = built["est_dof_scaled"]
                    built["verdict"] = (
                        f"CAP-BOUND at {built['cap']} DOF (not a refinement at the existing cap); "
                        f"diagnostic build refused: invalid_geometry")
                    if est is not None and est > QUARTER_OOM_UPPER_DOF:
                        built["verdict"] += (f"; also mesh check infeasible on this card "
                                             f"(est. {est} DOF)")
            elif built.get("ok"):
                dof = built.get("dof")
                built["verdict"] = mesh_verdict(dof)
                if factor == 1.0:
                    ref_dof = dof
            else:
                est = built["est_dof_scaled"]
                if est is not None and est > QUARTER_OOM_UPPER_DOF:
                    built["verdict"] = (
                        f"mesh check infeasible on this card (est. {est} DOF); mesher refused "
                        f"at epw {built['epw']:g}: invalid_geometry")
                else:
                    built["verdict"] = ("build refused (geometry): "
                                        + str(built.get("error"))[:120])
            rec["candidates"][label] = built
            echo(f"  {h} {label} (epw {built['epw']:g}): "
                 + (f"tri={built.get('n_triangles')} dof={built.get('dof')} "
                    f"{built['seconds']}s -> {built['verdict']}" if built.get("ok")
                    else f"{built.get('error', '')[:110]} -> {built['verdict']}"))
        results.append(rec)

    _write_json(out_root / "mesh_dryrun.json", {
        "check": REFINE_CHECK,
        "stored_resolution_only": "reference built at the run's stored epw; no solve was run",
        "quarter_oom_onset_dof": QUARTER_OOM_ONSET_DOF,
        "quarter_oom_upper_dof": QUARTER_OOM_UPPER_DOF,
        "designs": results,
    })
    return results


# ------------------------------------------------------------------ CLI


def _load_vram_class():
    import importlib.util
    path = REPO_ROOT / "tools" / "bench" / "_bench_common.py"
    spec = importlib.util.spec_from_file_location("bench_common", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.GpuMemPeak


def main(argv: list[str] | None = None) -> int:
    from hornlab_search.config import load_config
    from hornlab_search.dataset.store import DatasetStore
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.search.evaluate import evaluate, make_context, metrics_to_json
    from hornlab_search.search.gpulock import GpuBusyError, gpu_lock
    from hornlab_search.solve import worker

    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--design", action="append", metavar="RUN_DIR:HASH",
                    help="repeatable: a run directory and one of its design hashes")
    ap.add_argument("--designs-file", metavar="CSV", help="CSV with columns run,design")
    ap.add_argument("--out", required=True,
                    help="output root; one run dir per <run>__<tier> plus the JSON record")
    ap.add_argument("--modes", default="verify,finalist",
                    help="B1f pair mode tiers (default verify,finalist). FREQUENCY fidelity only; "
                         "the mesh is unchanged. Ignored in mesh mode.")
    ap.add_argument("--refine-epw-factor", type=float, metavar="F",
                    help="B1 mesh mode: multiply the stored mesh.epw by F, same screen grid")
    ap.add_argument("--build-meshes", action="store_true",
                    help="CPU-only sizing dry run: build the reference and refined meshes, no solve")
    ap.add_argument("--refine-factors", metavar="F1,F2",
                    help="with --build-meshes: refined candidates to build (e.g. 2,3)")
    ap.add_argument("--gain-threshold", type=float, metavar="DJ", default=None,
                    help="B1 mesh mode: |delta J| above this marks a design mesh-sensitive "
                         "(default: smallest adjacent J gap in the requested set)")
    ap.add_argument("--teardown-per-design", action=argparse.BooleanOptionalAction, default=True,
                    help="B1 mesh mode: verified BEAT-host teardown after each design (default on)")
    ap.add_argument("--record-vram", action=argparse.BooleanOptionalAction, default=True,
                    help="B1 mesh mode: per-design baseline/peak + shared-usage record "
                         "(default on)")
    ap.add_argument("--cache-dir", default=None,
                    help="shared solve cache (default: none, so the check really solves)")
    ap.add_argument("--dataset-dir", default="dataset")
    ap.add_argument("--trace-fraction", type=float, default=0.0)
    ap.add_argument("--dry-run", action="store_true", help="selection only (or mesh sizing only)")
    args = ap.parse_args(argv)

    mesh_mode = args.refine_epw_factor is not None or args.build_meshes
    if mesh_mode and args.refine_epw_factor is not None and args.build_meshes:
        print("choose one: --refine-epw-factor (solve) or --build-meshes (dry run)", file=sys.stderr)
        return 2
    if args.refine_epw_factor is not None and not args.refine_epw_factor > 0:
        print("--refine-epw-factor must be > 0", file=sys.stderr)
        return 2
    if args.build_meshes and not args.dry_run:
        print("--build-meshes requires --dry-run (it never solves)", file=sys.stderr)
        return 2
    if args.build_meshes and not args.refine_factors:
        print("--build-meshes needs --refine-factors (e.g. 2,3)", file=sys.stderr)
        return 2
    try:
        refine_factors = [float(x) for x in args.refine_factors.split(",")] \
            if args.refine_factors else []
    except ValueError:
        print("--refine-factors must be comma-separated numbers (e.g. 2,3)", file=sys.stderr)
        return 2
    if any(f <= 0 for f in refine_factors):
        print("--refine-factors values must be > 0", file=sys.stderr)
        return 2
    if mesh_mode and args.modes != "verify,finalist":
        print("--modes is a B1f pair-mode flag; it does not apply to mesh mode", file=sys.stderr)
        return 2
    modes = tuple(m.strip() for m in args.modes.split(",") if m.strip())
    bad = [m for m in modes if m not in MODES]
    if not mesh_mode and bad:
        print(f"fidelity_pairs: unknown mode(s) {bad}; known {list(MODES)}", file=sys.stderr)
        return 2
    try:
        pairs = parse_design_specs(args.design, args.designs_file)
    except (MissingDesignError, OSError) as exc:
        print(f"fidelity_pairs FAILED: {exc}", file=sys.stderr)
        return 2

    cfgs: dict[str, object] = {}

    def config_for_run(run_dir: Path):
        key = str(run_dir)
        if key not in cfgs:
            cfgs[key] = load_config(run_dir / "config.yaml")
        return cfgs[key]

    # ---- CPU-only mesh sizing dry run (no solve, no GPU lock)
    if args.build_meshes:
        try:
            results = build_meshes(pairs, args.out, config_for_run=config_for_run,
                                   factors=refine_factors)
        except (MissingDesignError, OSError, ValueError) as exc:
            print(f"fidelity_pairs FAILED: {exc}", file=sys.stderr)
            return 2
        refused = [r for r in results for c in r["candidates"].values() if not c.get("ok")]
        bad_ref = [r for r in results if not r["candidates"]["ref"].get("ok")]
        print(f"fidelity_pairs mesh sizing {'FAILED' if bad_ref else 'COMPLETE'}: "
              f"{len(results)} designs; {len(refused)} candidate build(s) refused (expected "
              f"findings recorded); record {Path(args.out) / 'mesh_dryrun.json'}")
        return 1 if bad_ref else 0

    store = None if args.dry_run else DatasetStore(REPO_ROOT / args.dataset_dir)
    worker.install_handlers()
    vram_factory = _load_vram_class() if (
        mesh_mode and args.record_vram and not args.dry_run) else None
    try:
        with (gpu_lock("fidelity_pairs: " + " ".join(f"{r}:{h}" for r, h in pairs)[:120])
              if not args.dry_run else contextlib.nullcontext()):
            if args.refine_epw_factor is not None:
                results = run_refine(
                    pairs, args.out, config_for_run=config_for_run, evaluate_fn=evaluate,
                    make_ctx_fn=make_context, warm_fn=worker.warm,
                    space_for_cfg=DesignSpace.from_config, factor=args.refine_epw_factor,
                    store=store, cache_dir=args.cache_dir,
                    trace_fraction=args.trace_fraction, teardown_fn=worker.shutdown,
                    teardown_per_design=args.teardown_per_design, vram_factory=vram_factory,
                    metrics_json_fn=metrics_to_json, gain_threshold=args.gain_threshold,
                    dry_run=args.dry_run)
            else:
                results = run_pairs(
                    pairs, args.out, config_for_run=config_for_run, evaluate_fn=evaluate,
                    make_ctx_fn=make_context, warm_fn=worker.warm,
                    space_for_cfg=DesignSpace.from_config, store=store,
                    cache_dir=args.cache_dir, modes=modes, trace_fraction=args.trace_fraction,
                    dry_run=args.dry_run)
    except GpuBusyError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (MissingDesignError, GridMismatchError) as exc:
        print(f"fidelity_pairs FAILED: {exc}", file=sys.stderr)
        return 2

    label = REFINE_CHECK if mesh_mode else PAIR_CHECK
    if mesh_mode:
        failed = [r for r in results if r.get("error")
                  or (r.get("refined") or {}).get("ok") is False
                  or (r.get("flags") or {}).get("spilled")
                  or (r.get("teardown_verified") is False)]
    else:
        failed = [r for r in results for m, v in (r.get("modes") or {}).items() if v and not v["ok"]]
    print(f"fidelity_pairs [{label}] {'FAILED' if failed else 'OK'}: {len(results)} designs"
          + ("" if mesh_mode else f" x {len(modes)} tiers")
          + f", {len(failed)} failed; output {args.out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
