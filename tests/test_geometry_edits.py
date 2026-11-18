"""Stage 4 WP 4.1 (2026-11-17): U3 freedoms as record edits, validity, point-grid hand-off."""
import pathlib
import tempfile

import numpy as np
import pytest

from hornlab_search.geometry import edits as E
from hornlab_search.geometry import record as R
from tests.conftest import requires_mesher
from tests.test_geometry_record import _elliptic_cone


def _rec():
    return R.sample_record(_elliptic_cone(n_mer=60, a0=12.7, b0=12.7, a1=280.0, b1=175.0,
                                          L=300.0), wall_thickness_mm=3.0)


def test_edits_pin_the_throat_and_keep_z():
    rec = _rec()
    for name, v in E.u3_variants(rec).items():
        assert np.allclose(v.inner[:, 0], rec.inner[:, 0]), name
        assert np.allclose(v.inner[:, :, 2], rec.inner[:, :, 2]), name
        assert v.meta["edit"] and v.meta["parent_digest"] == rec.digest()
        assert v.digest() != rec.digest()


def test_vertical_timing_hits_the_mouth_height_and_leaves_the_h_wall():
    rec = _rec()
    v = E.vertical_timing(rec, mouth_height_mm=460.0)
    assert R.descriptors(v)["mouth_height_mm"] == pytest.approx(460.0)
    assert np.allclose(v.inner[0], rec.inner[0])                 # H wall untouched (sin^2 0)
    val = E.validity(v, rec, envelope_mm={"width_mm": 600, "height_mm": 480, "depth_mm": 480})
    assert val["ok"] and val["reach_ge_5mm"] and val["throat_ring_unchanged"]


def test_termination_split_only_moves_the_lip_and_one_side():
    rec = _rec()
    h = E.termination_split(rec, side="h", extra_mm=15.0)
    n_lip = int(round((1 - E.LIP_FRACTION) * (rec.n_s - 1)))
    assert np.allclose(h.inner[:, :n_lip], rec.inner[:, :n_lip])
    assert R.descriptors(h)["mouth_width_mm"] == pytest.approx(R.descriptors(rec)["mouth_width_mm"] + 30.0)
    assert R.descriptors(h)["mouth_height_mm"] == pytest.approx(R.descriptors(rec)["mouth_height_mm"])


def test_section_steering_moves_the_corner_toward_the_superellipse():
    rec = _rec()                                                  # elliptic sections (p = 2)
    s = E.section_steering(rec, timing="late", exponent=3.0)
    mid = rec.n_phi // 2
    assert np.linalg.norm(s.inner[mid, -1, :2]) > np.linalg.norm(rec.inner[mid, -1, :2]) + 5.0
    e = E.section_steering(rec, timing="early", exponent=3.0)
    q = rec.n_s // 4
    assert np.linalg.norm(e.inner[mid, q, :2] - rec.inner[mid, q, :2]) > \
        np.linalg.norm(s.inner[mid, q, :2] - rec.inner[mid, q, :2])


def test_diagonal_pull_is_inward_at_45_only():
    rec = _rec()
    dpl = E.diagonal_pull(rec, pull_mm=10.0)
    mid = rec.n_phi // 2
    assert np.linalg.norm(rec.inner[mid, -1, :2]) - np.linalg.norm(dpl.inner[mid, -1, :2]) == pytest.approx(10.0, rel=1e-3)
    assert np.allclose(dpl.inner[0], rec.inner[0]) and np.allclose(dpl.inner[-1], rec.inner[-1])


def test_validity_flags_an_envelope_breach_and_a_fold():
    rec = _rec()
    big = E.vertical_timing(rec, mouth_height_mm=520.0)
    val = E.validity(big, rec, envelope_mm={"width_mm": 600, "height_mm": 480, "depth_mm": 480})
    assert val["inside_envelope"] is False and val["ok"] is False
    shrink = E.apply_radial_edit(rec, lambda u, p: -80.0 * np.sin(np.pi * u), name="pinch")
    assert E.validity(shrink, rec)["w_h_nondecreasing_before_lip"] is False


def test_record_to_grid_carries_angle_digest_and_wall():
    rec = _rec()
    g = E.record_to_grid(rec)
    assert g["inner_points"].shape == (61, 65, 3) and g["wall_thickness_mm"] == 3.0
    assert g["meta"]["record_digest"] == rec.digest() and g["meta"]["quarter"] is True
    assert g["meta"]["source_auto_angle_deg"] == pytest.approx(E.throat_half_angle_deg(rec))
    assert 0.0 < E.throat_half_angle_deg(rec) < 90.0


@requires_mesher
def test_control_and_variants_mesh_through_the_point_grid_route():
    pytest.importorskip("gmsh")
    from hornlab_search.config import load_config, mesh_spec
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.mesh.grid_build import build_grid_mesh
    root = pathlib.Path(__file__).resolve().parents[1]
    cfg = load_config(root / "examples" / "typologies" / "home_landscape_2026-11-15"
                      / "hl__biradial_es_style_v7.yaml")
    rec = R.record_for_design(DesignSpace.from_config(cfg).seed, cfg)
    ms = mesh_spec("screen", cfg)
    for name, v in [("control", rec), *E.u3_variants(rec).items()]:
        assert E.validity(v, rec)["ok"], name
        m = build_grid_mesh(E.record_to_grid(v, wall_thickness_mm=rec.wall_thickness_mm or 3.0),
                            ms, pathlib.Path(tempfile.mkdtemp()) / "m.msh", cfg, mode="screen")
        assert m is not None, name
