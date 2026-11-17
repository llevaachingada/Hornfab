"""Read-only BO study view models for the local GUI.

This module is the only place that turns study artifacts and run rows into the small,
bounded JSON the study page consumes.  It never imports torch/botorch, never writes,
and never computes an acoustic score.  Derived numbers (best-so-far, coverage, rank
correlation, hypervolume, PCA coordinates) are explicit transformations of recorded
values and name their source in the returned view.

The study service and run readers are injected by the GUI server.  A failed view is a
tagged ``failed`` result, never an exception that takes down the study panel.
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import yaml

from .data_studies import MAX_BYTES, bounded_preview

MAX_POINTS = 200
MAX_SERIES = 120
MAX_TABLE = 60
MAX_RESULT_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
MAX_RUN_BYTES = 16 * 1024 * 1024
RUN_ID_RE = __import__("re").compile(r"^study-[0-9a-f]{16}$")
HASH_RE = __import__("re").compile(r"^[0-9a-f]{6,64}$")

#: Marker for a diagnostics/model field an older study never recorded.  Never a zero/fill.
NOT_RECORDED = "not recorded"
MODEL_SENSITIVITY_NOTE = "model sensitivity, not a proven physical effect"
SLICE_ANCHOR_NOTE = "other knobs held at incumbent"
ACQUISITION_NOTE = ("acquisition value is an optimizer ranking signal, not measured horn "
                    "quality and not a probability of success")
DESIGNATION_VALUES = ("exploration", "exploitation", "fallback")
STATUS_LABELS = {
    "analysis": "whether this view could be computed from recorded evidence",
    "artifact_validation": "artifact registration/validation status (not physical success)",
    "physical": "measured/verified/refused physical outcome (not artifact validation)",
}

PHASE_VIEWS = {
    "overview": ("run",),
    "data": ("run", "data_summary", "target_integrity", "design_space"),
    "explain": ("run", "calibration", "sensitivity", "design_space"),
    "propose": ("run", "proposal_explanation"),
    "execute": ("run", "convergence", "trust_region", "pareto"),
    "decide": ("run", "pareto", "verification"),
}


# --------------------------------------------------------------------------- small helpers


def _finite(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _int(value) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _view(status: str, reason: str | None = None, **data) -> dict:
    out = {"status": status}
    if reason:
        out["reason"] = reason
    out.update(data)
    return out


def _mapping(value) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _clip_text(value, limit: int = 500):
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _policy(study: Mapping) -> str:
    spec = study.get("spec") if isinstance(study, Mapping) else None
    policy = (spec or {}).get("policy") if isinstance(spec, Mapping) else None
    if isinstance(policy, Mapping):
        value = policy.get("proposal_policy") or policy.get("mode")
        if isinstance(value, str) and value:
            return value
    return "scalar"


def _objective_version(manifest: Mapping | None) -> int | None:
    if not isinstance(manifest, Mapping):
        return None
    task = manifest.get("task")
    if isinstance(task, Mapping):
        return _int(task.get("objective_version"))
    return None


def _active_keys(manifest: Mapping | None) -> list[str]:
    if not isinstance(manifest, Mapping):
        return []
    keys = manifest.get("active_keys")
    if not isinstance(keys, list):
        return []
    return [str(k) for k in keys if isinstance(k, str) and k][:64]


# --------------------------------------------------------------------------- evidence helpers


def _artifact_status(meta: Mapping | None) -> str:
    """Artifact registration/validation status, kept separate from physical success."""
    if not isinstance(meta, Mapping):
        return NOT_RECORDED
    return str(meta.get("status") or NOT_RECORDED)


def _status_kinds(analysis_status: str, *, artifact_status=None, physical: Any = NOT_RECORDED) -> dict:
    """Three distinct status dimensions; a validation ``unknown`` is not physical failure."""
    return {
        "analysis": analysis_status,
        "artifact_validation": artifact_status or NOT_RECORDED,
        "physical": physical,
        "labels": dict(STATUS_LABELS),
    }


def _physical_counts(observations: Iterable[Mapping]) -> dict:
    measured = verified = refused = 0
    for row in observations:
        result = _mapping(row.get("result"))
        kind = result.get("kind")
        outcome = str(result.get("outcome") or "")
        if outcome in ("cheap_refusal", "refused", "refusal"):
            refused += 1
            continue
        if result.get("eligible") is True and _finite(result.get("observed_j")) is not None:
            if kind == "verify":
                verified += 1
            elif kind == "screen":
                measured += 1
    if measured or verified or refused:
        parts = []
        if measured:
            parts.append(f"measured:{measured}")
        if verified:
            parts.append(f"verified:{verified}")
        if refused:
            parts.append(f"refused:{refused}")
        return {"measured": measured, "verified": verified, "refused": refused,
                "summary": ", ".join(parts)}
    return {"measured": 0, "verified": 0, "refused": 0, "summary": NOT_RECORDED}


def _model_provenance(meta, content, *, retrospective: bool, source: str) -> dict:
    """Which model revision/time supplied a prediction, and whether it was refit later."""
    content = _mapping(content)
    return {
        "source": source,
        "artifact_sha256": (meta or {}).get("sha256") if isinstance(meta, Mapping) else None,
        "artifact_revision": (meta or {}).get("revision") if isinstance(meta, Mapping) else None,
        "generated_utc": _clip_text(content.get("generated_utc"), 64),
        "model_revision": _int(content.get("model_revision") or content.get("revision")),
        "training_set_id": _clip_text(content.get("training_set_id"), 80),
        "model_policy": _clip_text(content.get("model_policy") or content.get("policy"), 80),
        "retrospective": bool(retrospective),
        "prediction_source": content.get("prediction_source"),
        "note": _clip_text(content.get("retrospective_note"), 500) if retrospective else None,
    }


def _designation(selection_reason, fallback) -> str:
    """Constraint: only exploration | exploitation | fallback are ever returned."""
    if fallback is True:
        return "fallback"
    text = str(selection_reason or "").lower()
    if "explor" in text or "maximin" in text:
        return "exploration"
    return "exploitation"


# --------------------------------------------------------------------------- artifact reads


def _artifact(service, study_id: str, kind: str, *, max_bytes: int = MAX_ARTIFACT_BYTES):
    """Return ``(content, metadata, reason)`` for a current-revision JSON artifact."""
    try:
        meta = service.get_artifact_metadata(study_id, kind)
    except Exception as exc:  # noqa: BLE001 - a registry error is a view state
        return None, {}, f"{kind} metadata unavailable: {type(exc).__name__}"
    if meta.get("status") != "available":
        return None, meta, f"{kind} artifact is {meta.get('status', 'unavailable')}"
    try:
        raw = service.store.read_artifact(meta["sha256"])
    except Exception as exc:  # noqa: BLE001
        return None, meta, f"{kind} bytes unavailable: {type(exc).__name__}"
    if len(raw) > max_bytes:
        return None, meta, f"{kind} artifact exceeds the bounded view size"
    try:
        content = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None, meta, f"{kind} artifact is not JSON"
    if not isinstance(content, dict):
        return None, meta, f"{kind} artifact is not an object"
    return content, meta, None


def _training_arrays(service, study_id: str):
    """Read the bounded training NPZ (X/J) without pickles; ``(dict, reason)``."""
    try:
        meta = service.get_artifact_metadata(study_id, "training")
    except Exception as exc:  # noqa: BLE001
        return None, f"training metadata unavailable: {type(exc).__name__}"
    if meta.get("status") != "available":
        return None, f"training artifact is {meta.get('status', 'unavailable')}"
    try:
        raw = service.store.read_artifact(meta["sha256"])
    except Exception as exc:  # noqa: BLE001
        return None, f"training bytes unavailable: {type(exc).__name__}"
    if len(raw) > 32 * 1024 * 1024:
        return None, "training artifact exceeds the bounded view size"
    try:
        with np.load(io.BytesIO(raw), allow_pickle=False) as arrays:
            X = np.asarray(arrays["X"], dtype=float)
            J = np.asarray(arrays["J"], dtype=float).reshape(-1)
    except Exception as exc:  # noqa: BLE001
        return None, f"training arrays unreadable: {type(exc).__name__}"
    if X.ndim != 2 or X.shape[0] != len(J) or not np.isfinite(X).all() or not np.isfinite(J).all():
        return None, "training arrays are not finite (X, J)"
    return {"X": X, "J": J}, None


def _package(service, study_id):
    return _artifact(service, study_id, "package", max_bytes=1_000_000)


def _results(service, study_id):
    return _artifact(service, study_id, "results", max_bytes=MAX_RESULT_BYTES)


def _proposal(service, study_id):
    return _artifact(service, study_id, "proposal", max_bytes=1_000_000)


def _model(service, study_id):
    return _artifact(service, study_id, "model", max_bytes=1_000_000)


def _manifest(service, study_id):
    return _artifact(service, study_id, "training_manifest", max_bytes=2_000_000)


def _pareto_metrics(service, study_id):
    return _artifact(service, study_id, "pareto_metrics", max_bytes=4_000_000)


def _diagnostics_artifact(service, study_id):
    """``(content_or_None, can_compute, metadata, reason)`` for the diagnostics artifact."""
    content, meta, reason = _artifact(service, study_id, "diagnostics", max_bytes=1_000_000)
    if isinstance(content, Mapping) and content.get("schema") == "study-model-diagnostics-v1" \
            and content.get("status", "ok") == "ok":
        return content, True, meta, None
    arrays, _why = _training_arrays(service, study_id)
    return None, arrays is not None, meta, reason


def _diagnostics(service, study_id):
    """The optional ``diagnostics`` artifact; ``(content_or_None, can_compute)``."""
    content, can_compute, _meta, _reason = _diagnostics_artifact(service, study_id)
    return content, can_compute


def _verification(service, study_id):
    return _artifact(service, study_id, "verification", max_bytes=1_000_000)


def _snapshot(service, study_id):
    return _artifact(service, study_id, "snapshot", max_bytes=1_000_000)


# --------------------------------------------------------------------------- run readers


def _run_id(service, study_id) -> str | None:
    meta = service.get_artifact_metadata(study_id, "package")
    if meta.get("status") != "available" or not HASH_RE.match(str(meta.get("sha256") or "")):
        return None
    return f"study-{meta['sha256'][:16]}"


def _run_paths(runs_root, service, study_id) -> dict:
    run_id = _run_id(service, study_id)
    if run_id is None or not RUN_ID_RE.match(run_id):
        return {"run_id": None, "run_dir": None, "verify_dir": None}
    run_dir = Path(runs_root) / run_id
    return {"run_id": run_id, "run_dir": run_dir, "verify_dir": run_dir / "verify"}


def _read_ndjson(path: Path, *, max_rows: int = 2000) -> list[dict]:
    try:
        size = path.stat().st_size
    except OSError:
        return []
    if size > MAX_RUN_BYTES:
        return []
    rows: list[dict] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if len(rows) >= max_rows:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return []
    return rows


def _screen_rows(run_dir: Path | None) -> list[dict]:
    """Screen rows for either a plain run (``search.ndjson``) or a study run
    (``screen/search.ndjson``)."""
    if not run_dir:
        return []
    base = Path(run_dir)
    for candidate in (base / "screen" / "search.ndjson", base / "search.ndjson"):
        if candidate.is_file():
            return _read_ndjson(candidate)
    return []


def _verify_rows(run_dir: Path | None) -> list[dict]:
    return _read_ndjson(Path(run_dir) / "verify" / "search.ndjson") if run_dir else []


def _resolve_arm_dir(runs_root, arm: Mapping) -> Path | None:
    """Resolve an arm to its run folder from an explicit run or a night summary."""
    if not isinstance(arm, Mapping):
        return None
    if isinstance(arm.get("run"), str) and arm["run"]:
        return Path(runs_root) / arm["run"]
    if arm.get("night") and arm.get("job"):
        summary_path = Path(runs_root) / "nights" / str(arm["night"]) / "summary.jsonl"
        for record in _read_ndjson(summary_path, max_rows=500):
            if record.get("id") != arm.get("job"):
                continue
            raw_dir = record.get("run_dir")
            if isinstance(raw_dir, str) and raw_dir:
                candidate = Path(raw_dir)
                if candidate.is_dir():
                    return candidate
            return None
    return None


def _observations(results: Mapping | None) -> list[Mapping]:
    if not isinstance(results, Mapping):
        return []
    rows = results.get("observations")
    if not isinstance(rows, list):
        return []
    return [row for row in rows[:MAX_POINTS * 2] if isinstance(row, Mapping)]


def _best_verify(rows: Iterable[Mapping]) -> float | None:
    values = [_finite(row.get("objective")) for row in rows if row.get("ok") is True]
    values = [value for value in values if value is not None]
    return min(values) if values else None


def _budget(service, study_id) -> dict:
    package, _meta, _reason = _package(service, study_id)
    if not isinstance(package, Mapping):
        return {}
    budget = package.get("budget")
    return {
        "budget": dict(budget) if isinstance(budget, Mapping) else None,
        "budget_profile": package.get("budget_profile"),
        "lane": package.get("lane"),
        "deadline": package.get("deadline"),
    }


def _eta(results: Mapping | None, budget: Mapping | None, run_dir: Path | None) -> dict | None:
    if not isinstance(budget, Mapping) or not isinstance(results, Mapping):
        return None
    progress = results.get("progress")
    if not isinstance(progress, Mapping):
        return None
    screen_rows = _screen_rows(run_dir)
    verify_rows = _verify_rows(run_dir)
    screen_seconds = [_finite((row.get("seconds") or {}).get("total"))
                      for row in screen_rows if row.get("ok") is True]
    verify_seconds = [_finite((row.get("seconds") or {}).get("total"))
                      for row in verify_rows if row.get("ok") is True]
    screen_seconds = [v for v in screen_seconds if v is not None]
    verify_seconds = [v for v in verify_seconds if v is not None]
    screen_left = max(0, int(budget.get("screen_calls", 0) or 0) - int(progress.get("screen_calls", 0) or 0))
    verify_left = max(0, int(budget.get("verify_calls", 0) or 0) - int(progress.get("verify_calls", 0) or 0))
    screen_median = float(np.median(screen_seconds)) if screen_seconds else None
    verify_median = float(np.median(verify_seconds)) if verify_seconds else None
    if screen_median is None and verify_median is None:
        return None
    return {
        "screen_remaining": screen_left,
        "verify_remaining": verify_left,
        "screen_seconds_each": screen_median,
        "verify_seconds_each": verify_median,
        "screen_seconds": (screen_left * screen_median) if screen_median is not None else None,
        "verify_seconds": (verify_left * verify_median) if verify_median is not None else None,
        "basis": ("median recorded solve seconds in this run" if screen_seconds or verify_seconds
                  else "no recorded solve durations"),
        "note": "Estimate from recorded solve times; verify is much heavier than screen.",
    }


# --------------------------------------------------------------------------- series/statistics


def _downsample(points: list[list], cap: int = MAX_SERIES) -> list[list]:
    if len(points) <= cap:
        return points
    step = max(1, math.ceil((len(points) - 1) / (cap - 1)))
    out = [points[0]]
    out.extend(points[1:-1:step])
    out.append(points[-1])
    return out[:cap]


def _bo_series(observations: Iterable[Mapping]) -> dict:
    points, solves, refusals, exploration, exploration_points, verify = [], [], [], [], [], []
    best: float | None = None
    screens = 0
    for index, row in enumerate(observations):
        candidate = row.get("candidate")
        if not isinstance(candidate, Mapping):
            candidate = {}
        result = row.get("result")
        if not isinstance(result, Mapping):
            result = {}
        kind = result.get("kind")
        j = _finite(result.get("observed_j"))
        if kind == "screen":
            screens += 1
            if result.get("outcome") == "cheap_refusal" or result.get("eligible") is False:
                refusals.append(index)
            if j is not None and result.get("eligible") is True:
                best = j if best is None else min(best, j)
                points.append([index, best])
                solves.append([index, j])
            if (candidate.get("selection_reason") in ("maximin_exploration", "exploration",
                                                      "exploration_fallback")
                    or candidate.get("exploration") is True):
                exploration.append(index)
                if j is not None:
                    exploration_points.append([index, j])
        elif kind in ("verify", "audit"):
            if j is not None:
                verify.append([index, j, kind])
    return {
        "points": _downsample(points),
        "solves": _downsample(solves),
        "refusals": refusals[:MAX_POINTS],
        "exploration": exploration[:MAX_POINTS],
        "exploration_points": exploration_points[:MAX_POINTS],
        "verify": verify[:MAX_POINTS],
        "screens": screens,
        "best_j": best,
    }


def _run_series(rows: Sequence[Mapping]) -> dict:
    points, solves, refusals = [], [], []
    best: float | None = None
    for index, row in enumerate(rows):
        j = _finite(row.get("objective"))
        if row.get("ok") is True and j is not None:
            best = j if best is None else min(best, j)
            points.append([index, best])
            solves.append([index, j])
        else:
            refusals.append(index)
    return {
        "points": _downsample(points),
        "solves": _downsample(solves),
        "refusals": refusals[:MAX_POINTS],
        "best_j": best,
        "screens": len(rows),
    }


def _screens_to_target(rows: Iterable[Mapping], target: float | None, *, field="objective") -> int | None:
    if target is None:
        return None
    for index, row in enumerate(rows):
        if row.get("ok") is not True:
            continue
        value = _finite(row.get(field))
        if value is not None and value <= target:
            return index
    return None


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None

    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        index = 0
        while index < len(values):
            end = index
            while end + 1 < len(values) and values[order[end + 1]] == values[order[index]]:
                end += 1
            rank = (index + end) / 2.0 + 1.0
            for pos in range(index, end + 1):
                out[order[pos]] = rank
            index = end + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if dx == 0 or dy == 0:
        return None
    return round(numerator / (dx * dy), 4)


def _residual_stats(points: Iterable[Mapping]) -> dict:
    """Error statistics of recorded predictions vs later measurements (J units)."""
    pairs = []
    for point in points:
        predicted, measured = _finite(point.get("predicted")), _finite(point.get("measured"))
        if predicted is not None and measured is not None:
            pairs.append(measured - predicted)
    if not pairs:
        return {"n": 0, "rmse": None, "mae": None, "mean_error": None}
    return {"n": len(pairs),
            "rmse": round(math.sqrt(sum(v * v for v in pairs) / len(pairs)), 6),
            "mae": round(sum(abs(v) for v in pairs) / len(pairs), 6),
            "mean_error": round(sum(pairs) / len(pairs), 6)}


def _nearest_training(training: Mapping | None, manifest: Mapping | None, vector,
                      *, k: int = 5) -> dict:
    """Nearest recorded training rows to a normalized candidate vector, by L2 distance."""
    if training is None:
        return {"available": False, "status": NOT_RECORDED, "items": [],
                "reason": "the training arrays are not recorded"}
    try:
        v = np.asarray(vector, dtype=float).reshape(-1)
        X = np.asarray(training.get("X"), dtype=float)
        J = np.asarray(training.get("J"), dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return {"available": False, "status": NOT_RECORDED, "items": [],
                "reason": "the candidate active vector is not recorded"}
    if X.ndim != 2 or v.shape != (X.shape[1],) or not np.isfinite(v).all():
        return {"available": False, "status": NOT_RECORDED, "items": [],
                "reason": "the candidate vector does not match the training dimension"}
    distance = np.sqrt(((X - v) ** 2).sum(axis=1))
    ids = manifest.get("ids") if isinstance(manifest, Mapping) else None
    identities = _mapping(_mapping(manifest).get("meta")).get("identities")
    identities = _mapping(identities)
    order = np.argsort(distance, kind="stable")[:max(1, int(k))]
    items = []
    for index in order:
        ident = _mapping(identities.get(str(ids[index]))) if isinstance(ids, list) \
            and index < len(ids) else {}
        items.append({
            "id": str(ids[index]) if isinstance(ids, list) and index < len(ids) else None,
            "distance_l2": round(float(distance[index]), 6),
            "j": _finite(J[index]) if index < len(J) else None,
            "design_hash": ident.get("design_hash"),
            "geometry_hash": ident.get("geometry_hash"),
        })
    return {"available": True, "status": "recorded", "items": items,
            "distance_metric": "L2 in the model's normalized active space"}


def _incumbent_from_observations(observations: Iterable[Mapping]) -> dict | None:
    """Best eligible measured screen row recorded in results (params + vector identity)."""
    best = None
    for row in observations:
        result = _mapping(row.get("result"))
        if result.get("kind") != "screen" or result.get("eligible") is not True:
            continue
        j = _finite(result.get("observed_j"))
        if j is None:
            continue
        candidate = _mapping(row.get("candidate"))
        params = result.get("params") if isinstance(result.get("params"), Mapping) \
            else candidate.get("params")
        vector = candidate.get("active_vector") or candidate.get("x")
        if best is None or j < best["j"]:
            best = {"j": j, "params": dict(params) if isinstance(params, Mapping) else None,
                    "x": list(vector) if isinstance(vector, (list, tuple)) else None,
                    "design_hash": candidate.get("design_hash") or result.get("design_hash")}
    return best


def _param_delta(candidate_params, incumbent_params) -> dict:
    if not isinstance(candidate_params, Mapping) or not isinstance(incumbent_params, Mapping):
        return {"available": False, "status": NOT_RECORDED, "items": [],
                "reason": "candidate and incumbent parameters are not both recorded"}
    items = []
    for key in sorted(set(candidate_params) | set(incumbent_params)):
        before, after = _finite(incumbent_params.get(key)), _finite(candidate_params.get(key))
        if before is None or after is None:
            continue
        items.append({"key": str(key), "incumbent": before, "candidate": after,
                      "delta": round(after - before, 9)})
    return {"available": bool(items), "status": "recorded" if items else NOT_RECORDED,
            "items": items, "note": "candidate minus incumbent"}


def _inside_box(vector, box) -> bool | None:
    try:
        v = np.asarray(vector, dtype=float).reshape(-1)
        lo = np.asarray(box.get("lo"), dtype=float).reshape(-1)
        hi = np.asarray(box.get("hi"), dtype=float).reshape(-1)
    except (TypeError, ValueError, AttributeError):
        return None
    if v.shape != lo.shape or v.shape != hi.shape or not np.isfinite(v).all():
        return None
    return bool(np.all(v >= lo - 1e-9) and np.all(v <= hi + 1e-9))


def _slice_payload(item: Mapping) -> dict | None:
    """One 1-D posterior slice in real parameter units, with the invalid-combination flag."""
    item = _mapping(item)
    xs, mean, sd = item.get("x"), item.get("j_mean"), item.get("j_sd")
    if not (isinstance(xs, list) and isinstance(mean, list) and isinstance(sd, list)
            and len(xs) == len(mean) == len(sd) and 2 <= len(xs) <= 200):
        return None
    means = [_finite(v) for v in mean]
    sds = [_finite(v) for v in sd]
    lower = [_finite(v) for v in item.get("j_lower") or []]
    upper = [_finite(v) for v in item.get("j_upper") or []]
    if len(lower) != len(means):
        lower = [None if m is None or s is None else round(m - 2.0 * s, 9)
                 for m, s in zip(means, sds)]
    if len(upper) != len(means):
        upper = [None if m is None or s is None else round(m + 2.0 * s, 9)
                 for m, s in zip(means, sds)]
    feasibility = _mapping(item.get("feasibility"))
    warning = {
        "checked": feasibility.get("checked") is True,
        "status": str(feasibility.get("status") or "unknown"),
        "invalid_count": _int(feasibility.get("invalid_count")),
        "reason": _clip_text(feasibility.get("reason"), 400) or
        ("cheap feasibility was not evaluated for this slice; a 1-D slice can pass through "
         "geometrically invalid combinations"),
    }
    return {
        "key": _clip_text(item.get("key"), 80),
        "x": [_finite(v) for v in xs], "x_unit": [_finite(v) for v in item.get("x_unit") or []],
        "j_mean": means, "j_sd": sds, "j_lower": lower, "j_upper": upper,
        "anchor_x": _finite(item.get("anchor_x")),
        "anchor_x_unit": _finite(item.get("anchor_x_unit")),
        "anchor_j_mean": _finite(item.get("anchor_j_mean")),
        "unit": item.get("unit") or item.get("x_unit"),
        "feasibility_warning": warning,
        "labels": {"x": "parameter value in real units",
                   "j_mean": "model-predicted J",
                   "band": "mean ±2σ model credible interval",
                   "anchor": SLICE_ANCHOR_NOTE,
                   "caveat": MODEL_SENSITIVITY_NOTE,
                   "invalid": "a 1-D slice may pass through geometrically invalid combinations"},
    }


def _frontier_axes() -> dict:
    """The Pareto frontier is coverage(deg) × ripple(dB); J is never an axis."""
    return {"x": "coverage_deg", "y": "ripple_db", "units": ["deg", "dB"],
            "direction": "minimize",
            "note": ("J is a separate scalar ranking shown beside each point; it is not a "
                     "frontier axis, and acoustics-vs-size is not a recorded dimension.")}


def _nondominated(points: list[dict]) -> None:
    """Mark ``point['nondominated']`` for 2-D minimisation (coverage, ripple)."""
    for point in points:
        point["nondominated"] = True
    for i, a in enumerate(points):
        ax, ay = a["coverage_deg"], a["ripple_db"]
        for j, b in enumerate(points):
            if i == j:
                continue
            bx, by = b["coverage_deg"], b["ripple_db"]
            if bx <= ax and by <= ay and (bx < ax or by < ay):
                a["nondominated"] = False
                break


def _hypervolume(points: list[Mapping], limits) -> float | None:
    """2-D minimisation hypervolume in the frozen reference box."""
    try:
        ref_x, ref_y = float(limits[0]), float(limits[1])
    except (TypeError, ValueError, IndexError):
        return None
    if not (math.isfinite(ref_x) and math.isfinite(ref_y)):
        return None
    usable = [(float(p["coverage_deg"]), float(p["ripple_db"])) for p in points
              if p.get("nondominated") and math.isfinite(float(p["coverage_deg"]))
              and math.isfinite(float(p["ripple_db"]))]
    usable = [(x, y) for x, y in usable if x <= ref_x and y <= ref_y]
    if not usable:
        return 0.0
    usable.sort()
    area = 0.0
    for index, (x, y) in enumerate(usable):
        next_x = usable[index + 1][0] if index + 1 < len(usable) else ref_x
        area += max(0.0, next_x - x) * max(0.0, ref_y - y)
    return round(area, 8)


def _normalise_reference(reference: Mapping | None) -> dict | None:
    if not isinstance(reference, Mapping):
        return None
    limits = reference.get("limits")
    ref_point = reference.get("ref_point")
    if not isinstance(limits, (list, tuple)) or not isinstance(ref_point, (list, tuple)):
        return None
    if len(limits) == 1 and isinstance(limits[0], (list, tuple)):
        limits = limits[0]
    if len(ref_point) == 1 and isinstance(ref_point[0], (list, tuple)):
        ref_point = ref_point[0]
    try:
        limits = [float(v) for v in limits]
        ref_point = [float(v) for v in ref_point]
    except (TypeError, ValueError):
        return None
    if len(limits) != 2 or len(ref_point) != 2:
        return None
    return {"limits": limits, "ref_point": ref_point,
            "units": list(reference.get("units") or ["deg", "dB"]),
            "direction": reference.get("direction") or "minimize"}


# --------------------------------------------------------------------------- views


def convergence_view(service, study, *, runs_root, root=None, comparison=None) -> dict:
    sid = study["id"]
    results, results_meta, reason = _results(service, sid)
    if results is None:
        return _view("missing", reason or "run results are not available")
    manifest, _meta, _reason = _manifest(service, sid)
    paths = (_run_paths(runs_root, service, sid) if runs_root is not None
             else {"run_id": None, "run_dir": None, "verify_dir": None})
    run_dir = paths["run_dir"]
    bo = _bo_series(_observations(results))
    if not bo["points"]:
        return _view("missing", "run results contain no measured screen J yet")
    budget = _budget(service, sid)
    verify_rows = _verify_rows(run_dir)
    bo["best_verify_j"] = _best_verify(verify_rows) or (
        min((p[1] for p in _bo_series(_observations(results))["verify"]), default=None))
    bo["points"] = _downsample(bo["points"])
    arms = [{
        "id": "bo", "label": "BO", "method": "bo", "policy": _policy(study),
        "color_slot": 0, "run_id": paths["run_id"], "screens": bo["screens"],
        "verify": len(verify_rows), "best_j": bo["best_j"],
        "best_verify_j": bo["best_verify_j"], "budget_profile": budget.get("budget_profile"),
        "points": bo["points"], "solves": bo["solves"], "refusals": bo["refusals"],
        "exploration": bo["exploration"], "exploration_points": bo["exploration_points"],
        "verify_points": bo["verify"],
        "screens_to_target": None,
    }]
    spec = comparison or (find_comparison_spec(root, Path(service.store.root))
                          if (root and runs_root is not None) else None)
    target = None
    incumbent = None
    versions = {_objective_version(manifest)}
    if isinstance(spec, Mapping):
        target = _finite(spec.get("target_j"))
        inc = spec.get("incumbent")
        if isinstance(inc, Mapping):
            incumbent = {"j": _finite(inc.get("j")), "label": _clip_text(inc.get("label"), 200)}
        for arm in spec.get("arms") or ():
            if not isinstance(arm, Mapping) or arm.get("method") == "bo":
                continue
            arm_dir = _resolve_arm_dir(runs_root, arm)
            if arm_dir is None:
                continue
            rows = _screen_rows(arm_dir)
            series = _run_series(rows)
            arm_verify = _verify_rows(arm_dir)
            arm_version = _int(rows[0].get("objective_version")) if rows else None
            versions.add(arm_version)
            arms.append({
                "id": str(arm.get("id") or arm_dir.name),
                "label": _clip_text(arm.get("label") or arm.get("id") or arm_dir.name, 120),
                "method": str(arm.get("method") or "cma"),
                "policy": _clip_text(arm.get("policy"), 40),
                "color_slot": len(arms) % 8,
                "run_id": arm_dir.name,
                "screens": series["screens"],
                "verify": len(arm_verify),
                "best_j": series["best_j"],
                "best_verify_j": _best_verify(arm_verify),
                "budget_profile": arm.get("budget_profile"),
                "points": series["points"], "solves": series["solves"],
                "refusals": series["refusals"], "exploration": [],
                "exploration_points": [],
                "verify_points": [],
                "screens_to_target": _screens_to_target(rows, target),
            })
    if target is not None and arms[0].get("screens_to_target") is None:
        # BO screens are in results, not in a run ndjson written by this study's worker.
        for index, row in enumerate(_observations(results)):
            result = _mapping(row.get("result"))
            if result.get("kind") != "screen" or result.get("eligible") is not True:
                continue
            value = _finite(result.get("observed_j"))
            if value is not None and value <= target:
                arms[0]["screens_to_target"] = index
                break
    versions = {v for v in versions if v is not None}
    status = "ready" if len(arms) > 1 else "partial"
    notes = []
    if len(arms) == 1:
        notes.append("Matched CMA arms are not recorded for this study yet.")
    if len(versions) > 1:
        status = "partial"
        notes.append("These arms use different objective versions; J is not comparable across them.")
    return _view(status, None, objective_version=_objective_version(manifest),
                 arms=arms, incumbent=incumbent, target_j=target,
                 versions_mixed=len(versions) > 1, versions=sorted(versions),
                 budget=budget.get("budget"), budget_profile=budget.get("budget_profile"),
                 progress=results.get("progress"), eta=_eta(results, budget.get("budget"), run_dir),
                 run={"run_id": paths["run_id"],
                      "has_screen": bool(run_dir and ((run_dir / "screen" / "search.ndjson").is_file()
                                                       or (run_dir / "search.ndjson").is_file())),
                      "has_verify": bool(paths["verify_dir"] and (paths["verify_dir"] / "search.ndjson").is_file())},
                 status_kinds=_status_kinds(status,
                                            artifact_status=_artifact_status(results_meta),
                                            physical=_physical_counts(_observations(results))),
                 notes=notes)


def _calibration_core(service, study, *, results=None) -> dict:
    sid = study["id"]
    if results is None:
        results, _meta, reason = _results(service, sid)
    else:
        reason = None
    if results is None:
        return _view("missing", reason or "run results are not available")
    observations = _observations(results)
    points = []
    physical = []
    seen = set()
    interval_label = None
    for row in observations:
        candidate = _mapping(row.get("candidate"))
        result = _mapping(row.get("result"))
        if result.get("kind") != "screen" or result.get("eligible") is not True:
            continue
        measured = _finite(result.get("observed_j"))
        predicted = candidate.get("predicted")
        if measured is None or not isinstance(predicted, Mapping):
            continue
        if _finite(predicted.get("j_mean")) is not None:
            mean = _finite(predicted.get("j_mean"))
            lower = _finite(predicted.get("j_lower"))
            upper = _finite(predicted.get("j_upper"))
            if mean is None:
                continue
            lower = mean if lower is None else lower
            upper = mean if upper is None else upper
            interval_label = interval_label or _clip_text(predicted.get("interval_label"), 300)
            key = str(result.get("solve_id") or candidate.get("candidate_id") or len(points))
            if key in seen:
                continue
            seen.add(key)
            points.append({"solve_id": key, "predicted": mean,
                           "lower": lower, "upper": upper, "measured": measured,
                           "inside": bool(lower <= measured <= upper)})
        elif isinstance(predicted.get("coverage_deg"), Mapping):
            cov = _mapping(predicted.get("coverage_deg"))
            rip = _mapping(predicted.get("ripple_db"))
            if rip:
                physical.append({
                    "solve_id": str(result.get("solve_id") or ""),
                    "coverage_deg": {k: _finite(cov.get(k)) for k in ("mean", "lower", "upper")},
                    "ripple_db": {k: _finite(rip.get(k)) for k in ("mean", "lower", "upper")},
                    "measured_j": measured,
                })
    if not points and not physical:
        # Old runs persisted only the initial proposal's prediction.  Use it if the
        # candidate identity matches a real screen row; never invent a join.
        proposal, _meta, _reason = _proposal(service, sid)
        if isinstance(proposal, Mapping):
            predicted = proposal.get("predicted")
            candidate = _mapping(proposal.get("candidate"))
            if isinstance(predicted, Mapping) and _finite(predicted.get("j_mean")) is not None:
                identity = candidate.get("candidate_id") or candidate.get("design_hash")
                for row in observations:
                    c = _mapping(row.get("candidate"))
                    r = _mapping(row.get("result"))
                    if r.get("kind") != "screen" or r.get("eligible") is not True:
                        continue
                    if identity and identity in (c.get("candidate_id"), c.get("design_hash")):
                        measured = _finite(r.get("observed_j"))
                        if measured is not None:
                            lower = _finite(predicted.get("j_lower"))
                            upper = _finite(predicted.get("j_upper"))
                            points.append({
                                "solve_id": str(r.get("solve_id") or identity),
                                "predicted": _finite(predicted.get("j_mean")),
                                "lower": lower,
                                "upper": upper,
                                "measured": measured,
                                "inside": bool(lower is not None and upper is not None
                                               and lower <= measured <= upper),
                                "source": "initial proposal only",
                            })
                            break
    xs = [p["predicted"] for p in points if p["predicted"] is not None]
    ys = [p["measured"] for p in points if p["predicted"] is not None]
    coverage = (sum(1 for p in points if p["inside"]) / len(points)) if points else None
    n = len(points)
    status = "ready" if n >= 3 else ("partial" if n else "missing")
    reason = None
    if n == 0:
        reason = ("No per-screen model predictions are recorded for this run. "
                  "The next analyze/propose records them; old runs keep only the initial proposal.")
    elif n < 3:
        reason = f"Only {n} predicted screen(s) are recorded; calibration needs at least 3."
    return _view(status, reason, points=points[:MAX_TABLE], physical=physical[:MAX_TABLE],
                 n=n, coverage=round(coverage, 4) if coverage is not None else None,
                 spearman=_spearman(xs, ys),
                 interval_label=interval_label or "model credible interval",
                 notes=["Predicted values are model credible intervals, never measured J."])


def _sequential_validation(service, study, view) -> dict:
    """Out-of-sample tracking of proposals against their subsequent screen measurements.

    Clearly named and separated from :func:`_loo_section` so the frontend cannot blur a
    sequential proposal check with LOO on the original training cohort.
    """
    points = [p for p in (view.get("points") or []) if isinstance(p, Mapping)]
    n = len(points)
    pairs = [(_finite(p.get("predicted")), _finite(p.get("measured"))) for p in points]
    xs = [a for a, b in pairs if a is not None and b is not None]
    ys = [b for a, b in pairs if a is not None and b is not None]
    coverage = _finite(view.get("coverage"))
    interval_label = _clip_text(view.get("interval_label"), 300) or "model credible interval"
    model, model_meta, _reason = _model(service, study["id"])
    proposal, proposal_meta, _reason = _proposal(service, study["id"])
    provenance = _model_provenance(
        model_meta, model, retrospective=False,
        source="study model/proposal artifacts recorded when the candidate was proposed")
    provenance["proposal_generated_utc"] = _clip_text(_mapping(proposal).get("generated_utc"), 64)
    provenance["proposal_artifact_sha256"] = (_mapping(proposal_meta).get("sha256")
                                              if isinstance(proposal_meta, Mapping) else None)
    return {
        "label": "Sequential proposals vs subsequently measured J",
        "source": "recorded proposal prediction joined to its later screen measurement",
        "out_of_sample": True,
        "n": n,
        "n_with_interval": sum(1 for p in points
                               if p.get("lower") is not None and p.get("upper") is not None),
        "points": points[:MAX_TABLE],
        "physical": list(view.get("physical") or [])[:MAX_TABLE],
        "coverage": coverage,
        "coverage_percent": round(coverage * 100.0, 2) if coverage is not None else None,
        "rank_correlation": _spearman(xs, ys),
        "error": _residual_stats(points),
        "interval_label": interval_label,
        "interval_evidence": {
            "declared_interval": interval_label,
            "claimed_level": 0.95,
            # A small sequential sample never proves 95% calibration, so it is not claimed.
            "calibrated_95_supported": False,
            "empirical_coverage": coverage,
            "n": n,
            "basis": ("share of measured J inside each recorded per-proposal interval "
                      "(tracking statistic, not calibration proof)" if n else NOT_RECORDED),
            "note": ("±2σ is the model's credible interval; it is not presented as a calibrated "
                     "95% interval unless the recorded evidence supports that."),
        },
        "model_provenance": provenance,
        "notes": ["Predicted values are model credible intervals, never measured J.",
                  "This section tracks later proposals; it is not the training-cohort LOO."],
    }


def _loo_section(can_compute, diag, diag_meta, clean, loo, summary) -> dict:
    """Efficient LOO on the original training cohort, explicitly not sequential tracking."""
    provenance = (_model_provenance(
        diag_meta, diag, retrospective=True,
        source="diagnostics artifact: refit of the stored training set") if diag else
        {"available": False, "status": NOT_RECORDED, "retrospective": None,
         "note": "no model diagnostics artifact is recorded for this study"})
    if not diag or not clean:
        return {"label": "Efficient leave-one-out on the original training cohort",
                "source": "diagnostics artifact (efficient_loo_cv, no refit per row)",
                "out_of_sample": False, "available": False, "status": NOT_RECORDED,
                "can_compute": bool(can_compute), "n": NOT_RECORDED, "rows": [],
                "truncated": NOT_RECORDED, "summary": NOT_RECORDED, "method": NOT_RECORDED,
                "rank_correlation": NOT_RECORDED, "error": NOT_RECORDED,
                "interval_evidence": {"status": NOT_RECORDED,
                                      "calibrated_95_supported": False,
                                      "note": "not recorded; compute model diagnostics first"},
                "model_provenance": provenance}
    evidence = dict(_mapping(loo.get("interval_evidence")))
    evidence.setdefault("calibrated_95_supported", False)
    coverage95 = _finite(summary.get("coverage_95"))
    return {
        "label": _clip_text(loo.get("label"), 300) or
        "Efficient leave-one-out on the original training cohort",
        "source": "diagnostics artifact (efficient_loo_cv, no refit per row)",
        "out_of_sample": False, "available": True, "status": "recorded",
        "can_compute": True, "n": len(clean), "rows": clean,
        "truncated": bool(loo.get("truncated")), "summary": dict(summary),
        "method": _clip_text(loo.get("method"), 300),
        "rank_correlation": _finite(summary.get("spearman")),
        "coverage_95_percent": (round(coverage95 * 100.0, 2)
                                if coverage95 is not None else None),
        "error": _mapping(loo.get("error")) or {"rmse": _finite(summary.get("rmse")),
                                                "mae": None, "mean_error": None},
        "cohort": _clip_text(loo.get("cohort"), 300),
        "interval_evidence": evidence,
        "model_provenance": provenance,
        "notes": ["Leave-one-out on the original training cohort; hyperparameters held fixed.",
                  "Not sequential tracking of later proposal predictions."],
    }


def calibration_view(service, study) -> dict:
    """Two named sections: sequential proposal tracking and training-cohort efficient LOO."""
    sid = study["id"]
    results, results_meta, _reason = _results(service, sid)
    view = _calibration_core(service, study, results=results)
    diag, can_compute, diag_meta, _diag_reason = _diagnostics_artifact(service, sid)
    observations = _observations(results) if isinstance(results, Mapping) else []
    counts = _physical_counts(observations)
    loo = _mapping(diag.get("loo")) if diag else {}
    summary = _mapping(loo.get("summary"))
    rows_value = loo.get("rows")
    rows = rows_value if isinstance(rows_value, list) else []
    clean = []
    for row in rows[:400]:
        row = _mapping(row)
        obs, mean, sd = _finite(row.get("j_obs")), _finite(row.get("j_mean")), _finite(row.get("j_sd"))
        if obs is None or mean is None:
            continue
        clean.append({"id": _clip_text(row.get("id"), 80), "j_obs": obs, "j_mean": mean, "j_sd": sd})
    if diag and clean:
        # Legacy shape kept for the existing renderer; the named section below is unambiguous.
        view["loo"] = {"available": True, "n": len(clean), "rows": clean,
                       "truncated": bool(loo.get("truncated")), "summary": dict(summary),
                       "method": _clip_text(loo.get("method"), 300)}
        if view.get("status") == "missing":
            view["status"] = "partial"
            view.pop("reason", None)
    else:
        view["loo"] = {"available": False, "can_compute": bool(can_compute)}
    view["sections"] = {
        "sequential_validation": ("proposals joined to their subsequent screen measurements "
                                  "(out-of-sample tracking)"),
        "efficient_loo_cv": ("leave-one-out on the original training cohort (hyperparameters "
                             "held fixed)"),
    }
    view["sequential_validation"] = _sequential_validation(service, study, view)
    view["efficient_loo_cv"] = _loo_section(can_compute, diag, diag_meta, clean, loo, summary)
    view["status_kinds"] = _status_kinds(
        view.get("status", "missing"),
        artifact_status=_artifact_status(results_meta),
        physical=counts)
    view["diagnostics"] = ({"available": True, "status": "recorded",
                            "can_compute": True,
                            "model_provenance": view["efficient_loo_cv"]["model_provenance"]}
                           if diag else
                           {"available": False, "status": NOT_RECORDED,
                            "can_compute": bool(can_compute),
                            "model_provenance": view["efficient_loo_cv"]["model_provenance"]})
    view["notes"] = list(view.get("notes") or []) + [
        "The two sections are not interchangeable: sequential tracking is out-of-sample; "
        "efficient LOO is on the original training cohort."]
    return view


def model_performance_view(service, study) -> dict:
    """Alias whose name matches the frontend's Model-performance panel."""
    return calibration_view(service, study)


def _sensitivity_status(service, study, view, diag_meta) -> dict:
    results, _meta, _reason = _results(service, study["id"])
    counts = _physical_counts(_observations(results)) if isinstance(results, Mapping) else \
        {"summary": NOT_RECORDED}
    return _status_kinds(view.get("status", "missing"),
                         artifact_status=_artifact_status(diag_meta),
                         physical=counts)


def sensitivity_view(service, study) -> dict:
    view = _sensitivity_core(service, study)
    diag, can_compute, diag_meta, diag_reason = _diagnostics_artifact(service, study["id"])
    if not diag:
        view["diagnostics"] = {"available": False, "can_compute": bool(can_compute),
                               "status": NOT_RECORDED,
                               "reason": diag_reason or "no model diagnostics are recorded"}
        # Old studies never fabricated diagnostics; say so for every missing field.
        for field in ("hyperparameters", "relevance", "posterior_slices", "loo", "pareto"):
            view.setdefault(field, NOT_RECORDED)
        view["knobs"] = view.get("knobs") or []
        view["slices"] = view.get("slices") or []
        view["status_kinds"] = _sensitivity_status(service, study, view, diag_meta)
        return view
    slices_block = _mapping(diag.get("slices"))
    per_key = _mapping(slices_block.get("per_key"))
    slices = []
    for key, item in list(per_key.items())[:24]:
        payload = _slice_payload({**dict(_mapping(item)), "key": key})
        if payload is not None:
            slices.append(payload)
    relevance = [dict(_mapping(r)) for r in (diag.get("relevance") or [])
                 if isinstance(r, Mapping) and r.get("key")]
    by_key = {str(r["key"]): r for r in relevance}
    if view.get("knobs"):
        for knob in view["knobs"]:
            item = by_key.get(str(knob.get("key")), {})
            knob["rank"] = _int(item.get("rank"))
            knob["at_bound"] = item.get("at_bound") if isinstance(item.get("at_bound"), bool) else None
            knob["inv_lengthscale"] = _finite(item.get("inv_lengthscale"))
            knob["meaning"] = MODEL_SENSITIVITY_NOTE
    view["diagnostics"] = {
        "available": bool(slices), "can_compute": True, "status": "recorded",
        "anchor": _clip_text(slices_block.get("anchor"), 80),
        "grid_n": _int(slices_block.get("grid_n")),
        "model_provenance": _model_provenance(
            diag_meta, diag, retrospective=True,
            source="diagnostics artifact: refit of the stored training set"),
    }
    view["hyperparameters"] = (dict(_mapping(diag.get("hyperparameters")))
                               if isinstance(diag.get("hyperparameters"), Mapping)
                               else NOT_RECORDED)
    view["relevance"] = relevance[:MAX_TABLE]
    view["posterior_slices"] = {
        "available": bool(slices),
        "anchor": "incumbent",
        "other_knobs": SLICE_ANCHOR_NOTE,
        "labels": {"caveat": MODEL_SENSITIVITY_NOTE},
        "items": slices,
    }
    view["slices"] = slices
    view["labels"] = {"knobs": MODEL_SENSITIVITY_NOTE, "slices": SLICE_ANCHOR_NOTE}
    if view.get("status") == "missing":
        relevance_nonzero = [r for r in relevance
                             if (_finite(r.get("inv_lengthscale")) or 0.0) > 0]
        total = sum(_finite(r.get("inv_lengthscale")) or 0.0 for r in relevance_nonzero)
        if total > 0:
            view["knobs"] = [{"key": _clip_text(r.get("key"), 80), "lengthscale": None,
                              "importance": round((_finite(r.get("inv_lengthscale")) or 0.0) / total, 6),
                              "rank": _int(r.get("rank")),
                              "at_bound": r.get("at_bound") if isinstance(r.get("at_bound"), bool) else None,
                              "inv_lengthscale": _finite(r.get("inv_lengthscale")),
                              "meaning": MODEL_SENSITIVITY_NOTE}
                             for r in relevance_nonzero[:MAX_TABLE]]
            view["status"] = "partial"
            view.pop("reason", None)
    view["status_kinds"] = _sensitivity_status(service, study, view, diag_meta)
    view["model_provenance"] = view["diagnostics"]["model_provenance"]
    return view


def _sensitivity_core(service, study) -> dict:
    sid = study["id"]
    model, _meta, reason = _model(service, sid)
    if model is None:
        return _view("missing", reason or "model artifact is not available")
    hyper = model.get("hyperparameters")
    if not isinstance(hyper, Mapping):
        return _view("missing",
                     "Model hyperparameters were not recorded for this proposal; the next "
                     "analyze/propose records them.",
                     policy=_policy(study), model_status=model.get("status"),
                     engine=model.get("library_versions"))
    lengthscales = hyper.get("lengthscales")
    if not isinstance(lengthscales, list) or not lengthscales:
        return _view("missing", "The model artifact has no lengthscales.",
                     policy=_policy(study), model_status=model.get("status"))
    values = [_finite(v) for v in lengthscales]
    values = [v if v is not None and v > 0 else None for v in values]
    manifest, _meta, _reason = _manifest(service, sid)
    keys = _active_keys(manifest)
    note = None
    if len(keys) != len(values):
        keys = [f"knob_{i + 1}" for i in range(len(values))]
        note = "Knob names are not recorded for this model; showing the encoded order."
    usable = [(key, value) for key, value in zip(keys, values) if value is not None]
    if not usable:
        return _view("missing", "Model lengthscales are not finite and positive.")
    inverse = [1.0 / value for _key, value in usable]
    total = sum(inverse)
    knobs = [{"key": key, "lengthscale": round(value, 6),
              "importance": round(inv / total, 6) if total else None}
             for (key, value), inv in zip(usable, inverse)]
    knobs.sort(key=lambda item: (-(item["importance"] or 0), item["key"]))
    status = "ready" if model.get("status") == "ok" else "partial"
    return _view(status, None, policy=_policy(study), model_status=model.get("status"),
                 engine=model.get("library_versions"), knobs=knobs[:MAX_TABLE],
                 lengthscale_bounds=hyper.get("lengthscale_bounds"),
                 outputscale=hyper.get("outputscale"),
                 note=note,
                 notes=["Relative knob sensitivity is 1/lengthscale, normalized; "
                        "it describes the model, not a proven acoustic effect."])


def trust_region_view(service, study) -> dict:
    policy = _policy(study)
    if policy != "turbo":
        return _view("not_applicable", f"Current policy is {policy}; trust region applies to turbo only.",
                     policy=policy)
    sid = study["id"]
    results, results_meta, reason = _results(service, sid)
    proposal, _proposal_meta, _reason = _proposal(service, sid)
    records = []
    if isinstance(proposal, Mapping) and isinstance(proposal.get("trust_region"), Mapping):
        records.append(proposal["trust_region"])
    observations = _observations(results)
    for row in observations:
        candidate = _mapping(row.get("candidate"))
        record = candidate.get("trust_region")
        if isinstance(record, Mapping):
            records.append(record)
    unique = {}
    for record in records:
        index = _int(record.get("proposal_index"))
        if index is not None:
            unique[index] = record
    records = [unique[key] for key in sorted(unique)]
    counts = _physical_counts(observations)
    if not records:
        return _view("missing", reason or "No trust-region state is recorded for this run.",
                     policy=policy,
                     status_kinds=_status_kinds("missing",
                                                artifact_status=_artifact_status(results_meta),
                                                physical=counts))
    series, attempts, events = [], [], []
    previous_length = None
    latest = None
    for record in records:
        index = _int(record.get("proposal_index"))
        state = _mapping(record.get("state_after"))
        length = _finite(state.get("length"))
        step = {
            "proposal_index": index,
            "length": length,
            "iteration": _int(state.get("iteration")),
            "success_counter": _int(state.get("success_counter")),
            "failure_counter": _int(state.get("failure_counter")),
            "status": state.get("status") or NOT_RECORDED,
            "change": None,
        }
        if length is not None:
            step["change"] = ("expansion" if previous_length is not None
                              and length > previous_length * (1 + 1e-9) else
                              "shrink" if previous_length is not None
                              and length < previous_length * (1 - 1e-9) else None)
            events.append({"proposal_index": index, "kind": step["change"],
                           "from": previous_length, "to": length})
            series.append([index if index is not None else len(series), length])
            previous_length = length
        attempts.append(step)
        latest = record
    state = _mapping(latest.get("state_after")) if latest is not None else {}
    budget = _budget(service, sid)
    manifest, _meta, _reason = _manifest(service, sid)
    progress = _mapping(_mapping(results).get("progress"))
    budget_values = _mapping(budget.get("budget"))
    screens = _int(progress.get("screen_calls"))
    total = _int(budget_values.get("screen_calls"))
    length = _finite(state.get("length"))
    collapsed = state.get("status") == "collapsed" or (length is not None and length < 0.5 ** 7)
    box = _mapping(latest.get("box")) if latest is not None else {}
    keys = _active_keys(manifest)
    lo_value, hi_value, weight_value = box.get("lo"), box.get("hi"), box.get("weights")
    lo_values = lo_value if isinstance(lo_value, list) else []
    hi_values = hi_value if isinstance(hi_value, list) else []
    weights = weight_value if isinstance(weight_value, list) else []
    if not keys:
        keys = [f"x{i}" for i in range(max(len(lo_values), len(hi_values)))]
    bounds = []
    for index, key in enumerate(keys[:MAX_TABLE]):
        lo = _finite(lo_values[index]) if index < len(lo_values) else None
        hi = _finite(hi_values[index]) if index < len(hi_values) else None
        bounds.append({
            "key": key, "lo": lo, "hi": hi,
            "width": round(hi - lo, 9) if lo is not None and hi is not None else None,
            "weight": _finite(weights[index]) if index < len(weights) else None,
            "space": "normalized active space", "global": {"lo": 0.0, "hi": 1.0},
        })
    center = state.get("center") if isinstance(state.get("center"), list) else None
    training, _reason = _training_arrays(service, sid)
    nearest = _nearest_training(training, manifest, center, k=1) if center else \
        {"available": False, "status": NOT_RECORDED, "items": []}
    nearest_item = (nearest.get("items") or [None])[0] if nearest.get("available") else None
    center_identity = ({
        "resolved": bool(nearest_item and (nearest_item.get("distance_l2") or 0.0) <= 1e-6),
        "id": (nearest_item or {}).get("id"),
        "design_hash": (nearest_item or {}).get("design_hash"),
        "geometry_hash": (nearest_item or {}).get("geometry_hash"),
        "distance_l2": (nearest_item or {}).get("distance_l2"),
        "basis": "nearest training row to the normalized trust-region centre",
    } if center else {"resolved": False, "status": NOT_RECORDED})
    latest_box = {"lo": lo_values, "hi": hi_values}
    inside = outside = unknown = 0
    proposals = []
    for row in observations:
        candidate = _mapping(row.get("candidate"))
        result = _mapping(row.get("result"))
        record = _mapping(candidate.get("trust_region"))
        vector = candidate.get("active_vector") or candidate.get("x")
        if vector is None:
            continue
        proposal_box = _mapping(record.get("box"))
        used_box = proposal_box if proposal_box.get("lo") and proposal_box.get("hi") else latest_box
        flag = _inside_box(vector, used_box)
        if flag is None:
            unknown += 1
        elif flag:
            inside += 1
        else:
            outside += 1
        proposals.append({
            "proposal_index": _int(record.get("proposal_index")),
            "design_hash": candidate.get("design_hash") or result.get("design_hash"),
            "inside": flag,
            "box_source": "proposal" if proposal_box.get("lo") else "latest",
        })
    return _view("ready", None, policy=policy, length_series=series,
                 length_over_attempts=attempts[:MAX_SERIES],
                 expansion_steps=[e for e in events if e["kind"] == "expansion"][:MAX_SERIES],
                 shrink_steps=[e for e in events if e["kind"] == "shrink"][:MAX_SERIES],
                 length_bounds=state.get("length_bounds"),
                 active_keys=keys,
                 success_counter=_int(state.get("success_counter")),
                 failure_counter=_int(state.get("failure_counter")),
                 iteration=_int(state.get("iteration")),
                 center=center,
                 center_identity=center_identity,
                 box={"lo": box.get("lo"), "hi": box.get("hi"), "weights": box.get("weights")}
                 if box else None,
                 normalized_parameter_bounds=bounds,
                 proposals=proposals[:MAX_POINTS],
                 proposals_inside=inside, proposals_outside=outside, proposals_unknown=unknown,
                 terminal={"collapsed": bool(collapsed),
                           "status": state.get("status") or NOT_RECORDED,
                           "reason": state.get("terminal_reason"),
                           "label": "converged" if collapsed else "active",
                           "note": ("A collapsed box means the local search converged; it is "
                                    "not necessarily global convergence.")},
                 budget={"used": screens, "total": total,
                         "unspent": (max(0, total - screens)
                                     if total is not None and screens is not None else None),
                         "unspent_note": "unspent budget stays visible after a terminal state"},
                 status_kinds=_status_kinds("ready",
                                            artifact_status=_artifact_status(results_meta),
                                            physical=counts),
                 notes=["A collapsed box means converged, not failed. Unspent budget is reported.",
                        "The centre is linked to its recorded design identity when resolvable."])


def pareto_view(service, study, *, runs_root=None) -> dict:
    policy = _policy(study)
    if policy != "pareto":
        return _view("not_applicable", f"Current policy is {policy}; the frontier applies to pareto only.",
                     policy=policy)
    sid = study["id"]
    payload, payload_meta, reason = _pareto_metrics(service, sid)
    if payload is None:
        return _view("missing", reason or "pareto_metrics artifact is not available")
    reference = _normalise_reference(payload.get("reference"))
    observations = _mapping(payload.get("observations"))
    manifest, _meta, _reason = _manifest(service, sid)
    manifest_map = _mapping(manifest)
    identities = _mapping(_mapping(manifest_map.get("meta")).get("identities"))
    training, _reason = _training_arrays(service, sid)
    j_by_id = {}
    if training is not None and manifest_map:
        ids = manifest_map.get("ids")
        if isinstance(ids, list) and len(ids) == len(training["J"]):
            j_by_id = {str(oid): float(value) for oid, value in zip(ids, training["J"])}
    points = []
    for oid, obs in list(observations.items())[:MAX_POINTS]:
        if not isinstance(obs, Mapping) or obs.get("status") != "complete":
            continue
        cov, rip = _finite(obs.get("coverage_deg")), _finite(obs.get("ripple_db"))
        if cov is None or rip is None:
            continue
        identity = _mapping(identities.get(oid))
        points.append({
            "observation_id": str(oid),
            "design_hash": identity.get("design_hash"),
            "coverage_deg": cov, "ripple_db": rip,
            "j": j_by_id.get(str(oid)), "source": "training", "measured": True,
        })
    results, _meta, _reason = _results(service, sid)
    finalists = set()
    verification, _meta, _reason = _verification(service, sid)
    if isinstance(verification, Mapping):
        selection = _mapping(verification.get("selection"))
        finalists = set(selection.get("finalists") or ()) | set(selection.get("audits") or ())
    for row in _observations(results):
        candidate = _mapping(row.get("candidate"))
        result = _mapping(row.get("result"))
        if result.get("kind") != "screen":
            continue
        objectives = result.get("objectives")
        metric = result.get("pareto_metric")
        cov = rip = None
        if isinstance(objectives, list) and len(objectives) == 2:
            cov, rip = _finite(objectives[0]), _finite(objectives[1])
        elif isinstance(metric, Mapping):
            cov, rip = _finite(metric.get("coverage_deg")), _finite(metric.get("ripple_db"))
        if cov is None or rip is None:
            continue
        design = candidate.get("design_hash") or candidate.get("geometry_hash") or result.get("design_hash")
        points.append({
            "observation_id": str(result.get("physical_id") or result.get("solve_id") or len(points)),
            "design_hash": design, "coverage_deg": cov, "ripple_db": rip,
            "j": _finite(result.get("observed_j")), "source": "screen", "measured": True,
            "finalist": bool(design in finalists or result.get("geometry_id") in finalists),
        })
    # De-duplicate by observation/design identity, keeping the measured row.
    deduped = {}
    for point in points:
        key = (point.get("design_hash"), point.get("coverage_deg"), point.get("ripple_db"))
        if key not in deduped:
            deduped[key] = point
    points = list(deduped.values())[:MAX_POINTS]
    excluded_points = []
    excluded_value = payload.get("excluded")
    if isinstance(excluded_value, Mapping):
        for oid, item in list(excluded_value.items())[:MAX_POINTS]:
            item = _mapping(item)
            excluded_points.append({
                "observation_id": str(oid),
                "status": item.get("status") or NOT_RECORDED,
                "reason": _clip_text(item.get("reason"), 300),
                "coverage_deg": _finite(item.get("coverage_deg")),
                "ripple_db": _finite(item.get("ripple_db")),
            })
    if not points:
        return _view("partial", "No measured coverage/ripple rows are available yet.",
                     reference=reference, frontier_axes=_frontier_axes(),
                     excluded_points=excluded_points,
                     notes=[payload.get("reference_policy")])
    _nondominated(points)
    nondominated = [{"observation_id": p.get("observation_id"), "design_hash": p.get("design_hash"),
                     "coverage_deg": p.get("coverage_deg"), "ripple_db": p.get("ripple_db"),
                     "j": p.get("j")} for p in points if p.get("nondominated")]
    hv = _hypervolume(points, reference["limits"]) if reference else None
    predicted = []
    for row in _observations(results):
        candidate = _mapping(row.get("candidate"))
        pred = candidate.get("predicted")
        if isinstance(pred, Mapping) and isinstance(pred.get("coverage_deg"), Mapping):
            cov_pred = _mapping(pred.get("coverage_deg"))
            rip_pred = _mapping(pred.get("ripple_db"))
            predicted.append({
                "design_hash": candidate.get("design_hash"),
                "source": "predicted", "measured": False,
                "coverage_deg": {k: _finite(cov_pred.get(k)) for k in ("mean", "lower", "upper")},
                "ripple_db": {k: _finite(rip_pred.get(k)) for k in ("mean", "lower", "upper")},
            })
    notes = [
        "Frozen reference comes from the training rows; later rows still train the model "
        "but add no hypervolume when worse than the reference.",
        "Training subset uses frontier/crowding, not the older latest-64/best-64 rule.",
        "Coverage is plain physical coverage error (owner decision 2026-11-15); J is shown beside it.",
    ]
    if isinstance(payload.get("limitations"), list):
        notes.extend(str(x) for x in payload["limitations"][:6])
    status = "ready" if reference is not None and points else "partial"
    paths = _run_paths(runs_root, service, sid) if runs_root is not None else {}
    diag, can_compute, diag_meta, _diag_reason = _diagnostics_artifact(service, sid)
    diag_pareto = _mapping(diag.get("pareto")) if diag else {}
    front_ids = [str(x) for x in diag_pareto.get("front_ids", [])[:MAX_POINTS]] \
        if isinstance(diag_pareto.get("front_ids"), list) else None
    hv_trace = [[_int(r.get("seq")), _finite(r.get("hv"))] for r in diag_pareto.get("hv_trace", [])[:MAX_SERIES]
                if isinstance(r, Mapping)] if isinstance(diag_pareto.get("hv_trace"), list) else None
    diagnostics = ({"available": True, "front_ids": front_ids, "hv_trace": hv_trace,
                    "model_provenance": _model_provenance(
                        diag_meta, diag, retrospective=True,
                        source="diagnostics artifact: refit of the stored training set")}
                   if diag and (front_ids is not None or hv_trace is not None)
                   else {"available": False, "can_compute": bool(can_compute),
                         "status": NOT_RECORDED if not diag else "recorded"})
    counts = _physical_counts(_observations(results))
    return _view(status, None, reference=reference, frozen_reference=reference,
                 reference_policy=payload.get("reference_policy"),
                 frontier_axes=_frontier_axes(),
                 points=points, hypervolume=hv, diagnostics=diagnostics,
                 hypervolume_trace=hv_trace,
                 nondominated=nondominated[:MAX_POINTS],
                 excluded_points=excluded_points[:MAX_TABLE],
                 n_complete=_int(payload.get("n_complete")), n_excluded=_int(payload.get("n_excluded")),
                 predicted=predicted[:MAX_TABLE], metric_policy=payload.get("metric_policy"),
                 status_kinds=_status_kinds(status,
                                            artifact_status=_artifact_status(payload_meta),
                                            physical=counts),
                 run_id=paths.get("run_id"),
                 notes=notes + ["Predicted points are separated from measured points.",
                                "J is displayed beside each point; the frontier axes are "
                                "coverage error (deg) and ripple (dB)."])


def _predicted_block(predicted) -> dict | str:
    predicted = _mapping(predicted)
    mean = _finite(predicted.get("j_mean"))
    if mean is not None:
        return {"kind": "scalar_j", "j_mean": mean,
                "j_lower": _finite(predicted.get("j_lower")),
                "j_upper": _finite(predicted.get("j_upper")),
                "y_sd": _finite(predicted.get("y_sd")),
                "interval_label": _clip_text(predicted.get("interval_label"), 300) or
                "model credible interval",
                "nonphysical": predicted.get("nonphysical") if
                isinstance(predicted.get("nonphysical"), bool) else None,
                "flags": list(predicted.get("flags") or [])[:20]}
    objectives = []
    for name, unit in (("coverage_deg", "deg"), ("ripple_db", "dB")):
        item = _mapping(predicted.get(name))
        if item:
            objectives.append({"name": name, "unit": unit,
                               "mean": _finite(item.get("mean")),
                               "lower": _finite(item.get("lower")),
                               "upper": _finite(item.get("upper")),
                               "interval_label": _clip_text(item.get("interval"), 300) or
                               "model credible interval"})
    if objectives:
        return {"kind": "physical_objectives", "objectives": objectives,
                "note": "predicted physical objective intervals, never measured values"}
    return NOT_RECORDED


def proposal_explanation_view(service, study, *, runs_root=None) -> dict:
    """Why the current candidate was proposed, from recorded artifacts only."""
    sid = study["id"]
    policy = _policy(study)
    proposal, proposal_meta, reason = _proposal(service, sid)
    if not isinstance(proposal, Mapping):
        return _view("missing", reason or "proposal artifact is not available", policy=policy,
                     status_kinds=_status_kinds("missing"))
    results, _results_meta, _reason = _results(service, sid)
    observations = _observations(results)
    model, model_meta, _reason = _model(service, sid)
    manifest, _meta, _reason = _manifest(service, sid)
    training, _reason = _training_arrays(service, sid)
    candidate = _mapping(proposal.get("candidate")) or _mapping(proposal.get("proposal"))
    predicted = _predicted_block(proposal.get("predicted"))
    acquisition = _mapping(proposal.get("acquisition"))
    selection_reason = proposal.get("selection_reason") or acquisition.get("selection_reason")
    fallback = proposal.get("fallback") is True
    designation = _designation(selection_reason, fallback)
    trusted = _mapping(candidate.get("trust_region")) or _mapping(proposal.get("trust_region"))
    index = _int(proposal.get("proposal_index") or candidate.get("proposal_index")
                 or trusted.get("proposal_index"))
    index_source = "proposal artifact"
    if index is None:
        identity = candidate.get("candidate_id") or candidate.get("design_hash")
        for position, row in enumerate(observations):
            c = _mapping(row.get("candidate"))
            r = _mapping(row.get("result"))
            if identity and identity in (c.get("candidate_id"), c.get("design_hash"),
                                         r.get("design_hash")):
                index = position
                index_source = "position of the matching results observation"
                break
    vector = candidate.get("active_vector") or candidate.get("x")
    nearest = _nearest_training(training, manifest, vector, k=5)
    incumbent = _incumbent_from_observations(observations)
    delta = _param_delta(candidate.get("params"),
                         incumbent.get("params") if incumbent else None)
    vector_delta = {"available": False, "status": NOT_RECORDED, "items": []}
    if incumbent and incumbent.get("x") is not None and isinstance(vector, (list, tuple)):
        try:
            a = np.asarray(incumbent["x"], dtype=float).reshape(-1)
            b = np.asarray(vector, dtype=float).reshape(-1)
            if a.shape == b.shape:
                vector_delta = {"available": True, "status": "recorded",
                                "distance_l2": round(float(np.sqrt(((b - a) ** 2).sum())), 6),
                                "note": "normalized active-space distance to the incumbent"}
        except (TypeError, ValueError):
            pass
    acq_value = _finite(acquisition.get("value"))
    acquisition_payload = {
        "value": acq_value,
        "units": _clip_text(acquisition.get("units"), 300),
        "rank": 1 if acq_value is not None else NOT_RECORDED,
        "rank_basis": ("the selected candidate maximized the recorded acquisition score among "
                       "the scored legal candidates" if acq_value is not None else NOT_RECORDED),
        "n_candidates": _int(acquisition.get("n_candidates")),
        "chunks": _int(acquisition.get("chunks")),
        "acq_seed": _int(acquisition.get("acq_seed")),
        "is_ranking_signal": True,
        "meaning": ACQUISITION_NOTE,
    }
    checks = _mapping(candidate.get("checks"))
    model_version = {
        "artifact_sha256": (model_meta or {}).get("sha256") if isinstance(model_meta, Mapping) else None,
        "artifact_revision": (model_meta or {}).get("revision") if isinstance(model_meta, Mapping) else None,
        "status": _mapping(model).get("status") or NOT_RECORDED,
        "policy": _mapping(model).get("policy") or proposal.get("proposal_policy") or policy,
        "generated_utc": _clip_text(_mapping(model).get("generated_utc"), 64),
        "library_versions": dict(_mapping(_mapping(model).get("library_versions"))),
        "hyperparameters_recorded": isinstance(_mapping(model).get("hyperparameters"), Mapping),
        "retrospective": False,
    }
    counts = _physical_counts(observations)
    analysis = "ready" if proposal.get("status") in (None, "ok") else str(proposal.get("status"))
    return _view(analysis, None,
                 policy=proposal.get("proposal_policy") or policy,
                 proposal_index=index if index is not None else NOT_RECORDED,
                 proposal_index_source=index_source if index is not None else NOT_RECORDED,
                 model_version=model_version,
                 model_provenance=_model_provenance(
                     model_meta, model, retrospective=False,
                     source="model/proposal artifacts recorded when the candidate was proposed"),
                 acquisition=acquisition_payload,
                 predicted=predicted,
                 predicted_objectives=(predicted.get("objectives")
                                       if isinstance(predicted, Mapping) else NOT_RECORDED),
                 selection_reason=_clip_text(selection_reason, 500) or NOT_RECORDED,
                 fallback=fallback,
                 designation=designation,
                 designation_values=list(DESIGNATION_VALUES),
                 nearest_training_designs=nearest,
                 cheap_check_feasibility={
                     "checks": dict(checks) if checks else NOT_RECORDED,
                     "status": _clip_text(candidate.get("status"), 300) or NOT_RECORDED,
                     "note": ("cheap checks only; mesh/acoustic eligibility is unknown until a "
                              "solve is measured"),
                 },
                 parameter_delta_vs_incumbent=delta,
                 active_vector_delta_vs_incumbent=vector_delta,
                 incumbent=({"j": incumbent["j"], "design_hash": incumbent.get("design_hash")}
                            if incumbent else NOT_RECORDED),
                 candidate_identity={"candidate_id": candidate.get("candidate_id"),
                                     "design_hash": candidate.get("design_hash"),
                                     "geometry_hash": candidate.get("geometry_hash")},
                 status_kinds=_status_kinds(analysis,
                                            artifact_status=_artifact_status(proposal_meta),
                                            physical=counts),
                 notes=["Acquisition values are ranking signals, not measured horn quality.",
                        "Predicted J is a model credible interval, never a measured result.",
                        "Designation is constrained to exploration, exploitation or fallback."])


def _scalar_target(value) -> dict | None:
    """Bounded JSON copy of a recorded resolved target (scalars and scalar lists only)."""
    if not isinstance(value, Mapping) or not value:
        return None
    out = {}
    for key, item in list(value.items())[:MAX_TABLE]:
        if not isinstance(key, str):
            continue
        if isinstance(item, bool):
            out[key] = item
        elif isinstance(item, (int, float)):
            out[key] = _finite(item)
        elif isinstance(item, str):
            out[key] = _clip_text(item, 200)
        elif isinstance(item, (list, tuple)) and len(item) <= MAX_SERIES:
            if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in item):
                out[key] = [_finite(v) for v in item]
    return out or None


def acoustic_target_integrity_view(service, study) -> dict:
    """The resolved scoring target recorded with the snapshot, never a typology guess."""
    sid = study["id"]
    snapshot, snapshot_meta, reason = _snapshot(service, sid)
    if snapshot is None:
        return _view("missing", reason or "snapshot artifact is not available",
                     scoring_target_available=False,
                     reason_code="scoring_target_unavailable", target=NOT_RECORDED,
                     objective_version=None,
                     note="no recorded scoring target; it is not derived from the typology name")
    task = _mapping(snapshot.get("task"))
    target = _scalar_target(task.get("resolved_target"))
    objective_version = _int(task.get("objective_version"))
    identity = {
        "objective_version": objective_version,
        "brief_name": _clip_text(task.get("brief_name"), 200),
        "brief_sha256": _clip_text(task.get("brief_sha256"), 80),
        "config_name": _clip_text(task.get("config_name"), 200),
        "config_sha256": _clip_text(task.get("config_sha256"), 80),
    }
    if target is None:
        return _view("missing", "scoring target unavailable",
                     scoring_target_available=False,
                     reason_code="scoring_target_unavailable", target=NOT_RECORDED,
                     target_identity=identity,
                     source="snapshot.task.resolved_target",
                     status_kinds=_status_kinds("missing",
                                                artifact_status=_artifact_status(snapshot_meta),
                                                physical=NOT_RECORDED),
                     note=("the resolved target the scorer used was not recorded; it is not "
                           "fabricated from the typology/family name"))
    return _view("ready", None,
                 scoring_target_available=True, target=target,
                 target_identity=identity,
                 source="snapshot.task.resolved_target (the target the scorer actually used)",
                 separate_from_measurements=True,
                 labels={
                     "target": "scoring target used by the objective",
                     "measured": "measured response curves (kept separate)",
                     "tolerance": "tolerance region (kept separate when recorded)",
                 },
                 status_kinds=_status_kinds("ready",
                                            artifact_status=_artifact_status(snapshot_meta),
                                            physical=NOT_RECORDED),
                 notes=["Targets are the scorer's resolved values, never a typology-based guess.",
                        "Actual curves, target curves and tolerance regions stay separately "
                        "legend-labelled."])


def design_space_view(service, study) -> dict:
    sid = study["id"]
    training, reason = _training_arrays(service, sid)
    manifest, _meta, _reason = _manifest(service, sid)
    points = []
    rows = []
    if training is not None:
        X, J = training["X"], training["J"]
        for index in range(min(len(X), MAX_POINTS)):
            rows.append((X[index], float(J[index]), "training", None))
    results, _meta, _reason = _results(service, sid)
    for row in _observations(results):
        candidate = _mapping(row.get("candidate"))
        result = _mapping(row.get("result"))
        vector = candidate.get("x") or candidate.get("active_vector")
        if not isinstance(vector, list) or not vector:
            continue
        j = _finite(result.get("observed_j"))
        if j is None:
            continue
        rows.append((np.asarray(vector, dtype=float), j, "screen",
                     candidate.get("design_hash")))
    if len(rows) < 3:
        return _view("missing", reason or "Not enough design vectors for a projection.")
    try:
        X = np.vstack([np.asarray(vector, dtype=float).reshape(-1) for vector, _j, _s, _h in rows])
    except ValueError:
        return _view("missing", "Design vectors have inconsistent dimensions.")
    if X.ndim != 2 or not np.isfinite(X).all():
        return _view("missing", "Design vectors are not finite.")
    centered = X - X.mean(axis=0)
    try:
        _u, singular, vt = np.linalg.svd(centered, full_matrices=False)
    except np.linalg.LinAlgError:
        return _view("missing", "Design projection failed.")
    coords = centered @ vt[:2].T if vt.shape[0] >= 2 else np.column_stack(
        [centered[:, 0], np.zeros(len(centered))])
    total = float(np.sum(singular ** 2)) or 1.0
    explained = [round(float(v) / total, 4) for v in (singular[:2] ** 2)]
    for index, (vector, j, source, design) in enumerate(rows):
        points.append({"x": round(float(coords[index, 0]), 6),
                       "y": round(float(coords[index, 1]), 6),
                       "j": round(float(j), 8), "source": source,
                       "design_hash": design})
    status = "ready" if training is not None else "partial"
    return _view(status, None, points=points[:MAX_POINTS], explained=explained,
                 active_keys=_active_keys(manifest),
                 notes=["2-D PCA of the encoded training/proposal vectors; axes are not acoustic."])


def data_summary_view(service, study, *, runs_root=None) -> dict:
    sid = study["id"]
    snapshot, snapshot_meta, reason = _snapshot(service, sid)
    manifest, manifest_meta, _reason = _manifest(service, sid)
    budget = _budget(service, sid)
    paths = _run_paths(runs_root, service, sid) if runs_root is not None else {}
    if snapshot is None and manifest is None:
        return _view("missing", reason or "No snapshot or training manifest is available.")
    snapshot_map = _mapping(snapshot)
    manifest_map = _mapping(manifest)
    source = _mapping(snapshot_map.get("source"))
    cohort = _mapping(snapshot_map.get("cohort"))
    scores = _mapping(cohort.get("scores"))
    subset = _mapping(manifest_map.get("subset_policy"))
    return _view("ready", None,
                 objective_version=_objective_version(manifest),
                 training={"n": manifest_map.get("n"),
                           "n_min": manifest_map.get("n_min"),
                           "n_max": manifest_map.get("n_max"),
                           "n_eligible": manifest_map.get("n_eligible"),
                           "active_keys": _active_keys(manifest),
                           "subset_policy": _clip_text(subset.get("rule"), 500) if subset else None,
                           "excluded_ids": len(manifest_map.get("excluded_ids") or ()),
                           "sources": {k: _clip_text(v, 300) for k, v in source.items()
                                       if k in ("scores_json", "catalog_csv", "dataset_root")}},
                 cohort={"records": scores.get("records"), "ok": scores.get("ok"),
                         "failed": scores.get("failed")},
                 budget=budget.get("budget"), budget_profile=budget.get("budget_profile"),
                 run_id=paths.get("run_id"),
                 status_kinds=_status_kinds(
                     "ready",
                     artifact_status=(_artifact_status(snapshot_meta)
                                      if _artifact_status(snapshot_meta) != NOT_RECORDED
                                      else _artifact_status(manifest_meta)),
                     physical=NOT_RECORDED),
                 notes=["Excluded rows are listed by id in the training manifest; no row is filled."])


def verification_view(service, study) -> dict:
    sid = study["id"]
    verification, verification_meta, reason = _verification(service, sid)
    if verification is None:
        return _view("missing", reason or "No verification artifact is recorded.")
    selection = _mapping(verification.get("selection"))
    verified = list(verification.get("verified_geometry_ids") or ())
    return _view("ready", None,
                 finalists=list(selection.get("finalists") or ())[:MAX_TABLE],
                 audits=list(selection.get("audits") or ())[:MAX_TABLE],
                 verified_geometry_ids=verified[:MAX_TABLE],
                 shortfall=selection.get("shortfall"), audit_shortfall=selection.get("audit_shortfall"),
                 artifact_status=verification.get("status"),
                 status_kinds=_status_kinds(
                     "ready", artifact_status=_artifact_status(verification_meta),
                     physical=(f"verified:{len(verified)}" if verified else NOT_RECORDED)))


# --------------------------------------------------------------------------- comparison specs


def load_comparison_specs(root) -> list[dict]:
    """List declarative comparison specs under ``tools/analysis/specs/bo_*.yaml``."""
    specs_dir = Path(root) / "tools" / "analysis" / "specs"
    out = []
    if not specs_dir.is_dir():
        return out
    for path in sorted(specs_dir.glob("bo_*.yaml")):
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(payload, Mapping):
            continue
        out.append({"name": path.stem, "label": payload.get("name") or path.stem,
                    "path": path.name, "spec": payload})
    return out


def find_comparison_spec(root, study_root: Path | None) -> dict | None:
    if root is None or study_root is None:
        return None
    try:
        resolved = Path(study_root).resolve()
    except OSError:
        return None
    for item in load_comparison_specs(root):
        for arm in item["spec"].get("arms") or ():
            if not isinstance(arm, Mapping) or not arm.get("study_root"):
                continue
            candidate = Path(root) / str(arm["study_root"])
            try:
                if candidate.resolve() == resolved:
                    return item["spec"]
            except OSError:
                continue
    return None


def method_board_view(spec: Mapping, *, root, runs_root, service_for) -> dict:
    """Render one declarative comparison spec from recorded rows only."""
    if not isinstance(spec, Mapping) or not isinstance(spec.get("arms"), list):
        raise ValueError("comparison spec requires an arms list")
    runs_root = Path(runs_root)
    target = _finite(spec.get("target_j"))
    arms = []
    for arm in spec["arms"][:MAX_TABLE]:
        if not isinstance(arm, Mapping):
            continue
        arm_id = str(arm.get("id") or "")
        method = str(arm.get("method") or "unknown")
        run_dir = None
        verify_dir = None
        rows = []
        verify_rows = []
        study_id = None
        if arm.get("study_root"):
            try:
                _rid, service = service_for(Path(root) / str(arm["study_root"]))
                study_id = str(arm["study_id"]) if arm.get("study_id") else None
                if study_id is None:
                    studies = service.list_studies(limit=2)
                    if len(studies) == 1:
                        study_id = studies[0]["id"]
                if study_id is not None:
                    paths = _run_paths(runs_root, service, study_id)
                    run_dir = paths["run_dir"]
                    verify_dir = paths["verify_dir"]
                    results, _meta, _reason = _results(service, study_id)
                    for row in _observations(results):
                        result = _mapping(row.get("result"))
                        if result.get("kind") == "screen" and result.get("eligible") is True:
                            rows.append({"ok": True, "objective": result.get("observed_j")})
                        elif result.get("kind") == "verify":
                            verify_rows.append({"ok": result.get("observed_j") is not None,
                                                "objective": result.get("observed_j")})
            except Exception:  # noqa: BLE001 - a missing arm is a board state
                pass
        arm_dir = _resolve_arm_dir(runs_root, arm)
        if arm_dir is not None:
            run_dir = arm_dir
            rows = _screen_rows(run_dir)
            verify_rows = _verify_rows(run_dir)
        if not rows and run_dir is not None:
            rows = _screen_rows(run_dir)
        if run_dir is not None:
            run_verify = _verify_rows(run_dir)
            if run_verify:
                verify_rows = run_verify
        series = _run_series(rows)
        best_verify = _best_verify(verify_rows)
        arms.append({
            "id": arm_id, "label": _clip_text(arm.get("label") or arm_id, 120),
            "method": method, "policy": _clip_text(arm.get("policy"), 40),
            "budget_profile": arm.get("budget_profile"),
            "screens": len(rows), "verify": len(verify_rows),
            "best_screen_j": series["best_j"], "best_verify_j": best_verify,
            "screens_to_target": _screens_to_target(rows, target),
            "complete": best_verify is not None,
            "run_id": run_dir.name if run_dir is not None else None,
            "study_id": study_id,
        })
    groups: dict[str, list[dict]] = {}
    for arm in arms:
        groups.setdefault(arm["method"], []).append(arm)
    stats = {}
    for method, items in groups.items():
        values = [a["best_verify_j"] for a in items if a["best_verify_j"] is not None]
        screens = [a["screens_to_target"] for a in items if a["screens_to_target"] is not None]
        stats[method] = {
            "n": len(items), "n_verified": len(values),
            "median_verify_j": round(float(np.median(values)), 6) if values else None,
            "seed_spread": round(max(values) - min(values), 6) if len(values) >= 2 else None,
            "median_screens_to_target": round(float(np.median(screens)), 3) if screens else None,
        }
    comparisons = []
    for item in spec.get("comparisons") or ():
        if not isinstance(item, Mapping):
            continue
        a, b = item.get("a"), item.get("b")
        rule = item.get("rule") or "verify_median_gap_exceeds_spread"
        entry = {"id": item.get("id"), "a": a, "b": b, "rule": rule,
                 "status": "incomplete", "verdict": "incomplete", "reason": None}
        if rule == "verify_median_gap_exceeds_spread":
            sa, sb = stats.get(str(a)), stats.get(str(b))
            if not sa or not sb or sa["median_verify_j"] is None or sb["median_verify_j"] is None:
                missing = [str(name) for name, stat in ((a, sa), (b, sb))
                           if not stat or stat.get("median_verify_j") is None]
                entry["reason"] = f"No measured verify J yet for: {', '.join(missing) or 'both methods'}."
            elif sa["n_verified"] < 2 or sb["n_verified"] < 2:
                entry["reason"] = "Both methods need at least two verified arms for a seed spread."
            else:
                gap = abs(sa["median_verify_j"] - sb["median_verify_j"])
                spread = max(sa["seed_spread"] or 0.0, sb["seed_spread"] or 0.0)
                entry.update({"status": "ready", "gap": round(gap, 6),
                              "spread": round(spread, 6),
                              "verdict": ("inconclusive" if gap <= spread else
                                          (str(a) if sa["median_verify_j"] < sb["median_verify_j"] else str(b)))})
                entry["reason"] = ("gap exceeds the larger seed spread" if gap > spread
                                   else "gap does not exceed the larger seed spread")
        elif rule == "hypervolume":
            entry["reason"] = "Hypervolume comparison needs measured metric rows for both methods."
        comparisons.append(entry)
    return _view("ready" if arms else "missing", None, name=spec.get("name"),
                 objective_version=_int(spec.get("objective_version")),
                 target_j=target, incumbent=spec.get("incumbent"),
                 arms=arms, methods=stats, comparisons=comparisons,
                 notes=["Screen J is reported but does not decide; the pre-declared rule does."])


# --------------------------------------------------------------------------- aggregator


def bo_views(service, study, *, phase: str, runs_root=None, root=None) -> dict:
    """Return the phase-relevant BO view bundle; never raise for a single failed view."""
    if phase not in PHASE_VIEWS:
        return _view("missing", "unknown study phase")
    runners = {
        "run": lambda: _run_links(service, study, runs_root),
        "data_summary": lambda: data_summary_view(service, study, runs_root=runs_root),
        "target_integrity": lambda: acoustic_target_integrity_view(service, study),
        "design_space": lambda: design_space_view(service, study),
        "calibration": lambda: calibration_view(service, study),
        "sensitivity": lambda: sensitivity_view(service, study),
        "proposal_explanation": lambda: proposal_explanation_view(service, study, runs_root=runs_root),
        "convergence": lambda: convergence_view(service, study, runs_root=runs_root, root=root),
        "trust_region": lambda: trust_region_view(service, study),
        "pareto": lambda: pareto_view(service, study, runs_root=runs_root),
        "verification": lambda: verification_view(service, study),
    }
    views: dict[str, Any] = {"phase": phase}
    for name in PHASE_VIEWS[phase]:
        try:
            views[name] = runners[name]()
        except Exception as exc:  # noqa: BLE001 - one view must not break the panel
            views[name] = _view("failed", f"{type(exc).__name__}: {exc}")
    bounded, count = bounded_preview(views, max_bytes=MAX_BYTES - 16_000)
    if not isinstance(bounded, Mapping):
        return _view("failed", "BO view bundle exceeded the bounded panel size")
    result: dict[str, Any] = dict(bounded)
    if count:
        result["_truncated"] = count
    return result


def _run_links(service, study, runs_root) -> dict:
    sid = study["id"]
    if runs_root is None:
        return _view("missing", "run root is not configured")
    paths = _run_paths(runs_root, service, sid)
    budget = _budget(service, sid)
    if paths["run_id"] is None:
        return _view("missing", "no prepared package is recorded")
    run_id = paths["run_id"]
    package_meta = service.get_artifact_metadata(sid, "package")
    run_dir = paths["run_dir"]
    has_screen = bool(run_dir and ((run_dir / "screen" / "search.ndjson").is_file()
                                   or (run_dir / "search.ndjson").is_file()))
    return _view("ready", None,
                 run_id=run_id,
                 has_screen=has_screen,
                 has_verify=bool(paths["verify_dir"] and (paths["verify_dir"] / "search.ndjson").is_file()),
                 package_id=package_meta.get("sha256") if package_meta.get("status") == "available" else None,
                 budget=budget.get("budget"), budget_profile=budget.get("budget_profile"),
                 lane=budget.get("lane"), deadline=budget.get("deadline"))


__all__ = [
    "ACQUISITION_NOTE", "DESIGNATION_VALUES", "MODEL_SENSITIVITY_NOTE", "NOT_RECORDED",
    "PHASE_VIEWS", "SLICE_ANCHOR_NOTE", "acoustic_target_integrity_view", "bo_views",
    "calibration_view", "convergence_view", "data_summary_view", "design_space_view",
    "find_comparison_spec", "load_comparison_specs", "method_board_view",
    "model_performance_view", "pareto_view", "proposal_explanation_view", "sensitivity_view",
    "trust_region_view", "verification_view",
]
