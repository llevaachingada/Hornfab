# Deferred real-data validation plan (Pass 2 prepares; does not execute)

- **Date:** 2026-11-22
- **Status:** PREPARED ONLY — `NOT EXECUTED - REQUIRES OWNER AUTHORIZATION`
- **Applies to:** `feat/metric-aware-bo` after Pass 2
- **Binding rule:** none of the commands below may run in Pass 2. Pass 2 performed no historical
  rescore, no replay, no real-data GP fit and no full-archive traversal.

## 0. Why this is a separate phase

Pass 2 proves the study integration on synthetic packages: artifact build/serialize/reload, policy
capability, study construction, adaptive proposal/update, recovery, diagnostics and constrained-BO
research. None of that establishes predictive accuracy on actual horn solves, and the GP is still a
**proposal model** — the canonical `objective/scalar_v10.py` / `scalar_v11.py` remain the only
authority for measured acoustic quality. A real-data pass needs its own authorization because it
reopens stored acoustic responses and can create misleading-looking evidence if identity pins are
wrong.

## 1. Preconditions (all must be true before any command)

1. Owner authorization for a bounded real-data phase, naming the exact dataset root and run IDs.
2. `git status --porcelain` clean in the execution checkout, or an explicit decision that uncommitted
   work is out of scope; record HEAD.
3. The canonical checkout stays on its own branch; real-data work uses a dedicated worktree/checkout
   per the owner's current rule.
4. The isolated Bayesian interpreter is recorded with its dependency versions
   (`C:/Users/hunte/Hrns/oc-wt/bo-study/bayes-venv/Scripts/python.exe`; Pass 2 measured
   torch 2.14.1+cpu, botorch 0.18.1, gpytorch 1.15.2, linear_operator 0.6.1, numpy 2.5.4,
   Python 3.12.10).
5. GPU lock free and `HORNLAB_GPU_LOCK=refuse` even though this plan is CPU-only: no BEM job may be
   admitted beside the traversal by accident.
6. A written cohort scope: dataset root, objective version, brief hash, score identity, run IDs and
   a hard record cap. `study_cohort`'s `limit` is a **training-selection cap**, never a
   raw-discovery cap.

## 2. Step 1 — census (counts only, bounded)

Purpose: confirm how many observations are actually compatible before reading any response array.
Do not rank, do not replay, do not write a training artifact yet.

```powershell
# NOT EXECUTED - REQUIRES OWNER AUTHORIZATION
# Bounded to explicit run IDs; prints catalog counts only.
& $py tools/analysis/catalog.py --dataset <DECLARED_DATASET_ROOT> --out <BOUNDED_OUT_DIR> `
    --run-id <RUN_ID_1> [--run-id <RUN_ID_2> ...]
```

Accept only if the catalog reports: one objective version, one brief hash, one score identity, one
task identity, one backend, one fidelity, one grid hash, one dependency hash, one mesh hash. Any
mixed identity means the scope is wrong — stop, do not "clean" it by pooling.

Deliverable: `census.json` + counts pasted into evidence. **No cohort rows are replayed in this
step.**

## 3. Step 2 — bounded cohort preparation (canonical replay of selected rows only)

```powershell
# NOT EXECUTED - REQUIRES OWNER AUTHORIZATION
& $py tools/analysis/study_cohort.py `
    --config <FROZEN_BRIEF_CONFIG> `
    --dataset <DECLARED_DATASET_ROOT> `
    --out <BOUNDED_COHORT_DIR> `
    --limit 256 `
    --run-id <RUN_ID_1> [--run-id <RUN_ID_2> ...]
```

Expected after Pass 2 hardening:

- v10/v11 groups are encoded through the frozen `ActiveProjection` with `verify_round_trip=True`;
- stored J is used for pre-replay ranking **only** when the catalog score identity and brief hash are
  established and match the frozen config; otherwise the record is excluded with
  `score_identity_unavailable`;
- if no candidate is encodable, the command returns a typed refusal
  (`metric_selection_unavailable`) with `n_records_considered` and per-record reasons, and replays
  nothing. Any broader replay requires `allow_unranked_replay=True` **and** owner authorization, and
  is labelled `replay_authorized` in the output;
- only the selected rows are replayed; `selected_ids` / `excluded_ids` / reasons are retained.

Stop conditions: any `bounds_identity_mismatch`, `active_parameter_order_mismatch`,
`score_identity_mismatch`, `component_parity` exclusion rate above the pre-declared ceiling, or a
refusal. Do not lower the ceiling after seeing the result.

## 4. Step 3 — component parity against stored scored terms

For each selected row, build the v10/v11 component vector from the **stored canonical term row**
(the scorer's own terms, not a recomputation from raw curves) and require
`J == sum(components)` within `PARITY_ABS_TOL/PARITY_REL_TOL` (`1e-12` serialization tolerance).
This is the check that the GP training label is the same J the scorer produced.

Pass 2 already performs this inside `build_metric_training_artifact` and again on artifact reload
(`validate_metric_training_artifact`). The real-data step only needs to run it on real rows and
record the per-row `parity_abs` distribution and the maximum absolute delta.

Refuse the whole cohort if any row needs a residual to balance, any row is a penalty/failure row, or
any v11 CD term is `unmeasurable`; `cuts_fallback` rows are excluded unless the frozen policy sets
`allow_cd_cuts_fallback=True` and they are never pooled with balloon rows.

## 5. Step 4 — immutable training artifact

```python
# NOT EXECUTED - REQUIRES OWNER AUTHORIZATION
# Python API, not a shell command. The study builder attaches the artifact and its manifest.
from hornlab_search.studies.service import StudyService
from hornlab_search.studies import metric_study

service = StudyService("<STUDY_ROOT>")
metric_study.build_metric_training(
    service, "<STUDY_ID>", root="<STUDY_ROOT>",
    selection=<SELECTION_RESULT>,
    identity_metadata={
        "objective_version": <10|11>,
        "brief_hash": "<FROZEN_BRIEF_HASH>",
        "score_hash": "<FROZEN_SCORE_IDENTITY>",
        "encoding": <FROZEN_ACTIVEPROJECTION>,
        "task_identity": "<FROZEN_TASK_IDENTITY>",
        "backend": "<FROZEN_BACKEND>",
        "fidelity": "screen",
        "grid_hash": "<FROZEN_GRID_HASH>",
        "dependency_hash": "<FROZEN_DEPENDENCY_HASH>",
        "mesh_hash": "<FROZEN_MESH_HASH>",
    },
    idempotency_key="metric-training:<COHORT_HASH>",
)
```

The artifact must reload byte-identically through `metric_artifact.artifact_from_bytes` and pass
`validate_metric_training_artifact` (arrays, IDs, schema hash, J reconstruction, bounds/score/task
identity, policy compatibility). Record the artifact checksum.

## 6. Step 5 — real CPU GP fits (CPU float64 only)

Fit A scalar, B two-component, C v10 four-component, D v11 six-component (E correlated optional,
not required) on the **same** frozen artifact and same seeds.

Record per arm: n, d, m, fit time, acquisition time, total CPU overhead, finite-posterior status,
per-output hyperparameters, and library versions. Do not switch the optimizer, do not queue a solve,
do not promote a policy from these numbers.

## 7. Step 6 — evaluation

1. Whole-run holdout and chronological holdout (later observations as test) — never random-only.
2. MAE, RMSE, Spearman rank correlation, top-decile recall, prediction bias.
3. Uncertainty coverage: report empirical coverage of model intervals and label it
   **not calibrated** unless a calibration study is separately authorized.
4. Candidate-ranking quality: compare the arm's top-k proposals against the observed J ranking of
   the same held-out candidates.
5. Selection disagreement between scalar and composite arms.
6. Numerical failures and warnings, verbatim.

A scalar-GP win is a legitimate finding and must be recorded as such. Do not tune the synthetic or
real split to force a composite win.

## 8. Step 7 — decision output

Only after 1–7: a written recommendation in
`docs/research/metric_bo_2026-11-22/` with the exact identities, counts, holdout design, metrics,
limitations and a proposed next authorization. Promotion of `metric_composite_v1` into
`PRODUCTION_POLICIES` (real execution) is a **separate owner decision** after this validation; Pass 2
deliberately leaves it out so no study can dispatch a real solve under the new policy.

## 9. Explicit non-goals

- No historical bulk rescoring.
- No re-ranking of historical top designs.
- No change to v10/v11 definitions, weights, tolerances or stored J.
- No implied acoustic improvement claim from model metrics.
