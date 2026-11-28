# Boundary Lab 0.5.0: research findings for hornlab-search

Date 2026-10-21. Senior architecture research, read-only. Boundary Lab (BL) `JWSound/boundary-lab` tag `v0.5.0`
(commit `6c9185b`, released 2026-10-20); BEAT Engine `JWSound/BEAT_Engine` `v0.6.0` (`1bb46da`); our pins
`hornlab-beat-bem` `38544d2`, `hornlab-waveguide-mesher` `b922e807a5`. Nothing from BL was installed or executed.
Detailed, cited inventories: `docs/research/boundary_lab_0.5/bl_inventory.md` (BL itself) and
`docs/research/boundary_lab_0.5/beat_compat.md` (engine, mesh, Ath, licences). Labels: **[verified]** read in source,
**[inferred]** reasoned, **[unverified]** needs a run.

Companion: `docs/BOUNDARY_LAB_INTEGRATION_PLAN.md` (what to build).

## The short version

1. **BL 0.5.0 adds Generator Plugins** (geometry-provider API, exchange schema 1): a folder with `provider.json` in
   `<BL>/geometry_providers/` that generates meshes inside the app, and a host service API (`ProviderHost`) that lets
   a plugin queue solves, watch status and read results. The docs explicitly anticipate optimizers ("use
   `result(job_id)` to correlate an optimizer evaluation"). [verified]
2. **BL now has a headless solve**: `blab project validate|solve PROJECT [--request overlay.json] [--backend ...]
   [--events ndjson]`, writing a documented run directory. This **corrects** our frozen plan
   (`docs/plan/12_RESEARCH_BASIS.md` section 1, `docs/plan/README.md` row 3), which said `blab project solve` was not
   BL's CLI; that was true for the BL version reviewed then and is no longer true. [verified `src/blab/project_cli.py:66`]
3. **Our mesher's output is already BL-shaped**: MSH 2.2 ASCII triangles with Ath physical names (`SD1G0` rigid wall,
   `SD1D1001` driven surface); BL treats `SD1D1001` as the driven diaphragm. [verified]
4. **The engine underneath has drifted**: `hornlab-beat-bem` vendors a patched pre-extraction copy of BL's engine
   (about 2026-10-01 to -07), not a BEAT release. BL pins BEAT 0.6.0 and **hard-fails on any other version**. [verified]
5. Therefore the cheap, high-value integration is **interchange, not embedding**: export our designs as solve-ready
   BL projects, cross-check our solver against BL's headless BEAT 0.6.0, and ship a geometry provider so BL users
   can open hornlab designs. Running the CMA-ES search inside BL's GUI is possible but is the wrong first step.

## 0. Spot checks done by the orchestrator (on top of the two appendices)

| Claim | Evidence | Status |
|---|---|---|
| 0.5.0 released 2026-10-20 | tag `v0.5.0`, commit `6c9185b 2026-10-20`, `pyproject.toml` version 0.5.0 | verified |
| `blab project solve` exists | `src/blab/project_cli.py:66` | verified |
| BL refuses any BEAT except 0.6.0 | `src/blab/solvers/engine_distribution.py:8-9` | verified |
| BL CLI/headless never shut down the Julia worker | no `shutdown_beat_engine_workers` in `cli.py`, `project_cli.py`, `headless.py`, `system_solve.py` | verified (by absence) |
| DI/beamwidth only in a Qt module | `src/blab/ui/balloon.py` imports `matplotlib.backends.backend_qtagg` at top | verified |
| BL phasor `exp(+i omega t)`; vendored engine in hornlab-beat-bem `exp(-i omega t)` | `docs/advanced/Phasor Convention.md:3`; HB `config.py:326`, `julia/BeatEngineDriver.jl:499` | verified |
| BL driven-surface name `SD1D1001` | `src/blab/ath.py:29` | verified |
| Example plugin runs gmsh in an isolated subprocess | `geometry_providers/vented_enclosure/enclosure/backend.py:120-124` (`sys.executable -I -B`) | verified |
| Generator documents default `mesh_scale_factor` 0.001 (mm) | `src/blab/generators/base.py:95` | verified |

## 1. What BL 0.5.0 exposes (ranked by usefulness to us)

| Surface | What it gives | Maturity signals | Fit for hornlab-search |
|---|---|---|---|
| **Project file `.blab.json`** (schema 10, physical model v1) | A solve-ready exterior BEM model: mesh resource (`scale_to_m`), one `unbounded_air` region, `rigid`/`moving` boundaries, `ideal_velocity_source` + `normal_velocity` port, `symmetry` `off/x/xy` | Versioned; loader accepts 1..10; 9->10 additive; minimal template `tests/fixtures/remote-exterior.blab.json` | **High**: writing JSON needs no BL dependency; users open our designs in the GUI |
| **Headless CLI** `blab project validate/solve` | Same compile path as the GUI; overlay sets exact `frequencies_hz`, probes, retention; `--events ndjson`; run dir `manifest.json` v2 + per-frequency JSON/NPZ (complex64 Pa) | Exit codes 0/1/2/130; `--output` must not exist; skips GUI mesh repair; **no worker shutdown** | **High** for a cross-check solver and comparability; low for the inner search loop (per-call startup, unmeasured) |
| **Generator plugin** (provider API 1) | Our geometry inside the BL GUI; in-memory `MeshData` or file meshes; single-mesh mode supports `mirror_axes` + reduced mesh | API about 5 weeks old; several "future work" notes; plugins are trusted in-process code, disabled until enabled | **Medium-high** as a hand-off/viewer: BL users generate hornlab designs natively |
| **Host services** (`ProviderHost`: context, solve, status, cancel, result, current_result, subscribe) | Plugin can queue solves and read `SolvedSystem` | GUI only; frequencies, backend, physics host-owned; 1 active + 1 pending job; 4 results / 32 jobs retained; `generate()` GUI-thread only, no host-driven generation | **Low** for batch search; possible later for an interactive "refine in BL" mode |
| **Server** `blab server` (HTTP, bearer token, ZIP of compiled request) | Remote solve, `/v1/capabilities`, `/v1/jobs` | "development preview"; one job, 409 when busy, no queue/retention; no memory meshes | **Low** now; interesting for a cloud GPU later (`docs/CLOUD_GPU_REPORT.md`) |
| **In-process `blab.headless` library** | Warm worker without CLI startup | Not a documented public API | Avoid (unstable) |
| **Ath route** | BL drives a bundled proprietary Ath exe | Opaque cfg text; non-commercial licence; Wine off-Windows | **Low**: OSSE-only translation, no mesher->Ath exporter exists |

## 2. Physics and convention alignment (what must match for results to be comparable)

| Topic | hornlab-search today | BL 0.5.0 / BEAT 0.6.0 | Consequence |
|---|---|---|---|
| Units | mesher writes metres; `mesh_scale=1.0` (silent killer 1) | resource `scale_to_m` (1.0 for metres); generator documents default **0.001** | Every export must set 1.0 explicitly and a test must prove it (bbox check) |
| Symmetry | `quadrants` `1/14/1234` (`12` rejected), single source `mesh/sizing.py::SYMMETRY_PLANE` | project `symmetry` `xy/x/off`; reduced mesh must lie in +X(+Y); Ath `Quadrants 1->xy, 14->x, 1234->off, 12` rejected | Map from `sizing.SYMMETRY_PLANE` only; test pairing (silent killer 2) |
| Tags | `SD1G0`=1 rigid, `SD1D1001`=2 source (`mesh/build.py:40`); `SD2G0`=3 possible | every surface group needs exactly one boundary role; groups resolve by name and/or tag | Exporter assigns roles from the mesh's own `$PhysicalNames`; unknown groups refuse export |
| Excitation | unit normal **acceleration** on tag 2 (Collin Q #10) | `normal_velocity` port, **1 m/s** basis | Normalized metrics (beamwidth, DI, ripple, normalized polars) compare directly; absolute level differs by 20 log10(omega) and phase by 90 deg. Convert, do not compare raw |
| Time convention | `exp(-i omega t)` (vendored engine) | `exp(+i omega t)` | Magnitudes unaffected; conjugate before comparing phase, group delay or impedance |
| Precision | per hornlab-beat-bem config | BL solves float32 / complex64 outputs | Expect float32-level differences; still far below our 0.039 dB noise floor [inferred, to measure] |
| Observation | H/V arcs 73 angles at 2 m; theta-phi balloon with sin(theta) weights | H/V polar step `polar_angle_step_deg` (default 10) at 2 m, +Z forward, H in XZ, V in YZ; optional equal-area Fibonacci sphere (`spherical_sampling_enabled`, default off) | Exporter sets 2 m, a step matching our grid, and enables the sphere; DI computed by **our** code from BL's sphere |
| DI / beamwidth | `metrics/` (`di_source` "balloon") | not a headless output; GUI-only maths in `ui/balloon.py` | We compute both ourselves from BL pressures; never import BL UI code |
| Frequencies | frozen screen grid, log, band-capped | prefs parsed as **ints**; GUI order van-der-Corput; headless ascending; overlay `frequencies_hz` exact | Always pass `frequencies_hz` in the overlay; sort by frequency when reading |
| Formulation | Burton-Miller, GMRES tol 1e-5 | same formulation and router; BEAT 0.6.0 CUDA exterior uses a **direct-system** assembler (one N x N, in-place LU) | BL may fit larger meshes on the 8 GB card than our four-operator path [inferred]; relevant to `docs/HIGH_FREQUENCY_OPTIONS.md` |
| 0.6.0 numerics change | n/a | projected FEM-BEM **interface** correction | Coupled-only; exterior BEM-only results unaffected [verified, `beat_compat.md` A.5] |

## 3. Engine and dependency situation

- `hornlab-beat-bem` 38544d2 vendors a locally patched BL engine (fork commit `3ea846e`, 2026-10-01) plus ported BEAT
  PRs #17/#19/#20/#23; it has no BEAT version and no `beat-engine` dependency. It speaks the legacy "source request"
  (schema 2) that BEAT keeps but calls "not the public contract". BEAT 0.6.0's public contract is the compiled-system
  JSON over worker protocol v1. Five HornLab-only request keys (`source_motion`, `solve_precision`,
  `surface_traces_enabled`, `spherical_grid`, `diagonal_enabled`) do not exist in stock BEAT. [verified]
- BL hard-requires `beat_engine == 0.6.0` at import. **Installing BL into our venv would pin the engine for the whole
  environment.** BL must live in its own environment and be called as a subprocess. [verified]
- Neither BL's CLI nor its headless path shuts down the persistent Julia worker. Our GPU-hygiene rules (CLAUDE.md
  rules 1, 2, 6) therefore apply to every BL call we make: clear before, verify after. [verified by absence; runtime
  behaviour unverified]

## 4. The plugin system, in the detail that drives the design

- Discovery: only `<BL app root>/geometry_providers/<pkg>/provider.json`; fingerprinted without import; disabled until
  the user enables it; only the bundled vented enclosure is auto-enabled. [verified]
- Manifest: `manifest_version 1`, `provider_api 1`, `id` (lowercase, unique, not `ath`), `name`, `version`,
  `source_schema_version`, `backend` (`module:factory`), optional `editor`, `default_source`, `mesh_scale_factor`
  (units to metres, default 1.0). [verified]
- Loading: trusted in-process Python in a private module namespace (relative imports only, no `sys.path` changes). The
  host does not pip-install anything; binary extensions must match BL's Python. Backends run in generation workers;
  editors are PySide6 widgets on the GUI thread. [verified]
- Exchange: `GenerationRequest` (request_id, provider_id, document_id, source, project_revision, configuration
  snapshot, run_root) -> session `generate()` -> `GenerationResponse(request_id, geometry, configuration_patch)`.
  `GeneratedGeometry` is single-mesh (file or `MeshData`, optional `mirror_axes` + `reduced_mesh_data` or
  `reduced_cleaned_mesh_path`, radiator hints) or a named assembly (symmetry must be Off). Patches can set boundaries,
  components, ports, channels, symmetry, stitching; never frequencies, backend or mesh paths. [verified]
- The bundled vented-enclosure provider (about 700 lines) launches gmsh in an isolated subprocess
  (`sys.executable -I -B worker.py`) and returns file meshes. That is the pattern for us, with one change: our worker
  must run **our** venv's interpreter, because BL's Python does not have `hornlab_mesher`. [verified pattern;
  interpreter choice is our design]

## 5. Licences (not legal advice)

BL and BEAT: GPL-3.0 text, no "or later" grant found. hornlab-search, hornlab_mesher: AGPL-3.0-or-later.
hornlab-beat-bem labels itself GPL-3.0-or-later, which is broader than the visible upstream grant (a question for its
author). A plugin that runs our code in a **separate process** and exchanges files/JSON creates no combined work
[inferred]; an in-process AGPL plugin would also be compatible via GPLv3/AGPLv3 section 13 [inferred], with the AGPL
network clause applying to hosted use. The plan keeps hornlab code out of BL's process, which sidesteps the question.
Ath is proprietary (non-commercial), run by BL as a separate process; we do not touch it.

## 6. Corrections to our own docs found by this pass

| Doc | Says | Now |
|---|---|---|
| `docs/plan/12_RESEARCH_BASIS.md` s1, `docs/plan/README.md` row 3 (frozen) | `blab project solve` is not BL's CLI | It is, since BL's headless CLI was added; recorded here because plan files are frozen |
| `docs/plan/01_CONTRACTS.md` (frozen) | bbox check "0.1 to 1 m" | code and task 04 spec use 0.02-5.0 m (intentional, task 04) |
| `docs/HIGH_FREQUENCY_OPTIONS.md` | CUDA fused path not used | Still true for our pinned source driver; BEAT 0.6.0's **compiled** CUDA driver uses a direct-system assembler, so the 2.45x option exists upstream without patching HornLab [verified in BEAT source, VRAM unmeasured] |

## 7. What could not be verified here (needs the GPU box or a BL install)

- BL headless runtime, start-up cost per call, and Julia host exit on Windows.
- BEAT 0.6.0 CUDA VRAM and speed on the RTX 4060 (direct-system path).
- Numerical agreement between BL headless and our `beat_cuda` on the same mesh.
- Whether our quarter mesh passes BL's fundamental-domain check without snapping changes.
- Whether BL's float32 outputs move our metrics measurably.

## Sources

- Boundary Lab: https://github.com/JWSound/boundary-lab (tag v0.5.0); release notes `docs/releases/0.5.0.md`
- BEAT Engine: https://github.com/JWSound/BEAT_Engine (tag v0.6.0)
- Release 0.4.3 PR: https://github.com/JWSound/boundary-lab/pull/21
- Vented enclosure generator PR: https://github.com/JWSound/boundary-lab/pull/43
- hornlab-beat-bem: https://github.com/m3gnus/hornlab-beat-bem
- diyAudio Boundary Lab thread: https://www.diyaudio.com/community/threads/boundary-lab.440847/page-2
