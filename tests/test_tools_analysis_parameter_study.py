"""Focused tests for tools/analysis/parameter_study.py (S4 M1, offline).

Synthetic-cohort tests cover the pure report mechanics (task identity, exact decomposition,
deterministic selection, effect-curve bin merging, held-out suppression, interaction
not_estimable).  One optional smoke test runs the real CLI on a bounded subset of the local
native cohort when the read-only inputs exist; it is skipped only when those local inputs are
absent (CI), never to hide a failure.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from conftest import REPO
from test_tools_analysis_common import load_tool, run_cli

ps = load_tool("parameter_study")

CONFIG = REPO / "examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml"
BRIEF = REPO / "examples/briefs/campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml"
ACTIVITY = REPO / "scratch/bo_m0/b2/activity/parameter_activity.json"
PILOT = REPO / "scratch/bo_m0/r0/offline_scores_native/offline_scores.json"
CATALOG = REPO / "scratch/bo_m0/s0/catalog/catalog.csv"
DATASET = REPO / "dataset"


def _loaded():
    from hornlab_search.config import load_config
    from hornlab_search.design.space import DesignSpace
    from hornlab_search.objective import replay

    brief = replay.load_brief_context(BRIEF)
    config = load_config(CONFIG)
    space = DesignSpace.from_config(config)
    if ACTIVITY.is_file():
        activity = json.loads(ACTIVITY.read_text(encoding="utf-8"))
    else:  # the synthetic tests do not need the recorded B2 ledger content
        activity = {
            "controls": [],
            "counts": {},
            "active_projection": {"full_keys": list(space.keys()),
                                  "active_keys": list(space.keys()),
                                  "fixed_values": {}},
        }
    return brief, config, space, activity


def _fake_arrays() -> dict:
    f = np.array([300, 400, 800, 1280, 2000, 2500, 3200, 3957, 4500, 5500, 6500, 8000],
                 dtype=float)
    angles = np.array([0.0, 30.0, 60.0, 90.0])
    spl = np.tile(np.linspace(84.0, 92.0, f.size)[:, None], (1, angles.size))
    return {
        "freqs_hz": f,
        "h_angles_deg": angles,
        "v_angles_deg": angles,
        "spl_h_db": spl,
        "spl_v_db": spl * 0.999,
        "di_db": np.full(f.size, 10.0),
        "bw_h_deg": np.full(f.size, 55.0),
        "bw_v_deg": np.full(f.size, 54.0),
        "ripple_h_db": np.full(f.size, 0.2),
        "ripple_v_db": np.full(f.size, 0.25),
    }


def _make_rows(space, *, n: int = 40, constant_j: bool = False) -> list[dict]:
    rng = np.random.default_rng(7)
    keys = list(space.keys())
    rows = []
    for i in range(n):
        params = copy.deepcopy(space.seed.params)
        for key in keys:
            params[key] = space.bounds[key].from_unit(float(rng.random()))
        length = float(params.get("L_mm", 260.0))
        j = 5.0 if constant_j else float(1.0 + 0.004 * abs(length - 260.0) + 0.1 * (i % 5))
        terms = {k: 0.0 for k in ps.V4_WEIGHTED_KEYS}
        terms["cov"] = j
        terms["total"] = j
        outputs = {
            "bw_h_mean_deg": 55.0 + 0.01 * (length - 260.0) + 0.5 * (i % 3),
            "bw_v_mean_deg": 54.0 + 0.01 * (length - 260.0) + 0.4 * (i % 3),
            "di_mean_db": 10.0 + 0.002 * (length - 260.0),
            "di_slope_db_per_dec": 2.0 + 0.01 * (i % 4),
            "ripple_mean_db": 0.2 + 0.01 * (i % 5),
            "flatness_db": 1.5 + 0.02 * (i % 4),
            "spdi_mean_db": 8.0 + 0.003 * (length - 260.0),
        }
        shard, row = 30 + i // 20, i % 20
        rows.append({
            "shard": shard,
            "row": row,
            "params": params,
            "family": "OSSE",
            "design_hash": f"design{i:04d}",
            "j": j,
            "terms": terms,
            "stored_j": j,
            "parity_delta": 0.0,
            "status": "exact_complete",
            "reasons": [],
            "physical_id": f"phys{i}",
            "metric_id": f"metric{i}",
            "score_id": f"score{i}",
            "objective_version": 4,
            "metric_source": "stored",
            "target": {},
            "weights": dict(ps.replay.load_brief_context(BRIEF).weights),
            "diagnostics": {},
            "physical_outputs": outputs,
            "arrays": _fake_arrays(),
            "meta": {"mesh_hash": f"m{i}", "solve_hash": f"s{i}",
                     "metrics_scalars": {"f11_hz": 3957.14}},
            "catalog": {"config_name": ps.NATIVE_CONFIG, "fidelity": "screen",
                        "backend": "beat_cuda", "geometry_id": f"design{i:04d}",
                        "physical_solve_id": f"phys{i}", "run_id": "",
                        "experiment_id": ""},
        })
    return rows


def _pilot(n: int) -> dict:
    return {
        "counts": {"scored": n, "exact_complete": n, "config_unknown": 0},
        "parity": {"n": n, "n_compared": n, "max_abs_delta": 0.0, "within_1e-6": n},
        "exclusions": {},
    }


def _catalog_stats(n: int) -> dict:
    return {
        "ok_rows": n, "failed_rows": 0, "failure_kinds": {},
        "unique_geometries": n, "unique_design_hashes": n, "unique_physical_solves": n,
        "fidelities": {"screen": n}, "run_id_present": 0, "experiment_id_present": 0,
        "objective_versions": {"4": n}, "briefs": {ps.NATIVE_CONFIG: n},
        "brief_hashes": {"fake": n}, "score_identities": n,
    }


# --------------------------------------------------------------------- task identity / math


def test_task_identity_comes_from_resolved_brief():
    brief, _config, _space, _activity = _loaded()
    ti = ps._task_identity(brief, CONFIG)
    target = ti["resolved_target"]
    assert ti["objective_version"] == 4
    assert ti["brief_name"] == brief.name
    assert ti["brief_hash"] == brief.brief_hash()
    assert ti["cov_narrow_ratio"] == 2.0
    assert ti["weights"]["load"] == 0.0
    assert ti["tolerances"]["cov"] == 2.0
    assert target["band_lo_hz"] == brief.target.band_lo_hz == 300.0
    assert target["band_hi_hz"] == brief.target.band_hi_hz == 8000.0
    assert target["f0_hz"] == brief.target.f0_hz == 1280.0
    assert target["freq_weights"] == brief.target.freq_weights
    assert "load_brief_context" in ti["resolution_source"]


def test_exact_decomposition_preserves_raw_normalized_weighted_total():
    terms = {"cov": 1.5, "rip": 0.25, "di": 2.0, "dislope": 0.5, "flat": 0.4,
             "load": 0.0, "distd": 0.8, "diag": 0.6}
    weights = {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5,
               "load": 0.0, "distd": 0.5, "diag": 0.5}
    tolerances = {"cov": 2.0, "rip": 1.0, "di": 0.4, "dislope": 9.0, "flat": 1.5,
                  "load": 0.3, "distd": 2.0, "diag": 2.0}
    expected = sum(weights[k] * terms[k] for k in ps.V4_WEIGHTED_KEYS)
    terms["total"] = expected
    out = ps.decompose_frozen_j(terms, weights, tolerances)
    assert out["total"] == pytest.approx(expected)
    assert out["normalized"]["cov"] == pytest.approx(1.5)
    assert out["raw"]["cov"] == pytest.approx(3.0)
    assert out["weighted"]["di"] == pytest.approx(0.3 * 2.0)
    assert out["total_matches_replay_j"] is True


# --------------------------------------------------------------------- selection


def test_design_selection_is_deterministic_lowest_j_plus_spread():
    _brief, _config, space, activity = _loaded()
    rows = _make_rows(space, n=60)
    active = list(activity["active_projection"]["active_keys"])
    a, meta_a = ps.select_designs(rows, active, space.bounds, space.family, max_designs=5)
    b, meta_b = ps.select_designs(rows, active, space.bounds, space.family, max_designs=5)
    assert [r["design_hash"] for r in a] == [r["design_hash"] for r in b]
    assert 3 <= len(a) <= 5
    assert len({r["design_hash"] for r in a}) == len(a)
    assert a[0]["j"] == min(r["j"] for r in rows)
    assert meta_a["rule"] == meta_b["rule"] == "lowest_j_plus_maximin_best_half_v1"
    assert meta_a["selected"] == len(a)
    assert all(r["selection_reason"]["role"] in ("lowest_j_seed", "maximin_diversity")
               for r in a)


# --------------------------------------------------------------------- effects / curves / interactions


def test_effect_curves_merge_until_ten_unique_observations():
    rows = []
    X = []
    for i in range(100):
        rows.append({"params": {"a_deg": float(i), "L_mm": float(i % 3)}, "j": float(i)})
        X.append([i / 99.0, (i % 3) / 2.0])
    out = ps.effect_curves(rows, ["a_deg", "L_mm"], {}, "OSSE", {
        "status": "produced", "_X": X, "_valid_rows": rows,
        "_oof": {"j": [float(i) for i in range(100)]},
    })
    a = out["features"]["a_deg"]
    assert a["status"] == "ok"
    # 100 distinct observations -> ten decile bins, each with >=10 unique values.
    assert all(b["n_unique"] >= 10 for b in a["bins"])
    # Only three distinct L_mm values -> adjacent bins merge into one honest bin.
    lm = out["features"]["L_mm"]
    assert len(lm["bins"]) == 1
    assert lm["bins"][0]["n_unique"] == 3


def test_interaction_is_not_estimable_when_all_endpoints_are_boundary_excluded():
    class _ZeroModel:
        def predict(self, X):
            return np.zeros(len(X), dtype=float)

    effects = {
        "status": "produced",
        "_models": {"j": _ZeroModel()},
        "_X": np.ones((30, 2), dtype=float).tolist(),
        "_y": {"j": list(range(30))},
        "_valid_rows": [{} for _ in range(30)],
    }
    out = ps.interaction_diagnostic([], ["a", "b"], {}, "OSSE", effects)
    assert out["status"] == "produced"
    pair = out["pairs"][0]
    assert pair["status"] == "not_estimable"
    assert pair["reason_code"] == "insufficient_supported_anchors"
    assert all(s["n_evaluated"] == 0 for s in pair["steps"])
    assert all(s["n_boundary_excluded"] == 20 for s in pair["steps"])


def test_flat_frozen_j_suppresses_recommendation_from_heldout():
    _brief, _config, space, activity = _loaded()
    rows = _make_rows(space, n=40, constant_j=True)
    active = list(activity["active_projection"]["active_keys"])
    effects = ps.fit_effects(rows, active, space.bounds, space.family, analysis_seed=7)
    assert effects["status"] == "produced"
    assert effects["outputs"]["j"]["status"] == "flat_response"
    assert effects["heldout"]["passed"] is False
    assert effects["heldout"]["recommendation_status"].startswith("suppressed")


# --------------------------------------------------------------------- full payload schema


def test_payload_has_frozen_schema_and_actual_design_blocks():
    brief, config, space, activity = _loaded()
    rows = _make_rows(space, n=40)
    payload = ps.build_payload(
        brief=brief, config=config, pilot=_pilot(len(rows)),
        catalog_stats=_catalog_stats(len(rows)), activity=activity, rows=rows,
        config_path=CONFIG, dataset_root=None, catalog_rows={}, run_geometry=False,
        analysis_seed=7, max_designs=5,
    )
    assert set(payload) == {"tool", "schema_version", "protocol", "task_identity", "cohort",
                            "controls", "designs", "evidence", "limitations"}
    assert payload["tool"] == "parameter_study"
    assert payload["schema_version"] == 1
    assert payload["protocol"] == "bo-study-v1.1"
    assert payload["cohort"]["rows"] == len(rows)
    assert payload["cohort"]["run_ids_missing"] is True
    assert payload["cohort"]["experiment_identity"]["status"] == "insufficient_evidence"
    assert len(payload["designs"]) == 5
    for design in payload["designs"]:
        assert {"design_hash", "params", "geometry_descriptors", "response_bands_hz",
                "source_caveat_hz", "score_terms", "identities", "provenance",
                "selection_reason"} <= set(design)
        assert design["source_caveat_hz"] == 3957.0
        assert design["response_bands_hz"]["status"] == "ok"
        assert design["score_terms"]["total_matches_replay_j"] is True
        assert design["provenance"]["shard"] is not None
        assert design["provenance"]["row"] is not None
        assert design["provenance"]["run_id"] is None
        assert design["provenance"]["independent_experiment_identity"] == "insufficient_evidence"
    assert payload["evidence"]["parity"]["pilot"]["n_compared"] == len(rows)
    assert payload["evidence"]["design_selection"]["rule"] == \
        "lowest_j_plus_maximin_best_half_v1"
    assert payload["evidence"]["effects"]["screening_policy"]["status"] == \
        "below_policy_descriptive_diagnostic"
    blob = json.dumps(payload)
    assert "3957" in blob
    assert "Loading weight is 0.0" in blob
    assert "delta-J" in blob


# --------------------------------------------------------------------- real bounded smoke


@pytest.mark.skipif(not (PILOT.is_file() and CATALOG.is_file() and ACTIVITY.is_file()
                         and DATASET.is_dir()),
                    reason="local read-only S4 inputs are not present")
def test_cli_real_bounded_subset(tmp_path: Path):
    proc = run_cli("parameter_study", ["--limit", "30", "--no-geometry"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = json.loads((tmp_path / "out" / "parameter_study.json").read_text(encoding="utf-8"))
    assert doc["tool"] == "parameter_study"
    assert doc["cohort"]["rows"] == 200
    assert doc["cohort"]["run_ids_missing"] is True
    assert doc["cohort"]["backend_calls"] == 0
    # The full R0 artifact exposes all 200 rows, not the 50-row display cap.
    assert "offline_scores_native_full" in doc["cohort"]["pilot_artifact"]
    assert doc["cohort"]["pilot_join"]["artifact_rows_exposed"] == 200
    assert doc["cohort"]["pilot_join"]["joined"] == 30
    assert doc["cohort"]["pilot_join"]["mismatched_j"] == 0
    assert "subset" in doc["cohort"]["design_pool_note"]
    assert 3 <= len(doc["designs"]) <= 5
    assert len(doc["controls"]) == 20
    assert doc["evidence"]["effects"]["status"] in ("produced", "insufficient_support")
    md = (tmp_path / "out" / "parameter_study.md").read_text(encoding="utf-8")
    assert "Parameter study" in md
    assert "Limitations" in md


def test_good_design_fold_prediction_does_not_allow_recommendation():
    brief, config, space, activity = _loaded()
    rows = _make_rows(space, n=40)
    active = list(activity["active_projection"]["active_keys"])
    effects = ps.fit_effects(rows, active, space.bounds, space.family, analysis_seed=7)
    assert effects["heldout"]["passed"] is True
    assert effects["heldout"]["recommendation_status"] == "suppressed_insufficient_independent_evidence"
    assert effects["screening_policy"]["min_unique_observations"] == 100
    assert effects["screening_policy"]["min_independent_groups"] == 5
    payload = ps.build_payload(brief=brief, config=config, pilot=_pilot(len(rows)),
                               catalog_stats=_catalog_stats(len(rows)), activity=activity,
                               rows=rows, config_path=CONFIG, dataset_root=None,
                               catalog_rows={}, run_geometry=False, analysis_seed=7,
                               max_designs=3)
    assert payload["evidence"]["heldout"]["passed"] is True
    assert payload["evidence"]["recommendation"]["status"] == "suppressed"
    assert payload["evidence"]["recommendation"]["reason"] == \
        "independent_group_validation_and_effect_stability_not_established"


def test_missing_physical_output_uses_output_specific_folds():
    _brief, _config, space, activity = _loaded()
    rows = _make_rows(space, n=40)
    for row in rows[:10]:
        row["physical_outputs"].pop("bw_h_mean_deg")
    effects = ps.fit_effects(rows, list(activity["active_projection"]["active_keys"]),
                             space.bounds, space.family, analysis_seed=7)
    output = effects["outputs"]["bw_h_mean_deg"]
    assert output["n_observations"] == 30
    assert output["status"] == "ok"
    assert sum(f["n_test"] for f in output["folds"]) == 30


def test_interactions_do_not_claim_group_stability_from_full_fit():
    class Coupled:
        def predict(self, x):
            return x[:, 0] * x[:, 1]

    rng = np.random.default_rng(7)
    x = rng.uniform(0.1, 0.7, size=(80, 2))
    effects = {"status": "produced", "_models": {"j": Coupled()}, "_X": x.tolist(),
               "_y": {"j": list(range(80))}, "_valid_rows": [{}] * 80}
    out = ps.interaction_diagnostic([], ["a", "b"], {}, "OSSE", effects)
    assert out["pairs"][0]["status"] == "not_estimable"
    assert out["pair_order_stability_spearman"] == {}
    for step in out["pairs"][0]["steps"]:
        if step["n_supported"] == 0:
            assert step["median_abs_D"] is None


def test_missing_stored_f11_is_not_fabricated():
    summary = ps.response_band_summary(_fake_arrays(), {})
    assert summary["status"] == "ok"
    assert summary["stored_f11_hz"] is None
    assert summary["source_caveat_hz"] == ps.SOURCE_CAVEAT_HZ
