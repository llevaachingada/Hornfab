# All-seed CPU mesh and source checks

From repository root, run:

```powershell
.\.venv\Scripts\python.exe docs/research/typologies/dual_lame_2026-11-16/all_seed_mesh/run.py
```

The script reconstructs all 28 supplied pack seeds using the fixed K01 and L01 diagnostic configurations, binds K `rim_sweep` to `g_rim_sweep_ratio`, copies the L core and prefixes each proposed extension with `g_`, and requires exact agreement with the previously recorded adapter-screen parameter values. It only changes the config name, relative brief path, fixed seed values and matching fixed bounds. The template resolution, physical brief, solver settings and generator declarations remain unchanged. Inputs and implementation file hashes are in `provenance.json`; fixed configs, retained meshes, detailed shape-check and mesh-audit output, exceptions, and mesh hashes are in `configs/`, `meshes/` and `results.json`. `run.log` captures the run output. Existing meshes are only audited if the current shape check reports saving one.

All 27 seeds that passed the earlier adapter screen (K01–K16 and L01–L11) generated and passed `shape_check`: envelope and source fit checks passed and mesh node counts were below the screen cap. L12 was retained and refused before meshing: its computed width was 633.564 mm against the 600 mm limit. Its full exception is in the results; no seed value or envelope was relaxed.

Each of the 27 saved meshes has one edge-connected triangle component, zero duplicate-node-set or zero-area triangles, no nonmanifold edges, no inconsistent two-face edge winding, and no boundary edge off the two symmetry planes. Tag-2 sources span 0–18 mm on both transverse axes, corresponding to a 36 mm mirrored diameter. Their fourfold triangulated source surface areas range from 1011.561 to 1011.568 mm². Each source is a curved cap with z range 0–0.314191 mm, not a flat plane. The brief uses an 18 mm radius assumption; the supplied pack notes a 35.8 mm manufacturer outlet.

This is a CPU geometry and mesh screen only. The incidence audit is not a geometric self-intersection test, a proof of mirrored volume validity, a mesh convergence study, or an acoustic solve. No GPU or queue was used.

**Historical snapshot:** this run predates the subsequent L lip-tangent correction. See the input hashes for the exact implementation.
