"""Boundary traces: ordering recovery and the exact-field round trip (test 19).

``test_dof_permutations_*`` need the mesher and bempp (CPU only, no GPU). ``test_19`` is the
gate on the phase-2 learned-backend direction: if the exact boundary integral cannot reproduce
the solver's own far field from its own traces, no learned boundary map can become a polar.

Run:  .venv\\Scripts\\python.exe -m pytest tests/test_solve_traces.py -v -m slow
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import requires_beat, requires_bempp, requires_mesher
from hornlab_search.config import freq_grid
from hornlab_search.solve import traces as tr
from hornlab_search.solve.base import arc_angles_deg
from hornlab_search.solve.beat import BeatBackend
from test_solve_support import (build_seed_mesh, clean_host_state, emit, release_and_verify, spec_with)


@pytest.fixture(scope="module")
def quarter6(tmp_path_factory):
    return build_seed_mesh(tmp_path_factory.mktemp("tq"), "1", 4200.0)


# ------------------------------------------------------------------ no GPU


@requires_mesher
def test_read_msh_geometry_matches_the_beat_reader(quarter6):
    nodes, faces = tr.read_msh_geometry(quarter6.path)
    assert nodes.shape[1] == 3 and faces.shape[1] == 3
    assert faces.shape[0] == quarter6.n_triangles
    assert faces.min() >= 0 and faces.max() < nodes.shape[0]
    try:
        import hornlab_beat_bem as beat
    except ImportError:
        return
    info = beat.read_gmsh22_info(quarter6.path)
    assert info.n_vertices == nodes.shape[0] and info.n_triangles == faces.shape[0]


@requires_bempp
@requires_mesher
def test_dof_permutations_are_one_to_one_on_a_real_mesh(quarter6, capsys):
    import hornlab_bempp_bem as bempp
    nodes, faces = tr.read_msh_geometry(quarter6.path)
    cen = nodes[faces].mean(axis=1)
    traces = {"points": nodes, "face_centroids": cen, "symmetry_plane": quarter6.symmetry_plane}
    loaded = bempp.load_mesh(quarter6.path, scale=1.0, native_symmetry_plane=quarter6.symmetry_plane)
    pp, pq = tr.dof_permutations(loaded, traces)
    assert np.array_equal(np.sort(pp), np.arange(nodes.shape[0]))
    assert np.array_equal(np.sort(pq), np.arange(faces.shape[0]))
    ident_p = bool(np.array_equal(pp, np.arange(pp.size)))
    ident_q = bool(np.array_equal(pq, np.arange(pq.size)))
    emit(capsys, f"dof ordering: n_p1={pp.size} (file nodes {nodes.shape[0]}), n_dp0={pq.size} "
                 f"(file triangles {faces.shape[0]}); bempp P1 order == file node order: {ident_p}; "
                 f"bempp DP0 order == file triangle order: {ident_q}")


def test_ordering_mismatch_is_refused_not_guessed():
    a = np.random.default_rng(1).normal(size=(10, 3))
    with pytest.raises(tr.TraceOrderingError, match="not one-to-one"):
        tr._match_points(a, np.vstack([a[:5], a[:5]]), "x", 1e-9)
    with pytest.raises(tr.TraceOrderingError, match="mismatch"):
        tr._match_points(a, a + 1e-3, "x", 1e-9)
    with pytest.raises(tr.TraceOrderingError, match="dofs"):
        tr._match_points(a, a[:9], "x", 1e-9)
    perm = np.random.default_rng(2).permutation(10)
    assert np.array_equal(tr._match_points(a, a[perm], "x", 1e-9), perm)


def test_cut_points_follow_the_solver_convention():
    a = arc_angles_deg(5)
    h = tr.cut_points(a, 2.0, "horizontal")
    v = tr.cut_points(a, 2.0, "vertical")
    assert np.allclose(h[2], [0, 0, 2.0]) and np.allclose(h[4], [2.0, 0, 0], atol=1e-12)
    assert np.allclose(v[4], [0, 2.0, 0], atol=1e-12) and np.allclose(h[0], [-2.0, 0, 0], atol=1e-12)
    with pytest.raises(ValueError):
        tr.cut_points(a, 2.0, "diagonal")


# ------------------------------------------------------------------ 19 (GPU)


@requires_beat
@requires_bempp
@requires_mesher
@pytest.mark.slow
@pytest.mark.gpu
def test_19_traces_reproduce_the_solvers_own_far_field(quarter6, tmp_path, capsys):
    state = clean_host_state()
    assert state["hosts_left"] == []
    try:
        be = BeatBackend("cuda")
        spec = spec_with(freq_grid(500, 4000, 12), balloon=False)
        out, raw = be.solve_traced(quarter6, spec)
        assert out.ok, out.message
        r = out.response
        traces = tr.package_traces(quarter6, spec, raw)
    finally:
        end = release_and_verify()
    assert end["hosts_left"] == [], end

    nf = len(spec.freqs_hz)
    assert traces["pressure"].shape == (nf, r.n_dof)               # the solver's vertex count IS n_dof
    assert traces["neumann"].shape == (nf, quarter6.n_triangles)
    assert traces["pressure"].dtype == traces["neumann"].dtype == np.complex128
    path = tmp_path / "traces_one_design.npz"
    np.savez(path, **{k: v for k, v in traces.items() if isinstance(v, np.ndarray)})
    size = path.stat().st_size

    idx = [0, 5, 11]
    freqs = np.asarray(spec.freqs_hz)[idx]
    d = {}
    for plane, key, pkey in (("horizontal", "spl_h_db", "p_h"), ("vertical", "spl_v_db", "p_v")):
        pts = tr.cut_points(r.h_angles_deg, spec.observation.distance_m, plane)
        p = tr.field_from_traces(traces, pts, freqs)
        spl = 20 * np.log10(np.abs(p) / 20e-6)
        d[plane] = (np.abs(spl - getattr(r, key)[idx]).max(axis=1),
                    np.abs(p - getattr(r, pkey)[idx]).max(axis=1) / np.abs(getattr(r, pkey)[idx]).max(axis=1))
    lines = ["test 19 trace round trip (quarter mesh, n_dof=%d, n_faces=%d):" % (r.n_dof, quarter6.n_triangles),
             f"  traces: pressure {traces['pressure'].shape} {traces['pressure'].dtype}, "
             f"neumann {traces['neumann'].shape} {traces['neumann'].dtype}, points {traces['points'].shape} "
             f"{traces['points'].dtype}, face_centroids {traces['face_centroids'].shape}",
             f"  ordering: {traces['ordering']}",
             f"  disk size, one design, {nf} frequencies, uncompressed npz: {size} bytes ({size / 1e6:.3f} MB); "
             f"per frequency {size / nf:.0f} bytes",
             "  f_hz    max|dSPL_H| dB   max|dSPL_V| dB   max rel|dp_H|   max rel|dp_V|"]
    for i, f in enumerate(freqs):
        lines.append(f"  {f:7.1f}  {d['horizontal'][0][i]:14.5f}  {d['vertical'][0][i]:14.5f}  "
                     f"{d['horizontal'][1][i]:12.3e}  {d['vertical'][1][i]:12.3e}")
    worst = max(d["horizontal"][0].max(), d["vertical"][0].max())
    lines.append(f"  MAX difference, recovered vs solver far field: {worst:.5f} dB")
    emit(capsys, "\n".join(lines))
    assert worst < 0.1, f"exact recovery from traces differs from the solver's far field by {worst} dB"
