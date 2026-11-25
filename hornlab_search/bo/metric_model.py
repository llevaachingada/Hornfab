"""Multi-output metric-composite GP fit and posterior prediction (Pass 1).

The engine fits one independent :class:`botorch.models.SingleTaskGP` per canonical scoring
component and wraps the fitted models in a :class:`botorch.models.ModelListGP`.  The ADR policy
(``metric_composite_v1``) is:

* Matérn-5/2 ARD ``ScaleKernel``, ``ConstantMean``, CPU ``float64``, at most two Torch threads;
* deterministic seed per output;
* per-output ``Standardize`` for non-constant outputs, with a fixed observation noise
  ``max(1e-6 * sample_variance, 1e-5)`` in **original** contribution units;
* constant/zero-variance outputs are not standardised: they use a fixed small noise and a
  deliberately flat, near-zero-slope posterior that contributes no directional acquisition signal.

Torch/BoTorch/GPyTorch are imported lazily inside the functions so importing this module (or
``hornlab_search.bo``) never requires the optional engine.

Failure never fabricates a prediction.  Every structural, import, optimiser, hyperparameter or
posterior failure returns :class:`~.metric_contracts.MetricModelFitResult` with
``status="unavailable"`` and a reason naming the failed output where applicable.
"""
from __future__ import annotations

import hashlib
import math
import time
import warnings
from typing import Any

import numpy as np

from .metric_artifact import validate_metric_training_artifact
from .metric_contracts import (
    METRIC_COMPOSITE_POLICY,
    MetricModelFitResult,
    MetricPrediction,
    component_names,
    sha256_json,
)
from .model import NUM_THREADS, library_versions

MODEL_POLICY = METRIC_COMPOSITE_POLICY
MODEL_POLICY_VERSION = "metric-composite-v1"

LENGTHSCALE_LOWER = 0.005
LENGTHSCALE_UPPER = 4.0
LENGTHSCALE_INIT = 0.25
OUTPUTSCALE_LOWER = 1e-3
OUTPUTSCALE_UPPER = 1e3
OUTPUTSCALE_INIT = 1.0
MEAN_INIT = 0.0
NOISE_FLOOR_MULTIPLIER = 1e-6
NOISE_FLOOR_MIN = 1e-5
CONSTANT_NOISE = 1e-5
CONSTANT_LENGTHSCALE = 1.0
CONSTANT_OUTPUTSCALE = OUTPUTSCALE_LOWER
FLAT_VARIANCE_TOL = 1e-12
FIT_MAX_ITERS = 100
JITTER_INITIAL = 1e-8
JITTER_RESET = 1e-6

STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"

REASON_OK = "ok"
REASON_INSUFFICIENT_DATA = "insufficient_data"
REASON_NONFINITE_TRAINING_DATA = "nonfinite_training_data"
REASON_INVALID_ARTIFACT = "invalid_artifact"
REASON_COMPONENT_MISMATCH = "component_mismatch"
REASON_CAPABILITY_MISSING = "capability_missing"
REASON_MODEL_UNAVAILABLE = "model_unavailable"
REASON_OUTPUT_FIT_FAILED = "output_fit_failed"
REASON_NONFINITE_POSTERIOR = "nonfinite_posterior"

PREDICTION_LABEL = (
    "model posterior prediction from independent-output GPs; not a solved acoustic result")


def _import_engine():
    """Lazily import the optional numerical stack.  Returns ``(engine, error)``."""
    try:
        import torch
        import gpytorch
        from gpytorch.constraints import Interval
        from gpytorch.kernels import MaternKernel, ScaleKernel
        from gpytorch.means import ConstantMean
        from gpytorch.mlls import ExactMarginalLogLikelihood
        from botorch.fit import fit_gpytorch_mll
        from botorch.models import ModelListGP, SingleTaskGP
        from botorch.models.transforms.outcome import Standardize
    except Exception as exc:  # noqa: BLE001 - absence of the optional engine is a capability error
        return None, f"{type(exc).__name__}: {exc}"
    return {
        "torch": torch,
        "gpytorch": gpytorch,
        "Interval": Interval,
        "MaternKernel": MaternKernel,
        "ScaleKernel": ScaleKernel,
        "ConstantMean": ConstantMean,
        "ExactMarginalLogLikelihood": ExactMarginalLogLikelihood,
        "fit_gpytorch_mll": fit_gpytorch_mll,
        "ModelListGP": ModelListGP,
        "SingleTaskGP": SingleTaskGP,
        "Standardize": Standardize,
    }, None


def _unavailable(reason: str, *, detail: str | None = None, d: int | None = None,
                 n: int | None = None, output_names: tuple[str, ...] = (),
                 per_output: tuple[dict, ...] = (), model_hash: str = "",
                 artifact_checksum: str = "", seed: int = 0, timing_s: float | None = None,
                 versions: dict | None = None,
                 warnings_seen: tuple[str, ...] = ()) -> MetricModelFitResult:
    return MetricModelFitResult(
        status=STATUS_UNAVAILABLE, reason=reason, detail=detail, model=None,
        output_names=tuple(output_names), d=d, n=n, train_X=None,
        train_ids=(), per_output=tuple(per_output), model_hash=model_hash,
        artifact_checksum=artifact_checksum,
        library_versions=(versions if versions is not None else library_versions()),
        seed=int(seed), timing_s=timing_s, warnings=tuple(warnings_seen),
        policy=MODEL_POLICY)


def _array_digest(value) -> str:
    arr = np.ascontiguousarray(np.asarray(value, dtype=np.float64))
    return hashlib.sha256(arr.tobytes()).hexdigest()


def _model_hash(X, J, Y, *, component_names_: tuple[str, ...], seed: int) -> str:
    return sha256_json({
        "policy": MODEL_POLICY,
        "version": MODEL_POLICY_VERSION,
        "seed": int(seed),
        "component_names": list(component_names_),
        "X_sha256": _array_digest(X),
        "J_sha256": _array_digest(J),
        "Y_components_sha256": _array_digest(Y),
    })


def _sample_variance(values: np.ndarray) -> float:
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    if arr.size < 2:
        return 0.0
    return float(np.var(arr, ddof=1))


def _is_constant(values: np.ndarray) -> bool:
    return _sample_variance(values) <= FLAT_VARIANCE_TOL


def _noise_original(variance: float, *, constant: bool) -> float:
    if constant:
        return float(CONSTANT_NOISE)
    return float(max(NOISE_FLOOR_MULTIPLIER * float(variance), NOISE_FLOOR_MIN))


def _extract_hyperparameters(model) -> dict:
    try:
        lengthscales = model.covar_module.base_kernel.lengthscale.detach().cpu().numpy()
        outputscale = float(model.covar_module.outputscale.detach().cpu().item())
        mean_constant = float(model.mean_module.constant.detach().cpu().item())
    except Exception:  # noqa: BLE001
        return {}
    return {
        "lengthscales": np.asarray(lengthscales, dtype=float).reshape(-1).tolist(),
        "lengthscale_bounds": [LENGTHSCALE_LOWER, LENGTHSCALE_UPPER],
        "lengthscale_init": LENGTHSCALE_INIT,
        "outputscale": outputscale,
        "outputscale_bounds": [OUTPUTSCALE_LOWER, OUTPUTSCALE_UPPER],
        "outputscale_init": OUTPUTSCALE_INIT,
        "mean_constant": mean_constant,
    }


def _extract_noise(model):
    try:
        return model.likelihood.noise.detach().cpu().numpy().reshape(-1).tolist()
    except Exception:  # noqa: BLE001
        return None


def _stdvs_sq(model):
    try:
        return float((model.outcome_transform.stdvs.detach().cpu() ** 2).sum().item())
    except Exception:  # noqa: BLE001
        return None


def _finite_hyperparameters(hyper: dict) -> bool:
    try:
        ls = np.asarray(hyper.get("lengthscales"), dtype=float)
        out = hyper.get("outputscale")
        mean = hyper.get("mean_constant")
        if out is None or mean is None:
            return False
        return bool(ls.size > 0 and np.all(np.isfinite(ls))
                    and math.isfinite(float(out)) and math.isfinite(float(mean)))
    except (TypeError, ValueError):
        return False


def _posterior_is_finite(posterior) -> bool:
    try:
        return bool(posterior.mean.isfinite().all() and posterior.variance.isfinite().all())
    except Exception:  # noqa: BLE001
        return False


def _build_constant_model(engine, X_t, y_t, *, d: int, noise: float, value: float):
    """Construct a deliberately flat single-output GP for a constant component.

    No MLL optimisation is run: a constant target has no gradient direction.  The kernel is pinned
    to a wide lengthscale and the lowest allowed outputscale so the posterior is flat and its
    contribution to the composite acquisition is non-directional.
    """
    torch = engine["torch"]
    lengthscale_constraint = engine["Interval"](LENGTHSCALE_LOWER, LENGTHSCALE_UPPER)
    covariance = engine["ScaleKernel"](
        engine["MaternKernel"](nu=2.5, ard_num_dims=int(d), lengthscale_prior=None,
                               lengthscale_constraint=lengthscale_constraint),
        outputscale_prior=None,
        outputscale_constraint=engine["Interval"](OUTPUTSCALE_LOWER, OUTPUTSCALE_UPPER),
    )
    train_Yvar = torch.full((X_t.shape[0], 1), float(noise), dtype=torch.float64)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with engine["gpytorch"].settings.min_fixed_noise(double_value=1e-12):
            model = engine["SingleTaskGP"](
                X_t, y_t, train_Yvar=train_Yvar, covar_module=covariance,
                mean_module=engine["ConstantMean"](), outcome_transform=None)
    with torch.no_grad():
        model.covar_module.base_kernel.lengthscale = CONSTANT_LENGTHSCALE
        model.covar_module.outputscale = CONSTANT_OUTPUTSCALE
        model.mean_module.constant = float(value)
    model.eval()
    return model, [f"{w.category.__name__}: {w.message}" for w in caught]


def _fit_one_output(engine, X_t, y_t, *, index: int, output_name: str, d: int, n: int,
                    seed: int, max_iters: int) -> tuple[dict, Any, tuple[str, ...]]:
    """Fit one independent SingleTaskGP, returning its provenance record and model."""
    torch = engine["torch"]
    gpytorch = engine["gpytorch"]
    y_np = y_t.detach().cpu().numpy().reshape(-1)
    variance = _sample_variance(y_np)
    constant = variance <= FLAT_VARIANCE_TOL
    noise = _noise_original(variance, constant=constant)
    output_seed = int(seed) + int(index)
    torch.manual_seed(output_seed)

    captured: list[str] = []
    record: dict = {
        "name": str(output_name),
        "index": int(index),
        "n": int(n),
        "sample_variance": variance,
        "constant": bool(constant),
        "standardized": bool(not constant),
        "noise_original": float(noise),
        "noise_transformed": None,
        "lengthscales": [],
        "outputscale": None,
        "mean_constant": None,
        "mll_value": None,
        "fit_method": ("constant_parked" if constant else "exact_mll"),
        "attempts": 0,
        "jitter": None,
        "posterior_finite": False,
        "seed": output_seed,
    }

    if constant:
        value = float(np.mean(y_np)) if y_np.size else 0.0
        model, construction_warnings = _build_constant_model(
            engine, X_t, y_t, d=d, noise=noise, value=value)
        captured.extend(construction_warnings)
        hyper = _extract_hyperparameters(model)
        if not _finite_hyperparameters(hyper):
            raise RuntimeError("constant output produced non-finite hyperparameters")
        with torch.no_grad():
            posterior = model.posterior(X_t, observation_noise=False)
            if not _posterior_is_finite(posterior):
                raise RuntimeError("constant output produced a non-finite latent posterior")
        record.update(hyper)
        record["noise_transformed"] = _extract_noise(model)
        record["posterior_finite"] = True
        record["posterior_variance_mean"] = float(
            posterior.variance.detach().cpu().numpy().mean())
        return record, model, tuple(captured)

    lengthscale_constraint = engine["Interval"](LENGTHSCALE_LOWER, LENGTHSCALE_UPPER)
    covariance = engine["ScaleKernel"](
        engine["MaternKernel"](nu=2.5, ard_num_dims=int(d), lengthscale_prior=None,
                               lengthscale_constraint=lengthscale_constraint),
        outputscale_prior=None,
        outputscale_constraint=engine["Interval"](OUTPUTSCALE_LOWER, OUTPUTSCALE_UPPER),
    )
    train_Yvar = torch.full((n, 1), float(noise), dtype=torch.float64)

    last_detail: str | None = None
    model = None
    for jitter in (JITTER_INITIAL, JITTER_RESET):
        record["jitter"] = jitter
        try:
            with warnings.catch_warnings(record=True) as construction_warnings:
                warnings.simplefilter("always")
                with gpytorch.settings.min_fixed_noise(double_value=1e-12):
                    candidate = engine["SingleTaskGP"](
                        X_t, y_t, train_Yvar=train_Yvar, covar_module=covariance,
                        mean_module=engine["ConstantMean"](),
                        outcome_transform=engine["Standardize"](m=1))
            captured.extend(f"{w.category.__name__}: {w.message}"
                            for w in construction_warnings)
            expected_noise = float(noise) / _stdvs_sq(candidate)
            if not np.allclose(_extract_noise(candidate), expected_noise,
                               rtol=1e-12, atol=0.0):
                raise RuntimeError("fixed transformed noise does not match declared variance")
            with torch.no_grad():
                candidate.covar_module.base_kernel.lengthscale = LENGTHSCALE_INIT
                candidate.covar_module.outputscale = OUTPUTSCALE_INIT
                candidate.mean_module.constant = MEAN_INIT
            mll = engine["ExactMarginalLogLikelihood"](candidate.likelihood, candidate)
            with warnings.catch_warnings(record=True) as fit_warnings:
                warnings.simplefilter("always")
                record["attempts"] += 1
                with gpytorch.settings.cholesky_jitter(jitter):
                    engine["fit_gpytorch_mll"](
                        mll,
                        optimizer_kwargs={"options": {"maxiter": int(max_iters)}},
                        max_attempts=1,
                    )
            captured.extend(f"{w.category.__name__}: {w.message}" for w in fit_warnings)
            candidate.eval()
            hyper = _extract_hyperparameters(candidate)
            if not _finite_hyperparameters(hyper):
                raise RuntimeError("fit produced non-finite hyperparameters")
            with torch.no_grad():
                posterior = candidate.posterior(X_t, observation_noise=False)
                new_mll = float(mll(candidate(*candidate.train_inputs),
                                    candidate.train_targets).detach())
            if not (_posterior_is_finite(posterior) and math.isfinite(new_mll)):
                raise RuntimeError("fit produced a non-finite posterior/MLL")
            model = candidate
            record.update(hyper)
            record["noise_transformed"] = _extract_noise(candidate)
            record["mll_value"] = new_mll
            record["posterior_finite"] = True
            record["posterior_variance_mean"] = float(
                posterior.variance.detach().cpu().numpy().mean())
            last_detail = None
            break
        except Exception as exc:  # noqa: BLE001 - retry once at the reset jitter
            last_detail = f"{type(exc).__name__}: {exc}"
            model = None
            continue

    if model is None:
        raise RuntimeError(last_detail or "exact MLL fit failed")
    return record, model, tuple(captured)


def fit_metric_model(artifact, *, seed: int = 0, max_iters: int = FIT_MAX_ITERS
                     ) -> MetricModelFitResult:
    """Fit one independent GP per component and wrap them in ``ModelListGP``.

    Returns ``status="ok"`` only when every output fits, has finite hyperparameters and produces
    a finite latent posterior.  Any other outcome is a tagged ``unavailable`` result naming the
    failed output; no zero/mean-filled model or prediction is fabricated.
    """
    started = time.perf_counter()
    versions = library_versions()

    def _fail(reason: str, detail: str, *, d=None, n=None, names=(), records=(),
              model_hash="", checksum="") -> MetricModelFitResult:
        return _unavailable(reason, detail=detail, d=d, n=n, output_names=names,
                            per_output=records, model_hash=model_hash,
                            artifact_checksum=checksum, seed=seed,
                            timing_s=time.perf_counter() - started, versions=versions)

    if artifact is None:
        return _fail(REASON_INVALID_ARTIFACT, "artifact is None")
    if getattr(artifact, "status", None) != STATUS_OK:
        return _fail(REASON_INVALID_ARTIFACT,
                     f"artifact status is {getattr(artifact, 'status', None)!r}")
    X = getattr(artifact, "X", None)
    J = getattr(artifact, "J", None)
    Y = getattr(artifact, "Y_components", None)
    if X is None or J is None or Y is None:
        return _fail(REASON_INSUFFICIENT_DATA, "artifact has no X/J/Y_components arrays")
    try:
        # Artifacts expose read-only NumPy arrays; copy the validated training arrays so Torch
        # receives writable float64 storage (avoids the undefined-behaviour warning while keeping
        # the artifact itself immutable).  Values are unchanged.
        X = np.array(X, dtype=np.float64, copy=True)
        J = np.asarray(J, dtype=np.float64)
        Y = np.array(Y, dtype=np.float64, copy=True)
    except (TypeError, ValueError) as exc:
        return _fail(REASON_INVALID_ARTIFACT, f"artifact arrays are not numeric: {exc}")
    if X.ndim != 2 or Y.ndim != 2 or X.shape[0] != Y.shape[0]:
        return _fail(REASON_INSUFFICIENT_DATA,
                     f"X/Y must be 2-D with matching rows, got X{X.shape}, Y{Y.shape}")
    n, d = int(X.shape[0]), int(X.shape[1])
    if J.size != n:
        return _fail(REASON_INSUFFICIENT_DATA,
                     f"J must have {n} entries, got shape {J.shape}", d=d, n=n)
    if n < 2:
        return _fail(REASON_INSUFFICIENT_DATA,
                     f"at least two observations are required, got n={n}", d=d, n=n)
    m = int(Y.shape[1])
    names = tuple(getattr(artifact, "component_names", ()) or ())
    if not names:
        try:
            names = tuple(component_names(int(getattr(artifact, "objective_version", 10))))
        except (TypeError, ValueError):
            names = ()
    if len(names) != m:
        return _fail(REASON_COMPONENT_MISMATCH,
                     f"artifact names {names!r} do not match Y_components columns m={m}",
                     d=d, n=n, names=names)
    if not np.all(np.isfinite(X)):
        return _fail(REASON_NONFINITE_TRAINING_DATA, "X contains NaN/Inf", d=d, n=n,
                     names=names)
    if np.any((X < 0.0) | (X > 1.0)):
        return _fail(REASON_INVALID_ARTIFACT, "X contains values outside [0,1]", d=d, n=n,
                     names=names)
    J_col = J.reshape(-1, 1)
    if not np.all(np.isfinite(J_col)):
        return _fail(REASON_NONFINITE_TRAINING_DATA, "J contains NaN/Inf", d=d, n=n,
                     names=names)
    for i, name in enumerate(names):
        if not np.all(np.isfinite(Y[:, i])):
            return _fail(f"{REASON_NONFINITE_TRAINING_DATA}:{name}",
                         f"component output {name!r} contains NaN/Inf", d=d, n=n,
                         names=names)
    # Artifact integrity gate: checksum (when present) + arrays + per-row J reconstruction +
    # component schema + recorded bounds/score payloads.  Runs before any Torch import/fit, so a
    # corrupt artifact can never be fitted; a mismatch is a tagged refusal, never repaired.
    artifact_check = validate_metric_training_artifact(artifact)
    if not artifact_check.ok:
        return _fail(artifact_check.reason or REASON_INVALID_ARTIFACT,
                     f"artifact integrity check failed: {artifact_check.reason}"
                     + (f": {artifact_check.detail}" if artifact_check.detail else ""),
                     d=d, n=n, names=names)
    overall_hash = _model_hash(X, J_col, Y, component_names_=names, seed=seed)
    checksum = str(getattr(artifact, "checksum", "") or "")
    train_ids = tuple(str(v) for v in (getattr(artifact, "observation_ids", ()) or ()))

    engine, import_error = _import_engine()
    if engine is None:
        return _fail(REASON_CAPABILITY_MISSING,
                     f"optional BoTorch engine is unavailable: {import_error}",
                     d=d, n=n, names=names, model_hash=overall_hash, checksum=checksum)

    torch = engine["torch"]
    try:
        torch.set_num_threads(NUM_THREADS)
    except Exception:  # noqa: BLE001 - thread pinning is best-effort
        pass
    X_t = torch.as_tensor(X, dtype=torch.float64)
    models = []
    records: list[dict] = []
    all_warnings: list[str] = []
    for i, name in enumerate(names):
        y_t = torch.as_tensor(Y[:, i:i + 1], dtype=torch.float64)
        try:
            record, output_model, warnings_seen = _fit_one_output(
                engine, X_t, y_t, index=i, output_name=name, d=d, n=n, seed=int(seed),
                max_iters=int(max_iters))
        except Exception as exc:  # noqa: BLE001 - never let an output failure escape
            return _fail(f"{REASON_OUTPUT_FIT_FAILED}:{name}",
                         f"component output {name!r} failed: {type(exc).__name__}: {exc}",
                         d=d, n=n, names=names, records=tuple(records),
                         model_hash=overall_hash, checksum=checksum)
        records.append(record)
        models.append(output_model)
        all_warnings.extend(warnings_seen)

    try:
        model = engine["ModelListGP"](*models)
        model.eval()
    except Exception as exc:  # noqa: BLE001
        return _fail(REASON_MODEL_UNAVAILABLE,
                     f"ModelListGP construction failed: {type(exc).__name__}: {exc}",
                     d=d, n=n, names=names, records=tuple(records),
                     model_hash=overall_hash, checksum=checksum)

    # A final all-output latent posterior check before the model is published.
    try:
        with torch.no_grad():
            posterior = model.posterior(X_t, observation_noise=False)
            mean = posterior.mean.detach().cpu().numpy()
            variance = posterior.variance.detach().cpu().numpy()
        if mean.shape != (n, m) or variance.shape != (n, m):
            raise RuntimeError(f"posterior shapes {mean.shape}/{variance.shape} != {(n, m)}")
        if not (np.all(np.isfinite(mean)) and np.all(np.isfinite(variance))):
            raise RuntimeError("posterior contains NaN/Inf")
    except Exception as exc:  # noqa: BLE001
        return _fail(REASON_NONFINITE_POSTERIOR,
                     f"combined latent posterior failed: {type(exc).__name__}: {exc}",
                     d=d, n=n, names=names, records=tuple(records),
                     model_hash=overall_hash, checksum=checksum)

    return MetricModelFitResult(
        status=STATUS_OK, reason=REASON_OK, detail=None, model=model,
        output_names=names, d=d, n=n, train_X=np.array(X, dtype=np.float64, copy=True),
        train_ids=train_ids, per_output=tuple(records), model_hash=overall_hash,
        artifact_checksum=checksum, library_versions=versions, seed=int(seed),
        timing_s=time.perf_counter() - started, warnings=tuple(all_warnings),
        policy=MODEL_POLICY)


def predict_metric_components(model_result, X) -> MetricPrediction:
    """Predict component means/SDs and composite ``J`` from the independent-output posterior.

    ``j_mean = sum(component_mean)`` and ``j_sd = sqrt(sum(component_variance))`` under the
    explicit independent-output assumption.  Values are never clamped; non-finite or
    nonphysical outcomes are flagged.
    """
    if model_result is None or getattr(model_result, "status", None) != STATUS_OK \
            or getattr(model_result, "model", None) is None:
        return MetricPrediction(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                detail="no fitted metric model")
    engine, import_error = _import_engine()
    if engine is None:
        return MetricPrediction(status=STATUS_UNAVAILABLE, reason=REASON_CAPABILITY_MISSING,
                                detail=f"optional BoTorch engine is unavailable: {import_error}")
    torch = engine["torch"]
    try:
        arr = np.asarray(X, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        expected_d = int(getattr(model_result, "d", 0) or 0)
        if arr.ndim != 2 or (expected_d and arr.shape[1] != expected_d):
            return MetricPrediction(status=STATUS_UNAVAILABLE,
                                    reason=REASON_INSUFFICIENT_DATA,
                                    detail=f"unexpected candidate shape {arr.shape}")
        if not np.all(np.isfinite(arr)):
            return MetricPrediction(status=STATUS_UNAVAILABLE,
                                    reason=REASON_NONFINITE_TRAINING_DATA,
                                    detail="candidate X contains NaN/Inf")
        try:
            torch.set_num_threads(NUM_THREADS)
        except Exception:  # noqa: BLE001
            pass
        with torch.no_grad():
            posterior = model_result.model.posterior(
                torch.as_tensor(arr, dtype=torch.float64), observation_noise=False)
            mean = posterior.mean.detach().cpu().numpy()
            variance = posterior.variance.clamp_min(0.0).detach().cpu().numpy()
    except Exception as exc:  # noqa: BLE001 - a failed posterior is a tagged unavailability
        return MetricPrediction(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                detail=f"posterior failed: {type(exc).__name__}: {exc}")

    m = len(getattr(model_result, "output_names", ()) or ())
    if mean.ndim == 1:
        mean = mean.reshape(-1, 1)
    if variance.ndim == 1:
        variance = variance.reshape(-1, 1)
    if m and (mean.shape[1] != m or variance.shape != mean.shape):
        return MetricPrediction(status=STATUS_UNAVAILABLE, reason=REASON_COMPONENT_MISMATCH,
                                detail=f"posterior shape {mean.shape} does not match m={m}")
    if mean.shape[0] != arr.shape[0]:
        return MetricPrediction(status=STATUS_UNAVAILABLE, reason=REASON_INSUFFICIENT_DATA,
                                detail=f"posterior rows {mean.shape[0]} != candidates "
                                       f"{arr.shape[0]}")

    component_sd = np.sqrt(np.maximum(variance, 0.0))
    j_mean = np.sum(mean, axis=1)
    j_sd = np.sqrt(np.sum(np.maximum(variance, 0.0), axis=1))

    flags: list[str] = []
    if not (np.all(np.isfinite(mean)) and np.all(np.isfinite(component_sd))
            and np.all(np.isfinite(j_mean)) and np.all(np.isfinite(j_sd))):
        flags.append("nonfinite_prediction")
    if np.any(j_mean < 0.0):
        flags.append("nonphysical_predicted_J_negative")
    if np.any(mean < 0.0):
        flags.append("negative_component_mean")
    return MetricPrediction(
        status=STATUS_OK, reason=REASON_OK, detail=PREDICTION_LABEL,
        component_mean=mean, component_sd=component_sd, j_mean=j_mean, j_sd=j_sd,
        flags=tuple(flags), observation_noise=False)


__all__ = [
    "MODEL_POLICY",
    "MODEL_POLICY_VERSION",
    "LENGTHSCALE_LOWER",
    "LENGTHSCALE_UPPER",
    "LENGTHSCALE_INIT",
    "OUTPUTSCALE_LOWER",
    "OUTPUTSCALE_UPPER",
    "OUTPUTSCALE_INIT",
    "MEAN_INIT",
    "NOISE_FLOOR_MULTIPLIER",
    "NOISE_FLOOR_MIN",
    "CONSTANT_NOISE",
    "FLAT_VARIANCE_TOL",
    "FIT_MAX_ITERS",
    "JITTER_INITIAL",
    "JITTER_RESET",
    "STATUS_OK",
    "STATUS_UNAVAILABLE",
    "REASON_OK",
    "REASON_INSUFFICIENT_DATA",
    "REASON_NONFINITE_TRAINING_DATA",
    "REASON_INVALID_ARTIFACT",
    "REASON_COMPONENT_MISMATCH",
    "REASON_CAPABILITY_MISSING",
    "REASON_MODEL_UNAVAILABLE",
    "REASON_OUTPUT_FIT_FAILED",
    "REASON_NONFINITE_POSTERIOR",
    "PREDICTION_LABEL",
    "fit_metric_model",
    "predict_metric_components",
]
