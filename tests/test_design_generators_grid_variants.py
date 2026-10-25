"""Photo-driven JMLC-family variants (fix-6): span/harmonic/variant knobs. Offline.

BINDING RESEARCH: docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md.
C2 symmetry basis (verbatim): with phi measured FROM THE HORIZONTAL mouth-plane axis (+x),
left-right mirror is x -> -x / phi -> pi - phi; the invariant basis is
{cos 2k phi, sin(2k+1) phi}.  Even cosines are quarter-safe; odd sines (and the axial bend
bend*sin phi) require the HALF model (quadrants "14", plane yz, x >= 0); a cos(phi) term
breaks the LR mirror and is refused.  P = (y cos phi, y sin phi, x), millimetres.

Covered: fc_h==fc_v axisymmetric rows; the cos2-phi (side-deep) and sin-phi (top!=bottom)
laws; the cos(phi) refusal; half-grid endpoint rows on yz; the W fc_h ~= H fc_v datasheet
invariant on the saddle seed; the iwata_ar AR=1/area-product/extent laws; the toroidal
C1 + 2 r_lip width gain + the lib-2 JMLC-350 plausibility check; the three configs and
catalog entries.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from conftest import EXAMPLES
from hornlab_search.config import load_config
from hornlab_search.design import families
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import registry
from hornlab_search.design.generators import profiles as P
from hornlab_search.design.space import DesignSpace
from hornlab_search.search.campaign import is_compatible, load_catalog
from hornlab_search.types import Design

TYP = EXAMPLES / "typologies"
BRIEFS = EXAMPLES / "briefs"
R0 = 12.7
A0 = 5.0

ORG_BRIEF = {
    "driver": {"exit_radius_mm": R0, "exit_angle_deg": A0},
    "envelope": {"max_mouth_w_mm": 520.0, "max_mouth_h_mm": 420.0, "max_depth_mm": 260.0},
}
AXI_BRIEF = {
    "driver": {"exit_radius_mm": R0, "exit_angle_deg": A0},
    "envelope": {"max_mouth_w_mm": 360.0, "max_mouth_h_mm": 360.0, "max_depth_mm": 220.0},
}


def _rows_spec(kind="salmon_elliptical", *, span=None, n_phi=25, wt=3.0):
    spec = {"name": "grid", "rows": {"type": kind}, "n_phi": n_phi, "n_s": 32,
            "wall_thickness_mm": wt}
    if span is not None:
        spec["span"] = span
    return spec


def _grid(spec, knobs, brief=ORG_BRIEF):
    return G.rows_grid_points(spec, knobs, brief)


# ------------------------------------------------------------------ C2 basis / span

def test_cos2_only_keeps_the_lr_mirror_and_rolls_the_sides_deepest():
    phis = np.linspace(-0.5 * math.pi, 0.5 * math.pi, 25)
    mult = G.rows_stop_multiplier(phis, [0.25], [])
    # LR mirror phi -> pi - phi
    np.testing.assert_allclose(mult, G.rows_stop_multiplier(math.pi - phis, [0.25], []),
                               rtol=0.0, atol=1e-12)
    # deepest rollback at the sides (phi = 0), shallowest at +/-90
    i_side = int(np.argmin(np.abs(phis)))
    assert mult[i_side] == pytest.approx(1.25)
    assert mult[0] == pytest.approx(mult[-1]) == pytest.approx(0.75)
    assert mult[i_side] > mult[0]


def test_sin_phi_keeps_the_lr_mirror_and_makes_top_differ_from_bottom():
    phis = np.linspace(-0.5 * math.pi, 0.5 * math.pi, 25)
    mult = G.rows_stop_multiplier(phis, [], [0.2])
    np.testing.assert_allclose(mult, G.rows_stop_multiplier(math.pi - phis, [], [0.2]),
                               rtol=0.0, atol=1e-12)
    assert mult[-1] == pytest.approx(1.2)     # top (phi = +90)
    assert mult[0] == pytest.approx(0.8)      # bottom (phi = -90)
    assert mult[-1] != pytest.approx(mult[0])


def test_cos_phi_is_refused():
    with pytest.raises(registry.GeneratorError, match="mirror|left-right|foreign"):
        G.rows_task_harmonics({"g_stop_cos1k": 0.2}, half=False)


def test_cos_phi_is_refused_through_the_knob_path_too():
    with pytest.raises(registry.GeneratorError, match="mirror|left-right|foreign"):
        _grid(_rows_spec("salmon_elliptical", n_phi=15),
              {"g_fc_h_hz": 800.0, "g_fc_v_hz": 1200.0, "g_T": 0.8,
               "g_stop_deg": 170.0, "g_stop_cos1k": 0.2})


def test_b_terms_and_bend_require_the_half_span():
    with pytest.raises(Exception, match="half"):
        G.rows_task_harmonics({"g_stop_sin2k1": [0.2]}, half=False)
    with pytest.raises(Exception, match="half"):
        G.rows_task_harmonics({"g_bend_sin1_mm": 5.0}, half=False)


def test_half_span_phi_endpoints_lie_on_the_yz_plane_and_mirror():
    # symmetric half model: row -90 and row +90 are y-mirror images with x = z = 0 plane
    spec = _rows_spec("salmon_axisym", span="half", n_phi=25)
    knobs = {"g_fc_h_hz": 800.0, "g_fc_v_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0}
    grid, meta = _grid(spec, knobs)
    assert meta["span"] == "half" and meta["half_model"] is True
    assert meta["quadrants"] == "14" and meta["symmetry_plane"] == "yz"
    assert np.allclose(grid[0, :, 0], 0.0, atol=1e-9)
    assert np.allclose(grid[-1, :, 0], 0.0, atol=1e-9)
    np.testing.assert_allclose(grid[0, :, 1], -grid[-1, :, 1], rtol=0.0, atol=1e-9)
    np.testing.assert_allclose(grid[0, :, 2], grid[-1, :, 2], rtol=0.0, atol=1e-9)


def test_half_span_needs_an_odd_n_phi_of_at_least_25():
    spec = _rows_spec("salmon_axisym", span="half", n_phi=24)
    with pytest.raises(Exception, match="ODD|odd|25"):
        _grid(spec, {"g_fc_h_hz": 800.0, "g_fc_v_hz": 800.0, "g_T": 0.8,
                     "g_stop_deg": 170.0})


def test_fc_h_equals_fc_v_is_the_axisymmetric_rows():
    base = {"g_T": 0.8, "g_stop_deg": 170.0}
    ell, _ = _grid(_rows_spec("salmon_elliptical", span="quarter", n_phi=15),
                   {**base, "g_fc_h_hz": 800.0, "g_fc_v_hz": 800.0})
    ax, _ = _grid(_rows_spec("salmon_axisym", span="quarter", n_phi=15),
                  {**base, "g_fc_h_hz": 800.0, "g_fc_v_hz": 800.0})
    np.testing.assert_allclose(ell, ax, rtol=0.0, atol=1e-9)


# ------------------------------------------------------------------ saddle config / invariant

def test_saddle_config_is_a_half_model_with_the_datasheet_invariant():
    cfg = load_config(TYP / "salmon_saddle.yaml")
    space = DesignSpace.from_config(cfg)
    assert space.keys() == ["g_T", "g_fc_h_hz", "g_fc_v_hz", "g_stop_deg"]
    block = space.seed.params["grid"]
    assert block["span"] == "half" and block["n_phi"] == 25
    assert block["knobs"]["g_stop_cos2k"] == [0.25]
    assert block["knobs"]["g_stop_sin2k1"] == [0.2]
    assert isinstance(space, GeneratedSpace)
    assert cfg.brief is not None
    families.validate(space.seed)
    grid, meta = G.rows_grid_points(
        {k: v for k, v in block.items() if k != "knobs"}, block["knobs"], cfg.brief)
    assert meta["span"] == "half" and meta["quadrants"] == "14"
    # W fc_h ~= H fc_v (the lib-2 datasheet invariant), report-only in the meta too
    assert abs(meta["wfc_over_hfc"] - 1.0) <= 0.02
    assert meta["w_times_fc_h"] == pytest.approx(
        meta["mouth_w_mm"] * block["knobs"]["g_fc_h_hz"])
    assert meta["h_times_fc_v"] == pytest.approx(
        meta["mouth_h_mm"] * block["knobs"]["g_fc_v_hz"])
    # top != bottom: the +90 row is the deeper of the two ends
    stops = meta["row_stop_deg"]
    assert stops[-1] > stops[0]
    assert meta["rows"][-1]["mouth_y_mm"] != meta["rows"][0]["mouth_y_mm"]
    print(f"\nsaddle seed: W {meta['mouth_w_mm']:.1f} H {meta['mouth_h_mm']:.1f} "
          f"Wfc {meta['w_times_fc_h']:.0f} Hfc {meta['h_times_fc_v']:.0f} "
          f"ratio {meta['wfc_over_hfc']:.4f}; top {stops[-1]:.1f} bottom {stops[0]:.1f}")


# ------------------------------------------------------------------ iwata_ar

def _iwata(knobs, brief=ORG_BRIEF):
    return _grid(_rows_spec("iwata_ar", n_phi=15, wt=2.0), knobs, brief)


def test_iwata_ar1_equals_the_plain_lecleach_rows():
    k = {"g_fc_hz": 800.0, "g_T": 0.5, "g_stop_deg": 180.0, "g_ar_m": 1.0, "g_ar_p": 1.0}
    ar1, _ = _iwata(k)
    plain, _ = _grid(_rows_spec("lecleach", n_phi=15), {
        "g_fc_hz": 800.0, "g_T": 0.5, "g_stop_deg": 180.0})
    np.testing.assert_allclose(ar1, plain, rtol=0.0, atol=1e-9)


def test_iwata_ar_area_product_and_mouth_scaling():
    base_k = {"g_fc_hz": 800.0, "g_T": 0.5, "g_stop_deg": 180.0, "g_ar_p": 1.0}
    ar2, meta2 = _iwata({**base_k, "g_ar_m": 2.0})
    ar1, _ = _iwata({**base_k, "g_ar_m": 1.0})
    # H row (phi = 0) and V row (phi = 90) share the same l stations (resample=False)
    r_h = np.hypot(ar2[0, :, 0], ar2[0, :, 1])
    r_v = np.hypot(ar2[-1, :, 0], ar2[-1, :, 1])
    r_base = np.hypot(ar1[0, :, 0], ar1[0, :, 1])
    assert np.max(np.abs(r_h * r_v - r_base ** 2)) <= 1e-9
    # mouth extents follow sqrt(AR_m) / 1/sqrt(AR_m)
    mouth_base = float(r_base[-1])
    assert float(r_h[-1]) == pytest.approx(mouth_base * math.sqrt(2.0), abs=1e-6)
    assert float(r_v[-1]) == pytest.approx(mouth_base / math.sqrt(2.0), abs=1e-6)
    assert "our reconstruction of the published principle" in meta2["construction_label"]
    assert meta2["ar_m"] == pytest.approx(2.0) and meta2["ar_p"] == pytest.approx(1.0)


def test_iwata_ar_is_quarter_only():
    with pytest.raises(Exception, match="quarter"):
        _grid(_rows_spec("iwata_ar", span="half", n_phi=25, wt=2.0),
              {"g_fc_hz": 800.0, "g_T": 0.5, "g_stop_deg": 180.0,
               "g_ar_m": 2.0, "g_ar_p": 1.0})


# ------------------------------------------------------------------ toroidal_rollback

def _march(fc=600.0, T=0.8, stop=170.0, r0=12.7):
    return P.lecleach_exact(r0, fc, T, 5.0, stop, 1.0, c=P.C_AIR)


def test_toroidal_lip_is_tangent_continuous_at_the_joint():
    x, y, phi, meta = _march()
    last_seg = math.degrees(math.atan2(y[-1] - y[-2], x[-1] - x[-2]))
    _xl, _yl, lip = G.append_tangent_lip(x, y, 30.0, float(meta["stop_deg"]))
    assert lip["joint_tangent_deg"] == pytest.approx(float(meta["stop_deg"]))
    assert abs(last_seg - lip["joint_tangent_deg"]) <= 0.01


def test_toroidal_lip_adds_two_radii_to_the_width_at_the_max_y_bearing():
    # A vertical wall ending exactly at its max-y bearing; the tangent arc reaches
    # C_y + r = y_end + r, so the (two-sided) width grows by exactly 2 r.
    x = np.array([0.0, 0.0])
    y = np.array([10.0, 40.0])
    r = 10.0
    xl, yl, lip = G.append_tangent_lip(x, y, r, 90.0)
    plain_w = 2.0 * float(np.max(y))
    lip_w = 2.0 * float(np.max(yl))
    assert lip_w - plain_w == pytest.approx(2.0 * r, abs=0.1)
    assert lip["applied"] is True and lip["wrap_deg"] == pytest.approx(180.0)


def test_toroidal_lib2_jmlc350_plausibility_check():
    """LABELED [documented-inputs, inferred]: fc 350 / T 0.8 / r0 25.4 mm / r_lip 30 mm.

    phi0 = 5 deg is OUR assumption (the product's exit/fc/T/stop are unpublished); the
    speed of sound is the published case's own c = 344 m/s.  The tangent-arc lip gives a
    594.1 mm overall width vs the published JMLC-350 diameter 595 mm (inside +/-3 mm).
    This is a plausibility check, NOT a reproduction claim.
    """
    x, y, _phi, meta = P.lecleach_exact(25.4, 350.0, 0.8, 5.0, 360.0, 1.0, c=344.0)
    _xl, yl, _lip = G.append_tangent_lip(x, y, 30.0, float(meta["stop_deg"]))
    width = 2.0 * float(np.max(yl))
    assert abs(width - 595.0) <= 3.0
    print(f"\nJMLC-350 plausibility: plain {2*y.max():.1f} mm -> lip width {width:.2f} mm "
          f"(published 595.0 +/- 3)")


def test_toroidal_rows_pass_the_self_approach_guard():
    spec = _rows_spec("toroidal_rollback", n_phi=15)
    knobs = {"g_fc_hz": 600.0, "g_T": 0.8, "g_stop_deg": 170.0, "g_r_lip_mm": 30.0}
    grid, meta = _grid(spec, knobs, AXI_BRIEF)
    assert meta["lip_wrap_deg"] == pytest.approx(180.0)
    assert meta["min_self_approach_mm"] >= 2.0 * 3.0 + G.SELF_APPROACH_MARGIN_MM
    outer = G.grid_outer_points(grid, 3.0)
    assert outer.shape == grid.shape
    # the same guard refuses a folded sheet (limit 2t + 2)
    theta = np.linspace(0.0, 1.5 * math.pi, 33)
    rho = 10.0 + 3.0 * np.cos(theta)
    z = 3.0 * np.sin(theta)
    phis = np.linspace(0.0, 0.5 * math.pi, 15)
    curled = np.stack([np.stack([rho * math.cos(p), rho * math.sin(p), z], axis=-1)
                       for p in phis])
    with pytest.raises(Exception, match="self-approach"):
        G.grid_outer_points(curled, 3.0)


def test_toroidal_is_axisymmetric_quarter_only():
    spec = _rows_spec("toroidal_rollback", span="half", n_phi=25)
    with pytest.raises(Exception, match="quarter"):
        _grid(spec, {"g_fc_hz": 600.0, "g_T": 0.8, "g_stop_deg": 170.0,
                     "g_r_lip_mm": 30.0}, AXI_BRIEF)


# ------------------------------------------------------------------ lecleach harmonic rows

def test_lecleach_rows_accept_the_cos_harmonic_and_per_azimuth_fc_pair():
    spec = _rows_spec("lecleach", n_phi=15)
    knobs = {"g_fc_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0,
             "g_fc_h_hz": 800.0, "g_fc_v_hz": 1200.0, "g_stop_cos2k": [0.1]}
    _grid_, meta = _grid(spec, knobs, AXI_BRIEF)
    assert meta["fc_h_hz"] == pytest.approx(800.0)
    assert meta["fc_v_hz"] == pytest.approx(1200.0)
    assert max(meta["row_fc_hz"]) > min(meta["row_fc_hz"])
    assert meta["stop_cos2k"] == [0.1]
    assert meta["row_stop_deg"][0] > meta["row_stop_deg"][-1]


def test_lecleach_lone_fc_v_is_refused_and_unknown_knobs_are_refused():
    spec = _rows_spec("lecleach", n_phi=15)
    base = {"g_fc_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0}
    with pytest.raises(Exception, match="foreign knob"):
        _grid(spec, {**base, "g_fc_v_hz": 1200.0}, AXI_BRIEF)
    with pytest.raises(Exception, match="foreign"):
        _grid(spec, {**base, "g_nonsense": 1.0}, AXI_BRIEF)


# ------------------------------------------------------------------ defaults / canonicalisation

def test_absent_and_explicit_zero_harmonics_are_the_same_recipe():
    spec = _rows_spec("salmon_elliptical", span="quarter", n_phi=15)
    base = {"g_fc_h_hz": 800.0, "g_fc_v_hz": 1200.0, "g_T": 0.8, "g_stop_deg": 170.0}
    a = G.design_params(spec, base, ORG_BRIEF)["grid"]
    b = G.design_params(spec, {**base, "g_stop_cos2k": [], "g_stop_sin2k1": [0.0],
                               "g_bend_sin1_mm": 0.0}, ORG_BRIEF)["grid"]
    assert a == b
    assert "g_stop_cos2k" not in b["knobs"]


def test_bend_shifts_the_mouth_plane_of_the_half_rows():
    spec = _rows_spec("salmon_axisym", span="half", n_phi=25)
    base = {"g_fc_h_hz": 800.0, "g_fc_v_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0}
    g0, _ = _grid(spec, base)
    gb, mb = _grid(spec, {**base, "g_bend_sin1_mm": 5.0})
    # w(s) = 3s^2 - 2s^3: zero at the throat, one at the mouth
    np.testing.assert_allclose(gb[:, 0, 2], g0[:, 0, 2], rtol=0.0, atol=1e-12)
    assert gb[0, -1, 2] - g0[0, -1, 2] == pytest.approx(-5.0, abs=1e-9)   # phi = -90
    assert gb[-1, -1, 2] - g0[-1, -1, 2] == pytest.approx(5.0, abs=1e-9)   # phi = +90
    i_side = int(np.argmin(np.abs(np.linspace(-0.5, 0.5, 25))))
    assert gb[i_side, -1, 2] == pytest.approx(g0[i_side, -1, 2])
    assert mb["bend_sin1_mm"] == pytest.approx(5.0)


def test_quarter_recipe_has_no_span_key_and_half_recipe_does():
    quarter = G.design_params(_rows_spec("salmon_elliptical", n_phi=15),
                              {"g_fc_h_hz": 800.0, "g_fc_v_hz": 1200.0, "g_T": 0.8,
                               "g_stop_deg": 170.0}, ORG_BRIEF)["grid"]
    assert set(quarter) == set(G.ROWS_BLOCK_KEYS) and "span" not in quarter
    half = G.design_params(_rows_spec("salmon_elliptical", span="half", n_phi=25),
                           {"g_fc_h_hz": 800.0, "g_fc_v_hz": 1200.0, "g_T": 0.8,
                            "g_stop_deg": 160.0, "g_stop_cos2k": [0.25],
                            "g_stop_sin2k1": [0.2]}, ORG_BRIEF)["grid"]
    assert half["span"] == "half"
    assert half["knobs"]["g_stop_cos2k"] == [0.25]


# ------------------------------------------------------------------ configs + catalog

def _version(name):
    return load_config(TYP / f"{name}.yaml")


def test_variant_recipes_round_trip_json_and_materialize():
    expected = {
        "salmon_saddle": {"g_fc_h_hz", "g_fc_v_hz", "g_T", "g_stop_deg"},
        "lecleach_iwata_ar": {"g_ar_m", "g_ar_p", "g_fc_hz", "g_stop_deg"},
        "lecleach_toroidal": {"g_T", "g_fc_hz", "g_r_lip_mm", "g_stop_deg"},
    }
    for name, keys in expected.items():
        cfg = _version(name)
        space = DesignSpace.from_config(cfg)
        assert isinstance(space, GeneratedSpace) and cfg.brief is not None
        assert set(space.keys()) == keys
        families.validate(space.seed)
        json.dumps(space.seed.params)
        json.dumps(space.provenance(space.seed))
        assert registry.envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0
    saddle = DesignSpace.from_config(_version("salmon_saddle"))
    assert saddle.seed.params["grid"]["span"] == "half"
    assert saddle.seed.params["grid"]["n_phi"] == 25
    assert _version("salmon_saddle").mesh.quadrants == "14"
    assert _version("lecleach_iwata_ar").mesh.quadrants == "1"
    assert _version("lecleach_toroidal").mesh.quadrants == "1"


def test_example_catalog_entries_are_honest_and_named_neutrally():
    catalog = load_catalog(EXAMPLES / "catalog.yaml")
    by_name = {e["name"]: e for e in catalog}
    for name in ("salmon_saddle", "lecleach_iwata_ar", "lecleach_toroidal"):
        assert name in by_name
        assert by_name[name]["group"] == "organic"
        assert (EXAMPLES / by_name[name]["config"]).is_file()
    assert by_name["salmon_saddle"]["symmetry"] == "hv"
    assert by_name["lecleach_iwata_ar"]["symmetry"] == "hv"
    assert by_name["lecleach_toroidal"]["symmetry"] == "axisymmetric"
    org = load_config(TYP / "salmon_saddle.yaml").brief
    axi = load_config(TYP / "lecleach_toroidal.yaml").brief
    assert org is not None and axi is not None
    for name in ("salmon_saddle", "lecleach_iwata_ar"):
        ok, why = is_compatible(by_name[name], org)
        assert ok and why == "", (name, why)
    ok, why = is_compatible(by_name["lecleach_toroidal"], axi)
    assert ok and why == ""
    # the axisymmetric torus is correctly SKIPPED under the 90x60 organic brief
    ok, why = is_compatible(by_name["lecleach_toroidal"], org)
    assert not ok and "axisymmetric" in why
    # neutrality: the SHIPPED yamls and catalog never spell a retired product name.
    # (Lowercase row/kind identifiers such as iwata_ar are the landed contract and stay.)
    forbidden = ("FH-N2", "E-JMLC", "EJMLC", "IWATA", "FERGUSON")
    shipped = sorted(EXAMPLES.rglob("*.yaml"))
    assert shipped
    for path in shipped:
        text = path.read_text(encoding="utf-8")
        hits = [token for token in forbidden if token in text]
        assert not hits, (str(path.relative_to(EXAMPLES)), hits)


def test_span_and_kind_consistency_is_enforced():
    # an explicit span must be one of the two landed values
    with pytest.raises(registry.GeneratorError, match="span"):
        _grid(_rows_spec("salmon_elliptical", span="full", n_phi=15),
              {"g_fc_h_hz": 800.0, "g_fc_v_hz": 1200.0, "g_T": 0.8,
               "g_stop_deg": 170.0})
    # span: quarter next to an odd-sine / bend request is a contradiction: those terms
    # are HALF-only in the C2 basis, so the landed route refuses the mis-meshed recipe.
    knobs = {"g_fc_h_hz": 800.0, "g_fc_v_hz": 1200.0, "g_T": 0.8, "g_stop_deg": 170.0}
    quarter = _rows_spec("salmon_elliptical", span="quarter", n_phi=25)
    with pytest.raises(registry.GeneratorError, match="half"):
        _grid(quarter, {**knobs, "g_stop_sin2k1": [0.2]})
    with pytest.raises(registry.GeneratorError, match="half"):
        _grid(quarter, {**knobs, "g_bend_sin1_mm": 5.0})
    # both-mirror-plane kinds refuse an explicit half span (quarter is the honest model)
    with pytest.raises(registry.GeneratorError, match="quarter"):
        _grid(_rows_spec("iwata_ar", span="half", n_phi=25, wt=2.0),
              {"g_fc_hz": 800.0, "g_T": 0.5, "g_stop_deg": 180.0,
               "g_ar_m": 2.0, "g_ar_p": 1.0})
    with pytest.raises(registry.GeneratorError, match="quarter"):
        _grid(_rows_spec("toroidal_rollback", span="half", n_phi=25),
              {"g_fc_hz": 600.0, "g_T": 0.8, "g_stop_deg": 170.0,
               "g_r_lip_mm": 30.0}, AXI_BRIEF)
