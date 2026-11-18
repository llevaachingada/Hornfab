# Space card: `hl__ath_tritonia_landscape_v9`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__ath_tritonia_landscape_v9.yaml`; family OSSE; generator False. CPU only; evidence for a person, nothing applied.

- Legal sample points: 9/9; effective dimension {'median': 9.0, 'min': 9, 'max': 10, 'searched': 14}
- Box scan: {'ok': 96, 'outside': 0, 'refused': 0} (ok fraction 100%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 0%, 0.15: 0%, 0.20: 0%, 0.25: 0%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 273.27 | 172.02 | - | 1.00 / 0.98 |
| `a0_deg` | active | 2.93 | 1.38 | - | 1.00 / 1.00 |
| `a_deg` | active | 10.67 | 5.69 | k | 1.00 / 1.00 |
| `az_a_cos_amp` | active | 3.28 | 1.37 | - | 1.00 / 1.00 |
| `az_fold_v_deg` | active | 1.46 | 0.49 | - | 1.00 / 1.00 |
| `az_fold_v_width_deg` | active | 3.28 | 0.99 | - | 1.00 / 1.00 |
| `k` | active | 2.85 | 1.52 | a_deg | 1.00 / 1.00 |
| `morph_corner_mm` | active | 8.32 | 0.96 | - | 1.00 / 1.00 |
| `morph_height_mm` | active | 170.65 | 56.83 | - | 1.00 / 1.00 |
| `morph_rate` | active | 37.06 | 14.51 | - | 1.00 / 1.00 |
| `morph_width_mm` | active | 158.08 | 53.48 | - | 1.00 / 1.00 |
| `n` | active | 22.95 | 12.56 | s | 1.00 / 1.00 |
| `q` | active | 22.03 | 12.40 | s | 1.00 / 1.00 |
| `s` | active | 7.01 | 3.74 | n, q | 1.00 / 1.00 |

Envelope margin model: R^2 0.69, sign agreement 96%, inside 100%, binding {'height_mm': 41, 'depth_mm': 32, 'width_mm': 24}

## Recommendations (not applied)

- **link_rejected_by_data** `s`: surface direction parallel to q (|cos| 0.990); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "q", "scale": 0.7879502501437736, "offset": 0.18752052497585858}`
- **link_rejected_by_data** `k`: surface direction parallel to a_deg (|cos| 0.966); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "a_deg", "scale": -0.005859586782283339, "offset": 1.463877576127471}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.25}`
