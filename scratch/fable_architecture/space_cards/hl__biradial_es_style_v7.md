# Space card: `hl__biradial_es_style_v7`

Config `examples/typologies/home_landscape_2026-11-15/hl__biradial_es_style_v7.yaml`; family FREEFORM; generator True. CPU only; evidence for a person, nothing applied.

- Legal sample points: 7/7; effective dimension {'median': 8.0, 'min': 8, 'max': 8, 'searched': 8}
- Box scan: {'ok': 64, 'outside': 0, 'refused': 0} (ok fraction 100%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 0%, 0.15: 0%, 0.20: 0%, 0.25: 0%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 100.00 | 50.86 | - | 1.00 / 1.00 |
| `h_a_deg` | active | 13.50 | 4.57 | - | 1.00 / 1.00 |
| `h_n` | active | 13.60 | 4.07 | - | 1.00 / 1.00 |
| `h_rm_mm` | active | 32.18 | 9.72 | - | 1.00 / 1.00 |
| `mouth_exponent` | active | 51.65 | 14.73 | - | 1.00 / 1.00 |
| `v_a_deg` | active | 14.22 | 7.29 | - | 1.00 / 1.00 |
| `v_n` | active | 13.77 | 6.24 | - | 1.00 / 1.00 |
| `v_rm_mm` | active | 74.54 | 29.03 | - | 1.00 / 1.00 |

Envelope margin model: R^2 0.80, sign agreement 100%, inside 100%, binding {'height_mm': 13, 'width_mm': 52}

## Recommendations (not applied)

- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.25}`
