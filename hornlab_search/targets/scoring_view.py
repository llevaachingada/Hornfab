"""P0 scoring-truth view (additive, read-only display truth). Reconstructs scored masks/constants per objective version; never recomputes or changes J.

This module is a pure presentation helper. Given an immutable run's captured ``target`` block,
its captured ``objective`` block, the active term weights and (for v6) the per-design metric
scalars / design params, it reconstructs the frequency windows, angles and constants that the
scorer in ``hornlab_search.objective.scalar*`` actually uses. It never imports GUI code and never
recomputes or edits a score: every number here is a read-only restatement of scorer semantics.

Objective-version dispatch (pinned contract):

* v1/v2 - flat coverage over the whole band: ``below_mode == "scored"``,
  ``h_lo_hz == v_lo_hz == band_lo_hz``.
* v3 - coverage masked below ``f0``: ``below_mode == "mask"``,
  ``h_lo_hz == v_lo_hz == f0_hz`` (falling back to ``band_lo_hz``).
* v4/v5/v7/v8 - ``cov_below_f0`` (``"mask"`` or ``"one_sided"``), ``cov_narrow_ratio``,
  horizontal onset ``f0_hz`` and vertical onset ``f0_v_hz`` (falling back to the H onset).
* v6 - the pattern onset is **per design**: ``f_pattern_hz = pattern_beta * fc_hz`` where
  ``fc_hz`` resolves exactly as ``scalar_v6.resolve_fc_hz`` does (explicit objective ``fc_hz``,
  then the design's ``fc_hz`` / ``g_fc_hz`` scalar, then a ``g_fc_hz`` design param searched flat
  and under ``grid`` / ``knobs``, then ``target.f0_hz``, then ``band_lo_hz``). In v6 the coverage
  onset is ``f_pattern_hz`` for BOTH planes; ``h_lo_hz`` / ``v_lo_hz`` record the ``f0``-derived
  window used by the DI / level-side terms (the v6 scorer computes ``score = band & (f >= f0)``
  for ``di_rise`` / ``distd`` / ``diag``).

Weight handling
---------------
``weights`` may be ``None`` or a partial mapping. A missing key is treated as **zero**; briefs
carry explicit weights, so a missing weight genuinely means "this term is not scored". Values that
are ``None`` or non-finite are also treated as zero. The docstring of each public helper states
which weight key it reads.

Everything exported here is additive. Nothing in ``objective/**``, ``metrics/**`` or
``targets/spec.py`` is imported for its side effects, and no score is recomputed.
"""
from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping

import numpy as np

from hornlab_search.metrics.di import di_from_cuts, target_di_gaussian_db

__all__ = [
    "score_window",
    "di_summary",
    "bw8k_floor",
    "diag_summary",
    "measured_di_slope",
    "build_scoring_view",
]

#: Objective versions whose scoring windows this view can reconstruct.
_SUPPORTED_VERSIONS = (1, 2, 3, 4, 5, 6, 7, 8, 9)

#: The v7 scorer's 8 kHz floor sampling cap (``scalar_v7.BW8K_HZ``), restated as a read-only constant.
_BW8K_HZ = 8000.0

#: Static, display-only caveats attached to every built view. The wording is part of the contract.
_NOTES = {
    "distd": (
        "std(DI) raw spread over the score band - NOT residual roughness; a perfectly "
        "linear rise keeps distd > 0"
    ),
    "di_slope": (
        "slope-only scoring is translation invariant in dB; the intercept is not scored "
        "when di weight is 0"
    ),
    "illustrative_corridor": (
        "any hypothetical narrowing curve drawn by the GUI is display-only, NOT the scored "
        "target; it may violate the 8 kHz floor"
    ),
}


# --------------------------------------------------------------------------- small input guards


def _num(value, *, positive: bool = False) -> float | None:
    """Return ``value`` as a finite float, else ``None``. Bools are not numbers here."""
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    if positive and out <= 0.0:
        return None
    return out


def _as_version(version) -> int | None:
    """Normalise ``version`` to one of ``_SUPPORTED_VERSIONS``; anything else -> ``None``."""
    if isinstance(version, bool):
        return None
    if isinstance(version, float) and not version.is_integer():
        return None
    try:
        out = int(version)
    except (TypeError, ValueError):
        return None
    return out if out in _SUPPORTED_VERSIONS else None


def _as_mapping(value) -> dict:
    """``value`` as a plain dict when it is a mapping or a dataclass, else ``{}`` (never raises)."""
    if isinstance(value, Mapping):
        try:
            return dict(value)
        except Exception:  # noqa: BLE001 - a hostile mapping must not crash the view
            return {}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        try:
            return dataclasses.asdict(value)
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _weight(weights, key: str) -> float:
    """The weight ``key`` as a finite float; missing / ``None`` / non-finite counts as 0."""
    if not isinstance(weights, Mapping):
        return 0.0
    value = weights.get(key, 0.0)
    out = _num(value)
    return 0.0 if out is None else out


def _target_view(raw_target) -> dict | None:
    """Validate the immutable ``target`` block into a small plain dict, or ``None``.

    Requires positive finite coverage angles and ``0 < band_lo_hz < band_hi_hz`` - the same
    essentials ``Target.from_dict`` requires - so a malformed/empty target never reaches the
    reconstructors.
    """
    raw = _as_mapping(raw_target)
    band_lo = _num(raw.get("band_lo_hz"), positive=True)
    band_hi = _num(raw.get("band_hi_hz"), positive=True)
    h_deg = _num(raw.get("coverage_h_deg"), positive=True)
    v_deg = _num(raw.get("coverage_v_deg"), positive=True)
    if band_lo is None or band_hi is None or h_deg is None or v_deg is None:
        return None
    if not band_hi > band_lo:
        return None
    slope = _num(raw.get("di_slope_target"))
    return {
        "band_lo_hz": band_lo,
        "band_hi_hz": band_hi,
        "h_deg": h_deg,
        "v_deg": v_deg,
        "f0_hz": _num(raw.get("f0_hz"), positive=True),
        "f0_v_hz": _num(raw.get("f0_v_hz"), positive=True),
        "di_target_db": _num(raw.get("di_target_db")),
        "di_slope_target": 0.0 if slope is None else slope,
        "coverage_v_up_deg": _num(raw.get("coverage_v_up_deg")),
        "coverage_v_down_deg": _num(raw.get("coverage_v_down_deg")),
    }


def _below_mode(raw_objective: Mapping, default: str = "mask") -> str:
    """Only ``"mask"`` and ``"one_sided"`` are scoring modes; anything else falls back."""
    return "one_sided" if raw_objective.get("cov_below_f0") == "one_sided" else default


def _narrow_ratio(raw_objective: Mapping, default: float = 2.0) -> float:
    """``cov_narrow_ratio`` when finite, else the scorer's default (v4+ uses 2.0)."""
    value = _num(raw_objective.get("cov_narrow_ratio"))
    return default if value is None else value


def _resolve_v6_fc_hz(raw_objective: Mapping, design_scalars, design_params,
                      f0_hz: float | None, band_lo_hz: float) -> float:
    """Mirror ``scalar_v6.resolve_fc_hz`` EXACTLY.

    The scorer reads only the objective block's explicit ``fc_hz`` and the design's
    ``metrics.scalars`` (``fc_hz`` / ``g_fc_hz``, then the brief ``f0``). It never reads
    the generator knobs in ``design.json`` — live-run evidence
    (``runs/20261112T113047Z-screen-24053e``, two stored rows) shows varying ``g_fc_hz``
    leaves every scored onset at ``f_pattern = pattern_beta * f0`` because no scalar key
    is stored. ``design_params`` is therefore accepted for API stability but deliberately
    unread here, so the GUI can never show a pattern onset the scorer did not use."""
    fc = _num(raw_objective.get("fc_hz"), positive=True)
    if fc is not None:
        return fc

    scalars = _as_mapping(design_scalars)
    for key in ("fc_hz", "g_fc_hz"):
        fc = _num(scalars.get(key), positive=True)
        if fc is not None:
            return fc

    if f0_hz is not None:
        return f0_hz
    return band_lo_hz


# --------------------------------------------------------------------------- public helpers


def score_window(raw_target: dict, raw_objective: dict | None, version: int,
                 design_scalars: dict | None = None,
                 design_params: dict | None = None) -> dict | None:
    """Reconstruct the scored frequency window for one objective version.

    Returns a dict with these keys (always all of them):

    ``h_lo_hz``, ``v_lo_hz`` - per-plane coverage onset (``None`` never: falls back to band_lo).
    ``below_mode`` - ``"scored"`` | ``"mask"`` | ``"one_sided"``.
    ``narrow_ratio`` - the narrow-side weight; 1.0 for v1-v3 (no asymmetry), v4+'s
    ``cov_narrow_ratio`` (default 2.0).
    ``band_lo_hz``, ``band_hi_hz`` - the scored band.
    ``h_deg``, ``v_deg`` - total target coverage angles.
    ``coverage_v_up_deg``, ``coverage_v_down_deg`` - signed V halves (``None`` when absent).
    ``fc_hz``, ``f_pattern_hz``, ``pattern_beta`` - v6 only; ``None`` on every other version.

    ``raw_objective`` also carries the ``cov_below_f0`` / ``cov_narrow_ratio`` / ``pattern_beta``
    / ``fc_hz`` knobs. ``design_scalars`` is the per-design metric-scalar mapping (flat);
    ``design_params`` may carry ``g_fc_hz`` flat or under ``grid`` / ``knobs``.

    Malformed or missing ``raw_target`` (and an unsupported ``version``) returns ``None``.
    Never raises.
    """
    try:
        target = _target_view(raw_target)
        if target is None:
            return None
        v = _as_version(version)
        if v is None:
            return None
        obj = _as_mapping(raw_objective)

        band_lo = target["band_lo_hz"]
        band_hi = target["band_hi_hz"]
        f0 = target["f0_hz"]
        f0_v = target["f0_v_hz"]

        out = {
            "h_lo_hz": band_lo,
            "v_lo_hz": band_lo,
            "below_mode": "mask",
            "narrow_ratio": 1.0,
            "band_lo_hz": band_lo,
            "band_hi_hz": band_hi,
            "h_deg": target["h_deg"],
            "v_deg": target["v_deg"],
            "coverage_v_up_deg": target["coverage_v_up_deg"],
            "coverage_v_down_deg": target["coverage_v_down_deg"],
            "fc_hz": None,
            "f_pattern_hz": None,
            "pattern_beta": None,
        }

        if v in (1, 2):
            out["below_mode"] = "scored"
            out["h_lo_hz"] = band_lo
            out["v_lo_hz"] = band_lo
            return out

        if v == 3:
            h_lo = band_lo if f0 is None else f0
            out["below_mode"] = "mask"
            out["h_lo_hz"] = h_lo
            out["v_lo_hz"] = h_lo
            return out

        if v == 6:
            h_lo = band_lo if f0 is None else f0
            fc = _resolve_v6_fc_hz(obj, design_scalars, design_params, f0, band_lo)
            beta = _num(obj.get("pattern_beta"), positive=True)
            beta = 1.6 if beta is None else beta
            out["below_mode"] = _below_mode(obj)
            out["narrow_ratio"] = _narrow_ratio(obj)
            out["h_lo_hz"] = h_lo
            # v6's coverage uses one pattern onset (f_pattern) for BOTH planes; f0_v is not read
            # by the v6 scorer, so the DI-side window is the same for H and V.
            out["v_lo_hz"] = h_lo
            out["fc_hz"] = float(fc)
            out["f_pattern_hz"] = float(beta * fc)
            out["pattern_beta"] = float(beta)
            return out

        # v4 / v5 / v7 / v8 / v9
        h_lo = band_lo if f0 is None else f0
        v_lo = h_lo if f0_v is None else f0_v
        out["below_mode"] = _below_mode(obj)
        # v9's cov_narrow_ratio DEFAULT is 1.0 (amended RFC); scalar targets keep no special
        # narrow-side prior in v9 either way — the brief's explicit key always wins.
        out["narrow_ratio"] = _narrow_ratio(obj, default=1.0 if v == 9 else 2.0)
        out["h_lo_hz"] = h_lo
        out["v_lo_hz"] = v_lo
        if v == 9:
            profile_view = _profile_view(raw_target)
            if profile_view is not None:
                # Per-plane effective onset = max(first_anchor_hz, plane f0) (amendment §D).
                out["h_lo_hz"] = profile_view["onset_h_hz"] if profile_view["onset_h_hz"] else out["h_lo_hz"]
                out["v_lo_hz"] = profile_view["onset_v_hz"] if profile_view["onset_v_hz"] else out["v_lo_hz"]
        return out
    except Exception:  # noqa: BLE001 - a display helper must never crash the caller
        return None


def _profile_view(raw_target) -> dict | None:
    """The v9 coverage-profile display block for one raw target dict, or ``None``.

    Emitted keys (pop-when-unbuildable; a v7 target has no ``profile`` key at all)::

        {"mode", "interpolation", "onset_h_hz", "onset_v_hz",
         "freqs_hz", "h_pref", "h_min", "h_max", "v_pref", "v_min", "v_max"}

    ``freqs_hz`` is a 32-point log grid from the lower per-plane onset to ``band_hi``
    (single point when the onset already sits at the band top). Per-plane arrays carry
    ``None`` below THAT plane's own onset (unscored there) and evaluate
    ``targets.profile.profile_value`` above it; ``min``/``max`` are ``None`` everywhere in
    ``target`` mode. Malformed input or a missing ``targets.profile`` module returns ``None``
    — the config layer refuses invalid profiles at load, so this helper stays display-only."""
    try:
        raw = _as_mapping(raw_target)
        target = _target_view(raw)
        if target is None:
            return None
        profile_raw = _as_mapping(raw.get("coverage_profile"))
        if not profile_raw or profile_raw.get("mode") is None:
            return None
        from hornlab_search.targets import profile as _profile  # lazy: parallel-lane module

        mode = str(profile_raw.get("mode"))
        interpolation = str(profile_raw.get("interpolation") or "log_frequency")
        f0 = target["f0_hz"]
        f0_v = target["f0_v_hz"] if target["f0_v_hz"] is not None else f0
        band_lo = target["band_lo_hz"]
        band_hi = target["band_hi_hz"]

        anchors_h = _profile.parse_profile(
            profile_raw.get("h") if isinstance(profile_raw.get("h"), (list, tuple)) else [],
            "h", f0)
        anchors_v = _profile.parse_profile(
            profile_raw.get("v") if isinstance(profile_raw.get("v"), (list, tuple)) else [],
            "v", f0_v)
        onset_h = _profile.profile_onset_hz(anchors_h, f0)
        onset_v = _profile.profile_onset_hz(anchors_v, f0_v)

        lo = min(onset_h, onset_v)
        lo = band_lo if lo < band_lo else lo
        if lo >= band_hi:
            freqs = [float(band_hi)]
        else:
            steps = 32
            lo_l, hi_l = (0.0 if lo <= 0 else _log10c(lo)), _log10c(band_hi)
            freqs = [10.0 ** (lo_l + (hi_l - lo_l) * i / (steps - 1)) for i in range(steps)]
            freqs[0], freqs[-1] = float(lo), float(band_hi)
        # Emit and evaluate the SAME rounded grid, so a consumer interpolating from
        # ``freqs_hz`` reproduces the plotted profile arrays exactly.
        freqs = [round(f, 6) for f in freqs]

        def _plane(anchors, onset):
            pref, mn, mx = [], [], []
            for f in freqs:
                if f + 1e-9 < onset:
                    pref.append(None); mn.append(None); mx.append(None)
                    continue
                p, lo_v, hi_v = _profile.profile_value(anchors, float(f))
                pref.append(float(p))
                mn.append(None if lo_v is None else float(lo_v))
                mx.append(None if hi_v is None else float(hi_v))
            return pref, mn, mx

        h_pref, h_min, h_max = _plane(anchors_h, onset_h)
        v_pref, v_min, v_max = _plane(anchors_v, onset_v)
        return {
            "mode": mode,
            "interpolation": interpolation,
            "onset_h_hz": float(onset_h),
            "onset_v_hz": float(onset_v),
            "freqs_hz": freqs,
            "h_pref": h_pref, "h_min": h_min, "h_max": h_max,
            "v_pref": v_pref, "v_min": v_min, "v_max": v_max,
        }
    except Exception:  # noqa: BLE001
        return None


def _log10c(value: float) -> float:
    return float(np.log10(float(value))) if _np_isfinite(value) and value > 0 else 0.0


def _np_isfinite(value) -> bool:
    try:
        import math
        return math.isfinite(value)
    except (TypeError, ValueError):
        return False


def di_summary(raw_target: dict, weights: dict | None, version: int) -> dict | None:
    """Reconstruct the DI level/slope scoring truth for one objective version.

    Returns ``{"level_db", "level_source", "level_scored", "slope_db_per_dec",
    "slope_scored", "anchor_hz"}``:

    * ``level_source`` is ``"explicit"`` when ``target.di_target_db`` is set, else ``"cuts"``
      (v1) or ``"gaussian"`` (v2+), using ``hornlab_search.metrics.di``. v6 and v9 (amended RFC
      2026-11-17) score no DI level at all, so they return ``level_db = level_source = None``.
    * ``level_scored`` is true iff the ``di`` weight is non-zero and the version is neither 6
      nor 9.
    * ``slope_db_per_dec`` is ``target.di_slope_target`` (0.0 when absent).
    * ``slope_scored`` reads ``di_rise`` on v6 and ``dislope`` everywhere else.
    * ``anchor_hz`` is ``target.f0_hz`` (falling back to ``band_lo_hz``).

    ``weights`` may be ``None`` / partial: a missing key is treated as zero (briefs carry
    explicit weights). ``di`` gates the level; ``dislope`` / ``di_rise`` gate the slope.
    Malformed target (or unsupported version) returns ``None``. Never raises.
    """
    try:
        target = _target_view(raw_target)
        if target is None:
            return None
        v = _as_version(version)
        if v is None:
            return None

        h_deg = target["h_deg"]
        v_deg = target["v_deg"]
        explicit = target["di_target_db"]

        if v in (6, 9):
            # v6 and v9 (amended RFC 2026-11-17) score no DI level at all: v9's level truth is
            # the declared per-plane profile, and only the slope/slope-residual terms are scored.
            level_db = None
            level_source = None
        elif explicit is not None:
            level_db = float(explicit)
            level_source = "explicit"
        elif v == 1:
            level_db = float(di_from_cuts(h_deg, v_deg))
            level_source = "cuts"
        else:
            level_db = float(target_di_gaussian_db(h_deg, v_deg))
            level_source = "gaussian"

        level_scored = v not in (6, 9) and _weight(weights, "di") != 0.0
        if v == 6:
            slope_scored = _weight(weights, "di_rise") != 0.0
        else:
            slope_scored = _weight(weights, "dislope") != 0.0

        anchor = target["f0_hz"] if target["f0_hz"] is not None else target["band_lo_hz"]
        return {
            "level_db": level_db,
            "level_source": level_source,
            "level_scored": bool(level_scored),
            "slope_db_per_dec": float(target["di_slope_target"]),
            "slope_scored": bool(slope_scored),
            "anchor_hz": float(anchor),
        }
    except Exception:  # noqa: BLE001
        return None


def bw8k_floor(raw_target, raw_objective, version: int, freqs_hz, bw_h_deg, bw_v_deg) -> dict | None:
    """Reconstruct the v7-style one-sided 8 kHz beamwidth floor, exactly as the scorer samples it.

    Mirrors ``scalar_v7._bw8k_floor_penalty``: cap the frequency at ``min(8000, band_hi)``, take
    the last solved sample at or below the cap, and compare BOTH planes at that single frequency
    to ``bw8k_floor * coverage_*``. Only narrowing is charged.

    Returns ``{"floor_hz", "floor_h_deg", "floor_v_deg", "min_bw_h_deg", "min_bw_v_deg",
    "penalty_raw"}`` or ``None`` when the objective has no finite positive ``bw8k_floor``, the
    target/bw arrays are thin, no sample lies at or below the cap, or the sampled beamwidths are
    not finite.

    ``version`` is accepted for signature symmetry; the floor is a raw objective constant and
    applies to any version that carries it (today v5/v7/v8). Never raises.
    """
    try:
        obj = _as_mapping(raw_objective)
        ratio = _num(obj.get("bw8k_floor"), positive=True)
        if ratio is None:
            return None
        target = _target_view(raw_target)
        if target is None:
            return None

        f = np.asarray(freqs_hz, dtype=float).ravel()
        bw_h = np.asarray(bw_h_deg, dtype=float).ravel()
        bw_v = np.asarray(bw_v_deg, dtype=float).ravel()
        if f.size == 0 or bw_h.size != f.size or bw_v.size != f.size:
            return None

        cap = min(_BW8K_HZ, float(target["band_hi_hz"]))
        below = np.nonzero(f <= cap)[0]
        if below.size == 0:
            return None
        i = int(below[-1])

        min_bw_h = float(bw_h[i])
        min_bw_v = float(bw_v[i])
        if not (math.isfinite(min_bw_h) and math.isfinite(min_bw_v)):
            return None

        floor_h = ratio * float(target["h_deg"])
        floor_v = ratio * float(target["v_deg"])
        dh = max(0.0, floor_h - min_bw_h)
        dv = max(0.0, floor_v - min_bw_v)
        penalty = float((dh ** 2 + dv ** 2) / 100.0)
        return {
            "floor_hz": float(f[i]),
            "floor_h_deg": float(floor_h),
            "floor_v_deg": float(floor_v),
            "min_bw_h_deg": min_bw_h,
            "min_bw_v_deg": min_bw_v,
            "penalty_raw": penalty,
        }
    except Exception:  # noqa: BLE001
        return None


def diag_summary(raw_target, weights) -> dict | None:
    """Reconstruct the diagonal-reference truth: ``{"reference_deg", "scored"}``.

    ``reference_deg`` is ``(coverage_h_deg + coverage_v_deg) / 2`` (v4's round diagonal
    reference). ``scored`` reads the ``diag`` weight; missing weights count as zero. Malformed
    target returns ``None``. Never raises.
    """
    try:
        target = _target_view(raw_target)
        if target is None:
            return None
        return {
            "reference_deg": float(0.5 * (target["h_deg"] + target["v_deg"])),
            "scored": bool(_weight(weights, "diag") != 0.0),
        }
    except Exception:  # noqa: BLE001
        return None


def measured_di_slope(freqs_hz, di_db, score_lo_hz) -> float | None:
    """``polyfit(log10 f, DI, 1)[0]`` over ``f >= score_lo_hz``, or ``None``.

    Callers pass band-limited arrays (``[band_lo, band_hi]``): only the scored lower onset
    ``score_lo_hz`` is applied here. Non-finite frequencies/levels are dropped; fewer than two
    usable points (or a degenerate log-frequency axis) returns ``None``. Never raises.
    """
    try:
        f = np.asarray(freqs_hz, dtype=float).ravel()
        d = np.asarray(di_db, dtype=float).ravel()
        if f.size != d.size:
            return None
        lower = _num(score_lo_hz)
        ok = np.isfinite(f) & np.isfinite(d) & (f > 0.0)
        if lower is not None:
            ok &= f >= lower
        if int(ok.sum()) < 2:
            return None
        x = np.log10(f[ok])
        if float(np.ptp(x)) == 0.0:
            return None
        slope = float(np.polyfit(x, d[ok], 1)[0])
        return slope if math.isfinite(slope) else None
    except Exception:  # noqa: BLE001
        return None


def build_scoring_view(raw_target, raw_objective, weights, version: int, *,
                       design_scalars=None, design_params=None,
                       freqs_hz=None, bw_h_deg=None, bw_v_deg=None,
                       di_db=None) -> dict | None:
    """Assemble the complete display-truth payload for one objective version.

    Returns::

        {
          "objective_version": int,
          "coverage": score_window(...),          # None when unbuildable
          "di": di_summary(...),                  # None when unbuildable
          "bw8k_floor": bw8k_floor(...) | None,
          "diag": diag_summary(...) | None,
          "notes": {...},                         # three fixed display caveats
          "profile": {...},                       # v9 only (amendment 2026-11-17):
                                                  # mode/interpolation/onsets + the shared
                                                  # 32-point log grid with per-plane
                                                  # pref/min/max arrays (None below each
                                                  # plane's own onset; min/max None in
                                                  # target mode). Pop-when-unbuildable —
                                                  # pre-v9 targets carry no key at all.
        }

    ``di_db`` is accepted for API symmetry; the measured slope is exposed by
    :func:`measured_di_slope` and is deliberately NOT part of this pinned payload. An unsupported
    ``version`` (or any unbuildable assembly) returns ``None``; malformed sub-inputs leave the
    corresponding sub-dict ``None``. Never raises.
    """
    try:
        v = _as_version(version)
        if v is None:
            return None
        out = {
            "objective_version": v,
            "coverage": score_window(
                raw_target, raw_objective, v,
                design_scalars=design_scalars, design_params=design_params,
            ),
            "di": di_summary(raw_target, weights, v),
            "bw8k_floor": bw8k_floor(
                raw_target, raw_objective, v, freqs_hz, bw_h_deg, bw_v_deg,
            ),
            "diag": diag_summary(raw_target, weights),
            "notes": dict(_NOTES),
        }
        # v9 (2026-11-17 amendment): the coverage-profile display block. Pop-when-unbuildable:
        # a pre-v9 target carries no "profile" key at all, so existing payloads stay identical.
        profile_block = _profile_view(raw_target)
        if profile_block is not None and v == 9:
            out["profile"] = profile_block
        return out
    except Exception:  # noqa: BLE001
        return None
