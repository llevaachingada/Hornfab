# Space card: `hl__ath_core_petal_hvlaw_v7`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__ath_core_petal_hvlaw_v7.yaml`; family OSSE; generator False. CPU only; evidence for a person, nothing applied.

- Legal sample points: 9/9; effective dimension {'median': 6.0, 'min': 6, 'max': 7, 'searched': 11}
- Box scan: {'ok': 60, 'outside': 36, 'refused': 0} (ok fraction 62%)
- Predicted bad rate by sigma0: 0.05: 2%, 0.10: 44%, 0.15: 46%, 0.20: 52%, 0.25: 58%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 256.43 | 143.94 | - | 1.00 / 0.28 |
| `a0_deg` | active | 1.81 | 1.20 | - | 1.00 / 1.00 |
| `a_deg` | active | 182.36 | 85.71 | az_a_sf_amp | 1.00 / 0.28 |
| `az_a_cos_amp` | active | 189.81 | 57.89 | - | 1.00 / 0.31 |
| `az_a_cos_pow` | active | 49.72 | 15.17 | - | 1.00 / 1.00 |
| `az_a_sf_amp` | active | 74.67 | 31.67 | a_deg | 1.00 / 0.69 |
| `az_s_cos2_amp` | active | 51.45 | 16.61 | - | 1.00 / 0.73 |
| `k` | active | 40.78 | 27.21 | - | 1.00 / 1.00 |
| `n` | active | 77.34 | 39.18 | s | 0.44 / 1.00 |
| `q` | active | 35.41 | 13.87 | s | 1.00 / 0.81 |
| `s` | active | 68.60 | 34.60 | n, q | 1.00 / 0.83 |

Envelope margin model: R^2 0.81, sign agreement 82%, inside 63%, binding {'height_mm': 9, 'depth_mm': 37, 'width_mm': 51}

## Recommendations (not applied)

- **link_rejected_by_data** `q`: surface direction parallel to s (|cos| 0.994); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "s", "scale": 0.14971671194333722, "offset": 0.8745675510289141}`
- **link_rejected_by_data** `az_a_sf_amp`: surface direction parallel to a_deg (|cos| 0.984); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "a_deg", "scale": 0.1207411840326426, "offset": 0.10221158321657775}`
- **rebound** `q`: edge slice mostly refused/outside while the middle is not; proposal `{"lower_hi_to_unit": 0.8}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.05}`
- **constraint** `*`: envelope binds jointly; linear margin model R^2 0.81, sign right 82%, only 63% of the box inside; proposal `{"intercept_mm": 622.6322108617214, "gradient_mm_per_range": {"L_mm": -404.3298887609985, "a0_deg": -20.838726425393276, "a_deg": -306.82161042957387, "az_a_cos_amp": -282.9386877317305, "az_a_cos_pow": 21.692234122247697, "az_a_sf_amp": -96.69233134092049, "az_s_cos2_amp": -88.71925005858478, "k": 29.845806430886057, "n": 200.7425446046785, "q": -99.14565116197846, "s": -195.04768932044223}}`
