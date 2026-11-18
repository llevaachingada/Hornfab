# Link candidates

Run `20261116T043544Z-screen-dd15d8` — top-decile rows: 6.

Knob pairs with |rho| >= 0.6 (top-decile), with the proposed linear link:

| a | b | rho | scale | offset | R² |
|---|---|---:|---:|---:|---:|
| `g_crown_mm` | `g_height_mm` | -0.886 | -1.469 | 354.2 | 0.166
| `g_depth_mm` | `g_width_mm` | +0.829 | 0.4981 | 448.7 | 0.112
| `g_axial_h_mm` | `g_crown_mm` | -0.771 | -1.807 | 46.38 | 0.807
| `g_h_depth_scale` | `g_junction_power` | -0.600 | -114.1 | 147.6 | 0.094

### Proposed `links:` entries (Group B)

- `g_crown_mm = -1.807 * g_axial_h_mm + 46.38` (R² 0.807)
- `g_height_mm = -1.469 * g_crown_mm + 354.2` (R² 0.166)
- `g_width_mm = 0.4981 * g_depth_mm + 448.7` (R² 0.112)
- `g_junction_power = -114.1 * g_h_depth_scale + 147.6` (R² 0.094)
