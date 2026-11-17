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
    # The censored cell stores a WIDTH (the grid extent), never a "lower bound".
    assert connected["censored_legacy_width_deg"] == pytest.approx(180.0)
    assert "censored_lower_bound_deg" not in connected

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


def test_nonfinite_near_lobe_samples_are_floored_not_crashed():
    a = _angles()
    s = _gaussian(a, 25.0)
    # Inject NaN where the pattern is at -0.24 dB (well above the -6.02 dB threshold), not at a
    # 70 dB-down grid edge.  This actually exercises the -120 dB floor: each NaN becomes a hole
    # in the above-threshold run, so the boresight-connected width stops at the hole while the
    # legacy OUTERMOST crossings still reach the real +/-25 deg edges.
    i_neg5 = int(np.flatnonzero(np.isclose(a, -5.0))[0])
    i_pos5 = int(np.flatnonzero(np.isclose(a, 5.0))[0])
    s[i_neg5] = np.nan
    s[i_pos5] = np.nan

    report = cut_pattern_quality(a, s)
    assert report["legacy"]["status"] == "valid"
    assert report["legacy"]["width_deg"] == pytest.approx(50.0, abs=1e-6)
    assert report["legacy"]["n_crossings"] == 6          # each floored NaN adds a pair
    assert report["connected"]["status"] == "valid"
    assert report["connected"]["width_deg"] < 10.0       # first crossing is the +/-5 deg hole
    assert report["connected"]["width_deg"] > 0.0
    assert report["connected"]["n_threshold_transitions"] == 6
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


def test_missing_balloon_grid_is_refused_not_silently_equal_area():
    dirs, _grid, theta_per_sample = _structured_balloon()
    beam = -6.0206 * (theta_per_sample / 20.0) ** 2

    # A stored response without a balloon_grid must never switch quadrature silently: the same
    # beam would read a very different DI with equal-area weights.
    with pytest.raises(BalloonUnavailableError, match="no balloon_grid"):
        balloon_directivity(beam, dirs, grid=None)
    with pytest.raises(BalloonUnavailableError, match="no balloon_grid"):
        balloon_lobe_map(beam[None, :], dirs, None)


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

    # (A same-array H/V comparison was vacuous and is deliberately gone.)

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


# --------------------------------------------------------------------------- parity report CLI

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_REPORT_TOOL = _ROOT / "tools" / "analysis" / "pattern_quality_report.py"
_RUN_CROWE = _ROOT / "runs" / "20261115T205453Z-screen-32f7c4" / "designs" / "22365b569be9"
_RUN_KLANG = _ROOT / "runs" / "20261116T225543Z-screen-6acf41" / "designs" / "491efb2132b8"
_RUN_OSSE = (_ROOT / "runs" / "20261116T153619Z-screen-c221aa" / "designs"
             / "6d6dd332b282")
_HAS_PARITY_RUNS = all((d / "response.npz").is_file() and (d / "metrics.json").is_file()
                       for d in (_RUN_CROWE, _RUN_KLANG, _RUN_OSSE))


def _report_tool():
    spec = importlib.util.spec_from_file_location("pattern_quality_report_tool", _REPORT_TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_report_requires_an_explicit_out_and_prints_a_typed_error(capsys):
    report = _report_tool()
    with pytest.raises(SystemExit) as exc:
        report.main(["some-input"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "pattern_quality_report: argument error" in err
    assert "--out" in err


def test_parity_comparison_excludes_sentinel_and_detects_a_di_delta():
    report = _report_tool()
    fabricated = {
        "per_frequency": [
            {"freq_hz": 100.0,
             "H": {"legacy": {"width_deg": 10.0}},
             "V": {"legacy": {"width_deg": 20.0}},
             "balloon": {"di_db": 1.0}},
            {"freq_hz": 200.0,
             "H": {"legacy": {"width_deg": 11.0}},
             "V": {"legacy": {"width_deg": 21.0}},
             "balloon": {"di_db": 3.0}},
        ],
        "balloon": {"status": "valid"},
    }
    stored = {"freqs_hz": [100.0, 200.0],
              "bw_h_deg": [10.0, 180.0],          # second H cell is the no-crossing sentinel
              "bw_v_deg": [20.0, 180.0],
              "di_db": [1.0, 2.0]}
    comp = report.parity_comparison(fabricated, stored)
    assert comp["legacy_comparable_cells"] == 2
    assert comp["legacy_h_cells"] == 1 and comp["legacy_v_cells"] == 1
    assert comp["legacy_max_abs_delta_deg"] == pytest.approx(0.0, abs=1e-15)
    assert comp["di_comparable_cells"] == 2
    assert comp["di_max_abs_delta_db"] == pytest.approx(1.0)
    assert comp["failed"] is True


@pytest.mark.skipif(not _HAS_PARITY_RUNS,
                    reason="requires the local stored runs and metrics.json files")
def test_parity_mode_reproduces_the_published_zero_and_8_882e_16(tmp_path, capsys):
    report = _report_tool()
    rc = report.main([str(_RUN_CROWE), str(_RUN_KLANG), str(_RUN_OSSE),
                      "--out", str(tmp_path), "--parity"])
    out = capsys.readouterr().out
    assert rc == 0
    legacy_lines = [ln for ln in out.splitlines() if "comparable legacy cells=" in ln]
    di_lines = [ln for ln in out.splitlines() if "max|diag_di - stored_metrics_di|" in ln]
    assert len(legacy_lines) == 3 and len(di_lines) == 3
    assert all("0.000e+00 deg" in ln for ln in legacy_lines)
    assert all("8.882e-16 dB" in ln for ln in di_lines)
    assert (tmp_path / "parity_check.json").is_file()


def test_report_refuses_typed_input_errors_but_reraises_tool_bugs(tmp_path, monkeypatch):
    report = _report_tool()
    design = tmp_path / "designs" / "abc123"
    design.mkdir(parents=True)
    (design / "response.npz").write_bytes(b"not-an-npz")

    def typed(path):
        raise PatternQualityInputError("corrupt stored response")

    monkeypatch.setattr(report, "load_response", typed)
    rc = report.main([str(design), "--out", str(tmp_path / "out")])
    assert rc == 2

    def bug(path):
        raise RuntimeError("tool bug must surface")

    monkeypatch.setattr(report, "load_response", bug)
    with pytest.raises(RuntimeError, match="tool bug must surface"):
        report.main([str(design), "--out", str(tmp_path / "out2")])
