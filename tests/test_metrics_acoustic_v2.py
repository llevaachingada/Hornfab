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


# ---- full sphere / onsets (Rev2 P0/P1)
from hornlab_search.metrics.acoustic_v2 import (balloon_di, balloon_lobes, keele_estimate,  # noqa: E402
                                                loading_onset, pattern_control_onset)

NT, NP = 37, 72
TH = np.repeat(np.linspace(0, np.pi, NT), NP)


def _db(p):
    return 20 * np.log10(np.maximum(p, 1e-12))[None]


def test_balloon_di_analytic():
    assert balloon_di(np.zeros((1, NT * NP)), [NT, NP])["di_db"][0] == pytest.approx(0, abs=1e-9)
    assert balloon_di(_db((1 + np.cos(TH)) / 2), [NT, NP])["di_db"][0] == pytest.approx(4.771, abs=0.02)
    assert balloon_di(_db(np.abs(np.cos(TH))), [NT, NP])["di_db"][0] == pytest.approx(4.771, abs=0.02)


def test_balloon_di_invalid_not_zero():
    s = np.zeros((1, NT * NP))
    s[0, 5] = np.nan
    r = balloon_di(s, [NT, NP])
    assert r["status"][0] == "invalid" and np.isnan(r["di_db"][0])


def test_balloon_detached_hot_spot():
    b = np.where(TH < np.radians(30), 0.0, -20.0) + np.where(np.abs(TH - np.pi / 2) < 0.1, 23.0, 0.0)
    r = balloon_lobes(b[None], [NT, NP])
    assert r["outside_peak_db"][0] == pytest.approx(3.0)
    assert r["island_count"][0] == 1
    assert r["max_above_axis_db"][0] == pytest.approx(3.0)


def test_onsets_and_missing():
    assert loading_onset([1, 2], None)["status"] == "missing"
    r = loading_onset([100, 200, 400, 800], [0.1, 0.3, 0.8, 0.9])
    assert r["onset_hz"] == 400 and r["bracket_hz"] == [200, 400]
    p = pattern_control_onset([1, 2, 3, 4, 5], [120, 100, 82, 78, 80], 80, 5, dwell=3)
    assert p["onset_hz"] == 3 and p["status"] == "valid"
    assert pattern_control_onset([1, 2], [120, 130], 80, 5)["status"] == "not_reached"


def test_keele_is_labeled_heuristic():
    k = keele_estimate(700, 50)
    assert k["method"] == "heuristic" and k["binding"] is False
    assert k["keele_estimated_dimension_mm"] == pytest.approx(725.7, abs=0.1)
