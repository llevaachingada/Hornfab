"""Acceptance gates for a metric surrogate (11_PHASE2_SURROGATE section 4). Pure numpy/scipy.

Rank correlation, not RMSE: a search needs to know which candidate is better. A surrogate that
fails its rank gate is NOT used (the report says so; more data or a better encoding is the fix).
"""
from __future__ import annotations

from typing import Callable

import numpy as np
from scipy import stats

# Thresholds are frozen by the plan; evaluate_gates() reports them next to the measured values.
GATE_SPEARMAN = 0.90
GATE_TOPK = 12            # of TOPK_N
TOPK_N = 20
GATE_BW_MAE_DEG = 2.0
GATE_DI_MAE_DB = 0.3
GATE_INVALID_ACC = 0.85
GATE_SWEEPS = 50
MIN_HELDOUT = 500         # the plan requires >= 500 BEM-solved held-out designs


def spearman(pred, true) -> float:
    """Spearman rank correlation over finite pairs; nan if fewer than 3."""
    p, t = np.asarray(pred, float), np.asarray(true, float)
    m = np.isfinite(p) & np.isfinite(t)
    if m.sum() < 3 or np.ptp(p[m]) == 0 or np.ptp(t[m]) == 0:
        return float("nan")
    return float(stats.spearmanr(p[m], t[m])[0])


def topk_overlap(pred, true, k: int = TOPK_N) -> int:
    """How many of the true best-k (lowest) objective values are in the surrogate's best-k."""
    p, t = np.asarray(pred, float), np.asarray(true, float)
    m = np.isfinite(p) & np.isfinite(t)
    idx = np.flatnonzero(m)
    k = min(k, idx.size)
    if k == 0:
        return 0
    bp = set(idx[np.argsort(p[idx], kind="stable")[:k]])
    bt = set(idx[np.argsort(t[idx], kind="stable")[:k]])
    return len(bp & bt)


def mae(pred, true) -> float:
    p, t = np.asarray(pred, float), np.asarray(true, float)
    m = np.isfinite(p) & np.isfinite(t)
    return float(np.mean(np.abs(p[m] - t[m]))) if m.any() else float("nan")


def invalid_accuracy(p_ok, ok_true, threshold: float = 0.5) -> float:
    """Fraction of truly-invalid designs the surrogate predicts invalid (p_ok < threshold)."""
    p, ok = np.asarray(p_ok, float), np.asarray(ok_true, bool)
    bad = ~ok
    if not bad.any():
        return float("nan")
    return float(np.mean(p[bad] < threshold))


def sweep_sign_flips(scalar_fn: Callable[[np.ndarray], np.ndarray], n_dim: int,
                     n_sweeps: int = GATE_SWEEPS, steps: int = 11, tol: float = 1e-3,
                     seed: int = 0) -> dict:
    """One-parameter sweeps of a batched scalar predictor ``scalar_fn((m, n_dim)) -> (m,)``.

    A sweep FLIPS if its successive differences (ignoring |diff| < tol, the surrogate's own
    noise) change sign more than once, i.e. the response goes up-down-up or down-up-down. A
    single turn is allowed (physics has optima); a zig-zag is a model that is not modelling
    anything. Strict reading of the plan's "no sign flips": the gate passes at 0 flips.
    """
    rng = np.random.default_rng(seed)
    flips, sweeps = 0, []
    grid = np.linspace(0.0, 1.0, steps)
    for _ in range(n_sweeps):
        base = rng.random(n_dim)
        d = int(rng.integers(n_dim))
        U = np.tile(base, (steps, 1))
        U[:, d] = grid
        y = np.asarray(scalar_fn(U), float)
        diff = np.diff(y)
        sig = np.sign(diff[np.abs(diff) >= tol * max(1.0, np.nanmax(np.abs(y)))])
        changes = int(np.sum(sig[1:] != sig[:-1])) if sig.size > 1 else 0
        bad = changes > 1
        flips += bad
        sweeps.append({"dim": d, "sign_changes": changes, "flip": bool(bad)})
    return {"n_sweeps": n_sweeps, "flips": int(flips), "sweeps": sweeps}


def evaluate_gates(*, obj_pred, obj_true, bw_pred, bw_true, di_pred, di_true, p_ok, ok_true,
                   flips: int, n_heldout: int | None = None) -> dict:
    """All six gates. Inputs are 1-D arrays over the held-out set (bw/di: per-design in-band
    means or flattened curves). Returns {'gates': {name: {value, threshold, pass}}, 'pass': bool,
    'warnings': [...]}. NaN values FAIL."""
    def g(value, thr, ok):
        return {"value": value, "threshold": thr, "pass": bool(ok)}

    rho = spearman(obj_pred, obj_true)
    top = topk_overlap(obj_pred, obj_true)
    bw = mae(bw_pred, bw_true)
    di = mae(di_pred, di_true)
    inv = invalid_accuracy(p_ok, ok_true)
    gates = {
        "spearman": g(rho, f"> {GATE_SPEARMAN}", np.isfinite(rho) and rho > GATE_SPEARMAN),
        "topk_overlap": g(top, f">= {GATE_TOPK} of {TOPK_N}", top >= GATE_TOPK),
        "bw_mae_deg": g(bw, f"< {GATE_BW_MAE_DEG}", np.isfinite(bw) and bw < GATE_BW_MAE_DEG),
        "di_mae_db": g(di, f"< {GATE_DI_MAE_DB}", np.isfinite(di) and di < GATE_DI_MAE_DB),
        "invalid_accuracy": g(inv, f"> {GATE_INVALID_ACC}",
                              np.isfinite(inv) and inv > GATE_INVALID_ACC),
        "monotonic_flips": g(int(flips), "== 0", flips == 0),
    }
    warnings = []
    if n_heldout is not None and n_heldout < MIN_HELDOUT:
        warnings.append(f"held-out set has {n_heldout} designs; the plan requires >= {MIN_HELDOUT}"
                        " for the gates to count. Result is indicative only.")
    return {"gates": gates, "pass": all(v["pass"] for v in gates.values()) and not warnings,
            "warnings": warnings}
