"""Focused tests for the locked scalar-pool v1 GP (hornlab_search/bo/model.py).

The model-fit tests need the isolated BoTorch engine and are skipped when it is absent; the
structural gates and the capability error do not import it.  Run with the bayes interpreter from
the checkout root:

    & C:\\Users\\hunte\\Hrns\\oc-wt\\bo-study\\bayes-venv\\Scripts\\python.exe -m pytest \
        tests/test_bo_model.py -q
"""
from __future__ import annotations

import dataclasses
import importlib.util
import sys

import numpy as np
import pytest

from hornlab_search.bo import (
    LENGTHSCALE_INIT,
    MODEL_POLICY,
    NOISE_FLOOR_MULTIPLIER,
    OUTPUTSCALE_INIT,
    build_training_set,
    fit_model,
    make_pure_observations,
    predict_j,
)

HAS_BOTORCH = importlib.util.find_spec("botorch") is not None
requires_botorch = pytest.mark.skipif(
    not HAS_BOTORCH, reason="optional BoTorch engine (isolated bayes venv) absent")


def _ts(d=2, n=16, seed=1):
    return build_training_set(make_pure_observations(d, n, seed=seed), d=d)


@pytest.fixture(scope="module")
def training():
    return _ts()


@pytest.fixture(scope="module")
def fitted(training):
    return fit_model(training, seed=0)


# ------------------------------------------------------------------ structural gates


def test_lower_true_j_gives_larger_bo_target_exact_sign():
    ts = _ts()
    assert np.all(ts.Y == -ts.J)
    order = np.argsort(ts.J, axis=0).reshape(-1)
    # J ascending -> Y descending: the model target is exactly the negated objective.
    assert np.all(np.diff(ts.Y[order].reshape(-1)) <= 0.0)
    assert float(ts.Y.min()) == pytest.approx(-float(ts.J.max()))
    assert float(ts.Y.max()) == pytest.approx(-float(ts.J.min()))


def test_needs_initial_data_below_n_min():
    ts = build_training_set(make_pure_observations(2, 15, seed=1), d=2)
    assert ts.status == "needs_initial_data"
    result = fit_model(ts)
    assert result.status == "unavailable"
    assert result.reason == "needs_initial_data"
    assert result.model is None


def test_flat_training_response_refuses_a_confident_model():
    ts = _ts()
    flat = dataclasses.replace(ts, J=np.full_like(ts.J, 1.25),
                               Y=np.full_like(ts.Y, -1.25))
    result = fit_model(flat)
    assert result.status == "unavailable"
    assert result.reason == "flat_training_response"
    assert result.model is None
    assert "sample variance" in (result.detail or "")


def test_nonfinite_training_data_refuses():
    ts = _ts()
    bad_x = np.array(ts.X, copy=True)
    bad_x[0, 0] = np.nan
    result = fit_model(dataclasses.replace(ts, X=bad_x))
    assert result.status == "unavailable"
    assert result.reason == "nonfinite_training_data"
    assert result.model is None


def test_insufficient_arrays_refuse():
    ts = _ts()
    result = fit_model(dataclasses.replace(ts, X=None))
    assert result.status == "unavailable"
    assert result.reason == "insufficient_data"
    assert result.model is None


def test_unsupported_model_policy_refuses():
    result = fit_model(_ts(), "some_other_policy")
    assert result.status == "unavailable"
    assert result.reason == "unsupported_model_policy"


def test_optional_engine_absent_is_a_clean_capability_error(monkeypatch):
    ts = _ts()
    for key in [k for k in sys.modules if k == "botorch" or k.startswith("botorch.")]:
        monkeypatch.delitem(sys.modules, key, raising=False)
    monkeypatch.setitem(sys.modules, "botorch", None)
    result = fit_model(ts)
    assert result.status == "unavailable"
    assert result.reason == "capability_missing"
    assert result.model is None
    assert "BoTorch" in (result.detail or "")


# ------------------------------------------------------------------ locked fit


@requires_botorch
def test_fit_uses_locked_policy_and_returns_provenance(training, fitted):
    assert fitted.status == "ok" and fitted.reason == "ok"
    assert fitted.model_policy == MODEL_POLICY
    assert fitted.seed == 0
    assert fitted.d == training.d and fitted.n == training.n
    assert fitted.train_ids == training.ids
    assert fitted.train_X.shape == training.X.shape

    # Fixed noise in ORIGINAL output-squared units: train_Yvar = 1e-6 * sample variance(J).
    s2 = float(np.var(training.J.reshape(-1), ddof=1))
    assert fitted.s2_original == pytest.approx(s2, rel=1e-12)
    assert fitted.train_Yvar_original == pytest.approx(NOISE_FLOOR_MULTIPLIER * s2, rel=1e-12)

    # Fixed noise is transformed through Standardize and lands at exactly 1e-6.
    noise = np.asarray(fitted.hyperparameters["noise_transformed"], dtype=float)
    assert noise.shape == (training.n,)
    assert np.allclose(noise, NOISE_FLOOR_MULTIPLIER, rtol=1e-12, atol=0.0)
    std_sq = fitted.fit["stdvs_sq"]
    assert std_sq == pytest.approx(s2, rel=1e-10)

    hyper = fitted.hyperparameters
    assert len(hyper["lengthscales"]) == training.d
    assert all(0.005 <= float(v) <= 4.0 for v in hyper["lengthscales"])
    assert 1e-3 <= float(hyper["outputscale"]) <= 1e3
    assert np.isfinite(float(hyper["mean_constant"]))
    assert hyper["lengthscale_init"] == LENGTHSCALE_INIT
    assert hyper["outputscale_init"] == OUTPUTSCALE_INIT

    assert fitted.fit["method"] == "exact_mll"
    assert fitted.fit["attempts"] == 1
    assert fitted.fit["max_iters"] == 100
    assert fitted.fit["jitter"] == 1e-8
    assert fitted.library_versions["botorch"] is not None
    assert fitted.library_versions["gpytorch"] is not None


@requires_botorch
def test_locked_kernel_structure(fitted):
    model = fitted.model
    base = model.covar_module.base_kernel
    assert float(base.nu) == pytest.approx(2.5)
    assert int(base.ard_num_dims) == fitted.d
    assert list(base.named_priors()) == []
    assert list(model.covar_module.named_priors()) == []
    assert type(model.mean_module).__name__ == "ConstantMean"
    assert type(model.outcome_transform).__name__ == "Standardize"


@requires_botorch
def test_predict_j_reverses_interval_endpoints(training, fitted):
    pred = predict_j(fitted, training.X[:4])
    assert pred.status == "ok" and pred.reason == "ok"
    assert pred.observation_noise is False
    assert pred.y_sd is not None and np.all(pred.y_sd >= 0.0)
    # J = -Y: interval endpoints reverse, and the J interval stays ordered.
    assert np.allclose(pred.j_mean, -pred.y_mean, rtol=0.0, atol=0.0)
    assert np.allclose(pred.j_lower, -(pred.y_mean + 1.96 * pred.y_sd), rtol=0.0, atol=0.0)
    assert np.allclose(pred.j_upper, -(pred.y_mean - 1.96 * pred.y_sd), rtol=0.0, atol=0.0)
    assert np.all(pred.j_lower <= pred.j_mean)
    assert np.all(pred.j_mean <= pred.j_upper)
    # Exact sign: a larger BO target Y corresponds to a smaller predicted J.
    assert np.allclose(pred.j_mean, -pred.y_mean, rtol=0.0, atol=0.0)
    assert "model credible interval" in pred.interval_label
    assert pred.flags == () and pred.nonphysical is False


def test_negative_predicted_j_is_flagged_not_clamped():
    from hornlab_search.bo import summarize_j

    # A positive latent Y mean means predicted J = -Y < 0: the display must flag it, not clamp.
    pred = summarize_j(np.array([0.5]), np.array([0.1]))
    assert pred.status == "ok"
    assert pred.j_mean[0] == pytest.approx(-0.5, rel=0.0, abs=0.0)
    assert pred.j_lower[0] == pytest.approx(-(0.5 + 1.96 * 0.1), rel=0.0, abs=0.0)
    assert pred.j_upper[0] == pytest.approx(-(0.5 - 1.96 * 0.1), rel=0.0, abs=0.0)
    assert "nonphysical_predicted_J_negative" in pred.flags
    assert pred.nonphysical is True
    assert pred.to_dict()["j_mean"] == [pytest.approx(-0.5)]


def test_nonfinite_prediction_is_flagged():
    from hornlab_search.bo import summarize_j

    pred = summarize_j(np.array([np.nan]), np.array([0.1]))
    assert "nonfinite_prediction" in pred.flags


@requires_botorch
def test_same_seed_fit_is_reproducible(training):
    a = fit_model(training, seed=7)
    b = fit_model(training, seed=7)
    assert a.status == b.status == "ok"
    assert a.hyperparameters["lengthscales"] == pytest.approx(
        b.hyperparameters["lengthscales"], rel=1e-6, abs=1e-8)
    assert a.hyperparameters["outputscale"] == pytest.approx(
        b.hyperparameters["outputscale"], rel=1e-6, abs=1e-8)
    pa = predict_j(a, training.X)
    pb = predict_j(b, training.X)
    assert np.allclose(pa.j_mean, pb.j_mean, rtol=1e-6, atol=1e-8)
    assert np.allclose(pa.j_lower, pb.j_lower, rtol=1e-6, atol=1e-8)


@requires_botorch
def test_reported_transformed_noise_is_actual_expected(fitted):
    expected = fitted.train_Yvar_original / fitted.fit["stdvs_sq"]
    assert fitted.fit["train_Yvar_transformed_expected"] == expected
    np.testing.assert_allclose(fitted.hyperparameters["noise_transformed"], expected, rtol=1e-12, atol=0)
    assert not any("Very small noise" in warning for warning in fitted.warnings)
