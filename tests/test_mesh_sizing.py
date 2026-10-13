"""Offline tests for mesh/sizing.py (04 tests 9-12)."""
from __future__ import annotations

import dataclasses
import math

import pytest

from hornlab_search.config import QUADRANT_FACTOR as CONFIG_QF
from hornlab_search.config import mesh_spec
from hornlab_search.constants import C_AIR
from hornlab_search.mesh import sizing
from hornlab_search.mesh.sizing import (QUADRANT_FACTOR, SYMMETRY_PLANE, dof_cap_for, estimate_dofs,
                                        f_max_for_dofs, max_triangles_for, res_mm_for,
                                        triangles_for)


# ------------------------------------------------------------------ test 9


def test_res_mm_for_matches_formula():
    r = res_mm_for(6.0, 10000)
    want = 1000 * 343 / (6 * 10000)
    assert want == pytest.approx(5.7167, abs=5e-5)
    assert abs(r["mouth"] - want) < 1e-9
    assert abs(r["rear"] - want) < 1e-9
    assert abs(r["throat"] - want / 2) < 1e-9
    assert C_AIR == 343.0                       # never 344


def test_res_mm_for_rejects_nonpositive():
    with pytest.raises(ValueError):
        res_mm_for(0.0, 1000)
    with pytest.raises(ValueError):
        res_mm_for(6.0, -1)


# ------------------------------------------------------------------ test 10


def test_symmetry_plane_and_quadrant_factor_agree():
    assert set(SYMMETRY_PLANE) == set(QUADRANT_FACTOR)
    assert SYMMETRY_PLANE["1"] == "yz+xz" and QUADRANT_FACTOR["1"] == 4
    assert (SYMMETRY_PLANE["1"], QUADRANT_FACTOR["1"]) == ("yz+xz", 4)
    assert SYMMETRY_PLANE["1234"] is None and QUADRANT_FACTOR["1234"] == 1
    assert SYMMETRY_PLANE["12"] == "xz" and QUADRANT_FACTOR["12"] == 2
    assert SYMMETRY_PLANE["14"] == "yz" and QUADRANT_FACTOR["14"] == 2


def test_quadrant_factor_agrees_with_config_copy():
    """config.py keeps its own copy for max_triangles; the two must never drift."""
    assert dict(CONFIG_QF) == dict(QUADRANT_FACTOR)


# ------------------------------------------------------------------ test 11


def test_max_triangles_for_contract_example():
    assert max_triangles_for(8000, "1", 0.5, 1.15) == math.ceil(8000 / 0.5 * 4 * 1.15) == 73600
    assert max_triangles_for(8000, "1234", 0.5, 1.15) == 18400
    assert max_triangles_for(16000, "12", 0.5, 1.15) == 73600
    assert max_triangles_for(8000, "1", 0.51, 1.15) == math.ceil(8000 / 0.51 * 4 * 1.15 - 1e-9)


def test_max_triangles_for_rejects_bad_input():
    with pytest.raises(ValueError):
        max_triangles_for(8000, "13", 0.5)
    with pytest.raises(ValueError):
        max_triangles_for(8000, "1", 0.0)


def test_estimate_dofs():
    assert estimate_dofs(16000, "1", 0.5) == 8000
    assert estimate_dofs(15686, "1", 0.51) == 8000
    assert estimate_dofs(0, "1234", 0.5) == 0
    with pytest.raises(ValueError):
        estimate_dofs(10, "x", 0.5)


# ------------------------------------------------------------------ test 12


@pytest.mark.parametrize("quadrants", ["1234", "12", "14", "1"])
@pytest.mark.parametrize("dpt", [0.5, 0.51])
def test_f_max_for_dofs_inverts_the_chain(quadrants, dpt):
    area_m2 = 0.5
    epw = 6.0
    for f in (2_000.0, 8_000.0, 13_000.0, 20_000.0):
        tri = triangles_for(area_m2, epw, f, quadrants)
        dofs = tri * dpt
        back = f_max_for_dofs(dofs, area_m2, epw, quadrants, dpt)
        assert back == pytest.approx(f, rel=0.005)


def test_f_max_for_dofs_contract_arithmetic():
    """01_CONTRACTS section 6 table: a 0.125 m^2 quarter surface at epw 6 and 8000 dofs buys
    'about 13 kHz' with the mesher's 2.3 triangles per h^2."""
    f = f_max_for_dofs(8000, 0.125 * 4, 6.0, "1", 0.5)
    assert 11_000 < f < 15_000
    # more dofs, higher frequency; bigger horn, lower frequency; more epw, lower frequency
    assert f_max_for_dofs(16000, 0.5, 6.0, "1", 0.5) > f
    assert f_max_for_dofs(8000, 2.0, 6.0, "1", 0.5) < f
    assert f_max_for_dofs(8000, 0.5, 8.0, "1", 0.5) < f


def test_f_max_scales_as_sqrt_dofs():
    a = f_max_for_dofs(8000, 0.5, 6.0, "1", 0.51)
    b = f_max_for_dofs(32000, 0.5, 6.0, "1", 0.51)
    assert b / a == pytest.approx(2.0, rel=1e-9)


def test_f_max_for_dofs_rejects_nonpositive():
    for args in [(0, 0.5, 6, "1", 0.5), (8000, 0, 6, "1", 0.5), (8000, 0.5, 0, "1", 0.5),
                 (8000, 0.5, 6, "1", 0)]:
        with pytest.raises(ValueError):
            f_max_for_dofs(*args)


# ------------------------------------------------------------------ caps come from Config


def test_dof_cap_for_reads_the_config_not_a_constant(cfg):
    for mode in ("screen", "verify", "final"):
        assert dof_cap_for(None, cfg.mesh, mode) == cfg.mesh.dof_cap(mode)
    changed = dataclasses.replace(cfg.mesh, dof_cap_screen=5000)
    assert dof_cap_for(None, changed, "screen") == 5000


def test_dof_cap_for_infers_mode_from_both_forward_formulas(cfg):
    """Infers the cap from MeshSpec.max_triangles, whether it came from config.mesh_spec
    (ceil(2*cap*qf*slack)) or from sizing.max_triangles_for (ceil(cap/dpt*qf*slack))."""
    qf = QUADRANT_FACTOR[cfg.mesh.quadrants]
    for mode in ("screen", "verify", "final"):
        cap = cfg.mesh.dof_cap(mode)
        ms = mesh_spec(mode, cfg)
        assert dof_cap_for(ms, cfg.mesh) == cap
        ms2 = dataclasses.replace(ms, max_triangles=max_triangles_for(
            cap, cfg.mesh.quadrants, cfg.mesh.dof_per_triangle, cfg.mesh.max_triangle_slack))
        assert dof_cap_for(ms2, cfg.mesh) == cap
    # a hand-built spec falls back to inverting max_triangles_for
    ms3 = dataclasses.replace(mesh_spec("screen", cfg), max_triangles=max_triangles_for(
        12345, cfg.mesh.quadrants, cfg.mesh.dof_per_triangle, cfg.mesh.max_triangle_slack))
    assert abs(dof_cap_for(ms3, cfg.mesh) - 12345) <= 1
    assert qf == 4


def test_example_config_caps_are_not_hardcoded_in_sizing(cfg):
    import inspect
    src = inspect.getsource(sizing)
    for banned in ("8000", "16000", "24000"):
        assert banned not in src.replace("8000 dofs", "")   # only prose may mention a number
