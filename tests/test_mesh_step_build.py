"""WP14: ``cad`` recipe -> labelled STEP -> ``.msh`` in METRES (``mesh/step_build.py``).

Real CAD + real gmsh, offline, CPU only. The suite builds ONE tiny 2x2 multicell and
shares it; the full 3x3 example config is only loaded/validated here (the focused 3x3
mesh build is the validation-run step, and it is far too slow/big for a unit test).
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from conftest import EXAMPLES, requires_build123d, requires_mesher
from hornlab_search.config import load_config, mesh_spec
from hornlab_search.design import families
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build, step_build, topology
from hornlab_search.types import (Design, GeometryInvalidError, MeshResult, MeshSpec)

pytestmark = [requires_build123d, requires_mesher]

EXAMPLE = EXAMPLES / "typologies" / "multicell_3x3.yaml"

#: A SHORT, COARSE multicell: 2x2 cells, 120 mm long, one resolution step above the
#: 3x3 recipe. epw 10 at 2 kHz is the point where the gmsh max-edge overshoot still
#: leaves the whole mesh valid at f_max (see the module's frequency-limit notes).
TINY = dict(
    tool="multicell",
    n_h=2,
    n_v=2,
    alpha_total_deg=60.0,
    beta_total_deg=60.0,
    length_mm=120.0,
    z_s_mm=30.0,
    r_throat_mm=12.7,
    septum_mm=2.0,
    throat_wall_mm=3.0,
    flare_hz=500.0,
)
TINY_SPEC = MeshSpec(epw=10.0, f_max_hz=2000.0, quadrants="1234",
                     max_triangles=10**6, allow_large_mesh=False)


def _triangle_block(mesh):
    index = [i for i, block in enumerate(mesh.cells) if block.type in ("triangle", "triangle3")][0]
    return np.asarray(mesh.points, dtype=float), np.asarray(mesh.cells[index].data, np.int64), \
        np.asarray(mesh.cell_data["gmsh:physical"][index], np.int64)


@pytest.fixture(scope="module")
def cfg():
    return load_config(EXAMPLE)


@pytest.fixture(scope="module")
def tiny(cfg, tmp_path_factory):
    """One shared 2x2 build: (MeshResult, out_dir, Design)."""
    design = Design("FREEFORM", {"cad": dict(TINY)})
    out = tmp_path_factory.mktemp("wp14_step_mesh")
    result = build.build_mesh(design, TINY_SPEC, cfg, out, mode="screen")
    return result, out, design


@pytest.fixture(scope="module")
def tiny_meta(tiny):
    _result, out, _design = tiny
    return json.loads((out / "mesh_meta.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ (a) build + units


def test_mesh_builds_in_metres_with_both_tags(tiny):
    result, out, design = tiny
    assert isinstance(result, MeshResult)
    assert result.n_triangles > 200
    assert result.quadrants == "1234"
    assert result.symmetry_plane is None          # sizing.SYMMETRY_PLANE["1234"]
    assert result.n_dof is None                   # only a solve reports dofs
    assert set(result.res_mm) == {"throat", "mouth", "rear"}
    assert result.res_mm["throat"] == pytest.approx(result.res_mm["mouth"] / 2.0)

    summary, xyz, tri = build.read_msh_summary(result.path, return_arrays=True)
    assert summary["tags"].get(step_build.WALL_TAG, 0) > 0      # 1 = SD1G0
    assert summary["tags"].get(step_build.DRIVER_TAG, 0) > 0    # 2 = SD1D1001
    assert summary["tag_names"][1] == "SD1G0"
    assert summary["tag_names"][2] == "SD1D1001"
    # METRES, proven: the mouth is 2*120*tan(30) = 138.6 mm = 0.1386 m. Millimetres
    # would land at 138.6 and the build's bbox guard would already have refused.
    extent = max(summary["bbox_m"][3] - summary["bbox_m"][0],
                 summary["bbox_m"][4] - summary["bbox_m"][1],
                 summary["bbox_m"][5] - summary["bbox_m"][2])
    assert 0.10 < extent < 0.20
    assert result.bbox_m == summary["bbox_m"]
    assert tuple(round(v, 12) for v in result.bbox_m) == \
        tuple(round(v, 12) for v in summary["bbox_m"])

    report = topology.check_surface(xyz, tri, None)
    assert report.nonmanifold_edges == 0
    assert report.bad_open_edges == 0
    assert report.near_coincident == 0

    # the generated (not referenced) labelled STEP sits beside the mesh
    step = out / "cad" / step_build.STEP_FILENAME
    assert step.is_file() and step.stat().st_size > 10_000
    assert (out / "mesh.msh").is_file()

    # the dof/symmetry guards ran in the route: a reduced spec is refused outright
    with pytest.raises(GeometryInvalidError, match="FULL solid"):
        step_build.build_mesh_from_cad(
            dict(TINY), MeshSpec(epw=10.0, f_max_hz=2000.0, quadrants="1",
                                 max_triangles=10**6), cfg, out / "reduced", mode="screen")


# ------------------------------------------------------------------ (b) frequency


def test_frequency_validation_passes_at_recipe_fmax(tiny, tiny_meta):
    result, _out, _design = tiny
    from hornlab_mesher.mesh_validation import mesh_frequency_validation
    from hornlab_mesher.step_mapping import StepFaceGroup, StepLabelSelector
    from hornlab_mesher.step_prepare import OccSurfaceRole

    recorded = tiny_meta["cad"]["frequency_validation"]
    assert recorded["requested_max_frequency_hz"] == pytest.approx(TINY_SPEC.f_max_hz)
    assert recorded["status"] == "valid"
    assert recorded["invalid_sources"] == []
    assert recorded["per_source"]["driver"]["effective_max_valid_frequency_hz"] >= \
        TINY_SPEC.f_max_hz

    # Re-run the mesher's validator on the WRITTEN .msh, in metres (unit_scale 1.0):
    # this doubles as proof the file on disk really is metres.
    import meshio
    points, triangles, tags = _triangle_block(meshio.read(result.path))
    specs = [StepFaceGroup("driver", StepLabelSelector("driver"),
                           OccSurfaceRole("source"), tag=2,
                           resolution_mm=TINY_SPEC.epw)]
    report = mesh_frequency_validation(
        points, triangles, tags, specs,
        unit_scale_to_m=1.0,
        requested_max_frequency_hz=TINY_SPEC.f_max_hz,
    )
    assert report["status"] == "valid"
    assert report["global_status"] == "valid"
    assert report["global_max_edge_m"] < 0.2                      # metres, not mm
    assert report["per_source"]["driver"]["triangle_count"] == int(
        (tags == 2).sum())


# ------------------------------------------------------------------ (c) driver face


def test_driver_face_round_trip_is_exactly_one_group(tiny, tiny_meta):
    _result, out, _design = tiny
    cad = tiny_meta["cad"]
    assert cad["face_inventory"]["driver"] == 1
    assert cad["face_inventory"]["wall"] == cad["wall_surfaces"] > 0
    assert cad["gmsh_surfaces"] == cad["driver_surfaces"] + cad["wall_surfaces"]
    assert cad["driver_surfaces"] == 1
    assert cad["physical_tags"] == {"1": "SD1G0", "2": "SD1D1001"}

    # the STEP itself, read back through the tool's own round-trip check
    tool = step_build.load_cad_tool()
    inventory = tool.read_face_inventory(out / "cad" / step_build.STEP_FILENAME)
    assert inventory == cad["face_inventory"]

    summary = build.read_msh_summary(_result.path)
    # exactly one driver FACE (one surface) -> one contiguous tag-2 element set
    assert summary["tags"][2] > 0
    assert summary["tags"][2] < summary["tags"][1]


def test_provenance_echo_shape(tiny, tiny_meta):
    result, _out, design = tiny
    assert tiny_meta["key"] == f"{design.hash()}-{TINY_SPEC.hash()}"
    cad = tiny_meta["cad"]
    assert cad["tool"] == step_build.CAD_TOOL_RELPATH
    assert len(cad["tool_sha256"]) == 64
    assert len(cad["step_sha256"]) == 64
    assert cad["recipe"] == TINY
    assert cad["step_bytes"] > 10_000
    assert cad["solid"]["solids"] == 1
    assert cad["solid"]["all_shells_closed"] is True
    assert cad["solid"]["driver_faces"] == 1
    assert set(cad["frequency_validation"]) >= {
        "status", "global_status", "per_source", "warnings", "requested_max_frequency_hz"}
    assert set(cad["repair"]) >= {"degenerate_triangles_removed", "welded_vertices"}
    assert set(cad["topology"]) >= {"triangles", "free_edges", "nonmanifold_edges"}
    assert tiny_meta["result"]["n_triangles"] == result.n_triangles


def test_same_recipe_same_mesh_bytes(cfg, tmp_path):
    design = Design("FREEFORM", {"cad": dict(TINY)})
    first = build.build_mesh(design, TINY_SPEC, cfg, tmp_path / "a", mode="screen")
    second = build.build_mesh(design, TINY_SPEC, cfg, tmp_path / "b", mode="screen")
    assert first.n_triangles == second.n_triangles
    assert first.bbox_m == second.bbox_m
    assert _sha256(first.path) == _sha256(second.path)


def _sha256(path) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# ------------------------------------------------------------------ (d) recipe errors


@pytest.mark.parametrize("block,needle", [
    ({**TINY, "bogus": 1}, "unknown key"),
    ({k: v for k, v in TINY.items() if k != "flare_hz"}, "missing required key"),
    ({**TINY, "septum_mm": 1.4}, "septum_mm"),
    ({**TINY, "tool": "cadquery"}, "cad.tool"),
    ({**TINY, "n_h": 1}, "n_h"),
    ({**TINY, "n_v": 9}, "n_v"),
    ({**TINY, "n_h": 2.5}, "n_h"),
    ({**TINY, "alpha_total_deg": 180.0}, "alpha_total_deg"),
    ({**TINY, "length_mm": 0.0}, "length_mm"),
    ({**TINY, "z_s_mm": 200.0}, "z_s_mm"),
    ({**TINY, "r_throat_mm": -1.0}, "r_throat_mm"),
    ({**TINY, "throat_wall_mm": 0.0}, "throat_wall_mm"),
    ({**TINY, "flare_hz": -5.0}, "flare_hz"),
    ("not a mapping", "mapping"),
])
def test_cad_block_validation_errors(block, needle):
    with pytest.raises(step_build.CadParamsError, match=needle):
        step_build.validate_cad_params(block)
    with pytest.raises(GeometryInvalidError, match="FREEFORM.cad"):
        families.validate(Design("FREEFORM", {"cad": block}))


def test_cad_design_carries_only_cad_and_stays_freeform():
    with pytest.raises(GeometryInvalidError, match="not a cad design key"):
        families.validate(Design("FREEFORM", {"cad": dict(TINY), "L_mm": 120.0}))
    with pytest.raises(GeometryInvalidError, match="must use family FREEFORM"):
        families.validate(Design("OSSE", {"cad": dict(TINY)}))


# ------------------------------------------------------------------ (e) STEP export refusal


def test_export_step_refuses_grid_and_cad_designs(tmp_path):
    grid_cfg = load_config(EXAMPLES / "typologies" / "grid_ellipse.yaml")
    grid_design = DesignSpace.from_config(grid_cfg).seed
    assert "grid" in grid_design.params
    with pytest.raises(GeometryInvalidError, match="GRID design"):
        build.export_step(grid_design, mesh_spec("screen", grid_cfg), grid_cfg,
                          tmp_path / "grid.step")
    assert not (tmp_path / "grid.step").exists()

    cad_cfg = load_config(EXAMPLE)
    cad_design = DesignSpace.from_config(cad_cfg).seed
    with pytest.raises(GeometryInvalidError, match="cad design"):
        build.export_step(cad_design, mesh_spec("screen", cad_cfg), cad_cfg,
                          tmp_path / "cad.step")
    assert not (tmp_path / "cad.step").exists()


# ------------------------------------------------------------------ (f) example config


def test_example_config_loads_and_validates(cfg):
    assert cfg.name == "multicell_3x3"
    assert cfg.family == "FREEFORM"
    assert cfg.generator is None                     # a cad config is not a generator config
    assert cfg.mesh.quadrants == "1234"
    assert cfg.target_raw["band_hi_hz"] == 4000.0
    assert mesh_spec("screen", cfg).f_max_hz == 4000.0
    seed = DesignSpace.from_config(cfg).seed
    assert list(seed.params) == ["cad"]
    recipe = seed.params["cad"]
    assert set(recipe) == set(step_build.CAD_KEYS)
    families.validate(seed)                          # the cad branch, not FREEFORM anchors

    # the recipe IS the CAD lane's proven default configuration
    tool = step_build.load_cad_tool()
    for key, value in recipe.items():
        if key == "tool":
            continue
        assert getattr(tool.DEFAULTS, key) == value, key
    assert recipe["n_h"] % 2 == 1 and recipe["n_v"] % 2 == 1   # axis cell in air, not septum
