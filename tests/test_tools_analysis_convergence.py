"""A.1 convergence.py — golden tests on a synthetic run (tmp_path fixtures only).

Scenario (hand-computed expectations): 20 new valid evals with new minima at
evals 1-10 (30 -> 11.2), 11-15 (-> 11.0), a tail improvement to 10.8 at eval 16, then a
flat tail; 4 refusals (3 invalid_geometry + 1 mesh_too_large) and 1 cached replay.
"""
from __future__ import annotations

import pytest

from test_tools_analysis_common import (load_tool, make_row, run_cli,
                                        run_json_payload, write_run)

conv = load_tool("convergence")

EVAL_OBJECTIVES = [30.0, 25.0, 20.0, 18.0, 16.0, 14.0, 13.0, 12.0,
                   11.5, 11.2, 11.1, 11.05, 11.03, 11.02, 11.0] + [10.8] * 5


def _scenario_rows() -> list[dict]:
    rows: list[dict] = []
    i = 0

    def ev(obj: float) -> None:
        nonlocal i
        rows.append(make_row(i, obj))
        i += 1

    for obj in EVAL_OBJECTIVES[:10]:      # evals 1-10
        ev(obj)
        if obj == 20.0:                   # after eval 3: three refused candidates
            for k in range(3):
                rows.append(make_row(i, 1000.0, ok=False, kind="invalid_geometry",
                                     error="invalid geometry"))
                i += 1
    rows.append(make_row(i, 1000.0, ok=False, kind="mesh_too_large", error="too big"))
    i += 1
    rows.append(make_row(i, 25.0, cached=True, design_hash="dh0009"))  # a replay (eval 2)
    i += 1
    for obj in EVAL_OBJECTIVES[10:]:
        ev(obj)
    return rows


def test_analyse_run_golden_numbers(tmp_path):
    run_dir = write_run(_scenario_rows(), tmp_path, "runA", seed=1030)
    r = conv.analyse_run(run_dir)
    assert r["run_dir"].endswith("runA")
    assert r["brief"] == "native__ath_core_v4" and r["family"] == "OSSE"
    assert r["objective_version"] == 4 and r["mode"] == "screen"
    assert r["n_rows"] == 25 and r["n_valid"] == 21 and r["n_cached"] == 1
    assert r["n_new_valid"] == 20
    assert r["refusals"] == {"invalid_geometry": 3, "mesh_too_large": 1}
    assert r["final_best"] == 10.8
    assert [p["n"] for p in r["curve"]] == list(range(1, 21))
    assert [p["best"] for p in r["curve"][:10]] == EVAL_OBJECTIVES[:10]
    # cached replays never advance the eval axis / wall clock
    assert r["curve"][9]["wall_s"] == 20.0 and r["curve"][14]["wall_s"] == 30.0
    assert r["curve"][-1]["wall_s"] == 40.0
    assert r["evals_to_1pct"] == 16      # first best <= 10.908
    assert r["evals_to_5pct"] == 10      # first best <= 11.34
    assert r["last20_improvement"] is True
    assert r["last20_improvement_pct"] == pytest.approx((11.0 - 10.8) / 10.8 * 100.0)
    # one window of 24 non-cached rows, rate 4/24
    assert r["refusal_rate_by_kind"] == [
        {"w": [1, 24], "rate": pytest.approx(4 / 24),
         "kinds": {"invalid_geometry": 3, "mesh_too_large": 1}}]


def test_analyse_run_degrades_on_tiny_run(tmp_path):
    rows = [make_row(0, 30.0), make_row(1, 3000.0, ok=False, kind="invalid_geometry")]
    run_dir = write_run(rows, tmp_path, "tiny")
    r = conv.analyse_run(run_dir)
    assert r["n_new_valid"] == 1 and r["n_valid"] == 1
    assert r["final_best"] == 30.0
    assert r["evals_to_1pct"] == 1 and r["evals_to_5pct"] == 1
    assert r["last20_improvement"] is False and r["last20_improvement_pct"] is None


def test_cli_writes_json_md_and_chart(tmp_path):
    run_dir = write_run(_scenario_rows(), tmp_path, "runA", seed=1030)
    out = tmp_path / "out"
    proc = run_cli("convergence", ["--run", str(run_dir)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert f"convergence OK: 1 run(s) -> {out}" in proc.stdout
    doc = run_json_payload(out, "convergence")
    assert doc["tool"] == "convergence" and len(doc["runs"]) == 1
    assert doc["runs"][0]["final_best"] == 10.8
    assert (out / "convergence.md").exists()
    assert (out / "convergence_1.png").exists()


def test_cli_two_runs_two_charts_and_md_table(tmp_path):
    a = write_run(_scenario_rows(), tmp_path, "runA", seed=1030)
    b = write_run([make_row(i, 40.0 - i) for i in range(12)], tmp_path, "runB", seed=1031)
    out = tmp_path / "out"
    proc = run_cli("convergence", ["--run", str(a), "--run", str(b)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(out, "convergence")
    assert [r["n_new_valid"] for r in doc["runs"]] == [20, 12]
    assert (out / "convergence_1.png").exists() and (out / "convergence_2.png").exists()
    md = (out / "convergence.md").read_text(encoding="utf-8")
    assert "runA" in md and "runB" in md
    assert "final best J: **10.8**" in md
    assert "invalid_geometry" in md


def test_cli_missing_run_dir_is_exit_2(tmp_path):
    proc = run_cli("convergence", ["--run", str(tmp_path / "nope")], tmp_path)
    assert proc.returncode == 2
    assert "no search.ndjson" in proc.stderr
