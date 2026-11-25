from dataclasses import replace
from types import SimpleNamespace

import pytest

from conftest import REPO
from hornlab_search.config import ConfigError, envelope_policy, load_config, mesh_spec
from hornlab_search.design.generators import grid, registry
from hornlab_search.design.size import full_bbox_extents_mm, size_feasibility_record
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh.build import build_mesh
from hornlab_search.search import cma, rundir
from hornlab_search.search.evaluate import envelope_violation


def _brief(**overrides):
    return {"driver": {"exit_radius_mm": 18, "exit_angle_deg": 2},
            "envelope": {"max_mouth_w_mm": 600, "max_mouth_h_mm": 480, "max_depth_mm": 200,
                         **overrides}}


def test_envelope_policies_share_the_product_box_and_identify_candidate_limits():
    production = envelope_policy(_brief())
    near = envelope_policy(_brief(enforce=False, max_utilization=1.15))
    open_policy = envelope_policy(_brief(enforce=False))

    assert production.product_limits_mm == near.product_limits_mm == open_policy.product_limits_mm
    assert production.mesh_limits_mm == (600.5, 480.5, 215)
    assert near.mesh_limits_mm == pytest.approx((690, 552, 230))
    assert open_policy.mesh_limits_mm == (1200, 1200, 1200)
    assert len({production.policy_id, near.policy_id, open_policy.policy_id}) == 3


def test_embedded_brief_refuses_conflicting_utilization(tmp_path):
    import yaml

    original = load_config(REPO / "examples/typologies/grid_ellipse.yaml")
    raw = dict(original.raw)
    raw["brief"] = _brief(enforce=True, max_utilization=1.1)
    snapshot = tmp_path / "config.yaml"
    snapshot.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError, match=r"envelope\.max_utilization"):
        load_config(snapshot)


def test_cma_refuses_policy_change_before_reusing_run_rows(tmp_path):
    original = envelope_policy(_brief(enforce=False))
    rundir.write_json_atomic(tmp_path / "run.json", {"envelope_policy": original.as_dict()})
    cfg = SimpleNamespace(brief=_brief(enforce=False, max_utilization=1.15))
    with pytest.raises(ValueError, match="cannot resume after changing the candidate envelope"):
        cma._prepare(cfg, tmp_path, "screen", None, None, None, 0.0, "", None, None)


@pytest.mark.parametrize(("planes", "expected"), [
    ("yz+xz", (580, 360, 210)),
    ("yz", (580, 170, 210)),
    (None, (280, 170, 210)),
])
def test_full_bounds_reconstruct_only_declared_mirror_planes(planes, expected):
    assert full_bbox_extents_mm((0.01, 0.01, -0.01, 0.29, 0.18, 0.2), planes) == pytest.approx(expected)


def test_mesh_metadata_separates_product_fit_from_candidate_fit():
    mesh = SimpleNamespace(bbox_m=(0, 0, 0, 0.32, 0.22, 0.21),
                           symmetry_plane="yz+xz", n_dof=3200)
    near = _brief(enforce=False, max_utilization=1.15)
    record = size_feasibility_record(mesh, envelope_policy(near), design_hash="d",
                                    mesh_hash="m", mounted=False)
    assert record["width_mm"] == pytest.approx(640)
    assert record["product_margins"] == pytest.approx(
        {"width": 640 / 600 - 1, "height": 440 / 480 - 1, "depth": 210 / 200 - 1})
    assert record["max_utilization"] == pytest.approx(640 / 600)
    assert record["product_fit"] == "outside"
    assert record["candidate_fit"] == "inside"
    assert not envelope_violation(mesh, near)
    assert envelope_violation(mesh, _brief()).startswith("outside the brief envelope")
    assert envelope_violation(mesh, _brief(enforce=False, sanity_max_mm=630)).startswith(
        "outside the sanity envelope")


def test_standard_freeform_open_depth_and_physical_validation():
    spec = {"profile_h": {"type": "conical"}}
    with pytest.raises(registry.GeneratorError, match="invalid_envelope"):
        registry.materialize(spec, {"L_mm": 220}, _brief())
    params = registry.materialize(spec, {"L_mm": 220}, _brief(enforce=False))
    assert params["profileH"]["points"][-1][0] == 220
    with pytest.raises(registry.GeneratorError, match="wall_thickness_mm"):
        registry.materialize({**spec, "wall_thickness_mm": -5}, {"L_mm": 220}, _brief(enforce=False))


def test_generic_grid_open_depth_has_distinct_recipe_and_retains_asymmetric_width_height():
    spec = {"name": "grid", "profile_h": {"type": "conical"},
            "profile_v": {"type": "conical"}}
    knobs = {"L_mm": 220, "h_rm_mm": 175, "v_rm_mm": 115}
    open_brief = _brief(enforce=False)
    with pytest.raises(registry.GeneratorError, match="invalid_envelope"):
        grid.design_params(spec, knobs, _brief())
    block = grid.design_params(spec, knobs, open_brief)["grid"]
    assert block["uncapped_span_mm"] == pytest.approx(220)
    selected = {key: value for key, value in block.items() if key != "knobs"}
    points, info = grid.grid_points(selected, block["knobs"], _brief(), legacy_depth_limits=True)
    assert info["L_mm"] == pytest.approx(220)
    assert points[..., 2].max() == pytest.approx(220)
    w, h, _ = grid.envelope_extents(selected, block["knobs"], open_brief)
    assert w > h


@pytest.mark.parametrize("config_name", ["grid_ellipse_mod", "grid_ellipse"])
def test_cpu_mesh_admits_selected_oversize_grid_without_changing_within_box_recipe(
        config_name, tmp_path):
    pytest.importorskip("hornlab_mesher")
    cfg = load_config(REPO / "examples/typologies" / f"{config_name}.yaml")
    original = DesignSpace.from_config(cfg).seed
    open_brief = {**cfg.brief, "envelope": {**cfg.brief["envelope"], "enforce": False}}
    unchanged = DesignSpace.from_config(replace(cfg, brief=open_brief)).seed
    assert original.hash() == unchanged.hash()

    narrow = {**open_brief, "envelope": {**open_brief["envelope"], "max_mouth_h_mm": 100}}
    open_cfg = replace(cfg, brief=narrow)
    selected = DesignSpace.from_config(open_cfg).seed
    mesh = build_mesh(selected, mesh_spec("screen", open_cfg), open_cfg, tmp_path, mode="screen")
    production = {**narrow, "envelope": {**narrow["envelope"], "enforce": True}}
    assert not envelope_violation(mesh, narrow)
    assert envelope_violation(mesh, production).startswith("outside the brief envelope")
    width, height, depth = full_bbox_extents_mm(mesh.bbox_m, mesh.symmetry_plane)
    approx = grid.envelope_extents(selected.params["grid"], selected.params["grid"]["knobs"], narrow)
    shell = selected.params["grid"]["wall_thickness_mm"]
    assert (approx[0] - width, approx[1] - height) == pytest.approx((2 * shell, 2 * shell))
    assert depth == pytest.approx(approx[2], abs=2 * shell)
    record = size_feasibility_record(mesh, envelope_policy(narrow), design_hash=selected.hash(),
                                    mesh_hash=mesh_spec("screen", open_cfg).hash(), mounted=False)
    assert record["mouth_aperture"]["source"] == "sampled_terminal_inner_rim_projection"
    assert record["mouth_aperture"]["width_mm"] == pytest.approx(mesh.terminal_rim_wh_mm[0])
