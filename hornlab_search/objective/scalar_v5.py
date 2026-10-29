"""Objective v5 (2026-10-29): loading frequency, constant-velocity flatness, 8 kHz floor, asymmetric V.

v5 is v4's tolerance-normalised objective plus four owner-reviewed scoring changes. The evidence
and the no-invented-keys mapping live in the commit that adds this file; the term schema is:

    V5_WEIGHTED_KEYS = cov rip di dislope flat load distd diag flat_cv

``load`` is REUSED. Under v5 it is redefined as the COMBINED loading penalty (C1) instead of
v4/v3's "mean Re z shortfall" - the key name, the weight and the tolerance are the brief's existing
ones, so no key is invented. The stored ``terms`` are the normalised values (``raw / tol``), as in
v4, so ``sum(w_k * terms[k])`` is ``total``; the raw value is ``terms[k] * tol``.

What v5 adds over v4 (each is driven by the objective block or the target, never by a new term name):

* C1 ``load`` - the LOWEST FREQUENCY OF LOADING. ``LFP20`` is the first ascending log2-f crossing
  of Re z through ``lfp_re_z`` (default 0.20), interpolated between the bracketing solved samples;
  ``LFP50`` is the crossing through 0.50. ``lfp_pen = max(0, log2(LFP20 * lfp_crossover_ratio /
  F_X))`` with ``F_X = target.f0_effective_hz()``: the design is penalised when it only loads well
  above the band it is meant to control. ``rez_pen = max(0, loaded_re_z - min Re z at f >= F_X)``
  (default ``loaded_re_z`` 0.50) is the old shortfall, now measured only where the pattern matters.
  ``LFP20`` at the lowest solved sample is an UPPER BOUND (the crossing is at or below the grid
  start), as the owner asked. A crossing above the highest solved frequency, no z, or no solved
  sample at/above F_X is UNMEASURABLE -> ``NAN_TERM_FILL`` (never NaN/inf). ``lfp20_hz``,
  ``lfp50_hz`` and ``rez_min_from_fx`` ride along as diagnostic keys (in ``V5_ALL_KEYS``, never
  weighted).
* C2 ``flat_cv`` - constant-VELOCITY on-axis flatness over ``F_X <= f <= 3000 Hz``. Unit
  acceleration level ``on_axis_db`` becomes the unit-velocity level ``on_axis_db + 20*log10(f)``;
  a line is fitted against ``log2(f)`` and the population standard deviation of the residual is the
  raw term. This is the band where a PA horn's tone lives; the existing ``flat`` term keeps scoring
  unit-acceleration flatness over the whole band, so C2 adds to it and does not replace it. Fewer
  than two usable samples -> ``NAN_TERM_FILL``. A zero weight stores 0.0 (like v4's distd/diag).
* C3 8 kHz one-sided floor - at the highest solved frequency at or below ``min(8000, band_hi)``, a
  horizontal beamwidth narrower than ``bw8k_floor`` (default 0.75) times ``coverage_h_deg`` adds
  ``deficit^2 / 100`` to the RAW ``cov``; the same for V. One-sided: a wider pattern is not
  rewarded. No frequency at or below that cap -> ``NAN_TERM_FILL`` for ``cov``.
* C5 asymmetric V - when the target carries BOTH ``coverage_v_up_deg`` and ``coverage_v_down_deg``
  (validated to sum to ``coverage_v_deg``), the vertical half of ``cov`` scores the -6 dB V edges
  against the two signed targets: ``(upper - up)^2 + (lower - down)^2`` / 100, with the same
  narrow-side ratio (upper error < 0 is narrow; lower error > 0 is narrow). Absent either key,
  v5's V coverage is v4's single total-width term. ``coverage_v_deg`` stays for every other metric
  and gate.

Everything else - rip, di, dislope, flat, distd, diag, the frequency weighting, the below-f0 rule -
is v4's, inherited through ``_objective_v3``/``scalar_v4``. ``objective_v5`` never raises and never
returns nan or inf. Pure numpy, no solver.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

from ..metrics.polar import beamwidth_edges_deg
from ..targets.spec import Target
from .scalar import penalty_result
from .scalar_v2 import (_cut_arrays, _objective_v3, _plain_mean, _weighted_mean,
                        freq_weight_vector)
from .scalar_v4 import (V4_ALL_KEYS, V4_DEFAULT_WEIGHTS, V4_WEIGHTED_KEYS, _cov_term, _diag_term,
                        _side_weight)
from .terms import NAN_TERM_FILL, PENALTY_FAILED, WEIGHTED_KEYS

log = logging.getLogger("hornlab_search.objective.scalar_v5")

__all__ = ["objective_v5", "V5Params", "V5_WEIGHTED_KEYS", "V5_ALL_KEYS", "V5_DEFAULT_WEIGHTS",
           "resolve_v5_weights", "worst_valid_j"]

#: v4's weighted terms plus the constant-velocity flatness. ``load`` keeps its name (C1).
V5_EXTRA_WEIGHTED_KEYS = ("flat_cv",)
V5_WEIGHTED_KEYS = V4_WEIGHTED_KEYS + V5_EXTRA_WEIGHTED_KEYS
#: C1 diagnostics: extra, NEVER weighted, but part of the stored key set.
V5_DIAGNOSTIC_KEYS = ("lfp20_hz", "lfp50_hz", "rez_min_from_fx")
V5_ALL_KEYS = V4_ALL_KEYS + V5_EXTRA_WEIGHTED_KEYS + V5_DIAGNOSTIC_KEYS
#: v4's defaults plus a silent (zero-weight) flat_cv; load stays 0.0 unless the brief asks.
V5_DEFAULT_WEIGHTS = {**V4_DEFAULT_WEIGHTS, "flat_cv": 0.0}

_COV_BELOW_F0 = ("mask", "one_sided")
_DIAG_REFERENCES = ("round",)
_BLOCK_KEYS = {"version", "tolerances", "cov_narrow_ratio", "cov_below_f0", "diag_reference",
               "loaded_re_z", "lfp_re_z", "lfp_crossover_ratio", "bw8k_floor"}
#: The C2 constant-velocity band's upper edge (Hz), owner-directed.
FLAT_CV_BAND_HI_HZ = 3000.0
#: The C3 floor is measured at or below this frequency (Hz).
BW8K_HZ = 8000.0


@dataclass(frozen=True)
class V5Params:
    """The ``objective:`` block of a v5 brief, validated. Tolerances have NO defaults."""

    tolerances: dict
    cov_narrow_ratio: float = 2.0
    cov_below_f0: str = "mask"
    diag_reference: str = "round"
    loaded_re_z: float = 0.50
    lfp_re_z: float = 0.20
    lfp_crossover_ratio: float = 1.6
    bw8k_floor: float = 0.75

    @classmethod
    def from_block(cls, block: dict) -> "V5Params":
        """Validate a raw ``objective:`` mapping. Raises ``ValueError`` (config wraps it).

        A v5 block missing any tolerance, or carrying a non-positive / non-finite tolerance or
        scoring constant, is an error: a silent default would let two briefs mean different things
        by the same weight."""
        if not isinstance(block, dict):
            raise ValueError("objective must be a mapping")
        unknown = set(block) - _BLOCK_KEYS
        if unknown:
            raise ValueError(f"objective unknown key(s) {sorted(unknown)} "
                             f"(allowed for v5: {sorted(_BLOCK_KEYS)})")
        tol = block.get("tolerances")
        if not isinstance(tol, dict):
            raise ValueError("objective v5 needs a 'tolerances' mapping with one entry per term: "
                             f"{list(V5_WEIGHTED_KEYS)}")
        missing = [k for k in V5_WEIGHTED_KEYS if k not in tol]
        extra = sorted(set(tol) - set(V5_WEIGHTED_KEYS))
        if missing or extra:
            raise ValueError(f"objective.tolerances: missing {missing}, unknown {extra} "
                             f"(required: {list(V5_WEIGHTED_KEYS)})")
        clean: dict = {}
        for k in V5_WEIGHTED_KEYS:
            v = tol[k]
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or not math.isfinite(float(v)) or not float(v) > 0.0:
                raise ValueError(f"objective.tolerances.{k} must be a finite number > 0, got {v!r}")
            clean[k] = float(v)
        ratio = block.get("cov_narrow_ratio", 2.0)
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) \
                or not math.isfinite(float(ratio)) or not float(ratio) > 0.0:
            raise ValueError(f"objective.cov_narrow_ratio must be a finite number > 0, got {ratio!r}")
        below = block.get("cov_below_f0", "mask")
        if below not in _COV_BELOW_F0:
            raise ValueError(f"objective.cov_below_f0 must be one of {list(_COV_BELOW_F0)}, got {below!r}")
        ref = block.get("diag_reference", "round")
        if ref not in _DIAG_REFERENCES:
            raise ValueError(f"objective.diag_reference must be one of {list(_DIAG_REFERENCES)}, got {ref!r}")
        constants = {}
        for key, default in (("loaded_re_z", 0.50), ("lfp_re_z", 0.20),
                             ("lfp_crossover_ratio", 1.6), ("bw8k_floor", 0.75)):
            v = block.get(key, default)
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or not math.isfinite(float(v)) or not float(v) > 0.0:
                raise ValueError(f"objective.{key} must be a finite number > 0, got {v!r}")
            constants[key] = float(v)
        return cls(tolerances=clean, cov_narrow_ratio=float(ratio), cov_below_f0=str(below),
                   diag_reference=str(ref), **constants)

    def to_block(self) -> dict:
        """The normalised mapping stored in the config (so ``config_sha`` covers every choice)."""
        return {"version": 5, "tolerances": dict(self.tolerances),
                "cov_narrow_ratio": self.cov_narrow_ratio, "cov_below_f0": self.cov_below_f0,
                "diag_reference": self.diag_reference, "loaded_re_z": self.loaded_re_z,
                "lfp_re_z": self.lfp_re_z, "lfp_crossover_ratio": self.lfp_crossover_ratio,
                "bw8k_floor": self.bw8k_floor}


def resolve_v5_weights(weights: dict | None) -> dict:
    """v5 defaults overlaid with ``weights``; unknown keys warn (never raise), as in v1-v4."""
    out = dict(V5_DEFAULT_WEIGHTS)
    for k, v in (weights or {}).items():
        if k in V5_DEFAULT_WEIGHTS:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                log.warning("weight %r=%r is not a number; using the default %r", k, v, out[k])
        else:
            log.warning("unknown objective weight %r ignored (known: %s)", k, sorted(V5_DEFAULT_WEIGHTS))
    return out


def worst_valid_j(params: V5Params, weights: dict | None) -> float:
    """J of a VALID design whose every weighted term is unmeasurable (each = ``NAN_TERM_FILL``).

    The penalty-ordering invariant (plan 3d.2): this must stay far below ``PENALTY_INVALID``, or a
    refused design could outrank a working one. Config checks it at load, per brief."""
    w = resolve_v5_weights(weights)
    return float(sum(w[k] * NAN_TERM_FILL / params.tolerances[k] for k in V5_WEIGHTED_KEYS))


def _v5_penalty(value: float = PENALTY_FAILED, *, n_in_band: int = 0) -> tuple[float, dict]:
    j, t = penalty_result(value, n_in_band=n_in_band)
    t["distd"] = 0.0
    t["diag"] = 0.0
    t["flat_cv"] = 0.0
    for k in V5_DIAGNOSTIC_KEYS:
        t[k] = NAN_TERM_FILL
    return j, t


def objective_v5(metrics, resp, ok, target: Target, weights: dict | None, params: V5Params):
    """Score one evaluation under objective v5. ``(J, terms)``; ``terms`` has ``V5_ALL_KEYS``."""
    try:
        return _objective_v5(metrics, resp, ok, target, weights, params)
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("objective_v5() failed; returning the failure penalty")
        return _v5_penalty(PENALTY_FAILED)


# ------------------------------------------------------------------ C1 combined loading


def _first_crossing_hz(f: np.ndarray, z: np.ndarray, thr: float) -> float | None:
    """First ascending log2-f crossing of Re z through ``thr``, linearly interpolated in z.

    ``None`` when no finite bracket reaches ``thr`` (the crossing is above the highest solved
    frequency, or there is no z at all). When the LOWEST usable sample is already at or above
    ``thr`` the true crossing is at or below the grid start: the grid start is returned, which
    the caller documents as an upper bound.
    """
    ff = np.asarray(f, dtype=float)
    zz = np.asarray(z, dtype=float)
    ok = np.isfinite(zz)
    if not ok.any():
        return None
    fa, za = ff[ok], zz[ok]
    if fa.size == 0:
        return None
    if za[0] >= thr:
        return float(fa[0])
    idx = np.nonzero((za[:-1] < thr) & (za[1:] >= thr))[0]
    if idx.size == 0:
        return None
    i = int(idx[0])
    z0, z1 = float(za[i]), float(za[i + 1])
    t = (thr - z0) / (z1 - z0)
    lg = math.log2(float(fa[i])) + t * (math.log2(float(fa[i + 1])) - math.log2(float(fa[i])))
    return float(2.0 ** lg)


def _load_v5(metrics, target: Target, params: V5Params) -> tuple[float, dict]:
    """(raw combined loading penalty, diagnostics). Unmeasurable -> ``NAN_TERM_FILL``."""
    diag = {k: NAN_TERM_FILL for k in V5_DIAGNOSTIC_KEYS}
    z = getattr(metrics, "z_throat_real", None)
    f = np.asarray(metrics.freqs_hz, dtype=float)
    if z is None:
        return NAN_TERM_FILL, diag
    z = np.asarray(z, dtype=float)
    fx = float(target.f0_effective_hz())
    # rez_pen needs a measured Re z AT/ABOVE F_X; without one the whole term is unmeasurable.
    above = np.isfinite(z) & (f >= fx)
    if not above.any():
        return NAN_TERM_FILL, diag
    rez_min = float(np.min(z[above]))
    diag["rez_min_from_fx"] = rez_min
    lfp20 = _first_crossing_hz(f, z, params.lfp_re_z)
    lfp50 = _first_crossing_hz(f, z, 0.50)
    if lfp20 is not None:
        diag["lfp20_hz"] = lfp20
    if lfp50 is not None:
        diag["lfp50_hz"] = lfp50
    if lfp20 is None:                            # crossing above the highest solved sample
        return NAN_TERM_FILL, diag
    lfp_pen = max(0.0, math.log2(lfp20 * params.lfp_crossover_ratio / fx))
    rez_pen = max(0.0, params.loaded_re_z - rez_min)
    raw = lfp_pen + rez_pen
    if not math.isfinite(raw):
        return NAN_TERM_FILL, diag
    return float(raw), diag


# ------------------------------------------------------------------ C2 constant-velocity flatness


def _flat_cv_term(metrics, target: Target, f: np.ndarray, weight: float) -> float:
    """Population std of the residual of unit-velocity level vs log2(f), F_X..3000 Hz."""
    if weight == 0.0:
        return 0.0
    try:
        sel = (f >= float(target.f0_effective_hz())) & (f <= FLAT_CV_BAND_HI_HZ)
        fs = f[sel]
        oa = np.asarray(metrics.on_axis_db, dtype=float)[sel]
        good = np.isfinite(oa) & np.isfinite(fs) & (fs > 0.0)
        fs, oa = fs[good], oa[good]
        if fs.size < 2:
            return NAN_TERM_FILL
        x = np.log2(fs)
        if float(np.ptp(x)) <= 0.0:
            return NAN_TERM_FILL
        y = oa + 20.0 * np.log10(fs)             # unit acceleration -> unit velocity
        coef = np.polyfit(x, y, 1)
        resid = y - np.polyval(coef, x)
        out = float(np.std(resid))
        return out if math.isfinite(out) else NAN_TERM_FILL
    except Exception:  # noqa: BLE001 - unmeasurable, never a crash
        log.debug("flat_cv failed", exc_info=True)
        return NAN_TERM_FILL


# ------------------------------------------------------------------ C3 / C5 coverage


def _bw8k_floor_penalty(metrics, target: Target, f: np.ndarray, params: V5Params) -> float | None:
    """One-sided 8 kHz floor penalty for raw ``cov``; ``None`` when the floor is unjudgeable.

    Measured at the highest solved frequency at or below ``min(8000, band_hi)`` (so a grid without
    exactly 8 kHz uses the highest solved sample below it). Only NARROW patterns are charged."""
    if f.size == 0:
        return None
    cap = min(BW8K_HZ, float(target.band_hi_hz))
    below = np.nonzero(f <= cap)[0]
    if below.size == 0:
        return None
    i = int(below[-1])
    try:
        bw_h = float(np.asarray(metrics.bw_h_deg, dtype=float)[i])
        bw_v = float(np.asarray(metrics.bw_v_deg, dtype=float)[i])
    except Exception:  # noqa: BLE001
        return None
    if not (math.isfinite(bw_h) and math.isfinite(bw_v)):
        return None
    floor_h = params.bw8k_floor * float(target.coverage_h_deg)
    floor_v = params.bw8k_floor * float(target.coverage_v_deg)
    dh = max(0.0, floor_h - bw_h)
    dv = max(0.0, floor_v - bw_v)
    return float((dh ** 2 + dv ** 2) / 100.0)


def _cov_h_plane(metrics, target: Target, f: np.ndarray, band: np.ndarray,
                 params: V5Params) -> float:
    """Horizontal coverage exactly as v4's per-plane loop (mask / narrow ratio / below-f0)."""
    wv = freq_weight_vector(f, target)
    f0_h = target.f0_effective_hz()
    err = np.asarray(metrics.bw_h_deg, dtype=float) - float(target.coverage_h_deg)
    above = f >= f0_h
    side = _side_weight(err, params.cov_narrow_ratio)
    if params.cov_below_f0 == "one_sided":
        included = band
        side = np.where(~above & (err > 0.0), 0.0, side)
    else:
        included = band & above
    contrib = (side * err ** 2)[included] / 100.0
    if target.freq_weights is not None:
        m, _ = _weighted_mean(contrib, wv[included])
    else:
        m, _ = _plain_mean(contrib)
    return float(m)


def _cov_v_asymmetric(resp, target: Target, f: np.ndarray, band: np.ndarray,
                      params: V5Params) -> float | None:
    """C5: signed V -6 dB edges vs the two target halves, frequency-weighted like cov.

    Scored at each solved f >= max(1.5 * F_X, f0_v) inside the band. ``None`` when the V cut is
    unusable at every one of those frequencies (the caller turns that into ``NAN_TERM_FILL``)."""
    keys = (getattr(target, "coverage_v_up_deg", None), getattr(target, "coverage_v_down_deg", None))
    if keys[0] is None or keys[1] is None:
        return None
    cuts = _cut_arrays(resp, f.size)
    if cuts is None:
        return None
    _ha, va, _sh, sv = cuts
    fx = float(target.f0_effective_hz())
    f0_v = float(target.f0_v_hz) if target.f0_v_hz is not None else fx
    lo = max(1.5 * fx, f0_v)
    idx = np.nonzero(band & (f >= lo))[0]
    if idx.size == 0:
        return None
    up_t, down_t = float(keys[0]), float(keys[1])
    contrib = np.full(idx.size, np.nan)
    for n, i in enumerate(idx):
        try:
            lower, upper = beamwidth_edges_deg(va, np.asarray(sv, dtype=float)[i])
        except Exception:  # noqa: BLE001 - a missing 0 sample / bad cut: this f is unusable
            continue
        if not (math.isfinite(lower) and math.isfinite(upper)):
            continue
        e_up = upper - up_t
        e_dn = lower - down_t
        s_up = params.cov_narrow_ratio if e_up < 0.0 else 1.0
        s_dn = params.cov_narrow_ratio if e_dn > 0.0 else 1.0   # lower edge closer to 0 = narrow
        contrib[n] = (s_up * e_up ** 2 + s_dn * e_dn ** 2) / 100.0
    if target.freq_weights is not None:
        m, _ = _weighted_mean(contrib, freq_weight_vector(f, target)[idx])
    else:
        m, _ = _plain_mean(contrib)
    if not math.isfinite(m):
        return None
    return float(m)


def _cov_term_v5(metrics, resp, target: Target, f: np.ndarray, band: np.ndarray,
                 params: V5Params) -> float:
    """v4 coverage plus the 8 kHz floor, with v4's behaviour when V is symmetric."""
    if getattr(target, "coverage_v_up_deg", None) is not None \
            and getattr(target, "coverage_v_down_deg", None) is not None:
        v = _cov_v_asymmetric(resp, target, f, band, params)
        if v is None:
            return NAN_TERM_FILL
        base = _cov_h_plane(metrics, target, f, band, params) + v
    else:
        base = _cov_term(metrics, target, f, band, params)
    floor = _bw8k_floor_penalty(metrics, target, f, params)
    if floor is None:
        return NAN_TERM_FILL
    if not math.isfinite(base):
        return NAN_TERM_FILL
    return float(base + floor)


# ------------------------------------------------------------------ the objective


def _objective_v5(metrics, resp, ok, target: Target, weights, params: V5Params):
    if metrics is None or not ok:
        return _v5_penalty(PENALTY_FAILED)
    w = resolve_v5_weights(weights)
    # v3 supplies rip/di/dislope/flat and every v3 NaN/mask rule; v5 recomputes cov and load.
    _, raw = _objective_v3(metrics, resp, ok, target, {k: w[k] for k in WEIGHTED_KEYS})
    if raw["penalty"] > 0.0:
        return _v5_penalty(float(raw["penalty"]), n_in_band=int(raw["n_in_band"]))

    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    score = band & (f >= target.f0_effective_hz())

    t_raw = {k: float(raw[k]) for k in WEIGHTED_KEYS}
    t_raw["cov"] = _cov_term_v5(metrics, resp, target, f, band, params)

    if w["distd"] != 0.0:
        di_s = np.asarray(metrics.di_db, dtype=float)[score]
        good = di_s[np.isfinite(di_s)]
        t_raw["distd"] = float(np.std(good)) if good.size >= 2 else 0.0
    else:
        t_raw["distd"] = 0.0
    t_raw["diag"] = (_diag_term(metrics, resp, target, f, score, params)
                     if w["diag"] != 0.0 else 0.0)

    t_raw["load"], diag = _load_v5(metrics, target, params)
    t_raw["flat_cv"] = _flat_cv_term(metrics, target, f, w["flat_cv"])

    t = {k: t_raw[k] / params.tolerances[k] for k in V5_WEIGHTED_KEYS}
    if not all(math.isfinite(v) for v in t.values()):
        return _v5_penalty(PENALTY_FAILED, n_in_band=int(raw["n_in_band"]))
    total = sum(w[k] * t[k] for k in V5_WEIGHTED_KEYS)
    if not math.isfinite(total):
        return _v5_penalty(PENALTY_FAILED, n_in_band=int(raw["n_in_band"]))
    t["penalty"] = 0.0
    t["total"] = float(total)
    t["n_nan"] = raw["n_nan"]
    t["n_in_band"] = raw["n_in_band"]
    t["di_estimated"] = raw["di_estimated"]
    for k in V5_DIAGNOSTIC_KEYS:
        t[k] = float(diag[k])
    assert set(t) == set(V5_ALL_KEYS)
    return float(total), t
