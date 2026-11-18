# Link candidates

Run `20261115T162516Z-screen-e31b23` — top-decile rows: 8.

Knob pairs with |rho| >= 0.6 (top-decile), with the proposed linear link:

| a | b | rho | scale | offset | R² |
|---|---|---:|---:|---:|---:|
| `g_fc_hz` | `g_stop_deg` | +0.667 | 0.4676 | -100 | 0.527

### CMA covariance directions (2-3 knobs, one dominant direction)

| rank | eigenvalue | fraction | keys | loadings |
|---|---:|---:|---|---|
| 1 | 2.59 | 0.636 | `g_stop_deg`, `g_ar_m` | g_stop_deg:-0.81, g_ar_m:-0.52 |
| 2 | 0.7982 | 0.196 | `g_ar_m`, `g_stop_deg` | g_ar_m:+0.84, g_stop_deg:-0.44 |
| 3 | 0.5059 | 0.124 | `g_ar_p`, `g_stop_deg` | g_ar_p:-0.90, g_stop_deg:-0.36 |

### Proposed `links:` entries (Group B)

- `g_stop_deg = 0.4676 * g_fc_hz + -100` (R² 0.527)
