"""Objective v9 (2026-11-16 RFC + 2026-11-17 amendment): non-CD profile scoring.

Offline, CPU only, synthetic MetricSets/Responses. The contracts pinned here:

* the v9 term set: ``cov_profile rip flat load dislope di_roughness flat_cv``, optional
  ``hf_floor``, and raw-unweighted ``diag``/``distd``;
* ``cov_profile`` corridor (zero inside ``[min,max]``, ``min - bw`` narrow-weighted below,
  ``bw - max`` above) and target (quadratic against ``preferred``) modes, including the
  ``cov_below_f0`` one-sided rule against the profile's lower bound;
* per-frequency ripple uses the profile envelope width, not the scalar coverage target;
* ``di_roughness`` is the population std of DI about ``a + b*log10 f`` and is orthogonal to
  ``dislope``;
* G11: a one-anchor ``mode: target`` brief scores the same J as the equivalent v7 constant
  coverage case within 1e-12;
* G12: ``objective.bw8k_floor`` is refused naming both keys; explicit ``hf_floor`` is its own
  weighted term; a valid corridor brief scores end to end;
* config: v9 requires ``target.coverage_profile``, wires ``V9Params`` and uses the first
  anchor's ``preferred_deg`` in the K-law feasibility preflight.
"""
from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from hornlab_search.config import (ConfigError, _brief_preflight_and_derive,
                                   _validate_objective_block, load_brief)
from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.metrics.smoothness import ripple_detrended_db
from hornlab_search.objective.scalar_v7 import V7_WEIGHTED_KEYS, V7Params, objective_v7
from hornlab_search.objective.scalar_v9 import (
    V9_ALL_KEYS,
    V9_DEFAULT_WEIGHTS,
    V9_OPTIONAL_WEIGHTED_KEYS,
    V9_UNWEIGHTED_KEYS,
    V9_WEIGHTED_KEYS,
    V9Params,
    objective_v9,
    resolve_v9_weights,
    worst_valid_v9_j,
)
from hornlab_search.objective.terms import NAN_TERM_FILL, PENALTY_FAILED
from hornlab_search.targets.profile import profile_value
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

ONES = {k: 1.0 for k in V9_WEIGHTED_KEYS}
_T = {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0, "band_lo_hz": 700.0,
      "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0}


def _params(tol=None, **kw) -> V9Params:
    return V9Params.from_block({"version": 9, "tolerances": dict(ONES if tol is None else tol),
                                **kw})


def _anchor_tuple(row):
    hz, pref, lo, hi = row
    out = {"hz": float(hz), "preferred_deg": float(pref)}
    if lo is not None:
        out["min_deg"] = float(lo)
    if hi is not None:
        out["max_deg"] = float(hi)
    return out


def _profile_target(mode, h, v, **kw) -> Target:
    # ``cov_below_f0`` is an objective-block key (V9Params), not a Target field; the tests pass
    # it through this helper for brevity, so drop it before the strict Target parser.
    kw.pop("cov_below_f0", None)
    raw = {**_T, **kw, "coverage_profile": {
        "mode": mode, "interpolation": "log_frequency",
        "h": [_anchor_tuple(row) for row in h], "v": [_anchor_tuple(row) for row in v]}}
    return Target.from_dict(raw)


def _target(**kw) -> Target:
    """Target-mode single-anchor profile (the G11 fixture)."""
    return _profile_target("target", [(700.0, 80.0, None, None)],
                           [(700.0, 50.0, None, None)], **kw)


def _corridor_target(h=None, v=None, **kw) -> Target:
    h = h or [(700.0, 80.0, 70.0, 90.0), (8000.0, 80.0, 70.0, 90.0)]
    v = v or [(700.0, 50.0, 40.0, 60.0), (8000.0, 50.0, 40.0, 60.0)]
    return _profile_target("corridor", h, v, **kw)


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


# ------------------------------------------------------------------ schema + params

def test_v9_key_set_defaults_and_owner_locks():
    assert V9_WEIGHTED_KEYS == ("cov_profile", "rip", "flat", "load", "dislope",
                                "di_roughness", "flat_cv")
    assert V9_OPTIONAL_WEIGHTED_KEYS == ("hf_floor",)
    assert V9_UNWEIGHTED_KEYS == ("diag", "distd")
    for k in ("cov_profile", "rip", "flat", "load", "dislope", "di_roughness", "flat_cv",
              "hf_floor", "diag", "distd"):
        assert k in V9_ALL_KEYS
    assert V9_DEFAULT_WEIGHTS["diag"] == 0.0 and V9_DEFAULT_WEIGHTS["distd"] == 0.0
    assert V9_DEFAULT_WEIGHTS["flat_cv"] == 1.0
    assert "bw8k_floor" not in V9_ALL_KEYS


def test_v9_params_round_trip_and_tolerances_are_required():
    p = _params()
    assert p.cov_narrow_ratio == 1.0 and p.cov_below_f0 == "mask"
    assert p.cov_v_weight == 1.0 and p.flat_band == "band"
    assert p.loaded_re_z == 0.50 and p.lfp_re_z == 0.20 and p.lfp_crossover_ratio == 1.6
    out = p.to_block()
    assert out["version"] == 9 and "bw8k_floor" not in out and "diag_reference" not in out
    assert out["tolerances"] == ONES
    assert V9Params.from_block(out) == p
    for k in V9_WEIGHTED_KEYS:
        tol = {j: 1.0 for j in V9_WEIGHTED_KEYS if j != k}
        with pytest.raises(ValueError, match="missing"):
            V9Params.from_block({"version": 9, "tolerances": tol})


def test_v9_refuses_bw8k_floor_naming_both_keys():
    with pytest.raises(ValueError) as exc:
        V9Params.from_block({"version": 9, "tolerances": ONES, "bw8k_floor": 0.75})
    msg = str(exc.value)
    assert "objective.bw8k_floor" in msg
    assert "min_deg" in msg


def test_v9_hf_floor_mapping_is_validated_and_emitted_only_when_declared():
    block = {"version": 9, "tolerances": ONES,
             "hf_floor": {"hz": 8000.0, "h_deg": 60.0, "v_deg": 37.5, "weight": 0.5,
                          "tolerance": 1.0}}
    p = V9Params.from_block(block)
    assert p.hf_floor is not None
    assert p.hf_floor["weight"] == 0.5 and p.hf_floor["tolerance"] == 1.0
    assert p.to_block()["hf_floor"] == p.hf_floor
    assert "hf_floor" not in _params().to_block()
    for key, bad in (("hz", 0.0), ("h_deg", 181.0), ("v_deg", -1.0), ("weight", -0.1),
                     ("tolerance", 0.0)):
        raw = dict(block["hf_floor"], **{key: bad})
        with pytest.raises(ValueError, match=f"hf_floor.{key}"):
            V9Params.from_block({"version": 9, "tolerances": ONES, "hf_floor": raw})
    with pytest.raises(ValueError, match="hf_floor"):
        V9Params.from_block({"version": 9, "tolerances": ONES, "hf_floor": {"hz": 8000.0}})


def test_resolve_weights_warns_and_owner_locks_diag_distd():
    w = resolve_v9_weights({"cov_profile": 2.0, "diag": 5.0, "distd": 5.0, "nope": 9})
    assert w["cov_profile"] == 2.0 and w["diag"] == 0.0 and w["distd"] == 0.0
    assert "nope" not in w
    assert resolve_v9_weights(None) == V9_DEFAULT_WEIGHTS


def test_worst_valid_v9_j_includes_hf_floor_only_when_declared():
    tol = {k: 2.0 for k in V9_WEIGHTED_KEYS}
    w = {**V9_DEFAULT_WEIGHTS, "cov_profile": 2.0}
    j = worst_valid_v9_j(_params(tol), w)
    expect = sum(resolve_v9_weights(w)[k] * NAN_TERM_FILL / 2.0 for k in V9_WEIGHTED_KEYS)
    assert j == pytest.approx(expect)
    p = _params(tol, hf_floor={"hz": 8000.0, "h_deg": 60.0, "v_deg": 40.0, "weight": 0.5,
                               "tolerance": 1.0})
    j_hf = worst_valid_v9_j(p, {**w, "hf_floor": 0.5})
    assert j_hf == pytest.approx(expect + 0.5 * NAN_TERM_FILL / 1.0)


# ------------------------------------------------------------------ G11 equivalence

def test_g11_target_mode_matches_v7_within_1e_12():
    t = _target(f0_hz=700.0)
    f = np.geomspace(700.0, 8000.0, 9)
    ref = target_di_gaussian_db(80.0, 50.0)
    m = _metrics(f, t, di=ref + 2.0 * np.log10(f / 700.0),
                 on_axis=3.0 * np.log2(f / 1000.0) ** 2, z=np.full(f.size, 0.6),
                 ripple_h=np.full(f.size, 0.2), ripple_v=np.full(f.size, 0.1))
    w7 = {"cov": 1.0, "rip": 1.0, "di": 0.0, "dislope": 0.5, "flat": 0.5, "load": 1.0,
          "flat_cv": 0.0, "distd": 0.0, "diag": 0.0}
    p7 = V7Params.from_block({"version": 7, "tolerances": {k: 1.0 for k in V7_WEIGHTED_KEYS},
                              "cov_narrow_ratio": 1.0, "bw8k_floor": 0.75})
    w9 = {"cov_profile": 1.0, "rip": 1.0, "flat": 0.5, "load": 1.0, "dislope": 0.5,
          "di_roughness": 0.0, "flat_cv": 0.0}
    j7, terms7 = objective_v7(m, None, True, t, w7, p7)
    j9, terms9 = objective_v9(m, None, True, t, w9, _params(cov_narrow_ratio=1.0))
    assert terms7["cov"] == pytest.approx(0.0, abs=1e-12)
    assert terms9["cov_profile"] == pytest.approx(0.0, abs=1e-12)
    assert j9 == pytest.approx(j7, abs=1e-12)
    assert j9 > 0.0


# ------------------------------------------------------------------ cov_profile math

def test_cov_profile_is_zero_inside_the_corridor():
    t = _corridor_target()
    f = np.geomspace(700.0, 8000.0, 6)
    m = _metrics(f, t, bw_h=np.full(f.size, 80.0), bw_v=np.full(f.size, 50.0))
    _, terms = objective_v9(m, None, True, t, {"cov_profile": 1.0}, _params())
    assert terms["cov_profile"] == pytest.approx(0.0, abs=1e-12)


def test_cov_profile_below_min_is_narrow_weighted():
    t = _corridor_target()
    f = np.geomspace(700.0, 8000.0, 4)
    m = _metrics(f, t, bw_h=np.full(f.size, 60.0), bw_v=np.full(f.size, 50.0))
    _, terms = objective_v9(m, None, True, t, {"cov_profile": 1.0},
                            _params(cov_narrow_ratio=2.0))
    # (70 - 60)^2 / 100 = 1 per frequency, x2 narrow ratio; V is inside the corridor.
    assert terms["cov_profile"] == pytest.approx(2.0)


def test_cov_profile_above_max_is_plain_weighted():
    t = _corridor_target()
    f = np.geomspace(700.0, 8000.0, 4)
    m = _metrics(f, t, bw_h=np.full(f.size, 100.0), bw_v=np.full(f.size, 50.0))
    _, terms = objective_v9(m, None, True, t, {"cov_profile": 1.0},
                            _params(cov_narrow_ratio=2.0))
    # (100 - 90)^2 / 100 = 1, wide side is never multiplied by the narrow ratio.
    assert terms["cov_profile"] == pytest.approx(1.0)


def test_cov_profile_target_mode_scores_preferred_with_narrow_ratio():
    t = _target()
    f = np.geomspace(700.0, 8000.0, 4)
    m = _metrics(f, t, bw_h=np.full(f.size, 90.0), bw_v=np.full(f.size, 40.0))  # H wide, V narrow
    _, terms = objective_v9(m, None, True, t, {"cov_profile": 1.0},
                            _params(cov_narrow_ratio=2.0))
    # H: (90-80)^2/100 = 1; V: 2 * (40-50)^2/100 = 2.
    assert terms["cov_profile"] == pytest.approx(3.0)


def test_cov_profile_below_onset_one_sided_vs_mask():
    h = [(1000.0, 80.0, 70.0, 90.0), (8000.0, 80.0, 70.0, 90.0)]
    t_one = _corridor_target(h=h, f0_hz=700.0, cov_below_f0="one_sided")
    t_mask = _corridor_target(h=h, f0_hz=700.0)
    f = np.array([700.0, 1000.0, 2000.0])
    m = _metrics(f, t_one, bw_h=np.array([60.0, 80.0, 80.0]), bw_v=np.full(f.size, 50.0))
    # 700 Hz is below onset 1000: 60 < min 70 -> 2 * (10^2)/100 = 2, mean over 3 = 2/3.
    _, one = objective_v9(m, None, True, t_one, {"cov_profile": 1.0},
                          _params(cov_narrow_ratio=2.0, cov_below_f0="one_sided"))
    assert one["cov_profile"] == pytest.approx(2.0 / 3.0)
    _, masked = objective_v9(m, None, True, t_mask, {"cov_profile": 1.0},
                             _params(cov_narrow_ratio=2.0))
    assert masked["cov_profile"] == pytest.approx(0.0, abs=1e-12)
    # A WIDE pattern below the onset is free under one_sided.
    wide = _metrics(f, t_one, bw_h=np.array([100.0, 80.0, 80.0]),
                    bw_v=np.full(f.size, 50.0))
    _, wide_terms = objective_v9(wide, None, True, t_one, {"cov_profile": 1.0},
                                 _params(cov_narrow_ratio=2.0, cov_below_f0="one_sided"))
    assert wide_terms["cov_profile"] == pytest.approx(0.0, abs=1e-12)


def test_cov_profile_honours_freq_weights():
    t = _corridor_target()
    f = np.array([700.0, 1000.0, 2000.0, 4000.0])
    t = Target.from_dict({**_T,
                          "coverage_profile": {
                              "mode": "corridor", "interpolation": "log_frequency",
                              "h": [_anchor_tuple((700.0, 80.0, 70.0, 90.0)),
                                    _anchor_tuple((8000.0, 80.0, 70.0, 90.0))],
                              "v": [_anchor_tuple((700.0, 50.0, 40.0, 60.0)),
                                    _anchor_tuple((8000.0, 50.0, 40.0, 60.0))]},
                          "freq_weights": {"band_hz": [[700.0, 1000.0, 3.0]]}})
    costs = np.array([100.0, 100.0, 60.0, 60.0])       # [1, 1, 2, 2] raw cost per frequency
    m = _metrics(f, t, bw_h=costs, bw_v=np.full(f.size, 50.0))
    _, terms = objective_v9(m, None, True, t, {"cov_profile": 1.0},
                            _params(cov_narrow_ratio=2.0))
    assert terms["cov_profile"] == pytest.approx((3 + 3 + 2 + 2) / 8.0)


# ------------------------------------------------------------------ per-frequency ripple

def _ripple_resp(f, h_profile, v_profile):
    # 73 angles, 2.5 deg spacing: the production ``solve.angle_count``.  A 37-point grid leaves
    # only five samples inside a 20 deg corridor, below ripple_detrended_db's 7-sample floor.
    ang = np.linspace(-90.0, 90.0, 73)
    spl = np.array([-6.0206 * (ang / 42.0) ** 2 + 0.3 * np.sin(ang / 7.0) for _ in f])
    return SimpleNamespace(freqs_hz=np.asarray(f), h_angles_deg=ang, v_angles_deg=ang,
                           spl_h_db=spl, spl_v_db=spl, axis_index=36)


def test_rip_uses_the_per_frequency_profile_envelope_width():
    t = _corridor_target()
    f = np.array([700.0, 1000.0, 2000.0, 4000.0])
    resp = _ripple_resp(f, None, None)
    expected = []
    for j, fj in enumerate(f):
        _p, lo, hi = profile_value(((700.0, 80.0, 70.0, 90.0),
                                    (8000.0, 80.0, 70.0, 90.0)), float(fj))
        width = float(hi) - float(lo)
        expected.append(ripple_detrended_db(resp.h_angles_deg, resp.spl_h_db[j], width)
                        + ripple_detrended_db(resp.v_angles_deg, resp.spl_v_db[j], width))
    m = _metrics(f, t)
    _, terms = objective_v9(m, resp, True, t, {"rip": 1.0}, _params())
    assert terms["rip"] == pytest.approx(float(np.mean(expected)), rel=1e-12)

    # Target mode uses 2*preferred instead of max-min.
    tt = _target()
    expected_t = [
        ripple_detrended_db(resp.h_angles_deg, resp.spl_h_db[j], 2.0 * 80.0)
        + ripple_detrended_db(resp.v_angles_deg, resp.spl_v_db[j], 2.0 * 50.0)
        for j in range(f.size)]
    _, terms_t = objective_v9(_metrics(f, tt), resp, True, tt, {"rip": 1.0}, _params())
    assert terms_t["rip"] == pytest.approx(float(np.mean(expected_t)), rel=1e-12)


# ------------------------------------------------------------------ di_roughness

def test_di_roughness_of_a_straight_rising_di_is_zero_and_dislope_is_orthogonal():
    t = _profile_target("target", [(700.0, 80.0, None, None)],
                        [(700.0, 50.0, None, None)], di_slope_target=5.0)
    f = np.geomspace(700.0, 8000.0, 9)
    di = 12.0 + 5.0 * np.log10(f / 700.0)
    m = _metrics(f, t, di=di)
    _, terms = objective_v9(m, None, True, t,
                            {"di_roughness": 1.0, "dislope": 1.0, "rip": 0.0, "flat": 0.0,
                             "load": 0.0, "cov_profile": 0.0, "flat_cv": 0.0}, _params())
    assert terms["di_roughness"] == pytest.approx(0.0, abs=1e-9)
    assert terms["dislope"] == pytest.approx(0.0, abs=1e-9)
    t0 = _profile_target("target", [(700.0, 80.0, None, None)],
                         [(700.0, 50.0, None, None)], di_slope_target=0.0)
    _, terms0 = objective_v9(_metrics(f, t0, di=di), None, True, t0,
                             {"dislope": 1.0, "rip": 0.0, "flat": 0.0, "load": 0.0,
                              "cov_profile": 0.0, "flat_cv": 0.0, "di_roughness": 0.0}, _params())
    assert terms0["dislope"] == pytest.approx(25.0, rel=1e-9)     # slope error 5^2


def test_di_roughness_of_a_jagged_di_is_positive_and_enters_j():
    t = _target()
    f = np.geomspace(700.0, 8000.0, 9)
    zig = np.array([0.0, 0.8, -0.7, 0.6, -0.5, 0.4, -0.3, 0.2, 0.0])
    di = 12.0 + 5.0 * np.log10(f / 700.0) + zig
    w = {"di_roughness": 1.0, "rip": 0.0, "flat": 0.0, "load": 0.0, "cov_profile": 0.0,
         "flat_cv": 0.0, "dislope": 0.0}
    m = _metrics(f, t, di=di)
    j, terms = objective_v9(m, None, True, t, w, _params())
    assert terms["di_roughness"] > 0.0
    assert j == pytest.approx(terms["di_roughness"])


# ------------------------------------------------------------------ diag / distd

def test_diag_distd_are_raw_and_never_change_j():
    t = _target()
    f = np.geomspace(700.0, 8000.0, 9)
    ref = target_di_gaussian_db(80.0, 50.0)
    di = ref + 2.0 * np.log10(f / 700.0)
    m = _metrics(f, t, di=di, z=np.full(f.size, 0.6),
                 on_axis=2.0 * np.log2(f / 1000.0) ** 2)
    j_a, terms_a = objective_v9(m, None, True, t,
                                {"diag": 5.0, "distd": 5.0}, _params())
    j_b, terms_b = objective_v9(m, None, True, t, {}, _params())
    assert j_a == pytest.approx(j_b, rel=0.0, abs=0.0)
    assert terms_a["distd"] == pytest.approx(float(np.std(di)))
    assert terms_a["diag"] == pytest.approx(NAN_TERM_FILL)   # no balloon -> raw fill
    weighted = sum(resolve_v9_weights({}, _params())[k] * terms_a[k]
                   for k in V9_WEIGHTED_KEYS)
    assert terms_a["total"] == pytest.approx(weighted)


# ------------------------------------------------------------------ G12: hf_floor + corridor

def test_g12_hf_floor_is_its_own_weighted_term():
    t = _corridor_target(h=[(700.0, 80.0, 70.0, 90.0), (8000.0, 60.0, 50.0, 70.0)])
    f = np.array([700.0, 2000.0, 8000.0])
    m = _metrics(f, t, bw_h=np.full(f.size, 50.0), bw_v=np.full(f.size, 30.0))
    p = _params(hf_floor={"hz": 8000.0, "h_deg": 60.0, "v_deg": 40.0, "weight": 0.5,
                          "tolerance": 2.0})
    w = {k: 0.0 for k in V9_WEIGHTED_KEYS}
    w["hf_floor"] = 0.5
    j, terms = objective_v9(m, None, True, t, w, p)
    # (60-50)^2 + (40-30)^2 = 200 -> raw 2.0 -> normalised 1.0; weight 0.5.
    assert terms["hf_floor"] == pytest.approx(1.0)
    assert j == pytest.approx(0.5)
    assert "hf_floor" in p.to_block()


def test_g12_valid_corridor_brief_scores_end_to_end():
    t = _corridor_target(
        h=[(700.0, 80.0, 72.0, 90.0), (2000.0, 72.0, 62.0, 84.0),
           (8000.0, 58.0, 50.0, 70.0)],
        v=[(700.0, 50.0, 44.0, 58.0), (8000.0, 38.0, 32.0, 46.0)])
    f = np.geomspace(700.0, 8000.0, 12)
    bw_h = np.array([0.5 * (profile_value(t.coverage_profile_h, float(x))[1]
                            + profile_value(t.coverage_profile_h, float(x))[2]) for x in f])
    bw_v = np.array([0.5 * (profile_value(t.coverage_profile_v, float(x))[1]
                            + profile_value(t.coverage_profile_v, float(x))[2]) for x in f])
    m = _metrics(f, t, bw_h=bw_h, bw_v=bw_v, z=np.full(f.size, 0.6),
                 on_axis=2.0 * np.log2(f / 1000.0) ** 2,
                 ripple_h=np.full(f.size, 0.2), ripple_v=np.full(f.size, 0.1))
    j, terms = objective_v9(m, None, True, t, None, _params())
    assert math.isfinite(j) and j > 0.0
    assert set(terms) == set(V9_ALL_KEYS)
    assert terms["penalty"] == 0.0
    assert terms["cov_profile"] == pytest.approx(0.0, abs=1e-12)


# ------------------------------------------------------------------ failure + bookkeeping

def test_failed_evaluation_returns_the_penalty_with_the_v9_key_set():
    t = _target()
    j, terms = objective_v9(None, None, False, t, None, _params())
    assert j == PENALTY_FAILED and set(terms) == set(V9_ALL_KEYS)
    assert terms["penalty"] == PENALTY_FAILED
    assert all(math.isfinite(v) for v in terms.values())


def test_no_solved_frequency_in_the_band_is_the_failure_penalty():
    t = _target()
    j, terms = objective_v9(_metrics(np.array([100.0, 200.0]), t), None, True, t, None,
                            _params())
    assert j == PENALTY_FAILED and terms["n_in_band"] == 0


# ------------------------------------------------------------------ config surface

def _brief_raw(*, with_profile: bool = False) -> dict:
    target = {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0, "band_lo_hz": 700.0,
              "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0,
              "f0_hz": 700.0}
    if with_profile:
        target["coverage_profile"] = {
            "mode": "corridor", "interpolation": "log_frequency",
            "h": [_anchor_tuple((700.0, 80.0, 72.0, 90.0)),
                  _anchor_tuple((8000.0, 58.0, 50.0, 70.0))],
            "v": [_anchor_tuple((700.0, 50.0, 44.0, 58.0)),
                  _anchor_tuple((8000.0, 38.0, 32.0, 46.0))]}
    return {
        "name": "v9", "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 5.0},
        "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0,
                     "max_depth_mm": 220.0},
        "symmetry": "hv", "target": target,
        "weights": {"cov_profile": 1.0, "rip": 1.0, "flat": 0.5, "load": 1.0,
                    "dislope": 0.5, "di_roughness": 1.0, "flat_cv": 1.0},
        "objective": {"version": 9, "tolerances": ONES},
    }


def test_config_validator_accepts_v9_and_emits_the_normalised_block():
    out = _validate_objective_block({"version": 9, "tolerances": ONES}, "b.yaml")
    assert out["version"] == 9 and out["cov_narrow_ratio"] == 1.0
    assert out["cov_below_f0"] == "mask" and out["cov_v_weight"] == 1.0
    assert "bw8k_floor" not in out
    with pytest.raises(ConfigError, match="bw8k_floor"):
        _validate_objective_block({"version": 9, "tolerances": ONES, "bw8k_floor": 0.75},
                                  "b.yaml")


def test_config_requires_target_coverage_profile_for_v9(tmp_path):
    raw = _brief_raw(with_profile=False)
    path = Path(tmp_path) / "brief.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_brief(path)
    msg = str(exc.value)
    assert "objective.version 9" in msg and "target.coverage_profile" in msg


def test_config_passthrough_keeps_the_coverage_profile_block(tmp_path):
    raw = _brief_raw(with_profile=True)
    path = Path(tmp_path) / "brief.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    out = load_brief(path)
    assert out["target"]["coverage_profile"] == raw["target"]["coverage_profile"]


def test_k_law_feasibility_uses_the_first_anchor_preferred_deg():
    raw = _brief_raw(with_profile=True)
    brief = {"target": raw["target"], "envelope": raw["envelope"]}
    out = _brief_preflight_and_derive({"seed_params": {}, "bounds": {}}, brief, "b.yaml")
    feas = out["feasibility"]
    k = 25400.0 * 1000.0
    assert feas["required_mouth_w_mm"] == pytest.approx(k / (700.0 * 80.0))
    assert feas["required_mouth_h_mm"] == pytest.approx(k / (700.0 * 50.0))
    # No profile = the scalar coverage angles, byte-identical to the pre-amendment path.
    raw2 = _brief_raw(with_profile=False)
    brief2 = {"target": raw2["target"], "envelope": raw2["envelope"]}
    out2 = _brief_preflight_and_derive({"seed_params": {}, "bounds": {}}, brief2, "b.yaml")
    assert out2["feasibility"]["required_mouth_w_mm"] == pytest.approx(
        k / (700.0 * 80.0))
    assert out2["feasibility"]["required_mouth_h_mm"] == pytest.approx(
        k / (700.0 * 50.0))
