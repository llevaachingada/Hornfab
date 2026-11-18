# Space card: `atlas__ath_core`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\atlas_2026-10-30\atlas__ath_core.yaml`; family OSSE; generator False. CPU only; evidence for a person, nothing applied.

- Legal sample points: 9/9; effective dimension {'median': 8.0, 'min': 7, 'max': 9, 'searched': 14}
- Box scan: {'ok': 57, 'outside': 37, 'refused': 2} (ok fraction 59%)
- Predicted bad rate by sigma0: 0.05: 25%, 0.10: 27%, 0.15: 46%, 0.20: 52%, 0.25: 48%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 438.77 | 253.95 | - | 1.00 / 0.62 |
| `a_deg` | active | 388.81 | 217.07 | k | 1.00 / 0.84 |
| `k` | active | 59.30 | 41.01 | a_deg | 1.00 / 1.00 |
| `morph_corner_mm` | active | 33.20 | 3.62 | - | 1.00 / 1.00 |
| `morph_exponent` | inactive | 0.00 | 0.00 | - | 1.00 / 1.00 |
| `morph_fixed` | active | 85.94 | 29.27 | - | 1.00 / 1.00 |
| `morph_height_mm` | active | 134.53 | 39.78 | - | 1.00 / 1.00 |
| `morph_rate` | active | 95.31 | 33.59 | - | 1.00 / 1.00 |
| `morph_width_mm` | active | 138.05 | 39.13 | - | 1.00 / 1.00 |
| `n` | active | 10.09 | 5.39 | - | 1.00 / 1.00 |
| `q` | active | 11.87 | 3.59 | - | 1.00 / 0.97 |
| `s` | active | 34.08 | 10.71 | - | 1.00 / 1.00 |
| `s1` | active | 24.23 | 15.27 | - | 1.00 / 1.00 |
| `s2` | active | 12.92 | 9.42 | - | 1.00 / 1.00 |

Envelope margin model: R^2 0.57, sign agreement 79%, inside 61%, binding {'depth_mm': 52, 'width_mm': 22, 'height_mm': 21}

## Recommendations (not applied)

- **fix** `morph_exponent`: moves no surface point at any sampled point
- **link_rejected_by_data** `k`: surface direction parallel to a_deg (|cos| 0.987); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "a_deg", "scale": -0.007597397735362253, "offset": 1.1838570251957665}`
- **rebound** `L_mm`: edge slice mostly refused/outside while the middle is not; proposal `{"lower_hi_to_unit": 0.8}`
- **rebound** `a_deg`: edge slice mostly refused/outside while the middle is not; proposal `{"lower_hi_to_unit": 0.8}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": null}`
