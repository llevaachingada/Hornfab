# Space card: `hl__ext_throat_hvlaw_v7`

Config `examples/typologies/home_landscape_2026-11-15/hl__ext_throat_hvlaw_v7.yaml`; family OSSE; generator False. CPU only; evidence for a person, nothing applied.

- Legal sample points: 7/7; effective dimension {'median': 8.0, 'min': 7, 'max': 8, 'searched': 8}
- Box scan: {'ok': 27, 'outside': 37, 'refused': 0} (ok fraction 42%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 6%, 0.15: 34%, 0.20: 38%, 0.25: 34%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 230.50 | 125.42 | - | 1.00 / 0.38 |
| `a_deg` | active | 182.32 | 97.72 | - | 1.00 / 0.27 |
| `az_a_cos_amp` | active | 182.32 | 57.77 | - | 1.00 / 0.38 |
| `az_a_cos_pow` | active | 68.34 | 25.03 | - | 1.00 / 1.00 |
| `az_s_cos2_amp` | active | 87.32 | 28.73 | - | 1.00 / 0.53 |
| `s` | active | 69.85 | 37.04 | - | 1.00 / 0.77 |
| `throat_ext_angle_deg` | active | 9.42 | 2.78 | - | 1.00 / 1.00 |
| `throat_ext_length_mm` | active | 160.00 | 106.48 | - | 1.00 / 1.00 |

Envelope margin model: R^2 0.91, sign agreement 91%, inside 43%, binding {'width_mm': 43, 'depth_mm': 14, 'height_mm': 8}

## Recommendations (not applied)

- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.1}`
- **constraint** `*`: envelope binds jointly; linear margin model R^2 0.91, sign right 91%, only 43% of the box inside; proposal `{"intercept_mm": 523.1149608760212, "gradient_mm_per_range": {"L_mm": -335.81138572035826, "a_deg": -368.1871093761526, "az_a_cos_amp": -306.9453804888999, "az_a_cos_pow": 8.35695306935014, "az_s_cos2_amp": -92.66603232366332, "s": -112.86380775091963, "throat_ext_angle_deg": 18.65025653623823, "throat_ext_length_mm": -0.19641170502096053}}`
