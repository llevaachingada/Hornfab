# Metric-BO GUI opt-in surface and release rehearsal (C3)

Date: 2026-11-23 (test run 2026-11-24 local / 2026-11-24T00:39Z)
Machine: HAL, Windows, RTX 4060 8 GB (numbers in `TOOLCHAIN.md`)
Scope: C3 operator surface only. CPU tests and a read-only registry probe. No mesh, BEM, GPU,
dataset, queue, night or package-execution job was run. The metric canary remains **HELD** on the
independent B4 verdict; this note does not approve it.

Interpreter (owner-verified order; source, bayes site-packages, solver site-packages):

```powershell
$env:PYTHONPATH="C:\Users\hunte\Hrns\hornlab-search;C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Lib\site-packages;C:\Users\hunte\Hrns\hornlab-search\.venv\Lib\site-packages"
$env:OMP_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"
& C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Scripts\python.exe -m pytest <files> -q -o addopts="" -p no:cacheprovider
```

`-o addopts=""` overrides the repository's `addopts = "-ra -q"` so the exact summary line is
printed instead of being suppressed by a second `-q`.

## What changed

- `hornlab_search/gui/data_studies.py`
  - Reads the studied `metric_training` / `metric_training_manifest` artifacts and exposes a
    `metric` block on every study panel: task identity, qualified rows (`manifest.n`), artifact
    revision/sha (training + manifest), objective version, synthetic flag, measured `observed`
    J from `results` rows, separate `predicted` J, package mode, budget/profile, lane, deadline,
    and the re-verified approvals/release status.
  - Appends a metric-composite policy card **only for an opt-in metric study**; the frozen
    scalar/turbo/pareto/cma-seed/exploration fallback tuple and their order are unchanged.
  - A metric study never receives the legacy scalar "Prepare immutable solve package" action;
    the opt-in action is labelled and carries `metric=real_metric_v1`, `budget_profile`,
    `approvals_record`, and GPU lane. Non-metric studies keep the legacy action exactly.
  - Launch / queue actions for metric packages are gated on the re-verified release status;
    held, synthetic, offline, missing-approval and stale-revision packages are disabled.
- `hornlab_search/gui/study_jobs.py`
  - `StudyRunBridge.prepare_package` accepts the opt-in metric fields and routes them to
    `hornlab_search.studies.package.prepare_real_metric_package`; absent metric fields keep the
    historical `prepare_run_package` path byte-for-byte.
  - `StudyRunBridge.launch` calls `_require_metric_release_if_any` before any launcher:
    non-`real_metric_v1` metric packages are refused; real metric packages go through the CLI
    `_require_real_metric_release` gate (production), or its exact root-aware equivalent when a
    contained `approvals_root` is injected (tests/embedded roots).
- `hornlab_search/gui/static/studies.js`
  - Adds the opt-in metric policy card when the panel supplies it, opt-in approvals/budget
    inputs, and a dedicated "Real metric (opt-in)" section that keeps measured J and predicted J
    visibly separate. Legacy fallback cards keep their order.
- `tests/test_study_gui_metric.py` (new)
  - Rehearses the routes with real-shaped fixtures, a temporary held/approved approvals record,
    and a counting fake launcher; every backend/subprocess entry point is patched to fail. The
    panel is checked before any package exists (opt-in action enabled, scalar fall-through
    absent), a synthetic package panel never enables a live solve, and a production-shaped bridge
    is checked to delegate to the CLI release gate.

No `hornlab_search/studies/*`, `hornlab_search/bo/*`, config, brief, queue or night file was
changed.

## GUI routes and checked API

| GUI route | Python seam | Checked API |
|---|---|---|
| `GET /api/studies/<id>/<phase>` (execute) | `data_studies.workflow_panel` / `metric_panel` | reads metric artifacts; `verify_real_metric_package_files` on an existing package; `load_metric_approvals` |
| `POST /api/studies/<id>/package` (`metric=real_metric_v1`) | `StudyRunBridge.prepare_package` | `prepare_real_metric_package` |
| `POST /api/studies/<id>/package` (no metric) | `StudyRunBridge.prepare_package` | existing `prepare_run_package` (unchanged) |
| `POST /api/studies/<id>/launch` | `StudyRunBridge.launch` | `_require_metric_release_if_any` -> CLI `_require_real_metric_release` or root-aware equivalent |

There is no parallel package or metric implementation. `server.py` was not edited; the existing
`package` and `launch` routes are reused.

## Refusal matrix

| Route / input | Result | Launcher calls |
|---|---|---|
| Prepare, held approvals (`HELD_PENDING_PARENT_RELEASE`) | package prepared; panel shows HELD; launch disabled | 0 |
| Launch, held approvals | typed 422 (`HELD_PENDING_PARENT_RELEASE`) | 0 |
| Prepare, approved record | package prepared; panel shows approved + parent release unset | 0 |
| Launch, approved but `HORNLAB_METRIC_REAL_EXECUTE` unset | typed 422 (parent release required) | 0 |
| Launch, approved + parent release set | reaches the fake launcher exactly once (no backend) | 1 |
| Prepare, missing approvals record | typed 422 | 0 |
| Prepare, bad approvals schema | typed 400 | 0 |
| Prepare, missing `budget_profile` | typed 400 | 0 |
| Prepare, forced scalar proposal policy (fall-through) | typed 400 | 0 |
| Launch, synthetic metric package | typed 422 ("can never authorize a real solver") | 0 |
| Release gate, `real_data_offline_v1` package | typed 422 ("can never authorize a real solver") | 0 |
| Launch, stale study revision | typed 409 | 0 |
| Legacy scalar/turbo/pareto package | existing launch path unchanged (tested by the GUI/study neighbours) | n/a |

Zero-call proof: `tests/test_study_gui_metric.py::_no_backend` replaces
`production.build_worker`, `production.execute_study`, `solve.base.get_backend`,
`subprocess.run`, `subprocess.Popen` and `os.system` with hard failures, and asserts
`launcher.calls == []` in every refusal case.

## Real canary, read-only panel probe [measured]

Read-only `GET /api/studies/aa1b1b86b1f446f9a8d329662c9884f6/execute` against the existing
`runs/metric_bo_canary_2026-11-23/registry` (no write, no solve):

```text
study aa1b1b86b1f446f9a8d329662c9884f6 revision 1
panel status unknown
metric status ready
mode real_metric_v1
task_identity 82dbd04691c7b456
qualified_rows 174
artifact_revision 1
artifact_sha256 fd7c01871635f64c2c8b4a4f3fcf682d7a7c9f94f0b6584d23a35e56459e7b3c
manifest sha 31f5fa1449506d506addc022125e32f35856714ac6c2682bfba9078369cbd20d
synthetic False objective_version 11
observed {'status': 'missing', 'best_j': None, 'n_measured': 0, 'source': 'results observations observed_j'}
predicted {'status': 'model_prediction', 'j': 7.713770897134498, 'measured': False, 'source': 'proposal predicted j_mean (model output, never a measurement)'}
budget_profile metric-canary-8x2 lane gpu deadline 2026-11-30T05:05:22+00:00
release {'status': 'unavailable', 'approvals_status': 'HELD_PENDING_PARENT_RELEASE', 'owner_authorized': False, 'parent_release': False, 'refit_every': 4, 'pinned_files': 7, 'reason': 'approvals status is HELD_PENDING_PARENT_RELEASE; owner authorization is absent; parent release HORNLAB_METRIC_REAL_EXECUTE=1 is unset'}
actions [('package', False, 'Prepare real metric package (opt-in)'), ('launch', False, 'Launch serial solve study'), ('cancel', False, 'Stop after current candidate'), ('queue_study', False, 'Write night-queue file for this study')]
```

Interpretation: the real canary artifact reports the expected 174 qualified rows, task identity
`82dbd04691c7b456`, revision 1 and the training/manifest hashes above. The package approval is
`HELD_PENDING_PARENT_RELEASE` with no owner authorization and no parent release, so every live
action is disabled. No solve was attempted or implied.

## Test output [measured]

New focused file (`tests/test_study_gui_metric.py`), `--junitxml` reported
`tests="12" errors="0" failures="0" skipped="0"`:

```text
12 passed, 25 warnings in 12.03s
```

Focused GUI/study neighbours (12 files: new metric test, production/instrumentation, GUI studies
API/module/QA, lifecycle, queue, solve-design job, package gate, CLI canary, real-metric package):

```text
72 passed, 69 warnings in 38.16s
```

All GUI/study CPU neighbours (16 files: every `test_gui_stud*`, every `test_study_gui_*`,
`test_study_launch_durable`, `test_study_duplicate_execution`, `test_study_package_gate`,
`test_studies_cli_metric_canary`, `test_studies_package_metric_real`):

```text
123 passed, 69 warnings in 76.49s (0:01:16)
```

## Direct API and status transcription

- `prepare_real_metric_package` is called with `approvals_record`, `budget_profile`, `lane='gpu'`,
  `deadline`, `expected_revision`, `idempotency_key`, frozen dependency pins and the optional
  contained `approvals_root`.
- `verify_real_metric_package_files(package, root=<gui root>)` supplies the panel's approvals
  status, owner flag and pinned-file count.
- `_require_real_metric_release` is the production launch gate; a contained root uses the same
  status/owner/parent-release/interpreter checks through the package module because the CLI
  helper resolves the approval record from the canonical checkout. If the parent wants one
  signature for both, add `root=` to the CLI helper; no other API gap blocked the GUI.

## Canary status

The metric canary is still **HELD_PENDING_PARENT_RELEASE** and no live metric dispatch is
approved by this slice. The GUI exposes the checked path, refuses every ungated route and makes
zero backend calls on dry-run/refusal paths.
