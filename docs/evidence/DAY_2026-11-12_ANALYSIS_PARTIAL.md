# Day analysis — PARTIAL (2026-11-12)

**STATUS: PARTIAL — not the final day evidence.** The GPU continuation queue is still running
(`g2`–`g9`). This report covers the runs completed or in progress by ~16:30: `g1`/`g1b`, `c2`,
`g6` base, `g8`/`g9` bases. The final report will add `g2`–`g7`, the `g5` staged A/B, and the
A.6 narrow-vs-control / staged-vs-joint comparisons, then supersede this document.

- Spec: `tools/analysis/specs/day_2026-11-12.yaml` (partial fill; `g2`–`g7` commented out).
- Report source: `oc-wt/AN/scratch/report_day_partial/` (local); committed charts are in
  `docs/evidence/day_2026-11-12_partial/` (`10` PNGs).
- No code, queue, or default changes. J is comparable only within a brief.

The generated A.8 report follows, then the additional CPU-only analyses run today.

---

# Day analysis report

Spec: `C:\Users\hunte\Hrns\oc-wt\AN\tools\analysis\specs\day_2026-11-12.yaml`. Each section's JSON/MD lives in its subfolder of `--out`.

- **g1** (convergence): ok
- **c2** (convergence): ok
- **g8** (convergence): ok
- **g9** (convergence): ok
- **v6_seeds** (seed_variance): ok
- **g1** (sensitivity): ok
- **g6** (sensitivity): ok
- **g1** (links): ok
- **g1** (walls): ok
- **g6** (walls): ok
- **g1** (term_balance): ok
- **g6** (term_balance): ok
- **g1** (fidelity): ok

## g1 (convergence)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\convergence_g1\convergence.json

# Convergence

Best-so-far J over new **valid** evaluations (cached replays are not new evals).

## `20261030T170642Z-screen-fbab4f`

- brief `atlas__core_law` (family `OSSE`; objective v4, mode `screen`)
- rows: 1001 (567 valid, 1 cached replays, 566 new valid)
- final best J: **2.1282739397440635**
- evals to within 1% of final best: 467; within 5%: 467
- still improving in the last 20%: **True** (7.85% of final best)

| window | refusal rate | kinds |
|---|---:|---|
| 1–50 | 0.48 | invalid_geometry×14, mesh_too_large×10 |
| 51–100 | 0.40 | invalid_geometry×15, mesh_too_large×5 |
| 101–150 | 0.46 | invalid_geometry×18, mesh_too_large×5 |
| 151–200 | 0.32 | invalid_geometry×12, mesh_too_large×4 |
| 201–250 | 0.44 | invalid_geometry×18, mesh_too_large×4 |
| 251–300 | 0.36 | invalid_geometry×14, mesh_too_large×4 |
| 301–350 | 0.34 | invalid_geometry×12, mesh_too_large×5 |
| 351–400 | 0.40 | invalid_geometry×14, mesh_too_large×6 |
| 401–450 | 0.36 | invalid_geometry×14, mesh_too_large×4 |
| 451–500 | 0.64 | invalid_geometry×25, mesh_too_large×7 |
| 501–550 | 0.44 | invalid_geometry×17, mesh_too_large×5 |
| 551–600 | 0.44 | invalid_geometry×13, mesh_too_large×9 |
| 601–650 | 0.62 | invalid_geometry×24, mesh_too_large×7 |
| 651–700 | 0.34 | invalid_geometry×13, mesh_too_large×4 |
| 701–750 | 0.44 | invalid_geometry×19, mesh_too_large×3 |
| 751–800 | 0.50 | invalid_geometry×16, mesh_too_large×9 |
| 801–850 | 0.42 | invalid_geometry×18, mesh_too_large×2, solve_failed×1 |
| 851–900 | 0.32 | invalid_geometry×13, mesh_too_large×3 |
| 901–950 | 0.62 | invalid_geometry×26, mesh_too_large×5 |
| 951–1000 | 0.34 | invalid_geometry×12, mesh_too_large×5 |


----

## c2 (convergence)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\convergence_c2\convergence.json

# Convergence

Best-so-far J over new **valid** evaluations (cached replays are not new evals).

## `20261112T144510Z-screen-00cf9c`

- brief `lecleach_rollback` (family `FREEFORM`; objective v6, mode `screen`)
- rows: 200 (186 valid, 0 cached replays, 186 new valid)
- final best J: **0.8318890740005608**
- evals to within 1% of final best: 97; within 5%: 97
- still improving in the last 20%: **False** (0.53% of final best)

| window | refusal rate | kinds |
|---|---:|---|
| 1–50 | 0.10 | invalid_geometry×5 |
| 51–100 | 0.02 | invalid_geometry×1 |
| 101–150 | 0.12 | invalid_geometry×6 |
| 151–200 | 0.04 | invalid_geometry×2 |


----

## g8 (convergence)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\convergence_g8\convergence.json

# Convergence

Best-so-far J over new **valid** evaluations (cached replays are not new evals).

## `20261112T110126Z-screen-c414b1`

- brief `atlas__osse_ext_throat` (family `OSSE`; objective v7, mode `screen`)
- rows: 201 (140 valid, 1 cached replays, 139 new valid)
- final best J: **6.636102849109874**
- evals to within 1% of final best: 45; within 5%: 45
- still improving in the last 20%: **False** (0.00% of final best)

| window | refusal rate | kinds |
|---|---:|---|
| 1–50 | 0.28 | invalid_geometry×14 |
| 51–100 | 0.34 | invalid_geometry×17 |
| 101–150 | 0.32 | invalid_geometry×16 |
| 151–200 | 0.28 | invalid_geometry×14 |


----

## g9 (convergence)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\convergence_g9\convergence.json

# Convergence

Best-so-far J over new **valid** evaluations (cached replays are not new evals).

## `20261030T111108Z-screen-377bbe`

- brief `atlas__ath_core` (family `OSSE`; objective v4, mode `screen`)
- rows: 1326 (1141 valid, 1 cached replays, 1140 new valid)
- final best J: **2.0986738064025143**
- evals to within 1% of final best: 754; within 5%: 754
- still improving in the last 20%: **False** (0.00% of final best)

| window | refusal rate | kinds |
|---|---:|---|
| 1–50 | 0.14 | invalid_geometry×3, mesh_too_large×4 |
| 51–100 | 0.08 | invalid_geometry×3, mesh_too_large×1 |
| 101–150 | 0.28 | invalid_geometry×9, mesh_too_large×5 |
| 151–200 | 0.04 | invalid_geometry×2 |
| 201–250 | 0.12 | invalid_geometry×5, mesh_too_large×1 |
| 251–300 | 0.04 | invalid_geometry×1, mesh_too_large×1 |
| 301–350 | 0.06 | invalid_geometry×1, mesh_too_large×2 |
| 351–400 | 0.10 | invalid_geometry×3, mesh_too_large×2 |
| 401–450 | 0.08 | invalid_geometry×3, mesh_too_large×1 |
| 451–500 | 0.12 | invalid_geometry×3, mesh_too_large×3 |
| 501–550 | 0.08 | invalid_geometry×2, mesh_too_large×2 |
| 551–600 | 0.14 | invalid_geometry×4, mesh_too_large×3 |
| 601–650 | 0.16 | invalid_geometry×2, mesh_too_large×6 |
| 651–700 | 0.20 | invalid_geometry×7, mesh_too_large×3 |
| 701–750 | 0.10 | invalid_geometry×3, mesh_too_large×2 |
| 751–800 | 0.08 | invalid_geometry×3, mesh_too_large×1 |
| 801–850 | 0.18 | invalid_geometry×7, mesh_too_large×2 |
| 851–900 | 0.22 | invalid_geometry×8, mesh_too_large×3 |
| 901–950 | 0.16 | invalid_geometry×7, mesh_too_large×1 |
| 951–1000 | 0.20 | invalid_geometry×7, mesh_too_large×3 |
| 1001–1050 | 0.08 | invalid_geometry×2, mesh_too_large×2 |
| 1051–1100 | 0.12 | invalid_geometry×3, mesh_too_large×3 |
| 1101–1150 | 0.20 | invalid_geometry×8, mesh_too_large×2 |
| 1151–1200 | 0.16 | invalid_geometry×3, mesh_too_large×5 |
| 1201–1250 | 0.24 | invalid_geometry×5, mesh_too_large×7 |
| 1251–1300 | 0.20 | invalid_geometry×7, mesh_too_large×3 |
| 1301–1325 | 0.24 | invalid_geometry×2, mesh_too_large×3, solve_failed×1 |


----

## v6_seeds (seed_variance)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\seed_variance_v6_seeds\seed_variance.json

# Report section

```json
{
 "groups": {
  "v6_seeds": {
   "runs": [
    "runs\\20261112T113047Z-screen-24053e",
    "runs\\20261112T144510Z-screen-00cf9c"
   ],
   "n_seeds": 2,
   "seeds": [
    {
     "run_dir": "runs\\20261112T113047Z-screen-24053e",
     "cma_seed": 1234,
     "best_j": 1.5356464623830732,
     "n_new_valid": 142,
     "evals_to_1pct": 64,
     "evals_to_5pct": 1
    },
    {
     "run_dir": "runs\\20261112T144510Z-screen-00cf9c",
     "cma_seed": 1236,
     "best_j": 0.8318890740005608,
     "n_new_valid": 186,
     "evals_to_1pct": 97,
     "evals_to_5pct": 97
    }
   ],
   "median_best": 1.183767768191817,
   "spread_best": 0.7037573883825124,
   "ci95_median_best": null,
   "seed_distances_norm": {
    "runs\\20261112T113047Z-screen-24053e|runs\\20261112T144510Z-screen-00cf9c": 0.5738191986308632
   },
   "ecdf_1pct": [
    [
     97.0,
     0.5
    ],
    [
     186.0,
     0.5
    ]
   ],
   "ecdf_5pct": [
    [
     97.0,
     0.5
    ],
    [
     186.0,
     0.5
    ]
   ]
  }
 },
 "verdicts": [],
 "seed_rule": "A beats B only when medians differ by more than both spreads; >= 5 seeds prints a verdict (3-4 = indicative)"
}
```


----

## g1 (sensitivity)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\sensitivity_g1\sensitivity.json

# Sensitivity

Run `20261030T170642Z-screen-fbab4f` (family `OSSE`, objective v4, 567 valid rows).
Spearman on optimizer samples is biased; the surrogate importance below is the
unbiased companion (productionised from `study_2026-11-12/sensitivity_analysis.py`).

| knob | rho | n |
|---|---:|---:|
| `L_mm` | -0.705 | 567 |
| `a_deg` | -0.225 | 567 |
| `k` | +0.183 | 567 |
| `s` | +0.177 | 567 |
| `morph_rate` | +0.174 | 567 |
| `morph_corner_mm` | -0.088 | 567 |
| `az_s_cos2_amp` | -0.071 | 567 |
| `az_sf_n1` | -0.071 | 567 |
| `az_n_cos2_amp` | -0.064 | 567 |
| `az_sf_b` | -0.060 | 567 |
| `az_a_sf_amp` | +0.044 | 567 |
| `az_sf_n2` | -0.044 | 567 |
| `az_sf_n3` | -0.027 | 567 |
| `n` | -0.024 | 567 |
| `az_a_cos_pow` | -0.021 | 567 |
| `az_a_cos_amp` | -0.012 | 567 |
| `morph_fixed` | +0.012 | 567 |

### Top-decile vs all (distribution shift)

| knob | mean all | mean top | shift (norm to bound width) |
|---|---:|---:|---:|
| `L_mm` | 217.8 | 309.4 | 0.220 |
| `s` | 0.5824 | 0.3588 | -0.149 |
| `a_deg` | 16.99 | 20.37 | 0.085 |
| `az_a_sf_amp` | 16.55 | 11.64 | -0.082 |
| `az_sf_b` | 0.7681 | 0.8218 | 0.067 |
| `az_n_cos2_amp` | 0.8704 | 1.192 | 0.064 |
| `az_sf_n2` | 17.23 | 18.89 | 0.059 |
| `az_a_cos_amp` | -11.54 | -9.284 | 0.056 |
| `az_sf_n3` | 15.51 | 16.9 | 0.050 |
| `k` | 2.121 | 1.894 | -0.048 |
| `morph_rate` | 3.771 | 3.463 | -0.041 |
| `az_a_cos_pow` | 10.67 | 10.13 | -0.030 |
| `morph_fixed` | 0.2182 | 0.2073 | -0.018 |
| `az_sf_n1` | 15.33 | 15.78 | 0.016 |
| `morph_corner_mm` | 33.82 | 34.98 | 0.015 |
| `n` | 6.613 | 6.512 | -0.011 |
| `az_s_cos2_amp` | 0.1662 | 0.165 | -0.002 |
| `a0_deg` | 1.2 | 1.2 | — |
| `aspect_ratio` | 1 | 1 | — |
| `az_sf_a` | 1 | 1 | — |
| `az_sf_m` | 4 | 4 | — |
| `exponent` | 2 | 2 | — |
| `morph_allow_shrinkage` | 0 | 0 | — |
| `morph_exponent` | 4 | 4 | — |
| `morph_height_mm` | 399 | 399 | — |
| `morph_target` | 1 | 1 | — |
| `morph_width_mm` | 399 | 399 | — |
| `q` | 0.996 | 0.996 | — |
| `r0_mm` | 25.4 | 25.4 | — |
| `s1` | 1.14 | 1.14 | — |
| `s2` | 0.025 | 0.025 | — |

### Global surrogate (RandomForestRegressor, R² OOS 0.49)

| knob | permutation importance (ΔJ) |
|---|---:|
| `L_mm` | 1.276 ± 0.19 |
| `morph_rate` | 0.2279 ± 0.059 |
| `az_a_sf_amp` | 0.1567 ± 0.038 |
| `a_deg` | 0.07013 ± 0.019 |
| `k` | 0.05725 ± 0.011 |
| `s` | 0.02774 ± 0.0061 |
| `morph_fixed` | 0.01975 ± 0.019 |
| `morph_corner_mm` | 0.01291 ± 0.017 |
| `az_s_cos2_amp` | 0.01053 ± 0.005 |
| `n` | 0.006918 ± 0.0029 |
| `az_n_cos2_amp` | 0.00408 ± 0.0037 |
| `az_sf_b` | 0.002616 ± 0.0025 |
| `az_a_cos_amp` | 0.002393 ± 0.0025 |
| `a0_deg` | 0 ± 0 |
| `aspect_ratio` | 0 ± 0 |
| `az_sf_a` | 0 ± 0 |
| `az_sf_m` | 0 ± 0 |
| `exponent` | 0 ± 0 |
| `morph_allow_shrinkage` | 0 ± 0 |
| `morph_exponent` | 0 ± 0 |
| `morph_height_mm` | 0 ± 0 |
| `morph_target` | 0 ± 0 |
| `morph_width_mm` | 0 ± 0 |
| `q` | 0 ± 0 |
| `r0_mm` | 0 ± 0 |
| `s1` | 0 ± 0 |
| `s2` | 0 ± 0 |
| `az_sf_n2` | -0.001918 ± 0.0028 |
| `az_a_cos_pow` | -0.002833 ± 0.0033 |
| `az_sf_n3` | -0.003178 ± 0.0076 |
| `az_sf_n1` | -0.004613 ± 0.0048 |


----

## g6 (sensitivity)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\sensitivity_g6\sensitivity.json

# Sensitivity

Run `20261112T113047Z-screen-24053e` (family `FREEFORM`, objective v6, 142 valid rows).
Spearman on optimizer samples is biased; the surrogate importance below is the
unbiased companion (productionised from `study_2026-11-12/sensitivity_analysis.py`).

| knob | rho | n |
|---|---:|---:|
| `g_stop_deg` | -0.630 | 142 |
| `g_fc_hz` | +0.354 | 142 |
| `g_T` | +0.008 | 142 |

### Top-decile vs all (distribution shift)

| knob | mean all | mean top | shift (norm to bound width) |
|---|---:|---:|---:|
| `g_stop_deg` | 227.7 | 238.5 | 0.090 |
| `g_fc_hz` | 633.9 | 614.8 | -0.032 |
| `g_T` | 0.7341 | 0.7285 | -0.008 |

### Global surrogate (RandomForestRegressor, R² OOS 0.97)

| knob | permutation importance (ΔJ) |
|---|---:|
| `g_fc_hz` | 1.689 ± 0.08 |
| `g_T` | 0.05072 ± 0.0098 |
| `g_stop_deg` | 0.003955 ± 0.0029 |


----

## g1 (links)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\links_g1\links.json

# Link candidates

Run `20261030T170642Z-screen-fbab4f` — top-decile rows: 57.

Knob pairs with |rho| >= 0.6 (top-decile), with the proposed linear link:

| a | b | rho | scale | offset | R² |
|---|---|---:|---:|---:|---:|
| `a_deg` | `az_a_sf_amp` | -0.647 | -0.6127 | 24.12 | 0.427

### Proposed `links:` entries (Group B)

- `az_a_sf_amp = -0.6127 * a_deg + 24.12` (R² 0.427)


----

## g1 (walls)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\walls_g1\walls.json

# Bound walls

Run `20261030T170642Z-screen-fbab4f` — 57 top-decile rows; a knob is a wall at 50% of the top decile within 3% of a bound.

| knob | lo | hi | frac at lo | frac at hi | wall |
|---|---:|---:|---:|---:|---|
| `morph_fixed` | 0.0 | 0.6 | 0.11 | 0.02 |  |
| `k` | 0.3 | 5.0 | 0.07 | 0.02 |  |
| `s` | 0.0 | 1.5 | 0.09 | 0.00 |  |
| `az_a_cos_pow` | 2.0 | 20.0 | 0.05 | 0.00 |  |
| `az_sf_n2` | 2.0 | 30.0 | 0.00 | 0.05 |  |
| `a_deg` | 0.0 | 40.0 | 0.00 | 0.02 |  |
| `az_a_sf_amp` | -10.0 | 50.0 | 0.02 | 0.00 |  |
| `az_s_cos2_amp` | -0.3 | 0.5 | 0.00 | 0.02 |  |
| `az_sf_n1` | 2.0 | 30.0 | 0.00 | 0.02 |  |
| `az_sf_n3` | 2.0 | 30.0 | 0.00 | 0.02 |  |
| `morph_corner_mm` | 0.0 | 80.0 | 0.00 | 0.02 |  |
| `n` | 1.0 | 10.0 | 0.00 | 0.02 |  |
| `L_mm` | 104.0 | 520.0 | 0.00 | 0.00 |  |
| `az_a_cos_amp` | -30.0 | 10.0 | 0.00 | 0.00 |  |
| `az_n_cos2_amp` | -2.0 | 3.0 | 0.00 | 0.00 |  |
| `az_sf_b` | 0.4 | 1.2 | 0.00 | 0.00 |  |
| `morph_rate` | 0.5 | 8.0 | 0.00 | 0.00 |  |

### Proposed box changes (Group B `narrow` inputs)

- **narrow** `L_mm` -> [187.439764029, 453.0903105743]: top-decile span padded 5%
- **narrow** `a_deg` -> [1.8495270379000002, 40.0]: top-decile span padded 5%
- **narrow** `az_a_cos_amp` -> [-29.0517383952, 7.6505460157]: top-decile span padded 5%
- **narrow** `az_a_sf_amp` -> [-10.0, 35.417780512]: top-decile span padded 5%
- **narrow** `az_n_cos2_amp` -> [-1.6483192066, 3.0]: top-decile span padded 5%
- **narrow** `az_s_cos2_amp` -> [-0.25498574640000005, 0.5]: top-decile span padded 5%
- **narrow** `az_sf_n3` -> [3.1761965629999995, 30.0]: top-decile span padded 5%
- **narrow** `n` -> [1.3639379299, 10.0]: top-decile span padded 5%
- **narrow** `s` -> [0.0, 1.1712424413]: top-decile span padded 5%

_proposals are inputs for Group B 'narrow', never automatic config changes_


----

## g6 (walls)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\walls_g6\walls.json

# Bound walls

Run `20261112T113047Z-screen-24053e` — 15 top-decile rows; a knob is a wall at 50% of the top decile within 3% of a bound.

| knob | lo | hi | frac at lo | frac at hi | wall |
|---|---:|---:|---:|---:|---|
| `g_fc_hz` | 600.0 | 1200.0 | 0.87 | 0.00 | lo |
| `g_stop_deg` | 120.0 | 240.0 | 0.00 | 0.87 | hi |
| `g_T` | 0.3 | 1.0 | 0.00 | 0.00 |  |

### Proposed box changes (Group B `narrow` inputs)

- **narrow** `g_T` -> [0.6865265537999999, 0.7768846393000001]: top-decile span padded 5%
- **widen_lo** `g_fc_hz` -> [540.0, 1200.0]: 87% of the top decile within 3% of lo; widen candidate (-10%), gated by physical safety
- **widen_hi** `g_stop_deg` -> [120.0, 264.0]: 87% of the top decile within 3% of hi; widen candidate (+10%), gated by physical safety

_proposals are inputs for Group B 'narrow', never automatic config changes_


----

## g1 (term_balance)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\term_balance_g1\term_balance.json

# Term balance

Brief `atlas__core_law` (objective v4, 567 valid rows, 57 top-decile).

Share of J per term (median / mean over valid rows):

| term | share median | share mean | weight | tolerance |
|---|---:|---:|---:|---:|
| `cov` | 0.337 | 0.343 | 1.0 | 2.0 |
| `dislope` | 0.305 | 0.305 | 0.5 | 9.0 |
| `diag` | 0.145 | 0.149 | 0.5 | 2.0 |
| `di` | 0.083 | 0.092 | 0.3 | 0.4 |
| `distd` | 0.045 | 0.048 | 0.5 | 2.0 |
| `flat` | 0.037 | 0.049 | 0.5 | 1.5 |
| `rip` | 0.008 | 0.014 | 1.0 | 1.0 |
| `load` | 0.000 | 0.000 | 0.0 | 0.3 |

Raw-unit values of the top-decile designs (recalibration inputs):

| term | median | p10 | p90 |
|---|---:|---:|---:|
| `cov` | 1.72 | 1.215 | 2.569 |
| `rip` | 0.1429 | 0.1063 | 0.2658 |
| `di` | 0.707 | 0.3713 | 0.9459 |
| `dislope` | 13.23 | 3.111 | 26.82 |
| `flat` | 1.071 | 0.4739 | 1.818 |
| `load` | 0 | 0 | 0 |
| `distd` | 1.263 | 0.7289 | 1.523 |
| `diag` | 1.547 | 0.8709 | 2.76 |


----

## g6 (term_balance)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\term_balance_g6\term_balance.json

# Term balance

Brief `lecleach_rollback` (objective v6, 142 valid rows, 15 top-decile).

Share of J per term (median / mean over valid rows):

| term | share median | share mean | weight | tolerance |
|---|---:|---:|---:|---:|
| `di_rise` | 0.758 | 0.706 | 0.4 | 4.0 |
| `distd` | 0.154 | 0.145 | 0.3 | 2.0 |
| `cov_pat` | 0.056 | 0.052 | 0.3 | 15.0 |
| `flat` | 0.014 | 0.044 | 0.5 | 1.5 |
| `z_smooth` | 0.014 | 0.019 | 0.8 | 0.15 |
| `rip` | 0.004 | 0.004 | 0.8 | 2.0 |
| `load_near` | 0.000 | 0.030 | 1.0 | 0.25 |
| `diag` | 0.000 | 0.000 | 0.0 | 4.5 |

Raw-unit values of the top-decile designs (recalibration inputs):

| term | median | p10 | p90 |
|---|---:|---:|---:|
| `load_near` | 0 | 0 | 0 |
| `z_smooth` | 0.002924 | 0.002396 | 0.003661 |
| `flat` | 0.05242 | 0.04117 | 0.05869 |
| `rip` | 0.01557 | 0.0154 | 0.01581 |
| `cov_pat` | 4.342 | 4.3 | 4.37 |
| `di_rise` | 11.73 | 11.71 | 11.76 |
| `distd` | 1.596 | 1.595 | 1.597 |
| `diag` | 0 | 0 | 0 |


----

## g1 (fidelity)

Status: **ok**
- JSON: C:\Users\hunte\Hrns\oc-wt\AN\scratch\report_day_partial\fidelity_g1\fidelity.json

# Screen-vs-verify fidelity

Run `20261030T170642Z-screen-fbab4f` (brief `atlas__core_law`, objective v4): 12 paired design(s).

- median verify-vs-screen bias: **29.2%**
- Spearman (all paired designs): **0.6643356643356644**
- Spearman (screen top 5 only): **0.49999999999999994**

| design | J screen | J verify | bias % |
|---|---:|---:|---:|
| `030b009edd09` | 2.4075 | 3.2615 | +35.5% |
| `132a6a03166b` | 2.2310 | 2.8881 | +29.5% |
| `2030b0308599` | 2.9482 | 3.6640 | +24.3% |
| `2971ee4eaa85` | 2.4170 | 3.1252 | +29.3% |
| `2b1810253691` | 2.1283 | 3.0204 | +41.9% |
| `8c42018fe94a` | 2.7106 | 3.4870 | +28.6% |
| `a2e81e969ded` | 2.4615 | 3.1578 | +28.3% |
| `a54aa0ce6d76` | 2.8438 | 3.6724 | +29.1% |
| `aab4cd83ff29` | 2.3513 | 3.0404 | +29.3% |
| `aef4cba05731` | 2.8742 | 2.9797 | +3.7% |
| `ca8b31e06f97` | 2.2953 | 2.8105 | +22.4% |
| `ef60bef416f0` | 2.3320 | 3.1251 | +34.0% |

_bias = (J_verify - J_screen)/J_screen * 100; top-5 agreement is the screen's own ranking ability among its finalists_


----


---

## Appendix — additional CPU-only analyses (2026-11-12)

### A.7 lane parity (reconstructed per-backend pair)

**PASS (CP-7b): 5/5 compared designs within 0.2 dB**, max |dSPL| **0.0356 dB**, |dJ| <= 3.4e-5.
The source run's `verify/` was mixed by the pre-#44 shared-directory collision; the per-backend
responses were reconstructed read-only from `cache_cpu/solve/<key>` and `cache/solve/<key>` for the
same 5 designs. Raw: `oc-wt/G/scratch/lane_parity_2026-11-12/report/lane_parity.{json,md}`.

### Fidelity census (24/24 verify-bearing runs)

| run | paired designs | median screen bias | Spearman (all) | Spearman (top 5) |
|---|---:|---:|---:|---:|
| `20261030T170642Z-screen-fbab4f` (core_law) | 12 | 29.2% | 0.664 | 0.500 |
| `20261030T111108Z-screen-377bbe` (ath_core) | 10 | 48.9% | 0.600 | 0.400 |
| `elites_20261030_hypex` | 17 | 17.9% | 0.993 | 1.000 |

All 24 runs ran cleanly; the per-run JSON/MD/PNGs are in `oc-wt/AN/scratch/fidelity_census/`.
The policy implication is the C.4 one: verify the top 15–20 and rank finalists by verify J, not
screen J.

### Seed variance (`freeform_sculpt`, equal budget)

The equal-budget group is **25 seeds 5101–5125** (151 rows each), not 26. The 26th run
(`20261023T201245Z-screen-32f5b5`, seed 1234, 777 rows) is at a different budget.

- median best J **18.58868427480999**; spread (max-min) **4.780348414761317** (25.7% of median);
  bootstrap 95% CI of median [18.41349804684173, 19.18579587078396].
- The mixed 26-run group gives spread 6.212850767307559; it is **not** a seed-variance estimate.
- Outputs: `oc-wt/AN/scratch/seedvar_freeform25eq/` (clean) and `...26b/` (mixed).

### D.3 `dataset_cpu` merge — dry run

The A.7 parity report is PASS. `merge_lane_dataset.py --src dataset_cpu --dst dataset --parity
<A.7 json>` reports **237 rows in 1 shard, all `beat_cpu`, 0 already present, 0 non-CPU**; dry run
writes nothing. **Apply is owner-gated and must wait until the GPU queue stops writing `dataset/`.**
Raw: `oc-wt/AN/scratch/d3_dryrun_2026-11-12.txt`.

### GPU queue state at ~16:53

`g1b_core_law_resume_tail` 1001 evals (best J 2.12827), `g1c_verify_core_law_top10` 17 verify
evals; `g2_core_law_seed1031` was at **241/300** and active. `g3`–`g9` remain queued
(`runs/nights/gpu_day_2026-11-12_cont.yaml`). The final report will include them.
