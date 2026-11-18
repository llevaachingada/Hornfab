# Link candidates

Run `20261117T071329Z-screen-e4f90d` — top-decile rows: 11.

Knob pairs with |rho| >= 0.6 (top-decile), with the proposed linear link:

| a | b | rho | scale | offset | R² |
|---|---|---:|---:|---:|---:|
| `g_beak_diagonal_mm` | `g_lame_start_frac` | +0.727 | 0.007169 | 0.1995 | 0.386
| `g_beak_h_setback_mm` | `g_beak_v_projection_mm` | -0.727 | -0.2311 | 1.509 | 0.495
| `g_beak_v_projection_mm` | `g_theta_h0_deg` | -0.682 | -0.9864 | 7.293 | 0.320

### CMA covariance directions (2-3 knobs, one dominant direction)

| rank | eigenvalue | fraction | keys | loadings |
|---|---:|---:|---|---|
| 1 | 2.608 | 0.208 | `g_theta_v1_deg`, `g_lame_p_mouth`, `g_beak_v_projection_mm` | g_theta_v1_deg:-0.58, g_lame_p_mouth:-0.49, g_beak_v_projection_mm:+0.38 |
| 2 | 1.158 | 0.092 | `g_theta_v0_deg`, `g_beak_diagonal_mm` | g_theta_v0_deg:-0.74, g_beak_diagonal_mm:+0.40 |
| 3 | 1.111 | 0.088 | `g_beak_h_setback_mm`, `g_beak_start_frac` | g_beak_h_setback_mm:-0.71, g_beak_start_frac:+0.55 |

### Proposed `links:` entries (Group B)

- `g_beak_v_projection_mm = -0.2311 * g_beak_h_setback_mm + 1.509` (R² 0.495)
- `g_lame_start_frac = 0.007169 * g_beak_diagonal_mm + 0.1995` (R² 0.386)
- `g_theta_h0_deg = -0.9864 * g_beak_v_projection_mm + 7.293` (R² 0.320)
