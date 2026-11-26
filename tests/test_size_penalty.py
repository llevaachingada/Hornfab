"""Opt-in soft size cost on J (objective/size_penalty.py; owner 2026-11-25)."""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest
import yaml

from hornlab_search.config import ConfigError, load_brief
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.design.space import DesignSpace
from hornlab_search.objective.size_penalty import (size_penalty_terms, soft_penalty_block,
                                                   validate_soft_penalty)
from hornlab_search.objective.terms import NAN_TERM_FILL
from hornlab_search.search.evaluate import evaluate, make_context, read_ndjson
from test_search_support import LIBS, SyntheticBackend, fast_cfg, install_fakes

BLOCK = {"weight": 1.0, "tolerance": 0.05}


def test_cost_is_zero_inside_the_box_and_quadratic_past_it():
    assert size_penalty_terms({"max_utilization": 0.9}, BLOCK) == {"size_penalty": 0.0,
                                                                     "size_utilization": 0.9}
    assert size_penalty_terms({"max_utilization": 1.0}, BLOCK)["size_penalty"] == 0.0
    assert size_penalty_terms({"max_utilization": 1.05}, BLOCK)["size_penalty"] == pytest.approx(1.0)
    assert size_penalty_terms({"max_utilization": 1.10}, BLOCK)["size_penalty"] == pytest.approx(4.0)
    two = size_penalty_terms({"max_utilization": 1.10}, {"weight": 2.0, "tolerance": 0.10})
    assert two["size_penalty"] == pytest.approx(2.0)


def test_unmeasured_size_is_not_free():
    for rec in (None, {}, {"status": "geometry_unmeasured"}, {"max_utilization": float("nan")}):
        out = size_penalty_terms(rec, BLOCK)
        assert out == {"size_penalty": NAN_TERM_FILL, "size_utilization": -1.0}


@pytest.mark.parametrize("block, enforce, match", [
    ({"weight": 1.0}, False, "missing"),
    ({"weight": 1.0, "tolerance": 0.05, "start": 1.0}, False, "unknown"),
    ({"weight": 0.0, "tolerance": 0.05}, False, "positive"),
    ({"weight": 1.0, "tolerance": True}, False, "positive"),
    (BLOCK, True, "enforce: false"),
    ([1, 2], False, "mapping"),
])
def test_validator_refuses_bad_blocks(block, enforce, match):
    with pytest.raises(ValueError, match=match):
        validate_soft_penalty(block, "brief x", enforce=enforce)


def test_absent_block_means_no_size_term():
    assert soft_penalty_block(None) is None
    assert soft_penalty_block({"envelope": {"enforce": False, "max_utilization": 1.3}}) is None


def _brief_yaml(tmp_path, env_extra):
    src = "examples/briefs/home_xo900_2026-11-20/room_landscape_80x50_900_hf1440_v11cd_open115_2026-11-25.yaml"
    raw = yaml.safe_load(open(src, encoding="utf-8"))
    raw["envelope"].update(env_extra)
    p = tmp_path / "b.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


def test_brief_loader_accepts_and_validates_the_block(tmp_path):
    ok = load_brief(_brief_yaml(tmp_path, {"soft_penalty": dict(BLOCK), "max_utilization": 1.3}))
    assert soft_penalty_block(ok) == BLOCK
    with pytest.raises(ConfigError, match="enforce: false"):
        load_brief(_brief_yaml(tmp_path, {"enforce": True, "max_utilization": None,
                                          "soft_penalty": dict(BLOCK)}))
    with pytest.raises(ConfigError, match="soft_penalty"):
        load_brief(_brief_yaml(tmp_path, {"soft_penalty": {"weight": 1.0}}))


def _with_envelope(cfg, envelope):
    brief = {**(cfg.brief or {}), "envelope": envelope}
    return dataclasses.replace(cfg, brief=brief, raw={**cfg.raw, "brief": brief})


def _run(cfg, tmp_path, name, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    store = DatasetStore(tmp_path / f"{name}_ds")
    space = DesignSpace.from_config(cfg)
    ev = evaluate(space.seed, space, cfg, "screen", tmp_path / name, store, be,
                  ctx=make_context(cfg, store, lib_shas=LIBS, ndjson=tmp_path / name / "search.ndjson"))
    (row,) = read_ndjson(tmp_path / name / "search.ndjson")
    return ev, row


@pytest.mark.parametrize("box_mm, oversize", [(60.0, True), (2000.0, False)])
def test_evaluate_adds_the_cost_after_the_acoustic_objective(smoke_cfg, tmp_path, monkeypatch,
                                                             box_mm, oversize):
    cfg = fast_cfg(smoke_cfg)
    base_env = {"max_mouth_w_mm": box_mm, "max_mouth_h_mm": box_mm, "max_depth_mm": box_mm,
                "enforce": False, "max_utilization": 1000.0, "sanity_max_mm": 5000.0}
    plain, plain_row = _run(_with_envelope(cfg, base_env), tmp_path, "plain", monkeypatch)
    soft, row = _run(_with_envelope(cfg, {**base_env, "soft_penalty": dict(BLOCK)}), tmp_path,
                     "soft", monkeypatch)
    assert not plain.error and not soft.error
    assert "size_penalty" not in plain.terms and "size_penalty" not in plain_row["terms"]
    expected = size_penalty_terms(row["size_feasibility"], BLOCK)
    assert soft.terms["size_penalty"] == pytest.approx(expected["size_penalty"])
    assert soft.terms["size_utilization"] == pytest.approx(expected["size_utilization"])
    assert soft.terms["J_acoustic"] == pytest.approx(plain.objective)
    assert soft.objective == pytest.approx(plain.objective + expected["size_penalty"])
    assert row["objective"] == pytest.approx(soft.objective)
    assert (expected["size_penalty"] > 0.0) is oversize
    assert np.isfinite(soft.objective)
