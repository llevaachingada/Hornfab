"""Focused tests for the research-only constrained acquisition module.

Synthetic only: a tiny one-dimensional GP on a valid v10 four-component artifact fitted to a
known synthetic function, plus pure-array feasibility tests.  ``load_j`` is the constraint; the other components are the objective.
"""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.bo.metric_contracts import (MetricTrainingArtifact, V10_COMPONENT_NAMES,
                                                sha256_json)
from hornlab_search.bo.metric_constraints import (
    MARGIN_CONVENTION,
    RESEARCH_POLICY,
    PhysicalConstraint,
    build_constrained_acquisition,
    constraint_margins,
    evaluate_constrained_candidates,
    feasibility_from_samples,
    select_constrained_candidate,
)
from hornlab_search.bo.metric_model import fit_metric_model
from hornlab_search.bo.policy import PROPOSAL_POLICIES


def _artifact(n=28, seed=11):
    rng = np.random.default_rng(seed)
    X = rng.random((n, 1))
    # A valid v10 component schema keeps the real artifact-integrity gate in play:
    # load_j is the constraint output (x - 0.5); coverage_j is the scalar objective.
    load = X[:, 0] - 0.50
    coverage = (X[:, 0] - 0.20) ** 2
    ripple = np.full(n, 0.01)
    other = np.zeros(n)
    Y = np.column_stack([load, coverage, ripple, other])
    J = np.sum(Y, axis=1, keepdims=True)
    metadata = {"objective_version": 10, "synthetic": True, "feature_names": ["x"]}
    checksum = sha256_json({"X": X.tolist(), "J": J.tolist(), "Y": Y.tolist()})
    return MetricTrainingArtifact(
        status="ok", objective_version=10, feature_names=("x",),
        component_names=V10_COMPONENT_NAMES, X=X, J=J, Y_components=Y,
        observation_ids=tuple(f"obs-{i:03d}" for i in range(n)),
        selected_ids=tuple(f"obs-{i:03d}" for i in range(n)),
        metadata=metadata, checksum=checksum)


@pytest.fixture(scope="module")
def fitted():
    result = fit_metric_model(_artifact(), seed=0, max_iters=30)
    assert result.status == "ok", result.reason
    return result


def _constraint(threshold=0.0, key="load_j"):
    return PhysicalConstraint(metric_key=key, units="J contribution", threshold=float(threshold),
                              source="synthetic", fidelity="synthetic")


# ------------------------------------------------------------------ pure array contract


def test_margin_convention_and_pure_feasibility():
    assert "<= 0" in MARGIN_CONVENTION
    # samples: [sample, query, output]; output 0 is "score", output 1 is "constraint"
    samples = np.array([
        [[0.9, 0.20], [0.1, 0.80]],
        [[0.8, 0.40], [0.2, 0.90]],
        [[0.7, 0.50], [0.3, 0.10]],
    ])
    cons = [_constraint(0.5, key="constraint")]
    g = constraint_margins(samples, cons, ("score", "constraint"))
    np.testing.assert_allclose(g[..., 0], samples[..., 1] - 0.5)
    feasible, margins = feasibility_from_samples(samples, cons, ("score", "constraint"))
    expected = np.array([[True, False], [True, False], [True, True]])
    np.testing.assert_array_equal(feasible, expected)
    assert feasible.shape == (3, 2) and margins.shape == (3, 2, 1)


def test_a_large_score_is_not_reinterpreted_as_a_constraint():
    # A terrible score with a satisfied constraint remains feasible: score magnitude is not a
    # feasibility signal.
    samples = np.array([[[1000.0, 0.10]], [[999.0, 0.20]]])
    feasible, _ = feasibility_from_samples(samples, [_constraint(0.5, key="constraint")],
                                           ("score", "constraint"))
    assert feasible.all()


def test_missing_constraint_output_raises_in_the_pure_helper():
    with pytest.raises(KeyError):
        constraint_margins(np.zeros((2, 2)), [_constraint(key="absent")],
                           ("score", "constraint"))


# ------------------------------------------------------------------ acquisition


def test_build_requires_the_constraint_output_and_an_objective(fitted):
    missing = build_constrained_acquisition(fitted, [_constraint(key="absent")])
    assert missing.status == "unavailable"
    assert "constraint_output_missing" in missing.reason and missing.acq is None
    every = [PhysicalConstraint(name, "J contribution", 0.0, "synthetic", "synthetic")
             for name in V10_COMPONENT_NAMES]
    no_obj = build_constrained_acquisition(fitted, every)
    assert no_obj.status == "unavailable" and no_obj.reason == "no_objective_outputs"
    dup = build_constrained_acquisition(fitted, [_constraint(), _constraint()])
    assert dup.reason == "duplicate_constraint"
    assert build_constrained_acquisition(None, [_constraint()]).reason == "invalid_model"
    bad_policy = PhysicalConstraint("load_j", "J contribution", 0.0, "synthetic", "synthetic",
                                    missing_value_policy="impute")
    assert "unsupported_missing_value_policy" in (
        build_constrained_acquisition(fitted, [bad_policy]).reason)


def test_constrained_acquisition_and_infeasible_mask(fitted):
    constraint = _constraint(0.0)
    built = build_constrained_acquisition(fitted, [constraint], acq_seed=1, sample_shape=64)
    assert built.ok and built.acq is not None
    assert built.objective_output_names == ("coverage_j", "ripple_j", "other_j")
    assert built.constraint_output_names == ("load_j",)
    assert built.research_only is True and built.policy == RESEARCH_POLICY
    assert RESEARCH_POLICY not in PROPOSAL_POLICIES

    pool = np.linspace(0.0, 1.0, 21).reshape(-1, 1)
    evaluation = evaluate_constrained_candidates(built, pool, n_samples=128, seed=3)
    assert evaluation.ok
    probs = evaluation.feasibility_probability
    # The far-infeasible end of the pool is refused; the feasible end has finite values.
    assert probs[-1] < 0.5
    assert np.isneginf(evaluation.values[-1])
    assert np.isfinite(evaluation.values[0])
    assert evaluation.infeasible_count >= 1
    np.testing.assert_allclose(evaluation.values[evaluation.feasibility_probability <= 0.0],
                               -np.inf)

    selected = select_constrained_candidate(evaluation, min_feasibility_probability=0.5)
    assert selected.ok and selected.candidate_index is not None
    assert pool[selected.candidate_index, 0] <= 0.55
    assert selected.feasibility_probability >= 0.5


def test_no_feasible_candidate_is_refused(fitted):
    built = build_constrained_acquisition(fitted, [_constraint(threshold=-10.0)],
                                          acq_seed=0, sample_shape=32)
    assert built.ok
    evaluation = evaluate_constrained_candidates(built, np.linspace(0, 1, 11).reshape(-1, 1),
                                                n_samples=32, seed=1)
    assert evaluation.ok
    assert evaluation.infeasible_count == evaluation.n
    selected = select_constrained_candidate(evaluation)
    assert selected.status == "unavailable"
    assert selected.reason == "no_feasible_candidate"


def test_nonfinite_candidates_and_missing_model_are_unavailable(fitted):
    built = build_constrained_acquisition(fitted, [_constraint()], acq_seed=0, sample_shape=32)
    bad = np.array([[0.1], [np.nan]])
    assert evaluate_constrained_candidates(built, bad).status == "unavailable"
    assert evaluate_constrained_candidates(None, np.zeros((2, 1))).status == "unavailable"
    assert select_constrained_candidate(None).status == "unavailable"
