"""Stage A plumbing on SYNTHETIC labels (smooth analytic stand-in, NOT horn physics). These tests
prove the code path (features -> train -> gates -> evaluator -> NSGA-II); they say nothing about
the real gates, which need >= 500 held-out BEM records across families. Needs torch."""
import copy
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from hornlab_search.config import load_config, mode_freqs
from hornlab_search.dataset.store import Y_METRIC_KEYS
from hornlab_search.design.space import Bound, DesignSpace
from hornlab_search.objective.scalar import objective
from hornlab_search.search.nsga import search_pareto
from hornlab_search.surrogate import gates
from hornlab_search.surrogate.features import cluster_holdout, unit_matrix
from hornlab_search.surrogate.model import load_bundle
from hornlab_search.surrogate.predict import Surrogate
from hornlab_search.surrogate.train import _recompute_true_objectives, train_surrogate
from hornlab_search.targets.spec import Target
from hornlab_search.types import MetricSet

EX = Path(__file__).resolve().parents[1] / "examples" / "osse_baseline.yaml"


def _screen_freqs(cfg):
    """The grid the config solves on, so a synthetic bundle matches the frozen config contract."""
    return np.asarray(mode_freqs("screen", cfg), float)


def _synthetic(space, n, seed, scramble=False):
    rng = np.random.default_rng(seed)
    cfg = load_config(EX)
    freqs = _screen_freqs(cfg)
    U = rng.random((n, len(space.keys())))
    X = np.stack([[space.bounds[k].from_unit(u) for k, u in zip(space.keys(), r)] for r in U])
    f = (freqs / freqs.max())[None, :]
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
    target = Target.from_dict(cfg.target_raw)
    obj = np.full(n, np.nan)
    for i in np.flatnonzero(ok):
        m = MetricSet(freqs, ym["bw_h_deg"][i], ym["bw_v_deg"][i], ym["di_db"][i], "balloon",
                      ym["ripple_h_db"][i], ym["ripple_v_db"][i], ym["on_axis_db"][i], None)
        obj[i] = objective(m, True, target, cfg.weights)[0]
    arrays = {"X": X.astype(np.float32), "key_names": space.keys(), "y_metrics": ym,
              "y_scalars": {"objective": obj}, "freqs_hz": freqs,
              "design_hash": np.array([f"synth{i:06d}" for i in range(n)], dtype=str),
              "family": np.array(["OSSE"] * n), "ok": ok}
    return arrays, target, cfg


def _dup_rows(arrays, reps):
    """Rebuild an arrays dict taking ``reps`` (indices) from every aligned array."""
    def take(v):
        return np.asarray(v)[reps]

    out = dict(arrays)
    out["X"] = take(arrays["X"])
    out["ok"] = take(arrays["ok"])
    out["design_hash"] = take(arrays["design_hash"])
    out["family"] = take(arrays["family"])
    out["y_metrics"] = {k: take(v) for k, v in arrays["y_metrics"].items()}
    out["y_scalars"] = {k: take(v) for k, v in arrays["y_scalars"].items()}
    return out



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
    # the synthetic model does NOT pass the real gates, so the CLI refuses unless overridden
    rc = main(["surrogate", "propose", "--config", str(EX), "--out", str(tmp_path / "s.pt"),
               "--proposals", str(tmp_path / "p.json"), "--n-top", "3", "--n-var", "2"])
    assert rc == 1 and "REFUSED" in capsys.readouterr().out
    rc = main(["surrogate", "propose", "--config", str(EX), "--out", str(tmp_path / "s.pt"),
               "--proposals", str(tmp_path / "p.json"), "--n-top", "3", "--n-var", "2",
               "--allow-unvalidated"])
    assert rc == 0 and (tmp_path / "p.json").exists()
    assert not (tmp_path / "p.json.tmp").exists()      # atomic write left no temp file behind


def test_bundle_freezes_gate_verdict_and_config(setup, tmp_path):
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 300, 9)
    _, rep = train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=80,
                             out_path=tmp_path / "s.pt")
    meta = load_bundle(tmp_path / "s.pt")["meta"]
    assert isinstance(meta["gate_report"]["gates_passed"], bool)
    assert meta["gate_report"]["n_heldout"] == rep["n_heldout"]
    assert set(meta["gate_report"]["gates"]) == set(rep["gates"])
    assert meta["family"] == space.family and meta["keys"] == list(space.keys())
    assert meta["bounds"]["a_deg"] == {"lo": space.bounds["a_deg"].lo,
                                       "hi": space.bounds["a_deg"].hi,
                                       "log": space.bounds["a_deg"].log}
    assert np.allclose(meta["freqs_hz"], _screen_freqs(cfg))


def test_keeps_existing_passing_bundle_on_failed_retrain(setup, tmp_path):
    """A retrain that fails must not clobber a bundle whose stored verdict passed."""
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 200, 21)
    out = tmp_path / "s.pt"
    train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=40, out_path=out)
    b = load_bundle(out)
    b["meta"]["gate_report"]["gates_passed"] = True    # pretend a validated model is on disk
    from hornlab_search.surrogate.model import save_bundle
    save_bundle(out, states=b["states"], meta=b["meta"], mu=b["mu"], sd=b["sd"])
    assert load_bundle(out)["meta"]["gate_report"]["gates_passed"] is True
    # a fresh failing run to the SAME path must keep the passing file
    _, rep = train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=20,
                             out_path=out)
    assert rep["pass"] is False and rep["kept_existing_bundle"] is True and rep["saved"] is False
    assert load_bundle(out)["meta"]["gate_report"]["gates_passed"] is True


def test_propose_refuses_after_bounds_change(setup):
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 120, 4)
    sur, _ = train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=30)
    assert sur.config_mismatch(space, freqs_hz=_screen_freqs(cfg)) is None
    other = copy.deepcopy(space)
    b = other.bounds["a_deg"]
    other.bounds["a_deg"] = Bound(lo=b.lo + 1.0, hi=b.hi, search=b.search, log=b.log)
    msg = sur.config_mismatch(other, freqs_hz=_screen_freqs(cfg))
    assert msg is not None and "bounds" in msg and "a_deg" in msg
    # a different frequency grid is named too
    fmsg = sur.config_mismatch(space, freqs_hz=np.linspace(500, 5500, 8))
    assert fmsg is not None and "freqs_hz" in fmsg


def test_cli_propose_refuses_missing_verdict(setup, tmp_path, capsys):
    from hornlab_search.cli import main
    from hornlab_search.surrogate.model import load_bundle, save_bundle
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 150, 17)
    out = tmp_path / "s.pt"
    train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=30, out_path=out)
    b = load_bundle(out)
    b["meta"].pop("gate_report", None)                 # simulate a pre-verdict bundle
    save_bundle(out, states=b["states"], meta=b["meta"], mu=b["mu"], sd=b["sd"])
    rc = main(["surrogate", "propose", "--config", str(EX), "--out", str(out),
               "--proposals", str(tmp_path / "p.json")])
    assert rc == 1 and "REFUSED" in capsys.readouterr().out


def test_duplicate_rows_dropped_before_holdout(setup):
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 120, 11)
    reps = np.concatenate([np.arange(120), np.arange(0, 120, 4)])       # 30 duplicate rows
    dup = _dup_rows(arrays, reps)
    sur, rep = train_surrogate(dup, space, target, cfg.weights, ensemble=1, epochs=30)
    assert rep["n_duplicates_dropped"] == 30
    assert sur.meta["n_duplicates_dropped"] == 30
    assert rep["n_heldout"] + sur.meta["n_train"] == 120                 # holdout ran on 120, not 150


@pytest.mark.timeout(300)
def test_rank_gate_uses_recomputed_true_objective(setup):
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 600, 1)
    held = np.ones(arrays["X"].shape[0], bool)
    rec = _recompute_true_objectives(arrays, held, target, cfg.weights)
    stored = np.asarray(arrays["y_scalars"]["objective"], float)
    m = np.isfinite(stored)
    assert np.allclose(rec[m], stored[m], atol=1e-9)                     # recompute == objective()
    # a corrupted stored objective must not change the recomputed labels
    bad = dict(arrays)
    bad["y_scalars"] = {"objective": np.zeros_like(stored)}
    rec2 = _recompute_true_objectives(bad, held, target, cfg.weights)
    assert np.allclose(rec2[m], stored[m], atol=1e-9)
    _, rep = train_surrogate(bad, space, target, cfg.weights, ensemble=1, epochs=80)
    assert rep["objective_delta_max"] > 0                                # drift is reported
    assert np.isfinite(rep["gates"]["spearman"]["value"])

