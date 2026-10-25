"""Tests 8-11 of 08_TASK_PIPELINE (offline parts of the self-test) plus fake-backend runs of
run_analytic/run_crosscheck so the verdict logic is exercised without a solver.

Also pins the CLI's lock-ownership rule (2026-10-25 fix-16): a selftest REFUSED by the GPU lock
must not call worker.shutdown(), because it never acquired the lock and owns no workers; the
success path keeps the verified shutdown at the end of the measurement (AGENTS.md rule 6)."""
from __future__ import annotations

import contextlib
from collections import Counter
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search import cli
from hornlab_search.constants import C_AIR, RHO_AIR
from hornlab_search.mesh.build import read_msh_summary
from hornlab_search.search import gpulock
from hornlab_search.search.selftest import (KA_VALUES, analytic_magnitude, format_analytic,
                                            icosphere, run_analytic, write_sphere_msh)
from hornlab_search.solve import worker
from hornlab_search.solve.base import arc_angles_deg
from hornlab_search.types import Response, SolveOutcome


# 8
@pytest.mark.parametrize("n", [0, 1, 2, 3, 4])
def test_icosphere_counts_watertight_volume(n):
    p, t = icosphere(0.1, n)
    assert t.shape == (20 * 4 ** n, 3)
    assert p.shape[0] == 10 * 4 ** n + 2                     # Euler: V = F/2 + 2
    edges = Counter()
    for a, b, c in t:
        for u, v in ((a, b), (b, c), (c, a)):
            edges[(min(u, v), max(u, v))] += 1
    assert set(edges.values()) == {2}, "mesh is not watertight"
    # directed edges must also be consistent: each directed edge appears exactly once
    directed = Counter((u, v) for a, b, c in t for u, v in ((a, b), (b, c), (c, a)))
    assert set(directed.values()) == {1}
    vol = np.einsum("ij,ij->i", p[t[:, 0]], np.cross(p[t[:, 1]], p[t[:, 2]])).sum() / 6.0
    assert vol > 0
    if n == 4:
        assert abs(vol / (4.0 / 3.0 * np.pi * 0.1 ** 3) - 1.0) < 0.02


# 9
@pytest.mark.parametrize("n", [0, 2, 4])
def test_every_vertex_is_on_the_sphere(n):
    p, _ = icosphere(0.1, n)
    assert np.abs(np.linalg.norm(p, axis=1) - 0.1).max() < 1e-12


def test_icosphere_rejects_bad_subdivision():
    with pytest.raises(ValueError):
        icosphere(0.1, -1)


# 10
def test_write_sphere_msh_round_trips_through_the_reader(tmp_path):
    p, t = icosphere(0.1, 3)
    path = tmp_path / "s.msh"
    write_sphere_msh(p, t, path)
    s = read_msh_summary(path)
    assert s["n_triangles"] == 1280 and s["n_nodes"] == 642
    assert s["tags"] == {2: 1280} and s["tag_names"][2] == "SD1D1001"
    assert np.allclose(s["bbox_m"], (-0.1, -0.1, -0.1, 0.1, 0.1, 0.1), atol=5e-3)
    assert abs(s["area_m2"] / (4 * np.pi * 0.1 ** 2) - 1.0) < 0.02
    text = path.read_text()
    assert "2.2 0 8" in text and text.count("\n") > 1280


# 11
def test_analytic_magnitude_limits_and_monotone():
    a, r = 0.1, 2.0
    hi = analytic_magnitude(a, r, 100.0)
    assert abs(hi / (RHO_AIR * C_AIR * a / r) - 1) < 0.01
    lo = analytic_magnitude(a, r, 0.01)
    assert abs(lo / (RHO_AIR * C_AIR * 0.01 * a / r) - 1) < 0.01
    ka = np.geomspace(0.01, 100, 200)
    assert np.all(np.diff(analytic_magnitude(a, r, ka)) > 0)


# ---- verdict logic with a fake backend that IS a perfect pulsating sphere

class SphereBackend:
    """Returns the exact pulsating-sphere field for whatever sphere mesh it is given."""
    def __init__(self, name="beat_cuda", omni_error_db=0.0, scale=0.37, level_error=None,
                 accel=True):
        self.name = name
        self.accel = accel
        self.omni_error_db = omni_error_db
        self.scale = scale
        self.level_error = level_error or {}

    def available(self):
        return True, "fake"

    def warm(self):
        pass

    def release(self):
        pass

    def solve(self, mesh, spec):
        f = np.asarray(spec.freqs_hz)
        ka = 2 * np.pi * f * 0.1 / C_AIR
        ang = arc_angles_deg(spec.observation.angle_count)
        mag = self.scale * analytic_magnitude(0.1, spec.observation.distance_m, ka)
        if self.accel:
            mag = mag / (2 * np.pi * f)               # unit ACCELERATION drive (TOOLCHAIN C5)
        err = self.level_error.get(mesh.n_dof, np.zeros(f.size))
        db = 20 * np.log10(mag / 2e-5) + err
        h = np.tile(db[:, None], (1, ang.size))
        h = h + self.omni_error_db * np.cos(np.radians(ang))[None, :]
        nb = spec.observation.balloon_points
        bal = None
        if nb:
            rng = np.random.default_rng(1)
            bal = db[:, None] + self.omni_error_db * rng.standard_normal((f.size, nb))
        r = Response(freqs_hz=f, h_angles_deg=ang, v_angles_deg=ang, spl_h_db=h, spl_v_db=h.copy(),
                     balloon_dirs=None if bal is None else np.tile([0, 0, 1.0], (nb, 1)),
                     spl_balloon_db=bal, z_throat=None, backend=self.name, n_dof=mesh.n_dof)
        return SolveOutcome(True, r, 0.01, None, "")


def test_run_analytic_passes_a_perfect_sphere(cfg, tmp_path):
    # level error shrinks with refinement: 642 dofs (sub3) > 2562 (sub4) > 10242 (sub5)
    errs = {642: np.array([0, 0, 0, 0.3, 0.9]), 2562: np.array([0, 0, 0, 0.1, 0.3]),
            10242: np.array([0, 0, 0, 0.02, 0.05])}
    res = run_analytic(cfg, tol_db=0.5, subdivisions=3, convergence_levels=(3, 4, 5),
                       backend_factory=lambda n: SphereBackend(n, level_error=errs), workdir=tmp_path)
    # sub3 spread 0.9 dB > 0.5: the verdict must say FAIL on the shape check, not hide it
    assert res["checks"]["R(ka) spread"]["passed"] is False and res["passed"] is False
    assert res["convergence"]["monotone_decreasing"] is True
    assert np.allclose(res["freqs_hz"], [273, 546, 1092, 2183, 4367], atol=1.0)
    assert np.allclose(res["ka"], KA_VALUES)
    assert max(abs(e) for e in res["spreading_err_db"]) < 1e-9
    assert "FAIL" in format_analytic(res)

    res = run_analytic(cfg, tol_db=0.5, subdivisions=3, convergence_levels=(3, 4, 5),
                       backend_factory=lambda n: SphereBackend(n), workdir=tmp_path)
    assert res["passed"] is True
    assert res["r_spread_db"] < 1e-9
    assert res["checks"]["convergence"]["passed"] is False        # equal errors are not "decreasing"
    assert res["passed_with_convergence"] is False
    assert all(abs(r["r_dev_db"]) < 1e-9 for r in res["rows"])
    assert "RESULT: PASS" in format_analytic(res)


def test_run_analytic_flags_a_non_omnidirectional_port_model(cfg, tmp_path):
    res = run_analytic(cfg, tol_db=0.5, subdivisions=3, convergence_levels=(),
                       backend_factory=lambda n: SphereBackend(n, omni_error_db=3.0), workdir=tmp_path)
    assert res["checks"]["omnidirectionality"]["passed"] is False
    assert res["checks"]["spreading 2m->4m"]["passed"] is True
    assert "port model" in res["diagnosis"]
    assert res["passed"] is False


def test_run_analytic_reports_a_wrong_spreading(cfg, tmp_path):
    class Bad(SphereBackend):
        def solve(self, mesh, spec):
            out = super().solve(mesh, spec)
            if spec.observation.distance_m > 3:
                out.response.spl_h_db = out.response.spl_h_db + 3.0       # 4 m only 3 dB quieter
            return out
    res = run_analytic(cfg, subdivisions=3, convergence_levels=(), backend_factory=lambda n: Bad(n),
                       workdir=tmp_path)
    assert res["checks"]["spreading 2m->4m"]["passed"] is False and res["passed"] is False


def test_a_velocity_driven_backend_needs_drive_velocity_and_the_raw_spread_is_always_reported(cfg, tmp_path):
    be = lambda n: SphereBackend(n, accel=False)                     # noqa: E731
    res = run_analytic(cfg, subdivisions=3, convergence_levels=(), drive="velocity",
                       backend_factory=be, workdir=tmp_path)
    assert res["passed"] is True and res["r_spread_raw_db"] < 1e-9
    wrong = run_analytic(cfg, subdivisions=3, convergence_levels=(), drive="acceleration",
                         backend_factory=be, workdir=tmp_path)
    assert wrong["passed"] is False and wrong["r_spread_db"] > 20.0   # the convention matters
    res = run_analytic(cfg, subdivisions=3, convergence_levels=(), backend_factory=lambda n: SphereBackend(n),
                       workdir=tmp_path)
    assert res["r_spread_raw_db"] > 20.0 and res["passed"] is True     # literal test fails, corrected passes
    assert max(abs(r["abs_vs_unit_accel_db"] - res["rows"][0]["abs_vs_unit_accel_db"])
               for r in res["rows"]) < 1e-9


# ------------------------------------------------------------------ CLI lock ownership (fix-16)

def _selftest_args(tmp_path) -> SimpleNamespace:
    """The argparse namespace _cmd_selftest reads (analytics, no GPU; body is stubbed/faked)."""
    return SimpleNamespace(config=None, backend=None, runs_dir=str(tmp_path),
                           cache_dir=str(tmp_path / "cache"), dataset_dir=str(tmp_path / "dataset"),
                           analytic=True, no_convergence=True, convergence="3", tol_db=0.5,
                           subdivisions=3, n_freqs=5)


def test_lock_refused_selftest_does_not_shut_down_workers(monkeypatch, tmp_path, capsys):
    """fix-16: a GpuBusyError refusal must NOT reach worker.shutdown() -- this process never
    acquired the lock and started no worker, so a shutdown would force-kill the live job's host."""
    calls = []
    monkeypatch.setattr(worker, "install_handlers", lambda *a, **k: None)
    monkeypatch.setattr(worker, "shutdown", lambda *a, **k: calls.append((a, k)))

    @contextlib.contextmanager
    def busy_lock(command, runs_root=None):
        raise gpulock.GpuBusyError('GPU busy: tester running "other job" (pid 4242) since now')
        yield                                                   # pragma: no cover

    monkeypatch.setattr(gpulock, "gpu_lock", busy_lock)
    assert cli._cmd_selftest(_selftest_args(tmp_path)) == 3
    assert calls == [], "a lock-refused selftest must not shut down (and kill) another job's workers"
    assert "GPU busy" in capsys.readouterr().err


def test_successful_selftest_still_verifies_shutdown(monkeypatch, tmp_path):
    """The happy path keeps rule 6 exactly as today: one verified worker shutdown at the end."""
    calls = []
    monkeypatch.setattr(worker, "install_handlers", lambda *a, **k: None)
    monkeypatch.setattr(worker, "shutdown", lambda *a, **k: calls.append(k))
    monkeypatch.setattr(cli, "_selftest_body", lambda args, cfg, st: 0)

    @contextlib.contextmanager
    def held_lock(command, runs_root=None):
        yield

    monkeypatch.setattr(gpulock, "gpu_lock", held_lock)
    assert cli._cmd_selftest(_selftest_args(tmp_path)) == 0
    assert calls == [{"verify": True}]
