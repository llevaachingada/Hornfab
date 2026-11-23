"""Metric-composite builder/service integration tests (Pass 2, lane A).

All fixtures are synthetic: a real ``StudyService`` registry in ``tmp_path``, a synthetic frozen
snapshot, a real ``metric-training-v1`` artifact round-tripped through Lane B's bytes loader, a real
CPU multi-output GP fit, and a pure-Python synthetic evaluator.  No mesh, BEM/GPU, pipeline or
dataset call is made.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from hornlab_search.bo import metric_artifact, metric_identity
from hornlab_search.bo.metric_model import fit_metric_model
from hornlab_search.studies import builders, metric_study
from hornlab_search.studies.metric_study import (
    METRIC_POLICY,
    MetricSyntheticEvaluator,
    build_metric_model,
    build_metric_pool,
    build_metric_proposal,
    build_metric_training,
    metric_bindings,
    metric_execution_gate,
    prepare_metric_run_package,
)
from hornlab_search.studies.production import ProductionJournal
from hornlab_search.studies.schema import PROTOCOL, canonical
from hornlab_search.studies.service import StudyService

from test_bo_policy_metric import ENC, _identity, _pool, _selection


def _deadline(hours=1):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _snapshot(service, sid):
    meta = _identity()
    snapshot = {
        "tool": "study_snapshot",
        "schema": builders.SNAPSHOT_SCHEMA,
        "schema_version": 1,
        "protocol": PROTOCOL,
        "generated_utc": "2026-11-22T00:00:00+00:00",
        "study_id": sid,
        "revision": 1,
        "task": {
            "config": "synthetic://metric/config.yaml",
            "config_sha256": meta["task_identity"],
            "brief": "synthetic://metric/brief.yaml",
            "brief_sha256": meta["brief_hash"],
            "objective_version": 10,
            "resolved_target": {"band_lo_hz": 700.0, "band_hi_hz": 8000.0},
        },
        "source": {"scores_json_sha256": "1" * 64, "catalog_csv_sha256": "2" * 64},
        "no_backend_calls": True,
    }
    service.attach_artifact(sid, 1, "snapshot", canonical(snapshot).encode("utf-8"), {},
                            "snapshot:metric:test")


def _study(tmp_path):
    service = StudyService(tmp_path / "registry")
    study = service.create_study({"protocol": PROTOCOL}, "create")
    sid = study["id"]
    _snapshot(service, sid)
    return service, sid


def _stages(tmp_path, *, seed=0):
    """Attach snapshot -> metric training -> model -> pool -> proposal -> package."""
    service, sid = _study(tmp_path)
    training = build_metric_training(
        service, sid, root=tmp_path, selection=_selection(), identity_metadata=_identity())
    model = build_metric_model(service, sid, root=tmp_path, seed=seed)
    pool = build_metric_pool(service, sid, root=tmp_path, pool=_pool(n=10))
    proposal = build_metric_proposal(service, sid, root=tmp_path, seed=seed)
    package = prepare_metric_run_package(
        service, sid, lane="cpu", deadline=_deadline(), idempotency_key="metric-package:test")
    return {
        "service": service, "sid": sid, "training": training, "model": model,
        "pool": pool, "proposal": proposal, "package": package,
    }


def _runtime(stages):
    artifact, manifest, training_meta, manifest_meta = metric_study._load_training_artifact(
        stages["service"], stages["sid"])
    model_manifest = metric_study._json(stages["service"], stages["sid"], "model")
    fitted = fit_metric_model(artifact, seed=int(model_manifest["seed"]))
    assert fitted.status == "ok", fitted.reason
    pool = metric_study._load_pool_object(stages["service"], stages["sid"])
    return artifact, fitted, pool, (manifest.get("bounds") or {}).get("hash") or ""


def synthetic_result(candidate, attempt_id):
    """Deterministic pure-Python acoustic stand-in: J is the mean of the active vector."""
    vector = np.asarray(candidate["x"], dtype=float).reshape(-1)
    j = float(np.mean(vector)) + 0.05
    return {
        "solve_id": candidate["solve_id"],
        "kind": "screen",
        "call_status": "called",
        "outcome": "success",
        "eligible": True,
        "observed_j": j,
        "components": [j, 0.0, 0.0, 0.0],
        "physical_id": "synthetic:" + candidate["solve_id"],
        "score_id": "synthetic-score:" + candidate["solve_id"],
        "x": candidate["x"],
        "params": candidate.get("params") or {},
    }


# --------------------------------------------------------------------------- builder stage


def test_builder_stage_attaches_training_model_pool_proposal_and_package(tmp_path):
    stages = _stages(tmp_path)
    service, sid = stages["service"], stages["sid"]
    for kind in (metric_study.METRIC_TRAINING_KIND,
                 metric_study.METRIC_TRAINING_MANIFEST_KIND, "model", "pool", "proposal",
                 "package"):
        meta = service.get_artifact_metadata(sid, kind)
        assert meta["status"] == "available", (kind, meta)

    training_manifest = metric_study._json(service, sid, metric_study.METRIC_TRAINING_MANIFEST_KIND)
    assert training_manifest["synthetic"] is True
    assert training_manifest["no_backend_calls"] is True
    assert training_manifest["artifact_bytes_sha256"] == stages["training"]["artifact_bytes_sha256"]
    assert training_manifest["bounds"]["payload"]["active_keys"] == list(ENC.active_keys)
    assert training_manifest["selected_ids"]

    model_manifest = metric_study._json(service, sid, "model")
    assert model_manifest["schema"] == metric_study.METRIC_MODEL_SCHEMA
    assert model_manifest["policy"] == METRIC_POLICY
    assert model_manifest["pickled_model"] is False
    assert model_manifest["model_state_persisted"] is False
    assert model_manifest["model_hash"]
    assert model_manifest["artifact_checksum"] == training_manifest["checksum"]
    assert [record["name"] for record in model_manifest["per_output"]] == list(
        training_manifest["component_names"])

    proposal = metric_study._json(service, sid, "proposal")
    assert proposal["schema"] == metric_study.METRIC_PROPOSAL_SCHEMA
    assert proposal["proposal_policy"] == METRIC_POLICY
    assert proposal["verification_mode"] == "scalar"
    assert proposal["candidate"]["candidate_id"]
    assert proposal["predicted"]["note"] == "model prediction, not a solved acoustic result"
    assert proposal["acquisition"]["units"] == (
        "qLogNEI (technical ranking only, not J and not a probability)")
    assert proposal["provenance"]["synthetic"] is True
    assert proposal["predictions_appended_to_measured_rows"] is False

    bindings = metric_bindings(service, sid)
    assert bindings["status"] == "ok", bindings
    assert bindings["artifact_bytes_sha256"] == training_manifest["artifact_bytes_sha256"]
    assert bindings["bounds_hash"] == training_manifest["bounds"]["hash"]
    assert bindings["synthetic"] is True

    package = stages["package"]
    assert package["proposal_policy"]["policy"] == METRIC_POLICY
    assert package["proposal_policy"]["verification_mode"] == "scalar"
    assert package["metric"]["synthetic"] is True
    assert package["metric"]["real_solver_allowed"] is False
    assert package["metric"]["training_artifact_sha256"] == bindings["artifact_bytes_sha256"]
    # Re-verifying the published body must succeed and keep the metric block inside the hash.
    from hornlab_search.studies.package import package_hash, verify_package
    assert package_hash(package) == package["package_id"]
    verify_package(package)


def test_metric_bindings_refuse_tampered_checksum(tmp_path):
    stages = _stages(tmp_path)
    service, sid = stages["service"], stages["sid"]
    proposal = metric_study._json(service, sid, "proposal")
    tampered = json.loads(json.dumps(proposal))
    tampered["metric_training"]["checksum"] = "0" * 64
    result = metric_bindings(service, sid, tampered)
    assert result["status"] == "unavailable"
    assert result["reason"] == "metric_artifact_invalid"


def test_build_metric_proposal_is_idempotent_and_deterministic(tmp_path):
    stages = _stages(tmp_path)
    service, sid = stages["service"], stages["sid"]
    first = metric_study._json(service, sid, "proposal")
    again = build_metric_proposal(service, sid, root=tmp_path, seed=0)
    assert again["idempotent"] is True
    second = metric_study._json(service, sid, "proposal")
    assert second["candidate"]["candidate_id"] == first["candidate"]["candidate_id"]
    assert second["model"]["model_hash"] == first["model"]["model_hash"]


# --------------------------------------------------------------------------- execution gate


def test_execution_gate_refuses_real_solver(tmp_path):
    package = _stages(tmp_path)["package"]
    refused = metric_execution_gate(package, allow_real_solver=True,
                                    synthetic_evaluator=lambda c, a: {})
    assert refused["status"] == "refused"
    assert refused["reason"] == "metric_composite_real_execution_not_authorized"
    assert refused["real_solver_allowed"] is False

    missing = metric_execution_gate(package)
    assert missing["status"] == "refused"
    assert missing["reason"] == "metric_composite_real_execution_not_authorized"

    allowed = metric_execution_gate(package, synthetic_evaluator=lambda c, a: {})
    assert allowed["status"] == "ok"
    assert allowed["reason"] == "synthetic_only"
    assert allowed["real_solver_allowed"] is False


def test_synthetic_study_never_reaches_solver_mesh_or_pipeline(tmp_path, monkeypatch):
    stages = _stages(tmp_path)

    def boom(*args, **kwargs):
        raise AssertionError("a real solver/mesh/pipeline path was reached")

    import hornlab_search.search.evaluate as pipeline
    import hornlab_search.solve.base as solve_base
    monkeypatch.setattr(pipeline, "evaluate", boom)
    monkeypatch.setattr(solve_base, "get_backend", boom)
    try:
        import hornlab_search.mesh.build as mesh_build
        monkeypatch.setattr(mesh_build, "build_mesh", boom, raising=False)
    except ImportError:
        pass

    from hornlab_search.studies.runner import run_package
    artifact, fitted, pool, bounds = _runtime(stages)
    evaluator = MetricSyntheticEvaluator(
        artifact, fitted, pool, synthetic_evaluator=synthetic_result, seed=0,
        bounds_hash=bounds, proposal_limit=2)
    journal = ProductionJournal(stages["service"])
    result = run_package(stages["package"], evaluator, metric_study.FrozenLaneAdapter(),
                         journal)
    assert result["status"] == "pool_exhausted"
    assert journal.state(stages["package"]["package_id"])["screen_calls"] == 2


# --------------------------------------------------------------------------- adaptive run


def test_synthetic_adaptive_run_three_proposals(tmp_path):
    service, sid = _study(tmp_path)
    result = metric_study.run_synthetic_metric_study(
        service, sid, root=tmp_path, synthetic_evaluator=synthetic_result,
        selection=_selection(), identity_metadata=_identity(), pool=_pool(n=10),
        seed=0, proposal_limit=3, deadline=_deadline())
    assert result["status"] == "pool_exhausted"
    assert result["synthetic"] is True
    assert result["progress"]["screen_calls"] == 3
    assert len(result["observations"]) == 3
    for item in result["observations"]:
        assert item["result"]["synthetic"] is True
        assert item["result"]["provenance"]["real_solver_calls"] == 0
        assert item["result"]["call_status"] == "called"

    results = metric_study._json(service, sid, "results")
    assert results["synthetic"] is True
    assert results["provenance"]["no_backend_calls"] is True
    assert results["progress"]["screen_calls"] == 3

    # The next synthetic evaluator sees the durable observations and refits from them.
    artifact, fitted, pool, bounds = _runtime({"service": service, "sid": sid})
    restored = MetricSyntheticEvaluator(
        artifact, fitted, pool, synthetic_evaluator=synthetic_result, seed=0,
        bounds_hash=bounds, proposal_limit=3)
    journal = ProductionJournal(service)
    assert restored.restore_progress(journal.load_progress(result["package"]["package_id"]))
    assert restored.history.proposal_index == 3
    assert restored.next_candidate({"screen_calls": 3}) is None
