# Sculpted H/V meridians and returning mouths

November 20, 2026. CPU geometry checkpoint for the archived first-row R-OSSE and Crowe-X FAV-001. The study produced nine derivatives and two byte-matched controls. It replaces a lip-only hypothesis with trials that change development through the wall, then tests a distinct terminal finish on two of those bodies.

Machine and stack: Windows on the local i7-14650HX, project Python 3.12, installed waveguide mesher `55da4f46d662d8dcd7a9f94a609eeea4009fcd62`, and VTK 9.7.2 for CPU facet queries.

[Same-scale BEM mesh views](views.png) · [Five meridians and curvature](meridians.png) · [3D lip edges, forward reach and rollback](lip_overlay.png) · [Arc sections and surface normals](sections_normals.png)

## Checkout and archived controls

| Ref | Live SHA |
|---|---|
| Local `hornfab-all-2026-11-18` | `5c5f6f616023cbc04bc328105894628f62aa96b5` |
| `origin/main` | `243136d026c9dcb59015c5d1fd322909c6079e01` |
| `origin/hornfab-all-2026-11-18` | `08728b5b1e4e3073a3324d54430ffdce9cbecb61` |

Fetch and the open-pull API check showed PR #75 (Klangfilm c200/rolled h12) and PR #77 (system foundations). Local HEAD was eight commits ahead of the pushed integration branch. The local favorite night held the GPU with `favSC__core_polish` during initial checks, and `favRB` ridge and beak jobs remain in the existing queue. The existing `osse_rollback` beak runs before its tangent lip is generated. This study uses neither that construction nor its queue. Pre-existing dirty files and the previous overlay evidence were preserved. [PR #75](https://github.com/llevaachingada/Hornfab/pull/75) · [PR #77](https://github.com/llevaachingada/Hornfab/pull/77).

R0 is `823dc1721a76`, recovered from `runs/20261117T053153Z-screen-15f0e4` and its nested verify directory. The ordinary canonical resolver rejected the saved record with `GeneratorError grid rows: unknown key(s) ['driver', 'implementation_sha256', 'schema']`. The historical `tools/geometry/rosse_rect_cli.py` bridge still matches the saved three-file implementation digest `601056d0d18f5ba0f699d93ae0e497f48f483f80f1a93640b4db13f74a746b9f`. It regenerated the original 25 × 49 native inner array. The original meridian-plane offset regenerated its 3 mm outer sheet. A CPU remesh matched the verify archive byte-for-byte, with 6,443 nodes, 12,546 triangles and 58 source faces. The reference's measured mesh depth is 480.066 mm, including the cap and shell, while the original sampled envelope was 477.628 mm. We keep R0 exact. Every derivative is inside its declared 600 × 480 × 480 mm envelope in the emitted mesh.

The R0 saved recipe uses 575.463741 × 442.951742 mm nominal dimensions, exponent 6.935646, H 37.812411°, V 17.075683°, diagonal addition 0°, `k=2.4794610419`, `m=.85`, `r=.2820232949`, `b=.0002388511`, `q=3` and `tmax=.9669894771`. Its HF1440 source brief specifies an 18 mm radius, 2° nominal exit, auto cap, freestanding quarter body and v7 with a 1 kHz vertical coverage onset. The archived v7 scores were 3.4910677068462976 (screen) and 3.75208496258515 (verify). The current replay reproduced verify v7 exactly. An offline v11 rescore of the same archived 300 Hz–8 kHz verify response gives 4.779948718044434. It is a scorer comparison on stored fields. [Exact recipe and remesh provenance](reference.json) · [Archived acoustic replay](archived_acoustics.json).

C0 is the original Crowe-X `4140768780f0`, with an exact zero-control return of both sampled arrays and a byte-identical FAV-001 verify mesh. It remains the CD-specific protected host. Fold-warm `68001408e339` and extended-throat `e85cdd7c61f6` are retained as v11 benchmarks. The earlier CPU transfer test reproduced the extended-throat mesh with its two native sheets and retained source setup. Fold-warm still needs a route-specific parity check before derivation. [Previous protected-host controls](../termination_overlay_2026-11-20/README.md) · [Original v11 verify cohort](../cd_v11_2026-11-20/VERIFY.md).

## Construction and independent controls

**A. Native per-azimuth R-OSSE.** `geometry/_sculpted_rosse_v1.py` evaluates the installed rev7 meridian in its native parameter for each physical azimuth. It uses a common 36 mm circular entrance and smooth transition from a 2° cone, constant through 8 mm and completed at 42 mm of physical z on the forward branch. The meridians continue independently beyond the collar, reversing axially through their returns. H/45°/V values are interpolated by a mirror-symmetric combination of `cos²(phi)`, `sin²(phi)` and `sin²(2phi)` with the 45° value explicitly anchored. This permits separate opening angle, apex shift `m`, apex radius factor `r` and bending `b` at the three reference directions. The width, height and Lamé exponent set a separate physical rim outline. Since published `R` belongs to `t=1`, the code solves for the native R at each azimuth when the requested edge is truncated earlier. Changing angle alone then holds the projected inner lip exactly on the specified outline. A unit test compares the installed evaluator with a direct independent five-station calculation of the published rev7 equations at the published R=200 mm reference parameters.

**B. Terminal finish.** With arc measured along the returned meridian, the optional finish takes independent H/45°/V radial and axial motions and a start fraction. An endpoint-neutral signed normal displacement adds curvature authority without changing the final station. C2 smoothstep weights start and end with zero first and second derivatives. The finish therefore has a smooth join in the continuous parameter, which still needs a fitted-surface check. K1/K2 share the same A body, so their contrast isolates the finishing layer as a whole. The candidate finish uses H/45°/V axial changes of −8/−3/+6 mm, radial changes of −4/−3/−1 mm, arc starts .74/.77/.80 and curvature displacements of 1/.8/.6 mm. The apex shift and radius in A also shape the native return independently of the finish.

**Protected-host derivatives.** `geometry/_sculpted_host_v1.py` works from the exact two sheets. The body has an arc-windowed radial section-growth control and an axial map that ramps between the original z=48 and 215 mm. Its monotonicity check prevents the body map from creating a new backward branch, while the original rollback survives. The separate arc-based terminal gate starts at .80 of the original inner meridian. Both captured sheets receive the same paired sample displacement, holding the paired vectors and upstream samples. Those vectors can deviate from the new surface normal. This is a comparison and measurement route while shell fidelity is investigated.

The new constructions are HornFab hypotheses around an independently checked published evaluator. The existing Klangfilm–Lamé E2/E3 use aspect/exponent control with shallow or absent return. V5 inherits the V4 direction with deeper development and its own negative signed sweep. They informed K1's rounded landscape aperture and quieter diagonal transition. K1/K2 retain the R0 direction of H/V sweep and the R-OSSE return. This construction leaves the Klangfilm curved-cap area law and the separate H/V core untouched. [Klangfilm contract](../../knowledge/contracts/klangfilm_lame_hv.md) · [E2 study sheet](../../queue/klangfilm_lame_ellipse_E2_sheet.png) · [V5 study sheet](../../queue/klangfilm_lame_V5_sheet.png).

| Primary source | Use |
|---|---|
| [Batík rev7](https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf) | Parametric rollback and numerical witness. Primary indexed equation text was available. |
| [Batík, Segmentizing a Horn](https://at-horns.eu/seg-horn.html) | Coordinates and smooth angular-sector weighting. The current harmonic law is original. |
| [Di Cola and Doldi](https://aes.org/publications/elibrary/elibrary-page/?id=9124) | Mouth pressure magnitude and phase motivate the diffraction diagnostic. |
| [Gu, You and Shen](https://pubmed.ncbi.nlm.nih.gov/40928147/) | Rectangular horns with separate coverage, shape smoothness and efficiency objectives. |
| [Dong et al.](https://pubmed.ncbi.nlm.nih.gov/33765791/) | Joint loading, smoothness and directivity decisions in an axisymmetric study. |
| [Sridhar, Tylka and Choueiri](https://3d3a.princeton.edu/publications/generalized-metrics-constant-directivity) | Complementary listening-window, DI and polar-correlation measures. |

## What built

Sweep is the V-minus-H difference of the maximum z of each bore meridian. Lip delta compares the final stations. Neither refers to projected aperture. Dimensions are from actual 6 epw quarter solver meshes reflected in H and V. The projected lip area is the inner-edge polygon integrated in x/y.

| Case | Geometry | Forward sweep (mm) | Lip delta (mm) | Meshed W × H × D (mm) | Projected lip area (cm²) |
|---|---|---:|---:|---|---:|
| R0 | Exact R-OSSE archive | 233.0 | 224.1 | 573.3 × 441.4 × 480.1 | 2457.2 |
| R1 | Reduced sweep | 29.3 | 28.2 | 575.5 × 443.0 × 339.3 | 2477.2 |
| R2 | Medium sweep | 96.1 | 92.4 | 575.5 × 443.0 × 360.3 | 2477.2 |
| R3 | Strong sweep | 157.5 | 151.5 | 575.5 × 443.0 × 408.5 | 2477.2 |
| R4 | Near-reference sweep | 215.0 | 206.8 | 575.5 × 443.0 × 461.4 | 2477.2 |
| K1 | Smooth landscape wing | 136.1 | 126.3 | 579.0 × 401.0 × 389.9 | 2088.7 |
| K2 | K1 with a sculpted return | 149.0 | 140.3 | 571.0 × 399.0 × 395.0 | 2042.4 |
| C0 | Exact FAV-001 archive | −0.1 | 0.4 | 587.4 × 450.3 × 263.5 | 2389.9 |
| C1 | Moderate Crowe body | 63.9 | 64.4 | 587.4 × 450.3 × 297.4 | 2389.9 |
| C2 | Strong Crowe body and return | 121.2 | 122.4 | 581.4 × 450.3 × 327.1 | 2362.3 |
| C3 | Crowe terminal control | 2.6 | 3.4 | 591.4 × 450.3 × 263.4 | 2408.4 |

R1–R4 demonstrate sweep control at fixed projected footprint. K1 moves the footprint toward the requested landscape proportion as an independent choice. C1 produces visible whole-body development at unchanged projected opening. C2's first compact axial bump caused a second forward lobe and was refused before mesh generation. The tested monotone axial map removed that extra lobe without clipping or removing the intentional return. The older sharp C-return used clamped Hermites and a different v10 objective. Its soft-bend counterpart reproduced a 0.932237 mm clearance rejection at its saved settings. Those cases remain negative controls for promotion. [Geometry and control manifest](manifest.json) · [Rolled-terminal negative control](../termination_overlay_2026-11-20/negative_control.json).

Qualification applies to these individual tested points. R1–R4 used H opening angles 36–38°, V 17.8–27°, and an unchanged projected aperture. K1/K2 exercised exponent 3.3 and H/45°/V apex-radius factors .34/.32/.30. Crowe examples tested H body setback down to −55 mm and V extension up to +62 mm. Each intermediate azimuth is checked. Combinations that introduce self-contact, a second forward lobe, shell inversion, or envelope exceedance are refused.

## Fidelity and acoustic gate

All 11 cases passed existing freestanding mesher facet and final topology checks at 6 epw. The six selected finer meshes also built at 8 epw. The CPU runner also checked both triangles of every sampled cell for consistent orientation, per-meridian self-intersection and single forward apex, discrete nonadjacent clearance on both sheets, a round source ring, and physical source tag 2. The true 3D normal offset on R/K has a 3 mm paired distance and minima of about 2.96–2.99 mm when projected onto one-sided sampled cell normals. C2's projected minimum is about 2.02 mm because both frozen sheets are transported together. These statistics and existing mesher checks cover sampled normals and emitted facets. A global continuous CAD clearance or a bound on wall thickness between samples has not been established. [Full CPU manifest](manifest.json).

The wall-only VTK locator compares the saved surfaces with the BEM facets. R3's worst near-lip sample distances dropped from 0.48/0.79 mm (inner/outer) to 0.26/0.41 mm at 8 epw. K1 dropped from 0.64/1.08 mm to 0.37/0.53 mm. C0 and C1 retain roughly 2.7–2.8 mm external near-lip discrepancies at both resolutions, so candidate C shells need a fitted-surface audit. These are unsigned nearest-facet distances at samples. They cannot bound inter-station error or prove the nearest triangle lies on the corresponding sheet. All 11 full mirrored VTU diagnostic exports preserve points, connectivity and physical tags on read-back, with welded seams and valid closed edge topology. VTU includes the excitation patch. The GRID STEP route still refuses export, so CAD/STEP and manufacturing parity remain open. [Sample-to-facet measurements](fidelity.json) · [Export and source records](manifest.json).

All arms kept the HF1440 source settings and the analytic round ring, with the same sampled axial span on the cap. Oriented source facets differed for each nonzero derivative. The symmetric nearest-node displacement was under 0.0002 mm for R1–R3 and K1/K2 against R0, around 1.46 mm for R4, and around 1.75 mm for C1/C2 against C0. C1/C2 and C0 all had 56 faces, despite the changed node positions. Before an acoustic contrast, pin the actual source boundary or separately quantify the residual from remeshing it. Explicit numeric cap forwarding now works on native and GRID mesh routes. Previously cached explicit-cap solves can contain an auto-cap mesh, so use clean identities and a fresh cache for any source-sensitivity arm. [Actual source patch comparison](source_patch_comparison.json) · [Source sensitivity and cache history](../ripple_program_2026-11-20/README.md).

**Decision.** Submit the mesh comparison for visual acceptance first. R2/R3 are the cleanest native body contrast because they share the new collar and projected opening. R4 is closest to R0's axial sweep and needs a controlled source patch. K1/K2 isolate the finish, and C1 is the first protected-host derivative worth checking after the exterior mismatch is characterized. C2 is a detailed geometry comparison arm with a weaker shell-normal separation result. Keep the original controls R0 and C0 in the cohort. Use R0 to benchmark archival performance, because comparing it directly with any new R design also introduces the new collar and shell construction. After the source and mesh gates, lock the v11 specification and observation grid. Quantify H/V cuts, 30°/45° and full balloon, listening-window and off-axis smoothness, DI slope/std, correlation, sidelobes, complex impedance, axial phase, and mouth pressure where available. Bracket 8–16 kHz separately for driver-cap sensitivity and spatial convergence. Routine search remains gated on controlled BEM.

## Reproduce

Run from the canonical checkout. The study needs the two archived runs and the historical bridge. Case surfaces, 6/8 epw meshes and diagnostic VTUs are under `scratch/sculpted_meridians/study/`. The plot commands use the saved mesh in metres and surface arrays in millimetres.

```powershell
.venv\Scripts\python.exe tools/geometry/sculpted_meridians_study.py --fine --export-mesh
.venv\Scripts\python.exe tools/geometry/render_sculpted_meridians.py scratch/sculpted_meridians/study/manifest.json --out scratch/sculpted_meridians/study/views_final
scratch\vizenv\Scripts\python.exe tools/geometry/check_sculpted_mesh_fidelity.py scratch/sculpted_meridians/study/manifest.json --out scratch/sculpted_meridians/study/fidelity.json
.venv\Scripts\python.exe -m pytest tests/test_sculpted_meridians_geometry.py tests/test_design_record_body_beak.py tests/test_rolled_terminal_geometry.py tests/test_mesh_grid_build.py -q -s -p no:cacheprovider -o addopts=
```

```text
36 passed in 17.75s
```

The separate six-worker CPU profile (`-m "not slow and not gpu and not crosscheck" -n 6 --dist loadscope -p no:cacheprovider`) reported unrelated-area failures and errors in the progress stream and stopped at 99% without a final summary. The focused geometry selection completed and provides the regression result for this study.
