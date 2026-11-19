# Offline tests for the lecleach H/V pair construction (a reconstruction of the published ellipsoidal-wavefront principle),
# 2026-11-16, item 13 of docs/queue/HOME_18H_PLAN_2026-11-16.md.
#
# Grounding: docs/research/typologies/LECLEACH_HV_ELLIPSOID_2026-11-16.md (sections cited per
# test); the rejected lobed bodies came from the old per-azimuth independent-march reading of
# the fc pair (run 20261116T040651Z-screen-e53ae9, rim non-elliptical +11% / +183% and
# axially non-planar 155-319 mm). These tests pin the properties the construction guarantees:
import math

import numpy as np
import pytest

from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import registry

AXI_BRIEF = {
    "driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0},
}

SPEC = {"rows": {"type": "lecleach"}, "n_phi": 15, "n_s": 32, "name": "grid"}


def _grid(knobs, spec=SPEC, brief=AXI_BRIEF):
    return G.rows_per_azimuth(spec, knobs, brief)


def _knobs(fc_h=450.0, fc_v=800.0, T=0.6, stop=200.0, **extra):
    knobs = {"g_fc_hz": fc_h, "g_fc_h_hz": fc_h, "g_fc_v_hz": fc_v,
             "g_T": T, "g_stop_deg": stop}
    knobs.update(extra)
    return knobs


def _segments_intersect(p1, p2, p3, p4, eps=1e-12):
    """True when 2-D segments p1-p2 and p3-p4 properly cross (side test, touching = no)."""
    def s(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = (s(p3, p4, p1), s(p3, p4, p2), s(p1, p2, p3), s(p1, p2, p4))
    return ((d1 * d2 < -eps) and (d3 * d4 < -eps))


def _row_self_intersects(x, y):
    """True when the row's 2-D polyline crosses itself (the rollback hook may fold back
    past 180 deg - the published deep-roll look - but must never cross itself)."""
    pts = np.column_stack([np.asarray(x), np.asarray(y)])
    n = len(pts)
    for i in range(n - 1):
        for j in range(i + 2, n - 1):
            if _segments_intersect(pts[i], pts[i + 1], pts[j], pts[j + 1]):
                return True
    return False


def test_hv_rows_share_one_station_chain_and_are_planar():
    """The rows share the core march's stations; the rim is one axial plane curve."""
    grid, meta = _grid(_knobs())
    # every row is pre-sampled at the SAME stations -> x identical per station
    # (compare directly: this numpy's assert_allclose refuses broadcastable shapes)
    assert float(np.max(np.abs(grid[:, :, 2] - grid[0, :, 2][None, :]))) <= 1e-9
    # rim planarity: the old failure was a 155-319 mm axial rim spread
    rim_x = grid[:, -1, 2]
    assert float(np.max(rim_x) - np.min(rim_x)) <= 1e-6


def test_hv_rows_mouth_outline_is_an_ellipse_and_convex():
    """The mouth edge equals the ellipse through the H/V plane endpoints; convex, no waist."""
    grid, meta = _grid(_knobs())
    phis = np.arctan2(grid[:, -1, 1], grid[:, -1, 0])
    r_end = np.hypot(grid[:, -1, 0], grid[:, -1, 1])
    a, b = float(r_end[0]), float(r_end[-1])
    r_ellipse = (a * b) / np.sqrt((b * np.cos(phis)) ** 2 + (a * np.sin(phis)) ** 2)
    np.testing.assert_allclose(r_end, r_ellipse, atol=1e-6 * max(a, b))
    # explicit convexity: no concave vertex anywhere on the closed rim (mirrored full ring)
    full = np.column_stack([
        np.concatenate([grid[:, -1, 0], -grid[::-1, -1, 0]]),
        np.concatenate([grid[:, -1, 1], grid[::-1, -1, 1]]),
    ])
    d = np.diff(full, axis=0)
    side = d[:, 0] * np.roll(d, -1, axis=0)[:, 1] - d[:, 1] * np.roll(d, -1, axis=0)[:, 0]
    assert int((side[:-1] < -1e-9).sum()) == 0


def test_hv_rows_body_silhouette_stays_convex_in_the_mouth_plane():
    """No lobes: the widest station per azimuth is convex too (the rejected bodies failed here)."""
    grid, _meta = _grid(_knobs())
    radii = np.hypot(grid[:, :, 0], grid[:, :, 1])
    j = np.argmax(radii, axis=1)
    sil = np.column_stack([grid[np.arange(len(j)), j, 0], grid[np.arange(len(j)), j, 1]])
    full = np.vstack([sil, sil[::-1] * np.array([-1.0, 1.0])])
    d = np.diff(full, axis=0)
    side = d[:, 0] * np.roll(d, -1, axis=0)[:, 1] - d[:, 1] * np.roll(d, -1, axis=0)[:, 0]
    assert int((side[:-1] < -1e-9).sum()) == 0


def test_hv_rows_never_self_intersect_and_keep_a_round_throat():
    """Every row is a simple curve (no lobes/folds through itself); the tuck-in of the
    deep-roll lip past ~200 deg stays small (the references' continuous rollback); station 0
    is the driver's round exit on every phi."""
    for fc_h, fc_v, T, stop in ((450.0, 800.0, 0.6, 200.0), (450.0, 800.0, 0.6, 240.0),
                                (300.0, 1150.0, 0.9, 200.0), (800.0, 450.0, 0.4, 170.0)):
        knobs = _knobs(fc_h=fc_h, fc_v=fc_v, T=T, stop=stop, **{"g_stop_a2": 0})
        grid, meta = _grid(knobs)
        for i in range(grid.shape[0]):
            assert not _row_self_intersects(grid[i, :, 2], np.hypot(grid[i, :, 0],
                                                                    grid[i, :, 1])), \
                f"row {i} (phi {meta['row_stop_deg'][i]:.1f} deg) self-intersects"
        radii = np.hypot(grid[:, :, 0], grid[:, :, 1])
        # the lip tuck-in (how far the rim recedes inside its own widest bearing):
        # report-bounded, not zero - the published rollback past 180 deg tucks
        tuck = float(np.max(radii.max(axis=1) - radii[:, -1]))
        assert tuck <= 0.08 * float(radii.max()), f"lip tuck-in {tuck:.1f} mm too deep"
        np.testing.assert_allclose(radii[:, 0], meta["throat_radius_mm"], atol=1e-9)
        assert meta["throat_radius_mm"] == pytest.approx(18.0, abs=1e-6)


def test_hv_rows_match_the_fc_product_invariant():
    """lib-2 4.3: W*fc_h ~= H*fc_v within 2 % (dossier validation item 3 / JMLC invariant).

    Checked WITHOUT the stop harmonic: the invariant is exact when both planes roll to
    the same depth; the per-plane stop law deliberately trades part of it for the
    per-plane rollback difference (reported, not enforced).
    """
    _grid_, meta = _grid(_knobs(stop=170.0))
    product = meta["mouth_fc_product_mm_hz"]
    assert product["width_x_fc_h"] == pytest.approx(product["height_x_fc_v"], rel=0.02)


def test_hv_rows_degenerate_to_the_axisymmetric_march_when_fc_h_equals_fc_v():
    """fc_h = fc_v (with no stop harmonic) reproduces the plain lecleach rows exactly."""
    knobs_pair = _knobs(fc_h=800.0, fc_v=800.0, stop=170.0)
    knobs_single = {"g_fc_hz": 800.0, "g_T": 0.6, "g_stop_deg": 170.0}
    grid_pair, _ = _grid(knobs_pair)
    grid_single, _ = _grid(knobs_single)
    np.testing.assert_allclose(grid_pair, grid_single, atol=1e-9)


def test_hv_rows_per_plane_rollback_follows_the_stop_harmonic():
    """a2 = the per-plane rollback difference: plane stops = stop0*(1 +/- a2), gated in range."""
    grid, meta = _grid(_knobs(stop=200.0, **{"g_stop_a2": 0.15}))
    assert meta["plane_stop_h_deg"] == pytest.approx(230.0)
    assert meta["plane_stop_v_deg"] == pytest.approx(170.0)
    assert meta["row_stop_deg"][0] == pytest.approx(230.0)
    assert meta["row_stop_deg"][-1] == pytest.approx(170.0)
    # the plane meridians keep their own march endpoints as the section axes
    assert meta["row_stop_actual_deg"][0] == pytest.approx(230.0)
    assert meta["row_stop_actual_deg"][-1] == pytest.approx(170.0)


def test_hv_rows_meta_carries_the_published_construction_labels():
    _grid_, meta = _grid(_knobs())
    assert meta["fc_core_hz"] == pytest.approx(math.sqrt(450.0 * 800.0))
    assert "construction_label" in meta and "base_construction_label" in meta
    assert "ellipse" in meta["section_law"]


def test_hv_fc_pair_ratio_is_capped_at_the_published_territory():
    """Ratio max/min <= 4 (E-JMLC territory 1.5-3.0 + margin); the old 300/1400 corner refused."""
    with pytest.raises(registry.GeneratorError, match="ratio"):
        _grid(_knobs(fc_h=300.0, fc_v=1400.0))
    # margin is honoured in both directions
    _grid_ , _meta = _grid(_knobs(fc_h=800.0, fc_v=3100.0))
    assert _meta["fc_core_hz"] == pytest.approx(math.sqrt(800.0 * 3100.0))
    with pytest.raises(registry.GeneratorError, match="ratio"):
        _grid(_knobs(fc_h=1400.0, fc_v=300.0))


def test_hv_rows_build_validly_across_the_config_box_corners():
    """Item-13 lesson: every box corner that the stop/ratio gates admit must build convex."""
    corners = [(300.0, 450.0), (300.0, 1150.0), (800.0, 450.0), (800.0, 1150.0),
               (450.0, 800.0)]
    for fc_h, fc_v in corners:
        for T in (0.4, 0.9):
            for stop, a2 in ((150.0, -0.3), (240.0, 0.35), (200.0, 0.15)):
                knobs = _knobs(fc_h=fc_h, fc_v=fc_v, T=T, stop=stop, **{"g_stop_a2": a2})
                try:
                    grid, meta = _grid(knobs)
                except registry.GeneratorError as exc:
                    # only the per-plane stop range gate may refuse (240*(1+0.35) > 240)
                    assert "stop" in str(exc), f"unexpected refusal at {fc_h}/{fc_v}/{T}/{stop}/{a2}: {exc}"
                    continue
                radii = np.hypot(grid[:, :, 0], grid[:, :, 1])
                for i in range(grid.shape[0]):
                    assert not _row_self_intersects(grid[i, :, 2], radii[i]), \
                        f"self-intersecting row at {fc_h}/{fc_v}/{T}/{stop}/{a2}, phi {i}"
                rim = np.hypot(grid[:, -1, 0], grid[:, -1, 1])
                a, b = float(rim[0]), float(rim[-1])
                phis = np.arctan2(grid[:, -1, 1], grid[:, -1, 0])
                r_ellipse = (a * b) / np.sqrt(
                    (b * np.cos(phis)) ** 2 + (a * np.sin(phis)) ** 2)
                np.testing.assert_allclose(
                    rim, r_ellipse, atol=1e-6 * max(a, b),
                    err_msg=f"non-elliptical rim at {fc_h}/{fc_v}/{T}/{stop}/{a2}")


def test_g_stop_a2_alias_feeds_the_stop_harmonic():
    """The 2026-11-16 scalar alias still maps to g_stop_cos2k[0] (default-off, documented)."""
    knobs = {"g_fc_hz": 450.0, "g_fc_h_hz": 450.0, "g_fc_v_hz": 800.0, "g_T": 0.6,
             "g_stop_deg": 200.0, "g_r_lip_mm": 0.0, "g_stop_a2": 0.15}
    grid, meta = _grid(knobs)
    assert meta["stop_cos2k"] == [0.15]
    assert meta["plane_stop_h_deg"] == pytest.approx(230.0)
