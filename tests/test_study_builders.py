"""Focused M3 builder tests: temp study roots, tiny fixtures, no solver.

The tiny fixture reuses the real signed native config to obtain legal OSSE
designs, then writes a 32-row dataset shard/catalog/scores triple under the
study root.  Nothing here touches the live dataset, cache, mesher or solver.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.bo.data import CandidatePool, PoolCandidate
from hornlab_search.bo.policy import ProposalOutcome
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace
from hornlab_search.studies import builders
from hornlab_search.studies.schema import Unavailable
from hornlab_search.studies.service import StudyService

NATIVE_CONFIG = (Path(__file__).resolve().parents[1] / "examples" / "typologies"
                 / "campaign_2026-10-26_v4" / "native__ath_core_v4.yaml")
ROWS = 32


def _tiny_fixture(root: Path):
    """Write a legal 32-row native fixture under the explicit study root."""
    fixture = root / "fixtures"
    dataset = fixture / "dataset"
    dataset.mkdir(parents=True, exist_ok=True)
    cfg = load_config(NATIVE_CONFIG)
    space = DesignSpace.from_config(cfg)
    shard_rows = []
    score_rows = []
    for i in range(ROWS):
        u = np.clip(0.02 + 0.94 * (i + 1) / (ROWS + 1), 0.0, 1.0)
        design = space.denormalize(np.full(len(space.keys()), u))
        design_hash = design.hash()
        solve_hash = f"solve-{i:04d}"
        shard_rows.append({
            "ok": True, "family": design.family, "params": dict(design.params),
            "design_hash": design_hash, "solve_hash": solve_hash,
        })
        score_rows.append({
            "shard": 0, "row": i, "config_name": "native__ath_core_v4",
            "status": "exact_complete", "complete": True,
            "j": 1.0 + 0.1 * i, "physical_id": f"physical-{i:04d}",
            "metric_id": f"metric-{i:04d}", "score_id": f"score-{i:04d}",
            "design_hash": design_hash, "stored_j": 1.0 + 0.1 * i,
            "stored_objective_version": 4, "parity_delta": 0.0,
            # Strict native policy gate: the replay must evidence the frozen metric policy.
            "objective_version": 4, "metric_source": "stored",
            "diagnostics": {"ripple_used_response": True},
            "target": {"band_lo_hz": 300.0, "band_hi_hz": 8000.0},
            "weights": {"cov": 1.0, "rip": 1.0},
        })
    (dataset / "shard-0000.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in shard_rows), encoding="utf-8")
    catalog = fixture / "catalog.csv"
    catalog.write_text(
        "root,shard_index,row,config_name,objective_version,backend,brief_hash,"
        "dependency_hash,task_identity,fidelity,grid_hash\n"
        + "".join(f"dataset,0,{i},native__ath_core_v4,4,beat_cuda,brief-fixture,"
                  f"dep-fixture,task-fixture,screen,grid-fixture\n" for i in range(ROWS)),
        encoding="utf-8")
    scores = fixture / "scores.json"
    scores.write_text(json.dumps({
        "cohort": {"native_config": "native__ath_core_v4"},
        "brief": {"objective_version": 4},
        "parity": {"n": ROWS, "n_compared": ROWS, "max_abs_delta": 0.0},
        "rows": score_rows,
    }), encoding="utf-8")
    return {
        "task": {"config": str(NATIVE_CONFIG), "objective_version": 4},
        "source": {"scores_json": str(scores), "catalog_csv": str(catalog),
                   "dataset_root": str(dataset)},
    }


def _service_with_study(root: Path, spec=None):
    service = StudyService(root)
    study = service.create_study(spec or {"protocol": "bo-study-v1.1"}, "create")
    return service, study["id"]


def _pool(n=4, d=13):
    candidates = tuple(
        PoolCandidate(
            candidate_id=f"c{i}", pool_index=i, seed=0,
            active_vector=np.full(d, 0.4 + 0.05 * i), full_vector=np.zeros(d + 1),
            design_hash=f"design-{i}", geometry_hash=f"geometry-{i}",
            intended_solve_hash=f"solve-{i}", params={}, descriptors={}, checks={})
        for i in range(n))
    return CandidatePool(status="ok", requested=n, seed=0, seeds_tried=(0,),
                         candidates=candidates, counts={}, seed_reports=(),
                         intended_solve_hash=None, note=builders.POOL_STATUS_NOTE)


def test_snapshot_training_analysis_attach_exact_hashes_and_dependencies(tmp_path):
    service, sid = _service_with_study(tmp_path / "registry")
    spec = _tiny_fixture(tmp_path / "registry")

    snapshot = builders.freeze_snapshot(service, sid, root=tmp_path / "registry", spec=spec)
    assert snapshot["status"] == "ok"
    snapshot_meta = snapshot["snapshot"]
    assert snapshot_meta["kind"] == "snapshot" and len(snapshot_meta["sha256"]) == 64
    payload = json.loads(service.store.read_artifact(snapshot_meta["sha256"]))
    assert payload["schema"] == builders.SNAPSHOT_SCHEMA
    assert payload["no_backend_calls"] is True
    assert payload["cohort"]["scores"]["records"] == ROWS
    assert payload["cohort"]["scores"]["ok"] == ROWS
    assert payload["task"]["objective_version"] == 4
    assert len(payload["task"]["config_sha256"]) == 64
    assert len(payload["source"]["scores_json_sha256"]) == 64

    training = builders.build_training(service, sid, root=tmp_path / "registry", spec=spec)
    assert training["status"] == "ok" and training["d"] == 13 and training["n"] == ROWS
    manifest = json.loads(service.store.read_artifact(training["training_manifest"]["sha256"]))
    assert manifest["dependencies"]["snapshot"] == snapshot_meta["sha256"]
    assert manifest["dependencies"]["training"] == training["training"]["sha256"]
    assert manifest["dependencies"]["training_ids"] == training["training_ids"]["sha256"]
    with np.load(service.store.artifacts / training["training"]["sha256"],
                 allow_pickle=False) as arrays:
        assert arrays["X"].shape == (ROWS, 13)
        assert np.array_equal(arrays["Y"], -arrays["J"])
        assert arrays["ids"].dtype.kind == "U"

    analysis = builders.build_analysis(service, sid, root=tmp_path / "registry", spec=spec)
    assert analysis["status"] == "ok"
    analysis_payload = json.loads(service.store.read_artifact(analysis["artifact"]["sha256"]))
    assert analysis_payload["recommendation_status"] == "suppressed"
    assert analysis_payload["metric_math_recomputed"] is False
    assert analysis_payload["subset"]["retained"] == ROWS


def test_repeated_builds_are_idempotent_and_keep_the_same_bytes(tmp_path):
    root = tmp_path / "registry"
    service, sid = _service_with_study(root)
    spec = _tiny_fixture(root)
    first = builders.freeze_snapshot(service, sid, root=root, spec=spec)
    second = builders.freeze_snapshot(service, sid, root=root, spec=spec)
    assert second["idempotent"] is True
    assert second["snapshot"]["sha256"] == first["snapshot"]["sha256"]
    t1 = builders.build_training(service, sid, root=root, spec=spec)
    t2 = builders.build_training(service, sid, root=root, spec=spec)
    assert t2["idempotent"] is True
    assert t2["training"]["sha256"] == t1["training"]["sha256"]
    assert t2["training_manifest"]["sha256"] == t1["training_manifest"]["sha256"]
    assert service.store.recovery_diagnostics()["unreferenced"] == []


def test_missing_and_outside_root_inputs_are_typed_unavailable(tmp_path):
    root = tmp_path / "registry"
    service, sid = _service_with_study(root)
    outside = tmp_path / "outside-scores.json"
    outside.write_text("{}", encoding="utf-8")
    spec = _tiny_fixture(root)
    spec["source"]["scores_json"] = str(outside)
    with pytest.raises(Unavailable) as exc:
        builders.freeze_snapshot(service, sid, root=root, spec=spec)
    assert "outside the allowed study/repository roots" in str(exc.value)
    assert str(outside.resolve()) in str(exc.value)

    spec = _tiny_fixture(root)
    spec["source"]["scores_json"] = str(root / "fixtures" / "missing.json")
    with pytest.raises(Unavailable) as exc:
        builders.freeze_snapshot(service, sid, root=root, spec=spec)
    assert "not found" in str(exc.value)

    spec = {"task": {"config": str(NATIVE_CONFIG)},
            "source": {"scores_json": "../../escape.json"}}
    with pytest.raises(Unavailable):
        builders.freeze_snapshot(service, sid, root=root, spec=spec)


def test_builders_never_write_dataset_or_cache_paths(tmp_path):
    root = tmp_path / "registry"
    service, sid = _service_with_study(root)
    spec = _tiny_fixture(root)
    dataset = Path(spec["source"]["dataset_root"])
    before = {p: p.read_bytes() for p in dataset.iterdir() if p.is_file()}
    builders.freeze_snapshot(service, sid, root=root, spec=spec)
    builders.build_training(service, sid, root=root, spec=spec)
    builders.build_analysis(service, sid, root=root, spec=spec)
    assert not (root / "cache").exists()
    assert not (root / "dataset").exists()
    after = {p: p.read_bytes() for p in dataset.iterdir() if p.is_file()}
    assert after == before


def test_scalar_proposal_without_engine_is_capability_missing(tmp_path, monkeypatch):
    root = tmp_path / "registry"
    service, sid = _service_with_study(root)
    spec = _tiny_fixture(root)
    builders.freeze_snapshot(service, sid, root=root, spec=spec)
    builders.build_training(service, sid, root=root, spec=spec)
    builders.build_analysis(service, sid, root=root, spec=spec)
    result = builders.build_proposal(service, sid, root=root, spec=spec, policy="scalar",
                                     pool=_pool())
    assert result["status"] == "capability_missing"
    proposal = json.loads(service.store.read_artifact(result["proposal"]["sha256"]))
    assert proposal["status"] == "capability_missing"
    assert proposal["candidate"] is None and proposal["predicted"] is None
    assert proposal["predictions_appended_to_measured_rows"] is False
    assert proposal["status_note"] == builders.POOL_STATUS_NOTE
    assert proposal["verification_mode"] == "scalar"


def test_scalar_proposal_predictions_are_tagged_and_never_measured(tmp_path, monkeypatch):
    root = tmp_path / "registry"
    service, sid = _service_with_study(root)
    spec = _tiny_fixture(root)
    builders.freeze_snapshot(service, sid, root=root, spec=spec)
    builders.build_training(service, sid, root=root, spec=spec)
    builders.build_analysis(service, sid, root=root, spec=spec)

    from hornlab_search.bo import policy as policy_mod
    candidate = {"candidate_id": "c0", "geometry_hash": "geometry-0",
                 "design_hash": "design-0", "intended_solve_hash": "solve-0",
                 "active_vector": [0.5] * 13, "params": {}, "checks": {}}
    outcome = ProposalOutcome(
        status="ok", reason="ok", policy="scalar", selection_reason="acquisition",
        proposal=candidate,
        predicted={"j_mean": 2.0, "j_lower": 1.0, "j_upper": 3.0,
                   "interval_label": "model credible interval", "observation_noise": False},
        acquisition={"value": -0.25, "units": "log acquisition ranking diagnostic"},
        verification_mode="scalar", library_versions={"engine": "botorch"})
    monkeypatch.setattr(policy_mod, "capability_status",
                        lambda *a, **k: {"status": "ok", "reason": None, "detail": None,
                                         "library_versions": {}})
    monkeypatch.setattr(policy_mod, "fit_and_propose", lambda *a, **k: outcome)

    result = builders.build_proposal(service, sid, root=root, spec=spec, policy="scalar",
                                     seed=7, pool=_pool())
    assert result["status"] == "ok"
    proposal = json.loads(service.store.read_artifact(result["proposal"]["sha256"]))
    assert proposal["candidate"]["candidate_id"] == "c0"
    assert proposal["predicted"]["j_mean"] == 2.0
    assert proposal["predictions_appended_to_measured_rows"] is False
    manifest = json.loads(service.store.read_artifact(result["model"]["sha256"]))
    assert manifest["model_state_persisted"] is False
    assert manifest["policy"] == "scalar"


def test_pareto_without_validated_cohort_refuses_without_candidate(tmp_path):
    root = tmp_path / "registry"
    service, sid = _service_with_study(root)
    spec = _tiny_fixture(root)
    builders.freeze_snapshot(service, sid, root=root, spec=spec)
    builders.build_training(service, sid, root=root, spec=spec)
    builders.build_analysis(service, sid, root=root, spec=spec)
    result = builders.build_proposal(service, sid, root=root, spec=spec, policy="pareto",
                                     pool=_pool())
    assert result["status"] == "capability_missing"
    proposal = json.loads(service.store.read_artifact(result["proposal"]["sha256"]))
    assert proposal["candidate"] is None
    assert proposal["reason"] == "validated_cohort_required"
    assert proposal["verification_mode"] == "pareto"
