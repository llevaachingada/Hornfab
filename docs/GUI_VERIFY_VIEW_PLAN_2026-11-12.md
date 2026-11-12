# GUI verify / high-resolution view — design & implementation plan (2026-11-12)

**Status:** PLAN (not implemented). Owner-approved direction: display verified (high-resolution) results inside the
existing local web GUI, in a way that is native to this repo — no build step, no new dependencies, read-only.
**Related:** `docs/GUI_PLAN.md`, `docs/GUI_INTEGRATION_PLAN_2026-10-25.md`, `docs/GUI_CONTRAST_PLAN.md`,
`docs/research/TEST_SUITE_EFFICIENCY_2026-11-12.md`, day-plan groups A (analysis toolkit) / C (calibration) /
D (night ops) / E (GUI) / G (objective v8 proposal). Boundary Lab research is folded into section 5.

**Why this exists.** The search scores candidates with fast, coarse solves ("screen"). Verify re-solves the
shortlist at higher fidelity (same objective): finer mesh where needed, a denser frequency grid, and a denser
observation balloon. Screen scores are systematically optimistic and rank their own finalists poorly (measured:
verify worse than screen in 95 of 104 paired cases, typically +25–50 %; screen top-5 vs verify rank correlation
0.1–0.3). Verify is therefore the trustworthy score and the only stored data good enough to judge polars/balloons
before printing — but today the GUI has **no verify view**: `run_detail` and the leaderboards are screen-centric,
and inline verify data (`<run>/verify/`) is invisible to run discovery.

---

## 1. Grounding — what the checkout actually supports (verified 2026-11-12)

- **Two storage layouts for verify.**
  1. *Inline* (no `--brief`): `cli.py::_verify_body` writes `<run>/verify/search.ndjson` and
     `<run>/verify/designs/<hash>/…`, with **no `run.json`, no `config.yaml`, no `best.json`**. `_run_dirs`
     only discovers top-level `RUN_ID` directories, so inline verify is currently unreachable in the GUI.
  2. *Separate run* (with `--brief`): a normal run directory whose `run.json` carries `mode:"verify"` and
     `verify_of:{run, top, brief}` (the `run` is an **absolute path**).
- **Default shortlist is `--top 5`** (not 10). Frequency counts differ per brief (`grid.verify_points_per_octave`);
  today's stored verify rows carry ~29 frequencies vs the 12-point screen grid. **Never hardcode counts — read
  `metrics.freqs_hz` / row fields.**
- **Fidelity facts:** screen 12 frequencies / 512-point balloon / ≤5,000 dof; verify ~29 frequencies / 1,024-point
  balloon / ≤7,000 dof (final 8,900). Verify meshes can equal the screen mesh when the cap is not binding; the
  solver prints that note.
- **`gui/data.py` is screen-centric.** The claim "the GUI already prefers verify rows" is true only inside
  `run_gate_audit` and campaign grouping by `auto_<brief>__<mode>`; `run_detail` and leaderboards do not merge.
  The pairing must be built explicitly — reproduce the rule in `tools/analysis/fidelity.py` (screen rows
  excluding `mode:"verify"`, verify rows from `<run>/verify/search.ndjson` plus `mode:"verify"` rows, deduped by
  highest `n`). Do **not** import `tools/` from the GUI.
- **Existing visual/route grammar to extend:** run detail already hosts sibling sub-views (`/evolution`, `/umap`,
  `/archive`, `/balloon`, `/3d`); `updateNav` highlights Runs for all `#/run/…` paths; `balloon.js` implements the
  3D balloon with `setFreq`/radar; `charts.js` has `chart()` (xlog, band, hlines, vlines, series) and `isobarMap`;
  chips/pills/tokens/contrast rules exist (`GUI_CONTRAST_PLAN.md`).

---

## 2. User workflow — the questions a horn designer asks, and where they are answered

| Question | Answer surface |
|---|---|
| Is the screen winner really best? | Verify summary strip: best verified design, screen-#1 → verify rank, top-5 overlap, rank agreement. |
| How much did the screen lie? | Bias KPI (`n_worse/n_pairs`, median bias %), Δ column, screen-J vs verify-J scatter with diagonal. |
| Is it stable across frequency and angle? | Per-design panel: one frequency scrubber synced across balloon, H/V cuts and curves; screen ghosts; band-delta chips. |
| Does it pass gates? | Gate chips per row/panel from a committed audit; "not audited" when absent — never invented. |
| Which do I export/print? | Per-design actions with explicit safety rules; compare-two-verified; exact CLI commands where the GUI cannot safely act. |

Audience nuance: the owner needs a build/print decision; the collaborator needs reproducibility and parent links;
beta testers need plain wording and a copyable command. All three must see fidelity labels — **no "winner"
without "verified"**.

---

## 3. Information architecture — decision

1. **Primary — Verify sub-view inside run detail:** `#/run/<id>/verify`, entered from a persistent
   **Verification card** on the run page. Deep-linkable, holds the dense table without bloating the main run page,
   no new top-level nav item (native: run detail already hosts sibling sub-views).
2. **Discovery — verify runs are first-class *rows*, second-class *pages*:** badge `verify` and
   `↳ verification of <parent>` in the Runs list (plus a `Mode: All/Screen/Verify` filter); opening a verify run
   redirects to the parent's Verify view with an info banner ("verification run of X; its rows are not a search");
   suppress search-history panels (convergence/terms/sensitivity) for `mode:"verify"`.
3. **Optional — a "Verified only" filter** on Runs. No dedicated top-level page (would duplicate Runs/Compare and
   separate verify from its parent).

Run-detail entry point (text wireframe):

```
Run detail top:
  [eyebrow: Run · OSSE · screen fidelity]
  KPIs
  ┌ Verification ─────────────────────────────────────────────┐
  │ 5 verified of 240 screened · best verify J 8.42           │
  │ [Open verify view →] [Verify top 5…]                      │
  │ Not verified yet: `hornlab-search verify --run "runs/<id>" --top 5` [Copy] │
  └───────────────────────────────────────────────────────────┘
```

Separate verify run opened directly:

```
[alert info] This is a verification run of <parent>. Its rows are not a search.
[Open parent verify →] [Parent run →]
```

---

## 4. Screen-by-screen design (text wireframes)

### A. Verify view — `#/run/<id>/verify`

```
← Run <name>
eyebrow  VERIFY · J v7 · run <id> · brief <name> · band 300–5.5k
h2 Verification of <name>
[pill verify · 29 freq · 1024-pt balloon · ≤7,000 dof]
[pill screen · 12 freq · 512-pt balloon · ≤5,000 dof]   [pill mixed grid?]

KPI strip:
  Verified 5 · Failed 0 · Screen bias median +18.2% · Worse on verify 5/5
  Screen #1 → verify #2 · Top-5 overlap 3/5 · Rank agreement ρ=0.30

[scatter: J screen (x) vs J verify (y), diagonal reference]   [caption]

[toolbar] Sort: Verify J ▾ | Show: All / Gate-pass / Failed
          [ ] Screen ghost   [Compare two verified…]

table (default sort verify J ascending):
 Design        Screen J  Verify J  Δ J (v−s)      Screen rank  Verify rank  Gates         dof/tris      Actions
 aaaa… OSSE     6.88      7.32     +0.44 (+6.4%) worse   1/5         2/5       [throat pass][load fail][f11 pass]  6,912 / 18k  [Open][Copy]
caption: Ranked by verify J. Screen J is context only — scored on a coarser grid.
         Δ is a fidelity diagnostic, not a ranking across modes.
```

- No audit → omit the Gates column and say "No committed gate audit for this run — no pass/fail invented."
- Failed verify row → keep it: `Verify J = –`, chip `failed · mesh_too_large`, limited panel.
- Missing screen pair → "no screen row — delta unavailable."
- Empty state → "Not verified yet. Verify re-solves the best designs at higher resolution; screen scores are not
  a print decision." + copyable `verify --run "runs/<id>" --top 5` and the `--designs h1,h2` variant.
- Running state → "Verification in progress — 3 of 5 rows written; rows appear as each design finishes."
  (Separate runs use `run.json.status`; inline verify infers from newest-row age, labelled "possibly running".)

### B. Per-design high-res panel (the "look at the horn" surface)

```
┌ Design aaaa… · OSSE · [verify] ─────────────── [Compare…] [Copy hash] [Open verify run] ┐
│ Frequency  [━━━━━━━━━●━━━━━━━━]  2.0 kHz · 17/29   [ ] show screen ghost                │
│ ┌ 3D balloon (verify, 1024 pt) ┐  ┌ H cut @ 2.0 kHz ┐  ┌ V cut @ 2.0 kHz ┐              │
│ │ orbit/zoom; dB-radius blob;  │  │ verify / screen  │  │ verify / screen  │              │
│ │ white 6 dB isobars; guides   │  └──────────────────┘  └──────────────────┘              │
│ └──────────────────────────────┘  ┌ Isobar map (frequency × angle, H & V) ┐             │
│ ┌ On-axis (mean removed) ┐ ┌ DI ┐ ┌ Ripple H/V ┐ ┌ Beamwidth H/V ┐                       │
│ │ verify solid; screen ghost dashed; f marker │ ...                                      │
│ Gates: [round throat pass] [loading fail] [f11 pass]   audit tier: verify               │
│ Density: verify 29 freq · 1024 pt · 6,912 dof  |  screen 12 freq · 512 pt · 5,004 dof    │
│ [Copy verify command] [Open balloon ↗] [Export STEP] [Report caveat]                     │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

- One frequency index drives balloon, both polar cuts, the isobar-map cursor and curve `vlines`.
- Polar cuts are ordinary line charts (x = angle, y = normalized dB, −30..0), not a new circular plot; caption:
  "each side normalized to its own on-axis; absolute level is not compared."
- 3D balloon is verify-only (single WebGL scene); offer a screen-balloon link instead of mixing tiers.
- Band-delta chips: mean |Δ|, "worst at 3.2 kHz" — labelled diagnostic.
- Fidelity pills carry **actual** counts read from the data, never hardcoded.

### C. Compare two verified designs

Inside the Verify view: `/verify/compare?a=<hash>&b=<hash>`. Two selectors limited to verified designs of this
run; overlay curves/cuts; per-frequency delta table using the existing compare-table pattern. Banner if the two
rows are not from the same verify group/objective. Caption "differences only, no verdict." Cross-run comparison
stays on `#/compare` (run level).

---

## 5. Borrowed from Boundary Lab (v0.5.0) — and what we reject

Research based on the BL repo docs/screenshots (`github.com/JWSound/boundary-lab`: README, User Guide,
`assets/mainwindow.png`, `balloon.png`, `plotviewer.png`, `forwardbeamshape.png`) and BL internals
(`src/blab/ui/balloon.py`, `ui/plots.py`, `plotting.py`), plus our `docs/BOUNDARY_LAB_0.5_RESEARCH.md`,
`docs/ab/BOUNDARY_LAB_AB.md`, `docs/research/boundary_lab_0.5/bl_inventory.md`.

**Borrow (fold into the per-design panel only — the IA above stays):**
- Results grammar: **Directivity (isobars) → Balloon → Curves** in one results surface.
- Balloon grammar: dB-radius blob (radius = max(SPL − floor, 0)), floor line, **white 6 dB isobar contours**,
  H/V/on-axis guide rays, optional protractor/radar cut, frequency × angle isobar slice — `balloon.js`/`isobarMap`
  already provide the primitives; align labels/legend with `charts.js`.
- **Discrete frequency scrubber labelled in Hz** with a "17/29" readout (BL's slider), plus an independent
  azimuth/radar control where useful.
- **Explicit A/B state** and frozen ("captured") contours for comparison — never BL's hidden hold-right-mouse.
- **Quality honesty:** point-count/density, normalisation/floor, `di_source`, view tier beside every plot.
- **Print at full stored resolution** (we re-render from stored data; we never re-solve).

**Reject:** dockable/floating panels and OS-separate result windows (loses URL state, print layout, small-screen
behaviour); hidden gestures; turbo as the sole encoding and colour-only verdicts (contrast plan + words);
implying BL-class density (our balloons are ~8–27× coarser — show actual density); mixing solve groups or
objective versions in one comparison.

---

## 6. Reuse inventory, data plumbing, endpoints

**Reuse:** routes `GET /api/run/<id>`, `/api/runs`, `/api/balloon/<run>[/<hash>]`, `/api/mesh/<run>/<hash>`,
`/api/compare`, `/api/jobs`; readers `read_ndjson`, `run_summary`, `run_detail`, `design_curves`, `balloon`,
`mesh_surface`, `run_gate_audit`, solve-group fingerprints; UI helpers `api`, `skel`, `errBanner`, `pill`, `fmt`,
`fmtHz`, `fmtDeg`, `jVersionLabel`, `objectiveVersionBannerHtml`, `runProvenanceGroup`,
`renderProvenanceBadges`, `gateAuditHtml`, `eliteGateChips`, `f11CaveatHtml`, `verdictChipHtml`; `chart()`,
`isobarMap`, `wallSection`, `initBalloon3d`/`setFreq`/`drawRadar`; tokens `--best/--seed/--warn/--bad/--good/--accent`
and classes `.pill/.kpi/.fig/.card/.tbl-wrap/.filter-bar/.balloon-controls/.grid2/.maps/.alert.warn/.hint/.mono`.

**`gui/data.py` additions (read-only, no writes, no `tools/` import):**
- `verify_sources(source_run, runs)` → inline (`<run>/verify/search.ndjson`) + sibling runs whose
  `run.json.verify_of.run` resolves to the parent (absolute path; basename fallback for moved trees).
- `verify_report(runs, run_id)` → sources, per-design screen/verify rows + ranks + deltas + gates + density,
  summary (n_verified/n_failed/n_pairs/n_worse/bias median %, Spearman all + top-5, top-5 overlap,
  best verified, screen-#1 verify rank), `comparable` flag.
- **Comparability rule:** ignore `freqs_hz.mode` (it makes every screen↔verify pair "mixed" under the existing
  fingerprint) but require same band, objective version, backend, mesh policy and `verify_points_per_octave`;
  otherwise `comparable:false`, deltas/ranking disabled with a visible reason (raw verify J still shown).
- Additive `run_detail.verification` summary (count/best/sources/link); additive `run_summary.verify_of` and
  `has_inline_verify` — include `run.json` and `<run>/verify/search.ndjson` mtimes in the summary cache key.

**New endpoints:** `GET /api/verify/<run_id>`; `GET /api/design/<run_id>/<hash>?tier=verify` (plus `tier` on
`/api/balloon` and `/api/mesh`; default unchanged); verify jobs reuse `POST /api/jobs` with
`{kind:"verify", args:{run, top, brief?}}`.

**Do not invent:** build step/npm/new dependency; in-process solving; edits to run folders; merged
screen+verify leaderboards; fabricated gates or densities ("–", "not audited", `available:false`); new colour
tokens; one-click export that silently ranks by screen J.

---

## 7. Interaction, accessibility, performance

- **One scrubber state** (verify frequency index) drives balloon `setFreq`, both polar cuts, isobar cursor and
  curve markers; URL (`?design=<hash>&f=<hz>&ghost=1`); `requestAnimationFrame` coalescing; redraw the panel only.
- **Screen ghost** checkbox persisted in localStorage; dashed `--seed`; default on.
- **Delta colouring** is direction only (`--bad` worse / `--good` better) always with signed text; no invented
  significance thresholds.
- **Sorting:** verify J (default), screen J, delta, ranks, hash, gate count; stable; selection kept by hash;
  `aria-sort`.
- **Accessibility:** keyboard selection, slider `aria-valuetext` ("2.0 kHz, verify frequency 17 of 29"), charts
  `role="img"` with design/frequency labels, live region on selection, focus-visible tokens, state always carries
  words not colour alone, reduced motion respected.
- **Performance:** fetch table first, then one design on selection; cache payloads per `run|tier|hash`; verify
  balloon ~29×1024 floats (~120–250 KB binary); `_dispose3d` before replacing the balloon; never prefetch all
  balloon payloads.

---

## 8. Implementation slices (each shippable; headless tests in `tests/test_gui_views_l2.py` style)

1. **Data/API foundation (prerequisite).** `gui/data.py`, `gui/server.py`, `tests/test_gui_verify.py`:
   `verify_sources`/`verify_report`, tier-aware readers, routes. Tests: inline + separate layouts, dedupe by
   latest `n`, failed row, missing screen pair, `available:false`, cross-band `comparable:false`, gate merge,
   invalid hash 400, route 200. Read-only, JSON-safe, no `tools/` import.
2. **Entry points and identity.** `app.js` (+ CSS only if a new class): routes before the generic run route;
   Verification card; verify-run banner; Runs-list chips/filter/parent links; compare fidelity banner. Pure-helper
   tests + `node --check`. No top-level nav item; absent verify shows the exact command; verify-run detail never
   presents search history as meaningful.
3. **Verify table/summary.** `viewVerify`, KPIs, scatter, sort/filter/selection, URL state, empty/running/failed
   states. Tests: table HTML, summary HTML, delta cell, empty HTML, query parse/build. Default verify-J sort; no
   mixed-mode ranking; gate column only with an audit.
4. **Per-design panel.** Lazy design fetch → balloon lazy load, scrub sync, ghost toggle, cuts/curves, gate chips,
   actions. Tests: band-delta stats, fidelity chips, scrub index, panel HTML; `node --check`. One design per
   fetch; failed/missing response honest; no screen substitution.
5. **Compare two verified.** Route/mode, selectors, overlays, per-frequency delta table, group banner. Only
   verified designs; no cross-run mix; "differences only".
6. *(Optional, needs API first)* **Verify selected / export.** Allow `designs` hashes in the existing verify job
   kind (`D.HASH` validation, exclusive with `top`), expose "Verify selected". Export remains command+caveat until
   `export-step` supports `--designs` (today it ranks by screen J — never offer a one-click that silently exports
   screen winners).

---

## 9. Risks / open questions (retire before building)

1. Inline vs separate verify layouts (inline has no `run.json`/`best.json`/`config.yaml`) — confirm on real data.
2. `verify_of.run` is an absolute path; parent matching must normalize + basename fallback.
3. Cross-grid comparability: `freqs_hz.mode` makes every pair "mixed"; use a fidelity-specific rule (ignore mode,
   check band/objective/backend/mesh/`verify_points_per_octave`).
4. Gate audit is optional/stale and may key verify rows under the source run id — merge both; unknown =
   "not audited", never fail.
5. Responses are overwritten by a re-verify (same `<verify>/designs/<hash>/response.npz`) — dedupe by latest `n`
   and disclose "latest solve only".
6. `n_vertices` is not in ndjson rows (only `n_dof`, `n_triangles`) — show dof/tris.
7. Default shortlist is top 5 and frequency counts vary — read from rows/metrics, never hardcode.
8. Export/report gaps: `export-step --top N` ranks by screen J and has no `--designs`; `report` requires
   `config.yaml` (inline verify lacks it).
9. Verify runs in campaigns appear as `auto_<brief>__verify`; confirm `leaders()` excludes them for Home.
10. Legacy verify dirs from before the two-lane row fields have no `lane`/`backend`; render "unknown tier" rather
    than guessing.
