"""Metric-composite study integration (Pass 2, protocol ``bo-study-v1.1``).

This module extends the existing builder/service system rather than inventing a parallel store:

    build_metric_training(service, study_id, *, root, ...)
    build_metric_model(service, study_id, *, root, ...)
    build_metric_pool(service, study_id, *, root, ...)          # helper used by the synthetic path
    build_metric_proposal(service, study_id, *, root, ...)
    metric_bindings(service, study_id, proposal=None)
    prepare_metric_run_package(...)
    metric_execution_gate(package, *, allow_real_solver=False, synthetic_evaluator=None)

Every write goes through :meth:`StudyService.attach_artifact`; the durable journal is the real
:class:`~hornlab_search.studies.production.ProductionJournal` over a temp ``StudyService``.
``metric_composite_v1`` is deliberately absent from ``PRODUCTION_POLICIES`` and the execution gate
refuses real solver runs: the only allowed evaluator is an explicitly injected synthetic function.

Importing this module does not import Torch, BoTorch, a solver or a mesher.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hornlab_search.bo import metric_artifact, metric_contracts, metric_identity
from hornlab_search.bo.data import CandidatePool, PoolCandidate
from hornlab_search.bo.metric_contracts import SelectionResult, component_names, sha256_json
from hornlab_search.bo.metric_training import build_metric_training_artifact
from hornlab_search.bo.policy import POLICY_METRIC_COMPOSITE
from hornlab_search.bo.propose import ProposalHistory

from . import builders
from .package import (
    PACKAGE_KIND,
    PACKAGE_SCHEMA,
    package_hash,
    prepare_run_package,
    verify_package,
)
from .runner import (
    CapabilityMissing,
    ContractError,
    decode_proposal_history,
    encode_proposal_history,
    run_package,
)
from .schema import PROTOCOL, Conflict, StudyError, Unavailable, canonical
from .service import DraftAttemptJournal, StudyService

METRIC_POLICY = POLICY_METRIC_COMPOSITE
METRIC_TRAINING_KIND = metric_artifact.ARTIFACT_KIND          # "metric_training"
METRIC_TRAINING_MANIFEST_KIND = "metric_training_manifest"
METRIC_TRAINING_MANIFEST_SCHEMA = "metric-training-manifest-v1"
METRIC_MODEL_SCHEMA = "study-model-manifest-v1"
METRIC_PROPOSAL_SCHEMA = "study-proposal-v1"
METRIC_POOL_SCHEMA = builders.POOL_MANIFEST_SCHEMA

SYNTHETIC_PROVENANCE = {
    "synthetic": True,
    "real_solver_calls": 0,
    "no_backend_calls": True,
    "evaluator": "metric_synthetic_evaluator",
    "note": "synthetic metric-composite study; no mesh, BEM/GPU, pipeline or dataset call",
}

SUPPORTED_OBJECTIVE_VERSIONS = (10, 11)

#: Task identity fields compared by the policy and the artifact validator.
TASK_IDENTITY_FIELDS = ("task_identity", "backend", "fidelity", "grid_hash",
                        "dependency_hash", "mesh_hash")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _json(service, study_id, kind):
    meta = service.get_artifact_metadata(study_id, kind)
    if meta.get("status") != "available":
        raise Unavailable(f"{kind} artifact unavailable")
    return json.loads(service.store.read_artifact(meta["sha256"]))


def _existing(service, study_id, revision, kind):
    meta = service.get_artifact_metadata(study_id, kind, revision=revision)
    return meta if meta.get("status") in ("available", "stale") else None


def _unwrap(meta):
    return {k: meta[k] for k in ("study_id", "revision", "kind", "sha256", "status")
            if k in meta}


def _artifact_bytes(artifact) -> bytes:
    return metric_artifact.artifact_bytes(artifact)


# --------------------------------------------------------------------------- identity


def _config_encoding(snapshot):
    """Best-effort live projection from the snapshot's frozen config (None when unreadable)."""
    task = (snapshot or {}).get("task") or {}
    raw = task.get("config")
    if not raw or not Path(str(raw)).is_file():
        return None
    try:
        from hornlab_search.config import load_config
        from hornlab_search.design.space import DesignSpace
        cfg = load_config(raw)
        space = DesignSpace.from_config(cfg)
        return builders._task_encoding(space)
    except Exception:  # noqa: BLE001 - identity derivation falls back to explicit pins
        return None


def _derive_identity(snapshot, *, identity_metadata=None):
    """Build the complete identity metadata block for a metric training artifact.

    Explicit caller values win; anything absent is derived from the frozen snapshot/config.  A
    missing score identity token is refused rather than invented from an unrelated hash.
    """
    explicit = dict(identity_metadata or {})
    task = (snapshot or {}).get("task") or {}
    version = explicit.get("objective_version", task.get("objective_version"))
    try:
        version = int(version)
    except (TypeError, ValueError):
        raise Unavailable("metric training needs objective version 10 or 11")
    if version not in SUPPORTED_OBJECTIVE_VERSIONS:
        raise Unavailable(f"metric training supports objective v10/v11, got {version!r}")
    if task.get("objective_version") is not None \
            and int(task["objective_version"]) != version:
        raise Unavailable("caller objective version disagrees with the frozen snapshot")

    encoding = explicit.get("encoding") if isinstance(explicit, dict) else None
    if encoding is None:
        encoding = _config_encoding(snapshot)
    metadata = dict(explicit)
    metadata.pop("encoding", None)
    if "bounds_hash" not in metadata or "bounds_identity_payload" not in metadata:
        if encoding is None:
            raise Unavailable("metric training needs the live encoding or explicit bounds identity")
        payload = metric_identity.bounds_payload(encoding, strict=True)
        metadata["bounds_hash"] = metric_identity.recompute_bounds_hash(payload)
        metadata["bounds_identity_payload"] = payload
        metadata["active_keys"] = list(payload["active_keys"])
        metadata["projection_version"] = payload["projection_version"]

    brief_hash = str(metadata.get("brief_hash") or task.get("brief_sha256") or "").strip()
    score_hash = str(metadata.get("score_hash") or "").strip()
    if not brief_hash:
        raise Unavailable("metric training needs a brief identity hash")
    if not score_hash:
        raise Unavailable("metric training needs the frozen catalog score identity hash")
    score_module = metadata.get("score_module")
    score_payload = metric_identity.score_payload(
        objective_version=version, brief_hash=brief_hash, score_hash=score_hash,
        score_module=score_module)
    metadata.setdefault("score_identity_payload", score_payload)
    metadata.setdefault("score_identity", metric_identity.recompute_score_hash(score_payload))
    metadata.setdefault("brief_hash", brief_hash)
    metadata.setdefault("score_hash", score_hash)
    metadata.setdefault("objective_version", version)

    metadata.setdefault("task_identity", str(task.get("config_sha256") or ""))
    metadata.setdefault("backend", str(task.get("backend") or "synthetic"))
    metadata.setdefault("fidelity", "screen")
    if "grid_hash" not in metadata:
        metadata["grid_hash"] = sha256_json({
            "band_lo_hz": (task.get("resolved_target") or {}).get("band_lo_hz"),
            "band_hi_hz": (task.get("resolved_target") or {}).get("band_hi_hz"),
            "config_sha256": task.get("config_sha256"),
        })
    if "dependency_hash" not in metadata:
        source = (snapshot or {}).get("source") or {}
        metadata["dependency_hash"] = sha256_json({
            "scores_json_sha256": source.get("scores_json_sha256"),
            "catalog_csv_sha256": source.get("catalog_csv_sha256"),
            "config_sha256": task.get("config_sha256"),
            "brief_sha256": task.get("brief_sha256"),
        })
    metadata.setdefault("mesh_hash", "")
    for field in TASK_IDENTITY_FIELDS:
        value = metadata.get(field)
        if field != "mesh_hash" and (value is None or not str(value).strip()):
            raise Unavailable(f"metric training identity field {field!r} is missing")
    metadata["component_schema"] = metric_contracts.component_schema(version)["schema_id"]
    metadata["component_schema_hash"] = metric_contracts.component_schema_hash(version)
    return metadata


def _validate_selection(selection, metadata):
    if not isinstance(selection, SelectionResult):
        raise Unavailable("an explicit SelectionResult is required for metric training")
    if not selection.ok or selection.status != "ok":
        raise Unavailable(f"metric selection status is {selection.status!r}; refusing to publish")
    version = int(metadata["objective_version"])
    expected = tuple(component_names(version))
    if selection.objective_version is not None and int(selection.objective_version) != version:
        raise Unavailable("selection objective version disagrees with the identity block")
    if tuple(selection.component_names) and tuple(selection.component_names) != expected:
        raise Unavailable("selection component names/order disagree with the frozen schema")
    if not selection.selected:
        raise Unavailable("metric selection has no selected observations")
    bounds = str(metadata.get("bounds_hash") or "")
    for candidate in selection.selected:
        if candidate.components is None:
            raise Unavailable(f"selected observation {candidate.observation_id!r} has no components")
        if tuple(candidate.component_names) and tuple(candidate.component_names) != expected:
            raise Unavailable(f"selected observation {candidate.observation_id!r} has a different "
                              "component schema")
        if candidate.bounds_hash and bounds and candidate.bounds_hash != bounds:
            raise Unavailable(f"selected observation {candidate.observation_id!r} has a different "
                              "bounds identity")
        try:
            if not float(candidate.J) == float(candidate.J):
                raise ValueError("non-finite J")
        except (TypeError, ValueError):
            raise Unavailable(f"selected observation {candidate.observation_id!r} has no finite J")
    return selection


def _selection_from_spec(effective):
    """Only an explicit selection (or explicit records) is accepted; never fabricated."""
    records = effective.get("metric_records") if isinstance(effective, dict) else None
    if records is None:
        raise Unavailable("an explicit metric SelectionResult is required; no selection is "
                          "inferred from scalar training artifacts")
    raise Unavailable("metric_records must be selected by the caller into a SelectionResult")


# --------------------------------------------------------------------------- training


def build_metric_training(service, study_id, *, root, spec=None, selection=None,
                          identity_metadata=None, idempotency_key=None):
    """Build/attach ``metric_training`` (npz bytes) and its manifest.

    ``selection`` is an explicit, already-selected :class:`SelectionResult` (the metric selector is
    a caller decision; this builder never invents components).  Dependencies always include the
    frozen snapshot and, when declared, the scalar training artifacts the selection came from.
    """
    study, effective = builders._study_spec(service, study_id, spec)
    revision = study["revision"]
    existing = {kind: _existing(service, study_id, revision, kind)
                for kind in (METRIC_TRAINING_KIND, METRIC_TRAINING_MANIFEST_KIND)}
    if all(existing.values()):
        return {"status": "ok", "revision": revision, "idempotent": True,
                "training": _unwrap(existing[METRIC_TRAINING_KIND]),
                "manifest": _unwrap(existing[METRIC_TRAINING_MANIFEST_KIND]),
                "artifact": existing[METRIC_TRAINING_MANIFEST_KIND]}
    snapshot_meta = builders._require(service, study_id, "snapshot")
    snapshot = _json(service, study_id, "snapshot")
    metadata = _derive_identity(snapshot, identity_metadata=identity_metadata)
    if selection is None:
        selection = _selection_from_spec(effective if isinstance(effective, dict) else {})
    selection = _validate_selection(selection, metadata)
    feature_names = tuple(str(k) for k in (metadata.get("active_keys") or ())) or None
    artifact = build_metric_training_artifact(
        selection, identity_metadata=metadata, feature_names=feature_names)
    if not artifact.ok:
        raise Unavailable("metric training artifact refused: " + "; ".join(artifact.reasons))
    blob = _artifact_bytes(artifact)
    bytes_sha = _sha256_bytes(blob)
    deps = {"snapshot": snapshot_meta["sha256"]}
    # A selection explicitly sourced from the scalar training artifacts records those pins.
    source_kinds = (effective.get("metric_selection_source")
                    if isinstance(effective, dict) else None) or ()
    for kind in ("training", "training_manifest"):
        if kind in source_kinds:
            dep = builders._require(service, study_id, kind)
            deps[kind] = dep["sha256"]
    manifest = {
        "tool": "study_metric_training_manifest",
        "schema": METRIC_TRAINING_MANIFEST_SCHEMA,
        "schema_version": 1,
        "protocol": PROTOCOL,
        "generated_utc": _utc_now(),
        "study_id": study_id,
        "revision": revision,
        "status": "ok",
        "artifact_format": metric_artifact.ARTIFACT_FORMAT,
        "artifact_kind": metric_artifact.ARTIFACT_KIND,
        "artifact_bytes_sha256": bytes_sha,
        "checksum": artifact.checksum,
        "objective_version": int(artifact.objective_version),
        "component_names": list(artifact.component_names),
        "component_schema": metadata.get("component_schema"),
        "component_schema_hash": metadata.get("component_schema_hash"),
        "bounds": {"hash": metadata.get("bounds_hash"),
                   "payload": metadata.get("bounds_identity_payload")},
        "score": {"identity": metadata.get("score_identity"),
                  "payload": metadata.get("score_identity_payload")},
        "task": {field: metadata.get(field) for field in TASK_IDENTITY_FIELDS},
        "active_keys": metadata.get("active_keys"),
        "projection_version": metadata.get("projection_version"),
        "feature_names": list(artifact.feature_names),
        "observation_ids": list(artifact.observation_ids),
        "selected_ids": list(artifact.selected_ids),
        "excluded": [dict(e) for e in artifact.excluded],
        "excluded_ids": [str(e.get("observation_id")) for e in artifact.excluded],
        "selection_policy": dict(metadata.get("policy") or {}),
        "selection_policy_hash": metadata.get("policy_hash"),
        "d": int(artifact.d),
        "n": int(artifact.n),
        "m": int(artifact.m),
        "synthetic": True,
        "no_backend_calls": True,
        "dependencies": dict(deps),
        "limitations": [
            "Training rows are compatible canonical observations only; no prediction or failed "
            "solve is trained.",
            "Synthetic-only Pass 2 artifact; no BEM/GPU solve, replay or queue action was taken.",
        ],
    }
    training_meta = builders._attach_once(
        service, study_id, revision, METRIC_TRAINING_KIND, blob, deps,
        idempotency_key or f"{METRIC_TRAINING_KIND}:{revision}:{bytes_sha}")
    manifest_deps = {**deps, METRIC_TRAINING_KIND: training_meta["sha256"]}
    manifest["dependencies"] = dict(manifest_deps)
    manifest_meta = builders._attach_once(
        service, study_id, revision, METRIC_TRAINING_MANIFEST_KIND,
        builders._json_bytes(manifest), manifest_deps,
        f"{METRIC_TRAINING_MANIFEST_KIND}:{revision}:{bytes_sha}")
    return {"status": "ok", "revision": revision, "idempotent": False,
            "training": _unwrap(training_meta), "manifest": _unwrap(manifest_meta),
            "artifact": manifest_meta, "checksum": artifact.checksum,
            "artifact_bytes_sha256": bytes_sha,
            "d": int(artifact.d), "n": int(artifact.n), "m": int(artifact.m)}


def _load_training_artifact(service, study_id):
    """Reload + revalidate the frozen training artifact against its manifest identities."""
    training_meta = builders._require(service, study_id, METRIC_TRAINING_KIND)
    manifest_meta = builders._require(service, study_id, METRIC_TRAINING_MANIFEST_KIND)
    manifest = _json(service, study_id, METRIC_TRAINING_MANIFEST_KIND)
    blob = service.store.read_artifact(training_meta["sha256"])
    if _sha256_bytes(blob) != manifest.get("artifact_bytes_sha256"):
        raise Unavailable("metric training bytes disagree with the manifest hash")
    artifact, check = metric_artifact.artifact_from_bytes(
        blob, expected_checksum=manifest.get("checksum"))
    if artifact is None or not check.ok:
        raise Unavailable(f"metric training artifact could not be loaded: "
                          f"{check.detail or check.reason}")
    expected_score = (manifest.get("score") or {}).get("payload")
    expected_bounds = ((manifest.get("bounds") or {}).get("hash"))
    expected_task = manifest.get("task") or {}
    validation = metric_artifact.validate_metric_training_artifact(
        artifact, expected_bounds_hash=expected_bounds,
        expected_score=expected_score, expected_task=expected_task)
    if not validation.ok:
        raise Unavailable(f"metric training artifact identity validation failed: "
                          f"{validation.detail or validation.reason}")
    if str(artifact.checksum) != str(manifest.get("checksum")):
        raise Unavailable("metric training checksum disagrees with the manifest")
    return artifact, manifest, training_meta, manifest_meta


# --------------------------------------------------------------------------- model


def build_metric_model(service, study_id, *, root, seed=0, idempotency_key=None):
    """Fit the multi-output component GP on CPU and attach the JSON model manifest.

    No pickled model object is ever written: the manifest records the deterministic reconstruction
    inputs (artifact checksum/bytes hash, seed, dependency versions), the model hash, per-output
    hyperparameters and timing.
    """
    study = service.get_study(study_id)
    revision = study["revision"]
    existing = _existing(service, study_id, revision, "model")
    if existing is not None:
        return {"status": "ok", "revision": revision, "idempotent": True,
                "model": _unwrap(existing), "artifact": existing}
    snapshot_meta = builders._require(service, study_id, "snapshot")
    artifact, training_manifest, training_meta, manifest_meta = _load_training_artifact(
        service, study_id)
    from hornlab_search.bo.metric_model import fit_metric_model
    fitted = fit_metric_model(artifact, seed=int(seed))
    if getattr(fitted, "status", None) != "ok":
        raise Unavailable(f"metric model fit refused: {fitted.reason}: {fitted.detail}")
    payload = {
        "tool": "study_metric_model_manifest",
        "schema": METRIC_MODEL_SCHEMA,
        "schema_version": 1,
        "protocol": PROTOCOL,
        "generated_utc": _utc_now(),
        "study_id": study_id,
        "revision": revision,
        "status": "ok",
        "policy": METRIC_POLICY,
        "verification_mode": "scalar",
        "seed": int(seed),
        "artifact_checksum": artifact.checksum,
        "artifact_bytes_sha256": training_meta["sha256"],
        "training_manifest_sha256": manifest_meta["sha256"],
        "objective_version": int(artifact.objective_version),
        "component_names": list(artifact.component_names),
        "component_schema_hash": training_manifest.get("component_schema_hash"),
        "bounds_hash": training_manifest.get("bounds", {}).get("hash"),
        "model_hash": fitted.model_hash,
        "d": int(fitted.d or 0),
        "n": int(fitted.n or 0),
        "output_names": list(fitted.output_names),
        "per_output": [dict(record) for record in (fitted.per_output or ())],
        "timing_s": fitted.timing_s,
        "library_versions": dict(fitted.library_versions or {}),
        "warnings": list(fitted.warnings or ()),
        "reconstruction": {
            "source": "metric_training artifact bytes",
            "artifact_bytes_sha256": training_meta["sha256"],
            "artifact_checksum": artifact.checksum,
            "seed": int(seed),
            "fit_function": "hornlab_search.bo.metric_model.fit_metric_model",
        },
        "model_state_persisted": False,
        "pickled_model": False,
        "synthetic": True,
        "no_backend_calls": True,
        "dependencies": {"snapshot": snapshot_meta["sha256"],
                         METRIC_TRAINING_KIND: training_meta["sha256"],
                         METRIC_TRAINING_MANIFEST_KIND: manifest_meta["sha256"]},
        "limitations": [
            "Independent-output GPs: inter-component correlation is not modelled.",
            "Hyperparameters are published as JSON; no pickled model object is serialised.",
        ],
    }
    meta = builders._attach_once(
        service, study_id, revision, "model", builders._json_bytes(payload),
        payload["dependencies"],
        idempotency_key or f"model:{revision}:{METRIC_POLICY}:{int(seed)}")
    return {"status": "ok", "revision": revision, "idempotent": False,
            "model": _unwrap(meta), "artifact": meta, "model_hash": fitted.model_hash}


# --------------------------------------------------------------------------- pool


def build_metric_pool(service, study_id, *, root, pool=None, config_path=None, encoding=None,
                      idempotency_key=None, spec=None):
    """Attach the immutable candidate pool used by a metric proposal (or use its manifest)."""
    study, effective = builders._study_spec(service, study_id, spec)
    revision = study["revision"]
    existing = _existing(service, study_id, revision, "pool")
    if existing is not None:
        return {"status": "ok", "revision": revision, "idempotent": True,
                "pool": _unwrap(existing), "artifact": existing}
    snapshot_meta = builders._require(service, study_id, "snapshot")
    snapshot = _json(service, study_id, "snapshot")
    if pool is None:
        task = snapshot.get("task") or {}
        config_path = config_path or task.get("config")
        if config_path is None:
            raise Unavailable("a candidate pool or frozen task config is required")
        source = effective.get("source") if isinstance(effective, dict) else None
        pool = builders._load_pool(None, source, config_path, root=root, seed=0)
        if encoding is None:
            encoding = _config_encoding(snapshot)
    payload = builders._pool_manifest(
        pool, policy=METRIC_POLICY,
        config_path=(config_path or (snapshot.get("task") or {}).get("config") or ""),
        encoding=encoding)
    payload["metric_policy"] = METRIC_POLICY
    payload["synthetic"] = True
    meta = builders._attach_once(
        service, study_id, revision, "pool", builders._json_bytes(payload),
        {"snapshot": snapshot_meta["sha256"]},
        idempotency_key or f"pool:{revision}:{METRIC_POLICY}")
    return {"status": "ok", "revision": revision, "idempotent": False,
            "pool": _unwrap(meta), "artifact": meta,
            "n_candidates": len(getattr(pool, "candidates", ()) or ())}


def _load_pool_object(service, study_id):
    raw = _json(service, study_id, "pool")
    if not raw.get("candidates"):
        raise Unavailable("metric pool artifact has no candidates")
    candidates = []
    import numpy as np
    for row in raw["candidates"]:
        row = dict(row)
        for key in ("active_vector", "full_vector"):
            row[key] = np.asarray(row[key], dtype=float)
        candidates.append(PoolCandidate(**row))
    summary = raw.get("summary") or {}
    return CandidatePool(
        status="ok", requested=len(candidates), seed=summary.get("seed"),
        seeds_tried=tuple(summary.get("seeds_tried") or ()), candidates=tuple(candidates),
        counts=summary.get("counts") or {}, seed_reports=(),
        intended_solve_hash=summary.get("intended_solve_hash"),
        note=raw.get("status_note") or builders.POOL_STATUS_NOTE)


# --------------------------------------------------------------------------- proposal


def build_metric_proposal(service, study_id, *, root, policy=METRIC_POLICY, seed=0,
                          idempotency_key=None):
    """Validate the model manifest, re-fit deterministically and attach ``study-proposal-v1``."""
    if policy != METRIC_POLICY:
        raise StudyError(f"unsupported metric proposal policy {policy!r}")
    study = service.get_study(study_id)
    revision = study["revision"]
    existing = _existing(service, study_id, revision, "proposal")
    if existing is not None:
        return {"status": "ok", "revision": revision, "idempotent": True,
                "proposal": _unwrap(existing), "artifact": existing}
    snapshot_meta = builders._require(service, study_id, "snapshot")
    pool_meta = builders._require(service, study_id, "pool")
    model_meta = builders._require(service, study_id, "model")
    model_manifest = _json(service, study_id, "model")
    artifact, training_manifest, training_meta, manifest_meta = _load_training_artifact(
        service, study_id)
    if model_manifest.get("status") != "ok" or model_manifest.get("policy") != METRIC_POLICY:
        raise Unavailable("metric model manifest is not a successful metric_composite_v1 fit")
    if model_manifest.get("artifact_bytes_sha256") != training_meta["sha256"]:
        raise Unavailable("metric model manifest binds a different training artifact")
    model_seed = model_manifest.get("seed")
    if type(model_seed) is not int or model_seed < 0:
        raise Unavailable("metric model manifest has an invalid seed")
    from hornlab_search.bo.metric_model import fit_metric_model
    from hornlab_search.bo.metric_propose import MetricProposalPolicy, propose_metric_candidate
    fitted = fit_metric_model(artifact, seed=model_seed)
    if getattr(fitted, "status", None) != "ok":
        raise Unavailable(f"deterministic metric refit refused: {fitted.reason}: {fitted.detail}")
    if str(fitted.model_hash) != str(model_manifest.get("model_hash")):
        raise Unavailable("deterministic metric refit produced a different model_hash")
    pool = _load_pool_object(service, study_id)
    bounds_hash = str((training_manifest.get("bounds") or {}).get("hash") or "")
    proposal_policy = MetricProposalPolicy(
        acq_seed=int(seed), proposal_seed=int(seed), bounds_hash=bounds_hash)
    result = propose_metric_candidate(
        fitted, pool, policy=proposal_policy, history=_fresh_metric_history(),
        require_identity=True, expected_bounds_hash=bounds_hash)
    if getattr(result, "status", None) != "ok":
        raise Unavailable(f"metric proposal refused: {result.reason}: {result.detail}")
    payload = {
        "tool": "study_metric_proposal",
        "schema": METRIC_PROPOSAL_SCHEMA,
        "schema_version": 1,
        "protocol": PROTOCOL,
        "generated_utc": _utc_now(),
        "study_id": study_id,
        "revision": revision,
        "status": "ok",
        "reason": "ok",
        "proposal_policy": METRIC_POLICY,
        "verification_mode": "scalar",
        "seed": int(seed),
        "selection_reason": result.selection_reason,
        "candidate": result.candidate,
        "proposal": result.candidate,
        "predicted": {
            "component_means": [float(v) for v in (result.component_means or ())],
            "component_sds": [float(v) for v in (result.component_sds or ())],
            "j_mean": result.predicted_j,
            "total_sd": result.total_sd,
            "note": "model prediction, not a solved acoustic result",
        },
        "acquisition": {
            "value": result.acquisition_score,
            "units": "qLogNEI (technical ranking only, not J and not a probability)",
            "policy": result.policy,
            "acq_seed": int(result.acq_seed),
        },
        "model": {"sha256": model_meta["sha256"], "model_hash": fitted.model_hash},
        "pool": {"sha256": pool_meta["sha256"],
                 "n_candidates": len(pool.candidates)},
        "metric_training": {
            "artifact_bytes_sha256": training_meta["sha256"],
            "manifest_sha256": manifest_meta["sha256"],
            "checksum": training_manifest.get("checksum"),
            "objective_version": training_manifest.get("objective_version"),
            "component_names": list(training_manifest.get("component_names") or ()),
            "component_schema_hash": training_manifest.get("component_schema_hash"),
            "bounds": dict(training_manifest.get("bounds") or {}),
            "score": dict(training_manifest.get("score") or {}),
            "task": dict(training_manifest.get("task") or {}),
        },
        "predictions_appended_to_measured_rows": False,
        "status_note": builders.POOL_STATUS_NOTE,
        "provenance": dict(SYNTHETIC_PROVENANCE),
        "synthetic": True,
        "no_backend_calls": True,
        "dependencies": {"snapshot": snapshot_meta["sha256"],
                         METRIC_TRAINING_KIND: training_meta["sha256"],
                         METRIC_TRAINING_MANIFEST_KIND: manifest_meta["sha256"],
                         "model": model_meta["sha256"],
                         "pool": pool_meta["sha256"]},
        "limitations": [
            "Advisory synthetic proposal; no BEM/GPU solve was run.",
            "Predicted component means/SDs and J are model outputs, not measured results.",
            "The acquisition value is a technical ranking diagnostic, not J and not a "
            "probability of success.",
        ],
    }
    meta = builders._attach_once(
        service, study_id, revision, "proposal", builders._json_bytes(payload),
        payload["dependencies"],
        idempotency_key or f"proposal:{revision}:{METRIC_POLICY}:{int(seed)}")
    return {"status": "ok", "revision": revision, "idempotent": False,
            "proposal": _unwrap(meta), "artifact": meta,
            "candidate_id": result.candidate_id,
            "predicted": payload["predicted"], "acquisition": payload["acquisition"]}


def _fresh_metric_history():
    """A fresh durable proposal history for a direct (non-journal) metric proposal call."""
    from hornlab_search.bo.metric_propose import MetricProposalHistory
    return MetricProposalHistory()


# --------------------------------------------------------------------------- bindings


def metric_bindings(service, sid, proposal=None):
    """Re-read/revalidate the training artifact and compare the proposal's pinned checksums.

    Mirrors ``pareto_bindings``: returns a typed ``ok``/refusal mapping instead of raising for a
    missing or tampered binding.  A real execution path must never use this to authorize a solve.
    """
    try:
        proposal = proposal if proposal is not None else _json(service, sid, "proposal")
    except Unavailable as exc:
        return {"status": "unavailable", "reason": "metric_proposal_missing",
                "detail": str(exc)}
    binding = proposal.get("metric_training") if isinstance(proposal, dict) else None
    if not isinstance(binding, dict) or not binding.get("artifact_bytes_sha256"):
        return {"status": "unavailable", "reason": "metric_binding_missing",
                "detail": "proposal does not bind a metric-training-v1 artifact"}
    meta = service.get_artifact_metadata(sid, METRIC_TRAINING_KIND)
    if meta.get("status") != "available" or meta.get("sha256") != binding["artifact_bytes_sha256"]:
        return {"status": "unavailable", "reason": "metric_artifact_mismatch",
                "detail": "metric training artifact is missing or differs from the proposal"}
    manifest_meta = service.get_artifact_metadata(sid, METRIC_TRAINING_MANIFEST_KIND)
    if binding.get("manifest_sha256") and manifest_meta.get("sha256") != binding["manifest_sha256"]:
        return {"status": "unavailable", "reason": "metric_artifact_mismatch",
                "detail": "metric training manifest differs from the proposal binding"}
    try:
        blob = service.store.read_artifact(meta["sha256"])
    except Unavailable as exc:
        return {"status": "unavailable", "reason": "metric_artifact_mismatch", "detail": str(exc)}
    artifact, check = metric_artifact.artifact_from_bytes(
        blob, expected_checksum=binding.get("checksum"))
    if artifact is None or not check.ok:
        return {"status": "unavailable", "reason": "metric_artifact_invalid",
                "detail": check.detail or check.reason}
    bounds = binding.get("bounds") or {}
    score = binding.get("score") or {}
    validation = metric_artifact.validate_metric_training_artifact(
        artifact, expected_bounds_hash=bounds.get("hash"),
        expected_score=score.get("payload"), expected_task=binding.get("task"))
    if not validation.ok:
        return {"status": "unavailable", "reason": "metric_identity_mismatch",
                "detail": validation.detail or validation.reason}
    if str(artifact.checksum) != str(binding.get("checksum")):
        return {"status": "unavailable", "reason": "metric_artifact_mismatch",
                "detail": "artifact checksum differs from the proposal binding"}
    if str(artifact.objective_version) != str(binding.get("objective_version")):
        return {"status": "unavailable", "reason": "metric_identity_mismatch",
                "detail": "artifact objective version differs from the proposal binding"}
    return {
        "status": "ok",
        "reason": "ok",
        "detail": None,
        "artifact": artifact,
        "artifact_checksum": artifact.checksum,
        "artifact_bytes_sha256": meta["sha256"],
        "manifest_sha256": manifest_meta.get("sha256"),
        "bounds_hash": bounds.get("hash"),
        "score_identity": (score.get("identity")
                           or (score.get("payload") or {}).get("score_identity")),
        "objective_version": int(artifact.objective_version),
        "component_names": list(artifact.component_names),
        "component_schema_hash": metric_contracts.component_schema_hash(
            int(artifact.objective_version)),
        "n": int(artifact.n),
        "d": int(artifact.d),
        "m": int(artifact.m),
        "synthetic": True,
        "no_backend_calls": True,
    }


# --------------------------------------------------------------------------- package / gate


def prepare_metric_run_package(service, study_id, *, expected_revision=None, lane="cpu",
                               deadline=None, idempotency_key=None, code_pins=None,
                               dependency_pins=None, resolved_config=None,
                               budget_profile="baseline"):
    """Reuse :func:`prepare_run_package` with the additive synthetic metric block."""
    bindings = metric_bindings(service, study_id)
    if bindings.get("status") != "ok":
        raise Unavailable(f"metric proposal bindings are not ready: {bindings.get('detail')}")
    metric = {
        "policy": METRIC_POLICY,
        "training_artifact_sha256": bindings["artifact_bytes_sha256"],
        "training_manifest_sha256": bindings["manifest_sha256"],
        "training_checksum": bindings["artifact_checksum"],
        "objective_version": bindings["objective_version"],
        "component_schema_hash": bindings["component_schema_hash"],
        "bounds_hash": bindings["bounds_hash"],
        "score_identity": bindings["score_identity"],
        "proposal_sha256": (service.get_artifact_metadata(study_id, "proposal").get("sha256")),
        "model_sha256": (service.get_artifact_metadata(study_id, "model").get("sha256")),
        "synthetic": True,
        "real_solver_allowed": False,
        "no_backend_calls": True,
        "provenance": dict(SYNTHETIC_PROVENANCE),
    }
    return prepare_run_package(
        service, study_id, expected_revision=expected_revision, lane=lane,
        deadline=deadline, idempotency_key=idempotency_key, code_pins=code_pins,
        dependency_pins=dependency_pins, resolved_config=resolved_config,
        budget_profile=budget_profile, metric=metric)


def metric_execution_gate(package, *, allow_real_solver=False, synthetic_evaluator=None):
    """Typed gate for the metric package: synthetic evaluator only, never a real solver.

    ``allow_real_solver`` is accepted for symmetry with future gates but is deliberately not
    sufficient: a metric-composite package is never authorized to touch mesh/BEM/GPU/pipeline.
    """
    if not isinstance(package, dict):
        return {"status": "refused", "reason": "invalid_package",
                "detail": "package must be an object", "real_solver_allowed": False}
    try:
        verify_package(package)
    except (StudyError, Unavailable) as exc:
        return {"status": "refused", "reason": "invalid_package", "detail": str(exc),
                "real_solver_allowed": False}
    policy = (package.get("proposal_policy") or {}).get("policy")
    if policy != METRIC_POLICY:
        return {"status": "refused", "reason": "not_metric_package",
                "detail": f"package policy is {policy!r}, not {METRIC_POLICY!r}",
                "real_solver_allowed": False}
    metric = package.get("metric") or {}
    if metric.get("synthetic") is not True or metric.get("real_solver_allowed") is not False:
        return {"status": "refused",
                "reason": "metric_composite_real_execution_not_authorized",
                "detail": "metric package is not marked synthetic-only",
                "real_solver_allowed": False}
    if allow_real_solver:
        return {"status": "refused",
                "reason": "metric_composite_real_execution_not_authorized",
                "detail": "metric_composite_v1 real solver execution is not authorized",
                "real_solver_allowed": False}
    if not callable(synthetic_evaluator):
        return {"status": "refused",
                "reason": "metric_composite_real_execution_not_authorized",
                "detail": "an explicitly injected synthetic evaluator is required",
                "real_solver_allowed": False}
    return {"status": "ok", "reason": "synthetic_only",
            "detail": "synthetic evaluator injected; real solver forbidden",
            "real_solver_allowed": False, "synthetic_evaluator": synthetic_evaluator,
            "package_id": package.get("package_id")}


# --------------------------------------------------------------------------- synthetic adapters


class FrozenLaneAdapter:
    """No-op owned lane: it holds no cache/dataset roots and never starts a host or solver."""

    lane_contract = "b5-owned-lane-v1"

    def __init__(self):
        self.runtime = None

    @contextmanager
    def owned(self, lane, package):
        if lane not in ("cpu", "gpu") or package.get("lane") != lane:
            raise ValueError("explicit matching lane required")
        if self.runtime is not None:
            raise RuntimeError("nested synthetic lane ownership is not allowed")
        self.runtime = {"lane": lane, "synthetic": True, "dataset_dir": None,
                        "cache_dir": None, "worker_dir": None}
        try:
            yield self.runtime
        finally:
            self.runtime = None


class MetricSyntheticEvaluator:
    """Runner-protocol evaluator that only calls an injected deterministic synthetic function.

    The durable journal, candidate pool, model and artifact are real; the acoustic evaluation is
    a pure Python function supplied by the caller.  Nothing here imports or touches
    ``hornlab_search.solve``/``mesh``/``pipeline``.
    """

    adapter_contract = "b5-metric-synthetic-evaluator-v1"

    def __init__(self, artifact, model_result, pool, *, synthetic_evaluator, seed=0,
                 bounds_hash="", proposal_limit=None, policy=None, history=None,
                 initial_results=None):
        self.artifact = artifact
        self.model_result = model_result
        self.pool = pool
        self.synthetic_evaluator = synthetic_evaluator
        self.seed = int(seed)
        self.bounds_hash = str(bounds_hash or "")
        self.proposal_limit = (None if proposal_limit is None else int(proposal_limit))
        from hornlab_search.bo.metric_propose import MetricProposalPolicy
        self.policy = policy if isinstance(policy, MetricProposalPolicy) else MetricProposalPolicy(
            acq_seed=self.seed, proposal_seed=self.seed, bounds_hash=self.bounds_hash)
        # The runner's durable encode/decode contract uses the shared ProposalHistory shape; the
        # metric proposal engine accepts it directly (same field names).
        self.history = history if isinstance(history, ProposalHistory) else ProposalHistory()
        self._proposal_count = int(self.history.proposal_index)
        self._results = dict(initial_results or {})
        self._X = [list(map(float, row)) for row in artifact.X]
        self._J = list(map(float, artifact.J.reshape(-1)))
        self._Y = [list(map(float, row)) for row in artifact.Y_components]
        self._seen = set()

    # -- capability
    def capability_status(self):
        missing = []
        if not callable(self.synthetic_evaluator):
            missing.append("synthetic_evaluator")
        if getattr(self.model_result, "status", None) != "ok":
            missing.append("model")
        if getattr(self.pool, "status", None) != "ok" or not getattr(self.pool, "candidates", ()):
            missing.append("pool")
        if missing:
            return {"status": "capability_missing",
                    "reason": "synthetic_evaluator_unavailable",
                    "detail": "missing prerequisites: " + ", ".join(missing),
                    "missing": missing, "mode": "synthetic"}
        return {"status": "ok", "reason": None, "detail": None, "missing": [],
                "mode": "synthetic", "real_solver": False}

    # -- proposal
    def _candidate(self, result):
        raw = dict(result.candidate or {})
        vector = raw.get("active_vector", raw.get("full_vector"))
        vector = None if vector is None else [float(v) for v in vector]
        solve_id = (result.intended_solve_hash or raw.get("intended_solve_hash")
                    or result.design_hash or raw.get("design_hash")
                    or result.candidate_id or raw.get("candidate_id"))
        if not isinstance(solve_id, str) or not solve_id:
            raise ContractError("metric proposal did not carry an exact solve identity")
        geometry = (result.geometry_hash or raw.get("geometry_hash")
                    or result.design_hash or raw.get("design_hash") or solve_id)
        return {
            "kind": "screen",
            "solve_id": str(solve_id),
            "candidate_id": result.candidate_id or raw.get("candidate_id"),
            "geometry_id": str(geometry),
            "geometry_hash": str(geometry),
            "design_hash": result.design_hash or raw.get("design_hash"),
            "intended_solve_hash": result.intended_solve_hash or raw.get("intended_solve_hash"),
            "params": dict(raw.get("params") or {}),
            "x": vector,
            "vector": vector,
            "active_vector": vector,
            "predicted": {
                "component_means": list(result.component_means or ()),
                "component_sds": list(result.component_sds or ()),
                "j_mean": result.predicted_j,
                "total_sd": result.total_sd,
            },
            "selection_reason": result.selection_reason,
            "acquisition": {"value": result.acquisition_score,
                            "units": "qLogNEI (technical ranking only)",
                            "acq_seed": result.acq_seed},
            "status": builders.POOL_STATUS_NOTE,
            "checks": {},
            "descriptors": {},
        }

    def next_candidate(self, state):
        if self.proposal_limit is not None and self._proposal_count >= self.proposal_limit:
            return None
        from hornlab_search.bo.metric_propose import propose_metric_candidate
        result = propose_metric_candidate(
            self.model_result, self.pool, policy=self.policy, history=self.history,
            require_identity=True, expected_bounds_hash=self.bounds_hash)
        if getattr(result, "status", None) != "ok":
            return None
        candidate = self._candidate(result)
        geometry = candidate.get("geometry_hash")
        design = candidate.get("design_hash")
        self.history = replace(
            self.history,
            proposal_index=int(result.next_proposal_index or self.history.proposal_index + 1),
            excluded_geometry_hashes=tuple(dict.fromkeys(
                (*self.history.excluded_geometry_hashes, str(geometry)))),
            excluded_design_hashes=tuple(dict.fromkeys(
                (*self.history.excluded_design_hashes,
                 *([] if design is None else [str(design)])))),
        )
        self._proposal_count = int(self.history.proposal_index)
        return candidate

    # -- cache / cheap checks
    def lookup(self, candidate):
        result = self._results.get(str(candidate.get("solve_id")))
        if result is None:
            return None
        cached = dict(result)
        cached["call_status"] = "not_called"
        return cached

    def preflight(self, candidate):
        vector = candidate.get("active_vector", candidate.get("x"))
        if vector is None:
            return None
        try:
            import numpy as np
            arr = np.asarray(vector, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            return self._refusal(candidate, "invalid synthetic vector")
        if not np.all(np.isfinite(arr)) or np.any(arr < 0.0) or np.any(arr > 1.0):
            return self._refusal(candidate, "synthetic vector is non-finite or outside [0,1]")
        return None

    @staticmethod
    def _refusal(candidate, error):
        return {"solve_id": candidate["solve_id"], "kind": candidate.get("kind"),
                "call_status": "not_called", "outcome": "cheap_refusal", "eligible": False,
                "error": str(error), "geometry_id": candidate.get("geometry_id"),
                "design_hash": candidate.get("design_hash"),
                "synthetic": True}

    # -- evaluation (only the injected function)
    def evaluate(self, candidate, attempt_id):
        if not callable(self.synthetic_evaluator):
            raise CapabilityMissing("no synthetic evaluator was injected")
        result = self.synthetic_evaluator(candidate, attempt_id)
        if not isinstance(result, dict):
            raise ContractError("synthetic evaluator must return a result dict")
        result = dict(result)
        if result.get("solve_id") not in (None, candidate["solve_id"]):
            raise ContractError("synthetic result solve identity mismatch")
        result.setdefault("solve_id", candidate["solve_id"])
        result.setdefault("kind", "screen")
        result.setdefault("call_status", "called")
        result["synthetic"] = True
        result["provenance"] = dict(SYNTHETIC_PROVENANCE)
        result.setdefault("geometry_id", candidate.get("geometry_id"))
        result.setdefault("design_hash", candidate.get("design_hash"))
        result.setdefault("x", candidate.get("x"))
        result.setdefault("params", candidate.get("params") or {})
        if result.get("physical_id") is None:
            result["physical_id"] = "synthetic:" + candidate["solve_id"]
        if result.get("score_id") is None:
            result["score_id"] = "synthetic-score:" + candidate["solve_id"]
        self._results[candidate["solve_id"]] = result
        return result

    # -- learning
    def _augmented_artifact(self):
        from dataclasses import replace as _replace
        import numpy as np
        return _replace(
            self.artifact,
            X=np.asarray(self._X, dtype=np.float64),
            J=np.asarray(self._J, dtype=np.float64).reshape(-1, 1),
            Y_components=np.asarray(self._Y, dtype=np.float64),
            observation_ids=tuple(self.artifact.observation_ids)
            + tuple(f"synthetic-{i}" for i in range(len(self._X) - len(self.artifact.observation_ids))),
            selected_ids=tuple(self.artifact.selected_ids)
            + tuple(f"synthetic-{i}" for i in range(len(self._X) - len(self.artifact.selected_ids))))

    def _add_observation(self, result):
        if result.get("kind") not in (None, "screen"):
            return False
        if result.get("outcome") not in ("success", "cached"):
            return False
        if result.get("eligible") is not True:
            return False
        solve_id = str(result.get("solve_id"))
        if solve_id in self._seen:
            return False
        try:
            j = float(result.get("observed_j"))
        except (TypeError, ValueError):
            return False
        if j != j or j in (float("inf"), float("-inf")):
            return False
        components = result.get("components")
        if components is None:
            # A metric-composite refit cannot be honest without component labels.
            return False
        vector = result.get("x")
        if vector is None:
            return False
        try:
            import numpy as np
            x = np.asarray(vector, dtype=float).reshape(-1)
            y = np.asarray(components, dtype=float).reshape(-1)
        except (TypeError, ValueError):
            return False
        if x.size != len(self._X[0]) or y.size != len(self._Y[0]):
            return False
        self._X.append([float(v) for v in x])
        self._J.append(j)
        self._Y.append([float(v) for v in y])
        self._seen.add(solve_id)
        return True

    def _refit(self):
        from hornlab_search.bo.metric_model import fit_metric_model
        fitted = fit_metric_model(self._augmented_artifact(), seed=self.seed)
        if getattr(fitted, "status", None) == "ok":
            self.model_result = fitted
            return True
        reason = str(getattr(fitted, "reason", "") or "")
        if reason == "capability_missing":
            return True
        return reason not in ("model_unavailable", "nonfinite_training_data",
                              "nonfinite_posterior")

    def observe(self, result):
        if not isinstance(result, dict):
            return True
        if result.get("kind") in ("verify", "audit"):
            return True
        if self._add_observation(result):
            return self._refit()
        return True

    # -- resume
    def restore_progress(self, progress):
        if not isinstance(progress, dict):
            raise ContractError("journal progress must be an object")
        stored = progress.get("rng_state")
        history = decode_proposal_history(stored, progress.get("proposal_index"))
        self.history = history
        self._proposal_count = int(history.proposal_index)
        self._X = [list(map(float, row)) for row in self.artifact.X]
        self._J = list(map(float, self.artifact.J.reshape(-1)))
        self._Y = [list(map(float, row)) for row in self.artifact.Y_components]
        self._seen = set()
        self._results = {}
        for item in progress.get("observations") or ():
            result = dict(item.get("result") or {})
            candidate = dict(item.get("candidate") or {})
            if result.get("x") is None and candidate.get("x") is not None:
                result["x"] = candidate.get("x")
            self._results[str(result.get("solve_id") or candidate.get("solve_id"))] = result
            if self._add_observation(result):
                self._refit()
        return self._refit()

    def proposal_rng_state(self):
        return encode_proposal_history(self.history, {
            "proposal_sequence": self._proposal_count,
            "policy": METRIC_POLICY,
            "synthetic": True,
            "bounds_hash": self.bounds_hash,
        })


# --------------------------------------------------------------------------- orchestration


def _existing_package(service, study_id):
    meta = service.get_artifact_metadata(study_id, PACKAGE_KIND)
    if meta.get("status") != "available":
        return None
    raw = service.store.read_artifact(meta["sha256"])
    body = json.loads(raw)
    return {"package_id": _sha256_bytes(raw), **body}


def run_synthetic_metric_study(service, study_id, *, root, synthetic_evaluator,
                               selection=None, identity_metadata=None, pool=None,
                               seed=0, proposal_limit=None, deadline=None, lane="cpu",
                               package=None, spec=None, idempotency_key=None):
    """Orchestrate the synthetic metric-composite study end to end.

    Steps: frozen snapshot -> validated training artifact -> CPU model -> immutable pool ->
    proposal -> synthetic package -> durable journal run (simulate/observe/refit/next) -> persisted
    synthetic summary.  Calling again with the same package resumes from the durable journal; it
    never re-evaluates a resolved candidate and never silently re-selects a staged proposal.
    """
    from .production import ProductionJournal

    deadline = deadline or (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    builders._require(service, study_id, "snapshot")
    if selection is not None or _existing(service, study_id, service.get_study(study_id)["revision"],
                                          METRIC_TRAINING_KIND) is None:
        build_metric_training(service, study_id, root=root, spec=spec, selection=selection,
                              identity_metadata=identity_metadata)
    build_metric_model(service, study_id, root=root, seed=int(seed))
    if pool is not None or _existing(service, study_id, service.get_study(study_id)["revision"],
                                     "pool") is None:
        build_metric_pool(service, study_id, root=root, pool=pool, spec=spec)
    build_metric_proposal(service, study_id, root=root, policy=METRIC_POLICY, seed=int(seed))
    if package is None:
        package = _existing_package(service, study_id)
        if package is None:
            package = prepare_metric_run_package(service, study_id, lane=lane, deadline=deadline,
                                                 idempotency_key=idempotency_key)
    gate = metric_execution_gate(package, synthetic_evaluator=synthetic_evaluator)
    if gate.get("status") != "ok":
        raise Unavailable(f"metric execution gate refused: {gate.get('detail')}")
    artifact, manifest, training_meta, manifest_meta = _load_training_artifact(service, study_id)
    model_meta = builders._require(service, study_id, "model")
    model_manifest = _json(service, study_id, "model")
    from hornlab_search.bo.metric_model import fit_metric_model
    fitted = fit_metric_model(artifact, seed=int(model_manifest["seed"]))
    if getattr(fitted, "status", None) != "ok":
        raise Unavailable(f"synthetic study refit refused: {fitted.reason}")
    pool_obj = _load_pool_object(service, study_id)
    evaluator = MetricSyntheticEvaluator(
        artifact, fitted, pool_obj, synthetic_evaluator=synthetic_evaluator, seed=int(seed),
        bounds_hash=(manifest.get("bounds") or {}).get("hash") or "",
        proposal_limit=proposal_limit)
    lane_adapter = FrozenLaneAdapter()
    journal = ProductionJournal(service)
    result = run_package(package, evaluator, lane_adapter, journal)
    progress = journal.load_progress(package["package_id"])
    summary = {
        "status": result.get("status"),
        "package_id": package["package_id"],
        "study_id": study_id,
        "revision": package["spec_revision"],
        "proposal_policy": METRIC_POLICY,
        "model_hash": fitted.model_hash,
        "artifact_checksum": artifact.checksum,
        "artifact_bytes_sha256": training_meta["sha256"],
        "progress": journal.state(package["package_id"]),
        "observations": progress.get("observations") or (),
        "provenance": dict(SYNTHETIC_PROVENANCE),
        "synthetic": True,
        "no_backend_calls": True,
        "real_solver_calls": 0,
    }
    existing_results = service.get_artifact_metadata(study_id, "results")
    if existing_results.get("status") == "missing":
        try:
            service.attach_artifact(
                study_id, package["spec_revision"], "results",
                canonical(summary).encode("utf-8"), {"package": package["package_id"]},
                f"results:{package['package_id']}")
        except (Conflict, Unavailable):
            pass
    return {"status": result.get("status"), "package": package, "model_hash": fitted.model_hash,
            "artifact_checksum": artifact.checksum, "progress": summary["progress"],
            "observations": summary["observations"], "synthetic": True}


__all__ = [
    "METRIC_POLICY",
    "METRIC_TRAINING_KIND",
    "METRIC_TRAINING_MANIFEST_KIND",
    "METRIC_TRAINING_MANIFEST_SCHEMA",
    "METRIC_MODEL_SCHEMA",
    "METRIC_PROPOSAL_SCHEMA",
    "SYNTHETIC_PROVENANCE",
    "TASK_IDENTITY_FIELDS",
    "build_metric_training",
    "build_metric_model",
    "build_metric_pool",
    "build_metric_proposal",
    "metric_bindings",
    "prepare_metric_run_package",
    "metric_execution_gate",
    "MetricSyntheticEvaluator",
    "FrozenLaneAdapter",
    "run_synthetic_metric_study",
]
