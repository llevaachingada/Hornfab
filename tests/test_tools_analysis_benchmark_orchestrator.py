"""P1c benchmark_orchestrator.py tests — plan derivation/identity, seed refusals,
override isolation and offline report over synthetic run dirs.

Nothing here touches a GPU, solver or real ``runs/`` tree.  Run dirs are built with
``test_tools_analysis_common.write_run``; the base config/brief are synthetic but
loadable by the real ``hornlab_search.config`` loader.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from test_tools_analysis_common import (REPO, load_tool, make_row, write_run)

bo = load_tool("benchmark_orchestrator")


# ------------------------------------------------------------------ fixtures

BRIEF = {
    "name": "synthetic_v4",
    "description": "synthetic benchmark brief",
    "driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0},
    "envelope": {"max_mouth_w_mm": 400.0, "max_mouth_h_mm": 400.0, "max_depth_mm": 300.0},
    "symmetry": "hv",
    "target": {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0,
               "band_lo_hz": 1000.0, "band_hi_hz": 10000.0},
    "weights": {"cov": 1.0, "rip": 1.0, "di": 1.0, "dislope": 1.0, "flat": 1.0,
                "load": 0.0, "distd": 1.0, "diag": 0.0},
    "objective": {"version": 4,
                  "tolerances": {"cov": 10.0, "rip": 2.0, "di": 5.0, "dislope": 2.0,
                                 "flat": 5.0, "load": 2.0, "distd": 10.0, "diag": 10.0}},
}

CONFIG = {
    "name": "synthetic_task_v4",
    "description": "synthetic benchmark base",
    "family": "OSSE",
    "brief_file": "brief.yaml",
    "seed_params": {"a_deg": 30.0, "a0_deg": 10.0, "n": 4.0, "t0_mm": 40.0, "L_mm": 250.0},
    "bounds": {
        "a_deg": {"lo": 10.0, "hi": 60.0},
        "a0_deg": {"lo": 0.0, "hi": 30.0},
        "n": {"lo": 1.0, "hi": 8.0},
        "t0_mm": {"lo": 20.0, "hi": 60.0},
        "L_mm": {"lo": 150.0, "hi": 300.0, "search": False},
    },
    "mesh": {"epw": 6.0, "quadrants": "1", "dof_cap_screen": 24000,
             "dof_cap_verify": 24000, "dof_cap_final": 24000,
             "dof_per_triangle": 0.51, "rear_res_factor": 1.5},
    "solve": {"backend": "beat_cuda", "distance_m": 10.0, "angle_count": 73,
              "balloon": True, "balloon_points_screen": 512,
              "balloon_points_verify": 1024, "gmres_tol": 1e-5, "timeout_s": 900},
    "search": {"algorithm": "cma", "sigma0": 0.2, "seed": 1000, "budget": 60,
               "tolfun": 0.001, "popsize": None, "budget_counts": "new",
               "max_attempts": 108, "error_policy": "legacy"},
}


def _fixture(tmp_path: Path) -> dict:
    """Write a loadable synthetic brief/config and a fake warm-source run dir."""
    src = tmp_path / "inputs"
    src.mkdir()
    brief_path = src / "brief.yaml"
    brief_path.write_text(yaml.safe_dump(BRIEF), encoding="utf-8")
    cfg_path = src / "base.yaml"
    cfg_path.write_text(yaml.safe_dump(CONFIG), encoding="utf-8")
    warm = write_run([_row(0, 12.0)], tmp_path, "warm_source", config=CONFIG, seed=999)
    return {"src": src, "brief": brief_path, "base": cfg_path, "warm": warm}


def _row(i: int, objective: float, *, version: int = 4, family: str = "OSSE") -> dict:
    row = make_row(i, objective, version=version, family=family)
    row["seconds"] = {"total": 2.0, "solve": 1.5}
    return row


def _curve_rows(objectives: list[float]) -> list[dict]:
    return [_row(i, obj) for i, obj in enumerate(objectives)]


def _arms(warm: Path, *, include_bo: bool = True) -> list[dict]:
    arms = [
        {"id": "cold_cma", "algorithm": "cma",
         "overrides": {"warm_start": None, "sigma0": 0.2},
         "expected_information": "no prior candidates"},
        {"id": "warm_mean", "algorithm": "cma_warm_mean",
         "overrides": {"sigma0": 0.2, "warm_start": {
             "from_runs": [str(warm)], "top_k": 10, "sigma_from_spread": False}},
         "expected_information": "prior best mean only"},
        {"id": "warm_cov", "algorithm": "cma_warm_covariance",
         "overrides": {"sigma0": 0.2, "warm_start": {
             "from_runs": [str(warm)], "top_k": 10, "sigma_from_spread": False,
             "covariance": {"blend": 0.25}}},
         "expected_information": "prior mean and covariance shape"},
    ]
    if include_bo:
        arms += [
            {"id": "scalar_bo", "algorithm": "bo_scalar",
             "overrides": {"policy": "scalar"}, "expected_information": "scalar GP"},
            {"id": "turbo", "algorithm": "turbo",
             "overrides": {"policy": "turbo"}, "expected_information": "trust region GP"},
        ]
    return arms


def _spec(fx: dict, *, seeds=None, arms=None, pairs=None, **extra) -> dict:
    spec = {
        "schema": "benchmark-plan-v1",
        "task": "synthetic matched pilot",
        "base_config": str(fx["base"]),
        "brief": str(fx["brief"]),
        "objective_version": 4,
        "family": "OSSE",
        "seeds": seeds if seeds is not None else [1000, 1001, 1002, 1003, 1004],
        "budget": 4,
        "target_j": 12.0,
        "practical_delta": 0.5,
        "floor_j": 0.5,
        "arms": arms if arms is not None else _arms(fx["warm"]),
        "pairs": pairs if pairs is not None else [["cold_cma", "warm_mean"]],
    }
    spec.update(extra)
    return spec


def _write_spec(tmp_path: Path, spec: dict, name: str = "spec.yaml") -> Path:
    d = tmp_path / "spec"
    d.mkdir(exist_ok=True)
    path = d / name
    path.write_text(yaml.safe_dump(spec), encoding="utf-8")
    return path


def _plan(tmp_path: Path, fx: dict, spec: dict | None = None, *, pilot: bool = False) -> dict:
    spec_path = _write_spec(tmp_path, spec or _spec(fx))
    return bo.plan_spec(spec_path, tmp_path / "plan_out", pilot=pilot)


def _arm_cfg(plan: dict, arm_id: str) -> dict:
    rec = next(a for a in plan["arms"] if a["id"] == arm_id)
    return yaml.safe_load(Path(rec["config_file"]).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_arm_runs(tmp_path: Path, plan: dict, arm_ids: list[str], *,
                    curves: dict[str, list[float]] | None = None,
                    seeds: list[int] | None = None,
                    extra_run_json: dict | None = None) -> dict[str, list[Path]]:
    seeds = seeds or plan["seeds"]
    out: dict[str, list[Path]] = {}
    for arm_id in arm_ids:
        cfg = _arm_cfg(plan, arm_id)
        dirs = []
        for i, seed in enumerate(seeds):
            if curves and arm_id in curves:
                base = curves[arm_id]
                rows = [_row(j, obj + 0.2 * i) for j, obj in enumerate(base)]
            else:
                rows = [_row(j, 10.0 - j + 0.2 * i) for j in range(plan["budget"])]
            d = write_run(rows, tmp_path / "runs", f"{arm_id}_{seed}",
                          config=cfg, family="OSSE", seed=seed,
                          extra_run_json=extra_run_json)
            dirs.append(d)
        out[arm_id] = dirs
    return out


def _results_args(results: dict[str, list[Path]]) -> list[str]:
    return [f"{arm}=" + ",".join(str(d) for d in dirs) for arm, dirs in results.items()]


# ------------------------------------------------------------------ plan


def test_plan_derives_arms_identity_and_advisory(tmp_path):
    fx = _fixture(tmp_path)
    spec = _spec(fx)
    plan = _plan(tmp_path, fx, spec)

    assert plan["schema"] == "benchmark-plan-v1"
    assert plan["dispatched"] is False and plan["advisory_only"] is True
    assert plan["seeds"] == [1000, 1001, 1002, 1003, 1004]
    assert plan["pilot"] is False
    assert {a["algorithm"] for a in plan["arms"]} == {
        "cma", "cma_warm_mean", "cma_warm_covariance", "bo_scalar", "turbo"}
    for arm in plan["arms"]:
        assert Path(arm["config_file"]).is_file()
        assert arm["identity"]["hash"] == plan["identity"]["hash"]
        assert arm["seeds"] == plan["seeds"]
        assert arm["launch"]["commands"]
        assert plan["launch"]["arms"][arm["id"]]["commands"] == arm["launch"]["commands"]
        # The derived YAML is self-contained: its brief path is absolute and resolves
        # outside the original config's directory.
        derived = yaml.safe_load(Path(arm["config_file"]).read_text(encoding="utf-8"))
        brief_file = Path(derived["brief_file"])
        assert brief_file.is_absolute() and brief_file.is_file()
        assert brief_file.resolve() == fx["brief"].resolve()
    assert plan["launch"]["dispatched"] is False

    cold = _arm_cfg(plan, "cold_cma")
    assert "warm_start" not in cold["search"]
    mean = _arm_cfg(plan, "warm_mean")
    assert mean["search"]["warm_start"]["sigma_from_spread"] is False
    assert "covariance" not in mean["search"]["warm_start"]
    cov = _arm_cfg(plan, "warm_cov")
    assert cov["search"]["warm_start"]["covariance"]["blend"] == 0.25
    # BO arms keep the task config's algorithm; the proposal policy is plan-level.
    scalar = _arm_cfg(plan, "scalar_bo")
    assert scalar["search"]["algorithm"] == "cma"
    assert next(a for a in plan["arms"] if a["id"] == "scalar_bo")["plan_level_overrides"]["policy"] == "scalar"
    # budget is plan-level and applied to every arm config
    assert all(_arm_cfg(plan, a["id"])["search"]["budget"] == 4 for a in plan["arms"])


def test_missing_training_cohort_is_refused(tmp_path):
    fx = _fixture(tmp_path)
    spec = _spec(fx, information_parity={
        "training_cohort": str(tmp_path / "missing_cohort"),
        "training_cohort_sha256": "0" * 64,
        "catalog_sha256": "0" * 64,
        "budget_profile": "comparison-80x2",
    })
    with pytest.raises(SystemExit) as exc:
        _plan(tmp_path, fx, spec)
    assert exc.value.code == 2


def test_bo_launch_is_executable_with_a_declared_cohort(tmp_path):
    fx = _fixture(tmp_path)
    cohort = tmp_path / "cohort.json"
    cohort.write_text("{}", encoding="utf-8")
    sha = hashlib.sha256(cohort.read_bytes()).hexdigest()
    spec = _spec(fx, information_parity={
        "training_cohort": str(cohort),
        "training_cohort_sha256": sha,
        "catalog_sha256": sha,
        "budget_profile": "comparison-80x2",
    })
    plan = _plan(tmp_path, fx, spec)
    launch = plan["launch"]["arms"]["scalar_bo"]
    assert launch["executable"] is True
    assert "<catalog_sha_required>" not in launch["commands"][0]
    assert sha in launch["commands"][0]


def test_plan_does_not_modify_base_and_writes_outside_inputs(tmp_path):
    fx = _fixture(tmp_path)
    before = _sha(fx["base"])
    plan = _plan(tmp_path, fx)
    assert _sha(fx["base"]) == before
    out = tmp_path / "plan_out"
    assert (out / "benchmark_plan.json").is_file()
    assert (out / "benchmark_plan.md").is_file()
    assert (out / "arms").is_dir()
    # output is outside the input/spec dirs
    assert not str(Path(plan["arms"][0]["config_file"]).resolve()).startswith(
        str((tmp_path / "spec").resolve()))
    doc = json.loads((out / "benchmark_plan.json").read_text(encoding="utf-8"))
    assert doc["dispatched"] is False and "advisory" in doc


def test_duplicate_seeds_refused(tmp_path):
    fx = _fixture(tmp_path)
    spec = _spec(fx, seeds=[1000, 1001, 1002, 1003, 1003])
    with pytest.raises(SystemExit) as exc:
        _plan(tmp_path, fx, spec)
    assert exc.value.code == 2


def test_fewer_than_five_seeds_needs_pilot(tmp_path):
    fx = _fixture(tmp_path)
    spec = _spec(fx, seeds=[1000, 1001, 1002])
    with pytest.raises(SystemExit) as exc:
        _plan(tmp_path, fx, spec)
    assert exc.value.code == 2
    plan = _plan(tmp_path, fx, spec, pilot=True)
    assert plan["pilot"] is True
    assert plan["seed_count"] == 3


def test_unknown_arm_field_and_algorithm_refused(tmp_path):
    fx = _fixture(tmp_path)
    bad_field = _spec(fx, arms=[{**_arms(fx["warm"])[0], "surprise": 1}])
    with pytest.raises(SystemExit):
        _plan(tmp_path, fx, bad_field)
    bad_algo = _spec(fx, arms=[{**_arms(fx["warm"])[0], "algorithm": "quantum_cma"}])
    with pytest.raises(SystemExit):
        _plan(tmp_path, fx, bad_algo)


def test_unknown_override_and_new_bound_refused(tmp_path):
    fx = _fixture(tmp_path)
    bad_override = _spec(fx, arms=[{
        "id": "cold_cma", "algorithm": "cma",
        "overrides": {"warm_start": None, "not_a_search_key": 1},
        "expected_information": "x"}])
    with pytest.raises(SystemExit):
        _plan(tmp_path, fx, bad_override)
    new_bound = _spec(fx, arms=[{
        "id": "cold_cma", "algorithm": "cma",
        "overrides": {"warm_start": None, "bounds": {"invented_knob": {"lo": 0.0, "hi": 1.0}}},
        "expected_information": "x"}])
    with pytest.raises(SystemExit):
        _plan(tmp_path, fx, new_bound)


def test_bounds_are_frozen_for_a_matched_optimizer_comparison(tmp_path, capsys):
    fx = _fixture(tmp_path)
    spec = _spec(fx, arms=[{
        "id": "cold_cma", "algorithm": "cma",
        "overrides": {"warm_start": None, "bounds": {"a_deg": {"lo": 10.0, "hi": 50.0}}},
        "expected_information": "x"}])
    with pytest.raises(SystemExit) as exc:
        _plan(tmp_path, fx, spec)
    assert exc.value.code == 2
    assert "bounds are frozen" in capsys.readouterr().err


# ------------------------------------------------------------------ report


def test_report_costs_pairs_and_floor_verdict(tmp_path):
    fx = _fixture(tmp_path)
    plan = _plan(tmp_path, fx)
    curves = {"cold_cma": [10.0, 9.0, 8.0, 7.0],
              "warm_mean": [8.0, 7.0, 6.0, 5.0]}
    results = _write_arm_runs(tmp_path, plan, ["cold_cma", "warm_mean"], curves=curves)
    payload = bo.report(tmp_path / "plan_out" / "benchmark_plan.json", results,
                        tmp_path / "report_out")
    assert payload["schema"] == "benchmark-report-v1"
    assert payload["dispatched"] is False and payload["advisory_only"] is True
    arms = {a["id"]: a for a in payload["arms"]}
    cold = arms["cold_cma"]
    assert cold["n_runs"] == 5
    assert cold["cost"]["attempts_new"] == 20
    assert cold["cost"]["valid_evaluations_new"] == 20
    assert cold["cost"]["cache_hits"] == 0
    assert cold["cost"]["actual_bem_calls_observed"] == 20
    assert cold["cost"]["actual_bem_seconds"] == pytest.approx(30.0)
    assert cold["median_curve"][-1]["n"] == 4
    assert cold["replicates"]["n_independent_replicates"] == 5

    assert len(payload["pairs"]) == 1
    pair = payload["pairs"][0]
    assert pair["n_pairs"] == 5
    assert pair["verdict"]["verdict"] == "b-beats-a"
    assert pair["verdict"]["decisive_claim"] is True
    assert pair["verdict"]["effect"]["mean"] == pytest.approx(2.0)
    assert pair["ab_compare"]["paired"]["pairing_declared"] is True
    assert (tmp_path / "report_out" / "benchmark_report.json").is_file()
    assert (tmp_path / "report_out" / "benchmark_report.md").is_file()


def test_report_missing_seed_refused(tmp_path):
    fx = _fixture(tmp_path)
    plan = _plan(tmp_path, fx)
    results = _write_arm_runs(tmp_path, plan, ["cold_cma", "warm_mean"],
                              seeds=plan["seeds"][:-1])
    # add the fifth run manually for the second arm only -> first arm is short
    results["warm_mean"].append(
        write_run([_row(0, 7.0)], tmp_path / "runs", "warm_mean_extra",
                  config=_arm_cfg(plan, "warm_mean"), seed=plan["seeds"][-1]))
    with pytest.raises(SystemExit) as exc:
        bo.report(tmp_path / "plan_out" / "benchmark_plan.json", results,
                  tmp_path / "report_out")
    assert exc.value.code == 2


def test_report_extra_seed_refused(tmp_path):
    fx = _fixture(tmp_path)
    plan = _plan(tmp_path, fx)
    results = _write_arm_runs(tmp_path, plan, ["cold_cma", "warm_mean"])
    results["cold_cma"].append(
        write_run([_row(0, 7.0)], tmp_path / "runs", "cold_extra",
                  config=_arm_cfg(plan, "cold_cma"), seed=9999))
    with pytest.raises(SystemExit) as exc:
        bo.report(tmp_path / "plan_out" / "benchmark_plan.json", results,
                  tmp_path / "report_out")
    assert exc.value.code == 2


def test_report_duplicate_seed_refused(tmp_path):
    fx = _fixture(tmp_path)
    plan = _plan(tmp_path, fx)
    results = _write_arm_runs(tmp_path, plan, ["cold_cma", "warm_mean"])
    # replace one run with a second dir carrying the same declared seed
    first = results["cold_cma"][0]
    dup = write_run([_row(0, 6.0)], tmp_path / "runs", "cold_dup",
                    config=_arm_cfg(plan, "cold_cma"), seed=plan["seeds"][0])
    results["cold_cma"][0] = dup
    results["cold_cma"].append(first)
    with pytest.raises(SystemExit) as exc:
        bo.report(tmp_path / "plan_out" / "benchmark_plan.json", results,
                  tmp_path / "report_out")
    assert exc.value.code == 2


def test_report_cross_task_refused(tmp_path):
    fx = _fixture(tmp_path)
    plan = _plan(tmp_path, fx)
    results = _write_arm_runs(tmp_path, plan, ["cold_cma", "warm_mean"])
    wrong_cfg = {**_arm_cfg(plan, "cold_cma"), "family": "ICW"}
    results["cold_cma"][0] = write_run(
        [_row(0, 7.0, family="ICW")], tmp_path / "runs", "cold_wrong_task",
        config=wrong_cfg, family="ICW", seed=plan["seeds"][0])
    with pytest.raises(SystemExit) as exc:
        bo.report(tmp_path / "plan_out" / "benchmark_plan.json", results,
                  tmp_path / "report_out")
    assert exc.value.code == 2


def test_report_undeclared_arm_refused(tmp_path):
    fx = _fixture(tmp_path)
    plan = _plan(tmp_path, fx)
    results = _write_arm_runs(tmp_path, plan, ["cold_cma", "warm_mean"])
    results["not_declared"] = results["cold_cma"][:1]
    with pytest.raises(SystemExit):
        bo.report(tmp_path / "plan_out" / "benchmark_plan.json", results,
                  tmp_path / "report_out")


def test_report_fewer_than_five_pairs_is_pilot_only(tmp_path):
    fx = _fixture(tmp_path)
    spec = _spec(fx, seeds=[1000, 1001, 1002])
    plan = _plan(tmp_path, fx, spec, pilot=True)
    results = _write_arm_runs(tmp_path, plan, ["cold_cma", "warm_mean"],
                              curves={"cold_cma": [10.0, 9.0, 8.0, 7.0],
                                      "warm_mean": [8.0, 7.0, 6.0, 5.0]})
    payload = bo.report(tmp_path / "plan_out" / "benchmark_plan.json", results,
                        tmp_path / "report_out")
    pair = payload["pairs"][0]
    assert pair["n_pairs"] == 3
    assert pair["verdict"]["verdict"] == "pilot_only"
    assert pair["verdict"]["decisive_claim"] is False
    assert payload["overall"]["any_decisive"] is False


def test_report_without_floor_refuses_decisive_claim(tmp_path):
    fx = _fixture(tmp_path)
    spec = _spec(fx)
    spec.pop("floor_j")
    plan = _plan(tmp_path, fx, spec)
    results = _write_arm_runs(tmp_path, plan, ["cold_cma", "warm_mean"],
                              curves={"cold_cma": [10.0, 9.0, 8.0, 7.0],
                                      "warm_mean": [8.0, 7.0, 6.0, 5.0]})
    payload = bo.report(tmp_path / "plan_out" / "benchmark_plan.json", results,
                        tmp_path / "report_out")
    pair = payload["pairs"][0]
    assert pair["verdict"]["decisive_claim"] is False
    assert pair["verdict"]["verdict"] in ("indicative", "no-verdict")
    assert "floor" in pair["verdict"]["reason"].lower()
    assert payload["overall"]["floor_present"] is False
    assert payload["overall"]["any_decisive"] is False


def test_report_information_parity_mismatch_blocks(tmp_path):
    fx = _fixture(tmp_path)
    plan = _plan(tmp_path, fx)
    results = _write_arm_runs(tmp_path, plan, ["cold_cma", "warm_mean"])
    # Rewrite the warm arm's config snapshot so the recorded warm sources differ from the
    # plan's declared parity; the run identity stays otherwise equal.
    warm_dir = results["warm_mean"][0]
    rj = json.loads((warm_dir / "run.json").read_text(encoding="utf-8"))
    assert rj["config"]["search"]["warm_start"]["from_runs"]
    rj["config"]["search"]["warm_start"]["from_runs"] = ["/tmp/not_the_declared_source"]
    (warm_dir / "run.json").write_text(json.dumps(rj, indent=1), encoding="utf-8")
    payload = bo.report(tmp_path / "plan_out" / "benchmark_plan.json", results,
                        tmp_path / "report_out")
    warm = next(a for a in payload["arms"] if a["id"] == "warm_mean")
    assert warm["information_parity"]["status"] == "blocking"
    assert payload["pairs"][0]["verdict"]["decisive_claim"] is False


def test_report_accepts_bo_mirror_bo_seed(tmp_path):
    """Mirrored BO/TuRBO study run dirs record ``bo_seed`` instead of ``cma_seed``."""
    fx = _fixture(tmp_path)
    plan = _plan(tmp_path, fx, _spec(fx, pairs=[["cold_cma", "scalar_bo"]]))
    cfg = _arm_cfg(plan, "scalar_bo")
    results: dict[str, list[Path]] = {"cold_cma": [], "scalar_bo": []}
    for i, seed in enumerate(plan["seeds"]):
        results["cold_cma"].append(write_run(
            [_row(j, 10.0 - j + 0.2 * i) for j in range(4)], tmp_path / "runs",
            f"cold_{seed}", config=_arm_cfg(plan, "cold_cma"), seed=seed))
        results["scalar_bo"].append(write_run(
            [_row(j, 9.0 - j + 0.2 * i) for j in range(4)], tmp_path / "runs",
            f"bo_{seed}", config=cfg, seed=seed,
            extra_run_json={"cma_seed": None, "bo_seed": seed,
                            "algorithm": "scalar"}))
    payload = bo.report(tmp_path / "plan_out" / "benchmark_plan.json", results,
                        tmp_path / "report_out")
    bo_arm = next(a for a in payload["arms"] if a["id"] == "scalar_bo")
    assert bo_arm["n_runs"] == 5
    assert [r["seed"] for r in bo_arm["runs"]] == plan["seeds"]
    assert payload["pairs"][0]["n_pairs"] == 5


# ------------------------------------------------------------------ template


def test_pilot_template_loads_and_validates():
    path = REPO / "tools" / "analysis" / "specs" / "matched_optimizer_pilot_2026-11-21.yaml"
    assert path.is_file()
    out = bo.validate_spec_file(path, check_sources=False)
    assert out["objective_version"] > 0
    assert len(out["seeds"]) == 5
    assert len(set(out["seeds"])) == 5
    assert len(out["arms"]) == 5
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    algorithms = {a["algorithm"] for a in spec["arms"]}
    assert {"cma", "cma_warm_mean", "cma_warm_covariance", "bo_scalar", "turbo"} <= algorithms
    assert spec["budget"] >= 1 and spec["floor_j"] is not None
