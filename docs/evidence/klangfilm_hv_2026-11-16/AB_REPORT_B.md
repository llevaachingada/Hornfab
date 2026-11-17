# Klangfilm-Lame H/V Stage A - controlled acoustic A/B

**Scope.** BEM runs sharing mesh policy, source cap, solver and frequency grid. The only difference between arms is the intended throat-angle key: `A1` = H-plane only (theta_H 9.4631 -> 14.0 deg, theta_V pinned at its measured base), `A2` = V-plane only (theta_V 9.4378 -> 5.0 deg, theta_H pinned at its measured base). `A0` is the incumbent; its geometry array is bit-identical to `klangfilm-lame-v1` at blend 0.

Scores under the smooth and CD policies are reported side by side but **never compared to each other**: the same stored responses are re-scored through the canonical replay path.

## A0 reuse gate

- cached run `runs\20261116T205942Z-screen-8b22b5` design `786caa6b08d7` (status `running`)
- geometry array equal to legacy: **True**, grid sha256 `7e80214c3b280209`
- same brief path: **True**; blocks equal: {'driver': True, 'envelope': True, 'grid': True, 'mesh': True, 'objective': True, 'solve': True, 'target': True, 'weights': True}
- library SHAs equal: **False** (cached `{'hornlab_beat_bem': '38e5b1f8ca840ebf6351c54611a08fedb1a0750f', 'hornlab_bempp_bem': '8e6910602ece9abb2e9ce0db7a637f4bedf17f53', 'hornlab_mesher': '55da4f46d662d8dcd7a9f94a609eeea4009fcd62', 'hornlab_plots': '9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44', 'hornlab_search': '0cd9543474dde441dce811c2f18c52dbee6ad905'}`, now `{'hornlab_beat_bem': '38e5b1f8ca840ebf6351c54611a08fedb1a0750f', 'hornlab_bempp_bem': '8e6910602ece9abb2e9ce0db7a637f4bedf17f53', 'hornlab_mesher': '55da4f46d662d8dcd7a9f94a609eeea4009fcd62', 'hornlab_plots': '9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44', 'hornlab_search': 'caa37d08be4bf0cda119d79234ec3221d7dada6d'}`)
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

## b1

- run `C:\Users\hunte\Hrns\hornlab-search\runs\20261117T062219Z-screen-b72640`, design `f8a98b31eee0`, design.json sha256 `a906ebb8d802916a`
- backend beat_cuda, dofs 3341, tris 6375, quadrants 1, angles 73, balloon [16, 32], solve 18.8276046999963 s
- -6 dB multi-lobe bins H/V: **0/0**; cut-limit saturated bins H/V: 2/3
- DI range 5.09 dB, variance 2.369 dB^2, slope 10.01 dB/dec
- off-axis wobble (|dSPL| per freq step, -25/0/+25 deg) H [0.8095089760959525, 0.7486922916908356, 0.8095090333095868], V [1.9992813479408373, 0.7486922916908356, 1.9992809252493982]

| band (bins) | BW_H mean | BW_V mean | DI mean | ripple H/V | sidelobe H/V | |Z| ours |
|---|---|---|---|---|---|---|
| 700-1200 Hz (2) | 63.2 | 110.1 | 9.8 | 2.9 / 0.5 | -5.6 / -2.1 | 0.8 |
| 1.2-5.6 kHz (9) | 62.8 | 42.2 | 14.1 | 3.3 / 2.7 | -5.7 / -9.5 | 1.0 |
| 5.6-8 kHz (2) | 45.2 | 35.2 | 17.0 | 5.2 / 3.7 | -9.6 / -14.1 | 1.0 |

## b2

- run `C:\Users\hunte\Hrns\hornlab-search\runs\20261117T062314Z-screen-262183`, design `59954be44142`, design.json sha256 `9b380bef98eba291`
- backend beat_cuda, dofs 4153, tris 7967, quadrants 1, angles 73, balloon [16, 32], solve 21.27089609997347 s
- -6 dB multi-lobe bins H/V: **0/0**; cut-limit saturated bins H/V: 2/3
- DI range 5.90 dB, variance 4.268 dB^2, slope 10.39 dB/dec
- off-axis wobble (|dSPL| per freq step, -25/0/+25 deg) H [1.001128852579511, 0.9092919962959662, 1.0011287381140472], V [2.05879988181223, 0.9092919962959662, 2.0587999687600784]

| band (bins) | BW_H mean | BW_V mean | DI mean | ripple H/V | sidelobe H/V | |Z| ours |
|---|---|---|---|---|---|---|
| 700-1200 Hz (2) | 69.7 | 112.0 | 9.8 | 2.7 / 0.5 | -5.6 / -2.0 | 0.9 |
| 1.2-5.6 kHz (9) | 62.2 | 42.5 | 14.2 | 3.5 / 2.9 | -5.8 / -9.6 | 1.0 |
| 5.6-8 kHz (2) | 41.6 | 33.0 | 18.1 | 5.6 / 3.9 | -11.0 / -14.3 | 1.0 |

## b3

- run `C:\Users\hunte\Hrns\hornlab-search\runs\20261117T062347Z-screen-4d3c1c`, design `48060310c5ed`, design.json sha256 `6072be59cbe86ffd`
- backend beat_cuda, dofs 3087, tris 5887, quadrants 1, angles 73, balloon [16, 32], solve 18.6431758000399 s
- -6 dB multi-lobe bins H/V: **0/0**; cut-limit saturated bins H/V: 2/3
- DI range 4.01 dB, variance 1.180 dB^2, slope 8.61 dB/dec
- off-axis wobble (|dSPL| per freq step, -25/0/+25 deg) H [0.9447236314357975, 0.8318393687766583, 0.9447235586147376], V [2.4248554013112225, 0.8318393687766583, 2.424855261167795]

| band (bins) | BW_H mean | BW_V mean | DI mean | ripple H/V | sidelobe H/V | |Z| ours |
|---|---|---|---|---|---|---|
| 700-1200 Hz (2) | 67.1 | 103.5 | 9.9 | 2.7 / 0.5 | -5.1 / -2.3 | 0.9 |
| 1.2-5.6 kHz (9) | 65.2 | 47.3 | 13.7 | 3.0 / 2.4 | -5.1 / -9.0 | 1.0 |
| 5.6-8 kHz (2) | 47.9 | 40.5 | 15.5 | 4.5 / 3.5 | -8.5 / -11.3 | 1.0 |

## b4

- run `C:\Users\hunte\Hrns\hornlab-search\runs\20261117T062551Z-screen-4ad99d`, design `2eb09e6cd9ed`, design.json sha256 `3057693f3d439ded`
- backend beat_cuda, dofs 3864, tris 7398, quadrants 1, angles 73, balloon [16, 32], solve 21.182404599967413 s
- -6 dB multi-lobe bins H/V: **0/0**; cut-limit saturated bins H/V: 2/3
- DI range 4.55 dB, variance 2.309 dB^2, slope 9.38 dB/dec
- off-axis wobble (|dSPL| per freq step, -25/0/+25 deg) H [1.1330033165506357, 0.8783062766463998, 1.1330034352624125], V [2.203045403884106, 0.8783062766463998, 2.2030453921000044]

| band (bins) | BW_H mean | BW_V mean | DI mean | ripple H/V | sidelobe H/V | |Z| ours |
|---|---|---|---|---|---|---|
| 700-1200 Hz (2) | 66.1 | 103.1 | 10.0 | 2.7 / 0.5 | -5.5 / -2.3 | 0.9 |
| 1.2-5.6 kHz (9) | 64.0 | 41.3 | 14.2 | 3.2 / 2.8 | -5.3 / -9.9 | 1.0 |
| 5.6-8 kHz (2) | 44.1 | 33.9 | 16.8 | 5.0 / 4.0 | -9.7 / -13.0 | 1.0 |

## Axis authority (mean -6 dB beamwidth change vs A0)

| arm | band | dBW_H | dBW_V | max |dBW_H| | max |dBW_V| |
|---|---|---|---|---|---|
| b1 | 700-1200 Hz | -34.4 | -33.2 | 35.8 | 36.4 |
| b1 | 1.2-5.6 kHz | -7.0 | -30.0 | 14.4 | 37.6 |
| b1 | 5.6-8 kHz | -17.8 | -9.8 | 19.8 | 10.2 |
| b2 | 700-1200 Hz | -27.9 | -31.3 | 45.6 | 34.5 |
| b2 | 1.2-5.6 kHz | -7.6 | -29.7 | 17.6 | 35.4 |
| b2 | 5.6-8 kHz | -21.4 | -12.1 | 21.5 | 12.7 |
| b3 | 700-1200 Hz | -30.5 | -39.8 | 32.3 | 42.3 |
| b3 | 1.2-5.6 kHz | -4.6 | -25.0 | 22.5 | 45.0 |
| b3 | 5.6-8 kHz | -15.1 | -4.5 | 20.0 | 7.4 |
| b4 | 700-1200 Hz | -31.5 | -40.3 | 40.9 | 43.4 |
| b4 | 1.2-5.6 kHz | -5.8 | -31.0 | 15.2 | 47.1 |
| b4 | 5.6-8 kHz | -18.8 | -11.2 | 20.9 | 11.5 |

## Decision (Phase B gate, computed from the table above)

Rule fixed before the solves: a Phase B seed is worth optimizing only if the mean -6 dB beamwidth in 1.2-5.6 kHz lands within +-10 deg of 80 deg H / 50 deg V, `Var(DI)` over that band drops by >= 25 % versus A0, no plane gains a second -6 dB lobe, and `load` does not get worse.

- **b1**: BW 62.8 H / 42.2 V (target 80/50, within +-10: False); Var(DI) 2.369 vs A0 2.160 (drop -9.7 %, >=25 %: False); multi-lobe bins 0/0 (ok: True); load 0.000 vs A0 0.777 (ok: True).
  - smooth J 9.80662656918318 ; CD J 19.98037279236928
  - gate: **FAIL**
- **b2**: BW 62.2 H / 42.5 V (target 80/50, within +-10: False); Var(DI) 4.268 vs A0 2.160 (drop -97.6 %, >=25 %: False); multi-lobe bins 0/0 (ok: True); load 0.000 vs A0 0.777 (ok: True).
  - smooth J 12.381640590601016 ; CD J 22.994693496272053
  - gate: **FAIL**
- **b3**: BW 65.2 H / 47.3 V (target 80/50, within +-10: False); Var(DI) 1.180 vs A0 2.160 (drop 45.4 %, >=25 %: True); multi-lobe bins 0/0 (ok: True); load 0.000 vs A0 0.777 (ok: True).
  - smooth J 6.569751987386718 ; CD J 14.827333775504703
  - gate: **FAIL**
- **b4**: BW 64.0 H / 41.3 V (target 80/50, within +-10: False); Var(DI) 2.309 vs A0 2.160 (drop -6.9 %, >=25 %: False); multi-lobe bins 0/0 (ok: True); load 0.000 vs A0 0.777 (ok: True).
  - smooth J 9.430735721808828 ; CD J 19.62639408114992
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

### b1 - smooth policy

- J = **9.80662656918318** (exact_complete), stored J 9.80662656918318, parity delta 0.0
- score id `0571ef150e9954f9`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\b1_balanced.yaml`

| term | value |
|---|---|
| cov | 1.4349105362496044 |
| rip | 0.39369756770322667 |
| di | 0.0 |
| dislope | 1.316216248746328 |
| flat | 0.45120337059919463 |
| load | 0.0 |
| distd | 1.2090461312729093 |
| diag | 4.78598418136027 |
| flat_cv | 0.44117021855124405 |
| penalty | 0.0 |
| total | 9.80662656918318 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 329.1659420130517 |
| lfp50_hz | 361.27233868114644 |
| rez_min_from_fx | 0.6483621524108952 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### b1 - cd policy

- J = **19.98037279236928** (exact_complete), stored J 9.80662656918318, parity delta None
- score id `45464d17a5e60a32`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\ab_cd_policy.yaml`

| term | value |
|---|---|
| cov | 5.657432670323863 |
| rip | 0.39369756770322667 |
| di | 8.056180732289253 |
| dislope | 1.331869842678146 |
| flat | 0.45120337059919463 |
| load | 0.0 |
| distd | 0.5034424179341432 |
| diag | 9.262025379159356 |
| flat_cv | 0.44117021855124405 |
| penalty | 0.0 |
| total | 19.98037279236928 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 329.1659420130517 |
| lfp50_hz | 361.27233868114644 |
| rez_min_from_fx | 0.6483621524108952 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### b2 - smooth policy

- J = **12.381640590601016** (exact_complete), stored J 12.381640590601016, parity delta 0.0
- score id `8d1e2aed9473a7cb`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\b2_wide.yaml`

| term | value |
|---|---|
| cov | 1.6891104032267268 |
| rip | 0.3884633830613539 |
| di | 0.0 |
| dislope | 2.710622777373361 |
| flat | 0.41542786875616927 |
| load | 0.0 |
| distd | 1.4356758169192343 |
| diag | 5.555860189291151 |
| flat_cv | 0.3941940863511053 |
| penalty | 0.0 |
| total | 12.381640590601016 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 328.8613269007489 |
| lfp50_hz | 416.93562185957364 |
| rez_min_from_fx | 0.7140405390972224 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### b2 - cd policy

- J = **22.994693496272053** (exact_complete), stored J 12.381640590601016, parity delta None
- score id `811b22d640bd0152`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\ab_cd_policy.yaml`

| term | value |
|---|---|
| cov | 6.689887217300192 |
| rip | 0.3884633830613539 |
| di | 7.686414981241359 |
| dislope | 1.766353561746758 |
| flat | 0.41542786875616927 |
| load | 0.0 |
| distd | 0.5808135986008834 |
| diag | 10.95175001976171 |
| flat_cv | 0.3941940863511053 |
| penalty | 0.0 |
| total | 22.994693496272053 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 328.8613269007489 |
| lfp50_hz | 416.93562185957364 |
| rez_min_from_fx | 0.7140405390972224 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### b3 - smooth policy

- J = **6.569751987386718** (exact_complete), stored J 6.569751987386718, parity delta 0.0
- score id `2322831c6d6986e5`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\b3_soft.yaml`

| term | value |
|---|---|
| cov | 1.1432221812987522 |
| rip | 0.4169455886907377 |
| di | 0.0 |
| dislope | 0.1861011392022175 |
| flat | 0.5206217284243058 |
| load | 0.0 |
| distd | 0.939035922097609 |
| diag | 3.1429858094306518 |
| flat_cv | 0.4811504824545972 |
| penalty | 0.0 |
| total | 6.569751987386718 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 349.01478073241304 |
| lfp50_hz | 475.0102662758203 |
| rez_min_from_fx | 0.732315695368301 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### b3 - cd policy

- J = **14.827333775504703** (exact_complete), stored J 6.569751987386718, parity delta None
- score id `d674a0015f653d1f`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\ab_cd_policy.yaml`

| term | value |
|---|---|
| cov | 4.287752019886906 |
| rip | 0.4169455886907377 |
| di | 8.341452404406354 |
| dislope | 0.750131351840001 |
| flat | 0.5206217284243058 |
| load | 0.0 |
| distd | 0.40327697919568867 |
| diag | 5.926969257500559 |
| flat_cv | 0.4811504824545972 |
| penalty | 0.0 |
| total | 14.827333775504703 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 349.01478073241304 |
| lfp50_hz | 475.0102662758203 |
| rez_min_from_fx | 0.732315695368301 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### b4 - smooth policy

- J = **9.430735721808828** (exact_complete), stored J 9.430735721808828, parity delta 0.0
- score id `16eab50fdd81b0b9`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\b4_wide_h.yaml`

| term | value |
|---|---|
| cov | 1.3490740483116261 |
| rip | 0.4251250010569078 |
| di | 0.0 |
| dislope | 0.9865571320297559 |
| flat | 0.42520425492481356 |
| load | 0.0 |
| distd | 1.1539841343763548 |
| diag | 4.929645197361489 |
| flat_cv | 0.3737480812102882 |
| penalty | 0.0 |
| total | 9.430735721808828 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 332.61020993977155 |
| lfp50_hz | 391.6000935178236 |
| rez_min_from_fx | 0.8144704353484867 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### b4 - cd policy

- J = **19.62639408114992** (exact_complete), stored J 9.430735721808828, parity delta None
- score id `5c9eb484e0cf6957`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\ab_cd_policy.yaml`

| term | value |
|---|---|
| cov | 5.213320029398094 |
| rip | 0.4251250010569078 |
| di | 7.616565912866819 |
| dislope | 1.1477523545047659 |
| flat | 0.42520425492481356 |
| load | 0.0 |
| distd | 0.47426380414127006 |
| diag | 9.731744811586776 |
| flat_cv | 0.3737480812102882 |
| penalty | 0.0 |
| total | 19.62639408114992 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 332.61020993977155 |
| lfp50_hz | 391.6000935178236 |
| rez_min_from_fx | 0.8144704353484867 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

## Reading rules

- Wall angles are geometry, not beamwidth. No result here shows that theta_H/theta_V map to horizontal/vertical coverage.
- The driver source cap is the existing simulation assumption, unchanged by this comparison.
- J is comparable only within one policy; the smooth brief is not a CD score.
- A band row with 1 bin is a single frequency, not a band statistic.
