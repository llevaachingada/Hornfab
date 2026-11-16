# Handoff: exposing BoTorch in the GUI (verified state, data model, design, slices)

**For:** the agent who will implement the BoTorch GUI work.
**Written:** 2026-11-15, after the BoTorch readiness pass, the four-arm staging, and the launch of the
single-arm cov pilot. **Supersedes** `BO_GUI_HANDOFF_2026-11-15.md` (that note is still useful for the
workflow/visualisation reasoning, but several of its "state" lines are now wrong - see §1.3).
**Owner brief:** "I'm not seeing it anywhere on the GUI. Understand what the data is we need to show
and how we can best show the BoTorch stuff." Implement it yourself; do not ask the owner to design.

Read in this order: this file, `docs/BAYESIAN_STUDIES_RUNBOOK.md`, `docs/research/BAYESIAN_STUDY_
ORCHESTRATOR_SPEC_2026-11-12.md` §3/§5, `docs/queue/BO_MULTITYPOLOGY_PLAN_2026-11-16.md` §2b/§6.
Old note: `docs/research/BO_GUI_HANDOFF_2026-11-15.md`.

---

## 0. The one bug that explains "I can't see it anywhere"

The GUI serves exactly **one** study store:

```python
# hornlab_search/gui/server.py:51
self._study_service = StudyService(self.runs / "studies")
```

Every BoTorch arm is prepared with its own root (`prepare_study.py --root runs/bo_multityp_2026-11-16/
bo_cov_s71001`), and each root gets its own `studies.sqlite3` + content-addressed artifacts. So:

```
GET http://127.0.0.1:8765/api/studies        ->  {"studies": []}      # verified live, 2026-11-15
GET http://127.0.0.1:8765/api/typologies     ->  200, 782,571 bytes   # the rest of the GUI is fine
```

The nav link exists (`static/app.js:4154`, "Analysis -> Studies"), the routes exist, the panels exist.
The list is empty because the studies are in 15 other roots. **Nothing else is broken.** Fixing that
single lookup is slice 0 and it is the difference between "the feature is invisible" and "the feature
works".

Current study roots on disk (16, found with `Get-ChildItem runs -Recurse -Filter studies.sqlite3`):

```
runs/studies                                     <- GUI store, EMPTY (do not delete)
runs/bo_vs_cma_2026-11-15/bo_s31001|2|3          <- 3 scalar BO arms, 60 obs each (complete)
runs/home_landscape_b_2026-11-15/scalar_s61001   <- nightly arm
runs/home_landscape_b_2026-11-15/turbo_s62001    <- TuRBO arm
runs/home_landscape_b_2026-11-15/pareto_s63001   <- Pareto arm
runs/home_landscape_d_2026-11-15/scalar_s61001   <- 60 obs
runs/home_landscape_d_2026-11-15/turbo_s62001    <- 16 obs, trust-region state present
runs/home_landscape_d_2026-11-15/turbo_s62001_rerun
runs/home_landscape_d_2026-11-15/pareto_s63001   <- 58 obs, pareto_metrics artifact present
runs/bo_multityp_2026-11-16/bo_cov_s71001        <- RUNNING (cov pilot, 25+6)
runs/bo_multityp_2026-11-16/_smoke_bo_*          <- 5 prep-only smoke roots (evidence; filter them out)
```

---

## 1. State of the world (verified 2026-11-15)

### 1.1 Backend - all merged in the canonical checkout
| Piece | Where |
|---|---|
| Study service (SQLite + content-addressed artifacts), revisions, idempotency | `studies/service.py`, `store.py`, `schema.py` |
| Build chain: snapshot -> training -> analysis -> proposal (+ pool, model) | `studies/builders.py` |
| Immutable run package | `studies/package.py` |
| Serial adaptive runner, journal, verify/audit selection, reconcile | `studies/runner.py`, `evaluator.py`, `production.py`, `reconcile.py` |
| Policies | `bo/policy.py` (dispatcher), `bo/model.py`, `bo/acquisition.py`, `bo/propose.py`, `bo/turbo.py`, `bo/pareto.py`, `bo/metrics.py` |
| CLI | `python -m hornlab_search.studies.cli {create,snapshot,analyze,propose,package,run,reconcile,decide,export}` |
| Staging tools | `tools/analysis/study_cohort.py`, `tools/bo_compare/prepare_study.py`, `tools/bo_compare/preflight_arms.py` |
| Night gate | `tools/run_campaign_night.py --admission PACKET`, `tools/night_queue/queue.ps1 -Admission/-DryRun` |

**Proposal policies** (`bo/policy.py:43-51`): `scalar`, `turbo`, `pareto` are engine policies and are
production-executable (`production.py:50`); `cma_seed` and `exploration` are non-BO adapters (no model)
and are refused by the production worker. Model: one locked `scalar_pool_v1` GP (`SingleTaskGP`,
Matern-5/2 ARD, `Standardize`, float64, **CPU only** - see the runbook's "Why the GP fit stays on the
CPU"); Pareto fits two of them into a `ModelListGP`.

**Budget profiles** (`studies/package.py:39-45`):
| profile | screens | verify | total | attempts | use |
|---|---:|---:|---:|---:|---|
| `baseline` (default) | 18 | 6 | 24 | 120 | frozen bo-study-v1.1 |
| `comparison-25` | 25 | 6 | 31 | 150 | small multi-typology arms (current) |
| `comparison-30` | 30 | 6 | 36 | 180 | same, 5 more solves |
| `comparison-60` | 60 | 6 | 66 | 300 | matched BO-vs-CMA campaigns |

### 1.2 What is running right now
`bo_cov_pilot_2026-11-16` (owner-authorised single arm): study `4ce07cfdc30e408e9e088eb6ce228f64`,
package `e8a5f81b17968244`, root `runs/bo_multityp_2026-11-16/bo_cov_s71001`, task
`p80x60__ext_throat_hvlaw_cov_v7` (231 training rows, d=9, seed 71001, `comparison-25`).
Screen run: `runs/study-e8a5f81b17968244/screen` (and `verify` after the screens). Logs:
`runs/nights/queue_bo_cov_pilot_2026-11-16.log`, `runs/nights/bo_cov_pilot_2026-11-16_runner_*.log`.

### 1.3 Corrections to the 11-15 handoff (read these before trusting it)
- TuRBO and production Pareto are **merged** (`e25da03`), not on a branch. Do not "wait for the merge".
- `turbo` is already in the Python `POLICY_FALLBACKS` (`gui/data_studies.py`) **and** in the JS
  `POLICY_MODES`/`POLICY_FALLBACKS` (`static/studies.js`) - that part of its step 3 is done.
- Budget profiles are now four, not two.
- `prepare_study.py` also accepts `--config/--brief` (any typology) and `--budget-profile`.
- The BO-vs-CMA night **finished** (3 BO arms x 60 screens / 66 attempts, 3 CMA arms x 60; CMA best
  J 3.23278). It is not "running at hand-off".
- Its §7 "next: bo_ext night" never ran; the current work is the 4-typology campaign instead.

---

## 2. What the BoTorch data actually is (the part to understand before drawing anything)

### 2.1 Two storage layers
1. **Study root** (`<root>/studies.sqlite3` + `<root>/artifacts/<sha256>`). Tables: `studies`,
   `revisions`, `artifacts`, `events`, `idempotency`, `packages`, `attempts`, `observations`,
   `proposal_state`, `launches`, `decisions`.
2. **Solve runs** (`runs/study-<package16>/{screen,verify}`) - *ordinary* hornlab runs:
   `search.ndjson`, `designs/<hash>/response.npz`, `run.json`. Every existing run view can open them.

`observations` is the join table: `(study_id, package_id, observation_seq, attempt_id, physical_id,
score_id)`. `attempts` holds `(solve_id, kind, candidate_json, reserved, status, result_json)`.

### 2.2 Artifacts: what each one answers (these are your only data sources)
| kind (schema) | Question it answers | Key fields |
|---|---|---|
| `study-snapshot-v1` | What data feeds this study? | `cohort`, `completeness`, `exclusions`, `parity`, `source`, `spec_hash` |
| `study-training-manifest-v1` | What did the model train on? | `n`, `d`, `n_eligible`, `active_keys` (the searched knobs), `elite_ids`, `maximin_ids`, `excluded_ids`, `meta.measured_dependency_pins`, `meta.cohort_policy`, `dependencies` |
| `study-training-dataset-v1` | Which rows? | `selected_ids`, `elite_ids`, `maximin_ids`, `excluded_ids`, `training_set_id` |
| `study-analysis-v1` | Is the data trustworthy? | `recommendation_status`, `heldout_support`, `refusals_by_reason`, `metric_score_identity`, `snapshot` |
| `study-pool-manifest-v1` | What was proposed from? | `n_candidates`, `summary`, `encoding`, `config`, `status_note` |
| `study-model-manifest-v1` | What model, which engine? | `policy`, `counts`, `library_versions`, **`model_state_persisted: false`**, `limitations` |
| `study-proposal-v1` | The pick and why | `candidate` (params, `active_vector`, `checks{envelope,throat,materialized}`, `descriptors`), `predicted{j_mean, j_lower, j_upper, y_sd, interval_label, nonphysical}`, `acquisition{value, units, n_candidates, chunks, acq_seed}`, `selection_reason`, `fallback`, `counts`, `verification_mode`, `trust_region` (turbo), `pareto` (pareto) |
| `study-pareto-metrics-v1` | The trade-off data | `reference{limits, ref_point, units}`, `observations{<id>: {coverage_deg, ripple_db, status, physical_metric_spec_hash}}`, `metric_policy`, `n_complete`, `n_excluded`, `reference_policy` |
| `run-package-v1` | What will execute | `budget`, `budget_profile`, `lane`, `deadline`, `code_pins`, `dependency_pins`, `artifacts`, `resolved_config`, `adaptive_policy`, `recovery_rules` |
| `results` / `decision` | Outcomes | measured rows + the recorded decision/export |

**Per-solve truth** lives in `attempts.result_json` (and mirrors into the run ndjson):
`observed_j`, `j`, `eligible`, `outcome`, `error`, `terms{cov, rip, di, diag, flat, flat_cv, dislope,
distd, load, lfp20_hz, lfp50_hz, f11_hz, ...}`, `weights{...}`, `target{coverage_h_deg,
coverage_v_deg, f0_hz, band_lo_hz, band_hi_hz, ...}`, `normalized_terms{cov, rip}`,
`canonical_replay{status, parity_delta, complete}`, `params{...}`, `x`, and the identity triple
(`design_hash`, `geometry_hash`, `solve_id`, `physical_id`, `score_id`, `metric_id`).
This is what a "why/measured" table must render - not a re-derived number.

### 2.3 What is NOT available (do not design around it)
- **GP hyperparameters / lengthscales are not persisted.** `model_state_persisted: false`; the model
  manifest has only `counts`/`detail`; no artifact contains `lengthscale`. The old handoff's
  "knob sensitivity from 1/lengthscale" needs a **new artifact** computed in the Bayesian subprocess
  (slice 9). Until then, do not promise it.
- **Predicted J is per proposal**, not per measured row. Join proposals to measurements by
  `attempt_id`/`solve_id`; never interpolate.
- **No cross-study index.** Study ids are uuid4 hex and unique, but nothing maps id -> root; that is
  slice 0's job.
- **No live push.** Panels are polled by the client; refresh on the existing cadence.

---

## 3. What the GUI shows today (and what is missing)

- Routes: `#/analysis/studies` (list/create) and `#/analysis/study/<id>/<phase>`
  (`static/app.js:185`; `studies.js:39`). Phases (`data_studies.py:14`): **overview, data, explain,
  propose, execute ("Run & Verify"), decide**.
- Server: `GET /api/studies`, `/api/studies/<id>`, `/api/studies/<id>/<phase>`,
  `/api/studies/<id>/artifacts/<kind>`, `/api/studies/<id>/jobs`, `/api/studies/<id>/export`
  (`server.py:123-197`), plus POST actions (`server.py:332+`). Panel builders:
  `workflow_panel`, `policy_cards`, `execute_view`, `artifact_panel`, `decision_panel_artifact`,
  `bounded_preview` (`gui/data_studies.py`). CPU jobs: `gui/study_jobs.py` (`StudyCpuJobs`,
  `StudyRunBridge`).
- What renders: phase stepper, 5 policy cards, candidate table with interval cells, progress counter,
  verification list, artifact chips, JSON previews.
- **Missing:** root discovery (§0), convergence, calibration, "why this pick", trust-region panel,
  Pareto frontier, method board, refusals breakdown, ETA, deep links into run views (the helper
  `studyRunLink` exists but is barely used), and any indication that a study is queued/held by the
  night system.

---

## 4. Recommended exposure (design)

### 4.1 Information architecture
Promote Bayes to a first-class area; it is a different workflow from a CMA run.

```
Bayes                              (new top-level nav group, next to Runs / Analysis)
  Studies                          #/bayes/studies        list of every study, any root
  Study <id>                       #/bayes/study/<id>/<phase>   (same 6 phases)
  Method board                     #/bayes/compare        matched arms: BO / TuRBO / Pareto / CMA
```
Keep the old `#/analysis/studies` as a redirect (the owner has links in docs).

### 4.2 Study list (the fix for "I can't see it")
One row per study, merged across roots:

| column | source |
|---|---|
| task + objective version | `spec.task` / snapshot `spec_hash` metadata |
| policy chip (scalar / turbo / trade-offs / cma-seed / exploration) | study spec `policy.proposal_policy` |
| status (no data / proposed / packaged / running / done / refused) | `readiness()` + artifact states |
| budget | package `budget_profile` + `budget` vs `observations`+`attempts` |
| best **verify** J and best screen J | observations/attempts, verify separated |
| root | `runs/...` path, shown as a mono chip/tooltip (provenance matters) |
| age / last event | `studies.event_seq` or artifact `generated_utc` |

Filters: policy, task, running-only, failed-only. Empty state must say *"N study roots found, 0
studies in them"* so a future root problem is self-diagnosing.

### 4.3 Per-study page (extend the existing six phases)
| phase | add |
|---|---|
| overview | one-paragraph "what this is / what it cost"; the run-package card (lane, deadline, budget, pins, admission/night membership); links to the screen/verify runs |
| data | training-set composition (n/d/active knobs, included vs excluded counts, refusal reasons), dependency pins vs executing interpreter, "this cohort came from these runs" |
| explain | analysis status (`recommendation_status`, heldout support, `refusals_by_reason`), pool size, model policy + engine versions; **calibration chart** (once slice 3) |
| propose | policy cards (5), **why-this-pick** panel, candidate table with acquisition rank + exploration flag, trust-region box (turbo), frontier (pareto) |
| execute | live **convergence**, progress (solved vs budget, verified vs pending, refusals by reason), ETA from measured seconds, trust-region L trace (turbo), frontier (pareto) |
| decide | finalists + audits (screen vs verify), deep links to balloon / isobars / 3D / verify-compare, hi-fi numbers when cached, decision record |

### 4.4 The eight BO views, each with its contract
| # | view | phase | data | notes |
|---|---|---|---|---|
| 1 | **Convergence**: best-so-far J vs solve index, incumbent line, refusals as ticks, exploration picks marked | execute | observations + attempts (`observed_j`, `kind`, `selection_reason`) | log/linear toggle; same objective version only; overlay a CMA arm only when you have its ndjson |
| 2 | **Why this pick**: predicted J with credible interval, acquisition value + rank, `selection_reason`, `fallback`, cheap-check badges | propose | `study-proposal-v1` | the single most useful panel for a non-specialist |
| 3 | **Calibration**: predicted (CI) vs measured J, y=x, coverage %, Spearman rho | explain/execute | proposals joined to attempts by solve_id | shows whether the model can be trusted |
| 4 | **Budget/ETA**: used/total, screens vs verify, seconds/solve, ETA | execute | package + attempts timestamps | verify is ~7.5x a screen - show separately |
| 5 | **Trust region** (turbo): L trace with double/halve events, success/fail counters, box lo/hi per knob as bars | execute | `proposal.trust_region` (`state_after`, `attempts[].box`, `length`, legal counts) | "collapsed" is convergence, not an error |
| 6 | **Pareto frontier**: coverage deg x ripple dB, grey measured, highlighted nondominated, frozen reference, hypervolume | execute/decide | `study-pareto-metrics-v1` + `proposal.pareto.reference` | click a point -> candidate drill-down + J |
| 7 | **Method board**: matched arms, best verify J per seed, seed spread, screens-to-target, verdict from the plan's fixed rules | new page | `runs/nights/<night>/summary.jsonl` + a small comparison spec YAML | never rank across briefs/objective versions |
| 8 | **Drill-down**: candidate -> run view (`#/run/study-<pkg16>/...`), balloon, isobars, 3D, verify compare, hi-fi | everywhere | run dirs | `studyRunLink` exists; verify `viewRunDetail` accepts `study-*` ids |

**Hard UI rules:** every number comes from the backend; the model interval is labelled *model
credible interval*, never "measured"; the acquisition value is a ranking diagnostic, never a
probability; the GUI never computes J or ranks designs; bounded JSON only (128 KB artifact cap,
`MAX_ITEMS`/`MAX_BYTES`); light/dark and phone width must keep working.

---

## 5. Implementation slices (each independently shippable, each with tests)

**Slice 0 - multi-root discovery (blocker; do this first).**
Add `gui/study_roots.py`: scan `runs/**/studies.sqlite3`, skip `runs/studies` (the GUI store) and
`_smoke_*` roots, build `{study_id: (root, StudyService)}` with a bounded cache keyed on mtime.
Change `hub`/`Api` (`server.py`) so every `/api/studies*` route resolves the root by study id;
`GET /api/studies` merges `study_summaries()` across roots and adds `root` + `task` + `policy`.
Tests: synthetic two-root fixture in `tmp_path` (use `StudyService` to create a study in each), id
uniqueness, missing/corrupt sqlite is skipped not fatal, list bounded at 50/root, unknown id -> 404.
Acceptance: with today's disk, `/api/studies` returns >= 15 studies including the running pilot.

**Slice 1 - list UI** (root/task/policy/budget/state/best-verify chips, filters, honest empty state).
Tests: `tests/test_gui_studies_module.py`, `test_gui_study_adapters.py` patterns + a DOM-stub case in
`tests/gui_study_lifecycle.mjs`.

**Slice 2 - execute truth**: build progress from `attempts`/`observations` (kinds screen/verify/audit,
statuses reserved/resolved/refused/unknown), refusals by reason, ETA, and stop showing the package
fallback once a screen exists. Tests: `tests/test_studies_b5_runner.py` style fixtures.

**Slice 3 - why-this-pick + calibration** (views 2 and 3). Pure read: proposal + attempts.
**Slice 4 - convergence** (view 1) including the incumbent line from the training set.
**Slice 5 - budget/package panel** (view 4) + pins + night/admission membership.
**Slice 6 - trust region** (view 5) against `runs/home_landscape_d_2026-11-15/turbo_s62001`.
**Slice 7 - Pareto frontier** (view 6) against `runs/home_landscape_d_2026-11-15/pareto_s63001`
(58 obs + `study-pareto-metrics-v1` already on disk).
**Slice 8 - method board** (view 7) from night summaries + a comparison spec; needs owner sign-off on
the spec file format.
**Slice 9 - hyperparameter persistence + sensitivity** (view: 1/lengthscale bars). Requires a new
optional field in the model manifest written by `bo/model.py` + `builders.build_proposal`, and owner
sign-off because it touches an artifact schema. Do not fake it from acquisition values.
**Slice 10 - deep links + hi-fi artifact** (view 8), cached via a CPU job.
**Slice 11 - queue integration**: "Send to queue" writes a night file + admission packet and launches
via `queue.ps1 -Admission` (never a direct GPU launch, never a second runner). Reuse
`tools/bo_compare/preflight_arms.py` as the pre-send check.

Suggested order: 0, 1, 2, 3, 4, 5, 7, 6, 8, 10, 11, 9. (Pareto before trust region because the Pareto
data on disk is richer and the owner's open question is a listening trade-off.)

Acceptance for every slice: offline pytest; a screenshot at desktop and phone width, light and dark;
no number the backend did not produce; no new charting library (use `charts.js`: `isobarMap`,
`polarMap`, `globePlot`, `chart`, `heat`, `sparkline`, `wallSection`).

---

## 6. Gotchas that will bite you

1. **Code pins include the GUI.** `studies/package.py:57-59` hashes every `hornlab_search/**/*.py`
   into `code_pins`, so `gui/*.py` edits change the pin set. A package prepared before your edit will
   fail `execution_condition`/preflight after it. Consequence: **prepare arm packages only when the
   code is frozen**, and expect to re-prepare after a GUI change. The running pilot's package is
   already pinned and keeps running; the three unstarted arms are staged but *not prepared*, so they
   are safe.
2. **No torch in the server.** Proposals/fits run in the Bayesian subprocess
   (`studies.production.study_interpreter`, currently `../oc-wt/bo-study/bayes-venv`). CPU jobs go
   through `gui/study_jobs.py`; never import botorch in `gui/**`.
3. **GPU hygiene:** the GUI must never start a solve. Launching is the night runner's job
   (`.claude/skills/hornlab-night-queue`: detached, keep-awake, one runner, lane locks).
4. **Objective versions:** production accepts v4 and v7 only; `band_split`/`meh` configs are refused.
   Never compare J across versions or across briefs.
5. **Pareto semantics (owner decision 2026-11-15):** the frontier objective is *plain* coverage error
   x ripple; J (which keeps the 8 kHz floor) is displayed next to every frontier point but is not the
   frontier objective. Rows worse than the frozen reference still train the model but add no
   hypervolume. Show both facts on the page.
6. **Verify is expensive** (~7.5x a screen) and only runs after the screens; do not mix it into the
   screen progress bar.
7. **Study solves are ordinary runs** but their dataset rows carry run id `screen`/`verify`, which is
   ambiguous across studies. Until a per-study run id is written into row metadata, never build a
   cohort by `--run-id screen`.
8. **Model state is not persisted** (§2.3). Do not display hyperparameters until slice 9.
9. **Bounded everything:** artifacts can exceed 128 KB and real ids/configs exceed 50 entries; use
   `bounded_preview` and say when you truncated.
10. **Revision drift / stale artifacts** are normal (the store marks them). Show them; never silently
    reinterpret an old artifact as current.
11. **Do not delete `runs/studies`** even when empty; it is the GUI's own store root.
12. **Ambiguous recovery:** a crashed attempt stays `unknown` and blocks a new claim until
    `study reconcile` proves the owner dead. Surface that state instead of offering "run again".

---

## 7. Evidence to develop against (offline; no GPU, no solves)

```powershell
# every study root and its artifacts
Get-ChildItem runs -Recurse -Filter studies.sqlite3 | ForEach-Object { $_.DirectoryName }

# one study, all artifacts, field names (read-only)
.venv\Scripts\python.exe - <<'PY'
import glob, json
root = "runs/home_landscape_d_2026-11-15/pareto_s63001"
for p in glob.glob(root + "/artifacts/*"):
    d = json.load(open(p, encoding="utf-8"))
    print(d.get("schema"), sorted(d)[:12])
PY

# live panels (read-only)
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/api/studies
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/api/studies/<id>/execute
```

Fixture studies (all complete or nearly so, no GPU needed to read them):

| purpose | root | study id | package | obs |
|---|---|---|---:|---:|
| scalar, 60 screens + 6 verify | `runs/bo_vs_cma_2026-11-15/bo_s31001` | `66ab47f9b47e45a68791dda68ef777b5` | `f269f257b24e00f2` | 60 |
| scalar arm 2 / 3 | `.../bo_s31002`, `.../bo_s31003` | `23733930…`, `de83380a…` | `24b6cdf8…`, `82b9e51a…` | 60 |
| TuRBO with trust-region state | `runs/home_landscape_d_2026-11-15/turbo_s62001` | `371df039514942faae3802d9d2992212` | - | 16 |
| Pareto with `pareto_metrics` | `runs/home_landscape_d_2026-11-15/pareto_s63001` | `0519e65a0ae34ddd9f74d75727bd9d90` | - | 58 |
| live pilot (`comparison-25`) | `runs/bo_multityp_2026-11-16/bo_cov_s71001` | `4ce07cfdc30e408e9e088eb6ce228f64` | `e8a5f81b17968244` | running |

Screen/verify runs to deep-link: `runs/study-f269f257b24e00f2/{screen,verify}`,
`runs/study-e8a5f81b17968244/{screen,verify}`, plus the nightly arms' run dirs (find them by
`run.json` next to each root).

Monitoring (safe during a live night): `.venv\Scripts\python.exe tools/night_status.py --since-hours 12`.

---

## 8. Open questions for the owner (ask once, then decide)

1. **Nav placement:** top-level **Bayes** group (recommended) or keep it under Analysis → Reports?
2. **Store convention:** discovery over per-arm roots (recommended, no migration) or start preparing
   every new arm with `--root runs/studies/<slug>` so one store always sees them? (Discovery is
   needed either way for the 15 roots already on disk.)
3. **Persist GP hyperparameters** (slice 9) so sensitivity can be shown? Additive optional fields in
   the model manifest; no frozen-contract change, but it touches an artifact schema.
4. **GUI launch:** route "Run" through the night queue (recommended: keeps one GPU runner, lane
   locks, keep-awake, cutoff) or keep a direct launch path?
5. **Method board scope:** implement the pre-declared rules from the plan docs, or only display the
   raw numbers and let the owner judge?

---

## 9. Definition of done for the first delivery

- `/api/studies` lists every study on disk with its root, policy, budget and state; the running pilot
  appears while it is solving.
- Opening the pilot from the GUI shows: training composition (231 rows, d=9, active knobs), the
  current pick with predicted J + interval + why, live convergence, budget/ETA, refusals, and links
  to its `screen` run views.
- Opening the Pareto arm shows a frontier with the frozen reference and clickable points.
- Opening the TuRBO arm shows its trust-region box and L trace.
- No number in the UI is computed by the client, and no solve can be started from the GUI except
  through the night queue.
