"""B.2 (day 2026-11-12): ``search.links`` — linked knobs are computed from their parent
(``scale * parent + offset``, clipped to ``[min, max]``) BEFORE meshing, removed from the CMA
dimension, recorded in run.json, and their seed value is ignored. Absent key = today's
behaviour byte for byte (same dimensions, no run.json key).
"""
from __future__ import annotations

import dataclasses
import json

import pytest
import yaml

from hornlab_search.config import ConfigError, load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.dataset.store import DatasetStore
from hornlab_search.search import cma as cma_mod
from hornlab_search.search.evaluate import read_ndjson
from hornlab_search.search.links import apply_links
from test_search_support import SyntheticBackend, fast_cfg, install_fakes


def _cfg_with_links(tmp_path, smoke_cfg_path, links):
    raw = yaml.safe_load(Path_read(smoke_cfg_path))
    raw["search"]["links"] = links
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def Path_read(p):
    from pathlib import Path
    return Path(p).read_text(encoding="utf-8")


@pytest.fixture
def smoke_cfg_path():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "examples" / "search_smoke.yaml"


# ------------------------------------------------------------------ config validation

def test_links_load_and_are_resolved(tmp_path, smoke_cfg_path):
    cfg = _cfg_with_links(tmp_path, smoke_cfg_path,
                          {"exponent": {"from": "s", "scale": 6.0, "offset": 1.0},
                           "n": {"from": "s", "scale": 4.0, "offset": 2.0, "min": 2.5}})
    assert cfg.search.links["n"] == {"from": "s", "scale": 4.0, "offset": 2.0,
                                     "min": 2.5, "max": 8.0}       # max defaults the bound hi
    assert cfg.search.links["exponent"] == {"from": "s", "scale": 6.0, "offset": 1.0,
                                            "min": 1.0, "max": 8.0}


@pytest.mark.parametrize("links,match", [
    ({"nope": {"from": "s"}}, "not a searched bound"),            # unknown knob
    ({"exponent": {"from": "nope"}}, "not a searched bound"),     # unknown parent
    ({"exponent": {"from": "n"}, "n": {"from": "s"}}, "one level only"),  # chain => refused
    ({"exponent": {"from": "exponent"}}, "one level only"),       # self-link (cycle)
    ({"exponent": {"from": "s", "scale": "2"}}, "finite number"),
    ({"exponent": {"from": "s", "offset": True}}, "finite number"),
    ({"exponent": {"from": "s", "maxx": 1}}, "unknown key"),
    ({"exponent": {"from": "s", "min": 9.0}}, "must lie inside"),
    ({"exponent": {"from": "s", "min": 5.0, "max": 2.0}}, "must lie inside"),
])
def test_links_bad_yaml_is_a_configerror(tmp_path, smoke_cfg_path, links, match):
    with pytest.raises(ConfigError, match=match):
        _cfg_with_links(tmp_path, smoke_cfg_path, links)


def test_links_with_a_generator_block_is_refused(tmp_path, smoke_cfg_path):
    raw = yaml.safe_load(Path_read(smoke_cfg_path))
    raw["search"]["links"] = {"exponent": {"from": "s"}}
    raw["generator"] = {"name": "whatever"}
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    with pytest.raises(ConfigError, match="generator"):
        load_config(p)


def test_absent_links_key_defaults_to_none(tmp_path, smoke_cfg_path):
    raw = yaml.safe_load(Path_read(smoke_cfg_path))
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    assert load_config(p).search.links is None


# ------------------------------------------------------------------ runtime behaviour

def test_reduce_space_removes_the_linked_knob_from_the_cma_dimension(smoke_cfg, tmp_path,
                                                                     smoke_cfg_path):
    raw = yaml.safe_load(Path_read(smoke_cfg_path))
    raw["search"]["links"] = {"exponent": {"from": "s"}}
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    cfg = load_config(p)
    space = DesignSpace.from_config(cfg)
    full_keys = DesignSpace.from_config(load_cfg_no_links(tmp_path, smoke_cfg_path)).keys()
    from hornlab_search.search import links as links_mod
    reduced, resolved = links_mod.reduce_space(space, cfg)
    assert "exponent" in full_keys and "exponent" not in reduced.keys()
    assert "s" in reduced.keys()                       # the parent stays searched
    assert resolved == {"exponent": {"from": "s", "scale": 1.0, "offset": 0.0,
                                     "min": 1.0, "max": 8.0}}


def load_cfg_no_links(tmp_path, smoke_cfg_path):
    raw = yaml.safe_load(Path_read(smoke_cfg_path))
    p = tmp_path / "cfg0.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return load_config(p)


def test_apply_links_scales_offsets_and_clips(tmp_path, smoke_cfg_path):
    cfg = _cfg_with_links(tmp_path, smoke_cfg_path,
                          {"exponent": {"from": "s", "scale": 10.0, "offset": 0.0,
                                        "min": 1.0, "max": 8.0}})
    space = DesignSpace.from_config(cfg)
    d = space.denormalize(space.normalize(space.seed))
    import copy
    stale = copy.deepcopy(d.params)
    stale["exponent"] = 12345.6                        # a seed/candidate value that must be ignored
    from hornlab_search.types import Design
    out = apply_links(Design("OSSE", stale), space, cfg)
    expected = min(max(10.0 * stale["s"], 1.0), 8.0)   # clipped to [1, 8]
    assert out.params["exponent"] == expected
    assert dict(stale)["exponent"] == 12345.6          # the input design is never mutated


def test_links_run_reaches_valid_designs_with_computed_params(tmp_path, smoke_cfg_path, monkeypatch):
    from pathlib import Path
    raw = yaml.safe_load(Path_read(smoke_cfg_path))
    raw["search"]["links"] = {"exponent": {"from": "s", "scale": 6.0, "offset": 1.0}}
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    cfg = load_config(p)
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    cma_mod.search(fast_cfg(cfg, budget=6), rd, "screen", backend=be, budget=6,
                   store=DatasetStore(rd / "ds"))
    rows = read_ndjson(rd / "search.ndjson")
    assert rows, "the search must have evaluated at least the seed"
    for r in rows:
        if r.get("kind") == "invalid_geometry":
            continue
        params = r["params"]
        expected = min(max(6.0 * params["s"] + 1.0, 1.0), 8.0)
        assert abs(params["exponent"] - expected) < 2e-9, (params["s"], params["exponent"])
    run_json = json.loads((rd / "run.json").read_text())
    assert run_json["links"] == {"exponent": {"from": "s", "scale": 6.0, "offset": 1.0,
                                              "min": 1.0, "max": 8.0}}


def test_default_run_json_has_no_links_key(smoke_cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    install_fakes(monkeypatch, be)
    rd = tmp_path / "r"
    cma_mod.search(fast_cfg(smoke_cfg, budget=3), rd, "screen", backend=be, budget=3,
                   store=DatasetStore(rd / "ds"))
    run_json = json.loads((rd / "run.json").read_text())
    assert "links" not in run_json
