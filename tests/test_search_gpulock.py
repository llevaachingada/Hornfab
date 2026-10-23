"""Offline tests for hornlab_search.search.gpulock.

All tests use tmp_path; no GPU, no solver, no subprocess.
"""
from __future__ import annotations

import json
import os
import signal
import sys
from pathlib import Path

import pytest

from hornlab_search.search.gpulock import (
    GpuBusyError,
    _LOCK_OWNER_ENV,
    _lock_path,
    _pid_alive,
    gpu_lock,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _write_foreign_lock(lock_path: Path, pid: int, user: str = "tester", command: str = "test cmd") -> None:
    """Write a lock file as if another process (or a dead one) owns it."""
    import datetime
    data = {
        "pid": pid,
        "user": user,
        "command": command,
        "start_time": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    lock_path.write_text(json.dumps(data), encoding="utf-8")


def _dead_pid() -> int:
    """Return a PID that is very unlikely to be alive."""
    # Use a large unlikely PID
    return 99_999_998


# ---------------------------------------------------------------------------
# basic acquire / release
# ---------------------------------------------------------------------------


def test_acquire_and_release(tmp_path):
    """Lock file is created while inside context and removed on exit."""
    lp = _lock_path(tmp_path)
    assert not lp.exists()
    with gpu_lock("test command", runs_root=tmp_path):
        assert lp.exists()
        data = json.loads(lp.read_text())
        assert data["pid"] == os.getpid()
        assert "command" in data
        assert "start_time" in data
    assert not lp.exists()


def test_second_acquire_live_pid_raises(tmp_path):
    """Second acquire when the lock is held by a live PID raises GpuBusyError."""
    lp = _lock_path(tmp_path)
    # Write a lock with our own PID as the "foreign" holder (alive)
    _write_foreign_lock(lp, os.getpid(), user="other", command="other cmd")
    # Clear env var so reentrancy logic doesn't apply
    old = os.environ.pop(_LOCK_OWNER_ENV, None)
    try:
        with pytest.raises(GpuBusyError) as exc_info:
            with gpu_lock("new command", runs_root=tmp_path):
                pass
        msg = str(exc_info.value)
        assert "GPU busy" in msg
        assert "other" in msg          # user
        assert "other cmd" in msg      # command
        assert str(os.getpid()) in msg  # pid
    finally:
        if old is not None:
            os.environ[_LOCK_OWNER_ENV] = old


def test_error_message_fields(tmp_path):
    """GpuBusyError message contains user, command, pid, and time."""
    lp = _lock_path(tmp_path)
    _write_foreign_lock(lp, os.getpid(), user="alice", command="hornlab-search search")
    old = os.environ.pop(_LOCK_OWNER_ENV, None)
    try:
        with pytest.raises(GpuBusyError) as exc_info:
            with gpu_lock("new", runs_root=tmp_path):
                pass
        msg = str(exc_info.value)
        assert "alice" in msg
        assert "hornlab-search search" in msg
        assert str(os.getpid()) in msg
    finally:
        if old is not None:
            os.environ[_LOCK_OWNER_ENV] = old


def test_stale_lock_taken_over(tmp_path):
    """A lock file naming a dead PID is taken over silently."""
    lp = _lock_path(tmp_path)
    dead = _dead_pid()
    assert not _pid_alive(dead), f"PID {dead} should not be alive"
    _write_foreign_lock(lp, dead)
    # Should not raise
    with gpu_lock("takeover", runs_root=tmp_path):
        data = json.loads(lp.read_text())
        assert data["pid"] == os.getpid()
    assert not lp.exists()


# ---------------------------------------------------------------------------
# reentrancy via env var
# ---------------------------------------------------------------------------


def test_reentrancy_env_var(tmp_path):
    """A child that sets HORNLAB_GPU_LOCK_OWNER to the current lock PID skips acquisition."""
    lp = _lock_path(tmp_path)
    with gpu_lock("outer", runs_root=tmp_path):
        # Simulate a child process that already has the env var set by the parent
        outer_pid = os.getpid()
        os.environ[_LOCK_OWNER_ENV] = str(outer_pid)
        # Inner call should not raise or deadlock
        with gpu_lock("inner", runs_root=tmp_path):
            pass  # Should pass through without trying to re-acquire
        # Lock still exists and still belongs to outer
        assert lp.exists()
    assert not lp.exists()


def test_reentrancy_env_var_wrong_pid(tmp_path):
    """If env var names a DIFFERENT pid, reentrancy does NOT apply."""
    lp = _lock_path(tmp_path)
    # Write a lock held by our own PID (alive)
    _write_foreign_lock(lp, os.getpid(), user="holder")
    # Set env var to a dead pid (not the lock holder)
    dead = _dead_pid()
    old = os.environ.get(_LOCK_OWNER_ENV)
    os.environ[_LOCK_OWNER_ENV] = str(dead)
    try:
        with pytest.raises(GpuBusyError):
            with gpu_lock("child", runs_root=tmp_path):
                pass
    finally:
        if old is None:
            os.environ.pop(_LOCK_OWNER_ENV, None)
        else:
            os.environ[_LOCK_OWNER_ENV] = old


# ---------------------------------------------------------------------------
# KeyboardInterrupt releases the lock
# ---------------------------------------------------------------------------


def test_lock_released_after_keyboard_interrupt(tmp_path):
    """Lock is removed even when the body raises KeyboardInterrupt."""
    lp = _lock_path(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        with gpu_lock("interrupted", runs_root=tmp_path):
            assert lp.exists()
            raise KeyboardInterrupt
    assert not lp.exists()


# ---------------------------------------------------------------------------
# env var cleanup
# ---------------------------------------------------------------------------


def test_env_var_set_and_restored(tmp_path):
    """HORNLAB_GPU_LOCK_OWNER is set while inside and restored on exit."""
    old = os.environ.pop(_LOCK_OWNER_ENV, None)
    try:
        with gpu_lock("env-check", runs_root=tmp_path):
            assert os.environ.get(_LOCK_OWNER_ENV) == str(os.getpid())
        assert _LOCK_OWNER_ENV not in os.environ
    finally:
        if old is not None:
            os.environ[_LOCK_OWNER_ENV] = old
