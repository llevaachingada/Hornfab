# Link candidates

Run `20261115T161238Z-screen-1b1b6e` — top-decile rows: 8.

Knob pairs with |rho| >= 0.6 (top-decile), with the proposed linear link:

| a | b | rho | scale | offset | R² |
|---|---|---:|---:|---:|---:|
| `g_T` | `g_ar_m` | +0.762 | 0.6212 | 1.14 | 0.489

### CMA covariance directions (2-3 knobs, one dominant direction)

| rank | eigenvalue | fraction | keys | loadings |
|---|---:|---:|---|---|
| 1 | 2.052 | 0.423 | `g_stop_deg`, `g_ar_m` | g_stop_deg:+0.82, g_ar_m:+0.39 |
| 2 | 1.223 | 0.252 | `g_fc_hz`, `g_T` | g_fc_hz:+0.78, g_T:+0.54 |
| 3 | 0.6052 | 0.125 | `g_ar_m`, `g_T` | g_ar_m:+0.85, g_T:+0.40 |

### Proposed `links:` entries (Group B)

- `g_ar_m = 0.6212 * g_T + 1.14` (R² 0.489)
