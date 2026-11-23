"""Synthetic model-comparison diagnostics for the metric-composite research lane.

The comparison fits the same synthetic train/test data and the same seeds to four arms:

* ``A_scalar``        — one GP on scalar ``J``;
* ``B_two_component`` — two-component composite;
* ``C_v10_four``      — four-component v10-shaped composite;
* ``D_v11_six``       — six-component v11-shaped composite.

An optional correlated-output arm ``E_correlated`` is documented but not implemented; this module
does not claim to test it.

The landscapes are synthetic and fixed.  They are **not tuned to make a composite arm win**: a
scalar win is a legitimate, recorded finding.  Metrics are pure functions (MAE, RMSE, Spearman
rank correlation, top-decile recall, empirical interval coverage, prediction bias) plus timing,
candidate-selection disagreement and numerical-failure counts.

Coverage is reported as the **empirical coverage of model intervals**, explicitly not a calibrated
uncertainty claim.  No acoustic improvement is claimed: all outputs are synthetic.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np

RESEARCH_POLICY = "synthetic_model_comparison_research_v1"
RESEARCH_ONLY = True
Z_INTERVAL = 1.96
COVERAGE_LABEL = "empirical coverage of model intervals; not calibrated"
STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"

ARM_NAMES = ("A_scalar", "B_two_component", "C_v10_four", "D_v11_six")
ARM_COMPONENT_COUNTS = {"A_scalar": 1, "B_two_component": 2, "C_v10_four": 4, "D_v11_six": 6}
ARM_LABELS = {
    "A_scalar": "single scalar GP on J",
    "B_two_component": "two-component composite",
    "C_v10_four": "four-component v10-shaped composite",
    "D_v11_six": "six-component v11-shaped composite",
}
OPTIONAL_ARM_NOT_IMPLEMENTED = "E_correlated"

LANDSCAPE_NAMES = (
    "approximately_additive",
    "correlated_outputs",
    "independent_outputs",
    "constant_contribution",
    "multiple_basins",
    "strong_local_concentration",
    "different_length_scales",
    "different_magnitudes",
)


# ---------------------------------------------------------------------------- pure metrics


def _paired(pred, true) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(pred, dtype=np.float64).reshape(-1)
    t = np.asarray(true, dtype=np.float64).reshape(-1)
    if p.size != t.size:
        raise ValueError(f"prediction/truth sizes differ: {p.size} vs {t.size}")
    mask = np.isfinite(p) & np.isfinite(t)
    return p[mask], t[mask]


def mae(pred, true) -> float | None:
    p, t = _paired(pred, true)
    return None if p.size == 0 else float(np.mean(np.abs(p - t)))


def rmse(pred, true) -> float | None:
    p, t = _paired(pred, true)
    return None if p.size == 0 else float(np.sqrt(np.mean((p - t) ** 2)))


def prediction_bias(pred, true) -> float | None:
    p, t = _paired(pred, true)
    return None if p.size == 0 else float(np.mean(p - t))


def _ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    ranks[order] = np.arange(1, values.size + 1, dtype=np.float64)
    # average ties
    sorted_vals = values[order]
    i = 0
    while i < sorted_vals.size:
        j = i + 1
        while j < sorted_vals.size and sorted_vals[j] == sorted_vals[i]:
            j += 1
        if j - i > 1:
            ranks[order[i:j]] = (i + 1 + j) / 2.0
        i = j
    return ranks


def spearman_rank(pred, true) -> float | None:
    p, t = _paired(pred, true)
    if p.size < 3:
        return None
    rp, rt = _ranks(p), _ranks(t)
    dp, dt = rp - rp.mean(), rt - rt.mean()
    denom = math.sqrt(float(dp @ dp) * float(dt @ dt))
    if not denom > 0.0:
        return None
    return float((dp @ dt) / denom)


def top_decile_recall(pred, true, *, fraction: float = 0.1) -> float | None:
    """Overlap between the predicted-best and true-best sets (lower is better)."""
    p, t = _paired(pred, true)
    n = p.size
    if n < 10:
        return None
    k = max(1, int(math.ceil(float(fraction) * n)))
    true_best = set(np.argsort(t, kind="mergesort")[:k].tolist())
    pred_best = set(np.argsort(p, kind="mergesort")[:k].tolist())
    return float(len(true_best & pred_best) / k)


def empirical_coverage(pred_mean, pred_sd, true, *, z: float = Z_INTERVAL) -> float | None:
    m = np.asarray(pred_mean, dtype=np.float64).reshape(-1)
    t = np.asarray(true, dtype=np.float64).reshape(-1)
    s = np.asarray(pred_sd, dtype=np.float64).reshape(-1)
    if not (m.size == t.size == s.size):
        raise ValueError("pred_mean, pred_sd and true must have the same size")
    mask = np.isfinite(m) & np.isfinite(t) & np.isfinite(s)
    m, t, s = m[mask], t[mask], s[mask]
    if m.size == 0:
        return None
    with np.errstate(invalid="ignore"):
        covered = np.abs(t - m) <= float(z) * np.maximum(s, 0.0)
    return float(np.mean(covered))


# ---------------------------------------------------------------------------- landscapes


def _p(parts: Sequence[np.ndarray]) -> tuple[np.ndarray, ...]:
    return tuple(np.asarray(v, dtype=np.float64).reshape(-1) for v in parts)


def _approximately_additive(X):
    x0, x1, x2 = X[:, 0], X[:, 1], X[:, 2 % X.shape[1]]
    return _p([
        0.20 + 0.30 * x0,
        0.15 + 0.25 * x1,
        0.10 + 0.20 * x2 + 0.02 * x0 * x1,
        0.05 + 0.10 * x0 ** 2,
        0.05 + 0.05 * np.sin(2.0 * x1),
    ])


def _correlated_outputs(X):
    f = X[:, 0] + 0.5 * X[:, 1]
    g = X[:, 0] * X[:, 1]
    return _p([
        0.20 + 0.40 * f,
        0.10 + 0.20 * f,
        0.05 + 0.10 * f ** 2,
        0.05 + 0.05 * g,
        0.05 + 0.02 * f,
    ])


def _independent_outputs(X):
    x0, x1, x2 = X[:, 0], X[:, 1], X[:, 2 % X.shape[1]]
    return _p([
        0.10 + 0.25 * np.sin(2.0 * np.pi * x0) ** 2,
        0.25 + 0.30 * np.cos(3.0 * np.pi * x1) ** 2,
        0.10 + 0.20 * x2 ** 2,
        0.10 + 0.10 * np.exp(-((x0 - 0.3) ** 2) / 0.05),
        0.10 + 0.08 * np.abs(np.sin(4.0 * np.pi * x1)),
    ])


def _constant_contribution(X):
    x0, x1 = X[:, 0], X[:, 1]
    return _p([
        np.full(X.shape[0], 0.25),
        0.15 + 0.25 * x0,
        0.10 + 0.15 * x1,
        0.05 + 0.10 * x0 * x1,
        0.05 + 0.05 * x0 ** 2,
    ])


def _multiple_basins(X):
    x0, x1 = X[:, 0], X[:, 1]
    return _p([
        0.20 + 0.50 * np.sin(3.0 * np.pi * x0) ** 2,
        0.20 + 0.50 * np.sin(3.0 * np.pi * x1 + 0.4) ** 2,
        0.10 + 0.20 * np.cos(2.0 * np.pi * x0 * x1) ** 2,
        0.05 + 0.10 * x0,
        0.05 + 0.10 * x1,
    ])


def _strong_local_concentration(X):
    x0, x1, x2 = X[:, 0], X[:, 1], X[:, 2 % X.shape[1]]
    return _p([
        0.80 * np.exp(-((x0 - 0.20) ** 2) / (2.0 * 0.03 ** 2)),
        0.70 * np.exp(-((x1 - 0.70) ** 2) / (2.0 * 0.04 ** 2)),
        0.20 * np.exp(-((x2 - 0.50) ** 2) / (2.0 * 0.06 ** 2)),
        0.05 + 0.05 * x0,
        0.05 + 0.05 * x1,
    ])


def _different_length_scales(X):
    x0, x1, x2 = X[:, 0], X[:, 1], X[:, 2 % X.shape[1]]
    return _p([
        0.10 + 0.40 * x0,
        0.10 + 0.30 * np.sin(12.0 * np.pi * x1) ** 2,
        0.10 + 0.20 * x2,
        0.05 + 0.20 * np.sin(20.0 * np.pi * x0) ** 2,
        0.05 + 0.05 * x1,
    ])


def _different_magnitudes(X):
    x0, x1, x2 = X[:, 0], X[:, 1], X[:, 2 % X.shape[1]]
    return _p([
        2.00 + 0.50 * x0,
        0.20 + 0.05 * x1,
        0.02 + 0.01 * x2,
        0.10 + 0.02 * x0 * x1,
        0.05 + 0.01 * x1 ** 2,
    ])


_LANDSCAPE_FUNCTIONS: dict[str, Callable[[np.ndarray], tuple[np.ndarray, ...]]] = {
    "approximately_additive": _approximately_additive,
    "correlated_outputs": _correlated_outputs,
    "independent_outputs": _independent_outputs,
    "constant_contribution": _constant_contribution,
    "multiple_basins": _multiple_basins,
    "strong_local_concentration": _strong_local_concentration,
    "different_length_scales": _different_length_scales,
    "different_magnitudes": _different_magnitudes,
}


def landscape_components(name: str, X) -> tuple[np.ndarray, ...]:
    """Five explicit non-negative parts for a named synthetic landscape."""
    try:
        fn = _LANDSCAPE_FUNCTIONS[str(name)]
    except KeyError as exc:
        raise ValueError(f"unknown synthetic landscape {name!r}; known: {LANDSCAPE_NAMES}") from exc
    arr = np.asarray(X, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError(f"X must be 2-D with at least two columns, got {arr.shape}")
    parts = _LANDSCAPE_FUNCTIONS[str(name)](arr)
    if not all(np.all(np.isfinite(p)) for p in parts):
        raise ValueError(f"landscape {name!r} produced a non-finite part")
    return parts


def arm_component_matrix(arm: str, X, *, landscape: str = "approximately_additive"
                          ) -> tuple[np.ndarray, np.ndarray]:
    """True ``J`` and the arm-specific component matrix whose rows sum to J."""
    return _arm_matrix(str(arm), str(landscape), X)


def _arm_matrix(arm: str, landscape: str, X) -> tuple[np.ndarray, np.ndarray]:
    parts = landscape_components(landscape, X)
    J = np.sum(np.column_stack(parts), axis=1)
    m = ARM_COMPONENT_COUNTS[arm]
    explicit = list(parts[:m - 1])
    last = J - np.sum(np.column_stack(explicit), axis=1) if explicit else J
    return J, np.column_stack(explicit + [last])


# ---------------------------------------------------------------------------- comparison engine


@dataclass(frozen=True)
class SyntheticComparisonResult:
    status: str
    reason: str
    detail: str | None = None
    landscapes: tuple[str, ...] = ()
    arms: tuple[str, ...] = ARM_NAMES
    per_landscape: tuple[dict, ...] = ()
    aggregate: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    limitations: str = (
        "Synthetic landscapes only. Coverage is empirical coverage of model intervals and is "
        "explicitly not calibrated. No acoustic improvement is claimed. The correlated-output "
        "arm E is not implemented.")
    research_only: bool = RESEARCH_ONLY
    policy: str = RESEARCH_POLICY
    timing_s: float | None = None

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "landscapes": list(self.landscapes),
            "arms": list(self.arms),
            "per_landscape": [dict(v) for v in self.per_landscape],
            "aggregate": dict(self.aggregate),
            "config": dict(self.config),
            "limitations": self.limitations,
            "research_only": bool(self.research_only),
            "policy": self.policy,
            "timing_s": self.timing_s,
        }


def _fit_outputs(X_train, Y_train, names, *, seed: int, max_iters: int):
    """Fit one independent GP per output using the shared metric_model patterns.

    The research comparison deliberately does not build a ``metric-training-v1`` artifact: arm A
    has a single scalar output and arm B two outputs, neither of which is a frozen component
    schema.  The GP construction, per-output standardisation, noise floor and failure tagging are
    the production ``metric_model`` helpers.
    """
    from . import metric_model
    from .metric_contracts import MetricModelFitResult

    engine, import_error = metric_model._import_engine()
    if engine is None:
        return None, f"capability_missing: {import_error}"
    torch = engine["torch"]
    try:
        from .model import NUM_THREADS, library_versions
        torch.set_num_threads(NUM_THREADS)
        versions = library_versions()
    except Exception:  # noqa: BLE001
        versions = {}
    X = np.array(X_train, dtype=np.float64, copy=True)
    Y = np.array(Y_train, dtype=np.float64, copy=True)
    n, d = int(X.shape[0]), int(X.shape[1])
    X_t = torch.as_tensor(X, dtype=torch.float64)
    models = []
    records: list[dict] = []
    warnings_seen: list[str] = []
    for i, name in enumerate(names):
        y_t = torch.as_tensor(Y[:, i:i + 1], dtype=torch.float64)
        try:
            record, output_model, seen = metric_model._fit_one_output(
                engine, X_t, y_t, index=i, output_name=str(name), d=d, n=n,
                seed=int(seed), max_iters=int(max_iters))
        except Exception as exc:  # noqa: BLE001 - a failed arm is a recorded numerical failure
            return None, f"output_fit_failed:{name}: {type(exc).__name__}: {exc}"
        records.append(record)
        models.append(output_model)
        warnings_seen.extend(seen)
    model = engine["ModelListGP"](*models)
    model.eval()
    return MetricModelFitResult(
        status="ok", reason="ok", model=model, output_names=tuple(names), d=d, n=n,
        train_X=X, per_output=tuple(records), library_versions=versions, seed=int(seed),
        policy="synthetic_model_comparison"), None


def _run_arm(arm: str, X_train, Y_train, X_test, true_J_test, *, seed: int,
             max_iters: int) -> dict:
    from .metric_model import predict_metric_components

    m = ARM_COMPONENT_COUNTS[arm]
    names = tuple(f"component_{i}" for i in range(m)) if arm != "A_scalar" else ("J",)
    started = time.perf_counter()
    fit, error = _fit_outputs(X_train, Y_train, names, seed=int(seed), max_iters=int(max_iters))
    fit_s = float(time.perf_counter() - started)
    record = {
        "arm": arm, "components": m, "status": "unavailable", "reason": "",
        "mae": None, "rmse": None, "spearman": None, "top_decile_recall": None,
        "coverage": None, "coverage_label": COVERAGE_LABEL, "bias": None,
        "fit_time_s": fit_s, "acquisition_time_s": None, "total_cpu_s": None,
        "predicted_best_index": None, "numerical_failures": 1,
    }
    if fit is None:
        record["reason"] = str(error or "fit_failed")
        return record
    acq_started = time.perf_counter()
    pred = predict_metric_components(fit, X_test)
    acq_s = time.perf_counter() - acq_started
    record["acquisition_time_s"] = acq_s
    record["total_cpu_s"] = fit_s + acq_s
    if getattr(pred, "status", None) != "ok" or pred.j_mean is None:
        record["reason"] = str(getattr(pred, "reason", "prediction_failed"))
        return record
    pred_J = np.asarray(pred.j_mean, dtype=np.float64).reshape(-1)
    record.update({
        "status": "ok", "reason": "ok",
        "mae": mae(pred_J, true_J_test),
        "rmse": rmse(pred_J, true_J_test),
        "spearman": spearman_rank(pred_J, true_J_test),
        "top_decile_recall": top_decile_recall(pred_J, true_J_test),
        "coverage": empirical_coverage(pred_J, pred.j_sd, true_J_test),
        "bias": prediction_bias(pred_J, true_J_test),
        "predicted_best_index": int(np.argmin(pred_J)),
        "numerical_failures": 0,
    })
    return record


def _mean_of(values: Sequence[float | None]) -> float | None:
    finite = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return float(np.mean(finite)) if finite else None


def run_synthetic_model_comparison(*, landscapes: Sequence[str] | None = None, n_train: int = 48,
                                   n_test: int = 20, d: int = 3, seed: int = 7,
                                   max_iters: int = 40) -> SyntheticComparisonResult:
    """Fit the four arms on identical synthetic data and record the actual outcome.

    The same ``X_train``/``X_test`` and the same seed are used for every arm and landscape.  No
    landscape is tuned to favour a composite arm.  The result records a scalar win as-is.
    """
    started = time.perf_counter()
    names = tuple(LANDSCAPE_NAMES if landscapes is None else landscapes)
    unknown = [n for n in names if n not in _LANDSCAPE_FUNCTIONS]
    if unknown:
        return SyntheticComparisonResult(
            status=STATUS_UNAVAILABLE, reason="unknown_landscape",
            detail=f"unknown landscapes {unknown!r}", landscapes=names,
            timing_s=time.perf_counter() - started)
    if int(n_train) < 8 or int(n_test) < 10 or int(d) < 2:
        return SyntheticComparisonResult(
            status=STATUS_UNAVAILABLE, reason="invalid_config",
            detail="need n_train >= 8, n_test >= 10 and d >= 2",
            landscapes=names, timing_s=time.perf_counter() - started)

    rng = np.random.default_rng(int(seed))
    X_train = rng.random((int(n_train), int(d)))
    X_test = rng.random((int(n_test), int(d)))

    per_landscape: list[dict] = []
    for landscape in names:
        true_J, _ = _arm_matrix("A_scalar", landscape, X_test)
        arm_records: dict[str, dict] = {}
        for arm in ARM_NAMES:
            _, Y_train = _arm_matrix(arm, landscape, X_train)
            arm_records[arm] = _run_arm(arm, X_train, Y_train, X_test, true_J,
                                        seed=int(seed), max_iters=int(max_iters))
        scalar_best = arm_records["A_scalar"]["predicted_best_index"]
        for arm, record in arm_records.items():
            if scalar_best is None or record["predicted_best_index"] is None:
                record["candidate_selection_disagreement"] = None
            else:
                record["candidate_selection_disagreement"] = int(
                    record["predicted_best_index"] != scalar_best)
        per_landscape.append({"landscape": landscape, "arms": arm_records,
                              "true_J_range": [float(np.min(true_J)), float(np.max(true_J))]})

    aggregate: dict[str, dict] = {}
    for arm in ARM_NAMES:
        records = [entry["arms"][arm] for entry in per_landscape]
        ok_records = [r for r in records if r["status"] == "ok"]
        disagreements = [r["candidate_selection_disagreement"] for r in records
                         if r.get("candidate_selection_disagreement") is not None]
        aggregate[arm] = {
            "label": ARM_LABELS[arm],
            "components": ARM_COMPONENT_COUNTS[arm],
            "n_landscapes": len(records),
            "n_ok": len(ok_records),
            "numerical_failures": int(sum(int(r.get("numerical_failures", 1)) for r in records)),
            "mae": _mean_of([r["mae"] for r in records]),
            "rmse": _mean_of([r["rmse"] for r in records]),
            "spearman": _mean_of([r["spearman"] for r in records]),
            "top_decile_recall": _mean_of([r["top_decile_recall"] for r in records]),
            "coverage": _mean_of([r["coverage"] for r in records]),
            "coverage_label": COVERAGE_LABEL,
            "bias": _mean_of([r["bias"] for r in records]),
            "fit_time_s": float(sum(float(r.get("fit_time_s") or 0.0) for r in records)),
            "acquisition_time_s": float(sum(float(r.get("acquisition_time_s") or 0.0)
                                            for r in records)),
            "total_cpu_s": float(sum(float(r.get("total_cpu_s") or 0.0) for r in records)),
            "candidate_selection_disagreement_rate": (
                float(np.mean(disagreements)) if disagreements else None),
        }

    status = STATUS_OK if any(v["n_ok"] > 0 for v in aggregate.values()) else STATUS_UNAVAILABLE
    return SyntheticComparisonResult(
        status=status, reason="ok" if status == STATUS_OK else "all_arms_failed",
        detail=None, landscapes=names, per_landscape=tuple(per_landscape), aggregate=aggregate,
        config={"n_train": int(n_train), "n_test": int(n_test), "d": int(d),
                "seed": int(seed), "max_iters": int(max_iters), "z_interval": Z_INTERVAL,
                "optional_arm_not_implemented": OPTIONAL_ARM_NOT_IMPLEMENTED},
        timing_s=time.perf_counter() - started)


__all__ = [
    "RESEARCH_POLICY",
    "RESEARCH_ONLY",
    "Z_INTERVAL",
    "COVERAGE_LABEL",
    "ARM_NAMES",
    "ARM_COMPONENT_COUNTS",
    "ARM_LABELS",
    "OPTIONAL_ARM_NOT_IMPLEMENTED",
    "LANDSCAPE_NAMES",
    "mae",
    "rmse",
    "prediction_bias",
    "spearman_rank",
    "top_decile_recall",
    "empirical_coverage",
    "landscape_components",
    "arm_component_matrix",
    "SyntheticComparisonResult",
    "run_synthetic_model_comparison",
]
