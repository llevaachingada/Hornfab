# Space card: `rf__section_axial_home_v7`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\rolled_family_2026-11-15\rf__section_axial_home_v7.yaml`; family FREEFORM; generator True. CPU only; evidence for a person, nothing applied.

- Legal sample points: 9/9; effective dimension {'median': 8.0, 'min': 8, 'max': 8, 'searched': 8}
- Box scan: {'ok': 89, 'outside': 3, 'refused': 4} (ok fraction 93%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 6%, 0.15: 15%, 0.20: 29%, 0.25: 23%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `g_axial_h_mm` | active | 13.25 | 2.29 | - | 1.00 / 1.00 |
| `g_axial_v_mm` | active | 15.64 | 4.93 | - | 1.00 / 1.00 |
| `g_crown_mm` | active | 46.08 | 8.88 | - | 1.00 / 1.00 |
| `g_depth_mm` | active | 134.46 | 78.87 | - | 1.00 / 1.00 |
| `g_h_depth_scale` | active | 36.61 | 14.85 | - | 1.00 / 1.00 |
| `g_height_mm` | active | 184.90 | 64.20 | - | 1.00 / 1.00 |
| `g_junction_power` | active | 6.46 | 0.86 | - | 1.00 / 1.00 |
| `g_width_mm` | active | 63.19 | 21.82 | - | 1.00 / 0.75 |

Envelope margin model: R^2 0.98, sign agreement 99%, inside 96%, binding {'height_mm': 4, 'width_mm': 89}

## Recommendations (not applied)

- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.15}`
