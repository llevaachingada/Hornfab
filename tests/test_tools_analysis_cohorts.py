"""S0 cohorts.py — operation-specific comparability and ATH census tests.

Synthetic catalog-like records only.  Every test pins the failure mode the S0 prompt names:
mixed versions/briefs/fidelity are rejected where inappropriate, an intentional treatment
difference is accepted, missing provenance is explicit, and duplicate cache rows never inflate
independent solves.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from test_tools_analysis_common import load_tool

coh = load_tool("cohorts")

ATH_BRIEF = "native_ath_core_2in_v4"
ATH_HASH = "fa45251216b5"
ATH_TARGET = {"coverage_h_deg": 50.0, "coverage_v_deg": 50.0,
              "band_lo_hz": 300.0, "band_hi_hz": 8000.0, "f0_hz": 1280.0,
              "freq_weights": {"band_hz": [[2500.0, 5500.0, 2.0]]}}


def spec() -> dict:
    return {"status": "ok", "name": "native__ath_core_v4", "brief": ATH_BRIEF,
            "brief_hash": ATH_HASH, "family": "OSSE", "objective_version": 4,
            "target": dict(ATH_TARGET),
            "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5,
                        "flat": 0.5, "load": 0.0, "distd": 0.5, "diag": 0.5},
            "tolerances": {"cov": 2.0, "rip": 1.0, "di": 0.4, "dislope": 9.0,
                           "flat": 1.5, "load": 0.3, "distd": 2.0, "diag": 2.0},
            "cov_narrow_ratio": 2.0, "cov_below_f0": "mask",
            "diag_reference": "round", "backend": "beat_cuda"}


def rec(i: int, *, ok: bool = True, brief: str = ATH_BRIEF,
        brief_hash: str = ATH_HASH, version: int = 4, fidelity: str = "screen",
        backend: str = "beat_cuda", config: str = "cfgA", run: str | None = "run-a",
        mesh: str = "mesh0", grid: str = "grid0", dep: str = "dep0",
        geom: str | None = None, solve: str | None = None,
        complete: bool = True, classification: str | None = None,
        missing_score: list[str] | None = None,
        missing_loading: list[str] | None = None,
        gate_failures: list[str] | None = None,
        score_known: bool = True, failure_kind: str | None = None) -> dict:
    classification = classification or ("complete" if complete else "partial_unsupported")
    provenance = {"config": config, "brief": brief, "brief_hash": brief_hash}
    return {
        "ok": ok,
        "failure_kind": failure_kind,
        "provenance": provenance,
        "family": "OSSE",
        "target": dict(ATH_TARGET),
        "target_hash": "target-hash",
        "objective_version": version,
        "score_identity": f"score-{version}-{brief_hash}",
        "score_parameters_known": score_known,
        "fidelity": fidelity,
        "backend": backend,
        "mesh_spec_id": mesh,
        "grid_hash": grid,
        "dependency_hash": dep,
        "software_hash": "software0",
        "own_commit": "own0",
        "geometry_id": geom or f"g{i}",
        "physical_solve_id": solve or f"s{i}",
        "experiment_id": run,
        "run_id": run,
        "config_name": config,
        "treatment_id": config,
        "terms": {"keys": ["cov", "rip", "di", "penalty", "total"]},
        "completeness": {
            "classification": classification,
            "complete_replayable": complete,
            "missing_score_arrays": list(missing_score or []),
            "missing_loading_arrays": list(missing_loading or []),
            "gate_failures": list(gate_failures or []),
        },
        "unknowns": [],
    }


# ------------------------------------------------------------------ comparability


def test_mixed_objective_versions_rejected_for_performance():
    p = coh.compare_operation([rec(0), rec(1, version=5)], "performance")
    assert p["status"] == "incompatible"
    assert "objective_version_mismatch" in p["blocking"]
    assert p["compatible_for_inference"] is False


def test_mixed_briefs_rejected_but_whole_config_equality_not_required():
    p = coh.compare_operation(
        [rec(0, config="cfgA"), rec(1, brief="other_brief", brief_hash="bbbbbbbbbbbb",
                                    config="cfgB")],
        "performance")
    assert p["status"] == "incompatible"
    assert "brief_mismatch" in p["blocking"]
    # A treatment difference alone is not the blocker.
    p2 = coh.compare_operation([rec(0, config="cfgA"), rec(1, config="cfgB")],
                               "performance")
    assert p2["status"] == "compatible"
    assert any(d["key"] == "config_name" for d in p2["allowed_differences"])


def test_mixed_fidelity_rejected_for_performance_but_allowed_for_fidelity_compare():
    records = [rec(0, geom="g0", fidelity="screen"),
               rec(1, geom="g0", fidelity="verify")]
    bad = coh.compare_operation(records, "performance")
    assert bad["status"] == "incompatible"
    assert "fidelity_mismatch" in bad["blocking"]
    good = coh.compare_operation(records, "fidelity_comparison")
    assert good["status"] == "compatible"
    assert good["n_pairs"] == 1
    assert sorted(good["pairs"][0]["fidelities"]) == ["screen", "verify"]
    assert any(d["key"] == "fidelity" for d in good["allowed_differences"])


def test_backend_parity_allows_only_backend_to_differ():
    records = [rec(0, geom="g0", backend="beat_cuda"),
               rec(1, geom="g0", backend="beat_cpu")]
    p = coh.compare_operation(records, "backend_parity")
    assert p["status"] == "compatible"
    assert p["n_pairs"] == 1
    assert sorted(p["pairs"][0]["backends"]) == ["beat_cpu", "beat_cuda"]
    bad = coh.compare_operation(records, "performance")
    assert "backend_mismatch" in bad["blocking"]


def test_intentional_optimizer_treatment_is_accepted_and_identified():
    records = [rec(0, config="cma_control"), rec(1, config="bayes_treatment")]
    p = coh.compare_operation(records, "optimizer_ab")
    assert p["status"] == "compatible"
    assert p["treatments"] == ["bayes_treatment", "cma_control"]
    assert any(d["key"] == "config_name" for d in p["allowed_differences"])
    # Same treatment is not an A/B.
    p2 = coh.compare_operation([rec(0, config="cfgA"), rec(1, config="cfgA")], "optimizer_ab")
    assert "treatment_not_varied" in p2["blocking"]


def test_missing_provenance_is_flagged_and_blocks_task_identity():
    r = rec(0)
    r["provenance"] = {}
    p = coh.compare_operation([r, rec(1)], "performance")
    assert p["status"] == "incompatible"
    assert "brief_unknown" in p["blocking"]
    assert "brief_hash_unknown" in p["blocking"]


def test_unknown_score_parameters_are_a_warning_not_silent_equality():
    p = coh.compare_operation([rec(0, score_known=False), rec(1, score_known=False)],
                              "performance")
    assert p["status"] == "compatible_with_unknowns"
    assert "score_parameters_unknown" in p["warnings"]
    assert p["compatible_for_inference"] is True


def test_spec_attachment_only_matches_the_resolved_brief():
    records = [rec(0), rec(1, brief="other_brief", brief_hash="bbbbbbbbbbbb")]
    attached = coh.attach_score_spec(records, spec())
    assert attached[0]["score_parameters_known"] is True
    assert attached[0]["score_spec"]["brief_hash"] == ATH_HASH
    assert attached[1]["score_parameters_known"] is False
    assert "score_spec" not in attached[1]


# ------------------------------------------------------------------ ATH census


def ath_records() -> list[dict]:
    return [
        rec(0, run="run-a", geom="g0", solve="s0"),
        rec(1, run="run-b", geom="g0", solve="s0"),          # duplicate solve
        rec(2, run="run-c", geom="g2", solve="s2"),
        rec(3, run="run-a", geom="g3", solve="s3", complete=False,
            classification="partial_unsupported", missing_score=["spl_balloon_db"]),
        rec(4, run="run-a", geom="g4", solve="s4", complete=False,
            classification="partial_loading_inputs", missing_loading=["z_throat"]),
        rec(5, ok=False, run="run-a", failure_kind="invalid_geometry"),
        rec(6, brief="other_brief", brief_hash="bbbbbbbbbbbb", geom="g6"),
        rec(7, version=7, geom="g7"),
        rec(8, fidelity="verify", geom="g8", solve="s8", run="run-v"),
    ]


def test_ath_census_counts_records_solves_geometries_experiments_and_arrays():
    p = coh.ath_census(ath_records(), spec(), min_geometries=1)
    assert p["operation"] == "ath_census"
    assert p["status"] == "eligible"
    assert p["matched_records"] == 7
    assert p["excluded_records"] == {"brief_mismatch": 1, "objective_version_mismatch": 1}
    assert len(p["groups"]) == 2
    screen = next(g for g in p["groups"] if g["group"]["fidelity"] == "screen")
    c = screen["counts"]
    assert c["n_records"] == 6 and c["n_ok"] == 5 and c["n_failed"] == 1
    assert c["n_unique_physical_solves"] == 4      # s0 duplicated
    assert c["n_unique_geometries"] == 4
    assert c["n_independent_experiments_known"] == 3  # run-a, run-b, run-c
    assert c["n_records_experiment_unknown"] == 0
    assert c["n_complete_replayable"] == 3
    assert c["n_partial_unsupported"] == 1
    assert c["n_partial_loading_inputs"] == 1
    assert c["missing_arrays"] == {"spl_balloon_db": 1}
    assert c["missing_loading_inputs"] == {"z_throat": 1}
    assert c["failures_by_type"] == {"invalid_geometry": 1}
    verify = next(g for g in p["groups"] if g["group"]["fidelity"] == "verify")
    assert verify["counts"]["n_complete_replayable"] == 1


def test_ath_census_returns_insufficient_evidence_below_the_minimum():
    p = coh.ath_census(ath_records(), spec(), min_geometries=10)
    assert p["status"] == "insufficient_evidence"
    assert "no_group_reaches_min_geometries" in p["reason_codes"]
    assert all(g["status"] == "insufficient_evidence" for g in p["groups"])


def test_ath_census_does_not_pool_screen_and_verify():
    p = coh.ath_census(ath_records(), spec(), min_geometries=1)
    assert p["policy"]["pool_across_groups"] is False
    assert {g["group"]["fidelity"] for g in p["groups"]} == {"screen", "verify"}
    assert p["totals_descriptive_only"]["n_records"] == 7


def test_ath_census_reports_experiment_provenance_gap():
    records = [rec(0, run=None), rec(1, run=None, geom="g1")]
    p = coh.ath_census(records, spec(), min_geometries=1)
    c = p["groups"][0]["counts"]
    assert c["n_independent_experiments_known"] == 0
    assert c["n_records_experiment_unknown"] == 2
    assert p["groups"][0]["status"] == "eligible_with_provenance_gaps"


# ------------------------------------------------------------------ spec resolution


def test_resolve_ath_spec_reads_a_config_and_its_brief(tmp_path):
    brief = {
        "name": "brief-x",
        "target": dict(ATH_TARGET),
        "weights": {"cov": 1.0},
        "objective": {"version": 4, "tolerances": {"cov": 2.0},
                      "cov_narrow_ratio": 2.0},
    }
    bpath = tmp_path / "brief.yaml"
    bpath.write_text(yaml.safe_dump(brief), encoding="utf-8")
    cfg = {"name": "native__ath_core_v4", "family": "OSSE",
           "brief_file": "brief.yaml", "solve": {"backend": "beat_cuda"}}
    cpath = tmp_path / "config.yaml"
    cpath.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    s = coh.resolve_ath_spec(cpath)
    assert s["status"] == "ok"
    assert s["brief"] == "brief-x"
    assert s["objective_version"] == 4
    assert s["cov_narrow_ratio"] == 2.0
    assert s["target"]["band_lo_hz"] == 300.0
    assert len(s["brief_hash"]) == 12


def test_resolve_ath_spec_reports_insufficient_evidence_when_unreadable(tmp_path):
    s = coh.resolve_ath_spec(tmp_path / "missing-config.yaml")
    assert s["status"] == "insufficient_evidence"
    assert s["reason"] == "ath_spec_unavailable"
