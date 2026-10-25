"""Mesher-gated tests for mesh/grid_build.py: GRID grid -> real .msh (CPU, offline).

Same conventions as tests/test_mesh_build.py (``pytestmark = requires_mesher``): every test
drives the real hornlab_mesher; none touches the GPU, no solve is run.
"""
from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config
from hornlab_search.constants import C_AIR
from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import registry
from hornlab_search.mesh import build, grid_build, sizing, topology
from hornlab_search.types import MeshResult, MeshSpec, MeshTooLargeError

pytestmark = requires_mesher

R0_MM = 5.0
A0_DEG = 8.0
L_MM = 60.0
RM_MM = 25.0
N_PHI = 13
N_S = 32

BRIEF = {
    "driver": {"exit_radius_mm": R0_MM, "exit_angle_deg": A0_DEG},
    "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 300.0, "max_depth_mm": 220.0},
}
SPEC = {"name": "grid", "profile_h": {"type": "conical"}, "profile_v": "same",
        "n_phi": N_PHI, "n_s": N_S, "max_wall_deg": 80.0, "wall_thickness_mm": 3.0}
KNOBS = {"L_mm": L_MM, "h_rm_mm": RM_MM}

#: mouth_res 12 mm at epw 6 -> f_max = 1000 c / (6 * 12) Hz; throat = mouth / 2, rear = mouth.
EPW = 6.0
MOUTH_RES_MM = 12.0
F_MAX_HZ = 1000.0 * C_AIR / (EPW * MOUTH_RES_MM)


def big(cfg):
    """Caps lifted: these tests study meshing, not the VRAM budget."""
    return dataclasses.replace(cfg, mesh=dataclasses.replace(
        cfg.mesh, dof_cap_screen=10**6, dof_cap_verify=10**6, dof_cap_final=10**6))


@pytest.fixture(scope="module")
def cfg():
    return big(load_config(EXAMPLES / "osse_baseline.yaml"))


@pytest.fixture(scope="module")
def mesh_spec():
    return MeshSpec(epw=EPW, f_max_hz=F_MAX_HZ, quadrants="1", max_triangles=10**6)


@pytest.fixture(scope="module")
def grid_pair():
    return G.grid_points(SPEC, KNOBS, BRIEF)


def test_grid_mesh_builds_and_matches_the_repo_mesh_result_contract(cfg, mesh_spec, grid_pair,
                                                                   tmp_path):
    inner, meta = grid_pair
    # no outer_points in the dict: build_grid_mesh must synthesize the freestanding shell
    r = grid_build.build_grid_mesh(
        {"inner_points": inner, "meta": meta, "wall_thickness_mm": 3.0},
        mesh_spec, tmp_path / "mesh.msh", cfg)
    assert isinstance(r, MeshResult)
    assert Path(r.path).is_file() and Path(r.path).stat().st_size > 1000
    assert r.n_triangles > 0
    assert r.n_dof is None                       # only a solve reports dofs (contract)
    assert r.quadrants == "1"
    assert r.symmetry_plane == "yz+xz" == sizing.SYMMETRY_PLANE["1"]

    res = sizing.res_mm_for(EPW, F_MAX_HZ)
    assert r.res_mm == pytest.approx(res, rel=0, abs=1e-12)
    assert r.res_mm["throat"] == pytest.approx(r.res_mm["mouth"] / 2.0)
    assert set(r.res_mm) == {"throat", "mouth", "rear"}

    summary, xyz, tri = build.read_msh_summary(Path(r.path), return_arrays=True)
    assert summary["n_triangles"] == r.n_triangles
    assert tuple(summary["bbox_m"]) == tuple(r.bbox_m)
    ext = max(r.bbox_m[3] - r.bbox_m[0], r.bbox_m[4] - r.bbox_m[1], r.bbox_m[5] - r.bbox_m[2])
    assert build.BBOX_MIN_M <= ext <= build.BBOX_MAX_M
    assert summary["tags"].get(build.SOURCE_TAG, 0) > 0          # SD1D1001 present
    assert r.bbox_m[0] == 0.0 and r.bbox_m[1] == 0.0             # quarter sits in +x +y
    # the same topology/symmetry check build.py runs passed inside build_grid_mesh
    rep = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["1"])
    assert rep.bad_open_edges == 0 and rep.nonmanifold_edges == 0

    # dof accounting is the build.py chain: estimate_dofs OR vertex count vs the cap
    cap = sizing.dof_cap_for(mesh_spec, cfg.mesh)
    est = max(sizing.estimate_dofs(r.n_triangles, "1", cfg.mesh.dof_per_triangle),
              summary["n_nodes_used"])
    assert est <= cap
    print(f"\ntriangles={r.n_triangles} verts={summary['n_nodes_used']} dofs={est} cap={cap} "
          f"bbox={r.bbox_m} seconds={r.seconds:.3f}")


def test_density_and_geometry_use_keywords_not_positions(cfg, mesh_spec, grid_pair, tmp_path,
                                                        monkeypatch):
    """Regression for the MeshDensity positional trap (arg 4 is aperture_res_scale)."""
    import hornlab_mesher.mesher as mesher
    from hornlab_mesher.geometry import PointGridBuildMode

    captured = {}
    real = mesher.build_mesh_with_info

    def spy(geometry, density, **kwargs):
        captured["geometry"], captured["density"], captured["kwargs"] = geometry, density, kwargs
        return real(geometry, density, **kwargs)

    monkeypatch.setattr(mesher, "build_mesh_with_info", spy)
    inner, meta = grid_pair
    grid_build.build_grid_mesh({"inner_points": inner, "meta": meta},
                               mesh_spec, tmp_path / "mesh.msh", cfg)
    density = captured["density"]
    assert density.aperture_res_scale == 1.0
    assert density.throat_res_mm == pytest.approx(MOUTH_RES_MM / 2.0)
    assert density.mouth_res_mm == pytest.approx(MOUTH_RES_MM)
    assert density.rear_res_mm == pytest.approx(MOUTH_RES_MM)
    assert density.max_triangles == int(mesh_spec.max_triangles)
    assert density.allow_large_mesh is False
    geom = captured["geometry"]
    assert geom.build_mode is PointGridBuildMode.FREESTANDING
    assert geom.outer_points is not None and geom.closed is False
    assert geom.symmetry_planes == ("x", "y")
    assert geom.source_shape == 1
    assert geom.wall_thickness_mm == 3.0
    assert captured["kwargs"]["scale_to_metres"] is True


def test_tiny_cap_raises_mesh_too_large_and_leaves_no_mesh(cfg, mesh_spec, grid_pair, tmp_path):
    inner, meta = grid_pair
    tiny = dataclasses.replace(mesh_spec, max_triangles=10)
    out = tmp_path / "tiny" / "mesh.msh"
    with pytest.raises(MeshTooLargeError):
        grid_build.build_grid_mesh({"inner_points": inner, "meta": meta}, tiny, out, cfg)
    assert not out.exists()


def test_without_outer_points_the_mesher_lands_in_bare_and_fails_topology(grid_pair, tmp_path):
    """Measured on the pin (NOTES 2026-10-24): no outer_points -> BARE, builds, fails topology.

    The freestanding builder itself refuses a geometry without an outer shell -- that is the
    ValueError guard build_grid_mesh exists to satisfy.
    """
    from hornlab_mesher.builders.point_grid_freestanding import _build_freestanding_point_grid
    from hornlab_mesher.geometry import MeshDensity, PointGridBuildMode, PointGridHornGeometry
    from hornlab_mesher.mesher import build_mesh_with_info
    from hornlab_search.types import GeometryInvalidError

    inner, meta = grid_pair
    bare = PointGridHornGeometry(inner_points=inner, closed=False, wall_thickness_mm=3.0,
                                 source_shape=1,
                                 source_auto_angle_deg=meta["source_auto_angle_deg"],
                                 symmetry_planes=("x", "y"))
    assert bare.build_mode is PointGridBuildMode.BARE
    with pytest.raises(ValueError, match="requires outer_points"):
        _build_freestanding_point_grid(bare)

    density = MeshDensity(throat_res_mm=MOUTH_RES_MM / 2.0, mouth_res_mm=MOUTH_RES_MM,
                          rear_res_mm=MOUTH_RES_MM, aperture_res_scale=1.0,
                          max_triangles=20000, allow_large_mesh=False)
    path, _info = build_mesh_with_info(bare, density, output_path=tmp_path / "bare.msh",
                                       scale_to_metres=True)
    _summary, xyz, tri = build.read_msh_summary(Path(path), return_arrays=True)
    with pytest.raises(GeometryInvalidError, match="not closed/manifold"):
        topology.check_surface(xyz, tri, "yz+xz")


def test_quarter_and_full_grid_are_the_same_surface_mirrored_4x():
    """Geometry basis for the later full-vs-quarter GPU consistency check."""
    quarter, mq = G.grid_points(SPEC, KNOBS, BRIEF)
    full, mf = G.grid_points(SPEC, KNOBS, BRIEF, full_circle=True)
    n = N_PHI
    assert full.shape == (4 * (n - 1), N_S + 1, 3)
    assert mq["quarter"] is True and mf["quarter"] is False
    assert mf["n_phi"] == 4 * (n - 1) and mf["n_phi_quarter"] == n

    mirror_x = quarter * np.array([-1.0, 1.0, 1.0])
    mirror_xy = quarter * np.array([-1.0, -1.0, 1.0])
    mirror_y = quarter * np.array([1.0, -1.0, 1.0])
    blocks = [full[:n], full[n:2 * n - 1], full[2 * n - 1:3 * n - 2],
              full[3 * n - 2:4 * n - 4]]
    expected = [quarter, mirror_x[::-1][1:], mirror_xy[1:], mirror_y[::-1][1:-1]]
    deltas = [float(np.max(np.abs(a - b))) for a, b in zip(blocks, expected)]
    print(f"\nshared quadrant max|d|={deltas[0]:.3e} mm; quadrant blocks max|d|={deltas}")
    for a, b in zip(blocks, expected):
        assert np.allclose(a, b, rtol=0.0, atol=1e-9)
    # every full row is the quarter row reflected: |x|,|y|,z all match the quarter row set
    assert np.array_equal(full[:n], quarter)


def test_grid_generator_error_is_not_wrapped_as_geometry_invalid(cfg, mesh_spec, tmp_path):
    """A self-approaching grid travels the generator error path, not a mesher wrap."""
    theta = np.linspace(0.0, 1.5 * math.pi, N_S + 1)
    rho = 10.0 + 3.0 * np.cos(theta)
    z = 3.0 * np.sin(theta)
    phi = np.linspace(0.0, 0.5 * math.pi, N_PHI)
    curled = np.stack([np.stack([rho * np.cos(p), rho * np.sin(p), z], axis=-1) for p in phi])
    with pytest.raises(registry.GeneratorError, match="self-approach"):
        grid_build.build_grid_mesh({"inner_points": curled, "wall_thickness_mm": 3.0,
                                    "meta": {"quarter": True,
                                             "source_auto_angle_deg": A0_DEG}},
                                   mesh_spec, tmp_path / "mesh.msh", cfg)
