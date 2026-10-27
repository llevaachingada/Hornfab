"""Objective v4 (2026-10-27): tolerance-normalised terms plus the review's scoring additions.

Why (docs/research/V4_SCORING_REVIEW_2026-10-27.md, docs/evidence/OBJECTIVE_V4_TOLERANCES.md): v3's
six raw terms differ in scale by ~300x, so a weight did not mean influence (load 0.5 gave 2 % of J)
and four of eight smoke-night cells were 82-92 % one term. v4 divides every term by a brief-set
TOLERANCE, "the size of a miss that counts as one unit of bad", so a weight of 0.5 really is half the
influence of 1.0 relative to the chosen tolerance:

    J = sum_k  w_k * term_k / tol_k  + penalty            k in cov rip di dislope flat load distd diag

The stored ``terms`` hold the NORMALISED values (``term_k / tol_k``), so ``w_k * terms[k]`` sums to
``total`` and every display that multiplies by the weights stays right. The raw value is
``terms[k] * tol_k`` using the run's embedded brief. The raw scale of each term is v3's.

What v4 adds over v3 (each is opt-in through the brief's ``objective:`` block; with the defaults the
cov/rip/di/dislope/flat/load terms are v3's, only divided by their tolerances):

* ``cov_narrow_ratio`` (default 1.0): coverage error on the NARROW side (beamwidth below target, i.e.
  beamy) counts this many times a wide-side error. 2.0 is the proposed value for constant-directivity
  waveguide briefs; 1.0 for loading briefs where narrowing is the design.
* ``cov_below_f0`` = ``mask`` (default, v3: not scored below f0) or ``one_sided``: below f0 a wide
  pattern is physics (a horn cannot hold the pattern there) and is free, but a narrow pattern is a
  defect and is still scored. Intended for the low-reach PA class.
* ``distd`` (weight default 0): standard deviation of the directivity index over the scored band, in
  dB. The Princeton constant-directivity study found DI standard deviation and polar cross-correlation
  the metrics that quantify constancy on both definitions; ``dislope`` only sees a straight-line trend.
* ``diag`` (weight default 0): the 45 / 135 degree -6 dB beamwidths from the stored balloon against a
  ROUND reference (the mean of the H and V targets), squared and /100 like ``cov``, with the same
  narrow-side ratio. Reads the crease / pucker shape that H/V-only cov and rip cannot see. It does not
  penalise diagonal-vs-H/V inconsistency (that would punish the shapes the crease cells look for).

The presence band (2.5-5.5 kHz) emphasis is NOT a v4 term: it is the brief's existing
``target.freq_weights``, which already weights cov, rip, diag and the means here.

``objective_v4`` never raises and never returns nan or inf. Pure numpy, no solver.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

from ..metrics.diagonal import diagonal_beamwidths_deg
from ..targets.spec import Target
from .scalar import penalty_result
from .scalar_v2 import (_cut_arrays, _on_axis_index, _objective_v3, _plain_mean,
                        _weighted_mean, freq_weight_vector)
from .terms import ALL_KEYS, DEFAULT_WEIGHTS, NAN_TERM_FILL, PENALTY_FAILED, WEIGHTED_KEYS

log = logging.getLogger("hornlab_search.objective.scalar_v4")

__all__ = ["objective_v4", "V4Params", "V4_WEIGHTED_KEYS", "V4_ALL_KEYS", "V4_DEFAULT_WEIGHTS",
           "worst_valid_j"]

#: The two terms v4 adds to the six of v1-v3.
V4_EXTRA_KEYS = ("distd", "diag")
V4_WEIGHTED_KEYS = WEIGHTED_KEYS + V4_EXTRA_KEYS
V4_ALL_KEYS = ALL_KEYS + V4_EXTRA_KEYS
#: New terms are off unless a brief weights them: a v4 brief with only tolerances is "v3, normalised".
V4_DEFAULT_WEIGHTS = {**DEFAULT_WEIGHTS, "distd": 0.0, "diag": 0.0}

_COV_BELOW_F0 = ("mask", "one_sided")
_DIAG_REFERENCES = ("round",)
_BLOCK_KEYS = {"version", "tolerances", "cov_narrow_ratio", "cov_below_f0", "diag_reference"}


@dataclass(frozen=True)
class V4Params:
    """The ``objective:`` block of a v4 brief, validated. Tolerances have NO defaults."""

    tolerances: dict
    cov_narrow_ratio: float = 1.0
    cov_below_f0: str = "mask"
    diag_reference: str = "round"

    @classmethod
    def from_block(cls, block: dict) -> "V4Params":
        """Validate a raw ``objective:`` mapping. Raises ``ValueError`` (config wraps it).

        A v4 block missing any tolerance, or carrying a non-positive / non-finite one, is an error:
        a silent default would let two briefs mean different things by the same weight."""
        if not isinstance(block, dict):
            raise ValueError("objective must be a mapping")
        unknown = set(block) - _BLOCK_KEYS
        if unknown:
            raise ValueError(f"objective unknown key(s) {sorted(unknown)} "
                             f"(allowed for v4: {sorted(_BLOCK_KEYS)})")
        tol = block.get("tolerances")
        if not isinstance(tol, dict):
            raise ValueError("objective v4 needs a 'tolerances' mapping with one entry per term: "
                             f"{list(V4_WEIGHTED_KEYS)}")
        missing = [k for k in V4_WEIGHTED_KEYS if k not in tol]
        extra = sorted(set(tol) - set(V4_WEIGHTED_KEYS))
        if missing or extra:
            raise ValueError(f"objective.tolerances: missing {missing}, unknown {extra} "
                             f"(required: {list(V4_WEIGHTED_KEYS)})")
        clean: dict = {}
        for k in V4_WEIGHTED_KEYS:
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
        ref = block.get("diag_reference", "round")
        if ref not in _DIAG_REFERENCES:
            raise ValueError(f"objective.diag_reference must be one of {list(_DIAG_REFERENCES)}, got {ref!r}")
        return cls(tolerances=clean, cov_narrow_ratio=float(ratio), cov_below_f0=str(below),
                   diag_reference=str(ref))

    def to_block(self) -> dict:
        """The normalised mapping stored in the config (so ``config_sha`` covers every choice)."""
        return {"version": 4, "tolerances": dict(self.tolerances),
                "cov_narrow_ratio": self.cov_narrow_ratio, "cov_below_f0": self.cov_below_f0,
                "diag_reference": self.diag_reference}


def resolve_v4_weights(weights: dict | None) -> dict:
    """v4 defaults overlaid with ``weights``; unknown keys warn (never raise), as in v1-v3."""
    out = dict(V4_DEFAULT_WEIGHTS)
    for k, v in (weights or {}).items():
        if k in V4_DEFAULT_WEIGHTS:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                log.warning("weight %r=%r is not a number; using the default %r", k, v, out[k])
        else:
            log.warning("unknown objective weight %r ignored (known: %s)", k, sorted(V4_DEFAULT_WEIGHTS))
    return out


def worst_valid_j(params: V4Params, weights: dict | None) -> float:
    """J of a VALID design whose every weighted term is unmeasurable (each = ``NAN_TERM_FILL``).

    The penalty-ordering invariant (plan 3d.2): this must stay far below ``PENALTY_INVALID``, or a
    refused design could outrank a working one. Config checks it at load, per brief."""
    w = resolve_v4_weights(weights)
    return float(sum(w[k] * NAN_TERM_FILL / params.tolerances[k] for k in V4_WEIGHTED_KEYS))


def _v4_penalty(value: float = PENALTY_FAILED, *, n_in_band: int = 0) -> tuple[float, dict]:
    j, t = penalty_result(value, n_in_band=n_in_band)
    for k in V4_EXTRA_KEYS:
        t[k] = 0.0
    return j, t


def objective_v4(metrics, resp, ok, target: Target, weights: dict | None, params: V4Params):
    """Score one evaluation under objective v4. ``(J, terms)``; ``terms`` has ``V4_ALL_KEYS``."""
    try:
        return _objective_v4(metrics, resp, ok, target, weights, params)
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("objective_v4() failed; returning the failure penalty")
        return _v4_penalty(PENALTY_FAILED)


def _side_weight(err: np.ndarray, ratio: float) -> np.ndarray:
    """``ratio`` on the narrow side (error < 0), 1.0 on the wide side. NaN errors get 1.0."""
    return np.where(err < 0.0, ratio, 1.0)


def _cov_term(metrics, target: Target, f: np.ndarray, band: np.ndarray, params: V4Params) -> float:
    """Coverage with the narrow-side ratio and the optional one-sided-below-f0 rule.

    Per plane: the (frequency-weighted) mean of ``side * err^2 / 100`` over the scored set, summed
    over H and V - the same shape as v3's cov, so with ratio 1 and ``mask`` it IS v3's cov."""
    wv = freq_weight_vector(f, target)
    f0_h = target.f0_effective_hz()
    f0_v = float(target.f0_v_hz) if target.f0_v_hz is not None else f0_h
    total = 0.0
    for bw, cov_t, f0 in ((metrics.bw_h_deg, target.coverage_h_deg, f0_h),
                          (metrics.bw_v_deg, target.coverage_v_deg, f0_v)):
        err = np.asarray(bw, dtype=float) - float(cov_t)
        above = f >= f0
        side = _side_weight(err, params.cov_narrow_ratio)
        if params.cov_below_f0 == "one_sided":
            included = band
            side = np.where(~above & (err > 0.0), 0.0, side)      # wide below f0 is physics: free
        else:
            included = band & above
        contrib = (side * err ** 2)[included] / 100.0
        if target.freq_weights is not None:
            m, _ = _weighted_mean(contrib, wv[included])
        else:
            m, _ = _plain_mean(contrib)
        total += m
    return float(total)


def _diag_term(metrics, resp, target: Target, f: np.ndarray, score: np.ndarray,
               params: V4Params) -> float:
    """Mean over the scored band of ((bw45 - t)^2 side + (bw135 - t)^2 side) / 100 with ``t`` the
    round reference (mean of the H and V targets). Unmeasurable (no balloon) = ``NAN_TERM_FILL``."""
    cuts = _cut_arrays(resp, f.size)
    ax = None if cuts is None else _on_axis_index(resp, cuts[0])
    dirs = getattr(resp, "balloon_dirs", None)
    bal = getattr(resp, "spl_balloon_db", None)
    if cuts is None or ax is None or dirs is None or bal is None:
        return NAN_TERM_FILL
    bal = np.asarray(bal, dtype=float)
    if bal.ndim != 2 or bal.shape[0] != f.size:
        return NAN_TERM_FILL
    t_ref = 0.5 * (float(target.coverage_h_deg) + float(target.coverage_v_deg))
    idx = np.nonzero(score)[0]
    contrib = np.full(idx.size, np.nan)
    for n, i in enumerate(idx):
        w45, w135 = diagonal_beamwidths_deg(dirs, bal[i], float(cuts[2][i, ax]))
        e = np.array([w45 - t_ref, w135 - t_ref])
        if np.all(np.isfinite(e)):
            contrib[n] = float(np.sum(_side_weight(e, params.cov_narrow_ratio) * e ** 2)) / 100.0
    if target.freq_weights is not None:
        m, _ = _weighted_mean(contrib, freq_weight_vector(f, target)[idx])
    else:
        m, _ = _plain_mean(contrib)
    return float(m)


def _objective_v4(metrics, resp, ok, target: Target, weights, params: V4Params):
    if metrics is None or not ok:
        return _v4_penalty(PENALTY_FAILED)
    w = resolve_v4_weights(weights)
    # v3 supplies the raw cov/rip/di/dislope/flat/load (and every NaN/mask rule); v4 overrides cov
    # only when asked, and adds distd / diag. v3 is handed the six v1-v3 weights only.
    _, raw = _objective_v3(metrics, resp, ok, target, {k: w[k] for k in WEIGHTED_KEYS})
    if raw["penalty"] > 0.0:
        return _v4_penalty(float(raw["penalty"]), n_in_band=int(raw["n_in_band"]))

    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    score = band & (f >= target.f0_effective_hz())

    t_raw = {k: float(raw[k]) for k in WEIGHTED_KEYS}
    if params.cov_narrow_ratio != 1.0 or params.cov_below_f0 != "mask":
        t_raw["cov"] = _cov_term(metrics, target, f, band, params)

    if w["distd"] != 0.0:
        di_s = np.asarray(metrics.di_db, dtype=float)[score]
        good = di_s[np.isfinite(di_s)]
        t_raw["distd"] = float(np.std(good)) if good.size >= 2 else 0.0
    else:
        t_raw["distd"] = 0.0
    t_raw["diag"] = (_diag_term(metrics, resp, target, f, score, params)
                     if w["diag"] != 0.0 else 0.0)

    t = {k: t_raw[k] / params.tolerances[k] for k in V4_WEIGHTED_KEYS}
    if not all(math.isfinite(v) for v in t.values()):
        return _v4_penalty(PENALTY_FAILED, n_in_band=int(raw["n_in_band"]))
    total = sum(w[k] * t[k] for k in V4_WEIGHTED_KEYS)
    if not math.isfinite(total):
        return _v4_penalty(PENALTY_FAILED, n_in_band=int(raw["n_in_band"]))
    t["penalty"] = 0.0
    t["total"] = float(total)
    t["n_nan"] = raw["n_nan"]
    t["n_in_band"] = raw["n_in_band"]
    t["di_estimated"] = raw["di_estimated"]
    assert set(t) == set(V4_ALL_KEYS)
    return float(total), t
