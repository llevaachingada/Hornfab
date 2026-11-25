"""Durable metric-composite refit transaction (real canary worker, Pass 2/3).

This module owns the *only* place a real ``metric_composite_v1`` screen may enter a refit and
the only place a training snapshot/pointer is advanced.  It is deliberately small and numpy-only
at import time; the multi-output GP fit is imported lazily.

Transaction (all steps are ordered and idempotent):

1. accepted screens are validated against the frozen artifact identity and canonical component
   parity (:func:`metric_candidate_from_result`);
2. every ``refit_every`` (=4) newly accepted unique screens rebuild an immutable
   ``metric-training-v1`` artifact over the frozen base rows + the accepted rows;
3. that artifact's exact bytes are published content-addressed by :meth:`StudyStore.publish`;
4. a versioned ``metric-refit-snapshot-v1`` record is published content-addressed *before* the
   pointer moves;
5. only then is an append-only ``metric_refit_pointer`` event written.  A crash between 3/4 and 5
   leaves an orphan snapshot; recovery republishes the identical bytes (same digest) and advances
   the pointer once.  A backend call is never repeated because recovery only replays the journal.

Rows excluded from a refit: verify/audit, cache hits (``call_status != called``), duplicate
catalog observations, failed/refused outcomes, and rows whose metric parity or task identity was
refused.  Deduplication uses ``metric_dataset_record.physical_solve_id`` (the catalog identity),
never the replay physical id, which identifies different (replay) evidence.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from hornlab_search.bo import metric_artifact
from hornlab_search.bo.metric_contracts import (
    MetricTrainingCandidate,
    SelectionResult,
    parity_tolerance,
    validate_components,
)
from hornlab_search.bo.metric_training import build_metric_training_artifact
from hornlab_search.bo.policy import POLICY_METRIC_COMPOSITE

from .schema import StudyError, Unavailable, canonical, digest

METRIC_POLICY = POLICY_METRIC_COMPOSITE
METRIC_TRAINING_KIND = "metric_training"
METRIC_TRAINING_MANIFEST_KIND = "metric_training_manifest"

#: Real-execution provenance mode (frozen package interface agreed with the packaging lane).
REAL_METRIC_PROVENANCE = "real_metric_v1"
#: A refit is published after every four newly accepted unique canary screens.
REAL_METRIC_REFIT_EVERY = 4

METRIC_REFIT_SNAPSHOT_KIND = "metric_refit_snapshot"
METRIC_REFIT_SNAPSHOT_FORMAT = "metric-refit-snapshot-v1"
METRIC_REFIT_SNAPSHOT_SCHEMA_VERSION = 1
METRIC_REFIT_POINTER_EVENT = "metric_refit_pointer"
METRIC_REFIT_POINTER_FORMAT = "metric-refit-pointer-v1"

_IDENTITY_FIELDS = (
    "task_identity", "backend", "fidelity", "grid_hash", "dependency_hash", "mesh_hash",
    "brief_hash", "score_hash", "bounds_hash",
)
_HEX64 = set("0123456789abcdef")


class MetricRefitError(Unavailable):
    """A typed refusal from the metric refit/real-package gate."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_hex64(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX64


def _is_catalog_id(value) -> bool:
    """Catalog ``physical_solve_id`` is the 16-hex sha16 join key, not a sha256."""
    return isinstance(value, str) and len(value) == 16 and set(value) <= _HEX64


def _json(service, study_id, kind):
    meta = service.get_artifact_metadata(study_id, kind)
    if meta.get("status") != "available":
        raise Unavailable(f"{kind} artifact unavailable")
    return json.loads(service.store.read_artifact(meta["sha256"]))


def _artifact_identity_metadata(metadata) -> dict:
    """Return only the frozen identity/box/score keys required to re-stamp a refit artifact."""
    metadata = dict(metadata or {})
    return {
        key: metadata[key]
        for key in (
            "objective_version", "brief_hash", "score_hash", "score_identity",
            "score_identity_payload", "task_identity", "backend", "fidelity", "grid_hash",
            "dependency_hash", "mesh_hash", "bounds_hash", "bounds_identity_payload",
            "active_keys", "projection_version", "component_schema", "component_schema_hash",
        )
        if key in metadata
    }


def _artifact_candidates(artifact) -> tuple[MetricTrainingCandidate, ...]:
    """Reconstruct the frozen artifact's identity-stamped rows (no stored data is invented)."""
    metadata = dict(getattr(artifact, "metadata", {}) or {})
    active_keys = tuple(str(k) for k in (metadata.get("active_keys") or ()))
    if not active_keys:
        active_keys = tuple(str(k) for k in (artifact.feature_names or ()))
    stamps = {
        "objective_version": int(artifact.objective_version),
        "brief_hash": str(metadata.get("brief_hash") or ""),
        "score_hash": str(metadata.get("score_hash") or ""),
        "task_identity": str(metadata.get("task_identity") or ""),
        "backend": str(metadata.get("backend") or ""),
        "fidelity": str(metadata.get("fidelity") or ""),
        "grid_hash": str(metadata.get("grid_hash") or ""),
        "dependency_hash": str(metadata.get("dependency_hash") or ""),
        "mesh_hash": str(metadata.get("mesh_hash") or ""),
        "active_keys": active_keys,
        "bounds_hash": str(metadata.get("bounds_hash") or ""),
        "status": "ok",
        "component_names": tuple(artifact.component_names),
    }
    X = np.asarray(artifact.X, dtype=np.float64)
    J = np.asarray(artifact.J, dtype=np.float64).reshape(-1)
    Y = np.asarray(artifact.Y_components, dtype=np.float64)
    return tuple(
        MetricTrainingCandidate(
            observation_id=str(artifact.observation_ids[index]),
            x=np.array(X[index], dtype=np.float64, copy=True),
            J=float(J[index]),
            components=np.array(Y[index], dtype=np.float64, copy=True),
            **stamps,
        )
        for index in range(int(artifact.n))
    )


def build_refit_artifact(base_artifact, accepted) -> object:
    """Build a fresh, checksum-valid artifact over the frozen base rows + accepted screens."""
    selection = SelectionResult(
        status="ok",
        objective_version=int(base_artifact.objective_version),
        component_names=tuple(base_artifact.component_names),
        selected=tuple(_artifact_candidates(base_artifact)) + tuple(accepted),
        policy={},
        policy_hash="",
    )
    artifact = build_metric_training_artifact(
        selection,
        identity_metadata=_artifact_identity_metadata(base_artifact.metadata),
        feature_names=tuple(base_artifact.feature_names),
        require_identity=True,
    )
    if not getattr(artifact, "ok", False):
        raise MetricRefitError(
            "refit artifact refused: " + "; ".join(artifact.reasons or ("unknown",)))
    return artifact


def metric_candidate_from_result(result, *, artifact, seen_ids) -> MetricTrainingCandidate:
    """Validate one measured screen and turn it into a refit candidate or raise a typed refusal.

    ``seen_ids`` is the set of catalog ``physical_solve_id`` values already in the refit ledger
    (the frozen base cohort plus every accepted screen).  Only a genuinely new, called, parity
    exact, canonical v10/v11 screen with a bound dataset record and matching catalog identity can
    pass.
    """
    if not isinstance(result, dict):
        raise MetricRefitError("result_not_an_object")
    if result.get("kind") != "screen":
        raise MetricRefitError("not_a_screen")
    if result.get("call_status") != "called":
        raise MetricRefitError("not_a_new_backend_call")
    if result.get("outcome") != "success":
        raise MetricRefitError("not_a_successful_outcome")
    if result.get("eligible") is not True:
        raise MetricRefitError("not_eligible")
    if result.get("metric_refusal"):
        raise MetricRefitError("metric_refused:" + str(result["metric_refusal"]))

    record = result.get("metric_dataset_record")
    if not isinstance(record, dict):
        raise MetricRefitError("dataset_reference_missing")
    catalog_id = str(record.get("physical_solve_id") or "")
    if not _is_catalog_id(catalog_id):
        raise MetricRefitError("dataset_physical_solve_id_invalid")
    if catalog_id in seen_ids:
        raise MetricRefitError("duplicate_catalog_observation")
    for key in ("root", "shard", "row"):
        if key not in record:
            raise MetricRefitError("dataset_reference_incomplete")
    identity = record.get("identity")
    if not isinstance(identity, dict):
        raise MetricRefitError("dataset_identity_missing")

    metadata = dict(getattr(artifact, "metadata", {}) or {})
    for field in _IDENTITY_FIELDS:
        expected = str(metadata.get(field) or "")
        if not expected or str(identity.get(field) or "") != expected:
            raise MetricRefitError(f"metric_identity_mismatch:{field}")
    expected_keys = tuple(str(k) for k in (metadata.get("active_keys") or ()))
    if tuple(str(k) for k in (identity.get("active_keys") or ())) != expected_keys:
        raise MetricRefitError("metric_identity_mismatch:active_keys")

    try:
        version = int(str(result.get("objective_version")))
    except (TypeError, ValueError):
        raise MetricRefitError("objective_version_missing")
    if version != int(artifact.objective_version):
        raise MetricRefitError("objective_version_mismatch")
    try:
        j = float(str(result.get("observed_j")))
    except (TypeError, ValueError):
        raise MetricRefitError("observed_j_nonfinite")
    if not np.isfinite(j):
        raise MetricRefitError("observed_j_nonfinite")
    components = np.asarray(result.get("components"), dtype=np.float64).reshape(-1)
    if components.size != len(tuple(artifact.component_names)):
        raise MetricRefitError("component_count_mismatch")
    ok, reconstructed, why = validate_components(
        version, components, j, names=tuple(artifact.component_names))
    if not ok or abs(float(reconstructed) - j) > parity_tolerance(j):
        raise MetricRefitError("component_parity_failed:" + "; ".join(why))

    try:
        x = np.asarray(result.get("x"), dtype=np.float64).reshape(-1)
    except (TypeError, ValueError):
        raise MetricRefitError("projected_design_invalid")
    if x.size != int(artifact.d) or not np.all(np.isfinite(x)):
        raise MetricRefitError("projected_design_invalid")
    if np.any((x < 0.0) | (x > 1.0)):
        raise MetricRefitError("projected_design_out_of_box")

    solve_id = result.get("solve_id")
    if not isinstance(solve_id, str) or not solve_id:
        raise MetricRefitError("solve_identity_missing")
    for field in ("physical_id", "score_id", "metric_id"):
        if not isinstance(result.get(field), str) or not result[field]:
            raise MetricRefitError(f"replay_identity_missing:{field}")
    design_hash = result.get("design_hash")
    if not isinstance(design_hash, str) or not design_hash:
        raise MetricRefitError("design_identity_missing")

    stamps = {
        "brief_hash": str(metadata.get("brief_hash") or ""),
        "score_hash": str(metadata.get("score_hash") or ""),
        "task_identity": str(metadata.get("task_identity") or ""),
        "backend": str(metadata.get("backend") or ""),
        "fidelity": str(metadata.get("fidelity") or ""),
        "grid_hash": str(metadata.get("grid_hash") or ""),
        "dependency_hash": str(metadata.get("dependency_hash") or ""),
        "mesh_hash": str(metadata.get("mesh_hash") or ""),
        "active_keys": expected_keys,
        "bounds_hash": str(metadata.get("bounds_hash") or ""),
    }
    return MetricTrainingCandidate(
        observation_id=catalog_id,
        physical_id=catalog_id,
        solve_id=solve_id,
        design_hash=design_hash,
        geometry_hash=str(result.get("geometry_hash") or design_hash),
        x=np.array(x, dtype=np.float64, copy=True),
        J=j,
        objective_version=version,
        status="ok",
        components=np.array(components, dtype=np.float64, copy=True),
        component_names=tuple(artifact.component_names),
        cd_status=result.get("cd_status"),
        quality_flags=tuple(result.get("quality_flags") or ()),
        source={
            "attempt_id": result.get("attempt_id"),
            "dataset": {k: record.get(k) for k in ("root", "shard", "row")},
        },
        **stamps,
    )


class MetricRefitLedger:
    """Content-addressed refit snapshots plus an append-only pointer, per package."""

    def __init__(self, service, study_id, package_id, *, base_artifact, base_manifest,
                 base_artifact_sha256, seed, refit_every=REAL_METRIC_REFIT_EVERY):
        if int(refit_every) != REAL_METRIC_REFIT_EVERY:
            raise MetricRefitError("refit_every must be 4 for the metric canary")
        self.service = service
        self.store = service.store
        self.study_id = study_id
        self.package_id = package_id
        self.base_artifact = base_artifact
        self.base_manifest = dict(base_manifest or {})
        self.base_artifact_sha256 = str(base_artifact_sha256 or "")
        self.seed = int(seed)
        self.refit_every = int(refit_every)
        self._snapshot = None
        self._generation = 0
        self._pointer = None
        self._load_current()

    # -- state ---------------------------------------------------------------
    @property
    def generation(self):
        return self._generation

    @property
    def current_artifact(self):
        return self._snapshot["artifact"] if self._snapshot is not None else self.base_artifact

    @property
    def pointer(self):
        return dict(self._pointer) if self._pointer is not None else None

    def _latest_pointer(self):
        with self.store.connect() as conn:
            rows = conn.execute(
                "SELECT seq,payload_json FROM events WHERE study_id=? AND kind=? ORDER BY seq",
                (self.study_id, METRIC_REFIT_POINTER_EVENT)).fetchall()
        if not rows:
            return None
        pointer = None
        seen = set()
        for row in rows:
            try:
                item = json.loads(row["payload_json"])
            except (TypeError, ValueError) as exc:
                raise MetricRefitError(f"metric refit pointer is corrupt: {exc}") from exc
            if not isinstance(item, dict) or item.get("format") != METRIC_REFIT_POINTER_FORMAT:
                raise MetricRefitError("metric refit pointer has an unknown format")
            generation = item.get("generation")
            if type(generation) is not int or generation < 1:
                raise MetricRefitError("metric refit pointer generation is invalid")
            if generation in seen:
                raise MetricRefitError(f"duplicate metric refit pointer generation {generation}")
            seen.add(generation)
            pointer = item
        if pointer is None:
            return None
        if sorted(seen) != list(range(1, max(seen) + 1)):
            raise MetricRefitError("metric refit pointer history has a gap")
        return pointer

    def _load_current(self):
        pointer = self._latest_pointer()
        if pointer is None:
            self._pointer = None
            self._generation = 0
            self._snapshot = None
            return
        snapshot_sha = pointer.get("snapshot_sha256")
        if not _is_hex64(snapshot_sha):
            raise MetricRefitError("metric refit pointer has no snapshot digest")
        try:
            snapshot = json.loads(self.store.read_artifact(snapshot_sha))
        except (Unavailable, ValueError, TypeError) as exc:
            raise MetricRefitError(f"metric refit snapshot is unreadable: {exc}") from exc
        if not isinstance(snapshot, dict) or \
                snapshot.get("format") != METRIC_REFIT_SNAPSHOT_FORMAT:
            raise MetricRefitError("metric refit snapshot has an unknown format")
        for key in ("generation", "artifact_bytes_sha256", "artifact_checksum",
                    "accepted_ids", "journal_attempt_ids", "model_seed", "proposal_state"):
            if key not in snapshot:
                raise MetricRefitError(f"metric refit snapshot is missing {key}")
        if snapshot.get("generation") != pointer.get("generation"):
            raise MetricRefitError("metric refit snapshot/pointer generation mismatch")
        if snapshot.get("artifact_bytes_sha256") != pointer.get("artifact_bytes_sha256"):
            raise MetricRefitError("metric refit snapshot/pointer artifact mismatch")
        if snapshot.get("accepted_ids") != pointer.get("accepted_ids"):
            raise MetricRefitError("metric refit snapshot/pointer accepted-id mismatch")
        if digest(snapshot.get("proposal_state")) != pointer.get("proposal_state_sha256"):
            raise MetricRefitError("metric refit proposal-state digest mismatch")
        if len(snapshot["accepted_ids"]) != int(snapshot["generation"]) * self.refit_every:
            raise MetricRefitError("metric refit snapshot accepted-id count is inconsistent")
        artifact = self._load_artifact(
            snapshot["artifact_bytes_sha256"], snapshot["artifact_checksum"])
        self._snapshot = {"record": snapshot, "artifact": artifact, "sha256": snapshot_sha}
        self._generation = int(snapshot["generation"])
        self._pointer = pointer

    def _load_artifact(self, artifact_sha, checksum):
        if not _is_hex64(artifact_sha):
            raise MetricRefitError("metric refit artifact digest is invalid")
        try:
            blob = self.store.read_artifact(artifact_sha)
        except Unavailable as exc:
            raise MetricRefitError(f"metric refit artifact is missing: {exc}") from exc
        artifact, check = metric_artifact.artifact_from_bytes(
            blob, expected_checksum=checksum)
        if artifact is None or not getattr(check, "ok", False):
            raise MetricRefitError(
                "metric refit artifact is invalid: "
                + str(getattr(check, "detail", None) or getattr(check, "reason", None)))
        validation = metric_artifact.validate_metric_training_artifact(
            artifact,
            expected_bounds_hash=(self.base_manifest.get("bounds") or {}).get("hash"),
            expected_score=(self.base_manifest.get("score") or {}).get("payload"),
            expected_task=self.base_manifest.get("task") or {})
        if not getattr(validation, "ok", False):
            raise MetricRefitError(
                "metric refit artifact identity validation failed: "
                + str(getattr(validation, "detail", None) or getattr(validation, "reason", None)))
        return artifact

    # -- advance -------------------------------------------------------------
    def _publish_snapshot(self, artifact, accepted_ids, journal_attempt_ids, proposal_state,
                          model_hash, target):
        artifact_blob = metric_artifact.artifact_bytes(artifact)
        artifact_sha = self.store.publish(artifact_blob)
        if digest_bytes(artifact_blob) != artifact_sha:
            raise MetricRefitError("refit artifact publication digest mismatch")
        record = {
            "format": METRIC_REFIT_SNAPSHOT_FORMAT,
            "kind": METRIC_REFIT_SNAPSHOT_KIND,
            "schema_version": METRIC_REFIT_SNAPSHOT_SCHEMA_VERSION,
            "policy": METRIC_POLICY,
            "study_id": self.study_id,
            "package_id": self.package_id,
            "created_utc": _utc_now(),
            "generation": int(target),
            "refit_every": self.refit_every,
            "base_artifact_bytes_sha256": self.base_artifact_sha256,
            "artifact_bytes_sha256": artifact_sha,
            "artifact_checksum": str(artifact.checksum),
            "accepted_ids": list(accepted_ids),
            "journal_attempt_ids": [None if v is None else str(v)
                                    for v in journal_attempt_ids],
            "journal_observation_count": len(journal_attempt_ids),
            "model_seed": self.seed,
            "model_hash": str(model_hash),
            "proposal_state": proposal_state,
            "proposal_state_sha256": digest(proposal_state),
            "objective_version": int(artifact.objective_version),
            "component_names": list(artifact.component_names),
            "n": int(artifact.n),
            "d": int(artifact.d),
            "m": int(artifact.m),
            "bounds_hash": (self.base_manifest.get("bounds") or {}).get("hash"),
            "score_identity": (self.base_manifest.get("score") or {}).get("identity"),
            "task": dict(self.base_manifest.get("task") or {}),
        }
        snapshot_blob = canonical(record).encode("utf-8")
        snapshot_sha = self.store.publish(snapshot_blob)
        if digest_bytes(snapshot_blob) != snapshot_sha:
            raise MetricRefitError("refit snapshot publication digest mismatch")
        return record, snapshot_sha

    def advance(self, artifact, accepted_ids, journal_attempt_ids, proposal_state, *,
                model_hash, target=None):
        """Publish the snapshot, then append the pointer event.  Never writes a stale pointer."""
        target = self._generation + 1 if target is None else int(target)
        if target <= self._generation:
            raise MetricRefitError("metric refit pointer cannot move backwards")
        if len(accepted_ids) != target * self.refit_every:
            raise MetricRefitError("metric refit accepted-id count does not match the generation")
        record, snapshot_sha = self._publish_snapshot(
            artifact, accepted_ids, journal_attempt_ids, proposal_state, model_hash, target)
        pointer = {
            "format": METRIC_REFIT_POINTER_FORMAT,
            "kind": METRIC_REFIT_SNAPSHOT_KIND,
            "generation": target,
            "refit_every": self.refit_every,
            "snapshot_sha256": snapshot_sha,
            "artifact_bytes_sha256": record["artifact_bytes_sha256"],
            "artifact_checksum": record["artifact_checksum"],
            "accepted_ids": list(accepted_ids),
            "journal_attempt_ids": list(record["journal_attempt_ids"]),
            "model_seed": self.seed,
            "model_hash": str(model_hash),
            "proposal_state_sha256": record["proposal_state_sha256"],
            "created_utc": _utc_now(),
        }
        self.service.append_event(
            self.study_id, METRIC_REFIT_POINTER_EVENT, pointer,
            f"metric_refit_pointer:{self.package_id}:{target}")
        self._pointer = pointer
        self._generation = target
        self._snapshot = {"record": record, "artifact": artifact, "sha256": snapshot_sha}
        return {"generation": target, "snapshot_sha256": snapshot_sha,
                "artifact_bytes_sha256": record["artifact_bytes_sha256"],
                "artifact_checksum": record["artifact_checksum"],
                "accepted_ids": list(accepted_ids), "model_hash": str(model_hash),
                "model_seed": self.seed}

    def refit(self, accepted, attempt_ids, proposal_state):
        """Advance to ``len(accepted)//4``; fail closed on an ambiguous pointer/prefix.

        Returns the new snapshot record, or ``None`` when no new full batch exists.  A failed
        fit raises :class:`MetricRefitError` without publishing a snapshot or moving the pointer.
        """
        target = len(accepted) // self.refit_every
        ordered_ids = [c.observation_id for c in accepted]
        if self._pointer is not None:
            pinned = list(self._pointer.get("accepted_ids") or ())
            if pinned != ordered_ids[:len(pinned)]:
                raise MetricRefitError(
                    "metric refit pointer accepted IDs are not a prefix of the journal replay")
        if target <= self._generation:
            return None
        cut = target * self.refit_every
        artifact = build_refit_artifact(self.base_artifact, accepted[:cut])
        from hornlab_search.bo.metric_model import fit_metric_model
        fitted = fit_metric_model(artifact, seed=self.seed)
        if getattr(fitted, "status", None) != "ok":
            raise MetricRefitError(
                "metric refit fit failed: "
                + str(getattr(fitted, "reason", None) or "unknown")
                + (f": {fitted.detail}" if getattr(fitted, "detail", None) else ""))
        return self.advance(
            artifact, ordered_ids[:cut], list(attempt_ids)[:cut], proposal_state,
            model_hash=getattr(fitted, "model_hash", ""), target=target)


def digest_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


# --------------------------------------------------------------------------- real package gate


def verify_real_metric_package(service, package, *, root, cfg=None):
    """Typed execution gate for the explicit ``real_metric_v1`` package contract.

    Delegates the frozen body/approval-record/pinned-file checks to the packaging lane's
    :func:`verify_real_metric_package_files`, then independently re-reads the study's immutable
    artifacts so a stale or hand-edited package can never execute against different training data.
    Every failure is a typed refusal; there is no fallback to scalar or synthetic execution.
    """
    from . import package as package_mod
    from .metric_study import metric_bindings

    try:
        if not isinstance(package, dict):
            raise MetricRefitError("invalid_package")
        metric = package.get("metric")
        if not isinstance(metric, dict):
            raise MetricRefitError("real metric package has no metric block")
        if metric.get("provenance_mode") != package_mod.REAL_METRIC:
            raise MetricRefitError(
                f"metric provenance mode is {metric.get('provenance_mode')!r}")
        if metric.get("synthetic") is not False or metric.get("real_solver_allowed") is not True:
            raise MetricRefitError("real metric package must be non-synthetic and solver-authorized")
        if package.get("lane") != "gpu":
            raise MetricRefitError("real metric canary requires the gpu lane")
        if cfg is not None and getattr(getattr(cfg, "solve", None), "backend", None) != "beat_cuda":
            raise MetricRefitError("real metric canary requires the beat_cuda backend")

        # The approvals record is repo-relative by contract.  An execution project root may be
        # outside the repository, so it is only used as the base when the record actually exists
        # there (contained test roots); otherwise the repository root is the base.
        from pathlib import Path as _Path
        record = (metric.get("approvals") or {}).get("record")
        record_base = None
        if isinstance(record, str) and record and not _Path(record).is_absolute() \
                and root is not None:
            candidate = _Path(root).resolve() / record
            if candidate.is_file():
                record_base = root
        files = package_mod.verify_real_metric_package_files(package, root=record_base)
        approval_status = (files.get("approvals") or {}).get("status")
        if approval_status not in package_mod.METRIC_EXECUTABLE_APPROVAL_STATUSES:
            raise MetricRefitError(
                f"metric approvals status {approval_status!r} is not executable "
                f"(parent release still held: {package_mod.METRIC_APPROVAL_STATUSES})")

        if service is None:
            raise MetricRefitError("the study service is required to revalidate real metric pins")
        study_id = package.get("study_id")
        revision = package.get("spec_revision")
        budget = package.get("budget") or {}
        approvals_block = metric.get("approvals")
        if not isinstance(approvals_block, dict):
            raise MetricRefitError("real metric approvals block is missing")
        approvals = package_mod.load_metric_approvals(
            approvals_block.get("record"), root=record_base)["payload"]
        if approvals.get("task_identity") != approvals_block.get("task_identity"):
            raise MetricRefitError("metric approvals record task_identity differs from the package")
        if approvals.get("artifact_sha256") != approvals_block.get("artifact_sha256"):
            raise MetricRefitError("metric approvals record artifact_sha256 differs from the package")
        for key in ("screen_cap", "verify_cap"):
            if approvals.get(key) != approvals_block.get(key):
                raise MetricRefitError(f"metric approvals record {key} differs from the package")
        if approvals.get("refit_every") != REAL_METRIC_REFIT_EVERY:
            raise MetricRefitError("metric approvals refit_every must be 4")
        if approvals_block.get("refit_every") != REAL_METRIC_REFIT_EVERY:
            raise MetricRefitError("real metric package approvals refit_every must be 4")
        if approvals_block.get("screen_cap") != budget.get("screen_calls"):
            raise MetricRefitError("real metric approvals screen_cap must equal the screen budget")
        if approvals_block.get("verify_cap") != budget.get("verify_calls"):
            raise MetricRefitError("real metric approvals verify_cap must equal the verify budget")

        metas = {
            kind: service.get_artifact_metadata(study_id, kind, revision=revision)
            for kind in (METRIC_TRAINING_KIND, METRIC_TRAINING_MANIFEST_KIND, "model",
                         "proposal", "pool")
        }
        for kind, meta in metas.items():
            if meta.get("status") != "available":
                raise MetricRefitError(f"{kind} artifact is unavailable")
        manifest = json.loads(
            service.store.read_artifact(metas[METRIC_TRAINING_MANIFEST_KIND]["sha256"]))
        if manifest.get("synthetic") is not False:
            raise MetricRefitError(
                "real metric execution requires real (non-synthetic) training data")
        if int(manifest.get("objective_version", -1)) not in (10, 11):
            raise MetricRefitError("real metric training objective version must be v10/v11")
        task = manifest.get("task") or {}
        score = (manifest.get("score") or {}).get("payload") or {}
        expected_pins = {
            "training_artifact_sha256": manifest.get("artifact_bytes_sha256"),
            "training_manifest_sha256": metas[METRIC_TRAINING_MANIFEST_KIND]["sha256"],
            "proposal_sha256": metas["proposal"]["sha256"],
            "model_sha256": metas["model"]["sha256"],
        }
        for key, expected in expected_pins.items():
            value = metric.get(key)
            if not _is_hex64(value):
                raise MetricRefitError(f"real metric package pin {key} is invalid")
            if value != expected:
                raise MetricRefitError(f"real metric package pin {key} does not match the study")
        if metric.get("training_checksum") != manifest.get("checksum"):
            raise MetricRefitError(
                "real metric package training_checksum does not match the study manifest")
        if approvals_block.get("artifact_sha256") != manifest.get("checksum"):
            raise MetricRefitError(
                "metric approvals artifact_sha256 does not match the training checksum")
        if approvals_block.get("task_identity") != task.get("task_identity"):
            raise MetricRefitError("metric approvals task_identity does not match the metric manifest")
        if metric.get("task_identity") != task.get("task_identity"):
            raise MetricRefitError("real metric package task_identity does not match the manifest")

        identity_fields = ("task_identity", "backend", "fidelity", "grid_hash",
                           "dependency_hash", "mesh_hash")
        app_identity = approvals.get("identity") or {}
        for field in identity_fields:
            if app_identity.get(field) != task.get(field):
                raise MetricRefitError(
                    f"metric approvals identity {field!r} differs from the metric artifact")
        bis_identity = metric.get("identity") or {}
        for field in identity_fields:
            if bis_identity.get(field) != task.get(field):
                raise MetricRefitError(
                    f"real metric package identity {field!r} differs from the metric artifact")
        for field in ("brief_hash", "score_hash"):
            if app_identity.get(field) not in (None, score.get(field)):
                raise MetricRefitError(
                    f"metric approvals identity {field!r} differs from the metric artifact")
            if bis_identity.get(field) not in (None, score.get(field)):
                raise MetricRefitError(
                    f"real metric package identity {field!r} differs from the metric artifact")

        source = metric.get("source_provenance")
        source_sha = metric.get("source_provenance_sha256")
        intake = manifest.get("offline_intake")
        if not isinstance(source, dict) or not isinstance(intake, dict) or source != intake:
            raise MetricRefitError(
                "real metric source provenance does not match the frozen offline intake")
        if not _is_hex64(source_sha) or digest(source) != source_sha:
            raise MetricRefitError("real metric source provenance hash is invalid")

        bindings = metric_bindings(service, study_id)
        if bindings.get("status") != "ok" or bindings.get("synthetic") is not False:
            raise MetricRefitError(
                "metric artifact binding is not a valid measured artifact: "
                + str(bindings.get("detail")))
        pool_payload = json.loads(service.store.read_artifact(metas["pool"]["sha256"]))
        if not pool_payload.get("candidates"):
            raise MetricRefitError("real metric candidate pool is empty")
        return {
            "status": "ok", "reason": "real_metric_v1", "detail": None,
            "real_solver_allowed": True,
            "approval_status": approval_status,
            "task_identity": task.get("task_identity"),
            "artifact_sha256": manifest.get("checksum"),
            "training_artifact_sha256": manifest.get("artifact_bytes_sha256"),
            "training_checksum": manifest.get("checksum"),
            "refit_every": REAL_METRIC_REFIT_EVERY,
            "screen_cap": approvals_block.get("screen_cap"),
            "verify_cap": approvals_block.get("verify_cap"),
            "pinned_files": files.get("pinned_files"),
        }
    except MetricRefitError as exc:
        return {"status": "refused", "reason": "real_metric_package_invalid",
                "detail": str(exc), "real_solver_allowed": False}
    except (StudyError, Unavailable, KeyError, ValueError, TypeError, OSError) as exc:
        return {"status": "refused", "reason": "real_metric_package_invalid",
                "detail": f"{type(exc).__name__}: {exc}", "real_solver_allowed": False}
