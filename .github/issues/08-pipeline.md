---
title: "[08] Objective, search, report, CLI"
labels: [wave-2, blocked]
blocked_by: [04, 05, 06, 07]
---

**Plan file:** [`docs/plan/08_TASK_PIPELINE.md`](../../docs/plan/08_TASK_PIPELINE.md)
**Wave:** 2
**Branch:** `task/08-pipeline`

## Owned files
Create and edit ONLY these (from the task file's "Owner of:" line):

`hornlab_search/objective/terms.py`, `scalar.py`, `search/evaluate.py`, `cma.py`, `nsga.py`, `selftest.py`, `report/html.py`, `cli.py` (transferred from task 03), `tests/test_objective_*.py`, `test_search_*.py`, `test_report_*.py`, `test_end_to_end.py`

## Checkpoint
**CP-6**: every test passes, `selftest --analytic` passes at 0.5 dB (or the documented port-model reason is given), the cross-check is reported, the 60-evaluation search completes, and the report opens in a browser with the noise floor at the top. The search is not required to beat the seed.

Paste the full checkpoint output in the PR.

## Blocked by
Issues [04], [05], [06], [07] (CP-2 through CP-5 must all pass first).

## Dispatch
Use the verbatim template in [`docs/plan/00_ORCHESTRATOR.md`](../../docs/plan/00_ORCHESTRATOR.md) ("Dispatch prompt template"), with `<path>` = `docs/plan`, `<repo>` = the repo root, and `[YOUR TASK FILE]` = the plan file above. Do not paraphrase it.

## Wave 0 findings that affect this task
- **Solver API drift.** hornlab-beat-bem 0.2.0 returns `SolveResult` (`frequencies_hz`, `pressure_complex` (F,P,N) c128, `spl_db` (F,P,N), `impedance` (F,) c128, `observation_angles_deg`, `mesh_info(n_vertices, n_triangles, physical_tag_areas_m2)`, `timings`, `sphere_pressure_complex`/`sphere_theta_deg`/`sphere_phi_deg`, `surface_pressure_complex`/`surface_neumann_complex`), NOT the plan's `Response`/`p1_dof_count`/`native_diagnostics`. `p1_dof_count == mesh_info.n_vertices`. Task 05 adapts `SolveResult` -> `Response`; build against `Response`, not `SolveResult`.
- **dof caps.** The plan's caps (8000/16000/24000) are NOT safe on the 8 GB RTX 4060 Laptop; see TOOLCHAIN.md for the measured caps. Measured dof/triangle: 0.500 full-domain, ~0.51 quarter.
- **GPU/Julia hygiene.** Stale persistent Julia hosts hold ~1 GB VRAM each and cause false OOMs/crashes; follow the "GPU / Julia hygiene" section in AGENTS.md. Clear workers at the end of every selftest, run and search, and do not report throughput or peak-VRAM numbers from a dirty state.
