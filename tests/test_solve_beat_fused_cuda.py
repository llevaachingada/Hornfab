"""WP15 GPU gate: the fused CUDA Burton-Miller path vs the default CUDA path.

Plan: docs/research/senior_pass_2026-10-24/04_IMPLEMENTATION_PLAN.md WP15 step 9; fork branch
hornlab-search/fused-cuda @ fa99ee5 in C:\\Users\\hunte\\Hrns\\forks\\hornlab-beat-bem.

Requires the FORK INSTALLED BY SHA (docs/FORKS.md step 4) for the A/B part: the base pin's
driver emits no `assembly_path` diagnostics and has no fused path (the proven-refusal part
passes on any installation, the A/B part only on the fused fork).

Run: .venv\\Scripts\\python.exe -m pytest tests/test_solve_beat_fused_cuda.py -m "slow and gpu" -q
GPU hygiene: module fixture clears hosts + records the VRAM baseline; the host is RESTARTED
between the flag-off and flag-on solves (the env is set before each spawn, so the host inherits
it); the final release is verified against the process list.
"""
from __future__ import annotations

import dataclasses
import os

import numpy as np
import pytest

from conftest import requires_beat, requires_mesher
from hornlab_search.config import solve_spec
from hornlab_search.metrics.polar import beamwidth_deg
from hornlab_search.solve import worker
from hornlab_search.solve.beat import BeatBackend
from test_solve_support import build_seed_mesh, clean_host_state, emit, release_and_verify, seed_cfg

pytestmark = [requires_beat, requires_mesher, pytest.mark.slow, pytest.mark.gpu]

F_HZ = 2000.0          # the CP-7 seed quarter mesh at 2 kHz: small, fast, kR in the fine range
TOL_ON_DB = 0.01       # plan step 9: on-axis within 0.01 dB
TOL_BW_DEG = 0.1       # ... beamwidth within 0.1 deg
RTOL_Z = 1e-3          # ... z_throat rtol 1e-3
TOL_DET_DB = 1e-4      # flag-off self-reproduction floor; see the test's docstring and
                       # NOTES_FOR_SENIOR.md 2026-10-24 (bit-identity is NOT achievable across
                       # Float32 CUDA reduction order: ~1.6e-7 dB on the base pin, worst
                       # observed 1.74e-05 dB on a fork rerun)


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    state = clean_host_state()
    assert state["hosts_left"] == [], f"BEAT hosts survived the pre-test clear: {state}"
    mesh = build_seed_mesh(tmp_path_factory.mktemp("fused"), "1", F_HZ)
    yield _Ctx(mesh, solve_spec("screen", seed_cfg()))
    end = release_and_verify()
    assert end["hosts_left"] == [], f"a BEAT host survived release: {end}"


class _Ctx:
    def __init__(self, mesh, spec):
        self.mesh, self.spec = mesh, spec


def test_fused_cuda_matches_default_path(ctx, capsys):
    # ---- 1. the default path (flag off), from a clean host
    be_plain = BeatBackend("cuda")
    assert os.environ.get("HORNLAB_BEAT_FUSED_BM_CUDA") == "0"   # the default resets it explicitly
    out0 = be_plain.solve(ctx.mesh, ctx.spec)
    assert out0.ok, out0.message
    resp0 = out0.response
    assert resp0.meta.get("cuda_fused") in (False, None)

    # ---- 2. the guard: a fused REQUEST against a warm host spawned BEFORE the env must be
    # REFUSED (old-path data may never pass as a fused solve), not silently served.
    spec_fused = dataclasses.replace(ctx.spec, extra={"cuda_fused": True})
    be_fused_stale_host = BeatBackend("cuda", cuda_fused=True)   # env=1 now, but the host above
    # was spawned while it was "0": the driver runs the old path and the diagnostics must say so.
    out1 = be_fused_stale_host.solve(ctx.mesh, spec_fused)
    assert not out1.ok, "a warm host spawned without the env must not deliver a fused solve"
    assert "fused" in out1.message
    worker.shutdown(verify=True)

    # ---- 3. restart the host with the flag inherited, then solve fused
    be_fused = BeatBackend("cuda", cuda_fused=True)
    assert os.environ.get("HORNLAB_BEAT_FUSED_BM_CUDA") == "1"
    out2 = be_fused.solve(ctx.mesh, spec_fused)
    assert out2.ok, out2.message
    resp1 = out2.response
    assert resp1.meta.get("cuda_fused") is True
    diags = [d for d in (resp1.meta.get("native_diagnostics") or []) if isinstance(d, dict)]
    assert diags and all(d.get("assembly_path") == "fused_cuda" for d in diags), \
        f"diagnostics must prove the fused path ran: {diags}"

    # ---- 4. agreement (plan bars)
    ax = resp0.axis_index
    on0 = np.asarray(resp0.spl_h_db, dtype=float)[:, ax]
    on1 = np.asarray(resp1.spl_h_db, dtype=float)[:, ax]
    d_on = float(np.max(np.abs(on0 - on1)))
    bw0_h, _ = beamwidth_deg(resp0.h_angles_deg, resp0.spl_h_db[0])
    bw1_h, _ = beamwidth_deg(resp1.h_angles_deg, resp1.spl_h_db[0])
    bw0_v, _ = beamwidth_deg(resp0.v_angles_deg, resp0.spl_v_db[0])
    bw1_v, _ = beamwidth_deg(resp1.v_angles_deg, resp1.spl_v_db[0])
    z0 = np.asarray(resp0.z_throat, dtype=complex)
    z1 = np.asarray(resp1.z_throat, dtype=complex)
    d_z = float(np.max(np.abs(z0 - z1))) / max(float(np.max(np.abs(z0))), 1e-12)
    emit(capsys, f"fused_cuda A/B @ {F_HZ:.0f} Hz, seed quarter mesh: on-axis max diff "
                 f"{d_on:.4f} dB (bar {TOL_ON_DB}); bw H {bw0_h:.2f}->{bw1_h:.2f} deg, "
                 f"V {bw0_v:.2f}->{bw1_v:.2f} deg (bar {TOL_BW_DEG}); z_throat rel {d_z:.2e} "
                 f"(rtol {RTOL_Z})")
    assert d_on <= TOL_ON_DB, f"on-axis changed: {d_on:.4f} dB"
    assert abs(bw0_h - bw1_h) <= TOL_BW_DEG, "H beamwidth changed"
    assert abs(bw0_v - bw1_v) <= TOL_BW_DEG, "V beamwidth changed"
    assert d_z <= RTOL_Z, f"z_throat changed beyond rtol: {d_z:.2e}"


def test_flag_off_reproduces_itself_from_a_clean_host(ctx, capsys):
    """Flag OFF: the default path reproduces itself within the CUDA Float32 floor.

    Bit-for-bit (np.array_equal) is NOT attainable on this stack: the CUDA assembly/solve runs
    Float32 with order-varying reductions, so two solves of the SAME spec differ at the ulp
    level, and the spread VARIES BY RUN. Measured with the original zero-tolerance assertion
    on BOTH installs (pre-existing upstream property, not introduced by the fork):
      - fork fa99ee5:  max |d spl_h_db| ~9e-8 dB  (runs/m2_fused_cuda/fused_gpu_test.log)
      - base 38544d2:  max |d spl_h_db| ~1.6e-7 dB (runs/m2_fused_cuda/det_check_base_pin.log)
      - fork fa99ee5 rerun: 1.74e-05 dB — the WORST observed (fused_gpu_test_rerun.log)
    The floor below (1e-4 dB) sits ~5.7x above that worst measurement (not three orders of
    margin — the earlier ~1e-7 numbers oversold it) and ~400x below the CP-7f A/B bar
    (0.039 dB). If a flake ever crosses the floor, 1e-3 dB is still 39x below the bar — but
    that decision waits for a REPRODUCED crossing (rule-7 spirit); a real path/cache/host
    mixup moves results by full dB.
    """
    worker.shutdown(verify=True)                                # leave the fused host behind
    be = BeatBackend("cuda")
    assert os.environ.get("HORNLAB_BEAT_FUSED_BM_CUDA") == "0"
    out_a = be.solve(ctx.mesh, ctx.spec)
    assert out_a.ok, out_a.message
    out_b = be.solve(ctx.mesh, ctx.spec)
    assert out_b.ok, out_b.message
    a = np.asarray(out_a.response.spl_h_db, dtype=float)
    b = np.asarray(out_b.response.spl_h_db, dtype=float)
    d = float(np.max(np.abs(a - b)))
    emit(capsys, f"flag-off determinism, same spec twice: max |d spl_h_db| "
                 f"{d:.2e} dB (floor {TOL_DET_DB}; CP-7f bar 0.039)")
    assert d <= TOL_DET_DB, "the flag-off path moved beyond its measured determinism floor"