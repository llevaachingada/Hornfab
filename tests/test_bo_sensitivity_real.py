"""Real-artifact loader + M2 proposal evidence tests; no solver, GPU or mesher call.

These tests exercise the documented real-data entry point in
``tools/analysis/bo_sensitivity.py``.  The committed native artifact is read (numpy only),
tamper/refusal paths are checked, and the proposal record is assembled from synthetic
selection data.  The only optional-engine test (noise-floor scaling) runs in the isolated
BoTorch venv and skips honestly where BoTorch is absent.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from tools.analysis.bo_sensitivity import (
    _build_proposal_artifact,
    _fit_with_noise_multiplier,
    load_native_training_set,
    run_real_diagnostics,
)

REPO = Path(__file__).resolve().parents[1]
ARTIFACT_JSON = (REPO / "docs" / "evidence" / "bo_study_2026-11-12"
                 / "b2_native" / "native_trainingset.json")

HAS_BOTORCH = importlib.util.find_spec("botorch") is not None
requires_botorch = pytest.mark.skipif(
    not HAS_BOTORCH, reason="optional BoTorch engine (isolated bayes venv) absent")


# ------------------------------------------------------------------ fixtures / fakes


def _synthetic_training_set(n: int = 30, d: int = 2):
    from hornlab_search.bo.data import TrainingSet

    rng = np.random.default_rng(0)
    X = rng.random((n, d))
    J = rng.random(n) + 0.1
    ids = tuple(f"id-{i:04d}" for i in range(n))
    return TrainingSet(
        status="ok", d=d, n=n, X=X, J=J.reshape(-1, 1), Y=-J.reshape(-1, 1),
        Y_phys=None, G=None, ids=ids, selected_ids=ids, excluded_ids=(),
        elite_ids=ids, maximin_ids=(), n_eligible=n, n_unique=n,
        n_min=max(16, 2 * (d + 1)), n_max=256, active_keys=("a", "b"),
        projection_version="synthetic-projection", preparation=None)


def _fake_fit(training_set, multiplier):
    from hornlab_search.bo.model import ModelFitResult

    variance = float(np.var(np.asarray(training_set.J)))
    return ModelFitResult(
        status="ok", reason="ok", d=training_set.d, n=training_set.n, model=object(),
        s2_original=variance, train_Yvar_original=1e-6 * variance * float(multiplier),
        train_ids=tuple(training_set.ids))


def _fake_predict(model_result, X):
    return np.full(len(X), 0.5, dtype=float)


def _fake_propose(model_result, seed):
    return {
        "status": "ok",
        "candidate_id": f"candidate-{seed}",
        "geometry_hash": f"geometry-{seed}",
        "selection_reason": "acquisition",
        "predicted": {"j_mean": 0.5, "j_lower": 0.1, "j_upper": 0.9},
        "acquisition": {"value": -1.0, "units": "ranking diagnostic"},
    }


def _copy_artifact(tmp_path: Path) -> Path:
    target = tmp_path / ARTIFACT_JSON.name
    shutil.copy2(ARTIFACT_JSON, target)
    shutil.copy2(ARTIFACT_JSON.with_suffix(".npz"), target.with_suffix(".npz"))
    return target


# ------------------------------------------------------------------ real artifact loader


def test_load_native_artifact_shape_hashes_and_missing_groups():
    loaded = load_native_training_set(ARTIFACT_JSON)
    assert loaded["status"] == "ok", loaded.get("reason")
    training = loaded["training"]
    provenance = loaded["provenance"]

    assert (training.n, training.d) == (197, 13)
    assert training.X.shape == (197, 13)
    assert np.all(np.isfinite(training.X))
    assert np.all(np.isfinite(training.J))
    assert np.array_equal(training.Y, -training.J)
    assert len(training.selected_ids) == 197
    assert provenance["hashes_verified"] is True
    assert provenance["n_unique_design_hashes"] == 192
    assert provenance["objective_versions"] == [4]
    assert provenance["solve_hash_groups"] == {"3181879c7477": 192,
                                               "4d7ec3ee2758": 5}
    assert provenance["projection_version"] == "active-projection-v1"
    assert provenance["independent_groups_available"] is False
    assert any("no independent run/resume group identity" in note
               for note in loaded["limitations"])


def test_load_native_artifact_refuses_tampered_hash_and_cohort(tmp_path):
    path = _copy_artifact(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["hashes"]["x_sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    refused = load_native_training_set(path)
    assert refused["status"] == "unavailable"
    assert "hash mismatch" in refused["reason"]

    cohort_dir = tmp_path / "cohort"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    path = _copy_artifact(cohort_dir)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["config"] = str(tmp_path / "other__config.yaml")
    path.write_text(json.dumps(payload), encoding="utf-8")
    refused = load_native_training_set(path)
    assert refused["status"] == "unavailable"
    assert "cohort config" in refused["reason"]


def test_load_native_artifact_refuses_mixed_objective_versions(tmp_path):
    path = _copy_artifact(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    first = next(iter(payload["identities"]))
    payload["identities"][first]["stored_objective_version"] = 5
    path.write_text(json.dumps(payload), encoding="utf-8")
    refused = load_native_training_set(path)
    assert refused["status"] == "unavailable"
    assert "mixed objective versions" in refused["reason"]


# ------------------------------------------------------------------ descriptive diagnostics


def test_real_diagnostics_descriptive_without_groups_records_noise_and_pools():
    training = _synthetic_training_set()
    report = run_real_diagnostics(
        training_set=training, cohort_ids=["same"] * training.n,
        fit=_fake_fit, predict=_fake_predict, propose=_fake_propose,
        diagnostic_caps=(16, 24), noise_multipliers=(0.1, 1.0, 10.0),
        pool_seeds=(11, 12))
    assert report["status"] == "complete_descriptive"
    assert report["validation_mode"] == "descriptive_no_independent_groups"
    assert report["gate_pass"] is None
    assert report["cohort"]["independent_groups_available"] is False

    # Every prespecified noise multiplier is recorded and never used to select.
    assert {cell["noise_multiplier"] for cell in report["fits"]} == {0.1, 1.0, 10.0}
    assert all(cell["not_used_for_selection"] for cell in report["fits"])
    assert all(cell["status"] == "ok" for cell in report["fits"])

    names = {subset["name"] for subset in report["subsets"]}
    assert {"frozen_subset", "all_eligible", "stratified_by_J_cap16"} <= names
    for subset in report["subsets"]:
        assert set(subset["retained_ids"]).isdisjoint(subset["excluded_ids"])
        assert len(subset["retained_ids"]) == subset["n"]

    # Two independent pool seeds, both real proposal records at the production multiplier.
    assert {proposal["pool_seed"] for proposal in report["proposals"]} == {11, 12}
    assert all(proposal["geometry_hash"] for proposal in report["proposals"])
    assert {proposal["noise_multiplier"] for proposal in report["proposals"]} == {1.0}

    comparison = report["comparison_preparation"]
    assert comparison["status"] == "preparation_only_off_policy_retrospective"
    assert comparison["cma_seed"]["status"] == "unmeasured"
    assert comparison["space_filling"]["status"] == "not_computed"
    json.dumps(report, allow_nan=False)


def test_real_diagnostics_refuses_missing_groups_and_mixed_cohorts():
    training = _synthetic_training_set()
    refused = run_real_diagnostics(training_set=training, require_groups=True)
    assert refused["status"] == "unavailable"
    assert refused["reason_code"] == "capability_missing"
    assert refused["fits"] == [] and refused["proposals"] == []

    mixed = run_real_diagnostics(
        training_set=training, cohort_ids=["a"] * (training.n - 1) + ["b"])
    assert mixed["status"] == "unavailable"
    assert mixed["reason_code"] == "capability_missing"


def test_real_diagnostics_capability_missing_is_tagged_not_fabricated():
    from hornlab_search.bo.model import ModelFitResult

    training = _synthetic_training_set()

    def missing_fit(training_set, multiplier):
        return ModelFitResult(status="unavailable", reason="capability_missing",
                              d=training_set.d, n=training_set.n)

    report = run_real_diagnostics(
        training_set=training, cohort_ids=["same"] * training.n,
        fit=missing_fit, predict=_fake_predict, propose=_fake_propose,
        diagnostic_caps=(16,), pool_seeds=(11, 12))
    assert report["status"] == "capability_missing"
    assert report["reason_code"] == "capability_missing"
    assert all(cell["status"] == "unavailable"
               and cell["model_reason"] == "capability_missing"
               for cell in report["fits"])
    assert report["proposals"] == []
    json.dumps(report, allow_nan=False)


@requires_botorch
def test_noise_multiplier_scales_train_yvar_and_is_restored():
    from hornlab_search.bo import model as model_mod
    from hornlab_search.bo.data import build_training_set, make_pure_observations

    training = build_training_set(make_pure_observations(3, 40, seed=1), d=3)
    base = _fit_with_noise_multiplier(training, 1.0)
    low = _fit_with_noise_multiplier(training, 0.1)
    high = _fit_with_noise_multiplier(training, 10.0)
    assert base.status == low.status == high.status == "ok"
    assert low.s2_original == pytest.approx(base.s2_original)
    assert low.train_Yvar_original / base.train_Yvar_original == pytest.approx(
        0.1, rel=1e-6)
    assert high.train_Yvar_original / base.train_Yvar_original == pytest.approx(
        10.0, rel=1e-6)
    # The production floor is restored after every diagnostic fit.
    assert model_mod.NOISE_FLOOR_MULTIPLIER == 1e-6


# ------------------------------------------------------------------ proposal artifact


def _candidate():
    from hornlab_search.bo.data import PoolCandidate

    return PoolCandidate(
        candidate_id="candidate-0", pool_index=0, seed=20261112,
        active_vector=np.array([0.1, 0.2, 0.3]), full_vector=np.array([0.1, 0.2, 0.3]),
        design_hash="design-0", geometry_hash="geometry-0",
        intended_solve_hash="solve-0", params={"a": 1.0}, descriptors={}, checks={})


def _selection(index: int = 0) -> dict:
    return {
        "status": "ok",
        "reason": "ok",
        "model": {"model_policy": "scalar_pool_v1", "library_versions": {}},
        "selection": {
            "proposal_index": index,
            "next_proposal_index": index + 1,
            "selection_reason": "acquisition" if (index + 1) % 4 else "exploration",
            "predicted": {
                "j_mean": 3.0, "j_lower": 2.02, "j_upper": 3.98,
                "y_mean": -3.0, "y_sd": 0.5,
                "interval_label": ("model credible interval: marginal mu +/- 1.96*sigma "
                                   "from the latent posterior (observation_noise=False)"),
                "observation_noise": False, "flags": [],
            },
            "acquisition": {
                "value": -0.5,
                "units": ("log qLogNEI acquisition score (ranking diagnostic only; not "
                          "predicted J, not a probability of success)"),
                "acq_seed": 0,
            },
            "counts": {"legal": 10},
            "seeds_tried": [20261112],
        },
    }


def test_proposal_artifact_sign_units_cadence_and_no_measured_rows():
    artifact = _build_proposal_artifact(
        selection=_selection(0), candidate=_candidate(),
        training={"training_set_id": "training-0"},
        pool={"status_note": "cheap-check-passed; mesh/acoustic eligibility unknown"},
        encoding={"active_keys": ["a", "b", "c"]},
        config={"objective_version": 4}, validation={"status": "ok"})
    assert artifact["status"] == "ok"
    predicted = artifact["predicted"]
    assert predicted["j_lower"] <= predicted["j_mean"] <= predicted["j_upper"]
    assert predicted["j_mean"] == -predicted["y_mean"]
    assert predicted["interval_lower_negative"] is False
    assert "model credible interval" in predicted["interval_label"]
    assert "ranking diagnostic" in artifact["acquisition"]["units"]
    assert artifact["candidate"]["key_order"] == ["a", "b", "c"]
    assert artifact["predictions_appended_to_measured_rows"] is False
    assert artifact["selection"]["exploration_cadence"]["every"] == 4
    assert artifact["selection"]["exploration_cadence"]["index_is_exploration"] is False
    assert artifact["selection"]["exploration_cadence"]["exploration_indices"] == [3]
    assert artifact["pool"]["status_note"] == (
        "cheap-check-passed; mesh/acoustic eligibility unknown")
    json.dumps(artifact, allow_nan=False)

    exploration = _build_proposal_artifact(
        selection=_selection(3), candidate=_candidate(),
        training={"training_set_id": "training-0"}, pool={},
        encoding={"active_keys": ["a", "b", "c"]},
        config={"objective_version": 4}, validation={"status": "ok"})
    assert exploration["selection"]["selection_reason"] == "exploration"
    assert exploration["selection"]["exploration_cadence"]["index_is_exploration"] is True


def test_proposal_artifact_model_unavailable_is_tagged_without_predictions():
    selection = {
        "status": "unavailable",
        "reason": "capability_missing",
        "model": {"status": "unavailable", "reason": "capability_missing"},
        "selection": {
            "proposal_index": 0,
            "next_proposal_index": 1,
            "candidate_id": "candidate-0",
            "geometry_hash": "geometry-0",
            "predicted": None,
            "acquisition": None,
        },
    }
    artifact = _build_proposal_artifact(
        selection=selection, candidate=_candidate(), training={}, pool={},
        encoding={"active_keys": ["a", "b", "c"]}, config={"objective_version": 4},
        validation={"status": "not_run"})
    assert artifact["status"] == "capability_missing"
    assert artifact["reason_code"] == "capability_missing"
    assert artifact["predicted"] is None
    assert artifact["acquisition"] is None
    assert artifact["exploration_fallback"]["predicted"] is None
    assert artifact["predictions_appended_to_measured_rows"] is False
    json.dumps(artifact, allow_nan=False)


def test_proposal_artifact_flags_negative_interval_without_clamping():
    selection = _selection(0)
    selection["selection"]["predicted"].update({
        "j_lower": -1.0, "j_mean": 1.0, "j_upper": 3.0,
        "y_mean": -1.0, "y_sd": 1.0,
    })
    artifact = _build_proposal_artifact(
        selection=selection, candidate=_candidate(), training={}, pool={},
        encoding={"active_keys": ["a", "b", "c"]}, config={"objective_version": 4},
        validation={"status": "ok"})
    assert artifact["status"] == "ok"
    assert artifact["predicted"]["interval_lower_negative"] is True
    assert artifact["predicted"]["j_lower"] == -1.0  # reported, never clamped
    assert any("negative (nonphysical) J" in note
               for note in artifact["limitations"])
    json.dumps(artifact, allow_nan=False)
