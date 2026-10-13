"""Stage A plumbing on SYNTHETIC labels (smooth analytic stand-in, NOT horn physics). These tests
prove the code path (features -> train -> gates -> evaluator -> NSGA-II); they say nothing about
the real gates, which need >= 500 held-out BEM records across families. Needs torch."""
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from hornlab_search.config import load_config
from hornlab_search.dataset.store import Y_METRIC_KEYS
from hornlab_search.design.space import DesignSpace
from hornlab_search.objective.scalar import objective
from hornlab_search.search.nsga import search_pareto
from hornlab_search.surrogate import gates
from hornlab_search.surrogate.features import cluster_holdout, unit_matrix
from hornlab_search.surrogate.predict import Surrogate
from hornlab_search.surrogate.train import train_surrogate
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

EX = Path(__file__).resolve().parents[1] / "examples" / "osse_baseline.yaml"
FREQS = np.linspace(500, 5500, 8)


def _synthetic(space, n, seed, scramble=False):
    rng = np.random.default_rng(seed)
    U = rng.random((n, len(space.keys())))
    X = np.stack([[space.bounds[k].from_unit(u) for k, u in zip(space.keys(), r)] for r in U])
    f = (FREQS / FREQS.max())[None, :]
    bw = 110 - 50 * U[:, [0]] * (1 - 0.3 * f) + 20 * U[:, [1]] + 0 * f
    di = 8 + 6 * U[:, [2]] + 4 * f + 3 * U[:, [0]]
    ym = {"bw_h_deg": bw, "bw_v_deg": bw * 0.7, "di_db": di,
          "ripple_h_db": 1 + 2 * U[:, [1]] + 0 * f, "ripple_v_db": 1 + 2 * U[:, [2]] + 0 * f,
          "on_axis_db": 3 * f * U[:, [3]]}
    if scramble:
        ym = {k: rng.permutation(v) for k, v in ym.items()}
    ok = U[:, 4] > 0.1                                     # a "can't mesh" corner
    for v in ym.values():
        v[~ok] = np.nan
    cfg = load_config(EX)
    target = Target.from_dict(cfg.target_raw)
    obj = np.full(n, np.nan)
    for i in np.flatnonzero(ok):
        m = MetricSet(FREQS, ym["bw_h_deg"][i], ym["bw_v_deg"][i], ym["di_db"][i], "balloon",
                      ym["ripple_h_db"][i], ym["ripple_v_db"][i], ym["on_axis_db"][i], None)
        obj[i] = objective(m, True, target, cfg.weights)[0]
    arrays = {"X": X.astype(np.float32), "key_names": space.keys(), "y_metrics": ym,
              "y_scalars": {"objective": obj}, "freqs_hz": FREQS,
              "family": np.array(["OSSE"] * n), "ok": ok}
    return arrays, target, cfg


@pytest.fixture(scope="module")
def setup():
    cfg = load_config(EX)
    space = DesignSpace.from_config(cfg)
    return cfg, space


def test_unit_matrix_roundtrip(setup):
    _, space = setup
    arrays, _, _ = _synthetic(space, 20, 0)
    U = unit_matrix(arrays["X"], arrays["key_names"], space)
    assert U.shape == (20, len(space.keys())) and U.min() >= 0 and U.max() <= 1


def test_cluster_holdout_fraction(setup):
    U = np.random.default_rng(0).random((400, 5))
    h = cluster_holdout(U, 0.15)
    assert 0.12 * 400 <= h.sum() <= 0.45 * 400


@pytest.mark.timeout(600)
def test_train_gates_evaluator_and_pareto(setup, tmp_path):
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 900, 1)
    sur, rep = train_surrogate(arrays, space, target, cfg.weights, ensemble=2, epochs=400,
                               out_path=tmp_path / "s.pt")
    assert rep["n_heldout"] >= 100
    # plumbing sanity on smooth labels: rank correlation is high and invalid corner is learned
    assert rep["gates"]["spearman"]["value"] > 0.8
    assert rep["gates"]["invalid_accuracy"]["value"] > 0.5
    assert not rep["pass"]                      # < 500 held-out: must never claim a real pass
    sur2 = Surrogate.load(tmp_path / "s.pt")    # frozen format round-trips exactly
    U = np.random.default_rng(2).random((5, len(space.keys()))).astype(np.float32)
    assert np.allclose(sur.predict(U)["di_db"], sur2.predict(U)["di_db"], atol=1e-5)
    front = search_pareto(cfg, tmp_path / "run", sur.evaluator(space, target, cfg.weights),
                          pop=16, gens=4, seed=0)
    assert front and (tmp_path / "run" / "pareto.json").exists()
    assert all(e.mesh_hash == "surrogate" for e in front)


@pytest.mark.timeout(600)
def test_scrambled_labels_fail_rank_gate(setup):
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 900, 3, scramble=True)
    _, rep = train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=200)
    assert not rep["gates"]["spearman"]["pass"]
    assert not rep["pass"]


@pytest.mark.timeout(600)
def test_propose_returns_unique_valid_designs(setup):
    from hornlab_search.surrogate import ismo
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 600, 5)
    sur, _ = train_surrogate(arrays, space, target, cfg.weights, ensemble=2, epochs=200)
    props = ismo.propose(sur, space, target, cfg.weights, n_top=5, n_var=3, pop=24, gens=3)
    hashes = [p["design"].hash() for p in props]
    assert len(hashes) == len(set(hashes)) and {"exploit", "explore"} >= {p["kind"] for p in props}
    assert any(p["kind"] == "exploit" for p in props)


def test_cli_surrogate_errors_and_propose(setup, tmp_path, capsys):
    from hornlab_search.cli import main
    cfg, space = setup
    rc = main(["surrogate", "train", "--config", str(EX), "--dataset-dir", str(tmp_path / "nope")])
    assert rc == 1 and "does not exist" in capsys.readouterr().out
    arrays, target, _ = _synthetic(space, 400, 7)
    train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=100,
                    out_path=tmp_path / "s.pt")
    rc = main(["surrogate", "propose", "--config", str(EX), "--out", str(tmp_path / "s.pt"),
               "--proposals", str(tmp_path / "p.json"), "--n-top", "3", "--n-var", "2"])
    assert rc == 0 and (tmp_path / "p.json").exists()
