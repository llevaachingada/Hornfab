<!-- Research appendix, 2026-10-21. Produced by a research subagent under senior-review orchestration, read-only against Boundary Lab v0.5.0 (6c9185b), BEAT_Engine v0.6.0 (1bb46da), hornlab-beat-bem 38544d2. Key claims spot-checked by the orchestrator (see docs/BOUNDARY_LAB_0.5_RESEARCH.md section 0). Paths like BL/..., BE/..., HB/..., HM/... refer to those repos; local clone paths have been removed. -->

# Boundary Lab 0.5.0 - integration inventory for hornlab-search

Scope: read-only study of the clone at `.../scratchpad/ext/boundary-lab` (tag `v0.5.0`, HEAD `6c9185b`, 2026-10-20; `git tag` shows `0.4.3`, `v0.4.4`, `v0.5.0`). Nothing was executed or installed; the bundled `ath/ath202608.exe` was only inspected with `strings`.

Conventions: all paths are relative to the clone root. `file:line` citations refer to the v0.5.0 tree. **[verified]** = read directly in source/docs; **[inferred]** = my deduction from code structure, not directly stated or tested. Terms: BL = Boundary Lab; BEAT = BEAT Engine (the Julia solver BL wraps, `beat-engine` wheel).

Repo facts: Python >= 3.11 (`pyproject.toml:10`), package `boundary-lab` 0.5.0, entry point `blab = blab.cli:main` (`pyproject.toml:33-34`), GitHub `JWSound/boundary-lab` (README). 408 commits, 55 between v0.4.4 and v0.5.0. CI is Windows-only, Python 3.11 (`.github/workflows/ci.yml`); GUI = PySide6 + pyvista (optional extra `gui`, `pyproject.toml:23-27`); base install (no extra) is the Qt-free headless stack: `beat-engine`, `gmsh`, `matplotlib`, `meshio`, `numpy`, `scipy` (`pyproject.toml:12-19`).

---

## 1. Entry points: `blab` CLI

### 1.1 Top-level dispatcher
`src/blab/cli.py:7-17` maps `blab <command>` to a module's `main(args, prog=...)` (lazy `import_module`, so `blab project` never imports Qt) [verified]:

| Command | Module | Notes |
|---|---|---|
| `gui` | `blab.gui` (`gui.py:297`) | Needs `[gui]` extra |
| `project` | `blab.project_cli` | **The automation surface** (validate/solve/evaluate-fem/compare-fem/export-speaker/speaker-preflight) |
| `server` | `blab.server` (`server.py:337`) | HTTP job server (section 3) |
| `clean` | `blab.mesh_clean` (`mesh_clean.py:1151`) | `blab clean in.msh out.msh --merge-tol ...` (writes Gmsh 2.2) |
| `conform-interface` | `blab.interface_conform` (`:1668`) | FEM/BEM interface conforming (`--fem-interface`, `--bem-interface`, `--force`, `--binary`) |
| `rocm` | `blab.rocm` (`:274`) | `detect` / `configure` / `clear` SDK discovery (`--json`) |
| `prepare`, `plot` | `blab.postprocess`, `blab.plotting` | Legacy: operate on historical `.npz` result files |
| `solve` | `blab.solver` | **Retired**: prints a message and `SystemExit`s with text (`solver.py:6-12`) |

### 1.2 `blab project ...` (`src/blab/project_cli.py`)

| Subcommand | Args (project_cli.py lines) | Effect |
|---|---|---|
| `validate PROJECT` | `--request FILE`, `--backend {beat_auto,beat_cpu,beat_cuda,beat_rocm,beat_metal...}` (default `beat_auto`), `--julia-executable` (default env `BLAB_JULIA_EXE` or `julia`), `--json` (:55-64) | Load -> migrate -> compile -> validate. Prints summary. No matrix assembly. |
| `solve PROJECT` | `--request`, `--backend`, `--output DIR`, `--server-url URL`, `--server-token-env` (default `BLAB_SERVER_TOKEN`), `--events {text,ndjson}`, `--julia-executable`, `--julia-threads N|auto` (:66-88) | Full solve, writes a run directory (section 5.1) |
| `evaluate-fem RUN_DIR` | `--surface-pattern` (repeatable, default `exit_*`), gates, `--split-surface-entities` (:90-112) | Interior-FEM exit-plane QA; irrelevant to exterior BEM |
| `compare-fem A B` | convergence gates (:114-124) | Irrelevant to exterior BEM |
| `export-speaker PROJECT --output X.blabsp` | `--fidelity {pattern,fixed,coupled}`, `--viewport-model`, ROM options, `--events` (:126-147) | Solves and writes a `.blabsp` ZIP64 package |
| `speaker-preflight PROJECT` | `--rom-rank`, `--precision`, `--json` (:149-162) | Storage/VRAM estimate for Level-3 packages |

Backend ids: `HEADLESS_BACKEND_IDS = ("beat_auto", *f"beat_{info.backend_id}" for backend_catalog())` (`headless.py:65-66`). The catalog comes from the installed `beat_engine` wheel (cpu, cuda, rocm, metal per release docs [inferred from `docs/macos-installer.md`, `beat-engine-*.md`]; legacy alias `beat_cpu_condensed -> beat_cpu`, `solvers/registry.py:102-130`). `beat_auto` = CUDA if `nvidia-smi` exists, `julia` exists and a subprocess `julia --project=<cuda env> -e "import CUDA; exit(CUDA.functional() ? 0 : 1)"` succeeds (30 s timeout), else CPU (`headless.py:184-226`) [verified]. **Gotcha:** `validate --backend beat_auto` therefore *does* launch Julia for the probe (`project_cli.py:205`), contradicting the doc sentence "does not launch Julia" (`docs/advanced/cli-workflow.md:74`). Use an explicit `--backend` to avoid it [verified].

### 1.3 Exit codes and error channel [verified]
- Success: `0`.
- `KeyboardInterrupt`: `130` (`project_cli.py:182-183`). The run dir is finalized `status: "interrupted"` (`headless.py:598-605`).
- Any other exception (bad project, invalid request, solver failure, **existing `--output` dir**, missing Julia): `1` (`:184-199`). With `--json` or `--events ndjson` the error is one stdout JSON line `{"event":"error","error_type":...,"message":...}`; otherwise `Type: msg` on stderr.
- Argparse usage errors: `2` (standard argparse, `cli.py:26-34`).
- There is no finer taxonomy (no distinct codes for validation vs solver failure vs OOM). Failures after the first frequency leave a partially valid run dir (`status: "failed"`, `completion_mask` shows what finished).

### 1.4 Can a project be solved headless without the GUI? Yes [verified]
`blab project solve` loads the `.blab.json`, compiles with the same `prepare_system_solve` path the GUI uses, and runs `PhysicalSystemProductionBackend(...).create_system_session(request).solve_stream()` (`headless.py:544-630`). Preconditions:
1. The project **must contain a `physical_system` object** (`headless.py:102-103`). Legacy projects that only have Ath `source_config_by_name` (e.g. `examples/Ath_SingleSourceWaveguide`, `Ath_2WayBookshelf`, `Ath+Mesh_*`; checked: 5 of the 13 shipped example projects) have none and are rejected - they must be opened/saved once in the GUI, which seeds the system. [verified by scripting over `examples/**/*.blab.json`]
2. Mesh files must exist (or be embedded `MeshData`).
3. Julia on PATH (or `--julia-executable`/`BLAB_JULIA_EXE`), and `python -m beat_engine instantiate --backend <cpu|cuda|...>` done (README).
4. `--output` must not exist (`headless.py:411-413`); default is `<project dir>/runs/headless/<name>-<YYYYmmdd-HHMMSS>` (`:392-396`).
5. In headless mode the GUI-only steps do **not** run: near-coincident-vertex repair (`ui/mesh_assembly.py`), exterior watertightness warning dialog (`ui/main_window/solve_workflow.py:473,658`), preview. `analyze_exterior_mesh_topology` (`mesh_topology.py`) is Qt-free and could be called by us pre-solve [inferred]. A bad mesh surfaces as the post-hoc error "solver returned non-finite results" (`coupled_backend.py` `_parse_result`).

### 1.5 Progress events (`--events ndjson`, stdout, one JSON per line) [verified, `headless.py:565-630`]
`started{output,backend_id,frequency_count}` -> `status{message}`* -> `frequency_completed{index,freq_hz,solved_count,frequency_count}`* -> `completed{output,backend_id,solved_count,frequency_count}` | `failed{message,solved_count}` | `interrupted{solved_count}`. In `text` mode, progress goes to stderr and the final summary JSON to stdout.

### 1.6 `validate --json` output keys [verified, `headless.py:363-389`]
`valid, project, project_schema_version, system_id, system_name, solve_kind (exterior_bem|coupled_bem_fem|interior_fem), backend_id, symmetry, frequency_count, frequency_min_hz, frequency_max_hz, excitation_port_ids[], output_ids[], meshes[{id,name,purpose,file,size_bytes,sha256}|{...,source:"memory",file:null,sha256}], assumptions[{status:included|excluded,statement}], backend_requested`.

### 1.7 Request overlay (`--request FILE`, schema_version 1) [verified, `headless.py:229-268, 633-694`]
`frequencies_hz[]` XOR `frequency_sweep{min_hz,max_hz,count,spacing:log|linear}`; `excitation_port_ids[]`; `include_project_observations` (default true; false drops the H/V polar + sphere + radiation-source outputs); `probes[{id, coordinate_frame:"project", points_m:[[x,y,z],...]}]` -> quantity `acoustic:pressure:probe:<id>` on domain `observation:probe:<id>`; `retain[] in {bem_boundary_pressure, bem_boundary_neumann, bem_boundary_traces, fem_nodal_pressure, interface_radiated_pressure}`; `solver_options{}` (overlay on defaults; `symmetry` must equal the project's, `headless.py:345-347`). Frequencies must be finite, > 0, unique (`:663-671`). Probes in interior-only systems are rejected. Observation planes are *not* settable in the overlay.

---

## 2. Project format (`.blab.json`)

### 2.1 Schema version and migration [verified]
- `PROJECT_SCHEMA_VERSION = 10` (`src/blab/project/io.py:18`); loader accepts 1..10, raises otherwise (`:150-162`). v1/v2 migrate the legacy Ath scripts; <=6 migrate global FEM loss onto bounded regions (`:158-162, 207-295`). v9 -> v10 (0.5.0) only adds assembly artifacts (`artifact.meshes[]`, `provider_metadata`); `git diff v0.4.4 v0.5.0 -- src/blab/project/io.py` is +8 lines. "Releases supporting only schema 9 or earlier reject schema 10" (`docs/advanced/geometry-provider-api.md:181-182`).
- **Docs are stale on this**: `docs/Inputs and Outputs.md` example shows `"schema_version": 8` [verified].
- Normalization (`io.py:175-204`) builds a *fresh dict*: unknown top-level keys are dropped when BL loads the file (the on-disk file is untouched until the GUI saves). `physical_system.metadata` (open JSON dict, validated finite-JSON by the compiler, `physical_compiler.py` `_validate_json_mapping`) and `generator_documents[].source` (provider-owned dict) do survive.

### 2.2 Top-level structure (`io.py:21-35`)
| Key | Content |
|---|---|
| `schema_version` | 10 |
| `generator_documents[]` | `{id, name, provider_id, provider_schema_version, source{}, mesh_enabled, mesh_scale_factor (default **0.001**), mesh_translation_mm [x,y,z] (**rounded to int mm** on save/load, `project/model.py:211,231-239`), artifact{...}}` (`model.py:198-244`) |
| `active_generator_document_id` | GUI tab |
| `imported_meshes[]` | GUI inventory: `{name, source_file, cleaned_file, scale_factor (0.001), translation_mm, enabled}`; **ignored by the headless loader** (it reads `physical_system.meshes`) |
| `stitch_exterior_meshes` | bool; fuse all exterior-region BEM parts using `stitch_tolerance_mm` |
| `symmetry` | `"off"|"x"|"xy"`; invalid value silently becomes `off` (`headless.py:108-110`) |
| `source_config_by_name` | legacy radiator config (read-only compat, dropped once a physical system exists) |
| `channel_config_by_name`, `component_channel_by_id`, `max_spl_limits_by_channel` | GUI channel synthesis only; headless output is per-excitation, never channel-mixed |
| `project_preferences` | see 2.5 |
| `physical_system` | the authoring graph (2.3) |
| `observation_planes[]` | GUI field planes (need retained BEM traces; not part of the `--request`) |

`generator_documents[].artifact` (`model.py:269-299`): `output_dir, mesh_path, cleaned_mesh_path, reduced_cleaned_mesh_path, source_path`, plus `mesh_data`/`reduced_mesh_data` (packed base64 `MeshData`), `mirror_axes[]`, and for assemblies `meshes[{id,purpose,mesh_path,mesh_data}]` + `provider_metadata`. Relative paths are stored relative to the project dir and resolved on read (`io.py:66-147`).

### 2.3 Physical System Model (`docs/Physical System Model.md`, `src/blab/physical_model.py`) [verified]
`PHYSICAL_MODEL_VERSION = 1` (`physical_model.py:18`); `physical_system_from_dict` raises on other values (`:261-263`).

| Entity | Fields | Enums |
|---|---|---|
| `meshes[]` `MeshResource` | `id, name, file, purpose, scale_to_m (1.0), translation_m [3], mesh_data?` | `purpose`: `bem_surface`, `fem_volume` |
| `regions[]` `AcousticRegion` | `id, name, kind, mesh_ids[], volume_groups[PhysicalGroupRef], sound_speed_m_per_s (343), density_kg_per_m3 (1.21), loss_model{}` | `bounded_air` (FEM), `unbounded_air` (BEM) |
| `boundaries[]` `Boundary` | `id, name, region_id, group{mesh_id, dimension(2), name?, tag?}, kind, parameters{}` | `rigid, moving, interface, plane_wave_tube_termination, impedance, unused(->rigid)` |
| `interfaces[]` | `id, name, bounded_boundary_id, unbounded_boundary_id, coordinate_tolerance_m (1e-8)` | coupled only |
| `components[]` | `id, name, kind, boundary_ids[], parameters{}` | `ideal_velocity_source, electrodynamic_transducer, passive_radiator(deferred)` |
| `excitation_ports[]` | `id, name, component_id, kind` | `normal_velocity` (1 m/s basis), `voltage` (2.83 V basis) |
| `model_version`, `metadata{}` | | |

Solve kind inferred from regions (`infer_physical_solve_kind`, `physical_model.py:154-173`): exactly 1 unbounded + 0 bounded = `exterior_bem`; 0 unbounded = `interior_fem`; both = `coupled_bem_fem`. More than one unbounded region is an error.

Compiler invariants (`physical_compiler.py:255-455, 690-748`): unique object IDs globally; region/mesh purpose match; every tagged surface group of each region's mesh gets exactly one boundary (unassigned *or* extra/duplicate groups are errors - so `Boundary.group` set must equal the mesh's surface physical groups); a `moving` boundary owned by exactly one component; each active component has exactly one compatible port; groups resolve by `name` (and `tag` if both given they must match), else by `tag` alone (the `tests/fixtures/remote-exterior.blab.json` fixture uses tags with `name: null`, `group.tag` 1/2); mesh must carry `gmsh:physical` cell data.

### 2.4 What an exterior BEM-only (waveguide) model needs [verified: `solvers/coupled_backend.py:730-778`, `physical_compiler.py`, `system_solve.py`]
1. One `bem_surface` mesh resource (`scale_to_m = 1.0` for metres; translation in metres).
2. One `unbounded_air` region referencing it; `volume_groups: []`; `loss_model: {}` (a non-empty loss model is rejected: "does not support region loss models").
3. A `Boundary` for every surface physical group: `rigid` or `moving`, with `parameters: {}` (any boundary parameters rejected).
4. One `ideal_velocity_source` component owning the `moving` boundary(ies), one `normal_velocity` port per component. Component `parameters` may only contain `motion_profile` (`uniform`/`uniform_normal` default, or `rigid_translation`), `motion_axis` (required and unit-normalised for `rigid_translation`; must lie in active symmetry planes), `boundary_motion_weights{boundary_id: w>0}` (`source_motion.py:1-43`). Electrodynamic transducers are rejected in exterior-only.
5. `interfaces: []`.
6. Top-level `symmetry` consistent with the mesh (reduced mesh must lie in the positive-X / positive-X,Y fundamental domain; near-plane points are snapped, `symmetry.py`). Without symmetry the BEM surface must be watertight; with symmetry open edges are allowed only on the symmetry planes (`docs/Coupled Solver.md:180-182`). **Normals must be outward** (docs/Model Assumptions: "The exterior mesh is the boundary of the acoustic domain"; explicit orientation validation for plain exterior meshes was not found in the headless path) [inferred].
7. Frequencies via `project_preferences` or the request overlay.
Minimal working example: `tests/fixtures/remote-exterior.blab.json` (only `schema_version`, `physical_system`, `symmetry`) [verified]. Everything else defaults (`ProjectPreferencesState()`; one default Ath generator document with no artifact).

### 2.5 Frequency and observation settings (`project/model.py:23-105`)
`project_preferences`: `freq_min_hz` (200), `freq_max_hz` (20000), `freq_count` (41) - **parsed as ints** (`_bounded_int`; a float is truncated) and log-spaced as float32 (`live.py:959-968`); `polar_angle_step_deg` (10), `polar_observation_distance_m` (2.0), `spherical_sampling_enabled` (False), `balloon_angle_precision_deg` (2.5; clamped to 0.5..15; Fibonacci point count = `round(41253/angle^2)`, `headless.py:281-282`), `stitch_tolerance_mm` (2.0), plus GUI display fields. Use `--request` `frequencies_hz` for non-integer or arbitrary frequencies.

Observation geometry (`system_solve.py:474-507`) [verified]: forward axis is **+Z**; horizontal polar = `d*[sin a, 0, cos a]` (XZ plane), vertical = `d*[0, sin a, cos a]` (YZ plane), `a` in [-180, 180] step `polar_angle_step_deg`, at `polar_observation_distance_m` (default 2 m); optional equal-area Fibonacci sphere (`theta_polar_rad` from +Z, `phi_azimuth_rad` from +X toward +Y). Solver options default `quadrature_order=4, singular_order=4` for BEM-only, 2/2 with FEM; `cache_frequency_invariant: true`; Burton-Miller always on, `burton_miller_assembly: direct_system|operator_matrices` for exterior (`coupled_backend.py:739-741`).

### 2.6 Mesh format [verified, partly inferred]
`docs/Coupled Solver.md:~68`: FEM = Gmsh 4.1 ASCII tetra; BEM = **Gmsh 2.2 ASCII** first-order triangles. Files are read twice: by BL via `meshio` (`mesh_cache.py`) and by the Julia worker by path [the path is passed in the compiled request, section 4]. Memory meshes (`MeshData`) avoid files (section 4.4).

---

## 3. Server / remote API

### 3.1 Transport and endpoints [verified: `src/blab/server.py`, `docs/advanced/boundary-lab-server_advanced.md`]
Plain HTTP (`ThreadingHTTPServer`), JSON replies, ZIP uploads. `blab server --root DIR [--port 8765] [--host 127.0.0.1] [--mode private-network|hosted] [--backend auto|cpu|cuda|rocm...] [--token-env NAME] [--julia-executable] [--julia-threads]` (`server.py:337-393`).

| Method/path | Behaviour |
|---|---|
| `GET /v1/capabilities[?connection_test=1]` | `{protocol:"blab-remote", version:2, state: ready|starting|unavailable, request_schema_version, result_schema_version, backend_ids[], backends{id:{available,state,reason,engine,runtime,solve_kinds}}, phasor_conventions:["exp(+i omega t)"], observation_planes:false, max_bundle_bytes: 256 MiB, runtime_check}` (`server.py:254-278`) |
| `POST /v1/jobs` | `Content-Type: application/zip`, bounded `Content-Length` (no chunked). 202 `{job_id}` after staging/validation. 409 if a job is already running (**no queue**); 415 wrong type; 400 invalid; 401 bad token (`:279-292`, `submit` `:114-150`) |
| `GET /v1/jobs/<32-hex>?cursor=N` | up to 32 events from the on-disk `events.ndjson` journal + `next_cursor` (`:293-298`) |
| `DELETE /v1/jobs/<id>` | cooperative cancel, 202 (`:299-301`, `cancel` `:193-200`) |

Events: `accepted{backend_id, execution_backend}`, `status{message}`, `result{result: system_frequency_result dict}`, terminal `completed|failed{error}|cancelled` with `worker` provenance (`server.py:127-191`).
Job upload (`remote_contract.py`): ZIP with `job.json` + `assets/<sha256>.msh`; envelope keys exactly `{protocol:"blab-remote", version:2, observation_planes:false, request, assets[{name,size,sha256}]}`; `request` keys exactly `{schema_version, compiled_system, frequencies_hz, excitation_port_ids, outputs, solver_options}`; `solver_options` allowlist `{quadrature_order, singular_order, validation_diagnostics, cache_frequency_invariant, static_condensation, symmetry, precision, bem_backend, transducer_reference_voltage_v}`; output `options` limited to `{points_m, observation_domains}`; <=1024 entries, 256 MiB (`remote_contract.py:20-70, 114-166`). Server picks backend (auto: CUDA > ROCm > CPU; interior FEM always CPU; pinned unavailable runtime fails, `server.py:78-99`).

### 3.2 Auth, versions, lifecycle
- `Authorization: Bearer <token>` compared with `hmac.compare_digest`; token >= 32 ASCII chars, no whitespace; env `BLAB_SERVER_TOKEN` (or `--token-env`). `hosted` mode *requires* a token; `private-network` allows none (`server.py:213-219, 246-251`). HTTP only (TLS by proxy/VPN/SSH). No users, no per-job ownership: all token holders see all jobs. Client refuses redirects and uses system TLS trust (`remote.py:185-211`).
- Version negotiation: client demands exact equality of `protocol`, `version` (=2), `request_schema_version`, `result_schema_version` and support for `exp(+i omega t)` (`remote.py:246-259`). Service version "is independent of the engine request/result versions".
- Lifecycle: one job at a time; restart marks interrupted jobs failed, keeps journals; **no retention cleanup, no queue**; docs call it "a development preview, not a public HTTP service deployment" (`boundary-lab-server_advanced.md:119-124`). Remote observation planes unsupported. Memory meshes are rejected for remote transport (`docs/advanced/geometry-provider-api.md:518-520`; `protocol.py:21-27`); `build_job_bundle` reads `.msh` files only (`remote_contract.py:73-107`).
- Client side: `blab project solve --server-url http://host:8765 [--server-token-env X]` uses `RemoteBackend`/`RemoteSession` (`remote.py`): upload bundle, poll cursor every 0.2 s, convert events back into `SystemFrequencyResult`, write the *same* run-dir artifact with `manifest.remote_job_id` (`headless.py:599-617`). `--backend` must be omitted with `--server-url` (`project_cli.py:229-231`).
- Docker: `Dockerfile` targets `cpu` and `cuda` (Julia 1.12.6 image), env `BLAB_SERVER_MODE=hosted`, `/data/jobs`, port 8765 (`docs/Docker.md`).

### 3.3 What an external client needs for the server [verified/inferred]
The wire payload is the *compiled* BEAT request (`SystemSolveRequest` -> `system_solve_request_to_dict`), including FEM-BEM topology maps. A non-BL client must either (a) call BL's own compile code to produce it, or (b) hand-build a compiled system itself, which for exterior BEM is straightforward (no interfaces; resolved group tags/element counts - `compiled_system` schema in the BEAT repo `system-v1.schema.json`, not vendored here). [inferred]

---

## 4. Solver / worker contracts

### 4.1 Who owns what [verified: `docs/advanced/BEAT Compiled System Contract.md`, `BEAT Local Dependency.md`]
BEAT owns the numerical wire format, JSON Schema (`urn:beat-engine:system-solve:1`), conformance corpus and Python+Julia validators; BL owns authoring, migration, mesh preparation and the translation (`system_contract.py` maps an explicit field list, not `asdict`). Independent clients "can construct JSON requests without importing Boundary Lab". Versions: request `schema_version` 1, compiled system `contract_version` 1 (BL emits 2 for exterior sources with `rigid_translation`, `physical_compiler.py:~125`), frequency result `schema_version` 2 (typed base64 arrays: `dtype`, `shape`, `order:"C"`, `byte_order:"little"`; complex = interleaved re/im), result-v1 decimal decoding retained for history. Field-array protocol v1 for `bem_field`.

**Docs lag the code:** worker/contract docs cite BEAT `v0.1.2` URLs and `cli-workflow.md:53-54` says "pinned BEAT Engine 0.4.0", while the pin is **0.6.0** (see section 8). Treat the Python source and `engine_distribution.py` as authoritative [verified].

### 4.2 Compiled system essentials (units, tags, symmetry)
- Geometry = `points * scale_to_m + translation_m`, all lengths in **metres**; sound speed m/s; density kg/m^3; frequency Hz; observation points in the same global metre frame (`BEAT Compiled System Contract.md` "Coordinates, paths..."). Faces/indices zero-based; interface maps zero-based.
- Mesh references in a compiled system are **worker-local filesystem paths**; relative paths resolve against the worker's cwd, so BL absolutises them (`physical_compiler.py` `_compile_mesh` -> `str(Path(file).resolve())`). Physical groups resolved to `{mesh_id, dimension, tag, name}`.
- Boundary tags/names: BL resolves by Gmsh physical *name* (preferred) or tag; renumbering tags across regenerations is safe if names are stable (`docs/advanced/geometry-provider-api.md:274-278`).
- Symmetry: passed as `solver_options.symmetry` (`off|x|xy`); BL passes a **reduced** mesh and BEAT adds mirrored source contributions and evaluates the full-space field from the reduced solve (`docs/Model Assumptions.md` "Symmetry"). BL infers completion factors for electrodynamic drivers only; for ideal exterior sources the user supplies the physical meaning (full-rate velocity on the reduced surface). Mesh/symmetry mismatches are the user's responsibility (`SymmetryValidationError`, `symmetry.py:29-39`, raised during GUI/compile preparation).
- Phasor convention: BL requests `exp(+i omega t)` and rejects workers/results that do not report it (`coupled_backend.py` `_parse_result`; `docs/Inputs and Outputs.md`; `docs/advanced/Phasor Convention.md`).
- Precision: BL's production backend is hard-wired `precision="float32"` (`coupled_backend.py:1057`); frequencies are float32-quantised by `build_log_frequencies`. No float64 option through the headless CLI (the engine's FP64 CPU reference is "not selectable as an application solver", `docs/Coupled Solver.md`) [verified].

### 4.3 Worker protocol (`docs/advanced/BEAT Worker Protocol.md`) [verified]
Persistent Julia worker driven over stdin/stdout JSON lines: `ready` announcement (protocol `beat-worker` v1; `contracts`; `operations: solve, bem_field`; `precisions`; `solve_kinds`; per-backend `available`+`reason`; `cancellation: marker_file`; runtime/provenance), commands `{"operation":"solve","request":"/abs/request.json","protocol_version":1,"result_schema_version":2}`, events `status|result|field_result` then exactly one terminal `completed|cancelled|failed` (code `worker_request_failed`). Cooperative cancel via a marker file named in `cancel_path`. After a terminal event the process is reusable; closing an iterator early discards the worker. Mesh paths are worker-local ("no remote asset transfer" in the protocol itself; the HTTP server layers it on top).
Provenance (`BEAT Run Provenance.md`): each result carries `diagnostics.engine_provenance` (engine name/version/`source_sha256`, Julia path, Project/Manifest hashes, sysimage, threads, BLAS, OS/CPU, actual backend/device, per-mesh SHA-256).

### 4.4 In-memory meshes ("inline" transport)
BEAT worker advertises `contracts.mesh_data:[1]` and `request_transports:["file","inline_json"]`; BL then sends the whole request as one JSON line with base64 packed `float64` points and `int64` connectivity/tags (`docs/advanced/geometry-provider-api.md:507-521`; `coupled_backend.py:~259-300`: `inline = any(mesh.mesh_data ...)`, no cancel marker; cancelling an inline solve terminates the worker). Local only; not for the HTTP server.

### 4.5 Backend selection [verified]
Local ids `beat_cpu`, `beat_cuda`, `beat_rocm`, (`beat_metal` on Apple Silicon) from `beat_engine.backend_catalog()`; each maps to a Julia project dir (`engine_paths(backend).project`) and Julia threads default 8 (CPU/others) / 4 (CUDA) (`coupled_backend.py:1047-1049`). `BLAB_PACKAGED_BACKENDS` restricts the list for installers (`solvers/registry.py:80-82`). `beat_remote` = server. CUDA needs Maxwell+; ROCm needs rocBLAS+rocSOLVER; Metal Float32, CPU/Metal FEM options (docs). Backend availability is a runtime probe, not a numerical qualification (worker protocol doc).
**Hard version coupling:** `engine_distribution.py:9-11` raises at import unless `beat_engine.__version__ == "0.6.0"`. Installing `boundary-lab` into an environment that also hosts `hornlab_beat_bem` pins the *whole env* to one beat-engine version [inferred conflict; hornlab_beat_bem's own BEAT pin not visible here].
**Worker lifetime:** `PhysicalSystemProductionBackend` defaults `persistent_worker=True` (`coupled_backend.py:1045`), workers live in an in-process `WorkerPool` (`beat_engine_runtime.py:158-184`). `project_cli`/`headless` never call `shutdown_beat_engine_workers()` (only `server.py:392` and the GUI do; grep-verified). Whether the Julia child exits promptly when `blab project solve` exits (pipe EOF) or lingers (idle timeout) is **not determinable from this repo** - must be tested against your GPU-hygiene rules before relying on it [inferred risk]. A server process, by contrast, owns/stops its workers (`server.py:386-393`).

---

## 5. Results

### 5.1 Headless run directory (`HeadlessResultWriter`, `headless.py:399-541`; `docs/advanced/cli-workflow.md:205-231`) [verified]
```
<out>/manifest.json            schema "boundary-lab-headless-result", schema_version 2
      project.snapshot.blab.json   byte copy of the input project
      request.json             the public overlay actually used (+ remote info)
      compiled-system.json     full compiled BEAT system (with absolute mesh paths)
      domains.json / domains.npz   frequency-invariant coordinates/topology
      frequencies/NNNNNN.json  per-frequency metadata (+ diagnostics, engine_provenance)
      frequencies/NNNNNN.npz   arrays q0000, q0001, ... (complex64 pressure etc.)
```
`manifest.json`: `status (running|complete|failed|interrupted)`, `started_at_utc`, `finished_at_utc`, `project_sha256`, `backend_id` (actual backend if remote), `solve_kind`, `phasor_convention`, `frequencies_hz[]` (request order; ascending log by default in headless), `excitation_port_ids[]`, `solver_options`, `engine_runs[]`, `meshes[{id,name,purpose,file|source:memory,sha256}]`, `completion_mask[]`, `results[{freq_hz,metadata_file,arrays_file}]`, `remote_job_id`, `worker`, `error`. Each frequency is committed atomically (tmp + `os.replace`), so partial runs remain readable. Frequency JSON: `{freq_hz, excitation_port_ids, diagnostics, arrays_file, quantities[{key:"qNNNN", id, quantity, unit, target_id, axes[], shape[], dtype, metadata}]}`.
No official Python *loader* exists for this directory (only an internal reader in `fem_validation.py:299-340`); the layout is simple (manifest -> JSON -> `np.load` NPZ) [verified by grep].

### 5.2 Canonical quantities for an exterior solve [verified: `solve_results/model.py:29-48`, `system_solve.py:129-307`]
| Quantity id | Axes (after `frequency`) | Unit | Meaning |
|---|---|---|---|
| `acoustic:pressure:horizontal-polar` / `...:vertical-polar` | `excitation, observation` | Pa (complex64) | domain `observation:horizontal-polar`/`...vertical-polar` supplies `angle_deg`, `points_m` |
| `acoustic:pressure:sphere` | `excitation, observation` | Pa | only if `spherical_sampling_enabled`; domain `observation:sphere` has `points_m, r_distance_m, theta_polar_rad, phi_azimuth_rad` |
| `acoustic:pressure:probe:<id>` | `excitation, observation` | Pa | from request `probes` |
| `acoustic:radiation-impedance` | per radiator (domain `components:radiators` with `component_id`, `name`, `effective_area_m2`, ...) | acoustic impedance | exterior only; normalised by driven area (`acoustic_impedance.py`) |
| `acoustic:pressure:bem-boundary`, `acoustic:normal-derivative:bem-boundary` | `excitation, bem_node|bem_face` | Pa, Pa/m | `retain: bem_boundary_traces`; domain `domain:bem-boundary` (`points_m`, `triangles`) |
| coupled/interior only | `electrical:voice-coil-current`, `mechanical:diaphragm-velocity`, `acoustic:interface-*`, `acoustic:pressure:fem-nodes` | | not available in exterior BEM |

Compact form: BL asks the engine for one `ui:exterior-pressure` block of shape `(excitation, observation)` and splits it by `observation_domains` offsets (`system_solve.py:442-471`). Results are **complex per excitation port** (1 m/s basis for `normal_velocity` ports); polarity/level/delay/filters are applied by the *application* afterwards (`channel_synthesis.py`) and are NOT applied in headless output. Absolute SPL = `20*log10(|p|/20e-6)` (`solve_results/derived.py:17-25`).

### 5.3 In-process `SolvedSystem` (what plugins receive) [verified, `solve_results/model.py:57-346`]
`SolvedSystem{run_id, provenance{backend_id, solve_kind, solver_options, phasor_convention, started_at_utc, engine_runs}, frequencies_hz (float64 array), excitation_ids, domains{id: ResultDomain{kind,dimensions,coordinates,topology,metadata}}, quantities{id: SolvedQuantity{quantity,unit,dimensions=("frequency",...),values,domain_id,metadata,available_frequency_mask}}, completion_mask, diagnostics_by_frequency, status, compiled_system, schema_version=1}`; helpers `.quantity(id)`, `.quantities_for(name)`, `.solved_count`, `.complete`. Derived helpers: `pressure_spl_db`, `phase_deg`, `velocity_to_excursion`, `electrical_input_impedance` (`solve_results/__init__.py`).
**GUI-solve frequency order is NOT ascending**: `prepare_system_solve` reorders log frequencies with a van-der-Corput sequence for live plotting (`system_solve.py:116-121`, `live.py:971-984`) and `SolvedSystemBuilder` keeps that order (`solve_workflow.py:636-646`). Sort by `frequencies_hz` before use [verified]. Headless overrides this with ascending log frequencies (`headless.py:315-324`).

### 5.4 Directivity, DI, beamwidth, exports
- **DI / beamwidth are not headless outputs.** Spherical DI = `-10*log10(mean(10^(SPL_rel/10)))` over the equal-area Fibonacci balloon, SPL normalised to on-axis (`ui/balloon.py:1182-1228`); `_wavefront_shape_summary` (`ui/balloon.py:~1140-1180`) fits the forward -6 dB contour as a superellipse and returns `shape_exponent, fit_residual_percent, horizontal_beamwidth_deg, vertical_beamwidth_deg, aspect_ratio, directivity_index_db` (documented in `docs/advanced/forward-beam-shape.md`). These live in a Qt-importing module (`ui/balloon.py` imports PySide6/pyvista [inferred from the `ui/` package]) - lift the maths, do not import it. Our own `di_source: "balloon"` computation from `acoustic:pressure:sphere` is straightforward and must enable `spherical_sampling_enabled` in the project.
- CEA-2034-style curves from the H/V planes: `spinorama.compute_spinorama_from_planes` (`spinorama.py:55`, pure NumPy; On Axis, Listening Window, Early Reflections, Sound Power, PIR, ERDI, SPDI/"Spherical DI").
- Exports (GUI): polar `.txt` per angle (freq, normalised dB, rel. phase; `exporting/polar.py`), on-axis `.txt` per channel (REW/VituixCAD; `exporting/on_axis.py`), balloon directory `metadata.json + topology.npz + spl_db.npy + radius_norm.npy` (`BALLOON_EXPORT_SCHEMA_VERSION = 2`, `exporting/balloon.py:18`), `.blabsp` speaker packages (versioned ZIP64, levels 1-3, `docs/Inputs and Outputs.md`), static plots.
- Impedance: exterior radiation impedance quantity (above); electrical input impedance needs a `voltage` port (coupled/interior).

---

## 6. THE PLUGIN SYSTEM ("Generator Plugins" / geometry providers)

Doc: `docs/advanced/geometry-provider-api.md` (674 lines; read in full). Introduced 2026-09-17/18 (commits `6ccce01`, `fbf81c2`); extended with assemblies/vented enclosure 2026-10-09 - i.e. **~5 weeks old at 0.5.0**. Exchange schema version `1` (`generators/base.py:18` `PROVIDER_API_VERSION = 1`).

### 6.1 Architecture in one paragraph [verified]
A provider is a local folder with a `provider.json` manifest whose Python entry points are imported *in the Boundary Lab process*. The **backend** (`create_backend(**options)` -> object with `create_session(request)` and `restore(document)`) runs inside a `QThread` generation worker (`ui/generator_worker.py:11-59`, `ui/operation_controllers.py:47-55`) - a thread, not a subprocess. The optional **editor** (`create_editor(parent, document_host)`) runs on the GUI thread and must supply a PySide6 `QWidget`. A provider *session* turns a JSON `source` dict into geometry plus an optional **configuration patch** over the physical system; the host validates and commits both transactionally. Solve submission/status/results are exposed through a Future-based `ProviderHost` facade, reachable from the editor (`document_host.services`) and optionally from the backend via `bind_host(host)`.

### 6.2 Discovery, enable/disable, trust [verified: `generators/catalog.py`, `ui/settings.py:170-186`, `ui/provider_preferences.py`]
- **Single discovery location:** `<APP_ROOT>/geometry_providers/*/provider.json` (`catalog.py:23-24`); `APP_ROOT` = repo root or env `BLAB_RESOURCE_ROOT` (`paths.py`). No per-user plugin dir, no `sys.path` hook, no entry points. Plugins must be copied into the install tree (Windows installer/restage scripts copy the folder).
- Scanning (`ProviderCatalog.scan`, `catalog.py:104-136`) only reads manifests and SHA-256-fingerprints `*.py` files (all must resolve inside the package dir); no code is imported. Reserved ids `ath`, `ath4`; duplicate ids are conflicts.
- **Enabled set** = QSettings key `providers/enabled` (GUI preference, per user/machine); newly discovered packages are *disabled*; "opening a project never enables a package"; default provider for new designs = `providers/default`. The bundled `blab.vented_enclosure` is the only allowlisted first-party id (`bundled_provider_ids`, `catalog.py:27-34`) and is auto-enabled once (`providers/vented_enclosure_introduced`, `settings.py:176-181`); "a manifest cannot claim first-party status".
- UI: **Edit > Generator Plugins...** (table with Enabled/Name/Version/Status/Folder, Rescan, Open install folder, default-provider combo). Warning text: "Enable plugins you trust: plugins execute Python inside Boundary Lab."
- **No sandbox**: "Providers are trusted in-process Python code, with the application's filesystem and process access" (`geometry-provider-api.md:348-353`). The host does not pip-install or build environments; native extensions must match BL's Python (3.13 in the Windows runtime lock, `packaging/runtime-lock.json`; 3.11+ for source installs).
- Changing a loaded package requires an app restart (`"Package changed after loading; restart Boundary Lab."`, `catalog.py:132-134`).

### 6.3 Manifest (`provider.json`) [verified: `catalog.py:37-77`, docs :316-340]
```json
{ "manifest_version": 1, "provider_api": 1,
  "id": "blab.vented_enclosure", "name": "Vented Enclosure", "version": "0.1.0",
  "source_schema_version": 1,
  "backend": "enclosure.backend:create_backend",
  "editor":  "enclosure.editor:create_editor",
  "default_source": { ...json... },
  "mesh_scale_factor": 1.0 }
```
Rules: `manifest_version`/`provider_api` must be the int `1`; `id` matches `[a-z][a-z0-9_.-]*`; `backend`/`editor` are `module:factory` (`[A-Za-z_]\w*(\.[A-Za-z_]\w*)*:[A-Za-z_]\w*`); `editor` optional; `source_schema_version` positive int, **must equal the saved design's `provider_schema_version`** else generation is disabled ("No automatic source-schema migration", doc :425-426); `default_source` JSON object copied into new designs; `mesh_scale_factor` >0 finite (units->metres; set `1.0` for metre meshes - the project default for generator docs is `0.001`).

### 6.4 Loading mechanism [verified: `catalog.py:156-179`]
First use creates a synthetic namespace module `_blab_provider_<sha256(path)[:20]>` with `__path__ = [package dir]` registered in `sys.modules`, then `importlib.import_module("<ns>.<module>")` and `getattr(name)`. Hence: **relative imports work** (`from .parameters import ...`), the package dir is *not* added to `sys.path` (so `import enclosure` fails), modules stay loaded for the process lifetime, import errors are cached as a package error until restart. Backend factory is called per generation in the worker thread with the host's `provider_options` kwargs (`ath_exe`, etc. for Ath; plugin may ignore via `**options`); editor factory on the GUI thread.

### 6.5 Exchange types (all in `blab.generators`, `generators/__init__.py`)
| Type | Fields (base.py) | Notes |
|---|---|---|
| `GenerationRequest` (:100-122) | `provider_id, document_id, mesh_name, source{}, run_root: Path, case_name, provider_options{}, schema_version=1, request_id (uuid), project_revision, configuration{}` | frozen; `source/configuration/provider_options` are deep-copied. `configuration` = `{physical_system|None, channel_config, component_channels, symmetry_config{mode}, stitching_config{enabled,tolerance_mm}}` (`configuration.py:50-63`). `physical_system` is `None` before first generation |
| `GenerationResponse` (:218-229) | `request_id` (must echo), `geometry`, `configuration_patch{}`, `schema_version=1` | return this (bare `GeneratedGeometry` is a legacy adapter; assemblies require `GenerationResponse`) |
| `GeneratedGeometry` (:125-206) | `provider_id, output_dir, mesh_path|None, radiators: tuple[RadiatorConfig], source_path, cleaned_mesh_path, reduced_cleaned_mesh_path, mirror_axes, quality_warning, provider_metadata, mesh_data: MeshData|None, reduced_mesh_data, meshes: tuple[GeneratedMesh]` | exactly one of `mesh_path`/`mesh_data` (legacy single mesh) **or** `meshes` (assembly); `reduced_mesh_data` required if `mirror_axes` + symmetry used with a memory mesh (`solver_mesh_data_for_symmetry`, :175-182) |
| `GeneratedMesh` (:40-59) | `id` (`[a-z][a-z0-9_-]*`), `purpose` (`bem_surface|fem_volume`), exactly one of `mesh_path`/`mesh_data` | host id = `<document_id>/mesh/<id>` via `generated_mesh_id`; display name `<design>__<id>` |
| `MeshData` (`mesh_data.py:36-169`) | `points (N,3)<f8`, `cells [(type, idx)]` with types `triangle, triangle6, tetra, tetra10` (meshio/VTK order, zero-based), `physical_tags[(M,)]` (positive ints), `physical_names {name: (tag, dim 2|3)}` | immutable, SHA-256 `digest`; `from_meshio`, `to_meshio`, `to_payload` (base64 packed), validated by `beat_engine.beat_contract.mesh.validate_mesh_data`. Every used tag must be named. BEM needs linear triangles |
| `RadiatorConfig` (`config.py:34-45`) | `name, tag, mesh, channel, velocity_offset_db, level_db, polarity, delay_ms, hpf, lpf, drive_group, drive_group_name` | **legacy driven-surface hint**; used only to seed an exterior system the first time (`project/migration.py:46-166`) |
| `GeneratorCapabilities`, `GeneratorDocument`, `GeneratedGeometryReference` | | project persistence types |

Validation (`complete_generation`, `base.py:232-252`): rejects non-int/unknown schema versions, mismatched `request_id` or `provider_id`, malformed patches. Host additionally rejects stale/replayed completions, changed projects/designs (`application.py:35-39`, `project_revision` content digest at `configuration.py:66-78`).

### 6.6 Patch semantics (`configuration_patch`) [verified: `generators/configuration.py`, docs :191-270]
Sections (`PATCH_SECTIONS`, :34-47): entity sections `regions, surface_assignments (-> boundaries), interfaces, component_assignments (-> components), excitation_ports` each `{ "upsert": [...], "remove": [ids] }` keyed by entity `id`; `channel_config` keyed by `name`; `component_channels` `{id, channel}`; `component_parameters {component_id: {param patch}}` (recursive merge, no key deletion); `symmetry_config {mode: off|x|xy}`; `stitching_config {enabled, tolerance_mm}`. Rules: omitted = preserved; nested dicts merge, **arrays replace**; `null` is an error (use `remove`); unknown fields rejected; new entity ids must start with `<document_id>/`; existing entities may only be modified if wholly inside the generating design's meshes; shared exterior region may be referenced but not rewritten; whole candidate is validated (references, ownership, coverage, interface conformity) and committed atomically - failure leaves project + artifact untouched (generated files are not deleted). Frequencies, backend, outputs, preferences and mesh paths are **not** patchable.

### 6.7 Two geometry modes
1. **Legacy single mesh** (e.g. an exterior waveguide): `GeneratedGeometry(mesh_path|mesh_data, radiators=(RadiatorConfig("throat", tag, mesh=request.mesh_name),), mirror_axes, reduced_mesh_data)`; the host seeds the standard exterior system (rigid/moving boundaries, `ideal_velocity_source` + `normal_velocity` port, region `region:exterior-air`) if no physical system exists (`generators/application.py:51-83`). A patch may then set `symmetry_config`. Symmetry **is supported** here (via `mirror_axes` + `reduced_mesh_data` or reduced file). The test fixture `tests/fixtures/geometry_providers/example_box/` does exactly this with an in-memory 12-triangle box.
2. **Named assembly** (`GeneratedGeometry(meshes=(...))` + full `physical_patch`): multi-mesh FEM/BEM coupled designs. **Requires project symmetry Off** (`application.py:130,211`; `resources.py:266`; `postprocess.py:337-340`); must supply complete regions/boundaries/interfaces/components/ports in the same response; compiles the candidate (`PhysicalSystemCompiler().compile`, `application.py:229`) before accepting. Persisted in schema 10 (memory meshes embedded, file meshes by relative path) and restorable **without the plugin** (`tests/test_generator_assemblies.py:120` `..._save_reopen_headless_and_preview_without_plugin`).

### 6.8 Editor / widgets (Qt) [verified: `ui/provider_editor.py`, `ui/main_window/generator_documents.py:100-190`]
Return an adapter with `widget` (a plain `QWidget`, **not** a `QDockWidget`), `apply_source(source, revision)`, `set_operation_state(state)` (`state.active/phase/message`), `dispose()`. BL owns dock placement, tabs, the Generate/Stop buttons, persistence, and widget deletion; the dock keeps the `ath_editor_dock` layout identity. The factory receives `DocumentHost`:

| Member | Semantics |
|---|---|
| `document_id`, `provider_id` | identity |
| `snapshot()` -> `SourceSnapshot(source, revision, schema_version)` | GUI thread only; revision = SHA-256 of `[epoch, doc id, schema, source]` |
| `update_source(source, expected_revision=)` | replaces whole source dict (JSON round-tripped), persisted immediately; stale -> `ProviderHostError("stale_source")` |
| `generate(expected_revision=)` -> request_id | selects the document, runs the normal Generate; raises `busy` if anything is generating/solving/preparing; **GUI thread only** (`wrong_thread` otherwise); coalesce slider events |
| `services` | scoped `ProviderHost` (6.9) |
Subscriptions are auto-removed on dispose. Failing editors degrade to a read-only JSON text view with the source preserved. Providers *without* an editor can still generate, but then cannot drive anything from code.

### 6.9 Host services: submit solves, subscribe, cancel, query results [verified: `generators/host.py`, `ui/provider_host.py`]
`ProviderHost` (all methods return `concurrent.futures.Future`; calls may originate on any thread and are marshalled to the GUI thread by `DesktopProviderHost` via a queued Qt signal):

| Method | Result | Meaning |
|---|---|---|
| `context()` | `ProviderContext(document_id, provider_id, project_revision, freq_min_hz, freq_max_hz, freq_count, schema_version)` | **Frequencies are host-owned** (from GUI `frequency_range()`); revision = SHA-256(project content + GUI preferences JSON) - changes with solver prefs/frequency settings (`ui/provider_host.py:70-79`) |
| `solve(SolveCommand(expected_revision, request_id=uuid, replace_pending=False))` | `SolveJob` (queued) | exact-revision solve through the GUI Solve path (`SolveWorkflowController.start_provider_solve`, `solve_workflow.py:123-137`); cannot override frequencies/backend/outputs/physics |
| `status(job_id)` | `SolveJob(job_id, request_id, context, state, message, solved_count, expected_count, run_id)` | states: `queued, preparing, running, cancelling` -> `completed, failed, cancelled, superseded, stale` |
| `cancel(job_id)` | `SolveJob` | own document's job; pending -> `cancelled` immediately; active -> cooperative (inline BEAT retires its worker) |
| `result(job_id)` | `SolvedSystem` (deep copy) | after terminal state; complete or partial; errors `not_ready`, `result_unavailable` |
| `current_result()` | `SolvedSystem` | host's latest finalised snapshot (includes manual GUI solves); not guaranteed to match edited geometry |
| `subscribe(cb)` / `unsubscribe(id)` | token / None | events `ProviderEvent(kind="geometry_accepted"|"solve_status", job, context, generation_request_id)`; callbacks run on the GUI dispatch thread; <=64 subscriptions per document binding |
Errors: `ProviderHostError.code` in `busy, stale_revision, request_conflict, invalid_context, unknown_job, not_ready, result_unavailable, subscription_limit, closed, unknown_command` plus `wrong_thread, stale_source, generation_failed` from `DocumentHost`.
Scheduling (`ProviderService`, `host.py:119-339`): one active solve + one pending slot; `replace_pending=True` supersedes only the same owner's pending request; pending waits for generation/preview preparation/active solve to settle then re-checks revision (stale => `stale`); retains **4 result snapshots, 32 job records**; identical retry returns the same job; same `request_id` with different content => `request_conflict`. A solve requires an *accepted* solve-ready physical system; exterior-topology warnings **fail the job** instead of showing the confirm dialog (docs :576-578).
Backends get `ProviderHost` through optional `bind_host(host)` before `create_session` (`generator_worker.py:29-30`); but a backend cannot solve its own just-generated geometry inside `generate()` (acceptance happens after it returns). The loop must therefore be driven from the **editor** (GUI thread): `generate` -> wait `geometry_accepted` (context has the new solve revision) -> `solve` -> watch `solve_status` -> `result(job_id)` -> compute objective -> `update_source` -> repeat. All of `generate/update_source/snapshot` are GUI-thread-only, so an optimiser thread must hop to the GUI thread (signals/QTimer) for each candidate [inferred from `DocumentHost._document`, `provider_editor.py:217-225`]. There is **no host-driven generation API** and no live numerical arrays; docs say so (`:661-663`, which also stale-ly list "custom provider widgets" as missing though they exist).
Test coverage of the end-to-end path is mostly with stubbed `start`/`busy` (`tests/test_ui_provider_host.py`, `tests/test_provider_host.py`, `tests/test_solve_workflow_controller.py:744`); the doc advertises a CPU smoke solve only for the vented enclosure (`geometry_providers/vented_enclosure/README.md`) [verified].

### 6.10 Worked example: bundled `geometry_providers/vented_enclosure/`
Files: `provider.json` (id `blab.vented_enclosure`, `mesh_scale_factor: 1.0`, 17-field `default_source` in metres), `enclosure/backend.py` (175 lines), `parameters.py` (112; pure-Python SI geometry + validation, no Qt/gmsh), `worker.py` (229; isolated Gmsh/OpenCASCADE), `editor.py` (199; Qt sliders + sketch).
- `create_backend(**options)` -> `EnclosureBackend`; `restore()` returns `None` ("host restores cached assembly resources without executing plugins").
- `EnclosureSession.generate` (`backend.py:102-163`): validate source (`validate`, exact key set `==DEFAULTS`); require `symmetry_config.mode == "off"`; create **fresh** `run_root/vented_enclosure_<uuid>` dir (never overwrite accepted files); write `source.json`; spawn `[sys.executable, "-I", "-B", "-X", "utf8", worker.py, source.json]` with `CREATE_NO_WINDOW` (Gmsh is kept out of the app process); poll every 0.1 s honouring `stop_requested`/`stop()` (terminate+reap child); read `mesh_info.json`; return `GenerationResponse(request_id, GeneratedGeometry(provider_id, output, None, (), source_path=source, meshes=(GeneratedMesh("interior","fem_volume", mesh_path=interior.msh), GeneratedMesh("exterior","bem_surface", mesh_path=exterior.msh)), provider_metadata=metadata), configuration_patch(request))`. Outputs: Gmsh 4.1 ASCII FEM, Gmsh 2.2 ASCII BEM, BREP, log.
- `configuration_patch` (`backend.py:16-84`): ids prefixed `request.document_id + "/"`; adds `<doc>/interior` (`bounded_air`, volume group `air`) and `<doc>/exterior` (`unbounded_air`) **only if absent, joining an existing exterior region's id found in `request.configuration["physical_system"]`**; boundaries `{inside,outside}/{inner_wall|outer_wall: rigid, driver: moving, port_mouth: interface}`; one `interface` (port mouth); component `<doc>/driver` (`electrodynamic_transducer`, `DRIVER_DEFAULTS` Re 5.8, Le 0.5 mH, Bl 8, Mmd 35 g, Cms 0.4 mm/N, Rms 1.5, `rigid_translation` axis +Z) only on first creation (user edits preserved on regeneration); port `<doc>/voltage` (`voltage`); `component_channels` route to `main` if unrouted. Physical-group *names* (`driver`, `port_mouth`, `inner_wall`, `outer_wall`, `air`) are the contract between the mesher and the patch.
- Editor: Qt sliders + numeric inputs, front/profile sketch painted without meshing; BL's Generate button triggers `generate`. It does **not** use `services.solve` (the minimal editor in `tests/fixtures/geometry_providers/example_box/box/editor.py` shows `host.services.subscribe(self.event)`).
- Limits visible here: symmetry Off only; one plugin generation at a time; cancellation works by terminating the subprocess.

### 6.11 Limits and caveats (collected) [verified unless marked]
- Assemblies: symmetry Off only; removing/disabling a design requires resolving cross-design dependencies; no automatic symmetry reduction of coupled interface meshes.
- Preview and solve preparation are **serialized**; one active + one pending provider solve; `busy` rejections (no queue for interactive generation); shared-memory transport and concurrent preparation are "future work"; "No reduced solve latency is claimed" (doc :53-55).
- Memory-mesh transport = base64 inside JSON (no shared memory); remote server and legacy simulation transports reject memory meshes; exact Level-3 speaker export needs file assets.
- Providers see/read-only detached request copies; cannot change host frequency range, count, backend, outputs; project preferences (e.g. `spherical_sampling_enabled` for DI) are *not* patchable - the user must set them in the GUI.
- GUI-driven solve clears plots/locks inputs per candidate (`solve_workflow.py` `_begin_run`), and every `update_source` marks the project dirty; per-candidate GUI overhead is not benchmarked in the repo [inferred].
- Generation workers are threads: Gmsh's Python API is process-global/non-reentrant; Ath path serialises with `ATH_GMSH_LOCK` and a subprocess (`ath.py:44`, `ath_gmsh_worker`), the vented plugin uses a subprocess. A mesher that calls gmsh in-thread must do likewise [inferred].
- No hot reload; trust is all-or-nothing; no signing; enabled list is per-machine QSettings.

---

## 7. Ath integration

- **Ath is an external Windows executable** bundled in-repo: `ath/ath202608.exe` (868 KB; README: "Ath is bundled with permission from Marcel Batik"; `docs/macos-ath-setup.md:15-17` says it is "free for non-commercial use" and BL's GPLv3 "does not grant additional rights to Ath"). On macOS/Linux it runs through Wine (`ath.py:136-148`, `ath_setup.py`, QSettings keys `macos/ath_executable`, `macos/wine_executable`).
- Flow (`src/blab/ath.py`, `generators/ath.py`): `AthGeneratorBackend.create_session(request)` writes the user's `.cfg` text (`request.source["text"]`, source format `ath_cfg`, `generators/ath.py:29-31`) to `run_root/<case>/<case>.cfg`, runs `ath.exe <cfg> -b` ("blab mode": Gmsh `.geo` on stdout, diagnostics on stderr; `ath.py:136-146, 173-230`), then spawns `python -B -X utf8 -m blab.ath_gmsh_worker ...` to mesh the `.geo` to `.msh`, clean it (`clean_mesh`, merge/area tolerances) and write the **expanded** `<case>.msh` and (if symmetry) `<case>_reduced.msh` in Gmsh 2.2 ASCII (`build_ath_mesh_artifacts`, `ath.py:550-612`).
- **Only one parameter is interpreted by BL: `Mesh.Quadrants`** (`ATH_QUADRANTS_RE`, `ath_mirror_axes_from_config_text`, `ath.py:100-133`): `1` -> mirror axes `("x","y")` (XY quarter), `14` -> `("x",)`, `1234`/absent -> none, `12` (Y-only) -> error ("Boundary Lab does not support Y-only symmetry"), multiple assignments -> error. This is the "Quadrants vs symmetry flag" coupling: `mirror_axes` decides which mesh variant the *project's* separate `symmetry` setting selects (`GeneratedGeometry.solver_mesh_path_for_symmetry`, `base.py:188-191`; `headless.py:151-155`).
- Physical surfaces Ath must emit: driven diaphragm **`SD1D1001`** (required, `ath.py:34 DRIVEN_DIAPHRAGM_PHYSICAL_NAME`), optional complex-source triple `SD1D1003` (dome, 0 dB), `SD1D1002` (inner surround, -2.5 dB), `SD1D1001` (outer surround, -12 dB), or `//#// DRV` footer records (`internal_id user_id name ref_elements weight_absolute weight_db driving_direction`, `parse_ath_drive_definitions`) -> `RadiatorConfig` with `drive_group="ath:<id>"` and `velocity_offset_db=weight_db` (`_radiators_from_physical_names`, `ath.py:508-547`). Example config also shows `SD1G0` as the undriven throat-plate group (`source_config_by_name`).
- **Ath cfg keys seen in BL's shipped examples** (counted over `examples/**/*.blab.json`; BL itself does not define or validate any of them): `Throat.Profile` (`1 = OS-SE waveguide` per example comment), `Throat.Diameter` [mm], `Throat.Angle`, `Length`, `Coverage.Angle` (may be an expression like `36 + 17*cos(p)^2`, `tests/test_ui_ath_editor.py:76`), `Term.s`, `Term.q`, `Term.n`, `OS.k`, `Slot.Length`, `GCurve.Type/Width/Dist/SF/Rot/AspectRatio` (superformula), `Morph.TargetWidth/TargetHeight/TargetShape/FixedPart/Rate/CornerRadius/AllowShrinkage`, `Mesh.AngularSegments/LengthSegments/CornerSegments/ThroatResolution/MouthResolution/InterfaceResolution/InterfaceOffset/Quadrants/SubdomainSlices/Enclosure{Spacing,Depth,EdgeRadius,EdgeType,FrontResolution,BackResolution}/RearShape/Roundover`, `Output.STL/ABECProject`, `ABEC.SimType`, `GridExport:*`, `Source.Contours/Velocity`, `DrivingWeight`, `LFSource.B`, `SID`. No R-OSSE keys appear in the repo's examples or tests; the Ath binary's strings include `R-OSSE.PrintApex`, `Rollback`, `Throat.Ext.*` [verified via `strings`]; the R-OSSE parameter vocabulary (R, a0, r0, k, b, m, q, ...) is therefore **not documented by BL** and would have to be taken from Ath's own manual [inferred: `Throat.Profile = 3` selecting R-OSSE is from my knowledge of Ath, not from this repo].
- Implication for hornlab-search: BL treats Ath cfg text as an opaque blob in `generator_documents[].source.text`; emitting Ath-syntax OSSE configs would make BL run *Ath's* mesher (different from `hornlab_mesher`), is Windows/Wine only, and carries Ath's non-commercial terms. A geometry-provider plugin or a pre-meshed `.msh` + `physical_system` are the routes that use `hornlab_mesher` output.
- Ath is `provider_id: "ath"`, reserved; editor = `AthScriptEditor` with syntax highlighting (`ui/ath_syntax.py`).

---

## 8. What changed 0.4.4 -> 0.5.0 (integrator view)

`docs/releases/0.4.4.md`: maintenance release (updater only); BEAT stays **0.1.4**. `docs/releases/0.5.0.md` + `git diff v0.4.4 v0.5.0 --stat` (307 files; `deploy/` app removed to a separate repo [Boundary Lab Deploy]; ~171k insertions / ~484k deletions mostly deploy assets):

| Change | Integrator impact |
|---|---|
| **BEAT pin 0.1.4 -> 0.6.0** (`pyproject.toml:13`, wheel SHA-256 `10db2ee28eb9a8675fa0131127a04eeaad61097328c3aac453721a5924187dd3`, mirrored in `packaging/runtime-lock.json` "beat_requirement"); hard runtime check `engine_distribution.py:9-11` | Results change: "projected FEM-BEM interface correction changes numerical results and rejects rank-deficient or poorly conditioned interface triangulations"; "Worker and result schema versions remain unchanged" (0.5.0.md). Exterior-only solves unaffected by the interface fix [inferred] |
| Geometry-provider plugin API + assemblies + vented-enclosure plugin | Section 6. Project schema 9 -> 10 |
| In-memory meshes (`mesh_data.py` new, `mesh_cache.py`, `headless.py` +73) | Headless/project files can carry `MeshData` (base64) in `physical_system.meshes[].mesh_data` or `generator_documents[].artifact.mesh_data`; no mesh file needed; inline transport requires BEAT >= 0.6 (earlier workers reject) |
| Axial prescribed sources (`source_motion.py` new): `motion_profile: "rigid_translation"` + `motion_axis` for exterior ideal sources; compiled-system contract_version 2 when used | Relevant to piston drivers in waveguide models; must lie in symmetry planes |
| Near-coincident-vertex detection/repair (`mesh_quality.py`) | GUI only |
| Interface radiation per interface, `retain: interface_radiated_pressure`, interface geometry diagnostics | Coupled only |
| Thermoviscous wall loss option, driver text import/export | FEM/GUI |
| macOS Apple Silicon (Metal) installer; Windows CPU/CUDA standalone installer tooling; Windows consoles suppressed for subprocesses | Metal backend now first-class in docs (`0.5.0-metal-qualification.md`) |
| `HEADLESS_*`: `resolve_headless_backend` honours `BLAB_PACKAGED_BACKENDS`; `retain` gains `interface_radiated_pressure` | additive |
| Known limitation (release notes): Vented_Sub 50 Hz voice-coil current differs 0.134% CPU vs CUDA (> 0.1% screen); CUDA 0.145% vs FP64 reference. "Use CPU when low-current accuracy matters" | coupled/electrical, not exterior pressure |
| Release status: "Boundary Lab release preparation remains in progress ... exact main-commit CI and final installer qualification remain publication gates" (end of 0.5.0.md) | 0.5.0 tag exists but notes read as pre-publication |

CLI surface in `project_cli.py` between tags: only `export-speaker` gained `--viewport-model/--viewport-model-scale`; `validate/solve` arguments unchanged [verified via `git diff`]. Request overlay schema (v1) and result manifest (v2) unchanged.

---

## 9. Licensing

- **Boundary Lab: GNU GPL v3** - `LICENSE` is the verbatim GPLv3 text ("Version 3, 29 June 2007"); no "or later" statement, no SPDX headers (`grep SPDX` empty), no `license` field in `pyproject.toml`, README/AGENTS.md contain no additional terms. Treat as GPL-3.0 (possibly "-only"; unstated) [verified/inferred]. `packaging/windows.iss:30` ships the LICENSE.
- **Plugin API: no separate license, no exception clause, no plugin-specific terms** anywhere (greps for license/GPL/AGPL/copyright over md/toml/json/iss/txt: only the Ath note and installer LicenseFile) [verified]. The API is just part of the GPLv3 `blab` package; a plugin that does `from blab.generators import ...` is in-process, dynamically-linked use of a GPLv3 library, i.e. a combined work.
- **Can an AGPL-3.0-or-later plugin be loaded? Technically yes and, legally, GPLv3 section 13 / AGPLv3 section 13 expressly allow combining the two** (`LICENSE:550-557` "Use with the GNU Affero General Public License": you may link or combine a GPLv3 work with an AGPLv3 work into a single combined work; GPL terms apply to the GPL part, AGPL section 13 network clause to the AGPL part). The plugin folder is distributed separately from BL, and BL does not verify licenses. An AGPL-3.0-or-later hornlab-search is therefore compatible with a GPLv3 host in the plugin case [inferred; not legal advice]. Two caveats: (1) if the plugin links `hornlab_*` packages they must also be GPL/AGPL-compatible - their licences are not visible here; (2) if BL is "GPLv3-only" and hornlab-search is "AGPLv3-or-later", the combination is still permitted via section 13, but you cannot relicense BL's code.
- Using the CLI/server (separate processes, files and HTTP) creates no combination at all.
- Third-party: **Ath** is bundled "with permission" and is free for non-commercial use only (`docs/macos-ath-setup.md`); BEAT Engine licence is not in this repo (separate repo `JWSound/BEAT_Engine`) - check before redistributing BEAT wheels with hornlab-search.

---

## 10. Integration surfaces ranked (for an external optimiser such as hornlab-search)

Ranking = suitability for *batch objective search* (many candidates, GPU, scored on beamwidth/DI/ripple) combined with stability signals.

### Rank 1 - Project-file export + headless CLI (`blab project validate|solve`)
- **What it gives:** a fully scripted, GUI-free exterior-BEM solve of *our* `hornlab_mesher` geometry (metre `.msh`, `scale_to_m = 1.0`) with H/V polar planes, optional Fibonacci sphere (for balloon DI), arbitrary probes, retained BEM traces, radiation impedance; per-excitation complex pressure; provenance (engine hash, device, mesh SHA-256); resumable-readable partial runs; same project opens in the BL GUI for human inspection (a "winner export").
- **Maturity signals:** headless since 2026-08-13; documented in `cli-workflow.md` and recommended first in `AGENTS.md` ("Use the headless project workflow for automated diagnosis"); explicit versions: project schema 10, request v1, result manifest v2, BEAT contract request v1/system v1/result v2; CI runs an installed-engine validate+solve smoke on every PR (`scripts/check_engine_integration.py`, `ci.yml`); `tests/fixtures/remote-exterior.blab.json` is a stable minimal example. Version policy: 0.x, "document any breaking change explicitly".
- **Risks / work:** (a) we must author `physical_system` ourselves (group names <-> tag coverage rules, section 2.4) and keep it consistent with `symmetry`; (b) one process + cold Julia startup per solve unless we drive `blab.headless` in-process (below); (c) worker shutdown behaviour of `blab project solve` is unverified (no explicit `shutdown_beat_engine_workers`) - must be tested against the hornlab GPU-hygiene rules; (d) no DI/beamwidth/ripple postprocessing - we compute from complex pressure (sphere/planes); (e) FP32 only, frequencies float32/ints from preferences unless `--request` is used; (f) no watertightness/near-coincident-vertex checks headless; (g) beat-engine exactly 0.6.0 in that environment; (h) exit codes coarse (0/1/2/130); (i) `validate --backend beat_auto` probes CUDA via Julia; (j) legacy Ath-only projects not solvable; (k) docs partly stale (schema 8 in examples, BEAT 0.1.2/0.4.0 mentions).

### Rank 2 - In-process Python library (Qt-free `blab.headless` / `blab.system_solve` / `PhysicalSystemProductionBackend`)
- **What it gives:** the same pipeline without file/Julia-startup overhead per call: `load_headless_project`, `prepare_headless_solve`, `run_headless_solve(..., backend=...)` or `backend.create_system_session(request).solve_stream()` yielding `SystemFrequencyResult` objects; warm persistent worker across candidates (`persistent_worker=True` default; GUI "cuda_worker_reuse" idle-cleanup policy is GUI-side only); in-memory `MeshData` meshes (no `.msh` write) via inline transport; `SolvedSystemBuilder` for stacked arrays.
- **Maturity:** not a documented public API ("Keep reusable solve preparation free of Qt; the GUI and CLI should call the same core contracts", `AGENTS.md`); no stability promise, 0.x; function signatures changed in 0.5.0 (e.g. `prepare_system_solve(..., cuda_worker_reuse=...)`).
- **Risks:** pins the whole Python env to `beat-engine==0.6.0` and brings gmsh/meshio/matplotlib/scipy; must manage Julia host lifetime ourselves (BL's rule set differs from `HORNLAB_BEAT_PERSISTENT_HOST` hygiene) [inferred]; shape of `PreparedSystemSolve`/`HeadlessSolveSpec` may churn.

### Rank 3 - Results reading (run directory / `SolvedSystem` / canonical quantity ids)
- **What it gives:** a stable, self-describing on-disk format: `manifest.json` (schema `boundary-lab-headless-result` v2) + per-frequency JSON/NPZ + domains; quantity ids (`acoustic:pressure:horizontal-polar`, `...:vertical-polar`, `...:sphere`, `...:probe:<id>`, `acoustic:radiation-impedance`) and coordinate conventions (+Z forward; H = XZ, V = YZ; phasor `exp(+i omega t)`; complex64 Pa per excitation).
- **Risks:** no official loader; GUI-order frequencies are non-monotonic (van der Corput) in `SolvedSystem` from GUI/plugin solves; DI/beamwidth code is inside the Qt `ui/balloon.py` module (re-implement); `.blabsp` and balloon exports are visualisation-oriented, not needed.

### Rank 4 - Server API (`blab server`, `/v1/capabilities|jobs`)
- **What it gives:** remote/containerised GPU offload (Docker `cpu`/`cuda` targets), with the server owning the Julia workers and cleaning them at shutdown (`server.py:386-393`) - a possible way to isolate GPU lifecycle from the optimiser; journals + cursor polling; capability/backend discovery; bearer auth.
- **Maturity:** explicitly "development preview, not a public HTTP service deployment"; wire version 2; exact-version negotiation (older clients rejected); **one job at a time, 409 when busy, no queue**, no retention cleanup, shared token = shared jobs, plain HTTP, 256 MiB bundle cap, remote observation planes and memory meshes unsupported, only allow-listed solver options.
- **Risks:** payload is the *compiled* BEAT request with absolute-path-free hashed `.msh` assets - clients without BL must hand-build compiled systems (feasible for exterior-only) or use BL's `blab project solve --server-url`; per-candidate upload overhead; serial throughput identical to local single GPU.

### Rank 5 - Geometry-provider plugin (in-process, GUI-hosted)
- **What it gives:** native appearance of `hornlab_mesher` designs inside the BL GUI: custom Qt editor, Generate/Stop, in-memory `MeshData` (no files), transactional physical-system seeding via `radiators` hint or patch, symmetry via `mirror_axes`+`reduced_mesh_data` (single-mesh mode), host-side solve queue (`ProviderHost.solve/status/result/subscribe/cancel`) with correlated `SolvedSystem` results, project persistence without the plugin installed. Good for an *interactive* "tweak a horn, press Generate, press Solve" front end or for pushing an optimiser-found winner into BL.
- **Maturity:** ~5 weeks old; exchange schema v1 with multiple explicit "future work" notes (shared-memory transport, concurrent preparation, host-driven generation, per-pair stitching policies, cross-provider interface composition API, hot reload, symmetric assemblies); end-to-end provider-solve path only partially tested (stubs); docs internally inconsistent (custom widgets "not yet" vs implemented).
- **Risks for batch optimisation (the dominant ones):** requires a running desktop GUI session (PySide6) and an editor widget to drive loops; `generate()`/`update_source()` are GUI-thread-only; everything is serialized through one project/preview/solve pipeline with per-candidate plot reset and preview refresh; frequencies and sphere sampling (DI) are host/user-owned and not patchable; 4-result/32-job retention; install only into `<APP_ROOT>/geometry_providers`; user must enable it; no sandbox (the plugin has full process access); generation runs in a Qt worker thread (gmsh needs a subprocess); source-schema changes are unmigrated; the PySide6/BL version couples the plugin to BL internals (`blab.*` imports). **Not recommended as the optimisation driver; reasonable as an optional viewer/handoff.**

### Rank 6 - Ath cfg route (`generator_documents` with `provider_id: "ath"`)
- Emits OSSE-like geometry through Ath's own mesher: Windows exe (Wine elsewhere), non-commercial licence, no control from Python beyond the cfg text, only `Mesh.Quadrants` interpreted by BL. Low relevance since hornlab already owns the mesher; useful only as a cross-check generator.

### Cross-cutting facts to build on
1. Minimal exterior project = `tests/fixtures/remote-exterior.blab.json` pattern (one `bem_surface` mesh, one `unbounded_air` region, rigid+moving boundaries covering *all* surface groups, one `ideal_velocity_source` + `normal_velocity` port, `symmetry`, `scale_to_m=1.0`).
2. Units/axes: metres, +Z forward, `exp(+i omega t)`, outward normals, reduced mesh in positive-X/(Y) domain for symmetry, ideal source basis 1 m/s.
3. Must-test before adoption: Julia process exit after `blab project solve`; GPU VRAM baseline/peak per hornlab rule; CPU vs hornlab_beat_bem agreement on a reference horn at equal mesh (BL is FP32 only; hornlab path may differ); behaviour with `symmetry: xy` and an OSSE quarter mesh; whether BL's exterior sphere/plane pressures reproduce hornlab's balloon DI within tolerance.
4. Docs-vs-code discrepancies to remember: `Inputs and Outputs.md` schema 8; BEAT version mentions 0.1.2/0.4.0 vs pin 0.6.0; "validate does not launch Julia" vs auto-backend probe; provider doc "custom provider widgets not yet" vs implemented editors.
