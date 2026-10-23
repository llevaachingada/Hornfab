"""Offline: a dead BEAT worker host is recovered and the candidate retried once (2026-10-23,
OSSE seed 4101: one host reset turned into 21 solve_failed rows and ended the search)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from hornlab_search.solve import beat as beat_mod
from hornlab_search.solve import worker

RESET = ConnectionResetError(10054, "An existing connection was forcibly closed by the remote host")


@pytest.fixture
def backend(monkeypatch):
    calls = {"recover": 0, "warm": 0}
    monkeypatch.setattr(beat_mod, "check_symmetry_pairing", lambda mesh: None)
    monkeypatch.setattr(beat_mod, "_to_response", lambda raw, spec, mesh: SimpleNamespace(meta={}))
    monkeypatch.setattr(worker, "recover_after_failure",
                        lambda name: calls.__setitem__("recover", calls["recover"] + 1))
    monkeypatch.setattr(worker, "warm", lambda be: calls.__setitem__("warm", calls["warm"] + 1))
    monkeypatch.setattr(worker, "note_solve_seconds", lambda *a, **k: None)
    be = beat_mod.BeatBackend("cuda", track_vram=False)
    return be, calls


def scripted(be, monkeypatch, script):
    """solve_raw raises / returns per call from ``script``; returns the call log."""
    log = []

    def solve_raw(mesh, spec, *, surface_traces=False):
        item = script[len(log)]
        log.append(item)
        if isinstance(item, BaseException):
            raise item
        return item
    monkeypatch.setattr(be, "solve_raw", solve_raw)
    return log


MESH = SimpleNamespace(path="m.msh", n_triangles=10, n_dof=10, quadrants=4)


def test_worker_exit_is_recovered_rewarmed_and_retried_once(backend, monkeypatch):
    be, calls = backend
    log = scripted(be, monkeypatch, [RESET, object()])
    out = be.solve(MESH, None)
    assert out.ok and len(log) == 2
    assert calls == {"recover": 1, "warm": 1}
    assert out.response.meta["worker_exit_retries"] == 1


def test_a_second_worker_exit_is_reported_once_and_not_retried_again(backend, monkeypatch):
    be, calls = backend
    log = scripted(be, monkeypatch, [RESET, RESET, object()])
    out = be.solve(MESH, None)
    assert not out.ok and len(log) == 2
    assert out.message.startswith("[worker_exit]") and "after one re-warm and retry" in out.message
    assert calls["warm"] == 1


def test_other_failures_are_not_retried(backend, monkeypatch):
    be, calls = backend
    log = scripted(be, monkeypatch, [ValueError("singular system"), object()])
    out = be.solve(MESH, None)
    assert not out.ok and len(log) == 1 and calls["warm"] == 0
    assert out.message.startswith("[other]")


def test_a_failed_rewarm_is_this_candidates_failure_not_a_crash(backend, monkeypatch):
    be, calls = backend
    scripted(be, monkeypatch, [RESET, object()])

    def boom(_be):
        raise RuntimeError("julia did not start")
    monkeypatch.setattr(worker, "warm", boom)
    out = be.solve(MESH, None)
    assert not out.ok and "re-warm after worker_exit failed" in out.message


def test_recover_after_failure_drops_the_librarys_cached_clients(monkeypatch):
    """Killing the host is not enough: hornlab_beat_bem caches a HostedBeatWorker whose socket
    stays dead. Recovery must empty that cache (detach_workers) as well."""
    order = []
    monkeypatch.setattr(worker, "clear_stale_hosts", lambda **kw: order.append("kill") or [])
    worker._WARM.add("beat_cuda")
    worker.recover_after_failure("beat_cuda", drop_clients=lambda: order.append("drop"))
    assert order == ["drop", "kill"] and not worker.is_warm("beat_cuda")


def test_recover_after_failure_defaults_to_detach(monkeypatch):
    seen = []
    monkeypatch.setattr(worker, "detach", lambda: seen.append("detach"))
    monkeypatch.setattr(worker, "clear_stale_hosts", lambda **kw: [])
    worker.recover_after_failure("beat_cuda")
    assert seen == ["detach"]
