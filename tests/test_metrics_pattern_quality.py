"""WP2 pattern-quality diagnostics - offline synthetic fixtures (no solver, no GPU).

Every fixture is a pure numpy array.  The tests pin the differences that matter:

* the legacy OUTERMOST width grows when a detached side lobe is present, while the
  boresight-CONNECTED width does not;
* a censored/unmeasurable case never silently becomes 180 or 0 degrees;
* the H12 off-axis-excess threshold is reused, not redefined;
* spherical DI uses the canonical sin(theta) quadrature (and differs from naive equal weights);
* the balloon cone-of-validity (theta=0 present, grid not too sparse) is enforced.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from hornlab_search.metrics.pattern_quality import (
    OA_ISLAND_ANOMALOUS_DB,
    OA_ISLAND_WARN_DB,
    BalloonTooSparseError,
    BalloonUnavailableError,
    PatternQualityInputError,
    balloon_directivity,
    balloon_lobe_map,
    connected_main_lobe,
    cut_pattern_quality,
    h12_offaxis_excess_threshold_db,
    legacy_outermost_width,
    off_axis_excess,
    pattern_quality_from_response,
)


# --------------------------------------------------------------------------- helpers


def _angles(step: float = 1.0) -> np.ndarray:
    """Odd, strictly ascending -90..+90 grid with an exact 0."""
    n = int(round(90.0 / step))
    return np.arange(-n, n + 1, dtype=float) * step


def _gaussian(angles: np.ndarray, half_deg: float = 25.0) -> np.ndarray:
    return -6.0206 * (angles / half_deg) ** 2


def _balloon(theta_deg, phi_deg):
    """(nT*nP, 3) unit directions plus the matching structured grid shape."""
    t, p = np.meshgrid(np.asarray(theta_deg, float), np.asarray(phi_deg, float), indexing="ij")
    x = np.sin(np.radians(t)) * np.cos(np.radians(p))
    y = np.sin(np.radians(t)) * np.sin(np.radians(p))
    z = np.cos(np.radians(t))
    dirs = np.column_stack([x.ravel(), y.ravel(), z.ravel()])
    return dirs, (len(theta_deg), len(phi_deg))


def _structured_balloon(n_theta: int = 19, n_phi: int = 36):
    theta = np.linspace(0.0, 180.0, n_theta)
    phi = np.linspace(0.0, 360.0, n_phi, endpoint=False)
    dirs, grid = _balloon(theta, phi)
    theta_per_sample = np.repeat(theta, n_phi)
    return dirs, grid, theta_per_sample


# --------------------------------------------------------------------------- cut fixtures


def test_single_gaussian_lobe():
    a = _angles()
    s = _gaussian(a, 25.0)
    report = cut_pattern_quality(a, s)

    legacy = report["legacy"]
    connected = report["connected"]
    assert legacy["status"] == "valid"
    assert connected["status"] == "valid"
    assert legacy["width_deg"] == pytest.approx(50.0, abs=1e-6)
    assert connected["width_deg"] == pytest.approx(50.0, abs=1e-6)
    assert connected["island_count"] == 0
    assert report["pattern_quality_flags"] == []


def test_centered_plateau():
    a = _angles()
    # -0.2 dB plateau to +/-40 deg, then a 2 dB/deg skirt.
    s = np.where(np.abs(a) <= 40.0, -0.2, -0.2 - 2.0 * (np.abs(a) - 40.0))
    report = cut_pattern_quality(a, s)

    # The threshold is referenced to the (normalised) on-axis level, so the skirt needs a
    # 6.0206 dB drop: crossing at |a| = 40 + 6.0206/2 = 43.0103 deg, width 86.0206 deg.
    expected = 2.0 * (40.0 + 6.0206 / 2.0)
    assert report["legacy"]["width_deg"] == pytest.approx(expected, abs=0.05)
    assert report["connected"]["width_deg"] == pytest.approx(expected, abs=0.05)
    assert report["connected"]["lower_edge_deg"] == pytest.approx(-expected / 2.0, abs=0.05)
    assert report["connected"]["upper_edge_deg"] == pytest.approx(expected / 2.0, abs=0.05)
    assert report["connected"]["island_count"] == 0


def test_disconnected_outer_lobe_grows_legacy_not_connected():
    a = _angles()
    s = _gaussian(a, 15.0)
    island = (np.abs(a) >= 50.0) & (np.abs(a) <= 60.0)
    s[island] = -1.0                      # two detached above-threshold islands

    legacy = legacy_outermost_width(a, s)
    connected = connected_main_lobe(a, s)

    assert legacy["status"] == "valid"
    assert legacy["width_deg"] > 110.0          # outermost crossings jump to the islands
    assert connected["status"] == "valid"
    assert connected["width_deg"] == pytest.approx(30.0, abs=0.05)
    assert connected["island_count"] == 2
    assert connected["island_total_extent_deg"] > 15.0
    assert legacy["width_deg"] - connected["width_deg"] > 80.0

    report = cut_pattern_quality(a, s)
    assert "disconnected_above_threshold_islands" in report["pattern_quality_flags"]
    assert "legacy_width_inflated_by_islands" in report["pattern_quality_flags"]
    assert connected["n_reentries"] == 2
    assert connected["n_threshold_transitions"] == 6


def test_h12_threshold_is_the_existing_definition():
    # The diagnostic must reuse H12's value, not carry a second copy.
    from hornlab_search.objective.scalar_v7 import _OA_EXCESS_THRESHOLD_DB

    assert h12_offaxis_excess_threshold_db() == float(_OA_EXCESS_THRESHOLD_DB)


def test_offaxis_peak_above_on_axis_flags():
    a = _angles()
    s = -3.0 + 5.0 * np.exp(-0.5 * ((a - 50.0) / 5.0) ** 2)   # +2 dB at 50 deg, -3 on axis
    off = off_axis_excess(a, s)

    assert off["status"] == "valid"
    assert off["threshold_db"] == pytest.approx(h12_offaxis_excess_threshold_db())
    assert off["max_offaxis_db"] == pytest.approx(5.0, abs=1e-6)
    assert off["max_offaxis_angle_deg"] == pytest.approx(50.0)
    assert off["max_excess_db"] == pytest.approx(5.0 - off["threshold_db"], abs=1e-6)
    assert off["mean_excess_db"] > 0.0

    flags = cut_pattern_quality(a, s)["pattern_quality_flags"]
    assert "off_axis_peak_gt_0p5_db" in flags
    assert "off_axis_peak_gt_1p0_db" in flags
    assert 0.5 == OA_ISLAND_WARN_DB and 1.0 == OA_ISLAND_ANOMALOUS_DB


def test_no_crossing_is_censored_never_180_or_zero():
    a = _angles()
    s = np.full_like(a, -3.0)             # everywhere inside the -6 dB threshold

    legacy = legacy_outermost_width(a, s)
    connected = connected_main_lobe(a, s)

    assert legacy["status"] == "censored"
    assert legacy["width_deg"] is None
    assert legacy["n_crossings"] == 0
    assert legacy["legacy_sentinel_deg"] == 180.0
    assert connected["status"] == "censored"
    assert connected["width_deg"] is None
    assert connected["lower_edge_deg"] is None
    assert connected["upper_edge_deg"] is None
    assert connected["lower_edge_status"] == "censored"
    assert connected["upper_edge_status"] == "censored"
    assert connected["island_count"] == 0

    # A dead (all non-finite) cut is unmeasurable, not a width.
    dead = legacy_outermost_width(a, np.full_like(a, np.nan))
    dead_conn = connected_main_lobe(a, np.full_like(a, np.nan))
    assert dead["status"] == "unmeasurable" and dead["width_deg"] is None
    assert dead_conn["status"] == "unmeasurable" and dead_conn["width_deg"] is None


def test_one_sided_crossing():
    a = _angles()
    s = np.where(a >= 0.0, _gaussian(a, 20.0), -1.0)   # above threshold on the -90 side

    legacy = legacy_outermost_width(a, s)
    connected = connected_main_lobe(a, s)

    assert legacy["status"] == "valid_one_sided"
    assert legacy["n_crossings"] == 1
    assert legacy["width_deg"] == pytest.approx(110.0, abs=0.05)   # +20 to -90 grid edge
    assert connected["status"] == "censored"
    assert connected["width_deg"] is None
    assert connected["upper_edge_deg"] == pytest.approx(20.0, abs=0.05)
    assert connected["lower_edge_deg"] is None
    assert connected["lower_edge_status"] == "censored"
    assert connected["lower_bound_deg"] == pytest.approx(-90.0)


def test_corrupted_angles_raise_typed_error():
    good = _angles()
    s = _gaussian(good, 20.0)

    with pytest.raises(PatternQualityInputError):
        cut_pattern_quality(np.array([-90.0, np.nan, 0.0, 90.0]), np.zeros(4))
    with pytest.raises(PatternQualityInputError):
        cut_pattern_quality(np.array([-90.0, -10.0, 10.0, 90.0]), np.zeros(4))   # no 0 deg
    with pytest.raises(PatternQualityInputError):
        cut_pattern_quality(np.array([-90.0, 0.0, 0.0, 90.0]), np.zeros(4))       # duplicate 0
    with pytest.raises(PatternQualityInputError):
        cut_pattern_quality(good[::-1], s[::-1])                                 # not ascending


def test_nonfinite_offaxis_samples_are_floored_not_crashed():
    a = _angles()
    s = _gaussian(a, 25.0)
    s[5] = np.nan
    s[-7] = np.nan

    report = cut_pattern_quality(a, s)
    assert report["legacy"]["status"] == "valid"
    assert report["legacy"]["width_deg"] == pytest.approx(50.0, abs=1e-6)
    assert report["connected"]["status"] == "valid"
    assert report["connected"]["width_deg"] == pytest.approx(50.0, abs=1e-6)
    assert report["off_axis"]["status"] == "valid"
    assert np.isfinite(report["off_axis"]["max_offaxis_db"])


# --------------------------------------------------------------------------- balloon fixtures


def test_uniform_omni_has_zero_di():
    dirs, grid, _theta = _structured_balloon()
    omni = np.zeros(dirs.shape[0])
    out = balloon_directivity(omni, dirs, grid=grid)

    assert out["status"] == "valid"
    assert out["weighting"] == "sin_theta"
    assert abs(out["di_db"]) < 1e-9


def test_equal_area_vs_sin_theta_weighting_differs():
    dirs, grid, theta_per_sample = _structured_balloon()
    beam = -6.0206 * (theta_per_sample / 20.0) ** 2

    on_grid = balloon_directivity(beam, dirs, grid=grid)
    equal = balloon_directivity(beam, dirs, grid=None)   # naive equal weights

    assert on_grid["weighting"] == "sin_theta"
    assert equal["weighting"] == "equal_area"
    # On a theta-phi grid the equal-weight average over-counts the polar (loud) region, so it
    # reads a LOWER DI than the canonical sin(theta) quadrature.
    assert on_grid["di_db"] > equal["di_db"] + 1.0


def test_balloon_requires_a_theta_zero_sample():
    theta = np.linspace(5.0, 175.0, 18)                 # no boresight sample
    phi = np.linspace(0.0, 360.0, 36, endpoint=False)
    dirs, grid = _balloon(theta, phi)
    with pytest.raises(BalloonUnavailableError):
        balloon_directivity(np.zeros(dirs.shape[0]), dirs, grid=grid)


def test_balloon_too_sparse_is_refused():
    theta = np.linspace(0.0, 180.0, 3)
    phi = np.linspace(0.0, 360.0, 3, endpoint=False)
    dirs, grid = _balloon(theta, phi)
    with pytest.raises(BalloonTooSparseError):
        balloon_directivity(np.zeros(dirs.shape[0]), dirs, grid=grid)
    with pytest.raises(BalloonTooSparseError):
        balloon_lobe_map(np.zeros((1, dirs.shape[0])), dirs, grid)


def test_balloon_lobe_map_warns_about_sampling_density():
    dirs, grid, theta_per_sample = _structured_balloon()
    beam = -6.0206 * (theta_per_sample / 20.0) ** 2
    out = balloon_lobe_map(beam[None, :], dirs, grid)

    assert out["status"] == "valid"
    assert out["grid"] == [19, 36]
    assert out["resolution_deg"][0] == pytest.approx(10.0)      # 180 / (19-1)
    assert out["resolution_deg"][1] == pytest.approx(10.0)      # 360 / 36
    assert "not resolved" in out["sampling_density_warning"]


# --------------------------------------------------------------------------- symmetry / interpolation


def test_quarter_domain_hv_symmetry_and_reflection():
    a = _angles()
    s = _gaussian(a, 25.0)

    h = cut_pattern_quality(a, s)
    v = cut_pattern_quality(a, s.copy())
    assert h["connected"]["width_deg"] == pytest.approx(v["connected"]["width_deg"])
    assert h["connected"]["lower_edge_deg"] == pytest.approx(-h["connected"]["upper_edge_deg"])

    # A tilted cut and its mirror image swap the signed edges exactly.
    tilted = s + 0.5 * a
    mirrored = cut_pattern_quality(a, tilted[::-1])
    original = cut_pattern_quality(a, tilted)
    assert mirrored["connected"]["lower_edge_deg"] == pytest.approx(
        -original["connected"]["upper_edge_deg"], abs=1e-6)
    assert mirrored["connected"]["upper_edge_deg"] == pytest.approx(
        -original["connected"]["lower_edge_deg"], abs=1e-6)


def test_interpolation_is_angularly_consistent():
    # exact half-pressure threshold (20*log10(0.5)), not the rounded -6.0206 label
    analytic = 2.0 * abs(20.0 * np.log10(0.5)) / 0.1   # crossing at 60.2060 deg each side

    coarse_a = _angles(5.0)
    coarse_s = -0.1 * np.abs(coarse_a)
    fine_a = _angles(0.5)
    fine_s = -0.1 * np.abs(fine_a)

    coarse = connected_main_lobe(coarse_a, coarse_s)
    fine = connected_main_lobe(fine_a, fine_s)
    legacy_coarse = legacy_outermost_width(coarse_a, coarse_s)

    assert coarse["width_deg"] == pytest.approx(analytic, abs=1e-6)
    assert fine["width_deg"] == pytest.approx(analytic, abs=1e-6)
    assert coarse["width_deg"] == pytest.approx(fine["width_deg"], abs=1e-6)
    assert legacy_coarse["width_deg"] == pytest.approx(analytic, abs=1e-6)


# --------------------------------------------------------------------------- response wrapper


def test_response_wrapper_annotates_missing_balloon():
    a = _angles()
    s = _gaussian(a, 25.0)
    resp = SimpleNamespace(
        freqs_hz=np.array([1000.0, 2000.0]),
        h_angles_deg=a, v_angles_deg=a.copy(),
        spl_h_db=np.tile(s, (2, 1)), spl_v_db=np.tile(s, (2, 1)),
        spl_balloon_db=None, balloon_dirs=None, meta={},
    )
    report = pattern_quality_from_response(resp, coverage_h_deg=80.0, coverage_v_deg=50.0)

    assert report["balloon"]["status"] == "unavailable"
    assert report["balloon"]["error_type"] == "BalloonUnavailableError"
    for row in report["per_frequency"]:
        assert row["balloon"]["di_db"] is None
        assert row["balloon"]["lobe_map"] is None
        assert row["H"]["legacy"]["width_deg"] == pytest.approx(50.0, abs=1e-6)
        assert row["V"]["off_axis"]["mean_excess_in_coverage_db"] is not None


def test_response_wrapper_balloon_valid():
    a = _angles()
    s = _gaussian(a, 25.0)
    dirs, grid, theta_per_sample = _structured_balloon()
    beam = -6.0206 * (theta_per_sample / 20.0) ** 2
    resp = SimpleNamespace(
        freqs_hz=np.array([1000.0, 2000.0]),
        h_angles_deg=a, v_angles_deg=a.copy(),
        spl_h_db=np.tile(s, (2, 1)), spl_v_db=np.tile(s, (2, 1)),
        spl_balloon_db=np.tile(beam, (2, 1)), balloon_dirs=dirs,
        meta={"balloon_grid": list(grid)},
    )
    report = pattern_quality_from_response(resp)

    assert report["balloon"]["status"] == "valid"
    assert report["balloon"]["grid"] == [19, 36]
    assert report["balloon"]["resolution_deg"] is not None
    assert "coarse balloon map" in report["balloon"]["sampling_density_warning"]
    for row in report["per_frequency"]:
        assert row["balloon"]["status"] == "valid"
        assert row["balloon"]["di_db"] is not None
        assert row["balloon"]["lobe_map"] is not None
        assert row["balloon"]["diagonal"]["status"] in (
            "valid", "partial", "censored", "unmeasurable")
