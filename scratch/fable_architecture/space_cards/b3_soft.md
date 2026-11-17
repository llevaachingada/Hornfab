# Space card: `klangfilm_hv_core__b3_soft`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\klangfilm_hv_2026-11-16\configs\b3_soft.yaml`; family FREEFORM; generator True. CPU only; evidence for a person, nothing applied.

- Legal sample points: 8/9; effective dimension {'median': 12.0, 'min': 12, 'max': 12, 'searched': 12}
- Box scan: {'ok': 81, 'outside': 0, 'refused': 15} (ok fraction 84%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 0%, 0.15: 0%, 0.20: 10%, 0.25: 19%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `g_beak_diagonal_mm` | active | 10.00 | 2.87 | - | 1.00 / 1.00 |
| `g_beak_h_setback_mm` | active | 10.00 | 2.42 | - | 1.00 / 1.00 |
| `g_beak_start_frac` | active | 7.64 | 0.67 | - | 1.00 / 1.00 |
| `g_beak_v_projection_mm` | active | 5.00 | 1.57 | - | 1.00 / 1.00 |
| `g_core_length_mm` | active | 240.23 | 131.95 | - | 1.00 / 0.92 |
| `g_lame_end_frac` | active | 3.20 | 0.91 | - | 1.00 / 1.00 |
| `g_lame_p_mouth` | active | 30.39 | 8.06 | - | 1.00 / 1.00 |
| `g_lame_start_frac` | active | 1.23 | 0.35 | - | 1.00 / 1.00 |
| `g_theta_h0_deg` | active | 14.80 | 5.89 | - | 1.00 / 1.00 |
| `g_theta_h1_deg` | active | 134.05 | 36.30 | - | 1.00 / 1.00 |
| `g_theta_v0_deg` | active | 12.71 | 6.92 | - | 1.00 / 1.00 |
| `g_theta_v1_deg` | active | 74.47 | 27.20 | - | 1.00 / 1.00 |

Envelope margin model: R^2 0.92, sign agreement 100%, inside 100%, binding {'width_mm': 26, 'depth_mm': 53, 'height_mm': 3}

## Recommendations (not applied)

- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.2}`
