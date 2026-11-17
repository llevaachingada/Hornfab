# A10 — P1 predictor replay: hooks A, B, C and the unbiased-pool step

**Run:** 2026-11-17, HEAD `8562e1b`, canonical checkout `C:\Users\hunte\Hrns\hornlab-search`.
Read-only, CPU only, no solve, no pytest, no git mutation. Interpreter `.venv\Scripts\python.exe`.
Scripts `.p1/build_desc.py`, `.p1/replay.py`, `.p1/fairpool.py`; records `.p1/desc_all.npz`,
`.p1/results.json`, `.p1/fairpool.json`. Descriptors rebuilt for **3,410 of 3,414** valid rows
(4 rows of `hl__lecleach_hv_landscape_smooth_v7` have too little wall profile to describe); J is the
**stored** objective, never recomputed. The v7 `cov` and `di` terms regenerated with the repo's own
term functions match the stored terms **exactly** on all rows of the 19 test lanes (max |Δ| 0.0000).
Predicted full J is **unavailable** (the model predicts H/V beamwidth and DI only); where a full-J
prediction would be required it is marked unavailable, never substituted.

## Headline

1. **The unbiased-pool stop condition fired.** No BoTorch study lane has a single solved design that
   was not selected by a rule: strict count is **0 of 8 lanes**. Even counting model-free maximin
   exploration proposals (and inferring a quarter of the unrecorded rows from the frozen cadence),
   6 of 8 lanes stay under 30 and the other 2 only pass on an unverified upper bound. The fair-pool
   replay was therefore **not run**, and no optimizer-visited substitute is reported as a finding.
2. **Hook A fails its stated line against the solved result that matters.** Rank correlation with the
   lanes' best full J is **0.733** (line ≥ 0.8) and only **1 of the true top five** lanes is in the
   predicted top five. The like-for-like comparison against the *coverage+DI decile* is 0.944 and is
   reported as a diagnostic, not as the pass. **Hook B fails:** the predictor's single pick beats the
   actual first solve in **11 of 19** lanes (line 13 of 19) and is no better than one random stored
   design (**11 of 19**). The best of its top eight does reach the 11th within-lane J percentile that
   an7 reported, but a start is one shape: the single pick sits at the 37th percentile.
3. **Hook C's wins are the pool's, not the predictor's.** Predictor top 8/16/32 beat the actual first
   8/16/32 in **14/16/13 of 19** lanes, but a random draw from the same CMA-visited pool beats the
   first rows in **18/17/14 of 19** and beats the predictor's set in **10/12/10 of 19**. The
   skip test fails: **8.9 %** of designs the predictor would skip are in the lane's true top 10 %
   (line < 2 %). The published an7 result reproduces exactly on its own sample: 0.55 / 0.43 / 0.30
   median gaps; 12 of 19 vs earliest; 9 of 19 vs random.

## Data, splits and definitions

| Item | Value |
|---|---|
| Rows with valid 18-frequency metrics | 3,414 (all runs are landscape 80×50 / 600×480×480) |
| Rows with rebuilt 27-number descriptor | 3,410 |
| Test lanes (an7 rule: `cd` brief, ≥ 40 stored rows) | **19** |
| Predictor | `.fable/an3.py`: ExtraTrees, 200 trees, `min_samples_leaf=2`, seed 0 |
| Input / output | 27 shape numbers (bounding size + 12-bin H/V wall profiles) → 18-frequency H/V beamwidth + DI |
| Sibling split | `.x3/strict.py` map, whole sibling group held out from training |
| Engine split | `.x3/strict.py` groups OSSE / GRID / GEN-FF, whole group held out |
| Lane order | `created_utc`, tie-break (`run`, `n`) — replaces an7's per-run `n` order |
| Ranked objective (prediction) | v7 `cov + 0.3·di`, tolerance-normalised (the `cov+DI` part of J) |
| Outcome (no prediction) | **stored full J**, plus the stored `cov` and `di` terms |
| Outside support | nearest-training-neighbour distance > 1.5 × the 99th percentile of training leave-one-out neighbour distance (standardised descriptors) |

The 19 lanes and stored row counts: petal 46, tritonia_v8 112, tritonia_v9 120, twinray 161,
biradial 309, crowe_home 158, crowe_x_osse 202, es_rollback 79, ext_throat 137, lecleach_iwata 80,
osse_fold_warm 248, osse_morph 75, rolled_spiral 61, rosse_rect 254, rf_section 51, rr_crowe 160,
sp_control 48, sp_moderate 47, sp_strong 47. The `smooth` lanes are training data only.

## Step 1 (done first) — unbiased designs per lane

"Unbiased" = a stored solved design that was not chosen by an optimizer. The runs themselves contain
**none**: all 692 run configs use `algorithm: cma` (664) or `cma_me` (28), so every run row is
search-visited. The 58 `runs/study-*/{screen,verify}` directories are CMA cohort runs for study
preparation, not Sobol rows; the actual BoTorch packages are under `runs/bo_*`, `runs/home_*_2026-11-*`
and `runs/night31_2026-11-17`. Every solved study observation carries a `pool-*` or `turbo-*` id, and
every arm with a surviving proposal artifact records an acquisition selection over a fixed Sobol pool
(`qLogNEI` or `qLogNEHVI`; for example 1,707 legal candidates in `bo_s31001`).

| Study lane | Arms | Solved observations | Strict unbiased | Recorded model-free ("exploration") | Cadence upper bound¹ | ≥ 30? |
|---|---:|---:|---:|---:|---:|---|
| `hl__ext_throat_hvlaw_v7` | 5 | 219 | 0 | 6 | 64 | only at upper bound |
| `p80x60__osse_ext_throat_home700_v7_seed5678` | 3 | 180 | 0 | 0 | 52 | only at upper bound |
| `hl__ath_tritonia_landscape_v8` | 1 | 58 | 0 | 0 | 2 | no |
| `hl__ath_twinray380_landscape_v8` | 1 | 80 | 0 | 0 | 1 | no |
| `hl__osse_rrect_fold_warm_v7` | 1 | 80 | 0 | 0 | 1 | no |
| `p80x60__ath_core_14in_home700_v7` | 2 | 27 | 0 | 7 | 9 | no |
| `p80x60__ext_throat_corelaw_v7` | 1 | 25 | 0 | 6 | 7 | no |
| `p80x60__ext_throat_hvlaw_cov_v7` | 1 | 25 | 0 | 0 | 8 | no |

¹ Upper bound = recorded exploration + ⌈unrecorded screens / 4⌉, because `ProposalPolicy` takes the
model-free maximin arm on every fourth 0-based proposal. It is a bound, not a count: those arms did
not store a per-row selection reason. The strict count is zero for every arm and needs no inference.

**Stop condition: fired.** All 8 lanes have fewer than 30 unbiased designs on the recorded count, and
6 of 8 stay below 30 even on the generous upper bound. On the 19 replay lanes the position is worse:
15 lanes have no study observations at all, and the 4 that do have 0 strict unbiased rows. The
unbiased fair-pool comparison is therefore **not run**. The biased replay below is labelled as such
and is not offered as a substitute for step 7.

## Known result reproduced first

`.fable/an7.py` re-run at this HEAD on its own 70-per-lane descriptor sample and `fam()` sibling rule:
**19 lanes; median gap to lane best — earliest-8 0.55, predictor-8 0.43, random-8 0.30; predictor-8
beats earliest-8 in 12 of 19 and random-8 in 9 of 19; pick percentile 40 / 11.** This reproduces
`PREDICTOR_AND_WORKFLOW.md` §6 exactly and validates the pipeline. The replay below differs in three
declared ways only: all valid rows instead of the 70-per-lane sample, the strict sibling map instead
of `fam()`, and chronological order instead of per-run `n`.

## Hook A — lane ordering

Trained on all other sibling groups, each lane scored by the mean predicted `cov+DI` of its best
predicted decile. Two actual comparators: the same decile statistic on stored terms, and the lane's
best stored full J.

| Lane | n | Predicted decile | Actual decile (cov+DI) | Actual best J | Rank pred | Rank actual | Rank best J |
|---|---:|---:|---:|---:|---:|---:|---:|
| ath_core_petal | 46 | 1.827 | 2.567 | 5.32 | 9 | 10 | 7 |
| tritonia_v8 | 112 | 1.317 | 1.517 | 5.69 | 5 | 6 | 9 |
| tritonia_v9 | 120 | 1.126 | 1.174 | 5.01 | 4 | 3 | 6 |
| twinray | 161 | 1.353 | 1.733 | 4.91 | 6 | 7 | 5 |
| biradial | 309 | 0.985 | 1.193 | 6.45 | 1 | 4 | 10 |
| crowe_home | 158 | 4.285 | 4.653 | 16.92 | 13 | 13 | 11 |
| crowe_x_osse | 202 | 1.030 | 1.081 | 5.34 | 2 | 2 | 8 |
| es_rollback | 79 | 5.562 | 5.915 | 20.86 | 14 | 14 | 15 |
| ext_throat | 137 | 1.925 | 1.409 | 3.10 | 10 | 5 | 1 |
| lecleach_iwata | 80 | 5.620 | 6.261 | 19.42 | 15 | 15 | 14 |
| osse_fold_warm | 248 | 1.673 | 1.745 | 3.62 | 8 | 8 | 2 |
| osse_morph | 75 | 1.410 | 1.822 | 3.99 | 7 | 9 | 3 |
| rolled_spiral | 61 | 3.645 | 4.572 | 17.71 | 11 | 11 | 13 |
| rosse_rect | 254 | 1.079 | 0.776 | 4.56 | 3 | 1 | 4 |
| rf_section | 51 | 3.942 | 4.589 | 17.40 | 12 | 12 | 12 |
| rr_crowe | 160 | 7.017 | 7.069 | 22.54 | 18 | 16 | 16 |
| sp_control | 48 | 7.126 | 7.081 | 22.77 | 19 | 17 | 17 |
| sp_moderate | 47 | 6.844 | 7.135 | 22.94 | 17 | 18 | 18 |
| sp_strong | 47 | 6.704 | 7.464 | 23.79 | 16 | 19 | 19 |

| Variant | n | Rank corr. vs actual decile | Rank corr. vs best full J | True top-5 in predicted top-5 |
|---|---:|---:|---:|---:|
| Sibling groups held out (primary) | 19 | **0.944** | **0.733** | 1 of 5 (by best J); 4 of 5 (by actual decile) |
| Whole engine group held out | 19 | 0.896 | 0.665 | 1 of 5 (by best J) |
| Equal 40-row pool per lane (sensitivity) | 19 | 0.937 | — | 4 of 5 (by actual decile) |

Predicted top five: biradial, crowe_x_osse, rosse_rect, tritonia_v9, tritonia_v8.
True top five by best J: ext_throat (3.10), osse_fold_warm (3.62), osse_morph (3.99), rosse_rect
(4.56), twinray (4.91). The predictor leads with `biradial_es_style_v7`, an extrapolation lane
(131/309 designs outside support) whose real best J is 6.45.

## Hook B — starting shape

One pick per lane: the lowest predicted `cov+DI` among all stored designs; "first" is the lane's
chronologically earliest solve; "random" is one random stored design (median of 200 draws).
Denominators are 19 lanes.

| Lane | n | First J | Predictor pick J | Random J | First — pick — random (cov+DI) | Outside pick? |
|---|---:|---:|---:|---:|---|---|
| ath_core_petal | 46 | 8.68 | 9.00 | 10.95 | 3.25 — 3.46 — 4.69 | no |
| tritonia_v8 | 112 | 26.90 | 7.04 | 11.12 | 7.89 — 1.61 — 2.49 | no |
| tritonia_v9 | 120 | 5.69 | 5.98 | 6.33 | 1.57 — 1.30 — 1.67 | no |
| twinray | 161 | 11.40 | 5.49 | 7.61 | 3.43 — 1.41 — 2.71 | no |
| biradial † | 309 | 7.78 | 8.13 | 7.15 | 1.46 — 1.71 — 1.41 | **yes** |
| crowe_home | 158 | 17.96 | 18.79 | 17.80 | 5.01 — 4.84 — 4.87 | no |
| crowe_x_osse | 202 | 6.06 | 5.69 | 6.18 | 1.14 — 1.10 — 1.28 | no |
| es_rollback † | 79 | 23.01 | 22.94 | 22.16 | 6.47 — 6.68 — 6.43 | **yes** |
| ext_throat | 137 | 6.83 | 4.25 | 6.80 | 2.39 — 1.59 — 2.28 | no |
| lecleach_iwata | 80 | 21.54 | 19.68 | 21.07 | 6.34 — 6.79 — 6.51 | no |
| osse_fold_warm | 248 | 4.29 | 4.23 | 4.46 | 1.83 — 1.82 — 2.03 | no |
| osse_morph | 75 | 8.27 | 8.49 | 7.03 | 3.62 — 3.14 — 2.82 | no |
| rolled_spiral | 61 | 29.92 | 21.34 | 25.78 | 7.33 — 5.74 — 6.36 | no |
| rosse_rect | 254 | 9.70 | 7.57 | 5.81 | 2.23 — 1.65 — 1.15 | no |
| rf_section | 51 | 17.95 | 19.91 | 18.49 | 5.06 — 4.46 — 4.98 | no |
| rr_crowe | 160 | 23.09 | 22.59 | 22.93 | 7.14 — 6.98 — 7.14 | no |
| sp_control | 48 | 23.20 | 22.92 | 23.08 | 7.18 — 7.09 — 7.15 | no |
| sp_moderate | 47 | 23.65 | 23.85 | 23.26 | 7.36 — 7.44 — 7.24 | no |
| sp_strong | 47 | 24.47 | 24.61 | 24.09 | 7.69 — 7.75 — 7.57 | no |

† Predictor pick is outside the training support. Its outcome is marked, not reported as a finding;
no predicted beam change is reported anywhere (the model's beam output is never used as evidence).

| Outcome | Predictor beats first | Predictor beats random | Random beats first | Median gap pick − first | Median gap pick − random |
|---|---:|---:|---:|---:|---:|
| Stored full J (primary) | **11 / 19** | **11 / 19** | **14 / 19** | −0.068 | −0.231 |
| Stored `cov+DI` only | 13 / 19 | 12 / 19 | 13 / 19 | — | — |
| Full J, outside-pick lanes excluded | 10 / 17 | — | — | — | — |

Predictor beats both first and random in 9 of 19; is worse than both in 6 of 19. Median within-lane
J percentile of the pick: **37** (0 = best). Only 3 of 19 picks are in the lane's best 10 %.

## Hook C — scouting round

Best J among the first N actual solves, the predictor's top N, and random N draws from the same
visited pool (median of 200). "Reveals" is the number of chronological real rows needed to reach that
set's best J, both measured on the same lane order; a better (lower) J usually needs more reveals, so J
and reveals must be read together.

| N | Predictor beats first-N (J) | Predictor beats random-N (J) | Random-N beats first-N (J) | Median reveals: first / pred / random | `cov+DI`: pred beats first / random |
|---:|---:|---:|---:|---|---|
| 8 | **14 / 19** | **9 / 19** | **18 / 19** | 3 / 16 / 30 | 17 / 19, 11 / 19 |
| 16 | **16 / 19** | **7 / 19** | **17 / 19** | 10 / 33 / 38 | 15 / 19, 12 / 19 |
| 32 | **13 / 19** | **9 / 19** | **14 / 19** | 27 / 45 / 50 | 11 / 19, 9 / 19 |

Per-lane N=8: the predictor's 8 are worse than a random 8 in 10 of 19 lanes and worse than the
actual first 8 in 5 of 19. The best of the predictor's top eight sits at the 11th within-lane J
percentile (the an7 figure); top 16 and top 32 reach the 4th and 0th. The count against the first
rows is inflated by the earliest solved rows being poor starts: any draw from the whole visited pool
beats them (18 of 19 for random).

## Skip test — designs the predictor would not solve

Bottom half of each lane by predicted `cov+DI`; true top 10 % by stored full J. Pooled denominator
1,193 skipped designs in 19 lanes.

| Test | Skipped designs in lane top 10 % | Denominator | Rate | Pass line | Verdict |
|---|---:|---:|---:|---:|---|
| Full J (stated) | 106 | 1,193 | **8.9 %** | < 2 % | **fail** |
| `cov+DI` top decile (sensitivity) | 84 | 1,193 | **7.0 %** | < 2 % | **fail** |

Worst lanes: sp_strong 5/23 (21.7 %), biradial 27/154 (17.5 %), rosse_rect 22/127 (17.3 %),
rf_section 4/25 (16.0 %), es_rollback 6/39 (15.4 %), crowe_home 10/79 (12.7 %). No lane passes.

## Verdict against the stated pass lines

| Hook | Stated pass line (§4) | Measured | Verdict |
|---|---|---|---|
| A. Lane ordering | rank correlation ≥ 0.8 against solved lane results, siblings excluded | 0.733 vs best full J (0.944 vs the same cov+DI statistic); 1 of true top 5 in predicted top 5 | **Fail** |
| B. Start picking | predictor picks beat the usual starts in ≥ 2/3 of lanes | 11 of 19 (13 needed); 11 of 19 vs random; 10 of 17 excluding outside picks | **Fail** |
| C. Scouting round | same line applied to N = 8/16/32 | 14, 16, 13 of 19 vs first-N; 9, 7, 9 of 19 vs random-N; random-N beats first-N in 18/17/14 | **Fail against the credible baseline** (meets the literal start-beating line at all three N, but random does too) |
| Skip test | < 2 % of skipped designs in lane top 10 % | 8.9 % (106/1,193) | **Fail** |
| Step 7. Unbiased pool | ≥ 30 independent designs per lane, else leave untested | 0 strict in every lane; 6 of 8 < 30 even at the upper bound | **Stop fired; not tested** |

## What failed, and what is unknown

- **Failed:** the gates fail on the credible comparison, and the unbiased step cannot be run at all.
  The apparent hook C win over the actual first rows is reproduced by random draws from the same pool,
  so it attributes nothing to the predictor; hook C meets the literal start-beating line only where a
  random draw does too.
- **Worst lanes and why.** `sp_control/moderate/strong` have within-lane rank correlations +0.05,
  −0.44, −0.50 although their median support distance is only 0.10–0.21: they fail *inside* the
  training support, not by extrapolation, because holding out the whole `sp__` group removes the only
  similar shapes. `biradial` (−0.41) and `rosse_rect` (−0.18) are genuine extrapolation: median
  distance to the nearest training design 2.68 and 2.25 standardised units, with 42 % and 36 % of
  their designs beyond the support bound. The remaining lanes are weak but not extrapolating.
- **Unknown:** whether a fair unbiased pool would change any conclusion — it does not exist in the
  stored record. The 8 study lanes' missed quarter-cadence proposals are not stored per row, so even
  the generous count is an inference. Also unknown: the effect of the 4 undescribed rows; whether the
  support rule (1.5 × training 99th-percentile neighbour distance) is the right rejection rule; and
  how much of hook A's like-for-like correlation is lane-level difficulty rather than design-level
  prediction.

## What this does not prove

It does not prove that the predictor cannot help a workflow. It measures the existing model, on
optimizer-visited pools, with a coverage+DI ranking and a full-J outcome; it cannot show what the
predictor would do on an even design pool spread across each lane's ranges, which is the test the
brief actually asks for and which needs new solves. It does not establish any acoustic result: every
J quoted is a stored run objective, and no predicted beamwidth change is reported. It does not
validate the distance-rejection rule or the 30-design floor as decision thresholds; both are checks,
not calibrated gates.

## Next action

1. Do **not** deploy or schedule hooks A–C or D/E on this evidence. Hook A should not be offered as
   an owner-reviewed ordering proposal on the strength of the like-for-like 0.944; against the lane's
   best J it misses the line.
2. To answer the actual question, prepare the declared prospective test: ≥ 30 designs per lane drawn
   evenly across the ranges (not CMA-visited), solved and scored under the same brief and budget,
   with the predictor, a random draw and plain CMA compared on matched denominators. That is the
   owner-approval BEM stage in §10 (40 solves for two lanes) extended to the ≥ 30/lane floor; it
   cannot be substituted by more mining of the current runs.
3. If a cheap next CPU step is wanted, record a per-proposal `selection_reason` and the Sobol pool
   index for every future study observation, so the unbiased count is recoverable rather than
   inferred.

## Reproduce

From `C:\Users\hunte\Hrns\hornlab-search`:

```powershell
.venv\Scripts\python.exe scratch\fable_architecture\.p1\build_desc.py   # 3,410 descriptors, ~48 s
.venv\Scripts\python.exe scratch\fable_architecture\.p1\replay.py       # hooks A/B/C + skip, writes results.json
.venv\Scripts\python.exe scratch\fable_architecture\.p1\fairpool.py     # step-7 counts + stop rule
.venv\Scripts\python.exe scratch\fable_architecture\.fable\an7.py       # known-result reproduction
```

All four are read-only CPU scripts; none builds a mesh, solves, or writes outside
`scratch/fable_architecture/.p1/`. `an7.py` reads its own 70-per-lane descriptor sample from disk.
