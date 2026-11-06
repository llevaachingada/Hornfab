"""A/B check: containers, mesh mirroring, convention conversions (offline, numpy only)."""
import numpy as np
import pytest

from hornlab_search.compare import fake, hornfab_side as hs
from hornlab_search.compare.model import AbData
from hornlab_search.compare.mshio import blab_symmetry, mirror_to_full, read_msh, write_msh
from hornlab_search.mesh import sizing, topology
from hornlab_search.solve import phasor


def _signed_volume(m):
    p0, p1, p2 = (m.xyz[m.tri[:, k]] for k in range(3))
    return float(np.einsum("ij,ij->i", p0, np.cross(p1, p2)).sum() / 6.0)


def test_msh_round_trip(tmp_path):
    m = fake.fake_sphere_quarter_mesh(2)
    write_msh(m, tmp_path / "q.msh")
    r = read_msh(tmp_path / "q.msh")
    assert r.tri.shape == m.tri.shape
    assert r.names == {1: "SD1G0", 2: "SD1D1001"}
    assert np.allclose(r.tag_areas()[2], m.tag_areas()[2])


def test_mirror_quarter_to_closed_full_mesh_with_outward_normals():
    q = fake.fake_sphere_quarter_mesh(2)
    full = mirror_to_full(q, "1")
    assert full.tri.shape[0] == 4 * q.tri.shape[0]
    assert full.tag_areas()[2] == pytest.approx(4 * q.tag_areas()[2])
    topology.check_surface(full.xyz, full.tri, None)           # closed, manifold, no unwelded seam
    assert _signed_volume(full) > 0                              # all four images keep outward winding


def test_mirror_half_mesh_and_noop():
    q = fake.fake_sphere_quarter_mesh(2)
    half = mirror_to_full(q, "14")                               # yz only: mirrors x, still open on y=0
    assert half.tri.shape[0] == 2 * q.tri.shape[0]
    assert mirror_to_full(q, "1234") is q


def test_mirror_refuses_mesh_outside_its_fundamental_domain():
    q = fake.fake_sphere_quarter_mesh(2)
    q.xyz[:, 0] -= 0.05
    with pytest.raises(ValueError, match="quadrant"):
        mirror_to_full(q, "1")


def test_blab_symmetry_pairs_with_the_single_solver_table():
    """Silent killer 2: Boundary Lab's flag and the solver flag come from sizing.SYMMETRY_PLANE together."""
    for quadrants, plane in sizing.SYMMETRY_PLANE.items():
        if plane == "xz":
            with pytest.raises(ValueError):
                blab_symmetry(quadrants)
        else:
            assert blab_symmetry(quadrants) == {"yz+xz": "xy", "yz": "x", None: "off"}[plane]
            assert (sizing.QUADRANT_FACTOR[quadrants] == 1) == (blab_symmetry(quadrants) == "off")


def test_acceleration_to_velocity_closed_form():
    """|p_vel| = 2 pi f |p_acc|; conjugated for exp(+i w t). Cross-checked against solve/phasor.py (independent code)."""
    f = np.array([100.0, 1000.0, 10000.0])
    p_bl = (1.0 + 2.0j) * np.ones((3, 4))
    ours = phasor.boundary_lab_to_ours(p_bl, f)
    back = hs.accel_to_canonical(ours, f)
    assert np.allclose(back, p_bl)
    assert np.allclose(hs.canonical_to_accel(p_bl, f), ours)
    spl = np.full((3, 4), 90.0)
    assert np.allclose(hs.spl_accel_to_velocity_db(spl, f)[:, 0] - 90.0, 20 * np.log10(2 * np.pi * f))


def test_reference_freqs_match_boundary_lab_log_grid():
    f = hs.reference_freqs(100, 20000, 12)
    assert f[0] == 100.0 and f[-1] == 20000.0
    assert len(f) == int(round(np.log2(200) * 12)) + 1
    bl = np.logspace(np.log10(100), np.log10(20000), len(f)).astype(np.float32)      # blab.live.build_log_frequencies
    assert np.allclose(f, bl, rtol=2e-6, atol=0.006)
    with pytest.raises(ValueError):
        hs.reference_freqs(500, 100)


def test_from_response_canonical_basis_and_round_trip(tmp_path):
    resp = fake.fake_response(fake.FAKE_FREQS[:20], angle_count=37, balloon_points=200)
    ab = hs.from_response(resp)
    f = ab.freqs_hz
    truth = fake.truth_p(f, fake.arc_dirs(ab.angles_deg, "H"))
    assert np.allclose(ab.p_h, truth, rtol=1e-9)
    assert np.allclose(ab.z_norm, fake.truth_z(f))
    ab.save(tmp_path / "x")
    back = AbData.load(tmp_path / "x")
    assert np.array_equal(back.p_h, ab.p_h) and back.meta["drive"] == ab.meta["drive"]
    assert back.balloon_kind == "theta_phi"


def test_abdata_validation_messages():
    with pytest.raises(ValueError, match="strictly ascending"):
        AbData("x", "t", np.array([2.0, 1.0]), np.array([0.0]))
    with pytest.raises(ValueError, match="spl_h_db"):
        AbData("x", "t", np.array([1.0, 2.0]), np.array([-1.0, 0.0, 1.0]), spl_h_db=np.zeros((2, 2)))
