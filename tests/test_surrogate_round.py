"""Focused, offline tests for this lane's surrogate/CLI fixes:

* ``surrogate.round.load_proposals`` argument/file validation (the solve path needs the real
  backend and is deliberately NOT exercised here);
* the ``surrogate round`` CLI pre-flight refusals;
* the ``surrogate train`` GATES-FAILED vs GATES-REFUSED headline split.

No solver, no GPU, no mesher: ``train_surrogate`` and ``to_training_arrays`` are stubbed.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

EX = Path(__file__).resolve().parents[1] / "examples" / "osse_baseline.yaml"


def _proposal(**kw):
    base = {"family": "OSSE", "params": {"r0_mm": 12.7}, "kind": "exploit",
            "pred_J": 1.5, "std": 0.2}
    base.update(kw)
    return base


# ------------------------------------------------------------------ load_proposals

def test_load_proposals_validates(tmp_path):
    from hornlab_search.surrogate.round import load_proposals
    with pytest.raises(ValueError, match="does not exist"):
        load_proposals(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_proposals(bad)
    empty = tmp_path / "e.json"
    empty.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty"):
        load_proposals(empty)
    missing = tmp_path / "m.json"
    missing.write_text(json.dumps([{"family": "OSSE"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="missing field"):
        load_proposals(missing)
    badkind = tmp_path / "k.json"
    badkind.write_text(json.dumps([_proposal(kind="x")]), encoding="utf-8")
    with pytest.raises(ValueError, match="kind"):
        load_proposals(badkind)
    good = tmp_path / "g.json"
    good.write_text(json.dumps([_proposal()]), encoding="utf-8")
    assert load_proposals(good) == [_proposal()]


def test_run_round_validates_before_any_solver(tmp_path):
    from hornlab_search.config import load_config
    from hornlab_search.surrogate.round import run_round
    cfg = load_config(EX)
    p = tmp_path / "p.json"
    p.write_text(json.dumps([_proposal()]), encoding="utf-8")
    with pytest.raises(ValueError, match="mode must be"):
        run_round(p, cfg, mode="nope", out_dir=tmp_path / "o")
    with pytest.raises(ValueError, match="out_dir is required"):
        run_round(p, cfg, mode="screen", out_dir=None)
    assert not (tmp_path / "o").exists()          # refused before doing anything


# ------------------------------------------------------------------ surrogate round CLI

def test_cli_round_requires_existing_proposals(tmp_path, capsys):
    pytest.importorskip("torch")
    from hornlab_search.cli import main
    rc = main(["surrogate", "round", "--config", str(EX),
               "--proposals", str(tmp_path / "nope.json"),
               "--out-dir", str(tmp_path / "round"),
               "--dataset-dir", str(tmp_path / "dataset")])
    out = capsys.readouterr().out
    assert rc == 1 and "does not exist" in out


def test_cli_round_requires_out_dir(tmp_path, capsys):
    pytest.importorskip("torch")
    from hornlab_search.cli import main
    p = tmp_path / "p.json"
    p.write_text(json.dumps([_proposal()]), encoding="utf-8")
    rc = main(["surrogate", "round", "--config", str(EX), "--proposals", str(p),
               "--dataset-dir", str(tmp_path / "dataset")])
    out = capsys.readouterr().out
    assert rc == 1 and "--out-dir is required" in out


# ------------------------------------------------------------------ train headline split

def _fake_rep(passed: bool, gates_pass: dict, n_heldout: int, warnings=()) -> dict:
    return {"gates": {k: {"value": 1.0, "threshold": "x", "pass": v}
                      for k, v in gates_pass.items()},
            "pass": passed, "warnings": list(warnings), "n_heldout": n_heldout,
            "n_duplicates_dropped": 0, "objective_delta_max": 0.0, "objective_delta_mean": 0.0,
            "saved": True, "kept_existing_bundle": False}


_ALL_PASS = {"spearman": True, "topk_overlap": True, "bw_mae_deg": True, "di_mae_db": True,
             "invalid_accuracy": True, "monotonic_flips": True}


def _run_train(monkeypatch, tmp_path, rep, capsys):
    from hornlab_search.dataset import store as dstore
    from hornlab_search.surrogate import train as train_mod
    from hornlab_search.cli import main
    (tmp_path / "dataset").mkdir()

    def fake_arrays(store, **kw):
        return {"X": np.zeros((60, 4), np.float32),
                "meta": {"n_considered": 60, "n_selected": 60, "skipped_grid_mismatch": 0,
                         "skipped_bad_arrays": 0, "skipped_keys": []}}

    monkeypatch.setattr(dstore, "to_training_arrays", fake_arrays)
    monkeypatch.setattr(train_mod, "train_surrogate", lambda *a, **k: (object(), rep))
    rc = main(["surrogate", "train", "--config", str(EX),
               "--dataset-dir", str(tmp_path / "dataset")])
    return rc, capsys.readouterr().out


def test_train_headline_failed_names_the_failing_gates(monkeypatch, tmp_path, capsys):
    pytest.importorskip("torch")
    gates_pass = dict(_ALL_PASS, spearman=False, monotonic_flips=False)
    rep = _fake_rep(False, gates_pass, 225, warnings=["held-out set has 225 designs; ..."])
    rc, out = _run_train(monkeypatch, tmp_path, rep, capsys)
    assert rc == 1
    assert "GATES FAILED: spearman, monotonic_flips" in out
    assert "GATES REFUSED" not in out


def test_train_headline_refused_when_all_gates_pass_but_heldout_below_floor(
        monkeypatch, tmp_path, capsys):
    pytest.importorskip("torch")
    rep = _fake_rep(False, _ALL_PASS, 225,
                    warnings=["held-out set has 225 designs; the plan requires >= 500 ..."])
    rc, out = _run_train(monkeypatch, tmp_path, rep, capsys)
    assert rc == 1
    assert ("GATES REFUSED (indicative only): all 6 measured gates pass; "
            "held-out 225 < 500 formal floor") in out
    assert "GATES FAILED" not in out


def test_train_headline_passed(monkeypatch, tmp_path, capsys):
    pytest.importorskip("torch")
    rep = _fake_rep(True, _ALL_PASS, 600)
    rc, out = _run_train(monkeypatch, tmp_path, rep, capsys)
    assert rc == 0 and "GATES PASSED" in out
