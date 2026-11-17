# Space card: `atlas__core_law`

Config `C:\Users\hunte\Hrns\hornlab-search\examples\typologies\atlas_2026-10-30\atlas__core_law.yaml`; family OSSE; generator False. CPU only; evidence for a person, nothing applied.

- Legal sample points: 7/9; effective dimension {'median': 8.0, 'min': 5, 'max': 10, 'searched': 17}
- Box scan: {'ok': 32, 'outside': 42, 'refused': 22} (ok fraction 33%)
- Predicted bad rate by sigma0: 0.05: 8%, 0.10: 29%, 0.15: 25%, 0.20: 52%, 0.25: 58%

| knob | label | max disp mm/range | RMS mm/range | coupled | feasible lo/hi frac |
|---|---|---:|---:|---|---|
| `L_mm` | active | 1263.54 | 608.96 | - | 1.00 / 0.17 |
| `a_deg` | active | 664.18 | 319.10 | az_a_sf_amp | 1.00 / 0.17 |
| `az_a_cos_amp` | active | 197.88 | 40.50 | - | 1.00 / 0.72 |
| `az_a_cos_pow` | active | 39.40 | 15.47 | - | 1.00 / 1.00 |
| `az_a_sf_amp` | active | 1230.21 | 497.16 | a_deg | 0.53 / 0.34 |
| `az_n_cos2_amp` | active | 42.51 | 13.24 | az_s_cos2_amp | 1.00 / 1.00 |
| `az_s_cos2_amp` | active | 90.47 | 29.50 | az_n_cos2_amp | 1.00 / 1.00 |
| `az_sf_b` | active | 342.09 | 158.80 | - | 1.00 / 0.58 |
| `az_sf_n1` | active | 354.24 | 145.37 | - | 0.56 / 1.00 |
| `az_sf_n2` | active | 114.16 | 38.13 | - | 1.00 / 1.00 |
| `az_sf_n3` | active | 197.59 | 76.80 | - | 1.00 / 1.00 |
| `k` | active | 124.92 | 69.15 | - | 1.00 / 1.00 |
| `morph_corner_mm` | active | 29.39 | 2.97 | - | 1.00 / 1.00 |
| `morph_fixed` | active | 77.08 | 14.84 | morph_rate | 1.00 / 1.00 |
| `morph_rate` | active | 108.16 | 20.85 | morph_fixed | 1.00 / 1.00 |
| `n` | active | 96.68 | 33.65 | - | 0.67 / 1.00 |
| `s` | active | 322.79 | 139.54 | - | 1.00 / 0.61 |

Envelope margin model: R^2 0.78, sign agreement 83%, inside 44%, binding {'width_mm': 40, 'depth_mm': 13, 'height_mm': 22}

## Recommendations (not applied)

- **link_rejected_by_data** `a_deg`: surface direction parallel to az_a_sf_amp (|cos| 0.998); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "az_a_sf_amp", "scale": 0.3398779068206161, "offset": -6.895726738721564}`
- **link_rejected_by_data** `morph_fixed`: surface direction parallel to morph_rate (|cos| 0.987); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "morph_rate", "scale": 0.032745927214854385, "offset": -0.09823778164456315}`
- **link_rejected_by_data** `az_n_cos2_amp`: surface direction parallel to az_s_cos2_amp (|cos| 0.986); rejected: the empirical links payload has no same-sign matching pair; data_agrees=false; proposal `{"from": "az_s_cos2_amp", "scale": -2.464330096480417, "offset": 2.066795922190496}`
- **sigma0** `*`: predicted bad-candidate rate <= 15% from the seed; proposal `{"max_safe_sigma0": 0.05}`
- **constraint** `*`: envelope binds jointly; linear margin model R^2 0.78, sign right 83%, only 44% of the box inside; proposal `{"intercept_mm": 1403.970877503182, "gradient_mm_per_range": {"L_mm": -1254.6704013067188, "a_deg": -1101.6991090601625, "az_a_cos_amp": -118.93164869794589, "az_a_cos_pow": -87.79924061908116, "az_a_sf_amp": -1597.6708614877884, "az_n_cos2_amp": 277.64584434365383, "az_s_cos2_amp": -16.926485569083336, "az_sf_b": -198.99070839200138, "az_sf_n1": 45.65628958030748, "az_sf_n2": -287.45106846090414, "az_sf_n3": -55.50765862535096, "k": 208.90379121192944, "morph_corner_mm": 326.81080411891685, "morph_fixed": -80.61553733272216, "morph_rate": 80.30796770116991, "n": 562.1690193930797, "s": -107.58734262027261}}`
