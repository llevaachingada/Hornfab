"""meridian_sanity: clean cone passes; S-curve, throat pinch and over-deep rollback are caught; a short lip
reversal (beak) and a smooth one-way rollback are allowed."""
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools/analysis"))
import meridian_sanity as M  # noqa: E402


def _grid(angles_deg, ds=2.0):
    """Two-row grid whose H and V meridians follow the same wall-angle list (from the axis)."""
    r, z, pts = 18.0, 0.0, [(18.0, 0.0)]
    for a in angles_deg:
        r += ds * math.sin(math.radians(a))
        z += ds * math.cos(math.radians(a))
        pts.append((r, z))
    p = np.array(pts)
    q = np.zeros((2, len(p), 3))
    q[0, :, 0], q[0, :, 2] = p[:, 0], p[:, 1]
    q[1, :, 1], q[1, :, 2] = p[:, 0], p[:, 1]
    return q


def test_clean_flare_and_smooth_rollback_pass():
    assert M.check_grid(_grid(np.linspace(8, 60, 120)))["ok"]
    roll = np.concatenate([np.linspace(8, 60, 150), np.linspace(60, 190, 40)])
    assert M.check_grid(_grid(roll))["ok"]


def test_s_curve_pinch_and_deep_rollback_are_flagged():
    s = np.concatenate([np.linspace(8, 40, 50), np.linspace(40, 25, 30), np.linspace(25, 60, 60)])
    assert "s_curve" in M.check_grid(_grid(s))["h"]["flags"]
    pinch = np.concatenate([np.linspace(9, 3, 30), np.linspace(3, 50, 90)])
    assert "throat_pinch" in M.check_grid(_grid(pinch))["v"]["flags"]
    assert "deep_rollback" in M.check_grid(_grid(np.linspace(8, 260, 200)))["h"]["flags"]


def test_short_lip_reversal_is_lip_treatment_not_an_s_curve():
    lip = np.concatenate([np.linspace(8, 55, 180), np.linspace(55, 49, 12)])
    assert M.check_grid(_grid(lip))["ok"]
