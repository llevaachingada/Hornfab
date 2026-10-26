# LANE D AUDIT — reference/hybrid typologies + brief/objective mechanics

Date: 2026-10-26. Branch `unified-typologies` (read-only). Interpreter
`C:\Users\hunte\Hrns\hornlab-search\.venv\Scripts\python.exe`, cwd
`C:\Users\hunte\Hrns\hornlab-search`. **No repo files edited.** CPU only: no GPU solve, no
`search`/`run` without `--dry-run`, no Julia. Scratch: this `audit_ref\` directory.

Evidence tags: **[measured]** = real gmsh mesh / real code output this session;
**[estimated]** = the repo's own pre-mesh area estimator (`build.estimate_triangles_premesh`,
the same one the dof guard uses) or arithmetic; **[read]** = code/doc citation only.

Probe harness (scratch, all CPU):
- `probe_ref.py seed` — `load_config(config, brief=...)`, caps raised **in memory** to 60 000,
  `mesh_spec("screen")` (f_max = 8 000 Hz), real `build_mesh` in a temp dir; records
  status, tris, dofs, mouth W×H, depth, envelope overshoot. 7 configs × 4 briefs.
- `probe_ref.py lhs` — same load, 28 LHS+corners points/config×brief through
  `space.denormalize` → `families.to_mesher_config` → coarse `resolve_geometry` (20 mm) +
  pre-mesh triangle estimate; records ok / envelope-over / refused + reason, mouth W×H,
  depth, est dofs.
- `capability.py`, `cap2.py`, `hyb_probe.py`, `obj_check.py`, `freqs.py` — counterfactuals and
  objective demonstrations.

---

## 0. Headline findings (read this if nothing else)

1. **`aspect_ratio` is W/H and is applied to the WHOLE horn, throat included.** `families.py:66`
   ("width-to-height scaling"); `profile_sampling.py:481-487` (`c = |cos φ|/aspect_ratio`) and
   `:860` (`raw_radials[i] = curve_radius * scale`). Measured: OSSE with r0 17.78 and
   `aspect_ratio 1.25` has a **22.2 × 17.8 mm elliptical throat**, not a 35.6 mm circular one
   [measured]. So the field is a whole-body ellipse stretch, not a mouth-only aspect.
2. **The shipped [1.0, 2.0] box cannot express the campaign briefs' mouth orientation.**
   The repo itself defines the required mouth as `W ← coverage_h`, `H ← coverage_v`
   (`config.py:1046-1047,1051-1052`) and `d = K/(f0·cov)` (`config.py:858-865`). B1/B2/B3b
   therefore need **W/H = 0.667 (taller than wide)**; B3a needs 1.00. With `aspect_ratio ≥ 1`
   the whole native OSSE/R-OSSE/ICW family can only make **W ≥ H** → B1/B2/B3b are
   structurally impossible for those families, and B3a is the only compatible native brief.
   The briefs' own envelopes are taller than wide (360×520, 560×830, 500×740), confirming the
   intent.
3. **Widening `aspect_ratio` below 1 is NOT a clean fix**: it also shrinks the throat in x
   (0.667 × 17.78 = 11.9 mm), so the horn no longer matches the circular driver exit and the
   source tag is an elliptical piston (the cap follows the throat boundary,
   `point_grid_sources.py:103-128`). The correct asymmetric construction already exists in the
   FREEFORM generator route: `crossSections = [circle@t=0, ellipse@t=1]` plus independent H/V
   meridians (`registry.py:316-326`).
4. **The native families get NO f0 seed derivation at all** — `config.py:1016-1019` writes
   "no generator block (formula/native family)". Under every campaign brief their seeds are the
   YAML seeds and are wrong: `osse_baseline` is **802×642×266 mm under all of B1/B3a/B3b**
   (overshoot 1.23 / 0.08 / 0.60) [measured].
5. **Native configs are driver-pinned at load and refuse other driver classes**:
   `osse_baseline` r0 17.78 refuses B2 (1-in); `rosse_baseline`/`icw_rollback` r0 12.7 refuse
   B1/B3a/B3b [measured, `ConfigError` at `config.py:556`]. ICW is the exception: its r0 lives
   at `icw_seed.r0_mm`, and the pin check tests only root `r0_mm` (`config.py:600`), so **ICW
   silently ignores the brief's driver** (same 300×300 seed under every brief) [measured].
6. **Only `biradial_keele` derives a K-law-true seed** for B2/B3a/B3b (measured 529.2×793.8 /
   705.6×705.6 / 470.6×705.6, exactly 100 % of required, 0.0 overshoot). B1 is refused at
   seed-load because its closure line needs W = 368.6 > the 360 envelope [measured].
7. **`widened_to_closure` is misnamed and the S1A invariant is false.** Under B2/B3a/B3b the
   biradial bound widening is driven by the **K-law mouth**, not the closure line:
   `v_rm_mm` 230 → **396.9** (B2), `h_rm_mm` 210 → **352.8** (B3a) [measured, derivation notes].
   S1A line 1257 ("Widening only ever reaches the closure line") does not hold.
8. **Screen never solves below 500 Hz; verify solves 300–500.** `band_lo` 300 is used only as
   the scoring mask, so rip/di/flat/load include 300–500 Hz in verify and nothing below 500 in
   screen [read + measured demonstration: zeroing sub-500 ripple changes verify J by −6.90 and
   screen J by 0.0000].

---

## Part 1 — configs

### 1.1 Orientation convention (the key check)

| fact | evidence |
|---|---|
| `aspect_ratio` = width/height | `families.py:66`; `docs/reference/PARAMETERS.md:67-76` ("b = a*aspect_ratio"); `profile_sampling.py:481-487` |
| `aspect_ratio` scales the entire meridian (throat + mouth) | `profile_sampling.py:819,860`; measured throat 22.2×17.8 mm at ar 1.25 |
| required `W` comes from **coverage_h**, required `H` from **coverage_v** | `config.py:1046-1047`, `1051-1052`; `_keele_required_mouth_mm` `config.py:862-865` |
| `f_break_h` uses the width, `f_break_v` the height | `evaluate.py:248` → `metrics/compute.py:146-147`; `mouth_dims_m` `evaluate.py:178-186` |
| required mouths | B1 332.0×498.0 (W/H 0.667); B2 529.2×793.8 (0.667); B3a 705.6×705.6 (1.00); B3b 470.4×705.6 (0.667) [measured] |
| envelopes | B1 360×520×400; B2 560×830×450; B3a 740×740×650; B3b 500×740×600 |

Consequence: **the K-law mouth for 90×60/60×40 at a shared f0 is taller than wide**, because
the larger coverage angle needs the *smaller* dimension. The shipped `a_deg 37.5 / ar 1.25`
OSSE seed does the opposite (60° H × 75° V at ar 1.25).

### 1.2 Per-config knobs

#### `examples/osse_baseline.yaml` — native OSSE (quarter, epw 6)

| knob | physical meaning | current seed / bounds | recommended per brief | reason | evidence |
|---|---|---|---|---|---|
| `r0_mm` | throat radius (pinned to driver) | 17.78 / [17.78,17.78] | B1/B3a/B3b ok; **B2 needs a 12.7 copy** | WP2 pin refuses a mismatched driver | `config.py:539,600`; measured ConfigError |
| `a_deg` | coverage half-angle (one value, both planes at ar=1) | 37.5 / [5,55] | B1: 30 (V=60); B2: 30 (scratch 1in); B3a: 45; B3b: 30 | sets the binding (V) axis | `families.py:54`; derivation `config.py:988-990` |
| `a0_deg` | throat half-angle | 15.5 / [2,30] | `exit_angle_deg` if the brief says `throat_angle_policy: pin`, else leave | brief does not pin | `config.py:571-585` |
| `L_mm` | axial depth, shared by both planes | 260 / [140,420] | B1: ≈169; B2: ≈381; B3a: ≈241; B3b: ≈338 | L sets the V mouth (K-law) | measured counterfactual |
| `aspect_ratio` | whole-horn W/H ellipse stretch | 1.25 / **[1.0,2.0]** | **do not lower** without a throat fix; use a FREEFORM typology for B1/B2/B3b | ar<1 makes the throat 11.9 mm wide | `profile_sampling.py:481-487,860`; measured |
| `n,s,q,k` | termination/saturation; mouth flare curve | n4 s0.7 q.995 k1 / n[2,8] s[0,1] q[.9,1] k[.3,2.5] | keep | mouth size is dominated by s/n; not a substitute for the L/ar geometry | measured |
| `exponent` | superellipse cross-section exponent | 4 / [1,8] | 4 | shape only | `families.py:64` |

Measurements [measured]: seed **15 524 tri / 7 917 dof** and mouth **802.1×641.7×266 mm** for
B1/B3a/B3b (identical — no derivation). Overshoot: B1 **1.2251**, B3a **0.0832**, B3b **0.6027**
→ the seed is graded-infeasible under B1/B3b before the search starts. B2 refused.

Counterfactual with the *correct* construction [estimated, coarse geometry]: `a_deg=30,
aspect_ratio=0.667` reproduces B1 **332.8×498.0, depth 164, ~3 008 dof @8 kHz**; B2
**529.9×793.7, depth 377, ~8 464 dof**; B3a `a=45, ar=1, L=241` → **705.6×705.6, depth 237,
~8 453 dof**. So the native family only needs a *throat-correct* asymmetric-mouth mechanism —
not merely a wider bound.

#### `examples/rosse_baseline.yaml` — native R-OSSE (quarter, epw 6)

| knob | meaning | current / bounds | recommendation | evidence |
|---|---|---|---|---|
| `r0_mm` | throat (pinned) | 12.7 / [12.7,12.7] | only 1-in briefs (B2); other briefs refused | measured |
| `a_deg` | coverage half-angle | 45 / [5,55] | B2: 30 | measured counterfactual |
| `R_mm` | nominal mouth/reference radius; length is derived | 155 / **[80,220]** | **B2 needs ≈400**; B1≈255; B3a/B3b≈360 | H/2 ≈ R; mouth is R-driven | `PARAMETERS.md:4049-4058`; measured |
| `tmax` | rollback truncation | 1.0 / [0.5,1] | 1.0 | full mouth | `PARAMETERS.md:4203-4205` |
| `q,m,r,b,k` | R-OSSE blend/shape | 1.0/.85/.4/.2/1.0 | keep | shape only | `families.py:108-116` |
| `aspect_ratio` | whole-horn W/H | 1.33 / [1,2] | same throat caveat as OSSE | `profile_sampling.py:860` |

Measured: B2 seed **412.3×310.0×78.2, 3 688 tri / 1 881 dof**, overshoot 0.0 but only
78 % × 39 % of the required mouth. `R_mm=400, ar=0.667` counterfactual → **521×788, depth 322,
~9 710 dof** [estimated] — inside B2's 830 depth/height and under the 12 000 safe dof budget.

#### `examples/icw_rollback.yaml` — native ICW (quarter)

| knob | meaning | current / bounds | recommendation | evidence |
|---|---|---|---|---|
| `icw_seed.R_mm` | aperture radius driving rollback | 160 / [80,220] | **B3a needs ≈500** (mouth ≈ 0.7·R) | measured max mouth 310 at R=220 |
| `icw_seed.tmax` | rollback saturation | 1.0 / [0.7,1] | 1.0 | `PARAMETERS.md:3686-3694` |
| `icw_seed.q,m,r` | seed shape | 1.0/.85/.4 | keep | — |
| `icw_seed.a_deg` | coverage half-angle, **pinned 45** | 45 / [45,45] | only 90° square; no asymmetric brief possible | `examples/icw_rollback.yaml` |
| `icw_seed.aspect_ratio` | W/H — **legal key but not exposed** | absent | expose it (1.0) if ICW must serve 90×60 | `families.py:173-176` (ICW shares OSSE shape keys) |
| root `r0_mm` | **not present** (nested only) | — | WP2 pin needs to target `icw_seed.r0_mm` | `config.py:600`; measured |

Measured: **same 300.0×300.0×46.1 mm, 2 120 tri / 1 081 dof under ALL FOUR briefs** (0–45 % of
required). The mesher also emits `outer wall self-intersects ... normal flip` on the seed (inner
surface unaffected) [measured]. ICW is 90×90-only today and far too small for B3a.

#### `examples/typologies/biradial_keele.yaml` — FREEFORM generator (quarter, epw 8 ship)

| knob | meaning | current / bounds | recommendation per brief | reason | evidence |
|---|---|---|---|---|---|
| `L_mm` | shared depth | 195 / [170,220] | B1 **≤185** (or B1 envelope W ≥375); B2/B3a/B3b 195 fine | closure line r0+tan(a)·L must fit the envelope | `config.py:963-975`; measured |
| `h_a_deg` | H-plane power-series wall half-angle | 40.5 / [30,45] | derived 0.9·cov_h/2 (B1 40.5, B2 27→clamped 30, B3a 40.5) | patent rule + bound clamp | `config.py:955-962` |
| `v_a_deg` | V-plane wall half-angle | 27 / [18,34] | derived 0.9·cov_v/2 (B2 18, B3a 40.5→clamped 34) | — | measured notes |
| `h_rm_mm` / `v_rm_mm` | per-plane mouth radius | 195/145; bounds [140,210]/[95,230] | derivation sets exactly req/2 and widens the bound when needed | K-law mouth | `config.py:968-984` |
| `h_n` / `v_n` | flare exponents | 5.5 / 4.0; [2,8] | keep | claim-14 range | `docs/research/typologies/BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md §4.4` |
| `mesh.epw` | mesh resolution | **8.0** | **6.0** for the campaign | halves tris/dofs | measured |

Measured seeds: B2 **529.2×793.8×198, 17 216 tri / 8 780 dof (epw 8)**; B3a **705.6×705.6×198,
21 120 / 10 771**; B3b **470.6×705.6×198, 15 254 / 7 780**; all overshoot 0.0 and exactly 100 %
of required. At **epw 6** [measured]: B2 9 803 tri (≈5 000 dof), B3a 11 966 tri (≈6 103 dof) —
comfortably under the 12 000 safe budget. B1 **refused**: `mouth 369 x 498 mm exceeds the brief
envelope 360 x 520 mm` (closure W = 368.6). Fix: B1 `max_mouth_w_mm ≥ 375` (the V axis, which
is the memory-bound axis, is unchanged) or `L_mm ≤ 185`.

#### `examples/typologies/hyb_osse_h_tractrix_v.yaml` — FREEFORM generator

| knob | meaning | current / bounds | recommendation | evidence |
|---|---|---|---|---|
| `L_mm` | shared depth | 120 / [90,170] | **not fixable by a small bound change** — exclude from B1/B2/B3a/B3b | measured V ceiling |
| `h_a_deg` | H OSSE half-angle | 45 / [35,55] | B2 derives 30 → clamped 35 | `config.py:988-990`; measured |
| `h_s` | H termination | 0.3 / [0,0.8] | keep | — |
| `v_fc_hz` | V tractrix cutoff (sets V curvature) | 650 / [450,1000] | **no rule here can reach the required H** | measured |

Measured: V-plane height max **161.7 mm at fc 450, L 170** (needed 498), and it *decreases* at
lower fc for a fixed L; the H OSSE at L170/a45 already gives W=409 > B1's 360. No shared-L
combination gives 332×498. Seeds: B1 230.8×162.2 (808 dof), B2 218.3×124.1 (674), B3a/B3b same.
Verdict: **not a candidate for these briefs**; L would have to grow well past 400 mm and the V
law replaced (hypex/tractrix can't both fit the shared depth).

#### `examples/typologies/hyb_osse_h_hypex_v.yaml` — FREEFORM generator

| knob | meaning | current / bounds | recommendation per brief | evidence |
|---|---|---|---|---|
| `L_mm` | shared depth | 120 / **[90,145]** | B1 **150**; B2 **≈350**; B3a **≈300**; B3b **≈210** | measured H mouth vs L |
| `h_a_deg` | H OSSE half-angle | 45 / [35,50] | lower `lo` to **30** (B2 cov_h/2=30; today derives 30 → clamps 35) | `config.py:988-990` |
| `h_s` | H termination | 0.3 / [0,0.6] | keep | — |
| `v_rm_mm` | **V mouth radius = the V mouth size** | 100 / **[50,140]** | B1 **255**; B2 **400**; B3a/B3b **355** | measured H=2·rm exactly |
| `v_T` | hypex T (loading shape) | 0.7 / [0,1] | keep | — |

Measured with `v_rm` at the required radius: B1 `rm 249, a45, L145` → **W 350, H 498, depth 145**
(fits 360×520!); B2 `rm 397, a30, L≈340` → W≈529, H 794, depth 340 (fits 560×830×450); B3a
`rm 353, a45, L≈300` → W≈700, H 706, depth 300 (fits 740×740×650); B3b `rm 353, a45, L≈195` →
W≈470, H 706. Today the derivation sets `v_rm = req_h/2` and then **clamps to 140** (all four
briefs) → the shipped seed is 280 mm tall vs 498–794 required (35–56 %) [measured].

#### `examples/typologies/qtw_waveguide.yaml` — FREEFORM generator (quarter, epw 8 ship)

| knob | meaning | current / bounds | recommendation | evidence |
|---|---|---|---|---|
| `L_mm` | shared depth / bell length | 190 / [150,215] | keep for high-f0 hifi; **exclude from B1/B2/B3b** | measured |
| `h_a_deg`/`v_a_deg` | arc turn = half dispersion (per plane) | 45/30; [34,46]/[22,33] | keep; B2 derives 30/20 → clamps 34/22, B3a derives 45/45 → clamps 33 | `config.py:991-993` |
| `h_R_arc_mm`/`v_R_arc_mm` | throat arc radius | 45/45; [25,80] | keep | — |

The QTW mouth is `arc + (L−z*)tan(a)`, not K-law sized. Measured seeds: B2 **266.5×176.4**
(50 %×22 % of required), B3a **380.4×268.7** (54 %×38 %), B3b **380.4×245.0** (81 %×35 %), B1
**refused** (378 > 360). The arc rule ties the *larger* coverage plane to the *faster* flare, so
its mouth aspect is ~1.4–1.5 where the K-law needs 0.667 — structurally the inverse. QTW is fine
on `hifi_90x60_1in` (f0 1450, small required mouth) but not on these low-f0 campaign briefs.

### 1.3 Compatibility matrix (campaign briefs)

`✓` = can hold the K-law mouth within the brief envelope using the config's own knobs
(measured seed or measured counterfactual); `✗` = structurally short; `pin` = refused at load.
dofs are at **8 kHz**, quarter domain, epw 6.

| config | B1 90×60 @850 1.4in | B2 60×40 @800 1in | B3a 90×90 @400 1.4in | B3b 90×60 @600 1.4in |
|---|---|---|---|---|
| osse_baseline | ✗ (W≥H; seed 802×642, over 1.23) | pin (17.78 vs 12.7) | **✓** a45/ar1/L241 → 706×706, **8 453** [est] | ✗ (W≥H; seed over 0.60) |
| rosse_baseline | pin | ✓ with R_mm→400, ar .667, **9 710** [est] (throat caveat) | pin (R_mm→~360 needed) | pin |
| icw_rollback | ✗ (ignores pin; 300×300) | ✗ (300×300) | ✗ (300×300; needs R≈500) | ✗ (300×300) |
| biradial_keele | ✗ seed (369>360; fix L≤185 or env W≥375) | **✓ exact**, 17 216 tri / **8 780** at epw8 → ~5 000 at epw6 [measured] | **✓ exact**, 21 120 / 10 771 → ~6 103 [measured] | **✓ exact**, 15 254 / 7 780 → ~4 375 [measured] |
| hyb_osse_h_tractrix_v | ✗ (V 162/498) | ✗ (124/794) | ✗ (162/706) | ✗ (162/706) |
| hyb_osse_h_hypex_v | ✓ with v_rm→255, L150, **~? <2 000** | ✓ with v_rm→400, L350 | ✓ with v_rm→355, L300 | ✓ with v_rm→353, L210 |
| qtw_waveguide | ✗ seed (378>360) and V 241/498 | ✗ (176/794) | ✗ (269/706) | ✗ (245/706) |

Seed measurements (real gmsh, 8 kHz top) [measured]:

| config | B1 | B2 | B3a | B3b |
|---|---|---|---|---|
| osse_baseline | 15 524 tri / 7 917 dof, 802×642, over 1.225 | load refused | 15 524 / 7 917, 802×642, over 0.083 | same, over 0.603 |
| rosse_baseline | load refused | 3 688 / 1 881, 412×310, over 0 | load refused | load refused |
| icw_rollback | 2 120 / 1 081, 300×300 | 2 120 / 1 081 | 2 120 / 1 081 | 2 120 / 1 081 |
| biradial_keele | seed refused | 17 216 / 8 780, 529×794 (epw8) | 21 120 / 10 771, 706×706 | 15 254 / 7 780, 471×706 |
| hyb_osse_h_tractrix_v | 1 585 / 808, 231×162 | 1 321 / 674, 218×124 | 1 585 / 808 | 1 585 / 808 |
| hyb_osse_h_hypex_v | 2 593 / 1 322, 291×280 | 2 010 / 1 025, 218×280 | 2 593 / 1 322 | 2 593 / 1 322 |
| qtw_waveguide | seed refused | 4 571 / 2 331, 267×176 (epw8) | 7 212 / 3 678, 380×269 | 6 891 / 3 514, 380×245 |

### 1.4 Probe failure rates (28 LHS+corners points per config×brief, shipped box)

Counts are `ok / envelope-over / refused` (refused = generator error, curvature guard, or
geometry-invalid). "Reach" = best simultaneous `min(W/W_req, H/H_req)` over valid samples; a
random-sample lower bound (the analytic counterfactuals above are the real ceiling).

| config | B1 | B2 | B3a | B3b |
|---|---|---|---|---|
| osse_baseline | 7/21/0, reach 0.66 | load refused | 21/7/0, 0.77 | 10/18/0, 0.59 |
| rosse_baseline | load refused | 25/3/0, 0.48 | load refused | load refused |
| icw_rollback | 26/0/0, 0.62 | 26/0/0, 0.39 | 26/0/0, 0.44 | 26/0/0, 0.44 |
| biradial_keele | load refused | 21/0/7, 0.86 (seed 1.00) | 23/0/5, 0.87 (seed 1.00) | 18/0/10, 0.87 (seed 1.00) |
| hyb_osse_h_tractrix_v | 18/0/6, 0.38 | 16/0/8, 0.24 | 23/0/1, 0.28 | 23/0/1, 0.28 |
| hyb_osse_h_hypex_v | 26/0/0, 0.57 | 26/0/0, 0.36 | 26/0/0, 0.38 | 26/0/0, 0.40 |
| qtw_waveguide | load refused | 26/0/0, 0.32 | 26/0/0, 0.38 | 26/0/0, 0.38 |

Notable refusal causes inside the *box* (real search-space loss):
- biradial closure guard: **5–10 of 28** samples rejected (`rm=… cannot close a tan(…) cone`).
- hyb_tractrix: 1–8 of 24 rejected by the FREEFORM outward-wall curvature guard
  (`max(0,−wallThickness·κ)=0.43–0.61 ≥ margin 0.40`) and 4 by the mouth envelope.
- osse/rosse LHS "envelope over" is the box being much wider than these tight envelopes; it is
  the graded-penalty path, not a crash.

**Probe failure rates are not the main problem.** `hyb_hypex`, `qtw`, `icw` sample 26/26 "ok"
(low dof, inside envelope) yet reach only 0.32–0.57 of the required mouth — a search over them
can never satisfy `cov`. The audit's warning is **capability**, not refusal rate.

---

## Part 2 — brief/objective mechanics (file:line for every claim)

### a) Which frequencies are solved; is 300–500 Hz scored in verify only?

**Screen** = `FREQ_GRIDS["screen"] = (500, 10 000, 12)` (`config.py:26-30`), top clipped to
`band_hi` (`mode_freqs`, `config.py:776-780`). For `band_hi 8000` [measured]:
`500, 643, 828, 1065, 1370, 1763, 2269, 2919, 3756, 4832, 6218, 8000` (12 points).

**Verify** = `(300, 16 000, 25)` clipped to 8000 (`config.py:28,777-780`) plus the WP4
`verify_points_per_octave` extension in [5 kHz, band_hi] (`config.py:43-45,781-787`). With
`verify_points_per_octave: 6` [measured] the union has **29** points:
`300, 344, 394, 452, 519, 595, 682, 782, 896, 1028, 1178, 1351, 1549, 1776, 2037, 2335, 2678,
3070, 3520, 4037, 4628, 5000, 5307, 5623, 6085, 6325, 6977, 7113, 8000`.
**The extension is additive; it never removes base points.**

**`band_lo` is not used by `mode_freqs` at all** — only `band_hi` clips the grid
(`config.py:777-779`). `band_lo` enters scoring only as the band mask
`band = (f >= band_lo) & (f <= band_hi)` (`scalar_v2.py:299`), used for rip/di/flat/load
(`scalar_v2.py:333-355`); cov/dislope additionally require `f >= f0`
(`scalar_v2.py:309-310,320-332`).

So: screen solves **nothing** below 500 Hz, while verify solves and scores 300/344/394/452 in
`rip`, `di`, `flat` and `load`. Demonstration [measured, `obj_check.py`]: setting the sub-500
ripple to 50 dB changes **verify J by −6.90**, screen J by **0.0000**. Two further consequences:
- `on_axis_db` is normalised to the **band mean** (`metrics/compute.py:104-115`), so adding
  300–452 in verify also shifts the reference used by `flat`.
- the K-law preflight's `verify_freqs_below_f0` is counted on the *frozen* 25-point grid without
  the ppo extension (`config.py:1060-1067`): B1 reports 8/25 while the real verify grid is 8/29.
  The count is right; the denominator is not the solved grid.

**Verdict:** screen and verify J are **not comparable** — different grids (density and band) and,
for the full-band terms, different frequency sets. This is inherent to the frozen design, but it
means a `screen → verify` J delta is not a pure "better geometry" signal. If the campaign wants
comparable J across tiers, score all terms over a common sub-band (see (c)) or accept
tier-local ranking only (the repo already warns; `BRIEF_AND_SCORING_GUIDE` §3).

### b) v3 masking; the `load` term; is z reported on the fused path?

**v3** = `objective_v3` (`scalar_v2.py:275-380`): `band` is the full `[band_lo, band_hi]`
(`:299`); `f0 = target.f0_hz if set else band_lo` (`:309`); `score = band & (f >= f0)`
(`:310`).
- **cov** is computed only on `score` (`:320-329`, frequency-weighted when `freq_weights` is set).
- **dislope** is fitted only on `score` (`:331-332`).
- **rip** (`:336-342`), **di** (`:344-353`), **flat** (`:355`), **load** (`:333-334`) use the
  **full band**.
- `terms["n_in_band"] = n_score` (`:377`) — despite the name, in v3 it is the *cov score count*
  (measured: screen 9, verify 21 for B1), not the in-band count. `n_nan` remains band-based
  (`:357-366`).
- With no `freq_weights`, v2 == v3 numerically (mask only removes below-f0 points from two terms).

The mask acts on **solved grid points**, so the effective cov floor is the first grid point
≥ f0: B1 f0 850 → first cov point **1065 Hz**; B2 800 → 828; B3b 600 → 643; B3a 400 → 500.

**`load`** (`terms.py:92-98`): `mean_f( max(0, z_min − Re z_throat) )` over the full band; `z` is
read from `metrics.z_throat_real` over the same band (`scalar_v2.py:333`), and
`z_throat_real` is **Re(Z_specific)/(ρc)** (`CONTRACTS` §10 at `docs/plan/01_CONTRACTS.md:541`;
`solve/beat.py:53,321-327`), so `z_min` is a dimensionless ratio with 1.0 = plane-wave duct.
The repo's own "loaded" threshold is **0.7** (`evaluate.py:273`, `LOAD_THRESHOLD`).

Is `load` usable to express "loads down to ~400 Hz"? **Not directly.**
- It is a *mean shortfall*, not a per-frequency threshold, so a 400 Hz shortfall is diluted by
  the ~12 (screen) / ~29 (verify) frequencies. Measured: z = [0.2,0.4,0.6,0.8,1.0] at
  300/400/500/1000/2000, z_min 0.5 → term 0.08; z_min 0.7 → 0.18.
- **Screen never solves 400 Hz** (grid starts 500), so a 400 Hz loading target is invisible in
  screen. Only verify (300–452 present) can see it.
- `z_min 0.5` (B3b) is *weaker* than the repo's loaded definition (0.7). Recommend `z_min 0.7`
  and `load 0.5` if the intent is "loaded", and treat it as verify-only evidence.
- A true "loads down to 400" objective needs a threshold/max over `f ≤ 400` (a `load_band_hz`
  plus `min_f`/`all(f≤400: z≥z_min)` shape), not the current mean.

**Is `z` reported by the `beat_cuda` fused path?** **Yes.** The impedance is computed after the
shared per-frequency solve in `impedance_for_radiators` (`BeatEngineDriver.jl:1311-1336`,
called at `:2042`) and emitted for every path at `:2138`; the fused Burton-Miller assembly lives
inside `pressure_for_drives`, which produces the same `pressure` array. The Python side converts
`raw.impedance` → `z_throat` unconditionally (`solve/beat.py:321-333`) after the fused-path
assertion (`:223-245,334-336`). Caveats: the library's own capability note calls `impedance` a
"raw mean pressure, not a mechanical or acoustic impedance" (`capabilities.py:363-370`); and
with `aspect_ratio != 1` the source tag is an **elliptical** cap (measured above), so the
area-weighted drive is not a circular-driver drive.

### c) Minimal exact design for `target.cov_band_hz` (NOT implemented)

Goal: score `cov` over a sub-band (e.g. f0..~f11), leaving rip/di/flat/load full-band and
dislope at the f0 mask.

1. **`hornlab_search/targets/spec.py`**
   - Add a field *after* `f0_hz` (keep it last; `report/html.py:453`, `tests/test_targets.py:73`
     and others construct `Target(...)` positionally with 5 args):
     `cov_band_hz: tuple[float, float] | None = None`.
   - `from_dict` (`:26-63`): after the `f0_hz` parse (`:52-53`), parse a 2-element list/tuple;
     validate finite, `0 < lo < hi`, and `lo >= band_lo` and `hi <= band_hi`. Raise `ValueError`
     with `"cov_band_hz"` so `load_brief` (`config.py:203-206`) converts it to `ConfigError`.
   - `f0_effective_hz` unchanged.
2. **`hornlab_search/objective/scalar_v2.py::_objective_v3`** (`:294-380`)
   - Keep `score = band & (f >= f0)` for dislope (`:332`).
   - Build a second mask, e.g. `cov_score = score & (f >= cov_lo) & (f <= cov_hi)` where
     `cov_lo, cov_hi = target.cov_band_hz or (f0, band_hi)`. Use `cov_score` **only** in the cov
     block (`:320-329`). If `cov_score` is empty → keep the current `NAN_TERM_FILL`/penalty
     behaviour and log.
   - `n_in_band` (`:377`): keep it = cov-score count (documented); add no new term key (the key
     set is frozen at `terms.py:22-27`).
   - `objective_v2` is untouched. With `cov_band_hz is None` v3 is byte-identical to today.
3. **`hornlab_search/config.py`**
   - No new top-level brief key: `cov_band_hz` lives inside `target:`; `load_brief` validates the
     target through `Target.from_dict` (`config.py:203-206`), so it is covered.
   - `_brief_preflight_and_derive` (`:1025-1070`) optionally echoes `cov_band_hz` into the
     `feasibility` block (nice-to-have; not required for correctness).
4. **Hash / provenance**
   - `config_sha` hashes `cfg.raw` including the merged `target` and `brief`
     (`search/rundir.py:40-42`; `config.py:657-668`) → a new band is automatically a **new
     record group**; resume refuses (or warns) via `cli.py:675-685`. Good.
   - The **solve-spec hash does not include the target** (`config.py:809-853`), so the solve
     cache is still valid; a disk solve-cache hit **recomputes metrics and J**
     (`evaluate.py:919-963`), so re-scoring is cheap and correct.
   - **Gap to close:** the in-run/resume memo is keyed on design+mesh+solve hash only
     (`evaluate.py:660-667`) — with `--allow-config-change` a resumed run can return the old J
     for already-evaluated designs. Add the target/objective identity to the memo key (or
     document `--allow-config-change` as unsafe across scoring changes). This gap already exists
     for `f0_hz`.
   - **Gap to close:** the GUI's solve-group fingerprint includes only
     `mode/band_lo/band_hi/verify_points_per_octave` (`gui/data.py:620-627`); it does **not**
     include coverage, f0, weights or (now) the cov band, so compare can silently mix different
     scoring landscapes. Add `cov_band_hz` (and ideally a target hash) to `ident`; pin it in
     `tests/test_gui_integration_phases.py`.
5. **GUI / docs**
   - `app.js:1676-1687` (`f0KpiHtml`), `:1745-1755` (objective options), `:2611` (brief hint
     "masks everything below ... f0"), and the pinned strings in
     `tests/test_gui_brief_authoring.py:731,814` must learn the cov band (or stay f0-only with a
     separate KPI).
   - `docs/plan/01_CONTRACTS.md` §11 is **frozen** and its `Target` block (`:553-563`) omits
     even the existing `f0_hz`; adding `cov_band_hz` therefore needs a dated **owner-approved
     amendment** recorded in the guide/CONTINUITY (do not edit the frozen plan without owner
     sign-off), plus `docs/BRIEF_AND_SCORING_GUIDE` and `INDEX`.
6. **Tests needed** (all offline):
   - `Target.from_dict` accepts `[lo, hi]`, rejects wrong length/type, `lo<=0`, `hi<=lo`,
     `lo<band_lo`, `hi>band_hi`, unknown keys still rejected.
   - v3 with `cov_band_hz` scores cov only on that subset: a synthetic MetricSet with a huge
     cov error outside the band but not inside yields the same cov term as the inside-only
     array, while rip/di/flat/load are unchanged (mirror `tests/test_brief_derivation.py:73-120`).
   - None/absent → v3 == v2 bit-for-bit.
   - Empty cov band → penalty, no crash.
   - `config_sha` changes when the band changes; solve-spec hash does not; run-dir snapshot
     round-trips.
   - GUI compare fingerprint distinguishes two bands (extend
     `tests/test_gui_integration_phases.py`).

### d) Driver f11 above-band treatment

`f11 = BESSEL_J1P_11·C_AIR/(2π·r0)` (`constants.py:12-16`; computed at
`metrics/compute.py:129-130`, radius from `evaluate.py:214-230`): **7 914 Hz at 1 in,
5 653 Hz at 1.4 in, 3 957 Hz at 2 in** [measured]. Above f11 the uniform plane/rigid-cap source
is not a real driver exit (`docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md:69-70`).

The **objective does not treat f11 at all** — no mask, no weight, no cap. It is a report scalar
(`metrics/compute.py:148`, `report/html.py:272-275,401`) and a GUI caveat rendered when
`band_hi > f11` (`app.js:1664-1673`).

Exposure at the campaign's 8 kHz top [measured]: screen points above f11 are B1/B3a/B3b **2/12**
(6218, 8000), B2 **1/12** (8000); verify **5/29** for the 1.4-in briefs. So at 8 kHz the f11
exposure is modest-but-real for 1.4 in and negligible for 1 in. For the shipped 2-in briefs
(f11 3 957) it would be 5/12 — substantial.

Recommendations: (i) keep 8 kHz as the *mesh* top but make the **scored** cov band
`f0..min(f11, band_hi)` via `cov_band_hz` (this is exactly the CONTINUITY follow-up); (ii) for
1.4-in/2-in campaigns, treat >f11 cov points as report-only or compare geometries only, and say
so in the run record; (iii) do not use 8 kHz as a *pattern* claim for a 2-in driver.

### e) Does the f0 seed derivation produce K-law-consistent seeds per config × brief?

| config | B1 | B2 | B3a | B3b | mechanism |
|---|---|---|---|---|---|
| osse_baseline | **no rule** | load refused | **no rule** | **no rule** | `config.py:1016-1019` |
| rosse_baseline | load refused | **no rule** | load refused | load refused | same |
| icw_rollback | **no rule** | **no rule** | **no rule** | **no rule** | same |
| biradial_keele | **derivation runs, seed refused** | **K-law exact** | **K-law exact** | **K-law exact** | `config.py:939-984` |
| hyb_osse_h_tractrix_v | partial: H a_deg only; V no rule | same | same | same | `config.py:988-996` |
| hyb_osse_h_hypex_v | V K-law, **clamped 249→140**; H a only | V **397→140**; H a 30→35 | V **353→140**; H a 45 | V **353→140**; H a 45 | `config.py:988-993,986-987` |
| qtw_waveguide | seed refused; a only | a 30→34, 20→22 (clamped) | a 45, v 45→33 | a 45, 30 | `config.py:991-993` |

So the K-law seed derivation is **correct for `biradial_keele` only** (B2/B3a/B3b; measured exact),
and it **silently clips elsewhere**:
- **No derivation at all** for native OSSE/R-OSSE/ICW — the notes say "no generator block
  (formula/native family)" (`config.py:1016-1019`). Their seeds are 39–242 % of required.
- **OSSE profile rule only sets `a_deg`**, not the mouth/depth (`config.py:988-990`), so hybrid H
  mouths are not K-law sized.
- **Tractrix has no rule** (`config.py:995-996`).
- **Clamps that silently break K-law**: qtw (B2 30→34, 20→22; B3a v 45→33), hyb_hypex
  (v_rm→140 on every brief), hyb_tractrix (B2 h_a 30→35), biradial (B2 h_a 27→30, B3a v_a 40.5→34).
  They are flagged `clamped_to_bound: true` in the derivation notes, but the **seed still loads**
  — so the GUI seed card is the only place the mismatch is visible.
- **B1 × biradial is a hard seed refusal**, not a clamp: the closure line at a=40.5, L=195,
  r0=17.78 is 184.3 → mouth 368.6 > 360 envelope. The derived `a` also cannot be 40.5 with a
  smaller L unless L is reduced (L is not part of the derivation).
- **The `widened_to_closure` flag fires for K-law widening**, not only the closure line:
  B2 `v_rm` 230→396.9, B3a `h_rm` 210→352.8, B3b `h_rm` 210→235.2, `v_rm` 230→352.8 [measured].
  S1A line 1257 says "Widening only ever reaches the closure line" — false. The note text itself
  is honest ("K-law mouth radius (d/2), floored at the closure line"), so only the flag name and
  the doc claim need correcting.

---

## Risks / recommendations (ranked)

1. **Do not expect the native OSSE/R-OSSE/ICW families to compete on B1/B2/B3b as-is.** Their
   cross-section model stretches the throat; the required mouth is taller than wide. Either
   (a) run those briefs on FREEFORM generator typologies, or (b) fork the mesher to add a
   mouth-only aspect/`throat_round` control, then widen `aspect_ratio` lo to ~0.6 with the
   throat pinned. Silently lowering `aspect_ratio` would ship a 12 mm throat for a 1.4-in driver.
2. **`osse_baseline`/`rosse_baseline` seeds are graded-infeasible under the campaign briefs**
   (overshoot up to 1.23). A campaign launched on them starts far outside the envelope; the
   search pays a graded penalty and may never find its way in. Reseed or use a derived typology.
3. **Biradial B1 needs an envelope or seed tweak**: `max_mouth_w_mm` 360 → ≥375, or `L_mm` seed
   ≤185. Everything else about biradial is green (exact seeds, 4.4–8.8 k dofs).
4. **Campaign caps**: with `solve.cuda_fused: true` (safe 12 000 dof) and `epw 6`,
   `dof_cap_screen`/`dof_cap_verify` must be raised from 5 000/7 000 to ~12 000, otherwise every
   8 kHz B1/B2/B3a seed is refused by the pre-mesh guard (measured: 15 524 tri OSSE seed,
   17 216 tri biradial epw 8). Set `biradial`/`qtw` `epw: 6` too.
5. **ICW is not driver-honest**: the WP2 pin misses `icw_seed.r0_mm` (`config.py:600`) and it has
   no exposed `aspect_ratio`; it runs a fixed 300×300 1-in horn under 1.4-in briefs. Fix the pin
   target or exclude ICW from cross-driver campaigns.
6. **`load` cannot express "down to 400 Hz"**: screen can't see it, the mean dilutes it, and
   `z_min 0.5` is below the repo's 0.7 "loaded" threshold. B3b's loading intent is currently
   only weakly scored.
7. **Screen↔verify J is not a clean delta** because verify adds 300–452 Hz to four full-band
   terms (and changes the `on_axis` reference). Rank within a tier; use `cov_band_hz` if a
   common scored band is wanted.
8. **f11 and the elliptical-throat source** are report-only caveats today. At 8 kHz the f11
   exposure is 2/12 screen points (1.4 in), but the source-model caveat still applies; cap the
   *scored* band at f11 for 2-in drivers.
9. **Provenance gaps for any new target key**: `config_sha` covers it; the solve-cache recomputes
   J; but the GUI compare fingerprint and the in-run memo do not key on scoring identity. Close
   both when `cov_band_hz` lands.

---

## Appendix — key raw outputs

```
# osse_baseline x B1 dry-run (shipped caps)
dry-run FAILED: seed cannot be meshed in screen mode: MeshTooLargeError: pre-mesh estimate
~17402 triangles (~8875 dofs) is over 1.5x the dof cap 5000 at f_max=8000 Hz, epw=6

# cap raised in memory, real mesh:
osse_baseline B1  15524 tri / 7917 dof, W 802.1 H 641.7 D 266.0, overshoot 1.2251
osse_baseline B3a same geometry, overshoot 0.0832
osse_baseline B3b same geometry, overshoot 0.6027
osse_baseline B2  ConfigError: bounds.r0_mm pinned 17.78 vs brief 12.7

# seeds (real mesh)
rosse_baseline   B2  412.3 x 310.0 x 78.2   3688 tri / 1881 dof
icw_rollback     all 300.0 x 300.0 x 46.1   2120 tri / 1081 dof
biradial_keele   B2  529.2 x 793.8 x 198.0 17216 tri / 8780 dof (epw 8)
biradial_keele   B3a 705.6 x 705.6 x 198.0 21120 tri / 10771 dof
biradial_keele   B3b 470.6 x 705.6 x 198.0 15254 tri / 7780 dof
biradial_keele   B1  GeometryInvalidError: mouth 369 x 498 > envelope 360 x 520
qtw_waveguide    B2  266.5 x 176.4 x 193.0  4571 tri / 2331 dof
qtw_waveguide    B3a 380.4 x 268.7 x 193.0  7212 tri / 3678 dof
qtw_waveguide    B1  GeometryInvalidError: mouth 378 x 241 > envelope 360 x 520
hyb_tractrix     B1  230.8 x 162.2 x 108.1  1585 tri / 808 dof
hyb_hypex        B1  290.9 x 280.0 x 123.0  2593 tri / 1322 dof

# biradial epw 6
B2 9803 tri (~5000 dof), B3a 11966 tri (~6103 dof)

# counterfactuals (coarse geometry + premesh estimate)
OSSE B1  a30 ar0.667 L169 -> 332.8 x 498.0, depth 164, ~3008 dof
OSSE B2  a30 ar0.667 L381 -> 529.9 x 793.7, depth 377, ~8464 dof
OSSE B3a a45 ar1.0  L241 -> 705.6 x 705.6, depth 237, ~8453 dof
OSSE B3b a30 ar0.667 L338 -> 471.4 x 705.6, depth 333, ~6703 dof
R-OSSE B2 R400 ar0.667   -> 521 x 788, depth 322, ~9710 dof
hyb_hypex B1 v_rm249 a45 L145 -> W350 H498 D145
hyb_hypex B2 v_rm397 a30 L340 -> W~529 H794 D340
hyb_hypex B3a v_rm353 a45 L300 -> W~700 H706 D300

# objective demonstration (B1 grid, f0 850)
screen n=12 f 500..8000, v3 n_in_band=9, zeroing sub-500 ripple: J delta 0.0000
verify n=29 f 300..8000, v3 n_in_band=21, zeroing sub-500 ripple: J delta -6.8966
load z=[.2,.4,.6,.8,1.0] at 300/400/500/1000/2000: z_min .5 -> .080 ; z_min .7 -> .180
```
