# Space card: `hl__ath_twinray380_landscape_v8`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__ath_twinray380_landscape_v8.yaml`; family OSSE; generator False. CPU only; evidence for a person, nothing applied.

- Legal sample points: 9/9; effective dimension {'median': 10.0, 'min': 9, 'max': 10, 'searched': 13}
- Box scan: {'ok': 89, 'outside': 7, 'refused': 0} (ok fraction 93%)
- Predicted bad rate by sigma0: 0.05: 0%, 0.10: 0%, 0.15: 0%, 0.20: 8%, 0.25: 2%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 249.77 | 143.44 | - | 1.00 / 0.92 |
| `a0_deg` | active | 1.47 | 0.86 | k | 1.00 / 1.00 |
| `a_deg` | active | 40.10 | 22.61 | - | 1.00 / 1.00 |
| `az_fold_v_deg` | active | 10.22 | 2.79 | - | 1.00 / 1.00 |
| `az_fold_v_width_deg` | active | 3.61 | 1.18 | - | 1.00 / 1.00 |
| `k` | active | 10.74 | 7.23 | a0_deg | 1.00 / 1.00 |
| `morph_corner_mm` | active | 21.92 | 2.80 | - | 1.00 / 1.00 |
| `morph_height_mm` | active | 214.34 | 68.17 | - | 1.00 / 1.00 |
| `morph_rate` | active | 46.51 | 18.09 | - | 1.00 / 1.00 |
| `morph_width_mm` | active | 160.50 | 47.73 | - | 1.00 / 1.00 |
| `n` | active | 11.89 | 5.59 | s | 1.00 / 1.00 |
| `q` | active | 18.07 | 7.95 | s | 1.00 / 0.98 |
| `s` | active | 34.09 | 15.10 | n, q | 1.00 / 1.00 |

Envelope margin model: R^2 0.68, sign agreement 91%, inside 93%, binding {'width_mm': 23, 'depth_mm': 44, 'height_mm': 30}

## Recommendations (not applied)

- **link_rejected_by_data** `n`: surface direction parallel to s (|cos| 0.986); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "s", "scale": -2.8316478179699796, "offset": 9.931872022467948}`
- **link_rejected_by_data** `q`: surface direction parallel to s (|cos| 0.986); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "s", "scale": 0.037309147994517664, "offset": 0.9686126224748262}`
- **link_rejected_by_data** `a0_deg`: surface direction parallel to k (|cos| 0.965); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "k", "scale": -0.4673015942767349, "offset": 1.6756666131415754}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.25}`
