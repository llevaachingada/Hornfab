"""A.4 links.py — golden tests: |rho| >= 0.6 top-decile pairs with least-squares fits,
plus CMA covariance eigenvector dominance from run.json / cma/covariance.json.

Scenario: 60 valid rows -> top decile = 6 rows, on which n = 0.1 * a_deg + 1 exactly
(rho = 1) while a0_deg and t0_mm are constant (no pair, no fit). The CMA snapshot has
one 2-knob dominant eigenpair and one 3-knob one.
"""
from __future__ import annotations

import json

import pytest

from test_tools_analysis_common import (load_tool, make_row, run_cli,
                                        run_json_payload, write_run)

links = load_tool("links")

N = 60
TOP_A = [20.0, 25.0, 30.0, 35.0, 40.0, 45.0]
TOP_N = [0.1 * a + 1.0 for a in TOP_A]  # n = 0.1*a_deg + 1


def _rows() -> list[dict]:
    rows = []
    for i, (a, n) in enumerate(zip(TOP_A, TOP_N)):
        rows.append(make_row(i, float(i + 1), params={
            "a_deg": a, "a0_deg": 15.0, "n": n, "t0_mm": 30.0}))
    for i in range(N - len(TOP_A)):
        rows.append(make_row(len(TOP_A) + i, 100.0 + i, params={
            "a_deg": 10.0 + 50.0 * ((i * 7) % 100) / 100.0,
            "a0_deg": 30.0 * ((i * 3) % 100) / 100.0,
            "n": 1.0 + 7.0 * ((i * 11) % 100) / 100.0,
            "t0_mm": 20.0 + 40.0 * ((i * 13) % 100) / 100.0}))
    return rows


CMA = {
    "keys": ["a_deg", "a0_deg", "n", "t0_mm"],
    "n_dim": 4,
    "eigenpairs": [
        {"rank": 1, "eigenvalue": 4.2, "fraction": 0.61,
         "top_loadings": [{"key": "a_deg", "loading": 0.7},
                          {"key": "a0_deg", "loading": -0.6},
                          {"key": "n", "loading": 0.0}]},
        {"rank": 2, "eigenvalue": 1.1, "fraction": 0.24,
         "top_loadings": [{"key": "a_deg", "loading": 0.5},
                          {"key": "a0_deg", "loading": 0.5},
                          {"key": "n", "loading": 0.5},
                          {"key": "t0_mm", "loading": 0.5}]},
    ],
}


def test_pairs_and_fit_golden(tmp_path):
    run = write_run(_rows(), tmp_path, "runA")
    p = links.analyse_run(run)
    assert p["top_decile_n"] == 6
    assert [(x["a"], x["b"]) for x in p["pairs"]] == [("a_deg", "n")]
    pair = p["pairs"][0]
    assert pair["rho"] == pytest.approx(1.0)
    fit = pair["fit"]
    assert fit["scale"] == pytest.approx(0.1) and fit["offset"] == pytest.approx(1.0)
    assert fit["r2"] == pytest.approx(1.0)
    assert p["proposed_links"] == [{
        "knob_b": "n", "knob_a": "a_deg", "scale": pytest.approx(0.1),
        "offset": pytest.approx(1.0), "r2": pytest.approx(1.0),
        "source": "rho_top_decile"}]
    assert p["cma_directions"] == []  # no covariance snapshot in this run


def test_cma_directions_from_run_json(tmp_path):
    run = write_run(_rows(), tmp_path, "runA", extra_run_json={"cma_covariance": CMA})
    p = links.analyse_run(run)
    dirs = p["cma_directions"]
    assert [d["rank"] for d in dirs] == [1, 2]
    # rank 1: the top 2 |loadings| carry sqrt(0.85)/sqrt(0.85) = 1.0 of the norm
    assert dirs[0]["keys"] == ["a_deg", "a0_deg"]
    assert dirs[0]["loadings"] == {"a_deg": 0.7, "a0_deg": -0.6}
    assert dirs[0]["eigenvalue"] == 4.2 and dirs[0]["fraction"] == 0.61
    # rank 2: evenly spread -> needs 3 knobs to reach the 0.85 cover
    assert dirs[1]["keys"] == ["a_deg", "a0_deg", "n"]


def test_cma_directions_from_sidecar(tmp_path):
    run = write_run(_rows(), tmp_path, "runA")
    (run / "cma").mkdir()
    (run / "cma" / "covariance.json").write_text(json.dumps(CMA), encoding="utf-8")
    p = links.analyse_run(run)
    assert [d["rank"] for d in p["cma_directions"]] == [1, 2]


def test_few_top_rows_degrade_to_empty(tmp_path):
    rows = [make_row(i, 100.0 - i, params={"a_deg": 20.0 + i, "n": 2.0 + 0.1 * i})
            for i in range(20)]  # top decile = 3 rows < MIN_TOP_ROWS
    run = write_run(rows, tmp_path, "small")
    p = links.analyse_run(run)
    assert p["top_decile_n"] == 3
    assert p["pairs"] == [] and p["proposed_links"] == [] and p["cma_directions"] == []


def test_cli_report_and_chart(tmp_path):
    run = write_run(_rows(), tmp_path, "runA", extra_run_json={"cma_covariance": CMA})
    out = tmp_path / "out"
    proc = run_cli("links", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(out, "links")
    assert doc["tool"] == "links"
    assert doc["proposed_links"][0]["knob_b"] == "n"
    assert len(doc["cma_directions"]) == 2
    md = (out / "links.md").read_text(encoding="utf-8")
    assert "| `a_deg` | `n` |" in md and "Proposed `links:` entries" in md
    assert (out / "links.png").exists()


def test_missing_run_is_exit_2(tmp_path):
    proc = run_cli("links", ["--run", str(tmp_path / "nope")], tmp_path)
    assert proc.returncode == 2 and "no search.ndjson" in proc.stderr
