# 10 — SENIOR HANDOFF: Phase B/C — review assumptions, then take metric-composite BO live

- **Date:** 2026-11-23
- **For:** the senior agent taking over from the Pass 1/Pass 2 orchestration + data-collection ops
- **You inherit:** a fully implemented, synthetically validated metric-composite BO engine on a
  pushed feature branch, and six fresh real-data cohorts sized above the training gate. Your job:
  review the assumptions below, run the real-data validation (Phase B, CPU-only), wire production
  execution (Phase C, code), and start real BO runs (Phase D, GPU) — in that order, each gated.

## 0. Two checkouts — keep them straight

| Checkout | Branch / state | Role |
|---|---|---|
| `C:/Users/hunte/Hrns/hornfab-metric-bo-wt` | `feat/metric-aware-bo` @ `39b6c9aa` (pushed) | ALL BO code lives here. Continue Phase C work here. |
| `C:/Users/hunte/Hrns/hornlab-search` | `hornfab-all-2026-11-18` @ `a30f2de9` + **63 dirty files from other agents** | Canonical ops checkout: runs/, dataset/, queues, `.venv`. Do NOT commit here; do NOT incorporate other agents' uncommitted changes. |

- Interpreters: BO/pytest → `C:/Users/hunte/Hrns/oc-wt/bo-study/bayes-venv/Scripts/python.exe`
  (torch 2.14.1+cpu, botorch 0.18.1); queue ops → canonical `.venv\Scripts\python.exe`.
- Docs of record: `docs/research/metric_bo_2026-11-22/` (ADR §1–10, docs 02–09) on the feature
  branch. Doc 07 = real-data plan (prepared, NOT executed). Doc 08 = matched pilot (NOT launched).
  Doc 09 = implementation status + promotion gates.

## 1. What is already done (verified, do not redo)

- **Engine (Pass 1+2, pushed):** v10/v11 contribution extractors with exact J parity; strict
  bounds/score identity (`bo/metric_identity.py`); deterministic `metric-training-npz-v1`
  serialization with tamper-evident reload (`bo/metric_artifact.py`); opt-in policy
  `metric_composite_v1` in `PROPOSAL_POLICIES` (appended 6th, NOT in `PRODUCTION_POLICIES`,
  not GUI-launchable); synthetic-only study path `studies/metric_study.py` over the real
  `ProductionJournal`/`runner.py` with recovery/idempotency tests; `metric_execution_gate` refuses
  real solver execution by construction. Research-only: `physical_composite.py`,
  `metric_constraints.py`, `metric_diagnostics.py` (incl. optional LMC arm E). Advisory
  `optimizer_switch.py` extension is read-only.
- **Verification:** post-hardening suite **587 passed / 3 skipped** (pre-existing native-archive
  skips) on the bayes venv. Independent oracle review of `cffc0a4f`: `ship`; its minors + one
  blocker (the synthetic refit loop silently never refit — integrity gate refused every refit;
  fixed by rebuilding fresh checksum-valid artifacts; tests now assert refits actually happen)
  are fixed in `39b6c9aa`. A council review run produced malformed output and was discarded.
- **Prohibitions honored so far:** no real-data fit, no rescore/replay, no BEM outside normal
  queues, no canonical-checkout changes, no merge.

## 2. The data — six real cohorts, verified counts (your Phase B input)

All are **objective v11, open-envelope identities** (`envelope.enforce: false`, 1200 mm ceiling;
briefs `*_open` — their J must NEVER be ranked against closed-envelope cohorts). Configs:
`examples/typologies/round3_2026-11-22/{r3_c400_a,r3_c400_b,r3_c500,r3_home_fold_a,r3_v11_fold,r3_fav}.yaml`
(canonical checkout). Run dirs (canonical `runs/`), per identity:

| Identity | Run dirs (all pool: same config/brief/backend/fidelity/lib_sha) | usable (ok screens) | best J |
|---|---|---|---|
| compact400 Fold b | `20261122T221847Z-screen-5857d8`, `20261123T153053Z-screen-22c95a` | **145** | **0.9679** fleet best |
| compact400 Fold a | `20261122T220612Z-screen-24ed78`, `20261123T153756Z-screen-b0d8ff` | **151** | 1.0243 |
| compact500 Crowe | `20261122T223153Z-screen-98b41d`, `20261123T154400Z-screen-08157b` | **213** | 1.7051 |
| home v10 Fold a | `20261122T205923Z-screen-391141`, `20261123T161240Z-screen-6db400` | **177** | 1.1932 |
| v11 Fold | `20261123T001107Z-screen-c88c3d`, `20261123T162314Z-screen-9a1835` | **121** | 3.4287 |
| FAV v11 | `20261122T232104Z-screen-2cc59b`, `20261123T163519Z-screen-3c2a65` | **186** | 3.3079 |

Sources: round3 night (2026-11-22) + topup1/topup2/topup2b (resumed CMA, same run dirs) +
seedspread (fresh seeds 31011–31016, new run dirs, 60 evals each). Measured eval rates for
budgeting: c400 ≈ 12 s/eval, home ≈ 18 s, c500 ≈ 32 s, fav ≈ 35 s (GPU screen tier).

Alternate/older data: closed-envelope sculpted900 cohorts (~30 rows each — below gate),
home-v10 closed cohort (~120 rows — below gate identity-wise for round3 but usable for a
closed-envelope Phase B), and ~12.5k v4 / ~12.5k v7 rows (UNUSABLE — extractor supports v10/v11 only).

## 3. Assumptions you must review (each was load-bearing for the counts above)

1. **"ok screen rows" ≠ verified usable rows.** My counts are `ok is True` from each run's
   `search.ndjson`. The real gate is the doc-07 cohort build: canonical term rows, component
   parity, `NAN_TERM_FILL`/penalty refusals, CD `balloon` requirement (cuts_fallback excluded by
   default), identity hashes. Expect some attrition — treat 121–213 as upper bounds until
   `study_cohort`/`build_metric_training` accepts them.
2. **lib_sha stability across pooled run dirs.** The topups/seedspread ran 11-22→11-23 and reused
   the same config yamls, but I did NOT diff `lib_sha`/dependency pins across the pooled run dirs.
   If the hornlab forks changed between round3 and the topups, those run dirs will refuse to pool
   (by design). Check first; do not "fix" by editing identities.
3. **a/b variant configs are separate cohorts.** `r3_c400_a` and `r3_c400_b` are different yamls;
   I counted them separately. Verify their brief/bounds actually differ (if identical, they could
   legally pool — a bonus, not an assumption).
4. **Seedspread rows reached the dataset store.** The fresh-seed jobs are `kind: command` runs with
   default `--dataset-dir`; I verified `search.ndjson` rows but not that the dataset shards/index
   ingested them. Confirm the cohort build sees them.
5. **Terms availability for v11:** every pooled row needs complete balloon CD metrics
   (`cd_status=balloon`); verify none of the pooled arms silently used cuts fallback.
6. **Acquisition semantics:** `composite_utility = -sum(component samples)`; acquisition is
   qLogNEI maximization and is NOT predicted J (tests in `tests/test_bo_metric_acquisition_sign.py`).
   Re-verify if you touch `metric_objective.py`.
7. **Engine economics:** independent-output GPs (no cross-component correlation); constant
   components park flat; interval coverage is empirical, NOT calibrated; predicted J is a proposal
   signal, never a measurement. Promotion requires verified acoustic improvement, never predicted J.
8. **Synthetic refit ≠ production refit.** The synthetic evaluator rebuilds a fresh artifact per
   refit and journals observations; a real worker should publish updated immutable artifacts per
   accepted batch (doc 09 limitation 8 — addressed in design, still to implement in Phase C).

## 4. Phase B — real-data validation (CPU only; owner-authorized data, no GPU)

Follow `07_DEFERRED_REAL_DATA_PLAN.md` steps 1–7, adapted to the round3 cohorts:

1. **Census + cohort build per identity.** Resolve the exact cohort-prep invocation for these runs
   (the `dataset/` shards are thin index rows; `study_cohort.py` consumes a catalog — determine
   whether the catalog must be built over the runs' dataset dirs or the consolidated shards; this
   was left unresolved by design). Suggested first target: **c400b** (145 rows, fleet best).
2. **Identity + parity gates.** Expect typed refusals (`bounds_identity_mismatch`,
   `score_identity_unavailable`, `component_parity`, `metric_selection_unavailable`); refusals are
   findings — record them, never widen gates to make cohorts pass.
3. **Immutable artifact** via `studies/metric_study.build_metric_training`
   (`require_identity=True`), reload through `metric_artifact.artifact_from_bytes`, then
   `validate_metric_training_artifact` with the live projection + frozen score/task identities.
4. **CPU fits:** arms A scalar / B 2-comp / C v10-4comp / D v11-6comp (+E LMC optional) on the same
   frozen artifact; record MAE/RMSE/Spearman/top-decile/coverage/bias/timings.
5. **Holdouts + ranking quality** (whole-run and chronological); report calibration as
   not-calibrated; a scalar win is a legitimate finding.
6. **Verdict doc** in this directory + CONTINUITY/ISSUES.

Gate: composite ranking at least not-worse than scalar on holdouts, with recorded limitations.

## 5. Phase C — production enablement (code, on the feature branch)

Only after Phase B passes:

1. Append `metric_composite_v1` to `PRODUCTION_POLICIES` (studies/production.py) + GUI exposure
   (policy selector/policy_status), update the frozen-tuple tests append-only.
2. `execution_capability`: metric branch = verify_package + `metric_bindings` (re-read stored
   artifact bytes, revalidate identities, snapshot-derived bounds when the config is readable) +
   pool/engine checks. Mirror the synthetic gate's refusal reasons for anything missing.
3. `production.build_worker`: metric evaluator support (load metric bindings + artifact, call
   `fit_and_propose("metric_composite_v1", ...)` with `require_identity=True`), keeping
   scalar/turbo/pareto paths byte-identical.
4. Per-accepted-batch immutable refit artifacts (the `metric_refit_state` mechanism already
   exists; extend to publish updated training artifacts).
5. Tests: production-shape with the synthetic evaluator through `execute_study`, real-path refusal
   tests, GUI tests. No thresholds weakened.

## 6. Phase D — actually optimizing horns (GPU; queue discipline applies)

- One GPU solve at a time; `HORNLAB_GPU_LOCK=refuse` for unattended jobs; `gpu-clean` + VRAM
  baseline before measurements; launch detached (`tools/night_queue/launch_detached.ps1`);
  `-Cutoff` is **today-only**; strict resume refuses cap **shrinks** (raise caps only); the
  runner's bound-pinning watchdog stops arms whose top designs pin a box edge — for BO data
  collection use per-job `watchdog: {pin_ignore: [...]}`; `kind: search` has no seed passthrough —
  use `kind: command` with explicit argv if you need `--cma-seed`.
- Start with one horn (recommendation: **compact400 Fold c400b** — fleet best 0.968, most
  verified) and run the adaptive BO study: BO proposes → screen solves measure → refit → repeat,
  4 finalists + 2 audits at verify fidelity. BO's own accepted solves keep pooling into the cohort
  (same identity) — the data flywheel.
- Round4 box-widening is a SEPARATE owner decision: the bound-pinning evidence
  (L_mm/morph_corner_mm/g_L_mm/az_a_cos_pow) says where, but widening = new identity = cohorts
  reset. Do not widen silently.
- Optional matched pilot (doc 08) only if the owner wants CMA-vs-BO proof: arms A CMA / B scalar BO
  / C composite, 25–30 screens per arm, matched identities, verified improvement per compute.

## 7. Standing constraints (unchanged)

Never modify `objective/scalar_v10.py`/`scalar_v11.py`/`metrics/**` or the frozen
`docs/plan/01_CONTRACTS.md`. Never rank J across identities/versions. Never rank a GPU queue over
another live runner. Every push updates `docs/CONTINUITY.md` + `docs/ISSUES.md`. Canonical checkout
is shared — coordinate before committing there (currently: don't).

## 8. Suggested first 48 hours

1. Review this doc against the code (2 h) — especially §3 assumptions 1–5.
2. Phase B cohort build on c400b + home_fold_a (the two strongest candidates) — resolve the
   catalog invocation, record attrition honestly (half a day).
3. CPU fits + holdouts for c400b (half a day) → written verdict.
4. If verdict is positive: Phase C wiring (1 day) + Phase D first BO study on c400b
   (40–60 BO-proposed screens ≈ 15–25 min GPU + verification).
