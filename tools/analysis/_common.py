"""Shared helpers for the `tools/analysis/` evolutionary-analysis toolkit (2026-11-12).

Pure offline, stdlib + numpy/scipy (+ matplotlib with the Agg backend, optional
sklearn is imported lazily and only where a tool says so). Reads run dirs
(``search.ndjson`` / ``config.yaml`` / ``run.json``) read-only; every output goes
to a caller-provided ``--out`` folder. Never imports from the GUI, never writes
into ``runs/``. Schema per report: ``tools/analysis/schema.md``.

Terminology lives in schema.md; the core ones again here because every tool uses
them: a *valid row* has ``ok == true``; a *new eval* is non-``cached``; the
convergence X axis counts *new valid* evaluations in file order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[2]

#: matplotlib is chart-only and must never pop a window; force the Agg backend
#: before anything else imports pyplot.
import matplotlib  # noqa: E402

matplotlib.use("Agg")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _finite(x):
    """JSON-able float: non-finite -> None (report JSON is written with allow_nan=False)."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def read_ndjson(path: Path) -> list[dict]:
    """Rows of a ``search.ndjson``; torn/truncated trailing lines are skipped, never fatal."""
    out: list[dict] = []
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_yaml(path: Path):
    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def params_flat(row: dict) -> dict:
    """Flat numeric knob dict of a row; generator families nest theirs under ``grid.knobs``."""
    p = row.get("params")
    if not isinstance(p, dict):
        return {}
    if isinstance(p.get("grid"), dict) and isinstance(p["grid"].get("knobs"), dict):
        p = p["grid"]["knobs"]
    return {str(k): float(v) for k, v in p.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(float(v))}


def knobs_shared(rows: list[dict]) -> list[str]:
    keys: list[set] = [set(params_flat(r)) for r in rows]
    if not keys:
        return []
    inter = set.intersection(*keys)
    return sorted(inter)


def bounds_of(config: dict | None) -> dict:
    """``{key: (lo, hi)}`` numeric search bounds of a config (``search: false`` knobs excluded)."""
    out: dict[str, tuple[float, float]] = {}
    b = (config or {}).get("bounds") or {}
    for k, v in b.items():
        if not isinstance(v, dict) or v.get("search") is False:
            continue
        try:
            lo, hi = float(v["lo"]), float(v["hi"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(lo) and math.isfinite(hi) and hi > lo:
            out[str(k)] = (lo, hi)
    return out


def run_config(run_dir: Path) -> dict:
    """The run's effective config: run.json's snapshot first, else config.yaml. Read-only."""
    run_json = read_json(Path(run_dir) / "run.json") or {}
    cfg = run_json.get("config")
    if not isinstance(cfg, dict):
        cfg = read_yaml(Path(run_dir) / "config.yaml")
    return cfg if isinstance(cfg, dict) else {}


def run_meta(run_dir: Path, cfg: dict | None = None) -> dict:
    """``{brief, family, objective_version, mode}`` provenance of a run dir."""
    run_json = read_json(Path(run_dir) / "run.json") or {}
    cfg = cfg if cfg is not None else run_config(run_dir)
    rows = read_ndjson(Path(run_dir) / "search.ndjson")
    fam = run_json.get("family") or cfg.get("family")
    versions: dict[int, int] = {}
    modes: dict[str, int] = {}
    for r in rows:
        v = r.get("objective_version")
        if isinstance(v, int):
            versions[v] = versions.get(v, 0) + 1
        m = r.get("mode")
        if isinstance(m, str):
            modes[m] = modes.get(m, 0) + 1
    majority = lambda counts: (max(counts, key=counts.get) if counts else None)
    return {
        "brief": run_json.get("config_name") or cfg.get("name"),
        "family": fam,
        "objective_version": majority(versions),
        "mode": majority(modes),
        "cma_seed": run_json.get("cma_seed"),
        "has_rows": bool(rows),
    }


def load_run(run_dir: Path) -> dict:
    """Everything the tools need from one run dir, read-only."""
    run_dir = Path(run_dir)
    if not (run_dir / "search.ndjson").exists():
        raise FileNotFoundError(f"{run_dir}: no search.ndjson — not a run dir")
    cfg = run_config(run_dir)
    rows = read_ndjson(run_dir / "search.ndjson")
    meta = run_meta(run_dir, cfg)
    return {"run_dir": run_dir, "config": cfg, "rows": rows,
            "bounds": bounds_of(cfg), "meta": meta}


def _sha16(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _finite_float_list(values) -> list[float]:
    out: list[float] = []
    for v in values or []:
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            out.append(f)
    return out


def _task_config(config: dict) -> dict:
    """Config with the per-run search seed/budget removed (task identity, not schedule)."""
    try:
        cfg = json.loads(json.dumps(config or {}, default=str))
    except (TypeError, ValueError):
        return {}
    search = cfg.get("search")
    if isinstance(search, dict):
        search.pop("seed", None)
        search.pop("budget", None)
    return cfg


def run_fingerprint(run: dict) -> dict:
    """Task/scoring/grid/fidelity/software identity of one run (analysis-only)."""
    run_dir = Path(run["run_dir"])
    run_json = read_json(run_dir / "run.json") or {}
    cfg = run.get("config") or {}
    meta = run.get("meta") or {}
    solve = cfg.get("solve")
    if not isinstance(solve, dict):
        solve = {}
    mesh = cfg.get("mesh")
    if not isinstance(mesh, dict):
        mesh = {}
    first_metrics: dict = {}
    for row in run.get("rows") or []:
        metrics = row.get("metrics")
        if isinstance(metrics, dict) and metrics.get("freqs_hz"):
            first_metrics = metrics
            break
    grid = {
        "freqs_hz": _finite_float_list(first_metrics.get("freqs_hz")),
        "angle_count": solve.get("angle_count"),
        "balloon": solve.get("balloon"),
        "balloon_points_screen": solve.get("balloon_points_screen"),
        "quadrants": mesh.get("quadrants"),
        "backend": solve.get("backend") or run_json.get("backend"),
    }
    target = cfg.get("target")
    if not isinstance(target, dict):
        target = {}
    software = run_json.get("lib_shas")
    return {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "brief": meta.get("brief"),
        "family": meta.get("family"),
        "objective_version": meta.get("objective_version"),
        "mode": meta.get("mode"),
        "cma_seed": meta.get("cma_seed"),
        "backend": grid["backend"],
        "grid": grid,
        "grid_hash": _sha16(grid),
        "target": target,
        "target_hash": _sha16(target),
        "task_config_hash": _sha16(_task_config(cfg)),
        "config_sha": run_json.get("config_sha"),
        "software": software,
        "software_hash": _sha16(software) if software else None,
        "software_unknown": not bool(software),
        "runtime": run_json.get("runtime"),
    }


def compare_compatibility(runs: list[dict], *, block_task_config: bool = False) -> dict:
    """Compare task/objective/grid/fidelity/software identity across runs.

    ``blocking`` lists reasons that forbid pooled *prospective* inference.  The
    tools still hard-error on objective/brief/family mismatch; grid/fidelity/
    software drift is reported and blocks paired inference rather than silently
    pooling incompatible measurements.  Different search treatment settings are
    expected in an A/B comparison and are not compared here unless
    ``block_task_config`` is True (same-config seed groups).
    """
    fingerprints = [run_fingerprint(r) for r in runs]
    keys = ("objective_version", "brief", "family", "mode", "backend",
            "grid_hash", "target_hash")
    if block_task_config:
        keys = keys + ("task_config_hash",)
    same: dict[str, bool] = {}
    differing: dict[str, list] = {}
    blocking: list[str] = []
    for key in keys:
        values = {json.dumps(fp.get(key), sort_keys=True, default=str) for fp in fingerprints}
        same[key] = len(values) <= 1
        if len(values) > 1:
            differing[key] = sorted(values)
            blocking.append(f"{key}_mismatch")
    software_hashes = {fp.get("software_hash") for fp in fingerprints}
    if None in software_hashes:
        blocking.append("software_unknown")
    non_null = {h for h in software_hashes if h is not None}
    if len(non_null) > 1:
        blocking.append("software_drift")
    if len(software_hashes) > 1 and len(non_null) <= 1:
        blocking.append("software_partially_unknown")
    variants: dict[str, int] = {}
    for fp in fingerprints:
        name = fp.get("software_hash") or "unknown"
        variants[name] = variants.get(name, 0) + 1
    task_blocking = [b for b in blocking
                     if b.split("_", 1)[0] in ("objective", "brief", "family")]
    return {
        "n_runs": len(fingerprints),
        "same": same,
        "differing": differing,
        "blocking": sorted(set(blocking)),
        "software_variants": dict(sorted(variants.items())),
        "compatible_for_descriptive": not task_blocking,
        "compatible_for_inference": not blocking,
        "fingerprints": fingerprints,
    }


def replicate_info(run: dict) -> dict:
    """Replicate identity: resume segments/restarts inside one run are one replicate."""
    run_json = read_json(Path(run["run_dir"]) / "run.json") or {}
    resumes = run_json.get("resumes") or []
    restarts = run_json.get("restarts") or []
    return {
        "run_id": Path(run["run_dir"]).name,
        "cma_seed": (run.get("meta") or {}).get("cma_seed"),
        "n_resume_segments": 1 + len(resumes),
        "resume_timestamps": list(resumes),
        "n_restarts": len(restarts),
        "is_resumed": bool(resumes),
        "has_restarts": bool(restarts),
        "note": "resume segments and restarts are parts of one replicate, not extra seeds",
    }


def replicate_summary(runs: list[dict]) -> dict:
    """Several run dirs with the same CMA seed are duplicates, not independent reps."""
    infos = [replicate_info(r) for r in runs]
    by_seed: dict[Any, list[str]] = {}
    for info in infos:
        by_seed.setdefault(info["cma_seed"], []).append(info["run_id"])
    duplicates = {str(seed): ids for seed, ids in by_seed.items() if len(ids) > 1}
    n_independent = len(infos) - sum(len(ids) - 1 for ids in duplicates.values())
    return {
        "n_run_dirs": len(infos),
        "n_independent_replicates": n_independent,
        "duplicate_seed_run_dirs": duplicates,
        "resumed_runs": [i["run_id"] for i in infos if i["is_resumed"]],
        "restarted_runs": [i["run_id"] for i in infos if i["has_restarts"]],
        "note": "duplicate run dirs sharing a CMA seed are not independent evidence",
    }


def valid_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("ok") is True]


def new_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("cached") is False]


# ------------------------------------------------------- outcome classification
#
# ``search.ndjson`` failure kinds in the inspected archive are: invalid_geometry,
# invalid_envelope, mesh_too_large, solve_failed, exception (plus older/unknown
# labels).  Only the first three are cheap pre-BEM refusals; solve_failed is an
# infrastructure/solver event with real elapsed work; exception is a pipeline
# failure whose stage is not proven by the kind alone.  Never collapse them.
CHEAP_REFUSAL_KINDS = ("invalid_geometry", "invalid_envelope", "mesh_too_large")
GEOMETRY_REFUSAL_KINDS = ("invalid_geometry",)
ENVELOPE_REFUSAL_KINDS = ("invalid_envelope",)
RESOURCE_REFUSAL_KINDS = ("mesh_too_large",)
SOLVER_FAILURE_KINDS = ("solve_failed",)
PIPELINE_FAILURE_KINDS = ("exception", "metrics_failed")


def failed_kind(row: dict) -> str:
    """Best-effort failure kind of a row; ``unknown`` is a real answer, not a guess."""
    kind = row.get("kind")
    if isinstance(kind, str) and kind.strip():
        return kind.strip()
    err = row.get("error")
    if isinstance(err, str) and err.strip():
        head = err.split(":", 1)[0].strip()
        return head or "unknown"
    return "unknown"


def outcome_category(row: dict) -> str:
    """``valid | cheap_refusal | solver_failure | pipeline_failure | unknown_failure``.

    ``cheap_refusal`` means a deterministic pre-BEM refusal (geometry/envelope/
    resource); it is not a measured acoustic result and not a BEM call.
    """
    if row.get("ok") is True:
        return "valid"
    kind = failed_kind(row)
    if kind in CHEAP_REFUSAL_KINDS:
        return "cheap_refusal"
    if kind in SOLVER_FAILURE_KINDS:
        return "solver_failure"
    if kind in PIPELINE_FAILURE_KINDS:
        return "pipeline_failure"
    return "unknown_failure"


def row_total_seconds(row: dict) -> float | None:
    """The row's recorded ``seconds.total`` (finite float), else ``None``."""
    sec = (row.get("seconds") or {}).get("total")
    if sec is None:
        return None
    try:
        v = float(sec)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def row_solve_seconds(row: dict) -> float | None:
    """The row's recorded BEM ``seconds.solve`` (finite float), else ``None``.

    A positive value is direct evidence that at least one BEM solve attempt ran;
    a recorded ``solve_failed`` with zero/absent seconds still counts as an
    inferred call in :func:`cost_ledger`.
    """
    sec = (row.get("seconds") or {}).get("solve")
    if sec is None:
        return None
    try:
        v = float(sec)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _parse_utc(value) -> float | None:
    """Epoch seconds of an ISO-8601 run timestamp, or ``None`` when unparseable."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def top_decile(rows: list[dict], n_min: int = 3) -> list[dict] | None:
    """The lowest-J ceil(n/10) valid rows (at least ``n_min``); None below 10 valid rows.

    Schema: the top decile is ``max(3, ceil(n_valid / 10))`` rows, and a run with
    < 10 valid rows has no top decile at all (tools degrade)."""
    valid = valid_rows(rows)
    if len(valid) < 10:
        return None
    n = max(n_min, math.ceil(len(valid) * 0.1))
    return sorted(valid, key=lambda r: float(r.get("objective", float("inf"))))[:n]


def best_so_far_curve(run: dict, *, include_failed_seconds: bool = False,
                      include_cached_seconds: bool = False) -> list[dict]:
    """Best-so-far over *new valid* evaluations, in row order, with wall seconds.

    The eval axis ``n`` counts new valid evaluations only (cached replays are not
    new evals).  The cost axis is cumulative ``seconds.total``:

    * default (``include_failed_seconds=False``) — the historical view: only the
      successful rows' seconds are summed.  This deliberately reproduces the old
      behaviour used by ``convergence.py``; it **understates** true elapsed work.
    * ``include_failed_seconds=True`` — every non-cached attempt's seconds are
      summed in row order, so refused/invalid/solver-failed work is included
      before the next valid point.  This is the honest cost axis for S3.
    * ``include_cached_seconds=True`` — cached replay overhead is also added.

    Points carry both ``wall_s`` (the selected basis) and ``wall_s_valid_only``
    (successful rows only), plus ``attempt_n`` (non-cached attempts so far).
    """
    out: list[dict] = []
    best = float("inf")
    wall = 0.0
    valid_wall = 0.0
    attempt_n = 0
    for r in run["rows"]:
        sec = row_total_seconds(r) or 0.0
        if r.get("cached") is True:
            if include_cached_seconds:
                wall += sec
            continue
        attempt_n += 1
        if include_failed_seconds:
            wall += sec
        if r.get("ok") is not True:
            continue
        try:
            obj = float(r["objective"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(obj) and obj < best:
            best = obj
        valid_wall += sec
        out.append({"n": len(out) + 1, "best": best,
                    "wall_s": wall if include_failed_seconds else valid_wall,
                    "wall_s_valid_only": valid_wall,
                    "attempt_n": attempt_n})
    return out


def cost_ledger(rows: list[dict], stats: dict | None = None,
                started_utc: str | None = None,
                finished_utc: str | None = None) -> dict:
    """Honest per-run cost/attempt ledger — counts and elapsed seconds stay separate.

    Distinguishes index rows, cached replays/hits, new attempts, valid evaluations,
    cheap pre-BEM refusals (geometry/envelope/resource), solver/infrastructure
    failures, pipeline/unknown failures, observed BEM calls (positive
    ``seconds.solve``), inferred BEM attempts (recorded ``solve_failed`` included)
    and timing observations usable by the bo-study-v1.1 cost extension.

    Elapsed seconds include failed/refused attempts.  ``wall_span`` is used only
    when both run timestamps parse; otherwise the label says
    ``accumulated_candidate_cost_no_wall_span`` and the overhead is ``None``.
    """
    rows_total = len(rows)
    cache_hits = 0
    cached_flag_unknown = 0
    valid_cached = 0
    attempts_new = 0
    valid_new = 0
    category_counts = {"cheap_refusal": 0, "solver_failure": 0,
                       "pipeline_failure": 0, "unknown_failure": 0}
    kind_counts: dict[str, int] = {}
    attempt_seconds = 0.0
    valid_seconds = 0.0
    failed_refused_seconds = 0.0
    cached_seconds = 0.0
    missing_seconds_attempts = 0
    bem_calls_observed = 0
    bem_calls_inferred = 0
    bem_seconds = 0.0
    timing_observations = 0
    z_log_seconds: list[float] = []
    for r in rows:
        sec = row_total_seconds(r)
        solve = row_solve_seconds(r)
        cached_flag = r.get("cached")
        if cached_flag is None:
            cached_flag_unknown += 1
        if cached_flag is True:
            cache_hits += 1
            if sec is not None:
                cached_seconds += sec
            if r.get("ok") is True:
                valid_cached += 1
            continue
        attempts_new += 1
        if sec is None:
            missing_seconds_attempts += 1
        else:
            attempt_seconds += sec
        cat = outcome_category(r)
        if cat == "valid":
            valid_new += 1
            if sec is not None:
                valid_seconds += sec
        else:
            category_counts[cat] += 1
            kind_counts[failed_kind(r)] = kind_counts.get(failed_kind(r), 0) + 1
            if sec is not None:
                failed_refused_seconds += sec
        if solve is not None and solve > 0:
            bem_calls_observed += 1
            bem_seconds += solve
            timing_observations += 1
            z_log_seconds.append(round(math.log(max(solve, 1e-3)), 9))
        elif cat == "solver_failure":
            # A recorded solve failure with no positive time still attempted a call.
            bem_calls_inferred += 1
    bem_calls_inferred += bem_calls_observed
    wall_span = None
    start_epoch = _parse_utc(started_utc)
    end_epoch = _parse_utc(finished_utc)
    if start_epoch is not None and end_epoch is not None and end_epoch >= start_epoch:
        wall_span = end_epoch - start_epoch
    recorded_total = attempt_seconds + cached_seconds
    overhead = (wall_span - recorded_total) if wall_span is not None else None
    cost_label = ("wall_start_end" if wall_span is not None
                  else "accumulated_candidate_cost_no_wall_span")
    out: dict[str, Any] = {
        "index_rows": rows_total,
        "cache_hits": cache_hits,
        "cached_flag_unknown": cached_flag_unknown,
        "attempts_new": attempts_new,
        "valid_evaluations_new": valid_new,
        "valid_evaluations_cached": valid_cached,
        "valid_evaluations_total": valid_new + valid_cached,
        "cheap_refusals": category_counts["cheap_refusal"],
        "geometry_refusals": kind_counts.get("invalid_geometry", 0),
        "envelope_refusals": kind_counts.get("invalid_envelope", 0),
        "resource_refusals": kind_counts.get("mesh_too_large", 0),
        "solver_failures": category_counts["solver_failure"],
        "pipeline_failures": category_counts["pipeline_failure"],
        "unknown_failures": category_counts["unknown_failure"],
        "failure_kinds": dict(sorted(kind_counts.items())),
        "actual_bem_calls_observed": bem_calls_observed,
        "actual_bem_calls_inferred": bem_calls_inferred,
        "actual_bem_seconds": bem_seconds,
        "timing_observations": timing_observations,
        "z_log_seconds": z_log_seconds,
        "elapsed_seconds": {
            "attempts_all_incl_failed_refused": attempt_seconds,
            "valid_new": valid_seconds,
            "failed_refused_attempts": failed_refused_seconds,
            "cached_replay": cached_seconds,
            "recorded_total": recorded_total,
            "wall_span": wall_span,
            "unaccounted_overhead": overhead,
            "missing_seconds_attempts": missing_seconds_attempts,
        },
        "cost_label": cost_label,
        "cost_model_gate": {
            "target": "z=log(max(actual_uncached_BEM_seconds,1e-3))",
            "min_timing_observations": 30,
            "n_timing_observations": timing_observations,
            "eligible": timing_observations >= 30,
            "status": ("eligible_not_fitted_in_m0" if timing_observations >= 30
                       else "unavailable_insufficient_timing"),
            "note": "M0 reports eligibility only; no cost GP is fitted and no "
                    "speedup is claimed.",
        },
    }
    if isinstance(stats, dict):
        out["run_stats"] = {
            "evaluations": stats.get("evaluations"),
            "non_cached": stats.get("non_cached"),
            "cache_hits": stats.get("cache_hits"),
            "failures": stats.get("failures"),
            "total_gpu_seconds": stats.get("total_gpu_seconds"),
            "total_mesh_seconds": stats.get("total_mesh_seconds"),
        }
        out["stats_reconciliation"] = {
            "index_rows_equal_evaluations": rows_total == stats.get("evaluations"),
            "attempts_new_equal_non_cached": attempts_new == stats.get("non_cached"),
            "cache_hits_equal": cache_hits == stats.get("cache_hits"),
            "failures_equal": (category_counts["cheap_refusal"]
                               + category_counts["solver_failure"]
                               + category_counts["pipeline_failure"]
                               + category_counts["unknown_failure"]) == stats.get("failures"),
        }
    return out


def sum_cost_ledgers(ledgers: list[dict]) -> dict:
    """Aggregate several :func:`cost_ledger` results with counts/seconds summed."""
    scalar_keys = ("index_rows", "cache_hits", "attempts_new", "valid_evaluations_new",
                   "valid_evaluations_cached", "cheap_refusals", "geometry_refusals",
                   "envelope_refusals", "resource_refusals", "solver_failures",
                   "pipeline_failures", "unknown_failures", "actual_bem_calls_observed",
                   "actual_bem_calls_inferred", "actual_bem_seconds",
                   "timing_observations")
    elapsed_keys = ("attempts_all_incl_failed_refused", "valid_new",
                    "failed_refused_attempts", "cached_replay", "recorded_total",
                    "wall_span", "unaccounted_overhead", "missing_seconds_attempts")
    out: dict[str, Any] = {k: 0 for k in scalar_keys}
    elapsed: dict[str, float] = {k: 0.0 for k in elapsed_keys}
    kinds: dict[str, int] = {}
    for led in ledgers:
        for k in scalar_keys:
            out[k] += led.get(k) or 0
        for k in elapsed_keys:
            v = (led.get("elapsed_seconds") or {}).get(k)
            if isinstance(v, (int, float)) and math.isfinite(float(v)):
                elapsed[k] += float(v)
        for k, v in (led.get("failure_kinds") or {}).items():
            kinds[k] = kinds.get(k, 0) + int(v)
    out["elapsed_seconds"] = elapsed
    out["failure_kinds"] = dict(sorted(kinds.items()))
    out["cost_model_status"] = ("eligible_not_fitted_in_m0"
                                if out["timing_observations"] >= 30
                                else "unavailable_insufficient_timing")
    return out


def cost_model_eligibility(cost_totals: dict, compatibility: dict,
                           min_observations: int = 30) -> dict:
    """bo-study-v1.1 cost-GP gate: >= 30 **and** compatible timing observations.

    Count alone is not enough: pooling timing rows across differing task/grid/
    fidelity/software identities is not a compatible cost dataset.  M0 reports
    eligibility only; it fits no model and claims no speedup.
    """
    n = int(cost_totals.get("timing_observations") or 0)
    count_ok = n >= min_observations
    compat_ok = bool(compatibility.get("compatible_for_inference"))
    if not count_ok:
        status = "unavailable_insufficient_timing"
    elif not compat_ok:
        status = "unavailable_incompatible_identity"
    else:
        status = "eligible_not_fitted_in_m0"
    return {
        "target": "z=log(max(actual_uncached_BEM_seconds,1e-3))",
        "min_observations": min_observations,
        "n_timing_observations": n,
        "count_gate_passed": count_ok,
        "compatibility_gate_passed": compat_ok,
        "compatibility_blocking": list(compatibility.get("blocking") or []),
        "eligible": count_ok and compat_ok,
        "status": status,
        "note": "M0 reports eligibility only; no cost GP is fitted and no speedup "
                "is claimed.",
    }


def evals_to_within(curve: list[dict], final_best: float, rel: float) -> int | None:
    """First new-valid-eval index whose best-so-far is within ``rel`` of ``final_best``.

    The best-so-far decreases monotonically towards ``final_best``, so the distance that
    can shrink is ``best - final_best`` (schema: "best-so-far <= 1.01 * final_best")."""
    if not curve or not math.isfinite(final_best):
        return None
    thresh = abs(final_best) * rel
    for p in curve:
        if p["best"] - final_best <= thresh:
            return int(p["n"])
    return None


def last20_improvement(curve: list[dict]) -> tuple[bool, float | None]:
    """(flag, improvement %) — best improved by > 1% of the final best inside the last 20%."""
    n = len(curve)
    if n < 10:
        return False, None
    final = curve[-1]["best"]
    tail_start = curve[max(0, math.ceil(n * 0.8)) - 1]["n"]
    best_before = min((p["best"] for p in curve if p["n"] < tail_start), default=final)
    if not math.isfinite(final) or final <= 0:
        return False, None
    imp_pct = (best_before - final) / max(abs(final), 1e-12) * 100.0
    return imp_pct > 1.0, imp_pct


def refusal_windows(rows: list[dict], w: int = 50) -> list[dict]:
    """Refusal rate by kind per window of ``w`` non-cached rows (last window may be shorter)."""
    new = new_rows(rows)
    out = []
    for start in range(0, len(new), w):
        win = new[start:start + w]
        kinds: dict[str, int] = {}
        refused = 0
        for r in win:
            if r.get("ok") is not True:
                refused += 1
                kind = str(r.get("kind") or r.get("error") or "unknown")
                kinds[kind] = kinds.get(kind, 0) + 1
        out.append({"w": [start + 1, start + len(win)], "rate": refused / len(win),
                    "kinds": kinds})
    return out


# ------------------------------------------------------------------ stats


def spearman(x, y) -> float | None:
    """Spearman rho; scipy when present, else an equivalent hand-rolled rank formula."""
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    good = np.isfinite(xv) & np.isfinite(yv)
    xv, yv = xv[good], yv[good]
    if xv.size < 3:
        return None
    if np.ptp(xv) == 0 or np.ptp(yv) == 0:
        return None  # a constant input has no defined rank correlation
    try:
        import scipy.stats as sps  # type: ignore

        rho = float(sps.spearmanr(xv, yv).statistic)  # type: ignore[union-attr]
        return rho if math.isfinite(rho) else None
    except Exception:  # noqa: BLE001 - degrade to the hand-rolled formula
        rx = _ranks(xv)
        ry = _ranks(yv)
        dx = rx - rx.mean()
        dy = ry - ry.mean()
        den = math.sqrt(float(dx @ dx) * float(dy @ dy))
        return float(dx @ dy) / den if den > 0 else None


def _ranks(v: np.ndarray) -> np.ndarray:
    # Ties share the average rank (scipy-compatible).
    order = np.argsort(v, kind="stable")
    ranks = np.empty(v.size, dtype=float)
    sorted_v = v[order]
    i = 0
    while i < v.size:
        j = i
        while j + 1 < v.size and sorted_v[j + 1] == sorted_v[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def bootstrap_ci(values: list[float], n_boot: int = 2000, seed: int = 0) -> list[float] | None:
    """Percentile bootstrap 95% CI of the median (fixed seed = reproducible reports)."""
    if len(values) < 3:
        return None
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    meds = np.median(arr[rng.integers(0, arr.size, size=(n_boot, arr.size))], axis=1)
    lo, hi = np.percentile(meds, [2.5, 97.5])
    return [float(lo), float(hi)]


def _normal_ppf(p: float) -> float:
    """Stdlib normal quantile (no SciPy dependency for planning arithmetic)."""
    from statistics import NormalDist

    return float(NormalDist().inv_cdf(p))


def paired_diff_ci(values, n_boot: int = 4000, seed: int = 0,
                   statistic: str = "mean") -> list[float] | None:
    """Percentile bootstrap CI of the paired-difference mean/median (fixed seed)."""
    arr = np.asarray([v for v in values if v is not None], dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        return None
    rng = np.random.default_rng(seed)
    samples = arr[rng.integers(0, arr.size, size=(n_boot, arr.size))]
    stat = samples.mean(axis=1) if statistic == "mean" else np.median(samples, axis=1)
    lo, hi = np.percentile(stat, [2.5, 97.5])
    return [float(lo), float(hi)]


def paired_summary(diffs, practical_delta: float | None = None,
                   n_boot: int = 4000, seed: int = 0) -> dict:
    """Paired-difference summary with CI, signs and a conservative decision.

    ``d = A - B`` for a paired comparison; negative means A has the lower J
    (better).  The decision uses the bootstrap CI of the mean paired difference
    against ``practical_delta``; a five-pair pilot is labelled a pilot, never a
    significance guarantee.
    """
    arr = np.asarray([v for v in (diffs or []) if v is not None], dtype=float)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    delta = float(practical_delta) if practical_delta is not None else 0.0
    out: dict[str, Any] = {
        "n_pairs": n,
        "difference_definition": "d = A - B (negative => A has lower J / is better)",
        "practical_delta": delta,
    }
    if n == 0:
        out.update({"status": "no_pairs", "decision": "insufficient_pairs"})
        return out
    mean = float(arr.mean())
    median = float(np.median(arr))
    sd = float(arr.std(ddof=1)) if n >= 2 else None
    a_better = int(np.sum(arr < 0))
    b_better = int(np.sum(arr > 0))
    ties = int(np.sum(arr == 0))
    direction = "a_better" if mean < 0 else ("b_better" if mean > 0 else None)
    ci_mean = paired_diff_ci(arr, n_boot=n_boot, seed=seed, statistic="mean")
    ci_median = bootstrap_ci(list(arr), n_boot=n_boot, seed=seed)
    if n < 2 or ci_mean is None:
        decision = "insufficient_pairs"
    elif n < 5:
        decision = "pilot_only"
    elif ci_mean[1] < -delta:
        decision = "a_better"
    elif ci_mean[0] > delta:
        decision = "b_better"
    else:
        decision = "inconclusive"
    out.update({
        "status": "ok",
        "mean": mean,
        "median": median,
        "sd": sd,
        "ci95_bootstrap_mean": ci_mean,
        "ci95_bootstrap_median": ci_median,
        "signs": {"a_better": a_better, "b_better": b_better, "ties": ties},
        "direction": direction,
        "decision": decision,
        "evidence_class": "pilot" if n < 10 else "larger_pilot",
        "pilot": n < 10,
        "note": ("Fewer than five pairs: pilot only; not a significance guarantee."
                 if n < 5 else
                 "Pilot-scale paired evidence; plan expansion from the paired variability."),
    })
    return out


def power_planning(pilot_diffs, practical_delta: float | None,
                   alpha: float = 0.05, power: float = 0.8) -> dict:
    """Sample-size planning from pilot paired differences and a practical target.

    Normal approximation to a paired one-sample test.  The practical target is a
    declared effect in J (or the chosen metric), not the historical max-min range
    and not one universal number.
    """
    arr = np.asarray([v for v in (pilot_diffs or []) if v is not None], dtype=float)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    if n < 2:
        return {"status": "unavailable", "reason": "need at least two pilot pairs",
                "pilot_n": n}
    sd = float(arr.std(ddof=1))
    if practical_delta is None or float(practical_delta) <= 0:
        return {"status": "unavailable", "reason": "declare a positive practical_delta",
                "pilot_n": n, "pilot_sd": sd}
    if sd <= 0:
        return {"status": "unavailable", "reason": "zero pilot paired-difference SD",
                "pilot_n": n}
    effect = abs(float(practical_delta)) / sd
    z_alpha = _normal_ppf(1.0 - alpha / 2.0)
    z_power = _normal_ppf(power)
    n_required = int(math.ceil(((z_alpha + z_power) / effect) ** 2))
    return {
        "status": "ok",
        "pilot_n": n,
        "pilot_mean": float(arr.mean()),
        "pilot_sd": sd,
        "practical_delta": float(practical_delta),
        "alpha": float(alpha),
        "power": float(power),
        "standardized_effect": effect,
        "n_pairs_required": n_required,
        "method": "normal approximation to a paired one-sample test",
        "note": "Planning estimate from the pilot; not a guarantee for a future study.",
    }


def _curve_to_budget(curve: list[dict], x_key: str, budget) -> list[dict]:
    if budget is None:
        return list(curve or [])
    out = []
    for p in curve or []:
        x = p.get(x_key)
        if isinstance(x, (int, float)) and math.isfinite(float(x)) and float(x) <= budget:
            out.append(p)
    return out


def value_at_budget(curve: list[dict], budget, x_key: str = "n") -> dict:
    """Best-so-far value reached by ``budget`` on the chosen axis (censoring-aware)."""
    sub = _curve_to_budget(curve, x_key, budget)
    if not sub:
        return {"value": None, "x": None, "censored": True, "observed": False,
                "x_key": x_key, "budget": budget}
    last = sub[-1]
    x = last.get(x_key)
    censored = bool(budget is not None and isinstance(x, (int, float)) and x < budget)
    return {"value": last.get("best"), "x": x, "censored": censored, "observed": True,
            "x_key": x_key, "budget": budget}


def time_to_target(curve: list[dict], target_j: float | None, x_key: str = "n",
                   budget=None) -> dict:
    """First x where best-so-far <= ``target_j``; censored at the observed budget."""
    if target_j is None:
        return {"reached": None, "value": None, "censored": None, "x_key": x_key,
                "target_j": None, "censored_at": None}
    target = float(target_j)
    sub = _curve_to_budget(curve, x_key, budget)
    for p in sub:
        best = p.get("best")
        if isinstance(best, (int, float)) and best <= target:
            return {"reached": True, "value": p.get(x_key), "censored": False,
                    "x_key": x_key, "target_j": target, "censored_at": None}
    last = sub[-1].get(x_key) if sub else None
    return {"reached": False, "value": None, "censored": True, "x_key": x_key,
            "target_j": target, "censored_at": last}


def ecdf_time_to_target(curves: list[list[dict]], target_j: float,
                        x_key: str = "n", budget=None) -> dict:
    """Step ECDF of time-to-target with explicit right-censoring.

    Censored runs stay in the denominator but are never counted as reached; the
    plotted fraction is therefore a lower bound on the uncensored CDF.  Their last
    observed budget is still an event x-coordinate so the censoring is visible.
    """
    events: list[tuple[float, bool]] = []
    n_reached = 0
    for curve in curves:
        t = time_to_target(curve, target_j, x_key=x_key, budget=budget)
        if t["reached"]:
            n_reached += 1
            events.append((float(t["value"]), True))
        else:
            cap = t.get("censored_at")
            if cap is None:
                cap = budget if budget is not None else 0.0
            events.append((float(cap), False))
    n = len(events)
    if n == 0:
        return {"points": [], "n_runs": 0, "n_reached": 0, "n_censored": 0,
                "censored_fraction": None, "target_j": target_j, "x_key": x_key,
                "budget": budget, "ecdf_is_lower_bound": True}
    xs = sorted({t for t, _ in events})
    points: list[list[float]] = []
    prev: float | None = None
    for x in xs:
        frac = sum(1 for t, reached in events if reached and t <= x) / n
        if frac != prev:
            points.append([x, frac])
            prev = frac
    return {
        "points": points,
        "n_runs": n,
        "n_reached": n_reached,
        "n_censored": n - n_reached,
        "censored_fraction": (n - n_reached) / n,
        "target_j": float(target_j),
        "x_key": x_key,
        "budget": budget,
        "ecdf_is_lower_bound": True,
        "note": ("censored runs are placed at their last observed budget but are "
                 "not counted as reached; the fraction is a lower bound"),
    }


def expected_runtime(curves: list[list[dict]], target_j: float,
                     x_key: str = "n", budget=None) -> dict:
    """Right-censored expected runtime to target per successful run (ERT).

    ``ERT = sum(cost_i) / n_success`` where a censored run contributes at least
    its last observed budget.  That makes the estimate a lower bound on the true
    ERT; the assumption is reported with the number.
    """
    times: list[float] = []
    n_success = 0
    for curve in curves:
        t = time_to_target(curve, target_j, x_key=x_key, budget=budget)
        if t["reached"]:
            n_success += 1
            times.append(float(t["value"]))
        else:
            cap = t.get("censored_at")
            if cap is None:
                cap = budget if budget is not None else 0.0
            times.append(float(cap))
    n = len(times)
    if n_success == 0:
        return {"ert": None, "status": "no_success", "n_runs": n, "n_success": 0,
                "n_censored": n, "target_j": target_j, "x_key": x_key,
                "budget": budget}
    return {
        "ert": sum(times) / n_success,
        "status": "ok",
        "n_runs": n,
        "n_success": n_success,
        "n_censored": n - n_success,
        "target_j": target_j,
        "x_key": x_key,
        "budget": budget,
        "ert_is_lower_bound": True,
        "assumption": ("censored runs cost at least their last observed budget; "
                       "ERT = sum(cost)/n_success, so the value is a lower bound"),
    }


def beats_rule(median_a: float, spread_a: float, median_b: float, spread_b: float,
               n_runs: int) -> str:
    """The 2026-10-23 rule: A beats B only when medians differ by more than both spreads.

    >= 5 runs -> a verdict; 3-4 (and 1-2, seed_variance only) -> 'indicative' when the
    rule holds (schema.md's seed_variance example). ``ab_compare`` floors < 3 to
    'no-verdict' itself before calling this, per its own schema section."""
    diff = abs(median_a - median_b)
    if not (diff > spread_a and diff > spread_b):
        return "no-verdict"
    if n_runs >= 5:
        return "a-beats-b" if median_a < median_b else "b-beats-a"
    return "indicative"


# ------------------------------------------------------------------ output


def chart_or_none(name: str):
    """Import pyplot on demand; a missing matplotlib degrades to 'no chart', never a failure."""
    try:
        import matplotlib.pyplot as plt  # type: ignore

        return plt
    except Exception:  # noqa: BLE001 - charts are best-effort
        print(f"warning: matplotlib unavailable, skipping chart {name}", file=sys.stderr)
        return None


def jsonable(obj) -> Any:
    """Deep-copy a payload into plain JSON types: numpy scalars -> Python, non-finite -> None
    (schema.md: every report is written with allow_nan=False and non-finite floats are null)."""
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        return v if math.isfinite(v) else None
    return obj


def write_report(out_dir: Path, tool: str, payload: dict, md: str,
                 charts: "dict[str, Callable[[object], object]] | None" = None) -> dict:
    """Write ``<tool>.json`` + ``<tool>.md`` (+ PNG charts) into ``out_dir``; return paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(jsonable(payload), tool=tool, generated_utc=utc_now())
    jpath = out_dir / f"{tool}.json"
    jpath.write_text(json.dumps(payload, indent=1, allow_nan=False, default=str),
                     encoding="utf-8")
    (out_dir / f"{tool}.md").write_text(md, encoding="utf-8")
    written = {"json": str(jpath), "md": str(out_dir / f"{tool}.md")}
    for fname, fn in (charts or {}).items():
        plt = chart_or_none(fname)
        if plt is None:
            continue
        try:
            fig = fn(plt)
            if fig is None:
                continue
            fig.savefig(out_dir / fname, dpi=120)  # type: ignore[union-attr]
            plt.close(fig)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001 - charts are best-effort, the JSON is the contract
            print(f"warning: chart {fname} failed ({type(exc).__name__}: {exc})", file=sys.stderr)
            plt.close("all")
            continue
        written[fname] = str(out_dir / fname)
    return written


def add_out_arg(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--out", required=True,
                    help="output dir for <name>.json/.md and PNG charts (never runs/)")


def fail(msg: str) -> "SystemExit":
    print(f"ERROR: {msg}", file=sys.stderr)
    return SystemExit(2)
