"""Opt-in stage timer (throughput packet WP0).

Off by default. Set ``HORNLAB_STAGE_TIMING=1`` and every candidate directory gets a
``stage_timing.ndjson`` (one JSON line per stage) next to ``design.json``. Nothing else changes:
no row, record, cache key or hash reads this file.

Usage inside the pipeline::

    tm = profiling.begin(design_dir, design_hash, key)      # None when disabled
    with profiling.stage("mesh_build"):                      # no-op when disabled
        mesh = build_mesh(...)
    profiling.record("solver_path", 0.0, assembly_path="fused_cuda")
    profiling.end(tm)                                        # appends the lines

The "current timer" lives in a ``ContextVar`` so a background prefetch thread (WP2) has its own
timer and never writes into the main thread's. Everything here is pure stdlib and offline.
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import os
import threading
import time
from pathlib import Path

ENV_FLAG = "HORNLAB_STAGE_TIMING"
FILE_NAME = "stage_timing.ndjson"

_CURRENT: contextvars.ContextVar = contextvars.ContextVar("hornlab_stage_timer", default=None)
_WRITE_LOCK = threading.Lock()


def enabled() -> bool:
    return str(os.environ.get(ENV_FLAG, "")).strip().lower() in ("1", "true", "yes", "on")


class StageTimer:
    """Collects stage records for one candidate and appends them as ndjson on ``flush``."""

    def __init__(self, directory, design_hash: str = "", key: str = "", clock=time.perf_counter):
        self.directory = None if directory is None else Path(directory)
        self.design_hash = str(design_hash)
        self.key = str(key)
        self._clock = clock
        self.rows: list[dict] = []

    def add(self, name: str, seconds: float, **meta) -> dict:
        row = {"stage": str(name), "seconds": float(seconds), "design_hash": self.design_hash,
               "key": self.key, "thread": threading.current_thread().name,
               "unix_time": time.time()}
        row.update(meta)
        self.rows.append(row)
        return row

    @contextlib.contextmanager
    def stage(self, name: str, **meta):
        t0 = self._clock()
        try:
            yield
        finally:
            self.add(name, self._clock() - t0, **meta)

    def summary(self) -> dict:
        """Total seconds per stage name (a stage that ran twice is summed)."""
        out: dict[str, float] = {}
        for r in self.rows:
            out[r["stage"]] = out.get(r["stage"], 0.0) + float(r["seconds"])
        return out

    def flush(self) -> Path | None:
        """Append the collected rows to ``<directory>/stage_timing.ndjson``; clears them."""
        if self.directory is None or not self.rows:
            self.rows = []
            return None
        path = self.directory / FILE_NAME
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with _WRITE_LOCK, open(path, "a", encoding="utf-8") as fh:
                for r in self.rows:
                    fh.write(json.dumps(r, default=str, sort_keys=True) + "\n")
        except OSError:                       # timing is bookkeeping; never fail a candidate
            return None
        finally:
            self.rows = []
        return path


def begin(directory, design_hash: str = "", key: str = "") -> StageTimer | None:
    """Start the current thread's timer, or return ``None`` (and set nothing) when disabled."""
    if not enabled():
        _CURRENT.set(None)
        return None
    timer = StageTimer(directory, design_hash, key)
    _CURRENT.set(timer)
    return timer


def end(timer: StageTimer | None) -> Path | None:
    """Flush ``timer`` (if any) and clear the current timer."""
    _CURRENT.set(None)
    return None if timer is None else timer.flush()


def current() -> StageTimer | None:
    return _CURRENT.get()


@contextlib.contextmanager
def stage(name: str, **meta):
    """Time a block against the current timer; a no-op when none is active."""
    timer = _CURRENT.get()
    if timer is None:
        yield
        return
    with timer.stage(name, **meta):
        yield


def record(name: str, seconds: float = 0.0, **meta) -> None:
    """Add a post-hoc row (e.g. the solver path read off a response) to the current timer."""
    timer = _CURRENT.get()
    if timer is not None:
        timer.add(name, seconds, **meta)


def solver_path_meta(resp) -> dict:
    """What the solver response says about how it ran: backend, device, fused flag, the
    per-frequency ``assembly_path`` set, solver timings. Safe on any object (never raises)."""
    out: dict = {}
    try:
        out["backend"] = getattr(resp, "backend", None)
        meta = getattr(resp, "meta", None) or {}
        out["device"] = meta.get("device")
        out["cuda_fused"] = meta.get("cuda_fused")
        out["per_frequency_calls"] = meta.get("per_frequency_calls")
        out["freq_batch_size"] = meta.get("freq_batch_size")
        out["n_dof"] = getattr(resp, "n_dof", None)
        out["vram_baseline_mib"] = meta.get("vram_baseline_mib")
        out["vram_peak_mib"] = meta.get("vram_peak_mib")
        diags = meta.get("native_diagnostics") or []
        paths = sorted({str(d.get("assembly_path")) for d in diags if isinstance(d, dict)
                        and d.get("assembly_path") is not None})
        out["assembly_paths"] = paths
        out["timings"] = meta.get("timings")
    except Exception:                         # noqa: BLE001 - diagnostics only
        pass
    return out
