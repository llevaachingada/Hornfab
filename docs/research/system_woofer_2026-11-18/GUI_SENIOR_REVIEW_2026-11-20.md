# Senior review + next-phase handoff — Horn + woofer GUI (2026-11-20)

**For:** the local orchestrator (single integrator) on `hornfab-all-2026-11-18`, canonical
checkout `C:/Users/hunte/Hrns/hornlab-search`.
**Supersedes:** the phase order in `GUI_COMPLETION_HANDOFF_2026-11-19.md` from P6 on. Every rule,
UX standard and handback format in that file still applies unless this file overrides it.
**Reviewed state:** HEAD `279b072` plus the hw lane's uncommitted files (last touched 2026-11-19
09:50; the lane stopped without a handback). No code was changed by this review.

Do the work in the order of §4. Each step lists files, the exact change, and an acceptance check.
Lines marked **ANNOTATION** explain the reasoning so you can make the right call when the code
has moved since this review.

---

## 1. What was verified

| Check | Result |
|---|---|
| Tests: `tests/system` + `tests/test_gui*.py` + `test_b8_lanes_bounded_gui.py` (`-n 6 --dist loadscope`) | **1095 tests, 3 failures, 0 errors, 7 skipped** (env-gated real-BL). Failures: 1 pre-existing (`test_b8…host_cleanup…`); 2 new, both live-store coupling (F2). |
| Browser at 1280×900, private instance on port 8823 | `#/hw/cases`, `#/hw/case/…` (all 5 tabs), `#/hw/screens`, `#/hw/screen/27616eedee09009f`, `#/hw/readiness`: no console errors, no page overflow, no stretched chart, every chart labelled, no `<h1>`. The 3D tab renders the 62864 case with the 3.0 mm overlap shown. |
| Missing pages | `#/hw` (Overview), `#/hw/new` (wizard), `#/hw/compare` show "Unknown view". There is no crossover page and no stage/validate/solve dialog. |
| Non-negotiables (grep + read) | No channel summing anywhere (`combine`/`recombine`/`filter_bank` unused in hw code); no dB/log math in hw JS; spec save is name-regex + containment + overwrite-guarded; solve needs the env flag **and** a recorded decision 6; GUI `hw-*` jobs refuse when `runs/.cpu.lane.lock` is held. |
| Owner gates | B and C answered "Yes (Recommended)" (CONTINUITY 2026-11-19). D (solve approval) and E (calibration) are still open. |

The work is good overall: the backends for P2–P5 and P8 are careful, tested and honest
(refusal tokens, recorded-number reproduction, Python-only math). The problems are integration
hygiene, data growth the GUI didn't anticipate, and the missing frontends.

---

## 2. Findings (most severe first)

**F1 — BLOCKER. `hornfab-all` HEAD is inconsistent.**
- Committed `gui/jobs.py:390-398` imports `gui/data_hw_stage.py`, which is **untracked**, as is
  its test `tests/system/test_gui_hw_stage.py`.
- `tools/system/gui_system_job.py` has the stage/validate/solve verbs only in the working tree.
- A clean checkout raises `ModuleNotFoundError` on any `hw-stage`/`hw-validate`/`hw-solve`
  preview or launch.
- *Fix:* step 1.

**F2 — HIGH. Two tests assert the live, growing data store.**
- `test_gui_hw_screen.py:124` expects `replay_count == 2`; the evidence queue added a third
  replay.
- `test_gui_hw_stage.py:303` expects no low-band runs; 5 now exist.
- Every new CPU solve turns them red. That violates "never weaken a test" from the other side:
  the tests are wrong, not the code.
- *Fix:* step 2.

**F3 — HIGH. Registry stale; 11 new solved cases show `UNDECLARED`.**
- The CPU evidence queue (`docs/evidence/system_evidence_2026-11-19/README.md`) solved:
  - LF 20–200 Hz on five projects;
  - both default-box wide cells, so the motor × box matrix is **4/4**;
  - a 10 m far-field control;
  - a 49-frequency control;
  - since that readout, `ev_mesh_refine/…35700`, `ev_assembled_motor_real/…01612`,
    `ev_assembled_motor_real_lf/…32036` and `ev_mesh_refine_dense/…40968` (15:00–15:13 UTC
    today, while this review ran). **The CPU lane is live:** expect more `ev_*` dirs. List them
    at step 3 time instead of trusting this list.
- `readiness.yaml` still lists R3, R4, R5 and R6 as `open` with no evidence, and the GUI cannot
  link a case to its LF, dense, far-field or refinement control. So the case page still says
  "LF not solved" and "convergence unchecked" for projects whose controls exist.
- *Fix:* steps 3–4 (registry v2).

**F4 — HIGH. The only copy of the evidence store lives inside a git worktree.**
- `hornlab-search/system_runs` is a **junction** to
  `hornlab-woofer-system-wt/system_runs`.
- Every manifest holds absolute paths into the worktree.
- That branch is now merged, so the worktree looks disposable to any cleanup tool; removing it
  deletes all sha-pinned BL evidence.
- *Fix:* step 5 (owner gate G).

**F5 — MEDIUM. A dialog control that does nothing.**
- `data_hw_stage.py:406-407` validates `clearance_m` (range `0.0`–`0.05`, line 78) and
  `stage_options` offers it (line 324), but it is never forwarded: the CLI always uses the 1 mm
  default.
- A lower bound of 0.0 would also allow a zero gate if it were ever wired.
- *Fix:* step 6.

**F6 — MEDIUM. Manual evidence solves bypass the CPU-lane lock.**
- `tools/run_campaign_night.py:1738-1747` holds `.cpu.lane.lock` for queued nights, but
  `tools/system/evidence_case.py --solve` run by hand (the LF retry was manual) takes no lock.
- So a GUI `hw-*` job can start beside it.
- *Fix:* step 7.

**F7 — MEDIUM. Frontends missing for finished backends.**
- P4 compare (`/api/hw/compare`, `/compare-matrix`), P5 wizard (`/assets`, `/drivers`,
  `/spec-defaults`, `/specs`, `POST spec/validate|save`) and P8 overview (`/api/hw/overview`)
  have no pages.
- P6 has no dialogs, and no GET routes for stage options, solve presets or authorization state.
- P7 has nothing at all.
- The menu lacks Overview and New system.
- *Fix:* steps 9–13.

**F8 — LOW.**
- `server.py:659` comment says "no writes", but the same branch serves `spec/save`, which
  writes. Fix the comment.
- The evidence README's "Not established" list says "No bassbox-vs-BL conclusion yet", which
  contradicts its own bassbox section. It also says "No convergence", which the new
  `ev_mesh_refine` run may change. The CPU lane owns that README: leave it to them and note it
  in your handback.

**F9 — LOW (UX). The screen shortlist table is too dense.**
- It has 14 columns with two-line abbreviated headers.
- The owner has called the hw visuals hard to read twice.
- *Fix:* step 8.

---

## 3. Architecture going forward

### 3.1 Registry v2: declarations stay human, but proposals come from the tool that made the case

**ANNOTATION:** the GUI must never infer fidelity or motor (rule 3). But hand-editing one shared
YAML after every queue doesn't scale, and it is why F3 happened. So split *proposal* from
*approval*:

```
docs/research/system_woofer_2026-11-18/
  readiness.yaml          schema hw_readiness_v2: risks, decisions, and `case_files: [cases.d/*.yaml]`
  cases.d/
    00_handoff_2026-11-19.yaml     the 9 existing entries, moved verbatim
    10_evidence_2026-11-19.yaml    the ev_* entries (step 3)
```

- Each case entry gains:
  - `status: proposed | approved`;
  - `proposed_by` (tool or agent);
  - `approved_by` (owner or senior, a quote or commit);
  - `controls:` (below);
  - `evidence: <doc>#<anchor>`.
- The GUI shows `proposed` entries with a **"proposed"** chip and the label greyed. It shows
  approved labels normally. A missing entry is still `UNDECLARED`.
- **Loader rules** (`data_hw.load_registry`):
  - accept v1 and v2;
  - glob only `cases.d/*.yaml` inside the registry folder;
  - a duplicate `key` across files is an error shown on Readiness, never a silent override.

### 3.2 Control links: what a case's placeholders really mean

```yaml
- key: bl_smoke_wide/20261118T231115Z-g4wide-56836-b5d6490a
  controls:
    lf:          ev_lf_assembled_demo/20261120T051458Z-lf_20_200-35104-5973f4ef
    dense:       ev_dense_g4_49/20261120T052433Z-dense_49-50100-30d7ef04
    farfield:    ev_farfield_g4_10m/20261120T051941Z-farfield_10m-10828-d72876e6
    mesh_refine: ev_mesh_refine/20261120T145915Z-assembly-35700-6860289b   # only if it passes the mesh_refine rule below (unverified)
```

**Server-side validation** (`data_hw._placeholders`): a control link counts only if **all** of
these hold. A failed link shows a `CONTROL_LINK_INVALID[<reason>]` token and is ignored.

- The linked case is solved (`run/manifest.json` status complete).
- For `lf`, `dense` and `farfield`, the two **run** manifests have the same `project_sha256`.
  **Verified 2026-11-20:** `ev_*` case manifests have *no* top-level `project_sha256`; they record
  `source_case` (an absolute path) instead, and the project hash is in each `run/manifest.json`.
  Compare run-manifest hashes. Show the declared `source_case` as provenance, but do not trust it
  alone.
- For `mesh_refine` (a new staging by definition, e.g. `ev_mesh_refine/…35700` has its own
  project): the linked case's `spec.source` and `spec.horn` equal the source's, except
  `mesh_size_m`/`detail_size_m`.

Placeholder wording then changes:
- `LF_NOT_SOLVED` becomes "Low band solved separately: <link>".
- `CONVERGENCE_UNCHECKED` splits in two:
  - "Frequency sampling: control <link> (max 0.03 dB at shared points)";
  - "Mesh refinement: <link | not run>".

  The numbers come from a small Python summary (`hw_control_summary`), not JS.

**ANNOTATION:** this keeps "never infer" intact. A human or tool declares the link, and the
server only checks that the declaration is physically consistent.

### 3.3 LF and wide on one chart, never one curve

When a case has an `lf` control, the Response tab plots both solves on one frequency axis as two
**separate series with a visible gap** at the seam (~200 Hz). The legend says "LF solve" and
"wide solve", and a caption says they are two solves of the same project. The data are never
concatenated in Python or JS. Only same-channel, same-reference, same-probe-id overlays are
allowed (reuse the P1 overlay refusal).

### 3.4 Durable store (owner gate G)

- **Short term:** `git worktree lock --reason "holds system_runs evidence store; do not remove"
  C:/Users/hunte/Hrns/hornlab-woofer-system-wt` plus a verified backup copy (robocopy /MIR to a
  path the owner chooses; compare file counts and a sha manifest).
- **Long term (not this round):** a store-level `STORE_LOCATION.json` path-remap that
  `bl_results`/`data_hw` apply when reading old absolute paths. Old manifests are immutable and
  never rewritten.

### 3.5 Hermetic tests

- **Unit tests** use `tmp_path` stores built from committed fixtures (as `test_gui_hw.py` does).
- **"Live store" tests** may only assert:
  - facts frozen by an immutable case key (e.g. "case X has 25/25 complete");
  - recorded numbers of specific case dirs;
  - `>=` lower bounds on counts.

  They never assert equality on counts that grow. They skip when the store is absent.

---

## 4. Work order

Commit after each step with conventional `gui`/`system`/`docs` scopes. **Push rule:**
CONTINUITY + ISSUES in the same commit. Only stage your own paths: the canonical checkout also
carries other lanes' uncommitted work (`config.py`, `objective/*`, `search/evaluate.py`,
`metrics/cd.py`, `scalar_v11.py`, cd_v11 docs, scratch JSONs). Never stage or stash those.

1. **Make HEAD consistent (F1).**
   - Stage exactly: `gui/data_hw_stage.py`, `tests/system/test_gui_hw_stage.py`,
     `tools/system/gui_system_job.py`, and (if they belong to the hw lane, per the diff)
     `gui/static/{hw.js,hw3d.js,hw_screen.js,app.js,app.css,glossary.js,index.html}`,
     `tools/gui/browser_check.py`, `docs/INDEX.md`, `docs/CODE_MAP.md`.
   - Diff each one first. Commit hunks that are hw work; leave any other lane's hunks unstaged
     (`git add -p`).
   - Acceptance: `git stash -u` on a scratch clone of HEAD (or `git worktree add` **only if the
     owner allows**; otherwise `git archive HEAD | tar -x` into the scratchpad), then
     `python -c "import hornlab_search.gui.data_hw_stage"` passes and `tests/system/test_gui_hw*.py`
     run green there.
2. **Hermetic tests (F2).**
   - Rewrite `test_live_replays_group_and_are_byte_identical` to assert the replay group
     contains at least the two committed replay dirs and that all members are byte-identical.
   - Rewrite `test_solve_presets_are_sourced_from_the_recorded_runs` against a `tmp_path` store
     (no low-band run → estimate unavailable), plus a live-store case that asserts the
     `lowband12` estimate becomes *available* now that LF runs exist.
   - Acceptance: both green, and they stay green after adding a dummy case dir to a temp copy.
3. **Registry v2 + evidence entries (F3, §3.1).**
   - Implement the loader (v1/v2, `cases.d/` glob, duplicate-key error) with tests.
   - Move the 9 entries to `cases.d/00_*.yaml` as `approved` (`approved_by: senior review
     2026-11-19`).
   - Write `cases.d/10_evidence_2026-11-19.yaml` with every `ev_*` case as `status: proposed`.
     Take the motor, shape and fidelity values *verbatim from the evidence README table and
     intro*: #4/#6 real T/S, #5/R0/#2 demo, all demo shape. Every entry cites its README row.
   - Mark the two failed `ev_lf_motor_real` attempts with `note:` from the README.
   - Update risk statuses with evidence links:
     - R3 → `in_progress` (LF solved; bassbox model-difference audit open);
     - R4 → `closed` for the 2×2 wide matrix (README table);
     - R5 → `in_progress` (10 m control: 1.38 dB max);
     - R6 → `in_progress` (dense control done; mesh refinement pending readout).
   - **Owner/senior approval of the proposed entries happens at handback, not by you.**
4. **Control links (§3.2, §3.3).**
   - Add `controls:` from each `ev_*` case's own `source_case` field (verified mapping
     2026-11-20). Map it to the source *key*, never compare absolute paths:

     | Source | `lf` | other controls |
     |---|---|---|
     | #4 | `ev_lf_motor_real/…30640` (the two earlier attempts are not controls) | — |
     | #5 | `ev_lf_demo_twin/…23196` | — |
     | #6 | `ev_lf_default_real/…45416` | `wide`: `ev_wide_default_real/…46632` (#6 was staged-only; this is its wide solve) |
     | R0 | `ev_lf_default_demo/…01448` | `wide`: `ev_wide_default_demo/…36092` |
     | #2 (`bl_smoke_wide`) | `ev_lf_assembled_demo/…35104` | `dense`: `ev_dense_g4_49/…50100`; `farfield`: `ev_farfield_g4_10m/…10828` |

     `ev_mesh_refine/…35700` → `ev_mesh_refine_dense/…40968` is its own dense control.
     `ev_assembled_motor_real{,_lf}` derive from `bl_horn_assembly/…11000` (the #1/#2 project)
     with a patched motor: they are a **new motor-axis case pair**, not controls of #2.
   - Add a `wide` control kind next to `lf`/`dense`/`farfield`/`mesh_refine`: it fills a
     staged-only case's Response tab from its declared wide solve.
   - Implement validation, placeholder wording, `hw_control_summary`, and the two-series LF+wide
     chart.
   - Tests:
     - a valid link changes the placeholder;
     - a link to a different `project_sha256` gives `CONTROL_LINK_INVALID`;
     - a link to an unsolved case gives `CONTROL_LINK_INVALID`;
     - the chart payload carries two series, never one merged array.
5. **Owner gate G (F4, §3.4).** Ask: "The only copy of the BL evidence store is inside the
   woofer worktree (`system_runs`, junctioned into the main checkout). May I `git worktree lock`
   it and make a verified backup to <path>?" Do nothing destructive. Quote the answer in
   CONTINUITY.
6. **`clearance_m` (F5).** Recommended: remove it from `stage_options` and the dialog, and refuse
   the field in `stage_argv` with "clearance is fixed at the R16 1 mm minimum". Alternatively,
   add `--min-clearance-m` to `reference prepare`, forward it to
   `stage_horn_project(min_clearance_m=)`, and set the lower bound to `1e-3` (never 0). The CLI
   and `system/` are not GUI files, so the alternative needs a `NOTES_FOR_SENIOR.md` entry and
   your ownership of `system/cli.py`; prefer the removal. Add a test either way.
7. **Lock manual evidence solves (F6).** In `tools/system/evidence_case.py`, wrap the `--solve`
   path in `hornlab_search.search.gpulock.cpu_lane_lock(f"evidence_case {experiment_id}")`. If
   a night already holds the lock, `cpu_lane_lock` decides whether to wait or refuse. Do not add
   a bypass. Test that a held lock refuses with the holder named. Coordinate with the CPU lane
   before editing: they own this tool.
8. **Shortlist table (F9).**
   - Default columns: Driver, Box (W×H×D, L), Tuning / F3, XO Hz, Match H/V, Feasible, Pick.
   - A "Columns" chooser (persisted in the URL) for the rest.
   - Grouped header row: Box | Low end | Crossover | Match | Build.
   - Full-word headers with `tip()`.
   - Re-run `tools/gui/browser_check.py` and save before/after screenshots to evidence.
9. **P8 Overview + final menu.** `#/hw` page on `/api/hw/overview`, per original handoff §5.1.
   Add Overview and New system to the menu (§3 of that handoff). The "next step" must account
   for the evidence cases (e.g. "LF solved; next: bassbox model-difference audit (R3)" links to
   Readiness, not to an action the GUI can't do).
10. **P4 Compare page** on the existing endpoints. Add quick-pick chips for the **four**
    README matrix pairs and the G6 pair. Acceptance: the per-frequency max |ΔdB| matches the
    README table (8.58 @ 1641, 22.25 @ 1641, 23.64 @ 1823, 21.28 @ 1641) to 0.01 dB. Put that
    in a test against the real dirs (skip when absent).
11. **P5 wizard + Quick launch** on the existing endpoints (original handoff §5.2).
    Acceptance: launching with the committed example spec, asset `0062fb59fbf63eae` and the 4
    drivers reproduces study `27616eedee09009f`. The queue already showed that is
    byte-identical, so assert identity.
12. **P6 dialogs.**
    - Add GET routes `hw/stage-options`, `hw/solve-presets`, `hw/authorization` (wrapping
      existing `data_hw_stage` functions).
    - Stage dialog from a shortlist row or a case.
    - Validate button.
    - Solve dialog visible but disabled with the decision-6 reason. The `lowband12` preset now
      shows a real estimate (step 2).
    - The **"Check in Boundary Lab…"** button on the screen page becomes live.
13. **P7 Crossover (locked)** per original handoff §5.9 (`data_hw_dsp.py`, `hw_dsp.js`).
    Per-channel filtered curves only. The sum panel stays locked with the decision-3 reason.
    Include a test that `combine` is never called.
14. **QA + handback.**
    - `tools/gui/browser_check.py` on every hw page at 1280/1009/768/375 px, dark and light.
    - A keyboard-only run of the story.
    - The node lifecycle harness for hw routes (still missing: `tests/gui_hw_lifecycle.mjs`).
    - Handback in the original §10 format at
      `docs/research/system_woofer_2026-11-18/GUI_HANDBACK_<date>.md`.

---

## 5. Owner gates (current)

| Gate | Status | Effect if unanswered |
|---|---|---|
| B screens + spec save | **Yes** (2026-11-19) | build |
| C stage + validate | **Yes** (2026-11-19) | build |
| D solve approval (decision 6) | open | Solve visible, disabled |
| E calibration policy (decision 3) | open | crossover sum locked |
| **G store durability** | new, step 5 | no lock/backup; record the risk in ISSUES |
| **H approve proposed registry entries** | new, at handback | entries stay `proposed` (greyed) |

---

## 6. Additional NEEDS_SENIOR_REVIEW items for your handback

Besides the standard list in the original §10, include:
- every registry entry you wrote, with the README line it came from;
- the control-link validation rules as implemented (which fields are compared);
- the two-series LF+wide chart payload;
- the `git add -p` decisions in step 1 (which hunks you left for other lanes and why);
- any CPU-lane coordination with the evidence lane (step 7);
- confirmation that no step touched the GPU lock or `gpu-clean`.

---

## 7. Science follow-ups (not GUI work; record in ISSUES, don't do)

- **R3 next:** the bassbox model-difference audit (finite baffle, port end correction/NFR,
  losses), as the evidence README concludes. Not another F3 comparison.
- **R6:** read out `ev_mesh_refine/…35700` against #2 (complex-pressure delta per probe, with
  tolerances declared before reading the result).
- **WP3:** read out `ev_assembled_motor_real/…01612` against #2 (demo motor in the same assembly).
- **R1 / decision 3** still blocks every system-level number.

---

## 8. Addendum 2026-11-20 11:05 — evidence-lane results and gate G (senior)

Steps 1–4 have landed (`9b90e25`, `01a67b3`, `b6c9ccc`, `05af010`). The CPU evidence lane then
pushed `c06ddb4` (verified on `origin/hornfab-all-2026-11-18`; README sections checked). Its
results change what the GUI must say. Apply this addendum before continuing at step 5.

### 8.1 New facts (from `docs/evidence/system_evidence_2026-11-19/README.md`)

- **Mesh convergence is negative.** Three meshes (3,954 / 5,976 / 9,148 interior triangles) on
  the same 49-freq grid: nulls move, max on-axis |ΔdB| ≈ 16 dB, RMS 2.6–3.3 dB, non-monotonic.
  Every current system case is `SINGLE_MESH` and **not converged at nulls**.
- **The demo motor is materially wrong** for assembled work. The real-motor assembled case is
  +4.8 to +7.8 dB (mean 6.75 dB, max phase 32.1°) over the demo assembled case, 200–2500 Hz,
  and up to 5.31 dB at LF.
- **Real-motor assembled = derived case.** The motor is patched into a copied project's
  `physical_system.components[].parameters` and then BL-validated. It is *not* a BL-host
  `apply_configuration_patch` staging record, and the transducer shape is still demo.
- **Bassbox ≠ installed LF.** BL is 3.5–5.4 dB below bassbox at 46–132 Hz on the seed box; BL
  has a 30 Hz port peak and a 162 Hz null the lumped model lacks.
- **Census** (`docs/system_data/`): 54 cases / 19 solved / 29 staged / 3 refused / 3 invalid,
  a snapshot at `c06ddb4`.

### 8.2 GUI changes (add as step 4b, before step 5)

1. **Convergence state is declared, not inferred.**
   - Add a registry-level block `store_flags:` with
     `SINGLE_MESH_NOT_CONVERGED_AT_NULLS: {evidence: README#mesh-convergence, applies_to: all_solved}`.
   - `_placeholders` shows it on every solved case in place of `CONVERGENCE_UNCHECKED`, with the
     numbers from the README cited (not recomputed).
   - The Compare page shows the same banner: "Differences near nulls can be mesh artefacts
     (up to ~16 dB). Read smooth regions only."
   - The flag disappears only when the registry says a convergence protocol passed.
2. **Motor provenance chip.** Registry case field `motor_provenance:` takes one of
   `bl_host_patch` (#4/#6 via `motor_map`), `derived_patch` (`ev_assembled_motor_real*`) or
   `demo`. The chip reads "real motor (derived patch)" with the README's qualification as its
   tooltip. Proposed entries only: approval is gate H.
3. **The `DEMO_MOTOR` placeholder states its measured impact.** Use: "Demo motor: understates
   the assembled woofer basis by about 6–7 dB per 2.83 V (README#real-motor-assembled)." This
   is a quoted, sourced number. JS adds no arithmetic.
4. **No ranking anywhere.** No sorted "best case" lists, no system score, no Overview
   recommendation of a case. Add a test that `hw_overview`'s next step never names a case as
   best. Owner decision 3 and a passed convergence protocol both block ranking.
5. **Risk register updates** (`readiness.yaml`):
   - **R6** → `in_progress`, retitled "Not mesh-converged at nulls (negative result); convergence
     protocol needed".
   - **R4/WP3**: the assembled real-motor pair is done; keep R4 closed and cite the WP3 section.
   - **R3**: the bassbox comparison is done, and the next item is the model-difference audit.
   - Add **R18 (HIGH)**: "Real-motor assembled cases are derived patches, not BL-host staging
     records", evidence README.
6. **Census reconciliation (handback item).** The GUI's states (solved/staged/stage_failed/
   solve_failed/recorded/empty) do not map 1:1 to the census (solved/staged/refused/invalid).
   In the handback, list both counts at the same commit and explain each difference. Do not
   change either side to force a match.
7. **README stale line (tell the CPU lane; don't edit their file).** Its "Not established" list
   (README line ~225) still says "No convergence (mesh unchanged between 25 and 49)" and "No
   bassbox-vs-BL conclusion yet". Both now contradict sections of the same file.

### 8.3 Gate G — senior recommendation (the owner answers; quote that answer in CONTINUITY)

Owner question: lock the woofer worktree and back up `system_runs` to
`E:\hornlab-system-evidence-backup-2026-11-20` (50 MB / 1,424 files; E: 366 GB free).
Senior recommendation given to the owner: **yes, both**, under these conditions:

- `git worktree lock --reason "holds the only system_runs evidence store; do not remove" C:/Users/hunte/Hrns/hornlab-woofer-system-wt`.
- **Copy from the physical path** `C:\Users\hunte\Hrns\hornlab-woofer-system-wt\system_runs`,
  not through the junction. Use `robocopy <src> <dst> /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ /NP
  /LOG:<dst>\..\robocopy_2026-11-20.log` — `/E`, **not `/MIR`** (a mirror can delete), and `/XJ`
  so no junction is followed.
- **Verify, don't trust robocopy's summary:** write a sha256 manifest (relative path, size,
  sha256) of the source and the destination with the same script; they must be identical. Store
  `SHA256SUMS.txt` beside the backup and commit only the manifest's own sha256 + file count to
  CONTINUITY (not the 1,424-line list).
- Record that the backup is a **recovery copy, not a working store**: manifests inside it still
  hold absolute paths into the worktree. Restoring means putting it back at the original path,
  or the future `STORE_LOCATION.json` remap (§3.4).
- If the CPU lane is mid-solve, back up **after** it releases `.cpu.lane.lock`, and note the
  cutoff (newest case dir included).
- Re-run the backup after every evidence batch until the store moves out of the worktree. Add
  an ISSUES item for the long-term move.
