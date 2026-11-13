<!-- Standalone handoff: deliver this entire file to a local coding agent in the Hornfab repo root. -->

> **LOCAL IMPLEMENTATION AGENT: START HERE**  
> This is an execution specification, not an instruction to implement every work package immediately. Read the repository instructions (`AGENTS.md`, `CLAUDE.md`, and applicable local skills), check the current branch, dirty tree, live lane locks and pinned dependencies, and then begin with **P0a, cache provenance**. Treat the SHA values below as a research snapshot; if `main` has advanced, reconcile source changes before editing. Do not overwrite existing work or launch GPU benchmarks without lane-owner authorization.
>
> **First deliverable:** a narrowly scoped, tested P0a change or an evidence-backed blocker report. Record the paths and cache entry types audited (single solve, band split, MEH, formula mesh, GRID/CAD), demonstrate same-pin hits and cross-pin misses, and preserve legacy records intact. Wait for the corresponding gate to pass before changing the BEAT or mesher fork pin.
>
> **Per work package:** create an isolated branch or change set; produce a small source diff, unit tests, captured benchmark commands and results (only if authorized), before/after acoustic and provenance checks, a pass/fail decision against the gates below, and a concise handoff for the next package. Do not merge multiple solver/mesher policy changes into one unreviewable implementation.

# HornFab senior engineering review and hardened implementation plan

**Baseline:** 2026-11-13. **Read-only research:** no GPU work, live queue changes, source edits or benchmark executions.  
**HornFab:** `llevaachingada/Hornfab@3ed7f568d30e2fdc76576598e5b54eb9b34662f3`  
**BEAT:** `llevaachingada/hornlab-beat-bem@0850ef39b29d7c51f8fbb082184d3784d2ff8bef`  
**Mesher:** `jamescollinharky/hornlab-waveguide-mesher@55da4f46d662d8dcd7a9f94a609eeea4009fcd62`  
**Hardware:** RTX 4060 Laptop 8 GB, i7-14650HX, ~32 GB RAM, Windows 11.  
**Objective:** maximize **verified acoustic information and verified-finalist discovery per whole-run wall-clock hour**, not nominal triangles per second.

## Executive decisions

1. **Add an urgent P0 cache-provenance safeguard, omitted by the incoming handoff.** The shared solve-cache lookup does not compare mesher/solver SHAs; mesh cache identity likewise lacks mesher SHA. This must be corrected before changing pinned forks. Keep old data, prevent silent attribution of old results to new code.
2. **Measure screen-to-verify ranking reliability before making screening cheaper.** Current evidence reports weak rank correlations, sometimes 0.1–0.3 Spearman in top-five groups. Isolate whether the cause is frequency-grid undersampling, mesh resolution, observation grid, or score method before selecting a new screen grid. Do not assert a single cause from the observed score differences.
3. **Use already-shipped frequency batching and region-aware meshing, not duplicate them.** `HORNLAB_FREQ_BATCH_SIZE=12`, `mesh.rear_res_factor`, and `mesh.band_split` exist. Validate on matching work; introduce no new control surface unless existing knobs prove insufficient.
4. **Prioritize a narrow BEAT fork fix to skip unused fused-CUDA GPU identity arrays.** Exact pinned source confirms allocation regardless of fused selection. The fused solve branch does not read them. Claimed 4.3 GiB at ~14k P1 / ~27.6k DP0 is *derived allocation size*, not verified peak saving. Change only this allocation in the first solver patch.
5. **Test the rear shell first by changing element density, not shape.** A coarser physical rear mesh preserves CAD geometry but not necessarily acoustic accuracy. A flat mathematical rear is a different physical model. Test separately.
6. **Put the high-band CPU proposal behind a DOF, RAM and physics gate.** The 25,171-DOF 16-kHz *mesh* test used a 1-kHz CPU solve and globally validated rigid walls only to ~10.3 kHz. It does not demonstrate full-band fidelity or a usable 50–100-horn CPU runtime.
7. **Extend the current band-split evaluator for selective finalists only after its seam test is repaired.** One backend per band, durable provenance, independent high-band records and cross-band accuracy gates. Avoid a second optimization/scoring architecture.
8. **Defer persistent GPU context, direct-device field evaluation, arbitrary adaptive BEM, curved higher-order elements and a new FMM solver** until measured bottlenecks and resolution needs justify each.

## 1. Corrections to the other agent's research

| Claim or proposal | Review verdict | Action |
|---|---|---|
| Fused CUDA unconditionally allocates identity cache | **Source verified at pinned SHA**, not peak memory-measured | Highest-priority isolated BEAT change after cache guard |
| Skip `cuda_solve_identity_cache` to save ~4.3 GiB at 14k/27.6k | **Allocation arithmetic only**; memory pool, lifetimes and LU workspaces make peak savings unknown | Pair old/new fork at same mesh, field, frequency, warm state and shared GPU memory |
| CPU was 6.4x faster near 8k DOFs | **Superseded.** It was old unfused/spilling CUDA | Fused 2-channel CUDA 2.66 vs CPU 5.96 s/frequency in November 3 audit; do not use older figures for backend routing |
| November 12 `8k` throughput arm implies 8 kHz limit | **Incorrect if interpreted as frequency**: `8k` labels approximate **DOF** class | Keep frequency limit separate from size/DOF limit |
| 16-kHz CPU benchmark establishes 16-kHz finalist economics | **Incorrect**: the large-mesh CPU benchmark was run at **1 kHz**; rigid walls estimated valid only to ~10.3 kHz | No time promises until high-frequency convergence and per-frequency CPU timing measured |
| T2 large horn can simply move to a 32-GB RAM CPU at 16–20 kHz | **Not established.** T2's globally valid 12-kHz mesh had ~34k P1 DOFs | Add estimated N, host RAM and dense-solver workspace refusal before expensive jobs |
| `mesh.band_split` is a new mechanism to build | **Already implemented** in `search/evaluate.py` | Harden instead: seam, mixed-backend routing, response/provenance merge and high-band-only CLI |
| Curvature-aware Gmsh setting can reduce DOFs | Current `curvature_npts` on STEP/CAD primarily **refines** existing global sizing; formula and GRID differ | Use as diagnostic only; defer new combined-field mesher until evidence |
| Uniform outer wall should always use a fixed ~25 mm resolution | **Unjustified**, especially 12–20 kHz | Compare controlled `rear_res_factor` levels and realized edge distributions |
| ATH rear can be simplified using `RearShape=2` | ATH 4.8.2 manual describes flat mathematical disc; **2026 ATH CORE actually uses `RearShape=3`**, `FrontOffset=40`, `Step=50`; pinned mesher's ATH text importer accepts only rear shape 1 | Keep actual CORE rear versus hypothetical simplified rear clearly separate; don't claim automatic import parity |
| Full prior archives already support rescoring under every future scorer | **False as a universal statement.** `objective/replay.py` supports replay dispatch for versions 1–4; v5–v7 need compatibility work | Preserve response data; mark replay support explicitly and test new score versions |
| `lib_shas` in dataset makes all caches cross-pin safe | **False.** Cache lookup does not test those SHAs; old response may be accepted and then attributed to a new run | P0 cache provenance remediation without deleting data |
| Bad triangle angles are main source of GMRES stagnation | **Disproven as a general explanation** by pinned mesher quality study | Deprioritize smoothing; investigate near quadrature, source tags, conditioning separately |
| Frequency-independent dense matrices can be reused across changed frequencies | **No.** Helmholtz matrices depend on wavenumber; P1 identity and geometric/quadrature preparation can be reused, LU normally cannot | Bound cache to genuinely frequency-independent items; no claimed factorization reuse |

### A critical capacity distinction

T2's measured global-edge-validation pass for **12 kHz** required **33,959 DOFs** at EPW 8.4. On the *same physical geometry*, a naive constant-area, h^-2 extrapolation gives ~60k DOFs at 16 kHz and ~94k at 20 kHz. **These are illustrative scaling scenarios, not mesh-build measurements.** Local clearance caps and geometry variation may change the result materially. At 34k DOFs, one dense complex64 N×N matrix is ~8.6 GiB; 60k is ~26.8 GiB; 94k is ~65.8 GiB, **before** workspaces and host memory. A 32-GB CPU does not resolve the underlying dense-BEM capacity problem. Do not equate a lower-fidelity source-patch-valid mesh with a whole-surface-converged one.

## 2. Source-based current architecture

- `hornlab_search/mesh/sizing.py`: wavelength-based throat/mouth/rear target sizes; requests, not realized maximum edges.
- `hornlab_search/mesh/build.py`: formula path; `rear_res_factor` applied to rear/outer and included in the formula cache suffix; mesh cache does **not** check mesher SHA. GRID and CAD routes branch into `grid_build.py`/`step_build.py` and currently lack the same shared formula mesh cache.
- Pinned mesher `density.py`: independent `inner`, `mouth`, `outer`, `rear`, `throat_disc`, interfaces; graded fields, rollback clearance and outer-wall guards. A freestanding BEM horn needs a closed or appropriately symmetry-reduced exterior boundary, not an arbitrary open skin. Coarsening the rear changes the discretization of an acoustically coupled surface.
- `hornlab_search/config.py`: opt-in `mesh.band_split`, `mesh.rear_res_factor`, CAD-only `curvature_npts`, user-custom frequency grid, verify caps, source controls.
- `hornlab_search/search/evaluate.py`: `split_freq_bands`, `_compute_band_split` and `_seam_check` exist. The seam test presently solves the **first frequency above an edge** on the lower band's mesh, potentially beyond its rated maximum. Record is diagnostic rather than an enforceable quality gate. Top-band-only traces are retained when enabled, not all bands.
- `hornlab_search/solve/beat.py`: persistent Julia host, `HORNLAB_FREQ_BATCH_SIZE` override, BEAT CPU and fused CUDA paths; regular separate CUDA calls by default. CPU/GPU results require physical parity and WDDM shared-memory tracking.
- `hornlab_search/solve/cache.py`: key `design_hash-mesh_hash-solve_hash`; `lookup` checks only `status.ok` and a loadable response; currently no SHA verification. `dataset/identity_v2.py` defines add-on physical/analysis/score/study IDs but the physical ID itself includes neither solver SHA nor a response checksum. `objective/replay.py` is not universal over all current objective versions.
- Current 2026-11-13 queue: `docs/research/QUEUE_PLAN_REV2_2026-11-13.md` reports some geometry ablation and fidelity jobs **queued, not executed**. Do not duplicate, preempt, or count them as evidence. Do not disturb existing CPU/GPU lane locks.

## 3. Priority work packages (do in sequence; no large campaign)

### P0a. Freeze baseline and prevent cache cross-pin contamination (blocker)

**Why:** Neither library commit is included in the shared solve-cache key. A solver/mesher pin bump with the same design, mesh and solve hashes can return an old response and record it under new library metadata. The formula mesh cache has the analogous mesher dependency issue. Existing `lib_shas` reporting does not prevent this.

**Edit:** `hornlab_search/solve/cache.py`, `hornlab_search/search/evaluate.py`, `hornlab_search/mesh/build.py`, `hornlab_search/dataset/identity_v2.py` and tests. Introduce explicit versioned cache namespace or required provenance comparison on lookup/store, covering solver SHA, mesher SHA and any physical algorithm policy that affects interpretation. Cache format/schema version also matters. Preserve and expose legacy entries, but permit reuse only when provenance can be proved; don't copy old cache bytes into new-version namespaces blindly. Keep existing `physical_solve_id` as a historical/logical join key and append an implementation-qualified ID/checksum rather than rewriting prior records. Add mismatch, missing-provenance and matching-provenance tests. Inspect all three single-mesh, band-split and MEH lookup paths.

**Gate:** A deliberately simulated pin change returns **cache miss**, never a mislabeled hit; exact same-pin repeated request still hits; old datasets and caches remain untouched. No production pin change before this passes.

### P0b. Establish useful-information baseline and screen fidelity decomposition

**Why:** In `THROUGHPUT_N1`, 95% of 104 paired verify-J values are worse than screen-J, and many small-cohort Spearman correlations are low. Absolute J shifts across changed grids alone are not proof of a bad ranking; poor rank agreement is the actual issue. Its suggested cause, inadequate coverage of 2.5–5.5 kHz, is plausible, **not isolated**.

Use existing cached finalists, `tools/calibration/plan_calibration.py`, `compare_calibration.py`, `tools/analysis/fidelity.py`, `tools/bench/timing_ledger.py`. A minimal crossed study on 6–10 representative, diverse candidates:

1. Existing screen mesh + existing frequency grid.
2. **Same mesh** + dense/targeted frequency grid.
3. Finer verify mesh + **same** screen frequency grid.
4. Finer verify mesh + dense frequency grid.

Hold source, observation radius, angles, backend, geometry, target and score function fixed. Test observation-angle/radius fidelity separately (note existing `fid_dist8m` and `fid_ang145` queue jobs; do not repeat). Score all responses with the **same scoring contract** on a compatible grid, or clearly mark unaligned comparisons. Record Spearman/Kendall, top-5/top-10 recall (where sample supports it), physical output errors, wall time, refusal counts and unknowns. Until calibration establishes a trustworthy short list, verify ~15–20 diverse finalists instead of top five only.

**Gate:** New screen policy is adopted only if finalist recall/rank agreement improves materially at acceptable whole-run cost and no important off-axis behavior is missed. Do not launch a larger optimizer merely because a cheaper mesh is possible.

### P1. Deploy measured frequency-batching policy with no fork change

**Already exists:** On 2026-11-12, `HORNLAB_FREQ_BATCH_SIZE=12` on fused CUDA improved warm 12-point times from 5.957 to 1.273 s (~1k DOF class), 18.040 to 8.488 s (~4k), and 47.075 to 25.015 s (~8k); classes approximate, exact DOFs not echoed. These are *solver-only*, not whole-candidate. **This `8k` is DOFs, not 8 kHz.**

**Work:** Test full candidate elapsed, actual source arrays and WDDM shared memory under the current queue-owned safe benchmarking process, with batch=1,4,12 on 2–3 frozen designs, 12 and 25 frequency grids where feasible. Avoid making a new config setting when the env override is adequate. Keep prefetch off near VRAM pressure: November 12 prefetch results did not show a justified solver improvement and unfused arms failed.

**Gate:** Repeatable whole-run improvement, identical frequency list and correct complex pressure/impedance, no shared-memory spill. Roll out per job, not blindly across different bands/sizes.

### P2. Eliminate unused fused-CUDA GPU identity-cache allocation (smallest source-proven fork change)

**Pinned source:** `hornlab_beat_bem/julia/BeatEngineDriver.jl:1533–1536` builds CPU identity matrices; `:1631–1667` builds CUDA identity cache **even when fused CUDA selected**; `:1848–1915` fused branch directly assembles and solves LHS/RHS, never accessing `cuda_solve_identity_cache`; `:2049` cache is read only in non-fused drive route. `BeatEngineCore.jl:1417–1423` materializes two dense `CuArray(Complex...)` identities. `:2251–2252` releases them. Before patch verify **all** readers and correction/source/impedance paths, and that flags are settled before the skip.

**Edit only** the fork `BeatEngineDriver.jl` + appropriate tests: construct CUDA solve identity cache when and only when non-fused CUDA actually needs it. No mesher, quadrature, scoring, or performance “cleanup” combined. Must not change multi-channel handling or near correction's permitted modes. Follow `docs/FORKS.md` with a new immutable SHA, validation and revert route. First deploy in isolated trial only after P0a.

**Measure:** same cold/warm mesh at ~4k, ~8k, near existing safe high limit; dedicated peak, **Windows shared peak**, CUDA.jl live versus reserved, wall, assembly/LU, field, errors, repeat variance. Derived omitted arrays ~`8*(N² + N*E)` bytes; this does not guarantee equal peak saving or a larger viable DOF limit.

**Gate:** analytic selftest, crosscheck, per-channel and impedance parity within established *measured numerical variability*, no stale workers/spill, meaningful net memory improvement and/or increased safe DOF. Never require universal bit identity on FP32 CUDA. If no observed gain, revert and document the negative result. **Do not** bundle CPU identity matrix optimizations or LU rewrites.

### P3. Rear-shell element-efficiency study (same geometry, different tessellation)

**First the conceptual distinction:** (a) keep rear CAD geometry but use larger surface triangles; (b) construct a geometrically simpler rear, e.g., ATH's mathematical flat disc; (c) an enclosure/infinite-baffle model changes the acoustic boundary problem. These are **not** interchangeable. The closed source, throat, mouth-rim seams and appropriate symmetry must remain valid. ATH CORE 2026 uses `Mesh.RearShape=3` and an explicitly shaped rear, not flat-disc mode. The pinned mesher's ATH text import rejects other rear shapes besides 1, so full CORE parity cannot be assumed.

**Low-code first:** `mesh.rear_res_factor=1.0, 1.5, 2.0, 2.4/2.5` in copied configs with same physical horn, same inner CAD, same frequency grid/solver. The outer-wall clearance guard can force local refinement; measure *actual* per-region triangle count/DOF and edge max/p95, chord/normal deviation and intersections. Gmsh seam constraints can alter inner triangulation even though CAD is constant; compare that too. Use 4 seed horns: modest OSSE, rolled R-OSSE, H/V or sculpted ATH-like morph, large T2 if memory safe. Start mesh-build and source validation only, then a small common-frequency acoustic A/B with an independently refined reference.

**Geometry-difference phase only after density results:** build one optional realistic-versus-simplified rear geometry arm. It is a *physical-model ablation* for diffraction/impedance, not a demonstrated mesh-only acceleration. Preserve lip radius and freestanding radiation conditions. Do not add a generic `rear_shape` user knob before a successful prototype.

**Gate:** geometric integrity, source patch, symmetry, same physical geometry for the density test, converged H/V/diagonal/full balloon directivity and throat impedance, and a statistically meaningful end-to-end saving. Reject even large triangle reductions if directional/impedance sensitivity fails or the clearance guard eats the gain.

### P4. True mesh-fidelity diagnostic (not global EPW inflation)

Start with per-**physical-region** counts/edge percentiles and chord error: source, throat transition, inner wall, lip/roundover, aperture rim, rear shell and rear cap, and additional ports/septa. Mesher `mesh_surface_groups` knows role labels before export, but the output's physical tags may not retain all of those roles; add an offline role-summary artifact if required. Do not infer region from a single undifferentiated wall tag.

Create `mesh_fidelity_status` with at least: (1) source/adjacent valid, other walls coarse; (2) globally max-edge-valid; (3) CAD geometry fidelity checked; (4) acoustically converged vs named reference; (5) not assessed. The STEP `global_warn_source_hard` accepts underresolved remote walls; preserve the warning without presenting it as full-wall fidelity. Different geometry routes need route-specific reporting, with common definitions.

`curvature_npts=0/8/12/20` on STEP only may identify missing fillet refinement but mainly **adds** triangles. Do not promote it as a DOF-saving optimization. Gmsh supports restricted size fields and min combinations; the pinned point-grid mesher already turns off global from-points/curvature/boundary extension where it controls size itself. Do not reimplement it. Do targeted feature-amplitude, local normals and chord tests for ATH-like ridges at separate geometric-prototype fidelity.

**Gate:** metadata predicts actual local mesh-quality problems and the physical convergence study, rather than just producing prettier triangles. Strict global max-edge is a conservative *screen*, not a sufficient or universally necessary proof of acoustic convergence.

### P5. Band-split A/B and efficient, qualified seam tests

**Already shipped:** `mesh.band_split: {edges_hz: [...]}` partitions the same requested grid, sizes each mesh for its band top and caches responses separately. It can be faster by avoiding high-res assembly at lower frequencies, but total mesh-build overhead and different discretization errors are unmeasured.

**Fix first:** `_seam_check` currently solves first frequency **above** an edge on the lower-band mesh. Instead compare at the last lower-band frequency (which is at or below the mesh's valid limit): solve that same frequency on the upper band's qualified mesh, then compare on-axis/complex response, polar beamwidth, DI, impedance and phase as applicable. If edge=last point, that is ideal. Alternatively insert an explicit shared edge probe on both meshes. Make failures and exceedances enforceable in verify mode, not just metadata. Define that bands have compatible physical geometry, boundary/source tags and solver inputs. Record *per-band* mesh hash, validator status, DOFs, backend, cache provenance and trace coverage.

**A/B:** one mesh for entire 300–12/16-kHz range vs 2 bands (e.g. 2–3 kHz boundary) vs 3 bands on 2–4 existing designs. Identical request frequencies, source, observations and geometry. Count additional mesh builds, shared cache hits and seam probes. No promised 2–4× until a matched end-to-end measurement exists.

**Gate:** physical response agrees with a common finer reference, seam passes, entire requested frequency list remains unchanged, benefit survives extra mesh and validation time, and cache/score provenance is unambiguous.

### P6. Selective, feasibility-gated 8–20-kHz finalist verification

**Do not make `CPU` the default for >8 kHz.** Route by *realized DOFs, memory, source model and measured wall*, not frequency label. Fused CUDA can solve high frequencies on small enough horns; dense BEAT CPU may be impossible on fully resolved large T2 horns despite enough CPU cores.

**Proposal:** existing low-band screen and verify first; select 10–20 **diverse, verified** finalists with both score and acoustic-shape diversity, not simply the 100 lowest historical J values. Trial 8–12 kHz on 3–5, then 12–16 kHz on ~2–5, then 16–20 kHz on only designs passing strict feasibility and source assumptions. Do not use high-band J as a directly comparable score to full-band J. Use separate descriptive HF metrics until a clearly specified objective defines how bands are integrated.

**Feasibility preflight for each horn and target upper frequency:** build mesh on CPU only; determine global/source-adjacent/cad fidelity; count DOFs; predict dense memory lower bound and measure a safe CPU trial; flag likely OOM before launching. Record frequency count and observation cost. Start with one representative high frequency, not the whole sweep. The Nov 3 25,171-DOF MEH mesh test was a **1-kHz** CPU solve of ~100.7 s and globally valid walls only ~10.3 kHz: not a 16-kHz time forecast.

**Pipeline extension, after P5:** `verify --run ... --designs-file ... --freq-range 8000:16000 --backend beat_cpu --verify-dir ...` is a **proposed new interface, not an existing command**. Implementation must reuse `search/evaluate.py`, `config.mode_freqs/solve_spec`, selected-design logic and cache, return a high-band record with independent identity, and optionally combine validated prior low-band responses for analysis. A future per-band backend router can choose fused CUDA or CPU using an empirically measured threshold, no blind hardcoded 8-kHz switch. Respect concurrent lane locks and no image-name process killing.

**Gate:** measured per-frequency wall and peak host RAM for representative size categories, full-wall mesh status or explicit agreed fidelity caveat, selected-source validity, memory margin and accurate observations; stop any 20-kHz plan that requires an impossible dense matrix. No 50–100-horn commitment based on one low-frequency timing sample.

### P7. Boundary-trace reuse and other narrowly scoped data improvements

The current BEAT adapter can capture surface P1 pressure / DP0 Neumann traces on selected solves, but `trace_fraction` defaults to 0.05, and band-split currently stores traces for the highest band only. A higher-value data proposal than an elaborate persistent GPU mesh cache is **retain complete per-band boundary traces for a small number of finalists**, enabling a separately validated re-evaluation at new angles, distances or balloon grids without rebuilding/factoring the dense boundary operator. This does **not** recalculate pressure at new frequencies or from a different source. Storage cost, precise trace provenance and a postprocessing field-evaluation adapter need testing. Previous records without traces cannot use this shortcut.

**Gate:** independent field re-evaluation reproduces same-solve cuts/balloon pressure (including complex phase) at matching observation points; track trace bytes and field wall time; no false promise of a new BEM solve being avoided for new frequencies.

### P8. Advanced research backlog, NOT immediate implementation

| Candidate | Rank | Reason and trigger |
|---|---|---|
| Faster CUDA regular quadrature order / wavelength selector | Next solver experiment **only if** P2 and mesh studies insufficient | High assembly share, but changing integration order changes accuracy; validate against higher quadrature and near-thin-wall tests |
| LU workspace/pooling and GPU transfer overlap | Diagnostic-first | Profile peak live and reserved arrays, cuSOLVER, real/imag buffers; only optimize confirmed material overhead |
| Persistent prepared mesh/GPU context across calls | Defer | The 12-frequency batching already amortizes most construction; across candidates geometries differ, and band splitting uses distinct meshes. Demonstrate extra improvement beyond batching first |
| Direct GPU pressure-to-field path | Defer | Pinned fused solver currently downloads pressure (`return_gpu=false`) and CUDA field evaluation reuploads it. Likely secondary next to assembly; test only after memory patch |
| Global smoothing, edge swapping | Defer | Prior mesher study substantially improved quality but fixed only 1 of 6 stubborn GMRES cases; not a compelling performance target |
| New full goal-oriented / adjoint BEM refinement | Research | Sound mathematical basis but custom error estimator for current Burton–Miller P1/DP0, not cheap to integrate |
| Curved/higher-order elements | Research | Requires solver basis, kernels and singular quadrature changes, not a Gmsh flag |
| NumCalc / Mesh2HRTF ML-FMM | **Best independent large-N feasibility spike** | Published Burton–Miller/FMM acoustic code; use `NumCalc -estimate_ram`, sample mesh, independent radiation parity. Not P1/DP0 drop-in, verify symmetry, source and normal handling |
| FMM3D / hfmm3d | Reference/kernels only | CPU Helmholtz particle-kernel library, not complete BEM. Its docs warn about suboptimal high-frequency FMM behavior; needs formulations/preconditioner/near integration |
| Bempp OSRC Burton–Miller | Solver prototype | Explicit OSRC example, but preconditioner and symmetry compatibility uncertain; benchmark end-to-end and operator parity |
| Dedicated axisymmetric multimodal solver | Specialized future | Potential major efficiency for truly axisymmetric horns only; cannot reproduce ATH X-morph or asymmetric sources |
| Reduced-order frequency sweeps | Later | Frequency-response approximation needs independent exact-frequency checks and preserved approximate fidelity labels |

## 3A. ATH configuration interpretation (avoid false mesh comparisons)

The ATH 4.8.2 guide, page 20, confirms that `Mesh.AngularSegments` is the number of calculated profiles around the horn, `Mesh.LengthSegments` is the number of axial geometry slices, and `Mesh.CornerSegments` reserves profiles at rounded-rectangle corners. The 2026 ATH CORE author describes `NAC` as the angular index of its diagonal. These **primarily determine the shape sampling/grid**, distinct from Gmsh's final local acoustic triangle-size fields. They are not comparable to BEAT's `ObservationSpec.angle_count`, nor do `100 * 20` points directly specify the solver's DOF count. For a controlled ATH comparison, preserve the same physical contour and sample its CAD deviation before comparing final Gmsh edges and unknowns. `Mesh.InterfaceResolution=8` is unused in CORE's stated example.

### Operator-facing commands (read-only until a lane is authorized)

```powershell
# Pin/version and unit-test checks (no solver campaign).
git rev-parse HEAD
.\.venv\Scripts\python.exe -m pytest tests/test_solve_cache.py tests/test_mesh_sizing.py tests/test_obj_replay.py -q

# Discover exact current bench CLI; do not assume old arguments are still supported.
.\.venv\Scripts\python.exe tools/bench/mesh_policy_study.py --help
.\.venv\Scripts\python.exe tools/bench/throughput_matrix.py --help

# The confirmed batching switch for an authorized and isolated GPU run:
$env:HORNLAB_FREQ_BATCH_SIZE = "12"
# Actual timed command only after queue/lock checks, with frozen baseline and output path:
# .\.venv\Scripts\python.exe tools/bench/throughput_matrix.py --config examples/osse_baseline_fusedcuda.yaml
```

New `verify --freq-range` and a mixed-backend band router are proposals, **not commands available on current main**. Avoid `--allow-config-change` for comparative search-resume work because it explicitly mixes old/new-J rows. Never run `gpu-clean`, kill Julia processes by image name or overwrite a cache while another lane is active.

## 4. Measurements and acceptance contract

**Frozen test manifest per arm:** horn design hash/parameters, physical CAD/GRID shape, exact mesh path/checksum and mesher SHA, requested and realized element size per region, P1 DOFs/DP0 faces, source/symmetry and tags, frequency array and grid semantics, backend/solver SHA/flag/quadrature/corrections/precision, observation radius/angles/balloon, cache state, score version and brief, Windows host tree, CPU/RAM and GPU dedicated/shared peaks, warm/cold state, actual wall time and retry/refusal counts.

**Geometry:** watertight or proper symmetry boundary topology, source patch and wall clearance unchanged, no self-intersections; physical-feature amplitude, lip normal, chord deviation preserved. For geometry-only rear experiments compare physical models explicitly, never count a geometry change as same-mesh speedup.

**Acoustic reference:** choose a feasible finer mesh and stronger quadrature where possible; verify source, near-rim and representative exterior regions with controlled refinement. Compare on-axis and off-axis complex pressure/phase, H/V/diagonal, full 3D balloon, beamwidth and lobes, DI and complex throat impedance, across frequency. Track worst-direction and worst-frequency errors, not averages alone. Existing HornFab gates (e.g. normalized ReZ ~0.03, beamwidth ~2°, DI ~0.2 dB) are provisional starting contracts; high-frequency narrow lobes may require stronger requirements. If reference itself cannot converge in available resources, label the result **not established**.

**Performance:** direct GPU process metrics + WDDM shared usage, CUDA.jl live/reserved, CPU resident RAM and memory bandwidth/threads, mesh build, geometry precheck, matrix assembly, LU, field, score, data store/cache, retries and failures. For concurrent work use actual elapsed critical path, not sum of overlapping timers. Report both `successful physically verified designs / elapsed hour` and `verified top-k finalist recall / elapsed hour` compared with a frozen reference. Record negative and inconclusive outcomes.

**Data:** immutable old response files, explicit checksum and source SHA; no cache key collisions across physical implementation changes; new and old score identities separate. Reuse previous wavefields only for calculations their stored frequency/angle/trace/source/mesh fidelity supports. A scorer revision does not automatically invalidate physically stored responses; a high-frequency, source or observation change may require new physics.

## 5. Decision gates and stop rules

- **Gate 0, before any new pin:** provenance-hardened caches, tests pass with same SHA/mismatch/legacy cases, no prior data deleted.
- **Gate 1, before redoing scores or searches:** frequency/mesh source of screening rank error isolated, justified candidate-selection policy; benchmark whole-run cost and verified finalist recall.
- **Gate 2, before adopting fork optimization:** source-proven identity-cache skip yields measured real memory/throughput benefit or higher safe DOF, with same-physics parity and no shared spill. Negative result closes the task.
- **Gate 3, before coarsening rear as default:** realized DOF reduction, full acoustic parity at named frequencies and candidate classes, and end-to-end cost improvement. Clearance guard forced refinement or unacceptable lip/diffraction changes stops it.
- **Gate 4, before band-split default:** qualified overlap seam, entire request-grid parity, no missing partial outputs, cache and trace correctness, improved complete-campaign elapsed.
- **Gate 5, before 16–20 kHz finalist campaign:** per-horn CPU/GPU feasibility report, measured one-frequency wall and RAM, verified global or explicitly limited wall fidelity, source physics meaningful; no extrapolated 50/100-horn schedule.
- **Gate 6, for alternative BEM:** only after dense method cannot hit the required source/physics/mesh objective. Use one same-mesh cross-check, memory feasibility, convergence and independent NumCalc/OSRC results before planning a new backend.

## 6. Agent task split (minimize parallel conflict)

1. **Read-only auditor:** confirm current commit/pins, active queues, cache provenance, screen/verify evidence, per-route mesher semantics; write exact evidence manifest and tests to add.
2. **HornFab Python integration owner:** P0 cache protection, objective replay compatibility reporting and band seam tests on a separate branch. No scorer changes, no new optimization algorithm.
3. **BEAT fork owner:** P2 identity-cache patch only, after P0 and permission to test an isolated GPU lane; follow `docs/FORKS.md`. No installed `.venv` hand-edits.
4. **Mesher/physics study owner:** config copies and CPU-only mesh audit; no mesher-fork changes until A/B supports them; preserve the actual pinned CORE/ATH geometry distinction.
5. **Benchmark owner:** freeze cohort, run paired safe tests only in an authorized lane, use `docs/throughput/S9_PERFORMANCE_PREPARATION_2026-11-12.md` ledger and `tools/bench/throughput_matrix.py`; report complete wall, shared spill and physical parity.
6. **Integrator:** accept/reject each independently validated patch, update immutable SHA and docs, and merge one gate at a time. No live optimization or scoring changes without a controlled calibration comparison.

## 7. Technical references and source map

Repository evidence (exact main snapshot):

- [THROUGHPUT_N1](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/docs/evidence/THROUGHPUT_N1_2026-11-12.md)
- [BENCH_AUDIT](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/docs/evidence/BENCH_AUDIT_2026-11-03.md)
- [HARDWARE](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/docs/evidence/HARDWARE_2026-11-01.md)
- [BENCH_CPU_VS_CUDA](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/docs/evidence/BENCH_CPU_VS_CUDA_2026-11-03.md) (historical CPU speed claim superseded by BENCH_AUDIT, but 16-kHz mesh/1-kHz CPU probe details retained)
- [HF12K_VERIFY](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/docs/evidence/HF12K_VERIFY_2026-10-23.md)
- [S9_PERFORMANCE_PREPARATION](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/docs/throughput/S9_PERFORMANCE_PREPARATION_2026-11-12.md)
- [WP1 identity-cache plan](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/docs/throughput/WP1_FUSED_IDENTITY_CACHE_PATCH.md)
- [QUEUE_PLAN_REV2](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/docs/research/QUEUE_PLAN_REV2_2026-11-13.md)
- [FORKS policy](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/docs/FORKS.md)
- [solve cache](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/hornlab_search/solve/cache.py), [evaluate](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/hornlab_search/search/evaluate.py), [mesh build](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/hornlab_search/mesh/build.py), [dataset identity](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/hornlab_search/dataset/identity_v2.py), [replay](https://github.com/llevaachingada/Hornfab/blob/3ed7f568d30e2fdc76576598e5b54eb9b34662f3/hornlab_search/objective/replay.py)
- [Pinned BEAT driver](https://github.com/llevaachingada/hornlab-beat-bem/blob/0850ef39b29d7c51f8fbb082184d3784d2ff8bef/hornlab_beat_bem/julia/BeatEngineDriver.jl) and [Pinned BEAT core](https://github.com/llevaachingada/hornlab-beat-bem/blob/0850ef39b29d7c51f8fbb082184d3784d2ff8bef/hornlab_beat_bem/julia/src/BeatEngineCore.jl)
- [Pinned mesher density](https://github.com/jamescollinharky/hornlab-waveguide-mesher/blob/55da4f46d662d8dcd7a9f94a609eeea4009fcd62/hornlab_mesher/density.py), [mesh quality](https://github.com/jamescollinharky/hornlab-waveguide-mesher/blob/55da4f46d662d8dcd7a9f94a609eeea4009fcd62/docs/mesh-quality.md)

External primary sources:

- [ATH CORE (2026) original rear shape 3 and mesh settings](https://www.at-horns.eu/core.html) and [ATH user guide (historical RearShape 1/2)](https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf)
- [Gmsh mesh-size fields and boundaries](https://gmsh.info/doc/texinfo/gmsh.html)
- [CUDA.jl live/reserved memory and pool](https://cuda.juliagpu.org/dev/usage/memory/)
- [NumCalc BEM / ML-FMM paper (2024)](https://doi.org/10.1016/j.enganabound.2024.01.008) and [NumCalc RAM estimator and runner](https://mesh2hrtf.readthedocs.io/en/latest/mesh2hrtf.html)
- [Bempp Burton–Miller OSRC example](https://github.com/bempp/bempp-cl/blob/main/examples/helmholtz/osrc_burton_miller.py)
- [FMM3D docs, including high-frequency method limitation](https://github.com/flatironinstitute/FMM3D/blob/master/docs/index.rst)
- [Adaptive exterior Helmholtz BEM error estimator, 2025](https://www.sciencedirect.com/science/article/abs/pii/S0022460X25003177)
- [Matrix-free model reduction for BEM frequency sweeps, 2022](https://doi.org/10.1016/j.jsv.2022.117323)
- [Axisymmetric finite-enclosure horn directivity, JASA 2024](https://pubmed.ncbi.nlm.nih.gov/38546169/)

**Intentionally omitted from immediate implementation:** new scoring versions, general horn geometry optimizers, broad simultaneous solver/mesher changes, large CPU/GPU campaigns, unlimited rear coarsening, new higher-order elements and custom FMM. Each would introduce more confounders before the existing numerical and pipeline capabilities have been characterized.
