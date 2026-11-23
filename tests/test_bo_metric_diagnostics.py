"""Focused tests for the synthetic model-comparison diagnostics.

Pure-metric tests use known arrays.  The comparison test runs small real CPU GP fits on synthetic
landscapes (n_train <= 24, d <= 3) so it stays fast; it records whatever outcome occurs and never
asserts that a composite arm must win.
"""
from __future__ import annotations

import numpy as np
import pytest

from hornlab_search.bo import metric_diagnostics as md
from hornlab_search.bo.metric_diagnostics import (
    ALL_ARM_NAMES,
    ARM_COMPONENT_COUNTS,
    ARM_NAMES,
    LANDSCAPE_NAMES,
    OPTIONAL_ARM_NAME,
    OPTIONAL_ARM_STATUS,
    arm_component_matrix,
    empirical_coverage,
    landscape_components,
    mae,
    prediction_bias,
    rmse,
    run_synthetic_model_comparison,
    spearman_rank,
    top_decile_recall,
)


def test_pure_metrics_on_known_arrays():
    pred = np.array([1.0, 2.0, 3.0, 4.0])
    true = np.array([1.5, 2.0, 2.5, 5.0])
    assert mae(pred, true) == pytest.approx(0.5)
    assert rmse(pred, true) == pytest.approx(np.sqrt((0.25 + 0.0 + 0.25 + 1.0) / 4.0))
    assert prediction_bias(pred, true) == pytest.approx(-0.25)
    assert spearman_rank([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman_rank([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)
    assert spearman_rank([1, 2], [1, 2]) is None
    # lower is better: predicted and true best decile coincide for a monotone map
    x = np.arange(20, dtype=float)
    assert top_decile_recall(x, x) == pytest.approx(1.0)
    assert top_decile_recall(x, x[::-1]) == pytest.approx(0.0)
    assert top_decile_recall(np.arange(5), np.arange(5)) is None
    mean = np.array([0.0, 0.0, 0.0])
    sd = np.array([1.0, 1.0, 1.0])
    assert empirical_coverage(mean, sd, np.array([0.0, 1.0, 3.0])) == pytest.approx(2 / 3)
    assert empirical_coverage(mean, sd, np.array([np.nan, 1.0, 3.0])) == pytest.approx(0.5)


def test_landscapes_cover_the_required_cases_and_components_sum_to_j():
    required = {"approximately_additive", "correlated_outputs", "independent_outputs",
                "constant_contribution", "multiple_basins", "strong_local_concentration",
                "different_length_scales", "different_magnitudes"}
    assert required.issubset(set(LANDSCAPE_NAMES))
    X = np.random.default_rng(0).random((16, 3))
    for landscape in LANDSCAPE_NAMES:
        parts = landscape_components(landscape, X)
        assert len(parts) == 5
        assert all(np.all(np.isfinite(p)) and np.all(p >= 0.0) for p in parts)
        for arm in ALL_ARM_NAMES:
            J, Y = arm_component_matrix(arm, X, landscape=landscape)
            assert Y.shape == (16, ARM_COMPONENT_COUNTS[arm])
            np.testing.assert_allclose(np.sum(Y, axis=1), J, rtol=0.0, atol=1e-12)
    const = landscape_components("constant_contribution", X)[0]
    assert np.allclose(const, const[0])


def test_comparison_runs_all_four_arms_and_records_actual_outcome():
    result = run_synthetic_model_comparison(
        landscapes=["approximately_additive", "correlated_outputs"],
        n_train=24, n_test=12, d=2, seed=3, max_iters=20)
    assert result.ok and result.status == "ok"
    assert result.research_only is True
    assert "not calibrated" in result.limitations
    assert "No acoustic improvement" in result.limitations
    assert result.config["optional_arm_status"] == OPTIONAL_ARM_STATUS
    assert result.config["include_optional"] is False
    assert result.config["optional_arm_name"] == OPTIONAL_ARM_NAME
    assert result.optional_arm_status == OPTIONAL_ARM_STATUS
    assert set(result.aggregate) == set(ARM_NAMES)
    assert OPTIONAL_ARM_NAME not in result.aggregate
    for arm in ARM_NAMES:
        aggregate = result.aggregate[arm]
        assert aggregate["components"] == ARM_COMPONENT_COUNTS[arm]
        assert aggregate["n_landscapes"] == 2
        assert aggregate["coverage_label"] == "empirical coverage of model intervals; not calibrated"
        assert aggregate["fit_time_s"] >= 0.0
    # The scalar arm must always produce a recorded outcome; a scalar win is legitimate.
    assert result.aggregate["A_scalar"]["n_ok"] >= 1
    assert result.aggregate["A_scalar"]["mae"] is not None
    # Per-landscape records expose the same fields for every arm.
    for entry in result.per_landscape:
        for arm in ARM_NAMES:
            record = entry["arms"][arm]
            for key in ("mae", "rmse", "spearman", "top_decile_recall", "coverage", "bias",
                        "fit_time_s", "acquisition_time_s", "total_cpu_s",
                        "candidate_selection_disagreement", "numerical_failures"):
                assert key in record


def test_comparison_is_deterministic_for_a_fixed_seed():
    kwargs = dict(landscapes=["approximately_additive"], n_train=20, n_test=10, d=2, seed=5,
                  max_iters=20)
    a = run_synthetic_model_comparison(**kwargs)
    b = run_synthetic_model_comparison(**kwargs)
    assert a.ok and b.ok
    for arm in ARM_NAMES:
        va = a.aggregate[arm]["mae"]
        vb = b.aggregate[arm]["mae"]
        if va is None:
            assert vb is None
        else:
            assert va == pytest.approx(vb, rel=0.0, abs=1e-12)


def test_invalid_configuration_is_refused():
    assert run_synthetic_model_comparison(landscapes=["nope"]).status == "unavailable"
    assert run_synthetic_model_comparison(n_train=2).status == "unavailable"


def test_optional_lmc_arm_runs_on_one_landscape():
    result = run_synthetic_model_comparison(
        landscapes=["approximately_additive"], n_train=24, n_test=12, d=3, seed=7,
        max_iters=20, include_optional=True)
    assert result.ok
    assert result.arms == ALL_ARM_NAMES
    assert result.optional_arm_status == OPTIONAL_ARM_STATUS == "implemented_research_only"
    assert OPTIONAL_ARM_NAME in result.aggregate
    record = result.per_landscape[0]["arms"][OPTIONAL_ARM_NAME]
    assert record["status"] == "ok"
    assert record["marker"] == "LMC"
    assert record["architecture"] == "lmc_multitask"
    assert record["optional"] is True and record["research_only"] is True
    for key in ("mae", "spearman", "coverage"):
        assert record[key] is not None and np.isfinite(record[key])
    aggregate = result.aggregate[OPTIONAL_ARM_NAME]
    assert aggregate["n_ok"] >= 1
    assert aggregate["marker"] == "LMC"
    assert aggregate["optional"] is True and aggregate["research_only"] is True
    assert "does not validate that correlation on real data" in result.limitations


def test_default_comparison_excludes_optional_arm():
    result = run_synthetic_model_comparison(
        landscapes=["approximately_additive"], n_train=20, n_test=10, d=2, seed=2,
        max_iters=20)
    assert result.optional_arm_status == OPTIONAL_ARM_STATUS
    assert result.config["include_optional"] is False
    assert result.config["optional_arm_name"] == OPTIONAL_ARM_NAME
    assert OPTIONAL_ARM_NAME not in result.aggregate
    assert set(result.per_landscape[0]["arms"]) == set(ARM_NAMES)


def test_optional_lmc_arm_is_deterministic_for_a_fixed_seed():
    kwargs = dict(landscapes=["approximately_additive"], n_train=20, n_test=10, d=3, seed=11,
                  max_iters=20, include_optional=True)
    a = run_synthetic_model_comparison(**kwargs)
    b = run_synthetic_model_comparison(**kwargs)
    assert a.ok and b.ok
    va = a.aggregate[OPTIONAL_ARM_NAME]["mae"]
    vb = b.aggregate[OPTIONAL_ARM_NAME]["mae"]
    assert va is not None and vb is not None
    assert va == pytest.approx(vb, rel=0.0, abs=1e-12)


def test_optional_lmc_failure_is_tagged_and_never_crashes(monkeypatch):
    def _fail(*args, **kwargs):
        return None, {}, "lmc_fit_failed: synthetic API mismatch"

    monkeypatch.setattr(md, "_fit_lmc", _fail)
    result = run_synthetic_model_comparison(
        landscapes=["approximately_additive"], n_train=16, n_test=10, d=2, seed=1,
        max_iters=10, include_optional=True)
    assert result.ok
    assert result.aggregate[OPTIONAL_ARM_NAME]["n_ok"] == 0
    assert result.aggregate[OPTIONAL_ARM_NAME]["numerical_failures"] == 1
    record = result.per_landscape[0]["arms"][OPTIONAL_ARM_NAME]
    assert record["status"] == "unavailable"
    assert record["optional"] is True and record["research_only"] is True
    assert "lmc_fit_failed" in record["reason"]
    # A-D still ran.
    assert result.aggregate["A_scalar"]["n_ok"] >= 1
