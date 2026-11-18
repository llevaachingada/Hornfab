"""Stage 3 WP 3.1/3.2 (2026-11-17): canonical surface record, contract v2."""
import math

import numpy as np
import pytest

from hornlab_search.geometry import record as R


def _elliptic_cone(n_mer=20, n_pts=50, a0=12.7, b0=12.7, a1=240.0, b1=160.0, L=300.0):
    """Quarter of an elliptical conical horn: section half-axes grow linearly with z."""
    phi = np.linspace(0, math.pi / 2, n_mer)
    z = np.linspace(0, L, n_pts) ** 1.0
    a = a0 + (a1 - a0) * z / L
    b = b0 + (b1 - b0) * z / L
    pts = np.empty((n_mer, n_pts, 3))
    for i, p in enumerate(phi):
        pts[i, :, 0] = a * math.cos(p)
        pts[i, :, 1] = b * math.sin(p)
        pts[i, :, 2] = z
    return pts


def test_shape_units_and_endpoints():
    rec = R.sample_record(_elliptic_cone())
    assert rec.inner.shape == (61, 65, 3) and rec.arc_length_mm.shape == (61, 65)
    assert np.allclose(rec.inner[0, -1], [240.0, 0.0, 300.0], atol=1e-9)    # H wall at the mouth
    assert np.allclose(rec.inner[-1, -1], [0.0, 160.0, 300.0], atol=1e-9)   # V wall at the mouth
    assert rec.sampler_version == R.SAMPLER_VERSION


def test_determinism_byte_identical_and_digest_stable():
    a = R.sample_record(_elliptic_cone())
    b = R.sample_record(_elliptic_cone())
    assert a.inner.tobytes() == b.inner.tobytes() and a.digest() == b.digest()
    c = R.sample_record(_elliptic_cone(a1=240.001))
    assert c.digest() != a.digest() and 0.0 < a.max_deviation_mm(c) < 0.01


def test_refinement_moves_points_little():
    coarse = R.sample_record(_elliptic_cone(n_mer=20))
    fine = R.sample_record(_elliptic_cone(n_mer=80))
    assert coarse.max_deviation_mm(fine) < 2.0   # linear azimuth interp of an ellipse, 20 meridians
    fine2 = R.sample_record(_elliptic_cone(n_mer=160))
    assert fine.max_deviation_mm(fine2) < coarse.max_deviation_mm(fine)


def test_descriptors_of_elliptic_cone():
    d = R.descriptors(R.sample_record(_elliptic_cone(n_mer=200)))
    assert d["mouth_width_mm"] == pytest.approx(480.0) and d["mouth_height_mm"] == pytest.approx(320.0)
    assert d["depth_mm"] == pytest.approx(300.0) and d["rollback"] is False
    assert d["area_mm2"][-1] == pytest.approx(math.pi * 240 * 160, rel=2e-3)
    assert d["shape_index"][-1] == pytest.approx(math.pi / 4, rel=2e-3)
    assert d["aspect"][-1] == pytest.approx(1.5, rel=1e-6)
    # H wall half-angle of a cone is constant: atan((240-12.7)/300)
    want = math.degrees(math.atan((240 - 12.7) / 300))
    assert np.allclose(d["h_wall_angle_deg"][2:-2], want, atol=0.05)


def test_envelope_margins_signed():
    rec = R.sample_record(_elliptic_cone(n_mer=200), wall_thickness_mm=5.0)
    m = R.envelope_margins(rec, {"width_mm": 600, "height_mm": 300, "depth_mm": 480})
    assert m["width_mm"] == pytest.approx(600 - 490) and m["height_mm"] == pytest.approx(300 - 330)
    assert m["depth_mm"] == pytest.approx(180.0)
    m0 = R.envelope_margins(rec, {"width_mm": 600}, include_wall=False)
    assert m0["width_mm"] == pytest.approx(120.0) and m0["height_mm"] is None


def test_rollback_lip_is_kept_by_arc_length():
    pts = _elliptic_cone()
    lip = np.linspace(0, math.pi * 0.75, 15)
    ext = []
    for m in pts:
        r_end, z_end = np.hypot(*m[-1, :2]), m[-1, 2]
        ux, uy = m[-1, 0] / r_end, m[-1, 1] / r_end
        rr = r_end + 20 * np.sin(lip)
        zz = z_end + 20 * (1 - np.cos(lip)) * 0 + 20 * np.sin(lip) - 20 * (1 - np.cos(lip))
        ext.append(np.c_[m, ][:, :].tolist() + [[r * ux, r * uy, z] for r, z in zip(rr[1:], zz[1:])])
    rec = R.sample_record(np.asarray(ext))
    assert R.descriptors(rec)["rollback"] is True


@pytest.mark.parametrize("bad,reason", [
    (np.zeros((5, 10, 3)), R.R_ZERO_MERIDIAN),
    (np.zeros((5, 10, 2)), R.R_BAD_INPUT),
])
def test_typed_refusals(bad, reason):
    with pytest.raises(R.RecordRefusal) as e:
        R.sample_record(bad)
    assert e.value.reason == reason


def test_nonmonotone_azimuth_refused():
    pts = _elliptic_cone()[::-1].copy()
    pts[[3, 4]] = pts[[4, 3]]
    with pytest.raises(R.RecordRefusal) as e:
        R.sample_record(pts)
    assert e.value.reason == R.R_NONMONOTONE_PHI


def test_cad_and_ported_designs_refused():
    from hornlab_search.types import Design
    with pytest.raises(R.RecordRefusal) as e:
        R.native_points(Design("FREEFORM", {"mid_ports": [1]}), None)
    assert e.value.reason == R.R_PORTS


def test_record_for_a_real_generator_design_without_meshing():
    from pathlib import Path
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    cfg = load_config(Path(__file__).resolve().parents[1] / "examples" / "typologies" / "hypex.yaml")
    seed = DesignSpace.from_config(cfg).seed
    rec = R.record_for_design(seed, cfg)
    assert rec.inner.shape == (61, 65, 3) and rec.route == "native"
    assert rec.meta["design_hash"] == seed.hash()
    assert rec.inner[0, 0, 0] == pytest.approx(12.7)          # brief driver exit radius
    assert R.record_for_design(seed, cfg).digest() == rec.digest()
