"""Real-solver tests for the beat adapter (05 tests 11-16 and 18). GPU, one process, one warm host.

Run:  .venv\\Scripts\\python.exe -m pytest tests/test_solve_beat.py -v -m slow

Order matters: test 14 runs FIRST so it sees a genuinely cold host. The module fixture kills
every BEAT host before the first solve (recording the VRAM baseline) and, at the end, releases
the host through ``worker.shutdown`` and asserts the process list is empty (AGENTS.md hygiene
rule 6). Measured numbers are printed live with ``[measured]`` so they survive ``-v`` capture.
"""
from __future__ import annotations

import dataclasses
import time

import numpy as np
import pytest

from conftest import requires_beat, requires_mesher
from hornlab_search.mesh.sizing import estimate_dofs
from hornlab_search.solve import worker
from hornlab_search.solve.base import Backend, arc_angles_deg
from hornlab_search.solve.beat import BeatBackend
from hornlab_search.types import Response
from test_solve_support import (build_seed_mesh, clean_host_state, emit, normalized_db,
                                release_and_verify, seed_cfg, spec_with)

pytestmark = [requires_beat, requires_mesher, pytest.mark.slow, pytest.mark.gpu]

# The seed horn is large (bbox 0.80 x 0.64 x 0.27 m), so f_max is chosen per mesh to hit a target dof count
# (measured with the real mesher): quarter 4200 Hz -> 2,316 dofs; quarter 3200 Hz -> 1,388;
# full 3100 Hz -> 4,941; full 2000 Hz -> 2,356. epw = 6, so each mesh resolves up to its f_max.
F_QA, F_QB, F_FA, F_FC = 4200.0, 3200.0, 3100.0, 2000.0


@pytest.fixture(scope="module")
def solver(tmp_path_factory):
    state = clean_host_state()
    assert state["hosts_left"] == [], f"BEAT hosts survived the pre-test clear: {state}"
    be = BeatBackend("cuda")
    ok, why = be.available()
    assert ok, why
    be.baseline = state                         # recorded for the report
    yield be
    end = release_and_verify()
    assert end["hosts_left"] == [], f"a BEAT host survived release: {end}"


@pytest.fixture(scope="module")
def quarter_a(tmp_path_factory):
    return build_seed_mesh(tmp_path_factory.mktemp("qa"), "1", F_QA)            # ~2.3k dofs


@pytest.fixture(scope="module")
def quarter_b(tmp_path_factory):
    return build_seed_mesh(tmp_path_factory.mktemp("qb"), "1", F_QB)            # ~1.4k dofs


@pytest.fixture(scope="module")
def full_a(tmp_path_factory):
    return build_seed_mesh(tmp_path_factory.mktemp("fa"), "1234", F_FA)         # ~4.9k dofs


@pytest.fixture(scope="module")
def full_coarse(tmp_path_factory):
    return build_seed_mesh(tmp_path_factory.mktemp("fc"), "1234", F_FC, mode="screen")   # ~2.4k dofs


# 14 -- runs first on purpose
def test_14_warm_worker_cold_then_warm_then_post_detach(solver, quarter_a, capsys, caplog):
    import logging
    caplog.set_level(logging.INFO, logger="hornlab_search.solve.worker")
    worker.mark_cold()
    spec = spec_with([1000.0])
    emit(capsys, f"baseline: {solver.baseline}")
    t = []
    for label in ("cold", "warm"):
        out = solver.solve(quarter_a, spec)
        assert out.ok, out.message
        t.append(out.seconds)
    worker.detach()
    out = solver.solve(quarter_a, spec)
    assert out.ok, out.message
    t.append(out.seconds)
    emit(capsys, f"test 14: cold={t[0]:.2f} s  warm={t[1]:.2f} s  post-detach={t[2]:.2f} s  "
                 f"(cold/warm = {t[0] / t[1]:.1f}x, cold/post-detach = {t[0] / t[2]:.1f}x)  "
                 f"peak_vram_delta_mib={out.peak_vram_mb}")
    emit(capsys, "worker log lines: " + " | ".join(r.getMessage() for r in caplog.records
                                                    if "solve" in r.getMessage()))
    assert any("second solve" in r.getMessage() for r in caplog.records)
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING], "worker reuse warning fired"
    assert t[1] * 3.0 <= t[0], f"second solve not 3x faster: {t}"
    assert t[2] * 3.0 <= t[0], f"post-detach solve not 3x faster: {t}"


def test_14b_worker_warm_then_solve_and_verified_release(solver, quarter_a, capsys):
    """The path a search takes: release -> worker.warm(backend) -> solves. And the release path
    itself is verified against the real process table."""
    rel = release_and_verify()
    assert rel["hosts_left"] == []
    emit(capsys, f"release: {rel}")
    worker.mark_cold()
    t0 = time.perf_counter()
    worker.warm(solver)
    t_warm = time.perf_counter() - t0
    worker.warm(solver)                                           # idempotent: instant
    t_again = time.perf_counter() - t0 - t_warm
    spec = spec_with([1000.0])
    times = []
    for _ in range(2):
        out = solver.solve(quarter_a, spec)
        assert out.ok, out.message
        times.append(out.seconds)
    emit(capsys, f"test 14b: worker.warm()={t_warm:.2f} s (repeat call {t_again * 1000:.1f} ms)  "
                 f"first solve after warm={times[0]:.2f} s  second={times[1]:.2f} s")
    assert t_again < 0.5


# 11
def test_11_three_frequencies_valid_response(solver, quarter_a, capsys):
    spec = spec_with([1000.0, 2000.0, 4000.0])
    out = solver.solve(quarter_a, spec)
    assert out.ok, out.message
    r = out.response
    assert isinstance(r, Response) and r.backend == "beat_cuda"
    assert r.spl_h_db.shape == r.spl_v_db.shape == (3, 73)
    assert np.array_equal(r.h_angles_deg, arc_angles_deg(73)) and r.axis_index == 36
    assert np.all(np.isfinite(r.spl_h_db)) and np.all(np.isfinite(r.spl_v_db))
    assert r.n_dof is not None and r.n_dof > 0
    assert r.balloon_dirs.shape == (512, 3) and r.spl_balloon_db.shape == (3, 512)
    assert r.meta["balloon_grid"] == [16, 32]
    assert r.p_h.dtype == np.complex128 and r.z_throat.shape == (3,)
    assert out.peak_vram_mb is not None
    emit(capsys, f"test 11: n_dof={r.n_dof} n_triangles={quarter_a.n_triangles} "
                 f"spl_h range=[{r.spl_h_db.min():.2f}, {r.spl_h_db.max():.2f}] dB  "
                 f"Re(z_throat)={np.round(r.z_throat.real, 3).tolist()} "
                 f"Im(z_throat)={np.round(r.z_throat.imag, 3).tolist()}  "
                 f"solve={out.seconds:.2f} s  vram_baseline={r.meta['vram_baseline_mib']} "
                 f"peak_delta={out.peak_vram_mb}")
    emit(capsys, f"meta.native_diagnostics[0]={r.meta['native_diagnostics'][0]}")
    emit(capsys, f"meta.timings={r.meta['timings']}")
    emit(capsys, "SolveConfig repr (copy-pasteable):\n" + repr(solver.make_config(
        quarter_a, spec)))


# 12
def test_12_mirror_symmetry_of_the_cuts_is_the_noise_floor(solver, quarter_a, full_a, capsys):
    freqs = [500.0, 1000.0, 2000.0, 3000.0]
    results = {}
    for label, mesh in (("quarter(2.3k dof)", quarter_a), ("full(4.9k dof)", full_a)):
        out = solver.solve(mesh, spec_with(freqs, balloon=False))
        assert out.ok, out.message
        r = out.response
        mirror_h = np.abs(r.spl_h_db - r.spl_h_db[:, ::-1]).max()
        mirror_v = np.abs(r.spl_v_db - r.spl_v_db[:, ::-1]).max()
        hv = np.abs(r.spl_h_db - r.spl_v_db).max()
        results[label] = (mirror_h, mirror_v, hv, r.n_dof)
        emit(capsys, f"test 12 [{label}] n_dof={r.n_dof}: max|H(+a)-H(-a)|={mirror_h:.5f} dB  "
                     f"max|V(+a)-V(-a)|={mirror_v:.5f} dB  max|H-V|={hv:.5f} dB")
    for label, (mh, mv, hv, _) in results.items():
        assert mh < 0.05 and mv < 0.05, (label, mh, mv)


def test_12b_full_domain_and_quarter_domain_agree(solver, quarter_b, full_a, capsys):
    """Orchestrator CP-3 addendum: the same horn, full vs quarter domain, on meshes that resolve
    the whole band (f_max 3.1-3.2 kHz at epw 6), 0.1 dB."""
    freqs = [500.0, 1000.0, 2000.0, 3000.0]
    spec = spec_with(freqs, balloon=False)
    rf = solver.solve(full_a, spec)
    rq = solver.solve(quarter_b, spec)
    assert rf.ok and rq.ok, (rf.message, rq.message)
    f, q = rf.response, rq.response
    ax = f.axis_index
    d_abs = np.abs(f.spl_h_db - q.spl_h_db).max(axis=1)
    d_norm = np.abs(normalized_db(f.spl_h_db, ax) - normalized_db(q.spl_h_db, ax)).max(axis=1)
    d_vnorm = np.abs(normalized_db(f.spl_v_db, ax) - normalized_db(q.spl_v_db, ax)).max(axis=1)
    emit(capsys, "test 12b full vs quarter (resolved to ~3.1 kHz): dofs full=%d quarter=%d\n"
                 "  f_hz        abs_dB   norm_H_dB  norm_V_dB\n%s" % (
                     f.n_dof, q.n_dof,
                     "\n".join(f"  {fr:7.0f}  {a:9.4f}  {n:9.4f}  {v:9.4f}"
                               for fr, a, n, v in zip(freqs, d_abs, d_norm, d_vnorm))))
    assert d_norm.max() < 0.1 and d_vnorm.max() < 0.1
    assert d_abs.max() < 0.1


# 13
def test_13_idempotence_two_identical_solves(solver, quarter_a, capsys):
    spec = spec_with([500.0, 1000.0, 2000.0, 4000.0, 8000.0])
    a = solver.solve(quarter_a, spec)
    b = solver.solve(quarter_a, spec)
    assert a.ok and b.ok, (a.message, b.message)
    ra, rb = a.response, b.response
    dh = np.abs(ra.spl_h_db - rb.spl_h_db).max()
    dv = np.abs(ra.spl_v_db - rb.spl_v_db).max()
    db = np.abs(ra.spl_balloon_db - rb.spl_balloon_db).max()
    bit = np.array_equal(ra.spl_h_db, rb.spl_h_db) and np.array_equal(ra.spl_v_db, rb.spl_v_db)
    rel = np.abs(ra.p_h - rb.p_h).max() / np.abs(ra.p_h).max()
    emit(capsys, f"test 13 idempotence: max|dH|={dh:.3e} dB  max|dV|={dv:.3e} dB  "
                 f"max|dBalloon|={db:.3e} dB  bit-identical={bit}  max rel |dp_h|={rel:.3e}")
    assert max(dh, dv) < 1e-2


# 15
def test_15_symmetry_flag_mismatch_is_loudly_wrong(solver, quarter_b, capsys):
    spec = spec_with([500.0, 1000.0, 2000.0, 3000.0], balloon=False)
    good = solver.solve(quarter_b, spec)
    assert good.ok, good.message
    cfg_bad = dataclasses.replace(solver.make_config(quarter_b, spec), native_symmetry_plane=None)
    raw = solver.solve_raw(quarter_b, spec, cfg=cfg_bad)
    bad_h = raw.spl_db[:, 0, :]
    d = np.abs(bad_h - good.response.spl_h_db)
    emit(capsys, "test 15 quarter mesh solved WITHOUT the flag vs with it: "
                 f"max |dB| per frequency {np.round(d.max(axis=1), 2).tolist()}  overall max={d.max():.2f} dB  "
                 f"on-axis error per frequency {np.round(d[:, 36], 2).tolist()} dB")
    assert d.max() > 3.0


# 16
def test_16_solver_dof_count_vs_sizing_estimate(solver, quarter_a, full_a, capsys):
    cfg = seed_cfg()
    rows = []
    for label, mesh in (("quarter 2.3k", quarter_a), ("full 4.9k", full_a)):
        out = solver.solve(mesh, spec_with([1000.0], balloon=False))
        assert out.ok, out.message
        est = estimate_dofs(mesh.n_triangles, mesh.quadrants, cfg.mesh.dof_per_triangle)
        rows.append((label, mesh.n_triangles, out.response.n_dof, est))
    emit(capsys, "test 16 n_dof from the solver vs sizing.estimate_dofs (dof_per_triangle=%s):\n%s" % (
        cfg.mesh.dof_per_triangle,
        "\n".join(f"  {l:14s} n_tri={t:6d}  solver n_dof={n:6d}  estimate={e:6d}  ratio={e / n:.3f}"
                  for l, t, n, e in rows)))
    for label, t, n, e in rows:
        assert abs(e - n) / n <= 0.15, (label, n, e)


# 18
def test_18_asymmetric_placement_has_the_predicted_sign(solver, full_coarse, capsys):
    """Shift the horn to -X (and separately to -Y) by moving the observation origin to +d: the
    +angle side is farther and further off the horn's axis, so the cut must be QUIETER at +angle
    than at -angle. Predicted by hand: ~1/r alone gives 20*log10(2.15/1.85) = 1.3 dB at 90 deg.
    A reversed arc would flip the sign. Full-domain mesh: a translated quarter mesh would break
    its own symmetry planes."""
    d = 0.15
    freqs = [800.0, 1600.0]
    spec = spec_with(freqs, balloon=False)
    a = arc_angles_deg(73)
    pos, neg = a > 9.0, a < -9.0
    lines = []
    for plane, origin, key in (("H", (d, 0.0, 0.0), "spl_h_db"), ("V", (0.0, d, 0.0), "spl_v_db")):
        raw = solver.solve_raw(full_coarse, spec, frame_origin_m=origin)
        from hornlab_search.solve import beat as beat_mod
        r = beat_mod._to_response(raw, spec, full_coarse)
        spl = getattr(r, key)
        diff = spl[:, ::-1] - spl                       # spl(-a) - spl(+a) at index of +a
        by_angle = diff[:, a > 0]
        mean_gap = diff[:, pos].mean()
        lines.append(f"{plane}-cut, horn at -{plane == 'H' and 'X' or 'Y'}: mean[spl(-a)-spl(+a)] over 9..90 deg = "
                     f"{mean_gap:+.3f} dB ; at 90 deg per freq = {np.round(diff[:, -1], 3).tolist()} ; "
                     f"fraction of angle pairs with the predicted sign = {(by_angle > 0).mean():.3f}")
        other = key.replace("h", "v") if plane == "H" else key.replace("v", "h")
        sym = np.abs(getattr(r, other) - getattr(r, other)[:, ::-1]).max()
        lines.append(f"  (the orthogonal cut stays mirror-symmetric: max asymmetry {sym:.4f} dB)")
        assert mean_gap > 0.3, (plane, mean_gap)
        assert (by_angle[:, 3:] > 0).all(), (plane, "sign flips somewhere")
        assert diff[:, -1].min() > 0.5
        assert sym < 0.05
    emit(capsys, "test 18 asymmetric sign check:\n  " + "\n  ".join(lines))


def test_zz_release_leaves_no_julia_host_behind(solver, capsys):
    end = release_and_verify()
    emit(capsys, f"final release: {end}")
    assert end["hosts_left"] == []
    assert isinstance(solver, Backend)
