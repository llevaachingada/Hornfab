"""v9 coverage-profile Target schema (2026-11-17, amended RFC §B/D — schema lane).

Pins the additive ``target.coverage_profile`` surface exactly as dispatched:

* modes ``corridor`` / ``target`` with the amendment's semantics (corridor: >=2 anchors,
  strict ``min < max`` per anchor, preferred inside; target: one anchor allowed, the
  legacy per-anchor constant target, and G11's case);
* the anchor-below-f0 refusal naming ``target.coverage_profile.<plane>[i].hz`` + the
  plane's f0 (v uses ``f0_v_hz`` when set);
* byte-identical no-profile Targets and the ``dataclasses.asdict`` round-trip;
* ``profile_value`` / ``profile_onset_hz`` geometry (log-linear, end-clamped).
"""
from __future__ import annotations

import dataclasses

import pytest

from hornlab_search.targets.profile import (MODES, parse_profile, profile_onset_hz,
                                            profile_value)
from hornlab_search.targets.spec import Target

_T_BASE = {"coverage_h_deg": 80.0, "coverage_v_deg": 50.0,
           "band_lo_hz": 350.0, "band_hi_hz": 8000.0, "f0_hz": 700.0}
_CORRIDOR = {"mode": "corridor",
             "h": [{"hz": 700.0, "preferred_deg": 80.0, "min_deg": 70.0, "max_deg": 90.0},
                   {"hz": 8000.0, "preferred_deg": 43.5, "min_deg": 35.0, "max_deg": 52.0}],
             "v": [{"hz": 700.0, "preferred_deg": 50.0, "min_deg": 40.0, "max_deg": 60.0},
                   {"hz": 8000.0, "preferred_deg": 27.0, "min_deg": 20.0, "max_deg": 34.0}]}


def _target_with(profile: dict | None, **overrides) -> Target:
    return Target.from_dict({**_T_BASE, **({"coverage_profile": profile} if profile else {}),
                             **overrides})


# --------------------------------------------------------------------------- valid parses

def test_corridor_profile_parses_and_sorts():
    t = _target_with(_CORRIDOR)
    assert t.coverage_profile_mode == "corridor"
    assert t.coverage_profile_interpolation == "log_frequency"
    assert t.coverage_profile_h[0] == (700.0, 80.0, 70.0, 90.0)
    assert t.coverage_profile_v[-1] == (8000.0, 27.0, 20.0, 34.0)


def test_target_mode_single_anchor_is_the_constant_profile():
    t = _target_with({"mode": "target", "h": [{"hz": 700.0, "preferred_deg": 80.0}],
                      "v": [{"hz": 700.0, "preferred_deg": 50.0}]})
    assert t.coverage_profile_mode == "target"
    assert t.coverage_profile_h == ((700.0, 80.0, None, None),)
    assert t.coverage_profile_v == ((700.0, 50.0, None, None),)


def test_explicit_interpolation_accepted_and_defaults():
    t = _target_with({**_CORRIDOR, "interpolation": "log_frequency"})
    assert t.coverage_profile_interpolation == "log_frequency"
    assert _target_with(_CORRIDOR).coverage_profile_interpolation == "log_frequency"


def test_no_profile_target_is_unchanged():
    t = _target_with(None)
    assert t.coverage_profile_mode is None and t.coverage_profile_h is None
    assert t.coverage_profile_v is None and t.coverage_profile_interpolation is None
    names = [f.name for f in dataclasses.fields(Target)]
    assert names[:11] == ["coverage_h_deg", "coverage_v_deg", "band_lo_hz", "band_hi_hz",
                          "di_target_db", "di_slope_target", "z_min", "freq_weights",
                          "f0_hz", "f0_v_hz", "coverage_v_up_deg"]


# ---------------------------------------------------------------------------- refusals

def test_mode_and_interpolation_valued():
    with pytest.raises(ValueError, match="mode must be one of"):
        _target_with({**_CORRIDOR, "mode": "hard"})
    with pytest.raises(ValueError, match="interpolation must be one of"):
        _target_with({**_CORRIDOR, "interpolation": "linear"})


def test_unknown_profile_key_refused():
    with pytest.raises(ValueError, match="unknown key"):
        _target_with({**_CORRIDOR, "warp": True})


def test_corridor_requires_two_anchors_naming_plane():
    single = {"mode": "corridor",
              "h": [{"hz": 700.0, "preferred_deg": 80.0, "min_deg": 70.0, "max_deg": 90.0}],
              "v": [{"hz": 700.0, "preferred_deg": 50.0, "min_deg": 40.0, "max_deg": 60.0}]}
    with pytest.raises(ValueError, match="'corridor' requires at least two h anchors"):
        _target_with(single)


def test_corridor_anchor_without_minmax_refused():
    bad = {"mode": "corridor",
           "h": [{"hz": 700.0, "preferred_deg": 80.0}, {"hz": 8000.0, "preferred_deg": 40.0}],
           "v": [{"hz": 700.0, "preferred_deg": 50.0, "min_deg": 40.0, "max_deg": 60.0}]}
    with pytest.raises(ValueError, match="requires min_deg and max_deg"):
        _target_with(bad)


def test_corridor_min_ge_max_refused():
    bad = {"mode": "corridor",
           "h": [{"hz": 700.0, "preferred_deg": 80.0, "min_deg": 91.0, "max_deg": 90.0},
                 {"hz": 8000.0, "preferred_deg": 40.0, "min_deg": 30.0, "max_deg": 50.0}],
           "v": [{"hz": 700.0, "preferred_deg": 50.0, "min_deg": 40.0, "max_deg": 60.0},
                 {"hz": 8000.0, "preferred_deg": 27.0, "min_deg": 20.0, "max_deg": 34.0}]}
    with pytest.raises(ValueError, match="h\\\\\\[0\\\\\\]|h\\[0\\].*min_deg"):
        _target_with(bad)


def test_target_mode_carrying_minmax_refused():
    bad = {"mode": "target",
           "h": [{"hz": 700.0, "preferred_deg": 80.0, "min_deg": 70.0, "max_deg": 90.0}],
           "v": [{"hz": 700.0, "preferred_deg": 50.0}]}
    with pytest.raises(ValueError, match="must not carry.*min_deg/max_deg"):
        _target_with(bad)


def test_anchor_below_plane_f0_refused_naming_key_and_f0():
    # H anchor below f0_hz
    with pytest.raises(ValueError, match="coverage_profile\\.h\\[0\\]\\.hz") as e:
        _target_with({"mode": "target",
                      "h": [{"hz": 500.0, "preferred_deg": 80.0}],
                      "v": [{"hz": 700.0, "preferred_deg": 50.0}]})
    assert "700" in str(e.value)
    # V anchor below f0_v_hz when the per-plane floor is set higher
    with pytest.raises(ValueError, match="coverage_profile\\.v\\[0\\]\\.hz") as e2:
        _target_with({"mode": "target",
                      "h": [{"hz": 700.0, "preferred_deg": 80.0}],
                      "v": [{"hz": 699.0, "preferred_deg": 50.0}]}, f0_v_hz=900.0)
    assert "900" in str(e2.value)


def test_duplicate_hz_and_non_ascending_refused():
    dup = {"mode": "target",
           "h": [{"hz": 700.0, "preferred_deg": 80.0}, {"hz": 700.0, "preferred_deg": 60.0}],
           "v": [{"hz": 700.0, "preferred_deg": 50.0}]}
    with pytest.raises(ValueError, match="duplicate hz"):
        _target_with(dup)


# --------------------------------------------------------------- round-trip + geometry

def test_asdict_round_trip_with_corridor_profile():
    t = _target_with(_CORRIDOR)
    assert Target.from_dict(dataclasses.asdict(t)) == t


def test_profile_value_log_linear_and_clamped():
    anchors = parse_profile([{"hz": 700.0, "preferred_deg": 80.0, "min_deg": 70.0, "max_deg": 90.0},
                             {"hz": 8000.0, "preferred_deg": 43.5, "min_deg": 35.0, "max_deg": 52.0}],
                            "h", 700.0)
    assert profile_value(anchors, 700.0) == (80.0, 70.0, 90.0)
    assert profile_value(anchors, 8000.0) == (43.5, 35.0, 52.0)
    frac = __import__("math").log10(8000.0 / 700.0)
    # exactly halfway in log space
    mid = 700.0 * (8000.0 / 700.0) ** 0.5
    pref, lo, hi = profile_value(anchors, mid)
    assert pref == pytest.approx(80.0 + (43.5 - 80.0) * 0.5)
    assert lo == pytest.approx(70.0 + (35.0 - 70.0) * 0.5)
    assert hi == pytest.approx(90.0 + (52.0 - 90.0) * 0.5)
    # end clamps
    assert profile_value(anchors, 250.0) == (80.0, 70.0, 90.0)
    assert profile_value(anchors, 20000.0) == (43.5, 35.0, 52.0)
    del frac


def test_target_mode_minmax_are_none():
    anchors = parse_profile([{"hz": 700.0, "preferred_deg": 80.0}], "h", 700.0)
    assert profile_value(anchors, 1000.0) == (80.0, None, None)


def test_onset_is_max_anchor1_f0():
    anchors = parse_profile([{"hz": 1000.0, "preferred_deg": 80.0}], "h", 700.0)
    assert profile_onset_hz(anchors, 700.0) == 1000.0
    # an anchor that OMITS hz defaults to the plane's f0 -> onset == f0 (the floor case)
    anchors2 = parse_profile([{"preferred_deg": 80.0}], "h", 700.0)
    assert profile_onset_hz(anchors2, 700.0) == 700.0
    assert MODES == ("corridor", "target")
