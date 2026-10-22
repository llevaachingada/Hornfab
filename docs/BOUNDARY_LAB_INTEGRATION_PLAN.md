# Boundary Lab 0.5.0 integration plan for hornlab-search

Date 2026-10-21. Status: **PROPOSED, not started.** **Priority revised 2026-10-22** (`docs/SENIOR_ARCHITECTURE_REPORT_2026-10-22.md` s2): core work first, then BL-1 export, BL-2 cross-check, the engine question; BL-3 plugin PARKED. Read `docs/BOUNDARY_LAB_0.5_RESEARCH.md` first (findings,
evidence, conventions table). This plan adds to the project; it changes no frozen contract, no gate, no solver.

## 1. Decision and reasoning

**Integrate by interchange, keep the search loop where it is.**

| Option | Verdict | Why |
|---|---|---|
| A. Export solve-ready `.blab.json` projects | **Do first** | No BL dependency (we write JSON); every best design opens in the BL GUI; enables B |
| B. BL headless (`blab project solve`) as a **cross-check solver** | **Do second** | Third independent check next to bempp (CP-7b), on the engine BL users run (BEAT 0.6.0); results comparable with the BL community |
| C. hornlab **geometry provider plugin** for BL | **Do third** | BL users generate OSSE/ICW/FREEFORM hornlab designs natively, and load our best designs; small, matches BL's own example pattern |
| D. Run CMA-ES inside BL via host services | **Not now** | GUI-only, serialized (1 active + 1 pending), host owns frequencies/backend, no host-driven generation; our loop, dataset and GPU hygiene would all be rebuilt around a 5-week-old API |
| E. Replace `hornlab-beat-bem` with a direct BEAT 0.6.0 backend | **Separate decision** | Large (compiled-system builder + decoder), but gets the CUDA direct-system assembler (more dofs on 8 GB) and an upstream-maintained engine; needs B's numbers first and the HornLab author's view |
| F. BL server | **Later** | "development preview", one job at a time; revisit for cloud GPU (`docs/CLOUD_GPU_REPORT.md`) |

Principles that hold in every phase:
1. **BL never runs in our venv.** BL hard-pins `beat_engine == 0.6.0`; it gets its own environment and is called as a
   subprocess (`HORNLAB_BLAB_EXE` pointing at its `blab`). Our code never imports `blab`.
2. **Our code never runs in BL's process.** The plugin launches our interpreter as a subprocess, exactly like BL's own
   vented-enclosure example launches gmsh. This also keeps licences at arm's length.
3. **Silent killers carried over by construction:** mesh scale is always `scale_to_m = 1.0` and tested; BL symmetry is
   derived from `mesh/sizing.py::SYMMETRY_PLANE` (one source), never a second table; DI is ours, from BL's balloon,
   `di_source = "balloon"`.
4. **GPU hygiene (CLAUDE.md) for every BL solve:** BL does not shut down its Julia worker, so our wrapper clears
   stale hosts before, kills after, verifies VRAM, one GPU job at a time.
5. Every horn number stays in YAML; every new parameter name comes from BL's or the mesher's own schema (hard rule 3).

## 2. Ownership (needs an orchestrator/user sign-off before code)

| New path | Proposed owner |
|---|---|
| `hornlab_search/blab/**` (`conventions.py`, `project.py`, `results.py`, `headless.py`, `provider_worker.py`) | new task "BL integration" (orchestrator) |
| `integrations/boundary_lab/hornlab_waveguide/**` (the BL plugin package) | same |
| `tests/test_blab_*.py` | same |
| `hornlab_search/cli.py` subcommands `export-blab`, `selftest --crosscheck-blab` | task 08 (additive) |
| `TOOLCHAIN.md` BL environment section | task 02 |
| `CLAUDE.md` ownership row, `.github/workflows/ci.yml` (no change expected) | orchestrator |

## 3. Phases

### BL-0. Environment (GPU box, no code)
1. Separate venv for BL 0.5.0 (its installer or `pip install` of the tag in a new venv); `python -m beat_engine
   instantiate --backend cuda`. Record path, versions, BEAT wheel SHA-256 (`10db2ee2...dd3`) in `TOOLCHAIN.md`.
2. `blab project validate tests/fixtures/remote-exterior.blab.json --json` from BL's own repo, then one headless solve of
   that fixture with `--backend beat_cuda`; afterwards check `Get-Process julia` (BL leaves its worker; record whether it
   exits on its own and after how long).
Exit: **CP-11a** paste of versions, the validate JSON, the solve summary, and the Julia process list before/after.

### BL-1. Project export (offline; CI-testable)
Files: `hornlab_search/blab/conventions.py`, `hornlab_search/blab/project.py`, CLI `hornlab-search export-blab`.
- `conventions.py` (pure, no BL import):
  - `blab_symmetry(quadrants)`: from `sizing.SYMMETRY_PLANE`: `"yz+xz" -> "xy"`, `"yz" -> "x"`, `None -> "off"`,
    `"xz"` -> raise (BL has no Y-only symmetry). Test: every key of `SYMMETRY_PLANE` maps or raises, together with
    `QUADRANT_FACTOR` (silent killer 2 test pattern).
  - Boundary roles from the mesh's `$PhysicalNames`: `SD1D1001 -> moving`, `SD1G0`/`SD2G0 -> rigid`; any other group
    -> refuse export with the group name (BL requires every group to have exactly one role).
  - Excitation basis conversion helpers for B: our unit acceleration vs BL `normal_velocity` 1 m/s, and the
    `exp(+i wt)` vs `exp(-i wt)` conjugation, each with a closed-form unit test.
- `project.py::export_project(design, cfg, mode, out_dir)`:
  1. Build the mesh with our own `mesh.build.build_mesh` (same epw, cap, quadrants as the run), copy the `.msh` into
     `out_dir/meshes/`.
  2. Write `out_dir/<name>.blab.json`, `schema_version 10`, with only what BL's minimal fixture needs plus preferences:
     `physical_system` (model_version 1): one `bem_surface` mesh resource (`scale_to_m 1.0`, `translation_m [0,0,0]`),
     one `unbounded_air` region (`loss_model {}`), boundaries per role, one `ideal_velocity_source` component, one
     `normal_velocity` port, `interfaces []`, `metadata {"hornlab": {design_hash, family, params, config_name,
     config_sha, lib_shas, mode, quadrants}}` (metadata survives BL loading; research s2.1).
     Top-level `symmetry` from `blab_symmetry`. `project_preferences`: `polar_observation_distance_m` =
     `solve.distance_m`, `polar_angle_step_deg` chosen to reproduce our angle grid (derived from `solve.angle_count`,
     refuse if not representable), `spherical_sampling_enabled true`, `balloon_angle_precision_deg` giving about
     `balloon_points_<mode>` Fibonacci points (`round(41253 / a^2)`, clamp 0.5-15).
  3. Write `out_dir/request.json` (overlay schema 1) with `frequencies_hz` = `config.mode_freqs(mode, cfg)` exactly
     (BL parses preference frequencies as ints; the overlay avoids that).
  4. Refuse: bbox outside our guard, non-1.0 scale, unknown physical group, `quadrants "12"`.
- CLI: `hornlab-search export-blab --config <yaml> [--run <dir> --top N | --seed] [--mode screen|verify] --out <dir>`.
- Tests (`tests/test_blab_project.py`, offline): JSON structure against a frozen copy of BL's field list (not BL
  code); `scale_to_m == 1.0`; symmetry pairing for all quadrants; role assignment from a real mesher `.msh`
  (`requires_mesher`); frequencies exact; refusal cases. Optional `requires_blab` test: `blab project validate` passes
  (deselected in CI like `gpu`).
Exit: **CP-11b** export of the `osse_baseline` seed and the CP-8c best OSSE design; `blab project validate --json`
pasted (expect `solve_kind exterior_bem`, `symmetry xy`, 12 frequencies); open in the BL GUI and screenshot.

### BL-2. Cross-check solver via BL headless (GPU box)
Files: `hornlab_search/blab/headless.py`, `hornlab_search/blab/results.py`, `selftest --crosscheck-blab`.
- `headless.py`: hygiene (clear stale Julia, record VRAM baseline) -> `blab project solve <proj> --request request.json
  --backend beat_cuda --events ndjson --output <fresh dir>` as a subprocess with timeout -> parse ndjson events ->
  kill BL's Julia worker -> verify the process list (CLAUDE.md rule 6).
- `results.py`: read `manifest.json` v2 and per-frequency NPZ (no BL import), sort by frequency, take
  `acoustic:pressure:{horizontal,vertical}-polar` and `acoustic:pressure:sphere`, convert basis and time convention,
  and build our `Response` so the **existing** `metrics_from_response` path computes beamwidth, ripple, on-axis and
  balloon DI (the Fibonacci sphere is equal-area, which `metrics_from_response` already handles).
- `selftest --crosscheck-blab --config <yaml>`: one design, our `beat_cuda` vs BL headless on the **same exported
  mesh**, report through `hornlab-search compare` plus SPL differences on the cuts.
- Acceptance uses the **frozen** CP-7b rule (`docs/plan/09_CHECKPOINTS.md`): two-solver disagreement < 0.2 dB means both
  are very likely right. No new threshold is invented.
Exit: **CP-11c** cross-check pasted for the OSSE seed (quarter) and one ICW design; Julia process list clean after.
If it fails: stop, report, do not "fix" by adjusting conversions without a closed-form check.

### BL-3. hornlab geometry provider plugin for BL (BL GUI)
Package `integrations/boundary_lab/hornlab_waveguide/`, installed by copying into `<BL>/geometry_providers/`:
```
provider.json        {"manifest_version":1,"id":"hornlab.waveguide","name":"hornlab waveguide","version":"0.1.0",
                      "provider_api":1,"source_schema_version":1,"backend":"waveguide.backend:create_backend",
                      "default_source":{...},"mesh_scale_factor":1.0}
waveguide/backend.py  BL-side only: subprocess to the hornlab interpreter, returns GenerationResponse
waveguide/editor.py   (BL-3b) small PySide6 form + "Load best from hornlab run" button
```
- Source (saved in the BL project): `{"hornlab_python": "<abs path to .venv python>", "family", "params", "mode",
  "epw", "quadrants"}` or `{"hornlab_python", "run_dir", "rank"}` to load a searched design. Unknown fields retained.
- `backend.py` runs `<hornlab_python> -I -m hornlab_search.blab.provider_worker <source.json> <fresh run_root dir>`
  (fresh directory per revision, never overwriting an accepted artifact), waits with Stop support, and returns a
  **single-mesh** `GeneratedGeometry`: full mesh (`quadrants 1234`), plus `reduced_cleaned_mesh_path` and `mirror_axes`
  from `blab_symmetry` when the design is symmetric, plus a radiator hint for `SD1D1001`, so BL's standard exterior
  seeding assigns rigid/moving roles. `configuration_patch` sets `symmetry_config` only. No frequencies (host-owned).
- `hornlab_search/blab/provider_worker.py` (our side, CI-testable): validate the design, mesh full and reduced with
  our `build_mesh`, write both `.msh` and a small JSON result (paths, groups, bbox, hornlab provenance).
- BL-3a ships without an editor (BL shows the source as read-only JSON and can still Generate); BL-3b adds the form.
- Tests: worker offline (`requires_mesher`); manifest fields vs the API table; the BL-side backend only in the BL env
  (`requires_blab`).
Exit: **CP-11d** on the GPU box: enable the plugin, generate the OSSE seed and the CP-8c best design, solve in the BL
GUI, compare BL's plots with ours (and with CP-11c numbers). Screenshots plus the comparison pasted.

### BL-4. Later, each needs its own decision
- Interactive refinement inside BL using `ProviderHost` (editor-driven: update_source -> generate -> geometry_accepted
  -> solve -> result), for small local tweaks of a searched design, not for the batch search.
- Direct BEAT 0.6.0 backend (`beat_cuda06`): compiled-system builder + decoder; only if CP-11c shows agreement and the
  user wants the CUDA direct-system memory headroom (`docs/HIGH_FREQUENCY_OPTIONS.md`).
- BL server on a rented GPU.
- Exporting `.blabsp` speaker packages.

## 4. Risks and how each is contained

| Risk | Containment |
|---|---|
| mm/m scale (BL default 0.001) | exporter and plugin force 1.0; bbox test; validate shows mesh extent |
| Symmetry mismatch | single mapping from `SYMMETRY_PLANE`; pairing test; BL fundamental-domain check in CP-11b |
| Excitation basis or phase sign error | closed-form tests of the conversions; CP-11c compares normalized metrics first |
| Julia hosts piling up (BL never shuts down) | wrapper kills and verifies; CP-11a measures BL's behaviour |
| BL API churn (provider API 5 weeks old) | pin BL tag in TOOLCHAIN; the plugin touches only documented exchange types; exporter writes only fields in BL's minimal fixture |
| BL headless skips GUI mesh repair | we validate our meshes ourselves; BL's `validate` is part of CP-11b |
| Float32 in BL vs our precision | measured in CP-11c against the 0.039 dB noise floor |
| Licences | separate processes in both directions; no BL code copied into this repo |

## 5. Decisions needed from the user

1. Approve the order A -> B -> C and leave D/E/F for later?
2. Approve the new ownership rows (section 2) so a task can be dispatched?
3. Install BL 0.5.0 in its own environment on the GPU box (BL-0)?
4. Contact JW Sound (BL) about: a stable headless results reader, worker shutdown on CLI exit, and whether they would
   list a hornlab provider; and the HornLab author about the engine drift (vendored engine vs BEAT 0.6.0).

## 6. Effort estimate [inferred]

| Phase | Code | Tests | GPU time |
|---|---|---|---|
| BL-0 | none | n/a | under 1 h |
| BL-1 | about 300 lines | about 15 offline tests | none |
| BL-2 | about 300 lines | about 10 offline + 1 GPU | about 1 h |
| BL-3a/b | about 250 + 200 lines | about 8 offline | about 1 h (GUI) |
