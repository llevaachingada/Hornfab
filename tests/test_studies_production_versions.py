"""Objective v10/v11 production-study compatibility (opt-in registry, explicit dispatch).

No BoTorch, no solver: these are unit checks on the task registry, the admission gate, and the
version-specific training metric identity.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from hornlab_search.config import load_config
from hornlab_search.objective.replay import brief_from_config
from hornlab_search.studies import builders, production
from hornlab_search.studies.schema import Unavailable

V10_TASK = (builders.COMPACT400_V10XO_TASK_NAME, builders.COMPACT400_V10XO_CONFIG,
            builders.COMPACT400_V10XO_BRIEF, 10)
V10_HOME_TASK = (builders.HOME_V10_TASK_NAME, builders.HOME_V10_CONFIG,
                 builders.HOME_V10_BRIEF, 10)
V11_TASK = (builders.HOME900_V11CD_TASK_NAME, builders.HOME900_V11CD_CONFIG,
            builders.HOME900_V11CD_BRIEF, 11)


def test_registry_registers_the_new_version_tasks(tmp_path):
    assert builders.registered_objective_versions() == frozenset({4, 7, 10, 11})
    for name, config, brief, version in (V10_TASK, V10_HOME_TASK, V11_TASK):
        entry = builders._TASK_REGISTRY[name]
        assert entry == {"config": config, "brief": brief, "objective_version": version}
        assert name in builders._ALLOWED_TASK_NAMES
        resolved = builders._read_task({"name": name}, root=tmp_path)
        assert resolved["config"] == config
        assert resolved["brief"] == brief
        assert resolved["objective_version"] == version
        cfg = load_config(config)
        assert cfg.objective_version == version
        assert brief_from_config(config).objective_version == version
        assert builders.registered_task_for(version, str(config), str(brief)) is entry
        # The config's own brief_file resolves to the same registered brief.
        from hornlab_search.objective.replay import load_brief_context
        resolved_brief = load_brief_context(brief)
        assert resolved_brief.objective_version == version


def test_registry_matching_does_not_alias_another_brief(tmp_path):
    assert builders.registered_task_for(
        10, str(builders.COMPACT400_V10XO_CONFIG), str(builders.HOME900_V11CD_BRIEF)) is None
    assert builders.registered_task_for(10, None, None) is None
    assert builders.registered_task_for("not-a-version", "a", "b") is None


def test_admission_accepts_v4_v7_and_the_registered_tasks():
    v4 = builders.DEFAULT_CONFIG
    assert production.objective_admission(
        load_config(v4), {"config": str(v4), "brief": str(builders.DEFAULT_BRIEF)}) is None
    v7 = builders.HOME_CONFIG
    assert production.objective_admission(
        load_config(v7), {"config": str(v7), "brief": str(builders.HOME_BRIEF)}) is None
    for _name, config, brief, _version in (V10_TASK, V10_HOME_TASK, V11_TASK):
        assert production.objective_admission(
            load_config(config), {"config": str(config), "brief": str(brief)}) is None


def test_admission_refuses_an_unregistered_version():
    reason = production.objective_admission(SimpleNamespace(objective_version=9), {})
    assert reason is not None and "registered v10/v11" in reason
    reason = production.objective_admission(SimpleNamespace(objective_version=6), {})
    assert reason is not None and "registered v10/v11" in reason


def test_admission_refuses_a_registered_version_with_an_unregistered_pair():
    cfg = load_config(builders.COMPACT400_V10XO_CONFIG)
    reason = production.objective_admission(
        cfg, {"config": str(builders.COMPACT400_V10XO_CONFIG),
              "brief": str(builders.HOME900_V11CD_BRIEF)})
    assert reason is not None and "registered study task" in reason
    assert production.objective_admission(cfg, {}) is not None


def test_admission_refuses_an_unfreezable_metric_policy(monkeypatch):
    def boom(*args, **kwargs):
        raise ValueError("objective block is malformed")

    monkeypatch.setattr("hornlab_search.bo.metrics.freeze_metric_policy_for_version", boom)
    reason = production.objective_admission(
        load_config(builders.HOME900_V11CD_CONFIG),
        {"config": str(builders.HOME900_V11CD_CONFIG),
         "brief": str(builders.HOME900_V11CD_BRIEF)})
    assert reason is not None and "cannot be frozen" in reason


def _derived(tmp_path, base_config, brief, *, mutate=None, name="derived.yaml"):
    """A matched-benchmark arm config: copy the registered task, replace the brief path,
    and change only declared search metadata (unless ``mutate`` changes task identity)."""
    raw = yaml.safe_load(Path(base_config).read_text(encoding="utf-8"))
    raw.pop("brief", None)
    raw["brief_file"] = str(brief)
    if mutate is not None:
        mutate(raw)
    path = tmp_path / name
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def test_derived_config_with_unchanged_task_identity_is_admitted(tmp_path):
    """The matched-benchmark orchestrator derives arm configs under its own output dir.

    Only the search treatment may differ; the registered task identity must still admit it.
    """
    for version, config, brief, name in (
        (10, builders.COMPACT400_V10XO_CONFIG, builders.COMPACT400_V10XO_BRIEF, "v10.yaml"),
        (10, builders.HOME_V10_CONFIG, builders.HOME_V10_BRIEF, "v10home.yaml"),
        (11, builders.HOME900_V11CD_CONFIG, builders.HOME900_V11CD_BRIEF, "v11.yaml"),
    ):
        derived = _derived(tmp_path, config, brief, name=name,
                           mutate=lambda raw: raw["search"].update(
                               {"sigma0": 0.21, "seed": 777}))
        match = builders.registered_task_match(version, str(derived), str(brief))
        assert match is not None and match["basis"] == "derived_task_identity"
        assert production.objective_admission(
            load_config(derived), {"config": str(derived), "brief": str(brief)}) is None


@pytest.mark.parametrize("mutate", [
    lambda raw: raw["mesh"].update({"quadrants": "14"}),
    lambda raw: raw["bounds"][sorted(raw["bounds"])[0]].update(
        {"lo": float(raw["bounds"][sorted(raw["bounds"])[0]]["lo"]) + 1.0}),
])
def test_derived_config_with_changed_task_identity_is_refused(tmp_path, mutate):
    derived = _derived(tmp_path, builders.COMPACT400_V10XO_CONFIG,
                       builders.COMPACT400_V10XO_BRIEF, mutate=mutate)
    assert builders.registered_task_match(
        10, str(derived), str(builders.COMPACT400_V10XO_BRIEF)) is None
    reason = production.objective_admission(
        load_config(derived),
        {"config": str(derived), "brief": str(builders.COMPACT400_V10XO_BRIEF)})
    assert reason is not None and "registered study task" in reason


def test_derived_config_with_a_different_brief_is_refused(tmp_path):
    derived = _derived(tmp_path, builders.COMPACT400_V10XO_CONFIG,
                       builders.COMPACT400_V10XO_BRIEF)
    assert builders.registered_task_match(
        10, str(derived), str(builders.HOME900_V11CD_BRIEF)) is None


def _tiny_dataset(root: Path, *, version: int, grid=None):
    dataset = root / "dataset"
    (dataset / "shard-0000").mkdir(parents=True, exist_ok=True)
    np.savez(dataset / "shard-0000" / "rec-0000.npz",
             freqs_hz=np.asarray(grid if grid is not None else
                                 [350.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0]))
    (dataset / "shard-0000.jsonl").write_text(
        json.dumps({"objective_version": version, "design_hash": "d0", "solve_hash": "s0"}) + "\n",
        encoding="utf-8")
    training = SimpleNamespace(ids=("row-0",),
                               meta={"identities": {"row-0": {"shard": 0, "row": 0}}})
    return dataset, training


def test_training_metric_identity_carries_the_version_specific_hash(tmp_path):
    dataset, training = _tiny_dataset(tmp_path, version=11)
    task = {"config": str(builders.HOME900_V11CD_CONFIG), "objective_version": 11}
    identity = builders._training_metric_identity(
        task, training, {"dataset_root": str(dataset)})
    assert identity is not None
    assert identity["objective_version"] == 11
    assert identity["schema"] == "bo-physical-metric-v11/1"
    assert len(identity["physical_metric_spec_hash"]) == 64
    assert identity["cd"]["band_hz"] == [900.0, 8000.0]
    assert "hornlab_search.objective.scalar_v11" in identity["code_sha256"]

    dataset10, training10 = _tiny_dataset(tmp_path / "v10", version=10)
    task10 = {"config": str(builders.COMPACT400_V10XO_CONFIG), "objective_version": 10}
    identity10 = builders._training_metric_identity(
        task10, training10, {"dataset_root": str(dataset10)})
    assert identity10 is not None
    assert identity10["schema"] == "bo-physical-metric-v10/1"
    assert identity10["physical_metric_spec_hash"] != identity["physical_metric_spec_hash"]
    assert "cd" not in identity10


def test_training_metric_identity_is_absent_for_v4_and_v7(tmp_path):
    dataset, training = _tiny_dataset(tmp_path, version=4)
    for config, version in ((builders.DEFAULT_CONFIG, 4), (builders.HOME_CONFIG, 7)):
        identity = builders._training_metric_identity(
            {"config": str(config), "objective_version": version}, training,
            {"dataset_root": str(dataset)})
        assert identity is None


def test_training_metric_identity_rejects_mixed_objective_versions(tmp_path):
    dataset, training = _tiny_dataset(tmp_path, version=10)   # stored rows say v10
    with pytest.raises(Unavailable, match="mix objective versions"):
        builders._training_metric_identity(
            {"config": str(builders.HOME900_V11CD_CONFIG), "objective_version": 11},
            training, {"dataset_root": str(dataset)})
