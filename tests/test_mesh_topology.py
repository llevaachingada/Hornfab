"""mesh/topology.py: pre-solve surface checks (idea after Boundary Lab 0.5.0). Synthetic cases pin
each failure class; the mesher-gated test proves real meshes of every family pass."""
import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.mesh import topology
from hornlab_search.mesh.build import SymmetryMismatchError
from hornlab_search.types import GeometryInvalidError

# closed tetrahedron (every edge shared by exactly two faces)
P = np.array([[0.1, 0.1, 0.0], [0.3, 0.1, 0.0], [0.1, 0.3, 0.0], [0.1, 0.1, 0.2]])
T = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]])


def test_closed_surface_passes_full_domain():
    rep = topology.check_surface(P, T, None)
    assert rep.open_edges == 0 and rep.nonmanifold_edges == 0 and rep.near_coincident == 0


def test_open_surface_off_planes_is_invalid_geometry():
    with pytest.raises(GeometryInvalidError, match="open edge"):
        topology.check_surface(P, T[:3], None)


def test_open_edges_on_active_symmetry_plane_are_allowed():
    # O=(0,0,0) A=(.2,0,0) on y=0 & z=0, B=(0,.2,0) on x=0 & z=0, C=(0,0,.2) on x=0 & y=0
    pts = np.array([[0.0, 0.0, 0.0], [0.2, 0.0, 0.0], [0.0, 0.2, 0.0], [0.0, 0.0, 0.2]])
    # one face ABC: free edges A-C (y=0, on plane), B-C (x=0, on plane), A-B (only z=0: off)
    rep = topology.analyze(pts, np.array([[1, 2, 3]]), "yz+xz")
    assert (rep.open_edges, rep.open_edges_on_planes, rep.bad_open_edges) == (3, 2, 1)
    with pytest.raises(GeometryInvalidError, match="1 open edge"):
        topology.check_surface(pts, np.array([[1, 2, 3]]), "yz+xz")
    # faces OAC (in y=0) and OCB (in x=0): every free edge lies on a symmetry plane
    rep = topology.check_surface(pts, np.array([[0, 1, 3], [0, 3, 2]]), "yz+xz")
    assert rep.open_edges == 4 and rep.bad_open_edges == 0
    # the same surface with symmetry OFF is open
    with pytest.raises(GeometryInvalidError):
        topology.check_surface(pts, np.array([[0, 1, 3], [0, 3, 2]]), None)


def test_nonmanifold_edge_is_invalid_geometry():
    pts = np.vstack([P, [[0.2, 0.0, -0.1]]])
    tri = np.vstack([T, [[0, 1, 4]]])                       # edge 0-1 now has three faces
    with pytest.raises(GeometryInvalidError, match="non-manifold"):
        topology.check_surface(pts, tri, None)


def test_near_coincident_vertices_are_invalid_geometry():
    pts = np.vstack([P, P[1] + 1e-12])                     # an unwelded copy of vertex 1
    tri = T.copy()
    tri[1] = [0, 4, 3]                                      # one face uses the copy
    with pytest.raises(GeometryInvalidError, match="near-coincident"):
        topology.check_surface(pts, tri, None)


def test_reduced_mesh_outside_its_domain_stops_the_run():
    bad = P - np.array([0.2, 0.0, 0.0])                     # reaches x = -0.1
    with pytest.raises(SymmetryMismatchError, match="fundamental domain"):
        topology.check_surface(bad, T, "yz+xz")
    topology.check_fundamental_domain(bad, "xz")            # y stays >= 0: fine for xz only
    with pytest.raises(ValueError):
        topology.symmetry_planes("ab")


def test_symmetry_planes_cover_every_quadrant_mapping():
    from hornlab_search.mesh import sizing
    for q, plane in sizing.SYMMETRY_PLANE.items():
        assert len(topology.symmetry_planes(plane)) == {"1234": 0, "12": 1, "14": 1, "1": 2}[q]


@requires_mesher
@pytest.mark.timeout(1200)
@pytest.mark.parametrize("name", ["osse_baseline", "icw_termination", "throat_adapter",
                                  "freeform_sculpt", "freeform_hv"])
def test_real_meshes_of_every_family_pass(tmp_path, name):
    from hornlab_search.config import load_config, mesh_spec
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.mesh.build import build_mesh, read_msh_summary
    from hornlab_search.mesh import sizing
    cfg = load_config(EXAMPLES / f"{name}.yaml")
    space = DesignSpace.from_config(cfg)
    m = build_mesh(space.seed, mesh_spec("screen", cfg), cfg, tmp_path, mode="screen")
    _, xyz, tri = read_msh_summary(m.path, return_arrays=True)
    rep = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE[cfg.mesh.quadrants])
    assert rep.bad_open_edges == 0 and rep.min_vertex_spacing_m > 1e3 * rep.tolerance_m
    # a cache hit re-runs the checks on the stored file and still passes
    build_mesh(space.seed, mesh_spec("screen", cfg), cfg, tmp_path, mode="screen")
