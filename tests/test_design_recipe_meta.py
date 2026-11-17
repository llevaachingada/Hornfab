"""WP 0.9 recipe metadata v2 (additive, non-identity) and the E-012 `mode` guard. Offline."""
import copy
import json

import pytest

from conftest import EXAMPLES
from hornlab_search.config import load_config
from hornlab_search.design import recipe_meta
from hornlab_search.design.families import to_mesher_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import sizing
from hornlab_search.types import Design, GeometryInvalidError, MeshSpec

ICW = dict(termination="flat_baffle", r0_mm=12.7, a0_deg=14.5, L_mm=160.0, R_mm=130.0,
           coverage_angle_deg=50.0, hold_start=0.3, hold_end=0.7)
MOUNT = {"type": "enclosure", "depth_mm": 250.0,
         "margins_mm": {"l": 10.0, "t": 10.0, "r": 10.0, "b": 10.0}, "edge_mm": 5.0,
         "plan": "rounded_rectangle"}


def _ms():
    return MeshSpec(epw=6.0, f_max_hz=10000.0, quadrants="1", max_triangles=73600)


def test_formula_route_resolves_mesher_defaults():
    m = recipe_meta.recipe_metadata(Design("ICW", dict(ICW)))
    assert m["schema"] == "recipe_meta_v2"
    assert m["termination"] == {"kind": "flat_baffle", "source": "family_param"}
    assert m["wall_thickness_mm"] == {"value": 6.0, "source": "mesher_default"}
    assert m["source_cap"]["angle_deg"] == 14.5 and m["source_cap"]["radius_mm"] is None
    assert m["source_cap"]["shape"] == 1 and m["source_cap"]["curvature"] == 0


def test_explicit_wall_and_enclosure_zero_wall():
    d = Design("ICW", {**ICW, "wall_thickness_mm": 4.0})
    assert recipe_meta.recipe_metadata(d)["wall_thickness_mm"] == {"value": 4.0, "source": "recipe"}
    e = recipe_meta.recipe_metadata(d, mounting=MOUNT)
    assert e["wall_thickness_mm"]["value"] == 0.0 and e["mode"] == "enclosure"


def test_unknown_termination_is_explicit_none():
    m = recipe_meta.recipe_metadata(Design("R-OSSE", {}))
    assert m["termination"] == {"kind": None, "source": "not_recorded"}


def test_grid_route_resolves_cap_radius_like_the_mesher():
    import numpy as np
    ring = np.zeros((4, 2, 3))
    for i, a in enumerate(np.linspace(0, 1.5, 4)):
        ring[i, 0] = [25.0 * np.cos(a), 25.0 * np.sin(a), 0.0]
    d = Design("FREEFORM", {"grid": {"wall_thickness_mm": 3.0}})
    m = recipe_meta.recipe_metadata(d, grid_inner=ring, grid_meta={"source_auto_angle_deg": 30.0})
    assert m["source_cap"]["source"] == "point_grid_resolved"
    assert m["source_cap"]["radius_mm"] == pytest.approx(25.0 / 0.5, rel=0.02)
    assert m["wall_thickness_mm"]["value"] == 3.0
    dflt = recipe_meta.recipe_metadata(Design("FREEFORM", {"grid": {}}))
    assert dflt["wall_thickness_mm"] == {"value": 3.0, "source": "grid_build_default"}


def test_metadata_never_raises():
    class Bad:
        family = "X"
        params = None
    out = recipe_meta.recipe_metadata(Bad())
    assert out["schema"] == "recipe_meta_v2"


def test_metadata_does_not_move_identity():
    """design hash / config_sha are functions of params and config raw only."""
    d = Design("ICW", dict(ICW))
    h = d.hash()
    recipe_meta.recipe_metadata(d)
    assert d.hash() == h and "recipe_meta" not in json.dumps(d.params)
    from hornlab_search.search import rundir
    cfg = load_config(EXAMPLES / "typologies" / "conical.yaml")
    sha = rundir.config_sha(cfg.raw)
    space = DesignSpace.from_config(cfg)
    seed = space.seed
    before = seed.hash()
    prov = space.provenance(seed)
    assert prov["recipe_meta"]["schema"] == "recipe_meta_v2"
    assert seed.hash() == before and rundir.config_sha(cfg.raw) == sha
    # the dataset/provenance copy of the generator block takes a fixed key list (evaluate.py)
    assert "recipe_meta" not in {k: prov[k] for k in ("name", "spec", "knobs", "brief", "brief_hash")}


def test_mode_key_cannot_overwrite_enclosure_flip(tmp_path):
    res = sizing.res_mm_for(6.0, 10000.0)
    d = Design("ICW", {**ICW, "mode": "freestanding"})
    with pytest.raises(GeometryInvalidError, match="contradicts brief.mounting"):
        to_mesher_config(d, _ms(), res, tmp_path / "m.msh", mounting=copy.deepcopy(MOUNT))
    ok = to_mesher_config(Design("ICW", dict(ICW)), _ms(), res, tmp_path / "m.msh",
                          mounting=copy.deepcopy(MOUNT))
    assert ok["mode"] == "enclosure" and "enclosure" in ok
    fs = to_mesher_config(Design("ICW", {**ICW, "mode": "bare"}), _ms(), res, tmp_path / "m.msh")
    assert fs["mode"] == "bare"
