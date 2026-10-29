"""Unit tests for ``tools/rescore/gate_audit.py``.

Tiny synthetic dicts only: no stored runs, no meshes, no GPU, no solver. The analytic expectations
are the gate definitions in the tool docstring, not the tool's own implementation.
"""
from __future__ import annotations

import importlib.util
import math
import sys

import numpy as np
import pytest

from conftest import REPO

TOOL = REPO / "tools" / "rescore" / "gate_audit.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("gate_audit_tool", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ga = _load_tool()


# ------------------------------------------------------------------ interpolation


def test_log_interpolation_is_geometric_and_never_extrapolates():
    assert ga.interp_log_f([100.0, 400.0], [0.0, 2.0], 200.0) == pytest.approx(1.0)
    assert ga.interp_log_f([100.0, 200.0, 400.0], [1.0, 2.0, 4.0], 400.0) == pytest.approx(4.0)
    # log(200/100) / log(400/100) = 0.5
    assert ga.interp_log_f([100.0, 400.0], [1.0, 3.0], 200.0) == pytest.approx(2.0)
    assert math.isnan(ga.interp_log_f([100.0, 400.0], [1.0, 3.0], 50.0))
    assert math.isnan(ga.interp_log_f([100.0, 400.0], [1.0, 3.0], 500.0))


def test_crossing_freq_interpolates_in_log_frequency():
    # z crosses 0.20 between 200 Hz (0.15) and 400 Hz (0.25): halfway in log f.
    f = [100.0, 200.0, 400.0, 800.0]
    z = [0.10, 0.15, 0.25, 0.60]
    freq, note = ga.crossing_freq(f, z, ga.LFP_RE_Z)
    assert note == ""
    assert freq == pytest.approx(200.0 * math.sqrt(2.0))


# ------------------------------------------------------------------ H gate


def test_h_gate_passes_at_the_inclusive_tolerance_and_inside_band():
    # 72/90 = 0.80 and 108/90 = 1.20 are exactly the +/-20% edges.
    res = ga.gate_h([500, 1000, 2000, 4000, 8000], [72, 90, 108, 90, 90], 90, 500, 8000)
    assert res.passed and not res.unresolved


def test_h_gate_fails_when_one_sample_is_outside_tolerance():
    res = ga.gate_h([500, 1000, 2000, 4000, 8000], [90, 70, 90, 90, 90], 90, 500, 8000)
    assert not res.passed and not res.unresolved
    assert "1 of 5" in res.reason


def test_h_gate_unresolved_when_fx_is_below_the_solved_grid():
    res = ga.gate_h([500, 1000, 2000], [90, 90, 90], 90, 400, 8000)
    assert not res.passed and res.unresolved
    assert "below the lowest solved frequency" in res.reason


def test_h_gate_unresolved_when_no_sample_lies_in_the_band():
    res = ga.gate_h([500, 1000], [90, 90], 90, 9000, 8000)
    assert not res.passed and res.unresolved
    assert "no solved sample" in res.reason


# ------------------------------------------------------------------ V gate


def test_v_gate_uses_the_asymmetric_060_to_125_window():
    f = [500, 1000, 2000, 4000, 8000]
    # 0.60 and 1.25 pass; 0.79 (would fail a +/-20% window) and 1.21 (would also fail) pass.
    res = ga.gate_v(f, [0, 54, 71.1, 112.5, 90], 90, 500, 1000, 8000)
    assert res.passed and not res.unresolved
    low = ga.gate_v(f, [0, 53.9, 90, 90, 90], 90, 500, 1000, 8000)
    high = ga.gate_v(f, [0, 54, 90, 112.6, 90], 90, 500, 1000, 8000)
    assert not low.passed and not low.unresolved
    assert not high.passed and not high.unresolved


def test_v_gate_window_starts_at_max_1_5fx_and_f0v():
    # f0_v = 1000 Hz beats 1.5 * 500 Hz, so the 800 Hz sample is outside the gate window.
    f = [500, 800, 1000, 2000, 4000, 8000]
    res = ga.gate_v(f, [90, 999, 54, 90, 108.9, 90], 90, 500, 1000, 8000)
    assert res.passed and not res.unresolved


def test_v_gate_is_unresolved_when_the_window_has_no_samples():
    res = ga.gate_v([500, 1000], [90, 90], 90, 500, 1000, 8000)
    # window [1000, 8000] does have 1000; use a grid that ends below the window instead
    assert res.passed
    res = ga.gate_v([500, 600], [90, 90], 90, 500, 1000, 8000)
    assert not res.passed and res.unresolved


# ------------------------------------------------------------------ DI rise gate


def test_di_rise_gate_uses_max_minus_min_only_inside_the_band():
    f = [300, 500, 1000, 2000, 4000, 8000]
    # The 300 Hz sample (0 dB) is outside [500, 8000] and must not affect the rise.
    di = [0.0, 10.0, 10.5, 12.0, 11.0, 10.0]
    res = ga.gate_di_rise(f, di, 500, 8000)
    assert res.passed and res.value == pytest.approx(2.0)
    res = ga.gate_di_rise(f, [0.0, 10.0, 10.5, 16.0, 11.0, 10.0], 500, 8000)
    assert not res.passed and not res.unresolved
    assert "DI rise 6.000" in res.reason


def test_di_rise_gate_is_unresolved_without_in_band_samples():
    res = ga.gate_di_rise([9000, 10000], [8.0, 9.0], 500, 8000)
    assert not res.passed and res.unresolved


# ------------------------------------------------------------------ BW8K gate


def test_bw8k_floor_uses_the_top_solved_frequency_and_flags_below_band_hi():
    res = ga.gate_bw8k([500, 1000, 2000, 4000], [90, 90, 90, 67.5],
                       [90, 90, 90, 67.5], 90, 90, 8000)
    assert res.gate.passed and res.top_below_band_hi
    assert res.freq_hz == 4000.0
    failed = ga.gate_bw8k([500, 1000, 2000, 4000], [90, 90, 90, 67.4],
                          [90, 90, 90, 67.5], 90, 90, 8000)
    assert not failed.gate.passed and not failed.gate.unresolved


def test_bw8k_is_unresolved_when_nothing_is_at_or_below_band_hi():
    res = ga.gate_bw8k([9000], [90], [90], 90, 90, 8000)
    assert not res.gate.passed and res.gate.unresolved


# ------------------------------------------------------------------ loading / LFP20


def test_loading_gate_computes_lfp20_50_70_and_rez():
    f = [100, 200, 400, 800]
    z = [0.0, 0.5, 0.7, 1.0]
    res = ga.gate_loading(f, z, f_x=400)
    assert res.gate.passed and not res.gate.unresolved
    assert res.lfp50_hz == pytest.approx(200.0)
    assert res.lfp70_hz == pytest.approx(400.0)
    # 0.20 crossing: 100 * (200/100) ** (0.20/0.50) = 131.95 Hz
    assert res.lfp20_hz == pytest.approx(100.0 * 2.0 ** 0.4)
    assert res.rez_at_fx == pytest.approx(0.7)
    assert res.rez_min_from_fx == pytest.approx(0.7)


def test_loading_gate_resolved_low_when_grid_starts_above_lfp20():
    f = [100, 200, 400]
    z = [0.25, 0.55, 0.60]
    res = ga.gate_loading(f, z, f_x=200)
    assert res.gate.passed and not res.gate.unresolved
    assert res.lfp20_hz == 100.0
    assert res.lfp20_note == "<= 100"


def test_loading_gate_resolved_low_still_fails_the_crossover_ratio():
    res = ga.gate_loading([100, 200], [0.25, 0.60], f_x=150)
    assert not res.gate.passed and not res.gate.unresolved
    assert res.lfp20_hz == 100.0
    assert "LFP20" in res.gate.reason


def test_loading_gate_unresolved_when_lfp20_crossing_is_above_the_grid():
    res = ga.gate_loading([100, 200], [0.10, 0.15], f_x=200)
    assert not res.gate.passed and res.gate.unresolved
    assert res.lfp20_hz is None
    assert "no upward crossing" in res.lfp20_note


def test_loading_gate_requires_rez_loaded_above_fx():
    res = ga.gate_loading([100, 200, 400, 800], [0.10, 0.20, 0.40, 0.60], f_x=400)
    assert not res.gate.passed and not res.gate.unresolved
    assert "Re z" in res.gate.reason


def test_loading_gate_unresolved_without_fx_samples():
    res = ga.gate_loading([100, 200], [0.10, 0.30], f_x=500)
    assert not res.gate.passed and res.gate.unresolved


# ------------------------------------------------------------------ throat gate


def test_throat_gate_fails_a_stretched_or_non_round_throat():
    stretched = ga.gate_throat(
        {"width_mm": 26.0, "height_mm": 36.0, "roundness": 1.0}, 36.0
    )
    assert not stretched.passed and not stretched.unresolved
    assert "26.0 x 36.0" in stretched.reason
    squarish = ga.gate_throat(
        {"width_mm": 36.0, "height_mm": 36.0, "roundness": 1.1}, 36.0
    )
    assert not squarish.passed and "not round" in squarish.reason


def test_throat_gate_passes_a_round_exit_and_unresolves_a_missing_mesh():
    ok = ga.gate_throat({"width_mm": 36.0, "height_mm": 36.0, "roundness": 1.0}, 36.0)
    assert ok.passed and not ok.unresolved
    missing = ga.gate_throat(None, 36.0)
    assert not missing.passed and missing.unresolved
    unreadable = ga.gate_throat(
        {"width_mm": float("nan"), "height_mm": float("nan"), "roundness": float("nan")}, 36.0
    )
    assert not unreadable.passed and unreadable.unresolved


# ------------------------------------------------------------------ stored-row parsing


def _raw_row(design_hash="abc123", objective_version=None, **overrides):
    row = {
        "ok": True,
        "design_hash": design_hash,
        "mesh_hash": "def456",
        "family": "OSSE",
        "objective": 1.25,
        "n_dof": 1234,
        "seconds": {"mesh": 1.0, "solve": 2.0, "total": 3.0},
        "metrics": {
            "freqs_hz": [500, 1000, 2000, 4000, 8000],
            "bw_h_deg": [90, 90, 90, 90, 90],
            "bw_v_deg": [90, 90, 90, 90, 90],
            "di_db": [9.0, 10.0, 11.0, 11.0, 10.0],
            "z_throat_real": [0.01, 0.2, 0.5, 0.8, 1.0],
        },
    }
    if objective_version is not None:
        row["objective_version"] = objective_version
    row.update(overrides)
    return row


def test_row_parsing_is_objective_version_agnostic():
    v4 = _raw_row(objective_version=4, terms={"cov": 1.0, "total": 1.25})
    v5 = _raw_row(objective_version=5, terms=None, family="R-OSSE")
    p4 = ga.parse_stored_row(v4, "screen")
    p5 = ga.parse_stored_row(v5, "verify")
    assert p4 is not None and p5 is not None
    assert p4["design"] == p5["design"] == "abc123"
    assert p4["mesh_hash"] == p5["mesh_hash"] == "def456"
    assert p4["J"] == p5["J"] == pytest.approx(1.25)
    assert p4["seconds_total"] == p5["seconds_total"] == pytest.approx(3.0)
    assert np.array_equal(p4["freqs"], p5["freqs"])
    assert np.array_equal(p4["bw_h"], p5["bw_h"])
    assert p4["z_real"] is not None and np.array_equal(p4["z_real"], p5["z_real"])
    # A row with no objective_version at all is read the same way.
    p_absent = ga.parse_stored_row(_raw_row(), "screen")
    assert p_absent is not None and p_absent["design"] == "abc123"


def test_parse_drops_failed_or_metricless_rows():
    assert ga.parse_stored_row(_raw_row(ok=False), "screen") is None
    assert ga.parse_stored_row(_raw_row(metrics=None), "screen") is None
    assert ga.parse_stored_row(_raw_row(metrics={"freqs_hz": []}), "screen") is None


def test_verify_rows_replace_screen_rows_for_the_same_design_only():
    screen = [
        _raw_row(design_hash="a", objective=1.0),
        _raw_row(design_hash="b", objective=2.0),
    ]
    verify = [_raw_row(design_hash="a", objective=1.5)]
    selected = ga.select_rows(screen, verify)
    assert [(tier, row["design"]) for tier, row in selected] == [
        ("verify", "a"),
        ("screen", "b"),
    ]
