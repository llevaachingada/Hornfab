# Handoff: BoTorch in the GUI (architecture, workflows, visualisation, wiring)

**For:** the next agent, who will design and then implement the GUI integration of the Bayesian (BoTorch) study
system. **Written:** 2026-11-15 by the session that built the BO-vs-CMA comparison, TuRBO and production Pareto.
**Your deliverable first:** a design + implementation plan (`docs/research/BO_GUI_DESIGN_<date>.md`) for owner
review. Then implement it in slices, each with tests.

Read this whole note, then `docs/BAYESIAN_STUDIES_RUNBOOK.md`,
`docs/research/BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md` (§3, §5 GUI) and `docs/queue/BO_EXT_PLAN_2026-11-16.md`.

---

## 0. Hard constraints (read before touching anything)

1. **Study code pinning.** Every study package pins a sha256 of **every `hornlab_search/**/*.py`**
   (`studies/package.py` `EXECUTION_CODE_FILES`). Editing any Python file under `hornlab_search/` while a study runs
   or is queued makes its preflight fail. The GUI lives at `hornlab_search/gui/*.py`, so it is covered too.
   - Work in a **git worktree**.
   - Merge only when no study is queued or running (`runs/nights/queue_*.log`, `tools/night_status.py`).
   - A future fix worth proposing: exclude `hornlab_search/gui/**` from `EXECUTION_CODE_FILES`, since the GUI
     doesn't affect a solve. That needs owner sign-off because it changes the pin contract.
2. **No GPU work from you.** No `hornlab-search search/run/verify`, no `studies.cli run --execute`, no `gpu-clean`
   (see `CLAUDE.md` GPU hygiene and `.claude/skills/hornlab-night-queue`). Offline pytest and the GUI dev server are
   fine. Never run anything that imports BoTorch inside the GUI server process: proposals and fits run in the
   **Bayesian interpreter** subprocess (`studies.production.study_interpreter`).
3. **The GUI never computes or ranks scores** (header of `static/studies.js`). Every number comes from a backend
   artifact. Predictions are labelled "model credible interval" and are never shown as measured J.
4. **Rules for every push:** `docs/CONTINUITY.md` + `docs/ISSUES.md` in the same commit; INDEX/CODE_MAP lines for new
   files.
5. **Owner plot style (memory):** isobars use rainbow 3 dB bands with hairline contours, thin lines, no chunky
   halos. Reuse `static/charts.js` (`isobarMap`, `polarMap`, `globePlot`, `chart`, `heat`, `sparkline`,
   `wallSection`), `static/balloon.js`, `static/view3d.js`. Don't add a charting library without asking.

---

## 1. What exists today

### Backend (BoTorch side)
| Piece | Where | State |
|---|---|---|
| Study service (SQLite + content-addressed artifact store), revisions, idempotency | `hornlab_search/studies/service.py`, `store.py`, `schema.py` | merged |
| Build chain: snapshot → training → analysis → proposal (+ pool, model) | `studies/builders.py` | merged |
| Run package (immutable, hashed; `budget_profile` baseline 18+6 or `comparison-60`) | `studies/package.py` | merged (`159ee1a`) |
| Serial adaptive runner, journal, verify/audit selection, reconcile | `studies/runner.py`, `evaluator.py`, `production.py`, `reconcile.py` | merged |
| Policies: `scalar` (GP + qLogNEI over a 4096 Sobol pool, every 4th pick exploration), `cma_seed`, `exploration` | `hornlab_search/bo/*.py` | merged |
| **`turbo`** (trust region) and **production `pareto`** (qLogNEHVI on coverage error × ripple; `pareto_metrics` artifact; frozen reference) | `bo/turbo.py`, `bo/pareto.py`, `bo/metrics.py`, wiring in builders/evaluator/production | **branch `feat/bo-turbo-pareto` (`e25da03`), not merged** — merges after the current nights |
| CLI | `python -m hornlab_search.studies.cli {create,snapshot,analyze,propose,package,run,reconcile,decide,export}` | merged |
| Matched-comparison tooling | `tools/bo_compare/prepare_study.py` (`--policy`), `tools/analysis/study_cohort.py --run-id` | merged / branch |
| Hi-fi offline score (listening window, PIR, seat-to-seat spread) | `tools/analysis/hifi_rescore.py` | merged |

### GUI side
- **Routes:** `#/analysis/studies` (list/create) and `#/analysis/study/<id>/<phase>` with phases **overview, data,
  explain, propose, execute ("Run & Verify"), decide** (`static/studies.js`, `app.js` lines ~150-190).
- **Server:** `gui/server.py` `/api/studies…` GET/POST, `gui/data_studies.py` (panel models: `workflow_panel`,
  `policy_cards`, `execute_view`, `artifact_panel`, `decision_panel_artifact`, `bounded_preview`),
  `gui/study_jobs.py` (CPU job registry for analyze/propose; `StudyRunBridge` prepare_package/launch/cancel).
- **What the current UI shows:** phase stepper, policy cards (scalar / coverage-ripple / cma-seed / exploration;
  `POLICY_MODES` has **no `turbo`**), a candidate table with interval cells, a progress counter strip, a
  verification list, artifact chips, and JSON previews.
- **What it doesn't show:** no BO-specific charts at all. No convergence, no model-fit diagnostics, no
  predicted-vs-measured, no Pareto frontier, no trust-region view, and no link from a study design to the existing
  run views (balloon, isobars, 3D, verify compare).
- **Other GUI areas to connect to:**

| Route | What it is |
|---|---|
| `#/run/<id>` | run detail |
| `/verify`, `/verify/compare` | screen-vs-verify |
| `/balloon` | BL-style balloon |
| `/evolution` | CMA convergence |
| `/umap` | design-space map |
| `/archive` | CMA-ME archive |
| `/3d` | 3D horn render |
| `#/analysis/<report>` | decision-first day report |
| `#/compare` | compare designs |
| `#/elites` | elite catalog |
| `#/launch`, `#/status` | night-queue launch and status |
| `#/briefs`, `#/compose` | briefs |
| `#/typology/<name>` | sandbox |

- **Where study solves land:**
  - `runs/study-<package16>/{screen,verify}/search.ndjson` + `designs/<hash>/response.npz`, i.e. ordinary run
    folders, so the existing run views can open them by run id.
  - Their dataset rows carry run id `screen` / `verify`. That is ambiguous across studies; see §6.

---

## 2. Who uses this and for what (workflows to design for)

The owner is building a home hi-fi horn (80×60-ish, 700 Hz crossover, 1.4-inch driver, DSP available). They are not a
BO specialist. They need **"what should I solve next, why, and did it work?"** in plain language, plus the ability to
pick a trade-off.

| # | Workflow | Steps today | What the GUI must make easy |
|---|---|---|---|
| W1 | **Warm-start a study from past runs** | `study_cohort --run-id …` → create → snapshot → … (CLI) | Pick task + source runs (with counts, exclusions, objective version) → see the training set → one button to analyze/propose. Show plainly which runs feed it and which are excluded. |
| W2 | **Choose a strategy** | `--policy scalar/turbo/pareto` | Strategy cards with a plain-language "use when" (§4), data requirements, and what success looks like. Enable TuRBO only when a good basin exists; Pareto only when metric observations are complete. |
| W3 | **Queue it** | night files + `queue.ps1` (detached) | "Add to queue" from a prepared package, so the study runs inside the existing night system (lane lock, keep-awake, cutoff). It must not launch a GPU job beside a running night. Today's in-GUI `launch` path is separate from the night runner; reconcile them (§5.4). |
| W4 | **Watch it run** | tail logs, read ndjson | A live study page: convergence vs CMA, latest pick and why (acquisition vs exploration vs trust region), refusals, ETA, budget used. |
| W5 | **Judge it** | hand analysis | Predicted-vs-measured (calibration), screen-vs-verify, finalists with full acoustic views, hi-fi score, comparison against matched CMA arms. |
| W6 | **Pick a horn from the trade-off menu** (Pareto) | none | Interactive frontier: click a point → balloon / isobars / 3D / beamwidth / hi-fi, with J alongside → mark a decision → export/print. |
| W7 | **Chain strategies** | manual | "Polish this winner" (TuRBO child study from a scalar study's data), "Map trade-offs" (Pareto child). `create_child` already exists as an action. |
| W8 | **Compare methods** | `docs/queue/BO_*_PLAN` decision rules | A comparison board for matched arms (BO / TuRBO / Pareto / CMA): best verify J per seed, seed spread, screens-to-target. It applies the pre-declared rules and shows a verdict with its evidence. |

---

## 3. Recommended visualisations (each mapped to the data that already exists)

Keep every chart small, accessible and light/dark aware, using the `charts.js` primitives.

| View | Phase/page | Data source | Notes |
|---|---|---|---|
| **Convergence: best-so-far J vs new solves**, BO arms overlaid on matched CMA arms, incumbent line | execute + comparison board | study `screen/search.ndjson`; CMA run ndjson; same objective version only | The single most important chart. Use a log or linear y toggle. Mark exploration picks and refusals as ticks (like the 12 Nov report's convergence figure). |
| **Predicted vs measured J** with 95 % model intervals | explain / execute | proposal records (predicted mean/interval) joined to measured rows by solve id | Shows whether the model is trustworthy. Plot the y = x line, calibration coverage % and rank correlation. |
| **Knob sensitivity from the GP** (1/lengthscale bars) | explain | model artifact hyperparameters (`lengthscales`) | Plain label: "how strongly J reacts to each knob". Same knob names as `param-catalog.v1.json` / paramtips. |
| **1-D partial-dependence slices** (posterior mean ± band along one knob, others at the best design) | explain | needs a small backend endpoint that evaluates the posterior on a line **in the Bayesian subprocess** (not the server) and caches it as an artifact | Optional slice 2. Never computed in the browser. |
| **Design-space map**: where training data and proposals sit (2-D projection) | data / propose | training X, pool, proposals | Reuse the `/umap` view technique. Colour by J, with proposals as rings. |
| **Candidate table** (exists), plus "why this pick": acquisition rank, exploration flag, trust-region in/out | propose | proposal record | Add a plain reason string per row. |
| **Trust-region panel** (TuRBO): L over time with doubling/halving events, success/failure counters, box extents per knob drawn as bars inside [0,1] | execute | turbo state persisted in proposal history (`bo/turbo.py`) | Show "converged/collapsed" clearly as a good stop, not an error. |
| **Pareto frontier**: coverage error (deg) × ripple (dB), measured points in grey, nondominated set highlighted, frozen reference box, hypervolume number, finalists ringed | execute / decide | `pareto_metrics` artifact + measured metric observations + frozen reference | Clicking a point opens its design (see next row). Show J beside each point (owner decision 2026-11-15: the Pareto coverage objective is plain, but J is still displayed). |
| **Design drill-down** from any table or plot point | everywhere | study run dirs are ordinary runs | Deep-link to `#/run/study-<pkg16>/…`: balloon, isobars (rainbow 3 dB), 3D, verify compare. Plus hi-fi numbers. Make sure `viewRunDetail` handles study run ids. |
| **Screen vs verify** for finalists and audits | decide | `verify/search.ndjson` | Reuse `verify.js` (`deltaCellHtml`, summaries). |
| **Method comparison board** | new `#/analysis/compare-methods` or in the analysis report | arm run dirs per night summary | Verdict per pre-declared rule, with the raw numbers underneath. |
| **Budget/progress strip** (exists) | execute | journal state | Add ETA from measured seconds per solve, plus refits. |

---

## 4. Plain-language strategy cards (copy for W2)

- **Scalar ("best single score")**
  - Learns a map of J from everything solved so far, then solves the design most likely to beat the best.
  - Every 4th pick explores somewhere new.
  - Use when you want the best horn under the current brief.
- **Trust region / TuRBO ("polish the winner")**
  - Searches only a box around the current best, which grows when it keeps improving and shrinks when it stops.
  - It stops by itself when the box collapses; that means converged, not failed.
  - Use after scalar has found a good region.
- **Trade-off map / Pareto ("show me the options")**
  - Ignores J's weights and finds the best possible coverage-vs-ripple balances.
  - Use when choosing what you want to hear rather than trusting the weights.
- **CMA seed / exploration** (exist, non-BO): seed from a CMA archive, or space-filling exploration.

---

## 5. Architecture recommendations (your design should confirm or replace these)

1. **Backend-computed view models only.** Add view builders in `gui/data_studies.py` (or a new
   `gui/data_bo.py`): `convergence_view`, `calibration_view`, `sensitivity_view`, `pareto_view`, `trust_region_view`,
   `method_board_view`. They read study artifacts plus run ndjson and return bounded JSON (existing
   `bounded_preview` limits). Unit-test them with synthetic studies, following the `tests/test_studies_*`,
   `test_gui_views_analysis*` patterns.
2. **Heavy or BoTorch work stays in the Bayesian subprocess,** through the existing CPU job registry
   (`gui/study_jobs.py`). Partial-dependence curves become a new job kind that writes an artifact. The server
   process never imports torch.
3. **Policy list:** add `turbo` to `POLICY_MODES` / `POLICY_FALLBACKS` (`static/studies.js`) and to `policy_cards`
   once `feat/bo-turbo-pareto` merges. Keep the backend `capability_status` as the source of truth for
   enabled/disabled plus its reason.
4. **One execution path.**
   - Today the GUI `launch` starts a study directly, while tonight's runs go through night files.
   - Recommend that GUI "Run" = **append a study job to a night file / queue** (or a small wrapper that hands a
     prepared package to `queue.ps1` with `-WaitPid` on any live runner). That keeps lane locks, keep-awake and
     cutoff consistent.
   - Never start a second GPU runner (night-queue skill rule 3).
5. **Identity and linking.**
   - The run id for study solves is `study-<package16>` (folder), but dataset rows say `screen`/`verify`.
   - Propose (separate small backend change, owner OK) writing the study package prefix into dataset row metadata
     so cohorts can select per study (`study_cohort --run-id` currently can't tell studies apart).
6. **Comparison board inputs** come from night `summary.jsonl` files plus the plan docs' arm lists. Ideally a
   small declarative "comparison spec" YAML (like `tools/analysis/specs/*.yaml`) that names the arms, the decision
   rules and the incumbent. The board then renders from that spec, and the rules can't drift.
7. **Hi-fi numbers:** expose `tools/analysis/hifi_rescore.py` results as a cached artifact per study, computed in a
   CPU job, not live.

---

## 6. Known gaps and risks to plan around

- **Pareto contract decisions:**
  - v7 metric policy accepted (owner OK, plain coverage).
  - The training subset uses frontier/crowding, not the spec's "latest 64 + best 64" adaptive rule.
  - Rows worse than the frozen reference still train the model but add no hypervolume.

  Show these as notes on the Pareto page.
- **Ambiguous `screen` run id** in dataset rows (§5.5).
- **Code-pin coupling of the GUI** (§0.1).
- **`study_interpreter`** is `../oc-wt/bo-study/bayes-venv`, outside the repo. Surface a clear "engine missing"
  state (already in `STATES`).
- **Budget profiles:** `baseline` (18+6) is the default. `comparison-60` is for matched campaigns; show which one a
  package carries.
- **Verify cost** is ~7.5× a screen. Show verify ETA separately.
- **Accessibility and phone width:** the existing app is responsive; keep it so.

---

## 7. Evidence and data to develop against (offline, no GPU)

- Pilot study: `scratch/2026-11-14_bayes/pilot/` (package `72834b64…`), runs `runs/study-72834b64942a29f1/{screen,verify}`.
- BO-vs-CMA night (running at hand-off): `runs/nights/bo_vs_cma_2026-11-15/`, studies under
  `runs/bo_vs_cma_2026-11-15/bo_s3100{1,2,3}/`, runs `runs/study-f269f257b24e00f2/…` (arm 1), CMA arm runs listed in
  that night's `summary.jsonl`.
- Next: the `bo_ext_2026-11-16` night (TuRBO/scalar/Pareto arms) produces trust-region state and a Pareto frontier
  to design against.
- The smoke procedure for building turbo/pareto packages offline is in the `feat/bo-turbo-pareto` commit message
  and `tools/bo_compare/prepare_study.py`. Copy the needed dataset shard into the worktree's `scratch/`; builders
  refuse inputs outside the study or repo root.

## 8. Suggested slices (adjust in your design)

1. View models + tests: convergence, calibration, sensitivity, method board (read-only). No pin-sensitive backend
   changes beyond the GUI.
2. Study page charts: execute and explain phases, plus deep links into the run views.
3. Strategy cards plus `turbo` in the policy selector (after `feat/bo-turbo-pareto` merges).
4. Pareto frontier page with drill-down and decision recording.
5. Trust-region panel.
6. Queue integration (W3) and child-study chaining (W7).
7. Optional: partial-dependence job, and per-study dataset identity.

**Acceptance for each slice:**
- offline tests;
- a screenshot at desktop and phone width, light and dark;
- no number the backend didn't produce;
- the study code-pin rule respected at merge time.
