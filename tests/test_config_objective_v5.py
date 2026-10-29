"""Objective v5 config surface: block validation, defaults, the penalty-ordering guard, dispatch.

Offline, CPU only. v5 adds ``flat_cv`` to the tolerance set and four scoring constants to the
objective block; every one is validated here (a typo must never be silent). v4's block and
dispatch stay exactly as they were.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from hornlab_search.config import ConfigError, _validate_objective_block, load_config
from hornlab_search.objective import DEFAULT_WEIGHTS
from hornlab_search.objective.scalar_v4 import V4_ALL_KEYS, V4_WEIGHTED_KEYS, V4Params
from hornlab_search.objective.scalar_v5 import (
    V5_ALL_KEYS,
    V5_WEIGHTED_KEYS,
    V5Params,
    worst_valid_j,
)
from hornlab_search.targets.spec import Target

ONES = {k: 1.0 for k in V5_WEIGHTED_KEYS}
V4_ONES = {k: 1.0 for k in V4_WEIGHTED_KEYS}
W = dict(DEFAULT_WEIGHTS)
_T = {"coverage_h_deg": 90.0, "coverage_v_deg": 60.0, "band_lo_hz": 300.0, "band_hi_hz": 12000.0,
      "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0}


# ------------------------------------------------------------------ block validation

def test_v5_block_round_trips_with_its_defaults():
    out = _validate_objective_block({"version": 5, "tolerances": ONES}, "b.yaml")
    assert out["version"] == 5
    assert out["cov_narrow_ratio"] == 2.0
    assert out["cov_below_f0"] == "mask" and out["diag_reference"] == "round"
    assert out["loaded_re_z"] == 0.50 and out["lfp_re_z"] == 0.20
    assert out["lfp_crossover_ratio"] == 1.6 and out["bw8k_floor"] == 0.75
    assert out["tolerances"] == ONES
    # A brief may override every constant; the normalised block carries the choice.
    over = _validate_objective_block(
        {"version": 5, "tolerances": ONES, "loaded_re_z": 0.4, "lfp_re_z": 0.15,
         "lfp_crossover_ratio": 2.0, "bw8k_floor": 0.8, "cov_narrow_ratio": 1.5,
         "cov_below_f0": "one_sided", "diag_reference": "round"}, "b.yaml")
    assert over["loaded_re_z"] == 0.4 and over["lfp_re_z"] == 0.15
    assert over["lfp_crossover_ratio"] == 2.0 and over["bw8k_floor"] == 0.8
    assert over["cov_narrow_ratio"] == 1.5 and over["cov_below_f0"] == "one_sided"


def test_v5_requires_a_tolerance_for_every_key_including_flat_cv():
    for k in V5_WEIGHTED_KEYS:
        tol = {j: 1.0 for j in V5_WEIGHTED_KEYS if j != k}
        with pytest.raises(ConfigError, match="missing"):
            _validate_objective_block({"version": 5, "tolerances": tol}, "b.yaml")


def test_v5_refuses_unknown_tolerance_and_block_keys():
    with pytest.raises(ConfigError, match="unknown"):
        _validate_objective_block({"version": 5, "tolerances": {**ONES, "lfp": 1.0}}, "b.yaml")
    with pytest.raises(ConfigError, match="unknown key"):
        _validate_objective_block({"version": 5, "tolerances": ONES, "load_rez": 1.0}, "b.yaml")
    with pytest.raises(ConfigError, match="unknown key"):
        _validate_objective_block({"version": 5, "tolerances": ONES, "vasym": 1.0}, "b.yaml")


@pytest.mark.parametrize("key", ["loaded_re_z", "lfp_re_z", "lfp_crossover_ratio", "bw8k_floor"])
@pytest.mark.parametrize("bad", [0, -1.0, float("nan"), float("inf"), True, "2", None])
def test_v5_refuses_bad_scoring_constants(key, bad):
    with pytest.raises(ConfigError, match=f"objective.{key}"):
        _validate_objective_block({"version": 5, "tolerances": ONES, key: bad}, "b.yaml")


@pytest.mark.parametrize("bad", [0, -1.0, float("nan"), True, "2"])
def test_v5_refuses_bad_cov_narrow_ratio(bad):
    with pytest.raises(ConfigError, match="cov_narrow_ratio"):
        _validate_objective_block({"version": 5, "tolerances": ONES, "cov_narrow_ratio": bad},
                                  "b.yaml")


def test_v5_refuses_bad_choices():
    with pytest.raises(ConfigError, match="cov_below_f0"):
        _validate_objective_block({"version": 5, "tolerances": ONES, "cov_below_f0": "free"},
                                  "b.yaml")
    with pytest.raises(ConfigError, match="diag_reference"):
        _validate_objective_block({"version": 5, "tolerances": ONES, "diag_reference": "square"},
                                  "b.yaml")


# ------------------------------------------------------------------ v4 unchanged

def test_v4_block_and_dispatch_are_untouched():
    out = _validate_objective_block({"version": 4, "tolerances": V4_ONES}, "b.yaml")
    assert out["version"] == 4 and out["cov_narrow_ratio"] == 1.0
    assert set(out["tolerances"]) == set(V4_WEIGHTED_KEYS)
    assert _validate_objective_block({"version": 3}, "b.yaml") == {"version": 3}
    with pytest.raises(ConfigError, match="unknown"):
        _validate_objective_block({"version": 3, "tolerances": V4_ONES}, "b.yaml")
    with pytest.raises(ConfigError, match="1, 2, 3, 4 or 5"):
        _validate_objective_block({"version": 6}, "b.yaml")
    from hornlab_search.search.evaluate import _OBJECTIVE_SCORERS, _score_v4

    assert _OBJECTIVE_SCORERS[4] is _score_v4          # the v4 scorer object did not move


def test_v5_penalty_ordering_guard_is_checked_at_load(tmp_path):
    tol = dict(ONES, load=1e-3)
    typ, brief = _write_cfg(tmp_path, {"version": 5, "tolerances": tol}, {**W, "load": 0.5})
    with pytest.raises(ConfigError, match="refusal penalty"):
        load_config(typ, brief=brief)
    # The same tolerances with load off are fine.
    typ2, brief2 = _write_cfg(tmp_path / "ok", {"version": 5, "tolerances": tol}, dict(W))
    cfg = load_config(typ2, brief=brief2)
    assert worst_valid_j(V5Params.from_block(cfg.objective_params), cfg.weights) < 500.0


# ------------------------------------------------------------------ end to end

def _write_cfg(tmp_path, objective, weights):
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    typ = tmp_path / "typ.yaml"
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
    brief = tmp_path / "brief.yaml"
    brief.write_text(yaml.safe_dump({
        "name": "v5", "description": "v5 test brief",
        "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 5.0},
        "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0, "max_depth_mm": 220.0},
        "symmetry": "hv", "target": {**_T, "f0_hz": 300.0}, "weights": weights,
        "objective": objective}, sort_keys=False), encoding="utf-8")
    return typ, brief


def _metrics(f, t: Target):
    from hornlab_search.metrics.di import target_di_gaussian_db
    from hornlab_search.types import MetricSet

    ref = target_di_gaussian_db(t.coverage_h_deg, t.coverage_v_deg)
    return MetricSet(freqs_hz=np.asarray(f, dtype=float),
                     bw_h_deg=np.full(np.size(f), 80.0), bw_v_deg=np.full(np.size(f), 60.0),
                     di_db=np.full(np.size(f), ref), di_source="balloon",
                     ripple_h_db=np.zeros(np.size(f)), ripple_v_db=np.zeros(np.size(f)),
                     on_axis_db=np.zeros(np.size(f)), z_throat_real=None, scalars={})


def test_load_config_carries_v5_params_and_the_scorer_dispatches(tmp_path):
    from hornlab_search.search.evaluate import _score, make_context

    typ, brief = _write_cfg(tmp_path, {"version": 5, "tolerances": ONES}, dict(W))
    cfg = load_config(typ, brief=brief)
    assert cfg.objective_version == 5
    assert cfg.objective_params["version"] == 5
    ctx = make_context(cfg, lib_shas={})
    assert isinstance(ctx.objective_params, V5Params)
    assert ctx.objective_params.cov_narrow_ratio == 2.0
    f = np.geomspace(300.0, 12000.0, 9)
    j, terms = _score(_metrics(f, ctx.target), None, ctx)
    assert set(terms) == set(V5_ALL_KEYS) and j > 0.0


def test_load_config_still_carries_v4_params(tmp_path):
    from hornlab_search.search.evaluate import make_context

    typ, brief = _write_cfg(tmp_path, {"version": 4, "tolerances": V4_ONES}, dict(W))
    cfg = load_config(typ, brief=brief)
    assert cfg.objective_version == 4 and cfg.objective_params["version"] == 4
    ctx = make_context(cfg, lib_shas={})
    assert isinstance(ctx.objective_params, V4Params)
    assert set(ctx.objective_params.tolerances) == set(V4_WEIGHTED_KEYS)
    assert set(V4_ALL_KEYS) - set(V5_ALL_KEYS) == set()
