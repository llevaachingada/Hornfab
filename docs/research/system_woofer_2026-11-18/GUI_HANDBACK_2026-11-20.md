# GUI handback — 2026-11-20

Senior-review implementation pass on `hornfab-all-2026-11-18` (canonical checkout
`C:/Users/hunte/Hrns/hornlab-search`). Mandate:
`docs/research/system_woofer_2026-11-18/GUI_SENIOR_REVIEW_2026-11-20.md` §4 steps 1–14, in order,
staging only this lane's hunks; stop at owner gates G and H. Every rule, UX standard and handback
format in `GUI_COMPLETION_HANDOFF_2026-11-19.md` still applies.

## 1. State

- **Branch:** `hornfab-all-2026-11-18`.
- **HEAD at handback:** branch `6531663` plus this docs commit (other lanes' commits interleave);
  this lane's code HEAD was `cfa7846`.
- **Commits since the reviewed HEAD `279b072` (this lane only; other lanes' commits interleave):**
  - `9b90e25` feat(gui): horn+woofer stage/validate/solve bridge, screen and 3D views (F1)
  - `01a67b3` test(gui): make hw replay and solve-preset tests hermetic (F2)
  - `b6c9ccc` feat(gui): registry v2 with proposed evidence cases (F3)
  - `05af010` feat(gui): validated control links and LF+wide two-series payload (step 4)
  - `aa71c68` fix(gui): remove the dead clearance_m stage control (F5)
  - `ef415fa` fix(system): take the CPU lane lock for manual evidence solves (F6)
  - `be05284` fix(gui): compare recorded grids within 0.01 Hz; README matrix acceptance (step 10 backend)
  - `61582c6` feat(gui): overview R3 next-step and P6 dialog GET routes (steps 9/12 backend)
  - `5ab291e` feat(gui): locked crossover DSP preview backend (step 13 backend)
  - `99358c2` feat(gui): screen defaults reproduce the recorded 27616eed study (step 11 backend)
  - `71da083` feat(gui): readable shortlist table with grouped headers + column chooser (F9/step 8)
  - `337feaf` fix(gui): shortlist readability follow-ups (observer review)
  - `6f488b7` feat(gui): Overview page and final five-item menu (P8/step 9)
  - `8fe7fa4` fix(gui): project readiness loader accepts hw_readiness_v2
  - `fe868d2` feat(gui): New system wizard and Quick launch (P5/step 11)
  - `405d741` feat(gui): P6 stage/validate/solve dialogs + overview readability (step 12)
  - `909181c` feat(gui): Compare page + matrix and locked Crossover page (steps 10/13)
  - `cfa7846` test(gui): hw lifecycle harness + gate-H registry approvals
  - this docs commit → the handback + gate-H quote + continuity/issues/index/code-map/active-state
- **Worktree:** not clean by design. This lane committed its own GUI/system paths; the canonical
  checkout still carries other lanes' uncommitted work (`hornlab_search/config.py`,
  `objective/versions.py`, `search/evaluate.py`, `objective/scalar_v11.py`, cd_v11 evidence/queues,
  scratch JSONs) and the other-lane hunks in `app.js` (`sortRunsForTable`, beamwidth height).
  None of those were staged. Other lanes advanced the branch during the pass (`22ae1f7` v11;
  `243136d` merge; `f460398` GUI evidence/research; `6531663` source.cap evidence); `f460398`
  swept an in-flight copy of this handback and some evidence, so this final docs commit supersedes
  that draft.
- **Store:** `system_runs` is still the junction to
  `C:/Users/hunte/Hrns/hornlab-woofer-system-wt/system_runs`. The worktree is **locked**
  (`holds system_runs evidence store; do not remove`) and a verified copy is at
  `E:\hornlab-system-evidence-backup-2026-11-20` (1,424/1,424 files; identical sha256 manifests).
- **Phase order note:** P0/P1 landed before this pass; §4 steps 1–14 here replace the P6+ order in
  the 2026-11-19 handoff. P2/P3/P4/P5/P6/P7/P8 frontends are now present (see §3).

## 2. Tests (pasted, not summarized)

### Command 1 — system + all `tests/test_gui*.py` + B8 GUI (`-n 6 --dist loadscope`)

```
tests=1117 failures=1 errors=0 skipped=7 time=681.745
FAILED tests/test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths
```

- **PRE-EXISTING** (not introduced here): the review §1 recorded this exact failure at `279b072`;
  the `subprocess.Popen` line in `hornlab_search/gui/study_jobs.py` was introduced by
  `b019623 feat(gui): solve a study design and render its run views`, before this pass.
- `0` NEW failures. The two live-store coupling failures named in F2 are gone (step 2).
- Real-BL staging gate (handoff §9 command 3), after the `clearance_m` change:
  `HORNLAB_BL_REAL_TESTS=1 pytest tests/system/test_bl_stage.py -q` → **11 passed**, exit 0.

### Command 2 — full repo profile (`-m "not slow and not gpu and not crosscheck" -n 6`)

```
tests=5586 failures=7 errors=0 skipped=29 time=764.020
FAILED tests/test_targets.py::test_from_dict_round_trips_example_targets[score_identities.yaml]
FAILED tests/test_objective_v8.py::test_v8_is_registered_nowhere_and_never_changes_a_default
FAILED tests/test_objective_v8.py::test_v8_key_set_is_v4_minus_load_plus_the_extras
FAILED tests/test_tools_search_preflight.py::test_generated_history_fallback_reads_grid_knobs
FAILED tests/test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths
FAILED tests/test_dataset_manifest.py::test_manifest_census_groups_and_provenance
FAILED tests/test_queue_fable_scout40.py::test_scout40_jobs_are_budgeted_and_grouped
```

One-line causes and ownership:
- `score_identities.yaml` has no `target` block; the test glob includes it. **PRE-EXISTING**
  (`f117cbb`, Overview phase 1, before this pass).
- v8 registration/key-set and dataset-manifest `objective_versions` now include `11` because
  `hornlab_search/objective/versions.py` is modified by **another lane** (v11 registration;
  `objective/scalar_v11.py` is untracked in the same lane).
- `search_preflight` history-source test: **other lane** (`config.py` / `search/evaluate.py` are
  modified by that lane; this pass did not touch them).
- B8 host-cleanup: **PRE-EXISTING** (above).
- scout40 queue expects 18 jobs, the file now has 24 (`d6c9abd`, queue lane, before this pass).
No failure is in a file this pass changed; all GUI/system tests are green apart from the recorded
B8 exception.

### Browser checks

- Shortlist (step 8): 8/8 width×theme combinations, 0 failures, 0 console errors; before/after
  screenshots in `docs/evidence/hw_gui_2026-11-20/shortlist_{before,after}/`.
- Overview (step 9 + polish): 8/8, 0 failures; `overview/browser_report.json`.
- Wizard/Quick launch (step 11): 16/16, 0 failures; `wizard/browser_report.json`.
- Dialogs (step 12): independent Playwright check exit 0 (dialog semantics, preview, 20-Tab trap,
  Esc/focus return, 375 fit, Solve disabled + decision-6 + real lowband12 estimate, 0 job POSTs,
  0 console errors); screenshots in `dialogs/`.
- Final sweep (all routes incl. compare/crossover): **104/104 combinations, 0 failures, 0 console
  errors**; `full/browser_report.json`. One intermediate run hit a transient
  `ERR_CONNECTION_FAILED` on the matrix page at 768 dark; that combination passed on a single rerun
  and the entire sweep then passed cleanly.
- Keyboard-only story: **14/14 steps**, 0 console errors; `keyboard/keyboard_report.json`.
- Lifecycle harness: `node tests/gui_hw_lifecycle.mjs` → `hw GUI lifecycle ok`, exit 0;
  `pytest tests/test_gui_hw_lifecycle.py -q` → 1 passed.

Note: the venv lacks `playwright`; browser checks use
`C:\Users\hunte\AppData\Local\Programs\Python\Python313\python.exe tools\gui\browser_check.py`.
The GUI itself runs under `.venv\Scripts\python.exe`.

## 3. Step checklist (§4 of the senior review)

1. **HEAD consistency (F1)** — DONE. `gui/data_hw_stage.py`, `tests/system/test_gui_hw_stage.py`,
   `tools/system/gui_system_job.py`, `hw3d.js`, `hw_screen.js`, `hw.js`, `app.css`, `glossary.js`,
   `index.html`, `browser_check.py` committed; scratch `git archive HEAD` import + hw tests green.
   app.js staged hunk-wise: hw import/routes/nav only; `sortRunsForTable` and beamwidth-height hunks
   left for their lane. docs/INDEX/CODE_MAP had no hw hunks at step 1, so none were staged.
2. **Hermetic tests (F2)** — DONE. Replay test asserts the committed pair is grouped and all members
   sha256-identical (>= count, no exact count); solve-preset test uses a tmp_path store plus a live
   store case that asserts lowband12 is now available. Acceptance: a temp store with a third dummy
   replay still groups 3 byte-identical members.
3. **Registry v2 + evidence entries (F3)** — DONE. `data_hw.load_registry` accepts v1/v2, reads only
   `cases.d/*.yaml` inside the registry folder, reports duplicate keys and drops ambiguous keys from
   the declaration map. The 9 handoff entries moved verbatim to `cases.d/00_handoff_2026-11-19.yaml`
   as approved; **16** evidence cases are proposed in `cases.d/10_evidence_2026-11-19.yaml`; R3/R5/R6
   are in_progress, R4 closed for the 2×2 wide matrix, each with a README evidence link. The project
   readiness merge (`data_overview_registry.py`) now accepts v2 (test fix).
4. **Control links + chart (§3.2/§3.3)** — DONE. Declared `lf/wide/dense/farfield/mesh_refine` links
   are validated server-side; failures show `CONTROL_LINK_INVALID[reason]` and are ignored.
   `hw_control_summary` computes the sampling number in Python (#2: 0.033 dB at 25 shared points).
   `hw_basis` returns the LF solve as a separate `overlays[]` array; the Response tab draws two
   series with a gap at 200 Hz, never a concatenated/merged array. A staged-only case with a `wide`
   control serves that solve as its base series and says so.
5. **Owner gate G** — ASKED AND ANSWERED (see §4); lock + verified backup executed.
6. **`clearance_m` (F5)** — DONE. Removed from `stage_options`; `stage_argv` refuses the field with
   “clearance: fixed at the R16 1 mm minimum; not a stage argument”; test added.
7. **CPU-lane lock for manual evidence solves (F6)** — DONE. `evidence_case.py --solve` enters
   `cpu_lane_lock("evidence_case <experiment>")` around `reference.solve`; a live holder under
   `refuse` returns 1 with “CPU LANE BUSY: … <holder>”; test uses a temp runs/ dir. The CPU lane's
   `--motor-patch` work was committed by that lane (`c06ddb4`) before the edit; no bypass added.
8. **Shortlist table (F9)** — DONE. Seven default columns under a grouped header, full-word headers
   with `tip()`, URL-persisted `?cols=` chooser, one sort glyph, sticky Driver column, prominent
   scroll banner, 375 card note; observer follow-ups fixed. Before/after evidence committed.
9. **P8 Overview + final menu** — DONE. `#/hw` on `/api/hw/overview` with KPIs, seven-step story,
   server-computed next step (R3 bassbox audit links to Readiness), recents and readiness summary;
   five-item menu; route/nav wired. Overview review defects (KPI slab, table clipping, label wrap,
   copy) fixed and re-checked.
10. **P4 Compare page** — DONE. `hw_compare.js`: solved-case pickers + Swap, the five quick-pick
    pairs (four README matrix pairs + G6), verbatim refusal tokens with no charts, on-axis
    whole-grid maxima, what-changed, per-probe/excitation ratio + Δphase charts, band tables and
    the 2×2 matrix with cells/edges. DOM check confirms the four README values (8.58@1641,
    22.25@1641, 23.64@1823, 21.28@1641) and the matrix; backend acceptance in `be05284`.
11. **P5 wizard + Quick launch** — DONE. `hw_new.js` + routes; 4-step Guided and Quick launch;
    initial inventory limit 40 (1.4 s) + user-triggered limit 200 load-all; identity test pins
    `27616eedee09009f` from the committed spec + asset + 4 drivers (and `DEFAULT_LIMIT_BOXES` is 8
    to match the recorded screen).
12. **P6 dialogs** — DONE. Stage (shortlist/case, preview, clearance verdict), Validate, disabled
    Solve with decision-6 reason and real presets, live “Check in Boundary Lab…”; independent
    Playwright check exit 0; no real job launched.
13. **P7 Crossover (locked)** — DONE. `hw_dsp.js` + `POST /api/hw/dsp-preview`: disabled
    spec-default controls, per-channel filtered SPL/phase curves (never summed), wrapped/unwrapped
    toggle, verdicts, locked System sum panel with decision-3/R1, permanent captions; a woofer-only
    run shows one channel and says the other is absent. Backend/no-combine test in `5ab291e`.
14. **QA + handback** — DONE. Final browser sweep **104/104** (13 routes × 4 widths × dark/light),
    keyboard-only story **14/14 steps** with 0 console errors, hw lifecycle harness
    (`tests/gui_hw_lifecycle.mjs` + pytest wrapper) green, this file and the docs/CONTINUITY/ISSUES
    updates committed.

## 4. Owner gates

- **B (screens + spec save):** answered 2026-11-19, exact: **"Yes to both (Recommended)"**.
- **C (stage + validate):** answered 2026-11-19, exact: **"Yes (Recommended)"**.
- **D (solve approval, decision 6):** **open**. Solve dialog visible but disabled with the
  decision-6 reason; no GUI solve is authorized.
- **E (calibration policy, decision 3):** **open**. Crossover per-channel curves only; the system
  sum panel is locked with the decision-3/R1 reason.
- **F (frozen contract / install change):** not triggered; `docs/plan/**` and `01_CONTRACTS.md`
  untouched; no BL/BEAT install change.
- **G (store durability):** answered 2026-11-20, exact:
  > "Gate G: yes to both. Lock the woofer worktree and back up system_runs to
  > E:\hornlab-system-evidence-backup-2026-11-20, following GUI_SENIOR_REVIEW_2026-11-20.md
  > section 8.3 (copy from the physical path, robocopy /E not /MIR with /XJ, sha256 manifest of
  > source and destination must match, after the CPU lane lock is released). Quote this answer in
  > CONTINUITY."

  Executed: worktree locked; `robocopy /E /XJ` from the physical path; 1,424/1,424 files; source
  and destination sha256 manifests both
  `06d1e55a2155c72528deb3e33e8dee0b07de322ddc9c7c273c7ac30b79d6fd02`. The review has no §8.3;
  the written method in the answer was followed exactly.
- **H (proposed registry entries):** answered 2026-11-20, exact:
  > "Approve the 11 README-covered".

  Applied: those 11 entries are `status: approved`, `approved_by: owner 2026-11-20`; the 2 WP3
  assembled real-motor cases and 3 mesh-refinement controls remain `proposed` (greyed + chip).
  The committed-registry test now expects 20 approved / 5 proposed.

## 5. Deviations from the handoff/review

1. **Playwright interpreter.** `tools/gui/browser_check.py` runs under Python 3.13 (the venv lacks
   `playwright`). The GUI server still runs under `.venv\Scripts\python.exe`. Recorded so the senior
   uses the same command.
2. **Compare grid tolerance.** The two README box pairs store the same 25-point grid rounded
   differently (222.2 vs 222.195 Hz). `data_hw_compare._first_diff` now allows 0.01 Hz; lengths and
   endpoints still have to match, so a real grid change still refuses. This was required by step 10's
   acceptance numbers; the P4 refusal rule is otherwise unchanged.
3. **Screen default `limit_boxes` 4 → 8.** The recorded `27616eedee09009f` study used `--limit-boxes
   8 --shortlist-size 6`; the GUI default was 4, which would have produced a different id. Step 11's
   identity test now passes with the GUI defaults. `shortlist_size` was already 6.
4. **`wide` control on a staged-only case.** The review's lf/dense/farfield rule compares two run
   manifests; a staged case has no run. For those cases the link is validated against the **staged
   project_sha256** (the same project identity the linked run records). This is what makes #6/R0
   usable before their own solve; it is a deliberate extension, not an inferred link.
5. **Empty `ev_mesh_refine/…52652` directory.** It has no `case.blab.json` and no manifest; it is
   counted under the GUI's empty state and is not declared in the registry (there is nothing to
   label).
6. **`tools/data/system_cases.py`** still validates `hw_readiness_v1`; it will report a schema error
   against the v2 registry until updated. It is a read-only census/export tool outside the GUI; left
   for its owner (see §7).
7. **Other-lane hunks.** `app.js` (`sortRunsForTable`, beamwidth height) and
   `docs/INDEX.md`/`CODE_MAP.md` (cd_v11/system-evidence lines) were left unstaged throughout.
8. **The CPU evidence lane committed while this pass ran.** `c06ddb4 feat(system): real-motor
   assembled + mesh-convergence evidence` landed between steps 2 and 3; step 7's lock wraps that
   lane's committed motor-patch path additively.
9. **No real GUI stage/solve was launched.** The stage dialog's preview and the real-BL staging suite
   (11 passed) cover staging; the Solve button stays disabled by gate D. The handoff §6 P6 real-stage
   acceptance should be re-run by the senior if a live case dir is wanted.

## 6. NEEDS_SENIOR_REVIEW

### New endpoints

- `GET /api/hw/stage-options`, `/solve-presets`, `/authorization` (`server.py::_hw`) wrap
  `data_hw_stage` readers. **stage-options** lists only `system/ref_case/horn_full/*/mesh.msh` inside
  the store and parses the mesh's own 2D groups; **solve-presets** reads run manifests only;
  **authorization** is env + a recorded decision-6 record and is always false while decision 6 is
  open. No write path exists in any of them.
- `POST /api/hw/dsp-preview` validates a DSP point against the committed example spec's ranges, then
  returns per-channel filtered arrays + `validate_dsp_point` verdicts + a locked-sum panel. It never
  imports or calls `combine`; the test monkeypatches `combine()`/`recombine_with_dsp()` to raise.
- `GET /api/hw/compare` still has no top-level `frequencies_hz`; the Compare page reads the grid
  from `/api/hw/basis/<a>?domain=<probe>` (one extra GET) and degrades to the maxima/band tables if
  that call fails. `compare-matrix` returns the three consecutive 2×2 edges; the page fetches the
  closing box pair from `/api/hw/compare` separately. Both are candidates for a future API fold-in,
  not correctness gaps.
- `POST /api/hw/spec/save` was already present; the misleading “no writes” comment was corrected.
  It is the only GUI-written file (`examples/systems/user/`), parser-validated, name-regex +
  containment + overwrite-guarded.

### New/changed job kinds

- `hw-stage`, `hw-validate`, `hw-solve` (`gui/jobs.py`) are CPU-only, use
  `tools/system/gui_system_job.py`, refuse a second system job, read (never take) the CPU-lane
  marker, and are range/enum-checked in `data_hw_stage`. The solve kind is additionally gated by
  `authorization_state`; the UI exposes it disabled.
- Cancellation: the existing JobManager path is used unchanged; the new kinds do not add a kill
  path. A stage job that is cancelled mid-BL leaves the case dir; the immutable-case model is
  unchanged.

### Where numbers are derived (Python, never JS)

- `data_hw._dense_delta` — max |dB| at shared/nearest point-probe frequencies; #2 reports 0.033 dB
  at 25 points (README 0.03). It uses the same excitation id/per_input/reference matching as the
  overlay rule.
- `data_hw_compare._whole_grid` / `_band_rows` — `max_abs_ratio_db` and `max_abs_ratio_at_hz`
  (20log10 |p_a/p_b|), plus the recorded-evidence `max_relative_delta_percent`. The README matrix
  test pins 8.58/22.25/23.64/21.28 dB at 1641/1641/1823/1641.
- `woofer_seed` — `study_id` from the canonical input dict; the P5 test reconstructs
  `27616eedee09009f` from the recorded study + committed spec + asset + 4 drivers.
- `data_hw.overview_next_step` — R3 (in_progress + “bassbox” evidence + a solved case) outranks
  Compare and links to Readiness; otherwise the order is new → stage → compare → read → solve →
  screen.
- `hw_control_summary` — the only control number shown; no JS arithmetic.

### Near-sum / inference review points

- `hw_basis` overlays: main and LF arrays are separate (`overlays[0].excitations`), never
  concatenated. The chart draws them as two series with a gap.
- `data_hw_dsp`: per-channel filtered arrays only; the payload has no `p_total`/sum/combined data
  key; the locked panel is a value (`panel: "system sum"`), not a curve.
- Registry: labels come only from `cases.d`; proposed entries are greyed + chipped; a missing key is
  `UNDECLARED`; a duplicate key is an error and is dropped from the declaration map. The GUI never
  infers fidelity/motor/shape.
- `hw_assets`/`hw_drivers`/`hw_spec_defaults`/`hw_specs` are read-only; the asset inventory is
  bounded by the requested run limit (40 initial, 200 on demand).

### Caching

- `data_hw._CACHE` (64) is keyed by the registry file + every `cases.d/*.yaml` stamp; a new/changed
  case file invalidates it. `_ASSET_CACHE` (8) is keyed by the runs/system dir mtimes and the limit;
  the first 200-asset scan is 30 s cold (hence the 40-first wizard), 0.6 s warm.
- `data_hw_screen`/`data_hw_compare`/`bl_results` caches are keyed by the relevant file stamps; no
  unbounded per-case cache was added.

### Not verified in the browser / open verification

- No real `hw-stage`/`hw-validate`/`hw-solve` job was launched from the GUI. The dialog preview,
  argv validation, backend tests and the real-BL staging suite are green; a live GUI stage is the
  remaining acceptance (handoff §6 P6).
- The P5 Launch button was not used against the live store (the wizard preview/identity is tested).
- The 3D tab was reviewed at G0/review time; the new lifecycle harness
  (`tests/gui_hw_lifecycle.mjs` + `tests/test_gui_hw_lifecycle.py`) now mounts every hw view,
  exercises the real 3D 2-D fallback, runs the `[data-v3d]` dispose sweep, and checks 10
  mount→dispose cycles for listener/observer/timer growth. It does not measure WebGL
  `renderer.info` (the browser has no 3D context in the harness); the Three.js viewer is unchanged
  from the reviewed G0/P3 build.
- Light/dark and 375/768/1009/1280 sweeps cover every page: final **104/104**, 0 failures.

### Step 1 hunk decisions

- `app.js`: staged only the hw import/routes/nav hunks. Left unstaged: the `sortRunsForTable` hunk
  and the two beamwidth-height hunks (another lane).
- `docs/INDEX.md` / `docs/CODE_MAP.md`: their working-tree hunks were cd_v11/system-evidence, not
  hw; none staged at step 1. This pass adds its own lines in the handback commit, staged hunk-wise.
- `tools/system/evidence_case.py` / `tests/system/test_evidence_case.py`: the CPU lane's
  motor-patch work landed as `c06ddb4`; step 7's lock hunk was committed separately.

### CPU lane coordination

No CPU-lane lock or solve process was live at the step 7 edit, at the gate-G copy, or at the final
tests. The lane committed its motor-patch work (`c06ddb4`) while this pass ran; its README/evidence
docs were left to that lane (including the F8 “no bassbox conclusion” contradiction). The manual
`evidence_case --solve` now takes the same marker as a queued night.

### No GPU

No step took or touched `runs/.gpu.lock`, ran `gpu-clean`, or killed a process by image name. All
solves referenced here are CPU (`beat_cpu`) or already-recorded GPU evidence read-only.

## 7. Known issues left open

- `tools/data/system_cases.py` still expects `hw_readiness_v1`; the census export will report a
  schema error against v2 until its loader gains the v2 branch (read-only tool, not the GUI).
- CPU evidence README (F8): the “Not established / no bassbox conclusion” paragraph contradicts its
  own bassbox section; the CPU lane owns that file.
- `ev_mesh_refine/20261120T145909Z-assembly-52652-a14fe6ac` is an empty directory (no manifest);
  hidden by default and counted as empty, not declared.
- Pre-existing B8 host-cleanup test failure (`subprocess.Popen` in `gui/study_jobs.py`, from
  `b019623`); unchanged.
- Global frame defects observed on hw screenshots but not introduced by this pass: the sidebar
  wordmark is clipped at 1280/1009/768, and the 375 collapsed nav shows “Overview” twice (Results
  and Horn + woofer) with group labels hidden. Not fixed here (shared frame, not the hw views).
- Full-profile failures from other lanes (v11 registration, score_identities, scout40 queue,
  search_preflight) are listed in §2 with ownership; this pass did not touch those files.
- `docs/INDEX.md` / `CODE_MAP.md` other-lane hunks remain unstaged; this pass adds its own lines in
  the handback commit.
- Gate H approved the 11 README-covered evidence entries; the 2 WP3 assembled real-motor cases and
  3 mesh-refinement controls intentionally remain `proposed` (greyed + chip) until their readouts.
- The Compare page makes two extra GETs (the grid basis + the closing 2×2 pair); the data is the
  same API data, not a second computation.

## 8. Evidence index

- `docs/evidence/hw_gui_2026-11-20/shortlist_before/` — shortlist before (8 screenshots + report).
- `docs/evidence/hw_gui_2026-11-20/shortlist_after/` — after + chooser/scrolled/375 card evidence.
- `docs/evidence/hw_gui_2026-11-20/overview/` — Overview (8 screenshots + report, refreshed).
- `docs/evidence/hw_gui_2026-11-20/wizard/` — New system/Quick launch (16 screenshots + report).
- `docs/evidence/hw_gui_2026-11-20/dialogs/` — stage/solve dialogs (7 screenshots + Playwright
  check output in the session log; the script lives in the temp workspace).
- `docs/evidence/hw_gui_2026-11-20/sweep1/` — first full sweep (72/72, superseded).
- `docs/evidence/hw_gui_2026-11-20/full/` — final sweep: 13 routes × 4 widths × dark/light
  (104 screenshots + `browser_report.json`, 0 failures).
- `docs/evidence/hw_gui_2026-11-20/keyboard/` — keyboard-only story report (14 steps, 0 console
  errors) + final Overview screenshot.
- `docs/evidence/hw_gui_2026-11-20/compare/`, `.../crossover/` — DOM-check screenshots of the
  Compare maxima/matrix and the locked Crossover page.
- JUnit XML: `C:\Users\hunte\AppData\Local\Temp\opencode\hw_final1b.xml` (command 1),
  `C:\Users\hunte\AppData\Local\Temp\opencode\hw_full.xml` (command 2). These are temp paths; the
  counters are pasted in §2.

**Handback ready for the senior review session:**
`docs/research/system_woofer_2026-11-18/GUI_HANDBACK_2026-11-20.md` at the commit that adds this
file.
