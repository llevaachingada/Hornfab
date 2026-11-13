from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.bo.metrics import freeze_metric_policy, measure_metrics
from hornlab_search.objective.replay import Brief
from hornlab_search.objective.scalar_v4 import V4_WEIGHTED_KEYS
from hornlab_search.targets.spec import Target


def fixture():
    target = Target(50, 50, 300, 4000, None, f0_hz=1000, f0_v_hz=2000,
                    freq_weights={"band_hz": [[2000, 4000, 2]]})
    block = {"version": 4, "tolerances": {k: 1 for k in V4_WEIGHTED_KEYS},
             "cov_narrow_ratio": 2, "cov_below_f0": "mask", "diag_reference": "round"}
    brief = Brief("fixture", target, {}, 4, block, None)
    f = np.array([500., 1000., 2000., 4000.])
    a = np.array([-30., -20., -15., -10., 0., 10., 15., 20., 30.])
    cuts = np.tile(-0.01 * a**2, (4, 1))
    response = SimpleNamespace(h_angles_deg=a, v_angles_deg=a, spl_h_db=cuts, spl_v_db=cuts,
                               axis_index=4, balloon_dirs=None, spl_balloon_db=None)
    metrics = SimpleNamespace(freqs_hz=f, bw_h_deg=np.full(4, 40.), bw_v_deg=np.full(4, 60.),
                              di_db=np.full(4, 6.), on_axis_db=np.zeros(4),
                              ripple_h_db=np.ones(4), ripple_v_db=np.ones(4))
    return brief, f, metrics, response


def test_resolved_ratio_and_frozen_support():
    b, f, m, r = fixture()
    p = freeze_metric_policy(b, f)
    o = measure_metrics(p, m, r)
    assert o.status == "complete", o.reason
    assert o.coverage_deg == pytest.approx(np.sqrt(300))
    assert o.ripple_db >= 0
    assert p.payload["masks"]["coverage_h"] == [False, True, True, True]
    assert p.payload["masks"]["coverage_v"] == [False, False, True, True]
    assert p.payload["weights"] == [1, 1, 2, 2]


def test_missing_bins_and_fallback_refused():
    b, f, m, r = fixture()
    p = freeze_metric_policy(b, f)
    m.bw_v_deg[2] = np.nan
    assert measure_metrics(p, m, r).status == "capability_missing"
    m.bw_v_deg[2] = 60
    assert measure_metrics(p, m, None).status == "capability_missing"
    r.spl_h_db = np.ones((1, 1))
    assert measure_metrics(p, m, r).status == "capability_missing"


def test_shared_restriction_is_partial_and_identified():
    b, f, m, r = fixture()
    full = freeze_metric_policy(b, f)
    p = freeze_metric_policy(b, f, restricted_mask=np.array([True, True, False, True]), restriction_name="shared")
    m.bw_v_deg[2] = np.nan
    assert measure_metrics(p, m, r).status == "partial"
    assert p.physical_metric_spec_hash != full.physical_metric_spec_hash
    with pytest.raises(ValueError):
        freeze_metric_policy(b, f, restricted_mask=np.zeros(4, dtype=bool), restriction_name="empty")


def test_invalid_weights_and_support_rejected():
    b, f, m, r = fixture()
    bad = replace(b, target=replace(b.target, freq_weights={"band_hz": [[1000, 2000, -1]]}))
    with pytest.raises(ValueError):
        freeze_metric_policy(bad, f)
    p = freeze_metric_policy(b, f)
    m.freqs_hz = f + 1
    assert measure_metrics(p, m, r).status == "capability_missing"

