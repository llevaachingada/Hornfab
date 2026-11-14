# Test-suite optimization plan — measured 2026-11-13 (senior pass)

**Status:** PLAN. Owner-gated. **Nothing in this document has been applied** — no test deleted, no
assertion touched, no CI edit, no dependency added.
**Supersedes the "next step" of** `docs/research/TEST_SUITE_EFFICIENCY_2026-11-12.md` (its R1–R8 are
still correct and still unapplied; this pass re-measures, finds where the seconds actually live, and
makes parallelism — not deletion — the primary lever).
**Related:** `docs/CONTINUITY.md` 2026-11-12/13 entries, `docs/ISSUES.md`, `.github/workflows/ci.yml`,
`tests/conftest.py`, `pyproject.toml`.

---

## 0. The answer in five lines

1. The suite is **3,739 tests in 975.8 s of test time, 18 min 12 s wall, 0 failures** (CI selection,
   full local venv). Yesterday's equivalent was 588 s; today's has grown ~40 %.
2. **41 tests (1.1 % of the suite) carry 57 % of the time.** The other 2,913 tests cost 19 s in total.
3. **The machine has 24 logical cores and pytest uses one.** Parallelism is the lever; deletion is not.
4. Deleting dead tests and merging thin files is worth **≲1 min of wall time** — do it for
   maintainability, and do it with a bar, but do not expect it to make the suite fast.
5. Target with this plan: **18 min → 2–3 min** for the routine lane, **every existing test still
   running**, run nightly/pre-merge instead of on every keystroke.

---

## 1. Measured facts (2026-11-13, this machine, full local venv)

Command (exactly the CI selection, `.venv\Scripts\python.exe`):

```powershell
python -m pytest -m "not slow and not gpu and not crosscheck" --durations=60 --junitxml=ci_junit.xml
```

| Measurement | Value |
|---|---|
| Collected (all) | 3,760 cases / 307 files / 3,065 test functions |
| Run in the CI selection | **3,739 run, 18 skipped, 0 failed, 0 errors, 21 deselected** |
| Test time (junit `time` sum) | **975.8 s** |
| Wall clock | **1,092 s = 18 min 12 s** |
| Collection / startup | 5.4 s collected; ~10 % of wall is harness overhead |
| Dependency-gated files (`requires_mesher/beat/bempp/build123d`) | **331.5 s = 34.0 %** — CI never runs these (CI installs no mesher/beat/bempp) |
| Ungated files (what CI actually runs) | 644.3 s = 66.0 % |

### 1.1 Cost concentration

| Threshold | Tests | Time | Share |
|---|---:|---:|---:|
| ≥ 10 s | 19 | 398.7 s | 40.9 % |
| ≥ 5 s | **41** | **556.5 s** | **57.0 %** |
| ≥ 1 s | 162 | 790.4 s | 81.0 % |
| < 0.05 s | 2,913 | 19.4 s | 2.0 % |

### 1.2 The 41 tests ≥5 s (the entire problem, by name)

| s | test |
|---:|---|
| 48.11 | `test_bassbox::test_recommendation_meets_the_owner_targets` (module fixture: one real design sweep) |
| 46.05 | `test_gui_preview_shape::test_generator_kind_osse_axi_sections_mouth_3d_and_timings` |
| 36.46 | `test_search_export_step::test_export_step_seed_writes_a_step_file` |
| 35.44 | `test_search_export_step::test_export_step_run_ranks_distinct_designs` |
| 28.35 | `test_tools_hf_sync::test_push_dry_run_makes_no_network_call` (setup, cause unexplained — see §5.4) |
| 23.82 | `test_report_html::test_report_under_10_mb_for_200_evaluations` |
| 18.42 | `test_gui_preview_shape::test_plughorn_3d_survives_one_untriangulable_face` |
| 17.82 | `test_tools_analysis_parameter_study::test_cli_real_bounded_subset` |
| 15.04 | `test_tools_analysis_parameter_study::test_good_design_fold_prediction_does_not_allow_recommendation` |
| 14.55 | `test_search_campaign::test_cli_families_with_brief` |
| 14.50 | `test_search_campaign::test_cli_families_parses` |
| 14.47 | `test_mesh_plughorn::test_cone_fill_exports_one_connected_solid[path0]` |
| 13.82 | `test_search_campaign::test_cli_families_incompat_reason_not_truncated` |
| 13.58 | `test_search_pipeline_prefetch::test_cma_me_with_prefetch_matches_serial` |
| 13.41 | `test_mesh_mid_ports::test_mid_ports_absent_mesh_byte_identical` |
| 12.63 | `test_solve_fused_flag::test_beatbackend_env_flag_init` |
| 11.60 | `test_mesh_plughorn::test_mesh_build_one_driver_face[path0]` |
| 10.34 | `test_mesh_build::test_export_step` |
| 10.29 | `test_mesh_plughorn::test_morph_knobs_move_what_they_say` |
| 9.69 | `test_design_freeform_sculpt::test_seed_and_samples_mesh_on_the_real_mesher` |
| 9.49 | `test_mesh_mid_ports::test_mid_ports_on_inventory` |
| 9.36 | `test_solve_traces::test_dof_permutations_are_one_to_one_on_a_real_mesh` |
| 8.60 | `test_search_restarts::test_interrupt_and_resume_matches_the_uninterrupted_run_with_no_double_spend` |
| 7.99 | `test_gui_preview_shape::test_typology_link_resolves_by_catalog_name` |
| 7.88 | `test_tools_analysis_v8_rescore::test_full_run_is_deterministic` |
| 7.88 | `test_tools_analysis_parameter_study::test_payload_has_frozen_schema_and_actual_design_blocks` |
| 7.79 | `test_search_cma::test_resume_performs_zero_solves_for_finished_work_and_matches_an_uninterrupted_run` |
| 7.68 | `test_mesh_plughorn::test_front_chamber_volume_and_cutoff` |
| 7.11 | `test_mesh_build::test_quarter_is_a_quarter` |
| 7.00 | `test_mesh_plughorn::test_examples_load_and_seed` |
| 6.97 | `test_mesh_plughorn::test_cone_fill_exports_one_connected_solid[path1]` |
| 6.90 | `test_search_restarts::test_all_restarts_stopping_naturally_ends_on_restarts_exhausted` |
| 6.88 | `test_mesh_build::test_triangle_count_scales_as_fmax_squared` |
| 6.83 | `test_search_pipeline_prefetch::test_prefetch_gives_identical_rows_in_identical_order_and_overlaps` |
| 6.22 | `test_search_pipeline_prefetch::test_budget_and_resume_with_prefetch_match_serial` |
| 5.99 | `test_mesh_meh_step_build::test_t1_mesh_keeps_two_entry_groups` |
| 5.83 | `test_mesh_plughorn::test_quadrants_must_be_full` |
| 5.59 | `test_report_html::test_report_has_run_id_and_at_least_six_pngs` |
| 5.47 | `test_tools_analysis_parameter_study::test_missing_physical_output_uses_output_specific_folds` |
| 5.39 | `test_report_html::test_report_states_an_improvement_when_there_is_one` |
| 5.29 | `test_search_cma::test_trace_sampling_is_deterministic_and_close_to_the_configured_rate` |

### 1.3 Cost concentration by file (top 12 = 59 % of all test time)

| s | n | gated | file |
|---:|---:|---|---|
| 74.1 | 14 | – | `test_gui_preview_shape.py` (real build123d/OCP 3D tessellation) |
| 73.0 | 13 | mesher+cad | `test_mesh_plughorn.py` |
| 71.9 | 4 | mesher | `test_search_export_step.py` (real OCP STEP export) |
| 50.3 | 30 | mesher | `test_mesh_build.py` (~34 real gmsh builds) |
| 49.7 | 12 | – | `test_tools_analysis_parameter_study.py` |
| 48.7 | 65 | – | `test_bassbox.py` (one module fixture = 48.1 s) |
| 43.2 | 56 | – | `test_search_campaign.py` (3 CLI runs × 45 config+space loads) |
| 43.1 | 8 | – | `test_report_html.py` (real figure rendering) |
| 36.0 | 12 | – | `test_search_pipeline_prefetch.py` |
| 34.0 | 15 | – | `test_search_cma.py` |
| 28.4 | 8 | – | `test_tools_hf_sync.py` |
| 22.9 | 2 | mesher | `test_mesh_mid_ports.py` |

### 1.4 Growth and shape

| Measurement | Value |
|---|---|
| Test files added since 2026-11-12 | **129** |
| Test LOC vs source LOC | **50,760 vs 50,734 (1.00 : 1)** |
| Files with < 5 test functions | **83 of 307 (27 %)**; 9 files have exactly one test |
| Non-test helper modules in `tests/` | 7 (`conftest.py`, `test_dataset_factory.py`, `gui_verify_fixtures.py`, …) |
| Marked `slow` today | 6 files (all GPU/BEM end-to-end) — none of the 41 above |
| Parallelism wired | **none** — no `pytest-xdist`, no `-n`, CI is serial |

---

## 2. Why the suite feels slow to agents (the part that is not pytest)

Pytest is half the story. The other half is execution topology, unchanged from the 2026-11-12 review:

1. `.github/workflows/ci.yml` still triggers on **both** `push` and `pull_request` → 2 full runs per
   branch push; no pip cache; docs-only commits re-run the whole suite.
2. **30 git worktrees exist** under `oc-wt/`, `hf-wt/`, `meh-wt/`, `swarm-wt/`, each with its own copy
   of ~200–275 test files. A lane that runs the suite in its worktree runs 18 minutes of CPU on a box
   that is simultaneously running a GPU night and other lanes.
3. The de-facto protocol (CONTINUITY "Final gate [measured]" entries) is *paste a full-suite run*, so
   lanes and the orchestrator each pay the 18 minutes — often twice (lane + merge).
4. Locally the suite is **34 % slower than CI** because the dev venv has the mesher/solver installed,
   so `requires_*` gates do not skip. Agents therefore pay 5.5 minutes of real meshing that CI never
   pays — on every green check.

So: the same code is verified 2–4 times, on one core, with a third of the time spent rebuilding meshes
that CI would have skipped.

---

## 3. What will **not** work (so we do not spend a week on it)

| Idea | Reality | Verdict |
|---|---|---|
| "Delete the dead tests and it'll be fast" | The 41 slow tests are not dead — they are the real mesh/STEP/campaign/CMA integration coverage. Everything else is already ~0 s. | Deletion buys ≲ 1 min. Don't sell it as a speed fix. |
| "Consolidate 307 files into fewer" | Full collection of 3,760 cases is **5.4 s**. | Legibility win only. Worth doing slowly, not as an optimization. |
| "Reduce parametrization" | Largest single parametrized product is 35 cases; file totals come from many functions. | Not a lever. |
| "Use the `slow` marker" | Marker exists and is already deselected in CI — **but only 6 files use it, none of the 41**. | Correct lever, just never completed. |
| "Skip the mesher tests locally" | Would make local ≠ CI in the other direction: CI never runs them, so nobody would. | Bad. Keep them, move them. |
| "Run every test on the GPU" | numpy/scipy unit tests have no GPU path; moving them needs a cupy rewrite. And only 19 tests (5 files) do a real BEM solve. | Wrong lever for 99 % of the suite. |
| "Run the GPU solves inside the 2-min loop" | A fused 4k-dof solve is 8.5 s and the GPU lane does 13 of them plus 4 mesh builds. It cannot be 2 min. | Run it as a **parallel lane** (Phase 1b), not sequentially. |
| "Delete the GPU lock so tests stop refusing" | No test acquires the lock. The refusal is the default *policy*, not the mechanism. | Policy fixed in Phase 1b: warn-by-default (`refuse`/`off` by env); the lock file is kept as the host-ownership signal. |

---

## 4. The plan

Five phases, ordered by (time saved) ÷ (risk). Each phase has a hard gate; a phase that fails its gate
does not get merged and does not get followed by the next one.

### Phase 0 — Prove the parallelism lever (≈30 min, reversible, biggest single win)

The box has 24 logical cores; pytest uses 1. This is the whole optimization.

1. Add `pytest-xdist` to `[project.optional-dependencies] dev` (or install into `.venv` first as a
   trial without touching `pyproject.toml`).
2. Four small parallel-safety fixes **before** the first trial run (all `tmp_path`/import edits, no
   assertions changed):
   - `tests/test_design_generators_grid_full_ring.py:164,186` — writes fixed `runs/c2_probe*`; move to `tmp_path`.
   - `tests/test_s1a_driver_briefs.py:245` — writes fixed `runs/s1a_probe`; move to `tmp_path`.
   - `tests/test_surrogate_stage_a.py:21`, `test_surrogate_hardening.py:13`, `test_surrogate_ismo.py:3`
     — module-scope `torch` imports (2.8 s per worker); make them lazy inside the tests.
   - Keep GPU/BEM files out via the existing markers (`not gpu and not crosscheck`), and never run
     xdist during a GPU night (one CUDA lane rule).
3. Trial, then measure:

```powershell
# trial 1 — ordering-safe, respects module-scoped fixtures
python -m pytest -m "not slow and not gpu and not crosscheck" -n 6 --dist loadscope -p no:cacheprovider
# trial 2 — if green, push to 8 (leave headroom for the GPU lane / other agents)
python -m pytest -m "not slow and not gpu and not crosscheck" -n 8 --dist loadscope
```

**Gate:** same 3,739 run, **0 failed, 0 errors**, identical skip count; wall ≤ 6 min at `-n 6`.

**MEASURED 2026-11-13 (applied on branch `test/testspeed-2026-11-13`):**

| Run | Wall | junit test time | Inflation vs serial |
|---|---:|---:|---:|
| serial baseline (Phase 0 measurement) | 1,092 s (18.2 min) | 975.8 s | 1.00× |
| `-n 6 --dist loadscope`, no env caps | 420.7 s (7.0 min) | 1,787.3 s | 1.83× |
| **`-n 6 --dist loadscope`, single-thread BLAS** | **353.0 s (5.9 min)** | **1,359.9 s** | **1.39×** |

**3.1× faster, 3,766 cases, and the only failures are pre-existing** (`test_tools_experiments_manifest.py`
fails identically under a serial run in this checkout — 4 failed / 24 collection errors; it is not
caused by xdist and is out of scope here).

**`-n 8` is worse, measured:** same selection and caps, 8 workers → **2,933 s of test time** and the
poles balloon (`test_gui_preview_shape` 56 s → **186 s**, `test_gui_sandbox_explore` 57 s → 171 s,
`test_search_export_step` 82 s → 136 s). Wall was ~8.5 min vs 5.9 min at `-n 6`. Eight workers on
24 cores oversubscribe the native mesher/OCCT/BLAS pools; use **6**.

**The thread caps are not optional.** Without `OMP_NUM_THREADS=1` / `OPENBLAS_NUM_THREADS=1` /
`MKL_NUM_THREADS=1` / `NUMEXPR_NUM_THREADS=1` / `VECLIB_MAXIMUM_THREADS=1`, six workers each spawn a
full BLAS/OpenMP pool and the suite *inflates* by 1.83× (gmsh/OCCT tests go 46 s → 90 s). With the caps
the inflation is 1.39×. The canonical command therefore sets them:

```powershell
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"; $env:VECLIB_MAXIMUM_THREADS="1"
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" `
    -n 6 --dist loadscope -p no:cacheprovider
```

**What the remaining 5.9 min is** (fused run, per test, capped): `test_export_step` pair **82 s + 76 s**
on one worker (they share a module, so `loadscope` serialises them — together the critical path),
`test_gui_sandbox_explore::test_morph_capability_rule` 57 s (`D.list_configs(ROOT)` parses 45 configs),
`test_gui_preview_shape` 56 s, `test_bassbox` 55 s, `test_report_html` 39 s, `test_search_campaign`
33 s. Those six are the next honest targets — and two of them are **fixture bugs, not slow tests**:
`list_configs` and the campaign family table are re-parsed per test and should be session-cached
(Phase 2). No test needs to be deferred to get below ~4 min; the remaining cost is re-computation.

> Why `-n 6` and not `-n auto`: `auto` would grab 24 workers on a machine that is also running a GPU
> solve, a GUI, and other agent lanes. Oversubscription is how this box gets bogged down in the first
> place. Measured: **6 is the sweet spot**; 8 is worse (see the table above), `auto` would be far worse.

### Phase 1 — Cost lanes (owner decision 2026-11-13: **NOT APPLIED — no `slow` marking**)

Owner: "I don't [care] about this whole slow profile thing, we need everything to go fast." So this
phase is **cancelled as written**: nothing is deferred to a nightly lane. The `slow` marker was instead
removed from the six files that used it (it duplicated `gpu`/`crosscheck` on 16 of its 21 tests and
uniquely labelled only 5, all of them real BEM solves). See Phase 1b.

What replaces it: run the heavy CPU tests **inside the parallel lane** and remove their *re-computation*
(Phase 2). The measured remaining cost after Phase 0 is six tests (§Phase 0 table); two of them are
fixture bugs, not slow work. Deferring them would hide the bug.

Kept for the record — the marking list that was **not** applied:

- every test in the §1.2 list that belongs to a file **without** a `requires_*` gate:
  `test_bassbox` `rows` tests (all 4 that use the module fixture), `test_gui_preview_shape` (3 heavy),
  `test_search_campaign` CLI-family (3), `test_report_html` (3), `test_search_pipeline_prefetch` (4),
  `test_search_cma` (5), `test_tools_analysis_parameter_study` (5), `test_tools_analysis_v8_rescore` (2),
  `test_search_restarts` (2), `test_solve_fused_flag::test_beatbackend_env_flag_init` (1),
  `test_tools_hf_sync` (the one 28 s setup test);
- every **real-build** test in a gated file: `test_search_export_step` (2), `test_mesh_plughorn` (13),
  `test_mesh_build` (heavy subset, keep the 4 cheap guard tests), `test_mesh_mid_ports` (2),
  `test_mesh_build_grid_halfmodel` (8), `test_mesh_build_lecleach_rows` (8), `test_mesh_meh_step_build`
  (12), `test_mesh_build_grid_rows` (4), `test_mesh_build_grid` (8), `test_mesh_topology` (5),
  `test_cad_multicell` (5), `test_design_generators_grid_full_ring` (2), `test_design_freeform_sculpt`
  (1), `test_solve_traces::test_dof_permutations…` (1), `test_mounting` (3), `test_search_ext_throat` (1),
  `test_s1a_driver_briefs` (1), `test_gui_sandbox_explore` (preview subset), `test_bo_data` (3),
  `test_bo_proposal_validation` (1), `test_tools_analysis_geometry_effects` (10),
  `test_tools_analysis_geometry_descriptors` (4), `test_search_evaluate::…cad row…` (1).

Never mark: the closed-form physics gates, contract/schema pins, `test_mesh_pin`, `test_param_catalog`,
`test_config*`, anything asserting the three silent killers (mesh_scale, quadrants/symmetry, DI source).

The profiles written down in `AGENTS.md` (there is no Makefile; PowerShell commands):

| Profile | Command | Who runs it | Measured target |
|---|---|---|---|
| **fast** (per edit, per lane) | `pytest -m "not slow and not gpu and not crosscheck" -n 6 --dist loadscope` + single-thread BLAS env | every agent, every change | **5.9 min** |
| **ci** (the gate) | same selection, `-n 2`, no env caps | GitHub Actions | ~4 min (Phase 3) |
| **gpu** (parallel lane, fused) | `pytest -m "gpu"` | every merge, concurrent with **fast** | 3–6 min (Phase 1b) |

**Gate:** `fast` + `gpu` run counts reconcile to the collected total (no test lost, none skipped
permanently); `fast` is green with the same 4 pre-existing failures as a serial run.

> **No `slow` profile.** The 21 tests that carried `slow` were 16 duplicates of `gpu`/`crosscheck` and
> 5 real BEM solves. The marker is gone from `tests/`; the GPU lane is a **concurrent** lane, and the
> heavy CPU tests run in **fast**. Remaining time is attacked by removing re-computation, not by
> deferring tests.

### Phase 1b — Put the GPU lane on the shipping path and remove the false lock (owner-directed)

#### GPU tests: everything that can run fused, runs fused

**Measured, from this repo's own bench** (`docs/evidence/THROUGHPUT_N1_2026-11-12.md`, RTX 4060,
warm b12 per solve):

| dofs | fused ON | fused OFF | |
|---|---:|---:|---|
| ~1k | 1.273 s | 1.608 s | 1.26× |
| ~4k | **8.488 s** | 12.053 s | **1.42×** |
| ~8k | 25.015 s | **FAILS (all warm reps)** | fused-off cannot run it |

Peak VRAM: 4,900 MiB fused vs 7,499 MiB fused-off at 8k. Fused also wins at 1k and 4k. So fused is
**both the faster arm and the only arm that survives 8k** — and 154 example configs set
`cuda_fused: true`, none set false.

**The problem:** `tests/test_solve_beat.py:39` builds its module fixture as `BeatBackend("cuda")`, and
`SolveConfig.cuda_fused` defaults to `False` (`hornlab_search/config.py:83`). That file is 10 of the 14
GPU tests and it validates the **fused-off** path — the slower arm that fails at 8k. The suite is
green on a path production does not use.

Fixes, in order:
1. `test_solve_beat.py` fixture → `BeatBackend("cuda", cuda_fused=True)`; assert
   `r.meta["cuda_fused"] is True` in the first solve so a silently-unfused host fails loudly
   (`solve/beat.py:368` `_assert_cuda_fused_path` already enforces this for config-driven solves).
2. Prefer constructing test backends **from a config** (`cfg.solve.cuda_fused`) over the dataclass
   default, so tests inherit the shipping default instead of a programmatic default.
3. Keep the existing A/B guard (`test_solve_beat_fused_cuda.py`, 2 tests): it already proves fused vs
   default agree to 0.0000 dB on-axis, 0.0 deg beamwidth, `z_throat` rel 5.5e-7, and that a
   stale-host fused *request* is refused. One A/B test is enough; do not duplicate it.
4. **Drop `slow` from the four GPU files; keep `gpu`.** `gpu` means "different lane", not "run later".

Cost of the GPU lane (fused): **19 tests across 5 files** — the 14 solve/geometry tests plus the 5
CLI-level runs in `test_end_to_end.py` that used to be `slow`-only. The 14 are 13 solve calls + 4 mesh
builds (1.4k / 2.3k / 2.4k / 4.9k dofs), the solves at ~1.3–8.5 s each at the measured warm rates, plus
one cold Julia host start and one MEH end-to-end. Expected **5–10 min**, concurrent with the 5.9 min
fast lane. *Unknown until measured*: the cold host start, `test_end_to_end.py`'s 5 CLI runs and the MEH
end-to-end dominate that range; time them first, do not trust the estimate. The hours-long work is the
CP-3/CP-5/CP-7 checkpoint ladder, not these files.

Caveat to check on the first run: `test_end_to_end_meh.py` is the one that could dominate; measure it
separately and, if it is >5 min, keep only that test on the checkpoint ladder.

#### The GPU lock: advisory by default, refuse on request — APPLIED

**Correction to the first draft:** `_cmd_selftest` must KEEP the lock. It is analytic, but its
`finally` calls `worker.shutdown(verify=True)`, and a shutdown from a process that does not own the
running job's host is exactly the 2026-10-25 bug (a lock-refused selftest killed another campaign's
host). Removing the lock there would re-introduce it. That item is withdrawn.

The roadblock is real, and it is not the lock mechanism — it is the **default policy**. Applied
change in `hornlab_search/search/gpulock.py`:

- New policy knob, resolved per call: `policy` argument > `HORNLAB_GPU_LOCK` env > default.
- Values: `refuse` (old behaviour, raises `GpuBusyError`), **`warn` (new default: prints the holder
  and proceeds unlocked, never touching the holder's lock file)**, `off` (silent).
- `gpu_lock(..., policy=...)` exposed; stale-PID takeover is unchanged; reentrancy is unchanged.
- `gpu-clean` keeps its own refusal unless `--force` (it deletes processes — that one stays fatal).

Why this is safe enough to be the default: the owner explicitly accepts overlapping an interactive
solve, and `worker.live_locked_lanes` still reads the lock files as the host-ownership signal, so
hygiene does not start killing other lanes' Julia hosts. Unattended runs opt back into the old
behaviour with one env var:

```powershell
$env:HORNLAB_GPU_LOCK="refuse"   # nights, measurements, checkpoints
```

Tests: `tests/test_search_gpulock.py` keeps its three refusal cases (now passing `policy="refuse"`
explicitly) and gains four: warn-by-default (with the holder's lock left intact), `off` is silent,
env `refuse` restores the fatal path, unknown policy is rejected.

**Why not delete `gpulock.py` outright:** `search/worker.live_locked_lanes` uses the lock files as the
*ownership signal* for Julia-host hygiene. Without it, `gpu-clean` cannot tell a live lane's warm host
from an orphan and will kill it — which is the exact failure mode that produced the recorded false
OOMs.

### Phase 1b — applied changes (branch `test/testspeed-2026-11-13`)

| Change | Files |
|---|---|
| GPU solve suite runs **fused** by default | `tests/test_solve_beat.py` (`BeatBackend("cuda", cuda_fused=True)`, `_spec()` wrapper sets `SolveSpec.extra["cuda_fused"]`, `test_11` asserts `meta["cuda_fused"] is True`) |
| `spec_with(..., cuda_fused=...)` carries the flag into `SolveSpec.extra` | `tests/test_solve_support.py` |
| `slow` removed from the GPU/BEM files (kept `gpu` / `crosscheck`) | `test_solve_beat.py`, `test_solve_beat_fused_cuda.py`, `test_end_to_end_meh.py`, `test_solve_crosscheck.py`, `test_solve_traces.py` |
| `test_end_to_end.py` is a real GPU solve → `slow` replaced by `gpu` | `tests/test_end_to_end.py` |
| GPU lock default → `warn` (+ `off`/`refuse`), policy tests | `hornlab_search/search/gpulock.py`, `tests/test_search_gpulock.py` |

Not done on purpose: `test_solve_beat_fused_cuda.py` keeps its deliberate unfused first solve (it is
the A/B), and `test_solve_traces.py::test_19` stays unfused — the trace reconstruction contract was
never validated against the fused assembler and there is no GPU on this pass to prove it. Changing it
blind would be a silent-killer risk.


### Phase 2 — Remove accidental cost (≈2–4 h, ~90–150 s, zero coverage loss)

These are real inefficiencies, not "slow tests":

| Fix | File | Saves |
|---|---|---|
| Session-scope the catalog (`build_catalog(ROOT)` called 19×) | `test_param_catalog.py:137-578` | ~8 s |
| Session fixture for the 45-config CLI family table | `test_search_campaign.py:514-566` + `cli.py:1421` | ~60–90 s |
| Module-scope the mesh results reused across tests | `test_mesh_build.py`, `test_mesh_build_grid*.py`, `test_mesh_build_lecleach_rows.py` | ~20–30 s |
| Module-scope a GUI repo template, copy-on-write into `tmp_path` | `test_gui.py:54`, `test_gui_integration_phases.py:226` | ~5–10 s |
| Replace `time.sleep` polls with a `threading.Event` from `JobManager` | `test_gui.py:221,370`, `test_gui_integration_phases.py:885` | ~5 s + removes flake |
| Batch `node` calls to one process per JS module | `test_gui_verify_panel.py:56`, `test_gui_verify_table.py:57` | ~2–4 s |
| Explain/fix the 28 s setup on a "no network call" test | `test_tools_hf_sync.py:20-29` | up to 28 s |

**Gate:** per-file junit time before/after pasted; assertions untouched; no test renamed away.

### Phase 3 — CI topology — APPLIED 2026-11-13

Applied in `.github/workflows/`:

1. One trigger: `pull_request` + `push: branches: [main]` (ends the 2-runs-per-push; 122 runs in one
   day on 2026-11-12).
2. `cache: pip` on `setup-python`.
3. `paths-ignore: ["docs/**", "**/*.md", "NOTES_FOR_SENIOR.md"]` on the main job, plus a new
   `docs.yml` that runs on docs-only changes and executes `tests/test_param_catalog.py tests/test_config.py`.
4. `-n 2 --dist loadscope` in the CI test step, with the same single-thread BLAS/OpenMP env as local.
5. Required check on `main`: **not done** — that is a GitHub branch-protection setting, owner action.

**`gen_param_catalog.py --check` is deliberately NOT gated.** It fails on a clean tree today:
`docs/reference/PARAMETERS.md` carries a hand-maintained "Search-config keys" section that the
generator does not emit, so `--check` reports STALE and `--write` deletes 158 lines of hand-written
contract text. `docs.yml` documents the gap and gates the JSON byte-equality test instead. Fold the
search/brief keys into the generator, then add the `--check` step.

Remaining from the prior review: R5 (CI-as-merge-gate protocol) and R6 (required checks).

**Gate:** one PR shows before/after wall time and a green required check; total CI minutes for a week
compared against the 824-min/day baseline.

### Phase 4 — Curation with a bar (ongoing, ~1 min of speed, high maintainability value)

This is the anti-slop half. It is deliberately last, because it is the only phase with a real
regression risk, and it cannot be justified as a speed fix.

1. **Delete only what the audit proves dead.** The audit is complete (2026-11-13, read-only,
   `--collect-only` + AST resolution of all 1,829 `hornlab_search`/`tools` imports). Headline: **the
   allowed deletions are 18 tests out of 3,739 (0.5 %), worth ≈ 1 s.** There is no dead-test pool.
   The allow-list, strict and no-coverage-loss:

   | # | What | Where | Count |
   |---|---|---|---|
   | 1 | Duplicate JS `node --check` — keep `test_gui.py:398-408` (the parametrized canonical gate) and the `verify.js` contract check | `test_gui_verify_panel.py:442`, `test_gui_verify_table.py:431`, `test_gui_chart_standards.py:26,32`, `test_gui_brief_authoring.py:112-120`, `test_gui_integration_phases.py:593-601`, `test_gui_views_analysis_m1.py:225-231`, `test_gui_search_history.py:267`, `test_gui_sandbox_page.py:43`, `test_gui_param_tips.py:48`, `test_gui_verify_panel.py:451` | 12 |
   | 2 | Half-model mesh section duplicated near-verbatim; keep `test_mesh_build_grid_halfmodel.py:41-133` (stronger assertions) | `test_mesh_build_lecleach_rows.py:123-201` | 4 |
   | 3 | `resample_strict` + `cma_me` refusal duplicated; keep the dedicated module | `test_search_outcomes.py:133` | 1 |
   | 4 | Vacuous smoke: only `is not None` on a function that always returns a list | `test_tools_analysis_seed_pack.py:332` | 1 |

   Renames/trims (not deletions): `tests/test_tools_analysis_s3_cost.py` tests no `s3_cost.py` — rename
   to `test_tools_analysis_cost_ledger.py` (it is the only coverage of `_common.cost_ledger`);
   `test_config_extends.py:127` asserts a renamed profile is absent — drop that one line, keep the v7
   assertion; 4 test names in `test_objective_v7.py:102,440,448` and `test_config_objective_v7.py:165`
   still say "v5" for what became v7.

   Rule for any deletion: (a) the audit evidence above, (b) a green full run after it, (c) a CONTINUITY
   note saying what coverage moved where.

   **Two coverage holes the audit found** (neither is fixed by going faster, and both matter more than
   the 18 deletions):
   - **18 `requires_botorch` tests never run in CI or the default venv** (`test_bo_acquisition` 5,
     `test_bo_model` 5, `test_bo_propose` 7, `test_bo_sensitivity_real` 1). They only run in the
     isolated `bayes-venv`. Either add a `[bayes]` CI job or state the gap in CONTINUITY.
   - **6 tests are permanently skipped in CI** because they pin local data under gitignored `runs/` and
     `scratch/` (`test_mesh_throat_check:61`, `test_metrics_loudness:75`, `test_bo_data:224/262/278`,
     `test_tools_analysis_parameter_study:301`). Mark them `local_data` so the skip is visible by name
     rather than by accident.
2. **Merge thin files.** 83 files have <5 test functions, 9 have exactly one. Merge by subject
   (`test_gui_*` → per-view files; `test_b8_*` → `test_studies_*`; `test_tools_analysis_*` → keep, they
   map 1:1 to a tool). Do this in batches of ~10 with a green run between batches. Expect **no**
   measurable speed gain — say so in the commit.
3. **Adopt a bar for new test files**: a new file must introduce a new subsystem or a new contract;
   otherwise the test extends the module's existing file. 129 new files in 48 h is the signal that this
   bar is missing.
4. **Retire stale worktrees.** 30 checkouts × ~200 test files each is 30 copies of the suite on one
   disk, and every lane that runs tests there pays full price. Audit which branches are merged,
   archive the evidence, delete the worktree. (Owner decision; do not delete unmerged branches.)

---

## 5. Expected outcome

| Stage | Routine lane (local) | GPU lane | CI test step | Coverage |
|---|---|---|---|---|
| Today | **18 min serial, all 3,739** | not run per change | ~6–8 min serial | 100 % locally, GPU unrun |
| + Phase 0 (xdist `-n 6`) | **4–5 min** | — | unchanged | 100 % |
| + Phase 1b (fused GPU lane) | 4–5 min | **3–6 min, concurrent** | unchanged | 100 % incl. fused path |
| + Phase 1 (cost lanes) | **~2 min** at `-n 6` | 3–6 min, concurrent | ~3–4 min at `-n 2` | 100 % |
| + Phase 2 (setup fixes) | **~1.5–2 min** | 3–6 min | ~3 min | 100 % |
| + Phase 3 (CI topology) | — | — | ~4 min × ⅓ as many runs | 100 % |
| + Phase 4 (curation) | ~unchanged | ~unchanged | ~unchanged | 100 %, smaller surface |

Every test still runs. Nothing is skipped permanently; nothing is deselected that is not deselected
today. The wall-clock cost of the CPU lane is `max(fast, gpu)` because the two lanes run together, not
in sequence. Fused CUDA makes the GPU lane ~1.2–1.4× faster than the fused-off path it tests today.

---

## 6. Do not do

- Do not delete or `skip` a test to make the number smaller — not even a "suspicious" one. Delete only
  on audit evidence, and only with the full suite green afterwards.
- Do not lower `timeout = 900`, and do not add `--timeout` per test to make failures disappear.
- **Do not delete `search/gpulock.py`.** Fix the false refusals (Phase 1b, second half) but keep the lock files:
  `worker.live_locked_lanes` reads them as the ownership signal for Julia-host hygiene. Without it,
  `gpu-clean` kills live lanes' hosts and produces the documented false-OOM numbers.
- Do not run `-n` xdist workers **and** a real solve **and** the GPU lane on the same 8 GB card and
  expect clean timings; the GPU lane is measured, the rest is not.
- Do not use `-n auto` on this box.
- Do not drop the docs job's `gen_param_catalog --check` — `docs/reference/*.md` are generated.
- Do not leave the CPU-heavy `slow` tests without a lane; "moved" is only acceptable if it runs
  somewhere.
- Do not treat file consolidation as an optimization. It is hygiene.

---

## 7. Decisions needed from the owner

1. **Approve Phase 0** (add `pytest-xdist`, four `tmp_path`/lazy-import fixes, trial at `-n 6`). This
   alone is the 18 → 4–5 min win and is fully reversible.
2. **Pick the nightly slot** for the `slow` lane — the existing night queue, a GitHub scheduled job, or
   the pre-merge step. Without an answer, Phase 1 has nowhere to move tests to.
3. **Approve the agent protocol change**: lanes run the `fast` profile + CI as the gate; the full local
   suite only for shared-core changes (`config.py`, `search/evaluate.py`, `search/cma*`, `objective/**`,
   `types.py`, `dataset/record.py`) or once per merge batch.
4. **Worktree retirement**: which of the 30 checkouts are dead? (Owner-only call; this pass did not
   touch them.)
5. **Two coverage holes** (Phase 4): do we add a `[bayes]` CI job for the 18 BoTorch tests, or accept
   and document the gap? This is independent of the speed work and is the only real *safety* deficit
   found in the audit.
6. **GPU lane (Phase 1b) — APPLIED, one open call:** the GPU test backend now flips to
   `cuda_fused=True` and `test_solve_beat.py` asserts `meta["cuda_fused"] is True`; the GPU files
   dropped `slow` and keep `gpu`; the lock policy is `HORNLAB_GPU_LOCK=warn` by default
   (`refuse`/`off` by env). `_cmd_selftest` KEEPS its lock on purpose — its verified shutdown would
   otherwise kill a live job's host. **Open:** should unattended nights set `HORNLAB_GPU_LOCK=refuse`
   in the night runner itself (recommended: yes, so a typo in the shell cannot silently overlap two
   CUDA jobs)?

---

## 8. Appendix — reproduction

```powershell
# the measurement behind §1 (writes a junit; inspect with any junit reader)
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" `
    --durations=60 -q --no-header -p no:cacheprovider --junitxml=runs\integ_2026-11-13\ci_junit.xml

# per-test durations, ≥5 s
#   parse ci_junit.xml: sum of testcase@time, sort desc
# collection cost
.venv\Scripts\python.exe -m pytest --collect-only -q
```

The raw capture for this pass is at `runs/integ_2026-11-13/ci_junit.xml` (untracked local evidence,
3,739 cases / 975.8 s).

Machine: 24 logical cores, Windows, `.venv` with `hornlab_mesher`, `hornlab_beat_bem`,
`hornlab_bempp_bem`, `build123d`, `torch`, `hornlab_plots` installed (so every `requires_*` gate runs).
The capture was taken while two read-only audit lanes were also running, so absolute seconds are
slightly pessimistic; the ranking and the shares are stable against the 2026-11-12 capture.
