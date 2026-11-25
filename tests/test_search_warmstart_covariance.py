"""P1b (senior optimizer audit, 2026-11-21): opt-in covariance-transfer warm start.

Covers the documented coordinate transform, the sampler injection (empirical covariance),
the end-to-end run.json record, byte-identical mean-only behaviour when the covariance block
is absent/false, and every refusal path. No solver/GPU: synthetic backend only.
"""
from __future__ import annotations

from pathlib import Path

import cma as cma_lib
import numpy as np
import pytest
import yaml

from hornlab_search.config import ConfigError, load_config
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.design.space import DesignSpace
from hornlab_search.search import cma as cma_mod
from hornlab_search.search import warmstart
from hornlab_search.search.evaluate import read_ndjson
from hornlab_search.search.rundir import read_json, write_json_atomic
from test_search_support import SyntheticBackend, fast_cfg, install_fakes


@pytest.fixture
def smoke_cfg_path():
    return Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml"


def _raw(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _warm_cfg(tmp_path, smoke_yaml, warm, name="cfg", mutate=None):
    raw = _raw(smoke_yaml)
    raw["search"]["warm_start"] = warm
    if mutate is not None:
        mutate(raw)
    p = tmp_path / f"{name}.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def _source_run(tmp_path, monkeypatch, smoke_yaml, name="src"):
    """A real (synthetic-backend) single-ES run dir with a full cma/covariance.json."""
    smoke = load_config(smoke_yaml)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / name
    cma_mod.search(fast_cfg(smoke, budget=5), rd, "screen", backend=be, budget=5,
                   store=DatasetStore(rd / "ds"))
    assert (rd / "cma" / "covariance.json").is_file()
    return rd


def _run_cfg(tmp_path, monkeypatch, cfg, name):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    out = tmp_path / name
    cma_mod.search(fast_cfg(cfg, budget=4), out, "screen", backend=be, budget=4,
                   store=DatasetStore(out / "ds"))
    return out


# ---------------------------------------------------------------- transform convention

def test_transform_formula_shape_and_scale():
    C_old = np.array([[2.0, 0.3, 0.1],
                      [0.3, 0.5, 0.05],
                      [0.1, 0.05, 0.8]])
    spans_old = np.array([2.0, 8.0, 0.4])
    spans_new = np.array([4.0, 1.0, 2.0])
    sigma_old = 0.37
    d = C_old.shape[0]

    # scale_sigma=False preserves the transformed overall scale: sigma^2 * C == T.
    C_new, target, info = warmstart.transfer_covariance(
        C_old, sigma_old, spans_old, spans_new,
        blend=1.0, eig_floor=1e-8, eig_cap=1e8, scale_sigma=False)
    T = ((spans_old[:, None] * (sigma_old ** 2 * C_old) * spans_old[None, :])
         / (spans_new[:, None] * spans_new[None, :]))
    np.testing.assert_allclose(target ** 2 * C_new, T, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(C_new, C_new.T, atol=1e-15)
    assert np.linalg.eigvalsh(C_new).min() > 0.0
    assert info["spd_verified"] is True
    assert abs(np.trace(C_new) - d) < 1e-10

    # scale_sigma=True keeps the same SHAPE but declares the config sigma0 as the width.
    C_same, target_same, _ = warmstart.transfer_covariance(
        C_old, sigma_old, spans_old, spans_new,
        blend=1.0, eig_floor=1e-8, eig_cap=1e8, scale_sigma=True, sigma0=0.23)
    np.testing.assert_allclose(C_same, C_new, rtol=1e-12, atol=1e-12)
    assert target_same == pytest.approx(0.23)

    # The conservative blend is a convex mix with the identity (both trace d).
    C_blend, _, _ = warmstart.transfer_covariance(
        C_old, sigma_old, spans_old, spans_new,
        blend=0.25, eig_floor=1e-8, eig_cap=1e8, scale_sigma=True, sigma0=0.23)
    np.testing.assert_allclose(C_blend, 0.75 * np.eye(d) + 0.25 * C_new,
                               rtol=1e-12, atol=1e-12)
    assert abs(np.trace(C_blend) - d) < 1e-10


def test_eigen_floor_and_cap_are_enforced():
    C_old = np.diag([1.0e-12, 1.0e12, 1.0])
    spans = np.ones(3)
    C_new, _, info = warmstart.transfer_covariance(
        C_old, 0.4, spans, spans,
        blend=1.0, eig_floor=1e-3, eig_cap=1e3, scale_sigma=True, sigma0=0.2)
    w = np.linalg.eigvalsh(C_new)
    assert w.min() >= 1e-3 - 1e-12
    assert w.max() <= 1e3 + 1e-9
    assert info["eig_floor"] == 1e-3 and info["eig_cap"] == 1e3

    # A clip/blend can change trace(C_target); scale_sigma=False must still preserve trace(T).
    C_unscaled, target, info_u = warmstart.transfer_covariance(
        C_old, 0.4, spans, spans,
        blend=0.5, eig_floor=0.4, eig_cap=1.0, scale_sigma=False)
    assert np.trace(target ** 2 * C_unscaled) == pytest.approx(info_u["raw_trace"],
                                                               rel=1e-12)
    assert abs(np.trace(C_unscaled) - 3.0) > 0.1       # the trace really did move


# ---------------------------------------------------------------- sampler injection

def test_injected_covariance_matches_empirical_sampling():
    """20k draws, relative Frobenius error of the empirical covariance < 5%.

    For a d=3 Gaussian the sample-covariance entries have relative standard error about
    sqrt(2/n) ≈ 1.0%; a 5% band is ~5 sigma at n=20,000, so this is a real mismatch detector,
    not a loose smoke check.
    """
    d = 3
    C_target = np.array([[1.4, 0.3, 0.1],
                         [0.3, 0.8, -0.2],
                         [0.1, -0.2, 0.6]])
    C_target *= d / np.trace(C_target)                 # documented trace(d) convention
    sigma = 0.23
    es = cma_lib.CMAEvolutionStrategy([0.5, 0.5, 0.5], sigma,
                                      {"verbose": -1, "seed": 17})
    injected = cma_mod.apply_initial_covariance(es, C_target)
    assert injected["spd_verified"] is True
    draws = np.asarray(es.ask(20000), dtype=float)
    empirical = np.cov(draws, rowvar=False, bias=True)
    target = sigma ** 2 * C_target
    rel = np.linalg.norm(empirical - target, "fro") / np.linalg.norm(target, "fro")
    assert rel < 0.05, f"relative Frobenius covariance error {rel:.4f} exceeds 0.05"
    assert np.linalg.eigvalsh(empirical).min() > 0.0


def test_injection_refuses_non_spd():
    es = cma_lib.CMAEvolutionStrategy([0.5, 0.5], 0.2, {"verbose": -1, "seed": 3})
    with pytest.raises(ConfigError, match="not SPD"):
        cma_mod.apply_initial_covariance(es, np.array([[1.0, 2.0], [2.0, 1.0]]))


# ---------------------------------------------------------------- end to end

def _mutated_bounds(raw):
    """Different old/new spans: shrink a few bounds but keep the smoke seed inside."""
    raw["bounds"]["a_deg"] = {"lo": 10.0, "hi": 50.0}
    raw["bounds"]["n"] = {"lo": 2.5, "hi": 7.0}
    raw["bounds"]["s"] = {"lo": 0.1, "hi": 0.9}


def test_end_to_end_covariance_record_and_search_runs(
        tmp_path, smoke_cfg_path, monkeypatch):
    rd = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    cfg = _warm_cfg(tmp_path, smoke_cfg_path,
                    {"from_runs": [str(rd)], "covariance": {"blend": 0.4}},
                    name="cov", mutate=_mutated_bounds)
    out = _run_cfg(tmp_path, monkeypatch, cfg, "r")
    rj = read_json(out / "run.json")
    cov = rj["warm_start"]["covariance"]
    keys = DesignSpace.from_config(cfg).keys()
    assert cov["source"]["run"] == str(rd)
    assert cov["source"]["covariance_path"] == str(rd / "cma" / "covariance.json")
    assert len(cov["source"]["C_sha256"]) == 64
    assert cov["source"]["objective_version"] == int(cfg.objective_version)
    assert cov["keys"] == keys
    assert set(cov["spans_old"]) == set(keys) and set(cov["spans_new"]) == set(keys)
    assert cov["spans_old"]["a_deg"] == pytest.approx(50.0)   # source span 5..55
    assert cov["spans_new"]["a_deg"] == pytest.approx(40.0)   # this config 10..50
    assert cov["blend"] == pytest.approx(0.4)
    assert cov["scale_sigma"] is True
    assert cov["target_sigma"] == pytest.approx(cfg.search.sigma0)
    assert cov["spd_verified"] is True
    assert cov["injected_condition_number"] >= 1.0
    assert abs(cov["trace"] - len(keys)) < 1e-8
    rows = read_ndjson(out / "search.ndjson")
    assert rows and rj["status"] == "finished"


def test_absent_and_false_covariance_records_are_identical(
        tmp_path, smoke_cfg_path, monkeypatch):
    rd = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    cfg_absent = _warm_cfg(tmp_path, smoke_cfg_path, {"from_runs": [str(rd)]},
                           name="absent")
    cfg_false = _warm_cfg(tmp_path, smoke_cfg_path,
                          {"from_runs": [str(rd)], "covariance": False}, name="false")
    out_a = _run_cfg(tmp_path, monkeypatch, cfg_absent, "ra")
    out_f = _run_cfg(tmp_path, monkeypatch, cfg_false, "rf")
    wa = read_json(out_a / "run.json")["warm_start"]
    wf = read_json(out_f / "run.json")["warm_start"]
    assert "covariance" not in wa and "mean_source" not in wa
    assert wa == wf                                  # byte-identical mean-only record


# ---------------------------------------------------------------- refusals

def _sidecar(rd):
    return rd / "cma" / "covariance.json"


def test_missing_sidecar_is_refused(tmp_path, smoke_cfg_path, monkeypatch):
    rd = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    _sidecar(rd).unlink()
    cfg = _warm_cfg(tmp_path, smoke_cfg_path, {"from_runs": [str(rd)], "covariance": True})
    space = DesignSpace.from_config(cfg)
    _, record = warmstart.mean_and_sigma(cfg, space)
    with pytest.raises(warmstart.WarmStartError, match="covariance.json is missing"):
        warmstart.covariance(cfg, space, record)


def test_restart_only_summary_without_full_C_is_refused(
        tmp_path, smoke_cfg_path, monkeypatch):
    rd = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    snap = read_json(_sidecar(rd))
    snap.pop("C")                                    # exactly what the restart path writes
    write_json_atomic(_sidecar(rd), snap)
    cfg = _warm_cfg(tmp_path, smoke_cfg_path, {"from_runs": [str(rd)], "covariance": True})
    space = DesignSpace.from_config(cfg)
    _, record = warmstart.mean_and_sigma(cfg, space)
    with pytest.raises(warmstart.WarmStartError, match="compressed/restart-only"):
        warmstart.covariance(cfg, space, record)


def test_dimension_above_max_dim_is_refused(tmp_path, smoke_cfg_path, monkeypatch):
    rd = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    cfg = _warm_cfg(tmp_path, smoke_cfg_path,
                    {"from_runs": [str(rd)], "covariance": {"max_dim": 2}})
    space = DesignSpace.from_config(cfg)
    _, record = warmstart.mean_and_sigma(cfg, space)
    with pytest.raises(warmstart.WarmStartError, match="above max_dim"):
        warmstart.covariance(cfg, space, record)


def test_sidecar_knob_mismatch_is_refused(tmp_path, smoke_cfg_path, monkeypatch):
    rd = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    snap = read_json(_sidecar(rd))
    snap["keys"] = list(reversed(snap["keys"]))
    write_json_atomic(_sidecar(rd), snap)
    cfg = _warm_cfg(tmp_path, smoke_cfg_path, {"from_runs": [str(rd)], "covariance": True})
    space = DesignSpace.from_config(cfg)
    _, record = warmstart.mean_and_sigma(cfg, space)
    with pytest.raises(warmstart.WarmStartError, match="knob-name/order mismatch"):
        warmstart.covariance(cfg, space, record)


def test_non_spd_source_covariance_is_refused(tmp_path, smoke_cfg_path, monkeypatch):
    rd = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    snap = read_json(_sidecar(rd))
    d = len(snap["keys"])
    snap["C"] = (-np.eye(d)).tolist()
    write_json_atomic(_sidecar(rd), snap)
    cfg = _warm_cfg(tmp_path, smoke_cfg_path, {"from_runs": [str(rd)], "covariance": True})
    space = DesignSpace.from_config(cfg)
    _, record = warmstart.mean_and_sigma(cfg, space)
    with pytest.raises(warmstart.WarmStartError, match="not SPD"):
        warmstart.covariance(cfg, space, record)


def test_covariance_with_restarts_is_refused_not_ignored(tmp_path, smoke_cfg_path, monkeypatch):
    rd = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    with pytest.raises(ConfigError, match="restarts"):
        _warm_cfg(tmp_path, smoke_cfg_path,
                  {"from_runs": [str(rd)], "covariance": True},
                  mutate=lambda raw: raw["search"].update(
                      {"restarts": {"mode": "ipop", "max": 1}}))


def test_covariance_with_cma_me_is_refused_not_ignored(tmp_path, smoke_cfg_path):
    from test_search_cma_me import qd_block

    with pytest.raises(ConfigError, match="cma_me"):
        _warm_cfg(tmp_path, smoke_cfg_path, {"from_runs": ["."], "covariance": True},
                  mutate=lambda raw: raw["search"].update(
                      {"algorithm": "cma_me", "qd": qd_block()}))


# ---------------------------------------------------------------- config validation

def test_covariance_true_resolves_conservative_defaults(tmp_path, smoke_cfg_path):
    cfg = _warm_cfg(tmp_path, smoke_cfg_path, {"from_runs": ["."], "covariance": True})
    cov = cfg.search.warm_start["covariance"]
    assert cov == warmstart.COVARIANCE_DEFAULTS
    assert cov["blend"] == 0.25 and cov["max_dim"] == 16 and cov["scale_sigma"] is True


@pytest.mark.parametrize("bad, match", [
    ("yes", "true, false or a mapping"),
    ({"magic": 1}, "unknown key"),
    ({"blend": 1.5}, "blend"),
    ({"blend": True}, "must be a number"),
    ({"eig_floor": 0}, "eig_floor"),
    ({"eig_cap": 1e-9}, "eig_cap"),
    ({"max_dim": 0}, "max_dim"),
    ({"max_dim": 17}, "max_dim"),
    ({"max_dim": 2.5}, "max_dim"),
    ({"scale_sigma": 1}, "scale_sigma"),
])
def test_bad_covariance_config_is_refused(tmp_path, smoke_cfg_path, bad, match):
    with pytest.raises(ConfigError, match=match):
        _warm_cfg(tmp_path, smoke_cfg_path, {"from_runs": ["."], "covariance": bad})
