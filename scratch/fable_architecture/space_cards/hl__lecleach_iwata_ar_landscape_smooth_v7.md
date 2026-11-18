# Space card: `hl__lecleach_iwata_ar_landscape_smooth_v7`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__lecleach_iwata_ar_landscape_smooth_v7.yaml`; family FREEFORM; generator True. CPU only; evidence for a person, nothing applied.

- Legal sample points: 7/9; effective dimension {'median': 5.0, 'min': 5, 'max': 5, 'searched': 5}
- Box scan: {'ok': 63, 'outside': 0, 'refused': 33} (ok fraction 66%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 2%, 0.15: 21%, 0.20: 31%, 0.25: 42%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `g_T` | active | 35.16 | 20.78 | - | 1.00 / 1.00 |
| `g_ar_m` | active | 66.83 | 22.30 | - | 1.00 / 1.00 |
| `g_ar_p` | active | 4.15 | 1.78 | - | 1.00 / 1.00 |
| `g_fc_hz` | active | 274.05 | 156.29 | - | 0.86 / 1.00 |
| `g_stop_deg` | active | 90.60 | 43.43 | - | 0.41 / 1.00 |

Envelope margin model: R^2 0.89, sign agreement 100%, inside 100%, binding {'height_mm': 25, 'width_mm': 39}

## Recommendations (not applied)

- **rebound** `g_fc_hz`: edge slice mostly refused/outside while the middle is not; proposal `{"raise_lo_to_unit": 0.2}`
- **rebound** `g_stop_deg`: edge slice mostly refused/outside while the middle is not; proposal `{"raise_lo_to_unit": 0.2}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.1}`
