"""Objective v9 (2026-11-17, amended RFC ``NON_CD_OBJECTIVE_PROFILE_RFC_2026-11-16``):
frequency-dependent H/V coverage profiles, detrended DI roughness, and an optional HF floor.

v9 is the non-CD profile objective. It reuses v7's private helpers (``_load_v7``,
``_flat_cv_term``), v4's ``_diag_term`` and v2's ``_v2_flat_value`` unchanged; only the
coverage term, the per-frequency ripple window and ``di_roughness`` are new. The stored
``terms`` are the normalised weighted values (``raw / tolerance``), so ``total`` is
``sum(w_k * terms[k])`` for the weighted keys.

The term set is::

    V9_WEIGHTED_KEYS = cov_profile rip flat load dislope di_roughness flat_cv
    optional weighted: hf_floor   (present in the weighted set ONLY when declared)
    unweighted reported raw: diag distd   (owner-locked: weight 0, never normalised)

Owner-locked invariants (amendment 2026-11-17):

* ``diag`` and ``distd`` are ALWAYS computed and reported raw, but never weighted. They are
  not part of ``total``; a brief cannot turn them back on through ``weights``.
* ``objective.bw8k_floor`` is REFUSED with v9. The coverage profile's ``min_deg`` is the
  narrow-side HF constraint; a second ``0.75 * flat`` floor would double-charge narrowing.
  An extra HF penalty exists only through the explicit, independently weighted ``hf_floor``
  mapping (own ``hz``/``h_deg``/``v_deg``/``weight``/``tolerance``).
* Historical J is immutable: v9 never redefines v7's ``distd``; ``di_roughness`` is a new
  orthogonal key.

Below-onset corridor semantics (amendment section D): the effective per-plane onset is
``max(first_anchor_hz, f0_plane)`` (``f0_hz`` for H, ``f0_v_hz`` for V, falling back to
``f0_hz``). With ``cov_below_f0: mask`` those frequencies are excluded entirely. With
``cov_below_f0: one_sided`` a wide pattern below the onset is physics and free, while a
narrow pattern (below the profile's lower bound: corridor ``min_deg`` or target
``preferred_deg``) is charged with ``cov_narrow_ratio`` - exactly v7's one-sided rule,
re-expressed against the profile bound.

``objective_v9`` never raises and never returns nan or inf. Pure numpy, no solver.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

from ..metrics.smoothness import ripple_detrended_db
from ..targets.profile import profile_onset_hz, profile_value
from ..targets.spec import Target
from .scalar import penalty_result
from .scalar_v2 import (_cut_arrays, _objective_v3, _plain_mean, _v2_flat_value,
                        _weighted_mean, freq_weight_vector)
from .scalar_v4 import _diag_term
from .scalar_v7 import V7_DIAGNOSTIC_KEYS, _flat_cv_term, _load_v7
from .terms import NAN_TERM_FILL, PENALTY_FAILED, WEIGHTED_KEYS

log = logging.getLogger("hornlab_search.objective.scalar_v9")

__all__ = ["objective_v9", "V9Params", "V9_WEIGHTED_KEYS", "V9_ALL_KEYS",
           "V9_DEFAULT_WEIGHTS", "V9_UNWEIGHTED_KEYS", "resolve_v9_weights",
           "worst_valid_v9_j"]

#: The base v9 weighted terms. ``flat_cv`` is appended below: v9 scores it as a weighted
#: term (default weight 1.0, RFC 4.8), unlike v7 where it defaults to weight 0.0.
V9_BASE_WEIGHTED_KEYS = ("cov_profile", "rip", "flat", "load", "dislope", "di_roughness")
V9_WEIGHTED_KEYS = V9_BASE_WEIGHTED_KEYS + ("flat_cv",)
#: ``hf_floor`` joins the weighted set only when the objective block declares it.
V9_OPTIONAL_WEIGHTED_KEYS = ("hf_floor",)
#: Reported RAW and never normalised; owner-locked at weight 0.
V9_UNWEIGHTED_KEYS = ("diag", "distd")
V9_BOOKKEEPING_KEYS = ("penalty", "total", "n_nan", "n_in_band", "di_estimated")
#: v7's loading diagnostics ride along unchanged (never weighted).
V9_DIAGNOSTIC_KEYS = V7_DIAGNOSTIC_KEYS
V9_ALL_KEYS = (V9_WEIGHTED_KEYS + V9_OPTIONAL_WEIGHTED_KEYS + V9_UNWEIGHTED_KEYS
               + V9_BOOKKEEPING_KEYS + V9_DIAGNOSTIC_KEYS)
#: RFC 4.8 defaults; diag/distd are owner-locked to zero, flat_cv is a v9 weighted term.
V9_DEFAULT_WEIGHTS = {
    "cov_profile": 1.0, "rip": 1.0, "flat": 0.5, "load": 1.0, "dislope": 0.5,
    "di_roughness": 1.0, "flat_cv": 1.0, "diag": 0.0, "distd": 0.0,
}

_COV_BELOW_F0 = ("mask", "one_sided")
_PROFILE_MODES = ("corridor", "target")
_FLAT_BANDS = ("band", "scored")
_HF_FLOOR_KEYS = {"hz", "h_deg", "v_deg", "weight", "tolerance"}
_BLOCK_KEYS = {"version", "tolerances", "cov_narrow_ratio", "cov_below_f0", "cov_v_weight",
               "flat_band", "loaded_re_z", "lfp_re_z", "lfp_crossover_ratio", "hf_floor"}
_BW8K_REFUSAL = ("objective.bw8k_floor is invalid with v9; the coverage profile min_deg is "
                 "the narrow-side HF constraint")
#: The C2 constant-velocity band's upper edge is v7's (reused through ``_flat_cv_term``).
BW8K_HZ = 8000.0


@dataclass(frozen=True)
class V9Params:
    """The ``objective:`` block of a v9 brief, validated. Tolerances have NO defaults."""

    tolerances: dict
    cov_narrow_ratio: float = 1.0
    cov_below_f0: str = "mask"
    cov_v_weight: float = 1.0
    flat_band: str = "band"
    loaded_re_z: float = 0.50
    lfp_re_z: float = 0.20
    lfp_crossover_ratio: float = 1.6
    hf_floor: dict | None = None

    def weighted_keys(self) -> tuple[str, ...]:
        """The weighted key set for THIS block (``hf_floor`` only when declared)."""
        keys: list[str] = list(V9_WEIGHTED_KEYS)
        if self.hf_floor is not None:
            keys.append("hf_floor")
        return tuple(keys)

    @classmethod
    def from_block(cls, block: dict) -> "V9Params":
        """Validate a raw ``objective:`` mapping. Raises ``ValueError`` (config wraps it)."""
        if not isinstance(block, dict):
            raise ValueError("objective must be a mapping")
        # Amendment section C: refuse the legacy floor BEFORE the generic unknown-key error so
        # the message names both keys and explains why.
        if "bw8k_floor" in block:
            raise ValueError(_BW8K_REFUSAL)
        unknown = set(block) - _BLOCK_KEYS
        if unknown:
            raise ValueError(f"objective unknown key(s) {sorted(unknown)} "
                             f"(allowed for v9: {sorted(_BLOCK_KEYS)})")
        tol = block.get("tolerances")
        if not isinstance(tol, dict):
            raise ValueError("objective v9 needs a 'tolerances' mapping with one entry per term: "
                             f"{list(V9_WEIGHTED_KEYS)}")
        missing = [k for k in V9_WEIGHTED_KEYS if k not in tol]
        extra = sorted(set(tol) - set(V9_WEIGHTED_KEYS))
        if missing or extra:
            raise ValueError(f"objective.tolerances: missing {missing}, unknown {extra} "
                             f"(required: {list(V9_WEIGHTED_KEYS)})")
        clean: dict = {}
        for k in V9_WEIGHTED_KEYS:
            v = tol[k]
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or not math.isfinite(float(v)) or not float(v) > 0.0:
                raise ValueError(f"objective.tolerances.{k} must be a finite number > 0, got {v!r}")
            clean[k] = float(v)
        ratio = block.get("cov_narrow_ratio", 1.0)
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) \
                or not math.isfinite(float(ratio)) or not float(ratio) > 0.0:
            raise ValueError(f"objective.cov_narrow_ratio must be a finite number > 0, got {ratio!r}")
        below = block.get("cov_below_f0", "mask")
        if below not in _COV_BELOW_F0:
            raise ValueError(f"objective.cov_below_f0 must be one of {list(_COV_BELOW_F0)}, got {below!r}")
        flat_band = block.get("flat_band", "band")
        if flat_band not in _FLAT_BANDS:
            raise ValueError(f"objective.flat_band must be one of {list(_FLAT_BANDS)}, got {flat_band!r}")
        cov_v_weight = block.get("cov_v_weight", 1.0)
        if isinstance(cov_v_weight, bool) or not isinstance(cov_v_weight, (int, float)) \
                or not math.isfinite(float(cov_v_weight)) or not 0.0 <= float(cov_v_weight) <= 1.0:
            raise ValueError(f"objective.cov_v_weight must be a number in [0, 1], got {cov_v_weight!r}")
        constants = {}
        for key, default in (("loaded_re_z", 0.50), ("lfp_re_z", 0.20),
                             ("lfp_crossover_ratio", 1.6)):
            v = block.get(key, default)
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or not math.isfinite(float(v)) or not float(v) > 0.0:
                raise ValueError(f"objective.{key} must be a finite number > 0, got {v!r}")
            constants[key] = float(v)
        hf_floor = None
        if block.get("hf_floor") is not None:
            hf_floor = _validate_hf_floor(block["hf_floor"])
        return cls(tolerances=clean, cov_narrow_ratio=float(ratio), cov_below_f0=str(below),
                   cov_v_weight=float(cov_v_weight), flat_band=str(flat_band),
                   hf_floor=hf_floor, **constants)

    def to_block(self) -> dict:
        """The normalised mapping stored in the config; never emits ``bw8k_floor``."""
        out = {
            "version": 9,
            "tolerances": dict(self.tolerances),
            "cov_narrow_ratio": self.cov_narrow_ratio,
            "cov_below_f0": self.cov_below_f0,
            "cov_v_weight": self.cov_v_weight,
            "flat_band": self.flat_band,
            "loaded_re_z": self.loaded_re_z,
            "lfp_re_z": self.lfp_re_z,
            "lfp_crossover_ratio": self.lfp_crossover_ratio,
        }
        if self.hf_floor is not None:
            out["hf_floor"] = dict(self.hf_floor)
        return out


def _validate_hf_floor(raw) -> dict:
    """Validate the optional explicit HF floor mapping (its own weight and tolerance)."""
    if not isinstance(raw, dict):
        raise ValueError(f"objective.hf_floor must be a mapping with keys "
                         f"{sorted(_HF_FLOOR_KEYS)}, got {type(raw).__name__}")
    unknown = set(raw) - _HF_FLOOR_KEYS
    missing = sorted(_HF_FLOOR_KEYS - set(raw))
    if unknown or missing:
        raise ValueError(f"objective.hf_floor: missing {missing}, unknown {sorted(unknown)} "
                         f"(required: {sorted(_HF_FLOOR_KEYS)})")
    out = {}
    for key in ("hz", "h_deg", "v_deg", "tolerance"):
        v = raw[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) \
                or not math.isfinite(float(v)) or not float(v) > 0.0:
            raise ValueError(f"objective.hf_floor.{key} must be a finite number > 0, got {v!r}")
        out[key] = float(v)
    for key in ("h_deg", "v_deg"):
        if out[key] > 180.0:
            raise ValueError(f"objective.hf_floor.{key} must be <= 180, got {out[key]!r}")
    w = raw["weight"]
    if isinstance(w, bool) or not isinstance(w, (int, float)) \
            or not math.isfinite(float(w)) or not float(w) >= 0.0:
        raise ValueError(f"objective.hf_floor.weight must be a finite number >= 0, got {w!r}")
    out["weight"] = float(w)
    return out


def resolve_v9_weights(weights: dict | None, params: V9Params | None = None) -> dict:
    """v9 defaults overlaid with ``weights``; unknown keys warn (never raise).

    ``diag``/``distd`` are owner-locked: a supplied weight is warned about and forced to 0.0.
    ``hf_floor`` joins the resolved set only when ``params`` declares it.
    """
    out = dict(V9_DEFAULT_WEIGHTS)
    hf = params.hf_floor if params is not None else None
    if hf is not None:
        out["hf_floor"] = float(hf["weight"])
    for k, v in (weights or {}).items():
        if k in ("diag", "distd"):
            try:
                requested = float(v)
            except (TypeError, ValueError):
                requested = 0.0
            if requested != 0.0:
                log.warning("objective v9 reports %r unweighted; the weight %r is ignored", k, v)
            continue
        if k in out:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                log.warning("weight %r=%r is not a number; using the default %r", k, v, out[k])
        else:
            log.warning("unknown objective weight %r ignored (known: %s)",
                        k, sorted(V9_DEFAULT_WEIGHTS))
    out["diag"] = 0.0
    out["distd"] = 0.0
    return out


def worst_valid_v9_j(params: V9Params, weights: dict | None) -> float:
    """J of a VALID design whose every weighted term is unmeasurable (``NAN_TERM_FILL``).

    The penalty-ordering invariant: this must stay far below ``PENALTY_INVALID`` so a refused
    design always ranks below a working one. Config checks it at load, per brief."""
    w = resolve_v9_weights(weights, params)
    total = sum(w[k] * NAN_TERM_FILL / params.tolerances[k] for k in V9_WEIGHTED_KEYS)
    hf = params.hf_floor
    if hf is not None:
        total += w["hf_floor"] * NAN_TERM_FILL / hf["tolerance"]
    return float(total)


def _v9_penalty(value: float = PENALTY_FAILED, *, n_in_band: int = 0) -> tuple[float, dict]:
    """The failure row: every v9 key present and finite, weighted terms 0.0, diagnostics fill."""
    t = {k: 0.0 for k in (V9_WEIGHTED_KEYS + V9_OPTIONAL_WEIGHTED_KEYS + V9_UNWEIGHTED_KEYS)}
    t.update({k: 0.0 for k in V9_BOOKKEEPING_KEYS})
    t["penalty"] = float(value)
    t["total"] = float(value)
    t["n_in_band"] = int(n_in_band)
    for k in V9_DIAGNOSTIC_KEYS:
        t[k] = NAN_TERM_FILL
    return float(value), t


def objective_v9(metrics, resp, ok, target: Target, weights: dict | None, params: V9Params):
    """Score one evaluation under objective v9. ``(J, terms)``; ``terms`` has ``V9_ALL_KEYS``."""
    try:
        return _objective_v9(metrics, resp, ok, target, weights, params)
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("objective_v9() failed; returning the failure penalty")
        return _v9_penalty(PENALTY_FAILED)


# ------------------------------------------------------------------ profile access

def _profile_mode(target: Target) -> str:
    """``corridor`` / ``target``; defensive ``target`` when the attribute is absent."""
    mode = getattr(target, "coverage_profile_mode", None)
    return mode if mode in _PROFILE_MODES else "target"


def _plane_anchors(target: Target, plane: str):
    """The plane's anchor tuple, with a scalar-coverage fallback for hand-built targets."""
    raw = getattr(target, f"coverage_profile_{plane}", None)
    if raw:
        return tuple(raw)
    cov = float(target.coverage_h_deg if plane == "h" else target.coverage_v_deg)
    if plane == "h" or target.f0_v_hz is None:
        f0 = float(target.f0_effective_hz())
    else:
        f0 = float(target.f0_v_hz)
    return ((f0, cov, None, None),)


def _plane_f0(target: Target, plane: str) -> float:
    if plane == "v" and target.f0_v_hz is not None:
        return float(target.f0_v_hz)
    return float(target.f0_effective_hz())


def _plane_onset(target: Target, plane: str) -> float:
    """Effective onset ``max(first_anchor_hz, f0_plane)`` (amendment section D)."""
    anchors = _plane_anchors(target, plane)
    try:
        return float(profile_onset_hz(anchors, _plane_f0(target, plane)))
    except Exception:  # noqa: BLE001 - a malformed profile degrades to its first anchor
        log.debug("profile_onset_hz failed for plane %s", plane, exc_info=True)
        try:
            return float(anchors[0][0])
        except Exception:  # noqa: BLE001
            return _plane_f0(target, plane)


def _profile_at(anchors, freq_hz: float):
    """(preferred, min, max) at one solved frequency via the shared log-linear interpolation."""
    pref, lo, hi = profile_value(anchors, float(freq_hz))
    return float(pref), (None if lo is None else float(lo)), (None if hi is None else float(hi))


# ------------------------------------------------------------------ cov_profile

def _plane_cov_cost(metrics, target: Target, f: np.ndarray, band: np.ndarray,
                    params: V9Params, plane: str) -> float:
    """Frequency-weighted mean corridor/target cost for one plane."""
    bw = np.asarray(metrics.bw_h_deg if plane == "h" else metrics.bw_v_deg, dtype=float)
    anchors = _plane_anchors(target, plane)
    mode = _profile_mode(target)
    onset = _plane_onset(target, plane)
    wv = freq_weight_vector(f, target)
    if params.cov_below_f0 == "one_sided":
        included = band
    else:
        included = band & (f >= onset)
    contrib = np.full(f.size, np.nan)
    for j in np.flatnonzero(included):
        try:
            pref, lo, hi = _profile_at(anchors, float(f[j]))
        except Exception:  # noqa: BLE001 - this frequency is unmeasurable
            log.debug("profile_value failed for plane %s at f=%g", plane, f[j], exc_info=True)
            continue
        val = float(bw[j])
        if not math.isfinite(val):
            continue
        if f[j] < onset:
            # one_sided only (mask excluded them): wide below the onset is physics and free.
            lower = lo if (mode == "corridor" and lo is not None) else pref
            d = val - lower
            contrib[j] = (params.cov_narrow_ratio * d * d / 100.0) if d < 0.0 else 0.0
        elif mode == "corridor" and lo is not None and hi is not None:
            if val < lo:
                contrib[j] = params.cov_narrow_ratio * (lo - val) ** 2 / 100.0
            elif val > hi:
                contrib[j] = (val - hi) ** 2 / 100.0
            else:
                contrib[j] = 0.0
        else:
            d = val - pref
            side = params.cov_narrow_ratio if d < 0.0 else 1.0
            contrib[j] = side * d * d / 100.0
    if target.freq_weights is not None:
        m, _ = _weighted_mean(contrib[included], wv[included])
    else:
        m, _ = _plain_mean(contrib[included])
    return float(m)


def _cov_profile_term(metrics, target: Target, f: np.ndarray, band: np.ndarray,
                      params: V9Params) -> float:
    """``mean_H(cost) + cov_v_weight * mean_V(cost)`` normalised by one cov_profile tolerance."""
    h = _plane_cov_cost(metrics, target, f, band, params, "h")
    v = _plane_cov_cost(metrics, target, f, band, params, "v")
    return float(h + params.cov_v_weight * v)


def _cov_n_in_band(target: Target, f: np.ndarray, band: np.ndarray, params: V9Params) -> int:
    """The H-plane scored-frequency count (v3/v7 bookkeeping parity)."""
    if params.cov_below_f0 == "one_sided":
        return int(band.sum())
    return int((band & (f >= _plane_onset(target, "h"))).sum())


# ------------------------------------------------------------------ per-frequency ripple

def _v9_ripple_values(metrics, resp, target: Target, band: np.ndarray):
    """Per-frequency ``ripple_h + ripple_v`` using the profile envelope width at that frequency.

    Corridor mode uses ``max - min``; target mode uses ``2 * preferred`` (the width whose
    -6 dB edges sit at ``preferred``). Mirrors v2's graceful fallback to the stored ripple
    pair when the Response is absent or malformed - it does NOT call ``_v2_ripple_values``
    because that helper hard-codes the scalar coverage targets.
    """
    f = np.asarray(metrics.freqs_hz, dtype=float)
    n = f.size
    arrays = _cut_arrays(resp, n)
    anchors_h = _plane_anchors(target, "h")
    anchors_v = _plane_anchors(target, "v")
    mode = _profile_mode(target)
    if arrays is not None:
        ha, va, sh, sv = arrays
        out = np.full(n, np.nan)
        try:
            for j in np.flatnonzero(band):
                pref_h, lo_h, hi_h = _profile_at(anchors_h, float(f[j]))
                pref_v, lo_v, hi_v = _profile_at(anchors_v, float(f[j]))
                width_h = (hi_h - lo_h) if (mode == "corridor" and lo_h is not None
                                            and hi_h is not None) else 2.0 * pref_h
                width_v = (hi_v - lo_v) if (mode == "corridor" and lo_v is not None
                                            and hi_v is not None) else 2.0 * pref_v
                out[j] = (ripple_detrended_db(ha, sh[j], width_h)
                          + ripple_detrended_db(va, sv[j], width_v))
            return out, True
        except Exception:  # noqa: BLE001 - malformed angles fall back to the stored values
            log.debug("objective_v9: per-frequency ripple failed; using stored v1 ripple",
                      exc_info=True)
    try:
        rh = np.asarray(metrics.ripple_h_db, dtype=float)
        rv = np.asarray(metrics.ripple_v_db, dtype=float)
        if rh.shape == rv.shape and rh.shape == f.shape:
            return rh + rv, False
    except Exception:  # noqa: BLE001
        pass
    return np.full(n, np.nan), False


def _rip_term_v9(metrics, resp, target: Target, f: np.ndarray, band: np.ndarray) -> float:
    """Frequency-weighted mean of the per-frequency profile-window ripple (WP4 as v7)."""
    values, _used = _v9_ripple_values(metrics, resp, target, band)
    if target.freq_weights is not None:
        m, _ = _weighted_mean(values[band], freq_weight_vector(f, target)[band])
    else:
        m, _ = _plain_mean(values[band])
    return float(m)


# ------------------------------------------------------------------ di_roughness

def _di_roughness(metrics, f: np.ndarray, score: np.ndarray) -> float:
    """Population std of ``DI - (a + b*log10 f)`` over the finite score-band DI samples.

    Fewer than two usable pairs: 0.0, mirroring ``dislope_term``'s convention that an
    unmeasurable slope cannot score a departure from it. ``dislope`` remains the orthogonal
    slope term, so a perfectly straight rising DI scores 0 here.
    """
    ff = np.asarray(f, dtype=float)[score]
    di = np.asarray(metrics.di_db, dtype=float)[score]
    good = np.isfinite(ff) & np.isfinite(di) & (ff > 0.0)
    ff, di = ff[good], di[good]
    if ff.size < 2:
        return 0.0
    x = np.log10(ff)
    if float(np.ptp(x)) <= 0.0:
        return 0.0
    try:
        coef = np.polyfit(x, di, 1)
        resid = di - np.polyval(coef, x)
        out = float(np.std(resid))
    except Exception:  # noqa: BLE001 - unmeasurable, never a crash
        log.debug("di_roughness failed", exc_info=True)
        return NAN_TERM_FILL
    return out if math.isfinite(out) else NAN_TERM_FILL


# ------------------------------------------------------------------ optional hf_floor

def _hf_floor_term(metrics, target: Target, f: np.ndarray, params: V9Params) -> float:
    """One-sided narrow-only HF floor at the last solved ``f <= min(hz, band_hi)``.

    Absent ``hf_floor`` -> 0.0. Present but unjudgeable (no solved sample at/below the cap, or
    non-finite beamwidths) -> ``NAN_TERM_FILL``, like v7's C3 floor convention.
    """
    hff = params.hf_floor
    if hff is None:
        return 0.0
    if f.size == 0:
        return NAN_TERM_FILL
    cap = min(float(hff["hz"]), float(target.band_hi_hz))
    below = np.nonzero(f <= cap)[0]
    if below.size == 0:
        return NAN_TERM_FILL
    i = int(below[-1])
    try:
        bw_h = float(np.asarray(metrics.bw_h_deg, dtype=float)[i])
        bw_v = float(np.asarray(metrics.bw_v_deg, dtype=float)[i])
    except Exception:  # noqa: BLE001
        return NAN_TERM_FILL
    if not (math.isfinite(bw_h) and math.isfinite(bw_v)):
        return NAN_TERM_FILL
    dh = max(0.0, float(hff["h_deg"]) - bw_h)
    dv = max(0.0, float(hff["v_deg"]) - bw_v)
    return float((dh ** 2 + dv ** 2) / 100.0)


# ------------------------------------------------------------------ the objective

def _objective_v9(metrics, resp, ok, target: Target, weights, params: V9Params):
    if metrics is None or not ok:
        return _v9_penalty(PENALTY_FAILED)
    w = resolve_v9_weights(weights, params)
    # v3 supplies rip/dislope/flat/load and every NaN/mask rule; v9 then overrides the terms
    # it redefines. v3 is handed the six v1-v3 weights only (cov/di are not v9 terms).
    _, raw = _objective_v3(metrics, resp, ok, target,
                           {k: w.get(k, 0.0) for k in WEIGHTED_KEYS})
    if raw["penalty"] > 0.0:
        return _v9_penalty(float(raw["penalty"]), n_in_band=int(raw["n_in_band"]))

    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    score = band & (f >= target.f0_effective_hz())

    t_raw = {k: float(raw[k]) for k in WEIGHTED_KEYS}
    if params.flat_band == "scored":        # opt-in: on-axis flatness from the crossover up
        t_raw["flat"] = _v2_flat_value(metrics, resp, target, score)
    t_raw["cov_profile"] = _cov_profile_term(metrics, target, f, band, params)
    t_raw["rip"] = _rip_term_v9(metrics, resp, target, f, band)
    t_raw["dislope"] = float(raw["dislope"])          # v3 already fits the score band
    t_raw["load"], load_diag = _load_v7(metrics, target, params)
    t_raw["flat_cv"] = _flat_cv_term(metrics, target, f, w["flat_cv"])

    di_s = np.asarray(metrics.di_db, dtype=float)[score]
    good = di_s[np.isfinite(di_s)]
    t_raw["distd"] = float(np.std(good)) if good.size >= 2 else 0.0   # owner-locked raw
    t_raw["di_roughness"] = _di_roughness(metrics, f, score)
    t_raw["hf_floor"] = _hf_floor_term(metrics, target, f, params)
    t_raw["diag"] = _diag_term(metrics, resp, target, f, score, params)  # raw, unweighted

    active: list[str] = list(V9_WEIGHTED_KEYS)
    hf = params.hf_floor
    hf_tol = float(hf["tolerance"]) if hf is not None else 1.0
    if hf is not None:
        active.append("hf_floor")
    t = {}
    for k in active:
        tol = (hf_tol if k == "hf_floor" else params.tolerances[k])
        t[k] = t_raw[k] / tol
    if not all(math.isfinite(v) for v in t.values()):
        return _v9_penalty(PENALTY_FAILED, n_in_band=int(raw["n_in_band"]))
    total = sum(w[k] * t[k] for k in active)
    if not math.isfinite(total):
        return _v9_penalty(PENALTY_FAILED, n_in_band=int(raw["n_in_band"]))
    if hf is None:
        t["hf_floor"] = 0.0                          # static key, no contribution
    t["diag"] = float(t_raw["diag"])                 # raw, never normalised
    t["distd"] = float(t_raw["distd"])               # raw, never normalised
    t["penalty"] = 0.0
    t["total"] = float(total)
    t["n_nan"] = raw["n_nan"]
    t["n_in_band"] = _cov_n_in_band(target, f, band, params)
    t["di_estimated"] = raw["di_estimated"]
    for k in V9_DIAGNOSTIC_KEYS:
        t[k] = float(load_diag[k])
    assert set(t) == set(V9_ALL_KEYS)
    return float(total), t
