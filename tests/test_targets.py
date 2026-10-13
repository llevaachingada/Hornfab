"""Contract tests 26-30 for Target, required_mouth_m, feasibility_report, coverage_from_room."""
from __future__ import annotations

import dataclasses

import pytest
import yaml

from conftest import EXAMPLES
from hornlab_search.targets.spec import Target
from hornlab_search.targets.venue import (
    coverage_from_room, feasibility_report, required_mouth_m)

REQUIRED = ("coverage_h_deg", "coverage_v_deg", "band_lo_hz", "band_hi_hz")


# 26
def test_required_mouth_12_inch_example():
    assert required_mouth_m(90.0, 926.0) == pytest.approx(0.3048, abs=0.001)


# 27
def test_required_mouth_second_worked_example():
    assert required_mouth_m(45.0, 1850.0) == pytest.approx(0.3048, abs=0.002)


# 28
def test_coverage_from_symmetric_room():
    t = coverage_from_room(10.0, 5.0, 20.0, 4.0)
    assert 0.0 < t.coverage_h_deg < 180.0
    assert 0.0 < t.coverage_v_deg < 180.0
    assert t.di_target_db is None
    widths = [coverage_from_room(w, 5.0, 20.0, 4.0).coverage_h_deg for w in (4.0, 8.0, 16.0, 30.0)]
    assert widths == sorted(widths) and len(set(widths)) == 4
    assert all(0.0 < h < 180.0 for h in widths)


def test_coverage_from_room_numbers():
    # 10 m wide at 5 m: half-angle atan(1) = 45 deg -> 90 deg total.
    t = coverage_from_room(10.0, 5.0, 20.0, 4.0)
    assert t.coverage_h_deg == pytest.approx(90.0, abs=1e-9)
    # ear 0.8 m below the source: atan(0.8/5) - atan(0.8/20) = 9.0903 - 2.2906 deg.
    assert t.coverage_v_deg == pytest.approx(6.7997, abs=1e-3)


def test_splay_widens_horizontal_coverage_only():
    a = coverage_from_room(10.0, 5.0, 20.0, 4.0)
    b = coverage_from_room(10.0, 5.0, 20.0, 4.0, splay_deg=10.0)
    assert b.coverage_h_deg == pytest.approx(a.coverage_h_deg + 20.0, abs=1e-9)
    assert b.coverage_v_deg == a.coverage_v_deg


def test_deeper_near_row_narrows_coverage():
    a = coverage_from_room(10.0, 4.0, 20.0, 4.0).coverage_h_deg
    b = coverage_from_room(10.0, 8.0, 20.0, 4.0).coverage_h_deg
    assert b < a


@pytest.mark.parametrize("kwargs", [
    dict(listener_width_m=0.0, depth_near_m=5.0, depth_far_m=20.0, height_m=4.0),
    dict(listener_width_m=10.0, depth_near_m=0.0, depth_far_m=20.0, height_m=4.0),
    dict(listener_width_m=10.0, depth_near_m=20.0, depth_far_m=5.0, height_m=4.0),
    dict(listener_width_m=10.0, depth_near_m=5.0, depth_far_m=20.0, height_m=1.0),
    dict(listener_width_m=10.0, depth_near_m=5.0, depth_far_m=5.0, height_m=4.0),   # V = 0
])
def test_coverage_from_room_rejects_bad_geometry(kwargs):
    with pytest.raises(ValueError):
        coverage_from_room(**kwargs)


# 29
def test_feasibility_45_degrees_to_700_hz():
    t = Target(75.0, 45.0, 700.0, 13000.0, None)
    r = feasibility_report(t)
    assert set(r) == {"mouth_h_m", "mouth_v_m", "note"}
    assert r["mouth_v_m"] == pytest.approx(0.81, abs=0.005)
    assert r["mouth_h_m"] == pytest.approx(25400.0 / (700.0 * 75.0), abs=1e-9)
    assert r["mouth_v_m"] > r["mouth_h_m"]
    assert "0.81 m" in r["note"] and "vertical" in r["note"]


def test_feasibility_note_says_whether_it_fits():
    t = Target(75.0, 45.0, 700.0, 13000.0, None)
    assert "cannot be held" in feasibility_report(t, mouth_limit_m=0.4)["note"]
    assert "Both fit" in feasibility_report(t, mouth_limit_m=1.0)["note"]


# 30
@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.yaml")), ids=lambda p: p.name)
def test_from_dict_round_trips_example_targets(path):
    block = yaml.safe_load(path.read_text(encoding="utf-8"))["target"]
    t = Target.from_dict(block)
    for k in REQUIRED:
        assert getattr(t, k) is not None
    assert Target.from_dict(dataclasses.asdict(t)) == t
    assert t.coverage_h_deg == block["coverage_h_deg"] and t.band_hi_hz == block["band_hi_hz"]


def test_from_dict_rejects_missing_unknown_and_none():
    ok = dict(coverage_h_deg=75, coverage_v_deg=45, band_lo_hz=700, band_hi_hz=13000)
    assert Target.from_dict(ok).di_target_db is None
    for k in REQUIRED:
        bad = dict(ok)
        del bad[k]
        with pytest.raises(ValueError):
            Target.from_dict(bad)
        bad[k] = None
        with pytest.raises(ValueError):
            Target.from_dict(bad)
    with pytest.raises(ValueError):
        Target.from_dict({**ok, "coverage_horizontal": 3})
    with pytest.raises(ValueError):
        Target.from_dict({**ok, "band_lo_hz": 20000})
