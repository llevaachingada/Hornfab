"""Process-wide GPU lock for hornlab-search (01_CONTRACTS section 14 extension).

Prevents two GPU jobs from running simultaneously on the same machine.

API
---
    from hornlab_search.search.gpulock import gpu_lock, GpuBusyError

    with gpu_lock("hornlab-search search --config ..."):
        ...  # GPU work here

Lock file: <repo>/runs/.gpu.lock  (or ``runs_root`` / ".gpu.lock" when injected)
Contents: JSON {pid, user, command, start_time (ISO local)}

Reentrancy
----------
``campaign`` runs each family's ``search`` as a subprocess.  The holder sets the
env-var ``HORNLAB_GPU_LOCK_OWNER=<pid>`` so children see it and skip re-acquiring.

Stale lock
----------
If the lock file names a PID that is no longer alive the lock is taken over silently
(no psutil dependency needed; a Windows-safe ``os.kill(pid, 0)`` is used instead).
"""
from __future__ import annotations

import contextlib
import datetime
import getpass
import json
import os
import time
from pathlib import Path

# Env-var set by the lock holder so child processes can skip acquisition.
_LOCK_OWNER_ENV = "HORNLAB_GPU_LOCK_OWNER"

REPO = Path(__file__).resolve().parents[2]
_DEFAULT_RUNS = REPO / "runs"


class GpuBusyError(RuntimeError):
    """Raised when the GPU lock is held by a live process."""


def _pid_alive(pid: int) -> bool:
    """Return True if the process with *pid* is currently running. Sends nothing to it.

    Windows: ``OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)`` + ``GetExitCodeProcess`` (STILL_ACTIVE).
    NOT ``os.kill(pid, 0)``: on Windows signal 0 is CTRL_C_EVENT, so that call tries to send Ctrl-C to
    the pid's console group and fails for a process in another console, which made a live lock holder
    look stale (2026-10-23). POSIX: ``os.kill(pid, 0)`` is the standard existence probe.
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        k32.CloseHandle.argtypes = (wintypes.HANDLE,)
        h = k32.OpenProcess(0x1000, False, pid)            # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ctypes.get_last_error() == 5            # ERROR_ACCESS_DENIED: exists, not ours
        try:
            code = wintypes.DWORD()
            if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                return True                                # opened but unreadable: assume alive
            return code.value == 259                       # STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _lock_path(runs_root: Path | None = None) -> Path:
    root = Path(runs_root) if runs_root is not None else _DEFAULT_RUNS
    root.mkdir(parents=True, exist_ok=True)
    return root / ".gpu.lock"


def _read_lock(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_lock(path: Path, pid: int, command: str) -> None:
    data = {
        "pid": pid,
        "user": _safe_user(),
        "command": command,
        "start_time": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _safe_user() -> str:
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001
        return "unknown"


def _acquire(path: Path, command: str) -> bool:
    """Try to create the lock file exclusively.  Return True on success."""
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    try:
        data = json.dumps({
            "pid": os.getpid(),
            "user": _safe_user(),
            "command": command,
            "start_time": datetime.datetime.now().isoformat(timespec="seconds"),
        }).encode()
        os.write(fd, data)
    finally:
        os.close(fd)
    return True


@contextlib.contextmanager
def gpu_lock(command: str, runs_root: Path | None = None):
    """Context manager that acquires the GPU lock for the duration of *command*.

    Raises :class:`GpuBusyError` if the lock is held by a live process.
    Takes over a stale lock whose PID is gone.
    Child processes whose ``HORNLAB_GPU_LOCK_OWNER`` env-var names the current
    lock PID proceed without acquiring (reentrancy for campaign subprocesses).
    Removes the lock on exit even on KeyboardInterrupt, but only when it still
    owns the lock.
    """
    path = _lock_path(runs_root)
    my_pid = os.getpid()

    # ---- reentrancy: a child whose env names the current lock's PID skips acquisition
    owner_env = os.environ.get(_LOCK_OWNER_ENV, "").strip()
    if owner_env:
        try:
            env_pid = int(owner_env)
        except ValueError:
            env_pid = None
        if env_pid is not None:
            # read the lock to confirm it's still ours
            lock_data = _read_lock(path)
            if lock_data and lock_data.get("pid") == env_pid:
                # We are a descendant of the lock holder - skip acquisition entirely
                yield
                return

    # ---- attempt to acquire
    acquired = False
    while True:
        if _acquire(path, command):
            acquired = True
            break
        # Lock file exists - check if stale
        lock_data = _read_lock(path)
        if lock_data is None:
            # Race: file vanished between our check and the read - retry
            time.sleep(0.05)
            continue
        holder_pid = lock_data.get("pid")
        if holder_pid is None or not _pid_alive(holder_pid):
            # Stale lock - try to remove and re-acquire
            try:
                path.unlink()
            except OSError:
                pass
            time.sleep(0.05)
            continue
        # Lock is held by a live process
        user = lock_data.get("user", "?")
        cmd = lock_data.get("command", "?")
        start = lock_data.get("start_time", "?")
        raise GpuBusyError(
            f'GPU busy: {user} running "{cmd}" (pid {holder_pid}) since {start}'
        )

    # ---- set env var for children
    old_env = os.environ.get(_LOCK_OWNER_ENV)
    os.environ[_LOCK_OWNER_ENV] = str(my_pid)
    try:
        yield
    finally:
        # Restore env
        if old_env is None:
            os.environ.pop(_LOCK_OWNER_ENV, None)
        else:
            os.environ[_LOCK_OWNER_ENV] = old_env
        # Remove lock only if we still own it
        if acquired:
            lock_data = _read_lock(path)
            if lock_data and lock_data.get("pid") == my_pid:
                try:
                    path.unlink()
                except OSError:
                    pass
