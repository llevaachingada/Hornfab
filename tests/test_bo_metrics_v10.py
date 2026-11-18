"""BO metric policy for objective v10 (2026-11-18 PR-D, staged with PR-A; owner-gated).

Pinned: the v4/v7 ``freeze_metric_policy`` still refuses v10; the separate v10 policy is a
distinct, deterministic metric identity; its observations are the v9 profile coverage cost and
the declared-region ripple; and a cohort never mixes v7/v9/v10 labels.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.bo.cohort import validate_cohort
from hornlab_search.bo.metrics import (
    METRIC_SCHEMA_V10,
    assert_single_objective_cohort,
    freeze_metric_policy,
    freeze_metric_policy_v10,
    measure_metrics_v10,
)
from hornlab_search.objective.replay import Brief
from hornlab_search.objective.scalar_v9 import V9_WEIGHTED_KEYS, V9Params, _cov_profile_term
from hornlab_search.objective.scalar_v10 import V10Params, _rip_term_v10
from hornlab_search.targets.spec import Target

ONES = {k: 1.0 for k in V9_WEIGHTED_KEYS}
F = np.array([500.0, 1000.0, 2000.0, 4000.0])
ANG = np.linspace(-90.0, 90.0, 73)


def _row(hz, pref, lo, hi):
    return {"hz": hz, "preferred_deg": pref, "min_deg": lo, "max_deg": hi}


def _target() -> Target:
    return Target.from_dict({
        "coverage_h_deg": 80.0, "coverage_v_deg": 50.0, "band_lo_hz": 700.0,
        "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0, "z_min": 0.0,
        "coverage_profile": {"mode": "corridor", "interpolation": "log_frequency",
                             "h": [_row(700.0, 80.0, 70.0, 90.0), _row(8000.0, 80.0, 70.0, 90.0)],
                             "v": [_row(700.0, 50.0, 40.0, 60.0), _row(8000.0, 50.0, 40.0, 60.0)]}})


def _brief(region="preferred_edge", version=10):
    block = {"version": version, "tolerances": dict(ONES)}
    if version == 10:
        block["ripple_region"] = region
        params = V10Params.from_block(block)
    else:
        params = V9Params.from_block(block)
    return Brief("v10fixture", _target(), {}, version, block, params)


def _metrics(bw_h=85.0):
    return SimpleNamespace(freqs_hz=F.copy(), bw_h_deg=np.full(4, bw_h), bw_v_deg=np.full(4, 50.0),
                           di_db=np.full(4, 6.0), on_axis_db=np.zeros(4),
                           ripple_h_db=np.ones(4), ripple_v_db=np.ones(4))


def _response(bump_deg=None):
    h = -6.0206 * (ANG / 40.0) ** 2
    v = -6.0206 * (ANG / 25.0) ** 2
    if bump_deg is not None:
        h = h.copy()
        h[np.isclose(np.abs(ANG), bump_deg)] += 3.0
    return SimpleNamespace(freqs_hz=F.copy(), h_angles_deg=ANG, v_angles_deg=ANG,
                           spl_h_db=np.array([h] * 4), spl_v_db=np.array([v] * 4),
                           axis_index=36, balloon_dirs=None, spl_balloon_db=None)


def test_v4_v7_policy_still_refuses_v10():
    with pytest.raises(ValueError, match="v4 or v7"):
        freeze_metric_policy(_brief(), F)


def test_v10_policy_refuses_other_versions():
    with pytest.raises(ValueError, match="v10"):
        freeze_metric_policy_v10(_brief(version=9), F)


def test_v10_policy_is_a_distinct_deterministic_identity():
    a = freeze_metric_policy_v10(_brief(), F)
    b = freeze_metric_policy_v10(_brief(), F)
    assert a.physical_metric_spec_hash == b.physical_metric_spec_hash      # stable
    assert a.payload["schema"] == METRIC_SCHEMA_V10 and a.payload["objective_version"] == 10
    assert a.payload["ripple_region"] == {"mode": "preferred_edge"}
    other = {freeze_metric_policy_v10(_brief(r), F).physical_metric_spec_hash for r in (
        "min_edge", {"mode": "seat_zone_deg", "h_deg": 100.0, "v_deg": 60.0})}
    assert a.physical_metric_spec_hash not in other and len(other) == 2
    part = freeze_metric_policy_v10(_brief(), F, restricted_mask=np.array([True, True, False, True]),
                                    restriction_name="shared")
    assert part.payload["status"] == "partial"
    assert part.physical_metric_spec_hash != a.physical_metric_spec_hash


def test_v10_observation_matches_the_objective_terms():
    p = freeze_metric_policy_v10(_brief(), F)
    m, r = _metrics(), _response(bump_deg=37.5)
    o = measure_metrics_v10(p, m, r)
    assert o.status == "complete", o.reason
    t = _target()
    band = (F >= 700.0) & (F <= 8000.0)
    params = V10Params.from_block(_brief().objective_block)
    assert o.coverage_deg == pytest.approx(_cov_profile_term(m, t, F, band, params.v9), rel=1e-12)
    assert o.ripple_db == pytest.approx(
        _rip_term_v10(m, r, t, F, band, {"mode": "preferred_edge"}), rel=1e-12)
    assert o.ripple_db > 0.05                       # the 37.5 deg bump is inside +/-40
    o_min = measure_metrics_v10(freeze_metric_policy_v10(_brief("min_edge"), F), m, r)
    assert o_min.ripple_db == pytest.approx(0.0, abs=1e-9)


def test_v10_measure_refusals():
    p = freeze_metric_policy_v10(_brief(), F)
    assert measure_metrics_v10(p, _metrics(), None).status == "capability_missing"
    m = _metrics()
    m.bw_v_deg[2] = np.nan
    assert measure_metrics_v10(p, m, _response()).status == "capability_missing"
    tampered = type(p)(p.payload_json.replace("preferred_edge", "min_edge"),
                       p.physical_metric_spec_hash)
    assert measure_metrics_v10(tampered, _metrics(), _response()).reason == \
        "metric policy hash mismatch"


def test_cohort_never_mixes_v7_v9_v10_labels():
    p10 = freeze_metric_policy_v10(_brief(), F)
    assert assert_single_objective_cohort([10, 10, p10]) == 10
    for mix in ([7, 10], [9, 10], [7, 9], [p10, 9]):
        with pytest.raises(ValueError, match="mixed objective labels"):
            assert_single_objective_cohort(mix)
    for bad in ([], [8], [True], ["10"]):
        with pytest.raises(ValueError):
            assert_single_objective_cohort(bad)


def _cohort_helpers():
    path = Path(__file__).with_name("test_bo_cohort_gate.py")
    spec = importlib.util.spec_from_file_location("_cohort_gate_helpers", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_validate_cohort_refuses_v9_v10_and_v7_v10_mixes():
    h = _cohort_helpers()
    assert validate_cohort([h._versioned(0, 10), h._versioned(1, 10)], d=2).ok
    for other in (7, 9):
        res = validate_cohort([h._versioned(0, other), h._versioned(1, 10)], d=2)
        assert res.status == "incompatible"
