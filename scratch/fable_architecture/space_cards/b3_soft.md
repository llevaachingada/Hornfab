# Space card: `klangfilm_hv_core__b3_soft`

Config `examples/typologies/klangfilm_hv_2026-11-16/configs/b3_soft.yaml`; family FREEFORM; generator True. CPU only; evidence for a person, nothing applied.

- Legal sample points: 6/7; effective dimension {'median': 12.0, 'min': 12, 'max': 12, 'searched': 12}
- Box scan: {'ok': 54, 'outside': 0, 'refused': 10} (ok fraction 84%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 0%, 0.15: 6%, 0.20: 6%, 0.25: 22%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `g_beak_diagonal_mm` | active | 10.00 | 2.87 | - | 1.00 / 1.00 |
| `g_beak_h_setback_mm` | active | 10.00 | 2.41 | - | 1.00 / 1.00 |
| `g_beak_start_frac` | active | 6.58 | 0.64 | - | 1.00 / 1.00 |
| `g_beak_v_projection_mm` | active | 5.00 | 1.57 | - | 1.00 / 1.00 |
| `g_core_length_mm` | active | 242.96 | 132.03 | - | 1.00 / 0.92 |
| `g_lame_end_frac` | active | 3.20 | 0.91 | - | 1.00 / 1.00 |
| `g_lame_p_mouth` | active | 30.39 | 8.06 | - | 1.00 / 1.00 |
| `g_lame_start_frac` | active | 1.23 | 0.35 | - | 1.00 / 1.00 |
| `g_theta_h0_deg` | active | 15.02 | 5.89 | - | 1.00 / 1.00 |
| `g_theta_h1_deg` | active | 144.19 | 37.43 | - | 1.00 / 1.00 |
| `g_theta_v0_deg` | active | 14.14 | 7.55 | - | 1.00 / 1.00 |
| `g_theta_v1_deg` | active | 81.40 | 30.10 | - | 1.00 / 1.00 |

Envelope margin model: R^2 0.93, sign agreement 100%, inside 100%, binding {'width_mm': 18, 'depth_mm': 35, 'height_mm': 2}

## Recommendations (not applied)

- **rebound** `g_theta_h1_deg`: edge slice mostly refused/outside while the middle is not; proposal `{"lower_hi_to_unit": 0.8}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.2}`
