import io
import json
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.gui.data_bo import (
    bo_views,
    calibration_view,
    convergence_view,
    data_summary_view,
    design_space_view,
    method_board_view,
    pareto_view,
    sensitivity_view,
    trust_region_view,
    verification_view,
)
from hornlab_search.gui.study_index import StudyIndex
from hornlab_search.studies.service import StudyService


def _json_bytes(value):
    return json.dumps(value, allow_nan=False).encode()


def _study(root: Path, *, policy="scalar", question="test study"):
    service = StudyService(root)
    created = service.create_study(
        {"protocol": "bo-study-v1.1", "question": question,
         "policy": {"proposal_policy": policy, "seed": 7}}, "create")
    return service, created["id"]


def _attach(service, sid, kind, value, dependencies=None, key=None):
    content = value if isinstance(value, bytes) else _json_bytes(value)
    return service.attach_artifact(sid, 1, kind, content, dependencies or {}, key or kind)


def _fixture(tmp_path: Path, *, policy="scalar", with_predictions=True,
             with_hyperparameters=True, with_pareto=False, with_trust_region=False):
    root = tmp_path / "registry"
    service, sid = _study(root, policy=policy)
    snapshot = _attach(service, sid, "snapshot", {
        "tool": "study-snapshot-v1", "status": "ok",
        "task": {"objective_version": 7},
        "source": {"scores_json": "scores.json", "catalog_csv": "catalog.csv",
                   "dataset_root": "dataset"},
        "cohort": {"scores": {"records": 4, "ok": 4, "failed": 0}},
    }, key="snapshot")
    manifest = {
        "tool": "study-training-manifest-v1", "status": "ok", "d": 3, "n": 4, "n_min": 2,
        "n_max": 256, "n_eligible": 4, "active_keys": ["L_mm", "a_deg", "morph_rate"],
        "ids": ["t1", "t2", "t3", "t4"], "excluded_ids": [],
        "subset_policy": {"rule": "64 lowest-J + 192 maximin"},
        "task": {"objective_version": 7},
        "meta": {"identities": {
            "t1": {"design_hash": "t1", "shard": 0, "row": 1},
            "t2": {"design_hash": "t2", "shard": 0, "row": 2},
        }},
    }
    _attach(service, sid, "training_manifest", manifest,
            {"snapshot": snapshot["sha256"]}, key="manifest")
    training = io.BytesIO()
    np.savez_compressed(training, X=np.asarray([[0, 0, 0], [1, 1, 1], [0.5, 0.2, 0.8],
                                                [0.2, 0.7, 0.4]], dtype=float),
                        J=np.asarray([4.0, 3.5, 3.2, 3.8], dtype=float))
    _attach(service, sid, "training", training.getvalue(),
            {"training_manifest": service.get_artifact_metadata(sid, "training_manifest")["sha256"]},
            key="training")
    model = {
        "tool": "study-model-manifest-v1", "status": "ok", "policy": policy,
        "library_versions": {"engine": "botorch", "available": True},
        "limitations": ["manifest identity only"],
        "model_state_persisted": with_hyperparameters,
    }
    if with_hyperparameters:
        model["hyperparameters"] = {
            "lengthscales": [0.1, 0.5, 2.0],
            "lengthscale_bounds": [0.005, 4.0],
            "outputscale": 1.2,
        }
    _attach(service, sid, "model", model, key="model")
    candidate = {"candidate_id": "c1", "design_hash": "d1", "geometry_hash": "g1",
                 "x": [0.1, 0.2, 0.3], "active_vector": [0.1, 0.2, 0.3],
                 "predicted": ({"j_mean": 3.0, "j_lower": 2.0, "j_upper": 4.0,
                                "interval_label": "model credible interval"}
                               if with_predictions else None)}
    _attach(service, sid, "proposal", {
        "tool": "study-proposal", "schema": "study-proposal-v1", "status": "ok",
        "proposal_policy": policy, "predicted": candidate["predicted"],
        "candidate": candidate,
        **({"trust_region": {
            "policy": "turbo_pool_v1", "proposal_index": 0,
            "box": {"lo": [0.0, 0.1, 0.2], "hi": [0.4, 0.5, 0.6],
                    "weights": [1.0, 1.0, 1.0]},
            "state_after": {"length": 0.8, "status": "active",
                            "success_counter": 1, "failure_counter": 0,
                            "iteration": 0, "length_bounds": {"min": 0.0078125, "max": 1.6}},
        }} if with_trust_region else {}),
    }, key="proposal")
    observations = []
    values = [(3.0, 2.2, True, "success"), (2.0, 2.6, True, "success"),
              (4.0, None, False, "cheap_refusal"), (3.0, 2.4, True, "success")]
    for index, (mean, measured, eligible, outcome) in enumerate(values):
        predicted = ({"j_mean": mean, "j_lower": mean - 0.7, "j_upper": mean + 0.7,
                      "interval_label": "model credible interval"} if with_predictions else None)
        observations.append({
            "candidate": {"candidate_id": f"c{index}", "design_hash": f"d{index}",
                          "x": [index / 4, 0.2, 0.3], "predicted": predicted,
                          "selection_reason": "exploration" if index == 1 else "acquisition",
                          **({"trust_region": {
                              "proposal_index": index,
                              "state_after": {"length": 0.8 - index * 0.2,
                                              "status": "collapsed" if index == 3 else "active",
                                              "success_counter": index,
                                              "failure_counter": 0,
                                              "iteration": index,
                                              "length_bounds": {"min": 0.0078125, "max": 1.6}},
                              "box": {"lo": [0.0, 0.1, 0.2], "hi": [0.4, 0.5, 0.6],
                                      "weights": [1.0, 1.0, 1.0]},
                          }} if with_trust_region else {})},
            "result": {"kind": "screen", "eligible": eligible, "outcome": outcome,
                       "observed_j": measured, "solve_id": f"s{index}",
                       "design_hash": f"d{index}", "geometry_id": f"g{index}",
                       "physical_id": f"p{index}",
                       "pareto_metric": ({"status": "complete", "coverage_deg": 1.0 + index,
                                          "ripple_db": 0.5 + index / 10,
                                          "physical_metric_spec_hash": "a" * 64}
                                         if with_pareto else None)}
        })
    observations.append({
        "candidate": {"candidate_id": "v1", "design_hash": "dv1", "x": [0.2, 0.3, 0.4]},
        "result": {"kind": "verify", "eligible": False, "outcome": "success",
                   "observed_j": 2.95, "solve_id": "v1", "design_hash": "dv1"},
    })
    _attach(service, sid, "results", {
        "status": "pool_exhausted", "package_id": "pkg", "observations": observations,
        "progress": {"screen_calls": 4, "verify_calls": 1, "total_calls": 5,
                     "attempts": 5, "unresolved": False},
    }, key="results")
    package = _attach(service, sid, "package", {
        "package_id": "pkg", "budget": {"screen_calls": 6, "verify_calls": 2,
                                        "total_calls": 8, "attempts": 20},
        "budget_profile": "comparison-60", "lane": "gpu",
        "deadline": "2026-11-16T00:00:00+00:00",
    }, key="package")
    if with_pareto:
        _attach(service, sid, "pareto_metrics", {
            "status": "ok", "n_complete": 2, "n_excluded": 0,
            "reference": {"limits": [3.0, 1.0], "ref_point": [-3.0, -1.0],
                          "units": ["deg", "dB"], "direction": "minimize"},
            "metric_policy": {"physical_metric_spec_hash": "a" * 64},
            "observations": {
                "t1": {"status": "complete", "coverage_deg": 1.0, "ripple_db": 0.5},
                "t2": {"status": "complete", "coverage_deg": 2.0, "ripple_db": 0.2},
            },
            "reference_policy": "frozen once",
            "limitations": ["metric helper"],
        }, key="pareto_metrics")
    _attach(service, sid, "verification", {
        "status": "ok", "selection": {"finalists": ["g1"], "audits": ["g2"],
                                      "shortfall": 0, "audit_shortfall": 0},
        "verified_geometry_ids": ["g1", "g2"],
    }, key="verification")
    run_id = f"study-{package['sha256'][:16]}"
    run_dir = tmp_path / "runs" / run_id
    (run_dir / "screen").mkdir(parents=True)
    (run_dir / "verify").mkdir(parents=True)
    screen_rows = []
    for index, objective in enumerate((4.0, 3.5, 3.2, 3.8)):
        screen_rows.append({"n": index, "mode": "screen", "ok": True, "objective": objective,
                            "objective_version": 7, "seconds": {"total": 10.0 + index}})
    (run_dir / "screen" / "search.ndjson").write_text(
        "\n".join(json.dumps(row) for row in screen_rows), encoding="utf-8")
    (run_dir / "verify" / "search.ndjson").write_text(
        "\n".join(json.dumps({"ok": True, "objective": value, "mode": "verify",
                              "seconds": {"total": 30.0}})
                  for value in (2.9, 3.1)), encoding="utf-8")
    study = service.get_study(sid)
    return service, study, tmp_path / "runs"


def test_views_are_derived_from_recorded_rows(tmp_path):
    service, study, runs = _fixture(tmp_path)
    convergence = convergence_view(service, study, runs_root=runs)
    assert convergence["status"] == "partial"
    assert convergence["objective_version"] == 7
    arm = convergence["arms"][0]
    assert arm["screens"] == 4 and arm["best_j"] == pytest.approx(2.2)
    assert arm["refusals"] and arm["exploration"]
    assert convergence["eta"]["screen_seconds_each"] == pytest.approx(11.5)
    assert convergence["run"]["run_id"].startswith("study-")

    calibration = calibration_view(service, study)
    assert calibration["status"] == "ready" and calibration["n"] == 3
    assert 0 <= calibration["coverage"] <= 1
    assert calibration["spearman"] is not None

    sensitivity = sensitivity_view(service, study)
    assert sensitivity["status"] == "ready"
    assert [k["key"] for k in sensitivity["knobs"]][0] == "L_mm"
    assert sum(k["importance"] for k in sensitivity["knobs"]) == pytest.approx(1.0)

    data = data_summary_view(service, study, runs_root=runs)
    assert data["status"] == "ready" and data["objective_version"] == 7
    assert data["training"]["active_keys"] == ["L_mm", "a_deg", "morph_rate"]

    space = design_space_view(service, study)
    assert space["status"] == "ready" and len(space["points"]) >= 3
    assert sum(space["explained"]) <= 1.0
    assert verification_view(service, study)["status"] == "ready"


def test_missing_instrumentation_is_explicit_not_invented(tmp_path):
    service, study, runs = _fixture(tmp_path, with_predictions=False, with_hyperparameters=False)
    calibration = calibration_view(service, study)
    assert calibration["status"] == "missing"
    assert "next analyze/propose" in calibration["reason"]
    sensitivity = sensitivity_view(service, study)
    assert sensitivity["status"] == "missing"
    assert "hyperparameters" in sensitivity["reason"]
    trust = trust_region_view(service, study)
    assert trust["status"] == "not_applicable"
    pareto = pareto_view(service, study, runs_root=runs)
    assert pareto["status"] == "not_applicable"

    turbo_service, turbo_study, _runs = _fixture(tmp_path / "turbo", policy="turbo",
                                                  with_trust_region=True)
    trust = trust_region_view(turbo_service, turbo_study)
    assert trust["status"] == "ready"
    assert len(trust["length_series"]) >= 2
    assert trust["terminal"]["collapsed"] is True
    assert trust["box"] and len(trust["box"]["lo"]) == 3


def test_pareto_view_builds_a_frontier_and_hypervolume(tmp_path):
    service, study, runs = _fixture(tmp_path, policy="pareto", with_pareto=True)
    view = pareto_view(service, study, runs_root=runs)
    assert view["status"] == "ready"
    assert view["reference"]["limits"] == [3.0, 1.0]
    assert any(point["nondominated"] for point in view["points"])
    assert view["hypervolume"] is not None and view["hypervolume"] > 0
    assert any(point.get("finalist") for point in view["points"])


def test_bo_views_are_phase_scoped_and_bounded(tmp_path):
    service, study, runs = _fixture(tmp_path, policy="turbo", with_trust_region=True)
    execute = bo_views(service, study, phase="execute", runs_root=runs)
    assert set(execute) >= {"phase", "run", "convergence", "trust_region", "pareto"}
    assert execute["trust_region"]["status"] == "ready"
    assert execute["pareto"]["status"] == "not_applicable"
    explain = bo_views(service, study, phase="explain", runs_root=runs)
    assert set(explain) >= {"phase", "calibration", "sensitivity", "design_space"}
    assert "convergence" not in explain
    assert len(json.dumps(execute, allow_nan=False)) <= 128_000


def test_method_board_applies_the_declared_rule(tmp_path):
    service, study, runs = _fixture(tmp_path)
    spec = {
        "name": "test board", "objective_version": 7, "target_j": 3.3,
        "incumbent": {"j": 3.3, "label": "prior"},
        "comparisons": [{"id": "bo-vs-cma", "a": "bo", "b": "cma",
                         "rule": "verify_median_gap_exceeds_spread"}],
        "arms": [
            {"id": "bo1", "method": "bo", "label": "BO 1",
             "study_root": "registry", "study_id": study["id"]},
            {"id": "bo2", "method": "bo", "label": "BO 2",
             "study_root": "registry", "study_id": study["id"]},
            {"id": "cma1", "method": "cma", "label": "CMA 1", "run": "cma-a"},
            {"id": "cma2", "method": "cma", "label": "CMA 2", "run": "cma-b"},
        ],
    }
    for name, objective in (("cma-a", 3.6), ("cma-b", 3.5)):
        path = runs / name
        path.mkdir(parents=True)
        (path / "search.ndjson").write_text(json.dumps({"ok": True, "objective": objective}),
                                            encoding="utf-8")
        (path / "verify").mkdir()
        (path / "verify" / "search.ndjson").write_text(
            json.dumps({"ok": True, "objective": objective}), encoding="utf-8")
    index = StudyIndex(tmp_path, primary_root=tmp_path / "registry")
    board = method_board_view(spec, root=tmp_path, runs_root=runs,
                              service_for=index.service_for_path)
    assert board["status"] == "ready"
    assert board["methods"]["bo"]["median_verify_j"] == pytest.approx(2.9)
    assert board["methods"]["cma"]["median_verify_j"] == pytest.approx(3.55)
    assert board["comparisons"][0]["verdict"] == "bo"
    assert board["arms"][0]["screens_to_target"] is not None
