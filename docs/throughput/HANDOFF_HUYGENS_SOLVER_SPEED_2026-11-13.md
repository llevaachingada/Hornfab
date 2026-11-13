# Hornfab / Huygens: High-Frequency Solver Throughput
## Senior engineering review, approval, and staged implementation handoff

**Date:** 2026-11-13  
**Status:** **PROPOSAL ONLY. NOT APPROVED FOR IMPLEMENTATION.**  
**Target:** `llevaachingada/Hornfab`, current `main` at review time; observed `9380b81942f0879294c28b295cdfb5a0d5b9bfb5` (2026-11-13 20:28:56 UTC). Re-read `main` and local changes before acting.  
**Hardware:** Owner: Windows 11 laptop, Intel i7-14650HX, 32 GB RAM, NVIDIA RTX 4060 Laptop, 8 GB VRAM. Collaborator: Apple Silicon MacBook (exact chip and RAM **not established**).  
**Mandate:** Make 3D horn/waveguide acoustic simulation substantially faster and extend practical frequency range **without compromising physically credible results, past datasets, search continuity, or UI reliability**.

> **To the local senior agent:** Review and harden this document **before implementing anything**. Identify unsupported assumptions, compare it against the current checked-out code and active work, and return (1) GO / GO WITH CONDITIONS / NO-GO for each phase, (2) corrected file/function targets, (3) minimal test plan, (4) prioritized bounded tasks with owners, (5) numerical/physics risks, (6) conflicts with other active agents or runs. **Do not change defaults, start GPU jobs, kill hosts, or modify files in this first review pass.** Do not treat any speculative speedup as a promise. Where current code contradicts this document, current code wins, and the discrepancy must be reported.

---

## 0. Owner-facing objective and definition of success

Hornfab is a horn/waveguide design tool: the user specifies coverage, operating frequency, geometry and mounting constraints; the optimizer makes designs, meshes them, solves their 3D acoustics, evaluates response/polars/impedance, and keeps the best candidates. Current high-resolution or broad-band solves can take tens of seconds to minutes per horn, making optimization and 20 kHz validation expensive. Huygens reports solving a small, symmetric ATH waveguide from 1–20 kHz in **1.2 seconds** on an M4 Pro Mac mini. This is an informative benchmark, **not an equivalent benchmark on a large Hornfab horn**.

Success is:

1. **Faster physical evaluations per hour** at **fixed acoustic accuracy** and identical source/geometry/boundary conditions, rather than just faster mathematical execution with a looser mesh.
2. **Fewer out-of-memory or shared-memory spill events**, especially in 10–20 kHz verification.
3. **No change to the meaning of the acoustics or objective** from a performance setting. Historical results remain valid, recoverable, and correctly versioned.
4. **A comprehensible normal-user interface:** select a design goal, choose a suitable solve fidelity, see predicted feasibility and runtime, launch through the existing job manager, receive comparable response curves, and know whether the result is screened or verified.
5. **Graceful fallback** when an acceleration method is incompatible, unstable, unavailable on the machine, or slower than the proven baseline.

**Non-goals for this effort:** BoTorch integration; score version proliferation; reweighting directivity/loading objectives; introducing an unvalidated new horn typology; relaxing acoustic fidelity to meet a headline number; buying hardware; rebuilding the GUI; treating Apple Metal as a CUDA API.

---

## 1. What Huygens actually reports, and what it does NOT establish

Primary external source: Arnaud Demion, *A Boundary Element Solver on Apple's GPU, Checked Against AKABAK*, October 2026, https://demaudio.com/blog/bem-on-the-gpu/ . Huygens 0.1.0, results dated October 4, 2026.

### Reported results (author-reported; not independently reproduced here)

| Test | Huygens result | Important scope |
|---|---:|---|
| ATH OSSE example | **1.2 s total**, 40 frequencies, 1–20 kHz | Finest mesh **12,640 triangles**; mesh varies with frequency; compact, symmetric waveguide case |
| Small elliptical waveguide, ATH mesh | **4.2 s**, 40 frequencies, 500 Hz–16 kHz | Finest mesh **4,660 triangles**; raised skirt changes integral path |
| Same small waveguide, Huygens-generated mesh | **8.5 s**, 40 frequencies | Finest mesh **6,216 triangles** |
| Six waveguides, same Mac and meshes vs `hornlab-metal-bem` | ~**1 s** Huygens vs **7.3 s** HornLab quarter-domain, **98 s** HornLab full-domain | Author says comparison includes meshing; different cases and configurations from Hornfab's large horns |
| Huygens vs AKABAK, identical ATH waveguide elements | Median polar deviation **0.007 dB**, max **0.30 dB** at 16 kHz far off axis | Different RMS vs peak convention corrected by 3.01 dB; AKABAK far-field convention aligned |
| Huygens vs exact vibrating-cap sphere | ≤**0.13 dB** across tested frequencies | Closed-body reference, not speed proof on a large waveguide |

### Huygens methods explicitly described by author

- Galerkin BEM with special singular/near-singular quadrature.
- Burton–Miller for closed bodies; infinite rigid baffle represented with a half-space Green function for eligible waveguides; quarter symmetry where valid.
- Frequency-varying mesh density; do **not** interpret 40 frequencies as 40 solves on a 20 kHz mesh.
- **Metal GPU** assembles dense matrices in float32; **CPU iterative** solver consumes them; unified Apple memory avoids discrete GPU→CPU matrix transfer.
- **Pipelined sweep:** assembly of frequency `i+1` overlaps solving `i`.
- GPU-vs-CPU integration paths depend on geometry. Raised mouth skirt cases reportedly trigger expensive CPU integration, making a smaller mesh slower than a larger flat-mouth mesh.
- Double-precision CPU reference used in continuous numerical regression testing.

### Explicit limits / unresolved questions

- A public source repository for Demion's **Huygens 0.1.0** was **not located/verified**. Do not invent repository access or claim to have inspected its private kernels. The publicly accessible **HornLab Metal** code below is a *related comparison/implementation reference*, **not Huygens source code**.
- The article does **not** establish that Huygens solves an arbitrary 3D free-standing, asymmetric, thick-walled, multi-source horn at 20 kHz in 1.2 s.
- Whether its fast waveguide benchmark uses a less expensive boundary operator than Hornfab's fused exterior Burton–Miller remains a **hypothesis requiring source/author clarification and cross-physics testing**.
- The published timings are on an **M4 Pro Mac mini**, not the collaborator's as-yet-unspecified MacBook and not the RTX 4060.
- It does not establish that switching Hornfab to CPU GMRES will itself reach 1.2 s.
- The source article cites foundational acoustic mathematics, not a disclosed set of speed-optimization papers. Differentiate acoustic validation references from performance method references.

### Huygens sources the senior agent must re-read

- Blog and methods: https://demaudio.com/blog/bem-on-the-gpu/
- Burton & Miller (1971): classical combined-field exterior BIE, DOI/catalogue links from article. Physics/uniqueness, not speed technique.
- Schenck (1968): CHIEF/irregular-frequency mitigation, physics/uniqueness, not speed technique.
- Morse & Ingard, *Theoretical Acoustics* (1968): analytical spherical radiation validation.
- Siemens BEMAO DAGA 2023: https://pub.dega-akustik.de/DAGA_2023/data/articles/000555.pdf
- Atak et al., BEMAO theory (ISMA 2022): https://past.isma-isaac.be/downloads/isma2022/proceedings/Contribution_313_proceeding_3.pdf
- Public comparison implementation: https://github.com/m3gnus/hornlab-metal-bem

---

## 2. Verified Hornfab code/evidence inventory (recheck all against local HEAD)

**Owner repo:** https://github.com/llevaachingada/Hornfab  
**Pinned BEAT fork:** https://github.com/llevaachingada/hornlab-beat-bem  
**Main project solver dependency in inspected `pyproject.toml`:** `hornlab-beat-bem` @ `0850ef39b29d7c51f8fbb082184d3784d2ff8bef`. Do not assume another branch is installed on the laptop.

### Existing features, not new features to reinvent

| Feature | Observed implementation | Crucial detail |
|---|---|---|
| Dual-plane native symmetry | `hornlab_search/mesh/sizing.py`; `mesh/build.py`; `solve/beat.py` | `quadrants: "1"` means quarter model with `yz+xz`; not valid for arbitrary asymmetric horn |
| Fused CUDA Burton–Miller | `solve/beat.py`; fork `julia/src/BeatEngineCudaBurtonMiller.jl` | **Opt-in** `solve.cuda_fused: true`; baseline `examples/osse_baseline.yaml` doesn't enable it; fused example does |
| Frequency-band meshes | `config.py` `mesh.band_split`, `search/evaluate.py::_compute_band_split` and `_seam_check` | Separate meshes, frequencies and solve-cache entries by band; not automatically enabled in every configuration |
| Rear/outer shell mesh coarsening | `mesh/build.py::res_mm_for_spec`, `config.py` `mesh.rear_res_factor` | Changes outer shell and rear cap, not acoustic throat/bore/mouth surface; validate result before adoption |
| Curvature meshing | `config.py` `mesh.curvature_npts` | Not proof that all curvature-dependent sizing is globally optimal |
| Dense CUDA solve | Fork `BeatEngineCudaBurtonMiller.jl`; `julia/src/BeatEngineDenseSolve.jl` | Fused CUDA LU on GPU; changing `gmres_tol` in YAML **does not** turn it into GMRES |
| CPU/Metal GMRES | Fork `BeatEngineDenseSolve.jl` | Uses different preconditioning from native HornLab Metal implementation; must distinguish solve formulations |
| Existing cross-check and provenance | `solve/bempp.py`, `solve/cache.py`, `types.py`, `docs/FORKS.md` | Keep solver version, mesh, boundary conditions, frequency grid, observations and numerical method identities separate |
| Existing GUI | `gui/jobs.py`, `gui/server.py`, `gui/data*.py`, `gui/static/app.js`, `gui/static/verify.js` | GUI is a **launcher/viewer**; computations run through the allow-listed CLI/job system, never in-process |

### Existing measured performance (not predictions)

Source: `docs/evidence/FUSED_CUDA_2026-10-24.md`:

| Quarter-domain DOFs | Fused CUDA per-frequency | Observation |
|---:|---:|---|
| 8,919 | 9.11 s | Baseline test; 2.2 GB incremental peak VRAM |
| 12,183 | 13.72 s | ~4.7 GB incremental peak VRAM |
| 15,984 | 458.6 s | Fits, but assembly consumed ~437 s; memory pressure cliff |
| 20,237 | Did not complete | Worker host died; no valid solve |

Source: `docs/evidence/BENCH_AUDIT_2026-11-03.md`:

- An 8,044-DOF two-source mesh on old four-operator CUDA used roughly **38.8 s/frequency** and spilled heavily into Windows shared RAM; **fused CUDA ~2.66 s/frequency** with ~2.1 GB dedicated memory under matched test conditions. Major past bottleneck **was an avoidable implementation path**.
- `docs/evidence/BENCH_FULLRANGE_THREADS_2026-11-03.md` and `docs/evidence/BENCH_40_DESIGNS_2026-11-03.md` show CPU/CUDA crossover is geometry- and setup-dependent. Do not turn one benchmark into a universal CPU-vs-GPU ranking.
- `TOOLCHAIN.md` records the 8 GB RTX 4060, 32 GB RAM, Julia version and historical pinned SHAs; read current values instead of repeating stale numbers.
- `docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md` already explores quadrature-order reduction, CUDA GMRES, FMM and axisymmetric approaches. It is a useful **research baseline**, not evidence that the proposals shipped.

### What the repo's mesh formula means

`hornlab_search/mesh/sizing.py::res_mm_for(epw, fmax)` uses `h_mouth = c/(epw*fmax)` and `h_throat = h_mouth/2`. At 20 kHz and 6 elements/wavelength, mouth is about **2.86 mm**, throat **1.43 mm**. Total DOFs depend on *actual horn surface area, shape, shell, source and symmetry*. Do not infer 20 kHz memory from frequency alone. The old toolchain table includes ~8,941 quarter-domain DOFs at 3.0 mm mouth/1.5 mm throat on **one small OSSE**, not on arbitrary larger horns.

Memory of one dense complex float32 N×N matrix is `8N²` bytes; factorization, corrections, assembly buffers, memory pools and multiple operators add overhead. **Dense GMRES with a resident matrix is still O(N²) memory**, even if it avoids extra LU workspace. Only matrix-free/compressed operator methods materially remove the underlying quadratic storage.

---

## 3. Critical acoustic equivalence gate

A solver may be faster because it solves a **different physical problem**. No performance claim is accepted until an apples-to-apples comparison fixes:

1. **Geometry:** same closed/reduced Gmsh mesh when testing solve engine; record triangle count, P1 DOFs, exact mesh bytes/hash, throat/mouth/rear element sizes, shell/mounting, symmetry.
2. **Boundary domain:** free-space/freestanding vs **infinite rigid baffle** vs finite enclosure; don't silently replace one with another.
3. **Source:** same velocity amplitude and motion (normal vs axial), phase, source area/tag(s), peak vs RMS convention, prescribed Neumann profile and multi-entry sources.
4. **Formulation:** BM vs conventional CBIE vs shifted complex-k; treatment of irregular frequencies; near/singular integrals; precision; tolerances; harmonic sign convention.
5. **Observations:** far-field vs finite distance (Huygens article notes AKABAK far-field convention); H/V/diagonal polar grid, balloon/equal-area weighting, diffraction/post-processing, `di_source`.
6. **Frequency grid:** exact same frequencies, especially top octave and resonant gaps; no 12-point sparse screen compared with a 40-point sweep.
7. **Numerical reference:** at least one independent high-resolution/high-accuracy reference and mesh convergence test. Close agreement between two approximate solvers on the same coarse mesh is not enough.
8. **Timing scope:** mesh generation, cache hits, startup/JIT, GPU transfer, GPU assembly, singular/near corrections, CPU/GPU solve, field evaluation, scoring, and total wall. Explicit warm vs cold.

**Important high-frequency source-model limit:** A 20 kHz ideal uniform-velocity throat boundary does not establish realistic compression-driver phase-plug radiation at 20 kHz. Preserve the distinction between ideal-source BEM correctness and complete driver/system predictiveness.

---

## 4. Staged review/implementation packages (approval gates)

The senior reviewer may re-order packages based on local benchmark evidence. Every package below is **opt-in and individually gateable**. **No phase is approved simply because this file exists.**

### P0: READ-ONLY diagnostic baseline and data safety audit (REQUIRED FIRST)

**Goal:** Determine actual current bottlenecks without solver changes or new GPU runs initially.

**Read first:** `AGENTS.md`, `CLAUDE.md`, `docs/CONTINUITY.md`, `docs/ISSUES.md`, `docs/plan/01_CONTRACTS.md`, `TOOLCHAIN.md`, `docs/FORKS.md`, `docs/GUI_VERIFY_VIEW_PLAN_2026-11-12.md`, `docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md`, performance evidence above.

**Inspect:** `hornlab_search/solve/beat.py`, `hornlab_search/search/evaluate.py`, `hornlab_search/config.py`, `hornlab_search/mesh/sizing.py`, `hornlab_search/mesh/build.py`, `hornlab_search/solve/cache.py`, `hornlab_search/types.py`, `pyproject.toml`, fork `BeatEngineDriver.jl`, `BeatEngineCudaBurtonMiller.jl`, `BeatEngineDenseSolve.jl`.

**Tasks:**

- Confirm current local checkout/pin, available worker paths, baseline config flags, effective `cuda_fused`, CPU/Metal provision status, active jobs and locks. **Do not stop or disturb active queues.**
- Inventory real winner/reference meshes and classify small OSSE, large/expensive rectangular/ATH shape, optional multi-source and free-standing/finite enclosure. Report meshes already available, so no unnecessary new solves.
- Extract existing per-stage timing data and failures from immutable runs/logs. Compare **actual solver seconds** vs **complete candidate wall time** including geometry, meshing, orchestration and metric calculations.
- Identify any `20 kHz exceeds RAM` claim's inputs: actual area/DOFs, full vs quarter symmetry, number and dtype of matrices, LU workspace, Windows shared RAM, batch width, cache residency and peak allocated vs resident bytes.
- Audit solve identity/cache: all numerical changes must alter provenance/key correctly; *no existing response silently reused under changed quadrature/formulation/mesh.* Inspect compatibility with dataset and score replay.
- Inventory existing tests, identify missing reference fixtures, draw an error-budget ledger.
- Produce **GO/NO-GO matrix** for P1–P5, ranked by expected impact/effort/risk.

**Exit deliverable:** Read-only findings memo with exact paths, current SHAs, line ranges, tabulated measured data, blockers, and a short owner decision list. **No new solves or code edits unless separately approved.**

### P1: Same-physics, same-mesh benchmark harness

**Purpose:** Prevent performance conclusions from changing the problem. A benchmark harness should run only after reviewer approves the controlled GPU/CPU time budget and confirms no competing owner workload.

**Candidates:** 1 representative compact OSSE quarter-mesh; 1 larger/harder quarter-mesh; optionally 1 free-standing or multi-source case. Include 500 Hz, 2 kHz, 8 kHz, 16 kHz, and 20 kHz where mesh is physically adequate/within resource limits; use exact matched grids for actual A/B.

**Files to examine for reuse:** `tools/bench/throughput_matrix.py`, `tools/bench/cuda_cpu_40designs.py`, `tools/bench/full_range_cuda_cpu.py`, `tools/measure_fused_ceiling.py`, `tests/test_solve_crosscheck.py`, `tests/test_solve_beat_fused_cuda.py`.

**Measurements:** mesh/cache hit, DOFs, max/min mesh edge and curvature, full/incremental wall, each solver stage, peak **dedicated GPU + Windows shared GPU + host RAM**, GPU transfer bytes/time, CPU/GPU utilization, host startup, failure/fallback reason, H/V/diagonal cuts, impedance, numerical error, condition/residual when available.

**Acceptance:** Validated common test case, reproducible artifacts, no accidental cached or background-work advantage, report across multiple warmed repetitions plus cold startup. Baseline must be retained forever, not overwritten.

### P2: Fast-path configuration and adaptive discretization, before new algorithms

**A. Confirm fused CUDA whenever eligible.** Inspect effective backend in every queued or reported solve; don't blindly make it default for unsupported features. Compare fused to conventional only on identical physical problems.

**B. Test `mesh.band_split`.** Example **research** edges 5/10/16 kHz for a 1–20 kHz evaluation, *not production defaults*. Capture band meshes, accuracy at seams, full-sweep runtime, memory, and complete high-frequency polars. Note: adaptive band meshes reduce average work, **not** peak memory on the highest band.

**C. Test `rear_res_factor`, `curvature_npts` and possible throat over-refinement.** At 20 kHz the current formula forces throat twice as fine as mouth. Test whether this is warranted for real shapes, small fillets and phase-sensitive features. Do not coarsen based solely on visual smoothness.

**D. Test CUDA regular integration quadrature.** The pinned BEAT fork documents a CPU wavelength-based 1/2/4 selector; CUDA currently uses fixed order. Investigate exposing a hashed `solve.quadrature_order`, fixed 4 vs fixed 2 A/B, and only then frequency/kh-adaptive integration. Keep singular/near corrections. This targets assembly cost, **not dense matrix storage**.

**Read:** `docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md`, `hornlab_search/search/evaluate.py::_compute_band_split/_seam_check`, fork `docs/beat-engine-CUDA.md`, `BeatEngineCudaRegular.jl`, `BeatEngineDriver.jl`.

**Gate:** Acoustic parity to independent reference at top end and near nulls; no unexpected seam jumps, stale cache collisions, incorrect symmetry, broken invalid-geometry checks, or degraded worst-case performance. Proposed provisional targets, **to be approved by senior:** on-axis and ordinary off-axis SPL within ~0.05 dB through midband, ~0.1 dB high band; beamwidth within ~0.5°, DI within ~0.05 dB, and impedance magnitude/phase comparably bounded. Near nulls, use complex pressure normalized errors rather than raw maximum dB differences. Mesh-convergence errors may be larger; make thresholds physically justified, not cosmetically passable.

### P3: Iterative solver experiment (CPU and CUDA; NO DEFAULT CHANGE)

**Why:** On larger systems dense LU is expensive and requires additional workspace. A stable Krylov solver could avoid LU and permit larger meshes; it still stores O(N²) if given a dense matrix.

**Known reference code:**

- Native Metal source: https://github.com/m3gnus/hornlab-metal-bem/blob/main/hornlab_metal_bem/metal/native_helper/Sources/HornlabMetalBemNative/GmresSolve.swift
- Documentation: https://github.com/m3gnus/hornlab-metal-bem/blob/main/docs/architecture.md
- Owner's BEAT fork: `hornlab_beat_bem/julia/src/BeatEngineDenseSolve.jl` (diagonal preconditioner; CPU/Metal GMRES currently; fused CUDA direct LU).

**Important caution:** HornLab Metal's documented **20–35 iterations** comes from its tested `standard`/complex-k operator configurations with block-Jacobi; owner fork's BM may require more. Do not transpose its iteration count, residual thresholds or shifted-k assumptions to real-k Burton–Miller without head-to-head proof. A shifted complex wavenumber may change the physical operator/solution if misused.

**Prototype A:** CPU/Metal reference on same dense system, compare block-Jacobi vs diagonal, factor construction, convergence, residual, backward error, reorthogonalization. Keep LU as truth reference. 

**Prototype B:** CUDA-resident dense GMRES, ideally reuse the same assembled fused BM matrix, with correctly conditioned preconditioner and stable high-precision Krylov accumulations. Avoid `float32`-only Arnoldi orthogonality failure documented in existing research.

**Prototype C (only if A/B warrant):** Assess CPU solve on pinned host memory with GPU assembly and data transfer. Apple unified memory makes this natural on Metal; 4060 PCIe transfers can swamp gains. Compare GPU-resident against GPU→CPU routes in end-to-end time.

**Stop criteria:** unstable/unbounded iteration growth, inaccessible precision floor, interior-resonance artifacts, fallback frequency > approved threshold, host VRAM/RAM pressure, loss of impedance/phase accuracy, or higher wall time than LU for intended mesh regime. Always expose iterations, residual, and fallback in run metadata.

**Never silently accept:** partial convergence, degraded relative residual, lower integration precision, or the first successful solver result without verifying fields/polars.

### P4: Bounded frequency pipelining and native performance

**Goal:** Overlap *real* work, not merely launch multiple GPU solves and spill memory.

- Reuse immutable geometry/quadrature/near-pair caches across frequencies.
- For NVIDIA: investigate *double-buffered GPU assembly + device iterative solve* with conservative peak-memory bounds; evaluate alternative GPU assembly + CPU solve only if transfer and PCIe profiling justify it.
- For Apple Silicon: compare BEAT `beat_metal` with standalone `hornlab-metal-bem` **on the same mesh and physics**, and assess native Metal's documented double-buffered assembly/CPU Accelerate overlap. This separate public package is not automatically wired into Hornfab's optimizer.
- Explicitly consider BEAT's historical CUDA multi-frequency batching cliff (5,140 DOF: 689 s single batched call vs ~33 s when frequencies called separately in old test). Never re-enable naive batching to mimic Huygens.
- Have a bounded scratch-buffer/memory budget, stream results to persistent outputs incrementally, handle cancel/kill/restart deterministically, and avoid double-counting processing.
- If timing says GPU assembly and CPU solve can't overlap effectively, retain single-frequency flow. Under memory pressure, throughput will be worse despite more parallelism.

**Gate:** At least a convincing repeatable end-to-end improvement at *fixed response error* with no worker leaks, no shared-memory spill, no cache changes, and graceful cancellation. Set gain target after measured P1 baseline (candidate threshold ~1.3× sustained, not a promise).

### P5: Research-only higher-ceiling methods (separate proposal, separate approval)

- **True matrix-free / fast-multipole BEM:** eliminate full dense matrix, not merely dense LU factorization. Review Bempp-cl FMM, NumCalc, FMM3D/HFMM3D, preconditioners and how BM's hypersingular/adjoint operators would be evaluated. Consider high-frequency `kD` and near-field correction. CPU prototype first; GPU production is a different project.
- **Specialized infinite-baffle waveguide formulation:** exploit half-space Green function where the **physical mounting is an infinite rigid baffle**. Not a valid replacement for free-standing/finite-baffle cases; compare fields and impedance, not just beamwidth.
- **Axisymmetric/multimodal methods:** drastic savings for rotationally symmetric or separable modal designs; inappropriate as drop-in for rectangular H/V, ATH ridged, asymmetrical or multiple-entry geometries unless separately validated.
- **Adaptive high-order BEM (BEMAO):** select element order based on error and frequency; research paper shows numerical advantages. It requires discretization/solver changes. Possible follow-on once P2/P3 evidence is in.

**Gate:** Separate technical design and legal/license review, full provenance schema, independent numerical oracle, owner approval and experimental feature flags. No speculative speedup commitments.

---

## 5. Approval thresholds, metrics, and validation corpus

The senior agent must set final numerical gates using actual production error budgets. Suggested measurement protocol:

- **Three fixtures minimum:** (i) compact symmetric OSSE with flat mouth, (ii) larger ATH/ridged rectangular/freeform quarter geometry, (iii) free-standing or finite-enclosure geometry; add multi-entry case if needed. Include intentionally bad/sliver/close-gap geometry for regression, not only clean winners.
- **Same mesh** first for solver/integration comparisons; **mesh-convergence ladder** separately for adaptive mesh claims. Include source/cap symmetry and coordinate frame checks. Compute per-frequency `k*h` distribution and outliers, not simply global mm resolution.
- **Physically sensitive outputs:** complex polar pressure on axis and off axis, H/V/diagonal cuts, full-sphere DI if requested, lobing/null flags, throat impedance, source-to-source impedance for MEH, seam continuity, reflection/near-field conditions.
- **Not just median error:** max error outside deep nulls, median/p95 error, complex pressure near nulls, peak-to-peak polar ripple, loading and modal anomalies, converged verified scores. Explicit frequency and angular region where errors occur.
- **Multiple repeats:** stable warm median/p95, startup separately, GPU dedicated/shared/host memory, max/avg DOFs, total candidate wall, candidates/hour, failures, cache hits. Record thermal and desktop-load conditions and physical laptop power mode.
- **Hold-outs:** 10–20 kHz and one non-baseline horn family must be included before claiming general improvement. Do not calibrate solely to the ATH OSSE demo.
- **Regression:** previous `analytic` and `crosscheck` tests plus tests that stress new data/provenance fields. Observe `docs/FORKS.md` checkpoint tolerances; do not weaken them.

**Definition of speed gain:** `baseline complete-candidate wall / new complete-candidate wall` at fixed requested output fidelity. Report `solver-only`, `mesh + solver`, `end-to-end optimizer`, and `CPU/Metal/CUDA hardware` separately. **New hardware or reduced physics fidelity cannot be credited as algorithmic speedup.**

### Immediate decision gates

| Gate | GO if | NO-GO if |
|---|---|---|
| P0 | Reproducible explanation of current slow paths and memory; caches/jobs protected | Cannot establish effective solver path or physical problem identity |
| P1 | Matched benchmarks, no spill/contamination, useful coverage of actual geometries | Timings are from different meshes/frequencies or cache histories |
| P2 | Faster at matched converged acoustic fidelity and bounded worst-case behavior | Only faster because mesh underresolves 20 kHz or physical geometry changed |
| P3 | Stable residual/field agreement, benchmark improvement or meaningful memory headroom | Iteration blowups, silent fallback, incorrect BM/shifted-k physics |
| P4 | Bounded overlap actually reduces end-to-end wall, handles cancellation | Shared-memory paging, worker leakage, high peaks or scheduling conflicts |
| P5 | Separate approved design and proven need beyond P2–P4 | An unvalidated wholesale solver rewrite is proposed |

---

## 6. Data integrity, cache identity, reproducibility, rollback

**Must preserve:** raw acoustic arrays, observation grids, frequency lists, mesh hashes, source/boundary identity, solver library SHAs, precision, formulation, quadrature settings, actual residual/iteration counts, physical units, backend and fidelity. Physical solves must remain reusable under different **scoring** versions when inputs match; changing physical solver behavior must not silently reuse old solves.

Required engineering controls:

1. Every opt-in numerical method gets a **distinct immutable solve identity** (new physics/formulation/mesh/precision/quadrature/preconditioner where output can differ), and the exact package Git SHA; unit-test cache invalidation AND legitimate reuse.
2. Historical physical simulations are immutable; add side-by-side results rather than mutating `response.npz` or old run folders.
3. Append-only metadata for new benchmark runs, including `backend`, `method`, `formulation`, `precision`, `mesh_policy`, `effective_epw`, `quadrature_order`, `symmetry`, `source_model`, `mounting`, `iterations`, `residual`, `fallback`, `peak dedicated/shared GPU memory`, if implemented and available. These are **proposed semantic fields**, not a claim they currently all exist.
4. Never edit `.venv/Lib/site-packages` or `.julia` in place. Fork changes follow `docs/FORKS.md`, commit/pin by immutable SHA, test and offer rollback to previous pin.
5. Do not corrupt CPU/GPU parallel lanes. The one GPU must be locked; read-only reviewers cannot call `gpu-clean`, terminate worker hosts, POST to job endpoints or launch test solves while a job is running.
6. Follow repo's **2026-11-12 consolidated-checkout amendment** in `AGENTS.md`: work in the canonical local checkout; no unsolicited worktrees, branch juggling, or independent git mutations by worker agents. Parent integrator owns git operations; file edits are coordinated.
7. On an approved pushed commit, update `docs/CONTINUITY.md` and `docs/ISSUES.md`, plus `docs/INDEX.md` / `docs/CODE_MAP.md` for new documents/modules; do not modify frozen contracts casually.

### Rollback

- Remove experimental solve flag or switch backend to last proven path.
- Restore prior solver fork pin SHA and old config defaults.
- Confirm historic runs still render; old solve-cache hits and score replay still work.
- Preserve all experimental evidence even after rollback, labeled as experimental and failed if applicable.
- Compare post-rollback physical fields to prechange baseline before re-enabling production optimization.

---

## 7. UI / UX proposal (no premature redesign)

**Principle:** This should primarily be an *engine efficiency upgrade*. The designer should still work in the same **Compose / Launch → Search → Verify → Compare / Elites → export** flow. Users shouldn't have to know GMRES, Burton–Miller, quadrature order or CUDA kernel details to design a horn.

### Level 1: No visible changes while P0–P2 are experimental

- Only backend diagnostics and versioned result metadata change. Keep Compose, Launch, Run Detail, Verification and Elites familiar.
- No new navigation item or giant solver-tuning form; no silently switching solver based on unmeasured heuristics.
- A background acceleration flag can be set in advanced YAML by expert users and shown clearly on the run detail if present.

### Level 2: Once P2/P3 pass, expose a small understandable fidelity choice

Use existing config/brief pattern and jobs system. **Proposed labels, not current UI controls:**

| UI choice | Meaning to user | Suggested internal behavior after acceptance |
|---|---|---|
| **Fast search** | Explore many shapes quickly | Existing screen grid; optional band split and fastest *validated* backend |
| **Detailed verification** | Carefully check leading designs across band | Higher density frequency/polar grids, measured mesh-convergence policy and stable solve route |
| **Full-range check (up to 20 kHz)** | Validate high-frequency coverage and irregularities | Estimated DOFs/RAM, adaptive band meshes, eligible acceleration, validated fallback |

- Display **estimated high-band resource fit** from premesh data, not a universal “20 kHz unsupported.” Show *estimated* vs *measured*, hardware device and model type.
- Display **physically relevant fidelity:** last solved frequency, mesh resolution, verification tier, symmetry, baffle/mounting, ideal-source vs driver-informed label, and any accuracy warnings.
- If optimized solver fails, show: “Fast method unavailable / did not converge; verified fallback used” or “Result incomplete,” never an unqualified green pass.
- Preserve current `screen` / `verify` / `final` and objective-version labels. An accelerated **screen** should never masquerade as a **verified** horn.
- On Run Detail/Verify, continue showing the same SPL, H/V polars, directivity, impedance, full balloon and side-by-side comparisons. The rendering semantics must not change with solver backend.
- Place deep numeric details in a collapsible expert-only **Simulation details** panel. Proposed contents: method, source, mesh and DOF by band, effective frequency grid, time by stage, peak VRAM/RAM, convergence status, implementation SHA, fallback and crosscheck result.
- Use existing backend JSON API and `gui/jobs.py` allow-listed subprocess runner. No in-process solve in `gui/server.py`; no new JS build/dependency unless separately justified.

**UI safety gates:** Honor `docs/GUI_VERIFY_VIEW_PLAN_2026-11-12.md`: only measured values (missing `–`/unknown), screen and verify explicitly distinguished, accessible status words not merely colors, no duplicated stale run listings or log flooding. Tests should cover disabled actions during live GPU lock and reliable missing metadata for old runs.

### Normal design workflow after successful implementation

1. User chooses horn typology, coverage and bandwidth, maximum size, throat/source and mounting.
2. UI tells them the design is **feasible to simulate** on this machine, or that a high-band run exceeds measured memory (with reason).
3. Optimize normally. Software may reuse precomputed geometry and use fewer unnecessary surface elements at low frequencies; a validated iterative solver may replace an expensive direct factorization on larger problems.
4. Browse the same design rankings and polar/directivity charts.
5. Verify promising designs to higher frequencies and tighter mesh/response convergence. High-frequency results are explicitly labeled as **ideal source** unless driver behavior is modeled.
6. Export geometry / design package using existing workflow; numerical provenance remains accessible.

**No automatic improvement in physical sound quality just because the solver is faster.** The expected value is more trustworthy acoustic evidence, faster iteration and more exploration within the same compute budget.

---

## 8. Risk register for senior approval

| Risk | Severity | Why it matters | Containment |
|---|---|---|---|
| Reduced quadrature or mesh silently shifts directivity | High | Looks like better horn while merely less resolved | Same-mesh integration A/B plus independent finer-mesh validation |
| Incorrect singular/near-field handling near flutes/ridges/septa | High | ATH/crosshair shapes can contain tight curvature/adjacent walls | Pathological geometry fixtures; near-pair coverage and complex field errors |
| BM vs classical/shifted-k formulation mismatch | High | Can create convincing but false resonant/loading features | Physical-equivalence gate, exact sphere/independent solver, modal/irregular-frequency tests |
| GMRES false convergence or unstable iteration counts | High | Missed polar anomalies, impedance corruption | True residual, backward error, preconditioner diagnostics, clear fallback |
| Windows CUDA shared-memory spill | High | Appears to fit but becomes 10x slower or crashes worker | Track both dedicated and shared memory; fail fast; bounded concurrency |
| Apples-to-oranges Huygens performance comparison | Medium | Unrealistic timelines and inappropriate architecture | Matched mesh and physical formulation, end-to-end benchmarks |
| High-frequency ideal driver boundary misleading | High | Good computed pattern may not be real compression driver | Ideal-source provenance; separate phase-plug/driver validation |
| Cache contamination | Critical | Historical datasets become irreproducible or new results wrong | Immutable identities, pinned SHAs, cache parity tests, isolated run paths |
| Interrupting active optimization/night queues | High | Lost work / corrupted GPU state | P0 review-only, scheduler approval, GPU lock and owner coordination |
| Additional UI controls confuse nontechnical users | Medium | Feature progress makes product harder to operate | Minimal existing-flow integration, expert-only disclosure, accessibility tests |
| Mac backend incorrectly assumed installed/compatible | Medium | Benchmarks impossible or incomparable | Provision status check; true chip/RAM/OS recorded; separate native Metal pilot |
| Scope expands into solver rewrite | High | Large engineering cost without validated gain | P0–P4 before P5, owner approval at every phase |

---

## 9. Honest outcome expectations

### Likely (if validated)
- Substantial time savings from **removing unnecessary work** in full-band sweeps, especially because the lowest frequencies do not need the 20 kHz mesh.
- Faster CUDA matrix assembly if lower/order-adaptive quadrature proves accurate.
- Some memory headroom by eliminating LU workspaces with an iterative route, if convergence is stable; this does **not** eliminate dense-matrix O(N²) memory.
- Better utilization of the existing RTX 4060 and Apple Silicon collaborator machine without buying a new GPU.
- Same physical acoustic output and user-facing charts, produced more efficiently.

### Possible but uncertain
- Single-digit-second **full-band** solving for small, eligible symmetric waveguides, especially on Apple Silicon. This is a research target inferred from Huygens/HornLab benchmarks, **not a Hornfab performance prediction**.
- Moderate-to-large (>2×) speedups for some end-to-end screens when band splitting, quadrature and scheduling are combined, provided errors remain within the acceptance envelope.
- 20 kHz verify coverage on larger horns if geometry/mesh reduction and/or new solver permit it. Not guaranteed on 8 GB.

### Not justified now
- “Every horn will solve to 20 kHz in 1.2 seconds.”
- “The RTX 4060 is too weak for high-frequency BEM.”
- “Switching from LU to GMRES makes memory linear.”
- “Apple unified memory gives the same architecture on a Windows discrete GPU.”
- “Faster simulations necessarily design better-sounding horns.”
- “Huygens is open-source and we can directly port its kernels.” No public Huygens source was confirmed.

---

## 10. Senior agent review response template

Respond in this exact structure:

```markdown
# Senior review decision: Hornfab Huygens performance initiative
Date / local HEAD / pinned solver SHA / active queue status:

## 1. Overall verdict
GO / GO WITH CONDITIONS / NO-GO (review-only or implementation), and why.

## 2. Corrections to this handoff
Table: statement | evidence in current code | accurate correction | severity.

## 3. Phase decisions
P0: GO/NO-GO; P1...P5, dependencies, owners, and why.

## 4. First permitted actions (read-only unless approved)
Exact files, fixtures, measurements, stop conditions.

## 5. Numerical validation plan
Cases, baseline backend, same physical assumptions, mesh/near-singular/precision/field/impedance error gates.

## 6. Memory and performance budget
Measured DOF limits, dedicated/shared RAM headroom, CPU/Mac paths, full-candidate timing definition, fallback.

## 7. Data and GUI change control
Cache/version keys, rollback, UI scope, preservation of old records, compatibility with current GUI.

## 8. Unresolved owner decisions
Only decisions that materially change allowed implementation scope.

## 9. Proposed first PR/commit scope
Smallest approved experiment, specific changed files, tests and criteria; no unfunded solver rewrites.
```

---

## 11. Source/reference map and confidence

**Primary Huygens author report:** https://demaudio.com/blog/bem-on-the-gpu/ (claimed performance, validated waveguide sphere, methods; *author-reported*).  
**Public HornLab Metal source:** https://github.com/m3gnus/hornlab-metal-bem (independent/public implementation reference; inspect `docs/architecture.md` and `metal/native_helper/Sources/HornlabMetalBemNative/GmresSolve.swift`).  
**BEAT fork:** https://github.com/llevaachingada/hornlab-beat-bem (owner pinned implementation; CUDA fused BM, CPU/Metal GMRES).  
**Hornfab:** https://github.com/llevaachingada/Hornfab (`docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md`; `docs/evidence/FUSED_CUDA_2026-10-24.md`; `docs/evidence/BENCH_AUDIT_2026-11-03.md`; `docs/evidence/BENCH_FULLRANGE_THREADS_2026-11-03.md`; GUI and contracts).  
**Siemens adaptive high-order:** https://pub.dega-akustik.de/DAGA_2023/data/articles/000555.pdf and https://past.isma-isaac.be/downloads/isma2022/proceedings/Contribution_313_proceeding_3.pdf (published benchmarks; not a plug-in).  
**Bempp reference:** https://bempp.com/handbook/core/assembling_operators.html (alternative solver/operator methods; no benchmark here on user's hardware).  
**AKABAK:** https://randteam.de/AKABAK3/AKABAK-Introduction.html (comparison reference; Huygens article cautions on conventions and demo-limit timing).

**Evidence classes:** “Measured” refers only to historical committed Hornfab evidence or external author-reported numbers explicitly labeled as such; “verified source state” to code inspected on the named GitHub commit; “proposed” to candidate architecture/UI/tests; “inferred” to expert interpretation. **No fresh controlled 20 kHz or Huygens head-to-head run was performed as part of this handoff.**

---

**Review request to senior agent:** Make this an efficient engineering effort with a small first proof, not a new scoring/versioning program. Preserve data, protect active jobs, explain every physical-model shortcut, and show the owner actual matched performance evidence before recommending any permanent solver or UI change.
