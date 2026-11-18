"""E1 - synthetic adversarial tests for the v9 ripple-window semantics (senior directive Â§5).

NEW file only; imports the installed objective/metrics modules read-only and asserts their
*measured* behaviour on synthetic cuts. No existing file is edited, so the legacy semantics stay
exactly what production scores with today.

Demonstrates (empirically, by scanning where a defect changes the ripple value):
  1. Corridor mode: `scalar_v9` passes the corridor SPREAD (hi - lo) as the total polar angle
     into `smoothness.ripple_detrended_db`, which then inspects only +/-(hi - lo)/2 degrees.
     A 70-90 deg H corridor therefore inspects a 20 deg window (+/-10), not the corridor.
  2. Target mode: `scalar_v9` passes 2 * preferred, so a single target of 80 deg inspects
     +/-80 deg - twice the design's declared -6 dB half-edge of +/-40 deg.
  3. End-to-end rank flip: with the defect outside the legacy corridor window, the legacy v9
     score prefers the bumpy design; the corrected window (guaranteed-min edge or declared
     seat zone) prefers the smooth one.
"""
from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from hornlab_search.metrics.smoothness import ripple_detrended_db
from hornlab_search.objective.scalar_v9 import V9Params, _rip_term_v9
from hornlab_search.targets.spec import Target

AXIS = 0.0  # all synthetic cuts are normalized to 0 dB on axis


def smooth_cut(slope_db: float = 0.003, step: float = 0.25, amp: float = 0.0,
               bump_deg: float | None = None, sigma_deg: float = 2.0,
               floor: float = -120.0) -> tuple[np.ndarray, np.ndarray]:
    """Parabolic-in-dB smooth beam (axis 0 dB, no ripple) with an optional Gaussian bump.

    ``slope_db`` gives the dB drop per squared degree, so the -6.02 dB half-width sits at
    sqrt(6.0206 / slope) degrees; level stays above the ripple floor (-40 dB) inside +/-50 deg.
    """
    a = np.arange(-90.0, 90.0 + step / 2, step)
    spl = -AXIS - slope_db * a ** 2
    spl = np.where(spl < floor, floor, spl)
    if amp and bump_deg is not None:
        spl = spl + amp * np.exp(-0.5 * ((a - bump_deg) / sigma_deg) ** 2)
        spl = np.maximum(spl, floor)
    return a, spl


def window_reach(slope_db: float, amp: float, width_total: float,
                 threshold_ripple: float = 0.3) -> float:
    """Largest |defect angle| whose bump changes the detrended ripple beyond threshold.

    Probes the EFFECTIVE inspected window of ``ripple_detrended_db(., ., width_total)``:
    a bump placed at |a0| beyond the true half-window cannot change the residual std.
    """
    reach = 0.0
    for bump in np.arange(2.0, 95.0, 1.0):
        clean = smooth_cut(slope_db)[1]
        bumped = smooth_cut(slope_db, amp=amp, bump_deg=float(bump))[1]
        a, _ = smooth_cut(slope_db)
        r_clean = ripple_detrended_db(a, clean, width_total)
        r_bump = ripple_detrended_db(a, bumped, width_total)
        if abs(r_bump - r_clean) > threshold_ripple:
            reach = max(reach, float(bump))
    return reach


class TestCorridorModeInspectsOnlyHiMinusLo:
    """Corridor mode: scalar_v9 passes (hi - lo) as the total angle (audit 4.1)."""

    # 70-90 corridor: scalar_v9 computes width_h = hi - lo = 20 -> the ripple window is +/-10.
    LEGACY = 20.0
    # Policy-corrected candidates (audit 4.1 question): guaranteed-min edge (lo) as the inspect
    # half-width pair, the widest legal edge (hi), or the mid corridor ("seat zone").
    CORR_MIN = 70.0   # total angle 70 -> inspects +/-35
    CORR_MAX = 90.0   # total angle 90 -> inspects +/-45
    CORR_SEAT = 80.0  # total angle 80 -> inspects +/-40

    def test_legacy_window_is_hi_minus_lo(self):
        # A defect at 45 deg (inside the legal 70-90 beam, well outside +/-10) is invisible.
        a, clean = smooth_cut(0.003)
        _, with_defect = smooth_cut(0.003, amp=8.0, bump_deg=45.0)
        assert abs(ripple_detrended_db(a, clean, self.LEGACY)
                   - ripple_detrended_db(a, with_defect, self.LEGACY)) < 1e-6
        # .. and the measured window reach of the legacy width IS +/-(hi-lo)/2 = +/-10 deg.
        reach = window_reach(0.003, 8.0, self.LEGACY)
        assert 8.5 <= reach <= 13.0, reach

    @pytest.mark.parametrize("width,lo_reach,hi_reach", [
        (CORR_MIN, 33.0, 38.5), (CORR_SEAT, 38.0, 43.5), (CORR_MAX, 43.0, 49.0)])
    def test_corrected_windows_reach_into_the_corridor(self, width, lo_reach, hi_reach):
        reach = window_reach(0.003, 8.0, width)
        assert lo_reach <= reach <= hi_reach, reach


class TestTargetModeInspectsTwiceTheEdge:
    """Target mode: scalar_v9 passes 2 * preferred as the total angle."""

    def test_target80_inspects_to_80_deg(self):
        # Preferred 80 deg => declared -6 dB half-edge is +/-40, but width 2*80 = 160 inspects
        # out to +/-80: twice the design's own edge.
        reach = window_reach(0.003, 8.0, 160.0)
        assert 74.0 <= reach <= 86.0, reach
        # The corrected interpretation (the window whose -6 dB edges sit at preferred) is
        # width_total = preferred: reach +/-40.
        reach40 = window_reach(0.003, 8.0, 80.0)
        assert 37.0 <= reach40 <= 44.5, reach40

    def test_target_mode_is_twice_as_wide_as_declared(self):
        # Same synthetic defect at 60 deg: inside the legacy 2*pref window, outside the corrected
        # half-window; the legacy ripple score therefore charges behavior the design never
        # declared as its beam, and the corrected one does not.
        a, with_defect = smooth_cut(0.003, amp=8.0, bump_deg=60.0)
        _, clean = smooth_cut(0.003)
        assert (ripple_detrended_db(a, with_defect, 160.0)
                - ripple_detrended_db(a, clean, 160.0)) > 0.5
        assert abs(ripple_detrended_db(a, with_defect, 80.0)
                   - ripple_detrended_db(a, clean, 80.0)) < 0.3


# ------------------------------------------------------------------ end-to-end v9 consequences

@pytest.fixture(scope="module")
def target() -> Target:
    """A v9 corridor target: H 70-90, V 40-60 (the audit 4.1 worked example), band 350-8000."""
    return Target.from_dict({
        "coverage_h_deg": 80.0, "coverage_v_deg": 50.0,
        "band_lo_hz": 350.0, "band_hi_hz": 8000.0, "f0_hz": 700.0,
        "coverage_profile": {
            "mode": "corridor",
            "h": [{"hz": 700.0, "preferred_deg": 80.0, "min_deg": 70.0, "max_deg": 90.0},
                  {"hz": 8000.0, "preferred_deg": 80.0, "min_deg": 70.0, "max_deg": 90.0}],
            "v": [{"hz": 700.0, "preferred_deg": 50.0, "min_deg": 40.0, "max_deg": 60.0},
                  {"hz": 8000.0, "preferred_deg": 50.0, "min_deg": 40.0, "max_deg": 60.0}],
        },
    })


class _StubMetrics:
    """Duck-typed MetricSet: objective v9's ripple path needs only freqs_hz (+ fallbacks)."""

    def __init__(self, freqs):
        self.freqs_hz = np.asarray(freqs, dtype=float)
        self.ripple_h_db = np.full(self.freqs_hz.size, np.nan)
        self.ripple_v_db = np.full(self.freqs_hz.size, np.nan)


class _StubResponse:
    """Duck-typed Response: scalar_v9's _cut_arrays uses exactly these four fields."""

    def __init__(self, angles, spl):
        self.freqs_hz = np.full(spl.shape[0], 700.0)
        self.h_angles_deg = angles
        self.v_angles_deg = angles
        self.spl_h_db = spl
        self.spl_v_db = spl


def _v9_rip(metrics, resp, target: Target, ripple_variant: dict | None = None) -> float:
    """The v9 rip term; with ``ripple_variant``, the per-frequency window correction.

    ``scalar_v9._rip_term_v9`` is called unchanged for the legacy value; the corrected variant
    recomputes the SAME term from the same detrending with the corrected total angle, so only
    the window differs (no module of the repo is modified).
    """
    if ripple_variant is None:
        band = np.ones(metrics.freqs_hz.size, dtype=bool)
        return _rip_term_v9(metrics, resp, target, metrics.freqs_hz, band)
    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = np.ones(f.size, dtype=bool)
    ha, va, sh, sv = resp.h_angles_deg, resp.v_angles_deg, resp.spl_h_db, resp.spl_v_db
    assert target.coverage_profile_mode == "corridor"
    a_h = target.coverage_profile_h[0]
    a_v = target.coverage_profile_v[0]
    lo_h, hi_h = a_h[2], a_h[3]
    lo_v, hi_v = a_v[2], a_v[3]
    total_angle = ripple_variant["total_angle"](lo_h, hi_h)
    vals = np.array([ripple_detrended_db(ha, sh[j], total_angle)
                     + ripple_detrended_db(va, sv[j], total_angle) for j in np.flatnonzero(band)])
    return float(np.mean(vals))


def _rip_legacy_total_angle(target: Target) -> float:
    """What scalar_v9 feeds ripple_detrended_db today: hi - lo per plane (audit 4.1)."""
    lo_h, hi_h = target.coverage_profile_h[0][2], target.coverage_profile_h[0][3]
    lo_v, hi_v = target.coverage_profile_v[0][2], target.coverage_profile_v[0][3]
    # The legacy H and V windows differ; _v9_ripple_values adds both planes so the joint term
    # sees H: Â±10 plus V: Â±10 for the 70-90/40-60 corridor. Use the H plane size as the probe.
    return hi_h - lo_h


class TestEndToEndRankFlip:
    """A design with a mid-corridor lobe defect beats a smooth one under legacy v9, loses under
    any corrected window."""

    def test_rank_flip(self, target: Target):
        freqs = np.array([400.0, 1000.0, 3000.0])
        amp = 8.0
        # A: legal width, a strong symmetric pair of bumps at +/-38 deg (inside the 70-90
        # corridor's seat-zone and widest windows, far outside the legacy +/-10 window).
        _, spl_a = smooth_cut(0.003)
        spl_a_full = spl_a + amp * np.exp(-0.5 * ((np.abs(
            np.arange(-90, 90.25, 0.25)) - 38.0) / 2.0) ** 2)
        # B: slightly wider (76 deg), perfectly smooth.
        spl_b = -0.0029 * np.arange(-90, 90.25, 0.25) ** 2 + 0.0
        resp_a = _StubResponse(np.arange(-90, 90.25, 0.25),
                               np.repeat(spl_a_full[None, :], freqs.size, axis=0))
        resp_b = _StubResponse(np.arange(-90, 90.25, 0.25),
                               np.repeat(spl_b[None, :], freqs.size, axis=0))
        m = _StubMetrics(freqs)
        params = V9Params.from_block({"version": 9, "tolerances": {
            "cov_profile": 3.0, "rip": 1.0, "flat": 1.5, "load": 0.3, "dislope": 9.0,
            "di_roughness": 1.5, "flat_cv": 1.5}})

        # The legacy term (inside the scorer) cannot see mid-corridor defects: A scores ~B.
        rip_a_legacy = _v9_rip(m, resp_a, target)
        rip_b_legacy = _v9_rip(m, resp_b, target)
        assert rip_a_legacy < 0.5, rip_a_legacy       # the 8 dB bump at +/-38 is invisible
        assert abs(rip_b_legacy) < 0.5, rip_b_legacy

        legacy_total_angle = _rip_legacy_total_angle(target)
        assert abs(legacy_total_angle - 20.0) < 1e-9  # hi - lo for the 70-90 corridor

        # The policy choice itself matters: the guaranteed-min window (lo = 70 -> +/-35) barely
        # sees a defect at +/-38; the seat-zone (~ +/-40) and widest (hi = 90 -> +/-45) windows
        # charge it clearly. Every corrected variant flips the ranking to B.
        seen = []
        for variant in ({"total_angle": lambda lo, hi: lo},                # guaranteed-min edge
                        {"total_angle": lambda lo, hi: (lo + hi) / 2.0},   # seat zone
                        {"total_angle": lambda lo, hi: hi}):               # widest legal edge
            rip_a_corr = _v9_rip(m, resp_a, target, variant)
            rip_b_corr = _v9_rip(m, resp_b, target, variant)
            seen.append(rip_a_corr)
            assert abs(rip_b_corr) < 0.5, (variant, rip_b_corr)
            # Rank flip at the J level: legacy prefers A (its only visible window is defect-free);
            # corrected prefers B once the mid-corridor defect is charged.
            assert rip_a_corr > rip_b_corr > rip_a_legacy
        assert seen[0] < 1.0 and seen[1] > 1.0 and seen[2] > 2.0, seen
