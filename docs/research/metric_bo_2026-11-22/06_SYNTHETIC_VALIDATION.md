# 06 — Pass 2 synthetic validation record

- **Date:** 2026-11-22
- **Branch / worktree:** `feat/metric-aware-bo` at `C:/Users/hunte/Hrns/hornfab-metric-bo-wt`
- **Interpreter:** `C:/Users/hunte/Hrns/oc-wt/bo-study/bayes-venv/Scripts/python.exe`
  (Python 3.12.10, numpy 2.5.4, torch 2.14.1+cpu, botorch 0.18.1, gpytorch 1.15.2,
  linear_operator 0.6.1, pytest 9.2.0)
- **Status:** synthetic only. No real dataset, no run archive, no BEM/GPU/mesh/solver, no queue.
  Every number below is a model or test number, **not** an acoustic measurement.

## 1. Parent regression suite (actual run)

Command (worktree root, thread caps per `AGENTS.md`, four workers, junit written outside the repo):

```powershell
$env:PYTHONPATH="C:/Users/hunte/Hrns/hornfab-metric-bo-wt"
$env:OMP_NUM_THREADS="1"; $env:OPENBLAS_NUM_THREADS="1"; $env:MKL_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"; $env:VECLIB_MAXIMUM_THREADS="1"
& "C:/Users/hunte/Hrns/oc-wt/bo-study/bayes-venv/Scripts/python.exe" -m pytest `
  tests/test_bo_acquisition.py tests/test_bo_cohort_gate.py tests/test_bo_data.py `
  tests/test_bo_data_p2.py tests/test_bo_diagnostics.py tests/test_bo_encoding.py `
  tests/test_bo_extensions.py tests/test_bo_metric_acquisition_sign.py `
  tests/test_bo_metric_artifact.py tests/test_bo_metric_constraints.py `
  tests/test_bo_metric_diagnostics.py tests/test_bo_metric_identity.py `
  tests/test_bo_metric_model.py tests/test_bo_metric_propose.py `
  tests/test_bo_metric_training.py tests/test_bo_metrics.py tests/test_bo_metrics_adapter.py `
  tests/test_bo_metrics_v10.py tests/test_bo_model.py tests/test_bo_native_policy_gate.py `
  tests/test_bo_pareto.py tests/test_bo_pareto_production.py tests/test_bo_physical_composite.py `
  tests/test_bo_pipeline.py tests/test_bo_policy.py tests/test_bo_policy_metric.py `
  tests/test_bo_prepare_study_cli.py tests/test_bo_proposal_validation.py `
  tests/test_bo_propose.py tests/test_bo_turbo.py tests/test_study_builders.py `
  tests/test_study_production.py tests/test_study_adaptive_real.py tests/test_study_api_m3.py `
  tests/test_study_cohort_fallback_safety.py tests/test_study_cohort_intake.py `
  tests/test_study_cohort_metric_selection.py tests/test_study_duplicate_execution.py `
  tests/test_study_evaluator.py tests/test_study_gui_instrumentation.py `
  tests/test_study_gui_production.py tests/test_study_launch_durable.py `
  tests/test_study_package_gate.py tests/test_studies_b5_integration.py `
  tests/test_studies_b5_runner.py tests/test_studies_budget_profiles.py `
  tests/test_studies_cli_b2.py tests/test_studies_metric.py `
  tests/test_studies_metric_recovery.py tests/test_studies_package_b2.py `
  tests/test_studies_registry_b1.py tests/test_b8_study_integration.py `
  tests/test_tools_analysis_cohorts.py tests/test_tools_analysis_optimizer_switch.py `
  tests/test_optimizer_switch_metric_advisory.py tests/test_metrics_cd.py `
  tests/test_objective_v10.py tests/test_objective_v11.py tests/test_objective_v9.py `
  tests/test_gui_studies_module.py tests/test_gui_study_adapters.py tests/test_gui_study_queue.py `
  -q -o addopts="" -p no:cacheprovider -n 4 --dist loadscope `
  --junitxml="C:/Users/hunte/AppData/Local/Temp/opencode/pass2_junit.xml"
```

Actual result:

```
583 passed, 3 skipped, 131 warnings in 88.61s (0:01:28)
```

The three skips are the pre-existing missing native archive fixtures in `tests/test_bo_data.py`
(`native scores/catalog/dataset artifacts are not present in this checkout`). No test was skipped,
weakened or given a looser tolerance in this pass.

Lane-scoped runs also executed by the parent:

| Slice | Result |
|---|---|
| Lane B: metric training/model/propose + cohort + new identity/artifact/fallback tests | 74 passed |
| Lane C: physical composite + constraints + diagnostics + advisory + existing switch test | 33 passed |
| Lane A: policy/study/recovery + acquisition sign | 31 passed |
| Lane A regression: policy + builders + production + pareto production | 60 passed |

Warnings are the expected BoTorch/GPyTorch `NumericalWarning`, `GPInputWarning` and
`torch.jit.script` deprecation notices; there were no collection errors and no numerical failures
reported as passes.

## 2. Parent evidence run (real CPU multi-output GP fit)

Script: `C:/Users/hunte/AppData/Local/Temp/opencode/pass2_evidence.py` (outside the repository).
It uses the real Pass-1 selector/artifact builder, the real byte serializer, the real policy
capability/proposal path, a real `StudyService` registry in a temp directory, the real
`ProductionJournal`, and a pure-Python synthetic evaluator. Exact output:

```
[artifact]
n=18 d=3 m=4 version=metric-training-v1
components=['load_j', 'coverage_j', 'ripple_j', 'other_j']
checksum=02efd6679f8e5f7f7c32887fe3ff326466fbe6cde40715688469ba47ae605032
bytes_sha256=3e9e0050456cefaad4add2d5a093a4d7606bd677bd2f878460def5e5249fca88
byte_identical_serialization=True bytes=7097
roundtrip_status=ok validation_status=ok reason=ok
bounds_hash=22c3d1efdc12c39cba3b4093faff584017fd5b37cf807c2314ef32a94245386c
score_identity=48542f6bdfc84166fc612d0b3ec9445faabbad58348c555fe2268e9d44594552
[policy capability]
status=ok reason=ok bounds_hash=22c3d1efdc12c39cba3b4093faff584017fd5b37cf807c2314ef32a94245386c m=4 n=18
[policy fit_and_propose]
status=ok reason=ok candidate=c4
predicted_j=0.8428035572253674 total_sd=0.5096119664778258
component_means=[0.8428035572253674, 0.0, 0.0, 0.0] component_sds=[0.5091851703831174, 0.012039084119543844, 0.012039084119543844, 0.012039084119543844]
acquisition=-4.623198611920531 units=qLogNEI (technical ranking only, not J and not a probability)
fallback=False verification_mode=scalar
fit_s=2.167579700006172 model_hash=069cc06b079bfe6394a64f10ed46d46304a9c8c34304169044309af2539a4515
  output=load_j constant=False fit_method=exact_mll noise_original=1e-05 lengthscales=[0.005000004378620075, 0.028765651924295803, 0.5056710916425631]
  output=coverage_j constant=True fit_method=constant_parked noise_original=1e-05 lengthscales=[0.9999999999999999, 0.9999999999999999, 0.9999999999999999]
  output=ripple_j constant=True fit_method=constant_parked noise_original=1e-05 lengthscales=[0.9999999999999999, 0.9999999999999999, 0.9999999999999999]
  output=other_j constant=True fit_method=constant_parked noise_original=1e-05 lengthscales=[0.9999999999999999, 0.9999999999999999, 0.9999999999999999]
[study builders]
kinds=['metric_training', 'metric_training_manifest', 'model', 'pool', 'proposal', 'package']
training_status=ok model_status=ok pool_status=ok proposal_status=ok
model_hash=069cc06b079bfe6394a64f10ed46d46304a9c8c34304169044309af2539a4515 proposal_candidate=c4
package_id=4040cd4361d7325c21a2dcfdf3549d8106f72eaeaf29e07dd4cf7cfd28c9ab1c policy=metric_composite_v1 metric_synthetic=True
metric_bindings_status=ok reason=ok bounds_hash=22c3d1efdc12c39cba3b4093faff584017fd5b37cf807c2314ef32a94245386c
real_solver_gate=refused/metric_composite_real_execution_not_authorized real_solver_allowed=False
[synthetic adaptive study]
status=pool_exhausted screen_calls=3 attempts=3 observations=3
model_hash=069cc06b079bfe6394a64f10ed46d46304a9c8c34304169044309af2539a4515 artifact_checksum=02efd6679f8e5f7f7c32887fe3ff326466fbe6cde40715688469ba47ae605032
  index=0 solve=solve-4 j=0.5166666666666666 synthetic=True real_solver_calls=0
  index=1 solve=solve-5 j=0.48333333333333334 synthetic=True real_solver_calls=0
  index=2 solve=solve-3 j=0.55 synthetic=True real_solver_calls=0
[resume with same package]
status=pool_exhausted screen_calls=3 attempts=3 observations=3
```

Interpretation, with the limits stated:

1. **Deterministic model reconstruction.** The policy path and the study-model path produced the
   same `model_hash` from the same frozen artifact and seed. The durable model artifact is a
   manifest, not a pickled model.
2. **Constant outputs are parked, not fitted.** The synthetic data has one varying component and
   three zero-variance components; the fit reports `constant_parked` for the latter. This is the
   documented behaviour, not a hidden failure.
3. **Prediction ≠ measurement.** The proposal's predicted J for `c4` was `0.8428`, while the
   synthetic evaluator returned `0.5167`. That gap is a legitimate illustration that the GP is a
   proposal model and must never be read as a measured J.
4. **Acquisition is not J.** The recorded acquisition is `-4.623` in qLogNEI units, explicitly
   labelled technical ranking only.
5. **Recovery.** Re-running the same package evaluated nothing twice (`screen_calls=3`,
   `attempts=3`, three observations before and after).
6. **Real execution is impossible.** The gate refused even with `allow_real_solver=True`.

## 3. What this does not establish

- No predictive accuracy on real horns; no real-data fit was performed.
- No improvement over CMA-ES, scalar BO, or TuRBO.
- No calibrated uncertainty: interval coverage is reported only as empirical coverage in the
  diagnostics module, explicitly not calibrated.
- No acoustic improvement and no new BEM solve.
- Bitwise reproducibility across different Torch/BLAS platforms is not claimed. Reproducibility is
  from the same interpreter, seed, frozen arrays and recorded dependency versions.

## 4. Reproduce

Everything above is reproducible from the branch with the isolated interpreter. The parent evidence
script lives outside the repository (temp path) so no generated study data is committed; the
equivalent assertions are in `tests/test_studies_metric.py`,
`tests/test_studies_metric_recovery.py`, `tests/test_bo_policy_metric.py`,
`tests/test_bo_metric_artifact.py`, `tests/test_bo_metric_identity.py`,
`tests/test_study_cohort_fallback_safety.py`, `tests/test_bo_physical_composite.py`,
`tests/test_bo_metric_constraints.py`, `tests/test_bo_metric_diagnostics.py`,
`tests/test_bo_metric_acquisition_sign.py` and `tests/test_optimizer_switch_metric_advisory.py`.
