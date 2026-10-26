"""Phase 0 item 2B (2026-10-26): the optional per-plane scoring frequency ``target.f0_v_hz``.

Contract (owner-directed objective v3 amendment):

* absent ``f0_v_hz`` -> the objective's every term and J are BIT-IDENTICAL to the
  pre-amendment function (the test carries a verbatim copy of that function), and the
  config / params / solve-spec hashes and the dataset record bytes are unchanged;
* set ``f0_v_hz`` -> cov is the SUM of two separately masked means: the horizontal error
  over ``f >= f0_hz`` and the vertical error over ``f >= f0_v_hz``.  A vertical error
  below f0_v does not move J; a horizontal error between f0 and f0_v still does.
* validation: ``0 < f0_v_hz <= band_hi_hz`` and (when f0_hz is set) ``f0_v_hz >= f0_hz``.
* ``load_brief`` accepts a brief carrying ``target.f0_v_hz``.

Offline, CPU only.
"""
from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np
import pytest
import yaml

from hornlab_search.config import load_brief, load_config, solve_spec
from hornlab_search.design.space import DesignSpace
from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.objective import DEFAULT_WEIGHTS
from hornlab_search.objective.scalar import penalty_result, resolve_weights
from hornlab_search.objective.scalar_v2 import (
    _plain_mean,
    _v2_flat_value,
    _v2_ripple_values,
    _weighted_mean,
    freq_weight_vector,
    objective_v3,
)
from hornlab_search.objective import terms as T
from hornlab_search.objective.terms import (
    ALL_KEYS,
    NAN_TERM_FILL,
    PENALTY_FAILED,
    WEIGHTED_KEYS,
)
from hornlab_search.search.rundir import config_sha
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

W = dict(DEFAULT_WEIGHTS)
_T_DICT = {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0, "band_lo_hz": 300.0,
           "band_hi_hz": 12000.0, "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0}


# ------------------------------------------------------------------ the pre-change function
# Verbatim copy of _objective_v3 as it stood before the 2B amendment (2026-10-26), so the
# absent-key test compares against the real old behaviour rather than an approximation.

def _prechange_v3(metrics, resp, ok, target, weights):
    if metrics is None or not ok:
        return penalty_result(PENALTY_FAILED)
    w = resolve_weights(weights)
    f = np.asarray(metrics.freqs_hz, dtype=float)
    band = (f >= target.band_lo_hz) & (f <= target.band_hi_hz)
    n_band = int(band.sum())
    if n_band == 0:
        return penalty_result(PENALTY_FAILED, n_in_band=0)

    def b(x):
        return np.asarray(x, dtype=float)[band]

    f0 = float(target.f0_hz) if target.f0_hz is not None else float(target.band_lo_hz)
    score = band & (f >= f0)
    n_score = int(score.sum())
    if n_score == 0:
        return penalty_result(PENALTY_FAILED, n_in_band=n_band)

    def s(x):
        return np.asarray(x, dtype=float)[score]

    e_f = ((np.asarray(metrics.bw_h_deg, float)[score] - target.coverage_h_deg) ** 2
           + (np.asarray(metrics.bw_v_deg, float)[score] - target.coverage_v_deg) ** 2) / 100.0
    if target.freq_weights is not None and n_score >= 1:
        cov, _ = _weighted_mean(e_f, freq_weight_vector(f, target)[score])
    elif n_score >= 1:
        cov, _ = _plain_mean(e_f)
    else:
        cov = NAN_TERM_FILL

    dsl, _ = T.dislope_term(s(f), s(metrics.di_db), target)
    z = None if metrics.z_throat_real is None else b(metrics.z_throat_real)
    load, _ = T.load_term(z, target)

    ripple_values, _used_resp = _v2_ripple_values(metrics, resp, target, band)
    if target.freq_weights is not None:
        rip, _ = _weighted_mean(ripple_values[band], freq_weight_vector(f, target)[band])
    else:
        rip, _ = _plain_mean(ripple_values[band])

    if float(w["di"]) == 0.0:
        di = 0.0
        di_used = False
    else:
        ref = (float(target.di_target_db) if target.di_target_db is not None
               else target_di_gaussian_db(target.coverage_h_deg, target.coverage_v_deg))
        di_mean, _ = _plain_mean((b(metrics.di_db) - ref) ** 2)
        di = di_mean / 10.0
        di_used = True

    flat = _v2_flat_value(metrics, resp, target, band)

    bad = np.zeros(n_band, dtype=bool)
    for arr in (metrics.bw_h_deg, metrics.bw_v_deg, metrics.on_axis_db):
        bad |= ~np.isfinite(b(arr))
    bad |= ~np.isfinite(ripple_values[band])
    if di_used:
        bad |= ~np.isfinite(b(metrics.di_db))
    if z is not None:
        bad |= ~np.isfinite(z)

    t = {"cov": cov, "rip": rip, "di": di, "dislope": dsl, "flat": flat, "load": load,
         "penalty": 0.0}
    if not all(math.isfinite(t[k]) for k in WEIGHTED_KEYS):
        return penalty_result(PENALTY_FAILED, n_in_band=n_band)
    total = sum(w[k] * t[k] for k in WEIGHTED_KEYS)
    if not math.isfinite(total):
        return penalty_result(PENALTY_FAILED, n_in_band=n_band)
    t["total"] = float(total)
    t["n_nan"] = int(bad.sum())
    t["n_in_band"] = n_score
    t["di_estimated"] = 1.0 if metrics.di_source == "cuts_estimate" else 0.0
    assert set(t) == set(ALL_KEYS)
    return float(total), t


# ------------------------------------------------------------------ helpers

def _target(**extra) -> Target:
    return Target.from_dict({**_T_DICT, **extra})


def _metrics(freqs, target: Target, *, bw_h=None, bw_v=None) -> MetricSet:
    """A synthetic metric set with the target's Gaussian DI reference (all terms finite)."""
    f = np.asarray(freqs, dtype=float)
    return MetricSet(
        freqs_hz=f,
        bw_h_deg=(np.full(f.size, target.coverage_h_deg) if bw_h is None else bw_h),
        bw_v_deg=(np.full(f.size, target.coverage_v_deg) if bw_v is None else bw_v),
        di_db=np.full(f.size, target_di_gaussian_db(target.coverage_h_deg,
                                                    target.coverage_v_deg)),
        di_source="balloon",
        ripple_h_db=np.zeros(f.size), ripple_v_db=np.zeros(f.size),
        on_axis_db=np.zeros(f.size), z_throat_real=None, scalars={})


# ------------------------------------------------------------------ (a) absent = bit-identical

@pytest.mark.parametrize("weighted", [False, True])
def test_absent_f0v_is_bit_identical_to_the_prechange_function(weighted):
    t = _target(f0_hz=1000.0)
    assert t.f0_v_hz is None
    if weighted:
        t = Target.from_dict({**_T_DICT, "f0_hz": 1000.0,
                              "freq_weights": {"band_hz": [[1500.0, 8000.0, 4.0]]}})
    freqs = np.geomspace(t.band_lo_hz, t.band_hi_hz, 17)
    # A case with every term non-trivial: a cov gradient, a ripple, an on-axis tilt.
    m = _metrics(freqs, t,
                 bw_h=np.full(freqs.size, t.coverage_h_deg) + np.linspace(0.0, 25.0, freqs.size),
                 bw_v=np.full(freqs.size, t.coverage_v_deg) + np.linspace(0.0, 12.0, freqs.size))
    m.ripple_h_db = np.linspace(0.0, 1.0, freqs.size)
    m.ripple_v_db = np.linspace(0.0, 0.5, freqs.size)
    m.on_axis_db = np.linspace(-2.0, 2.0, freqs.size)
    m.scalars = {}

    new_J, new_terms = objective_v3(m, None, True, t, W)
    old_J, old_terms = _prechange_v3(m, None, True, t, W)

    assert new_J == old_J                      # EXACT equality, not approx
    assert new_terms == old_terms              # every term, including bookkeeping
    assert set(new_terms) == set(ALL_KEYS)
    assert new_terms["cov"] > 0.0 and new_terms["rip"] > 0.0


def test_absent_f0v_keeps_config_params_solve_hashes_and_j():
    """Pin the pre-change goldens captured before the 2B edit (see the lane report)."""
    cfg = load_config(Path(__file__).resolve().parents[1]
                      / "examples" / "typologies" / "lecleach_asym_odd.yaml")
    t = Target.from_dict(cfg.target_raw)
    assert t.f0_v_hz is None
    assert config_sha(cfg.raw) == "d153b1dd96d1"
    assert DesignSpace.from_config(cfg).seed.hash() == "103316ebbfeb"
    assert solve_spec("screen", cfg).hash() == "cfdb0910d126"

    freqs = np.geomspace(t.band_lo_hz, t.band_hi_hz, 14)
    m = MetricSet(
        freqs_hz=freqs,
        bw_h_deg=np.full(freqs.size, t.coverage_h_deg) + np.linspace(0.0, 40.0, freqs.size),
        bw_v_deg=np.full(freqs.size, t.coverage_v_deg) + np.linspace(0.0, 20.0, freqs.size),
        di_db=np.full(freqs.size, target_di_gaussian_db(t.coverage_h_deg,
                                                        t.coverage_v_deg)),
        di_source="balloon", ripple_h_db=np.zeros(freqs.size),
        ripple_v_db=np.zeros(freqs.size), on_axis_db=np.zeros(freqs.size),
        z_throat_real=None, scalars={})
    J, terms = objective_v3(m, None, True, t, W)
    assert J == 9.526627218934914
    assert terms["n_in_band"] == 10


def test_dataset_target_dict_omits_absent_f0v():
    """Dataset records are emitted only when set, so pre-amendment records stay byte-identical."""
    from hornlab_search.dataset.record import _target_dict

    assert "f0_v_hz" not in _target_dict(_target(f0_hz=1000.0))
    assert "f0_v_hz" not in _target_dict(_target())
    out = _target_dict(_target(f0_hz=1000.0, f0_v_hz=2000.0))
    assert out["f0_v_hz"] == 2000.0


# ------------------------------------------------------------------ (b) per-plane mask

def test_vertical_below_f0v_is_masked_while_horizontal_still_counts():
    t = _target(f0_hz=500.0, f0_v_hz=2000.0)
    freqs = np.array([400.0, 750.0, 1000.0, 2500.0, 5000.0])
    base = _metrics(freqs, t)
    J0, terms0 = objective_v3(base, None, True, t, W)
    assert terms0["n_in_band"] == 4          # H mask: f >= 500 (400 excluded)
    assert terms0["cov"] == 0.0

    # A vertical error at 750 Hz sits ABOVE f0 (so the H mask includes it) but BELOW f0_v:
    # the vertical term must not see it -> J unchanged exactly.
    v_below = _metrics(freqs, t, bw_v=np.full(freqs.size, t.coverage_v_deg) + 0.0)
    v_below.bw_v_deg[1] = t.coverage_v_deg + 100.0
    J_v_below, _ = objective_v3(v_below, None, True, t, W)
    assert J_v_below == J0

    # A horizontal error at the SAME 750 Hz must count (the H mask scores f >= f0).
    h_mid = _metrics(freqs, t)
    h_mid.bw_h_deg[1] = t.coverage_h_deg + 100.0
    J_h_mid, terms_h = objective_v3(h_mid, None, True, t, W)
    assert J_h_mid > J0
    assert terms_h["cov"] == pytest.approx(100.0 ** 2 / 100.0 / 4.0)

    # A vertical error at/above f0_v (2500 Hz) does count.
    v_above = _metrics(freqs, t)
    v_above.bw_v_deg[3] = t.coverage_v_deg + 100.0
    J_v_above, terms_v = objective_v3(v_above, None, True, t, W)
    assert J_v_above > J0
    assert terms_v["cov"] == pytest.approx(100.0 ** 2 / 100.0 / 2.0)

    # Below f0 = 500 neither plane is scored.
    low = _metrics(freqs, t)
    low.bw_h_deg[0] = t.coverage_h_deg + 500.0
    low.bw_v_deg[0] = t.coverage_v_deg + 500.0
    assert objective_v3(low, None, True, t, W)[0] == J0


def test_f0v_cov_is_the_sum_of_two_masked_means_with_freq_weights():
    t = Target.from_dict({**_T_DICT, "f0_hz": 500.0, "f0_v_hz": 2000.0,
                          "freq_weights": {"band_hz": [[2000.0, 9000.0, 3.0]]}})
    freqs = np.array([750.0, 2500.0, 5000.0])
    m = _metrics(freqs, t)
    m.bw_h_deg = np.array([t.coverage_h_deg + 10.0, t.coverage_h_deg + 20.0,
                           t.coverage_h_deg + 30.0])
    m.bw_v_deg = np.array([t.coverage_v_deg + 99.0, t.coverage_v_deg + 40.0,
                           t.coverage_v_deg + 50.0])
    _J, terms = objective_v3(m, None, True, t, W)
    # H: plain mean over all three H-scored rows (750, 2500, 5000), weight 3 on the last two.
    h = np.array([10.0 ** 2, 20.0 ** 2, 30.0 ** 2]) / 100.0
    h_mean = (h[0] + 3.0 * h[1] + 3.0 * h[2]) / (1.0 + 3.0 + 3.0)
    # V: rows at/above 2000 (2500, 5000), both weighted 3.
    v = np.array([40.0 ** 2, 50.0 ** 2]) / 100.0
    v_mean = (3.0 * v[0] + 3.0 * v[1]) / (3.0 + 3.0)
    assert terms["cov"] == pytest.approx(h_mean + v_mean, rel=0.0, abs=1e-15)


# ------------------------------------------------------------------ (c) validation

def test_f0v_validation():
    assert _target(f0_v_hz=2000.0).f0_v_hz == 2000.0      # f0_hz absent is legal
    with pytest.raises(ValueError, match="target.f0_v_hz"):
        _target(f0_hz=1000.0, f0_v_hz=900.0)              # below f0
    with pytest.raises(ValueError, match="target.f0_v_hz"):
        _target(f0_v_hz=12001.0)                          # above band_hi
    with pytest.raises(ValueError, match="target.f0_v_hz"):
        _target(f0_v_hz=0.0)
    with pytest.raises(ValueError, match="unknown key"):
        _target(f0_vertical=1000.0)                        # a typo is an error, never silent


# ------------------------------------------------------------------ (d) load_brief + config

def _brief_payload(*, f0_v=None) -> dict:
    target = dict(_T_DICT)
    target["f0_hz"] = 800.0
    if f0_v is not None:
        target["f0_v_hz"] = f0_v
    return {
        "name": "f0v", "description": "2B test brief",
        "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 5.0},
        "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0,
                     "max_depth_mm": 220.0},
        "symmetry": "hv",
        "target": target,
        "weights": dict(W),
        "objective": {"version": 3},
    }


def test_load_brief_accepts_target_f0v():
    d = Path(tempfile.mkdtemp(prefix="f0v_"))
    p = d / "brief.yaml"
    p.write_text(yaml.safe_dump(_brief_payload(f0_v=1500.0), sort_keys=False),
                 encoding="utf-8")
    brief = load_brief(p)
    assert brief["target"]["f0_v_hz"] == 1500.0
    assert Target.from_dict(brief["target"]).f0_v_hz == 1500.0


def test_config_feasibility_emits_f0v_only_when_present():
    d = Path(tempfile.mkdtemp(prefix="f0v_cfg_"))
    typ = d / "typ.yaml"
    typ.write_text(yaml.safe_dump({
        "name": "typ", "family": "FREEFORM", "brief_file": "brief.yaml",
        "generator": {"name": "typology",
                      "profile_h": {"type": "hypex"}, "profile_v": {"type": "hypex"},
                      "n_anchors": 16, "max_wall_deg": 80.0, "mouth": "ellipse"},
        "seed_params": {"L_mm": 190.0, "h_rm_mm": 120.0, "v_rm_mm": 120.0,
                        "h_T": 0.7, "v_T": 0.7},
        "bounds": {"L_mm": {"lo": 140.0, "hi": 220.0},
                   "h_rm_mm": {"lo": 60.0, "hi": 150.0},
                   "v_rm_mm": {"lo": 60.0, "hi": 150.0},
                   "h_T": {"lo": 0.3, "hi": 1.0}, "v_T": {"lo": 0.3, "hi": 1.0}},
        "target": dict(_T_DICT), "weights": dict(W),
        "mesh": {"epw": 8.0, "quadrants": "1", "dof_cap_screen": 5000,
                 "dof_cap_verify": 7000, "dof_cap_final": 8900,
                 "dof_per_triangle": 0.51},
        "solve": {"backend": "beat_cuda", "distance_m": 2.0, "angle_count": 73,
                  "balloon": True, "balloon_points_screen": 512,
                  "balloon_points_verify": 1024, "gmres_tol": 1.0e-05,
                  "timeout_s": 900},
        "search": {"algorithm": "cma", "sigma0": 0.25, "seed": 1234, "budget": 100,
                   "popsize": None, "tolfun": 0.001},
    }, sort_keys=False), encoding="utf-8")

    def _brief(name, payload):
        p = d / name
        p.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return p

    with_v = load_config(typ, brief=_brief("with.yaml", _brief_payload(f0_v=1500.0)))
    without = load_config(typ, brief=_brief("without.yaml", _brief_payload()))
    assert with_v.raw["feasibility"]["f0_v_hz"] == 1500.0
    assert "f0_v_hz" not in without.raw["feasibility"]
