# HANDOFF - measure and model the paper-cone mid driver + rear bowl (cone_plughorn typology)

2026-10-28. For the next agent. Goal: make `cone_plughorn` predictions (SPL at 1 W, excursion, max SPL, impedance,
directivity) accurate enough that a printed horn + a real paper-cone driver measures like the model. Read this file,
then `docs/research/typologies/CONE_MIDHORN_AXEHEAD_2026-10-28.md` (sections 5d + 6) and `docs/DRIVER_MODEL.md`.
Labels: [published] = maker sheet / patent; [measured] = our own number; [inferred] = our reasoning; [unknown].

## 1. What exists (do not rebuild)

| Piece | Where | State |
|---|---|---|
| Horn + axe head + driver bowl CAD tool | `tools/cad/plughorn.py` | Evo 7SH / Evo 2SH topology from Funktion-One's own 3D models; cone = one conical `driver` face (BEM tag 2) between a post and the cone rim, `front_gap_mm` behind the throat; bowl gross volume `rear_chamber_l()` (motor NOT subtracted) |
| Configs + briefs | `examples/typologies/cone_plughorn_2026-10-28/`, `examples/briefs/cone_midhorn_2026-10-28/` | meshed (7SH 9.4k dofs, 2SH 6.0k), never solved |
| Lumped driver circuit | `hornlab_search/driver/compression.py` (`drive`, `max_spl_db`) | written for compression drivers: Re, Le (single inductor), Bl, Mmd, Cms, Rms, Sd, front compliance V1, optional rear chamber; uses the BEM throat impedance `z_throat` over the tag-2 face |
| Source motion | `solve.source_motion: axial` (beat backends) | rigid piston along +z; the default `normal` drives the cone face along its own normal (a cos(cone angle) error, ~0.85-0.9 on a 10-inch cone) - USE `axial` for a cone |
| Velocity profile | `solve.source_profile_alpha` (fused CUDA only, WP16) | J0-shaped profile across the source; a first handle on cone break-up |
| Driver file format | `examples/drivers/_template.yaml` | add cone keys rather than a new format |
| Reference CAD | `reference/funktion-one/` (local, gitignored, F1 copyright) | DWG + ODA-converted DXF + topology JSON; no driver inside the CAD |

## 2. What Funktion-One publishes (and does not)

| Fact | Value | Label / source |
|---|---|---|
| Evo 7SH 10-inch band | 220 Hz - 4 kHz | [published] Evo 7SH spec sheet D0009-01 |
| Evo 7SH 10-inch sensitivity | 112 dB at 4.9 V, 1 m, free field (24 ohm nominal -> 1.0 W) | [published] same |
| Evo 7SH 10-inch power | 250 W AES; 1.4-inch 75 W, 114 dB at 5.6 V | [published] same |
| Evo 7SH dispersion | 40 H x 20 V; 250 Hz - 18 kHz (-3 dB) system | [published] same |
| Evo 2SH | 8-inch + 1-inch, 280 Hz - 18 kHz, 111 dB at 4 V (16 ohm -> 1 W), 200 W, 50 H x 25 V | [published] Solution One / F1 Evo 2SH sheets |
| Res 2 (older) | 8-inch mid + 1-inch, 106 dB at 4 V (16 ohm), 50 x 25 | [published] Res 2 sheet |
| Driver Thiele/Small parameters | NOT published by Funktion-One for any mid driver | [unknown] - searched 2026-10-28 |
| OEM | "Funktion-One designed drivers"; a Celestion TF1025 is sold second-hand as a "Funktion One 10-inch" (a woofer, 50 Hz-2.5 kHz, 97 dB) - NOT evidence for the mid-horn driver | [published] listing; relevance [unknown] |
| Cone material | paper ("paper across the vocal range", 8-inch to ~6.5 kHz in some boxes) | secondary (Jumble Blue critique) |

So: the absolute targets to reproduce are 112 dB/1 W (7SH, 10-inch) and 111 dB/1 W (2SH, 8-inch) in the mid band;
the driver itself must be MEASURED or substituted by a published pro mid driver.

## 3. Measurement plan (real hardware; owner buys/chooses the driver)

1. **Small-signal T/S of the actual cone driver** (free air, then added mass or known closed box):
   impedance sweep with REW / ARTA LIMP / DATS (or a Klippel LPM if available): Re, Fs, Qms, Qes, Le (and a
   2-element or Wright / L2-R2 semi-inductance fit - a 10-inch paper cone's voice-coil impedance is NOT a plain Le
   above 1 kHz), Bl, Mms, Cms, Sd (measure the effective diameter to mid-surround). Record temperature.
2. **Moving mass split**: Mms includes the driver's own air load; the BEM supplies the FRONT air load through the
   horn, so the circuit needs Mmd = Mms - front free-air load (the `compression.py` Mmd path; it flags Mms today).
3. **Cone geometry for the mesh**: cone outer/inner diameter, depth, dust-cap height/diameter (or none - the axe-head
   post sits there), surround width. These set `cone_r_mm`, `cone_depth_mm`, `post_r_mm`, `front_gap_mm`.
4. **Rear bowl**: measure the net air volume behind the cone (fill with dry rice/water in a bag, subtract the motor),
   and its damping (stuffing or not). This is the rear compliance Ca = Vb / (rho c^2) plus a loss.
5. **Validation measurements on a printed horn**: (a) impedance of driver in horn + bowl (the horn loading shows as
   damped resonances - compare with the circuit fed by the BEM z_throat); (b) on-axis SPL at 1 m and 2.83 V / 1 W,
   ground-plane or gated far field, 250 Hz-4 kHz; (c) H/V polars every 10 deg; (d) excursion at the band bottom
   (laser or dial gauge at low frequency).
6. **Cone break-up** (paper): an accelerometer/laser scan at a few frequencies, or accept the rigid-piston model up
   to ~1-1.5 kHz and treat above it as the open question (see 4.4).

## 4. Modelling plan (software)

1. **BEM**: solve the cone_plughorn mesh with `source_motion: axial`; the front chamber (`front_gap_mm`) and the
   throat ring are in the mesh, so the circuit must NOT add a second front compliance (V1 = 0).
2. **Generalise `driver/compression.py` to a cone driver** (keep the compression path byte-identical): keys `kind:
   cone`, `mmd_g` or `mms_g` + `sd_cm2`, `rear_box_l` (sealed bowl; optional `rear_box_q` loss), and an inductance
   model (`le_mh` plain, or `l2_mh`/`r2_ohm` semi-inductance). The radiating area is the cone face's area projected
   on the axis (`Sd`), and `z_throat` from BEM is already averaged over the driven face.
3. **Rear bowl in the circuit**: series compliance Vb/(rho c^2) + small air mass behind the cone; volume from
   `PlughornParams.rear_chamber_l()` minus the measured motor volume, or the measured net volume.
4. **Break-up / velocity profile**: v1 rigid piston; v2 `source_profile_alpha` fitted to a measured vibrometer
   profile or an empirical "effective radius shrinks above f_b" law; label it [inferred] until measured.
5. **Outputs** to wire into `tools/loudness_report.py --driver`: SPL at 1 W/1 m, excursion vs Xmax, max SPL
   (thermal + Xmax limited), impedance curve, efficiency. Compare against 112 dB (7SH) / 111 dB (2SH) - those are
   F1's measured system numbers with THEIR driver and processing, so expect only the order of magnitude to agree
   until our driver is measured.
6. **Stand-in drivers while the real one is unknown**: published pro 10-inch / 8-inch paper-cone MID drivers
   (e.g. B&C, Faital Pro, 18 Sound, Beyma, Celestion mid-bass/midrange lines). Fetch the datasheets yourself; put
   only published values in `examples/drivers/` (never invent a number; R9 rule); prefer ones with Mmd/Mms, Bl, Sd,
   Le given.

7. **Cone fill (front-chamber volume)**: the patents say the axe head's rear fills the cone ("eats the compression
   chamber"); the CAD carries no driver, so `plughorn.py` has no fill and `theory()` over-estimates the front air volume
   (front-chamber cut-off ~420 Hz on the Evo 7SH, too low for a 4 kHz mid). A revolved fill following the cone at a gap was
   tried on 2026-10-28 and REMOVED: union left the chamber as a detached shell, subtracting it from the air core broke the
   body. Rebuild it as part of the driver work (e.g. loft the fill and the axe-head base as ONE solid before the union).

## 5. Rules for the next agent

- Zero GPU while a night runs (CLAUDE.md GPU hygiene); mesh checks with `tools/shape_check.py` are CPU-safe.
- Research goes in one `docs/research/` file with a source table and labels; update `docs/INDEX.md`.
- Every pushed commit updates `docs/CONTINUITY.md` + `docs/ISSUES.md`.
- The 2.4-2.7 mm axe-head/throat gap is a BEM thin-gap accuracy risk: check `near_correction` and a CPU cross-check
  on one frequency before trusting the throat impedance.

## Sources (fetched 2026-10-28)

| Source | Gave |
|---|---|
| Funktion-One Evo 7SH spec sheet D0009-01 (https://musicshopellectrica.com/images/pdf-manuals/Funktion-One_Evo7SH_Spec_Sheet.pdf) | 10-inch 220 Hz-4 kHz, 112 dB at 4.9 V, 250 W AES, 24 ohm; 40 x 20 |
| Funktion-One Evo 7SH page (https://funktion-one.com/product/evo-7sh-skeletal/) | product context (page is JS-rendered) |
| Evo 2SH sheets via Solution One (https://s3.eu-central-3.ionoscloud.com/solution-one/b5156be4-907c-4cb0-a530-efca238f8e43/FRFunktionOneF1Evo2SH.pdf, search summary) | 8-inch + 1-inch, 111 dB at 4 V, 200 W, 16 ohm, 50 x 25, 280 Hz-18 kHz |
| Funktion-One Res 2 (https://www.funktion-one.com/product/res-2) | 8-inch mid 106 dB at 4 V, 50 x 25 |
| eBay listing "Funktion One Celestion TF1025" (https://www.ebay.de/itm/374329110943, search snippet only; page 403) | OEM hint only |
| Jumble Blue critique (https://www.jumble.blue/en/what-nobody-tells-you-and-admits-about-funktion-one/) | paper cones across the vocal range, axe-head history |
| Patents US6557664B1, US6650760B1, US4836327A | axe-head geometry and mounting (see the typology dossier) |
