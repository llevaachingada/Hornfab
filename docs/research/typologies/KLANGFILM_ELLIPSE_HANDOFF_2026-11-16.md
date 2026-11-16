# Elliptical Klangfilm horn cell - hand-off (2026-11-16)

Status: geometry built and mesher-verified, **not queued, not committed, not owner-approved**. The owner says it still
does not look like the reference images. Contact sheet: `docs/queue/klangfilm_param_sheet.png` (one parameter changed
per row, plus 4 "closest attempts" next to the owner's references).

## Files

| file | what |
|---|---|
| `tools/geometry/klangfilm_ellipse.py` | the geometry (pure numpy): `profile()`, `make_grid()`, `validate_shape()` |
| `tools/geometry/klangfilm_ellipse_cli.py` | entry point for search / verify / shape-check / preflight (rebinds the existing rolled-rect bridge, like `rosse_rect_cli.py`; no `grid.py` change) |
| `examples/typologies/home_landscape_2026-11-15/hl__klangfilm_ellipse_smooth_v7.yaml` | search config (smooth brief) |
| `docs/queue/klangfilm_param_sheet.png` | parameter sweep contact sheet |
| `docs/queue/klangfilm_ellipse_v2.png`, `klangfilm_throat_closeup.png` | top/side/3-4 and throat views |
| owner sources | `Klangfilm_Elliptical_Horn_Calculator_diy_v10.xlsm` (uploaded); reference images `docs/queue/lecleach_refs_2026-11-16/4.png`, owner markup `5.png`; diyAudio post screenshots (construction-vector bending, stereographic projection) - in the chat only |

Commands (repo root, project venv):
```
.venv\Scripts\python.exe tools\geometry\klangfilm_ellipse_cli.py shape-check <cfg>
.venv\Scripts\python.exe tools\geometry\klangfilm_ellipse_cli.py preflight <cfg> --samples 16
.venv\Scripts\python.exe tools\geometry\klangfilm_ellipse_cli.py search --config <cfg> --mode screen --budget 60 --cma-seed 1234
```

## Where the math comes from

The owner's `.xlsm` contains a VBA macro `draw_klangfilm` by Dr. Bernd Ahlswede (Sep/Oct 2018; non-commercial use per
the author), citing B. Kolbrek, *Introduction to Horn Theory* (2007). The macro was extracted from `xl/vbaProject.bin`
(MS-OVBA decompression) and ported line by line. **Verification:** the port reproduces the workbook's stored macro output
(Sheet1 columns F-H, fc 343 Hz, throat 19 mm, stretch 1.5) to within 0.001 mm at all 9 stored stations. The workbook's
Sheet2 formulas (rotations alpha/beta and `A*x/(A+B+z)`) are only the 3D chart view (rotation animation + perspective);
they do not change the geometry.

## The formulas (SI units in the macro; mm in the port)

Inputs: cut-off `fc`, throat radius `y0` (driver exit, 18 mm here), `stretch`.

1. Spherical-wave (Klangfilm) horn:
   - `r0 = c / (pi fc)`, c = 343 m/s - radius of the spherical wavefront at the mouth; sets size AND curl radius.
   - `m = 4 pi fc / c`; `h0 = r0 - sqrt(r0^2 - y0^2)` (wavefront cap height at the throat).
   - Along the horn, cap height grows exponentially: `h(x) = h0 exp(m x)`.
   - Wavefront area = spherical cap `S = 2 pi r0 h`; equal-area radius `yh = sqrt(S/pi - h^2) = sqrt(2 r0 h - h^2)`.
   - Axial station of the wall: `xh = x - h + h0`.
   - Consequences: axial depth peaks at `h = 1/m = r0/4` (the wall turns back), the horn is widest at `h = r0`
     (`yh = r0`), and it rolls back and closes as `h -> 2 r0`. **The rollback is the profile itself**, not an added lip.
2. Elliptical stretch (Ahlswede):
   - `strm = 1 + sin( ((yh - y0)/(r0 - y0)) * pi/2 ) * (stretch - 1)` - 1 at the throat (round), `stretch` at the widest point.
   - Wavefront = tri-axial ellipsoid cap with semi-axes `ra`, `rb = r0/strm`, `c = r0`, height `h`; `ra` is solved
     (Newton in the macro, bisection in the port) so the ellipsoid cap AREA equals `2 pi r0 h`.
   - Section semi-axes: `a = ra sin(thz)`, `b = rb sin(thz)`, `thz = acos(1 - h/r0)`. H = major axis a, V = minor b.
   - Every section is a **planar ellipse** at its station `xh`.

## Parameters (search knobs, `g_` prefix in configs)

| knob | source | what it does | box | notes |
|---|---|---|---|---|
| `fc_hz` | calculator | `r0 = c/(pi fc)`: overall size, mouth size, depth and the curl radius of the rolled lip together | 480-800 | fc 560 + stretch 1.6 -> 548 x 244 mm mouth; fc < ~520 exceeds the 600 mm width |
| `stretch` | calculator | H/V aspect of the ellipse at the widest point (area-preserving) | 1.15-2.2 | 1.6 ~ 80H x 50V; 2.2 -> 630 x 177 (over envelope) |
| `end_frac` | calculator (its stop condition, as a knob) | `h_end / r0`: where the profile stops. < 1 no rollback, 1.0 = flange perpendicular to the axis, 1.85 = deep curl back toward the throat | 1.0-1.85 | does NOT change outer W/H (those peak at h = r0); changes depth and how far the lip wraps |
| `bend_radius_mm` | **ours** (owner request 2026-11-16, not in the calculator) | front arc seen from above: each azimuth row is pulled back by the sagitta `R - sqrt(R^2 - x_rim^2)` of its rim's lateral position, ramped in by smoothstep along the horn (0 at throat, full at the lip). Result: centre line forward, sides back; top/bottom (V) lips ahead of side (H) lips | 320-3000 | must exceed the half-width; 20000 = flat. A first version shifted every point by its own x: that sheared the rolled lip into a fold and the mesher refused it ("prohibited facet pairs") - fixed by the per-row rigid shift |
| `throat_ellipse` | **ours** (owner request; not in the calculator) | exponent on the calculator's stretch ramp argument: `arg^p`. 1.0 = macro (throat stays ~round for 30 mm: a/b 1.07 at z 30 mm); 0.4 -> 1.26 at 5 mm, 1.56 at 30 mm; 0.2 squeezes V below the 18 mm exit (kink) | 0.3-1.0 | the driver exit row is always exactly round (36 mm 1.4 in) |
| `wall_thickness_mm`, `n_phi`, `n_s` | mesh | shell thickness, azimuth rows (quarter model), stations | fixed 3 / 19 / 64 | |

Brief: `room_landscape_80x50_700_hf1440_v7_smooth.yaml` - a spherical-wave horn narrows with frequency (not constant
directivity), so it is scored on the smooth-directivity brief, not the CD base brief.

## Why it is set up this way

- **Bridge, not `grid.py`**: `grid.py` holds uncommitted edits by two other agents (Le Cleac'h per-plane work, `g_stop_a2`);
  the rolled-rect bridge (`rolled_rect_cli.install`) lets a standalone module supply the grid with no shared-file edits.
- **Exact port first**: the owner asked for published math; the base is the calculator verbatim and verified.
  `bend_radius_mm` and `throat_ellipse` are additions the owner asked for and are labelled as ours.
- **Quarter model** (H and V mirror symmetry), as all home cells.

## Verified (CPU, real mesher via shape-check)

Seed (fc 560, stretch 1.6, end 1.5, R 400, throat 0.4): 5,832 DOF, mouth 548 x 244 mm, depth 265 mm, round exit, fits
600 x 480 x 480. Preflight 14/16 random box samples valid. **No offline unit tests written yet** for this module
(to add: macro parity on the 9 stored stations, round exit row, bend sagitta, envelope).

## Open - why it still does not match the references

1. **Proportions.** A Klangfilm spherical-wave horn is inherently short: depth peaks at `h = r0/4` and the rest of the
   growth happens while the wall turns back, so depth ~ 0.3-0.5 x width and the body is a squat "doughnut" curl.
   The reference `4.png` is long and slender (long throat tube, depth > width). That looks like a Le Cleac'h / JMLC
   profile (sphericalhorns.net JMLC calculator) and/or the bent variants in the diyAudio post, not the base calculator.
2. **Bent variants not implemented.** The diyAudio post describes three ways to bend the planar ellipses with the
   construction vector r0 (slide points along the vector to |r0|; z-only shift; rotate the vector to end on the elliptical
   cylinder) and a stereographic projection. No equations were given; the calculator does not contain them.
3. **Curl radius is tied to fc.** In this construction the lip curl radius = r0 = c/(pi fc); an independent "lip radius"
   knob would leave the published method. If the owner wants it independent, decide how (e.g. a toroidal lip blended
   onto the profile at h = r0).
4. Next decision for the owner: keep this Klangfilm cell, or put the same three features (elliptical throat, rollback depth,
   front-arc radius) on the long Le Cleac'h profile (worktree `worktree-agent-a4731ed7e21e33eee`, saddle construction,
   commit 22829bc).

## Closest attempts on the contact sheet (row 6)

| label | fc | stretch | end | R | throat | mouth / depth |
|---|---|---|---|---|---|---|
| closest A | 450 | 1.3 | 1.85 | 330 | 0.4 | 603 x 373 / 462 (over width) |
| closest B | 500 | 1.8 | 1.8 | 340 | 0.3 | 650 x 243 / 472 (over width) |
| closest C | 600 | 1.4 | 1.7 | 280 | 0.5 | 474 x 260 / 308 (fits) |
| closest D | 420 | 1.6 | 1.6 | 380 | 0.35 | 731 x 325 / 506 (over) |
