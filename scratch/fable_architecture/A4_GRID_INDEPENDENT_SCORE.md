# A4 — is a grid-independent score achievable, and where does the grid dependence come from?

**Run:** 2026-11-16 23:27 ET, HEAD `207f97a`. Read-only, CPU, no solve. Script `.a4/a4.py`,
records `.a4/records.json`. Data: the 58 screen/verify pairs under `runs/study-*` (same mesh,
18 versus 29 solved frequencies). Scorer: objective v7 from each study's own config, metrics
regenerated with the parity-exact harness `.tmp/fable_replay_harness.py`.
"Dense N" means the stored response interpolated (PCHIP in log-frequency) onto N points equally
spaced in log-frequency from 350 to 8,000 Hz, then scored with the unchanged scorer.

## Headline

1. **A grid-independent score exists and needs no new term definitions.** Scoring on a uniform
   dense log grid converges: going from 58 to 116 points changes J by sd 0.045 (0.016 among the
   best 28 designs), and from 116 to 232 by sd 0.025 (0.008). Rank correlation 1.000 and 0.999.
   On a uniform log grid a plain sample mean *is* the log-frequency integral, so the existing
   scorer already computes the grid-independent quantity once its input grid is uniform and dense.
2. **The large "29 → 58" shift reported in R2 is a change of definition, not noise.** It is the
   difference between the stored grid's uneven sample weighting and the uniform one: mean +0.38,
   sd 0.61 over all pairs, sd 0.20 among the best 28. It is spread over several terms (table
   below), not caused by one.
3. **What remains after the definition is fixed is the real sampling error: how well 18 solved
   frequencies determine the response.** Dense score from the 18-point solve versus dense score
   from the 29-point solve: mean +0.08, sd 0.20 over all pairs; **mean +0.13, sd 0.13, rank
   correlation 0.88 among the best 28**. With the stored grids the same comparison is sd 0.17 and
   rank correlation 0.81. So the dense definition removes about a quarter of the spread at the top
   and improves ranking, but 18 solved frequencies still leave about 0.13 J of uncertainty.
   R2's subsampling table says about 22 solved frequencies bring that to about 0.10.

## Numbers

| Comparison (b − a) | All 58: mean / sd / rank corr | Best 28: mean / sd / rank corr |
|---|---|---|
| Stored screen (18) → stored verify (29) | +0.426 / 0.554 / 0.975 | +0.186 / 0.169 / 0.807 |
| Verify stored grid → verify dense 58 | +0.375 / 0.608 / 0.980 | +0.391 / 0.197 / 0.862 |
| Verify dense 58 → dense 116 | −0.044 / 0.045 / 1.000 | −0.045 / 0.016 / 0.997 |
| Verify dense 116 → dense 232 | −0.032 / 0.025 / 1.000 | −0.030 / 0.008 / 0.999 |
| Dense 232 from 18 solved → from 29 solved | +0.084 / 0.200 / 0.984 | +0.128 / 0.126 / 0.882 |

Weighted term contributions to each difference (mean / sd, best 28 designs):

| Term | Stored grid → dense 58 | Dense 58 → dense 232 | Dense: 18 solved → 29 solved |
|---|---|---|---|
| cov | +0.063 / 0.079 | −0.003 / 0.009 | −0.011 / 0.014 |
| rip | −0.048 / 0.008 | −0.001 / 0.000 | +0.005 / 0.008 |
| di | +0.119 / 0.067 | −0.016 / 0.006 | +0.012 / 0.003 |
| dislope | +0.034 / 0.049 | −0.007 / 0.008 | −0.010 / 0.029 |
| flat | +0.108 / 0.068 | −0.028 / 0.016 | +0.061 / 0.043 |
| load | +0.006 / 0.027 | +0.002 / 0.003 | +0.030 / 0.043 |
| distd | +0.011 / 0.017 | −0.003 / 0.003 | −0.003 / 0.007 |
| diag | +0.036 / 0.063 | −0.008 / 0.011 | −0.008 / 0.027 |
| flat_cv | +0.062 / 0.071 | −0.011 / 0.011 | +0.053 / 0.081 |

## Reading

- The definition shift is led by `di`, `flat`, `cov` and `flat_cv`. These are means and standard
  deviations over whatever frequencies were solved; the screen and verify grids bunch extra points
  between 2.5 and 4.3 kHz and near the band edges, which silently weights those regions.
- The residual sampling error at the top is led by `flat_cv` (sd 0.08), `flat` and `load`
  (0.04 each). These are on-axis flatness and the loading crossing: quantities that depend on fine
  frequency detail an 18-point solve does not resolve. Coverage, ripple and DI are stable (sd
  ≤ 0.015). So the remaining noise is in the on-axis and loading terms, not in directivity.
- Dense scoring is free: it is interpolation of data already solved.

## What this does and does not establish

- Establishes: for these 58 designs and objective v7, a convergent grid-independent J; the size of
  the definitional shift; the residual at 18 solved frequencies; which terms carry each.
- Does not establish: the same numbers for v9 or a ranges-plus-constancy score (the method
  transfers; the values must be re-measured); mesh-refinement error (B1); other typologies (all 58
  pairs come from the BO-versus-CMA study cohort).
- Dense J is **not comparable** with any stored J. Adopting it means a new score identity and a
  re-score of history, which the identity system supports.

## Correction to earlier documents

`FABLE_DISCOVERY.md` §5.1 reported "both on a dense grid: sd 0.12, rank correlation 0.89" from a
harness with a DI error. With the parity-exact harness the best-28 figures are sd 0.13 and 0.88:
the conclusion stands. The later note that "interpolation alone shifts J by sd 0.61, so
interpolation is not a fix" misread R2: that shift is the change of definition.

**Next action enabled:** the scoring stage of an implementation plan can specify "score on a
uniform dense log grid (116 points) from at least 22 solved frequencies" as a concrete, measured
proposal, pending the same measurement under the owner's chosen objective.
