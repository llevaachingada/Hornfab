"""Active learning (ISMO) pieces, plan section 4. Pure selection and honest reporting; the BEM
solve of the proposals runs through the normal ``evaluate`` path on the GPU box."""
from __future__ import annotations

import numpy as np

from . import gates


def propose(sur, space, target, weights: dict, *, n_top: int = 30, n_var: int = 10,
            pop: int = 200, gens: int = 60, seed: int = 0) -> list[dict]:
    """Optimise the surrogate objective with NSGA-II (J plus the ensemble spread as a second,
    minimised-negatively objective would hide good designs, so J alone is the first column and
    -std the second), then return ``n_top`` best-predicted designs and ``n_var`` further designs
    with the highest ensemble variance among the final population. Each item:
    {design, kind: 'exploit'|'explore', pred_J, std}."""
    from ..search.nsga import nsga2

    k = len(space.keys())

    def f(U):
        p = sur.predict(U.astype(np.float32))
        return np.stack([sur.objective(p, target, weights), -p["std"]], 1)

    res = nsga2(f, k, pop=pop, gens=gens, seed=seed, init=space.normalize(space.seed)[None, :])
    X = res["X"]
    p = sur.predict(X.astype(np.float32))
    J, std = sur.objective(p, target, weights), p["std"]
    valid = p["p_ok"] >= 0.5
    order = [i for i in np.argsort(J, kind="stable") if valid[i]]
    seen, out = set(), []

    def add(i, kind):
        d = space.denormalize(X[i])
        h = d.hash()
        if h in seen:
            return False
        seen.add(h)
        out.append({"design": d, "kind": kind, "pred_J": float(J[i]), "std": float(std[i])})
        return True

    n = 0
    for i in order:
        if n >= n_top:
            break
        n += add(i, "exploit")
    n = 0
    for i in np.argsort(-std, kind="stable"):
        if n >= n_var:
            break
        if valid[i]:
            n += add(i, "explore")
    return out


def round_report(pred_J, true_J, random_true_J, *, n_top: int | None = None) -> dict:
    """Step 5 of the loop, which must appear in every report: how good were the BEM-solved
    proposals, and are they better than random designs? ``random_true_J`` are BEM objectives of
    random (non-surrogate) designs, e.g. the search's early evaluations. ``working`` is False
    unless the proposals' median beats the random median AND the rank correlation on the
    proposals is positive; if False, more iterations will not fix it."""
    pj, tj = np.asarray(pred_J, float), np.asarray(true_J, float)
    rj = np.asarray(random_true_J, float)
    rj = rj[np.isfinite(rj)]
    m = np.isfinite(tj)
    med_p = float(np.median(tj[m])) if m.any() else float("nan")
    med_r = float(np.median(rj)) if rj.size else float("nan")
    rho = gates.spearman(pj, tj)
    working = bool(np.isfinite(med_p) and np.isfinite(med_r) and med_p < med_r
                   and np.isfinite(rho) and rho > 0)
    return {"n": int(m.sum()), "n_solved_failed": int((~m).sum()), "median_true_J": med_p,
            "median_random_J": med_r, "spearman_on_proposals": rho, "working": working}
