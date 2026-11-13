"""S7 advisory surrogate validation (offline, numpy only, never changes a default).

Usage::

    PY tools\\analysis\\surrogate_validation.py --rows rows.jsonl --out DIR
        [--test-frac 0.25] [--k 5] [--topk 5] [--pool pool.jsonl] [--n-propose 6]

Input rows (JSONL or a JSON list), one per evaluated design::

    {"row_id": str, "design_hash": str, "t": number (wall time or evaluation index),
     "objective_version": int, "x": [unit-cube floats], "ok": bool,
     "j": float|null, "metrics": {name: float, ...}}

What it does:
1. Capability gate: every row's ``objective_version`` must pass
   ``hornlab_search.surrogate.capability.require_supported``; mixed versions are refused
   (never rank J across versions).  Refusal is the result, not an error to work around.
2. Chronological split: the latest ``test_frac`` of rows by ``t`` are test.  Leakage
   checks: no training row is later than any test row; any test row whose design_hash
   also appears in training is REMOVED from test and counted (no same-geometry leak).
   Preprocessing (per-axis scale) is fit on training rows only.
3. Model: k-nearest-neighbour regression in the unit cube (mean = prediction, neighbour
   std = uncertainty) for J and every metric; a separate kNN feasibility probability.
   Baseline: training mean.  Test rows beyond the training support (nearest-train
   distance > 95th percentile of train-train NN distances) are flagged OOD and get no
   prediction (fallback, counted).
4. Report: Spearman, top-k recall, decision regret, MAE per metric vs baseline,
   feasibility Brier score + reliability bins, 95% interval coverage.
5. Optional proposals from ``--pool``: exploit / uncertainty / diversity mix; they are
   hypotheses for later normal-evaluator BEM validation, never measured values.

Resume-safe: the output file name carries the sha256 of (inputs + parameters); a
complete file with that key is reused (``resumed: true``), a stale ``.partial`` file is
reported and replaced; writes go via temp file + atomic rename.  Advisory only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

TOOL = "surrogate_validation"
SCHEMA_VERSION = 1


class Refused(Exception):
    def __init__(self, reason, detail):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


# --------------------------------------------------------------------------- input


def load_rows(path: Path) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    s = text.lstrip()
    if s.startswith("["):
        rows = json.loads(s)
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise Refused("bad_input", "rows must be a list of objects")
    return rows


def _validate(rows: list[dict]) -> tuple[list[dict], int, list[str]]:
    """Return usable rows, their common objective version and the metric names."""
    from hornlab_search.surrogate.capability import UnsupportedObjectiveError, require_supported
    if len(rows) < 8:
        raise Refused("insufficient_rows", f"need >= 8 rows, got {len(rows)}")
    versions = {r.get("objective_version") for r in rows}
    if len(versions) != 1:
        raise Refused("mixed_objective_versions",
                      f"rows mix objective versions {sorted(map(str, versions))}; never pooled")
    version = versions.pop()
    try:
        require_supported(version, context="surrogate_validation")
    except UnsupportedObjectiveError as exc:
        raise Refused("unsupported_objective_version", str(exc)) from exc
    dim = None
    metric_names = None
    for r in rows:
        missing = [k for k in ("row_id", "design_hash", "t", "x", "ok") if r.get(k) is None]
        if missing:
            raise Refused("missing_inputs", f"row {r.get('row_id')!r} lacks {missing}")
        x = r["x"]
        if not isinstance(x, list) or not x or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in x):
            raise Refused("missing_inputs", f"row {r['row_id']!r} has a non-finite/empty x")
        if dim is None:
            dim = len(x)
        elif len(x) != dim:
            raise Refused("missing_inputs", "rows disagree on x dimension")
        if r["ok"] and not (isinstance(r.get("j"), (int, float)) and math.isfinite(r["j"])):
            raise Refused("missing_inputs", f"ok row {r['row_id']!r} has no finite j")
        names = sorted((r.get("metrics") or {}).keys()) if r["ok"] else None
        if names is not None:
            metric_names = names if metric_names is None else sorted(set(metric_names) & set(names))
    return rows, version, metric_names or []


# --------------------------------------------------------------------------- split


def chronological_split(rows: list[dict], test_frac: float) -> dict:
    order = sorted(range(len(rows)), key=lambda i: (float(rows[i]["t"]), str(rows[i]["row_id"])))
    n_test = max(1, int(round(test_frac * len(rows))))
    train_idx, test_idx = order[:-n_test], order[-n_test:]
    t_cut = max(float(rows[i]["t"]) for i in train_idx)
    # Ties at the cut would put "simultaneous" rows on both sides: move them to train.
    tie = [i for i in test_idx if float(rows[i]["t"]) <= t_cut]
    train_idx += tie
    test_idx = [i for i in test_idx if i not in tie]
    train_hashes = {rows[i]["design_hash"] for i in train_idx}
    leaked = [i for i in test_idx if rows[i]["design_hash"] in train_hashes]
    test_idx = [i for i in test_idx if i not in leaked]
    # Duplicates inside test: keep the earliest only.
    seen, dedup = set(), []
    for i in test_idx:
        if rows[i]["design_hash"] not in seen:
            seen.add(rows[i]["design_hash"])
            dedup.append(i)
    checks = {
        "max_train_t": t_cut,
        "min_test_t": min((float(rows[i]["t"]) for i in dedup), default=None),
        "no_future_rows_in_train": all(float(rows[i]["t"]) <= t_cut for i in train_idx)
        and all(float(rows[i]["t"]) > t_cut for i in dedup),
        "same_geometry_removed_from_test": len(leaked),
        "duplicate_test_rows_removed": len(test_idx) - len(dedup),
        "tie_rows_moved_to_train": len(tie),
        "shared_design_hashes": len({rows[i]["design_hash"] for i in dedup} & train_hashes),
    }
    assert checks["shared_design_hashes"] == 0 and checks["no_future_rows_in_train"]
    return {"train": train_idx, "test": dedup, "checks": checks}


# --------------------------------------------------------------------------- model


class KNN:
    """k-NN in a train-only standardised unit cube. Mean + neighbour std."""

    def __init__(self, X, k):
        self.mu = X.mean(axis=0)
        self.sd = X.std(axis=0)
        self.sd[self.sd < 1e-9] = 1.0
        self.Z = (X - self.mu) / self.sd
        self.k = max(1, min(k, len(X)))
        d = self._dist(self.Z)
        np.fill_diagonal(d, np.inf)
        nn = d.min(axis=1)
        self.support = float(np.quantile(nn[np.isfinite(nn)], 0.95)) if len(X) > 1 else 0.0

    def _dist(self, Z):
        return np.sqrt(((Z[:, None, :] - self.Z[None, :, :]) ** 2).sum(-1))

    def neighbours(self, X):
        d = self._dist((X - self.mu) / self.sd)
        idx = np.argsort(d, axis=1)[:, : self.k]
        return idx, d.min(axis=1)


def _spearman(a, b):
    if len(a) < 3:
        return None
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    if ra.std() == 0 or rb.std() == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def _fit_eval(rows, split, metric_names, k, topk):
    tr, te = split["train"], split["test"]
    X = np.array([rows[i]["x"] for i in range(len(rows))], dtype=float)
    ok = np.array([bool(rows[i]["ok"]) for i in range(len(rows))])
    model = KNN(X[tr], k)
    idx, nnd = model.neighbours(X[te])
    tr_arr = np.asarray(tr)
    ood = nnd > model.support + 1e-12
    out = {"n_train": len(tr), "n_test": len(te), "n_ood_fallback": int(ood.sum()),
           "support_radius": model.support}

    # Feasibility (all test rows, incl. failed ones); OOD gets the train base rate.
    base_rate = float(ok[tr].mean())
    p_ok = np.where(ood, base_rate, ok[tr_arr[idx]].mean(axis=1))
    y_ok = ok[te].astype(float)
    bins = []
    for lo in np.linspace(0, 1, 5, endpoint=False):
        m = (p_ok >= lo) & (p_ok < lo + 0.2 + (1e-9 if lo >= 0.8 else 0))
        if m.any():
            bins.append({"bin": [float(lo), float(lo + 0.2)], "n": int(m.sum()),
                         "mean_pred": float(p_ok[m].mean()), "observed": float(y_ok[m].mean())})
    out["feasibility"] = {"brier": float(np.mean((p_ok - y_ok) ** 2)),
                          "brier_baseline": float(np.mean((base_rate - y_ok) ** 2)),
                          "reliability_bins": bins}

    # Regression on ok rows only: neighbours drawn from ok training rows.
    tr_ok = [i for i in tr if ok[i]]
    te_ok_mask = np.array([ok[i] for i in te]) & ~ood
    te_ok = [i for i, m in zip(te, te_ok_mask) if m]
    out["regression"] = {"status": "insufficient_data"}
    if len(tr_ok) >= 3 and len(te_ok) >= 3:
        reg = KNN(X[tr_ok], k)
        ridx, _ = reg.neighbours(X[te_ok])
        tro = np.asarray(tr_ok)

        def target(i, name):
            return rows[i]["j"] if name == "j" else (rows[i].get("metrics") or {}).get(name)

        per = {}
        for name in ["j", *metric_names]:
            ytr = np.array([target(i, name) for i in tr_ok], dtype=float)
            yte = np.array([target(i, name) for i in te_ok], dtype=float)
            pos = {i: n for n, i in enumerate(tro)}
            nb = np.vectorize(lambda r: ytr[pos[tro[r]]])(ridx)
            mean, std = nb.mean(axis=1), nb.std(axis=1, ddof=1) if nb.shape[1] > 1 else np.zeros(len(yte))
            base = float(ytr.mean())
            entry = {"mae": float(np.mean(np.abs(mean - yte))),
                     "mae_baseline": float(np.mean(np.abs(base - yte))),
                     "spearman": _spearman(mean, yte)}
            half = 1.96 * np.maximum(std, 1e-12)
            entry["interval_95_coverage"] = float(np.mean(np.abs(yte - mean) <= half))
            if name == "j":
                kk = min(topk, len(yte))
                pred_top = set(np.argsort(mean)[:kk])
                true_top = set(np.argsort(yte)[:kk])
                entry.update(topk=kk, topk_recall=len(pred_top & true_top) / kk,
                             regret=float(yte[int(np.argmin(mean))] - yte.min()),
                             direction="minimize")
            per[name] = entry
        out["regression"] = {"status": "ok", "n_eval": len(te_ok), "targets": per}
    return out, model


# --------------------------------------------------------------------------- proposals


def propose(rows, split, pool, n, k):
    """Mixed exploit/uncertainty/diversity picks from a candidate pool (hypotheses only)."""
    tr_ok = [i for i in split["train"] + split["test"] if rows[i]["ok"]]
    if not pool or len(tr_ok) < 3:
        return {"status": "no_pool_or_data", "proposals": []}
    X = np.array([rows[i]["x"] for i in tr_ok], float)
    y = np.array([rows[i]["j"] for i in tr_ok], float)
    reg = KNN(X, k)
    P = np.array([c["x"] for c in pool], float)
    idx, nnd = reg.neighbours(P)
    mean, std = y[idx].mean(axis=1), y[idx].std(axis=1)
    in_support = nnd <= reg.support + 1e-12
    chosen, out = set(), []

    def take(order, role):
        for j in order:
            if j not in chosen and len(out) < n:
                chosen.add(j)
                out.append({"candidate_id": pool[j].get("candidate_id", str(j)), "role": role,
                            "predicted_j": float(mean[j]), "uncertainty": float(std[j]),
                            "in_support": bool(in_support[j]), "measured": False,
                            "status": "hypothesis"})
                return

    roles = ["exploit", "uncertainty", "diversity"]
    while len(out) < min(n, len(pool)):
        before = len(out)
        for role in roles:
            if role == "exploit":
                take([j for j in np.argsort(mean) if in_support[j]], role)
            elif role == "uncertainty":
                take(list(np.argsort(-std)), role)
            else:
                if chosen:
                    C = P[sorted(chosen)]
                    dmin = np.sqrt(((P[:, None] - C[None]) ** 2).sum(-1)).min(axis=1)
                    take(list(np.argsort(-dmin)), role)
                else:
                    take(list(range(len(pool))), role)
        if len(out) == before:
            break
    return {"status": "ok", "proposals": out,
            "note": "predictions are hypotheses; validate with the normal evaluator (BEM) later"}


# --------------------------------------------------------------------------- driver


def run(rows_path: Path, out_dir: Path, *, test_frac=0.25, k=5, topk=5,
        pool_path: Path | None = None, n_propose=6) -> dict:
    params = {"test_frac": test_frac, "k": k, "topk": topk, "n_propose": n_propose}
    h = hashlib.sha256(Path(rows_path).read_bytes())
    if pool_path:
        h.update(Path(pool_path).read_bytes())
    h.update(json.dumps(params, sort_keys=True).encode())
    key = h.hexdigest()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / f"{TOOL}-{key[:16]}.json"
    partial = final.with_suffix(".partial")
    if final.is_file():
        try:
            existing = json.loads(final.read_text(encoding="utf-8"))
            if existing.get("input_key") == key and existing.get("complete") is True:
                existing["resumed"] = True
                return existing
        except ValueError:
            pass
    stale_partial = partial.exists()
    payload = {"tool": TOOL, "schema_version": SCHEMA_VERSION, "input_key": key, "params": params,
               "advisory_only": True, "changes_defaults": False, "resumed": False,
               "stale_partial_replaced": stale_partial, "input": {"rows": str(rows_path),
                                                                    "pool": str(pool_path) if pool_path else None}}
    try:
        rows, version, metric_names = _validate(load_rows(rows_path))
        split = chronological_split(rows, test_frac)
        evaluation, _ = _fit_eval(rows, split, metric_names, k, topk)
        pool = load_rows(pool_path) if pool_path else None
        payload.update(status="ok", objective_version=version, metric_names=metric_names,
                       split={"kind": "chronological", "checks": split["checks"],
                              "train_ids": [rows[i]["row_id"] for i in split["train"]],
                              "test_ids": [rows[i]["row_id"] for i in split["test"]]},
                       evaluation=evaluation,
                       proposals=propose(rows, split, pool, n_propose, k))
    except Refused as exc:
        payload.update(status="refused", reason=exc.reason, detail=exc.detail)
    payload["complete"] = True
    data = json.dumps(payload, indent=1, sort_keys=True, allow_nan=False) + "\n"
    partial.write_text(data, encoding="utf-8")
    os.replace(partial, final)
    payload["path"] = str(final)
    return payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="S7 advisory surrogate validation (offline)")
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--test-frac", type=float, default=0.25)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--pool", default=None)
    ap.add_argument("--n-propose", type=int, default=6)
    a = ap.parse_args(argv)
    if not 0.05 <= a.test_frac <= 0.5:
        ap.error("--test-frac must be in [0.05, 0.5]")
    p = run(Path(a.rows), Path(a.out), test_frac=a.test_frac, k=a.k, topk=a.topk,
            pool_path=Path(a.pool) if a.pool else None, n_propose=a.n_propose)
    print(f"surrogate_validation {p['status']}"
          + (f" ({p.get('reason')})" if p["status"] != "ok" else "") + " [advisory only]")
    return 0 if p["status"] == "ok" else 3


if __name__ == "__main__":
    sys.exit(main())
