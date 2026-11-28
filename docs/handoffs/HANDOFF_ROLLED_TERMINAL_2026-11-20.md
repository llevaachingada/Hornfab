# HANDOFF — rolled H terminal / rollback geometry, width 500 + yellow C

**Date:** 2026-11-20
**Audience:** senior geometry/acoustics agent (review first, then one bounded implementation + single-solve pass)
**Status:** **NOT ACCEPTED.** The user says “a bunch of these do not look right and don’t really get to what I was asking.” Do not treat the current candidates as accepted because the H-cut numbers match the sketch. The user has rejected the look.

---

## 1. The user’s request (verbatim)

> “Yeah if we can get the width to be more like 500mm See the screenshot attached I have drawn sketched over it in yellow where I feel like the rollback should start”

Earlier, in the same thread:

> “How can we get this having better dispersion characteristics and not be so narrow in the high frequency range? Can we also widen the parameter bound so that g_decay is not pinned at high? And Score better overall and perform better Acoustically”

> “Is V10 the correct scorer to use in the situation”

> “Can you queue up some of the variants here that you think would perform best for maybe 60 solves each”

> “Can you give me a handoff here for a senior agent to review these and try to improve the geometry a bunch of these do not look right and don't really get to what I was asking you to change about it”

**The current task:** width ≈500 mm; trim the **horizontal flat face before the rollback**; **start the rollback at the yellow mark**; keep a **visible rollback** but less horizontal face; keep the **throat, vertical cut, height, depth** the same; reduce the overall size.

The sketch is over the H cut of the 576 mm best. The yellow band is at **x≈±220, z≈160**, curling down/inward to **x≈±190, z≈120–130**. The current wall runs out to **x≈±288 (576 best) / ±250 (500 width)**, then curls with a small hook.

---

## 2. Baseline and the current best

- Original run: `runs/20261119T172313Z-screen-081506`
- Best design: `96790c88352e`, **J 9.3054** (objective v10), 576×344×242 mm, screen 4959 dofs.
- H 1.07/2.27/4.26/8k: **112.9 / 93.6 / 69.3 / 50.4°**
- V 1.07/2.27/4.26/8k: **114.8 / 69.8 / 56.9 / 42.8°**
- Terms: dislope 7.322 of 9.305 (79 %); cov 0.631; load 0.523; flat_cv 0.410; flat 0.449; rip 0.033.
- Original config: `examples/typologies/fable_v2_2026-11-19/hl__rolled_rect_hybrid_vbeak_v10_v1.yaml`
- Render: `docs/renders/2026-11-19-last-day-horns/last_day_setA_05.png` (the no-C shape).

The score is dominated by a rising DI (8.1 dB/dec score-band), i.e. the H/V narrowing. The user’s current complaint is the **geometry look**, not the J.

### The accepted reference for HF dispersion (different construction)

- Ext-throat `925868ab64d9`, OSSE, same v10 brief, screen J 1.7919; verify `runs/20261120T161054Z-verify-bf45ad` **J 1.9693**, H 70.8 / V 61.2 at 8 kHz, score-band DI slope 0.14, `di_source=balloon`.
- This is still the only design that holds the HF corridor. The rolled family does not; do not promise 60–90° at 8 kHz from the rolled body without a genuinely new HF mechanism.

---

## 3. What was implemented (and what is contested)

Two new versioned, additive rolled-family mechanisms are in the tree:

1. **Flare-timing CD wall-angle shear** — `_rolled_rect_cd_v1.py`, adapter `rolled_cd_family.py`, kind `rolled_family_rect_cd_v1`.
   - Additive/zero-control; 15 tests; front-load variant J 8.326, V 8k 47.8°, but H 8k 50.8°.
   - It cannot change the lip angle; it does not fix H at 8 kHz.

2. **H terminal roll-onset / C-return law** — `_rolled_rect_terminal_v1.py`, adapter `rolled_terminal_family.py`, kind `rolled_family_rect_term_v1`.
   - H-meridian Hermite through `P0` (parent forward, parent tangent), `P1` (half-width, z_f − max_drop), `P2` (roll_frac·half-width, z_f − roll_drop), `P3` (lip_frac·half-width, z_f − lip_drop); `tm_lip_angle_deg` sets the lip tangent.
   - H-only: C2 azimuthal blend exactly zero at/beyond 40° from H; V/throat theoretically bit-identical.
   - 12 focused tests; neutral bit-for-bit.
   - Configs: `examples/typologies/rolled_terminal_2026-11-20/{neutral,candidate,soft_c,soft_bend}.yaml`.

Additive dispatch edits (kept): `hornlab_search/design/generators/grid.py`, `hornlab_search/design/generated.py`, `hornlab_search/mesh/build.py` — each only adds `rolled_cd_family` / `rolled_terminal_family` to the family tuples. `rolled_family.py`, `_rolled_rect_v1.py`, `_rolled_rect_cd_v1.py` are untouched.

Other lane’s uncommitted work (do **not** touch): `hornlab_search/config.py`, `objective/replay.py`, `objective/versions.py`, `search/evaluate.py`, `metrics/cd.py`, `examples/briefs/cd_v11_*`, `examples/typologies/cd_v11_*`.

---

## 4. Measured results (all v10, screen, balloon DI, unless stated)

| design | run id | J | rip | H 1.07/2.27/4.26/8k | V 1.07/2.27/4.26/8k | bbox / dofs |
|---|---|---|---|---|---|---|
| original 576 best | `20261119T172313Z-screen-081506` | 9.3054 | 0.033 | 112.9 / 93.6 / 69.3 / 50.4 | 114.8 / 69.8 / 56.9 / 42.8 | 576×344×242 / 4959 |
| width 520 only | `20261120T163437Z-screen-888636` | 9.0555 | ~0.030 | 111.4 / 91.1 / 67.8 / 49.5 | 112.5 / 70.3 / 56.9 / 42.9 | 520×344×242 / 4143 |
| **width 500 neutral** | `20261120T165651Z-screen-6a36c3` | **9.0033** | 0.0285 | 111.0 / 90.5 / 67.2 / 49.2 | 111.8 / 70.6 / 56.9 / 42.9 | 500×344×242 / 4036 |
| sharp C (candidate) | `20261120T165805Z-screen-01eebe` | 9.6015 | 0.1593 | 110.6 / 86.7 / 66.5 / 48.8 | 115.5 / 66.3 / 52.7 / 41.6 | 500×344×242 / 5760 |
| soft lip C (lip drop 70→55) | `20261120T182453Z-screen-63c7f7` | 9.5780 | 0.1576 | 112.6 / 86.7 / 66.5 / 49.0 | 115.4 / 66.6 / 52.7 / 41.8 | 500×344×242 / 5273 |
| soft bend (24/40/70) | — | — | — | — | — | **mesh fail**, 0.932 mm clearance |
| front-load CD | `20261120T162808Z-screen-accb39` | 8.3264 | 0.0938 | 105.5 / 100.7 / 76.6 / 50.8 | 113.7 / 64.1 / 54.1 / 47.8 | 576×344×242 / 4769 |

- Width 500 is the **size/score** answer: −13.2 % width, J −0.30 (inside the 0.4677 floor), H/V essentially unchanged.
- The C adds ~0.6 J and a ~0.13 ripple term; the soft lip did **not** reduce it (0.1576 vs 0.1593). The C did not move H 8 kHz (48.8–49.0). The C is **look-only as-is**.
- The front-load CD variant is the **score** seed (8.326), not the HF answer (H 8k 50.8).
- The soft-bend mesh failure: 0.932 mm CAD clearance at the mouth (z 193.9–201.1), 14 remaining prohibited facet pairs.

---

## 5. The critical H-cut mismatch (lead issue)

The terminal-law readout claims “geometry meets the sketch,” but the **max-width point is 15 mm above the parent control**:

| landmark | 500 neutral (control) | sharp C | user’s sketch |
|---|---|---|---|
| max width / z | 249.96 / **159.0** | 249.96 / **174.8** | width 500; outer edge z≈160 |
| roll onset x / z | no 220 return | 219.96 / 159.8 | ≈220 / ≈160 |
| lip x / z | 236.9 / 144.0 | 189.97 / 124.8 | ≈190 / 120–130 |

**The C’s `P1` (max width 250) is at z=174.8, 15 mm higher than the control’s max-width point z=159.** That is the forward/up bulge the user is seeing. The yellow mark at 220/160 is the `P2` roll onset; the wall still has a 250/174.8 flat face before it. The law’s `g_tm_max_drop_mm=20` anchors `P1` to `z_f−20`, not to the parent’s max-width z.

**First thing to try:** set the C’s max-width point to the parent/control max-width z (≈159), i.e. `g_tm_max_drop_mm` ≈ **35.8** (not 20), and `g_tm_roll_drop_mm` ≈ **35** (P2 z≈159.8) or slightly less; keep the x landmarks 250 / 220 / 190 and the lip z≈125. Re-render the H cut and the 3D. If that removes the bulge and the C still meshes, it is the right direction. Verify the `z_f`/`P0` semantics first: the law’s `P0` is the parent forward point; the control’s max-width z is 159, not `z_f` 194.8. The current C is anchoring the flat face above the parent, not trimming it.

The sketch’s yellow x may be absolute (220/190) or proportional on the 576 (0.76/0.66 of 288). The current law uses absolute 220/190 = 0.88/0.76 of the 500 half-width. Confirm visually before changing; the absolute landmarks match the sketch’s x, but the relative shape is tighter.

---

## 6. Other potential issues to review

1. **Forward bulge / max-z anchor** (above). The C’s `P1` at 174.8 is above the parent max 159. The user’s “doesn’t look right” is most likely this. The user wants the flat face at the parent’s outer edge, not a raised forward lip.
2. **H/V blend.** The C is H-only with a 40° C2 azimuthal blend. The 3D mouth may be lumpy/creased where the C fades into the V walls; the V cut is bit-identical, but the transition is not necessarily natural. Render top/isometric/front; consider a wider blend or a C2 H/V transition. The user wants the vertical components the same, so do not change the V cut; change only how the H C fades.
3. **Outer shell / wall thickness.** The C’s outer shell is a normal offset. The 6.0 mesh fails at 0.95 mm clearance; 5.9 passes. Check the wall thickness at the C, the outer surface smoothness, the lip return, the printability, the watertightness. A proper outer offset or a lip roundover may be needed. Do not “fix” the 6.0 failure by lowering the mesh density without saying so; the 5.9 vs 6.0 comparison is a confound in the J/ripple numbers.
4. **Hermite P0..P3 formulation.** A single cubic through four points can overshoot/loop; the z/x clamps can flatten the C; the lip tangent (`tm_lip_angle_deg`) affects the whole cubic, not just the lip. The current soft attempts (lip drop 55, bend 24/40) either did not reduce the ripple or failed the mesh. A C2 spline/arc with an extra control point, a separate lip roundover, or a piecewise arc may be the right law; do not keep tweaking the same four knobs if the render still looks wrong.
5. **Width-only 500 is not the requested design.** It scales the whole H wall; the H cut still ends in the parent’s small hook at 236.9/144, not the yellow C. It is the **size reference** (J 9.0033, 500×344×242), not the trimmed-face/rollback shape.
6. **C acoustic cost.** The C adds ~0.6 J and a ~0.13 ripple term; the soft lip did not help. The C does not widen H 8k. The C is a look/size change; do not claim the HF goal is fixed. The ext-throat 70.8 is still the HF reference.
7. **Mesh-density confound.** Sharp/soft C at epw 5.9; control at 6.0. The C’s tighter surface exceeds 6000 dofs at 6.0. The J/ripple comparison is not perfectly controlled. If a corrected C can mesh at 6.0, use it; otherwise state the caveat.
8. **V metrics differ slightly despite H-only.** The V cut is theoretically identical; the V beamwidths at 1.07k differ (111.8 control vs 115.4 C) due to the H C diffraction/mesh. Check the V cut bit-identity; do not change the V geometry.
9. **The 576 vs 500 landmark scale.** The sketch is over the 576 H cut; the yellow x≈220/190. The 500 law uses absolute 220/190 (0.88/0.76 of 250); the 576 relative is 0.76/0.66 of 288. Confirm whether the user wants the C at absolute x or proportional. The current absolute match may be right, but the C’s relative size is different.
10. **The user’s “a bunch of these” includes the width-only 500 and the CD variant.** The width-only 500 is a simple shrink (boxy?); the CD variant changes the V and does not address the H roll. Review all candidates visually, not just the sharp C.
11. **The GPU self-lock bug.** A `hornlab-search run` can self-lock/print GPU busy for its own pid after a previous hung wrapper; do not loop. Stop the specific wrapper pid, `gpu-clean`, and retry once. Never delete `runs/.gpu.lock` by hand; never force-clean another lane’s live verify. The lane is currently clean.

---

## 7. What the senior needs to do

**Review first (no GPU):**
1. Read this handoff, the original run/config, `runs/m13_rolled_cd/TERMINAL_READOUT.md`, `runs/m13_rolled_cd/READOUT.md`, the new kernels/adapters, the tests, and the user’s sketch coordinates.
2. Render the actual geometry: H cut, V cut, top, isometric, front, and a close-up of the H roll for the 576 best, 500 neutral, sharp C, soft C, and front-load CD. Use the `hornlab-render` skill / existing meshes. The numeric H-cut match is not enough; the user rejected the look.
3. Diagnose the visible defects specifically: forward bulge/max-z (lead), H/V blend/lump, lip shape/depth, outer shell/wall, mouth flatness, symmetry.
4. Confirm the sketch interpretation: absolute 220/190 vs relative; max width 250 vs 220; the C’s top/roll z; whether the overall width 500 includes the C’s max or the lip.

**Then one bounded implementation (CPU first):**
5. Correct the terminal law (new versioned kernel — do not edit the frozen parent/CD kernels in place; the digest binds them):
   - Anchor the C’s max-width point to the parent’s max-width z (≈159) and the yellow x/z; no material above the parent’s max-width/outer edge.
   - Keep the roll onset at x≈220/z≈160 and the lip at x≈190/z≈125; keep a visible C/rollback; less horizontal face.
   - Keep width 500, height 344, depth 228/242, throat 15.75°, V cut unchanged.
   - Fix the H/V blend and outer shell/wall; target epw 6.0 if it can mesh, otherwise 5.9 with a written caveat.
   - If the Hermite single cubic cannot produce a natural C, use a C2 spline/arc with an extra control point or a separate lip/roll roundover; a new versioned law is acceptable.
6. Run the focused tests (zero-control, V/throat identity, envelope, no self-intersection, digest) + `tools/shape_check.py`; render again. **Do not** run a search.
7. Only after the render looks like the user’s sketch, run **one** single screen solve (`run --config ... --mode screen`) with GPU hygiene. Report H/V at 643/1065/2268/4260/8000, J, dof, mesh epw, and the H-cut landmarks vs the sketch.
8. Report back with images and the acceptance checklist. The user must approve the look before any 60-valid search.

**Do not:**
- Do not run a full search / 60-valid queue on the current C. The user’s gate was “after the softened C”; the soft C failed the ripple gate.
- Do not edit `_rolled_rect_v1.py`, `rolled_family.py`, the frozen contracts, or the other lane’s uncommitted files.
- Do not force the GPU lane; one solve at a time.
- Do not claim “meets the sketch” from the H-cut numbers alone.

---

## 8. Acceptance checklist for the corrected geometry

- [ ] Width 500 ±5 mm; height 344; depth 228 (overall 242); throat/V/thickness unchanged (bit-identical V cut).
- [ ] H cut: max width 250 at the parent’s max-width z (≈159–160); roll onset x≈220/z≈160; lip x≈190/z≈120–130; visible C/rollback; no flat face above the parent outer edge; no forward bulge.
- [ ] 3D: smooth H/V transition; no crease/lump; natural mouth/lip; outer shell smooth; wall ≥3 mm; watertight; no self-approach.
- [ ] Mesh at epw 6.0 if possible; if 5.9, the dof/ripple caveat is stated.
- [ ] One single screen solve; H/V/J reported; the C is a look/size change, not the HF fix.
- [ ] Renders: H cut, V cut, top, isometric, front, close-up; compared to the user’s sketch.
- [ ] The user’s visual approval before any search/queue.

---

## 9. Files, commands, run ids

**Original:**
- `runs/20261119T172313Z-screen-081506` (best `96790c88352e`, J 9.3054)
- `examples/typologies/fable_v2_2026-11-19/hl__rolled_rect_hybrid_vbeak_v10_v1.yaml`
- `docs/renders/2026-11-19-last-day-horns/last_day_setA_05.png`

**Size variants:**
- `examples/typologies/rolled_size_2026-11-20/hl__rolled_size_w500.yaml`, `_w520.yaml`
- `examples/typologies/rolled_terminal_2026-11-20/neutral.yaml` (500 neutral, run `20261120T165651Z-screen-6a36c3`, J 9.0033)
- `.../candidate.yaml` (sharp C, run `20261120T165805Z-screen-01eebe`, J 9.6015)
- `.../soft_c.yaml` (lip 55, run `20261120T182453Z-screen-63c7f7`, J 9.5780)
- `.../soft_bend.yaml` (mesh fail, 0.932 mm)

**CD:**
- `examples/typologies/rolled_cd_2026-11-20/{control,candidate,variant}.yaml`
- front-load run `20261120T162808Z-screen-accb39`, J 8.3264
- `runs/m13_rolled_cd/READOUT.md`

**New code:**
- `hornlab_search/design/generators/_rolled_rect_cd_v1.py`
- `hornlab_search/design/generators/rolled_cd_family.py`
- `hornlab_search/design/generators/_rolled_rect_terminal_v1.py`
- `hornlab_search/design/generators/rolled_terminal_family.py`
- `tests/test_rolled_cd_geometry.py` (15)
- `tests/test_rolled_terminal_geometry.py` (12)
- `tests/test_rolled_family_geometry.py` (parent)
- Additive dispatch: `grid.py`, `generated.py`, `mesh/build.py`

**Run/verify:**
- `runs/m13_rolled_cd/TERMINAL_READOUT.md`
- ext-throat verify `runs/20261120T161054Z-verify-bf45ad` (J 1.9693, H 70.8/V 61.2 at 8k)
- rolled best verify `runs/20261120T161330Z-verify-124fee` (J 9.238, H 50.4/V 42.8 at 8k)

**Commands:**
```
pytest tests/test_rolled_terminal_geometry.py tests/test_rolled_cd_geometry.py tests/test_rolled_family_geometry.py -q -p no:cacheprovider
tools/shape_check.py examples/typologies/rolled_terminal_2026-11-20/<config>.yaml
gpu-clean; nvidia-smi; HORNLAB_GPU_LOCK=refuse; hornlab-search run --config <config> --mode screen
```
59 focused tests pass as of this handoff; no agents are running; the GPU lane is clean.

---

## 10. Open questions for the user

1. **Absolute or proportional C?** The yellow x≈220/190 on the 576 best is 0.76/0.66 of the half-width; the 500 law uses absolute 220/190 = 0.88/0.76 of 250. Which should the corrected C use?
2. **Max width 250 or 220?** The user says width “more like 500” (max 250) but the yellow roll starts at 220. Should the wall still reach 250 at z≈159 and then roll at 220/160, or should the overall max be 220 (width ≈440)?
3. **HF priority.** The C does not fix H 8k; the ext-throat is 70.8. Is the C a look/size change only, or must the HF corridor be met too (which needs a different construction)?
4. **Mesh/mesh fidelity.** Is 5.9 acceptable for the C, or must 6.0 be achieved with a corrected outer shell?
5. **Ripple.** Is the C’s ~0.13 ripple acceptable for a look-only variant, or must the C be acoustically clean (likely a new roundover law)?

---

## 11. Bottom line

- **Width 500 neutral** is the measured size win: 500×344×242, J 9.0033, H 8k 49.2, −13.2 % width, V/throat/depth unchanged. Use it as the size reference.
- **The C is not accepted.** It matches the yellow x/z landmarks but raises the max-width point 15 mm above the parent and adds ripple; the soft lip/bend attempts did not fix it. The user says the shape does not look right.
- **The senior’s job** is to re-anchor the C to the parent’s outer max z, fix the H/V blend/outer shell, render and compare, and only then run one single solve. Do not queue a search.
- **The HF answer** remains the ext-throat `925868ab64d9` (H 70.8/V 61.2 at 8k); the rolled family is a form/size experiment until a genuinely new HF mechanism exists.
