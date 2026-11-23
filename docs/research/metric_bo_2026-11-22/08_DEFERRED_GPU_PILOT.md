# Deferred matched BEM pilot plan (Pass 2 prepares; does not launch)

- **Date:** 2026-11-22
- **Status:** PREPARED ONLY — `NOT EXECUTED - REQUIRES OWNER AUTHORIZATION`
- **Applies to:** `feat/metric-aware-bo` after real-data validation (doc 07) and a separate owner
  authorization for new solves

## 1. Question the pilot must answer

Does the metric-composite proposal policy produce **independently verified acoustic improvement per
total compute time** versus continued CMA-ES and versus the existing scalar BO / scalar TuRBO arms,
on the same physical task?

Predicted J, acquisition score, or model fit quality are **not** the success metric. A lower
predicted J is a hypothesis, not a result.

## 2. Arms (all matched)

| Arm | Optimizer | Notes |
|---|---|---|
| A | Continued CMA-ES | the incumbent; same seed population and sigma policy as the historical run |
| B | Existing scalar BoTorch or scalar TuRBO | unchanged production policy (`scalar` or `turbo`) |
| C | Metric-composite BoTorch or composite TuRBO | `metric_composite_v1` over the frozen training artifact; adaptation layer per doc 02 |

Matched for every arm:

- same physical task, brief and objective version (v10 or v11, never pooled);
- same active parameter keys, order, bounds, transforms and fixed values (the bounds identity hash
  must be identical across arms);
- same backend, fidelity, frequency grid, mesh identity and solver/dependency pins;
- same immutable code identity (commit SHA + `EXECUTION_CODE_FILES` pins);
- same screening budget and the same verification policy (4 finalists + 2 audits);
- same historical-information policy: a declared, frozen cohort; later arms may not see solves from
  earlier arms;
- same prospective budget, declared before launch.

## 3. Preliminary size (owner decision, not assumed)

- 25–30 new screening solves per arm, multiple seeds (at least 2 per arm).
- Common-fidelity verification solves for each arm's finalists, using the existing verification
  policy; verification calls are budgeted separately and are not counted as screening progress.
- No arm may exceed its declared budget because another arm "looks promising".

## 4. Operational constraints

- **One GPU solve at a time, machine-wide.** `HORNLAB_GPU_LOCK=refuse` for every unattended job.
  Parallel agents never authorize a concurrent BEM solve.
- `gpu-clean` and VRAM baseline (`nvidia-smi --query-gpu=memory.used`) before the first solve; record
  baseline + peak with the shared-memory spill check.
- Queue jobs through the existing night-queue machinery; do not modify an existing queue to add an
  arm. Each arm is its own queue file with its own controller state.
- No verification solve is launched before its arm's screen budget closes.
- CPU GP work for arm C runs in the isolated Bayesian interpreter and is recorded separately from GPU
  wall time; total compute time includes both.

## 5. Evidence required

1. Frozen arm manifests: task, brief hash, objective version, bounds identity hash, active keys,
   backend, fidelity, grid hash, code pins, seeds, budget.
2. Per-arm screen trace: candidate identity, proposal index, predicted J / acquisition (arm C only),
   measured J, status, timestamps.
3. Verification result per finalist, including actual H/V directivity and LF loading — not only the
   scalar J.
4. Total compute ledger: GPU solve seconds, verification seconds, CPU model seconds, per arm.
5. Selection-disagreement table: which candidates each arm proposed, and what the others would have
   proposed at the same state where reconstructible.
6. Numerical failures and refusals, verbatim.

## 6. Analysis

- Primary: independently verified acoustic improvement (H/V directivity + LF loading + the canonical
  J of the verified finalist) per total compute second, arm C vs A and C vs B.
- Secondary: best verified J, time-to-best, failure fraction, verification pass rate.
- Report uncertainty honestly: with 25–30 screens per arm and 2 seeds, a difference smaller than the
  observed seed variance is not a result.
- Record an explicit `INSUFFICIENT_EVIDENCE` outcome if the arms cannot be separated.

## 7. Promotion rule

Arm C is promoted to a default-eligible policy only if:

1. real-data validation (doc 07) shows composite candidate ranking is at least not worse than scalar
   on held-out cohorts, with recorded limitations;
2. the matched pilot shows a verified acoustic benefit per compute time that survives seed variance;
3. the owner records the promotion decision and updates `PROPOSAL_POLICIES`,
   `PRODUCTION_POLICIES`, labels and GUI text in one append-only commit;
4. the existing scalar/TuRBO/Pareto defaults remain unchanged unless separately decided.

Until then the policy stays opt-in and real execution stays refused by
`metric_execution_gate` / the absence of `metric_composite_v1` from `PRODUCTION_POLICIES`.

## 8. Explicit non-goals for Pass 2

- No GPU job, no BEM solve, no verification solve, no campaign, no queue change.
- No claim of acoustic improvement.
- No automatic CMA-to-BO switching; the advisory in doc 05 is read-only.
