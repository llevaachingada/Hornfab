"""Focused tests for the B7 unified proposal-policy dispatcher (bo/policy.py).

These tests are offline: the dispatcher route tests monkeypatch the engines, and capability
tests never need BoTorch.  A subprocess import guard proves that importing ``hornlab_search.bo``
does not import torch/botorch.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import hornlab_search.bo as bo
import hornlab_search.bo.policy as policy_mod
from hornlab_search.bo import (
    PARETO_POLICY,
    PROPOSAL_POLICIES,
    PROPOSAL_POLICY_LABELS,
    CandidatePool,
    ParetoFit,
    PoolCandidate,
    ProposalHistory,
    ProposalResult,
    TrustRegion,
    acquisition_scores,
    build_training_set,
    capability_status,
    fit_and_propose,
    frozen_reference,
    make_pure_observations,
    nondominated,
    select_subset,
    verification_mode,
)
from hornlab_search.bo.cohort import CohortResult
from hornlab_search.bo.data import POOL_STATUS_NOTE, TrainingObservation
from hornlab_search.bo.metrics import MetricObservation

HAS_BOTORCH = importlib.util.find_spec("botorch") is not None
HASH_A = "a" * 64
HASH_B = "b" * 64


# --------------------------------------------------------------------------- fixtures


def _training(n=16, d=2):
    return build_training_set(make_pure_observations(d, n, seed=1), d=d)


def _cohort(observation_ids=("o0", "o1", "o2", "o3"), metric_hash=HASH_A):
    observations = tuple(
        TrainingObservation(f"{oid}", np.array([i / 4.0, 1.0 - i / 4.0]), float(i),
                            geometry_hash=f"g{i}", solve_hash=f"s{i}")
        for i, oid in enumerate(observation_ids))
    identity = (
        ("metric_policy", "bo.physical_metric_spec_hash", json.dumps(metric_hash)),
        ("frequency_masks", "bo.physical_metric_spec_hash", json.dumps(metric_hash)),
    )
    return CohortResult("ok", (), observations, identity)


def _metric_observations(observation_ids=("o0", "o1", "o2", "o3"), metric_hash=HASH_A,
                         coverage=(1.0, 2.0, 3.0, 4.0), ripple=(4.0, 3.0, 2.0, 1.0),
                         status="complete"):
    return {
        oid: MetricObservation(status, None, metric_hash, cov, rip)
        for oid, cov, rip in zip(observation_ids, coverage, ripple)
    }


def _pool(vectors, *, status="ok", seeds=(0,)):
    candidates = []
    for i, vector in enumerate(vectors):
        arr = np.asarray(vector, dtype=float).reshape(-1)
        candidates.append(PoolCandidate(
            candidate_id=f"c{i:02d}", pool_index=i, seed=int(seeds[0]),
            active_vector=arr.copy(), full_vector=arr.copy(),
            design_hash=f"d{i:02d}", geometry_hash=f"g{i:02d}",
            intended_solve_hash="solve-0", params={}, descriptors={}, checks={}))
    return CandidatePool(
        status=status, requested=len(candidates), seed=0, seeds_tried=tuple(seeds),
        candidates=tuple(candidates), counts={}, seed_reports=(),
        intended_solve_hash="solve-0", note=POOL_STATUS_NOTE)


# --------------------------------------------------------------------------- imports/exports


def test_importing_bo_does_not_import_torch_or_botorch():
    code = (
        "import sys\n"
        "import hornlab_search.bo\n"
        "assert 'torch' not in sys.modules, 'torch was imported eagerly'\n"
        "assert 'botorch' not in sys.modules, 'botorch was imported eagerly'\n"
        "assert 'gpytorch' not in sys.modules, 'gpytorch was imported eagerly'\n"
        "print('ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-B", "-c", code], capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parents[1]))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"


def test_export_surface_is_complete():
    expected = {
        "PARETO_POLICY", "fit_pareto", "propose_pareto", "frozen_reference", "nondominated",
        "select_subset", "ParetoFit", "acquisition_scores", "fit_constrained_pareto",
        "loading_margins", "cost_aware_log_score", "fit_cost_model", "TrustRegion",
        "trust_box", "update_trust_region",
        "PROPOSAL_POLICIES", "PROPOSAL_POLICY_LABELS", "ProposalOutcome",
        "capability_status", "fit_and_propose", "verification_mode", "propose_by_policy",
        "POLICY_SCALAR", "POLICY_PARETO", "POLICY_CMA_SEED", "POLICY_EXPLORATION",
    }
    assert expected <= set(bo.__all__)
    for name in expected:
        assert hasattr(bo, name), name
    assert PARETO_POLICY == "pareto_pool_v1"
    assert TrustRegion is bo.TrustRegion
    assert PROPOSAL_POLICIES == ("scalar", "pareto", "cma_seed", "exploration")
    assert set(PROPOSAL_POLICY_LABELS) == set(PROPOSAL_POLICIES)
    assert "trade-off" in PROPOSAL_POLICY_LABELS["pareto"]
    assert "seed" in PROPOSAL_POLICY_LABELS["cma_seed"].lower()
    assert PROPOSAL_POLICY_LABELS["exploration"] == "fixed exploration"


def test_verification_modes_are_frozen():
    assert verification_mode("pareto") == "pareto"
    for policy in ("scalar", "cma_seed", "exploration"):
        assert verification_mode(policy) == "scalar"
    with pytest.raises(ValueError):
        verification_mode("not-a-policy")


# --------------------------------------------------------------------------- capability gates


def test_scalar_capability_requires_training_data_and_engine():
    assert capability_status("scalar")["status"] == "unavailable"
    assert capability_status("scalar")["reason"] == "training_set_required"
    small = build_training_set(make_pure_observations(2, 5, seed=1), d=2)
    cap = capability_status("scalar", training_set=small)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == "insufficient_training_data"
    good = _training()
    cap = capability_status("scalar", training_set=good)
    expected = "ok" if HAS_BOTORCH else "capability_missing"
    assert cap["status"] == expected
    assert cap["data_status"] == "ok"
    assert cap["engine_status"] == ("ok" if HAS_BOTORCH else "capability_missing")


def test_pareto_capability_refuses_unvalidated_or_incomplete_evidence():
    assert capability_status("pareto")["reason"] == "validated_cohort_required"
    assert capability_status(
        "pareto", cohort=SimpleNamespace(ok=False, observations=()))["reason"] == \
        "validated_cohort_required"
    cohort = _cohort()
    assert capability_status("pareto", cohort=cohort)["reason"] == \
        "metric_observation_bindings_required"

    mismatched = _metric_observations(metric_hash=HASH_B)
    cap = capability_status("pareto", cohort=cohort, metric_observations=mismatched)
    assert cap["data_status"] == "unavailable"
    assert cap["reason"] == "metric_observation_incomplete_or_incompatible"

    partial = _metric_observations(status="capability_missing")
    cap = capability_status("pareto", cohort=cohort, metric_observations=partial)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == "metric_observation_incomplete_or_incompatible"

    missing = _metric_observations()
    missing.pop("o2")
    cap = capability_status("pareto", cohort=cohort, metric_observations=missing)
    assert cap["reason"] == "metric_observation_binding_mismatch"


def test_pareto_capability_accepts_valid_fixture_and_frozen_reference(monkeypatch):
    cohort, metrics = _cohort(), _metric_observations()
    monkeypatch.setattr(policy_mod, "_engine_available", lambda: True)
    cap = capability_status("pareto", cohort=cohort, metric_observations=metrics)
    assert cap["status"] == "ok", cap
    assert cap["verification_mode"] == "pareto"
    assert cap["data_status"] == "ok"
    assert cap["frozen_reference"]["ref_point"] == pytest.approx([-4.3, -4.3])

    monkeypatch.setattr(policy_mod, "_engine_available", lambda: False)
    cap = capability_status("pareto", cohort=cohort, metric_observations=metrics)
    assert cap["status"] == "capability_missing"
    assert cap["engine_status"] == "capability_missing"
    assert cap["data_status"] == "ok"


def test_scalar_engine_absence_is_a_clean_capability_refusal(monkeypatch):
    monkeypatch.setattr(policy_mod, "_engine_available", lambda: False)
    cap = capability_status("scalar", training_set=_training())
    assert cap["status"] == "capability_missing"
    assert cap["reason"] == "capability_missing"
    assert "engine" in (cap["detail"] or "").lower()


def test_unknown_policy_is_refused():
    cap = capability_status("mystery")
    assert cap["status"] == "unavailable"
    assert cap["reason"] == "unsupported_policy"
    assert cap["verification_mode"] is None
    out = fit_and_propose("mystery")
    assert not out.ok and out.reason == "unsupported_policy"
    assert out.predicted is None and out.proposal is None


# --------------------------------------------------------------------------- scalar routing


def test_scalar_routes_fit_then_propose(monkeypatch):
    calls = {}

    def fake_fit(training_set, seed=0):
        calls["fit"] = (training_set, seed)
        return SimpleNamespace(status="ok", reason="ok")

    def fake_propose(model_result, pool, history=None, *, encoding=None, config=None,
                     resolution_mm=30.0):
        calls["propose"] = (model_result, pool, history, encoding, config, resolution_mm)
        return ProposalResult(
            status="ok", reason="ok", selection_reason="acquisition",
            candidate={"candidate_id": "chosen"}, predicted={"j_mean": 1.5},
            acquisition={"value": 2.5}, counts={"legal": 1},
            library_versions={"engine": "botorch"})

    monkeypatch.setattr(policy_mod._model, "fit_model", fake_fit)
    monkeypatch.setattr(policy_mod._propose, "propose_one", fake_propose)
    history = ProposalHistory(proposal_index=3)
    out = fit_and_propose("scalar", training_set=object(), pool=object(), history=history,
                          seed=7, encoding="enc", config="cfg", resolution_mm=12.0)
    assert out.ok and out.policy == "scalar" and out.verification_mode == "scalar"
    assert out.proposal == {"candidate_id": "chosen"}
    assert out.predicted == {"j_mean": 1.5}
    assert out.selection_reason == "acquisition"
    assert calls["fit"][1] == 7
    assert calls["propose"][1] is not None and calls["propose"][2] is history
    assert calls["propose"][3:] == ("enc", "cfg", 12.0)


def test_scalar_fit_failure_is_propagated_without_predictions(monkeypatch):
    monkeypatch.setattr(
        policy_mod._model, "fit_model",
        lambda *a, **k: SimpleNamespace(status="unavailable", reason="insufficient_data",
                                       detail="too few rows", library_versions={}))
    out = fit_and_propose("scalar", training_set=object(), pool=object())
    assert out.status == "unavailable" and out.reason == "insufficient_data"
    assert out.proposal is None and out.predicted is None and out.acquisition is None
    assert out.detail == "too few rows"


def test_scalar_capability_failure_keeps_the_tag(monkeypatch):
    monkeypatch.setattr(
        policy_mod._model, "fit_model",
        lambda *a, **k: SimpleNamespace(status="unavailable", reason="capability_missing",
                                       detail="no engine", library_versions={}))
    out = fit_and_propose("scalar", training_set=object(), pool=object())
    assert out.status == "capability_missing"
    assert out.reason == "capability_missing"
    assert out.predicted is None


def test_scalar_propose_failure_is_propagated(monkeypatch):
    monkeypatch.setattr(
        policy_mod._model, "fit_model",
        lambda *a, **k: SimpleNamespace(status="ok", reason="ok"))
    monkeypatch.setattr(
        policy_mod._propose, "propose_one",
        lambda *a, **k: ProposalResult(
            status="unavailable", reason="pool_exhausted", candidate=None, predicted=None))
    out = fit_and_propose("scalar", training_set=object(), pool=object())
    assert out.status == "pool_exhausted"
    assert out.reason == "pool_exhausted"
    assert out.proposal is None and out.predicted is None


# --------------------------------------------------------------------------- Pareto routing


def _fake_pareto_fit(*args, **kwargs):
    return ParetoFit("ok", "ok", model=object(), train_X=np.zeros((2, 2)),
                     reference={"ref_point": [-3.0, -3.0]},
                     outputs=(object(), object()))


def test_pareto_routes_fit_then_propose(monkeypatch):
    calls = {}

    def fake_fit(cohort, metric_observations, seed=0):
        calls["fit"] = (cohort, metric_observations, seed)
        return _fake_pareto_fit()

    def fake_propose(fit, pool, history, *, encoding, config, seed=0, resolution_mm=30.0):
        calls["propose"] = (fit, pool, history, seed)
        return {
            "status": "ok",
            "candidate": {"candidate_id": "pareto-1"},
            "physical_predictions": {"coverage_deg": {"mean": 1.0},
                                     "ripple_db": {"mean": 2.0}},
            "acquisition_value": 4.5,
            "selection_reason": "qLogNEHVI",
            "reference": {"ref_point": [-3.0, -3.0]},
            "counts": {"legal": 2},
            "note": "Coverage/ripple trade-off frontier",
        }

    monkeypatch.setattr(policy_mod._pareto, "fit_pareto", fake_fit)
    monkeypatch.setattr(policy_mod._pareto, "propose_pareto", fake_propose)
    history = ProposalHistory(proposal_index=1)
    out = fit_and_propose("pareto", cohort="cohort", metric_observations={"o0": object()},
                          pool="pool", history=history, seed=11, encoding="enc", config="cfg")
    assert out.ok and out.policy == "pareto" and out.verification_mode == "pareto"
    assert out.proposal == {"candidate_id": "pareto-1"}
    assert out.predicted == {"coverage_deg": {"mean": 1.0}, "ripple_db": {"mean": 2.0}}
    assert out.acquisition["value"] == 4.5
    assert out.acquisition["reference"] == {"ref_point": [-3.0, -3.0]}
    assert calls["fit"][2] == 11
    assert calls["propose"][1] == "pool" and calls["propose"][3] == 11


def test_pareto_fit_failure_is_propagated(monkeypatch):
    called = []
    monkeypatch.setattr(
        policy_mod._pareto, "fit_pareto",
        lambda *a, **k: ParetoFit("unavailable", "validated_cohort_required"))
    monkeypatch.setattr(
        policy_mod._pareto, "propose_pareto",
        lambda *a, **k: called.append(True))
    out = fit_and_propose("pareto", cohort=object(), metric_observations={}, pool=object())
    assert out.status == "unavailable"
    assert out.reason == "validated_cohort_required"
    assert out.predicted is None and out.proposal is None
    assert not called


def test_pareto_pool_exhaustion_is_tagged(monkeypatch):
    monkeypatch.setattr(policy_mod._pareto, "fit_pareto", _fake_pareto_fit)
    monkeypatch.setattr(
        policy_mod._pareto, "propose_pareto",
        lambda *a, **k: {"status": "unavailable", "reason": "pool_exhausted"})
    out = fit_and_propose("pareto", cohort=object(), metric_observations={}, pool=object())
    assert out.status == "pool_exhausted"
    assert out.reason == "pool_exhausted"
    assert out.predicted is None and out.acquisition is None


# --------------------------------------------------------------------------- CMA seed pack


def test_cma_seed_selection_is_deterministic_and_non_bo():
    seeds = [
        {"source": "S5", "seed": 2, "cheap_checks_passed": True, "candidate_id": "b"},
        {"source": "S5", "seed": 1, "cheap_checks_passed": True, "candidate_id": "a"},
    ]
    first = fit_and_propose("cma_seed", cma_seed_candidates=seeds)
    second = fit_and_propose("cma_seed", cma_seed_candidates=list(reversed(seeds)))
    assert first.ok and second.ok
    assert first.selection_reason == "cma_archive_seed"
    assert first.proposal["seed_identity"] == second.proposal["seed_identity"] == "S5|1"
    assert first.proposal["eligibility"] == "passed"
    assert first.predicted is None and first.acquisition is None
    assert first.verification_mode == "scalar"
    assert "non-BO" in first.detail


def test_cma_seed_prefers_passed_over_unknown():
    seeds = [
        {"source": "arch", "seed": 1, "eligibility": "unknown"},
        {"source": "arch", "seed": 2, "cheap_checks_passed": True},
    ]
    out = fit_and_propose("cma_seed", cma_seed_candidates=seeds)
    assert out.proposal["seed_identity"] == "arch|2"
    assert out.proposal["eligibility"] == "passed"
    assert out.counts == {"input": 2, "passed": 1, "unknown": 1, "rejected": 0,
                          "selectable": 2}


def test_cma_seed_refuses_absent_duplicate_and_invalid_seeds():
    absent = fit_and_propose("cma_seed", cma_seed_candidates=None)
    assert absent.status == "unavailable" and absent.reason == "explicit_seed_candidates_required"

    duplicate = fit_and_propose("cma_seed", cma_seed_candidates=[
        {"source": "S5", "seed": 1, "cheap_checks_passed": True},
        {"source": "S5", "seed": 1, "eligibility": "unknown"},
    ])
    assert duplicate.status == "unavailable" and duplicate.reason == "duplicate_seed_identity"

    invalid = fit_and_propose("cma_seed", cma_seed_candidates=[
        {"source": "S5", "seed": 1},
    ])
    assert invalid.status == "unavailable" and invalid.reason == "invalid_seed_candidate"

    rejected = fit_and_propose("cma_seed", cma_seed_candidates=[
        {"source": "S5", "seed": 1, "cheap_checks_passed": False},
    ])
    assert rejected.status == "unavailable" and rejected.reason == "no_eligible_seed"

    no_identity = fit_and_propose("cma_seed", cma_seed_candidates=[
        {"seed": 1, "cheap_checks_passed": True},
    ])
    assert no_identity.status == "unavailable"
    assert no_identity.reason == "invalid_seed_candidate"


def test_cma_seed_capability_status():
    monkeypatch_ok = capability_status(
        "cma_seed", seeds=[{"source": "S5", "seed": 1, "eligibility": "unknown"}])
    assert monkeypatch_ok["status"] == "ok"
    assert monkeypatch_ok["engine_status"] == "not_required"
    assert monkeypatch_ok["verification_mode"] == "scalar"
    assert capability_status("cma_seed")["reason"] == "explicit_seed_candidates_required"


# --------------------------------------------------------------------------- exploration


def test_exploration_uses_maximin_and_is_labelled_non_bo(monkeypatch):
    checked = []
    monkeypatch.setattr(
        policy_mod._propose, "validate_selected_candidate",
        lambda candidate, *a, **k: checked.append(candidate.geometry_hash))
    out = fit_and_propose("exploration", pool=_pool([[0.1, 0.2], [0.7, 0.8], [0.4, 0.5]]),
                          history=ProposalHistory(), encoding=object(), config=object())
    assert out.ok, out.reason
    assert out.selection_reason == "maximin_exploration"
    assert out.predicted is None and out.acquisition is None
    assert out.verification_mode == "scalar"
    assert "non-BO" in out.detail
    assert checked == [out.proposal["geometry_hash"]]


def test_exploration_refuses_absent_or_exhausted_pool():
    absent = fit_and_propose("exploration", pool=None)
    assert absent.status == "unavailable" and absent.reason == "legal_pool_required"

    exhausted = fit_and_propose("exploration", pool=_pool([], status="pool_exhausted"))
    assert exhausted.status == "pool_exhausted"
    assert exhausted.reason == "pool_exhausted"

    empty = fit_and_propose("exploration", pool=_pool([]))
    assert empty.status == "pool_exhausted"

    bad_vector = _pool([[float("nan"), 0.2]])
    invalid = fit_and_propose("exploration", pool=bad_vector)
    assert invalid.status == "pool_exhausted"


def test_exploration_filters_known_history(monkeypatch):
    pool = _pool([[0.1, 0.2], [0.7, 0.8]])
    monkeypatch.setattr(policy_mod._propose, "validate_selected_candidate", lambda *a, **k: None)
    history = ProposalHistory(excluded_geometry_hashes=("g00", "g01"))
    out = fit_and_propose("exploration", pool=pool, history=history,
                          encoding=object(), config=object())
    assert out.status == "pool_exhausted"
    assert out.reason == "pool_exhausted"


# --------------------------------------------------------------------------- hypervolume/reference


def test_constraint_columns_cannot_enter_reference_or_front():
    errors = np.array([[1.0, 4.0], [2.0, 3.0], [3.0, 2.0], [4.0, 1.0]])
    assert nondominated(errors).tolist() == [True, True, True, True]
    reference = frozen_reference(errors)
    assert len(reference["ref_point"]) == 2
    assert len(reference["limits"]) == 2
    assert all(value < 0 for value in reference["ref_point"])
    assert reference["ref_point"] == pytest.approx([-4.3, -4.3])
    # A three-column margin matrix is refused outright: margins are never hypervolume axes.
    with pytest.raises(ValueError):
        frozen_reference(np.ones((4, 3)))
    with pytest.raises(ValueError):
        select_subset(np.zeros((4, 2)), np.ones((4, 3)), np.zeros(4),
                      ["a", "b", "c", "d"])


def test_acquisition_failure_never_fabricates_values():
    scores = acquisition_scores(SimpleNamespace(status="unavailable", reason="capability_missing"),
                                [[0.1], [0.2]])
    assert scores["status"] == "unavailable"
    assert "values" not in scores


# --------------------------------------------------------------------------- delegation


def test_propose_by_policy_delegates_to_the_dispatcher():
    out = bo.propose_by_policy(
        "cma_seed", cma_seed_candidates=[{"source": "S5", "seed": 3,
                                          "eligibility": "unknown"}])
    assert out.ok
    assert out.policy == "cma_seed"
    assert out.proposal["seed_identity"] == "S5|3"
