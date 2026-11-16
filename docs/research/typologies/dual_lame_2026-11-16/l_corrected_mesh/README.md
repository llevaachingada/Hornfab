# Corrected L CPU mesh and source checks

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe docs/research/typologies/dual_lame_2026-11-16/l_corrected_mesh/run.py
```

This is the L-only rerun after the lip-tangent correction. It uses the same supplied seed mapping, L01 configuration template and physical brief as the earlier `all_seed_mesh` run; source, input and script hashes are recorded in `provenance.json`. Configs and generated meshes are retained with detailed per-case results and errors in `results.json`. The earlier adapter-screen status and digest in each result are historical comparisons, not claims about the corrected kernel.

L01–L11 all passed the CPU shape, envelope, node-cap and driver-source checks. L12 remained refused before meshing because its sampled width was 633.063 mm against a 600 mm envelope; its values and envelope were not changed. Every generated mesh has one edge-connected triangle component; no duplicate-node-set or zero-area triangles, nonmanifold edges, inconsistent shared-edge winding or boundaries off symmetry planes were found. The source spans 0–18 mm on both axes, implying 36 mm diameter after mirroring, and its triangulated fourfold surface area ranges from 1011.564119 to 1011.564343 mm². The source is a curved cap, z=0–0.314191 mm.

These incidence checks alone do not establish absence of geometric intersections, mirrored volume validity, mesh convergence or acoustic performance. No acoustic solve, GPU or queue was used.
