# Parent M0 freeze — SIGNED (bo-study-v1.1)

Status: **SIGNED 2026-11-13.** The R0 brief-target rescore/native-only replay and the S0 native-only
census landed; the parent re-read both artifacts and the M2 interface tests before signing. B2 is
deliverable-complete. This signature freezes the task/cohort/encoding/metric contract for offline
M2/M3 work; it does not authorize a real solve, a production default change, or an acoustic benefit
claim. Evidence paths are relative to `docs/evidence/bo_study_2026-11-12/`.

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

## 5. Cohort and eligibility (final evidence)

- Parent-observed native-only: **197 ok rows** (192 screen + 5 verify), 192 unique geometries,
  197 unique physical solves; run_id absent on all native rows → independent-experiment identity
  is `insufficient_evidence` unless recovered from run provenance explicitly. Source
  `s0/cohorts.json` (`ath_native_census`).
- S0 four-config descriptive census: 3,185 records / 2,412 complete replayable rows; native-only
  census status `eligible_with_provenance_gaps`, `independent_experiments:
  insufficient_evidence`. Source `s0/cohorts.json`.
- R0 replay final: **200 replayed / 197 parity-compared, max |ΔJ| = 0**, zero backend calls; the
  five unpaired rows are stored-v3 records replayed under a v4 variant and are labelled
  unpaired, not silently compared. Brief-target scoring (`2500–5500 Å⁻²`) is included in the
  replayed identity. Source `r0/offline_scores.json` (`parity.n_compared = 197`,
  `parity.max_abs_delta = 0.0`, `backend_guard.calls = 0`).
- M1 evidence (`s4/parameter_study.json`, `s6/source_fidelity.json`) was regenerated against the
  final R0 artifact: 200 replayed, 197 compared, five actual selectable designs, recommendation
  status suppressed because independent experiment groups are not established. This is an honest
  descriptive/insufficient-evidence outcome, not a failure of the replay machinery and not a
  reason to pool another brief.
- The native cohort remains **descriptive/advisory** for M2: 197 rows but fewer than the frozen
  independent-group eligibility policy. BoTorch proposals may be generated and tested; they are
  off-policy predictions, never closed-loop benefit evidence.

## 6. Advisory BoTorch dependency (frozen)

Isolated venv `C:\Users\hunte\Hrns\oc-wt\bo-study\bayes-venv`:
`torch 2.14.1+cpu, botorch 0.18.1, gpytorch 1.15.2, linear_operator 0.6.1, numpy 2.5.4, scipy 1.18.1`.
Live venv unchanged; lazy import only; `model_unavailable` when absent.

## 7. M0 gate checklist

- [x] Parent critical assessment of both external reviews + legacy surrogate audit
- [x] B2 activity ledger + geometry fixtures + encoding/pool fixtures (tests offline green)
- [x] S0 catalog/cohorts mechanics (88 new tests green)
- [x] R0 replay/parity/preservation mechanics (zero backend calls)
- [x] R0 brief-target rescore + native-only counts: `r0/offline_scores.json`, 200 replayed /
      197 compared / max |ΔJ| 0 / zero backend calls.
- [x] S0 native-only census: `s0/cohorts.json`, `eligible_with_provenance_gaps`;
      independent experiments `insufficient_evidence`.
- [x] Parent freeze signed; ATH eligibility statement recorded (section 9).

## 9. ATH eligibility statement (signed)

The candidate task **is eligible for offline advisory M2/M3 work** and **is not yet eligible for a
closed-loop optimization claim**:

- Eligible: `native__ath_core_v4` resolved through `native_ath_core_2in_v4` has 197 complete
  replayable native rows / 192 unique geometries / 197 unique physical solves with exact v4 replay
  parity and zero backend calls. That supports a real TrainingSet, pool, scalar fit and advisory
  proposals under the frozen encoding (d=13, `morph_exponent` projected at 4.0).
- Not eligible: the archive does not establish independent experiment groups (run identity is
  absent), so held-out/importance recommendations are suppressed and a closed-loop BO speed or
  acoustic-benefit claim is not supported. Five nominal verify rows are not five independent
  replicates.
- Still excluded: pooling the four-config descriptive census, the narrow `native__ath_core_v4_narrow`
  config, other briefs/objective versions/backends/fidelity specs, or treating the inline YAML
  target (500–5500 Hz) as the resolved brief (300–8000 Hz, f0 1280 Hz, narrow ratio 2).
- Context limits stay visible: 2-inch uniform-piston source with the f11≈3957 Hz caveat; loading
  weight 0; v8 remains unregistered; above the source marker these are geometry comparisons under
  that excitation, not driver-efficiency/SPL/distortion evidence.
- A real pilot still requires the separately scheduled budget/deadline/lane approval. This
  signature authorizes no solve, dataset/cache/queue/default change, or adoption decision.

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
