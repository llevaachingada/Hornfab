# Space card: `hl__es_style_rollback_v7`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__es_style_rollback_v7.yaml`; family FREEFORM; generator True. CPU only; evidence for a person, nothing applied.

- Legal sample points: 9/9; effective dimension {'median': 5.0, 'min': 4, 'max': 5, 'searched': 5}
- Box scan: {'ok': 94, 'outside': 0, 'refused': 2} (ok fraction 98%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 0%, 0.15: 2%, 0.20: 6%, 0.25: 2%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `g_T` | active | 28.81 | 19.17 | - | 1.00 / 1.00 |
| `g_ar_m` | active | 47.76 | 12.40 | - | 1.00 / 1.00 |
| `g_ar_p` | active | 8.41 | 3.77 | - | 1.00 / 1.00 |
| `g_fc_hz` | active | 153.31 | 95.59 | - | 1.00 / 1.00 |
| `g_stop_deg` | conditional | 26.02 | 14.42 | - | 1.00 / 1.00 |

Envelope margin model: R^2 0.99, sign agreement 100%, inside 100%, binding {'width_mm': 95}

## Recommendations (not applied)

- **check_condition** `g_stop_deg`: active at some sampled points only: its effect depends on another knob (split the lane or link the condition)
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.25}`
