---
title: "[06] Metrics and targets"
labels: [wave-1]
blocked_by: []
---

**Plan file:** [`docs/plan/06_TASK_METRICS.md`](../../docs/plan/06_TASK_METRICS.md)
**Wave:** 1
**Branch:** `task/06-metrics`

## Owned files
Create and edit ONLY these (from the task file's "Owner of:" line):

`hornlab_search/metrics/polar.py`, `di.py`, `smoothness.py`, `impedance.py`, `compute.py`, `targets/spec.py`, `targets/venue.py`, `tests/test_metrics_*.py`, `tests/test_targets_*.py`

## Checkpoint
**CP-4**: all 35 tests pass and every analytic case is inside its stated tolerance (cardioid reads 180.0 and 4.771).

Paste the full checkpoint output in the PR.

## Blocked by
none

## Dispatch
Use the verbatim template in [`docs/plan/00_ORCHESTRATOR.md`](../../docs/plan/00_ORCHESTRATOR.md) ("Dispatch prompt template"), with `<path>` = `docs/plan`, `<repo>` = the repo root, and `[YOUR TASK FILE]` = the plan file above. Do not paraphrase it.

## Wave 0 findings that affect this task
- **Balloon.** `ObservationConfig(sphere_grid=(n_theta, n_phi))`; returns `sphere_pressure_complex` (F, n_theta*n_phi); theta 0..180 deg, phi 0..348.75 deg.
- **Cardioid.** `fake_response` cardioid is exactly -6.0206 dB at +-90 deg; a strict -6.0 threshold reads ~179.7 deg beamwidth. Use `20*log10(0.5)` or a tolerance at the cut edge.
- **Test fixtures.** `tests/conftest.py` provides `fake_response`, `fibonacci_512`, and `requires_*` markers. The CP-1 angle test checks the step is whole hundredths of a degree because (73-1) does not divide 180.
