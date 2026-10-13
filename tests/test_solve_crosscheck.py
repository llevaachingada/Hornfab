"""Test 17: the same mesh through two independent solvers (Julia BEAT on CUDA, bempp-cl on CPU).

Run:  .venv\\Scripts\\python.exe -m pytest tests/test_solve_crosscheck.py -v -m crosscheck

Disagreement is a FINDING, not something to tune away (05_TASK_SOLVE). The assertions here are
deliberately loose sanity bounds that catch a frame/ordering/units bug (tens of dB); the real
output is the printed per-frequency table, which goes to the senior agent as is.
"""
from __future__ import annotations

import numpy as np
import pytest

from conftest import requires_beat, requires_bempp, requires_mesher
from hornlab_search.solve import worker
from hornlab_search.solve.base import arc_angles_deg
from hornlab_search.solve.beat import BeatBackend
from hornlab_search.solve.bempp import BemppBackend
from test_solve_support import (build_seed_mesh, clean_host_state, emit, normalized_db,
                                release_and_verify, spec_with)

pytestmark = [requires_beat, requires_bempp, requires_mesher, pytest.mark.crosscheck, pytest.mark.slow]

FREQS = [500.0, 1000.0, 2000.0, 3000.0, 4000.0]


@pytest.fixture(scope="module")
def mesh(tmp_path_factory):
    return build_seed_mesh(tmp_path_factory.mktemp("xc"), "1", 4200.0)      # ~2.3k quarter dofs, resolves 4.2 kHz


@pytest.fixture(scope="module")
def beat_cuda():
    state = clean_host_state()
    assert state["hosts_left"] == []
    be = BeatBackend("cuda")
    ok, why = be.available()
    assert ok, why
    yield be
    end = release_and_verify()
    assert end["hosts_left"] == [], end


@requires_bempp
def test_bempp_formulation_follows_what_native_symmetry_supports():
    from hornlab_search.types import MeshResult
    import hornlab_bempp_bem as bempp
    be = BemppBackend()
    quarter = MeshResult("x.msh", 10, None, "1", "yz+xz", {}, (0,) * 6, 0.0)
    full = MeshResult("x.msh", 10, None, "1234", None, {}, (0,) * 6, 0.0)
    from hornlab_search.types import SolveSpec
    from test_solve_support import spec_with
    spec = spec_with([1000.0])
    cq, cf = be.make_config(quarter, spec), be.make_config(full, spec)
    assert cq.formulation == bempp.BIEFormulation.STANDARD and cq.native_symmetry_plane == "yz+xz"
    assert cf.formulation == bempp.BIEFormulation.BURTON_MILLER and cf.native_symmetry_plane is None
    assert cq.mesh_scale == cf.mesh_scale == 1.0 and cq.gmres_tol == spec.gmres_tol
    assert cq.observation.angle_min_deg == -90.0 and cq.observation.angle_max_deg == 90.0
    assert np.allclose(cq.frame_override.origin, 0) and np.allclose(cq.frame_override.axis, [0, 0, 1])
    bempp.reject_unsupported_native_symmetry(cq)             # the config bempp itself accepts
    with pytest.raises(ValueError):
        BemppBackend(formulation="nonsense")


def test_17_beat_cuda_vs_bempp_cpu_same_mesh(beat_cuda, mesh, capsys):
    be_bempp = BemppBackend()
    ok, why = be_bempp.available()
    assert ok, why
    spec = spec_with(FREQS, balloon=False)
    ob = beat_cuda.solve(mesh, spec)
    assert ob.ok, ob.message
    oc = be_bempp.solve(mesh, spec)
    assert oc.ok, oc.message
    b, c = ob.response, oc.response
    assert np.array_equal(b.h_angles_deg, c.h_angles_deg) == True and np.array_equal(c.h_angles_deg, arc_angles_deg(73))
    ax = b.axis_index
    nh = np.abs(normalized_db(b.spl_h_db, ax) - normalized_db(c.spl_h_db, ax))
    nv = np.abs(normalized_db(b.spl_v_db, ax) - normalized_db(c.spl_v_db, ax))
    ab = np.abs(b.spl_h_db - c.spl_h_db)
    on_axis_gap = b.spl_h_db[:, ax] - c.spl_h_db[:, ax]
    # complex agreement too (phase conventions are the same by construction)
    rel = np.abs(b.p_h - c.p_h).max(axis=1) / np.abs(b.p_h).max(axis=1)
    lines = ["test 17 beat_cuda (Burton-Miller, dense LU) vs bempp_cpu (formulation=%s, assembly=numba/opencl "
             "auto), same quarter mesh (n_dof beat=%d bempp=%d), 73-angle cuts:" % (c.meta["formulation"], b.n_dof, c.n_dof),
             "  f_hz   max|dH|_norm  max|dV|_norm  max|dH|_abs  on-axis(beat-bempp)  max rel|dp_h|   mean|dH|_norm",
             ] + [f"  {f:6.0f}  {h:11.4f}  {v:11.4f}  {a:11.4f}  {g:+17.4f}  {r:13.4e}  {m:12.4f}"
                  for f, h, v, a, g, r, m in zip(FREQS, nh.max(axis=1), nv.max(axis=1), ab.max(axis=1),
                                                  on_axis_gap, rel, nh.mean(axis=1))]
    lines.append(f"  beat solve {ob.seconds:.2f} s, bempp solve {oc.seconds:.2f} s")
    lines.append(f"  Re z_throat beat  : {np.round(b.z_throat.real, 4).tolist()}")
    lines.append(f"  Re z_throat bempp : {np.round(c.z_throat.real, 4).tolist()}")
    emit(capsys, "\n".join(lines))
    # loose bounds: a frame / sign / units bug is tens of dB; agreement itself is the table above.
    assert np.all(np.isfinite(nh)) and nh.max() < 3.0, nh.max(axis=1)
    assert np.all(np.isfinite(nv)) and nv.max() < 3.0, nv.max(axis=1)
