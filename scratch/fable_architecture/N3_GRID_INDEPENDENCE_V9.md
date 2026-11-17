# N3 — grid independence under v9 corridor plus constancy

Run: 2026-11-17, HEAD `8562e1b` at run time (script authored under `caa37d0`; the commit between the
two touches only docs/scratch). Read-only, CPU. Script: `scratch/fable_architecture/.n3/a4_v9.py`;
log `scratch/fable_architecture/.n3/a4_v9.log`. Inputs: the 58 study screen/verify pairs in
`runs/study-*` (identical design intersection and ok filter as A4); stored `response.npz`;
`.tmp/fable_replay_harness.py` for parity metrics and interpolation.

§0 gate (run once for the session): `parity smoke: worst regenerated-vs-stored DI ...: 0.0 n 17`.

## Headline

1. **v9 J on a uniform dense log grid converges by 58 points**: dense 58 → 116 changes J by sd 0.032
   (all 58 pairs) and 0.019 (best 28), rank correlation 0.999–0.997; 116 → 232 by sd 0.012 / 0.008.
   That is inside A4's comparison line (sd ≤ 0.05). The residual from having 18 solved frequencies
   rather than 29 is sd 0.193 (all) and **0.113 at the top**, rank 0.953 — the same size as A4's v7
   result (0.13).
2. **Adding the strict constancy cost changes the grid requirement.** J_v9+constancy is *not*
   converged at 58 points: 58 → 116 moves it by sd 0.175 (all) and 0.055 (best 28), the latter just
   over the 0.05 line; 116 → 232 is sd 0.058 / 0.014. So if the owner adopts constancy, the dense
   grid must be **116 points, not 58**. The 18 → 29-solved residual grows to sd 0.370 (all) / 0.205
   (best 28, rank 0.983) because the constancy cost is estimated from few solved frequencies.
3. **Constancy is the dominant secondary quantity, not a correction.** Its mean cost is 6.09 (all)
   and 3.22–3.45 (best 28) against J_v9 means of 3.77–3.98; it is ~55 % of J_v9+constancy and is
   J-independent. At v9 the residual error is carried by `flat_cv`, `load` and `flat` — the same
   terms as A4's v7 result. The best-28 set by v9 dense-116 overlaps A4's v7 criterion set 25/28.

## Corridor and weights used (placeholders)

Target `T_co` and the v9 block and weights are exactly `.a9/a9.py` lines 18–22:

```
coverage_profile: mode corridor
  h: [[700, 75, 60, 90], [8000, 75, 60, 90]]      (nominal, lower bound, upper bound; degrees)
  v: [[1000, 50, 40, 60], [8000, 50, 40, 60]]
block  v9: flat_band scored, cov_v_weight 0.5, cov_narrow_ratio 2, cov_below_f0 mask,
  tolerances cov_profile 3, rip 1, flat 1.5, load 0.3, dislope 9, di_roughness 0.5, flat_cv 1.5
weights: cov_profile 1, rip 1, flat 0.5, load 1, dislope 1, di_roughness 1, flat_cv 1
```

**These are placeholders** (the same ones N3/S1 used), not the owner's decision. Constancy is the
strict per-plane term from `.s1/replay.py` (function `constancy`, `linear=False`, weight 1 for H and
0.5 for V), with the H level clipped to the v9 corridor [60, 90] deg; a sensitivity run used the
literal `.s1` window [60, 80]. All 58 pairs scored without a penalty; 0 constancy cells are NaN;
`max |sum(weighted terms) − J_v9| = 0.0`.

## Result table — J_v9 (primary)

Dense grids: 58, 116, 232 points on `geomspace(350, 8000)`; "18 → 29 solved" compares the screen
response (18 frequencies) with the verify response (29), both on the same dense grid.

| Comparison (b − a) | All 58: mean / sd / rank corr | Best 28 by v9 dense-116: mean / sd / rank corr | A4-style v7 set (n = 28) |
|---|---|---|---|
| verify native 29 → dense 58 (definition change) | +0.212 / 0.200 / 0.984 | +0.185 / 0.154 / 0.894 | +0.184 / 0.174 / 0.912 |
| dense 58 → dense 116 | −0.009 / **0.032** / 0.999 | −0.015 / **0.019** / 0.997 | −0.016 / 0.020 / 0.997 |
| dense 116 → dense 232 | −0.015 / **0.012** / 1.000 | −0.017 / **0.008** / 0.998 | −0.017 / 0.009 / 0.998 |
| dense 232: from 18 solved → from 29 solved | +0.047 / 0.193 / 0.990 | +0.052 / **0.113** / 0.953 | +0.088 / 0.128 / 0.954 |
| dense 58 : from 18 solved → from 29 solved | +0.041 / 0.196 / 0.990 | +0.049 / 0.114 / 0.958 | +0.088 / 0.129 / 0.956 |

## Result table — J_v9 + constancy (secondary)

| Comparison (b − a) | All 58: mean / sd / rank corr | Best 28: mean / sd / rank corr | A4-style v7 set |
|---|---|---|---|
| verify native 29 → dense 58 | +0.537 / 1.081 / 0.989 | +0.328 / 0.404 / 0.946 | +0.248 / 0.294 / 0.958 |
| dense 58 → dense 116 | +0.112 / **0.175** / 1.000 | +0.070 / **0.055** / 0.998 | +0.079 / 0.061 / 0.999 |
| dense 116 → dense 232 | −0.031 / **0.058** / 1.000 | −0.021 / **0.014** / 0.999 | −0.023 / 0.012 / 1.000 |
| dense 232: 18 solved → 29 solved | −0.032 / 0.370 / 0.996 | −0.041 / **0.205** / 0.983 | +0.017 / 0.185 / 0.987 |
| dense 58 : 18 solved → 29 solved | −0.047 / 0.377 / 0.996 | −0.048 / 0.207 / 0.987 | +0.013 / 0.185 / 0.988 |

The constancy term's own contribution to these differences (mean / sd, all | best 28): 58 → 116
+0.121 / 0.155 | +0.085 / 0.046; 116 → 232 −0.016 / 0.054 | −0.004 / 0.009; 18 → 29 solved
−0.079 / 0.265 | −0.093 / 0.120. The J_v9 part of the 58 → 116 change is *smaller* than J_v9's own
(−0.009), so the constancy term is what makes the secondary quantity need 116 points.

## Per-term attribution (weighted contributions to J_v9 differences, mean / sd)

| Term | native 29 → dense 58 (all \| best 28) | dense 58 → 232 (all \| best 28) | 18 → 29 solved (all \| best 28) |
|---|---|---|---|
| cov_profile | +0.005 / 0.073 \| +0.002 / 0.021 | +0.010 / 0.013 \| +0.006 / 0.004 | −0.007 / 0.017 \| −0.003 / 0.005 |
| rip | −0.012 / 0.005 \| −0.012 / 0.003 | −0.000 / 0.000 \| −0.000 / 0.000 | +0.002 / 0.003 \| +0.003 / 0.004 |
| flat | +0.043 / 0.028 \| +0.035 / 0.029 | −0.011 / 0.005 \| −0.010 / 0.004 | **+0.016 / 0.032 \| +0.017 / 0.023** |
| load | +0.025 / 0.066 \| +0.006 / 0.027 | +0.006 / 0.014 \| +0.001 / 0.002 | **+0.026 / 0.047 \| +0.024 / 0.042** |
| dislope | +0.020 / 0.170 \| +0.029 / 0.048 | −0.004 / 0.033 \| −0.006 / 0.008 | −0.027 / 0.096 \| −0.008 / 0.027 |
| di_roughness | +0.068 / 0.093 \| +0.052 / 0.103 | −0.013 / 0.016 \| −0.012 / 0.020 | −0.002 / 0.075 \| −0.016 / 0.067 |
| flat_cv | +0.063 / 0.071 \| +0.073 / 0.063 | −0.012 / 0.011 \| −0.013 / 0.010 | **+0.038 / 0.091 \| +0.034 / 0.068** |

At the top the residual from 18 vs 29 solved frequencies is led by `flat_cv` (+0.034), `load`
(+0.024) and `flat` (+0.017); `rip` contributes 0.003. That is the same attribution A4 found for v7
(flat_cv, flat, load), so the v9 corridor does not move the error into the coverage term.

## Constancy diagnostics

| Grid | mean fitted H level (deg) | at/above 90 | at/below 60 |
|---|---:|---:|---:|
| verify native 29 | 69.17 | 0 | 1 |
| dense 58 | 69.50 | 0 | 1 |
| dense 116 | 69.51 | 0 | 1 |
| dense 232 | 69.52 | 0 | 1 |

The fitted level sits at ~69.5°, so the H upper clip is inactive on this cohort: the [60, 80] and
[60, 90] windows give identical results (the sensitivity block is identical to the secondary block),
and one design clips at the 60° floor in every grid.

## Cross-checks

- **A4 reproduction:** on the stored v7 screen grid, `max |J_v7 difference| = 0.00` over 58 pairs; the
  A4 best-28 set has 28 members and is reproduced exactly (overlap 28/28). The v9 best-28 set by
  dense-116 overlaps it 25/28.
- **Dense scores are a different identity** from stored J: only ranks and overlaps are compared here,
  never J values, and v7/v9 values are never compared.
- **Sibling rule:** the 58 study pairs are the same pairs A4 used; no split was widened.

## Verdict against the stated lines

- **Convergence sd ≤ 0.05 (A4 comparison, not a threshold):** J_v9 meets it at 58 points (0.032 all,
  0.019 top). J_v9+constancy does **not** (0.175 all, 0.055 top) and needs 116 points (0.058 all,
  0.014 top).
- **Residual at the top about 0.13:** J_v9 is sd 0.113 (rank 0.953) — at the line. J_v9+constancy is
  sd 0.205 (rank 0.983) — about 1.6× the line, carried by the constancy term's frequency noise.
- **Per-term table:** supplied; `flat_cv`, `load`, `flat` carry the residual, `rip` does not.

## What failed / what is unknown

- **Locale of the constancy definition.** The v9 corridor H bounds are [60, 90]; `.s1`'s literal call
  is [60, 80]. They are identical on this cohort only because no fitted level reaches 80. A cohort
  with flatter-after-clip designs would separate them; not tested.
- **The 18 → 29 residual is not removable by grid density.** It is a property of the solved
  frequencies, so no dense-grid point count fixes it; only more solved frequencies (or a smarter
  interpolation) can.
- **Whether 116 points is enough for the constancy term on the full 3,802-row landscape** is not
  tested; the 58 study pairs are the A4 sample and skew to better designs.
- **The corridor and weights remain placeholders**; a different corridor width would move the
  coverage term and possibly the convergence numbers.

## What this does not prove

- That the owner should adopt v9, the corridor, or constancy — it measures their grid behaviour only.
- That dense scores rank real horns better than stored J; A4's caveat stands.
- That 116 points is the minimum for J_v9 (58 already converges); it is the minimum for the
  constancy-augmented quantity on this cohort.

## Next action enabled

The scoring proposal can state, on measured numbers: score J_v9 on a uniform dense log grid of at
least 58 points; if constancy is added, use at least 116. Residual error from 18 solved frequencies
at the top stays sd 0.11 (J_v9) / 0.21 (J_v9+constancy), so a candidate's rank near the top is
stable (0.95 / 0.98) but its value is not comparable across grids. Owner decision still needed on
the corridor, the constancy functional and the frequency budget.

## Reproduce

```powershell
cd C:\Users\hunte\Hrns\hornlab-search
.venv/Scripts/python.exe scratch/fable_architecture/.tmp/fable_replay_harness.py
.venv/Scripts/python.exe scratch/fable_architecture/.n3/a4_v9.py
```

Runtime ~9 minutes on CPU. The script writes no records file; its printed tables are in
`.n3/a4_v9.log`. No file outside `scratch/fable_architecture/` was written.
