import numpy as np
import pytest

from hornlab_search.bo.extensions import TrustRegion, cost_aware_log_score, trust_box, update_trust_region, loading_margins


def test_cost_heuristic_includes_lognormal_variance_and_minimum_data():
    assert cost_aware_log_score([2], [1], [.5], n_observations=29)["status"] == "capability_missing"
    result = cost_aware_log_score([2], [1], [.5], n_observations=30)
    assert result["values"] == pytest.approx([.75])
    assert cost_aware_log_score([2], [1], [-1], n_observations=30)["status"] == "capability_missing"


def test_trust_region_updates_and_never_updates_on_infrastructure():
    state = TrustRegion((.5, .5), 10.)
    lo, hi = trust_box(state, [1., 4.])
    assert lo == pytest.approx([.3, 0]) and hi == pytest.approx([.7, 1])
    for j in (9., 8., 7.):
        state = update_trust_region(state, outcome="measured", candidate=[.4, .6], J=j)
    assert state.length == 1.6 and state.successes == 0
    before = state
    state = update_trust_region(state, outcome="infrastructure_failure")
    assert state.status == "paused" and state.iteration == before.iteration
    assert state.failures == before.failures


def test_refusals_shrink_and_subthreshold_best_is_preserved():
    state = TrustRegion((.5,), 10.)
    state = update_trust_region(state, outcome="measured", candidate=[.6], J=9.999)
    assert state.center == (.6,) and state.best_j == 9.999 and state.failures == 1
    for _ in range(3):
        state = update_trust_region(state, outcome="geometry_refusal")
    assert state.length == .4 and state.failures == 0
    with pytest.raises(ValueError):
        update_trust_region(state, outcome="unknown")


def test_loading_margins_match_canonical_gate_and_refuse_missing_crossing():
    from types import SimpleNamespace
    from hornlab_search.targets.spec import Target
    t = Target(50, 50, 100, 4000, None, z_min=.5, f0_hz=1000, loaded_hi_hz=3000)
    f = np.array([100., 300., 500., 1000., 2000., 3000., 4000.])
    good = np.array([.1, .3, .6, .7, .8, .9, 1.])
    out = loading_margins(f, good, t, SimpleNamespace())
    assert out["status"] == "ok" and out["feasible"]
    bad = good.copy(); bad[4] = .4
    out = loading_margins(f, bad, t, SimpleNamespace())
    assert out["status"] == "ok" and not out["feasible"] and out["margins"][1] > 0
    assert loading_margins(f, np.full_like(f, .1), t, SimpleNamespace())["status"] == "constraint_model_unavailable"
