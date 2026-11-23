# Metric-composite study integration (Pass 2, lane A)

- **Date:** 2026-11-22
- **Branch:** `feat/metric-aware-bo`
- **Worktree:** `C:/Users/hunte/Hrns/hornfab-metric-bo-wt`
- **Depends on:** `ADR_metric_composite_v1.md` (Pass 1), `bo/metric_artifact.py` and
  `bo/metric_propose.py` identity hardening (lane B, landed), `bo/metric_identity.py` (parent).
- **Scope:** policy registration + study builder/service integration + synthetic-only execution
  boundary. No BEM/GPU/mesh/solver call, no historical replay, no real-data fit, no queue change,
  no score/objective edit, no default optimizer change.

## 1. Policy contract (`metric_composite_v1`)

Appended as the sixth policy after `turbo`:

```
PROPOSAL_POLICIES = ("scalar", "pareto", "cma_seed", "exploration", "turbo",
                     "metric_composite_v1")
PROPOSAL_POLICY_LABELS["metric_composite_v1"] =
    "metric-composite Bayesian (per-term contributions)"
ENGINE_POLICIES = {scalar, pareto, turbo, metric_composite_v1}
PRODUCTION_POLICIES = ("scalar", "turbo", "pareto")        # unchanged
```

- `verification_mode("metric_composite_v1") == "scalar"`. The composite utility is
  `-sum(components)`, so the decision quantity is still the scalar `J`; finalist selection follows
  the frozen scalar rule exactly.
- Opt-in only. No default selection, menu default, fallback or capability probe changes. The five
  earlier policies keep their order and semantics byte-for-byte; `PRODUCTION_POLICIES` is untouched.
- New refusal constants are appended; no existing constant was renamed:
  `metric_training_artifact_required`, `metric_training_artifact_invalid`,
  `metric_training_version_unsupported`, `metric_objective_version_unsupported`,
  `metric_component_schema_mismatch`, `metric_training_array_invalid`,
  `metric_bounds_identity_mismatch`, `metric_score_identity_mismatch`,
  `metric_task_identity_mismatch`, `metric_engine_unavailable`,
  `metric_artifact_module_unavailable`.

### `capability_status(..., metric_training=None)`

`metric_training` is a `MetricTrainingBinding` (or a mapping / bare artifact). It carries the
artifact plus the caller's frozen identities:

```
MetricTrainingBinding(
  artifact, encoding, expected_bounds_hash, expected_score, expected_task, component_schema)
```

`status == "ok"` only when **all** of the following hold:

1. a `metric-training-v1` artifact is present and Lane B's
   `validate_metric_training_artifact` accepts it (checksum/manifest, schema, arrays, component
   order, `J == sum(Y_components)` per row, X in `[0,1]`, finite values);
2. objective version is 10 or 11 and matches the artifact metadata;
3. component names/order and schema hash match the frozen v10/v11 schema;
4. the caller's live `ActiveProjection` recomputes to `expected_bounds_hash`, and the artifact's
   recorded bounds hash + payload agree (`check_bounds_identity`, `recompute_bounds_hash`);
5. the caller's score payload (`objective_version`, `brief_hash`, `score_hash`, score module)
   recomputes to the artifact's recorded `score_identity` (`check_score_identity`);
6. `task_identity`, `backend`, `fidelity`, `grid_hash`, `dependency_hash` equal the caller's frozen
   expected dict (`check_identity_fields`); missing identity fails closed;
7. the optional BoTorch/GPyTorch/Torch engine is importable;
8. a legal candidate pool with a finite unit-box vector is present.

A failure is a tagged refusal (`unavailable` / `capability_missing` / `pool_exhausted`) with a
metric-specific reason. It **never** falls through to the scalar arm. Same-dimension/different-box,
changed transform, changed active order, missing/wrong score identity, wrong component schema,
missing engine and missing pool are covered by tests.

### `fit_and_propose(..., metric_training=..., metric_policy=..., metric_history=...,
metric_evaluation=...)`

- Strict validation first (identical to `capability_status`); then `fit_metric_model(artifact,
  seed=seed)` and `propose_metric_candidate(..., require_identity=True,
  expected_bounds_hash=<recomputed>)`.
- The metric proposal policy is forced to carry the expected bounds hash; `require_identity=True`
  makes `bounds_hash == ""` impossible on an `ok` proposal.
- Mapping into `ProposalOutcome`:
  - `proposal` = candidate dict;
  - `predicted = {component_means, component_sds, j_mean, total_sd,
    note="model prediction, not a solved acoustic result"}`;
  - `acquisition = {value, units="qLogNEI (technical ranking only, not J and not a probability)",
    policy, acq_seed}`;
  - `model_hyperparameters` = per-output fit records + model hash.
- Every failure is tagged `unavailable`/`capability_missing`; no automatic fallback, no maximin
  substitution, no fabricated prediction. `metric_evaluation` is accepted for forward-compatible
  callers but a prebuilt acquisition is never trusted for validation: the proposal is rebuilt from
  the frozen artifact + pool.

## 2. Package contract (additive only)

`studies/package.py` gained one optional keyword, `metric=None`:

- When absent, the package body and identity are exactly the historical scalar/turbo/pareto body.
- When present, `body["metric"]` is part of the canonical body/hash. `verify_package` requires:
  - `metric.policy == "metric_composite_v1"`;
  - `metric.synthetic is True`;
  - `metric.real_solver_allowed is False`;
  - a non-empty `metric.training_artifact_sha256`.
- The metric block records: training artifact bytes sha + manifest sha + checksum, objective
  version, component schema hash, bounds hash, score identity, proposal/model shas, synthetic
  provenance and `no_backend_calls=True`.

`metric_execution_gate(package, *, allow_real_solver=False, synthetic_evaluator=None)`:

- `allow_real_solver=True` is **still refused** with
  `reason="metric_composite_real_execution_not_authorized"`; the parameter documents intent, never
  grants authority.
- Only an explicitly injected `synthetic_evaluator` yields `status="ok"`,
  `reason="synthetic_only"`, `real_solver_allowed=False`.
- The gate validates the package first and touches no mesh/solve/pipeline path.

## 3. Study integration (extends builders/service; no parallel store)

New `hornlab_search/studies/metric_study.py`; every artifact is published through
`StudyService.attach_artifact` with explicit content hashes and dependencies.

| Function | Attaches | Key fields |
|---|---|---|
| `build_metric_training` | `metric_training` (npz bytes via lane B `artifact_bytes`), `metric_training_manifest` (JSON) | schema/checksum, bounds/score/task pins, selected/excluded IDs, d/n/m, `no_backend_calls=True` |
| `build_metric_model` | `model` (`study-model-manifest-v1`) | policy, seed, artifact bytes sha + checksum, model hash, per-output hyperparameters, dependency versions, timing, `pickled_model=False`, `model_state_persisted=False` |
| `build_metric_pool` | `pool` (existing `study-pool-manifest-v1`) | full candidate vectors, metric policy, synthetic flag |
| `build_metric_proposal` | `proposal` (`study-proposal-v1`) | candidate, predicted components, acquisition record, identity pins, synthetic provenance, pinned checksums |
| `metric_bindings` | read-only | typed ok/refusal mirroring `pareto_bindings` |
| `prepare_metric_run_package` | `package` | reuses `prepare_run_package` + additive metric block |

- `build_metric_training` requires an explicit `SelectionResult` (or explicit records are refused).
  It validates component rows, objective version, bounds/score/task identities and never invents a
  selection or a component. Dependencies always include the frozen `snapshot`; scalar
  `training`/`training_manifest` are added only when declared via
  `spec["metric_selection_source"]`.
- `build_metric_model` reloads the training artifact through
  `artifact_from_bytes(expected_checksum=...)`, revalidates it with
  `validate_metric_training_artifact` against the manifest pins, then fits on CPU. No pickled
  object is written.
- `build_metric_proposal` validates the model manifest, re-fits from the frozen artifact with the
  recorded seed, and refuses if the recomputed `model_hash` differs. It then loads the pool
  artifact, proposes with `require_identity=True`, and publishes nothing on failure.
- `metric_bindings` re-reads the exact artifact bytes, revalidates checksum/schema/arrays/identities
  and compares the proposal's pinned checksums; a tampered binding is a typed refusal, never a
  repaired value.
- `prepare_metric_run_package` refuses unless `metric_bindings` is `ok`.

## 4. Synthetic-only execution boundary

- `MetricSyntheticEvaluator` implements the `studies/runner.py` protocol:
  `capability_status` is `ok` only for a synthetic evaluator; `next_candidate` proposes over the
  frozen pool with identity enforcement; `lookup` returns an already-journaled result with
  `call_status="not_called"` and consumes no reservation; `preflight` is cheap and deterministic;
  `evaluate` calls **only** the injected synthetic function; `observe` appends component-labelled
  observations and refits under the frozen seed/policy; `restore_progress` /
  `proposal_rng_state` round-trip through `encode_proposal_history` / `decode_proposal_history`.
- `FrozenLaneAdapter` satisfies `lane_contract="b5-owned-lane-v1"` but owns no cache/dataset
  roots, starts no host and mutates no environment.
- `run_synthetic_metric_study` orchestrates snapshot -> training -> model -> pool -> proposal ->
  package -> journal run -> simulate -> persist synthetic summary -> observe/refit -> next
  proposal, and resumes from the durable journal when called again.
- The durable journal is the real `ProductionJournal` over a temp `StudyService`. Tests prove:
  unknown attempts block resume; a staged pending proposal is evaluated, never silently
  re-selected; rerunning after a limit stop evaluates nothing twice; a resumed study makes the
  same next proposal/model hash as an uninterrupted run; and monkeypatched solver/mesh/pipeline
  sentinels are never reached.

## 5. Tests and evidence

Interpreter:

```
$env:PYTHONPATH="C:/Users/hunte/Hrns/hornfab-metric-bo-wt"
& "C:/Users/hunte/Hrns/oc-wt/bo-study/bayes-venv/Scripts/python.exe" -m pytest <files> -q
```

| File | Result |
|---|---|
| `tests/test_bo_policy_metric.py` | 16 passed |
| `tests/test_bo_metric_acquisition_sign.py` | 4 passed |
| `tests/test_studies_metric.py` | 6 passed |
| `tests/test_studies_metric_recovery.py` | 5 passed |
| `tests/test_bo_policy.py` (append-only tuple/labels/mode updates) | 26 passed |
| `tests/test_study_builders.py` + `tests/test_study_production.py` + `tests/test_bo_pareto_production.py` | 34 passed |

Commands and measured results (2026-11-22, bayes venv):

```
# new lane-A tests
31 passed, 41 warnings in 16.62s

# existing policy/builder/production regression slice
60 passed, 7 warnings in 22.30s
```

The acquisition-sign evidence is exact: `composite_utility(samples) == -samples.sum(dim=-1)`
(bit-equal), the real CPU BoTorch qLogNEI argmax is the selected candidate, the reported
acquisition score is not the predicted `J`, and a candidate with the lower predicted `J` loses the
acquisition to a higher-uncertainty candidate.

## 6. Limitations / explicit non-goals

- `metric_composite_v1` is not in `PRODUCTION_POLICIES`; real execution stays impossible.
- Synthetic-only. No historical rescoring/replay, no real-data fit, no BEM/GPU solve.
- `build_metric_training` consumes an explicit caller selection; deriving a real metric cohort
  from stored dataset records is a later pass (and would need real component extraction plumbing).
- Independent-output GPs do not model inter-component correlation (inherited Pass-1 limitation).
- The synthetic summary artifact is `results` with explicit provenance; it is not a measured
  acoustic result and must never be consumed as one.
