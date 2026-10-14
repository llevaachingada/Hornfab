import numpy as np

from hornlab_search.surrogate import ismo


def test_round_report_working_and_not():
    t = np.arange(40.0)
    ok = ismo.round_report(t, t, np.arange(40.0) + 50)
    assert ok["working"] and ok["spearman_on_proposals"] > 0.99
    bad = ismo.round_report(t, t, np.arange(40.0) - 50)   # random designs were better
    assert not bad["working"]
    nan = ismo.round_report(t, np.full(40, np.nan), t)
    assert not nan["working"] and nan["n"] == 0


def test_round_report_penalty_is_a_failed_proposal():
    """A failed BEM proposal arrives as the finite penalty 1e3, not NaN; it must be treated as
    unsolved, not as a real objective dragging the median."""
    from hornlab_search.objective.terms import PENALTY_FAILED
    t = np.arange(40.0)
    tj = t.copy()
    tj[0] = PENALTY_FAILED
    r = ismo.round_report(t, tj, t + 50)
    assert r["n_solved_failed"] == 1 and r["n"] == 39
    assert np.isfinite(r["median_true_J"]) and r["working"]

