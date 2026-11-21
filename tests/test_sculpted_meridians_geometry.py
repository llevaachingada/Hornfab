"""CPU checks of the experimental sampled-host and native meridian laws."""
from dataclasses import replace

import numpy as np
import pytest

from conftest import requires_mesher
from hornlab_search.geometry._sculpted_host_v1 import shape_host
from hornlab_search.geometry._sculpted_rosse_v1 import Body, Finish, Planes, finish_meridian, surface


@pytest.fixture
def host():
    phi = np.linspace(0, np.pi / 2, 9)
    z = np.r_[np.linspace(0, 250, 31), np.linspace(248, 230, 10)]
    rho = np.linspace(18, 290, len(z))
    inner = np.stack(np.broadcast_arrays(np.cos(phi[:, None]) * rho,
                                        np.sin(phi[:, None]) * rho,
                                        z[None, :]), axis=-1).copy()
    outer = inner.copy()
    outer[..., 0] += 3 * np.cos(phi[:, None])
    outer[..., 1] += 3 * np.sin(phi[:, None])
    return inner, outer


@pytest.fixture
def body():
    return Body(575.4637409703, 442.9517420413, 6.9356460581, Planes(37.5, 28, 20),
                Planes(.85, .85, .85), Planes(.2820232949, .2820232949, .2820232949),
                Planes(.0002388511, .0002388511, .0002388511), .9669894771, 2.4794610419, 3)


def test_host_zero_identity_and_protected_entrance(host):
    inner, outer = host
    a, b = shape_host(inner, outer, {}, wall_thickness_mm=3)
    assert a is inner and b is outer
    a, b = shape_host(inner, outer, {"body_h_axial_mm": -40, "body_v_axial_mm": 40,
                                    "body_h_radial_mm": 8}, wall_thickness_mm=3)
    np.testing.assert_array_equal(a[:, :5], inner[:, :5])
    np.testing.assert_array_equal(b[:, :5], outer[:, :5])
    np.testing.assert_allclose(b - a, outer - inner, atol=1e-13)


def test_host_axial_mapping_preserves_real_return_and_plane_values(host):
    inner, outer = host
    a, _ = shape_host(inner, outer, {"body_h_axial_mm": -40, "body_v_axial_mm": 40,
                                     "body_diagonal_axial_mm": 10}, wall_thickness_mm=3)
    # On the plateau H=-40, diagonal=-40/2+40/2+10, V=+40 mm.
    np.testing.assert_allclose((a - inner)[[0, 4, 8], 28, 2], [-40, 10, 40], atol=1e-12)
    before = np.diff(inner[..., 2], axis=1)
    after = np.diff(a[..., 2], axis=1)
    assert np.all(np.sign(after) == np.sign(before))
    assert np.any(after < 0)


def test_host_terminal_is_independent_of_body(host):
    inner, outer = host
    body_controls = {"body_h_axial_mm": -20, "body_v_axial_mm": 20}
    terminal = {"terminal_h_axial_mm": -3, "terminal_v_axial_mm": 2,
                "terminal_diagonal_radial_mm": 1}
    body, _ = shape_host(inner, outer, body_controls, wall_thickness_mm=3)
    combined, _ = shape_host(inner, outer, {**body_controls, **terminal}, wall_thickness_mm=3)
    only, _ = shape_host(inner, outer, terminal, wall_thickness_mm=3)
    np.testing.assert_allclose(combined - body, only - inner, atol=1e-13)
    np.testing.assert_array_equal(only[:, :20], inner[:, :20])
    np.testing.assert_allclose((only - inner)[[0, 4, 8], -1, 2], [-3, -.5, 2])


def test_planes_and_finish():
    p = Planes(10, 22, 30)
    np.testing.assert_allclose(p.at(np.array([0, np.pi/4, np.pi/2])), [10, 22, 30])
    z = np.linspace(0, 100, 101)
    rho = np.linspace(18, 120, 101)
    a, b = finish_meridian(z, rho, 0, Finish())
    assert a is z and b is rho
    a, b = finish_meridian(z, rho, 0, Finish(axial_mm=Planes(-3, 0, 0)))
    np.testing.assert_array_equal(a[:70], z[:70])
    assert a[-1] == 97 and b[-1] == rho[-1]
    c, d = finish_meridian(z, rho, 0, Finish(roundover_mm=Planes(2, 0, 0)))
    np.testing.assert_array_equal([c[0], c[-1], d[0], d[-1]], [z[0], z[-1], rho[0], rho[-1]])
    assert np.max(np.hypot(c - z, d - rho)) > 1.5


@requires_mesher
def test_native_rev7_against_published_equations():
    from hornlab_mesher.profile_formulas import profile_points

    radius, throat, k, q, m, r = 200., 12.7, 1.5, 3.8, .75, .35
    c1 = (k * throat)**2
    c2 = 2 * k * throat * np.tan(np.deg2rad(5))
    c3 = np.tan(np.deg2rad(35))**2
    length = (np.sqrt(c2**2 - 4*c3*(c1 - (radius + throat*(k - 1))**2)) - c2) / (2*c3)
    t = np.linspace(0, 1, 5)
    axial = length * (np.hypot(r, m) - np.hypot(r, t-m))
    bore = np.sqrt(c1 + c2*length*t + c3*(length*t)**2) + throat*(1-k)
    mouth = radius + length * (1 - np.sqrt(1 + c3*(t-1)**2))
    expected = np.column_stack((axial, (1-t**q)*bore + t**q*mouth))
    spec = dict(type="R-OSSE", R=radius, r0=throat, k=k, a=35, a0=5,
                q=q, m=m, r=r, b=0, tmax=1)
    np.testing.assert_allclose(profile_points(spec, 5), expected, rtol=0, atol=1e-10)


@requires_mesher
def test_native_rosse_collar_source_and_aperture(body):
    kwargs = dict(radius_mm=18, source_angle_deg=2, wall_mm=3,
                  collar_mm=(8, 42), n_phi=9, n_s=81)
    a, outer = surface(body, Finish(), **kwargs)
    modified, _ = surface(replace(body, angle_deg=Planes(42, 32, 22)), Finish(), **kwargs)
    assert a.shape == outer.shape == (9, 81, 3)
    np.testing.assert_allclose(np.hypot(a[:, 0, 0], a[:, 0, 1]), 18, atol=1e-10)
    np.testing.assert_allclose(a[:, 0, 2], 0, atol=1e-10)
    # Every native point inside the collar lies on the same round cone.
    rho = np.hypot(a[..., 0], a[..., 1])
    mask = a[..., 2] <= 8
    np.testing.assert_allclose(rho[mask], 18 + np.tan(np.deg2rad(2))*a[..., 2][mask], atol=1e-10)
    np.testing.assert_allclose(np.hypot(a[:, -1, 0], a[:, -1, 1]),
                               np.hypot(modified[:, -1, 0], modified[:, -1, 1]), atol=1e-9)
    assert np.max(np.abs(a[..., 2] - modified[..., 2])) > 1
    assert np.any(np.diff(a[..., 2], axis=1) < 0)


@pytest.mark.parametrize("controls", [{"invalid": 1}, {"body_h_axial_mm": -100},
                                      {"body_h_radial_mm": float('nan')},
                                      {"body_h_radial_mm": -1000}])
def test_host_invalid_controls_refused(host, controls):
    with pytest.raises(ValueError):
        shape_host(*host, controls, wall_thickness_mm=3)


@requires_mesher
def test_rosse_invalid_controls_refused(body):
    with pytest.raises(ValueError, match="opening angle"):
        surface(replace(body, angle_deg=Planes(90, 30, 20)), Finish(), radius_mm=18,
                source_angle_deg=2, wall_mm=3, collar_mm=(8, 20), n_phi=9, n_s=81)
    with pytest.raises(ValueError, match="terminal start"):
        finish_meridian(np.arange(5.), np.arange(5.) + 18, 0,
                        Finish(start_arc=Planes(.4, .4, .4)))
