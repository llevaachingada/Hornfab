# ADR — metric-composite Bayesian optimization (Pass 1)

- **Date:** 2026-11-22
- **Status:** Accepted for Pass 1; production study integration deferred to Pass 2.
- **Branch:** `feat/metric-aware-bo`
- **Base:** `a30f2de9a5898d51b1c2e48b0513297db6e7584e` (`hornfab-all-2026-11-18`)
- **Worktree:** `C:/Users/hunte/Hrns/hornfab-metric-bo-wt`
- **Owner authorization:** one dedicated worktree, exception to the 2026-11-12 consolidated-checkout
  amendment. The canonical checkout is not modified.

## 1. Problem and decision

The existing Bayesian engine models one scalar `Y = -J` with `scalar_pool_v1`. That answers “what
will `J` be?” but not “which scoring term is the proposal trading away?”. Pass 1 adds a
**composite scalar** engine:

1. Fit one independent GP per *scoring contribution* (component) measured in canonical `J` units.
2. Form posterior **samples** of the component vector.
3. Evaluate the existing scalar objective as a deterministic function of those samples:
   `utility(samples) = -sum(samples over the component dimension)` because lower `J` is better.
4. Propose the candidate maximizing a Monte-Carlo acquisition (`qLogNoisyExpectedImprovement`).

This is **not** Pareto optimization. There is no Pareto front, no dominance filtering, and no
per-component acceptance target. The single scalar `J` identity remains the decision quantity.

The GP is a **proposal model only**. It never produces an authoritative measured `J`; the canonical
scorers remain the only authority for measured acoustic quality:

- `hornlab_search/objective/scalar_v10.py`
- `hornlab_search/objective/scalar_v11.py`

No scoring formula is duplicated, rewritten, or re-tuned. No historical rescore, replay, BEM solve,
queue change, optimizer default, or score-version change is part of Pass 1.

## 2. Frozen identities

| Identity | Value |
|---|---|
| Training artifact | `metric-training-v1` |
| Model + acquisition policy | `metric_composite_v1` |
| v10 component schema | `v10-metric-components-v1` |
| v11 component schema | `v11-metric-components-v1` |
| Encoding | existing `active-projection-v1` / `ActiveProjection`; exact `space.keys()` order |
| Scalar authority | canonical `objective_v10` / `objective_v11` term rows |
| Backend / fidelity | one exact identity per artifact; screen and verify never pool |
| Objective versions | one version per artifact; v10 and v11 never pool |

Component names and order are frozen:

- v10: `load_j`, `coverage_j`, `ripple_j`, `other_j`
- v11: `load_j`, `other_base_j`, `cd_lw_j`, `cd_di_std_j`, `cd_nacc_j`, `offaxis_smooth_j`

Each schema has an explicit SHA-256 over canonical JSON (component order, source term mapping,
objective version, report-only keys). The artifact records the schema hash; a mismatch is a
refusal, never a silent remap.

## 3. Contribution extraction

Inputs are the **canonical scorer’s own term row**, the resolved weights, and the validated
params object. Contributions are always in `J` contribution units; they are not assumed to be dB,
degrees, or ratios.

### v10

`w = resolve_v10_weights(weights, params)`, `active = params.weighted_keys()`.

```
load_j     = w["load"]       * terms["load"]
coverage_j = w["cov_profile"]* terms["cov_profile"]
ripple_j   = w["rip"]        * terms["rip"]
other_j    = sum(w[k] * terms[k] for k in active
                 if k not in {"load", "cov_profile", "rip"})
```

`other_j` includes every active optional term (`hf_floor`, `constancy`) and `flat`, `dislope`,
`di_roughness`, `flat_cv`. `J_reconstructed = load_j + coverage_j + ripple_j + other_j`.
`ripple_region` semantics are preserved by using the canonical v10 term row; the extractor never
recomputes ripple.

### v11

`w = resolve_v11_weights(weights, params)`. The four CD weights come only from `objective.cd`.

```
load_j       = w["load"] * t["load"]
other_base_j = sum over every active v10/v9 weighted key except "load"
cd_lw_j      = w["cd_lw"] * t["cd_lw"]
cd_di_std_j  = w["cd_di_std"] * t["cd_di_std"]
cd_nacc_j    = w["cd_nacc"] * t["cd_nacc"]
offaxis_j    = w["offaxis_smooth"] * t["offaxis_smooth"]
```

`cd_omega_2pi` and `cd_status_code` are report-only and are not contributions. The extractor mirrors
the scorer’s base-term re-normalisation (`(t * tol) / tol`) before multiplying by the weight, so the
reconstruction follows the scorer’s arithmetic rather than a residual.

### Parity and refusals

- `J_reconstructed` must equal canonical `terms["total"]` within a declared floating-point
  tolerance (`abs <= 1e-12 + 1e-12 * max(1, |J|)`); the observed absolute delta is recorded.
- No component is computed as “J minus the others”. A parity failure is a tagged refusal.
- Refuse penalty/failure rows (`terms["penalty"] > 0`), non-finite terms, missing keys, and a term
  equal to the scorer’s documented `NAN_TERM_FILL` sentinel (whole-term unmeasurable).
- v11 CD status: `balloon` is valid; `cuts_fallback` requires an explicit
  `allow_cd_cuts_fallback=True` policy and is flagged; `unmeasurable` is refused. A cuts-fallback
  row is never silently mixed with balloon rows.
- v10 `di_estimated` (cuts-estimate DI) is refused by default and only allowed with an explicit
  `allow_cuts_estimate_di=True` policy; the flag is retained either way.
- Partial in-band NaNs that do not make a whole term unmeasurable are retained and flagged with
  `n_nan`; the canonical `J` already accounts for them.

## 4. Cohort selection (data contract)

The prior defect — positional `selected[:limit]` before downstream selection in
`tools/analysis/study_cohort.py` (and the equivalent raw-row truncation in
`bo.data.build_native_training_set`) — is corrected. **`n_max = 256` is a training-selection cap,
never a raw-data discovery cap.**

Required order:

1. Identify all completed compatible observations in the selected cohort group.
2. Enforce exact compatibility identities (objective version, brief/score hash, task identity,
   backend, fidelity, frequency grid, dependency/mesh identity, active keys, bounds hash).
3. Deduplicate physical observations and cached results; conflicting duplicates are incompatible.
4. Validate parameter encoding through `ActiveProjection`; no clipping and no invented vectors.
5. Rank/select over the **whole compatible corpus**: `64` lowest-`J` elites plus deterministic
   maximin diversity up to `256`. Ties by observation ID.
6. Record selected and excluded IDs with reasons.
7. Emit an immutable artifact with a manifest checksum.

The selector is metadata-first and bounded-memory: it consumes metadata plus encoded `X`/`J`, then
the caller replays only the selected rows. A synthetic cohort with >256 rows and a best observation
at index 299 must include that observation in the selected set.

Failure policy: no fabricated `J`, no synthetic failure penalty treated as measured acoustic data.
Failed solves, penalty rows, missing scores, wrong versions/backends/grids/fidelities, invalid or
out-of-bounds parameters, and changed bounds are excluded with typed reasons.

## 5. Training artifact (`metric-training-v1`)

Deterministic, immutable payload:

```
X              float64[n, d]     active unit vectors
J              float64[n, 1]     canonical scalar J
Y_components   float64[n, m]     contribution units, schema order
Y_phys, G      optional, separately identified
metadata:
  objective_version, brief_hash, score_hash, component schema + hash
  physical_task, source_identity, family/generator, screen/verify fidelity
  active_keys, feature_names, bounds, transforms, bounds_hash
  backend, frequency/grid identity, mesh/solver/dependency identity
  observation_ids, design/solve hashes, selected_ids, excluded_ids + reasons
  selection policy + hash, manifest checksum
```

Validation: shapes, float64, finiteness, `X` in `[0,1]`, unique IDs, schema/order match, and
`J == sum(Y_components)` within the declared tolerance. Arrays are read-only after construction.
The checksum covers canonical metadata plus per-array SHA-256 values.

## 6. Model policy (`metric_composite_v1`)

- Independent-output multi-output GP: one `SingleTaskGP` per component, wrapped in `ModelListGP`
  (supported by BoTorch 0.18.1). Independent outputs do **not** model inter-component correlation;
  this limitation is explicit. `ModelListGP` also permits genuinely different observation sets.
- Matérn-5/2 ARD, `ScaleKernel`, `ConstantMean`, CPU `float64`, deterministic seeds, two Torch
  threads maximum.
- Per-output standardisation for non-constant outputs. Fixed observation noise
  `max(1e-6 * sample_variance, 1e-5)` in original output units.
- Constant/zero-variance outputs: no standardisation, near-zero-slope GP with a fixed small noise;
  the posterior is flat and contributes no directional acquisition signal. This is documented, not
  hidden.
- Every fit checks finite hyperparameters and a finite latent posterior. Any failure returns a
  tagged `unavailable` result naming the failed output; no zero or mean-filled predictions.

## 7. Acquisition and proposal policy

```
utility(samples) = -sum(samples, dim=-1)          # lower J is better
acquisition      = qLogNoisyExpectedImprovement
objective        = GenericMCObjective(utility)
sampler          = SobolQMCNormalSampler(sample_shape=[128], seed=acq_seed)
X_baseline       = observed training X
prune_baseline   = False
q                = 1 (serial proposal mode)
```

The acquisition is evaluated from posterior **samples**, never from the posterior mean of `J`.
Candidates come from the existing legal finite candidate pools (`build_candidate_pool`) or any
caller-supplied pool already restricted to a TuRBO local box. Pending candidates are excluded;
known/excluded identities and near-duplicates of training/pending/accepted vectors are rejected.
Ties are broken by candidate ID.

Every proposal records: candidate ID, model/data hashes, acquisition policy + seed, acquisition
score, predicted `J` (sum of component means), component means, component posterior SDs, total
posterior SD (`sqrt(sum(var))`, independence assumption), fit time, acquisition time, bounds
identity, and proposal seed. These are predictions, not solved acoustic results.

Model or acquisition failure returns a tagged `unavailable` status with a reason code. There is no
silent fallback to another policy and no fabricated prediction.

## 8. Pass 1 boundaries

Implemented and tested with synthetic fixtures only:

- cohort selection correction + contribution extractors
- `metric-training-v1` artifact
- multi-output GP fit on synthetic CPU data
- composite qLogNEI acquisition and q=1 proposal

Explicitly out of scope for Pass 1:

- real historical rescoring/replay/fits; full-dataset `study_cohort`
- production study-worker wiring or policy registration
- physical-metric research model
- BEM/GPU work, queue changes, v10/v11 behavior changes, optimizer defaults
- merging into `main` or touching the canonical checkout

## 9. Pass 2 interface

Pass 2 consumes:

1. `select_metric_training_observations(...) -> SelectionResult`
2. `build_metric_training_artifact(...) -> MetricTrainingArtifact`
3. `fit_metric_model(artifact, seed=...) -> MetricModelFitResult`
4. `build_metric_acquisition(model_result, ...) -> MetricAcquisitionResult`
5. `propose_metric_candidate(model_result, candidate_pool, ...) -> MetricProposalResult`

No Pass 2 caller is added in this pass. The artifact and result dataclasses are the contract.

## 10. Pass 2 integration decisions (2026-11-22)

Pass 2 did not change the scientific decision in §1–§7. It added the frozen study boundary:

1. **Identity authority.** `bo/metric_identity.py` owns the bounds and score identity contracts.
   The bounds payload records the projection version, ordered active keys, per-key physical
   `lo`/`hi`, log flag, transform kind and fixed values; the score payload records objective
   version, brief hash, catalog score identity and score module. A caller-declared hash is accepted
   only when it equals a recomputed hash and every other frozen source agrees. Missing or
   inconsistent identity is a typed refusal.
2. **Artifact format.** `bo/metric_artifact.py` freezes `metric-training-npz-v1`: deterministic
   ZIP_STORED NPZ (fixed order, fixed timestamps), canonical-JSON manifest, per-array sha256,
   no pickle, `allow_pickle=False` on read. Reload revalidates arrays, IDs, component order/schema,
   per-row `J == sum(components)`, bounds/score payloads and task identities.
3. **Policy.** `metric_composite_v1` is appended to `PROPOSAL_POLICIES` and `ENGINE_POLICIES`; it
   is not the default and not in `PRODUCTION_POLICIES`. The capability and dispatch branches
   require the strict binding and never fall back to scalar, maximin or a fabricated proposal.
4. **Study integration.** `studies/metric_study.py` extends the existing builders/service with
   `metric_training` + `metric_training_manifest` + a model manifest (deterministic reconstruction,
   no pickled model) + the existing pool + a `proposal` artifact + an additive synthetic `package`
   block. `metric_bindings` re-reads and revalidates stored bytes.
5. **Execution boundary.** `metric_execution_gate` refuses real solver execution even with
   `allow_real_solver=True`; only an injected synthetic evaluator is accepted. The synthetic
   evaluator implements the existing `studies/runner.py` protocol over the real durable journal, so
   recovery/idempotency is the established mechanism, not a parallel one.
6. **Research-only modules.** `physical_composite.py` (canonical v11 CD arithmetic, partial-J
   honesty), `metric_constraints.py` (signed `g(x) <= 0` hard-feasibility qLogNEI) and
   `metric_diagnostics.py` (synthetic arm comparison) are not registrable policies. The optimizer
   advisory is read-only and never switches a running optimizer.
7. **Scientific limits remain.** Synthetic evidence only; no real-data fit, no calibrated
   uncertainty, no acoustic improvement claim. Real-data validation and the matched BEM pilot are
   prepared in docs 07/08 and require separate owner authorization.

See docs 02–09 in this directory for the contracts, validation record, deferred plans and
implementation status.
