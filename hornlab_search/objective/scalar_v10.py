"""Objective v10 PROPOSAL (2026-11-18, PR-A, OWNER-GATED): v9 with an explicit ripple region.

v10 is v9 in every term except ``rip``. v9's per-frequency ripple window
(``scalar_v9._v9_ripple_values``) passes ``max - min`` (corridor mode) or ``2 * preferred``
(target mode) to :func:`ripple_detrended_db`, which reads its argument as a TOTAL polar angle
and inspects ``+/- angle/2``. Code-verified semantics (2026-11-18, PR #67 head 319003c):

* ``polar.beamwidth_deg`` returns the TOTAL included angle between the -6 dB crossings, and
  ``scalar_v9._plane_cov_cost`` compares ``bw_h_deg`` directly against ``preferred_deg`` /
  ``min_deg`` / ``max_deg``. So profile angles are FULL beamwidths, not half-angles.
* Hence v9 corridor mode inspects ``+/- (max-min)/2`` (a 70-90 deg corridor scores +/-10 deg),
  and v9 target mode inspects ``+/- preferred`` (an 80 deg target scores +/-80 deg, twice the
  -6 dB edge at +/-40 deg). The v9 docstring ("the width whose -6 dB edges sit at
  ``preferred``") holds only if ``preferred`` were a half-angle, which it is not.

v9 J is immutable (historical runs, owner rule): ``scalar_v9.py`` is not edited. v10 instead
REQUIRES an explicit ``objective.ripple_region`` - there is NO default; the policy is the
owner's (audit 01 section 4.1) and a brief that omits it is refused:

* ``ripple_region: preferred_edge`` - inspect ``+/- preferred/2`` (the preferred -6 dB edges);
* ``ripple_region: min_edge`` - inspect ``+/- min/2`` (the guaranteed-minimum edges; corridor
  mode only, refused for a target-mode profile);
* ``ripple_region: max_edge`` - inspect ``+/- max/2`` (the widest permitted edges; corridor mode
  only). Added 2026-11-18 after E1: ``min_edge`` cannot see a mid-corridor defect;
* ``ripple_region: {mode: seat_zone_deg, h_deg: H, v_deg: V}`` - an explicitly declared TOTAL
  inspected angle per plane, constant over frequency.

Everything else (term set, tolerances, weights, masks, penalties, ``score_grid``) is v9's,
reused through v9's own helpers. The score identity differs from v9 by construction: the
stored block carries ``version: 10`` and the ``ripple_region`` (``v10_score_identity``).

``objective_v10`` never raises and never returns nan or inf. Pure numpy, no solver.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from dataclasses import dataclass

import numpy as np

from ..metrics.smoothness import ripple_detrended_db
from ..targets.spec import Target
from .scalar_v2 import (_cut_arrays, _objective_v3, _plain_mean, _v2_flat_value,
                        _weighted_mean, freq_weight_vector)
from .scalar_v4 import _diag_term
from .scalar_v7 import _flat_cv_term, _load_v7
from .scalar_v9 import (V9_ALL_KEYS, V9_DIAGNOSTIC_KEYS, V9_WEIGHTED_KEYS, V9Params,
                        _constancy_term, _cov_n_in_band, _cov_profile_term, _di_roughness,
                        _hf_floor_term, _on_score_grid, _plane_anchors, _profile_at,
                        _profile_mode, _v9_penalty, resolve_v9_weights, worst_valid_v9_j)
from .terms import PENALTY_FAILED, WEIGHTED_KEYS

log = logging.getLogger("hornlab_search.objective.scalar_v10")

__all__ = ["objective_v10", "V10Params", "V10_ALL_KEYS", "V10_RIPPLE_REGIONS",
           "V10_SCORE_IDENTITY_NAME", "resolve_v10_weights", "worst_valid_v10_j",
           "v10_inspected_total_deg", "v10_score_identity"]

#: v10 reports exactly v9's key set (only the meaning of ``rip`` changes).
V10_ALL_KEYS = V9_ALL_KEYS
V10_RIPPLE_REGIONS = ("preferred_edge", "min_edge", "max_edge", "seat_zone_deg")
V10_SCORE_IDENTITY_NAME = "objective_v10_ripple_region"
_SEAT_KEYS = {"mode", "h_deg", "v_deg"}
_MAX_TOTAL_DEG = 360.0


def _validate_ripple_region(raw) -> dict:
    """Normalise ``objective.ripple_region``; raises ``ValueError``. No default exists."""
    if raw is None:
        raise ValueError("objective v10 requires objective.ripple_region (no default; owner "
                         f"policy): one of {list(V10_RIPPLE_REGIONS)}")
    if isinstance(raw, str):
        if raw == "seat_zone_deg":
            raise ValueError("objective.ripple_region seat_zone_deg needs a mapping "
                             "{mode: seat_zone_deg, h_deg: <total deg>, v_deg: <total deg>}")
        if raw not in V10_RIPPLE_REGIONS:
            raise ValueError(f"objective.ripple_region must be one of {list(V10_RIPPLE_REGIONS)}, "
                             f"got {raw!r}")
        return {"mode": raw}
    if not isinstance(raw, dict):
        raise ValueError(f"objective.ripple_region must be a string or mapping, got {raw!r}")
    mode = raw.get("mode")
    if mode not in V10_RIPPLE_REGIONS:
        raise ValueError(f"objective.ripple_region.mode must be one of {list(V10_RIPPLE_REGIONS)}, "
                         f"got {mode!r}")
    if mode != "seat_zone_deg":
        extra = sorted(set(raw) - {"mode"})
        if extra:
            raise ValueError(f"objective.ripple_region {mode} takes no other keys, got {extra}")
        return {"mode": mode}
    extra = sorted(set(raw) - _SEAT_KEYS)
    if extra:
        raise ValueError(f"objective.ripple_region unknown key(s) {extra} "
                         f"(allowed: {sorted(_SEAT_KEYS)})")
    out = {"mode": "seat_zone_deg"}
    for k in ("h_deg", "v_deg"):
        v = raw.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) \
                or not 0.0 < float(v) <= _MAX_TOTAL_DEG:
            raise ValueError(f"objective.ripple_region.{k} must be a TOTAL angle in "
                             f"(0, {_MAX_TOTAL_DEG:g}] deg, got {v!r}")
        out[k] = float(v)
    return out


@dataclass(frozen=True)
class V10Params:
    """A v10 ``objective:`` block: a validated :class:`V9Params` plus ``ripple_region``."""

    v9: V9Params
    ripple_region: dict

    def __getattr__(self, name):
        # Callers that read v9 fields (tolerances, score_grid, hf_floor, ...) see v9's values.
        if name in ("v9", "ripple_region"):
            raise AttributeError(name)
        return getattr(self.v9, name)

    def weighted_keys(self) -> tuple[str, ...]:
        return self.v9.weighted_keys()

    @classmethod
    def from_block(cls, block: dict) -> "V10Params":
        if not isinstance(block, dict):
            raise ValueError("objective must be a mapping")
        if "version" in block and block["version"] != 10:
            raise ValueError(f"V10Params needs objective.version 10, got {block['version']!r}")
        region = _validate_ripple_region(block.get("ripple_region"))
        rest = {k: v for k, v in block.items() if k not in ("ripple_region", "version")}
        rest["version"] = 9          # V9Params ignores the value; keep its key check intact
        return cls(v9=V9Params.from_block(rest), ripple_region=region)

    def to_block(self) -> dict:
        out = self.v9.to_block()
        out["version"] = 10
        out["ripple_region"] = dict(self.ripple_region)
        return out


def v10_score_identity(params: V10Params) -> dict:
    """Stable identity of a v10 scoring definition: name + normalised block + sha256."""
    block = params.to_block()
    canon = json.dumps(block, sort_keys=True, separators=(",", ":"))
    return {"name": V10_SCORE_IDENTITY_NAME, "block": block,
            "sha256": hashlib.sha256(canon.encode("utf-8")).hexdigest()}


def resolve_v10_weights(weights: dict | None, params: V10Params | None = None) -> dict:
    return resolve_v9_weights(weights, None if params is None else params.v9)


def worst_valid_v10_j(params: V10Params, weights: dict | None) -> float:
    return worst_valid_v9_j(params.v9, weights)


def v10_inspected_total_deg(target: Target, plane: str, freq_hz: float, region: dict) -> float:
    """The TOTAL polar angle v10 inspects for ``plane`` at ``freq_hz`` (window is +/- half)."""
    mode = region["mode"]
    if mode == "seat_zone_deg":
        return float(region["h_deg" if plane == "h" else "v_deg"])
    pref, lo, _hi = _profile_at(_plane_anchors(target, plane), float(freq_hz))
    if mode == "preferred_edge":
        return float(pref)
    edge = lo if mode == "min_edge" else _hi
    if edge is None or _profile_mode(target) != "corridor":
        raise ValueError(f"ripple_region {mode} needs a corridor-mode coverage profile "
                         "(min_deg/max_deg present)")
    return float(edge)


def _v10_ripple_values(metrics, resp, target: Target, band: np.ndarray, region: dict):
    """Per-frequency ``ripple_h + ripple_v`` over the declared region. No silent fallback to
    the stored v1 ripple: that pair was computed over a different window, so a missing
    Response leaves the term unmeasurable (``NAN_TERM_FILL`` via the shared mean helpers)
    instead of mixing window definitions."""
    f = np.asarray(metrics.freqs_hz, dtype=float)
    n = f.size
    out = np.full(n, np.nan)
    arrays = _cut_arrays(resp, n)
    if arrays is None:
        return out
    ha, va, sh, sv = arrays
    for j in np.flatnonzero(band):
        wh = v10_inspected_total_deg(target, "h", float(f[j]), region)
        wv = v10_inspected_total_deg(target, "v", float(f[j]), region)
        out[j] = ripple_detrended_db(ha, sh[j], wh) + ripple_detrended_db(va, sv[j], wv)
    return out


def _rip_term_v10(metrics, resp, target: Target, f: np.ndarray, band: np.ndarray,
                  region: dict) -> float:
    values = _v10_ripple_values(metrics, resp, target, band, region)
    if target.freq_weights is not None:
        m, _ = _weighted_mean(values[band], freq_weight_vector(f, target)[band])
    else:
        m, _ = _plain_mean(values[band])
    return float(m)


def objective_v10(metrics, resp, ok, target: Target, weights: dict | None, params: V10Params):
    """Score one evaluation under objective v10. ``(J, terms)``; ``terms`` has ``V10_ALL_KEYS``."""
    try:
        if not isinstance(params, V10Params):
            raise ValueError("objective_v10 needs V10Params")
        if ok and params.v9.score_grid is not None:
            metrics, resp = _on_score_grid(metrics, resp, target, params.v9)
        return _objective_v10(metrics, resp, ok, target, weights, params)
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("objective_v10() failed; returning the failure penalty")
        return _v9_penalty(PENALTY_FAILED)


def _objective_v10(metrics, resp, ok, target: Target, weights, params: V10Params):
    """Line-for-line ``scalar_v9._objective_v9`` except the ``rip`` term (kept in step by
    ``tests/test_objective_v10.py::test_v10_seat_zone_equal_to_v9_window_reproduces_v9_j``)."""
    p9 = params.v9
    if metrics is None or not ok:
        return _v9_penalty(PENALTY_FAILED)
    w = resolve_v9_weights(weights, p9)
    _, raw = _objective_v3(metrics, resp, ok, target,
                           {k: w.get(k, 0.0) for k in WEIGHTED_KEYS})
    if raw["penalty"] > 0.0:
        return _v9_penalty(float(raw["penalty"]), n_in_band=int(raw["n_in_band"]))

    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    score = band & (f >= target.f0_effective_hz())

    t_raw = {k: float(raw[k]) for k in WEIGHTED_KEYS}
    if p9.flat_band == "scored":
        t_raw["flat"] = _v2_flat_value(metrics, resp, target, score)
    t_raw["cov_profile"] = _cov_profile_term(metrics, target, f, band, p9)
    t_raw["rip"] = _rip_term_v10(metrics, resp, target, f, band, params.ripple_region)
    t_raw["dislope"] = float(raw["dislope"])
    t_raw["load"], load_diag = _load_v7(metrics, target, p9)
    t_raw["flat_cv"] = _flat_cv_term(metrics, target, f, w["flat_cv"])

    di_s = np.asarray(metrics.di_db, dtype=float)[score]
    good = di_s[np.isfinite(di_s)]
    t_raw["distd"] = float(np.std(good)) if good.size >= 2 else 0.0
    t_raw["di_roughness"] = _di_roughness(metrics, f, score)
    t_raw["hf_floor"] = _hf_floor_term(metrics, target, f, p9)
    t_raw["constancy"] = _constancy_term(metrics, target, f, band, p9)
    t_raw["diag"] = _diag_term(metrics, resp, target, f, score, p9)

    active: list[str] = list(V9_WEIGHTED_KEYS)
    hf = p9.hf_floor
    hf_tol = float(hf["tolerance"]) if hf is not None else 1.0
    if hf is not None:
        active.append("hf_floor")
    cst = p9.constancy
    if cst is not None:
        active.append("constancy")
    t = {}
    for k in active:
        tol = (hf_tol if k == "hf_floor" else float(cst["tolerance"]) if k == "constancy"
               else p9.tolerances[k])
        t[k] = t_raw[k] / tol
    if not all(math.isfinite(v) for v in t.values()):
        return _v9_penalty(PENALTY_FAILED, n_in_band=int(raw["n_in_band"]))
    total = sum(w[k] * t[k] for k in active)
    if not math.isfinite(total):
        return _v9_penalty(PENALTY_FAILED, n_in_band=int(raw["n_in_band"]))
    if hf is None:
        t["hf_floor"] = 0.0
    if cst is None:
        t["constancy"] = 0.0
    t["diag"] = float(t_raw["diag"])
    t["distd"] = float(t_raw["distd"])
    t["penalty"] = 0.0
    t["total"] = float(total)
    t["n_nan"] = raw["n_nan"]
    t["n_in_band"] = _cov_n_in_band(target, f, band, p9)
    t["di_estimated"] = raw["di_estimated"]
    for k in V9_DIAGNOSTIC_KEYS:
        t[k] = float(load_diag[k])
    assert set(t) == set(V10_ALL_KEYS)
    return float(total), t
