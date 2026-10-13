---
title: "[07] Dataset record and store"
labels: [wave-1]
blocked_by: []
---

**Plan file:** [`docs/plan/07_TASK_DATASET.md`](../../docs/plan/07_TASK_DATASET.md)
**Wave:** 1
**Branch:** `task/07-dataset`

## Owned files
Create and edit ONLY these (from the task file's "Owner of:" line):

`hornlab_search/dataset/record.py`, `store.py`, `tests/test_dataset_*.py`

## Checkpoint
**CP-5**: all 23 tests pass, the crash-simulation test actually recovers, and the projected disk for 10,000 records is a number someone can plan around, with and without traces.

Paste the full checkpoint output in the PR.

## Blocked by
none

## Dispatch
Use the verbatim template in [`docs/plan/00_ORCHESTRATOR.md`](../../docs/plan/00_ORCHESTRATOR.md) ("Dispatch prompt template"), with `<path>` = `docs/plan`, `<repo>` = the repo root, and `[YOUR TASK FILE]` = the plan file above. Do not paraphrase it.

## Wave 0 findings that affect this task
- **Solver API drift.** hornlab-beat-bem 0.2.0 returns `SolveResult` (`frequencies_hz`, `pressure_complex` (F,P,N) c128, `spl_db` (F,P,N), `impedance` (F,) c128, `observation_angles_deg`, `mesh_info(n_vertices, n_triangles, physical_tag_areas_m2)`, `timings`, `sphere_pressure_complex`/`sphere_theta_deg`/`sphere_phi_deg`, `surface_pressure_complex`/`surface_neumann_complex`), NOT the plan's `Response`/`p1_dof_count`/`native_diagnostics`. `p1_dof_count == mesh_info.n_vertices`. Task 05 adapts `SolveResult` -> `Response`.
- **Test fixtures.** `tests/conftest.py` provides `fake_response`, `fibonacci_512`, and `requires_*` markers. The CP-1 angle test checks the step is whole hundredths of a degree because (73-1) does not divide 180.
