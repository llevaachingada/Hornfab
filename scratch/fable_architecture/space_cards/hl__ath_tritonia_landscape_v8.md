# Space card: `hl__ath_tritonia_landscape_v8`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__ath_tritonia_landscape_v8.yaml`; family OSSE; generator False. CPU only; evidence for a person, nothing applied.

- Legal sample points: 9/9; effective dimension {'median': 10.0, 'min': 9, 'max': 10, 'searched': 14}
- Box scan: {'ok': 92, 'outside': 0, 'refused': 4} (ok fraction 96%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 0%, 0.15: 0%, 0.20: 0%, 0.25: 0%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 273.27 | 176.29 | - | 1.00 / 0.98 |
| `a0_deg` | active | 2.74 | 1.33 | - | 1.00 / 1.00 |
| `a_deg` | active | 8.79 | 4.40 | - | 1.00 / 1.00 |
| `az_a_cos_amp` | active | 4.54 | 1.93 | - | 1.00 / 1.00 |
| `az_fold_v_deg` | active | 1.34 | 0.40 | - | 1.00 / 1.00 |
| `az_fold_v_width_deg` | active | 2.72 | 0.80 | - | 1.00 / 1.00 |
| `k` | active | 2.55 | 1.37 | - | 1.00 / 1.00 |
| `morph_corner_mm` | active | 8.32 | 0.98 | - | 1.00 / 1.00 |
| `morph_height_mm` | active | 170.65 | 58.90 | - | 1.00 / 1.00 |
| `morph_rate` | active | 61.74 | 25.74 | - | 1.00 / 1.00 |
| `morph_width_mm` | active | 158.08 | 53.99 | - | 1.00 / 1.00 |
| `n` | active | 24.57 | 13.72 | s | 1.00 / 1.00 |
| `q` | active | 23.76 | 13.95 | s | 1.00 / 1.00 |
| `s` | active | 7.13 | 3.86 | n, q | 1.00 / 1.00 |

Envelope margin model: R^2 0.70, sign agreement 97%, inside 100%, binding {'depth_mm': 29, 'height_mm': 41, 'width_mm': 23}

## Recommendations (not applied)

- **link** `s`: surface direction parallel to q (|cos| 0.991); data_agrees=unknown; proposal `{"from": "q", "scale": 0.8121966490908422, "offset": 0.16388668705178877}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.25}`
