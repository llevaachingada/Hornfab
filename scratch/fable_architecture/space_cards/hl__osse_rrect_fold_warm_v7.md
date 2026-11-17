# Space card: `hl__osse_rrect_fold_warm_v7`

Config `examples/typologies/home_landscape_2026-11-15/hl__osse_rrect_fold_warm_v7.yaml`; family OSSE; generator False. CPU only; evidence for a person, nothing applied.

- Legal sample points: 7/7; effective dimension {'median': 12.0, 'min': 12, 'max': 13, 'searched': 18}
- Box scan: {'ok': 64, 'outside': 0, 'refused': 0} (ok fraction 100%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 0%, 0.15: 0%, 0.20: 0%, 0.25: 0%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 44.74 | 22.99 | - | 1.00 / 1.00 |
| `a0_deg` | weak | 0.39 | 0.22 | - | 1.00 / 1.00 |
| `a_deg` | active | 10.16 | 5.78 | k | 1.00 / 1.00 |
| `az_a_cos_amp` | active | 8.45 | 3.29 | - | 1.00 / 1.00 |
| `az_a_cos_pow` | active | 7.64 | 2.92 | - | 1.00 / 1.00 |
| `az_fold_h_deg` | active | 34.82 | 8.93 | - | 1.00 / 1.00 |
| `az_fold_h_width_deg` | active | 18.92 | 6.25 | - | 1.00 / 1.00 |
| `az_fold_v_deg` | active | 79.28 | 23.03 | - | 1.00 / 1.00 |
| `az_fold_v_width_deg` | active | 27.69 | 8.66 | - | 1.00 / 1.00 |
| `az_s_cos2_amp` | active | 1.48 | 0.42 | - | 1.00 / 1.00 |
| `k` | active | 5.27 | 3.14 | a_deg | 1.00 / 1.00 |
| `morph_corner_mm` | active | 6.84 | 0.97 | - | 1.00 / 1.00 |
| `morph_height_mm` | active | 26.39 | 7.99 | - | 1.00 / 1.00 |
| `morph_rate` | active | 6.63 | 2.13 | - | 1.00 / 1.00 |
| `morph_width_mm` | active | 16.54 | 5.10 | - | 1.00 / 1.00 |
| `n` | active | 1.74 | 0.74 | q, s | 1.00 / 1.00 |
| `q` | active | 5.59 | 2.01 | n, s | 1.00 / 1.00 |
| `s` | active | 3.35 | 1.42 | n, q | 1.00 / 1.00 |

Envelope margin model: R^2 1.00, sign agreement 100%, inside 100%, binding {'width_mm': 65}

## Recommendations (not applied)

- **fix_or_widen** `a0_deg`: whole range moves the surface <= 0.39 mm (below the ~1 mm mesher fit): CMA spends a dimension on mesh noise
- **link** `a_deg`: surface direction parallel to k (|cos| 0.982); proposal `{"from": "k", "scale": -10.29330988644193, "offset": 65.34030674157415}`
- **link** `n`: surface direction parallel to q (|cos| 0.968); proposal `{"from": "q", "scale": -27.97404807928285, "offset": 32.695845840443575}`
- **link** `n`: surface direction parallel to s (|cos| 0.990); proposal `{"from": "s", "scale": -4.2458400706679, "offset": 10.031360466838851}`
- **link** `q`: surface direction parallel to s (|cos| 0.986); proposal `{"from": "s", "scale": 0.14335215071014032, "offset": 0.8186333550718957}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.25}`
