# Phase B geometry preflight (CPU only, no solve)

Monotone integrated-slope H/V core: `theta_i(z) = theta_i0 + (theta_i1-theta_i0) Q(z/L)`,
`r_i(z) = r0 + int tan(theta_i) dz`, Lamé section with independent `p(z)`, and a late swept
beak. `cd_core_blend = 0` returns the v1 grid bit-for-bit. No acoustic result exists for any
Phase B seed; this table is geometry only.

| seed | kind | theta_H | theta_V | L mm | p mouth | area throat->mouth (mm2) | W/H/D mm | turns | lip clear mm | envelope | grid sha256 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a0 | legacy v1 (control) | 9.46 deg (parent) | 9.44 deg (parent) | - | 5.01 | 1018 -> 48471 | 541/261/234 | 1 | - | OK | `7e80214c3b280209` |
| b1 | monotone H/V core | 8.0 -> 48.0 deg | 5.0 -> 24.5 deg | 380.0 | 4.00 | 1018 -> 106551 | 480/240/380 | 0 | 19.5 | OK | `416efc4b7ad0946c` |
| b2 | monotone H/V core | 12.0 -> 50.5 deg | 4.0 -> 22.0 deg | 420.0 | 4.80 | 1018 -> 131118 | 595/233/420 | 0 | 19.5 | OK | `70cbde3d2638f6cd` |
| b3 | monotone H/V core | 7.0 -> 52.1 deg | 6.0 -> 30.4 deg | 340.0 | 3.00 | 1018 -> 111077 | 473/266/345 | 0 | 19.6 | OK | `993aef1c5018d863` |
| b4 | monotone H/V core | 7.0 -> 53.0 deg | 6.0 -> 25.0 deg | 400.0 | 3.00 | 1018 -> 130007 | 563/262/405 | 0 | 21.5 | OK | `798ee31d18a3db8c` |

`turns` counts axial sign changes on the H and V meridians (0 = a pure forward core; a
positive beak over a late gate can add one intended setback).

The `p` column is `lame_p_mouth` for the core seeds and the parent's own value for A0.

**Not a validity certificate.** `lame_shell`/`check_self_approach` and a real mesh are still
required before any Phase B solve; the lip clearance here is a sampled minimum between the last
station and the body.
