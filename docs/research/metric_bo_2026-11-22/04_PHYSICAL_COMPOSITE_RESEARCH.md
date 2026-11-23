# 04 — Physical-metric composite (research only)

- **Date:** 2026-11-22
- **Lane:** LANE C writer, branch `feat/metric-aware-bo`
- **Module:** `hornlab_search/bo/physical_composite.py`
- **Tests:** `tests/test_bo_physical_composite.py`
- **Status:** research instrument only. It is **not** a production proposal policy and is **not**
  registered in `hornlab_search.bo.policy.PROPOSAL_POLICIES`.

## 1. Why this is research-only

The production composite policy (`metric_composite_v1`) fits one GP per **canonical scoring
component** in J contribution units. This module explores a different, physical-unit view: one GP
per CD physical output produced by `hornlab_search.metrics.cd`. The two views answer different
questions, and the physical view is not a substitute for the canonical scorer.

Every result carries:

```
research_only = True
policy        = "physical_composite_research_v1"
```

A test asserts that `"physical_composite_research_v1"` is not in `PROPOSAL_POLICIES` and that the
policy name is absent from the registered policy vocabulary.

## 2. Metric contract

Only fields actually produced by `metrics/cd.py::cd_metrics` are used. No metric is invented and
no missing value is filled.

| `metric_key` | v11 term | units | source | frequency support | missing policy |
|---|---|---|---|---|---|
| `cd_lw_db` | `cd_lw` (M2) | dB | either (balloon preferred; cuts fallback flagged) | 700–8000 Hz | refuse |
| `cd_di_std_db` | `cd_di_std` (M4) | dB | either (depends on `metrics.di_db`) | 700–8000 Hz | refuse |
| `cd_nacc` | `cd_nacc` (M5) | ratio 0..1 | cuts | 700–8000 Hz | refuse |
| `offaxis_smooth_db` | `offaxis_smooth` | dB | cuts | 2500–8000 Hz | refuse |

Each `PhysicalMetricSpec` is frozen and exposes `identity_hash = sha256(canonical_json(spec))`.
The module-level schema hash covers objective version 11 plus the four definitions in order.

`cd_omega_2pi` and `cd_status_code` are **not** contributions here: they are report-only in v11
and are not modelling targets. In a `cd_metrics` payload, `cd_status` is used only to decide
whether the row is usable.

### Future candidates, deliberately not implemented

`h_coverage_deg`, `v_coverage_deg` and `loading_re_z` are recorded in
`FUTURE_METRIC_CANDIDATES` but are **not** produced by `metrics/cd.py`. Adding them would mix a
different measurement contract into a CD physical model, so this pass does not do it.

## 3. Contribution extraction

`extract_physical_contributions(cd_raw, *, params, objective_version=11)` accepts the exact dict
returned by `cd_metrics` and a validated `V11Params`. Weights and tolerances come from the
canonical resolver and the validated parameter block, never from constants in this module:

```text
w = resolve_v11_weights(weights, params)
cd_lw_j          = w["cd_lw"]          * _norm_cd(cd_lw_db,     objective.cd.lw.tolerance_db)
cd_di_std_j      = w["cd_di_std"]      * _norm_cd(cd_di_std_db, objective.cd.di_std.tolerance_db)
cd_nacc_j        = w["cd_nacc"]        * _norm_nacc(cd_nacc,    objective.cd.nacc.tolerance)
offaxis_smooth_j = w["offaxis_smooth"] * _norm_cd(offaxis_smooth_db,
                                                  objective.cd.offaxis.tolerance_db)
```

`_norm_cd` and `_norm_nacc` are imported from `objective/scalar_v11.py`, so the arithmetic is the
scorer's own normalisation. The result records contributions by term, physical metric values,
weights, tolerances, `cd_status`, flags and the schema hash.

### Refusals (never fills)

- non-11 objective version;
- missing `V11Params`;
- unknown/missing `cd_status`, or `cd_status == "unmeasurable"`;
- `cd_status == "cuts_fallback"` unless `allow_cd_cuts_fallback=True` (allowed is flagged);
- any missing metric key, non-numeric or non-finite value;
- `cd_nacc` outside the physical ratio interval `[0, 1]` (1e-9 numerical slack);
- non-finite canonical contribution.

A refused row has `status="unavailable"` and no fabricated contribution values.

### Formula parity evidence

`tests/test_bo_physical_composite.py` builds a tiny synthetic v11 response, calls the canonical
`objective_v11` scorer and `metrics.cd.cd_metrics` on the same objects, and asserts:

1. the four extracted contributions equal `w[k] * terms[k]` from the canonical term row
   (`rtol=0`, `atol=1e-12`);
2. they also equal the hand formula in physical units
   (`w * raw / tolerance`; for NACC `w * (1 - nacc) / tolerance`);
3. their sum is less than the canonical `J`, confirming that CD terms alone are not the full score.

## 4. Reconstruction contract

`reconstruct_physical_j(...)` accepts canonical term-key contributions in J units. A full J is
returned (`status="ok"`, `partial=False`) **only** when:

- a validated `params` object supplies the required active term set, and
- every active base term **and** all four CD terms are present and finite.

Otherwise the result is `status="partial"`, `partial=True`, `j=None`, and `missing_terms` names
exactly what is absent. `j_partial_sum` is a diagnostic only. CD terms alone therefore cannot claim
a full physical-score reconstruction.

A test supplies all base contributions from the synthetic canonical term row plus the extracted CD
contributions and recovers the canonical `J` within `1e-12`; dropping one base term returns
`partial=True` again.

## 5. Research GP and nonlinear transforms

`fit_physical_model(X, Y_phys, ...)` fits one independent GP per physical output in **physical
units**, reusing the `bo.metric_model` patterns (Matérn-5/2 ARD, per-output standardisation,
fixed noise floor, constant outputs parked flat). It validates shapes, finiteness and the `[0,1]`
input box, and returns a tagged result. The model is a `ModelListGP`; no policy registration path
exists.

`evaluate_physical_transform(model_result, X, transform, ...)` draws posterior **samples** and
returns:

- `sampled_mean` = mean of the per-sample transform;
- `sampled_sd` = standard deviation of the per-sample transform;
- `transform_of_mean` = transform of the posterior mean (diagnostic only);
- `nonlinear_gap` = `sampled_mean - transform_of_mean`.

A test uses a quadratic transform and asserts that the two evaluations differ, so the
mean-of-transform vs transform-of-mean case is exercised rather than assumed.

## 6. Explicit limitations

- **No calibrated uncertainty claim.** The GP intervals are model diagnostics. Tests report
  empirical interval coverage only, explicitly labelled not calibrated.
- **No acoustic improvement claim.** Outputs are predictions from synthetic or canonical
  contribution rows, not solved acoustic results. No BEM/GPU/mesh/solver call is made here.
- **Independent outputs.** The model does not represent correlation between physical metrics.
- **No production wiring.** Nothing here is registered in `bo.policy`, used by a study, or used
  to change a queue or optimizer default.
- **v11 only.** The module refuses other objective versions. v11 CD metrics are not universal
  requirements; a non-CD brief must not be forced through this module.
- **Cuts fallback is refused by default.** It is a degraded measurement path and must be an
  explicit, flagged opt-in.

## 7. Validation

Command (bayes venv, worktree on `PYTHONPATH`):

```powershell
$env:PYTHONPATH="C:/Users/hunte/Hrns/hornfab-metric-bo-wt"
& "C:/Users/hunte/Hrns/oc-wt/bo-study/bayes-venv/Scripts/python.exe" `
  -m pytest tests/test_bo_physical_composite.py -q -p no:cacheprovider
```

See the lane handoff for the final pass/fail count. The tests use synthetic fixtures only; no real
data, dataset traversal, historical reopen or BEM solve.
