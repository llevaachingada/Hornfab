"""Pure historical catalog identities derived from persisted dataset metadata."""
from __future__ import annotations

import math
from typing import Any, Mapping
from .identity_v2 import sha16 as _sha16, physical_solve_id

_EXTERNAL_LIBS = ("hornlab_mesher", "hornlab_beat_bem", "hornlab_bempp_bem", "hornlab_plots")


def _finite(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _num_or_none(x) -> float | None:
    return _finite(x)


def _int_or_none(x) -> int | None:
    if x is None or isinstance(x, bool):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _str_or_none(x) -> str | None:
    if isinstance(x, str) and x:
        return x
    return None


def _dict_or_empty(x) -> dict:
    return x if isinstance(x, dict) else {}


def objective_version(meta: dict) -> tuple[int, str]:
    if "objective_version" in meta:
        v = meta.get("objective_version")
        if isinstance(v, int) and not isinstance(v, bool):
            return v, "record"
        try:
            return int(str(v)), "record_coerced"
        except (TypeError, ValueError):
            return 1, "invalid_defaults_to_v1"
    return 1, "absent_defaults_to_v1"


def lib_shas(meta: dict) -> dict[str, str]:
    raw = _dict_or_empty(meta.get("lib_shas"))
    return {str(k): str(v) for k, v in raw.items() if isinstance(v, (str, int, float))}


def _dependency_hash(shas: dict[str, str]) -> str:
    return _sha16({k: shas.get(k) for k in _EXTERNAL_LIBS})


def target_block(meta: dict) -> dict:
    target = _dict_or_empty(meta.get("target"))
    block = {
        "coverage_h_deg": _num_or_none(target.get("coverage_h_deg")),
        "coverage_v_deg": _num_or_none(target.get("coverage_v_deg")),
        "coverage_v_up_deg": _num_or_none(target.get("coverage_v_up_deg")),
        "coverage_v_down_deg": _num_or_none(target.get("coverage_v_down_deg")),
        "band_lo_hz": _num_or_none(target.get("band_lo_hz")),
        "band_hi_hz": _num_or_none(target.get("band_hi_hz")),
        "f0_hz": _num_or_none(target.get("f0_hz")),
        "f0_v_hz": _num_or_none(target.get("f0_v_hz")),
        "di_target_db": _num_or_none(target.get("di_target_db")),
        "di_slope_target": _num_or_none(target.get("di_slope_target")),
        "z_min": _num_or_none(target.get("z_min")),
        "driver_exit_radius_mm": _num_or_none(target.get("driver_exit_radius_mm")),
        "freq_weights": target.get("freq_weights"),
        "raw_keys": sorted(str(k) for k in target),
    }
    # v9 (2026-11-17, amended RFC): the coverage profile is part of the scoring identity.
    # Display passthrough pop-when-absent so legacy blocks stay byte-identical.
    profile = target.get("coverage_profile")
    if isinstance(profile, dict):
        block["coverage_profile"] = dict(profile)
        block["raw_keys"] = sorted(set(block["raw_keys"]) | {"coverage_profile"})
    return block


def target_identity(target: dict) -> dict:
    """Semantic scoring target identity; ``raw_keys`` is provenance, not scoring.

    The v9 coverage profile (2026-11-17 amendment) enters only when present â€” a
    profile-less brief keeps the exact legacy identity dict and therefore the exact
    legacy ``target_hash``, so two briefs differing only in profile can never collide."""
    identity = {k: target.get(k) for k in (
        "coverage_h_deg", "coverage_v_deg", "coverage_v_up_deg", "coverage_v_down_deg",
        "band_lo_hz", "band_hi_hz", "f0_hz", "f0_v_hz", "di_target_db",
        "di_slope_target", "z_min", "freq_weights")}
    profile = target.get("coverage_profile")
    if isinstance(profile, dict):
        identity["coverage_profile"] = dict(profile)
    return identity


def solve_block(meta: dict) -> dict:
    solve = _dict_or_empty(meta.get("solve"))
    obs = _dict_or_empty(solve.get("observation"))
    freqs = solve.get("freqs_hz")
    freqs = [round(float(f), 6) for f in freqs] if isinstance(freqs, list) else []
    return {
        "backend": _str_or_none(solve.get("backend")),
        "mode": _str_or_none(solve.get("mode")),
        "freqs_hz": freqs,
        "observation": {
            "distance_m": _num_or_none(obs.get("distance_m")),
            "angle_count": _int_or_none(obs.get("angle_count")),
            "balloon": obs.get("balloon") if isinstance(obs.get("balloon"), bool) else None,
            "balloon_points": _int_or_none(obs.get("balloon_points")),
        },
        "gmres_tol": _num_or_none(solve.get("gmres_tol")),
        "seconds": _num_or_none(solve.get("seconds")),
        "peak_vram_mb": _num_or_none(solve.get("peak_vram_mb")),
        "n_dof": _int_or_none(solve.get("n_dof")),
    }


def terms_identity(meta: dict) -> dict:
    terms = _dict_or_empty(meta.get("terms"))
    metrics = _dict_or_empty(meta.get("metrics_scalars"))
    return {
        "keys": sorted(str(k) for k in terms),
        "penalty": _num_or_none(terms.get("penalty")),
        "total": _num_or_none(terms.get("total")),
        "n_in_band": _int_or_none(terms.get("n_in_band")),
        "n_nan": _int_or_none(terms.get("n_nan")),
        "di_estimated": terms.get("di_estimated"),
        "di_source": _str_or_none(metrics.get("di_source")),
    }


def _grid_hash(solve: dict) -> str:
    return _sha16({"freqs_hz": solve.get("freqs_hz"),
                   "observation": solve.get("observation"),
                   "gmres_tol": solve.get("gmres_tol")})


def catalog_identity_from_record(meta: Mapping[str, Any]) -> dict[str, Any]:
    """Return historical catalog identities without storage I/O.

    Historical null hashing is preserved; consumers must validate completeness.
    score_hash is a catalog schema identity, not the replay per-result score ID.
    """
    target_hash = _sha16(target_identity(target_block(meta)))
    ov, _ = objective_version(meta)
    prov = _dict_or_empty(meta.get("provenance"))
    solve = solve_block(meta)
    terms = terms_identity(meta)
    score = _sha16({"objective_version": ov, "target": target_hash,
                    "brief": prov.get("brief"), "brief_hash": prov.get("brief_hash"),
                    "terms_keys": terms["keys"], "terms_schema": True})
    task = _sha16({"family": meta.get("family"), "brief": prov.get("brief"),
                   "brief_hash": prov.get("brief_hash"), "target": target_hash,
                   "objective_version": ov})
    return {"physical_solve_id": physical_solve_id(meta.get("design_hash"), meta.get("mesh_hash"), meta.get("solve_hash")),
            "task_identity": task, "grid_hash": _grid_hash(solve),
            "dependency_hash": _dependency_hash(lib_shas(meta)),
            "mesh_hash": _str_or_none(meta.get("mesh_hash")),
            "backend": solve["backend"], "fidelity": solve["mode"],
            "brief_hash": prov.get("brief_hash"), "score_hash": score}
