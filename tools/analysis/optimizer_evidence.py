"""Composed, read-only optimizer-evidence report (P1a) — advisory only.

Usage::

    python tools/analysis/optimizer_evidence.py \
        --run runs/<a> [--run runs/<b> ...] \
        [--config examples/typologies/<cfg>.yaml ...] \
        [--catalog scratch/bo_m0/s0/catalog/catalog.json --scores scratch/bo_m0/s0/offline_scores.json] \
        [--qd-manifest-a a.json --qd-manifest-b b.json] \
        [--space-card] [--geometry-activity] --out scratch/optimizer_evidence/<tag>

This tool composes the existing offline analyses into one evidence payload. It never
dispatches a search, never edits a queue/config/run, and never changes an algorithm default.
The default path is fast and run-level only: ``optimizer_switch`` (typed outcomes, cost
ledger, stall/wall signals), ``continuation_advice`` (identity-resolved floor and advice),
``_common.cost_ledger``/``compare_compatibility``, and the budget heuristic. Geometry
sampling (space cards / parameter activity) is explicit opt-in and is recorded as
requested/skipped in every report; it never meshes or solves.

Schema (``optimizer-evidence-v1``)::

    {
      "schema": "optimizer-evidence-v1",
      "advisory_only": true,
      "dispatches_work": false,
      "changes_defaults": false,
      "decision_rule": "<the audit decision rule, verbatim>",
      "bo_admission_note": "<strict cohort/admission; raw valid rows are not 100 usable rows>",
      "run_cards": [{
        "run_id", "run_dir",
        "identity": {objective_version, brief, score_identity_hash, backend, fidelity, grid, hash},
        "outcome_counts": {valid, cached, geometry_refusal, ..., counts_sum_to_index_rows},
        "cost_ledger": {attempts_new, valid_evaluations_new, actual_bem_seconds, elapsed_seconds, ...},
        "failure_signal": {window_rows, fraction, above_threshold, counts, dominant_kind, ...},
        "progress": {valid_rows, best_j, best_row_n, relative_gain_last_window, stalled},
        "walls": [{key, lo, hi, frac_lo, frac_hi, wall_lo, wall_hi}],
        "wall_note",
        "continuation": {floor_J, status, matched_entry, match_quality, uncertainty,
                         advice, why, improvement, borderline, floor_band, n_valid, window},
        "key_numbers": {best_j, floor_J, recorded_total_seconds, ...},
        "provenance": [{field, source_tool, source_field, value}, ...]
      }],
      "cross_run": {
        "n_runs", "descriptive_only": true, "compatible_for_inference",
        "compatible_for_descriptive", "blocking", "ranking": {performed: false, ...},
        "decision_rule", "compatibility": <compare_compatibility output>
      },
      "alternatives": [{action, why, evidence: [{tool, field, value}], confidence, constraints,
                        run_id}],   # at most 2
      "decision": {status: ok|no_decisive_signal|insufficient_evidence, reason},
      "budget_heuristic": [{config, status, n_free_knobs, default_popsize, screen_budget,
                            compare_budget, recommended_budget, applied: false, provenance}],
      "seed_pack": {"status": "not_supplied"} | {status, spec, eligible_total, selected_count,
                                                   top, limitations, provenance},
      "qd_compare": {"status": "not_supplied"} | {status, identity, equal_cost, arms, ...},
      "opt_in": {"space_card": {requested, status, reason, entries},
                 "geometry_activity": {requested, status, reason, entries}},
      "limitations": [...]
    }

Provenance rule: every derived scalar in ``key_numbers`` carries a ``source_tool`` and the
exact ``source_field`` path it was read from; the same applies to outcome buckets and the
identity. Unknown identities yield ``no applicable published floor`` — a published threshold
is never borrowed from another brief.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from _common import (bounds_of, compare_compatibility, cost_ledger, fail, load_run,
                     read_json, read_yaml, write_report)
import continuation_advice
import optimizer_switch
from floor_registry import identity_from_run, identity_summary

TOOL = "optimizer_evidence"
SCHEMA = "optimizer-evidence-v1"

#: Verbatim from docs/research/optimizer_audit_2026-11-21/README.md §4.
DECISION_RULE = (
    "**Decision rule:** maximize *best verified same-identity acoustic gain* and the number "
    "of *distinct, physically valid verified basins* per actual backend time, including "
    "preparation and optimizer overhead. Never compare raw J across different resolved "
    "briefs or versions."
)

BO_ADMISSION_NOTE = (
    "For BO, use study_cohort and prepare_study.py's strict cohort/admission checks; 100 "
    "usable training rows is a minimum, and raw valid rows are not that gate."
)

_CONFIDENCE = {"measured", "strongly_indicated", "hypothesis"}

#: Numeric card fields and the exact tool/field path each was read from.
_KEY_PROVENANCE = {
    "valid_rows": ("optimizer_switch", "progress.valid_rows"),
    "best_j": ("optimizer_switch", "progress.best_j"),
    "best_row_n": ("optimizer_switch", "progress.best_row_n"),
    "relative_gain_last_window": ("optimizer_switch", "progress.relative_gain_last_window"),
    "index_rows": ("optimizer_switch", "cost_ledger.index_rows"),
    "attempts_new": ("optimizer_switch", "cost_ledger.attempts_new"),
    "actual_bem_calls_inferred": ("optimizer_switch",
                                  "cost_ledger.actual_bem_calls_inferred"),
    "actual_bem_seconds": ("optimizer_switch", "cost_ledger.actual_bem_seconds"),
    "recorded_total_seconds": ("optimizer_switch",
                               "cost_ledger.elapsed_seconds.recorded_total"),
    "wall_span_seconds": ("optimizer_switch", "cost_ledger.elapsed_seconds.wall_span"),
    "unaccounted_overhead_seconds": ("optimizer_switch",
                                     "cost_ledger.elapsed_seconds.unaccounted_overhead"),
    "failure_fraction": ("optimizer_switch", "failure_signal.fraction"),
    "floor_J": ("continuation_advice", "resolution.floor_J"),
    "continuation_improvement": ("continuation_advice", "improvement"),
}

_OUTCOME_KEYS = optimizer_switch.OUTCOME_KEYS
_OUTCOME_LABELS = optimizer_switch.OUTCOME_LABELS


# --------------------------------------------------------------------------- small helpers


def _finite(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _guard_out(out_dir: Path, run_paths: list[Path]) -> None:
    """Refuse an ``--out`` inside any input run dir (exit 2)."""
    out = Path(out_dir).resolve()
    for path in run_paths:
        resolved = Path(path).resolve()
        if out == resolved or resolved in out.parents:
            raise fail(
                f"{TOOL}: output must be outside every input run directory ({resolved})")


def _provenance(field: str, tool: str, source_field: str, value) -> dict:
    return {"field": field, "source_tool": tool, "source_field": source_field,
            "value": value}


def _numeric_provenance(prefix: str, value, tool: str) -> list[dict]:
    """Provenance for every finite number in a composed block (nested dicts/lists included)."""
    out: list[dict] = []

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                walk(child, f"{path}.{key}" if path else str(key))
        elif isinstance(node, (list, tuple)):
            for child in node:
                walk(child, f"{path}[]")
        elif isinstance(node, bool) or node is None:
            return
        elif isinstance(node, (int, float)):
            out.append({"field": path, "source_tool": tool, "source_field": path,
                        "value": node})

    walk(value, prefix)
    return out


# --------------------------------------------------------------------------- run card


def _run_card(run_dir: Path) -> dict:
    """One composed per-run evidence card (read-only; reloads are deliberate)."""
    run = load_run(run_dir)
    identity = identity_from_run(run)
    cont = continuation_advice.analyse(run_dir)
    switch = optimizer_switch.analyse_run(run_dir)

    resolution = cont.get("resolution") or {}
    progress = switch.get("progress") or {}
    ledger = switch.get("cost_ledger") or {}
    elapsed = ledger.get("elapsed_seconds") or {}
    failure = switch.get("failure_signal") or {}
    walls = switch.get("walls") or []

    continuation = {
        "floor_J": resolution.get("floor_J"),
        "status": resolution.get("status"),
        "matched_entry": resolution.get("matched_entry"),
        "match_quality": resolution.get("match_quality"),
        "uncertainty": resolution.get("uncertainty"),
        "caveat": resolution.get("caveat"),
        "advice": cont.get("advice"),
        "why": cont.get("why"),
        "improvement": cont.get("improvement"),
        "borderline": cont.get("borderline"),
        "floor_band": cont.get("floor_band"),
        "n_valid": cont.get("n_valid"),
        "window": cont.get("window"),
        "best_final": cont.get("best_final"),
    }

    key_numbers = {
        "valid_rows": progress.get("valid_rows"),
        "best_j": progress.get("best_j"),
        "best_row_n": progress.get("best_row_n"),
        "relative_gain_last_window": progress.get("relative_gain_last_window"),
        "index_rows": ledger.get("index_rows"),
        "attempts_new": ledger.get("attempts_new"),
        "actual_bem_calls_inferred": ledger.get("actual_bem_calls_inferred"),
        "actual_bem_seconds": ledger.get("actual_bem_seconds"),
        "recorded_total_seconds": elapsed.get("recorded_total"),
        "wall_span_seconds": elapsed.get("wall_span"),
        "unaccounted_overhead_seconds": elapsed.get("unaccounted_overhead"),
        "failure_fraction": failure.get("fraction"),
        "floor_J": resolution.get("floor_J"),
        "continuation_improvement": cont.get("improvement"),
    }

    provenance = [
        {"field": "identity", "source_tool": "floor_registry",
         "source_field": "identity_summary", "value": identity.get("hash")},
        {"field": "continuation.advice", "source_tool": "continuation_advice",
         "source_field": "advice", "value": continuation.get("advice")},
        {"field": "continuation.match_quality", "source_tool": "continuation_advice",
         "source_field": "resolution.match_quality",
         "value": continuation.get("match_quality")},
    ]
    for field, (tool, source_field) in _KEY_PROVENANCE.items():
        provenance.append(_provenance(field, tool, source_field, key_numbers.get(field)))
    for key in _OUTCOME_KEYS:
        provenance.append(_provenance(f"outcome_counts.{key}", "optimizer_switch",
                                      f"outcome_counts.{key}",
                                      (switch.get("outcome_counts") or {}).get(key)))
    pinned = [w.get("key") for w in walls if w.get("wall_lo") or w.get("wall_hi")]
    provenance.append(_provenance("walls.pinned_keys", "optimizer_switch",
                                  "walls[].wall_lo / walls[].wall_hi", pinned))
    # Every remaining derived number in the composed blocks gets an explicit source path.
    provenance += _numeric_provenance("identity", identity_summary(identity),
                                      "floor_registry")
    provenance += _numeric_provenance("outcome_counts", switch.get("outcome_counts"),
                                      "optimizer_switch")
    provenance += _numeric_provenance("cost_ledger", ledger, "optimizer_switch")
    provenance += _numeric_provenance("failure_signal", failure, "optimizer_switch")
    provenance += _numeric_provenance("progress", progress, "optimizer_switch")
    provenance += _numeric_provenance("walls", walls, "optimizer_switch")
    provenance += _numeric_provenance("continuation", continuation, "continuation_advice")

    identity_block = identity_summary(identity)
    return {
        "run_id": Path(run_dir).name,
        "run_dir": str(Path(run_dir)),
        "identity": identity_block,
        "outcome_counts": switch.get("outcome_counts"),
        "cost_ledger": ledger,
        "failure_signal": failure,
        "progress": progress,
        "walls": walls,
        "wall_note": switch.get("wall_note"),
        "continuation": continuation,
        "key_numbers": key_numbers,
        "provenance": provenance,
    }


# --------------------------------------------------------------------------- alternatives


def _failure_alternative(card: dict) -> dict | None:
    failure = card.get("failure_signal") or {}
    if not failure.get("above_threshold"):
        return None
    dominant = failure.get("dominant_kind") or "unknown"
    counts = failure.get("counts") or {}
    n_dominant = counts.get(dominant, 0)
    label = _OUTCOME_LABELS.get(dominant, dominant)
    if dominant in ("geometry_refusal", "envelope_refusal", "resource_refusal"):
        action = "investigate_geometry_envelope_resource"
        why = (f"Failure-dominated window: the dominant recorded outcome is {label} "
               f"({n_dominant} of {failure.get('window_rows')} window rows). Investigate "
               "geometry, envelope and resource failure kinds first.")
    elif dominant == "solver_failure":
        action = "investigate_solver_failures"
        why = (f"Failure-dominated window: the dominant recorded outcome is {label} "
               f"({n_dominant} of {failure.get('window_rows')} window rows). Investigate the "
               "solver/infrastructure failure first.")
    elif dominant == "pipeline_failure":
        action = "investigate_pipeline_failures"
        why = (f"Failure-dominated window: the dominant recorded outcome is {label} "
               f"({n_dominant} of {failure.get('window_rows')} window rows). Investigate the "
               "pipeline/metrics stage first.")
    else:
        action = "investigate_failure_kinds"
        why = (f"Failure-dominated window: the dominant recorded outcome is {label} "
               f"({n_dominant} of {failure.get('window_rows')} window rows). Classify the "
               "failure kinds before changing an optimizer.")
    return {
        "action": action,
        "why": why,
        "evidence": [
            {"tool": "optimizer_switch", "field": "failure_signal.above_threshold",
             "value": True},
            {"tool": "optimizer_switch", "field": "failure_signal.fraction",
             "value": _finite(failure.get("fraction"))},
            {"tool": "optimizer_switch", "field": "failure_signal.dominant_kind",
             "value": dominant},
            {"tool": "optimizer_switch", "field": f"failure_signal.counts.{dominant}",
             "value": n_dominant},
        ],
        "confidence": "measured",
        "constraints": [
            "Diagnose the named failure kinds before changing the optimizer or bounds.",
            "Non-valid rows are not all failures; typed counts separate refusals, "
            "solver/pipeline failures and cached replays.",
        ],
    }


def _wall_alternative(card: dict) -> dict | None:
    pins = [w for w in (card.get("walls") or []) if w.get("wall_lo") or w.get("wall_hi")]
    if not pins:
        return None
    keys = [w.get("key") for w in pins]
    sides = [("lo" if w.get("wall_lo") else "hi") + ":" + str(w.get("key")) for w in pins]
    return {
        "action": "review_limits_not_auto_widen",
        "why": (f"Wall signal on {', '.join(keys)}: review the pinned dimensions and physical "
                "limits. A wall is a diagnostic, not proof that widening is safe or useful."),
        "evidence": [
            {"tool": "optimizer_switch", "field": "walls[].wall_lo / walls[].wall_hi",
             "value": sides},
        ],
        "confidence": "measured",
        "constraints": ["Do not automatically widen bounds; a wall candidate is gated by "
                        "physical safety and owner sign-off."],
    }


def _stall_alternative(card: dict) -> dict | None:
    progress = card.get("progress") or {}
    if progress.get("stalled") is not True:
        return None
    pins = [w for w in (card.get("walls") or []) if w.get("wall_lo") or w.get("wall_hi")]
    if pins:
        return None  # the wall diagnostic owns this case; never auto-widen
    return {
        "action": "seed_or_global_exploration",
        "why": ("Search stalled with no pinned wall: the last-window relative gain is below "
                "the existing threshold. Check headroom and sampling scale, then consider a new "
                "seed or global exploration."),
        "evidence": [
            {"tool": "optimizer_switch", "field": "progress.stalled", "value": True},
            {"tool": "optimizer_switch", "field": "progress.relative_gain_last_window",
             "value": _finite(progress.get("relative_gain_last_window"))},
        ],
        "confidence": "strongly_indicated",
        "constraints": [
            "Inspect headroom/sampling scale before restarting.",
            "For a collapsed TuRBO region inspect its recorded state and consider a separately "
            "controlled restart, not an assumed automatic one.",
        ],
    }


def _continuation_alternative(card: dict) -> dict | None:
    """Floor-dependent: only emitted when the run's identity has a matched floor."""
    continuation = card.get("continuation") or {}
    if continuation.get("floor_J") is None:
        return None
    if continuation.get("advice") != "propose continuation":
        return None
    identity = card.get("identity") or {}
    brief = identity.get("brief") or {}
    return {
        "action": "extend_same_identity_lane",
        "why": continuation.get("why") or (
            "The last-window gain exceeds the published floor beyond the declared "
            "uncertainty band; continue this same-identity lane."),
        "evidence": [
            {"tool": "continuation_advice", "field": "improvement",
             "value": _finite(continuation.get("improvement"))},
            {"tool": "continuation_advice", "field": "resolution.floor_J",
             "value": _finite(continuation.get("floor_J"))},
            {"tool": "continuation_advice", "field": "resolution.match_quality",
             "value": continuation.get("match_quality")},
            {"tool": "continuation_advice", "field": "identity.brief.name",
             "value": brief.get("name")},
            {"tool": "continuation_advice", "field": "identity.brief.sha256",
             "value": brief.get("sha256")},
            {"tool": "continuation_advice", "field": "identity.score_identity_hash",
             "value": identity.get("score_identity_hash")},
        ],
        "confidence": "strongly_indicated",
        "constraints": [
            "Same resolved identity only (brief, score identity, solver/fidelity, grid).",
            "Verify any claimed gain before widening bounds or changing task identity.",
            "Never rank raw J across different briefs or objective versions.",
        ],
    }


def _verification_alternative(card: dict) -> dict | None:
    continuation = card.get("continuation") or {}
    if continuation.get("advice") != "verify on common grid":
        return None
    return {
        "action": "common_grid_verification",
        "why": continuation.get("why") or (
            "The continuation gain is inside the declared uncertainty band around the floor; "
            "verify both runs on one common grid before a continue/stop decision."),
        "evidence": [
            {"tool": "continuation_advice", "field": "borderline",
             "value": continuation.get("borderline")},
            {"tool": "continuation_advice", "field": "improvement",
             "value": _finite(continuation.get("improvement"))},
            {"tool": "continuation_advice", "field": "floor_J",
             "value": _finite(continuation.get("floor_J"))},
        ],
        "confidence": "strongly_indicated",
        "constraints": ["Verify both runs on one common grid; do not act on a provisional "
                        "screen-J difference."],
    }


def _run_alternatives(card: dict) -> list[dict]:
    """At most two evidence-backed alternatives for one run, in priority order.

    Unknown floor suppresses only floor-dependent advice (continuation / common-grid
    verification). Typed failure, wall and stall diagnostics do not borrow a threshold and
    are still emitted.
    """
    continuation = card.get("continuation") or {}
    candidates = [
        _failure_alternative(card),
        _wall_alternative(card),
        _stall_alternative(card),
    ]
    if continuation.get("floor_J") is not None:
        candidates.append(_continuation_alternative(card))
        candidates.append(_verification_alternative(card))
    out = [alt for alt in candidates if alt is not None]
    for alt in out:
        if alt["confidence"] not in _CONFIDENCE:  # defensive: impossible by construction
            raise ValueError(f"{TOOL}: invalid confidence {alt['confidence']!r}")
        alt["run_id"] = card.get("run_id")
    return out[:2]


# --------------------------------------------------------------------------- optional sections


def _n_free_knobs(config_path: Path) -> tuple[int, str]:
    """Free search knobs of a config, with an explicit fallback label when loading fails."""
    try:
        from hornlab_search.config import load_config
        from hornlab_search.design.space import DesignSpace

        cfg = load_config(Path(config_path))
        return len(DesignSpace.from_config(cfg).keys()), "design_space"
    except Exception:  # noqa: BLE001 - the report must still name the config
        raw = read_yaml(Path(config_path))
        if not isinstance(raw, dict):
            raise
        return len(bounds_of(raw)), "bounds_fallback"


def _budget_section(config_paths: list[Path]) -> list[dict]:
    from hornlab_search.search import budget_heuristic

    out: list[dict] = []
    for config_path in config_paths:
        entry: dict[str, Any] = {"config": str(config_path)}
        try:
            n_knobs, source = _n_free_knobs(Path(config_path))
        except Exception as exc:  # noqa: BLE001 - one bad config must not hide the rest
            entry.update({"status": "error", "error": f"{type(exc).__name__}: {exc}",
                          "applied": False})
            out.append(entry)
            continue
        suggestion = budget_heuristic.suggest_budget(n_knobs)
        entry.update({
            "status": "ok",
            "n_free_knobs": n_knobs,
            "knob_count_source": source,
            "default_popsize": suggestion["popsize_default"],
            "screen_budget": suggestion["screen"],
            "compare_budget": suggestion["compare"],
            "recommended_budget": suggestion["recommended"],
            "uncapped_budget": suggestion["uncapped"],
            "restarts_mode": suggestion["restarts_mode"],
            "rationale": suggestion["rationale"],
            "sources": suggestion["sources"],
            "applied": False,
            "provenance": {
                "source_tool": "hornlab_search.search.budget_heuristic",
                "source_field": "suggest_budget",
                "entrypoint": "suggest_budget(n_free_knobs)",
            },
        })
        out.append(entry)
    return out


def _seed_pack_section(catalog, scores, *, k: int, task, objective_version, family,
                       fidelity, min_score_percentile: float, seed: int) -> dict:
    if not catalog:
        return {"status": "not_supplied"}
    try:
        import seed_pack

        pack = seed_pack.build_seed_pack(
            Path(catalog), k=max(1, int(k)), task=task,
            objective_version=objective_version, family=family, fidelity=fidelity,
            min_score_percentile=float(min_score_percentile),
            scores_path=(Path(scores) if scores else None), seed=int(seed))
    except Exception as exc:  # noqa: BLE001 - optional input, reported not fatal
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}",
                "provenance": {"source_tool": "seed_pack",
                               "entrypoint": "build_seed_pack",
                               "input": {"catalog": str(catalog),
                                         "scores": str(scores) if scores else None}}}
    selections = pack.get("selections") or []
    if pack.get("error"):
        status = "error"
    elif not selections:
        status = "no_selections"
    else:
        status = "built"
    return {
        "status": status,
        "spec": pack.get("spec"),
        "eligible_total": (pack.get("eligible") or {}).get("total"),
        "selected_count": len(selections),
        "top": [{"rank": s.get("rank"), "design_hash": s.get("design_hash"),
                 "score": s.get("score"), "config_name": s.get("config_name"),
                 "objective_version": s.get("objective_version"),
                 "provenance_gaps": s.get("provenance_gaps")}
                for s in selections[:5]],
        "limitations": pack.get("limitations"),
        "error": pack.get("error"),
        "provenance": {
            "source_tool": "seed_pack",
            "source_field": "build_seed_pack",
            "input": {"catalog": str(catalog),
                      "scores": str(scores) if scores else None},
            "fields": ["spec", "eligible.total", "selections[]"],
        },
    }


def _qd_section(manifest_a, manifest_b) -> dict:
    if not manifest_a or not manifest_b:
        return {"status": "not_supplied"}
    try:
        import qd_compare

        a = read_json(Path(manifest_a))
        b = read_json(Path(manifest_b))
        if not isinstance(a, dict) or not isinstance(b, dict):
            raise ValueError("both QD manifests must be JSON objects")
        report = qd_compare.compare_manifests(a, b, source_a=str(manifest_a),
                                              source_b=str(manifest_b))
    except SystemExit as exc:  # qd_compare.fail() is a refusal, not a report crash
        return {"status": "refused", "error": str(exc),
                "provenance": {"source_tool": "qd_compare",
                               "source_field": "compare_manifests"}}
    except Exception as exc:  # noqa: BLE001 - optional input, reported not fatal
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}",
                "provenance": {"source_tool": "qd_compare",
                               "source_field": "compare_manifests"}}
    return {
        "status": "compared",
        "identity": report.get("identity"),
        "equal_cost": report.get("equal_cost"),
        "arms": [{"arm_id": arm.get("arm_id"), "algorithm": arm.get("algorithm"),
                  "n_eligible": arm.get("n_eligible"),
                  "n_excluded": arm.get("n_excluded"),
                  "hypervolume": _finite(arm.get("hypervolume"))}
                 for arm in report.get("arms") or []],
        "hypervolume_difference_a_minus_b": _finite(
            report.get("hypervolume_difference_a_minus_b")),
        "interpretation": report.get("interpretation"),
        "provenance": {"source_tool": "qd_compare",
                       "source_field": "compare_manifests",
                       "manifests": {"a": str(manifest_a), "b": str(manifest_b)}},
    }


def _space_card_section(config_paths: list[Path], requested: bool,
                        run_paths: list[Path]) -> dict:
    if not requested:
        return {"requested": False, "status": "skipped",
                "reason": "not requested (default fast path)"}
    if not config_paths:
        return {"requested": True, "status": "skipped",
                "reason": "no --config supplied"}
    import space_card

    entries: list[dict] = []
    ran = False
    for config_path in config_paths:
        try:
            card = space_card.card_for(
                Path(config_path), run=(run_paths[0] if run_paths else None),
                points=8, box_n=64, sigma_n=32)
        except Exception as exc:  # noqa: BLE001 - one bad config must not hide the rest
            entries.append({"config": str(config_path), "status": "error",
                            "error": f"{type(exc).__name__}: {exc}"})
            continue
        ran = True
        geometry = card.get("geometry") or {}
        entries.append({
            "config": str(config_path),
            "status": "ran",
            "name": card.get("name"),
            "family": card.get("family"),
            "keys": card.get("keys"),
            "legal_points": geometry.get("legal_points"),
            "n_points": geometry.get("n_points"),
            "effective_dimension": geometry.get("effective_dimension"),
            "recommendation_actions": [r.get("action") for r in
                                       card.get("recommendations") or []],
            "note": "read-only space evidence; CPU geometry sampling only; nothing applied",
        })
    return {"requested": True, "status": "ran" if ran else "error", "entries": entries,
            "note": "no mesh and no BEM solve; evidence only"}


def _geometry_activity_section(config_paths: list[Path], requested: bool) -> dict:
    if not requested:
        return {"requested": False, "status": "skipped",
                "reason": "not requested (default fast path)"}
    if not config_paths:
        return {"requested": True, "status": "skipped",
                "reason": "no --config supplied"}
    import parameter_activity

    entries: list[dict] = []
    ran = False
    for config_path in config_paths:
        try:
            ledger = parameter_activity.build_ledger(Path(config_path), run_geometry=True)
        except Exception as exc:  # noqa: BLE001 - one bad config must not hide the rest
            entries.append({"config": str(config_path), "status": "error",
                            "error": f"{type(exc).__name__}: {exc}"})
            continue
        ran = True
        entries.append({
            "config": str(config_path),
            "status": "ran",
            "counts": ledger.get("counts"),
            "search_d": (ledger.get("search") or {}).get("d"),
            "active_projection": ledger.get("active_projection"),
            "geometry": ledger.get("geometry"),
            "task_eligibility": ledger.get("task_eligibility"),
            "note": "read-only control/geometry evidence; no mesh and no BEM solve",
        })
    return {"requested": True, "status": "ran" if ran else "error", "entries": entries,
            "note": "no mesh and no BEM solve; nothing applied"}


# --------------------------------------------------------------------------- assembly


def build_report(*, run_dirs=None, configs=None, catalog=None, scores=None,
                 qd_manifest_a=None, qd_manifest_b=None, space_card: bool = False,
                 geometry_activity: bool = False, seed_k: int = 8, seed_task=None,
                 seed_objective_version=None, seed_family=None, seed_fidelity=None,
                 seed_percentile: float = 0.0, seed: int = 0) -> dict:
    """Compose the full advisory payload (does not write files)."""
    run_paths = [Path(p).resolve() for p in (run_dirs or [])]
    config_paths = [Path(p) for p in (configs or [])]

    run_cards = [_run_card(path) for path in run_paths]
    loaded = [load_run(path) for path in run_paths]
    if loaded:
        compatibility = compare_compatibility(loaded)
    else:
        compatibility = {
            "n_runs": 0, "same": {}, "differing": {}, "blocking": ["no_runs"],
            "software_variants": {}, "compatible_for_descriptive": False,
            "compatible_for_inference": False, "fingerprints": [],
        }

    cross_run = {
        "n_runs": compatibility.get("n_runs", len(run_paths)),
        "descriptive_only": True,
        "compatible_for_inference": bool(compatibility.get("compatible_for_inference")),
        "compatible_for_descriptive": bool(compatibility.get("compatible_for_descriptive")),
        "blocking": list(compatibility.get("blocking") or []),
        "same": compatibility.get("same") or {},
        "differing": compatibility.get("differing") or {},
        "software_variants": compatibility.get("software_variants") or {},
        "ranking": {
            "performed": False,
            "raw_j_ranking": None,
            "reason": ("Raw J is never ranked across different briefs, objective versions "
                       "or tasks."),
        },
        "decision_rule": DECISION_RULE,
        "compatibility": compatibility,
    }

    incompatible = (len(run_cards) >= 2
                    and not compatibility.get("compatible_for_inference"))
    any_floor = any((card.get("continuation") or {}).get("floor_J") is not None
                    for card in run_cards)
    missing_floor_runs = [str(card.get("run_id")) for card in run_cards
                          if (card.get("continuation") or {}).get("floor_J") is None]

    alternatives: list[dict] = []
    if not incompatible:
        # Failure/wall/stall diagnostics never borrow a floor; floor-dependent advice is
        # filtered per run inside _run_alternatives.
        collected: list[dict] = []
        for card in run_cards:
            collected.extend(_run_alternatives(card))
        alternatives = collected[:2]

    if not run_cards:
        decision: dict[str, Any] = {"status": "insufficient_evidence",
                                    "reason": "no run supplied"}
    elif incompatible:
        decision = {
            "status": "insufficient_evidence",
            "reason": ("cross-run identities are not compatible for inference: "
                       + ", ".join(compatibility.get("blocking") or [])),
        }
    elif not any_floor:
        decision = {
            "status": "insufficient_evidence",
            "reason": ("no run identity resolves to an applicable published floor; only "
                       "non-floor diagnostics are available (missing floor: "
                       + ", ".join(missing_floor_runs) + ")"),
        }
    elif missing_floor_runs:
        decision = {
            "status": "insufficient_evidence",
            "reason": ("some run identities have no applicable published floor; "
                       "floor-dependent advice is suppressed for: "
                       + ", ".join(missing_floor_runs)),
        }
    elif not alternatives:
        decision = {
            "status": "no_decisive_signal",
            "reason": ("no decisive failure, wall, stall or borderline signal was present"),
        }
    else:
        decision = {"status": "ok",
                    "reason": "evidence-backed advisory alternatives are available"}
    decision["missing_floor_runs"] = missing_floor_runs

    return {
        "schema": SCHEMA,
        "advisory_only": True,
        "dispatches_work": False,
        "changes_defaults": False,
        "decision_rule": DECISION_RULE,
        "bo_admission_note": BO_ADMISSION_NOTE,
        "run_cards": run_cards,
        "cross_run": cross_run,
        "alternatives": alternatives,
        "decision": decision,
        "budget_heuristic": _budget_section(config_paths),
        "seed_pack": _seed_pack_section(
            catalog, scores, k=seed_k, task=seed_task,
            objective_version=seed_objective_version, family=seed_family,
            fidelity=seed_fidelity, min_score_percentile=seed_percentile, seed=seed),
        "qd_compare": _qd_section(qd_manifest_a, qd_manifest_b),
        "opt_in": {
            "space_card": _space_card_section(config_paths, space_card, run_paths),
            "geometry_activity": _geometry_activity_section(config_paths,
                                                            geometry_activity),
        },
        "limitations": [
            "Advisory only: this report never dispatches work, edits a queue/config/run or "
            "changes an algorithm default.",
            "Raw J is not comparable across different briefs, objective versions or tasks; "
            "compare best verified same-identity gain and distinct valid basins per actual "
            "backend time instead.",
            "The default path reads run records only; space cards and geometry activity are "
            "opt-in and use CPU geometry sampling only (no mesh, no BEM solve).",
            "Raw valid rows are not independent seeds and are not 100 usable BO training "
            "rows; BO admission requires the strict cohort/admission checks.",
            "Missing timing, cached rows and unrecorded preparation costs limit the cost "
            "ledger; inspect identities and matched budgets before comparing methods.",
        ],
    }


# --------------------------------------------------------------------------- markdown


def _md(payload: dict) -> str:
    lines = [
        "# Optimizer evidence (advisory only)",
        "",
        payload.get("decision_rule", ""),
        "",
        f"Schema `{payload.get('schema')}`; advisory_only={payload.get('advisory_only')}; "
        f"dispatches_work={payload.get('dispatches_work')}; "
        f"changes_defaults={payload.get('changes_defaults')}.",
        "",
        f"Decision: **{payload.get('decision', {}).get('status')}** — "
        f"{payload.get('decision', {}).get('reason')}",
        "",
    ]

    for card in payload.get("run_cards") or []:
        identity = card.get("identity") or {}
        continuation = card.get("continuation") or {}
        counts = card.get("outcome_counts") or {}
        key_numbers = card.get("key_numbers") or {}
        lines += [
            f"## {card.get('run_id')}",
            "",
            f"- Objective v{_fmt(identity.get('objective_version'))}; brief "
            f"`{(identity.get('brief') or {}).get('name')}`; backend "
            f"`{_fmt(identity.get('backend'))}`; identity `{_fmt(identity.get('hash'))}`.",
            f"- Typed outcomes (index rows): " + ", ".join(
                f"{key}={counts.get(key)}" for key in _OUTCOME_KEYS) + ".",
            f"- Cost: attempts_new={_fmt(key_numbers.get('attempts_new'))}; "
            f"valid_rows={_fmt(key_numbers.get('valid_rows'))}; recorded_total_s="
            f"{_fmt(key_numbers.get('recorded_total_seconds'))}; wall_span_s="
            f"{_fmt(key_numbers.get('wall_span_seconds'))}; actual_bem_s="
            f"{_fmt(key_numbers.get('actual_bem_seconds'))}.",
            f"- Floor: {_fmt(continuation.get('floor_J'))} "
            f"({continuation.get('status')}, {continuation.get('match_quality')}); "
            f"advice: {continuation.get('advice')} — {continuation.get('why')}",
            f"- Wall note: {card.get('wall_note') or 'none'}",
            "",
        ]

    alternatives = payload.get("alternatives") or []
    lines += ["## Suggested alternatives (not applied)", ""]
    if not alternatives:
        lines.append("None: the evidence present is insufficient or the run shows no decisive "
                     "failure, wall, stall or borderline signal.")
    for alt in alternatives:
        lines.append(f"- **{alt.get('action')}** ({alt.get('confidence')}): {alt.get('why')}")
        for ev in alt.get("evidence") or []:
            lines.append(f"  - `{ev.get('tool')}:{ev.get('field')}` = {_fmt(ev.get('value'))}")
        for constraint in alt.get("constraints") or []:
            lines.append(f"  - constraint: {constraint}")
    lines.append("")

    cross = payload.get("cross_run") or {}
    lines += [
        "## Cross-run compatibility",
        "",
        f"{cross.get('n_runs')} run(s); descriptive_only={cross.get('descriptive_only')}; "
        f"compatible_for_inference={cross.get('compatible_for_inference')}; "
        f"blocking: {', '.join(cross.get('blocking') or []) or 'none'}.",
        "Raw J ranking: not performed (never rank raw J across different briefs, objective "
        "versions or tasks).",
        "",
    ]

    budget = payload.get("budget_heuristic") or []
    if budget:
        lines += ["## Budget heuristic (not applied)", ""]
        for entry in budget:
            if entry.get("status") == "ok":
                lines.append(
                    f"- `{entry.get('config')}`: n={entry.get('n_free_knobs')}, "
                    f"popsize={entry.get('default_popsize')}, screen="
                    f"{entry.get('screen_budget')}, compare={entry.get('compare_budget')}.")
            else:
                lines.append(f"- `{entry.get('config')}`: {entry.get('status')} — "
                             f"{entry.get('error')}")
        lines.append("")

    seed = payload.get("seed_pack") or {}
    lines += ["## Seed pack", ""]
    if seed.get("status") == "not_supplied":
        lines.append("Not supplied (`--catalog`/`--scores` absent).")
    else:
        lines.append(f"Status {seed.get('status')}; selected "
                     f"{seed.get('selected_count')}/{seed.get('eligible_total')}.")
    lines.append("")

    qd = payload.get("qd_compare") or {}
    lines += ["## QD comparison", ""]
    if qd.get("status") == "not_supplied":
        lines.append("Not supplied (both `--qd-manifest-a` and `--qd-manifest-b` are required).")
    else:
        lines.append(f"Status {qd.get('status')}.")
    lines.append("")

    opt_in = payload.get("opt_in") or {}
    lines += ["## Opt-in analyses", ""]
    for name in ("space_card", "geometry_activity"):
        section = opt_in.get(name) or {}
        lines.append(f"- {name}: requested={section.get('requested')}; "
                     f"status={section.get('status')}; "
                     f"reason={section.get('reason') or 'n/a'}.")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- CLI


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--run", action="append", default=[],
                        help="search run directory; repeat for multiple runs")
    parser.add_argument("--config", action="append", default=[],
                        help="optional config YAML for the budget heuristic / opt-in analyses")
    parser.add_argument("--catalog", default=None,
                        help="catalog.json for the optional seed pack")
    parser.add_argument("--scores", default=None,
                        help="offline_scores.json for the optional seed pack")
    parser.add_argument("--qd-manifest-a", default=None,
                        help="QD comparison arm A manifest (requires arm B)")
    parser.add_argument("--qd-manifest-b", default=None,
                        help="QD comparison arm B manifest (requires arm A)")
    parser.add_argument("--space-card", action="store_true",
                        help="opt-in: CPU space cards (no mesh, no BEM solve)")
    parser.add_argument("--geometry-activity", action="store_true",
                        help="opt-in: CPU parameter/geometry activity (no mesh, no BEM solve)")
    parser.add_argument("--seed-k", type=int, default=8,
                        help="seed pack k when --catalog is supplied (default 8)")
    parser.add_argument("--seed-task", default=None, help="seed pack task filter")
    parser.add_argument("--seed-objective-version", type=int, default=None,
                        help="seed pack objective-version filter")
    parser.add_argument("--seed-family", default=None, help="seed pack family filter")
    parser.add_argument("--seed-fidelity", default=None, help="seed pack fidelity filter")
    parser.add_argument("--seed-percentile", type=float, default=0.0,
                        help="seed pack minimum score percentile (default 0)")
    parser.add_argument("--seed", type=int, default=0,
                        help="seed pack RNG tie-break seed (default 0)")
    parser.add_argument("--out", required=True,
                        help="report directory outside every input run")
    args = parser.parse_args(argv)

    run_paths = [Path(p).resolve() for p in args.run]
    out = Path(args.out).resolve()
    _guard_out(out, run_paths)

    try:
        payload = build_report(
            run_dirs=run_paths, configs=[Path(p) for p in args.config],
            catalog=args.catalog, scores=args.scores,
            qd_manifest_a=args.qd_manifest_a, qd_manifest_b=args.qd_manifest_b,
            space_card=args.space_card, geometry_activity=args.geometry_activity,
            seed_k=args.seed_k, seed_task=args.seed_task,
            seed_objective_version=args.seed_objective_version,
            seed_family=args.seed_family, seed_fidelity=args.seed_fidelity,
            seed_percentile=args.seed_percentile, seed=args.seed)
    except (FileNotFoundError, ValueError) as exc:
        raise fail(f"{TOOL}: {exc}") from exc

    write_report(out, TOOL, payload, _md(payload))
    print(f"{TOOL} OK: {len(payload['run_cards'])} run(s), "
          f"{len(payload['alternatives'])} alternative(s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
