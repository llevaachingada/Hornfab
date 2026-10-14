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

    def config_mismatch(self, space, *, freqs_hz=None, family: str | None = None) -> str | None:
        """First way the frozen config contract in ``meta`` disagrees with the config being
        proposed with (family, key order, per-key bounds, and -- when ``freqs_hz`` is given -- the
        frequency grid). Returns a message naming the mismatched field, or None when they agree.

        Old bundles that predate the contract (no ``bounds``) are reported as mismatched so the
        caller refuses rather than silently proposing off a different contract."""
        fam = family if family is not None else space.family
        exp_fam = self.meta.get("family")
        if exp_fam is not None and exp_fam != fam:
            return f"family: bundle was trained for {exp_fam!r}, config proposes {fam!r}"
        exp_keys = self.meta.get("keys")
        if exp_keys is not None and list(exp_keys) != list(space.keys()):
            return f"keys: bundle keys {list(exp_keys)} != config keys {list(space.keys())}"
        bounds = self.meta.get("bounds")
        if not bounds:
            return "bounds: bundle has no recorded bounds (retrain to freeze the config contract)"
        for k in space.keys():
            b = space.bounds[k]
            e = bounds.get(k)
            if e is None:
                return f"bounds[{k}]: missing from the bundle"
            if (float(e["lo"]) != float(b.lo) or float(e["hi"]) != float(b.hi)
                    or bool(e["log"]) != bool(b.log)):
                return (f"bounds[{k}]: bundle lo/hi/log={e['lo']}/{e['hi']}/{e['log']} != "
                        f"config {b.lo}/{b.hi}/{b.log}")
        exp_freqs = self.meta.get("freqs_hz")
        if freqs_hz is not None and exp_freqs is not None:
            a = np.asarray(exp_freqs, float)
            b = np.asarray(freqs_hz, float)
            if a.shape != b.shape or not np.allclose(a, b, rtol=0.0, atol=1e-3):
                return (f"freqs_hz: bundle grid has {a.size} points "
                        f"({a.min():g}..{a.max():g} Hz), config wants {b.size} points "
                        f"({b.min():g}..{b.max():g} Hz)")
        return None

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
