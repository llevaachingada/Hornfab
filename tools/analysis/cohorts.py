"""S0 operation-specific comparability and the ATH census (2026-11-12).

Consumes ``catalog.py`` records.  It never reads a dataset artifact itself and never writes to
a source root.

The key rule is that *the same operation does not require the same whole config*.  Four
operations have different allowed differences:

``performance``
    Compare measured outcomes within one task/scoring/mesh/grid/backend/dependency identity.
    Different designs, solves and experiments are expected; a brief, objective version,
    target, fidelity or backend change is rejected.
``backend_parity``
    Pair the same design/task/scoring under different ``backend`` values.  Backend is the
    allowed difference; objective/brief/fidelity/mesh/grid identity are required equal.
``fidelity_comparison``
    Pair screen/verify (or other measured fidelities) under the same task/scoring/backend.
    Fidelity, grid and mesh resolution are the allowed differences; objective/brief/backend
    are required equal.
``optimizer_ab``
    Compare intentional search treatments under one physical/scoring/measurement identity.
    The treatment (config) is allowed to differ and must be identified; objective/brief/
    fidelity/backend are rejected if mixed.

A record does not store objective weights/tolerances (only target + version + terms).  A
caller may pass a resolved brief/score spec; ``attach_score_spec`` then adds it to the score
identity.  Without one, ``score_parameters_unknown`` is reported as a warning, never silently
treated as equal.

ATH census
----------
``ath_census`` counts the resolved ``native__ath_core_v4`` cohort: brief band/f0, objective
v4, one fidelity at a time, one backend, one external dependency identity.  It reports records,
unique physical solves, unique geometries, independent experiments, complete replayable scores
(parent-frozen array/gate rule), missing arrays and failures by type.  It returns
``insufficient_evidence`` rather than pooling unrelated briefs/versions/fidelities.

Usage::

    .venv\\Scripts\\python.exe tools\\analysis\\cohorts.py \\
        --root dataset --operation ath --out scratch\\bo_m0\\s0\\ath_census

Read-only over the sources; writes only under ``--out``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import catalog
from _common import REPO, add_out_arg, fail, jsonable, read_yaml, utc_now

TOOL = "cohorts"
SCHEMA_VERSION = 1
ATH_MIN_GEOMETRIES = 16  # protocol bo-study-v1.1 n_min = max(16, 2*(d+1)); d is at least 7
NATIVE_CONFIG = "native__ath_core_v4"
_EXTERNAL_LIBS = ("hornlab_mesher", "hornlab_beat_bem", "hornlab_bempp_bem", "hornlab_plots")

OPERATIONS = ("performance", "backend_parity", "fidelity_comparison", "optimizer_ab")

#: Identity fields, in the names every record carries (see catalog.py).
TASK_FIELDS = ("brief", "brief_hash", "family", "target_hash", "objective_version")
MEASUREMENT_FIELDS = ("fidelity", "backend", "mesh_spec_id", "grid_hash", "dependency_hash")
SCORE_FIELDS = ("score_identity",)
EXPERIMENT_FIELDS = ("experiment_id", "config_name")

_OP_POLICY: dict[str, dict[str, Any]] = {
    "performance": {
        "required": TASK_FIELDS + SCORE_FIELDS + MEASUREMENT_FIELDS,
        "allowed": ("geometry_id", "physical_solve_id", "experiment_id", "config_name"),
        "treatments": False,
        "note": "same task/scoring/fidelity/backend/mesh/grid/dependency; designs and "
                "experiments may differ",
    },
    "backend_parity": {
        "required": TASK_FIELDS + SCORE_FIELDS
                    + ("fidelity", "mesh_spec_id", "grid_hash", "dependency_hash"),
        "allowed": ("backend", "own_commit", "geometry_id", "physical_solve_id",
                    "experiment_id", "config_name"),
        "pairs_by": ("geometry_id", "mesh_spec_id", "grid_hash"),
        "treatments": False,
        "note": "backend is the allowed difference; pair the same design/solve spec",
    },
    "fidelity_comparison": {
        "required": TASK_FIELDS + SCORE_FIELDS + ("backend", "dependency_hash"),
        "allowed": ("fidelity", "grid_hash", "mesh_spec_id", "geometry_id",
                    "physical_solve_id", "experiment_id", "config_name"),
        "pairs_by": ("geometry_id", "brief_hash", "objective_version", "backend"),
        "treatments": False,
        "note": "screen/verify is the allowed difference; never mix objective/brief/backend",
    },
    "optimizer_ab": {
        "required": TASK_FIELDS + SCORE_FIELDS + MEASUREMENT_FIELDS,
        "allowed": ("geometry_id", "physical_solve_id", "experiment_id", "config_name",
                    "run_id"),
        "treatments": True,
        "note": "intentional config/treatment difference; physical/scoring/fidelity/"
                "backend identity must match",
    },
}


# ------------------------------------------------------------------ identities


def _prov(record: dict) -> dict:
    return record.get("provenance") if isinstance(record.get("provenance"), dict) else {}


def field_value(record: dict, key: str) -> Any:
    """The comparison value for a catalog identity field (``None`` = unknown)."""
    prov = _prov(record)
    if key == "brief":
        return prov.get("brief")
    if key == "brief_hash":
        return prov.get("brief_hash")
    if key == "family":
        return record.get("family")
    if key == "target_hash":
        return record.get("target_hash")
    if key == "objective_version":
        return record.get("objective_version")
    if key == "score_identity":
        return record.get("score_identity")
    if key == "fidelity":
        return record.get("fidelity")
    if key == "backend":
        return record.get("backend")
    if key == "mesh_spec_id":
        return record.get("mesh_spec_id")
    if key == "grid_hash":
        return record.get("grid_hash")
    if key == "dependency_hash":
        return record.get("dependency_hash")
    if key == "software_hash":
        return record.get("software_hash")
    if key == "own_commit":
        return record.get("own_commit")
    if key == "geometry_id":
        return record.get("geometry_id")
    if key == "physical_solve_id":
        return record.get("physical_solve_id")
    if key == "experiment_id":
        return record.get("experiment_id")
    if key == "run_id":
        return record.get("run_id")
    if key == "config_name":
        return record.get("config_name")
    return record.get(key)


def _variant_map(records: list[dict], keys: Iterable[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key in keys:
        counts: Counter[str] = Counter()
        for r in records:
            val = field_value(r, key)
            encoded = json.dumps(val, sort_keys=True, default=str)
            counts[encoded] += 1
        out[key] = {"n_variants": len(counts),
                    "values": [json.loads(k) for k in sorted(counts)],
                    "counts": {k: counts[k] for k in sorted(counts)}}
    return out


def _record_is_ok(record: dict) -> bool:
    return record.get("ok") is True


# ------------------------------------------------------------------ score spec

def _brief_hash_12(brief: dict) -> str:
    """Same rule as ``hornlab_search.design.generated.brief_hash`` (sha256[:12], no path)."""
    body = {k: v for k, v in brief.items() if k != "path"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]


def resolve_ath_spec(config_path: str | Path | None = None,
                     brief_path: str | Path | None = None) -> dict:
    """Read the resolved candidate task/brief (read-only) into a cohort/score spec.

    Defaults to the parent-verified ``native__ath_core_v4`` config and its real brief.  The
    spec carries the resolved target/weights/tolerances; it is data, not a new config.
    """
    cfg_path = Path(config_path) if config_path else (
        REPO / "examples" / "typologies" / "campaign_2026-10-26_v4" /
        "native__ath_core_v4.yaml")
    cfg = read_yaml(cfg_path)
    bpath = Path(brief_path) if brief_path else None
    if bpath is None and isinstance(cfg, dict) and cfg.get("brief_file"):
        bpath = (cfg_path.parent / str(cfg["brief_file"])).resolve()
    brief = read_yaml(bpath) if bpath is not None else None
    if not isinstance(cfg, dict) or not isinstance(brief, dict):
        return {
            "status": "insufficient_evidence",
            "reason": "ath_spec_unavailable",
            "config_path": str(cfg_path),
            "brief_path": None if bpath is None else str(bpath),
            "config_readable": isinstance(cfg, dict),
            "brief_readable": isinstance(brief, dict),
        }
    target = brief.get("target") if isinstance(brief.get("target"), dict) else {}
    objective = brief.get("objective") if isinstance(brief.get("objective"), dict) else {}
    weights = brief.get("weights") if isinstance(brief.get("weights"), dict) else {}
    return {
        "status": "ok",
        "name": cfg.get("name"),
        "config_path": str(cfg_path),
        "brief_path": str(bpath),
        "brief": brief.get("name"),
        "brief_hash": _brief_hash_12(brief),
        "family": cfg.get("family"),
        "objective_version": objective.get("version"),
        "target": {
            "coverage_h_deg": target.get("coverage_h_deg"),
            "coverage_v_deg": target.get("coverage_v_deg"),
            "band_lo_hz": target.get("band_lo_hz"),
            "band_hi_hz": target.get("band_hi_hz"),
            "f0_hz": target.get("f0_hz"),
            "freq_weights": target.get("freq_weights"),
        },
        "weights": dict(weights),
        "tolerances": objective.get("tolerances") if isinstance(objective.get("tolerances"), dict)
        else {},
        "cov_narrow_ratio": objective.get("cov_narrow_ratio"),
        "cov_below_f0": objective.get("cov_below_f0", "mask"),
        "diag_reference": objective.get("diag_reference", "round"),
        "backend": (cfg.get("solve") or {}).get("backend")
        if isinstance(cfg.get("solve"), dict) else None,
        "note": "resolved from the real config + brief; never substitutes inline YAML targets",
    }


def attach_score_spec(records: list[dict], spec: dict | None) -> list[dict]:
    """Return copies with the resolved score spec attached where the record matches it.

    A record whose brief/hash does not match keeps ``score_parameters_known=False``; nothing is
    inferred or silently filled.
    """
    if not spec or spec.get("status") != "ok":
        return records
    spec_hash = hashlib.sha256(json.dumps(
        {k: spec.get(k) for k in ("brief", "brief_hash", "objective_version", "target",
                                  "weights", "tolerances", "cov_narrow_ratio",
                                  "cov_below_f0", "diag_reference")},
        sort_keys=True, default=str).encode()).hexdigest()[:16]
    out: list[dict] = []
    for record in records:
        r = dict(record)
        prov = _prov(r)
        same = (prov.get("brief") == spec.get("brief")
                and (spec.get("brief_hash") is None
                     or prov.get("brief_hash") == spec.get("brief_hash"))
                and (spec.get("objective_version") is None
                     or r.get("objective_version") == spec.get("objective_version")))
        if same:
            r["score_spec"] = {
                "brief": spec.get("brief"), "brief_hash": spec.get("brief_hash"),
                "brief_path": spec.get("brief_path"),
                "objective_version": spec.get("objective_version"),
                "target": spec.get("target"), "weights": spec.get("weights"),
                "tolerances": spec.get("tolerances"),
                "cov_narrow_ratio": spec.get("cov_narrow_ratio"),
                "cov_below_f0": spec.get("cov_below_f0"),
                "diag_reference": spec.get("diag_reference"),
                "spec_hash": spec_hash,
            }
            r["score_parameters_known"] = True
            # A score identity is target+version+brief+full spec+terms schema; the terms values
            # are results, not identity.
            r["score_identity"] = hashlib.sha256(json.dumps(
                {"objective_version": r.get("objective_version"),
                 "target_hash": r.get("target_hash"),
                 "brief_hash": prov.get("brief_hash"),
                 "spec_hash": spec_hash,
                 "terms_keys": (r.get("terms") or {}).get("keys")},
                sort_keys=True, default=str).encode()).hexdigest()[:16]
        else:
            # The caller supplied one resolved spec; a record that does not match it has no
            # verified weights/tolerances for this comparison.
            r["score_parameters_known"] = False
            r.pop("score_spec", None)
        out.append(r)
    return out


# ------------------------------------------------------------------ ATH census


def _record_matches_ath(record: dict, spec: dict) -> tuple[bool, str | None]:
    prov = _prov(record)
    if not prov.get("brief"):
        return False, "brief_missing"
    if spec.get("brief") and prov.get("brief") != spec.get("brief"):
        return False, "brief_mismatch"
    if spec.get("brief_hash") and prov.get("brief_hash") != spec.get("brief_hash"):
        return False, "brief_hash_mismatch"
    if spec.get("family") and record.get("family") != spec.get("family"):
        return False, "family_mismatch"
    if record.get("objective_version") != spec.get("objective_version"):
        return False, "objective_version_mismatch"
    target = record.get("target") or {}
    expected = spec.get("target") or {}
    for key in ("band_lo_hz", "band_hi_hz", "f0_hz", "coverage_h_deg", "coverage_v_deg"):
        if expected.get(key) is None:
            continue
        if target.get(key) != expected.get(key):
            return False, f"target_{key}_mismatch"
    return True, None


def _group_key(record: dict, keys: Iterable[str]) -> tuple:
    return tuple(json.dumps(field_value(record, k), sort_keys=True, default=str) for k in keys)


def _count_group(records: list[dict]) -> dict:
    ok = [r for r in records if _record_is_ok(r)]
    failed = [r for r in records if not _record_is_ok(r)]
    complete = [r for r in ok if (r.get("completeness") or {}).get("complete_replayable")]
    missing_score: Counter[str] = Counter()
    missing_loading: Counter[str] = Counter()
    shape_issues: Counter[str] = Counter()
    gate_failures: Counter[str] = Counter()
    unknowns: Counter[str] = Counter()
    for r in ok:
        comp = r.get("completeness") or {}
        for k in comp.get("missing_score_arrays") or []:
            missing_score[k] += 1
        for k in comp.get("missing_loading_arrays") or []:
            missing_loading[k] += 1
        for k in comp.get("shape_issues") or []:
            shape_issues[k] += 1
        for k in comp.get("gate_failures") or []:
            gate_failures[k] += 1
    for r in records:
        for k in r.get("unknowns") or []:
            unknowns[k] += 1
    experiments = {r.get("experiment_id") for r in ok if r.get("experiment_id")}
    return {
        "n_records": len(records),
        "n_ok": len(ok),
        "n_failed": len(failed),
        "n_unique_physical_solves": len({r.get("physical_solve_id") for r in ok
                                         if r.get("physical_solve_id")}),
        "n_unique_geometries": len({r.get("geometry_id") for r in ok
                                    if r.get("geometry_id")}),
        "n_unique_score_identities": len({r.get("score_identity") for r in ok
                                          if r.get("score_identity")}),
        "n_independent_experiments_known": len(experiments),
        "n_records_experiment_unknown": sum(1 for r in records if not r.get("experiment_id")),
        "n_complete_replayable": len(complete),
        "n_partial_unsupported": sum(
            1 for r in ok if (r.get("completeness") or {}).get("classification")
            == "partial_unsupported"),
        "n_partial_loading_inputs": sum(
            1 for r in ok if (r.get("completeness") or {}).get("classification")
            == "partial_loading_inputs"),
        "n_shape_incoherent": sum(
            1 for r in ok if (r.get("completeness") or {}).get("classification")
            == "shape_incoherent"),
        "n_gate_incomplete": sum(
            1 for r in ok if (r.get("completeness") or {}).get("classification")
            == "gate_incomplete"),
        "n_torn_artifact": sum(
            1 for r in ok if (r.get("completeness") or {}).get("classification")
            == "torn_artifact"),
        "n_missing_npz": sum(
            1 for r in ok if (r.get("completeness") or {}).get("classification")
            == "missing_npz"),
        "missing_arrays": dict(sorted(missing_score.items())),
        "missing_loading_inputs": dict(sorted(missing_loading.items())),
        "shape_issues": dict(sorted(shape_issues.items())),
        "gate_failures": dict(sorted(gate_failures.items())),
        "failures_by_type": dict(sorted(Counter(
            r.get("failure_kind") for r in failed if r.get("failure_kind")).items())),
        "unknown_field_counts": dict(sorted(unknowns.items())),
        "run_ids": sorted(experiments),
        "configs": sorted({r.get("config_name") for r in records if r.get("config_name")}),
        "software_hashes": dict(sorted(Counter(
            r.get("software_hash") for r in records if r.get("software_hash")).items())),
        "own_commits": dict(sorted(Counter(
            r.get("own_commit") for r in records if r.get("own_commit")).items())),
        "grid_hashes": sorted({r.get("grid_hash") for r in records if r.get("grid_hash")}),
        "target_hashes": sorted({r.get("target_hash") for r in records
                                 if r.get("target_hash")}),
    }


def _status_for_group(counts: dict, min_geometries: int) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if counts["n_complete_replayable"] < min_geometries:
        reasons.append("fewer_complete_replayable_than_min_geometries")
    if counts["n_unique_geometries"] < min_geometries:
        reasons.append("fewer_unique_geometries_than_min_geometries")
    if reasons:
        return "insufficient_evidence", reasons
    if counts["n_records_experiment_unknown"] > 0:
        return "eligible_with_provenance_gaps", ["experiment_identity_unknown_for_some_rows"]
    return "eligible", []


def ath_census(records: list[dict], spec: dict | None = None, *,
               group_by: Iterable[str] = ("config_name", "family", "fidelity", "backend",
                                          "dependency_hash"),
               min_geometries: int = ATH_MIN_GEOMETRIES,
               config_filter: str | None = None,
               family_filter: str | None = None) -> dict:
    """Count the resolved ATH cohort without pooling unrelated physical configurations.

    The default group key includes ``config_name`` and ``family``: sharing a brief/objective
    is not enough to pool two physical search configurations.  A caller may additionally
    restrict the census by recorded ``config_name`` / ``family`` (the native-only census).
    """
    spec = spec or resolve_ath_spec()
    if not spec or spec.get("status") != "ok":
        return {
            "tool": TOOL,
            "operation": "ath_census",
            "status": "insufficient_evidence",
            "reason": (spec or {}).get("reason", "ath_spec_unavailable"),
            "spec": spec,
            "counts": {},
            "groups": [],
            "policy": {"pool_across_groups": False},
        }
    matched: list[dict] = []
    excluded: Counter[str] = Counter()
    for r in records:
        if r.get("excluded"):
            excluded[f"excluded_{r.get('excluded')}"] += 1
            continue
        ok, why = _record_matches_ath(r, spec)
        if ok:
            matched.append(r)
        else:
            excluded[str(why or "unknown")] += 1
    enriched = attach_score_spec(matched, spec)

    # Descriptive per-config table: kept separate from any pooled/trainable claim.
    descriptive_configs: list[dict] = []
    by_config: dict[tuple, list[dict]] = defaultdict(list)
    for r in enriched:
        by_config[_group_key(r, ("config_name", "family"))].append(r)
    for key in sorted(by_config, key=lambda k: tuple(str(x) for x in k)):
        rows = by_config[key]
        cfg, fam = [json.loads(v) for v in key]
        counts = _count_group(rows)
        descriptive_configs.append({
            "config_name": cfg,
            "family": fam,
            "counts": counts,
            "eligible_for_training": False,
            "note": "descriptive only; configurations are not pooled solely for sharing a "
                    "brief/objective",
        })
    descriptive_configs.sort(key=lambda d: (-d["counts"]["n_complete_replayable"],
                                            str(d["config_name"]), str(d["family"])))

    filtered: list[dict] = []
    for r in enriched:
        if config_filter is not None:
            if not r.get("config_name"):
                excluded["config_unknown_filter"] += 1
                continue
            if r.get("config_name") != config_filter:
                excluded["config_filter_mismatch"] += 1
                continue
        if family_filter is not None:
            if r.get("family") != family_filter:
                excluded["family_filter_mismatch"] += 1
                continue
        filtered.append(r)

    groups: list[dict] = []
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    keys = tuple(group_by)
    for r in filtered:
        grouped[_group_key(r, keys)].append(r)
    for key in sorted(grouped, key=lambda k: tuple(str(x) for x in k)):
        rows = grouped[key]
        counts = _count_group(rows)
        status, reasons = _status_for_group(counts, min_geometries)
        lib_shas = (rows[0].get("lib_shas") or {}) if rows else {}
        groups.append({
            "group": dict(zip(keys, [json.loads(v) for v in key])),
            "dependency_shas": {k: lib_shas.get(k) for k in _EXTERNAL_LIBS},
            "status": status,
            "reason_codes": reasons,
            "counts": counts,
        })
    # Totals are descriptive only; the policy forbids pooling across the groups for training.
    totals = _count_group(filtered)
    eligible = [g for g in groups if g["status"] in ("eligible", "eligible_with_provenance_gaps")]
    groups.sort(key=lambda g: (-g["counts"]["n_complete_replayable"],
                               json.dumps(g["group"], sort_keys=True, default=str)))
    primary = groups[0] if groups else None
    if eligible:
        status = "eligible" if all(g["status"] == "eligible" for g in eligible) \
            else "eligible_with_provenance_gaps"
    else:
        status = "insufficient_evidence"
    reason_codes = [] if eligible else ["no_group_reaches_min_geometries"]
    if totals.get("n_records_experiment_unknown"):
        reason_codes.append("experiment_identity_unknown_for_some_rows")
    return {
        "tool": TOOL,
        "operation": "ath_census",
        "status": status,
        "reason_codes": reason_codes,
        "eligibility": {
            "complete_replayable_data": ("eligible" if eligible
                                         else "insufficient_evidence"),
            "independent_experiments": ("ok" if not totals.get(
                "n_records_experiment_unknown") else "insufficient_evidence"),
            "overall": status,
        },
        "min_geometries": min_geometries,
        "spec": spec,
        "filter": {
            "config_name": config_filter,
            "family": family_filter,
            "native_only": config_filter == NATIVE_CONFIG,
        },
        "policy": {
            "pool_across_groups": False,
            "pool_across_configs": False,
            "descriptive_configs_not_pooled": True,
            "group_by": list(keys),
            "rule": "config/family, screen/verify, backend and external dependency identity "
                    "are separate cohorts; a total across groups is descriptive only",
            "array_rule": "complete replayable v4 requires h/v angles, h/v SPL, balloon_dirs, "
                          "spl_balloon_db and on_axis_db; z_throat/loading is separate and a "
                          "missing loading input is never complete",
        },
        "matched_records_before_filter": len(enriched),
        "matched_records": len(filtered),
        "excluded_records": dict(sorted(excluded.items())),
        "totals_descriptive_only": totals,
        "descriptive_configs": descriptive_configs,
        "independent_experiments": {
            "known": totals.get("n_independent_experiments_known", 0),
            "records_experiment_unknown": totals.get(
                "n_records_experiment_unknown", 0),
            "status": ("ok" if not totals.get("n_records_experiment_unknown")
                       else "insufficient_evidence"),
            "note": "run_id is the only recorded experiment identity; absence is not "
                    "inferred from timestamps or config names",
        },
        "primary_group": primary,
        "groups": groups,
    }


def ath_native_census(records: list[dict], spec: dict | None = None, **kwargs) -> dict:
    """The native ``native__ath_core_v4`` physical configuration only (not pooled)."""
    kwargs.setdefault("config_filter", NATIVE_CONFIG)
    return ath_census(records, spec, **kwargs)


# ------------------------------------------------------------------ comparability


def compare_operation(records: list[dict], operation: str, *,
                      spec: dict | None = None) -> dict:
    """Assess whether records are comparable for ``operation``.

    Returns ``status`` in ``compatible | compatible_with_unknowns | incompatible |
    insufficient_evidence``, the required/allowed field variants, blocking reasons, allowed
    differences and operation-specific pairs/treatments.
    """
    if operation not in _OP_POLICY:
        raise ValueError(f"unknown operation {operation!r}; expected one of {OPERATIONS}")
    policy = _OP_POLICY[operation]
    if spec is not None:
        records = attach_score_spec(records, spec)
    ok = [r for r in records if _record_is_ok(r) and not r.get("excluded")]
    failed = [r for r in records if not _record_is_ok(r) and not r.get("excluded")]
    excluded = sum(1 for r in records if r.get("excluded"))
    base = {
        "tool": TOOL,
        "operation": operation,
        "policy": policy,
        "n_records": len(records),
        "n_ok": len(ok),
        "n_failed_excluded": len(failed),
        "n_excluded": excluded,
    }
    if not ok:
        base.update({"status": "insufficient_evidence",
                     "reason_codes": ["no_successful_records"],
                     "compatible_for_inference": False,
                     "compatible_for_descriptive": False})
        return base
    required = tuple(policy["required"])
    allowed = tuple(policy["allowed"])
    req_variants = _variant_map(ok, required)
    all_variants = _variant_map(ok, allowed)
    blocking: list[str] = []
    warnings: list[str] = []
    for key, info in req_variants.items():
        if info["n_variants"] > 1:
            blocking.append(f"{key}_mismatch")
        if any(v is None for v in info["values"]):
            blocking.append(f"{key}_unknown")
    if any(not r.get("score_parameters_known") for r in ok):
        warnings.append("score_parameters_unknown")
    allowed_differences = [
        {"key": key, "n_variants": info["n_variants"], "values": info["values"],
         "counts": info["counts"]}
        for key, info in sorted(all_variants.items()) if info["n_variants"] > 1
    ]
    treatments = sorted({r.get("treatment_id") for r in ok if r.get("treatment_id")})
    if policy.get("treatments"):
        if len(treatments) < 2:
            blocking.append("treatment_not_varied" if len(treatments) == 1
                            else "treatment_identity_unknown")
        if any(not r.get("treatment_id") for r in ok):
            blocking.append("treatment_identity_unknown")
    pairs: list[dict] = []
    pair_by = policy.get("pairs_by")
    if pair_by:
        grouped: dict[tuple, list[dict]] = defaultdict(list)
        for r in ok:
            grouped[_group_key(r, pair_by)].append(r)
        for key in sorted(grouped, key=lambda k: tuple(str(x) for x in k)):
            rows = grouped[key]
            if operation == "backend_parity":
                variants = sorted({r.get("backend") for r in rows if r.get("backend")})
                if len(variants) > 1:
                    pairs.append({"pair": dict(zip(pair_by, [json.loads(v) for v in key])),
                                  "backends": variants,
                                  "n_records": len(rows)})
            elif operation == "fidelity_comparison":
                variants = sorted({r.get("fidelity") for r in rows if r.get("fidelity")})
                if len(variants) > 1:
                    pairs.append({"pair": dict(zip(pair_by, [json.loads(v) for v in key])),
                                  "fidelities": variants,
                                  "n_records": len(rows)})
    unique_blocking = sorted(set(blocking))
    if unique_blocking:
        status = "incompatible"
    elif warnings:
        status = "compatible_with_unknowns"
    else:
        status = "compatible"
    task_blockers = [b for b in unique_blocking
                     if b.split("_", 1)[0] in ("brief", "family", "objective", "target")]
    return {
        **base,
        "status": status,
        "reason_codes": unique_blocking,
        "warnings": sorted(set(warnings)),
        "required_equal": list(required),
        "allowed_differences": allowed_differences,
        "variants": {"required": req_variants, "allowed": all_variants},
        "blocking": unique_blocking,
        "compatible_for_inference": not unique_blocking,
        "compatible_for_descriptive": not task_blockers,
        "treatments": treatments,
        "pairs": pairs,
        "n_pairs": len(pairs),
    }


# ------------------------------------------------------------------ output


def deterministic_payload(payload: dict, *, generated_utc: str | None = None) -> dict:
    doc = dict(payload)
    doc.setdefault("schema_version", SCHEMA_VERSION)
    doc.setdefault("tool", TOOL)
    doc["generated_utc"] = generated_utc or utc_now()
    return jsonable(doc)


def _md(payload: dict) -> str:
    lines = ["# Cohorts", "", f"- operation: **{payload.get('operation')}**",
             f"- status: **{payload.get('status')}**",
             f"- generated: `{payload.get('generated_utc')}`", ""]
    if payload.get("reason_codes"):
        lines.append(f"- reason codes: `{', '.join(payload['reason_codes'])}`")
    if payload.get("warnings"):
        lines.append(f"- warnings: `{', '.join(payload['warnings'])}`")
    if payload.get("policy"):
        pol = payload["policy"]
        lines.append(f"- required equal: `{', '.join(pol.get('required', []))}`")
        lines.append(f"- allowed differences: `{', '.join(pol.get('allowed', []))}`")
        if pol.get("note"):
            lines.append(f"- note: {pol['note']}")
    if payload.get("operation") == "ath_census":
        spec = payload.get("spec") or {}
        lines += ["", "## Resolved ATH task", "",
                  f"- config: `{spec.get('config_path')}`",
                  f"- brief: `{spec.get('brief')}` (`{spec.get('brief_hash')}`)",
                  f"- objective v{spec.get('objective_version')}; target "
                  f"{spec.get('target')}",
                  f"- matched records: **{payload.get('matched_records')}**; "
                  f"excluded: `{payload.get('excluded_records')}`",
                  f"- group rule: {payload.get('policy', {}).get('rule')}",
                  "", "## Groups", ""]
        for g in payload.get("groups") or []:
            c = g.get("counts") or {}
            lines.append(f"### `{g.get('group')}` — {g.get('status')}")
            lines.append(f"- records/ok/failed: **{c.get('n_records')} / {c.get('n_ok')} / "
                         f"{c.get('n_failed')}**")
            lines.append(f"- unique solves / geometries / experiments known: "
                         f"**{c.get('n_unique_physical_solves')} / "
                         f"{c.get('n_unique_geometries')} / "
                         f"{c.get('n_independent_experiments_known')}**")
            lines.append(f"- complete replayable: **{c.get('n_complete_replayable')}**; "
                         f"partial unsupported/loading/gate/torn: "
                         f"**{c.get('n_partial_unsupported')} / "
                         f"{c.get('n_partial_loading_inputs')} / "
                         f"{c.get('n_gate_incomplete')} / {c.get('n_torn_artifact')}**")
            lines.append(f"- missing arrays: `{c.get('missing_arrays')}`; failures: "
                         f"`{c.get('failures_by_type')}`")
            lines.append(f"- experiment id unknown rows: "
                         f"**{c.get('n_records_experiment_unknown')}**")
        lines.append("")
        return "\n".join(lines)
    if payload.get("allowed_differences"):
        lines += ["", "## Allowed differences", ""]
        for d in payload["allowed_differences"]:
            lines.append(f"- `{d['key']}`: {d['n_variants']} variants `{d['values']}`")
    if payload.get("blocking"):
        lines += ["", "## Blocking", ""]
        for b in payload["blocking"]:
            lines.append(f"- `{b}`")
    if payload.get("pairs"):
        lines += ["", "## Pairs", ""]
        for p in payload["pairs"]:
            lines.append(f"- `{p.get('pair')}`: {p.get('backends') or p.get('fidelities')}")
    lines.append("")
    return "\n".join(lines)


def write_cohorts(payload: dict, out_dir: str | Path, *,
                  generated_utc: str | None = None, csv_export: bool = True) -> dict:
    out = Path(out_dir)
    # Refuse to write into a dataset root if the caller included one in the payload.
    for root in (payload.get("source_roots") or []):
        try:
            out.resolve().relative_to(Path(root).resolve())
            raise ValueError(f"refusing to write inside an input dataset root: {out}")
        except ValueError as exc:
            if "refusing" in str(exc):
                raise
        except OSError:
            pass
    doc = deterministic_payload(payload, generated_utc=generated_utc)
    out.mkdir(parents=True, exist_ok=True)
    jpath = out / "cohorts.json"
    jpath.write_text(json.dumps(doc, indent=1, sort_keys=True, allow_nan=False,
                                ensure_ascii=False) + "\n", encoding="utf-8")
    mpath = out / "cohorts.md"
    mpath.write_text(_md(doc), encoding="utf-8")
    written = {"json": str(jpath), "md": str(mpath)}
    if csv_export:
        cpath = out / "cohorts.csv"
        with cpath.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["operation", "group", "status", "records", "ok", "failed",
                               "unique_solves", "unique_geometries",
                               "experiments_known", "experiment_unknown",
                               "complete_replayable", "partial_unsupported",
                               "partial_loading", "gate_incomplete", "torn_artifact",
                               "missing_arrays", "failures_by_type"],
                lineterminator="\n")
            writer.writeheader()
            if doc.get("operation") == "ath_census":
                for g in doc.get("groups") or []:
                    c = g.get("counts") or {}
                    writer.writerow({
                        "operation": doc.get("operation"),
                        "group": json.dumps(g.get("group"), sort_keys=True, default=str),
                        "status": g.get("status"),
                        "records": c.get("n_records"), "ok": c.get("n_ok"),
                        "failed": c.get("n_failed"),
                        "unique_solves": c.get("n_unique_physical_solves"),
                        "unique_geometries": c.get("n_unique_geometries"),
                        "experiments_known": c.get("n_independent_experiments_known"),
                        "experiment_unknown": c.get("n_records_experiment_unknown"),
                        "complete_replayable": c.get("n_complete_replayable"),
                        "partial_unsupported": c.get("n_partial_unsupported"),
                        "partial_loading": c.get("n_partial_loading_inputs"),
                        "gate_incomplete": c.get("n_gate_incomplete"),
                        "torn_artifact": c.get("n_torn_artifact"),
                        "missing_arrays": json.dumps(c.get("missing_arrays") or {},
                                                     sort_keys=True),
                        "failures_by_type": json.dumps(c.get("failures_by_type") or {},
                                                       sort_keys=True),
                    })
            else:
                writer.writerow({"operation": doc.get("operation"),
                                 "group": "all", "status": doc.get("status"),
                                 "records": doc.get("n_records"), "ok": doc.get("n_ok"),
                                 "failed": doc.get("n_failed_excluded")})
        written["csv"] = str(cpath)
    return written


# ------------------------------------------------------------------ CLI


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="cohorts.py",
        description="Operation-specific cohort comparability and the resolved ATH census "
                    "(read-only over dataset shards).",
    )
    ap.add_argument("--root", action="append", required=True,
                    help="dataset root holding shard-*.jsonl (repeat for dataset_cpu, ...)")
    add_out_arg(ap)
    ap.add_argument("--operation", default="ath_census",
                    choices=("ath_census",) + OPERATIONS,
                    help="ath_census (default) or a comparability operation")
    ap.add_argument("--config", default=None,
                    help="ATH resolved config YAML (default: the campaign native__ath_core_v4)")
    ap.add_argument("--brief", default=None,
                    help="brief YAML for the ATH task / score spec (default: config brief_file)")
    ap.add_argument("--fidelity", default=None, choices=("screen", "verify", "final"),
                    help="filter to one fidelity before a comparability operation")
    ap.add_argument("--backend", default=None, help="filter to one backend")
    ap.add_argument("--limit", type=int, default=None,
                    help="max shard records processed per root (bounded pilot)")
    ap.add_argument("--no-csv", action="store_true", help="skip the CSV export")
    args = ap.parse_args(argv)
    try:
        cat = catalog.build_catalog(args.root, limit=args.limit)
        spec = resolve_ath_spec(args.config, args.brief)
        records = cat.get("records") or []
        if args.operation == "ath_census":
            payload = ath_census(records, spec)
            payload["source_roots"] = [str(Path(r)) for r in args.root]
            payload["catalog_counts"] = cat.get("counts") or {}
        else:
            selected = records
            if args.fidelity:
                selected = [r for r in selected if r.get("fidelity") == args.fidelity]
            if args.backend:
                selected = [r for r in selected if r.get("backend") == args.backend]
            payload = compare_operation(selected, args.operation, spec=spec)
            payload["source_roots"] = [str(Path(r)) for r in args.root]
            payload["catalog_counts"] = cat.get("counts") or {}
        written = write_cohorts(payload, args.out, csv_export=not args.no_csv)
    except (OSError, ValueError) as exc:
        raise fail(str(exc))
    print(f"cohorts OK: operation={payload.get('operation')} status={payload.get('status')}")
    for g in payload.get("groups") or []:
        c = g.get("counts") or {}
        print(f"  group={g.get('group')} status={g.get('status')} "
              f"records={c.get('n_records')} complete={c.get('n_complete_replayable')} "
              f"solves={c.get('n_unique_physical_solves')} "
              f"geoms={c.get('n_unique_geometries')} "
              f"experiments_known={c.get('n_independent_experiments_known')} "
              f"experiment_unknown={c.get('n_records_experiment_unknown')}")
    print(f"  json={written['json']}")
    if "csv" in written:
        print(f"  csv={written['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
