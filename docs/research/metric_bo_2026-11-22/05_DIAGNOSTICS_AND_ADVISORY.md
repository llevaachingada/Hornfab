# 05 — Diagnostics and optimizer advisory (research only)

- **Date:** 2026-11-22
- **Lane:** LANE C writer, branch `feat/metric-aware-bo`
- **Modules:** `hornlab_search/bo/metric_diagnostics.py`,
  `tools/analysis/optimizer_switch.py`
- **Tests:** `tests/test_bo_metric_diagnostics.py`,
  `tests/test_optimizer_switch_metric_advisory.py`,
  plus the existing `tests/test_tools_analysis_optimizer_switch.py`
- **Status:** synthetic diagnostics + advisory reporting only. No optimizer is switched, no queue
  is changed and no production policy is modified.

## 1. Synthetic model comparison

`run_synthetic_model_comparison(...)` fits four default arms to **identical** synthetic train/test
data and the same seed, plus an optional fifth arm:

| arm | components | meaning |
|---|---:|---|
| `A_scalar` | 1 | one GP on scalar `J` |
| `B_two_component` | 2 | two-component composite |
| `C_v10_four` | 4 | four-component v10-shaped composite |
| `D_v11_six` | 6 | six-component v11-shaped composite |
| `E_correlated_lmc_v1` (optional) | 6 | one correlated LMC multitask GP over all outputs |

Arm E is **research-only and optional**: `OPTIONAL_ARM_STATUS = "implemented_research_only"` and
`include_optional=False` by default. It is never required for acceptance. When enabled, it fits one
BoTorch 0.18.1 `MultiTaskGP` in the documented stacked-task form
(`train_X = [[x_i, task_t], ...]`, `task_feature = d`, `rank = min(m, 2)`), rather than one
independent `SingleTaskGP` per output. A failed optional fit (capability missing, API mismatch,
numerical failure) is recorded as `E_correlated_lmc_v1: unavailable` with
`numerical_failures=1`; it never crashes the comparison.

The default independent GP construction reuses the `bo.metric_model` helpers (`_import_engine`,
`_fit_one_output`, per-output standardisation, fixed noise floor, `ModelListGP`,
`predict_metric_components`). The synthetic arms do not build a `metric-training-v1` artifact
because arm A (one scalar output) and arm B (two outputs) are not frozen component schemas.

### Landscapes

All landscapes are fixed synthetic functions. They are **not tuned to make a composite arm win**:

- approximately additive;
- correlated outputs;
- independent outputs;
- constant contribution;
- multiple basins;
- strong local concentration;
- different length scales;
- different contribution magnitudes.

Each landscape supplies five explicit non-negative parts. Each arm's component matrix is built so
its rows sum exactly to the same true `J`; the scalar arm sees `J` directly, the two-component arm
sees `(part 0, remainder)`, and so on.

### Metrics

Pure functions, tested on known arrays:

- MAE and RMSE;
- Spearman rank correlation (average-rank tie handling);
- top-decile recall (lower `J` is better);
- empirical interval coverage at `z = 1.96`;
- prediction bias;
- fit time, posterior/acquisition-time proxy, total CPU overhead;
- candidate-selection disagreement versus the scalar arm;
- numerical failures.

Coverage is **empirical coverage of model intervals and is explicitly not calibrated**. It is not a
confidence guarantee.

### Actual outcome (recorded, not tuned)

Run: `n_train=48`, `n_test=20`, `d=3`, `seed=7`, `max_iters=40`, all eight landscapes,
`include_optional=False` (A–D), total wall time ≈ 15.1 s on CPU.

| arm | MAE | RMSE | Spearman | top-decile recall | coverage (not calibrated) | bias | fit+acq time (s) | failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A_scalar | 0.0596 | 0.0766 | 0.774 | 0.75 | 0.9625 | +0.00785 | 3.41 | 0 |
| B_two_component | 0.0273 | 0.0374 | 0.959 | 0.81 | 0.9813 | +0.00177 | 2.36 | 0 |
| C_v10_four | 0.0122 | 0.0157 | 0.990 | 1.00 | 1.0000 | -0.00069 | 4.00 | 0 |
| D_v11_six | 0.0109 | 0.0139 | 0.991 | 1.00 | 1.0000 | -0.00162 | 5.34 | 0 |

Optional arm E on the approximately-additive landscape alone (`n_train=48`, `n_test=20`, `d=3`,
`seed=7`, `max_iters=40`): MAE 0.000464, RMSE 0.000782, Spearman 1.000, top-decile recall 1.00,
coverage 1.000, bias +0.0000822, fit+acq 0.292 s, 0 numerical failures, marker `LMC`.

The composite arms won this synthetic comparison. **That is not evidence that a composite arm is
superior on real acoustic data.** These landscapes are largely additive by construction, which is
the regime where decomposing a sum helps; the comparison also costs roughly 1–2 extra GP fits for
the four/six-component arms. A scalar win would have been reported just as plainly. The optional LMC
arm models correlation between outputs but **does not validate that correlation on real data**.

## 2. Optimizer advisory

`tools/analysis/optimizer_switch.py` was extended **append-only**:

- every existing key and recommendation string is unchanged;
- a new `switch` block is added to each per-run report (JSON and Markdown);
- `analyse_run(path, *, model_diagnostics=None, historical_validation=None)` accepts optional
  diagnostic inputs but behaves exactly as before when they are omitted;
- the CLI gains optional `--model-diagnostics <json>` and `--historical-validation <status>`.

### Structured switch block

```text
recommendation ∈ {CONTINUE_CMA, TRY_SCALAR_BO, TRY_TURBO, TRY_METRIC_COMPOSITE,
                  REVIEW_BOUNDS, INSUFFICIENT_DATA, MODEL_UNAVAILABLE}
reasons                : list[str]
inputs                 : compatible_completed_solves, compatible_designs, active_dimension,
                         cohort_coverage, cma_stagnation, incumbent_concentration,
                         bounds_saturation, model_diagnostic_quality,
                         historical_validation_status, expected_overhead, thresholds
advisory_only          : true
executes_search        : false
changes_queue          : false
metric_composite       : {status, research_only, validation, never_proven_superior, ...}
```

Decision order is deliberately conservative:

1. too few compatible completed solves → `INSUFFICIENT_DATA`;
2. a supplied model diagnostic is unusable → `MODEL_UNAVAILABLE`;
3. recent failure/refusal fraction above threshold → `CONTINUE_CMA` (investigate failures);
4. bounds saturation above threshold → `REVIEW_BOUNDS` (never auto-widen);
5. CMA stagnation → `TRY_METRIC_COMPOSITE` only when a usable model diagnostic exists, otherwise
   `TRY_SCALAR_BO` / `TRY_TURBO` / `CONTINUE_CMA` depending on cohort size and dimension;
6. otherwise → `CONTINUE_CMA`.

### Metric-composite labelling

The switch never reports metric-composite as proven. Its default label is
`validation_required`; even a supplied `validated` status is downgraded to
`validation_required` in this advisory, and `never_proven_superior` is always `true`. The reason
text says explicitly that it is research-only, has not been shown superior, and must not be
presented as proven.

### Advisory only

The tool does not execute a search, change a queue, edit a config, or switch a production policy.
Tests build synthetic run directories in `tmp_path` and assert the advisory flags, the structured
inputs, the research-only labelling, the bounds-review priority and unchanged existing keys.

## 3. Explicit limitations

- **No calibrated uncertainty claim.** Coverage numbers are empirical model-interval coverage on
  synthetic data and are labelled not calibrated.
- **No acoustic improvement claim.** Every number above is synthetic; no BEM/GPU/mesh/solver call
  was made.
- The optional LMC arm models correlation between outputs but does not validate that correlation
  on real data; arm E is research-only and excluded by default.
- The comparison does not test real data.
- The advisory switch consumes raw run metadata; it is not a statistical comparison and does not
  establish that any optimizer is better.
- Metric-composite remains research-only and validation-required regardless of the switch output.

## 4. Validation

```powershell
$env:PYTHONPATH="C:/Users/hunte/Hrns/hornfab-metric-bo-wt"
$py = "C:/Users/hunte/Hrns/oc-wt/bo-study/bayes-venv/Scripts/python.exe"
& $py -m pytest tests/test_bo_metric_diagnostics.py -q -p no:cacheprovider
& $py -m pytest tests/test_optimizer_switch_metric_advisory.py `
    tests/test_tools_analysis_optimizer_switch.py -q -p no:cacheprovider
```

See the lane handoff for the final pass/fail counts. All fixtures are synthetic and run in
`tmp_path`; no real data or historical corpus is touched.
