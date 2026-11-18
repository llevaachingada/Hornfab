# CROWE V2A — actual BEM-wall geometry truth (WP1, 2026-11-17)

Status: **DONE** (measurement + tests + evidence). No BEM solve, GPU job, queue change or stored
run-artifact mutation. CPU mesh build/read only.

This note implements WP1 of
[`docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md`](../research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md)
(section WP1, with §2.2 and §5). It measures the mismatch between the continuous
`crowe_hv_area_aspect_v1` law and the **actual interior acoustic wall of the meshed BEM domain**
for the c0 seed and 11 representative search points under the c1 four-DOF box.

## Boundary conditions observed

- The GPU lane was **held** by the live owner search `runs/20261115T020650Z-screen-22931c` for this
  entire task. `runs/.gpu.lock` was not touched; no solve, no GPU test, no queue job and no
  `gpu-clean` was run.
- Only the existing CPU mesh path (`hornlab_search/mesh/build.py` -> pinned `hornlab_mesher`,
  gmsh) was used. All 12 meshes are in a temp directory, not in the repository.
- No file outside the WP1 ownership list was edited. Concurrent-lane uncommitted files were read
  only.

## HEAD and working-tree snapshot at lane start

```
8b255f074cb12e80a0a53fa2176dfba1d5802f75
 M docs/INDEX.md
 M docs/knowledge/README.md
 M hornlab_search/cli.py
 M hornlab_search/config.py
 M hornlab_search/gui/jobs.py
 M hornlab_search/objective/scalar_v9.py
 M hornlab_search/search/cma.py
 M hornlab_search/search/evaluate.py
 M scratch/fable_architecture/space_cards/b3_soft.json
 M scratch/fable_architecture/space_cards/b3_soft.md
 M scratch/fable_architecture/space_cards/hl__biradial_es_style_v7.json
 M scratch/fable_architecture/space_cards/hl__biradial_es_style_v7.md
 M scratch/fable_architecture/space_cards/hl__crowe_x_osse_cd_v7.json
 M scratch/fable_architecture/space_cards/hl__crowe_x_osse_cd_v7.md
 M scratch/fable_architecture/space_cards/hl__osse_rrect_fold_warm_v7.json
 M scratch/fable_architecture/space_cards/hl__osse_rrect_fold_warm_v7.md
 M scratch/fable_architecture/space_cards/summary.json
 M tests/test_search_qd_failure_isolation.py
 M tests/test_targets.py
 M tools/analysis/space_card.py
?? .claude/worktrees/
?? docs/research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md
?? examples/typologies/home_landscape_2026-11-15/hl__klangfilm_lame_curved_v1_c200w.yaml
?? tests/test_cli_finalist_mode.py
?? tests/test_gui_jobs_finalist_mode.py
?? tests/test_search_record_gate.py
?? tests/test_tools_analysis_space_card_data_agrees.py
?? tests/test_v9_polar_window.py
```

The tool also captures its own run-time `git rev-parse HEAD` and `git status --porcelain` into the
JSON `meta.git` block. (During the run another lane modified `docs/CONTINUITY.md`; that change is
not this lane's and was not touched.)

## What was added

- `tools/analysis/crowe_mesh_truth.py` — the WP1 measurement tool.
- `tests/test_crowe_mesh_truth.py` — 21 offline tests.
- `tests/fixtures/crowe_v2a/c0_quarter_screen_8k/{mesh.msh,mesh_meta.json}` — one stored real c0
  quarter mesh used for the offline topology/surface regression (no gmsh at test time).
- `docs/evidence/crowe_v2a_geometry_truth/cases_manifest.json` — the 12-case canonical sample set.
- `docs/evidence/crowe_v2a_geometry_truth/surface_truth.json` and `.csv` — full machine-readable
  results (all sections, per-station stats, hashes, provenance).
- This note.

### Reuse, not a second instrument

- Intended law: `hornlab_search/design/generators/crowe_hv_area_aspect_v1.py:evaluate` (the same
  function the search materialises).
- Native reference: the pinned mesher's own point grid via
  `hornlab_search/design/families.to_mesher_config` +
  `hornlab_mesher.config_builder.resolve_geometry`.
- Mesh build: `hornlab_search/mesh/build.py:build_mesh` (project guards, CPU gmsh).
- Mesh read/tags: `hornlab_search/compare/mshio.py:read_msh`.
- Role-aware inner-wall isolation and the *native-floor*-relative FABLE v2 rule follow the stable
  sampler logic in `scratch/fable_architecture/.n1b/inner.py` and `.x4c/inner.py`
  (`CANONICAL_SURFACE_CONTRACT.md` §12). The existing law-level Jacobian in
  `tools/geometry/crowe_hv_area_aspect_jacobian.py` is reused for the descriptor rank.
- `tools/analysis/mesh_fidelity.py` was inspected and **not** extended: it is an edge-length /
  wavelength report per physical tag. It has no analytic reference surface, no triangle-surface
  projection, no inner/outer role classification and no signed deviation. Adding those would turn it
  into a different instrument, so WP1 lives in the separate read-only tool.

## Measurement definitions (all mm unless stated)

| Quantity | Definition | Label |
|---|---|---|
| analytic sample | `evaluate()` at the case's own `L`; superellipse radial half-span `r(φ)` at `z` | [measured] |
| BEM inner wall | tag `1`/`SD1G0` triangles whose centroid radial half-span is within 2 mm of the law at the same `(z, φ)`; this excludes the offset outer shell/rear/rim that share the wall tag | [measured] |
| analytic→mesh deviation | exact point-to-triangle 3D distance from each analytic sample to the classified inner-wall triangles (KD-tree candidate selection, `k=24`; **not** nearest-vertex) | [measured] |
| signed bias | mean of `sign(dot(mesh_closest − analytic, radial_unit)) · distance`; positive = mesh wall outside the analytic wall | [derived] |
| native floor | distance from classified inner-wall mesh nodes to the pinned mesher's native point grid at 10 mm sample resolution (FABLE N1/N1b/X4 definition) | [measured] |
| FABLE v2 rule | `p99_analytic ≤ max(1 mm, 1.25 · native_floor_p99)` | [derived] |
| dense diagnostic | same analytic→mesh distance on a 97 × 73 grid (1/96 forward, 1.25° azimuth) to test whether the sparse prescribed set hides a corner/feature | [derived] |
| mesh section | plane/triangle intersection at `z`; H/V half-spans, full area by fourfold symmetry, aspect | [measured] |
| geometry rank | normalized law-surface displacement columns for the four knobs at the common samples; one-sided inward differences at bounds | [derived] |

The prescribed WP1 sample set is 7 physical stations (`0,5,10,20,40,80,100 mm`) plus 6 normalized
stations (`u=0,0.2,0.4,0.6,0.8,1.0`), at `0,22.5,45,67.5,90°` azimuths → 65 analytic samples per
case (a physical station beyond a shorter `L` would be a typed skip, never 0.0).

## Provenance / identity

| Field | Value | Label |
|---|---|---|
| repo HEAD | `8b255f074cb12e80a0a53fa2176dfba1d5802f75` | [measured] |
| base config | `examples/.../configs/c1_four_dof_bounds.yaml`, `config_sha256` short `581b3a83cc4c` | [measured] |
| generator | `crowe_hv_area_aspect_v1`, implementation SHA-256 `6cd9e4d7db492017be307170b7bcb8343abb4dfd8a0c9ad3ac1d8ebc56e98862` | [measured] |
| mesher pin | `55da4f46d662d8dcd7a9f94a609eeea4009fcd62` (`hornlab-waveguide-mesher` 0.2.4) | [measured] |
| surface fit (configured) | `auto` (absent from the built manifest's `mesher_config.mesh`) | [measured] |
| surface fit (resolved) | `approximate` for this FREEFORM family | [measured] |
| mesh units | metres on disk; converted to mm for this analysis | [measured] |
| symmetry | `quadrants="1"`, native plane `yz+xz`; quarter domain `x≥0, y≥0` | [measured] |
| physical solve id | `not_applicable` — geometry-only run, no acoustic solve | [unavailable] |
| full outer envelope | built bbox/depth are reported; wall-thickness/roll-bead manufacturability is not inferred from an inner-only bbox | [derived] / [unavailable] |
| acoustic behaviour | not measured; no BEM was invoked | [unavailable] |

Per-case `design_hash`, effective `config_sha256`, mesh SHA-256, mesher config key and all section
rows are in `surface_truth.json`. Nothing here is [interpolated] or [proposed].

## Sample set (12 admitted cases, 0 refusals)

The tool also supports typed refusals (an out-of-bounds knob records `status="refused"` with the
exception type and does not build a mesh); no bound was patched. All 12 canonical cases admitted.

`cases_manifest.json` roles: c0 seed, 2 interior heights, single-variable low/high for all four
knobs, 2 coupled feasible corners.

## Per-case measured surface truth

`surface_truth.csv` (columns: median, p99, max, signed bias, dense p99/max, native floor, FABLE
threshold/pass, surface rank, mesh triangle count). Values in mm.

| Case | design_hash | config_sha | mesh_sha256 | median | p99 | max | signed bias | dense p99 | dense max | native floor p99 | rule thresh | pass | rank |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---:|
| c0_seed | 1c206df9912f | b3a74c02a5d3 | 92a881a0060b | 0.0100 | 0.1263 | 0.1363 | -0.0235 | 0.1266 | 0.1649 | 0.0191 | 1.000 | yes | 4 |
| interior_h400 | 40a6d4faa44f | 0880776b0e73 | 863769618127 | 0.0096 | 0.1221 | 0.1416 | -0.0232 | 0.1311 | 0.2048 | 0.0201 | 1.000 | yes | 4 |
| interior_h430 | 33d67042efa1 | c6f540f73ddd | 8df2b007be5b | 0.0132 | 0.1276 | 0.1351 | -0.0230 | 0.1320 | 0.2023 | 0.0210 | 1.000 | yes | 4 |
| height_low300 | 4ed6f689670f | 9714dac4c6b3 | f47281387193 | 0.0082 | 0.1237 | 0.1647 | -0.0197 | 0.1339 | 0.1873 | 0.0224 | 1.000 | yes | 4 |
| length_low220 | b3d9e3029c0a | 7ee3f18287b5 | e089c92b2986 | 0.0156 | 0.1122 | 0.1207 | -0.0222 | 0.1231 | 0.1697 | 0.0142 | 1.000 | yes | 4 |
| length_high340 | 81d1d3d069a8 | 82cc06c46773 | ed613549f098 | 0.0144 | 0.1204 | 0.1207 | -0.0219 | 0.1314 | 0.2007 | 0.0243 | 1.000 | yes | 4 |
| area_bias_low | f94b52e10fbf | 628bed42c2f3 | e6f58039b773 | 0.0134 | 0.1286 | 0.1410 | -0.0266 | 0.1329 | 0.1793 | 0.0190 | 1.000 | yes | 4 |
| area_bias_high | 4be8694c191e | 05f61a9c27c1 | 60de01241bb1 | 0.0108 | 0.1266 | 0.1372 | -0.0243 | 0.1251 | 0.1697 | 0.0199 | 1.000 | yes | 4 |
| u50_low | 00c288fc750f | b4ba97b4bf66 | 3b3a313bcbcd | 0.0232 | 0.1217 | 0.1236 | -0.0274 | 0.1495 | **0.2195** | 0.0193 | 1.000 | yes | 4 |
| u50_high | c09f2d92e60e | f2386134d203 | c7f6c43827ac | 0.0152 | 0.1139 | 0.1207 | -0.0244 | 0.1148 | 0.1653 | 0.0182 | 1.000 | yes | 4 |
| corner_small_boxy | fb01cd9e6ff0 | beecf34d081d | 8e2236e1f809 | 0.0143 | 0.1135 | 0.1647 | -0.0191 | 0.1078 | 0.1855 | 0.0160 | 1.000 | yes | 4 |
| corner_large_round | 7ea002a56ea9 | f29877aa67f2 | 995d6efab5e2 | 0.0097 | 0.1197 | 0.1207 | -0.0217 | 0.1421 | 0.1874 | 0.0241 | 1.000 | yes | 4 |

Worst prescribed-set p99: **0.1286 mm** (`area_bias_low`). Worst dense diagnostic point:
**0.2195 mm** (`u50_low`). Worst native floor p99: 0.0243 mm. Every case passes the FABLE v2
relative rule; note that here the absolute 1 mm floor governs, because the native floor is only
0.014–0.024 mm. **The defensible result is the absolute p99 (≈0.11–0.13 mm), not the pass flag.**

### c0 seed per-station sections (analytic vs mesh)

| Basis | z (mm) | analytic a | analytic b | mesh H half-span | mesh V half-span | A law | A mesh | ΔH | ΔV | ΔA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| physical | 0 | 18.0000 | 18.0000 | 18.0000 | 18.0000 | 1017.876 | 1017.594 | +0.0000 | +0.0000 | -0.28 |
| physical | 5 | 18.1864 | 18.1862 | 18.1879 | 18.1877 | 1039.064 | 1036.636 | +0.0015 | +0.0015 | -2.43 |
| physical | 10 | 18.3967 | 18.3953 | 18.3979 | 18.3965 | 1063.246 | 1059.526 | +0.0013 | +0.0011 | -3.72 |
| physical | 20 | 18.8919 | 18.8817 | 18.8939 | 18.8834 | 1121.367 | 1120.077 | +0.0020 | +0.0017 | -1.29 |
| physical | 40 | 20.2081 | 20.1299 | 20.2107 | 20.1318 | 1283.814 | 1281.165 | +0.0026 | +0.0019 | -2.65 |
| physical | 80 | 24.4898 | 23.8948 | 24.4903 | 23.8961 | 1888.495 | 1883.188 | +0.0005 | +0.0013 | -5.31 |
| physical | 100 | 27.7750 | 26.6231 | 27.7824 | 26.6287 | 2426.471 | 2422.911 | +0.0074 | +0.0056 | -3.56 |
| normalized | 60 | 22.0311 | 21.7751 | 22.0347 | 21.7778 | 1527.419 | 1526.700 | +0.0036 | +0.0027 | -0.72 |
| normalized | 120 | 32.1574 | 30.1618 | 32.1677 | 30.1690 | 3239.933 | 3241.262 | +0.0103 | +0.0072 | +1.33 |
| normalized | 180 | 56.4819 | 49.2134 | 56.5006 | 49.2380 | 9714.681 | 9698.330 | +0.0187 | +0.0247 | -16.35 |
| normalized | 240 | 118.0368 | 97.5988 | 118.0560 | 97.6453 | 41175.196 | 41155.785 | +0.0192 | +0.0465 | -19.41 |
| normalized | 300 | 290.0000 | 237.0000 | 290.0000 | 237.0000 | 246693.317 | 246605.315 | +0.0000 | +0.0000 | -88.00 |

The maximum section-area error in this c0 set is 88 mm² at the mouth (246,693 vs 246,605 mm²,
−0.036 %). The realized throat is exactly 36.000 × 36.000 mm; the mouth is exactly
580.000 × 474.000 mm. All 12 cases had the exact nominal mouth dimensions and the same 36 mm
modeled source section.

### Resolution study (c0, screen + two denser CPU meshes)

The small negative signed bias is triangle-discretisation/surface-fit, not a law error: it shrinks
with mesh resolution while the law and the sampling stay unchanged.

```
epw 6  tris  8318 inner  4486 dev p50 0.0100 p99 0.1263 max 0.1363 dense p99 0.1266 max 0.1649 signed -0.0235 open_off 0 time 15.7s
epw 9  tris 18420 inner  9993 dev p50 0.0080 p99 0.0803 max 0.1030 dense p99 0.0880 max 0.1280 signed -0.0118 open_off 0 time 47.7s
epw 12 tris 32194 inner 17578 dev p50 0.0056 p99 0.0709 max 0.0848 dense p99 0.0754 max 0.1023 signed -0.0082 open_off 0 time 87.2s
```

The fitted surface converges toward the analytic law (dense max 0.165 → 0.128 → 0.102 mm). No
FREEFORM control-pole, station-density, angular-sampling, lip/corner or source-closure defect is
visible at the millimetre scale. The c0 screen mesh is the shipped analysis resolution; the denser
meshes are a diagnostic only and are not proposed as a new pin.

### Geometry rank at the common canonical samples

Normalization: columns are law-surface displacement in mm per unit normalized box coordinate,
divided by the RMS sample radius (dimensionless). One-sided inward differences are used for any
seed on a bound (the c0 seed is on the H upper bound). `rank` uses the generator's own 1e-6/1e-2
singular-value thresholds.

| Case | singular values (relative) | L | H | bias | u50 | max abs cosine | rank |
|---|---|---:|---:|---:|---:|---:|---:|
| c0_seed | 4.440, 1.716, 0.226, 0.087 | 4.440 | 1.716 | 0.227 | 0.088 | 0.162 | 4 |
| interior_h400 | 4.533, 1.871, 0.224, 0.145 | 4.533 | 1.870 | 0.226 | 0.147 | 0.178 | 4 |
| interior_h430 | 4.495, 1.799, 0.225, 0.120 | 4.495 | 1.798 | 0.226 | 0.121 | 0.174 | 4 |
| height_low300 | 4.667, 2.148, 0.247, 0.220 | 4.667 | 2.147 | 0.223 | 0.249 | 0.185 | 4 |
| length_low220 | 5.306, 2.036, 0.302, 0.113 | 5.306 | 2.036 | 0.303 | 0.115 | 0.153 | 4 |
| length_high340 | 4.085, 1.582, 0.206, 0.079 | 4.085 | 1.581 | 0.207 | 0.080 | 0.166 | 4 |
| area_bias_low | 4.445, 1.716, 0.215, 0.083 | 4.445 | 1.715 | 0.216 | 0.084 | 0.160 | 4 |
| area_bias_high | 4.435, 1.717, 0.237, 0.091 | 4.435 | 1.716 | 0.238 | 0.093 | 0.164 | 4 |
| u50_low | 4.440, 1.727, 0.225, 0.080 | 4.440 | 1.727 | 0.226 | 0.081 | 0.124 | 4 |
| u50_high | 4.440, 1.700, 0.226, 0.122 | 4.440 | 1.699 | 0.227 | 0.124 | 0.178 | 4 |
| corner_small_boxy | 5.700, 2.579, 0.399, 0.289 | 5.700 | 2.578 | 0.291 | 0.406 | 0.188 | 4 |
| corner_large_round | 4.081, 1.593, 0.216, 0.074 | 4.081 | 1.593 | 0.217 | 0.075 | 0.130 | 4 |

All 12 cases are full-rank at the surface-displacement level. `L_forward_mm` dominates the
displacement (it rescales the whole wall), `height_v_active_mm` is second, and
`area_mid_bias`/`aspect_timing_u50` are weaker but non-zero and not collinear (max |cosine| ≤ 0.19).
This is **geometry rank**, not acoustic independence.

### Topology / source / shell (all 12 cases)

| Check | Result | Label |
|---|---|---|
| physical tags | `{1: SD1G0, 2: SD1D1001}` in every case; tag 2 is the loaded source face | [measured] |
| source face | 36.000 × 36.000 mm full extents in every case; z from 0 to ~0.31 mm | [measured]/[derived] |
| open edges | all on the `quadrants="1"` symmetry planes; **0 off-symmetry open edges** in every case | [measured] |
| non-manifold edges | 0 in every case | [measured] |
| winding-inconsistent shared edges | 0 in every case | [measured] |
| built bbox / full W,H,D | 580.0 × 474.0 × 303.0 mm (depth includes the 3 mm rear closure) at the c0 seed; nominal mouth W/H exact per case | [measured]/[derived] |
| wall stand-off (shell centroids) | median 3.00 mm in every case; core min 2.64–2.77 mm (first/last 5 mm excluded); raw min 0.45–0.49 mm is the welded rim, not a wall undercut | [measured]/[derived] |
| terminal z | `L_forward_mm` exactly; delta 0.000 mm in every case | [measured] |
| unmeasurable stations | 0 | [measured] |

## Findings

1. **No material law-vs-wall mismatch in V2A.** Across 12 representative cases the prescribed-set
   p99 is 0.112–0.129 mm and the denser 97 × 73 diagnostic never exceeds 0.220 mm. This is far
   below the 1 mm FABLE absolute floor and does not reproduce the 1.1–1.6 mm corner mismatch seen
   in the older Crowe-X/rounded-rectangle lane. The smoother superellipse sections are represented
   well by the pinned mesher; **do not generalise this to cornered/rounded-rectangle families.**
2. **Residual sign and origin.** The signed bias is small and negative (−0.019 to −0.027 mm: the
   mesh sits just inside the analytic wall). The resolution study shows it shrinking with mesh
   refinement (−0.023 → −0.012 → −0.008 mm), so it is triangle discretisation/surface fit, not a
   generator-law defect.
3. **The native floor is near zero for this route.** The mesh is built from the same native point
   grid, so mesh-node-to-native-grid distances are 0.014–0.024 mm at p99. The FABLE rule therefore
   reduces to the 1 mm absolute floor. The meaningful evidence is the absolute p99, not the pass
   flag.
4. **Geometry rank is four at the actual surface.** Every case has four non-negligible singular
   values and max pairwise cosine ≤ 0.19. The ranking of sensitivity is L > H > area bias ≈ u50.
   This does not prove acoustic independence.
5. **The STOP condition was not triggered.** The pinned mesher does expose an accurate,
   role-selectable acoustic surface for V2A. No replacement mesher, no fork edit and no `.venv`
   change was made, and none is needed for this family.
6. **Topology is clean.** Source tag loaded, 36 mm source section, exact mouth dimensions, zero
   off-symmetry open edges, zero non-manifold/winding errors, and a maintained ~3 mm solid wall.

## Limitations / what is not claimed

- The mesh is the screen mesh at `f_max = 8000 Hz`, `epw = 6`, quarter domain. Higher-frequency
  verify/final meshes were not solved (and no solve was authorised). The 12 meshes are temp
  artifacts; their SHA-256 values are recorded in the JSON, not committed.
- The prescribed 65-sample comparison is deliberately sparse; the dense diagnostic is the guard
  against a hidden corner/feature. It is not a substitute for a full convergence study.
- The analysis measures geometry, not acoustics. No pressure, directivity, impedance or score
  claim is made.
- The full outer envelope/manufacturability (including the 474 mm active height inside a 480 mm
  total envelope) is not established from an inner-only bbox; only the built outer bbox/depth and
  shell stand-off are reported.

## Reproduce

CPU only. The interpreter is `.venv\Scripts\python.exe`; thread caps are set as required.

```powershell
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"; $env:VECLIB_MAXIMUM_THREADS="1"

.venv\Scripts\python.exe -m pytest tests/test_crowe_mesh_truth.py -q -p no:cacheprovider
# .....................                                                    [100%]
# EXITCODE=0   (21 tests)

.venv\Scripts\python.exe tools/analysis/crowe_mesh_truth.py ^
  --config examples/typologies/crowe_hv_area_aspect_2026-11-16/configs/c1_four_dof_bounds.yaml ^
  --samples docs/evidence/crowe_v2a_geometry_truth/cases_manifest.json ^
  --out docs/evidence/crowe_v2a_geometry_truth/surface_truth.json ^
  --mesh-root "%TEMP%\crowe_v2a_truth_meshes"
```

Real run output (12/12 `ok`; the full JSON/CSV is the machine-readable record):

```
[crowe_mesh_truth] case c0_seed ...
[crowe_mesh_truth]   ok median 0.010 mm, p99 0.126 mm, max 0.136 mm
[crowe_mesh_truth] case interior_h400 ...
[crowe_mesh_truth]   ok median 0.010 mm, p99 0.122 mm, max 0.142 mm
[crowe_mesh_truth] case interior_h430 ...
[crowe_mesh_truth]   ok median 0.013 mm, p99 0.128 mm, max 0.135 mm
[crowe_mesh_truth] case height_low300 ...
[crowe_mesh_truth]   ok median 0.008 mm, p99 0.124 mm, max 0.165 mm
[crowe_mesh_truth] case length_low220 ...
[crowe_mesh_truth]   ok median 0.016 mm, p99 0.112 mm, max 0.121 mm
[crowe_mesh_truth] case length_high340 ...
[crowe_mesh_truth]   ok median 0.014 mm, p99 0.120 mm, max 0.121 mm
[crowe_mesh_truth] case area_bias_low ...
[crowe_mesh_truth]   ok median 0.013 mm, p99 0.129 mm, max 0.141 mm
[crowe_mesh_truth] case area_bias_high ...
[crowe_mesh_truth]   ok median 0.011 mm, p99 0.127 mm, max 0.137 mm
[crowe_mesh_truth] case u50_low ...
[crowe_mesh_truth]   ok median 0.023 mm, p99 0.122 mm, max 0.124 mm
[crowe_mesh_truth] case u50_high ...
[crowe_mesh_truth]   ok median 0.015 mm, p99 0.114 mm, max 0.121 mm
[crowe_mesh_truth] case corner_small_boxy ...
[crowe_mesh_truth]   ok median 0.014 mm, p99 0.113 mm, max 0.165 mm
[crowe_mesh_truth] case corner_large_round ...
[crowe_mesh_truth]   ok median 0.010 mm, p99 0.120 mm, max 0.121 mm
[crowe_mesh_truth] wrote docs/evidence/crowe_v2a_geometry_truth/surface_truth.json (+ surface_truth.csv)
EXITCODE=0
```

Law-only mode needs no mesher:

```
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"
.venv\Scripts\python.exe tools/analysis/crowe_mesh_truth.py ^
  --config examples/typologies/crowe_hv_area_aspect_2026-11-16/configs/c1_four_dof_bounds.yaml ^
  --out "%TEMP%\crowe_truth_law2.json" --no-mesh
# ... all 12 cases "law_only"
# EXITCODE=0
```

### Known limitation

`--existing-mesh` is single-case only (it needs one `mesh.msh` and one matching seed). The
multi-case path always rebuilds/uses the project mesh cache. The test suite's real-c0 regression
uses the stored fixture, so the default offline test run never starts gmsh.

## Files

| Path | Role |
|---|---|
| `tools/analysis/crowe_mesh_truth.py` | WP1 tool (analytic law + CPU mesh truth + rank; no solve imports) |
| `tests/test_crowe_mesh_truth.py` | 21 offline tests (analytic, exact-distance, signed-error, tags, topology, rank, refusal, real c0 fixture) |
| `tests/fixtures/crowe_v2a/c0_quarter_screen_8k/` | stored c0 quarter mesh + manifest for the offline topology regression |
| `docs/evidence/crowe_v2a_geometry_truth/cases_manifest.json` | the 12-case canonical sample set |
| `docs/evidence/crowe_v2a_geometry_truth/surface_truth.json` | full results incl. per-case sections, provenance, hashes |
| `docs/evidence/crowe_v2a_geometry_truth/surface_truth.csv` | per-case summary |
| `docs/evidence/CROWE_V2A_SOLVER_SURFACE_TRUTH_2026-11-17.md` | this note |

## 11. Hardening pass addendum (2026-11-17, second pass)

Independent static review + fresh-input reproduction were run after the initial capture. Corrections
and tool changes, in one place:

- **Label correction.** The analytic `evaluate()` sections are a **[derived]** computed reference, not
  a measurement; only the triangle-surface deviation statistics (and the stored mesh checks) are
  **[measured]**. Earlier prose used `[measured]` for the law samples — read those as `[derived]`.
- **Schema.** `config_sha256`/`base_config_sha256` now carry the full 64-hex digest (plus a
  `config_sha_short`/`base_config_sha_short` alias; earlier values were 12-hex prefixes under a
  256-bit field name). `surface_fit_resolved_native`/`native_grid_shape` are now typed
  `"unavailable"`: `geometry.record.native_points` does not expose the mesher's resolved
  surface-fit mode, and none is invented.
- **Refusal semantics.** `main` exits **1** when any case is `refused` (previously it always exited 0,
  so an all-refused run looked successful in automation). The broad `except Exception` that converted
  any tool bug into a typed refusal is narrowed to expected generator/config/mesher errors;
  unexpected exceptions now fail loudly.
- **Reuse.** `native_geometry` now calls `hornlab_search/geometry/record.py::native_points` instead of
  duplicating it; measured numbers are unchanged (c0 p99 0.12630539225424334, dense 0.126621, rank 4,
  short shas `b3a74c02a5d3`/`581b3a83cc4c` re-verified identical).
- **Jacobian steps.** One-sided differences divide by the actually-achieved inward step for samples
  near (not on) a bound; on-bound seeds keep the full step.
- **Rank scope (restated).** Mesh-surface rank 4 requires the **c1 four-DOF box** config with the case
  knobs; the c0 config itself fixes every bound (`lo == hi`), giving rank 0 by construction. All rank
  numbers in this note used the c1 box.
- **Mesher-optional existing-mesh mode.** With `--existing-mesh`, native-floor-dependent outputs are
  typed `"unmeasurable (mesher not installed)"` when `hornlab_mesher` is absent; topology/surface/rank
  still run. The fixture regression test therefore stays offline-capable and CI-safe.
- **Independent reproduction (fresh inputs, not the authors' 12 cases).** Two new c1-box corners:
  `interior_low_h350` (H350/L250/bias0/u50.5) bias −0.0174 mm, p99 0.133 mm, rank 4, FABLE pass;
  `corner_big_long_boxy` (H474/L340/bias−0.15/u50.65) bias −0.0282 mm, p99 0.125 mm, rank 4, FABLE
  pass. Determinism: two `--existing-mesh` runs on the c0 fixture differ **only** in `meta.utc`.
- **No-mutation proof.** Stored `response.npz`/`best.json` hashes identical before/after all tool
  invocations; `git status --porcelain` unchanged.
- **Tests.** `tests/test_crowe_mesh_truth.py` is now **26 tests** (added: full/short sha, CLI exit
  code, mesher-absent existing-mesh, near-bound achieved-step, per-azimuth samples), 0 failed.
