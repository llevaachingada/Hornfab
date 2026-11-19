# HANDOFF — finish the Horn + woofer GUI (local orchestrator, 2026-11-19)

**You are:** the local orchestrator / single integrator for `hornlab-search`.
**Your job:** take the Horn + woofer GUI from G0 (read-only, built) to complete, following the
design below. Then hand back to the senior reviewer (the session that wrote this) for a final
hardening pass. **Work order:** P0 → P9 (§6). Stop at every owner gate (§7).
**Handback:** a file in the format of §10. Do not mark anything "done" that you have not seen
working in the browser and in the test output.

Read first, in this order:
1. This file.
2. `GUI_SYSTEM_PLAN_2026-11-19.md` (same folder): the original plan and the G0-as-built notes.
3. `SENIOR_REVIEW_HANDOFF_2026-11-19.md` §2–§5, §7, §8: the system architecture, the risk register,
   the owner decisions and the non-goals.
4. Repo rules: `AGENTS.md` (owner amendments, 8 hard rules, push rule, test profiles) and
   `CLAUDE.md`.

---

## 0. Ground truth at handoff time

| Item | State |
|---|---|
| Work location | Worktree `C:/Users/hunte/Hrns/hornlab-woofer-system-wt`, branch `feat/woofer-system-v0`, last commit `a2e8769`. **Uncommitted:** the R16 clearance gate (`system/boundarylab/{clearance,stage}.py`, `tests/system/{test_clearance,test_bl_stage}.py`), the whole G0 GUI (`gui/{data_hw,server}.py`, `gui/static/{hw.js,app.js,index.html}`, `tests/system/test_gui_hw.py`, `readiness.yaml`) and the plan docs (`GUI_SYSTEM_PLAN_*`, this file). Check `git status --short` before committing. |
| Branch base | `1e9f71b`, which is behind `hornfab-all-2026-11-18`. GUI files diverged on that side. |
| Canonical checkout | `C:/Users/hunte/Hrns/hornlab-search` on `hornfab-all-2026-11-18`. It has **uncommitted edits by another lane** to `gui/static/{app,charts,sandbox,view3d}.js`. Do not touch or stash them without the owner. |
| Tests (worktree) | `tests/system` + all `tests/test_gui*.py` + `test_b8_lanes_bounded_gui.py`: 861 tests, 3 failures, 7 env-gated skips. The 3 failures **pre-exist without the G0 changes** (verified by stashing): `test_b8_lanes_bounded_gui.py::test_study_modules_have_no_host_cleanup_or_process_kill_paths`, `test_gui_preview_shape.py::test_plughorn_3d_survives_one_untriangulable_face`, `test_gui_preview_shape.py::test_typology_link_resolves_by_catalog_name`. Not yours to fix here; do not let the count grow. |
| GUI built (G0) | `#/hw/cases`, `#/hw/case/<exp>/<case>`, `#/hw/readiness`; `gui/data_hw.py`, `gui/static/hw.js`, `hw` dispatch in `gui/server.py`, registry `readiness.yaml`. |
| Data on disk | `system_runs/system/<experiment>/<case>/` (gitignored, immutable, sha-pinned manifests); screen studies at `system_runs/woofer_seed*/woofer_seed.json` (schema `hornlab.system.woofer_seed.v1`, newest study `27616eedee09009f` in `woofer_seed_stage5_blfit`). |
| Run the GUI | `.venv\Scripts\python.exe -m hornlab_search.gui --port 8799 --no-browser --root .` from the worktree (use `-m hornlab_search.gui`; `-m hornlab_search.gui.server` exits silently). Port 8765 may be the owner's own GUI, so do not use it. From the canonical checkout, the case data is not there; see P0 step 0. |

---

## 1. Non-negotiables (violating any one fails the handback)

1. **No acoustics in JavaScript.** Every number on screen comes from a Python reader or a pure
   function in `hornlab_search/system/`. JS formats and plots only.
2. **Never sum the woofer and horn channels** anywhere (UI, API, export) until owner decision 3
   (calibration policy, R1) is answered and `combine()` accepts it. The woofer basis is Pa per
   2.83 V and the horn basis is Pa per 1 m/s.
3. **Never infer a fidelity label, real-vs-demo motor or transducer shape.** They come from
   `readiness.yaml` only; anything else shows `UNDECLARED`.
4. **Refusal tokens are shown verbatim**, with a plain-English gloss next to them. Never hidden,
   never rephrased away.
5. **No GPU.** Every system job is CPU (`beat_cpu`). The GUI never takes or touches
   `runs/.gpu.lock` for system work, never runs `gpu-clean`, and never kills processes by image
   name.
6. **No Boundary Lab solve without an authorization record** (owner decision 6). The solve
   action ships disabled until the owner answers (§7).
7. **File safety:** case keys pass the existing `_KEY_PART` regex and store containment. Mesh,
   spec and study files are read only from inside their roots. A manifest path never widens what
   the server reads.
8. **Frozen/owned files:** `docs/plan/**` and `01_CONTRACTS.md` are frozen. The installed BL,
   BEAT and Julia are read-only. Hard rules 1–8 in `AGENTS.md` apply. A shared file you must
   change (`app.js`, `index.html`, `server.py`, `glossary.js`, `jobs.py`, `app.css`) gets the
   **smallest additive edit** (routing, one menu block, one dispatch branch, glossary entries, one
   job kind). New behaviour goes in new files.
9. **Never weaken a test** (hard rule 7). A failing check is a finding for the handback.

---

## 2. The user's workflow — mirror the horn side

A basic user already knows the horn workflow: **pick a brief → pick typologies → launch → read
the run page → compare**. The Horn + woofer side follows the same shape, in the same words where
possible.

```
Horn side (exists)                     Horn + woofer side (build)
───────────────────────────────────    ─────────────────────────────────────────────────
Home                                  Overview          #/hw            "where am I, what's next"
Briefs / Typologies                   (inside the wizard: horn asset, drivers, box limits)
New run → Guided (Compose)            New system        #/hw/new        4-step wizard
        → Quick launch                               #/hw/launch     from a saved system spec
Runs list                             Screens           #/hw/screens    one row per screen study
Run detail (KPIs, tabs, figures)      Screen detail     #/hw/screen/<study>   shortlist → pick
                                      Cases             #/hw/cases      Boundary Lab checks (G0)
                                      Case detail       #/hw/case/<exp>/<case> (G0, extend)
Compare                               Compare           #/hw/compare?a=&b=     A/B and 2×2
—                                     Crossover         #/hw/case/<…>/crossover (locked until R1)
Status                                Readiness         #/hw/readiness  (G0)
```

**The story the user follows (the copy uses these exact step names):**

1. **Pick a horn.** One of your saved horn designs.
2. **Pick woofer drivers.** One or more from the driver catalog.
3. **Set the box limits and targets.** Size ranges, port, coverage and lowest frequency (F3).
4. **Screen.** A fast CPU estimate (seconds to a few minutes) gives a shortlist of buildable
   boxes. It never names a single winner.
5. **Check in Boundary Lab.** Stage and validate one shortlisted design (CPU, minutes). This
   proves the box can be built and the horn clears it.
6. **Solve.** The full simulation (CPU; about 2.5 minutes for 25 frequencies on this machine).
   Needs approval.
7. **Read the results.** Per-channel response, polars and geometry; compare cases; crossover
   later.

Every screen says which step it belongs to. The Overview shows the path with the user's progress.

---

## 3. Navigation (final)

Replace the G0 menu block in `index.html` with:

```
HORN + WOOFER
  ◎ Overview      #/hw
  ＋ New system    #/hw/new        (also covers #/hw/launch, like "New run")
  ▤ Screens       #/hw/screens    (active on #/hw/screen/…)
  ▣ Cases         #/hw/cases      (active on #/hw/case/… and #/hw/compare)
  ☰ Readiness     #/hw/readiness
```

Use five items. Compare and Crossover are reached from the case page toolbar, the same way
horn Compare is reached from a run's toolbar. The menu highlight rules go into `updateNav` in
`app.js` (two lines already exist for Cases and Readiness).

---

## 4. House style — copy it, don't invent it

Take these patterns from `viewRunDetail` / `viewCompose` in `app.js` and the classes in
`app.css`. Mirror them in `hw.js` (and new `hw_*.js` modules). Do not add a new design language.

| Pattern | Horn source | Use for |
|---|---|---|
| Page header: `<div class="eyebrow">Horn + woofer · …</div><h2>Title</h2><p class="mono muted">id</p>` + provenance `pill-row` | run detail header | every hw page. **G0 uses `<h1>` + `section-header`; change it.** |
| Verdict-first `.kpis` strip | `#kpi-strip` | Overview, Screen detail, Case detail |
| `.run-toolbar` = `nav.run-tabs` (`a.run-tab-link`, `aria-current="page"`) + `.run-actions` (buttons, `.btn-sm`, one `.primary`) | run toolbar | Screen and Case detail tabs and actions |
| `newRunModeHtml()`-style mode switch (Guided / Quick launch) | `#/compose` / `#/launch` | `#/hw/new` / `#/hw/launch` |
| Numbered wizard sections, `job-type-btn` + `aria-pressed` radio rows, `.form-grid`, `.hint` with `role="status"`, `<pre>` command preview, `Launch` primary button, `.gpu-busy-note` | Compose | New system wizard |
| `.fig` card: `.fig-head` with `h3` (+ `tip()`), `.seg-toggle` with `aria-pressed`, `.cap` caption, `.legend` | run detail figures | every chart |
| `.grid2` small multiples | beamwidth H/V | woofer vs horn side by side |
| `table` in `.tbl-wrap`, `tr.clickable` rows | Runs / Campaigns lists | lists |
| `.alert.{error,warn,info}`, `.pill.{good,warn,bad}` | everywhere | refusals, placeholders, states |
| `brk()` (word-break points in long ids), `fmtHz/fmtDeg/fmtMm/fmtDb` | `app.js` helpers (not exported) | long ids and units. Copy the helpers into the hw module, or export them from `app.js` as an additive edit; do not re-implement other formats |
| `tip(key, label)` from `glossary.js` | everywhere | every technical label (new terms in §8.4) |
| Skeleton while loading (`skel()` in `verify.js`) | verify view | every async page |

---

## 5. Page designs

Wireframes are layout intent, not pixel specs. Every page must also satisfy the UX rules in §8.

### 5.1 Overview — `#/hw` (P8)

```
Horn + woofer                                                    (eyebrow)
Design a two-way: a saved horn over a vented woofer               (h2)
┌ KPIs ───────────────────────────────────────────────────────────────┐
│ Screens 3 │ Shortlisted 6 │ Checked in BL 9 │ Solved 5 │ Blocked by decisions 2 │
└─────────────────────────────────────────────────────────────────────┘
How it works   ①Pick a horn ②Drivers ③Box limits ④Screen ⑤Check in BL ⑥Solve ⑦Read
               (each step a link; done steps ticked from what exists on disk)
┌ Next step card (one sentence + one primary button) ──────────────────┐
│ e.g. "Shortlist ready (6 designs). Check one in Boundary Lab →"      │
└──────────────────────────────────────────────────────────────────────┘
Recent screens (3 rows)          Recent cases (5 rows, same columns as Cases)
Readiness summary: "2 owner decisions block: real driver shape (1), solve approval (6) →"
```

The next step is computed server-side (`hw_overview`) from disk, never guessed in JS. Empty
store: the next step is "Start a new system →".

### 5.2 New system wizard — `#/hw/new` (P5) and Quick launch — `#/hw/launch`

Mode switch at the top (Guided / Quick launch), exactly like New run.

```
Step 1 · Pick a horn
  Cards from the saved-horn inventory (system.horn_assets.inventory_runs + asset_row):
  name, brief, design hash, quality chip (EXACT_COMPLEX / MAGNITUDE_ONLY), band, and a
  "full-domain mesh available" chip. Thumbnail: the run's existing wall-section or
  render if present (reuse run-detail data; never re-mesh).
  Filter: search box, "has full-domain mesh" toggle.  Selecting shows a one-line summary.
  MAGNITUDE_ONLY → inline warn: "Screen only: no phase or delay claims for this horn."
Step 2 · Pick woofer drivers   (multi-select, at least 1)
  Cards from load_driver_catalog: name, size, Fs / Vas / Qts / Sd / Xmax (units in labels),
  "T/S verified" chip, "Real shape: missing cone depth, surround, cap" warn chip
  (drivers.geometry_completeness). Hover = source file + which fields are vendor vs derived (R15).
Step 3 · Box limits and targets
  Two-handle min–max inputs (sandbox knob style, editable numbers both ends) for:
  width, height, depth (mm), net volume (L), tuning (Hz), port area (cm²), port flare;
  wall (mm), port type (select).  Targets: H and V coverage (°), listening window (°), F3 max (Hz).
  Assembly: horn layout (select), woofer centre range, horn offset range (mm).
  Defaults from examples/systems/two_way_80x50_700_research.yaml. Every field: tip, unit,
  live validation (server: contracts.parse_system_spec_dict); errors next to the field.
  "Save as…" writes a spec YAML (§5.2a).
Step 4 · Screen
  Summary of choices + exact command preview (<pre>), lane note "CPU · about N s",
  [Launch screen] primary.  After launch: progress line + link to the job log;
  on finish → redirect to the new Screen detail.
```

**Quick launch:** pick a saved spec, an asset and drivers, then Preview and Launch. Three
controls, the same as horn Quick launch.

**5.2a Saved specs:** user specs live in `examples/systems/user/<name>.yaml` (a new folder,
`_KEY_PART` names, no overwrite without an explicit "Replace" confirm). The writer
round-trips through `parse_system_spec_dict`. Unknown keys are refused with the parser's own
message (hard rule 3: no invented keys).

### 5.3 Screens list — `#/hw/screens` (P2)

This is the Runs-list equivalent. One row per `woofer_seed.json` found under `system_runs/`
(`woofer_seed*/` and `screens/<study>/` for GUI-launched ones).

Columns: study id (mono), when, horn (brief and hash), drivers, shortlist n, panel-fit
rejected n, claim chip ("heuristic screen, no winner"). Replays that share a `study_id` are
grouped, with "byte-identical replay ×2" when their sha256 match.

### 5.4 Screen detail — `#/hw/screen/<study>` (P2)

```
Horn + woofer · Screen · study 27616eedee09009f                  (eyebrow, mono id)
Shortlist for lecleach_rollback_1in_v6 × 4 drivers               (h2)
pill-row: SCREEN_MAGNITUDE · no phase/delay claims · BL panel-fit applied (demo transducer dims)
⚠ alert.warn (claim): "Heuristic screen — no single winner, not a validated ranking."
KPIs: Drivers 4 │ Boxes considered 32 │ Kept 27 │ Pareto front 9 │ Shortlist 6 │ Panel-fit rejected 11
toolbar tabs: [Shortlist] [Trade-offs] [Rejected] [Panel fit]        actions: [Check in Boundary Lab…] (disabled until a row is picked)
```

- **Shortlist tab:** table of `shortlist` rows. Columns:
  - driver, `shortlist_reason`, box W×H×D, net L, tuning Hz, port cm², F3 Hz;
  - XO Hz and band, match error H/V (dB²), excursion margin dB, port velocity ratio, footprint m²;
  - feasibility chips (all `feasibility` keys);
  - a radio to pick the row.

  Column headers come from `axis_directions` (the "−" / "+" arrow shows whether lower or higher
  is better). Sortable. The selected row is a URL state `?row=<candidate_id>`.
- **Trade-offs tab:** a scatter with X and Y axis selects over `numeric_axes`. Kept rows are
  dots, the Pareto front is ringed, shortlist rows are filled, rejected cells are hollow (hover
  shows the reason). Click selects the row (the same state as the table). Reuse `chart()` with
  `dots: true`.
- **Rejected tab:** `rejected_ledger` grouped by `stage` with counts, a filter by reason
  prefix, and verbatim reasons.
- **Panel fit tab:** the to-scale front baffle for the selected row (walls, driver cutout, port
  with flare, required vs available separation arrows). A toggle switches between "BL demo
  transducer" and "real driver (Sd-derived Ø)". A front-height what-if slider and a port-area
  what-if call `POST /api/hw/panel-fit`, which wraps `woofer_seed.bl_panel_fit_feasible`. The
  verdict and the exact reason string show under the drawing. Caption: "Pre-check that mirrors
  Boundary Lab's validator; Boundary Lab's own validate is the authority."
  - **Acceptance:** with real 12PR300 dims on 371.2 mm the page shows the refusal with
    0.1821 m required vs 0.1501 m available. The recorded 170 cm² demo cell reproduces BL's
    refusal.
- **"Check in Boundary Lab…"** opens the stage dialog (§5.7) prefilled from the row
  (`box`, `placement.dz_mm` → horn offset, driver). **P6.**

### 5.5 Cases list — `#/hw/cases` (G0, polish in P1)

Keep the G0 table. P1 changes:
- house header;
- group rows by experiment, collapsible, with the newest case expanded;
- a **"Show superseded / empty"** toggle (empty dirs and failed attempts hidden by default but
  counted);
- add the `recorded` and `empty` counts to the KPIs;
- persist filters in the URL (already `?f=`);
- keyboard row navigation (already Enter).

### 5.6 Case detail — `#/hw/case/<exp>/<case>` (G0, extend P1/P3/P4)

Restructure the G0 page into the run-detail shape:

```
eyebrow: Horn + woofer · Case · bl_stage_horn_project
h2: #2 · G4 wide basis                         mono key
pill-row: solved 25/25 · COUPLED_VENTED_FEM_BEM_LEM · motor demo · shape demo · gap 17.0 mm
⚠ Placeholders (collapsible <details open> on first visit; remembered per viewer)
KPIs: Freqs 25 (200–2500 Hz) │ On-axis woofer @ 1 kHz dB/2.83 V │ On-axis horn @ 1 kHz dB/(m/s) │ Gap mm │ Box L
toolbar tabs: [Overview] [Geometry 3D] [Response] [Polars] [Provenance]
          actions: [Compare…] [Crossover…](locked badge) [Validate] [Solve…](gated) [Open folder path ⧉]
```

- **Overview:** the 2-D elevations (existing), the box-and-horn table, a "Related" list
  (parent staged project, paired case, other cases with the same geometry identity), and the
  registry note.
- **Geometry 3D (P3):** new module `hw3d.js`.
  - `const THREE = await loadThree()` from `view3d.js` (it returns the namespace).
  - `import("three/addons/controls/OrbitControls.js")`.
  - Two meshes from `GET /api/hw/mesh/<exp>/<case>?part=box|horn`: the box semi-transparent,
    the horn solid.
  - The clearance as a coloured line between the closest pair.
  - Toggles: box opacity, show probes (as directions; the 2 m distance is off-scale, so say so),
    reset view.
  - 2-D fallback = the existing elevations.
  - Dispose on route change: the container carries `data-v3d` and `_dispose3d`, so the router
    sweep in `route()` already cleans it up.
- **Response:**
  - G0 per-channel charts.
  - Add a "Probe" seg-toggle in place of the select when there are ≤ 6 probes.
  - A "Phase: wrapped / unwrapped" toggle (unwrap in Python: add `phase_unwrapped_deg` to
    `hw_basis`).
  - A "Show other cases" overlay picker, limited to the same channel, same per-input reference
    and same probe id; anything else is refused with the reason.
  - Export CSV of exactly what is plotted, with a units header.
- **Polars:** the G0 heatmaps + a "Range: −90…90 / full 360" seg-toggle + per-channel −6 dB
  beamwidth lines. The beamwidth is computed in Python (`hw_basis` adds it), never in JS.
- **Provenance:** the G0 table + "Copy" buttons for hashes + links to the evidence-doc section
  quoting this case (registry `evidence:` field; add it to `readiness.yaml` cases).

### 5.7 Actions — stage, validate, solve (P6)

All three are **CPU jobs** through `JobManager` (`gui/jobs.py`). They run through a
repo-relative entry script, the way `tools/geometry/rolled_rect_cli.py` jobs do:

- **Entry:** new `tools/system/gui_system_job.py`. It is a thin argv bridge to
  `hornlab_search.system.cli` (`reference prepare|validate|solve|report`) and
  `hornlab_search.system.woofer_seed` (`main`). No logic of its own.
- **Wiring the entry (verified 2026-11-19):** `Job.entry` exists, but `JobManager._bridge_entry`
  picks it from the job's *config* (rows adapters only), not from the kind. So `_new_job` needs
  one additive branch: `hw-*` kinds get `entry="tools/system/gui_system_job.py"`. Also the
  `POST /api/preview` branch in `server.py` hardcodes `"hornlab-search " + argv`. For `hw-*`
  kinds it must print `python tools/system/gui_system_job.py …`, the command that will really
  run (reuse `Job.view`'s prefix rule). A preview that lies about the command is a handback
  blocker.
- **Lane lock:** read the holder with the existing `gui/data.py::_lane_lock(runs, "cpu")` (file
  names come from `search/gpulock.py::LANE_LOCK_FILES`). Do not write a second lock reader.
- **New job kinds** in `build_argv`, all `gpu=False`: `hw-screen`, `hw-stage`, `hw-validate`,
  `hw-solve`. Every argument is validated like the existing kinds:
  - repo/store-contained paths;
  - `_int` / `float` ranges;
  - enum checks for backend: **only `beat_cpu` is allowed** from the GUI.
- **One system job at a time** (refuse a second with a clear message). Respect
  `runs/.cpu.lane.lock` (via `_lane_lock`): if another live process holds it, refuse with
  "CPU lane busy (<holder>)" and never kill it.
- **Stage dialog:** fields are prefilled from a screen row or an existing case:
  - `--overrides` (box parameters),
  - horn mesh (picker limited to `system_runs/system/ref_case/horn_full/*/mesh.msh`),
  - `--source-group` (select populated from the mesh's groups),
  - `--translation-mm` (z only exposed; x/y fixed 0, with an "advanced" disclosure),
  - `--experiment-id` (default `bl_gui_<date>`).

  The dialog then shows the exact command preview (same validation path, `POST /api/preview`
  with kind `hw-stage`) and **Stage + validate** (primary). After the job: link to the new case.
  The clearance verdict shows prominently, because the R16 gate makes a too-close horn a
  failed stage.
- **Validate:** a one-click re-validate of an existing staged case (CPU, seconds).
- **Solve dialog (owner decision 6):**
  - Request preset: "Smoke 3 freqs" / "Wide 25 freqs 200–2500 Hz" / "Low band 12 freqs 20–200
    Hz (R3)", written as request JSON into the case dir by the job script, never by the server.
  - Estimated CPU time from the recorded runs.
  - **Authorization record:** who, why and scope, all required, with a shape decided by the owner.
  - A typed confirmation ("solve").
  - Until the owner answers decision 6, the Solve button is visible but **disabled**, with the
    tooltip "Needs owner approval for GUI-started Boundary Lab solves (decision 6)". The flag is
    `HORNLAB_GUI_ALLOW_BL_SOLVE=1` *and* a recorded owner decision.
- **Job feedback:**
  - Queue/progress row reuses the existing jobs panel (`#/status` shows system jobs too, with a
    "CPU · system" tag).
  - Success → toast + link; failure → `alert.error` with the last 20 log lines and the refusal
    token, if any.

### 5.8 Compare — `#/hw/compare?a=<key>&b=<key>` (P4)

- **Pickers:** two case selects (solved cases only). A "Swap" button. Quick-pick chips for the
  registry's `pair_with` pairs ("Motor A/B #4 vs #5", "G6 #3 vs #2").
- **Server refusal** unless the frequency grids, probe ids and excitation ids match. Each
  mismatch is one token: `GRID_MISMATCH`, `PROBE_SET_MISMATCH`, `EXCITATION_MISMATCH`. The page
  shows the refusal and what differs.
- **"What changed"** box: the identity diff between A and B (motor, box dims, horn offset,
  geometry hash, mesh size).
- **Charts:** per channel and per probe,
  - |B_a/B_b| in dB and Δphase versus frequency;
  - a table of the max relative delta per band (LF < 500 Hz, XO 500–1500 Hz, HF > 1500 Hz).

  The band edges are labelled as display choices.
- **2×2 matrix mode** (`?matrix=motor,box`): a grid with motor rows and box columns. Each cell is
  a case chip (solved / staged / missing, with link). Each edge between cells links to that
  pairwise compare.
- **Acceptance:**
  - reproduces the recorded motor A/B 120–144 % (LF 120 %, XO 140–149 %);
  - reproduces the G6 max relative delta 0.356–0.575, to stored precision.

  Write both as tests against the real dirs, skipping when they are absent, like
  `test_real_staged_cases_replay`.

### 5.9 Crossover — `#/hw/case/<exp>/<case>/crossover` (P7, mostly gated)

Build the page now in its **locked** form:
- Controls are shown but disabled: crossover type (LR2/LR4/LR8 from the spec), XO Hz,
  gain per channel, horn delay (ms), woofer polarity, up to 2 woofer PEQ bands (fc, gain,
  Q).
- What works now: **per-channel filtered curves** (filter bank applied to each channel on its
  own axis, via `dsp.filter_bank`), with the `dsp.validate_dsp_point` verdicts listed.
- A locked "System sum" panel says: "Summing needs a channel calibration policy (owner decision
  3, risk R1). Woofer: Pa per 2.83 V. Horn: Pa per 1 m/s."
- Permanent captions: "Analog prototype filters, not a digital (biquad) implementation." and
  "An electrical LR4 is not an acoustic LR4."

When decision 3 lands, a later WP4 turns on the sum through `combine.recombine_with_dsp` with
the calibration record shown next to the curve. **Not in this handoff's scope.**

### 5.10 Readiness — `#/hw/readiness` (G0, polish P1)

- House header.
- Each risk row links to its evidence doc.
- A filter by level and status.
- Decisions show "who decides" and "what it unblocks", by linking to the gated GUI features in
  this doc.

---

## 6. Build plan — phases, files, acceptance

Commit at the end of every phase. Conventional commits with `gui` or `system` scope; push rule:
CONTINUITY + ISSUES in the same commit. At each phase run the system + GUI tests (command in §9)
and the browser check list (§8.6). Paste the real output into your phase log.

| Phase | Do | Files (new unless marked) | Acceptance |
|---|---|---|---|
| **P0 Integrate** | 0) **Data location (verified 2026-11-19):** `system_runs/` is gitignored and exists **only** in the worktree; the canonical checkout has none. Its manifests hold *absolute* paths into the worktree (horn `mesh_path`, BL outputs), so **never copy or move it**. Instead add an additive `--system-store DIR` option to `gui/server.py::main` (default: `$HORNLAB_SYSTEM_STORE`, else `<root>/system_runs`), pass it to `App(system_store=…)`, and run the canonical GUI with `--system-store C:/Users/hunte/Hrns/hornlab-woofer-system-wt/system_runs`. Containment then holds because the absolute paths resolve inside that store. GUI-launched jobs (P5/P6) write into the same store. 1) In the worktree, commit the uncommitted R16 + G0 work as two commits (`feat(system): R16 clearance gate…`, `feat(gui): horn+woofer G0 views…`). 2) **Owner gate A** (§7): resolve the canonical checkout's foreign uncommitted GUI edits. 3) Merge `feat/woofer-system-v0` into `hornfab-all-2026-11-18` in the canonical checkout; resolve conflicts additively (keep both sides' routes/menu). 4) Add `docs/INDEX.md` lines for every doc in `docs/research/system_woofer_2026-11-18/` and `docs/CODE_MAP.md` lines for `hornlab_search/system/**`, `gui/data_hw.py`, `gui/static/hw.js`. 5) Run the test baseline. **All later phases happen in the canonical checkout** (owner amendment 2026-11-12: no new worktrees). | `docs/INDEX.md`*, `docs/CODE_MAP.md`*, CONTINUITY*, ISSUES* | Merge clean; failures = exactly the 3 pre-existing (or the hornfab-all baseline equivalent, recorded before merging); `#/hw/cases` loads in the canonical checkout. |
| **P1 House style + G0 fixes** | Header pattern (§4); toolbar tabs on Case detail; KPIs incl. recorded/empty; grouped Cases list + superseded toggle; `<details>` placeholders; glossary entries (§8.4) moved from `hw.js` `GLOSS` into `glossary.js` `TERMS` and used via `tip()`; skeletons; fix the duplicate `BODY_CLEARANCE_VIOLATION` chip on the case page (pill row + token row both show it); light-theme pass. | `hw.js`*, `glossary.js`*, `app.css`* (only if a class is missing; prefer existing) | Every hw page passes §8.6; no `<h1>` in hw pages. |
| **P2 Screens** | `data_hw.hw_screens(root)` + `hw_screen(root, study)` (study id `^[0-9a-f]{16}$`, search roots allow-listed: `system_runs/woofer_seed*`, `system_runs/screens/*`); `POST /api/hw/panel-fit` (pure; validated numeric inputs with min/max; returns `{feasible, reason, required_m, available_m}`, adding the numbers to `bl_panel_fit_feasible`'s output via a sibling helper; do **not** change its signature). Views: list + detail with the 4 tabs. | `gui/data_hw_screen.py`, `gui/static/hw_screen.js`, `server.py`* (dispatch), `app.js`* (routes) | Shortlist reproduces `woofer_seed.json` rows exactly; panel-fit numbers match §5.4 acceptance; scatter selection ↔ table selection ↔ URL in sync. |
| **P3 3D geometry** | `GET /api/hw/mesh/<exp>/<case>?part=box|horn` → `{verts (mm, flat), tris (flat), bbox, units}`, decimation cap (e.g. 60 k tris, recorded `decimated: true` if hit); containment as `_inside`. `hw3d.js` viewer. | `gui/static/hw3d.js`, `data_hw.py`* | Renders #2 and the 62864 violation case (overlap visibly red); no WebGL context leak across 10 route changes (check `renderer.info`); 2-D fallback when three.js fails. |
| **P4 Compare** | `hw_compare(a, b)` + matrix view. | `gui/data_hw_compare.py`, `gui/static/hw_compare.js` | §5.8 acceptance numbers; mismatch refusals tested. |
| **P5 New system** | Asset inventory, driver catalog, spec validate/save endpoints; wizard + quick launch; `hw-screen` job kind; screens written to `system_runs/screens/<study>/`. | `gui/data_hw_new.py`, `gui/static/hw_new.js`, `tools/system/gui_system_job.py`, `jobs.py`* (kinds) | A fresh screen launched from the GUI with the committed example spec + asset `0062fb59fbf63eae` + 4 drivers produces study `27616eedee09009f`-equivalent rows (same `input_sha256` → same `study_id`); invalid spec fields show the parser's message next to the field. |
| **P6 BL actions** | `hw-stage`, `hw-validate`, `hw-solve` kinds; dialogs; solve disabled per decision 6. | `jobs.py`*, `hw.js`*, `gui_system_job.py`* | Stage from a shortlist row → new case dir with `clearance` PASS record; a deliberately bad offset (−3 mm) → stage fails with `BODY_CLEARANCE_VIOLATION` shown in the dialog; solve button disabled with the decision-6 tooltip; argv validation tests for every kind (bad path, bad backend, out-of-range numbers). |
| **P7 Crossover (locked)** | `POST /api/hw/dsp-preview` returning **per-channel** filtered bases only + `validate_dsp_point` verdicts; locked sum panel. | `gui/data_hw_dsp.py`, `gui/static/hw_dsp.js` | A test asserts the endpoint response has no summed/combined field, and that `combine` is never called (monkeypatch to raise). |
| **P8 Overview** | `hw_overview` (KPIs + next step from disk) + page + final menu (§3). | `data_hw.py`*, `hw.js`*, `index.html`* | Next step correct for: empty store, screen-only, staged-only, solved. |
| **P9 QA + evidence + handback** | §8.6 on every page in dark + light, at 1280 / 1009 / 768 / 375 px; keyboard-only run of the 7-step story; JS lifecycle test (node harness like `tests/gui_study_results_lifecycle.mjs`) for hw route mount/unmount; screenshots into `docs/evidence/hw_gui_<date>/` (hornlab-evidence skill rules); write the handback (§10). | `tests/gui_hw_lifecycle.mjs`, `tests/test_gui_hw_lifecycle.py`, evidence folder | §10 complete. |

`*` = existing file; additive edit only.

---

## 7. Owner gates — stop and ask; never decide these yourself

| Gate | When | Ask the owner | If no answer |
|---|---|---|---|
| **A** | P0 step 2 | "The canonical checkout has uncommitted edits to `app.js`, `charts.js`, `sandbox.js`, `view3d.js` from another lane. Commit them, shelve them, or wait?" | Do not merge. Continue P1–P4 **in the worktree** (owner already allowed that worktree) and report. |
| **B** | before P5 | "May the GUI launch CPU screen jobs, and may it write user specs to `examples/systems/user/`?" | Build the wizard with Launch disabled ("needs owner approval") and Save disabled. |
| **C** | before P6 | Plan question 3: "Is GUI-launched CPU stage + validate acceptable?" | Build dialogs; actions disabled with the reason. |
| **D** | P6 solve | Decision 6: the authorization record shape (who/why/scope; free-form vs registry). | Solve disabled (default). |
| **E** | P7 | Decision 3 (calibration policy, R1). | Locked sum panel (default). Never build a sum. |
| **F** | anytime | Any change to a frozen contract, the BL/BEAT install, or `01_CONTRACTS.md`. | Do not do it. `NOTES_FOR_SENIOR.md` entry. |

Use the owner's exact words in CONTINUITY when a gate opens.

---

## 8. UX rules (apply to every page; the browser check list tests them)

### 8.1 Plain language and honesty
- Labels are short and in plain English with units: "Net volume (L)", "Port area (cm²)",
  "Horn offset from baffle (mm)". The technical name goes in the `tip()` hover.
- Each page starts with one sentence saying what it is and which story step it belongs to.
- A screen estimate is never called a result, and a solve is never called measured. Fidelity
  chips are always visible near the numbers they qualify.
- Empty states always offer the next action ("No screens yet. Start a new system →").

### 8.2 Controls
- Expose: the step choices, ranges with min and max editable, the targets, the action buttons,
  view toggles (probe, plane, phase mode, range), and compare pickers.
- Hide behind an "Advanced" disclosure: horn x/y offset, mesh sizes, scan limits, timeouts,
  experiment id. Show their defaults.
- Never expose: backend choice (CPU only), anything GPU, force/overwrite flags, raw file paths
  as free-text inputs. Paths are pickers over allow-listed roots.
- Sensible defaults always come from committed examples, never from JS constants.
- Every expensive action: preview the exact command first, show the lane and estimated time,
  then one primary button. Irreversible or costly ones get a confirm step.
- Disabled controls always say why (tooltip *and* visible hint text; a tooltip alone is not
  accessible).

### 8.3 Feedback and state
- Loading: skeletons. Errors: `alert.error` with the server message and the token gloss.
  Long jobs: progress row + log link, and the page stays usable.
- All view state that matters is in the URL (tab, filter, selected row, probe, compare pair).
  Back and forward work; reload restores the view.
- No silent auto-refresh that moves content. If polling is needed for jobs, update in place and
  stop polling when the route changes.

### 8.4 Glossary entries to add (`glossary.js` `TERMS`)
`hw_fidelity`, `hw_screen`, `e_shape`, `panel_fit`, `clearance`, `f3`, `fb_tuning`,
`port_velocity`, `excursion_margin`, `xo_band`, `per_input_ref`, `ideal_horn_source`,
`demo_motor`, `demo_shape`, `lf_not_solved`, `convergence`, `stage_validate`, `bl_solve`,
`authorization`, `calibration_policy`. Each needs `label`, `unit`, `short` and `long`. The
`long` text is sourced from the handoff/evidence docs (cite the doc in a code comment), with no
new acoustic claims.

### 8.5 Accessibility and layout
- Keyboard: every action reachable; visible focus; Enter/Space on rows and toggles; `Esc`
  closes dialogs, and focus returns to the opener.
- ARIA: `aria-pressed` on toggles, `aria-current` on tabs, `role="status"` on hints,
  `role="alert"` on errors, `aria-label` on every chart SVG.
- Contrast: use the existing tokens only (`--good/--warn/--bad/--accent/--muted`). Colour is
  never the only signal (chips carry text).
- Layout: no page-level horizontal scroll at 375 / 768 / 1009 / 1280 px. Wide tables scroll
  inside `.tbl-wrap`. Charts measure their container *after* insertion (the G0 polar bug: an
  unsized SVG measures 300 px and is then CSS-stretched; set `data-chart` and width before
  drawing).

### 8.6 Browser check list (per page, dark and light, every width)
1. No console errors (`read_console_messages onlyErrors`).
2. `document.documentElement.scrollWidth <= clientWidth`.
3. Every chart: rendered width equals its `width` attribute (no CSS stretch), and has an
   `aria-label`.
4. Keyboard-only: reach and trigger every control.
5. Reload restores state from the URL.
6. Every number traced to an API field (spot-check 3 per page against the JSON).
7. Screenshot saved to the evidence folder.

---

## 9. Commands

```powershell
# tests (system + GUI); compare the counts with the P0 baseline
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"
.venv\Scripts\python.exe -m pytest tests\system tests\test_gui*.py tests\test_b8_lanes_bounded_gui.py -q -p no:warnings --junitxml=<tmp>\hw.xml
# full repo profile (AGENTS.md "every edit") before each push
.venv\Scripts\python.exe -m pytest -m "not slow and not gpu and not crosscheck" -n 6 --dist loadscope -p no:cacheprovider
# real Boundary Lab staging tests (CPU, no solve) after touching stage/clearance/job code
$env:HORNLAB_BL_REAL_TESTS="1"; .venv\Scripts\python.exe -m pytest tests\system\test_bl_stage.py -q
# GUI for browser checks (canonical checkout, after P0 step 0 adds --system-store)
.venv\Scripts\python.exe -m hornlab_search.gui --port 8799 --no-browser --root . --system-store C:\Users\hunte\Hrns\hornlab-woofer-system-wt\system_runs
```

Write files with LF line endings. A Python `write_text` on Windows writes CRLF; that happened
once in G0 and was fixed. Check with `git diff --stat` that only your lines changed.

---

## 10. Handback to the senior (required format)

Write `docs/research/system_woofer_2026-11-18/GUI_HANDBACK_<YYYY-MM-DD>.md`, commit it, and
tell the owner: "Handback ready for the senior review session: <path> at <commit>."

```
# GUI handback — <date>
## 1. State
branch, HEAD sha, commits since P0 (git log --oneline), worktree clean? (git status --porcelain)
## 2. Tests (pasted, not summarized)
junitxml counters for §9 command 1 and command 2; list every failure with a one-line cause;
mark each PRE-EXISTING (with proof) or NEW.
## 3. Phase checklist
P0..P9: done / partial / blocked, each with the acceptance line from §6 and the evidence path
(screenshot, test name, or pasted output).
## 4. Owner gates
A..F: asked when, exact owner answer (quoted), what was built as a result.
## 5. Deviations from this handoff
what, why, and the file:line.
## 6. NEEDS_SENIOR_REVIEW (the important part)
One entry per item: ID, file:line, category, what to look at, why you are unsure.
Always include entries for:
  - every new endpoint (path containment, input validation, error leakage);
  - every new job kind (argv construction, lane/lock handling, cancellation);
  - any place a number is derived (where, by which Python function);
  - any place you came near summing channels or inferring a label;
  - caching (keys, invalidation on file change, memory growth);
  - anything you could not verify in the browser.
## 7. Known issues left open
bug, impact, suggested fix, whether it blocks release.
## 8. Evidence index
screenshots folder, logs, junitxml paths.
```

**The senior's final hardening pass will:**
- review every §6 entry;
- re-run the tests and the browser check list;
- fuzz the endpoints (keys, paths, numbers);
- audit the job argv builders;
- check that no channel sum or label inference exists (grep + tests);
- re-verify the acceptance numbers in §5.4 and §5.8 against disk;
- review a11y and responsive behaviour;
- fix or file what it finds.

Make that easy: small commits, honest §6, no hidden partials.

---

## 11. Known issues in G0 to fix in P1 (found by the senior)

1. Hw pages use `<h1>` + `section-header`; the house style is eyebrow + `<h2>`.
2. Case page shows the clearance verdict twice (pill row and token row).
3. Cases KPIs omit `recorded` and `empty` counts.
4. `hw.js` keeps its own `GLOSS` map; move it to `glossary.js` `TERMS` (§8.4).
5. `data_hw.hw_cases` replays clearance for every horn case on first load (about 0.5 s total,
   cached by file stamps). Fine now; if the store grows past ~200 cases, move it to an explicit
   "Check clearance" action or a background prefetch. Note it in the handback either way.
6. The handoff summary line says "6 solved"; disk and the handoff table say 5. The ledger is
   right; do not "fix" the ledger to 6.
7. Stage-failure tokens are `STAGE_FAILED[<error type>]`, because the runner reports BL
   refusals, its own assertions and adapter bugs the same way. Keep that wording; do not
   relabel all of them as BL refusals.
