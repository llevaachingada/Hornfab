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

# --- cone driver in a sealed rear bowl (2026-10-28, handoff section 4) -----------------------------

CONE = {"name": "synthetic cone", "kind": "cone", "re_ohm": 6.5, "sd_cm2": 350.0, "mmd_g": 18.0,
        "fs_hz": 55.0, "qms": 4.0, "bl_tm": 12.0}


def test_new_keys_do_not_change_the_compression_path():
    """The same compression driver with and without ``kind: compression`` gives identical numbers."""
    base = {**BASE, "le_mh": 0.08, "fs_hz": None, "cms_mm_per_n": 0.04,
            "rear_chamber_cm3": 40.0, "front_chamber_cm3": 2.0}
    f = np.geomspace(200, 8000, 31)
    resp = fake_response(f, 0.7 - 0.3j, 0.01)
    a = drive(CompressionDriver.from_dict(base), resp, volts_rms=2.83)
    b = drive(CompressionDriver.from_dict({**base, "kind": "compression"}), resp, volts_rms=2.83)
    assert set(a) == set(b)
    for key, value in a.items():
        if isinstance(value, np.ndarray):
            assert np.array_equal(value, b[key]), key
        else:
            assert value == b[key], key
    assert a["kind"] == "compression" and a["inductance_model"] == "plain" and not a["breakup_applied"]
    assert a["rear_box_m3"] is None


def test_rear_box_and_box_q_conserve_energy():
    """A sealed compliance AND a box-loss resistance in the rear branch keep the circuit lossless."""
    d = CompressionDriver.from_dict({**CONE, "rear_box_l": 6.1, "rear_box_q": 7.0})
    assert d.rear_box_m3 == pytest.approx(6.1e-3)
    f = np.geomspace(20, 500, 40)
    resp = fake_response(f, 0.9 - 0.2j, 0.01)
    out = drive(d, resp, volts_rms=2.83)
    i = 2.83 / out["z_in_ohm"]
    w = 2 * np.pi * f
    v = out["excursion_mm_peak"] * 1e-3 * w / math.sqrt(2.0)
    # rear_box_q is a series acoustic resistance at fs; its loss is the extra term in the balance
    cab = 6.1e-3 / (RHO_AIR * C_AIR ** 2)
    rr = 1.0 / (2 * math.pi * d.fs_hz * 7.0 * cab)
    ud = out["sd_eff_m2"] * v
    p_in = np.real(2.83 * np.conj(i))
    losses = np.abs(i) ** 2 * d.re_ohm + d.rms_kg_s * v ** 2 + rr * np.abs(ud) ** 2
    np.testing.assert_allclose(p_in - losses, out["acoustic_power_w"], rtol=1e-9, atol=1e-15)


def test_sealed_rear_box_raises_resonance_and_lowers_excursion_peak():
    f = np.geomspace(20, 600, 600)
    # a light acoustic load, so the mechanical system resonance is the visible excursion peak
    resp = fake_response(f, 1e-3 + 0j, 0.01)
    free = drive(CompressionDriver.from_dict({**CONE, "bl_tm": 3.0}), resp, volts_rms=1.0)
    boxed = drive(CompressionDriver.from_dict({**CONE, "bl_tm": 3.0, "rear_box_l": 6.1}), resp,
                  volts_rms=1.0)

    def peak(o):
        k = int(np.argmax(o["excursion_mm_peak"]))
        return f[k], o["excursion_mm_peak"][k]

    f_free, x_free = peak(free)
    f_box, x_box = peak(boxed)
    assert f_box > f_free            # the bowl's compliance stiffens the suspension
    assert x_box < x_free            # and the excursion peak is smaller


def test_lr2_semi_inductance_limits_and_plain_equivalence():
    low = {**BASE, "bl_tm": 1e-3}
    plain = CompressionDriver.from_dict({**low, "le_mh": 0.0})
    lr2 = CompressionDriver.from_dict({**low, "le_mh": 0.0, "l2_mh": 0.5, "r2_ohm": 3.0})
    resp_lo = fake_response([1e-4, 1e-3], 1.0, 0.01)
    np.testing.assert_allclose(drive(lr2, resp_lo)["z_in_ohm"], drive(plain, resp_lo)["z_in_ohm"],
                               rtol=1e-6, atol=1e-9)          # w -> 0: the LR-2 block vanishes
    resp_hi = fake_response([20000.0], 0.9 - 0.2j, 0.01)
    z_hi = drive(lr2, resp_hi)["z_in_ohm"][0]
    assert np.real(z_hi) == pytest.approx(6.0 + 3.0, abs=0.01)  # high f: the block -> R2
    assert drive(lr2, resp_hi)["inductance_model"] == "lr2"

    # a very large r2_ohm makes the LR-2 block a plain inductance of l2_mh
    big = CompressionDriver.from_dict({**BASE, "le_mh": 0.0, "l2_mh": 0.5, "r2_ohm": 1e15})
    flat = CompressionDriver.from_dict({**BASE, "le_mh": 0.5})
    resp = fake_response(np.geomspace(300, 8000, 25), 0.9 - 0.2j, 0.01)
    np.testing.assert_allclose(drive(big, resp)["z_in_ohm"], drive(flat, resp)["z_in_ohm"], rtol=1e-6)

    # energy: the LR-2 block is a real resistance R2*(wL2)^2/(R2^2+(wL2)^2) at every frequency
    d = CompressionDriver.from_dict({**BASE, "le_mh": 0.05, "l2_mh": 0.5, "r2_ohm": 3.0})
    f = np.geomspace(300, 6000, 25)
    out = drive(d, fake_response(f, 0.9 - 0.2j, 0.01), volts_rms=2.83)
    i = 2.83 / out["z_in_ohm"]
    w = 2 * np.pi * f
    v = out["excursion_mm_peak"] * 1e-3 * w / math.sqrt(2.0)
    wl2 = w * d.l2_h
    r_block = d.r2_ohm * wl2 ** 2 / (d.r2_ohm ** 2 + wl2 ** 2)
    p_in = np.real(2.83 * np.conj(i))
    losses = np.abs(i) ** 2 * (d.re_ohm + r_block) + d.rms_kg_s * v ** 2
    np.testing.assert_allclose(p_in - losses, out["acoustic_power_w"], rtol=1e-9, atol=1e-15)


def test_air_load_g_splits_a_published_mms_like_mmd():
    with_air = CompressionDriver.from_dict({"name": "a", "re_ohm": 6.0, "sd_cm2": 350.0, "mms_g": 20.0,
                                            "air_load_g": 2.0, "fs_hz": 55.0, "qms": 4.0, "bl_tm": 12.0})
    dry = CompressionDriver.from_dict({"name": "a", "re_ohm": 6.0, "sd_cm2": 350.0, "mmd_g": 18.0,
                                       "fs_hz": 55.0, "qms": 4.0, "bl_tm": 12.0})
    assert with_air.m_kg == dry.m_kg
    assert with_air.mass_may_include_air_load is False
    assert dry.mass_may_include_air_load is False
    resp = fake_response([55.0, 500.0], 0.9 - 0.2j, 0.01)
    for key, value in drive(with_air, resp).items():
        other = drive(dry, resp)[key]
        if isinstance(value, np.ndarray):
            assert np.array_equal(value, other), key
        else:
            assert value == other, key


def test_cone_refuses_a_front_chamber_bad_kinds_and_half_an_lr2():
    with pytest.raises(ValueError, match="front_chamber_cm3"):
        CompressionDriver.from_dict({**CONE, "front_chamber_cm3": 1.0})
    with pytest.raises(ValueError, match="kind"):
        CompressionDriver.from_dict({**BASE, "kind": "banana"})
    with pytest.raises(ValueError, match="r2_ohm"):
        CompressionDriver.from_dict({**BASE, "l2_mh": 0.5})
    with pytest.raises(ValueError, match="l2_mh"):
        CompressionDriver.from_dict({**BASE, "r2_ohm": 3.0})
    with pytest.raises(ValueError, match="air_load_g"):
        CompressionDriver.from_dict({**BASE, "air_load_g": 1.0})


def test_breakup_area_law_lowers_the_level_and_keeps_energy():
    f = np.array([10.0, 8000.0])
    resp = fake_response(f, 0.9 - 0.2j, 0.01)
    d0 = CompressionDriver.from_dict(CONE)
    db = CompressionDriver.from_dict({**CONE, "f_breakup_hz": 1200.0})
    o0, ob = drive(d0, resp, volts_rms=2.83), drive(db, resp, volts_rms=2.83)
    assert not o0["breakup_applied"] and ob["breakup_applied"]
    assert ob["spl_onaxis_db"][0] == pytest.approx(o0["spl_onaxis_db"][0], abs=0.01)  # f << f_b
    assert ob["spl_onaxis_db"][1] < o0["spl_onaxis_db"][1] - 6.0                     # well above f_b
    sd = d0.sd_m2
    np.testing.assert_allclose(ob["sd_eff_m2"], sd / (1.0 + (f / 1200.0) ** 2.0), rtol=1e-12)
    np.testing.assert_array_equal(o0["sd_eff_m2"], np.full(f.shape, sd))
    # the area law scales the load and Ud together, so the circuit stays lossless
    i = 2.83 / ob["z_in_ohm"]
    w = 2 * np.pi * f
    v = ob["excursion_mm_peak"] * 1e-3 * w / math.sqrt(2.0)
    p_in = np.real(2.83 * np.conj(i))
    losses = np.abs(i) ** 2 * db.re_ohm + db.rms_kg_s * v ** 2
    np.testing.assert_allclose(p_in - losses, ob["acoustic_power_w"], rtol=1e-9, atol=1e-15)
    # kind alone changes nothing: no f_breakup_hz -> the compression-path arithmetic
    d_comp = CompressionDriver.from_dict({k: v for k, v in CONE.items() if k != "kind"})
    for key, value in drive(d_comp, resp).items():
        if key == "kind":
            continue
        other = o0[key]
        if isinstance(value, np.ndarray):
            assert np.array_equal(value, other), key
        else:
            assert value == other, key
