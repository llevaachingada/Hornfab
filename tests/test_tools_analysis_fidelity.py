"""A.10 fidelity.py — golden tests: screen-vs-verify bias + within-run rank agreement.

Synthetic screen run (``search.ndjson`` mode ``screen`` rows) whose best designs are
re-solved at higher fidelity — some as ``mode: verify`` rows inside the same run file,
some in a real ``verify/search.ndjson`` sub-run. The golden verify relation is
J_verify = 1.25 * J_screen for every paired design except dh000, whose verify solve gets
BETTER (4.0 vs screen 10.0) so the all-pair Spearman drops to the exact hand value
rho = 1 - 6*sum(d^2) / (n*(n^2-1)) = 1 - 180/210 = 0.142857...
The screen top 5 (dh005..dh001) stay perfectly rank-agreeing: spearman_top5 = 1.0.
"""
from __future__ import annotations

import json

import pytest

from test_tools_analysis_common import (load_tool, make_row, run_cli, run_json_payload,
                                        write_run)

fid = load_tool("fidelity")

PAIRED = [f"dh{i:03d}" for i in range(6)]      # dh000..dh005 appear on BOTH sides


def js(dh: str) -> float:
    return 10.0 - int(dh[-3:])                 # dh000=10.0 ... dh009=1.0


def jv(dh: str) -> float:
    return 4.0 if dh == "dh000" else 1.25 * js(dh)


def _screen_rows(n_start: int = 10) -> list[dict]:
    rows = [make_row(i, js(f"dh{i:03d}"), design_hash=f"dh{i:03d}", mode="screen",
                     n=n_start + i, params={"a_deg": 10.0 + i})
            for i in range(10)]                # 10 screened designs (dh006..dh009 unpaired)
    # a re-played later candidate for dh002 with a WORSE older row (n=3, J=30):
    # the tool must keep the latest (highest n) row
    rows.append(make_row(20, 30.0, design_hash="dh002", mode="screen", n=3,
                         params={"a_deg": 10.0}))
    # dh000..dh004 re-solved as verify rows INSIDE the run's own ndjson
    rows += [make_row(30 + k, jv(f"dh{k:03d}"), design_hash=f"dh{k:03d}", mode="verify",
                      n=40 + k, params={"a_deg": 10.0}) for k in range(5)]
    return rows


def _verify_subrun_rows() -> list[dict]:
    dhs = [f"dh{k:03d}" for k in range(1, 6)] + ["dh010"]   # dh010 = verify-only
    return [make_row(60 + k, (50.0 if dh == "dh010" else jv(dh)),
                     design_hash=dh, mode="verify", n=60 + k,
                     params={"a_deg": 11.0})
            for k, dh in enumerate(dhs)]


def _run(tmp_path, name="fid"):
    d = write_run(_screen_rows(), tmp_path, name)
    vdir = d / "verify"
    vdir.mkdir()
    (vdir / "search.ndjson").write_text(
        "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in _verify_subrun_rows()),
        encoding="utf-8")
    return d


# ------------------------------------------------------------------- golden

def test_pairs_bias_and_rank_agreement(tmp_path):
    p = fid.analyse_run(_run(tmp_path))
    assert p["n_screen"] == 10 and p["n_verify"] == 7 and p["n_pairs"] == 6
    # latest screen row wins: dh002 pairs at J=8.0 (n=12), not the old n=3 row (30.0)
    dh2 = next(q for q in p["pairs"] if q["design_hash"] == "dh002")
    assert dh2["j_screen"] == 8.0 and dh2["j_verify"] == jv("dh002")
    # pairs sorted by design_hash; dh000's verify is BETTER (negative bias)
    assert p["pairs"][0] == {"design_hash": "dh000", "j_screen": 10.0, "j_verify": 4.0,
                             "bias_pct": pytest.approx(-60.0)}
    assert p["bias_median_pct"] == pytest.approx(25.0)          # five +25%, one -60%
    # hand-computed Spearman over all 6 pairs (dh000 inverts its rank):
    # sum d^2 = 25+1+1+1+1+1 = 30 -> rho = 1 - 6*30/(6*35)
    assert p["spearman_all"] == pytest.approx(1 - 6 * 30 / (6 * 35))
    # the screen's own top 5 (dh005..dh001) rank perfectly on verify
    assert p["spearman_top5"] == pytest.approx(1.0)


def test_bias_pct_sign_and_formula(tmp_path):
    p = fid.analyse_run(_run(tmp_path))
    winner = next(q for q in p["pairs"] if q["design_hash"] == "dh005")   # screen best
    assert winner["bias_pct"] == pytest.approx((6.25 - 5.0) / 5.0 * 100.0)


# ------------------------------------------------------------------- degrade

def test_fewer_than_three_pairs_degrades(tmp_path):
    rows = [make_row(i, 20.0 - i, design_hash=f"dh{i:03d}", mode="screen", n=10 + i,
                     params={"a_deg": 10.0 + i}) for i in range(14)]
    rows += [make_row(40 + k, 1.1 * (20.0 - k), design_hash=f"dh{k:03d}", mode="verify",
                      n=40 + k, params={"a_deg": 10.0 + k}) for k in range(2)]
    p = fid.analyse_run(write_run(rows, tmp_path, "two"))
    assert p["n_pairs"] == 2
    assert p["bias_median_pct"] == pytest.approx(10.0)   # both pairs: J_v = 1.10 * J_s
    assert p["spearman_all"] is None            # needs >= 3 pairs
    assert p["spearman_top5"] is None           # fewer than 5 paired designs
    assert "2 paired design(s)" in fid._md(p)    # md still renders


def test_no_verify_rows_at_all(tmp_path):
    rows = [make_row(i, 20.0 - i, design_hash=f"dh{i:03d}", mode="screen", n=10 + i,
                     params={"a_deg": 10.0 + i}) for i in range(14)]
    p = fid.analyse_run(write_run(rows, tmp_path, "screen_only"))
    assert p["n_pairs"] == 0 and p["bias_median_pct"] is None
    assert p["spearman_all"] is None and p["spearman_top5"] is None
    assert "—" in fid._md(p)


# ----------------------------------------------------------------------- CLI

def test_cli_report_and_chart(tmp_path):
    out = tmp_path / "out"
    proc = run_cli("fidelity", ["--run", str(_run(tmp_path))], tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(out, "fidelity")
    assert doc["tool"] == "fidelity" and doc["n_pairs"] == 6
    assert doc["bias_median_pct"] == pytest.approx(25.0)
    assert doc["spearman_top5"] == pytest.approx(1.0)
    md = (out / "fidelity.md").read_text(encoding="utf-8")
    assert "median verify-vs-screen bias: **25.0%**" in md and "`dh000`" in md
    assert (out / "fidelity.png").exists()


def test_missing_run_is_exit_2(tmp_path):
    proc = run_cli("fidelity", ["--run", str(tmp_path / "nope")], tmp_path)
    assert proc.returncode == 2 and "no search.ndjson" in proc.stderr
