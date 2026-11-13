"""S8 manifest-driven QD / Pareto comparison tests."""
from __future__ import annotations

import json

import pytest

from hornlab_search.types import Design

from test_tools_analysis_common import load_tool, run_cli, run_json_payload

qd = load_tool("qd_compare")


def _manifest(arm: str, points, *, algorithm="cma_me", failed=(), refused=(), training=2,
              reference=(5.0, 5.0), version=4, scoring_context_id="score-context-v4"):
    def result(kind, i, p, error, ok):
        design = {"family": "OSSE", "params": {"L_mm": 200.0 + i, "tag": kind}}
        return {"id": f"{arm}-{kind}-{i}", "design": design,
                "design_hash": Design(family="OSSE", params=design["params"]).hash(),
                "reconstruction_hash": qd.reconstruction_hash(design),
                "objectives": list(p), "error": error, "terms": {}, "ok": ok}
    results = [
        result("ok", i, p, "", True)
        for i, p in enumerate(points)
    ]
    results += [
        result("fail", i + len(points), p, "solve_failed: synthetic", False)
        for i, p in enumerate(failed)
    ]
    results += [
        result("refuse", i + len(points) + len(failed), p, "invalid_geometry: synthetic", False)
        for i, p in enumerate(refused)
    ]
    successful = len(points)
    total = successful + len(failed) + len(refused) + training
    return {
        "schema": "qd-compare-arm-v1", "arm_id": arm, "algorithm": algorithm,
        "identity": {"objective_version": version,
                     "scoring_context_id": scoring_context_id,
                     "task_id": "task-physical-v1", "spec_id": "screen-spec-v1",
                     "brief_id": "brief-native-v4", "family": "OSSE",
                     "weights": {"coverage": 1.0, "ripple": 1.0},
                     "tolerances": {"coverage": 0.05, "ripple": 0.5}},
        "axes": [
            {"name": "coverage_error_deg", "unit": "deg", "direction": "minimize"},
            {"name": "ripple_db", "unit": "dB", "direction": "minimize"},
        ],
        "frozen_reference": list(reference),
        "descriptor_space": {"names": ["mouth_aspect", "area_ratio"],
                             "ranges": [[0.25, 4.0], [1.0, 500.0]],
                             "reconstruction_hash": f"{arm}-archive-inputs"},
        "cost": {"unit": "equivalent_evaluations", "successful": successful,
                 "failed": len(failed), "refused": len(refused), "training": training,
                 "other": 0, "total": total,
                 "checkpoints": [{"label": "final", "after_results": len(results),
                    "successful": successful, "failed": len(failed),
                    "refused": len(refused), "training": training, "other": 0,
                    "total": total}]},
        "results": results,
    }


def test_known_front_hypervolume_and_f1_failure_exclusion():
    # Known minimisation front: (1,4), (2,2), (4,1); (3,3) is dominated.
    # Against frozen reference (5,5), exact dominated hypervolume is 4 + 6 + 1 = 11.
    # The tempting (0,0) failure must not enter either the front or hypervolume.
    a = _manifest("me", [(1, 4), (2, 2), (4, 1), (3, 3)],
                  failed=[(0, 0)], training=2)
    b = _manifest("pareto", [(1, 4), (2, 2), (4, 1), (3, 3)],
                  algorithm="nsga2", failed=[(0, 0)], training=2)
    report = qd.compare_manifests(a, b)
    assert report["equal_cost"]["total"] == 7
    assert [arm["hypervolume"] for arm in report["arms"]] == [pytest.approx(11.0)] * 2
    assert [[p["objectives"] for p in arm["front"]] for arm in report["arms"]] == [
        [[1.0, 4.0], [2.0, 2.0], [4.0, 1.0]],
        [[1.0, 4.0], [2.0, 2.0], [4.0, 1.0]],
    ]
    assert report["arms"][0]["excluded_ids"] == ["me-fail-4"]


def test_training_and_failure_costs_are_part_of_equal_cost_gate():
    a = _manifest("a", [(1, 2)], failed=[(0, 0)], training=2)
    b = _manifest("b", [(1, 2)], failed=[(0, 0)], training=1)
    with pytest.raises(SystemExit) as exc:
        qd.compare_manifests(a, b)
    assert exc.value.code == 2


@pytest.mark.parametrize("field,value", [
    ("objective_version", 6), ("scoring_context_id", "other-score-context"),
    ("task_id", "other-task"), ("spec_id", "other-spec"),
])
def test_identity_mismatch_is_refused(field, value):
    a = _manifest("a", [(1, 2)])
    b = _manifest("b", [(1, 2)])
    b["identity"][field] = value
    with pytest.raises(SystemExit) as exc:
        qd.compare_manifests(a, b)
    assert exc.value.code == 2


def test_reference_is_frozen_shared_and_strictly_worse():
    a = _manifest("a", [(1, 2)])
    b = _manifest("b", [(1, 2)], reference=(6, 5))
    with pytest.raises(SystemExit):
        qd.compare_manifests(a, b)
    b = _manifest("b", [(5, 2)])
    with pytest.raises(SystemExit):
        qd.compare_manifests(a, b)


def test_scalar_j_and_meh_are_refused():
    a = _manifest("a", [(1, 2)])
    b = _manifest("b", [(1, 2)])
    a["axes"][0] = {"name": "J", "unit": "score", "direction": "minimize"}
    with pytest.raises(SystemExit):
        qd.compare_manifests(a, b)
    a = _manifest("a", [(1, 2)])
    a["identity"]["family"] = "MEH"
    with pytest.raises(SystemExit):
        qd.compare_manifests(a, b)


def test_cost_ledger_must_match_classified_results():
    a = _manifest("a", [(1, 2)], failed=[(0, 0)])
    a["cost"]["failed"] = 0
    a["cost"]["total"] -= 1
    with pytest.raises(SystemExit):
        qd.compare_manifests(a, _manifest("b", [(1, 2)], failed=[(0, 0)]))


def test_duplicate_geometry_is_charged_but_front_deduplicated():
    a = _manifest("a", [(1, 2)])
    duplicate = dict(a["results"][0], id="a-retry")
    a["results"].append(duplicate)
    a["cost"]["successful"] += 1
    a["cost"]["total"] += 1
    a["cost"]["checkpoints"][0].update(
        after_results=2, successful=2, total=a["cost"]["total"])
    b = _manifest("b", [(1, 2)])
    b_duplicate = dict(b["results"][0], id="b-retry")
    b["results"].append(b_duplicate)
    b["cost"]["successful"] += 1
    b["cost"]["total"] += 1
    b["cost"]["checkpoints"][0].update(
        after_results=2, successful=2, total=b["cost"]["total"])
    report = qd.compare_manifests(a, b)
    assert report["arms"][0]["n_eligible_attempts"] == 2
    assert report["arms"][0]["n_eligible"] == 1
    assert report["arms"][0]["duplicate_eligible_attempt_ids"] == ["a-retry"]


def test_reconstruction_and_ok_contract_are_verified():
    a = _manifest("a", [(1, 2)])
    b = _manifest("b", [(1, 2)])
    a["results"][0]["reconstruction_hash"] = "arbitrary"
    with pytest.raises(SystemExit):
        qd.compare_manifests(a, b)
    a = _manifest("a", [(1, 2)])
    a["results"][0]["ok"] = "yes"
    with pytest.raises(SystemExit):
        qd.compare_manifests(a, b)
    a = _manifest("a", [(1, 2)])
    a["results"][0].update(ok=True, error="solve_failed: contradictory")
    with pytest.raises(SystemExit):
        qd.compare_manifests(a, b)


def test_ok_false_empty_error_is_unknown_failure_not_complete():
    a = _manifest("a", [(1, 2)])
    a["results"][0].update(ok=False, error="")
    a["cost"].update(successful=0, failed=1)
    a["cost"]["checkpoints"][0].update(successful=0, failed=1)
    b = _manifest("b", [(1, 2)])
    b["results"][0].update(ok=False, error="")
    b["cost"].update(successful=0, failed=1)
    b["cost"]["checkpoints"][0].update(successful=0, failed=1)
    report = qd.compare_manifests(a, b)
    assert report["arms"][0]["n_eligible"] == 0
    assert report["arms"][0]["outcome_categories"] == {"unknown_error": 1}


def test_zdt1_known_front_and_dominated_point():
    xs = [0.0, 0.25, 1.0]
    front = [[x, 1.0 - x ** 0.5] for x in xs]
    a = _manifest("a", front + [[0.75, 0.75]], reference=(1.1, 1.1))
    b = _manifest("b", front + [[0.75, 0.75]], reference=(1.1, 1.1))
    report = qd.compare_manifests(a, b)
    assert [p["objectives"] for p in report["arms"][0]["front"]] == front


def test_cli_writes_json_and_markdown(tmp_path):
    a = _manifest("me", [(1, 4), (2, 2), (4, 1)])
    b = _manifest("pareto", [(1, 4), (2, 2), (4, 1)], algorithm="nsga2")
    ap, bp = tmp_path / "a.json", tmp_path / "b.json"
    ap.write_text(json.dumps(a), encoding="utf-8")
    bp.write_text(json.dumps(b), encoding="utf-8")
    cp = run_cli("qd_compare", ["--a", str(ap), "--b", str(bp)], tmp_path)
    assert cp.returncode == 0, cp.stderr
    report = run_json_payload(tmp_path / "out", "qd_compare")
    assert report["tool"] == "qd_compare"
    assert report["arms"][0]["hypervolume"] == pytest.approx(11.0)
    assert len(report["input_manifests"]["a"]["sha256"]) == 64
    assert "Equal-cost QD / Pareto comparison" in (tmp_path / "out" / "qd_compare.md").read_text()
