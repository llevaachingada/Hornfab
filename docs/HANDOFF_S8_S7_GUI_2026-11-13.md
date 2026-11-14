# Handoff — GUI architecture and planning for the S8 discovery and S7 surrogate-validation tools (2026-11-13)

Status of this document: **planning and implementation brief. No GUI change for these tools exists yet.**
The four analysis tools and their tests are merged on `main` at `dc64fd7`. The GUI Analysis page
(`#/analysis`) already renders older Group A tools; it has **no dedicated panels** for these four and
does not parse their JSON. This document records what was built, the exact artifact contracts, the
current GUI plumbing with file:line references, and concrete implementation paths.

Owner request that produced this handoff (verbatim):

> Give me a handoff that will explain the current work that's been done thus far on all these tools and then we had all the correct implementation plans or anything else related to this so that it can do GUI architecture and planning paths based on these new features

---

## 1. Repository state and constraints

| Item | Value |
|---|---|
| Canonical checkout | `C:\Users\hunte\Hrns\hornlab-search` |
| Branch | `main`, pushed at `dc64fd7` (`feat(analysis): finish S8 discovery contracts and S7 advisory hardening`) |
| Interpreter | `.\.venv\Scripts\python.exe` (PowerShell needs the `.\` prefix) |
| `pr55-local` | `C:\Users\hunte\Hrns\hf-wt\pr55` is read-only; its last observed HEAD was `31a8958`. Do not merge it. |
| Rules | `AGENTS.md` (canonical checkout, one integrator commits, docs index in the same commit, no installed-file edits, no new solver/mesher) |

Hard constraints for the GUI lane (from `AGENTS.md` and the existing Analysis-page contract):

- The GUI **never runs an analysis** and **never imports `tools/` code** (`gui/data.py:4035`).
  It reads artifacts the tools already wrote.
- No new dependencies, no build step, no chart library. Inline SVG + the existing `charts.js`
  primitives.
- No new hardcoded colours: use the CSS custom properties in `app.css`
  (`--surface --viz-canvas --ink --muted --label --rule --accent --accent-soft --accent-strong
  --seed --best --band --good --warn --warn-soft --bad --bad-soft --f-display --f-body --f-mono`).
- No writes into `runs/`, `dataset/`, `cache/` or live queues; GUI tests are offline.
- Do not weaken or delete any existing analysis test. Preserve unknown fields (the page ignores
  fields it does not know; it never guesses values).

---

## 2. Executive summary

**Done (S8/S7 lane, merged):**

| Tool | Purpose | Output files | Tests |
|---|---|---|---|
| `tools/analysis/geometry_descriptors.py` (416 lines) | Geometry-only descriptors from a strict `Design`; separate band-aware behaviour view; navigation map | `geometry_descriptors.json` + `geometry_descriptors.md` | 37 |
| `tools/analysis/hypothesis_cards.py` (195 lines) | Provenance-checked parent/combination/ablation experiment card | `hypothesis_cards.json` + `hypothesis_cards.md` | 11 |
| `tools/analysis/qd_compare.py` (493 lines) | Equal-cost QD/Pareto comparison with frozen HV reference | `qd_compare.json` + `qd_compare.md` | 14 |
| `tools/analysis/surrogate_validation.py` (573 lines) | S7 advisory surrogate validation over stored rows | `surrogate_validation-<input_key16>.json` (no `.md`) | 21 |

Verification at `dc64fd7`: `pytest tests/test_tools_analysis_*.py -m "not slow and not gpu and not
crosscheck"` → **308 passed, exit 0**; S8-scope broad run → **329 passed, exit 0**; `compileall
tools/analysis` → exit 0. Evidence: `scratch/2026-11-13_s8/focused-s8.xml`,
`scratch/2026-11-13_s8/regression-final.xml` (scratch is git-ignored).

**Not done (this handoff):** GUI integration. Today an S8/S7 output folder appears in `#/analysis`
only as a set of file names plus `extra_tools` pills captioned *"no dedicated renderer; read them in
REPORT.md and the raw JSON. Their contents are never guessed here."* (`app.js:3314-3318`).

**Recommendation:** implement read-only panels inside the existing Analysis tab, in two small
increments: (1) contract registration + panels for the three fixed-name tools, (2) the surrogate
keyed-file discovery problem (see §10), then optional charts. Do not build a new tab or a live
analysis runner.

---

## 3. Tool contracts (what a GUI renderer can bind to)

These shapes are the tools' JSON contracts as of `dc64fd7`. `write_report` (`tools/analysis/_common.py:1095-1121`)
adds `tool` and `generated_utc` and writes with `allow_nan=False`; non-finite numbers are `null`.

### 3.1 `geometry_descriptors.json`

```jsonc
{
  "tool": "geometry_descriptors", "generated_utc": "...", "schema_version": "...",
  "descriptor_keys": ["length_mm", "mouth_width_mm", "mouth_height_mm", "mouth_aspect_w_h",
                      "mouth_projected_area_mm2", "throat_projected_area_mm2",
                      "mouth_to_throat_area_ratio", "mouth_width_over_length",
                      "mouth_height_over_length"],
  "geometry_only": true,
  "designs": [{
    "schema_version": "...", "design_hash": "...", "family": "OSSE|R-OSSE|ICW|FREEFORM",
    "units": {"length": "mm", "area": "mm2", "ratio": "dimensionless"},
    "geometry": { /* exactly descriptor_keys -> finite float */ },
    "termination": {"kind": "...", /* family-specific keys: n,s,q / tmax,m,r,b,q / angles */},
    "provenance": {"api": "hornlab_mesher.config_builder.resolve_geometry",
                   "resolver_module": "...", "resolver_source_sha256": "...",
                   "formula": "...", "resolution_mm": 8.0,
                   "mesh_built": false, "gmsh_called": false, "bem_called": false},
    "navigation_only": {"pca": "not computed", "kmeans": "not computed", "note": "..."}
  }],
  "navigation": {
    "schema_version": "geometry-navigation-v1", "navigation_only": true, "ranking": false,
    "feature_keys": [ /* 9 keys */ ],
    "standardization": {"mean": [9], "std": [9], "zero_variance_keys": []},
    "pca": {"explained_variance_ratio": [2], "components": [[2],[2]]},
    "kmeans": {"clusters": 3, "seed": 1030, "n_init": 8, "inertia": 0.0,
               "centers_standardized": [[9], ...]},
    "rows": [{"design_hash": "...", "pc1": 0.0, "pc2": 0.0, "cluster": 0}],
    "note": "PCA and k-means are navigation aids only; no quality ordering is implied."
  }
}
```

Refusals (`GeometryDescriptorError`, non-zero exit): not a `Design`; any forbidden score/task key at
any depth (case-insensitive; `j`, `score`, `objective`, `metrics`, `weights`, `target`, `brief`,
`score_identity`, `scoring_context_id`, `scalar_score`, `objective_j`, ...); `MEH`; `mid_ports`;
`cad`; `grid`; unresolvable geometry. Admitted families: `ICW`, `OSSE`, `R-OSSE`, `FREEFORM`.

GUI meaning: this is **geometry**, not acoustic quality. The navigation map is **navigation only**,
never a ranking and never acoustic similarity.

### 3.2 `hypothesis_cards.json`

```jsonc
{
  "tool": "hypothesis_cards", "schema_version": 1, "status": "proposed", "generated_utc": "...",
  "identity": {"task_id": "...", "scoring_context_id": "...",
               "objective_version": 4, "physical_spec_id": "..."},
  "resolved_context_sha256": "...",
  "parents": [{"id": "...", "design_hash": "...", "source": "...",
               "source_sha256": "...", "family": "...", "params": {}}],
  "experiments": [{"role": "parent_a|parent_b|combination|ablate_a|ablate_b|broad_control",
                   "parent_ids": ["..."], "config": "...",
                   "config_sha256": "...", "design_hash": "...", "family": "...",
                   "params": {}, "validation": "canonical_geometry_resolved",
                   "geometry_descriptors": { /* §3.1 per-design object */ },
                   "physical_feasibility": "unverified_requires_normal_evaluator",
                   "removed_feature": "(ablations only)"}],
  "expected_band_hz": [lo, hi],
  "trade_off": "...", "unknowns": ["..."], "features": ["..."], "constraints": ["..."],
  "evidence": "hypothesis only; acoustic effects and mesh feasibility unmeasured",
  "card_id": "..."
}
```

Refusals: invented/aliased parents, parent hash mismatch, missing roles, combination equal to a
parent, an ablation that does not change the combination, mixed experiment contexts, expected band
outside the task band, MEH, unsafe output paths.

GUI meaning: every field is a **proposal**. `physical_feasibility` stays
`unverified_requires_normal_evaluator`; no J, no score, no measured claim may be shown.

### 3.3 `qd_compare.json`

```jsonc
{
  "schema": "qd-compare-report-v1", "tool": "qd_compare", "generated_utc": "...",
  "identity": {"objective_version": 4, "scoring_context_id": "...", "task_id": "...",
               "spec_id": "...", "brief_id": "...", "family": "...", "weights": {}, "tolerances": {}},
  "input_manifests": {"a": {"source": "...", "sha256": "..."},
                      "b": {"source": "...", "sha256": "..."}},
  "axes": [{"name": "...", "unit": "deg|dB|...", "direction": "minimize"},
           {"name": "...", "unit": "...", "direction": "minimize"}],
  "frozen_reference": [x_ref, y_ref],
  "descriptor_space": {"names": ["..."], "ranges": [[lo,hi]],
                       "arm_reconstruction_hashes": {"<arm_id>": "sha256"}},
  "equal_cost": {"unit": "equivalent_evaluations", "total": 120,
                 "includes": ["successful","failed","refused","training","other"]},
  "arms": [{
    "arm_id": "...", "algorithm": "...",
    "cost": {"unit": "equivalent_evaluations", "successful": 0, "failed": 0, "refused": 0,
             "training": 0, "other": 0, "total": 120, "checkpoints": [ /* full ledger */ ]},
    "n_eligible": 0, "n_eligible_attempts": 0, "duplicate_eligible_attempt_ids": [],
    "n_excluded": 0, "excluded_ids": [], "outcome_categories": {"measured": 0, "...": 0},
    "front": [{"id": "...", "design_hash": "...", "reconstruction_hash": "...",
               "category": "...", "objectives": [x, y]}],
    "hypervolume": 0.0
  }, { /* arm B */ }],
  "hypervolume_difference_a_minus_b": 0.0,
  "interpretation": "descriptive navigation comparison only; no statistical win claim, ..."
}
```

Refusals: differing identity/axes/reference/descriptor space, unequal total cost, missing attempted
results, a cost ledger that disagrees with the outcome classifier, `ok:true` with an error,
design-hash/reconstruction mismatch, paused MEH.

GUI meaning: the budget is **attempt-equivalent accounting**, not elapsed time; the comparison is
**descriptive**, never a win/loss claim. Failures are charged but never plotted or archived.

### 3.4 `surrogate_validation-<key16>.json`

Written by the tool's own driver, **not** `write_report`; there is **no `.md`** and the file name
carries the input+code hash. Payload:

```jsonc
{
  "tool": "surrogate_validation", "schema_version": 1, "code_version": 2,
  "input_key": "<sha256>", "params": {"test_frac": 0.25, "k": 5, "topk": 5,
                                      "n_propose": 6, "advisory_stored_j": false},
  "advisory_only": true, "changes_defaults": false, "resumed": false,
  "stale_partial_replaced": false, "input": {"rows": "...", "pool": null},
  "path": null,
  "status": "ok" | "refused",
  "reason": "(refusals)", "detail": "(refusals)",
  "objective_version": 4,
  "metric_names": ["..."],
  "validation_mode": "advisory_stored_j" | "legacy_capability",
  "score_identity": "...",                       // advisory mode only
  "split": {"kind": "chronological", "checks": {}, "train_ids": [], "test_ids": []},
  "evaluation": {
    "n_train": 0, "n_test": 0, "n_ood_fallback": 0, "support_radius": 0.0,
    "feasibility": {"brier": 0.0, "brier_baseline": 0.0,
                    "reliability_bins": [{"bin": [lo,hi], "n": 0,
                                          "mean_pred": 0.0, "observed": 0.0}]},
    "regression": {"status": "ok" | "insufficient_data", "n_eval": 0,
                   "n_ood_fallback": 0,
                   "targets": {"j": {"mae": 0.0, "mae_baseline": 0.0, "spearman": 0.0,
                                     "interval_95_coverage": 0.0, "topk": 5,
                                     "topk_recall": 0.0, "regret": 0.0, "direction": "minimize"},
                               "<metric>": { /* mae, mae_baseline, spearman, coverage */ }}}
  },
  "proposals": {"status": "ok" | "no_pool_or_data",
                "proposals": [{"candidate_id": "...", "role": "exploit|uncertainty|diversity",
                               "predicted_j": 0.0, "uncertainty": 0.0, "in_support": true,
                               "measured": false, "status": "hypothesis"}],
                "note": "predictions are hypotheses; validate with the normal evaluator (BEM) later"},
  "complete": true
}
```

Refusals (`status: "refused"` with `reason`): mixed/unsupported objective versions, missing or
mixed `score_spec` identity, incomplete stored-label evidence, malformed rows (non-finite values,
non-bool `ok`, duplicate IDs, out-of-unit-cube `x`), no chronological split, forbidden output root,
`--advisory-stored-j` on non-v4.

GUI meaning: **advisory only**. The stored-label mode validates supplied evidence; it does not
reconstruct raw arrays and does not make the production surrogate able to score v4. OOD proposals
carry `predicted_j: null`; predictions are never measurements.

---

## 4. Where the artifacts live — and a real guard conflict

All four tools refuse an `--out` inside the live `runs/`, `dataset/`, `cache/` trees
(`geometry_descriptors.py:394-396`, `hypothesis_cards.py:179-180`, `qd_compare.py:102-109`,
`surrogate_validation.py:84-92`). The GUI's default analysis root is **`runs/analysis/`**
(`gui/server.py:38-39`).

Consequence: with the current guards, the GUI cannot see an S8/S7 output produced directly into
`runs/analysis/`. The supported workflow is:

```powershell
.\.venv\Scripts\python.exe tools\analysis\geometry_descriptors.py --input scratch\2026-11-13_s8\designs.json --out scratch\2026-11-13_s8\geometry
.\.venv\Scripts\python.exe -m hornlab_search.gui --analysis-dir scratch\2026-11-13_s8
```

(Or copy a finished artifact set into `runs/analysis/<set>/` — a human copy is not a tool write.)
Decide in §10 whether to add an explicit, narrow exception for `runs/analysis/` in the tools (a tool
change with its own tests) or keep the documented `--analysis-dir` workflow. **Do not** weaken the
guard silently.

---

## 5. Current GUI architecture (verified, at `dc64fd7`)

### 5.1 Server/API

- `App.__init__`: `self.analysis_dir = analysis_dir or self.runs / "analysis"`
  (`hornlab_search/gui/server.py:34-39`).
- API: `/api/analysis` → `D.analysis_sets(...)`; `/api/analysis/<set>` → `D.analysis_report(...)`
  (`server.py:134-137`).
- File serving: `/analysis/<set>/<name>` and `/analysis/<set>/<section>/<name>`, suffixes
  `.png/.md/.json/.html`, containment-checked against the analysis root, no directory listing
  (`server.py:360-361, 421-463`).
- CLI flag `--analysis-dir` (`server.py:555-559`).

### 5.2 Python data layer (`hornlab_search/gui/data.py`)

- `ANALYSIS_TOOL_JSONS` — the fixed whitelist of parsed tools (`data.py:4044-4046`):
  `convergence, seed_variance, sensitivity, links, walls, ab_compare, lane_parity,
  term_balance, fidelity, report_day, parameter_study, source_fidelity`.
- `analysis_sets(root)` (`data.py:4057-4121`): lists the root (".") and immediate subdirectories that
  hold any `.json` or `REPORT.md`; per set returns `id, files, tools, generated_utc, has_report_md,
  n_sections, n_errors`. `files` includes only `*.json` and `REPORT.md` (`data.py:4088-4089`) —
  `<tool>.md` is **not listed** even though the file route can serve it.
- `analysis_report(root, name)` (`data.py:4124-4244`): parses only whitelisted `<tool>.json`
  (`payloads`), supports `report_day` section subdirectories, exposes a whitelisted tool as the flat
  key `<tool>` (`4226-4232`), returns `extra_tools` = non-whitelisted JSON stems as names only
  (`4212-4213`), and `REPORT.md` text capped at 200 000 chars (`4234-4243`).
- Unknown tools are deliberately never parsed: *"extra_tools (passed through as names only; Group A
  may add fields/tools at any time)"* (`data.py:4127`).

### 5.3 Client (`hornlab_search/gui/static/app.js`)

- `ANALYSIS_SECTION_TOOLS` (`app.js:2644-2645`) — the JS-side section order/allow-list. It is a
  **second, independent list**; it already omits `ab_compare`, `lane_parity` and `report_day`
  (Python parses them, the page ignores them). Adding a tool to Python alone exposes JSON at the API
  but renders nothing; adding it to JS alone renders nothing because the payload is absent.
- `analysisSectionsOf(d)` (`app.js:2686-2712`): uses `d.sections[]` when present, otherwise rebuilds
  sections from flat keys for tools in `ANALYSIS_SECTION_TOOLS`.
- `analysisPageHtml(d)` (`app.js:3321-3340`) composes, in order: hero, objective-version banner,
  term balance, convergence, walls, sensitivity, seed variance, fidelity, links, M1 study cards,
  errors, `analysisExtrasHtml`, technical appendix.
- `analysisExtrasHtml` (`app.js:3314-3318`) renders the `extra_tools` pills with the
  "no dedicated renderer" caption.
- Technical appendix: `ANALYSIS_APPENDIX_FIELDS` (`app.js:3204-3216`) per-tool scalar fields;
  `_anFileLinks` (`app.js:3227-3235`) builds links from section `files`/`pngs`.
- Charts are **pure HTML builders that register draw jobs**; `_anChartJob` (`app.js:2738-2743`) and
  `_anDrawCharts` (`app.js:2744-2752`) run in a `requestAnimationFrame` after insertion and redraw
  on route/resize. No chart library.
- Helpers available: `_anNum`, `_anPct`, `_anObj`, `_anArr`, `_anRunId`, `_anRunLink`,
  `_anSectionHead`, `_anKpi`, `pill`, `fmt`, `esc`.

### 5.4 Tests

- `tests/test_gui_views_analysis.py` — literal JSON fixtures, set listing, flat/nested payloads,
  traversal refusals, file-route containment, `extra_tools` names (`:137`).
- `tests/test_gui_views_analysis_m1.py` — the two frozen M1 study artifacts; use it as the pattern
  for adding a new tool panel with exact-value assertions (`:47-48` asserts whitelist membership).
- `tests/test_gui_chart_standards.py` — chart conventions.
- Run: `node --check hornlab_search/gui/static/app.js` and
  `.\.venv\Scripts\python.exe -m pytest tests/test_gui_views_analysis.py tests/test_gui_views_analysis_m1.py tests/test_gui_chart_standards.py -q`.

### 5.5 What happens today with an S8 folder

Pointing `--analysis-dir` at a folder containing e.g. `qd_compare.json`:

- the set is listed (`files` contains the JSON);
- `/api/analysis/<set>` returns `extra_tools: ["qd_compare"]` and **no** `qd_compare` key;
- the page shows the pill caption; the JSON values are never displayed;
- a `.md` beside it is not in `files`, so it is not linked (the route could serve it by exact URL).

---

## 6. Gap list (checkable)

| Tool | Missing in GUI |
|---|---|
| geometry_descriptors | Whitelist entry; descriptor table; resolver SHA provenance; termination block; PCA/k-means navigation panel with the navigation-only caption; `.md` link |
| hypothesis_cards | Whitelist entry; identity/parents panel; six-role matrix including `removed_feature`; expected band; trade-off/unknowns/features/constraints; "unverified" callout; `.md` link |
| qd_compare | Whitelist entry; identity header; axes/units/reference; equal attempt-equivalent cost pill; per-arm ledger + outcome categories; front scatter with frozen reference; excluded/duplicate tables; interpretation text |
| surrogate_validation | Discovery for keyed filenames (§10); status/refusal panel; split counts; feasibility Brier + reliability bins; regression table incl. J top-k recall/regret/coverage; proposals with OOD nulls and `measured:false`; advisory-mode and provenance labels |
| all | `files` listing does not expose `<tool>.md`; no tests; no INDEX/continuity note for GUI panels |

No ISSUES row currently tracks this GUI work; the plan row is
`docs/research/COUNCIL_REVIEW_AND_IMPL_PLAN_2026-11-12.md:235` (S10: "trade-off/novelty maps,
hypothesis cards", "add S3/S4/S6/S8 panels incrementally").

---

## 7. Implementation paths

### Option A — recommended: read-only panels in the existing Analysis tab

Two increments, each independently shippable and testable.

**A1. Contract registration + three fixed-name tools (geometry, hypothesis, QD)**

1. `gui/data.py`:
   - Extend `ANALYSIS_TOOL_JSONS` with `"geometry_descriptors"`, `"hypothesis_cards"`, `"qd_compare"`.
   - Decide whether `files` should also list `<tool>.md` (recommended: add `p.name.endswith(".md")`),
     or add a per-tool `md` field. Keep `REPORT.md` behaviour unchanged.
   - No parsing beyond the existing verbatim pass-through; do not validate payloads in the API.
2. `gui/static/app.js`:
   - Extend `ANALYSIS_SECTION_TOOLS` with the three names (order controls page order; put
     `qd_compare` after `seed_variance`, `geometry_descriptors` and `hypothesis_cards` at the end
     before `parameter_study`, or as agreed).
   - Extend `ANALYSIS_APPENDIX_FIELDS` with scalar provenance fields
     (e.g. geometry: `schema_version`; hypothesis: `status`, `card_id`, `resolved_context_sha256`;
     QD: `schema_version`, `hypervolume_difference_a_minus_b`, `equal_cost`).
   - Add pure builders `analysisGeometryDescriptorHtml(data)`,
     `analysisHypothesisCardHtml(data)`, `analysisQdCompareHtml(data)` and wire them into
     `analysisPageHtml`.
   - Use `_anChartJob`/`_anDrawCharts` only for the two scatter plots (geometry navigation,
     QD front). Tables and KPI tiles need no chart.
3. Tests: new `tests/test_gui_views_analysis_s8.py` with one literal fixture per tool copied from the
   tool tests (do **not** import `tools/`). Assert: whitelist membership, flat payload exposure,
   panel marker + exact key values, absent/invalid payload renders nothing or a verbatim refusal,
   `extra_tools` no longer contains the registered names.

**A2. Surrogate validation discovery** — see §10.

### Option B — minimal registration only

Add the names to both lists and the appendix fields, rely on the existing scalar appendix and raw
file link, no dedicated panels/charts. This is a small PR and immediately stops the misleading
"no dedicated renderer" caption, but it barely improves comprehension. Only acceptable as a
stop-gap.

### Option C — a separate "Discovery" tab

Would need a new server route, nav entry, tests and a separate evidence doc. Not recommended: the
Analysis tab is exactly "read-only rendering of stored analysis outputs" (`data.py:4034-4039`), and
these tools are analysis outputs. A second tab duplicates discovery, error and file-serving logic.

### Guardrails for all options

- Add nothing that executes a tool, shells out, or imports `tools/analysis/*` from the GUI.
- Never derive/patch missing numbers in JS. A missing field renders "not present"; an invalid
  payload renders its refusal/`status` verbatim.
- Never rank hypotheses, never call PCA clusters "similar designs", never call QD predictions a
  measured outcome, never present attempt-equivalent cost as wall time.
- Keep unknown fields passing through untouched (the page already ignores unknown keys).

---

## 8. Panel specifications (data binding + wording)

### 8.1 Geometry descriptors

- Header: "Geometry descriptors — N designs; families …; resolver `<module>` @ `<sha256[:12]>`;
  resolution 8 mm; no mesh, no gmsh, no BEM."
- KPI tiles: designs, distinct families, mouth W×H range, area-ratio range, clusters.
- Table (one row per design): design_hash (mono, truncate with title), family, length, mouth W×H,
  aspect W/H, mouth area, throat area, mouth/throat ratio, W/L, H/L. Units in the column headers.
- Provenance card: `api`, `resolver_source_sha256` (full in appendix), `formula`, and the three
  false flags `mesh_built/gmsh_called/bem_called`.
- Navigation card: scatter of `navigation.rows` (pc1 vs pc2) coloured by cluster using the existing
  CSS vars; show `pca.explained_variance_ratio` and `kmeans.seed/n_init/inertia`; print
  `navigation.note` verbatim.
- Honest label: "Geometry only. Absolute scale is real: a scaled copy behaves differently at a
  fixed frequency. Navigation clusters are not acoustic similarity."

### 8.2 Hypothesis card

- Banner: `status: proposed`, short `card_id`, identity chips (objective vN, task, scoring context,
  physical spec).
- Parents: two cards with id, family, design_hash, source path, `source_sha256[:12]` (full in
  appendix); config values in a folded block (params can be large).
- Role matrix: six rows; columns role, design_hash, config, removed feature (ablations only),
  validation, physical feasibility. No J, no score.
- Lists: expected band, trade-off, features, unknowns, constraints.
- Prominent warning (verbatim from `evidence`): "hypothesis only; acoustic effects and mesh
  feasibility unmeasured". Never render a predicted benefit as a result.

### 8.3 QD/Pareto comparison

- Identity header: objective version, scoring_context_id, task_id, spec_id, family; the two input
  manifest sources + SHA-256 prefixes.
- Cost pill: "Equal total: `<total>` attempt-equivalent evaluations — successful, failed, refused,
  training and other are all charged. This is accounting equality, not elapsed time."
- Arms table: arm, algorithm, eligible, eligible attempts, duplicates, excluded, hypervolume.
- Two scatter panels (or one overlaid with distinct markers): x = `axes[0].name` [unit],
  y = `axes[1].name` [unit]; eligible points; front polyline; dashed lines at `frozen_reference`;
  excluded points are **not** plotted (list ids in a table).
- Ledger: `outcome_categories` chips, `excluded_ids`, `duplicate_eligible_attempt_ids`.
- Print `interpretation` verbatim; show `hypervolume_difference_a_minus_b` as a descriptive number
  only.
- Missing/refused payload: render the tool's stderr text or "not present", never a fabricated chart.

### 8.4 Surrogate validation

- Mode/status chips: `advisory_stored_j` vs `legacy_capability`; `advisory_only: true`,
  `changes_defaults: false`; `resumed`, `code_version`, `input_key[:12]`.
- Refused: `reason` and `detail` verbatim; no metric cards.
- Split: train/test counts, `n_ood_fallback`, `support_radius`, `checks`.
- Feasibility: Brier and baseline side by side (lower is better); reliability table/bins
  (`predicted` vs `observed`, n).
- Regression: if `insufficient_data`, show status + OOD count only. If `ok`: a J row with MAE,
  baseline MAE, Spearman, top-k recall, regret, 95% interval coverage; a per-metric table with the
  same fields minus top-k.
- Proposals: candidate, role, prediction (`null` → "no prediction (outside training support)"),
  uncertainty, `measured: false`, `status: hypothesis`; print the tool note.
- Standalone disclaimer: "Stored-label mode validates supplied evidence only. It cannot reconstruct
  raw arrays and does not make the production surrogate score v4."

---

## 9. How to produce fixture artifacts (offline, for GUI development)

```powershell
# 1) Geometry: input is exactly [{"family": "...", "params": {...}}, ...]
.\.venv\Scripts\python.exe tools\analysis\geometry_descriptors.py `
  --input scratch\2026-11-13_s8\designs.json --out scratch\2026-11-13_s8\geometry

# 2) Hypothesis card: a spec JSON referencing real parent JSON files and experiment configs
.\.venv\Scripts\python.exe tools\analysis\hypothesis_cards.py `
  --spec scratch\2026-11-13_s8\card_spec.json --out scratch\2026-11-13_s8\cards

# 3) QD/Pareto: two arm manifests with identical identity, axes, reference and total cost
.\.venv\Scripts\python.exe tools\analysis\qd_compare.py `
  --a scratch\2026-11-13_s8\arm_a.json --b scratch\2026-11-13_s8\arm_b.json `
  --out scratch\2026-11-13_s8\qd

# 4) Surrogate validation: rows JSONL (+ optional pool JSONL)
.\.venv\Scripts\python.exe tools\analysis\surrogate_validation.py `
  --rows scratch\2026-11-13_s8\rows.jsonl --out scratch\2026-11-13_s8\surrogate `
  [--pool ...] [--advisory-stored-j]
```

Then start the GUI with `--analysis-dir scratch\2026-11-13_s8` and open `#/analysis`.
For tests, copy the exact payload literals from `tests/test_tools_analysis_*.py` (they already carry
valid and malformed cases) rather than executing the tools from the test suite.

---

## 10. Surrogate keyed-file discovery (decision needed)

`surrogate_validation` writes `surrogate_validation-<input_key16>.json` and no `.md`; a folder can
hold several keys from different inputs/parameters. `analysis_report` only reads the exact
`<tool>.json`, so keyed files never become the flat `surrogate_validation` payload; they appear in
`extra_tools` as `surrogate_validation-<hash>` names.

Options, in preference order:

1. **GUI-side glob (recommended):** in `data.py`, when no `surrogate_validation.json` exists, find
   `surrogate_validation-*.json` in the set, read each header, prefer `complete: true`, then the
   newest `generated_utc` (payloads do not carry `generated_utc`; use file mtime or the newest key),
   expose it as `surrogate_validation`, and list every candidate under
   `surrogate_validation_candidates` (name, input_key[:12], status, mtime) for the panel to show.
   Add a containment-safe reader; never execute the tool.
2. **Tool-side stable alias:** have the tool also write/refresh `surrogate_validation.json` as a
   copy of the newest complete payload. Simple for the GUI, but duplicates truth and needs a tool
   test; only with owner approval because the tool is already merged and its keyed name is part of
   its resume contract.
3. **Do nothing:** keep keyed names in `extra_tools`; the panel never appears. Acceptable only if
   surrogate GUI visibility is deferred.

Whichever option is chosen, the panel must state which key/mode produced the shown numbers.

---

## 11. Test plan and acceptance

Minimum new coverage (offline; no GPU, no solver, no analysis execution):

1. `tests/test_gui_views_analysis_s8.py`:
   - each of the four tools is in `D.ANALYSIS_TOOL_JSONS` (and in `ANALYSIS_SECTION_TOOLS` via a
     served-page assertion);
   - a fixture set is listed and the flat payload is exposed verbatim;
   - a registered tool's name disappears from `extra_tools`;
   - the rendered HTML contains the panel marker, an exact numeric value, and the required
     warning text (navigation-only / hypothesis only / attempt-equivalent / advisory-only);
   - a refused/`insufficient_data` payload renders the status verbatim and no invented metric;
   - malformed JSON never raises (existing defensive contract);
   - for surrogate: two keyed files select the expected one (if Option 1 is implemented).
2. Existing tests stay green, including the `extra_tools` assertion at
   `tests/test_gui_views_analysis.py:137` (if the fixture uses a registered stem, update it to an
   unregistered one — do not delete the coverage).
3. Commands:
   ```powershell
   node --check hornlab_search/gui/static/app.js
   .\.venv\Scripts\python.exe -m pytest tests/test_gui_views_analysis.py `
     tests/test_gui_views_analysis_m1.py tests/test_gui_chart_standards.py -q
   .\.venv\Scripts\python.exe -m pytest tests/test_gui_views_analysis_s8.py -q
   ```
4. Docs: update `docs/CODE_MAP.md` (GUI additions), `docs/INDEX.md` (this handoff already indexed),
   and add a CONTINUITY entry + ISSUES row with the exact commands and results.
5. Evidence: paste the test tails (exit codes) into the handoff/PR body. Screenshots are optional and
   must be same-environment evidence, not cross-machine truth.

Definition of done for the lane: an S8/S7 output folder renders readable panels (tables + honest
labels) in `#/analysis`, the page never guesses or ranks, all listed tests pass offline, and no tool
runs from the GUI.

---

## 12. Ownership and sequencing

| Lane | Files | Notes |
|---|---|---|
| GUI data/API | `hornlab_search/gui/data.py`, `tests/test_gui_views_analysis_s8.py` | Add whitelist, md listing, surrogate discovery helper |
| GUI client | `hornlab_search/gui/static/app.js` (+ `app.css` only if unavoidable), GUI tests | Add section list, appendix fields, builders, chart jobs |
| Docs/integration | `docs/CODE_MAP.md`, `docs/INDEX.md`, `docs/CONTINUITY.md`, `docs/ISSUES.md` | Same commit as the GUI code |

Keep the two increments separate: (A1) three fixed-name tools, (A2) surrogate discovery. Each with
its own tests and CONTINUITY evidence. The parent integrator commits; do not have two agents edit
`app.js` concurrently.

---

## 13. Open decisions

1. Surrogate keyed files: GUI glob (Option 1) vs tool-side stable alias (Option 2) vs defer.
2. Should the tools permit `--out runs/analysis/<set>`? Today they refuse any path under `runs/`.
   If yes, add a narrow, tested exception; if no, document `--analysis-dir` as the only workflow.
3. Should `files` list every `.md` (recommended) or only `REPORT.md` plus a per-tool `md` field?
4. Panel placement/order in `ANALYSIS_SECTION_TOOLS` (before or after the M1 study cards).
5. Charts: inline SVG for the two scatters (recommended) vs no charts at all in A1.
6. Whether hypothesis cards deserve a top-of-page "proposed experiments" section separate from the
   per-set appendix. Recommendation: keep them in the analysis set until the S10 design review.

---

## 14. References

- `tools/analysis/schema.md` — shared analysis-report conventions (headers, `null` semantics,
  cost/attempt terminology).
- `docs/research/S8_DISCOVERY_RESOLUTION_2026-11-13.md` — decisions on geometry/behaviour
  separation, hypothesis/ablation policy, frozen HV reference, S7 capability limits, research
  sources.
- `docs/research/COUNCIL_REVIEW_AND_IMPL_PLAN_2026-11-12.md` — S8 row (`:233`) and S10 row (`:235`:
  "trade-off/novelty maps, hypothesis cards", "add S3/S4/S6/S8 panels incrementally").
- `docs/HANDOFF_ANALYSIS_PAGE_2026-11-12.md` — the E.1 visual-report work order and its definition
  of done; the same visual grammar applies here.
- `docs/CODE_MAP.md:3-7` — where the four tools are mapped today.
- pyribs CMA-MAE recipe: <https://docs.pyribs.org/en/stable/tutorials/cma_mae.html>
- Hypervolume reference-point research:
  <https://ci-labo-omu.github.io/assets/paper/pdf_file/multiobjective/ecj_gecco2017_hv.pdf>
- Keele horn-mouth research:
  <https://aes.org/publications/elibrary/elibrary-page/?id=1693>
