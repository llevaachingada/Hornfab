"""Scoring-truth view (P0, 2026-11-16): the read-only reconstruction of what each objective
version actually scores from an immutable run config.

Every expectation here is a restatement of scorer semantics, pinned against the live v1-v8
scoring code. No scorer is called and no J is recomputed: these tests prove the *display* helper
reports the same masks/angles/constants the scorer uses.

Pinned numbers come from the 80x50 / f0=700 / band 350-8000 home fixture
(``examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7_smooth.yaml``).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from hornlab_search.targets import scoring_view as SV

# The report fixture: 80 H x 50 V above 700 Hz in a 350-8000 Hz band.
TARGET = {
    "coverage_h_deg": 80.0,
    "coverage_v_deg": 50.0,
    "band_lo_hz": 350.0,
    "band_hi_hz": 8000.0,
    "di_target_db": None,
    "di_slope_target": 5.0,
    "z_min": 0.5,
    "f0_hz": 700.0,
    "f0_v_hz": 700.0,
    "loaded_hi_hz": 5600.0,
}

OBJ_V7 = {
    "version": 7,
    "bw8k_floor": 0.75,
    "cov_below_f0": "mask",
    "cov_narrow_ratio": 1.0,
}

W_V7 = {
    "cov": 1.0,
    "rip": 1.0,
    "di": 0.0,
    "dislope": 1.0,
    "flat": 0.5,
    "load": 1.0,
    "distd": 1.0,
    "diag": 1.0,
    "flat_cv": 1.0,
}

# The exact solved/brief frequency rows used by the handoff fixture.
FREQS = [
    250.0, 315.0, 400.0, 500.0, 643.33, 827.75, 1065.04, 1370.35, 1763.18,
    2268.63, 2573.0, 2918.96, 3311.0, 3755.72, 4260.0, 4832.36, 6217.63, 8000.0,
]
DI_DB = [
    4.445151996885757, 5.650723119117576, 5.181839681558358, 5.527601936350958,
    6.642195607180671, 7.822720301434824, 8.826984653294062, 9.65386757800663,
    10.64292935484801, 11.609191483854266, 12.115260050236188, 12.634486785353864,
    13.16245021463857, 13.725209633170934, 14.31462422953917, 14.896542215720395,
    16.111858275280902, 17.372343482542895,
]
# Last-point H/V widths from the same fixture (the 8 kHz floor samples these two).
BW_H_LAST = 39.47950689800333
BW_V_LAST = 33.85482929647661
BW_H = [float(x) for x in np.linspace(80.0, BW_H_LAST, len(FREQS))]
BW_V = [float(x) for x in np.linspace(55.0, BW_V_LAST, len(FREQS))]
BW_H[-1] = BW_H_LAST
BW_V[-1] = BW_V_LAST

G_FLOOR = 0.75
FLOOR_H = G_FLOOR * 80.0
FLOOR_V = G_FLOOR * 50.0
FLOOR_PENALTY_EXPECTED = (
    (FLOOR_H - BW_H_LAST) ** 2 + (FLOOR_V - BW_V_LAST) ** 2
) / 100.0

# DI reference values for the same 80 x 50 target.
DI_GAUSSIAN_80X50 = 13.079574383820045
DI_CUTS_80X50 = 10.576418879992264


# --------------------------------------------------------------------------- module contract


def test_module_docstring_states_the_p0_contract():
    doc = SV.__doc__ or ""
    assert "P0 scoring-truth view (additive, read-only display truth)" in doc
    assert "never recomputes or changes J" in doc


def test_module_never_imports_gui_code():
    from pathlib import Path

    source = Path(SV.__file__).read_text(encoding="utf-8")
    assert "hornlab_search.gui" not in source
    assert "from ..gui" not in source
    assert "import gui" not in source


# --------------------------------------------------------------------------- score_window


def test_score_window_v7_fixture_is_the_pinned_mask():
    win = SV.score_window(TARGET, OBJ_V7, 7)
    assert isinstance(win, dict)
    assert set(win) == {
        "h_lo_hz", "v_lo_hz", "below_mode", "narrow_ratio", "band_lo_hz", "band_hi_hz",
        "h_deg", "v_deg", "coverage_v_up_deg", "coverage_v_down_deg",
        "fc_hz", "f_pattern_hz", "pattern_beta",
    }
    assert win["h_lo_hz"] == 700.0
    assert win["v_lo_hz"] == 700.0
    assert win["below_mode"] == "mask"
    assert win["narrow_ratio"] == 1.0
    assert win["band_lo_hz"] == 350.0
    assert win["band_hi_hz"] == 8000.0
    assert win["h_deg"] == 80.0
    assert win["v_deg"] == 50.0
    # Signed V halves are absent on the report brief.
    assert win["coverage_v_up_deg"] is None
    assert win["coverage_v_down_deg"] is None
    # v6-only keys are present but None on every other version.
    assert win["fc_hz"] is None
    assert win["f_pattern_hz"] is None
    assert win["pattern_beta"] is None


def test_score_window_v1_v2_are_scored_over_the_whole_band():
    for version in (1, 2):
        win = SV.score_window(TARGET, {}, version)
        assert win["below_mode"] == "scored"
        assert win["h_lo_hz"] == win["v_lo_hz"] == 350.0
        assert win["narrow_ratio"] == 1.0  # v1/v2 have no narrow-side asymmetry


def test_score_window_v3_masks_below_f0_with_band_fallback():
    win = SV.score_window(TARGET, {}, 3)
    assert win["below_mode"] == "mask"
    assert win["h_lo_hz"] == win["v_lo_hz"] == 700.0
    no_f0 = dict(TARGET)
    no_f0.pop("f0_hz")
    win2 = SV.score_window(no_f0, {}, 3)
    assert win2["h_lo_hz"] == win2["v_lo_hz"] == 350.0


def test_score_window_v4_family_reads_below_mode_and_per_plane_f0():
    one_sided = {"cov_below_f0": "one_sided", "cov_narrow_ratio": 1.0}
    for version in (4, 5, 7, 8):
        win = SV.score_window(TARGET, one_sided, version)
        assert win["below_mode"] == "one_sided"
        assert win["narrow_ratio"] == 1.0
        assert win["h_lo_hz"] == 700.0
        assert win["v_lo_hz"] == 700.0
    # A vertical onset above f0 is honoured.
    asym = dict(TARGET, f0_v_hz=900.0)
    win = SV.score_window(asym, {}, 4)
    assert win["h_lo_hz"] == 700.0
    assert win["v_lo_hz"] == 900.0


def test_score_window_v4_defaults_match_the_scorer():
    win = SV.score_window(TARGET, {}, 4)
    assert win["below_mode"] == "mask"       # cov_below_f0 default
    assert win["narrow_ratio"] == 2.0        # cov_narrow_ratio default
    # Only the two scoring modes survive; anything else falls back to mask.
    assert SV.score_window(TARGET, {"cov_below_f0": "scored"}, 4)["below_mode"] == "mask"
    assert SV.score_window(TARGET, {"cov_below_f0": "junk"}, 4)["below_mode"] == "mask"


def test_score_window_v4_v_lo_falls_back_to_h_lo():
    no_f0_v = dict(TARGET)
    no_f0_v.pop("f0_v_hz")
    win = SV.score_window(no_f0_v, {}, 7)
    assert win["v_lo_hz"] == win["h_lo_hz"] == 700.0
    no_f0 = {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0,
             "band_lo_hz": 350.0, "band_hi_hz": 8000.0}
    win2 = SV.score_window(no_f0, {}, 7)
    assert win2["h_lo_hz"] == win2["v_lo_hz"] == 350.0


def test_score_window_carries_signed_v_halves():
    asym = dict(TARGET, coverage_v_up_deg=30.0, coverage_v_down_deg=-20.0)
    win = SV.score_window(asym, {}, 5)
    assert win["coverage_v_up_deg"] == 30.0
    assert win["coverage_v_down_deg"] == -20.0


# --------------------------------------------------------------------------- v6 per-design onset


def test_v6_pattern_onset_is_per_design_from_metric_scalars():
    obj = {"version": 6, "pattern_beta": 1.6, "cov_below_f0": "one_sided"}
    target = dict(TARGET, f0_hz=1200.0, f0_v_hz=1200.0)
    slow = SV.score_window(target, obj, 6, design_scalars={"g_fc_hz": 622.8556566221})
    fast = SV.score_window(target, obj, 6, design_scalars={"g_fc_hz": 900.0})
    assert slow["fc_hz"] == pytest.approx(622.8556566221)
    assert slow["f_pattern_hz"] == pytest.approx(622.8556566221 * 1.6)  # 996.569...
    assert fast["fc_hz"] == pytest.approx(900.0)
    assert fast["f_pattern_hz"] == pytest.approx(1440.0)
    # Per-design proof: same brief/target, different scored cov onset.
    assert slow["f_pattern_hz"] != fast["f_pattern_hz"]
    assert slow["pattern_beta"] == fast["pattern_beta"] == 1.6
    assert slow["below_mode"] == fast["below_mode"] == "one_sided"
    assert slow["narrow_ratio"] == 2.0  # v6 cov_narrow_ratio default
    # h_lo/v_lo are the f0-derived DI-side window; both planes share it in v6.
    assert slow["h_lo_hz"] == slow["v_lo_hz"] == 1200.0


def test_v6_fc_precedence_order():
    target = dict(TARGET, f0_hz=1200.0)
    obj = {"version": 6, "pattern_beta": 2.0}
    # 1) explicit objective fc_hz wins over every design source.
    win = SV.score_window(target, dict(obj, fc_hz=500.0), 6,
                          design_scalars={"fc_hz": 700.0, "g_fc_hz": 900.0})
    assert win["fc_hz"] == 500.0
    assert win["f_pattern_hz"] == 1000.0
    # 2) metric scalar fc_hz beats g_fc_hz.
    win = SV.score_window(target, obj, 6, design_scalars={"fc_hz": 700.0, "g_fc_hz": 900.0})
    assert win["fc_hz"] == 700.0
    # 3) metric scalar g_fc_hz (the scorer reads scalars only — generator knobs are NOT a source;
    #    live-run evidence runs/20261112T113047Z-screen-24053e: metrics never store g_fc_hz).
    win = SV.score_window(target, obj, 6, design_scalars={"g_fc_hz": 900.0})
    assert win["fc_hz"] == 900.0
    # 4) design.json params g_fc_hz is DELIBERATELY unread (the scorer never sees it —
    #    scalar_v6.resolve_fc_hz order is params.fc_hz -> metrics.scalars -> f0 -> band_lo),
    #    so a per-design generator knob must never produce a scored onset the scorer did not use.
    assert SV.score_window(target, obj, 6, design_params={"g_fc_hz": 800.0})["fc_hz"] == 1200.0
    assert SV.score_window(
        target, obj, 6,
        design_params={"grid": {"knobs": {"g_fc_hz": 622.8556566221}}})["fc_hz"] == 1200.0
    # 5) target f0 when no design source exists.
    win = SV.score_window(target, obj, 6, design_scalars={}, design_params={})
    assert win["fc_hz"] == 1200.0
    assert win["f_pattern_hz"] == pytest.approx(2400.0)
    # 6) band_lo when f0 is absent too.
    no_f0 = dict(TARGET)
    no_f0.pop("f0_hz")
    win = SV.score_window(no_f0, obj, 6)
    assert win["fc_hz"] == 350.0


def test_v6_real_run_onset_is_f0_not_generator_knob():
    """Live-run truth (deliverable-1 evidence, runs/20261112T113047Z-screen-24053e): metrics
    scalars carry no fc_hz/g_fc_hz key, so the scorer resolves fc = f0 = 1200 -> f_pattern
    1920 for every design, even though design.json knobs carry g_fc_hz ~623. The view must
    reproduce 1920, never a knob-derived onset."""
    target = dict(TARGET, f0_hz=1200.0)
    obj = {"version": 6, "pattern_beta": 1.6, "cov_below_f0": "one_sided"}
    win = SV.score_window(target, obj, 6,
                          design_scalars={"di_mean_db": 9.7},   # real scalar set has no fc keys
                          design_params={"grid": {"knobs": {"g_fc_hz": 622.8556566221}}})
    assert win["fc_hz"] == 1200.0
    assert win["f_pattern_hz"] == pytest.approx(1920.0)
    assert win["below_mode"] == "one_sided"


def test_v6_invalid_fc_sources_fall_through():
    target = dict(TARGET, f0_hz=1200.0)
    obj = {"version": 6}
    win = SV.score_window(
        target, obj, 6,
        design_scalars={"fc_hz": 0.0, "g_fc_hz": float("nan")},
        design_params={"g_fc_hz": -5.0, "grid": {"g_fc_hz": "junk"}},
    )
    assert win["fc_hz"] == 1200.0
    assert win["pattern_beta"] == 1.6  # default beta
    assert win["f_pattern_hz"] == pytest.approx(1920.0)


def test_v6_junk_or_zero_pattern_beta_uses_the_scorer_default():
    target = dict(TARGET, f0_hz=1000.0)
    for beta in (0.0, -1.0, float("nan"), "junk", None):
        win = SV.score_window(target, {"version": 6, "pattern_beta": beta}, 6)
        assert win["pattern_beta"] == 1.6
        assert win["f_pattern_hz"] == pytest.approx(1600.0)


def test_v6_ignores_f0_v_hz_for_its_di_side_window():
    # scalar_v6._cov_pat_term builds a _PatTarget with f0_v_hz=None: one onset for both planes.
    target = dict(TARGET, f0_hz=700.0, f0_v_hz=1000.0)
    win = SV.score_window(target, {"version": 6}, 6)
    assert win["h_lo_hz"] == win["v_lo_hz"] == 700.0
    assert win["fc_hz"] == 700.0
    assert win["f_pattern_hz"] == pytest.approx(1120.0)


# --------------------------------------------------------------------------- di_summary


def test_di_summary_v7_fixture_is_the_pinned_gaussian_slope_truth():
    di = SV.di_summary(TARGET, W_V7, 7)
    assert set(di) == {
        "level_db", "level_source", "level_scored", "slope_db_per_dec",
        "slope_scored", "anchor_hz",
    }
    assert di["level_db"] == pytest.approx(DI_GAUSSIAN_80X50, abs=1e-9)
    assert di["level_source"] == "gaussian"
    assert di["level_scored"] is False            # di weight 0.0 on the smooth brief
    assert di["slope_db_per_dec"] == 5.0
    assert di["slope_scored"] is True             # dislope weight 1.0
    assert di["anchor_hz"] == 700.0


def test_di_summary_level_weight_gate():
    assert SV.di_summary(TARGET, {"di": 0.3}, 7)["level_scored"] is True
    assert SV.di_summary(TARGET, {"di": 0.0}, 7)["level_scored"] is False
    assert SV.di_summary(TARGET, {}, 7)["level_scored"] is False
    assert SV.di_summary(TARGET, None, 7)["level_scored"] is False
    assert SV.di_summary(TARGET, {"di": None}, 7)["level_scored"] is False


def test_di_summary_v1_uses_cuts_and_v2plus_uses_gaussian():
    v1 = SV.di_summary(TARGET, {"di": 1.0}, 1)
    assert v1["level_source"] == "cuts"
    assert v1["level_db"] == pytest.approx(DI_CUTS_80X50, abs=1e-9)
    for version in (2, 3, 4, 5, 7, 8):
        di = SV.di_summary(TARGET, {"di": 1.0}, version)
        assert di["level_source"] == "gaussian"
        assert di["level_db"] == pytest.approx(DI_GAUSSIAN_80X50, abs=1e-9)


def test_di_summary_explicit_target_level_wins():
    explicit = dict(TARGET, di_target_db=11.25)
    for version in (1, 2, 7):
        di = SV.di_summary(explicit, {"di": 1.0}, version)
        assert di["level_source"] == "explicit"
        assert di["level_db"] == 11.25


def test_di_summary_v6_has_no_level_and_reads_di_rise():
    di = SV.di_summary(TARGET, {"di": 1.0, "di_rise": 0.4}, 6)
    assert di["level_db"] is None
    assert di["level_source"] is None
    assert di["level_scored"] is False             # v6 never scores a DI level
    assert di["slope_db_per_dec"] == 5.0
    assert di["slope_scored"] is True
    assert di["anchor_hz"] == 700.0
    assert SV.di_summary(TARGET, {"di_rise": 0.0}, 6)["slope_scored"] is False
    assert SV.di_summary(TARGET, {}, 6)["slope_scored"] is False


def test_di_summary_explicit_level_is_still_none_on_v6():
    explicit = dict(TARGET, di_target_db=11.25)
    di = SV.di_summary(explicit, {"di": 1.0}, 6)
    assert di["level_db"] is None
    assert di["level_source"] is None


def test_di_summary_slope_weight_gate_and_missing_weights():
    assert SV.di_summary(TARGET, {"dislope": 0.0}, 7)["slope_scored"] is False
    assert SV.di_summary(TARGET, {"dislope": -1.0}, 7)["slope_scored"] is True
    assert SV.di_summary(TARGET, {"di": 1.0}, 7)["slope_scored"] is False  # weight missing -> 0
    # v6 reads di_rise, never dislope.
    assert SV.di_summary(TARGET, {"dislope": 1.0}, 6)["slope_scored"] is False


def test_di_summary_anchor_falls_back_to_band_lo():
    no_f0 = dict(TARGET)
    no_f0.pop("f0_hz")
    assert SV.di_summary(no_f0, {}, 7)["anchor_hz"] == 350.0


def test_di_summary_malformed_or_unsupported_returns_none():
    assert SV.di_summary({}, {}, 7) is None
    assert SV.di_summary(dict(TARGET, coverage_h_deg=None), {}, 7) is None
    assert SV.di_summary(TARGET, {}, 0) is None
    assert SV.di_summary(TARGET, {}, 9) is None
    assert SV.di_summary(TARGET, {}, None) is None


# --------------------------------------------------------------------------- bw8k_floor


def test_bw8k_floor_matches_the_scorer_fixture():
    floor = SV.bw8k_floor(TARGET, OBJ_V7, 7, FREQS, BW_H, BW_V)
    assert floor is not None
    assert set(floor) == {
        "floor_hz", "floor_h_deg", "floor_v_deg",
        "min_bw_h_deg", "min_bw_v_deg", "penalty_raw",
    }
    assert floor["floor_hz"] == 8000.0
    assert floor["floor_h_deg"] == 60.0
    assert floor["floor_v_deg"] == 37.5
    assert floor["min_bw_h_deg"] == pytest.approx(BW_H_LAST)
    assert floor["min_bw_v_deg"] == pytest.approx(BW_V_LAST)
    assert floor["penalty_raw"] == pytest.approx(FLOOR_PENALTY_EXPECTED, abs=1e-9)
    assert floor["penalty_raw"] == pytest.approx(4.3437, abs=1e-3)


def test_bw8k_floor_samples_the_last_frequency_at_or_below_the_cap():
    target = dict(TARGET, band_hi_hz=6000.0)
    floor = SV.bw8k_floor(target, OBJ_V7, 7, FREQS, BW_H, BW_V)
    assert floor["floor_hz"] == 4832.36            # index 15 is the last sample <= 6000
    assert floor["floor_h_deg"] == pytest.approx(60.0)  # ratio * target, not * sample


def test_bw8k_floor_only_charges_narrowing():
    wide_h = [200.0] * len(FREQS)
    wide_v = [200.0] * len(FREQS)
    floor = SV.bw8k_floor(TARGET, OBJ_V7, 7, FREQS, wide_h, wide_v)
    assert floor["penalty_raw"] == 0.0


def test_bw8k_floor_is_version_agnostic_when_the_key_is_present():
    # The contract: any version that carries a finite positive bw8k_floor is reconstructed.
    for version in (4, 5, 7, 8):
        floor = SV.bw8k_floor(TARGET, OBJ_V7, version, FREQS, BW_H, BW_V)
        assert floor is not None
        assert floor["floor_hz"] == 8000.0


def test_bw8k_floor_none_when_absent_or_unbuildable():
    assert SV.bw8k_floor(TARGET, {}, 7, FREQS, BW_H, BW_V) is None
    assert SV.bw8k_floor(TARGET, {"bw8k_floor": 0.0}, 7, FREQS, BW_H, BW_V) is None
    assert SV.bw8k_floor(TARGET, {"bw8k_floor": -0.75}, 7, FREQS, BW_H, BW_V) is None
    assert SV.bw8k_floor(TARGET, {"bw8k_floor": float("nan")}, 7, FREQS, BW_H, BW_V) is None
    assert SV.bw8k_floor(TARGET, {"bw8k_floor": "junk"}, 7, FREQS, BW_H, BW_V) is None
    assert SV.bw8k_floor(TARGET, OBJ_V7, 7, [], [], []) is None
    assert SV.bw8k_floor(TARGET, OBJ_V7, 7, [9000.0], [40.0], [30.0]) is None  # above cap
    assert SV.bw8k_floor(TARGET, OBJ_V7, 7, FREQS, BW_H[:-1], BW_V) is None     # thin
    assert SV.bw8k_floor({}, OBJ_V7, 7, FREQS, BW_H, BW_V) is None              # no target
    nan_tail = list(BW_H)
    nan_tail[-1] = float("nan")
    assert SV.bw8k_floor(TARGET, OBJ_V7, 7, FREQS, nan_tail, BW_V) is None


# --------------------------------------------------------------------------- diag_summary


def test_diag_summary_reference_and_weight():
    diag = SV.diag_summary(TARGET, {"diag": 1.0})
    assert diag == {"reference_deg": 65.0, "scored": True}
    assert SV.diag_summary(TARGET, {"diag": 0.0})["scored"] is False
    assert SV.diag_summary(TARGET, {})["scored"] is False
    assert SV.diag_summary(TARGET, None)["scored"] is False
    assert SV.diag_summary({}, {"diag": 1.0}) is None


# --------------------------------------------------------------------------- measured_di_slope


def test_measured_di_slope_matches_the_fixture_over_the_scored_band():
    slope = SV.measured_di_slope(FREQS, DI_DB, 700.0)
    assert slope == pytest.approx(9.567573280356504, abs=1e-9)


def test_measured_di_slope_excludes_below_onset_and_drops_nonfinite():
    all_points = SV.measured_di_slope(FREQS, DI_DB, 350.0)
    assert all_points == pytest.approx(9.347449114741151, abs=1e-9)
    assert all_points != pytest.approx(SV.measured_di_slope(FREQS, DI_DB, 700.0))
    # A non-finite level below the onset changes nothing.
    noisy = list(DI_DB)
    noisy[0] = float("nan")
    assert SV.measured_di_slope(FREQS, noisy, 700.0) == pytest.approx(9.567573280356504, abs=1e-9)
    # Non-finite frequency is dropped too.
    bad_f = list(FREQS)
    bad_f[0] = float("nan")
    assert SV.measured_di_slope(bad_f, DI_DB, 350.0) == pytest.approx(
        SV.measured_di_slope(FREQS, DI_DB, 350.0), abs=1e-12)


def test_measured_di_slope_needs_two_points():
    assert SV.measured_di_slope(FREQS, DI_DB, 9000.0) is None
    assert SV.measured_di_slope([700.0], [10.0], 700.0) is None
    assert SV.measured_di_slope([700.0, 700.0], [10.0, 11.0], 700.0) is None  # degenerate x
    assert SV.measured_di_slope(FREQS, DI_DB[:-1], 700.0) is None            # length mismatch
    assert SV.measured_di_slope([], [], 700.0) is None


# --------------------------------------------------------------------------- build_scoring_view


def test_build_scoring_view_payload_is_the_pinned_assembly():
    view = SV.build_scoring_view(TARGET, OBJ_V7, W_V7, 7)
    assert isinstance(view, dict)
    assert set(view) == {
        "objective_version", "coverage", "di", "bw8k_floor", "diag", "notes",
    }
    assert view["objective_version"] == 7
    assert view["coverage"] == SV.score_window(TARGET, OBJ_V7, 7)
    assert view["di"] == SV.di_summary(TARGET, W_V7, 7)
    assert view["diag"] == SV.diag_summary(TARGET, W_V7)
    assert view["bw8k_floor"] is None  # no frequency arrays supplied
    assert view["notes"] == {
        "distd": (
            "std(DI) raw spread over the score band - NOT residual roughness; a perfectly "
            "linear rise keeps distd > 0"
        ),
        "di_slope": (
            "slope-only scoring is translation invariant in dB; the intercept is not scored "
            "when di weight is 0"
        ),
        "illustrative_corridor": (
            "any hypothetical narrowing curve drawn by the GUI is display-only, NOT the scored "
            "target; it may violate the 8 kHz floor"
        ),
    }


def test_build_scoring_view_wires_the_floor_and_accepts_di_db():
    view = SV.build_scoring_view(
        TARGET, OBJ_V7, W_V7, 7,
        freqs_hz=FREQS, bw_h_deg=BW_H, bw_v_deg=BW_V, di_db=DI_DB,
    )
    assert view["bw8k_floor"] == SV.bw8k_floor(TARGET, OBJ_V7, 7, FREQS, BW_H, BW_V)
    assert view["bw8k_floor"]["floor_hz"] == 8000.0
    # di_db is accepted (the measured slope is exposed by measured_di_slope, not in the payload).
    assert "measured_di_slope" not in view


def test_build_scoring_view_forwards_v6_design_sources():
    target = dict(TARGET, f0_hz=1200.0, f0_v_hz=1200.0)
    obj = {"version": 6, "pattern_beta": 1.6, "cov_below_f0": "one_sided"}
    view = SV.build_scoring_view(
        target, obj, {"di_rise": 0.4}, 6,
        design_scalars={"g_fc_hz": 622.8556566221},
    )
    assert view["coverage"]["fc_hz"] == pytest.approx(622.8556566221)
    assert view["coverage"]["f_pattern_hz"] == pytest.approx(996.5690505953601)
    assert view["di"]["slope_scored"] is True
    assert view["di"]["level_db"] is None


def test_build_scoring_view_is_none_for_an_unsupported_version():
    assert SV.build_scoring_view(TARGET, OBJ_V7, W_V7, 0) is None
    assert SV.build_scoring_view(TARGET, OBJ_V7, W_V7, 9) is None
    assert SV.build_scoring_view(TARGET, OBJ_V7, W_V7, None) is None
    assert SV.build_scoring_view(TARGET, OBJ_V7, W_V7, True) is None


def test_build_scoring_view_never_raises_on_dicts_of_none():
    none_target = {
        "coverage_h_deg": None, "coverage_v_deg": None,
        "band_lo_hz": None, "band_hi_hz": None,
        "di_target_db": None, "di_slope_target": None, "f0_hz": None, "f0_v_hz": None,
    }
    none_objective = {"version": None, "bw8k_floor": None, "cov_below_f0": None,
                      "cov_narrow_ratio": None, "pattern_beta": None, "fc_hz": None}
    none_weights = {"di": None, "dislope": None, "di_rise": None, "diag": None}
    view = SV.build_scoring_view(
        none_target, none_objective, none_weights, 7,
        design_scalars={"fc_hz": None, "g_fc_hz": None},
        design_params={"g_fc_hz": None, "grid": {"g_fc_hz": None}},
        freqs_hz=[None], bw_h_deg=[None], bw_v_deg=[None], di_db=[None],
    )
    assert isinstance(view, dict)
    assert view["coverage"] is None
    assert view["di"] is None
    assert view["bw8k_floor"] is None
    assert view["diag"] is None
    assert view["notes"]  # static display caveats survive malformed inputs


# --------------------------------------------------------------------------- malformed inputs


def test_score_window_malformed_target_or_version_returns_none():
    assert SV.score_window({}, None, 7) is None
    assert SV.score_window(None, None, 7) is None
    assert SV.score_window([], {}, 7) is None
    assert SV.score_window({"coverage_h_deg": 80.0}, {}, 7) is None
    assert SV.score_window(dict(TARGET, band_lo_hz=None), {}, 7) is None
    assert SV.score_window(dict(TARGET, band_hi_hz=350.0), {}, 7) is None  # not > band_lo
    assert SV.score_window(dict(TARGET, coverage_v_deg=0.0), {}, 7) is None
    assert SV.score_window(TARGET, {}, 0) is None
    assert SV.score_window(TARGET, {}, 9) is None
    assert SV.score_window(TARGET, {}, None) is None
    assert SV.score_window(TARGET, {}, True) is None
    assert SV.score_window(TARGET, {}, 7.5) is None


def test_score_window_never_raises_on_non_mapping_objective_and_design_sources():
    win = SV.score_window(TARGET, "not-a-mapping", 6,
                          design_scalars="junk", design_params=42)
    assert win["fc_hz"] == 700.0
    assert win["pattern_beta"] == 1.6


def test_public_api_is_exported():
    assert set(SV.__all__) == {
        "score_window", "di_summary", "bw8k_floor", "diag_summary",
        "measured_di_slope", "build_scoring_view",
    }
    for name in SV.__all__:
        assert callable(getattr(SV, name))
