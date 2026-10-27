# Learnings — 2026-10-26 senior pass (campaign prep, sandbox, Ath creases)

Durable findings for future agents. Each item says what was learned, the evidence, and where it lives.
`docs/plan/**` is frozen, so this file is the research-basis addendum; cite it from new work.

## Geometry / typologies
1. **Ath's creased walls (CORE, TwinRay, Opus) come from a per-direction law, not from Morph.** CORE's
   published script (at-horns.eu/core.html) writes `a = 5 + 35*sf(4,12,15,16,1,0.618,p) - 15*cos(p)^10`,
   `n = 6 + 1.5cos²p`, `s = 0.6 + 0.23cos²p`, plus a rectangle Morph (rate 3, fixed 0, corner 16.5).
   Result: a = 25.0 / 33.8 / 23.4° at p = 0/45/90; the wider diagonals fold the walls. Morph alone only
   squares the mouth. Implemented as native-OSSE `az_*` knobs (`design/families.py::azlaw_expressions`,
   dossier `docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md` §5b).
2. **The OS-SE guiding curve (`gcurve_*`) is the other crease route.** It is OSSE-only and the mesher
   refuses it unless the cross-section is circular (`exponent` 2, `aspect_ratio` 1). Research: start
   with type 1 (superellipse, se_n 2–5, dist 0.3–0.7) and add the superformula later.
3. **What looks/sounds plausible:** one smooth bump per quadrant, diagonal ≤ ~10–15° wider than H/V,
   slope ≲ 1°/° of azimuth. Multi-lobe laws (`az_sf_m` 8/12) are fine at a ~10° swing with n1 ≈ 2;
   n1 ≈ 1 with large amplitudes gives sharp, wavy walls (likely diffraction). Curated sandbox recipes
   are in the 2026-10-26 conversation summary in CONTINUITY.
4. **FREEFORM horns refuse a rectangle Morph on an elliptical base** (convexity guard). Use target 3
   (superellipse) on FREEFORM bases. R-OSSE/ICW Morph is mesh-proven.
5. **The rows self-approach guard had a false-refusal bug** (chord vs equal arc on any curved lip).
   Fixed: non-adjacent = arc ≥ π/2 × (2t+2). Real folds still refuse (ff703a1).
6. Salmon/Le Cléac'h have **no mouth-size knob**; the mouth follows from fc (W·fc ≈ 1.9e5 mm·Hz for
   JMLC, ≈ 3.2e5 for Salmon at stop 150°), stop angle and T.

## Search / scoring
7. **Boxes were the binding constraint in past passes.** CMA works in a unit box (sigma0 0.15 of the box
   width), so a ±5 % box only polishes the seed. Envelope refusals are pre-mesh (~1 s) and cost no GPU.
   Rule now: physical-range boxes (`tools/widen_campaign_boxes.py`), `infeasible_penalty: graded`, never
   narrow a box to lower the invalid rate; fix the seed instead. Next: auto wall-expansion
   (`tools/expand_walls.py`, owed).
8. **Score each horn type for what it is for:** constant-directivity briefs use v3 with a K-law f0
   (wide briefs add f0_v); rows families on coverage briefs use dislope 0; Le Cléac'h native is scored
   mainly on loading (load 0.5, z_min 0.7, cov 0.3); ATH natives use v3 with f0 from their published
   mouth. v2 without f0 lets unfixable sub-f0 coverage error dominate J.
9. **Blind spots of J:** H/V planes only (diagonal/crease benefits invisible); screens start at 500 Hz
   (sub-500 loading only at verify); load term is band-averaged (diluted); coverage graded to 8 kHz past
   the 1.4-inch driver's 5.6 kHz cross-mode.
10. **Driver realism:** the ideal source is fine below the first *axisymmetric* duct mode (36 mm exit:
    ~11.6 kHz), not just f11 (5.6 kHz), for symmetric annular phase plugs (CIARE PWT+FEA agreed 1–15 kHz).
    Measured: piston vs breathing cap changes beamwidth < 0.5°. Sensitivity check available via
    `solve.source_profile_alpha` (fused only).
11. **Drivers for briefs:** 1.4-inch = r0 18.0 mm (36 mm exit, B&C DE800/900, BMS 4594ND), exit
    half-angle 2–3°; 1-inch drivers are not credible at 800 Hz; 300–400 Hz loading needs the
    BMS 4592/4594 class.

## Compute
12. Fused CUDA: 12,183 dofs = 4.9 GB / 13.7 s per freq (comfortable); 15,984 completes but at
    458 s/freq (unusable); 20,237 kills the worker. Run memory ladders LAST in a night.

## Tooling / GUI
13. The GUI now shows anything on disk (configs/briefs at any depth, all runs, auto per-brief
    leaderboards, night runner on the Status page). The sandbox has a free / search-limits switch,
    Morph, guiding-curve and per-direction-law cards. Mesher config refusals show as reasons.
