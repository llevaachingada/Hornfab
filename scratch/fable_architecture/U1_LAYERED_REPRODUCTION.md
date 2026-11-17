# N4 — U1: can a layered form reproduce existing horns?

Run: 2026-11-17, HEAD `caa37d0`. Read-only, CPU only; no mesh build, no solve, no pytest, no git
mutation. Scripts: `scratch/fable_architecture/.u1/u1.py`. Inputs: `.fable/rows.pkl`; the stored
recipes/configs of the best valid design of each lane; the N1b build routes. Records: `.u1/u1.json`,
`.u1/<lane>.png` (five section overlays).

§0 gate (run once for the session): `parity smoke: worst regenerated-vs-stored DI ...: 0.0 n 17`.

## Headline

1. **The layered description with three ribs and one superellipse per station does not reproduce any
   of the five horns.** Own-rib (exact ψ) worst deviations: ext-throat 48.26 mm, biradial 3.43,
   Crowe 29.90, rolled 48.25, Klangfilm 3.88. Zero of five lanes is at or under 0.5 mm, and all five
   are above 2 mm, so **the brief's N4 failure line is met and this is handed back.**
2. **The failure is the section law, not azimuth sampling.** Every rib is reproduced exactly
   (identity check ≤6e-14 mm), so 0°/45°/90° are matched by construction. The superellipse then
   misses the intermediate azimuths by up to 48 mm: given the three radii, the exponent needed to
   match the 45° radius makes the section far too boxy at 30–60°. Adding azimuth ribs and replacing
   the superellipse by a Pchip blend fixes most of it: 5 ribs → worst 1.00–27.08 mm, 9 ribs → 0.25–11.43,
   17 ribs → 0.12–3.36. **Only ext-throat reaches 0.5 mm at the brief's ladder (9 ribs, 0.25 mm);
   the other four need finer than every 11.25°.**
3. **Replacing each rib's ψ with a spline through 4/6/8 control values is much worse than keeping it
   exact** — worst 8.97–208.11 mm. ψ is not a compact descriptor at the lip: the rolled and Klangfilm
   lips turn through a large angle within a few stations, and a Pchip through 4–8 samples smooths the
   turn away. The 3-rib exact-ψ form is the best compact form measured here, and it still fails.

## Design used per lane

| Lane | design | run | stored J |
|---|---|---|---:|
| `hl__ext_throat_hvlaw_v7` | `3a1038da45d0` | `20261115T143219Z-screen-d3a1bb` | 3.103 |
| `hl__biradial_es_style_v7` | `d24016b7ab8a` | `20261116T090751Z-screen-37b115` | 6.447 |
| `hl__crowe_x_osse_cd_v7` | `77308ed8afa3` | `20261116T074832Z-screen-620f81` | 5.344 |
| `rf__section_axial_home_v7` | `eb9cd62fbc3f` | `20261116T020629Z-screen-0d29d7` | 17.397 |
| `hl__klangfilm_lame_curved_v1` | `563037821c92` | `20261116T224336Z-screen-55f39d` | 8.634 |

Best valid design of each lane by stored J (within-lane only; Klangfilm restricted to
digest-verified rows). Rolled substitutes for lecleach per N1b (lecleach is not reproducible at HEAD).

## Method

Target surface = the contract-v2 record (65 stations × 61 azimuths; 1.5° step), built from the
generator, not from the mesh. Per design:

1. Ribs at azimuth 0°, 45°, 90°; per rib the step lengths Δs and the wall angle ψ of each step from
   the +z axis. Rebuilding each rib from ψ and Δs returns it within **≤6e-14 mm** on all five lanes
   (the runbook's 0.01 mm check passes).
2. At each station a superellipse through the 0° radius `a` and 90° radius `b`, with `p` solved so the
   45° radius is matched; `p` clipped to [1, 16], clipped stations counted.
3. Depth at each azimuth from the three ribs' depths, piecewise-linear in the superellipse's own
   parametric angle θ. The runbook leaves this blend open; this is the section's own blend, and it is
   exact at 0/45/90°.
4. Compare with the target at all 65 × 61 points. Worst-point region: first 10 % of stations = throat,
   last 15 % = lip, else body; azimuth 30–60° = corner.

## Result table — own-rib (exact ψ) rebuild, mm

| Lane | median | p95 | worst | worst region | clipped stations (p = 16) | verdict |
|---|---:|---:|---:|---|---:|---|
| ext-throat | 3.875 | 22.889 | **48.259** | lip / corner, station 58, φ 30.0° | 36/65 | fail |
| biradial | 0.375 | 2.761 | **3.427** | body, station 26, φ 25.5° | 0/65 | fail |
| Crowe | 1.989 | 17.334 | **29.898** | lip / corner, station 64, φ 31.5° | 45/65 | fail |
| rolled | 2.012 | 28.098 | **48.246** | lip, station 60, φ 18.0° | 46/65 | fail |
| Klangfilm | 0.500 | 2.527 | **3.876** | body / corner, station 28, φ 37.5° | 0/65 | fail |

Pass line (brief): own-rib rebuild worst ≤ 0.5 mm for at least three lanes → **0 of 5**.
Failure line: two or more lanes above 2 mm → **5 of 5; met.**

### Why the worst points are where they are

- **ext-throat, station 58:** radii 247.9 (0°) → 212.2 (45°) → 149.3 (90°), target 30° radius 230.7.
  The 45° radius forces `p = 16` (and is still 1.4 mm short of the p-16 value), which makes the section
  near-rectangular: the model gives 279.0 at 30° (+48.3 mm) and 256.7 at 15° (+13.3), while it is low
  at 60° (172.4 vs 190.5). No exponent in [1, 16] matches both the 45° and 30° radii — the section is
  not in the superellipse family.
- **rolled, station 60:** the lip's depth varies by 109 mm around the quadrant (z = 129.1 at 0°,
  186.5 at 18°, 238.0 at 90°), and the radius drops 297.7 → 242.5 → 139.4. The superellipse is right at
  the three ribs and 34 mm high at 18°; the parametric depth blend is 24 mm low there. Both the section
  law and the depth blend fail on a rolled lip.
- **Crowe, station 64:** the rectangular corner is exactly the shape a 3-rib superellipse cannot pin;
  45/65 stations sit at the p = 16 clip.
- **biradial and Klangfilm** are the mildest (3.4 / 3.9 mm), both failing at the 25–40° corner.

## ψ splines (4, 6, 8 control values) — worst deviation, mm

| Lane | 4 | 6 | 8 | exact-ψ 3-rib for comparison |
|---|---:|---:|---:|---:|
| ext-throat | 73.89 | 48.63 | 44.36 | 48.26 |
| biradial | 23.74 | 11.88 | 8.97 | 3.43 |
| Crowe | 39.85 | 29.60 | 28.65 | 29.90 |
| rolled | 208.11 | 148.54 | 118.03 | 48.25 |
| Klangfilm | 162.14 | 96.75 | 66.73 | 3.88 |

Except for ext-throat at 4 controls, smoothing ψ is never better than keeping it exact. ψ must be
sampled where it turns (the lip), so a spline on 4–8 equally spaced values is the wrong compression:
the largest errors (rolled, Klangfilm) are lip values.

## Extra azimuth ribs — worst deviation, mm (superellipse replaced by a Pchip blend through the ribs)

| Lane | 5 ribs (22.5°) | 9 ribs (11.25°) | 17 ribs (~5.5°) |
|---|---:|---:|---:|
| ext-throat | 1.00 | **0.25** | 0.12 |
| biradial | 2.12 | 1.04 | 0.53 |
| Crowe | 17.37 | 4.78 | 2.21 |
| rolled | 27.08 | 11.43 | 3.36 |
| Klangfilm | 11.34 | 1.89 | 0.95 |

The answer to the brief's question: **at 22.5° and 67.5° (5 ribs) no lane reaches 0.5 mm; at every
11.25° (9 ribs) only ext-throat does (0.25 mm). The other four do not reach 0.5 mm even at ~5.5°
(17 ribs), so for those lanes the azimuth-rib count alone is not the limit either — the section and
depth laws are.** Klangfilm is non-monotone (3 ribs 3.88 → 5 ribs 11.34): the superellipse happened to
fit better than the 5-rib Pchip near a curved section.

## Mesh difference, reported separately (runbook N4 change)

For lanes recorded as "mesh departs from design at corners", U1's target is the **generator's
surface**, so the numbers above are design-surface reproduction. The mesh difference measured in N1b,
on the same record, is:

| Lane | inner-wall record p99 vs mesh (N1b) | envelope excess vs mesh (N1b) |
|---|---:|---|
| Crowe | 1.353 mm | up to 1.64 mm at W/H |
| rolled | 0.856 mm | up to 0.70 mm at W/H |
| biradial | 0.101 mm | ≤1.42 mm at the rim (5/10 designs) |
| ext-throat | 0.108 mm | ≤1.41 mm on H |
| Klangfilm | 1.155 mm | ≤0.12 mm |

These are one to two orders below the layered deviations above, so the N4 failure is not a mesh
artefact.

## Verdict against the brief's lines

- **Pass line:** own-rib rebuild worst ≤ 0.5 mm on at least three lanes → **0 of 5. Not met.**
- **Failure line:** two or more lanes above 2 mm → **5 of 5. Met.**
- **Extra-rib report:** given above; only ext-throat reaches 0.5 mm within the brief's ladder.
- **Overlay pictures:** one per lane in `.u1/`; the ext-throat sheet shows the failure directly (boxy
  rebuild against the smooth target at stations 32–64).

## What failed / what is unknown

- **Three ribs + one superellipse is not a sufficient section law** for any of the five lanes. The
  fitted exponent is forced by the 45° radius and then mis-shapes 15–70°.
- **ψ is not compact.** A spline through 4–8 ψ values is worse than the exact rib in four of five
  lanes; no tested control count is usable. Unknown: whether control points placed at the lip's
  curvature peaks (rather than equally spaced) would fix it; not tested, because the brief fixes
  equally spaced controls.
- **The depth law was not isolated.** The runbook leaves the depth blend open; this run uses the
  superellipse's parametric angle. Rolled's lip shows a 24 mm depth error at 18°, but the radius is
  also 34 mm off there, so the two are not separated. A depth-only test at the exact rib radii would
  settle it.
- **Whether a different section family fixes it** (e.g. two exponents, a rounded-rectangle
  construction, or a per-quadrant blend) is untested. That is a design decision, not a measurement.
- **No lane passes, so U2 and U3 were not run** (the task list conditions them on N4 passing).

## What this does not prove

- Nothing acoustic: no response, solve or score.
- That the horns cannot be described compactly — only that this layered description (3 ribs +
  superellipse + parametric depth, and ψ splines) does not describe them within 0.5 mm.
- That the canonical record is wrong: N1b showed it reproduces the mesh; U1 shows the compression of
  that record into the layered form fails.

## Next action enabled

**Hand back (N4 failure line met).** The generator decision needs a high-thinking pass: either the
layered description's section and depth laws are redesigned (two exponents, a rounded-rectangle
section, curvature-placed ψ knots, a depth law per side), or the plan accepts the record itself as
the description and drops the "compact layered backbone" claim. U2/U3 remain conditional and were not
run.

## Reproduce

```powershell
# from C:\Users\hunte\Hrns\hornlab-search
git rev-parse --short HEAD
.venv/Scripts/python.exe scratch/fable_architecture/.tmp/fable_replay_harness.py
.venv/Scripts/python.exe scratch/fable_architecture/.u1/u1.py
```

`u1.py` writes `.u1/u1.json` and the five PNGs. No file outside `scratch/fable_architecture/` was
written; `runs/`, `examples/`, `hornlab_search/` and `tools/` were read only.
