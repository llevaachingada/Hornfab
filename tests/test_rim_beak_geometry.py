"""CPU contracts for the rim-beak overlay (kind beak_v1, rim-beak-v1). One mesher call; no solver."""
import copy
import hashlib
import tempfile
from pathlib import Path

import numpy as np
import pytest

from conftest import REPO
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design.generators import _rim_beak_v1 as kernel
from hornlab_search.design.generators import cd_backbone_rows_family as rf
from hornlab_search.design.generators import rim_beak_family as kf
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.design.space import DesignSpace

CFG = REPO / "examples/typologies/cd_bo_cohort_2026-11-25"


def _seed(name):
    cfg = load_config(CFG / f"{name}.yaml")
    space = DesignSpace.from_config(cfg)
    return cfg, space, space.seed.params["grid"]


def _with(block, brief, **rb):
    knobs = {**block["knobs"], **{f"g_{k}": float(v) for k, v in rb.items()}}
    spec = {k: v for k, v in block.items() if k != "knobs"}
    spec["rows"] = {"type": kf.KIND, "parent_rows": {k: v for k, v in block["rows"]["parent_rows"].items()
                                                     if k not in ("schema", "implementation_sha256")}}
    spec["rows"]["parent_rows"]["parent_rows"] = block["rows"]["parent_rows"]["parent_rows"]
    out = kf.design_params(spec, knobs, brief)["grid"]
    return out, kf.resolve_grid(out, brief)


@pytest.mark.parametrize("name", ["lcl_beak_cohort", "iwar_beak_cohort"])
def test_neutral_returns_parent_bit_for_bit(name):
    cfg, _space, block = _seed(name)
    child = kf.resolve_grid(block, cfg.brief)
    pblock = kf._parent_block(block, kf._split(block["knobs"])[0])
    parent = rf.resolve_grid(pblock, cfg.brief)
    np.testing.assert_array_equal(child["inner_points"], parent["inner_points"])
    assert "outer_points" not in child


def test_neutral_verify_mesh_matches_rows_bb_parent():
    from hornlab_search.mesh.build import build_mesh
    shas = []
    for name in ("lcl_beak_cohort", "lcl_bb_cohort"):
        cfg = load_config(CFG / f"{name}.yaml")
        with tempfile.TemporaryDirectory() as td:
            mesh = build_mesh(DesignSpace.from_config(cfg).seed, mesh_spec("verify", cfg), cfg, Path(td),
                              mode="verify")
            shas.append(hashlib.sha256(Path(mesh.path).read_bytes()).hexdigest())
    assert shas[0] == shas[1]


def test_beak_moves_lips_and_keeps_throat_and_early_wall():
    cfg, _space, block = _seed("lcl_beak_cohort")
    base = np.asarray(kf.resolve_grid(block, cfg.brief)["inner_points"], float)
    _b, geo = _with(block, cfg.brief, rb_h_mm=40.0, rb_v_mm=-25.0, rb_d_mm=0.0, rb_start_frac=0.6)
    new = np.asarray(geo["inner_points"], float)
    np.testing.assert_array_equal(new[..., :2], base[..., :2])          # purely axial
    for j, expect in ((0, 40.0), (new.shape[0] - 1, -25.0)):
        f = int(np.argmax(base[j, :, 2]))
        np.testing.assert_allclose(new[j, f:, 2] - base[j, f:, 2], expect, atol=1e-9)   # rigid lip/return/rim
        assert int(np.argmax(new[j, :, 2])) == f
        np.testing.assert_array_equal(new[j, :3, 2], base[j, :3, 2])   # throat and early wall untouched
    assert geo["meta"]["rim_beak_rows"]["dz_h_mm"] == pytest.approx(40.0)
    assert any("rim beak" in n for n in geo["meta"]["notes"])
    assert "outer_points" in geo


def test_kernel_neutral_and_limits():
    arr = np.zeros((3, 6, 3))
    out, info = kernel.apply_to_inner(arr, {"rb_h_mm": 0.0, "rb_v_mm": 0.0, "rb_d_mm": 0.0, "rb_start_frac": 0.6})
    assert out is arr and info == []
    with pytest.raises(ValueError):
        kernel.validate_rb({"rb_h_mm": 61.0, "rb_v_mm": 0.0, "rb_d_mm": 0.0, "rb_start_frac": 0.6})


def test_recipe_refusals():
    cfg, _space, block = _seed("lcl_beak_cohort")
    for edit in ({"schema": "x"}, {"implementation_sha256": "x"}, {"parent_rows": {"type": "lecleach"}}):
        bad = copy.deepcopy(block)
        bad["rows"].update(edit)
        with pytest.raises(GeneratorError):
            kf.resolve_grid(bad, cfg.brief)
    bad = copy.deepcopy(block)
    bad["span"] = "full"
    with pytest.raises(GeneratorError):
        kf.resolve_grid(bad, cfg.brief)


def test_bo_encoding_round_trip():
    from hornlab_search.bo.encoding import ActiveProjection
    for name in ("lcl_beak_cohort", "iwar_beak_cohort"):
        _cfg, space, _block = _seed(name)
        proj = ActiveProjection.identity(space)
        assert proj.denormalize(proj.normalize_design(space.seed)).hash() == space.seed.hash()
