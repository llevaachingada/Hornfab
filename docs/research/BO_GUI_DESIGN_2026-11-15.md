# BO GUI design and implementation plan (2026-11-15)

**For:** owner review. **From:** the GUI/BO integration session.
**Input:** `docs/research/BO_GUI_HANDOFF_2026-11-15.md`, the Bayesian spec (§3, §5),
`docs/BAYESIAN_STUDIES_RUNBOOK.md`, `docs/queue/BO_VS_CMA_PLAN_2026-11-15.md`,
`docs/queue/BO_EXT_PLAN_2026-11-16.md`, and a read-only inspection of the real pilot and
`bo_vs_cma_2026-11-15` artifacts.

**Status:** design accepted for implementation in slices. This document is the deliverable the
handoff asks for; the slice log at the end records what was built.

---

## 0. Executive summary

Build a **read-only BO analysis layer** over the study workspace, computed in Python and rendered
as small SVG/HTML panels in the existing vanilla GUI. The study page gains:

- **Execute:** convergence (best-so-far vs solve, BO arms over matched CMA arms), budget/ETA,
  trust-region state for TuRBO, Pareto frontier for Pareto;
- **Explain:** predicted-vs-measured calibration, GP knob sensitivity, design-space map;
- **Decide:** Pareto drill-down, screen-vs-verify, hi-fi links, decision recording;
- **Data:** source runs, exclusions, objective version, training rows.

A new **`#/analysis/compare-methods`** board renders the pre-declared comparison rules from a
declarative spec, so the rules cannot drift.

Three decisions shape the work:

1. **The browser never computes or ranks a score.** It receives bounded JSON from
   `gui/data_bo.py`; every number is read from a study artifact, a run `search.ndjson`, or is a
   declared transformation (best-so-far, coverage %, rank correlation, hypervolume) computed in
   Python. Predictions stay labelled **model credible interval**; they never become measured J.
2. **Heavy or BoTorch work stays in the Bayesian subprocess.** The server process never imports
   torch/botorch. The only new compute is numpy over bounded artifact arrays (PCA, statistics).
   Partial-dependence curves, hi-fi rescoring and scalar-arm Pareto metrics are CPU jobs that
   write artifacts, not live requests.
3. **The GUI must see the studies the nights actually create.** The night prep tool writes a
   study root per arm (`runs/bo_vs_cma_2026-11-15/bo_s31001/`), not the GUI's default
   `runs/studies`. Add a bounded **study-root index** (explicit `--study-root` plus discovery of
   `runs/**/studies.sqlite3`), with every read/action routed to the owning root. Without this
   the most important studies are invisible to the GUI.

The work is developed in the worktree `C:\Users\hunte\Hrns\bogui-wt` on `feat/bo-gui`, based on
`feat/bo-turbo-pareto` (`e25da03`) plus the 2026-11-15 handoff docs. **It must not merge while
`bo_vs_cma_2026-11-15` or `sab_home_gpu_rest_2026-11-15` is queued or running** (handoff §0.1;
`docs/queue/BO_EXT_PLAN_2026-11-16.md` L4-5).

---

## 1. Ground truth: what the study data actually contains

Inspected read-only: pilot `scratch/2026-11-14_bayes/pilot/`, arm
`runs/bo_vs_cma_2026-11-15/bo_s31001/`, runs `runs/study-72834b64942a29f1/` and
`runs/study-f269f257b24e00f2/`.

### 1.1 Layout

```
<study-root>/
  studies.sqlite3                 studies, revisions, artifacts, attempts, observations,
                                  packages, proposal_state, launches, decisions
  artifacts/<sha256>              content-addressed JSON/NPZ
  package.json                    copy of the immutable run package
  workers/<job>/worker.log
<runs-root>/study-<package16>/{screen,verify}/
  search.ndjson                   ordinary run rows (design_hash, objective, terms, metrics)
  designs/<hash>/{metrics.json,response.npz,mesh.msh}
```

`<package16>` is the first 16 hex of the package hash. Real example: package
`f269f257b24e00f2…` → run id `study-f269f257b24e00f2`.

### 1.2 Artifacts that matter

| Artifact | Real fields used by the GUI | Notes |
|---|---|---|
| `snapshot` | task config/brief paths + hashes, objective version | identity, never a score |
| `training_manifest` | `active_keys`, `d`, `n`, `n_min`, `ids`, `selected_ids`, `excluded_ids`, `subset_policy`, `task.objective_version`, `meta.cohort_policy` | training rows/exclusions; `active_keys` are the knob names |
| `training` | NPZ `X`, `J`, `Y`, `Y_phys` | bounded 2-D projection only |
| `analysis` | `heldout_support`, `metric_score_identity`, `subset` | model diagnostics, not a recommendation |
| `model` | `status`, `policy`, `library_versions`, `counts`, `limitations` | **currently no hyperparameters** — see §6 |
| `proposal` | `candidate`, `predicted` (`j_mean`, `j_lower`, `j_upper`, `interval_label`), `acquisition`, `selection_reason`, `trust_region` (turbo), `pareto` (binding) | initial proposal only |
| `pool` | candidate sample + status note | design-space context |
| `package` | `package_id`, `budget`, `budget_profile`, `lane`, `deadline`, `verification_policy`, `code_pins` | run identity and budget |
| `results` | `observations[] = {candidate, result}`; result has `kind`, `outcome`, `eligible`, `observed_j`, `normalized_terms`, `pareto_metric`, `objectives`, `canonical_replay`, `seconds` | **the best source for BO convergence, calibration and trust-region history** |
| `verification` | `selection.finalists`, `selection.audits`, `verified_geometry_ids` | decide phase |
| `pareto_metrics` | `metric_policy`, `reference` (`limits`, `ref_point`), `observations` (`coverage_deg`, `ripple_db`), `excluded`, `n_complete` | only on the turbo/Pareto branch |

### 1.3 What is missing today (and therefore what §6 instruments)

- **Per-proposal predictions are not persisted.** `results.observations[*].candidate.predicted`
  is `null` for all 66 attempts of the real arm; only the initial `proposal` artifact carries a
  prediction. The evaluator normalises `predicted` but the policy outcome keeps it outside the
  candidate dict (`evaluator.py:_normalise` L184-221; `_propose_through_policy` L223-245).
- **Model hyperparameters are not persisted.** `model` says
  `"model_state_persisted": false` and lists only `library_versions` and counts
  (`builders.py` L1086-1117). `fit_model` does produce `hyperparameters.lengthscales`
  (`bo/model.py` L416-425), but it is dropped before the artifact.
- **Trust-region history is only in the initial proposal artifact.** The live evaluator adopts
  `outcome.trust_region` (`evaluator.py` L241-245, L494-499), but the per-attempt candidate does
  not carry the record, so the GUI cannot plot L over time.
- **Study roots are not discovered.** `App._studies()` uses `runs/studies` only
  (`server.py` L48-52); the night arms live elsewhere.

These are small, additive backend changes. They change the study code pin (§0 of the handoff), so
they ship on the same post-night merge as the GUI.

---

## 2. Constraints and non-goals

**Must hold**

- No GUI click starts a solve. No GPU work from the GUI agent. No torch/botorch import in the
  server process.
- Every displayed number comes from a backend artifact or a named derived statistic; no score
  math and no ranking in JavaScript.
- Predictions are "model credible interval", never measured J; screen and verify stay separate.
- Never rank J across objective versions. If a comparison mixes versions, the view returns
  `partial` with `versions_mixed: true` and refuses a shared J axis.
- Study code pinning: merge only with no running/queued study; update
  `docs/CONTINUITY.md`, `docs/ISSUES.md`, `docs/INDEX.md`, `docs/CODE_MAP.md` in the same commit.
- The frontend stays dependency-free: no charting library, no framework. Reuse
  `static/charts.js` primitives through a small `study_charts.js` module.
- Light/dark and phone width are acceptance criteria, not polish.

**Not in this pass**

- Partial-dependence curves (needs a new Bayesian-subprocess job and artifact) — designed but
  optional slice 7.
- Per-study dataset row identity (`screen`/`verify` ambiguity) — proposed separately; needs a
  dataset metadata change and owner sign-off.
- Scalar-arm Pareto metric recomputation (needs a CPU job over stored records) — the board shows
  the missing state and the exact job to run.
- Multi-region TuRBO, constraint GPs, cost-aware ranking (out of scope in the BO_EXT plan §4).

---

## 3. UX design

### 3.1 Navigation

- The existing study phase tabs stay: **Overview | Data | Explain | Propose | Run & Verify |
  Decide**. No new phase is required; BO panels appear where the handoff maps them.
- The Analysis page gains one entry: **Compare methods** (new `#/analysis/compare-methods`).
- The study list shows a small root badge (`runs/bo_vs_cma_2026-11-15/bo_s31001`), the policy
  (`scalar` / `turbo` / `pareto`), and the budget profile (`baseline` / `comparison-60`).

### 3.2 Execute phase — "is it working?"

Order, top to bottom:

1. **Status strip**: package hash, revision, lane, deadline, budget profile, progress, ETA.
   ETA = measured median seconds per solve × remaining budget, labelled "estimate from recorded
   solve times"; verify ETA is shown separately (~7.5× a screen).
2. **Convergence**: one chart, best-so-far J vs solve index. BO arm solid; matched CMA arms
   dashed; refusals as muted ticks; exploration picks ringed; incumbent horizontal line; a linear
   / log-y toggle. Screen J is reported but labelled "does not decide".
3. **Trust region** (turbo only): L over proposal index with L_min/L_max guides; success/failure
   counters; latest box extents per knob as 0–1 bars; status chip **converged (box collapsed)**
   in green, not an error. Unspent budget shown when it collapses early.
4. **Pareto frontier** (pareto only): coverage error (deg) × ripple (dB); measured points grey,
   nondominated highlighted, frozen reference box, hypervolume, finalists ringed, J beside each
   point. Click a point → drill-down. Notes state the v7 plain-coverage decision, the
   frontier/crowding training subset, and that rows beyond the reference still train but add no
   hypervolume.
5. **Run links**: open the screen run, the verify run, and the balloon/3D views. Links are built
   only from ids the backend produced.

### 3.3 Explain phase — "can I trust the model?"

1. **Predicted vs measured J** with 95% model intervals. y = x line; points labelled "model
   credible interval"; calibration coverage % and Spearman rank correlation in a caption. If
   fewer than 3 predictions were persisted, show `partial` and the reason (old runs) rather than
   inventing points.
2. **Knob sensitivity** from the GP lengthscales: horizontal bars, longest bar = strongest effect;
   label "relative knob sensitivity (1/lengthscale, normalized)". Knob names come from
   `training_manifest.active_keys` / the parameter catalog, never invented.
3. **Design-space map**: 2-D PCA of training X (grey, J colour) + proposals (rings) + Pareto
   points (accent). Axis captions include variance explained. If fewer than 3 rows, show
   missing.
4. **Model notes**: policy, engine/library versions, fit status, counts, `limitations`.

### 3.4 Data phase

Source runs with row counts and exclusions, objective version, training subset policy, and the
design-space map. This answers W1 ("which runs feed it and which are excluded") without a table
of 185 ids.

### 3.5 Decide phase

Pareto drill-down + screen-vs-verify table (reuse `verify.js` patterns: `deltaCellHtml`,
summaries) + hi-fi numbers when a cached artifact exists + the existing decision form. The
decision remains a registry event, not a new artifact.

### 3.6 Compare methods board

A single page with a spec selector. For each arm: method, seed, policy, budget profile, best
verify J, seed spread, screens-to-target, verify coverage, and a status chip. The verdict card
applies the pre-declared rule and shows the raw numbers underneath. If an arm is incomplete, the
verdict is **incomplete**, with the exact missing jobs — never a guess.

### 3.7 Visual language and accessibility

- Use `charts.js` (`chart`, `catColor`, `sparkline`) and theme tokens; no hard-coded hex.
- Every chart has `role="img"` + a one-sentence `aria-label`, plus a text/table fallback with the
  same numbers. Colour is never the only encoding (line style + labels).
- Charts are responsive: `svg { width: 100%; height: auto; }`; the study layout collapses to one
  column below 900 px. Tables scroll horizontally rather than clipping.
- Empty states are explicit and actionable ("no run results yet", "engine missing", "old study:
  predictions were not persisted").

---

## 4. Architecture

### 4.1 Data flow

```
studies.sqlite3 + artifacts/*  ──► StudyService (per root)
runs/study-*/{screen,verify}/* ──► run readers (bounded)
                         │
                         ▼
             gui/data_bo.py  (pure Python, numpy only)
                         │  bounded JSON
                         ▼
             workflow_panel() ──► GET /api/studies/<id>/<phase>
                         │
                         ▼
             studies.js render placeholders + tables
                         │
                         ▼
             study_charts.js draws SVG with charts.js
```

### 4.2 New/changed modules

| Path | Change |
|---|---|
| `hornlab_search/gui/data_bo.py` | **new**: view models (convergence, calibration, sensitivity, trust region, Pareto, design space, method board). Pure functions; no service writes. |
| `hornlab_search/gui/study_index.py` | **new**: bounded root discovery + service routing; returns root ids/labels. |
| `hornlab_search/gui/data_studies.py` | `workflow_panel` accepts `runs_root` and attaches `data["bo"]`; policy cards no longer hard-code scalar-only when the backend reports more. |
| `hornlab_search/gui/server.py` | routes for multi-root study access, `/api/comparisons`, `root` query/body handling; passes `runs_root` to `workflow_panel`. |
| `hornlab_search/gui/static/studies.js` | renders BO panels/placeholders/tables; passes `root` through the API adapter; deep-link helper. |
| `hornlab_search/gui/static/study_charts.js` | **new**: imports `charts.js`; draws convergence, calibration, sensitivity, Pareto, trust-region L, design space. Attaches point drill-down. |
| `hornlab_search/gui/static/app.js` | imports `study_charts.js`; study route query (`root`); compare-methods route; balloon `design` query. |
| `hornlab_search/gui/static/app.css` | study chart/layout/panel styles, responsive rules, focus states. |
| `hornlab_search/gui/static/balloon.js` | optional `preselected` design from `?design=<hash>`. |
| `hornlab_search/studies/evaluator.py` | persist `predicted` + `trust_region` on the candidate. |
| `hornlab_search/bo/policy.py` | `ProposalOutcome.model_hyperparameters` (additive). |
| `hornlab_search/studies/builders.py` | write `hyperparameters` to the model manifest. |
| `tools/analysis/specs/bo_method_board_2026-11-15.yaml` | **new**: declarative comparison spec. |
| `tests/test_gui_bo_views.py` | **new**: view-model tests with synthetic artifacts. |
| `tests/test_gui_bo_module.py` | **new**: Node test for `study_charts.js` pure helpers. |
| `tests/test_gui_study_index.py` | **new**: multi-root list/read/action routing. |
| `docs/research/BO_GUI_DESIGN_2026-11-15.md` | this document. |

### 4.3 Study-root index

- Roots = explicit `--study-root` values + `HORNLAB_STUDY_ROOTS` + `runs/studies` + discovery of
  `runs/**/studies.sqlite3` (depth ≤ 4, cached ~10 s). Each root gets a stable id
  `sha256(relative_path)[:8]` and a display label.
- `GET /api/studies` returns `{"studies":[{...,"root":root_id,"root_label":...}], "roots":[...]}`.
- `GET /api/studies/<id>` and `<phase>` accept `?root=<root_id>`. If omitted, a unique id is
  resolved; a duplicate returns 409 with "ambiguous study id; pass root".
- POSTs accept a `root` field, which the server pops before any strict job-payload validation.
- Discovery is read-only and bounded; it never opens a database for writing.
- The primary/create root remains `runs/studies`.

### 4.4 View-model contract

Every sub-view is a dict:

```
{
  "status": "ready" | "partial" | "missing" | "unavailable" | "not_applicable",
  "reason": "human sentence" (required unless ready),
  "source": "artifact:results + run:screen",
  "notes": ["..."],            # limitations and contract notes
  ... bounded data ...
}
```

`data["bo"]` is always present on the phase panel, even when every sub-view is missing, so the
frontend can show honest empty states. A view-builder exception is caught and becomes
`{"status":"failed","reason":"..."}`; it never breaks the study panel.

**Hard bounds:** ≤ 200 points per series (best-so-far downsampled to ≤ 120 while keeping the last
point and every improvement), ≤ 60 Pareto points, ≤ 50 rows per table, strings ≤ 500 chars,
total `data["bo"]` ≤ 96 KB after `bounded_preview`. Raw artifact bytes are not exposed.

**Declared derived statistics** (computed in Python, source named in the view):

| Statistic | Definition | Why it is allowed |
|---|---|---|
| best-so-far | running min of recorded `observed_j` per solve | transformation of measured J |
| screens-to-target | first screen index with J ≤ declared target | transformation of measured J |
| calibration coverage | fraction of measured J inside the recorded model interval | join of two recorded values |
| Spearman rank correlation | ranks of predicted vs measured | statistic, not a score |
| hypervolume | 2-D sweep in the frozen reference box | metric over recorded pairs |
| PCA coordinates | SVD of training X | projection, not a score |

---

## 5. View specifications

### 5.1 `convergence_view(service, study, *, runs_root, comparison=None)`

Inputs: `results` artifact (BO arm), `runs_root/<run_id>/screen/search.ndjson` (CMA arms),
optional comparison spec. Output:

```
status, objective_version, arms:[{id,label,method,policy,color_slot,
  points:[[i,best_j]], solves:[[i,j,kind,outcome]], refusals:[[i]], exploration:[[i]],
  screens, verify, budget_profile, best_verify_j, screens_to_target}],
incumbent:{j,label}|null, versions_mixed, notes
```

- BO arm points come from `results.observations` in attempt order; only `kind=="screen"` updates
  best-so-far; verify/audit are drawn as separate marks.
- CMA arms come from `search.ndjson` rows with `ok`; row order is solve order.
- If only the BO arm exists, status is `partial` with "matched arms not recorded yet".
- Do not mix objective versions; if they differ, omit the shared axis and say why.

### 5.2 `calibration_view(service, study)`

Join `candidate.predicted` to `result.observed_j` by `solve_id` (screen only). Output points
`{solve_id, predicted:{mean,lower,upper}, measured, inside}`; coverage, Spearman, n. Fallback:
the initial `proposal.predicted` matched by `candidate_id`/`design_hash` to the first screen row,
n=1 → `partial`. Pareto physical predictions are returned separately as
`{coverage_deg:{mean,lower,upper}, ripple_db:{...}}` and are not plotted on the J chart.

### 5.3 `sensitivity_view(service, study)`

Read `model.hyperparameters.lengthscales` (new) and `training_manifest.active_keys`. Output
`{status, policy, knobs:[{key,lengthscale,importance}], lengthscale_bounds, engine, reason}`.
If absent: `missing` with "model hyperparameters were not recorded for this proposal; the next
analyze/propose records them." No fallback to invented sensitivities.

### 5.4 `trust_region_view(service, study)`

Policy must be `turbo`. Walk `results.observations[*].candidate.trust_region` (new) and/or the
proposal artifact's `trust_region`. Output:

```
status, policy, length_series:[[i,L]], success:failure counters per step,
box:{lo:[...],hi:[...],weights:[...]} (latest),
terminal:{collapsed:bool,reason}, budget:{used,total}, notes
```

`collapsed` is rendered as **converged**, with the unspent budget; it is not an error.

### 5.5 `pareto_view(service, study, *, runs_root)`

Inputs: `pareto_metrics` artifact, `results.observations[*].result.objectives` /
`pareto_metric`, frozen reference. Output:

```
status, reference:{limits,ref_point,units,direction}, points:[{design_hash,coverage_deg,
ripple_db,j,measured,nondominated,finalist}], hypervolume, n_complete, n_excluded,
predicted:[{coverage_deg,ripple_db}] (if persisted), notes:[v7 plain coverage, subset policy,
beyond-reference rows]
```

Nondominance and hypervolume are computed in Python over recorded pairs. The page never
recomputes acoustic metrics.

### 5.6 `design_space_view(service, study)`

Read `training` NPZ (bounded) + results candidate `x` vectors. 2-D PCA (SVD), return
`points:[{x,y,j,source:"training"|"screen"|"pareto"|"proposal",design_hash}]`, `explained`.
No UMAP dependency in the server; PCA is deterministic and fast for ≤ 256 rows.

### 5.7 `method_board_view(spec, *, runs_root)`

Spec shape (YAML):

```yaml
name: bo-vs-cma-2026-11-15
runs_root: runs
objective_version: 7
incumbent: {j: 3.2325, label: "prior CMA best"}
target_j: 3.2325
decision:
  verify_median_gap_must_exceed_spread: true
  screens_to_target_target: 3.2325
arms:
  - {id: bo_s31001, method: bo, policy: scalar, study_root: runs/bo_vs_cma_2026-11-15/bo_s31001, budget_profile: comparison-60}
  - {id: cma_s3101, method: cma, run: 20261115T052416Z-screen-cdbc27, budget_profile: 60}
```

Arm resolution order: explicit `run`/`verify`; else `summary.jsonl` by job id; else the study
root's package hash → `study-<pkg16>`. The board reads only recorded rows; missing arms make the
verdict `incomplete`.

Verdict logic:

- best verify J per arm from `<run>/verify/search.ndjson` (`ok` rows), else BO results kind
  `verify`; audits reported separately;
- median per method, seed spread = max − min within a method;
- BoTorch/TuRBO wins only if `median_a < median_b` and `gap > max(spread_a, spread_b)`;
- screens-to-target = first screen row with J ≤ `target_j`, else `> budget`;
- Pareto arm: hypervolume of measured nondominated points in the frozen reference box, plus
  frontier table (coverage, ripple, J, design hash, links).

### 5.8 Deep links

- Run: `#/run/<run_id>` and `#/run/<run_id>/verify`.
- Design: `#/run/<run_id>/balloon?design=<design_hash>` (add `?design` support to the balloon
  view; it already has a design selector). From there the user can open 3D/verify.
- Study return context: append `study=<id>&root=<root>` to the existing `return` query; the
  existing `study-return-context` link in `app.js` is extended to accept `root`.

---

## 6. Backend instrumentation (pin-affecting, merge with the GUI)

These are tiny and additive; they do not change any score or selection rule. They exist so the
GUI can show what the model actually said.

1. **Persist per-proposal predictions.**
   `studies/evaluator.py::_propose_through_policy` currently returns `outcome.proposal` and drops
   `outcome.predicted`. Return a copy with `predicted=outcome.predicted`,
   `trust_region=outcome.trust_region` (turbo), `selection_reason`, `acquisition`.
   `_normalise` already copies `predicted`; add `trust_region`.
2. **Persist model hyperparameters.**
   Add `model_hyperparameters: dict | None` to `bo/policy.py::ProposalOutcome`; set it from
   `fitted.hyperparameters` on scalar/turbo success (Pareto: one entry per output). Write
   `"hyperparameters": outcome.model_hyperparameters` and
   `"model_state_persisted": bool(...)` in `studies/builders.py`'s model manifest.
3. **Persist trust-region records per attempt.**
   Covered by (1). The initial proposal artifact already carries the record; the sequence now
   follows the run.

No change to `EXECUTION_CODE_FILES` is made in this pass. The GUI remains pinned, so the merge
gate is a hard "no running/queued study". The separate proposal to exclude `hornlab_search/gui/**`
from the pin remains an owner decision (handoff §0.1).

---

## 7. Slices, acceptance and tests

Each slice is a working state; no slice relaxes an existing test.

### Slice 1 — view models + multi-root index (read-only)

- `gui/data_bo.py`, `gui/study_index.py`, `workflow_panel` wiring, `/api/studies?root=`,
  `/api/comparisons` + spec file.
- Tests: synthetic study with results/proposal/model/pareto artifacts; assert shapes, bounds,
  missing states, version mixing, derived statistics, and that no score is recomputed.
- Acceptance: `pytest tests/test_gui_bo_views.py tests/test_gui_study_index.py -q` green;
  a read-only pass over the real `bo_s31001` study returns `partial`/`ready` views without
  touching the DB.

### Slice 2 — study charts + deep links

- `study_charts.js`, `studies.js` placeholders/tables, CSS, balloon `?design`.
- Tests: Node pure-render test + Python HTML test; screenshots at desktop/phone, light/dark.
- Acceptance: execute/explain render from the real pilot; no JS score math (grep for arithmetic
  on J is limited to formatting/axis mapping); deep links open the selected design.

### Slice 3 — policy cards + turbo/strategy copy

- `POLICY_MODES` includes `turbo`; `policy_cards` renders all backend cards; strategy copy from
  handoff §4 with "use when" and "what success looks like"; turbo enabled only when the backend
  says `ready` and the spec policy is turbo-compatible.
- Tests: policy card status/serialization; no client inference of readiness.

### Slice 4 — Pareto page

- `pareto_view` + UI in execute/decide; frontier table + drill-down; v7 notes.
- Tests: nondominance/hypervolume on a hand-built 2-D set; reference box; missing artifact.

### Slice 5 — trust-region panel

- `trust_region_view` + UI; L series, counters, box bars, converged state.
- Tests: synthetic turbo records (grow/shrink/collapse); non-turbo returns `not_applicable`.

### Slice 6 — queue integration + child studies

- "Queue for tonight" writes a **new** night file (never edits the running one) with a
  `studies.cli run` job for the prepared package, and either launches `queue.ps1` with
  `-WaitPid` on a live runner or presents the exact command for the owner to launch. The default
  is the safe path: write + show, because the GUI server must not start a second GPU runner.
- Child-study chaining reuses the existing `create_child` action.
- Tests: night-file content, no edit to a running night, refusal without a package/study root.

### Slice 7 — optional

- Partial-dependence job (Bayesian subprocess) + cached artifact; per-study dataset identity.
- Not required for the first owner review; designed here so it does not block slices 1-6.

**Evidence for every slice:** offline pytest output, a Node test for JS, and a screenshot at
desktop + phone width in light and dark. No GPU/study run is started by this work.

---

## 8. Test and evidence plan

- **Unit/view models:** `tests/test_gui_bo_views.py` builds a `StudyService(tmp_path)` with
  synthetic `snapshot`, `training_manifest`, `model`, `proposal`, `results`, `pareto_metrics`;
  writes a synthetic run dir; asserts every view's status/shape/bounds and the "never invent"
  cases.
- **Server/API:** extend `tests/test_gui_studies_api.py` style in-process `App` tests for
  `root` routing and `/api/comparisons`.
- **JS:** `tests/test_gui_studies_module.py` style Node import for pure helpers; a new
  `tests/test_gui_bo_module.py` imports `study_charts.js` via `pathToFileURL` (it may import
  `charts.js` relatively).
- **Real-data read-only smoke:** run the view builders against `runs/bo_vs_cma_2026-11-15/bo_s31001`
  and the pilot in a script; assert no exception, bounded JSON, and that the missing
  instrumentation states are explicit. This does not solve or write.
- **Compile:** `python -m compileall hornlab_search/gui hornlab_search/studies hornlab_search/bo`.
- **Merge gate:** `tools/night_status.py` shows no runner/julia; `tools/night_status.py` +
  `runs/nights/queue_*.log` confirm both nights finished; then update docs and merge.

---

## 9. Risks, decisions and open questions

| Risk / decision | Handling |
|---|---|
| GUI code pin changes preflight | This is the main merge risk. Work only in `bogui-wt`; merge only when no study is queued/running. The GUI-exclusion proposal stays separate and needs owner sign-off. |
| Old studies lack predictions/hyperparameters | Views return `partial`/`missing` with the exact reason. The new instrumentation makes subsequent runs complete. |
| Multi-root discovery could be slow or unsafe | Depth-bounded, cached, read-only, only under `runs` by default; explicit `--study-root` for scratch. Actions still restricted to registered roots. |
| Derived statistics could be mistaken for scores | Every derived stat names its inputs; the UI says "derived from recorded rows"; no ranking of designs by a new metric. |
| Pareto comparison against scalar arms needs metrics | The board shows the missing state and the CPU job needed; it does not fabricate coverage/ripple from J. |
| Objective versions mixed in a board | `versions_mixed` → `partial`, no shared J axis, explicit banner. |
| Queue integration could start a second GPU runner | Default "write night file + show command"; any launch path must pass `-WaitPid` and the night-queue rules. |
| Night currently running | No GUI test starts a solver; all work is in the worktree; no merge until both nights finish. |

**Open questions for the owner (non-blocking for slices 1-5):**

1. Queue action: should the GUI ever launch `queue.ps1` itself, or always write the night file
   and hand the command to the owner? (Default in this design: write + show.)
2. Exclude `hornlab_search/gui/**` from `EXECUTION_CODE_FILES`? (Recommended later, but it changes
   the pin contract and needs sign-off.)
3. Partial-dependence curves: do you want them in the first review, or is the GP lengthscale
   sensitivity bar enough? (Default: lengthscale bar now; P-D job optional.)

---

## 10. Slice log (filled as the work lands)

| Date | Slice | Result | Evidence |
|---|---|---|---|
| 2026-11-15 | design | this document | handoff + read-only artifact inspection |
| 2026-11-15 | 1 — view models + root index | `data_bo.py`, `study_index.py`, `workflow_panel`/server wiring, `/api/comparisons` | `test_gui_bo_views.py`, `test_gui_study_index.py` |
| 2026-11-15 | 2 — charts + deep links | `study_charts.js`, study panels, CSS, balloon `?design` | `test_gui_bo_module.py`, screenshot set |
| 2026-11-15 | 3 — policy cards + turbo copy | turbo card, strategy copy, backend capability statuses | `test_gui_study_adapters.py`, `test_gui_studies_module.py` |
| 2026-11-15 | 4 — Pareto | `pareto_view`, frontier table/drill-down, reference/hypervolume notes | `test_gui_bo_views.py` |
| 2026-11-15 | 5 — trust region | `trust_region_view`, L series, box bars, converged state | `test_gui_bo_views.py` |
| 2026-11-15 | 6 — queue + child | `study_queue.py` (writes, never launches), `study_child.py`, UI actions | `test_gui_study_queue.py` |
| — | 7 — optional | partial-dependence job and per-study dataset identity: designed, not built | this document §7/§9 |
