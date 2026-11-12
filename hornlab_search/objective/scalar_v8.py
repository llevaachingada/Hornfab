"""Objective v8 PROPOSAL (2026-11-12, day-plan group G; OFFLINE ONLY, owner sign-off required).

This module is NOT registered anywhere: ``objective/versions.py`` still dispatches 1-7 only,
no brief uses v8, and nothing switches defaults. It exists as (a) an importable scorer with the
same ``(J, terms)`` conventions as v4/v7, (b) the subject of the offline re-score
(``tools/analysis/v8_rescore.py``) and (c) the owner brief
(``docs/research/OBJECTIVE_V8_PROPOSAL_2026-11-12.md``). NEVER switch a brief to v8 without
owner sign-off.

The v8 recipe (day plan section 5 "New group G"; math background in
``docs/research/SEARCH_MATH_DOSSIER_2026-11.md`` section 6, A.9 term-balance data):

1. **Linear units.** The plan section 5 finding: v4 mixes SQUARED errors (cov, dislope, diag, di)
   with LINEAR ones (rip, flat), so a weight's real influence changes with distance from target
   (v4 shares of J: cov 0.42, rip 0.01 with weight 1.0 like cov). v8 scores every term in the
   error's OWN LINEAR unit:

   =========== =========================== =============================================
   term        v8 raw unit                 definition
   =========== =========================== =============================================
   ``cov``     RMS deg                     sqrt(weighted mean of side-weighted squared
                                           H/V edge error), planes combined; v4's
                                           masks (f0, f0_v, narrow ratio, below-f0)
   ``diag``    RMS deg                     sqrt(mean of the side-weighted squared 45/135
                                           -6 dB beamwidth errors vs the round reference)
   ``rip``     RMS dB                      sqrt(weighted mean of the squared per-f
                                           ripple_h + ripple_v (v2 detrended when the
                                           Response is present))
   ``di``      RMS dB                      sqrt(mean of (di - DI target)^2)
   ``dislope`` dB/decade                   |slope - target|, LINEAR (1 dB/decade =
                                           0.301 dB/oct; the repo's only defined slope
                                           unit is dB/decade, so v8 keeps it)
   ``flat``    dB                          v2's detrended band flatness (already a dB
                                           std, inherited unchanged)
   ``distd``   dB                          v4's DI std over the scored band (linear dB)
   ``flat_cv`` dB                          v7's constant-velocity on-axis flatness
                                           (already a dB std), weight default 0.0
   =========== =========================== =============================================

   ``load`` is NOT a term in v8: loading becomes the hard :ref:`gates` below.

2. **Data-calibrated tolerances.** Each weighted term is divided by a per-brief-class tolerance
   ``tol_k = median(raw unit value of term k over the top decile of stored valid rows)`` (ranked
   under the class-matched v4 brief; measured 2026-11-12 over the committed dataset by
   ``tools/analysis/v8_rescore.py``, [measured] numbers in the owner brief). Near the optimum
   every weighted term then contributes ~equally per unit weight ("a weight is an influence").

3. **Gates as hard refusals.** Round throat, loading (LFP20 x 1.6 <= F_X and Re z >= 0.50 over
   the loaded window) and f11 (the loaded window must resolve and be non-empty) return the
   1e3 refusal penalty instead of contributing to J. Trigger rules (documented, never silent):

   * ``loading`` / ``f11`` fire ONLY for a loading-scored target (``target.z_min >= 0.5``, the
     repo's own class-B marker used by ``tools/rescore/rescore_v6_v7.classify_target``);
   * ``round_throat`` fires only when the caller supplies the throat shape (the same
     ``throat_check.throat_shape`` dict ``search/evaluate.py``'s C4 refusal reads); absent
     throat data = not applied, because in-search enforcement stays with C4;
   * a gate that is applied but UNMEASURABLE (no z, no crossing, empty window) REFUSES
     (the canonical ``tools/rescore/gate_audit.py`` convention: unresolved fails).

Everything else mirrors v4/v7 conventions: ``resolve_v8_weights`` overlays defaults (unknown keys
warn), ``worst_valid_j`` keeps the penalty-ordering invariant, a term whose every in-band sample
is unmeasurable stores ``NAN_TERM_FILL / tol`` (finite, unflattering), and ``objective_v8`` never
raises, never returns nan or inf. Pure numpy, no solver, no GPU.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

from ..constants import BESSEL_J1P_11, C_AIR
from ..mesh.throat_check import fits_exit
from ..metrics.di import di_slope_db_per_decade, target_di_gaussian_db
from ..metrics.diagonal import diagonal_beamwidths_deg
from ..targets.spec import Target
from .scalar import penalty_result
from .scalar_v2 import (_cut_arrays, _on_axis_index, _plain_mean, _v2_flat_value,
                        _v2_ripple_values, _weighted_mean, freq_weight_vector)
from .scalar_v4 import _side_weight
from .scalar_v7 import _first_crossing_hz, _flat_cv_term, _resolve_f11_hz
from .scalar_v7 import V7_DIAGNOSTIC_KEYS
from .terms import NAN_TERM_FILL, PENALTY_FAILED

log = logging.getLogger("hornlab_search.objective.scalar_v8")

__all__ = ["objective_v8", "v8_raw_terms", "v8_gate_refusal", "V8Params", "V8_WEIGHTED_KEYS",
           "V8_ALL_KEYS", "V8_DIAGNOSTIC_KEYS", "V8_DEFAULT_WEIGHTS", "V8_MEASURED_TOLERANCES",
           "GATE_KEYS", "LOADING_GATE_Z_MIN", "resolve_v8_weights", "worst_valid_j"]

#: v4/v7's weighted terms minus ``load`` (a gate in v8) plus v4's distd/diag and v7's flat_cv.
V8_WEIGHTED_KEYS = ("cov", "rip", "di", "dislope", "flat", "distd", "diag", "flat_cv")
#: Loading-window diagnostics, same keys as v7's C1 (shared convention, read-only extras).
V8_DIAGNOSTIC_KEYS = V7_DIAGNOSTIC_KEYS
#: Refusal flag stored with the terms (0.0 / 1.0, so the terms dict stays float-only).
V8_EXTRA_KEYS = V8_DIAGNOSTIC_KEYS + ("gate_failed",)
V8_ALL_KEYS = V8_WEIGHTED_KEYS + ("penalty", "total", "n_nan", "n_in_band", "di_estimated") \
    + V8_EXTRA_KEYS
#: v4's defaults for the shared keys (v4/v7 behaviour), ``load`` gone (gate), the v4-only and
#: v7-only extras stay silent unless a brief asks. Same defaults -> "v4 without the squared/load
#: pathologies plus calibration", nothing else moves.
V8_DEFAULT_WEIGHTS = {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5,
                      "distd": 0.0, "diag": 0.0, "flat_cv": 0.0}

#: The hard-refusal gate names (day plan section 5). ``round_throat`` needs caller-supplied
#: throat data; ``loading``/``f11`` need a loading-scored target (see the module docstring).
GATE_KEYS = ("round_throat", "loading", "f11")

#: A target whose ``z_min`` is at least this asks for the loading hold (the repo's own marker:
#: ``tools/rescore/rescore_v6_v7.classify_target`` calls such targets class B).
LOADING_GATE_Z_MIN = 0.5

#: The canonical gate constants (owner 2026-10-29, mirrored from ``tools/rescore/gate_audit.py``
#: and v7's defaults; NOT re-invented here).
_GATE_LFP_RE_Z = 0.20
_GATE_LOADED_RE_Z = 0.50
_GATE_LFP_CROSSOVER_RATIO = 1.6

#: Measured per-class tolerances: ``tol_k = median(raw unit value of term k over the top decile
#: of the class's stored valid dataset rows)`` ranked under the class-matched v4 brief, top
#: decile = max(3, ceil(n/10)) rows (the A.9 ``term_balance`` convention). Measured 2026-11-12
#: by ``tools/analysis/v8_rescore.py`` over the full committed dataset: **23,833 rows scored**
#: (class A 18,145; B 4,063; C 1,625). The numbers are summarised in
#: ``docs/research/OBJECTIVE_V8_PROPOSAL_2026-11-12.md`` section 4; the reproducible source is
#: the run JSON (``scratch/objective_v8_full_2026-11-12/v8_rescore.json``; command in the brief).
#: Values are in the units of the table above. They are descriptive calibration defaults for the
#: proposal, not an independently validated tolerance set.
V8_MEASURED_TOLERANCES: dict[str, dict[str, float]] = {
    "A": {"cov": 8.757688573042602, "rip": 0.42191807648960944, "di": 1.443739415254483,
          "dislope": 0.17439423463107215, "flat": 0.9284635221960371,
          "distd": 0.5647747600028713, "diag": 8.745682431974728,
          "flat_cv": 0.7642950396262194},
    "B": {"cov": 22.719221938279105, "rip": 0.5222073382675729, "di": 1.9399359904891833,
          "dislope": 1.69525764553831, "flat": 2.0988250353739883,
          "distd": 1.5949341457011132, "diag": 20.85593945083782,
          "flat_cv": 1.3608018938550763},
    "C": {"cov": 14.381957593015777, "rip": 0.3519286403834949, "di": 1.209070488584681,
          "dislope": 0.43361149512384534, "flat": 2.116955744540814,
          "distd": 0.7718229842948265, "diag": 15.445944458446165,
          "flat_cv": 1.1235766836224141},
}

_GATES = ("round_throat", "loading", "f11")
_BLOCK_KEYS = {"version", "tolerances", "cov_narrow_ratio", "cov_below_f0", "diag_reference",
               "gates", "loaded_re_z", "lfp_re_z", "lfp_crossover_ratio"}


@dataclass(frozen=True)
class V8Params:
    """The ``objective:`` block of a hypothetical v8 brief, validated. Tolerances have no silent
    defaults inside ``from_block``; the measured per-class defaults live in
    :data:`V8_MEASURED_TOLERANCES` and are used only through :meth:`for_class`."""

    tolerances: dict
    cov_narrow_ratio: float = 1.0
    cov_below_f0: str = "mask"
    diag_reference: str = "round"
    gates: tuple = _GATES
    loaded_re_z: float = _GATE_LOADED_RE_Z
    lfp_re_z: float = _GATE_LFP_RE_Z
    lfp_crossover_ratio: float = _GATE_LFP_CROSSOVER_RATIO

    @classmethod
    def from_block(cls, block: dict) -> "V8Params":
        """Validate a raw ``objective:`` mapping. Raises ``ValueError`` (config would wrap it)."""
        if not isinstance(block, dict):
            raise ValueError("objective must be a mapping")
        unknown = set(block) - _BLOCK_KEYS
        if unknown:
            raise ValueError(f"objective unknown key(s) {sorted(unknown)} "
                             f"(allowed for v8: {sorted(_BLOCK_KEYS)})")
        tol = block.get("tolerances")
        if not isinstance(tol, dict):
            raise ValueError("objective v8 needs a 'tolerances' mapping with one entry per term: "
                             f"{list(V8_WEIGHTED_KEYS)}")
        missing = [k for k in V8_WEIGHTED_KEYS if k not in tol]
        extra = sorted(set(tol) - set(V8_WEIGHTED_KEYS))
        if missing or extra:
            raise ValueError(f"objective.tolerances: missing {missing}, unknown {extra} "
                             f"(required: {list(V8_WEIGHTED_KEYS)})")
        clean: dict = {}
        for k in V8_WEIGHTED_KEYS:
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
        if below not in ("mask", "one_sided"):
            raise ValueError(f"objective.cov_below_f0 must be one of ['mask', 'one_sided'], "
                             f"got {below!r}")
        ref = block.get("diag_reference", "round")
        if ref not in ("round",):
            raise ValueError(f"objective.diag_reference must be one of ['round'], got {ref!r}")
        gates_raw = block.get("gates", list(_GATES))
        if isinstance(gates_raw, str) or not isinstance(gates_raw, (list, tuple)) \
                or any(g not in _GATES for g in gates_raw):
            raise ValueError(f"objective.gates must be a list drawn from {list(_GATES)}, "
                             f"got {gates_raw!r}")
        constants = {}
        for key, default in (("loaded_re_z", _GATE_LOADED_RE_Z), ("lfp_re_z", _GATE_LFP_RE_Z),
                             ("lfp_crossover_ratio", _GATE_LFP_CROSSOVER_RATIO)):
            v = block.get(key, default)
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or not math.isfinite(float(v)) or not float(v) > 0.0:
                raise ValueError(f"objective.{key} must be a finite number > 0, got {v!r}")
            constants[key] = float(v)
        return cls(tolerances=clean, cov_narrow_ratio=float(ratio), cov_below_f0=str(below),
                   diag_reference=str(ref), gates=tuple(gates_raw), **constants)

    @classmethod
    def for_class(cls, brief_class: str) -> "V8Params":
        """The measured-default parameters for a brief class (``"A"``, ``"B"`` or ``"C"``).

        Tolerances = :data:`V8_MEASURED_TOLERANCES`; gates all on (refusals for loading-scored
        targets; round throat when throat data is supplied)."""
        if brief_class not in V8_MEASURED_TOLERANCES:
            raise ValueError(f"no measured v8 tolerances for class {brief_class!r} "
                             f"(known: {sorted(V8_MEASURED_TOLERANCES)})")
        return cls.from_block({"version": 8,
                               "tolerances": dict(V8_MEASURED_TOLERANCES[brief_class])})

    def to_block(self) -> dict:
        """The normalised mapping stored in the config (so a config_sha would cover every choice)."""
        return {"version": 8, "tolerances": dict(self.tolerances),
                "cov_narrow_ratio": self.cov_narrow_ratio, "cov_below_f0": self.cov_below_f0,
                "diag_reference": self.diag_reference, "gates": list(self.gates),
                "loaded_re_z": self.loaded_re_z, "lfp_re_z": self.lfp_re_z,
                "lfp_crossover_ratio": self.lfp_crossover_ratio}


def resolve_v8_weights(weights: dict | None) -> dict:
    """v8 defaults overlaid with ``weights``; unknown keys warn (never raise), as in v1-v7."""
    out = dict(V8_DEFAULT_WEIGHTS)
    for k, v in (weights or {}).items():
        if k in V8_DEFAULT_WEIGHTS:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                log.warning("weight %r=%r is not a number; using the default %r", k, v, out[k])
        else:
            log.warning("unknown objective weight %r ignored (known: %s)", k, sorted(V8_DEFAULT_WEIGHTS))
    return out


def worst_valid_j(params: V8Params, weights: dict | None) -> float:
    """J of a VALID design whose every weighted term is unmeasurable (each = ``NAN_TERM_FILL``)."""
    w = resolve_v8_weights(weights)
    return float(sum(w[k] * NAN_TERM_FILL / params.tolerances[k] for k in V8_WEIGHTED_KEYS))


def _v8_penalty(value: float = PENALTY_FAILED, *, n_in_band: int = 0,
                diag: dict | None = None, gate_failed: bool = False) -> tuple[float, dict]:
    j, t = penalty_result(value, n_in_band=n_in_band)
    t.pop("load", None)          # v8 has no load term; the penalty dict keeps the v8 key set
    for k in V8_WEIGHTED_KEYS:
        t[k] = 0.0
    g = diag or {}
    for k in V8_DIAGNOSTIC_KEYS:
        t[k] = float(g[k]) if k in g else NAN_TERM_FILL
    t["gate_failed"] = 1.0 if gate_failed else 0.0
    return j, t


# ------------------------------------------------------------------ gates (hard refusals)


def _v8_exit_diameter_mm(target: Target) -> float | None:
    """The driven-plane diameter the round-throat gate compares against, from the target."""
    radius = getattr(target, "driver_exit_radius_mm", None)
    if radius is None:
        return None
    try:
        radius = float(radius)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(radius) and radius > 0.0):
        return None
    return 2.0 * radius


def _loading_and_f11_gates(freqs: np.ndarray, z: np.ndarray | None, target: Target,
                           metrics, params: V8Params) -> tuple[str | None, str | None, dict]:
    """Evaluate the loading and f11 gates for a loading-scored target.

    Returns ``(load_fail, f11_fail, diag)``; ``None`` means that gate passes. The diag values
    are stored with the terms either way (same keys as v7's C1 diagnostics).
    """
    diag = {k: NAN_TERM_FILL for k in V8_DIAGNOSTIC_KEYS}
    load_fail: str | None = None
    f11_fail: str | None = None
    fx = float(target.f0_effective_hz())
    band_hi = float(target.band_hi_hz)
    # The Re z hold's upper bound: v7's canonical precedence (explicit -> driver exit -> stored).
    loaded_hi = band_hi
    f11 = _resolve_f11_hz(target, metrics)
    if f11 is not None:
        loaded_hi = min(band_hi, f11)
        diag["f11_hz"] = f11
    diag["loaded_hi_hz"] = loaded_hi
    in_window = (freqs >= fx) & (freqs <= loaded_hi)
    if z is None:
        return ("no z_throat_real: the loading hold is unmeasurable",
                None if bool(in_window.any())
                else f"loaded window [{fx:g}, {loaded_hi:g}] Hz has no solved sample", diag)
    zgood = np.isfinite(z) & in_window
    if loaded_hi < fx:
        # Contradictory window (e.g. an explicit loaded_hi_hz below F_X): the f11 gate refuses
        # and the loading hold is unmeasurable with it.
        return (f"loaded window ends at {loaded_hi:g} Hz, below F_X {fx:g} Hz",
                f"loaded window ends at {loaded_hi:g} Hz, below F_X {fx:g} Hz", diag)
    if not zgood.any():
        # No measurable window: the loading hold is unmeasurable AND the window is empty.
        return ("no usable Re z sample in the loaded window "
                f"[{fx:g}, {loaded_hi:g}] Hz",
                f"loaded window [{fx:g}, {loaded_hi:g}] Hz has no solved sample", diag)
    lfp20 = _first_crossing_hz(freqs, z, params.lfp_re_z)
    lfp50 = _first_crossing_hz(freqs, z, 0.50)
    if lfp20 is not None:
        diag["lfp20_hz"] = lfp20
    if lfp50 is not None:
        diag["lfp50_hz"] = lfp50
    if lfp20 is None:
        load_fail = (f"LFP20 has no ascending crossing of Re z = {params.lfp_re_z:g} at or below "
                     f"the highest solved frequency {float(freqs[-1]):g} Hz")
    elif lfp20 * params.lfp_crossover_ratio > fx:
        load_fail = (f"LFP20 {lfp20:.1f} Hz x {params.lfp_crossover_ratio:g} = "
                     f"{lfp20 * params.lfp_crossover_ratio:.1f} Hz > F_X {fx:g} Hz")
    rez_min = float(np.min(z[zgood]))
    diag["rez_min_from_fx"] = rez_min
    if load_fail is None and rez_min < params.loaded_re_z:
        load_fail = (f"Re z {rez_min:.3f} < {params.loaded_re_z:g} in "
                     f"[{fx:g}, {loaded_hi:g}] Hz")
    return load_fail, f11_fail, diag


def _round_throat_gate(throat: dict, exit_diameter_mm: float | None) -> tuple[bool, str]:
    """The round-throat gate: ``throat_check.fits_exit`` on the supplied driven-plane shape.

    Same convention as ``search/evaluate.py``'s C4 refusal: a misfit or unjudgeable supplied
    shape refuses. Returns ``(refused, reason)``; the caller treats a missing shape as not
    applied (in-search enforcement stays with C4)."""
    if exit_diameter_mm is None:
        return True, "no driver exit radius on the target: the round-throat gate cannot compare"
    ok, why = fits_exit(dict(throat), float(exit_diameter_mm))
    if ok is None:
        return True, f"throat unresolved: {why}"
    if not ok:
        return True, f"throat does not fit the driver exit: {why}"
    return False, ""


# ------------------------------------------------------------------ linear-unit raw terms


def _weighted_rms(values: np.ndarray, weights: np.ndarray | None) -> float:
    """sqrt(weighted mean of squares) over the finite entries; empty = ``NAN_TERM_FILL``."""
    v = np.asarray(values, dtype=float)
    ok = np.isfinite(v)
    if not ok.any():
        return NAN_TERM_FILL
    vv = v[ok]
    if weights is not None:
        ww = np.asarray(weights, dtype=float)[ok]
        if ww.shape == vv.shape and np.all(np.isfinite(ww)) and float(np.sum(ww)) > 0.0:
            return float(math.sqrt(float(np.sum(ww * vv ** 2) / np.sum(ww))))
        # An unusable weight vector degrades to the plain mean (the _weighted_mean convention).
    return float(math.sqrt(float(np.mean(vv ** 2))))


def _cov_term_linear(metrics, target: Target, f: np.ndarray, band: np.ndarray,
                     params: V8Params) -> float:
    """RMS deg coverage: sqrt(sum of the per-plane weighted-mean squared side-weighted errors).

    v4's masks exactly (per-plane f0/f0_v, narrow-side ratio, optional one-sided below-f0) minus
    the /100 and the square: a plane whose every scored sample is unmeasurable makes the whole
    term ``NAN_TERM_FILL`` (not v4's sum-of-fills)."""
    wv = freq_weight_vector(f, target)
    f0_h = target.f0_effective_hz()
    f0_v = float(target.f0_v_hz) if target.f0_v_hz is not None else f0_h
    total_sq = 0.0
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
        contrib = (side * err ** 2)[included]
        if target.freq_weights is not None:
            m, _ = _weighted_mean(contrib, wv[included])
        else:
            m, _ = _plain_mean(contrib)
        if not math.isfinite(m) or m == NAN_TERM_FILL:
            return NAN_TERM_FILL
        total_sq += m
    return float(math.sqrt(total_sq))


def _di_term_linear(metrics, target: Target, band: np.ndarray) -> float:
    """RMS dB DI error against the DI target (v3's reference: explicit or the Gaussian beam)."""
    d = np.asarray(metrics.di_db, dtype=float)[band]
    if target.di_target_db is not None:
        ref = float(target.di_target_db)
    else:
        ref = float(target_di_gaussian_db(target.coverage_h_deg, target.coverage_v_deg))
    return _weighted_rms(d - ref, None)


def _dislope_term_linear(f: np.ndarray, di: np.ndarray, target: Target) -> float:
    """LINEAR DI-slope error in dB/decade (1 dB/decade = 0.301 dB/oct) over the score band.

    Fewer than two usable points: contributes 0.0 (v3's ``dislope_term`` convention)."""
    s = di_slope_db_per_decade(f, di)
    if not np.isfinite(s):
        return 0.0
    return float(abs(s - float(target.di_slope_target)))


def _diag_term_linear(metrics, resp, target: Target, f: np.ndarray, score: np.ndarray,
                      params: V8Params) -> float:
    """RMS deg diagonal error: v4's 45/135-degree loop without the /100 and the square.

    ``sqrt(mean_f(side-weighted summed squared errors))``; unmeasurable = ``NAN_TERM_FILL``."""
    cuts = _cut_arrays(resp, f.size)
    if cuts is None:
        return NAN_TERM_FILL
    ax = None if cuts is None else _on_axis_index(resp, cuts[0])
    dirs = getattr(resp, "balloon_dirs", None)
    bal = getattr(resp, "spl_balloon_db", None)
    if ax is None or dirs is None or bal is None:
        return NAN_TERM_FILL
    bal = np.asarray(bal, dtype=float)
    if bal.ndim != 2 or bal.shape[0] != f.size:
        return NAN_TERM_FILL
    t_ref = 0.5 * (float(target.coverage_h_deg) + float(target.coverage_v_deg))
    idx = np.nonzero(score)[0]
    if idx.size == 0:
        return NAN_TERM_FILL
    contrib = np.full(idx.size, np.nan)
    for n, i in enumerate(idx):
        w45, w135 = diagonal_beamwidths_deg(dirs, bal[i], float(cuts[2][i, ax]))
        e = np.array([w45 - t_ref, w135 - t_ref])
        if np.all(np.isfinite(e)):
            contrib[n] = float(np.sum(_side_weight(e, params.cov_narrow_ratio) * e ** 2))
    m = None
    if target.freq_weights is not None:
        m, _ = _weighted_mean(contrib, freq_weight_vector(f, target)[idx])
    else:
        m, _ = _plain_mean(contrib)
    if not math.isfinite(m) or m == NAN_TERM_FILL:
        return NAN_TERM_FILL
    return float(math.sqrt(m))


# ------------------------------------------------------------------ the whole raw term set


def v8_raw_terms(metrics, resp, target: Target, band: np.ndarray, score: np.ndarray,
                 params: V8Params, weights: dict | None = None,
                 throat: dict | None = None) -> dict:
    """Raw linear-unit values of every v8 weighted term plus gates/diagnostics.

    Returns ``{"raw": {term: value}, "diag": {key: value}, "gate_failed": bool,
    "gate_reason": str | None}``. Gate refusals do NOT blank the raw values (the caller decides
    what a refused row contributes). Raw values are weight-INDEPENDENT (a zero-weight term still
    stores its measured raw, so the tolerance calibration and any re-weighting see real data).
    This is the ONE term implementation: ``objective_v8`` and the offline re-score both call it,
    so the scorer and the analysis cannot drift.
    """
    f = np.asarray(metrics.freqs_hz, dtype=float)
    raw: dict = {}
    raw["cov"] = _cov_term_linear(metrics, target, f, band, params)
    ripple_values, _used_resp = _v2_ripple_values(metrics, resp, target, band)
    wv = freq_weight_vector(f, target) if target.freq_weights is not None else None
    raw["rip"] = _weighted_rms(ripple_values[band], (wv[band] if wv is not None else None))
    raw["di"] = _di_term_linear(metrics, target, band)
    raw["dislope"] = _dislope_term_linear(f[score], np.asarray(metrics.di_db, dtype=float)[score],
                                          target)
    raw["flat"] = _v2_flat_value(metrics, resp, target, band)
    # distd / diag / flat_cv raws are computed even at weight 0: the weighted contribution is
    # their weight * raw / tol either way, and the raw values are exactly what the tolerance
    # calibration (and any later re-weighting) needs. "Raw 0.0 at zero weight" is v7's storage
    # convention, not v8's; v8 always stores the measured raw.
    di_s = np.asarray(metrics.di_db, dtype=float)[score]
    good = di_s[np.isfinite(di_s)]
    raw["distd"] = float(np.std(good)) if good.size >= 2 else 0.0
    raw["diag"] = _diag_term_linear(metrics, resp, target, f, score, params)
    raw["flat_cv"] = _flat_cv_term(metrics, target, f, 1.0)

    diag = {k: NAN_TERM_FILL for k in V8_DIAGNOSTIC_KEYS}
    gate_failed = False
    gate_reason: str | None = None
    loading_scored = float(target.z_min) >= LOADING_GATE_Z_MIN
    if loading_scored and ("loading" in params.gates or "f11" in params.gates):
        z = None if metrics.z_throat_real is None else np.asarray(metrics.z_throat_real, dtype=float)
        load_fail, f11_fail, gdiag = _loading_and_f11_gates(f, z, target, metrics, params)
        diag.update(gdiag)
        if "loading" in params.gates and load_fail is not None:
            gate_failed, gate_reason = True, load_fail
        elif "f11" in params.gates and f11_fail is not None:
            gate_failed, gate_reason = True, f11_fail
    if "round_throat" in params.gates and throat is not None:
        refused, reason = _round_throat_gate(throat, _v8_exit_diameter_mm(target))
        if refused:
            gate_failed, gate_reason = True, reason
    return {"raw": raw, "diag": diag, "gate_failed": gate_failed, "gate_reason": gate_reason}


def v8_gate_refusal(metrics, resp, ok, target: Target, params: V8Params,
                    weights: dict | None, throat: dict | None = None) -> str | None:
    """The v8 hard-refusal reason for one evaluation, or ``None`` when nothing refuses.

    Mirrors exactly what :func:`objective_v8` refuses (gates only; an invalid/missing
    evaluation is the ordinary ``PENALTY_FAILED`` path, not a gate refusal)."""
    if metrics is None or not ok:
        return None
    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    if not band.any() or not (band & (f >= target.f0_effective_hz())).any():
        return None
    out = v8_raw_terms(metrics, resp, target, band, band & (f >= target.f0_effective_hz()),
                       params, throat=throat)
    return out["gate_reason"]


def objective_v8(metrics, resp, ok, target: Target, weights: dict | None, params: V8Params,
                 throat: dict | None = None) -> tuple[float, dict]:
    """Score one evaluation under objective v8. ``(J, terms)``; ``terms`` has ``V8_ALL_KEYS``.

    Hard refusals (loading / f11 for a loading-scored target, round throat when the caller
    supplies the throat shape) return the 1e3 failure penalty with ``terms["gate_failed"] = 1``.
    Never raises, never returns nan or inf."""

    def refused(value: float, *, n_in_band: int, info: dict | None = None):
        d = (info or {}).get("diag") if info else None
        reason = (info or {}).get("gate_reason") if info else None
        if reason:
            log.warning("objective_v8 refusal: %s", reason)
        return _v8_penalty(value, n_in_band=n_in_band, diag=d, gate_failed=bool(reason))

    try:
        return _objective_v8(metrics, resp, ok, target, weights, params, throat, refused)
    except Exception:  # noqa: BLE001 - the contract says never raises
        log.exception("objective_v8() failed; returning the failure penalty")
        return _v8_penalty(PENALTY_FAILED)


def _objective_v8(metrics, resp, ok, target: Target, weights, params: V8Params, throat,
                  refused) -> tuple[float, dict]:
    if metrics is None or not ok:
        return _v8_penalty(PENALTY_FAILED)
    w = resolve_v8_weights(weights)
    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    n_band = int(band.sum())
    if n_band == 0:
        log.warning("no solved frequency inside the band [%g, %g] Hz", target.band_lo_hz,
                    target.band_hi_hz)
        return _v8_penalty(PENALTY_FAILED, n_in_band=0)
    f0 = float(target.f0_effective_hz())
    score = band & (f >= f0)
    if not score.any():
        log.warning("the whole band [%g, %g] Hz sits below f0 = %g Hz; nothing to score",
                    target.band_lo_hz, target.band_hi_hz, f0)
        return _v8_penalty(PENALTY_FAILED, n_in_band=n_band)

    # HARD REFUSALS first: gates never contribute to J.
    info = v8_raw_terms(metrics, resp, target, band, score, params, w, throat)
    if info["gate_failed"]:
        return refused(PENALTY_FAILED, n_in_band=n_band, info=info)

    t = {k: info["raw"][k] / params.tolerances[k] for k in V8_WEIGHTED_KEYS}
    if not all(math.isfinite(v) for v in t.values()):
        return _v8_penalty(PENALTY_FAILED, n_in_band=n_band, diag=info["diag"])
    total = sum(w[k] * t[k] for k in V8_WEIGHTED_KEYS)
    if not math.isfinite(total):
        return _v8_penalty(PENALTY_FAILED, n_in_band=n_band, diag=info["diag"])
    t["penalty"] = 0.0
    t["total"] = float(total)
    t["n_nan"] = 0
    t["n_in_band"] = int(score.sum())
    t["di_estimated"] = 1.0 if metrics.di_source == "cuts_estimate" else 0.0
    for k in V8_DIAGNOSTIC_KEYS:
        t[k] = float(info["diag"][k])
    t["gate_failed"] = 0.0
    assert set(t) == set(V8_ALL_KEYS)
    return float(total), t
