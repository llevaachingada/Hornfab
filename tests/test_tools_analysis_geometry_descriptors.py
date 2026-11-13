"""S8 geometry descriptors: deterministic, scale-aware and score-free."""
from __future__ import annotations

import json
import math

import pytest
import numpy as np

from conftest import requires_mesher
from test_tools_analysis_common import load_tool

gd = load_tool("geometry_descriptors")


def _freeform(scale: float = 1.0):
    from hornlab_search.types import Design

    def profile(r1, angle):
        return {"points": [[0.0, 10.0 * scale], [100.0 * scale, r1 * scale]],
                "throatAngleDeg": 5.0, "mouthAngleDeg": angle}
    return Design("FREEFORM", {
        "profileH": profile(80.0, 45.0),
        "profileV": profile(50.0, 35.0),
        "crossSections": [{"t": 0.0, "shape": "circle"},
                          {"t": 1.0, "shape": "ellipse"}],
    })


def test_strict_design_only_and_recursive_score_assertion():
    from hornlab_search.types import Design

    with pytest.raises(TypeError, match="Design only"):
        gd.geometry_descriptors({"family": "ICW", "params": {}})
    bad = Design("FREEFORM", {"profileH": {"points": [], "metrics": {"j": 1.0}}})
    with pytest.raises(AssertionError, match="forbidden"):
        gd.geometry_descriptors(bad)
    with pytest.raises(AssertionError, match="forbidden"):
        gd.assert_no_score_leakage({"nested": [{"objective": 1.0}]})


def test_meh_and_mid_ports_are_refused_before_resolution():
    from hornlab_search.types import Design

    with pytest.raises(gd.GeometryDescriptorError, match="MEH is paused"):
        gd.geometry_descriptors(Design("MEH", {}))
    with pytest.raises(gd.GeometryDescriptorError, match="mid_ports"):
        gd.geometry_descriptors(Design("OSSE", {"mid_ports": {}}))


def test_cad_and_grid_are_not_silently_approximated():
    from hornlab_search.types import Design

    with pytest.raises(gd.GeometryDescriptorError, match="external STEP"):
        gd.geometry_descriptors(Design("FREEFORM", {"cad": {}}))
    with pytest.raises(gd.GeometryDescriptorError, match="not admitted"):
        gd.geometry_descriptors(Design("FREEFORM", {"grid": {}}))


def test_behavior_descriptors_are_separate_band_aware_and_score_free():
    from hornlab_search.types import MetricSet

    freqs = np.array([500.0, 1000.0, 2000.0, 4000.0])
    metrics = MetricSet(
        freqs_hz=freqs,
        bw_h_deg=np.array([90.0, 80.0, 70.0, 60.0]),
        bw_v_deg=np.array([80.0, 70.0, 60.0, 50.0]),
        di_db=np.array([4.0, 5.0, 6.0, 7.0]), di_source="balloon",
        ripple_h_db=np.array([3.0, 2.0, 1.0, 0.5]),
        ripple_v_db=np.array([4.0, 3.0, 2.0, 1.0]),
        on_axis_db=np.zeros(4), z_throat_real=None,
        scalars={"objective": -999.0, "score": 123.0},
    )
    out = gd.behavior_descriptors(metrics, (1000.0, 2000.0))
    assert out["band_hz"] == {"lo": 1000.0, "hi": 2000.0}
    assert out["frequency_samples_in_band"] == 2
    assert out["behavior"]["mean_bw_h_deg"] == 75.0
    assert out["behavior"]["mean_di_db"] == 5.5
    assert out["geometry_included"] is False
    assert out["score_fields_included"] is False
    assert "objective" not in json.dumps(out).casefold()


def test_behavior_descriptors_refuse_rows_and_bad_bands():
    with pytest.raises(TypeError, match="MetricSet only"):
        gd.behavior_descriptors({"metrics": {}}, (1000.0, 2000.0))


def test_navigation_is_deterministic_geometry_only_and_handles_zero_std():
    items = []
    for i, scale in enumerate((1.0, 1.2, 2.0, 2.2)):
        values = {key: (1.0 if key == "mouth_aspect_w_h" else scale * (j + 1))
                  for j, key in enumerate(gd.NUMERIC_DESCRIPTOR_KEYS)}
        items.append({"design_hash": f"d{i}", "geometry": values})
    a = gd.navigation_map(items, n_clusters=2, seed=7)
    b = gd.navigation_map(items, n_clusters=2, seed=7)
    assert a == b
    assert a["navigation_only"] is True and a["ranking"] is False
    assert "mouth_aspect_w_h" in a["standardization"]["zero_variance_keys"]
    assert [r["design_hash"] for r in a["rows"]] == ["d0", "d1", "d2", "d3"]
    with pytest.raises(gd.GeometryDescriptorError, match="fixed geometry vector"):
        gd.navigation_map([{"design_hash": "x", "geometry": {"score": 1.0}}])


@requires_mesher
def test_freeform_is_deterministic_and_scale_aware():
    a = gd.geometry_descriptors(_freeform())
    repeat = gd.geometry_descriptors(_freeform())
    b = gd.geometry_descriptors(_freeform(2.0))
    assert a == repeat
    ga, gb = a["geometry"], b["geometry"]
    for key in ("length_mm", "mouth_width_mm", "mouth_height_mm"):
        assert gb[key] == pytest.approx(2.0 * ga[key], rel=2e-3)
    for key in ("mouth_projected_area_mm2", "throat_projected_area_mm2"):
        assert gb[key] == pytest.approx(4.0 * ga[key], rel=3e-3)
    for key in ("mouth_aspect_w_h", "mouth_to_throat_area_ratio",
                "mouth_width_over_length", "mouth_height_over_length"):
        assert gb[key] == pytest.approx(ga[key], rel=3e-3)
    assert a["termination"] == {
        "kind": "freeform", "mouth_angle_h_deg": 45.0,
        "mouth_angle_v_deg": 35.0, "cross_section_shape": "ellipse"}
    assert a["provenance"]["gmsh_called"] is False
    assert a["provenance"]["bem_called"] is False
    assert len(a["provenance"]["resolver_source_sha256"]) == 64


@requires_mesher
@pytest.mark.parametrize("family,params,termination_kind", [
    ("OSSE", dict(r0_mm=17.78, a_deg=37.5, a0_deg=15.5, L_mm=260.0,
                  n=4.0, s=0.7, q=0.995, k=1.0, exponent=4.0, aspect_ratio=1.25), "osse"),
    ("R-OSSE", dict(R_mm=150.0, r0_mm=12.7, a_deg=60.0, a0_deg=15.5,
                    k=1.0, q=1.0, exponent=2.0, aspect_ratio=1.0), "r-osse"),
])
def test_osse_families_resolve_without_approximating(family, params, termination_kind):
    from hornlab_search.types import Design

    out = gd.geometry_descriptors(Design(family, params))
    assert out["family"] == family
    assert out["termination"]["kind"] == termination_kind
    assert all(math.isfinite(out["geometry"][k]) and out["geometry"][k] > 0.0
               for k in gd.NUMERIC_DESCRIPTOR_KEYS)


def test_nonfinite_and_malformed_inputs_refuse():
    from hornlab_search.types import Design

    with pytest.raises(gd.GeometryDescriptorError, match="resolution_mm"):
        gd.geometry_descriptors(_freeform(), resolution_mm=float("nan"))
    bad = _freeform()
    bad.params["profileH"]["points"][1][1] = float("nan")
    with pytest.raises(gd.GeometryDescriptorError, match="resolve failed"):
        gd.geometry_descriptors(bad)


@requires_mesher
def test_icw_exact_scale_ratios_and_termination():
    from hornlab_search.types import Design

    design = Design("ICW", {
        "termination": "flat_baffle", "r0_mm": 12.7, "a0_deg": 14.5,
        "L_mm": 160.0, "R_mm": 130.0, "coverage_angle_deg": 50.0,
        "hold_start": 0.30, "hold_end": 0.70, "kappa0": 0.25,
        "theta1_deg": 16.0, "n_coeff": 12, "kappa_abs_max": 1.0,
        "dkappa_ds_abs_max": 10.0, "theta_max_deg": 91.0,
    })
    out = gd.geometry_descriptors(design)
    assert out["termination"] == {"kind": "flat_baffle"}
    assert out["geometry"]["length_mm"] > 0.0
    assert out["geometry"]["mouth_aspect_w_h"] == pytest.approx(1.0, rel=1e-3)
    # ICW's R_mm is a curve constraint, not a promise that the resolved terminal
    # ring is exactly radius R.  The descriptor must report the canonical surface,
    # not silently replace it with the seed parameter.
    assert out["geometry"]["mouth_to_throat_area_ratio"] > 1.0
    assert out["geometry"]["mouth_projected_area_mm2"] == pytest.approx(
        0.25 * math.pi * out["geometry"]["mouth_width_mm"]
        * out["geometry"]["mouth_height_mm"], rel=2e-2)


@requires_mesher
def test_cli_writes_json_and_md_from_exact_design_contract(tmp_path):
    input_path = tmp_path / "designs.json"
    input_path.write_text(json.dumps({"family": _freeform().family,
                                      "params": _freeform().params}), encoding="utf-8")
    out = tmp_path / "out"
    assert gd.main(["--input", str(input_path), "--out", str(out)]) == 0
    payload = json.loads((out / "geometry_descriptors.json").read_text(encoding="utf-8"))
    assert payload["geometry_only"] is True
    assert payload["descriptor_keys"] == list(gd.NUMERIC_DESCRIPTOR_KEYS)
    assert (out / "geometry_descriptors.md").is_file()


def test_cli_refuses_search_rows_and_score_columns(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"family": "FREEFORM", "params": {}, "objective": 1.0}),
                    encoding="utf-8")
    with pytest.raises(gd.GeometryDescriptorError, match="exactly family and params"):
        gd.main(["--input", str(path), "--out", str(tmp_path / "out")])


def test_cli_refuses_output_overwrite_and_file_out(tmp_path):
    source = tmp_path / "geometry_descriptors.json"
    source.write_text(json.dumps({"family": _freeform().family, "params": _freeform().params}),
                      encoding="utf-8")
    with pytest.raises(gd.GeometryDescriptorError, match="overwrite"):
        gd.main(["--input", str(source), "--out", str(tmp_path)])
    out_file = tmp_path / "not-a-dir"
    out_file.write_text("x", encoding="utf-8")
    with pytest.raises(gd.GeometryDescriptorError, match="must be a directory"):
        gd.main(["--input", str(source), "--out", str(out_file)])

