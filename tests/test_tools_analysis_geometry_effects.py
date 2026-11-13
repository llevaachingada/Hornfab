"""Focused tests for tools/analysis/geometry_effects.py (B2 M0, offline; no mesh/BEM).

All sampling goes through the installed ``hornlab_mesher`` point-grid API (pure numpy, no gmsh).
The tests assert the hardening decision's required geometry facts:
  * target-1 morph exponent invariance and target-3 activity;
  * s1/s2 stretch conditionality;
  * H/V symmetry exchange;
  * diagonal (corner) contour change without a cardinal change;
  * units/scale and separation of sampled-surface equivalence from Design.hash;
  * CAD / non-star-shaped refusals and the recorded sampling-convergence check.
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import REPO, requires_mesher
from test_tools_analysis_common import load_tool

ge = load_tool("geometry_effects")

CONFIG = REPO / "examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml"
RES = 12.0


@pytest.fixture(scope="module")
def cfg():
    from hornlab_search.config import load_config

    return load_config(CONFIG)


@pytest.fixture(scope="module")
def space(cfg):
    from hornlab_search.design.space import DesignSpace

    return DesignSpace.from_config(cfg)


@pytest.fixture(scope="module")
def seed(space):
    return space.seed


def _sample(design, cfg, *, res=RES, converge=False):
    return ge.sample_surface(design, cfg, resolution_mm=res, check_convergence=converge)


@requires_mesher
def test_sampler_records_grid_units_symmetry_and_convergence(seed, cfg):
    s = _sample(seed, cfg, converge=True)
    assert s.units == "mm"
    assert s.radius_mm.shape == (len(ge.CANONICAL_ANGLES_DEG), len(ge.CANONICAL_T))
    assert s.meridians_mm["H"].shape == (len(ge.CANONICAL_T),)
    assert 0.0 in s.azimuths_deg and 45.0 in s.azimuths_deg and 90.0 in s.azimuths_deg
    assert s.grid["quadrants"] == "1"
    assert s.grid["symmetry_planes"] == ["x", "y"]
    assert s.grid["seam"] == "mirror planes (no seam)"
    assert s.descriptors["throat_radius_mm"] == pytest.approx(25.4, abs=1e-6)
    assert s.descriptors["mouth_width_mm"] == pytest.approx(397.0, abs=0.5)
    assert s.descriptors["mouth_height_mm"] == pytest.approx(397.0, abs=0.5)
    assert s.descriptors["depth_mm"] > 0.0
    assert s.descriptors["area_full_domain_mm2"] == pytest.approx(
        s.descriptors["area_sampled_mm2"] * 4.0)
    assert s.descriptors["stretch_active"] is True
    assert s.convergence["checked"] is True
    assert s.convergence["converged"] is True
    assert "not mesh" in s.convergence["note"]
    assert s.provenance["api"].endswith("resolve_geometry")
    # The fixture records a canonical cross-section, not a single scalar.
    assert len(s.cross_sections) == len(ge.STATION_FRACTIONS)
    assert all(len(cs["radius_mm"]) == len(ge.CANONICAL_ANGLES_DEG)
               for cs in s.cross_sections)


@requires_mesher
def test_target1_morph_exponent_is_invariant_but_hash_differs(seed, cfg):
    a = _sample(seed, cfg)
    b = _sample(ge.with_params(seed, morph_exponent=8.0), cfg)
    delta = ge.surface_delta(a, b)
    assert delta["max_abs_radius_delta_mm"] == 0.0
    assert delta["changed"] is False
    assert delta["design_hashes_equal"] is False
    assert delta["surface_fingerprints_equal"] is True
    assert ge.surfaces_equivalent(a, b) is True


@requires_mesher
def test_target3_morph_exponent_is_active(seed, cfg):
    base = ge.with_params(seed, morph_target=3, morph_exponent=2.0)
    other = ge.with_params(seed, morph_target=3, morph_exponent=8.0)
    a = _sample(base, cfg)
    b = _sample(other, cfg)
    delta = ge.surface_delta(a, b)
    assert delta["max_abs_radius_delta_mm"] > 1.0
    assert delta["changed"] is True
    assert delta["surface_fingerprints_equal"] is False
    assert ge.meridian_activity(a, b, "diagonal_45")["changed"] is True


@requires_mesher
def test_stretch_conditionality_s1_s2(seed, cfg):
    # s2 == 0 makes s1 a no-op, and s1 == 0 makes s2 a no-op (installed stretch_is_inactive).
    base = ge.with_params(seed, s1=1.0, s2=0.0)
    a = _sample(base, cfg)
    b = _sample(ge.with_params(base, s1=1.3), cfg)
    assert ge.surface_delta(a, b)["max_abs_radius_delta_mm"] == 0.0
    base2 = ge.with_params(seed, s1=0.0, s2=0.015)
    c = _sample(base2, cfg)
    d = _sample(ge.with_params(base2, s2=0.035), cfg)
    assert ge.surface_delta(c, d)["max_abs_radius_delta_mm"] == 0.0
    # With both nonzero the same perturbations change the surface.
    e = _sample(ge.with_params(seed, s1=1.0, s2=0.025), cfg)
    f = _sample(ge.with_params(seed, s1=1.3, s2=0.025), cfg)
    assert ge.surface_delta(e, f)["changed"] is True


@requires_mesher
def test_hv_symmetry_exchange(seed, cfg):
    wide = ge.with_params(seed, morph_width_mm=430.0, morph_height_mm=300.0)
    tall = ge.with_params(seed, morph_width_mm=300.0, morph_height_mm=430.0)
    a = _sample(wide, cfg)
    b = _sample(tall, cfg)
    # The H cut of the wide horn is exactly the V cut of the tall horn.
    assert np.max(np.abs(a.meridians_mm["H"] - b.meridians_mm["V"])) < 1e-9
    assert np.max(np.abs(a.meridians_mm["V"] - b.meridians_mm["H"])) < 1e-9
    assert ge.meridian_activity(a, b, "H")["changed"] is True
    assert ge.surface_delta(a, b)["changed"] is True


@requires_mesher
def test_diagonal_contour_changes_without_cardinal_change(seed, cfg):
    square = ge.with_params(seed, morph_width_mm=397.0, morph_height_mm=397.0,
                            morph_corner_mm=0.0)
    rounded = ge.with_params(seed, morph_width_mm=397.0, morph_height_mm=397.0,
                             morph_corner_mm=60.0)
    a = _sample(square, cfg)
    b = _sample(rounded, cfg)
    assert ge.meridian_activity(a, b, "diagonal_45")["changed"] is True
    assert ge.meridian_activity(a, b, "diagonal_135")["changed"] is True
    assert ge.meridian_activity(a, b, "H")["changed"] is False
    assert ge.meridian_activity(a, b, "V")["changed"] is False


@requires_mesher
def test_units_and_scale(seed, cfg):
    p = dict(seed.params)
    scaled = ge.with_params(
        seed,
        r0_mm=p["r0_mm"] * 2.0,
        L_mm=p["L_mm"] * 2.0,
        morph_width_mm=p["morph_width_mm"] * 2.0,
        morph_height_mm=p["morph_height_mm"] * 2.0,
        morph_corner_mm=p["morph_corner_mm"] * 2.0,
        s1=p["s1"] * 2.0,
        s2=p["s2"] / 2.0,
    )
    a = _sample(seed, cfg)
    b = _sample(scaled, cfg)
    assert b.units == "mm"
    assert b.descriptors["depth_mm"] == pytest.approx(
        2.0 * a.descriptors["depth_mm"], rel=2e-3)
    assert b.descriptors["mouth_width_mm"] == pytest.approx(
        2.0 * a.descriptors["mouth_width_mm"], rel=2e-3)
    assert b.descriptors["mouth_height_mm"] == pytest.approx(
        2.0 * a.descriptors["mouth_height_mm"], rel=2e-3)
    assert b.descriptors["area_full_domain_mm2"] == pytest.approx(
        4.0 * a.descriptors["area_full_domain_mm2"], rel=6e-3)
    assert b.descriptors["aspect_ratio"] == pytest.approx(
        a.descriptors["aspect_ratio"], rel=1e-3)


@requires_mesher
def test_cad_and_grid_surfaces_refuse(seed, cfg):
    from hornlab_search.types import Design

    with pytest.raises(ge.UnsupportedGeometryError):
        _sample(Design("FREEFORM", {"cad": {"tool": "x"}}), cfg)
    with pytest.raises(ge.UnsupportedGeometryError):
        _sample(Design("FREEFORM", {"grid": {"knobs": {}}}), cfg)


def test_non_star_shaped_points_refuse():
    # A synthetic folded surface: z decreases along the axial station at one azimuth.
    p = np.zeros((4, 3, 3), dtype=float)
    p[:, :, 0] = np.array([10.0, 20.0, 30.0])[None, :]
    p[:, :, 1] = 0.0
    p[:, :, 2] = np.array([0.0, 1.0, 0.5])[None, :]
    with pytest.raises(ge.UnsupportedGeometryError):
        ge.assert_star_shaped(p)
    ok = p.copy()
    ok[:, :, 2] = np.array([0.0, 1.0, 2.0])[None, :]
    ge.assert_star_shaped(ok)  # does not raise


@requires_mesher
def test_surface_fingerprint_is_not_a_design_hash(seed, cfg):
    a = _sample(seed, cfg)
    b = _sample(ge.with_params(seed, morph_exponent=8.0), cfg)
    assert ge.surface_fingerprint(a) == ge.surface_fingerprint(b)
    assert a.design_hash != b.design_hash
    assert ge.surface_delta(a, b)["design_hashes_equal"] is False
