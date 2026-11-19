"""D8 continuation rule (WP 7.2 advisory): propose only when the last-100 gain beats the floor."""
from __future__ import annotations

from test_tools_analysis_common import load_tool, make_row, write_run

ca = load_tool("continuation_advice")


def _curve(bests):
    return [{"n": i + 1, "best": b} for i, b in enumerate(bests)]


def test_gain_above_the_v7_floor_proposes_and_below_does_not():
    flat = [5.0] * 50 + [5.0 - 0.004 * i for i in range(100)]   # last-100 gain 0.396
    assert ca.advise(_curve(flat), 0.3105)["advice"] == "propose continuation"
    small = [5.0] * 50 + [5.0 - 0.002 * i for i in range(100)]  # gain 0.198: a win under 0.13, a tie under 0.31
    r = ca.advise(_curve(small), 0.3105)
    assert r["advice"] == "do not propose" and abs(r["improvement"] - 0.198) < 1e-9


def test_short_runs_and_unknown_identities_refuse_to_advise():
    assert ca.advise(_curve([5.0] * 100), 0.3105)["advice"] == "too short"
    assert ca.advise(_curve([5.0] * 300), None)["advice"] == "no floor"


def test_run_dir_end_to_end_uses_the_identity_floor(tmp_path):
    rows = [make_row(i, 5.0 - (0.005 * max(0, i - 49)), version=7) for i in range(160)]
    r = ca.analyse(write_run(rows, tmp_path))
    assert r["identity"] == {"objective_version": 7, "variant": ""} and r["floor"] == 0.3105
    assert r["advice"] == "propose continuation"
    rows4 = [make_row(i, 5.0 - 0.01 * i, version=4) for i in range(160)]
    assert ca.analyse(write_run(rows4, tmp_path, "v4"))["advice"] == "no floor"
