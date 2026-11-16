# CGAL sampled mesh self-intersection audit

This audit uses the independent CGAL 6.0.1.post202410241521 Python wheel in a separate CPython 3.12 Windows environment. It tests triangle intersections in the archived meshes, not the continuous parametric surfaces. Both K01 and L01 are open quarter models. A negative result does not establish source closure, physical tags, clearance, sampling convergence, watertightness of a full mirrored model, manufacturing feasibility, or acoustic suitability.

From the repository root, create a fresh isolated environment and run:

```powershell
.venv\Scripts\python.exe -m venv scratch\dual_lame_checkenv
scratch\dual_lame_checkenv\Scripts\python.exe -m pip install --only-binary=:all: cgal==6.0.1.post202410241521 numpy==2.5.5
scratch\dual_lame_checkenv\Scripts\python.exe docs\research\typologies\dual_lame_2026-11-16\cgal_audit\fixtures.py
scratch\dual_lame_checkenv\Scripts\python.exe docs\research\typologies\dual_lame_2026-11-16\cgal_audit\check_meshes.py docs\research\typologies\dual_lame_2026-11-16\mesh_audit\k01_geometry_only.msh docs\research\typologies\dual_lame_2026-11-16\mesh_audit\l01_geometry_only.msh
```

The local environment additionally has PyMeshLab from an earlier unsuccessful test; the CGAL scripts do not import it. Fixtures cover a noncoplanar crossing, coplanar containment and crossing, separation, near-parallel separation at 1e-12 units, a legitimate shared edge, and coplanar overlap across a shared edge. All seven passed. They do not exhaust near-degenerate configurations, shared-vertex nonmanifold input, numeric scale sensitivity, or all possible geometric arrangements.

The mesh reader accepts ASCII Gmsh 2.2 triangle elements only; it preserves vertex IDs and converts double values through 17-digit OFF text. It refuses other element types and records input SHA-256, counts, CGAL polyhedron validity and closure. CGAL accepted every node and triangle in each archived file and reported no self-intersection. K01 input SHA-256: `c3a4628d0a039fe5c95c4425548446e595d08c5c0654fea14e8886837f49e078`; L01: `b22dff6b46099f26cc488f15c01123bf61b8280960c69562d0acef05e93ebdbc`. Detailed results and script checksums are in the JSON files here.

CGAL API reference: https://doc.cgal.org/latest/Polygon_mesh_processing/ . Wheel: https://pypi.org/project/cgal/6.0.1.post202410241521/ .

An initial batch of 27 generated quarter meshes (K01–K16, L01–L11) returned no CGAL self-intersections and passed CGAL polyhedron input validation. These are recorded separately in `pre_lip_correction_meshes.json` with hashes; L geometry is being regenerated after a lip correction, so those L entries do not represent the corrected geometry. L12 was not generated in that batch. The batch can be checked with:

```powershell
$meshPaths = Get-ChildItem docs\research\typologies\dual_lame_2026-11-16\all_seed_mesh\meshes -Filter mesh.msh -Recurse | Sort-Object FullName | ForEach-Object { $_.FullName }
scratch\dual_lame_checkenv\Scripts\python.exe docs\research\typologies\dual_lame_2026-11-16\cgal_audit\check_meshes.py @meshPaths
```

After the lip correction, the regenerated L01–L11 meshes under `l_corrected_mesh/meshes` were rechecked. All 11 were valid open triangular polyhedra and CGAL reported no self-intersections; `meshes.json` records their individual hashes. L12 was refused by the generation audit and is not covered by this result. K01–K16 results are the K entries in `pre_lip_correction_meshes.json`.

```powershell
$meshPaths = Get-ChildItem docs\research\typologies\dual_lame_2026-11-16\l_corrected_mesh\meshes -Filter mesh.msh -Recurse | Sort-Object FullName | ForEach-Object { $_.FullName }
scratch\dual_lame_checkenv\Scripts\python.exe docs\research\typologies\dual_lame_2026-11-16\cgal_audit\check_meshes.py @meshPaths
```
