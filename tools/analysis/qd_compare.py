"""Manifest-driven, equal-cost QD vs Pareto hypervolume comparison.

This is an offline reporting tool.  It never runs an optimiser or solver and never
reconstructs failures as acoustic observations.  Each arm supplies every attempted
result plus disjoint successful / failed / refused / training / other costs.  The
comparison is refused unless both arms declare the same total cost, raw objective
axes, frozen hypervolume reference, and scoring/task/spec identity.

Manifest schema (``qd-compare-arm-v1``)::

    {
      "schema": "qd-compare-arm-v1", "arm_id": "cma_me", "algorithm": "cma_me",
      "identity": {"objective_version": 4, "scoring_context_id": "...",
                   "task_id": "...", "spec_id": "...", "brief_id": "...",
                   "family": "OSSE", "weights": {"cov": 1.0},
                   "tolerances": {"cov": 0.05}},
      "axes": [{"name": "coverage_error_deg", "unit": "deg", "direction": "minimize"},
               {"name": "ripple_db", "unit": "dB", "direction": "minimize"}],
      "frozen_reference": [30.0, 6.0],
      "descriptor_space": {"names": ["mouth_aspect", "area_ratio"],
                           "ranges": [[0.25, 4.0], [1.0, 500.0]],
                           "reconstruction_hash": "archive-input-sha256"},
      "cost": {"unit": "equivalent_evaluations", "successful": 3, "failed": 1,
               "refused": 0, "training": 2, "other": 0, "total": 6,
               "checkpoints": [{"label": "final", "after_results": 4,
                 "successful": 3, "failed": 1, "refused": 0, "training": 2,
                 "other": 0, "total": 6}]},
      "results": [{"id": "attempt-id", "design_hash": "physical-design-id",
                   "reconstruction_hash": "geometry-input-sha256",
                   "objectives": [10.0, 2.0], "error": "", "terms": {}}]
    }

``error`` and ``terms`` are passed through the same typed outcome classifier used by
``search/cma_me.py``.  Thus measured gates remain eligible, while deterministic
refusals and infrastructure/metric/unknown failures cannot enter the front.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from hornlab_search.search.nsga import fast_nondominated_sort
from hornlab_search.search.outcomes import DETERMINISTIC_CATEGORIES, classify
from hornlab_search.types import Design, Evaluation

from _common import add_out_arg, fail, write_report

TOOL = "qd_compare"
SCHEMA = "qd-compare-arm-v1"
IDENTITY_KEYS = ("objective_version", "scoring_context_id", "task_id", "spec_id",
                 "brief_id", "family", "weights", "tolerances")
COST_KEYS = ("successful", "failed", "refused", "training", "other")
_SCALAR_AXIS_NAMES = {"j", "objective", "objective_j", "scalar_score", "score"}
REPO = Path(__file__).resolve().parents[2]
_FORBIDDEN_OUTPUT_ROOTS = tuple(REPO / name for name in
                                ("runs", "dataset", "dataset_cpu", "cache", "cache_cpu"))


def _read_manifest(path: Path) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise fail(f"qd_compare: cannot read manifest {path}: {exc}") from None
    if not isinstance(value, dict):
        raise fail(f"qd_compare: manifest {path} must be a JSON object")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise fail(f"qd_compare: {label} must be a non-negative integer")
    return int(value)


def _canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), 9)
    return value


def reconstruction_hash(design: dict) -> str:
    """Full SHA-256 of the same canonical family/params payload used by ``Design.hash``."""
    blob = json.dumps(_canonical(design), sort_keys=True, separators=(",", ":"), default=float)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _manifest_hash(manifest: dict) -> str:
    blob = json.dumps(manifest, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _guard_out(path: Path) -> None:
    resolved = Path(path).resolve()
    for root in _FORBIDDEN_OUTPUT_ROOTS:
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            continue
        raise fail(f"qd_compare: --out may not write into live {root.name}/")


def _paused_meh(design: dict) -> bool:
    family = str(design.get("family") or "").lower()
    params = design.get("params") if isinstance(design.get("params"), dict) else {}
    if family == "meh" or "mid_ports" in params:
        return True
    for key, value in params.items():
        key_l, value_l = str(key).lower(), str(value).lower()
        if "mid_ports" in key_l or "mini_meh" in value_l or value_l == "meh":
            return True
        if "cad" in key_l and "meh" in value_l:
            return True
    return False


def _outcome(row: dict) -> Any:
    """Classify a manifest row through the production CMA/QD F1 outcome API."""
    ev = Evaluation(
        design_hash=str(row.get("id") or "manifest-row"),
        design=Design(family=row["design"]["family"], params=row["design"]["params"]),
        mesh_hash="manifest", solve_hash="manifest", objective=0.0,
        terms=(row.get("terms") if isinstance(row.get("terms"), dict) else {}),
        metrics=None, mesh=None, outcome=None, cached=False,
        error=(str(row.get("error") or "") if row["ok"] else
               str(row.get("error") or "unknown: manifest row marked ok=false without error")),
    )
    return classify(ev)


def _validate_manifest(manifest: dict, source: str) -> dict:
    if manifest.get("schema") != SCHEMA:
        raise fail(f"qd_compare: {source} schema must be {SCHEMA!r}")
    arm_id = manifest.get("arm_id")
    algorithm = manifest.get("algorithm")
    if not isinstance(arm_id, str) or not arm_id.strip():
        raise fail(f"qd_compare: {source} needs a non-empty arm_id")
    if not isinstance(algorithm, str) or not algorithm.strip():
        raise fail(f"qd_compare: {source} needs a non-empty algorithm")

    identity = manifest.get("identity")
    if not isinstance(identity, dict):
        raise fail(f"qd_compare: {source} needs an identity object")
    if isinstance(identity.get("objective_version"), bool) or not isinstance(
            identity.get("objective_version"), int):
        raise fail(f"qd_compare: {source} identity.objective_version must be an integer")
    for key in ("scoring_context_id", "task_id", "spec_id", "brief_id", "family"):
        if not isinstance(identity.get(key), str) or not identity[key].strip():
            raise fail(f"qd_compare: {source} identity.{key} must be a non-empty string")
    for key in ("weights", "tolerances"):
        block = identity.get(key)
        if not isinstance(block, dict):
            raise fail(f"qd_compare: {source} identity.{key} must be an object")
        for name, value in block.items():
            if not isinstance(name, str) or not name or isinstance(value, bool):
                raise fail(f"qd_compare: {source} identity.{key} has an invalid entry")
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                raise fail(f"qd_compare: {source} identity.{key}.{name} must be finite") from None
            if not math.isfinite(numeric):
                raise fail(f"qd_compare: {source} identity.{key}.{name} must be finite")
    if str(identity["family"]).upper() == "MEH":
        raise fail("qd_compare: family MEH is paused and is refused")

    axes = manifest.get("axes")
    if not isinstance(axes, list) or len(axes) != 2:
        raise fail(f"qd_compare: {source} needs exactly two raw acoustic axes")
    clean_axes = []
    for i, axis in enumerate(axes):
        if not isinstance(axis, dict):
            raise fail(f"qd_compare: {source} axis {i} must be an object")
        name, unit, direction = axis.get("name"), axis.get("unit"), axis.get("direction")
        if not isinstance(name, str) or not name.strip() or not isinstance(unit, str) or not unit.strip():
            raise fail(f"qd_compare: {source} axis {i} needs non-empty name and unit")
        if name.strip().lower() in _SCALAR_AXIS_NAMES or unit.strip().lower() == "j":
            raise fail("qd_compare: scalar J/score is not a Pareto or hypervolume axis")
        if direction != "minimize":
            raise fail(f"qd_compare: {source} axis {i} direction must be 'minimize'")
        clean_axes.append({"name": name.strip(), "unit": unit.strip(), "direction": direction})

    try:
        reference = np.asarray(manifest.get("frozen_reference"), dtype=float)
    except (TypeError, ValueError):
        raise fail(f"qd_compare: {source} frozen_reference must be two finite values") from None
    if reference.shape != (2,) or not np.isfinite(reference).all():
        raise fail(f"qd_compare: {source} frozen_reference must be two finite values")

    descriptor_space = manifest.get("descriptor_space")
    if not isinstance(descriptor_space, dict):
        raise fail(f"qd_compare: {source} needs a frozen descriptor_space")
    descriptor_names = descriptor_space.get("names")
    descriptor_ranges = descriptor_space.get("ranges")
    archive_reconstruction_hash = descriptor_space.get("reconstruction_hash")
    if (not isinstance(descriptor_names, list) or len(descriptor_names) != 2
            or any(not isinstance(v, str) or not v.strip() for v in descriptor_names)
            or len(set(descriptor_names)) != 2):
        raise fail(f"qd_compare: {source} descriptor_space.names needs two unique names")
    try:
        ranges = np.asarray(descriptor_ranges, dtype=float)
    except (TypeError, ValueError):
        raise fail(f"qd_compare: {source} descriptor_space.ranges must be 2x2 finite ranges") from None
    if (ranges.shape != (2, 2) or not np.isfinite(ranges).all()
            or bool(np.any(ranges[:, 1] <= ranges[:, 0]))):
        raise fail(f"qd_compare: {source} descriptor_space.ranges must be 2x2 finite lo<hi ranges")
    if not isinstance(archive_reconstruction_hash, str) or not archive_reconstruction_hash.strip():
        raise fail(f"qd_compare: {source} descriptor_space.reconstruction_hash is required")

    cost = manifest.get("cost")
    if not isinstance(cost, dict) or not isinstance(cost.get("unit"), str) or not cost["unit"].strip():
        raise fail(f"qd_compare: {source} needs cost.unit")
    if cost["unit"] != "equivalent_evaluations":
        raise fail(f"qd_compare: {source} cost.unit must be 'equivalent_evaluations'; "
                   "integer attempt equivalents are not elapsed time")
    counts = {key: _nonnegative_int(cost.get(key), f"{source} cost.{key}") for key in COST_KEYS}
    total = _nonnegative_int(cost.get("total"), f"{source} cost.total")
    if total != sum(counts.values()):
        raise fail(f"qd_compare: {source} cost.total must equal successful + failed + "
                   "refused + training + other")

    results = manifest.get("results")
    if not isinstance(results, list):
        raise fail(f"qd_compare: {source} results must be a list")
    seen: set[str] = set()
    designs: dict[str, dict] = {}
    eligible_rows, excluded_rows = [], []
    categories: dict[str, int] = {}
    for i, row in enumerate(results):
        if not isinstance(row, dict):
            raise fail(f"qd_compare: {source} result {i} must be an object")
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip() or row_id in seen:
            raise fail(f"qd_compare: {source} result {i} needs a unique non-empty id")
        seen.add(row_id)
        if not isinstance(row.get("ok"), bool):
            raise fail(f"qd_compare: {source} result {row_id!r} ok must be a strict boolean")
        if row["ok"] and str(row.get("error") or ""):
            raise fail(f"qd_compare: {source} result {row_id!r} cannot be ok=true with an error")
        design_payload = row.get("design")
        if (not isinstance(design_payload, dict)
                or not isinstance(design_payload.get("family"), str)
                or not isinstance(design_payload.get("params"), dict)):
            raise fail(f"qd_compare: {source} result {row_id!r} needs design.family and design.params")
        if design_payload["family"] != identity["family"]:
            raise fail(f"qd_compare: {source} result {row_id!r} family differs from identity")
        if _paused_meh(design_payload):
            raise fail(f"qd_compare: result {row_id!r} contains paused MEH/mid_ports/CAD-MEH input")
        design_hash = row.get("design_hash")
        row_reconstruction = row.get("reconstruction_hash")
        if not isinstance(design_hash, str) or not design_hash.strip():
            raise fail(f"qd_compare: {source} result {row_id!r} needs design_hash")
        if not isinstance(row_reconstruction, str) or not row_reconstruction.strip():
            raise fail(f"qd_compare: {source} result {row_id!r} needs reconstruction_hash")
        try:
            rebuilt_design = Design(family=design_payload["family"], params=design_payload["params"])
        except (TypeError, ValueError) as exc:
            raise fail(f"qd_compare: {source} result {row_id!r} invalid design: {exc}") from None
        if rebuilt_design.hash() != design_hash:
            raise fail(f"qd_compare: {source} result {row_id!r} design_hash does not match Design.hash()")
        expected_reconstruction = reconstruction_hash(
            {"family": design_payload["family"], "params": design_payload["params"]})
        if row_reconstruction != expected_reconstruction:
            raise fail(f"qd_compare: {source} result {row_id!r} reconstruction_hash mismatch")
        outcome = _outcome(row)
        categories[outcome.category] = categories.get(outcome.category, 0) + 1
        try:
            objectives = np.asarray(row.get("objectives"), dtype=float)
        except (TypeError, ValueError):
            objectives = np.asarray([], dtype=float)
        finite_pair = objectives.shape == (2,) and bool(np.isfinite(objectives).all())
        if outcome.strict_tell_eligible and not finite_pair:
            raise fail(f"qd_compare: eligible result {row_id!r} needs two finite objectives")
        record = {"id": row_id, "design_hash": design_hash,
                  "reconstruction_hash": row_reconstruction, "category": outcome.category,
                  "objectives": objectives.tolist() if finite_pair else None}
        prior = designs.get(design_hash)
        if prior is not None and prior["reconstruction_hash"] != row_reconstruction:
            raise fail(f"qd_compare: duplicate design_hash {design_hash!r} has conflicting "
                       "reconstruction hashes")
        if prior is None:
            designs[design_hash] = record
        (eligible_rows if outcome.strict_tell_eligible else excluded_rows).append(record)

    n_refused = sum(categories.get(name, 0) for name in DETERMINISTIC_CATEGORIES)
    n_success = len(eligible_rows)
    n_failed = len(results) - n_success - n_refused
    observed = {"successful": n_success, "failed": n_failed, "refused": n_refused}
    for key, value in observed.items():
        if counts[key] != value:
            raise fail(f"qd_compare: {source} cost.{key}={counts[key]} but results classify as {value}")
    if len(results) != counts["successful"] + counts["failed"] + counts["refused"]:
        raise fail(f"qd_compare: {source} results must include every attempted result")

    checkpoints = cost.get("checkpoints")
    if not isinstance(checkpoints, list) or not checkpoints:
        raise fail(f"qd_compare: {source} cost.checkpoints must be a non-empty list")
    clean_checkpoints = []
    previous = {key: 0 for key in (*COST_KEYS, "total")}
    previous_after = 0
    for i, checkpoint in enumerate(checkpoints):
        if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("label"), str):
            raise fail(f"qd_compare: {source} cost checkpoint {i} needs a label")
        after = _nonnegative_int(checkpoint.get("after_results"),
                                 f"{source} checkpoint {i}.after_results")
        if after < previous_after or after > len(results):
            raise fail(f"qd_compare: {source} cost checkpoints must be cumulative in result order")
        checkpoint_counts = {key: _nonnegative_int(checkpoint.get(key),
                                                    f"{source} checkpoint {i}.{key}")
                             for key in COST_KEYS}
        checkpoint_total = _nonnegative_int(checkpoint.get("total"),
                                            f"{source} checkpoint {i}.total")
        checkpoint_counts["total"] = checkpoint_total
        if checkpoint_total != sum(checkpoint_counts[key] for key in COST_KEYS):
            raise fail(f"qd_compare: {source} checkpoint {i} total is inconsistent")
        if any(checkpoint_counts[key] < previous[key] for key in previous):
            raise fail(f"qd_compare: {source} cost checkpoints may not decrease")
        prefix_outcomes = [_outcome(r) for r in results[:after]]
        prefix_refused = sum(o.category in DETERMINISTIC_CATEGORIES for o in prefix_outcomes)
        prefix_success = sum(o.strict_tell_eligible for o in prefix_outcomes)
        prefix_failed = after - prefix_success - prefix_refused
        if (checkpoint_counts["successful"], checkpoint_counts["failed"],
                checkpoint_counts["refused"]) != (prefix_success, prefix_failed, prefix_refused):
            raise fail(f"qd_compare: {source} checkpoint {i} does not account for result outcomes")
        clean_checkpoints.append({"label": checkpoint["label"], "after_results": after,
                                  **checkpoint_counts})
        previous, previous_after = checkpoint_counts, after
    if previous_after != len(results) or any(previous[key] != ({**counts, "total": total})[key]
                                              for key in previous):
        raise fail(f"qd_compare: {source} final cost checkpoint must match the full ledger")

    # Retried/cached attempts remain in cost accounting, but each physical geometry may occupy
    # the comparison front only once. Multiple complete scores for one design must agree under
    # the common scoring context; otherwise the manifest is internally inconsistent.
    unique_eligible: list[dict] = []
    eligible_by_design: dict[str, dict] = {}
    duplicate_ids: list[str] = []
    for row in eligible_rows:
        prior = eligible_by_design.get(row["design_hash"])
        if prior is None:
            eligible_by_design[row["design_hash"]] = row
            unique_eligible.append(row)
        else:
            if prior["objectives"] != row["objectives"]:
                raise fail(f"qd_compare: duplicate design_hash {row['design_hash']!r} has "
                           "different objectives under one scoring context")
            duplicate_ids.append(row["id"])

    return {
        "arm_id": arm_id.strip(), "algorithm": algorithm.strip(),
        "identity": {key: identity[key] for key in IDENTITY_KEYS},
        "axes": clean_axes, "reference": reference,
        "descriptor_space": {"names": descriptor_names, "ranges": ranges.tolist(),
                             "reconstruction_hash": archive_reconstruction_hash},
        "cost": {"unit": cost["unit"].strip(), **counts, "total": total,
                 "checkpoints": clean_checkpoints},
        "eligible": unique_eligible, "eligible_attempts": eligible_rows,
        "duplicate_eligible_attempt_ids": duplicate_ids, "excluded": excluded_rows,
        "outcome_categories": dict(sorted(categories.items())),
    }


def _hypervolume_2d(points: np.ndarray, reference: np.ndarray) -> tuple[float, np.ndarray]:
    """Exact dominated hypervolume for a finite 2-D minimisation front."""
    points = np.asarray(points, dtype=float)
    reference = np.asarray(reference, dtype=float)
    if points.ndim != 2 or points.shape[1:] != (2,) or not np.isfinite(points).all():
        raise ValueError("finite two-column points required")
    if reference.shape != (2,) or not np.isfinite(reference).all():
        raise ValueError("finite two-value reference required")
    if len(points) == 0:
        return 0.0, np.empty(0, dtype=int)
    if np.any(points >= reference):
        raise ValueError("frozen reference must be strictly worse than every eligible point")
    front = fast_nondominated_sort(points)[0]
    ordered = front[np.argsort(points[front, 0], kind="stable")]
    hv, upper_y = 0.0, float(reference[1])
    for idx in ordered:
        x, y = map(float, points[idx])
        if y < upper_y:
            hv += (float(reference[0]) - x) * (upper_y - y)
            upper_y = y
    return float(hv), front


def compare_manifests(manifest_a: dict, manifest_b: dict, *, source_a: str = "a",
                      source_b: str = "b") -> dict:
    a = _validate_manifest(manifest_a, source_a)
    b = _validate_manifest(manifest_b, source_b)
    if a["identity"] != b["identity"]:
        differing = [key for key in IDENTITY_KEYS if a["identity"][key] != b["identity"][key]]
        raise fail("qd_compare: arms differ in scoring/task/spec identity: " + ", ".join(differing))
    if a["axes"] != b["axes"]:
        raise fail("qd_compare: arms differ in raw objective axes or units")
    if not np.array_equal(a["reference"], b["reference"]):
        raise fail("qd_compare: arms do not share one frozen hypervolume reference")
    if (a["descriptor_space"]["names"] != b["descriptor_space"]["names"]
            or a["descriptor_space"]["ranges"] != b["descriptor_space"]["ranges"]):
        raise fail("qd_compare: arms do not share frozen descriptor names and ranges")
    if a["cost"]["unit"] != b["cost"]["unit"] or a["cost"]["total"] != b["cost"]["total"]:
        raise fail("qd_compare: arms are not equal total cost (including failures and training)")

    reference = a["reference"]
    summaries = []
    for arm in (a, b):
        points = np.asarray([r["objectives"] for r in arm["eligible"]], dtype=float).reshape(-1, 2)
        try:
            hv, front_idx = _hypervolume_2d(points, reference)
        except ValueError as exc:
            raise fail(f"qd_compare: arm {arm['arm_id']}: {exc}") from None
        summaries.append({
            "arm_id": arm["arm_id"], "algorithm": arm["algorithm"],
            "cost": arm["cost"], "n_eligible": len(arm["eligible"]),
            "n_eligible_attempts": len(arm["eligible_attempts"]),
            "duplicate_eligible_attempt_ids": arm["duplicate_eligible_attempt_ids"],
            "n_excluded": len(arm["excluded"]),
            "excluded_ids": [r["id"] for r in arm["excluded"]],
            "outcome_categories": arm["outcome_categories"],
            "front": [arm["eligible"][int(i)] for i in front_idx],
            "hypervolume": hv,
        })
    return {
        "schema": "qd-compare-report-v1", "identity": a["identity"],
        "input_manifests": {
            "a": {"source": source_a, "sha256": _manifest_hash(manifest_a)},
            "b": {"source": source_b, "sha256": _manifest_hash(manifest_b)},
        },
        "axes": a["axes"], "frozen_reference": reference.tolist(),
        "descriptor_space": {
            "names": a["descriptor_space"]["names"],
            "ranges": a["descriptor_space"]["ranges"],
            "arm_reconstruction_hashes": {
                a["arm_id"]: a["descriptor_space"]["reconstruction_hash"],
                b["arm_id"]: b["descriptor_space"]["reconstruction_hash"],
            },
        },
        "equal_cost": {"unit": a["cost"]["unit"], "total": a["cost"]["total"],
                       "includes": list(COST_KEYS)},
        "arms": summaries,
        "hypervolume_difference_a_minus_b": summaries[0]["hypervolume"] - summaries[1]["hypervolume"],
        "interpretation": ("descriptive navigation comparison only; no statistical win claim, "
                           "and excluded failures contribute cost but never archive/front points"),
    }


def _md(payload: dict) -> str:
    a, b = payload["arms"]
    axes = payload["axes"]
    return "\n".join([
        "# Equal-cost QD / Pareto comparison", "",
        f"Identity: objective v{payload['identity']['objective_version']}, score "
        f"`{payload['identity']['scoring_context_id']}`, task `{payload['identity']['task_id']}`, "
        f"spec `{payload['identity']['spec_id']}`.", "",
        f"Axes: {axes[0]['name']} [{axes[0]['unit']}] and {axes[1]['name']} [{axes[1]['unit']}], "
        f"both minimised. Frozen reference: {payload['frozen_reference']}.", "",
        f"Equal total cost: {payload['equal_cost']['total']} attempt-equivalent evaluations "
        "(successful + failed + refused + training + other; not elapsed time).", "",
        "| arm | algorithm | eligible | excluded | front | hypervolume |",
        "|---|---|---:|---:|---:|---:|",
        f"| {a['arm_id']} | {a['algorithm']} | {a['n_eligible']} | {a['n_excluded']} | "
        f"{len(a['front'])} | {a['hypervolume']:.8g} |",
        f"| {b['arm_id']} | {b['algorithm']} | {b['n_eligible']} | {b['n_excluded']} | "
        f"{len(b['front'])} | {b['hypervolume']:.8g} |", "",
        f"A - B hypervolume: {payload['hypervolume_difference_a_minus_b']:.8g}.", "",
        f"_{payload['interpretation']}._", "",
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--a", required=True, help="arm A JSON manifest")
    ap.add_argument("--b", required=True, help="arm B JSON manifest")
    add_out_arg(ap)
    args = ap.parse_args(argv)
    _guard_out(Path(args.out))
    payload = compare_manifests(_read_manifest(Path(args.a)), _read_manifest(Path(args.b)),
                                source_a=str(args.a), source_b=str(args.b))
    write_report(Path(args.out), TOOL, payload, _md(payload))
    print(f"qd_compare OK: {payload['arms'][0]['arm_id']} vs {payload['arms'][1]['arm_id']} "
          f"at equal cost {payload['equal_cost']['total']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
