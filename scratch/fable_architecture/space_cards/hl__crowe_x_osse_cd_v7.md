# Space card: `hl__crowe_x_osse_cd_v7`

Config `examples/typologies/home_landscape_2026-11-15/hl__crowe_x_osse_cd_v7.yaml`; family FREEFORM; generator True. CPU only; evidence for a person, nothing applied.

- Legal sample points: 4/7; effective dimension {'median': 7.0, 'min': 7, 'max': 7, 'searched': 9}
- Box scan: {'ok': 49, 'outside': 0, 'refused': 15} (ok fraction 77%)
- Predicted bad rate by sigma0: 0.05: 47%, 0.10: 56%, 0.15: 44%, 0.20: 50%, 0.25: 47%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `g_L_mm` | active | 125.57 | 66.71 | - | 1.00 / 0.03 |
| `g_a_h_deg` | active | 45.30 | 17.43 | - | 1.00 / 0.03 |
| `g_a_v_deg` | active | 31.19 | 13.95 | - | 1.00 / 1.00 |
| `g_n` | active | 17.89 | 10.05 | - | 0.17 / 1.00 |
| `g_r_lip_mm` | active | 39.54 | 24.17 | g_wrap_deg | 1.00 / 0.06 |
| `g_s` | active | 57.02 | 26.12 | - | 1.00 / 0.06 |
| `g_sf_ab` | active | 32.90 | 12.45 | - | 0.05 / 1.00 |
| `g_sf_amt` | active | 36.04 | 10.77 | - | 0.28 / 1.00 |
| `g_wrap_deg` | active | 20.18 | 11.51 | g_r_lip_mm | 1.00 / 1.00 |

Envelope margin model: R^2 0.97, sign agreement 100%, inside 100%, binding {'height_mm': 5, 'width_mm': 45}

## Recommendations (not applied)

- **link** `g_r_lip_mm`: surface direction parallel to g_wrap_deg (|cos| 0.969); proposal `{"from": "g_wrap_deg", "scale": 0.5301389056322042, "offset": -27.3535688237531}`
- **rebound** `g_L_mm`: edge slice mostly refused/outside while the middle is not; proposal `{"lower_hi_to_unit": 0.8}`
- **rebound** `g_s`: edge slice mostly refused/outside while the middle is not; proposal `{"lower_hi_to_unit": 0.8}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": null}`
