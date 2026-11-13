# Constrained-QD emitter: proposed contract (not implemented)

Status: **PROPOSED, parent-review only.** 2026-11-13. This document satisfies F1's requirement to
return an explicit constrained-QD design instead of silently claiming feasible-only learning. No
code in this document is active. v1 QD retains the disclosed
`legacy_finite_penalty_for_qd_v1` policy for deterministic geometry/resource refusals; archive
admission/rank correction is separate and already landed (`cma-me-archive-v2`).

## Why v1 is not feasible-only

`ribs` 0.12.0's `Scheduler.tell` binds one result slice per emitted solution and passes the full
batch to `EvolutionStrategyEmitter.tell`. `GridArchive` threshold learning is a MAP-elite
admission rule, not an ES constraint. Filtering rows, replacing public arrays after `ask`,
re-asking, or fabricating NaN/Infinity descriptors is not a supported equivalent and is forbidden.
A thin filter/wrapper is therefore **not assumed sufficient**; a true constrained emitter needs
either:

1. a supported public API in the pinned `ribs` that accepts per-solution feasibility/ranking
   metadata and excludes infeasible rows from the ES update; or
2. a separately reviewed pinned fork/new emitter class that implements the contract below.

## Proposed contract (for approval before code)

### Policy identity and scope

- Opt-in config key (proposed, not implemented): `search.qd.constrained_emitter: v1`.
- Only **deterministic geometry / brief-envelope / resource-cap refusals** are constrained out.
  Measured acoustic-gate failures remain the declared objective/constraint score when complete
  and measured; missing gate inputs remain `metric_error`/unknown, never a Boolean Gaussian.
- Infrastructure (`solve_failed`/metric/unknown) is handled by the already-landed
  `error_policy: retry_same_then_stop` before `tell`; it never becomes a feasibility observation.
- Wide configured bounds are unchanged. No hidden narrowing, no new acoustic cutoffs.

### Asked/evaluated/archive mapping

- Preserve emitted order, count, exact unit vectors and vector→materialized geometry→design hash
  mapping for every asked row.
- Archive admission: non-complete/refused rows are not stored in either the search or result
  archive and receive no improvement value; emitted rows remain in the batch at their original
  positions (the landed `FailureExcludingGridArchive` + failure-last ranker behavior).
- If a supported API cannot express the exclusion, the adapter must return
  `capability_missing`/unsupported; no private-state mutation, row dropping, or fake descriptors.

### ES update / parent weighting

- The ES mean/covariance update must exclude refused rows from parent selection and recombination,
  not merely rank them last. The adapter must define, in public API terms:
  - number of parents (`mu`) and how feasible ranks map to parents;
  - whether the archive improvement value or a declared constrained ranker drives selection;
  - handling of a partially feasible batch (no tell if the batch is incomplete/contaminated);
  - the exact behavior when every row is refused (no ES update; resumable stop).
- A custom ranker alone is not enough; the update path must be explicitly supported by the library
  or the pinned fork. The adapter must not claim trajectory-neutrality: correction can change
  invalid admission and ranks.

### Restart, replay and caps

- Full scheduler/emitter/ES/external RNG state or a verified deterministic replay must be
  checkpointed under a pinned protocol/spec/code identity.
- Ask a batch only after unresolved attempts are reconciled. A dispatched row with no durable
  result is unknown and stops the run before any new `ask`.
- Cumulative screen/attempts/backend-call caps persist across resumes; an explicit extension is
  recorded, a shrink is refused. Prefetch work is counted, cancelled/drained and never told after
  a stop.
- Restart rules (if any) must be declared and tested; a restart is not a new independent replicate.

### Verification and adoption gate

Required before adoption (offline fakes; no real BEM in the design pass):

1. valid/invalid seed, empty/nonempty search and result archives;
2. mixed/all-refusing batch, final-slot cap, partial last slot, cached refusals;
3. feasible parent weights vs the legacy emitter at matched total cost;
4. restart/replay/resume and cumulative-cap tests;
5. archive/result-archive exclusion and emitted order/count/hash round-trip;
6. a declared wide-box baseline comparison of verified quality per total wall/BEM cost;
7. an explicit statement of any changed admission/rank behavior (not trajectory-neutral).

No default change, production queue edit, or adoption follows from this document. A new optimizer
family or multi-fidelity policy needs its own parent-frozen protocol.

## Current status

- Archive/result-archive failure exclusion + failure-last ranker: **implemented**.
- Infrastructure isolation/retry before tell and durable reconciliation: **implemented**.
- Deterministic refusal policy: **legacy finite penalty, disclosed**; no feasible-only claim.
- Constrained-emitter adapter: **not implemented; this contract is the review gate.**
