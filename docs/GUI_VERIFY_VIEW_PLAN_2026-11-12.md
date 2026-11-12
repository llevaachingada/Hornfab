# GUI verify view + whole-GUI UX hardening — implementation plan (2026-11-12, v2)

**Status:** PLAN (not implemented). v2 supersedes the v1 design pass of the same date. v2 was hardened against a
**live inspection** of the GUI (built-in browser on `hornlab-search gui` against the real `runs/` tree, 425 runs,
24 inline verify folders, 16 verify runs, GPU + CPU lanes running), and widened by owner request to the
highest-value UI/UX and data-display fixes across the whole GUI, aimed at a **non-technical user**.
**Related:** `docs/GUI_PLAN.md`, `docs/GUI_INTEGRATION_PLAN_2026-10-25.md`, `docs/GUI_CONTRAST_PLAN.md`,
`docs/research/TEST_SUITE_EFFICIENCY_2026-11-12.md`, `docs/BOUNDARY_LAB_0.5_RESEARCH.md`.

**How to use this document (implementing agents).** Read section 0 (rules) and section 1 (facts). Then read **only
your own work package** in section 5. Each package lists the files you may edit, the functions you may touch,
step-by-step instructions, the tests to write, and a done-checklist. If something you need is not in your package,
do not improvise: append the question to `NOTES_FOR_SENIOR.md` and continue with the rest of the package.

---

## 0. Hard rules for every work package

1. **Read-only GUI.** The GUI never writes into a run folder, never solves in-process, and never imports
   `tools/`. New behaviour that runs work goes through the existing job system (`gui/jobs.py`, `POST /api/jobs`).
2. **No build step, no npm, no new Python or JS dependency, no new colour tokens.** Use the existing tokens
   (`--best --seed --warn --bad --good --accent`) and classes (`.pill .kpi .fig .card .tbl-wrap .filter-bar .grid2
   .alert.warn .hint .mono`).
3. **Never invent data.** Missing means you show `–`, `not audited`, `unknown`, or `available:false` with a reason.
   Never substitute screen data for verify data or the other way round. Never hardcode frequency counts, balloon
   point counts, the shortlist size or the dof cap. Read them from rows, `metrics.json` or `response.npz`.
4. **No GPU, no solver in tests.** All tests are offline and use synthetic fixtures (WP0). A GPU search is usually
   running on this machine: never run `gpu-clean`, never click Kill/Stop/Launch/Continue in a live GUI, and never
   start a job while reviewing.
5. **Labels carry words, not just colour.** Every score says its tier ("screen J" / "verify J") and objective
   version. No "winner" or "best" without "verified" or "screen".
6. **Edit only your own files and functions** (section 4 table). `app.js` is shared: touch only the functions your
   package names. If a merge conflict appears, keep both sides; never reformat code you do not own.
7. **Every push** updates `docs/CONTINUITY.md` and `docs/ISSUES.md` in the same commit (repo rule). A new doc or
   module gets a line in `docs/INDEX.md` / `docs/CODE_MAP.md` in the same commit.
8. Interpreter: `.venv\Scripts\python.exe` (see `TOOLCHAIN.md`). JS syntax check: `node --check <file>`.

---

## 1. Facts measured on 2026-11-12 (live inspection, real data)

These correct or extend v1. Implementers rely on these. Do not re-derive them.

**Verify storage: three layouts, not two.**

| Layout | How to recognise it | Count on disk | Parent link |
|---|---|---|---|
| **A. Inline** (`verify` without `--brief`) | `<run>/verify/search.ndjson` + `<run>/verify/designs/<hash>/` (metrics.json, response.npz, mesh.msh, design.json, status.json). No `run.json`, `config.yaml` or `best.json` inside `verify/`. | 24 runs | The enclosing run |
| **B. Linked verify run** (`verify --brief`) | Top-level run dir, `run.json.mode == "verify"`, `run.json.verify_of = {run, top, brief}` | 7 runs | `verify_of.run` is an **absolute path**. Some point to deleted scratchpad folders (`...\AppData\Local\Temp\...`): the parent is missing |
| **C. Standalone verify search** (`search --mode verify`, usually `--budget 1`) | Top-level run dir, `run.json.mode == "verify"`, **no `verify_of`** | 9 runs | None. It is a one-design high-fidelity solve of a config, not a verification of a run |

**Fidelity is per design, read from data.** Screen (sample): 12 frequencies, balloon grid **16×32 = 512** points.
Verify (sample): 29 frequencies, balloon grid **23×45 = 1,035** points (not 1,024). `response.npz` carries
`freqs_hz`, `spl_balloon_db`, `meta.balloon_grid`, `n_dof`, `backend`, `spl_h_db`, `spl_v_db`, `h_angles_deg`,
`v_angles_deg`, `z_throat`. Rows carry `n_dof`, `n_triangles`, `res_mm`, `peak_vram_mb`, `seconds`. There is no
`n_vertices`.

**Legacy rows are the common case.** 142 of 173 inline verify rows have **no `lane` and no `backend`** field. Treat
"unknown lane/backend" as normal and render it neutrally (`lane –`), not as a warning.

**`/api/balloon` returns JSON**, not binary: `spl` is a nested list (~29×1,035 floats, about 200–300 KB). Keep it
JSON. Cache it per `run|tier|hash` on the client.

**The run page today misleads in verify contexts (screenshots: run `…ed1da9`, verify run `…3f4992`).**
- KPI "Score: best J v4 3.86" is the best **screen** J, while the same page's gate table shows that run's verified
  designs at J 4.6–5.3. Nothing on the page says which tier 3.86 is.
- The gate-audit table renders **all ~150 audited rows inline** (page is ~12,000 px tall). Its `TIER` column is the
  audit CSV's tier: on a verify run it says `screen`.
- Opening a verify run (layout C) shows "Change vs start: no change", "Budget used 1/1", Evolution time-lapse,
  Design cloud, QD atlas, Continue run, CMA panels. None of these mean anything for a verify run.

**Whole-GUI findings (by impact).**

| # | Where | What was observed | Effect on a non-technical user |
|---|---|---|---|
| G1 | Elites | `GET /api/elites` **109 s cold, 60 s warm**, 3.1 MB. Page shows "Loading elites…" with no progress | Looks broken. Cause: per gate-audit CSV row, `run_objective_version(run_dir)` and `archive_heatmap.json` are re-read with no per-run memo |
| G2 | Launch, Typologies | `GET /api/typologies` **57 s cold, 7 s warm**, 600 KB. Launch awaits it before rendering anything (blank skeleton, no label, >8 s) | "Launch" looks dead |
| G3 | Runs list | "Newest first" sorts by run **id**. The live run is a resume of a 10-30 run, so it sits deep in the list. Table is 1,319 px wide in a 921 px wrap (sideways scroll). No mode/verify badge although `mode` is in `/api/runs` | Can't find the run that is running; can't tell verify from search |
| G4 | Home, Status, sidebar | Resumed run shows "996 / 117 evals (100%) over budget" with a full red bar. 117 is the **resume increment**, not the run budget | Reads as a fault |
| G5 | Sidebar run chip | Alternates between the GPU lane pid (14152), the CPU lane pid (7112) and "stopped search — no resumable run folder" between page loads. The red **Kill run** button follows whichever it shows | Ambiguous, and the kill target is unclear |
| G6 | Status | "Queue log" shows `queue_v5_continue_2026-10-29.log` while both lanes run today's queues | Stale information presented as current |
| G7 | Home "Best horn per brief" | ~30 briefs including legacy/test briefs (`7040`, `samonrip`, `75x35`); every line says "screen only"; no hint of verification | Can't tell which horns are trustworthy |
| G8 | Compare | Two bare `<select>`s with 425 runs each, no search, no brief filter, no guidance text | Unusable without knowing run ids |
| G9 | Compose vs Launch | Two nav items that both start runs (Compose: "Compose a run"; Launch: run/campaign form) | Which one do I use? |
| G10 | Navigation | 11 flat items mixing "see results" and "start work" | No mental model |
| G11 | Analysis | Empty state names `tools/analysis/` but gives no copyable command | Dead end |
| G12 | Run detail | 25+ sections in one scroll; key decision (is it verified? does it pass? can I print?) isn't at the top. The response charts start ~6,800 px down, under the gate table | Overload; the graphs people came for are hidden |
| G13 | All response charts | Autoscaled y axes, reference lines styled like data, H/V and start/best overlaid on one plot, no minor log grid, no solved-point markers, isobars clamp >0 dB (full list and fixes: WP9) | The same horn looks different from run to run; two different lines can look identical |

---

## 2. User workflow: the questions, and where each one is answered

| Question (plain words) | Answer surface | Package |
|---|---|---|
| What is running right now, and is it healthy? | Sidebar lane chips (GPU + CPU, both always shown), Status page | WP5 |
| Which horn is best for my brief, and can I trust it? | Home "Best horn per brief" with `verified` / `screen only` badge and next-step link | WP5 |
| Is the screen winner really best? | Verify view summary strip | WP3 |
| How much did the quick score lie? | Bias KPI, Δ column, screen-vs-verify scatter | WP3 |
| How does it sound off-axis, at each frequency? | Per-design panel: frequency scrubber, 3D balloon, H/V cuts, curves | WP6 |
| Does it pass the gates? | Gate chips from a committed audit, else "not audited" | WP3/WP6 |
| Is it ready to print? | "Ready to print?" checklist on the per-design panel | WP6 |
| What do I do next? | "Next step" banner on run detail and Home | WP4/WP5 |

Audience: the owner needs a build/print decision, the collaborator needs reproducibility, beta testers need plain
words and copyable commands. All three see tier labels on every score.

---

## 3. Information architecture (decisions; implementers do not revisit)

1. **Verify view is a sub-view of run detail:** `#/run/<id>/verify` (+ `?design=<hash>&f=<hz>&ghost=0|1`), and
   `#/run/<id>/verify/compare?a=<hash>&b=<hash>`. Entered from a **Verification card** at the top of run detail.
   No new top-level nav item.
2. **Verify runs are badged rows, not search pages.** Layout B opens with a banner and a link to the parent's
   Verify view. Layout C opens its own Verify view as a single-design verification (no pairing). In both, the
   search-history panels are hidden (section 5, WP4).
3. **Navigation is grouped, not extended** (WP5): three labelled groups in the existing sidebar:
   - **Results:** Home, Runs, Campaigns, Elites, Compare, Analysis
   - **Start work:** Briefs, Typologies, Compose, Launch
   - **System:** Status, Glossary
   Routes and hashes do not change.
4. **Plain-language layer:** every page gets one sentence under its `h2` saying what it is for, and every tier or
   score label links to its glossary entry.

### 3.1 Wireframes

Run detail, top (WP4):
```
[eyebrow: Run · OSSE · screen fidelity · brief b1w…]
h2 gcurve__osse_b1w_v4
Next step: 5 designs verified — open the Verify view to pick one to print.        [Open verify view →]
KPIs  …  "Best screen J v4  3.86"   (label now says screen)
┌ Verification ─────────────────────────────────────────────────────────────────────┐
│ verified 5 of 201 screened · best verify J 4.62 (608eef…) · screen #1 is verify #2  │
│ [Open verify view →]                                                              │
│ (none yet) Not verified yet. `hornlab-search verify --run "runs/<id>" --top 5` [Copy] │
└────────────────────────────────────────────────────────────────────────────────────┘
Gate audit — top 10 by J + every verified design   [Show all 152 ▾]   column "audit tier"
```

Verify view (WP3), per-design panel (WP6), compare (WP6): unchanged from v1 except the fixes in section 1:
```
← Run <name>
eyebrow  VERIFY · J v4 · brief <name> · band 300–8k
h2 Verification of <name>
[pill verify · 29 freq · 23×45 balloon (1,035 pt) · 2,203 dof]   [pill screen · 12 freq · 16×32 (512 pt)]
KPI strip: Verified 5 · Failed 0 · Screen bias median +18% · Worse on verify 5/5
           Screen #1 → verify #2 · Top-5 overlap 3/5 · Rank agreement ρ=0.30 (n=5)
[scatter: screen J (x) vs verify J (y), diagonal]  caption
toolbar: Sort ▾ | Show: All / Gate-pass / Failed | [x] Screen ghost | [Compare two…]
table: Design | Screen J | Verify J | Δ (v−s) | Screen rank | Verify rank | Gates | dof / tris | lane | Actions
caption: Ranked by verify J. Screen J is context only (coarser grid). Δ is a fidelity diagnostic.
```
Per-design panel:
```
Design 608eef… · OSSE · [verify] [J v4]                 [Compare…] [Copy hash] [Copy verify cmd]
Frequency [━━━━●━━━━] 2.0 kHz · 17/29     [x] screen ghost
[3D balloon, verify only]   [H cut]  [V cut]   [isobar map H | V with cursor]
[On-axis] [DI] [Ripple H/V] [Beamwidth H/V]   verify solid · screen dashed · f marker
Gates: [round throat pass] [loading fail] …   audit: docs/data/gate_audit_2026-10-29/…
Density: verify 29 f · 1,035 pt · 2,203 dof | screen 12 f · 512 pt · 2,1xx dof
Ready to print?  ✓ verified   ✗ gates (loading fails)   ✓ fits size   → Export: copy command (see caveat)
```
Layout C (standalone verify) header: `Single-design verification · no screen run to compare against` and the
table shows one row with screen columns `–`.

---

## 4. Parallel execution map

```
WAVE 0  (serial, one agent, ~1 h)   WP0  contracts: fixtures + frozen JSON + module stubs
WAVE 1  (parallel, five agents)     WP1 verify data/API     WP2 performance     WP3 verify table UI
                                    WP4 run pages identity  WP5 shell/home/nav/compare/status
WAVE 2  (parallel, two agents)      WP6 per-design panel + compare-two   WP7 verify-selected job
                                    WP9 chart standards (charts.js + run-detail chart blocks) — may run in
                                        Wave 1 too: it shares no function with WP1–WP5; WP6 then reuses it
                                    WP10 search history / CMA-ES views (Wave 1 eligible; merge after WP4)
WAVE 3  (serial, one agent)         WP8 integration + live browser acceptance pass
```

A package may start when every package in the previous wave is merged. Inside a wave, packages do not share
files or functions (table below), so they can be written at the same time and merged in any order.

| WP | May create | May edit (only these functions/blocks) |
|---|---|---|
| WP0 | `tests/gui_verify_fixtures.py`, `tests/fixtures/gui/verify_report_example.json`, `hornlab_search/gui/data_verify.py` (stub), `hornlab_search/gui/static/verify.js` (stub), `tests/test_gui_verify_contract.py` | `app.js`: `ROUTES` array (2 lines) and the import block (1 line). `server.py`: `App.get` (route stubs). `docs/INDEX.md`, `docs/CODE_MAP.md` |
| WP1 | `tests/test_gui_verify_data.py` | `data_verify.py` (all). `data.py`: `run_summary`/`_run_summary` (additive fields + cache key), `run_detail` (additive `verification` key), `balloon`, `design_curves`, `mesh_surface` (add `tier` param only). `server.py`: the verify/design/balloon/mesh branches of `App.get` |
| WP2 | `tests/test_gui_perf_elites.py` | `data.py`: `elites_catalog`, `typologies` and new private memo helpers placed directly above them. `app.js`: `viewElites`, `viewLaunch`, `viewTypologies` (loading states only) |
| WP3 | `tests/test_gui_verify_table.py` | `verify.js` (table, KPIs, scatter, states, URL helpers). `app.css`: append a `/* verify view */` block at the end |
| WP4 | `tests/test_gui_run_identity.py` | `app.js`: `viewRunsList`, `viewRunDetail` and helpers it alone calls, `gateAuditHtml` |
| WP5 | `tests/test_gui_shell_ux.py` | `index.html` (nav markup), `app.js`: `viewHome`, `viewStatus`, `viewCompare`, `viewCompose`/`viewLaunch` **header text only**, `viewAnalysis` empty state, `updateNav`, the sidebar run-pill code (~lines 540–900). `glossary.js`. `app.css`: append a `/* shell */` block. `data.py`: `leaders`, `status` (additive fields only) |
| WP6 | `tests/test_gui_verify_panel.py` | `verify.js` (panel + compare sections). `balloon.js`: add an optional `tier` argument to the fetch path and export `initBalloon3d`/`setFreq` if not exported |
| WP7 | `tests/test_gui_verify_jobs.py` | `jobs.py` (verify job args), `cli.py::_verify_body`/verify argparse **only if** `--designs` is missing (check first) |
| WP8 | `docs/GUI_VERIFY_ACCEPTANCE_2026-11-xx.md` | Fixes only for defects it finds, in the owning package's files |
| WP9 | `tests/test_gui_chart_standards.py` | `charts.js` (`chart`, `logTicks`, new helpers, `isobarMap` colour-bar/over-range band, `wallSection` untouched). `app.js`: the response-chart block of `viewRunDetail` (the `// Beamwidth vs target` … `// Throat impedance` section, ~lines 2621–2700), the same block in the campaign view (~lines 1280–1320), and the compare chart (~line 3266). `app.css`: append a `/* charts */` block |

WP2 and WP5 both list `viewLaunch`: WP2 owns its **data loading**, WP5 owns its **header text**. Merge WP2 first.

---

## 5. Work packages

### WP0 — Contracts (serial, blocks everything)

Goal: make Wave 1 parallel by freezing the data shape and providing fixtures.

1. Create `tests/gui_verify_fixtures.py` with a function `make_runs(tmp: Path) -> dict` that writes, under
   `tmp/runs/`, synthetic run folders (pattern: `tests/test_gui_views_l2.py`, no solver):
   - `R_SCREEN` = `20261112T120000Z-screen-aaa111`: `config.yaml`, `run.json` (`mode:"screen"`), `search.ndjson`
     with 8 ok rows (hashes `a1…`–`a8…`, 12 freqs) and 1 failed row; `designs/<h>/metrics.json` +
     `response.npz` (balloon grid 16×32) for the top 3.
   - Inline verify in `R_SCREEN/verify/`: `search.ndjson` rows for 4 of the top-5 hashes (29 freqs, grid 23×45,
     **no `lane`/`backend` keys**), one hash verified twice (`n` 0 and 3, the second with a different objective,
     to test "latest n wins"), one failed verify row (`ok:false, error:"mesh_too_large"`).
   - `R_LINKED` = `20261112T130000Z-verify-bbb222`: `run.json` with `mode:"verify"`,
     `verify_of:{run:"C:\\abs\\elsewhere\\runs\\20261112T120000Z-screen-aaa111", top:5, brief:"x.yaml"}`
     (absolute path from another machine: basename must still match), `search.ndjson` with 2 verify rows.
   - `R_ORPHAN` = `20261112T140000Z-verify-ccc333`: `verify_of.run` pointing at a missing folder.
   - `R_STANDALONE` = `20261112T150000Z-verify-ddd444`: `mode:"verify"`, no `verify_of`, budget 1, one row.
   - `R_XBAND` = screen run + inline verify whose verify `metrics.freqs_hz` covers a different band (for
     `comparable:false`).
   - A gate-audit CSV under `tmp/docs/data/gate_audit_test/gate_audit.csv` covering 3 hashes, one with tier
     `verify`, keyed by the **source** run id.
   Return a dict of ids and hashes.
2. Write the frozen response example `tests/fixtures/gui/verify_report_example.json` exactly matching
   section 6 (fill with plausible numbers). WP3/WP6 develop against this file.
3. Create stubs: `data_verify.py` with `verify_sources()` and `verify_report()` raising `NotImplementedError`;
   `verify.js` exporting `viewVerify(ROOT, runId, query)` that renders "Verify view coming soon" via existing
   `skel`/`errBanner` patterns.
4. `app.js`: import `viewVerify` from `./verify.js`; add **above** the `#/run/(.+)/3d` route:
   ```js
   { re: /^#\/run\/([^\/?#]+)\/verify\/compare(?:\?(.*))?$/, fn: m => viewVerify(ROOT, m[1], "compare", m[2] || "") },
   { re: /^#\/run\/([^\/?#]+)\/verify(?:\?(.*))?$/,          fn: m => viewVerify(ROOT, m[1], "table",   m[2] || "") },
   ```
   (The generic `#/run/(.+)$` is greedy; these must come first.)
5. `server.py` `App.get`: add `head == "verify" and len(parts) == 2` → `data_verify.verify_report(self.runs,
   parts[1], root=self.root)` and `head == "design" and len(parts) == 3` → `data_verify.design_payload(...)`.
6. `tests/test_gui_verify_contract.py`: fixture builder runs; example JSON has every key of section 6;
   `node --check` on `app.js` and `verify.js` (skip if `node` missing, like the L2 tests).
7. Add `data_verify.py`, `verify.js` to `docs/CODE_MAP.md`; this doc stays in `docs/INDEX.md` (update its line to
   "v2, live-inspected, WP0–WP8").

Done when: all existing GUI tests still pass, the new contract test passes, and `#/run/<id>/verify` shows the stub.

### WP1 — Verify data and API (backend)

Files: `data_verify.py`, the `data.py` functions listed in section 4, `server.py` branches.

1. `verify_sources(runs, run_id) -> list[dict]`. For run `run_id` return sources, each
   `{kind: "inline"|"linked"|"standalone", path, run_id, n_rows, newest_row_utc, status}`:
   - inline: `runs/<run_id>/verify/search.ndjson` exists.
   - linked: scan `_run_dirs(runs)` for `run.json.mode == "verify"` whose `verify_of.run` matches. Match rule:
     `Path(v).resolve() == runs/run_id` **or** `PureWindowsPath(v).name == run_id` (basename fallback).
     Memoize the scan per call; key the module cache on the `runs` dir mtime.
   - standalone: when `run_id` itself is `mode:"verify"` without `verify_of`.
   If `run_id` is a linked verify run, return `{redirect_to: <parent id or None>, parent_missing: bool}` in the
   report instead of pairing (parent_missing when the path neither resolves nor matches a basename).
2. `verify_report(runs, run_id, root)` returns the section 6 shape. Pairing rule (copy of
   `tools/analysis/fidelity.py`; do **not** import it): screen rows = run rows with `mode != "verify"` and `ok`;
   verify rows = all source rows; per hash keep the row with the **highest `n`** (tie: newest `created_utc`); add
   `"latest_only": true` when duplicates were dropped. Ranks are 1-based among ok rows of the same tier. Spearman
   via existing `data._spearman` (n<3 → `null`). Bias % = `(verify − screen) / screen × 100` per pair; median.
3. Comparability: `comparable = true` unless band, `objective_version`, backend (when both known) or mesh policy
   differ; ignore `freqs_hz.mode` and frequency count. When false: `comparable_reason` text; deltas, ranks and
   bias are `null`; raw verify J still listed.
4. Gates: reuse `data.run_gate_audit(root, run_id)`; also look rows up by the **linked** run id; unknown hash →
   `gates: null` (UI shows "not audited").
5. Density per design, read from disk: `n_freqs = len(metrics.freqs_hz)`, `balloon_grid` from
   `response.npz.meta`, `n_points = nT*nP`, `n_dof`, `n_triangles` from the row; missing → `null`.
6. Running state: linked runs use `run.json.status`; inline uses newest-row age < 30 min → `"possibly_running"`.
7. Tier-aware readers: add `tier: str = "screen"` to `balloon`, `design_curves`, `mesh_surface`; `tier=="verify"`
   reads `<run>/verify/designs/<h>/` for inline, or the linked/standalone run's `designs/<h>/`. Unknown tier →
   `ValueError` (400). Routes accept `?tier=verify`; default unchanged.
8. `design_payload(runs, run_id, h, tier)` = `design_curves` + `{tier, density, gates, row}` for one design.
9. Additive summaries: `run_summary` gains `mode`, `verify_of_run_id` (resolved basename or null),
   `has_inline_verify`; include `run.json` and `verify/search.ndjson` mtimes in the cache stamp. `run_detail` gains
   `verification: {n_verified, n_failed, best_verify_j, best_verify_hash, screen1_verify_rank, sources:[kinds]}`
   computed by calling `verify_report` (cheap path: skip curves).

Tests (`tests/test_gui_verify_data.py`, fixtures from WP0): every layout A/B/C and the orphan; latest-n dedupe;
failed row kept with `verify_j: null`; missing screen pair (`screen_j: null`, delta null); `comparable:false` on
`R_XBAND`; gate merge across source and linked id; invalid hash → 400; unknown tier → 400; `/api/verify/<id>`
200 via `App.get`; no file written under `tmp/runs` (compare a tree listing before and after); module does not
import `tools`.

### WP2 — Performance (Elites, Typologies, Launch)

1. Measure first: time `D.elites_catalog(runs, root)` and `D.typologies(root, runs)` against a copy-free read of
   the real tree (read-only) and paste the numbers in the PR.
2. `elites_catalog`: inside the loop, memoize per `run_id` the tuple `(has_run, version, heat_cells_by_hash)`.
   Build `heat_cells_by_hash` once per run (dict hash → best cell). Add a module cache keyed on
   `(tuple of CSV paths with mtimes, runs-dir mtime)`.
3. `typologies`: profile with `cProfile` and memoize the top cost the same way (expect `list_configs` /
   `catalog` / per-campaign detail). Keep output byte-identical: add a test that compares old vs new output on
   the fixture tree.
4. UI: `viewElites`, `viewTypologies`, `viewLaunch` show a labelled loading line ("Reading 3,000 audited designs…")
   and render the parts that do not need the slow payload first. `viewLaunch` must render the form from
   `briefs/jobs/configs/status` and fill the typology picker when `/api/typologies` arrives.
5. Targets on this machine: Elites warm < 3 s, cold < 15 s; Typologies warm < 2 s; Launch form visible < 2 s.

**Status 2026-11-12: implemented on branch `feat/gui-perf-wp2` (commit 7c30694, not pushed).** Measured on the
real tree: Elites 60–109 s → 3.5 s cold / 2 ms cached; Typologies warm 16–29 s → 0.9 s, cold 177 s → 38 s;
Launch no longer waits on Typologies. Causes found: per-CSV-row re-parse of each run's `config.yaml`/`run.json`/
`archive_heatmap.json` (elites); re-parsing `.msh` wall profiles for ~200 designs per call and pure-Python YAML
(typologies). **Remaining (WP2b):** cold `/api/configs` is ~42 s because `_config_seed_materializes` runs a
real seed materialization per config, cached only in memory. Persist that cache to a per-user cache file
(outside `runs/`, keyed by config path + mtime + brief mtime + package version) so a GUI restart is instant.

Tests: equality of output before/after memo on fixtures; cache invalidates when a CSV mtime changes.

### WP3 — Verify table view (frontend)

Develop against `tests/fixtures/gui/verify_report_example.json`; switch to `/api/verify/<id>` (same shape).

1. Pure helpers, exported from `verify.js` (tested in node): `parseVerifyQuery(q)`, `buildVerifyQuery(state)`,
   `deltaCellHtml(screenJ, verifyJ)` (signed text + `--bad`/`--good` direction class, `–` when either null),
   `sortRows(rows, key, dir)` (stable, nulls last), `fidelityPillsHtml(report)` (counts from data only),
   `summaryHtml(summary)`, `emptyStateHtml(runId)`, `standaloneHeaderHtml()`.
2. `viewVerify(ROOT, runId, "table", q)`: fetch report; if `redirect_to` → info banner + links (parent missing →
   "Its parent run is not in this runs folder"); render header, pills, KPI strip, scatter (`chart()` with a
   diagonal `hlines`/series; points labelled by short hash), toolbar, table, caption. Default sort verify J asc.
   Selection by hash kept across re-sorts and in the URL (`?design=`). Gates column only when
   `report.gate_audit.available`.
3. States: empty (copyable `verify --run "runs/<id>" --top 5` and the `--designs h1,h2` variant), running
   ("3 of 5 rows written"), failed row (`failed · <error>` chip), `comparable:false` alert with reason.
4. Accessibility: `aria-sort` on headers, rows focusable with Enter to select, live region announces selection.

Tests (`tests/test_gui_verify_table.py`, executed through node like the L2 guard tests): each helper with null,
negative and positive inputs; query round-trip; sort stability; empty and standalone HTML contain the command
and the words "screen" / "verify".

### WP4 — Run pages: identity, verification card, focus

Functions: `viewRunsList`, `viewRunDetail`, `gateAuditHtml`.

1. Runs list: a `mode` badge column (`screen` / `verify`); for verify rows a `↳ of <parent name>` link (or
   "parent not in this folder"); a **Mode** filter (All / Screen / Verify / Has verification); a **Sort** option
   "Last activity" (by `last`, **new default**) beside "Newest run id". Pin the running run(s) at the top with a
   `running` pill. Wrap the table so it fits 920 px: move dims and fail % into a second line of the name cell.
2. Run detail, top: a **Next step** sentence chosen by rule:
   not verified → "Screen scores are a first pass. Verify the top 5 before choosing a design." + copy command;
   verified → "N designs verified — open the Verify view to pick one."; verify run → banner (section 3.1).
3. **Verification card** under the KPIs from `detail.verification` (WP1): counts, best verify J + hash, screen #1 →
   verify rank, `[Open verify view →]`.
4. Relabel KPIs: "Best screen J vN" / "Start screen J vN". For resumed runs, budget KPI reads
   "`<n>` evals total · this resume `+<budget>`" instead of "996 / 117 over budget" (detect: `n > budget` and
   `run.json.command` contains `--resume`).
5. For `mode:"verify"` runs hide: Change vs start, Budget used, Evolution, Design cloud, QD atlas, Continue run,
   Convergence, Score breakdown start→best, CMA panels, Pin plan. Keep: KPIs that are per-design, curves, balloon,
   3D, gate audit, command.
6. `gateAuditHtml`: show top 10 by J plus every verified design; `Show all N` toggle; column header `Audit tier`;
   a verified design in the run gets a `verified` pill next to its hash.

Tests: pure helpers for next-step text, budget wording (resume and normal), hidden-panel list for verify runs,
gate table truncation; `node --check app.js`.

### WP5 — Shell, Home, Status, Compare, plain language

1. **Nav groups** in `index.html`: three `<div class="nav-group" role="group" aria-label="…">` headings (Results /
   Start work / System) around the existing links; `updateNav` unchanged in behaviour.
2. **Page purpose line**: one sentence under each page `h2` (text table in Appendix A).
3. **Lane chips** (sidebar): always render **two** chips, `GPU · <run name> · <evals>` and `CPU · <job> ·
   <state>`, from `/api/lanes` (one source; no alternation). Each Kill/Stop control names its lane and pid in the
   visible label ("Stop GPU run (pid 14152)") and keeps the existing two-step arm.
4. **Status**: queue log selection = newest log by mtime **per lane**; show the lane name and file date; older logs
   in a collapsed "Earlier queue logs" list.
5. **Home**: "Best horn per brief" gets a filter (default: briefs with a run in the last 30 days and the current
   objective version per brief; toggle "Show all briefs"), and a badge per line: `verified (J x.xx)` when any
   verification exists for that run, else `screen only` linking to the run's Next step. `leaders()` gains
   `verified_best_j`/`verified_n` additively (use `run_summary.has_inline_verify` + linked runs; no solve).
   Running-run KPI uses the WP4 resume wording (copy the helper; do not import from WP4's code paths).
6. **Compare**: replace the two selects with a filterable list (text box filters name/brief/family; brief
   dropdown; "same brief as A" checkbox default on), preselect `?a=` from the URL, and a one-line explanation
   ("Compares two runs' best designs. Only runs with the same objective version can be ranked against each other.").
7. **Compose vs Launch**: Compose header: "Build a run step by step (recommended)". Launch header: "Quick
   launch from a saved config — for experienced users." Add a link from each to the other.
8. **Analysis empty state**: copyable `.venv\Scripts\python.exe -m tools.analysis.<entry> --out runs/analysis/…`
   (read the actual entry point from `tools/analysis/` before writing it).
9. **Glossary**: add/confirm entries `screen`, `verify`, `J (score)`, `objective version`, `gate`, `f11`,
   `balloon`, `isobar`, `DI`, `beamwidth`, `dof`; make every pill/KPI label that names one of these link to it.

Tests: nav markup groups present and every route still reachable; lane chip HTML for (gpu only, cpu only, both,
none); leaders badge fields; compare filter helper.

### WP6 — Per-design high-res panel + compare two verified

1. On row selection, fetch `/api/design/<run>/<hash>?tier=verify` and (if ghost on) `?tier=screen`; cache by
   `run|tier|hash`. Never prefetch other designs.
2. One state object `{fIndex}` drives: balloon `setFreq`, H/V cut charts (x = angle, y = normalised dB −30..0),
   the isobar-map cursor, and `vlines` on curves. Coalesce with `requestAnimationFrame`. Slider
   `aria-valuetext="2.0 kHz, verify frequency 17 of 29"`. URL `f=<hz>` snaps to the nearest verify frequency.
3. Screen ghost: dashed `--seed` series on curves and cuts at the **nearest screen frequency** (label
   "screen @ 2.1 kHz" when it differs). The 3D balloon is verify only; a link opens the screen balloon.
4. Band-delta chips: mean |Δ| per curve over the overlapping band and "largest at <f>", labelled diagnostic.
5. **Ready to print? checklist** (words + icons, no colour-only): `verified` (this panel is verify tier: ✓),
   `gates` (all audited gates pass / which fail / not audited), `fits size` (bbox vs brief envelope when the brief
   has one, else "no size limit in brief"), `export` → copyable command + caveat: `export-step --top N` ranks by
   screen J; use `--designs` once WP7 lands, otherwise copy the hash and export manually.
6. Compare two verified (`/verify/compare?a=&b=`): two selects limited to this run's verified designs; overlaid
   curves and cuts at a shared scrubber; per-frequency delta table (existing compare-table pattern); banner when
   objective versions or bands differ; caption "differences only, no verdict".
7. `_dispose3d` before replacing the balloon; respect `prefers-reduced-motion`.
8. All panel charts use WP9's helpers and conventions (fixed axes, reference-line style, solved-frequency
   markers, H/V small multiples) and add WP9's circular `polarPlot` beside the H/V cut line charts, plus the
   off-axis family chart for the selected design.

Tests: band-delta stats on fixture arrays; nearest-frequency snap; checklist HTML for pass/fail/not-audited/no
size; compare query parse; `node --check verify.js balloon.js`.

### WP7 — Verify selected designs (job)

1. Check `cli.py` verify argparse for `--designs`. If present, only wire the GUI. If absent, add
   `--designs h1,h2` (mutually exclusive with `--top`, each validated with `HASH`), with a CLI test.
2. `jobs.py`: accept `{kind:"verify", args:{run, top?|designs?, brief?}}`; validate run id and hashes; reject both.
3. GUI: "Verify selected" button in the Verify view toolbar (WP3's file: add a single exported hook
   `renderVerifySelected(container, runId, hashes)` in a new section at the end of `verify.js`). It is disabled
   while the GPU lane lock is live, with the reason shown.

### WP8 — Integration and live acceptance (serial, last)

1. Full offline suite: `.venv\Scripts\python.exe -m pytest tests -k gui -q` green.
2. Start a review server **on its own port** against the real runs tree without touching the owner's GUI:
   `.venv\Scripts\python.exe -c "from pathlib import Path; from hornlab_search.gui.server import serve;
   serve(Path('.'), 8799, False, runs=Path('runs'))"`, open `http://localhost:8799` in the built-in browser.
3. Walk Appendix B; record pass/fail with a screenshot per line in `docs/GUI_VERIFY_ACCEPTANCE_<date>.md`.
4. Do not click Kill, Stop, Continue, Launch, gpu-clean or Verify selected on the real tree.

### WP9 — Chart standards: correct, honest, and laid out like audio-analysis software

**Why.** The charts were inspected on run `20261027T051600Z-screen-ed1da9` at 1400×900 and their code was read
(`charts.js::chart/logTicks/niceTicks/isobarMap`, `app.js` ~2621–2700). They are basically right: log frequency
axis, normalised polar data, isobars in the Boundary Lab / ATH / VituixCAD style (3 dB bands, −30..0 dB, white
contours, −6 dB heavier), wall section at true aspect, and a balloon using the same palette as the isobars.
The problems are scale choices and line styling that make the same horn look different from run to run, or that
make two different things look the same. Each fix below follows what horn and speaker people expect from VituixCAD,
ATH/ABEC reports, REW, Klippel and CTA-2034 ("spinorama") plots.

**Measured findings (the problem, then the convention to follow):**

| # | Chart | Today | Convention / fix |
|---|---|---|---|
| C1 | All frequency charts | Gridlines only at labelled 1-2-5 ticks (300, 500, 1k, 2k, 5k, 8k) | Log axis with **unlabelled minor gridlines at every integer × decade** (300, 400, 600, 700, 800, 900, 3k, 4k, …) and labelled majors at 1-2-5. That is the semi-log paper look every audio tool uses |
| C2 | On-axis response | y **autoscaled** to the data (here −9..+7 dB), so a 2 dB ripple and a 12 dB ripple fill the same height | **Fixed window, expanded only when data exceeds it:** −15..+10 dB, majors every 5 dB, minor lines every 1 dB. Fixed so 1 dB looks the same everywhere. Aim for about 25 dB per decade of x (the IEC 60268 drawing ratio) when width allows, but never shrink the width to get it |
| C3 | Directivity index | y autoscaled (here 4..14 dB) | **Fixed 0..15 dB** (expand to 20/25 when exceeded), ticks every 3 dB, DI target as a labelled reference line |
| C4 | Beamwidth | y ticks from `niceTicks` (0, 50, 100, 150) | Degrees use **15°/30° multiples**: y 0..180 (expand to 360 when exceeded), majors every 30°, minors every 15° |
| C5 | Beamwidth, impedance | Reference lines share colour and dash with data. Impedance: the 0.7 threshold (`--warn`, dashed) and the **start-design reactance** (`--seed`, dashed) look the same. Beamwidth: the f0 marker and the start-V curve are both dashed amber | **Reference lines** (targets, thresholds, f0, 0 dB, 1 ρc) use one neutral style: `--label` colour, **dotted** (`1 3`), 1 px, with a **right-edge text label** ("target 90°", "0.7 ρc", "f0 850 Hz"). Data series never use dotted. The start design is drawn only when "show starting design" is ticked (one toggle shared by every chart on the page, like the isobars checkbox) |
| C6 | Beamwidth, DI, on-axis | H and V on one chart, start and best overlaid: up to 6 curves plus 2 targets, with H/V coded only by dash | **H and V as two side-by-side panels with the same scales** (as the isobars already do), each with best, optional start and target. Direct-label line ends ("best", "start") as well as the legend |
| C7 | All curves | 12 screen frequencies joined by straight lines look like a dense measured curve | **Small markers at each solved frequency** (r = 2) plus a caption chip "12 solved frequencies (6/oct)" read from data. Verify curves get the same treatment (29 points). Never interpolate or smooth the lines |
| C8 | Isobars | Values above on-axis (off-axis louder than on-axis, common at horn HF lobes) are **clamped into the top 0 dB band**. Clipped to −40 dB at the low end (`data._norm_polar`) | Add one **over-range band** above 0 dB (`>0 dB`, pale pink `#FFB0C8`, legend tick "+") and an under-range note. Keep the 3 dB jet-family palette: it is the de-facto audio convention and the contour lines carry the levels without relying on colour |
| C9 | Isobars | Contours interpolate between 12 frequencies with no sign of where the data really is | **Tick marks on the x axis at solved frequencies** (short ticks under the plot) and "interpolated between N solved frequencies" in the caption (it is already there in text; add the ticks) |
| C10 | All frequency charts | The whole plot is tinted as "brief band" because the axis equals the band, so the tint carries no information. The region below the scoring floor f0 is unmarked | **Invert the shading:** leave the scored region clean and **grey-hatch the unscored parts**, below f0 ("not scored") and outside the band. Keep the f0 line |
| C11 | Run detail layout | The response charts start ~6,800 px down the page, below the 150-row gate table | Charts directly after the KPIs and Verification card (order: Isobars H/V → Beamwidth H/V → DI → On-axis → Impedance → Wall section → 3D). That is the Boundary Lab results order already chosen in section 3. The gate table moves below with WP4's truncation |
| C12 | Polar views (new, WP6) | v1 planned only straight-line angle charts | **Also offer a classic circular polar plot** at the scrubbed frequency: half or full circle by stored angle range (here ±90°), rings every 6 dB from 0 to −30, spokes every 15° (labelled every 30°), H and V overlaid (solid/dashed), screen ghost optional. Audio users read polars as circles. Keep the line chart as the "unrolled" alternative |
| C13 | Missing standard view | No off-axis response family | Add **"Off-axis responses (normalised)"**: one curve per angle at 0/15/30/45/60/75/90° from the stored polar rows, normalised to on-axis, sequential colour ramp light→dark by angle, H and V panels. This is the standard horn-evaluation graph next to the isobar map, and the data is already in `design_curves.polar_h/v` |
| C14 | Throat impedance | Normalised ×ρc axis, R solid / X dashed; good. Floor at 0 hides negative X | Keep. Allow y below 0 when X < 0 (`zlo = min(-0.5, …)`), label axis "Z / ρc", reference lines per C5 |
| C15 | Hover | Only the isobar map has a readout | One shared **hover crosshair + readout** for `chart()` ("2.0 kHz · best H 84° · start H 79°"), snapping to solved frequencies |
| C16 | Wall section, balloon, 3D | True aspect, house palette, honest captions | No change (checked). Keep |

**Steps.**
1. In `charts.js` add `logGrid(lo, hi) -> {major:[…1,2,5…], minor:[…all integer multiples…]}` and draw minor
   gridlines lighter (`--rule` at 50 % opacity) in `chart()` and `isobarMap()` when `xlog`. Keep `logTicks`
   (existing tests use it).
2. Add `chart()` options (all optional, defaults = today's behaviour so other callers are unchanged):
   `yMinor` (array), `refLines: [{y|x, label}]` (C5 style, drawn above data with right-edge labels),
   `markers: true` (C7), `unscored: [{x0, x1, label}]` (C10 hatch via an SVG `<pattern>`), `hover: true` (C15),
   `ariaLabel`.
3. Add `export const AXES = { onAxis:{lo:-15,hi:10,major:5,minor:1}, di:{lo:0,hi:15,major:3},
   beamwidth:{lo:0,hi:180,major:30,minor:15}, zrho:{lo:0,hi:1.5,major:0.25} }` and `fixedRange(spec, data)`
   that returns `spec` expanded **outward only** in whole major steps to contain the data. Unit-test it.
4. `isobarMap`: over-range band (C8), solved-frequency ticks (C9), minor log grid (C1). The colour bar gains a
   `>0` swatch at the top.
5. Rewrite the run-detail chart block to: H/V small multiples (C6), fixed ranges (C2–C4), reference style (C5),
   markers (C7), unscored hatch (C10), one shared "show starting design" toggle (C5), new off-axis family chart (C13).
   Use the same helper for the campaign view block and the compare chart so all pages agree.
6. Move the chart cards above the gate table in `viewRunDetail` (C11). Coordinate with WP4: WP4 owns the top of
   the function and the gate table; WP9 only moves the chart container `<div>` and edits inside it. Merge WP4 first.
7. Export a `polarPlot(svg, rowsH, rowsV, angles, fIndex, opts)` helper (C12) for WP6. WP6 owns where it appears.
8. Captions: every chart caption states normalisation ("relative to on-axis", "mean removed"), distance where
   known (`distance_m` from the balloon payload), the number of solved frequencies, and the tier (screen/verify).

**Tests** (`tests/test_gui_chart_standards.py`, through node like the L2 guard tests): `logGrid(300, 8000)` majors
`[500,1000,2000,5000]` + endpoints and minors containing 400, 600, 3000, 7000; `fixedRange` keeps −15..10 for
small data and expands to −20 for a −17 dB point; `chart()` with `refLines` renders a `<text>` label and a dotted
line; no data series uses the dotted dash pattern; `isobarMap` with a +2 dB cell paints the over-range colour;
markers count equals the number of finite points; `node --check charts.js app.js`.

**Done when:** Appendix B items 10–13 pass in the browser, in both themes, at 1400 px and at 900 px width.

### WP10 — Search history: CMA-ES and score distribution over time

**Inspected** on run `…ed1da9` (201 evals, 62 failures, resumed once at eval ~100): Convergence chart, Score
breakdown, Shape parameters table, Evolution time-lapse, Design cloud, QD atlas. Data on disk per CMA run:
`<run>/cma/fit.dat` (per generation: iteration, evaluations, **sigma**, **axis ratio**, best-ever, best, median,
worst, IQR, 25th percentile), `stddev.dat` (per-coordinate σ·√diag C), `axlen.dat` (principal axis lengths),
`parameters.json2`, `stoppings.json2`. The GUI reads none of these. Failed evaluations are recorded in `fit.dat`
as **1000.0** (the penalty), so the median/worst columns are 1000 whenever more than half a generation failed.

| # | Today | Fix |
|---|---|---|
| H1 | Convergence: dots above the y-limit (~9) are **clamped onto the top edge**, so a band of real points looks like a ceiling | Draw out-of-range points as small ▲ at the top edge with a count label ("14 above 9.0"). Offer a log-y toggle |
| H2 | Failures are "excluded" silently (31 % of this run) | Plot failures as grey × in a thin strip under the axis at their eval index; caption shows the count and the failure kinds |
| H3 | No sense of the **score distribution over time** | Per CMA generation (λ evals, from `fit.dat` or by grouping rows by `n // λ`): a shaded 25–75 % band plus a median line, computed **from ok rows only** (never the 1000 penalty), next to best-so-far. Generations where < 50 % succeeded get a hatch and "mostly failed" tooltip |
| H4 | Resume points are invisible (this run was resumed at ~100) | Vertical reference line at each resume boundary (from the row `created_utc` gaps or `run.json` history), label "resumed" (WP9 reference style) |
| H5 | CMA internals hidden (the CMA covariance card needs `run.json.cma_covariance`, absent on most runs) | New **"Search dynamics"** card from `cma/*.dat` (the standard pycma diagnostic plot, simplified): (a) step size σ vs evaluations (log y), (b) axis ratio (log y), (c) per-parameter σ (stddev.dat) as small multiples or a heat strip, normalised to each parameter's bound width. Plain-language caption: "σ shrinking = the search is narrowing in; axis ratio growing = some knobs matter much more than others; a flat σ late in the run = still exploring." Hide the card with a one-line note when `cma/` is absent |
| H6 | Shape-parameter table shows only the final best value | Add a per-parameter **sparkline of the best-so-far value vs eval** and a **bounds bar** (lo–hi track with a marker for best and a faint band for the top-6 spread). Parameters pinned at a bound already get chips; keep them |
| H7 | QD atlas link is shown on runs without an atlas and leads to an empty page | Show the link only when `archive_heatmap.json` exists. Otherwise omit it (the search algorithm pill already says `cma`) |
| H8 | Evolution: the large 3D box is empty by default ("3D off") | Collapse the 3D box to one line with the toggle until it is switched on; start on the 2D side/front views |
| H9 | Score breakdown bars are good but show weighted contributions without the weights | Add the weight next to each term label ("Coverage error ×1.0") and sort by best-design contribution |
| H10 | Campaign view has no cross-run history | Campaign detail: a small-multiple of best-so-far curves per family on a shared eval axis and shared y (same objective version only; mixed versions get the existing banner) |

**Steps.** (1) `data.py`: new read-only `cma_dynamics(run_dir)` that parses `cma/fit.dat`, `stddev.dat`,
`axlen.dat` (lines starting `%` are headers; columns per the header strings) into
`{available, gens:[{iter, evals, sigma, axis_ratio, best, p25, median, iqr}], stddev:[[…]], param_names}`. Use
`parameters.json2`/`config.yaml` bounds for names; null-out any value ≥ 1000 (penalty). Add it to `run_detail`
additively as `cma_dynamics`. (2) `app.js`: Convergence (H1–H4), Search dynamics card (H5), shape table (H6),
QD link (H7), score breakdown (H9). (3) `evolution.js`: H8. (4) Campaign view: H10.
Ownership: `data.py::cma_dynamics` (new) + one additive line in `run_detail` (coordinate with WP1/WP4: append,
don't reorder). `app.js`: the "How the search went" block of `viewRunDetail`, the convergence helper (~line 2076)
and the campaign-detail chart block. `evolution.js` for H8. WP10 can run in Wave 1 beside WP9; merge after WP4.

**Tests** (`tests/test_gui_search_history.py`): parse a synthetic `fit.dat` with header and penalty rows (median
1000 → null); missing `cma/` → `available:false`; per-generation quantiles from ok rows only; clamped-point count;
resume boundary detection from a row gap; `node --check`.

**Acceptance (append to Appendix B):** 14. Convergence on `…ed1da9` shows the 25–75 % band, the failure strip
(62 ×), the "resumed" line, and an "N above" marker instead of points stuck to the top edge. 15. Search dynamics
shows σ and axis ratio on log axes for `…ed1da9`, and is absent with a note on a run without `cma/`. 16. QD atlas
link is absent on `…ed1da9`.

---

## 6. Frozen API contract: `GET /api/verify/<run_id>`

Values are illustrative. The `//` comments explain fields; the fixture JSON file (WP0) must not contain them.

```json
{
  "run_id": "20261027T051600Z-screen-ed1da9",
  "name": "gcurve__osse_b1w_v4",
  "kind": "pairs",                        // "pairs" | "standalone" | "redirect" | "none"
  "redirect_to": null,                    // parent run id when this is a linked verify run
  "parent_missing": false,
  "objective_version": 4,
  "band_hz": [300, 8000],
  "sources": [{"kind": "inline", "path": "runs/<id>/verify/search.ndjson", "run_id": "<id>",
               "n_rows": 5, "newest_row_utc": "2026-10-28T21:44:33Z", "status": "finished"}],
  "state": "finished",                    // "finished" | "running" | "possibly_running" | "none"
  "comparable": true,
  "comparable_reason": null,
  "latest_only": false,
  "fidelity": {
    "verify": {"n_freqs": [29], "balloon_grid": [[23, 45]], "n_points": [1035], "dof_range": [2203, 6912]},
    "screen": {"n_freqs": [12], "balloon_grid": [[16, 32]], "n_points": [512], "dof_range": [1980, 5004]}
  },
  "summary": {
    "n_verified": 5, "n_failed": 0, "n_pairs": 5, "n_worse": 5, "bias_median_pct": 18.2,
    "spearman_all": 0.30, "spearman_top5": 0.30, "top5_overlap": 3,
    "best_verify_hash": "608eef092639", "best_verify_j": 4.622, "screen1_hash": "ad63b6311c33",
    "screen1_verify_rank": 2
  },
  "gate_audit": {"available": true, "source": "docs/data/gate_audit_2026-10-29/gate_audit.csv",
                 "labels": {"round_throat": "Round throat", "loading": "Loading"}},
  "rows": [{
    "hash": "608eef092639", "family": "OSSE",
    "screen_j": 4.40, "verify_j": 4.622, "delta_j": 0.22, "delta_pct": 5.0,
    "screen_rank": 3, "verify_rank": 1,
    "ok": true, "error": null, "n": 0, "created_utc": "2026-10-28T21:44:33Z",
    "lane": null, "backend": null,
    "n_dof": 2203, "n_triangles": 4229,
    "density": {"n_freqs": 29, "balloon_grid": [23, 45], "n_points": 1035},
    "gates": {"round_throat": true, "loading": false},
    "source_kind": "inline", "source_run_id": "20261027T051600Z-screen-ed1da9",
    "has_balloon": true, "has_mesh": true
  }]
}
```
Rules: numbers are JSON numbers or `null` (never `NaN`, run through `data.clean`); `fidelity.*` lists hold the
distinct values seen (mixed grids show more than one entry, and the UI shows a "mixed grid" pill).
`GET /api/design/<run_id>/<hash>?tier=screen|verify` = the `design_curves` payload plus
`{"tier", "density", "gates", "row"}`.

---

## 7. Interaction, accessibility, performance (applies to WP3–WP6)

- One frequency state, URL-backed, `requestAnimationFrame`-coalesced; redraw the panel only.
- Screen ghost persisted in `localStorage` (wrapped in try/catch), default on.
- Delta colour is direction only and always comes with signed text.
- Keyboard: Tab to rows, Enter selects, arrow keys move the scrubber; `focus-visible` tokens; charts `role="img"`
  with a label naming design and frequency; reduced motion respected.
- Fetch the table first, then one design on selection; never prefetch all balloons.

---

## 8. Risks / open items (retire in the named package)

| Risk | Package | Retirement |
|---|---|---|
| `verify_of.run` from another machine or deleted scratch dir | WP1 | basename fallback + `parent_missing` (fixture `R_ORPHAN`) |
| Standalone verify runs mistaken for searches | WP1/WP4 | `kind:"standalone"`, panels hidden |
| Re-verify overwrites `response.npz` | WP1 | latest-`n` rule + `latest_only` disclosure |
| `export-step` ranks by screen J, no `--designs` | WP6/WP7 | copy-command with caveat; never one-click |
| `report` needs `config.yaml` (inline verify lacks it) | WP4 | no "Make full report" on the Verify view |
| Verify campaigns `auto_<brief>__verify` in Home leaders | WP5 | add a test that `leaders()` excludes them |
| Elites/Typologies cache staleness | WP2 | mtime-keyed caches + invalidation test |
| Kill/Stop targets the wrong lane | WP5 | lane named in the label; test for two-lane state |

---

## Appendix A — page purpose lines (WP5)

| Page | Sentence under the title |
|---|---|
| Home | Where things stand: what's running, and the best horn found for each brief so far. |
| Status | The machine: GPU/CPU lanes, queues, disk and solver health. |
| Campaigns | Groups of runs that tried several horn families against one brief. |
| Runs | Every search and verification, newest activity first. |
| Analysis | Reports written by the analysis tools. This page shows them; it never runs them. |
| Elites | Designs that passed the gate audit, across all runs. |
| Compare | Put two runs side by side. |
| Briefs | Targets: coverage, band and maximum size a horn must meet. |
| Typologies | Horn families you can search, and which briefs they can meet. |
| Compose | Build a run step by step (recommended). |
| Launch | Quick launch from a saved config, for experienced users. |

## Appendix B — live acceptance checklist (WP8, on the real runs tree)

1. Home loads < 3 s; both lane chips visible and stable over 5 reloads; resumed run reads "N evals total · this
   resume +B", not "over budget".
2. Runs: default sort "Last activity" puts the running run first; Mode filter = Verify lists 16 rows with
   `verify` badges; linked rows show their parent; the 9 standalone rows say "single-design verification".
3. Run `20261027T051600Z-screen-ed1da9`: KPI says "Best screen J"; Verification card shows 5 verified; gate table
   shows ≤ 15 rows with "Show all"; Next step points at the Verify view.
4. Verify view of that run: pills read 29 freq / 1,035 pt and 12 freq / 512 pt (from data); scatter and table
   render; legacy rows show `lane –` without a warning.
5. Select a design: balloon, cuts and curves move together with the scrubber; ghost toggles; Ready to print?
   shows gate failures by name.
6. Open verify run `20261029T013620Z-verify-3f4992` (standalone): no CMA/evolution/continue panels; single-design
   header; gate table header says "Audit tier".
7. Open a linked verify run whose parent is a deleted scratch folder: "parent not in this runs folder" banner.
8. Elites < 3 s warm; Launch form visible < 2 s; Compare filter finds a run by typing part of its name.
9. Keyboard-only pass of the Verify view; dark and light theme screenshots.
10. Run detail: the first chart is visible without scrolling past the gate table; Beamwidth, DI and On-axis show
    separate H and V panels with fixed scales (on-axis −15..+10 dB, DI 0..15 dB, beamwidth 0..180° with 30° majors)
    and minor log gridlines at 300/400/600/…/7k.
11. Every reference line (targets, 0.7 ρc, 1 ρc, f0, 0 dB) is dotted grey with a right-edge text label; no data
    curve is dotted; the start design appears only when "show starting design" is ticked.
12. Markers sit at the solved frequencies; the caption says "12 solved frequencies (6/oct)" on a screen design and
    the verify count on a verify design. The region below f0 is hatched "not scored".
13. Isobar map shows solved-frequency ticks and the `>0 dB` swatch; the off-axis family chart and (in the Verify
    panel) the circular polar render for the selected design and frequency.
