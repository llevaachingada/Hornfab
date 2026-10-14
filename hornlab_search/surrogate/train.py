"""Train an ensemble on ``to_training_arrays`` output and report the gates (needs torch)."""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

from ..dataset.store import Y_METRIC_KEYS
from ..objective.scalar import objective
from ..types import MetricSet
from . import gates
from .features import cluster_holdout, unit_matrix
from .model import MetricMLP, bundle_gates_passed, save_bundle
from .predict import Surrogate


def _targets(arrays: dict) -> np.ndarray:
    ym = arrays["y_metrics"]
    return np.concatenate([ym[k] for k in Y_METRIC_KEYS], axis=1)       # (n, 6*nf)


def _dedup_by_design_hash(arrays: dict) -> tuple[dict, int]:
    """Drop rows whose ``design_hash`` was already seen (first occurrence wins), before the holdout
    split. Duplicate designs are exact repeats: keeping them lets the cluster holdout put a copy of
    a training design into the held-out set, which inflates the gate scores. Returns
    (arrays, n_dropped); a missing ``design_hash`` is a no-op."""
    dh = arrays.get("design_hash")
    if dh is None:
        return arrays, 0
    dh = np.asarray(dh)
    if dh.size == 0:
        return arrays, 0
    _, first = np.unique(dh.astype(str), return_index=True)
    keep = np.sort(first)
    dropped = int(dh.size - keep.size)
    if dropped == 0:
        return arrays, 0

    def take(v):
        return np.asarray(v)[keep]

    out = dict(arrays)
    out["X"] = take(arrays["X"])
    out["ok"] = take(arrays["ok"])
    out["y_metrics"] = {k: take(v) for k, v in arrays["y_metrics"].items()}
    out["y_scalars"] = {k: take(v) for k, v in arrays["y_scalars"].items()}
    for k in ("design_hash", "family", "di_source"):
        if k in arrays:
            out[k] = take(arrays[k])
    if isinstance(arrays.get("excitation"), dict):
        out["excitation"] = {k: take(v) for k, v in arrays["excitation"].items()}
    return out, dropped


def _recompute_true_objectives(arrays: dict, held: np.ndarray, target, weights: dict) -> np.ndarray:
    """True J for the held-out rows, recomputed from the exported metric arrays with the CURRENT
    target and weights (the same ``objective`` the predictions use). The stored per-record objective
    is only used elsewhere to report the drift, not to drive the rank gates."""
    ym = arrays["y_metrics"]
    freqs = arrays["freqs_hz"]
    ok = np.asarray(arrays["ok"], bool)
    z = ym.get("z_throat_real")
    idx = np.flatnonzero(held)
    out = np.full(idx.size, np.nan)
    for j, i in enumerate(idx):
        if not ok[i]:
            continue
        m = MetricSet(freqs, ym["bw_h_deg"][i], ym["bw_v_deg"][i], ym["di_db"][i], "balloon",
                      ym["ripple_h_db"][i], ym["ripple_v_db"][i], ym["on_axis_db"][i],
                      None if z is None else z[i])
        out[j] = objective(m, True, target, weights)[0]
    return out


def train_surrogate(arrays: dict, space, target, weights: dict, *, ensemble: int = 5,
                    hidden: int = 256, layers: int = 3, epochs: int = 300, lr: float = 2e-3,
                    holdout_frac: float = 0.15, seed: int = 0, out_path=None,
                    lib_sha: str | None = None) -> tuple[Surrogate, dict]:
    """``arrays`` MUST come from ``to_training_arrays(store, family=..., keys=space.keys(),
    ok_only=False)`` (failures teach the validity head). Returns (surrogate, report); the report
    holds the gates on the cluster-held-out set, and the SAME verdict is frozen into the bundle meta
    (``meta['gate_report']``) so ``surrogate propose`` can refuse an unvalidated model. A model
    failing a gate must not be used."""
    arrays, dropped = _dedup_by_design_hash(arrays)
    U = unit_matrix(arrays["X"], arrays["key_names"], space)
    Y, ok = _targets(arrays), np.asarray(arrays["ok"], bool)
    held = cluster_holdout(U, holdout_frac, seed=seed)
    tr = ~held
    ytr = Y[tr & ok]
    mu, sd = np.nanmean(ytr, 0), np.nanstd(ytr, 0)
    sd = np.where(~np.isfinite(sd) | (sd < 1e-6), 1.0, sd)
    mu = np.where(np.isfinite(mu), mu, 0.0)
    Z = ((Y - mu) / sd).astype(np.float32)
    mask = np.isfinite(Z) & ok[:, None]
    Z = np.nan_to_num(Z)

    states = []
    for e in range(ensemble):
        torch.manual_seed(seed + e)
        rng = np.random.default_rng(seed + e)
        net = MetricMLP(U.shape[1], Y.shape[1], hidden, layers)
        opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-4)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
        idx = np.flatnonzero(tr)
        Ut, Zt = torch.tensor(U), torch.tensor(Z)
        Mt, Ot = torch.tensor(mask), torch.tensor(ok, dtype=torch.float32)
        huber, bce = nn.HuberLoss(reduction="none"), nn.BCEWithLogitsLoss()
        for _ in range(epochs):
            b = rng.choice(idx, size=min(len(idx), 256), replace=len(idx) < 256)   # bootstrap-ish
            pred, logit = net(Ut[b])
            m = Mt[b].float()
            reg = (huber(pred, Zt[b]) * m).sum() / m.sum().clamp(min=1)
            loss = reg + 0.5 * bce(logit, Ot[b])
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        states.append({k: v.clone() for k, v in net.state_dict().items()})

    # Frozen config contract: proposing later must use exactly this family/keys/bounds/freq grid.
    meta = {"family": str(arrays["family"][0]) if len(arrays["family"]) else "",
            "keys": list(space.keys()), "freqs_hz": [float(f) for f in arrays["freqs_hz"]],
            "bounds": {k: {"lo": float(space.bounds[k].lo), "hi": float(space.bounds[k].hi),
                           "log": bool(space.bounds[k].log)} for k in space.keys()},
            "metric_names": list(Y_METRIC_KEYS), "hidden": hidden, "layers": layers,
            "lib_sha": lib_sha, "n_train": int(tr.sum()), "n_heldout": int(held.sum()),
            "n_duplicates_dropped": int(dropped)}
    sur = Surrogate(states, meta, mu, sd)
    rep = evaluate_heldout(sur, arrays, U, held, target, weights)
    rep["n_duplicates_dropped"] = int(dropped)
    meta["gate_report"] = {"gates_passed": bool(rep["pass"]),
                           "n_heldout": int(rep["n_heldout"]),
                           "warnings": list(rep["warnings"]),
                           "sweeps": int(rep["sweeps"]),
                           "gates": rep["gates"]}
    sur.meta = meta
    # Evaluate BEFORE saving. Never clobber a known-good (passing) bundle with a failed retrain.
    saved, kept_existing = False, False
    if out_path is not None:
        if not rep["pass"] and bundle_gates_passed(out_path):
            kept_existing = True
        else:
            save_bundle(out_path, states=states, meta=meta, mu=mu, sd=sd)
            saved = True
    rep["saved"] = saved
    rep["kept_existing_bundle"] = kept_existing
    return sur, rep


def evaluate_heldout(sur: Surrogate, arrays: dict, U: np.ndarray, held: np.ndarray, target,
                     weights: dict) -> dict:
    """Gate report on rows ``held``. True objectives are recomputed from the exported metric arrays
    with the CURRENT target/weights; the stored per-record objective is only used to report drift."""
    ok = np.asarray(arrays["ok"], bool)[held]
    true_stored = np.asarray(arrays["y_scalars"]["objective"], float)[held]
    true_obj = _recompute_true_objectives(arrays, held, target, weights)
    with np.errstate(invalid="ignore"):
        delta = np.abs(true_obj - true_stored)
    delta = delta[np.isfinite(delta)]
    pred = sur.predict(U[held])
    pred_obj = sur.objective(pred, target, weights)
    band = (sur.freqs >= target.band_lo_hz) & (sur.freqs <= target.band_hi_hz)
    ym = {k: np.asarray(arrays["y_metrics"][k])[held] for k in ("bw_h_deg", "bw_v_deg", "di_db")}
    sel = ok[:, None] & band[None, :]
    bw_p = np.concatenate([pred["bw_h_deg"][sel], pred["bw_v_deg"][sel]])
    bw_t = np.concatenate([ym["bw_h_deg"][sel], ym["bw_v_deg"][sel]])
    flips = gates.sweep_sign_flips(
        lambda X: sur.objective(sur.predict(X.astype(np.float32)), target, weights),
        U.shape[1])
    rep = gates.evaluate_gates(
        obj_pred=np.where(ok, pred_obj, np.nan), obj_true=np.where(ok, true_obj, np.nan),
        bw_pred=bw_p, bw_true=bw_t, di_pred=pred["di_db"][sel], di_true=ym["di_db"][sel],
        p_ok=pred["p_ok"], ok_true=ok, flips=flips["flips"], n_heldout=int(held.sum()))
    rep["sweeps"] = flips["n_sweeps"]
    rep["n_heldout"] = int(held.sum())
    # The stored objective is kept ONLY to report how far it drifted from the current-weight value.
    rep["objective_delta_max"] = float(delta.max()) if delta.size else 0.0
    rep["objective_delta_mean"] = float(delta.mean()) if delta.size else 0.0
    return rep
