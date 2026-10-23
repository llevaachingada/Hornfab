"""_pid_alive must see live processes in OTHER consoles and must never signal them (2026-10-23 bug:
os.kill(pid, 0) on Windows is CTRL_C_EVENT, so a live lock holder looked stale). Offline."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from hornlab_search.search import gpulock


def test_live_child_in_a_new_process_group_is_alive_then_dead():
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} \
        if os.name == "nt" else {"start_new_session": True}
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], **kw)
    try:
        assert gpulock._pid_alive(p.pid) is True
        assert p.poll() is None                       # the probe did not kill or interrupt it
    finally:
        p.kill()
        p.wait()
    assert gpulock._pid_alive(p.pid) is False
    assert gpulock._pid_alive(0) is False


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific")
def test_windows_probe_never_calls_os_kill(monkeypatch):
    def boom(*a):
        raise AssertionError("os.kill must not be used on Windows (signal 0 is CTRL_C_EVENT)")
    monkeypatch.setattr(gpulock.os, "kill", boom)
    assert gpulock._pid_alive(os.getpid()) is True
