# X4 — parameter-space intelligence: preliminary, incomplete

Recorded 2026-11-16 at HEAD `207f97a29e2f2f31a366da95e882f9b48761ab00`. No solves, mesh builds, changes to configs or tracked files. The X1 sampler is experimental and its round-trip contract has not been validated; all geometric numbers below are provisional. This is not sufficient evidence for parameter-space changes.

## Geometric checks

The X1 `sample` routine was applied to CPU-native materialized surfaces for two of the five desired lanes: 11 designs per lane (the best stored J and ten seeded random others), 31 azimuth × 65 arc stations, 10 mm materializer resolution. Each searched knob was perturbed one-sided by 1% of its configured range, with direction reversed at the upper bound. Movement is RMS Euclidean point displacement, in mm; these are step sizes, not derivatives or full-range effects. Each Jacobian column was normalized to unit norm before SVD, with numerical rank defined by singular value > 10⁻⁶ of the largest. Near-correspondences use absolute cosine > .95; negative cosine is also counted. Coordinate resampling, changing correspondence and materializer approximation can affect these measurements. Full per-design singular values and pairs are in `.x4/geometry.json`.

| Lane | Designs | Knobs | Normalized numerical rank range | Examples of 1%-step median movement |
|---|---:|---:|---:|---|
| `hl__osse_rrect_fold_warm_v7` | 11 | 18 | 18–18 | L .223 mm; a0 .002; fold-V angle .168 |
| `hl__ext_throat_hvlaw_v7` | 11 | 8 | 8–8 | L 1.233 mm; throat-extension length 1.052; throat-extension angle .049 |

In the fold-warm samples, pairs whose normalized columns exceeded .95 in absolute cosine at least once include `a_deg`/`k`, `n`/`s`, `n`/`q`, `q`/`s`, and `az_a_cos_amp`/`az_fold_h_deg`. No such pair occurred among the eight ext-throat knobs at these samples. This is a local observation, not a link recommendation. The raw sampler has not been demonstrated convergent for each knob and the necessary box-corner, throat-region, maxima and constraint-margin checks are missing. A low RMS movement for a 1%-range step does not meet the brief’s definition of inactivity everywhere.

The three required GRID/GEN-FF lane geometry Jacobians have not been implemented: X1 reported resolver failures for some Klangfilm samples, and it is not yet established how to perturb generator knobs while preserving the intended recipe. No meshes were built. Known conditional recoveries (`n/q` at `s=0`, `s1/s2`, morph target/exponent, guiding curve, `rot_deg`) were not systematically tested. No labels or agreement rates from Parts C/D are established.

## Limitations and permitted use

- The brief requires five-lane full-surface perturbations, acoustic bootstrap evidence, conditional corner checks and margin-based pinned labels; the work so far does not complete those gates.
- Recommend `fix` only for inactivity confirmed at relevant box corners; recommend a link only for geometrically confirmed coupling. A bound widening is a proposal only. Geometrically active but acoustically weak knobs stay free and can be flagged for later dimension reduction. No such recommendation is supported here.
- Success/failure thresholds are **not assessable**. Raw scripts and intermediate data are under `.x4/`.

## Exploratory acoustic importance

For each lane and target, five bootstrap training resamples were fit with ExtraTrees; each replicate uses a held-out random 20% from the same time subset and five permutation repeats. Entries are medians of held-out R² drop, with the range across the five bootstrap replicates in parentheses. Negative values indicate degradation in estimated importance, not evidence of inactivity. H and V targets are mean squared differences from 80° and 50° over frequencies ≥700 Hz, not full objective components. Sampling is clustered and models/importance are associational. Early and late halves are separately fit; no geometric labels, margin checks or classification agreement are inferred.


### hl__osse_rrect_fold_warm_v7 (n=248)

| Knob | J median [min,max] | H coverage error | V coverage error |
|---|---:|---:|---:|
| L_mm | 0.015 [0.005, 0.061] | 0.144 [0.130, 0.237] | 0.186 [0.165, 0.338] |
| a0_deg | 0.002 [-0.005, 0.008] | -0.003 [-0.009, 0.006] | -0.002 [-0.004, 0.006] |
| a_deg | 0.012 [0.002, 0.018] | 0.017 [0.010, 0.025] | 0.003 [-0.003, 0.008] |
| az_a_cos_amp | 0.022 [0.012, 0.027] | 0.005 [0.004, 0.010] | -0.002 [-0.008, 0.007] |
| az_a_cos_pow | -0.001 [-0.013, 0.001] | 0.002 [0.001, 0.015] | 0.001 [-0.016, 0.003] |
| az_s_cos2_amp | 0.004 [0.001, 0.009] | 0.001 [-0.003, 0.003] | 0.002 [-0.002, 0.012] |
| k | -0.004 [-0.004, 0.001] | 0.007 [-0.003, 0.029] | 0.001 [-0.002, 0.001] |
| morph_corner_mm | 0.000 [-0.012, 0.004] | 0.002 [0.000, 0.011] | 0.003 [-0.005, 0.018] |
| morph_height_mm | 0.001 [-0.004, 0.004] | 0.003 [-0.007, 0.011] | 0.003 [0.001, 0.016] |
| morph_rate | -0.002 [-0.018, 0.013] | 0.001 [-0.003, 0.002] | 0.003 [0.002, 0.008] |
| morph_width_mm | 0.001 [-0.004, 0.009] | 0.009 [-0.006, 0.019] | 0.002 [-0.000, 0.011] |
| n | 0.004 [-0.005, 0.005] | -0.002 [-0.004, 0.004] | 0.000 [-0.003, 0.007] |
| q | 0.010 [0.001, 0.017] | 0.002 [-0.000, 0.007] | -0.001 [-0.005, 0.006] |
| s | 0.004 [-0.021, 0.008] | 0.004 [-0.013, 0.008] | 0.002 [0.001, 0.005] |
| az_fold_v_deg | 0.500 [0.310, 0.535] | 0.669 [0.485, 0.762] | 0.639 [0.453, 0.912] |
| az_fold_v_width_deg | 0.120 [0.015, 0.150] | 0.007 [0.002, 0.008] | 0.151 [0.041, 0.308] |
| az_fold_h_deg | 0.134 [0.072, 0.255] | 0.227 [0.169, 0.372] | -0.004 [-0.014, 0.004] |
| az_fold_h_width_deg | 0.006 [-0.001, 0.021] | 0.019 [0.016, 0.042] | -0.001 [-0.013, 0.009] |

J top-third early/late feature overlap: 5/6; descriptive ranking stability, not X4 Part D label agreement.

H top-third early/late feature overlap: 5/6; descriptive ranking stability, not X4 Part D label agreement.

V top-third early/late feature overlap: 3/6; descriptive ranking stability, not X4 Part D label agreement.

### hl__ext_throat_hvlaw_v7 (n=137)

| Knob | J median [min,max] | H coverage error | V coverage error |
|---|---:|---:|---:|
| a_deg | 0.778 [0.559, 1.342] | 0.575 [0.433, 0.845] | 0.423 [0.288, 0.642] |
| L_mm | 0.006 [-0.002, 0.017] | 0.025 [0.006, 0.148] | 0.163 [0.130, 0.382] |
| s | 0.029 [-0.008, 0.042] | 0.027 [0.006, 0.055] | 0.062 [0.033, 0.121] |
| throat_ext_length_mm | 0.012 [-0.016, 0.019] | 0.001 [-0.008, 0.007] | 0.008 [-0.015, 0.016] |
| throat_ext_angle_deg | 0.008 [-0.017, 0.163] | 0.018 [-0.001, 0.145] | 0.007 [-0.021, 0.025] |
| az_a_cos_pow | 0.007 [0.000, 0.039] | 0.004 [-0.009, 0.029] | 0.015 [0.002, 0.063] |
| az_a_cos_amp | 0.103 [0.057, 0.187] | 0.298 [0.170, 0.358] | 0.012 [0.004, 0.032] |
| az_s_cos2_amp | -0.003 [-0.015, 0.008] | -0.011 [-0.016, 0.006] | 0.000 [-0.008, 0.017] |

J top-third early/late feature overlap: 2/3; descriptive ranking stability, not X4 Part D label agreement.

H top-third early/late feature overlap: 1/3; descriptive ranking stability, not X4 Part D label agreement.

V top-third early/late feature overlap: 3/3; descriptive ranking stability, not X4 Part D label agreement.

### hl__klangfilm_lame_curved_v1 (n=417)

| Knob | J median [min,max] | H coverage error | V coverage error |
|---|---:|---:|---:|
| g_fc_hz | 1.506 [1.348, 1.627] | 0.899 [0.841, 1.043] | 1.280 [1.216, 1.346] |
| g_aspect | 0.024 [0.014, 0.038] | 0.162 [0.151, 0.204] | 0.265 [0.235, 0.306] |
| g_lame_p | 0.002 [-0.004, 0.007] | 0.019 [0.009, 0.030] | 0.002 [-0.000, 0.006] |
| g_end_frac | 0.017 [0.012, 0.023] | 0.036 [0.030, 0.055] | 0.005 [0.004, 0.007] |
| g_rim_sweep_ratio | 0.073 [0.054, 0.102] | 0.296 [0.239, 0.398] | 0.019 [0.014, 0.024] |

J top-third early/late feature overlap: 2/2; descriptive ranking stability, not X4 Part D label agreement.

H top-third early/late feature overlap: 1/2; descriptive ranking stability, not X4 Part D label agreement.

V top-third early/late feature overlap: 2/2; descriptive ranking stability, not X4 Part D label agreement.

### hl__crowe_x_osse_cd_v7 (n=202)

| Knob | J median [min,max] | H coverage error | V coverage error |
|---|---:|---:|---:|
| g_a_h_deg | -0.002 [-0.008, 0.005] | 0.139 [0.070, 0.290] | 0.012 [-0.015, 0.030] |
| g_a_v_deg | 0.013 [-0.005, 0.048] | 0.001 [-0.002, 0.015] | 0.102 [0.075, 0.218] |
| g_L_mm | 0.343 [0.133, 0.501] | 0.017 [-0.023, 0.064] | 1.008 [0.845, 1.349] |
| g_s | 0.156 [0.102, 0.239] | 0.362 [0.207, 0.392] | 0.016 [0.005, 0.033] |
| g_n | 0.060 [0.011, 0.168] | 0.326 [0.094, 0.431] | 0.038 [0.009, 0.155] |
| g_r_lip_mm | 0.032 [-0.038, 0.119] | 0.002 [-0.013, 0.017] | 0.014 [0.001, 0.063] |
| g_wrap_deg | -0.000 [-0.023, 0.015] | 0.015 [-0.005, 0.030] | -0.002 [-0.005, 0.011] |
| g_sf_ab | -0.006 [-0.018, 0.018] | 0.031 [-0.025, 0.066] | -0.001 [-0.013, 0.009] |
| g_sf_amt | 0.034 [0.002, 0.040] | 0.156 [0.042, 0.201] | 0.003 [-0.002, 0.010] |

J top-third early/late feature overlap: 2/3; descriptive ranking stability, not X4 Part D label agreement.

H top-third early/late feature overlap: 3/3; descriptive ranking stability, not X4 Part D label agreement.

V top-third early/late feature overlap: 2/3; descriptive ranking stability, not X4 Part D label agreement.

### hl__biradial_es_style_v7 (n=309)

| Knob | J median [min,max] | H coverage error | V coverage error |
|---|---:|---:|---:|
| L_mm | 0.155 [0.075, 0.196] | 1.236 [1.144, 1.482] | 1.449 [1.284, 1.619] |
| h_a_deg | 0.144 [0.072, 0.216] | 0.022 [0.013, 0.044] | -0.002 [-0.003, 0.012] |
| v_a_deg | 0.032 [0.019, 0.041] | 0.001 [-0.000, 0.002] | 0.178 [0.162, 0.212] |
| h_rm_mm | 0.019 [0.005, 0.025] | 0.103 [0.091, 0.144] | -0.001 [-0.007, 0.012] |
| v_rm_mm | 0.056 [0.023, 0.081] | 0.000 [-0.003, 0.003] | 0.085 [0.058, 0.122] |
| h_n | 0.000 [-0.005, 0.014] | 0.000 [-0.001, 0.003] | 0.003 [0.001, 0.004] |
| v_n | 0.485 [0.283, 0.526] | 0.004 [0.001, 0.028] | 0.007 [-0.002, 0.022] |
| mouth_exponent | 0.055 [0.013, 0.143] | 0.052 [0.035, 0.057] | 0.008 [0.006, 0.015] |

J top-third early/late feature overlap: 2/3; descriptive ranking stability, not X4 Part D label agreement.

H top-third early/late feature overlap: 3/3; descriptive ranking stability, not X4 Part D label agreement.

V top-third early/late feature overlap: 3/3; descriptive ranking stability, not X4 Part D label agreement.

See `.x4/acoustic.py` and `.x4/acoustic.json` for complete reproducible results.

The acoustic tables include only numeric searched knobs present in the first eligible row and its recorded bounds; this selected 18 / 8 / 5 / 9 / 8 knobs respectively. Missing or conditional knobs and possible changes of bounds across runs need an explicit audit before interpreting omissions. Five sampled lanes do not cover every eligible lane in the data. These checks do not establish any classification or recommended fix, link, or bound change.

## Follow-up: five-lane exploratory Jacobians and conditionals

This section supersedes the earlier statement that GRID/GEN-FF Jacobians were not implemented. The same 1%-bound-range, one-sided finite difference and provisional X1 sampling protocol was run on five lanes spanning all three engine groups. For generated lanes, knobs were rematerialized with each original run config; every included baseline regenerated the archived design hash. Each table shows RMS displacement across surface sample points in mm, median and maximum across the 11 sampled designs, not maximum displacement at any point. Full singular values and per-design cosine pairs are in the JSON artifacts. Sampler fidelity, near-throat behavior and box-corner checks remain unverified.


### hl__osse_rrect_fold_warm_v7 (n=11, normalized ranks 18–18)

| Knob | Median movement (mm) | Maximum of design RMS (mm) |
|---|---:|---:|
| L_mm | 0.2234 | 0.2330 |
| a0_deg | 0.0023 | 0.0025 |
| a_deg | 0.0635 | 0.0702 |
| az_a_cos_amp | 0.0411 | 0.0501 |
| az_a_cos_pow | 0.0290 | 0.0388 |
| az_s_cos2_amp | 0.0046 | 0.0053 |
| k | 0.0336 | 0.0346 |
| morph_corner_mm | 0.0093 | 0.0232 |
| morph_height_mm | 0.0798 | 0.0832 |
| morph_rate | 0.0143 | 0.0329 |
| morph_width_mm | 0.0502 | 0.0516 |
| n | 0.0067 | 0.0132 |
| q | 0.0243 | 0.0283 |
| s | 0.0155 | 0.0173 |
| az_fold_v_deg | 0.1684 | 0.3267 |
| az_fold_v_width_deg | 0.0638 | 0.2037 |
| az_fold_h_deg | 0.1355 | 0.1823 |
| az_fold_h_width_deg | 0.0148 | 0.0884 |

Pairs exceeding absolute cosine .95 on at least one design: `a0_deg` / `k`, `a_deg` / `k`, `az_a_cos_amp` / `az_fold_h_deg`, `az_a_cos_pow` / `az_fold_v_width_deg`, `n` / `q`, `n` / `s`, `q` / `s`.

### hl__ext_throat_hvlaw_v7 (n=11, normalized ranks 8–8)

| Knob | Median movement (mm) | Maximum of design RMS (mm) |
|---|---:|---:|
| a_deg | 0.8943 | 0.9772 |
| L_mm | 1.2330 | 1.3267 |
| s | 0.3375 | 0.3910 |
| throat_ext_length_mm | 1.0518 | 1.0953 |
| throat_ext_angle_deg | 0.0487 | 0.0769 |
| az_a_cos_pow | 0.3130 | 0.6154 |
| az_a_cos_amp | 0.6238 | 0.7446 |
| az_s_cos2_amp | 0.2606 | 0.3052 |

Pairs exceeding absolute cosine .95 on at least one design: none.

### hl__ath_tritonia_landscape_v9 (n=11, normalized ranks 14–14)

| Knob | Median movement (mm) | Maximum of design RMS (mm) |
|---|---:|---:|
| L_mm | 1.6829 | 1.8838 |
| a0_deg | 0.0133 | 0.0161 |
| a_deg | 0.0196 | 0.1396 |
| k | 0.0115 | 0.0208 |
| az_a_cos_amp | 0.0047 | 0.0330 |
| az_fold_v_deg | 0.0023 | 0.0134 |
| az_fold_v_width_deg | 0.0032 | 0.0224 |
| morph_corner_mm | 0.0106 | 0.0111 |
| morph_height_mm | 0.6130 | 0.6293 |
| morph_rate | 0.1346 | 0.2215 |
| morph_width_mm | 0.5276 | 0.5950 |
| n | 0.0957 | 0.1582 |
| q | 0.0657 | 0.1560 |
| s | 0.0204 | 0.0387 |

Pairs exceeding absolute cosine .95 on at least one design: `a0_deg` / `a_deg`, `a0_deg` / `morph_rate`, `a_deg` / `k`, `a_deg` / `morph_rate`, `n` / `q`, `n` / `s`, `q` / `s`.

### hl__crowe_x_osse_cd_v7 (n=11, normalized ranks 9–9)

| Knob | Median movement (mm) | Maximum of design RMS (mm) |
|---|---:|---:|
| g_a_h_deg | 0.1811 | 0.1906 |
| g_a_v_deg | 0.1596 | 0.1646 |
| g_L_mm | 0.6692 | 0.7025 |
| g_s | 0.2879 | 0.3351 |
| g_n | 0.1448 | 0.1785 |
| g_r_lip_mm | 0.2288 | 0.3131 |
| g_wrap_deg | 0.1592 | 0.2152 |
| g_sf_ab | 0.1150 | 0.1951 |
| g_sf_amt | 0.1085 | 0.1321 |

Pairs exceeding absolute cosine .95 on at least one design: `g_r_lip_mm` / `g_wrap_deg`.

### hl__biradial_es_style_v7 (n=11, normalized ranks 8–8)

| Knob | Median movement (mm) | Maximum of design RMS (mm) |
|---|---:|---:|
| L_mm | 0.5127 | 0.5177 |
| h_a_deg | 0.0485 | 0.0566 |
| v_a_deg | 0.0649 | 0.0836 |
| h_rm_mm | 0.0976 | 0.1047 |
| v_rm_mm | 0.3008 | 0.3231 |
| h_n | 0.0350 | 0.0525 |
| v_n | 0.0626 | 0.1269 |
| mouth_exponent | 0.1161 | 0.2500 |

Pairs exceeding absolute cosine .95 on at least one design: none.


### Conditional spot checks

On the best stored `hl__osse_rrect_fold_warm_v7` native design, varying the following at the stated condition produced zero pointwise displacement on the sampled surface: `n` and `q` at `s=0` (also forcing `s1=s2=0` and azimuthal s modulation to zero); `s1` when `s2=0`; `s2` when `s1=0`; morph width and morph rate when `morph_target=0`; morph exponent at target 1. Positive controls produced RMS movement of 1.052 mm for `n` at positive `s`, 56.533 mm for `s1` at positive `s2`, 2.679 mm for `s2` at positive `s1`, and 18.589 mm for morph exponent at target 3. The positive `q` control failed: `UnsupportedGeometryError`, axial chord still 8.77 times its limit at the 2,048-segment refinement ceiling. `guiding curve` replacement of `a_deg` and `rot_deg` coupling were not tested. These are single-design checks with experimental sampling and selected values, not a box-wide inactivity classification; actual settings and errors are recorded in `.x4/conditionals.py` and `.x4/conditionals.txt`.

### Reproducibility blockers

All 11 attempted rematerializations for each of `hl__klangfilm_lame_curved_v1`, `hl__crowe_panel_home_v7`, and `hl__rosse_rect_cd_v7` failed before sampling. Current `generated.materialize` reports `GeneratorError: unknown rows type` respectively `klangfilm_lame`, `crowe_panel`, and `rosse_rect`; the complete messages and rows are in `.x4/generated_geometry.json`, `.x4/generated_geometry_extra.json`, and `.x4/generated_geometry_fifth.json`. This is an adapter compatibility finding at the current code, not evidence of inactive knobs or bad archived designs.

The five-lane geometric quota is now sampled, but classification, constraint margins, per-point maxima, targeted near-throat weighting, corner scans, all conditional cases, all-lane acoustic evidence and Parts C/D agreement criteria are still incomplete. These data do not support an overall X4 pass/failure or any fix/link recommendation.
