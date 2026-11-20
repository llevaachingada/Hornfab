# Pass C: GUI completion (shell lane first, then 6 parallel view lanes)

**Depends on:** Pass 0 (trio committed, checklist baseline), B2 (read models), B5 (dsp-preview).
**Where:** cloud is fine: the GUI is stdlib + vanilla JS and Chromium/Playwright are available in
the cloud container. Point the server at the committed fixture store:
`python3 -c "from hornlab_search.gui.server import main; main(['--system-store','tests/system/fixtures/case_store','--no-browser'])"`
(`--system-store` is a `gui/server.py` flag; `hornlab-search gui` does not expose it as of 2026-11-20, so lane C0
adds it to `cli.py` as a pass-through; confirm the other `server.main` flags before use). Final acceptance on the real store is local.

## Shared rules

- **No acoustics in JS.** Every number, status, Pareto flag and refusal comes from `/api/hw/*`.
- One module per view; each exports `mount(el, params)` and `dispose()`; `dispose` removes listeners,
  charts and WebGL contexts (`view3d.js`/`hw3d.js` dispose paths).
- Reuse `charts.js`, `view3d.js`, `glossary.js` and existing CSS tokens. No new dependency, no build step.
- House style: eyebrow + `<h2>` (F1). Disabled controls show a visible reason, not only a tooltip (F21).
- Only lane C0 edits `app.js`, `server.py` routing, nav, and `glossary.js`. View lanes request
  changes to those in their report.
- Lane reports: `docs/system_v1/lane_reports/C-<lane>.md` with screenshots paths (1x, scratch dir),
  checklist results, test counters.

---

## C0 - Shell (run first, alone)

**Owns:** `hornlab_search/gui/static/app.js` (routes/nav), `glossary.js`, `hornlab_search/gui/server.py`
(route table only), `hornlab_search/cli.py` (`gui --system-store` pass-through only), `tests/system/gui_hw_lifecycle.mjs` (new).
**Steps:** register routes `#/hw` (overview), `#/hw/new`, `#/hw/screens`, `#/hw/screen/<id>`,
`#/hw/cases`, `#/hw/case/<exp>/<case>`, `#/hw/compare`, `#/hw/crossover/<exp>/<case>`,
`#/hw/readiness`, each lazy-importing `hw_<view>.js` with a stub `mount/dispose` for views not yet
written. Move `hw.js`'s private `GLOSS` map into `glossary.js` (F4). Write the lifecycle harness:
for each route, mount -> navigate away -> assert no leaked listeners/canvases/WebGL contexts (F22).
Split `hw.js` into `hw_cases.js`, `hw_case.js`, `hw_readiness.js` with **no behaviour change**
(move code only) so view lanes own separate files.
**Done when:** every route mounts (stub or real), lifecycle harness green, existing GUI tests green.

## View lanes (parallel after C0)

| Lane | Owns | Backend it reads | Issues to close |
|---|---|---|---|
| C1 Overview | `hw_overview.js` | `hw_overview` backend (P8) | F11: "where am I / next step" for empty, screen-only, staged, solved states |
| C2 New system | `hw_new.js` | `data_hw_new.py` (P5) | F12; gate B allows CPU screen launch + Save-as; preview text from `jobs.preview` |
| C3 Screens | `hw_screen.js` | `data_hw_screen.py` (P2) | F10 row height/radio/clipping, panel-fit semantics, trade-off plot size |
| C4 Cases + Case | `hw_cases.js`, `hw_case.js` | `data_hw.py` read model (B2) | F2 duplicate clearance, F3 KPI census, F6 "6 solved" copy, F7 stage-failed wording, F8 polar sizing, F9 375 px |
| C5 Compare | `hw_compare.js` | `data_hw_compare.py` (P4) | F13, F18 |
| C6 Crossover + actions | `hw_crossover.js`, stage/validate dialog in `hw_case.js` via a separate `hw_actions.js` | `data_hw_dsp.py` (B5), `data_hw_stage.py` (P6) | F15, F16; sum panel shows `CAL_REQUIRED` refusal until a record exists; **Solve button stays disabled with visible reason "AUTH_REQUIRED (decision 6)"** (F17) |

C4 and C6 both touch the case page: C4 owns `hw_case.js`; C6 owns `hw_actions.js` and asks C4 (via
report) for a single mount point `<div data-hw-actions>`; C0 pre-creates that div in the split.

## Acceptance (integrator)

- [ ] Lifecycle harness green for every route.
- [ ] Browser checklist (handbook Appendix C) at 1280/1009/768/375: console clean, no horizontal
      scroll, charts sized correctly, keyboard reachable, reload-safe. Table in CONTINUITY.
- [ ] `tests/system/test_gui_hw*.py` and `tests/test_gui*.py` no worse than baseline.
- [ ] Local orchestrator repeats the checklist on the real store before merge to `main`.

## Paste-ready lane brief (fill LANE)

```
You are lane <LANE> of HornFab System v1 Pass C (GUI). Lane C0 has landed (skip this line if you
are C0). Read docs/system_v1/README.md sections 1, 2 and 4, docs/system_v1/01_CONTRACTS.md section
8, and only "Shared rules" plus your lane row/section in docs/system_v1/PASS_C_GUI.md. Edit only
your lane's files. Run the GUI on the fixture store, take 1x screenshots to the scratch dir, run the
lifecycle harness and your tests. Do not commit or edit CONTINUITY, ISSUES, INDEX or CODE_MAP.
Write docs/system_v1/lane_reports/C-<LANE>.md with files changed, test counters, checklist results
and requests for C0.
```
