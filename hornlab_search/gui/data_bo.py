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

PHASE_VIEWS = {
    "overview": ("run",),
    "data": ("run", "data_summary", "design_space"),
    "explain": ("run", "calibration", "sensitivity", "design_space"),
    "propose": ("run",),
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


def _diagnostics(service, study_id):
    """The optional ``diagnostics`` artifact; ``(content_or_None, can_compute)``."""
    content, _meta, _reason = _artifact(service, study_id, "diagnostics", max_bytes=1_000_000)
    if isinstance(content, Mapping) and content.get("schema") == "study-model-diagnostics-v1" \
            and content.get("status", "ok") == "ok":
        return content, True
    arrays, _why = _training_arrays(service, study_id)
    return None, arrays is not None


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
    results, _meta, reason = _results(service, sid)
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
                 notes=notes)


def _calibration_core(service, study) -> dict:
    sid = study["id"]
    results, _meta, reason = _results(service, sid)
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


def calibration_view(service, study) -> dict:
    """Predicted-vs-measured half plus, when diagnosed, a "LOO on training data" half."""
    view = _calibration_core(service, study)
    diag, can_compute = _diagnostics(service, study["id"])
    loo = _mapping(diag.get("loo")) if diag else {}
    rows = loo.get("rows") if isinstance(loo.get("rows"), list) else []
    if diag and rows:
        clean = []
        for row in rows[:400]:
            row = _mapping(row)
            obs, mean, sd = _finite(row.get("j_obs")), _finite(row.get("j_mean")), _finite(row.get("j_sd"))
            if obs is None or mean is None:
                continue
            clean.append({"id": _clip_text(row.get("id"), 80), "j_obs": obs, "j_mean": mean, "j_sd": sd})
        view["loo"] = {"available": True, "n": len(clean), "rows": clean,
                       "truncated": bool(loo.get("truncated")),
                       "summary": dict(_mapping(loo.get("summary"))),
                       "method": _clip_text(loo.get("method"), 300)}
        if view.get("status") == "missing":
            view["status"] = "partial"
            view.pop("reason", None)
    else:
        view["loo"] = {"available": False, "can_compute": bool(can_compute)}
    return view


def sensitivity_view(service, study) -> dict:
    view = _sensitivity_core(service, study)
    diag, can_compute = _diagnostics(service, study["id"])
    per_key = _mapping(_mapping(diag.get("slices")).get("per_key")) if diag else {}
    if not per_key:
        view["diagnostics"] = {"available": False, "can_compute": bool(can_compute)}
        return view
    slices = []
    for key, item in list(per_key.items())[:24]:
        item = _mapping(item)
        xs, ms, sds = (item.get(k) for k in ("x", "j_mean", "j_sd"))
        if not (isinstance(xs, list) and isinstance(ms, list) and isinstance(sds, list)
                and len(xs) == len(ms) == len(sds) and 2 <= len(xs) <= 100):
            continue
        slices.append({"key": _clip_text(key, 80), "x": [_finite(v) for v in xs],
                       "j_mean": [_finite(v) for v in ms], "j_sd": [_finite(v) for v in sds],
                       "anchor_x": _finite(item.get("anchor_x")), "unit": item.get("unit") or item.get("x_unit")})
    view["diagnostics"] = {"available": bool(slices), "can_compute": bool(can_compute),
                           "anchor": _clip_text(_mapping(diag.get("slices")).get("anchor"), 80),
                           "grid_n": _int(_mapping(diag.get("slices")).get("grid_n"))}
    view["slices"] = slices
    if view.get("status") == "missing":
        relevance = [r for r in (diag.get("relevance") or []) if isinstance(r, Mapping)]
        total = sum(_finite(r.get("inv_lengthscale")) or 0.0 for r in relevance)
        if total > 0:
            view["knobs"] = [{"key": _clip_text(r.get("key"), 80),
                              "lengthscale": None,
                              "importance": round((_finite(r.get("inv_lengthscale")) or 0.0) / total, 6)}
                             for r in relevance[:MAX_TABLE]]
            view["status"] = "partial"
            view.pop("reason", None)
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
    results, _meta, reason = _results(service, sid)
    proposal, _meta, _reason = _proposal(service, sid)
    records = []
    if isinstance(proposal, Mapping) and isinstance(proposal.get("trust_region"), Mapping):
        records.append(proposal["trust_region"])
    for row in _observations(results):
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
    if not records:
        return _view("missing", reason or "No trust-region state is recorded for this run.",
                     policy=policy)
    series = []
    latest = None
    for index, record in enumerate(records):
        state = _mapping(record.get("state_after"))
        length = _finite(state.get("length"))
        if length is not None:
            series.append([index, length])
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
    return _view("ready", None, policy=policy, length_series=series,
                 length_bounds=state.get("length_bounds"),
                 active_keys=_active_keys(manifest),
                 success_counter=_int(state.get("success_counter")),
                 failure_counter=_int(state.get("failure_counter")),
                 iteration=_int(state.get("iteration")),
                 box={"lo": box.get("lo"), "hi": box.get("hi"), "weights": box.get("weights")}
                 if box else None,
                 terminal={"collapsed": bool(collapsed),
                           "reason": state.get("terminal_reason")},
                 budget={"used": screens, "total": total},
                 notes=["A collapsed box means converged, not failed. Unspent budget is reported."])


def pareto_view(service, study, *, runs_root=None) -> dict:
    policy = _policy(study)
    if policy != "pareto":
        return _view("not_applicable", f"Current policy is {policy}; the frontier applies to pareto only.",
                     policy=policy)
    sid = study["id"]
    payload, _meta, reason = _pareto_metrics(service, sid)
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
    if not points:
        return _view("partial", "No measured coverage/ripple rows are available yet.",
                     reference=reference, notes=[payload.get("reference_policy")])
    if reference is not None:
        _nondominated(points)
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
    diag, can_compute = _diagnostics(service, sid)
    diag_pareto = _mapping(diag.get("pareto")) if diag else {}
    front_ids = [str(x) for x in diag_pareto.get("front_ids", [])[:MAX_POINTS]] \
        if isinstance(diag_pareto.get("front_ids"), list) else None
    hv_trace = [[_int(r.get("seq")), _finite(r.get("hv"))] for r in diag_pareto.get("hv_trace", [])[:MAX_SERIES]
                if isinstance(r, Mapping)] if isinstance(diag_pareto.get("hv_trace"), list) else None
    diagnostics = ({"available": True, "front_ids": front_ids, "hv_trace": hv_trace}
                   if front_ids is not None or hv_trace is not None
                   else {"available": False, "can_compute": bool(can_compute)})
    return _view(status, None, reference=reference, points=points, hypervolume=hv, diagnostics=diagnostics,
                 n_complete=_int(payload.get("n_complete")), n_excluded=_int(payload.get("n_excluded")),
                 predicted=predicted[:MAX_TABLE], metric_policy=payload.get("metric_policy"),
                 run_id=paths.get("run_id"),
                 notes=notes)


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
    snapshot, _meta, reason = _snapshot(service, sid)
    manifest, _meta, _reason = _manifest(service, sid)
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
                 notes=["Excluded rows are listed by id in the training manifest; no row is filled."])


def verification_view(service, study) -> dict:
    sid = study["id"]
    verification, _meta, reason = _verification(service, sid)
    if verification is None:
        return _view("missing", reason or "No verification artifact is recorded.")
    selection = _mapping(verification.get("selection"))
    return _view("ready", None,
                 finalists=list(selection.get("finalists") or ())[:MAX_TABLE],
                 audits=list(selection.get("audits") or ())[:MAX_TABLE],
                 verified_geometry_ids=list(verification.get("verified_geometry_ids") or ())[:MAX_TABLE],
                 shortfall=selection.get("shortfall"), audit_shortfall=selection.get("audit_shortfall"),
                 artifact_status=verification.get("status"))


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
        "design_space": lambda: design_space_view(service, study),
        "calibration": lambda: calibration_view(service, study),
        "sensitivity": lambda: sensitivity_view(service, study),
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
    "PHASE_VIEWS", "bo_views", "calibration_view", "convergence_view", "data_summary_view",
    "design_space_view", "find_comparison_spec", "load_comparison_specs", "method_board_view",
    "pareto_view", "sensitivity_view", "trust_region_view", "verification_view",
]
