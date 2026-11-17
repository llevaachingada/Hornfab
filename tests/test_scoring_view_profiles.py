"""v9 coverage-profile display truth (2026-11-17, amended RFC, orchestrator lane P1-3).

Pins the additive surface that lets the GUI draw the scored corridor without ever
inventing geometry the scorer does not see:

* ``targets.scoring_view.score_window`` — v9 onsets are ``max(anchor1_hz, plane f0)`` and
  the v9 ``cov_narrow_ratio`` default is 1.0 (amendment §B/§D).
* ``build_scoring_view["profile"]`` — mode/interpolation/onsets + a shared 32-point log
  grid carrying per-plane pref/min/max arrays with ``None`` below each plane's own onset
  (v7 targets keep the key absent entirely).
* ``tools.analysis.catalog._target_identity`` — legacy briefs keep the EXACT legacy
  identity dict (byte-stable ``target_hash``); a profile enters only when present.
* ``tools.analysis.cohorts`` — spec/record profile comparison is symmetric and strict.
* ``hornlab_search.dataset.record._target_dict`` — tuple anchors serialise to JSON lists.
"""
from __future__ import annotations

import dataclasses
import math
import sys
from pathlib import Path

import pytest

# ``tools/analysis`` modules import their siblings as top-level modules (``from _common import``);
# make that directory importable the same way the other analysis tool tests do.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "analysis"))

from hornlab_search.targets.scoring_view import build_scoring_view, score_window, _profile_view
from tools.analysis.catalog import _target_block, _target_identity, _sha16
from tools.analysis.cohorts import _record_matches_ath

WEIGHTS = {"cov_profile": 1.0, "rip": 1.0, "flat": 0.5, "load": 1.0,
           "dislope": 1.0, "di_roughness": 1.0, "flat_cv": 1.0}
V9_OBJECTIVE = {"version": 9, "cov_below_f0": "mask", "cov_narrow_ratio": 1.0,
                "tolerances": {"cov_profile": 8.0, "rip": 1.0, "flat": 1.5, "load": 0.3,
                               "dislope": 9.0, "di_roughness": 2.0, "flat_cv": 1.5}}
CORRIDOR_PROFILE = {
    "mode": "corridor", "interpolation": "log_frequency",
    "h": [{"hz": 700.0, "preferred_deg": 80.0, "min_deg": 70.0, "max_deg": 90.0},
          {"hz": 8000.0, "preferred_deg": 43.5, "min_deg": 35.0, "max_deg": 52.0}],
    "v": [{"hz": 700.0, "preferred_deg": 50.0, "min_deg": 40.0, "max_deg": 60.0},
          {"hz": 8000.0, "preferred_deg": 27.0, "min_deg": 20.0, "max_deg": 34.0}],
}
TARGET_PROFILE = {
    "mode": "target", "interpolation": "log_frequency",
    "h": [{"hz": 1000.0, "preferred_deg": 80.0}],          # single anchor: target mode only
    "v": [{"hz": 1000.0, "preferred_deg": 50.0}]}
TARGET_BASE = {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0,
               "band_lo_hz": 350.0, "band_hi_hz": 8000.0, "f0_hz": 700.0}


def _brief_target(profile: dict | None) -> dict:
    out = dict(TARGET_BASE)
    if profile is not None:
        out["coverage_profile"] = profile
    return out


# --------------------------------------------------------------------- score_window (v9)

def test_v9_score_window_uses_profile_onsets_and_ratio():
    window = score_window(_brief_target(CORRIDOR_PROFILE), V9_OBJECTIVE, 9)
    assert window["h_lo_hz"] == 700.0 and window["v_lo_hz"] == 700.0
    assert window["below_mode"] == "mask" and window["narrow_ratio"] == 1.0


def test_v9_onset_is_max_anchor1_f0():
    # anchor 1000 Hz sits above f0 700 -> onset is the anchor, not the f0.
    view = build_scoring_view(_brief_target(TARGET_PROFILE), V9_OBJECTIVE, WEIGHTS, 9)
    assert view["coverage"]["h_lo_hz"] == 1000.0
    assert view["profile"]["onset_h_hz"] == 1000.0


def test_v9_narrow_ratio_default_is_one_even_without_explicit_key():
    obj = {k: v for k, v in V9_OBJECTIVE.items() if k != "cov_narrow_ratio"}
    window = score_window(_brief_target(CORRIDOR_PROFILE), obj, 9)
    assert window["narrow_ratio"] == 1.0


def test_legacy_versions_stay_full_width_even_with_profile_key_present():
    # A profile is v9-only (config refuses it elsewhere); the v7 window ignores it.
    window = score_window(_brief_target(CORRIDOR_PROFILE), {"version": 7}, 7)
    assert window["h_lo_hz"] == 700.0 and window["narrow_ratio"] == 2.0   # v7 default


# ------------------------------------------------------------ build_scoring_view["profile"]

def test_profile_block_corridor_arrays_and_grid():
    view = build_scoring_view(_brief_target(CORRIDOR_PROFILE), V9_OBJECTIVE, WEIGHTS, 9)
    prof = view["profile"]
    assert prof["mode"] == "corridor" and prof["interpolation"] == "log_frequency"
    assert prof["onset_h_hz"] == 700.0 and prof["onset_v_hz"] == 700.0
    assert len(prof["freqs_hz"]) == 32
    assert prof["freqs_hz"][0] == 700.0 and prof["freqs_hz"][-1] == 8000.0
    # grid is ascending log-spaced
    l = [math.log10(f) for f in prof["freqs_hz"]]
    assert all(b > a for a, b in zip(l, l[1:]))
    # endpoints exact; interior log-linear between the two anchors (2-point profile is exact)
    h0, h1 = CORRIDOR_PROFILE["h"][0], CORRIDOR_PROFILE["h"][1]
    for i, f in enumerate(prof["freqs_hz"]):
        frac = (math.log10(f) - math.log10(h0["hz"])) / (math.log10(h1["hz"]) - math.log10(h0["hz"]))
        for arr, key in (("h_pref", "preferred_deg"), ("h_min", "min_deg"), ("h_max", "max_deg")):
            expected = h0[key] + (h1[key] - h0[key]) * frac
            assert prof[arr][i] == pytest.approx(expected, abs=1e-9)
    v0, v1 = CORRIDOR_PROFILE["v"][0], CORRIDOR_PROFILE["v"][1]
    for i, f in enumerate(prof["freqs_hz"]):
        frac = (math.log10(f) - math.log10(v0["hz"])) / (math.log10(v1["hz"]) - math.log10(v0["hz"]))
        assert prof["v_pref"][i] == pytest.approx(v0["preferred_deg"] + (v1["preferred_deg"] - v0["preferred_deg"]) * frac, abs=1e-9)


def test_target_mode_minmax_are_none_and_v7_has_no_profile_key():
    view = build_scoring_view(_brief_target(TARGET_PROFILE), V9_OBJECTIVE, WEIGHTS, 9)
    prof = view["profile"]
    assert all(v is None for v in prof["h_min"] + prof["h_max"] + prof["v_min"] + prof["v_max"])
    assert all(v is not None for v in prof["h_pref"] + prof["v_pref"])
    legacy = build_scoring_view(_brief_target(None), V9_OBJECTIVE, WEIGHTS, 7)
    assert "profile" not in legacy


def test_profile_view_none_on_malformed():
    assert _profile_view({"coverage_profile": {"mode": "corridor", "h": [{"hz": -1}]}}) is None
    assert _profile_view(None) is None


# ------------------------------------------------------------------- catalog identity

def test_identity_profile_absent_keeps_legacy_keys_and_hash():
    without = _target_identity(_brief_target(None))
    legacy_keys = {"coverage_h_deg", "coverage_v_deg", "coverage_v_up_deg", "coverage_v_down_deg",
                   "band_lo_hz", "band_hi_hz", "f0_hz", "f0_v_hz", "di_target_db",
                   "di_slope_target", "z_min", "freq_weights"}
    assert set(without.keys()) == legacy_keys
    with_p = _target_identity(_brief_target(CORRIDOR_PROFILE))
    assert set(with_p.keys()) == legacy_keys | {"coverage_profile"}
    assert _sha16(without) != _sha16(with_p)


def test_target_block_carries_profile_only_when_present():
    assert "coverage_profile" not in _target_block({"target": _brief_target(None)})
    block = _target_block({"target": _brief_target(CORRIDOR_PROFILE)})
    assert block["coverage_profile"]["mode"] == "corridor"
    assert "coverage_profile" in block["raw_keys"]


# -------------------------------------------------------------------------- cohorts gate

def _record(profile):
    return {"provenance": {
                "brief": "room_landscape_80x50_700_hf1440_v7_smooth",
                "brief_hash": "89e7b98566b5"},
            "family": "FREEFORM",
            "objective_version": 9,
            "target": {**TARGET_BASE, "band_lo_hz": 350.0,
                       **({"coverage_profile": profile} if profile is not None else {})}}


def test_cohorts_profile_symmetric_strict_match():
    brief = "room_landscape_80x50_700_hf1440_v7_smooth"
    spec = {"brief": brief, "brief_hash": "89e7b98566b5",
            "family": "FREEFORM", "objective_version": 9,
            "target": {**TARGET_BASE, "coverage_profile": CORRIDOR_PROFILE}}
    ok, why = _record_matches_ath(_record(CORRIDOR_PROFILE), spec)
    assert ok and why is None
    ok2, why2 = _record_matches_ath(_record(None), spec)
    assert not ok2 and why2 == "target_coverage_profile_mismatch"
    spec2 = {"brief": brief, "brief_hash": "89e7b98566b5",
             "family": "FREEFORM", "objective_version": 9, "target": dict(TARGET_BASE)}
    ok3, why3 = _record_matches_ath(_record(CORRIDOR_PROFILE), spec2)
    assert not ok3 and why3 == "target_coverage_profile_mismatch"


def test_cohorts_profile_value_differences_mismatch():
    other = dict(CORRIDOR_PROFILE, h=CORRIDOR_PROFILE["h"][:-1] +
                [{"hz": 8000.0, "preferred_deg": 40.0, "min_deg": 30.0, "max_deg": 50.0}])
    spec = {"brief": "room_landscape_80x50_700_hf1440_v7_smooth", "brief_hash": "89e7b98566b5",
            "family": "FREEFORM", "objective_version": 9,
            "target": {**TARGET_BASE, "coverage_profile": CORRIDOR_PROFILE}}
    ok, why = _record_matches_ath(_record(other), spec)
    assert not ok and why == "target_coverage_profile_mismatch"


# ------------------------------------------------------- dataset record serialisation

def test_target_dict_serialises_tuple_anchors_to_lists():
    @dataclasses.dataclass
    class _T:
        coverage_h_deg: float = 80.0
        coverage_v_deg: float = 50.0
        band_lo_hz: float = 350.0
        band_hi_hz: float = 8000.0
        di_target_db: float | None = None
        coverage_profile_h: tuple | None = ((700.0, 80.0, 70.0, 90.0), (8000.0, 43.5, 35.0, 52.0))
        coverage_profile_v: tuple | None = None

    from hornlab_search.dataset.record import _target_dict
    view = _target_dict(_T())
    assert view["coverage_profile_h"] == [[700.0, 80.0, 70.0, 90.0], [8000.0, 43.5, 35.0, 52.0]]
    assert view["coverage_profile_v"] is None
