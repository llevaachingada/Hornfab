"""B.1 (day 2026-11-12): ``search.warm_start`` — the CMA mean starts at the best valid design
(and sigma0 from the top-k median per-knob spread, clamped to [0.05, sigma0]) among the source
runs; a version/family/knob mismatch is refused unless allow_cross_brief; run.json records the
warm-start sources. Absent key = (None, None) = today's behaviour.
"""
from __future__ import annotations

import dataclasses
import json

import pytest
import yaml

from hornlab_search.config import ConfigError, load_config
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.design.space import DesignSpace
from hornlab_search.search import cma as cma_mod
from hornlab_search.search import warmstart
from hornlab_search.search.evaluate import append_ndjson, read_ndjson
from hornlab_search.search.rundir import write_json_atomic
from test_search_support import SyntheticBackend, fast_cfg, install_fakes


@pytest.fixture
def smoke_cfg_path():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml"


KNOWS = ["L_mm", "a0_deg", "a_deg", "aspect_ratio", "k", "n", "q", "s"]   # minus 'exponent'


def _source_run(tmp_path, monkeypatch, smoke_yaml, name="src"):
    """A real (synthetic-backend) search run dir the warm start can read later."""
    smoke = load_config(smoke_yaml)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / name
    cma_mod.search(fast_cfg(smoke, budget=5), rd, "screen", backend=be, budget=5,
                   store=DatasetStore(rd / "ds"))
    rows = [r for r in read_ndjson(rd / "search.ndjson") if r.get("ok")]
    assert rows, "the source run needs at least one valid row"
    return rd, min(rows, key=lambda r: float(r["objective"]))


def _warm_cfg_raw(tmp_path, smoke_yaml, warm):
    raw = yaml.safe_load(_read(smoke_yaml))
    raw["search"]["warm_start"] = warm
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def _read(p):
    from pathlib import Path
    return Path(p).read_text(encoding="utf-8")


def test_absent_warm_start_returns_none(smoke_cfg):
    space = DesignSpace.from_config(smoke_cfg)
    assert warmstart.mean_and_sigma(smoke_cfg, space) == (None, None)


def test_warm_mean_is_the_best_valid_design_and_sigma_recorded(
        tmp_path, smoke_cfg, smoke_cfg_path, monkeypatch):
    rd, best = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    cfg = _warm_cfg_raw(tmp_path, smoke_cfg_path, {"from_runs": [str(rd)]})
    space = DesignSpace.from_config(cfg)
    design, record = warmstart.mean_and_sigma(cfg, space)
    for k in KNOWS:
        # the mean must normalise to the same unit vector as the source's best row
        u_d = space.bounds[k].to_unit(float(design.params[k]))[0]
        u_b = space.bounds[k].to_unit(float(best["params"][k]))[0]
        assert abs(u_d - u_b) < 1e-12, k
    assert record["mean_design_hash"] == best["design_hash"]
    assert record["mean_objective"] == float(best["objective"])
    assert record["sources"][0]["path"] == str(rd)
    assert record["designs_clipped_to_box"] == 0
    assert isinstance(record["sigma_from_spread"], dict) \
        and record["sigma_from_spread"]["sigma0"] <= smoke_cfg.search.sigma0


def test_version_mismatch_is_refused_and_the_override_works(
        tmp_path, smoke_cfg, smoke_cfg_path, monkeypatch):
    rd, _ = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    raw = json.loads((rd / "run.json").read_text())
    raw["objective_version"] = 7
    raw["config"]["objective"] = {"version": 7}
    write_json_atomic(rd / "run.json", raw)
    cfg = _warm_cfg_raw(tmp_path, smoke_cfg_path, {"from_runs": [str(rd)]})
    space = DesignSpace.from_config(cfg)
    with pytest.raises(warmstart.WarmStartError, match="version/brief mismatch"):
        warmstart.mean_and_sigma(cfg, space)
    cfg2 = _warm_cfg_raw(tmp_path, smoke_cfg_path,
                         {"from_runs": [str(rd)], "allow_cross_brief": True})
    design, record = warmstart.mean_and_sigma(cfg2, space)
    assert design is not None and record["sources"][0]["objective_version"] == 7


def test_family_and_knob_mismatch_are_refused(tmp_path, smoke_cfg, smoke_cfg_path, monkeypatch):
    rd, _ = _source_run(tmp_path, monkeypatch, smoke_cfg_path)
    cfg = _warm_cfg_raw(tmp_path, smoke_cfg_path, {"from_runs": [str(rd)]})
    space = DesignSpace.from_config(cfg)
    raw = json.loads((rd / "run.json").read_text())
    raw["family"] = "R-OSSE"
    write_json_atomic(rd / "run.json", raw)
    with pytest.raises(warmstart.WarmStartError, match="family mismatch"):
        warmstart.mean_and_sigma(cfg, space)
    raw["family"] = cfg.family
    raw["config"]["bounds"]["exponent"] = {"lo": 1.0, "hi": 8.0, "search": False}
    write_json_atomic(rd / "run.json", raw)
    with pytest.raises(warmstart.WarmStartError, match="knob-name mismatch"):
        warmstart.mean_and_sigma(cfg, space)


def test_out_of_box_designs_are_clipped_and_counted(tmp_path, smoke_cfg, smoke_cfg_path):
    """A hand-written source run whose best row sits outside THIS config's box."""
    rd = tmp_path / "src"
    rd.mkdir()
    raw = {"family": "OSSE",
           "config": {"bounds": {"a_deg": {"lo": 0.0, "hi": 90.0}, "s": {"lo": 0.0, "hi": 1.0},
                                 "L_mm": {"lo": 140.0, "hi": 420.0},
                                 "a0_deg": {"lo": 0.0, "hi": 90.0},
                                 "aspect_ratio": {"lo": 1.0, "hi": 2.0},
                                 "k": {"lo": 0.3, "hi": 2.5}, "n": {"lo": 2.0, "hi": 8.0},
                                 "q": {"lo": 0.9, "hi": 1.0}, "exponent": {"lo": 1.0, "hi": 8.0}},
                      "objective": {"version": 1}},
           "objective_version": 1}
    write_json_atomic(rd / "run.json", raw)
    append_ndjson(rd / "search.ndjson", {
        "n": 0, "ok": True, "kind": "", "objective": -5.0, "design_hash": "ffff", "cached": False,
        "params": {"a_deg": 87.0, "s": 0.5, "L_mm": 260.0, "a0_deg": 15.5, "aspect_ratio": 1.25,
                   "k": 1.0, "n": 4.0, "q": 0.995, "exponent": 4.0}})
    cfg = _warm_cfg_raw(tmp_path, smoke_cfg_path, {"from_runs": [str(rd)]})
    cfg = dataclasses.replace(cfg, objective_version=1)
    space = DesignSpace.from_config(cfg)
    design, record = warmstart.mean_and_sigma(cfg, space)
    assert record["designs_clipped_to_box"] == 1
    assert design.params["a_deg"] == 55.0     # clipped to THIS box's hi
    assert record["mean_objective"] == -5.0


def test_search_reports_the_warm_start_in_run_json(tmp_path, smoke_cfg, smoke_cfg_path,
                                                   monkeypatch):
    rd, _ = _source_run(tmp_path, monkeypatch, smoke_cfg_path, name="src2")
    cfg = _warm_cfg_raw(tmp_path, smoke_cfg_path, {"from_runs": [str(rd)]})
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    out = tmp_path / "r"
    cma_mod.search(fast_cfg(cfg, budget=4), out, "screen", backend=be, budget=4,
                   store=DatasetStore(out / "ds"))
    rj = json.loads((out / "run.json").read_text())
    assert rj["warm_start"]["mean_design_hash"]
    assert rj["warm_start"]["from_runs"] == [str(rd)]
    assert rj["warm_start"]["sources"][0]["config_sha"]


def test_bad_source_paths_and_types_are_configerrors(tmp_path, smoke_cfg_path):
    with pytest.raises(ConfigError, match="unknown key"):
        _warm_cfg_raw(tmp_path, smoke_cfg_path, {"from_runs": ["x"], "magic": 1})
    with pytest.raises(ConfigError, match="top_k"):
        _warm_cfg_raw(tmp_path, smoke_cfg_path, {"from_runs": ["x"], "top_k": 0})
    with pytest.raises(ConfigError, match="sigma_from_spread"):
        _warm_cfg_raw(tmp_path, smoke_cfg_path, {"from_runs": ["x"], "sigma_from_spread": 1})
    with pytest.raises(ConfigError, match="does not exist"):
        _warm_cfg_raw(tmp_path, smoke_cfg_path, {"from_runs": ["runs/definitely_missing"]})
    with pytest.raises(ConfigError, match="non-empty"):
        _warm_cfg_raw(tmp_path, smoke_cfg_path, {"from_runs": []})
