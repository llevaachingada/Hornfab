"""A.2 seed_variance.py — golden tests on synthetic same-config/different-seed groups.

Groups alpha (5 seeds, best J 10/11/12.5/12/11.5) and beta (5 seeds, best J
14/15/14.5/15.5/14.5): median 11.5 vs 14.5, spreads 2.5 vs 1.5, diff 3.0 > both
spreads -> "a-beats-b" with >= 5 seeds (2026-10-23 rule).
"""
from __future__ import annotations

import math

import pytest

from test_tools_analysis_common import (BASE_CONFIG, load_tool, make_row, run_cli,
                                        run_json_payload, write_run)

sv = load_tool("seed_variance")

ALPHA_BESTS = [10.0, 11.0, 12.5, 12.0, 11.5]
BETA_BESTS = [14.0, 15.0, 14.5, 15.5, 14.5]
N_EVALS = 12


def _rows_for(final_best: float, offset: int, family: str = "OSSE") -> list[dict]:
    """12 evals whose best-so-far decreases linearly to ``final_best`` (step 0.3)."""
    rows = []
    for j in range(N_EVALS):
        obj = round(final_best + 0.3 * (N_EVALS - 1 - j), 6)
        rows.append(make_row(j, obj, params=None, family=family))
    # give the best (last) design a distinct knob vector per seed
    rows[-1]["params"] = sv.params_flat({}) | _kn_offset(offset)
    return rows


def _kn_offset(offset: int) -> dict:
    return {"a_deg": 10.0 + 1.7 * offset, "a0_deg": (3.0 * offset) % 30.0,
            "n": 1.0 + 0.7 * offset, "t0_mm": 20.0 + 4.0 * offset}


def _group_rows(bests: list[float], family: str = "OSSE") -> list[list[dict]]:
    return [_rows_for(b, i, family) for i, b in enumerate(bests)]


def test_analyse_group_golden(tmp_path):
    dirs = [write_run(rows, tmp_path, f"a{i}", seed=1030 + i)
            for i, rows in enumerate(_group_rows(ALPHA_BESTS))]
    g = sv.analyse_group("alpha", dirs)
    assert g["runs"] == [str(d) for d in dirs]
    assert g["n_seeds"] == 5
    assert [s["cma_seed"] for s in g["seeds"]] == [1030, 1031, 1032, 1033, 1034]
    assert [s["best_j"] for s in g["seeds"]] == ALPHA_BESTS
    assert g["median_best"] == 11.5
    assert g["spread_best"] == 2.5
    ci = g["ci95_median_best"]
    assert ci is not None and ci[0] <= 11.5 <= ci[1]
    # evals-to-target vs the RUN's own final best (steps of 0.3): 1% of 10.0 = 0.1
    # -> only the last eval; 5% -> the n where the 0.3 step drops below 0.5 (n=11)
    by_b = {round(s["best_j"], 3): s for s in g["seeds"]}
    assert by_b[10.0]["evals_to_1pct"] == N_EVALS and by_b[10.0]["evals_to_5pct"] == 11
    assert by_b[12.5]["evals_to_1pct"] == N_EVALS
    # group ECDF: only the best seed (b=10) ever reaches 10.5/10.1
    assert g["ecdf_5pct"] == [[11, 0.2], [12, 0.2]]
    assert g["ecdf_1pct"] == [[12, 0.2]]


def test_seed_distances_norm_golden(tmp_path):
    dirs = [write_run(rows, tmp_path, f"a{i}", seed=1030 + i)
            for i, rows in enumerate(_group_rows(ALPHA_BESTS))]
    g = sv.analyse_group("alpha", dirs)
    dist = g["seed_distances_norm"]
    assert len(dist) == 10  # 5 choose 2
    # first pair = (run0, run1): normalised per-knob (v-lo)/(hi-lo), RMS over 4 knobs
    b = BASE_CONFIG["bounds"]
    n0 = {k: (_kn_offset(0)[k] - b[k]["lo"]) / (b[k]["hi"] - b[k]["lo"])
          for k in ("a_deg", "a0_deg", "n", "t0_mm")}
    n1 = {k: (_kn_offset(1)[k] - b[k]["lo"]) / (b[k]["hi"] - b[k]["lo"])
          for k in ("a_deg", "a0_deg", "n", "t0_mm")}
    expect = math.sqrt(sum((n0[k] - n1[k]) ** 2 for k in n0) / 4.0)
    first = next(iter(dist))  # insertion order: (run0, run1)
    assert dist[first] == pytest.approx(expect)
    assert all(v is None or v >= 0 for v in dist.values())


def test_verdict_alpha_beats_beta_with_five_seeds(tmp_path):
    a_dirs = [write_run(rows, tmp_path, f"a{i}", seed=1030 + i)
              for i, rows in enumerate(_group_rows(ALPHA_BESTS))]
    b_dirs = [write_run(rows, tmp_path, f"b{i}", seed=2030 + i)
              for i, rows in enumerate(_group_rows(BETA_BESTS))]
    payload = sv.analyse_groups({"alpha": a_dirs, "beta": b_dirs})
    assert len(payload["verdicts"]) == 1
    v = payload["verdicts"][0]
    assert v["a"] == "alpha" and v["b"] == "beta"
    assert v["median_a"] == 11.5 and v["median_b"] == 14.5
    assert v["spread_a"] == 2.5 and v["spread_b"] == 1.5
    assert v["n_seeds"] == 5 and v["rule_holds"] is True
    assert v["verdict"] == "a-beats-b"


def test_verdict_with_fewer_than_five_seeds_is_indicative(tmp_path):
    a_dirs = [write_run(rows, tmp_path, f"a{i}", seed=1030 + i)
              for i, rows in enumerate(_group_rows(ALPHA_BESTS[:4]))]
    b_dirs = [write_run(rows, tmp_path, f"b{i}", seed=2030 + i)
              for i, rows in enumerate(_group_rows(BETA_BESTS[:4]))]
    payload = sv.analyse_groups({"alpha": a_dirs, "beta": b_dirs})
    v = payload["verdicts"][0]
    assert v["n_seeds"] == 4 and v["rule_holds"] is True and v["verdict"] == "indicative"


def test_verdict_below_the_rule_is_no_verdict(tmp_path):
    # alpha median 9.0 with spread 6.0 vs beta median 14.5 spread 1.5:
    # diff 5.5 is NOT more than alpha's spread -> no verdict despite the better median
    a_bests = [9.0, 15.0, 9.0, 15.0, 9.0]
    b_dirs = [write_run(rows, tmp_path, f"b{i}", seed=2030 + i)
              for i, rows in enumerate(_group_rows(BETA_BESTS))]
    a_dirs = [write_run(rows, tmp_path, f"a{i}", seed=1030 + i)
              for i, rows in enumerate(_group_rows(a_bests))]
    payload = sv.analyse_groups({"alpha": a_dirs, "beta": b_dirs})
    v = payload["verdicts"][0]
    assert v["median_a"] == 9.0 and v["spread_a"] == 6.0
    assert v["rule_holds"] is False and v["verdict"] == "no-verdict"


def test_group_mixing_objective_version_raises(tmp_path):
    d1 = write_run(_rows_for(10.0, 0), tmp_path, "v4run")
    d2 = write_run([make_row(j, 30.0 - j, version=6) for j in range(N_EVALS)],
                   tmp_path, "v6run")
    with pytest.raises(ValueError, match="mixes provenance"):
        sv.analyse_group("bad", [d1, d2])


def test_verdict_across_different_families_is_exit_2(tmp_path):
    icw_cfg = {**BASE_CONFIG, "family": "ICW"}
    a_dirs = [write_run(rows, tmp_path, f"a{i}", seed=1030 + i)
              for i, rows in enumerate(_group_rows(ALPHA_BESTS))]
    b_dirs = [write_run(_rows_for(b, i, family="ICW"), tmp_path, f"b{i}", seed=2030 + i,
                        config=icw_cfg, family="ICW")
              for i, b in enumerate(BETA_BESTS)]
    with pytest.raises(SystemExit) as exc:
        sv.analyse_groups({"alpha": a_dirs, "beta": b_dirs})
    assert exc.value.code == 2  # hard error per schema.md, never a warning


def test_cli_ok_and_exit_2_paths(tmp_path):
    a_dirs = [write_run(rows, tmp_path, f"a{i}", seed=1030 + i)
              for i, rows in enumerate(_group_rows(ALPHA_BESTS))]
    out = tmp_path / "out"
    argv = ["--group", "alpha=" + ",".join(str(d) for d in a_dirs)]
    proc = run_cli("seed_variance", argv, tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(out, "seed_variance")
    assert doc["tool"] == "seed_variance"
    g = doc["groups"]["alpha"]
    assert g["median_best"] == 11.5 and g["n_seeds"] == 5
    assert doc["verdicts"] == []
    assert "ecdf_1pct" in g
    assert "Rule:" in (out / "seed_variance.md").read_text(encoding="utf-8")

    # mixed-provenance group -> exit 2, no report written in the second --out
    d_v6 = write_run([make_row(j, 30.0 - j, version=6) for j in range(N_EVALS)],
                     tmp_path, "v6run")
    argv_bad = ["--group", "bad=" + ",".join(str(d) for d in (a_dirs[0], d_v6))]
    out2 = tmp_path / "out_bad"
    proc_bad = run_cli("seed_variance", argv_bad, tmp_path, out="out_bad")
    assert proc_bad.returncode == 2
    assert "mixes provenance" in proc_bad.stderr
    assert not out2.exists()
