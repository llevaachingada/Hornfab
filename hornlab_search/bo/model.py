"""Locked scalar-pool v1 BoTorch model (B3, protocol bo-study-v1.1).

Minimise the frozen scalar objective ``J`` by modelling ``Y = -J`` with a single-output
``SingleTaskGP`` and the locked kernel/mean/outcome-transform policy of spec section 3.3:

* ``SingleTaskGP`` + ``ConstantMean`` (starts at 0) +
  ``ScaleKernel(MaternKernel(nu=2.5, ard_num_dims=d))`` + ``Standardize(m=1)``;
* lengthscale bounds ``[0.005, 4]``, initial ``0.25``; outputscale bounds ``[1e-3, 1e3]``,
  initial ``1``; no custom priors;
* fixed ``train_Yvar = 1e-6 * s2`` in the **original** output-squared units, where ``s2`` is the
  sample variance of ``J``; ``Standardize`` transforms the variance along with the values;
* one exact-MLL attempt, at most 100 optimiser iterations, Cholesky jitter ``1e-8`` with a single
  ``1e-6`` reset;
* ``float64`` CPU tensors, at most two Torch threads, never ``.cuda()``.

BoTorch/GPyTorch/Torch are imported **lazily inside the functions**.  Importing
``hornlab_search.bo`` (or this module) never imports the optional engine; callers get a tagged
``capability_missing`` result instead.

Failure never fabricates a prediction: a failed gate/fit returns a :class:`ModelFitResult` with
``status="unavailable"`` and an explicit reason code.  Predicted ``J`` is minus the posterior mean
of ``Y``; the credible interval endpoints are reversed correctly and labelled a *model credible
interval*, not a physical tolerance.
"""
from __future__ import annotations

import math
import time
import warnings
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np

MODEL_POLICY = "scalar_pool_v1"
MODEL_POLICY_VERSION = "scalar-pool-v1"

#: Locked numeric policy (spec 3.3).  Do not substitute another method.
LENGTHSCALE_LOWER = 0.005
LENGTHSCALE_UPPER = 4.0
LENGTHSCALE_INIT = 0.25
OUTPUTSCALE_LOWER = 1e-3
OUTPUTSCALE_UPPER = 1e3
OUTPUTSCALE_INIT = 1.0
MEAN_INIT = 0.0
NOISE_FLOOR_MULTIPLIER = 1e-6
FLAT_VARIANCE_TOL = 1e-12
FIT_MAX_ITERS = 100
JITTER_INITIAL = 1e-8
JITTER_RESET = 1e-6
NUM_THREADS = 2
CREDIBLE_Z = 1.96

REASON_OK = "ok"
REASON_NEEDS_INITIAL_DATA = "needs_initial_data"
REASON_INSUFFICIENT_DATA = "insufficient_data"
REASON_NONFINITE_TRAINING_DATA = "nonfinite_training_data"
REASON_FLAT_TRAINING_RESPONSE = "flat_training_response"
REASON_MODEL_UNAVAILABLE = "model_unavailable"
REASON_CAPABILITY_MISSING = "capability_missing"
REASON_UNSUPPORTED_MODEL_POLICY = "unsupported_model_policy"

STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"

INTERVAL_LABEL = (
    "model credible interval: marginal mu +/- 1.96*sigma from the latent posterior "
    "(observation_noise=False); not a physical tolerance or frequentist confidence interval")


def _policy_name(model_policy) -> str:
    """Resolve the informational model-policy name (the lock is not overridable)."""
    if model_policy is None:
        return MODEL_POLICY
    if isinstance(model_policy, str):
        return model_policy
    if isinstance(model_policy, Mapping):
        for key in ("policy", "name", "model_policy"):
            value = model_policy.get(key)
            if value is not None:
                return str(value)
        return MODEL_POLICY
    return str(model_policy)


def _import_fit_engine():
    """Lazily import the optional numerical stack.  Returns ``(engine, error)``."""
    try:
        import torch
        import gpytorch
        from gpytorch.constraints import Interval
        from gpytorch.kernels import MaternKernel, ScaleKernel
        from gpytorch.means import ConstantMean
        from gpytorch.mlls import ExactMarginalLogLikelihood
        from botorch.fit import fit_gpytorch_mll
        from botorch.models import SingleTaskGP
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
        "SingleTaskGP": SingleTaskGP,
        "Standardize": Standardize,
    }, None


def library_versions() -> dict:
    """Installed engine versions, or an availability marker.  Never raises."""
    out: dict = {"engine": "botorch"}
    try:
        import torch
        out["torch"] = str(torch.__version__)
    except Exception:  # noqa: BLE001
        out["torch"] = None
    try:
        import botorch
        out["botorch"] = str(botorch.__version__)
    except Exception:  # noqa: BLE001
        out["botorch"] = None
    try:
        import gpytorch
        out["gpytorch"] = str(gpytorch.__version__)
    except Exception:  # noqa: BLE001
        out["gpytorch"] = None
    try:
        import linear_operator
        out["linear_operator"] = str(linear_operator.__version__)
    except Exception:  # noqa: BLE001
        out["linear_operator"] = None
    out["available"] = all(out.get(k) is not None for k in ("torch", "botorch", "gpytorch"))
    return out


@dataclass(frozen=True)
class ModelFitResult:
    """Tagged result of :func:`fit_model`.  Callers must never substitute zero predictions."""

    status: str
    reason: str
    detail: str | None = None
    d: int | None = None
    n: int | None = None
    model: Any = field(default=None, repr=False, compare=False)
    train_X: np.ndarray | None = field(default=None, repr=False, compare=False)
    train_ids: tuple[str, ...] = ()
    s2_original: float | None = None
    train_Yvar_original: float | None = None
    hyperparameters: dict = field(default_factory=dict)
    fit: dict = field(default_factory=dict)
    library_versions: dict = field(default_factory=dict)
    seed: int = 0
    model_policy: str = MODEL_POLICY
    timing_s: float | None = None
    warnings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "d": self.d,
            "n": self.n,
            "train_ids": list(self.train_ids),
            "s2_original": self.s2_original,
            "train_Yvar_original": self.train_Yvar_original,
            "hyperparameters": dict(self.hyperparameters),
            "fit": dict(self.fit),
            "library_versions": dict(self.library_versions),
            "seed": int(self.seed),
            "model_policy": self.model_policy,
            "timing_s": self.timing_s,
            "warnings": list(self.warnings),
        }


def _unavailable(reason: str, *, detail: str | None = None, d: int | None = None,
                 n: int | None = None, seed: int = 0, policy: str = MODEL_POLICY,
                 timing_s: float | None = None, versions: dict | None = None,
                 warnings_seen: tuple[str, ...] = ()) -> ModelFitResult:
    return ModelFitResult(
        status=STATUS_UNAVAILABLE, reason=reason, detail=detail, d=d, n=n, seed=int(seed),
        model_policy=policy, timing_s=timing_s,
        library_versions=(versions if versions is not None else library_versions()),
        warnings=warnings_seen)


def _sample_variance(J: np.ndarray) -> float:
    if J.size < 2:
        return 0.0
    return float(np.var(np.asarray(J, dtype=np.float64).reshape(-1), ddof=1))


def fit_model(training_set, model_policy=None, seed: int = 0) -> ModelFitResult:
    """Fit the locked ``scalar_pool_v1`` GP to a frozen :class:`~.data.TrainingSet`.

    Returns ``status="ok"`` only when the exact MLL fit and a finite latent posterior succeed.
    Every other outcome is a tagged ``status="unavailable"`` result with a reason code.
    """
    started = time.perf_counter()
    policy = _policy_name(model_policy)
    if policy != MODEL_POLICY:
        return _unavailable(REASON_UNSUPPORTED_MODEL_POLICY,
                            detail=f"locked policy is {MODEL_POLICY!r}, got {policy!r}",
                            seed=seed, policy=policy,
                            timing_s=time.perf_counter() - started)

    # ---- structural gates (no engine needed) ----------------------------------------------
    status = getattr(training_set, "status", None)
    X = getattr(training_set, "X", None)
    J = getattr(training_set, "J", None)
    Y = getattr(training_set, "Y", None)
    d = getattr(training_set, "d", None)
    n = getattr(training_set, "n", None)

    if status == "needs_initial_data":
        return _unavailable(REASON_NEEDS_INITIAL_DATA,
                            detail="training set is below n_min; no model is trained",
                            d=(None if d is None else int(d)), n=0, seed=seed, policy=policy,
                            timing_s=time.perf_counter() - started)
    if status != "ok":
        return _unavailable(REASON_INSUFFICIENT_DATA,
                            detail=f"training set status is {status!r}",
                            d=(None if d is None else int(d)), n=(None if n is None else int(n)),
                            seed=seed, policy=policy, timing_s=time.perf_counter() - started)

    if X is None or (J is None and Y is None):
        return _unavailable(REASON_INSUFFICIENT_DATA,
                            detail="training set has no X/J arrays",
                            d=(None if d is None else int(d)), n=(None if n is None else int(n)),
                            seed=seed, policy=policy, timing_s=time.perf_counter() - started)

    X = np.asarray(X, dtype=np.float64)
    if X.ndim != 2 or X.shape[0] < 1:
        return _unavailable(REASON_INSUFFICIENT_DATA,
                            detail=f"X must be 2-D with at least one row, got {X.shape}",
                            seed=seed, policy=policy, timing_s=time.perf_counter() - started)
    n_actual, d_actual = int(X.shape[0]), int(X.shape[1])
    if d is not None and int(d) != d_actual:
        return _unavailable(REASON_INSUFFICIENT_DATA,
                            detail=f"training_set.d={d} disagrees with X.shape[1]={d_actual}",
                            d=int(d), n=n_actual, seed=seed, policy=policy,
                            timing_s=time.perf_counter() - started)
    n_min = int(getattr(training_set, "n_min", 0) or 0)
    if n_min <= 0:
        n_min = max(16, 2 * (d_actual + 1))
    if n_actual < n_min:
        return _unavailable(REASON_NEEDS_INITIAL_DATA,
                            detail=f"n={n_actual} is below n_min={n_min}",
                            d=d_actual, n=n_actual, seed=seed, policy=policy,
                            timing_s=time.perf_counter() - started)

    # The lock is Y = -J.  If only Y is present, derive J = -Y (never invert the sign twice).
    if J is not None:
        J_arr = np.asarray(J, dtype=np.float64).reshape(-1, 1)
        Y_arr = -J_arr
        if Y is not None:
            Y_given = np.asarray(Y, dtype=np.float64).reshape(-1, 1)
            if Y_given.shape != Y_arr.shape or not np.allclose(Y_given, Y_arr, rtol=0.0,
                                                               atol=0.0):
                return _unavailable(
                    REASON_INSUFFICIENT_DATA,
                    detail="training set Y is not exactly -J; refusing an ambiguous sign",
                    d=d_actual, n=n_actual, seed=seed, policy=policy,
                    timing_s=time.perf_counter() - started)
    else:
        Y_arr = np.asarray(Y, dtype=np.float64).reshape(-1, 1)
        J_arr = -Y_arr
    if J_arr.shape != (n_actual, 1) or Y_arr.shape != (n_actual, 1):
        return _unavailable(REASON_INSUFFICIENT_DATA,
                            detail=f"J/Y shapes do not match X rows ({J_arr.shape}, {Y_arr.shape})",
                            d=d_actual, n=n_actual, seed=seed, policy=policy,
                            timing_s=time.perf_counter() - started)
    if not (np.all(np.isfinite(X)) and np.all(np.isfinite(J_arr))):
        return _unavailable(REASON_NONFINITE_TRAINING_DATA,
                            detail="X or J contains NaN/Inf",
                            d=d_actual, n=n_actual, seed=seed, policy=policy,
                            timing_s=time.perf_counter() - started)

    s2 = _sample_variance(J_arr)
    if s2 <= FLAT_VARIANCE_TOL:
        return _unavailable(REASON_FLAT_TRAINING_RESPONSE,
                            detail=f"sample variance s2={s2!r} <= {FLAT_VARIANCE_TOL!r}",
                            d=d_actual, n=n_actual, seed=seed, policy=policy,
                            timing_s=time.perf_counter() - started)

    # ---- optional engine ------------------------------------------------------------------
    engine, import_error = _import_fit_engine()
    versions = library_versions()
    if engine is None:
        return _unavailable(REASON_CAPABILITY_MISSING,
                            detail=f"optional BoTorch engine is unavailable: {import_error}",
                            d=d_actual, n=n_actual, seed=seed, policy=policy,
                            versions=versions, timing_s=time.perf_counter() - started)

    torch = engine["torch"]
    gpytorch = engine["gpytorch"]
    try:
        torch.set_num_threads(NUM_THREADS)
    except Exception:  # noqa: BLE001 - thread pinning is best-effort, never a fit failure
        pass

    dtype = torch.float64
    train_X = torch.as_tensor(X, dtype=dtype)
    train_Y = torch.as_tensor(Y_arr, dtype=dtype)
    yvar_original = float(NOISE_FLOOR_MULTIPLIER * s2)
    train_Yvar = torch.full((n_actual, 1), yvar_original, dtype=dtype)

    captured: list[str] = []
    fit_info: dict = {"method": "exact_mll", "attempts": 0, "max_iters": FIT_MAX_ITERS,
                      "jitter": None, "mll_value": None}
    model = None
    last_detail: str | None = None
    try:
        for jitter in (JITTER_INITIAL, JITTER_RESET):
            fit_info["jitter"] = jitter
            try:
                lengthscale_constraint = engine["Interval"](LENGTHSCALE_LOWER, LENGTHSCALE_UPPER)
                covariance = engine["ScaleKernel"](
                    engine["MaternKernel"](nu=2.5, ard_num_dims=d_actual,
                                           lengthscale_prior=None,
                                           lengthscale_constraint=lengthscale_constraint),
                    outputscale_prior=None,
                    outputscale_constraint=engine["Interval"](OUTPUTSCALE_LOWER,
                                                             OUTPUTSCALE_UPPER),
                )
                mean = engine["ConstantMean"]()
                # Standardization can round 1e-6 a few ulps below GPyTorch's default
                # floor, silently changing the declared fixed variance. Allow the exact
                # transformed value and verify it immediately after construction.
                with warnings.catch_warnings(record=True) as construction_warnings:
                    warnings.simplefilter("always")
                    with gpytorch.settings.min_fixed_noise(double_value=1e-12):
                        candidate_model = engine["SingleTaskGP"](
                            train_X, train_Y, train_Yvar=train_Yvar, covar_module=covariance,
                            mean_module=mean, outcome_transform=engine["Standardize"](m=1))
                captured.extend(f"{w.category.__name__}: {w.message}" for w in construction_warnings)
                expected_noise = yvar_original / _stdvs_sq(candidate_model)
                if not np.allclose(_extract_noise(candidate_model), expected_noise,
                                   rtol=1e-12, atol=0.0):
                    raise RuntimeError("fixed transformed noise does not match declared variance")
                # Locked initial values in the *physical* (constrained) space, after .to(dtype).
                with torch.no_grad():
                    candidate_model.covar_module.base_kernel.lengthscale = LENGTHSCALE_INIT
                    candidate_model.covar_module.outputscale = OUTPUTSCALE_INIT
                    candidate_model.mean_module.constant = MEAN_INIT
                mll = engine["ExactMarginalLogLikelihood"](candidate_model.likelihood,
                                                           candidate_model)
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    fit_info["attempts"] += 1
                    with gpytorch.settings.cholesky_jitter(jitter):
                        engine["fit_gpytorch_mll"](
                            mll,
                            optimizer_kwargs={"options": {"maxiter": FIT_MAX_ITERS}},
                            max_attempts=1,
                        )
                captured.extend(f"{w.category.__name__}: {w.message}" for w in caught)
                candidate_model.eval()
                # A successful fit must also produce finite hyperparameters and a finite
                # latent posterior; otherwise it is unusable for acquisition.
                hyper = _extract_hyperparameters(candidate_model)
                if not _finite_hyperparameters(hyper):
                    raise RuntimeError("fit produced non-finite hyperparameters")
                with torch.no_grad():
                    posterior = candidate_model.posterior(train_X, observation_noise=False)
                    new_mll = float(mll(candidate_model(*candidate_model.train_inputs),
                                        candidate_model.train_targets).detach())
                if not (math.isfinite(float(posterior.mean.sum()))
                        and math.isfinite(float(posterior.variance.sum()))
                        and math.isfinite(new_mll)):
                    raise RuntimeError("fit produced a non-finite posterior/MLL")
                model = candidate_model
                fit_info["mll_value"] = new_mll
                last_detail = None
                break
            except Exception as exc:  # noqa: BLE001 - retry once at the reset jitter
                last_detail = f"{type(exc).__name__}: {exc}"
                model = None
                continue
    except Exception as exc:  # noqa: BLE001 - never let an engine failure escape
        last_detail = f"{type(exc).__name__}: {exc}"
        model = None

    if model is None:
        return _unavailable(REASON_MODEL_UNAVAILABLE,
                            detail=last_detail or "exact MLL fit failed",
                            d=d_actual, n=n_actual, seed=seed, policy=policy,
                            versions=versions, timing_s=time.perf_counter() - started,
                            warnings_seen=tuple(captured))

    hyper = _extract_hyperparameters(model)
    hyper["noise_transformed"] = _extract_noise(model)
    hyper["mean_constant"] = float(model.mean_module.constant.detach().item())
    fit_info["train_Yvar_transformed_expected"] = yvar_original / _stdvs_sq(model)
    fit_info["stdvs_sq"] = _stdvs_sq(model)
    return ModelFitResult(
        status=STATUS_OK, reason=REASON_OK, d=d_actual, n=n_actual, model=model,
        train_X=np.array(X, dtype=np.float64, copy=True),
        train_ids=tuple(str(i) for i in getattr(training_set, "ids", ())),
        s2_original=s2, train_Yvar_original=yvar_original, hyperparameters=hyper,
        fit=fit_info, library_versions=versions, seed=int(seed), model_policy=policy,
        timing_s=time.perf_counter() - started, warnings=tuple(captured))


def _extract_hyperparameters(model) -> dict:
    try:
        lengthscales = model.covar_module.base_kernel.lengthscale.detach().cpu().numpy()
        outputscale = float(model.covar_module.outputscale.detach().cpu().item())
    except Exception:  # noqa: BLE001
        return {}
    return {
        "lengthscales": np.asarray(lengthscales, dtype=float).reshape(-1).tolist(),
        "lengthscale_bounds": [LENGTHSCALE_LOWER, LENGTHSCALE_UPPER],
        "lengthscale_init": LENGTHSCALE_INIT,
        "outputscale": outputscale,
        "outputscale_bounds": [OUTPUTSCALE_LOWER, OUTPUTSCALE_UPPER],
        "outputscale_init": OUTPUTSCALE_INIT,
    }


def _extract_noise(model):
    try:
        noise = model.likelihood.noise.detach().cpu().numpy().reshape(-1)
        return noise.tolist()
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
        raw_out = hyper.get("outputscale")
        if raw_out is None:
            return False
        return bool(ls.size > 0 and np.all(np.isfinite(ls))
                    and math.isfinite(float(raw_out)))
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True)
class PredictionResult:
    """Posterior summary converted back into original ``J`` units."""

    status: str
    reason: str
    detail: str | None = None
    j_mean: np.ndarray | None = None
    j_lower: np.ndarray | None = None
    j_upper: np.ndarray | None = None
    y_mean: np.ndarray | None = None
    y_sd: np.ndarray | None = None
    flags: tuple[str, ...] = ()
    nonphysical: bool = False
    interval_label: str = INTERVAL_LABEL
    observation_noise: bool = False

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK

    def to_dict(self) -> dict:
        def _plain(v):
            return None if v is None else np.asarray(v, dtype=float).reshape(-1).tolist()

        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "j_mean": _plain(self.j_mean),
            "j_lower": _plain(self.j_lower),
            "j_upper": _plain(self.j_upper),
            "y_mean": _plain(self.y_mean),
            "y_sd": _plain(self.y_sd),
            "flags": list(self.flags),
            "nonphysical": bool(self.nonphysical),
            "interval_label": self.interval_label,
            "observation_noise": bool(self.observation_noise),
        }


def predict_j(model_result: ModelFitResult, X) -> PredictionResult:
    """Predict ``J`` (not ``-J``) at candidate unit vectors, with reversed J-interval endpoints.

    ``predicted J = -posterior mean(Y)``.  With ``Y = -J`` the symmetric interval
    ``[mu_Y - z*sigma, mu_Y + z*sigma]`` becomes ``[-mu_Y - z*sigma, -mu_Y + z*sigma]`` (the
    endpoints swap).  Nonphysical values (e.g. a negative predicted ``J``) are **flagged**, never
    clamped or zero-filled.
    """
    if model_result is None or model_result.status != STATUS_OK or model_result.model is None:
        return PredictionResult(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                detail="no fitted model")
    engine, import_error = _import_fit_engine()
    if engine is None:
        return PredictionResult(status=STATUS_UNAVAILABLE, reason=REASON_CAPABILITY_MISSING,
                                detail=import_error)
    torch = engine["torch"]
    try:
        arr = np.asarray(X, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.ndim != 2 or arr.shape[1] != int(model_result.d or arr.shape[1]):
            return PredictionResult(status=STATUS_UNAVAILABLE, reason=REASON_INSUFFICIENT_DATA,
                                    detail=f"unexpected candidate shape {arr.shape}")
        if not np.all(np.isfinite(arr)):
            return PredictionResult(status=STATUS_UNAVAILABLE,
                                    reason=REASON_NONFINITE_TRAINING_DATA,
                                    detail="candidate X contains NaN/Inf")
        try:
            torch.set_num_threads(NUM_THREADS)
        except Exception:  # noqa: BLE001
            pass
        with torch.no_grad():
            posterior = model_result.model.posterior(
                torch.as_tensor(arr, dtype=torch.float64), observation_noise=False)
            y_mean = posterior.mean.detach().cpu().numpy().reshape(-1)
            y_sd = posterior.variance.clamp_min(0.0).sqrt().detach().cpu().numpy().reshape(-1)
    except Exception as exc:  # noqa: BLE001 - a failed posterior is a tagged unavailability
        return PredictionResult(status=STATUS_UNAVAILABLE, reason=REASON_MODEL_UNAVAILABLE,
                                detail=f"posterior failed: {type(exc).__name__}: {exc}")

    return summarize_j(y_mean, y_sd)


def summarize_j(y_mean, y_sd, *, z: float = CREDIBLE_Z) -> PredictionResult:
    """Convert latent ``Y=-J`` posterior moments to predicted ``J`` with reversed endpoints.

    Pure display math (no Torch): flags nonphysical predictions instead of clamping them.
    """
    y_mean = np.asarray(y_mean, dtype=np.float64).reshape(-1)
    y_sd = np.asarray(y_sd, dtype=np.float64).reshape(-1)
    if y_mean.size != y_sd.size:
        return PredictionResult(status=STATUS_UNAVAILABLE, reason=REASON_INSUFFICIENT_DATA,
                                detail="y_mean and y_sd have different lengths")
    j_mean = -y_mean
    j_lower = -(y_mean + z * y_sd)
    j_upper = -(y_mean - z * y_sd)
    flags: list[str] = []
    if not (np.all(np.isfinite(j_mean)) and np.all(np.isfinite(j_lower))
            and np.all(np.isfinite(j_upper))):
        flags.append("nonfinite_prediction")
    if np.any(j_mean < 0.0):
        flags.append("nonphysical_predicted_J_negative")
    return PredictionResult(
        status=STATUS_OK, reason=REASON_OK, j_mean=j_mean, j_lower=j_lower, j_upper=j_upper,
        y_mean=y_mean, y_sd=y_sd, flags=tuple(flags), nonphysical=bool(flags))


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
    "FLAT_VARIANCE_TOL",
    "FIT_MAX_ITERS",
    "JITTER_INITIAL",
    "JITTER_RESET",
    "NUM_THREADS",
    "CREDIBLE_Z",
    "INTERVAL_LABEL",
    "REASON_OK",
    "REASON_NEEDS_INITIAL_DATA",
    "REASON_INSUFFICIENT_DATA",
    "REASON_NONFINITE_TRAINING_DATA",
    "REASON_FLAT_TRAINING_RESPONSE",
    "REASON_MODEL_UNAVAILABLE",
    "REASON_CAPABILITY_MISSING",
    "REASON_UNSUPPORTED_MODEL_POLICY",
    "STATUS_OK",
    "STATUS_UNAVAILABLE",
    "ModelFitResult",
    "PredictionResult",
    "library_versions",
    "fit_model",
    "predict_j",
    "summarize_j",
]
