# Space card: `hl__crowe_x_square_v7`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__crowe_x_square_v7.yaml`; family FREEFORM; generator True. CPU only; evidence for a person, nothing applied.

- Legal sample points: 4/9; effective dimension {'median': 6.5, 'min': 6, 'max': 7, 'searched': 8}
- Box scan: {'ok': 33, 'outside': 0, 'refused': 63} (ok fraction 34%)
- Predicted bad rate by sigma0: 0.05: 75%, 0.10: 67%, 0.15: 56%, 0.20: 52%, 0.25: 67%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `g_L_mm` | active | 49.36 | 24.48 | - | 1.00 / 0.00 |
| `g_a_h_deg` | active | 17.69 | 8.50 | - | 1.00 / 0.00 |
| `g_a_v_deg` | active | 17.85 | 8.40 | - | 1.00 / 0.00 |
| `g_n` | active | 9.16 | 5.52 | - | 0.00 / 1.00 |
| `g_r_lip_mm` | active | 22.31 | 13.90 | - | 1.00 / 0.00 |
| `g_s` | active | 38.84 | 16.79 | - | 1.00 / 0.00 |
| `g_sf_amt` | active | 51.17 | 15.63 | - | 1.00 / 0.00 |
| `g_wrap_deg` | active | 21.87 | 12.60 | - | 0.00 / 0.00 |

Envelope margin model: R^2 1.00, sign agreement 100%, inside 100%, binding {'height_mm': 33}

## Recommendations (not applied)

- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": null}`
