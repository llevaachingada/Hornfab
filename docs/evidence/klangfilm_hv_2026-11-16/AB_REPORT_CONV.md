# Klangfilm-Lame H/V Stage A - controlled acoustic A/B

**Scope.** BEM runs sharing mesh policy, source cap, solver and frequency grid. The only difference between arms is the intended throat-angle key: `A1` = H-plane only (theta_H 9.4631 -> 14.0 deg, theta_V pinned at its measured base), `A2` = V-plane only (theta_V 9.4378 -> 5.0 deg, theta_H pinned at its measured base). `A0` is the incumbent; its geometry array is bit-identical to `klangfilm-lame-v1` at blend 0.

Scores under the smooth and CD policies are reported side by side but **never compared to each other**: the same stored responses are re-scored through the canonical replay path.

## A0 reuse gate

- cached run `runs\20261116T205942Z-screen-8b22b5` design `786caa6b08d7` (status `running`)
- geometry array equal to legacy: **True**, grid sha256 `7e80214c3b280209`
- same brief path: **True**; blocks equal: {'driver': True, 'envelope': True, 'grid': True, 'mesh': True, 'objective': True, 'solve': True, 'target': True, 'weights': True}
- library SHAs equal: **False** (cached `{'hornlab_beat_bem': '38e5b1f8ca840ebf6351c54611a08fedb1a0750f', 'hornlab_bempp_bem': '8e6910602ece9abb2e9ce0db7a637f4bedf17f53', 'hornlab_mesher': '55da4f46d662d8dcd7a9f94a609eeea4009fcd62', 'hornlab_plots': '9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44', 'hornlab_search': '0cd9543474dde441dce811c2f18c52dbee6ad905'}`, now `{'hornlab_beat_bem': '38e5b1f8ca840ebf6351c54611a08fedb1a0750f', 'hornlab_bempp_bem': '8e6910602ece9abb2e9ce0db7a637f4bedf17f53', 'hornlab_mesher': '55da4f46d662d8dcd7a9f94a609eeea4009fcd62', 'hornlab_plots': '9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44', 'hornlab_search': '7f7637e97fcdd7e1246032694a9e2ab0545f1733'}`)
- decision: `reuse_a0 = False`

## A0 incumbent

- run `C:\Users\hunte\Hrns\hornlab-search\runs\20261117T015442Z-screen-0afda0`, design `a01be912716b`, design.json sha256 `a84a8221d5bd871e`
- backend beat_cuda, dofs 7449, tris 14542, quadrants 1, angles 73, balloon [16, 32], solve 52.83645419997629 s
- -6 dB multi-lobe bins H/V: **0/0**; cut-limit saturated bins H/V: 3/5
- DI range 4.54 dB, variance 2.160 dB^2, slope 8.41 dB/dec
- off-axis wobble (|dSPL| per freq step, -25/0/+25 deg) H [0.981093352733647, 0.7819729066973495, 0.9810933525263689], V [1.3202950546900891, 0.7819729066973495, 1.3202950634068842]

| band (bins) | BW_H mean | BW_V mean | DI mean | ripple H/V | sidelobe H/V | |Z| ours |
|---|---|---|---|---|---|---|
| 700-1200 Hz (2) | 97.6 | 143.3 | 7.3 | 1.4 / 0.3 | -2.5 / -1.3 | 1.0 |
| 1.2-5.6 kHz (9) | 69.8 | 72.3 | 11.6 | 2.4 / 1.2 | -4.8 / -4.9 | 1.0 |
| 5.6-8 kHz (2) | 63.0 | 45.0 | 13.9 | 3.2 / 2.4 | -5.5 / -9.1 | 1.0 |

## a0epw9

- run `C:\Users\hunte\Hrns\hornlab-search\runs\20261117T063719Z-screen-47260f`, design `a01be912716b`, design.json sha256 `a84a8221d5bd871e`
- backend beat_cuda, dofs 16394, tris 32262, quadrants 1, angles 73, balloon [16, 32], solve 239.98603610001737 s
- -6 dB multi-lobe bins H/V: **0/0**; cut-limit saturated bins H/V: 3/5
- DI range 4.56 dB, variance 2.174 dB^2, slope 8.42 dB/dec
- off-axis wobble (|dSPL| per freq step, -25/0/+25 deg) H [0.9804756080301069, 0.7754292017338333, 0.9804754637093073], V [1.3133396446682681, 0.7754292017338333, 1.3133396087597022]

| band (bins) | BW_H mean | BW_V mean | DI mean | ripple H/V | sidelobe H/V | |Z| ours |
|---|---|---|---|---|---|---|
| 700-1200 Hz (2) | 97.6 | 143.3 | 7.3 | 1.4 / 0.3 | -2.5 / -1.3 | 1.0 |
| 1.2-5.6 kHz (9) | 69.7 | 72.2 | 11.7 | 2.5 / 1.2 | -4.8 / -4.9 | 1.0 |
| 5.6-8 kHz (2) | 63.0 | 45.3 | 13.9 | 3.2 / 2.4 | -5.4 / -9.0 | 1.0 |

## b3epw9

- run `C:\Users\hunte\Hrns\hornlab-search\runs\20261117T064133Z-screen-6d2651`, design `7a53202d1a5e`, design.json sha256 `2cd43964dd96faeb`
- backend beat_cuda, dofs 6757, tris 13091, quadrants 1, angles 73, balloon [16, 32], solve 48.92329619999509 s
- -6 dB multi-lobe bins H/V: **0/0**; cut-limit saturated bins H/V: 2/3
- DI range 4.01 dB, variance 1.177 dB^2, slope 8.60 dB/dec
- off-axis wobble (|dSPL| per freq step, -25/0/+25 deg) H [0.946343432241312, 0.8321007599103973, 0.9463435525881816], V [2.4298238743278566, 0.8321007599103973, 2.429824041850007]

| band (bins) | BW_H mean | BW_V mean | DI mean | ripple H/V | sidelobe H/V | |Z| ours |
|---|---|---|---|---|---|---|
| 700-1200 Hz (2) | 67.1 | 103.4 | 9.9 | 2.7 / 0.5 | -5.1 / -2.3 | 0.9 |
| 1.2-5.6 kHz (9) | 65.2 | 47.2 | 13.7 | 3.0 / 2.4 | -5.1 / -9.0 | 1.0 |
| 5.6-8 kHz (2) | 47.9 | 40.6 | 15.5 | 4.5 / 3.5 | -8.5 / -11.2 | 1.0 |

## Axis authority (mean -6 dB beamwidth change vs A0)

| arm | band | dBW_H | dBW_V | max |dBW_H| | max |dBW_V| |
|---|---|---|---|---|---|
| a0epw9 | 700-1200 Hz | -0.0 | -0.0 | 0.0 | 0.0 |
| a0epw9 | 1.2-5.6 kHz | -0.1 | -0.0 | 0.4 | 0.0 |
| a0epw9 | 5.6-8 kHz | +0.0 | +0.2 | 0.2 | 0.5 |
| b3epw9 | 700-1200 Hz | -30.5 | -39.9 | 32.3 | 42.4 |
| b3epw9 | 1.2-5.6 kHz | -4.6 | -25.0 | 22.5 | 45.0 |
| b3epw9 | 5.6-8 kHz | -15.1 | -4.5 | 20.1 | 7.5 |

## Decision (Phase B gate, computed from the table above)

Rule fixed before the solves: a Phase B seed is worth optimizing only if the mean -6 dB beamwidth in 1.2-5.6 kHz lands within +-10 deg of 80 deg H / 50 deg V, `Var(DI)` over that band drops by >= 25 % versus A0, no plane gains a second -6 dB lobe, and `load` does not get worse.

- **a0epw9**: BW 69.7 H / 72.2 V (target 80/50, within +-10: False); Var(DI) 2.174 vs A0 2.160 (drop -0.6 %, >=25 %: False); multi-lobe bins 0/0 (ok: True); load 0.775 vs A0 0.777 (ok: True).
  - smooth J 8.437406596645564 ; CD J 14.227139154426995
  - gate: **FAIL**
- **b3epw9**: BW 65.2 H / 47.2 V (target 80/50, within +-10: False); Var(DI) 1.177 vs A0 2.160 (drop 45.5 %, >=25 %: True); multi-lobe bins 0/0 (ok: True); load 0.000 vs A0 0.777 (ok: True).
  - smooth J 6.572710147570006 ; CD J 14.836864190844073
  - gate: **FAIL**

**No constant-directivity claim is made even on a pass**: the gate is a go/no-go for spending optimization time, not evidence of an 80x50 pattern. The driver source cap is still the existing assumption.

## Canonical v7 term contributions (same responses, two policies)

### a0 - smooth policy

- J = **8.43812590231321** (exact_complete), stored J 8.43812590231321, parity delta 0.0
- score id `032a947008a0a48a`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\a0.yaml`

| term | value |
|---|---|
| cov | 1.1246500601543548 |
| rip | 0.047237618391523184 |
| di | 0.0 |
| dislope | 0.9150926909154159 |
| flat | 0.3933165692593687 |
| load | 0.7774259477131893 |
| distd | 1.1315751531903604 |
| diag | 4.142577267126948 |
| flat_cv | 0.10290888019173401 |
| penalty | 0.0 |
| total | 8.43812590231321 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 514.2645835088722 |
| lfp50_hz | 571.8910781557869 |
| rez_min_from_fx | 0.7620557964045518 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### a0 - cd policy

- J = **14.207990584484536** (exact_complete), stored J 8.43812590231321, parity delta None
- score id `6dd5e73a609966a2`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\ab_cd_policy.yaml`

| term | value |
|---|---|
| cov | 3.5839348646903226 |
| rip | 0.047237618391523184 |
| di | 10.482910705583008 |
| dislope | 1.456539292488901 |
| flat | 0.3933165692593687 |
| load | 0.7774259477131893 |
| distd | 0.5276298206042861 |
| diag | 4.634597574402137 |
| flat_cv | 0.10290888019173401 |
| penalty | 0.0 |
| total | 14.207990584484536 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 514.2645835088722 |
| lfp50_hz | 571.8910781557869 |
| rez_min_from_fx | 0.7620557964045518 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### a0epw9 - smooth policy

- J = **8.437406596645564** (exact_complete), stored J 8.437406596645564, parity delta 0.0
- score id `27d8fe8bdda72399`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\a0_epw9.yaml`

| term | value |
|---|---|
| cov | 1.1272064318096071 |
| rip | 0.047201824280022134 |
| di | 0.0 |
| dislope | 0.9136390492483658 |
| flat | 0.39925286354706274 |
| load | 0.7751979940818692 |
| distd | 1.1317652012619703 |
| diag | 4.142104465546253 |
| flat_cv | 0.10066519864394476 |
| penalty | 0.0 |
| total | 8.437406596645564 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 514.0263850859596 |
| lfp50_hz | 571.3955077106364 |
| rez_min_from_fx | 0.7602182684333735 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### a0epw9 - cd policy

- J = **14.227139154426995** (exact_complete), stored J 8.437406596645564, parity delta None
- score id `efe59d134688ed25`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\ab_cd_policy.yaml`

| term | value |
|---|---|
| cov | 3.6002113063667935 |
| rip | 0.047201824280022134 |
| di | 10.478424862000905 |
| dislope | 1.4562029371579135 |
| flat | 0.39925286354706274 |
| load | 0.7751979940818692 |
| distd | 0.5278183933545574 |
| diag | 4.6405968068453705 |
| flat_cv | 0.10066519864394476 |
| penalty | 0.0 |
| total | 14.227139154426995 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 514.0263850859596 |
| lfp50_hz | 571.3955077106364 |
| rez_min_from_fx | 0.7602182684333735 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### b3epw9 - smooth policy

- J = **6.572710147570006** (exact_complete), stored J 6.572710147570006, parity delta 0.0
- score id `62c42f7050a8ef1a`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\b3_epw9.yaml`

| term | value |
|---|---|
| cov | 1.1435141477455233 |
| rip | 0.4189731694009074 |
| di | 0.0 |
| dislope | 0.1820813659154119 |
| flat | 0.5228412750376058 |
| load | 0.0 |
| distd | 0.9373016659212354 |
| diag | 3.1484752318679616 |
| flat_cv | 0.48094392920016316 |
| penalty | 0.0 |
| total | 6.572710147570006 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 348.7291713094425 |
| lfp50_hz | 473.50823011195115 |
| rez_min_from_fx | 0.732337854439519 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### b3epw9 - cd policy

- J = **14.836864190844073** (exact_complete), stored J 6.572710147570006, parity delta None
- score id `ab861208cb93ae10`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\ab_cd_policy.yaml`

| term | value |
|---|---|
| cov | 4.2865556159644855 |
| rip | 0.4189731694009074 |
| di | 8.339497329156785 |
| dislope | 0.7469213467181341 |
| flat | 0.5228412750376058 |
| load | 0.0 |
| distd | 0.4027716800530587 |
| diag | 5.938814453268016 |
| flat_cv | 0.48094392920016316 |
| penalty | 0.0 |
| total | 14.836864190844073 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 348.7291713094425 |
| lfp50_hz | 473.50823011195115 |
| rez_min_from_fx | 0.732337854439519 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

## Reading rules

- Wall angles are geometry, not beamwidth. No result here shows that theta_H/theta_V map to horizontal/vertical coverage.
- The driver source cap is the existing simulation assumption, unchanged by this comparison.
- J is comparable only within one policy; the smooth brief is not a CD score.
- A band row with 1 bin is a single frequency, not a band statistic.
