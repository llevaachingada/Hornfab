"""Objective v5 (2026-10-29): C1 combined loading, C2 constant-velocity flatness, C3 the 8 kHz
one-sided floor, C5 signed V coverage, plus the v4/v5 dispatch contract.

Offline, CPU only, synthetic MetricSets/Responses. The contracts pinned here:

* C1 ``load`` is ``max(0, log2(LFP20 * ratio / F_X)) + max(0, loaded_re_z - min Re z over
  [F_X, min(band_hi, f11)])``; the Re z hold stops at the design's ``f11_hz`` (``NAN_TERM_FILL``
  when the window has no sample); LFP at the grid start is an upper bound, a crossing above the grid
  end (or no z) is ``NAN_TERM_FILL``, and v4's load is untouched;
* C2 ``flat_cv`` is the population std of a unit-velocity level against a log2-f line over
  F_X..3000 Hz, normalised by its tolerance and 0.0 at zero weight;
* C3 the 8 kHz floor only charges NARROW patterns, at ``min(8000, band_hi)``, and ``cov``'s narrow
  ratio defaults to 2.0;
* C5 ``beamwidth_edges_deg`` reads the analytic cardioid/dipole, a symmetric target reproduces v4's
  cov, and a signed pair scores each half with the narrow-side ratio;
* v4's dispatch entry is unchanged and only version 5 reaches the v5 scorer.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.metrics.polar import beamwidth_edges_deg
from hornlab_search.objective import DEFAULT_WEIGHTS
from hornlab_search.objective.scalar_v4 import (
    V4_ALL_KEYS,
    V4_WEIGHTED_KEYS,
    V4Params,
    objective_v4,
)
from hornlab_search.objective.scalar_v5 import (
    V5_ALL_KEYS,
    V5_DEFAULT_WEIGHTS,
    V5_DIAGNOSTIC_KEYS,
    V5_WEIGHTED_KEYS,
    V5Params,
    objective_v5,
    resolve_v5_weights,
    worst_valid_j,
)
from hornlab_search.objective.terms import NAN_TERM_FILL, PENALTY_FAILED, WEIGHTED_KEYS
from hornlab_search.objective.versions import SUPPORTED_OBJECTIVE_VERSIONS
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet
from test_metrics_helpers import cardioid, cut_db, dipole, omni, probe_angles

W = dict(DEFAULT_WEIGHTS)
ONES = {k: 1.0 for k in V5_WEIGHTED_KEYS}
_T = {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0, "band_lo_hz": 300.0, "band_hi_hz": 12000.0,
      "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0}


def _params(tol=None, **kw) -> V5Params:
    return V5Params.from_block({"version": 5, "tolerances": dict(ONES if tol is None else tol), **kw})


def _target(**kw) -> Target:
    return Target.from_dict({**_T, **kw})


def _metrics(freqs, t: Target, *, bw_h=None, bw_v=None, di=None, z=None, on_axis=None,
             scalars=None) -> MetricSet:
    f = np.asarray(freqs, dtype=float)
    ref = target_di_gaussian_db(t.coverage_h_deg, t.coverage_v_deg)
    return MetricSet(
        freqs_hz=f,
        bw_h_deg=np.full(f.size, t.coverage_h_deg) if bw_h is None else np.asarray(bw_h, float),
        bw_v_deg=np.full(f.size, t.coverage_v_deg) if bw_v is None else np.asarray(bw_v, float),
        di_db=np.full(f.size, ref) if di is None else np.asarray(di, float),
        di_source="balloon", ripple_h_db=np.zeros(f.size), ripple_v_db=np.zeros(f.size),
        on_axis_db=np.zeros(f.size) if on_axis is None else np.asarray(on_axis, float),
        z_throat_real=None if z is None else np.asarray(z, float),
        scalars={} if scalars is None else dict(scalars))


# ------------------------------------------------------------------ schema + params

def test_v5_key_set_is_v4_plus_flat_cv_and_the_diagnostics():
    assert 5 in SUPPORTED_OBJECTIVE_VERSIONS
    assert V5_WEIGHTED_KEYS == V4_WEIGHTED_KEYS + ("flat_cv",)
    assert set(V5_ALL_KEYS) == set(V4_ALL_KEYS) | {"flat_cv"} | set(V5_DIAGNOSTIC_KEYS)
    assert V5_DIAGNOSTIC_KEYS == ("lfp20_hz", "lfp50_hz", "rez_min_from_fx", "f11_hz",
                                  "loaded_hi_hz")
    assert V5_DEFAULT_WEIGHTS == {**W, "distd": 0.0, "diag": 0.0, "flat_cv": 0.0}


def test_v5_defaults_and_params_require_every_tolerance():
    p = _params()
    assert p.cov_narrow_ratio == 2.0 and p.loaded_re_z == 0.50 and p.lfp_re_z == 0.20
    assert p.lfp_crossover_ratio == 1.6 and p.bw8k_floor == 0.75
    assert resolve_v5_weights(None)["flat_cv"] == 0.0
    for k in V5_WEIGHTED_KEYS:
        tol = {j: 1.0 for j in V5_WEIGHTED_KEYS if j != k}
        with pytest.raises(ValueError, match="missing"):
            V5Params.from_block({"version": 5, "tolerances": tol})


def test_worst_valid_j_uses_the_v5_term_set():
    tol = {k: 2.0 for k in V5_WEIGHTED_KEYS}
    w = {**W, "load": 0.5, "flat_cv": 1.0}
    j = worst_valid_j(_params(tol), w)
    wr = resolve_v5_weights(w)
    expect = sum(wr[k] * NAN_TERM_FILL / 2.0 for k in V5_WEIGHTED_KEYS)
    assert j == pytest.approx(expect)


# ------------------------------------------------------------------ C1 loading

def test_load_combines_lfp20_and_the_rez_shortfall():
    # LFP20 = 1000 (exact sample); ratio*LFP20 / F_X = 1000*1.6/800 = 2 -> lfp_pen = log2(2) = 1.
    # min Re z at/above 800 Hz = 0.20 -> rez_pen = 0.50 - 0.20 = 0.30. Raw load = 1.30.
    t = _target(f0_hz=800.0)
    f = np.array([250.0, 500.0, 1000.0, 2000.0, 4000.0])
    m = _metrics(f, t, z=[0.05, 0.10, 0.20, 0.40, 0.80])
    _, terms = objective_v5(m, None, True, t, {"load": 1.0}, _params())
    assert terms["load"] == pytest.approx(1.30)
    assert terms["lfp20_hz"] == pytest.approx(1000.0)
    assert terms["rez_min_from_fx"] == pytest.approx(0.20)
    # LFP50 interpolates in log2(f) between 0.40 at 2 kHz and 0.80 at 4 kHz (t = 0.25 octave).
    assert 2000.0 < terms["lfp50_hz"] < 4000.0
    assert terms["lfp50_hz"] == pytest.approx(2000.0 * 2.0 ** 0.25, rel=1e-9)


def test_lfp_at_the_grid_start_is_an_upper_bound_and_free_below_the_ratio():
    # Already loaded at the lowest solved sample: LFP20 = grid start = 250 Hz.
    # 250 * 1.6 = 400 <= F_X = 400 -> no frequency penalty; only the Re z shortfall remains.
    t = _target(f0_hz=400.0)
    f = np.array([250.0, 500.0, 1000.0, 2000.0, 4000.0])
    m = _metrics(f, t, z=[0.25, 0.30, 0.40, 0.60, 0.80])
    _, terms = objective_v5(m, None, True, t, {"load": 1.0}, _params())
    assert terms["lfp20_hz"] == pytest.approx(250.0)
    assert terms["load"] == pytest.approx(0.50 - 0.30)


def test_lfp_above_the_grid_end_is_the_unmeasurable_fill():
    t = _target(f0_hz=300.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, t, z=[0.01, 0.02, 0.05, 0.19])       # never reaches 0.20
    _, terms = objective_v5(m, None, True, t, {"load": 1.0}, _params())
    assert terms["load"] == pytest.approx(NAN_TERM_FILL)


def test_rez_hold_stops_at_f11_so_an_eight_k_dip_does_not_fail_loading():
    # Loaded >= 0.50 from F_X through f11 = 5584 Hz; the 0.29 dip at 8 kHz is above f11 and free.
    t = _target(f0_hz=600.0, band_hi_hz=8000.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0, 4000.0, 5584.0, 8000.0])
    z = [0.60, 0.62, 0.65, 0.70, 0.68, 0.55, 0.29]
    m = _metrics(f, t, z=z, scalars={"f11_hz": 5584.0})
    _, terms = objective_v5(m, None, True, t, {"load": 1.0}, _params())
    assert terms["load"] == pytest.approx(0.0)
    assert terms["rez_min_from_fx"] == pytest.approx(0.55)
    assert terms["f11_hz"] == pytest.approx(5584.0)
    assert terms["loaded_hi_hz"] == pytest.approx(5584.0)


def test_rez_below_half_inside_the_loaded_window_still_fails():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0)
    f = np.array([300.0, 600.0, 1000.0, 2000.0, 4000.0, 5584.0, 8000.0])
    z = [0.25, 0.60, 0.55, 0.40, 0.70, 0.55, 0.29]
    m = _metrics(f, t, z=z, scalars={"f11_hz": 5584.0})
    _, terms = objective_v5(m, None, True, t, {"load": 1.0}, _params())
    assert terms["rez_min_from_fx"] == pytest.approx(0.40)
    assert terms["load"] == pytest.approx(0.50 - 0.40)


def test_absent_or_null_f11_falls_back_to_band_hi():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0, 4000.0, 5584.0, 8000.0])
    z = [0.60, 0.62, 0.65, 0.70, 0.68, 0.55, 0.29]
    for scalars in ({}, {"f11_hz": None}):
        _, terms = objective_v5(_metrics(f, t, z=z, scalars=scalars), None, True, t,
                                {"load": 1.0}, _params())
        # The whole [F_X, BAND_HI] window applies again: the 8 kHz 0.29 dip is scored.
        assert terms["rez_min_from_fx"] == pytest.approx(0.29)
        assert terms["load"] == pytest.approx(0.50 - 0.29)
        assert terms["loaded_hi_hz"] == pytest.approx(8000.0)
        assert terms["f11_hz"] == pytest.approx(NAN_TERM_FILL)


def test_lfp20_penalty_is_unchanged_by_the_loaded_window():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0)
    f = np.array([300.0, 500.0, 600.0, 1200.0, 2400.0, 8000.0])
    z = [0.05, 0.10, 0.60, 0.65, 0.70, 0.70]
    m = _metrics(f, t, z=z, scalars={"f11_hz": 5584.0})
    _, terms = objective_v5(m, None, True, t, {"load": 1.0}, _params())
    cross = 500.0 * (600.0 / 500.0) ** 0.2          # LFP20 between 500 (0.10) and 600 (0.60)
    assert terms["load"] == pytest.approx(math.log2(cross * 1.6 / 600.0))
    assert terms["rez_min_from_fx"] == pytest.approx(0.60)


def test_no_z_or_no_sample_at_fx_is_the_unmeasurable_fill():
    from hornlab_search.objective.scalar_v5 import _load_v5

    t = _target(f0_hz=800.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    _, t_none = objective_v5(_metrics(f, t, z=None), None, True, t, {"load": 1.0}, _params())
    assert t_none["load"] == pytest.approx(NAN_TERM_FILL)
    assert t_none["lfp20_hz"] == pytest.approx(NAN_TERM_FILL)
    # No solved sample at or above F_X = 800: the loading term is unmeasurable even though z is
    # finite. The whole objective cannot score such a target (v3 masks below f0), so pin the C1
    # helper directly.
    raw, diag = _load_v5(_metrics(f[:2], t, z=[0.9, 0.9]), t, _params())
    assert raw == pytest.approx(NAN_TERM_FILL)
    assert diag["rez_min_from_fx"] == pytest.approx(NAN_TERM_FILL)


def test_explicit_loaded_hi_hz_wins_over_driver_and_stored_f11():
    # 80x80 owner brief: target loaded_hi_hz 5653 beats the driver-exit 5583.5 and stored 3809.
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, loaded_hi_hz=5653.0,
                driver_exit_radius_mm=18.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0, 4000.0, 5584.0, 8000.0])
    z = [0.60, 0.62, 0.65, 0.70, 0.68, 0.55, 0.29]
    m = _metrics(f, t, z=z, scalars={"f11_hz": 3809.0})
    _, terms = objective_v5(m, None, True, t, {"load": 1.0}, _params())
    assert terms["f11_hz"] == pytest.approx(5653.0)
    assert terms["loaded_hi_hz"] == pytest.approx(5653.0)


def test_driver_exit_f11_is_preferred_over_the_stored_design_f11():
    # No explicit target bound: the 18 mm driver exit gives 1.8412*343/(2*pi*0.018) = 5583.5 Hz.
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, driver_exit_radius_mm=18.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0, 4000.0, 5584.0, 8000.0])
    z = [0.60, 0.62, 0.65, 0.70, 0.68, 0.55, 0.29]
    m = _metrics(f, t, z=z, scalars={"f11_hz": 3809.0})   # extended main throat: ignored
    _, terms = objective_v5(m, None, True, t, {"load": 1.0}, _params())
    driver = 1.8412 * 343.0 / (2.0 * math.pi * 0.018)
    assert terms["f11_hz"] == pytest.approx(driver)
    assert terms["loaded_hi_hz"] == pytest.approx(driver)
    assert terms["rez_min_from_fx"] == pytest.approx(0.62)   # min in [600, 5583.5]; the 8 kHz dip is above f11


def test_design_f11_is_the_fallback_when_neither_explicit_nor_driver_is_known():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0, 4000.0, 5584.0, 8000.0])
    z = [0.60, 0.62, 0.65, 0.70, 0.68, 0.55, 0.29]
    m = _metrics(f, t, z=z, scalars={"f11_hz": 3809.0})
    _, terms = objective_v5(m, None, True, t, {"load": 1.0}, _params())
    assert terms["f11_hz"] == pytest.approx(3809.0)
    assert terms["loaded_hi_hz"] == pytest.approx(3809.0)
    assert terms["rez_min_from_fx"] == pytest.approx(0.62)


def test_the_827_hz_dip_fails_loading_under_every_upper_bound():
    # The owner's seed has Re z 0.291 at 827.75 Hz, inside every candidate loaded window.
    f = np.array([300.0, 600.0, 827.75, 1200.0, 2400.0, 4000.0, 5584.0, 8000.0])
    z = [0.60, 0.62, 0.291, 0.65, 0.70, 0.68, 0.55, 0.29]
    cases = (
        {"loaded_hi_hz": 5653.0},               # explicit driver f11
        {"driver_exit_radius_mm": 18.0},        # derived driver-exit f11
        {},                                     # stored design f11 / band_hi
    )
    for extra in cases:
        t = _target(f0_hz=600.0, band_hi_hz=8000.0, **extra)
        m = _metrics(f, t, z=z, scalars={"f11_hz": 3809.0})
        _, terms = objective_v5(m, None, True, t, {"load": 1.0}, _params())
        assert terms["rez_min_from_fx"] == pytest.approx(0.291)
        assert terms["load"] > 0.0


def test_v4_load_is_untouched():
    t = _target(f0_hz=300.0, z_min=0.5)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, t, z=[0.1, 0.2, 0.3, 0.4])
    p4 = V4Params.from_block({"version": 4, "tolerances": {k: 1.0 for k in V4_WEIGHTED_KEYS}})
    _, t4 = objective_v4(m, None, True, t, W, p4)
    assert t4["load"] == pytest.approx(float(np.mean([0.4, 0.3, 0.2, 0.1])))   # v3's definition
    # v4 with no z still scores 0.0 (v5 turns the same case into NAN_TERM_FILL).
    _, t4_none = objective_v4(_metrics(f, t, z=None), None, True, t, W, p4)
    assert t4_none["load"] == 0.0
    assert set(t4) == set(V4_ALL_KEYS)


# ------------------------------------------------------------------ C2 flat_cv

def test_flat_cv_of_a_constant_velocity_line_is_zero():
    t = _target(f0_hz=300.0)
    f = np.geomspace(300.0, 3000.0, 9)
    m = _metrics(f, t, on_axis=25.0 - 20.0 * np.log10(f))     # +20log10(f) = constant
    _, terms = objective_v5(m, None, True, t, {"flat_cv": 1.0}, _params())
    assert terms["flat_cv"] == pytest.approx(0.0, abs=1e-9)


def test_flat_cv_of_a_curved_velocity_line_is_positive_and_tolerance_normalised():
    t = _target(f0_hz=300.0)
    f = np.geomspace(300.0, 3000.0, 9)
    on_axis = 25.0 - 20.0 * np.log10(f) + 3.0 * np.log2(f / 1000.0) ** 2
    m = _metrics(f, t, on_axis=on_axis)
    _, t1 = objective_v5(m, None, True, t, {"flat_cv": 1.0}, _params())
    _, t2 = objective_v5(m, None, True, t, {"flat_cv": 1.0}, _params(tol=dict(ONES, flat_cv=2.0)))
    assert t1["flat_cv"] > 0.0
    assert t1["flat_cv"] == pytest.approx(2.0 * t2["flat_cv"], rel=1e-12)


def test_flat_cv_with_fewer_than_two_samples_is_the_fill():
    t = _target(f0_hz=300.0)
    f = np.array([1000.0, 4000.0])          # only one solved f in [300, 3000]
    _, terms = objective_v5(_metrics(f, t), None, True, t, {"flat_cv": 1.0}, _params())
    assert terms["flat_cv"] == pytest.approx(NAN_TERM_FILL)


def test_flat_cv_zero_weight_stores_zero():
    t = _target(f0_hz=300.0)
    f = np.geomspace(300.0, 3000.0, 9)
    m = _metrics(f, t, on_axis=10.0 * np.linspace(0.0, 3.0, f.size))   # clearly non-flat
    _, terms = objective_v5(m, None, True, t, W, _params())
    assert terms["flat_cv"] == 0.0


# ------------------------------------------------------------------ C3 8 kHz floor

def test_eight_k_floor_penalises_narrow_but_not_wide():
    t = _target(f0_hz=300.0)                 # coverage 90 x 60, floor 67.5 x 45
    f = np.array([300.0, 1000.0, 3000.0, 8000.0])
    narrow = _metrics(f, t, bw_h=[90.0, 90.0, 90.0, 63.0])
    on_target = _metrics(f, t, bw_h=[90.0, 90.0, 90.0, 90.0])
    wide = _metrics(f, t, bw_h=[90.0, 90.0, 90.0, 100.0])
    one = {"cov": 1.0}
    _, tn = objective_v5(narrow, None, True, t, one, _params())
    _, to = objective_v5(on_target, None, True, t, one, _params())
    _, tw = objective_v5(wide, None, True, t, one, _params())
    # base cov: the 63 deg top is NARROW, so it counts twice: 2 * (27^2/100) / 4.
    # The floor then adds (0.75*90 - 63)^2 / 100 = 4.5^2/100 once.
    assert tn["cov"] == pytest.approx(2.0 * (27.0 ** 2 / 100.0) / 4.0 + (4.5 ** 2 / 100.0))
    assert to["cov"] == pytest.approx(0.0)
    assert tw["cov"] == pytest.approx((10.0 ** 2 / 100.0) / 4.0)   # no reward above the floor


def test_cov_narrow_ratio_defaults_to_two_in_v5():
    t = _target(f0_hz=300.0, band_hi_hz=3000.0)
    f = np.array([300.0, 1000.0, 3000.0])
    narrow = _metrics(f, t, bw_h=np.full(f.size, 80.0))     # 10 deg narrow, still above the floor
    wide = _metrics(f, t, bw_h=np.full(f.size, 100.0))      # 10 deg wide
    one = {"cov": 1.0}
    _, tn = objective_v5(narrow, None, True, t, one, _params())
    _, tw = objective_v5(wide, None, True, t, one, _params())
    assert tn["cov"] == pytest.approx(2.0 * tw["cov"])
    assert tw["cov"] == pytest.approx(100.0 / 100.0)


# ------------------------------------------------------------------ C5 signed V edges

def test_beamwidth_edges_on_the_analytic_cardioid_and_dipole():
    ang = probe_angles()
    lo, hi = beamwidth_edges_deg(ang, cut_db(cardioid, ang))
    assert (lo, hi) == pytest.approx((-90.0, 90.0), abs=0.05)
    lo, hi = beamwidth_edges_deg(ang, cut_db(dipole, ang))
    assert lo == pytest.approx(-60.0, abs=0.05) and hi == pytest.approx(60.0, abs=0.05)


def test_beamwidth_edges_one_sided_uses_the_grid_edge_and_omni_uses_both():
    ang = probe_angles()
    lo, hi = beamwidth_edges_deg(ang, cut_db(omni, ang))
    assert (lo, hi) == pytest.approx((-90.0, 90.0))
    s = np.where(ang < 0.0, 74.0, 94.0)      # dead on the left, flat on the right
    s[ang == 0.0] = 94.0
    lo, hi = beamwidth_edges_deg(ang, s)
    assert lo < 0.0 and hi == pytest.approx(90.0)


def test_beamwidth_edges_needs_an_exact_zero_sample():
    ang = (np.arange(-36, 36) + 0.5) * 2.5
    with pytest.raises(ValueError):
        beamwidth_edges_deg(ang, np.zeros_like(ang))


_ANG = np.array([-90.0, -60.0, -30.0, 0.0, 30.0, 60.0, 90.0])


def _v_spl(up: float, down: float) -> np.ndarray:
    """A V cut whose linear-in-angle dB pattern crosses -6.0206 at exactly ``-down``/``+up``."""
    return np.where(_ANG >= 0.0, -6.0206 * _ANG / up, -6.0206 * _ANG / down)


def _v_response(f: np.ndarray, up: float, down: float, t: Target):
    s = np.vstack([_v_spl(up, down)] * f.size)
    h = np.zeros_like(s)
    return SimpleNamespace(freqs_hz=np.asarray(f, dtype=float), h_angles_deg=_ANG.copy(),
                           v_angles_deg=_ANG.copy(), spl_h_db=h, spl_v_db=s, axis_index=3)


def _asym_target(**kw) -> Target:
    return _target(coverage_v_up_deg=15.0, coverage_v_down_deg=-45.0, **kw)


def test_symmetric_target_reproduces_v4_cov():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0)
    f = np.geomspace(300.0, 4000.0, 8)
    m = _metrics(f, t, bw_h=90.0 + np.linspace(-8.0, 9.0, f.size),
                 bw_v=60.0 + np.linspace(3.0, -4.0, f.size))
    w = {"cov": 1.0}
    p4 = V4Params.from_block({"version": 4, "tolerances": {k: 1.0 for k in V4_WEIGHTED_KEYS},
                              "cov_narrow_ratio": 2.0})
    _, t4 = objective_v4(m, None, True, t, w, p4)
    _, t5 = objective_v5(m, None, True, t, w, _params())
    assert t5["cov"] == pytest.approx(t4["cov"], rel=1e-12)


def test_asymmetric_target_scores_each_half_with_the_narrow_ratio():
    t = _asym_target(f0_hz=300.0, band_hi_hz=4000.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, t)
    w = {"cov": 1.0}
    _, on = objective_v5(m, _v_response(f, 15.0, -45.0, t), True, t, w, _params())
    assert on["cov"] == pytest.approx(0.0, abs=1e-6)
    # Upper edge 10 deg wide -> plain error; lower edge 10 deg narrow -> ratio 2.
    _, wide_up = objective_v5(m, _v_response(f, 25.0, -45.0, t), True, t, w, _params())
    _, narrow_down = objective_v5(m, _v_response(f, 15.0, -35.0, t), True, t, w, _params())
    assert wide_up["cov"] == pytest.approx(1.0, rel=1e-6)
    assert narrow_down["cov"] == pytest.approx(2.0, rel=1e-6)


def test_asymmetric_target_without_a_usable_balloon_is_the_fill():
    t = _asym_target(f0_hz=300.0)
    f = np.geomspace(300.0, 4000.0, 4)
    _, terms = objective_v5(_metrics(f, t), None, True, t, {"cov": 1.0}, _params())
    assert terms["cov"] == pytest.approx(NAN_TERM_FILL)


def test_target_v_halves_are_validated_together_and_against_the_total():
    with pytest.raises(ValueError, match="together"):
        _target(coverage_v_up_deg=15.0)
    with pytest.raises(ValueError, match="together"):
        _target(coverage_v_down_deg=-45.0)
    with pytest.raises(ValueError, match="equal"):
        _target(coverage_v_up_deg=15.0, coverage_v_down_deg=-40.0)     # sums to 55, not 60
    with pytest.raises(ValueError, match="coverage_v_up_deg"):
        _target(coverage_v_up_deg=0.0, coverage_v_down_deg=-60.0)
    with pytest.raises(ValueError, match="coverage_v_down_deg"):
        _target(coverage_v_up_deg=60.0, coverage_v_down_deg=0.0)
    ok = _asym_target()
    assert ok.coverage_v_up_deg == 15.0 and ok.coverage_v_down_deg == -45.0


# ------------------------------------------------------------------ failures + dispatch

def test_failed_evaluation_returns_the_penalty_with_the_v5_key_set():
    t = _target()
    j, terms = objective_v5(None, None, False, t, W, _params())
    assert j == PENALTY_FAILED and set(terms) == set(V5_ALL_KEYS)
    assert terms["penalty"] == PENALTY_FAILED
    assert all(math.isfinite(v) for v in terms.values())


def test_v4_dispatch_entry_is_unchanged_and_only_v5_is_added():
    from hornlab_search.search.evaluate import _OBJECTIVE_SCORERS, _score_v4, _score_v5

    assert _OBJECTIVE_SCORERS[4] is _score_v4
    assert _OBJECTIVE_SCORERS[5] is _score_v5
    assert tuple(sorted(_OBJECTIVE_SCORERS)) == SUPPORTED_OBJECTIVE_VERSIONS
    assert tuple(sorted(WEIGHTED_KEYS)) == tuple(sorted(("cov", "rip", "di", "dislope", "flat",
                                                         "load")))
