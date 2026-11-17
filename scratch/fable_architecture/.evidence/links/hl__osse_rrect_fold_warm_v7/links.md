# Link candidates

Run `20261116T153619Z-screen-c221aa` — top-decile rows: 10.

Knob pairs with |rho| >= 0.6 (top-decile), with the proposed linear link:

| a | b | rho | scale | offset | R² |
|---|---|---:|---:|---:|---:|
| `az_fold_v_deg` | `q` | +0.855 | 0.0004035 | 0.966 | 0.626
| `az_a_cos_amp` | `az_s_cos2_amp` | +0.709 | 0.0237 | -0.3872 | 0.669
| `az_s_cos2_amp` | `q` | -0.697 | -0.1598 | 0.9346 | 0.326
| `az_fold_h_width_deg` | `morph_height_mm` | -0.685 | -0.4848 | 416.5 | 0.561
| `L_mm` | `morph_rate` | -0.661 | -0.02809 | 11.38 | 0.561
| `L_mm` | `morph_width_mm` | +0.661 | 0.6494 | 404.3 | 0.275
| `a0_deg` | `az_a_cos_amp` | -0.648 | -5.13 | 21.15 | 0.509
| `morph_rate` | `n` | +0.636 | 0.8444 | 2.394 | 0.263
| `L_mm` | `a0_deg` | +0.624 | 0.007738 | 0.3209 | 0.299
| `az_fold_h_width_deg` | `az_fold_v_width_deg` | -0.624 | -0.452 | 26.26 | 0.283
| `a_deg` | `morph_height_mm` | +0.600 | 5.472 | 187.8 | 0.357

### CMA covariance directions (2-3 knobs, one dominant direction)

| rank | eigenvalue | fraction | keys | loadings |
|---|---:|---:|---|---|
| 1 | 1.302 | 0.074 | `morph_width_mm`, `s`, `L_mm` | morph_width_mm:-0.56, s:+0.41, L_mm:-0.37 |
| 2 | 1.225 | 0.069 | `az_a_cos_amp`, `a0_deg`, `az_a_cos_pow` | az_a_cos_amp:-0.53, a0_deg:+0.41, az_a_cos_pow:-0.40 |

### Proposed `links:` entries (Group B)

- `az_s_cos2_amp = 0.0237 * az_a_cos_amp + -0.3872` (R² 0.669)
- `q = 0.0004035 * az_fold_v_deg + 0.966` (R² 0.626)
- `morph_height_mm = -0.4848 * az_fold_h_width_deg + 416.5` (R² 0.561)
- `morph_rate = -0.02809 * L_mm + 11.38` (R² 0.561)
- `az_a_cos_amp = -5.13 * a0_deg + 21.15` (R² 0.509)
- `morph_height_mm = 5.472 * a_deg + 187.8` (R² 0.357)
- `q = -0.1598 * az_s_cos2_amp + 0.9346` (R² 0.326)
- `a0_deg = 0.007738 * L_mm + 0.3209` (R² 0.299)
- `az_fold_v_width_deg = -0.452 * az_fold_h_width_deg + 26.26` (R² 0.283)
- `morph_width_mm = 0.6494 * L_mm + 404.3` (R² 0.275)
- `n = 0.8444 * morph_rate + 2.394` (R² 0.263)
