# AGENT HANDOFF — bo-study-v1.1 implementation (M0 done, M1/M2 in flight)

Written 2026-11-12 by the parent orchestrator. Read this fully before touching anything.
**Point the next agent at this file first line:** `C:\Users\hunte\Hrns\oc-wt\bo-study\AGENT_HANDOFF_2026-11-12.md`.

## 1. Governing documents (read in this order)

| Path (absolute) | Role |
|---|---|
| `C:\Users\hunte\Hrns\hornlab-search\AGENTS.md` | **Owner amendment at top: ONE consolidated checkout.** 8 hard rules, GPU hygiene, push rules. |
| `C:\Users\hunte\Hrns\hornlab-search\docs\research\HORN_OPTIMIZATION_HARDENING_2026-11-12.md` | Governing decisions (M0→M3 milestones, guardrails §6). |
| `C:\Users\hunte\Hrns\hornlab-search\docs\research\BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md` | Protocol **bo-study-v1.1**: locked math §3, execution policy §4, GUI §5, artifacts §6, wave table §7. |
| `C:\Users\hunte\Hrns\hornlab-search\docs\research\DATA_GA_IMPLEMENTATION_PROMPTS_2026-11-12.md` | Verbatim slice prompts S0–S11, B0–B8, R0 (contains the worker checkout-policy amendment). |
| `C:\Users\hunte\Hrns\hornlab-search\docs\research\COUNCIL_REVIEW_AND_IMPL_PLAN_2026-11-12.md` | Historical underlying plan. |
| `C:\Users\hunte\Hrns\hornlab-search\TOOLCHAIN.md` | Machine facts, dof caps, `HORNLAB_BEAT_WORKER_DIR` lanes. |

## 2. Parent decision + coordination files (outside the repo, in `C:\Users\hunte\Hrns\oc-wt\bo-study\`)

- `PARENT_M0_CONTRACT.md` — provisional freeze; execution paths superseded by `PARENT_M0_RESUME.md`.
- `PARENT_M0_RESUME.md` — **active lane brief**: canonical checkout, ownership tables, priorities.
- `PARENT_M0_FREEZE.md` — **the frozen contract**: task identity (native-only ATH v4), three-identity rules, encoding contract (`active-projection-v1`, d=13), metric policy (v4 raw via `V4Params` from the resolved brief; never `V8Params.for_class("A")`), cohort evidence, dependency pins, **§8 M1 artifact schemas** (`parameter_study`, `source_fidelity`).
- `PARENT_M0_ASSESSMENT.md` — critical review assessment + legacy-surrogate audit (v1-only scorer).
- `PARENT_DEPENDENCY_DECISION.md` — isolated `bayes-venv` (botorch 0.18.1 stack) + execution rules.
- `CONSOLIDATION_2026-11-12.md` — how all local work was merged into `main` (branch-by-branch).
- `preserve/` directories — snapshots of the pre-consolidation conflicted worktrees.

## 3. Where we are (verified state at handoff)

- **Checkout:** `C:\Users\hunte\Hrns\hornlab-search`, branch `main` (consolidated; local ≈43 commits ahead of origin; origin/main pushed at `3d995a6` + S3 merge by the prior push). Live GPU night queue runs FROM THIS CHECKOUT — never disturb it.
- **Interpreter (project):** `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe` (no botorch — by design).
- **Interpreter (BoTorch, isolated):** `C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv\Scripts\python.exe` (torch 2.14.1+cpu, botorch 0.18.1, gpytorch 1.15.2, linear_operator 0.6.1).

**M0 — complete and validated.**
- `hornlab_search/objective/replay.py` (+ `tools/analysis/offline_scores.py`): brief-target scoring bug FIXED (brief target is the scoring target; stored target is the parity comparator; parity only when target keys identical; test `test_brief_target_is_the_scoring_target_not_the_stored_target`). Native-only joins via `--catalog/--config-filter`; `--rows-cap` exposes full scored set.
- `tools/analysis/catalog.py`, `cohorts.py` (+ native-only census, config/family group keys). `tools/analysis/parameter_activity.py`, `geometry_effects.py` (target-1 exponent invariance, target-3 activity, 64-azimuth contour). `hornlab_search/bo/{encoding,data}.py` (`active-projection-v1`, `TrainingSet`, 4096 pool). `tools/analysis/_common.py` S3 accounting (committed earlier: `dabb5d1`).
- Cohort evidence: native-only **407 rows / ≥192 unique geometries / 196–200 replay-complete**; parity **197–200 compared, max |ΔJ| = 0**, zero backend calls; run_id absent → independent-experiment identity `insufficient_evidence`.
- Tests: 88 (B2/S0) + 51 (S3) + later suite batches — all green offline.

**M1 — 2 of 3 landed, 1 running.**
- ✅ `tools/analysis/source_fidelity.py` + 13 tests (S6): 197/197 cards, DI=balloon everywhere, pairing conservative, artifact `scratch/bo_m0/s6/source_fidelity.json`.
- ✅ S10: `ANALYSIS_TOOL_JSONS` += `parameter_study`,`source_fidelity`; renderers in `app.js`; `tests/test_gui_views_analysis_m1.py` 6 tests (10/10 analysis suite); fixtures `scratch/bo_m0/s10/fixtures/{full,degraded}/`.
- 🏃 S4 `tools/analysis/parameter_study.py` — running; routed to the **200-row** artifact (below).

**M2 — 2 lanes running.**
- 🏃 B3 `bo/{model,acquisition,propose}.py` — locked scalar engine (qNEI recipe in freeze/spec) in the bayes-venv.
- 🏃 S11 `tools/experiments/manifest.py` — pilot manifests (prep-only, no solves).
- Queued after S4 frees a lane: **S9** (bench prep), **B2 `bo/metrics.py`** (canonical metric adapter — R0 has landed, so it's startable now; B7 needs it).

## 4. Data artifacts lanes consume (ALL under `scratch/` — gitignored, regenerate with the CLIs in each tool's docstring)

- `scratch/bo_m0/s0/catalog/catalog.csv` (28.7k rows; **join key = (root, shard_index, row)** — `shard` column is a filename in v2 exports).
- `scratch/bo_m0/r0/offline_scores_native_full/offline_scores.json` — **use this one** (200 rows exposed; the sibling `offline_scores` dir caps at 50).
- `scratch/bo_m0/b2/{activity,pool_manifest,training_fixture}.json` (the last two in `.json`/`.npz` pairs).
- `scratch/bo_m0/s3/*` (cost ledgers, 25-seed verification), `scratch/bo_m0/s6/source_fidelity.json`, `scratch/bo_m0/s10/fixtures/**`.

## 5. File ownership (enforced; do not cross)

| Lane | Owns | Must not touch |
|---|---|---|
| R0 (done) | `objective/replay.py`, `tools/analysis/offline_scores.py`, `tests/test_obj_replay*`, `tests/test_tools_analysis_offline_scores*` | `_common.py`, dataset writer, config, solver, GUI |
| S0 (done) | `tools/analysis/{catalog,cohorts}.py` + its tests | same + `schema.md` |
| B2 (partial) | `tools/analysis/{parameter_activity,geometry_effects}.py`, `hornlab_search/bo/{__init__,encoding,data}.py` + tests; **`bo/metrics.py` next** | scorer math (consume R0), `_common.py`, production configs |
| S3 (done, merged) | `tools/analysis/{_common,seed_variance,ab_compare}.py`, `schema.md` | search/GUI/writers |
| S4 (running) | `tools/analysis/parameter_study.py` + tests | everything above |
| S6 (done) | `tools/analysis/source_fidelity.py` + tests | `fidelity.py`, `_common.py`, gui |
| S10 (done) | gui `data.py` (one tuple), `app.js` (two renderers + wiring), `tests/test_gui_views_analysis_m1.py` | server routes, S4/S6 modules |
| B3 (running) | `bo/{model,acquisition,propose}.py` + tests | encoding/data, replay, tools, gui, config, search |
| S11 (running) | `tools/experiments/**` + tests + scratch manifests | `tools/analysis/**`, config, search, cli, examples |
| Parent only | git mutations (add/commit/merge on `main`), `schema.md`, docs INDEX/CODE_MAP/CONTINUITY at push, pyproject `bayes` extra (deferred decision) | — |

## 6. Remaining implementation slices (and what can go parallel NOW)

Parallel waves respect **≤3 workers beside the parent**:

- **Wave NOW (2 lanes busy: B3, S11; S4 finishing):**
  1. `bo/metrics.py` (B2-owned file; NEW lane as soon as a slot frees) — canonical adapter consuming R0: `V4Params` from the resolved brief (ratio 2.0), response-detrended ripple assertions, frozen masks/weights hashing, `capability_missing` if inputs absent. **Gate for B7.**
  2. **S9** — `tools/bench` timing fixtures + throughput docs prep (no production evaluator edits).
- **After M2 gate (parent reviews B3 + sensitivity/diagnostics):**
  3. **B1 + B4 + B5 in parallel** (disjoint: registry / view-models+job-bridge / runner+reconcile) — one checkout, disjoint files, no worktrees needed.
  4. Then **B6** (needs B4's typed models) and **B7** commit 1→2→3 (sequential by spec), with **B8** adversarial suite; S1 only if QD/warm paths used; S2 audit-only.
- Owner-gated, not implementation: real pilots execution, v8 registration, default flips, pushes beyond task authorization.

## 7. Parallelization mechanics (choose correctly)

- **Default (use this):** one consolidated checkout, disjoint file ownership, ≤3 background lanes + parent; parent commits one validated slice at a time on `main`. This is what just ran S4/S6/S10 + B3/S11 concurrently with zero conflicts.
- **Worktree variant ONLY if the owner explicitly asks** (it overrides the AGENTS amendment): `git worktree add ..\oc-wt\<lane> -b task/<slug> origin/main`; lane does NOT commit (parent cherry-picks/merges `--no-ff` per slice into `main`); scratch artifacts must be written under the checkout's `scratch/` not per-worktree, so joins keep working; expect drift risk — reconcile by diffing slice files only, never whole-tree merges of stale branches.

## 8. Non-negotiables (from AGENTS + plan)

No BEM/GPU solves or host cleanup (queue is live from this checkout); no config/default/objective-registration changes (v8 stays unregistered); never `V8Params.for_class("A")`; never rank J across versions; never weaken/skip tests; no invented parameters/keys/units; read-only over `dataset*/`, `cache*/`, `runs/` (snapshot-hash what you read); no commits by lanes; no worktrees by default; BoTorch only via the bayes-venv, lazily imported; `bo/` modules must degrade to `capability_missing` when the engine is absent.

## 9. Operational gotchas learned (do not rediscover)

1. Background-lane `task_status` can read "running (unconfirmed)" while the lane is actually stopped — verify by `git status --short` + file mtimes, not the status API.
2. Worker fixer lanes stalled twice on long multi-part prompts; the parent took over the bounded last mile (that's legitimate: parent owns integration).
3. The catalog join key is `(root, shard_index, row)`; `offline_scores.load_catalog_index` already handles both export generations.
4. `offline_scores` default `rows` cap is 50 (display) — pass `--rows-cap` for joins.
5. A record's stored target may lack `freq_weights`; the resolved brief target is authoritative for scoring; parity only when keys match (test `test_brief_target_is_the_scoring_target_not_the_stored_target`).
6. The live dataset grows while lanes run (queue appends); cohort counters move between runs — record `generated_utc` and don't panic when counts differ.
7. `scratch/` is gitignored: fixtures needed by committed tests must be `git add -f` (S10's fixtures) or inlined in the test files.
8. LSP diagnostics in this tree are noisy (pre-existing pyright strictness) — tests + `node --check` are the arbiters, not the IDE panel.
