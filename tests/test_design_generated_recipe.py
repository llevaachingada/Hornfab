"""Durable generated-space intake: rebuild a Design from its persisted recipe.

The fixtures are two real archived v11 records (one Room 90x50/c500 grid, one FAV grid) taken from
``dataset/``: their ``provenance.generator`` block, recorded design hash, objective and full term
row. The tests prove the fail-closed recipe contract without a mesh, solver or GPU.
"""
import copy

import pytest

from conftest import EXAMPLES
from hornlab_search.bo.encoding import ActiveProjection, HashMismatchError
from hornlab_search.config import load_config
from hornlab_search.design.generated import (
    GeneratedSpace, GeneratorRecipeError, brief_hash, design_from_recipe,
)
from hornlab_search.design.space import DesignSpace

TYP = EXAMPLES / "typologies" / "round3_2026-11-22"
C500_CONFIG = TYP / "r3_c500.yaml"
FAV_CONFIG = TYP / "r3_fav.yaml"

#: Archived r3_c500 run 20261122T223153Z-screen-98b41d, row 247.
C500 = {
    "design_hash": "e7561f9dca7a",
    "objective": 3.1657266141178413,
    "generator": {
        "brief": "compact500_xo900_80x50_hf1440_v11cd_open",
        "brief_hash": "99a1d837354d",
        "knobs": {
            "g_L_mm": 258.1227589256,
            "g_a_h_deg": 31.1980072262,
            "g_a_v_deg": 30.3161069178,
            "g_k": 2.1361411324,
            "g_n": 3.0025971063,
            "g_q": 0.996,
            "g_r_lip_mm": 13.1468202495,
            "g_s": 0.3615829457,
            "g_sf_ab": 0.8543989367,
            "g_sf_amt": 0.1984608478,
            "g_sf_m": 4.0,
            "g_sf_n1": 1.8,
            "g_sf_n2": 7.0,
            "g_sf_start": 0.25,
            "g_wrap_deg": 137.1642954075,
        },
        "name": "grid",
        "spec": {
            "n_phi": 25,
            "n_s": 40,
            "name": "grid",
            "rows": {"type": "osse_rollback"},
            "span": "quarter",
            "wall_thickness_mm": 3.0,
        },
    },
    "terms": {
        "cd_di_std": 0.5702095450444867,
        "cd_lw": 0.18338376800785552,
        "cd_nacc": 0.19098731443288886,
        "cd_omega_2pi": 0.697974359902676,
        "cd_status_code": 0.0,
        "constancy": 0.0,
        "cov_profile": 0.045458439640839676,
        "di_estimated": 0.0,
        "di_roughness": 0.18667724305077685,
        "diag": 1.235224736551609,
        "dislope": 0.5777821046910103,
        "distd": 0.5997564989383053,
        "f11_hz": 5600.0,
        "flat": 0.3698324592043858,
        "flat_cv": 0.394448667045926,
        "hf_floor": 0.0,
        "lfp20_hz": 568.6871605697154,
        "lfp50_hz": 770.3352582741286,
        "load": 0.052607120483074976,
        "loaded_hi_hz": 5600.0,
        "n_in_band": 16,
        "n_nan": 0,
        "oa_excess_raw": 30.0,
        "offaxis_smooth": 1.4086306647472546,
        "penalty": 0.0,
        "rez_min_from_fx": 0.9041422503746757,
        "rip": 0.09737371126161404,
        "total": 3.1657266141178413,
    },
}

#: Archived r3_fav run 20261122T232104Z-screen-2cc59b, row 338.
FAV = {
    "design_hash": "5f042d687a62",
    "objective": 4.433823989378595,
    "generator": {
        "brief": "room_landscape_80x50_700_hf1440_v11cd_open",
        "brief_hash": "c6bc496e7b4f",
        "knobs": {
            "g_L_mm": 303.3713956403,
            "g_a_h_deg": 32.1630251231,
            "g_a_v_deg": 27.6653604964,
            "g_k": 1.3798200041,
            "g_n": 2.7480559143,
            "g_q": 0.996,
            "g_r_lip_mm": 18.5076046997,
            "g_s": 0.3704136372,
            "g_sf_ab": 0.9157253029,
            "g_sf_amt": 0.2569807571,
            "g_sf_m": 4.0,
            "g_sf_n1": 1.8,
            "g_sf_n2": 7.0,
            "g_sf_start": 0.25,
            "g_wrap_deg": 64.1737048398,
        },
        "name": "grid",
        "spec": {
            "n_phi": 25,
            "n_s": 40,
            "name": "grid",
            "rows": {"type": "osse_rollback"},
            "span": "quarter",
            "wall_thickness_mm": 3.0,
        },
    },
    "terms": {
        "cd_di_std": 0.41384300525804296,
        "cd_lw": 0.2363338273591529,
        "cd_nacc": 0.22620144999503378,
        "cd_omega_2pi": 0.6898338168101278,
        "cd_status_code": 0.0,
        "constancy": 0.0,
        "cov_profile": 0.0016169812097306688,
        "di_estimated": 0.0,
        "di_roughness": 0.27819529854553576,
        "diag": 0.4664272504409479,
        "dislope": 0.19541726286193123,
        "distd": 0.46703156167507753,
        "f11_hz": 5600.0,
        "flat": 0.876880197550563,
        "flat_cv": 0.7233681700090253,
        "hf_floor": 0.0,
        "lfp20_hz": 597.764190549986,
        "lfp50_hz": 884.1329931277365,
        "load": 1.7950282394095995,
        "loaded_hi_hz": 5600.0,
        "n_in_band": 16,
        "n_nan": 0,
        "oa_excess_raw": 30.0,
        "offaxis_smooth": 0.6964462712981102,
        "penalty": 0.0,
        "rez_min_from_fx": 0.41178498525828594,
        "rip": 0.13853590099818205,
        "total": 4.433823989378595,
    },
}


def _space(path):
    space = DesignSpace.from_config(load_config(path))
    assert isinstance(space, GeneratedSpace)
    return space


@pytest.fixture(scope="module", params=[("c500", C500_CONFIG, C500), ("fav", FAV_CONFIG, FAV)],
                ids=["c500", "fav"])
def archived(request):
    _label, config, fixture = request.param
    space = _space(config)
    assert brief_hash(space.brief) == fixture["generator"]["brief_hash"]
    return space, fixture


def test_real_recipe_rematerialises_and_round_trips(archived):
    space, fixture = archived
    design = design_from_recipe(space, fixture["generator"],
                                expected_design_hash=fixture["design_hash"])
    assert design.hash() == fixture["design_hash"]
    projection = ActiveProjection.from_space(space)
    x = projection.normalize_design(design, verify_round_trip=True)
    assert x.shape == (len(space.keys()),)
    assert (x >= 0.0).all() and (x <= 1.0).all()
    # The proof is exact: decoding the active vector reproduces the archived design hash.
    assert projection.denormalize(x).hash() == fixture["design_hash"]


def test_recipe_knobs_equal_the_archived_provenance(archived):
    space, fixture = archived
    design = design_from_recipe(space, fixture["generator"],
                                expected_design_hash=fixture["design_hash"])
    assert space.provenance(design)["knobs"] == fixture["generator"]["knobs"]


def test_missing_knob_is_refused(archived):
    space, fixture = archived
    recipe = copy.deepcopy(fixture["generator"])
    recipe["knobs"].pop("g_L_mm")
    with pytest.raises(GeneratorRecipeError, match="knob set differs"):
        design_from_recipe(space, recipe, expected_design_hash=fixture["design_hash"])


def test_extra_knob_is_refused(archived):
    space, fixture = archived
    recipe = copy.deepcopy(fixture["generator"])
    recipe["knobs"]["g_extra"] = 1.0
    with pytest.raises(GeneratorRecipeError, match="knob set differs"):
        design_from_recipe(space, recipe, expected_design_hash=fixture["design_hash"])


def test_changed_fixed_value_is_refused(archived):
    space, fixture = archived
    recipe = copy.deepcopy(fixture["generator"])
    recipe["knobs"]["g_q"] = 0.995
    with pytest.raises(GeneratorRecipeError, match="pinned generator knob 'g_q' changed"):
        design_from_recipe(space, recipe, expected_design_hash=fixture["design_hash"])


def test_out_of_box_knob_is_refused_without_clipping(archived):
    space, fixture = archived
    recipe = copy.deepcopy(fixture["generator"])
    recipe["knobs"]["g_L_mm"] = 10_000.0
    with pytest.raises(GeneratorRecipeError, match="outside its resolved bound"):
        design_from_recipe(space, recipe, expected_design_hash=fixture["design_hash"])


def test_changed_generator_spec_is_refused(archived):
    space, fixture = archived
    recipe = copy.deepcopy(fixture["generator"])
    recipe["spec"]["n_phi"] = 17
    with pytest.raises(GeneratorRecipeError, match="spec differs"):
        design_from_recipe(space, recipe, expected_design_hash=fixture["design_hash"])


def test_changed_brief_hash_is_refused(archived):
    space, fixture = archived
    recipe = copy.deepcopy(fixture["generator"])
    recipe["brief_hash"] = "000000000000"
    with pytest.raises(GeneratorRecipeError, match="brief_hash differs"):
        design_from_recipe(space, recipe, expected_design_hash=fixture["design_hash"])


def test_changed_geometry_hash_is_refused(archived):
    space, fixture = archived
    with pytest.raises(GeneratorRecipeError, match="re-materialised design hash"):
        design_from_recipe(space, fixture["generator"], expected_design_hash="000000000000")


def test_non_finite_and_list_knobs_are_refused(archived):
    space, fixture = archived
    recipe = copy.deepcopy(fixture["generator"])
    recipe["knobs"]["g_k"] = float("nan")
    with pytest.raises(GeneratorRecipeError, match="not finite"):
        design_from_recipe(space, recipe, expected_design_hash=fixture["design_hash"])
    recipe = copy.deepcopy(fixture["generator"])
    recipe["knobs"]["g_k"] = [2.0]
    with pytest.raises(GeneratorRecipeError, match="list-valued"):
        design_from_recipe(space, recipe, expected_design_hash=fixture["design_hash"])


def test_recipe_requires_a_generated_task_space():
    native = DesignSpace.from_config(load_config(EXAMPLES / "rosse_baseline.yaml"))
    with pytest.raises(GeneratorRecipeError, match="requires a generated task space"):
        design_from_recipe(native, C500["generator"], expected_design_hash=C500["design_hash"])


def test_other_family_projection_refuses_the_design():
    """A recipe only projects against the task that owns its bounds/knobs."""
    c500 = _space(C500_CONFIG)
    fav = _space(FAV_CONFIG)
    design = design_from_recipe(c500, C500["generator"], expected_design_hash=C500["design_hash"])
    with pytest.raises(HashMismatchError):
        ActiveProjection.from_space(fav).normalize_design(design, verify_round_trip=True)


def test_round_trip_failure_from_a_drifted_fixed_value_is_refused():
    """A task whose pinned value drifted after the recipe was proven fails the exact round-trip."""
    space = _space(C500_CONFIG)
    design = design_from_recipe(space, C500["generator"],
                                expected_design_hash=C500["design_hash"])
    space.seed_knobs["g_q"] = 0.995
    with pytest.raises(HashMismatchError, match="normalize->denormalize changed"):
        ActiveProjection.from_space(space).normalize_design(design, verify_round_trip=True)

