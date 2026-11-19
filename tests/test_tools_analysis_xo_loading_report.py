"""xo_loading_report (Gate A 2026-11-19): conventions checked against a pulsating sphere."""
import math

import numpy as np
import pytest

from hornlab_search.constants import C_AIR, RHO_AIR
from hornlab_search.types import Response
from tools.analysis import xo_loading_report as X

A_RAD, R_M = 0.02, 10.0


def sphere_response(freqs=None) -> Response:
    """Pulsating sphere of radius A_RAD driven at unit normal ACCELERATION, stored like the BEM:
    z in exp(-i w t) (mass-like Im < 0), pressure at R_M, full balloon, area as tag "2"."""
    f = np.geomspace(300.0, 3000.0, 12) if freqs is None else np.asarray(freqs, float)
    om = 2 * np.pi * f
    ka = om / C_AIR * A_RAD
    z_eng = (ka ** 2 + 1j * ka) / (1 + ka ** 2)
    u = 1.0 / om                                           # unit acceleration -> velocity
    p_mag = RHO_AIR * C_AIR * (om / C_AIR) * A_RAD ** 2 * u / (R_M * np.sqrt(1 + ka ** 2))
    ang = np.arange(-90.0, 90.1, 5.0)
    th, ph = np.meshgrid(np.linspace(2.5, 177.5, 36), np.arange(0.0, 360.0, 10.0), indexing="ij")
    dirs = np.c_[(np.sin(np.radians(th)) * np.cos(np.radians(ph))).ravel(),
                 (np.sin(np.radians(th)) * np.sin(np.radians(ph))).ravel(), np.cos(np.radians(th)).ravel()]
    p_cut = np.repeat(p_mag[:, None], ang.size, axis=1).astype(complex)
    spl = 20 * np.log10(np.abs(p_cut) / 20e-6)
    return Response(freqs_hz=f, h_angles_deg=ang, v_angles_deg=ang, spl_h_db=spl, spl_v_db=spl,
                    balloon_dirs=dirs, spl_balloon_db=None, z_throat=np.conj(z_eng), p_h=p_cut, p_v=p_cut,
                    p_balloon=np.repeat(p_mag[:, None], dirs.shape[0], axis=1).astype(complex),
                    meta={"distance_m": R_M, "physical_tag_areas_m2": {"2": 4 * math.pi * A_RAD ** 2}})


def test_energy_balance_closes_on_a_pulsating_sphere():
    r = sphere_response()
    ratio = X.balloon_power_per_accel(r) / X.input_power_per_accel(r)
    assert np.allclose(ratio, 1.0, rtol=1e-9)


def test_velocity_conversion_and_relative_levels():
    f = np.array([500.0, 1000.0, 2000.0])
    assert np.allclose(X.velocity_db([0.0, 0.0, 0.0], f) - 20 * np.log10(2 * np.pi * f), 0.0)
    # a flat per-velocity level reads as a 6 dB/oct FALL per acceleration: the audit's trap
    acc = -20 * np.log10(2 * np.pi * f)
    assert X.rel_db(f, acc, 1000.0, 2000.0) == pytest.approx(20 * math.log10(2), abs=1e-9)
    assert X.rel_db(f, X.velocity_db(acc, f), 1000.0, 2000.0) == pytest.approx(0.0, abs=1e-9)
    assert math.isnan(X.rel_db(f, acc, 100.0, 2000.0))


def test_detrended_residual_and_reflection():
    f = np.geomspace(500, 4000, 10)
    mx, sd = X.detrended_residual(f, 3.0 * np.log2(f) + 1.0, 600, 3000)
    assert abs(mx) < 1e-9 and sd < 1e-9
    assert X.reflection_mag([1.0 + 0j])[0] == pytest.approx(0.0)
    assert X.reflection_mag([1 - 0.5j])[0] == pytest.approx(X.reflection_mag([1 + 0.5j])[0])


def test_load_pieces_match_the_v7_definition():
    f = np.array([400.0, 500.0, 643.0, 828.0, 1065.0, 2000.0])
    rez = np.array([0.1, 0.3, 1.4, 1.9, 1.3, 1.0])
    lp = X.load_pieces(f, rez, 700.0, 5600.0)
    t = (0.2 - 0.1) / (0.3 - 0.1)                    # first crossing: linear in z over log2 f
    lfp20 = 2 ** (math.log2(400) + t * (math.log2(500) - math.log2(400)))
    assert lp["lfp20_hz"] == pytest.approx(lfp20)
    assert lp["rez_min"] == pytest.approx(1.0) and lp["rez_pen"] == 0.0
    assert lp["load_raw"] == pytest.approx(max(0.0, math.log2(lfp20 * 1.6 / 700.0)))


def test_diagnose_runs_with_bracket_and_hp():
    r = sphere_response()
    d = X.diagnose(r, drivers=X.bracket_drivers()[:2], probe_hz=(643.0, 828.0))
    s = d["summary"]
    assert len(s["driver_rows"]) == 2 and all(math.isfinite(v) for v in s["driver_min_median_max"]["on_828_rel_ref_db"])
    assert s["energy_ratio_min_max"][0] == pytest.approx(1.0, rel=1e-9)
    assert X.butterworth_hp([700.0], 700.0, 2)[0] == pytest.approx(1 / math.sqrt(2))
    assert len(X.bracket_drivers()) == 32


def test_cli_refuses_non_empty_out(tmp_path):
    (tmp_path / "x").write_text("x")
    with pytest.raises(SystemExit):
        X.main(["--out", str(tmp_path), "a=nowhere"])
