"""Lumped compression-driver model over the BEM throat impedance (P12, 2026-10-27).

Offline, CPU only, synthetic responses. The contracts pinned here:

* energy is conserved: electrical input = voice-coil heat + suspension loss + acoustic power, with a
  coil inductance, a front (compression) chamber and a rear chamber in the circuit;
* the textbook matched-load result: at fs, with no suspension loss, a radiation resistance equal to the
  electrical damping Bl^2/Re gives exactly 50 % efficiency;
* the level chain: a monopole-like stored on-axis pressure gives the closed-form SPL, and 1/r scaling
  from the stored 2 m to 1 m is +6.02 dB;
* the time convention: the BEM stores z in exp(-i w t) (mass-like loading has Im z < 0); a mass-like
  load must LOWER the electrical impedance peak below fs, never raise it;
* datasheet derivations (fs/Qms/Qes/Qts -> Cms/Rms/Bl), the Mms flag, and validation errors.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from hornlab_search.constants import C_AIR, REF_P, RHO_AIR
from hornlab_search.driver import CompressionDriver, band_mean_db, drive, max_spl_db
from hornlab_search.types import Response


def fake_response(freqs, z_bem, p_axis_per_accel, *, area_full=1.0e-3, distance_m=2.0) -> Response:
    f = np.asarray(freqs, dtype=float)
    ang = np.linspace(-90.0, 90.0, 73)
    p = np.full((f.size, ang.size), 1e-9 + 0j)
    p[:, 36] = p_axis_per_accel
    spl = 20.0 * np.log10(np.abs(p) / REF_P)
    meta = {"physical_tag_areas_m2": {"1": 0.1, "2": area_full / 4.0}, "quadrants": "1",
            "distance_m": distance_m}
    return Response(freqs_hz=f, h_angles_deg=ang, v_angles_deg=ang, spl_h_db=spl, spl_v_db=spl,
                    balloon_dirs=None, spl_balloon_db=None,
                    z_throat=np.broadcast_to(np.asarray(z_bem, dtype=complex), f.shape).copy(),
                    p_h=p, p_v=p, meta=meta)


BASE = {"name": "synthetic", "re_ohm": 6.0, "sd_cm2": 44.0, "mmd_g": 2.5, "fs_hz": 500.0, "qms": 4.0,
        "bl_tm": 16.0}


def test_energy_is_conserved_with_inductance_and_chambers():
    d = CompressionDriver.from_dict({**BASE, "fs_hz": None, "cms_mm_per_n": 0.04, "le_mh": 0.08,
                                     "front_chamber_cm3": 2.0, "rear_chamber_cm3": 40.0})
    assert d.rear_chamber_m3 == pytest.approx(40e-6)
    f = np.geomspace(300, 8000, 25)
    z = 0.6 - 0.4j                       # BEM convention, mass-like
    resp = fake_response(f, z, 0.01)
    out = drive(d, resp, volts_rms=2.83)
    i = 2.83 / out["z_in_ohm"]
    p_in = np.real(2.83 * np.conj(i))
    w = 2 * np.pi * f
    v = out["excursion_mm_peak"] * 1e-3 * w / math.sqrt(2.0)
    losses = np.abs(i) ** 2 * d.re_ohm + d.rms_kg_s * v ** 2
    np.testing.assert_allclose(p_in - losses, out["acoustic_power_w"], rtol=1e-9, atol=1e-15)
    assert np.all(out["efficiency_pct"] > 0) and np.all(out["efficiency_pct"] < 100)


def test_matched_resistive_load_at_fs_gives_half_efficiency():
    d = CompressionDriver.from_dict({**BASE, "qms": None, "rms_kg_s": 1e-12})
    r_e = d.bl_tm ** 2 / d.re_ohm                     # electrical damping, mechanical ohms
    area = d.sd_m2 ** 2 * RHO_AIR * C_AIR / r_e      # Sd^2 rho c / A == Bl^2 / Re
    resp = fake_response([d.fs_hz], 1.0, 0.01, area_full=area)
    out = drive(d, resp, volts_rms=2.83)
    assert out["efficiency_pct"][0] == pytest.approx(50.0, rel=1e-6)
    assert out["compression_ratio"] == pytest.approx(d.sd_m2 / area)


def test_monopole_level_and_one_over_r():
    d = CompressionDriver.from_dict(BASE)
    f = np.array([1000.0, 2000.0])
    area = 1.0e-3
    r = 2.0
    resp = fake_response(f, 1.0, RHO_AIR * area / (4 * np.pi * r), area_full=area, distance_m=r)
    out = drive(d, resp, volts_rms=2.83, ref_distance_m=1.0)
    w = 2 * np.pi * f
    expect = 20 * np.log10(RHO_AIR * area * w * out["throat_velocity_mps"] / (4 * np.pi * 1.0) / REF_P)
    np.testing.assert_allclose(out["spl_onaxis_db"], expect, atol=1e-9)
    at2 = drive(d, resp, volts_rms=2.83, ref_distance_m=2.0)["spl_onaxis_db"]
    np.testing.assert_allclose(out["spl_onaxis_db"] - at2, 20 * np.log10(2.0), atol=1e-9)


def _peak_hz(d, z_bem):
    f = np.geomspace(150, 2000, 600)
    out = drive(d, fake_response(f, z_bem, 0.01), volts_rms=1.0)
    return f[int(np.argmax(np.abs(out["z_in_ohm"])))]


def test_bem_mass_like_load_lowers_the_impedance_peak():
    d = CompressionDriver.from_dict({**BASE, "qms": 10.0})
    f_free = _peak_hz(d, 1e-9 + 0j)
    f_mass = _peak_hz(d, 1e-6 - 0.8j)     # Im < 0 is mass-like in the BEM's exp(-i w t) convention
    f_stiff = _peak_hz(d, 1e-6 + 0.8j)
    assert f_free == pytest.approx(d.fs_hz, rel=0.02)
    assert f_mass < f_free < f_stiff


def test_datasheet_derivations():
    d = CompressionDriver.from_dict({"name": "x", "re_ohm": 5.0, "sd_cm2": 40.0, "mmd_g": 2.0,
                                     "fs_hz": 600.0, "qms": 5.0, "qes": 0.5})
    w0 = 2 * math.pi * 600.0
    assert d.cms_m_per_n == pytest.approx(1 / (w0 ** 2 * 2e-3))
    assert d.rms_kg_s == pytest.approx(w0 * 2e-3 / 5.0)
    assert d.bl_tm == pytest.approx(math.sqrt(w0 * 2e-3 * 5.0 / 0.5))
    assert d.fs_hz == pytest.approx(600.0)
    q = CompressionDriver.from_dict({"name": "x", "re_ohm": 5.0, "sd_cm2": 40.0, "mms_g": 2.0,
                                     "fs_hz": 600.0, "qts": 0.4, "qes": 0.5, "bl_tm": 10.0})
    assert q.rms_kg_s == pytest.approx(w0 * 2e-3 / (1 / (1 / 0.4 - 1 / 0.5)))
    assert q.mass_may_include_air_load and not d.mass_may_include_air_load
    # fs already includes the driver's own rear chamber, so a rear volume alone is not added twice
    assert CompressionDriver.from_dict({**BASE, "rear_chamber_cm3": 30.0}).rear_chamber_m3 is None
    assert CompressionDriver.from_dict({**BASE, "nominal_impedance_ohm": 8}).volts_for_watts(1.0) == \
        pytest.approx(math.sqrt(8))


@pytest.mark.parametrize("bad, msg", [
    ({"sd_cm2": None}, "missing"),
    ({"mmd_g": None}, "mmd_g"),
    ({"re_ohm": -1}, "re_ohm"),
    ({"bl_tm": None}, "bl_tm or qes"),
    ({"qms": None}, "qms"),
    ({"colour": "red"}, "unknown"),
    ({"fs_hz": None}, "fs_hz"),
])
def test_validation_errors(bad, msg):
    with pytest.raises(ValueError, match=msg):
        CompressionDriver.from_dict({k: v for k, v in {**BASE, **bad}.items() if v is not None})


def test_max_spl_power_and_excursion_limits():
    f = np.geomspace(300, 6000, 20)
    resp = fake_response(f, 0.8 - 0.2j, 0.01)
    d = CompressionDriver.from_dict({**BASE, "nominal_impedance_ohm": 8, "power_aes_w": 100})
    out = max_spl_db(d, resp)
    np.testing.assert_allclose(out["max_spl_db"] - out["spl_1w_db"], 20.0, atol=1e-9)
    assert set(out["limit"]) == {"power"}
    tight = CompressionDriver.from_dict({**BASE, "nominal_impedance_ohm": 8, "power_aes_w": 100,
                                         "xmax_mm": 0.05})
    o2 = max_spl_db(tight, resp)
    assert o2["limit"][0] == "excursion" and o2["limit"][-1] == "power"
    assert np.all(o2["max_spl_db"] <= out["max_spl_db"] + 1e-9)


def test_band_mean_is_a_power_average():
    assert band_mean_db([1, 2, 3], [100.0, 100.0, 90.0], 1, 2) == pytest.approx(100.0)
    assert band_mean_db([1, 2], [100.0, 90.0], 1, 2) == pytest.approx(10 * math.log10((1 + 0.1) / 2) + 100)
    assert math.isnan(band_mean_db([1, 2], [100.0, 90.0], 5, 6))


def test_refuses_a_response_without_impedance_or_area():
    d = CompressionDriver.from_dict(BASE)
    r = fake_response([1000.0], 1.0, 0.01)
    with pytest.raises(ValueError, match="z_throat"):
        drive(d, Response(**{**r.__dict__, "z_throat": None}))
    with pytest.raises(ValueError, match="area"):
        drive(d, Response(**{**r.__dict__, "meta": {"distance_m": 2.0}}))
