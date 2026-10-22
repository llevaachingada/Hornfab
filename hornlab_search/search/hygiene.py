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
         "Get-CimInstance Win32_Process -Filter \"Name='julia.exe'\" | "
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
        if "julia" not in line.lower():
            continue
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        try:
            pid = int(parts[1])
        except ValueError:
            continue
        cmdline = parts[10] if len(parts) > 10 else ""
        if "julia" in cmdline.lower() and _cmdline_matches(cmdline):
            out.append({"pid": pid, "cmdline": cmdline})
    return out


def _cmdline_matches(cmdline: str) -> bool:
    """Return True when the command line mentions any project keyword."""
    low = cmdline.lower()
    return any(kw in low for kw in _PROJECT_KEYWORDS)


# ------------------------------------------------------------------ killing


def clear_julia(procs: list[dict[str, Any]] | None = None) -> list[int]:
    """Kill only Julia processes that belong to this project.

    If ``procs`` is None, calls :func:`list_project_julia` first.
    Returns the list of PIDs that were killed (or attempted).
    Only processes whose command line contains 'hornlab' or 'beat' are touched.
    """
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
        log.info("clear_julia: killing julia pid %d (%.80s)", pid, cmdline)
        try:
            if _is_windows() or _SIGKILL is None:
                subprocess.run(["taskkill", "/F", "/PID", str(pid)],
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
