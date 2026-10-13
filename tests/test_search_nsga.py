"""NSGA-II core (numpy) and the surrogate gates. Offline, no solver."""
import numpy as np

from hornlab_search.search.nsga import (crowding_distance, fast_nondominated_sort, nsga2)
from hornlab_search.surrogate import gates


def test_nondominated_sort_known_fronts():
    F = np.array([[1, 4], [2, 2], [4, 1], [3, 3], [5, 5]], float)
    fr = fast_nondominated_sort(F)
    assert sorted(fr[0].tolist()) == [0, 1, 2]
    assert fr[1].tolist() == [3] and fr[2].tolist() == [4]


def test_crowding_boundaries_infinite():
    d = crowding_distance(np.array([[0, 3], [1, 2], [3, 0]], float))
    assert np.isinf(d[0]) and np.isinf(d[2]) and np.isfinite(d[1])


def test_nsga2_converges_on_zdt1_like_front():
    def f(U):
        g = 1 + 9 * U[:, 1:].mean(1)
        return np.stack([U[:, 0], g * (1 - np.sqrt(U[:, 0] / g))], 1)
    r = nsga2(f, 5, pop=40, gens=60, seed=1)
    front = r["F"][r["front"]]
    assert len(front) >= 10
    # true front has g=1: f2 = 1 - sqrt(f1)
    assert np.mean(np.abs(front[:, 1] - (1 - np.sqrt(front[:, 0])))) < 0.05
    assert r["n_evals"] == 40 * 61


def test_nsga2_deterministic():
    f = lambda U: np.stack([U[:, 0], 1 - U[:, 0] + U[:, 1]], 1)
    a, b = nsga2(f, 2, pop=20, gens=10, seed=3), nsga2(f, 2, pop=20, gens=10, seed=3)
    assert np.array_equal(a["X"], b["X"])


def test_gates_perfect_and_broken():
    rng = np.random.default_rng(0)
    t = rng.random(600)
    ok = np.ones(600, bool); ok[:60] = False
    good = gates.evaluate_gates(obj_pred=t, obj_true=t, bw_pred=t, bw_true=t, di_pred=t,
                                di_true=t, p_ok=ok.astype(float), ok_true=ok, flips=0,
                                n_heldout=600)
    assert good["pass"] and not good["warnings"]
    bad = gates.evaluate_gates(obj_pred=-t + rng.random(600), obj_true=t, bw_pred=t + 5,
                               bw_true=t, di_pred=t, di_true=t, p_ok=np.ones(600), ok_true=ok,
                               flips=3, n_heldout=600)
    assert not bad["pass"] and not bad["gates"]["spearman"]["pass"]
    assert not bad["gates"]["invalid_accuracy"]["pass"]


def test_small_heldout_never_passes():
    t = np.arange(50.0)
    r = gates.evaluate_gates(obj_pred=t, obj_true=t, bw_pred=t, bw_true=t, di_pred=t, di_true=t,
                             p_ok=np.ones(50), ok_true=np.ones(50, bool), flips=0, n_heldout=50)
    assert r["warnings"] and not r["pass"]


def test_topk_overlap_and_sweeps():
    t = np.arange(100.0)
    assert gates.topk_overlap(t, t) == 20
    assert gates.topk_overlap(-t, t) == 0
    mono = gates.sweep_sign_flips(lambda U: U[:, 0] + U[:, 1], 2, n_sweeps=20)
    assert mono["flips"] == 0
    zig = gates.sweep_sign_flips(lambda U: np.sin(40 * U[:, 0]) + np.sin(40 * U[:, 1]), 2,
                                 n_sweeps=20, steps=21)
    assert zig["flips"] > 0
