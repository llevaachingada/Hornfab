# BoTorch in the GUI: implementation plan (orchestrator-ready)

> **Scope note (2026-11-15, later):** most WPs below already exist on `feat/bo-gui` (see
> `BO_GUI_DESIGN_2026-11-15.md` §10). The remaining work is `BO_GUI_CLOUD_HANDOFF_2026-11-16.md`.
> Keep this file for the diagnostics artifact spec (§1.1) and the BoTorch API notes (§0).

**Written:** 2026-11-15 (senior review of `BO_GUI_HANDOFF_2026-11-16.md`).
**Audience:** an orchestrator agent that dispatches parallel implementation agents. Each work
package (WP) below is self-contained: files it owns, what it builds, its contract, and its single
acceptance check. Read the handoff for the data model (§2) and gotchas (§6). This plan does not repeat them.
It **decides** the handoff's open questions (§8) so nobody has to stop and ask.

---

## 0. Senior review: what changes from the handoff

1. **Slice 0 is right and it is the whole "I can't see it" bug.** Keep it first and keep it small.
2. **GP hyperparameters are already computed. They are just thrown away.** `bo/model.py:416`
   `_extract_hyperparameters()` returns `lengthscales`, `outputscale` and their bounds into
   `ModelFitResult.hyperparameters`, and `to_dict()` serialises them (`model.py:177`). Only
   `studies/builders.py:1185-1212` drops them from the model manifest. So "sensitivity" is not a
   research slice. It is a few lines plus a diagnostics artifact. It moves up from slice 9 to wave 1.
3. **BoTorch 0.18.1 (the version in `bayes-venv`) gives us calibration for free.** We checked the
   installed source; botorch.org's `/docs` and `/api` paths returned 404.
   - `botorch.cross_validation.efficient_loo_cv(model, observation_noise=True, untransform=True)`
     returns `CVResults` (LOO posterior mean/variance for every training row). It does not refit
     each fold; it uses the closed-form K⁻¹ identity, which is O(n³) once. With n≈60–300 and d≈9
     that takes milliseconds. It gives **model calibration before a single new solve**, which the
     handoff's proposal-vs-measured calibration (view 3) cannot do until many picks are measured. Show both.
   - `botorch.utils.multi_objective.pareto.is_non_dominated(Y, maximize=True)` and
     `botorch.utils.multi_objective.hypervolume.Hypervolume(ref_point).compute(Y)` give the frontier
     mask and the hypervolume trace. Use them **inside the Bayes subprocess** so the frontier and HV
     the GUI shows are the same code the Pareto policy uses (`bo/pareto.py`). This avoids a second
     implementation in the server.
   - `model.posterior(X)` on a grid gives **1-D posterior slices through the incumbent**: for each
     active knob, the mean ±2σ of predicted J. This is the most intuitive "what the model believes
     each knob does" view, and it costs d×25 posterior calls.
   - Ax (`ax.analysis`, Sobol sensitivity) is **not installed** and depends on Ax's `Experiment`
     object. Do not add it. Lengthscale relevance + slices + LOO cover the same ground with zero
     new dependencies.
4. **All torch-side numbers come from a single new artifact, `study-model-diagnostics-v1`**, made by
   the Bayes subprocess. The GUI server stays torch-free (gotcha 2) and only reads JSON.
   For the 15 studies already on disk, a **CPU job refits from the stored training dataset** and
   attaches the artifact. No re-solves and no GPU are needed.
5. **UX: a running study needs a dashboard, not six phases.** The phase stepper suits *authoring*
   a study. Someone watching a night run wants one screen. Add a **Live** tab that the study opens
   on when a package exists. It shows a KPI strip, convergence, the current pick and budget/ETA. The six phases
   stay for drilling in.
6. **Code-pin gotcha drives scheduling.** Every `hornlab_search/**/*.py` edit changes `code_pins`.
   The running pilot is already pinned and unaffected. **Do not prepare any new arm package until
   this whole plan is merged**, then re-prepare. Tell the owner this in the final report.

### Owner questions (§8 of the handoff): decided
| # | Decision | Why |
|---|---|---|
| 1 Nav | Top-level **Bayes** group; `#/analysis/studies*` redirects | It is a different workflow from CMA runs |
| 2 Store | **Discovery** over per-arm roots; no migration | Needed for the 15 roots anyway; arm isolation is a feature |
| 3 Hyperparameters | **Persist** as additive optional fields + diagnostics artifact | Zero cost, already computed |
| 4 Launch | **Queue only** (night queue + admission). No direct launch button | One GPU runner, lane locks. The existing direct path is hidden behind `?dev=1` |
| 5 Method board | Show raw numbers **plus** pre-declared rule verdicts labelled *advisory* | Owner judges; the rules are visible, not authoritative |

---

## 1. Architecture

```
runs/**/studies.sqlite3  ──►  gui/study_roots.py  (StudyRegistry: id → root, StudyService; mtime cache)
                                   │
gui/server.py  /api/studies*  ─────┤   every route resolves the service by study id
               /api/bayes/*   ─────┤
                                   ▼
gui/data_bayes.py   pure readers → bounded JSON view-models (no torch, no J recomputation)
     ├ list_rows()        study list rows across roots
     ├ live_view()        KPI strip + convergence + budget/ETA + refusals + current pick
     ├ calibration_view() LOO (diagnostics artifact) + proposal-vs-measured (attempts join)
     ├ sensitivity_view() lengthscale relevance + 1-D slices (diagnostics artifact)
     ├ trust_region_view()  from proposal.trust_region across revisions
     ├ pareto_view()        from pareto-metrics + diagnostics frontier/HV trace
     └ method_board()       night summaries + comparison spec
                                   ▲
Bayes subprocess (bayes-venv, torch) ── studies/cli.py `diagnose` ── bo/diagnostics.py
     writes artifact kind "diagnostics" (schema study-model-diagnostics-v1)
     also emitted automatically by builders.build_proposal for new proposals

static/bayes/   (new ES modules, no new library; draw with charts.js `chart`, `sparkline`, `heat`, `el`)
     bayes_list.js   bayes_study.js (Live tab + phase shell)   bayes_views.js (all charts)
     bayes_board.js  (method board)
```

### 1.1 New artifact `study-model-diagnostics-v1` (kind `diagnostics`)
Made by `bo/diagnostics.py::build_diagnostics(fit: ModelFitResult, training_set, policy, pareto=None)`.
All values are on the **J scale shown to the user** (predicted J = −posterior mean, as `model.py:21`).
```jsonc
{
  "schema": "study-model-diagnostics-v1", "study_id": "...", "revision": 7,
  "training_set_id": "...", "policy": "scalar|turbo|pareto", "generated_utc": "...",
  "library_versions": {...}, "status": "ok|unavailable", "reason": "...",
  "hyperparameters": { "active_keys": [...], "lengthscales": [...], "outputscale": 1.2,
                       "noise": 0.01, "lengthscale_bounds": [0.005, 4] },
  "relevance": [ {"key": "throat_angle", "inv_lengthscale": 3.1, "rank": 1, "at_bound": false} ],
  "loo": { "method": "efficient_loo_cv (no refit)", "n": 231,
           "rows": [ {"id": "...", "j_obs": 3.4, "j_mean": 3.5, "j_sd": 0.2} ],     // cap 400
           "summary": {"rmse": .., "spearman": .., "coverage_95": .., "mean_z": .., "sd_z": ..} },
  "slices": { "anchor": "incumbent", "anchor_id": "...", "grid_n": 25,
              "per_key": { "throat_angle": {"x": [...], "j_mean": [...], "j_sd": [...],
                                             "anchor_x": .., "unit": "deg"} } },
  "pareto": null | { "objectives": ["coverage_err_deg","ripple_db"], "ref_point": [..],
                     "front_ids": [...], "hv_trace": [ {"seq": 1, "hv": 0.0} ] }   // pareto only
}
```
Rules: per-model only. For a Pareto `ModelListGP`, report hyperparameters/LOO **per objective**
(`"per_objective": {"coverage": {...}, "ripple": {...}}`). Slices are computed on the normalised
inputs and reported in raw units via the existing encoding. The artifact is capped at 128 KB, and
the LOO rows are truncated with a `"truncated": true` flag.

### 1.2 API additions (all GET, all bounded, all read-only)
| route | returns |
|---|---|
| `GET /api/studies` | merged list: `{studies:[row...], roots:{found:N, with_studies:M, skipped:[{root,reason}]}}` |
| `GET /api/bayes/study/<id>/live` | `live_view` |
| `GET /api/bayes/study/<id>/calibration` | `calibration_view` |
| `GET /api/bayes/study/<id>/sensitivity` | `sensitivity_view` (`available:false, can_compute:true` when no diagnostics yet) |
| `GET /api/bayes/study/<id>/trust_region` | `trust_region_view` (`applicable:false` for non-turbo) |
| `GET /api/bayes/study/<id>/pareto` | `pareto_view` (`applicable:false` for non-pareto) |
| `GET /api/bayes/board?spec=<name>` | `method_board` |
| `POST /api/studies/<id>/jobs` `{kind:"diagnose"}` | existing CPU-job mechanism, new kind |

The list row shape is `{id, root, task, objective_version, policy, state, budget:{profile, screens_used,
screens_total, verify_used, verify_total}, best:{screen_j, verify_j}, last_event_utc, running:bool,
diagnostics:bool}`. `state` is one of `no_data|proposed|packaged|running|done|refused|stale|blocked_unknown`.

---

## 2. Work packages and waves

**File ownership is the parallelism rule.** In waves 1–2 an agent creates only **new** files,
except the one shared file it is explicitly given. `server.py`, `static/app.js`, `index.html` and
`app.css` are edited **only** by WP0 and WP7.

### Wave 0 (one agent, do first, ~small)
**WP0: Discovery, routing and contract fixtures.**
- New `gui/study_roots.py`: `StudyRegistry(runs)`. It scans `runs/**/studies.sqlite3` (skips `_smoke_*`,
  keeps `runs/studies`, which is the GUI store, but it may be empty), opens each with `StudyService`,
  and maps `study_id → (root, service)`. Cache keyed on the sqlite mtime set, rescanned at most every 10 s.
  Corrupt/locked DB → recorded in `skipped`, never fatal. Open read-only where `StudyService` allows.
- `server.py`: replace `_studies()` with `_service_for(study_id)` on every `/api/studies/<id>*`
  GET and POST. Creating a *new* study still goes to `runs/studies`. The CPU bridge (`_study_cpu_bridge`)
  becomes per-service: a dict keyed by root, each built by the existing `_create_study_cpu_bridge` body.
  `/api/studies` merges rows across roots with the row shape in §1.2 (a minimal version is fine; WP1 enriches it).
- Register empty stub routes `/api/bayes/*` that call `data_bayes.<fn>` (import errors → 501), so
  WP1/WP3 only fill in functions.
- Write `tests/fixtures/bayes_api/{list,live,calibration,sensitivity,trust_region,pareto,board}.json`:
  **hand-written example payloads** exactly matching §1.1/§1.2 shapes, built from real numbers
  you read from the fixture roots (handoff §7). These are the frontend contract.
- Test (one file, `tests/test_gui_study_roots.py`): two synthetic roots in `tmp_path` + one corrupt
  sqlite → list has both studies, `skipped` has one entry, unknown id → 404.
- **Acceptance:** with the live disk, `GET /api/studies` returns ≥15 studies including
  `4ce07cfdc30e408e9e088eb6ce228f64`, and `/api/studies/0519e65a…/overview` is 200.

### Wave 1 (four agents in parallel, after WP0 merges)
**WP1: Backend view-models** (`gui/data_bayes.py` new; tests `tests/test_gui_data_bayes.py` new).
Implements `list_rows`, `live_view`, `calibration_view` (proposal-vs-measured half), `trust_region_view`,
`pareto_view` (from `study-pareto-metrics-v1`; frontier mask from diagnostics when present, else a plain
2-D non-dominated sort labelled `source:"server"`), `sensitivity_view` (reads the diagnostics artifact).
Details:
- Convergence: one series per attempt kind, ordered by `observation_seq`. `observed_j`, best-so-far,
  refusals as `{seq, reason}` ticks, `exploration:true` where `selection_reason` says so. The training
  incumbent comes from the training-dataset artifact's best eligible row (a horizontal line).
- Budget/ETA: screens and verify are counted **separately**. Seconds per solve = median of
  (resolved − reserved) timestamps from `attempts` when present, else the run dir's `search.ndjson`
  line times. ETA = remaining × median, with verify estimated at the measured verify median, or
  ×7.5 the screen median, labelled `estimated`.
- `blocked_unknown` state when any attempt is `unknown` (gotcha 12). Show the text "needs `study reconcile`".
- Every number is passed through from stored data. Nothing re-derives J.
- Tests: run each function against the **real fixture roots** read-only (skip if absent) and assert
  the shapes match `tests/fixtures/bayes_api/*.json` keys. That is one test per view, not more.

**WP2: Diagnostics artifact (Bayes side)** (`hornlab_search/bo/diagnostics.py` new; small edits to
`studies/builders.py` model manifest and a `diagnose` subcommand in `studies/cli.py`; test
`tests/test_bo_diagnostics.py` new, `pytest.importorskip("botorch")`).
- Model manifest: add `"hyperparameters": outcome.fit.hyperparameters` (or `{}`), and the
  `limitations` text now says state is not pickled but hyperparameters are recorded. Leave
  `model_state_persisted:false` (true in spirit: no state dict).
- `build_diagnostics` per §1.1 using `efficient_loo_cv`, `model.posterior`, `is_non_dominated`, and
  `Hypervolume`. The HV trace is recomputed over observation order using the frozen reference from
  `study-pareto-metrics-v1`.
- `build_proposal` attaches the diagnostics artifact after the model manifest (as a non-prerequisite
  artifact; it must not change readiness).
- `cli diagnose --root R --study ID`: loads the current training dataset, refits with the
  **same seed and model policy** as the stored model manifest, and attaches the diagnostics artifact. It is idempotent per
  `(revision, training_set_id)`. If the refit's hyperparameters differ from a stored manifest's,
  record both and set `"refit": true`.
- Test: a tiny synthetic 2-D training set (n=12) → artifact validates, LOO rows = n, slice grid = 25,
  relevance sorted. Plus one Pareto case with 2 objectives → `front_ids` non-empty, HV monotone.
- **Acceptance:** `python -m hornlab_search.studies.cli diagnose --root runs/home_landscape_d_2026-11-15/pareto_s63001 --study 0519e65a0ae34ddd9f74d75727bd9d90`
  (run with the bayes-venv interpreter) attaches an artifact < 128 KB.

**WP3: Frontend list + study shell + Live tab** (`static/bayes/bayes_list.js`,
`static/bayes/bayes_study.js`, `static/bayes/bayes.css`, all new). It develops against
`tests/fixtures/bayes_api/*.json` through an injectable `api` object (same pattern as
`mountStudyList(ROOT,{api})` in `studies.js`).
- **List:** a table with policy chip, task, state pill, budget meter (`stackBarHtml`, screens|verify),
  best verify J (bold) / best screen J (muted), root as a mono chip with full path in `title`, and
  relative age. Filters: policy, state, task text, "running only". Default sort: running first, then
  last event. Empty state: "Scanned N study roots: M had studies, K skipped (reasons)". Phone width:
  collapse to cards (task, chip, state, J).
- **Study shell:** a header with task, policy chip, root, state, and a link to its screen/verify runs
  (`#/run/study-<pkg16>/screen`). Tabs: **Live** (default when a package exists) · Data · Model ·
  Propose · Decide · Advanced (the six legacy phases rendered by the existing `studies.js`, untouched).
- **Live tab:** a KPI strip (budget used/total, best verify J, best screen J, ETA, refusals count), a
  convergence chart slot, a "current pick" card slot, and a budget breakdown. It polls `live` every
  10 s while `running`, otherwise once. The chart and card slots are filled by WP4 functions; until
  then they show placeholders.
- Accessibility: tabs are a `role=tablist` and every chart has a text summary underneath (also the
  phone fallback).

**WP4: Frontend views** (`static/bayes/bayes_views.js` new). Pure render functions
`(container, payload) → dispose`, each drawn with `charts.js` (`chart`, `sparkline`, `heat`, `el`,
`catColor`). No new library. Develop against the fixtures.
1. `renderConvergence`: observed J dots (screen = filled, verify = ring, exploration = hollow),
   best-so-far step line, training incumbent dashed line, refusal ticks on the x-axis, log/linear toggle.
2. `renderPickCard`: predicted J with the **model credible interval** bar (that label, verbatim), acquisition
   value + units with the subtitle "ranking score, not a probability", `selection_reason` as plain
   text, fallback badge, cheap-check badges (envelope/throat/materialized), the top-5 param deltas vs
   incumbent, and a "View candidate" deep link once solved.
3. `renderCalibration`: two panels. **(a) LOO on training data** is a predicted-vs-observed scatter
   with ±1.96σ whiskers, y=x, and coverage-95 / Spearman / RMSE chips, with the caption "leave-one-out,
   hyperparameters held fixed (may look optimistic at small n)". **(b) Picks vs measured** is the
   same chart for proposals joined to their solves, shown only when n ≥ 3.
4. `renderSensitivity`: horizontal bars of 1/lengthscale ranked, plus "at bound" flags. Clicking a bar
   opens that knob's **posterior slice** (mean line + ±2σ band + incumbent marker). Small multiples
   for the top 6 on desktop. Caption: "how strongly the model thinks J changes with each knob; a
   model belief, not a measurement". When unavailable, show a **Compute** button that POSTs the
   `diagnose` job and polls the existing jobs endpoint.
5. `renderTrustRegion`: an L-vs-iteration step chart with double/halve markers and success/fail
   counters, plus per-knob box bars (global range grey, TR box coloured, incumbent tick). "Collapsed"
   is labelled *converged*, not *failed*.
6. `renderPareto`: a coverage-error × ripple-dB scatter. Measured points are grey, the front is
   highlighted and joined by a step line, and the frozen reference is drawn as a dashed box corner. The
   tooltip shows J beside each point with the note "J is shown for reference; the frontier uses
   coverage × ripple". There is an HV trace sparkline, and clicking a point opens the candidate drill-down.
- All colours come from CSS tokens. Light/dark and phone width must hold.

### Wave 2 (two agents in parallel)
**WP5: Method board** (`gui/data_bayes_board.py` new, `static/bayes/bayes_board.js` new,
`docs/queue/comparisons/*.yaml` spec format). The comparison spec lists `{name, task,
objective_version, arms:[{label, policy, root|night_summary, seed}], rules:[...]}`. The view is
grouped bars of best verify J per seed per arm, a seed-spread whisker, a screens-to-target table, and rule
verdicts labelled **advisory**. It refuses to mix tasks or objective versions and says so. Write a
spec for `bo_vs_cma_2026-11-15` (3 BO + 3 CMA arms) as the first instance. One test: spec load +
mismatched objective version refused.

**WP6: Drill-down + queue hand-off** (edits `static/studies.js` `studyRunLink` users and
`gui/study_jobs.py` only).
- Every candidate/attempt row gets links to the run view, balloon, isobars, 3D and verify-compare via
  `studyRunLink`. Confirm `viewRunDetail` accepts `study-*` ids, and fix it in the route helper if not.
- Replace the direct "Run" action with **"Queue for tonight"**. It writes a night file + admission packet
  via the existing `tools/bo_compare/preflight_arms.py` check and shows the exact `queue.ps1
  -Admission … -DryRun` result. It never launches a solve. The direct path survives only behind `?dev=1`.

### Wave 3 (one agent, last)
**WP7: Integration, nav and polish** (`server.py`, `app.js`, `index.html`, `app.css`).
- Nav: new **Bayes** group (Studies, Method board) with the running-count badge from `/api/studies`.
- Routes: `#/bayes/studies`, `#/bayes/study/<id>/<tab>`, `#/bayes/board`. The old `#/analysis/studies*`
  routes redirect. The Analysis page link points to Bayes.
- Wire the WP3 shell to the real API and fill the slots with the WP4 renderers: Live = convergence + pick +
  budget; Model = calibration + sensitivity; Propose = pick card + TR or Pareto; Decide = finalists +
  drill-down links.
- Docs: update `docs/CODE_MAP.md` and the runbook's "where to look" section, and mark the handoff
  IMPLEMENTED.
- **One end-to-end check (the only manual pass):** start the GUI. For four studies (the live pilot,
  scalar `66ab47f9…`, turbo `371df039…` and Pareto `0519e65a…`), open each tab and screenshot at desktop + phone, in light + dark
  for the pilot only. Run `diagnose` on the four fixture studies so Model tabs are populated. Check the
  console for errors.

---

## 3. Testing policy (deliberately light)
- One pytest file per new backend module (WP0, WP1, WP2, WP5). Run against real fixture roots
  read-only where possible; synthetic only where needed. There are no frontend unit tests beyond
  keeping `tests/gui_study_lifecycle.mjs` green.
- There is a single manual/browser pass at WP7. No per-WP screenshots and no intermediate review gates.
- Before merge, run the existing suites `pytest tests/test_gui_* tests/test_studies_*` once.

## 4. Orchestrator notes
- Branch per WP off one integration branch `feat/bo-gui`. Merge WP0, then fan out wave 1, merge all
  four, fan out wave 2, merge, then WP7. Conflicts should be impossible given file ownership. If one
  occurs, the later WP rebases.
- A lower-effort implementer agent should be given: this file, handoff §2 and §6, and its WP section
  only.
- **Do not** prepare/launch any study package during this work (code pins). Read-only use of the
  live pilot's root is safe. WP2's `diagnose` writes to a study root, so run it only on the
  **finished** fixture roots, never on `bo_cov_s71001` while the pilot is solving.
- Final report to the owner must say that unstarted arms must be re-prepared after merge (pins changed).

## 5. Definition of done
The handoff's §9, plus:
- The Model tab of every fixture study shows LOO calibration and knob relevance + slices.
- Bayes is a top-level nav item, and the old links still work.
- No GUI action can start a GPU solve except through the night queue.
