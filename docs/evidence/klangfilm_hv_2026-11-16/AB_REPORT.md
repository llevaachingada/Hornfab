# Klangfilm-Lame H/V Stage A - controlled acoustic A/B

**Scope.** BEM runs sharing mesh policy, source cap, solver and frequency grid. The only difference between arms is the intended throat-angle key: `A1` = H-plane only (theta_H 9.4631 -> 14.0 deg, theta_V pinned at its measured base), `A2` = V-plane only (theta_V 9.4378 -> 5.0 deg, theta_H pinned at its measured base). `A0` is the incumbent; its geometry array is bit-identical to `klangfilm-lame-v1` at blend 0.

Scores under the smooth and CD policies are reported side by side but **never compared to each other**: the same stored responses are re-scored through the canonical replay path.

## A0 reuse gate

- cached run `C:\Users\hunte\Hrns\hornlab-search\runs\20261116T205942Z-screen-8b22b5` design `786caa6b08d7` (status `running`)
- geometry array equal to legacy: **True**, grid sha256 `7e80214c3b280209`
- same brief path: **True**; blocks equal: {'driver': True, 'envelope': True, 'grid': True, 'mesh': True, 'objective': True, 'solve': True, 'target': True, 'weights': True}
- library SHAs equal: **False** (cached `{'hornlab_beat_bem': '38e5b1f8ca840ebf6351c54611a08fedb1a0750f', 'hornlab_bempp_bem': '8e6910602ece9abb2e9ce0db7a637f4bedf17f53', 'hornlab_mesher': '55da4f46d662d8dcd7a9f94a609eeea4009fcd62', 'hornlab_plots': '9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44', 'hornlab_search': '0cd9543474dde441dce811c2f18c52dbee6ad905'}`, now `{'hornlab_beat_bem': '38e5b1f8ca840ebf6351c54611a08fedb1a0750f', 'hornlab_bempp_bem': '8e6910602ece9abb2e9ce0db7a637f4bedf17f53', 'hornlab_mesher': '55da4f46d662d8dcd7a9f94a609eeea4009fcd62', 'hornlab_plots': '9e4a6d0dd2ccb6e735dd00233dccccb50d12ed44', 'hornlab_search': 'unknown'}`)
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

## A1 H-only (theta_H 14)

- run `C:\Users\hunte\Hrns\hornlab-search\runs\20261117T015600Z-screen-de1861`, design `e40b381aa08a`, design.json sha256 `eaab754176dc557e`
- backend beat_cuda, dofs 7435, tris 14514, quadrants 1, angles 73, balloon [16, 32], solve 48.657305100001395 s
- -6 dB multi-lobe bins H/V: **0/0**; cut-limit saturated bins H/V: 3/5
- DI range 4.63 dB, variance 2.226 dB^2, slope 8.56 dB/dec
- off-axis wobble (|dSPL| per freq step, -25/0/+25 deg) H [0.9589973531333618, 0.738206694120543, 0.9589971485175047], V [1.276123644312807, 0.738206694120543, 1.276123561252191]

| band (bins) | BW_H mean | BW_V mean | DI mean | ripple H/V | sidelobe H/V | |Z| ours |
|---|---|---|---|---|---|---|
| 700-1200 Hz (2) | 97.6 | 143.3 | 7.3 | 1.4 / 0.3 | -2.5 / -1.3 | 0.9 |
| 1.2-5.6 kHz (9) | 69.4 | 72.3 | 11.7 | 2.5 / 1.2 | -4.8 / -4.9 | 1.0 |
| 5.6-8 kHz (2) | 60.2 | 45.5 | 14.2 | 3.5 / 2.4 | -6.1 / -9.0 | 1.0 |

## A2 V-only (theta_V 5)

- run `C:\Users\hunte\Hrns\hornlab-search\runs\20261117T015658Z-screen-7ffaad`, design `b6a2c90ee34d`, design.json sha256 `f0bc2f208ad1d5cb`
- backend beat_cuda, dofs 7464, tris 14572, quadrants 1, angles 73, balloon [16, 32], solve 49.915729200001806 s
- -6 dB multi-lobe bins H/V: **0/0**; cut-limit saturated bins H/V: 3/5
- DI range 4.57 dB, variance 2.172 dB^2, slope 8.47 dB/dec
- off-axis wobble (|dSPL| per freq step, -25/0/+25 deg) H [1.0171306006701815, 0.8109493518492983, 1.0171305006439817], V [1.3495928098348529, 0.8109493518492983, 1.3495928736397742]

| band (bins) | BW_H mean | BW_V mean | DI mean | ripple H/V | sidelobe H/V | |Z| ours |
|---|---|---|---|---|---|---|
| 700-1200 Hz (2) | 97.6 | 143.3 | 7.3 | 1.4 / 0.3 | -2.5 / -1.3 | 1.0 |
| 1.2-5.6 kHz (9) | 69.8 | 72.3 | 11.6 | 2.5 / 1.2 | -4.8 / -4.9 | 1.0 |
| 5.6-8 kHz (2) | 62.3 | 44.8 | 14.0 | 3.3 / 2.4 | -5.6 / -9.2 | 1.0 |

## Axis authority (mean -6 dB beamwidth change vs A0)

| arm | band | dBW_H | dBW_V | max |dBW_H| | max |dBW_V| |
|---|---|---|---|---|---|
| a1 | 700-1200 Hz | -0.0 | -0.0 | 0.0 | 0.0 |
| a1 | 1.2-5.6 kHz | -0.4 | +0.0 | 1.8 | 0.0 |
| a1 | 5.6-8 kHz | -2.7 | +0.4 | 4.0 | 0.8 |
| a2 | 700-1200 Hz | +0.0 | +0.0 | 0.0 | 0.0 |
| a2 | 1.2-5.6 kHz | -0.0 | -0.0 | 0.7 | 0.0 |
| a2 | 5.6-8 kHz | -0.7 | -0.2 | 1.2 | 0.2 |

## Decision (computed from the table above)

Rule fixed before the run: Stage A counts as having useful authority only if the intended axis moves the mean -6 dB beamwidth by **>= 3 deg** in at least one band, with cross-axis leak below 2 deg and no new -6 dB lobes. Otherwise Stage B (the monotonic CD core) is warranted.

- Intended-axis mean change in 1.2-5.6 kHz: A1 H -0.38 deg, A2 V -0.00 deg; in 5.6-8 kHz: A1 H -2.74 deg, A2 V -0.25 deg.
- Cross-axis leak: max 0.71 deg (A1 V +0.00 in 1.2-5.6 kHz; A2 H -0.03).
- Multi -6 dB lobes: none in any arm; cut-limit saturation unchanged (3 H bins, 5 V bins).
- J (smooth policy, comparable within policy): A0 8.438, A1 8.694 (+0.256), A2 8.567 (+0.129).
- J (CD policy, comparable within policy): A0 14.208, A1 14.548 (+0.340), A2 14.335 (+0.127).

**Result: Stage A does NOT have useful acoustic authority.** The largest intended-axis mean change is far below the 3 deg threshold, the high-frequency H change is a *narrowing* (wrong direction for the 80x50 target), and both scoring policies get worse. The throat-only offset cannot move a pattern that is set by the mouth and the rollback. **Phase B (monotonic integrated-slope core) is warranted; do not optimize this 4-knob box.**

**Not claimed:** 80x50 constant directivity, or that wall angle maps to coverage. The driver exit wavefront is still the existing source-cap assumption.

## Canonical v7 term contributions (same responses, two policies)

### a0 - smooth policy

- J = **8.43812590231321** (exact_complete), stored J 8.43812590231321, parity delta 0.0
- score id `4607eb459d54845e`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\a0.yaml`

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
- score id `cfa85bd44a5d2b3b`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\ab_cd_policy.yaml`

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

### a1 - smooth policy

- J = **8.693989108803722** (exact_complete), stored J 8.693989108803722, parity delta 0.0
- score id `f8d5e7b7afc8d02f`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\a1_h_only_single_axis.yaml`

| term | value |
|---|---|
| cov | 1.1658554186723828 |
| rip | 0.043484506399444026 |
| di | 0.0 |
| dislope | 1.0846695082451334 |
| flat | 0.33268924078490186 |
| load | 0.7697805430532916 |
| distd | 1.1615910759413277 |
| diag | 4.207171245635234 |
| flat_cv | 0.09509219046445712 |
| penalty | 0.0 |
| total | 8.693989108803722 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 513.4476463883601 |
| lfp50_hz | 569.6856901308605 |
| rez_min_from_fx | 0.7429883140333616 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### a1 - cd policy

- J = **14.548197978289563** (exact_complete), stored J 8.693989108803722, parity delta None
- score id `d697f53e1b165a5a`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\ab_cd_policy.yaml`

| term | value |
|---|---|
| cov | 3.769066235919014 |
| rip | 0.043484506399444026 |
| di | 10.446506585556676 |
| dislope | 1.5396630592184612 |
| flat | 0.33268924078490186 |
| load | 0.7697805430532916 |
| distd | 0.5384024920738865 |
| diag | 4.761613601138499 |
| flat_cv | 0.09509219046445712 |
| penalty | 0.0 |
| total | 14.548197978289563 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 513.4476463883601 |
| lfp50_hz | 569.6856901308605 |
| rez_min_from_fx | 0.7429883140333616 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### a2 - smooth policy

- J = **8.566905640298252** (exact_complete), stored J 8.566905640298252, parity delta 0.0
- score id `1a5800344f87f54f`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\a2_v_only_single_axis.yaml`

| term | value |
|---|---|
| cov | 1.1295303501417289 |
| rip | 0.04570321171831259 |
| di | 0.0 |
| dislope | 0.975738011192642 |
| flat | 0.3854590365871144 |
| load | 0.7869671972027519 |
| distd | 1.141897612829692 |
| diag | 4.162673947009842 |
| flat_cv | 0.1316657919097255 |
| penalty | 0.0 |
| total | 8.566905640298252 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 515.2859214974551 |
| lfp50_hz | 574.7621342598248 |
| rez_min_from_fx | 0.7839972530018301 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

### a2 - cd policy

- J = **14.334599251072783** (exact_complete), stored J 8.566905640298252, parity delta None
- score id `6d86c8c7db10cc46`, brief `examples\typologies\klangfilm_hv_2026-11-16\configs\ab_cd_policy.yaml`

| term | value |
|---|---|
| cov | 3.6094276356522186 |
| rip | 0.04570321171831259 |
| di | 10.471641115043363 |
| dislope | 1.487041298132878 |
| flat | 0.3854590365871144 |
| load | 0.7869671972027519 |
| distd | 0.5312643172362297 |
| diag | 4.673940105032215 |
| flat_cv | 0.1316657919097255 |
| penalty | 0.0 |
| total | 14.334599251072783 |
| n_nan | 0 |
| n_in_band | 13 |
| di_estimated | 0.0 |
| lfp20_hz | 515.2859214974551 |
| lfp50_hz | 574.7621342598248 |
| rez_min_from_fx | 0.7839972530018301 |
| f11_hz | 5600.0 |
| loaded_hi_hz | 5600.0 |

## Reading rules

- Wall angles are geometry, not beamwidth. No result here shows that theta_H/theta_V map to horizontal/vertical coverage.
- The driver source cap is the existing simulation assumption, unchanged by this comparison.
- J is comparable only within one policy; the smooth brief is not a CD score.
- A band row with 1 bin is a single frequency, not a band statistic.
