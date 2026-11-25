"""Bounds/score identity across the Pass 1 seams (Pass 2, synthetic only).

Covers the frozen-box identity law (same ``d`` is not the same physical box; transform and
active-key order matter), the selector's changed-bounds exclusion, artifact identity stamping
(``require_identity=True``) and the proposal identity gate.  No solver/GPU is touched; the
proposal paths use a fake model + patched acquisition so the identity contract is isolated.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.bo.metric_contracts import (
    MetricTrainingCandidate,
    SelectionResult,
    component_names,
)
from hornlab_search.bo.metric_identity import (
    REASON_BOUNDS_MISMATCH,
    REASON_BOUNDS_MISSING,
    bounds_identity,
    bounds_payload,
    check_score_identity,
    score_payload,
    score_identity,
)
from hornlab_search.bo.metric_propose import (
    MetricProposalPolicy,
    propose_metric_candidate,
)
from hornlab_search.bo.metric_training import (
    bounds_identity as training_bounds_identity,
    build_metric_training_artifact,
    select_metric_training_observations,
)
from hornlab_search.bo.metric_artifact import validate_metric_training_artifact

BRIEF = "b" * 32
SCORE = "c" * 32


def test_writer_brief_hash_is_accepted_and_matched_exactly():
    brief = "16825ffd3faf"
    payload = score_payload(objective_version=10, brief_hash=brief, score_hash=SCORE)
    metadata = {**payload, "score_identity_payload": payload,
                "score_identity": score_identity(objective_version=10, brief_hash=brief,
                                                 score_hash=SCORE)}
    assert check_score_identity(metadata=metadata, objective_version=10,
                                brief_hash=brief, score_hash=SCORE).ok
    assert not check_score_identity(metadata=metadata, objective_version=10,
                                    brief_hash="16825ffd3fa0", score_hash=SCORE).ok
    assert not check_score_identity(metadata=metadata, objective_version=10,
                                    brief_hash=brief + "0000", score_hash=SCORE).ok


def test_short_score_and_non_writer_brief_lengths_are_refused():
    with pytest.raises(ValueError):
        score_payload(objective_version=10, brief_hash="16825ffd3faf", score_hash="c" * 12)
    for length in (11, 13, 15):
        with pytest.raises(ValueError):
            score_payload(objective_version=10, brief_hash="b" * length, score_hash=SCORE)


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

    def __init__(self, keys=("a", "b", "c"), *, lo=0.0, hi=1.0, log=False, fixed=None):
        self.active_keys = tuple(keys)
        self.d = len(self.active_keys)
        self._lo, self._hi, self._log = float(lo), float(hi), bool(log)
        self.fixed_values = dict(fixed or {})

    def key_transforms(self):
        return {k: {"lo": self._lo, "hi": self._hi, "log": self._log,
                    "transform": "log10" if self._log else "identity", "active": True}
                for k in self.active_keys}


# --------------------------------------------------------------------------- bounds law


def test_same_dimension_is_not_the_same_box():
    base = Encoding()
    wider = Encoding(hi=2.0)
    assert base.d == wider.d
    assert bounds_identity(base) != bounds_identity(wider)


def test_transform_kind_and_active_key_order_change_identity():
    identity = Encoding(log=False)
    logged = Encoding(log=True, lo=0.01)
    assert bounds_identity(identity) != bounds_identity(logged)

    ordered = Encoding(keys=("a", "b", "c"))
    reordered = Encoding(keys=("b", "a", "c"))
    assert bounds_identity(ordered) != bounds_identity(reordered)


def test_fixed_values_change_identity():
    plain = Encoding()
    pinned = Encoding(fixed={"dropped_key": 0.5})
    assert bounds_identity(plain) == bounds_identity(plain)
    assert bounds_identity(plain) != bounds_identity(pinned)


def test_training_bounds_identity_delegates_to_strict_contract():
    encoding = Encoding()
    assert training_bounds_identity(encoding) == bounds_identity(encoding)


# --------------------------------------------------------------------------- selector


def _candidate(i, encoding, *, bounds_hash_value, d=None):
    return MetricTrainingCandidate(
        observation_id=f"obs-{i:03d}",
        x=np.array([0.1 + 0.01 * i, 0.2, 0.3], dtype=np.float64),
        J=float(i),
        objective_version=10,
        physical_id=f"phys-{i:03d}",
        brief_hash=BRIEF, score_hash=SCORE, task_identity=TASK["task_identity"],
        backend=TASK["backend"], fidelity=TASK["fidelity"], grid_hash=TASK["grid_hash"],
        dependency_hash=TASK["dependency_hash"], mesh_hash=TASK["mesh_hash"],
        active_keys=tuple(encoding.active_keys),
        bounds_hash=bounds_hash_value,
        status="ok")


def test_selector_excludes_same_different_physical_box():
    encoding = Encoding()
    stale_encoding = Encoding(hi=5.0)  # identical d, different physical box
    good = [_candidate(i, encoding, bounds_hash_value=bounds_identity(encoding))
            for i in range(4)]
    stale = _candidate(5, encoding, bounds_hash_value=bounds_identity(stale_encoding))
    selection = select_metric_training_observations(good + [stale], encoding=encoding)
    reasons = {entry["observation_id"]: list(entry["reasons"])
               for entry in selection.excluded}
    assert reasons["obs-005"] == ["bounds_identity_mismatch"]
    assert selection.n_unique == 4


# --------------------------------------------------------------------------- artifact identity


def _selection(encoding):
    names = tuple(component_names(10))
    components = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float64)
    candidate = MetricTrainingCandidate(
        observation_id="obs-0",
        x=np.array([0.2, 0.5, 0.7], dtype=np.float64),
        J=float(components.sum()), objective_version=10, physical_id="phys-0",
        brief_hash=BRIEF, score_hash=SCORE, task_identity=TASK["task_identity"],
        backend=TASK["backend"], fidelity=TASK["fidelity"], grid_hash=TASK["grid_hash"],
        dependency_hash=TASK["dependency_hash"], mesh_hash=TASK["mesh_hash"],
        active_keys=tuple(encoding.active_keys),
        bounds_hash=bounds_identity(encoding), status="ok",
        components=components, component_names=names)
    return SelectionResult(
        status="ok", d=encoding.d, n_available=1, n_compatible=1, n_unique=1,
        n_selected=1, n_min=16, n_max=256, selected=(candidate,),
        objective_version=10, component_names=names)


def _identity_metadata(encoding, **over):
    metadata = {"objective_version": 10, "brief_hash": BRIEF, "score_hash": SCORE,
                "encoding": encoding, **TASK}
    metadata.update(over)
    return metadata


def test_require_identity_stamps_and_validates_full_identity():
    encoding = Encoding()
    artifact = build_metric_training_artifact(
        _selection(encoding), identity_metadata=_identity_metadata(encoding),
        require_identity=True)
    assert artifact.ok
    assert artifact.metadata["bounds_hash"] == bounds_identity(encoding)
    assert artifact.metadata["bounds_identity_payload"]["active_keys"] == list(
        encoding.active_keys)
    assert artifact.metadata["score_identity"]
    assert artifact.metadata["score_identity_payload"]["brief_hash"] == BRIEF

    check = validate_metric_training_artifact(
        artifact, encoding=encoding, expected_bounds_hash=bounds_identity(encoding),
        expected_score={"objective_version": 10, "brief_hash": BRIEF, "score_hash": SCORE},
        expected_task=TASK)
    assert check.ok, check.to_dict()


def test_require_identity_refuses_missing_or_wrong_bounds_and_score():
    encoding = Encoding()
    selection = _selection(encoding)

    missing_bounds = build_metric_training_artifact(
        selection, identity_metadata={"objective_version": 10, "brief_hash": BRIEF,
                                      "score_hash": SCORE},
        require_identity=True)
    assert missing_bounds.status == "refused"
    assert "identity:bounds_payload_missing" in missing_bounds.reasons

    payload = bounds_payload(encoding, strict=True)
    wrong_bounds = build_metric_training_artifact(
        selection, identity_metadata=_identity_metadata(
            encoding, bounds_identity_payload=payload, bounds_hash="deadbeef"),
        require_identity=True)
    assert wrong_bounds.status == "refused"
    assert "identity:bounds_hash_mismatch" in wrong_bounds.reasons

    missing_version = build_metric_training_artifact(
        selection, identity_metadata={"brief_hash": BRIEF, "score_hash": SCORE,
                                      "encoding": encoding},
        require_identity=True)
    assert "identity:objective_version_missing" in missing_version.reasons

    missing_score = build_metric_training_artifact(
        selection, identity_metadata={"objective_version": 10, "encoding": encoding},
        require_identity=True)
    assert "identity:brief_hash_missing" in missing_score.reasons
    assert "identity:score_hash_missing" in missing_score.reasons

    wrong_score = build_metric_training_artifact(
        selection, identity_metadata=_identity_metadata(encoding, score_identity="d" * 64),
        require_identity=True)
    assert "identity:score_identity_mismatch" in wrong_score.reasons


def test_require_identity_false_keeps_pass1_synthetic_callers_working():
    encoding = Encoding()
    artifact = build_metric_training_artifact(
        _selection(encoding),
        identity_metadata={"brief_hash": "brief-1", "score_hash": "score-1",
                           "backend": "beat_cuda"})
    assert artifact.ok
    assert artifact.metadata["brief_hash"] == "brief-1"
    # No identity was invented for a synthetic caller.
    assert "bounds_identity_payload" not in artifact.metadata
    assert "score_identity" not in artifact.metadata


# --------------------------------------------------------------------------- proposal


def _fake_model(**over):
    data = dict(status="ok", reason="ok", model=object(), d=3,
                train_X=np.zeros((1, 3)), model_hash="m" * 64, artifact_checksum="a" * 64,
                timing_s=0.01, library_versions={})
    data.update(over)
    return SimpleNamespace(**data)


def _fake_pool():
    candidate = SimpleNamespace(
        candidate_id="pool-0", active_vector=np.array([0.2, 0.5, 0.7]),
        geometry_hash="geom-0", design_hash="design-0", intended_solve_hash="solve-0")
    return SimpleNamespace(status="ok", candidates=(candidate,))


def _patch_proposal(monkeypatch):
    import hornlab_search.bo.metric_propose as propose_module
    monkeypatch.setattr(
        propose_module, "build_metric_acquisition",
        lambda *a, **k: SimpleNamespace(status="ok", reason="ok", acq=object(),
                                        timing_s=0.0, detail=None))
    monkeypatch.setattr(
        propose_module, "evaluate_metric_candidates",
        lambda *a, **k: SimpleNamespace(ok=True, status="ok", reason="ok", detail=None,
                                        values=np.array([0.5])))
    monkeypatch.setattr(
        propose_module, "predict_metric_components",
        lambda *a, **k: SimpleNamespace(
            status="ok", reason="ok", detail=None, j_mean=np.array([0.1]),
            component_mean=np.zeros((1, 4)), component_sd=np.zeros((1, 4)),
            j_sd=np.array([0.0]), flags=()))


def test_propose_requires_nonempty_matching_bounds_identity(monkeypatch):
    _patch_proposal(monkeypatch)
    encoding = Encoding()
    expected = bounds_identity(encoding)
    model, pool = _fake_model(), _fake_pool()

    missing = propose_metric_candidate(
        model, pool, policy=MetricProposalPolicy(bounds_hash=""),
        require_identity=True, expected_bounds_hash=expected)
    assert missing.status == "unavailable"
    assert missing.reason == REASON_BOUNDS_MISSING
    assert missing.candidate is None

    no_expected = propose_metric_candidate(
        model, pool, policy=MetricProposalPolicy(bounds_hash=expected),
        require_identity=True, expected_bounds_hash=None)
    assert no_expected.reason == REASON_BOUNDS_MISSING

    wrong = propose_metric_candidate(
        model, pool, policy=MetricProposalPolicy(bounds_hash="a" * 64),
        require_identity=True, expected_bounds_hash=expected)
    assert wrong.reason == REASON_BOUNDS_MISMATCH

    # An empty hash from a second available source is still a refusal.
    pool.bounds_hash = ""
    pool_missing = propose_metric_candidate(
        model, pool, policy=MetricProposalPolicy(bounds_hash=expected),
        require_identity=True, expected_bounds_hash=expected)
    assert pool_missing.reason == REASON_BOUNDS_MISSING


def test_propose_valid_identity_and_pass1_default_unchanged(monkeypatch):
    _patch_proposal(monkeypatch)
    encoding = Encoding()
    expected = bounds_identity(encoding)
    model, pool = _fake_model(), _fake_pool()

    strict = propose_metric_candidate(
        model, pool, policy=MetricProposalPolicy(bounds_hash=expected),
        require_identity=True, expected_bounds_hash=expected)
    assert strict.status == "ok"
    assert strict.bounds_hash == expected

    legacy = propose_metric_candidate(
        model, _fake_pool(), policy=MetricProposalPolicy(bounds_hash="bounds-v1"))
    assert legacy.status == "ok"
    assert legacy.bounds_hash == "bounds-v1"
