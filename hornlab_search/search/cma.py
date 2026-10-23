"""CMA-ES search (01_CONTRACTS section 12, 08_TASK_PIPELINE section 4).

Unit box [0,1]^k, x0 = normalized seed, sigma0 from the config, seed from the config. Bounds are
clipped inside ``DesignSpace.denormalize``, not by CMA penalties.

Budget semantics: ``budget`` caps NON-CACHED evaluations only (the seed counts); a cache hit
(in-run memo, resumed ndjson row, cross-run solve cache) does not consume it. The cma
``maxfevals`` option is deliberately NOT used, because it counts cached replays too. The budget is
checked before every candidate, so a run can stop part-way through a generation; the partial
generation is not ``tell``-ed (a resume replays it from the cache and finishes it).

Resume is free: the same config and seed regenerate the same candidates, every one already in
``search.ndjson`` is a cache hit, so a re-run performs zero solves for work already done and then
carries on exactly where the uninterrupted run would have been.
"""
from __future__ import annotations

import logging
import math
import os
import time
from collections import Counter
from pathlib import Path

import cma as cma_lib
import numpy as np

from ..dataset.record import DEFAULT_TRACE_FRACTION
from ..design.space import DesignSpace
from ..mesh.build import MeshConsistencyError
from ..metrics import compute as metrics_compute
from ..solve import worker
from ..targets.spec import Target
from ..types import Evaluation
from . import rundir
from .evaluate import (collect_lib_shas, error_kind, evaluate, make_context, read_ndjson)

log = logging.getLogger("hornlab_search.search.cma")

EVALS_PER_PROJECTION = (1000, 10000)

# Consecutive non-cached ``solve_failed`` evaluations (each already retried once by the backend
# after a worker-host recovery) that stop a search. A string of solver failures says the solver
# is unhealthy, not that the designs are bad: scoring them as 1000-penalties flattens the landscape
# and CMA-ES then ends on ``tolflatfitness`` (OSSE seed 4101, 2026-10-23). Stopping instead keeps
# the run resumable: ``solve_failed`` rows are never memoised, so ``--resume`` re-solves them.
MAX_CONSECUTIVE_SOLVE_FAILURES = 3


class SolverUnhealthyError(RuntimeError):
    """Too many consecutive solver failures; the run stops (resumable) instead of scoring them."""


def summarize(evals: list[Evaluation], wall_seconds: list[float]) -> dict:
    """The honest answer to "how fast is this": counts, failures by reason, GPU seconds, mean
    seconds per candidate, candidates per hour, projected hours for 1,000 and 10,000."""
    new = [e for e in evals if not e.cached]
    fails = Counter(error_kind(e.error) for e in new if e.error)
    solve_s = sum(float(e.outcome.seconds) for e in new if e.outcome is not None)
    mesh_s = sum(float(e.mesh.seconds) for e in new if e.mesh is not None)
    mean_s = (sum(wall_seconds) / len(wall_seconds)) if wall_seconds else float("nan")
    cph = 3600.0 / mean_s if mean_s and math.isfinite(mean_s) and mean_s > 0 else float("nan")
    return {
        "evaluations": len(evals), "non_cached": len(new), "cache_hits": len(evals) - len(new),
        "failures_by_reason": dict(fails), "failures": int(sum(fails.values())),
        "total_gpu_seconds": solve_s, "total_mesh_seconds": mesh_s,
        "mean_seconds_per_candidate": mean_s, "candidates_per_hour": cph,
        "projected_hours": {str(n): (n / cph if math.isfinite(cph) and cph > 0 else float("nan"))
                            for n in EVALS_PER_PROJECTION},
    }


def summarize_rows(rows: list[dict]) -> dict:
    """The same summary computed from search.ndjson rows, i.e. cumulative over every resume of a
    run directory (``summarize`` only sees the current invocation)."""
    new = [r for r in rows if not r.get("cached")]
    fails = Counter(r.get("kind") or error_kind(r.get("error", "")) for r in rows if not r.get("ok"))
    sec = lambda r, k: float((r.get("seconds") or {}).get(k) or 0.0)       # noqa: E731
    tot = [sec(r, "total") for r in new]
    mean_s = (sum(tot) / len(tot)) if tot else float("nan")
    cph = 3600.0 / mean_s if tot and mean_s > 0 else float("nan")
    return {
        "evaluations": len(rows), "non_cached": len(new), "cache_hits": len(rows) - len(new),
        "failures_by_reason": dict(fails), "failures": int(sum(fails.values())),
        "total_gpu_seconds": sum(sec(r, "solve") for r in new),
        "total_mesh_seconds": sum(sec(r, "mesh") for r in new),
        "mean_seconds_per_candidate": mean_s, "candidates_per_hour": cph,
        "projected_hours": {str(n): (n / cph if math.isfinite(cph) and cph > 0 else float("nan"))
                            for n in EVALS_PER_PROJECTION},
    }


def _prepare(cfg, run_dir: Path, mode: str, backend, store, cache_dir, trace_fraction, command,
             config_path, lib_shas):
    """Shared setup of ``search`` and ``run_once``: directories, backend, warm worker, context."""
    run_dir = Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_compute.reset_warning_state()
    if backend is None:
        from ..solve.base import get_backend
        backend = get_backend(cfg.solve.backend, timeout_s=float(cfg.solve.timeout_s))
    worker.warm(backend)                       # once, before the seed; idempotent
    lib_shas = lib_shas or collect_lib_shas()
    ctx = make_context(cfg, store, cache_dir=cache_dir, lib_shas=lib_shas,
                       trace_fraction=trace_fraction, ndjson=run_dir / "search.ndjson")
    first = rundir.read_json(run_dir / "run.json") is None
    rundir.write_config_snapshot(run_dir, cfg)
    base = {"run_id": run_dir.name, "config_name": cfg.name, "family": cfg.family, "mode": mode,
            "config_path": None if config_path is None else str(config_path),
            "config": cfg.raw, "config_sha": rundir.config_sha(cfg.raw),
            "backend": cfg.solve.backend, "lib_shas": lib_shas,
            "toolchain": rundir.toolchain_snapshot(),
            "runtime": rundir.runtime_provenance(),
            "cma_seed": cfg.search.seed, "trace_fraction": trace_fraction,
            "command": command, "status": "running", "started_utc": rundir.utc_now(),
            "dataset_dir": None if store is None else str(store.root)}
    if first:
        base["created_utc"] = base["started_utc"]
        rundir.write_json_atomic(run_dir / "run.json", base)
    else:
        prev = rundir.read_json(run_dir / "run.json", {}) or {}
        resumes = list(prev.get("resumes", [])) + [base["started_utc"]]
        base.pop("started_utc")
        base["resumes"] = resumes
        rundir.update_run_json(run_dir, **base)
    return run_dir, backend, ctx


def _detach(backend) -> None:
    if str(getattr(backend, "name", "")).startswith("beat"):
        worker.detach()                        # leaves the host warm for the next run


def search(cfg, run_dir, mode="screen", resume=None, *, backend=None, budget: int | None = None,
           store=None, cache_dir=None, trace_fraction: float = DEFAULT_TRACE_FRACTION,
           command: str | None = None, config_path=None, lib_shas: dict | None = None,
           max_evals: int | None = None) -> Evaluation:
    """CMA-ES from the seed. Returns the best Evaluation. Writes into ``run_dir`` (or ``resume``,
    an existing run directory to continue): run.json, search.ndjson, best.json, designs/, cma/.

    ``budget`` caps NEW (non-cached) evaluations. ``max_evals`` additionally caps ALL evaluations
    of this invocation, cached ones included: a campaign comparison must give every family the
    same amount of search, and a replayed CMA seed would otherwise get its cached prefix for free.

    Raises only for things that must stop a run: a mesh units/symmetry bug
    (``MeshConsistencyError``), KeyboardInterrupt, an unusable backend.
    """
    if cfg.search.algorithm != "cma":
        raise ValueError(f"search.algorithm {cfg.search.algorithm!r} is not implemented in phase 1 (cma)")
    run_dir = Path(resume if resume is not None else run_dir)
    run_dir, backend, ctx = _prepare(cfg, run_dir, mode, backend, store, cache_dir, trace_fraction,
                                     command, config_path, lib_shas)
    max_new = int(budget if budget is not None else cfg.search.budget)
    space = DesignSpace.from_config(cfg)
    x0 = space.normalize(space.seed)
    (run_dir / "cma").mkdir(exist_ok=True)
    opts = {"bounds": [0.0, 1.0], "seed": int(cfg.search.seed), "tolfun": float(cfg.search.tolfun),
            "verb_filenameprefix": str(run_dir / "cma") + os.sep, "verb_disp": 0, "verbose": -1}
    if cfg.search.popsize:
        opts["popsize"] = int(cfg.search.popsize)
    es = cma_lib.CMAEvolutionStrategy(list(map(float, x0)), float(cfg.search.sigma0), opts)

    evals: list[Evaluation] = []
    wall: list[float] = []
    state = {"best": None, "best_no": None, "seed_ev": None, "n_new": 0, "stop": "",
             "solve_fail_streak": 0}

    # On a resume the best so far is already on disk in search.ndjson: start from it, so a short
    # (or zero-budget) resume can never overwrite best.json with something worse.
    prior = [e for e in ctx.known.values() if not e.error]
    if prior:
        b0 = min(prior, key=lambda e: e.objective)
        rows0 = read_ndjson(run_dir / "search.ndjson")
        state["best"] = b0
        state["best_no"] = next((r.get("n") for r in rows0 if r.get("design_hash") == b0.design_hash), None)
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
            rundir.write_best(run_dir, ev, mode, state["best_no"])      # after EVERY improvement
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

    def finish(status: str) -> None:
        last = summarize(evals, wall)
        # run.json["stats"] is CUMULATIVE over every resume (from the ndjson); the numbers of this
        # invocation alone are kept under "last_invocation" (cache hits there include resume replays).
        stats = summarize_rows(read_ndjson(run_dir / "search.ndjson")) if (run_dir / "search.ndjson").exists() else last
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
        rundir.update_run_json(run_dir, **upd)
        log.info("search %s: %d evaluations (%d new, %d cached), %d failures %s, GPU %.1f s, "
                 "%.1f s/candidate, %.0f candidates/h, 1k evals = %.1f h, 10k = %.1f h",
                 status, stats["evaluations"], stats["non_cached"], stats["cache_hits"],
                 stats["failures"], stats["failures_by_reason"], stats["total_gpu_seconds"],
                 stats["mean_seconds_per_candidate"], stats["candidates_per_hour"],
                 stats["projected_hours"]["1000"], stats["projected_hours"]["10000"])

    try:
        # 1. the seed first: every later number is meaningless without the baseline it must beat
        seed_ev = run_one(space.seed)
        state["seed_ev"] = seed_ev
        log.info("seed J=%.4f terms=%s", seed_ev.objective,
                 {k: round(v, 4) for k, v in seed_ev.terms.items()})
        gen = 0
        cap = int(max_evals) if max_evals else None

        def exhausted() -> bool:
            return state["n_new"] >= max_new or (cap is not None and len(evals) >= cap)

        while not exhausted():
            stop = es.stop()
            if stop:
                state["stop"] = "cma: " + ", ".join(sorted(stop))
                break
            X = es.ask()
            F = []
            for x in X:
                if exhausted():
                    break
                F.append(run_one(space.denormalize(np.asarray(x))).objective)
            if len(F) < len(X):               # budget ran out mid-generation: do not tell
                state["stop"] = "budget"
                break
            es.tell(X, F)
            try:
                es.logger.add()
            except Exception:  # noqa: BLE001 - cma's own logging is optional
                pass
            gen += 1
            log.info("generation %d: best this generation %.4f, best overall %.4f (%d new evaluations)",
                     gen, min(F), state["best"].objective, state["n_new"])
        else:
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


def run_once(cfg, run_dir, mode="screen", *, backend=None, store=None, cache_dir=None,
             trace_fraction: float = DEFAULT_TRACE_FRACTION, command: str | None = None,
             config_path=None, lib_shas: dict | None = None) -> Evaluation:
    """Evaluate the seed design once (``hornlab-search run``): the same machinery as a search
    with a budget of one, without the optimizer."""
    run_dir, backend, ctx = _prepare(cfg, Path(run_dir), mode, backend, store, cache_dir,
                                     trace_fraction, command, config_path, lib_shas)
    space = DesignSpace.from_config(cfg)
    t0 = time.perf_counter()
    try:
        ev = evaluate(space.seed, space, cfg, mode, run_dir, store, backend, ctx=ctx)
        rundir.write_best(run_dir, ev, mode, 0)
        wall = [] if ev.cached else [time.perf_counter() - t0]
        stats = summarize([ev], wall)
        rundir.update_run_json(run_dir, status="finished", finished_utc=rundir.utc_now(), stats=stats,
                               last_invocation=stats,
                               seed={"design_hash": ev.design_hash, "objective": ev.objective,
                                     "terms": ev.terms},
                               best={"design_hash": ev.design_hash, "objective": ev.objective,
                                     "eval_no": 0})
    except MeshConsistencyError as exc:
        rundir.update_run_json(run_dir, status="aborted", stop_reason=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        _detach(backend)
    return ev
