"""Shared fakes for the search/report/CLI tests (not tests themselves): a synthetic backend whose
Response depends smoothly on the design, and a stand-in for ``build_mesh`` so no mesher or GPU is
needed. Import from tests with ``from test_search_support import ...``.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np

from conftest import fibonacci_sphere
from hornlab_search.search.selftest import icosphere, write_sphere_msh
from hornlab_search.solve.base import arc_angles_deg
from hornlab_search.types import (GeometryInvalidError, MeshResult, MeshTooLargeError, Response,
                                  SolveOutcome)

LIBS = {k: "0123456789abcdef" for k in ("hornlab_mesher", "hornlab_beat_bem", "hornlab_bempp_bem",
                                        "hornlab_plots", "hornlab_search")}


def fast_cfg(cfg, **search_kw):
    """A copy of ``cfg`` whose CMA tolfun cannot stop a short test run early."""
    s = dataclasses.replace(cfg.search, tolfun=1e-12, **search_kw)
    return dataclasses.replace(cfg, search=s)


def fake_build_mesh(invalid_if=None, too_large_if=None):
    """Stand-in for ``mesh.build.build_mesh`` with the same signature. Writes a 12-node icosphere
    .msh (so trace packaging has a real file) and a mesh_meta.json."""
    def build_mesh(design, mesh_spec, cfg, out_dir, *, mode=None, cache_dir=None):
        p = design.params
        if invalid_if and invalid_if(p):
            raise GeometryInvalidError("synthetic: illegal geometry")
        if too_large_if and too_large_if(p):
            raise MeshTooLargeError("synthetic: too many dofs")
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        pts, tris = icosphere(0.1, 0)
        msh = out_dir / "mesh.msh"
        write_sphere_msh(pts, tris, msh)
        (out_dir / "mesh_meta.json").write_text(json.dumps({
            "key": "k", "summary": {"area_m2": 0.1}, "mesher_config": {"mesh": {}}}))
        return MeshResult(path=str(msh), n_triangles=int(len(tris)), n_dof=None,
                          quadrants=mesh_spec.quadrants, symmetry_plane="yz+xz",
                          res_mm={"throat": 3.0, "mouth": 6.0, "rear": 6.0},
                          bbox_m=(0.0, 0.0, 0.0, 0.3, 0.2, 0.25), seconds=0.01)
    return build_mesh


def synthetic_response(params: dict, freqs, angle_count: int = 73, balloon_points: int = 64) -> Response:
    """Gaussian beam whose -6 dB half-widths come from the design: horizontal = a_deg, vertical =
    a_deg / aspect_ratio, slowly narrowing with frequency; ripple grows away from s = 0.5."""
    f = np.asarray(freqs, dtype=float)
    ang = arc_angles_deg(angle_count)
    a = float(params.get("a_deg", 37.5))
    ar = float(params.get("aspect_ratio", 1.25))
    n = float(params.get("n", 4.0))
    s = float(params.get("s", 0.7))
    narrow = 1.0 - 0.10 * np.log10(f / 2000.0) * (n / 4.0)
    wh = a * narrow
    wv = (a / ar) * narrow
    rip = 0.6 * abs(s - 0.5)

    def pat(w):
        # amplitude 0.5 (-6.0206 dB) exactly at theta = w
        return 20 * np.log10(np.exp(-np.log(2.0) * (ang[None, :] / w[:, None]) ** 2))

    ripple = rip * np.sin(np.radians(ang) * 6.0)[None, :]
    spl_h = 94.0 + pat(wh) + ripple
    spl_v = 94.0 + pat(wv) + ripple
    spl_h[:, angle_count // 2] = 94.0
    spl_v[:, angle_count // 2] = 94.0
    dirs = fibonacci_sphere(balloon_points)
    th_x = np.degrees(np.arctan2(dirs[:, 0], np.maximum(dirs[:, 2], 1e-3)))
    th_y = np.degrees(np.arctan2(dirs[:, 1], np.maximum(dirs[:, 2], 1e-3)))
    bal = np.empty((f.size, balloon_points))
    for i in range(f.size):
        bal[i] = 94.0 - 20 * np.log10(np.e) * np.log(2.0) * ((th_x / wh[i]) ** 2 + (th_y / wv[i]) ** 2)
    bal = np.maximum(bal, 94.0 - 60.0)
    z = (0.5 + 0.1 * np.log10(f / 1000.0)) + 0.2j
    return Response(freqs_hz=f, h_angles_deg=ang.copy(), v_angles_deg=ang.copy(), spl_h_db=spl_h,
                    spl_v_db=spl_v, balloon_dirs=dirs, spl_balloon_db=bal, z_throat=z,
                    backend="synthetic", n_dof=1234, meta={})


class SyntheticBackend:
    """Satisfies the Backend protocol. ``fail_on`` maps a 1-based solve number to an exception (or
    an ``ok=False`` outcome when given the string 'fail'). ``solve_traced`` exists so the trace
    path of ``evaluate`` can be exercised."""
    name = "synthetic"

    def __init__(self, fail_on: dict | None = None, seconds: float = 0.01):
        self.calls = 0
        self.traced_calls = 0
        self.warmed = 0
        self.released = 0
        self.fail_on = fail_on or {}
        self.seconds = seconds
        self.designs = []

    def available(self):
        return True, "synthetic"

    def warm(self):
        self.warmed += 1

    def release(self):
        self.released += 1

    def _solve(self, mesh, spec):
        self.calls += 1
        mode = self.fail_on.get(self.calls)
        if isinstance(mode, BaseException):
            raise mode
        if mode == "fail":
            return SolveOutcome(False, None, 0.0, None, "synthetic solver failure")
        params = self._params
        resp = synthetic_response(params, spec.freqs_hz, spec.observation.angle_count,
                                  max(spec.observation.balloon_points, 8))
        return SolveOutcome(True, resp, self.seconds, 100.0, "")

    # the evaluator hands us (mesh, spec) only; the design reaches us through the mesh file name
    # trick below would be fragile, so the fake build_mesh in tests/ stores params via this hook
    _params: dict = {}

    def solve(self, mesh, spec):
        return self._solve(mesh, spec)

    def solve_traced(self, mesh, spec):
        self.traced_calls += 1
        out = self._solve(mesh, spec)
        if not out.ok:
            return out, None
        nf = len(spec.freqs_hz)
        from hornlab_search.solve.traces import read_msh_geometry
        nodes, faces = read_msh_geometry(mesh.path)
        rng = np.random.default_rng(0)
        raw = {"pressure": rng.standard_normal((nf, len(nodes))) + 0j,
               "neumann": rng.standard_normal((nf, len(faces))) + 0j}
        return out, raw


def install_fakes(monkeypatch, backend: SyntheticBackend, invalid_if=None, too_large_if=None):
    """Patch ``evaluate.build_mesh`` so the backend knows which design it is solving."""
    from hornlab_search.search import evaluate as ev_mod
    inner = fake_build_mesh(invalid_if, too_large_if)

    def build_mesh(design, mesh_spec, cfg, out_dir, **kw):
        res = inner(design, mesh_spec, cfg, out_dir, **kw)
        backend._params = dict(design.params)
        backend.designs.append(design.hash())
        return res

    monkeypatch.setattr(ev_mod, "build_mesh", build_mesh)
