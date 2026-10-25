"""Le Cleac'h (JMLC): Fourcade 2015 exact construction — R9-J gate + wiring. Offline.

SOURCE OF TRUTH: ``docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md``
(fetched Fourcade PDF; section 2.3 canonical reference case; section 3 R9-J gate).

The gate is ``test_r9j_fourcade_fig7_validation_table``: the published fig. 7 / p.13
case is fc 400 Hz, T 0.8, throat DIAMETER 25.4 mm, exit 8.0 deg INCLUDED (= phi0 4.0
half-angle), dl 1.0 mm, c 344 m/s, stop 360 deg.  Measured here: width 467.30 mm
(published 467.30, 0.5 mm bar), 2 phi1 = 8.552 deg (8.55, 0.1 deg bar), L0
394/467/496/512 (394/467/496/511, <= 1 mm), S(L0) 0.1301/0.3779/0.5773/0.7294 m^2
(0.13/0.38/0.57/0.72, +/-2 %), overall length 321.79 (321.35, <= 1 mm).

Also covers: the half-angle convention (no double halving), knob determinism, the
FREEFORM wrapper (Hermite fidelity + exact segment-angle geometry + refusals above
88 deg), ``spherical_wave`` as the working T=1 case, the ``lecleach`` GRID rows
(axisymmetric rollback), and both example configs / catalog entries.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from conftest import EXAMPLES
from hornlab_search.config import load_config
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
FIDELITY_TOL_MM = 0.2
FREEFORM_N_ANCHORS = 48

# Published fig. 7 / p.13 (L0 mm, S(L0) m^2); stop 360 also carries the width/length/angle.
PUBLISHED = {90: (394.0, 0.13), 180: (467.0, 0.38), 270: (496.0, 0.57), 360: (511.0, 0.72)}
PUBLISHED_WIDTH_MM = 467.30
PUBLISHED_LENGTH_MM = 321.35
PUBLISHED_THROAT_INCLUDED_DEG = 8.55
REF_C = 344.0          # the published case's own speed of sound (NOT the repo default 343)


# ---------------------------------------------------------------------------
# R9-J GATE
# ---------------------------------------------------------------------------

def test_r9j_fourcade_fig7_validation_table(capsys):
    """R9-J: reproduce Fourcade fig. 7 (the gate that makes ``lecleach`` live).

    Tolerances are the task's R9-J bar: width <= 0.5 mm, included throat angle
    <= 0.1 deg, L0 <= 1 mm (the doc's regression guard; the looser +/-2 mm wording
    also passes), S(L0) +/-2 %, overall length <= 1 mm.
    """
    rows = []
    for stop, (pub_l0, pub_s) in PUBLISHED.items():
        x, y, phi, meta = P.lecleach_exact(R0, 400.0, 0.8, 4.0, float(stop),
                                           1.0, c=REF_C)
        rows.append((stop, x, y, phi, meta))
        assert meta["L0_mm"] == pytest.approx(pub_l0, abs=1.0), (
            f"stop {stop}: L0 {meta['L0_mm']:.2f} vs published {pub_l0}")
        assert abs(meta["S_L0_m2"] - pub_s) <= 0.02 * pub_s, (
            f"stop {stop}: S(L0) {meta['S_L0_m2']:.4f} vs published {pub_s}")
        assert meta["phi1_included_deg"] == pytest.approx(
            PUBLISHED_THROAT_INCLUDED_DEG, abs=0.1)
    _stop, x, y, phi, meta = rows[-1]                    # stop 360 = the full fig. 7 horn
    assert meta["width_mm"] == pytest.approx(PUBLISHED_WIDTH_MM, abs=0.5), (
        f"mouth width {meta['width_mm']:.2f} vs published {PUBLISHED_WIDTH_MM}")
    assert meta["max_x_mm"] == pytest.approx(PUBLISHED_LENGTH_MM, abs=1.0), (
        f"overall length {meta['max_x_mm']:.2f} vs published {PUBLISHED_LENGTH_MM}")

    with capsys.disabled():
        print("\n=== R9-J (Fourcade fig. 7; phi0 4.0 half-angle, c 344) ===")
        for stop, _x, _y, _phi, m in rows:
            pub_l0, pub_s = PUBLISHED[stop]
            print(f"  stop {stop:3d}: L0 {m['L0_mm']:6.1f} mm (pub {pub_l0:3.0f})  "
                  f"S {m['S_L0_m2']:.4f} m2 (pub {pub_s:.2f})")
        print(f"  width {meta['width_mm']:.2f} mm (pub {PUBLISHED_WIDTH_MM:.2f})  "
              f"length {meta['max_x_mm']:.2f} mm (pub {PUBLISHED_LENGTH_MM:.2f})  "
              f"2*phi1 {meta['phi1_included_deg']:.3f} deg (pub {PUBLISHED_THROAT_INCLUDED_DEG:.2f})")


# ---------------------------------------------------------------------------
# Half-angle convention (lib-1 C1)
# ---------------------------------------------------------------------------

def test_phi0_is_a_half_angle_and_is_not_halved_twice():
    _x, _y, _p, m4 = P.lecleach_exact(R0, 400.0, 0.8, 4.0, 90.0, 1.0, c=REF_C)
    assert m4["phi0_included_deg"] == pytest.approx(8.0)      # published 8.0 INCLUDED
    assert m4["phi1_included_deg"] == pytest.approx(PUBLISHED_THROAT_INCLUDED_DEG, abs=0.1)
    # Passing the published INCLUDED 8.0 as phi0 would be a HALF-angle of 8: the march
    # then reports ~17 deg included (fc 800/T 0.8; fc 400/phi0 8 is a non-positive bracket).
    _x, _y, _p, m8 = P.lecleach_exact(R0, 800.0, 0.8, 8.0, 90.0, 1.0, c=REF_C)
    assert m8["phi0_included_deg"] == pytest.approx(16.0)
    assert m8["phi1_included_deg"] > 16.0
    # The registry passes the brief's driver exit angle through unchanged (WP2 precedent).
    m = registry.build_meridian(
        {"type": "lecleach"},
        {"L_mm": 220.0, "h_fc_hz": 800.0, "h_T": 0.8, "h_stop_deg": 80.0},
        "h", r0=R0, a0=A0, L=220.0, max_wall=89.9, phi=0.0)
    assert m.theta_deg[0] == pytest.approx(A0)                 # not A0 / 2
    assert m.info["phi0_deg"] == pytest.approx(A0)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_knob_determinism():
    a = P.lecleach_exact(R0, 800.0, 0.8, A0, 88.0, 1.0, c=P.C_AIR)
    b = P.lecleach_exact(R0, 800.0, 0.8, A0, 88.0, 1.0, c=P.C_AIR)
    np.testing.assert_array_equal(a[0], b[0])
    np.testing.assert_array_equal(a[1], b[1])
    np.testing.assert_array_equal(a[2], b[2])
    assert a[3] == b[3]


# ---------------------------------------------------------------------------
# FREEFORM wrapper: fidelity, exact segment geometry, refusals
# ---------------------------------------------------------------------------

def test_freeform_wrapper_is_x_monotone_and_geometrically_consistent():
    m = P.lecleach(R0, 800.0, 0.8, 80.0, phi0_deg=A0)
    assert m.name == "lecleach"
    assert m.z_mm[0] == pytest.approx(0.0) and m.r_mm[0] == pytest.approx(R0)
    assert m.theta_deg[0] == pytest.approx(A0)
    assert np.all(np.diff(m.z_mm) > 0.0)
    assert np.all(m.r_mm > 0.0)
    assert np.all(np.diff(m.theta_deg) > 0.0)              # the march's dalpha > 0
    assert np.all(np.abs(m.theta_deg) < 90.0)
    # C1/geometry consistency: every segment is at the arrival station's wall angle
    # (x_{i+1}-x_i = dl cos phi_{i+1}, y_{i+1}-y_i = dl sin phi_{i+1}).
    seg = np.degrees(np.arctan2(np.diff(m.r_mm), np.diff(m.z_mm)))
    np.testing.assert_allclose(seg, m.theta_deg[1:], rtol=0.0, atol=1e-9)


@pytest.mark.parametrize("fc,T,stop", [
    (800.0, 0.8, 80.0),      # the example seed
    (600.0, 0.8, 88.0),
    (800.0, 1.0, 88.0),
    (1000.0, 0.8, 88.0),
    (1200.0, 1.0, 88.0),
])
def test_freeform_hermite_fidelity_through_the_config_anchor_count(fc, T, stop):
    m = registry.build_meridian(
        {"type": "lecleach"},
        {"L_mm": 220.0, "h_fc_hz": fc, "h_T": T, "h_stop_deg": stop},
        "h", r0=R0, a0=A0, L=220.0, max_wall=89.9, phi=0.0)
    anc = P.select_anchors(m, FREEFORM_N_ANCHORS)
    r_ref = P.hermite_reference(anc, m.z_mm)
    assert np.abs(r_ref - m.r_mm).max() <= FIDELITY_TOL_MM


def test_wrapper_refuses_frames_that_need_the_rows_route():
    with pytest.raises(registry.GeneratorError, match="GRID rows route"):
        P.lecleach(R0, 800.0, 0.8, 89.0, phi0_deg=A0)
    with pytest.raises(registry.GeneratorError, match="phi0_deg"):
        P.lecleach(R0, 800.0, 0.8)                          # phi0 missing
    with pytest.raises(registry.GeneratorError, match="phi0_deg"):
        P.lecleach(R0, 800.0, 0.8, 80.0, phi0_deg=80.0)


@pytest.mark.parametrize("kwargs, match", [
    ({"phi0_deg": 0.0, "stop_deg": 90.0}, "phi0_deg"),
    ({"phi0_deg": 4.0, "stop_deg": 361.0}, "stop_deg"),
    ({"phi0_deg": 4.0, "stop_deg": 90.0, "T": -1.0}, "T must be"),
    ({"phi0_deg": 4.0, "stop_deg": 90.0, "fc_hz": 0.0}, "fc_hz"),
    ({"phi0_deg": 4.0, "stop_deg": 90.0, "dl_mm": 0.0}, "dl_mm"),
    ({"phi0_deg": 4.0, "stop_deg": 90.0, "r0_mm": 0.0}, "r0_mm"),
])
def test_lecleach_exact_refusals(kwargs, match):
    args = {"r0_mm": R0, "fc_hz": 800.0, "T": 0.8, "stop_deg": 90.0, **kwargs}
    with pytest.raises(registry.GeneratorError, match=match):
        P.lecleach_exact(args.pop("r0_mm"), args.pop("fc_hz"), args.pop("T"),
                         args.pop("phi0_deg"), args.pop("stop_deg"),
                         args.pop("dl_mm", 1.0), c=P.C_AIR)


def test_non_positive_sii_is_refused_not_clamped():
    # fc 400 / phi0 5 deg gives S_ii < 0 at the first ring (a genuinely empty bracket).
    with pytest.raises(registry.GeneratorError, match="S_ii"):
        P.lecleach_exact(R0, 400.0, 0.8, 5.0, 90.0, 1.0, c=P.C_AIR)


def test_spherical_wave_is_the_working_t1_lecleach():
    sw = P.spherical_wave(R0, 800.0, 80.0, phi0_deg=A0)
    lc = P.lecleach(R0, 800.0, 1.0, 80.0, phi0_deg=A0)
    assert sw.name == lc.name == "lecleach"
    np.testing.assert_array_equal(sw.z_mm, lc.z_mm)
    np.testing.assert_array_equal(sw.r_mm, lc.r_mm)
    assert sw.info["T"] == 1.0


# ---------------------------------------------------------------------------
# GRID rows: verified rollback (axisymmetric)
# ---------------------------------------------------------------------------

ROWS_SPEC = {"name": "grid", "rows": {"type": "lecleach"}, "n_phi": 15, "n_s": 32,
             "wall_thickness_mm": 3.0}
ROWS_KNOBS = {"g_fc_hz": 800.0, "g_T": 0.8, "g_stop_deg": 185.0}
ROWS_BRIEF = {
    "driver": {"exit_radius_mm": R0, "exit_angle_deg": A0},
    "envelope": {"max_mouth_w_mm": 360.0, "max_mouth_h_mm": 360.0, "max_depth_mm": 220.0},
}


def test_rows_axisym_lecleach_grid_rolls_back():
    grid, meta = G.rows_grid_points(ROWS_SPEC, ROWS_KNOBS, ROWS_BRIEF)
    assert grid.shape == (15, 33, 3)
    assert meta["rows_type"] == "lecleach"
    assert "Fourcade 2015" in meta["construction_label"]
    assert "hypothesis_label" not in meta               # a verified construction, not a hypothesis
    assert meta["min_self_approach_mm"] >= 2.0 * 3.0 + G.SELF_APPROACH_MARGIN_MM
    assert meta["phi1_included_deg"] == pytest.approx(
        2.0 * P.lecleach_exact(R0, 800.0, 0.8, A0, 185.0, 1.0)[3]["phi1_deg"])
    # axisymmetric: every row is the same (x, y) profile at its own azimuth
    for i in range(1, grid.shape[0]):
        np.testing.assert_allclose(
            np.hypot(grid[i, :, 0], grid[i, :, 1]),
            np.hypot(grid[0, :, 0], grid[0, :, 1]), rtol=0.0, atol=1e-9)
        np.testing.assert_allclose(grid[i, :, 2], grid[0, :, 2], rtol=0.0, atol=1e-9)
    # rollback: x is non-monotone on every row (x_max is before the lip)
    assert all(m["x_max_mm"] > m["mouth_x_mm"] + 1e-6 for m in meta["rows"])
    # exact mirror planes for the quarter model
    assert np.all(grid[0, :, 1] == 0.0) and np.all(grid[-1, :, 0] == 0.0)


def test_rows_params_are_json_and_validated():
    params = G.design_params(ROWS_SPEC, ROWS_KNOBS, ROWS_BRIEF)
    block = params["grid"]
    assert set(block) == set(G.ROWS_BLOCK_KEYS)
    assert block["rows"] == {"type": "lecleach"}
    assert block["knobs"] == ROWS_KNOBS              # no zero-default canonicalisation here
    assert "L_mm" not in block and "L_mm" not in block["knobs"]
    json.dumps(params)
    families.validate(Design("FREEFORM", params))
    G.validate_grid_params(block)
    _grid, meta = G.rows_grid_points({k: v for k, v in block.items() if k != "knobs"},
                                     block["knobs"], ROWS_BRIEF)
    assert meta["construction_label"].startswith("Fourcade 2015")


def test_rows_envelope_extents_are_conservative():
    w, h, d = G.envelope_extents(ROWS_SPEC, ROWS_KNOBS, ROWS_BRIEF)
    grid, meta = G.rows_grid_points(ROWS_SPEC, ROWS_KNOBS, ROWS_BRIEF)
    assert w >= 2.0 * meta["mouth_radius_h_mm"]
    assert h >= 2.0 * meta["mouth_radius_v_mm"]
    assert d >= meta["x_span_mm"]
    assert w <= ROWS_BRIEF["envelope"]["max_mouth_w_mm"]
    assert h <= ROWS_BRIEF["envelope"]["max_mouth_h_mm"]
    assert d <= ROWS_BRIEF["envelope"]["max_depth_mm"]


@pytest.mark.parametrize("bad, match", [
    ({"g_stop_deg": 89.0}, "stop_deg"),
    ({"g_stop_deg": 241.0}, "stop_deg"),
    ({"g_fc_v_hz": 900.0}, "foreign knob"),
    ({"g_x_amp": 0.2}, "foreign knob"),
    ({"g_fc_hz": 0.0}, "fc_hz"),
    ({"g_T": -1.0}, "T must be"),
])
def test_rows_knob_refusals(bad, match):
    with pytest.raises(registry.GeneratorError, match=match):
        G.rows_per_azimuth(ROWS_SPEC, {**ROWS_KNOBS, **bad}, ROWS_BRIEF)


@pytest.mark.parametrize("bad, match", [
    ({"profile_h": {"type": "lecleach"}}, "foreign key"),
    ({"max_wall_deg": 80.0}, "foreign key"),
])
def test_rows_spec_refuses_freeform_only_keys(bad, match):
    with pytest.raises(registry.GeneratorError, match=match):
        G.rows_per_azimuth({**ROWS_SPEC, **bad}, ROWS_KNOBS, ROWS_BRIEF)


def test_rows_stop_below_180_builds_too():
    grid, meta = G.rows_grid_points(ROWS_SPEC, {**ROWS_KNOBS, "g_stop_deg": 140.0}, ROWS_BRIEF)
    assert grid.shape == (15, 33, 3)
    assert meta["stop_deg"] == pytest.approx(140.0)


def test_rows_stop_180_is_legal_for_fourcade():
    # The Salmon march refuses 180 (cap-area asymptote); Fourcade's construction does not.
    grid, meta = G.rows_grid_points(ROWS_SPEC, {**ROWS_KNOBS, "g_stop_deg": 180.0}, ROWS_BRIEF)
    assert grid.shape == (15, 33, 3)
    assert meta["stop_deg"] == pytest.approx(180.0)
    assert meta["min_self_approach_mm"] >= 2.0 * 3.0 + G.SELF_APPROACH_MARGIN_MM


# ---------------------------------------------------------------------------
# Example configs + catalog
# ---------------------------------------------------------------------------

def test_freeform_example_config_seed_and_provenance():
    cfg = load_config(TYP / "lecleach_f90.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace) and space.family == "FREEFORM"
    assert set(space.keys()) == {"h_fc_hz", "h_T", "h_stop_deg"}
    assert space.seed_knobs["L_mm"] == 220.0
    families.validate(space.seed)
    pH = space.seed.params["profileH"]["points"]
    assert pH[0][0] == 0.0 and pH[0][1] == pytest.approx(R0)
    assert space.seed.params["profileV"] == space.seed.params["profileH"]
    prov = space.provenance(space.seed)
    assert prov is not None
    assert prov["spec"]["profile_h"] == {"type": "lecleach"}
    assert prov["derived"]["h"]["type"] == "lecleach"
    assert prov["derived"]["h"]["phi0_deg"] == pytest.approx(A0)
    json.dumps(prov)
    json.dumps(space.seed.params)
    assert registry.envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0


def test_rollback_example_config_seed_and_provenance():
    cfg = load_config(TYP / "lecleach_rollback.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace) and space.family == "FREEFORM"
    assert set(space.keys()) == {"g_fc_hz", "g_T", "g_stop_deg"}
    block = space.seed.params["grid"]
    assert block["rows"] == {"type": "lecleach"}
    assert set(block["knobs"]) == {"g_fc_hz", "g_T", "g_stop_deg"}
    families.validate(space.seed)
    json.dumps(space.seed.params)
    json.dumps(space.provenance(space.seed))
    assert registry.envelope_overshoot_estimate(space.seed.params, cfg.brief) == 0.0


def test_catalog_entries_exist_and_are_compatible_with_the_axi_brief():
    catalog = load_catalog(EXAMPLES / "catalog.yaml")
    by_name = {e["name"]: e for e in catalog}
    assert "lecleach_f90" in by_name and "lecleach_rollback" in by_name
    assert by_name["lecleach_f90"]["group"] == "classical"
    assert by_name["lecleach_rollback"]["group"] == "organic"
    for name in ("lecleach_f90", "lecleach_rollback"):
        assert by_name[name]["symmetry"] == "axisymmetric"
        assert (EXAMPLES / by_name[name]["config"]).is_file()
    brief = load_config(TYP / "lecleach_f90.yaml").brief
    assert brief is not None
    for name in ("lecleach_f90", "lecleach_rollback"):
        ok, why = is_compatible(by_name[name], brief)
        assert ok and why == "", (name, why)
    # the stale "kept but not listed/disabled" note is gone
    text = (EXAMPLES / "catalog.yaml").read_text(encoding="utf-8")
    assert "lecleach stays blocked" not in text and "generator DISABLED" not in text
    assert "JMLC_LECLEACH_RESEARCH_2026-10-25.md" in text
