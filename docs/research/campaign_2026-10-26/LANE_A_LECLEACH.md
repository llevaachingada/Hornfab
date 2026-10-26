# LANE A — Le Cleac'h (JMLC) typology audit

2026-10-26 · repo `C:\Users\hunte\Hrns\hornlab-search` @ `unified-typologies` (uncommitted work from other lanes read only, never edited) · CPU meshing / dry-run only; **no GPU solve, no Julia, no repo writes**.
Scratch: `...\scratchpad\audit_lecleach\` (probe.py, run_cells.py, march_boundary.py, cfgs/, out/, briefs/).
Interpreter: `C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe`.

**Legend.** `[measured]` = this lane's CPU march or gmsh mesh probe, or a dimension read directly off a fetched datasheet drawing. `[published]` = a fetched text/manufacturer claim. `[estimated]` = arithmetic/scaling from measured numbers. No number below is invented.

---

## 0. Bottom line

1. **The f0 derivation is the main over-constraint, not the mesh budget.** It sets one `g_fc_hz` from the geometric mean of the K-law mouth, then clamps to the config's existing `[600,1200]` (rollback/toroidal/asym) or `[800,1200]` (iwata) bounds. Every campaign brief derives an fc **below** those floors — B1 462, B2 290, B3a 266, B3b 326 — so every current seed is silently a **much smaller horn** than the brief asks for (313 mm round vs 332×498, 529×794 or 706×706). [measured, derivation headers + seeds]
2. **The four campaign briefs are all taller than wide (H>W), while every commercial JMLC/IWATA is wider than tall (AR 1.84–2.79).** For a 90×60 brief the K-law needs W 332 × H 498; the AR needed is **0.667**, but `lecleach_iwata_ar` bounds are `[1.2,2.8]`. The current AR law cannot represent any of B1/B2/B3b. This is the second hard over-constraint. [measured/published]
3. **A JMLC fc is a loading corner, not a pattern corner.** The exact construction gives mouth diameter ≈ **0.55 λ at fc** (`W·fc ≈ 1.88e5 mm·Hz` at stop ≥170). Pattern control therefore starts at ~**1.8× fc**; the commercial line's "minimal frequency" is consistently **1.5× the model number** (JMLC-350→520, 400→600, 600→900, 200T→300; IWATA-300→450). A brief that uses f0 as a *90° coverage* frequency is asking a JMLC for ~1.7× its loading corner. [measured/published]
4. **`dislope` must be 0 for this family.** A non-CD profile cannot hold DI slope 0; the earlier 90° run's dislope term dominated J. Also reduce `cov` weight (0.3–0.5) or mask it above the frequency the mouth can actually control. Loading (`load` + `z_min`) is the honest objective. [measured, prior run + geometry]
5. **Half-model verdict:** a y >= 0 half (xz plane, quadrants `'12'`) is **geometrically exact** for `lecleach_asym_odd` (up/down mirror error **1.1e-13 mm** [measured]) and the solver/metrics layer already supports `'12'`/`xz`, **but the repo cannot generate it today**: the rows machinery's only half is phi = -90..+90 / yz / `'14'`, and `lecleach_asym` refuses `span: half`. Full ring is the only legal route until a new span is added. The half would halve the full-ring cost (B3b 5.5-13.7k -> 2.8-6.9k, native 3,338 -> 1,669); it would **not** rescue B3a-asym at 8 kHz (the 694 mm solution is ~28k full, ~14k half [estimated], still over the 12k ceiling).
6. **Best-fit answers per brief:** B1 -> `iwata_ar` (T 0.8, fc 462, AR 0.667): 331x495x223, **2,612 dofs** [measured]. B2 -> only with a **1.4-inch driver**: fc 278, T 1.0, AR 0.667: 525x786x421, **6,378 dofs** [measured]; as 1-inch it cannot be done. B3a -> 1.4-inch rollback fc 268/T 1.0/stop 170: **694x694x472, 7,241 dofs** [measured]; the K-law 706 mm is 1.7 % short, so 90 deg holds to **~407 Hz** (a 2-inch throat gives 699 mm/7,446 dofs for no real gain). B3b -> `iwata_ar` fc 326/T 1.0/AR 0.667: 467x699x355, **5,064 dofs** (1.3 % over the 5,000 screen cap) [measured].

---

## 1. What the f0 derivation actually overrides

`config.py::_brief_preflight_and_derive` → `_derive_generator_geometry` (only when `target.f0_hz` exists):

1. `req_w = 25,400,000/(f0·cov_h)`, `req_h = 25,400,000/(f0·cov_v)` mm (Keele).
2. `target_w = min(req_w, env_w − 2·wall)`, same for h (the freestanding shell is subtracted).
3. Grid rows: **one** `g_fc_hz = 188,000 / sqrt(target_w·target_h)`, then clamped to the config's existing bounds. [measured, code]
4. `iwata_ar` additionally sets `g_ar_m = target_w/target_h`, clamped to its bounds. Nothing else is derived: T, stop, eps, eps_start, r_lip, ar_p, and per-axis fc are untouched.
5. `lecleach_f90` (`generator.name: typology`) has **no lecleach derivation rule** — its fc stays at the seed 800 regardless of the brief. [measured, code]

Measured consequences:

| brief | req W×H (mm) | envelope (W×H×D) | derived fc | applied | resulting seed |
|---|---|---|---|---|---|
| B1 850/90×60/1.4" | 332.0×498.0 | 360×520×400 | 462.3 | **600** (clamped) | 312.5×312.5×149.8, 1,531 dofs |
| B2 800/60×40/1" | 529.2×793.8 | 560×830×450 | 290.1 | **600** | 310.8×310.8×180, 1,551 dofs |
| B3a 400/90×90/1.4" | 705.6×705.6 | 740×740×650 | 266.4 | **600** | 312.5×312.5×149.8, 1,531 dofs |
| B3b 600/90×60/1.4" | 470.4×705.6 | 500×740×600 | 326.3 | **600** | 312.5×312.5×149.8, 1,531 dofs |
| native 1200/90×90/1" | 235.2×235.2 | 400×400×260 | 799.3 | 799.3 (in range) | 235.1×235.1×116.4, 931 dofs |

The geometric-mean rule is also wrong for an **axisymmetric** family under an HV brief: it builds a round mouth of diameter √(W·H). For B1 that is 406 mm, which **exceeds the 360 mm width envelope by 13 %**; for B3b it is 576 mm, 15 % over the 500 mm width. When the fc floor binds instead, the horn is 25–60 % too small. Both failure modes are visible in the seed row above. [measured]

**Recommendation:** for grid rows, derive fc from the **narrow-axis** requirement (`188,000/target_w`) when the family is round, or from `target_w`/`target_h` separately via the `fc_h`/`fc_v` pair that the `lecleach` rows already accept but no shipped config exposes. Do not use the geometric mean for a non-square mouth.

---

## 2. Knob physics (measured on the exact Fourcade march)

All march numbers: `lecleach_exact`, r0 17.78 mm, exit half-angle 5°, c 343 m/s, dl 1 mm, stop 170° unless stated. [measured]

### 2.1 `g_fc_hz` — area-law cutoff (`m = 4πfc/c`)
- **Mouth size:** at fixed stop ≥170°, `W·fc` is invariant at **1.86–1.89e5 mm·Hz** across T 0.5–1.0 and r0 12.7/17.78/25.4. So fc 300 → W ~620; fc 600 → W ~313; fc 1200 → W ~158.
- **Depth:** roughly ∝ 1/fc: r0 17.78, T 0.8: fc300 D399, fc600 D147, fc1200 D42.
- **Validity floor:** the construction refuses (`S_ii ≤ 0`) when the area law grows too slowly for the discrete ring. Measured floors at stop 170: r0 12.7 → fc 400 only at T 1.0 (fc ≤350 refused at every T); r0 17.78 → fc 300 only at T 1.0, fc 350 at T ≥0.8; r0 25.4 → fc 256 at T ≥0.8. Smaller dl (0.5/0.25/0.1) does **not** rescue it, so this is a property of the construction, not the step. [measured]
- **What the brief overrides:** it replaces the seed only; the bounds stay, so the clamp is silent except in the `feasibility.derivation` note.

### 2.2 `g_T` — Fourcade shape factor
- T = 0 catenoidal, 0.707 hypex, 1 exponential (Fourcade eq. 42; ETF10 p.71/74). [published]
- **Mouth is nearly T-invariant** at stop ≥170 (1.86–1.89e5). **Depth is strongly T-dependent**: fc300, r0 17.78: T 0.3 D95, T 0.8 D399, T 1.0 D399 (T 0.3 refused at fc 300 below r0 25.4). At fc 600: T 0.3 D95, T 0.5 D164, T 0.8 D147, T 1.0 D136. So T trades throat flare/loading against depth, not mouth width. [measured]
- Low T + low fc is the invalid corner (1" and 1.4"): T ≤0.3 is refused at fc ≤600 for r0 12.7; T 0.5 is refused below fc ~480 at r0 17.78 (462 ERR, 500 OK) and below ~750?800 at r0 12.7. [measured]

### 2.3 `g_stop_deg` — how far around the rollback the wall is followed
- It is the **mouth-width knob at fixed fc**: `W·fc` = 1.47e5 at 90°, 1.72e5 at 120°, 1.88e5 at 170°, 1.88e5 at 240°. Above ~170° the width saturates (max y reached) and only curl/depth/self-approach grow. [measured]
- Stop 90 is a “no-rollback” horn (S 90° included? no: 45° half wall); stop 170–200 is the width-maximising practical window; 240 adds a near-closed lip with a 2t+2 risk.
- The 120–240 bounds are sensible; the upper end is not binding for width, but it is the source of most self-approach refusals at small mouths.

### 2.4 `g_eps_m`, `g_eps_start` — odd-cosine one-sided asymmetry
- Law: `r(φ,s) *= 1 + eps·w(s)·cos φ`, w = smoothstep opening at `eps_start`. At the mouth (w=1) the section is a circle of radius R shifted by eps·R along +x; **width stays 2R**, but the +x rim reaches (1+eps)R. Envelope overshoot is one-sided: `eps_max ≈ (env_half − t)/R − 1`. For a 360 mm envelope and R 156: eps ≤ **0.135**. The shipped 0.20 overshoots B1 by 5.7 % [measured].
- Symmetry: exact up/down mirror (xz), no left/right mirror (yz). Measured max up/down error **1.13e-13 mm** over 25 rows; no left/right mirror pairs exist by construction. [measured]
- `eps_start` only decides where the shift opens; it does not change the mouth size and cannot create an aspect ratio. A JMLC “90×60” is not achievable by eps.

### 2.5 `g_r_lip_mm` — tangent-continuous torus lip
- Continues the wall with the same tangent for 180°, then curls back. At stop 170 the march has already reached max width, so the lip adds almost **no width** (fc300: 620.0 → 620.7 mm) but adds depth and a second self-approach surface. [measured]
- Its radius must scale with the mouth: r_lip 30 at a 235 mm mouth fails `2t+2 = 8 mm` (measured 7.745 mm), while r_lip 20–35 at a 620 mm mouth passes 16/17. [measured]
- It is a mouth-termination/aesthetic knob, not a pattern or loading knob.

### 2.6 `g_ar_m`, `g_ar_p` — area-preserving AR evolution (iwata_ar)
- `W/H = AR_m` exactly, `W·H = (2y)²` preserved; AR_t = 1 at the throat. AR > 1 is wider than tall; **AR < 1 (taller than wide) is not in the bounds**.
- `ar_p` changes how fast the AR is reached along the arc (p→0 front-loaded, p→2 mouth-loaded); mouth size is unchanged.
- Current bounds [1.2, 2.8] are the single biggest blocker for all four campaign briefs (need 0.667). [measured seeds: AR 1.2 → 258×215 instead of 332×498]

### 2.7 Pinned knobs
- **Driver exit radius r0** sets the low-fc validity: 12.7 → fc floor 400 (T 1.0); 17.78 → 300 (T 1.0); 25.4 → 256 (T 0.8). A bigger throat buys low frequency, not just more area. [measured]
- **Driver exit half-angle 5°:** Fourcade's reference is 4° (published 8° included). At r0 12.7/fc400/T0.8, a0 4° works but 5° refuses — the first-step bracket is knife-edge. This is a real construction sensitivity, not a bug; the brief's 5° is plausible but must be validated at each low-fc corner. [measured]
- **n_phi/n_s/wall:** 15 rows quarter / 25 full, 32 stations, 3 mm wall. The 2t+2 = 8 mm guard is what refuses tight lips; a thinner wall helps here but not for the asym curl. [measured]
- **f90:** stop ≤88° (FREEFORM z-monotone), L_mm 220 block (may only shorten), wall 1.5 mm. At an 8 kHz top the 1.5 mm shell fails the mesher's `t·κ` guard at the 1 mm first step; **1.0 mm meshes** (653 dofs, 169 mm). [measured]

---

## 3. Per-config analysis

### 3.1 `lecleach_rollback` (axisymmetric, quarter, 3 knobs)
Current: seed fc 800/T 0.8/stop 170; bounds fc 600–1200, T 0.3–1.0, stop 120–240.
- Honest for **round** loading horns whose f0 is a loading corner: native 1200 (235 mm, 931 dofs) is the natural operating point.
- For B1/B2/B3b it is the wrong geometry (round). It cannot make 332×498 or 470×706 at any fc.
- For B3a it works at **fc 268 / T 1.0 / stop 170**: **694x694x472 mm, 7,241 dofs** [measured]. The K-law 706 mm is 1.7 % short, so 90 deg is held to **~407 Hz**. At fc 300/T 1.0 the mouth is 620 mm and the corner is 455 Hz; at fc 266 or below the march refuses even at T 1.0. The family is blocked by the 600 Hz fc floor, not by physics.
- For B3b as a **loading** brief it is honest: fc 380–480 keeps the round mouth inside 500 mm (W 392–495), 2.9–4.5k dofs, loading corner 380–480. Pattern is round, not 90×60.

### 3.2 `lecleach_toroidal` (rollback + lip)
Same meridian and bounds plus `g_r_lip_mm` 6–35, seed 30.
- At B1/B2/B3b the lip is cosmetically interesting but acoustically minor (width +0.7 mm, depth +lip). It does not fix aspect ratio.
- At B3a it is the same meridian (fc 268/T 1.0 -> 694 mm) with a 20-35 mm lip; measured at fc 300 it was 620.7 mm and 16/17 passed, one self-approach at a tight stop. Lip cost at 694 mm is ~9-10k dofs [estimated].
- **Shipped-seed bug:** under the family-native 1200 brief the derived fc 799 + r_lip 30 gives 7.745 mm self-approach and is **mesh-refused**. r_lip must drop to ≤~14 mm for a 235 mm mouth. [measured]

### 3.3 `lecleach_asym_odd` (full ring, 5 knobs)
Current: seed fc 800/T 0.8/stop 170/eps 0.20/eps_start 0; bounds fc 600–1200, T 0.3–1.0, stop 120–240, eps −0.3..0.3, eps_start 0–0.5.
- This is a **lateral single-sided** horn, not a 90×60 horn. It is honest as an asymmetric directivity experiment, not as a coverage brief.
- At B1 eps 0.20 overshoots the 360 mm envelope by 5.7 %; eps <=0.135 fits. At B3a eps <=0.15 is safe; at B3b (500 mm width) eps <=0.10 or fc >=420.
- Cost: full ring at 8 kHz is **5,554-13,705 dofs** at 466 mm mouth (1/17 over 12k), and **22,444 dofs** measured at 620 mm (fc 300); at the 694 mm B3a solution that scales to **~28k** [estimated] - unaffordable even halved. Half model would bring B3b to 2.8-6.9k and native to 1,669 [estimated], but B3a-asym remains over 12k.
- Native 1200: 3,338 dofs, 235×240×116, mesh-ok (half would be ~1.7k).

### 3.4 `lecleach_iwata_ar` (area-preserving AR, quarter, 5 knobs)
Current: seed fc 800/T **0.5 pinned**/stop 180/AR 2.0/p 1.0; bounds fc 800–1200, T 0.5–0.5, stop 120–240, AR 1.2–2.8, p 0.5–2.0.
- This is the **only config that can serve B1/B2/B3b honestly**, once T is unpinned and AR < 1 is allowed. Measured fixes:
  - B1: fc 462/T 0.8/AR 0.667/stop 170 → **330.6×494.9×223, 2,612 dofs** (target 332×498). 4/17 envelope-over in the recommended box.
  - B2 with 1.4" driver: fc 278/T 1.0/AR 0.667/stop 170 → **524.8×786.3×420.9, 6,378 dofs** (target 529×794, envelope 560×830×450). [measured]
  - B3b: fc 326/T 1.0/AR 0.667/stop 170 → **466.8×699.3×354.7, 5,064 dofs** (target 470×706). [measured]
  - B3a (90x90): AR must be 1.0, which is below the 1.2 floor; fc 268/T 1.0/AR 1.0 gives ~694 mm round and ~7.2k dofs [estimated], the same as rollback.
- The T pin is the blocker at low fc: T 0.5 refuses fc <~480 (r0 17.78) and <~750-800 (r0 12.7). B1 at fc 462 and B3b at 326 need T 0.8; B2 at 278 needs T 1.0.
- Current seed under B1 is 258×215 (AR 1.2, fc 800) — 22 % narrow and 57 % short. [measured]

### 3.5 `lecleach_f90` (FREEFORM, 3 knobs + blocks)
Current: h_fc 600–1200, h_T 0.3–1.0, h_stop 60–88, L_mm 220, n_anchors 48, wall 1.5, mouth ellipse.
- It is a **non-rolled** JMLC: stop ≤88°. Mouth at fc 600–1200 is only ~158–243 mm; it cannot serve B1/B2/B3a/B3b (all need ≥332 mm).
- It gets **no f0 derivation** (typology branch has no lecleach rule), so it stays at fc 800 under every brief.
- At 8 kHz with wall 1.5 mm it is **mesh-refused** on all three briefs (surface-curvature guard at the 1 mm throat step); with wall 1.0 mm it meshes (653 dofs, 169 mm). At its default 5.5 kHz band it meshes (363 dofs). [measured]
- Honest use: small 90×90 loading horn, fc ≥600, band ≤5.5 kHz, and wall 1.0 if 8 kHz is required.

### 3.6 Recommended campaign seeds / bounds (the deliverable table)

All fcs in Hz, dimensions mm. `cap` = dof cap to set for that brief (measured + ~10 % headroom). `dislope = 0` on every row; `load 0.5 / z_min 0.5-0.7` where loading is the point; `cov` 0.3-0.5 where pattern is secondary.

| brief | config | `g_fc_hz` seed [lo,hi] | `g_T` seed [lo,hi] | `g_stop_deg` seed [lo,hi] | special | cap | measured seed |
|---|---|---|---|---|---|---|---|
| B1 850/90x60/1.4" | `lecleach_iwata_ar` | **462** [430,520] | **0.8** [0.75,0.90] | **180** [150,220] | `g_ar_m` **0.667** [0.63,0.72]; `g_ar_p` **1.0** [0.7,1.4] | 3,500 | 331x495x223, 2,612 dofs |
| B2 800/60x40/**1.4"** | `lecleach_iwata_ar` | **278** [268,295] | **1.0** [0.95,1.0] | **170** [150,200] | `g_ar_m` **0.667** [0.63,0.72]; `g_ar_p` **1.0** [0.8,1.3] | 7,000 | 525x786x421, 6,378 dofs |
| B2 800/60x40/1" | ? | ? | ? | ? | **do not run**: 1" march refuses fc <400; max mouth 465 mm; 60x40 control only to ~1.1 kHz [estimated] | ? | ? |
| B3a 400/90x90/1.4" | `lecleach_rollback` | **268** [268,320] | **1.0** [0.98,1.0] | **170** [160,200] | 90° holds to ~407 Hz; 1.7 % short of 706 mm | 8,000 | 694x694x472, 7,241 dofs |
| B3a 400/90x90/1.4" | `lecleach_toroidal` | **268** [268,320] | **1.0** [0.98,1.0] | **170** [160,200] | `g_r_lip_mm` **25** [20,35] | 11,000 | ~694 mm, ~9-10k [estimated] |
| B3a 400/90x90/1.4" | `lecleach_iwata_ar` | **268** [268,320] | **1.0** [0.98,1.0] | **170** [160,200] | `g_ar_m` **1.0** [0.98,1.02] (needs bounds widened down) | 8,000 | ~694 round, ~7.2k [estimated] |
| B3b 600/90x60/1.4" | `lecleach_iwata_ar` | **326** [310,340] | **1.0** [0.95,1.0] | **170** [155,200] | `g_ar_m` **0.667** [0.63,0.72]; `g_ar_p` **1.0** [0.8,1.3] | 5,300 | 467x699x355, 5,064 dofs |
| B3b loading-only round alternative | `lecleach_rollback` | **400** [380,480] | **0.9** [0.8,1.0] | **180** [160,220] | `cov` 0.3, `load` 0.5, `z_min` 0.5; pattern is round, not 90x60 | 5,000 | 392-495 round, 2.9-4.5k |
| native 1200/90x90/1" | `lecleach_rollback` | **800** [740,900] | **0.8** [0.6,1.0] | **170** [150,200] | `load` 0.5, `z_min` 0.7, `cov` 0.3-0.5 | 2,000 | 235x235x116, 931 dofs |
| native 1200/90x90/1" | `lecleach_asym_odd` | **800** [740,900] | **0.8** [0.6,1.0] | **170** [150,200] | `g_eps_m` **0.1** [0,0.15]; `g_eps_start` 0.2 [0,0.4]; full ring | 4,000 | 235x240x116, 3,338 dofs |
| native 1200/90x90/1" | `lecleach_f90` | **800** [740,900] | **0.8** [0.6,1.0] | **80** [60,88] | wall 1.0 for 8 kHz (1.5 refuses); band 5.5k otherwise | 1,000 | 169 mm, 653 dofs @8k |
| asym variants (lateral shift, not AR) | `lecleach_asym_odd` | B1 **600**; B3b **420** [400,480] | **0.85** [0.85,1.0] | **170** | `eps <=0.10` for a 500 mm envelope (0.13 for 360 mm); full ring; this is a one-sided shift, **not** a 90x60 coverage solution | 12,000 | 466x475 at fc400, 5.5-13.7k |

Notes:
- **`g_T` is a shape/depth knob, not a mouth knob.** Low fc requires high T in this construction: B3a 268 needs T 1.0; B2 278 needs T 1.0; B1 462 needs T >=0.8. Do not leave the shipped 0.3 lower bound in a low-fc campaign.
- **`g_stop_deg`** above 200 adds no width and adds self-approach; 150-200 is the campaign window. Keep 240 only as an exploration edge.
- **`g_ar_m`** must be derived from the brief's **narrow axis** (`target_w/target_h`), not assumed >1. For a round brief pin 1.0.
- **Dof caps**: the shipped 5,000/7,000/8,900 caps are too low for B3b-iwata (5,064), B2-1.4" (6,378), B3a-1.4" (7,241). Raise screen/verify/final to 5,300/8,000/12,000 for the fused campaign; asym full ring needs 12,000 but B3a-asym is still over at 8k (~28k).
- **Weights**: `dislope 0.0` for every JMLC brief; `load 0.5` + `z_min 0.5-0.7` for loading briefs; `cov 0.3-0.5` (or 0.0 for B3b loading-only) because a round/loading JMLC cannot hold 90x60 above 600 Hz.

---

## 4. Half-model verdict for `lecleach_asym_odd`

**Question:** with `r = base(s)·(1 + eps·w(s)·cos φ)`, is a half model cut on xz (y ≥ 0, quadrants `'12'`) legal?

**Geometry: YES, exact.** cos φ is even under φ → −φ, so the radius, x and z are unchanged and only y flips. Measured over the 25-row full ring: max |P(φ) − mirror_y(P(−φ))| = **1.13e-13 mm**. [measured] Both seam rows (φ = 0 and 180) lie on y = 0 and are present in a 0..180 span, so the cut is clean.

**Repo today: NO, not reachable.**
- `mesh/sizing.py` already supports it: `QUADRANT_FACTOR['12'] = 2`, `SYMMETRY_PLANE['12'] = 'xz'`; `topology.check_surface` understands `xz` (y ≥ 0). The solver/metrics layer would accept the result.
- The **rows generator** does not: `_rows_span_phis` emits only quarter [0,90], half [−90,+90], full [0,360); `_rows_span_requested` treats “half” as yz and **explicitly refuses** `span: half` for `lecleach_asym` with eps ≠ 0; `_GRID_SYMMETRY_AXES` in `mesh/grid_build.py` has no `'12'` key and its `expected` check only accepts `'14'` for a half.
- So `quadrants '12'` exists in the **solver** vocabulary but not in the **generator** vocabulary. No shipped or ad-hoc path can produce it without code changes (which this audit must not make).

**What it would take:** a new span (e.g. `span: half_xz`, φ 0..180 inclusive, odd n_phi ≥25), `_GRID_SYMMETRY_AXES['12'] = ('y',)`, `expected='12'`, and a coarse half-vs-full equivalence test. [estimated: ~1 day + a validation pass]
**Payoff:** exactly half the full-ring dofs. Measured full ring / half estimate: native 3,338 -> 1,669; B3b 5,554-13,705 -> 2,777-6,853; B3a 22,444 at 620 mm -> 11,222 (at the 694 mm solution ~28.1k -> ~14k, still over 12k) [measured/estimated]. The half model is therefore the right fix for B3b/native cost, but not for B3a at 8 kHz; B3a-asym needs a lower band top or a coarser mesh.

---

## 5. Compatibility matrix (8 kHz, epw 6, CPU mesh, caps raised)

Dofs are the reduced-domain node count from the written `.msh`; campaign caps still have to be raised (see §6). “Run-with-changes” means the config is usable after the listed bound/seed/brief changes, not that the shipped seed is.

| config | B1 850/90×60/1.4" | B2 800/60×40/1" | B3a 400/90×90/1.4" | B3b 600/90×60/1.4" (load) | native 1200/90×90/1" |
|---|---|---|---|---|---|
| **rollback** | **don't** - round 313-360 mm, cannot make 332x498; 2.0k | **don't** - <=465 mm even at the fc 400/T 1.0 floor vs 794 | **run-with-changes** - fc 268/T 1.0/stop 170 -> 694x694x472, **7,241**; holds 90 deg to ~407 Hz (2" alternative 699/7,446) | **run-with-changes** (loading only) - fc 380-480/T 0.8-1.0/stop 170 -> 392-495 round, **2.9-4.5k**; dislope 0, cov 0.3 | **run** - fc 800/T 0.8/stop 170 -> 235x235x116, **931**; 23.5 % mesh refusals in the wide box |
| **toroidal** | **don't** - same round limit; lip no width | **don't** | **run-with-changes** - fc 268/T 1.0 + r_lip 20-35 -> ~694 mm, **~9-10k** [estimated]; measured fc 300 box 4.9-8.1k, 1/17 self-approach | **run-with-changes** (loading) - same as rollback; lip adds depth, not width | **run-with-changes** - fc 799/T 0.8/stop 170, r_lip <=14 (shipped 30 refuses) -> ~235 mm |
| **asym_odd** | **don't** - eps 0.2 over 5.7 %; eps <=0.13; still round | **don't** | **don't** at 8 kHz - full ring **22,444** at 620 mm (fc 300), ~28k at the 694 mm solution; half ~14k, still over 12k; at 5.5k ~13k [estimated] | **run-with-changes** - fc 420/T 0.85/eps <=0.10/stop 170 -> ~448x452, **5-6k** [estimated]; measured fc400/eps0.2 seed 466x475 was 12.9 % envelope-over; full ring only | **run** - 235x240x116, **3,338** |
| **iwata_ar** | **run-with-changes** - T 0.8/fc 462/AR 0.667/stop 170 -> 331x495x223, **2,612**; 4/17 envelope-over | **don't as 1"**; **run-with-changes at 1.4"** - fc 278/T 1.0/AR 0.667 -> 525x786x421, **6,378** | **run-with-changes** - AR 1.0 (needs bounds), fc 268/T 1.0 -> ~694 round, **~7.2k** [estimated] | **run-with-changes** - fc 326/T 1.0/AR 0.667/stop 170 -> 467x699x355, **5,064** (screen cap 5.0k is 1.3 % short) | **run-with-changes** - AR 1.0, fc 800/T 0.5-0.8 -> ~235 round, ~0.9-1.0k |
| **f90** | **don't** — max 243 mm, round, no f0 derivation, stop ≤88 | **don't** | **don't** | **don't** | **run-with-changes** — band 5.5k as shipped (363 dofs); 8k needs wall 1.0 (653 dofs) |

**If H/V coverage was swapped by mistake** (i.e. the owner meant a *wide* 90×60, as every commercial JMLC is), then B1/B2/B3b become AR 1.5/2.79/1.5 *wide* briefs: `iwata_ar`'s existing 1.2–2.8 bounds are then correct and only the fc floor must drop. Confirm before campaign. This is the single highest-leverage question in the audit.

---

## 6. Over-constraining vs under-constrained

### Over-constraining (a bound is hit by a sensible design or blocks a brief)
| bound | current | why it binds | recommendation |
|---|---|---|---|
| `g_fc_hz` lo | 600 (rb/tor/asym), 800 (iwata) | derived fc is 462/290/266/326 for B1/B2/B3a/B3b; every shipped seed is clamped to a 313 mm horn | per-brief lo: B1 430, B2 268 (1.4"), B3a 268, B3b 300; keep hi 600-1200 |
| `g_ar_m` | 1.2–2.8 | all four briefs need W/H = 0.667 (tall); 1.2 is a *wide* floor | [0.60, 2.80]; derive AR = target_w/target_h; pin 1.0 for round briefs |
| `g_T` | 0.5 pinned (iwata) | T 0.5 refuses fc <~480 (1.4") / <~750-800 (1") | unpin: [0.75, 1.0] for low-fc campaigns; keep 0.5 for fc >=800 |
| `g_T` lo | 0.3 | invalid corner at low fc; 1" fc ≤600 refuses at T ≤0.4 | derive `T_min(fc,r0)` or raise lo to 0.5 for fc <600 |
| `g_r_lip_mm` | 6–35 absolute | 30 at 235 mm mouth fails; 35 at 313 mm also tight | [6, min(35, 0.12·R_mouth)]; pin ~12 for the native brief |
| `g_stop_deg` hi | 240 | width saturates at 170; 240 adds self-approach (4/17 at native) | keep 240 globally; use 150–200 in campaign boxes |
| `eps` hi | 0.3 | one-sided envelope: eps >0.135 overshoots a 360 mm envelope at R 156 | campaign eps ≤0.13 (B1) / ≤0.15 (B3a/B3b); keep generator cap 0.3 |
| `f90` stop | 60–88 | physical FREEFORM z-monotone; but it excludes all rollback briefs | leave; f90 is not a rollback config |
| `f90` wall | 1.5 | fails 8 kHz curvature guard | 1.0 mm for 8 kHz |
| dof caps | 5,000/7,000/8,900 | B3b iwata 5,064; B2 1.4" 6,378; B3a 1.4" 7,241; asym full ring up to 22,444 | campaign: screen 5,300, verify 8,000, final 12,000 (fused), per brief |

### Under-constrained / invalid regions
- **March refusal (`S_ii <= 0`)** - not scored as a mesh failure because it happens at seed/materialize time: 1" fc <=350 any T; 1" fc 400 only T 1.0; 1.4" fc <=266 any T (fc 268 works only at T 1.0; fc 300 at T >=0.95); 1.4" T 0.5 refused below ~480; 2" fc 256 T <0.8; T <=0.3 at fc <=600 for 1". These are **physical/construction** limits (dl-independent), not arbitrary bounds. [measured]
- **Self-approach (`2t+2 = 8 mm`)** — 23.5 % of the native-1200 rollback box (4/17), 5.9 % of toroidal B3a (1/17), 0/17 of the low-fc rollback boxes. Tight curl at small mouth + high stop is the culprit. [measured]
- **Envelope one-sided overshoot** — asym eps; 5.9–52.9 % of the wide boxes when fc is below the narrow-axis requirement. [measured]
- **Full-ring 8 kHz dofs** — 1/17 B3b points and 1/1 B3a point exceed 12k; the 5,000 screen cap is exceeded by the asym full ring even at the native 235 mm seed (3,338). [measured]

---

## 7. Mesh-probe failure rates (measured)

19 seed probes across the five configs × five briefs at 8 kHz, epw 6, caps raised:

- **14 ok, 1 envelope-over, 4 refused (21.1 % refusal).** The four: toroidal × native (self-approach 7.745 mm), f90 × B1/B3a/native (surface-curvature guard, wall 1.5). The envelope-over: asym × B1 (eps 0.20, 5.7 %).
- LHS cells (16 points + seed unless noted):

| cell | n | ok | envelope-over | mesh-refused | dofs (min–max, median) |
|---|---|---|---|---|---|
| rollback B1 (fc 520–600) | 17 | 15 | 2 | 0 | 1,576–2,175 (1,869) |
| rollback B2 (fc 500–600, T 0.9–1.0) | 13 | 13 | 0 | 0 | 1,675–2,256 (1,939) |
| rollback B3a (fc 300–400, T 0.95–1.0) | 17 | 17 | 0 | 0 | 3,602–6,298 (4,783) |
| rollback B3b (fc 300–450) | 17 | 8 | 9 | 0 | 2,897–6,292 (4,270) |
| rollback native (fc 600–1200) | 17 | 13 | 0 | 4 | 486–1,632 (882) |
| toroidal B3a (fc 300–400, r_lip 20–35) | 17 | 16 | 0 | 1 | 4,901–8,099 (5,872) |
| asym B3b (fc 400–600, eps ±0.2) | 17 | 16 | 1 | 0 | 5,554–13,705 (9,264) |
| iwata B1 fix (T 0.8, AR 0.6–0.8) | 17 | 13 | 4 | 0 | 1,588–3,662 (2,252) |
| iwata B3b fix (seed) | 1 | 1 | 0 | 0 | 5,064 |
| iwata B2 1.4" (seed) | 1 | 1 | 0 | 0 | 6,378 |
| asym B3a 620 mm (single) | 1 | 1 | 0 | 0 | **22,444** |

No crashes, no non-manifold/geometry-invalid surprises beyond the reported guards. All failures are honest graded refusals.

---

## 8. Web sources (fetched this session; HTTP status recorded)

| # | Source / URL | Status | What it establishes |
|---|---|---|---|
| 1 | Fourcade, *Calcul du Pavillon Le Cleac'h* (2015), `https://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf` | **HTTP 200**, 400,493 B; `pdftotext` 30.6 KB | eq. 42 `S(l)=S0[cosh(ml/2)+T sinh(ml/2)]²`, eq. 43 `m=4πfc/c`; T=0 catenoidal, 0.707 hypex, 1 exponential; fig. 7 reference fc 400, r0 25.4, 8° included, stop 360; 1 mm step “diminuer pour fc élevées” |
| 2 | sphericalhorns.net, “JMLC Inspired Horn Calculator” (2020), `https://sphericalhorns.net/2020/12/21/jmlc-inspired-horn-calculator/` | **HTTP 200**, 54,827 B | “With T = 1 we get very similar looking horn profiles than the original JMLC profiles”; opening angle is intrinsic to fc/T (“increase the opening angle either use a higher cut-off value or a larger T”); examples 300 Hz and 425 Hz; 425 Hz / 1.4" round; rollback terminated at 180° |
| 3 | Auto-Tech JMLC-350, `https://horns-diy.pl/horns/jmlc/jmlc-350/` + datasheet `.../2015/07/JMLC-3501.pdf` | pages **200**; PDF **200**, 816,861 B (image-only; rendered + read) | min 520 Hz; mouth **Ø595 mm**, overall depth **435 mm**, stations 382/372/325, throat adapters **Ø25.4/35.6/38.1/50.8 mm**; measured with D1500-Ti 2" 500 Hz–20 kHz; sonogram visibly narrows from wide at 500 Hz to ~±10–15° at 10–20 kHz |
| 4 | Auto-Tech IWATA-300, `https://horns-diy.pl/horns/iwata/iwata-300/` + `.../IWATA-3001.pdf` | **200**; PDF 795,353 B (image-read) | min 450 Hz; **590 W × 320 H × 450 D**, throat Ø50.8; D/W = 0.76 |
| 5 | Auto-Tech E-JMLC-300, `https://horns-diy.pl/horns/e-jmlc/e-jmlc-300/` + `.../E-JMLC-3001.pdf` | **200**; PDF 857,470 B (image-read) | min 500 Hz; **920 W × 330 H × 430 D**, throat Ø50.8; AR 2.79 |
| 6 | Auto-Tech JMLC-200T / 400 / 600 pages | **200** each | min 300 / 600 / 900 Hz; model number ≈ fc, usable band ≈1.5× model |
| 7 | Le Cleac'h, ETF 2010 lecture, `https://rintelen.ch/download/JMMLC_horns_lecture_etf10.pdf` | **200**, 12,729,303 B; pages 60–90 extracted | p.70 family list; p.71 hyperbolic family T=0 catenoidal, 0.5<T<1 hypex, T=1 exponential, T>1 sinh; p.74 “normal range of T between 0 and 1”; p.82 the method is “the relation between the area of the wavefront and its distance to throat” |
| 8 | diyAudio 140190, `https://www.diyaudio.com/community/threads/jean-michel-lecleach-horns.140190/` | **200 but Cloudflare “Validating browser”** — no content | **unsourced** this session; do not quote |
| 9 | azurahorn.com | **HTTP 422 / cert error**, cPanel placeholder | **dead/unsourced**; no specs used |
| 10 | DuckDuckGo HTML / Bing via reader | 202 challenge / no organic results | search layer unavailable; primary sources used instead |

**Web-derived design practice.** Model number ≈ design fc; “minimal frequency” ≈ **1.5× fc** for JMLC (350→520, 400→600, 600→900, 200T→300) and IWATA (300→450), **1.67×** for E-JMLC (300→500). Commercial JMLC is a **wide** or round horn (AR 1.84–2.79), with a full toroidal roll; the 350's 435 mm overall depth vs 325 mm to the last axial station shows the lip is ~110 mm of the depth, not width. T is not published by the vendor; Fourcade's T=1 is the exponential limit, sphericalhorns says T=1 looks like JMLC, and the repo's 0.8 seed sits between the T=0.5 quasi-Iwata convention and T=1.

---

## 9. Open risks / questions

1. **H/V convention.** All four campaign briefs are tall (H>W); all commercial JMLC/IWATA are wide. If the owner's “90×60” means the conventional wide box, the coverage labels are swapped and the `iwata_ar` AR bounds become correct as-is. Confirm before spending GPU time. This changes every recommendation above.
2. **The march validity floor is construction-specific.** It is dl-independent in our probe, but a different first-step convention (sphericalhorns P1→P2) or c=344 vs 343 could move it by tens of Hz. Do not treat “fc 266 is invalid” as a universal acoustic limit; it is a limit of the Fourcade 1 mm march with 5° exit.
3. **8 kHz dof counts are screen-mesh (epw 6) counts.** Verify/final meshing at epw 8 or a different band top can move them ±10–15 % [estimated]; re-run the dry-run with the final caps before the campaign.
4. **No BEM was run.** Pattern/loading conclusions come from the construction geometry, the K-law, the measured prior beamwidth (180 -> 54 deg), and the vendor sonograms - not from a new solve. Treat "holds 90 deg to ~407 Hz" as a K-law estimate, not a measured polar.
5. **Half model is not implemented.** The geometric proof is exact, but the generator work + a half-vs-full equivalence test is a separate slice. Until then B3a-asym is unaffordable at 8 kHz and B3b-asym is near the ceiling.
6. **`lecleach_f90` 8 kHz failure** is a wall-thickness/curvature-guard interaction, not a solver limit; 1.0 mm fixes it, but 1.0 mm may print poorly. Owner decision.
7. **Vendor “minimal frequency” is a manufacturer claim**, not an independently measured f3; the Auto-Tech datasheets are image-only drawings + polars, and their reference planes are unlabelled. Use them for scale/AR, not as pass/fail targets.
8. **The f0 derivation's geometric-mean rule** is a repo invention, not published. It should be fixed before the campaign or every axisymmetric HV brief will be silently mis-sized. This is the highest-value code change (outside this audit's write scope).

---

## 10. Artifacts

- `probe.py` — CPU march + gmsh probe (no solver, no Julia), config copy with raised caps.
- `run_cells.py` — bounded per-cell bound/seed overrides and LHS.
- `march_boundary.py` — pure-march fc×T×stop validity/dimension map.
- `cfgs/`, `out/*.jsonl` — every point, status, triangles, dofs, W/H/D, reason.
- `briefs/blc_lecleach_90x90_1200_1in_300_8k.yaml`, `briefs/draft_b2b_..._14in.yaml`, `briefs/draft_b3a2_..._2in.yaml` — scratch variants used for the 1.4"/2" checks.
- Web captures: `fourcade.pdf/.txt`, `etf10.pdf`, `etf10_p60_90.txt`, `jmlc350_page-1.png`, `iwata300_page-1.png`, `ejmlc300_page-1.png`, `web_*.md`.
