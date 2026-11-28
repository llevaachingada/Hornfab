# Throat-sculpt geometry atlas — FAV-001 parent (2026-11-25)

Parent: FAV-001 `4140768780f0` (osse_rollback; r0 18.0 mm, source angle 2°; 700 Hz v11 CD brief). Kind
`throat_sculpt_v1` (LABELED HYPOTHESIS). Cases: `examples/typologies/throat_sculpt_2026-11-25/pilot_fav001.yaml`.
Command (CPU, pinned mesher, the search's own `build_grid_mesh`):

```powershell
.venv\Scripts\python.exe tools\geometry\throat_sculpt_pilot.py bank examples\typologies\throat_sculpt_2026-11-25\pilot_fav001.yaml --out runs\throat_sculpt_2026-11-25\bank_fav001
```

"Emitted mesh" waist = sections of the meshed wall triangles (source tag 2 excluded, quarter mirrored) — the
proof that the pinch survives meshing. Mesh verify spec: epw 6, f_max 8 kHz, throat element 3.57 mm.
Waists are minima over z ≥ 0 per plane (so an un-pinched plane reads 18.00 at the source ring).

| case | ts (resolved) | waist/r0 analytic | waist/r0 emitted mesh | z_min mm | plane ° | H waist mm | V waist mm | area/src at waist | min A/A_hull | axial occlusion | triangles |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B0_parent | parent (n_s 40) | 1.000 | 0.997 | 0 | 0 | 18.00 | 18.00 | 1.000 | 1.000 | 0.000 | 8702 |
| B0s_station | c2 1e-9 (stations only) | 1.000 | 0.997 | 0 | 0 | 18.00 | 18.00 | 1.000 | 1.000 | 0.000 | 8770 |
| S_h10 | slot_h 10 | 1.000 | 0.997 | 0 | 0 | 18.00 | 18.00 | 1.000 | 1.000 | 0.000 | 8704 |
| S_h20 | slot_h 20 | 1.000 | 0.997 | 0 | 0 | 18.00 | 18.00 | 1.000 | 0.999 | 0.000 | 8698 |
| S_h35 | slot_h 35 | 1.000 | 0.997 | 0 | 0 | 18.00 | 18.00 | 1.000 | 0.972 | 0.000 | 8674 |
| S_v20 | slot_v 20 | 1.000 | **mesher refused** | — | — | 18.00 | 18.00 | 1.000 | 0.959 | 0.000 | — |
| S_four30 | slot_h 30, slot_v 30, pow 4 | 1.000 | 0.997 | 0 | 0 | 18.00 | 18.00 | 1.000 | 0.934 | 0.000 | 8663 |
| P10_h | c2 −0.200, rise 12, fall 30 | 0.902 | 0.903 | 9 | 0 | 16.24 | 18.00 | 1.141 | 1.000 | 0.047 | 8693 |
| P20_h | c2 −0.310 | 0.800 | 0.797 | 11 | 0 | 14.40 | 18.00 | 1.218 | 0.996 | 0.099 | 8722 |
| P30_h | c2 −0.407 | 0.699 | 0.711 | 10 | 0 | 12.59 | 18.00 | 1.221 | 0.980 | 0.148 | 8751 |
| PA20_h | c2 −0.297, area kept | 0.800 | 0.797 | 11 | 0 | 14.40 | 18.00 | 1.178 | 0.998 | 0.102 | 8754 |
| PA30_h | c2 −0.387, area kept | 0.700 | 0.712 | 10 | 0 | 12.59 | 18.00 | 1.151 | 0.984 | 0.154 | 8737 |
| P20_v | c2 +0.269 (V pinch) | 0.801 | 0.802 | 11 | 90 | 18.00 | 14.41 | 1.219 | 0.996 | 0.097 | 8763 |
| P20_h_late | c2 −0.525, rise 25, fall 40 | 0.801 | 0.802 | 18 | 0 | 14.43 | 18.00 | 1.521 | 0.980 | 0.082 | 8745 |
| PA30_h_c4p | c2 −0.475, c4 +0.10, area kept | 0.700 | 0.706 | 10 | 0 | 12.59 | 18.00 | 1.149 | 0.996 | 0.211 | 8773 |
| PA30_h_c4m | c2 −0.294, c4 −0.10, area kept | 0.699 | 0.712 | 10 | 0 | 12.59 | 18.00 | 1.151 | 0.959 | 0.117 | 8754 |
| C_slot_pinch | slot_h 20 + c2 −0.223 | 0.801 | 0.804 | 12 | 0 | 14.43 | 18.00 | 1.073 | 0.999 | 0.110 | 8679 |
| X_bldlike_h | c2 −0.670, rise 20, fall 50, area kept | 0.550 | 0.550 | 16 | 0 | 9.90 | 18.00 | 1.355 | 0.936 | 0.214 | 8795 |
| X_bldfit_h | c2 −0.62, c4 −0.20, c6 +0.03, rise 25, fall 35 | 0.563 | 0.557 | 19 | 0 | 10.14 | 18.00 | 1.630 | 0.891 | 0.151 | 9004 |
| *ST260-BLD CAD (ref.)* | R-OSSE a0 = 8 − 35 sin⁴p | 0.378 | — | 25.5 | 90 | 22.25² | 4.80 | 1.868 | 0.876 | 0.210 | — |

² BLD's open plane at its waist station. Full machine-readable table: `bank_fav001.csv`.

Figures: [`atlas_sections.png`](atlas_sections.png) (sections at z 0-40 mm over the source disk and H/45°/V
meridians vs the parent; last panel = BLD CAD rotated 90° so its pinch is on H) and
[`throat_3d.png`](throat_3d.png) (mouth-on and oblique views of the first 60 mm).

## Reading

- **Slot (A)** never enters the source disk (occlusion 0), keeps the H wall on the 2° source cone for D mm and
  rejoins the parent at `max D + 40 mm`; a large H delay (35 mm) or the fourfold law already makes the
  section mildly nonconvex (A/A_hull 0.97 / 0.93) — a "vertical slot" whose sides are straight.
- **Radial (C)** produces true below-radius pinches on demand; the pinch-ratio target is hit to < 0.002·r0
  analytically and to ≤ 0.012·r0 after meshing (the 3.57 mm throat elements chord the waist slightly open at
  P30; finer throat elements would close that gap). Area-kept arms hold section area at the parent's value
  while H goes in and V goes out — the BLD near-throat mechanism (BLD: 0.97-0.99 area at 3-7 mm).
- c4 > 0 with c2 < 0 (PA30_h_c4p) pushes the diagonals in and raises occlusion to 21 % at the same H waist;
  c4 < 0 opens the diagonals and lowers it to 12 %. The BLD fit uses c4 ≈ −0.31·c2 (diagonals in **relative
  to a pure c2 law** in its own frame), giving the hourglass of `X_bldfit_h`.
- **Refusal**: `S_v20` (V delay 20 mm) is refused by the pinned mesher's symmetry-plane topology guard
  ("8 non-sliver triangles lie entirely in the y = 0 plane"); the analytic surface is regular (V row stays on
  the source cone, H row unchanged). Not chased: it is the rotated control of a lane the H cases cover.
- Packaging is unchanged by construction (mouth 587 × 450 mm, depth 260-261 mm, the parent's own).
