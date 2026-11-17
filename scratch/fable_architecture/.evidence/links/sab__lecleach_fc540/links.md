# Link candidates

Run `20261114T223630Z-screen-86e077` — top-decile rows: 15.

Knob pairs with |rho| >= 0.6 (top-decile), with the proposed linear link:

| a | b | rho | scale | offset | R² |
|---|---|---:|---:|---:|---:|
| `g_T` | `g_fc_hz` | -0.711 | -244.5 | 797.3 | 0.443

### CMA covariance directions (2-3 knobs, one dominant direction)

| rank | eigenvalue | fraction | keys | loadings |
|---|---:|---:|---|---|
| 1 | 1.631 | 0.926 | `g_T`, `g_fc_hz` | g_T:-0.99, g_fc_hz:+0.14 |
| 2 | 0.09506 | 0.054 | `g_fc_hz`, `g_stop_deg` | g_fc_hz:+0.97, g_stop_deg:-0.20 |
| 3 | 0.03505 | 0.020 | `g_stop_deg`, `g_fc_hz` | g_stop_deg:+0.98, g_fc_hz:+0.20 |

### Proposed `links:` entries (Group B)

- `g_fc_hz = -244.5 * g_T + 797.3` (R² 0.443)
