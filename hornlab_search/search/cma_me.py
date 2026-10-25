"""CMA-ME quality-diversity search (WP11b, ``search.algorithm: cma_me``).

CMA-ME (Fontaine 2020) runs a grid archive over a two-descriptor measure space; each emitter is a
CMA-ES instance whose ranking rewards *archive improvements* (new cells and better elites), so the
run fills a MAP of good designs instead of converging on one. This is a **search-only** feature:
the objective, the evaluator, the budget and the resume contract are exactly ``search.cma``'s.

Budget semantics (identical to ``search/cma.py``): ``budget`` caps NON-CACHED evaluations only (the
seed counts); a cache hit (in-run memo, resumed ndjson row, cross-run solve cache) does not consume
it. The budget is checked before every candidate, so a generation can be cut part-way; a partial
generation is NOT ``tell``-ed (a resume replays it from the cache and finishes it).

Resume is free and deterministic: the archive and the emitter are rebuilt from the same config and
seed, every replayed candidate is a cache hit, and the cached objective/measures are told back into
the scheduler in ask order. The archive therefore ends up byte-identical to an uninterrupted run's
— except ``solve_failed`` rows, which are never memoised (inherited from ``search/cma.py``) and
re-solve on a resume, so a run interrupted by a solver-unhealthy abort may legitimately diverge from
the uninterrupted replay.

ribs usage (installed 0.12.0, read-only; never edited):
- ``ribs.archives.GridArchive`` — ``threshold_min=-inf`` and ``learning_rate=1.0`` give CMA-ME's
  improvement values (``ribs/archives/_grid_archive.py``, ``add``: ``cur_threshold[is_new] = 0``
  and ``add_info["value"] = objective - cur_threshold``).
- ``ribs.emitters.EvolutionStrategyEmitter`` with ``ranker="2imp"``, ``es="cma_es"`` and
  ``selection_rule="mu"`` (``ribs/emitters/_evolution_strategy_emitter.py``): the canonical
  CMA-ME emitter (0.12.0 no longer ships ``CMAEvolutionEmitter``).
- ``ribs.schedulers.Scheduler``: strict ``ask``/``tell`` alternation in emitter order
  (``ribs/schedulers/_scheduler.py``). One emitter is used, so the batch is returned untouched.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from ..config import QD_DESCRIPTORS
from ..dataset.record import DEFAULT_TRACE_FRACTION
from ..design.space import DesignSpace
from ..mesh.build import MeshConsistencyError
from ..types import Evaluation
from . import rundir
from .cma import (MAX_CONSECUTIVE_SOLVE_FAILURES, SolverUnhealthyError, _detach, _prepare,
                  summarize, summarize_rows)
from .evaluate import error_kind, evaluate, read_ndjson

log = logging.getLogger("hornlab_search.search.cma_me")

#: A mean -6 dB beamwidth is an angle, so the archive's measure space is that physical interval in
#: both axes (the bins come from ``search.qd``). Fixed by descriptor UNITS, not by the data: an
#: archive whose ranges move with the run could not be compared or resumed reproducibly.
DESCRIPTOR_RANGE_DEG = (0.0, 180.0)

#: How many NEW evaluations may pass between archive.json / archive_heatmap.json refreshes. The
#: files are always rewritten at the end of a run, so this only bounds how stale a running run's
#: atlas may be.
ARCHIVE_REFRESH_EVALS = 25

#: descriptor name -> MetricSet field it averages over the in-band frequencies.
_DESCRIPTOR_FIELDS = {"mean_bw_h_deg": "bw_h_deg", "mean_bw_v_deg": "bw_v_deg"}


def _mean_in_band(values, freqs, lo: float, hi: float) -> float | None:
    """Mean of ``values`` at the in-band frequencies, ignoring non-finite samples. None when the
    band has no finite sample (a NaN-only metric must not become a descriptor coordinate)."""
    v = np.asarray(values, dtype=float)
    f = np.asarray(freqs, dtype=float)
    if v.shape != f.shape:
        return None
    mask = (f >= lo) & (f <= hi) & np.isfinite(v)
    if not mask.any():
        return None
    return float(v[mask].mean())


def descriptor_values(ev: Evaluation, cfg, names: tuple[str, str]) -> tuple[float, float] | None:
    """(descriptor_h, descriptor_v) for one evaluation, or None when it has no metrics / no
    finite in-band samples. Never raises."""
    metrics = ev.metrics
    if metrics is None:
        return None
    try:
        lo = float(cfg.target_raw["band_lo_hz"])
        hi = float(cfg.target_raw["band_hi_hz"])
    except (KeyError, TypeError, ValueError):
        return None
    out = []
    for name in names:
        field = _DESCRIPTOR_FIELDS.get(name)
        if field is None:
            return None
        value = _mean_in_band(getattr(metrics, field), metrics.freqs_hz, lo, hi)
        if value is None:
            return None
        out.append(value)
    return (float(out[0]), float(out[1]))


def _describe_descriptor(name: str) -> str:
    return f"{name} (mean of MetricSet.{_DESCRIPTOR_FIELDS[name]} over the in-band frequencies)"


def search(cfg, run_dir, mode="screen", resume=None, *, backend=None, budget: int | None = None,
           store=None, cache_dir=None, trace_fraction: float = DEFAULT_TRACE_FRACTION,
           command: str | None = None, config_path=None, lib_shas: dict | None = None,
           max_evals: int | None = None) -> Evaluation:
    """CMA-ME from the seed. Same argument surface and artifacts as ``search.cma.search``, plus
    ``archive.json`` / ``archive_heatmap.json`` and a ``qd`` block in run.json.

    ``budget`` caps NEW (non-cached) evaluations, exactly as in the single-ES path. Raises only for
    things that must stop a run (``MeshConsistencyError``, KeyboardInterrupt, an unusable backend,
    or the solver-unhealthy streak).
    """
    qd = getattr(cfg.search, "qd", None)
    if qd is None:
        raise ValueError("search.algorithm 'cma_me' needs search.qd (bins_h/bins_v have no default)")
    from ribs.archives import GridArchive
    from ribs.emitters import EvolutionStrategyEmitter
    from ribs.schedulers import Scheduler

    names = (str(qd["descriptor_h"]), str(qd["descriptor_v"]))
    for name in names:
        if name not in QD_DESCRIPTORS or name not in _DESCRIPTOR_FIELDS:
            raise ValueError(f"search.qd descriptor {name!r} is not supported by this build")
    bins = (int(qd["bins_h"]), int(qd["bins_v"]))

    run_dir = Path(resume if resume is not None else run_dir)
    run_dir, backend, ctx = _prepare(cfg, run_dir, mode, backend, store, cache_dir, trace_fraction,
                                     command, config_path, lib_shas)
    max_new = int(budget if budget is not None else cfg.search.budget)
    space = DesignSpace.from_config(cfg)
    x0 = space.normalize(space.seed)
    solution_dim = int(len(x0))

    archive = GridArchive(solution_dim=solution_dim, dims=list(bins),
                          ranges=[DESCRIPTOR_RANGE_DEG, DESCRIPTOR_RANGE_DEG],
                          seed=int(cfg.search.seed))
    emitter = EvolutionStrategyEmitter(
        archive, x0=np.asarray(x0, dtype=float), sigma0=float(cfg.search.sigma0),
        ranker="2imp", es="cma_es", selection_rule="mu",
        bounds=[(0.0, 1.0)] * solution_dim,
        batch_size=int(cfg.search.popsize) if cfg.search.popsize else None,
        seed=int(cfg.search.seed))
    scheduler = Scheduler(archive, [emitter])

    evals: list[Evaluation] = []
    wall: list[float] = []
    state = {"best": None, "best_no": None, "seed_ev": None, "n_new": 0, "stop": "",
             "solve_fail_streak": 0}
    hash_by_solution: dict[tuple, str] = {}
    seed_measures: np.ndarray | None = None
    rows0 = read_ndjson(run_dir / "search.ndjson")
    written_at = 0

    # On a resume the best so far is already on disk in search.ndjson: start from it, so a short
    # (or zero-budget) resume can never overwrite best.json with something worse.
    prior = [e for e in ctx.known.values() if not e.error]
    if prior:
        b0 = min(prior, key=lambda e: e.objective)
        state["best"] = b0
        state["best_no"] = next((r.get("n") for r in rows0
                                 if r.get("design_hash") == b0.design_hash), None)
        rundir.write_best(run_dir, b0, mode, state["best_no"])

    def run_one(design) -> Evaluation:
        t0 = time.perf_counter()
        ev = evaluate(design, space, cfg, mode, run_dir, store, backend, ctx=ctx)
        dt = time.perf_counter() - t0
        evals.append(ev)
        if not ev.cached:
            state["n_new"] += 1
            wall.append(dt)
        b = state["best"]
        if b is None or ev.objective < b.objective or (b.error and not ev.error):
            state["best"], state["best_no"] = ev, len(evals) - 1
            rundir.write_best(run_dir, ev, mode, state["best_no"])
        if not ev.cached and error_kind(ev.error) == "solve_failed":
            state["solve_fail_streak"] += 1
            if state["solve_fail_streak"] >= MAX_CONSECUTIVE_SOLVE_FAILURES:
                raise SolverUnhealthyError(
                    f"{state['solve_fail_streak']} consecutive solve_failed evaluations (last: "
                    f"{ev.error.splitlines()[0][:200]}); the solver is unhealthy, not the designs. "
                    f"Clear hosts (gpu-clean) and continue with --resume")
        elif not ev.cached:
            state["solve_fail_streak"] = 0
        return ev

    def archive_payload() -> dict:
        """The pinned ``archive.json`` payload: occupied cells only, sorted by (bin_h, bin_v).

        Cells carry the MINIMISATION objective (``objective`` = -archive objective, i.e. the same J
        as best.json) and the ndjson row number (``eval_no``) of the design that owns the cell. The
        stats are cumulative over every resume (they are read back from search.ndjson); the archive
        itself is rebuilt deterministically by replaying the same tells, so a resumed run ends with
        the same cells / ranges as an uninterrupted one."""
        eval_no = {}
        rows = read_ndjson(run_dir / "search.ndjson")
        for r in rows:
            eval_no.setdefault(str(r.get("design_hash")), r.get("n"))
        cells: list[dict] = []
        bounds = archive.boundaries
        data = archive.data()
        ints = np.asarray(data.get("index", []), dtype=np.int64)
        if ints.size:
            grid = archive.int_to_grid_index(ints)
            objs = np.asarray(data["objective"], dtype=float)
            sols = np.asarray(data["solution"], dtype=float)
            for k in range(len(ints)):
                i, j = int(grid[k][0]), int(grid[k][1])
                key = tuple(float(v) for v in sols[k])
                dh = hash_by_solution.get(key)
                if dh is None:
                    dh = space.denormalize(sols[k]).hash()
                cells.append({
                    "bin": [i, j],
                    "center": [
                        float(bounds[0][i] + 0.5 * (bounds[0][i + 1] - bounds[0][i])),
                        float(bounds[1][j] + 0.5 * (bounds[1][j + 1] - bounds[1][j])),
                    ],
                    "objective": float(-objs[k]),
                    "design_hash": dh,
                    "eval_no": eval_no.get(dh),
                })
        cells.sort(key=lambda c: (c["bin"][0], c["bin"][1]))
        total_bins = int(archive.cells)
        occupied = int(len(cells))
        non_cached = sum(1 for r in rows if not r.get("cached"))
        return {
            "algorithm": "cma_me",
            "descriptors": {"h": names[0], "v": names[1]},
            "bins": [bins[0], bins[1]],
            "ranges": {"h": list(DESCRIPTOR_RANGE_DEG), "v": list(DESCRIPTOR_RANGE_DEG)},
            "cells": cells,
            "stats": {
                "total_bins": total_bins,
                "occupied_bins": occupied,
                "coverage": (occupied / float(total_bins)) if total_bins else 0.0,
                "total_evals": len(rows),
                "non_cached": non_cached,
            },
        }

    def write_archive() -> dict:
        payload = archive_payload()
        rundir.write_json_atomic(run_dir / "archive.json", payload)
        # GUI contract: archive_heatmap.json is the ONLY file the read-only atlas consumes, and its
        # schema is exactly {"bins", "ranges", "descriptors": {"h", "v"}, "cells": [{h_center,
        # v_center, objective, design_hash}]} (occupied cells only). The descriptors are the same
        # names archive.json carries, so the atlas labels its axes without parsing the full record.
        heat = {
            "bins": payload["bins"],
            "ranges": payload["ranges"],
            "descriptors": payload["descriptors"],
            "cells": [{"h_center": c["center"][0], "v_center": c["center"][1],
                       "objective": c["objective"], "design_hash": c["design_hash"]}
                      for c in payload["cells"]],
        }
        rundir.write_json_atomic(run_dir / "archive_heatmap.json", heat)
        return payload

    def finish(status: str) -> None:
        payload = write_archive()
        last = summarize(evals, wall)
        stats = summarize_rows(read_ndjson(run_dir / "search.ndjson")) \
            if (run_dir / "search.ndjson").exists() else last
        seed_ev = state["seed_ev"]
        best = state["best"]
        upd = {"status": status, "finished_utc": rundir.utc_now(), "stop_reason": state["stop"],
               "stats": stats, "last_invocation": last, "budget": max_new}
        if seed_ev is not None:
            upd["seed"] = {"design_hash": seed_ev.design_hash, "objective": seed_ev.objective,
                           "terms": seed_ev.terms}
        if best is not None:
            upd["best"] = {"design_hash": best.design_hash, "objective": best.objective,
                           "eval_no": state["best_no"]}
        # Present ONLY for cma_me runs; a plain cma run.json keeps exactly today's schema.
        upd["qd"] = {"algorithm": "cma_me", "descriptors": payload["descriptors"],
                     "bins": payload["bins"], "ranges": payload["ranges"],
                     "total_bins": payload["stats"]["total_bins"],
                     "occupied_bins": payload["stats"]["occupied_bins"],
                     "coverage": payload["stats"]["coverage"],
                     "total_evals": payload["stats"]["total_evals"],
                     "non_cached": payload["stats"]["non_cached"],
                     "descriptor_h_meaning": _describe_descriptor(names[0]),
                     "descriptor_v_meaning": _describe_descriptor(names[1])}
        rundir.update_run_json(run_dir, **upd)
        log.info("CMA-ME %s: %d evaluations (%d new, %d cached), archive %d/%d cells "
                 "(%.1f%% coverage), best J=%.4f, %d failures %s",
                 status, stats["evaluations"], stats["non_cached"], stats["cache_hits"],
                 payload["stats"]["occupied_bins"], payload["stats"]["total_bins"],
                 100.0 * payload["stats"]["coverage"],
                 float("nan") if best is None else best.objective,
                 stats["failures"], stats["failures_by_reason"])

    def clip01(x) -> np.ndarray:
        return np.clip(np.asarray(x, dtype=float).reshape(-1), 0.0, 1.0)

    def tell_batch(X, evs) -> None:
        """Feed a full ask() batch back to the scheduler. Failed evaluations still go to the
        emitter (mirroring cma.py, which scores them with the penalty J) but their descriptor is
        unknown, so they reuse the seed's coordinates and a penalty objective: they can never
        replace a real elite. If even the seed produced no metrics the archive stays empty and the
        fallback is the corner (0, 0); every such row is counted as a failure above."""
        objective = np.asarray([-float(ev.objective) for ev in evs], dtype=float)
        fallback = seed_measures if seed_measures is not None else np.zeros(2, dtype=float)
        measures = []
        for ev, x in zip(evs, X):
            vals = descriptor_values(ev, cfg, names)
            measures.append(np.asarray(vals if vals is not None else fallback, dtype=float))
            hash_by_solution[tuple(float(v) for v in x)] = ev.design_hash
        scheduler.tell(objective=objective, measures=np.asarray(measures, dtype=float))

    try:
        # 1. the seed first: every later number is meaningless without the baseline it must beat.
        seed_ev = run_one(space.seed)
        state["seed_ev"] = seed_ev
        seed_desc = descriptor_values(seed_ev, cfg, names)
        if seed_desc is not None:
            seed_measures = np.asarray(seed_desc, dtype=float)
            hash_by_solution[tuple(float(v) for v in x0)] = seed_ev.design_hash
            archive.add(solution=np.asarray(x0, dtype=float)[None], objective=np.asarray(
                [-float(seed_ev.objective)]), measures=seed_measures[None])
        log.info("seed J=%.4f terms=%s descriptors=%s", seed_ev.objective,
                 {k: round(v, 4) for k, v in seed_ev.terms.items()},
                 None if seed_desc is None else tuple(round(v, 2) for v in seed_desc))
        cap = int(max_evals) if max_evals else None

        def exhausted() -> bool:
            return state["n_new"] >= max_new or (cap is not None and len(evals) >= cap)

        def maybe_refresh() -> None:
            nonlocal written_at
            if state["n_new"] - written_at >= ARCHIVE_REFRESH_EVALS:
                write_archive()
                written_at = state["n_new"]

        generation = 0
        while not exhausted():
            X = scheduler.ask()
            if len(X) == 0:                       # a degenerate emitter: never spin forever
                state["stop"] = "cma_me: no solutions"
                break
            batch_evs = []
            cut = False
            for x in X:
                if exhausted():
                    cut = True
                    break
                x = clip01(x)
                batch_evs.append(run_one(space.denormalize(x)))
            if cut:                               # budget ran out mid-generation: do not tell
                state["stop"] = "budget"
                break
            tell_batch(X, batch_evs)
            generation += 1
            maybe_refresh()
            log.info("CMA-ME generation %d: %d solutions, archive %d/%d cells, best overall %.4f "
                     "(%d new evaluations)", generation, len(X), len(archive), int(archive.cells),
                     state["best"].objective, state["n_new"])
        if not state["stop"]:
            state["stop"] = "budget"
        finish("finished")
    except KeyboardInterrupt:
        state["stop"] = "interrupted"
        finish("interrupted")
        raise
    except (MeshConsistencyError, SolverUnhealthyError) as exc:
        state["stop"] = f"aborted: {type(exc).__name__}: {exc}"
        finish("aborted")
        raise
    finally:
        _detach(backend)
    return state["best"]
