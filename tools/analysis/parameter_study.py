"""M1 parameter study report for the frozen ATH v4 candidate (S4, bo-study-v1.1).

This is the owner-facing **parameter_study.json / parameter_study.md** artifact frozen in
``PARENT_M0_FREEZE.md`` section 8.  It is an *analysis report*, not an optimizer:

* the task identity is resolved through ``hornlab_search.objective.replay.load_brief_context``
  (never an inline YAML target / weight copy);
* the cohort is the native-only ``native__ath_core_v4`` cohort.  The R0 pilot artifact supplies
  the scored/parity counts; the catalog supplies honest geometry/solve/apparatus counts.  Missing
  ``run_id``/``experiment_id`` is reported as ``insufficient_evidence`` for independence;
* the controls are the B2 ``parameter_activity`` ledger entries (read from its JSON, never
  re-derived here);
* 3-5 actual selectable designs are chosen from the scored rows by a deterministic recorded rule
  (lowest frozen J seed + maximin diversity in the active normalized space);
* every selected design carries params, canonical sampled geometry descriptors (through B2's
  ``geometry_effects`` module / installed mesher), a measured stored-array band summary, the exact
  frozen-J decomposition, the three replay identities and (shard, row) provenance;
* effects/interactions use the spec's ExtraTrees diagnostic over the native cohort.  They are
  **descriptive/diagnostic** because the cohort is below the 100-unique-observations/five-group
  screening policy and has no recorded independent experiment groups.  No recommendation is made
  when held-out validation fails to beat the training-mean baseline.

Offline only: no BEM, GPU, mesh build, dataset writer, cache write or search/default change.  Rows
are read through plain file reads and replayed through the canonical R0 adapter.  Output is
written only under ``--out``.

Usage::

    .venv\\Scripts\\python.exe tools\\analysis\\parameter_study.py \\
        --pilot scratch\\bo_m0\\r0\\offline_scores_native\\offline_scores.json \\
        --catalog scratch\\bo_m0\\s0\\catalog\\catalog.csv \\
        --activity scratch\\bo_m0\\b2\\activity\\parameter_activity.json \\
        --out scratch\\bo_m0\\s4\\parameter_study
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_DIR = Path(__file__).resolve().parent
for _p in (str(REPO_ROOT), str(ANALYSIS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _common import (REPO, add_out_arg, fail, jsonable, read_json, spearman,  # noqa: E402
                     utc_now, write_report)
from hornlab_search.objective import replay  # noqa: E402
from hornlab_search.types import Design  # noqa: E402

TOOL = "parameter_study"
SCHEMA_VERSION = 1
PROTOCOL = "bo-study-v1.1"
NATIVE_CONFIG = "native__ath_core_v4"

DEFAULT_CONFIG = (REPO / "examples" / "typologies" / "campaign_2026-10-26_v4" /
                  "native__ath_core_v4.yaml")
DEFAULT_BRIEF = (REPO / "examples" / "briefs" / "campaign_2026-10-26_v4" /
                 "native_ath_core_2in_v4.yaml")
DEFAULT_PILOT = REPO / "scratch" / "bo_m0" / "r0" / "offline_scores_native_full" / \
    "offline_scores.json"
DEFAULT_CATALOG = REPO / "scratch" / "bo_m0" / "s0" / "catalog" / "catalog.csv"
DEFAULT_ACTIVITY = REPO / "scratch" / "bo_m0" / "b2" / "activity" / "parameter_activity.json"
DEFAULT_DATASET = REPO / "dataset"

SOURCE_CAVEAT_HZ = 3957.0
ANALYSIS_SEED = 20261112
MIN_DESIGNS = 3
MAX_DESIGNS = 5
ETF_PARAMS = {
    "n_estimators": 256,
    "min_samples_leaf": 5,
    "max_features": 1.0,
    "n_jobs": 1,
    "random_state": ANALYSIS_SEED,
}
#: Prespecified finite model steps (NOT derivatives).
INTERACTION_STEPS = (0.025, 0.05, 0.10)
INTERACTION_ANCHORS = 20
INTERACTION_MIN_SUPPORTED = 5
PERMUTATION_REPEATS = 10
HOLDOUT_FOLDS = 5
MIN_EFFECT_ROWS = 16
MIN_CURVE_UNIQUE = 10
BAND_EDGES_HZ = (300.0, 1000.0, 2500.0, 3957.0, 5500.0, 8000.0)

#: Objective v4 terms (terms dict is already normalized by tolerance; see scalar_v4).
V4_WEIGHTED_KEYS = ("cov", "rip", "di", "dislope", "flat", "load", "distd", "diag")
_EFFECT_OUTPUTS = (
    ("j", "frozen objective J", "dimensionless"),
    ("bw_h_mean_deg", "band-mean H coverage", "deg"),
    ("bw_v_mean_deg", "band-mean V coverage", "deg"),
    ("di_mean_db", "band-mean directivity index", "dB"),
    ("di_slope_db_per_dec", "DI slope", "dB/decade"),
    ("ripple_mean_db", "band-mean ripple", "dB"),
    ("flatness_db", "on-axis flatness", "dB"),
    ("spdi_mean_db", "band-mean sound-power DI", "dB"),
)


# ---------------------------------------------------------------------------- small helpers


def _finite(value) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _rel(path) -> str:
    try:
        return Path(path).resolve().relative_to(REPO).as_posix()
    except (OSError, ValueError):
        return str(path)


def _hash_order(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (float(r["j"]), str(r.get("design_hash") or ""),
                                       int(r["provenance"]["shard"]),
                                       int(r["provenance"]["row"])))


def _catalog_native_stats(catalog_path) -> dict:
    """Honest native-only catalog counts (never invents a run/experiment identity)."""
    path = Path(catalog_path)
    if not path.is_file():
        return {"status": "unavailable", "path": str(path)}
    rows: list[dict] = []
    with open(path, encoding="utf-8", newline="") as fh:
        for rec in csv.DictReader(fh):
            if rec.get("config_name") == NATIVE_CONFIG:
                rows.append(rec)
    ok = [r for r in rows if str(r.get("ok")) == "True"]
    failed = [r for r in rows if str(r.get("ok")) != "True"]

    def uniq(items, key):
        return len({r.get(key) for r in items if r.get(key)})

    return {
        "status": "ok",
        "path": _rel(path),
        "native_rows": len(rows),
        "ok_rows": len(ok),
        "failed_rows": len(failed),
        "failure_kinds": dict(sorted(Counter(r.get("failure_kind") for r in failed
                                             if r.get("failure_kind")).items())),
        "unique_geometries": uniq(ok, "geometry_id"),
        "unique_design_hashes": uniq(ok, "design_hash"),
        "unique_physical_solves": uniq(ok, "physical_solve_id"),
        "fidelities": dict(sorted(Counter(r.get("fidelity") for r in ok
                                          if r.get("fidelity")).items())),
        "backends": dict(sorted(Counter(r.get("backend") for r in ok
                                        if r.get("backend")).items())),
        "briefs": dict(sorted(Counter(r.get("brief") for r in ok
                                      if r.get("brief")).items())),
        "brief_hashes": dict(sorted(Counter(r.get("brief_hash") for r in ok
                                            if r.get("brief_hash")).items())),
        "objective_versions": dict(sorted(Counter(str(r.get("objective_version")) for r in ok
                                                  if r.get("objective_version")).items())),
        "score_identities": uniq(ok, "score_identity"),
        "completeness": dict(sorted(Counter(r.get("completeness") for r in ok
                                            if r.get("completeness")).items())),
        "run_id_present": sum(1 for r in ok if r.get("run_id")),
        "experiment_id_present": sum(1 for r in ok if r.get("experiment_id")),
        "unknowns": dict(sorted(Counter(
            token for r in ok for token in (r.get("unknowns") or "").split(",") if token).items())),
    }


def _task_identity(brief: replay.Brief, config_path) -> dict:
    block = dict(brief.objective_block or {})
    return {
        "config": _rel(config_path),
        "brief_name": brief.name,
        "brief_hash": brief.brief_hash(),
        "brief_path": _rel(brief.source_path) if brief.source_path else None,
        "objective_version": int(brief.objective_version),
        "resolved_target": jsonable(dataclasses.asdict(brief.target)),
        "weights": jsonable(dict(brief.weights)),
        "tolerances": jsonable(dict(block.get("tolerances") or {})),
        "cov_narrow_ratio": block.get("cov_narrow_ratio"),
        "cov_below_f0": block.get("cov_below_f0"),
        "diag_reference": block.get("diag_reference"),
        "resolution_source": "hornlab_search.objective.replay.load_brief_context "
                             "(resolved config brief; no inline YAML target)",
    }


# ---------------------------------------------------------------------------- cohort replay


def _read_npz(dataset_root, shard: int, row: int) -> dict | None:
    p = Path(dataset_root) / f"shard-{int(shard):04d}" / f"rec-{int(row):04d}.npz"
    if not p.is_file():
        return None
    try:
        with np.load(p, allow_pickle=False) as z:
            return {k: z[k] for k in z.files}
    except Exception:  # noqa: BLE001 - a corrupt array file is an honest exclusion
        return None


def _physical_outputs(meta: dict, arrays: dict | None) -> dict:
    """Measured scalar outputs for the diagnostic model (stored scalars, array fallback)."""
    scalars = dict(meta.get("metrics_scalars") or {})
    out = {name: _finite(scalars.get(name)) for name, _label, _unit in _EFFECT_OUTPUTS[1:]}
    if arrays and any(v is None for v in out.values()):
        f = np.asarray(arrays.get("freqs_hz"), dtype=float) if arrays.get("freqs_hz") is not None \
            else None
        if f is not None and f.size:
            band = (f >= 300.0) & (f <= 8000.0)
            if band.any():
                def mean_of(name):
                    arr = arrays.get(name)
                    if arr is None:
                        return None
                    vals = np.asarray(arr, dtype=float)[band]
                    vals = vals[np.isfinite(vals)]
                    return float(vals.mean()) if vals.size else None

                fallback = {
                    "bw_h_mean_deg": mean_of("bw_h_deg"),
                    "bw_v_mean_deg": mean_of("bw_v_deg"),
                    "di_mean_db": mean_of("di_db"),
                    "ripple_mean_db": mean_of("ripple_h_db"),
                    "flatness_db": mean_of("on_axis_db"),
                }
                for k, v in fallback.items():
                    if out.get(k) is None:
                        out[k] = v
    return out


def _catalog_index_rows(catalog_path) -> dict[tuple[int, int], dict]:
    """Map ``(shard,row)`` -> native catalog record (read-only provenance join)."""
    path = Path(catalog_path)
    if not path.is_file():
        return {}
    out: dict[tuple[int, int], dict] = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for rec in csv.DictReader(fh):
            if rec.get("config_name") != NATIVE_CONFIG:
                continue
            try:
                key = (int(rec.get("shard_index") or rec.get("shard")),
                       int(rec.get("row")))
            except (TypeError, ValueError):
                continue
            out[key] = rec
    return out


def pilot_row_index(pilot: dict) -> dict[tuple[int, int], dict]:
    """Index the full R0 artifact's per-row join fields by ``(shard,row)``.

    The full artifact exposes all scored rows (the display artifact caps ``rows`` at 50); these
    are the live per-row J/terms/identity values, so the report reuses them instead of inventing
    a second table.
    """
    out: dict[tuple[int, int], dict] = {}
    for row in (pilot or {}).get("rows") or []:
        try:
            key = (int(row["shard"]), int(row["row"]))
        except (KeyError, TypeError, ValueError):
            continue
        out[key] = row
    return out


def load_replay_rows(dataset_root, candidates, brief: replay.Brief, *,
                     catalog_rows: dict | None = None,
                     pilot_rows: dict | None = None,
                     keep_arrays_for: set[tuple[int, int]] | None = None) -> tuple[list[dict], dict]:
    """Replay ``candidates`` through the canonical R0 adapter; join the full artifact rows."""
    keep_arrays_for = keep_arrays_for or set()
    catalog_rows = catalog_rows or {}
    pilot_rows = pilot_rows or {}
    rows: list[dict] = []
    excluded: Counter[str] = Counter()
    joined = 0
    join_mismatch = 0
    max_join_delta: float | None = None
    for shard, row, meta in candidates:
        arrays = _read_npz(dataset_root, shard, row)
        if arrays is None:
            excluded["missing_or_unreadable_npz"] += 1
            continue
        res = replay.replay_record(meta, arrays, brief=brief)
        if res.status != replay.STATUS_EXACT_COMPLETE or res.j is None:
            excluded[f"replay_status:{res.status}"] += 1
            for reason in res.reasons:
                excluded[f"reason:{reason.split(':', 1)[0]}"] += 1
            continue
        params = dict(meta.get("params") or {})
        if not params:
            excluded["missing_params"] += 1
            continue
        artifact = pilot_rows.get((int(shard), int(row)))
        artifact_j = _finite((artifact or {}).get("j"))
        if artifact is not None and artifact_j is not None:
            joined += 1
            delta = abs(float(res.j) - artifact_j)
            max_join_delta = delta if max_join_delta is None else max(max_join_delta, delta)
            if delta > 1e-9:
                join_mismatch += 1
        record = {
            "shard": int(shard),
            "row": int(row),
            "catalog": dict(catalog_rows.get((int(shard), int(row))) or {}),
            "params": params,
            "family": str(meta.get("family") or ""),
            "design_hash": (artifact or {}).get("design_hash") or res.design_hash
            or meta.get("design_hash"),
            # Use one internally consistent replay result; pilot differences remain diagnostics.
            "j": float(res.j),
            "terms": dict(res.terms or {}),
            "stored_j": res.stored_j,
            "parity_delta": res.parity_delta,
            "status": res.status,
            "reasons": list(res.reasons),
            "physical_id": res.physical_id,
            "metric_id": res.metric_id,
            "score_id": res.score_id,
            "objective_version": int(res.objective_version),
            "metric_source": res.metric_source,
            "target": res.target,
            "weights": dict(res.weights or {}),
            "diagnostics": dict(res.diagnostics or {}),
            "physical_outputs": _physical_outputs(meta, arrays),
            "pilot_join": artifact is not None,
            "pilot_join_delta": (abs(float(res.j) - artifact_j)
                                 if artifact is not None and artifact_j is not None else None),
            "meta": meta,
        }
        if (int(shard), int(row)) in keep_arrays_for:
            record["arrays"] = arrays
        rows.append(record)
    return rows, {
        "excluded": dict(sorted(excluded.items())),
        "pilot_join": {
            "artifact_rows_exposed": len(pilot_rows),
            "joined": joined,
            "mismatched_j": join_mismatch,
            "max_abs_join_delta": max_join_delta,
        },
    }


def load_candidates(dataset_root, catalog_path, limit: int = 200) -> tuple[list, dict]:
    """Reuse the R0 read-only scan to identify the native scored candidate rows."""
    import offline_scores as os

    catalog_index = os.load_catalog_index(catalog_path) if catalog_path else None
    scan = os.scan_dataset(dataset_root, catalog_index=catalog_index,
                           config_filter=NATIVE_CONFIG)
    candidates = scan["candidates"][:max(0, int(limit))]
    return candidates, scan["counters"]


# ---------------------------------------------------------------------------- design selection


def _normalized_features(rows: list[dict], active_keys, bounds, family: str):
    """Active [0,1]^d matrix + clipping ledger (historical clipping is never silently kept)."""
    from hornlab_search.design import families

    X = np.empty((len(rows), len(active_keys)), dtype=float)
    clipped: list[str] = []
    for i, row in enumerate(rows):
        for j, key in enumerate(active_keys):
            try:
                value = families.param_get(family, row["params"], key)
            except Exception:  # noqa: BLE001 - native params are flat; fall back to direct read
                value = row["params"].get(key)
            if value is None:
                clipped.append(f"missing:{key}")
                X[i, j] = np.nan
                continue
            u, was_clipped = bounds[key].to_unit(float(value))
            if was_clipped:
                clipped.append(f"clipped:{key}")
            X[i, j] = float(u)
    return X, clipped


def select_designs(rows: list[dict], active_keys, bounds, family: str, *,
                   max_designs: int = MAX_DESIGNS) -> tuple[list[dict], dict]:
    """Deterministic lowest-J + maximin spread rule.

    Seed = the lowest frozen-J scored design.  Remaining slots are filled from the better half
    (J <= median J) by maximin normalized Euclidean distance to the already-selected designs;
    ties break by lower J then design hash.  If the better half is exhausted, all rows are used.
    """
    valid = [r for r in rows if _finite(r.get("j")) is not None]
    if not valid:
        return [], {"rule": "lowest_j_plus_maximin_best_half_v1", "selected": 0}
    X, clipped = _normalized_features(valid, active_keys, bounds, family)
    good = np.all(np.isfinite(X), axis=1)
    valid = [r for r, ok in zip(valid, good) if ok]
    X = X[good]
    if len(valid) < MIN_DESIGNS:
        return [], {"rule": "lowest_j_plus_maximin_best_half_v1",
                    "selected": len(valid), "reason": "fewer_than_min_designs"}
    order = np.argsort(np.asarray([r["j"] for r in valid], dtype=float), kind="stable")
    ordered = [valid[i] for i in order]
    Xord = X[order]
    median_j = float(np.median([r["j"] for r in valid]))
    better = {i for i, r in enumerate(ordered) if float(r["j"]) <= median_j}

    selected_idx: list[int] = [0]
    reasons: dict[int, dict] = {
        0: {"role": "lowest_j_seed", "j_rank": 1,
            "min_distance": None}
    }
    while len(selected_idx) < min(int(max_designs), len(ordered)):
        chosen = None
        best_key = None
        better_unused = [i for i in better if i not in selected_idx]
        pool = better_unused if better_unused else [i for i in range(len(ordered))
                                                    if i not in selected_idx]
        for i in pool:
            if i in selected_idx:
                continue
            dists = np.linalg.norm(Xord[selected_idx] - Xord[i], axis=1)
            dmin = float(np.min(dists)) if dists.size else float("inf")
            key = (-dmin, float(ordered[i]["j"]), str(ordered[i].get("design_hash") or ""))
            if best_key is None or key < best_key:
                best_key = key
                chosen = i
        if chosen is None:
            break
        dists = np.linalg.norm(Xord[selected_idx] - Xord[chosen], axis=1)
        selected_idx.append(chosen)
        reasons[chosen] = {
            "role": "maximin_diversity",
            "j_rank": int(chosen) + 1,
            "min_distance": float(np.min(dists)),
        }
    selected = [ordered[i] for i in selected_idx]
    for i, row in enumerate(selected):
        row["selection_reason"] = reasons.get(selected_idx[i], {})
    return selected, {
        "rule": "lowest_j_plus_maximin_best_half_v1",
        "description": ("seed = lowest frozen-J scored design; remaining slots = maximin "
                        "normalized Euclidean spread within the better half (J <= median), "
                        "ties by lower J then design hash; deterministic"),
        "active_keys": list(active_keys),
        "n_candidates": len(valid),
        "median_j": median_j,
        "selected": len(selected),
        "clipped_features": sorted(set(clipped)),
    }


# ---------------------------------------------------------------------------- decomposition


def decompose_frozen_j(terms: dict, weights: dict, tolerances: dict) -> dict:
    """Exact v4 decomposition from the canonical replay terms.

    ``objective_v4`` returns *normalized* terms (raw / tolerance); the weighted total is
    ``sum(weight * normalized)``.  We expose raw = normalized * tolerance, normalized, weighted
    and the total; no scorer math is re-implemented.
    """
    normalized = {k: float(terms.get(k, 0.0)) for k in V4_WEIGHTED_KEYS}
    raw = {k: normalized[k] * float(tolerances.get(k, 1.0)) for k in V4_WEIGHTED_KEYS}
    weighted = {k: normalized[k] * float(weights.get(k, 0.0)) for k in V4_WEIGHTED_KEYS}
    total = float(sum(weighted.values()))
    return {
        "term_semantics": ("objective_v4 terms are normalized (raw/tolerance); "
                           "weighted = weight * normalized; total = sum(weighted)"),
        "raw": raw,
        "normalized": normalized,
        "weighted": weighted,
        "total": total,
        "total_matches_replay_j": bool(_finite(terms.get("total")) is not None
                                       and abs(float(terms.get("total")) - total) <= 1e-9),
        "extras": {k: terms.get(k) for k in ("n_in_band", "n_nan", "di_estimated", "penalty")
                   if k in terms},
    }


# ---------------------------------------------------------------------------- geometry / bands


def _geometry_descriptors(design: Design, config, *, resolution_mm: float = 12.0) -> dict:
    try:
        import geometry_effects as ge
    except Exception as exc:  # noqa: BLE001 - report the unavailable adapter honestly
        return {"status": "unavailable", "reason": f"geometry_effects import failed: {exc}"}
    try:
        sample = ge.sample_surface(design, config, resolution_mm=float(resolution_mm),
                                   check_convergence=False)
        return {
            "status": "ok",
            "units": sample.units,
            "descriptors": jsonable(sample.descriptors),
            "grid": jsonable(sample.grid),
            "provenance": jsonable(sample.provenance),
            "convergence": jsonable(sample.convergence),
            "sampling_note": ("canonical final-surface sample through the installed "
                              "hornlab_mesher API; sampling approximation, not a production "
                              "cache key or a mesh/BEM convergence claim"),
        }
    except Exception as exc:  # noqa: BLE001 - a refused/unsupported surface is reported
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


def _band_label(lo: float, hi: float) -> str:
    if hi <= SOURCE_CAVEAT_HZ:
        return "below_source_caveat"
    if lo >= SOURCE_CAVEAT_HZ:
        return "above_source_caveat_geometry_comparison"
    return "crosses_source_caveat"


def _axis_index(angles, target: float = 0.0) -> int | None:
    try:
        a = np.asarray(angles, dtype=float)
    except (TypeError, ValueError):
        return None
    if a.size == 0:
        return None
    return int(np.argmin(np.abs(a - float(target))))


def response_band_summary(arrays: dict, meta: dict) -> dict:
    """Measured stored-array summary over 300-8000 Hz, split at the ~3957 Hz source caveat."""
    if not arrays or arrays.get("freqs_hz") is None:
        return {"status": "unavailable", "reason": "no stored frequency array"}
    f = np.asarray(arrays["freqs_hz"], dtype=float)
    band = (f >= 300.0) & (f <= 8000.0)
    if not band.any():
        return {"status": "unavailable", "reason": "no stored bin inside 300-8000 Hz"}

    def col(name, angles_name=None, axis_target=0.0):
        arr = arrays.get(name)
        if arr is None:
            return None
        arr = np.asarray(arr, dtype=float)
        if arr.ndim == 2:
            idx = _axis_index(arrays.get(angles_name), axis_target) if angles_name else 0
            if idx is None or idx >= arr.shape[1]:
                return None
            arr = arr[:, idx]
        return arr

    series = {
        "on_axis_h_db": col("spl_h_db", "h_angles_deg", 0.0),
        "on_axis_v_db": col("spl_v_db", "v_angles_deg", 0.0),
        "di_db": col("di_db"),
        "bw_h_deg": col("bw_h_deg"),
        "bw_v_deg": col("bw_v_deg"),
        "ripple_h_db": col("ripple_h_db"),
        "ripple_v_db": col("ripple_v_db"),
    }
    bands = []
    for lo, hi in zip(BAND_EDGES_HZ[:-1], BAND_EDGES_HZ[1:]):
        mask = band & (f >= lo) & (f < hi if hi < BAND_EDGES_HZ[-1] else f <= hi)
        if not mask.any():
            continue
        stats = {}
        for name, arr in series.items():
            if arr is None or arr.shape[0] != f.size:
                continue
            vals = np.asarray(arr, dtype=float)[mask]
            vals = vals[np.isfinite(vals)]
            if vals.size:
                stats[name] = {"median": float(np.median(vals)),
                               "min": float(np.min(vals)), "max": float(np.max(vals)),
                               "n_finite": int(vals.size)}
        bands.append({
            "band_hz": [float(lo), float(hi)],
            "source_label": _band_label(float(lo), float(hi)),
            "n_stored_bins": int(mask.sum()),
            "stats": stats,
        })
    scalars = dict(meta.get("metrics_scalars") or {})
    f11 = _finite(scalars.get("f11_hz"))
    return {
        "status": "ok",
        "frequencies_hz": [float(v) for v in f[band]],
        "band_edges_hz": [float(v) for v in BAND_EDGES_HZ],
        "source_caveat_hz": SOURCE_CAVEAT_HZ,
        "stored_f11_hz": f11,
        "bands": bands,
        "note": ("measured stored arrays only; the 2-inch uniform-piston source caveat "
                 "f11 ~= 3957 Hz means above-caveat bands are geometry comparisons under "
                 "that excitation, not a universal validity boundary"),
    }


# ---------------------------------------------------------------------------- effects


def _correlated_groups(X: np.ndarray, keys, threshold: float = 0.8) -> list[list[str]]:
    d = X.shape[1]
    parent = list(range(d))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    if d > 1:
        try:
            corr = np.corrcoef(X, rowvar=False)
            for i in range(d):
                for j in range(i + 1, d):
                    if math.isfinite(float(corr[i, j])) and abs(float(corr[i, j])) >= threshold:
                        union(i, j)
        except Exception:  # noqa: BLE001 - degenerate/constant features simply stay singletons
            pass
    known = [("s1", "s2"), ("n", "q", "s"),
             ("morph_width_mm", "morph_height_mm", "morph_corner_mm", "morph_rate",
              "morph_fixed")]
    for group in known:
        idx = [keys.index(k) for k in group if k in keys]
        for a, b in zip(idx, idx[1:]):
            union(a, b)
    groups: dict[int, list[str]] = {}
    for i, key in enumerate(keys):
        groups.setdefault(find(i), []).append(key)
    return [sorted(v) for v in groups.values()]


def _r2(y, pred) -> float | None:
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    if y.size < 2:
        return None
    den = float(np.sum((y - y.mean()) ** 2))
    if den <= 0.0:
        return None
    return float(1.0 - np.sum((y - pred) ** 2) / den)


def fit_effects(rows: list[dict], active_keys, bounds, family: str, *,
                analysis_seed: int = ANALYSIS_SEED) -> dict:
    """ExtraTrees descriptive diagnostics for frozen J and available measured outputs."""
    try:
        from sklearn.ensemble import ExtraTreesRegressor
        from sklearn.model_selection import KFold
    except Exception as exc:  # noqa: BLE001 - report unavailable, never fabricate a model
        return {"status": "unavailable", "reason": f"sklearn unavailable: {exc}"}

    valid = [r for r in rows if _finite(r.get("j")) is not None]
    X, clipped = _normalized_features(valid, active_keys, bounds, family)
    good = np.all(np.isfinite(X), axis=1)
    valid = [r for r, ok in zip(valid, good) if ok]
    X = X[good]
    if len(valid) < MIN_EFFECT_ROWS:
        return {"status": "insufficient_support",
                "reason_code": "fewer_than_min_effect_rows",
                "n_rows": len(valid), "min_rows": MIN_EFFECT_ROWS}

    y_all = {
        "j": np.asarray([float(r["j"]) for r in valid], dtype=float),
    }
    for name, _label, _unit in _EFFECT_OUTPUTS[1:]:
        y_all[name] = np.asarray([_finite((r.get("physical_outputs") or {}).get(name))
                                  if _finite((r.get("physical_outputs") or {}).get(name))
                                  is not None else np.nan for r in valid], dtype=float)

    et_params = {**ETF_PARAMS, "random_state": int(analysis_seed)}
    n_splits = min(HOLDOUT_FOLDS, max(2, len(valid) // 4))
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=int(analysis_seed))
    outputs: dict[str, dict] = {}
    models: dict[str, Any] = {}
    oof: dict[str, np.ndarray] = {}
    importances: dict[str, Any] = {}

    for name, label, unit in _EFFECT_OUTPUTS:
        y = y_all[name]
        mask = np.isfinite(y)
        n = int(mask.sum())
        base = {"label": label, "unit": unit, "n_observations": n,
                "model": "ExtraTreesRegressor" if n >= MIN_EFFECT_ROWS else None}
        if n < MIN_EFFECT_ROWS:
            base.update({"status": "insufficient_support",
                         "reason_code": "fewer_than_min_effect_rows"})
            outputs[name] = base
            continue
        if float(np.var(y[mask])) <= 1e-12:
            base.update({"status": "flat_response", "reason_code": "zero_training_variance"})
            outputs[name] = base
            continue
        yv = y[mask]
        Xv = X[mask]
        pred_oof = np.full(yv.size, np.nan)
        fold_rows = []
        fold_models = []
        # Build fold indices after output-specific missing values are removed.
        for tr, te in kf.split(Xv):
            if tr.size < 2 or te.size < 1:
                continue
            model = ExtraTreesRegressor(**et_params)
            model.fit(Xv[tr], yv[tr])
            pred = np.asarray(model.predict(Xv[te]), dtype=float)
            pred_oof[te] = pred
            baseline = float(np.mean(yv[tr]))
            rmse_model = float(np.sqrt(np.mean((yv[te] - pred) ** 2)))
            rmse_base = float(np.sqrt(np.mean((yv[te] - baseline) ** 2)))
            fold_rows.append({"n_train": int(tr.size), "n_test": int(te.size),
                              "rmse_model": rmse_model, "rmse_training_mean_baseline": rmse_base})
            fold_models.append((model, tr, te))
        ok = np.isfinite(pred_oof)
        r2_oof = _r2(yv[ok], pred_oof[ok]) if ok.any() else None
        rmse_model_mean = float(np.mean([f["rmse_model"] for f in fold_rows])) \
            if fold_rows else None
        rmse_base_mean = float(np.mean([f["rmse_training_mean_baseline"] for f in fold_rows])) \
            if fold_rows else None
        beats = bool(rmse_model_mean is not None and rmse_base_mean is not None
                     and rmse_model_mean < rmse_base_mean and r2_oof is not None and r2_oof > 0.0)
        full = ExtraTreesRegressor(**et_params)
        full.fit(Xv, yv)
        models[name] = full
        oof[name] = pred_oof
        outputs[name] = {
            **base,
            "status": "ok",
            "r2_oof": r2_oof,
            "rmse_model_mean": rmse_model_mean,
            "rmse_training_mean_baseline_mean": rmse_base_mean,
            "beats_training_mean_baseline": beats,
            "folds": fold_rows,
        }

        if name == "j":
            groups = _correlated_groups(Xv, list(active_keys))
            group_stats: list[dict] = []
            rng = np.random.default_rng(int(analysis_seed))
            # Fold-level R2 loss; model fixed per fold, only the held-out block is permuted.
            base_fold_r2 = []
            for model, tr, te in fold_models:
                pred = np.asarray(model.predict(Xv[te]), dtype=float)
                base_fold_r2.append(_r2(yv[te], pred))
            for group in groups:
                idx = [list(active_keys).index(k) for k in group]
                losses = []
                for _repeat in range(PERMUTATION_REPEATS):
                    for k, (model, tr, te) in enumerate(fold_models):
                        Xp = Xv[te].copy()
                        perm = rng.permutation(Xp.shape[0])
                        Xp[:, idx] = Xp[perm][:, idx]
                        pred = np.asarray(model.predict(Xp), dtype=float)
                        r2p = _r2(yv[te], pred)
                        b = base_fold_r2[k]
                        if r2p is not None and b is not None:
                            losses.append(float(b - r2p))
                if losses:
                    group_stats.append({
                        "group": group,
                        "mean_heldout_r2_loss": float(np.mean(losses)),
                        "std_heldout_r2_loss": float(np.std(losses)),
                        "n": len(losses),
                    })
            group_stats.sort(key=lambda g: (-g["mean_heldout_r2_loss"], g["group"]))
            importances = {
                "method": ("held-out R2 loss under correlated-feature group permutation; "
                           "10 repeats; NOT delta-J and NOT causal"),
                "groups": group_stats,
            }

    j_out = outputs.get("j") or {}
    passed = bool(j_out.get("beats_training_mean_baseline"))
    return {
        "status": "produced",
        "model": "ExtraTreesRegressor",
        "model_params": dict(et_params),
        "analysis_seed": int(analysis_seed),
        "n_rows": len(valid),
        "n_features": len(active_keys),
        "active_keys": list(active_keys),
        "clipped_features": sorted(set(clipped)),
        "validation": {
            "method": f"deterministic {n_splits}-fold KFold over rows (shuffle, fixed seed)",
            "folds": n_splits,
            "baseline": "training-fold mean",
            "note": ("row-level folds, not independent experiments; group identity is not established "
                     "for this cohort"),
        },
        "screening_policy": {
            "min_unique_observations": 100,
            "min_independent_groups": 5,
            "independent_groups_known": None,
            "status": "below_policy_descriptive_diagnostic",
            "note": ("This implementation uses row-level folds and does not establish independent "
                     "experiment groups or stable supported effects; results are descriptive only."),
        },
        "outputs": outputs,
        "importance": importances,
        "heldout": {
            "frozen_j": j_out,
            "passed": passed,
            "recommendation_status": "suppressed_insufficient_independent_evidence",
            "reason_code": "independent_group_validation_and_effect_stability_not_established",
            "note": ("passed describes only the row-level predictive diagnostic; it does "
                     "not satisfy the independent-group or stable-effect recommendation gates"),
        },
        "_models": {k: v for k, v in models.items()},
        "_oof": {k: v.tolist() for k, v in oof.items()},
        "_X": X.tolist(),
        "_y": {k: v.tolist() for k, v in y_all.items()},
        "_valid_rows": valid,
    }


def effect_curves(rows: list[dict], active_keys, bounds, family: str,
                  effects: dict) -> dict:
    """Ten empirical quantile bins, merged until >=10 unique observations per bin."""
    if effects.get("status") == "produced" and effects.get("_X") is not None:
        X = np.asarray(effects["_X"], dtype=float)
        valid = list(effects.get("_valid_rows") or rows)
        if len(valid) != X.shape[0]:
            X, _clipped = _normalized_features(rows, active_keys, bounds, family)
            good = np.all(np.isfinite(X), axis=1)
            valid = [r for r, ok in zip(rows, good) if ok]
            X = X[good]
    else:
        X, _clipped = _normalized_features(rows, active_keys, bounds, family)
        good = np.all(np.isfinite(X), axis=1)
        valid = [r for r, ok in zip(rows, good) if ok]
        X = X[good]
    y = np.asarray([float(r["j"]) for r in valid], dtype=float)
    oof = effects.get("_oof", {}).get("j") if effects.get("status") == "produced" else None
    curves: dict[str, dict] = {}
    for j, key in enumerate(active_keys):
        x = X[:, j]
        unique = np.unique(x)
        if unique.size < 2:
            curves[key] = {"status": "not_estimable", "reason_code": "constant_feature",
                           "n": int(x.size), "n_unique": int(unique.size)}
            continue
        n_bins = min(10, int(unique.size))
        qs = np.quantile(x, np.linspace(0.0, 1.0, n_bins + 1))
        edges = np.unique(qs)
        if edges.size < 3:
            bins = [(0, x.size)]
        else:
            idx = np.clip(np.searchsorted(edges[1:-1], x, side="right"), 0, edges.size - 2)
            raw_bins: list[list[int]] = [[] for _ in range(edges.size - 1)]
            for i, b in enumerate(idx):
                raw_bins[int(b)].append(i)
            # Merge adjacent bins left-to-right until every bin has >=10 unique observations.
            merged: list[list[int]] = []
            for members in raw_bins:
                if not members:
                    continue
                if merged and len(np.unique(x[merged[-1]])) < MIN_CURVE_UNIQUE:
                    merged[-1].extend(members)
                else:
                    merged.append(list(members))
            if len(merged) > 1 and len(np.unique(x[merged[-1]])) < MIN_CURVE_UNIQUE:
                merged[-2].extend(merged[-1])
                merged.pop()
            bins = [(min(m), max(m)) for m in merged] if merged else [(0, x.size)]
        bin_rows = []
        for lo_i, hi_i in bins:
            members = np.arange(lo_i, hi_i + 1)
            if members.size == 0:
                continue
            xv = x[members]
            yv = y[members]
            raw_key = []
            for r in (valid[i] for i in members):
                try:
                    raw_key.append(float(r["params"][key]))
                except Exception:  # noqa: BLE001
                    raw_key.append(None)
            predicted = None
            if oof is not None:
                oof_arr = np.asarray(oof, dtype=float)
                if oof_arr.size == x.size:
                    pv = oof_arr[members]
                    pv = pv[np.isfinite(pv)]
                    if pv.size:
                        predicted = float(np.mean(pv))
            entry = {
                "x_norm_range": [float(np.min(xv)), float(np.max(xv))],
                "raw_value_range": [min(v for v in raw_key if v is not None)
                                    if any(v is not None for v in raw_key) else None,
                                    max(v for v in raw_key if v is not None)
                                    if any(v is not None for v in raw_key) else None],
                "n": int(members.size),
                "n_unique": int(np.unique(xv).size),
                "observed_j_mean": float(np.mean(yv)),
                "observed_j_median": float(np.median(yv)),
                "model_j_mean": predicted,
            }
            bin_rows.append(entry)
        curves[key] = {
            "status": "ok",
            "n": int(x.size),
            "n_unique": int(unique.size),
            "binning": ("empirical quantile bins merged until >=10 unique observations; "
                        "actual observations + model summary (descriptive, not causal)"),
            "bins": bin_rows,
            "points": [{"x_norm": float(xv),
                        "raw": float(r["params"][key])
                        if _finite(r["params"].get(key)) is not None else None,
                        "j": float(r["j"]),
                        "oof_j": (float(np.asarray(oof, dtype=float)[i])
                                  if oof is not None and np.asarray(oof).size == x.size
                                  and np.isfinite(float(np.asarray(oof, dtype=float)[i]))
                                  else None)}
                       for i, (xv, r) in enumerate(zip(x, valid))],
        }
    return {"status": "produced" if valid else "insufficient_support",
            "n_rows": len(valid), "features": curves,
            "note": ("effect curves are descriptive; model summary uses out-of-fold J "
                     "predictions; no causal label or automatic pinning")}


def interaction_diagnostic(rows: list[dict], active_keys, bounds, family: str,
                           effects: dict, *, analysis_seed: int = ANALYSIS_SEED) -> dict:
    """Finite-step model nonadditivity D_ij at 0.025/0.05/0.10 with support diagnostics."""
    if effects.get("status") != "produced":
        return {"status": "insufficient_support",
                "reason_code": effects.get("reason_code", "effects_unavailable"),
                "pairs": []}
    model = effects.get("_models", {}).get("j")
    if model is None:
        return {"status": "insufficient_support", "reason_code": "frozen_j_model_unavailable",
                "pairs": []}
    X = np.asarray(effects.get("_X"), dtype=float)
    y_j = np.asarray(effects.get("_y", {}).get("j"), dtype=float)
    if X.ndim != 2 or y_j.size != X.shape[0]:
        return {"status": "insufficient_support",
                "reason_code": "effect_feature_matrix_unavailable", "pairs": []}
    if X.shape[0] < 2 * len(active_keys):
        return {"status": "insufficient_support",
                "reason_code": "too_few_rows_for_interaction_anchors",
                "n_rows": int(X.shape[0]), "pairs": []}
    keys = list(active_keys)
    # Deterministic maximin anchors (lowest-J seed then spread); 20 anchors = eligibility screen.
    order = np.argsort(y_j, kind="stable")
    anchors = [int(order[0])] if order.size else []
    while len(anchors) < min(INTERACTION_ANCHORS, X.shape[0]):
        best_i, best_key = None, None
        for i in range(X.shape[0]):
            if i in anchors:
                continue
            dmin = float(np.min(np.linalg.norm(X[anchors] - X[i], axis=1)))
            key = (-dmin, i)
            if best_key is None or key < best_key:
                best_key, best_i = key, i
        if best_i is None:
            break
        anchors.append(best_i)
    # Training nearest-neighbour distance and the 95th percentile diagnostic cutoff.
    nn = np.full(X.shape[0], np.inf)
    for i in range(X.shape[0]):
        d = np.linalg.norm(X - X[i], axis=1)
        d[i] = np.inf
        if np.any(np.isfinite(d)):
            nn[i] = float(np.min(d))
    cutoff = float(np.percentile(nn[np.isfinite(nn)], 95)) if np.any(np.isfinite(nn)) else None

    pairs_out = []
    for a_i in range(len(keys)):
        for b_i in range(a_i + 1, len(keys)):
            ka, kb = keys[a_i], keys[b_i]
            steps = []
            for h in INTERACTION_STEPS:
                endpoint_blocks = []
                support = []
                boundary = 0
                base = np.arange(X.shape[1])
                for anchor in anchors:
                    x = X[anchor].copy()
                    pts = np.vstack([x,
                                     np.where(base == a_i, x + h, x),
                                     np.where(base == b_i, x + h, x),
                                     np.where((base == a_i) | (base == b_i), x + h, x)])
                    if np.any(pts < -1e-12) or np.any(pts > 1.0 + 1e-12):
                        boundary += 1
                        continue
                    pts = np.clip(pts, 0.0, 1.0)
                    endpoint_blocks.append(pts)
                    # 2D projected support around the anchor (diagnostic only).
                    other = np.arange(X.shape[0]) != anchor
                    d2 = np.linalg.norm(X[other][:, [a_i, b_i]] - x[[a_i, b_i]], axis=1)
                    nearest_2d = float(np.min(d2)) if d2.size else None
                    n_within_2d = int(np.sum(np.max(np.abs(X[other][:, [a_i, b_i]] - x[[a_i, b_i]]),
                                                   axis=1) <= h))
                    support.append({"nearest_2d": nearest_2d, "n_within_2d": n_within_2d})
                values = []
                if endpoint_blocks:
                    endpoints = np.vstack(endpoint_blocks)
                    preds = np.asarray(model.predict(endpoints), dtype=float).reshape(-1, 4)
                    try:
                        from scipy.spatial.distance import cdist

                        nn_to_train = np.min(cdist(endpoints, X), axis=1).reshape(-1, 4)
                    except Exception:  # noqa: BLE001 - small brute-force fallback
                        nn_to_train = np.vstack([
                            [np.min(np.linalg.norm(X - p, axis=1)) for p in block]
                            for block in endpoint_blocks])
                    for k, pred in enumerate(preds):
                        f0, fa, fb, fab = [float(v) for v in pred]
                        values.append(fab - fa - fb + f0)
                        nn_max = float(np.max(nn_to_train[k]))
                        support[k]["nn_max"] = nn_max
                        support[k]["supported"] = bool(
                            (cutoff is None or nn_max <= cutoff)
                            and int(support[k].get("n_within_2d") or 0) >= 1)
                else:
                    support = []
                all_vals = np.asarray(values, dtype=float)
                vals = all_vals[np.asarray([s["supported"] for s in support], dtype=bool)]
                n_supported = int(sum(1 for s in support if s["supported"]))
                stats = {
                    "step": float(h),
                    "n_evaluated": int(all_vals.size),
                    "n_supported": n_supported,
                    "n_boundary_excluded": int(boundary),
                    "median_abs_D": float(np.median(np.abs(vals))) if vals.size else None,
                    "mean_D": float(np.mean(vals)) if vals.size else None,
                    "sign_positive": int(np.sum(vals > 0.0)),
                    "sign_negative": int(np.sum(vals < 0.0)),
                    "sign_zero": int(np.sum(vals == 0.0)),
                }
                steps.append(stats)
            # Joint support and stability across independent-group fits are not established.
            # Even a sufficient number of geometric-neighbour diagnostics is not a certificate.
            status = "not_estimable"
            reason = ("insufficient_supported_anchors" if not any(
                step["n_supported"] >= INTERACTION_MIN_SUPPORTED for step in steps)
                else "independent_group_support_and_stability_not_established")
            pairs_out.append({
                "pair": [ka, kb],
                "status": status,
                "reason_code": reason,
                "steps": steps,
            })
    # No group-fold models are available: do not rank pairs by apparent step stability.
    stability = {}
    return {
        "status": "produced",
        "method": ("D_ij = f(x+h ei+h ej) - f(x+h ei) - f(x+h ej) + f(x); ExtraTrees finite "
                   "model changes at normalized steps 0.025/0.05/0.10"),
        "interpretation": ("local MODEL nonadditivity only; not a derivative, not a causal "
                           "acoustic interaction, not fANOVA and not a p-value"),
        "steps": list(INTERACTION_STEPS),
        "n_anchors": len(anchors),
        "nn_distance_95pct_cutoff": cutoff,
        "support_policy": {
            "supported_if": ("all four endpoint nearest-training distances <= 95th percentile "
                             "AND at least one other training design in the 2D +/-h projection"),
            "min_supported_anchors_per_step": INTERACTION_MIN_SUPPORTED,
            "boundary_anchors": "excluded explicitly per step; never clipped",
            "note": ("nearest-neighbour distance and 2D projected support are diagnostics, "
                     "not a joint-support certificate"),
        },
        "independent_group_coverage": {
            "n_groups": None,
            "status": "insufficient_evidence",
            "reason_code": "independent_group_coverage_not_established",
        },
        "pair_order_stability_spearman": stability,
        "pairs": pairs_out,
    }


# ---------------------------------------------------------------------------- payload


def build_payload(*, brief: replay.Brief, config, pilot: dict, catalog_stats: dict,
                  activity: dict, rows: list[dict], config_path,
                  dataset_root=None, catalog_rows: dict | None = None,
                  run_geometry: bool = True, resolution_mm: float = 12.0,
                  analysis_seed: int = ANALYSIS_SEED,
                  max_designs: int = MAX_DESIGNS) -> dict:
    """Assemble the frozen-schema payload (pure; the caller supplies loaded inputs)."""
    from hornlab_search.design.space import DesignSpace

    space = DesignSpace.from_config(config)
    full_keys = list(space.keys())
    projection = (activity or {}).get("active_projection") or {}
    active_keys = [k for k in (projection.get("active_keys") or full_keys) if k in space.bounds]
    if not active_keys:
        active_keys = full_keys
    bounds = space.bounds

    selected, selection = select_designs(rows, active_keys, bounds, config.family,
                                         max_designs=max_designs)
    selected_pairs = {(int(r["shard"]), int(r["row"])) for r in selected}
    # Ensure arrays for the selected designs (the loader may not have kept them).
    for r in selected:
        if "arrays" not in r:
            r["arrays"] = None
        if r.get("arrays") is None:
            r["arrays"] = _read_npz(DEFAULT_DATASET if "dataset_root" not in r else
                                    r["dataset_root"], r["shard"], r["row"]) or {}

    designs = []
    for r in selected:
        if r.get("arrays") is None and dataset_root is not None:
            r["arrays"] = _read_npz(dataset_root, r["shard"], r["row"]) or {}
        design = Design(str(r["family"] or config.family), dict(r["params"]))
        geometry = _geometry_descriptors(design, config, resolution_mm=resolution_mm) \
            if run_geometry else {"status": "skipped", "reason": "geometry sampling disabled"}
        catalog = r.get("catalog") or (catalog_rows or {}).get((int(r["shard"]), int(r["row"])), {})
        designs.append({
            "design_hash": r.get("design_hash"),
            "params": jsonable(dict(r["params"])),
            "geometry_descriptors": geometry,
            "response_bands_hz": response_band_summary(r.get("arrays") or {}, r.get("meta") or {}),
            "source_caveat_hz": SOURCE_CAVEAT_HZ,
            "score_terms": decompose_frozen_j(r.get("terms") or {}, r.get("weights") or {},
                                              (brief.objective_block or {}).get("tolerances") or {}),
            "identities": {
                "physical_id": r.get("physical_id"),
                "metric_id": r.get("metric_id"),
                "score_id": r.get("score_id"),
            },
            "provenance": {
                "shard": int(r["shard"]),
                "row": int(r["row"]),
                "dataset": "dataset",
                "design_hash": r.get("design_hash"),
                "mesh_hash": (r.get("meta") or {}).get("mesh_hash"),
                "solve_hash": (r.get("meta") or {}).get("solve_hash"),
                "config_name": catalog.get("config_name") or NATIVE_CONFIG,
                "fidelity": catalog.get("fidelity"),
                "backend": catalog.get("backend"),
                "geometry_id": catalog.get("geometry_id"),
                "physical_solve_id": catalog.get("physical_solve_id"),
                "run_id": catalog.get("run_id") or None,
                "experiment_id": catalog.get("experiment_id") or None,
                "independent_experiment_identity": "insufficient_evidence",
                "replay_status": r.get("status"),
            },
            "selection_reason": {
                **dict(r.get("selection_reason") or {}),
                "rule": selection.get("rule"),
                "frozen_j": float(r["j"]),
            },
        })

    effects = fit_effects(rows, active_keys, bounds, config.family,
                          analysis_seed=analysis_seed)
    curves = effect_curves(rows, active_keys, bounds, config.family, effects)
    interactions = interaction_diagnostic(rows, active_keys, bounds, config.family, effects,
                                          analysis_seed=analysis_seed)

    parity_pilot = dict((pilot or {}).get("parity") or {})
    replayed_parity = [abs(float(r["parity_delta"])) for r in rows
                       if r.get("parity_delta") is not None]
    recon_parity = {
        "n_replayed": len(rows),
        "n_compared": len(replayed_parity),
        "max_abs_delta": float(max(replayed_parity)) if replayed_parity else None,
        "within_1e-6": int(sum(1 for v in replayed_parity if v <= 1e-6)),
    }
    cohort_counts = dict((pilot or {}).get("counts") or {})
    cohort = {
        "rows": int(cohort_counts.get("scored") or parity_pilot.get("n") or len(rows)),
        "unique_geometries": int(catalog_stats.get("unique_geometries") or 0),
        "run_ids_missing": bool(catalog_stats.get("run_id_present", 0) == 0),
        "exclusions": {
            "catalog_failed_rows": int(catalog_stats.get("failed_rows") or 0),
            "catalog_failure_kinds": catalog_stats.get("failure_kinds") or {},
            "replay_exclusions": (pilot or {}).get("exclusions") or {},
            "reconstruction_exclusions": None,
            "config_unknown_rows": int(cohort_counts.get("config_unknown") or 0),
        },
        "generated_utc": utc_now(),
        "native_only": True,
        "config_name": NATIVE_CONFIG,
        "scored_exact_complete": int(cohort_counts.get("exact_complete") or 0),
        "parity_compared": int(parity_pilot.get("n_compared") or 0),
        "counts_note": ("Counts come from the supplied pilot and catalog snapshots; "
                        "reconstruction counts describe this report's replayed subset."),
        "native_catalog_ok_rows": int(catalog_stats.get("ok_rows") or 0),
        "native_catalog_fidelities": catalog_stats.get("fidelities") or {},
        "unique_physical_solves": int(catalog_stats.get("unique_physical_solves") or 0),
        "unique_design_hashes": int(catalog_stats.get("unique_design_hashes") or 0),
        "objective_versions": catalog_stats.get("objective_versions") or {},
        "briefs": catalog_stats.get("briefs") or {},
        "brief_hashes": catalog_stats.get("brief_hashes") or {},
        "score_identities": int(catalog_stats.get("score_identities") or 0),
        "experiment_identity": {
            "status": "insufficient_evidence",
            "run_ids_present": int(catalog_stats.get("run_id_present") or 0),
            "experiment_ids_present": int(catalog_stats.get("experiment_id_present") or 0),
            "reason_code": "independent_experiment_groups_not_established",
            "note": ("Group membership is not reconstructed from identifiers in this implementation; "
                     "repeated designs are not independent experiments."),
        },
        "reconstruction": {
            "n_replayed": len(rows),
            "n_selected_candidates": len(selected_pairs),
            "parity": recon_parity,
            "note": ("the R0 pilot artifact supplies the frozen cohort counts/parity; rows "
                     "were re-read and replayed through the canonical adapter only to attach "
                     "per-row features for this report"),
        },
    }

    controls = list((activity or {}).get("controls") or [])
    evidence = {
        "parity": {
            "pilot": parity_pilot,
            "reconstruction": recon_parity,
            "note": ("Parity compares stored and replayed J only where the replay reports a comparison; "
                     "uncompared rows are not parity successes."),
        },
        "heldout": effects.get("heldout") or {
            "status": "insufficient_support", "passed": False,
            "recommendation_status": "suppressed_no_model",
        },
        "support": ("The 100 unique observations and five independent groups are separate screens. "
                    "Design-level folds do not establish independent groups or stable supported "
                    "effects. Effects and interactions are descriptive, not recommendations."),
        "effects": {k: v for k, v in effects.items() if not k.startswith("_")},
        "effect_curves": curves,
        "interactions": interactions,
        "controls_projection": {
            "version": projection.get("version"),
            "full_keys": projection.get("full_keys") or full_keys,
            "active_keys": active_keys,
            "fixed_values": projection.get("fixed_values") or {},
            "counts": (activity or {}).get("counts") or {},
            "note": "B2 active-projection-v1 (morph_exponent held at its reference value)",
        },
        "design_selection": selection,
        "recommendation": {
            "status": "suppressed",
            "reason": ((effects.get("heldout") or {}).get("reason_code")
                       or "independent_group_validation_and_effect_stability_not_established"),
            "note": "no design is pinned; the report is an explanation artifact",
        },
    }

    limitations = [
        ("Source-piston caveat: the task uses a 2-inch uniform piston source with "
         "f11 ~= 3957 Hz; 300-8000 Hz results above the caveat are geometry comparisons "
         "under that excitation, not a universal validity boundary."),
        "Loading weight is 0.0: no loading, efficiency, distortion or maximum-SPL claims are made.",
        ("Independent experiment groups are not established by this report; row-level folds "
         "are not experimental replicates."),
        ("ExtraTrees is discontinuous: permutation importance is held-out R2 loss, never delta-J; "
         "interaction D_ij are finite model changes, not physical derivatives or causal "
         "acoustic interactions."),
        ("Exact normalized steps 0.025/0.05/0.10 are MODEL diagnostics only; unsupported or "
         "boundary-truncated pairs are reported as not_estimable, never clipped."),
        ("Geometry descriptors are a canonical sampled-surface approximation through the "
         "installed hornlab_mesher API; they are not production cache keys and not a mesh / "
         "BEM convergence proof."),
        ("Independent-group validation and stable supported effects are not established; historical "
         "search sampling is biased; effect curves and interaction rankings are descriptive."),
        ("J is not comparable across objective versions; this report is v4 only and the "
         "three replay identities are reported separately."),
    ]

    return {
        "tool": TOOL,
        "schema_version": SCHEMA_VERSION,
        "protocol": PROTOCOL,
        "task_identity": _task_identity(brief, config_path),
        "cohort": cohort,
        "controls": controls,
        "designs": designs,
        "evidence": evidence,
        "limitations": limitations,
    }


# ---------------------------------------------------------------------------- markdown


def _fmt(value, digits: int = 5) -> str:
    v = _finite(value)
    return "n/a" if v is None else f"{v:.{digits}g}"


def _markdown(p: dict) -> str:
    ti = p["task_identity"]
    c = p["cohort"]
    lines = [
        "# Parameter study (M1, bo-study-v1.1)",
        "",
        f"- task config: `{ti['config']}`",
        f"- resolved brief: `{ti['brief_name']}` (`{ti['brief_hash']}`)",
        f"- objective v{ti['objective_version']}; band "
        f"{ti['resolved_target'].get('band_lo_hz')}-{ti['resolved_target'].get('band_hi_hz')} Hz; "
        f"f0 {ti['resolved_target'].get('f0_hz')} Hz",
        f"- cohort: **{c['rows']}** scored rows, **{c['unique_geometries']}** unique geometries, "
        f"run ids missing: **{c['run_ids_missing']}**",
        f"- catalog native ok rows: **{c['native_catalog_ok_rows']}**, fidelities "
        f"`{c['native_catalog_fidelities']}`",
        f"- experiment identity: **{c['experiment_identity']['status']}**",
        "",
        "## Controls (B2 ledger)",
        "",
        "| key | category | resolved | range | evidence |",
        "|---|---|---:|---|---|",
    ]
    for ctrl in p["controls"]:
        b = ctrl.get("resolved", {}).get("bound") or {}
        val = ctrl.get("resolved", {}).get("value")
        rng = "-" if not b else f"{b.get('lo')} .. {b.get('hi')}" + (
            " (search)" if b.get("search") else " (fixed)")
        lines.append(f"| `{ctrl.get('key')}` | {ctrl.get('category')} | {_fmt(val)} | {rng} | "
                     f"{ctrl.get('evidence', {}).get('status')} |")
    lines += ["", "## Selected designs", "",
              f"Selection rule: {p['evidence']['design_selection'].get('description', '')}", "",
              "| design | J | cov | rip | di | dislope | distd | flat | diag | "
              "depth mm | mouth WxH mm | geometry |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for d in p["designs"]:
        t = d["score_terms"]["weighted"]
        g = d.get("geometry_descriptors", {})
        desc = g.get("descriptors") or {}
        lines.append(
            f"| `{d['design_hash']}` | {_fmt(d['score_terms']['total'])} | "
            f"{_fmt(t.get('cov'))} | {_fmt(t.get('rip'))} | {_fmt(t.get('di'))} | "
            f"{_fmt(t.get('dislope'))} | {_fmt(t.get('distd'))} | {_fmt(t.get('flat'))} | "
            f"{_fmt(t.get('diag'))} | {_fmt(desc.get('depth_mm'))} | "
            f"{_fmt(desc.get('mouth_width_mm'))}x{_fmt(desc.get('mouth_height_mm'))} | "
            f"{g.get('status')} |")
    ev = p["evidence"]
    par = ev["parity"]
    held = ev["heldout"]
    jh = held.get("frozen_j") or {}
    eff = ev["effects"]
    lines += ["", "## Evidence", "",
              f"- pilot parity: {par['pilot'].get('n_compared')}/{par['pilot'].get('n')} compared, "
              f"max |dJ| {_fmt(par['pilot'].get('max_abs_delta'))}",
              f"- reconstruction parity: {par['reconstruction'].get('n_compared')}/"
              f"{par['reconstruction'].get('n_replayed')} compared, max |dJ| "
              f"{_fmt(par['reconstruction'].get('max_abs_delta'))}",
              f"- row-level diagnostic held-out frozen J: R2_oof {_fmt(jh.get('r2_oof'))}, RMSE "
              f"{_fmt(jh.get('rmse_model_mean'))} vs training-mean baseline "
              f"{_fmt(jh.get('rmse_training_mean_baseline_mean'))}; passed "
              f"**{held.get('passed')}**",
              f"- recommendation: **{ev['recommendation']['status']}** "
              f"({ev['recommendation']['reason']})",
              f"- effects: **{eff.get('status')}**; screening policy "
              f"**{eff.get('screening_policy', {}).get('status')}**",
              f"- interactions: **{ev['interactions'].get('status')}** "
              f"({ev['interactions'].get('reason_code') or 'produced'})", ""]
    if eff.get("status") == "produced":
        lines += ["### Held-out model summary", "",
                  "| output | n | R2 oof | RMSE model | RMSE mean baseline | beats |",
                  "|---|---:|---:|---:|---:|---|"]
        for name, out in eff.get("outputs", {}).items():
            lines.append(f"| `{name}` | {out.get('n_observations')} | {_fmt(out.get('r2_oof'))} | "
                         f"{_fmt(out.get('rmse_model_mean'))} | "
                         f"{_fmt(out.get('rmse_training_mean_baseline_mean'))} | "
                         f"{out.get('beats_training_mean_baseline')} |")
        lines += ["", "### Held-out permutation importance (J; R2 loss, not dJ)", "",
                  "| group | mean R2 loss | std | n |", "|---|---:|---:|---:|"]
        for g in (eff.get("importance") or {}).get("groups", [])[:15]:
            lines.append(f"| `{', '.join(g['group'])}` | {_fmt(g['mean_heldout_r2_loss'], 4)} | "
                         f"{_fmt(g['std_heldout_r2_loss'], 3)} | {g['n']} |")
    it = ev["interactions"]
    lines += ["", "### Interaction diagnostic (finite model nonadditivity)", "",
              f"- status: **{it.get('status')}**; anchors: {it.get('n_anchors')}; "
              f"steps: {it.get('steps')}",
              f"- independent-group coverage: "
              f"**{(it.get('independent_group_coverage') or {}).get('status')}**",
              f"- step-order stability (Spearman): "
              f"`{it.get('pair_order_stability_spearman')}`",
              "- interpretation: local MODEL nonadditivity, not a derivative, causal acoustic "
              "interaction, fANOVA or p-value.", "",
              "| pair | status | median abs D @0.05 | supported anchors @0.05 |",
              "|---|---|---:|---:|"]
    # Show deterministic key order, not an unsupported interaction ranking.
    pairs = it.get("pairs") or []
    for pair in pairs[:10]:
        mid = (pair.get("steps") or [{}, {}, {}])[1]
        lines.append(f"| `{', '.join(pair.get('pair') or [])}` | {pair.get('status')} | "
                     f"{_fmt(mid.get('median_abs_D'), 4)} | {mid.get('n_supported')}/"
                     f"{mid.get('n_evaluated')} |")
    lines += ["", "## Limitations", ""]
    for item in p["limitations"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------- run / CLI


def run(*, pilot_path, catalog_path, activity_path, brief_path, config_path, dataset_root,
        out_dir, limit: int = 200, run_geometry: bool = True,
        resolution_mm: float = 12.0, analysis_seed: int = ANALYSIS_SEED,
        max_designs: int = MAX_DESIGNS, overwrite: bool = False) -> dict:
    from hornlab_search.config import load_config

    out = Path(out_dir)
    jpath = out / "parameter_study.json"
    mpath = out / "parameter_study.md"
    if not overwrite and (jpath.exists() or mpath.exists()):
        raise FileExistsError(
            f"{out}: parameter_study artifacts already exist; pass --overwrite to replace them")
    pilot = read_json(Path(pilot_path)) or {}
    activity = read_json(Path(activity_path)) or {}
    brief = replay.load_brief_context(brief_path)
    config = load_config(config_path)
    catalog_stats = _catalog_native_stats(catalog_path)
    catalog_rows = _catalog_index_rows(catalog_path)
    pilot_rows = pilot_row_index(pilot)
    candidates, scan_counters = load_candidates(dataset_root, catalog_path, limit=limit)

    # Replay inside the R0 zero-backend guard: this report must never solve.
    import offline_scores as os

    guard = os.BackendGuard()
    with guard:
        rows, replay_meta = load_replay_rows(dataset_root, candidates, brief,
                                             catalog_rows=catalog_rows,
                                             pilot_rows=pilot_rows)
    if guard.calls:
        raise RuntimeError(f"parameter_study: forbidden backend call(s): {guard.names}")

    payload = build_payload(brief=brief, config=config, pilot=pilot, catalog_stats=catalog_stats,
                            activity=activity, rows=rows, config_path=config_path,
                            dataset_root=dataset_root, catalog_rows=catalog_rows,
                            run_geometry=run_geometry, resolution_mm=resolution_mm,
                            analysis_seed=analysis_seed, max_designs=max_designs)
    payload["cohort"]["exclusions"]["reconstruction_exclusions"] = replay_meta["excluded"]
    payload["cohort"]["source_scan"] = scan_counters
    payload["cohort"]["backend_calls"] = int(guard.calls)
    payload["cohort"]["pilot_artifact"] = _rel(pilot_path)
    payload["cohort"]["pilot_join"] = replay_meta.get("pilot_join") or {}
    join = replay_meta.get("pilot_join") or {}
    if int(join.get("artifact_rows_exposed") or 0) > int(join.get("joined") or 0):
        payload["cohort"]["design_pool_note"] = (
            "design selection used the replayed subset because --limit is below the number of "
            "rows exposed by the full R0 artifact; run with the default --limit 200 for the "
            "full scored cohort")
    else:
        payload["cohort"]["design_pool_note"] = "design selection used the full exposed cohort"
    payload["evidence"]["parity"]["pilot_join"] = payload["cohort"]["pilot_join"]

    written = write_report(out, TOOL, payload, _markdown(payload))
    return {"payload": payload, "written": written, "backend_calls": int(guard.calls),
            "n_rows": len(rows), "n_designs": len(payload["designs"])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--pilot", type=Path, default=DEFAULT_PILOT,
                    help="R0 native offline_scores.json (cohort counts + parity)")
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG,
                    help="S0 catalog.csv (native config/geometry/solve provenance)")
    ap.add_argument("--activity", type=Path, default=DEFAULT_ACTIVITY,
                    help="B2 parameter_activity.json (embedded control ledger)")
    ap.add_argument("--brief", type=Path, default=DEFAULT_BRIEF,
                    help="resolved brief YAML (loaded through replay.load_brief_context)")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                    help="resolved native config YAML (bounds/seed for the DesignSpace)")
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET,
                    help="read-only dataset root (stored arrays; no writer)")
    ap.add_argument("--limit", type=int, default=200,
                    help="max native scored candidate rows replayed (default 200)")
    ap.add_argument("--resolution-mm", type=float, default=12.0,
                    help="geometry sampling resolution for selected designs (default 12)")
    ap.add_argument("--analysis-seed", type=int, default=ANALYSIS_SEED,
                    help=f"deterministic model/permutation seed (default {ANALYSIS_SEED})")
    ap.add_argument("--max-designs", type=int, default=MAX_DESIGNS,
                    help=f"selected designs, {MIN_DESIGNS}-{MAX_DESIGNS} (default {MAX_DESIGNS})")
    ap.add_argument("--no-geometry", action="store_true",
                    help="skip canonical surface sampling (the selected designs are still listed)")
    ap.add_argument("--overwrite", action="store_true",
                    help="replace an existing parameter_study.json/.md in --out")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    if not (MIN_DESIGNS <= int(args.max_designs) <= MAX_DESIGNS):
        raise fail(f"--max-designs must be in [{MIN_DESIGNS}, {MAX_DESIGNS}]")
    try:
        result = run(pilot_path=args.pilot, catalog_path=args.catalog,
                     activity_path=args.activity, brief_path=args.brief,
                     config_path=args.config, dataset_root=args.dataset, out_dir=args.out,
                     limit=int(args.limit), run_geometry=not args.no_geometry,
                     resolution_mm=float(args.resolution_mm),
                     analysis_seed=int(args.analysis_seed),
                     max_designs=int(args.max_designs), overwrite=bool(args.overwrite))
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        raise fail(f"parameter_study: {exc}") from exc
    p = result["payload"]
    held = p["evidence"]["heldout"]
    print(f"parameter_study OK: rows={p['cohort']['rows']} replayed={result['n_rows']} "
          f"designs={result['n_designs']} controls={len(p['controls'])} "
          f"backend_calls={result['backend_calls']}")
    print(f"selection={p['evidence']['design_selection']['rule']} "
          f"heldout_passed={held.get('passed')} "
          f"recommendation={p['evidence']['recommendation']['status']}")
    print(f"effects={p['evidence']['effects'].get('status')} "
          f"interactions={p['evidence']['interactions'].get('status')}")
    print(f"wrote {result['written']['json']} and {result['written']['md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

