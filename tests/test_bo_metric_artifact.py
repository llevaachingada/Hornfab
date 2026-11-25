"""Artifact serialization + integrity (Pass 2, synthetic only).

Proves the ``metric-training-npz-v1`` contract: deterministic bytes, a loader that refuses
tampered/foreign/non-finite payloads, and a validator that re-hashes the recorded bounds/score
identity and reconstruction-checks every ``J`` row.  No solver, dataset or GPU is touched.
"""
from __future__ import annotations

import dataclasses
import io
import zipfile

import numpy as np
import pytest

from hornlab_search.bo.metric_artifact import (
    ARTIFACT_FORMAT,
    ARTIFACT_KIND,
    REASON_ARRAY_NONFINITE,
    REASON_ARRAY_SHA,
    REASON_CHECKSUM_MISMATCH,
    REASON_J_ROW_MISMATCH,
    REASON_PICKLE_REFUSED,
    REASON_SCORE_MISMATCH,
    REASON_SCORE_MISSING,
    artifact_bytes,
    artifact_from_bytes,
    load_artifact_file,
    validate_metric_training_artifact,
)
from hornlab_search.bo.metric_contracts import (
    METRIC_TRAINING_VERSION,
    MetricTrainingArtifact,
    V10_COMPONENT_NAMES,
    component_names as schema_component_names,
    component_schema,
    component_schema_hash,
)
from hornlab_search.bo.metric_identity import (
    bounds_identity,
    bounds_payload,
    recompute_bounds_hash,
    score_identity,
    score_payload,
)

BRIEF = "b" * 32
SCORE = "c" * 32
TASK = {
    "task_identity": "task-1",
    "backend": "beat_cuda",
    "fidelity": "screen",
    "grid_hash": "grid-1",
    "dependency_hash": "dep-1",
    "mesh_hash": "mesh-1",
}


class Encoding:
    version = "test-active-projection-v1"

    def __init__(self, keys=("a", "b", "c"), *, lo=0.0, hi=1.0, log=False):
        self.active_keys = tuple(keys)
        self.d = len(self.active_keys)
        self._lo, self._hi, self._log = float(lo), float(hi), bool(log)

    def key_transforms(self):
        return {k: {"lo": self._lo, "hi": self._hi, "log": self._log,
                    "transform": "log10" if self._log else "identity", "active": True}
                for k in self.active_keys}


def make_artifact(*, n=4, encoding=None, objective_version=10, component_names=None,
                  Y=None, J=None, metadata_extra=None):
    encoding = encoding or Encoding()
    version = int(objective_version)
    payload = bounds_payload(encoding, strict=True)
    bounds_hash = recompute_bounds_hash(payload)
    score_payload_block = score_payload(objective_version=version, brief_hash=BRIEF,
                                        score_hash=SCORE)
    score_id = score_identity(objective_version=version, brief_hash=BRIEF, score_hash=SCORE)
    names = tuple(component_names or schema_component_names(version))
    X = np.linspace(0.1, 0.9, n * encoding.d, dtype=np.float64).reshape(n, encoding.d)
    if Y is None:
        base = np.linspace(0.1, 0.1 * len(names), len(names), dtype=np.float64)
        Y = np.tile(base, (n, 1))
    Y = np.asarray(Y, dtype=np.float64)
    if J is None:
        J = np.sum(Y, axis=1, keepdims=True)
    metadata = {
        "objective_version": version,
        "brief_hash": BRIEF,
        "score_hash": SCORE,
        "score_identity": score_id,
        "score_identity_payload": score_payload_block,
        "bounds_hash": bounds_hash,
        "bounds_identity_payload": payload,
        "component_schema": component_schema(version)["schema_id"],
        "component_schema_hash": component_schema_hash(version),
        **TASK,
    }
    metadata.update(metadata_extra or {})
    ids = tuple(f"obs-{i:02d}" for i in range(n))
    return MetricTrainingArtifact(
        status="ok", objective_version=version,
        feature_names=tuple(encoding.active_keys), component_names=names,
        X=np.array(X, dtype=np.float64), J=np.array(J, dtype=np.float64),
        Y_components=np.array(Y, dtype=np.float64),
        observation_ids=ids, selected_ids=ids, metadata=metadata,
        checksum="source-checksum-v1")


def _rewrite_member(blob: bytes, member: str, mutator) -> bytes:
    src = zipfile.ZipFile(io.BytesIO(blob))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as dst:
        for name in src.namelist():
            data = src.read(name)
            if name == member:
                data = mutator(data)
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            dst.writestr(info, data)
    return out.getvalue()


# --------------------------------------------------------------------------- determinism/round trip


def test_artifact_bytes_are_byte_identical_and_round_trip():
    artifact = make_artifact()
    first = artifact_bytes(artifact)
    second = artifact_bytes(make_artifact())
    assert first == second

    loaded, check = artifact_from_bytes(first, expected_checksum=artifact.checksum)
    assert check.ok and loaded is not None
    assert loaded.status == "ok"
    assert loaded.checksum == artifact.checksum
    assert np.array_equal(loaded.X, artifact.X)
    assert np.array_equal(loaded.J, artifact.J)
    assert np.array_equal(loaded.Y_components, artifact.Y_components)
    assert loaded.X.flags.writeable is False
    assert loaded.metadata["bounds_hash"] == artifact.metadata["bounds_hash"]

    # A loaded artifact is self-consistent and validates against the live projection/score/task.
    assert validate_metric_training_artifact(loaded).ok
    expected_score = {"objective_version": 10, "brief_hash": BRIEF, "score_hash": SCORE}
    live = validate_metric_training_artifact(
        loaded, encoding=Encoding(), expected_bounds_hash=artifact.metadata["bounds_hash"],
        expected_score=expected_score, expected_task=TASK)
    assert live.ok, live.to_dict()


def test_artifact_manifest_records_identity_and_format():
    blob = artifact_bytes(make_artifact())
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        import json
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["format"] == ARTIFACT_FORMAT
    assert manifest["kind"] == ARTIFACT_KIND
    assert manifest["version"] == METRIC_TRAINING_VERSION
    assert manifest["objective_version"] == 10
    assert manifest["component_names"] == list(V10_COMPONENT_NAMES)
    assert manifest["bounds_hash"] == make_artifact().metadata["bounds_hash"]
    assert manifest["score_identity"] == make_artifact().metadata["score_identity"]
    assert set(manifest["arrays"]) == {"X", "J", "Y_components"}
    assert manifest["arrays"]["X"]["dtype"] == "float64"
    assert manifest["arrays"]["X"]["shape"] == [4, 3]


# --------------------------------------------------------------------------- refusal paths


def test_artifact_from_bytes_refuses_garbage_truncated_and_foreign():
    _, bad = artifact_from_bytes(b"not a zip file")
    assert not bad.ok

    blob = artifact_bytes(make_artifact())
    _, truncated = artifact_from_bytes(blob[: len(blob) // 2])
    assert not truncated.ok

    foreign = io.BytesIO()
    with zipfile.ZipFile(foreign, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", b'{"format":"something-else","kind":"x"}')
    _, foreign_check = artifact_from_bytes(foreign.getvalue())
    assert not foreign_check.ok
    assert "format_foreign" in foreign_check.reason or "foreign" in foreign_check.reason


def test_tampered_array_bytes_are_refused():
    blob = artifact_bytes(make_artifact())

    def bump(payload):
        arr = np.lib.format.read_array(io.BytesIO(payload), allow_pickle=False)
        arr = arr + 1.0
        stream = io.BytesIO()
        np.lib.format.write_array(stream, arr, allow_pickle=False)
        return stream.getvalue()

    _, check = artifact_from_bytes(_rewrite_member(blob, "X.npy", bump))
    assert not check.ok
    assert check.reason == f"{REASON_ARRAY_SHA}:X"

    flipped = bytearray(blob)
    flipped[len(flipped) // 2] ^= 0xFF
    _, raw = artifact_from_bytes(bytes(flipped))
    assert not raw.ok


def test_nonfinite_arrays_are_refused():
    artifact = make_artifact()
    Y = np.array(artifact.Y_components, copy=True)
    Y[1, 2] = np.nan
    bad = dataclasses.replace(artifact, Y_components=Y)
    loaded, check = artifact_from_bytes(artifact_bytes(bad))
    assert loaded is None
    assert not check.ok
    assert f"{REASON_ARRAY_NONFINITE}:Y_components" in check.reasons


def test_validate_detects_j_row_mismatch():
    artifact = make_artifact()
    J = np.array(artifact.J, copy=True)
    J[2, 0] += 0.5
    broken = dataclasses.replace(artifact, J=J)
    check = validate_metric_training_artifact(broken)
    assert not check.ok
    assert f"{REASON_J_ROW_MISMATCH}:2" in check.reasons


def test_validate_detects_component_reorder_and_schema_hash():
    names = tuple(reversed(V10_COMPONENT_NAMES))
    reordered = make_artifact(component_names=names)
    check = validate_metric_training_artifact(reordered)
    assert not check.ok
    assert "artifact_component_schema_mismatch" in check.reasons

    bad_hash = make_artifact(metadata_extra={"component_schema_hash": "0" * 64})
    check = validate_metric_training_artifact(bad_hash)
    assert "artifact_component_schema_hash_mismatch" in check.reasons


def test_validate_detects_wrong_and_missing_score_identity():
    artifact = make_artifact()
    wrong = {"objective_version": 10, "brief_hash": BRIEF, "score_hash": "d" * 32}
    check = validate_metric_training_artifact(artifact, expected_score=wrong)
    assert not check.ok
    assert REASON_SCORE_MISMATCH in check.reasons

    metadata = dict(artifact.metadata)
    for key in ("score_identity", "score_identity_payload", "brief_hash", "score_hash"):
        metadata.pop(key, None)
    missing = dataclasses.replace(artifact, metadata=metadata)
    check = validate_metric_training_artifact(
        missing, expected_score={"objective_version": 10, "brief_hash": BRIEF,
                                 "score_hash": SCORE})
    assert not check.ok
    assert REASON_SCORE_MISSING in check.reasons


def test_validate_detects_wrong_bounds_identity():
    artifact = make_artifact()
    other = Encoding(keys=("a", "b", "c"), hi=2.0)
    check = validate_metric_training_artifact(
        artifact, encoding=other, expected_bounds_hash=bounds_identity(other))
    assert not check.ok
    assert "bounds_identity_mismatch" in check.reasons


def test_manifest_checksum_tamper_is_refused():
    artifact = make_artifact()
    blob = artifact_bytes(artifact)

    def drop_payload(payload):
        import json
        manifest = json.loads(payload.decode("utf-8"))
        manifest["bounds_hash"] = "tampered"
        return json.dumps(manifest).encode("utf-8")

    _, check = artifact_from_bytes(_rewrite_member(blob, "manifest.json", drop_payload))
    assert not check.ok
    assert check.reason == REASON_CHECKSUM_MISMATCH


def test_fit_gate_refuses_corrupt_artifact_before_any_torch_work():
    pytest.importorskip("torch")
    from hornlab_search.bo.metric_model import fit_metric_model

    loaded, check = artifact_from_bytes(artifact_bytes(make_artifact()))
    assert check.ok and loaded is not None
    Y = np.array(loaded.Y_components, copy=True)
    Y[0] = Y[0] + np.array([0.1, -0.1, 0.0, 0.0])  # J row sum unchanged, bytes changed
    corrupt = dataclasses.replace(loaded, Y_components=Y)
    result = fit_metric_model(corrupt)
    assert result.status == "unavailable"
    assert result.reason == REASON_CHECKSUM_MISMATCH
    assert result.model is None


def test_load_artifact_file_refuses_pickled_model_names(tmp_path):
    path = tmp_path / "model.pkl"
    path.write_bytes(b"not-a-pickle-but-should-never-be-opened")
    loaded, check = load_artifact_file(path)
    assert loaded is None
    assert not check.ok
    assert check.reason == REASON_PICKLE_REFUSED

    good = tmp_path / "artifact.npz"
    good.write_bytes(artifact_bytes(make_artifact()))
    loaded, check = load_artifact_file(good)
    assert check.ok and loaded is not None
