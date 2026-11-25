"""CPU contracts for the CD wall-angle backbone under a retained return (cd-backbone-v1).

Dossier: docs/research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md (section 4 ladder).
No mesher, no solver.
"""
import copy

import numpy as np
import pytest

from conftest import REPO
from hornlab_search.config import brief_for_envelope_adapter, load_config
from hornlab_search.design.generators import _cd_backbone_v1 as kernel
from hornlab_search.design.generators import cd_backbone_family as bf
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.design.space import Bound, DesignSpace

CFG_DIR = REPO / "examples/typologies/cd_backbone_2026-11-25"
PAIRS = [("rolled_bb_control", "rolled_bb_h100"), ("lame_bb_control_m040", "lame_bb_h100_m040")]


def resolved(name):
    cfg = load_config(CFG_DIR / f"{name}.yaml")
    block = DesignSpace.from_config(cfg).seed.params["grid"]
    brief = brief_for_envelope_adapter(cfg.brief)
    return block, brief, bf.resolve_grid(block, brief)


@pytest.mark.parametrize("name", ["rolled_bb_control", "lame_bb_control", "lame_bb_control_m040"])
def test_neutral_is_bit_for_bit_parent(name):
    block, brief, child = resolved(name)
    _parent, _bb = bf._split(block["knobs"])
    parent = bf.PARENTS[block["rows"]["type"]].resolve_grid(bf._parent_block(block, _parent), brief)
    np.testing.assert_array_equal(child["inner_points"], parent["inner_points"])
    np.testing.assert_array_equal(child["outer_points"], parent["outer_points"])


def test_neutral_kernel_returns_the_same_array():
    inner = np.zeros((3, 5, 3))
    out, info = kernel.apply_to_inner(inner, {"bb_h": 0.0, "bb_v": 0.0, "bb_throat_frac": 0.15,
                                              "bb_rollin_frac": 0.30})
    assert out is inner and info == []


@pytest.mark.parametrize("control,cand", PAIRS)
def test_throat_return_rim_and_v_plane_are_kept(control, cand):
    _, _, base = resolved(control)
    _, _, geo = resolved(cand)
    p, q = base["inner_points"], geo["inner_points"]
    for j in range(p.shape[0]):
        f = int(np.argmax(p[j, :, 2]))
        np.testing.assert_allclose(q[j, f:], p[j, f:], atol=1e-9)        # roll-on station and return
        np.testing.assert_allclose(q[j, 0], p[j, 0], atol=1e-9)          # throat station
        assert np.all(np.diff(q[j, :f + 1, 2]) > 0)                       # monotone pre-roll
    np.testing.assert_array_equal(q[-1], p[-1])                           # bb_v = 0: V row untouched
    # inner-sheet extents are exact; the 3 mm shell is re-offset from the new inner wall, which moved
    # the rolled overall depth by 0.0017 mm (measured 2026-11-25) -- recorded, bounded at 0.01 mm
    for axis in range(2):
        assert np.abs(q[..., axis]).max() == pytest.approx(np.abs(p[..., axis]).max(), abs=1e-9)
    assert np.ptp(q[..., 2]) == pytest.approx(np.ptp(p[..., 2]), abs=1e-9)
    for key in ("mouth_w_mm", "mouth_h_mm", "x_span_mm"):
        np.testing.assert_allclose(geo["meta"][key], base["meta"][key], atol=0.01)
    assert np.abs(q - p).max() > 5.0                                      # the body really changed


@pytest.mark.parametrize("cand,theta_c", [("rolled_bb_h100", 36.5117), ("lame_bb_h100_m040", 32.2239)])
def test_reference_case_and_realised_body_angle(cand, theta_c):
    _, _, geo = resolved(cand)
    assert geo["meta"]["backbone_rows"]["theta_c_h_deg"] == pytest.approx(theta_c, abs=0.01)
    rho, z, f, u, th, _ = kernel._row_profile(geo["inner_points"][0])
    body = (u > 0.25) & (u < 0.65)
    np.testing.assert_allclose(th[body], theta_c, atol=1.0)


def test_strength_is_continuous_near_zero():
    _, _, base = resolved("rolled_bb_control")
    out, _ = kernel.apply_to_inner(base["inner_points"], {"bb_h": 1e-6, "bb_v": 1e-6,
                                                          "bb_throat_frac": 0.15, "bb_rollin_frac": 0.30})
    assert np.abs(out - base["inner_points"]).max() < 1e-3


@pytest.mark.parametrize("edit", [{"g_bb_h": 1.2}, {"g_bb_throat_frac": 0.30, "g_bb_rollin_frac": 0.55},
                                  {"g_bb_rollin_frac": 0.10}])
def test_invalid_law_is_rejected(edit):
    block, brief, _ = resolved("rolled_bb_h050")
    bad = copy.deepcopy(block)
    bad["knobs"].update(edit)
    with pytest.raises(GeneratorError):
        bf.resolve_grid(bad, brief)


def test_missing_key_and_tampered_recipe_are_rejected():
    block, brief, _ = resolved("lame_bb_h050_m040")
    bad = copy.deepcopy(block)
    del bad["knobs"]["g_bb_v"]
    with pytest.raises(GeneratorError):
        bf.resolve_grid(bad, brief)
    for key in ("schema", "implementation_sha256"):
        bad = copy.deepcopy(block)
        bad["rows"][key] = "invalid"
        with pytest.raises(GeneratorError):
            bf.resolve_grid(bad, brief)


def test_dormant_shape_search_is_refused():
    cfg = load_config(CFG_DIR / "rolled_bb_control.yaml")
    space = DesignSpace.from_config(cfg)
    bounds = dict(space.bounds)
    bounds["g_bb_throat_frac"] = Bound(0.10, 0.20, search=True)
    seed = dict(cfg.seed_params)
    with pytest.raises(GeneratorError):
        bf.validate_search_config(cfg.generator, seed, bounds, cfg.brief)
