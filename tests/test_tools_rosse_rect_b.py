"""R-OSSE rolled-rectangle b-term contract (CPU only).

The b term is an axial bow. The family used to reject b < 0 outright, but a real-mesher
check on the 570 x 419 home seed built cleanly from -0.01 to -0.10, with the axial span
growing from 422 mm to 449 mm inside the 480 mm brief envelope. These tests pin the small
negative floor and the forward-bow direction without touching a solver.
"""
from __future__ import annotations

import numpy as np
import pytest

from tools.geometry import rosse_rect

DRIVER = {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0}
BRIEF = {
    "driver": DRIVER,
    "envelope": {"max_mouth_w_mm": 600.0, "max_mouth_h_mm": 480.0, "max_depth_mm": 480.0},
}
SHAPE = {
    "width_mm": 570.0106756648,
    "height_mm": 418.9439515532,
    "rect_exponent": 6.18064457,
    "a_h_deg": 36.9859895859,
    "a_v_deg": 17.8035069811,
    "a_diag_deg": 0.0,
    "k": 2.4192833474,
    "r": 0.3159812735,
    "m": 0.85,
    "b": -0.05,
    "q": 3.0,
    "tmax": 0.9727936653,
    "wall_thickness_mm": 3.0,
    "n_phi": 25,
    "n_s": 48,
}


def test_small_negative_b_meshes_and_bows_forward():
    shape = dict(SHAPE)
    rosse_rect.validate_shape(shape)
    points, _meta = rosse_rect.make_grid(shape, BRIEF)
    assert np.isfinite(points).all()
    assert np.ptp(points[..., 2]) < 480.0

    neutral, _ = rosse_rect.make_grid(dict(shape, b=0.0), BRIEF)
    assert np.ptp(points[..., 2]) > np.ptp(neutral[..., 2])


def test_b_below_the_tested_floor_is_rejected():
    with pytest.raises(ValueError, match=r"need b in \[-0.10,1\]"):
        rosse_rect.validate_shape(dict(SHAPE, b=-0.11))
