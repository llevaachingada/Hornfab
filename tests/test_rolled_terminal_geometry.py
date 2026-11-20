"""Focused CPU contracts for the H-only rolled terminal roll/C law.

Covers the additive zero control, V/throat/depth preservation, the roll-onset/lip landmarks,
digest/schema/driver guards, rolling guards and composition with the front-load CD law.
No mesher, no solver.
"""
import copy

import numpy as np
import pytest

from conftest import REPO
from hornlab_search.config import load_config
from hornlab_search.design.generators import _rolled_rect_terminal_v1 as tm
from hornlab_search.design.generators import rolled_family as rf
from hornlab_search.design.generators import rolled_terminal_family as rt
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.design.space import DesignSpace

CFG = REPO / "examples/typologies/rolled_terminal_2026-11-20"
W500 = REPO / "examples/typologies/rolled_size_2026-11-20/hl__rolled_size_w500.yaml"


def space(path):
    return DesignSpace.from_config(load_config(path))


def parent_geometry():
    sp = space(W500)
    return rf.resolve_grid(sp.seed.params["grid"], sp.brief)


def child_geometry(name):
    sp = space(CFG / f"{name}.yaml")
    return rt.resolve_grid(sp.seed.params["grid"], sp.brief), sp


def test_neutral_is_bit_for_bit_width500():
    base = parent_geometry()
    neutral, _ = child_geometry("neutral")
    np.testing.assert_array_equal(neutral["inner_points"], base["inner_points"])
    np.testing.assert_array_equal(neutral["outer_points"], base["outer_points"])
    for key in ("mouth_w_mm", "mouth_h_mm", "x_span_mm"):
        assert neutral["meta"][key] == base["meta"][key]


def test_v_cut_throat_and_depth_are_unchanged():
    base = parent_geometry()
    child, _ = child_geometry("candidate")
    np.testing.assert_array_equal(child["inner_points"][-1], base["inner_points"][-1])
    np.testing.assert_array_equal(child["outer_points"][-1], base["outer_points"][-1])
    # Throat rows (all azimuths at station 0) are untouched.
    np.testing.assert_array_equal(child["inner_points"][:, 0], base["inner_points"][:, 0])
    for key in ("mouth_h_mm", "x_span_mm"):
        np.testing.assert_allclose(child["meta"][key], base["meta"][key], atol=1e-2)  # outer-shell micron shift


def test_h_roll_onset_and_lip_landmarks():
    base = parent_geometry()
    child, _ = child_geometry("candidate")
    base_h = base["inner_points"][0]
    h = child["inner_points"][0]
    x, z = h[:, 0], h[:, 2]
    half = float(base_h[:, 0].max())
    forward = int(np.argmax(z))
    zf = float(z[forward])
    assert abs(float(x.max()) - half) < 1e-6
    assert abs(float(z.max()) - float(base_h[:, 2].max())) < 1e-9
    max_idx = int(np.argmax(x))
    # Roll onset: first return station at 0.88 of the half-width.
    onset = np.where(x[max_idx:] <= 0.88 * half)[0][0] + max_idx
    assert abs(float(x[onset]) - 0.88 * half) < 1e-6
    assert abs(float(z[onset]) - (zf - 35.0)) < 0.5
    # Returned lip: 0.76 of the half-width, 70 mm below the forward station.
    assert abs(float(x[-1]) - 0.76 * half) < 1e-6
    assert abs(float(z[-1]) - (zf - 70.0)) < 0.5
    # The terminal is a genuine inward C after the maximum: x and z non-increasing.
    assert np.all(np.diff(x[max_idx:]) <= 1e-9)
    # z is non-increasing through the C; the returned-lip Hermite endpoint may rise by <0.01 mm.
    assert np.all(np.diff(z[forward:]) <= 1e-2)
    assert child["meta"]["mouth_w_mm"] <= 500.5


def test_surfaces_are_finite_and_non_degenerate():
    child, _ = child_geometry("candidate")
    for sheet in ("inner_points", "outer_points"):
        pts = child[sheet]
        assert np.isfinite(pts).all()
        normal = np.cross(np.gradient(pts, axis=0), np.gradient(pts, axis=1))
        assert np.min(np.linalg.norm(normal, axis=-1)) > 1e-9


def test_envelope():
    cfg = load_config(CFG / "candidate.yaml")
    child, _ = child_geometry("candidate")
    env = cfg.brief["envelope"]
    assert child["meta"]["mouth_w_mm"] <= env["max_mouth_w_mm"]
    assert child["meta"]["mouth_h_mm"] <= env["max_mouth_h_mm"]
    assert child["meta"]["x_span_mm"] <= env["max_depth_mm"]


@pytest.mark.parametrize("edit", [
    {"g_tm_roll_frac": 0.99},
    {"g_tm_lip_frac": 0.95},
    {"g_tm_max_drop_mm": 40.0},
    {"g_tm_lip_angle_deg": 250.0},
])
def test_invalid_law_is_rejected(edit):
    sp = space(CFG / "candidate.yaml")
    block = copy.deepcopy(sp.seed.params["grid"])
    block["knobs"].update(edit)
    with pytest.raises(GeneratorError):
        rt.resolve_grid(block, sp.brief)


def test_schema_digest_and_driver_are_guarded():
    sp = space(CFG / "candidate.yaml")
    block = copy.deepcopy(sp.seed.params["grid"])
    rt.resolve_grid(block, sp.brief)
    for key in ("schema", "implementation_sha256"):
        bad = copy.deepcopy(block)
        bad["rows"][key] = "invalid"
        with pytest.raises(GeneratorError):
            rt.resolve_grid(bad, sp.brief)
    bad = copy.deepcopy(block)
    bad["rows"]["driver"]["exit_radius_mm"] += 1.0
    with pytest.raises(GeneratorError):
        rt.resolve_grid(bad, sp.brief)


def test_composes_with_front_load_cd():
    sp = space(CFG / "candidate.yaml")
    block = copy.deepcopy(sp.seed.params["grid"])
    block["knobs"].update({"g_cd_h_deg": -10.0, "g_cd_v_deg": -6.0})
    combo = rt.resolve_grid(block, sp.brief)
    cd_only = copy.deepcopy(block)
    cd_only["knobs"]["g_tm_roll_frac"] = 0.0
    cd_base = rt.resolve_grid(cd_only, sp.brief)
    np.testing.assert_array_equal(combo["inner_points"][-1], cd_base["inner_points"][-1])
    neutral, _ = child_geometry("neutral")
    assert not np.array_equal(combo["inner_points"], neutral["inner_points"])
    assert combo["meta"]["cd"]["cd_h_deg"] == -10.0
    assert combo["meta"]["terminal"]["tm_roll_frac"] == 0.88


def test_neutral_kernel_identity_object():
    pts = np.zeros((5, 7, 3))
    neutral = {"tm_roll_frac": 0.0, "tm_lip_frac": 0.76, "tm_max_drop_mm": 20.0,
               "tm_roll_drop_mm": 35.0, "tm_lip_drop_mm": 70.0, "tm_lip_angle_deg": 170.0}
    assert tm.is_neutral(neutral)
    assert tm.apply_to_inner(pts, neutral) is pts
