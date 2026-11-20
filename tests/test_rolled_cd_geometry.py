"""Focused CPU contracts for the rolled-CD wall-angle law (rolled_family_rect_cd_v1).

Covers dossier rungs V0-V5: zero-control identity, construction identity (throat/lip/return),
angle realisation, schema/digest/driver guards, envelope and shape guards. No mesher, no solver.
"""
import copy

import numpy as np
import pytest

from conftest import REPO
from hornlab_search.config import load_config
from hornlab_search.design.generators import _rolled_rect_cd_v1 as kernel
from hornlab_search.design.generators import rolled_cd_family as rc
from hornlab_search.design.generators import rolled_family as rf
from hornlab_search.design.generators.registry import GeneratorError
from hornlab_search.design.space import DesignSpace

CFG_DIR = REPO / "examples/typologies/rolled_cd_2026-11-20"


def space(name):
    return DesignSpace.from_config(load_config(CFG_DIR / f"{name}.yaml"))


def parent_block(block):
    knobs = {key: value for key, value in block["knobs"].items() if not key.startswith("g_cd_")}
    rows = copy.deepcopy(block["rows"])
    rows.update(type=rf.KINDS[0], schema=rf.SCHEMA,
                implementation_sha256=rf.implementation_digest())
    out = {key: block[key] for key in ("n_phi", "n_s", "wall_thickness_mm") if key in block}
    out.update(rows=rows, knobs=knobs)
    return out


def test_zero_control_is_bit_for_bit_parent():
    cfg = load_config(CFG_DIR / "control.yaml")
    block = space("control").seed.params["grid"]
    parent = rf.resolve_grid(parent_block(block), cfg.brief)
    child = rc.resolve_grid(block, cfg.brief)
    np.testing.assert_array_equal(child["inner_points"], parent["inner_points"])
    np.testing.assert_array_equal(child["outer_points"], parent["outer_points"])
    for key in ("mouth_w_mm", "mouth_h_mm", "x_span_mm"):
        assert child["meta"][key] == parent["meta"][key]
    assert "cd" not in child["meta"]


def test_neutral_kernel_returns_the_same_array():
    inner = np.zeros((5, 7, 3))
    neutral = {"cd_h_deg": 0.0, "cd_v_deg": 0.0,
               "cd_start_s": 0.3, "cd_peak_s": 0.6, "cd_end_s": 0.88}
    assert kernel.is_neutral(neutral)
    assert kernel.apply_to_inner(inner, neutral) is inner


@pytest.mark.parametrize("name", ["candidate", "variant"])
def test_lip_mouth_and_rolled_return_are_unchanged(name):
    control = load_config(CFG_DIR / "control.yaml")
    parent = rf.resolve_grid(parent_block(space("control").seed.params["grid"]), control.brief)
    child = rc.resolve_grid(space(name).seed.params["grid"], load_config(CFG_DIR / f"{name}.yaml").brief)
    end = child["meta"]["cd"]["cd_end_s"]
    for row in range(child["inner_points"].shape[0]):
        base = parent["inner_points"][row]
        rho = np.hypot(base[:, 0], base[:, 1])
        z = base[:, 2]
        forward = int(np.argmax(z))
        ds = np.hypot(np.diff(z[:forward + 1]), np.diff(rho[:forward + 1]))
        u = np.r_[0.0, np.cumsum(ds)] / np.sum(ds)
        np.testing.assert_array_equal(child["inner_points"][row, forward], base[forward])
        outside = u >= end
        assert outside.any()
        np.testing.assert_array_equal(
            child["inner_points"][row, :forward + 1][outside],
            base[:forward + 1][outside])
    for key in ("mouth_w_mm", "mouth_h_mm", "x_span_mm"):
        np.testing.assert_allclose(child["meta"][key], parent["meta"][key], atol=1e-9)


@pytest.mark.parametrize("name,axis", [("candidate", "h"), ("variant", "h")])
def test_wall_angle_schedule_is_realised(name, axis):
    control = load_config(CFG_DIR / "control.yaml")
    parent = rf.resolve_grid(parent_block(space("control").seed.params["grid"]), control.brief)
    cfg = load_config(CFG_DIR / f"{name}.yaml")
    child = rc.resolve_grid(space(name).seed.params["grid"], cfg.brief)
    row = 0 if axis == "h" else -1
    a, b, c = (child["meta"]["cd"][key] for key in ("cd_start_s", "cd_peak_s", "cd_end_s"))
    base = parent["inner_points"][row]
    rho0 = np.hypot(base[:, 0], base[:, 1])
    z0 = base[:, 2]
    forward = int(np.argmax(z0))
    ds = np.hypot(np.diff(z0[:forward + 1]), np.diff(rho0[:forward + 1]))
    s = np.r_[0.0, np.cumsum(ds)]
    u = s / s[-1]
    a0 = np.degrees(np.arctan2(np.diff(rho0[:forward + 1]), np.diff(z0[:forward + 1])))
    dat = child["inner_points"][row]
    rho1 = np.hypot(dat[:forward + 1, 0], dat[:forward + 1, 1])
    z1 = dat[:forward + 1, 2]
    a1 = np.degrees(np.arctan2(np.diff(rho1), np.diff(z1)))
    _bt, bp_full = kernel.window(u, a, b, c)
    mid = (u[:-1] + u[1:]) / 2
    _bm, bp = kernel.window(mid, a, b, c)
    amp = np.radians(child["meta"]["cd"]["cd_" + axis + "_deg"])
    target = np.degrees(amp * bp / np.max(np.abs(bp_full)))
    inside = (mid >= a) & (mid <= c)
    deviation = a1 - a0
    assert np.max(np.abs(deviation[inside])) > 0.5 * abs(np.degrees(amp))
    assert np.max(np.abs(deviation[inside] - target[inside])) < 1.0
    assert abs(np.mean(deviation[inside])) < 1.0


@pytest.mark.parametrize("name", ["candidate", "variant"])
def test_rolling_guards(name):
    cfg = load_config(CFG_DIR / f"{name}.yaml")
    geometry = rc.resolve_grid(space(name).seed.params["grid"], cfg.brief)
    for row in range(geometry["inner_points"].shape[0]):
        z = geometry["inner_points"][row, :, 2]
        rho = np.hypot(geometry["inner_points"][row, :, 0],
                       geometry["inner_points"][row, :, 1])
        forward = int(np.argmax(z))
        assert np.all(np.diff(z[:forward + 1]) > 0)
        assert np.all(np.diff(rho[:forward + 1]) >= -1e-9)
    for sheet in ("inner_points", "outer_points"):
        pts = geometry[sheet]
        assert np.isfinite(pts).all()
        normal = np.cross(np.gradient(pts, axis=0), np.gradient(pts, axis=1))
        assert np.min(np.linalg.norm(normal, axis=-1)) > 1e-9


def test_schema_digest_and_driver_are_guarded():
    cfg = load_config(CFG_DIR / "candidate.yaml")
    block = copy.deepcopy(space("candidate").seed.params["grid"])
    rc.resolve_grid(block, cfg.brief)
    for key in ("schema", "implementation_sha256"):
        bad = copy.deepcopy(block)
        bad["rows"][key] = "invalid"
        with pytest.raises(GeneratorError):
            rc.resolve_grid(bad, cfg.brief)
    bad = copy.deepcopy(block)
    bad["rows"]["driver"]["exit_radius_mm"] += 1.0
    with pytest.raises(GeneratorError):
        rc.resolve_grid(bad, cfg.brief)


@pytest.mark.parametrize("edit", [
    {"g_cd_h_deg": 30.0},
    {"g_cd_start_s": 0.60, "g_cd_peak_s": 0.50},
    {"g_cd_end_s": 0.99},
    {"g_cd_missing": 0.0},
])
def test_invalid_law_is_rejected(edit):
    cfg = load_config(CFG_DIR / "control.yaml")
    block = copy.deepcopy(space("control").seed.params["grid"])
    block["knobs"].update(edit)
    with pytest.raises(GeneratorError):
        rc.resolve_grid(block, cfg.brief)


@pytest.mark.parametrize("name", ["candidate", "variant"])
def test_envelope_and_mouth_unchanged(name):
    cfg = load_config(CFG_DIR / f"{name}.yaml")
    geometry = rc.resolve_grid(space(name).seed.params["grid"], cfg.brief)
    env = cfg.brief["envelope"]
    assert geometry["meta"]["mouth_w_mm"] <= env["max_mouth_w_mm"]
    assert geometry["meta"]["mouth_h_mm"] <= env["max_mouth_h_mm"]
    assert geometry["meta"]["x_span_mm"] <= env["max_depth_mm"]
    control_cfg = load_config(CFG_DIR / "control.yaml")
    base = rc.resolve_grid(space("control").seed.params["grid"], control_cfg.brief)
    np.testing.assert_allclose(geometry["meta"]["mouth_w_mm"], base["meta"]["mouth_w_mm"], atol=1e-9)
    np.testing.assert_allclose(geometry["meta"]["mouth_h_mm"], base["meta"]["mouth_h_mm"], atol=1e-9)
