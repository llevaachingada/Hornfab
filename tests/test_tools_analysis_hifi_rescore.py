"""hifi_rescore.py - golden tests on synthetic responses (no solver, tmp_path only).

Core contract: a design whose every direction shares ONE frequency shape (only a fixed taper per
angle) has zero non-EQ-able terms whatever that shape is, so the DSP score ignores a broad
on-axis bump while the passive score penalises it; angle-dependent ripple raises seat_spread.
"""
from __future__ import annotations

import json

import numpy as np
import pytest
import yaml

from test_tools_analysis_common import load_tool

hr = load_tool("hifi_rescore")

F = np.geomspace(250.0, 8000.0, 18)
ANG = np.arange(-90.0, 90.0 + 1e-9, 2.5)
N_BAL = 40


def _resp(shape_db, ripple=None):
    """Unit-acceleration SPL arrays whose unit-velocity form is shape(f) + taper(angle) (+ ripple)."""
    taper = -6.0 * (ANG / 40.0) ** 2
    base = shape_db[:, None] + taper[None, :] - 20.0 * np.log10(F)[:, None]
    sh = base.copy()
    if ripple is not None:
        sh = sh + ripple
    sv = base.copy()
    bal = shape_db[:, None] - 8.0 + np.zeros((F.size, N_BAL)) - 20.0 * np.log10(F)[:, None]
    return sh, sv, bal


def _terms(sh, sv, bal, f_lo=700.0, f_hi=8000.0):
    c = hr.spin_curves(F, ANG, sh, ANG, sv, bal)
    return c, hr.hifi_terms(c, f_lo, f_hi)


def test_common_shape_has_zero_non_eqable_terms_but_nonzero_broad_shape():
    bump = 3.0 * np.exp(-((np.log2(F) - np.log2(2000.0)) ** 2) / 0.5)   # broad, EQ-able
    _, t = _terms(*_resp(bump))
    assert t["seat_spread_db"] == pytest.approx(0.0, abs=1e-9)
    assert t["xo_spread_db"] == pytest.approx(0.0, abs=1e-9)
    assert t["pir_shape_db"] == pytest.approx(0.0, abs=1e-9)
    assert t["lw_shape_db"] > 0.3          # passive mode sees the bump


def test_flat_design_is_zero_everywhere():
    _, t = _terms(*_resp(np.zeros(F.size)))
    for k in hr.HIFI_KEYS:
        assert t[k] == pytest.approx(0.0, abs=1e-9), k


def test_angle_dependent_ripple_raises_seat_spread():
    rng = np.random.default_rng(0)
    rip = rng.normal(0.0, 1.0, (F.size, ANG.size)) * (np.abs(ANG) > 5)[None, :]
    _, clean = _terms(*_resp(np.zeros(F.size)))
    _, rough = _terms(*_resp(np.zeros(F.size), ripple=rip))
    assert rough["seat_spread_db"] > clean["seat_spread_db"] + 0.3


def test_unit_velocity_conversion_flattens_a_minus_6db_per_octave_drive():
    sh, sv, bal = _resp(np.zeros(F.size))
    c, _ = _terms(sh, sv, bal)
    assert np.ptp(c["on"]) == pytest.approx(0.0, abs=1e-9)


def test_off_grid_angle_is_refused():
    sh, sv, bal = _resp(np.zeros(F.size))
    with pytest.raises(ValueError):
        hr.spin_curves(F, np.arange(-90.0, 91.0, 7.0), sh[:, :27], ANG, sv, bal)


def test_too_few_band_points_gives_nan():
    _, t = _terms(*_resp(np.zeros(F.size)), f_lo=7000.0, f_hi=7500.0)
    assert all(np.isnan(v) for v in t.values())


def test_score_replaces_onaxis_terms_and_adds_weighted_hifi():
    item = {"J_v7": 5.0, "onaxis_v7": 1.5,
            "hifi": {"seat_spread_db": 0.2, "xo_spread_db": 0.4, "pir_shape_db": 0.1,
                     "lw_rough_db": 0.3, "lw_shape_db": 1.0}}
    tol = {k: 0.1 for k in hr.HIFI_KEYS}
    w = dict(hr.DEFAULT_WEIGHTS)
    dsp = hr.score(item, tol, w, hr.DSP_KEYS)
    assert dsp == pytest.approx(3.5 + 1.0 * 2 + 0.5 * 4 + 1.0 * 1 + 0.5 * 3)
    assert hr.score(item, tol, w, hr.PASSIVE_KEYS) == pytest.approx(dsp + 1.0 * 10)
    assert hr.onaxis_contribution({"flat": 2.0, "flat_cv": 1.0, "rip": 9.0},
                                  {"flat": 0.5, "flat_cv": 1.0, "rip": 1.0}) == pytest.approx(2.0)


def test_calibrated_tolerance_is_top_decile_median_with_floor():
    items = [{"J_v7": float(i), "hifi": {k: (0.0 if k == "xo_spread_db" else float(i))
                                          for k in hr.HIFI_KEYS}} for i in range(1, 31)]
    tol = hr.calibrate_tolerances(items)
    assert tol["seat_spread_db"] == pytest.approx(2.0)     # top 3 by J -> values 1,2,3
    assert tol["xo_spread_db"] == pytest.approx(0.05)      # floor


def test_cli_end_to_end(tmp_path):
    run = tmp_path / "runs" / "r1"
    rows = []
    rng = np.random.default_rng(1)
    for i in range(12):
        h = f"d{i:04d}"
        d = run / "designs" / h
        d.mkdir(parents=True)
        rip = rng.normal(0.0, 0.1 * i, (F.size, ANG.size))
        sh, sv, bal = _resp(np.zeros(F.size), ripple=rip)
        np.savez(d / "response.npz", freqs_hz=F, h_angles_deg=ANG, v_angles_deg=ANG,
                 spl_h_db=sh, spl_v_db=sv, spl_balloon_db=bal)
        rows.append({"n": i, "ok": True, "design_hash": h, "objective": 3.0 + 0.1 * i,
                     "objective_version": 7, "terms": {"flat": 0.5, "flat_cv": 0.5}})
    (run / "search.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (run / "config.yaml").write_text(yaml.safe_dump({
        "brief": {"name": "b"}, "target": {"f0_hz": 700.0, "band_hi_hz": 8000.0},
        "weights": {"flat": 0.5, "flat_cv": 1.0}}))
    out = tmp_path / "scratch" / "o"
    assert hr.main(["--run", str(run), "--out", str(out), "--top", "5"]) == 0
    payload = json.loads((out / "hifi_rescore.json").read_text())
    g = payload["groups"]["v7:b"]
    assert g["n"] == 12
    # ripple grows with i and so does J_v7 here -> both rankings agree
    assert g["dsp"]["spearman_vs_v7"] > 0.9
    assert (out / "hifi_rescore.md").read_text().startswith("# Hi-fi re-score")


def test_cli_refuses_out_inside_runs(tmp_path):
    run = tmp_path / "runs" / "r1"
    run.mkdir(parents=True)
    (run / "config.yaml").write_text("{}")
    with pytest.raises(SystemExit):
        hr.main(["--run", str(run), "--out", str(tmp_path / "runs" / "x")])
