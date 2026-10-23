# CP-8d retrain after the OSSE top-up (2026-10-23, ~15:55 EDT) — GATES FAILED, model NOT used

Setup: dataset snapshot `dataset_snap_20261023` (robocopy of `dataset\` at 15:50 after the overnight queue,
`dataset verify OK: 14091 records re-read, 0 bad, 0 bad arrays`); torch on CPU (`CUDA_VISIBLE_DEVICES=""`);
`hornlab-search surrogate train --config examples/osse_baseline.yaml --dataset-dir <snapshot> --out <scratch>`.
Code at `571a4be` (includes the `solve_failed` label exclusion). Thresholds unchanged (`surrogate/gates.py`);
held-out fraction 15 % (plan `docs/plan/11_PHASE2_SURROGATE.md`).

Training arrays (OSSE family): considered 3634, selected 3080, skipped_grid_mismatch 533, skipped_bad_arrays 0,
**skipped_solve_failed 21** (the OSSE seed-4101 host crash); 142 duplicate designs dropped before the cluster
holdout split; **held out 463 < 500** -> the result is indicative only (plan floor). Wall time 14 s per training.

| gate | threshold | 600 epochs (runbook attempt-2 setting) | 300 epochs (CLI default) | 2026-10-14, 600 epochs (for reference, `CP-8d.md`) |
|---|---|---|---|---|
| spearman | > 0.9 | **PASS** 0.963 | PASS 0.938 | PASS 0.9861 |
| topk_overlap | >= 12 of 20 | **FAIL** 11 | FAIL 0 | PASS 15 |
| bw_mae_deg | < 2.0 | **PASS** 1.476 | PASS 1.817 | PASS 1.704 |
| di_mae_db | < 0.3 | **PASS** 0.206 | PASS 0.262 | PASS 0.232 |
| invalid_accuracy | > 0.85 | **FAIL** 0.800 | FAIL 0.711 | PASS 0.952 |
| monotonic_flips | == 0 | **FAIL** 4 | FAIL 4 | FAIL 1 |
| held-out designs | >= 500 | 463 (indicative) | 463 | 285 |

Verdict: `surrogate train GATES FAILED: topk_overlap, invalid_accuracy, monotonic_flips` (both settings, exit 1).
The model is NOT used (`propose` refuses an unvalidated bundle). No tuning beyond the two settings above
(that would be gate shopping).

Reading (no claim beyond the numbers): more data (3080 vs 1501 selected) improved the regression gates' errors
(bw 1.476 vs 1.704 deg, di 0.206 vs 0.232 dB) but the ranking/validity gates got worse. Not investigated here;
candidate causes to check (owner / phase-2 decision, nothing changed): the top-up searches concentrate in a new
low-J basin (seed 4101 best J 6.28 vs 6.106 for the original run), so the held-out top-20 may be a narrow
cluster; the selected set is 2632 ok / 448 failed (14.5 % negatives for the validity head); the `monotonic_flips` semantics question from the 2026-10-14
addendum (`NOTES_FOR_SENIOR.md`) is still open.

To reach the 500 floor at 15 %: about 3,334 selected OSSE records, i.e. ~250 more on the screen grid (~1 GPU hour
at ~265/h). Owner decision.
