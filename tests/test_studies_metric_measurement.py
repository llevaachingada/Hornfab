from dataclasses import replace
from types import SimpleNamespace

import pytest

from hornlab_search.objective.replay import ReplayResult, STATUS_EXACT_COMPLETE
from hornlab_search.objective.scalar_v11 import CD_STATUS_CUTS_FALLBACK, resolve_v11_weights
from hornlab_search.dataset.identity_v2 import physical_solve_id
from hornlab_search.studies.evaluator import (bind_metric_record_identity, load_metric_dataset_record,
                                             record_metric_measurement)
from test_bo_metric_training import V11_WEIGHTS, _v11_terms


@pytest.fixture
def measured_v11():
    j, terms, params = _v11_terms()
    result = {"kind": "screen", "eligible": True, "call_status": "called", "observed_j": j,
              "design_hash": "geometry", "solve_id": "attempt-solve"}
    replay = ReplayResult(status=STATUS_EXACT_COMPLETE, reasons=(), physical_id="physical",
                          metric_id="metrics", score_id="score", objective_version=11,
                          metric_source="stored", design_hash="geometry", j=j, stored_j=j,
                          terms=terms.copy())
    brief = SimpleNamespace(objective_version=11, weights=V11_WEIGHTS, objective_params=params)
    return result, terms, replay, brief


def test_fresh_canonical_v11_screen_produces_six_labels(measured_v11):
    result, terms, replay, brief = measured_v11
    measured = record_metric_measurement(result, terms, replay, brief=brief)
    assert measured["eligible"] is True
    assert measured["physical_id"] == replay.physical_id
    assert measured["metric_id"] == replay.metric_id
    assert measured["score_id"] == replay.score_id
    assert measured["cd_status"] == "balloon"
    assert len(measured["components"]) == 6
    assert sum(measured["components"]) == pytest.approx(replay.j)


@pytest.mark.parametrize("change", [{"call_status": "not_called"}, {"kind": "verify"}])
def test_cached_or_verify_rows_cannot_train(measured_v11, change):
    result, terms, replay, brief = measured_v11
    skipped = record_metric_measurement({**result, **change}, terms, replay, brief=brief)
    assert not skipped["eligible"] and "components" not in skipped
    assert skipped["metric_refusal"] == "not_new_eligible_screen"


@pytest.mark.parametrize(("change", "reason"), [
    ({"design_hash": "wrong"}, "replay_identity_mismatch"),
    ({"stored_j": None}, "replay_score_mismatch"),
    ({"objective_version": 10}, "replay_identity_mismatch"),
    ({"status": "approximate"}, "replay_identity_mismatch"),
])
def test_replay_identity_and_stored_j_match_the_fresh_measurement(measured_v11, change, reason):
    result, terms, replay, brief = measured_v11
    refused = record_metric_measurement(result, terms, replace(replay, **change), brief=brief)
    assert not refused["eligible"] and "components" not in refused
    assert refused["metric_refusal"] == reason


def test_cuts_fallback_cannot_supply_a_live_label(measured_v11):
    result, terms, replay, brief = measured_v11
    live_terms = {**terms, "cd_status_code": CD_STATUS_CUTS_FALLBACK}
    refused = record_metric_measurement(result, live_terms, replay, brief=brief)
    assert not refused["eligible"] and "components" not in refused
    assert refused["metric_refusal"] == "live:cd_cuts_fallback"


def test_equal_total_with_changed_components_cannot_train(measured_v11):
    result, terms, replay, brief = measured_v11
    weights = resolve_v11_weights(brief.weights, brief.objective_params)
    changed = {**terms, "cd_lw": terms["cd_lw"] + 0.001 / weights["cd_lw"],
               "offaxis_smooth": terms["offaxis_smooth"] - 0.001 / weights["offaxis_smooth"]}
    refused = record_metric_measurement(result, terms, replace(replay, terms=changed), brief=brief)
    assert not refused["eligible"] and "components" not in refused
    assert refused["metric_refusal"] == "replay_component_mismatch"


def test_dataset_reference_binds_persisted_physics_separately_from_replay(measured_v11, tmp_path):
    result, terms, replay, brief = measured_v11
    physical_key = {"design_hash": result["design_hash"], "mesh_hash": "mesh", "solve_hash": "spec"}
    result.update(physical_key)
    dataset = {**physical_key, "ok": True, "objective_version": 11, "objective": replay.j,
               "run_id": "screen", "solve": {"mode": "screen"}, "terms": terms}
    store = SimpleNamespace(root=tmp_path, read=lambda shard, row: (dataset, {"response": [0.0]}))

    meta, reference = load_metric_dataset_record(store, (4, 9), result, run_id="screen", version=11)
    labeled = record_metric_measurement(result, meta["terms"], replay, brief=brief, dataset_record=reference)
    assert labeled["eligible"] is True
    assert labeled["physical_id"] == replay.physical_id
    assert labeled["metric_dataset_record"] == {"root": str(tmp_path), "shard": 4, "row": 9,
        "physical_solve_id": physical_solve_id(result["design_hash"], "mesh", "spec")}

    with pytest.raises(ValueError, match="dataset_record_missing"):
        load_metric_dataset_record(store, None, result, run_id="screen", version=11)
    with pytest.raises(ValueError, match="dataset_record_identity_mismatch"):
        load_metric_dataset_record(store, (4, 9), result, run_id="different", version=11)
    dataset["objective"] += 0.01
    with pytest.raises(ValueError, match="dataset_record_score_mismatch"):
        load_metric_dataset_record(store, (4, 9), result, run_id="screen", version=11)


def test_same_j_under_a_different_grid_or_brief_is_refused(smoke_cfg):
    from hornlab_search.bo.metric_training import bounds_identity
    from hornlab_search.dataset.catalog_identity import catalog_identity_from_record
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.studies.builders import _task_encoding

    space = DesignSpace.from_config(smoke_cfg)
    encoding = _task_encoding(space)
    design = space.seed
    bounds = bounds_identity(encoding)
    result = {"design_hash": design.hash(), "x": encoding.normalize_design(design).tolist()}
    meta = {"objective_version": 11, "family": design.family, "params": design.params,
            "design_hash": design.hash(), "mesh_hash": "mesh", "solve_hash": "solve",
            "provenance": {"brief": "fold", "brief_hash": "c6bc496e7b4f"},
            "terms": {"total": 5.0, "cd_lw": 1.0}, "lib_shas": {"hornlab_mesher": "mesher"},
            "solve": {"backend": "beat_cuda", "mode": "screen", "freqs_hz": [700.0, 8000.0]}}
    actual = catalog_identity_from_record(meta)
    expected = {k: actual[k] for k in ("task_identity", "grid_hash", "dependency_hash", "mesh_hash",
                                      "backend", "fidelity", "brief_hash", "score_hash")}
    assert bind_metric_record_identity(meta, result, expected=expected, encoding=encoding,
                                       bounds_hash=bounds)["bounds_hash"] == bounds
    with pytest.raises(ValueError, match="metric_task_identity_mismatch:grid_hash"):
        changed = {**meta, "solve": {**meta["solve"], "freqs_hz": [900.0, 8000.0]}}
        bind_metric_record_identity(changed, result, expected=expected, encoding=encoding, bounds_hash=bounds)
    with pytest.raises(ValueError, match="metric_task_identity_mismatch:brief_hash,score_hash,task_identity"):
        changed = {**meta, "provenance": {**meta["provenance"], "brief_hash": "c6bc496e7b5f"}}
        bind_metric_record_identity(changed, result, expected=expected, encoding=encoding, bounds_hash=bounds)
    with pytest.raises(ValueError, match="metric_proposal_projection_mismatch"):
        changed = {**result, "x": [*result["x"], 0]}
        bind_metric_record_identity(meta, changed, expected=expected, encoding=encoding, bounds_hash=bounds)
