from copy import deepcopy

import pytest

from hornlab_search.bo.cohort import POLICY_FIELDS, validate_cohort
from hornlab_search.bo.data import build_training_set


def row(i=0):
    target = {"coverage_h_deg": 50, "di_target_db": None}
    catalog = {"source": {"root": "dataset", "shard_index": 1, "row": i},
               "record_sha256": "record", "design_hash": f"design{i}", "ok": True,
               "config_name": "native", "backend": "beat", "fidelity": "screen",
               "grid_hash": "grid", "dependency_hash": "deps", "excitation": {"type": "piston"},
               "unknowns": []}
    replay = {"shard": 1, "row": i, "status": "exact_complete", "complete": True,
              "objective_version": 4, "physical_id": f"physical{i}", "metric_id": f"metric{i}",
              "score_id": f"score{i}", "metric_source": "recomputed", "design_hash": f"design{i}",
              "j": 2. + i, "target": target, "weights": {"cov": 1.},
              "diagnostics": {"ripple_used_response": True}}
    policy = {k: {"namespace": "test.policy", "value": f"{k}-v1", "evidence": f"source:{i}"} for k in POLICY_FIELDS}
    for k, ns, val in (("task", "s0.config_name", "native"), ("target", "r0.target", target),
                       ("resolved_brief", "r0.resolved_brief_hash", "full-r0-hash"),
                       ("backend", "s0.backend", "beat"), ("fidelity", "s0.fidelity", "screen"),
                       ("frequency_grid", "s0.grid_hash", "grid"), ("dependencies", "s0.dependency_hash", "deps"),
                       ("excitation", "s0.excitation", {"type": "piston"})):
        policy[k] = {"namespace": ns, "value": val, "evidence": f"source:{i}"}
    return {"catalog": catalog, "replay": replay, "replay_root": "dataset", "policy": policy, "x": [0.2, 0.3]}


def test_distinct_physical_ids_with_equal_evidenced_policy_are_accepted():
    result = validate_cohort([row(0), row(1)], d=2)
    assert result.ok, result.reasons
    assert len(result.observations) == 2
    assert result.observations[0].solve_hash == "physical0"
    assert build_training_set(result.observations, d=2).status == "needs_initial_data"


@pytest.mark.parametrize("field", POLICY_FIELDS)
def test_each_missing_policy_refuses_all_training(field):
    a, b = row(0), row(1)
    del b["policy"][field]
    result = validate_cohort([a, b], d=2)
    assert result.status == "capability_missing" and not result.observations


def test_cross_row_mismatch_and_unknown_provenance_refuse():
    a, b = row(0), row(1)
    b["policy"]["frequency_masks"]["value"] = "different"
    assert validate_cohort([a, b], d=2).status == "incompatible"
    b = row(1)
    b["catalog"]["unknowns"] = ["dependency_sha_unknown"]
    assert validate_cohort([a, b], d=2).status == "capability_missing"
    b = row(1)
    b["replay"]["score_id"] = None
    assert validate_cohort([a, b], d=2).status == "capability_missing"


def test_no_brief_hash_namespace_conflation_or_bad_join():
    a = row()
    a["policy"]["resolved_brief"]["namespace"] = "s0.brief_hash"
    assert validate_cohort([a], d=2).status == "incompatible"
    a = row()
    a["replay"]["row"] = 99
    assert validate_cohort([a], d=2).status == "incompatible"


def test_partial_and_conflicting_physical_provenance_refuse():
    a, b = row(0), row(1)
    b["replay"]["status"] = "partial_unsupported"
    assert validate_cohort([a, b], d=2).status == "incompatible"
    b = row(1)
    b["replay"]["physical_id"] = a["replay"]["physical_id"]
    assert validate_cohort([a, b], d=2).status == "incompatible"
