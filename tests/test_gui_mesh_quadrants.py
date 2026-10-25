"""GUI 3D-view quadrant reconstruction: mesh_surface's quadrants fallback chain (reader) and
view3d.js::mirrorMesh (real node module import — quarter '1' -> 4 copies, half '14'/'12' -> 2 copies,
full -> passthrough; single-reflection copies flip triangle handedness). Offline, no GPU."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from hornlab_search.gui import data as D

ROOT = Path(__file__).resolve().parents[1]

MSH = ("$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n3\n"
       "1 0 0 0\n2 0.1 0 0.05\n3 0 0.08 0.05\n$EndNodes\n"
       "$Elements\n1\n1 2 2 1 1 1 2 3\n$EndElements\n")

RUN = "20261025T000000Z-screen-abc123"


def _repo(tmp_path, cfg_quadrants, row_quadrants, meta_quadrants, extra_rows=()):
    """Minimal run dir: config.yaml, search.ndjson (_resolve_run requires it; the design's row omits
    `quadrants` entirely when there is none recorded), optional mesh_meta.json, always the same
    1-triangle mesh.msh (mirrors tests/test_gui.py fixture conventions)."""
    runs = tmp_path / "runs"
    run = runs / RUN
    run.mkdir(parents=True)
    cfg: dict = {"name": "fake"}
    if cfg_quadrants is not None:
        cfg["mesh"] = {"quadrants": cfg_quadrants}
    (run / "config.yaml").write_text(yaml.safe_dump(cfg))
    d = run / "designs" / "aaaaaaaaaaaa"
    d.mkdir(parents=True)
    (d / "mesh.msh").write_text(MSH)
    row = {"n": 0, "design_hash": "aaaaaaaaaaaa", "ok": True, "objective": 9.0, "mode": "screen",
           "family": "FREEFORM", "error": None, "generator": None}
    if row_quadrants is not None:
        row["quadrants"] = row_quadrants
    rows = [json.dumps(row)] + list(extra_rows)
    (run / "search.ndjson").write_text("\n".join(rows) + "\n")
    if meta_quadrants is not None:
        (d / "mesh_meta.json").write_text(json.dumps(
            {"result": {"quadrants": meta_quadrants, "n_triangles": 1, "n_dof": None}}))
    return runs


def test_mesh_surface_quadrants_meta_wins(tmp_path):
    runs = _repo(tmp_path, "1", "14", "12")
    assert D.mesh_surface(runs, RUN, "aaaaaaaaaaaa")["quadrants"] == "12"


def test_mesh_surface_quadrants_row_fallback(tmp_path):
    # The GRID route writes no mesh_meta.json (mesh/grid_build.py) — the search row carries the truth.
    runs = _repo(tmp_path, "1234", "14", None)
    assert D.mesh_surface(runs, RUN, "aaaaaaaaaaaa")["quadrants"] == "14"


def test_mesh_surface_quadrants_config_fallback(tmp_path):
    # A config-only solved design (no recorded quadrants in the row, no meta): config.yaml decides.
    runs = _repo(tmp_path, "1", None, None)
    assert D.mesh_surface(runs, RUN, "aaaaaaaaaaaa")["quadrants"] == "1"


def test_mesh_surface_quadrants_default_is_full(tmp_path):
    # Nothing records the meshed domain: '1234' (render as-is) is the only honest default.
    runs = _repo(tmp_path, None, None, None)
    assert D.mesh_surface(runs, RUN, "aaaaaaaaaaaa")["quadrants"] == "1234"


def test_mesh_surface_quadrants_ignores_other_designs_rows(tmp_path):
    other = {"n": 1, "design_hash": "bbbbbbbbbbbb", "ok": True, "objective": 8.0, "mode": "screen",
             "family": "FREEFORM", "error": None, "quadrants": "12", "generator": None}
    runs = _repo(tmp_path, None, None, None, extra_rows=[json.dumps(other)])
    assert D.mesh_surface(runs, RUN, "aaaaaaaaaaaa")["quadrants"] == "1234"


def _node() -> str | None:
    exe = shutil.which("node")
    if exe is None:
        return None
    out = subprocess.run([exe, "-e", "process.exit(0)"], capture_output=True)
    return exe if out.returncode == 0 else None


def test_mirror_mesh_reconstructs_full_models_from_quarters_and_halves(tmp_path):
    """Real node import of view3d.js (ES module): mirrorMesh copies + handedness per quadrant spec."""
    node = _node()
    if node is None:
        pytest.skip("node not installed")   # same environment gate as test_gui.py's ES-module check
    src = ROOT / "hornlab_search" / "gui" / "static" / "view3d.js"
    wrapper = tmp_path / "mirror_under_test.mjs"
    # the static file is outside tmp_path's module graph: resolve it by absolute file URL at import
    wrapper.write_text(
        'import { pathToFileURL } from "node:url";\n'
        'const { mirrorMesh } = await import(pathToFileURL(process.env.V3D_SRC).href);\n'
        'export default mirrorMesh;\n'
    )
    script = tmp_path / "run_mirror_test.mjs"
    script.write_text('''
import { default as mirrorMesh } from "./mirror_under_test.mjs";
import assert from "node:assert/strict";
// One triangle in the +x/+y quarter: verts [0,0,0, 1,0,0, 0,1,0] (mm), tris [0,1,2].
const verts = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]);
const tris = new Uint32Array([0, 1, 2]);
// full: passthrough, exact copy semantics
let m = mirrorMesh(verts, tris, "1234");
assert.equal(m.verts.length, 9); assert.equal(m.tris.length, 3);
assert.deepEqual([...m.verts], [0, 0, 0, 1, 0, 0, 0, 1, 0]);
// quarter '1': 4 copies of both verts and tris; extents balanced around both axes
m = mirrorMesh(verts, tris, "1");
assert.equal(m.verts.length / 3, 12); assert.equal(m.tris.length / 3, 4);
const xs = [...m.verts].filter((_, i) => i % 3 === 0), ys = [...m.verts].filter((_, i) => i % 3 === 1);
assert.equal(Math.min(...xs), -Math.max(...xs));
assert.ok(Math.min(...xs) < 0 && Math.min(...ys) < 0);
// A single reflection flips triangle handedness; two preserve it. For tris [0,1,2] the reflected
// copy's triangle is (t0, t2, t1) + offset = [3, 5, 4]. true for '14' ([1,1] then [-1,1]: one
// reflection) AND for '12' ([1,1] then [1,-1]: also one reflection).
for (const q of ["14", "12"]) {
  m = mirrorMesh(verts, tris, q);
  assert.equal(m.verts.length / 3, 6, q);
  assert.equal(m.tris.length / 3, 2, q);
  assert.deepEqual([...m.tris], [0, 1, 2, 3, 5, 4], q);
}
// unknown / absent: passthrough (never invented)
assert.deepEqual([...mirrorMesh(verts, tris, "99").tris], [0, 1, 2]);
assert.deepEqual([...mirrorMesh(verts, tris, undefined).tris], [0, 1, 2]);
console.log("mirrorMesh OK");
''')
    env = {**os.environ, "V3D_SRC": str(src)}
    out = subprocess.run([node, str(script)], capture_output=True, text=True, cwd=str(tmp_path), env=env)
    assert "mirrorMesh OK" in out.stdout, f"node test failed:\nstdout: {out.stdout}\nstderr: {out.stderr}"
