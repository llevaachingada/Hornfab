"""Offline tests for tools/analysis/crowe_mesh_truth.py (WP1).

Nothing here invokes gmsh, a BEM solver, CUDA or a GPU.  The real c0 topology regression uses a
stored ASCII ``.msh`` fixture built once through the project's CPU mesh path (``mesh/build.py``);
the rest are analytic/synthetic fixtures with known exact answers.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from conftest import REPO

_TOOL = REPO / "tools" / "analysis" / "crowe_mesh_truth.py"
_CFG = (REPO / "examples" / "typologies" / "crowe_hv_area_aspect_2026-11-16" / "configs"
        / "c0_four_dof_seed.yaml")
_BASE_CFG = (REPO / "examples" / "typologies" / "crowe_hv_area_aspect_2026-11-16" / "configs"
             / "c1_four_dof_bounds.yaml")
_FIXTURE = REPO / "tests" / "fixtures" / "crowe_v2a" / "c0_quarter_screen_8k"


def _load_tool(name: str, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


crt = _load_tool("crowe_mesh_truth_tool", _TOOL)


@pytest.fixture(scope="module")
def c0():
    from hornlab_search.config import load_config
    cfg = load_config(_CFG)
    shape = crt.family._shape(cfg.generator, cfg.seed_params)
    return cfg, shape, cfg.brief


@pytest.fixture(scope="module")
def c1():
    from hornlab_search.config import load_config
    cfg = load_config(_BASE_CFG)
    shape = crt.family._shape(cfg.generator, cfg.seed_params)
    return cfg, shape, cfg.brief


def _ring_surface(shape, brief, *, radial_offset_mm=0.0, n_phi=91, n_s=121,
                  include_source=False):
    """Synthetic wall from the analytic law at ``radial_offset_mm`` (mm), in metres."""
    from hornlab_search.compare.mshio import Mesh

    length = float(shape["L_forward_mm"])
    u = np.linspace(0.0, 1.0, int(n_s))
    phi = np.radians(np.linspace(0.0, 90.0, int(n_phi)))
    law = crt.family.evaluate(shape, brief, u)
    grid = np.empty((len(phi), len(u), 3), dtype=float)
    for j, p in enumerate(phi):
        r = crt.law_radius_mm(law["a_mm"], law["b_mm"], law["p"], p) + radial_offset_mm
        grid[j, :, 0] = r * math.cos(p)
        grid[j, :, 1] = r * math.sin(p)
        grid[j, :, 2] = u * length
    pts = grid.reshape(-1, 3)
    idx = np.arange(len(pts)).reshape(len(phi), len(u))
    t1 = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:]], axis=-1).reshape(-1, 3)
    t2 = np.stack([idx[:-1, :-1], idx[1:, 1:], idx[:-1, 1:]], axis=-1).reshape(-1, 3)
    tri = np.vstack([t1, t2])
    phys = np.full(len(tri), 1, dtype=np.int64)
    names = {1: "SD1G0", 2: "SD1D1001"}
    if include_source:
        origin = len(pts)
        pts = np.vstack([pts, np.zeros((1, 3))])
        fan = np.stack([np.full(len(phi) - 1, origin),
                        idx[:-1, 0], idx[1:, 0]], axis=-1)
        tri = np.vstack([tri, fan])
        phys = np.concatenate([phys, np.full(len(fan), 2, dtype=np.int64)])
    return Mesh(pts / 1000.0, tri, phys, names)


# ------------------------------------------------------------------ analytic law


def test_analytic_section_matches_generator_section_cuts(c0):
    cfg, shape, brief = c0
    rows = {r["z_mm"]: r for r in crt.family.section_cuts(
        cfg.generator, cfg.seed_params, brief, (0.0, 40.0, 100.0))}
    for z in (0.0, 40.0, 100.0):
        sec = crt.analytic_section(shape, brief, z)
        assert sec["a_mm"] == pytest.approx(rows[z]["a_mm"], abs=1e-4)
        assert sec["b_mm"] == pytest.approx(rows[z]["b_mm"], abs=1e-4)
        assert sec["area_mm2"] == pytest.approx(rows[z]["area_mm2"], abs=1e-3)
        assert sec["aspect"] == pytest.approx(rows[z]["aspect"], abs=1e-6)


def test_analytic_superellipse_points_lie_on_the_implicit_section(c0):
    cfg, shape, brief = c0
    pts, recs = crt.analytic_samples(shape, brief, (40.0,), (0.5,), (0.0, 22.5, 45.0, 90.0))
    for q, rec in zip(pts, recs):
        f = ((abs(q[0]) / rec["a_mm"]) ** rec["p"]
             + (abs(q[1]) / rec["b_mm"]) ** rec["p"])
        assert f == pytest.approx(1.0, rel=1e-12)
        assert q[2] == pytest.approx(rec["z_mm"])


def test_unknown_azimuth_radius_matches_axis_and_diagonal(c0):
    cfg, shape, brief = c0
    sec = crt.analytic_section(shape, brief, 100.0)
    assert crt.law_radius_mm(sec["a_mm"], sec["b_mm"], sec["p"], 0.0) == pytest.approx(sec["a_mm"])
    assert (crt.law_radius_mm(sec["a_mm"], sec["b_mm"], sec["p"], math.pi / 2)
            == pytest.approx(sec["b_mm"]))


def test_analytic_samples_are_deterministic(c0):
    cfg, shape, brief = c0
    a, ra = crt.analytic_samples(shape, brief)
    b, rb = crt.analytic_samples(shape, brief)
    assert np.array_equal(a, b)
    assert ra == rb


# ------------------------------------------------------------------ exact distance geometry


def test_point_to_surface_plane_distance_is_exact():
    tri = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]],
                    [[0.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]])
    pts = np.array([[0.25, 0.25, 1.5], [0.75, 0.75, -2.0]])
    out = crt.point_to_surface(pts, tri, k=2)
    assert out["distance_mm"].tolist() == pytest.approx([1.5, 2.0])


def test_section_area_and_spans_of_a_quarter_circle():
    n = 181
    phi = np.linspace(0.0, 0.5 * math.pi, n)
    r = 25.0
    ring = np.column_stack([r * np.cos(phi), r * np.sin(phi), np.zeros(n)])
    ring2 = ring.copy()
    ring2[:, 2] = 10.0
    pts = np.vstack([ring, ring2])
    idx = np.arange(2 * n).reshape(2, n)
    t1 = np.stack([idx[0, :-1], idx[1, :-1], idx[1, 1:]], axis=-1)
    t2 = np.stack([idx[0, :-1], idx[1, 1:], idx[0, 1:]], axis=-1)
    tri = pts[np.vstack([t1, t2])]
    sec = crt.mesh_section(tri, 5.0)
    assert sec["measurable"] is True
    assert sec["h_half_span_mm"] == pytest.approx(25.0, abs=1e-6)
    assert sec["v_half_span_mm"] == pytest.approx(25.0, abs=1e-6)
    assert sec["area_mm2"] == pytest.approx(math.pi * 25.0 ** 2, rel=2e-4)


def test_unmeasurable_section_is_typed_not_zero():
    tri = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]])
    sec = crt.mesh_section(tri, 10.0)
    assert sec["measurable"] is False
    assert "reason" in sec
    assert "area_mm2" not in sec


# ------------------------------------------------------------------ roles / topology


def test_source_and_shell_tag_classification(c0):
    cfg, shape, brief = c0
    mesh = _ring_surface(shape, brief, radial_offset_mm=0.0, include_source=True)
    roles = crt.classify_roles(mesh, shape, brief)
    assert roles["source_tag"] == 2
    assert roles["wall_tag"] == 1
    assert roles["tag_counts"] == {1: len(roles["wall_tri"]), 2: len(roles["source_tri"])}
    assert len(roles["source_tri"]) == 90          # 91 azimuths -> 90 source fan triangles
    assert not np.any(np.isin(roles["source_tri"], roles["wall_tri"]))


def test_inner_and_outer_sheets_are_separated_by_radial_role(c0):
    cfg, shape, brief = c0
    # Build inner + outer sheets as one tag-1 surface, as the real freestanding mesh does.
    from hornlab_search.compare.mshio import Mesh
    inner = _ring_surface(shape, brief, radial_offset_mm=0.0)
    outer = _ring_surface(shape, brief, radial_offset_mm=3.0)
    n = len(inner.xyz)
    mesh = Mesh(np.vstack([inner.xyz, outer.xyz]),
                np.vstack([inner.tri, outer.tri + n]),
                np.concatenate([inner.phys, outer.phys]), dict(inner.names))
    roles = crt.classify_roles(mesh, shape, brief)
    n_per_sheet = len(inner.tri)
    assert len(roles["inner_tri"]) == pytest.approx(n_per_sheet, rel=1e-6)
    assert len(roles["shell_tri"]) == pytest.approx(n_per_sheet, rel=1e-6)
    # The inner sheet is the one whose radial residual is ~0, not ~3 mm.
    assert abs(roles["inner_radial_delta_mm_stats"]["50"]) < 0.05
    assert roles["shell_radial_delta_mm_stats"]["5"] > 2.0

def test_closed_cube_has_no_holes_or_winding_errors():
    v = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                  [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], dtype=float)
    f = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
                  [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
                  [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    topo = crt.mesh_topology(v, f, ())
    assert topo["open_edges"] == 0
    assert topo["nonmanifold_edges"] == 0
    assert topo["winding_inconsistent_edges"] == 0


def test_open_edges_are_role_aware_for_a_quarter_domain():
    # Cube shifted off both symmetry planes, top face removed: every open ring edge is off-plane.
    v = np.array([[1, 1, 0], [2, 1, 0], [2, 2, 0], [1, 2, 0],
                  [1, 1, 1], [2, 1, 1], [2, 2, 1], [1, 2, 1]], dtype=float)
    f_top_removed = np.array([[0, 2, 1], [0, 3, 2],          # bottom
                              [0, 1, 5], [0, 5, 4],          # y=1
                              [1, 2, 6], [1, 6, 5],          # x=2
                              [2, 3, 7], [2, 7, 6],          # y=2
                              [3, 0, 4], [3, 4, 7]])         # x=1
    topo = crt.mesh_topology(v, f_top_removed, (0, 1))
    assert topo["open_edges"] == 4
    assert topo["open_edges_off_symmetry_planes"] == 4
    assert topo["open_edges_on_symmetry_planes"] == 0


# ------------------------------------------------------------------ signed-error fixture


@pytest.mark.parametrize("offset_mm,expected_sign", [(1.0, 1.0), (-1.0, -1.0)])
def test_intentional_signed_offset_is_recovered(c0, offset_mm, expected_sign):
    cfg, shape, brief = c0
    mesh = _ring_surface(shape, brief, radial_offset_mm=offset_mm, n_phi=181, n_s=241)
    roles = crt.classify_roles(mesh, shape, brief)
    inner = roles["xyz_mm"][mesh.tri[roles["inner_tri"]]]
    pts, recs = crt.analytic_samples(shape, brief)
    dev = crt._deviation_stats(pts, recs, inner, k=24)
    assert dev["measurable"] is True
    assert abs(dev["signed_bias_mm"]) == pytest.approx(abs(offset_mm), abs=0.2)
    assert math.copysign(1.0, dev["signed_bias_mm"]) == expected_sign
    assert abs(dev["median_mm"]) == pytest.approx(abs(offset_mm), abs=0.2)


# ------------------------------------------------------------------ rule / rank


def test_fable_rule_threshold_is_max_of_absolute_and_relative():
    assert crt.fable_v2_threshold(0.02) == pytest.approx(1.0)
    assert crt.fable_v2_threshold(2.0) == pytest.approx(2.5)


def test_law_and_surface_rank_are_contract_four(c1):
    cfg, shape, brief = c1
    bounds = crt._bounds(cfg)
    knobs = {k: float(v) for k, v in cfg.seed_params.items()}
    law = crt._law_rank(shape, knobs, bounds, brief)
    surf = crt.surface_displacement_rank(shape, brief, knobs, bounds)
    assert law["practical_rank"] == 4
    assert surf["practical_rank"] == 4
    assert set(surf["column_norms_relative"]) == set(crt.family.PARAM_KEYS)
    # A seed on its upper bound must use an inward one-sided difference, not a clipped centre.
    assert surf["scheme"]["height_v_active_mm"]["scheme"] == "one_sided_inward"


def test_surface_rank_columns_are_deterministic(c1):
    cfg, shape, brief = c1
    bounds = crt._bounds(cfg)
    knobs = {k: float(v) for k, v in cfg.seed_params.items()}
    a = crt.surface_displacement_rank(shape, brief, knobs, bounds)
    b = crt.surface_displacement_rank(shape, brief, knobs, bounds)
    assert a == b


# ------------------------------------------------------------------ guard / refusal


def test_no_solve_guard_refuses_a_loaded_solve_module(monkeypatch):
    monkeypatch.setitem(sys.modules, "hornlab_search.solve", object())
    with pytest.raises(RuntimeError, match="CPU geometry truth only"):
        crt.no_solve_guard()


def test_out_of_bounds_case_is_a_typed_refusal_without_meshing(tmp_path):
    from types import SimpleNamespace
    from hornlab_search.config import load_config
    cfg = load_config(_BASE_CFG)
    args = SimpleNamespace(no_mesh=False, existing_mesh=None, _mesh_root=tmp_path,
                           _resolved_cases=[{"name": "bad"}])
    case = {"name": "bad", "knobs": {"height_v_active_mm": 999.0, "L_forward_mm": 300.0,
                                     "area_mid_bias": 0.0, "aspect_timing_u50": 0.5}}
    rec = crt.analyse_case(cfg, case, args, {"mesher": crt.mesher_pin()})
    assert rec["status"] == "refused"
    assert rec["refusal"]["type"]
    assert not (tmp_path / "bad" / "mesh.msh").exists()


def test_law_only_mode_needs_no_mesher(c1, tmp_path):
    from types import SimpleNamespace
    cfg, shape, brief = c1
    args = SimpleNamespace(no_mesh=True, existing_mesh=None, _mesh_root=tmp_path,
                           _resolved_cases=[{"name": "c0"}])
    case = {"name": "c0", "knobs": {k: float(v) for k, v in cfg.seed_params.items()}}
    rec = crt.analyse_case(cfg, case, args, {"mesher": crt.mesher_pin()})
    assert rec["status"] == "law_only"
    assert rec["mesh"] is None
    assert rec["rank"]["surface_displacement"]["practical_rank"] == 4


# ------------------------------------------------------------------ real c0 regression (offline)


def test_real_c0_quarter_fixture_topology_and_surface_truth(c0):
    from hornlab_search.compare.mshio import read_msh
    cfg, shape, brief = c0
    mesh = read_msh(_FIXTURE / "mesh.msh")
    roles = crt.classify_roles(mesh, shape, brief)
    assert roles["tag_counts"] == {1: 8262, 2: 56}
    assert roles["source_tag"] == 2 and roles["wall_tag"] == 1
    assert 4400 <= len(roles["inner_tri"]) <= 4600

    topo = crt.mesh_topology(roles["xyz_mm"], mesh.tri,
                             crt._symmetry_axes(cfg.mesh.quadrants))
    assert topo["open_edges_off_symmetry_planes"] == 0
    assert topo["open_edges_on_symmetry_planes"] > 0
    assert topo["nonmanifold_edges"] == 0
    assert topo["winding_inconsistent_edges"] == 0

    inner = roles["xyz_mm"][mesh.tri[roles["inner_tri"]]]
    throat = crt.mesh_section(inner, 0.0)
    mouth = crt.mesh_section(inner, float(mesh_tip_z(inner)))
    assert throat["measurable"] and mouth["measurable"]
    assert throat["width_mm"] == pytest.approx(36.0, abs=1e-6)
    assert throat["height_mm"] == pytest.approx(36.0, abs=1e-6)
    assert mouth["width_mm"] == pytest.approx(580.0, abs=0.05)
    assert mouth["height_mm"] == pytest.approx(474.0, abs=0.05)

    src = crt._source_face(mesh, roles["xyz_mm"], roles["source_tri"])
    assert src["full_width_mm"] == pytest.approx(36.0, abs=1e-6)
    assert src["full_height_mm"] == pytest.approx(36.0, abs=1e-6)

    pts, recs = crt.analytic_samples(shape, brief)
    dev = crt._deviation_stats(pts, recs, inner, k=24)
    assert dev["measurable"] is True
    assert dev["p99_mm"] < 0.5
    assert dev["max_mm"] < 0.5


def mesh_tip_z(triangles):
    return float(np.max(triangles[:, :, 2]))


def test_real_c0_end_to_end_using_existing_mesh_matches_fixture(c0, tmp_path):
    from types import SimpleNamespace
    cfg, shape, brief = c0
    args = SimpleNamespace(no_mesh=False, existing_mesh=str(_FIXTURE), _mesh_root=tmp_path,
                           _resolved_cases=[{"name": "c0"}])
    case = {"name": "c0", "knobs": {k: float(v) for k, v in cfg.seed_params.items()}}
    rec = crt.analyse_case(cfg, case, args, {"mesher": crt.mesher_pin()})
    assert rec["status"] == "ok"
    assert rec["mesh"]["n_triangles"] == 8318
    assert rec["mesh"]["source_face"]["full_width_mm"] == pytest.approx(36.0, abs=1e-6)
    assert rec["mesh"]["terminal_z_delta_mm"] == pytest.approx(0.0, abs=1e-6)
    assert rec["mesh"]["symmetry"]["full_width_mm"] == pytest.approx(580.0, abs=1e-6)
    assert rec["fable_v2_rule"]["pass"] is True
    assert rec["deviation"]["p99_mm"] < 0.5
    assert rec["dense_diagnostic"]["max_mm"] < 0.5
    assert rec["mesh"]["topology"]["open_edges_off_symmetry_planes"] == 0
    # CSV/JSON writer is part of the CLI contract; exercise it offline.
    crt.write_outputs({"meta": {"tool": crt.TOOL}, "cases": [rec]}, tmp_path / "out.json")
    payload = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert payload["cases"][0]["status"] == "ok"
    assert (tmp_path / "out.csv").is_file()
