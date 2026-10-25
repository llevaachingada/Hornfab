"""TASK C (lib-2 C2): half-model rows, harmonic laws, lecleach_ar, torus lip.

Offline, CPU only.  Source of truth:
``docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md`` (lib-2;
sections 2.2, 2.3, 2.5 and 4) over the verified Fourcade meridian in
``docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md``.

Every variant here is a LABELED reconstruction/hypothesis: NO published per-azimuth
JMLC math, NO published AR construction and NO published torus-lip math exists.  The
phi origin is PINNED to the horizontal (+x) axis in the row builder and in the meta.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from conftest import EXAMPLES
from hornlab_search.config import load_brief, load_config
from hornlab_search.design import families
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import grid as G
from hornlab_search.design.generators import profiles as P
from hornlab_search.design.generators import registry
from hornlab_search.design.space import DesignSpace
from hornlab_search.search.campaign import is_compatible, load_catalog
from hornlab_search.types import Design

R0 = 12.7
A0 = 5.0
TYP = EXAMPLES / "typologies"
BRIEFS = EXAMPLES / "briefs"
BRIEF = {
    "driver": {"exit_radius_mm": R0, "exit_angle_deg": A0},
    "envelope": {"max_mouth_w_mm": 520.0, "max_mouth_h_mm": 420.0, "max_depth_mm": 260.0},
}


def rows_spec(kind: str, n_phi: int = 15, n_s: int = 32) -> dict:
    return {"name": "grid", "rows": {"type": kind}, "n_phi": n_phi, "n_s": n_s,
            "wall_thickness_mm": 3.0}


def mod_knobs(**extra) -> dict:
    out = {"g_fc_hz": 800.0, "g_T": 0.8, "g_stop0_deg": 170.0}
    out.update(extra)
    return out


def ar_knobs(**extra) -> dict:
    out = {"g_fc_hz": 800.0, "g_T": 0.5, "g_stop_deg": 170.0, "g_AR_m": 2.0, "g_p": 1.0}
    out.update(extra)
    return out


def rad(deg):
    return math.radians(float(deg))


# ---------------------------------------------------------------------------
# TASK C: fc_h == fc_v => axisymmetric rows
# ---------------------------------------------------------------------------


def test_fc_h_equal_fc_v_is_axisymmetric_at_1e_9():
    plain, plain_meta = G.rows_grid_points(rows_spec("lecleach"),
                                           {"g_fc_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0},
                                           BRIEF)
    mod, meta = G.rows_grid_points(rows_spec("lecleach_mod"),
                                   mod_knobs(g_fc_v_hz=800.0), BRIEF)
    assert meta["rows_type"] == "lecleach_mod"
    assert meta["row_span"] == "quarter"
    # every row is the same axisymmetric meridian at its own azimuth
    assert np.abs(mod - plain).max() <= 1e-9
    for i in range(mod.shape[0]):
        base = np.hypot(plain[0, :, 0], plain[0, :, 1])
        assert np.abs(np.hypot(mod[i, :, 0], mod[i, :, 1]) - base).max() <= 1e-9
        assert np.abs(mod[i, :, 2] - plain[0, :, 2]).max() <= 1e-9
    assert plain_meta["row_span"] == "quarter"


# ---------------------------------------------------------------------------
# TASK C: cos(2 phi)-only => LR mirror holds + deepest sides
# ---------------------------------------------------------------------------


def test_cos2_term_keeps_the_lr_mirror_and_rolls_the_sides_deepest():
    # Positive a2 => sides (phi = 0 / 180) get the LARGER stop (deeper roll).
    # HALF rows need an odd n_phi >= MIN_PHI_HALF (25); 25 is the landed minimum.
    half, meta = G.rows_grid_points(rows_spec("lecleach_mod", n_phi=25),
                                    mod_knobs(g_stop_a2_deg=30.0, g_stop_b1_deg=0.0),
                                    BRIEF)
    assert meta["row_span"] == "half" and meta["quadrants"] == "14"
    stops = np.asarray(meta["row_stop_deg"], dtype=float)
    phis = np.asarray([r["phi_deg"] for r in meta["rows"]], dtype=float)
    side = int(np.argmin(np.abs(phis)))
    top = int(np.argmax(np.abs(phis)))
    assert stops[side] > stops[top] + 1e-6                # deepest sides
    assert stops[side] == pytest.approx(200.0, abs=1e-9)
    assert np.allclose(stops, G.rows_harmonic_law(np.radians(phis), 170.0, 30.0, 0.0, 0.0, 0.0))

    # LR mirror: stop(phi) == stop(pi - phi) for every phi, so the full surface's
    # x -> -x half is the mirror image of this half.
    for phi_deg in (0.0, 30.0, 60.0, 90.0, -45.0):
        phi = rad(phi_deg)
        s = float(G.rows_harmonic_law(phi, 170.0, 30.0, 0.0, 0.0, 0.0))
        sm = float(G.rows_harmonic_law(math.pi - phi, 170.0, 30.0, 0.0, 0.0, 0.0))
        assert s == pytest.approx(sm, abs=1e-9)
    # cos(2 phi) is up/down even too: row at -phi is the y -> -y mirror of row at +phi.
    n = half.shape[0]
    for i in range(n // 2 + 1):
        expected = half[i].copy()
        expected[:, 1] = -expected[:, 1]
        assert np.abs(expected - half[n - 1 - i]).max() <= 1e-9


# ---------------------------------------------------------------------------
# TASK C: sin(phi) term => LR mirror holds + top != bottom
# ---------------------------------------------------------------------------


def test_sin_phi_term_keeps_the_lr_mirror_and_makes_top_differ_from_bottom():
    half, meta = G.rows_grid_points(rows_spec("lecleach_mod", n_phi=25),
                                    mod_knobs(g_stop_b1_deg=10.0), BRIEF)
    assert meta["row_span"] == "half" and meta["quadrants"] == "14"
    phis = np.asarray([r["phi_deg"] for r in meta["rows"]], dtype=float)
    stops = np.asarray(meta["row_stop_deg"], dtype=float)
    top, bottom = int(np.argmax(phis)), int(np.argmin(phis))
    # b1 = +10 -> the TOP stops 20 deg later than the BOTTOM
    assert stops[top] > stops[bottom] + 1e-6
    assert stops[top] - stops[bottom] == pytest.approx(20.0, abs=1e-9)
    # LR mirror holds: sin(phi) == sin(pi - phi)
    for phi_deg in (0.0, 30.0, 60.0, 90.0, -45.0):
        phi = rad(phi_deg)
        assert float(G.rows_harmonic_law(phi, 170.0, 0.0, 0.0, 10.0, 0.0)) == pytest.approx(
            float(G.rows_harmonic_law(math.pi - phi, 170.0, 0.0, 0.0, 10.0, 0.0)), abs=1e-9)
    # Both +/-90 rows lie exactly on the yz symmetry plane, and the geometry differs:
    assert np.all(half[top, :, 0] == 0.0) and np.all(half[bottom, :, 0] == 0.0)
    assert abs(float(np.hypot(half[top, -1, 0], half[top, -1, 1]))
               - float(np.hypot(half[bottom, -1, 0], half[bottom, -1, 1]))) > 0.1
    # The up/down mirror is BROKEN: a b1 term is odd under phi -> -phi.
    assert not np.allclose(np.hypot(half[top, -1, 0], half[top, -1, 1]),
                           np.hypot(half[bottom, -1, 0], half[bottom, -1, 1]))


@pytest.mark.parametrize("knob", ["g_stop_a1_deg", "g_stop_a3_deg", "g_stop_b2_deg",
                                  "g_stop_b4_deg", "g_bend_cos1_mm"])
def test_odd_cosine_or_even_sine_terms_are_refused(knob):
    with pytest.raises(registry.GeneratorError, match="left-right mirror"):
        G.rows_grid_points(rows_spec("lecleach_mod"), mod_knobs(**{knob: 20.0}), BRIEF)


def test_axial_bend_is_half_only_and_anchored_at_the_throat():
    bend = 5.0
    grid, meta = G.rows_grid_points(rows_spec("lecleach_mod", n_phi=25),
                                    mod_knobs(g_bend_b1_mm=bend), BRIEF)
    assert meta["row_span"] == "half" and meta["quadrants"] == "14"
    assert meta["bend_b1_mm"] == bend
    # w(l/L0) = 0 at the throat: every row still meets at the axis point
    assert float(np.max(np.abs(grid[:, 0, 2]))) <= 1e-12
    # at the mouth, delta-x = bend sin(phi) -> the +90 row is 2*bend ahead of the -90 row
    tip_top = float(grid[-1, -1, 2])
    tip_bottom = float(grid[0, -1, 2])
    assert tip_top - tip_bottom == pytest.approx(2.0 * bend, abs=1e-9)


# ---------------------------------------------------------------------------
# TASK C: the datasheet width*fc invariant (loose)
# ---------------------------------------------------------------------------


def test_width_times_fc_h_equals_height_times_fc_v_within_2_percent():
    _grid, meta = G.rows_grid_points(
        rows_spec("lecleach_mod"),
        mod_knobs(g_fc_v_hz=1100.0), BRIEF)
    w = 2.0 * meta["mouth_radius_h_mm"]
    h = 2.0 * meta["mouth_radius_v_mm"]
    lhs, rhs = w * 800.0, h * 1100.0
    assert abs(lhs - rhs) / (0.5 * (lhs + rhs)) <= 0.02, (w, h, lhs, rhs)


# ---------------------------------------------------------------------------
# TASK C: lecleach_ar area preservation + endpoint exactness
# ---------------------------------------------------------------------------


def test_lecleach_ar_preserves_area_exactly_and_keeps_the_endpoints():
    x, y, _phi, _m = P.lecleach_exact(R0, 800.0, 0.5, A0, 170.0, 1.0)
    AR, y_h, y_v = G.lecleach_ar_profile(x, y, 2.0, 1.0)
    assert AR[0] == pytest.approx(1.0) and AR[-1] == pytest.approx(2.0)
    area = np.pi * y_h * y_v
    ref = np.pi * y * y
    assert np.max(np.abs(area - ref)) <= 1e-9 * np.max(ref)

    grid, meta = G.rows_grid_points(rows_spec("lecleach_ar"), ar_knobs(), BRIEF)
    assert meta["rows_type"] == "lecleach_ar"
    assert meta["construction_label"] == G.ROWS_AR_CONSTRUCTION_LABEL
    assert meta["AR_t"] == 1.0 and meta["AR_m"] == 2.0
    # endpoint exactness: phi = 0 row is y_h, phi = 90 row is y_v, x is the march's own
    rh = float(np.hypot(grid[0, -1, 0], grid[0, -1, 1]))
    rv = float(np.hypot(grid[-1, -1, 0], grid[-1, -1, 1]))
    assert rh == pytest.approx(y_h[-1], abs=1e-9)
    assert rv == pytest.approx(y_v[-1], abs=1e-9)
    assert np.pi * rh * rv == pytest.approx(np.pi * y[-1] ** 2, rel=1e-9)
    assert grid[0, -1, 2] == pytest.approx(x[-1], abs=1e-9)
    assert grid[-1, -1, 2] == pytest.approx(x[-1], abs=1e-9)


# ---------------------------------------------------------------------------
# TASK C: quarter == half when all b-terms are 0 (regression)
# ---------------------------------------------------------------------------


def test_quarter_equals_half_when_all_b_terms_are_zero():
    q, qm = G.rows_grid_points(rows_spec("lecleach_mod", n_phi=25), mod_knobs(), BRIEF)
    # the PRESENCE of a zero b key is the half-model request
    h, hm = G.rows_grid_points(rows_spec("lecleach_mod", n_phi=25),
                               mod_knobs(g_stop_b1_deg=0.0), BRIEF)
    assert qm["row_span"] == "quarter" and qm["quadrants"] == "1"
    assert hm["row_span"] == "half" and hm["quadrants"] == "14"
    assert h.shape == (25, 33, 3) and q.shape == (25, 33, 3)
    # phi >= 0 is the SAME rows as the quarter grid (bit-for-bit).  The half samples
    # the [-90, +90] span every 7.5 deg; the 25-row quarter samples [0, 90] every
    # 3.75 deg, so half row 12+j (phi = 7.5j) matches quarter row 2j (same phi, same
    # march, same point).
    for j in range(13):
        assert np.abs(h[12 + j] - q[2 * j]).max() <= 1e-9


def test_half_model_needs_an_odd_n_phi():
    # the half-span helpers check the honest-resolution floor first ...
    with pytest.raises(registry.GeneratorError, match=r"n_phi >= 25"):
        G.rows_grid_points(rows_spec("lecleach_mod", n_phi=20),
                           mod_knobs(g_stop_b1_deg=0.0), BRIEF)
    # ... then the odd-count rule (the phi = 0 row and both +/-90 endpoints must exist)
    with pytest.raises(registry.GeneratorError, match="ODD n_phi"):
        G.rows_grid_points(rows_spec("lecleach_mod", n_phi=26),
                           mod_knobs(g_stop_b1_deg=0.0), BRIEF)


# ---------------------------------------------------------------------------
# TASK B4: torus lip width invariant + lib-2 datasheet cross-check
# ---------------------------------------------------------------------------


def test_tangent_torus_lip_adds_two_radii_to_the_total_width():
    base_knobs = {"g_fc_hz": 800.0, "g_T": 0.8, "g_stop_deg": 170.0}
    _g0, m0 = G.rows_grid_points(rows_spec("lecleach"), base_knobs, BRIEF)
    w0 = 2.0 * m0["mouth_radius_h_mm"]
    for r_lip in (10.0, 20.0, 30.0):
        _g, m = G.rows_grid_points(rows_spec("lecleach"),
                                   {**base_knobs, "g_r_lip_mm": r_lip}, BRIEF)
        w = 2.0 * m["mouth_radius_h_mm"]
        assert abs((w - w0) - 2.0 * r_lip) <= 1.0, (r_lip, w0, w)
        assert m["r_lip_mm"] == r_lip


def test_jmlc350_datasheet_torus_cross_check(capsys):
    """[datasheet cross-check, construction inputs inferred from lib-2 section 6; not a
    reproduction claim] T1 at fc 350 / T 0.8 / r0 25.4 + ~30 mm lip vs published 595."""
    x, y, _phi, meta = P.lecleach_exact(25.4, 350.0, 0.8, 5.0, 360.0, 1.0)
    base = 2.0 * float(np.max(y))
    total = base + 2.0 * 30.0
    assert abs(total - 596.0) <= 6.0, (base, total)
    with capsys.disabled():
        print(f"\n[torus datasheet cross-check] T1 width {base:.2f} mm + 2 x 30 mm = "
              f"{total:.2f} mm vs published 595 mm (|total - 596| = {abs(total - 596.0):.2f} <= 6)")


# ---------------------------------------------------------------------------
# TASK B5: the labeled depth fingerprint (NOT a reproduction claim)
# ---------------------------------------------------------------------------


def test_ar_narrow_axis_depth_fingerprint_is_deeper_proportioned(capsys):
    """lib-2 section 2.2: published 590 x 320 x 450 -> depth/width 0.76 vs a same-width
    T1 0.61.  Our AR stretch shares x (does not lengthen the horn), so the HORIZONTAL
    depth/width necessarily FALLS; the narrow-axis (vertical) depth/width rises by
    sqrt(AR_m) and is the quantity compared here.  [inferred]; not a reproduction claim.
    """
    plain, pm = G.rows_grid_points(
        rows_spec("lecleach"), {"g_fc_hz": 800.0, "g_T": 0.5, "g_stop_deg": 170.0}, BRIEF)
    ar, am = G.rows_grid_points(rows_spec("lecleach_ar"), ar_knobs(), BRIEF)
    plain_ratio = pm["L_mm"] / (2.0 * pm["mouth_radius_h_mm"])
    ar_minor_ratio = am["L_mm"] / (2.0 * am["mouth_radius_v_mm"])
    assert ar_minor_ratio > plain_ratio * 1.10, (plain_ratio, ar_minor_ratio)
    with capsys.disabled():
        print(f"\n[AR depth fingerprint, inferred] plain T1 depth/width {plain_ratio:.3f} "
              f"(lib-2 quotes 0.61 at its matched 2-inch case), AR narrow-axis "
              f"depth/width {ar_minor_ratio:.3f} (published-family reference 0.76); "
              f"+{100 * (ar_minor_ratio / plain_ratio - 1):.1f}% > 10%")


# ---------------------------------------------------------------------------
# recipe / params JSON contract
# ---------------------------------------------------------------------------


def test_mod_and_ar_recipe_contracts_round_trip():
    for spec, knobs, kind in (
            (rows_spec("lecleach_mod", n_phi=25),
             mod_knobs(g_stop_a2_deg=-30.0, g_stop_b1_deg=10.0, g_bend_b1_mm=0.0),
             "lecleach_mod"),
            (rows_spec("lecleach_ar"), ar_knobs(), "lecleach_ar")):
        params = G.design_params(spec, knobs, BRIEF)
        block = params["grid"]
        # span is PERSISTED ONLY FOR A HALF MODEL (the lecleach_mod entry carries a b1
        # term, so its block gains "span": "half"; the lecleach_ar quarter stays bare).
        expected_keys = set(G.ROWS_BLOCK_KEYS) | (
            {"span"} if kind == "lecleach_mod" else set())
        assert set(block) == expected_keys, (kind, sorted(block))
        if kind == "lecleach_mod":
            assert block["span"] == "half"
        assert block["rows"] == {"type": kind}
        assert "L_mm" not in block and "L_mm" not in block["knobs"]
        json.dumps(params)
        families.validate(Design("FREEFORM", params))
        G.validate_grid_params(block)
    # the half flag survives the recipe as the PRESENCE of the b key
    block = G.design_params(rows_spec("lecleach_mod", n_phi=25),
                            mod_knobs(g_stop_b1_deg=10.0), BRIEF)["grid"]
    assert "g_stop_b1_deg" in block["knobs"]


def test_lecleach_mod_knob_refusals():
    for bad, match in (
            ({"g_stop_a2_deg": 1.0, "g_bogus": 1.0}, "unknown knob"),
            ({"g_stop0_deg": 80.0}, "stop0_deg"),
            ({"g_AR_m": 2.0}, "unknown knob"),
            ({"g_bend_b1_mm": 200.0}, "bend_b1_mm"),
    ):
        with pytest.raises(registry.GeneratorError, match=match):
            G.rows_grid_points(rows_spec("lecleach_mod"), mod_knobs(**bad), BRIEF)


def test_lecleach_ar_knob_refusals():
    for bad, match in (
            ({"g_AR_m": 0.0}, "AR_m"),
            ({"g_p": 0.0}, " p must be"),
            ({"g_fc_v_hz": 900.0}, "foreign knob"),
            ({"g_stop_deg": 250.0}, "stop_deg"),
    ):
        with pytest.raises(registry.GeneratorError, match=match):
            G.rows_grid_points(rows_spec("lecleach_ar"), ar_knobs(**bad), BRIEF)


# ---------------------------------------------------------------------------
# configs + catalog
# ---------------------------------------------------------------------------


def test_example_configs_materialize_and_are_catalogued():
    for name in ("salmon_saddle", "lecleach_iwata_ar", "lecleach_toroidal"):
        cfg = load_config(TYP / f"{name}.yaml")
        space = DesignSpace.from_config(cfg)
        assert isinstance(space, GeneratedSpace)
        families.validate(space.seed)
        json.dumps(space.seed.params)
        json.dumps(space.provenance(space.seed))
        assert registry.envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0
    assert not (TYP / "lecleach.yaml").exists()       # the stale gated stub is removed
    assert "3.866 mm on 6 of 33 rings" in (TYP / "salmon_saddle.yaml").read_text(
        encoding="utf-8")          # the benign mesher warning is recorded in the config header


def test_catalog_entries_symmetry_and_brief_compatibility():
    catalog = {e["name"]: e for e in load_catalog(EXAMPLES / "catalog.yaml")}
    expected = {
        "salmon_saddle": "hv",
        "lecleach_iwata_ar": "hv",
        "lecleach_toroidal": "axisymmetric",
    }
    for name, symmetry in expected.items():
        entry = catalog[name]
        assert entry["group"] == "organic"
        assert entry["symmetry"] == symmetry
        assert (EXAMPLES / entry["config"]).is_file()
    organic = load_brief(BRIEFS / "organic_rollback_1in.yaml")
    axi = load_brief(BRIEFS / "axi_90x90_1in.yaml")
    # the WP10 grid entries' honesty (ora-2 SHOULD): zero-modulation ellipse IS axisymmetric,
    # the G8/G9-modulated section is NOT phi-independent -> hv
    assert catalog["grid_ellipse"]["symmetry"] == "axisymmetric"
    assert catalog["grid_ellipse_mod"]["symmetry"] == "hv"
    # organic is 90x60 (H != V): the hv entries are eligible, the axisymmetric torus is not
    for name in ("salmon_saddle", "lecleach_iwata_ar"):
        ok, why = is_compatible(catalog[name], organic)
        assert ok and why == "", (name, why)
    ok, why = is_compatible(catalog["lecleach_toroidal"], organic)
    assert not ok and "coverage_h" in why
    ok, why = is_compatible(catalog["lecleach_toroidal"], axi)
    assert ok and why == ""
    # 2026-10-25 POLICY CHANGE (owner-approved; the 7040 campaign finding): an axisymmetric
    # brief now REFUSES non-axisymmetric entries. The old pin ("hv is also eligible there")
    # allowed asymmetric families under a symmetric brief, which returned asymmetric bests
    # (458x240 mm mouths) that never matched the brief's own symmetric intent.
    for name in ("salmon_saddle", "lecleach_iwata_ar"):
        ok, why = is_compatible(catalog[name], axi)
        assert not ok and "axisymmetric" in why, (name, why)
