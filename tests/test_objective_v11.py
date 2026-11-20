"""Objective v11 (2026-11-20, owner-directed): v10 plus the ``objective.cd`` CD matrix.

Offline, CPU only, synthetic MetricSets/Responses. Pinned here:

* ``V11Params.from_block`` round-trips the normalised block and refuses a missing/unknown ``cd``,
  a bad CD weight/tolerance, a bad reference, an out-of-range angle and a non-increasing band;
* a synthetic balloon and a cuts-only Response both score a finite J with every v11 key, and the
  numeric ``cd_status_code`` distinguishes them (balloon vs cuts fallback);
* a v10 penalty propagates as a v11 penalty carrying every v11 key;
* ``worst_valid_v11_j`` stays far below ``PENALTY_INVALID``;
* changing any CD tolerance/weight changes the score identity;
* a synthetic stored record replays under v11 to exactly the in-process score.

The CD maths itself lives in ``metrics/cd.py`` and is tested by ``tests/test_metrics_cd.py``; this
file pins the objective integration.
"""
from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from hornlab_search.metrics.di import target_di_gaussian_db
from hornlab_search.objective.replay import _arrays_from_response, replay_record
from hornlab_search.objective.scalar_v9 import V9_WEIGHTED_KEYS
from hornlab_search.objective.scalar_v11 import (
    CD_OMEGA_2PI_UNMEASURABLE,
    CD_STATUS_BALLOON,
    CD_STATUS_CUTS_FALLBACK,
    CD_STATUS_UNMEASURABLE,
    V11_ALL_KEYS,
    V11Params,
    objective_v11,
    v11_score_identity,
    worst_valid_v11_j,
)
from hornlab_search.objective.terms import PENALTY_FAILED, PENALTY_INVALID
from hornlab_search.objective.versions import SUPPORTED_OBJECTIVE_VERSIONS
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet, Response

ONES = {k: 1.0 for k in V9_WEIGHTED_KEYS}
_T = {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0, "band_lo_hz": 700.0,
      "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0,
      "f0_hz": 700.0}
F = np.array([700.0, 1000.0, 2000.0, 2500.0, 3150.0, 4000.0, 5000.0, 6300.0, 8000.0])
ANG = np.linspace(-90.0, 90.0, 73)          # 2.5 deg spacing; includes the CD off-axis angles

#: The v11 brief weights: physical guards full, tonal/bumpiness terms reduced.
V11_WEIGHTS = {"cov_profile": 1.0, "rip": 0.5, "flat": 0.5, "load": 1.0, "dislope": 0.5,
               "di_roughness": 0.5, "flat_cv": 0.5}


def _row(hz, pref, lo=None, hi=None):
    out = {"hz": hz, "preferred_deg": pref}
    if lo is not None:
        out["min_deg"], out["max_deg"] = lo, hi
    return out


def _target() -> Target:
    return Target.from_dict({**_T, "coverage_profile": {
        "mode": "corridor", "interpolation": "log_frequency",
        "h": [_row(700.0, 80.0, 70.0, 90.0), _row(8000.0, 80.0, 70.0, 90.0)],
        "v": [_row(700.0, 50.0, 40.0, 60.0), _row(8000.0, 50.0, 40.0, 60.0)]}})


def _cd_block(**over) -> dict:
    block = {
        "band_hz": [700.0, 8000.0],
        "window_h_deg": 30.0,
        "window_v_deg": 10.0,
        "lw": {"weight": 1.5, "tolerance_db": 1.5},
        "di_std": {"weight": 0.75, "tolerance_db": 1.0},
        "nacc": {"weight": 0.75, "tolerance": 0.02},
        "offaxis": {"weight": 1.0, "tolerance_db": 1.0, "reference": "band_mean",
                    "band_hz": [2500.0, 8000.0],
                    "angles_h_deg": [-40, -30, 30, 40],
                    "angles_v_deg": [-25, -10, 10, 25]},
        "report": {"omega": True, "contour": False},
    }
    block.update(over)
    return block


def _block(**cd_over) -> dict:
    return {"version": 11, "tolerances": dict(ONES), "ripple_region": "preferred_edge",
            "cd": _cd_block(**cd_over)}


def _params(**cd_over) -> V11Params:
    return V11Params.from_block(_block(**cd_over))


def _metrics(target: Target) -> MetricSet:
    ref = target_di_gaussian_db(target.coverage_h_deg, target.coverage_v_deg)
    n = F.size
    return MetricSet(
        freqs_hz=F.copy(), bw_h_deg=np.full(n, 80.0), bw_v_deg=np.full(n, 50.0),
        di_db=np.full(n, ref), di_source="balloon",
        ripple_h_db=np.zeros(n), ripple_v_db=np.zeros(n), on_axis_db=np.zeros(n),
        z_throat_real=np.ones(n), scalars={})


def _balloon_dirs(n_theta=13, n_phi=24) -> np.ndarray:
    dirs = []
    for th in np.linspace(0.0, 180.0, n_theta):
        st, ct = math.sin(math.radians(th)), math.cos(math.radians(th))
        for ph in np.linspace(0.0, 360.0, n_phi, endpoint=False):
            dirs.append([st * math.cos(math.radians(ph)), st * math.sin(math.radians(ph)), ct])
    return np.asarray(dirs, dtype=float)


def _resp(balloon: bool, *, with_z: bool = True) -> Response:
    n, na = F.size, ANG.size
    sh = np.full((n, na), 90.0)
    sv = np.full((n, na), 90.0)
    if balloon:
        dirs = _balloon_dirs()
        spl_bal = np.full((n, dirs.shape[0]), 90.0)
    else:
        dirs = None
        spl_bal = None
    return Response(
        freqs_hz=F.copy(), h_angles_deg=ANG.copy(), v_angles_deg=ANG.copy(),
        spl_h_db=sh, spl_v_db=sv, balloon_dirs=dirs, spl_balloon_db=spl_bal,
        z_throat=np.ones(n, dtype=complex) if with_z else None, meta={})


# ------------------------------------------------------------------ params / validation

def test_v11_params_round_trip_and_normalised_block():
    p = _params()
    block = p.to_block()
    assert block["version"] == 11 and "cd" in block
    assert block["ripple_region"] == {"mode": "preferred_edge"}
    assert V11Params.from_block(block).to_block() == block          # normalised round trip
    # v11 delegates v9/v10 fields through the wrapper.
    assert p.weighted_keys() == p.v10.weighted_keys()
    assert p.tolerances is p.v10.v9.tolerances


def test_cd_is_required_and_validated():
    with pytest.raises(ValueError, match="objective.cd"):
        V11Params.from_block({"version": 11, "tolerances": dict(ONES),
                              "ripple_region": "preferred_edge"})
    with pytest.raises(ValueError, match="version 11"):
        V11Params.from_block({**_block(), "version": 10})

    for bad in (
        _block(bogus=1),                                             # unknown key
        _block(lw={"weight": -1.0, "tolerance_db": 1.5}),            # negative weight
        _block(lw={"weight": 1.0, "tolerance_db": 0.0}),             # zero tolerance
        _block(nacc={"weight": 1.0, "tolerance": float("inf")}),     # non-finite tolerance
        _block(band_hz=[8000.0, 700.0]),                             # lo >= hi
        _block(window_h_deg=120.0),                                  # window beyond +-90
        _block(offaxis={"weight": 1.0, "tolerance_db": 1.0, "reference": "bad",
                        "band_hz": [2500.0, 8000.0],
                        "angles_h_deg": [-40, 40], "angles_v_deg": [-10, 10]}),
        _block(offaxis={"weight": 1.0, "tolerance_db": 1.0, "reference": "band_mean",
                        "band_hz": [2500.0, 8000.0],
                        "angles_h_deg": [-100.0, 40.0], "angles_v_deg": [-10, 10]}),
    ):
        with pytest.raises(ValueError):
            V11Params.from_block(bad)


# ------------------------------------------------------------------ scoring

def test_balloon_and_cuts_only_score_finite_j_with_all_keys():
    t = _target()
    p = _params()
    m = _metrics(t)

    j_bal, terms_bal = objective_v11(m, _resp(True), True, t, V11_WEIGHTS, p)
    assert math.isfinite(j_bal) and terms_bal["penalty"] == 0.0
    assert set(terms_bal) == set(V11_ALL_KEYS)
    assert terms_bal["cd_status_code"] == CD_STATUS_BALLOON
    assert all(isinstance(terms_bal[k], (int, float)) for k in V11_ALL_KEYS)

    j_cut, terms_cut = objective_v11(m, _resp(False), True, t, V11_WEIGHTS, p)
    assert math.isfinite(j_cut) and terms_cut["penalty"] == 0.0
    assert set(terms_cut) == set(V11_ALL_KEYS)
    assert terms_cut["cd_status_code"] == CD_STATUS_CUTS_FALLBACK
    assert terms_cut["cd_omega_2pi"] == pytest.approx(-1.0)   # report-only, not measurable


def test_missing_metrics_is_a_v11_penalty_with_every_key():
    t, p = _target(), _params()
    j, terms = objective_v11(None, None, False, t, V11_WEIGHTS, p)
    assert j == PENALTY_FAILED and terms["penalty"] == PENALTY_FAILED
    assert set(terms) == set(V11_ALL_KEYS)
    assert terms["cd_status_code"] == CD_STATUS_UNMEASURABLE
    assert terms["cd_omega_2pi"] == CD_OMEGA_2PI_UNMEASURABLE


def test_v10_penalty_propagates_as_v11_penalty():
    """A v10 failure row (here: no metrics) becomes the v11 penalty with the same n_in_band."""
    t, p = _target(), _params()
    _, terms = objective_v11(_metrics(t), _resp(True), False, t, V11_WEIGHTS, p)
    assert terms["penalty"] == PENALTY_FAILED
    assert terms["total"] == PENALTY_FAILED
    assert set(terms) == set(V11_ALL_KEYS)


def test_worst_valid_v11_j_is_below_the_refusal_penalty():
    worst = worst_valid_v11_j(_params(), V11_WEIGHTS)
    assert 0.0 < worst < PENALTY_INVALID
    assert worst < 0.5 * PENALTY_INVALID          # the config gate's stricter condition


def test_identity_changes_with_cd_tolerance_or_weight():
    base = v11_score_identity(_params())["sha256"]
    tol = v11_score_identity(_params(lw={"weight": 1.5, "tolerance_db": 2.0}))["sha256"]
    weight = v11_score_identity(_params(nacc={"weight": 0.5, "tolerance": 0.02}))["sha256"]
    assert base != tol and base != weight and tol != weight
    assert v11_score_identity(_params())["name"] == "objective_v11_cd_matrix"


def test_v11_is_registered_and_dispatched():
    from hornlab_search.search.evaluate import _OBJECTIVE_SCORERS
    assert 11 in SUPPORTED_OBJECTIVE_VERSIONS
    t = _target()
    j, terms = _OBJECTIVE_SCORERS[11](_metrics(t), _resp(True), t, V11_WEIGHTS,
                                      _params().to_block())
    assert math.isfinite(j) and terms["penalty"] == 0.0
    assert set(terms) == set(V11_ALL_KEYS)


# ------------------------------------------------------------------ replay parity

def test_synthetic_stored_record_replays_to_the_in_process_score():
    """Synthetic replay (not a stored run): the canonical replay dispatch under v11 equals the
    in-process ``objective_v11`` score on the same reconstructed Response/MetricSet."""
    t, p = _target(), _params()
    resp = _resp(True)
    m = _metrics(t)
    j_in, terms_in = objective_v11(m, resp, True, t, V11_WEIGHTS, p)

    arrays = _arrays_from_response(resp)
    arrays.update({
        "bw_h_deg": m.bw_h_deg, "bw_v_deg": m.bw_v_deg, "di_db": m.di_db,
        "ripple_h_db": m.ripple_h_db, "ripple_v_db": m.ripple_v_db,
        "on_axis_db": m.on_axis_db, "z_throat": np.ones(F.size, dtype=complex),
    })
    meta = {
        "ok": True, "design_hash": "d0", "mesh_hash": "m0", "solve_hash": "s0",
        "family": "OSSE", "params": {}, "mesh": {},
        "solve": {"backend": "synthetic", "freqs_hz": list(F)},
        "lib_shas": {}, "metrics_scalars": {"di_source": m.di_source},
        "objective": None, "objective_version": 11, "target": dataclasses.asdict(t),
    }
    result = replay_record(meta, arrays, target=t, weights=V11_WEIGHTS,
                           objective_params=p.to_block(), objective_version=11)
    assert result.j is not None, result.reasons
    assert math.isfinite(result.j)
    assert result.j == pytest.approx(j_in, rel=1e-12, abs=1e-12)
    assert result.terms is not None
    assert set(result.terms) == set(V11_ALL_KEYS)
