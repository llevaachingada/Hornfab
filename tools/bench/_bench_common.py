"""Shared plumbing for the tools/bench scripts: host reset and GPU-memory sampling.

Two measurement defects found in the 2026-11-02 benches (docs/evidence/BENCH_AUDIT_2026-11-03.md):

1. ``taskkill /IM julia.exe`` is NOT a host reset. The BEAT host is a ``python -m
   hornlab_beat_bem.worker_host`` tree that respawns julia, so the warm host survived and "fresh host"
   arms were not fresh. ``kill_hosts`` here kills whole host trees through ``solve.worker``.
2. ``nvidia-smi memory.used`` cannot see WDDM sysmem fallback. When a CUDA allocation exceeds VRAM the
   Windows driver (>= 536.40, default policy) silently places it in shared system memory and the solve
   runs 5-10x slower instead of failing. ``GpuMemPeak`` samples the per-process ``\\GPU Process
   Memory(*)\\Shared Usage`` counter for the host tree, so a spilled arm is visible in the record.
   A CUDA timing with ``shared_peak_mib`` above a few hundred MiB measures PCIe paging, not the GPU.
"""
from __future__ import annotations

import os
import subprocess
import threading

from hornlab_search.solve import worker

#: Shared usage above this (MiB) on a CUDA arm means the solve spilled into system RAM.
SPILL_MIB = 512

_COUNTERS = ("Get-Counter '\\GPU Process Memory(*)\\Dedicated Usage','\\GPU Process Memory(*)\\Shared Usage' "
             "-EA SilentlyContinue | % { $_.CounterSamples } | % { $_.Path + '|' + [int64]$_.CookedValue }")


def kill_hosts() -> list[int]:
    """Kill every BEAT host tree (never by image name) and wait until the processes are gone."""
    return worker.clear_stale_hosts(force=True)


def nvsmi_used_mib() -> int | None:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True)
    try:
        return int(out.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return None


def _host_pids() -> set[int]:
    return worker.host_tree_pids(worker.list_processes()) | {os.getpid()}


def process_gpu_mib(pids: set[int]) -> tuple[int, int] | None:
    """(dedicated, shared) MiB summed over ``pids`` from the Windows GPU counters; None off Windows."""
    if os.name != "nt":
        return None
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _COUNTERS],
                       capture_output=True, text=True)
    ded = shared = 0
    for line in r.stdout.splitlines():
        path, _, val = line.rpartition("|")
        if "pid_" not in path:
            continue
        try:
            pid, value = int(path.split("pid_")[1].split("_")[0]), int(val)
        except ValueError:
            continue
        if pid in pids:
            if "dedicated usage" in path.lower():
                ded += value
            elif "shared usage" in path.lower():
                shared += value
    return ded >> 20, shared >> 20


class GpuMemPeak:
    """Sample from a thread (CLAUDE.md rule 5): device total (``peak``, nvidia-smi, includes other
    processes and CUDA.jl's cached pool), plus the host tree's own dedicated and SHARED usage."""

    def __init__(self, period: float = 1.0):
        self.period = period
        self.baseline = nvsmi_used_mib()
        self.peak = self.baseline or 0
        self.dedicated_peak_mib = 0
        self.shared_peak_mib = 0
        self._stop = threading.Event()

    def _loop(self) -> None:
        while not self._stop.is_set():
            v = nvsmi_used_mib()
            if v is not None:
                self.peak = max(self.peak, v)
            per = process_gpu_mib(_host_pids())
            if per is not None:
                self.dedicated_peak_mib = max(self.dedicated_peak_mib, per[0])
                self.shared_peak_mib = max(self.shared_peak_mib, per[1])
            self._stop.wait(self.period)

    def __enter__(self) -> "GpuMemPeak":
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._t.join(self.period * 3)

    @property
    def spilled(self) -> bool:
        return self.shared_peak_mib > SPILL_MIB

    def record(self) -> dict:
        return {"vram_baseline_mib": self.baseline, "peak_vram_mib": self.peak,
                "host_dedicated_peak_mib": self.dedicated_peak_mib,
                "host_shared_peak_mib": self.shared_peak_mib, "spilled": self.spilled}
