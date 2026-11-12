# Refusals, CMA trajectories, and dataset hygiene — handoff (2026-11-12)

**Audience:** an independent senior reviewer/implementer designing the next data/search improvements.
**Status:** research handoff only. No code, config, queue, or dataset changes were made for this document. Read-only findings; verify before acting.
**Repo snapshot:** `origin/main` = **5f7c116**. The live checkout is on `day/2026-11-12-queue` at `79edc8d` (not on main); the GPU night queue is still running (`g2`–`g9`). Use a main-synced worktree for code reads/runs; do not touch the live checkout, `runs/`, `cache*/`, `dataset*/`, or the queues.
**Owner's question:** "Is there a simple way so that anything that is an error gets rejected — it just gets removed from the optimizer, so refusals disappear and don't influence the trajectory of CMA/genetic algorithms?" Plus: achieve this **without over-constraining the horn parameters**, without corrupting the data, and without wasting time.

---

## 1. Short answer

**Yes for plain CMA-ES; no for CMA-ME as a simple config change.**

- **Plain CMA (`search.algorithm` absent/`plain`):** `search.infeasible_penalty: resample` (B.6) plus
  `search.budget_counts: valid` (B.4) and `search.max_attempts` is the implemented "remove it from the
  optimizer" path. A deterministic refusal is replaced by a fresh sample from the same CMA distribution
  (up to 10 tries per candidate) and **never told** to the ES. The refusal is still evaluated, logged in
  `search.ndjson`, and (with `valid`) free; the ES only ever sees valid candidates. Tests:
  `tests/test_search_resample.py` (`test_refusals_are_logged_but_every_told_candidate_is_valid`).
- **CMA-ME (the current core_law/g2 atlas runs): not a simple drop.** ribs 0.12 `Scheduler.tell` requires
  one result per asked solution; `resample` is refused at load with a `ConfigError`
  (`config.py:1366-1373`). Today `cma_me.tell_batch` tells every result, including refusals, using the
  **seed's archive coordinates** and the penalty objective (`cma_me.py:357-370`). The archive is protected
  (a penalty cannot replace a real elite), but the emitter's trajectory still sees the penalty. The
  available archive-level mitigation is **CMA-MAE** (`search.qd.maes`, `cma_me.py:157-183`): a
  `threshold_min` can reject penalty rows and the emitter drops `bounds=` (avoiding the ribs bounds-
  resampling distortion). That improves the archive, **not** the emitter's full trajectory. A true
  drop/resample in CMA-ME needs a custom scheduler/tell wrapper — new code, not a config flag.
- **`budget_counts: valid` alone does NOT remove the refusal from the trajectory.** It only stops the
  refusal consuming budget; the refusal is still told as a penalty. The exact default is documented at
  `config.py:845-868` and tested at `tests/test_search_budget_counts.py:80-102`.
- **The current high-refusal run is CMA-ME**, not plain CMA: `20261030T170642Z-screen-fbab4f` has
  `algorithm: cma_me`, `infeasible_penalty: graded`, no `budget_counts`. Its 434 refusals are told with
  the penalty. The `graded` option only grades `invalid_envelope`; the 434 are `invalid_geometry` /
  `mesh_too_large`, so they all carry the flat 1000 penalty.

**The simple path for a future plain-CMA experiment:**

```yaml
search:
  budget_counts: valid        # refusals do not consume budget
  max_attempts: 600           # default 4 x budget; hard stop for an all-refusing box
  infeasible_penalty: resample
```

Do **not** pair `resample` with `cma_me` (refused). For QD, use `search.qd.maes` (CMA-MAE) or accept the
penalty; do not pretend a one-line drop exists.

---

## 2. What the code does today — exact call sites

Line numbers are from the `origin/main` code at `5f7c116` (same code as the G2 worktree; verify with
`git show origin/main:<path>`).

### Evaluation / refusal kinds
- `hornlab_search/search/evaluate.py:66-75` — `KIND_INVALID`, `KIND_INVALID_ENV`, `KIND_TOO_LARGE`,
  `KIND_SOLVE`, `KIND_METRICS`, `KIND_EXC`; `DETERMINISTIC_KINDS = (invalid_geometry, invalid_envelope,
  mesh_too_large)`. `solve_failed` is **not** deterministic and is retried.
- `evaluate.py:1019-1033` — `_failure_penalty`: `PENALTY_INVALID` for deterministic kinds,
  `PENALTY_FAILED` for solver/metrics failures; `graded` only for `invalid_envelope` and only when the
  config sets `infeasible_penalty: graded`.
- `objective/terms.py` — `PENALTY_INVALID = PENALTY_FAILED = 1000.0`; no infinity (an inf would poison the
  CMA covariance).
- `evaluate.py:1183-1200`, `:1400-1416`, `:1499-1556` — where the mesh/generator/envelope checks set the
  failure kind. `mesh_too_large` is raised by the mesher; `invalid_envelope` is brief-dependent and has
  `no_marker`.
- `evaluate.py:12-19` — deterministic failures are memoized/marker-cached; solver failures are not.
- `evaluate.py:1036-1041` — the failure marker lives under
  `<solve_cache_root>/failures/<design>-<mesh>-<solve>.json`; a replay with the same key is
  `fail_cached`, writes no new dataset record, and consumes no budget. The marker carries `lib_shas` and
  `brief_hash`, so a library/brief change re-evaluates.

### Plain CMA and budget
- `hornlab_search/search/cma.py:55-61` — `REFUSAL_KINDS = DETERMINISTIC_KINDS`,
  `DEFAULT_ATTEMPTS_FACTOR = 4`, `RESAMPLE_CAP = 10`.
- `cma.py:64-68` — `_refusal(ev)` (deterministic refusal, including cached replays, is the resample class).
- `cma.py:71-85` — `budget_policy`: `new` (default) vs `valid`; attempts cap = explicit
  `max_attempts` or 4 x budget in `valid`; `None` cap in `new`.
- `cma.py:88-103` — `budget_count`: cached -> ignored; every new eval increments `n_new`/`attempts`;
  valid increments `n_valid`; deterministic refusals increment `n_refused_free` (but are still told).
- `cma.py:105-115` — `budget_exhausted`: `n_valid` in `valid`, `n_new` in `new`; attempts cap; campaign
  `max_evals` cap.
- `cma.py:414-429` — `valid` mode sets `tolfun=0`, `tolfunhist=0`, `tolflatfitness=1e12` so pycma's
  fitness-range stops do not fire on a refusal streak; the budget policy is the termination authority.
- `cma.py:551-601` — B.6 resample: in the prefetch and serial paths, a refused candidate is replaced with
  `es_instance.ask(1)` up to 10 times, `state["n_resampled"]` increments, and the refusal is logged but
  never told. After the cap the last refusal is told with the usual penalty so a fully-refusing box stops.
  `cma.py:597-599` — if the budget runs out mid-generation, `tell` is skipped (a resume replays).
- `cma.py:637-640` — the surrogate seeding excludes rows with `objective >= PENALTY_FAILED`.

### CMA-ME and CMA-MAE
- `hornlab_search/search/cma_me.py:3-28` — CMA-ME on ribs 0.12: one `GridArchive`, one
  `EvolutionStrategyEmitter(ranker="2imp", es="cma_es", selection_rule="mu")`, `Scheduler`; the docstring
  explicitly says budget semantics are the same as `cma.py` and a partial generation is not told.
- `cma_me.py:157-183` — B.8 CMA-MAE: `search.qd.maes` -> `GridArchive(learning_rate=0.01..0.1,
  threshold_min=-j_threshold)`, `ranker="imp"`, emitter `bounds=None`; absent `maes` = today's archive.
- `cma_me.py:357-370` — `tell_batch`: **every** evaluation goes to `scheduler.tell`; failed evaluations
  reuse the **seed's** measures (or the `(0,0)` fallback if the seed had no metrics) and a penalty
  objective. The docstring: a failure "can never replace a real elite"; it is counted as a failure.
- `cma_me.py:331-344` — B.4 budget block in the CMA-ME run.json (valid/refused/attempts).
- `config.py:1366-1373` — `search.infeasible_penalty: resample` with `cma_me` is a `ConfigError`:
  "ribs scheduler.tell needs one result per asked solution; refusals there keep today's seed-cell
  fallback."
- `cma_me.py:288-344` — archive payload/stats; the archive is where you can verify whether penalty rows
  ever occupy cells.

### Dataset behavior
- `hornlab_search/dataset/record.py:245-274` — `_arrays_for`: "Arrays of a successful evaluation. A
  failure has none."
- `record.py:297-317` — `build_record` **records failures too**: `ok=False`, `error` set, arrays empty.
  The docstring says this is intentional: "A surrogate needs to learn where the invalid region is, and a
  search needs to know how much of its budget went to failures."
- `dataset/store.py:18-19` — failures write no arrays; `:431-458` `stats()` reports `n`, `n_ok`,
  `n_failed`; `:502-522` `to_training_arrays(ok_only=True)` by default excludes failures (with
  `ok_only=False` they become NaN labels); `:546-551` solver crashes are excluded from training labels
  (they say nothing about the design).
- `search/evaluate.py:1671-1676` — a `fail_cached` replay writes no new dataset record; a first
  deterministic failure **does** go through `store.append` (metadata, no arrays).

### Tests and docs
- `tests/test_search_budget_counts.py` — B.4 contract:
  - `:80-92` default `new`: refusals DO consume budget; `be.calls == len(ok)` (the backend runs only for
    valid candidates); no `budget_counts` key in run.json.
  - `:45-67` `valid`: 10 valid exactly, refusals free, attempts = rows, cap 4 x budget.
  - `:70-78` all-refusing box stops at the cap (12 rows for budget 3), `stop_reason: budget`.
- `tests/test_search_resample.py` — B.6 contract:
  - `:26-52` resample + valid reaches the valid budget, refusals still logged, none consume budget.
  - `:54-63` "every told candidate is valid": best J comes from a valid row; refusals are logged.
  - `:65-82` an all-refusing box burns the 10-resample cap and still tells the last penalty.
  - `:84-99` `cma_me` + resample is a `ConfigError`.
- `docs/reference/PARAMETERS.md:10206-10328` — B.4/B.6/B.5/B.8 docs.
- `docs/research/SEARCH_MATH_DOSSIER_2026-11.md:19-96` — owner summary and Q1: refusal rate ~14-16%;
  9.8% of generations at least half flat-penalty; rejected designs are a truncated-sampling problem;
  recommendation: pre-mesh feasibility predicate + pycma resampling, graded penalty, widen walls, keep
  the penalty bedrock (never inf).
- `docs/IMPLEMENTATION_PLAN_2026-11-12_DAY.md` §5 — the measurements behind the amendments.

---

## 3. Measured evidence from the repo (read-only)

- **Run `20261030T170642Z-screen-fbab4f` (core_law, CMA-ME):** `run.json` search block is
  `algorithm: cma_me`, `infeasible_penalty: graded`, `budget_counts` absent.
  `search.ndjson`: **1001 rows, 567 ok, 434 refused** — 327 `invalid_geometry`, 106 `mesh_too_large`,
  1 `solve_failed`. Every refusal's objective is **1000**. The run's `archive.json` has **17 occupied
  cells and 0 penalty cells** (the seed cell is occupied, so the refusal fallback cannot replace a real
  elite). The archive is clean; the emitter still sees 434 penalties.
- **Main dataset (`dataset/`):** 57 shards, **28,573 records: 23,939 ok, 4,634 failed (16.2%)**. The
  failures are metadata-only (no arrays). The rescore tool scored 23,833 rows with arrays; the remainder
  are no-array/failed records. This is why the plan's archive-wide refusal figure is ~16%, while the
  core_law run is an outlier at 43%.
- **CPU-lane dataset (`dataset_cpu/`):** **237 records: 221 ok, 16 failed** — 14 `invalid_geometry`,
  2 `solve_failed`. The D.3 dry run selects **all 237** (`beat_cpu` only), so the 16 failure labels would
  be merged into `dataset/shard-lane-cpu.jsonl`; they carry no arrays and the default training export
  excludes them, but the dataset's `n_failed` grows. Decide whether that is desired (see §5).
- **D.3 dry run** already PASSES on the reconstructed A.7 pair (5/5 <=0.2 dB; max 0.0356 dB). It is
  owner-gated and must wait until the GPU queue stops writing `dataset/`.
- **The g2 core_law job is CMA-ME too** (same config); the B.6 resample flag does not apply.

---

## 4. Options, ranked — and the over-constraint guardrail

| Option | Does the refusal disappear from the optimizer? | Box change | Cost / risk | Status |
|---|---|---|---|---|
| **B.6 `resample` + B.4 `valid` + `max_attempts`** (plain CMA only) | **Yes** — never told; replaced by a fresh ask | none | rejection/truncated sampling bias near the feasible boundary; up to 10 extra asks; all-refusing box still tells the last penalty | **implemented + tested** (`test_search_resample.py`) |
| **B.4 `valid` alone** | No — still told as the penalty | none | only budget accounting changes | implemented |
| **B.8 CMA-MAE (`search.qd.maes`)** for QD | Archive-level only: `threshold_min` can reject penalty rows; emitter bounds removed | none | still told to the emitter; new `learning_rate`/`j_threshold` knobs; needs a 3-seed A/B | implemented, opt-in |
| **CMA-ME custom scheduler/tell filter/resample** | Potentially yes | none | ribs `Scheduler.tell` contract; new code; needs a test that the batch accounting stays exact | **not implemented** |
| **Repair/projection to a feasible neighbour** | The refused design becomes a different, evaluated design | none (repairs inside the box) | changes the candidate; needs a deterministic repair map + provenance; risks boundary bias | proposal |
| **Pre-mesh feasibility predicate / `is_feasible`** (pycma `ask_and_eval`) | Resamples before evaluation; similar to B.6 | none | wrong predicate hides real information; resample budget; the dossier recommends this with a cap | proposal; B.6 is the manual version |
| **Graded envelope penalty** | No — still a penalty, but with slope | none | only `invalid_envelope`; the 434 are flat 1000 | implemented; core_law has it but those kinds are flat |
| **Narrow/pin the box** | Fewer refusals, but changes the search space | **yes** | **over-constrains**; can lose the good horns; do not use as a refusal fix | available as `narrow` for data-driven walls only |
| **`fmin_con2` / augmented Lagrangian** | Constraint-aware, but changes the fitness values | none | breaks stored-J comparability; dossier parks it | not implemented |

**Guardrail:** the owner's instinct is right — do not shrink the box just to lower the refusal rate. The
dossier's Q1 recommendation is: keep the penalty bedrock (never `inf`), add a cheap pre-mesh feasibility
predicate + resampling with a cap, use the graded envelope penalty where the overshoot is continuous, and
widen physical walls rather than narrow the box. The box-wide search is the asset; refusals are a budget
and sampling problem, not a reason to fence the horn in.

---

## 5. Dataset hygiene — the previous "not in data" claim is only half true

- Failures **are** in `dataset/` metadata: `ok=false`, `error`, no arrays. `build_record` does this on
  purpose (`record.py:297-317`). They are **not** in the acoustic arrays, and
  `to_training_arrays(ok_only=True)` excludes them by default (`store.py:502-522`). They are useful as
  invalid-region labels for a surrogate; keep that option open.
- The **D.3 merge tool selects every `beat_cpu` row**; `plan_merge` at
  `tools/data/merge_lane_dataset.py:133-160` has **no `ok` filter**. The CPU lane has 16 failure records;
  they would be merged as metadata. If the owner wants a clean-only dataset, add an `ok` filter (or a
  separate failure shard/tag) before `--apply`; if failure labels are wanted, keep them and say so in the
  manifest. This is a decision for the next agent/owner, not a silent behavior.
- The **failure markers** (`evaluate.py:1036-1041`) stop repeated re-fails for the same
  design/mesh/solve and are invalidated by `lib_shas`/`brief_hash` changes. That is the current
  "don't waste time on the same refusal twice" mechanism.
- The GPU queue is still writing `dataset/`; **do not run D.3 apply** until it is idle.

---

## 6. Suggested offline verification (no GPU, no solves, no queue changes)

1. **Replay the B.4/B.6 tests** (they already prove the contracts): `pytest tests/test_search_budget_counts.py tests/test_search_resample.py -q`.
2. **Replay one archived plain-CMA run** with `budget_counts: valid` + `infeasible_penalty: resample` using
   the stored ndjson history as the fitness source, and compare: refusal share, flat-penalty generation
   share, best J at equal **valid** budget, and the extra asks spent. (The trajectory diverges once the
   policy changes; an offline replay is an approximation, not a proof. State that.)
3. **CMA-ME/CMA-MAE:** run a 3-seed budget-matched A/B on one atlas config; compare archive coverage,
   QD score, penalty cells in `archive.json`, and the `resampled at least` warning; the CMA-MAE
   `j_threshold` should reject penalty rows. This needs GPU/next night; keep it as a proposal.
4. **Verify the D.3 selection** with the dry run and count `ok` vs failed before any apply.
5. **Do not change defaults.** Every option is opt-in; the goldens/config hashes must stay identical.

---

## 7. Senior-review questions for the next agent

1. For each config family, should the next search be plain CMA (where resample is available) or CMA-ME
   (where it is not)? The atlas configs are QD by design; the simple refusal drop is a plain-CMA feature.
2. Is rejection/resampling bias acceptable at the observed refusal rates (16% archive, 43% core_law), or
   is repair/graded-penalty better for the boundary-heavy knobs (`morph_fixed`, `tmax`)?
3. Should `dataset_cpu` failures merge as labels or be filtered? Is the main dataset's 4,634 failure
   metadata wanted for a surrogate/constraint learner?
4. What is the acceptance test for "refusals don't influence the trajectory"? Suggested: every told
   candidate is valid; best J from a valid row; refusal share and attempts in `run.json`; no penalty
   cells in `archive.json` for QD; equal-valid-budget comparison vs the control.
5. Does the owner want a **wide-box control** alongside any narrowing/widening experiment? (Recommended:
   yes; the 2026-10-23 rule: A beats B only when medians differ by more than both spreads; >=5 seeds.)

---

## 8. Do-not-do

- Do not edit the live checkout, `runs/`, `cache*/`, `dataset*/`, the queues, or PR #25.
- Do not run GPU/solves/Julia/selftest from an analysis agent.
- Do not add `resample` to a `cma_me` config (ConfigError).
- Do not narrow the box to reduce refusals; use walls/narrow only for data-driven walls, with a control.
- Do not apply D.3 while the GPU queue writes `dataset/`; owner sign-off required.
- Do not claim failures are absent from the dataset: they are metadata labels with no arrays, excluded
  from training by default.

---

**Handoff prepared by the orchestrator, 2026-11-12. The owner asked for this to be passed to an
independent reviewer/implementer; the reviewer may verify every line with `git show origin/main:<path>`
and the run dirs, and should make its own decisions.**
