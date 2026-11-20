"""Fixed-angle spectral ripple metric: synthetic conventions and archive reproduction."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from hornlab_search.metrics import spectral as S

REPO = Path(__file__).resolve().parents[1]
ARCHIVE = REPO / "docs/evidence/runs/scout40_2026-11-19"

# Same grid as the archived responses (18 frequencies, 73 cut angles).
FREQS = np.array([250.0, 315.0, 400.0, 500.0, 643.33, 827.75, 1065.04, 1370.35,
                  1763.18, 2268.63, 2573.0, 2918.96, 3311.0, 3755.72, 4260.0, 4832.36,
                  6217.63, 8000.0])
ANGLES = np.arange(-90.0, 90.1, 2.5)
ANGLES_SMALL = np.array([-10.0, 0.0, 10.0])
LOG2F = np.log2(FREQS)
BAND_MASK = (FREQS >= 1065.0) & (FREQS <= 4832.5)


def _quadratic(log2f):
    return 1.0 + 1.3 * log2f - 0.35 * log2f ** 2


def _ripple(log2f):
    # No quadratic component: a wobble the order-2 fit leaves behind.
    return 0.8 * np.sin(2.2 * (log2f - np.mean(log2f)))


def _build(profile, angles=ANGLES):
    """On-axis is 0 dB; each angle column is ``profile(angle)`` across frequency."""
    s = np.zeros((FREQS.size, angles.size))
    for j, a in enumerate(angles):
        s[:, j] = profile(float(a))
    return s


def test_quadratic_is_removed_exactly():
    s = _build(lambda a: (a / 25.0) * _quadratic(LOG2F))
    curve = S.fixed_angle_residual_curve(FREQS, s, ANGLES, 25.0)
    assert curve["rms_db"] == pytest.approx(0.0, abs=1e-9)
    assert curve["max_abs_db"] == pytest.approx(0.0, abs=1e-9)
    assert curve["n"] == int(BAND_MASK.sum()) == 10
    assert curve["n_params"] == 3
    assert curve["dof"] == 7
    assert curve["reference"] == "trend"


def test_band_masking_ignores_out_of_band_spikes():
    clean = _build(lambda a: (a / 25.0) * _ripple(LOG2F))
    spiked = clean.copy()
    outside = ~BAND_MASK
    spiked[outside, :] += 40.0
    a = S.fixed_angle_residual_db(FREQS, clean, ANGLES, 25.0)
    b = S.fixed_angle_residual_db(FREQS, spiked, ANGLES, 25.0)
    assert np.isfinite(a) and a > 0.0
    assert b == pytest.approx(a, abs=1e-12)


def test_detrend_orders_one_to_three():
    s = _build(lambda a: (a / 25.0) * _quadratic(LOG2F))
    r1 = S.fixed_angle_residual_curve(FREQS, s, ANGLES, 25.0, detrend_order=1)
    r2 = S.fixed_angle_residual_curve(FREQS, s, ANGLES, 25.0, detrend_order=2)
    r3 = S.fixed_angle_residual_curve(FREQS, s, ANGLES, 25.0, detrend_order=3)
    assert r1["n_params"] == 2 and r1["dof"] == 8
    assert r2["n_params"] == 3 and r3["n_params"] == 4
    assert r1["rms_db"] > 0.05              # a quadratic is not a straight line
    assert r2["rms_db"] == pytest.approx(0.0, abs=1e-9)
    assert r3["rms_db"] == pytest.approx(0.0, abs=1e-9)


def test_refusal_on_missing_angle_short_band_and_non_finite():
    s_small = _build(lambda a: (a / 10.0) * _ripple(LOG2F), angles=ANGLES_SMALL)
    missing = S.fixed_angle_residual_curve(FREQS, s_small, ANGLES_SMALL, 5.0)
    assert np.isnan(missing["rms_db"]) and missing["reason"]

    s = _build(lambda a: (a / 25.0) * _ripple(LOG2F))
    short = S.fixed_angle_residual_curve(FREQS, s, ANGLES, 25.0, band_hz=(1065.0, 1371.0))
    assert np.isnan(short["rms_db"]) and "degrees of freedom" in short["reason"]

    bad = s.copy()
    bad[int(np.flatnonzero(BAND_MASK)[0]), int(np.argmin(np.abs(ANGLES - 25.0)))] = np.nan
    nonfinite = S.fixed_angle_residual_curve(FREQS, bad, ANGLES, 25.0)
    assert np.isnan(nonfinite["rms_db"]) and "non-finite" in nonfinite["reason"]

    assert np.isnan(S.fixed_angle_residual_db(FREQS, bad, ANGLES, 25.0))


def test_symmetric_pairs_detect_one_sided_artefact():
    s = _build(lambda a: (abs(a) / 25.0) * _ripple(LOG2F))
    rows = S.symmetric_pair_report(FREQS, s, ANGLES)
    row25 = next(r for r in rows if r["angle_deg"] == 25.0)
    assert row25["counterpart_deg"] == -25.0
    assert row25["delta_db"] == pytest.approx(0.0, abs=1e-12)

    jp = int(np.argmin(np.abs(ANGLES - 25.0)))
    jm = int(np.argmin(np.abs(ANGLES + 25.0)))
    s[:, jm] = 2.0 * s[:, jp]
    rows = S.symmetric_pair_report(FREQS, s, ANGLES)
    row25 = next(r for r in rows if r["angle_deg"] == 25.0)
    assert abs(row25["delta_db"]) > 0.1
    assert row25["delta_db"] == pytest.approx(
        row25["rms_db"] - row25["counterpart_rms_db"], abs=1e-12)


def test_band_mean_is_zero_for_a_constant_offset():
    s = _build(lambda a: (a / 25.0) * np.full(FREQS.size, 6.0))
    curve = S.fixed_angle_residual_curve(FREQS, s, ANGLES, 25.0, reference="band_mean")
    assert curve["reference"] == "band_mean"
    assert curve["n_params"] == 1
    assert curve["rms_db"] == pytest.approx(0.0, abs=1e-12)
    assert curve["max_abs_db"] == pytest.approx(0.0, abs=1e-12)


def test_band_mean_differs_from_trend_on_a_quadratic():
    s = _build(lambda a: (a / 25.0) * _quadratic(LOG2F))
    trend = S.fixed_angle_residual_curve(FREQS, s, ANGLES, 25.0, reference="trend")
    band_mean = S.fixed_angle_residual_curve(FREQS, s, ANGLES, 25.0, reference="band_mean")
    assert trend["rms_db"] == pytest.approx(0.0, abs=1e-9)
    assert band_mean["rms_db"] > 0.1          # the quadratic variation remains


def test_sensitivity_scan_covers_both_references():
    s = _build(lambda a: (a / 25.0) * _ripple(LOG2F))
    rows = S.sensitivity_scan(FREQS, s, ANGLES, [25.0], detrend_orders=(1, 2, 3))
    refs = {(r["reference"], r["detrend_order"]) for r in rows}
    assert ("trend", 1) in refs and ("trend", 2) in refs and ("trend", 3) in refs
    assert ("band_mean", None) in refs


REPRO = [
    ("20261119T073330Z-screen-723756", "ee85bcd2ad67", {"V+25": 1.151, "V+35": 1.441}),
    ("20261119T090559Z-screen-9b8767", "9b5428e6dec8", {"V+25": 0.266, "V+35": 0.351}),
    ("20261119T081214Z-screen-8470bd", "cf716e738ef8", {"V+25": 0.497, "V+35": 0.822}),
    ("20261119T085256Z-screen-c2203f", "efe4a8959d85", {"V+25": 0.382, "V+35": 0.596}),
]


@pytest.mark.parametrize("run,design,expected", REPRO)
def test_archive_reproduction(run, design, expected):
    path = ARCHIVE / run / "designs" / design / "response.npz"
    assert path.is_file(), f"missing archive response: {path}"
    z = np.load(path, allow_pickle=True)
    f = np.asarray(z["freqs_hz"], float)
    a = np.asarray(z["v_angles_deg"], float)
    s = np.asarray(z["spl_v_db"], float)
    got25 = S.fixed_angle_residual_db(f, s, a, 25.0)
    got35 = S.fixed_angle_residual_db(f, s, a, 35.0)
    assert got25 == pytest.approx(expected["V+25"], abs=2e-3)
    assert got35 == pytest.approx(expected["V+35"], abs=2e-3)
