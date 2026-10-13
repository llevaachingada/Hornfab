"""A trained surrogate as a batched evaluator (needs torch)."""
from __future__ import annotations

import numpy as np
import torch

from ..objective.scalar import PENALTY_INVALID, objective, penalty_result
from ..types import Design, Evaluation, MetricSet
from .features import unit_matrix  # noqa: F401  (re-exported for callers)
from .model import MetricMLP, build_models, load_bundle


class Surrogate:
    """Ensemble of MetricMLPs. ``predict`` returns metric curves (n, nf) in physical units,
    ``p_ok`` (n,) and the ensemble std of the stacked curves ``std`` (n,)."""

    def __init__(self, states, meta, mu, sd):
        self.meta, self.mu, self.sd = meta, np.asarray(mu), np.asarray(sd)
        self.freqs = np.asarray(meta["freqs_hz"], float)
        self.nf = len(self.freqs)
        self.names = list(meta["metric_names"])
        self.nets = build_models({"states": states, "meta": meta})

    @classmethod
    def load(cls, path) -> "Surrogate":
        b = load_bundle(path)
        return cls(b["states"], b["meta"], b["mu"], b["sd"])

    @torch.no_grad()
    def predict(self, U: np.ndarray) -> dict:
        x = torch.tensor(np.asarray(U, np.float32))
        outs, oks = [], []
        for net in self.nets:
            r, l = net(x)
            outs.append(r.numpy()); oks.append(torch.sigmoid(l).numpy())
        R = np.stack(outs)                                     # (E, n, 6nf)
        Y = R.mean(0) * self.sd + self.mu
        res = {n: Y[:, i * self.nf:(i + 1) * self.nf] for i, n in enumerate(self.names)}
        res["p_ok"] = np.mean(oks, 0)
        res["std"] = R.std(0).mean(1) if len(R) > 1 else np.zeros(len(x))
        return res

    def metric_set(self, pred: dict, i: int) -> MetricSet:
        return MetricSet(freqs_hz=self.freqs, bw_h_deg=pred["bw_h_deg"][i],
                         bw_v_deg=pred["bw_v_deg"][i], di_db=pred["di_db"][i],
                         di_source="balloon", ripple_h_db=pred["ripple_h_db"][i],
                         ripple_v_db=pred["ripple_v_db"][i], on_axis_db=pred["on_axis_db"][i],
                         z_throat_real=None)

    def objective(self, pred: dict, target, weights: dict) -> np.ndarray:
        """Surrogate J per row; predicted-invalid rows get PENALTY_INVALID."""
        out = np.empty(len(pred["p_ok"]))
        for i in range(len(out)):
            if pred["p_ok"][i] < 0.5:
                out[i] = PENALTY_INVALID
            else:
                out[i] = objective(self.metric_set(pred, i), True, target, weights)[0]
        return out

    def evaluator(self, space, target, weights: dict):
        """``evaluator(list[Design]) -> list[Evaluation]`` for ``search_pareto``. These are
        SURROGATE evaluations (mesh_hash/solve_hash 'surrogate', outcome None): re-solve every
        design you intend to believe with real BEM."""
        def run(designs: list[Design]) -> list[Evaluation]:
            U = np.stack([space.normalize(d) for d in designs])
            pred = self.predict(U)
            evs = []
            for i, d in enumerate(designs):
                if pred["p_ok"][i] < 0.5:
                    j, t = penalty_result(PENALTY_INVALID)
                    m = None
                else:
                    m = self.metric_set(pred, i)
                    j, t = objective(m, True, target, weights)
                evs.append(Evaluation(design_hash=d.hash(), design=d, mesh_hash="surrogate",
                                      solve_hash="surrogate", objective=j, terms=t, metrics=m,
                                      mesh=None, outcome=None, error="" if m else "surrogate_invalid"))
            return evs
        return run
