"""Metric refit transaction, restart, crash-recovery and budget tests.

The acoustic evaluation is a pure-Python fake (``measure_fn``); everything else is real: the
study service, the durable journal, :func:`run_package`, :class:`MetricRefitLedger`, the
content-addressed snapshot/pointer publication and the real metric GP proposal engine.

Crash points covered:
* after the 4th measurement is persisted but before ``observe``/refit;
* after the immutable snapshot bytes are published but before the pointer event advances.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("gpytorch")
pytest.importorskip("botorch")

from hornlab_search.bo.metric_model import fit_metric_model as real_fit_metric_model
from hornlab_search.studies import metric_study, package as package_mod
from hornlab_search.studies.evaluator import MetricPipelineStudyEvaluator
from hornlab_search.studies.metric_refit import (
    METRIC_REFIT_POINTER_EVENT,
    MetricRefitError,
    MetricRefitLedger,
)
from hornlab_search.studies.metric_study import (
    METRIC_POLICY,
    METRIC_TRAINING_MANIFEST_KIND,
    FrozenLaneAdapter,
    _json,
    _load_pool_object,
    _load_training_artifact,
    build_metric_model,
    build_metric_pool,
    build_metric_proposal,
    build_metric_training,
    prepare_metric_run_package,
)
from hornlab_search.studies.production import ProductionJournal
from hornlab_search.studies.runner import run_package
from test_bo_policy_metric import ENC, _identity, _pool, _selection
from test_studies_metric import _study


def _deadline():
    return (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()


def _build(tmp_path, monkeypatch, *, screens):
    profile = f"metric-test-{screens}x0"
    monkeypatch.setitem(package_mod.BUDGET_PROFILES, profile, {
        "screen_calls": screens, "verify_calls": 0, "total_calls": screens,
        "attempts": screens + 4})
    service, sid = _study(tmp_path)
    build_metric_training(service, sid, root=tmp_path, selection=_selection(),
                          identity_metadata=_identity())
    build_metric_model(service, sid, root=tmp_path, seed=0)
    build_metric_pool(service, sid, root=tmp_path, pool=_pool(n=10))
    build_metric_proposal(service, sid, root=tmp_path, seed=0)
    package = prepare_metric_run_package(
        service, sid, lane="cpu", deadline=_deadline(), budget_profile=profile,
        idempotency_key=f"metric-refit-test:{sid}:{screens}")
    return service, sid, package


def _measure_factory(log, manifest):
    task = dict(manifest.get("task") or {})
    score = dict((manifest.get("score") or {}).get("payload") or {})
    bounds = str((manifest.get("bounds") or {}).get("hash") or "")
    active_keys = list(manifest.get("active_keys") or ())

    def measure(candidate, attempt_id):
        log.append(candidate["solve_id"])
        x = np.asarray(candidate.get("x"), dtype=np.float64).reshape(-1)
        components = np.array([
            0.10 + 0.01 * x[0],
            0.10 + 0.01 * x[1],
            0.05 + 0.01 * x[2],
            0.05,
        ], dtype=np.float64)
        j = float(np.sum(components))
        # The catalog join key is the real 16-hex sha16 physical_solve_id, not a sha256.
        catalog_id = hashlib.sha256(("catalog:" + candidate["solve_id"]).encode()).hexdigest()[:16]
        identity = {
            **{field: task[field] for field in (
                "task_identity", "backend", "fidelity", "grid_hash", "dependency_hash",
                "mesh_hash")},
            "brief_hash": score.get("brief_hash"),
            "score_hash": score.get("score_hash"),
            "bounds_hash": bounds,
            "active_keys": active_keys,
        }
        return {
            "solve_id": candidate["solve_id"], "kind": "screen", "call_status": "called",
            "outcome": "success", "eligible": True, "observed_j": j,
            "components": components.tolist(), "objective_version": 10,
            "component_names": ["load_j", "coverage_j", "ripple_j", "other_j"],
            "x": x.tolist(), "params": candidate.get("params") or {},
            "design_hash": candidate.get("design_hash") or candidate["solve_id"],
            "geometry_hash": candidate.get("geometry_hash") or candidate["solve_id"],
            "solve_hash": candidate["solve_id"],
            "physical_id": "replay:" + candidate["solve_id"],
            "score_id": "score:" + candidate["solve_id"],
            "metric_id": "metric:" + candidate["solve_id"],
            "metric_dataset_record": {
                "root": "synthetic://dataset", "shard": 0, "row": len(log) - 1,
                "physical_solve_id": catalog_id, "identity": identity,
            },
            "attempt_id": attempt_id,
        }

    return measure


def _evaluator(service, sid, package, measure_fn):
    artifact, manifest, training_meta, _manifest_meta = _load_training_artifact(service, sid)
    model = _json(service, sid, "model")
    proposal = _json(service, sid, "proposal")
    ledger = MetricRefitLedger(
        service, sid, package["package_id"], base_artifact=artifact,
        base_manifest=manifest, base_artifact_sha256=training_meta["sha256"],
        seed=int(model["seed"]))
    return MetricPipelineStudyEvaluator(
        service, package, config=None, space=None, encoding=ENC, training_set=None,
        pool=_load_pool_object(service, sid), seed=int(model["seed"]),
        audit_seed=int(model["seed"]), evaluate_fn=lambda *args: None,
        policy=METRIC_POLICY, metric_artifact=artifact, metric_manifest=manifest,
        metric_ledger=ledger,
        initial_proposal=proposal.get("candidate") or proposal.get("proposal"),
        measure_fn=measure_fn)


def _run(service, package, evaluator):
    return run_package(package, evaluator, FrozenLaneAdapter(),
                       ProductionJournal(service))


def _pointer_events(service, sid):
    with service.store.connect() as conn:
        rows = conn.execute(
            "SELECT payload_json FROM events WHERE study_id=? AND kind=? ORDER BY seq",
            (sid, METRIC_REFIT_POINTER_EVENT)).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]


def _ledger(service, sid, package):
    artifact, manifest, training_meta, _ = _load_training_artifact(service, sid)
    model = _json(service, sid, "model")
    return MetricRefitLedger(
        service, sid, package["package_id"], base_artifact=artifact,
        base_manifest=manifest, base_artifact_sha256=training_meta["sha256"],
        seed=int(model["seed"]))


# --------------------------------------------------------------------------- normal refit


def test_runner_refits_at_four_screens_and_restart_reproduces_artifact_and_next_candidate(
        tmp_path, monkeypatch):
    reference_service, reference_sid, reference_package = _build(
        tmp_path / "reference", monkeypatch, screens=5)
    reference_log = []
    reference = _evaluator(reference_service, reference_sid, reference_package,
                           _measure_factory(reference_log,
                                            _json(reference_service, reference_sid,
                                                  METRIC_TRAINING_MANIFEST_KIND)))
    result = _run(reference_service, reference_package, reference)
    assert result["status"] == "pool_exhausted"
    assert len(reference_log) == 5
    assert reference._metric_refit_log and reference._metric_refit_log[-1]["generation"] == 1
    reference_pointer = reference._metric_ledger.pointer
    assert reference_pointer["generation"] == 1
    assert len(reference_pointer["accepted_ids"]) == 4
    reference_state = ProductionJournal(reference_service).state(
        reference_package["package_id"])
    assert reference_state["screen_calls"] == 5
    assert reference_state["attempts"] == 5
    assert reference_state["total_calls"] == 5

    service, sid, package = _build(tmp_path / "interrupted", monkeypatch, screens=5)
    log = []
    evaluator = _evaluator(service, sid, package,
                           _measure_factory(log, _json(
                               service, sid, METRIC_TRAINING_MANIFEST_KIND)))
    original_observe = evaluator.observe
    calls = {"n": 0}

    def observe(item):
        calls["n"] += 1
        if calls["n"] == 4:
            raise KeyboardInterrupt("crash after the 4th measurement was persisted")
        return original_observe(item)

    evaluator.observe = observe
    with pytest.raises(KeyboardInterrupt):
        _run(service, package, evaluator)
    assert len(log) == 4                     # measurement persisted, no refit ran
    assert _pointer_events(service, sid) == []
    assert ProductionJournal(service).state(package["package_id"])["screen_calls"] == 4

    resumed_log = []
    resumed = _evaluator(service, sid, package,
                         _measure_factory(resumed_log, _json(
                             service, sid, METRIC_TRAINING_MANIFEST_KIND)))
    result = _run(service, package, resumed)
    assert result["status"] == "pool_exhausted"
    # Only the 5th (next) proposal is evaluated: the four resolved measurements are replayed.
    assert resumed_log == [reference_log[4]]
    resumed_pointer = resumed._metric_ledger.pointer
    assert resumed_pointer["generation"] == 1
    assert resumed_pointer["accepted_ids"] == reference_pointer["accepted_ids"]
    assert resumed_pointer["artifact_bytes_sha256"] == \
        reference_pointer["artifact_bytes_sha256"]
    assert resumed_pointer["artifact_checksum"] == reference_pointer["artifact_checksum"]
    state = ProductionJournal(service).state(package["package_id"])
    assert state["screen_calls"] == 5
    assert state["attempts"] == 5
    assert state["total_calls"] == 5


# --------------------------------------------------------------------------- crash after publish


def test_crash_between_snapshot_publish_and_pointer_advance_recovers_without_repeating_a_call(
        tmp_path, monkeypatch):
    reference_service, reference_sid, reference_package = _build(
        tmp_path / "reference", monkeypatch, screens=5)
    reference_log = []
    reference = _evaluator(reference_service, reference_sid, reference_package,
                           _measure_factory(reference_log, _json(
                               reference_service, reference_sid,
                               METRIC_TRAINING_MANIFEST_KIND)))
    assert _run(reference_service, reference_package, reference)["status"] == "pool_exhausted"
    reference_pointer = reference._metric_ledger.pointer

    service, sid, package = _build(tmp_path / "crash", monkeypatch, screens=5)
    log = []
    evaluator = _evaluator(service, sid, package,
                           _measure_factory(log, _json(
                               service, sid, METRIC_TRAINING_MANIFEST_KIND)))
    original_append = service.append_event

    def append_after_publish(study_id, kind, payload, key):
        if kind == METRIC_REFIT_POINTER_EVENT:
            raise OSError("simulated crash after snapshot publication")
        return original_append(study_id, kind, payload, key)

    service.append_event = append_after_publish
    with pytest.raises(OSError):
        _run(service, package, evaluator)
    assert len(log) == 4
    assert _pointer_events(service, sid) == []       # snapshot orphan, pointer not advanced
    diagnostics = service.store.recovery_diagnostics()
    assert diagnostics["unreferenced"] or diagnostics["incomplete"]

    del service.append_event                            # restore the normal method
    resumed_log = []
    resumed = _evaluator(service, sid, package,
                         _measure_factory(resumed_log, _json(
                             service, sid, METRIC_TRAINING_MANIFEST_KIND)))
    result = _run(service, package, resumed)
    assert result["status"] == "pool_exhausted"
    assert resumed_log == [reference_log[4]]           # no backend call repeated
    resumed_pointer = resumed._metric_ledger.pointer
    assert resumed_pointer["generation"] == 1
    assert resumed_pointer["accepted_ids"] == reference_pointer["accepted_ids"]
    assert resumed_pointer["artifact_bytes_sha256"] == \
        reference_pointer["artifact_bytes_sha256"]
    state = ProductionJournal(service).state(package["package_id"])
    assert state["screen_calls"] == 5
    assert state["total_calls"] == 5
    assert len(log) + len(resumed_log) == 5             # exactly one call per screen


# --------------------------------------------------------------------------- exclusions


def test_verify_cache_duplicate_failed_and_parity_refused_rows_are_not_refit(tmp_path,
                                                                            monkeypatch):
    service, sid, package = _build(tmp_path, monkeypatch, screens=4)
    evaluator = _evaluator(service, sid, package,
                           _measure_factory([], _json(
                               service, sid, METRIC_TRAINING_MANIFEST_KIND)))
    manifest = _json(service, sid, METRIC_TRAINING_MANIFEST_KIND)
    pool_candidate = evaluator.pool.candidates[0]
    base_candidate = {
        "solve_id": "accepted-0", "x": list(pool_candidate.active_vector),
        "design_hash": pool_candidate.design_hash,
        "geometry_hash": pool_candidate.geometry_hash,
        "params": dict(pool_candidate.params),
    }
    measure = _measure_factory([], manifest)
    good = measure(base_candidate, "attempt-0")

    assert evaluator._add_observation(good) is True
    assert evaluator._add_observation(good) is False          # duplicate catalog observation
    assert evaluator._add_observation({**good, "kind": "verify"}) is False
    assert evaluator._add_observation({**good, "call_status": "not_called",
                                       "outcome": "cached"}) is False
    assert evaluator._add_observation({**good, "outcome": "solver_failure"}) is False
    assert evaluator._add_observation({**good, "eligible": False,
                                       "metric_refusal": "replay_score_mismatch"}) is False
    bad_parity = json.loads(json.dumps(good))
    bad_parity["components"][0] += 0.1
    assert evaluator._add_observation(bad_parity) is False
    wrong_identity = json.loads(json.dumps(good))
    wrong_identity["metric_dataset_record"]["identity"]["grid_hash"] = "0" * 64
    assert evaluator._add_observation(wrong_identity) is False
    base_duplicate = json.loads(json.dumps(good))
    base_duplicate["metric_dataset_record"]["physical_solve_id"] = \
        evaluator._metric_base_artifact.observation_ids[0]
    assert evaluator._add_observation(base_duplicate) is False
    assert len(evaluator._metric_accepted) == 1

    accepted_ids = [evaluator._metric_accepted[0].observation_id]
    for index in range(1, 4):
        candidate = {
            "solve_id": f"accepted-{index}",
            "x": list(evaluator.pool.candidates[index].active_vector),
            "design_hash": evaluator.pool.candidates[index].design_hash,
            "geometry_hash": evaluator.pool.candidates[index].geometry_hash,
            "params": dict(evaluator.pool.candidates[index].params),
        }
        result = measure(candidate, f"attempt-{index}")
        assert evaluator._add_observation(result) is True
        accepted_ids.append(result["metric_dataset_record"]["physical_solve_id"])
    assert evaluator._refit() is True
    pointer = evaluator._metric_ledger.pointer
    assert pointer["generation"] == 1
    assert pointer["accepted_ids"] == accepted_ids


# --------------------------------------------------------------------------- failed fit


def test_failed_refit_fit_does_not_publish_a_pointer(tmp_path, monkeypatch):
    service, sid, package = _build(tmp_path, monkeypatch, screens=4)
    log = []
    evaluator = _evaluator(service, sid, package,
                           _measure_factory(log, _json(
                               service, sid, METRIC_TRAINING_MANIFEST_KIND)))
    calls = {"n": 0}

    def flaky(artifact, *, seed=0):
        calls["n"] += 1
        if calls["n"] >= 4:                       # three proposal fits, then the refit fit
            return SimpleNamespace(status="unavailable", reason="numerical_failure",
                                   detail="synthetic refit failure", model_hash="")
        return real_fit_metric_model(artifact, seed=seed)

    monkeypatch.setattr("hornlab_search.bo.metric_model.fit_metric_model", flaky)
    result = _run(service, package, evaluator)
    assert result["status"] == "model_unavailable"
    assert _pointer_events(service, sid) == []
    assert ProductionJournal(service).state(package["package_id"])["screen_calls"] == 4
    assert evaluator._metric_error and "fit failed" in evaluator._metric_error


# --------------------------------------------------------------------------- budget


def test_spent_screen_budget_counts_each_backend_call_once_and_blocks_restart(tmp_path,
                                                                             monkeypatch):
    service, sid, package = _build(tmp_path, monkeypatch, screens=4)
    log = []
    evaluator = _evaluator(service, sid, package,
                           _measure_factory(log, _json(
                               service, sid, METRIC_TRAINING_MANIFEST_KIND)))
    result = _run(service, package, evaluator)
    assert result["status"] == "pool_exhausted"
    assert len(log) == 4
    state = ProductionJournal(service).state(package["package_id"])
    assert state["screen_calls"] == 4
    assert state["total_calls"] == 4
    assert state["attempts"] == 4

    resumed_log = []
    resumed = _evaluator(service, sid, package,
                         _measure_factory(resumed_log, _json(
                             service, sid, METRIC_TRAINING_MANIFEST_KIND)))
    result = _run(service, package, resumed)
    assert result["status"] == "pool_exhausted"
    assert resumed_log == []
    state = ProductionJournal(service).state(package["package_id"])
    assert state["screen_calls"] == 4
    assert state["attempts"] == 4


# --------------------------------------------------------------------------- fail closed


def test_ambiguous_pointer_generation_fails_closed(tmp_path, monkeypatch):
    service, sid, package = _build(tmp_path, monkeypatch, screens=4)
    evaluator = _evaluator(service, sid, package,
                           _measure_factory([], _json(
                               service, sid, METRIC_TRAINING_MANIFEST_KIND)))
    manifest = _json(service, sid, METRIC_TRAINING_MANIFEST_KIND)
    for index in range(4):
        candidate = {
            "solve_id": f"accepted-{index}",
            "x": list(evaluator.pool.candidates[index].active_vector),
            "design_hash": evaluator.pool.candidates[index].design_hash,
            "geometry_hash": evaluator.pool.candidates[index].geometry_hash,
            "params": dict(evaluator.pool.candidates[index].params),
        }
        assert evaluator._add_observation(
            _measure_factory([], manifest)(candidate, f"attempt-{index}")) is True
    assert evaluator._refit() is True
    pointer = evaluator._metric_ledger.pointer
    bogus = {**pointer, "generation": 2,
             "accepted_ids": pointer["accepted_ids"] + ["0" * 64] * 4}
    service.append_event(sid, METRIC_REFIT_POINTER_EVENT, bogus,
                         f"bogus-pointer:{package['package_id']}")
    with pytest.raises(MetricRefitError):
        _ledger(service, sid, package)


def test_refit_pointer_prefix_mismatch_fails_closed(tmp_path, monkeypatch):
    service, sid, package = _build(tmp_path, monkeypatch, screens=4)
    evaluator = _evaluator(service, sid, package,
                           _measure_factory([], _json(
                               service, sid, METRIC_TRAINING_MANIFEST_KIND)))
    manifest = _json(service, sid, METRIC_TRAINING_MANIFEST_KIND)
    accepted = []
    for index in range(4):
        candidate = {
            "solve_id": f"accepted-{index}",
            "x": list(evaluator.pool.candidates[index].active_vector),
            "design_hash": evaluator.pool.candidates[index].design_hash,
            "geometry_hash": evaluator.pool.candidates[index].geometry_hash,
            "params": dict(evaluator.pool.candidates[index].params),
        }
        result = _measure_factory([], manifest)(candidate, f"attempt-{index}")
        assert evaluator._add_observation(result) is True
        accepted.append(result["metric_dataset_record"]["physical_solve_id"])
    assert evaluator._refit() is True
    ledger = evaluator._metric_ledger
    wrong = [type(evaluator._metric_accepted[0])(
        observation_id="0" * 64, x=np.asarray(evaluator._metric_accepted[0].x),
        J=evaluator._metric_accepted[0].J,
        objective_version=evaluator._metric_accepted[0].objective_version)] + \
        list(evaluator._metric_accepted[1:])
    with pytest.raises(MetricRefitError):
        ledger.refit(wrong, [f"attempt-{i}" for i in range(4)],
                     evaluator.proposal_rng_state())


def test_metric_policy_is_a_package_gated_route_not_a_production_policy():
    from hornlab_search.studies.production import PRODUCTION_POLICIES
    from hornlab_search.bo.policy import verification_mode

    assert PRODUCTION_POLICIES == ("scalar", "turbo", "pareto")
    assert METRIC_POLICY not in PRODUCTION_POLICIES
    assert verification_mode("scalar") == verification_mode("turbo") == "scalar"
    assert verification_mode("pareto") == "pareto"
