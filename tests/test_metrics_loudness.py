"""Report-only horn loudness readout (P12, 2026-10-27). Offline, CPU only.

Pinned: the throat area is the mesh tag area times the symmetry copies; loading_db = 10 log10(Re z);
the output gap is the worst case from 0.95 f0 of max(0, 10 log10(0.7 / Re z)); f_loaded_hz is where
Re z stays >= 0.5; the on-axis level per 1 m/s throat velocity follows |p| = |H| w and 1/r to 1 m;
``horn_loudness`` never raises. One stored-data check (skipped when the run is absent): the throat
power equals the power through the stored balloon sphere within 0.5 dB.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from hornlab_search.constants import C_AIR, REF_P, RHO_AIR
from hornlab_search.metrics.loudness import (horn_loudness, loaded_from_hz, output_gap_db,
                                             throat_area_m2)
from hornlab_search.types import Response

REPO = Path(__file__).resolve().parents[1]


def resp_with(z, p_axis=0.01, *, quadrants="1", tag_area=2.5e-4, distance_m=2.0, f=None):
    f = np.asarray(f if f is not None else [500.0, 1000.0, 2000.0, 4000.0])
    ang = np.linspace(-90.0, 90.0, 73)
    p = np.full((f.size, ang.size), 1e-9 + 0j)
    p[:, 36] = p_axis
    spl = 20 * np.log10(np.abs(p) / REF_P)
    meta = {"physical_tag_areas_m2": {"2": tag_area}, "quadrants": quadrants, "distance_m": distance_m}
    return Response(freqs_hz=f, h_angles_deg=ang, v_angles_deg=ang, spl_h_db=spl, spl_v_db=spl,
                    balloon_dirs=None, spl_balloon_db=None,
                    z_throat=None if z is None else np.asarray(z, dtype=complex), p_h=p, p_v=p, meta=meta)


def test_throat_area_uses_the_symmetry_copies():
    assert throat_area_m2(resp_with([1, 1, 1, 1], quadrants="1")) == pytest.approx(1e-3)
    assert throat_area_m2(resp_with([1, 1, 1, 1], quadrants="12")) == pytest.approx(5e-4)
    assert throat_area_m2(resp_with([1, 1, 1, 1], quadrants="1234")) == pytest.approx(2.5e-4)
    r = resp_with([1, 1, 1, 1])
    assert math.isnan(throat_area_m2(Response(**{**r.__dict__, "meta": {}})))


def test_loading_gap_and_loaded_frequency():
    z = np.array([0.07, 0.35, 0.8, 1.05]) - 0.3j
    out = horn_loudness(resp_with(z), f0_hz=600.0)
    np.testing.assert_allclose(out["loading_db"], 10 * np.log10([0.07, 0.35, 0.8, 1.05]))
    # f0 600 -> scored from 570 Hz: the 1 kHz point (0.35) is the worst
    assert out["output_gap_at_f0_db"] == pytest.approx(10 * math.log10(0.7 / 0.35))
    assert out["f_loaded_hz"] == 2000.0
    assert out["throat_diameter_equiv_mm"] == pytest.approx(2000 * math.sqrt(1e-3 / math.pi))
    assert output_gap_db([500, 1000], [0.9, 1.2], 500) == 0.0
    assert math.isnan(loaded_from_hz([500, 1000], [0.2, 0.3]))


def test_onaxis_level_per_unit_velocity():
    f = np.array([1000.0, 2000.0])
    out = horn_loudness(resp_with([1, 1], p_axis=0.02, f=f), ref_distance_m=1.0)
    expect = 20 * np.log10(0.02 * 2 * np.pi * f * 2.0 / REF_P)
    np.testing.assert_allclose(out["onaxis_db_per_mps"], expect)


def test_never_raises_on_missing_data():
    r = resp_with(None)
    out = horn_loudness(Response(**{**r.__dict__, "meta": {}}), f0_hz=500.0)
    assert math.isnan(out["output_gap_at_f0_db"]) and math.isnan(out["throat_area_m2"])
    assert horn_loudness(object())["freqs_hz"].size == 0


STORED = REPO / "runs" / "20261027T104422Z-screen-a060fb" / "designs" / "589360bea375" / "response.npz"


@pytest.mark.skipif(not STORED.exists(), reason="stored campaign run not present (local data)")
def test_stored_throat_power_matches_balloon_power():
    from hornlab_search.solve.base import theta_deg_from_dirs
    from hornlab_search.solve.cache import load_response
    r = load_response(STORED)
    area = throat_area_m2(r)
    w = 2 * np.pi * r.freqs_hz
    th = theta_deg_from_dirs(np.asarray(r.balloon_dirs))
    wt = np.sin(np.radians(th))
    wt = wt / wt.sum() * 4 * np.pi
    w_throat = 0.5 * RHO_AIR * C_AIR * np.real(r.z_throat) * area / w ** 2
    w_ball = 0.5 * (np.abs(r.p_balloon) ** 2 / (RHO_AIR * C_AIR) * wt).sum(axis=1) * r.meta["distance_m"] ** 2
    assert np.max(np.abs(10 * np.log10(w_ball / w_throat))) < 0.5
    assert json.loads(json.dumps(r.meta["quadrants"])) == "1"
