"""Cone mid horn + axe head (``tools/cad/plughorn.py``) through the ``cad`` route (2026-10-28).

Real CAD + real gmsh, offline, CPU only. The defaults are the Evo 7SH numbers read from Funktion-One's
3D model; the pins below are those CAD values, so a geometry regression shows up as a number.
"""
from __future__ import annotations

from dataclasses import asdict, replace

import pytest

from conftest import EXAMPLES, requires_build123d, requires_mesher
from hornlab_search.config import load_config
from hornlab_search.design.generated import plughorn_params
from hornlab_search.design.space import DesignSpace
from hornlab_search.mesh import build, step_build
from hornlab_search.types import GeometryInvalidError, MeshSpec

pytestmark = [requires_build123d, requires_mesher]

FOLDER = EXAMPLES / "typologies" / "cone_plughorn_2026-10-28"
EVO7 = FOLDER / "cone_plughorn__evo7sh_narrow.yaml"
EVO2 = FOLDER / "cone_plughorn__evo2sh_wide.yaml"
COARSE = MeshSpec(epw=6.0, f_max_hz=1200.0, quadrants="1234", max_triangles=10**6, allow_large_mesh=False)


@pytest.fixture(scope="module")
def tool():
    return step_build.load_cad_tool(tool=step_build.PLUGHORN_TOOL)


def test_defaults_reproduce_the_evo7sh_cad(tool):
    p = tool.DEFAULTS
    assert p.plug_corner_d() == pytest.approx(258.8, abs=0.1)          # CAD corner depth (planar faces)
    d = p.derived()
    assert d["front_opening_mm"] == pytest.approx([559.6, 383.6], abs=0.1)
    assert d["throat_area_cm2"] == pytest.approx(223.6, abs=0.2)
    assert d["plug_clearance_mm"] >= p.plug_gap_mm
    assert 4.0 < d["compression_ratio"] < 6.0


def test_refusals(tool):
    with pytest.raises(ValueError, match="clearance"):
        replace(tool.DEFAULTS, plug_base_x_mm=88.0).validate()
    with pytest.raises(ValueError, match="widen"):
        replace(tool.DEFAULTS, mouth_side_x_mm=300.0).validate()
    with pytest.raises(ValueError, match="unknown"):
        tool.params_from_recipe({"tool": "plughorn", "nope": 1.0})


def test_step_build_validates_keys(tool):
    recipe = {"tool": "plughorn", **asdict(tool.DEFAULTS)}
    step_build.validate_cad_params(recipe)
    with pytest.raises(step_build.CadParamsError, match="unknown"):
        step_build.validate_cad_params({**recipe, "bogus": 1.0})
    missing = dict(recipe)
    missing.pop("length_mm")
    with pytest.raises(step_build.CadParamsError, match="missing"):
        step_build.validate_cad_params(missing)


def test_generator_knobs_and_envelope():
    cfg = load_config(EVO7)
    cad = plughorn_params(cfg.generator, {"plug_tip_x_mm": 190.0}, cfg.brief)["cad"]
    assert cad["tool"] == "plughorn" and cad["plug_tip_x_mm"] == 190.0
    assert set(cad) - {"tool"} == set(step_build.load_cad_tool(tool="plughorn").KEYS)
    with pytest.raises(ValueError):
        plughorn_params(cfg.generator, {"scale": 1.3}, cfg.brief)       # past the brief envelope


def test_examples_load_and_seed():
    for path in (EVO7, EVO2):
        space = DesignSpace.from_config(load_config(path))
        assert "cad" in space.seed.params, path.name


@pytest.mark.parametrize("path", [EVO2])
def test_mesh_build_one_driver_face(path, tmp_path):
    cfg = load_config(path)
    res = build.build_mesh(DesignSpace.from_config(cfg).seed, COARSE, cfg, tmp_path)
    summ = build.read_msh_summary(res.path)
    assert summ["tags"].get(2, 0) > 0 and summ["tags"].get(1, 0) > 0
    assert (tmp_path / "cad" / "plughorn.step").exists()


def test_quadrants_must_be_full(tmp_path):
    cfg = load_config(EVO2)
    with pytest.raises(GeometryInvalidError, match="FULL"):
        build.build_mesh(DesignSpace.from_config(cfg).seed, replace(COARSE, quadrants="1"), cfg, tmp_path)


MORPH = FOLDER / "cone_plughorn__morph_narrow_10in.yaml"


def _morph_params(tool, **changes):
    import yaml
    cfg = yaml.safe_load(MORPH.read_text(encoding="utf-8"))
    values = {**cfg["generator"]["fixed"], **cfg["seed_params"], **changes}
    return replace(tool.DEFAULTS, **values).resolve_morph()


def test_morph_seed_reproduces_the_cad(tool):
    p, raw = _morph_params(tool), tool.DEFAULTS
    for k in ("throat_side_x_mm", "mouth_side_x_mm", "mouth_top_y_mm", "front_side_x_mm", "plug_tip_x_mm",
              "plug_top_d_mm", "plug_base_x_mm"):
        assert getattr(p, k) == pytest.approx(getattr(raw, k), abs=1.0), k


def test_morph_knobs_move_what_they_say(tool):
    p = _morph_params(tool, m_wall_angle_h_deg=28.0, m_wall_angle_v_deg=14.0)
    d = p.derived()
    assert d["side_wall_angle_deg"] == pytest.approx(28.0, abs=0.1)
    assert d["top_wall_angle_deg"] == pytest.approx(14.0, abs=0.1)
    seed = _morph_params(tool).derived()
    assert d["k_law_pattern_h_hz"] < seed["k_law_pattern_h_hz"]          # bigger mouth holds the pattern lower
    hi = _morph_params(tool, m_compression_ratio=7.0, m_plug_base_frac=0.80)
    assert hi.throat_side_x_mm < _morph_params(tool).throat_side_x_mm      # more compression = smaller throat
    big = _morph_params(tool, cone_r_mm=125.0, cone_depth_mm=52.0, post_r_mm=25.0, m_bowl_auto=1.0)
    assert big.derived()["compression_ratio"] == pytest.approx(seed["compression_ratio"], rel=0.03)
    assert big.throat_side_x_mm > _morph_params(tool).throat_side_x_mm     # the throat regrows for a bigger cone
    with pytest.raises(ValueError, match="clearance"):                       # a throat gap that closes is refused
        _morph_params(tool, m_compression_ratio=8.0).validate()
