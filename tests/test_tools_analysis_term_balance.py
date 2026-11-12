"""A.9 term_balance.py — golden tests: share of J per term + raw-unit top-decile values.

All run dirs are synthetic (``test_tools_analysis_common`` fixtures, same row shape as
``hornlab_search/search/evaluate.py::evaluation_to_row``). The v4 ``terms`` rows follow
``hornlab_search/objective/scalar_v4.py`` lines 253-256 (t = raw/tol, total = sum w*t);
the v3 rows follow the pre-v4 contract (the stored term is already weighted, w*t).

Run layout: 120 valid rows -> top decile = 12 rows (max(3, ceil(120/10))). Rows i in
108..119 are the top decile (objective = 1000 - i, lowest J last). Their cov raw values
are exactly [0.01 .. 0.12]; every other row has cov raw 0.20.
"""
from __future__ import annotations

import pytest

from test_tools_analysis_common import (BASE_CONFIG, load_tool, make_row, run_cli,
                                        run_json_payload, v4_terms, write_run)

tb = load_tool("term_balance")

N = 120
N_TOP = 12                                  # max(3, ceil(120/10)) for 120 valid rows
TOP_COV_RAW = [0.01 + 0.01 * j for j in range(N_TOP)]   # [0.01 .. 0.12]

W = BASE_CONFIG["weights"]                  # cov/rip/di/dislope/flat/distd = 1.0; load/diag = 0.0
TOL = BASE_CONFIG["objective"]["tolerances"]

# raw-unit term values of a NON-top row (cov 0.20; the rest constant)
RAW_OTHER = {"cov": 0.20, "rip": 1.0, "di": 1.0, "dislope": 0.5, "flat": 1.0,
             "load": 0.5, "distd": 2.0, "diag": 1.0}
# share of J that cov carries in such a row: w * (0.20/0.05) / total
_T_CUM = {k: RAW_OTHER[k] / TOL[k] for k in TOL}
_TOTAL_OTHER = sum(W.get(k, 0.0) * _T_CUM[k] for k in TOL)
SHARE_COV_OTHER = (W["cov"] * _T_CUM["cov"]) / _TOTAL_OTHER


def _raw(i: int) -> dict:
    top = i - (N - N_TOP)
    cov = TOP_COV_RAW[top] if top >= 0 else 0.20
    return {**RAW_OTHER, "cov": cov}


def _v4_run(tmp_path, name="v4run"):
    rows = []
    for i in range(N):
        rows.append(make_row(i, 1000.0 - i,                       # top decile = i in 108..119
                             terms=v4_terms(_raw(i), W, TOL)))
    return write_run(rows, tmp_path, name)


# ----------------------------------------------------------------- shares (v4)

def test_shares_of_j_per_term_v4(tmp_path):
    run = _v4_run(tmp_path)
    p = tb.analyse_run(run)
    assert p["brief"] == "native__ath_core_v4"
    assert p["objective_version"] == 4
    assert p["n_valid"] == N and p["n_top"] == N_TOP
    # cov is the largest carrier in the synthetic rows; every share is a fraction
    assert 0.0 <= p["shares"]["cov"]["median"] <= 1.0
    assert p["shares"]["cov"]["median"] == pytest.approx(SHARE_COV_OTHER, rel=1e-9)
    # mean is exact given the constructed values: 108 constant-share rows plus the
    # 12 low-cov top-decile rows (share = cov_t / (cov_t + OTHER_J))
    other_j = _TOTAL_OTHER - _T_CUM["cov"]                       # constant J mass of the rest
    low = [(0.2 * k) / (0.2 * k + other_j) for k in range(1, N_TOP + 1)]
    assert p["shares"]["cov"]["mean"] == pytest.approx(
        (sum(low) + (N - N_TOP) * SHARE_COV_OTHER) / N, rel=1e-9)
    # load and diag carry weight 0 -> they cannot carry J
    assert p["shares"]["load"]["median"] == pytest.approx(0.0, abs=1e-12)
    assert p["shares"]["diag"]["median"] == pytest.approx(0.0, abs=1e-12)
    # shares are sorted by descending median
    med = [s["median"] for s in p["shares"].values()]
    assert med == sorted(med, reverse=True)


def test_weights_and_tolerances_reported_from_config(tmp_path):
    run = _v4_run(tmp_path)
    p = tb.analyse_run(run)
    assert p["weights"]["cov"] == 1.0 and p["weights"]["load"] == 0.0
    assert p["tolerances"]["cov"] == 0.05 and p["tolerances"]["rip"] == 0.5


# ------------------------------------------------- raw-unit top-decile (v4)

def test_top_decile_raw_is_term_times_tolerance(tmp_path):
    run = _v4_run(tmp_path)
    p = tb.analyse_run(run)
    raw = p["top_decile_raw"]["cov"]
    # t * tolerance recovers the raw value exactly (v4 stores term/tolerance)
    assert raw["median"] == pytest.approx(0.065)        # (0.06 + 0.07) / 2
    assert raw["p10"] == pytest.approx(0.021)           # 0.02 + 0.1 * (0.03 - 0.02)
    assert raw["p90"] == pytest.approx(0.109)           # 0.10 + 0.9 * (0.11 - 0.10)
    # const per row: the other weighted terms are constant across the decile
    assert p["top_decile_raw"]["rip"]["median"] == pytest.approx(1.0)
    assert p["top_decile_raw"]["load"]["median"] == pytest.approx(0.5)


def test_below_ten_valid_rows_has_no_top_decile(tmp_path):
    rows = [make_row(i, 10.0 + i, terms=v4_terms(_raw(i), W, TOL)) for i in range(6)]
    run = write_run(rows, tmp_path, "tiny")
    p = tb.analyse_run(run)
    assert p["n_valid"] == 6 and p["n_top"] == 0
    assert p["top_decile_raw"] == {}
    assert p["shares"]["cov"]["median"] == pytest.approx(SHARE_COV_OTHER, rel=1e-9)


# ----------------------------------------------------------------- v3 contract

def test_v3_rows_store_weighted_terms_raw_is_term_over_weight(tmp_path):
    W3 = {"cov": 2.0, "rip": 1.0, "di": 1.0, "dislope": 1.0, "flat": 1.0, "load": 1.0}
    cov_raw = [0.02 + 0.01 * j for j in range(12)]      # row i's raw cov
    rows = []
    for i in range(12):
        c = cov_raw[i]
        cov_t = W3["cov"] * c                            # v3 stores the WEIGHTED term
        rip_t = W3["rip"] * 1.0
        total = cov_t + rip_t
        rows.append(make_row(i, 100.0 - i, version=3,
                             terms={"cov": cov_t, "rip": rip_t, "di": 0.0, "dislope": 0.0,
                                    "flat": 0.0, "load": 0.0, "total": total}))
    cfg = {**BASE_CONFIG, "weights": W3, "objective": {"version": 3}}  # v3: no tolerances
    run = write_run(rows, tmp_path, "v3run", config=cfg)
    p = tb.analyse_run(run)
    assert p["objective_version"] == 3
    # share = stored (already weighted) contribution / total, median over the 12 rows
    sh = sorted((2.0 * c) / (2.0 * c + 1.0) for c in cov_raw)
    assert p["shares"]["cov"]["median"] == pytest.approx((sh[5] + sh[6]) / 2)
    # raw recovery: stored term / weight. 12 valid rows -> top decile = 3 rows,
    # the lowest-J ones (i = 9, 10, 11 -> raw cov 0.11, 0.12, 0.13; median 0.12)
    assert p["top_decile_raw"]["cov"]["median"] == pytest.approx(0.12)
    assert p["top_decile_raw"]["rip"]["median"] == pytest.approx(1.0)


# --------------------------------------------------------------------- CLI

def test_cli_single_run_emits_flat_schema_shape(tmp_path):
    run = _v4_run(tmp_path)
    out = tmp_path / "out"
    proc = run_cli("term_balance", ["--run", str(run)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(out, "term_balance")
    assert doc["tool"] == "term_balance"
    assert set(doc) >= {"brief", "objective_version", "n_valid", "shares",
                        "top_decile_raw", "weights", "tolerances"}
    assert "runs" not in doc
    assert doc["shares"]["cov"]["median"] == pytest.approx(SHARE_COV_OTHER, rel=1e-9)
    md = (out / "term_balance.md").read_text(encoding="utf-8")
    assert "`cov`" in md and "Raw-unit values" in md
    assert (out / "term_balance.png").exists()


def test_cli_two_runs_wrap_in_runs_list(tmp_path):
    run_a = _v4_run(tmp_path, "a")
    run_b = _v4_run(tmp_path, "b")
    out = tmp_path / "out"
    proc = run_cli("term_balance", ["--run", str(run_a), "--run", str(run_b)], tmp_path)
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(out, "term_balance")
    assert len(doc["runs"]) == 2 and doc["runs"][0]["brief"] == "native__ath_core_v4"


def test_missing_run_is_exit_2(tmp_path):
    proc = run_cli("term_balance", ["--run", str(tmp_path / "nope")], tmp_path)
    assert proc.returncode == 2 and "no search.ndjson" in proc.stderr
