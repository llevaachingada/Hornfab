---
title: "[05] Solve backends and warm worker"
labels: [wave-1]
blocked_by: []
---

**Plan file:** [`docs/plan/05_TASK_SOLVE.md`](../../docs/plan/05_TASK_SOLVE.md)
**Wave:** 1
**Branch:** `task/05-solve`

## Owned files
Create and edit ONLY these (from the task file's "Owner of:" line):

`hornlab_search/solve/base.py`, `beat.py`, `bempp.py`, `worker.py`, `traces.py`, `cache.py`, `tests/test_solve_*.py`

## Checkpoint
**CP-3**: the offline tests pass with nothing installed, a real solve returns a valid `Response`, the symmetry asymmetry is under 0.1 dB, and the warm worker demonstrably works.

Paste the full checkpoint output in the PR.

## Blocked by
none

## Dispatch
Use the verbatim template in [`docs/plan/00_ORCHESTRATOR.md`](../../docs/plan/00_ORCHESTRATOR.md) ("Dispatch prompt template"), with `<path>` = `docs/plan`, `<repo>` = the repo root, and `[YOUR TASK FILE]` = the plan file above. Do not paraphrase it.

## Wave 0 findings that affect this task
- **Solver API drift.** hornlab-beat-bem 0.2.0 returns `SolveResult` (`frequencies_hz`, `pressure_complex` (F,P,N) c128, `spl_db` (F,P,N), `impedance` (F,) c128, `observation_angles_deg`, `mesh_info(n_vertices, n_triangles, physical_tag_areas_m2)`, `timings`, `sphere_pressure_complex`/`sphere_theta_deg`/`sphere_phi_deg`, `surface_pressure_complex`/`surface_neumann_complex`), NOT the plan's `Response`/`p1_dof_count`/`native_diagnostics`. `p1_dof_count == mesh_info.n_vertices`. Task 05 adapts `SolveResult` -> `Response`.
- **Balloon.** `ObservationConfig(sphere_grid=(n_theta, n_phi))`; returns `sphere_pressure_complex` (F, n_theta*n_phi); theta 0..180 deg, phi 0..348.75 deg.
- **dof caps.** The plan's caps (8000/16000/24000) are NOT safe on the 8 GB RTX 4060 Laptop; see TOOLCHAIN.md for the measured caps. Measured dof/triangle: 0.500 full-domain, ~0.51 quarter.
- **GPU/Julia hygiene.** Stale persistent Julia hosts hold ~1 GB VRAM each and cause false OOMs/crashes; follow the "GPU / Julia hygiene" section in AGENTS.md. Task 05's `worker.py` must verify the host actually exits (check the process list) and test it.
- **Symmetry.** Quarter vs full symmetry agree to 0.04-0.06 dB up to 4 kHz on a resolved mesh.
