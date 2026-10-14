# CP-8d — train + gate the Stage A surrogate (FAILED — twice-failed gate step; model not used)

Runbook §6 on the committed fix set (e0b9b61 + 11304f6): verdict persistence, config freeze,
dedup, meta prints, NaN conventions. Training is CPU-only torch; the gate thresholds in
`surrogate/gates.py` were **never touched**.

## Attempt 1 — `surrogate train --config examples/osse_baseline.yaml --out surrogate_osse.pt` (defaults: 300 epochs)

```
training arrays: considered 2034, selected 1501, skipped_grid_mismatch 533, skipped_bad_arrays 0, skipped_keys []
WARNING: 533 record(s) were dropped for a DIFFERENT frequency grid than the training grid
PASS  spearman           0.9673429304539599  need > 0.9
FAIL  topk_overlap                5  need >= 12 of 20
FAIL  bw_mae_deg         2.110073152608039  need < 2.0
PASS  di_mae_db          0.2866880128889568  need < 0.3
PASS  invalid_accuracy   0.8571428571428571  need > 0.85
PASS  monotonic_flips             0  need == 0
WARNING: held-out set has 285 designs; the plan requires >= 500 for the gates to count. Result is indicative only.
dropped 1 duplicate design(s) before the cluster holdout split
objective delta (recomputed vs stored): max 0, mean 0
surrogate train GATES FAILED: topk_overlap, bw_mae_deg: 1501 records, 285 held out -> surrogate_osse.pt
TRAIN_EXIT=1
```

## Attempt 2 — the runbook's own next fix: `--epochs 600`

```
training arrays: considered 2034, selected 1501, skipped_grid_mismatch 533, skipped_bad_arrays 0, skipped_keys []
WARNING: 533 record(s) were dropped for a DIFFERENT frequency grid than the training grid
PASS  spearman           0.9861316166758567  need > 0.9
PASS  topk_overlap               15  need >= 12 of 20
PASS  bw_mae_deg         1.7041547187252157  need < 2.0
PASS  di_mae_db          0.23190069504540475  need < 0.3
PASS  invalid_accuracy   0.9523809523809523  need > 0.85
FAIL  monotonic_flips             1  need == 0
WARNING: held-out set has 285 designs; the plan requires >= 500 for the gates to count. Result is indicative only.
dropped 1 duplicate design(s) before the cluster holdout split
objective delta (recomputed vs stored): max 0, mean 0
surrogate train GATES FAILED: monotonic_flips: 1501 records, 285 held out -> surrogate_osse.pt
TRAIN600_EXIT=1
```

## Decision (runbook-conform)

- **Two failures on the same step → stop** (hard rule 8): the dated block `2026-10-14 cp-8d` was
  appended to `NOTES_FOR_SENIOR.md` with both tables and the three decisions needed.
- **The model was NOT used**: `surrogate propose` / `surrogate round` were not run — their
  runbook precondition is a gate pass ("Exit code 1 means NOT PASSED: then do NOT use the model").
  `round_report['working']` therefore was never measured → **CP-8d = FAIL** by the runbook's pass
  criterion, not merely "indicative".
- Honest reading (labelled as such): the Stage A machinery demonstrably works on real data — five
  measured gates improve monotonically with epochs (0.9673→0.9861 Spearman; top-5/20→15/20 overlap;
  2.11→1.70° beamwidth MAE; 0.287→0.232 dB DI MAE; 0.857→0.952 validity accuracy) — and everything
  blocking a formal pass is record quantity: held-out is 285 vs the 500 floor (the cluster-holdout
  fraction also overshoots 15 % on clumped CMA data), and the pool is capped at 1501 selected of
  2034 OSSE records by grid mismatch (533 skipped = 133 smoke-grid + 400 throat_adapter-grid).
- The remaining runbook fix is "more records": an OSSE top-up of ~1900 via
  `search --config examples/osse_baseline.yaml --resume runs\20261013T123136Z-screen-ca15be
  --budget 1900` ≈ **10.2 h** at the measured 187/h — a user/GPU-hours decision (also the
  CP-9 cloud path). The `monotonic_flips = 1` cause (sweep invalid-boundary vs genuine)
  is question (2) in the NOTES block.