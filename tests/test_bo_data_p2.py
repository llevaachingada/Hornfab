"""Lane C P2: Bayesian data payloads for the GUI (model performance, sensitivity, proposal,
trust region, Pareto) plus the CPU-only diagnostics job registration.

These tests exercise the pure ``gui/data_bo.py`` projections against synthetic study
artifacts.  They need no torch/botorch: the diagnostics artifact is data, exactly as the GUI
reads it.
"""
from __future__ import annotations

import inspect
import io
import json
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.gui.data_bo import (
    DESIGNATION_VALUES,
    NOT_RECORDED,
    acoustic_target_integrity_view,
    calibration_view,
    model_performance_view,
    pareto_view,
    proposal_explanation_view,
    sensitivity_view,
    trust_region_view,
)
from hornlab_search.studies.service import StudyService


def _json_bytes(value):
    return json.dumps(value, allow_nan=False).encode()


def _study(root: Path, *, policy="scalar", question="p2 study"):
    service = StudyService(root)
    created = service.create_study(
        {"protocol": "bo-study-v1.1", "question": question,
         "policy": {"proposal_policy": policy, "seed": 7}}, "create")
    return service, created["id"]


def _attach(service, sid, kind, value, dependencies=None, key=None):
    content = value if isinstance(value, bytes) else _json_bytes(value)
    return service.attach_artifact(sid, 1, kind, content, dependencies or {}, key or kind)


def _trust_record(index, length, *, status="active", center=(1.0, 1.0, 1.0),
                  success=0, failure=0):
    return {
        "policy": "turbo_pool_v1", "proposal_index": index,
        "box": {"lo": [0.0, 0.0, 0.0], "hi": [0.5, 0.5, 0.5], "weights": [1.0, 1.0, 1.0]},
        "state_after": {
            "center": list(center), "length": length, "status": status,
            "success_counter": success, "failure_counter": failure, "iteration": index,
            "length_bounds": {"init": 0.8, "min": 0.5 ** 7, "max": 1.6},
        },
    }


def _fixture(tmp_path: Path, *, policy="scalar", with_diagnostics=True,
             with_pareto=False, with_trust_region=False, resolved_target=None):
    root = tmp_path / "registry"
    service, sid = _study(root, policy=policy)
    snapshot = _attach(service, sid, "snapshot", {
        "tool": "study-snapshot-v1", "status": "ok",
        "task": {"objective_version": 7, "resolved_target": resolved_target,
                 "brief_name": "p80x60_cov", "brief_sha256": "b" * 64},
        "source": {"scores_json": "scores.json"}, "cohort": {"scores": {"records": 4}},
    }, key="snapshot")
    manifest = {
        "tool": "study-training-manifest-v1", "status": "ok", "d": 3, "n": 4,
        "n_min": 2, "n_max": 256, "n_eligible": 4,
        "active_keys": ["L_mm", "a_deg", "morph_rate"],
        "ids": ["t1", "t2", "t3", "t4"], "excluded_ids": [],
        "task": {"objective_version": 7},
        "meta": {"identities": {
            "t1": {"design_hash": "dh1", "geometry_hash": "gh1"},
            "t2": {"design_hash": "dh2", "geometry_hash": "gh2"},
        }},
    }
    _attach(service, sid, "training_manifest", manifest,
            {"snapshot": snapshot["sha256"]}, key="manifest")
    training = io.BytesIO()
    np.savez_compressed(
        training,
        X=np.asarray([[0, 0, 0], [1, 1, 1], [0.5, 0.2, 0.8], [0.2, 0.7, 0.4]], float),
        J=np.asarray([4.0, 3.5, 3.2, 3.8], float))
    training_meta = _attach(
        service, sid, "training", training.getvalue(),
        {"training_manifest": service.get_artifact_metadata(sid, "training_manifest")["sha256"]},
        key="training")
    model = {
        "tool": "study-model-manifest-v1", "status": "ok", "policy": policy,
        "generated_utc": "2026-11-16T09:00:00+00:00",
        "library_versions": {"engine": "botorch", "torch": "2.6"},
        "hyperparameters": {"lengthscales": [0.1, 0.5, 2.0],
                            "lengthscale_bounds": [0.005, 4.0], "outputscale": 1.2},
    }
    _attach(service, sid, "model", model, key="model")
    candidate_predicted = ({"coverage_deg": {"mean": 1.5, "lower": 1.0, "upper": 2.0},
                            "ripple_db": {"mean": 0.6, "lower": 0.4, "upper": 0.8}}
                           if with_pareto else
                           {"j_mean": 3.0, "j_lower": 2.0, "j_upper": 4.0, "y_sd": 0.5,
                            "interval_label": "model credible interval", "nonphysical": False,
                            "flags": []})
    candidate = {
        "candidate_id": "c3", "design_hash": "d3", "geometry_hash": "g3",
        "x": [0.1, 0.2, 0.3], "active_vector": [0.1, 0.2, 0.3],
        "params": {"L_mm": 120.0, "a_deg": 45.0},
        "checks": {"schema": "passed", "envelope": "passed", "throat": "passed",
                   "materialized": True, "mesh_built": False, "bem_called": False},
        "status": "cheap-check-passed; mesh/acoustic eligibility unknown",
        "predicted": candidate_predicted,
    }
    proposal = {
        "tool": "study_proposal", "schema": "study-proposal-v1", "status": "ok",
        "proposal_policy": policy, "proposal_index": 3, "fallback": False,
        "selection_reason": "acquisition",
        "predicted": candidate_predicted, "candidate": candidate,
        "acquisition": {"value": 1.234, "units": "log qLogNEI (ranking only)",
                        "n_candidates": 100, "chunks": 2, "acq_seed": 7},
    }
    if with_trust_region:
        proposal["trust_region"] = _trust_record(0, 0.8, success=0, failure=0)
    _attach(service, sid, "proposal", proposal, key="proposal")
    observations = []
    values = [(3.0, 2.2, True, "success", 120.0, 40.0),
              (2.0, 2.6, True, "success", 100.0, 50.0),
              (4.0, None, False, "cheap_refusal", 90.0, 30.0),
              (3.0, 2.4, True, "success", 110.0, 42.0)]
    for index, (mean, measured, eligible, outcome, length, angle) in enumerate(values):
        predicted = ({"coverage_deg": {"mean": 1.0 + index, "lower": 0.8 + index,
                                       "upper": 1.2 + index},
                      "ripple_db": {"mean": 0.5 + index / 10, "lower": 0.4,
                                    "upper": 0.6}} if with_pareto else
                     {"j_mean": mean, "j_lower": mean - 0.7, "j_upper": mean + 0.7,
                      "interval_label": "model credible interval"})
        record = {}
        if with_trust_region:
            record["trust_region"] = _trust_record(
                0 if index == 0 else index, (0.8, 1.6, 0.4, 0.007)[index],
                status="collapsed" if index == 3 else "active",
                success=index, failure=0)
        observations.append({
            "candidate": {"candidate_id": f"c{index}", "design_hash": f"d{index}",
                          "x": ([0.1, 0.2, 0.3] if index == 0 else [0.7, 0.7, 0.7]),
                          "active_vector": ([0.1, 0.2, 0.3] if index == 0 else [0.7, 0.7, 0.7]),
                          "params": {"L_mm": length, "a_deg": angle},
                          "predicted": predicted, **record,
                          "selection_reason": "exploration" if index == 1 else "acquisition"},
            "result": {"kind": "screen", "eligible": eligible, "outcome": outcome,
                       "observed_j": measured, "solve_id": f"s{index}",
                       "design_hash": f"d{index}", "geometry_id": f"g{index}",
                       "physical_measurement": measured is not None,
                       "params": {"L_mm": length, "a_deg": angle},
                       "pareto_metric": ({"status": "complete", "coverage_deg": 1.0 + index,
                                          "ripple_db": 0.5 + index / 10}
                                         if with_pareto else None)},
        })
    observations.append({
        "candidate": {"candidate_id": "v1", "design_hash": "dv1"},
        "result": {"kind": "verify", "eligible": True, "outcome": "success",
                   "observed_j": 2.95, "solve_id": "v1", "design_hash": "dv1",
                   "physical_measurement": True},
    })
    _attach(service, sid, "results", {
        "status": "pool_exhausted", "observations": observations,
        "progress": {"screen_calls": 4, "verify_calls": 1},
    }, key="results")
    package = _attach(service, sid, "package", {
        "package_id": "pkg", "budget": {"screen_calls": 6, "verify_calls": 2},
        "budget_profile": "comparison-60", "lane": "gpu",
    }, key="package")
    if with_diagnostics:
        _attach(service, sid, "diagnostics", {
            "schema": "study-model-diagnostics-v1", "status": "ok",
            "generated_utc": "2026-11-16T11:00:00+00:00", "revision": 1,
            "model_revision": 1, "training_set_id": "ts1",
            "retrospective": True,
            "prediction_source": "refit_from_stored_training_set",
            "retrospective_note": "retrospective refit",
            "relevance": [{"key": "L_mm", "inv_lengthscale": 2.0, "rank": 1, "at_bound": False},
                          {"key": "a_deg", "inv_lengthscale": 1.0, "rank": 2, "at_bound": True}],
            "loo": {
                "label": "Efficient leave-one-out on the original training cohort",
                "method": "efficient_loo_cv (no refit)", "n": 3, "truncated": False,
                "rows": [{"id": "a", "j_obs": 1.0, "j_mean": 1.1, "j_sd": 0.2},
                         {"id": "b", "j_obs": 2.0, "j_mean": 1.8, "j_sd": 0.3},
                         {"id": "c", "j_obs": 3.0, "j_mean": 3.2, "j_sd": 0.1}],
                "summary": {"rmse": 0.2, "spearman": 1.0, "coverage_95": 0.667},
                "error": {"rmse": 0.2, "mae": 0.15, "mean_error": 0.0},
                "rank_correlation": 1.0,
                "interval_evidence": {"declared_interval": "±1.96σ LOO",
                                      "calibrated_95_supported": False,
                                      "empirical_coverage": 0.667, "n": 3},
            },
            "slices": {"anchor": "incumbent", "grid_n": 3, "per_key": {
                "L_mm": {"x": [100.0, 120.0, 140.0], "j_mean": [3.4, 3.0, 2.8],
                         "j_sd": [0.2, 0.2, 0.2], "anchor_x": 120.0, "unit": "mm",
                         "feasibility": {"checked": True, "status": "warned",
                                         "invalid_count": 1, "reason": "invalid at 140 mm"}},
                "a_deg": {"x": [30.0, 45.0, 60.0], "j_mean": [3.2, 3.0, 2.9],
                          "j_sd": [0.1, 0.2, 0.3], "anchor_x": 45.0, "unit": "deg"},
            }},
            "pareto": ({"front_ids": ["t1", "t2"],
                        "hv_trace": [{"seq": 1, "hv": 0.1}, {"seq": 2, "hv": 0.3}]}
                       if with_pareto else None),
        }, {"training": training_meta["sha256"]}, key="diagnostics")
    if with_pareto:
        _attach(service, sid, "pareto_metrics", {
            "status": "ok", "n_complete": 2, "n_excluded": 1,
            "reference": {"limits": [3.0, 1.0], "ref_point": [-3.0, -1.0],
                          "units": ["deg", "dB"], "direction": "minimize"},
            "reference_policy": "frozen once from the complete training rows",
            "metric_policy": {"physical_metric_spec_hash": "a" * 64},
            "observations": {
                "t1": {"status": "complete", "coverage_deg": 1.0, "ripple_db": 0.5},
                "t2": {"status": "complete", "coverage_deg": 2.0, "ripple_db": 0.2},
            },
            "excluded": {"t3": {"status": "incomplete", "reason": "missing band support",
                                "coverage_deg": None, "ripple_db": None}},
            "limitations": ["metric helper"],
        }, key="pareto_metrics")
    run_id = f"study-{package['sha256'][:16]}"
    (tmp_path / "runs").mkdir(exist_ok=True)
    (tmp_path / "runs" / run_id / "screen").mkdir(parents=True)
    (tmp_path / "runs" / run_id / "verify").mkdir(parents=True)
    return service, service.get_study(sid), tmp_path / "runs"


def test_calibration_separates_sequential_tracking_from_training_loo(tmp_path):
    service, study, _runs = _fixture(tmp_path)
    view = model_performance_view(service, study)
    assert {"sequential_validation", "efficient_loo_cv", "sections"} <= set(view)
    sequential = view["sequential_validation"]
    loo = view["efficient_loo_cv"]
    assert sequential["out_of_sample"] is True
    assert loo["out_of_sample"] is False
    assert "subsequently measured" in sequential["label"]
    assert "original training cohort" in loo["label"]
    assert sequential["n"] == 3 and sequential["n_with_interval"] == 3
    assert sequential["rank_correlation"] is not None
    assert sequential["error"]["rmse"] is not None
    assert sequential["interval_evidence"]["calibrated_95_supported"] is False
    assert "not presented as a calibrated" in sequential["interval_evidence"]["note"]
    assert loo["n"] == 3 and loo["rank_correlation"] == 1.0
    assert loo["model_provenance"]["retrospective"] is True
    assert loo["model_provenance"]["model_revision"] == 1
    assert loo["model_provenance"]["generated_utc"] == "2026-11-16T11:00:00+00:00"
    # Legacy renderer key stays intact.
    assert view["loo"]["available"] is True and view["loo"]["n"] == 3


def test_missing_diagnostics_is_not_recorded_not_zero(tmp_path):
    service, study, _runs = _fixture(tmp_path, with_diagnostics=False)
    view = calibration_view(service, study)
    loo = view["efficient_loo_cv"]
    assert loo["available"] is False and loo["status"] == NOT_RECORDED
    assert loo["n"] == NOT_RECORDED and loo["summary"] == NOT_RECORDED
    sens = sensitivity_view(service, study)
    assert sens["diagnostics"]["status"] == NOT_RECORDED
    for field in ("hyperparameters", "relevance", "posterior_slices", "loo", "pareto"):
        assert sens[field] == NOT_RECORDED
    # No fabricated zero-importance knob list.
    assert all(knob.get("importance") != 0 for knob in sens.get("knobs") or [])
    assert sens["diagnostics"]["can_compute"] is True


def test_sensitivity_slices_use_real_units_anchor_and_invalid_warning(tmp_path):
    service, study, _runs = _fixture(tmp_path)
    view = sensitivity_view(service, study)
    slices = {item["key"]: item for item in view["posterior_slices"]["items"]}
    lmm = slices["L_mm"]
    assert lmm["x"] == [100.0, 120.0, 140.0] and lmm["unit"] == "mm"
    assert lmm["anchor_x"] == 120.0
    assert lmm["j_lower"][0] == pytest.approx(3.0)
    assert lmm["j_upper"][0] == pytest.approx(3.8)
    assert lmm["feasibility_warning"]["status"] == "warned"
    assert lmm["feasibility_warning"]["invalid_count"] == 1
    assert lmm["labels"]["caveat"] == "model sensitivity, not a proven physical effect"
    assert lmm["labels"]["anchor"] == "other knobs held at incumbent"
    # A slice with no attached evaluation must say unknown, not "valid".
    assert slices["a_deg"]["feasibility_warning"]["status"] == "unknown"
    assert slices["a_deg"]["feasibility_warning"]["checked"] is False
    # Relevance bars carry rank/bound evidence and the model-only caveat.
    knobs = {knob["key"]: knob for knob in view["knobs"]}
    assert knobs["L_mm"]["rank"] == 1 and knobs["a_deg"]["at_bound"] is True
    assert knobs["L_mm"]["meaning"] == "model sensitivity, not a proven physical effect"
    assert view["model_provenance"]["retrospective"] is True


def test_proposal_explanation_payload(tmp_path):
    service, study, runs = _fixture(tmp_path)
    view = proposal_explanation_view(service, study, runs_root=runs)
    assert view["status"] == "ready"
    assert view["designation"] in DESIGNATION_VALUES
    assert view["designation"] == "exploitation"
    assert view["proposal_index"] == 3
    assert view["acquisition"]["is_ranking_signal"] is True
    assert view["acquisition"]["rank"] == 1
    assert "not measured horn quality" in view["acquisition"]["meaning"]
    assert view["predicted"]["kind"] == "scalar_j"
    assert view["predicted"]["j_lower"] == 2.0 and view["predicted"]["j_upper"] == 4.0
    assert view["nearest_training_designs"]["available"] is True
    assert view["nearest_training_designs"]["items"][0]["id"] == "t1"
    delta = view["parameter_delta_vs_incumbent"]
    # Incumbent is the best measured screen (a_deg 40); the proposal asks for 45.
    assert delta["available"] is True
    deltas = {item["key"]: item for item in delta["items"]}
    assert deltas["a_deg"]["delta"] == 5.0 and deltas["L_mm"]["delta"] == 0.0
    assert view["cheap_check_feasibility"]["checks"]["envelope"] == "passed"
    assert view["model_version"]["retrospective"] is False
    assert view["model_provenance"]["retrospective"] is False
    assert view["status_kinds"]["physical"]["summary"].startswith("measured:3")


def test_turbo_payload_has_events_center_identity_and_inside_outside(tmp_path):
    service, study, _runs = _fixture(tmp_path, policy="turbo", with_trust_region=True)
    view = trust_region_view(service, study)
    assert view["status"] == "ready"
    assert [step["length"] for step in view["length_over_attempts"]] == [
        0.8, 1.6, 0.4, 0.007]
    assert [step["change"] for step in view["length_over_attempts"]] == [
        None, "expansion", "shrink", "shrink"]
    assert view["expansion_steps"] and view["shrink_steps"]
    assert view["center"] == [1.0, 1.0, 1.0]
    assert view["center_identity"]["resolved"] is True
    assert view["center_identity"]["design_hash"] == "dh2"
    assert len(view["normalized_parameter_bounds"]) == 3
    assert view["normalized_parameter_bounds"][0]["space"] == "normalized active space"
    assert view["proposals_inside"] >= 1 and view["proposals_outside"] >= 1
    assert view["terminal"]["collapsed"] is True
    assert view["terminal"]["label"] == "converged"
    assert view["budget"]["used"] == 4 and view["budget"]["total"] == 6
    assert view["budget"]["unspent"] == 2


def test_pareto_payload_axes_exclusions_and_predicted_separation(tmp_path):
    service, study, runs = _fixture(tmp_path, policy="pareto", with_pareto=True)
    view = pareto_view(service, study, runs_root=runs)
    assert view["status"] == "ready"
    assert view["frontier_axes"]["x"] == "coverage_deg"
    assert view["frontier_axes"]["y"] == "ripple_db"
    assert "J" in view["frontier_axes"]["note"]
    assert view["nondominated"]
    assert all("j" in point for point in view["points"])
    assert view["excluded_points"][0]["observation_id"] == "t3"
    assert view["excluded_points"][0]["status"] == "incomplete"
    assert all(point["measured"] is True for point in view["points"])
    predicted = view["predicted"]
    assert predicted and predicted[0]["source"] == "predicted"
    assert predicted[0]["measured"] is False
    assert view["diagnostics"]["front_ids"] == ["t1", "t2"]
    assert view["hypervolume_trace"][-1] == [2, 0.3]


def test_status_kinds_distinguish_validation_from_physical(tmp_path):
    service, study, _runs = _fixture(tmp_path)
    view = calibration_view(service, study)
    kinds = view["status_kinds"]
    assert kinds["artifact_validation"] == "available"
    assert kinds["physical"]["summary"].startswith("measured:3")
    assert "artifact" in kinds["labels"]["artifact_validation"]
    # Artifact validation being ``available`` says nothing about a physical refusal.
    assert kinds["physical"]["refused"] == 1


def test_diagnose_job_is_registered_and_cpu_only():
    from hornlab_search.bo import diagnostics as D
    from hornlab_search.gui.study_jobs import KINDS

    assert "diagnose" in KINDS
    assert D.KIND == "diagnostics"
    assert D.PREDICTION_SOURCE == "refit_from_stored_training_set"
    source = inspect.getsource(D).lower()
    for token in ("torch.cuda", "cuda", "gpu"):
        assert token not in source, f"diagnostics module references {token!r}"
    block = D._unavailable("s", 1, "scalar", "no fit")
    assert block["retrospective"] is True
    assert block["prediction_source"] == D.PREDICTION_SOURCE


def test_slice_feasibility_block_never_implies_validity():
    from hornlab_search.bo.diagnostics import slice_feasibility_block

    assert slice_feasibility_block(None)["status"] == "unknown"
    assert slice_feasibility_block([True, None])["status"] == "unknown"
    assert slice_feasibility_block([True, False, True])["status"] == "warned"
    assert slice_feasibility_block([True, False, True])["invalid_count"] == 1
    assert slice_feasibility_block([True, True])["status"] == "clear"


def test_acoustic_target_integrity_uses_recorded_target_only(tmp_path):
    target = {"coverage_h_deg": 60.0, "coverage_v_deg": [45.0, 50.0, 55.0],
              "f0_hz": 800.0, "band_lo_hz": 500.0, "band_hi_hz": 12000.0}
    service, study, _runs = _fixture(tmp_path, resolved_target=target)
    view = acoustic_target_integrity_view(service, study)
    assert view["status"] == "ready" and view["scoring_target_available"] is True
    assert view["target"]["coverage_h_deg"] == 60.0
    assert view["target"]["coverage_v_deg"] == [45.0, 50.0, 55.0]
    assert view["target_identity"]["objective_version"] == 7
    assert view["target_identity"]["brief_sha256"] == "b" * 64
    assert view["separate_from_measurements"] is True
    assert "typology" in view["notes"][0]

    # An old snapshot without a resolved target says so; it is never guessed from the family.
    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    missing_service, missing_study, _runs = _fixture(missing_root)
    missing = acoustic_target_integrity_view(missing_service, missing_study)
    assert missing["status"] == "missing"
    assert missing["scoring_target_available"] is False
    assert missing["reason_code"] == "scoring_target_unavailable"
    assert missing["target"] == NOT_RECORDED
