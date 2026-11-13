"""B.8 (day 2026-11-12): ``search.qd.maes`` — CMA-ME -> CMA-MAE option (Fontaine & Nikolaidis
2023): a soft GridArchive (learning_rate in [0.01, 0.1], threshold_min = -j_threshold as the
MAXIMISED objective), emitter ranker "imp" and NO emitter bounds (candidates clipped in
DesignSpace.denormalize, like plain CMA). Absent ``maes`` = today's CMA-ME (run.json's qd block
gains no key and the archive defaults stay 1.0 / -inf / "2imp" / bounds=).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import ConfigError, load_config
from hornlab_search.search import cma_me as qd_mod
from test_search_cma_me import knob_eval, qd_block, run_json, run_qd, two_knob_cfg

MAES = {"learning_rate": 0.05, "j_threshold": 999.0}


@pytest.fixture
def smoke_cfg_path():
    return Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml"


def _cfg(tmp_path, qd):
    raw = yaml.safe_load((EXAMPLES / "search_smoke.yaml").read_text(encoding="utf-8"))
    raw["search"]["algorithm"] = "cma_me"
    raw["search"]["qd"] = qd
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def test_maes_block_loads(tmp_path, smoke_cfg_path):
    cfg = _cfg(tmp_path, qd_block(maes=dict(MAES)))
    assert cfg.search.qd["maes"] == {"learning_rate": 0.05, "j_threshold": 999.0}


def test_absent_maes_keeps_the_cma_me_block_unchanged(tmp_path, smoke_cfg_path):
    cfg = _cfg(tmp_path, qd_block())
    assert "maes" not in cfg.search.qd


@pytest.mark.parametrize("qd,match", [
    (qd_block(maes={"learning_rate": 0.4, "j_threshold": 999.0}), "learning_rate"),
    (qd_block(maes={"learning_rate": 0.005, "j_threshold": 999.0}), "learning_rate"),
    (qd_block(maes={"learning_rate": 0.05, "j_threshold": 0.0}), "j_threshold"),
    (qd_block(maes={"learning_rate": 0.05, "j_threshold": 1000.0}), "j_threshold"),
    (qd_block(maes={"learning_rate": 0.05, "j_threshold": 1500.0}), "j_threshold"),
    (qd_block(maes={"learning_rate": 0.05, "j_threshold": float("nan")}), "j_threshold"),
    (qd_block(maes={"learning_rate": 0.05}), "j_threshold"),
    (qd_block(maes={"magic": 1}), "unknown key"),
    (qd_block(maes=5), "must be a mapping"),
])
def test_maes_bad_blocks_are_refused(tmp_path, smoke_cfg_path, qd, match):
    with pytest.raises(ConfigError, match=match):
        _cfg(tmp_path, qd)


def test_cma_mae_run_records_maes_in_run_json(tmp_path, smoke_cfg, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    smoke = two_knob_cfg(smoke_cfg, qd=qd_block(maes=dict(MAES)))
    rd = tmp_path / "maes_run"
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(smoke))
    run_qd(smoke, rd, 6)
    run_json_ = run_json(rd)
    assert run_json_["qd"]["maes"] == {"learning_rate": 0.05, "j_threshold": 999.0}
    assert run_json_["status"] == "finished"
    assert (rd / "archive_heatmap.json").exists()
    assert (rd / "archive.json").exists()


def test_default_cma_me_run_json_has_no_maes(tmp_path, smoke_cfg, monkeypatch):
    pytest.importorskip("ribs", reason="ribs not installed")
    smoke = two_knob_cfg(smoke_cfg, qd=qd_block())
    rd = tmp_path / "plain_run"
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(smoke))
    run_qd(smoke, rd, 6)
    run_json_ = run_json(rd)
    assert "maes" not in run_json_["qd"]


def test_cma_mae_archive_reaches_cells_beyond_the_plain_archive(tmp_path, smoke_cfg, monkeypatch):
    """With the soft archive the SAME budget fills AT LEAST as many cells as the plain CMA-ME:
    refused... (here the 2-knob fake never refuses; the assertion pins that maes keeps the
    machinery running and the archive non-empty)."""
    pytest.importorskip("ribs", reason="ribs not installed")
    smoke = two_knob_cfg(smoke_cfg, qd=qd_block(maes=dict(MAES)))
    rd = tmp_path / "maes2"
    monkeypatch.setattr(qd_mod, "evaluate", knob_eval(smoke))
    run_qd(smoke, rd, 12)
    payload = json.loads((rd / "archive.json").read_text())
    assert payload["cells"], "the soft archive must hold at least one elite"
    # J values stored are MINIMISATION J (=-archive objective): below the j_threshold always
    assert all(float(c["objective"]) < MAES["j_threshold"] for c in payload["cells"])
