# Link candidates

Run `20261115T020650Z-screen-22931c` — top-decile rows: 25.

Knob pairs with |rho| >= 0.6 (top-decile), with the proposed linear link:

| a | b | rho | scale | offset | R² |
|---|---|---:|---:|---:|---:|
| `a0_deg` | `az_a_cos_amp` | -0.708 | -15.24 | 32.52 | 0.523
| `az_a_cos_amp` | `s1` | -0.681 | -0.005615 | 1.266 | 0.297
| `az_s_cos2_amp` | `morph_fixed` | -0.610 | -0.2906 | 0.01887 | 0.311
| `morph_corner_mm` | `morph_exponent` | -0.605 | -0.03876 | 5.098 | 0.436
| `k` | `morph_fixed` | +0.603 | 0.03907 | -0.02484 | 0.338

### CMA covariance directions (2-3 knobs, one dominant direction)

| rank | eigenvalue | fraction | keys | loadings |
|---|---:|---:|---|---|
| 1 | 1.288 | 0.073 | `morph_height_mm`, `s1`, `n` | morph_height_mm:+0.48, s1:-0.46, n:-0.41 |
| 2 | 1.157 | 0.066 | `morph_rate`, `s1`, `s2` | morph_rate:+0.51, s1:+0.43, s2:-0.39 |
| 3 | 1.13 | 0.064 | `morph_width_mm`, `s2`, `az_a_sf_amp` | morph_width_mm:-0.66, s2:-0.29, az_a_sf_amp:+0.27 |

### Proposed `links:` entries (Group B)

- `az_a_cos_amp = -15.24 * a0_deg + 32.52` (R² 0.523)
- `morph_exponent = -0.03876 * morph_corner_mm + 5.098` (R² 0.436)
- `morph_fixed = 0.03907 * k + -0.02484` (R² 0.338)
- `morph_fixed = -0.2906 * az_s_cos2_amp + 0.01887` (R² 0.311)
- `s1 = -0.005615 * az_a_cos_amp + 1.266` (R² 0.297)
