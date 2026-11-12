"""A.5 walls.py — golden tests: bound walls per knob + narrowed/widened box proposal.

Scenario: 120 valid rows -> top decile = 12 rows. In those rows a_deg sits at the hi
bound (wall_hi), t0_mm sits at the lo bound (wall_lo), n spans the interior (narrow
proposal), a0_deg is constant (narrow proposal). Negative-bound widening is checked on
a synthetic config so the +/-10% arithmetic is exercised in both directions.
"""
from __future__ import annotations

import pytest

from test_tools_analysis_common import (BASE_CONFIG, load_tool, make_row, run_cli,
                                        run_json_payload, write_run)

walls = load_tool("walls")

N = 120
N_TOP = 12   # max(3, ceil(120/10))


def _top_params(i: int) -> dict:
    return {"a_deg": 59.0 + i / (N_TOP - 1),           # [59 .. 60]: hi wall, width 50
            "a0_deg": 15.0,                            # constant
            "n": 2.0 + 4.0 * i / (N_TOP - 1),          # [2 .. 6]: interior
            "t0_mm": 20.0 + i * 1.0 / (N_TOP - 1)}     # [20 .. 21]: lo wall, width 40


def _rows() -> list[dict]:
    rows = [make_row(i, float(i + 1), params=_top_params(i)) for i in range(N_TOP)]
    for i in range(N - N_TOP):
        rows.append(make_row(N_TOP + i, 100.0 + i, params={
            "a_deg": 10.0 + 50.0 * ((i * 7) % 100) / 100.0,
            "a0_deg": 30.0 * ((i * 3) % 100) / 100.0,
            "n": 1.0 + 7.0 * ((i * 11) % 100) / 100.0,
            "t0_mm": 20.0 + 40.0 * ((i * 13) % 100) / 100.0}))
    return rows


def test_wall_fractions_and_proposal_golden(tmp_path):
    run = write_run(_rows(), tmp_path, "runA")
    p = walls.analyse_run(run)
    assert p["top_decile_n"] == N_TOP
    by_key = {w["key"]: w for w in p["walls"]}
    # bounds: a_deg [10,60] width 50 -> 3% = 1.5; t0_mm [20,60] width 40 -> 1.2
    assert by_key["a_deg"]["frac_hi"] == 1.0 and by_key["a_deg"]["wall_hi"] is True
    assert by_key["a_deg"]["frac_lo"] == 0.0 and by_key["a_deg"]["wall_lo"] is False
    assert by_key["t0_mm"]["frac_lo"] == 1.0 and by_key["t0_mm"]["wall_lo"] is True
    assert by_key["n"]["wall_hi"] is False and by_key["n"]["wall_lo"] is False
    assert by_key["a0_deg"]["wall_hi"] is False and by_key["a0_deg"]["wall_lo"] is False
    prop = {q["key"]: q for q in p["proposal"]}
    # hi wall -> widen_hi +10% (hi stays the only changed side)
    assert prop["a_deg"]["action"] == "widen_hi"
    assert prop["a_deg"]["new_lo"] == 10.0
    assert prop["a_deg"]["new_hi"] == pytest.approx(66.0)
    # lo wall -> widen_lo -10%
    assert prop["t0_mm"]["action"] == "widen_lo"
    assert prop["t0_mm"]["new_hi"] == 60.0
    assert prop["t0_mm"]["new_lo"] == pytest.approx(18.0)
    # interior -> narrow to the top-decile span padded 5% of the bound width
    assert prop["n"]["action"] == "narrow"
    assert prop["n"]["new_lo"] == pytest.approx(2.0 - 0.05 * 7.0)
    assert prop["n"]["new_hi"] == pytest.approx(6.0 + 0.05 * 7.0)
    assert prop["a0_deg"]["action"] == "narrow"
    assert prop["a0_deg"]["new_lo"] == pytest.approx(15.0 - 0.05 * 30.0)
    assert "never automatic config changes" in p["note"]


def test_negative_bound_widening_arithmetic(tmp_path):
    cfg = {**BASE_CONFIG, "bounds": {
        "off_deg": {"lo": -5.0, "hi": -1.0},
        "amp_mm": {"lo": -5.0, "hi": 5.0},
    }}
    rows = [make_row(i, float(i + 1),
                     params={"off_deg": -1.0, "amp_mm": -5.0 + 0.01 * i}) for i in range(12)]
    rows += [make_row(12 + i, 100.0 + i, params={"off_deg": 0.0, "amp_mm": 0.0})
             for i in range(12)]
    run = write_run(rows, tmp_path, "neg", config=cfg)
    p = walls.analyse_run(run)
    prop = {q["key"]: q for q in p["proposal"]}
    # hi = -1 is a wall: "widen hi" moves it toward 0 (-0.9), never further negative
    assert prop["off_deg"]["action"] == "widen_hi"
    assert prop["off_deg"]["new_hi"] == pytest.approx(-0.9)
    assert prop["off_deg"]["new_lo"] == -5.0
    # lo = -5 is a wall: "widen lo" moves it to -5.5
    assert prop["amp_mm"]["action"] == "widen_lo"
    assert prop["amp_mm"]["new_lo"] == pytest.approx(-5.5)


def test_below_ten_valid_rows_degrades(tmp_path):
    rows = [make_row(i, 10.0 + i) for i in range(6)]
    run = write_run(rows, tmp_path, "tiny")
    p = walls.analyse_run(run)
    assert p["top_decile_n"] == 0 and p["walls"] == [] and p["proposal"] == []
    assert "no top decile" in p["note"]


def test_cli_report_and_chart(tmp_path):
    run = write_run(_rows(), tmp_path, "runA")
    out = tmp_path / "out"
    proc = run_cli("walls", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(out, "walls")
    assert doc["tool"] == "walls" and doc["top_decile_n"] == N_TOP
    md = (out / "walls.md").read_text(encoding="utf-8")
    assert "widen_hi" in md and "widen_lo" in md
    assert (out / "walls.png").exists()


def test_missing_run_is_exit_2(tmp_path):
    proc = run_cli("walls", ["--run", str(tmp_path / "nope")], tmp_path)
    assert proc.returncode == 2 and "no search.ndjson" in proc.stderr
