# Work order — make the GUI Analysis page a real visual report (2026-11-12)

Owner's goal: **improve the report, especially on the GUI side.** The Analysis tab
(`#/analysis`) must become a visual, plain-language report page in the spirit of the per-run
`runs/<id>/report.html`, while still carrying the exact numbers a senior designer /
mathematician needs. Do not delete the feature; do not spend a long time on it.

Status of this document: **execution spec. Nothing in the product is implemented yet.**
The analysis data already exists on disk. The blocker is that the GUI cannot see it.

---

## 1. Original request (verbatim)

> can we run this `.venv\Scripts\python.exe tools\analysis\report_day.py --spec tools\analysis\specs\day_2026-11-12.yaml --out runs\analysis\day_2026-11-12`
>
> I thought we already had one that was and in process one but this shows up in the GUI and it says to do it Why don't we go ahead and do it

> What was this report supposed to show i'm kind of surprised that it's exposed as its own tab in the GUI

> Is there a way we can make this if it's exposed in GUI to be more like
> http://127.0.0.1:8765/runs/20261112T225013Z-screen-633b4f/report.html
>
> Which is generated under a run and includes way better data and visualization make sure
> that can we improve this reporting or I mean analysis function to actually produce graphs
> and visuals and stuff like and then a human to read is whos a non technical user, But also
> provides high level information the Senior Sound System Designer or mathemathcin can find
> useful as well. I want to see not even sure what how useless is right now but I don't want
> to 86 and I don't want spend a lot of time fixing it up. Render the screenshot yourself I
> don't we obviously don't need any food the same information but are you supposed to be more
> visual and easier to understand and read and more useful

The attached screenshot was the per-run report: dark page, **Convergence** chart (J vs
evaluation number, grey eval dots, accent "running best" step line, dashed `seed` reference
line), and **Objective term breakdown** (stacked bars per design, coloured by term, total J at
the right, plus a raw-values table). That is the visual grammar to match. The information
does not have to be the same.

---

## 2. Definition of done (checkable)

Open `#/analysis/day_2026-11-12` in the GUI and you see, top to bottom:

1. A one-paragraph plain-language summary + a row of KPI tiles, all real numbers.
2. Four convergence panels (g1, c2, g8, g9) with a dashed seed-level line and a
   "still improving" / "converged" badge.
3. A prominent objective-term-balance section with stacked bars.
4. A bound-walls section with gauges and a widen hint.
5. Sensitivity bars (g1 and g6), a seed-variance area, a screen-vs-verify scatter (g1),
   and a link-candidate card (g1).
6. One honest callout for the errored `v6_seeds` section, showing the message verbatim.
7. A collapsed "For the technical reader" block with the exact tables.
8. Every run id links to `#/run/<id>`; every section that has a PNG links to it.

`#/analysis` (index) shows one row per set with tools, section count, error-count badge,
generated time, and still shows the run command when there are no sets.

All existing tests stay green:

```
node --check hornlab_search/gui/static/app.js
.\.venv\Scripts\python.exe -m pytest tests/test_gui_chart_standards.py tests/test_gui_views_analysis.py -q
```

---

## 3. Hard constraints

- Checkout: `C:\Users\hunte\Hrns\hornlab-search`. Interpreter `.\.venv\Scripts\python.exe`
  (PowerShell needs the `.\` prefix). Do not work in `oc-wt\*`.
- **No git mutations** (no add/commit/checkout). The parent integrator commits.
- **Do not regenerate** `runs/analysis/day_2026-11-12`; it is the evidence fixture for this
  work. The GPU night queue is still finishing the *final* fill; re-running is a later step.
- **Do not "fix" the `v6_seeds` error.** It is correct: g6 ran `beat_cuda`, c2 ran `beat_cpu`,
  and `seed_variance` refuses to pool two different BEM implementations. Show it, don't hide it.
- Writes are limited to: `hornlab_search/gui/data.py`, `hornlab_search/gui/server.py`,
  `hornlab_search/gui/static/app.js`, `hornlab_search/gui/static/app.css`,
  `tests/test_gui_views_analysis.py` (+ optionally one new test file).
  **Do not touch** `static/charts.js`, `static/index.html`, `hornlab_search/report/html.py`,
  `tools/analysis/**`, or any non-analysis view.
- No new dependencies, no build step, no chart library. Use `charts.js` + inline SVG + CSS.
- No new hardcoded colours: use the CSS custom properties already in `app.css`
  (`--surface --viz-canvas --ink --muted --label --rule --accent --accent-soft --accent-strong
  --seed --best --band --good --warn --warn-soft --bad --bad-soft --f-display --f-body --f-mono`).
  Dark theme values are already defined; do not re-declare theme blocks.

---

## 4. What exists today (facts, verified by execution)

### 4.1 The data is already there

`runs/analysis/day_2026-11-12/` contains `REPORT.md`, `report_day.md`, `report_day.json`, and:

```
convergence_g1|convergence_c2|convergence_g8|convergence_g9   (each: convergence.json + .md + convergence_1.png)
sensitivity_g1|sensitivity_g6                                  (sensitivity.json + .md, no png)
walls_g1|walls_g6                                              (walls.json + .md + .png)
term_balance_g1|term_balance_g6                                (term_balance.json + .md + .png)
links_g1                                                       (links.json + .md + .png)
fidelity_g1                                                    (fidelity.json + .md + .png)
```

`report_day.json` has `sections[]` with one entry per spec row; the only non-ok entry:

```json
{"id":"v6_seeds","tool":"seed_variance","status":"error",
 "error":"ValueError: group 'v6_seeds' is not one task/scoring identity: ['task_config_hash_mismatch']"}
```

### 4.2 Why the page is empty

`hornlab_search/gui/data.py`:
`analysis_sets()` (~line 3930) scans the analysis root and its **immediate** subdirectories and
expects flat `<tool>.json`. `analysis_report()` (~line 3968) then reads
`<set>/<tool>.json`. But `report_day.py` writes each section into its **own** subdirectory.
Verified probe output today:

```
day_2026-11-12  tools=['report_day']   convergence/seed_variance/sensitivity/links/walls/term_balance/fidelity -> ABSENT
```

`tests/test_gui_views_analysis.py` encodes the old **flat** layout (`day_2026-11-12` fixture
writes `convergence.json`, `seed_variance.json`, … side by side). That test must keep passing.

### 4.3 The page today

`static/app.js`, block `// ── E.1: analysis page (#/analysis)`:

| line | function |
|---|---|
| 2505 | `analysisConvergenceChart(svg, cv)` |
| 2522 | `analysisConvergenceHtml(cv)` |
| 2540 | `analysisSeedVarianceHtml(sv)` |
| 2583 | `analysisSensitivityHtml(s)` |
| 2618 | `analysisLinksHtml(lnk)` |
| 2652 | `analysisWallsHtml(w)` |
| 2678 | `async function viewAnalysis(setId)` |

It has no renderer for `term_balance`, `fidelity`, `ab_compare`, `lane_parity`; they fall into
"Other tool outputs — no dedicated renderer". Errors render as "not present".

### 4.4 Reusable pieces

- `charts.js` exports `chart(svg, {...})` with
  `{W,H,xlog,ylog,xlim,ylim,xticks,yticks,xlabel,ylabel,band,hlines,vlines,series,fill,yMinor,refLines,markers,unscored,ariaLabel}`.
  `series: [{pts:[[x,y],...], color, dash, dots, r, w, opacity}]`, `refLines: [{y| x, label, dash}]`.
  Also `measuredWidth(svg, fallback)`, `logGrid`, `AXES`, `fixedRange`, `angleTicks`, `polarPlot`.
  `chart()` measures its own width and sets `data-chart`, so draw it in `requestAnimationFrame`
  after the HTML is inserted. A window resize re-runs `route()` (app.js ~5918), so the view must
  be safe to re-render.
- CSS already provides `.card`, `.stack`, `.grid2`, `.kpis`, `.kpi`, `.pill`, `.pill.good/.warn/.bad`,
  `.pill-row`, `.eyebrow`, `.tbl-wrap`, `.muted`, `.mono`, `.status-grid`, `.status-card`, `.log-tail`.
  Prefer these over new classes.
- Route for run pages already exists: `#/run/<run_id>` (app.js route table ~line 144).
- Section PNGs are real files next to each JSON; the page will link to them (new route, below).

---

## 5. Lane A — data plumbing (`hornlab_search/gui/data.py`, `server.py`, tests)

### 5.1 `analysis_sets()`

Keep every current behaviour and ordering. Add, per set:

- discover **one level** of section subdirectories; for each subdir containing a recognised
  `<tool>.json`, count it;
- `"n_sections": int`;
- `"n_errors": int` — from `<set>/report_day.json` `sections[]` entries with
  `status == "error"`; `0` when the file is absent/unreadable/malformed (never raise);
- `"tools"` becomes the union of root-level tool JSONs and section tool JSONs, deduped,
  **in `ANALYSIS_TOOL_JSONS` order** (the existing test asserts
  `["convergence","seed_variance","sensitivity","links","walls"]` for the flat fixture).

### 5.2 `analysis_report()`

Add (leave all existing keys and semantics intact):

- `"sections"`: deterministic list of
  `{"id": "<subdir>", "tool": "<tool>", "data": {...}, "files": ["basename", ...],
    "has_png": bool, "pngs": ["convergence_1.png", ...]}`
  sorted by `(tool order per ANALYSIS_TOOL_JSONS, id)`.
- `"errors"`: `[{"id","tool","status","error"}]` from `report_day.json` where status == "error".
  Copy the fields verbatim; do not rewrite the message.
- `"n_sections"`: `len(sections)`.
- `"section_index"`: `{tool: [section ids]}`.
- **Flat compatibility rule:** for each tool, if exactly one section payload exists, keep
  setting `out[tool] = payload` (so the existing flat fixtures and single-section sets behave
  exactly as today). If a tool has 2+ sections, omit the flat key — `sections` carries them.
  State this in the docstring.
- `extra_tools` keeps working as today; additionally include unknown `<stem>.json` names found
  inside section subdirs (names only).

### 5.3 `server.py` — read-only section file route

Add `GET /analysis/<set>/<section>/<file>` and `GET /analysis/<set>/<file>`:

- set id and section id must match `D.ANALYSIS_SET_ID` semantics
  (`^[A-Za-z0-9_.\-]{1,80}$`);
- filename must match `^[A-Za-z0-9_.\-]{1,120}$` and have one of `.png .md .json .html`;
- containment: `base.resolve()` must be `app.analysis_dir.resolve()` or below it (same pattern
  as `analysis_report`); otherwise 404;
- serve with `mimetypes.guess_type`; the existing `_send` already sets `nosniff` and `no-store`;
- 404 for anything else; no directory listing; no generic static handler.
- Add a comment mirroring `Handler._report`'s "only these kinds of files are served" note.

### 5.4 Tests to add

In `tests/test_gui_views_analysis.py` (extend the existing fixture with a `report_day`-style
nested set) assert:

1. nested set lists all seven tools and `n_sections == 12`, `n_errors == 1`;
2. `analysis_report()["sections"]` has the expected ids/tools and the exact `data` payload;
3. `errors[0]["error"]` contains `task_config_hash_mismatch`;
4. a tool with 2+ sections has **no** flat key, and a tool with exactly 1 does;
5. malformed `report_day.json` → `errors == []`, no raise;
6. containment: `/analysis/..%2f..` style ids and `../../etc` filenames are refused
   (`ValueError` / 404), plus a valid PNG path returns 200 with `image/png`.

### 5.5 Lane A verification

```
.\.venv\Scripts\python.exe -m pytest tests/test_gui_views_analysis.py -q
.\.venv\Scripts\python.exe -m compileall hornlab_search/gui/data.py hornlab_search/gui/server.py
.\.venv\Scripts\python.exe -c "from pathlib import Path;from hornlab_search.gui import data as D;r=Path('runs/analysis').resolve();s=D.analysis_sets(r)[0];print(s['id'],s['tools'],s['n_sections'],s['n_errors']);d=D.analysis_report(r,s['id']);print([x['id']+':'+x['tool'] for x in d['sections']]);print(d['errors'])"
```

Expected: seven tools; `12 1`; twelve `id:tool` pairs; one error dict.

---

## 6. Lane B — the page (`static/app.js`, `static/app.css`)

Replace the block from `// ── E.1: analysis page` to just before
`// ── E.3: elites catalog`. Keep `api()`, `esc()`, `currentRoot()`, `errBanner()`, `skel()`.

General rules for every section:

- A missing payload renders **nothing** (no zero, no placeholder row).
- Every number is printed from the JSON; never derive a number the JSON does not contain.
- Section header pattern: `<div class="card">` → `.eyebrow` (kicker) → `<h2>` (plain-language
  title) → `<p class="muted">` one-sentence explanation → visual → technical detail in a
  `<details>`.
- Bars/gauges may use inline `style="width:NN%"` only; everything else uses classes/tokens.

### 6.1 Section order and content

**A. Hero**

- `<h2>` = the set id (`day_2026-11-12`), `.muted` line = generated time + folder.
- One paragraph, assembled from rules (only render a sentence when its data supports it):
  - "N search runs analysed" (`len(convergence sections)`).
  - "K were still improving when their budget ended" (count of
    `last20_improvement === true`); if K > 0 add "their budgets may be too small".
  - "M knobs are pressed against a search limit" (`walls` entries with `wall_lo || wall_hi`);
    add "widening them is the cheapest next experiment".
  - "Screening overstates J by X% versus verify" (`fidelity.bias_median_pct`) + "and ranks
    designs acceptably/ weakly" (`spearman_all >= 0.6`).
  - "One section refused to run" (n errors) — see the error callout.
- **KPI tiles** (`.kpis`/`.kpi`, `<span>` label + `<b>` value), only fields that exist:
  runs analysed, best J (min `final_best`, with its run id), converged / still improving,
  knobs at a limit, screen→verify bias %, section errors.

**B. Convergence (small multiples, 2× grid via `.grid2`)**

For each `convergence` section, one card:

- Title: section id + brief (`data.brief`) + `family` + `objective v{version}`.
- Chart: `chart(svg, {xlim:[0, max n], ylim:[0, max best * 1.05], xlabel:"new valid evaluations",
  ylabel:"objective J", series:[{pts: curve.map(p=>[p.n,p.best]), color:"var(--best)", w:2}],
  refLines:[{y: curve[0].best, label:"seed", dash:true}], markers:false, ariaLabel:...})`.
  (Read the resolved colour with `getComputedStyle(document.documentElement)
  .getPropertyValue("--best")` if `chart()` does not accept CSS vars — check first.)
- Badge next to the title: `last20_improvement ? pill warn "still improving (+X%)" : pill good "converged"`.
- Under the chart, one muted line: `best J {final_best} · {n_new_valid} new valid evals ·
  within 1% after {evals_to_1pct} evals` (skip null parts).
- Refusal strip: thin segmented bar of `refusal_rate_by_kind[]` windows, each segment
  `width = rate*100%`, `title` = window + kinds; plus a muted line with total `refusals`.
- Run link: `#/run/<run_id>` (basename of `run_dir`) and `↗ report` → `/runs/<run_id>/report.html`.

**C. Objective term balance (prominent, full width, before the grid)**

- Title: "What the score is actually made of".
- One-line explainer: "Each bar is one run's score split by term. A term that fills most of the
  bar is what the optimiser spent its effort on; the weight and tolerance are what the brief
  asked for."
- For each `term_balance` section: a row header (section id · brief · n valid), then two
  stacked horizontal bars (median and mean) built from `shares` (order keys by descending
  median). Segment `width = share * 100%`, colour by term index from a fixed palette derived
  from the tokens (`--accent`, `--seed`, `--good`, `--warn`, `--bad`, `--muted`, …).
- Legend with term → weight / tolerance from `weights` and `tolerances` (blank when absent).
- `<details>` "For the technical reader" → table of `top_decile_raw` (median/p10/p90 per term).

**D. Bound walls**

- Title: "Knobs pushed against a limit".
- Explainer: "A wall means most of the best designs sit as close to a limit as the search
  allows. The knob may want more room than the box gives it."
- Per `walls` section, a table/rows: knob name, a small gauge (lo..hi track with two fills
  `frac_lo`/`frac_hi`), chips `wall lo` / `wall hi` (`pill warn`), and the `proposal[]`
  action + `reason` verbatim. Use `wall_frac`/`wall_rel` only if you can explain them; skip
  otherwise.
- Run link as in B.

**E. Sensitivity**

- Title: "Which knobs move the score".
- Explainer: "Rank correlation between a knob and J. Bars to the right mean bigger = worse;
  bars to the left mean bigger = better. This is a descriptive ranking, not a causal claim."
- Per `sensitivity` section: rows sorted by `rho_abs` desc, diverging bar from a centre line
  (`rho` in [-1,1]), knob name left, `rho` and `n` right.
- If `surrogate.available`: a second strip "importance (RandomForest, R² = …)" using
  `importance[].permutation_importance`, sorted desc.

**F. Seed variance**

- Title: "Are the results repeatable across seeds?"
- Explainer: "One run per seed. A wide spread means the best J depends on luck. The docs treat
  fewer than five seeds as a pilot, not a verdict."
- Handles both shapes: `groups` (flat) and `descriptive_historical.groups`. Per group: dots for
  each `seeds[].best_j` on a common axis, a median tick, a `ci95_median_best` band when
  present. Print `n_seeds`, `median_best`, `spread_best`, and, when `n_seeds < 5`, a
  `pill` "pilot — not a verdict".
- If `verdicts[]` exist, render them as chips only when `verdict` is not "indicative"
  (do not invent one).

**G. Fidelity (screen vs verify)**

- Title: "How honest is a screen score?"
- Explainer: "A screen solve is cheap and a verify solve is accurate. Points above the dashed
  line were flattered by the screen. Ranking agreement is what matters when choosing finalists."
- Scatter `j_screen` (x) vs `j_verify` (y) with `refLines` 45° implemented as a `series` of two
  points `[min,max]` (or use `hlines` only if a 45° line is impossible). Annotate
  `bias_median_pct`, `spearman_all`, `spearman_top5`, `n_pairs`.
- Table of pairs (`design_hash`, both J, `bias_pct`) inside `<details>`.

**H. Link candidates**

- Only when `proposed_links` is non-empty.
- Title: "Knob pairs that move together".
- Per candidate: `knob_b = scale * knob_a + offset` in mono, `R²`, and
  `r2 < 0.8 ? pill warn "candidate only — below the 0.8 bar" : pill good "strong fit"`.
- Never present this as an applied config change.

**I. Errors (honest callout)**

- Title: "One section was not reported".
- For each `errors[]`: section id, tool, and the `error` string verbatim in a `.log-tail mono`.
- One muted sentence: "A refuse-to-run is a result: this tool will not pool runs that are not
  one task/scoring identity. Nothing was estimated in its place."

**J. Technical appendix (collapsed `<details class="card">`)**

- "For the technical reader": one table per tool with the raw fields (ρ, R², CI, refusal kinds,
  n, objective version, seeds, tolerance). Reuse the payload; no new numbers.
- Raw links: each section's `files` (md/json) and PNGs via the new route; `REPORT.md` already
  rendered as today's collapsed block (keep it, move it last).

### 6.2 Index page (`#/analysis`, no setId)

Keep the empty-state block and its command verbatim. Replace the table columns with:
Set · Tools (pills) · Sections · Errors · Generated. Errors column shows
`pill bad` count only when `n_errors > 0`. Rows remain clickable to `#/analysis/<id>`.
Show `n_errors` badge only if the field exists (old payloads).

### 6.3 Degrade path

If `data.sections` is missing entirely: build an equivalent synthetic `sections` array from the
flat keys (`convergence`, `seed_variance`, …) with `id = "default"` so old fixtures still
render. If neither exists: show REPORT.md only, as today.

### 6.4 Lane B verification

```
node --check hornlab_search/gui/static/app.js
.\.venv\Scripts\python.exe -m pytest tests/test_gui_chart_standards.py tests/test_gui_views_analysis.py -q
```

Then a render check without inventing data: assemble a payload from the real files in a
throwaway script under `$env:TEMP` (never in the repo), call the new HTML builders with it
(headless: stub `document`/`window` like `tests/test_gui_chart_standards.py` does), and assert
the output contains each section title and no `undefined`/`NaN`. Paste the output.

Finally, a manual pass: start the GUI, open `#/analysis/day_2026-11-12`, confirm items 1-8 of
§2 and that all charts redraw after a window resize.

---

## 7. Suggested order of work

1. Lane A §5.1-5.3, run §5.5 probe → confirms twelve sections and one error reach the API.
2. Lane B §6.1 A-C first (hero, convergence, term balance) — that alone fixes "it's useless".
3. Lane B §6.1 D-H, then I-J.
4. Index page §6.2, degrade path §6.3.
5. Run both test suites; do the browser pass; report screenshots-free evidence (DOM text).

## 8. Do not

- Do not add a `term_balance`/`fidelity` row to `ANALYSIS_TOOL_JSONS` and stop there — the
  renderer is the point.
- Do not show `v6_seeds` as an error count only; the message must be visible.
- Do not compare or rank J across objective versions (v4, v6, v7 all appear today). Never put
  them on one axis. The existing `objectiveVersionBannerHtml` helper exists for this — reuse it.
- Do not touch `tools/analysis/**` to make the GUI easier; the payloads are already sufficient.
