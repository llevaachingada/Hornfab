"""Focused tests for the metric-composite multi-output GP (Pass 1).

The fit tests run a **real** CPU ``float64`` BoTorch/GPyTorch fit on synthetic component data;
they are not individually skipped.  The whole module skips only when the optional bayes engine is
absent.  Run from the canonical checkout root with the isolated bayes interpreter and the
canonical solver packages appended (feature source, bayes site-packages, solver site-packages):

    $env:PYTHONPATH="C:\\Users\\hunte\\Hrns\\hornlab-search;C:\\Users\\hunte\\Hrns\\oc-wt\\bo-study\\bayes-venv\\Lib\\site-packages;C:\\Users\\hunte\\Hrns\\hornlab-search\\.venv\\Lib\\site-packages"
    & C:\\Users\\hunte\\Hrns\\oc-wt\\bo-study\\bayes-venv\\Scripts\\python.exe -m pytest \
        tests/test_bo_metric_model.py -q
"""
from __future__ import annotations

import dataclasses
import sys

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("gpytorch")
pytest.importorskip("botorch")
pytest.importorskip("linear_operator")

import hornlab_search
from hornlab_search.bo.metric_contracts import (
    V10_COMPONENT_NAMES,
    MetricTrainingArtifact,
    sha256_json,
)
from hornlab_search.bo.metric_model import (
    NOISE_FLOOR_MIN,
    NOISE_FLOOR_MULTIPLIER,
    fit_metric_model,
    predict_metric_components,
)

D = 3
N = 40
COMPONENT_NAMES = V10_COMPONENT_NAMES  # load, coverage, ripple, other (other is constant)


def synthetic_components(X: np.ndarray) -> np.ndarray:
    """Deterministic components; ``other_j`` is deliberately constant."""
    X = np.asarray(X, dtype=np.float64)
    x0, x1, x2 = X[:, 0], X[:, 1], X[:, 2]
    load = 0.10 + 0.30 * x0 + 0.02 * x1
    coverage = 0.10 + 0.20 * x0 + 0.03 * x2
    ripple = 0.05 + 0.15 * x0 * x1 + 0.02 * x2
    other = np.full(X.shape[0], 0.25)
    return np.column_stack([load, coverage, ripple, other])


def make_artifact(*, n: int = N, d: int = D, seed: int = 5) -> MetricTrainingArtifact:
    rng = np.random.default_rng(seed)
    X = rng.random((n, d))
    Y = synthetic_components(X)
    J = np.sum(Y, axis=1, keepdims=True)
    metadata = {
        "objective_version": 10,
        "bounds_hash": "synthetic-bounds-v1",
        "feature_names": ["x0", "x1", "x2"][:d],
        "component_schema": "v10-metric-components-v1",
    }
    checksum = sha256_json({
        "X": np.asarray(X, dtype=float).tolist(),
        "J": np.asarray(J, dtype=float).tolist(),
        "Y": np.asarray(Y, dtype=float).tolist(),
        "metadata": metadata,
    })
    return MetricTrainingArtifact(
        status="ok", objective_version=10,
        feature_names=tuple(metadata["feature_names"]),
        component_names=tuple(COMPONENT_NAMES),
        X=np.array(X, dtype=np.float64),
        J=np.array(J, dtype=np.float64),
        Y_components=np.array(Y, dtype=np.float64),
        observation_ids=tuple(f"obs-{i:03d}" for i in range(n)),
        selected_ids=tuple(f"obs-{i:03d}" for i in range(n)),
        metadata=metadata, checksum=checksum)


@pytest.fixture(scope="module")
def artifact() -> MetricTrainingArtifact:
    return make_artifact()


@pytest.fixture(scope="module")
def fitted(artifact):
    return fit_metric_model(artifact, seed=0)


# ------------------------------------------------------------------ real fit


def test_import_is_the_local_checkout_package():
    """The module under test must be this checkout's source, never a stale site-packages copy."""
    from pathlib import Path

    import hornlab_search

    expected = Path(__file__).resolve().parents[1] / "hornlab_search" / "__init__.py"
    assert Path(hornlab_search.__file__).resolve() == expected


def test_real_multitoutput_fit_is_finite_and_records_provenance(artifact, fitted):
    from botorch.models import ModelListGP

    assert fitted.status == "ok" and fitted.reason == "ok"
    assert fitted.policy == "metric_composite_v1"
    assert fitted.seed == 0
    assert fitted.d == D and fitted.n == N
    assert fitted.output_names == tuple(COMPONENT_NAMES)
    assert isinstance(fitted.model, ModelListGP)
    assert len(fitted.model.models) == len(COMPONENT_NAMES)
    assert np.array_equal(fitted.train_X, artifact.X)
    assert fitted.train_ids == artifact.observation_ids
    assert fitted.artifact_checksum == artifact.checksum
    assert len(fitted.model_hash) == 64
    assert fitted.library_versions["botorch"] is not None
    assert fitted.library_versions["gpytorch"] is not None
    assert fitted.library_versions["torch"] is not None
    assert fitted.timing_s is not None and fitted.timing_s > 0.0

    assert len(fitted.per_output) == len(COMPONENT_NAMES)
    variances = np.var(artifact.Y_components, axis=0, ddof=1)
    constant_mask = variances <= 1e-12
    assert constant_mask.tolist() == [False, False, False, True]

    for i, record in enumerate(fitted.per_output):
        assert record["name"] == COMPONENT_NAMES[i]
        assert record["posterior_finite"] is True
        assert record["sample_variance"] == pytest.approx(float(variances[i]), rel=1e-12)
        assert record["constant"] is bool(constant_mask[i])
        assert record["standardized"] is bool(not constant_mask[i])
        assert np.isfinite(record["sample_variance"])
        assert np.isfinite(record["noise_original"])
        assert len(record["lengthscales"]) == D
        assert all(np.isfinite(record["lengthscales"]))
        assert np.isfinite(record["outputscale"])
        assert np.isfinite(record["mean_constant"])
        if constant_mask[i]:
            assert record["noise_original"] == pytest.approx(1e-5, rel=0.0, abs=0.0)
            assert record["fit_method"] == "constant_parked"
        else:
            expected = max(NOISE_FLOOR_MULTIPLIER * float(variances[i]), NOISE_FLOOR_MIN)
            assert record["noise_original"] == pytest.approx(expected, rel=1e-12)
            assert record["fit_method"] == "exact_mll"
            assert record["attempts"] <= 2
            assert record["jitter"] in (1e-8, 1e-6)


def test_standardization_is_per_output_and_constant_output_is_not_standardized(fitted):
    transforms = [type(m.outcome_transform).__name__
                  if getattr(m, "outcome_transform", None) is not None else None
                  for m in fitted.model.models]
    assert transforms == ["Standardize", "Standardize", "Standardize", None]
    for m in fitted.model.models[:3]:
        assert float(m.covar_module.base_kernel.nu) == pytest.approx(2.5)
        assert int(m.covar_module.base_kernel.ard_num_dims) == D
        assert type(m.mean_module).__name__ == "ConstantMean"


def test_latent_posterior_and_component_prediction_are_finite(artifact, fitted):
    import torch

    pred = predict_metric_components(fitted, artifact.X)
    assert pred.status == "ok" and pred.reason == "ok"
    assert pred.component_mean is not None and pred.component_mean.shape == (N, 4)
    assert pred.component_sd is not None and pred.component_sd.shape == (N, 4)
    assert pred.j_mean is not None and pred.j_mean.shape == (N,)
    assert pred.j_sd is not None and pred.j_sd.shape == (N,)
    assert np.all(np.isfinite(pred.component_mean))
    assert np.all(np.isfinite(pred.component_sd))
    assert np.all(np.isfinite(pred.j_mean))
    assert np.all(np.isfinite(pred.j_sd))
    assert np.all(pred.component_sd >= 0.0)
    # Composite J and its independence-assumption SD are exact reductions of the components.
    np.testing.assert_allclose(pred.j_mean, np.sum(pred.component_mean, axis=1), rtol=0.0,
                               atol=0.0)
    np.testing.assert_allclose(pred.j_sd, np.sqrt(np.sum(pred.component_sd ** 2, axis=1)),
                               rtol=1e-12, atol=1e-15)
    assert pred.observation_noise is False
    assert "not a solved acoustic result" in (pred.detail or "")
    assert "nonfinite_prediction" not in pred.flags

    # Constant output: flat near-0.25 posterior, no NaN, tiny dispersion.
    assert np.allclose(pred.component_mean[:, 3], 0.25, rtol=0.0, atol=1e-8)
    assert float(np.max(pred.component_sd[:, 3])) < 0.1

    # ModelListGP posterior samples end in the component dimension.
    posterior = fitted.model.posterior(torch.as_tensor(artifact.X, dtype=torch.float64))
    samples = posterior.rsample(torch.Size([4]))
    assert tuple(samples.shape)[-1] == 4
    assert tuple(samples.shape)[:-1] == (4, N)


def test_same_seed_refit_is_deterministic(artifact):
    a = fit_metric_model(artifact, seed=3, max_iters=40)
    b = fit_metric_model(artifact, seed=3, max_iters=40)
    assert a.status == b.status == "ok"
    assert a.model_hash == b.model_hash
    for ra, rb in zip(a.per_output, b.per_output):
        assert ra["name"] == rb["name"]
        assert ra["constant"] == rb["constant"]
        assert ra["noise_original"] == pytest.approx(rb["noise_original"], rel=0.0, abs=0.0)
        if ra["constant"]:
            continue
        assert ra["lengthscales"] == pytest.approx(rb["lengthscales"], rel=1e-6, abs=1e-8)
        assert ra["outputscale"] == pytest.approx(rb["outputscale"], rel=1e-6, abs=1e-8)


def test_nonfinite_component_names_the_failed_output(artifact):
    Y = np.array(artifact.Y_components, copy=True)
    Y[0, 2] = np.nan
    bad = dataclasses.replace(artifact, Y_components=Y)
    result = fit_metric_model(bad)
    assert result.status == "unavailable"
    assert result.model is None
    assert result.per_output == ()
    assert "ripple_j" in (result.reason + " " + (result.detail or ""))


def test_artifact_checksum_and_versions_are_recorded(artifact, fitted):
    assert fitted.artifact_checksum == artifact.checksum
    assert set(["torch", "botorch", "gpytorch"]).issubset(fitted.library_versions)
    assert fitted.model_hash != ""


def test_optional_engine_absent_is_a_clean_capability_error(artifact, monkeypatch):
    for key in [k for k in sys.modules if k == "botorch" or k.startswith("botorch.")]:
        monkeypatch.delitem(sys.modules, key, raising=False)
    monkeypatch.setitem(sys.modules, "botorch", None)
    result = fit_metric_model(artifact)
    assert result.status == "unavailable"
    assert result.reason == "capability_missing"
    assert result.model is None
    assert "BoTorch" in (result.detail or "")


def test_prediction_shape_refusal_never_fabricates(fitted):
    pred = predict_metric_components(fitted, np.zeros((2, D + 1)))
    assert pred.status == "unavailable"
    assert pred.component_mean is None and pred.j_mean is None
    missing = predict_metric_components(None, np.zeros((1, D)))
    assert missing.status == "unavailable"
    assert missing.component_mean is None and missing.j_mean is None


def test_too_few_observations_refuses():
    tiny = make_artifact(n=1)
    result = fit_metric_model(tiny)
    assert result.status == "unavailable"
    assert result.reason == "insufficient_data"
    assert result.model is None
