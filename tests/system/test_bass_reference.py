"""Tests for ``hornlab_search.system.bass_reference`` (Lane B, Stage 1).

The wrapper must not contain a second lumped model: the physics is ``tools/bassbox.py`` loaded by
path. These tests pin the pass-through, the textbook B4 alignment *through* the wrapper, the
derived-port bookkeeping, the SYS-10 zero-volume refusal and the LF report shape.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]

from hornlab_search.meh.drivers import ConeDriver  # noqa: E402
from hornlab_search.system import bass_reference as br  # noqa: E402
from hornlab_search.system.contracts import BoxPoint, VentedBoxRanges  # noqa: E402

bb = br.bassbox


# --------------------------------------------------------------------------- synthetic driver

def _synthetic_driver(qts=0.383, fs=35.0, qms=10.0, mms_g=100.0, sd_cm2=500.0,
                      re_ohm=6.0) -> ConeDriver:
    """The textbook-alignment recipe from ``tests/test_bassbox.py`` (test-only)."""
    mms = mms_g * 1e-3
    sd = sd_cm2 * 1e-4
    qes = qts * qms / (qms - qts)
    bl = math.sqrt(2.0 * math.pi * fs * mms * re_ohm / qes)
    cms = 1.0 / ((2.0 * math.pi * fs) ** 2 * mms)
    vas_l = 1.2041 * 343.0 ** 2 * sd ** 2 * cms * 1e3
    return ConeDriver.from_dict({
        "name": "B4 reference",
        "kind": "cone",
        "re_ohm": re_ohm,
        "le_mh": 0.0,
        "bl_tm": bl,
        "sd_cm2": sd_cm2,
        "xmax_mm": 20.0,
        "p_aes_w": 500.0,
        "fs_hz": fs,
        "qms": qms,
        "mms_g": mms_g,
        "cms_mm_per_n": cms * 1e3,
        "vas_l": vas_l,
        "cutout_mm": 250.0,
        "depth_mm": 120.0,
        "source": "synthetic (test only)",
    })


def _relative(spl, f, lo=5.0, hi=8.0, fs=35.0):
    ref = float(np.mean(spl[(f >= lo * fs) & (f <= hi * fs)]))
    return spl - ref


def _b4_point(d: ConeDriver) -> BoxPoint:
    """B4: Vb = Vas/sqrt(2), fb = fs, lossless textbook parameters via the wrapper overrides."""
    vb_l = d.vas_l / math.sqrt(2.0)
    area_cm2 = 200.0
    l_eff_m = bb.port_effective_length(vb_l * 1e-3, d.fs_hz, area_cm2 * 1e-4)
    return BoxPoint(
        kind="vented",
        external_width_mm=420.0,
        external_height_mm=620.0,
        external_depth_mm=360.0,
        net_volume_l=vb_l,
        wall_mm=18.0,
        port_type="round_flared",
        port_throat_area_cm2=area_cm2,
        port_nfr=0.0,
        requested_tuning_hz=d.fs_hz,
        derived_effective_port_length_m=l_eff_m,
        derived_tuning_hz=d.fs_hz,
        fits={},
    )


# --------------------------------------------------------------------------- pass-through

def test_evaluate_wrapper_equals_direct_bassbox() -> None:
    """The contract-point wrapper returns exactly the direct ``bassbox.evaluate`` state."""
    d = _synthetic_driver()
    ranges = VentedBoxRanges(
        net_volume_l_range=(55.0, 65.0),
        tuning_hz_range=(40.0, 55.0),
        port_throat_area_cm2_range=(60.0, 120.0),
    )
    points = br.feasible_boxes(d, ranges)
    assert points, "the screening grid produced no feasible box"
    point = points[0]
    direct_box = bb.Box(
        "vented",
        point.net_volume_l,
        point.derived_tuning_hz,
        point.port_throat_area_cm2,
        br.port_neck_length_mm(point),
    )
    f = np.geomspace(20.0, 200.0, 37)
    wrapped = br.evaluate(f, d, point)
    direct = bb.evaluate(f, d, direct_box)

    np.testing.assert_allclose(wrapped.spl_db, direct.spl_db, rtol=1e-12, atol=0.0)
    np.testing.assert_allclose(wrapped.z_in_ohm, direct.z_in_ohm, rtol=1e-12, atol=0.0)
    np.testing.assert_allclose(wrapped.x_peak_mm, direct.x_peak_mm, rtol=1e-12, atol=0.0)
    np.testing.assert_allclose(wrapped.port_v_peak_mps, direct.port_v_peak_mps,
                               rtol=1e-12, atol=0.0)


def test_box_point_round_trips_to_the_same_tuning() -> None:
    d = _synthetic_driver()
    points = br.feasible_boxes(d, VentedBoxRanges())
    assert points
    for point in points[:5]:
        box = br.box_point_to_bassbox(point)
        assert box.tuning_hz == pytest.approx(point.derived_tuning_hz, rel=1e-12)


# --------------------------------------------------------------------------- B4 through wrapper

def test_textbook_b4_is_still_minus_3db_at_fs_through_the_wrapper() -> None:
    """Reuses the tests/test_bassbox.py B4 recipe, but constructs and evaluates via contract points."""
    d = _synthetic_driver()
    point = _b4_point(d)
    f = np.geomspace(5.0, 400.0, 800)
    state = br.evaluate(f, d, point, q_leak=1e9, q_port=1e9, n_end=0.0)
    spl = _relative(state.spl_db, f)
    at_fs = float(np.interp(math.log(d.fs_hz), np.log(f), spl))
    at_2fs = float(np.interp(math.log(2.0 * d.fs_hz), np.log(f), spl))
    assert at_fs == pytest.approx(-3.0, abs=0.2), f"B4 is {at_fs:.3f} dB at fs, expected -3.0"
    assert at_2fs == pytest.approx(0.0, abs=0.2), f"B4 passband is {at_2fs:.3f} dB at 2 fs"


# --------------------------------------------------------------------------- feasibility

def test_feasible_boxes_records_derived_port_data_and_fits() -> None:
    d = _synthetic_driver()
    points = br.feasible_boxes(d, VentedBoxRanges())
    assert points
    for point in points:
        assert point.kind == "vented"
        assert point.net_volume_l > 0.0
        assert point.derived_effective_port_length_m is not None
        assert point.derived_effective_port_length_m > 0.0
        assert point.derived_tuning_hz == pytest.approx(point.requested_tuning_hz, rel=1e-9)
        assert br.port_neck_length_mm(point) > 0.0
        for key in ("excursion_margin_db", "port_velocity_mps_40hz", "port_velocity_mps_63hz",
                    "neck_fits", "driver_rear_depth_fits"):
            assert key in point.fits
        assert point.fits["neck_fits"] is True
        assert point.fits["driver_rear_depth_fits"] is True


def test_zero_volume_range_is_infeasible_before_any_score() -> None:
    """SYS-10: Vb = 0 is impossible via the ranges, so no candidate reaches a score."""
    d = _synthetic_driver()
    assert br.feasible_boxes(d, VentedBoxRanges(net_volume_l_range=(0.0, 0.0))) == []
    mixed = br.feasible_boxes(d, VentedBoxRanges(net_volume_l_range=(0.0, 60.0)))
    assert all(point.net_volume_l > 0.0 for point in mixed)


def test_sealed_ranges_are_refused() -> None:
    d = _synthetic_driver()
    with pytest.raises(ValueError):
        br.feasible_boxes(d, VentedBoxRanges(kind="sealed"))


def test_slot_port_is_refused_at_the_lf_tier() -> None:
    d = _synthetic_driver()
    with pytest.raises(ValueError):
        br.feasible_boxes(d, VentedBoxRanges(port_type="slot"))


# --------------------------------------------------------------------------- report row

def test_lf_report_row_shape() -> None:
    d = _synthetic_driver()
    point = br.feasible_boxes(d, VentedBoxRanges())[0]
    row = br.lf_report_row(point, d)
    assert row["axis"] == "lf_headroom"
    assert row["nfr_ignored_at_lf_tier"] is True
    assert row["limiting_40hz"] in ("xmax", "p_aes", "port")
    assert row["limiting_63_120hz"] in ("xmax", "p_aes", "port")
    assert math.isfinite(row["f3_hz"])
    assert math.isfinite(row["margin_40hz_db"])
    assert math.isfinite(row["margin_63_120hz_db"])
    assert row["spl_reference"].startswith("1 m half space")
