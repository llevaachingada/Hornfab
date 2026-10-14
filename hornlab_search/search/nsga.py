"""Multi-objective search (NSGA-II). Phase 2.

NSGA-II needs roughly 100 individuals x 100 generations = 10,000 evaluations. Against real BEM
that is ~11 h; it becomes the right algorithm once an evaluator can score a whole population in
one batched forward pass (``surrogate.predict``). See 11_PHASE2_SURROGATE.md.

``nsga2`` is a plain numpy NSGA-II on the unit cube (minimisation). ``search_pareto`` wires it to
the design space: the evaluator is an argument, so a surrogate swaps in without touching this code.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

import numpy as np

from ..objective.terms import PENALTY_FAILED
from ..types import Evaluation

DEFAULT_OBJECTIVES = ("cov", "rip", "flat")


def _finite_or_penalty(F: np.ndarray) -> np.ndarray:
    """Replace any non-finite objective with ``PENALTY_FAILED``. A NaN compares False to
    everything, so ``NaN <= x`` and ``NaN < x`` are both False and a broken row would look
    NON-DOMINATED (rank 0). The penalty makes it dominated instead."""
    F = np.asarray(F, float)
    bad = ~np.isfinite(F)
    if bad.any():
        F = F.copy()
        F[bad] = PENALTY_FAILED
    return F


def fast_nondominated_sort(F: np.ndarray) -> list[np.ndarray]:
    """Fronts (index arrays), best first. F: (n, m), minimised."""
    n = F.shape[0]
    dom = (F[:, None, :] <= F[None, :, :]).all(-1) & (F[:, None, :] < F[None, :, :]).any(-1)
    n_dom_by = dom.sum(0)              # how many dominate i
    fronts, cur = [], np.flatnonzero(n_dom_by == 0)
    counts = n_dom_by.copy()
    while cur.size:
        fronts.append(cur)
        counts = counts - dom[cur].sum(0)
        counts[cur] = -1
        cur = np.flatnonzero(counts == 0)
    assert sum(len(f) for f in fronts) == n
    return fronts


def crowding_distance(F: np.ndarray) -> np.ndarray:
    n, m = F.shape
    d = np.zeros(n)
    if n <= 2:
        d[:] = np.inf
        return d
    for j in range(m):
        o = np.argsort(F[:, j], kind="stable")
        span = F[o[-1], j] - F[o[0], j]
        d[o[0]] = d[o[-1]] = np.inf
        if span > 0:
            d[o[1:-1]] += (F[o[2:], j] - F[o[:-2], j]) / span
    return d


def _rank_and_crowd(F: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rank = np.empty(len(F), int)
    crowd = np.empty(len(F))
    for r, fr in enumerate(fast_nondominated_sort(F)):
        rank[fr] = r
        crowd[fr] = crowding_distance(F[fr])
    return rank, crowd


def _variation(P, rank, crowd, rng, eta_c=15.0, eta_m=20.0, p_c=0.9):
    n, k = P.shape
    a, b = rng.integers(n, size=(2, n)), rng.integers(n, size=(2, n))
    def pick(i, j):
        return np.where((rank[i] < rank[j]) | ((rank[i] == rank[j]) & (crowd[i] >= crowd[j])), i, j)
    p1, p2 = P[pick(a[0], a[1])], P[pick(b[0], b[1])]
    u = rng.random((n, k))
    beta = np.where(u <= 0.5, (2 * u) ** (1 / (eta_c + 1)), (1 / (2 * (1 - u))) ** (1 / (eta_c + 1)))
    c = 0.5 * ((1 + beta) * p1 + (1 - beta) * p2)
    do = rng.random((n, 1)) < p_c
    c = np.where(do, c, p1)
    mut = rng.random((n, k)) < 1.0 / k
    u = rng.random((n, k))
    delta = np.where(u < 0.5, (2 * u) ** (1 / (eta_m + 1)) - 1, 1 - (2 * (1 - u)) ** (1 / (eta_m + 1)))
    return np.clip(c + mut * delta, 0.0, 1.0)


def nsga2(f: Callable[[np.ndarray], np.ndarray], n_dim: int, pop: int = 100, gens: int = 100,
          seed: int = 0, init: np.ndarray | None = None) -> dict:
    """Minimise ``f((n, n_dim)) -> (n, m)`` on [0,1]^n_dim. ``init`` rows seed the population.
    Returns {'X','F' (final population), 'front' (indices of rank 0), 'n_evals'}."""
    rng = np.random.default_rng(seed)
    P = rng.random((pop, n_dim))
    if init is not None and len(init):
        init = np.clip(np.atleast_2d(init), 0, 1)[:pop]
        P[:len(init)] = init
    F = _finite_or_penalty(np.asarray(f(P), float))
    n_evals = pop
    for _ in range(gens):
        rank, crowd = _rank_and_crowd(F)
        Q = _variation(P, rank, crowd, rng)
        FQ = _finite_or_penalty(np.asarray(f(Q), float))
        n_evals += len(Q)
        R, FR = np.vstack([P, Q]), np.vstack([F, FQ])
        keep = []
        for fr in fast_nondominated_sort(FR):
            if len(keep) + len(fr) <= pop:
                keep.extend(fr.tolist())
            else:
                cd = crowding_distance(FR[fr])
                keep.extend(fr[np.argsort(-cd, kind="stable")[:pop - len(keep)]].tolist())
                break
        P, F = R[keep], FR[keep]
    front = fast_nondominated_sort(F)[0]
    return {"X": P, "F": F, "front": front, "n_evals": n_evals}


def search_pareto(cfg, run_dir, evaluator, *, objectives=DEFAULT_OBJECTIVES, pop: int = 100,
                  gens: int = 100, seed: int | None = None) -> list[Evaluation]:
    """NSGA-II over the design space. ``evaluator(list[Design]) -> list[Evaluation]`` (batched);
    the objective vector is the RAW ``Evaluation.terms[k]`` for k in ``objectives`` (failed
    candidates carry the penalty in every component). Returns the Pareto-front Evaluations and
    writes ``<run_dir>/pareto.json``. Nothing here knows whether the evaluator is BEM or a
    surrogate; a surrogate front MUST be re-solved with real BEM before it is believed."""
    from ..design.space import DesignSpace

    space = DesignSpace.from_config(cfg)
    k = len(space.keys())

    def f(U: np.ndarray) -> np.ndarray:
        evs = evaluator([space.denormalize(u) for u in U])
        assert len(evs) == len(U), "evaluator must return one Evaluation per design"
        out = np.empty((len(U), len(objectives)))
        for i, e in enumerate(evs):
            bad = e.metrics is None or e.objective >= PENALTY_FAILED
            for j, name in enumerate(objectives):
                out[i, j] = e.objective if bad else float(e.terms[name])
        return out

    if seed is None:
        seed = int(getattr(getattr(cfg, "search", None), "seed", 0) or 0)
    res = nsga2(f, k, pop=pop, gens=gens, seed=seed, init=space.normalize(space.seed)[None, :])
    # Re-evaluate the final front designs once so the returned Evaluations match res['X'].
    designs = [space.denormalize(res["X"][i]) for i in res["front"]]
    front = list(evaluator(designs))
    out_dir = Path(run_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps({
        "objectives": list(objectives), "n_evals": res["n_evals"], "pop": pop, "gens": gens,
        "seed": seed, "keys": space.keys(),
        "front": [{"design": e.design.params, "family": e.design.family,
                   "design_hash": e.design_hash, "objective": e.objective,
                   "terms": {n: float(e.terms.get(n, float("nan"))) for n in objectives}}
                  for e in front],
    }, indent=1, default=float)
    tmp = out_dir / "pareto.json.tmp"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, out_dir / "pareto.json")
    return front
