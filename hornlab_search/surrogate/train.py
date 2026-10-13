"""Train an ensemble on ``to_training_arrays`` output and report the gates (needs torch)."""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

from ..dataset.store import Y_METRIC_KEYS
from . import gates
from .features import cluster_holdout, unit_matrix
from .model import MetricMLP, save_bundle
from .predict import Surrogate


def _targets(arrays: dict) -> np.ndarray:
    ym = arrays["y_metrics"]
    return np.concatenate([ym[k] for k in Y_METRIC_KEYS], axis=1)       # (n, 6*nf)


def train_surrogate(arrays: dict, space, target, weights: dict, *, ensemble: int = 5,
                    hidden: int = 256, layers: int = 3, epochs: int = 300, lr: float = 2e-3,
                    holdout_frac: float = 0.15, seed: int = 0, out_path=None,
                    lib_sha: str | None = None) -> tuple[Surrogate, dict]:
    """``arrays`` MUST come from ``to_training_arrays(store, family=..., keys=space.keys(),
    ok_only=False)`` (failures teach the validity head). Returns (surrogate, report); the report
    holds the gates on the cluster-held-out set. A model failing a gate must not be used."""
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

    meta = {"family": str(arrays["family"][0]) if len(arrays["family"]) else "",
            "keys": space.keys(), "freqs_hz": [float(f) for f in arrays["freqs_hz"]],
            "metric_names": list(Y_METRIC_KEYS), "hidden": hidden, "layers": layers,
            "lib_sha": lib_sha, "n_train": int(tr.sum()), "n_heldout": int(held.sum())}
    sur = Surrogate(states, meta, mu, sd)
    if out_path is not None:
        save_bundle(out_path, states=states, meta=meta, mu=mu, sd=sd)
    return sur, evaluate_heldout(sur, arrays, U, held, target, weights)


def evaluate_heldout(sur: Surrogate, arrays: dict, U: np.ndarray, held: np.ndarray, target,
                     weights: dict) -> dict:
    """Gate report on rows ``held``. True objectives come from the dataset's own scalars."""
    ok = np.asarray(arrays["ok"], bool)[held]
    true_obj = np.asarray(arrays["y_scalars"]["objective"], float)[held]
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
    return rep
