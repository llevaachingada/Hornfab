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
