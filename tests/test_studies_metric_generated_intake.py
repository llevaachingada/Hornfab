"""Generated-space records enter the offline metric intake through their recorded recipe.

A real archived Room 90x50/c500 row is wrapped in a one-row catalog/replay/shard intake. The
positive path proves the record is reconstructed AND encoded; it then stops at the documented
``needs_initial_data`` selection floor (one row is below ``n_min``). Every failure path is checked
before selection. Native OSSE behaviour is unchanged.
"""
import copy
import csv
import hashlib
import io
import json

import pytest

from conftest import EXAMPLES
from hornlab_search.bo.encoding import HashMismatchError
from hornlab_search.config import load_config
from hornlab_search.design.generated import design_from_recipe
from hornlab_search.design.space import DesignSpace
from hornlab_search.studies import metric_intake as mi
from hornlab_search.studies.schema import Unavailable
from test_design_generated_recipe import C500, C500_CONFIG

BRIEF = (EXAMPLES / "briefs" / "compact500_xo900_2026-11-20"
         / "compact500_xo900_80x50_hf1440_v11cd_open_2026-11-22.yaml")
RUN_ID = "20261122T223153Z-screen-98b41d"


@pytest.fixture(scope="module")
def archived():
    space = DesignSpace.from_config(load_config(C500_CONFIG))
    design = design_from_recipe(space, C500["generator"],
                                expected_design_hash=C500["design_hash"])
    meta = {
        "design_hash": C500["design_hash"],
        "family": "FREEFORM",
        "params": design.params,
        "objective": C500["objective"],
        "terms": C500["terms"],
        "objective_version": 11,
        "ok": True,
        "run_id": RUN_ID,
        "config_name": "r3_c500",
        "created_utc": "2026-11-22T22:32:38Z",
        "provenance": {
            "config": "r3_c500",
            "brief": C500["generator"]["brief"],
            "brief_hash": C500["generator"]["brief_hash"],
            "generator": copy.deepcopy(C500["generator"]),
        },
    }
    return space, meta


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pin(path):
    return {"path": str(path.resolve()), "sha256": _sha(path)}


def _intake(tmp_path, metas):
    """One-shard pinned intake around the supplied shard metadata rows."""
    config = C500_CONFIG.resolve()
    brief = BRIEF.resolve()
    identity = {
        "task_identity": "task-generated-test",
        "backend": "beat_cuda",
        "fidelity": "screen",
        "grid_hash": "gridhash-generated",
        "dependency_hash": "dephash-generated",
        "mesh_hash": "meshhash-generated",
        "brief_hash": C500["generator"]["brief_hash"],
        "score_hash": "scorehash-generated",
    }
    shard_lines = []
    catalog_rows = []
    replay_rows = []
    for row, meta in enumerate(metas):
        shard_lines.append(json.dumps(meta))
        oid = f"pid-{row:04d}"
        catalog_rows.append({
            "shard_index": 0, "row": row, "config_name": "r3_c500", "run_id": meta["run_id"],
            "task_identity": identity["task_identity"], "backend": identity["backend"],
            "fidelity": identity["fidelity"], "grid_hash": identity["grid_hash"],
            "dependency_hash": identity["dependency_hash"], "mesh_hash": identity["mesh_hash"],
            "brief_hash": identity["brief_hash"], "score_identity": identity["score_hash"],
            "objective_version": 11, "physical_solve_id": oid,
            "solve_hash": f"sol-{row:04d}", "design_hash": meta["design_hash"],
        })
        replay_rows.append({
            "shard": 0, "row": row, "status": "exact_complete", "complete": True,
            "config_name": "r3_c500", "catalog_run_id": meta["run_id"],
            "design_hash": meta["design_hash"], "j": meta["objective"],
        })

    shard = tmp_path / "shard-0000.jsonl"
    shard.write_text("\n".join(shard_lines) + "\n", encoding="utf-8")
    catalog = tmp_path / "catalog.csv"
    fields = ["shard_index", "row", "config_name", "run_id", "task_identity", "backend",
              "fidelity", "grid_hash", "dependency_hash", "mesh_hash", "brief_hash",
              "score_identity", "objective_version", "physical_solve_id", "solve_hash",
              "design_hash"]
    with catalog.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(catalog_rows)
    replay = tmp_path / "replay.json"
    replay.write_text(json.dumps({"rows": replay_rows}), encoding="utf-8")

    intake = {
        "config": _pin(config), "brief": _pin(brief), "catalog": _pin(catalog),
        "replay": _pin(replay), "shards": {"0": _pin(shard)}, "identity": identity,
    }
    snapshot = {"task": {"config": str(config), "config_sha256": _sha(config),
                         "brief": str(brief), "brief_sha256": _sha(brief),
                         "objective_version": 11}}
    return intake, snapshot


def test_generated_record_is_reconstructed_and_encoded(tmp_path, monkeypatch, archived):
    _space, meta = archived
    intake, snapshot = _intake(tmp_path, [meta])
    real = mi.select_metric_training_observations
    captured = {}

    def spy(records, *, encoding, policy=None):
        captured["records"] = list(records)
        return real(records, encoding=encoding, policy=policy)

    monkeypatch.setattr(mi, "select_metric_training_observations", spy)
    # One row is below the documented n_min floor, so selection refuses with needs_initial_data;
    # reaching that point proves the recipe was re-materialised, hash-checked and encoded.
    with pytest.raises(Unavailable, match="offline metric selection refused: needs_initial_data"):
        mi.select_offline_metric_cohort(intake, snapshot=snapshot)
    assert len(captured["records"]) == 1
    candidate = captured["records"][0]
    assert candidate.design_hash == C500["design_hash"]
    assert candidate.x.shape == (10,)
    assert candidate.components is not None and candidate.component_names
    assert candidate.cd_status == "balloon"


def test_legacy_generated_record_without_recipe_is_refused(tmp_path, archived):
    _space, meta = archived
    meta = copy.deepcopy(meta)
    del meta["provenance"]["generator"]
    intake, snapshot = _intake(tmp_path, [meta])
    with pytest.raises(Unavailable, match="has no generator recipe proof"):
        mi.select_offline_metric_cohort(intake, snapshot=snapshot)


@pytest.mark.parametrize("mutation,match", [
    (lambda knobs: knobs.pop("g_L_mm"), "knob set differs"),
    (lambda knobs: knobs.__setitem__("g_extra", 1.0), "knob set differs"),
])
def test_missing_or_extra_knob_is_refused(tmp_path, archived, mutation, match):
    _space, meta = archived
    meta = copy.deepcopy(meta)
    mutation(meta["provenance"]["generator"]["knobs"])
    intake, snapshot = _intake(tmp_path, [meta])
    with pytest.raises(Unavailable, match=match):
        mi.select_offline_metric_cohort(intake, snapshot=snapshot)


def test_changed_fixed_value_is_refused(tmp_path, archived):
    _space, meta = archived
    meta = copy.deepcopy(meta)
    meta["provenance"]["generator"]["knobs"]["g_q"] = 0.995
    intake, snapshot = _intake(tmp_path, [meta])
    with pytest.raises(Unavailable, match="pinned generator knob 'g_q' changed"):
        mi.select_offline_metric_cohort(intake, snapshot=snapshot)


def test_out_of_box_knob_is_refused(tmp_path, archived):
    _space, meta = archived
    meta = copy.deepcopy(meta)
    meta["provenance"]["generator"]["knobs"]["g_L_mm"] = 10_000.0
    intake, snapshot = _intake(tmp_path, [meta])
    with pytest.raises(Unavailable, match="outside its resolved bound"):
        mi.select_offline_metric_cohort(intake, snapshot=snapshot)


def test_geometry_hash_mismatch_is_refused(tmp_path, archived):
    _space, meta = archived
    meta = copy.deepcopy(meta)
    meta["design_hash"] = "000000000000"
    intake, snapshot = _intake(tmp_path, [meta])
    with pytest.raises(Unavailable, match="re-materialised design hash"):
        mi.select_offline_metric_cohort(intake, snapshot=snapshot)


def test_encoding_round_trip_failure_is_refused(tmp_path, monkeypatch, archived):
    _space, meta = archived
    intake, snapshot = _intake(tmp_path, [meta])
    real = mi._task_encoding

    class _Refusing:
        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def normalize_design(self, design, *, verify_round_trip=True):
            raise HashMismatchError("simulated round-trip failure")

    monkeypatch.setattr(mi, "_task_encoding", lambda space: _Refusing(real(space)))
    with pytest.raises(Unavailable, match="invalid offline metric intake"):
        mi.select_offline_metric_cohort(intake, snapshot=snapshot)


def test_generated_meta_on_a_native_task_is_refused(archived):
    _space, meta = archived
    native = DesignSpace.from_config(load_config(EXAMPLES / "rosse_baseline.yaml"))
    with pytest.raises(Unavailable, match="task is not generated"):
        mi._historical_design(native, meta, (0, 0), {})


def test_native_meta_keeps_the_historical_path():
    native = DesignSpace.from_config(load_config(EXAMPLES / "rosse_baseline.yaml"))
    meta = {"family": "R-OSSE", "params": {"r0_mm": 12.7}}
    design = mi._historical_design(native, meta, (0, 0), {})
    assert design.family == "R-OSSE"
    assert design.params == {"r0_mm": 12.7}
