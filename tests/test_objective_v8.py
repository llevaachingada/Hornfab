"""Objective v8 PROPOSAL (2026-11-12, day plan section 5 group G): offline scorer contract.

Offline, CPU only, synthetic MetricSets/Responses/throats; no real data. The contracts pinned
here:

* v8 is registered NOWHERE: ``objective/versions.py`` still lists 1-7 and the evaluate dispatch
  table has no v8 entry (the whole module is an owner-approval proposal, never a default);
* every weighted term is in LINEAR units (RMS deg cov/diag, RMS dB rip/di, linear dB/decade
  dislope error, dB stds flat/distd/flat_cv) and divided by a per-term tolerance;
* tolerances: every weighted key is required, positive and finite; the measured per-class
  defaults (``V8_MEASURED_TOLERANCES`` / ``V8Params.for_class``) are the only shipped numbers;
* loading / f11 / round-throat are HARD REFUSALS (the 1e3 failure penalty, ``gate_failed`` = 1),
  never weights: ``load`` is not a v8 term at all;
* the raws of zero-weight terms (distd / diag / flat_cv) are still measured (the tolerance
  calibration and any re-weighting need the real values);
* determinism: the same inputs give byte-identical terms, and the scorer never raises.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.objective import DEFAULT_WEIGHTS
from hornlab_search.objective.scalar_v4 import V4_WEIGHTED_KEYS
from hornlab_search.objective.scalar_v8 import (
    V8_ALL_KEYS,
    V8_DEFAULT_WEIGHTS,
    V8_MEASURED_TOLERANCES,
    V8_WEIGHTED_KEYS,
    LOADING_GATE_Z_MIN,
    objective_v8,
    resolve_v8_weights,
    v8_raw_terms,
    worst_valid_j,
    V8Params,
)
from hornlab_search.objective.terms import NAN_TERM_FILL, PENALTY_FAILED
from hornlab_search.objective.versions import SUPPORTED_OBJECTIVE_VERSIONS
from hornlab_search.search.evaluate import _OBJECTIVE_SCORERS
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

ONES = {k: 1.0 for k in V8_WEIGHTED_KEYS}
_T = {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0, "band_lo_hz": 300.0, "band_hi_hz": 8000.0,
      "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0}


def _params(tol=None, **kw) -> V8Params:
    return V8Params.from_block({"version": 8, "tolerances": dict(ONES if tol is None else tol),
                                **kw})


def _target(**kw) -> Target:
    return Target.from_dict({**_T, **kw})


def _metrics(freqs, t: Target, *, bw_h=None, bw_v=None, di=None, z=None, on_axis=None,
             ripple_h=None, ripple_v=None, scalars=None) -> MetricSet:
    f = np.asarray(freqs, dtype=float)
    ref = target_di_gaussian_db(t.coverage_h_deg, t.coverage_v_deg)
    return MetricSet(
        freqs_hz=f,
        bw_h_deg=np.full(f.size, t.coverage_h_deg) if bw_h is None else np.asarray(bw_h, float),
        bw_v_deg=np.full(f.size, t.coverage_v_deg) if bw_v is None else np.asarray(bw_v, float),
        di_db=np.full(f.size, ref) if di is None else np.asarray(di, float),
        di_source="balloon",
        ripple_h_db=np.zeros(f.size) if ripple_h is None else np.asarray(ripple_h, float),
        ripple_v_db=np.zeros(f.size) if ripple_v is None else np.asarray(ripple_v, float),
        on_axis_db=np.zeros(f.size) if on_axis is None else np.asarray(on_axis, float),
        z_throat_real=None if z is None else np.asarray(z, float),
        scalars={} if scalars is None else dict(scalars))


# ------------------------------------------------------------------ registration + schema

def test_v8_is_registered_nowhere_and_never_changes_a_default():
    assert SUPPORTED_OBJECTIVE_VERSIONS == (1, 2, 3, 4, 5, 6, 7)
    assert 8 not in _OBJECTIVE_SCORERS
    assert tuple(sorted(_OBJECTIVE_SCORERS)) == SUPPORTED_OBJECTIVE_VERSIONS


def test_v8_key_set_is_v4_minus_load_plus_the_extras():
    assert set(V8_WEIGHTED_KEYS) == (set(V4_WEIGHTED_KEYS) - {"load"}) | {"distd", "diag",
                                                                          "flat_cv"}
    assert V8_DEFAULT_WEIGHTS == {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5,
                                  "distd": 0.0, "diag": 0.0, "flat_cv": 0.0}
    assert "load" not in V8_ALL_KEYS and "load" not in V8_DEFAULT_WEIGHTS
    assert set(V8_ALL_KEYS) == set(V8_WEIGHTED_KEYS) | {
        "penalty", "total", "n_nan", "n_in_band", "di_estimated",
        "lfp20_hz", "lfp50_hz", "rez_min_from_fx", "f11_hz", "loaded_hi_hz", "gate_failed"}


def test_params_require_every_tolerance_and_reject_bad_values():
    p = _params()
    assert p.cov_narrow_ratio == 1.0 and p.cov_below_f0 == "mask"
    assert p.gates == ("round_throat", "loading", "f11")
    assert p.lfp_re_z == 0.20 and p.lfp_crossover_ratio == 1.6 and p.loaded_re_z == 0.50
    for k in V8_WEIGHTED_KEYS:
        tol = {j: 1.0 for j in V8_WEIGHTED_KEYS if j != k}
        with pytest.raises(ValueError, match="missing"):
            V8Params.from_block({"version": 8, "tolerances": tol})
    with pytest.raises(ValueError, match="unknown key"):
        V8Params.from_block({"version": 8, "tolerances": dict(ONES), "bw8k_floor": 1.0})
    with pytest.raises(ValueError, match="tolerances.cov"):
        V8Params.from_block({"version": 8, "tolerances": dict(ONES, cov=0.0)})
    with pytest.raises(ValueError, match="gates"):
        V8Params.from_block({"version": 8, "tolerances": dict(ONES), "gates": ["throat"]})
    with pytest.raises(ValueError, match="lfp_re_z"):
        V8Params.from_block({"version": 8, "tolerances": dict(ONES), "lfp_re_z": -1.0})
    assert p.to_block()["version"] == 8
    assert V8Params.from_block(p.to_block()) == p


def test_measured_default_tolerances_exist_for_every_class_and_every_term():
    assert sorted(V8_MEASURED_TOLERANCES) == ["A", "B", "C"]
    for cls, tolerances in V8_MEASURED_TOLERANCES.items():
        assert set(tolerances) == set(V8_WEIGHTED_KEYS), cls
        assert all(math.isfinite(v) and v > 0.0 for v in tolerances.values()), cls
        p = V8Params.for_class(cls)
        assert p.tolerances == tolerances
    with pytest.raises(ValueError, match="no measured v8 tolerances"):
        V8Params.for_class("Z")


def test_resolve_weights_warns_and_ignores_unknown_keys():
    w = resolve_v8_weights({"cov": 2.0, "nope": 9})
    assert w["cov"] == 2.0 and w["rip"] == 1.0 and "nope" not in w
    assert resolve_v8_weights(None) == V8_DEFAULT_WEIGHTS


def test_worst_valid_j_uses_the_v8_term_set():
    tol = {k: 2.0 for k in V8_WEIGHTED_KEYS}
    w = {**V8_DEFAULT_WEIGHTS, "cov": 2.0}
    j = worst_valid_j(_params(tol), w)
    # cov 2.0, rip 1.0, di 0.3, dislope 0.5, flat 0.5 carry weight; the three extras do not.
    assert j == pytest.approx((2.0 + 1.0 + 0.3 + 0.5 + 0.5) * NAN_TERM_FILL / 2.0)


# ------------------------------------------------------------------ linear-unit terms

def test_cov_is_rms_degrees_and_tolerance_normalised():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, t, bw_h=np.full(f.size, 94.0), bw_v=np.full(f.size, 64.0))
    # symmetric 4-deg error on both planes -> sqrt(2) * 4 deg of RMS error
    _, t1 = objective_v8(m, None, True, t, {"cov": 1.0}, _params())
    _, t2 = objective_v8(m, None, True, t, {"cov": 1.0}, _params(tol=dict(ONES, cov=2.0)))
    assert t1["cov"] == pytest.approx(math.sqrt(2.0) * 4.0)
    assert t2["cov"] == pytest.approx(t1["cov"] / 2.0)


def test_cov_narrow_side_counts_the_ratio_like_v4():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    one = {"cov": 1.0}
    narrow = objective_v8(_metrics(f, t, bw_h=np.full(f.size, 80.0)), None, True, t, one,
                          _params(cov_narrow_ratio=2.0))[1]
    wide = objective_v8(_metrics(f, t, bw_h=np.full(f.size, 100.0)), None, True, t, one,
                        _params(cov_narrow_ratio=2.0))[1]
    assert narrow["cov"] == pytest.approx(math.sqrt(2.0) * wide["cov"])
    # (2x side weight inside the RMS: sqrt(2*100) = sqrt(2)*sqrt(100) = sqrt(2) x wide)


def test_cov_per_plane_f0_v_mask_is_preserved():
    t = _target(f0_hz=800.0, band_hi_hz=8000.0, f0_v_hz=1400.0)
    f = np.array([800.0, 1000.0, 1400.0, 2800.0])
    # H perfect everywhere; V off by 6 deg everywhere but scored only at f >= f0_v (1400).
    m = _metrics(f, t, bw_h=np.full(f.size, 90.0), bw_v=np.full(f.size, 66.0))
    _, terms = objective_v8(m, None, True, t, {"cov": 1.0}, _params())
    # V plane scored only at f >= 1400 (2 samples): mean of 6^2 = 36; H zero -> sqrt(36) = 6.
    assert terms["cov"] == pytest.approx(6.0)


def test_cov_unmeasurable_plane_is_the_fill_not_zero():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    bw_h = np.full(f.size, 90.0)
    bw_v = np.full(f.size, np.nan)
    _, terms = objective_v8(_metrics(f, t, bw_h=bw_h, bw_v=bw_v), None, True, t,
                            {"cov": 1.0}, _params())
    assert terms["cov"] == pytest.approx(NAN_TERM_FILL / 1.0)


def test_rip_is_rms_db_over_the_band():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    # per-f ripple_h + ripple_v = 2.0 -> RMS = 2.0
    r = _metrics(f, t, ripple_h=np.full(f.size, 2.0))
    _, t1 = objective_v8(r, None, True, t, {"rip": 1.0}, _params())
    _, t2 = objective_v8(r, None, True, t, {"rip": 1.0}, _params(tol=dict(ONES, rip=4.0)))
    assert t1["rip"] == pytest.approx(2.0)
    assert t2["rip"] == pytest.approx(0.5)


def test_di_is_rms_db_error_against_the_di_target():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    ref = target_di_gaussian_db(90.0, 60.0)
    m = _metrics(f, t, di=np.full(f.size, ref + 1.5))
    _, terms = objective_v8(m, None, True, t, {"di": 1.0}, _params())
    assert terms["di"] == pytest.approx(1.5)


def test_dislope_is_the_linear_slope_error_in_db_per_decade():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0, di_slope_target=0.0)
    f = np.geomspace(300.0, 4000.0, 9)
    ref = target_di_gaussian_db(90.0, 60.0)
    m = _metrics(f, t, di=ref + 2.0 * np.log10(f / 1000.0))   # slope exactly +2 dB/decade
    _, terms = objective_v8(m, None, True, t, {"dislope": 1.0}, _params())
    assert terms["dislope"] == pytest.approx(2.0, rel=1e-6)
    t3 = _target(f0_hz=300.0, band_hi_hz=4000.0, di_slope_target=3.0)
    _, terms3 = objective_v8(m, None, True, t3, {"dislope": 1.0}, _params())
    assert terms3["dislope"] == pytest.approx(1.0, rel=1e-6)


def test_flat_removes_the_log2_tilt_and_scores_the_residual_db():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0)
    f = np.geomspace(300.0, 4000.0, 9)
    m_tilt = _metrics(f, t, on_axis=10.0 * np.log2(f))        # pure tilt: EQ-able -> 0
    _, tt = objective_v8(m_tilt, None, True, t, {"flat": 1.0}, _params())
    assert tt["flat"] == pytest.approx(0.0, abs=1e-6)
    m_rough = _metrics(f, t, on_axis=np.full(f.size, 90.0)
                       + np.array([0.0, 1.0, -1.0, 1.0, 0.0, -1.0, 1.0, -1.0, 0.0]))
    _, tr = objective_v8(m_rough, None, True, t, {"flat": 1.0}, _params())
    assert tr["flat"] > 0.0


def test_distd_diag_flat_cv_raws_are_measured_even_at_zero_weight():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0)
    f = np.geomspace(300.0, 4000.0, 9)
    ref = target_di_gaussian_db(90.0, 60.0)
    di = np.where(f < 1000.0, ref, ref + 2.0)
    m = _metrics(f, t, di=di, on_axis=np.full(f.size, 90.0)
                 + np.array([0.0, 1.0, -1.0, 1.0, 0.0, -1.0, 1.0, -1.0, 0.0]))
    band = (f >= t.band_lo_hz) & (f <= t.band_hi_hz)
    score = band & (f >= t.f0_effective_hz())
    raws = v8_raw_terms(m, None, t, band, score, _params(), None, None)["raw"]
    assert raws["distd"] == pytest.approx(float(np.std(di[score])))
    assert raws["flat"] > 0.0
    assert raws["flat_cv"] > 0.0                    # curvature even though the weight is 0.0
    # the on-axis values above have a residual with population std > 0
    assert raws["flat_cv"] != 0.0


# ------------------------------------------------------------------ diag (balloon fixture)

def _sphere_dirs(n=2500):
    i = np.arange(n) + 0.5
    z = 1.0 - 2.0 * i / n
    phi = math.pi * (1 + 5 ** 0.5) * i
    r = np.sqrt(1 - z * z)
    return np.column_stack([r * np.cos(phi), r * np.sin(phi), z])


def _round_beam_db(dirs, width_deg):
    th = np.degrees(np.arccos(np.clip(dirs[:, 2], -1, 1)))
    return -6.0206 * (th / (width_deg / 2.0)) ** 2


def _resp(freqs, balloon_widths, dirs):
    ang = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    nf = len(freqs)
    return SimpleNamespace(
        freqs_hz=np.asarray(freqs), h_angles_deg=ang, v_angles_deg=ang,
        spl_h_db=np.zeros((nf, ang.size)), spl_v_db=np.zeros((nf, ang.size)), axis_index=2,
        balloon_dirs=dirs,
        spl_balloon_db=np.array([_round_beam_db(dirs, w) for w in balloon_widths]))


def test_diag_is_rms_degrees_and_tracks_the_v4_squared_term():
    t = _target(f0_hz=300.0, coverage_h_deg=60.0, coverage_v_deg=60.0)
    f = np.geomspace(300.0, 12000.0, 5)
    dirs = _sphere_dirs()
    pinched = _resp(f, [40.0] * f.size, dirs)      # diagonal beam 20 deg narrower than round 60
    m = _metrics(f, t)
    _, tv8 = objective_v8(m, pinched, True, t, {"diag": 1.0}, _params())
    # v4 stores (m45 + m135)/100 with m = mean side-weighted squared errors; v8 is its sqrt.
    from hornlab_search.objective.scalar_v4 import V4_WEIGHTED_KEYS, objective_v4, V4Params
    p4 = V4Params.from_block({"version": 4, "tolerances": {k: 1.0 for k in V4_WEIGHTED_KEYS}})
    _, tv4 = objective_v4(m, pinched, True, t, {**DEFAULT_WEIGHTS, "diag": 1.0}, p4)
    assert tv8["diag"] == pytest.approx(10.0 * math.sqrt(tv4["diag"]), rel=1e-9)
    assert tv8["diag"] > 20.0                       # a 20-deg pinch is a big RMS diagonal error


def test_diag_without_a_balloon_is_the_fill():
    t = _target(f0_hz=300.0, coverage_h_deg=60.0, coverage_v_deg=60.0)
    f = np.geomspace(300.0, 12000.0, 5)
    _, terms = objective_v8(_metrics(f, t), None, True, t, {"diag": 1.0}, _params())
    assert terms["diag"] == pytest.approx(NAN_TERM_FILL)


def test_flat_cv_constant_velocity_line_is_zero():
    t = _target(f0_hz=300.0)
    f = np.geomspace(300.0, 3000.0, 9)
    m = _metrics(f, t, on_axis=25.0 - 20.0 * np.log10(f))
    _, terms = objective_v8(m, None, True, t, {"flat_cv": 1.0}, _params())
    assert terms["flat_cv"] == pytest.approx(0.0, abs=1e-9)


# ------------------------------------------------------------------ hard-refusal gates

def test_lfp20_too_late_refuses_the_loading_scored_target():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, z_min=0.7)
    f = np.array([300.0, 600.0, 1200.0, 2400.0, 8000.0])
    m = _metrics(f, t, z=[0.05, 0.10, 0.25, 0.60, 0.70])   # LFP20 = 1200 Hz x 1.6 = 1920 > 600
    j, terms = objective_v8(m, None, True, t, None, _params())
    assert j == PENALTY_FAILED and terms["gate_failed"] == 1.0
    assert terms["penalty"] == PENALTY_FAILED
    assert set(terms) == set(V8_ALL_KEYS)
    assert all(math.isfinite(v) for v in terms.values())


def test_rez_dip_inside_the_loaded_window_refuses():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, z_min=0.7)
    f = np.array([300.0, 600.0, 1200.0, 2400.0, 5584.0, 8000.0])
    m = _metrics(f, t, z=[0.60, 0.62, 0.291, 0.65, 0.55, 0.29],
                 scalars={"f11_hz": 5584.0})               # the dip is at/above f11? no: 1200 < 5584
    j, terms = objective_v8(m, None, True, t, None, _params())
    assert j == PENALTY_FAILED and terms["gate_failed"] == 1.0
    assert terms["rez_min_from_fx"] == pytest.approx(0.291)


def test_dip_above_f11_is_free_and_a_loaded_design_passes():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, z_min=0.7)
    f = np.array([300.0, 600.0, 1200.0, 2400.0, 5584.0, 8000.0])
    m = _metrics(f, t, z=[0.60, 0.62, 0.65, 0.70, 0.55, 0.29],
                 scalars={"f11_hz": 5584.0})               # the 8 kHz dip sits above f11
    j, terms = objective_v8(m, None, True, t, None, _params())
    assert j < 1.0 and terms["gate_failed"] == 0.0
    assert terms["rez_min_from_fx"] == pytest.approx(0.55)
    assert terms["f11_hz"] == pytest.approx(5584.0)


def test_loading_gate_never_fires_for_a_cd_target():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0)             # z_min 0: loading is not scored
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, t, z=[0.01, 0.02, 0.05, 0.10])          # would refuse a loading-scored target
    j, terms = objective_v8(m, None, True, t, None, _params())
    assert terms["gate_failed"] == 0.0 and j < 1.0


def test_unmeasurable_loading_hold_refuses():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, z_min=0.7)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    _, terms = objective_v8(_metrics(f, t, z=None), None, True, t, None, _params())
    assert terms["gate_failed"] == 1.0
    assert terms["lfp20_hz"] == pytest.approx(NAN_TERM_FILL)


def test_empty_loaded_window_refuses_f11():
    # explicit loaded_hi_hz below F_X: the window cannot exist -> f11 (and loading) refuse
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, z_min=0.7, loaded_hi_hz=500.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, t, z=[0.9, 0.9, 0.9, 0.9])
    j, terms = objective_v8(m, None, True, t, None, _params())
    assert j == PENALTY_FAILED and terms["gate_failed"] == 1.0
    assert terms["loaded_hi_hz"] == pytest.approx(500.0)


def test_gates_can_be_switched_off_in_the_block():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, z_min=0.7)
    f = np.array([300.0, 600.0, 1200.0, 2400.0, 8000.0])
    m = _metrics(f, t, z=[0.05, 0.10, 0.25, 0.60, 0.70])
    p = _params(gates=[])
    j, terms = objective_v8(m, None, True, t, None, p)
    assert terms["gate_failed"] == 0.0 and j < 1.0


def test_round_throat_gate_refuses_a_misfit_and_passes_a_fitting_shape():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, driver_exit_radius_mm=18.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, t)
    bad = {"width_mm": 24.0, "height_mm": 24.0, "roundness": 1.0}    # 48 mm throat vs 36 mm exit
    j, terms = objective_v8(m, None, True, t, None, _params(), throat=bad)
    assert j == PENALTY_FAILED and terms["gate_failed"] == 1.0
    good = {"width_mm": 36.0, "height_mm": 36.0, "roundness": 1.0}
    _, terms_ok = objective_v8(m, None, True, t, None, _params(), throat=good)
    assert terms_ok["gate_failed"] == 0.0
    # unreadable (non-finite) shape: unresolved -> refusal, per the canonical audit convention
    unreadable = {"width_mm": float("nan"), "height_mm": 36.0, "roundness": float("nan")}
    j2, terms2 = objective_v8(m, None, True, t, None, _params(), throat=unreadable)
    assert j2 == PENALTY_FAILED and terms2["gate_failed"] == 1.0


def test_round_throat_gate_without_throat_data_is_not_applied():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, driver_exit_radius_mm=18.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, t)
    _, terms = objective_v8(m, None, True, t, None, _params(), throat=None)
    assert terms["gate_failed"] == 0.0     # in-search enforcement stays with evaluate.py's C4


# ------------------------------------------------------------------ end-to-end + determinism

def test_synthetic_end_to_end_score_is_the_weighted_normalised_sum():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0)             # CD target: no loading gate
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    ref = target_di_gaussian_db(90.0, 60.0)
    m = _metrics(f, t, bw_h=np.full(f.size, 92.0), bw_v=np.full(f.size, 62.0),
                 ripple_h=np.ones(f.size), di=np.full(f.size, ref + 1.0))
    j, terms = objective_v8(m, None, True, t, None, _params())
    # cov: sqrt(2^2 + 2^2) = 2*sqrt(2); rip: 1.0; di: 1.0; flat/dislope: 0 (clean rows);
    # distd/diag/flat_cv weight 0. v8 defaults: cov 1, rip 1, di 0.3.
    expected = 2.0 * math.sqrt(2.0) + 1.0 + 0.3 * 1.0
    assert j == pytest.approx(expected, rel=1e-12)
    assert terms["total"] == pytest.approx(expected, rel=1e-12)
    assert terms["cov"] == pytest.approx(2.0 * math.sqrt(2.0))
    assert terms["gate_failed"] == 0.0


def test_tolerances_double_the_normalized_terms_halve():
    t = _target(f0_hz=300.0, band_hi_hz=4000.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, t, bw_h=np.full(f.size, 92.0), bw_v=np.full(f.size, 62.0))
    ones = {"cov": 1.0}
    _, t1 = objective_v8(m, None, True, t, ones, _params())
    _, t2 = objective_v8(m, None, True, t, ones, _params(tol=dict(ONES, cov=2.0)))
    assert t2["cov"] == pytest.approx(t1["cov"] / 2.0)


def test_determinism_same_inputs_same_terms():
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, z_min=0.7)
    f = np.array([300.0, 600.0, 1200.0, 2400.0, 5584.0, 8000.0])
    m = _metrics(f, t, z=[0.60, 0.62, 0.65, 0.70, 0.55, 0.29], scalars={"f11_hz": 5584.0})
    _, a = objective_v8(m, None, True, t, None, _params())
    _, b = objective_v8(m, None, True, t, None, _params())
    assert a == b


def test_never_raises_and_penalises_the_failure_paths():
    t = _target()
    for metrics, ok in ((None, False), (None, True), (_metrics(np.array([1.0, 2.0]), t), False)):
        j, terms = objective_v8(metrics, None, ok, t, None, _params())
        assert j == PENALTY_FAILED
        assert set(terms) == set(V8_ALL_KEYS)
    # no solved frequency in the band
    j, terms = objective_v8(_metrics(np.array([100.0, 200.0]), t), None, True, t, None,
                            _params())
    assert j == PENALTY_FAILED and terms["n_in_band"] == 0


def test_v8_gate_refusal_reports_the_same_reason_the_scorer_uses():
    from hornlab_search.objective.scalar_v8 import v8_gate_refusal
    t = _target(f0_hz=600.0, band_hi_hz=8000.0, z_min=0.7, driver_exit_radius_mm=18.0)
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, t, z=[0.05, 0.10, 0.25, 0.60])
    reason = v8_gate_refusal(m, None, True, t, _params(), None, throat=None)
    assert reason is not None and "LFP20" in reason
    cd = Target.from_dict({**_T})
    assert v8_gate_refusal(m, None, True, cd, _params(), None, throat=None) is None


def test_loading_gate_threshold_uses_the_repo_class_b_marker():
    # z_min just below the marker: no gate. At the marker: the gate applies.
    f = np.array([300.0, 600.0, 1200.0, 2400.0])
    m = _metrics(f, _target(f0_hz=600.0), z=[0.05, 0.1, 0.2, 0.3])
    assert LOADING_GATE_Z_MIN == 0.5          # the repo's classify_target threshold
    _, off = objective_v8(m, None, True, _target(f0_hz=600.0, z_min=0.49), None, _params())
    assert off["gate_failed"] == 0.0
    _, on = objective_v8(m, None, True, _target(f0_hz=600.0, z_min=0.50), None, _params())
    assert on["gate_failed"] == 1.0
