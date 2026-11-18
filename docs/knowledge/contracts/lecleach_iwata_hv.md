# Contract: Le Cleac'h / Iwata-AR and the H/V ellipsoidal pair (cross-check)

Date: 2026-11-18. Repo: HornFab main @1d6ebc8 (read-only review). Scope: does the H/V
adaptation lose the published parent construction? Labels: [published] [derived]
[reconstruction] [original-hypothesis] [code-verified] [unverified].

## 1. Identity
- **C-A `lecleach_iwata_ar`**: grid rows `type: iwata_ar` (grid.py:2267-2296) over the
  verified Fourcade march (profiles.py:412-562). AR law is [original-hypothesis]
  (YAML header cites "no published construction for this class exists").
  Config: examples/typologies/lecleach_iwata_ar.yaml; smooth copy
  home_landscape_2026-11-15/hl__lecleach_iwata_ar_landscape_smooth_v7.yaml.
- **C-B `lecleach_hv_pair`**: grid rows `type: lecleach` with `g_fc_v_hz` set
  (dispatch grid.py:2180-2186 -> `_rows_lecleach_hv_marches`, grid.py:1304-1430).
  Config: home_landscape_2026-11-15/hl__lecleach_hv_landscape_smooth_v7.yaml.
  Status: [reconstruction] of a [published] principle. The YAML description calling it
  "published ellipsoidal-wavefront construction" OVERSTATES the code (see 4, 9).

## 2. Lineage (what each ancestor supports)
| Source | Supports | Does NOT support |
|---|---|---|
| Fourcade 2015 eqs 10-27, 42-43 [published] (JMLC_LECLEACH_RESEARCH_2026-10-25.md) | the round meridian of ONE march, any fc/T/stop | any H/V split |
| sphericalhorns 2020-12-21 [published, secondary-author] | "round base sets wavefront areas"; per-plane PETF/hvdiff idea | an H/V equation (no formula fetched) |
| sphericalhorns 2019-08-05 eqs 10-12 [published, author] | planar section area kept (pi a b = pi r_m^2), b = r_m/f_s, a = r_m^2/b, n=2 ellipse | any 3-D wavefront identity; code does not use a = r_m^2/b |
| Auto-Tech 920x330 datasheet [published] | fc ratio ~2.8 as territory | any construction |
| Owner refs 4.png etc. [owner] | visual target | any equation |

## 3. Operator order (coordinate space: z/x axial, s arc fraction, phi from +x, psi section)
**C-B (pair):**
1. Core march at fc_core = sqrt(fc_h fc_v), deepest plane stop (grid.py:1350, 1367).
   Gives x_core(s), s = l/L_core.
2. Plane march H at fc_h, stop_h; plane march V at fc_v, stop_v (grid.py:1371-1376).
   Each resampled by its OWN arc fraction s = l/L_h, l/L_v (grid.py:1361-1376).
3. Rows: x = x_core(s) for ALL phi (grid.py:1398); axes a = r_h(s), b = r_v(s) taken
   verbatim (grid.py:1386-1392).
4. Interior phi: ellipse through the axes at the same s (grid.py:1400-1409). No march.
5. Rollback: stop_h, stop_v from rows_task_stop (gated [90,240]); interior stop values
   are REPORTS only (grid.py:1378-1385, 1403).
6. No rollback/lip torus (g_r_lip_mm pinned 0 in config).

**C-A (AR):** march -> resample by arc length (grid.py:2270) -> y_h = y sqrt(AR),
y_v = y/sqrt(AR), AR(s) = 1 + (AR_m-1) s^p (grid.py:1431-1466) -> ellipse per phi
(grid.py:2285-2288). x shared, one station chain.

## 4. Mathematics (as implemented)
- Fourcade: R0 = r0/sin(phi0); S0 = 2 pi R0^2 (1-cos phi0); m = 4 pi fc / c;
  S(l) = S0 [cosh(ml/2) + T sinh(ml/2)]^2; stepping eqs 23-27 (profiles.py:412-562).
  mm in/out, c = 343 m/s; phi0 is a HALF-angle. [published] eqs; [code-verified] stepping.
- Section (both C-A and C-B): r(phi) = a b / sqrt((b cos phi)^2 + (a sin phi)^2),
  phi from the horizontal (grid.py:1409, 2286). Ellipse with a = r at phi = 0. [derived]
- C-A: a = y sqrt(AR), b = y/sqrt(AR) => a b = y^2 exactly (grid_variants test
  `iwata_ar_area_product`). This is PLANAR area only. [derived, code-verified]
- C-B: a b at the mouth vs r_m^2 is NOT enforced; the code reports `area_note`
  (grid.py:1394). The lambda correction was tried and removed (dossier C2). [code-verified]
- Stop harmonic: stop(phi) = stop0 (1 + a2 cos 2phi) (grid.py:1851, 1403). Seed
  a2 = 0.05 gives stop_h ~ 225.8, stop_v ~ 204.3 deg (computed from the formula; [derived]).
- Endpoints: s = 0 is a circle r0 on every phi. No derivative matching across phi.
- Area: C-A planar (exact); C-B planar at mouth only (reported). S(l) is evaluated for
  the core only; neither has a wavefront area for H/V.

## 5. Parameter ownership (H/V pair, seed/box from its YAML)
| YAML key | Operator | Effect | Status | Bounds / provenance |
|---|---|---|---|---|
| g_fc_h_hz | plane march H | H flare scale, mouth r_h ~ 1/fc | searched | 300-750; seed 340; ratio cap 4.0 code gate [code-verified], territory 1.5-3.0 [published datasheet] |
| g_fc_v_hz | plane march V | V flare scale | searched | 450-1000; seed 520 [owner pick, reconstruction] |
| g_T | all marches | slimness | searched | 0.4-1.0 [unknown; dossier T1 notes] |
| g_stop_deg | stop0 | rollback depth | searched | 165-230 [reconstruction; code gate 90-240] |
| g_stop_a2 | stop harmonic | per-plane rollback diff | searched | -0.10..0.15 [original-hypothesis] |
| g_r_lip_mm | torus lip | lip | fixed 0 | [inferred approx] |
| g_fc_hz | none in pair path | ignored when fc pair set | conditional | seed still sets 340 (ambiguous) |
C-A: g_ar_m (AR_m, 1.0-2.8 smooth / 1.2-2.8 base) and g_ar_p (0.5-2.0) searched;
g_T pinned 0.5 (base) or 0.4-0.9 (smooth). AR bounds [original-hypothesis] (AR_m 2.0
from a "datasheet starting value"; published 2-inch 590/320 = 1.84 is one data point).

## 6. Zero-control identities
- C-B, fc_h = fc_v, a2 = 0, equal stops: equals the plain Fourcade rows (grid.py:1304
  degenerate note). Test `test_hv_rows_degenerate_to_the_axisymmetric_march_when_fc_h_equals_fc_v`
  (tests/test_design_generators_lecleach_hv.py:128), atol 1e-9. [exact by construction; test NOT RUN]
- C-B with fc_h != fc_v or a2 != 0: NO reduction to the round parent. Recovery of the
  parent requires both conditions.
- C-A, AR_m = 1: equals plain lecleach rows, atol 1e-9
  (tests/test_design_generators_grid_variants.py, `test_iwata_ar1_equals_the_plain_lecleach_rows`).
  [test NOT RUN]

## 7. Seeds and stated provenance
- examples/typologies/lecleach_iwata_ar.yaml: "our reconstruction of the published
  principle"; organic 1-inch brief; AR_m 2.0 "datasheet starting value"; wt 2.0 mm.
- hl__lecleach_iwata_ar_landscape_smooth_v7.yaml: seed from run eeef98 (best); fc 459.5,
  T 0.597, stop 110.8, AR_m 1.167 [searched result, [derived]].
- hl__lecleach_hv_landscape_smooth_v7.yaml: owner option 12 (fc_h 340 / fc_v 520, T 1.0,
  stop 215, a2 0.05) chosen 2026-11-16 from a visual grid [owner-decision, not evidence].

## 8. Objective fit
- Both HOME configs: `room_landscape_80x50_700_hf1440_v7_smooth.yaml` (di_slope_target 5.0)
  [code-verified]. Base `lecleach_iwata_ar.yaml`: `organic_rollback_1in.yaml` (other objective).
- Scores are not comparable across briefs (smooth YAML note: base 19.4 -> smooth 6.9).

## 9. Verification status
- C-A area: analytic + unit test (planar only). Evidence: grid_variants test.
- C-B: tests V1-V11 (tests/test_design_generators_lecleach_hv.py). NOT RUN here (no scipy).
- No GPU, BEM, mesh or measurement evidence exists for C-A or C-B.
- Cross-check snippet (numpy-only copy of eqs 10-27; approximate, NOT the repo code;
  scratchpad lc/march_check.py): r0 18 mm, phi0 2 deg, T 1.0, fc_h 340, fc_v 520,
  stop 215 both, dl 1 mm:
  - arc lengths L0 core 391, H 517, V 294 mm.
  - mouth x: core 187.5, H 266.9, V 128.8 mm.
  - max |x_core(s) - x_H(s)| = 91.9 mm; |x_core(s) - x_V(s)| = 69.1 mm (equal s).
  - mouth r_h r_v = 48484 mm^2 vs core r_m^2 = 48423 mm^2 (0.1%).
  - W fc_h vs H fc_v: 2*271.4*340 = 184.6e3 vs 2*178.7*520 = 185.8e3 (0.7%) [derived].

## 10. CROSS-CHECK FINDINGS (the answer)
**Yes, the H/V adaptation loses the parent construction in three ways:**

1. **H/V meridians are not the verified Fourcade marches.** The dossier says "the H and V
   plane meridians ARE their own verified marches" (LECLEACH_HV_ELLIPSOID s3.2). The code
   keeps only their RADII and replaces their AXIAL coordinate with x_core(s)
   (grid.py:1398). Measured mismatch at equal arc fraction: up to ~92 mm (H) and ~69 mm (V)
   at the seed-like snippet. The plane marches end at x = 267 (H) and 129 (V) mm; the rim
   is built at 188 mm for all phi. Rim planarity (test V1) is bought by discarding the
   parent's axial placement of each plane.
2. **"Shared wavefront station" is an arc-fraction station, not an equal-wavefront station.**
   The three marches have different arc lengths (391/517/294 mm), so s is not the same
   wavefront area. No S_h(l) = S_core(l) matching is performed. The 2019 article's
   area-based mapping is not used (only the planar a b relation is quoted).
3. **Planar pi a b conservation is not enforced and does not imply a 3-D identity.**
   a b = r_m^2 holds to ~0.1% at the mouth in the snippet and is reported, not enforced
   (dossier C2). Even exact planar conservation at every section would not prove an
   ellipsoidal wavefront or constant directivity: directivity is not computed anywhere in
   this construction, and no wavefront area is evaluated for H/V.

Preserved: the round core is the exact Fourcade march; H = V with no harmonic reduces exactly;
the mouth rim is convex (tests V2-V4).

**C-A (AR):** planar area exact (a b = y^2); parent wavefront area S(l) not preserved and
untested [unverified]; AR law [original-hypothesis]. **Label fix:** C-B YAML description and
the `docs/knowledge` card should say "reconstruction; planar section area; plane meridian radii only".

## 11. Proposed CPU-first checks (no GPU)
1. Install scipy in a venv; run the two lecleach_hv tests and the iwata_ar1 test.
2. Quantify the x_H / x_V shift on the real seed (replace snippet numbers).
3. 3-D wavefront area of the pair and AR surfaces vs S_core(l) (CPU integral); report residual.
4. Diagnostic: for each plane pick l_h with S_h(l_h) = S_core(l) and compare x_H vs x_core.

## 12. Open questions for senior review
- Keep the plane marches' own x (true 3-D surface) or the core x (current)? A geometry
  decision: it changes the rim.
- Label C-B as reconstruction and defer the 2019 wavefront transform?
- Does the owner's look (4.png) need the x-offset, or is the stop harmonic enough?
- g_fc_hz in the pair seed is ignored: remove or document?
