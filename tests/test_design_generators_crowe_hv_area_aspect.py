"""CROWE-inspired V2A forward area/aspect family (schema crowe-hv-area-aspect-v1).

Offline geometry tests. They check the V2A four-variable contract, exact identities, the timing
law, deterministic replay, config/search-box admission, the T2 identifiability rank and
(mesher-gated) a real quarter mesh.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from conftest import EXAMPLES, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design import families
from hornlab_search.design.generated import GeneratedSpace
from hornlab_search.design.generators import crowe_hv_area_aspect_v1 as family
from hornlab_search.design.generators import registry
from hornlab_search.design.space import Bound, DesignSpace
from hornlab_search.types import Design

ROOT = Path(__file__).resolve().parents[1]
TYP = EXAMPLES / "typologies" / "crowe_hv_area_aspect_2026-11-16" / "configs"
C0 = TYP / "c0_four_dof_seed.yaml"
C1 = TYP / "c1_four_dof_bounds.yaml"
C2 = TYP / "c2_round20_ab.yaml"
C3 = TYP / "c3_p22_ab.yaml"

GEN = {"name": family.KIND, "n_anchors": 29, "wall_thickness_mm": 3.0,
       "width_h_active_mm": 580.0, "p_mouth": 3.25, "throat_round_hold_mm": 0.0}
KNOBS = {"height_v_active_mm": 474.0, "L_forward_mm": 300.0,
         "area_mid_bias": 0.0, "aspect_timing_u50": 0.5}
BRIEF = {
    "driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0},
    "envelope": {"max_mouth_w_mm": 600.0, "max_mouth_h_mm": 480.0, "max_depth_mm": 480.0},
}
BOUNDS = {"height_v_active_mm": Bound(300.0, 474.0), "L_forward_mm": Bound(220.0, 340.0),
          "area_mid_bias": Bound(-0.15, 0.15), "aspect_timing_u50": Bound(0.35, 0.65)}


def _law(u, **knobs):
    return family.evaluate(family._shape(GEN, {**KNOBS, **knobs}), BRIEF,
                           np.asarray(u, dtype=float))


def _dense(**knobs):
    return _law(np.linspace(0.0, 1.0, 501), **knobs)


def test_throat_and_mouth_identities_are_exact():
    law = _law(np.array([0.0, 1.0]))
    r0 = BRIEF["driver"]["exit_radius_mm"]
    assert law["a_mm"][0] == pytest.approx(r0, abs=1e-12)
    assert law["b_mm"][0] == pytest.approx(r0, abs=1e-12)
    assert law["area_mm2"][0] == pytest.approx(np.pi * r0 * r0, rel=1e-12)
    assert law["aspect"][0] == pytest.approx(1.0, abs=1e-12)
    assert law["p"][0] == 2.0
    assert law["a_mm"][-1] == pytest.approx(GEN["width_h_active_mm"] / 2.0, abs=1e-9)
    assert law["b_mm"][-1] == pytest.approx(KNOBS["height_v_active_mm"] / 2.0, abs=1e-9)
    expected = family.flat_lame_area(GEN["width_h_active_mm"] / 2.0,
                                     KNOBS["height_v_active_mm"] / 2.0, GEN["p_mouth"])
    assert law["area_mm2"][-1] == pytest.approx(expected, rel=1e-12)
    assert law["aspect"][-1] == pytest.approx(
        GEN["width_h_active_mm"] / KNOBS["height_v_active_mm"], rel=1e-12)
    assert law["p"][-1] == pytest.approx(GEN["p_mouth"], abs=1e-12)


def test_every_station_has_area_C_times_a_times_b_and_aspect_a_over_b():
    law = _dense()
    c = np.array([family.flat_lame_area(1.0, 1.0, float(p)) for p in law["p"]])
    assert np.allclose(law["area_mm2"], c * law["a_mm"] * law["b_mm"], rtol=1e-13, atol=0.0)
    assert np.allclose(law["aspect"], law["a_mm"] / law["b_mm"], rtol=1e-13, atol=0.0)


def test_source_tangent_and_smooth_onset():
    law = _dense()
    slope_h = np.gradient(law["a_mm"], law["z_mm"], edge_order=2)[0]
    slope_v = np.gradient(law["b_mm"], law["z_mm"], edge_order=2)[0]
    expected = np.tan(np.radians(BRIEF["driver"]["exit_angle_deg"]))
    assert slope_h == pytest.approx(expected, rel=2e-4)
    assert slope_v == pytest.approx(expected, rel=2e-4)
    # Gate and its first two derivatives vanish at the source: the section starts round.
    assert law["aspect_gate"][0] == 0.0
    eps = 1e-4
    g0 = family._timing(np.array([0.0, eps, 2 * eps]), KNOBS["aspect_timing_u50"])
    assert g0[1] < 1e-9 and g0[2] < 1e-9
    early = _law(np.array([5.0, 10.0, 20.0]) / 300.0)
    assert np.all(np.abs(early["aspect"] - 1.0) < 1e-3)
    assert np.all(np.abs(early["p"] - 2.0) < 5e-3)


def test_aspect_timing_u50_is_the_half_development_point():
    for u50 in (0.35, 0.5, 0.65):
        law = _law(np.array([u50]), aspect_timing_u50=u50)
        assert law["aspect_gate"][0] == pytest.approx(0.5, abs=1e-9)
        assert law["aspect"][0] == pytest.approx(
            (GEN["width_h_active_mm"] / KNOBS["height_v_active_mm"]) ** 0.5, rel=1e-9)
        assert law["p"][0] == pytest.approx(2.0 + 0.5 * (GEN["p_mouth"] - 2.0), abs=1e-9)


def test_timing_law_has_zero_endpoint_first_and_second_derivatives():
    ends = np.array([0.0, 1.0])
    for u50 in (0.35, 0.50, 0.65):
        s, ds, d2s = family.timing_derivatives(ends, u50)
        assert s[0] == 0.0 and s[1] == 1.0
        assert abs(ds[0]) < 1e-12 and abs(ds[1]) < 1e-12
        assert abs(d2s[0]) < 1e-12 and abs(d2s[1]) < 1e-12
        assert family._timing(np.array([u50]), u50)[0] == pytest.approx(0.5, abs=1e-12)
        grid = family._timing(np.linspace(0.0, 1.0, 1001), u50)
        assert np.all(np.diff(grid) > 0.0)
    # fixed 20 mm hold: the shifted raw law keeps zero end derivatives, and the held physical
    # half point is still the configured u50.
    hold_u = 20.0 / 300.0
    raw = (0.5 - hold_u) / (1.0 - hold_u)
    s, ds, d2s = family.timing_derivatives(ends, raw)
    assert abs(ds[0]) < 1e-12 and abs(ds[1]) < 1e-12
    assert abs(d2s[0]) < 1e-12 and abs(d2s[1]) < 1e-12
    assert family._aspect_gate(np.array([0.5]), 0.5, hold_u)[0] == pytest.approx(0.5, abs=1e-12)


def test_owner_review_section_cuts_show_round_start_and_late_boxiness():
    rows = family.section_cuts(GEN, KNOBS, BRIEF)
    assert [row["z_mm"] for row in rows] == [0.0, 5.0, 10.0, 20.0, 40.0, 60.0, 100.0]
    for row in rows[:4]:
        assert row["aspect"] == pytest.approx(1.0, abs=1e-3)
        assert row["p"] == pytest.approx(2.0, abs=5e-3)
        assert row["wall_h_deg"] == pytest.approx(row["wall_v_deg"], abs=0.1)
        assert row["inside_round_hold"] is (row["z_mm"] == 0.0)
    ratios = [row["area_ratio_to_throat"] for row in rows]
    assert ratios == sorted(ratios) and ratios[0] == 1.0
    assert rows[3]["area_ratio_to_throat"] > 1.09
    assert rows[6]["p"] > 2.2
    print("\nsection cuts:", json.dumps(rows, sort_keys=True))


def test_area_mid_bias_is_local_and_mouth_exact():
    u = np.array([0.0, 0.5, 1.0])
    base = _law(u)
    biased = _law(u, area_mid_bias=0.15)
    assert biased["area_mm2"][1] > base["area_mm2"][1] * 1.10
    assert biased["area_mm2"][0] == pytest.approx(base["area_mm2"][0], abs=1e-12)
    assert biased["area_mm2"][2] == pytest.approx(base["area_mm2"][2], abs=1e-9)
    assert biased["aspect"][1] == pytest.approx(base["aspect"][1], rel=1e-12)
    assert family.materialize(GEN, {**KNOBS, "area_mid_bias": 0.15}, BRIEF) != \
        family.materialize(GEN, KNOBS, BRIEF)


def test_fixed_round_hold_is_circular_and_c2_at_its_boundary():
    hold_gen = {**GEN, "throat_round_hold_mm": 20.0}
    shape = family._shape(hold_gen, KNOBS)
    law = family.evaluate(shape, BRIEF, np.array([0.0, 10.0, 20.0, 40.0]) / KNOBS["L_forward_mm"])
    assert np.all(law["aspect"][:3] == 1.0)
    assert np.all(law["p"][:3] == 2.0)
    assert law["aspect_gate"][2] == 0.0
    assert law["aspect_gate"][3] > 0.0
    # zero first/second shape derivative at the hold boundary
    eps = 1e-4
    g = family.evaluate(shape, BRIEF, (20.0 + np.array([eps, 2 * eps])) / KNOBS["L_forward_mm"])
    assert g["aspect_gate"][0] < 1e-8
    with pytest.raises(family.GeneratorError, match="beyond the fixed throat hold"):
        family._shape({**GEN, "throat_round_hold_mm": 90.0},
                      {**KNOBS, "aspect_timing_u50": 0.2})
    params = family.materialize(hold_gen, KNOBS, BRIEF)
    assert len(params["crossSections"]) <= 32


def test_extreme_box_combinations_and_random_samples_stay_lawful():
    keys = sorted(family.PARAM_KEYS)
    for bits in range(16):
        knobs = {}
        for i, key in enumerate(keys):
            bound = BOUNDS[key]
            knobs[key] = bound.hi if (bits >> i) & 1 else bound.lo
        family.materialize(GEN, knobs, BRIEF)
    rng = np.random.default_rng(1234)
    for _ in range(100):
        knobs = {key: BOUNDS[key].lo + (BOUNDS[key].hi - BOUNDS[key].lo) * rng.random()
                 for key in keys}
        family.materialize(GEN, knobs, BRIEF)


def test_replay_is_deterministic_and_the_digest_is_stable():
    assert family.materialize(GEN, KNOBS, BRIEF) == family.materialize(GEN, KNOBS, BRIEF)
    assert family.implementation_digest() == family.implementation_digest()


def test_cold_subprocess_recreates_the_same_recipe():
    script = (
        "import json\n"
        "from hornlab_search.design.generators import crowe_hv_area_aspect_v1 as m\n"
        f"gen={GEN!r}\nknobs={KNOBS!r}\nbrief={BRIEF!r}\n"
        "print(json.dumps(m.materialize(gen,knobs,brief),sort_keys=True))\n")
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True,
                            text=True, check=True)
    assert json.loads(result.stdout) == json.loads(
        json.dumps(family.materialize(GEN, KNOBS, BRIEF), sort_keys=True))


def test_m0_outside_the_monotone_domain_is_refused():
    steep = {"driver": {"exit_radius_mm": 12.0, "exit_angle_deg": 15.0}}
    with pytest.raises(family.GeneratorError, match="no monotone area law"):
        family.evaluate(family._shape(GEN, {**KNOBS, "L_forward_mm": 480.0}), steep, [0.5])


def test_four_variable_contract_is_enforced():
    with pytest.raises(family.GeneratorError, match="exactly four search dimensions"):
        family.validate_search_config(GEN, KNOBS, {**BOUNDS, "p_mouth": Bound(3.0, 3.5)}, BRIEF)
    with pytest.raises(family.GeneratorError, match="unknown generator key"):
        family._shape({**GEN, "height_v_active_mm": 400.0}, KNOBS)
    with pytest.raises(family.GeneratorError, match="knob mismatch"):
        family._shape(GEN, {**KNOBS, "round_throat_mm": 20.0})
    with pytest.raises(family.GeneratorError, match="fixed bound must have lo == hi"):
        family.validate_search_config(
            GEN, KNOBS, {**BOUNDS, "L_forward_mm": Bound(220.0, 340.0, search=False)}, BRIEF)


def test_configs_load_validate_and_estimate_the_envelope():
    configs = [load_config(path) for path in (C0, C1, C2, C3)]
    spaces = [DesignSpace.from_config(cfg) for cfg in configs]
    assert all(isinstance(space, GeneratedSpace) for space in spaces)
    for space in spaces:
        families.validate(space.seed)
    assert spaces[0].seed.hash() == spaces[1].seed.hash()      # same seed geometry
    assert spaces[0].seed.hash() != spaces[2].seed.hash()      # fixed hold differs
    assert spaces[0].seed.hash() != spaces[3].seed.hash()      # p_mouth differs
    json.dumps(spaces[0].provenance(spaces[0].seed))
    assert registry.envelope_overshoot_estimate(spaces[0].seed.params, configs[0].brief) == 0.0
    assert configs[0].generator["name"] == family.KIND
    assert set(configs[1].bounds_raw) == family.PARAM_KEYS


def test_t2_identifiability_rank_is_four_at_three_parents():
    parents = [
        dict(KNOBS),
        {"height_v_active_mm": 360.0, "L_forward_mm": 260.0,
         "area_mid_bias": 0.08, "aspect_timing_u50": 0.4},
        {"height_v_active_mm": 420.0, "L_forward_mm": 330.0,
         "area_mid_bias": -0.08, "aspect_timing_u50": 0.6},
    ]
    for knobs in parents:
        report = family.identifiability_report(GEN, knobs, BOUNDS, BRIEF)
        assert report["effective_rank"] == 4
        assert report["practical_rank"] == 4
        assert report["weak_keys"] == []
        assert report["max_pairwise_abs_cosine"] < 0.9
        print("\nT2:", json.dumps(report, sort_keys=True))


@pytest.mark.parametrize("seed", [1234, 5678])
def test_random_search_box_samples_are_lawful(seed):
    cfg = load_config(C1)
    keys = sorted(family.PARAM_KEYS)
    lo = np.array([cfg.bounds_raw[k]["lo"] for k in keys], dtype=float)
    hi = np.array([cfg.bounds_raw[k]["hi"] for k in keys], dtype=float)
    rng = np.random.default_rng(seed)
    valid = 0
    for _ in range(100):
        knobs = dict(zip(keys, lo + (hi - lo) * rng.random(len(keys))))
        try:
            family.materialize(cfg.generator, knobs, cfg.brief)
            valid += 1
        except family.GeneratorError:
            pass
    assert valid >= 90


@requires_mesher
def test_real_quarter_mesh_is_closed_and_round_at_the_driver(tmp_path):
    from hornlab_search.mesh import build, sizing, topology, throat_check
    cfg = load_config(C0)
    space = DesignSpace.from_config(cfg)
    result = build.build_mesh(space.seed, mesh_spec("screen", cfg), cfg,
                              tmp_path / "mesh", mode="screen")
    assert result.n_triangles > 1000
    summary, xyz, tri = build.read_msh_summary(Path(result.path), return_arrays=True)
    assert summary["tags"].get(build.SOURCE_TAG, 0) > 0
    report = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["1"])
    assert report.bad_open_edges == 0 and report.nonmanifold_edges == 0
    shape = throat_check.throat_shape(Path(result.path))
    fits, reason = throat_check.fits_exit(shape, 36.0)
    assert fits is True, reason
    assert shape["roundness"] == pytest.approx(1.0, abs=1e-2)
    print(f"\nmesh: {result.n_triangles} tris, tags={summary['tags']}, "
          f"throat={shape['width_mm']:.3f}x{shape['height_mm']:.3f} mm")
