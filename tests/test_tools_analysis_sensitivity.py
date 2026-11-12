"""A.3 sensitivity.py — golden tests on a synthetic run.

Deterministic design: J depends ONLY on a_deg (J = (a_deg - 10) / 50, 80 valid rows);
every other knob is a decorrelated pseudo-random function of the row index, so Spearman
rho(a_deg, J) must be exactly 1.0, rho of every other knob strictly below 1, and the
RandomForest permutation importance must rank a_deg first (sklearn 1.9.1 installed).
Also exercised: the family row pooling for the global surrogate (--runs-dir).
"""
from __future__ import annotations

import pytest

from test_tools_analysis_common import (load_tool, make_row, run_cli,
                                        run_json_payload, write_run)

sens = load_tool("sensitivity")

N = 80


def _design(i: int) -> dict:
    return {"a_deg": 10.0 + 50.0 * i / (N - 1),                       # carries all of J
            "a0_deg": 30.0 * ((i * 37) % 100) / 100.0,
            "n": 1.0 + 7.0 * ((i * 29) % 100) / 100.0,
            "t0_mm": 20.0 + 40.0 * ((i * 31) % 100) / 100.0}


def _rows(n: int = N) -> list[dict]:
    rows = []
    for i in range(n):
        rows.append(make_row(i, (_design(i)["a_deg"] - 10.0) / 50.0, params=_design(i)))
    return rows


def test_spearman_golden_and_top_decile_shift(tmp_path):
    run = write_run(_rows(), tmp_path, "runA")
    p = sens.analyse_run(run)
    assert p["n_valid"] == N and p["top_decile_n"] == 8
    assert {s["key"] for s in p["spearman"]} == {"a_deg", "a0_deg", "n", "t0_mm"}
    a = {s["key"]: s for s in p["spearman"]}["a_deg"]
    assert a["rho"] == pytest.approx(1.0) and a["n"] == N
    assert p["spearman"][0]["key"] == "a_deg"  # sorted by |rho| desc
    assert all(abs(s["rho"]) < 1.0 for s in p["spearman"] if s["key"] != "a_deg")
    # top decile = 8 lowest J = 8 lowest a_deg; shift_norm normalised by the bound width
    shift = {s["key"]: s for s in p["top_decile_shift"]}["a_deg"]
    atop = sum(_design(i)["a_deg"] for i in range(8)) / 8.0
    aall = sum(d["a_deg"] for d in map(_design, range(N))) / N
    assert shift["mean_all"] == pytest.approx(aall)
    assert shift["mean_top"] == pytest.approx(atop)
    assert shift["shift_norm"] == pytest.approx((atop - aall) / (60.0 - 10.0))
    # a decorrelated knob's shift must be finite but small compared to a_deg's
    n_shift = {s["key"]: s for s in p["top_decile_shift"]}["n"]
    assert abs(n_shift["shift_norm"]) < abs(shift["shift_norm"])


def test_surrogate_permutation_importance_ranks_a_deg_first(tmp_path):
    run = write_run(_rows(), tmp_path, "runA")
    p = sens.analyse_run(run)
    sur = p["surrogate"]
    assert sur is not None
    if not sur["available"]:
        # the day-plan/schema degradation contract: sklearn is OPTIONAL (try/except,
        # falls back to Spearman) — CI has no sklearn, so the payload must say exactly
        # that and carry no importances; the deep surrogate checks below need sklearn.
        assert "note" in sur and "sklearn" in sur["note"]
        return
    assert sur["available"] is True
    assert sur["model"] == "RandomForestRegressor"
    assert sur["n_train"] == 64 and sur["n_test"] == 16  # 80 rows, test_size 0.2
    assert -1.0 <= sur["r2"] <= 1.0
    imp = sur["importance"]
    assert [d["key"] for d in imp] == ["a_deg", "n", "a0_deg", "t0_mm"] \
        or imp[0]["key"] == "a_deg"
    assert imp[0]["key"] == "a_deg"
    assert imp[0]["permutation_importance"] > 0.0
    assert all(set(d) == {"key", "permutation_importance", "std"} for d in imp)


def test_family_pooling_feeds_the_surrogate(tmp_path):
    runs_root = tmp_path / "runs_root"
    a = write_run(_rows(40), runs_root, "dirA")
    b = write_run(_rows(40), runs_root, "dirB")
    p_single = sens.analyse_run(a)
    assert p_single["surrogate"]["available"] is False  # 40 rows < SURROGATE_MIN_ROWS (and/or no sklearn)
    p_pool = sens.analyse_run(a, family_runs_dir=runs_root)
    sur = p_pool["surrogate"]
    if not sur["available"]:
        assert "note" in sur and "sklearn" in sur["note"]
        return
    assert sur["available"] is True and sur["n_train"] == 64 and sur["n_test"] == 16
    assert sur["importance"][0]["key"] == "a_deg"


def test_below_ten_valid_rows_degrades(tmp_path):
    rows = [make_row(i, 10.0 + i, params=_design(i)) for i in range(7)]
    run = write_run(rows, tmp_path, "tiny")
    p = sens.analyse_run(run)
    assert p["n_valid"] == 7 and p["top_decile_n"] is None
    assert p["spearman"] == [] and p["top_decile_shift"] == []
    assert p["surrogate"] is None


def test_missing_ndjson_is_exit_2(tmp_path):
    proc = run_cli("sensitivity", ["--run", str(tmp_path / "nope")], tmp_path)
    assert proc.returncode == 2
    assert "no search.ndjson" in proc.stderr


def test_cli_writes_report_and_chart(tmp_path):
    run = write_run(_rows(), tmp_path, "runA")
    proc = run_cli("sensitivity", ["--run", str(run)], tmp_path)
    out = tmp_path / "out"
    assert proc.returncode == 0, proc.stderr
    doc = run_json_payload(out, "sensitivity")
    assert doc["tool"] == "sensitivity" and doc["n_valid"] == N
    sur = doc["surrogate"]
    assert sur is not None and (sur["available"] is True
                                or ("note" in sur and "sklearn" in sur["note"]))
    assert "study_2026-11-12/sensitivity_analysis.py" in (out / "sensitivity.md").read_text(encoding="utf-8")
    assert (out / "sensitivity.png").exists()
