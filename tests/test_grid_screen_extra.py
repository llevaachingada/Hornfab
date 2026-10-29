"""B2 (2026-10-28, amendment): an EXPLICIT extra-frequency list for the SCREEN grid.

Brief ``grid: {screen_extra_hz: [250, 315, 400, 2573, 3311, 4260]}`` merges those points into the
frozen 12-point 500-10000 screen grid (already clipped to band_hi). No density law and no 3 %
dedup: the approved list is explicit. Points above band_hi are dropped; the bottom is never
clipped (250 Hz is below band_lo on purpose: the LFP/loading gate solves it, J does not score it).
Absent keys reproduce the old grid byte-for-byte; the verify/final grids are never touched.
"""
from __future__ import annotations

import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.config import (ConfigError, freq_grid, load_brief, load_config, mode_freqs,
                                   solve_spec)

APPROVED = [250.0, 315.0, 400.0, 2573.0, 3311.0, 4260.0]
#: Exact screen tuple for the 8 kHz brief with APPROVED, sorted and rounded to 2 decimals.
APPROVED_TUPLE = (250.0, 315.0, 400.0, 500.0, 643.33, 827.75, 1065.04, 1370.35, 1763.18,
                  2268.63, 2573.0, 2918.96, 3311.0, 3755.72, 4260.0, 4832.36, 6217.63, 8000.0)

BASE = {
    "name": "test_screen_extra",
    "description": "8 kHz brief for the screen extra-frequency grid tests",
    "driver": {"exit_radius_mm": 12.7, "exit_angle_deg": 5.0},
    "envelope": {"max_mouth_w_mm": 500.0, "max_mouth_h_mm": 500.0, "max_depth_mm": 400.0},
    "symmetry": "hv",
    "target": {"coverage_h_deg": 90.0, "coverage_v_deg": 90.0, "band_lo_hz": 700.0,
               "band_hi_hz": 8000.0, "di_target_db": None, "di_slope_target": 0.0},
    "weights": {"cov": 1.0, "rip": 1.0, "di": 0.3, "dislope": 0.5, "flat": 0.5, "load": 0.0},
}

#: The frozen screen grid clipped to this brief's 8 kHz band, exactly as before B2.
OLD_SCREEN = tuple(freq_grid(500, 8000, 12))


def _brief(tmp_path, grid=None, target=None, name="brief.yaml"):
    brief = {**BASE}
    if grid is not None:
        brief["grid"] = grid
    if target is not None:
        brief["target"] = {**BASE["target"], **target}
    p = tmp_path / name
    p.write_text(yaml.safe_dump(brief), encoding="utf-8")
    return p


def _cfg(tmp_path, grid=None, target=None, name="brief.yaml"):
    return load_config(EXAMPLES / "rosse_baseline.yaml",
                       brief=_brief(tmp_path, grid, target, name=name))


def test_absent_keys_reproduce_the_old_screen_grid(tmp_path):
    cfg = _cfg(tmp_path)
    assert cfg.grid is None
    assert mode_freqs("screen", cfg) == OLD_SCREEN == (
        500.0, 643.33, 827.75, 1065.04, 1370.35, 1763.18, 2268.63, 2918.96, 3755.72,
        4832.36, 6217.63, 8000.0)


def test_approved_list_is_merged_into_exactly_the_expected_tuple(tmp_path):
    cfg = _cfg(tmp_path, grid={"screen_extra_hz": APPROVED})
    assert (cfg.grid or {})["screen_extra_hz"] == APPROVED
    freqs = mode_freqs("screen", cfg)
    assert freqs == APPROVED_TUPLE
    assert len(freqs) == 18
    assert set(OLD_SCREEN) <= set(freqs)               # the frozen grid survives unchanged
    assert freqs == tuple(sorted(freqs))               # sorted
    assert all(round(f, 2) == f for f in freqs)        # rounded to 2 decimals


def test_250_hz_is_kept_below_band_lo(tmp_path):
    """250 Hz is the LFP/loading gate point: below band_lo on purpose, never clipped."""
    cfg = _cfg(tmp_path, grid={"screen_extra_hz": APPROVED},
               target={"band_lo_hz": 300.0}, name="brief_lo300.yaml")
    assert cfg.target_raw["band_lo_hz"] == 300.0
    freqs = mode_freqs("screen", cfg)
    assert 250.0 in freqs
    assert min(freqs) == 250.0


def test_extra_points_above_band_hi_are_dropped(tmp_path):
    cfg = _cfg(tmp_path, grid={"screen_extra_hz": [*APPROVED, 9000.0]})
    freqs = mode_freqs("screen", cfg)
    assert 9000.0 not in freqs
    assert max(freqs) == 8000.0
    assert freqs == APPROVED_TUPLE                          # the above-band point changed nothing


def test_band_hi_clipping_still_works_with_extras(tmp_path):
    cfg = _cfg(tmp_path, grid={"screen_extra_hz": [250.0, 315.0, 400.0, 9000.0]},
               target={"band_hi_hz": 2400.0}, name="brief_24k.yaml")
    freqs = mode_freqs("screen", cfg)
    assert max(freqs) <= 2400.0 + 1e-9
    assert 250.0 in freqs and 315.0 in freqs and 400.0 in freqs


def test_verify_and_final_grids_are_untouched_by_screen_extras(tmp_path):
    plain = _cfg(tmp_path)
    with_extra = _cfg(tmp_path, grid={"screen_extra_hz": APPROVED}, name="brief_extra.yaml")
    for mode in ("verify", "final"):
        assert mode_freqs(mode, with_extra) == mode_freqs(mode, plain)


def test_the_new_screen_tuple_changes_the_solve_hash_only_via_freqs(tmp_path):
    plain = _cfg(tmp_path)
    with_extra = _cfg(tmp_path, grid={"screen_extra_hz": APPROVED}, name="brief_extra.yaml")
    assert solve_spec("screen", with_extra).freqs_hz == APPROVED_TUPLE
    assert solve_spec("screen", with_extra).hash() != solve_spec("screen", plain).hash()
    assert solve_spec("screen", with_extra).extra == solve_spec("screen", plain).extra
    for mode in ("verify", "final"):
        assert solve_spec(mode, with_extra).hash() == solve_spec(mode, plain).hash()


def test_verify_points_per_octave_still_works_alone(tmp_path):
    cfg = _cfg(tmp_path, grid={"verify_points_per_octave": 8})
    assert mode_freqs("screen", cfg) == OLD_SCREEN
    assert 5000.0 in mode_freqs("verify", cfg)


@pytest.mark.parametrize("value, match", [
    (250, "non-empty list"),                       # scalar, not a list
    (True, "non-empty list"),                      # bool, not a list
    ("250", "non-empty list"),                     # string, not a list
    ([], "must not be empty"),
    ([250, True], r"screen_extra_hz\[1\]"),        # bool element
    ([0], r"screen_extra_hz\[0\]"),                # zero
    ([-250], r"screen_extra_hz\[0\]"),             # negative
    ([float("nan")], r"screen_extra_hz\[0\]"),     # non-finite
    ([float("inf")], r"screen_extra_hz\[0\]"),     # non-finite
    ([250, "315"], r"screen_extra_hz\[1\]"),       # non-number element
])
def test_screen_extra_hz_validation_refuses_bad_lists(tmp_path, value, match):
    p = _brief(tmp_path, grid={"screen_extra_hz": value}, name="brief_bad.yaml")
    with pytest.raises(ConfigError, match=match):
        load_brief(p)


def test_unknown_grid_keys_are_still_refused(tmp_path):
    for grid in ({"screen_lo_hz": 250, "screen_lo_points_per_octave": 4},
                 {"screen_points_per_octave": 4},
                 {"screen_extra_hz": APPROVED, "bogus": 1}):
        p = _brief(tmp_path, grid=grid, name="brief_unknown.yaml")
        with pytest.raises(ConfigError, match="unknown key"):
            load_brief(p)
