"""Policy integration tests for ``metric_composite_v1`` (Pass 2, lane A).

Every test is synthetic (no solver, no dataset).  The metric artifact is built with the real Pass-1
selector/artifact builder and round-tripped through Lane B's deterministic bytes loader, so the
policy is exercised against the same contract the study builder uses.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from hornlab_search.bo import metric_artifact, metric_identity, policy as policy_mod
from hornlab_search.bo.data import POOL_STATUS_NOTE, CandidatePool, PoolCandidate
from hornlab_search.bo.metric_contracts import (
    MetricTrainingCandidate,
    SelectionPolicy,
    component_names,
    component_schema_hash,
)
from hornlab_search.bo.metric_training import (
    bounds_identity,
    build_metric_training_artifact,
    select_metric_training_observations,
)
from hornlab_search.bo.policy import (
    POLICY_METRIC_COMPOSITE,
    MetricTrainingBinding,
    capability_status,
    fit_and_propose,
)
from hornlab_search.studies.production import PRODUCTION_POLICIES

D = 3
N = 18
VERSION = 10


class _Encoding:
    version = "test-active-projection-v1"

    def __init__(self, *, active_keys=None, hi=1.0, log=False):
        self.d = D
        self.active_keys = tuple(active_keys or (f"k{i}" for i in range(D)))
        self.fixed_values = {}
        self._hi = float(hi)
        self._log = bool(log)

    def key_transforms(self):
        lo = 0.1 if self._log else 0.0
        return {key: {"lo": lo, "hi": self._hi, "log": self._log,
                      "transform": "log10" if self._log else "identity", "active": True}
                for key in self.active_keys}


ENC = _Encoding()


def _identity(encoding=ENC):
    payload = metric_identity.bounds_payload(encoding, strict=True)
    score_payload = metric_identity.score_payload(
        objective_version=VERSION, brief_hash="a" * 64, score_hash="b" * 64)
    return {
        "brief_hash": "a" * 64,
        "score_hash": "b" * 64,
        "score_identity": metric_identity.recompute_score_hash(score_payload),
        "score_identity_payload": score_payload,
        "task_identity": "c" * 64,
        "backend": "beat_cuda",
        "fidelity": "screen",
        "grid_hash": "d" * 64,
        "dependency_hash": "e" * 64,
        "mesh_hash": "f" * 64,
        "objective_version": VERSION,
        "bounds_hash": metric_identity.recompute_bounds_hash(payload),
        "bounds_identity_payload": payload,
        "active_keys": list(payload["active_keys"]),
        "projection_version": payload["projection_version"],
        "component_schema": "v10-metric-components-v1",
        "component_schema_hash": component_schema_hash(VERSION),
    }


def _expected_task():
    meta = _identity()
    return {key: meta[key] for key in ("task_identity", "backend", "fidelity", "grid_hash",
                                       "dependency_hash")}


def _expected_score():
    return dict(_identity()["score_identity_payload"])


def _records(encoding=ENC):
    rng = np.random.default_rng(7)
    names = component_names(VERSION)
    meta = _identity(encoding)
    records = []
    for i in range(N):
        j = float(i) / 10.0
        records.append(MetricTrainingCandidate(
            observation_id=f"obs-{i:02d}", x=rng.uniform(0.05, 0.35, D), J=j,
            objective_version=VERSION, design_hash=f"design-{i:02d}", solve_id=f"solve-{i:02d}",
            brief_hash=meta["brief_hash"],
            score_hash=meta["score_hash"], task_identity=meta["task_identity"],
            backend=meta["backend"], fidelity=meta["fidelity"], grid_hash=meta["grid_hash"],
            dependency_hash=meta["dependency_hash"], mesh_hash=meta["mesh_hash"],
            active_keys=encoding.active_keys, bounds_hash=meta["bounds_hash"],
            status="ok", components=np.array([j, 0.0, 0.0, 0.0]), component_names=names))
    return records


def _selection(encoding=ENC):
    selection = select_metric_training_observations(
        _records(encoding), encoding=encoding,
        policy=SelectionPolicy(n_max=64, elite_n=32))
    assert selection.ok, selection.reasons
    return selection


def _artifact_and_binding(encoding=ENC):
    selection = _selection(encoding)
    meta = _identity(encoding)
    artifact = build_metric_training_artifact(selection, identity_metadata=meta)
    assert artifact.ok, artifact.reasons
    blob = metric_artifact.artifact_bytes(artifact)
    loaded, check = metric_artifact.artifact_from_bytes(blob, expected_checksum=artifact.checksum)
    assert check.ok and loaded is not None, check.detail
    binding = MetricTrainingBinding(
        artifact=loaded, encoding=encoding,
        expected_bounds_hash=meta["bounds_hash"], expected_score=_expected_score(),
        expected_task=_expected_task(), component_schema=meta["component_schema_hash"])
    return loaded, binding, meta


def _pool(n=4, d=D, start=0.8):
    candidates = tuple(
        PoolCandidate(
            candidate_id=f"c{i}", pool_index=i, seed=0,
            active_vector=np.array([start - 0.1 * i, 0.10 + 0.05 * i, 0.90 - 0.05 * i]),
            full_vector=np.zeros(d + 1), design_hash=f"design-{i}",
            geometry_hash=f"geometry-{i}", intended_solve_hash=f"solve-{i}",
            params={}, descriptors={}, checks={})
        for i in range(n))
    return CandidatePool(status="ok", requested=n, seed=0, seeds_tried=(0,),
                         candidates=candidates, counts={}, seed_reports=(),
                         intended_solve_hash=None, note=POOL_STATUS_NOTE)


@pytest.fixture(scope="module")
def fixture():
    return _artifact_and_binding()


# --------------------------------------------------------------------------- registration


def test_metric_policy_is_appended_and_opt_in_only():
    assert POLICY_METRIC_COMPOSITE == "metric_composite_v1"
    assert policy_mod.PROPOSAL_POLICIES[-1] == POLICY_METRIC_COMPOSITE
    assert policy_mod.PROPOSAL_POLICIES[:5] == (
        "scalar", "pareto", "cma_seed", "exploration", "turbo")
    assert POLICY_METRIC_COMPOSITE in policy_mod.ENGINE_POLICIES
    assert policy_mod.verification_mode(POLICY_METRIC_COMPOSITE) == "scalar"
    # Production execution deliberately stays scalar/turbo/pareto only.
    assert PRODUCTION_POLICIES == ("scalar", "turbo", "pareto")
    assert POLICY_METRIC_COMPOSITE not in PRODUCTION_POLICIES


# --------------------------------------------------------------------------- capability ok


def test_capability_ok_with_strict_identities(fixture, monkeypatch):
    _, binding, meta = fixture
    monkeypatch.setattr(policy_mod, "_engine_available", lambda: True)
    cap = capability_status(POLICY_METRIC_COMPOSITE, metric_training=binding, pool=_pool())
    assert cap["status"] == "ok", cap
    assert cap["reason"] == "ok"
    assert cap["verification_mode"] == "scalar"
    assert cap["objective_version"] == VERSION
    assert cap["artifact_checksum"]
    assert cap["bounds_hash"] == meta["bounds_hash"]
    assert cap["n"] == N and cap["d"] == D and cap["m"] == 4
    assert cap["required_inputs"] == ["metric_training", "pool"]


# --------------------------------------------------------------------------- capability refusals


def _cap(fixture, *, binding=None, pool=..., monkeypatch=None):
    if monkeypatch is not None:
        monkeypatch.setattr(policy_mod, "_engine_available", lambda: True)
    binding = binding if binding is not None else fixture[1]
    if pool is ...:
        pool = _pool()
    return capability_status(POLICY_METRIC_COMPOSITE, metric_training=binding, pool=pool)


def test_missing_artifact_is_a_typed_refusal(monkeypatch):
    monkeypatch.setattr(policy_mod, "_engine_available", lambda: True)
    cap = capability_status(POLICY_METRIC_COMPOSITE, metric_training=None, pool=_pool())
    assert cap["status"] == "unavailable"
    assert cap["reason"] == policy_mod.REASON_METRIC_TRAINING_REQUIRED


def test_missing_bounds_identity_refuses(fixture, monkeypatch):
    _, binding, _ = fixture
    broken = dataclasses.replace(binding, expected_bounds_hash="")
    cap = _cap(fixture, binding=broken, monkeypatch=monkeypatch)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == policy_mod.REASON_METRIC_BOUNDS_IDENTITY


def test_wrong_bounds_hash_refuses(fixture, monkeypatch):
    _, binding, _ = fixture
    broken = dataclasses.replace(binding, expected_bounds_hash="9" * 64)
    cap = _cap(fixture, binding=broken, monkeypatch=monkeypatch)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == policy_mod.REASON_METRIC_BOUNDS_IDENTITY


def test_same_dimension_different_box_refuses(fixture, monkeypatch):
    _, binding, meta = fixture
    wider = _Encoding(hi=2.0)
    broken = dataclasses.replace(
        binding, encoding=wider,
        expected_bounds_hash=bounds_identity(wider))
    cap = _cap(fixture, binding=broken, monkeypatch=monkeypatch)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == policy_mod.REASON_METRIC_BOUNDS_IDENTITY
    assert broken.expected_bounds_hash != meta["bounds_hash"]


def test_changed_transform_refuses(fixture, monkeypatch):
    _, binding, _ = fixture
    logged = _Encoding(log=True)
    broken = dataclasses.replace(binding, encoding=logged,
                                 expected_bounds_hash=bounds_identity(logged))
    cap = _cap(fixture, binding=broken, monkeypatch=monkeypatch)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == policy_mod.REASON_METRIC_BOUNDS_IDENTITY


def test_changed_active_order_refuses(fixture, monkeypatch):
    _, binding, _ = fixture
    reordered = _Encoding(active_keys=("k2", "k1", "k0"))
    broken = dataclasses.replace(binding, encoding=reordered,
                                 expected_bounds_hash=bounds_identity(reordered))
    cap = _cap(fixture, binding=broken, monkeypatch=monkeypatch)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == policy_mod.REASON_METRIC_BOUNDS_IDENTITY


def test_missing_score_identity_refuses(fixture, monkeypatch):
    _, binding, _ = fixture
    broken = dataclasses.replace(binding, expected_score={})
    cap = _cap(fixture, binding=broken, monkeypatch=monkeypatch)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == policy_mod.REASON_METRIC_SCORE_IDENTITY


def test_wrong_score_identity_refuses(fixture, monkeypatch):
    _, binding, _ = fixture
    wrong = dict(binding.expected_score, score_hash="1" * 64)
    broken = dataclasses.replace(binding, expected_score=wrong)
    cap = _cap(fixture, binding=broken, monkeypatch=monkeypatch)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == policy_mod.REASON_METRIC_SCORE_IDENTITY


def test_wrong_component_schema_refuses(fixture, monkeypatch):
    artifact, binding, _ = fixture
    swapped = dataclasses.replace(
        artifact, component_names=tuple(reversed(artifact.component_names)))
    broken = dataclasses.replace(binding, artifact=swapped)
    cap = _cap(fixture, binding=broken, monkeypatch=monkeypatch)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == policy_mod.REASON_METRIC_COMPONENT_SCHEMA


def test_missing_engine_refuses_with_a_metric_reason(fixture, monkeypatch):
    monkeypatch.setattr(policy_mod, "_engine_available", lambda: False)
    cap = capability_status(POLICY_METRIC_COMPOSITE, metric_training=fixture[1], pool=_pool())
    assert cap["status"] == "capability_missing"
    assert cap["reason"] == policy_mod.REASON_METRIC_ENGINE_MISSING


def test_missing_pool_refuses(fixture, monkeypatch):
    cap = _cap(fixture, pool=None, monkeypatch=monkeypatch)
    assert cap["status"] == "unavailable"
    assert cap["reason"] == policy_mod.REASON_LEGAL_POOL_REQUIRED


# --------------------------------------------------------------------------- fit/propose


def test_fit_and_propose_metric_returns_tagged_predictions(fixture):
    _, binding, meta = fixture
    out = fit_and_propose(POLICY_METRIC_COMPOSITE, metric_training=binding, pool=_pool(),
                          seed=0)
    assert out.status == "ok", out.reason
    assert out.policy == POLICY_METRIC_COMPOSITE
    assert out.verification_mode == "scalar"
    assert out.fallback is False
    assert out.proposal is not None and out.proposal["candidate_id"]
    assert set(out.predicted) == {"component_means", "component_sds", "j_mean", "total_sd",
                                  "note"}
    assert out.predicted["note"] == "model prediction, not a solved acoustic result"
    assert len(out.predicted["component_means"]) == 4
    assert out.acquisition["units"] == (
        "qLogNEI (technical ranking only, not J and not a probability)")
    assert out.acquisition["policy"] == POLICY_METRIC_COMPOSITE
    assert out.acquisition["value"] is not None
    assert out.acquisition["value"] != out.predicted["j_mean"]
    assert out.model_hyperparameters["model_hash"]


def test_fit_and_propose_missing_artifact_never_falls_back_to_scalar():
    out = fit_and_propose(POLICY_METRIC_COMPOSITE, metric_training=None, pool=_pool())
    assert out.status == "unavailable"
    assert out.reason == policy_mod.REASON_METRIC_TRAINING_REQUIRED
    assert out.proposal is None and out.predicted is None and out.acquisition is None
    assert out.fallback is False


def test_existing_policies_keep_their_verification_modes_and_scalar_default(
        monkeypatch):
    for policy in ("scalar", "cma_seed", "exploration", "turbo"):
        assert policy_mod.verification_mode(policy) == "scalar"
    assert policy_mod.verification_mode("pareto") == "pareto"
    cap = capability_status("mystery")
    assert cap["reason"] == "unsupported_policy"
    # No default selection changed: an unknown policy still refuses, never maps to metric.
    assert capability_status("scalar")["reason"] == "training_set_required"
