# Space card: `hl__ath_tritonia_landscape_v7`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__ath_tritonia_landscape_v7.yaml`; family OSSE; generator False. CPU only; evidence for a person, nothing applied.

- Legal sample points: 9/9; effective dimension {'median': 13.0, 'min': 11, 'max': 14, 'searched': 22}
- Box scan: {'ok': 78, 'outside': 13, 'refused': 5} (ok fraction 81%)
- Predicted bad rate by sigma0: 0.05: 15%, 0.10: 40%, 0.15: 60%, 0.20: 50%, 0.25: 77%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 300.69 | 176.37 | - | 1.00 / 0.98 |
| `a0_deg` | active | 4.68 | 2.10 | - | 1.00 / 1.00 |
| `a_deg` | active | 123.40 | 64.19 | - | 1.00 / 1.00 |
| `az_a_cos2p_amp` | active | 82.87 | 19.58 | - | 1.00 / 1.00 |
| `az_a_cos2p_pow` | active | 14.44 | 4.01 | - | 1.00 / 1.00 |
| `az_fold_h_deg` | active | 59.38 | 14.90 | - | 1.00 / 1.00 |
| `az_fold_h_width_deg` | active | 15.17 | 4.17 | - | 1.00 / 1.00 |
| `az_fold_v_deg` | active | 70.85 | 22.03 | - | 1.00 / 1.00 |
| `az_fold_v_width_deg` | active | 31.56 | 9.86 | - | 1.00 / 1.00 |
| `az_s_cos2_amp` | active | 9.96 | 2.72 | - | 1.00 / 1.00 |
| `k` | active | 43.18 | 22.81 | - | 1.00 / 1.00 |
| `morph_corner_mm` | active | 33.55 | 4.15 | - | 1.00 / 1.00 |
| `morph_exponent` | inactive | 0.00 | 0.00 | - | 1.00 / 1.00 |
| `morph_fixed` | conditional | 20.98 | 7.18 | morph_rate | 1.00 / 1.00 |
| `morph_height_mm` | active | 208.33 | 62.35 | - | 1.00 / 1.00 |
| `morph_rate` | active | 202.25 | 62.68 | morph_fixed | 0.83 / 1.00 |
| `morph_width_mm` | active | 166.19 | 48.24 | - | 1.00 / 1.00 |
| `n` | active | 20.73 | 8.95 | s | 0.94 / 1.00 |
| `q` | active | 9.71 | 5.29 | - | 1.00 / 0.98 |
| `s` | active | 25.32 | 9.70 | n | 1.00 / 1.00 |
| `s1` | active | 23.76 | 15.37 | - | 1.00 / 1.00 |
| `s2` | active | 18.60 | 12.93 | - | 1.00 / 1.00 |

Envelope margin model: R^2 0.63, sign agreement 85%, inside 86%, binding {'width_mm': 29, 'depth_mm': 25, 'height_mm': 38}

## Recommendations (not applied)

- **fix** `morph_exponent`: moves no surface point at any sampled point
- **check_condition** `morph_fixed`: active at some sampled points only: its effect depends on another knob (split the lane or link the condition)
- **link** `morph_fixed`: surface direction parallel to morph_rate (|cos| 0.996); data_agrees=unknown; proposal `{"from": "morph_rate", "scale": 0.0227371302871827, "offset": -0.0682113908615481}`
- **link** `n`: surface direction parallel to s (|cos| 0.985); data_agrees=unknown; proposal `{"from": "s", "scale": -6.30387272264386, "offset": 8.112710905850701}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.05}`
