"""Offline tests for the gpu-clean CLI command and the doctor disk-space check.

No GPU, no Julia, no solver.  hygiene and nvidia-smi are fully monkeypatched.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hornlab_search.cli import Doctor, _cmd_gpu_clean, main
from hornlab_search.search.gpulock import _LOCK_OWNER_ENV, _lock_path


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class FakeArgs:
    """Minimal args namespace for _cmd_gpu_clean."""
    force = False
    runs_dir = None
    cache_dir = None
    dataset_dir = None
    backend = None
    verbose = 0
    trace_fraction = 0.05


def _write_lock(lock_path: Path, pid: int, command: str = "other cmd") -> None:
    import datetime
    lock_path.write_text(
        json.dumps({"pid": pid, "user": "test", "command": command,
                    "start_time": datetime.datetime.now().isoformat(timespec="seconds")}),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# gpu-clean: refuse when locked by live other pid
# ---------------------------------------------------------------------------


def test_gpu_clean_refuses_when_locked(tmp_path, capsys):
    """gpu-clean exits 3 when the lock is held by a live other process."""
    lp = _lock_path(tmp_path)
    # Use a foreign PID (not our own) - we'll make _pid_alive return True for it
    foreign_pid = os.getpid() + 1000
    _write_lock(lp, foreign_pid)

    args = FakeArgs()
    args.runs_dir = str(tmp_path)

    # Clear env var so reentrancy logic doesn't apply
    old = os.environ.pop(_LOCK_OWNER_ENV, None)
    try:
        with patch("hornlab_search.search.gpulock._pid_alive", return_value=True):
            rc = _cmd_gpu_clean(args)
    finally:
        if old is not None:
            os.environ[_LOCK_OWNER_ENV] = old

    assert rc == 3
    captured = capsys.readouterr()
    assert "GPU busy" in captured.err


def test_gpu_clean_force_bypasses_lock(tmp_path, capsys):
    """--force skips the lock check and calls hygiene functions."""
    lp = _lock_path(tmp_path)
    _write_lock(lp, os.getpid())   # live process holds lock

    args = FakeArgs()
    args.runs_dir = str(tmp_path)
    args.force = True

    mock_procs = [{"pid": 12345, "cmdline": "julia hornlab_beat_bem"}]

    with patch("hornlab_search.search.hygiene.list_project_julia", return_value=mock_procs) as mock_list, \
         patch("hornlab_search.search.hygiene.clear_julia", return_value=[12345]) as mock_kill, \
         patch("hornlab_search.search.hygiene.vram_used_mib", return_value=1024.0) as mock_vram:
        rc = _cmd_gpu_clean(args)

    assert rc == 0
    captured = capsys.readouterr()
    assert "12345" in captured.out
    assert "1024" in captured.out


def test_gpu_clean_no_lock_runs_normally(tmp_path, capsys):
    """gpu-clean without a lock runs hygiene and reports VRAM."""
    args = FakeArgs()
    args.runs_dir = str(tmp_path)

    with patch("hornlab_search.search.hygiene.list_project_julia", return_value=[]) as mock_list, \
         patch("hornlab_search.search.hygiene.clear_julia", return_value=[]) as mock_kill, \
         patch("hornlab_search.search.hygiene.vram_used_mib", return_value=512.0):
        rc = _cmd_gpu_clean(args)

    assert rc == 0
    captured = capsys.readouterr()
    assert "no project" in captured.out.lower() or "0" in captured.out
    assert "512" in captured.out


def test_gpu_clean_no_nvidia_smi(tmp_path, capsys):
    """When nvidia-smi is missing, gpu-clean says so."""
    args = FakeArgs()
    args.runs_dir = str(tmp_path)

    with patch("hornlab_search.search.hygiene.list_project_julia", return_value=[]), \
         patch("hornlab_search.search.hygiene.clear_julia", return_value=[]), \
         patch("hornlab_search.search.hygiene.vram_used_mib", return_value=None):
        rc = _cmd_gpu_clean(args)

    assert rc == 0
    captured = capsys.readouterr()
    assert "nvidia-smi" in captured.out.lower() or "vram" in captured.out.lower()


# ---------------------------------------------------------------------------
# gpu-clean via main()
# ---------------------------------------------------------------------------


def test_gpu_clean_via_main(tmp_path, capsys):
    """main(['gpu-clean', '--runs-dir', ...]) dispatches correctly."""
    with patch("hornlab_search.search.hygiene.list_project_julia", return_value=[]), \
         patch("hornlab_search.search.hygiene.clear_julia", return_value=[]), \
         patch("hornlab_search.search.hygiene.vram_used_mib", return_value=0.0):
        rc = main(["gpu-clean", "--runs-dir", str(tmp_path)])
    assert rc == 0


# ---------------------------------------------------------------------------
# doctor disk-space check
# ---------------------------------------------------------------------------


def _make_disk_usage(total: int, free: int):
    """Return a shutil.disk_usage-compatible namedtuple."""
    import shutil
    return shutil.disk_usage.__class__  # unused; just build via shutil
    # We use collections.namedtuple directly
    from collections import namedtuple
    DU = namedtuple("disk_usage", ["total", "used", "free"])
    return DU(total=total, used=total - free, free=free)


def _disk_usage_mock(total: int, free: int):
    from collections import namedtuple
    DU = namedtuple("disk_usage", ["total", "used", "free"])
    return DU(total=total, used=total - free, free=free)


def test_doctor_disk_space_pass(tmp_path):
    """disk-space check passes and reports free GB."""
    free = 50 * 10**9
    total = 200 * 10**9
    mock_val = _disk_usage_mock(total, free)

    d = Doctor()
    with patch("hornlab_search.cli.shutil.disk_usage", return_value=mock_val):
        d.check_disk_space()

    assert len(d.results) == 1
    label, ok, reason = d.results[0]
    assert label == "disk-space"
    assert ok is True
    assert "WARNING" not in reason


def test_doctor_disk_space_warning_below_10gb(tmp_path):
    """disk-space check passes but prefixes WARNING when free < 10 GB."""
    free = 5 * 10**9  # 5 GB
    total = 200 * 10**9
    mock_val = _disk_usage_mock(total, free)

    d = Doctor()
    with patch("hornlab_search.cli.shutil.disk_usage", return_value=mock_val):
        d.check_disk_space()

    label, ok, reason = d.results[0]
    assert ok is True        # still passes
    assert "WARNING" in reason
    assert "5.0" in reason or "5" in reason
