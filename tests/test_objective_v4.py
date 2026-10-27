"""Objective v4 (2026-10-27): tolerance-normalised terms, asymmetric coverage, one-sided coverage
below f0, DI standard deviation and the diagonal term.

Offline, CPU only. The contracts pinned here:

* a v4 ``objective:`` block must carry a positive finite tolerance for every term (no defaults),
  and a config whose tolerances/weights let an all-unmeasurable valid design outrank a refusal
  (J > half the penalty) is refused at load;
* with all tolerances 1, ratio 1, ``mask`` and zero weights on the new terms, v4's terms ARE v3's;
* a tolerance divides its term, so ``w * terms[k]`` sums to ``total`` (the stored terms are the
  normalised values);
* the narrow side counts ``cov_narrow_ratio`` times the wide side; ``one_sided`` makes a wide
  pattern below f0 free but still scores a narrow one; ``mask`` ignores everything below f0;
* ``distd`` is the standard deviation of DI over the scored band; ``diag`` reads the 45/135 planes
  of the balloon against the round (mean H/V) reference.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.config import ConfigError, _validate_objective_block
from hornlab_search.metrics.diagonal import diagonal_beamwidths_deg
from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.objective import DEFAULT_WEIGHTS
from hornlab_search.objective.scalar_v2 import objective_v3
from hornlab_search.objective.scalar_v4 import (
    V4_ALL_KEYS,
    V4_WEIGHTED_KEYS,
    V4Params,
    objective_v4,
    worst_valid_j,
)
from hornlab_search.objective.terms import PENALTY_FAILED, WEIGHTED_KEYS
from hornlab_search.objective.versions import SUPPORTED_OBJECTIVE_VERSIONS
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

W = dict(DEFAULT_WEIGHTS)
_T = {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0, "band_lo_hz": 300.0, "band_hi_hz": 12000.0,
      "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0}
ONES = {k: 1.0 for k in V4_WEIGHTED_KEYS}


def _params(tol=None, **kw) -> V4Params:
    block = {"version": 4, "tolerances": dict(ONES if tol is None else tol), **kw}
    return V4Params.from_block(block)


def _target(**kw) -> Target:
    return Target.from_dict({**_T, **kw})


def _metrics(freqs, t: Target, *, bw_h=None, bw_v=None, di=None) -> MetricSet:
    f = np.asarray(freqs, dtype=float)
    ref = target_di_gaussian_db(t.coverage_h_deg, t.coverage_v_deg)
    return MetricSet(
        freqs_hz=f,
        bw_h_deg=np.full(f.size, t.coverage_h_deg) if bw_h is None else np.asarray(bw_h, float),
        bw_v_deg=np.full(f.size, t.coverage_v_deg) if bw_v is None else np.asarray(bw_v, float),
        di_db=np.full(f.size, ref) if di is None else np.asarray(di, float),
        di_source="balloon", ripple_h_db=np.zeros(f.size), ripple_v_db=np.zeros(f.size),
        on_axis_db=np.zeros(f.size), z_throat_real=None, scalars={})


# ------------------------------------------------------------------ versions + validation

def test_v4_is_a_supported_version():
    assert 4 in SUPPORTED_OBJECTIVE_VERSIONS


def test_params_require_every_tolerance():
    for k in V4_WEIGHTED_KEYS:
        tol = {j: 1.0 for j in V4_WEIGHTED_KEYS if j != k}
        with pytest.raises(ValueError, match="missing"):
            V4Params.from_block({"version": 4, "tolerances": tol})


@pytest.mark.parametrize("bad", [0, -1.0, float("nan"), float("inf"), True, "2", None])
def test_params_reject_bad_tolerances(bad):
    tol = dict(ONES)
    tol["cov"] = bad
    with pytest.raises(ValueError, match="tolerances.cov"):
        V4Params.from_block({"version": 4, "tolerances": tol})


def test_params_reject_unknown_keys_and_bad_choices():
    with pytest.raises(ValueError, match="unknown key"):
        V4Params.from_block({"version": 4, "tolerances": ONES, "tolerence": 1})
    with pytest.raises(ValueError, match="cov_below_f0"):
        _params(cov_below_f0="free")
    with pytest.raises(ValueError, match="cov_narrow_ratio"):
        _params(cov_narrow_ratio=0.0)
    with pytest.raises(ValueError, match="diag_reference"):
        _params(diag_reference="separable")
    with pytest.raises(ValueError, match="unknown"):
        V4Params.from_block({"version": 4, "tolerances": {**ONES, "bogus": 1.0}})


def test_config_block_round_trips_and_wraps_errors():
    out = _validate_objective_block({"version": 4, "tolerances": ONES, "cov_narrow_ratio": 2}, "t.yaml")
    assert out["version"] == 4 and out["cov_narrow_ratio"] == 2.0
    assert out["cov_below_f0"] == "mask" and out["tolerances"]["load"] == 1.0
    with pytest.raises(ConfigError, match="t.yaml"):
        _validate_objective_block({"version": 4}, "t.yaml")
    # v1-v3 blocks are unchanged: only 'version' is allowed.
    assert _validate_objective_block({"version": 3}, "t.yaml") == {"version": 3}
    with pytest.raises(ConfigError, match="unknown"):
        _validate_objective_block({"version": 3, "tolerances": ONES}, "t.yaml")


# ------------------------------------------------------------------ equals v3 when neutral

def test_neutral_v4_terms_equal_v3_terms():
    t = _target(f0_hz=800.0)
    f = np.geomspace(300.0, 12000.0, 17)
    m = _metrics(f, t, bw_h=90 + np.linspace(-20, 40, f.size), bw_v=60 + np.linspace(10, -15, f.size),
                 di=11.9 + np.linspace(-2, 3, f.size))
    j3, t3 = objective_v3(m, None, True, t, W)
    j4, t4 = objective_v4(m, None, True, t, W, _params())
    assert j4 == pytest.approx(j3, rel=1e-12)
    for k in WEIGHTED_KEYS:
        assert t4[k] == pytest.approx(t3[k], rel=1e-12)
    assert set(t4) == set(V4_ALL_KEYS)
    assert t4["distd"] == 0.0 and t4["diag"] == 0.0     # new terms are off by default


def test_tolerance_divides_its_term_and_terms_sum_to_total():
    t = _target(f0_hz=800.0)
    f = np.geomspace(300.0, 12000.0, 17)
    m = _metrics(f, t, bw_h=90 + np.linspace(-20, 40, f.size), bw_v=60 + np.linspace(10, -15, f.size))
    tol = dict(ONES, cov=4.0)
    _, base = objective_v4(m, None, True, t, W, _params())
    j, scaled = objective_v4(m, None, True, t, W, _params(tol))
    assert scaled["cov"] == pytest.approx(base["cov"] / 4.0, rel=1e-12)
    assert scaled["rip"] == pytest.approx(base["rip"], rel=1e-12)
    assert j == pytest.approx(sum(W[k] * scaled[k] for k in WEIGHTED_KEYS), rel=1e-12)
    assert scaled["total"] == pytest.approx(j)


# ------------------------------------------------------------------ coverage shape

def test_narrow_side_counts_ratio_times_the_wide_side():
    t = _target(f0_hz=300.0)
    f = np.geomspace(300.0, 12000.0, 9)
    narrow = _metrics(f, t, bw_h=np.full(f.size, 80.0))      # 10 deg narrow in H
    wide = _metrics(f, t, bw_h=np.full(f.size, 100.0))       # 10 deg wide in H
    p = _params(cov_narrow_ratio=2.0)
    _, tn = objective_v4(narrow, None, True, t, W, p)
    _, tw = objective_v4(wide, None, True, t, W, p)
    assert tw["cov"] == pytest.approx(100.0 / 100.0)
    assert tn["cov"] == pytest.approx(2.0 * tw["cov"])


def test_mask_ignores_below_f0_but_one_sided_scores_narrow_and_forgives_wide():
    t = _target(f0_hz=2000.0)
    f = np.geomspace(300.0, 12000.0, 17)
    below = f < 2000.0
    # Right on target above f0; below f0 the pattern is WIDE (physics) or NARROW (a defect).
    wide_lo = np.where(below, 130.0, 90.0)
    narrow_lo = np.where(below, 60.0, 90.0)
    mask = _params(cov_below_f0="mask")
    one = _params(cov_below_f0="one_sided")
    for bw, expect_mask, expect_one in ((wide_lo, 0.0, 0.0), (narrow_lo, 0.0, None)):
        m = _metrics(f, t, bw_h=bw)
        _, tm = objective_v4(m, None, True, t, W, mask)
        _, to = objective_v4(m, None, True, t, W, one)
        assert tm["cov"] == pytest.approx(expect_mask)
        if expect_one is not None:
            assert to["cov"] == pytest.approx(expect_one)
        else:
            assert to["cov"] > 0.0                  # a narrow pattern below f0 is still a defect


# ------------------------------------------------------------------ DI std

def test_distd_is_the_std_of_di_over_the_scored_band_and_off_at_zero_weight():
    t = _target(f0_hz=1000.0)
    f = np.geomspace(300.0, 12000.0, 17)
    di = np.where(f < 1000.0, 5.0, 10.0 + 2.0 * np.sign(np.sin(np.arange(f.size))))
    m = _metrics(f, t, di=di)
    scored = di[f >= 1000.0]
    _, off = objective_v4(m, None, True, t, W, _params())
    assert off["distd"] == 0.0
    _, on = objective_v4(m, None, True, t, {**W, "distd": 1.0}, _params(dict(ONES, distd=2.0)))
    assert on["distd"] == pytest.approx(float(np.std(scored)) / 2.0)


# ------------------------------------------------------------------ diagonal

def _sphere_dirs(n=2500):
    i = np.arange(n) + 0.5
    z = 1.0 - 2.0 * i / n
    phi = math.pi * (1 + 5 ** 0.5) * i
    r = np.sqrt(1 - z * z)
    return np.column_stack([r * np.cos(phi), r * np.sin(phi), z])


def _round_beam_db(dirs, width_deg):
    """-6.0206 dB exactly at polar angle width/2, round in every azimuth."""
    th = np.degrees(np.arccos(np.clip(dirs[:, 2], -1, 1)))
    return -6.0206 * (th / (width_deg / 2.0)) ** 2


def test_diagonal_beamwidth_of_a_round_beam_equals_the_beam_width():
    d = _sphere_dirs()
    bw45, bw135 = diagonal_beamwidths_deg(d, _round_beam_db(d, 60.0), 0.0)
    assert bw45 == pytest.approx(60.0, abs=1.5)
    assert bw135 == pytest.approx(60.0, abs=1.5)


def test_diagonal_beamwidth_unusable_balloon_is_nan():
    d = _sphere_dirs(200)
    a, b = diagonal_beamwidths_deg(d, np.zeros(200), float("nan"))
    assert math.isnan(a) and math.isnan(b)


def _resp(freqs, balloon_widths, dirs):
    ang = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    nf = len(freqs)
    return SimpleNamespace(
        freqs_hz=np.asarray(freqs), h_angles_deg=ang, v_angles_deg=ang,
        spl_h_db=np.zeros((nf, ang.size)), spl_v_db=np.zeros((nf, ang.size)), axis_index=2,
        balloon_dirs=dirs, spl_balloon_db=np.array([_round_beam_db(dirs, w) for w in balloon_widths]))


def test_diag_term_scores_the_round_reference_and_is_zero_weight_off():
    t = _target(f0_hz=300.0, coverage_h_deg=60.0, coverage_v_deg=60.0)
    f = np.geomspace(300.0, 12000.0, 5)
    m = _metrics(f, t)
    dirs = _sphere_dirs()
    good = _resp(f, [60.0] * f.size, dirs)
    pinched = _resp(f, [40.0] * f.size, dirs)         # diagonal beam 20 deg narrower than the round 60
    w = {**W, "diag": 1.0}
    _, off = objective_v4(m, good, True, t, W, _params())
    _, tg = objective_v4(m, good, True, t, w, _params())
    _, tp = objective_v4(m, pinched, True, t, w, _params())
    assert off["diag"] == 0.0
    assert tg["diag"] < 0.05
    assert tp["diag"] == pytest.approx(2 * 20.0 ** 2 / 100.0, rel=0.15)
    # The narrow side is heavier under a ratio.
    _, tp2 = objective_v4(m, pinched, True, t, w, _params(cov_narrow_ratio=2.0))
    assert tp2["diag"] == pytest.approx(2.0 * tp["diag"], rel=1e-9)


def test_diag_without_a_balloon_is_the_unflattering_fill_not_a_crash():
    t = _target(f0_hz=300.0)
    f = np.geomspace(300.0, 12000.0, 5)
    _, tm = objective_v4(_metrics(f, t), None, True, t, {**W, "diag": 1.0}, _params())
    assert tm["diag"] == pytest.approx(30.0)          # NAN_TERM_FILL / tolerance 1


# ------------------------------------------------------------------ penalties + ordering

def test_failed_evaluation_returns_the_penalty_with_the_v4_key_set():
    t = _target()
    j, terms = objective_v4(None, None, False, t, W, _params())
    assert j == PENALTY_FAILED and set(terms) == set(V4_ALL_KEYS)
    assert terms["penalty"] == PENALTY_FAILED


def test_worst_valid_j_matches_the_review_numbers_and_orders_below_the_penalty():
    # Option A tolerances (docs/evidence/OBJECTIVE_V4_TOLERANCES.md), default weights.
    tol = {"cov": 2.0, "rip": 1.0, "di": 0.4, "dislope": 9.0, "flat": 1.5, "load": 0.3,
           "distd": 2.0, "diag": 2.0}
    j = worst_valid_j(_params(tol), W)
    assert j == pytest.approx(30 * (1 / 2 + 1 + 0.3 / 0.4 + 0.5 / 9 + 0.5 / 1.5), rel=1e-9)
    assert j < 0.5 * 1000.0
    # A near-zero tolerance with a live weight breaks ordering - exactly what config refuses.
    assert worst_valid_j(_params(dict(tol, load=1e-3)), {**W, "load": 0.5}) > 0.5 * 1000.0


# ------------------------------------------------------------------ config + dispatch end to end

def _write_cfg(tmp_path, objective, weights):
    import yaml
    from pathlib import Path
    typ = Path(tmp_path) / "typ.yaml"
    typ.write_text(yaml.safe_dump({
        "name": "typ", "family": "FREEFORM", "brief_file": "brief.yaml",
        "generator": {"name": "typology", "profile_h": {"type": "hypex"},
                      "profile_v": {"type": "hypex"}, "n_anchors": 16, "max_wall_deg": 80.0,
                      "mouth": "ellipse"},
        "seed_params": {"L_mm": 190.0, "h_rm_mm": 120.0, "v_rm_mm": 120.0, "h_T": 0.7, "v_T": 0.7},
        "bounds": {"L_mm": {"lo": 140.0, "hi": 220.0}, "h_rm_mm": {"lo": 60.0, "hi": 150.0},
                   "v_rm_mm": {"lo": 60.0, "hi": 150.0}, "h_T": {"lo": 0.3, "hi": 1.0},
                   "v_T": {"lo": 0.3, "hi": 1.0}},
        "target": dict(_T), "weights": dict(W),
        "mesh": {"epw": 8.0, "quadrants": "1", "dof_cap_screen": 5000, "dof_cap_verify": 7000,
                 "dof_cap_final": 8900, "dof_per_triangle": 0.51},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73, "balloon": True,
                  "balloon_points_screen": 512, "balloon_points_verify": 1024, "gmres_tol": 1.0e-05,
                  "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 100,
                   "popsize": None, "tolfun": 0.001},
    }, sort_keys=False), encoding="utf-8")
    brief = Path(tmp_path) / "brief.yaml"
    brief.write_text(yaml.safe_dump({
        "name": "v4", "description": "v4 test brief",
        "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 5.0},
        "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0, "max_depth_mm": 220.0},
        "symmetry": "hv", "target": {**_T, "f0_hz": 800.0}, "weights": weights,
        "objective": objective}, sort_keys=False), encoding="utf-8")
    return typ, brief


def test_load_config_carries_v4_params_and_the_scorer_dispatches(tmp_path):
    from hornlab_search.config import load_config
    from hornlab_search.search.evaluate import _score, make_context

    typ, brief = _write_cfg(tmp_path, {"version": 4, "tolerances": ONES, "cov_narrow_ratio": 2.0},
                            dict(W))
    cfg = load_config(typ, brief=brief)
    assert cfg.objective_version == 4 and cfg.objective_params["cov_narrow_ratio"] == 2.0
    ctx = make_context(cfg, lib_shas={})
    assert isinstance(ctx.objective_params, V4Params)
    t = ctx.target
    f = np.geomspace(300.0, 12000.0, 9)
    j, terms = _score(_metrics(f, t, bw_h=np.full(f.size, 80.0)), None, ctx)
    assert set(terms) == set(V4_ALL_KEYS) and j > 0.0


def test_load_config_refuses_tolerances_that_break_penalty_ordering(tmp_path):
    from hornlab_search.config import load_config

    tol = dict(ONES, load=1e-3)
    typ, brief = _write_cfg(tmp_path, {"version": 4, "tolerances": tol}, {**W, "load": 0.5})
    with pytest.raises(ConfigError, match="refusal penalty"):
        load_config(typ, brief=brief)
