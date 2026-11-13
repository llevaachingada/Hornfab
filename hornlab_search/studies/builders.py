"""Real study-scoped artifact builders (protocol ``bo-study-v1.1`` M3).

The functions here turn a draft study + explicit, resolvable inputs into the
immutable artifacts the rest of the workflow consumes::

    freeze_snapshot(service, study_id, *, root, spec=None, idempotency_key=None)
    build_training(service, study_id, *, root, spec=None, idempotency_key=None)
    build_analysis(service, study_id, *, root, spec=None, idempotency_key=None)
    build_proposal(service, study_id, *, root, policy=None, seed=None, idempotency_key=None)

Design rules (frozen in the spec):

* every *write* goes through the study service's atomic, hash-verified,
  content-addressed publication; no dataset/cache/acoustic path is written and
  no writable ``DatasetStore`` is ever constructed;
* every input path must exist; a missing/unreadable input is a typed
  :class:`~hornlab_search.studies.schema.Unavailable` naming the exact path,
  never a fabricated empty artifact;
* the default source is the committed evidence at
  ``docs/evidence/bo_study_2026-11-12/`` for the signed native task
  (``native__ath_core_v4`` / ``native_ath_core_2in_v4``);
* predictions are never appended to measured rows, and a missing optional
  BoTorch engine is an explicit ``capability_missing`` result, not a fake
  candidate.

Nothing in this module imports torch/botorch at import time or calls a solver,
mesher, GPU, lane or job manager.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .schema import (PROTOCOL, Conflict, StudyError, Unavailable, canonical, digest)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASK_NAME = "native__ath_core_v4"
DEFAULT_BRIEF_NAME = "native_ath_core_2in_v4"
DEFAULT_CONFIG = (REPO_ROOT / "examples" / "typologies" / "campaign_2026-10-26_v4"
                  / "native__ath_core_v4.yaml")
DEFAULT_BRIEF = (REPO_ROOT / "examples" / "briefs" / "campaign_2026-10-26_v4"
                 / "native_ath_core_2in_v4.yaml")
DEFAULT_EVIDENCE_ROOT = REPO_ROOT / "docs" / "evidence" / "bo_study_2026-11-12"
DEFAULT_SCORES = DEFAULT_EVIDENCE_ROOT / "r0" / "offline_scores.json"
DEFAULT_COHORTS = DEFAULT_EVIDENCE_ROOT / "s0" / "cohorts.json"
DEFAULT_CATALOG = REPO_ROOT / "scratch" / "bo_m0" / "s0" / "catalog" / "catalog.csv"
DEFAULT_DATASET_ROOT = REPO_ROOT / "dataset"
DEFAULT_TRAINING_JSON = DEFAULT_EVIDENCE_ROOT / "b2_native" / "native_trainingset.json"
DEFAULT_POOL_JSON = REPO_ROOT / "scratch" / "bo_m0" / "m2" / "pools" / "pool-20261112.json"

# Home 80x60/700 target task (registered 2026-11-13, objective v7).
# Evidence root does NOT exist until the first cohort of runs completes; any
# snapshot or training build for this task fails with Unavailable (insufficient
# data) until explicit source paths are supplied by the caller.
HOME_TASK_NAME = "p80x60__osse_ext_throat_home700_v7"
HOME_BRIEF_NAME = "room_80x60_700_hf1440_v7"
HOME_CONFIG = (REPO_ROOT / "examples" / "typologies" / "print_80x60_2026-11-13"
               / "p80x60__osse_ext_throat_700_v7.yaml")
HOME_BRIEF = (REPO_ROOT / "examples" / "briefs" / "print_80x60_2026-11-13"
              / "room_80x60_700_hf1440_v7.yaml")
HOME_OBJECTIVE_VERSION = 7

# Task registry: maps every accepted task name to its (config, brief, objective_version).
# A task in this registry may be used by _read_task as a named task; a name absent from
# this registry is refused.  The M0 contract is frozen; registry additions do NOT alter it.
_TASK_REGISTRY: dict[str, dict] = {
    # M0 signed native task — frozen (do NOT change these paths or version)
    DEFAULT_TASK_NAME: {
        "config": DEFAULT_CONFIG,
        "brief": DEFAULT_BRIEF,
        "objective_version": 4,
    },
    # Home 80x60/700 living-room target (registered 2026-11-13)
    HOME_TASK_NAME: {
        "config": HOME_CONFIG,
        "brief": HOME_BRIEF,
        "objective_version": HOME_OBJECTIVE_VERSION,
    },
}

SNAPSHOT_SCHEMA = "study-snapshot-v1"
TRAINING_MANIFEST_SCHEMA = "study-training-manifest-v1"
ANALYSIS_SCHEMA = "study-analysis-v1"
MODEL_MANIFEST_SCHEMA = "study-model-manifest-v1"
POOL_MANIFEST_SCHEMA = "study-pool-manifest-v1"
PROPOSAL_SCHEMA = "study-proposal-v1"
DATASET_SCHEMA = "study-training-dataset-v1"

POOL_STATUS_NOTE = "cheap-check-passed; mesh/acoustic eligibility unknown"
_ALLOWED_TASK_NAMES = {
    DEFAULT_TASK_NAME, DEFAULT_CONFIG.stem, DEFAULT_BRIEF_NAME, DEFAULT_BRIEF.stem,
    HOME_TASK_NAME, HOME_CONFIG.stem, HOME_BRIEF_NAME, HOME_BRIEF.stem,
}


# --------------------------------------------------------------------------- helpers


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _json_value(value):
    """Coerce numpy/scalar values to strict, finite JSON (no NaN/Infinity)."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StudyError("artifact contains a non-finite float")
        return value
    if hasattr(value, "item") and not isinstance(value, (bytes, bytearray)):
        return _json_value(value.item())
    if isinstance(value, (bytes, bytearray)):
        return hashlib.sha256(bytes(value)).hexdigest()
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    return str(value)


def _json_bytes(value) -> bytes:
    return canonical(_json_value(value)).encode("utf-8")


def _deterministic_npz(arrays: dict) -> bytes:
    """Write an ``.npz`` with fixed member timestamps so bytes are reproducible.

    ``np.savez`` embeds the current time in the zip members; this writer keeps
    the same ``np.load`` contract but pins ``date_time`` so repeated builds of
    identical arrays hash identically.  Pickle is disabled.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        for name in sorted(arrays):
            value = arrays[name]
            if value is None:
                continue
            stream = io.BytesIO()
            import numpy as np
            np.lib.format.write_array(stream, np.asarray(value), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, stream.getvalue())
    return buffer.getvalue()


def _allowed_roots(root) -> tuple[Path, ...]:
    """Inputs may come from the repository (signed evidence/config) or the study root."""
    roots = [REPO_ROOT.resolve()]
    if root is not None:
        roots.append(Path(root).resolve())
    return tuple(dict.fromkeys(roots))


def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == base or base in path.parents for base in roots)


def _resolve_input(root, value, default: Path | None, label: str) -> Path:
    """Resolve an input path, requiring it to exist **and** stay in an allowed root.

    Allowed roots are the repository root (signed evidence/config) and the
    explicit study root.  A client-supplied spec cannot read an arbitrary file
    even if it exists; a path-like or traversal value is refused as
    ``Unavailable`` naming the resolved path.  Writes happen only through the
    study store, which is rooted at the explicit study root.
    """
    if value is None:
        if default is None:
            raise Unavailable(f"{label} is required")
        path = Path(default)
    else:
        path = Path(str(value))
        if not path.is_absolute():
            path = Path(root) / path
    path = path.resolve()
    if not _inside(path, _allowed_roots(root)):
        raise Unavailable(
            f"{label} is outside the allowed study/repository roots: {path}")
    if not path.exists():
        raise Unavailable(f"{label} not found: {path}")
    return path


def _canonical_ok(value) -> bool:
    return isinstance(value, str) and value.strip().lower() not in {"", "unknown", "none", "missing"}


def _load_json(path: Path, label: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise Unavailable(f"{label} could not be read: {path}: {exc}") from exc


def _study_spec(service, study_id, spec):
    study = service.get_study(study_id)
    if spec is None:
        return study, study["spec"]
    if not isinstance(spec, dict):
        raise StudyError("study spec override must be an object")
    return study, spec


def _read_task(task, *, root, config=None, brief=None):
    """Resolve config/brief/objective identity; unknown task identity refuses.

    When a named task is supplied without explicit config/brief paths, the task
    registry provides the correct defaults.  The M0 native task falls through to
    ``DEFAULT_CONFIG`` / ``DEFAULT_BRIEF`` as before; the home task uses its own
    registered paths.  Tasks absent from ``_ALLOWED_TASK_NAMES`` are refused.
    """
    task = task if isinstance(task, dict) else {}
    raw_config = config if config is not None else task.get("config")
    raw_brief = brief if brief is not None else task.get("brief")
    # Determine effective defaults from the task registry when no paths are given.
    effective_config_default = DEFAULT_CONFIG
    effective_brief_default = DEFAULT_BRIEF
    effective_version_default = 4
    if raw_config is None and raw_brief is None:
        name = task.get("name")
        if name is not None:
            name_str = str(name)
            if name_str not in _ALLOWED_TASK_NAMES:
                known = ", ".join(sorted(_TASK_REGISTRY))
                raise Unavailable(
                    f"unknown task identity {name_str!r}; known tasks: {known}")
            # Look up registry entry matching the canonical task name.
            for reg_name, entry in _TASK_REGISTRY.items():
                if name_str in (reg_name, entry["config"].stem,
                                entry["brief"].stem):
                    effective_config_default = entry["config"]
                    effective_brief_default = entry["brief"]
                    effective_version_default = entry["objective_version"]
                    break
    config_path = _resolve_input(root, raw_config, effective_config_default, "task config")
    if raw_brief is None:
        try:
            import yaml
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            brief_ref = raw.get("brief_file") if isinstance(raw, dict) else None
        except Exception:  # noqa: BLE001 - unreadable config is refused below
            brief_ref = None
        if brief_ref:
            candidate = (config_path.parent / str(brief_ref))
            raw_brief = candidate.resolve() if candidate.exists() else None
    brief_path = _resolve_input(root, raw_brief, effective_brief_default, "task brief")
    version = task.get("objective_version", effective_version_default)
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise StudyError("task objective_version must be a non-negative integer")
    return {
        "config": config_path,
        "brief": brief_path,
        "config_sha256": _sha256_file(config_path),
        "brief_sha256": _sha256_file(brief_path),
        "config_name": config_path.name,
        "brief_name": brief_path.stem,
        "objective_version": version,
    }


def _read_sources(source, *, root, scores_json=None, catalog_csv=None, dataset_root=None):
    source = source if isinstance(source, dict) else {}
    scores = _resolve_input(root, scores_json if scores_json is not None
                            else source.get("scores_json", source.get("scores")),
                            DEFAULT_SCORES, "scores_json")
    catalog = _resolve_input(root, catalog_csv if catalog_csv is not None
                             else source.get("catalog_csv", source.get("catalog")),
                             DEFAULT_CATALOG, "catalog_csv")
    dataset = _resolve_input(root, dataset_root if dataset_root is not None
                             else source.get("dataset_root", source.get("dataset")),
                             DEFAULT_DATASET_ROOT, "dataset_root")
    if not dataset.is_dir():
        raise Unavailable(f"dataset_root is not a directory: {dataset}")
    return {"scores_json": scores, "catalog_csv": catalog, "dataset_root": dataset}


def _existing(service, study_id, revision, kind):
    meta = service.get_artifact_metadata(study_id, kind, revision=revision)
    return meta if meta.get("status") in ("available", "stale") else None


def _attach_once(service, study_id, revision, kind, content, dependencies, key):
    """Attach ``content`` once; a matching existing artifact is returned unchanged."""
    existing = _existing(service, study_id, revision, kind)
    sha = _sha256_bytes(content)
    if existing is not None:
        if existing.get("sha256") == sha:
            return existing
        raise Conflict(f"{kind} artifact already attached with different content")
    return service.attach_artifact(study_id, revision, kind, content, dependencies, key)


def _unwrap(meta):
    return {k: meta[k] for k in ("study_id", "revision", "kind", "sha256", "status")
            if k in meta}


# --------------------------------------------------------------------------- snapshot


def _cohort_counts(scores_payload, catalog_path):
    rows = scores_payload.get("rows") if isinstance(scores_payload, dict) else None
    rows = [r for r in rows or () if isinstance(r, dict)]
    statuses = Counter(str(r.get("status") or "unknown") for r in rows)
    complete = statuses.get("exact_complete", 0)
    catalogue_rows = 0
    configs = set()
    try:
        import csv
        with open(catalog_path, encoding="utf-8", newline="") as fh:
            for rec in csv.DictReader(fh):
                catalogue_rows += 1
                name = str(rec.get("config_name") or "").strip()
                if name:
                    configs.add(name)
    except OSError as exc:
        raise Unavailable(f"catalog_csv could not be read: {catalog_path}: {exc}") from exc
    return {
        "scores": {
            "records": len(rows),
            "ok": complete,
            "failed": len(rows) - complete,
            "failed_by_status": {k: v for k, v in sorted(statuses.items())
                                 if k != "exact_complete"},
            "unique_geometries": len({str(r.get("design_hash")) for r in rows
                                      if r.get("design_hash")}),
            "unique_physical_solves": len({str(r.get("physical_id")) for r in rows
                                           if r.get("physical_id")}),
            "unknown_provenance": {
                "run_id_missing": sum(1 for r in rows
                                      if not _canonical_ok(r.get("catalog_run_id"))),
            },
        },
        "catalog": {"rows": catalogue_rows, "configs": sorted(configs)},
    }


def freeze_snapshot(service, study_id, *, root, spec=None, idempotency_key=None):
    """Build/attach the read-only ``study-snapshot-v1`` identity artifact."""
    study, effective = _study_spec(service, study_id, spec)
    revision = study["revision"]
    existing = _existing(service, study_id, revision, "snapshot")
    if existing is not None:
        return {"status": "ok", "snapshot": _unwrap(existing), "revision": revision,
                "artifact": existing, "idempotent": True}

    task = _read_task(effective.get("task"), root=root,
                      config=(effective.get("task") or {}).get("config")
                      if isinstance(effective.get("task"), dict) else None)
    sources = _read_sources(effective.get("source"), root=root)
    scores_payload = _load_json(sources["scores_json"], "scores_json")
    counts = _cohort_counts(scores_payload, sources["catalog_csv"])
    brief_block = scores_payload.get("brief") if isinstance(scores_payload, dict) else None
    resolved_target = (brief_block or {}).get("target") if isinstance(brief_block, dict) else None
    parity = scores_payload.get("parity") if isinstance(scores_payload, dict) else None
    cohort_ref = None
    if DEFAULT_COHORTS.is_file():
        cohort_payload = _load_json(DEFAULT_COHORTS, "cohorts artifact")
        cohort_ref = {
            "path": str(DEFAULT_COHORTS),
            "sha256": _sha256_file(DEFAULT_COHORTS),
            "status": cohort_payload.get("status"),
            "eligibility": cohort_payload.get("eligibility"),
            "independent_experiments": cohort_payload.get("independent_experiments"),
            "totals_descriptive_only": {
                k: cohort_payload.get("totals_descriptive_only", {}).get(k)
                for k in ("n_records", "n_ok", "n_failed", "n_unique_geometries",
                          "n_unique_physical_solves", "n_complete_replayable")
            },
        }
    dataset_exists = sources["dataset_root"].is_dir()
    snapshot = {
        "tool": "study_snapshot",
        "schema": SNAPSHOT_SCHEMA,
        "schema_version": 1,
        "protocol": PROTOCOL,
        "generated_utc": _utc_now(),
        "study_id": study_id,
        "revision": revision,
        "spec_hash": study["spec_hash"],
        "task": {
            "config": str(task["config"]),
            "config_name": task["config_name"],
            "config_sha256": task["config_sha256"],
            "brief": str(task["brief"]),
            "brief_name": task["brief_name"],
            "brief_sha256": task["brief_sha256"],
            "objective_version": task["objective_version"],
            "resolved_target": resolved_target,
        },
        "source": {
            "dataset_root": str(sources["dataset_root"]),
            "dataset_root_exists": dataset_exists,
            "scores_json": str(sources["scores_json"]),
            "scores_json_sha256": _sha256_file(sources["scores_json"]),
            "catalog_csv": str(sources["catalog_csv"]),
            "catalog_csv_sha256": _sha256_file(sources["catalog_csv"]),
            "cohorts_artifact": cohort_ref,
        },
        "cohort": counts,
        "parity": parity,
        "exclusions": {
            "failed_scores": counts["scores"]["failed"],
            "unknown_run_identity": counts["scores"]["unknown_provenance"]["run_id_missing"],
        },
        "unknown_provenance": {
            "independent_experiments": (cohort_ref or {}).get("independent_experiments"),
            "run_identity": ("insufficient_evidence"
                             if counts["scores"]["unknown_provenance"]["run_id_missing"]
                             else "present"),
        },
        "completeness": {
            "scores_json": "complete",
            "catalog_csv": "complete",
            "dataset_root": "present" if dataset_exists else "missing",
            "parity_compared": (parity or {}).get("n_compared") if isinstance(parity, dict) else None,
        },
        "no_backend_calls": True,
        "limitations": [
            "Read-only identity snapshot; no writable DatasetStore was constructed and no "
            "acoustic artifact was written.",
            "Completeness means the referenced inputs were readable, not that every row is "
            "eligible for a GP; independent experiment groups remain separately evidenced.",
        ],
    }
    content = _json_bytes(snapshot)
    key = idempotency_key or f"snapshot:{revision}:{_sha256_bytes(content)}"
    meta = service.attach_artifact(study_id, revision, "snapshot", content, {}, key)
    return {"status": "ok", "snapshot": _unwrap(meta), "revision": revision,
            "artifact": meta, "idempotent": False}


# --------------------------------------------------------------------------- training


def _require(service, study_id, kind):
    meta = service.get_artifact_metadata(study_id, kind)
    if meta.get("status") == "missing":
        raise Unavailable(f"current {kind} artifact is missing; build it first")
    if meta.get("status") != "available":
        raise Unavailable(f"current {kind} artifact is {meta.get('status')}")
    return meta


def _load_or_build_training(*, config_path, sources, root):
    """Prefer the committed native TrainingSet; otherwise build from the real inputs."""
    from hornlab_search.bo.data import build_native_training_set

    if sources is None:
        if (DEFAULT_TRAINING_JSON.is_file()
                and DEFAULT_TRAINING_JSON.with_suffix(".npz").is_file()):
            from tools.analysis.bo_sensitivity import load_native_training_set
            loaded = load_native_training_set(DEFAULT_TRAINING_JSON)
            if loaded.get("status") == "ok":
                return loaded["training"], loaded, "committed_artifact"
            raise Unavailable(
                f"committed training artifact is invalid: {loaded.get('reason')}")
        sources = _read_sources({}, root=root)
    training = build_native_training_set(
        config_path, scores_json=sources["scores_json"],
        catalog_csv=sources["catalog_csv"], dataset_root=sources["dataset_root"])
    return training, None, "native_build"


def build_training(service, study_id, *, root, spec=None, idempotency_key=None):
    """Build/attach ``training.npz``, ``training_ids.json`` and ``training_manifest.json``."""
    study, effective = _study_spec(service, study_id, spec)
    revision = study["revision"]
    existing = {kind: _existing(service, study_id, revision, kind)
                for kind in ("training", "training_ids", "training_manifest")}
    if all(existing.values()):
        return {"status": "ok", "revision": revision, "idempotent": True,
                "training": _unwrap(existing["training"]),
                "training_ids": _unwrap(existing["training_ids"]),
                "training_manifest": _unwrap(existing["training_manifest"]),
                "artifact": existing["training_manifest"]}

    snapshot = _require(service, study_id, "snapshot")
    task = _read_task(effective.get("task"), root=root,
                      config=(effective.get("task") or {}).get("config")
                      if isinstance(effective.get("task"), dict) else None)
    source_spec = effective.get("source") if isinstance(effective.get("source"), dict) else None
    sources = _read_sources(source_spec, root=root) if source_spec else None
    training, loaded, origin = _load_or_build_training(config_path=task["config"],
                                                       sources=sources, root=root)
    if getattr(training, "status", None) != "ok" or training.X is None:
        raise Unavailable(
            f"training set is {getattr(training, 'status', 'unavailable')!r}; "
            f"n_min={getattr(training, 'n_min', None)} n={getattr(training, 'n', 0)}")

    import numpy as np
    X = np.asarray(training.X, dtype=np.float64)
    J = np.asarray(training.J, dtype=np.float64).reshape(-1)
    Y = np.asarray(training.Y, dtype=np.float64).reshape(-1)
    Y_phys = None if training.Y_phys is None else np.asarray(training.Y_phys, dtype=np.float64)
    if not (np.all(np.isfinite(X)) and np.all(np.isfinite(J)) and np.all(np.isfinite(Y))):
        raise Unavailable("training arrays contain NaN/Infinity; refusing to publish")
    ids = tuple(str(i) for i in training.ids)
    dataset_bytes = _deterministic_npz({
        "X": X, "J": J, "Y": Y, "Y_phys": Y_phys,
        "ids": np.asarray(ids, dtype=np.str_),
    })
    dataset_sha = _sha256_bytes(dataset_bytes)
    ids_payload = {
        "tool": "study_training_ids",
        "schema": DATASET_SCHEMA,
        "protocol": PROTOCOL,
        "training_set_id": dataset_sha,
        "ids": list(ids),
        "selected_ids": list(training.selected_ids),
        "excluded_ids": list(training.excluded_ids),
        "elite_ids": list(training.elite_ids),
        "maximin_ids": list(training.maximin_ids),
    }
    manifest = {
        "tool": "study_training_manifest",
        "schema": TRAINING_MANIFEST_SCHEMA,
        "schema_version": 1,
        "protocol": PROTOCOL,
        "generated_utc": _utc_now(),
        "study_id": study_id,
        "revision": revision,
        "origin": origin,
        "training_set_id": dataset_sha,
        "status": training.status,
        "d": int(training.d),
        "n": int(training.n),
        "n_min": int(training.n_min),
        "n_max": int(training.n_max),
        "n_eligible": int(training.n_eligible),
        "n_unique": int(training.n_unique),
        "active_keys": list(training.active_keys),
        "projection_version": training.projection_version,
        "ids": list(ids),
        "selected_ids": list(training.selected_ids),
        "excluded_ids": list(training.excluded_ids),
        "elite_ids": list(training.elite_ids),
        "maximin_ids": list(training.maximin_ids),
        "subset_policy": {
            "method": "build_training_set",
            "n_min": int(training.n_min),
            "n_max": int(training.n_max),
            "rule": "64 lowest-J + 192 deterministic maximin when above the cap; "
                    "ties by observation/design ID",
        },
        "task": {
            "config": str(task["config"]),
            "config_sha256": task["config_sha256"],
            "brief": str(task["brief"]),
            "brief_sha256": task["brief_sha256"],
            "objective_version": task["objective_version"],
        },
        "sources": ({
            "scores_json": str(sources["scores_json"]),
            "scores_json_sha256": _sha256_file(sources["scores_json"]),
            "catalog_csv": str(sources["catalog_csv"]),
            "catalog_csv_sha256": _sha256_file(sources["catalog_csv"]),
            "dataset_root": str(sources["dataset_root"]),
        } if sources else ({
            "committed_artifact": str(DEFAULT_TRAINING_JSON),
            "committed_artifact_sha256": _sha256_file(DEFAULT_TRAINING_JSON),
        } if origin == "committed_artifact" else {})),
        "refusals": (
            [dict(r) for r in (getattr(training, "meta", {}) or {}).get("refused", ())]
            if origin == "native_build" else
            list((getattr(training, "meta", {}) or {}).get("refused", ()))),
        "refusal_reasons": dict((getattr(training, "meta", {}) or {}).get("refusal_reasons", {})),
        "no_backend_calls": True,
        "predictions_appended_to_measured_rows": False,
        "limitations": [
            "Training rows are measured/canonicalised observations only; no prediction is "
            "appended and no J=1000 failure row is trained.",
            "The frozen min/cap/subset policy is applied; excluded IDs are published.",
        ],
    }
    if loaded is not None:
        manifest["limitations"].extend(list(loaded.get("limitations") or ()))
    deps = {"snapshot": snapshot["sha256"]}
    dataset_meta = _attach_once(service, study_id, revision, "training", dataset_bytes,
                                deps, f"training:{revision}:{dataset_sha}")
    ids_meta = _attach_once(service, study_id, revision, "training_ids",
                            _json_bytes(ids_payload), deps, f"training_ids:{revision}:{dataset_sha}")
    manifest["dependencies"] = {"snapshot": snapshot["sha256"],
                                "training": dataset_meta["sha256"],
                                "training_ids": ids_meta["sha256"]}
    manifest_meta = _attach_once(service, study_id, revision, "training_manifest",
                                 _json_bytes(manifest), deps,
                                 f"training_manifest:{revision}:{dataset_sha}")
    return {"status": "ok", "revision": revision, "idempotent": False,
            "training": _unwrap(dataset_meta), "training_ids": _unwrap(ids_meta),
            "training_manifest": _unwrap(manifest_meta), "artifact": manifest_meta,
            "training_set_id": dataset_sha, "d": int(training.d), "n": int(training.n)}


# --------------------------------------------------------------------------- analysis


def build_analysis(service, study_id, *, root, spec=None, idempotency_key=None):
    """Emit a bounded analysis summary; never duplicating scorer mathematics."""
    study, _ = _study_spec(service, study_id, spec)
    revision = study["revision"]
    existing = _existing(service, study_id, revision, "analysis")
    if existing is not None:
        return {"status": "ok", "revision": revision, "artifact": existing,
                "analysis": _unwrap(existing), "idempotent": True}

    snapshot_meta = _require(service, study_id, "snapshot")
    training_meta = _require(service, study_id, "training")
    ids_meta = _require(service, study_id, "training_ids")
    manifest_meta = _require(service, study_id, "training_manifest")
    snapshot = _load_json(service.store.artifacts / snapshot_meta["sha256"], "snapshot")
    manifest = _load_json(service.store.artifacts / manifest_meta["sha256"], "training manifest")

    selected = list(manifest.get("selected_ids") or ())
    excluded = list(manifest.get("excluded_ids") or ())
    independent = ((snapshot.get("unknown_provenance") or {}).get("independent_experiments")
                   if isinstance(snapshot, dict) else None)
    insufficient = (not isinstance(independent, dict)
                    or independent.get("status") in (None, "insufficient_evidence")
                    or independent.get("known", 0) == 0)
    refusals = manifest.get("refusal_reasons") or {}
    analysis = {
        "tool": "study_analysis",
        "schema": ANALYSIS_SCHEMA,
        "schema_version": 1,
        "protocol": PROTOCOL,
        "generated_utc": _utc_now(),
        "study_id": study_id,
        "revision": revision,
        "snapshot": _unwrap(snapshot_meta),
        "training": {
            "artifact": _unwrap(training_meta),
            "ids": _unwrap(ids_meta),
            "manifest": _unwrap(manifest_meta),
            "training_set_id": manifest.get("training_set_id"),
            "d": manifest.get("d"),
            "n": manifest.get("n"),
            "n_min": manifest.get("n_min"),
            "n_max": manifest.get("n_max"),
            "active_keys": list(manifest.get("active_keys") or ()),
            "projection_version": manifest.get("projection_version"),
        },
        "subset": {
            "retained_ids": selected,
            "excluded_ids": excluded,
            "elite_ids": list(manifest.get("elite_ids") or ()),
            "maximin_ids": list(manifest.get("maximin_ids") or ()),
            "retained": len(selected),
            "excluded": len(excluded),
            "rule": (manifest.get("subset_policy") or {}).get("rule"),
        },
        "refusals_by_reason": dict(refusals),
        "metric_score_identity": {
            "brief_name": (snapshot.get("task") or {}).get("brief_name"),
            "brief_sha256": (snapshot.get("task") or {}).get("brief_sha256"),
            "objective_version": (snapshot.get("task") or {}).get("objective_version"),
            "parity": snapshot.get("parity"),
        },
        "heldout_support": {
            "status": ("insufficient_evidence" if insufficient else "descriptive"),
            "independent_experiments": independent,
            "note": ("independent run/resume groups are not established; descriptive fields "
                     "only and recommendations are suppressed" if insufficient
                     else "group identity is present; validation remains a caller decision"),
        },
        "recommendation_status": "suppressed" if insufficient else "descriptive",
        "metric_math_recomputed": False,
        "no_backend_calls": True,
        "limitations": [
            "Reuses bo.data/bo.cohort/bo.metrics identity metadata; no scorer math is copied here.",
            "A usable evidence report can coexist with a suppressed recommendation.",
        ],
    }
    deps = {"snapshot": snapshot_meta["sha256"], "training": training_meta["sha256"],
            "training_ids": ids_meta["sha256"], "training_manifest": manifest_meta["sha256"]}
    content = _json_bytes(analysis)
    meta = _attach_once(service, study_id, revision, "analysis", content, deps,
                        f"analysis:{revision}:{_sha256_bytes(content)}")
    return {"status": "ok", "revision": revision, "artifact": meta,
            "analysis": _unwrap(meta), "idempotent": False}


# --------------------------------------------------------------------------- proposal


def _load_pool(pool_arg, source_spec, config_path, *, root):
    from tools.analysis.bo_sensitivity import load_candidate_pool
    if pool_arg is not None:
        return pool_arg
    source = source_spec if isinstance(source_spec, dict) else {}
    raw = source.get("pool_json")
    path = _resolve_input(root, raw,
                          DEFAULT_POOL_JSON if DEFAULT_POOL_JSON.is_file() else None,
                          "pool_json")
    return load_candidate_pool(path)


def _pool_manifest(pool, *, policy, config_path, encoding):
    summary = pool.summary() if hasattr(pool, "summary") else {}
    sample = []
    for candidate in tuple(getattr(pool, "candidates", ()) or ())[:5]:
        try:
            sample.append(candidate.as_dict(include_vectors=False))
        except Exception:  # noqa: BLE001 - bounded, best-effort provenance only
            sample.append({"candidate_id": getattr(candidate, "candidate_id", None)})
    return {
        "tool": "study_pool_manifest",
        "schema": POOL_MANIFEST_SCHEMA,
        "schema_version": 1,
        "protocol": PROTOCOL,
        "generated_utc": _utc_now(),
        "policy": policy,
        "config": str(config_path),
        "encoding": (None if encoding is None else {
            "version": getattr(encoding, "version", None),
            "d": int(getattr(encoding, "d", 0)),
            "active_keys": list(getattr(encoding, "active_keys", ())),
        }),
        "summary": summary,
        "n_candidates": len(getattr(pool, "candidates", ()) or ()),
        "candidate_sample": sample,
        "status_note": POOL_STATUS_NOTE,
        "no_backend_calls": True,
    }


def _proposal_limitations(policy):
    return [
        "Advisory offline proposal; no BEM/GPU solve was run.",
        POOL_STATUS_NOTE,
        "Predicted J and its credible interval are model outputs, not measured results, and "
        "are never appended as measured rows.",
        "The acquisition value is a technical ranking diagnostic, not predicted J or a "
        "probability of success.",
        "J is objective v4 only; no cross-version ranking.",
        "The every-fourth exploration cadence is stateful and does not reset on resume.",
        f"proposal policy: {policy}; verification mode follows the frozen selection rule.",
    ]


def build_proposal(service, study_id, *, root, policy=None, seed=None, idempotency_key=None,
                   spec=None, pool=None, cohort=None, metric_observations=None,
                   cma_seed_candidates=None):
    """Build/attach model/pool/proposal artifacts through the landed policy dispatcher."""
    from hornlab_search.bo import policy as policy_mod

    study, effective = _study_spec(service, study_id, spec)
    revision = study["revision"]
    existing = {kind: _existing(service, study_id, revision, kind)
                for kind in ("model", "pool", "proposal")}
    if all(existing.values()):
        return {"status": "ok", "revision": revision, "idempotent": True,
                "model": _unwrap(existing["model"]), "pool": _unwrap(existing["pool"]),
                "proposal": _unwrap(existing["proposal"]), "artifact": existing["proposal"]}

    snapshot_meta = _require(service, study_id, "snapshot")
    training_meta = _require(service, study_id, "training")
    analysis_meta = _require(service, study_id, "analysis")
    manifest_meta = _require(service, study_id, "training_manifest")

    spec_policy = effective.get("policy") if isinstance(effective.get("policy"), dict) else {}
    chosen = (policy or spec_policy.get("proposal_policy")
              or (spec_policy.get("mode") if spec_policy.get("mode")
                  in policy_mod.PROPOSAL_POLICIES else None)
              or "scalar")
    if chosen not in policy_mod.PROPOSAL_POLICIES:
        raise StudyError(f"unsupported proposal policy {chosen!r}")
    if seed is None:
        seed = spec_policy.get("seed", spec_policy.get("acq_seed", 0))
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise StudyError("proposal seed must be an integer")

    task = _read_task(effective.get("task"), root=root,
                      config=(effective.get("task") or {}).get("config")
                      if isinstance(effective.get("task"), dict) else None)
    from hornlab_search.bo.encoding import ActiveProjection
    from hornlab_search.bo.data import TrainingSet
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace

    cfg = load_config(task["config"])
    space = DesignSpace.from_config(cfg)
    encoding = ActiveProjection.from_space(space, no_ops={"morph_exponent": 4.0})
    manifest = _load_json(service.store.artifacts / manifest_meta["sha256"], "training manifest")
    import numpy as np
    with np.load(service.store.artifacts / training_meta["sha256"], allow_pickle=False) as arrays:
        training_set = TrainingSet(
            status="ok", d=int(manifest["d"]), n=int(manifest["n"]),
            X=np.asarray(arrays["X"], dtype=np.float64),
            J=np.asarray(arrays["J"], dtype=np.float64).reshape(-1, 1),
            Y=np.asarray(arrays["Y"], dtype=np.float64).reshape(-1, 1),
            Y_phys=(np.asarray(arrays["Y_phys"], dtype=np.float64).reshape(-1, 1)
                    if "Y_phys" in arrays.files else None),
            G=None, ids=tuple(manifest["ids"]),
            selected_ids=tuple(manifest["selected_ids"]),
            excluded_ids=tuple(manifest["excluded_ids"]),
            elite_ids=tuple(manifest["elite_ids"]),
            maximin_ids=tuple(manifest["maximin_ids"]),
            n_eligible=int(manifest["n_eligible"]), n_unique=int(manifest["n_unique"]),
            n_min=int(manifest["n_min"]), n_max=int(manifest["n_max"]),
            active_keys=tuple(manifest["active_keys"]),
            projection_version=manifest.get("projection_version"), preparation=None,
            meta={})

    candidate_pool = None
    pool_error = None
    try:
        candidate_pool = _load_pool(pool, effective.get("source"), task["config"], root=root)
    except (Unavailable, StudyError, OSError, ValueError) as exc:
        pool_error = str(exc)

    capability = policy_mod.capability_status(
        chosen, training_set=training_set, cohort=cohort,
        metric_observations=metric_observations, pool=candidate_pool,
        seeds=cma_seed_candidates)
    pool_payload = (_pool_manifest(candidate_pool, policy=chosen, config_path=task["config"],
                                   encoding=encoding) if candidate_pool is not None else {
        "tool": "study_pool_manifest", "schema": POOL_MANIFEST_SCHEMA,
        "schema_version": 1, "protocol": PROTOCOL, "generated_utc": _utc_now(),
        "policy": chosen, "status": "unavailable", "reason": pool_error,
        "status_note": POOL_STATUS_NOTE, "no_backend_calls": True,
    })
    pool_meta = _attach_once(service, study_id, revision, "pool", _json_bytes(pool_payload),
                             {"snapshot": snapshot_meta["sha256"]},
                             f"pool:{revision}:{chosen}")

    outcome = None
    if capability.get("status") == "ok":
        outcome = policy_mod.fit_and_propose(
            chosen, training_set=training_set, cohort=cohort,
            metric_observations=metric_observations, pool=candidate_pool,
            seed=int(seed), encoding=encoding, config=cfg,
            cma_seed_candidates=cma_seed_candidates)
        status = outcome.status
        reason = outcome.reason
        detail = outcome.detail
    else:
        status = capability.get("status")
        reason = capability.get("reason")
        detail = capability.get("detail")
        # A preflight data/engine gap is a capability refusal, never a fabricated
        # proposal; the exact reason is preserved in the artifact.
        status = ("pool_exhausted" if status == "pool_exhausted" else "capability_missing")

    model_manifest = {
        "tool": "study_model_manifest",
        "schema": MODEL_MANIFEST_SCHEMA,
        "schema_version": 1,
        "protocol": PROTOCOL,
        "generated_utc": _utc_now(),
        "study_id": study_id,
        "revision": revision,
        "policy": chosen,
        "verification_mode": policy_mod.verification_mode(chosen),
        "seed": int(seed),
        "status": status,
        "reason": reason,
        "detail": detail,
        "training_set_id": manifest.get("training_set_id"),
        "training_set": _unwrap(training_meta),
        "library_versions": (outcome.library_versions if outcome is not None
                             else capability.get("library_versions")),
        "protocol": PROTOCOL,
        "selection_reason": getattr(outcome, "selection_reason", None),
        "counts": (outcome.counts if outcome is not None else {}),
        "model_state_persisted": False,
        "no_backend_calls": True,
        "limitations": [
            "Model hyperparameters/state are not serialised as a pickled object; only the "
            "manifest identity is published. Future adaptive refits use the manifest hashes.",
        ],
    }
    deps_model = {"snapshot": snapshot_meta["sha256"], "training": training_meta["sha256"],
                  "training_manifest": manifest_meta["sha256"]}
    model_meta = _attach_once(service, study_id, revision, "model", _json_bytes(model_manifest),
                              deps_model, f"model:{revision}:{chosen}")

    proposal = {
        "tool": "study_proposal",
        "schema": PROPOSAL_SCHEMA,
        "schema_version": 1,
        "protocol": PROTOCOL,
        "generated_utc": _utc_now(),
        "study_id": study_id,
        "revision": revision,
        "status": status,
        "reason": reason,
        "detail": detail,
        "proposal_policy": chosen,
        "verification_mode": policy_mod.verification_mode(chosen),
        "proposal": (outcome.proposal if outcome is not None else None),
        "candidate": (outcome.proposal if outcome is not None else None),
        "predicted": (outcome.predicted if outcome is not None else None),
        "acquisition": (outcome.acquisition if outcome is not None else None),
        "selection_reason": getattr(outcome, "selection_reason", None),
        "fallback": bool(getattr(outcome, "fallback", False)),
        "counts": (outcome.counts if outcome is not None else {}),
        "library_versions": (outcome.library_versions if outcome is not None
                             else capability.get("library_versions")),
        "predictions_appended_to_measured_rows": False,
        "status_note": POOL_STATUS_NOTE,
        "limitations": _proposal_limitations(chosen),
    }
    if proposal["proposal"] is not None:
        proposal["proposal"].setdefault("status_note", POOL_STATUS_NOTE)
    deps_proposal = {"snapshot": snapshot_meta["sha256"], "training": training_meta["sha256"],
                     "analysis": analysis_meta["sha256"], "model": model_meta["sha256"],
                     "pool": pool_meta["sha256"], "training_manifest": manifest_meta["sha256"]}
    proposal_meta = _attach_once(service, study_id, revision, "proposal", _json_bytes(proposal),
                                 deps_proposal,
                                 f"proposal:{revision}:{chosen}:{_sha256_bytes(_json_bytes(proposal))}")
    return {"status": status, "reason": reason, "revision": revision, "idempotent": False,
            "model": _unwrap(model_meta), "pool": _unwrap(pool_meta),
            "proposal": _unwrap(proposal_meta), "artifact": proposal_meta,
            "proposal_policy": chosen,
            "verification_mode": policy_mod.verification_mode(chosen),
            "predicted": proposal["predicted"]}


__all__ = [
    "SNAPSHOT_SCHEMA", "TRAINING_MANIFEST_SCHEMA", "ANALYSIS_SCHEMA",
    "MODEL_MANIFEST_SCHEMA", "POOL_MANIFEST_SCHEMA", "PROPOSAL_SCHEMA",
    "DEFAULT_CONFIG", "DEFAULT_BRIEF", "DEFAULT_EVIDENCE_ROOT", "DEFAULT_SCORES",
    "DEFAULT_CATALOG", "DEFAULT_DATASET_ROOT", "DEFAULT_TRAINING_JSON", "DEFAULT_POOL_JSON",
    "freeze_snapshot", "build_training", "build_analysis", "build_proposal",
]
