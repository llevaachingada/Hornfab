"""S7 advisory surrogate validation (offline, numpy only, never changes a default).

Usage::

    PY tools\\analysis\\surrogate_validation.py --rows rows.jsonl --out DIR
        [--test-frac 0.25] [--k 5] [--topk 5] [--pool pool.jsonl] [--n-propose 6]
        [--advisory-stored-j]

Input rows (JSONL or a JSON list), one per evaluated design::

    {"row_id": str, "design_hash": str, "t": number (wall time or evaluation index),
     "objective_version": int, "x": [unit-cube floats], "ok": bool,
     "j": float|null, "metrics": {name: float, ...}}

What it does:
1. Capability gate: by default every row's ``objective_version`` must pass
   ``hornlab_search.surrogate.capability.require_supported``; mixed versions are refused
   (never rank J across versions).  Refusal is the result, not an error to work around.
   ``--advisory-stored-j`` is a separate v4-only analysis path. It never claims that the
   legacy metric surrogate can score v4: every successful row must carry an exact stored
   label, complete evidence, and the same canonical resolved score-spec identity.
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
CODE_VERSION = 2
STORED_LABEL_SOURCE = "stored_evaluation"
STORED_LABEL_STATUS = "exact_complete"
REPO = Path(__file__).resolve().parents[2]
_FORBIDDEN_OUTPUT_ROOTS = tuple(REPO / name for name in
                                ("runs", "dataset", "dataset_cpu", "cache", "cache_cpu"))


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


def _guard_out(path: Path) -> None:
    resolved = Path(path).resolve()
    for root in _FORBIDDEN_OUTPUT_ROOTS:
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            continue
        raise Refused("forbidden_output",
                      f"--out may not write into live {root.name}/")
    if resolved.exists() and not resolved.is_dir():
        raise Refused("bad_output", f"--out must be a directory, got file {resolved}")


def _canonical_hash(value: object) -> str:
    """Stable full SHA-256 for a JSON score specification (never per-design data)."""
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise Refused("invalid_score_spec", f"score_spec is not canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _finite_mapping(value: object, name: str, *, positive=False) -> dict:
    if not isinstance(value, dict) or not value:
        raise Refused("incomplete_score_spec", f"score_spec.{name} must be a non-empty mapping")
    for key, raw in value.items():
        if not isinstance(key, str) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
            raise Refused("incomplete_score_spec", f"score_spec.{name} must contain finite numeric values")
        if positive and raw <= 0:
            raise Refused("incomplete_score_spec", f"score_spec.{name}.{key} must be > 0")
    return value


def _score_spec_identity(row: dict, version: int) -> tuple[str, dict]:
    """Validate and hash the resolved, cohort-level score contract.

    Deliberately excludes replay ``score_id``: replay IDs include metric/physical identity and
    therefore normally differ for every design.  This mirrors the resolved-spec approach in
    ``tools/analysis/cohorts.py`` rather than treating a per-result provenance ID as a cohort ID.
    """
    spec = row.get("score_spec")
    if not isinstance(spec, dict):
        raise Refused("missing_score_identity", f"row {row.get('row_id')!r} lacks score_spec")
    required = ("brief", "brief_hash", "objective_version", "target", "weights",
                "objective_block", "terms_keys", "score_schema_version")
    missing = [key for key in required if spec.get(key) is None]
    if missing:
        raise Refused("incomplete_score_spec", f"row {row.get('row_id')!r} score_spec lacks {missing}")
    if spec.get("objective_version") != version:
        raise Refused("score_identity_mismatch",
                      f"row {row.get('row_id')!r} score_spec objective version disagrees with row")
    if not isinstance(spec.get("brief"), str) or not spec["brief"].strip():
        raise Refused("incomplete_score_spec", "score_spec.brief must be a non-empty string")
    if not isinstance(spec.get("brief_hash"), str) or not spec["brief_hash"].strip():
        raise Refused("incomplete_score_spec", "score_spec.brief_hash must be a non-empty string")
    if not isinstance(spec.get("target"), dict) or not spec["target"]:
        raise Refused("incomplete_score_spec", "score_spec.target must be a resolved non-empty mapping")
    _finite_mapping(spec.get("weights"), "weights")
    block = spec.get("objective_block")
    if not isinstance(block, dict) or block.get("version") != version:
        raise Refused("incomplete_score_spec", "score_spec.objective_block must carry the same version")
    _finite_mapping(block.get("tolerances"), "objective_block.tolerances", positive=True)
    terms = spec.get("terms_keys")
    if (not isinstance(terms, list) or not terms
            or not all(isinstance(term, str) and term for term in terms)
            or len(set(terms)) != len(terms)):
        raise Refused("incomplete_score_spec", "score_spec.terms_keys must be unique non-empty strings")
    if not isinstance(spec.get("score_schema_version"), (str, int)):
        raise Refused("incomplete_score_spec", "score_spec.score_schema_version must be a string or integer")
    identity = _canonical_hash(spec)
    if row.get("score_identity") != identity:
        raise Refused("score_identity_mismatch",
                      f"row {row.get('row_id')!r} declared score_identity does not match score_spec")
    return identity, spec


def _validate_stored_label(row: dict, spec: dict) -> None:
    """Require provenance proving that J is an exact stored label, not an inferred input."""
    if not row.get("ok"):
        return
    evidence = row.get("label_evidence")
    if not isinstance(evidence, dict):
        raise Refused("incomplete_label_evidence", f"ok row {row.get('row_id')!r} lacks label_evidence")
    required = {
        "source": STORED_LABEL_SOURCE,
        "status": STORED_LABEL_STATUS,
        "complete": True,
        "objective_version": 4,
        "metrics_complete": True,
        "response_complete": True,
    }
    for key, expected in required.items():
        if evidence.get(key) != expected:
            raise Refused("incomplete_label_evidence",
                          f"ok row {row.get('row_id')!r} needs label_evidence.{key}={expected!r}")
    if not isinstance(evidence.get("score_id"), str) or not evidence["score_id"].strip():
        raise Refused("incomplete_label_evidence", "exact stored labels need a per-result score_id")
    if not isinstance(evidence.get("j"), (int, float)) or not math.isfinite(evidence["j"]):
        raise Refused("incomplete_label_evidence", "exact stored labels need a finite evidence J")
    if not math.isclose(float(evidence["j"]), float(row["j"]), rel_tol=0.0, abs_tol=1e-12):
        raise Refused("label_value_mismatch", f"row {row.get('row_id')!r} J differs from stored evidence")
    weights = spec["weights"]
    if float(weights.get("diag", 0.0)) != 0.0 and evidence.get("balloon_complete") is not True:
        raise Refused("incomplete_label_evidence", "weighted v4 diag needs complete balloon evidence")
    if float(weights.get("load", 0.0)) != 0.0 and evidence.get("throat_impedance_complete") is not True:
        raise Refused("incomplete_label_evidence", "weighted v4 load needs complete throat impedance evidence")


def _validate(rows: list[dict], *, advisory_stored_j=False) -> tuple[list[dict], int, list[str], str | None]:
    """Return usable rows, their common objective version and the metric names."""
    from hornlab_search.surrogate.capability import UnsupportedObjectiveError, require_supported
    if len(rows) < 8:
        raise Refused("insufficient_rows", f"need >= 8 rows, got {len(rows)}")
    versions = {r.get("objective_version") for r in rows}
    if len(versions) != 1:
        raise Refused("mixed_objective_versions",
                      f"rows mix objective versions {sorted(map(str, versions))}; never pooled")
    version = versions.pop()
    if type(version) is not int:
        raise Refused("missing_inputs", "objective_version must be an integer, not bool or text")
    if advisory_stored_j:
        if version != 4:
            raise Refused("advisory_stored_j_requires_v4",
                          f"--advisory-stored-j is scoped to objective v4, got {version!r}")
    else:
        try:
            require_supported(version, context="surrogate_validation")
        except UnsupportedObjectiveError as exc:
            raise Refused("unsupported_objective_version", str(exc)) from exc
    dim = None
    metric_names = None
    score_identity = None
    row_ids = set()
    for r in rows:
        missing = [k for k in ("row_id", "design_hash", "t", "x", "ok") if r.get(k) is None]
        if missing:
            raise Refused("missing_inputs", f"row {r.get('row_id')!r} lacks {missing}")
        if not isinstance(r["row_id"], str) or not r["row_id"].strip():
            raise Refused("missing_inputs", "row_id must be a non-empty string")
        if r["row_id"] in row_ids:
            raise Refused("duplicate_row_id", f"duplicate row_id {r['row_id']!r}")
        row_ids.add(r["row_id"])
        if not isinstance(r["design_hash"], str) or not r["design_hash"].strip():
            raise Refused("missing_inputs", f"row {r['row_id']!r} design_hash must be non-empty")
        if (isinstance(r["t"], bool) or not isinstance(r["t"], (int, float))
                or not math.isfinite(r["t"])):
            raise Refused("missing_inputs", f"row {r['row_id']!r} t must be finite numeric")
        if type(r["ok"]) is not bool:
            raise Refused("missing_inputs", f"row {r['row_id']!r} ok must be a JSON boolean")
        x = r["x"]
        if (not isinstance(x, list) or not x
                or not all(not isinstance(v, bool) and isinstance(v, (int, float))
                           and math.isfinite(v) and 0.0 <= v <= 1.0 for v in x)):
            raise Refused("missing_inputs",
                          f"row {r['row_id']!r} x must be finite numeric unit-cube values")
        if dim is None:
            dim = len(x)
        elif len(x) != dim:
            raise Refused("missing_inputs", "rows disagree on x dimension")
        if (r["ok"] and (isinstance(r.get("j"), bool)
                         or not isinstance(r.get("j"), (int, float))
                         or not math.isfinite(r["j"]))):
            raise Refused("missing_inputs", f"ok row {r['row_id']!r} has no finite j")
        if advisory_stored_j:
            row_identity, spec = _score_spec_identity(r, version)
            if score_identity is None:
                score_identity = row_identity
            elif row_identity != score_identity:
                raise Refused("mixed_score_identities",
                              "rows mix resolved brief/target/weights/tolerances/score schemas")
            _validate_stored_label(r, spec)
        metrics = r.get("metrics")
        if metrics is not None and not isinstance(metrics, dict):
            raise Refused("missing_inputs", f"row {r['row_id']!r} metrics must be a mapping")
        if isinstance(metrics, dict):
            for name, value in metrics.items():
                if (not isinstance(name, str) or not name
                        or isinstance(value, bool) or not isinstance(value, (int, float))
                        or not math.isfinite(value)):
                    raise Refused("missing_inputs",
                                  f"row {r['row_id']!r} has a non-finite/non-numeric metric")
        names = sorted((metrics or {}).keys()) if r["ok"] else None
        if names is not None:
            metric_names = names if metric_names is None else sorted(set(metric_names) & set(names))
    return rows, version, metric_names or [], score_identity


# --------------------------------------------------------------------------- split


def chronological_split(rows: list[dict], test_frac: float) -> dict:
    order = sorted(range(len(rows)), key=lambda i: (float(rows[i]["t"]), str(rows[i]["row_id"])))
    n_test = max(1, int(round(test_frac * len(rows))))
    train_idx, test_idx = order[:-n_test], order[-n_test:]
    if not train_idx or not test_idx:
        raise Refused("empty_chronological_split", "chronological split needs non-empty train and test")
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
    if not train_idx or not dedup:
        raise Refused("empty_chronological_split",
                      "ties/leakage/dedup left an empty chronological train or test set")
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


def _rankdata_average(values):
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    start = 0
    while start < len(values):
        stop = start + 1
        while stop < len(values) and values[order[stop]] == values[order[start]]:
            stop += 1
        ranks[order[start:stop]] = (start + stop - 1) / 2.0
        start = stop
    return ranks


def _spearman(a, b):
    if len(a) < 3:
        return None
    ra = _rankdata_average(a)
    rb = _rankdata_average(b)
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
    te_success = [i for i in te if ok[i]]
    te_ok = []
    reg = None
    reg_ood_count = len(te_success)
    if len(tr_ok) >= 3 and te_success:
        reg = KNN(X[tr_ok], k)
        _, reg_nnd = reg.neighbours(X[te_success])
        reg_ood = reg_nnd > reg.support + 1e-12
        te_ok = [i for i, is_ood in zip(te_success, reg_ood) if not is_ood]
        reg_ood_count = int(reg_ood.sum())
    out["regression"] = {"status": "insufficient_data",
                         "n_ood_fallback": reg_ood_count}
    if len(tr_ok) >= 3 and len(te_ok) >= 3:
        assert reg is not None
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
        out["regression"] = {"status": "ok", "n_eval": len(te_ok),
                             "n_ood_fallback": reg_ood_count, "targets": per}
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
                            "predicted_j": (float(mean[j]) if in_support[j] else None),
                            "uncertainty": (float(std[j]) if in_support[j] else None),
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
        pool_path: Path | None = None, n_propose=6, advisory_stored_j=False) -> dict:
    params = {"test_frac": test_frac, "k": k, "topk": topk, "n_propose": n_propose,
              "advisory_stored_j": bool(advisory_stored_j)}
    h = hashlib.sha256(Path(rows_path).read_bytes())
    if pool_path:
        h.update(Path(pool_path).read_bytes())
    h.update(json.dumps({"tool": TOOL, "schema_version": SCHEMA_VERSION,
                         "code_version": CODE_VERSION, "params": params},
                        sort_keys=True).encode())
    key = h.hexdigest()
    out_dir = Path(out_dir)
    try:
        _guard_out(out_dir)
    except Refused as exc:
        return {"tool": TOOL, "schema_version": SCHEMA_VERSION, "code_version": CODE_VERSION,
                "input_key": key, "status": "refused", "reason": exc.reason,
                "detail": exc.detail, "complete": True, "advisory_only": True,
                "changes_defaults": False, "resumed": False, "path": None}
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
    payload = {"tool": TOOL, "schema_version": SCHEMA_VERSION, "code_version": CODE_VERSION,
               "input_key": key, "params": params,
               "advisory_only": True, "changes_defaults": False, "resumed": False,
               "stale_partial_replaced": stale_partial, "input": {"rows": str(rows_path),
                                                                    "pool": str(pool_path) if pool_path else None}}
    try:
        rows, version, metric_names, score_identity = _validate(
            load_rows(rows_path), advisory_stored_j=advisory_stored_j)
        split = chronological_split(rows, test_frac)
        evaluation, _ = _fit_eval(rows, split, metric_names, k, topk)
        pool = load_rows(pool_path) if pool_path else None
        payload.update(status="ok", objective_version=version, metric_names=metric_names,
                       validation_mode=("advisory_stored_j" if advisory_stored_j else "legacy_capability"),
                       score_identity=score_identity,
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
    ap.add_argument("--advisory-stored-j", action="store_true",
                    help="v4-only: validate exact stored J labels under one resolved score identity")
    a = ap.parse_args(argv)
    if not 0.05 <= a.test_frac <= 0.5:
        ap.error("--test-frac must be in [0.05, 0.5]")
    p = run(Path(a.rows), Path(a.out), test_frac=a.test_frac, k=a.k, topk=a.topk,
            pool_path=Path(a.pool) if a.pool else None, n_propose=a.n_propose,
            advisory_stored_j=a.advisory_stored_j)
    print(f"surrogate_validation {p['status']}"
          + (f" ({p.get('reason')})" if p["status"] != "ok" else "") + " [advisory only]")
    return 0 if p["status"] == "ok" else 3


if __name__ == "__main__":
    sys.exit(main())




