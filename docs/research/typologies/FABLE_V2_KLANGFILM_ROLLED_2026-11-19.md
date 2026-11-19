# Fable v2: Klangfilm-Lamé c200 and rolled-rect h12, rebuilt (cloud Fable senior, 2026-11-19)

Owner ask: make the best version of `hl__klangfilm_lame_curved_v1_c200` (run `20261117T091346Z-screen-517217`)
and `home_range_pilot_rolled_control_h12` (run `20261117T190640Z-screen-643de7`), with better vertical
behaviour, a "beak", the right scorer, keeping the overall form; narrower targets or a dispersion range allowed.
Evidence: `docs/evidence/runs/<run>/` (scores.csv, design.json, best mesh), committed by the local orchestrator.
Lanes: `examples/typologies/fable_v2_2026-11-19/`. Queue: top of `docs/queue/fable_scout40_2026-11-19.yaml`.

## 1. Diagnosis (measured, from the archived scores)

| | Klangfilm c200 best `88973b1e44e9` | Rolled h12 best `445dafb7e760` |
|---|---|---|
| Brief / J | v7 smooth / 7.446 | discarded v9 h12 corridor / 92.6 |
| Mouth W x H x depth (mm) | 585 x 255 x 193 (V axis 223) | 542 x 299 x 233 (V axis 281) |
| Unused envelope height (600 x 480 x 480 box) | **219 mm** | 175 mm |
| Largest cost | `diag` 3.44 = 46 % of J | `diag` 25.2 = 27 % of J; `dislope` 10.3 |
| V beamwidth 643 / 1065 / 1763 / 4832 / 8000 Hz | 180 / 127 / 94 / 51 / 42 deg | 149 / 129 / 86 / 51 / 41 deg |
| H beamwidth same freqs | 118 / 88 / 79 / 70 / 58 deg | 103 / 132 / 128 / 66 / 46 deg |

Readings:
- **Klangfilm V has no pattern control below ~2 kHz.** The Keele sizing estimate for a 223 mm V mouth at
  50 deg is 25,400 / (0.223 x 50) = 2.3 kHz, matching the measured knee [inferred: Keele is a sizing estimate
  here, not a constraint on a smooth horn; CLAUDE.md]. A 440 mm V mouth moves that estimate to ~1.15 kHz, which is
  where the v10 V corridor starts (1 kHz). The parent cannot get there: one area law with a held aspect ratio
  ties V to H (`_klangfilm_lame_v1._stations`: `a = q b`, cap area locked), so a taller mouth means a narrower one.
- **Rolled H blows out mid-band** (103 -> 136 deg at 1.0-1.8 kHz) with a 542 mm mouth whose Keele estimate at
  80 deg is ~590 Hz: the H wall law (throat/rect turn, H depth), not the mouth size, is the problem; it then
  beams at 8 kHz (46 deg, square corners `rect_exponent` 10.8).
- **The scorer was wrong for both.** `diag` scores the 45-degree beamwidths against a ROUND reference (mean of
  the H and V targets, 65 deg; `objective/scalar_v4._diag_term`). For an intentionally landscape-rectangular
  mouth this is not a design goal. v10 drops it.

## 2. Scorer: v10 corridor (H 60-90, V 40-60 from 1 kHz, preferred-edge ripple)

Owner allowed narrower (60 x 40) or a range. Choice: **the shipped v10 corridor brief**
(`examples/briefs/home_landscape_2026-11-18_v10/room_landscape_80x50_700_hf1440_v10.yaml`):
- a range, not a point: anything inside 60-90 H / 40-60 V is free, so a naturally narrowing horn (both of these
  narrow with frequency) is not punished for it; 60 x 40 is the corridor's lower edge, so "narrower" is covered;
- no `diag` term (above); DI roughness instead of a flat-DI target;
- it is the identity with a published floor (0.4677 J) and the lane-best table, so these lanes become directly
  comparable with the leaders (fold-warm v7 1.42, morph v7 1.43, ext-throat v7 1.57);
- the h12 brief was this corridor in the discarded v9 math, so re-homing the rolled lane on v10 is exact in intent.

## 3. Construction changes

### 3a. Record-edit freedoms on the exact best designs (both families)
`design/generators/record_body.py` now takes four knobs on an explicit host record (seed = host exactly):
- `g_vt_mm`, `g_vt_hold`: **late V opening** (`geometry.edits.vertical_timing`). Basis: the WP 4.3 B2 table, where
  this freedom moved the intended V plane **+32.3 deg** in 1.1-2.5 kHz with H moving < half: the largest authority
  measured in the project (`docs/evidence/wp43_b2_authority/README.md`) [measured on the biradial host;
  transfer to these hosts inferred].
- `g_beak_v_mm`, `g_beak_start`: **V-lip beak** (new `geometry.edits.vertical_beak`): the top and bottom lips move
  forward along the axis, `dz = D sin^2(phi) Q((u-start)/(1-start))`; the side walls stay put. Same law as
  the Klangfilm Phase B `beak_v_projection_mm` (`_klangfilm_lame_hv_core_v1._beak_offsets`), whose contract labels
  its acoustic role [original-hypothesis] (`docs/knowledge/contracts/klangfilm_lame_hv.md`). Expected effect: the
  V diffraction edge moves ahead of the H edge and the V wall path lengthens; whether it buys V control is what the
  lane measures. D = 0 is an exact no-op, so the search can always fall back to the host.
- **Host-relative validity**: rolled lips fold back by design, so a U2 check refuses an edit only if the host passed
  it; the lip may not approach the wall closer than 2 mm (or the host's own clearance).
- **Shell fidelity**: `rows.outer_offset: normal` builds the outer shell with `lame_shell.offset_quarter_surface`,
  the Klangfilm family's own shell. Verified: the Klangfilm host replays its family geometry **bit-for-bit (inner
  and outer)**; the generic shell would differ by up to 2.5 mm at the curl. The rolled host replays exactly on the
  default shell (same function as the family). Tests: `tests/test_design_record_body_beak.py`.

Why the record route rather than a new kernel: the Klangfilm kernels are frozen copies (regenerate, never
hand-edit); a v2 kernel is a new typology build (research + contract + digest). The record route gives the same
freedoms on the exact best shapes tonight, keeps the form by construction, and the result tells us which freedom
deserves a kernel.

### 3b. Rolled family: whole-family search on v10, relief live
`hl__rolled_rect_hybrid_vbeak_v10_v1`: mode `smooth` -> `hybrid` (bit-identical at zero relief, tested), 13 searched
knobs: mouth width 500-590 and height 280-440 (box 600 x 480), depth 200-300, H-depth ratio 0.55-1.0, decay,
corner exponent 4-12 (rounder corners against the 8 kHz H beaming), rollback terminal 225-280 deg, throat turn
12-40 and rect turn 50-80 (the H mid-band blowout), and the family's own relief: `axial_v/h` +-20 mm,
`inward_v/h` 0-40 mm. Note: the family's `axial_v_mm` is a mid-curl relief bump (peak at 0.8 of the wall, zero by
0.96), NOT a lip beak; the true lip beak is the record lane (3a). Seed = the h12 best exactly.

## 4. Lanes and predeclared reading

| Job | Lane | Knobs | Budget | Pass |
|---|---|---|---|---|
| 1 | `hl__klangfilm_lame_c200_record_control_smooth` (`run`, 1 solve, original smooth brief) | none | 1 | J within 0.05 of 7.446: the record route replays c200 acoustically. Fail -> do not trust lane 2 |
| 2 | `hl__klangfilm_lame_c200_vbeak_v10_v1` | vt 200-450, hold 0-0.5, beak 0-45, start 0.3-0.8 | 60 | best beats its own seed (eval 0 = host on v10) by > 0.4677 J |
| 3 | `hl__rolled_rect_record_vbeak_v10_v1` | vt 260-440, hold, beak, start | 40 | same rule vs its seed |
| 4 | `hl__rolled_rect_hybrid_vbeak_v10_v1` | 13 family knobs | 80 | same rule; compare with lane 3 (beak on the exact shape vs whole-family reshaping) |

Also read the V beamwidth table of each winner: success in owner terms = V inside 40-60 deg from ~1.2 kHz up
(today: from ~2.3 kHz Klangfilm, ~1.8 kHz rolled) without H leaving 60-90.

Box sampling (CPU, 48 draws each): Klangfilm lane 48/48 build (mouth H up to 441), rolled record 48/48, rolled
hybrid 45/48 (3 generator refusals; `resample_strict` handles them). Mesh/dof check needs the owner box.

## 5. Not done / next if these win
- A Klangfilm-Lamé v2 kernel with an independent V law and a lip beak native to the curl (spine parameterisation),
  only if lane 2 shows the V freedoms pay (> floor). Needs `hornlab-typology-research` first.
- Phase B core (`b3_soft`, J 2.82 on the smooth brief) is already the best Klangfilm-family result; it runs in
  SCOUT40 job `s40__klangfilm_b3_soft`. If the record lanes stall, the core + beak is the next construction to
  re-home on v10.

## 6. Geometry pass (owner review of the renders, 2026-11-19) - SUPERSEDES the lane list in section 4

Owner: "why is the throat wobbly, why is the rollback so deep, there should not be S-curves". New CPU check
`tools/analysis/meridian_sanity.py` (S-curve = the wall turns back > 2 deg before the lip zone; throat pinch =
wall angle drops > 2 deg below its throat value; deep rollback = > 230 deg of turn or the lip returning into the
first 35 % of the depth; a <= 10 deg reversal in the last 10 % is lip treatment). Findings [measured geometry]:

| Shape | Finding | Cause | Action |
|---|---|---|---|
| Klangfilm c200 / c200w (v1 parent) | V throat pinch -6 deg, S-curve, 200-218 deg curl back to 9 % of depth | area lock ties V to H; optimizer pushed end_frac to its bound | record lanes + c200w DROPPED; replaced by the Phase B core lane |
| Klangfilm Phase A stage_a | S + pinch at the throat, 216-240 deg curl | forward-branch deformation | DROPPED |
| Phase B beak (any start <= 0.92) | wall bends back: S or a 16-deg lip kink | short C2 gate on a monotone core | beak PINNED at 0 in the new lane |
| Rolled h12 | H S-curve (-7 deg at mid-wall), 252-263 deg curl | depth_h_ratio 0.68; terminal 270 | depth_h_ratio 0.85-1.15, terminal 190-220, relief OFF (relief bumps are wiggles by design) |
| Biradial vt_v1 host | throat-blend overshoot: H wall 13.5 -> 45.7 -> 36.3 deg in the first 25 mm (the "wobbly throat") | OS-to-bi-radial blend overshoots the cone angle | vt_v1 PULLED from tonight; generator fix is a separate task |
| rf_section_axial | 242 deg H rollback | family default | DROPPED (it was the tail job) |
| b3_soft, Le Cleac'h H/V, Iwata-AR, Crowe V2A | clean (b3: 2-4 deg lip beak only; JMLC 206 deg roll with lip at 78 % depth) | - | kept |
| Native OSSE lanes (fold-warm, morph v8, ext-throat, petal, Tritonia, Crowe-X, R-OSSE) | not checkable offline (need hornlab_mesher) | - | owner box runs the check before launch |

Lanes now queued first: `hl__klangfilm_hv_core_c200form_v10_v1` (Phase B monotone H/V core: mouth ~540 x 376,
340 mm deep, 8 searched knobs; 46/64 box draws build, 0 geometry flags; the rest are box overflows the search
resamples) and `hl__rolled_rect_clean_v10_v1` (9 knobs; 96/96 box draws pass). Renders:
`docs/evidence/fable_v2_renders_2026-11-19/*_old_vs_clean.png`.
