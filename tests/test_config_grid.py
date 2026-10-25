"""WP10 wire-in, pure (no mesher) tests: grid configs -> GeneratedSpace -> FREEFORM designs.

The grid adapter keeps family FREEFORM (frozen contract) but its params are the compact surface
spec plus the knob recipe (``{"grid": {...}}``), consumed by ``mesh/build.py`` at mesh time.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from conftest import EXAMPLES
from hornlab_search.config import load_config
from hornlab_search.design import families, generated
from hornlab_search.design.generated import (GENERATOR_ERROR_KEY, GENERATOR_OVERSHOOT_KEY,
                                             GeneratedSpace)
from hornlab_search.design.generators import grid, registry
from hornlab_search.design.space import DesignSpace
from hornlab_search.objective.terms import graded_infeasible_penalty
from hornlab_search.types import GeometryInvalidError

TYP = EXAMPLES / "typologies"
GRID_CONFIGS = ("grid_ellipse", "grid_ellipse_mod")


def _cfg(name="grid_ellipse"):
    return load_config(TYP / f"{name}.yaml")


def _space(name="grid_ellipse"):
    return DesignSpace.from_config(_cfg(name))


# ------------------------------------------------------------------ config -> space -> params


@pytest.mark.parametrize("name", GRID_CONFIGS)
def test_grid_configs_load_as_freeform_generator_spaces(name):
    cfg = _cfg(name)
    assert cfg.family == "FREEFORM" and cfg.generator is not None
    assert cfg.generator["name"] == "grid"
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace) and space.family == "FREEFORM"
    assert space.seed.family == "FREEFORM"           # frozen family literal
    families.validate(space.seed)                    # the grid validate branch accepts it


@pytest.mark.parametrize("name", GRID_CONFIGS)
def test_grid_params_are_compact_json_and_carry_the_knob_recipe(name):
    space = _space(name)
    params = space.seed.params
    assert set(params) == {"grid"}
    block = params["grid"]
    assert set(block) == set(grid.GRID_BLOCK_KEYS)
    assert block["profile_h"] == {"type": "conical"} and block["profile_v"] == "same"
    assert isinstance(block["n_phi"], int) and block["n_phi"] >= grid.MIN_PHI_QUARTER
    assert isinstance(block["n_s"], int) and block["n_s"] >= 8
    assert block["max_wall_deg"] == pytest.approx(80.0)
    assert block["wall_thickness_mm"] == pytest.approx(3.0)
    # the recipe is present and equals the space's seed knobs (minus canonicalised defaults)
    assert block["knobs"] == grid._recipe_knobs(space.seed_knobs)
    assert block["knobs"]["L_mm"] == pytest.approx(space.seed_knobs["L_mm"])
    assert block["knobs"]["h_rm_mm"] == pytest.approx(space.seed_knobs["h_rm_mm"])
    text = json.dumps(params, sort_keys=True)         # JSON-serialisable, no numpy objects

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        else:
            assert isinstance(node, (str, int, float, bool)) and not isinstance(node, np.generic)

    walk(json.loads(text))


def test_zero_modulation_params_drop_default_knobs_and_keep_the_geometry_hash():
    space = _space("grid_ellipse")
    base = space.seed
    explicit_zero = space.design_from_knobs({**space.seed_knobs, "g_pnorm": 2.0,
                                             "g_term_side_mm": 0.0, "g_a1_mouth": 0.0,
                                             "g_a2_throat": 0.0})
    assert "g_pnorm" not in base.params["grid"]["knobs"]
    assert "g_pnorm" not in explicit_zero.params["grid"]["knobs"]
    assert explicit_zero.hash() == base.hash()       # same recipe -> same geometry hash

    knobs = {**space.seed_knobs, "g_a1_mouth": 0.06}
    modulated = space.design_from_knobs(knobs)
    assert modulated.params["grid"]["knobs"]["g_a1_mouth"] == pytest.approx(0.06)
    assert modulated.hash() != base.hash()           # the recipe distinguishes geometry


def test_design_hash_distinguishes_grid_sizes():
    space = _space("grid_ellipse")
    a = space.design_from_knobs({**space.seed_knobs, "L_mm": 140.0})
    b = space.design_from_knobs({**space.seed_knobs, "L_mm": 210.0})
    assert a.hash() != b.hash()
    assert a.params["grid"]["knobs"]["L_mm"] == pytest.approx(140.0)
    assert b.params["grid"]["knobs"]["L_mm"] == pytest.approx(210.0)


@pytest.mark.parametrize("name", GRID_CONFIGS)
def test_grid_design_space_round_trips_and_corners_are_invalid_or_legal(name):
    space = _space(name)
    k = len(space.keys())
    rng = np.random.default_rng(0)
    for x in [np.zeros(k), np.ones(k), *rng.random((10, k))]:
        d = space.denormalize(x)
        if GENERATOR_ERROR_KEY not in d.params:
            families.validate(d)
        assert np.allclose(space.normalize(d), np.clip(x, 0, 1), atol=1e-6)
        prov = space.provenance(d)
        assert prov["name"] == "grid" and prov["brief"] == "axi_90x90_1in"
        assert set(space.keys()) <= set(prov["knobs"])


def test_grid_provenance_carries_name_spec_and_knobs_for_row_distinguishability():
    space = _space("grid_ellipse_mod")
    prov = space.provenance(space.seed)
    assert prov["name"] == "grid"
    assert prov["spec"]["name"] == "grid" and prov["spec"]["profile_h"] == {"type": "conical"}
    assert prov["knobs"]["g_a1_mouth"] == pytest.approx(0.06)
    assert prov["brief"] == "axi_90x90_1in" and prov["brief_hash"]
    assert "h" in prov["derived"]                    # registry.info still reports the meridian


# ------------------------------------------------------------------ families.validate branch


def test_validate_grid_rejects_bad_spec_with_geometry_invalid():
    space = _space("grid_ellipse")
    good = space.seed.params["grid"]
    for block, match in (
        ({**good, "n_phi": 12}, "n_phi"),
        ({**good, "n_s": 4}, "n_s"),
        ({**good, "max_wall_deg": 95.0}, "max_wall_deg"),
        ({**good, "wall_thickness_mm": 20.0}, "wall_thickness_mm"),
        ({**good, "profile_h": {"type": "bogus"}}, "unknown typology"),
        ({**good, "knobs": {"g_pnorm": 0.5}}, "pnorm"),
        ({**good, "bogus": 1}, "unknown key"),
        ({k: v for k, v in good.items() if k != "knobs"}, "knobs are required"),
    ):
        with pytest.raises(GeometryInvalidError, match=match):
            families.validate(generated.Design("FREEFORM", {"grid": block}))


def test_validate_grid_rejects_foreign_top_level_keys_and_wrong_family():
    space = _space("grid_ellipse")
    block = space.seed.params["grid"]
    with pytest.raises(GeometryInvalidError, match="not a grid design key"):
        families.validate(generated.Design("FREEFORM", {"grid": block, "profileH": {}}))
    with pytest.raises(GeometryInvalidError, match="family FREEFORM"):
        families.validate(generated.Design("OSSE", {"grid": block}))


# ------------------------------------------------------------------ envelope estimate (WP3)


def test_grid_seed_envelope_estimate_is_zero_and_inside():
    cfg = _cfg()
    est = registry.envelope_overshoot_estimate(_space().seed.params, cfg.brief)
    assert est == 0.0


def test_long_grid_spec_estimate_is_positive_and_monotone():
    cfg = _cfg()
    block = _space().seed.params["grid"]
    estimates = []
    for L in (180.0, 400.0, 800.0):
        b = {**block, "knobs": {**block["knobs"], "L_mm": L}}
        estimates.append(registry.envelope_overshoot_estimate({"grid": b}, cfg.brief))
    assert estimates[0] == 0.0
    assert estimates[1] > 0.0 and estimates[2] > estimates[1] > 0.0
    # the graded penalty stays finite and monotone in the estimate
    penalties = [graded_infeasible_penalty(v) for v in estimates[1:]]
    assert all(np.isfinite(penalties)) and penalties[1] > penalties[0]


def test_big_mouth_is_graded_not_a_flat_generator_error():
    space = _space()
    d = space.design_from_knobs({**space.seed_knobs, "h_rm_mm": 400.0})
    assert GENERATOR_ERROR_KEY in d.params
    assert d.params[GENERATOR_ERROR_KEY].startswith("invalid_envelope")
    over = d.params[GENERATOR_OVERSHOOT_KEY]
    assert isinstance(over, float) and np.isfinite(over) and 0.0 < over <= 10.0


def test_modulated_corner_reports_a_finite_overshoot():
    """The mod config's top h_rm corner is slightly over the 360 mm mouth: graded, finite."""
    space = _space("grid_ellipse_mod")
    d = space.denormalize(np.ones(len(space.keys())))
    assert GENERATOR_ERROR_KEY in d.params
    assert d.params[GENERATOR_ERROR_KEY].startswith("invalid_envelope")
    assert 0.0 < d.params[GENERATOR_OVERSHOOT_KEY] < 10.0


# ------------------------------------------------------------------ error path (FREEFORM unchanged)


def test_grid_bad_knob_becomes_a_generator_error_design():
    space = _space()
    d = space.design_from_knobs({**space.seed_knobs, "g_pnorm": 0.2})
    assert GENERATOR_ERROR_KEY in d.params and "pnorm" in d.params[GENERATOR_ERROR_KEY]
    assert d.params["_knobs"]["g_pnorm"] == pytest.approx(0.2)


def test_non_grid_generator_is_untouched():
    """A plain typology generator still materialises FREEFORM anchors through the same module."""
    cfg = load_config(TYP / "conical.yaml")
    space = DesignSpace.from_config(cfg)
    assert isinstance(space, GeneratedSpace) and space.family == "FREEFORM"
    assert "profileH" in space.seed.params and "grid" not in space.seed.params
    assert generated.materialize(cfg.generator, space.seed_knobs, cfg.brief) == space.seed.params
