import numpy as np
import pytest
from hornlab_search.design.generators import lecleach_swept_hv as L, profiles

BASE = dict(g_fc_hz=500., g_T=.5, g_stop_deg=118., g_ar_m=1., g_ar_p=1.,
            g_lame_p_mouth=2., g_lip_radius_mm=0., g_rim_sweep_mm=0., g_axial_length_factor=1.)


def run(params):
    return L.make_grid(params, throat_radius_mm=18., throat_half_angle_deg=2., n_phi=17, n_s=80)


def test_round_parent_and_throat():
    pts, meta = run(BASE)
    z, r, _, _ = profiles.lecleach_exact(18., 500., .5, 2., 118.)
    arc = np.r_[0., np.cumsum(np.hypot(np.diff(z), np.diff(r)))]
    expected = np.interp(np.linspace(0, arc[-1], 81), arc, r)
    assert np.allclose(np.hypot(pts[:, :, 0], pts[:, :, 1]), expected)
    assert np.allclose(np.hypot(pts[:, 0, 0], pts[:, 0, 1]), 18.)
    assert meta['area_mode'] == 'flat_section_parent'


def test_sweep_is_zero_at_throat_and_measured_at_rim():
    base, _ = run(dict(BASE, g_ar_m=1.7, g_lame_p_mouth=3.))
    swept, meta = run(dict(BASE, g_ar_m=1.7, g_lame_p_mouth=3., g_rim_sweep_mm=10.))
    assert np.allclose(base[:, 0], swept[:, 0])
    assert swept[0, -1, 2] == pytest.approx(base[0, -1, 2] - 10.)
    assert swept[-1, -1, 2] == pytest.approx(base[-1, -1, 2])
    assert meta['depth_mm'] == pytest.approx(np.ptp(swept[:, :, 2]))


def test_unsupported_or_unknown_fields_refused():
    with pytest.raises(ValueError): run(dict(BASE, g_lip_radius_mm=-2.))
    with pytest.raises(ValueError): run(dict(BASE, g_axial_length_factor=1.5))
    with pytest.raises(ValueError): run(dict(BASE, typo=2))
    with pytest.raises(ValueError): run(dict(BASE, g_ar_p=.5))


def test_warp_hits_sampled_parent_bbox_depth():
    pts, meta = run(dict(BASE, g_axial_length_factor=1.2))
    assert meta['depth_mm'] == pytest.approx(1.2 * meta['parent_depth_mm'], rel=1e-9)
    assert np.allclose(np.hypot(pts[:, 0, 0], pts[:, 0, 1]), 18.)
    assert meta['axial_warp_delta_mm'] > 0


def test_lip_appends_circular_arc_without_moving_parent():
    base, _ = run(BASE)
    lip, meta = run(dict(BASE, g_lip_radius_mm=8.))
    assert np.allclose(lip[:, :81], base)
    assert lip.shape[1] == 89
    chord = np.linalg.norm(lip[:, -1] - lip[:, 80], axis=1)
    assert np.allclose(chord, 2 * 8 * np.sin(np.pi / 8))
    assert meta['lip_wrap_deg'] == 45
    assert meta['lip_continuity'] == 'tangent_to_discrete_march_interpolant_unvalidated'


@pytest.mark.parametrize("stop", [85., 118., 175.])
def test_lip_uses_transformed_discrete_march_endpoint_tangent(stop):
    params = dict(BASE, g_stop_deg=stop, g_ar_m=1.7, g_lame_p_mouth=3.5,
                  g_rim_sweep_mm=12., g_axial_length_factor=1.2, g_lip_radius_mm=8.)
    pts, _ = run(params)
    z, r, angle, _ = profiles.lecleach_exact(18., 500., .5, 2., stop)
    theta = np.radians(angle[-1])
    assert angle[-1] >= stop
    assert np.arctan2(r[-1] - r[-2], z[-1] - z[-2]) == pytest.approx(theta)
    phi = np.linspace(0., np.pi / 2., pts.shape[0])
    end = pts[:, 80, :]
    scale = np.hypot(end[:, 0], end[:, 1]) / r[-1]
    tr = scale * np.sin(theta)
    tz = np.full_like(tr, np.cos(theta))
    tangent = np.column_stack((tr*np.cos(phi), tr*np.sin(phi), tz))
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    normal = np.column_stack((tangent[:, 2]*np.cos(phi), tangent[:, 2]*np.sin(phi),
                              -np.hypot(tangent[:, 0], tangent[:, 1])))
    u = np.pi / 32
    expected = end + 8 * (np.sin(u)*tangent + (1-np.cos(u))*normal)
    assert np.allclose(pts[:, 81, :], expected, atol=1e-10)
    chord = pts[:, 81, :] - end
    chord /= np.linalg.norm(chord, axis=1)[:, None]
    assert np.allclose(np.sum(chord*tangent, axis=1), np.cos(u/2), atol=1e-12)
