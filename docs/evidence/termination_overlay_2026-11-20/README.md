# Axial termination overlay senior review

November 20, 2026. **Decision: hold the overlay at the geometry gate.** Crowe-X and extended-throat OSSE can both reproduce their archived meshes from exact surface inputs. The tested axial deformation preserved the archived inner-wall samples upstream and the aperture projection. It changed upstream outer-wall samples and altered the triangulated excitation patch. Those changes need to be resolved before a lip-only acoustic comparison.

## Live checkout and ownership

The canonical checkout was on `hornfab-all-2026-11-18`. The requested status, eight-commit log, fetch, ref checks and 48-hour night status were run before edits. GitHub's pull API confirmed both PRs were open against the integration branch. `origin/main` already contains the rolled CD/terminal work, v11, the favorites registry, and full score breakdown. The pushed integration branch adds two documentation commits. Local HEAD is another eight commits ahead and contains split-plane/loading work, alternate briefs and the active favorite study. Two tracked modifications and seven untracked files predated this review. [PR #75](https://github.com/llevaachingada/Hornfab/pull/75) · [PR #77](https://github.com/llevaachingada/Hornfab/pull/77).

```text
HEAD                                  5c5f6f616023cbc04bc328105894628f62aa96b5
origin/main                           243136d026c9dcb59015c5d1fd322909c6079e01
origin/hornfab-all-2026-11-18           08728b5b1e4e3073a3324d54430ffdce9cbecb61
```

Night status showed the live GPU holder in `favSC__core_fav`, PID 41256. The same night includes `favRB` ridge/beak singles, search and verify lanes at its tail. A separate source-sensitivity night also appeared in status. These lanes were left to their current owners. No archive file, generator, recipe, scorer, queue or GPU lock was edited.

Local commit `5c5f6f61` adds signed beaks and a separate radial angle ridge on `osse_rollback`. `grid.py` applies the beak in the pre-lip march, then recomputes the terminal tangent and appends a tangent lip. It has a positive-forward H parameter, so a positive H setback in this review corresponds to a negative H input there. The H/V combined single sets both amplitudes to 15 mm in opposing directions. That single and the ridge/search arms do not isolate the final-surface H, V or diagonal effect against the verify archive.

## Protected controls

The CPU rebuilt each original mesh without sharing its archive directory or a mesh cache. All three meshes matched the archived MSH bytes, including physical tags, and all three v11 scores replayed exactly from the stored responses.

| Host | Verify run | Archived mesh nodes / triangles | Native body and source | Exact replay J |
|---|---|---:|---|---:|
| Crowe-X FAV-001 `4140768780f0` | `20261120T185832Z-verify-e5de4a` | 4,487 / 8,702 | GRID, 3 mm shell, auto cap at 2° | 4.993881286003633 |
| Extended-throat OSSE `e85cdd7c61f6` | `20261120T185416Z-verify-9d392f` | 4,259 / 8,195 | Native OSSE, 5 mm shell, auto cap at 4.085794° | 3.3405686204251346 |
| Fold-warm OSSE `68001408e339` | `20261120T185520Z-verify-fec2a6` | 3,836 / 7,387 | Native OSSE, 6 mm shell, auto cap at 2.076666° | 3.6146314312259817 |

The live archive contains the frequency and balloon arrays, complex pressures and throat impedance. Each has 29 frequency points from 300 to 8,000 Hz, 73 horizontal and vertical cut points and 1,035 balloon directions. The recorded solves used 6 epw, 10 m, one quadrant, `yz+xz` symmetry, metre scale, normal motion and uncached fused CUDA. The rebuilds match mesh spec hash `8e789cd0deef`. The solve hashes replay as `20797f2ac2d7` for Crowe-X and extended throat and `35a2c89d3a47` for fold-warm. The archived library pins are HornLab Search `909181cdacdfb17300b9ef4ccd97ceb943b80142`, BEAT `38e5b1f8ca840ebf6351c54611a08fedb1a0750f` and mesher `55da4f46d662d8dcd7a9f94a609eeea4009fcd62`. Per-result replay score IDs include physical and metric identity. Compare prospective A/B results with one resolved v11 scoring specification and keep each result's own IDs. [Verify archive report](../cd_v11_2026-11-20/VERIFY.md) · [Exact hashes, frequencies, response shapes and replays](geometry.json).

## Construction decision

Use one shared axial displacement law behind host-specific capture and shell adapters if the geometry gate reopens. Limit the first version to freestanding, quarter-symmetric, single-source Crowe-X and extended-throat OSSE. A single record wrapper that reconstructs every shell from inner samples fails the exact-host requirement.

- `geometry/record.py` samples the inner wall at 61 by 65 for the default comparison record. That resamples all three originals. `design/generators/record_body.py` hashes inner points, validates its V-beak and timing knobs, and computes the outer sheet via its grid or normal offset. It does not store the exact original outer sheet, source build contract or historical identity.
- Crowe-X uses 25 by 41 native samples. Putting those exact samples through the untouched record wrapper produced the identical outer shell, tags and MSH. The serialized wrapper's design hash was `ae43fbe8f91f`. Zero in a new overlay must dispatch back to the original design, mesh and solve identities before candidate hashing. A new record hash alone cannot alias an archived design.
- Extended throat uses 41 by 318 native samples. The default GRID shell differed by up to 1.630 mm and yielded 8,171 triangles. Passing both unchanged native sheets and the archived source angle directly to `build_grid_mesh` reproduced the archived MSH byte-for-byte, including its 8,195 triangles. This passes neutral mesh parity for a future explicit two-sheet adapter. Fold-warm's default shell differed by up to 2.945 mm. Even supplying its explicit outer sheet yielded a different digest at the original triangle count. Keep fold-warm outside the first version until the remaining route differences are resolved.
- Freeze both native sheets and their byte digests at capture, along with the unchanged design recipe, actual source configuration, span, mounting, wall, mesher/toolchain and mesh policy. Link them to the archived MSH and response digests. Each nonzero treatment needs a separate versioned identity. Recompute neither base sheet through a potentially changed kernel at evaluation time. Reproduce each admitted host's shell locally and preserve the frozen exterior precisely up to onset. A generic full-surface normal offset is a different shell construction from Crowe's meridian-plane offset.
- The sampled basis uses physical azimuth from `atan2(y, x)` and cumulative arc along each native meridian, including the return. The tested onset was fixed at 0.70. At the rim, H setback acts as −H at 0°, V projection acts as +V at 90°, and 45° receives −H/2 + V/2 + D. These are independent geometric controls at three sampled reference directions. The three-dimensional acoustic field couples them. The quintic makes the displacement C2 at onset when the underlying station and azimuth maps are smooth. It cannot guarantee C2 in a fitted surface, a preserved wall tangent throughout the return, or a valid offset shell. Radial rollback, pre-mouth flare timing, mounted operation and manufacturing release are outside this version.

### Routing and source audit

`design/generated.py`, `design/generators/grid.py` and `mesh/build.py` dispatch the existing record wrapper through generated design validation and the mesh route. CMA uses `DesignSpace` and inherits that validation. Study adapters still need explicit schema/provenance admission for a new version. No optimizer entry is needed for these single-design checks. The GUI's generator preview in `gui/data.py` gets record inner points through the GRID rows fallback and rebuilds the outer shell generically, so its output is insufficient as evidence for an explicit-shell overlay. Preview and solver should share the resolved two-sheet geometry.

Numeric brief `source.cap` now reaches both GRID and native mesh construction. Native `export_step` still calls `to_mesher_config` without the numeric-cap injection used by `build_mesh`, and opens the throat intentionally. GRID STEP export is refused. There is no validated CAD/solver parity path for this treatment. The source-sensitivity log also documents an old native auto-cap mesh stored under an explicit-cap key before the wiring fix. Start a controlled source comparison with fresh outputs and a clean cache namespace. [Source sensitivity evidence](../ripple_program_2026-11-20/README.md).

## Geometry preflight

The CPU sampled Crowe perturbations for H setback 5/10/20 mm, V projection 5/10/20 mm, and diagonal −5/+5 mm. H5, H10, V5 and D5 were matched-resolution 6 epw mesh builds. All four kept inner x/y and inner points at and before onset bit-identical. They passed quarter topology, body-shell sampling checks and the 36 mm source-ring fit. Each moved 23–24 outer samples upstream of its paired inner point's onset due to the shell stencil. The source geometry inputs were held fixed. The tessellation was not fixed.

| 6 epw arm | Width × height × depth (mm) | Range of meridian segment stretch | Max sampled curvature (1/mm) | Source faces |
|---|---|---:|---:|---:|
| Archived control | 587.35 × 450.26 × 263.47 | 1.000–1.000 | 0.05568 | 56 |
| H5 | 587.35 × 450.26 × 263.42 | 0.969–1.006 | 0.05546 | 56 |
| H10 | 587.35 × 450.26 × 263.42 | 0.943–1.013 | 0.05546 | 58 |
| V5 | 587.35 × 450.26 × 268.14 | 0.992–1.046 | 0.05794 | 58 |
| D5 | 587.35 × 450.26 × 268.21 | 0.994–1.033 | 0.05706 | 58 |

H5's source vertices agreed within about 6 nanometres, but exact oriented face-coordinate equality failed. H10, V5 and D5 gained two source faces and replanted source vertices with roughly 1.46 mm nearest-node displacement. This measures a triangulation change, not cap sag or a shape shift of that magnitude. H5 changed one local axial segment sign near the turn; that result warrants checking return landmarks and oriented surface Jacobians on the fitted surface. A 6 epw mesh pass establishes a valid triangulated topology for the emitted candidate. It does not certify continuous clearance, normal-offset thickness, surface curvature, or chord error. The CPU 8 epw control/H5 pair also built, with 15,400 / 15,298 body-plus-source triangles and 95 source faces each. Matching source face counts do not establish equal tessellation. The largest mesh edges were 9.283 and 7.548 mm respectively. These are edge lengths, not chord errors. No acoustic convergence or repeatability floor was measured. [Mesh views](crowe_mesh_views.png) · [Meridian, tangent and curvature plots](crowe_meridians.png) · [Finer meshes and native adapter comparison](route_and_refinement.json).

The H-terminal v1 negative control uses three piecewise cubic Hermite spans. For the current `candidate`, the axial clamp moved six H-meridian samples by up to 0.293 mm, producing six flat axial steps; the width clamp moved none. Tangent alignment in the unclamped construction and a C2 azimuth taper do not ensure continuous meridian curvature. The `soft_bend` saved config at 5.9 epw reproduced its 0.932237 mm CAD-clearance rejection, with 14 prohibited facet pairs. The same config built when tested at 6 epw. It remains a clearance rejection for the proposed overlay gate. Historical v10 C-return results showed a ripple increase from about 0.029 to 0.159 and essentially unchanged H beamwidth near 8 kHz, with a 5.9 vs 6.0 epw comparison. They are a reason to keep the negative control, with no quantitative transfer to v11. [Clamp curves](c_return_meridian.png) · [Negative-control measurements](negative_control.json) · [Original terminal handoff](../../handoffs/HANDOFF_ROLLED_TERMINAL_2026-11-20.md).

## Acoustic basis and decision gate

Di Cola and Doldi connected measured mouth pressure magnitude and phase to polar response. Gu, You and Shen optimized rectangular-horn directivity and efficiency with a separate, multi-objective shape method. Batík distinguishes the parametric rollback from radial section operations in ATH. Dong, Doc and Félix showed enclosure-dependent beamwidth for axisymmetric horns in finite cylindrical enclosures. Collectively these support testing mouth perturbations on the intended mounting and source. None supplies this axial law or predicts its acoustic sign. A 5–20 mm displacement is roughly 1–4% of a wavelength at 700 Hz and 12–47% at 8 kHz in air at 343 m/s. The potential change is frequency-localized, and the unchanged aperture and throat give no established mechanism for correcting the favorite's low-frequency load deficit. [Di Cola and Doldi](https://aes.org/publications/elibrary/elibrary-page/?id=9124) · [Di Cola, Doldi and Saronni](https://aes.org/publications/elibrary/elibrary-page/?id=9893) · [Gu, You and Shen](https://pubmed.ncbi.nlm.nih.gov/40928147/) · [Batík OS-SE](https://www.at-horns.eu/osse.html) · [Batík parametric section change](https://at-horns.eu/seg-horn.html) · [Dong, Doc and Félix](https://pubs.aip.org/asa/jasa/article-abstract/155/3/2270/3279896/Directivity-of-horns-mounted-in-finite-enclosures) · [Gmsh curvature and size controls](https://www.gmsh.info/doc/texinfo/gmsh.html).

Gate A passed for the archived controls. Gate B held on the exterior onset stencil, source patch and unmeasured continuous clearance/fidelity. The smallest follow-up is FAV-001 H5 with a frozen upstream shell and a matched source boundary discretization. Choose extended throat as the second protected host. After verifying oriented surface derivatives, return landmarks, continuous clearance and fitted-surface-to-mesh chord error, one fresh control/H5 A/B and its matched finer repeat would test authority on the v11 off-axis and CD terms, absolute and relative full-balloon data, H/V/30°/45° cuts, ripple, DI, side lobes and complex throat load. Establish a v11 same-grid repeatability floor before promotion. The archived 8 kHz solve defines the baseline band. Any 8–16 kHz exploration requires a dedicated source and mesh sensitivity bracket. Gates C–E were not run.

## Reproduction

Local review scripts and retained CPU meshes are under `scratch/termination_overlay_2026-11-20/`. Run from the canonical repo root. The first capture-enabled pytest call raised Windows invalid handle in Gmsh; loading Gmsh early still failed in `generate`. The identical selection passed with pytest output capture disabled via `-s`. No tests or tolerances were changed.

```powershell
.venv\Scripts\python.exe scratch/termination_overlay_2026-11-20/probe.py
.venv\Scripts\python.exe scratch/termination_overlay_2026-11-20/negative_control.py
.venv\Scripts\python.exe scratch/termination_overlay_2026-11-20/route_and_refinement.py
.venv\Scripts\python.exe scratch/termination_overlay_2026-11-20/render.py
.venv\Scripts\python.exe tools/shape_check.py examples/typologies/rolled_terminal_2026-11-20/soft_bend.yaml --mode screen
.venv\Scripts\python.exe -m pytest tests/test_design_generators_grid_osse_split.py tests/test_design_record_body_beak.py tests/test_design_record_body_vt.py tests/test_rolled_terminal_geometry.py tests/test_mesh_grid_build.py -q -s -o addopts= -p no:cacheprovider
```

```text
........................................
...........

triangles=164 verts=109 dofs=109 cap=110870 bbox=(0.0, 0.0, -0.003, 0.02722104989415154, 0.02722104989415154, 0.06000000000000001) seconds=0.119
.
..
.
shared quadrant max|d|=0.000e+00 mm; quadrant blocks max|d|=[0.0, 0.0, 0.0, 0.0]
..
57 passed in 16.13s
```
