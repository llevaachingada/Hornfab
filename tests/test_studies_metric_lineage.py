"""Adaptive continuation: promote a published metric refit into a child study.

Uses the real Home v11 Fold canary registry (read-only copy) as the fixture: the child base
artifact must be the parent's gen-2 refit artifact (182 rows), with the parent lineage recorded and
the child model/pool/proposal built without any backend call.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("gpytorch")
pytest.importorskip("botorch")

from hornlab_search.studies.metric_lineage import promote_metric_refit
from hornlab_search.studies.metric_study import _load_training_artifact
from hornlab_search.studies.service import StudyService

REPO = Path(__file__).resolve().parents[1]
CANARY = REPO / "runs" / "metric_bo_canary_2026-11-23" / "registry_v4"
PARENT = "46cd5e1d3c63486796258fdc37e79abd"
PACKAGE = "3bf53815e1ab78bb7170455876531d5e79419ec844b4cf4799e46292b2ec9d8e"
GEN2_CHECKSUM = "10f1ffa31a84795f592f8bb3c1ec3f3d842a58ad7b3bb4139ac00c4bd0776ce6"
GEN2_BYTES = "6d482878ce3221484d25a0f475b7a27ada4ea9d712a41e1c042788b498d010b1"

pytestmark = pytest.mark.skipif(not CANARY.is_dir(), reason="canary registry fixture absent")


def test_promote_refit_creates_child_with_gen2_artifact_and_lineage(tmp_path):
    registry = tmp_path / "registry"
    shutil.copytree(CANARY, registry)
    service = StudyService(registry)

    result = promote_metric_refit(service, PARENT, PACKAGE, root=tmp_path)
    assert result["status"] == "ok"
    assert result["generation"] == 2
    assert result["n"] == 182
    assert result["artifact_checksum"] == GEN2_CHECKSUM
    assert result["artifact_bytes_sha256"] == GEN2_BYTES
    child = result["child_study_id"]
    assert child != PARENT

    artifact, manifest, _, _ = _load_training_artifact(service, child)
    assert artifact.n == 182
    assert artifact.checksum == GEN2_CHECKSUM
    assert manifest["synthetic"] is False
    assert manifest["no_backend_calls"] is True
    lineage = manifest["refit_lineage"]
    assert lineage["parent_study_id"] == PARENT
    assert lineage["parent_package_id"] == PACKAGE
    assert lineage["generation"] == 2
    assert len(lineage["accepted_ids"]) == 8
    assert lineage["artifact_bytes_sha256"] == GEN2_BYTES

    assert result["model"]["status"] == "ok"
    assert result["pool"]["status"] == "ok"
    assert result["proposal"]["status"] == "ok"

    # The child pool must not re-propose any design the parent already measured.
    parent = service.export_study(PARENT)
    pointer = [e for e in parent["events"] if e["kind"] == "metric_refit_pointer"][-1]
    payload = pointer.get("payload") or pointer.get("payload_json")
    if isinstance(payload, str):
        payload = json.loads(payload)
    used = set((payload.get("proposal_state") or {}).get("proposal_history", {}).get(
        "excluded_design_hashes") or ())
    used.update((payload.get("proposal_state") or {}).get("proposal_history", {}).get(
        "excluded_geometry_hashes") or ())
    pool = json.loads(service.store.read_artifact(
        service.get_artifact_metadata(child, "pool")["sha256"]))
    child_hashes = set()
    for candidate in pool.get("candidates") or ():
        for key in ("design_hash", "geometry_hash"):
            if candidate.get(key):
                child_hashes.add(candidate[key])
    assert child_hashes.isdisjoint(used)

    # Same key/payload returns the same child and does not duplicate artifacts.
    again = promote_metric_refit(service, PARENT, PACKAGE, root=tmp_path)
    assert again["child_study_id"] == child

    # A labelled promotion is a distinct child with the same 182-row artifact, so an adaptive
    # tranche can be sized independently of an already-bound package on the first child.
    adaptive = promote_metric_refit(service, PARENT, PACKAGE, root=tmp_path, label="adaptive20")
    assert adaptive["child_study_id"] != child
    assert adaptive["artifact_checksum"] == GEN2_CHECKSUM
    assert adaptive["n"] == 182

