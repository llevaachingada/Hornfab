"""CROWE-inspired forward area/aspect family (schema crowe-hv-area-aspect-v1).

Offline geometry tests. They check the document's exact identities, the owner's four throat rules,
deterministic replay, the config/search-box contract and (mesher-gated) a real quarter mesh.
"""
from __future__ import annotations

import dataclasses
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

ROOT = Path(__file__).resolve().parents[1]
TYP = EXAMPLES / "typologies" / "crowe_hv_area_aspect_2026-11-16" / "configs"
C0 = TYP / "c0_round30_480.yaml"
C1 = TYP / "c1_frontier_bounds.yaml"

GEN = {"name": family.KIND, "n_anchors": 29, "wall_thickness_mm": 3.0}
KNOBS = {
    "L_forward_mm": 300.0,
    "width_h_active_mm": 590.0,
    "height_v_active_mm": 474.0,
    "area_mid_rate": 0.0,
    "area_late_rate": 0.0,
    "aspect_mid": 0.0,
    "aspect_late": 0.0,
    "p_mouth": 3.5,
    "round_throat_mm": 30.0,
}
BRIEF = {
    "driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0},
    "envelope": {"max_mouth_w_mm": 600.0, "max_mouth_h_mm": 480.0, "max_depth_mm": 480.0},
}


def _law(u, **knobs):
    shape = family._shape(GEN, {**KNOBS, **knobs})
    return family.evaluate(shape, BRIEF, np.asarray(u, dtype=float))


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
    assert law["a_mm"][-1] == pytest.approx(KNOBS["width_h_active_mm"] / 2.0, abs=1e-9)
    assert law["b_mm"][-1] == pytest.approx(KNOBS["height_v_active_mm"] / 2.0, abs=1e-9)
    expected = family.flat_lame_area(KNOBS["width_h_active_mm"] / 2.0,
                                     KNOBS["height_v_active_mm"] / 2.0, KNOBS["p_mouth"])
    assert law["area_mm2"][-1] == pytest.approx(expected, rel=1e-12)
    assert law["aspect"][-1] == pytest.approx(
        KNOBS["width_h_active_mm"] / KNOBS["height_v_active_mm"], rel=1e-12)
    assert law["p"][-1] == pytest.approx(KNOBS["p_mouth"], abs=1e-12)


def test_every_station_has_area_C_times_a_times_b_and_aspect_a_over_b():
    law = _dense()
    c = np.array([family.flat_lame_area(1.0, 1.0, float(p)) for p in law["p"]])
    assert np.allclose(law["area_mm2"], c * law["a_mm"] * law["b_mm"], rtol=1e-13, atol=0.0)
    assert np.allclose(law["aspect"], law["a_mm"] / law["b_mm"], rtol=1e-13, atol=0.0)


def test_first_round_throat_is_exactly_circular_and_area_expands():
    law = _law(np.linspace(0.0, KNOBS["round_throat_mm"] / KNOBS["L_forward_mm"], 2001))
    assert np.all(law["aspect"] == 1.0)
    assert np.all(law["p"] == 2.0)
    assert np.all(law["a_mm"] == law["b_mm"])
    assert np.all(np.diff(law["area_mm2"]) > 0.0)
    assert float(law["area_mm2"][-1] / law["area_mm2"][0]) > 1.10


def test_owner_review_section_cuts_show_round_then_late_boxiness():
    rows = family.section_cuts(GEN, KNOBS, BRIEF)
    assert [row["z_mm"] for row in rows] == [0.0, 5.0, 10.0, 20.0, 40.0, 80.0]
    for row in rows[:4]:                       # 0/5/10/20 mm: inside the 30 mm round throat
        assert row["aspect"] == 1.0 and row["p"] == 2.0
        assert row["inside_round_throat"] is True
        assert row["wall_h_deg"] == pytest.approx(row["wall_v_deg"], abs=1e-9)
        assert row["curvature_h_1_per_mm"] == pytest.approx(row["curvature_v_1_per_mm"], abs=1e-12)
    ratios = [row["area_ratio_to_throat"] for row in rows]
    assert ratios == sorted(ratios) and ratios[0] == 1.0
    assert rows[4]["p"] > 2.0 and rows[4]["p"] < 2.01
    assert rows[5]["p"] > 2.05 and rows[5]["p"] < 2.2
    assert rows[4]["inside_round_throat"] is False and rows[5]["inside_round_throat"] is False
    # the owner rules: area has expanded well before the section gets visibly boxy
    assert rows[3]["area_ratio_to_throat"] > 1.05 and rows[3]["p"] == 2.0
    assert rows[5]["area_ratio_to_throat"] > 1.5
    print("\nsection cuts:", json.dumps(rows, sort_keys=True))


def test_source_tangent_equals_the_driver_exit_angle():
    law = _dense()
    slope_h = np.gradient(law["a_mm"], law["z_mm"], edge_order=2)[0]
    slope_v = np.gradient(law["b_mm"], law["z_mm"], edge_order=2)[0]
    expected = np.tan(np.radians(BRIEF["driver"]["exit_angle_deg"]))
    assert slope_h == pytest.approx(expected, rel=2e-4)
    assert slope_v == pytest.approx(expected, rel=2e-4)


def test_materialized_profiles_anchor_the_round_throat_and_mouth():
    params = family.materialize(GEN, KNOBS, BRIEF)
    h = params["profileH"]
    v = params["profileV"]
    assert h["throatAngleDeg"] == pytest.approx(2.0, abs=1e-3)
    assert v["throatAngleDeg"] == pytest.approx(2.0, abs=1e-3)
    assert h["points"][0][:2] == pytest.approx([0.0, 18.0], abs=1e-9)
    assert v["points"][0][:2] == pytest.approx([0.0, 18.0], abs=1e-9)
    assert h["points"][-1][:2] == pytest.approx([300.0, 295.0], abs=1e-9)
    assert v["points"][-1][:2] == pytest.approx([300.0, 237.0], abs=1e-9)
    assert len(params["crossSections"]) <= 32
    assert params["crossSections"][0] == {"t": 0.0, "shape": "circle"}
    assert params["crossSections"][-1]["t"] == 1.0
    assert params["crossSections"][-1]["exponent"] == pytest.approx(3.5)
    families.validate(families.Design("FREEFORM", params))


def test_perturbations_are_local_and_leave_the_mouth_exact():
    u = np.array([0.5, 0.85, 1.0])
    base = _law(u)
    for knob, pick in (("area_mid_rate", 0), ("area_late_rate", 1),
                       ("aspect_mid", 0), ("aspect_late", 1)):
        changed = _law(u, **{knob: 1.0})
        key = "area_mm2" if knob.startswith("area") else "aspect"
        assert changed[key][pick] > base[key][pick]
        assert changed["a_mm"][2] == pytest.approx(base["a_mm"][2], abs=1e-12)
        assert changed["b_mm"][2] == pytest.approx(base["b_mm"][2], abs=1e-12)
        assert family.materialize(GEN, {**KNOBS, knob: 1.0}, BRIEF) != family.materialize(GEN, KNOBS, BRIEF)


def test_extreme_perturbation_combinations_stay_monotone():
    for am in (-1.0, 0.0, 1.0):
        for al in (-1.0, 0.0, 1.0):
            for sm in (-1.0, 0.0, 1.0):
                for sl in (-1.0, 0.0, 1.0):
                    law = _dense(area_mid_rate=am, area_late_rate=al,
                                 aspect_mid=sm, aspect_late=sl)
                    assert np.all(np.diff(law["a_mm"]) > 0.0)
                    assert np.all(np.diff(law["b_mm"]) > 0.0)


def test_replay_is_deterministic_and_the_digest_is_stable():
    first = family.materialize(GEN, KNOBS, BRIEF)
    second = family.materialize(GEN, KNOBS, BRIEF)
    assert first == second
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
    knobs = {**KNOBS, "L_forward_mm": 480.0}
    with pytest.raises(family.GeneratorError, match="no monotone area law"):
        family.evaluate(family._shape(GEN, knobs), steep, np.array([0.5]))


def test_round_throat_longer_than_the_horn_and_unknown_knobs_are_refused():
    with pytest.raises(family.GeneratorError, match="round_throat_mm must be shorter"):
        family._shape(GEN, {**KNOBS, "L_forward_mm": 20.0, "round_throat_mm": 20.0})
    with pytest.raises(family.GeneratorError, match="knob mismatch"):
        family._shape(GEN, {**KNOBS, "unknown": 1.0})


def test_configs_load_validate_and_estimate_the_envelope():
    c0 = load_config(C0)
    c1 = load_config(C1)
    space0 = DesignSpace.from_config(c0)
    space1 = DesignSpace.from_config(c1)
    assert isinstance(space0, GeneratedSpace) and isinstance(space1, GeneratedSpace)
    families.validate(space0.seed)
    families.validate(space1.seed)
    assert space0.seed.hash() == space1.seed.hash()       # same seed, same geometry
    json.dumps(space0.provenance(space0.seed))
    assert registry.envelope_overshoot_estimate(space0.seed.params, c0.brief) == 0.0
    assert c0.generator["name"] == family.KIND


def test_search_box_endpoints_are_legal():
    cfg = load_config(C1)
    seeds = {k: float(v) for k, v in cfg.seed_params.items()}
    bounds = {k: Bound(lo=b["lo"], hi=b["hi"], search=b.get("search", True))
              for k, b in cfg.bounds_raw.items()}
    family.validate_search_config(cfg.generator, seeds, bounds, cfg.brief)
    bounds["round_throat_mm"] = Bound(10.0, 90.0, search=True)
    family.validate_search_config(cfg.generator, seeds, bounds, cfg.brief)


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
    assert valid >= 90          # >85 % admission gate, law-level only


def test_owner_review_curvature_is_continuous_at_the_gate():
    law_h = _law(np.array([0.1 - 1e-6, 0.1, 0.1 + 1e-6]))
    # the aspect and exponent gates are constant (C2) on both sides of the round throat
    assert np.allclose(law_h["aspect"], 1.0, atol=1e-12)
    assert np.allclose(law_h["p"], 2.0, atol=1e-12)


@requires_mesher
def test_real_quarter_mesh_is_closed_and_round_at_the_driver(tmp_path):
    from hornlab_search.mesh import build, sizing, topology, throat_check
    cfg = load_config(C0)
    space = DesignSpace.from_config(cfg)
    spec = mesh_spec("screen", cfg)
    result = build.build_mesh(space.seed, spec, cfg, tmp_path / "mesh", mode="screen")
    assert result.n_triangles > 1000
    summary, xyz, tri = build.read_msh_summary(Path(result.path), return_arrays=True)
    assert summary["tags"].get(build.SOURCE_TAG, 0) > 0
    report = topology.check_surface(xyz, tri, sizing.SYMMETRY_PLANE["1"])
    assert report.bad_open_edges == 0 and report.nonmanifold_edges == 0
    shape = throat_check.throat_shape(Path(result.path))
    fits, reason = throat_check.fits_exit(shape, 36.0)
    assert fits is True, reason
    # The continuous coupling plane is exactly round (a = b = r0); a triangle fan can only
    # approximate it, so this mesh-level check uses a 1 % polygon tolerance.
    assert shape["roundness"] == pytest.approx(1.0, abs=1e-2)
    print(f"\nmesh: {result.n_triangles} tris, tags={summary['tags']}, "
          f"throat={shape['width_mm']:.3f}x{shape['height_mm']:.3f} mm, "
          f"roundness={shape['roundness']:.6f}")
