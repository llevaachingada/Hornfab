"""Opt-in, offline numerical policies; unavailable evidence never becomes a pass."""
from __future__ import annotations

from dataclasses import dataclass, replace
import numpy as np


def loading_margins(freqs_hz, impedance_real, target, metrics):
    """Canonical loading/f11 signed margins, or unavailable on incomplete data."""
    from ..objective.scalar_v8 import V8Params, _loading_and_f11_gates
    from ..objective.scalar_v7 import _resolve_f11_hz
    from ..objective.terms import NAN_TERM_FILL
    try:
        f, z = np.asarray(freqs_hz, float), np.asarray(impedance_real, float)
        if (f.ndim != 1 or len(f) == 0 or z.shape != f.shape or not np.isfinite(f).all()
                or np.any(np.diff(f) <= 0) or not np.isfinite(z).all()):
            raise ValueError("complete ordered frequency and impedance arrays required")
        fx = float(target.f0_effective_hz())
        limit = _resolve_f11_hz(target, metrics)
        if limit is None: raise ValueError("loaded upper limit unknown")
        hi = min(float(target.band_hi_hz), float(limit))
        if not np.isfinite(fx) or fx <= 0 or not np.isfinite(hi) or hi <= 0:
            raise ValueError("invalid loading window")
        window = (f >= fx) & (f <= hi)
        if not window.any(): raise ValueError("loaded window has no samples")
        params = V8Params(tolerances={}, gates=())
        load_fail, f11_fail, diag = _loading_and_f11_gates(f, z, target, metrics, params)
        lfp = diag.get("lfp20_hz")
        if lfp is None or not np.isfinite(lfp) or lfp <= 0 or lfp == NAN_TERM_FILL:
            raise ValueError("ascending LFP20 crossing unavailable")
        margins = np.array([1.6*lfp/fx-1, (0.5-float(z[window].min()))/0.5, fx/hi-1])
        if bool(np.all(margins <= 0)) != (load_fail is None and f11_fail is None):
            raise ValueError("signed margins disagree with canonical gates")
        return {"status": "ok", "margins": margins.tolist(), "feasible": bool(np.all(margins <= 0)),
                "names": ["g_lfp", "g_hold", "g_window"]}
    except (AttributeError, TypeError, ValueError, IndexError, ArithmeticError) as exc:
        return {"status": "constraint_model_unavailable", "reason": str(exc)}


def cost_aware_log_score(log_acquisition, mu_log_seconds, var_log_seconds, *, n_observations):
    """Declared log-acquisition minus lognormal expected-cost heuristic."""
    if n_observations < 30:
        return {"status": "capability_missing", "reason": "fewer_than_30_compatible_uncached_timings"}
    a, m, v = (np.asarray(x, dtype=float) for x in (log_acquisition, mu_log_seconds, var_log_seconds))
    if a.shape != m.shape or a.shape != v.shape or not all(np.isfinite(x).all() for x in (a,m,v)) or np.any(v < 0):
        return {"status": "capability_missing", "reason": "invalid_cost_posterior"}
    return {"status": "ok", "values": a - (m + 0.5*v), "method": "log_acquisition_minus_log_expected_cost"}


def fit_cost_model(X, seconds, ids, *, cached, actual_bem, seed=0):
    """Fit log uncached actual-call seconds, including measured failed-call times."""
    from types import SimpleNamespace
    from .model import fit_model
    x, t = np.asarray(X, float), np.asarray(seconds, float)
    if x.ndim != 2 or t.shape != (len(x),) or len(ids) != len(x) or len(cached) != len(x) or len(actual_bem) != len(x):
        return {"status": "capability_missing", "reason": "invalid_timing_inputs"}
    if any(type(v) not in (bool, np.bool_) for v in (*cached, *actual_bem)):
        return {"status": "capability_missing", "reason": "unknown_timing_provenance"}
    valid = np.isfinite(t) & (t > 0) & ~np.asarray(cached, bool) & np.asarray(actual_bem, bool)
    if np.count_nonzero(valid) < 30:
        return {"status": "capability_missing", "reason": "fewer_than_30_compatible_uncached_timings"}
    x, t = x[valid], t[valid]
    # fit_model always models Y=-J: set J=-log(seconds) to model log(seconds).
    j = -np.log(np.maximum(t, 1e-3)).reshape(-1, 1)
    selected_ids = tuple(str(ids[i]) for i in np.flatnonzero(valid))
    data = SimpleNamespace(status="ok", d=x.shape[1], n=len(x), X=x, J=j, Y=-j,
                           ids=selected_ids, n_min=max(16, 2*(x.shape[1]+1)))
    fit = fit_model(data, seed=seed)
    if fit.status != "ok": return {"status": "capability_missing", "reason": fit.reason}
    return {"status": "ok", "fit": fit, "observation_ids": selected_ids,
            "target": "log(max(actual_uncached_BEM_seconds,1e-3))"}


@dataclass(frozen=True)
class TrustRegion:
    center: tuple[float, ...]
    best_j: float
    length: float = 0.8
    successes: int = 0
    failures: int = 0
    iteration: int = 0
    status: str = "active"


def trust_box(state: TrustRegion, lengthscales):
    center, ls = np.asarray(state.center, float), np.asarray(lengthscales, float)
    if (state.status != "active" or center.ndim != 1 or len(center) == 0 or ls.shape != center.shape
            or not np.isfinite(center).all() or np.any((center < 0) | (center > 1))
            or not np.isfinite(ls).all() or np.any(ls <= 0) or not np.isfinite(state.length)
            or state.length <= 0):
        raise ValueError("invalid trust-region state or lengthscales")
    weights = ls / np.exp(np.log(ls).mean())
    return np.maximum(0, center - state.length*weights/2), np.minimum(1, center + state.length*weights/2)


def update_trust_region(state: TrustRegion, *, outcome: str, candidate=None, J=None):
    """Persist one measured outcome; infrastructure pauses without counter changes."""
    if state.status != "active":
        raise ValueError("trust region is not active")
    if outcome == "infrastructure_failure":
        return replace(state, status="paused")
    if outcome not in {"measured", "geometry_refusal"}:
        raise ValueError("unknown outcome cannot update trust region")
    improved = False
    if outcome == "measured":
        vec = np.asarray(candidate, float)
        if (vec.shape != (len(state.center),) or not np.isfinite(vec).all()
                or np.any((vec < 0) | (vec > 1)) or J is None or not np.isfinite(J)):
            raise ValueError("measured outcome requires finite eligible candidate and J")
        improved = float(J) < state.best_j - 1e-3*max(abs(state.best_j), 1e-8)
    successes = state.successes + 1 if improved else 0
    failures = 0 if improved else state.failures + 1
    length = state.length
    if successes >= 3:
        length, successes = min(1.6, 2*length), 0
    if failures >= max(4, len(state.center)):
        length, failures = length/2, 0
    new_best = outcome == "measured" and float(J) < state.best_j
    return TrustRegion(tuple(float(v) for v in candidate) if new_best else state.center,
                       float(J) if new_best else state.best_j, length, successes, failures,
                       state.iteration + 1, "complete" if length < 0.5**7 else "active")
