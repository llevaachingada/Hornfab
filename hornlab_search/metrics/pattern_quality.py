"""Report-only physically meaningful pattern-quality diagnostics (WP2, 2026-11-17).

This module is a **diagnostic layer**, not a scorer.  It reuses the frozen definitions that
already exist in :mod:`hornlab_search.metrics`:

* ``metrics.polar.beamwidth_deg`` - the legacy **outermost** on-axis-referenced -6.0206 dB
  crossing pair.  Recomputed here only for comparability and labelled as the legacy definition.
  The legacy 180-degree sentinel is never reported as a measured width.
* ``metrics.acoustic_v2.main_lobe`` / ``sphere_weights`` / ``balloon_lobes`` - the existing
  **boresight-connected** first-crossing width, censored-status convention and the canonical
  theta-trapezoid x sin(theta) x uniform-phi sphere quadrature / connected-lobe map.
* ``metrics.di.di_from_balloon`` + ``metrics.di.sin_theta_weights`` - the canonical scoring-path
  spherical DI with sin(theta) solid-angle weighting.  A balloon with no stored ``balloon_grid``
  is a typed refusal: DI is never silently recomputed with equal-area weights.
* The H12 off-axis excess threshold is read from ``objective.scalar_v7`` (single source), not
  duplicated.  No objective term, weight or default penalty is added here.

Every metric is reported per frequency, separately for the H and V cuts, and - where a usable
full balloon exists - on the sphere.  A censored or unmeasurable quantity is reported as
``None`` with an explicit ``status``; it is never silently converted to 180 or 0 degrees.

Pure functions over angle-degree / dB arrays (numpy only).  No solver, mesher or file I/O.
"""
from __future__ import annotations

import numpy as np

from .acoustic_v2 import balloon_lobes, main_lobe
from .di import di_from_balloon, sin_theta_weights
from .polar import _threshold_db, beamwidth_deg, normalized_db

METHOD_VERSION = "pattern_quality.v1"

#: The legacy scalar reports this sentinel for "no crossing"; we keep it only under a key that
#: says it is a sentinel, never as the measurement.
LEGACY_SENTINEL_DEG = 180.0

#: Definition labels are part of the report contract (read by tests and the evidence doc).
LEGACY_DEFINITION = "legacy_outermost_onaxis_minus6"
CONNECTED_DEFINITION = "boresight_connected_first_crossing"

#: Diagnostic flag thresholds for an off-axis level ABOVE the boresight (dB re on-axis).
#: Flags are report-only: they are never weighted into J or any objective.
OA_ISLAND_WARN_DB = 0.5
OA_ISLAND_ANOMALOUS_DB = 1.0

#: A structured balloon must have at least this many theta/phi samples to support the coarse
#: lobe map.  The 512-point solver balloon is (16, 32) and clears this.  Finer features than one
#: grid cell are never claimed.
MIN_BALLOON_THETA = 4
MIN_BALLOON_PHI = 6
MIN_BALLOON_POINTS = 24

_ANGLE_TOL = 1e-9


class PatternQualityInputError(ValueError):
    """The cut/balloon arrays are structurally unusable (corrupt data, no 0-degree sample)."""


class BalloonUnavailableError(PatternQualityInputError):
    """A full balloon is missing, malformed, or has no boresight sample."""


class BalloonTooSparseError(BalloonUnavailableError):
    """A balloon exists but is too sparse to support the requested spherical diagnostics."""


class BalloonGridUnavailableError(BalloonUnavailableError):
    """A stored balloon has no ``balloon_grid`` meta, so the weighting is not defined.

    The canonical scoring path weights a structured theta-phi balloon by sin(theta).  Falling
    back to equal-area weights would change the DI silently, so this is a typed refusal.
    """


def h12_offaxis_excess_threshold_db() -> float:
    """The H12 off-axis-excess threshold, read from its single source.

    ``objective.scalar_v7._OA_EXCESS_THRESHOLD_DB`` is the existing opt-in H12 definition
    (``mean(max(0, SPL(theta) - SPL(0) - threshold))``).  The import is lazy so this diagnostic
    module never creates a metrics -> objective import cycle at import time.
    """
    from ..objective.scalar_v7 import _OA_EXCESS_THRESHOLD_DB  # noqa: PLC0415 - lazy by design

    return float(_OA_EXCESS_THRESHOLD_DB)


# --------------------------------------------------------------------------- input validation


def _validate_cut(angles_deg, spl_db) -> tuple[np.ndarray, np.ndarray, int]:
    """Strict cut validation shared by every cut diagnostic.

    The contract requires a strictly ascending angle array with exactly one 0-degree sample.
    Corrupt angles raise :class:`PatternQualityInputError`; a corrupt/non-finite SPL array is
    handled later (a non-finite on-axis level is "unmeasurable", not a number).
    """
    a = np.asarray(angles_deg, dtype=float)
    s = np.asarray(spl_db, dtype=float)
    if a.ndim != 1 or s.shape != a.shape:
        raise PatternQualityInputError(
            f"angles {a.shape} and spl {s.shape} must be equal 1-D arrays")
    if a.size < 2:
        raise PatternQualityInputError("need at least two angle samples")
    if not np.all(np.isfinite(a)):
        raise PatternQualityInputError("angles contain non-finite values")
    if np.any(np.diff(a) <= 0.0):
        raise PatternQualityInputError("angles must be strictly ascending")
    zero = np.flatnonzero(np.abs(a) < _ANGLE_TOL)
    if zero.size != 1:
        raise PatternQualityInputError(
            f"need exactly one exact 0-degree sample, found {zero.size}")
    return a, s, int(zero[0])


# --------------------------------------------------------------------------- legacy width


def legacy_outermost_width(angles_deg, spl_db, drop_db: float = 6.0) -> dict:
    """The untouched legacy outermost -drop_db width, H/V cut.

    Delegates to :func:`metrics.polar.beamwidth_deg`.  Returns the scalar only when it is a real
    measurement; ``n_crossings == 0`` (including a dead on-axis sample) is reported as
    ``status == "censored"`` or ``"unmeasurable"`` with ``width_deg = None``.  The legacy
    180-degree sentinel is preserved under ``legacy_sentinel_deg`` for audit, never as width.
    """
    a, s, i0 = _validate_cut(angles_deg, spl_db)
    width, n_crossings = beamwidth_deg(a, s, drop_db)
    if not np.isfinite(s[i0]):
        return {
            "definition": LEGACY_DEFINITION,
            "drop_db": float(drop_db),
            "width_deg": None,
            "status": "unmeasurable",
            "n_crossings": int(n_crossings),
            "one_sided": False,
            "legacy_sentinel_deg": float(width),
            "note": "non-finite on-axis level; the legacy 180-degree sentinel is not a width",
        }
    if n_crossings == 0:
        return {
            "definition": LEGACY_DEFINITION,
            "drop_db": float(drop_db),
            "width_deg": None,
            "status": "censored",
            "n_crossings": 0,
            "one_sided": False,
            "legacy_sentinel_deg": float(width),
            "note": "no threshold crossing in the sampled range; 180 degrees is a sentinel",
        }
    return {
        "definition": LEGACY_DEFINITION,
        "drop_db": float(drop_db),
        "width_deg": float(width),
        "status": "valid_one_sided" if n_crossings == 1 else "valid",
        "n_crossings": int(n_crossings),
        "one_sided": bool(n_crossings == 1),
        "legacy_sentinel_deg": None,
        "note": ("one crossing: the other edge is the angle-grid edge, as in beamwidth_deg"
                 if n_crossings == 1 else ""),
    }


# --------------------------------------------------------------------------- connected width


def _left_edge(a: np.ndarray, d: np.ndarray, thr: float, i: int) -> tuple[float, bool]:
    """Interpolated threshold edge at the start of an above-threshold run, walking left."""
    if i == 0:
        return float(a[0]), True
    t = (thr - d[i - 1]) / (d[i] - d[i - 1])
    return float(a[i - 1] + t * (a[i] - a[i - 1])), False


def _right_edge(a: np.ndarray, d: np.ndarray, thr: float, j: int) -> tuple[float, bool]:
    """Interpolated threshold edge at the end of an above-threshold run, walking right."""
    if j == a.size - 1:
        return float(a[-1]), True
    t = (thr - d[j]) / (d[j + 1] - d[j])
    return float(a[j] + t * (a[j + 1] - a[j])), False


def _island_runs(a: np.ndarray, d: np.ndarray, thr: float,
                 center_lo: int, center_hi: int) -> list[dict]:
    """Disconnected above-threshold runs OUTSIDE the boresight-connected centre run."""
    islands: list[dict] = []
    n = a.size
    i = 0
    while i < n:
        if center_lo <= i <= center_hi:
            i = center_hi + 1
            continue
        if d[i] >= thr:
            j = i
            while j + 1 < n and d[j + 1] >= thr:
                j += 1
            left, left_limited = _left_edge(a, d, thr, i)
            right, right_limited = _right_edge(a, d, thr, j)
            islands.append({
                "start_deg": float(a[i]),
                "end_deg": float(a[j]),
                "extent_deg": float(right - left),
                "peak_db": float(np.max(d[i:j + 1])),
                "edge_limited": bool(left_limited or right_limited),
            })
            i = j + 1
        else:
            i += 1
    return islands


def connected_main_lobe(angles_deg, spl_db, drop_db: float = 6.0) -> dict:
    """The boresight-connected -drop_db interval and its disconnected islands.

    The width is the interval containing theta=0, ending at the **first** threshold crossing on
    each side (reusing ``metrics.acoustic_v2.main_lobe``).  A detached side lobe therefore cannot
    widen it.  A censored side has ``lower_edge_deg`` / ``upper_edge_deg`` of ``None``; the grid
    edge is exposed separately as a labelled lower bound, never as a crossing.

    ``island_count`` is the number of disconnected above-threshold runs in the cut, with their
    interpolated angular extents.  ``n_threshold_transitions`` counts every crossing in the cut;
    ``n_reentries`` counts the islands (each is a re-entry above threshold).

    ``censored_legacy_width_deg`` records the legacy main-lobe WIDTH (a censored cell's grid
    extent), never a "lower bound": a bound is reported separately as ``lower_bound_deg`` /
    ``upper_bound_deg`` with an explicit grid-edge status.
    """
    a, s, i0 = _validate_cut(angles_deg, spl_db)
    if not np.isfinite(s[i0]):
        return {
            "definition": CONNECTED_DEFINITION,
            "drop_db": float(drop_db),
            "width_deg": None,
            "status": "unmeasurable",
            "lower_edge_deg": None,
            "upper_edge_deg": None,
            "lower_edge_status": "unmeasurable",
            "upper_edge_status": "unmeasurable",
            "lower_bound_deg": None,
            "upper_bound_deg": None,
            "censored_legacy_width_deg": None,
            "island_count": None,
            "island_extents_deg": [],
            "island_total_extent_deg": None,
            "islands": [],
            "n_threshold_transitions": None,
            "n_reentries": None,
            "note": "non-finite on-axis level; no connected width exists",
        }

    base = main_lobe(a, s, drop_db)
    d = normalized_db(s, s[i0])
    thr = _threshold_db(drop_db)
    above = d >= thr

    center_lo = i0
    while center_lo - 1 >= 0 and above[center_lo - 1]:
        center_lo -= 1
    center_hi = i0
    while center_hi + 1 < a.size and above[center_hi + 1]:
        center_hi += 1

    islands = _island_runs(a, d, thr, center_lo, center_hi)
    lower_status = str(base["left_status"])
    upper_status = str(base["right_status"])
    lower_bound = -float(base["left_deg"])
    upper_bound = float(base["right_deg"])
    censored = lower_status != "valid" or upper_status != "valid"

    transitions = int(np.count_nonzero(above[:-1] != above[1:]))
    out = {
        "definition": CONNECTED_DEFINITION,
        "drop_db": float(drop_db),
        "width_deg": None if censored else float(base["width_deg"]),
        "status": "censored" if censored else "valid",
        "lower_edge_deg": None if lower_status != "valid" else lower_bound,
        "upper_edge_deg": None if upper_status != "valid" else upper_bound,
        "lower_edge_status": lower_status,
        "upper_edge_status": upper_status,
        "lower_bound_deg": lower_bound,
        "upper_bound_deg": upper_bound,
        # A censored connected width stores the grid-edge WIDTH, not a bound.  The key says so.
        "censored_legacy_width_deg": float(base["width_deg"]) if censored else None,
        "island_count": int(len(islands)),
        "island_extents_deg": [float(v["extent_deg"]) for v in islands],
        "island_total_extent_deg": float(sum(v["extent_deg"] for v in islands)),
        "islands": islands,
        "n_threshold_transitions": transitions,
        "n_reentries": int(len(islands)),
        "note": ("censored: a grid edge is a lower bound, not an exact edge"
                 if censored else ""),
    }
    return out


# --------------------------------------------------------------------------- off-axis excess


def off_axis_excess(angles_deg, spl_db, *, threshold_db: float | None = None,
                    coverage_deg: float | None = None) -> dict:
    """Positive off-axis excess relative to the boresight sample of one cut.

    The definition is H12-compatible: for every finite off-axis sample,
    ``max(0, SPL(theta) - SPL(0) - threshold)``.  The threshold defaults to the existing H12
    value (see :func:`h12_offaxis_excess_threshold_db`).  Reports the largest signed off-axis
    level and its angle, the largest excess, and the mean excess over the **whole cut** and,
    when ``coverage_deg`` is given, over the samples inside ``+/- coverage_deg / 2``.
    """
    a, s, i0 = _validate_cut(angles_deg, spl_db)
    thr = h12_offaxis_excess_threshold_db() if threshold_db is None else float(threshold_db)
    cov = None if coverage_deg is None else float(coverage_deg)

    if not np.isfinite(s[i0]):
        return {
            "status": "unmeasurable",
            "threshold_db": thr,
            "coverage_deg": cov,
            "max_offaxis_db": None,
            "max_offaxis_angle_deg": None,
            "max_excess_db": None,
            "mean_excess_db": None,
            "mean_excess_in_coverage_db": None,
            "n_offaxis_samples": 0,
            "n_in_coverage_samples": 0,
            "note": "non-finite on-axis reference",
        }

    off = np.abs(a) > _ANGLE_TOL
    finite = off & np.isfinite(s)
    if not finite.any():
        return {
            "status": "unmeasurable",
            "threshold_db": thr,
            "coverage_deg": cov,
            "max_offaxis_db": None,
            "max_offaxis_angle_deg": None,
            "max_excess_db": None,
            "mean_excess_db": None,
            "mean_excess_in_coverage_db": None,
            "n_offaxis_samples": 0,
            "n_in_coverage_samples": 0,
            "note": "no finite off-axis samples",
        }

    delta = s[finite] - float(s[i0])
    off_angles = a[finite]
    k = int(np.argmax(delta))
    max_level = float(delta[k])
    excess = np.maximum(0.0, delta - thr)

    in_cov = np.abs(off_angles) <= 0.5 * cov + _ANGLE_TOL if cov is not None else None
    if in_cov is not None and in_cov.any():
        mean_cov = float(np.mean(excess[in_cov]))
        n_cov = int(in_cov.sum())
    else:
        mean_cov = None
        n_cov = 0

    return {
        "status": "valid",
        "threshold_db": thr,
        "coverage_deg": cov,
        "max_offaxis_db": max_level,
        "max_offaxis_angle_deg": float(off_angles[k]),
        "max_excess_db": float(excess.max()),
        "mean_excess_db": float(np.mean(excess)),
        "mean_excess_in_coverage_db": mean_cov,
        "n_offaxis_samples": int(finite.sum()),
        "n_in_coverage_samples": n_cov,
        "note": "excess is dB re the 0-degree sample; H12-compatible threshold",
    }


# --------------------------------------------------------------------------- flags


def pattern_quality_flags(cut: dict) -> list[str]:
    """Diagnostic flags for one cut report.  Report-only: never weighted into J.

    Thresholds are the WP2 diagnostic ones (>+0.5 dB and >+1.0 dB off axis), plus a detached-island
    note and a legacy-width-inflation note.  They are not pass/fail physics standards.
    """
    flags: list[str] = []
    off = cut.get("off_axis") or {}
    level = off.get("max_offaxis_db")
    if level is not None:
        if float(level) > OA_ISLAND_ANOMALOUS_DB:
            flags.append("off_axis_peak_gt_1p0_db")
        if float(level) > OA_ISLAND_WARN_DB:
            flags.append("off_axis_peak_gt_0p5_db")
    conn = cut.get("connected") or {}
    if conn.get("island_count"):
        flags.append("disconnected_above_threshold_islands")
    legacy = cut.get("legacy") or {}
    if (conn.get("width_deg") is not None and legacy.get("width_deg") is not None
            and float(legacy["width_deg"]) > float(conn["width_deg"]) + _ANGLE_TOL
            and conn.get("island_count")):
        flags.append("legacy_width_inflated_by_islands")
    return flags


def cut_pattern_quality(angles_deg, spl_db, drop_db: float = 6.0, *,
                        coverage_deg: float | None = None,
                        oa_threshold_db: float | None = None) -> dict:
    """All per-cut diagnostics for one frequency and one plane.

    Returns ``legacy``, ``connected``, ``off_axis`` and the union ``pattern_quality_flags``.
    """
    legacy = legacy_outermost_width(angles_deg, spl_db, drop_db)
    connected = connected_main_lobe(angles_deg, spl_db, drop_db)
    off = off_axis_excess(angles_deg, spl_db, threshold_db=oa_threshold_db,
                          coverage_deg=coverage_deg)
    out = {
        "legacy": legacy,
        "connected": connected,
        "off_axis": off,
        "drop_db": float(drop_db),
        "pattern_quality_flags": [],
    }
    out["pattern_quality_flags"] = pattern_quality_flags(out)
    return out


# --------------------------------------------------------------------------- balloon


def _validate_balloon(spl_balloon_db, balloon_dirs, grid) -> tuple[np.ndarray, np.ndarray,
                                                                    np.ndarray, tuple[int, int] | None]:
    """Validate a full balloon and return ``(spl_2d, dirs, theta_deg, grid_or_None)``.

    ``grid`` is ``[n_theta, n_phi]`` from ``Response.meta['balloon_grid']``; ``None`` means the
    weighting is undefined (e.g. an equal-area set), so DI and the structured lobe map refuse
    rather than silently switching quadrature.  A balloon with no theta=0 boresight sample is
    refused: every DI here is referenced to it.
    """
    b = np.asarray(spl_balloon_db, dtype=float)
    if b.ndim == 1:
        b = b[None, :]
    if b.ndim != 2:
        raise BalloonUnavailableError(f"balloon levels must be 1-D or 2-D, got {b.shape}")
    d = np.asarray(balloon_dirs, dtype=float)
    if d.ndim != 2 or d.shape[1] != 3:
        raise BalloonUnavailableError(f"balloon directions must be (n, 3), got {d.shape}")
    if b.shape[1] != d.shape[0]:
        raise BalloonUnavailableError(
            f"balloon levels {b.shape} do not match directions {d.shape}")
    if not np.all(np.isfinite(d)):
        raise BalloonUnavailableError("balloon directions contain non-finite values")

    z = np.clip(d[:, 2], -1.0, 1.0)
    theta = np.degrees(np.arccos(z))
    if not np.any(np.abs(theta) < _ANGLE_TOL):
        raise BalloonUnavailableError("balloon has no theta=0 boresight sample")

    grid_out = None
    if grid is not None:
        try:
            n_t, n_p = int(grid[0]), int(grid[1])
        except (TypeError, ValueError, IndexError) as exc:
            raise BalloonUnavailableError(f"invalid balloon_grid {grid!r}") from exc
        if n_t * n_p != d.shape[0]:
            raise BalloonUnavailableError(
                f"balloon_grid {n_t}x{n_p} = {n_t * n_p} does not match {d.shape[0]} samples")
        if n_t < MIN_BALLOON_THETA or n_p < MIN_BALLOON_PHI or d.shape[0] < MIN_BALLOON_POINTS:
            raise BalloonTooSparseError(
                f"balloon grid {n_t}x{n_p} ({d.shape[0]} samples) is too sparse for the "
                f"coarse lobe map (need >= {MIN_BALLOON_THETA}x{MIN_BALLOON_PHI} and "
                f">= {MIN_BALLOON_POINTS} samples)")
        grid_out = (n_t, n_p)
    return b, d, theta, grid_out


def balloon_directivity(spl_balloon_db_row, balloon_dirs, *,
                        grid=None, axis_db: float | None = None) -> dict:
    """Spherical DI for ONE frequency from a stored balloon.

    Uses the canonical scoring-path weighting: ``di_from_balloon`` with
    ``sin_theta_weights(theta)`` on a structured theta-phi grid.  A missing ``balloon_grid`` is
    refused (:class:`BalloonGridUnavailableError`) rather than silently falling back to
    equal-area weights, so a stored DI comparison can never change its weighting by accident.
    The axis reference defaults to the theta=0 balloon sample; callers replaying a stored response
    should pass the same on-axis cut level the scorer used.

    A dead pattern is ``status == "unmeasurable"`` with ``di_db = None``; an omnidirectional
    pattern correctly reads ``di_db == 0.0``.
    """
    b, _d, theta, grid_out = _validate_balloon(
        np.asarray(spl_balloon_db_row, dtype=float), balloon_dirs, grid)
    if grid_out is None:
        raise BalloonGridUnavailableError(
            "no balloon_grid in response meta: the sin(theta) weighting of the stored response "
            "is unknown, so DI is refused rather than recomputed with equal-area weights")
    row = b[0]
    if axis_db is None:
        axis = float(row[int(np.argmax(np.asarray(balloon_dirs, dtype=float)[:, 2]))])
    else:
        axis = float(axis_db)
    if not np.isfinite(axis) or not np.isfinite(row).any():
        return {
            "status": "unmeasurable",
            "di_db": None,
            "weighting": None,
            "axis_db": None if not np.isfinite(axis) else axis,
            "n_samples": int(row.size),
            "note": "non-finite on-axis reference or no finite balloon samples",
        }
    weights = sin_theta_weights(theta)
    di = di_from_balloon(row, axis, weights=weights)
    return {
        "status": "valid",
        "di_db": float(di),
        "weighting": "sin_theta",
        "axis_db": axis,
        "n_samples": int(row.size),
        "note": "",
    }


def balloon_lobe_map(spl_balloon_db, balloon_dirs, grid) -> dict:
    """Coarse connected-lobe map on a structured theta-phi balloon.

    Reuses ``metrics.acoustic_v2.balloon_lobes`` (same canonical quadrature and the same flood-fill
    connected main region).  The returned ``resolution_deg`` is the grid spacing; features finer
    than one cell are **not** resolved and the ``sampling_density_warning`` says so.
    """
    b, d, _theta, grid_out = _validate_balloon(spl_balloon_db, balloon_dirs, grid)
    if grid_out is None:
        raise BalloonGridUnavailableError(
            "no balloon_grid in response meta: a structured theta-phi grid is required for a "
            "lobe map")
    n_t, n_p = grid_out
    lobes = balloon_lobes(b, grid_out)
    d_theta = 180.0 / float(n_t - 1) if n_t > 1 else None
    d_phi = 360.0 / float(n_p)
    return {
        "status": "valid",
        "grid": [int(n_t), int(n_p)],
        "resolution_deg": [d_theta, float(d_phi)],
        "sampling_density_warning": (
            f"coarse balloon map: grid {n_t}x{n_p} gives about "
            f"{d_theta:.2f} deg theta x {d_phi:.2f} deg phi; angular features finer than one "
            "grid cell are not resolved and are never claimed."),
        "lobe_map": lobes,
    }


# --------------------------------------------------------------------------- response assembly


def _balloon_block(freqs: np.ndarray, axis_levels: np.ndarray,
                   balloon_dirs, spl_balloon_db, grid) -> tuple[dict, list[dict]]:
    """Per-frequency balloon results, or a typed refusal block."""
    try:
        b, dirs, _theta, grid_out = _validate_balloon(spl_balloon_db, balloon_dirs, grid)
        if grid_out is None:
            raise BalloonGridUnavailableError(
                "no balloon_grid in response meta: stored DI would need an assumed weighting; "
                "refusing rather than silently switching to equal-area weights")
        di_rows = [
            balloon_directivity(b[i], dirs, grid=grid_out,
                                axis_db=float(axis_levels[i]))
            for i in range(b.shape[0])
        ]
        lobe_block = balloon_lobe_map(b, dirs, grid_out)
        # Diagonal coverage overlay (reuses metrics.diagonal's first-crossing definition).
        from .diagonal import MAX_POLAR_DEG, diagonal_beamwidths_deg  # noqa: PLC0415

        # diagonal_beamwidths_deg reports a no-crossing ray as 2*MAX_POLAR_DEG; that is a
        # censored lower bound, not a measured diagonal.  Do not present it as a number.
        diag_saturated = 2.0 * float(MAX_POLAR_DEG)

        def _diag_plane(value):
            if not np.isfinite(value):
                return None, "unmeasurable"
            if float(value) >= diag_saturated - 1e-9:
                return None, "censored"          # 2*MAX_POLAR_DEG is a lower bound
            return float(value), "valid"

        diag_rows = []
        for i in range(b.shape[0]):
            bw45, bw135 = diagonal_beamwidths_deg(
                dirs, b[i], on_axis_db=float(axis_levels[i]))
            v45, st45 = _diag_plane(bw45)
            v135, st135 = _diag_plane(bw135)
            if st45 == "valid" and st135 == "valid":
                overall = "valid"
            elif st45 == "unmeasurable" and st135 == "unmeasurable":
                overall = "unmeasurable"
            else:
                overall = "partial"
            diag_rows.append({
                "diagonal_bw45_deg": v45,
                "diagonal_bw45_status": st45,
                "diagonal_bw135_deg": v135,
                "diagonal_bw135_status": st135,
                "status": overall,
                "censored_floor_deg": diag_saturated
                if (v45 is None or v135 is None) else None,
            })

        per_freq = []
        for i in range(b.shape[0]):
            lobes = None
            if lobe_block is not None:
                lm = lobe_block["lobe_map"]
                lobes = {k: (lm[k][i] if isinstance(lm[k], list) else lm[k])
                         for k in ("outside_peak_db", "outside_peak_theta_deg",
                                   "outside_peak_phi_deg", "island_count",
                                   "outside_power_fraction", "max_above_axis_db",
                                   "main_solid_angle_sr")}
            balloon_flags = []
            if lobes is not None and lobes.get("max_above_axis_db") is not None:
                hot = float(lobes["max_above_axis_db"])
                if hot > OA_ISLAND_ANOMALOUS_DB:
                    balloon_flags.append("balloon_hotspot_gt_1p0_db")
                if hot > OA_ISLAND_WARN_DB:
                    balloon_flags.append("balloon_hotspot_gt_0p5_db")
            per_freq.append({
                **di_rows[i],
                "lobe_map": lobes,
                "diagonal": diag_rows[i],
                "pattern_quality_flags": balloon_flags,
            })
        meta = {
            "status": "valid",
            "weighting": di_rows[0]["weighting"] if di_rows else None,
            "grid": [int(grid_out[0]), int(grid_out[1])],
            "resolution_deg": lobe_block["resolution_deg"],
            "sampling_density_warning": lobe_block["sampling_density_warning"],
            "note": "",
        }
        return meta, per_freq
    except BalloonUnavailableError as exc:
        meta = {
            "status": "refused",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "weighting": None,
            "grid": None,
            "resolution_deg": None,
            "sampling_density_warning": None,
            "note": "balloon diagnostics refused; no spherical values were invented",
        }
        per_freq = [{
            "status": "refused",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "di_db": None,
            "weighting": None,
            "n_samples": 0,
            "lobe_map": None,
            "diagonal": {"diagonal_bw45_deg": None, "diagonal_bw135_deg": None,
                         "status": "refused"},
            "pattern_quality_flags": [],
        } for _ in range(freqs.size)]
        return meta, per_freq


def pattern_quality_from_response(resp, *, coverage_h_deg: float | None = None,
                                  coverage_v_deg: float | None = None,
                                  drop_db: float = 6.0) -> dict:
    """Assemble the per-frequency report for one stored ``Response`` (read-only).

    Only the arrays already on the response are read.  The legacy and connected cut metrics always
    run; the spherical block is either ``valid`` or a typed ``refused`` with no invented numbers.
    """
    freqs = np.asarray(resp.freqs_hz, dtype=float)
    ha = np.asarray(resp.h_angles_deg, dtype=float)
    va = np.asarray(resp.v_angles_deg, dtype=float)
    sh = np.asarray(resp.spl_h_db, dtype=float)
    sv = np.asarray(resp.spl_v_db, dtype=float)
    if sh.ndim != 2 or sh.shape[0] != freqs.size or sh.shape[1] != ha.size:
        raise PatternQualityInputError(f"spl_h_db shape {sh.shape} does not match the H cut")
    if sv.ndim != 2 or sv.shape[0] != freqs.size or sv.shape[1] != va.size:
        raise PatternQualityInputError(f"spl_v_db shape {sv.shape} does not match the V cut")

    zero = np.flatnonzero(np.abs(ha) < _ANGLE_TOL)
    if zero.size != 1:
        raise PatternQualityInputError(
            f"H cut needs exactly one exact 0-degree sample, found {zero.size}")
    axis = int(zero[0])
    axis_levels = sh[:, axis]

    has_balloon = (getattr(resp, "spl_balloon_db", None) is not None
                   and getattr(resp, "balloon_dirs", None) is not None)
    meta = getattr(resp, "meta", {}) or {}
    if has_balloon:
        balloon_meta, balloon_rows = _balloon_block(
            freqs, axis_levels, resp.balloon_dirs, resp.spl_balloon_db,
            meta.get("balloon_grid"))
    else:
        balloon_meta = {
            "status": "unavailable",
            "error_type": "BalloonUnavailableError",
            "error": "response carries no spl_balloon_db/balloon_dirs",
            "weighting": None,
            "grid": None,
            "resolution_deg": None,
            "sampling_density_warning": None,
            "note": "no balloon: spherical DI and the 3-D lobe map are unavailable",
        }
        balloon_rows = [{
            "status": "unavailable",
            "error_type": "BalloonUnavailableError",
            "error": "response carries no balloon",
            "di_db": None,
            "weighting": None,
            "n_samples": 0,
            "lobe_map": None,
            "diagonal": {"diagonal_bw45_deg": None, "diagonal_bw135_deg": None,
                         "status": "unavailable"},
            "pattern_quality_flags": [],
        } for _ in range(freqs.size)]

    rows = []
    for i, f in enumerate(freqs):
        h = cut_pattern_quality(ha, sh[i], drop_db, coverage_deg=coverage_h_deg)
        v = cut_pattern_quality(va, sv[i], drop_db, coverage_deg=coverage_v_deg)
        flags = sorted(set(h["pattern_quality_flags"]) | set(v["pattern_quality_flags"])
                       | set(balloon_rows[i].get("pattern_quality_flags") or []))
        rows.append({
            "freq_hz": float(f),
            "H": h,
            "V": v,
            "balloon": balloon_rows[i],
            "pattern_quality_flags": flags,
        })

    return {
        "schema": "pattern_quality.v1",
        "method": METHOD_VERSION,
        "definitions": {
            "legacy": LEGACY_DEFINITION,
            "connected": CONNECTED_DEFINITION,
            "drop_db": float(drop_db),
            "note": ("legacy = outermost crossings (frozen polar.beamwidth_deg); "
                     "connected = first crossing each side from boresight (acoustic_v2.main_lobe)"),
        },
        "freqs_hz": [float(f) for f in freqs],
        "balloon": balloon_meta,
        "per_frequency": rows,
    }
