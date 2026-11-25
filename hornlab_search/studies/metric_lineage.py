"""Promote a published metric refit snapshot into a child study (adaptive continuation).

The canary/refit ledger is append-only per study and the run-package binding is one package per
study revision.  An adaptive tranche must therefore continue in a *child study* whose base
training artifact is the parent's latest immutable refit artifact.  This module performs that
promotion with no backend call and no new acoustic evidence:

* reads the parent's base artifact/manifest and its latest ``metric_refit_pointer``;
* creates a child study with the same frozen spec (``parent_id`` set);
* attaches the exact refit artifact bytes (content-addressed) and a manifest that keeps the
  parent's frozen task/bounds/score/component identity, its offline-intake pins, and an explicit
  ``refit_lineage`` block naming the parent study, package, generation, snapshot, accepted catalog
  IDs and journal attempts;
* builds the child model, candidate pool (excluding every already-used design) and proposal.

Everything is deterministic; repeating the call for the same parent/generation is idempotent.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from hornlab_search.bo import metric_artifact
from hornlab_search.bo.data import build_candidate_pool
from hornlab_search.config import load_config
from hornlab_search.design.space import DesignSpace

from . import builders
from .builders import _task_encoding
from .metric_refit import METRIC_REFIT_SNAPSHOT_FORMAT, MetricRefitLedger
from .metric_study import (
    METRIC_TRAINING_KIND,
    METRIC_TRAINING_MANIFEST_KIND,
    _json,
    _load_training_artifact,
    build_metric_model,
    build_metric_pool,
    build_metric_proposal,
)
from .schema import Unavailable, canonical


def _known_geometry(service, parent_study_id, pointer):
    """Every design/geometry hash the parent already used, including the refit history."""
    known = set()
    try:
        pool = _json(service, parent_study_id, "pool")
    except Unavailable:
        pool = {}
    for candidate in pool.get("candidates") or ():
        for key in ("design_hash", "geometry_hash", "candidate_id"):
            value = candidate.get(key)
            if isinstance(value, str) and value:
                known.add(value)
    state = (pointer or {}).get("proposal_state") or {}
    history = state.get("proposal_history") or {}
    for key in ("excluded_design_hashes", "excluded_geometry_hashes"):
        known.update(str(v) for v in (history.get(key) or ()) if v)
    return known


def promote_metric_refit(service, parent_study_id, package_id, *, root, seed=None, label=""):
    """Create/return the child study whose base artifact is the parent's latest refit snapshot."""
    parent = service.get_study(parent_study_id)
    base_artifact, base_manifest, _, _ = _load_training_artifact(service, parent_study_id)
    if seed is None:
        seed = int((_json(service, parent_study_id, "model") or {}).get("seed", 0))
    ledger = MetricRefitLedger(
        service, parent_study_id, package_id, base_artifact=base_artifact,
        base_manifest=base_manifest, base_artifact_sha256=base_artifact.checksum,
        seed=int(seed))
    pointer = ledger.pointer
    if pointer is None or ledger.generation < 1:
        raise Unavailable("no published metric refit snapshot to promote")
    promoted = ledger.current_artifact
    generation = int(ledger.generation)

    validation = metric_artifact.validate_metric_training_artifact(
        promoted, expected_bounds_hash=(base_manifest.get("bounds") or {}).get("hash"),
        expected_score=(base_manifest.get("score") or {}).get("payload"),
        expected_task=base_manifest.get("task") or {})
    if not validation.ok:
        raise Unavailable("promoted refit artifact failed identity validation: "
                          + str(validation.detail or validation.reason))

    child = service.create_study(
        parent["spec"],
        f"promote:{parent_study_id}:{package_id}:{generation}" + (f":{label}" if label else ""),
        parent_id=parent_study_id)
    child_id = child["id"]
    builders.freeze_snapshot(service, child_id, root=root)
    snapshot_meta = builders._require(service, child_id, "snapshot")

    blob = metric_artifact.artifact_bytes(promoted)
    bytes_sha = builders._sha256_bytes(blob)
    deps = {"snapshot": snapshot_meta["sha256"]}
    training_meta = builders._attach_once(
        service, child_id, 1, METRIC_TRAINING_KIND, blob, deps,
        f"metric_training:1:{bytes_sha}")

    manifest = copy.deepcopy(base_manifest)
    manifest.update({
        "study_id": child_id,
        "revision": 1,
        "generated_utc": pointer.get("created_utc") or base_manifest.get("generated_utc"),
        "artifact_bytes_sha256": bytes_sha,
        "checksum": promoted.checksum,
        "objective_version": int(promoted.objective_version),
        "component_names": list(promoted.component_names),
        "n": int(promoted.n),
        "d": int(promoted.d),
        "m": int(promoted.m),
        "observation_ids": list(promoted.observation_ids),
        "selected_ids": list(promoted.selected_ids),
        "synthetic": False,
        "no_backend_calls": True,
        "refit_lineage": {
            "format": METRIC_REFIT_SNAPSHOT_FORMAT,
            "parent_study_id": parent_study_id,
            "parent_package_id": package_id,
            "generation": generation,
            "snapshot_sha256": pointer["snapshot_sha256"],
            "artifact_bytes_sha256": pointer["artifact_bytes_sha256"],
            "artifact_checksum": pointer["artifact_checksum"],
            "accepted_ids": list(pointer.get("accepted_ids") or ()),
            "journal_attempt_ids": list(pointer.get("journal_attempt_ids") or ()),
            "model_seed": pointer.get("model_seed"),
            "model_hash": pointer.get("model_hash"),
            "promoted_utc": pointer.get("created_utc") or base_manifest.get("generated_utc"),
        },
    })
    manifest["dependencies"] = {**deps, METRIC_TRAINING_KIND: training_meta["sha256"]}
    manifest_meta = builders._attach_once(
        service, child_id, 1, METRIC_TRAINING_MANIFEST_KIND, builders._json_bytes(manifest),
        manifest["dependencies"], f"{METRIC_TRAINING_MANIFEST_KIND}:1:{bytes_sha}")

    model = build_metric_model(service, child_id, root=root, seed=int(seed))
    snapshot = _json(service, child_id, "snapshot")
    config_path = (snapshot.get("task") or {}).get("config")
    if not config_path:
        raise Unavailable("promoted child snapshot has no resolved config")
    cfg = load_config(config_path)
    space = DesignSpace.from_config(cfg)
    encoding = _task_encoding(space)
    pool = build_candidate_pool(
        space, encoding, cfg, n=128, seed=0,
        known_geometry_hashes=_known_geometry(service, parent_study_id, pointer))
    pool_result = build_metric_pool(service, child_id, root=root, pool=pool,
                                    config_path=config_path, encoding=encoding)
    proposal = build_metric_proposal(service, child_id, root=root, seed=int(seed))
    return {
        "status": "ok",
        "child_study_id": child_id,
        "parent_study_id": parent_study_id,
        "parent_package_id": package_id,
        "generation": generation,
        "snapshot_sha256": pointer["snapshot_sha256"],
        "artifact_bytes_sha256": bytes_sha,
        "artifact_checksum": promoted.checksum,
        "n": int(promoted.n),
        "d": int(promoted.d),
        "m": int(promoted.m),
        "model": model,
        "pool": pool_result,
        "proposal": proposal,
        "training": builders._unwrap(training_meta),
        "manifest": builders._unwrap(manifest_meta),
        "manifest_sha256": manifest_meta["sha256"],
    }
