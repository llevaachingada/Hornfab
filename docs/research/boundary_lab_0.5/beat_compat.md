<!-- Research appendix, 2026-10-21. Produced by a research subagent under senior-review orchestration, read-only against Boundary Lab v0.5.0 (6c9185b), BEAT_Engine v0.6.0 (1bb46da), hornlab-beat-bem 38544d2. Key claims spot-checked by the orchestrator (see docs/BOUNDARY_LAB_0.5_RESEARCH.md section 0). Paths like BL/..., BE/..., HB/..., HM/... refer to those repos; local clone paths have been removed. -->

# BEAT / Boundary Lab compatibility research for hornlab-search

Date: 2026-10-21. READ-ONLY research. Nothing from the clones was executed or installed.
Labels: [verified] = read in source/docs at the cited place; [inferred] = my reasoning from verified facts;
[unverified] = could not be checked here (needs a run, hardware, or a legal opinion).

Path abbreviations (all under ``):

| Abbrev | Tree | Revision checked |
|---|---|---|
| HB | `hornlab-beat-bem/` (m3gnus/hornlab-beat-bem) | `38544d214ba2e8a4977bb82170d2fb4a3f9fa8b0` (2026-10-07), checked out [verified] |
| BE | `BEAT_Engine/` (JWSound/BEAT_Engine) | tag `v0.6.0` = `1bb46da833a2a2d330d9b7d915a7ee5c31934812` (2026-10-20), = HEAD of main [verified `git rev-parse`]; partial clone (`--filter=blob:none`), full commit history present |
| BL | `boundary-lab/` (JWSound/boundary-lab) | tag `v0.5.0` = `6c9185b` [verified `git describe`] |
| HM | `hornlab_mesher/` | installed hornlab-waveguide-mesher 0.2.4 (AGPL-3.0-or-later) |
| HS | `` | our repo |

---

## A. Which BEAT does hornlab-beat-bem 38544d2 contain, and what is the gap to BEAT 0.6.0

### A.1 Identity of the pinned engine

* hornlab-beat-bem is Python package version `0.2.0`, license field `GPL-3.0-or-later`, only runtime dependency `numpy` (HB `pyproject.toml:7,10,14-16`) [verified]. It does **not** depend on the `beat-engine` wheel, and no "BEAT x.y.z" string exists anywhere in HB (grepped README/VENDORING/AGENTS/docs) [verified]. Engine identity is a content fingerprint over `*.py`, `julia/**.jl`, Project/Manifest tomls (HB `hornlab_beat_bem/runtime.py:46-57`) [verified].
* The Julia engine is a **vendored, locally modified copy** of the BEAT solver as it was inside Boundary Lab before extraction (HB `VENDORING.md:1-27`) [verified]. Sync points (HB `VENDORING.md:28-41`) [verified]:
  * original vendoring 2026-08-19 from boundary-lab `42c8781` (2026-08-17);
  * latest wholesale sync 2026-10-01: m3gnus/boundary-lab fork branch commit `3ea846eed48e25b88aa339d0188b9a69699a4815` (a Metal-focused branch);
  * then direct ports of official BEAT PRs: #17 `3d3e0a4`, #19 `85bac13`, #20 `4aa32e7` (CPU SIMD + precompile), #23 `3157fe0` (GMRES sweep reuse, 2026-10-01), and "fixed CPU regular-quadrature default" `ea86e0e`/`668daa4` (2026-10-07) (HB `VENDORING.md:413-466,468-510,511-538`) [verified]. All those official commits exist in BE history [verified `git cat-file`].
  * HornLab-local differences that stock BEAT does not have (HB `VENDORING.md:578-700`): `source_motion` (`normal`/`axial`), the exposed rigid half space guard, per-package request/output decisions, `deploy_solver.jl` and the `boundary_lab_deploy_*` dispatch **removed** (HB `VENDORING.md:600-640,772-776`) [verified].
* Position on the BEAT version line: BEAT 0.1.0 was cut 2026-09-08 from boundary-lab dev `01988025` (BE `docs/EXTRACTION.md:3-5`) [verified]; releases 0.1.2 (09-1x) ... 0.3.0 (2026-09-28), 0.4.0 (2026-10-07), 0.5.0 (10-09), 0.5.1 (10-13), 0.6.0 (10-20) [verified `git tag --format`]. HB's engine is **not a point on that line**: it is newer than 0.3.0 in some respects (CPU SIMD #17/#19, GMRES reuse #23, fixed quadrature) and older than 0.1.2 in others (no `BeatEnginePhasor.jl`: HB `VENDORING.md` says "The official engine's selectable phasor API is absent from this lineage"; no compiled-system driver; no `BeatEngineContract.jl`) [verified file diff: 17 source files exist only in BE: Contract, CpuRefinement, CudaBmFinalize, CudaCoupledBurtonMiller, CudaRhsPacked, InterfaceRadiation, InterfaceVelocity, MeshData, MetalCoupledBurtonMiller, MetalCoupledHost, MetalLoad, Mumps, Phasor, Provenance, SweepOverlap, Thermoviscous, WorkerCleanup]. Practical label: "BEAT main of roughly 2026-10-01..07, minus the compiled-contract work, plus HornLab patches" [inferred].
* File-level comparison of `julia/src/*.jl` (HB) vs `julia_local/src/*.jl` (BE v0.6.0), by `cmp`/`diff` [verified]:
  * byte-identical: `BeatEngineCpuSimd.jl`, `CudaCommon`, `CudaOperators`, `CudaRegularKernels`, `CudaSingular`, `MetalGatherKernels`, `MetalPackedPairs`, `MetalPairKernels`, `MetalRegular`, Rocm pair/regular/singular files. So CUDA regular+singular quadrature kernels and CPU SIMD kernels are the same code.
  * small diffs: `CpuBurtonMiller` (49 lines: `outgoing_wavenumber(k)`, `burton_miller_coupling(k)`, opt-in Float32 LU refinement), `CpuAssembly` (32), `CpuSolve` (6, coupling only), `CudaRegular` (9, RHS column index), `DenseSolve` (92: long comment on OpenBLAS vs Accelerate + refinement diagnostics only).
  * large diffs: `CudaBurtonMiller` (341: columns/cached-RHS-operator assembler), Coupled*, `MetalSingular`, `MetalFieldFast`, `SpeakerRom`, `Core`.

### A.2 How hornlab-beat-bem calls BEAT

* Python spawns `julia --project=<dir> --startup-file=no <pkg>/julia/solver.jl` (HB `worker.py:130-146`; project dirs `julia`, `julia_cuda`, `julia_rocm`, `julia_metal`, `runtime.py:18-21`) [verified]. Protocol is JSON lines on stdin/stdout: command `{"request": "<path>", "operation": "solve"}` (HB `worker.py:213`), Julia `worker_loop` emits `ready` with `protocol="boundary_lab_julia_worker"` and reads `message["request"]` (HB `julia/BeatEngineDriver.jl` `worker_loop`) [verified].
* Optional persistent host: a detached `python -m hornlab_beat_bem.worker_host` owns the Julia child and serves clients over a socket, so the Julia runtime outlives the Python process (HB `worker_host.py:1-40`, `worker_client.py:1-40`) [verified]. This is the "persistent Julia host" in our CLAUDE.md hygiene rules. Idle timeout and registry are HB inventions, not BEAT features [verified].
* Public API: `solve_frequencies(...)`, `solve(mesh_path, config)`, `warm_up`, `SolveConfig`, `ObservationConfig`, `GroundPlane`, `detach_workers`, `shutdown_workers` (HB `__init__.py:1-103`, `sweep.py:234-556`, `config.py:319-563`) [verified]. Request payload is the **legacy "source request"**: `{"schema_version": 2, "config": {mesh_file, scale_factor, meshes[{translation_m}], distance, step_size, min_angle, max_angle, tag_throat, symmetry, source_motion, quadrature_order, singular_order, regular_quadrature_mode, solve_precision, surface_traces_enabled, spherical_grid{theta_count,phi_count,theta_max_deg}, diagonal_enabled, near_correction_*, ground_plane_min_clearance_m, ...}, "frequencies_hz": [...]}` (HB `sweep.py:139-205`) [verified]. Results are converted from BEAT's `q = i rho omega v` velocity convention to unit-normal-acceleration (`p_accel = p_vel/(-i omega)`) for WG compatibility (HB `config.py:319-330`) [verified].
* Native result features HornLab relies on: polar cuts (H/V/diagonal), spherical grid ("balloon"), surface traces (P1 pressure + DP0 Neumann per frequency), impedance from throat force (`read_gmsh22_info`, HB `mesh.py:10-55`) [verified].

### A.3 BEAT 0.6.0: what it is and how it is called

* `beat-engine` 0.6.0 is a Python distribution (stdlib only, `requires-python >=3.11`, BE `pyproject.toml:5-10`) whose public API is **only** `EngineWorker`, `WorkerPool`, `EnginePaths`, `engine_paths`, `backend_catalog/backend_info` (BE `README.md:34-58,124-136`, `src/beat_engine/paths.py`, `backends.py`) [verified]. There is **no `solve_frequencies` and no `SolveConfig`**. `engine_paths()` returns two Julia entry scripts: `system_solver = julia_local/coupled_solver.jl` (compiled-system worker, the supported contract) and `source_solver = julia_local/solver.jl` (legacy source-request worker) (BE `paths.py:16-21`) [verified].
* The supported request is the **compiled-system contract**: `{"schema_version":1,"compiled_system":{meshes,regions,boundaries,interfaces,components,excitation_ports},"frequencies_hz","excitation_port_ids","outputs","solver_options"}` (BE `src/beat_engine/beat_contract/example-exterior-request.json`, `docs/BEAT Compiled System Contract.md:1-60`) [verified]. Worker protocol v1 `beat-worker` with versioned `ready` handshake, capability negotiation (`phasor_conventions`, `exterior_source_profiles`, `optional_output_quantities`, `request_transports: [file, inline_json]`), cooperative cancellation by marker file, one job at a time (BE `docs/BEAT Worker Protocol.md`, `src/beat_engine/beat_contract/worker-v1.json`) [verified].
* The legacy source entry is **kept but explicitly not the public contract**: "The source-request Julia entrypoint is retained for existing reference and Deploy comparisons. It is not the physical-system public request contract." (BE `docs/EXTRACTION.md:17-19`) [verified]. Its protocol is unchanged (`ready` with `protocol="boundary_lab_julia_worker"`, BE `BeatEngineDriver.jl:1546`) [verified].
* **HornLab-only request keys absent from stock 0.6.0 `BeatEngineDriver.jl`** (grep count 0 vs HB > 0) [verified]: `source_motion`, `solve_precision`, `surface_traces_enabled`, `spherical_grid`, `diagonal_enabled`. Keys present in both: `tag_throat`, `translation_m`, `ground_plane_min_clearance_m`, `regular_quadrature_mode`, `quadrature_order`, `singular_order`, `spherical_sampling_enabled`, `scale_factor`, `near_correction_enabled`. Consequence: pointing `hornlab_beat_bem` at BE's `solver.jl` would silently ignore axial source motion (it would run a breathing cap) [inferred from the missing key; the BE source driver ignores unknown keys, consistent with VENDORING's remark "Upstream has no `source_motion` key at all, so it ignores the value"] (HB `VENDORING.md:98-116`).
* Equivalents in the compiled contract: axial piston -> component parameters `motion_profile:"rigid_translation"`, `motion_axis:[0,0,1]`, `compiled_system.contract_version: 2`, worker must advertise `exterior_source_profiles` containing it (BE `docs/BEAT Compiled System Contract.md`, "Exterior ideal-velocity-source motion") [verified]; precision -> `solver_options.precision` float32/float64 (BE `BeatEngineCompiledDriver.jl:1037-1040`); surface traces -> outputs `bem_boundary_pressure` / `bem_boundary_neumann` (`:63-65`); balloon/polar -> output `exterior_pressure` with `options.points_m` list (arbitrary points; polar/sphere sampling is client-side in Boundary Lab, `observation_planes.py`, `balloon.py`) [verified]; throat impedance -> output `radiation_impedance` / `radiation_impedance_matrix` (`:1442,1455`). Near-correction keys are **not** read by the compiled exterior driver (no `near_correction` in `BeatEngineCompiledDriver.jl`; only the legacy source driver has it) [verified by grep].

### A.4 Version gap: what changed (BEAT release notes, `BE docs/releases/*.md`)

| Release | Date | Relevant change [verified from the notes] |
|---|---|---|
| 0.1.0 | 2026-09-08 | Extraction; Python worker client; contracts; CUDA FEM symbolic reuse |
| 0.1.2 | 2026-09-1x | Phasor conventions `exp(+/-i omega t)`; **"Defaults exterior-only CUDA system solves to direct Burton-Miller assembly, sharing one pivoted LU factorization across excitation right-hand sides"** (`burton_miller_assembly=operator_matrices` restores old path) |
| 0.1.3 | 09-13 | Backend catalog API; Metal backend |
| 0.1.4 | 09-15 | Interruptible worker startup; rigid-ground radiator contract fix; opt-in CUDA memory cleanup |
| 0.2.0 | 09-21 | Multi-package coupled deploy; in-memory mesh transport; CUDA worker memory reuse |
| 0.3.0 | 09-28 | CPU coupled deploy / ROM |
| 0.4.0 | 10-07 | Contract v3 exterior electrodynamic transducers; radiation impedance matrix; rigid-translation sources; **CPU regular quadrature default -> fixed** (already in HB); CPU SIMD; CPU Float32 LU refinement opt-in; CUDA.jl 6.4.2 |
| 0.5.0 | 10-09 | Metal deploy; thermoviscous wall losses (FEM, opt-in); exterior field outputs evaluated together per excitation |
| 0.5.1 | 10-13 | Metal init hotfix |
| 0.6.0 | 10-20 | Projected FEM-BEM interface correction; Float64 host factorization for monolithic coupled CPU/Metal Float32; Metal field-output batching. "Worker protocol and result schemas are unchanged." |

Numerics-relevant differences for an **exterior BEM-only** solve, HB(38544d2) vs BE v0.6.0 [verified unless labelled]:

| Item | HB 38544d2 | BE 0.6.0 |
|---|---|---|
| Entry point used | source driver `BeatEngineDriver.jl` | compiled driver `BeatEngineCompiledDriver.jl` via `coupled_solver.jl` (public); source driver retained |
| Time convention | `exp(-i omega t)` only; BM coupling `Complex(0,1)/k` (`CpuSolve.jl:56,71,106`) | selectable; unlabelled requests = negative time (identical numbers); **Boundary Lab requests positive time** (`Phasor Convention.md:1-4`); coupling `burton_miller_coupling(k) = i*sign/abs(k)` (`BeatEnginePhasor.jl`). Positive time = complex conjugate of the negative-time solution; "does not change conditioning, SPL, or dissipated power" (`Phasor Convention.md` last para) |
| CUDA exterior assembly | four-operator path in the driver; direct assembler exists in the library but the source driver never calls it | compiled driver: `requested_assembly` defaults to `"direct_system"` (`BeatEngineCompiledDriver.jl:1047`); `direct_cuda_assembly = backend==:cuda && requested=="direct_system"` (`:1054`); `solve_exterior_direct_cuda` (`:850-895`) does `lu!(system.matrix)` in place on the device; one factorization for all excitations |
| CUDA multi-excitation RHS | n/a | cached RHS operator `B` (extra `8*p1*dp0` bytes) only when >= 2 excitations and it fits; 1 excitation keeps the matrix-free path (`docs/Exterior CUDA excitations.md`, "Choosing the path") |
| CPU exterior solve | adaptive LU/GMRES (cost model, GMRES tol 1e-5) | compiled CPU exterior forces LU: `solve_burton_miller_neumann_system_cpu_with_report(cpu_direct_system; method=:lu)` (`BeatEngineCompiledDriver.jl:1301`). The legacy source driver in 0.6.0 still has the adaptive path |
| GMRES defaults | tol 1e-5 (`BLAB_BEAT_GMRES_TOL`), env `BLAB_BEAT_DENSE_SOLVE=auto` | **identical code** (diff of `BeatEngineDenseSolve.jl` is comment + refinement diagnostics only) |
| Fused BM (CPU, Metal) | `fused_burton_miller = beat_backend in (:cpu,:metal) && near_selection===nothing && BLAB_BEAT_FUSED_BM!="0"` (`BeatEngineDriver.jl:1215`) | same condition in the 0.6.0 source driver (`BeatEngineDriver.jl:965-967`); in the compiled driver "direct_system" = fused for CPU/Metal and direct for CUDA |
| CUDA.jl | 6.2.0, CUDA_Runtime_jll 0.23.0 (`julia_cuda/Manifest.toml`) | 6.4.2, CUDA_Runtime_jll 0.25.0 (`[compat] CUDA = "6.4"`) |
| CUDA precompile bundle | `BeatEngineCudaBundle` for the source driver | `BeatEngineCudaBundle` exists, but the compiled worker only has CPU and Metal bundles: "Only the CPU and Metal compiled bundles exist so far; others take the fallback" (`coupled_solver.jl:24`), so CUDA compiled-worker cold start compiles from source [verified comment; actual cost unmeasured] |
| Precision | Float32 default; `solve_precision="double"` CPU only | `precision` float32/float64 (CUDA Float64 support unverified); opt-in CPU Float32 LU refinement `BLAB_BEAT_CPU_LU_REFINEMENT_STEPS` 0..3 |
| Symmetry modes | `off,x,xy,ground` (`Core.jl:439`) | same set (`Core.jl:448`) [verified both] |
| Quadrature | fixed order 4 default on all backends; `wavelength` CPU opt-in | same |
| Near correction | present (CPU only) | only in legacy source driver |

### A.5 "Projected FEM-BEM interface correction": does it touch exterior BEM-only solves?

**No** [verified]. The 0.6.0 release note describes interface flux for "FEM weak loading and BEM radiation" and rank checks on the "interface coefficient transfer" (BE `docs/releases/0.6.0.md`, `docs/Projected interface flux.md`). The implementing commit `b826b4c` (#69) touches only: `BeatEngineCoupled.jl`, a metadata-only hunk inside the coupled branch of `BeatEngineCompiledDriver.jl` (adds `interface_flux_discretization` etc. around lines 3383/3642), the coupled warm-up workload, docs, and coupled/interface tests (`git show b826b4c --stat`). `git diff v0.5.1 v0.6.0 --stat -- src` lists 19 files: coupled, Metal field batching (#70), `CoupledCondensed` backend-preservation (#68), precompile inventories; **none** of the exterior CPU/CUDA assembly or solve files (no `*BurtonMiller*`, `*Regular*`, `*Singular*`, `DenseSolve`). So 0.5.1 -> 0.6.0 does not change exterior CPU/CUDA numerics; the numeric gap to HB comes from 0.1.x-0.5.1 (table above) [verified]. The only 0.6.0 exterior-relevant change is Metal field-output batching (`BeatEngineMetalFieldFast.jl`, irrelevant on CUDA).

### A.6 Answers to the specific questions

* Burton-Miller formulation: same operator combination (`b = (-S - eta(D* + 1/2 I)) q`, eta = i/k, per `docs/Exterior CUDA excitations.md` and `beat-engine-CUDA.md`); only the sign convention became selectable [verified].
* CUDA fused/direct path: the claim in our `docs/HIGH_FREQUENCY_OPTIONS.md:12-15` is **correct for the pinned source driver** [verified: HB `BeatEngineDriver.jl:1215`, and `assemble_burton_miller_neumann_system_cuda` is defined in `BeatEngineCudaBurtonMiller.jl:350` but only referenced from tests]. In BEAT 0.6.0 the same assembler **is called** by the compiled exterior driver, **on by default for CUDA** (`:1047-1065`, `:1305-1313`) and has been since BEAT 0.1.2 (commit `b1a1dc1`, 2026-09-08) [verified from `git log -S` and release notes]. The legacy 0.6.0 source driver still excludes CUDA (`BeatEngineDriver.jl:965`). So the "unused lever" in HIGH_FREQUENCY_OPTIONS option 4 is already pulled by Boundary Lab's path; it is not a 0.6.0 change.
  * The CUDA "direct" path is not the CPU/Metal "fused pair kernel"; it scatters directly into one complex `N x N` system `A` and RHS `b`, never materializing S, D, D', H, then `lu!` in place (HB `docs/beat-engine-CUDA.md:91-123`, BE `BeatEngineCompiledDriver.jl:850-895`). Operator memory arithmetic: four complex Float32 operators = `4*8*N^2` bytes vs one `8*N^2` => ~4x less operator memory, plus no 3x real/imag/complex peak (HB `BeatEngineCudaBurtonMiller.jl` comment "removes the 3x dense-matrix peak") [verified from comments; the 6x figure in HB README is the Metal/CPU fused pair-kernel number, `README.md:588-612`]. At 8,941 dofs `8*N^2` = 0.64 GB [inferred arithmetic]. Whether this removes the 5.1k-dof sweep cliff on our RTX 4060 (TOOLCHAIN.md M2/M3: 689 s sweep vs 33 s per-frequency calls) is [unverified]; needs a measurement from a clean process.
  * BEAT's own CUDA qualification of the direct path: V100-32GB, T4-16GB (44,662 faces, 22,549 P1 dofs, 60 excitations; peak 12,170 MiB with the cached mapping; vs a Float64 CPU reference rel-L2 5.6e-5, 0.0015 dB) (BE `docs/Exterior CUDA excitations.md` "Qualification") [verified as reported by upstream; nothing on 8 GB consumer cards].
* GMRES: see table; identical router and tolerance; CUDA never uses GMRES (it factors on device) [verified router comment `DenseSolve.jl:1-60`: cost model "wrong on CUDA/ROCm, which factor on the device"].
* Symmetry / balloon / observation: see A.3 and the table.

---

## B. Mesh conventions: Boundary Lab vs hornlab_mesher vs our code

### B.1 What each side writes / expects

| Topic | hornlab_mesher | Boundary Lab / BEAT 0.6.0 | Our contract |
|---|---|---|---|
| File format | Gmsh MSH **2.2 ASCII**, triangles, `$PhysicalNames` written (HM `mesher.py:307`, meshio output `:566-575`) [verified] | read via `meshio` (BL `mesh_cache.read_mesh`, `mesh_data.read_resource_mesh` -> `surface_names()` from `field_data`) [verified]; compiled path can also take packed `mesh_data` (`beat_contract/mesh.py`) | `mesh/build.py:read_msh_summary` parses 2.x ASCII only (`build.py:70-125`) |
| Units | writes **metres** when `scale_to_metres=True` (default; `points*0.001`, HM `mesher.py:565-566`) [verified] | every mesh resource has `scale_to_m` (positive) and `translation_m` (BE contract: "scaled by `scale_to_m` then translated by `translation_m`"; BL `MeshResource.scale_to_m`, `generators/application.py:95,178`) [verified]. Ath generator docs default `GeneratorDocument.mesh_scale_factor = 0.001` (mm, `generators/base.py:95`); provider manifests default `mesh_scale_factor` 1.0 (`geometry-provider-api.md` manifest table; `generators/catalog.py:46`) [verified] | `SolveConfig(mesh_scale=1.0)`; HS `docs/plan/01_CONTRACTS.md:143-149`; bbox guard `BBOX_MIN_M=0.02 .. BBOX_MAX_M=5.0` in `build.py:46-47` (note: the CONTRACTS text says "0.1 to 1 m"; code uses 0.02-5.0) [verified] |
| Physical group names/tags | `PhysicalGroup`: 1 `SD1G0` rigid wall, **2 `SD1D1001` primary source**, 3 `SD2G0` enclosure wall, 4 `I1-2` interface, 8 `mid_chamber`, 9 `mid_port_interior`, 10/11 `mid_port_exit_left/right`, 12 `mouth_aperture` (HM `tags.py:6-28`) [verified]. `_validate_physical_tags` requires tags 1 and 2 present (HM `mesher.py:1079-1083`) | **Names are the ATH names.** BL treats `SD1D1001` as the driven diaphragm (`DRIVEN_DIAPHRAGM_PHYSICAL_NAME`, BL `ath.py:29`; `detect_ath_radiators` `ath.py:508-547`: DRV metadata, else the dome trio `SD1D1001/2/3`, else a single `SD1D1001` -> radiator "throat") [verified]. For the BEAT request, tags are **not fixed numbers**: the compiler resolves each Boundary's group (mesh_id, dimension 2, name and/or tag) to a Gmsh tag; "Every tagged physical surface used by a region must receive exactly one boundary role" (BL `docs/Physical System Model.md`, Boundaries section) [verified]. The legacy source driver instead used `tag_throat` (default 2, `config.py:84`, `beat_engine_backend.py:536`) | source tag 2 = `SD1D1001`, `velocity_sources={2:1.0}` (HS `TOOLCHAIN.md:191`); `build.py:SOURCE_TAG=2` |
| Source vs rigid | tag 2 = `PRIMARY_SOURCE`, tag 1 = `RIGID_WALL` (also `SOURCE_TAGS` set includes 10, 11) | `seed_exterior_system` (BL `project/migration.py:46-105`): every surface group becomes a `Boundary` named after the group; `BoundaryKind.MOVING` iff a `RadiatorConfig` matches (mesh, tag), else `RIGID`; moving groups are wrapped into `ideal_velocity_source` components with a `normal_velocity` excitation port, grouped by Ath DRV `drive_group` [verified] | n/a |
| Symmetry | `Mesh.Quadrants` `1234|12|14|1` -> reduced mesh; plane snap (HM `mesher.py:1027`); quarter `1` = +x,+y | project `symmetry` in `{off,x,xy}`; "X symmetry uses a positive-X half model; XY symmetry a positive-X/positive-Y quarter"; the active mesh must lie in that fundamental domain, tolerance `max(1e-9 m, 1e-6*extent)` (BL `docs/Model Assumptions.md:163-170`, `symmetry.py:14-60`); BEAT re-checks (`validate_symmetry_fundamental_domain!`, BE `BeatEngineCompiledDriver.jl:611,1078-1080`). Ath `Mesh.Quadrants=1 -> mirror axes (x,y)`, `14 -> (x)`, `1234 -> ()`, `12` -> **rejected** (Y-only unsupported) (BL `ath.py:98-125`) [verified] | contracts: quadrants `"1234"|"12"|"14"|"1"` with matching `symmetry_plane`; `12` is rejected by hornlab-beat-bem too (`config.py:609-624`) [verified] |
| Ground / baffle | optional `infinite_baffle` shell contract (`mesher.py:628`) | `symmetry="ground"` rigid-ground image mode exists in both engines (Core `normalized_symmetry_mode`); compiled path validates it (`compiled_ground_contract.jl`) | HB `GroundPlane` |
| Open edges | closed shell contract `_validate_closed_shell_contract`; reduced meshes are open on cut planes | exterior assembly checks closure "allowing edges on active symmetry planes" (BL `docs/advanced/cli-workflow.md`, Headless Project Workflow; `exterior_preparation.py:281`) | same expectation |

### B.2 Could a hornlab_mesher `.msh` be loaded directly as a Boundary Lab exterior mesh?

Yes in principle; mapping needed [verified evidence for each step, but **not tested end to end**; no Boundary Lab code was run]:

1. Format/units: MSH 2.2 ASCII triangles with `$PhysicalNames` are what BL's Ath path produces and what `meshio` reads; metres => set the resource `scale_to_m = 1.0` (not the 0.001 Ath default). Translation `[0,0,0]` unless you want placement.
2. Physical-group mapping: `SD1G0 -> BoundaryKind.RIGID`, `SD1D1001 -> BoundaryKind.MOVING` + `PhysicalComponent(kind=ideal_velocity_source)` + `ExcitationPort(kind=normal_velocity)`. Because the mesher reuses the Ath names, BL's `detect_ath_radiators`/`seed_exterior_system` would assign them automatically if the mesh were delivered as a generated (Ath-provider) artifact; for a plain imported `.msh` the roles must be set in the System editor or written into a `.blab.json` `physical_system` (schema in BL `src/blab/physical_model.py`, example `examples/Ath_SingleSourceWaveguide/*.blab.json`).
3. Extra groups: every tagged surface needs a role. Our horn meshes use tags 1 and 2 (`SOURCE_TAG=2`; the rest of tags 3/4/8-12 only appear for enclosures/interfaces/multi-chamber, which our families do not currently emit [inferred from `build.py` and HS grep; not exhaustively checked]). Tag 3 `SD2G0` would map to rigid; 12 `mouth_aperture` and 4 `I1-2` have no BL meaning [unverified].
4. Symmetry: write the BL project `symmetry` as `x`/`xy` to match mesher `Quadrants` `14`/`1`; this is the same single-source-of-truth problem as our "quadrants vs flag" killer. `12` unsupported on both.
5. Phase convention: Boundary Lab and BEAT-with-BL results are `exp(+i omega t)`; HornLab/hornlab-beat-bem results are `exp(-i omega t)` after the acceleration conversion (HB `config.py:319-330`). Any complex quantity we use (phase, group delay, impedance imaginary part) must be conjugated consistently if we ever consume a BL result [verified conventions; handling is our work].
6. Plugin route (GeneratedMesh): `GeneratedMesh(id, purpose="bem_surface", mesh_path=... | mesh_data=MeshData)`, ids `[a-z][a-z0-9_-]*` (BL `generators/base.py:34-50`); an *assembly* response must return a `GenerationResponse` with `physical_patch` (regions/boundaries/components/excitation_ports) and requires symmetry **Off** ("This increment supports full models with symmetry Off. It rejects automatic assembly symmetry reduction", `geometry-provider-api.md`). The legacy single-mesh `GeneratedGeometry(mesh_path=..., radiators=(RadiatorConfig(name,tag),), mirror_axes=...)` path keeps symmetry support and automatic exterior seeding, and is the one Ath uses (BL `generators/ath.py`) [verified]. So the least-mapping route for a symmetric quarter horn is the legacy single-mesh provider with `radiators=(RadiatorConfig("throat", tag=2),)`, `mirror_axes=("x","y")` [inferred].
7. BL cleans/validates meshes (`mesh_clean.py` merge/area tolerances; `mesh_quality.py` warnings; Ath meshes go through `clean_mesh`) [verified existence; effect on our meshes unverified].

---

## C. Ath: parameter names and translators

### C.1 How Boundary Lab uses Ath

* BL drives the external closed-source `ath202608.exe` in batch mode (`ath.exe <cfg> -b`, Wine on Linux/macOS) (BL `ath.py:132-147,208-217`), captures the Gmsh `.geo` on stdout, strips Ath's `Mesh 2; Save` footer, and meshes with its own Gmsh worker (`ath_gmsh_worker.py`, `ath.py:376-...`); config text lives in the project as `source = {"format":"ath_cfg","text":...}` (BL `generators/ath.py:28-34`) [verified]. README: "Ath is bundled with permission from Marcel Batik" (BL `README.md:5`) [verified]. Ath geometry is **millimetres**; BL stores `mesh_scale_factor` 0.001 (`generators/base.py:95`).
* Ath config keys seen in BL's own probe/test config and example (BL `ath_setup.py:TEST_CONFIG`, `examples/Ath_SingleSourceWaveguide/...blab.json`) [verified]: `Throat.Profile`, `Throat.Diameter` (mm, **diameter**), `Throat.Angle`, `Length`, `Coverage.Angle`, `Term.s`, `Term.q`, `Term.n`, `OS.k`, `Slot.Length`, `GCurve.Type/Width/Dist/SF/Rot/AspectRatio`, `Morph.TargetWidth/TargetHeight/TargetShape/FixedPart/Rate/CornerRadius/AllowShrinkage`, `Mesh.AngularSegments/LengthSegments/CornerSegments/ThroatResolution/MouthResolution/InterfaceResolution/InterfaceOffset/Quadrants/SubdomainSlices`, `Mesh.Enclosure = {Spacing, Depth, EdgeRadius, EdgeType, FrontResolution, BackResolution}`, `Output.*`, `ABEC.SimType`. BL itself only parses `Mesh.Quadrants` and the `//#// DRV` footer (BL `ath.py:98-125,60-95`); everything else goes to the Ath exe.

### C.2 Parameter-name comparison (Ath cfg vs hornlab_mesher vs our YAML)

Source of the mesher side: `hornlab_mesher/config_parser.py` `parse_text_config` mapping tables (lines ~690-780 and `_MORPH_KEY_MAP`/`_GCURVE_KEY_MAP` 467-495) [verified]. Our names: `examples/osse_baseline.yaml`, `icw_termination.yaml`, `freeform_*.yaml`, `throat_adapter.yaml`.

| Concept | Ath cfg key | hornlab_mesher dict key (parse_text_config output) | hornlab-search YAML (`seed_params`) | Notes |
|---|---|---|---|---|
| Throat size | `Throat.Diameter` (mm, diameter) | `r0` = diameter/2 (parser divides, `config_parser.py` "if throat_diameter and no r0") | `r0_mm` (radius, mm) | factor 2; Ath also accepts bare `r0` inside an OSSE block |
| Wall half-angle | `Coverage.Angle` (or `a` in block) | `a` | `a_deg` | "coverage HALF-angle in the mesher's convention" (osse_baseline.yaml) |
| Throat angle | `Throat.Angle` (`a0`) | `a0` | `a0_deg` | |
| Length | `Length` (flat) / `L` (OSSE block) | `L` (`_athLengthMode="total"`) | `L_mm` | Ath ignores top-level `Length` beside an OSSE block (parser comment) |
| Termination | `Term.n`, `Term.s`, `Term.q` (`n`,`s`,`q`) | `n`, `s`, `q` | `n`, `s`, `q` | same names |
| Shape factor | `OS.k` / `Term.k` / `k` | `k` | `k` | |
| Throat extension / slot | `Throat.Ext.Length`, `Throat.Ext.Angle`, `Slot.Length` (top level only) | `throatExtLength`, `throatExtAngle`, `slotLength` | `throat_ext_length_mm`, `throat_ext_angle_deg`, `slot_length_mm` | mesher refuses in-block copies |
| R-OSSE | `R-OSSE = { R, a, a0, r0, m, b, q, k, ... }` | formula `R-OSSE`, keys `R,m,b,...` | (not used in our families) | |
| Cross-section | **no OSSE key**; via `GCurve.Type/Width/AspectRatio/SF/SE.n` and `Morph.Target*` | mesher-native `profileSystem.crossSection.{exponent, aspectRatio}` (`config_builder.py:1034-1049`) when given natively; `GCurve.SE.n` -> `gcurveSeN` when parsed from Ath | `exponent`, `aspect_ratio` | not the same code path; see C.4 |
| Mesh resolution | `Mesh.ThroatResolution`, `Mesh.MouthResolution`, `Mesh.RearResolution` (mm) | `throat_res_mm`, `mouth_res_mm`, `rear_res_mm` | `mesh.*` via `sizing` | |
| Symmetry | `Mesh.Quadrants` 1/12/14/1234 | `quadrants` | `mesh.quadrants` | |
| Source tags | `SD1D1001` driven, `SD1G0` wall | same names (`tags.py`) | tag 2 | |
| ICW | **not an Ath concept**: "ICW is not available via the ATH text format" (`config_parser.py:640-643`) | `profile.formula: ICW` via dict/contract only | `termination, kappa0, theta1_deg, R_mm, coverage_angle_deg, hold_start/end, ...` | |
| FREEFORM | not Ath | `profileH/profileV/crossSections` dict | same names as mesher | |

### C.3 Existing translators

* **Ath cfg -> mesher: exists.** `hornlab_mesher.parse_text_config` / `parse_ath_config` / `load_config` (accepts `.cfg`/`.txt`) (HM `config_parser.py:28-35,~600`, exported in `cli.py:36-45`) [verified]. It is strict: only `Throat.Profile = 1` (OS-SE); refuses `Horn.Part`, `Scale.Z`, `Rollback`, multi-source `Source.Contours`, `Mesh.Roundover`, `BEE`, `arcterm`, `trunc` etc., and unknown `Mesh.*` keys (`config_parser.py:75-100, 520-570`) [verified]. Parity claims: "checked against ath.exe V2026-08c" for several behaviours (comments in `config_parser.py`), plus an `ath_parity_sampling` mode (`profile_sampling.py`) [verified as comments; I did not reproduce them].
* **mesher -> Ath cfg: none found.** No writer/exporter in `hornlab_mesher` (grepped `*.py`, `icw/`, `builders/`, `cli.py` for `to_ath`, `export_ath`, `write_cfg`, `ath_cfg`: no hits) [verified]. The mesher's `cad.py` writes a `.wglink` bundle and STEP files, not Ath configs (`read_wglink`, `cad.py:1204`). The task description's "waveguide-generator can open ATH .cfg files" is consistent with the parser, but the reverse direction would be new code [inferred]. Boundary Lab has no mesher->Ath converter either (BL grep for `OSSE`/`hornlab` found nothing in `src/`) [verified by `grep -rn` on `src/blab/generators` and `ath.py` listing].

### C.4 Could our best designs be exported as an Ath cfg and reproduced by BL's Ath generator? Fidelity

* OSSE (our `osse_baseline`, `throat_adapter`): the base profile maps 1:1 by name (table above): `Throat.Diameter = 2*r0_mm`, `Coverage.Angle = a_deg`, `Throat.Angle = a0_deg`, `Length = L_mm`, `Term.n/s/q`, `OS.k = k`; throat extension/slot via `Throat.Ext.*`, `Slot.Length` [verified key mapping both ways]. Geometry fidelity of the **axisymmetric** profile is plausible because the mesher's importer was written against Ath's behaviour and parity-tested upstream [verified claims in comments; unreproduced].
* OSSE non-axisymmetric (`exponent` != 2 or `aspect_ratio` != 1, our default searches both): Ath has no `exponent` or aspect-ratio key in the OSSE block; the likely Ath expression is `GCurve.Type` = superellipse with `GCurve.SE.n = exponent`, `GCurve.AspectRatio = aspect_ratio`, `GCurve.Width`, plus `Morph.*` (the mesher's own parser exposes `SE.n` and `AspectRatio`, `_GCURVE_KEY_MAP:480-495`) [verified keys exist]. Whether the mesher's native `crossSection.exponent/aspectRatio` produces the **same** surface as Ath's GCurve/Morph pipeline is [unverified] and I expect differences in how the guiding curve is applied along the length (Ath: curve defined at `GCurve.Dist`, morph target shape/rate); an exporter would need a numerical check (compare node clouds from `build_from_config` fed the exported cfg vs the original dict, which uses the existing parser as round-trip oracle) [inferred recommended test].
* R-OSSE: mapped by name (`R, a, a0, r0, m, b, q, k`), same caveat [verified keys].
* ICW: **no Ath equivalent** (parser says so). FREEFORM (`profileH/V`, `crossSections`): no Ath equivalent. Any design from those families cannot go to Ath [verified].
* Mesh: Ath emits its own `.geo` and BL re-meshes it with Gmsh; the discretization will differ from `hornlab_mesher` meshes even for identical geometry (different triangulation, `Mesh.*Resolution` semantics), so a BL result is comparable to ours only to BEM discretization error, not bit-for-bit [inferred].
* Enclosure/baffle: `Mesh.Enclosure = {...}` maps to mesher `depth_mm, edge_mm, edge_type, enc_front_resolution, enc_back_resolution` plus `Spacing` (`_ENCLOSURE_KEY_MAP`, `config_parser.py:166-173`) [verified].
* Units: Ath cfg in mm (matches `*_mm`); BL scale 0.001.

---

## D. Licenses

| Component | License | Evidence |
|---|---|---|
| hornlab-beat-bem | declares `GPL-3.0-or-later` (HB `pyproject.toml:10`; README "Licence and provenance" line 1037: "**GPL-3.0-or-later** ... derivative ... stays GPL-3") | [verified] |
| BEAT Engine (BE) | GPL-3 full text in `LICENSE` (GPLv3, 29 June 2007); `pyproject.toml:11 license = {file = "LICENSE"}`; no per-file headers and no "or later" grant found (grep for `any later version`/`SPDX` in `*.py,*.jl,*.toml,*.md`: none) | [verified] |
| Boundary Lab | GPL-3 full text; no `license` field in `pyproject.toml`; same absence of "or later" grants | [verified] |
| Ath executable | proprietary third party, "bundled with permission from Marcel Batik" (BL `README.md:5`) | [verified]; terms of that permission [unverified] |
| hornlab_mesher / hornlab-plots / bempp-bem | AGPL-3.0-or-later (installed metadata) | [verified for mesher and plots] |
| hornlab-search (ours) | AGPL-3.0-or-later (`pyproject.toml:8`) | [verified] |

HB's own VENDORING says upstream "ships the bare GPL-3 licence text with no per-file copyright headers" (HB `VENDORING.md:11-14`). Hence HB's `GPL-3.0-or-later` label is a stronger grant than what upstream visibly gives (upstream looks "GPL-3.0-only" or unspecified) [inferred; this is a question for Collin or a lawyer, not something I can settle]. It matters little to us as long as we stay at v3.

Compatibility (not legal advice) [inferred from GPLv3 section 13 / AGPLv3 section 13]:

* (i) A Boundary Lab plugin that imports `hornlab_mesher` / `hornlab_search`: BL providers are "trusted in-process Python code" loaded by the host (`geometry-provider-api.md`, "Installing and developing provider packages"). The loaded process would combine a GPL-3 host, an AGPL-3-or-later mesher and our AGPL code. GPLv3 s13 and AGPLv3 s13 explicitly allow combining GPLv3 and AGPLv3 works; the GPL parts stay GPL, and the AGPL network clause applies to the combination as a whole. A plugin that uses BL's Python API is itself a derivative of a GPL-3 host, so it must be GPL-compatible: AGPL-3.0-or-later is. No blocker found. Practical effects: (a) the plugin must ship its own source under AGPL/GPL-compatible terms; (b) running such a plugin inside a **hosted** Boundary Lab Server (`blab.cli server --mode hosted`, `Boundary Lab Server.md`) would trigger the AGPL network-source clause for the users of that server; (c) Ath is a separate process (`subprocess.Popen`, `ath.py:208`), not linked.
* (ii) hornlab-search depending on `beat-engine` 0.6.0 directly instead of hornlab-beat-bem: same license family (GPL-3 vs hornlab-beat-bem's derivative GPL-3), already combined with AGPL code in our current dependency set (`pyproject.toml:14-16`; CONTRACTS section 1 "Licensing, stated once"). `beat-engine` is a pure-stdlib Python wheel (`dependencies = []`, BE `pyproject.toml:11-12`) plus Julia sources; licenses of Julia dependencies (CUDA.jl, JSON, StaticArrays, etc.) are [unverified] but are the same ones HB pulls today. Nothing here makes it worse than the current state. Obtaining it: wheel URL with SHA-256 pinned by BL: `https://github.com/JWSound/BEAT_Engine/releases/download/v0.6.0/beat_engine-0.6.0-py3-none-any.whl#sha256=10db2ee28eb9a8675fa0131127a04eeaad61097328c3aac453721a5924187dd3` (BL `pyproject.toml:12`) [verified]; "No PyPI publication is configured" (BE README) [verified].

---

## E. Options: (a) keep hornlab-beat-bem, (b) call BEAT 0.6.0 directly, (c) call Boundary Lab headless/server. Evidence only, no decision.

### Facts that bear on all three

* Our hard rule: "We never modify any installed HornLab, Boundary Lab, BEAT or Julia file" (HS `CLAUDE.md`, CONTRACTS section 1). Option (b)/(c) are consistent; patching HB's Julia is not.
* Our measured hardware limits on RTX 4060 8 GB with the **pinned** stack (HS `TOOLCHAIN.md`): quarter caps 5,000/7,000/8,900 dofs; warm per-frequency 0.4 s at 2.4k, 2.8 s at 5.1k, 7.5 s at 7.0k, 45 s at 8.9k (memory pressure); a 12-frequency sweep call at 5.1k took 689 s vs 33 s as one call per frequency; OOM at 15.7k quarter / above 5.5k-9.2k full; CPU faster-than-never but 1.3x-2.3x slower than CUDA (lines 77-141) [verified in our docs]. None of these numbers were measured against BEAT 0.6.0 [unverified].
* One GPU, one solve at a time (CLAUDE.md); BL server is also "one job at a time ... additional jobs are rejected and not queued" (BL `docs/Boundary Lab Server.md`, Everyday operation) [verified].

### (a) Keep hornlab-beat-bem (current)

* Python API we already use: `SolveConfig`, `solve_frequencies`, polar cuts, `spherical_grid` balloon, surface traces, axial source, persistent host with registry/adoption, hygiene tooling; maintained by Collin who also maintains the mesher/plots (so versions move together) [verified API; maintenance relationship stated in task context].
* Engine snapshot is frozen at ~2026-10-07 plus HornLab patches; BEAT fixes after that date are only ported by hand (`VENDORING.md:787-801` "Porting later official engine changes") [verified]. Stock BEAT features missing there: compiled contract, CUDA direct system in the driver path, exterior transducers, rigid-translation profile, thermoviscous losses, positive-time convention, Float32 LU refinement.
* CUDA path uses four dense operators (no fused/direct); per HIGH_FREQUENCY_OPTIONS.md that is our current VRAM limiter [verified in our doc; in the pinned source, `BeatEngineDriver.jl:1215`]. Metal/CPU already fused.
* Comparability: results match HornLab's other backends (unit-acceleration convention, `exp(-i omega t)`), so our dataset/schemas (`MetricSet`, traces) are consistent [verified conventions].
* License label GPL-3.0-or-later (see D) with the stronger-than-upstream caveat.

### (b) Add a backend that talks to BEAT 0.6.0's worker (`beat-engine` wheel)

* What we would write: a compiled-system request builder (meshes with `scale_to_m=1.0`, one `unbounded_air` region, `SD1G0` rigid boundary, `SD1D1001` moving boundary, one `ideal_velocity_source` component, one `normal_velocity` port), outputs (`exterior_pressure` at our polar and balloon point sets, optional `bem_boundary_pressure/neumann` for traces, `radiation_impedance`), solver options (`bem_backend:"cuda"`, `precision:"float32"`, `symmetry`, `phasor_convention`, `quadrature_order`, `singular_order`, `burton_miller_assembly:"direct_system"`), and result decoding (base64 typed arrays, result schema v2) using `beat_engine.EngineWorker` (BE README "Public Python API") [verified shapes from `example-exterior-request.json` and contract doc]. No code exists for this yet.
* Gains that are verifiable from source: CUDA direct-system assembly + in-place `lu!` by default; CUDA.jl 6.4.2; versioned handshake/capability negotiation and `beat_engine doctor` / `instantiate` tooling (`__main__.py`); maintained, tagged, SHA-256-pinned wheel; later fixes arrive by version bump; same engine and defaults as Boundary Lab users (see below).
* Costs/risks: loses HornLab-only conveniences (native polar cuts, sphere grid, diagonal plane, axial-source flag, persistent-host adoption, HB's hygiene/shutdown semantics: `EngineWorker.terminate()`, `WorkerPool`; whether it reliably ends the Julia process on Windows is [unverified]); the `WorkerCleanup.md` doc covers opt-in CUDA memory cleanup (BE `docs/WorkerCleanup.md`, not read in full); compiled CUDA worker has **no precompiled bundle** (cold start from source; `coupled_solver.jl:24`) [verified; magnitude unmeasured]; per-process Julia depot/instantiate required separately (`python -m beat_engine instantiate --backend cuda`); `precision` Float64 on CUDA unknown; engine wheel needs Python >= 3.11 (ours 3.11-3.13, ok).
* Numerical comparability to our existing dataset: not bit-identical; expected differences are Float32 summation order and conjugated phase (positive-time) if we adopt Boundary Lab's convention; magnitudes should agree to the "float32 repeatability" quoted by BEAT (e.g. rel-L2 ~3e-7 between two CUDA paths, 5.6e-5 vs Float64 CPU on their 20 kHz case, `Exterior CUDA excitations.md`) [verified as reported; not reproduced here]. A pinned-vs-0.6.0 comparison on our seed horns is [unverified] and would be the needed evidence; run each engine in a fresh process (hygiene rule 2).
* GPU memory: CUDA direct path holds one `8*N^2`-byte complex system (+ LU in place, ipiv) for a single excitation; no cached RHS operator for 1 excitation [verified code]. Expected to reduce the "memory pressure" regime observed at 5-9k dofs on 8 GB [inferred; unmeasured]. Persistent-worker pool growth rules still apply (BEAT also keeps a CUDA pool; `WorkerCleanup.md`).
* Maintenance: BEAT's exterior API surface is the contract JSON + schema, covered by a shared Python/Julia conformance corpus (`beat_contract/conformance.json`, 4000 lines) [verified], so breaking changes are versioned ("Existing worker and physical-system contracts remain supported").

### (c) Call Boundary Lab headless (`blab project solve`) or server

* Headless: `blab project validate x.blab.json --json`, `blab project solve x.blab.json --backend beat_cuda --output runs/x [--request overlay.json --events ndjson]`; output directory must not exist; result artifact directory with `manifest.json`, `request.json`, `compiled-system.json`, `domains.npz`, per-frequency `.json/.npz`, `exp(+i omega t)` (BL `docs/advanced/cli-workflow.md`, Headless Project Workflow and Result artifact) [verified]. Overlay supports arbitrary exterior `probes` (`points_m`), `frequencies_hz`/`frequency_sweep`, `retain` (`bem_boundary_pressure`, `bem_boundary_neumann`, `bem_boundary_traces`), `solver_options` (quadrature orders, `burton_miller_assembly`) [verified].
* Requires: a complete `.blab.json` physical system per candidate (we would generate it and the mesh file), BL installed (Python >= 3.11 with `gmsh, matplotlib, meshio, numpy, scipy` + optional GUI extra), Julia + BEAT instantiated, and process start per solve (Python+Julia start-up each time unless the BL server/worker is reused): per-candidate overhead is [unverified]; the headless CLI creates a new run directory and compiles the system each call.
* Server: `python -m blab.cli server --root ... --mode private-network|hosted --port 8765`, key via `BLAB_SERVER_TOKEN`, **one job at a time, others rejected** (BL `docs/Boundary Lab Server.md`); "Polar and balloon results are supported; observation planes are not yet available for remote solves"; HTTP API shape not read (`src/blab/server.py`, `remote_contract.py` unread) [unverified]. It selects the backend by policy "available GPU, then CPU" unless `--backend` is pinned.
* Comparability: strongest (identical code path as GUI users, same defaults: FP32 production backend `PhysicalSystemProductionBackend`, CUDA Julia threads 4 / others 8, `burton_miller_assembly` default `direct_system` for cuda/metal and `operator_matrices` for cpu; BL `solvers/coupled_backend.py:379-404,1041-1057`) [verified]. Cost: the heaviest dependency (Boundary Lab app + its mesh cleaning/compile layer between us and BEAT), AGPL/GPL mixture at process level is fine (subprocess) but anything importing `blab` in-process is GPL-3 combined work.
* BL mesh handling adds steps we do not control: `mesh_clean`/`mesh_quality`, exterior stitching optional, symmetry fundamental-domain checks, interface logic for coupled systems we do not need.
* Ath option: BL's native geometry path (Ath cfg) cannot express ICW/FREEFORM and approximates our non-circular OSSE cross-sections (C.4). A mesher-mesh project uses the "imported mesh" path instead (B.2).

### Cross-cutting facts

| Fact | Evidence |
|---|---|
| BL 0.5.0 pins exactly `beat-engine` 0.6.0 wheel with sha256 `10db2ee2...187dd3` | BL `pyproject.toml:12` [verified] |
| BEAT and BL production CUDA exterior default: direct system + LU on device, FP32 | BE `README.md` "Exterior-only compiled-system CUDA and Metal solves default to direct Burton-Miller assembly" + BL `coupled_backend.py` [verified] |
| BEAT docs still describe engine `0.1.2` in a protocol table and README says "package version is `0.4.0`" while the wheel is 0.6.0 (`worker-v1.json` says 0.6.0) | BE `docs/BEAT Worker Protocol.md`, `README.md`; stale docs, trust code [verified] |
| Phase convention differs (BL/BEAT positive time vs HornLab negative time) | `Phasor Convention.md`, BL `docs/Inputs and Outputs.md` ("Boundary Lab requests native exp(+i omega t)") vs HB `config.py:319-330` [verified] |
| 0.6.0 numerics changes outside coupled/Metal: none vs 0.5.1 | `git diff v0.5.1 v0.6.0 --stat -- src` [verified] |
| Unknown for 8 GB RTX 4060: BEAT 0.6.0 CUDA direct path peak VRAM, per-frequency time, sweep cliff behavior, cold start without a CUDA compiled bundle | no measurement possible here [unverified] |

---

## Things I could not verify

* Any runtime behavior (no code executed; no Julia, GPU, gmsh, mesher or BL run).
* Whether mesher native `crossSection.exponent/aspectRatio` equals Ath `GCurve`/`Morph` output; geometry equality of an exported Ath cfg.
* CUDA Float64 support in the 0.6.0 compiled driver; CUDA driver/toolkit requirement for CUDA.jl 6.4.2 / runtime jll 0.25 on our machine.
* HTTP API of `blab server` and `remote_contract.py`; per-call overhead of `blab project solve`.
* Whether `EngineWorker.terminate()` ends Julia reliably on Windows (our hygiene rule 6 concern).
* Legal conclusions in D; the Ath redistribution permission terms; Julia dependency licenses.
* How tags 4, 8-12 appear in our current meshes (our families appear to use only 1 and 2; not exhaustively checked).
