"""GPU and Julia process hygiene for campaign runs (TYPOLOGY_PLAN.md s7, LANE B).

Rules from CLAUDE.md GPU / Julia hygiene:
- Only kill Julia processes whose command line mentions 'hornlab' or 'beat'.
- Record VRAM before and after each search job.
- Make all hygiene functions mockable for tests (no module-level subprocess calls).
"""
from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
from typing import Any

try:
    import signal as _signal
    _SIGKILL = getattr(_signal, "SIGKILL", None)
except ImportError:
    _SIGKILL = None

log = logging.getLogger("hornlab_search.search.hygiene")

# Keywords that identify Julia processes started by this project (CLAUDE.md rule)
_PROJECT_KEYWORDS = ("hornlab", "beat")

#: Default for ``lane=``: derive it from HORNLAB_BEAT_WORKER_DIR (and fall back to the historical
#: keyword-only behaviour outside a lane). Distinct from an explicit None.
_AUTO_LANE = object()


def _lane_helpers():
    """The shared lane classifier from ``solve.worker`` (one source of truth, no duplication)."""
    from ..solve import worker
    return worker


def _default_lane() -> str | None:
    return _lane_helpers().lane_from_env()


def _is_windows() -> bool:
    return platform.system() == "Windows"


# ------------------------------------------------------------------ process listing


def list_project_julia() -> list[dict[str, Any]]:
    """Return Julia processes whose command line mentions 'hornlab' or 'beat'.

    Windows: PowerShell ``Get-CimInstance Win32_Process`` for julia.exe -> JSON.
    POSIX:   ``ps aux`` filtered for julia.

    Returns a list of ``{pid: int, cmdline: str}`` dicts.
    Raises no exception on missing tools; returns [] instead and logs a warning.
    """
    try:
        if _is_windows():
            return _list_project_julia_windows()
        return _list_project_julia_posix()
    except Exception as exc:  # noqa: BLE001
        log.warning("list_project_julia: could not enumerate Julia processes: %s", exc)
        return []


def _list_project_julia_windows() -> list[dict[str, Any]]:
    """PowerShell query for julia.exe processes; returns [] if PowerShell unavailable."""
    ps_cmd = (
        "Get-CimInstance Win32_Process -Filter \\\"Name='julia.exe'\\\" | "
        "Select-Object ProcessId, CommandLine | ConvertTo-Json -Depth 1"
    )
    # Use powershell.exe -Command syntax
    r = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         # julia.exe AND the BEAT worker_host python processes: the host respawns julia, so killing
         # julia alone leaves a warm host behind (found 2026-10-22).
         "Get-CimInstance Win32_Process -Filter \"Name='julia.exe' OR "
         "(Name='python.exe' AND CommandLine LIKE '%hornlab_beat_bem.worker_host%')\" | "
         "Select-Object ProcessId,CommandLine | ConvertTo-Json -Depth 1"],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        data = json.loads(r.stdout)
    except (ValueError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        data = [data]
    out = []
    for item in data:
        pid = item.get("ProcessId") or item.get("processId")
        cmdline = str(item.get("CommandLine") or item.get("commandLine") or "")
        if pid and _cmdline_matches(cmdline):
            out.append({"pid": int(pid), "cmdline": cmdline})
    return out


def _list_project_julia_posix() -> list[dict[str, Any]]:
    """``ps aux`` based listing for POSIX (Linux, macOS)."""
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=30)
    out = []
    for line in r.stdout.splitlines():
        low = line.lower()
        if "julia" not in low and "hornlab_beat_bem.worker_host" not in low:
            continue
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        try:
            pid = int(parts[1])
        except ValueError:
            continue
        cmdline = parts[10] if len(parts) > 10 else ""
        if ("julia" in cmdline.lower() or "worker_host" in cmdline.lower()) and _cmdline_matches(cmdline):
            out.append({"pid": pid, "cmdline": cmdline})
    return out


def _cmdline_matches(cmdline: str) -> bool:
    """Return True when the command line mentions any project keyword."""
    low = cmdline.lower()
    return any(kw in low for kw in _PROJECT_KEYWORDS)


# ------------------------------------------------------------------ killing


def clear_julia(procs: list[dict[str, Any]] | None = None, *,
                lane: str | None | object = _AUTO_LANE,
                runs_root=None, force: bool = False) -> list[int]:
    """Kill only Julia/BEAT processes that belong to this project AND to ``lane``.

    If ``procs`` is None, calls :func:`list_project_julia` first.
    Returns the list of PIDs that were killed (or attempted).
    Only processes whose command line contains 'hornlab' or 'beat' are touched.

    Two-lane rule (2026-11-12). ``lane`` defaults to the lane named by
    ``HORNLAB_BEAT_WORKER_DIR``. With a lane, a process is killed only when its ``--dir`` names the
    SAME lane; a process whose lane cannot be determined is logged as ``unknown host, left alone``
    and kept, and a host of ANOTHER lane whose lock is live is never touched (unless ``force``).
    Our own lane's live lock never blocks us: its holder is this lane's authority (the night
    controller), which is the process calling pre/post hygiene. With no lane at all the historical
    keyword-only behaviour is preserved.
    """
    worker_mod = _lane_helpers()
    resolved_lane = _default_lane() if lane is _AUTO_LANE else (lane or None)
    protected: set[str] = set()
    if not force:
        try:
            protected = worker_mod.live_locked_lanes(runs_root)
        except Exception:  # noqa: BLE001 - lock lookup must never stop a cleanup
            protected = set()
        if resolved_lane is not None:
            protected.discard(str(resolved_lane).lower())
    if procs is None:
        procs = list_project_julia()
    killed = []
    for p in procs:
        pid = p["pid"]
        cmdline = p.get("cmdline", "")
        if not _cmdline_matches(cmdline):
            log.warning("clear_julia: skipping pid %d — cmdline does not match project keywords: %.120s",
                        pid, cmdline)
            continue
        pl = worker_mod.host_lane(cmdline)
        if pl is not None and pl in protected:
            log.warning("clear_julia: lane %s lock is live; leaving pid %d alone", pl, pid)
            continue
        if resolved_lane is not None:
            if pl is None:
                log.info("unknown host, left alone: pid %d (lane %s)", pid, resolved_lane)
                continue
            if pl != str(resolved_lane).lower():
                log.info("clear_julia: pid %d belongs to lane %s (mine %s); left alone",
                         pid, pl, resolved_lane)
                continue
        log.info("clear_julia: killing julia pid %d (%.80s)", pid, cmdline)
        try:
            if _is_windows() or _SIGKILL is None:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],   # /T: the host's julia child too
                                capture_output=True, timeout=10)
            else:
                os.kill(pid, _SIGKILL)
            killed.append(pid)
        except (OSError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
            log.warning("clear_julia: could not kill pid %d: %s", pid, exc)
    return killed


# ------------------------------------------------------------------ VRAM


def vram_used_mib() -> float | None:
    """Query ``nvidia-smi`` for the first GPU's used VRAM in MiB.

    Returns None when nvidia-smi is unavailable or the output cannot be parsed.
    """
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return None
        line = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
        return float(line.strip())
    except (FileNotFoundError, IndexError, ValueError, subprocess.TimeoutExpired):
        return None


# ------------------------------------------------------------------ snapshot helper


def hygiene_snapshot(label: str) -> dict[str, Any]:
    """Return a dict with GPU and Julia state for a campaign log entry."""
    julia_procs = list_project_julia()
    vram = vram_used_mib()
    return {
        "label": label,
        "julia_project_procs": len(julia_procs),
        "julia_pids": [p["pid"] for p in julia_procs],
        "vram_used_mib": vram,
    }
