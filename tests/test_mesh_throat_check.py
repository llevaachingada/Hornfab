"""Round-throat check (owner rule 2026-10-27: no separate adapter; the horn starts round at the driver
exit). Offline: synthetic quarter meshes written with meshio, plus one stored mesh when present."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

meshio = pytest.importorskip("meshio")

from hornlab_search.mesh.throat_check import fits_exit, throat_shape  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def quarter_mesh(tmp_path, rx_mm, ry_mm, n=24, p=2.0) -> Path:
    """Quarter opening (x, y >= 0) as a fan of tag-2 triangles, plus one tag-1 wall triangle.
    ``p`` is the superellipse exponent of the rim (2 = ellipse)."""
    t = np.linspace(0.0, math.pi / 2, n + 1)
    c, s = np.cos(t), np.sin(t)
    x = rx_mm * 1e-3 * np.sign(c) * np.abs(c) ** (2.0 / p)
    y = ry_mm * 1e-3 * np.sign(s) * np.abs(s) ** (2.0 / p)
    pts = np.vstack([[0.0, 0.0, 0.0], np.column_stack([x, y, np.zeros_like(x)]), [0.05, 0.05, 0.05]])
    tri = np.array([[0, i, i + 1] for i in range(1, n + 1)] + [[1, n + 1, n + 2]])
    tag = np.array([2] * n + [1])
    path = tmp_path / "mesh.msh"
    meshio.write(path, meshio.Mesh(pts, [("triangle", tri)],
                                   cell_data={"gmsh:physical": [tag], "gmsh:geometrical": [tag]}),
                 file_format="gmsh22", binary=False)
    return path


def test_round_throat_matches_exit(tmp_path):
    s = throat_shape(quarter_mesh(tmp_path, 18.0, 18.0))
    assert s["width_mm"] == pytest.approx(36.0) and s["height_mm"] == pytest.approx(36.0)
    assert s["area_mm2"] == pytest.approx(math.pi * 18.0 ** 2, rel=0.01)
    assert fits_exit(s, 36.0) == (True, "round, matches the exit")
    assert fits_exit(s, 25.4)[0] is False


def test_stretched_and_squarish_throats_are_refused(tmp_path):
    ell = throat_shape(quarter_mesh(tmp_path, 13.0, 18.0))            # 26 x 36 ellipse
    ok, why = fits_exit(ell, 36.0)
    assert ok is False and "26.0 x 36.0" in why and "not round" not in why
    sq = throat_shape(quarter_mesh(tmp_path, 18.0, 18.0, p=4.0))      # rounded square, right size
    ok, why = fits_exit(sq, 36.0)
    assert ok is False and "not round" in why
    assert fits_exit(sq, None) == (None, "unknown")


def test_unreadable_mesh_is_unknown(tmp_path):
    s = throat_shape(tmp_path / "missing.msh")
    assert math.isnan(s["width_mm"]) and fits_exit(s, 36.0)[0] is None


STORED = REPO / "runs" / "20261027T104422Z-screen-a060fb" / "designs" / "589360bea375" / "mesh.msh"


@pytest.mark.skipif(not STORED.exists(), reason="stored campaign run not present (local data)")
def test_stored_rosse_winner_has_a_stretched_throat():
    s = throat_shape(STORED)                       # b3a__rosse_morph, aspect_ratio 0.73, 36 mm brief
    assert s["width_mm"] == pytest.approx(26.2, abs=0.2) and s["height_mm"] == pytest.approx(36.0, abs=0.2)
    assert fits_exit(s, 36.0)[0] is False
