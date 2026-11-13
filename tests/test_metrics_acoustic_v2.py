import numpy as np
import pytest

from hornlab_search.metrics.acoustic_v2 import main_lobe
from hornlab_search.metrics.polar import beamwidth_deg

A = np.linspace(-90, 90, 181)


def test_cardioid_matches_legacy_when_single_lobe():
    p = (1 + np.cos(np.radians(A))) / 2
    spl = 20 * np.log10(np.maximum(p, 1e-12))
    r = main_lobe(A, spl)
    # cardioid half-pressure is at exactly 90 deg, which is the range edge
    assert r["width_deg"] == pytest.approx(180.0, abs=1e-6)


def test_dipole_width_60_each_side():
    spl = 20 * np.log10(np.maximum(np.abs(np.cos(np.radians(A))), 1e-12))
    r = main_lobe(A, spl)
    assert r["status"] == "valid"
    assert r["width_deg"] == pytest.approx(120.0, abs=0.05)


def test_detached_side_lobe_does_not_widen_main_but_widens_legacy():
    base = -12.0 * (A / 30.0) ** 2
    lobe = 3.0 * np.exp(-((np.abs(A) - 70) / 4) ** 2)  # +3 dB above axis near +/-70
    spl = np.maximum(base, -40) + np.where(np.abs(A) > 50, 40 + lobe - 40, 0)
    spl = np.where(np.abs(A) > 60, np.maximum(spl, lobe), spl)
    r = main_lobe(A, spl)
    legacy, _ = beamwidth_deg(A, spl)
    assert r["width_deg"] < 60
    assert legacy > r["width_deg"]
    assert r["outside_peak_db"] == pytest.approx(3.0, abs=0.1)
    assert r["max_offaxis_db"] > 0


def test_no_crossing_is_censored_not_180():
    spl = np.zeros_like(A) - 1.0 * (A / 90) ** 2
    r = main_lobe(A, spl)
    assert r["status"] == "censored"
    assert r["left_status"] == r["right_status"] == "censored"


def test_requires_zero_sample():
    with pytest.raises(ValueError):
        main_lobe(np.linspace(-90, 90, 180), np.zeros(180))
