# Space card: `hl__lecleach_hv_landscape_smooth_v7`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__lecleach_hv_landscape_smooth_v7.yaml`; family FREEFORM; generator True. CPU only; evidence for a person, nothing applied.

- Legal sample points: 8/9; effective dimension {'median': 5.0, 'min': 4, 'max': 5, 'searched': 5}
- Box scan: {'ok': 83, 'outside': 0, 'refused': 13} (ok fraction 86%)
- Predicted bad rate by sigma0: 0.05: 17%, 0.10: 42%, 0.15: 52%, 0.20: 58%, 0.25: 54%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `g_T` | active | 43.16 | 27.69 | - | 1.00 / 1.00 |
| `g_fc_h_hz` | active | 217.71 | 95.68 | - | 0.61 / 1.00 |
| `g_fc_v_hz` | active | 155.21 | 96.38 | - | 1.00 / 1.00 |
| `g_stop_a2` | active | 25.02 | 10.51 | - | 1.00 / 0.66 |
| `g_stop_deg` | active | 25.06 | 11.49 | - | 1.00 / 0.89 |

Envelope margin model: R^2 0.69, sign agreement 100%, inside 100%, binding {'height_mm': 53, 'width_mm': 31}

## Recommendations (not applied)

- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": null}`
