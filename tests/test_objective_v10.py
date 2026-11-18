"""Objective v10 (2026-11-18 PR-A, owner-gated): v9 with an explicit, REQUIRED ripple region.

Offline, CPU only, synthetic MetricSets/Responses. Pinned here:

* profile angles are FULL beamwidths (the v9 cov term compares them with ``beamwidth_deg``'s
  total included angle), so v9's ``2*preferred`` window inspects twice the -6 dB edge;
* adversarial polar responses with a ripple feature at a known angle prove each
  ``ripple_region`` option inspects exactly the intended angles (and v9 does not);
* parity: a ``seat_zone_deg`` equal to v9's corridor window reproduces v9 J and every term,
  so v10 differs from v9 ONLY in the ripple window;
* no default (refused when absent), ``min_edge`` refused for target-mode profiles, a new
  score identity with a pinned sha256, and registration in the version/dispatch tables.

The v9 tests and v9 J are untouched (``tests/test_objective_v9.py`` still pins the v9 window).
"""
from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from hornlab_search.config import ConfigError, _validate_objective_block, load_brief
from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.objective.scalar_v9 import V9_WEIGHTED_KEYS, V9Params, objective_v9
from hornlab_search.objective.scalar_v10 import (
    V10_ALL_KEYS,
    V10Params,
    objective_v10,
    v10_inspected_total_deg,
    v10_score_identity,
)
from hornlab_search.objective.terms import PENALTY_FAILED
from hornlab_search.objective.versions import SUPPORTED_OBJECTIVE_VERSIONS
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

ONES = {k: 1.0 for k in V9_WEIGHTED_KEYS}
_T = {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0, "band_lo_hz": 700.0,
      "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0}
F = np.array([700.0, 1000.0, 2000.0, 4000.0])
ANG = np.linspace(-90.0, 90.0, 73)          # 2.5 deg spacing (production angle_count)


def _p10(region, **kw) -> V10Params:
    return V10Params.from_block({"version": 10, "tolerances": dict(ONES),
                                 "ripple_region": region, **kw})


def _p9(**kw) -> V9Params:
    return V9Params.from_block({"version": 9, "tolerances": dict(ONES), **kw})


def _row(hz, pref, lo=None, hi=None):
    out = {"hz": hz, "preferred_deg": pref}
    if lo is not None:
        out["min_deg"], out["max_deg"] = lo, hi
    return out


def _corridor() -> Target:
    return Target.from_dict({**_T, "coverage_profile": {
        "mode": "corridor", "interpolation": "log_frequency",
        "h": [_row(700.0, 80.0, 70.0, 90.0), _row(8000.0, 80.0, 70.0, 90.0)],
        "v": [_row(700.0, 50.0, 40.0, 60.0), _row(8000.0, 50.0, 40.0, 60.0)]}})


def _target_mode() -> Target:
    return Target.from_dict({**_T, "coverage_profile": {
        "mode": "target", "interpolation": "log_frequency",
        "h": [_row(700.0, 80.0)], "v": [_row(700.0, 50.0)]}})


def _metrics(t: Target, bw_h=None, bw_v=None) -> MetricSet:
    ref = target_di_gaussian_db(t.coverage_h_deg, t.coverage_v_deg)
    n = F.size
    return MetricSet(
        freqs_hz=F.copy(),
        bw_h_deg=np.full(n, 80.0) if bw_h is None else np.asarray(bw_h, float),
        bw_v_deg=np.full(n, 50.0) if bw_v is None else np.asarray(bw_v, float),
        di_db=np.full(n, ref), di_source="balloon",
        ripple_h_db=np.zeros(n), ripple_v_db=np.zeros(n), on_axis_db=np.zeros(n),
        z_throat_real=None, scalars={})


def _taper(edge_half_deg: float) -> np.ndarray:
    """A pure even-quadratic beam: the detrended quartic fit leaves ZERO residual."""
    return -6.0206 * (ANG / edge_half_deg) ** 2


def _resp(h_bump_deg=None, v_bump_deg=None, bump_db=3.0, h=None, v=None):
    """Smooth tapers plus an optional +bump at exactly +/-``*_bump_deg`` (one sample each side)."""
    sh = _taper(40.0) if h is None else h
    sv = _taper(25.0) if v is None else v
    sh, sv = sh.copy(), sv.copy()
    if h_bump_deg is not None:
        sh[np.isclose(np.abs(ANG), h_bump_deg)] += bump_db
    if v_bump_deg is not None:
        sv[np.isclose(np.abs(ANG), v_bump_deg)] += bump_db
    n = F.size
    return SimpleNamespace(freqs_hz=F.copy(), h_angles_deg=ANG, v_angles_deg=ANG,
                           spl_h_db=np.array([sh] * n), spl_v_db=np.array([sv] * n),
                           axis_index=36)


def _rip(obj, t, resp, params):
    _, terms = obj(_metrics(t), resp, True, t, {"rip": 1.0}, params)
    assert terms["penalty"] == 0.0
    return terms["rip"]


# ------------------------------------------------------------------ semantics (code-verified)

def test_profile_angles_are_full_beamwidths_not_half_angles():
    """cov_profile is zero when bw_h_deg (a TOTAL included angle) equals preferred_deg in
    target mode, and grows when bw is half of it: preferred is a full width."""
    t = _target_mode()
    _, at_pref = objective_v9(_metrics(t, bw_h=np.full(F.size, 80.0)), None, True, t, None, _p9())
    _, at_half = objective_v9(_metrics(t, bw_h=np.full(F.size, 40.0)), None, True, t, None, _p9())
    assert at_pref["cov_profile"] == pytest.approx(0.0, abs=1e-12)
    assert at_half["cov_profile"] > 1.0


def test_inspected_total_angles_per_option():
    t = _corridor()
    for f in F:
        assert v10_inspected_total_deg(t, "h", f, {"mode": "preferred_edge"}) == 80.0
        assert v10_inspected_total_deg(t, "v", f, {"mode": "preferred_edge"}) == 50.0
        assert v10_inspected_total_deg(t, "h", f, {"mode": "min_edge"}) == 70.0
        assert v10_inspected_total_deg(t, "v", f, {"mode": "min_edge"}) == 40.0
        assert v10_inspected_total_deg(t, "h", f, {"mode": "max_edge"}) == 90.0
        assert v10_inspected_total_deg(t, "v", f, {"mode": "max_edge"}) == 60.0
        seat = {"mode": "seat_zone_deg", "h_deg": 120.0, "v_deg": 30.0}
        assert v10_inspected_total_deg(t, "h", f, seat) == 120.0
        assert v10_inspected_total_deg(t, "v", f, seat) == 30.0
    for mode in ("min_edge", "max_edge"):
        with pytest.raises(ValueError, match="corridor"):
            v10_inspected_total_deg(_target_mode(), "h", 1000.0, {"mode": mode})


def test_max_edge_sees_a_defect_beyond_the_preferred_edge():
    """E1 (2026-11-18): H bump at +/-42.5 deg is outside preferred +/-40 but inside max +/-45."""
    t, r = _corridor(), _resp(h_bump_deg=42.5)
    assert _rip(objective_v10, t, r, _p10("preferred_edge")) == pytest.approx(0.0, abs=1e-9)
    assert _rip(objective_v10, t, r, _p10("max_edge")) > 0.05


# ------------------------------------------------------------------ adversarial windows

def test_smooth_taper_reads_zero_under_every_option():
    t = _corridor()
    for region in ("preferred_edge", "min_edge",
                   {"mode": "seat_zone_deg", "h_deg": 160.0, "v_deg": 160.0}):
        assert _rip(objective_v10, t, _resp(), _p10(region)) == pytest.approx(0.0, abs=1e-9)


def test_bump_between_min_and_preferred_edge_separates_the_options():
    """H bump at +/-37.5 deg: inside +/-40 (preferred 80) but outside +/-35 (min 70) and far
    outside v9's corridor window +/-10 (90-70=20 total)."""
    t, r = _corridor(), _resp(h_bump_deg=37.5)
    assert _rip(objective_v10, t, r, _p10("preferred_edge")) > 0.05
    assert _rip(objective_v10, t, r, _p10("min_edge")) == pytest.approx(0.0, abs=1e-9)
    assert _rip(objective_v9, t, r, _p9()) == pytest.approx(0.0, abs=1e-9)   # v9 misses it


def test_bump_just_outside_preferred_edge_is_ignored():
    t, r = _corridor(), _resp(h_bump_deg=42.5, v_bump_deg=27.5)
    assert _rip(objective_v10, t, r, _p10("preferred_edge")) == pytest.approx(0.0, abs=1e-9)


def test_v_plane_window_is_independent_of_h():
    """V bump at +/-22.5: inside V preferred +/-25 but outside V min +/-20."""
    t, r = _corridor(), _resp(v_bump_deg=22.5)
    assert _rip(objective_v10, t, r, _p10("preferred_edge")) > 0.05
    assert _rip(objective_v10, t, r, _p10("min_edge")) == pytest.approx(0.0, abs=1e-9)


def test_seat_zone_inspects_exactly_the_declared_total_angle():
    t, r = _corridor(), _resp(h_bump_deg=60.0)
    wide = {"mode": "seat_zone_deg", "h_deg": 120.0, "v_deg": 50.0}
    narrow = {"mode": "seat_zone_deg", "h_deg": 115.0, "v_deg": 50.0}
    assert _rip(objective_v10, t, r, _p10(wide)) > 0.05          # +/-60 includes the bump
    assert _rip(objective_v10, t, r, _p10(narrow)) == pytest.approx(0.0, abs=1e-9)


def test_target_mode_v9_overreaches_and_preferred_edge_does_not():
    """Target 80 deg: v9 inspects +/-80 (2*preferred total), v10 preferred_edge +/-40."""
    t, r = _target_mode(), _resp(h_bump_deg=60.0)
    assert _rip(objective_v9, t, r, _p9()) > 0.05
    assert _rip(objective_v10, t, r, _p10("preferred_edge")) == pytest.approx(0.0, abs=1e-9)


# ------------------------------------------------------------------ parity with v9

def test_v10_seat_zone_equal_to_v9_window_reproduces_v9_j():
    """Constant 70-90 / 40-60 corridor: v9 inspects a 20 deg total in both planes. A seat zone
    of 20/20 must give the same J and every term bit-for-bit (to 1e-12)."""
    t = _corridor()
    rng = np.random.default_rng(7)
    h = _taper(40.0) + 0.4 * np.sin(ANG / 3.0) + 0.05 * rng.standard_normal(ANG.size)
    v = _taper(25.0) + 0.3 * np.cos(ANG / 4.0)
    h[36] = 0.0
    v[36] = 0.0
    r = _resp(h=h, v=v)
    m = _metrics(t, bw_h=[78.0, 85.0, 92.0, 66.0], bw_v=[48.0, 55.0, 61.0, 38.0])
    j9, t9 = objective_v9(m, r, True, t, None, _p9())
    j10, t10 = objective_v10(m, r, True, t, None,
                             _p10({"mode": "seat_zone_deg", "h_deg": 20.0, "v_deg": 20.0}))
    assert t9["penalty"] == 0.0 and t9["rip"] > 0.0
    assert j10 == pytest.approx(j9, rel=1e-12)
    assert set(t10) == set(t9) == set(V10_ALL_KEYS)
    for k in t9:
        assert t10[k] == pytest.approx(t9[k], rel=1e-12, abs=1e-15), k


# ------------------------------------------------------------------ refusal + identity

def test_ripple_region_has_no_default_and_is_validated():
    with pytest.raises(ValueError, match="requires objective.ripple_region"):
        V10Params.from_block({"version": 10, "tolerances": dict(ONES)})
    for bad in ("edge", "seat_zone_deg", {"mode": "x"},
                {"mode": "seat_zone_deg", "h_deg": 0.0, "v_deg": 40.0},
                {"mode": "seat_zone_deg", "h_deg": 60.0},
                {"mode": "seat_zone_deg", "h_deg": 60.0, "v_deg": True},
                {"mode": "preferred_edge", "h_deg": 60.0}):
        with pytest.raises(ValueError):
            _p10(bad)
    with pytest.raises(ConfigError, match="ripple_region"):
        _validate_objective_block({"version": 10, "tolerances": dict(ONES)}, "b.yaml")


def test_min_edge_on_a_target_mode_profile_is_the_failure_penalty_at_score_time():
    t = _target_mode()
    j, terms = objective_v10(_metrics(t), _resp(), True, t, None, _p10("min_edge"))
    assert j == PENALTY_FAILED and terms["penalty"] == PENALTY_FAILED


def _brief(tmp_path, region, mode="corridor"):
    rows = ({"h": [_row(700.0, 80.0, 70.0, 90.0), _row(8000.0, 80.0, 70.0, 90.0)],
             "v": [_row(700.0, 50.0, 40.0, 60.0), _row(8000.0, 50.0, 40.0, 60.0)]}
            if mode == "corridor" else {"h": [_row(700.0, 80.0)], "v": [_row(700.0, 50.0)]})
    raw = {"name": "v10", "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 5.0},
           "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0, "max_depth_mm": 220.0},
           "symmetry": "hv",
           "target": {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0, "band_lo_hz": 700.0,
                      "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0,
                      "f0_hz": 700.0,
                      "coverage_profile": {"mode": mode, "interpolation": "log_frequency",
                                           **rows}},
           "weights": {"cov_profile": 1.0, "rip": 1.0, "flat": 0.5, "load": 1.0,
                       "dislope": 0.5, "di_roughness": 1.0, "flat_cv": 1.0},
           "objective": {"version": 10, "tolerances": dict(ONES), "ripple_region": region}}
    path = Path(tmp_path) / "brief.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


def test_config_loads_v10_and_refuses_min_edge_for_target_mode(tmp_path):
    out = load_brief(_brief(tmp_path, "preferred_edge"))
    assert out["objective"]["version"] == 10
    assert V10Params.from_block(out["objective"]).ripple_region == {"mode": "preferred_edge"}
    with pytest.raises(ConfigError, match="min_edge"):
        load_brief(_brief(tmp_path, "min_edge", mode="target"))
    with pytest.raises(ConfigError, match="max_edge"):
        load_brief(_brief(tmp_path, "max_edge", mode="target"))


def test_score_identity_is_new_stable_and_region_specific():
    ids = {name: v10_score_identity(_p10(region))["sha256"] for name, region in (
        ("pref", "preferred_edge"), ("min", "min_edge"), ("max", "max_edge"),
        ("seat", {"mode": "seat_zone_deg", "h_deg": 120.0, "v_deg": 60.0}))}
    assert len(set(ids.values())) == 4
    # Pinned: any change to the v10 block normalisation changes the identity on purpose.
    assert ids["pref"] == PINNED_PREFERRED_EDGE_SHA
    block = _p10("preferred_edge").to_block()
    assert block["version"] == 10 and block["ripple_region"] == {"mode": "preferred_edge"}
    assert _p9().to_block()["version"] == 9 and "ripple_region" not in _p9().to_block()
    assert V10Params.from_block(block).to_block() == block          # round trip


def test_v10_is_registered_and_dispatched():
    from hornlab_search.search.evaluate import _OBJECTIVE_SCORERS
    assert 10 in SUPPORTED_OBJECTIVE_VERSIONS and 9 in SUPPORTED_OBJECTIVE_VERSIONS
    t = _corridor()
    j, terms = _OBJECTIVE_SCORERS[10](_metrics(t), _resp(), t, None,
                                      _p10("preferred_edge").to_block())
    assert math.isfinite(j) and terms["penalty"] == 0.0


PINNED_PREFERRED_EDGE_SHA = "7823664cf589d6fd499a08f4cacdeda05963d4761aff7703bf91eea41ddd8498"
