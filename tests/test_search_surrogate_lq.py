"""B.7 (day 2026-11-12): ``search.surrogate: lq`` — the plain-CMA search is run through pycma's
SurrogatePopulation (fmin_lq_surr2-style): the budget buys generations via a linear/quadratic
model, the model is warmed from the run's own prior rows on a resume, and run.json records the
``surrogate`` block. Absent key = plain CMA byte for byte.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from hornlab_search.config import ConfigError, load_config
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search import cma as cma_mod
from hornlab_search.search.evaluate import read_ndjson
from test_search_support import SyntheticBackend, fast_cfg, install_fakes


@pytest.fixture
def smoke_cfg_path():
    return Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml"


def _lq_cfg(smoke_cfg_path, tmp_path, **extra):
    raw = yaml.safe_load(Path(smoke_cfg_path).read_text(encoding="utf-8"))
    raw["search"]["surrogate"] = "lq"
    raw["search"].update(extra)
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def test_surrogate_run_respects_the_budget_and_records_the_block(tmp_path, smoke_cfg_path,
                                                                 monkeypatch):
    cfg = _lq_cfg(smoke_cfg_path, tmp_path)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    best = cma_mod.search(fast_cfg(cfg, budget=12), rd, "screen", backend=be, budget=12,
                          store=DatasetStore(rd / "ds"))
    rows = read_ndjson(rd / "search.ndjson")
    assert best is not None and any(r["ok"] for r in rows)
    # every TRUE evaluation consumed at most the budget in the default 'new' counting
    assert len(rows) <= 12
    rj = json.loads((rd / "run.json").read_text())
    assert rj["surrogate"]["mode"] == "lq"
    assert rj["surrogate"]["model_seeded"] == 1        # the run's own seed row already seeds it
    # the lq model self-prunes (max_size = popsize), and carries at least min_model_size = 3
    assert 3 <= rj["surrogate"]["model_size"] <= len(rows)
    # the final (budget-cut) batch's true evals may trail: rows can exceed the surrogate's own
    # in-loop count (which excludes the separately-seeded seed row)
    assert 1 <= rj["surrogate"]["true_evaluations"] <= len(rows)


def test_default_run_has_no_surrogate_block(tmp_path, smoke_cfg_path, monkeypatch):
    cfg = load_config(str(smoke_cfg_path))
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    cma_mod.search(fast_cfg(cfg, budget=3), rd, "screen", backend=be, budget=3,
                   store=DatasetStore(rd / "ds"))
    assert "surrogate" not in json.loads((rd / "run.json").read_text())


def test_surrogate_resume_seeds_the_model_from_prior_rows(tmp_path, smoke_cfg_path, monkeypatch):
    cfg = _lq_cfg(smoke_cfg_path, tmp_path)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    cma_mod.search(fast_cfg(cfg, budget=6), rd, "screen", backend=be, budget=6,
                   store=DatasetStore(rd / "ds"))
    first = json.loads((rd / "run.json").read_text())
    n_first_rows = int(first["surrogate"]["true_evaluations"])
    # a resume sees the first invocation's rows and must seed the model from them
    be2 = SyntheticBackend()
    install_fakes(monkeypatch, be2)
    best2 = cma_mod.search(fast_cfg(cfg, budget=12), rd, "screen", backend=be2, budget=12,
                           store=DatasetStore(rd / "ds"))
    rows = read_ndjson(rd / "search.ndjson")
    rj = json.loads((rd / "run.json").read_text())
    assert rows[0]["ok"] is not None
    assert rj["surrogate"]["model_seeded"] >= n_first_rows
    assert best2 is not None


@pytest.mark.parametrize("patch,match", [
    ({"surrogate": "sq"}, "surrogate must be 'lq'"),
    ({"surrogate": True}, "surrogate must be 'lq'"),
    ({"surrogate": "lq", "restarts": {"mode": "ipop", "max": 1}}, "restarts"),
    ({"surrogate": "lq", "pipeline_prefetch": 2}, "pipeline_prefetch"),
])
def test_surrogate_bad_configs_are_refused(tmp_path, smoke_cfg_path, patch, match):
    raw = yaml.safe_load(Path(smoke_cfg_path).read_text(encoding="utf-8"))
    raw["search"].update(patch)
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    with pytest.raises(ConfigError, match=match):
        load_config(p)


def test_surrogate_with_cma_me_is_refused(tmp_path, smoke_cfg_path):
    raw = yaml.safe_load(Path(smoke_cfg_path).read_text(encoding="utf-8"))
    raw["search"]["algorithm"] = "cma_me"
    raw["search"]["surrogate"] = "lq"
    raw["search"]["qd"] = {"bins_h": 8, "bins_v": 8}
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    with pytest.raises(ConfigError, match="cma_me"):
        load_config(p)
