# M2 gate — real data, frozen native-only cohort (bo-study-v1.1)

Generated 2026-11-13 (~22Z) by a local offline session. No solve, mesh, GPU, queue, cache or dataset write;
`runs/` and `dataset/` were read only and every file read is SHA-256 listed in
`gate/m2_gate_diagnostics.json` (`input_sha256`).

## Verdict: `insufficient_evidence`

| Part of the gate | Result |
|---|---|
| Optional dependency isolation (BoTorch only in bayes-venv, lazy import) | pass |
| Cohort identity (frozen 197 rows) | pass, re-verified against a fresh read-only catalog |
| No path bypasses the strict gate | **failed as found, fixed in `bo/data.py`** (see 3) |
| Subset / noise 0.1-1-10 / two pool seeds | pass: re-run in bayes-venv, bit-identical to the committed M2 artifact |
| Holdout / group integrity | **insufficient_evidence**: the frozen cohort is ONE connected experiment |
| Simple / CMA comparison | partial: real 1-group holdout and CMA seed spread; BO benefit unmeasured |
| Immutable proposal | pass (`m2/proposal.json`, reproduced through the study CLI in S10 QA) |

The interfaces now pass. The **validation** half of the gate cannot pass on this archive: the protocol needs at
least five independent connected groups for group-held-out validation, and the cohort has one. The single
independent holdout that exists is mixed to negative for the GP (see 5). Under spec §7, M3 offline integration
can continue because no positive benchmark is required. This verdict does not support any BO benefit or
speed-up claim, any adoption, or a real pilot.

## 1. Cohort identity (verified, not attested)

- Committed TrainingSet `b2_native/native_trainingset.{json,npz}`: the hashes recompute exactly
  (x `e359ce20…`, J `2e813ff9…`). n=197, d=13, `active-projection-v1`.
- R0 input: the committed `r0/offline_scores.json` is byte-identical to the builder input
  `scratch/bo_m0/r0/offline_scores_native_full/offline_scores.json` (`2e5f2470…`).
- Fresh read-only catalog `scratch/bo_m0/m2_gate/catalog_20261113/catalog.csv` (`5e1eb62d…`, 30,723 records).
  All 197 training rows join on (shard,row) with design_hash agreement 197/197, config `native__ath_core_v4`
  197/197, dependency `e3614d0ba5956ded` 197/197, objective v4 197/197. Fidelity is 192 screen + 5 verify
  (two solve hashes), as the freeze declares.
- The rebuild with the patched strict builder (`gate/rebuild_native.json`) reproduces the committed X/J
  hashes exactly, with `cohort_policy.status = ok_mixed_fidelity_declared`. With
  `require_single_fidelity=True` the same inputs give `incompatible_cohort`, as they should.

## 2. Group integrity (recovered from run provenance)

The training rows were mapped to native run directories by exact (design_hash, solve_hash) membership
(`gate/m2_gate_diagnostics.json` → `group_recovery`):

- d37d64 (CMA seed 1234, one resume segment): 190 rows
- d37d64/verify (re-solves of d37d64 finalists): 5 rows
- the seed design, shared with the 1-eval smoke run c41398 (and also evaluated first by 46b68c): 2 rows

**Connected independent groups: 1.** The strict harness `bo_sensitivity.run_diagnostics` with these
groups returns `unavailable: five group folds and at least five independent connected groups are required`
(gate_pass null). No groups were invented, and rows were not split to force a pass.

## 3. Bypass audit (bug found and fixed)

`bo.cohort.validate_cohort` / `bo.pipeline.fit_validated_cohort` (the strict gate) have **no production
caller**; only tests use them. The real path is `bo.data.build_native_training_set`, used by
`studies/builders.py` and the M2 tools. It checked config, R0 status and identity presence, but **not**:
objective version, response-detrended-ripple evidence, or cross-row backend / brief / dependency / target /
weights / metric-source agreement. It would have pooled a dependency-shifted run silently.

Fix (`hornlab_search/bo/data.py`, tests `tests/test_bo_native_policy_gate.py`, 8 tests):

- Rows are refused with `objective_version_mismatch` or `metric_policy_unsupported`.
- A cross-row disagreement in `NATIVE_POLICY_FIELDS` returns `incompatible_cohort`, and a missing policy
  value returns `capability_missing`, with no partial pooling.
- Fidelity mixing is published in `meta.cohort_policy` and refused only with `require_single_fidelity=True`,
  because the signed freeze declares the mixed cohort.
- The frozen math, encoding and subset rules are unchanged.

Demonstration: building over the fresh R0 (frozen rows plus the second CMA run) now returns
`incompatible_cohort` with conflicts `dependency_hash` (e3614d0b… vs 84709bd8…) and `metric_source`
(stored vs regenerated).

## 4. Prescribed diagnostics (bayes-venv, torch 2.14.1+cpu, botorch 0.18.1)

`python -m tools.analysis.bo_sensitivity sensitivity --out scratch/bo_m0/m2_gate/sensitivity_rerun
--pool-a scratch/bo_m0/m2/pools/pool-20261112.json --pool-b scratch/bo_m0/m2/pools/pool-20261113.json`
→ `complete_descriptive`, 7 subsets × noise {0.1,1,10} = 21 fits, 14 proposals over two pool seeds
(20261112, 20261113). Against the committed `m2/sensitivity.json`: **14/14 proposal geometries identical,
max fit RMSE difference 0**. Alternative subsets: all_eligible, stratified_by_J_cap64/128,
lowJ_plus_maximin_cap64/128, majority_solve_group_192 (screen-only). Pool-seed sensitivity: the frozen subset
proposes `5c02b169…` (seed A) vs `b7e68df0…` (seed B), so the argmax depends on the pool draw. The noise
multiplier barely moves anything (in-sample RMSE 0.1132 at all three). Report: `gate/sensitivity_rerun.md`.

## 5. Simple / CMA comparison (real evidence where it exists)

**The independent holdout.** The second native CMA run `20261113T004133Z-screen-46b68c` (seed 1235,
identical config except the CMA seed) was replayed by `offline_scores.py`:

- 393 exact_complete rows, zero backend calls, source unchanged.
- 196 holdout rows share no geometry with training.
- Caveats: the run is dependency-shifted (beat/mesher/hornlab_search SHAs differ), it is one group, and it is
  screen-only.

Two J identities were evaluated, and the second is needed because of the replay finding in 6:

| frozen-subset GP (n=197, noise ×1) | GP RMSE | train-mean RMSE | 1-NN RMSE | GP Spearman | 1-NN Spearman | 95% interval coverage | top-20 overlap |
|---|---:|---:|---:|---:|---:|---:|---:|
| holdout, replayed brief-target J | 5.69 | 5.66 | 6.56 | 0.50 | 0.25 | 0.95 | 3/20 |
| holdout, stored runtime J | 6.45 | 5.76 | 6.48 | 0.51 | 0.32 | 0.95 | 5/20 |

- The GP's **magnitude error is not better than predicting the training mean**.
- It does carry **moderate rank information**: Spearman about 0.5, against about 0.25-0.32 for 1-NN.
- Its intervals are wide but nominally calibrated.
- stratified_by_J_cap128 is the only subset that beats the mean baseline on both identities (4.78 vs 5.68 and
  5.18 vs 5.77). This is diagnostic only; the production recipe is not changed.
- lowJ_plus_maximin_cap64 is badly over-confident (coverage 0.0 and 0.24).

Full table: `holdout_prediction` in the JSON.

**CMA baseline (stored runtime J; equal-budget best-so-far)**

| valid evals | seed 1234 (d37d64) | seed 1235 (46b68c) |
|---|---:|---:|
| 18 | 3.187 | 2.990 |
| 50 | 1.975 | 2.154 |
| 100 | 1.911 | 2.039 |
| 192 | 1.597 | 1.742 |

The seed-to-seed spread at the pilot budget of 18 valid evaluations is 0.20 J. **No BO proposal has been
solved, so BO-vs-CMA performance is unmeasured.** The proposals' predicted J (3.6-3.9, intervals spanning
negative J) is a model output, not an outcome.

## 6. New finding: replay metric regeneration drift (NOT fixed here; objective/replay is outside bo/)

`gate/target_probe.json` reproduces it with zero backend calls:

- A brief target that differs from the stored record target **only** in `driver_exit_radius_mm` (25.4, now
  surfaced on newer records' targets) is treated as a target change, so the metrics are regenerated.
- The regenerated `di` / `dislope` / `distd` terms disagree strongly with the stored runtime terms:
  - row 57/387: stored J 1.813 vs regenerated 4.187 (di 1.33 → 10.53)
  - frozen row 37/356, given the radius: 2.969 → 5.338

Consequences:

1. Replayed J for post-change records is not comparable with the frozen cohort's stored J.
2. The R0 "changed-target" variant regenerates through the same path, so its `j_changed 393/393` is
   suspect.

Owner of `objective/replay.py` to review; recorded in `docs/ISSUES.md`. The frozen 197-row cohort is not
affected, because its stored target equals the brief target and its stored metrics are used.

## Reproduce

Copies of the scripts are in `gate/`; they run from `scratch/bo_m0/m2_gate/`, because their repo root is resolved relative to that location.

```
.venv\Scripts\python.exe tools\analysis\catalog.py --root dataset --out scratch\bo_m0\m2_gate\catalog_20261113 --summary-only
.venv\Scripts\python.exe tools\analysis\offline_scores.py --dataset dataset --out scratch\bo_m0\m2_gate\offline_scores_native_20261113 --limit 600 --catalog scratch\bo_m0\m2_gate\catalog_20261113\catalog.csv --config-filter native__ath_core_v4 --rows-cap 600
.venv\Scripts\python.exe scratch\bo_m0\m2_gate\rebuild_native.py
<bayes-venv>\Scripts\python.exe -m tools.analysis.bo_sensitivity sensitivity --out scratch\bo_m0\m2_gate\sensitivity_rerun --pool-a scratch\bo_m0\m2\pools\pool-20261112.json --pool-b scratch\bo_m0\m2\pools\pool-20261113.json
<bayes-venv>\Scripts\python.exe scratch\bo_m0\m2_gate\m2_gate_diagnostics.py
.venv\Scripts\python.exe scratch\bo_m0\m2_gate\target_probe.py
```

## What would change the verdict

- At least five independent connected native experiments under one dependency/metric identity. They would
  need new runs, which is owner-scheduled.
- A fixed or adjudicated replay regeneration path.
- At least one equal-cost screen of BO proposals against a CMA arm (S11 pilot 1 pattern).
