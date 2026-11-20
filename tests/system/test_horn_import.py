"""Stage 2 tests: the accel->velocity import boundary and the fixed-horn pilot engine."""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hornlab_search.compare.hornfab_side import canonical_to_accel  # noqa: E402
from hornlab_search.system import contracts as C  # noqa: E402
from hornlab_search.system import horn_import  # noqa: E402
from hornlab_search.system import optimize  # noqa: E402
from hornlab_search.system import provenance  # noqa: E402
from hornlab_search.system import score  # noqa: E402


# --------------------------------------------------------------------------- synthetic asset

def _write_synthetic_response(tmp_path: Path, *, with_balloon: bool = True,
                              with_cuts: bool = True,
                              distance_m: float | None = 2.0) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    freqs = np.array([700.0, 1000.0, 1300.0])
    dirs = np.zeros((9, 3))
    dirs[:, 2] = np.cos(np.linspace(0.0, np.pi, 9))
    dirs[:, 0] = np.sin(np.linspace(0.0, np.pi, 9))
    p_vel = np.exp(-0.5 * (np.linspace(0.0, np.pi, 9)[None, :] * 1.5) ** 2
                   ).astype(np.complex128) * np.ones((3, 1))
    kw: dict[str, Any] = {
        "freqs_hz": freqs,
        "balloon_dirs": dirs,
        "spl_balloon_db": 90.0 + 20.0 * np.log10(np.abs(p_vel)),
        "meta": np.array(json.dumps({"distance_m": distance_m})),
        "backend": np.array("beat_cuda"),
        "n_dof": np.array(1234, dtype=np.int64),
    }
    if with_balloon:
        kw["p_balloon"] = canonical_to_accel(p_vel, freqs)
    if with_cuts:
        ang = np.linspace(-90.0, 90.0, 19)
        shape = np.exp(-0.5 * (np.radians(ang) * 1.2) ** 2).astype(np.complex128)
        pv = np.ones((3, 1)) * shape[None, :]
        kw["h_angles_deg"] = ang
        kw["v_angles_deg"] = ang
        kw["spl_h_db"] = 90.0 + 20.0 * np.log10(np.abs(pv))
        kw["spl_v_db"] = kw["spl_h_db"]
        kw["p_h"] = canonical_to_accel(pv, freqs)
        kw["p_v"] = canonical_to_accel(pv, freqs)
    path = tmp_path / "response.npz"
    np.savez(path, **kw)
    return path


def _asset_for(path: Path, fields: frozenset[str]) -> C.HornAsset:
    return C.HornAsset(
        asset_id="synthetic", design_hash="dh", response_path=str(path),
        mesh_path=None, geometry=C.GeometryMetadata(family="OSSE"),
        available_fields=fields, quality="MAGNITUDE_ONLY",
        freqs_hz=(700.0, 1000.0, 1300.0), source_basis=None,
    )


def test_conversion_is_exactly_the_hornfab_seam(tmp_path: Path) -> None:
    path = _write_synthetic_response(tmp_path)
    asset = _asset_for(path, frozenset({"p_balloon", "spl_balloon_db", "balloon_dirs",
                                        "freqs_hz"}))
    out = horn_import.convert_asset(asset)
    assert out.response.fidelity == "SCREEN_COMPLEX_APPROX"
    basis = out.response.excitation_bases["horn"]
    assert basis.per_input == "normal_velocity_mps"
    assert basis.time_convention == C.TIME_CONVENTION
    assert basis.distance_m == 2.0
    npz = np.load(path)
    expected = __import__("hornlab_search.compare.hornfab_side", fromlist=["x"]).accel_to_canonical(
        npz["p_balloon"], npz["freqs_hz"])
    np.testing.assert_allclose(
        cast(dict, out.response.p_by_excitation)["horn"], expected, rtol=1e-12, atol=0.0)
    # a converted asset NEVER claims phase qualification
    assert out.data_quality["phase_qualified"] is False
    assert "absolute_pa_per_volt" in out.data_quality["claims_refused"]
    assert out.response.require_phase() is None  # fields exist; refusals are label-level


def test_conversion_cuts_mode_and_magnitude_fallback(tmp_path: Path) -> None:
    path = _write_synthetic_response(tmp_path, with_balloon=False)
    asset = _asset_for(path, frozenset({"p_h", "p_v", "spl_h_db", "spl_v_db", "h_angles_deg",
                                        "v_angles_deg", "freqs_hz"}))
    cuts = horn_import.convert_asset(asset, mode="cuts")
    assert cast(dict, cuts.response.p_by_excitation)["horn"].shape[1] == 19 + 19
    assert cuts.response.excitation_bases["horn"].angular_frame == "hornfab_cuts_hv"

    mag_path = _write_synthetic_response(tmp_path / "m", with_balloon=False, with_cuts=False)
    mag_asset = C.HornAsset(
        asset_id="synthetic", design_hash="dh", response_path=str(mag_path),
        mesh_path=None, geometry=C.GeometryMetadata(), available_fields=frozenset({"freqs_hz"}),
        quality="MAGNITUDE_ONLY", freqs_hz=(700.0,), source_basis=None,
    )
    plain = horn_import.convert_asset(mag_asset)
    assert plain.response.fidelity == "SCREEN_MAGNITUDE"
    assert plain.response.excitation_names == ()
    with pytest.raises(C.PhaseUnavailable):
        plain.response.require_phase()


def test_find_asset_missing_is_a_reported_error(tmp_path: Path) -> None:
    with pytest.raises(C.DataQualityError, match="not found"):
        horn_import.find_asset("nope", tmp_path, scan_limit=3)


# --------------------------------------------------------------------------- pilot engine

_MIN_SPEC_FIELDS = dict(
    experiment_id="pilot_test",
    mode="fixed_horn",
    horn=C.HornRef(asset_id="unused"),
    woofer=C.WooferRef(driver_id="faitalpro_12pr300"),
    cabinet=C.VentedBoxRanges(net_volume_l_range=(35.0, 45.0), tuning_hz_range=(30.0, 40.0),
                              port_throat_area_cm2_range=(60.0, 100.0),
                              port_nfr_range=(0.0, 0.0)),
    assembly=C.AssemblyRanges(),
    dsp=C.DspRanges(xo_hz_range=(700.0, 1300.0)),
    target=C.SystemTargets(listening_angle_h_deg=(-30.0, 30.0),
                           listening_angle_v_deg=(-15.0, 15.0), low_freq_f3_hz_max=55.0),
    fidelity="screen_only",
)


def _spec(**overrides: Any) -> C.SystemSpecV1:
    fields: dict[str, Any] = dict(_MIN_SPEC_FIELDS)
    fields.update(overrides)
    return C.SystemSpecV1(**fields)


def test_pilot_is_deterministic_and_refuses_delay_claims(tmp_path: Path) -> None:
    first = optimize.run_pilot(_spec(), limit_boxes=4)
    second = optimize.run_pilot(_spec(), limit_boxes=4)
    assert first.report["json"] == second.report["json"]
    assert first.meta["study_id"] == second.meta["study_id"]
    assert first.rows and second.rows
    row = first.rows[0]
    assert row["claims"]["refused"] == ["coherent_sum", "delay_optimization",
                                        "absolute_pa_per_volt", "installed_directivity",
                                        "system_score"]
    assert row["dsp"]["relative_delay_ms"] == 0.0
    assert row["data_support"]["coherent"] is None
    # no writes outside an explicit case dir
    assert not (tmp_path / "system").exists()


def test_pilot_lf_gate_uses_the_spec_f3_target_only(tmp_path: Path) -> None:
    strict = optimize.run_pilot(_spec(), limit_boxes=3)
    lax = optimize.run_pilot(_spec(target=C.SystemTargets(
        listening_angle_h_deg=(-30.0, 30.0), listening_angle_v_deg=(-15.0, 15.0),
        low_freq_f3_hz_max=70.0)), limit_boxes=3)
    strict_lf = {r["lf_headroom"] for r in strict.rows}
    lax_lf = {r["lf_headroom"] for r in lax.rows}
    assert "FAIL" in strict_lf
    assert lax_lf == {"PASS"}
    # the mini-MEH margin columns are context, never gates
    strict_rows = strict.rows
    assert any(r["lf_row"]["margin_40hz_db"] < 0.0 for r in strict_rows
               if r["lf_headroom"] == "PASS") or strict_lf == {"FAIL"}


def test_pilot_flags_the_piston_handoff_nan_case(tmp_path: Path) -> None:
    """The master-doc 700 Hz case: a 12-inch piston has no -6 dB half-space crossing."""
    result = optimize.run_pilot(_spec(), limit_boxes=2)
    for row in result.rows:
        assert row["crossover_physics"] == "FAIL", row["crossover_screen"]["note"]
        assert "no -6 dB crossing" in row["crossover_screen"]["note"]
        piston_bw = row["crossover_screen"]["piston_bw_deg"]
        key700 = next(k for k in piston_bw if float(k) == 700.0)
        assert not np.isfinite(piston_bw[key700])


def test_pilot_manifest_round_trips(tmp_path: Path) -> None:
    result = optimize.run_pilot(_spec(), limit_boxes=2, out_dir=tmp_path)
    case_dir = Path(result.meta["case_dir"])
    payload = provenance.load_manifest(case_dir / "manifest.json")["payload"]
    assert payload["kind"] == "system_pilot_v0"
    # the manifest stores the CANONICAL form (lists/str-keys/floats); compare like-for-like
    canonical_rows = json.loads(C.canonical_json(list(result.rows)))
    assert payload["rows"] == canonical_rows


def test_pilot_geometry_path_is_a_supported_lf_screening_input() -> None:
    """Regression: the pilot used the non-existent 'LF_TS_SCREENING' fidelity label."""
    geometry = (Path(__file__).resolve().parents[2]
                / "examples" / "systems" / "driver_geometry" / "faitalpro_12pr300.yaml")
    result = optimize.run_pilot(_spec(), geometry_path=geometry, limit_boxes=2)
    assert result.driver.geometry_mm is not None
    # the vendor geometry has only cutout/frame/depth; installed tiers stay refused
    assert result.driver.data_quality["has_full_geometry"] is False
    assert result.rows


def test_pilot_rows_use_scalar_axes_and_f3_is_minimized() -> None:
    """The pilot must emit the same canonical Pareto row contract as woofer_seed."""
    result = optimize.run_pilot(_spec(), limit_boxes=3)
    for row in result.rows:
        assert set(row["axis_directions"]) == set(row["numeric_axes"])
        assert row["axis_directions"]["f3_hz"] == "-"
        assert row["axis_directions"]["net_volume_l"] == "-"
        assert row["axis_directions"]["margin_40hz_db"] == "+"
        assert all(isinstance(v, (int, float)) and not isinstance(v, bool)
                   for v in row["numeric_axes"].values())
        assert all(isinstance(v, bool) for v in row["feasibility"].values())
        assert isinstance(row["rules_skips"], list)

    # Lower F3 dominates higher F3 when every other axis and feasibility flag is equal.
    a = copy.deepcopy(result.rows[0])
    b = copy.deepcopy(result.rows[0])
    for key in a["numeric_axes"]:
        a["numeric_axes"][key] = 1.0
        b["numeric_axes"][key] = 1.0
    a["feasibility"] = {key: True for key in a["feasibility"]}
    b["feasibility"] = {key: True for key in b["feasibility"]}
    a["numeric_axes"]["f3_hz"] = 40.0
    b["numeric_axes"]["f3_hz"] = 50.0
    assert score.dominates(a, b, a["axis_directions"])
    assert not score.dominates(b, a, a["axis_directions"])


# --------------------------------------------------------------------------- beamwidth screen

class _FakeConverted:
    """Minimal duck-type of ConvertedHorn for the beamwidth screen test."""

    def __init__(self, freqs: np.ndarray, dirs: np.ndarray, p: np.ndarray) -> None:
        self.response = C.SystemResponse(
            frequencies_hz=freqs, excitation_names=("horn",),
            p_by_excitation={"horn": p},
            excitation_bases={"horn": C.SourceBasis(per_input="normal_velocity_mps",
                                                    distance_m=2.0, origin_xyz_m=(0, 0, 0),
                                                    angular_frame="cartesian_dirs",
                                                    source_geometry_hash="x")},
            p_total=None, magnitude_screen=None,
            observation_directions=dirs, observation_angles_deg=None,
            fidelity="SCREEN_COMPLEX_APPROX")


def test_horn_balloon_beamwidth_screen_symmetry_and_slope() -> None:
    freqs = np.array([700.0, 1300.0])
    theta = np.linspace(0.0, np.pi, 361)
    dirs = np.stack([np.sin(theta), np.zeros_like(theta), np.cos(theta)], axis=1)
    sigma = np.array([1.0, 0.55])          # narrower lobe at 1300 Hz
    level = np.exp(-0.5 * (theta[None, :] / sigma[:, None]) ** 2)
    p = (level + 0j).astype(np.complex128)
    f, bw, label = optimize.horn_balloon_beamwidth_screen(_FakeConverted(freqs, dirs, p))
    assert label and "screen" in label.lower()
    # -6 dB threshold = amplitude factor 0.5: exp(-.5 (theta/sigma)^2) = .5
    #   -> theta = sigma * sqrt(2*ln 2)
    expected = sigma * np.sqrt(2.0 * math.log(2.0))
    np.testing.assert_allclose(bw, np.degrees(expected), rtol=0.03)
    assert bw[1] < bw[0], f"narrower lobe must read narrower: {bw}"
