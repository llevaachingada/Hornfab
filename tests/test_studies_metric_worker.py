"""Real metric-composite worker tests (archived replay + explicit real package gate).

These tests use the *archived* Home v11 Fold evidence (catalog row, dataset shard record,
offline replay row and the 174-row training artifact / offline package written by
``runs/v11_bo_day_planning/fold_metric_service_174.py``).  No mesh, BEM/GPU or pipeline call is
made; the archived rows are read-only.

The real canary package is prepared through the packaging lane's
``prepare_real_metric_package`` and the execution gate revalidates the approval record, the
approval status, every frozen artifact pin and the measured training provenance before accepting
an injected real evaluator.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("gpytorch")
pytest.importorskip("botorch")

from hornlab_search.bo.metric_contracts import validate_components
from hornlab_search.bo.metric_training import bounds_identity
from hornlab_search.config import load_config
from hornlab_search.dataset.catalog_identity import catalog_identity_from_record
from hornlab_search.dataset.identity_v2 import physical_solve_id
from hornlab_search.design.space import DesignSpace
from hornlab_search.objective.replay import (ReplayResult, STATUS_EXACT_COMPLETE,
                                             brief_from_config)
from hornlab_search.studies import metric_study, package as package_mod
from hornlab_search.studies.builders import _task_encoding
from hornlab_search.studies.metric_refit import MetricRefitError, verify_real_metric_package
from hornlab_search.studies.metric_study import metric_execution_gate
from hornlab_search.studies.package import package_hash, verify_package
from hornlab_search.studies.service import StudyService
from hornlab_search.types import Design

REPO = Path(__file__).resolve().parents[1]
WORK = REPO / "runs" / "v11_bo_day_planning"
FOLD = WORK / "fold_150_status"
DATASET = REPO / "dataset"
ARCHIVE = WORK / "fold_metric_service_2x45dvv7" / "registry"
CONFIG = REPO / "examples" / "typologies" / "round3_2026-11-22" / "r3_v11_fold.yaml"
ARCHIVE_STUDY = "e62d9f3b1b264b0589d2b2ce6cc4ba60"
ARCHIVE_PACKAGE = "9c8862dd0afef2fa31d93866b36c07147b253da94e45726d799bb0eab1d392ba"
TASK_IDENTITY = "82dbd04691c7b456"
BRIEF_HASH = "c6bc496e7b4f"
SCORE_HASH = "77d4fdd49bd2c3b4"
MESH_HASH = "8e789cd0deef"
GRID_HASH = "c41ff9a7581ba429"
DEPENDENCY_HASH = "f4dcdca807bdfad0"
ARTIFACT_CHECKSUM = "8281868365fbd52423bdf2ead3d6df0308f4e93dec52ce10d6f752cbbe720b97"
ARTIFACT_BYTES_SHA = "fd7c01871635f64c2c8b4a4f3fcf682d7a7c9f94f0b6584d23a35e56459e7b3c"

pytestmark = pytest.mark.skipif(not ARCHIVE.is_dir(), reason="archived v11 metric evidence absent")


# --------------------------------------------------------------------------- archived fixture


def archived_row(shard=94, row=116):
    catalog = None
    with (FOLD / "catalog.csv").open(newline="", encoding="utf-8-sig") as handle:
        for item in csv.DictReader(handle):
            if int(item["shard_index"]) == shard and int(item["row"]) == row:
                catalog = item
                break
    if catalog is None:  # pragma: no cover - fixture guard
        raise AssertionError(f"catalog row {shard}/{row} not found")
    replay = next(item for item in json.loads((FOLD / "offline_scores.json").read_text())["rows"]
                  if int(item["shard"]) == shard and int(item["row"]) == row)
    line = (DATASET / f"shard-{shard:04d}.jsonl").read_text(encoding="utf-8").splitlines()[row]
    meta = json.loads(line)
    return catalog, replay, meta


class _ReadStore:
    """Minimal DatasetStore read surface for ``load_metric_dataset_record`` (no writes)."""

    def __init__(self, root):
        self.root = Path(root)

    def read(self, shard, row):
        line = (self.root / f"shard-{int(shard):04d}.jsonl").read_text(
            encoding="utf-8").splitlines()[int(row)]
        return json.loads(line), {"response": np.zeros(1)}


def _encoding():
    cfg = load_config(CONFIG)
    return _task_encoding(DesignSpace.from_config(cfg)), cfg


def _archived_measurement():
    catalog, replay_row, meta = archived_row()
    encoding, cfg = _encoding()
    brief = brief_from_config(CONFIG)
    design = Design(meta["family"], meta["params"])
    x = encoding.normalize_design(design, verify_round_trip=True)
    result = {
        "kind": "screen", "eligible": True, "call_status": "called",
        "observed_j": float(meta["objective"]), "design_hash": meta["design_hash"],
        "mesh_hash": meta["mesh_hash"], "solve_hash": meta["solve_hash"],
        "solve_id": "archived-" + catalog["physical_solve_id"], "x": x.tolist(),
    }
    replay = ReplayResult(
        status=STATUS_EXACT_COMPLETE, reasons=(), physical_id=replay_row["physical_id"],
        metric_id=replay_row["metric_id"], score_id=replay_row["score_id"],
        objective_version=11, metric_source="stored", design_hash=meta["design_hash"],
        j=float(replay_row["j"]), stored_j=float(replay_row["stored_j"]),
        terms=dict(meta["terms"]))
    return catalog, replay_row, meta, replay, brief, encoding, result


def test_archived_v11_row_yields_six_contributions_catalog_identity_and_dataset_reference():
    catalog, replay_row, meta, replay, brief, encoding, result = _archived_measurement()
    identity = catalog_identity_from_record(meta)
    assert identity["task_identity"] == TASK_IDENTITY
    assert identity["grid_hash"] == GRID_HASH
    assert identity["dependency_hash"] == DEPENDENCY_HASH
    assert identity["mesh_hash"] == MESH_HASH
    assert identity["brief_hash"] == BRIEF_HASH
    assert identity["score_hash"] == SCORE_HASH
    assert identity["physical_solve_id"] == catalog["physical_solve_id"]

    from hornlab_search.studies.evaluator import (bind_metric_record_identity,
                                                  load_metric_dataset_record,
                                                  record_metric_measurement)

    expected = {k: identity[k] for k in ("task_identity", "backend", "fidelity", "grid_hash",
                                         "dependency_hash", "mesh_hash", "brief_hash",
                                         "score_hash", "physical_solve_id")}
    bounds = metric_study.metric_identity.bounds_identity(encoding)
    bound = bind_metric_record_identity(meta, result, expected=expected, encoding=encoding,
                                        bounds_hash=bounds)
    assert bound["bounds_hash"] == bounds

    store = _ReadStore(DATASET)
    ds_meta, reference = load_metric_dataset_record(
        store, (94, 116), result, run_id=catalog["run_id"], version=11)
    assert reference["physical_solve_id"] == catalog["physical_solve_id"]
    assert reference["physical_solve_id"] == physical_solve_id(
        result["design_hash"], result["mesh_hash"], result["solve_hash"])
    reference["identity"] = bound

    labeled = record_metric_measurement(
        result, ds_meta["terms"], replay, brief=brief, dataset_record=reference)
    assert labeled["eligible"] is True
    assert len(labeled["components"]) == 6
    assert sum(labeled["components"]) == pytest.approx(float(replay.j), abs=1e-12)
    ok, reconstructed, why = validate_components(11, labeled["components"], replay.j)
    assert ok, why
    # The replay physical id identifies different evidence from the catalog join key.
    assert labeled["physical_id"] == replay_row["physical_id"]
    assert labeled["physical_id"] != labeled["metric_dataset_record"]["physical_solve_id"]
    assert labeled["metric_dataset_record"]["physical_solve_id"] == catalog["physical_solve_id"]
    assert labeled["metric_dataset_record"]["identity"]["task_identity"] == TASK_IDENTITY


@pytest.mark.parametrize(("mutation", "field"), [
    (lambda meta: meta["solve"]["freqs_hz"].__setitem__(0, meta["solve"]["freqs_hz"][0] + 100.0),
     "grid_hash"),
    (lambda meta: meta["provenance"].__setitem__("brief_hash", "c6bc496e7b5f"), "brief_hash"),
])
def test_wrong_brief_or_grid_cannot_bind_an_archived_row(mutation, field):
    catalog, _replay_row, meta = archived_row()
    _catalog2, _r2, _meta2, _replay, _brief, encoding, result = _archived_measurement()
    expected_identity = catalog_identity_from_record(meta)
    expected = {k: expected_identity[k] for k in (
        "task_identity", "backend", "fidelity", "grid_hash", "dependency_hash", "mesh_hash",
        "brief_hash", "score_hash", "physical_solve_id")}
    changed = json.loads(json.dumps(meta))
    mutation(changed)
    from hornlab_search.studies.evaluator import bind_metric_record_identity
    with pytest.raises(ValueError, match=f"metric_task_identity_mismatch:.*{field}"):
        bind_metric_record_identity(
            changed, result, expected=expected, encoding=encoding,
            bounds_hash=metric_study.metric_identity.bounds_identity(encoding))


# --------------------------------------------------------------------------- archived artifacts


@pytest.fixture()
def archive(tmp_path):
    target = tmp_path / "registry"
    shutil.copytree(ARCHIVE, target)
    service = StudyService(target)
    # The archived study already binds an offline package for revision 1.  Real preparation is
    # exercised on a temp copy, so drop only that binding (the package bytes stay readable by SHA).
    with service.store.connect() as conn:
        conn.execute("DELETE FROM artifacts WHERE study_id=? AND kind='package'", (ARCHIVE_STUDY,))
    return service


def _archived_package(service):
    body = json.loads(service.store.read_artifact(ARCHIVE_PACKAGE))
    return {"package_id": ARCHIVE_PACKAGE, **body}


def test_archived_174_row_artifact_and_offline_package_still_verify(archive):
    from hornlab_search.studies.metric_study import _load_training_artifact, metric_bindings

    artifact, manifest, training_meta, manifest_meta = _load_training_artifact(
        archive, ARCHIVE_STUDY)
    assert artifact.n == 174 and artifact.d == 18
    assert artifact.checksum == ARTIFACT_CHECKSUM
    assert training_meta["sha256"] == ARTIFACT_BYTES_SHA
    assert manifest["artifact_bytes_sha256"] == ARTIFACT_BYTES_SHA
    assert manifest["synthetic"] is False
    assert manifest["task"]["task_identity"] == TASK_IDENTITY
    assert manifest["task"]["grid_hash"] == GRID_HASH
    assert metric_bindings(archive, ARCHIVE_STUDY)["status"] == "ok"

    package = _archived_package(archive)
    verify_package(package)
    assert package["metric"]["provenance_mode"] == "real_data_offline_v1"
    assert package["metric"]["real_solver_allowed"] is False
    # The offline package must keep refusing solver authority, even when requested.
    refused = metric_execution_gate(package, allow_real_solver=True,
                                    synthetic_evaluator=lambda c, a: {})
    assert refused["status"] == "refused"
    assert refused["real_solver_allowed"] is False


# --------------------------------------------------------------------------- real package gate


class _RealEvaluator:
    synthetic_evaluator = None

    def next_candidate(self, state):
        return None

    def evaluate(self, candidate, attempt_id):
        raise AssertionError("the gate test must never dispatch an evaluation")


def _approvals_for(service, *, status="APPROVED_FOR_CANARY", profile="metric-canary-8x2"):
    manifest = json.loads(service.store.read_artifact(
        service.get_artifact_metadata(ARCHIVE_STUDY, "metric_training_manifest")["sha256"]))
    task = manifest["task"]
    score = manifest["score"]["payload"]
    return {
        "schema": "metric-real-approvals-v1",
        "status": status,
        "profile": profile,
        "screen_cap": 8,
        "verify_cap": 2,
        "refit_every": 4,
        "lane": "gpu",
        "task_identity": task["task_identity"],
        "artifact_sha256": manifest["checksum"],
        "identity": {
            **{field: task[field] for field in (
                "task_identity", "backend", "fidelity", "grid_hash", "dependency_hash",
                "mesh_hash")},
            "brief_hash": score["brief_hash"],
            "score_hash": score["score_hash"],
        },
    }


def _write_approvals(root, approvals):
    (root / "approvals.json").write_text(json.dumps(approvals), encoding="utf-8")


def _prepared_real_package(archive, root, *, status="APPROVED_FOR_CANARY",
                           profile="metric-canary-8x2"):
    approvals = _approvals_for(archive, status=status, profile=profile)
    _write_approvals(root, approvals)
    offline = json.loads(archive.store.read_artifact(ARCHIVE_PACKAGE))
    return package_mod.prepare_real_metric_package(
        archive, ARCHIVE_STUDY, approvals_record="approvals.json",
        budget_profile=profile, lane="gpu",
        deadline=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        approvals_root=root, dependency_pins=offline.get("dependency_pins"))


def _resign(body):
    return {"package_id": package_hash(body), **body}


def test_real_metric_gate_accepts_only_a_complete_pinned_gpu_package(archive, tmp_path):
    package = _prepared_real_package(archive, tmp_path)
    assert package["metric"]["provenance_mode"] == "real_metric_v1"
    assert package["budget_profile"] == "metric-canary-8x2"
    assert package["metric"]["approvals"]["artifact_sha256"] == ARTIFACT_CHECKSUM
    assert package["metric"]["training_checksum"] == ARTIFACT_CHECKSUM
    assert package["metric"]["no_backend_calls"] is False

    accepted = metric_execution_gate(
        package, allow_real_solver=True, real_evaluator=_RealEvaluator(),
        service=archive, root=tmp_path)
    assert accepted["status"] == "ok", accepted
    assert accepted["reason"] == "real_metric_v1"
    assert accepted["real_solver_allowed"] is True
    assert accepted["approval_status"] == "APPROVED_FOR_CANARY"
    assert accepted["task_identity"] == TASK_IDENTITY
    assert accepted["training_checksum"] == ARTIFACT_CHECKSUM

    refused = metric_execution_gate(package, allow_real_solver=True, service=archive,
                                    root=tmp_path)
    assert refused["reason"] == "real_metric_evaluator_required"
    refused = metric_execution_gate(package, real_evaluator=_RealEvaluator(), service=archive,
                                    root=tmp_path)
    assert refused["reason"] == "metric_real_execution_not_requested"

    assert verify_real_metric_package(archive, package, root=tmp_path)["status"] == "ok"


def test_held_approval_record_is_preparable_but_not_executable(archive, tmp_path):
    package = _prepared_real_package(archive, tmp_path, status="HELD_PENDING_PARENT_RELEASE")
    refused = metric_execution_gate(package, allow_real_solver=True,
                                    real_evaluator=_RealEvaluator(), service=archive,
                                    root=tmp_path)
    assert refused["status"] == "refused"
    assert "not executable" in refused["detail"]


def test_real_metric_gate_refuses_wrong_approvals_caps_lane_and_pins(archive, tmp_path):
    base = _prepared_real_package(archive, tmp_path)

    def tampered(mutate, *, approvals_mutate=None):
        body = json.loads(json.dumps({k: v for k, v in base.items() if k != "package_id"}))
        mutate(body)
        # Each case starts from a clean, versioned approvals record so a mutation from the
        # previous case cannot leak into this one through the shared tmp_path file.
        record = _approvals_for(archive)
        if approvals_mutate is not None:
            approvals = dict(body["metric"]["approvals"])
            approvals_mutate(approvals)
            body["metric"]["approvals"] = approvals
            approvals_mutate(record)
        _write_approvals(tmp_path, record)
        return metric_execution_gate(
            _resign(body), allow_real_solver=True, real_evaluator=_RealEvaluator(),
            service=archive, root=tmp_path)

    def set_approval(key, value):
        return lambda approvals: approvals.__setitem__(key, value)

    pin_artifact = {
        "training_artifact_sha256": "metric_training",
        "training_manifest_sha256": "metric_training_manifest",
        "proposal_sha256": "proposal",
        "model_sha256": "model",
    }

    def set_pin(key, value):
        def mutate(body):
            body["metric"][key] = value
            body["artifacts"][pin_artifact[key]] = value
        return mutate

    cases = [
        (tampered(lambda b: b["metric"]["approvals"].__setitem__("task_identity", "0" * 16),
                  approvals_mutate=set_approval("task_identity", "0" * 16)), "task_identity"),
        (tampered(lambda b: b["metric"]["approvals"].__setitem__("artifact_sha256", "0" * 64),
                  approvals_mutate=set_approval("artifact_sha256", "0" * 64)), "artifact_sha256"),
        (tampered(lambda b: b["metric"]["approvals"].__setitem__("screen_cap", 9),
                  approvals_mutate=set_approval("screen_cap", 9)), "caps"),
        (tampered(lambda b: b["metric"]["approvals"].__setitem__("verify_cap", 3),
                  approvals_mutate=set_approval("verify_cap", 3)), "caps"),
        (tampered(lambda b: b["metric"]["approvals"].__setitem__("refit_every", 3),
                  approvals_mutate=set_approval("refit_every", 3)), "refit_every"),
        (tampered(lambda b: b.__setitem__("lane", "cpu")), "gpu lane"),
        (tampered(set_pin("training_artifact_sha256", "0" * 64)), "training_artifact_sha256"),
        (tampered(set_pin("proposal_sha256", "0" * 64)), "proposal_sha256"),
        (tampered(lambda b: b["metric"].__setitem__("source_provenance_sha256", "0" * 64)),
         "source provenance"),
        (tampered(lambda b: b["metric"].__setitem__("synthetic", True)), "non-synthetic"),
        (tampered(lambda b: b["metric"].__setitem__("real_solver_allowed", False)),
         "authorize"),
        (tampered(lambda b: b["metric"].__setitem__("training_checksum", "0" * 64)),
         "training checksum"),
    ]
    for status, needle in cases:
        assert status["status"] == "refused", (needle, status)
        assert status["real_solver_allowed"] is False
        assert needle in (status.get("detail") or ""), (needle, status)


def test_real_metric_gate_fails_closed_without_service_or_approvals_record(archive, tmp_path):
    package = _prepared_real_package(archive, tmp_path)
    refused = metric_execution_gate(
        package, allow_real_solver=True, real_evaluator=_RealEvaluator(), service=None,
        root=tmp_path)
    assert refused["status"] == "refused"
    (tmp_path / "approvals.json").unlink()
    refused = metric_execution_gate(
        package, allow_real_solver=True, real_evaluator=_RealEvaluator(), service=archive,
        root=tmp_path)
    assert refused["status"] == "refused"
    assert "approvals record" in (refused.get("detail") or "")

def test_metric_route_reproduces_the_archived_proposal_through_a_strict_binding(archive):
    """The metric arm routes the frozen artifact through MetricTrainingBinding + fit_and_propose."""
    from hornlab_search.bo.policy import MetricTrainingBinding, fit_and_propose

    artifact, manifest, _training_meta, _manifest_meta = metric_study._load_training_artifact(
        archive, ARCHIVE_STUDY)
    encoding, _cfg = _encoding()
    pool = metric_study._load_pool_object(archive, ARCHIVE_STUDY)
    proposal = metric_study._json(archive, ARCHIVE_STUDY, "proposal")
    binding = MetricTrainingBinding(
        artifact=artifact, encoding=encoding,
        expected_bounds_hash=manifest["bounds"]["hash"],
        expected_score=dict(manifest["score"]["payload"]),
        expected_task=dict(manifest["task"]),
        component_schema=manifest["component_schema_hash"])
    outcome = fit_and_propose(
        "metric_composite_v1", metric_training=binding, pool=pool, seed=0,
        encoding=encoding)
    assert outcome.status == "ok", outcome.reason
    assert outcome.proposal["candidate_id"] == proposal["candidate"]["candidate_id"]
    assert outcome.predicted["j_mean"] == pytest.approx(
        proposal["predicted"]["j_mean"])
    assert outcome.fallback is False
