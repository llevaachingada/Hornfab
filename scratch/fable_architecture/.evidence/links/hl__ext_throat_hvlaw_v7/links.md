# Link candidates

Run `20261115T150043Z-screen-d1ebf6` — top-decile rows: 7.

Knob pairs with |rho| >= 0.6 (top-decile), with the proposed linear link:

| a | b | rho | scale | offset | R² |
|---|---|---:|---:|---:|---:|
| `a0_deg` | `throat_ext_angle_deg` | +1.000 | 1 | -4.981e-16 | 1.000
| `a_deg` | `az_a_cos_pow` | +0.821 | 0.2806 | -5.448 | 0.751
| `a_deg` | `az_a_cos_amp` | -0.750 | -0.8256 | 39.26 | 0.699
| `az_s_cos2_amp` | `r0_mm` | +0.750 | 15.62 | 26.08 | 0.527
| `r0_mm` | `throat_ext_length_mm` | +0.750 | 8.429 | -107 | 0.699
| `L_mm` | `s` | -0.714 | -0.006602 | 2.011 | 0.429
| `a0_deg` | `r0_mm` | +0.714 | 2.029 | 16.82 | 0.602
| `r0_mm` | `throat_ext_angle_deg` | +0.714 | 0.2966 | -3.583 | 0.602
| `L_mm` | `a_deg` | +0.643 | 0.1093 | 6.356 | 0.085
| `az_a_cos_amp` | `az_a_cos_pow` | -0.643 | -0.1991 | 5.85 | 0.368
| `az_a_cos_amp` | `r0_mm` | +0.643 | 0.2883 | 19.79 | 0.268
| `az_a_cos_amp` | `throat_ext_length_mm` | +0.643 | 2.46 | 59.38 | 0.192
| `az_a_cos_pow` | `r0_mm` | -0.607 | -1.101 | 27.23 | 0.419
| `az_s_cos2_amp` | `throat_ext_length_mm` | +0.607 | 186.2 | 120.1 | 0.737

### CMA covariance directions (2-3 knobs, one dominant direction)

| rank | eigenvalue | fraction | keys | loadings |
|---|---:|---:|---|---|
| 2 | 1.108 | 0.144 | `s`, `az_a_cos_amp`, `L_mm` | s:-0.70, az_a_cos_amp:+0.42, L_mm:-0.36 |
| 3 | 1.038 | 0.135 | `az_s_cos2_amp`, `throat_ext_length_mm` | az_s_cos2_amp:+0.70, throat_ext_length_mm:-0.45 |

### Proposed `links:` entries (Group B)

- `throat_ext_angle_deg = 1 * a0_deg + -4.981e-16` (R² 1.000)
- `az_a_cos_pow = 0.2806 * a_deg + -5.448` (R² 0.751)
- `throat_ext_length_mm = 186.2 * az_s_cos2_amp + 120.1` (R² 0.737)
- `az_a_cos_amp = -0.8256 * a_deg + 39.26` (R² 0.699)
- `throat_ext_length_mm = 8.429 * r0_mm + -107` (R² 0.699)
- `throat_ext_angle_deg = 0.2966 * r0_mm + -3.583` (R² 0.602)
- `r0_mm = 2.029 * a0_deg + 16.82` (R² 0.602)
- `r0_mm = 15.62 * az_s_cos2_amp + 26.08` (R² 0.527)
- `s = -0.006602 * L_mm + 2.011` (R² 0.429)
- `r0_mm = -1.101 * az_a_cos_pow + 27.23` (R² 0.419)
- `az_a_cos_pow = -0.1991 * az_a_cos_amp + 5.85` (R² 0.368)
- `r0_mm = 0.2883 * az_a_cos_amp + 19.79` (R² 0.268)
- `throat_ext_length_mm = 2.46 * az_a_cos_amp + 59.38` (R² 0.192)
- `a_deg = 0.1093 * L_mm + 6.356` (R² 0.085)
