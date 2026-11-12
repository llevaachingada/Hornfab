"""Opt-in candidate pipeline (throughput packet WP2): mesh i+1 while candidate i solves.

``pipeline_prefetch`` (config ``search.pipeline_prefetch`` or env ``HORNLAB_PIPELINE_PREFETCH``,
default 0) is how many candidates AHEAD of the one being evaluated get their mesh pre-built by a
single background worker (``mesh/prefetch.py``). With 0 the object is inert (``enabled`` False)
and the searchers run their original loops untouched.

What stays exactly as in the serial loop (the searchers still do all of this themselves):
  * candidates are evaluated one at a time, in ask order, by the coordinator thread (one GPU
    solve at a time; the GPU lock is untouched);
  * the coordinator is the only writer of search.ndjson / solve cache / dataset / best.json;
  * ``tell`` is called with F in the original ask order;
  * the seed is evaluated first, budget / cache-hit / failure / interrupt semantics are unchanged.
The only thing that moves earlier in time is candidate i+1's ``build_mesh`` call.
"""
from __future__ import annotations

import functools
import logging

from ..mesh.prefetch import MeshPrefetcher
from .evaluate import prefetch_candidate, prefetch_depth

log = logging.getLogger("hornlab_search.search.pipeline")


class CandidatePipeline:
    def __init__(self, cfg, mode: str, run_dir, ctx, depth: int | None = None, *,
                 prefetch_fn=None):
        self.depth = prefetch_depth(cfg) if depth is None else max(0, int(depth))
        self.enabled = self.depth > 0
        self._cfg, self._mode, self._run_dir, self._ctx = cfg, mode, run_dir, ctx
        self._fn = prefetch_fn or prefetch_candidate      # injectable for offline tests
        self._pf = MeshPrefetcher(self.depth)
        self._designs: list = []
        self._queued: set = set()

    def begin_generation(self, designs: list) -> None:
        self._designs = list(designs)
        self._queued = set()          # a duplicate design in one generation is built once

    def before(self, i: int) -> None:
        """Call right before evaluating candidate ``i`` of the current generation: wait for its
        own pre-build (so one directory is never built twice at once), then queue the next
        ``depth`` candidates so they build while ``i`` solves."""
        if not self.enabled or not self._designs:
            return
        self._pf.wait(self._designs[i].hash())
        for j in range(i + 1, min(len(self._designs), i + 1 + self.depth)):
            d = self._designs[j]
            if d.hash() in self._queued:
                continue
            if self._pf.submit(d.hash(), functools.partial(
                    self._fn, d, self._cfg, self._mode, self._run_dir, self._ctx)):
                self._queued.add(d.hash())

    def stats(self) -> dict:
        return {"depth": self.depth, "submitted": self._pf.submitted, "built": self._pf.built,
                "waited_seconds": round(self._pf.waited_seconds, 3),
                "disabled": bool(self._pf.disabled)}

    def close(self) -> None:
        if self.enabled:
            self._pf.close()
            log.info("pipeline prefetch: %s", self.stats())
