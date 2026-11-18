# Space card: `hl__crowe_x_osse_cd_v7`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\home_landscape_2026-11-15\hl__crowe_x_osse_cd_v7.yaml`; family FREEFORM; generator True. CPU only; evidence for a person, nothing applied.

- Legal sample points: 5/9; effective dimension {'median': 7.0, 'min': 7, 'max': 7, 'searched': 9}
- Box scan: {'ok': 73, 'outside': 0, 'refused': 23} (ok fraction 76%)
- Predicted bad rate by sigma0: 0.05: 50%, 0.10: 48%, 0.15: 44%, 0.20: 52%, 0.25: 52%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `g_L_mm` | active | 123.56 | 65.35 | - | 1.00 / 0.03 |
| `g_a_h_deg` | active | 43.98 | 16.68 | - | 1.00 / 0.03 |
| `g_a_v_deg` | active | 30.56 | 13.63 | - | 1.00 / 1.00 |
| `g_n` | active | 17.68 | 9.76 | - | 0.17 / 1.00 |
| `g_r_lip_mm` | active | 42.01 | 25.73 | g_wrap_deg | 1.00 / 0.06 |
| `g_s` | active | 55.70 | 25.56 | - | 1.00 / 0.06 |
| `g_sf_ab` | active | 32.40 | 12.16 | - | 0.05 / 1.00 |
| `g_sf_amt` | active | 33.54 | 9.82 | - | 0.28 / 1.00 |
| `g_wrap_deg` | active | 18.92 | 10.76 | g_r_lip_mm | 1.00 / 1.00 |

Envelope margin model: R^2 0.98, sign agreement 100%, inside 100%, binding {'height_mm': 10, 'width_mm': 64}

## Recommendations (not applied)

- **link_rejected_by_data** `g_wrap_deg`: surface direction parallel to g_r_lip_mm (|cos| 0.964); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "g_r_lip_mm", "scale": 1.4936322256210983, "offset": 58.77680962105438}`
- **rebound** `g_L_mm`: edge slice mostly refused/outside while the middle is not; proposal `{"lower_hi_to_unit": 0.8}`
- **rebound** `g_s`: edge slice mostly refused/outside while the middle is not; proposal `{"lower_hi_to_unit": 0.8}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": null}`
- **queue gate (2026-11-18)**: `no_headroom` — seed hash `9b5428e6dec8` equals the prior best; not queueable without `search.warm_start` + a stated refinement reason (a bound trim alone re-tests the optimum).
