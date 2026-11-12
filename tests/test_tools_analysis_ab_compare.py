"""A.6 ab_compare.py — golden tests: matched-eval best J, final medians/spreads, the
2026-10-23 rule with the ab_compare floor (<3 runs/side -> no-verdict).

Scenario A (2 runs vs 1 run): side A best-so-far per eval is [10,8,6,4] and [12,9,5,3],
so the equal-budget medians at n=1..4 are 11, 8.5, 5.5, 3.5; side B is [20,15,10,8].
With fewer than 3 runs per side the verdict is a labelled "no-verdict".
"""
from __future__ import annotations

import pytest

from test_tools_analysis_common import (BASE_CONFIG, load_tool, make_row, run_cli,
                                        run_json_payload, write_run)

ab = load_tool("ab_compare")


def _run_with_curve(tmp_path, name: str, objectives: list[float], **kw) -> object:
    rows = [make_row(j, obj) for j, obj in enumerate(objectives)]
    return write_run(rows, tmp_path, name, **kw)


def _write_side(tmp_path, prefix: str, curves: list[list[float]], **kw):
    return [_run_with_curve(tmp_path, f"{prefix}{i}", c, seed=1000 + i, **kw)
            for i, c in enumerate(curves)]


def test_equal_budget_and_final_golden(tmp_path):
    a = _write_side(tmp_path, "a", [[10.0, 8.0, 6.0, 4.0], [12.0, 9.0, 5.0, 3.0]])
    b = _write_side(tmp_path, "b", [[20.0, 15.0, 10.0, 8.0]])
    p = ab.analyse(a, b, "narrow", "control")
    assert p["label_a"] == "narrow" and p["label_b"] == "control"
    assert p["sides"]["a"] == {"runs": [str(d) for d in a], "n_runs": 2, "n_new_valid_max": 4}
    assert p["sides"]["b"]["n_runs"] == 1 and p["sides"]["b"]["n_new_valid_max"] == 4
    assert p["equal_budget"] == [{"n": 1, "best_a": 11.0, "best_b": 20.0},
                                 {"n": 2, "best_a": 8.5, "best_b": 15.0},
                                 {"n": 3, "best_a": 5.5, "best_b": 10.0},
                                 {"n": 4, "best_a": 3.5, "best_b": 8.0}]
    assert p["final"] == {"median_a": 3.5, "median_b": 8.0, "spread_a": pytest.approx(1.0),
                          "spread_b": pytest.approx(0.0)}
    v = p["verdict"]
    assert v["n_runs_per_side"] == 1 and v["verdict"] == "no-verdict"
    assert "below the 3-run" in v["note"]


def test_five_runs_each_prints_verdict(tmp_path):
    a = _write_side(tmp_path, "a", [[10.0, 9.0, 8.0, 7.0]] * 5)   # final 7, spread 0
    b = _write_side(tmp_path, "b", [[20.0, 19.0, 18.0, 17.0]] * 5)  # final 17, spread 0
    p = ab.analyse(a, b, "narrow", "control")
    v = p["verdict"]
    assert v["n_runs_per_side"] == 5 and v["rule_holds"] is True
    assert v["verdict"] == "a-beats-b"  # a's median 7 < b's 17


def test_three_four_runs_is_indicative(tmp_path):
    a = _write_side(tmp_path, "a", [[10.0, 9.0, 8.0, 7.0]] * 4)
    b = _write_side(tmp_path, "b", [[20.0, 19.0, 18.0, 17.0]] * 3)
    v = ab.analyse(a, b)["verdict"]
    assert v["n_runs_per_side"] == 3 and v["verdict"] == "indicative"


def test_downsampled_equal_budget_has_no_duplicate_last_point(tmp_path):
    curve = [50.0 - 0.5 * j for j in range(30)]
    a = _write_side(tmp_path, "a", [curve])
    b = _write_side(tmp_path, "b", [curve])
    p = ab.analyse(a, b)
    eq = p["equal_budget"]
    assert len(eq) <= 21
    assert eq[-1]["n"] == 30
    assert [q["n"] for q in eq] == sorted({q["n"] for q in eq})  # strictly increasing


def test_mixed_objective_versions_is_exit_2(tmp_path):
    a = _write_side(tmp_path, "a", [[10.0, 9.0, 8.0]])
    b = [write_run([make_row(j, 20.0 - j, version=6) for j in range(3)],
                   tmp_path, "b0", seed=2000)]
    with pytest.raises(SystemExit) as exc:
        ab.analyse(a, b)
    assert exc.value.code == 2


def test_mixed_families_is_exit_2(tmp_path):
    icw_cfg = {**BASE_CONFIG, "family": "ICW"}
    a = _write_side(tmp_path, "a", [[10.0, 9.0, 8.0]])
    b = [write_run([make_row(j, 20.0 - j, family="ICW") for j in range(3)],
                   tmp_path, "b0", seed=2000, config=icw_cfg, family="ICW")]
    with pytest.raises(SystemExit) as exc:
        ab.analyse(a, b)
    assert exc.value.code == 2


def test_cli_report_and_chart(tmp_path):
    a = _write_side(tmp_path, "a", [[10.0, 9.0, 8.0, 7.0]] * 5)
    b = _write_side(tmp_path, "b", [[20.0, 19.0, 18.0, 17.0]] * 5)
    argv = ["--a", ",".join(str(d) for d in a), "--b", ",".join(str(d) for d in b),
            "--label-a", "narrow", "--label-b", "control"]
    out = tmp_path / "out"
    proc = run_cli("ab_compare", argv, tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(out, "ab_compare")
    assert doc["tool"] == "ab_compare" and doc["verdict"]["verdict"] == "a-beats-b"
    md = (out / "ab_compare.md").read_text(encoding="utf-8")
    assert "**narrow**" in md and "a-beats-b" in md
    assert (out / "ab_compare.png").exists()


def test_missing_side_dir_is_exit_2(tmp_path):
    a = _write_side(tmp_path, "a", [[10.0, 9.0, 8.0]])
    proc = run_cli("ab_compare", ["--a", str(a[0]), "--b", str(tmp_path / "nope")], tmp_path)
    assert proc.returncode != 0  # missing search.ndjson raises through load_run
