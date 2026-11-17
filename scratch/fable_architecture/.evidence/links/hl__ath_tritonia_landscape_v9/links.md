# Link candidates

Run `20261117T003115Z-screen-4f7cd5` — top-decile rows: 12.

Knob pairs with |rho| >= 0.6 (top-decile), with the proposed linear link:

| a | b | rho | scale | offset | R² |
|---|---|---:|---:|---:|---:|
| `a0_deg` | `az_a_cos_amp` | +0.699 | 0.6925 | -21.04 | 0.467

### CMA covariance directions (2-3 knobs, one dominant direction)

| rank | eigenvalue | fraction | keys | loadings |
|---|---:|---:|---|---|
| 1 | 1.575 | 0.117 | `morph_corner_mm`, `az_fold_v_deg`, `morph_height_mm` | morph_corner_mm:+0.48, az_fold_v_deg:+0.48, morph_height_mm:-0.41 |
| 2 | 1.244 | 0.092 | `az_fold_v_width_deg`, `az_a_cos_amp`, `a_deg` | az_fold_v_width_deg:-0.51, az_a_cos_amp:-0.50, a_deg:-0.48 |
| 3 | 1.182 | 0.088 | `a_deg`, `q`, `az_a_cos_amp` | a_deg:-0.54, q:-0.48, az_a_cos_amp:+0.46 |

### Proposed `links:` entries (Group B)

- `az_a_cos_amp = 0.6925 * a0_deg + -21.04` (R² 0.467)
