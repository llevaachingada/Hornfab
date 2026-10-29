"""C4 (objective v5): the round-throat refusal happens AFTER the mesh and BEFORE any solver call.

Offline, CPU only. A synthetic quarter mesh is written with meshio (the same shape the real mesher
writes), so the REAL ``mesh.throat_check`` reads it; the backend records whether it was ever asked
to solve. A candidate whose driven throat is not the brief driver's round exit becomes a
deterministic invalid candidate (``invalid_geometry``), never a solver failure. A run without a
brief driver is never checked.
"""
from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

meshio = pytest.importorskip("meshio")

from hornlab_search.config import _validate_objective_block  # noqa: E402
from hornlab_search.design.space import DesignSpace  # noqa: E402
from hornlab_search.objective.scalar_v5 import V5_ALL_KEYS, V5_WEIGHTED_KEYS  # noqa: E402
from hornlab_search.search import evaluate as ev_mod  # noqa: E402
from hornlab_search.search.evaluate import make_context  # noqa: E402
from hornlab_search.types import GeometryInvalidError, MeshResult  # noqa: E402
from test_search_support import LIBS, SyntheticBackend  # noqa: E402

EXIT_RADIUS_MM = 18.0                      # 36 mm exit -> the round quarter mesh below
BRIEF = {"name": "throat", "driver": {"exit_radius_mm": EXIT_RADIUS_MM, "exit_angle_deg": 5.0},
         "envelope": {"max_mouth_w_mm": 10000.0, "max_mouth_h_mm": 10000.0,
                      "max_depth_mm": 10000.0}}
ONES = {k: 1.0 for k in V5_WEIGHTED_KEYS}


def _v5_cfg(smoke_cfg, brief):
    block = _validate_objective_block({"version": 5, "tolerances": ONES}, "test.yaml")
    return dataclasses.replace(smoke_cfg, objective_version=5, objective_params=block, brief=brief)


def _quarter_mesh(path: Path, rx_mm: float, ry_mm: float, n: int = 24) -> Path:
    """Quarter opening (x, y >= 0) as a fan of tag-2 triangles, plus one tag-1 wall triangle."""
    t = np.linspace(0.0, math.pi / 2, n + 1)
    x = rx_mm * 1e-3 * np.cos(t)
    y = ry_mm * 1e-3 * np.sin(t)
    pts = np.vstack([[0.0, 0.0, 0.0], np.column_stack([x, y, np.zeros_like(x)]),
                     [0.05, 0.05, 0.05]])
    tri = np.array([[0, i, i + 1] for i in range(1, n + 1)] + [[1, n + 1, n + 2]])
    tag = np.array([2] * n + [1])
    meshio.write(path, meshio.Mesh(pts, [("triangle", tri)],
                                   cell_data={"gmsh:physical": [tag], "gmsh:geometrical": [tag]}),
                 file_format="gmsh22", binary=False)
    return path


def _install_mesh(monkeypatch, tmp_path, rx_mm, ry_mm, backend):
    msh = _quarter_mesh(tmp_path / "mesh.msh", rx_mm, ry_mm)

    def build_mesh(design, mesh_spec, cfg, out_dir, **kw):
        backend._params = dict(design.params)
        backend.designs.append(design.hash())
        return MeshResult(path=str(msh), n_triangles=25, n_dof=None, quadrants="1",
                          symmetry_plane="yz+xz", res_mm={"throat": 3.0, "mouth": 6.0},
                          bbox_m=(0.0, 0.0, 0.0, 0.036, 0.036, 0.1), seconds=0.01)

    monkeypatch.setattr(ev_mod, "build_mesh", build_mesh)
    return msh


def _evaluate(cfg, tmp_path, backend):
    space = DesignSpace.from_config(cfg)
    ctx = make_context(cfg, None, lib_shas=LIBS)
    return ev_mod.evaluate(space.seed, space, cfg, "screen", tmp_path / "run", None, backend,
                           ctx=ctx)


def test_stretched_throat_raises_before_the_solver(smoke_cfg, tmp_path, monkeypatch):
    cfg = _v5_cfg(smoke_cfg, BRIEF)
    be = SyntheticBackend()
    msh = _install_mesh(monkeypatch, tmp_path, 13.0, 18.0, be)      # 26 x 36 ellipse
    mesh = MeshResult(path=str(msh), n_triangles=25, n_dof=None, quadrants="1",
                      symmetry_plane="yz+xz", res_mm={}, bbox_m=(0,) * 6, seconds=0.0)
    with pytest.raises(GeometryInvalidError, match="driver exit"):
        ev_mod._refuse_if_throat_misfits(mesh, cfg)

    ev = _evaluate(cfg, tmp_path, be)
    assert ev.error.startswith("invalid_geometry")
    assert "driver exit" in ev.error
    assert be.calls == 0, "the solver must never be asked to run"
    assert ev.mesh is not None and ev.objective == 1000.0


def test_round_throat_passes_and_reaches_the_v5_scorer(smoke_cfg, tmp_path, monkeypatch):
    cfg = _v5_cfg(smoke_cfg, BRIEF)
    be = SyntheticBackend()
    _install_mesh(monkeypatch, tmp_path, 18.0, 18.0, be)            # 36 mm round
    ev = _evaluate(cfg, tmp_path, be)
    assert not ev.error and be.calls == 1
    assert set(ev.terms) == set(V5_ALL_KEYS)
    assert "lfp20_hz" in ev.terms and "rez_min_from_fx" in ev.terms


def test_run_without_a_brief_driver_is_never_checked(smoke_cfg, tmp_path, monkeypatch):
    be = SyntheticBackend()
    _install_mesh(monkeypatch, tmp_path, 13.0, 18.0, be)            # would fail the check
    ev = _evaluate(smoke_cfg, tmp_path, be)                          # no brief at all
    assert not ev.error and be.calls == 1
    # A brief that carries no driver is equally exempt.
    be2 = SyntheticBackend()
    cfg = _v5_cfg(smoke_cfg, {"name": "nodriver"})
    _install_mesh(monkeypatch, tmp_path, 13.0, 18.0, be2)
    ev2 = _evaluate(cfg, tmp_path, be2)
    assert not ev2.error and be2.calls == 1
