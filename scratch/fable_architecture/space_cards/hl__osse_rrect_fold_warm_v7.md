# Space card: `hl__osse_rrect_fold_warm_v7`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__osse_rrect_fold_warm_v7.yaml`; family OSSE; generator False. CPU only; evidence for a person, nothing applied.

- Legal sample points: 9/9; effective dimension {'median': 12.0, 'min': 12, 'max': 13, 'searched': 18}
- Box scan: {'ok': 96, 'outside': 0, 'refused': 0} (ok fraction 100%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 0%, 0.15: 0%, 0.20: 0%, 0.25: 0%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 44.74 | 22.99 | - | 1.00 / 1.00 |
| `a0_deg` | weak | 0.42 | 0.22 | - | 1.00 / 1.00 |
| `a_deg` | active | 10.16 | 5.78 | k | 1.00 / 1.00 |
| `az_a_cos_amp` | active | 8.45 | 3.29 | - | 1.00 / 1.00 |
| `az_a_cos_pow` | active | 6.20 | 2.39 | - | 1.00 / 1.00 |
| `az_fold_h_deg` | active | 34.82 | 9.30 | - | 1.00 / 1.00 |
| `az_fold_h_width_deg` | active | 18.92 | 6.25 | - | 1.00 / 1.00 |
| `az_fold_v_deg` | active | 79.28 | 23.03 | - | 1.00 / 1.00 |
| `az_fold_v_width_deg` | active | 21.51 | 6.28 | - | 1.00 / 1.00 |
| `az_s_cos2_amp` | active | 1.43 | 0.42 | - | 1.00 / 1.00 |
| `k` | active | 5.25 | 3.14 | a_deg | 1.00 / 1.00 |
| `morph_corner_mm` | active | 6.84 | 0.97 | - | 1.00 / 1.00 |
| `morph_height_mm` | active | 26.39 | 8.15 | - | 1.00 / 1.00 |
| `morph_rate` | active | 6.35 | 2.08 | - | 1.00 / 1.00 |
| `morph_width_mm` | active | 16.35 | 5.10 | - | 1.00 / 1.00 |
| `n` | active | 1.73 | 0.72 | q, s | 1.00 / 1.00 |
| `q` | active | 5.45 | 2.01 | n, s | 1.00 / 1.00 |
| `s` | active | 3.35 | 1.42 | n, q | 1.00 / 1.00 |

Envelope margin model: R^2 1.00, sign agreement 100%, inside 100%, binding {'width_mm': 97}

## Recommendations (not applied)

- **fix_or_widen** `a0_deg`: whole range moves the surface <= 0.42 mm (below the ~1 mm mesher fit): CMA spends a dimension on mesh noise
- **link** `n`: surface direction parallel to s (|cos| 0.990); data_agrees=unknown; proposal `{"from": "s", "scale": -3.966362221114989, "offset": 9.751522929293564}`
- **link** `k`: surface direction parallel to a_deg (|cos| 0.982); data_agrees=unknown; proposal `{"from": "a_deg", "scale": -0.09393825458525228, "offset": 6.224170810380439}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.25}`
