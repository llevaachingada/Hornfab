"""Focused tests for explicit surrogate scoring-capability refusal (v4+ etc.).

No real solve/BEM/GPU and no config/objective default changes. The only trained model is
fitted on ``test_surrogate_stage_a``'s synthetic labels and a handful of epochs.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.surrogate.capability import (
    SUPPORTED_OBJECTIVE_VERSIONS,
    REQUIRED_METRIC_INPUTS,
    UnsupportedObjectiveError,
    capability_status,
    require_supported,
)

EX = Path(__file__).resolve().parents[1] / "examples" / "osse_baseline.yaml"


def _complete_inputs():
    return {k: object() for k in REQUIRED_METRIC_INPUTS}


# ---------------------------------------------------------------- capability matrix

def test_supported_versions_are_v1_only():
    assert SUPPORTED_OBJECTIVE_VERSIONS == (1,)
    st = capability_status(1)
    assert st["supported"] is True and st["status"] == "supported"
    assert st["reason_codes"] == [] and st["scorer"] == "objective.scalar"
    assert require_supported(1)["supported"] is True


@pytest.mark.parametrize("version", [2, 3, 4, 5, 6, 7, 8])
def test_newer_versions_are_unsupported(version):
    st = capability_status(version)
    assert st["supported"] is False and st["status"] == "unsupported"
    assert "unsupported_objective_version" in st["reason_codes"]
    with pytest.raises(UnsupportedObjectiveError) as exc:
        require_supported(version)
    assert exc.value.reason_code == "unsupported_objective_version"
    assert exc.value.objective_version == version


@pytest.mark.parametrize("version", [4, 5, 6, 7, 8])
def test_loading_versions_report_missing_throat_impedance(version):
    st = capability_status(version)
    assert "missing_throat_impedance" in st["reason_codes"]
    with pytest.raises(UnsupportedObjectiveError) as exc:
        require_supported(version)
    assert "missing_throat_impedance" in exc.value.reason_codes


@pytest.mark.parametrize("version", [None, "unknown", "v4", 99])
def test_none_or_unknown_is_unsupported_never_v1(version):
    st = capability_status(version)
    assert st["supported"] is False
    assert "unsupported_objective_version" in st["reason_codes"]
    with pytest.raises(UnsupportedObjectiveError):
        require_supported(version)


def test_v4_stays_unsupported_even_with_complete_inputs():
    inputs = dict(_complete_inputs(), z_throat_real=np.ones(3))
    st = capability_status(4, metric_inputs=inputs)
    assert st["supported"] is False
    assert "unsupported_objective_version" in st["reason_codes"]
    # It has impedance, so that reason is not claimed.
    assert "missing_throat_impedance" not in st["reason_codes"]


def test_v1_incomplete_metric_inputs_refuse():
    st = capability_status(1, metric_inputs={"freqs_hz": object()})
    assert st["supported"] is False
    assert st["reason_codes"] == ["missing_complete_metric_inputs"]
    st = capability_status(1, metric_inputs=_complete_inputs())
    assert st["supported"] is True


# ---------------------------------------------------------------- training / bundle meta

@pytest.fixture(scope="module")
def setup():
    pytest.importorskip("torch")
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    cfg = load_config(EX)
    return cfg, DesignSpace.from_config(cfg)


def _trained(setup, tmp_path):
    from test_surrogate_stage_a import _synthetic
    from hornlab_search.surrogate.train import train_surrogate
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 160, 31)
    out = tmp_path / "s.pt"
    sur, rep = train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=5,
                               objective_version=1, out_path=out)
    return cfg, space, sur, rep, out


def test_train_v1_records_version_and_capability(setup, tmp_path):
    from hornlab_search.surrogate.model import load_bundle
    _, _, sur, _, out = _trained(setup, tmp_path)
    meta = load_bundle(out)["meta"]
    assert meta["objective_version"] == 1
    assert meta["scoring_capability"]["supported"] is True
    assert meta["scoring_capability"]["objective_version"] == 1
    assert meta["scoring_capability"]["metric_source"] == "predicted_metric_curves"
    assert meta["scoring_capability"]["fabricated_throat_impedance"] is False
    assert sur.objective_version == 1


def test_v1_evaluate_still_works_and_does_not_fabricate_impedance(setup, tmp_path):
    from hornlab_search.targets.spec import Target
    cfg, space, sur, _, _ = _trained(setup, tmp_path)
    target = Target.from_dict(cfg.target_raw)
    U = np.random.default_rng(2).random((3, len(space.keys()))).astype(np.float32)
    pred = sur.predict(U)
    j = sur.objective(pred, target, cfg.weights)
    assert j.shape == (3,)
    assert np.all(np.isfinite(j))
    m = sur.metric_set(pred, 0)
    assert m.z_throat_real is None
    run = sur.evaluator(space, target, cfg.weights, objective_version=1)
    evs = run([space.seed])
    assert len(evs) == 1 and evs[0].mesh_hash == "surrogate"


def test_train_refuses_v4_before_writing_a_bundle(setup, tmp_path):
    from test_surrogate_stage_a import _synthetic
    from hornlab_search.surrogate.train import train_surrogate
    cfg, space = setup
    arrays, target, _ = _synthetic(space, 120, 32)
    out = tmp_path / "bad.pt"
    with pytest.raises(UnsupportedObjectiveError) as exc:
        train_surrogate(arrays, space, target, cfg.weights, ensemble=1, epochs=2,
                        objective_version=4, out_path=out)
    assert "unsupported_objective_version" in exc.value.reason_codes
    assert not out.exists()


def test_config_mismatch_names_objective_version(setup, tmp_path):
    from hornlab_search.surrogate.model import load_bundle, save_bundle
    from hornlab_search.surrogate.predict import Surrogate
    cfg, space, sur, _, out = _trained(setup, tmp_path)
    assert sur.config_mismatch(space, objective_version=1) is None
    msg = sur.config_mismatch(space, objective_version=4)
    assert msg is not None and "objective_version" in msg and "unsupported" in msg

    b = load_bundle(out)
    b["meta"]["objective_version"] = 4                  # simulate a mislabelled bundle
    save_bundle(out, states=b["states"], meta=b["meta"], mu=b["mu"], sd=b["sd"])
    sur4 = Surrogate.load(out)
    msg = sur4.config_mismatch(space, objective_version=1)
    assert msg is not None and "objective_version" in msg and "4" in msg
    U = np.random.default_rng(3).random((2, len(space.keys()))).astype(np.float32)
    with pytest.raises(UnsupportedObjectiveError):
        sur4.objective(sur4.predict(U), None, {})


def test_evaluator_refuses_unsupported_version(setup, tmp_path):
    _, space, sur, _, _ = _trained(setup, tmp_path)
    with pytest.raises(UnsupportedObjectiveError) as exc:
        sur.evaluator(space, None, {}, objective_version=7)
    assert "unsupported_objective_version" in exc.value.reason_codes
    with pytest.raises(UnsupportedObjectiveError):
        sur.objective({"p_ok": np.ones(1)}, None, {}, objective_version=8)


def test_run_round_refuses_before_any_solver(setup, tmp_path):
    from hornlab_search.surrogate.round import run_round
    cfg, _ = setup
    p = tmp_path / "p.json"
    p.write_text(json.dumps([{"family": "OSSE", "params": {"r0_mm": 12.7},
                              "kind": "exploit", "pred_J": 1.0, "std": 0.1}]), encoding="utf-8")
    cfg4 = dataclasses.replace(cfg, objective_version=4)
    with pytest.raises(UnsupportedObjectiveError) as exc:
        run_round(p, cfg4, mode="screen", out_dir=tmp_path / "round")
    assert "unsupported_objective_version" in exc.value.reason_codes
    assert not (tmp_path / "round").exists()


def test_cli_prints_refused_reason(setup, tmp_path, capsys, monkeypatch):
    pytest.importorskip("torch")
    from hornlab_search import config as config_mod
    from hornlab_search.cli import main
    cfg, _ = setup
    cfg4 = dataclasses.replace(cfg, objective_version=4)
    monkeypatch.setattr(config_mod, "load_config", lambda *a, **k: cfg4)
    rc = main(["surrogate", "train", "--config", str(EX),
               "--dataset-dir", str(tmp_path / "dataset")])
    out = capsys.readouterr().out
    assert rc == 1
    assert "surrogate train REFUSED: unsupported_objective_version" in out
