"""WP4 (throughput packet): opt-in curvature mesh sizing. Offline plumbing + default-unchanged."""
from __future__ import annotations

import dataclasses

import pytest
import yaml

from conftest import EXAMPLES, requires_mesher
from hornlab_search import config as config_mod
from hornlab_search.config import ConfigError, load_config, mesh_spec
from hornlab_search.mesh import step_build
from hornlab_search.types import MeshSpec, _canon, _hash

RES = {"throat": 3.0, "mouth": 6.0, "rear": 6.0}


def _old_hash(m: MeshSpec) -> str:
    """The hash input EXACTLY as it was before the curvature field existed."""
    return _hash(_canon({"epw": m.epw, "f_max_hz": m.f_max_hz, "quadrants": m.quadrants,
                         "max_triangles": m.max_triangles, "allow_large_mesh": m.allow_large_mesh}))


def test_default_mesh_hash_is_byte_identical_to_the_pre_change_hash():
    m = MeshSpec(epw=6.0, f_max_hz=10000.0, quadrants="1", max_triangles=12345)
    assert m.curvature_npts == 0.0
    assert m.hash() == _old_hash(m)


def test_non_default_curvature_changes_the_hash():
    m = MeshSpec(epw=6.0, f_max_hz=10000.0, quadrants="1", max_triangles=12345)
    assert dataclasses.replace(m, curvature_npts=12.0).hash() != m.hash()
    assert dataclasses.replace(m, curvature_npts=12.0).hash() != \
        dataclasses.replace(m, curvature_npts=8.0).hash()


def test_example_configs_default_to_off_and_keep_their_mesh_hash():
    for name in ("osse_baseline.yaml", "search_smoke.yaml"):
        cfg = load_config(EXAMPLES / name)
        assert cfg.mesh.curvature_npts == 0.0
        ms = mesh_spec("screen", cfg)
        assert ms.curvature_npts == 0.0 and ms.hash() == _old_hash(ms)


def test_config_plumbs_curvature_into_the_mesh_spec(tmp_path):
    raw = yaml.safe_load((EXAMPLES / "osse_baseline.yaml").read_text(encoding="utf-8"))
    raw["mesh"]["curvature_npts"] = 12
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    cfg = load_config(p)
    assert cfg.mesh.curvature_npts == 12.0
    base = mesh_spec("screen", load_config(EXAMPLES / "osse_baseline.yaml"))
    ms = mesh_spec("screen", cfg)
    assert ms.curvature_npts == 12.0 and ms.hash() != base.hash()


@pytest.mark.parametrize("bad", [-1, "x", float("nan"), 1000])
def test_bad_curvature_values_are_refused(tmp_path, bad):
    raw = yaml.safe_load((EXAMPLES / "osse_baseline.yaml").read_text(encoding="utf-8"))
    raw["mesh"]["curvature_npts"] = bad
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError, match="curvature_npts"):
        load_config(p)


def test_default_gmsh_options_are_exactly_todays():
    assert step_build.sizing_options(RES) == {"Mesh.MeshSizeFromCurvature": 0.0}
    assert step_build.sizing_options(RES, 0) == {"Mesh.MeshSizeFromCurvature": 0.0}


def test_opt_in_options_clamp_between_throat_and_wavelength_ceiling():
    opts = step_build.sizing_options(RES, 12.0)
    assert opts == {"Mesh.MeshSizeFromCurvature": 12.0, "Mesh.MeshSizeMax": 6.0,
                    "Mesh.MeshSizeMin": 3.0}


@requires_mesher
def test_mesher_installed_smoke_import():
    import hornlab_mesher  # noqa: F401
    assert callable(step_build.build_mesh_from_cad)
