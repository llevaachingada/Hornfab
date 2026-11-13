# Parent M0 freeze — draft (bo-study-v1.1)

Status: DRAFT pending the R0 brief-target rescore rerun and S0 native-only census. Parent commits
and version-bumps this file once those two reports land. B2 is treated as deliverable-complete.

## 1. Frozen candidate task

- Config `examples/typologies/campaign_2026-10-26_v4/native__ath_core_v4.yaml`, resolved through
  `examples/briefs/campaign_2026-10-26_v4/native_ath_core_2in_v4.yaml`.
- Objective **v4**; band 300–8000 Hz; 50°/50°; f0 1280 Hz; `cov_narrow_ratio 2.0`,
  `cov_below_f0 mask`, `diag_reference round`; weights cov 1, rip 1, di 0.3, dislope 0.5,
  flat 0.5, load 0.0, distd 0.5, diag 0.5; tolerances cov 2.0, rip 1.0, di 0.4, dislope 9.0,
  flat 1.5, load 0.3, distd 2.0, diag 2.0; 2.5–5.5 kHz freq weight ×2.
- **Cohort is native-only**: `config_name == native__ath_core_v4`. The four-config pool sharing
  the brief (atlas__ath_core, atlas__core_law, crease__core_law_v4, native__ath_core_v4) is
  descriptive only and must never be pooled for GP/advisory comparisons.
- Source caveat retained: 2-inch uniform piston, f11 ≈ 3957 Hz; above it results are geometry
  comparisons under that excitation. Loading weight is 0: no loading/efficiency/distortion claims.

## 2. Frozen three-identity rules

1. Physical identity = design/mesh/solve/excitation/dependency hashes + raw array digests
   (`replay._physical_identity`). Immutable.
2. Metric identity = physical id + metric code + target key + metric_source + di_source.
   Response-detrended ripple (`ripple_used_response true`) and available diag arrays are required
   for a v4 **complete** score; legacy stored ripple is `partial_unsupported`.
3. Score identity = metric id + objective version + weights + objective block + brief hash/name.
   A brief-supplied target **is** the scoring target; the stored record target is only the
   parity/target-change comparator. Parity is asserted only when target keys are identical.

## 3. Frozen encoding contract

- `hornlab_search/bo/encoding.py`, `hornlab_search/bo/data.py` (B2, offline-tested).
- `active-projection-v1`: drops only `morph_exponent` (inactive at `morph_target=1`, proven by
  source + 64-azimuth mouth-contour test; target 3 active). d = 13.
- Reconstruct the full alphabetical vector with `morph_exponent=4.0` before
  `space.denormalize`; fixed keys stay at the seed; no historical clipping.
- TrainingSet selection: n_min = max(16, 2*(d+1)); cap 256; 64 lowest-J + 192 deterministic
  maximin; stable IDs; no fake J=1000.
- Pool 4096: scrambled Sobol (recorded seed), cheap checks only, dedup by materialized geometry +
  intended solve identity + 1e-6 inf-norm; "cheap-check-passed, mesh/acoustic eligibility
  unknown."

## 4. Frozen metric policy (v4 raw)

- Build `V4Params` from the resolved brief object (never `V8Params.for_class("A")`; v8 stays
  unregistered).
- Ripple must use the response-detrended branch (`_used_resp true`); legacy fallback is a distinct
  partial metric, never pooled under one ripple label.
- Per-plane f0 masks come from the resolved Target (`f0_effective_hz`, `f0_v_hz`);
  cov mask = band ∧ f ≥ f0; diag uses the round reference 50°.

## 5. Cohort and eligibility (current evidence, to be finalized)

- Parent-observed native-only: **197 ok rows** (192 screen + 5 verify), 192 unique geometries,
  197 unique physical solves; run_id absent on all native rows → independent-experiment identity
  is `insufficient_evidence` unless recovered from run provenance explicitly.
- S0 four-config descriptive census: 3,185 records / 2,412 complete replayable rows.
- R0 replay pilot: 200 scored rows, 195 parity-compared, max |ΔJ| 0, zero backend calls; the
  five unpaired rows are stored-v3 records replayed under a v4 variant.
- **Pending R0 fix**: brief-target scoring (`2500–5500 ×2`) + native-only replay counts.
- **Pending S0**: native-only census section.

## 6. Advisory BoTorch dependency (frozen)

Isolated venv `C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv`:
`torch 2.14.1+cpu, botorch 0.18.1, gpytorch 1.15.2, linear_operator 0.6.1, numpy 2.5.4, scipy 1.18.1`.
Live venv unchanged; lazy import only; `model_unavailable` when absent.

## 7. M0 gate checklist

- [x] Parent critical assessment of both external reviews + legacy surrogate audit
- [x] B2 activity ledger + geometry fixtures + encoding/pool fixtures (tests offline green)
- [x] S0 catalog/cohorts mechanics (88 new tests green)
- [x] R0 replay/parity/preservation mechanics (zero backend calls)
- [ ] R0 brief-target rescore + native-only counts
- [ ] S0 native-only census
- [ ] Parent freeze signed; ATH eligibility statement recorded

## 8. M1 artifact schema v1 (parent-frozen)

Two immutable analysis artifacts under `scratch/bo_m0/m1/` (then `runs/analysis/`):

**`parameter_study.json`** (S4 owner):

```
{ "tool": "parameter_study", "schema_version": 1, "protocol": "bo-study-v1.1",
  "task_identity": {config, brief_name, brief_hash, objective_version: 4, resolved_target,
                    weights, tolerances, cov_narrow_ratio: 2.0},
  "cohort": {rows, unique_geometries, run_ids_missing: true, exclusions, generated_utc},
  "controls": [<B2 parameter_activity ledger entries>],
  "designs": [ {design_hash, params, geometry_descriptors, response_bands_hz, source_caveat_hz: 3957,
                score_terms: {raw, normalized, weighted, total}, identities: {physical_id, metric_id, score_id},
                provenance: {shard, row}, selection_reason} ],   # 3-5 actual selectable designs
  "evidence": {parity: {...}, heldout: {...}, support: "..."},
  "limitations": [ ... ] }
```

**`source_fidelity.json`** (S6 owner): per-design fidelity/source context � DI source,
balloon-vs-cuts, verify pairing status, physical size, missingness � read-only from runs.

S10 renders both through the existing `viewAnalysis` (`ANALYSIS_TOOL_JSONS` += the two tool names;
backend `analysis_report` already passes JSON verbatim; no DB, no jobs, no solve action).
