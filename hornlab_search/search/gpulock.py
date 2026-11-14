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
import sys
import time
from pathlib import Path
from typing import Callable

# Env-var set by the lock holder so child processes can skip acquisition.
_LOCK_OWNER_ENV = "HORNLAB_GPU_LOCK_OWNER"
#: Policy when the lock is held by a LIVE process. Owner decision 2026-11-13: an interactive
#: operator is allowed to overlap another GPU job ("I'm smart enough to not be running testing
#: while I'm doing a solve"), so the default is to WARN and proceed instead of refusing. Set
#: ``HORNLAB_GPU_LOCK=refuse`` for an unattended night/measurement run, or ``off`` to be silent.
_POLICY_ENV = "HORNLAB_GPU_LOCK"
_POLICIES = ("refuse", "warn", "off")
_DEFAULT_POLICY = "warn"
#: The CPU lane's own marker/lock, held by the nightly controller (2026-11-12 two-lane night).
#: Same mechanism, separate file: a live CPU lock means the CPU lane's Julia hosts must be left
#: alone by the GPU lane's gpu-clean/night hygiene, and vice versa.
_CPU_LANE_LOCK_OWNER_ENV = "HORNLAB_CPU_LANE_LOCK_OWNER"

#: Lane name -> its lock file name under ``runs/``. Two independent lanes, two independent locks.
LANE_LOCK_FILES = {"gpu": ".gpu.lock", "cpu": ".cpu.lane.lock"}

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


def lane_lock_path(lane: str, runs_root: Path | None = None) -> Path:
    """The lock file for ``lane`` (``gpu`` -> ``runs/.gpu.lock``, ``cpu`` -> ``runs/.cpu.lane.lock``).

    The CPU lane's marker is deliberately a *separate file* with the same semantics as the GPU
    lock, so the two lanes never contend for one marker and a live one can be recognised by the
    other lane's hygiene code. Unknown lane names are refused loudly (no silent default).
    """
    name = LANE_LOCK_FILES.get(str(lane).lower())
    if name is None:
        raise ValueError(f"unknown lane {lane!r} (known: {sorted(LANE_LOCK_FILES)})")
    root = Path(runs_root) if runs_root is not None else _DEFAULT_RUNS
    root.mkdir(parents=True, exist_ok=True)
    return root / name


def live_locked_lanes(runs_root: Path | None = None, *,
                      alive: "Callable[[int], bool] | None" = None) -> set[str]:
    """Lane names whose lock is held by a LIVE process other than us.

    Used by host-cleanup code to satisfy the two-lane rule: never touch a host of a lane whose
    lock is live. A dead holder (the 2026-10-28 timeout case) is not protected; a lock we hold
    ourselves is not protected either (so our own cleanup can still run).
    """
    root = Path(runs_root) if runs_root is not None else _DEFAULT_RUNS
    probe = alive or _pid_alive
    out: set[str] = set()
    for lane, name in LANE_LOCK_FILES.items():
        data = _read_lock(root / name)
        if not data:
            continue
        raw_pid = data.get("pid")
        if raw_pid is None:
            continue
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            continue
        if pid > 0 and pid != os.getpid() and probe(pid):
            out.add(lane)
    return out


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


def _resolve_policy(policy: str | None) -> str:
    """``policy`` argument > ``HORNLAB_GPU_LOCK`` env > :data:`_DEFAULT_POLICY`."""
    raw = policy if policy is not None else os.environ.get(_POLICY_ENV, "")
    value = str(raw).strip().lower() or _DEFAULT_POLICY
    if value not in _POLICIES:
        raise ValueError(f"unknown GPU lock policy {value!r} (known: {_POLICIES})")
    return value


@contextlib.contextmanager
def _locked(command: str, path: Path, owner_env: str, policy: str | None = None):
    """The shared lock mechanism: exclusive file create, stale takeover, reentrancy via
    ``owner_env``, and removal on exit only when the lock is still ours."""
    my_pid = os.getpid()

    # ---- reentrancy: a child whose env names the current lock's PID skips acquisition
    env_raw = os.environ.get(owner_env, "").strip()
    if env_raw:
        try:
            env_pid = int(env_raw)
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
        if holder_pid is None or not _pid_alive(int(holder_pid)):
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
        busy = f'GPU busy: {user} running "{cmd}" (pid {holder_pid}) since {start}'
        resolved = _resolve_policy(policy)
        if resolved == "refuse":
            raise GpuBusyError(busy)
        if resolved == "warn":
            print(f"WARNING: {busy}. Proceeding WITHOUT the GPU lock "
                  f"(HORNLAB_GPU_LOCK=refuse to make this fatal; run `hornlab-search gpu-clean` "
                  f"before the next measurement).", file=sys.stderr)
        # warn/off: proceed unlocked. We never acquired, so the finally below must not unlink.
        yield
        return

    # ---- set env var for children
    old_env = os.environ.get(owner_env)
    os.environ[owner_env] = str(my_pid)
    try:
        yield
    finally:
        # Restore env
        if old_env is None:
            os.environ.pop(owner_env, None)
        else:
            os.environ[owner_env] = old_env
        # Remove lock only if we still own it
        if acquired:
            lock_data = _read_lock(path)
            if lock_data and lock_data.get("pid") == my_pid:
                try:
                    path.unlink()
                except OSError:
                    pass


@contextlib.contextmanager
def gpu_lock(command: str, runs_root: Path | None = None, policy: str | None = None):
    """Context manager that acquires the GPU lock for the duration of *command*.

    A live holder is handled per :func:`_resolve_policy`: ``refuse`` raises
    :class:`GpuBusyError`, ``warn`` (the default, owner decision 2026-11-13) prints a loud
    warning and proceeds unlocked, ``off`` proceeds silently. Stale locks (dead PID) are taken
    over regardless of policy.
    Child processes whose ``HORNLAB_GPU_LOCK_OWNER`` env-var names the current
    lock PID proceed without acquiring (reentrancy for campaign subprocesses).
    Removes the lock on exit even on KeyboardInterrupt, but only when it still
    owns the lock.
    """
    with _locked(command, _lock_path(runs_root), _LOCK_OWNER_ENV, policy):
        yield


@contextlib.contextmanager
def cpu_lane_lock(command: str, runs_root: Path | None = None):
    """Context manager for the CPU lane's own marker (``runs/.cpu.lane.lock``).

    Same mechanism as :func:`gpu_lock`, separate file: the CPU lane holds this while its nightly
    controller runs, so GPU-side hygiene can see that the lane is live and must not touch its
    hosts. Reentrancy uses ``HORNLAB_CPU_LANE_LOCK_OWNER``; a stale holder is taken over.
    """
    with _locked(command, lane_lock_path("cpu", runs_root), _CPU_LANE_LOCK_OWNER_ENV):
        yield
