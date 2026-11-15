"""Independent geometry checks for the original rolled-rectangle experiment.

Numerical case and source limits: ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md.
No workers, BEM, Julia or GPU are involved.
"""
import copy
import math
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import quad
import yaml

from tools.geometry.rolled_rect import make_grid, spiral_reference, surface_at, validate_shape

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPES = ROOT/"examples/prototypes/rolled_rect_2026-11-15"
DRIVER = {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0}


@pytest.fixture
def shape():
    return yaml.safe_load((PROTOTYPES/"rect_reference.yaml").read_text())["shape"]


@pytest.mark.parametrize("decay", [0.0, 0.55, 0.7, 0.85])
@pytest.mark.parametrize("turn", [math.pi/2, math.pi, 1.5*math.pi])
def test_reference_matches_independent_quadrature(decay, turn):
    expected = [quad(lambda a: math.exp(-decay*a)*f(a), 0, turn)[0]
                for f in (math.cos, math.sin)]
    assert np.allclose(spiral_reference(turn, decay), expected, rtol=1e-12, atol=1e-12)


def test_round_throat_and_driver_tangent_in_every_azimuth(shape):
    phis = np.linspace(0, math.pi/2, 49)
    # Two tiny turns test the physical derivative, not a coarse mesh chord.
    p = surface_at(shape, DRIVER, [0, 1e-7, 2e-7], phis)
    assert np.max(np.abs(np.hypot(p[:, 0, 0], p[:, 0, 1])-18)) < 1e-12
    assert np.array_equal(p[:, 0, 2], np.zeros(len(phis)))
    rho = np.hypot(p[..., 0], p[..., 1])
    slope = (rho[:, 1]-rho[:, 0])/(p[:, 1, 2]-p[:, 0, 2])
    assert np.max(np.abs(slope-math.tan(math.radians(2)))) < 1e-6


def test_rectangular_dimensions_are_independent_and_corners_do_not_form_star(shape):
    phis = np.linspace(0, math.pi/2, 2001)
    for width, height in [(542, 299), (560, 310)]:
        s = {**shape, "width_mm": width, "height_mm": height}
        p = surface_at(s, DRIVER, [math.pi], phis)[:, 0]
        assert abs(2*np.max(p[:, 0])-width) < 1e-10
        assert abs(2*np.max(p[:, 1])-height) < 1e-10
        # A convex superellipse never pushes a corner past its rectangular envelope.
        lhs = (p[:, 0]/(width/2))**s["rect_exponent"]+(p[:, 1]/(height/2))**s["rect_exponent"]
        assert np.allclose(lhs, 1, atol=1e-12)
        top = p[(p[:, 0] < width/4) & (p[:, 0] > 0)]
        assert np.ptp(top[:, 1]) < 0.02  # near-straight central half of the top edge


def test_axial_and_radial_return_are_real(shape):
    t = np.linspace(0, 1.5*math.pi, 1001)
    p = surface_at({**shape, "depth_h_ratio": 1.0}, DRIVER, t, [0, math.pi/2])
    for row in p:
        radius = np.hypot(row[:, 0], row[:, 1])
        assert 89 < np.rad2deg(t[np.argmax(row[:, 2])]) < 91
        assert 179 < np.rad2deg(t[np.argmax(radius)]) < 181
        assert row[-1, 2] < np.max(row[:, 2])-50
        assert radius[-1] < np.max(radius)-5


def test_hv_pucker_is_axial_only_and_preserves_throat(shape):
    phis = np.linspace(0, math.pi/2, 49)
    t = np.linspace(0, 1.5*math.pi, 201)
    base = surface_at(shape, DRIVER, t, phis)
    changed = surface_at({**shape, "pucker_h_mm": 12, "pucker_v_mm": 16}, DRIVER, t, phis)
    assert np.array_equal(base[..., :2], changed[..., :2])
    assert np.array_equal(base[:, :40], changed[:, :40])
    assert np.allclose(changed[0, -1, 2]-base[0, -1, 2], 12)
    assert np.allclose(changed[-1, -1, 2]-base[-1, -1, 2], 16)
    assert np.min(changed[:, -1, 2]-base[:, -1, 2]) < -10


def test_quarter_shell_and_sampling_converge(shape):
    from hornlab_search.design.generators.grid import grid_outer_points
    brief = {"driver": DRIVER}
    coarse, meta = make_grid(shape, brief)
    fine, _ = make_grid({**shape, "n_phi": 97, "n_s": 192}, brief)
    assert meta["quarter"] and meta["symmetry_plane"] == "yz+xz"
    assert np.array_equal(coarse[0, :, 1], np.zeros(coarse.shape[1]))
    assert np.array_equal(coarse[-1, :, 0], np.zeros(coarse.shape[1]))
    outer = grid_outer_points(coarse, shape["wall_thickness_mm"])
    assert np.isfinite(outer).all()  # existing self-approach guard also executes
    for grid in (coarse, fine):
        assert np.all(np.linalg.norm(np.cross(np.gradient(grid, axis=0),
                                             np.gradient(grid, axis=1)), axis=-1) > 0)
    # Both use identical arc station fractions; interpolation convergence is geometric.
    assert np.max(np.linalg.norm(coarse-fine[::2, ::2], axis=-1)) < 0.01


def test_rejects_bad_or_unrecognized_parameters(shape):
    for change in [{"n_phi": 12}, {"decay": float("nan")}, {"terminal_deg": 360},
                   {"height_mm": 600}, {"pucker_h_mm": 100}, {"rect_exponent": 30},
                   {"typo_mm": 3}]:
        s = copy.deepcopy(shape)
        s.update(change)
        with pytest.raises(ValueError):
            validate_shape(s)
