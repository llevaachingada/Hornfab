"""Acquisition-sign evidence for the metric-composite engine (Pass 2 lane A).

These tests use the **real** CPU BoTorch stack on a tiny synthetic multi-output artifact
(``n<=30``, ``d=2``, ``m=2``).  They pin the three facts the policy contract depends on:

1. ``composite_utility(samples) == -samples.sum(dim=-1)`` exactly (lower J is higher utility);
2. on a controlled posterior the qLogNEI acquisition reaches its maximum at the candidate the
   engine selects, and the reported acquisition score is not a predicted ``J``;
3. a candidate with the *lower* predicted ``J`` need not win the acquisition, because posterior
   uncertainty can dominate -- proving ``acquisition != predicted J``.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("gpytorch")
pytest.importorskip("botorch")
pytest.importorskip("linear_operator")

from hornlab_search.bo.metric_contracts import (  # noqa: E402
    V10_COMPONENT_NAMES,
    MetricTrainingArtifact,
    sha256_json,
)
from hornlab_search.bo.metric_model import (  # noqa: E402
    fit_metric_model,
    predict_metric_components,
)
from hornlab_search.bo.metric_objective import (  # noqa: E402
    build_metric_acquisition,
    composite_utility,
    evaluate_metric_candidates,
)

#: Two varying components is enough for a multi-output (m=2) composite; the other two are the
#: frozen schema's constant remainder so the artifact still follows the v10 order.
M = 2


def _artifact(*, n: int = 20, seed: int = 3) -> MetricTrainingArtifact:
    rng = np.random.default_rng(seed)
    # Training points cluster near the low-J corner so the far corner has high posterior
    # variance: the classic exploration/exploitation split this test needs.
    X = rng.uniform(0.0, 0.2, (n, 2))
    load = 0.10 + 0.30 * X[:, 0]
    coverage = 0.05 + 0.15 * X[:, 1]
    ripple = np.full(n, 0.05)
    other = np.full(n, 0.05)
    Y = np.column_stack([load, coverage, ripple, other])
    J = np.sum(Y, axis=1, keepdims=True)
    names = V10_COMPONENT_NAMES
    return MetricTrainingArtifact(
        status="ok", objective_version=10, feature_names=("x0", "x1"),
        component_names=tuple(names), X=X, J=J, Y_components=Y,
        observation_ids=tuple(f"obs-{i:02d}" for i in range(n)),
        selected_ids=tuple(f"obs-{i:02d}" for i in range(n)),
        metadata={"objective_version": 10,
                  "component_names": list(names)},
        checksum=sha256_json({"X": X.tolist(), "J": J.tolist(), "Y": Y.tolist(),
                              "components": list(names)}))


@pytest.fixture(scope="module")
def fitted():
    result = fit_metric_model(_artifact(), seed=0)
    assert result.status == "ok", result.reason
    return result


# --------------------------------------------------------------------------- utility exactness


def test_composite_utility_is_exactly_negative_component_sum():
    import torch

    samples = torch.tensor(
        [
            [[0.10, 0.20, 0.30, 0.40]],
            [[0.90, 0.10, 0.05, 0.00]],
            [[0.01, 0.01, 0.01, 0.01]],
        ],
        dtype=torch.float64,
    ).reshape(3, 1, 1, 4)
    utility = composite_utility(samples)
    expected = -samples.sum(dim=-1)
    assert torch.equal(utility, expected)
    # And the sign is the documented one: a smaller component sum has the larger utility.
    sums = samples.sum(dim=-1).reshape(-1)
    assert int(torch.argmin(sums)) == int(torch.argmax(utility.reshape(-1)))


# --------------------------------------------------------------------------- controlled posterior


def _scores(fitted, candidates, *, acq_seed=0):
    acq = build_metric_acquisition(fitted, acq_seed=acq_seed)
    assert acq.status == "ok", acq.reason
    scores = evaluate_metric_candidates(acq, candidates)
    assert scores.status == "ok", scores.reason
    return scores.values


def test_acquisition_argmax_is_selected_and_score_is_not_predicted_j(fitted):
    candidates = np.array([[0.90, 0.90], [0.90, 0.10]])
    values = _scores(fitted, candidates, acq_seed=0)
    prediction = predict_metric_components(fitted, candidates)
    assert prediction.status == "ok"

    selected = int(np.argmax(values))
    assert selected == 0
    # The selected candidate is the acquisition maximum.
    assert float(values[selected]) == float(np.max(values))
    # Candidate 1 actually has the lower predicted J, yet candidate 0 wins: the acquisition is a
    # different quantity from the predicted J, and the reported score is not that J.
    assert float(prediction.j_mean[1]) < float(prediction.j_mean[0])
    assert selected != int(np.argmin(prediction.j_mean))
    assert float(values[selected]) != pytest.approx(float(prediction.j_mean[selected]))
    assert np.isfinite(values).all()


def test_uncertainty_can_outrank_a_lower_predicted_j(fitted):
    # The winner is not the lowest-predicted-J candidate: posterior uncertainty dominates.
    candidates = np.array([
        [0.10, 0.10],   # training-adjacent, low variance, lowest posterior mean J
        [0.50, 0.50],   # far in both dimensions, high variance
        [0.90, 0.90],   # far corner
        [0.90, 0.10],   # far along x0 only
        [0.10, 0.90],   # far along x1 only
    ])
    values = _scores(fitted, candidates, acq_seed=1)
    prediction = predict_metric_components(fitted, candidates)
    assert prediction.status == "ok"

    lowest_j = int(np.argmin(prediction.j_mean))
    winner = int(np.argmax(values))
    assert lowest_j == 0
    assert winner == 2
    assert winner != lowest_j
    # The winner carries a strictly *higher* predicted J than the uncertainty-disfavoured point.
    assert float(prediction.j_mean[4]) < float(prediction.j_mean[winner])
    assert float(values[4]) < float(values[winner])
    # The reported score is a logNEI ranking value, never the predicted J.
    assert float(values[winner]) != pytest.approx(float(prediction.j_mean[winner]))
    assert float(values[winner]) < 0.0
    # The winner's posterior SD is larger than the lower-J candidate's.
    assert float(prediction.j_sd[winner]) > float(prediction.j_sd[4])


def test_acquisition_is_reproducible_for_the_same_seed(fitted):
    candidates = np.array([[0.20, 0.30], [0.80, 0.70], [0.10, 0.90], [0.90, 0.10]])
    first = _scores(fitted, candidates, acq_seed=7)
    second = _scores(fitted, candidates, acq_seed=7)
    assert np.array_equal(first, second)
