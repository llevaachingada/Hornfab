"""Tests for tools/search_preflight.py (the 2026-11-14 pre-flight gate).

Everything here is offline: the default path builds no mesh, the history fixture is a
synthetic run directory created under tmp_path, and the sampling test uses --geometry-only
(the generated-design pre-mesh check) so gmsh is never imported.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "search_preflight.py"
EXAMPLES = REPO / "examples" / "typologies" / "suggest_ab_2026-11-14"
NARROW = EXAMPLES / "sab__lecleach_fc540_T_narrow.yaml"
CTRL = EXAMPLES / "sab__lecleach_ctrl.yaml"
FC540 = EXAMPLES / "sab__lecleach_fc540.yaml"


def _load_tool():
    spec = importlib.util.spec_from_file_location("search_preflight_tool", TOOL)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


preflight = _load_tool()


# ------------------------------------------------------------------ synthetic history

NATIVE_CONFIG = """\
name: preflight_history_fixture
family: OSSE
seed_params:
  r0_mm: 17.78
  a_deg: 30.0
  a0_deg: 15.5
  L_mm: 260.0
  n: 4.0
  s: 0.7
  q: 0.995
  k: 1.0
  exponent: 4.0
  aspect_ratio: 1.25
bounds:
  r0_mm: {lo: 17.78, hi: 17.78, search: false}
  a_deg: {lo: 10.0, hi: 50.0}
  L_mm: {lo: 200.0, hi: 320.0}
  n: {lo: 3.0, hi: 5.0}
target:
  coverage_h_deg: 75.0
  coverage_v_deg: 45.0
  band_lo_hz: 700.0
  band_hi_hz: 5500.0
  di_target_db: null
  di_slope_target: 0.0
weights: {cov: 1.0, rip: 1.0, di: 0.3, dislope: 0.5, flat: 0.5, load: 0.0}
mesh:
  epw: 6.0
  quadrants: '1'
  dof_cap_screen: 5000
  dof_cap_verify: 7000
  dof_cap_final: 8900
  dof_per_triangle: 0.51
solve:
  backend: beat_cpu
  distance_m: 2.0
  angle_count: 73
  balloon: true
  balloon_points_screen: 512
  balloon_points_verify: 1024
  gmres_tol: 1.0e-05
  timeout_s: 900
search: {algorithm: cma, sigma0: 0.25, seed: 1234, budget: 40, popsize: null, tolfun: 0.001}
"""

BOUNDS = {
    "a_deg": {"lo": 10.0, "hi": 50.0},
    "L_mm": {"lo": 200.0, "hi": 320.0},
    "n": {"lo": 3.0, "hi": 5.0},
}


NESTED_CONFIG = """\
name: preflight_nested_fixture
family: OSSE
seed_params:
  r0_mm: 17.78
  a0_deg: 15.5
  a_deg: 36.1555
  L_mm: 298.5605
  n: 6.0
  s: 0.5353
  q: 0.996
  k: 1.0
  exponent: 2.0
  aspect_ratio: 1.0
  az_a_sf_amp: 0.0
  az_a_cos_amp: 0.0
  az_s_cos2_amp: 0.0
bounds:
  r0_mm: {lo: 17.78, hi: 17.78, search: false}
  a_deg: {lo: 15.0, hi: 55.0}
  L_mm: {lo: 200.0, hi: 320.0}
  n: {lo: 3.0, hi: 8.0}
  s: {lo: 0.3, hi: 0.9}
  q: {lo: 0.9, hi: 1.0}
  k: {lo: 0.3, hi: 2.5}
  az_a_sf_amp: {lo: -10.0, hi: 35.42}
  az_a_cos_amp: {lo: -29.05, hi: 7.65}
  az_s_cos2_amp: {lo: -0.255, hi: 0.5}
target:
  coverage_h_deg: 80.0
  coverage_v_deg: 60.0
  band_lo_hz: 700.0
  band_hi_hz: 5500.0
  di_target_db: null
  di_slope_target: 0.0
weights: {cov: 1.0, rip: 1.0, di: 0.3, dislope: 0.5, flat: 0.5, load: 0.0}
mesh:
  epw: 6.0
  quadrants: '1'
  dof_cap_screen: 5000
  dof_cap_verify: 7000
  dof_cap_final: 8900
  dof_per_triangle: 0.51
solve:
  backend: beat_cpu
  distance_m: 2.0
  angle_count: 73
  balloon: true
  balloon_points_screen: 512
  balloon_points_verify: 1024
  gmres_tol: 1.0e-05
  timeout_s: 900
search: {algorithm: cma, sigma0: 0.15, seed: 1234, budget: 100, popsize: null, tolfun: 0.001}
"""

NESTED_BOUNDS = {
    "a_deg": {"lo": 15.0, "hi": 55.0},
    "L_mm": {"lo": 200.0, "hi": 320.0},
    "n": {"lo": 3.0, "hi": 8.0},
    "s": {"lo": 0.3, "hi": 0.9},
    "q": {"lo": 0.9, "hi": 1.0},
    "k": {"lo": 0.3, "hi": 2.5},
}

NESTED_BEST_PARAMS = {
    "a_deg": 36.1554992059,
    "L_mm": 298.5604964443,
    "n": 6.0,
    "s": 0.5353201345,
    "q": 0.996,
    "k": 1.0,
}


def _write_native_config(tmp_path: Path) -> Path:
    path = tmp_path / "native_config.yaml"
    path.write_text(NATIVE_CONFIG, encoding="utf-8")
    return path


def _seed_params() -> dict:
    return {
        "r0_mm": 17.78,
        "a_deg": 30.0,
        "a0_deg": 15.5,
        "L_mm": 260.0,
        "n": 4.0,
        "s": 0.7,
        "q": 0.995,
        "k": 1.0,
        "exponent": 4.0,
        "aspect_ratio": 1.25,
    }


def _write_run_dir(tmp_path: Path, rows, best_hash: str = "prior-best", *,
                   bounds: dict | None = None, family: str = "OSSE",
                   objective_version: int = 1, brief_file: str | None = None,
                   best_params: dict | None = None,
                   best_objective: float = 1.0) -> Path:
    run_dir = tmp_path / "run_fixture"
    run_dir.mkdir()
    config: dict = {
        "bounds": bounds or BOUNDS,
        "objective": {"version": objective_version},
    }
    if brief_file is not None:
        config["brief_file"] = brief_file
    run_json = {
        "objective_version": objective_version,
        "family": family,
        "config_sha": "deadbeef0000",
        "config": config,
        "best": {"design_hash": best_hash, "objective": best_objective},
    }
    (run_dir / "run.json").write_text(json.dumps(run_json), encoding="utf-8")
    best = {"design_hash": best_hash, "objective": best_objective, "ok": True}
    if best_params is not None:
        best["params"] = best_params
    (run_dir / "best.json").write_text(json.dumps(best), encoding="utf-8")
    with (run_dir / "search.ndjson").open("w", encoding="utf-8") as fh:
        for n, (params, objective, design_hash) in enumerate(rows):
            fh.write(json.dumps({
                "n": n,
                "ok": True,
                "params": params,
                "objective": objective,
                "design_hash": design_hash,
            }) + "\n")
    return run_dir


def _varied_rows():
    return [
        ({"a_deg": 12.0, "L_mm": 205.0, "n": 3.05}, 1.0, "row-a"),
        ({"a_deg": 30.0, "L_mm": 260.0, "n": 4.00}, 1.1, "row-b"),
        ({"a_deg": 48.0, "L_mm": 315.0, "n": 4.95}, 1.2, "row-c"),
    ]


def _run_json(capsys, argv) -> tuple[int, dict]:
    code = preflight.main(argv + ["--json"])
    out = capsys.readouterr().out
    return code, json.loads(out)


def _report(payload: dict, name: str) -> dict:
    return next(r for r in payload["configs"] if r["name"] == name)


def _codes(payload: dict, severity: str) -> list[str]:
    return [f["code"] for f in payload["configs"][0]["findings"]
            if f["severity"] == severity]


# ------------------------------------------------------------------ tests

def test_narrow_seed_is_hard_outside_box(capsys):
    """The 2026-11-14 narrow T arm had g_T=0.8 outside [0.687, 0.777]."""
    code, payload = _run_json(capsys, [str(NARROW)])
    assert code == 1
    hard_codes = [f["code"] for f in payload["hards"]]
    assert "seed_outside_box" in hard_codes
    report = _report(payload, "sab__lecleach_fc540_T_narrow")
    assert report["seed_outside_box"] == [
        {"key": "g_T", "value": 0.8, "lo": 0.687, "hi": 0.777}]
    message = next(f["message"] for f in payload["hards"]
                   if f["code"] == "seed_outside_box")
    assert "DesignSpace.normalize()" in message
    assert "eval 0 still scores the unclipped seed" in message


def test_ab_reports_the_changed_bound_key(capsys):
    """The fc540 arm changes only g_fc_hz lo; the two arms are otherwise matched."""
    code, payload = _run_json(capsys, [str(CTRL), str(FC540), "--ab", str(CTRL)])
    assert code == 0
    ctrl = _report(payload, "sab__lecleach_ctrl")
    fc540 = _report(payload, "sab__lecleach_fc540")
    assert ctrl["ab"]["changed_keys"] == []
    assert fc540["ab"]["changed_keys"] == ["g_fc_hz"]
    assert fc540["ab"]["unmatched"] == {}


def test_synthetic_history_is_usable(capsys, tmp_path):
    """A tiny synthetic run dir (search.ndjson + best.json + run.json) drives the history.

    The varied top-k makes the spread-recommended sigma equal to this config's sigma0 and
    the expected hit count high, so the history path finishes without a warning. This pins
    that the tool never depends on the repo's runs/ contents.
    """
    config = _write_native_config(tmp_path)
    run_dir = _write_run_dir(tmp_path, _varied_rows(), best_hash="prior-best")
    code, payload = _run_json(capsys, [str(config), "--from-runs", str(run_dir)])
    assert code == 0
    report = _report(payload, "preflight_history_fixture")
    history = report["history"]
    assert history is not None
    assert history["mean_design_hash"] == "row-a"
    # median per-key normalized span of the three rows (L_mm is 110/120 = 0.9167)
    assert history["sigma_from_spread"]["median_spread"] == pytest.approx(11 / 12)
    assert history["sigma0"] == pytest.approx(0.25)
    assert report["sigma"]["expected_hits"] > 3.0
    assert "low_hits" not in _codes(payload, "WARN")
    assert "history_unusable" not in _codes(payload, "WARN")
    assert "no_headroom" not in _codes(payload, "WARN")
    assert "no_history" not in _codes(payload, "INFO")


def test_no_headroom_when_seed_is_the_prior_best(capsys, tmp_path):
    """If the seed design hash equals the prior best, the run starts at the old optimum."""
    from hornlab_search.types import Design

    config = _write_native_config(tmp_path)
    seed_hash = Design("OSSE", _seed_params()).hash()
    run_dir = _write_run_dir(tmp_path, _varied_rows(), best_hash=seed_hash)
    code, payload = _run_json(capsys, [str(config), "--from-runs", str(run_dir)])
    assert code == 0
    assert "no_headroom" in _codes(payload, "WARN")
    assert _report(payload, "preflight_history_fixture")["seed_design_hash"] == seed_hash


def test_duplicate_topk_warns_sigma_and_low_hits_and_strict_exits_1(capsys, tmp_path):
    """Identical prior rows are the zero-headroom/oversized-sigma case in miniature."""
    config = _write_native_config(tmp_path)
    same = {"a_deg": 30.0, "L_mm": 260.0, "n": 4.0}
    rows = [(same, 1.0, "row-a"), (same, 1.0, "row-a"), (same, 1.0, "row-a")]
    run_dir = _write_run_dir(tmp_path, rows, best_hash="prior-best")
    code, payload = _run_json(capsys, [str(config), "--from-runs", str(run_dir)])
    assert code == 0
    warning_codes = _codes(payload, "WARN")
    assert "low_hits" in warning_codes
    assert "sigma_too_large" in warning_codes
    strict_code = preflight.main(
        [str(config), "--from-runs", str(run_dir), "--strict", "--json"])
    capsys.readouterr()
    assert strict_code == 1


def test_geometry_only_samples_without_meshing(capsys):
    """--geometry-only samples generated designs and never needs gmsh."""
    code, payload = _run_json(
        capsys, [str(CTRL), "--samples", "5", "--geometry-only", "--seed", "0"])
    assert code == 0
    sampling = _report(payload, "sab__lecleach_ctrl")["sampling"]
    assert sampling["samples"] == 5
    assert "geometry-only" in sampling["status"]
    assert sampling["unvalidated"] == 0
    assert sampling["valid"] + sampling["refused"] == 5
    # The sampled fraction is a UNIFORM box sample, not the CMA's seed-concentrated draw.
    assert sampling["distribution"] == "uniform box"
    for finding in payload["configs"][0]["findings"]:
        if finding["code"] == "refusals":
            assert "uniform box sample" in finding["message"]
    capsys.readouterr()
    assert preflight.main(
        [str(CTRL), "--samples", "5", "--geometry-only", "--seed", "0"]) == 0
    table = capsys.readouterr().out
    assert ("uniform box sample (an upper bound away from the seed; "
            "CMA concentrates near it)") in table


def test_ab_changed_key_is_inactive_in_prior_topk(capsys, tmp_path):
    """A bound change on a key that never moved in the prior top-k cannot separate arms."""
    config_a = _write_native_config(tmp_path)
    config_b = tmp_path / "native_config_b.yaml"
    config_b.write_text(
        NATIVE_CONFIG.replace("a_deg: {lo: 10.0, hi: 50.0}",
                              "a_deg: {lo: 15.0, hi: 50.0}"),
        encoding="utf-8")
    same = {"a_deg": 12.0, "L_mm": 260.0, "n": 4.0}
    run_dir = _write_run_dir(
        tmp_path, [(same, 1.0, "row-a"), (same, 1.0, "row-a")], best_hash="prior-best")
    code, payload = _run_json(
        capsys, [str(config_a), "--ab", str(config_b), "--from-runs", str(run_dir)])
    assert code == 0
    report = _report(payload, "preflight_history_fixture")
    assert report["ab"]["changed_keys"] == ["a_deg"]
    assert report["ab"]["all_changed_inactive"] is True
    assert "ab_changed_keys_inactive" in _codes(payload, "WARN")


def test_nested_incumbent_seed_matches_on_shared_knobs(capsys, tmp_path):
    """The H1 seed is the prior best on six shared knobs; only three az keys are new."""
    config = tmp_path / "nested_config.yaml"
    config.write_text(NESTED_CONFIG, encoding="utf-8")
    run_dir = _write_run_dir(
        tmp_path,
        [(NESTED_BEST_PARAMS, 1.2345, "prior-best-nested")],
        best_hash="prior-best-nested",
        bounds=NESTED_BOUNDS,
        best_params=NESTED_BEST_PARAMS,
        best_objective=1.2345,
    )
    code, payload = _run_json(capsys, [str(config), "--from-runs", str(run_dir)])
    assert code == 0
    findings = [f for f in payload["configs"][0]["findings"]
                if f["code"] == "no_headroom"]
    assert len(findings) == 1
    message = findings[0]["message"]
    assert "matches the prior best on every shared knob" in message
    for key in ("az_a_sf_amp", "az_a_cos_amp", "az_s_cos2_amp"):
        assert key in message
    assert "1.2345" in message
    # The native history path still honestly reports the knob-name mismatch.
    assert "history_unusable" in _codes(payload, "WARN")


def test_generated_history_fallback_reads_grid_knobs(capsys, tmp_path):
    """Real grid rows keep knobs under params.grid.knobs; the fallback must read them."""
    cfg = preflight.load_config(str(CTRL))

    def _grid_params(g_t, g_fc_hz, g_stop_deg):
        return {"grid": {
            "rows": {"type": "lecleach"},
            "n_phi": 15,
            "n_s": 32,
            "wall_thickness_mm": 3.0,
            "knobs": {"g_T": g_t, "g_fc_hz": g_fc_hz, "g_stop_deg": g_stop_deg},
        }}

    rows = [
        (_grid_params(0.50, 600.0, 130.0), 1.0, "grid-a"),
        (_grid_params(0.65, 700.0, 170.0), 1.1, "grid-b"),
        (_grid_params(0.80, 800.0, 220.0), 1.2, "grid-c"),
    ]
    run_dir = _write_run_dir(
        tmp_path,
        rows,
        best_hash="grid-prior",
        bounds=dict(cfg.bounds_raw),
        family=cfg.family,
        objective_version=cfg.objective_version,
        brief_file=cfg.raw.get("brief_file"),
        best_params=rows[0][0],
        best_objective=1.0,
    )
    code, payload = _run_json(capsys, [str(CTRL), "--from-runs", str(run_dir)])
    assert code == 0
    report = _report(payload, "sab__lecleach_ctrl")
    history = report["history"]
    assert history is not None
    assert history["source"] == "preflight-fallback"
    assert history["sigma_from_spread"]["median_spread"] > 0.0
    assert report["sigma"]["recommended_sigma"] is not None
    assert report["sigma"]["expected_hits"] is not None
    assert "history_unusable" not in _codes(payload, "WARN")


def test_ab_unvisited_region_is_reported(capsys, tmp_path):
    """A widening region absent from the prior top-k is INFO, not a verdict.

    The real fc540 treatment DID sample the added [540, 600) region, so this check must
    not claim a J difference cannot be attributed to the treatment.
    """
    config_a = _write_native_config(tmp_path)          # a_deg lo 10 (treatment)
    config_b = tmp_path / "native_config_b.yaml"
    config_b.write_text(
        NATIVE_CONFIG.replace("a_deg: {lo: 10.0, hi: 50.0}",
                              "a_deg: {lo: 20.0, hi: 50.0}"),
        encoding="utf-8")
    same = {"a_deg": 30.0, "L_mm": 260.0, "n": 4.0}
    run_dir = _write_run_dir(
        tmp_path,
        [(same, 1.0, "row-a"), (same, 1.1, "row-a")],
        best_hash="prior-best")
    code, payload = _run_json(
        capsys, [str(config_a), "--ab", str(config_b), "--from-runs", str(run_dir)])
    assert code == 0
    report = _report(payload, "preflight_history_fixture")
    region = report["ab"]["added_regions"]["a_deg"][0]
    assert region["rows_inside"] == 0
    assert region["raw"] == [10.0, 20.0]
    findings = payload["configs"][0]["findings"]
    assert not any(f["code"] == "ab_unvisited_region" for f in findings)
    info = next(f for f in findings
                if f["code"] == "ab_region_unrepresented_in_prior")
    assert info["severity"] == "INFO"
    assert "[10, 20)" in info["message"]
    assert "a_deg" in info["message"]
    assert "expected for a widening experiment" in info["message"]
    assert "cannot be attributed" not in info["message"]


def test_ab_treatment_misses_binding_key(capsys, tmp_path):
    """The L1 lesson: prior winners pin one key; the treatment moves another."""
    config_a = _write_native_config(tmp_path)          # a_deg lo 10
    config_b = tmp_path / "native_config_b.yaml"
    config_b.write_text(
        NATIVE_CONFIG.replace("L_mm: {lo: 200.0, hi: 320.0}",
                              "L_mm: {lo: 200.0, hi: 300.0}"),
        encoding="utf-8")
    pinned = {"a_deg": 10.0, "L_mm": 260.0, "n": 4.0}
    run_dir = _write_run_dir(
        tmp_path,
        [(pinned, 1.0, "row-a"), (pinned, 1.1, "row-a")],
        best_hash="prior-best")
    code, payload = _run_json(
        capsys, [str(config_a), "--ab", str(config_b), "--from-runs", str(run_dir)])
    assert code == 0
    report = _report(payload, "preflight_history_fixture")
    assert report["ab"]["changed_keys"] == ["L_mm"]
    assert report["ab"]["binding_keys"]["a_deg"]["side"] == "lo"
    warning = next(f for f in payload["configs"][0]["findings"]
                   if f["code"] == "ab_treatment_misses_binding_key")
    assert warning["severity"] == "WARN"
    assert "a_deg" in warning["message"]
    assert "lo bound" in warning["message"]
    assert "raw 10" in warning["message"]


def test_chi2_cdf_without_scipy():
    # Closed forms: k=2 CDF(x) = 1 - exp(-x/2); k=1 CDF(1) = erf(1/sqrt(2)).
    assert preflight.chi2_cdf(0.0, 3) == 0.0
    assert preflight.chi2_cdf(2.0, 2) == pytest.approx(1.0 - math.exp(-1.0), rel=1e-12)
    assert preflight.chi2_cdf(1.0, 1) == pytest.approx(
        math.erf(1.0 / math.sqrt(2.0)), rel=1e-10)
    assert preflight.chi2_cdf(1.0e6, 3) == pytest.approx(1.0, abs=1e-12)
