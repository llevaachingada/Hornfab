# Klangfilm-Lame H/V Phase A — geometry preflight

**DIAGNOSTIC ONLY.** Surface geometry from the Phase A kernel (`klangfilm-lame-hv-v1`); no meshing, BEM, GPU, shell, curvature or acoustic validation. These are geometry hypotheses, not acoustic winners.

Kernel called directly (`tools/geometry/klangfilm_lame_hv.py`), never the package adapter. H/V angles below are TRUE WALL HALF-ANGLES (not beamwidth halves). Envelope is a `sampled_conservative_estimate` (inner sampled quarter grid + wall thickness), not a mesh certificate.

Two as-specified seeds (a3, a4) are refused by the kernel's no-constriction invariant: a negative `g_*_mid_gain_mm` lets the B2 basis dominate the local wall slope, so the forward V radius stops being non-decreasing. The feasible variants (a3b, a4b) replace only that impossible negative gain with 0.0; the negative-V idea is recorded as Phase B motivation, not as a bug.

## Seed status

| seed | status | θ_H model/mesh (deg) | θ_V model/mesh (deg) | targets H/V (deg) | q(0)/q(5)/q(15) | p throat/0.2/0.5/0.8 | W/H/D inner (mm) | envelope | Δ vs A0 H/V (mm) | rejection reason |
|---|---|---|---|---|---|---|---|---|---|---|
| a0 | accepted | 9.46 / 9.77 | 9.44 / 9.41 | — / — | 1.000/1.001/1.015 | 2.000/2.645/4.933/5.006 | 541.3/260.7/233.7 | OK | 0.000 / 0.000 | — |
| a1 | accepted | 10.00 / 10.20 | 5.00 / 5.83 | 10.0 / 5.0 | 1.000/1.022/1.061 | 2.000/2.645/4.933/5.006 | 541.3/260.7/233.7 | OK | 0.122 / 0.993 | — |
| a2 | accepted | 14.00 / 13.44 | 5.00 / 5.83 | 14.0 / 5.0 | 1.000/1.039/1.098 | 2.000/2.645/4.933/5.006 | 541.3/260.7/233.7 | OK | 1.042 / 0.993 | — |
| a3 | **rejected** | — | — | — | — | — | — | — | — | `V forward radius shrinks below the throat radius` |
| a3b | accepted | 9.00 / 10.77 | 6.00 / 6.55 | 9.0 / 6.0 | 1.000/1.016/1.097 | 2.000/2.645/4.933/5.006 | 541.3/260.7/233.7 | OK | 17.917 / 0.889 | — |
| a4 | **rejected** | — | — | — | — | — | — | — | — | `V forward radius shrinks below the throat radius` |
| a4b | accepted | 9.00 / 10.32 | 4.00 / 5.03 | 9.0 / 4.0 | 1.000/1.024/1.096 | 2.000/2.645/4.933/5.006 | 541.3/260.7/233.7 | OK | 7.938 / 1.214 | — |
| a5 | accepted | 11.00 / 11.21 | 6.00 / 6.56 | 11.0 / 6.0 | 1.000/1.023/1.066 | 2.000/2.483/3.981/4.000 | 622.6/377.3/256.0 | **EXCEEDED** | 100.593 / 37.646 | — |

Δ vs A0 = max |forward semi-axis − A0 forward semi-axis| on A0's forward z stations. A0 (blend 0) is the legacy control; a5 also changes parent genes, so its Δ is not a single-knob measure.

A0 legacy control: blend 0 grid is **bit-exact** with `klangfilm_lame-v1` (sha256 `7e80214c3b280209…`).

## Convergence (accepted, non-legacy seeds)

Rebuilt at `n_phi=37` and at `n_s=128`. The mesh chord is expected to approach the analytic model angle as `n_s` rises; no hard bound is asserted, the numbers and trend are reported.

| seed | Δmax W @n_phi37 (mm) | Δmax H @n_phi37 (mm) | Δthroat spread @n_phi37 (mm) | Δmax W @n_s128 (mm) | Δmax H @n_s128 (mm) | mesh−model H/V @n_s64 (deg) | mesh−model H/V @n_s128 (deg) | trend H/V toward model |
|---|---|---|---|---|---|---|---|---|
| a1 | +0.0000 | +0.0000 | +0.00000 | +0.0722 | +0.0348 | +0.204 / +0.833 | +0.042 / +0.481 | toward / toward |
| a2 | +0.0000 | +0.0000 | +0.00000 | +0.0740 | +0.0356 | -0.562 / +0.831 | -0.358 / +0.479 | toward / toward |
| a3b | +0.0000 | +0.0000 | +0.00000 | +0.0886 | +0.0427 | +1.771 / +0.553 | +0.534 / +0.332 | toward / toward |
| a4b | +0.0000 | +0.0000 | +0.00000 | +0.0836 | +0.0403 | +1.321 / +1.028 | +0.412 / +0.584 | toward / toward |
| a5 | +0.0000 | +0.0000 | +0.00000 | +0.0000 | +0.0000 | +0.215 / +0.558 | -0.027 / +0.249 | toward / toward |

## Cached CD diagnostic `J_CD_cached`

**DIAGNOSTIC (NOT the v7 objective).** Band `[1200, 5600] Hz` inclusive; `mean(e_h^2) + mean(e_v^2) + Var(DI)`; population variance (ddof=0) over the selected bands; `tau = 8.0 deg` recorded as the reference tolerance. **cached run config used di_slope_target = +5 dB/dec with no DI weight; J values are NOT comparable across objectives and are not a score.**

- `J_CD_cached = 17.589146` over 9 cached bands (1370.35–4832.36 Hz).
- mean e_H² = 2.441653, mean e_V² = 12.987199, Var(DI) = 2.160294.
- DI mean = 11.643 dB, range = 4.536 dB (8.818–13.354 dB).
- f_break H = 586.4925768850987 Hz, f_break V = 1948.0509796198112 Hz, f_load = 643.33 Hz. f_break_h/f_break_v are cached reductions of the beamwidth curves; the J_CD_cached band starts at 1200 Hz, above both break points, so the whole diagnostic band is in the post-break narrowing region.

| freq (Hz) | BW_H (deg) | BW_V (deg) | DI (dB) | e_H | e_V |
|---|---|---|---|---|---|
| 1370.35 | 84.487 | 110.453 | 8.818 | +0.5608 | +7.5567 |
| 1763.18 | 80.079 | 94.173 | 9.742 | +0.0099 | +5.5217 |
| 2268.63 | 72.638 | 78.701 | 10.894 | -0.9203 | +3.5876 |
| 2573.00 | 67.891 | 72.415 | 11.530 | -1.5136 | +2.8019 |
| 2918.96 | 64.718 | 67.026 | 12.057 | -1.9102 | +2.1282 |
| 3311.00 | 62.804 | 62.595 | 12.496 | -2.1495 | +1.5744 |
| 3755.72 | 63.558 | 58.647 | 12.816 | -2.0553 | +1.0808 |
| 4260.00 | 65.664 | 54.759 | 13.081 | -1.7920 | +0.5949 |
| 4832.36 | 66.571 | 51.619 | 13.354 | -1.6786 | +0.2024 |

Source: `runs\20261116T205942Z-screen-8b22b5\designs\786caa6b08d7\metrics.json` (cached; no solve in this preflight).

