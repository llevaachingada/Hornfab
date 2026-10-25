"""Pin guard for the WP10 point-grid adapter's mesher API (issue #9 precedent).

``mesh/grid_build.py`` calls a non-``__init__`` mesher surface: the ``PointGridHornGeometry``
dataclass, ``MeshDensity``, and ``build_mesh_with_info``. A silent signature change in the
installed package would invalidate every GRID mesh, so this test names the exact API the adapter
depends on. Validated against the pinned fork/installed mesher b922e807.
"""
from __future__ import annotations

import dataclasses
import inspect

import pytest

from conftest import requires_mesher

pytestmark = requires_mesher

PIN_NOTE = ("the pinned hornlab_mesher API (validated at b922e807) changed; "
            "mesh/grid_build.py depends on this exact surface")


def test_point_grid_geometry_fields_the_adapter_sets():
    from hornlab_mesher.geometry import PointGridHornGeometry

    names = {f.name for f in dataclasses.fields(PointGridHornGeometry)}
    needed = {"inner_points", "outer_points", "closed", "symmetry_planes", "wall_thickness_mm",
              "source_shape", "source_auto_angle_deg"}
    missing = needed - names
    assert not missing, f"{PIN_NOTE}: PointGridHornGeometry lacks {sorted(missing)}"


def test_mesh_density_fields_and_positional_trap():
    from hornlab_mesher.geometry import MeshDensity

    names = [f.name for f in dataclasses.fields(MeshDensity)]
    needed = {"throat_res_mm", "mouth_res_mm", "rear_res_mm", "aperture_res_scale",
              "max_triangles", "allow_large_mesh"}
    missing = needed - set(names)
    assert not missing, f"{PIN_NOTE}: MeshDensity lacks {sorted(missing)}"
    # grid_build.py constructs MeshDensity with KEYWORDS on purpose: field 4 is
    # aperture_res_scale, not max_triangles (the positional trap).
    assert names[3] == "aperture_res_scale", (
        f"{PIN_NOTE}: MeshDensity field order changed (field 4 is {names[3]!r}, "
        "was aperture_res_scale); grid_build.py's keyword call is still correct, but the "
        "documented positional trap moved")
    assert MeshDensity().aperture_res_scale == 1.0
    assert MeshDensity().max_triangles == 18_000


def test_build_mesh_with_info_signature():
    from hornlab_mesher.mesher import build_mesh_with_info

    params = inspect.signature(build_mesh_with_info).parameters
    for name in ("geometry", "density", "output_path", "scale_to_metres", "quality_gate"):
        assert name in params, f"{PIN_NOTE}: build_mesh_with_info lacks parameter {name!r}"
    assert params["scale_to_metres"].default is True
    assert params["quality_gate"].default == "report"


def test_freestanding_guard_still_refuses_a_missing_outer_shell():
    """The ValueError grid_build.py exists to satisfy (BARE mode never raises it)."""
    import numpy as np

    from hornlab_mesher.builders.point_grid_freestanding import _build_freestanding_point_grid
    from hornlab_mesher.geometry import PointGridBuildMode, PointGridHornGeometry

    inner = np.zeros((3, 3, 3), dtype=float)
    inner[..., 2] = np.arange(3, dtype=float)[None, :]
    inner[..., 0] = 10.0
    bare = PointGridHornGeometry(inner_points=inner, closed=False)
    assert bare.build_mode is PointGridBuildMode.BARE
    with pytest.raises(ValueError, match="requires outer_points"):
        _build_freestanding_point_grid(bare)
