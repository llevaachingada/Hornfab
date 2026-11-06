"""Opt-in mesh prefetch (throughput packet WP2): build candidate i+1's mesh while i solves.

Mechanism (deliberately small): a one-thread executor builds the mesh with the SAME
``build.build_mesh`` the evaluator uses, then parks the ``MeshResult`` in a process-local memo
keyed by ``build.prebuilt_key``. ``build.build_mesh`` consults the memo first and hands the parked
result back, so ``evaluate()`` is unchanged apart from that one lookup. The coordinator thread is
still the ONLY writer of ndjson / solve cache / dataset: the worker thread writes only the
candidate's own ``designs/<hash>/`` mesh files, and the coordinator waits for a candidate's build
(``wait``) before it evaluates that candidate, so one directory is never built twice at once.

With the memo empty (the default, ``pipeline_prefetch`` 0) ``take`` is a dict miss and nothing
else in the program changes.

Failure policy: any exception in the worker is swallowed (logged at debug) and nothing is parked;
``evaluate()`` then builds the mesh itself on the coordinator thread and reproduces the same
error/penalty deterministically. If the error says gmsh wants the main thread, the prefetcher
disables itself with one warning and the run continues serially.
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

log = logging.getLogger("hornlab_search.mesh.prefetch")

_PREBUILT: dict = {}
_LOCK = threading.Lock()


def put(key, result) -> None:
    with _LOCK:
        _PREBUILT[key] = result


def take(key):
    """Pop and return the parked ``MeshResult`` for ``key`` (None when nothing is parked)."""
    if not _PREBUILT:                       # lock-free fast path: the default (prefetch off)
        return None
    with _LOCK:
        return _PREBUILT.pop(key, None)


def clear() -> None:
    with _LOCK:
        _PREBUILT.clear()


def parked() -> int:
    with _LOCK:
        return len(_PREBUILT)


class MeshPrefetcher:
    """Bounded (``depth`` candidates ahead), single-worker background builder."""

    def __init__(self, depth: int):
        self.depth = max(0, int(depth))
        self.disabled = self.depth == 0
        self._pool = None if self.disabled else ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="hornlab-mesh-prefetch")
        self._pending: dict = {}
        self.submitted = 0
        self.waited_seconds = 0.0
        self.built = 0

    def pending(self) -> int:
        return len(self._pending)

    def submit(self, token, fn) -> bool:
        """Queue ``fn()`` (returns truthy when it parked a mesh) under ``token``. False when
        disabled, already queued, or the bounded queue is full."""
        if self.disabled or token in self._pending or len(self._pending) >= self.depth:
            return False
        self._pending[token] = self._pool.submit(self._run, fn)
        self.submitted += 1
        return True

    def _run(self, fn):
        try:
            ok = bool(fn())
            if ok:
                self.built += 1
            return ok
        except Exception as exc:  # noqa: BLE001 - the coordinator rebuilds; never poison a run
            log.debug("mesh prefetch failed (the evaluator will rebuild): %r", exc)
            if "main thread" in str(exc).lower() and not self.disabled:
                log.warning("mesh prefetch disabled: the mesher needs the main thread (%s); "
                            "continuing serially", exc)
                self.disabled = True
            return False

    def wait(self, token) -> None:
        """Block until ``token``'s build finished (no-op when it was never queued)."""
        fut: Future | None = self._pending.pop(token, None)
        if fut is None:
            return
        t0 = time.perf_counter()
        fut.result()
        self.waited_seconds += time.perf_counter() - t0

    def close(self) -> None:
        """Cancel what has not started, let a running build finish, drop parked meshes."""
        if self._pool is not None:
            self._pool.shutdown(wait=True, cancel_futures=True)
        self._pending.clear()
        clear()
