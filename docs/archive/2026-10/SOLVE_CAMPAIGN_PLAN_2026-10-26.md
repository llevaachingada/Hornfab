# Solve campaign plan v2 — 2026-10-26 (hardened rewrite)

Status: **OWNER REVIEW PENDING.** This document replaces the same-day v1 plan in full; the original is
preserved verbatim at [`SOLVE_CAMPAIGN_PLAN_2026-10-26.orig.md`](SOLVE_CAMPAIGN_PLAN_2026-10-26.orig.md)
and the per-claim change register is §11. Nothing has run on GPU. v2 was produced from five complete
CPU/web audit lanes plus an independent adjudication pass; every load-bearing number carries a
provenance tag: **[M]** measured on this tree, **[D]** derived from measured inputs, **[E]** estimate,
**[W]** published source with URL in the lane reports.

Evidence base:

| Lane | Scope | Report |
|---|---|---|
| A | Le Cleac'h / JMLC (19 seeds, 10 LHS cells, web) | `…\scratchpad\audit_lecleach\REPORT.md` |
| B | Salmon / X-shape rows (42 derivations, 6 LHS boxes, 70 meshes, web) | `…\scratchpad\audit_salmon\REPORT.md` |
| C | ATH / Morph / FREEFORM (325 probe rows, R-OSSE/ICW morph proof, web) | `…\scratchpad\audit_ath\REPORT.md` |
| D | Reference/hybrid configs + objective mechanics a–e | `…\scratchpad\audit_ref\REPORT.md` |
| E | Outside web research (drivers, real horns, typology fit) | `…\scratchpad\research_web\REPORT.md` |
| — | Orchestrator verification F1–F9 | `…\scratchpad\_orch\FINDINGS_2026-10-26.md` |
| — | Adjudication (verdicts on every register item) | in-session, oracle pass 1 |

**Bottom line vs v1:** the physics, the staged T0→T4 structure, the per-brief leaderboards and the
fused-as-opt-in approach all survive. What changes: ~8 of v1's ~30 cells could not start and ~6 more
would silently search the wrong horn; the campaign vehicle for asymmetric mouths is **R-OSSE + pinned
morph** (mesh-proven), not bound-widening; B2 is replaced by a credible 1.4″ brief; the budget is
2–3× v1's estimate; and one owner ruling (mouth geometry, §7 D-11) blocks the matrix freeze.

---

## 0. Facts (re-checked in the tree; consequences stated)

| Fact | Where | Consequence |
|---|---|---|
| `FREQ_GRIDS`: screen 500–10k×12, verify 300–16k×25, final 250–20k×36; **only the top clips to `band_hi`**; `band_lo_hz` never clips (`config.py:26-30, 776-780`) | [M] point lists in §11 | Screen never scores below 500 Hz; **final solves 250–300 Hz unscored**. Screen J and verify J are *different functionals*, not one score measured twice (screen↔verify = a definition change, demonstrated: zeroing sub-500 ripple moves verify J by −6.90 and screen J by 0.0000). |
| Verify with `verify_points_per_octave: 6` yields **29 points**, not 25 | `config.py:781-787` [M] | Record the real count; `verify_freqs_below_f0` denominators in the feasibility record are grid-relative. |
| v3 masks **cov + dislope** below `f0` on grid points; rip/di/flat/load score the full band | `scalar_v2.py:309-332, 357-358`, `terms.py:92-98` [M] | `n_in_band` is actually the cov-score count (screen 9 / verify 21 for B1); **B1's first cov-scored point is 1065 Hz**, not 850. Any "holds its pattern from f0" claim must be worded accordingly. |
| `load` = `mean_f(max(0, z_min − Re z))`, skipped when the solver reports no z; **z IS reported on the fused path** (shared `impedance_for_radiators`); normalised by ρc (plane wave = 1) | `terms.py:92-98`, `metrics/compute.py:118`, BeatEngineDriver `:1311-1336, 2042, 2138` [M] | B3b's load term is live on fused — but `z_min 0.5` is below the repo's own loaded threshold **0.7** (`evaluate.py:273`). Use 0.7 and verify-only evidence; a full-band mean dilutes "loads to 400 Hz". |
| Fused CUDA: **12,183 dofs = the comfortable measured point** (4,913 MiB peak, 13.7 s/freq); 15,984 completes but is memory-pressured (7,819 MiB ≈ 95 % VRAM, assembly 437 s, **458.6 s/freq — 33× slower**); 20,237 kills the worker host. Opt-in rides in the solve-spec `extra` only when true (old hashes untouched) | `FUSED_CUDA_2026-10-24.md` §6.2; `config.py:80, 821` [M] | Per-config opt-in is correct. **12,000 is a throughput/headroom cap, not a fit cap** — 15,984 "fits" but is unusable for a search (≈1.5 GPU-h per screen candidate; ~370 MB headroom vs a 350–500 MB GUI baseline). Anything above 15,984 is unproven; Phase B measures it. |
| **Native families get no f0 seed derivation** (`generator`-block-only rule) | `config.py:1016-1019`; [M] identical 15,524-tri/7,921-dof mesh under B1 *and* B3a | Every native cell needs hand-authored per-brief seeds/bounds. Do not extend the derivation for this campaign. |
| Driver-pin guard refuses mismatched pinned `r0` for OSSE/R-OSSE/ICW (`config.py:539, 556`); **ICW's pin is silently missed** (nested `icw_seed.r0_mm`) | [M] refusals measured | Per-brief r0 re-pin in every campaign copy; fix the ICW nested-key check. |
| `aspect_ratio` is **whole-horn W/H, throat included**, shipped `[1.0, 2.0]` | `families.py:66` [M] | ar<1 shrinks the throat (22.2×17.8 mm at 0.667). Do **not** widen downward — the morph route (Lane C) makes asymmetric mouths without mesher work. |
| JMLC rows march: mouth×fc ≈ 1.47e5 @90° → ~1.88e5 @≥170°; **salmon rows march: 2.57e5 @120° → 3.65e5 @170° (~3.23e5 @150°)**; commercial rims 2.7–3.8e5 [W] | Lanes A/B [M] | The shared `_ROWS_MOUTH_FC_INVARIANT = 1.88e5` is right for lecleach and **~1.7× wrong for salmon** → salmon seeds oversized / organic f0 too high. Both constants are **stop-dependent**; pin the campaign stop window and re-measure each at that stop with one rim definition. |
| The JMLC derivation uses the **geometric mean** of the K-law mouth, then clamps to shipped fc floors [600,1200]/[800,1200] | `config.py:1007` [M] | All four briefs derive below the floors (462/290/266/326) → every shipped JMLC seed is a ~313 mm round horn. Fix the rule and widen the floors per brief. |
| `morph_*` legal for OSSE/R-OSSE/ICW/FREEFORM; **R-OSSE+morph mesh-proven 17/17** (targets 1/2/3, wall 5.0/2.5 mm, incl. 529×794); ICW 6/6 (cosmetic outer-wall warning only). Base config's missing `wall_thickness_mm` silently becomes the mesher's **6 mm** default — the real cause of past self-intersection failures, not the morph | Lane C [M] | R-4 gate **PASSES**. Native asymmetric-mouth cells run as R-OSSE+morph with `wall_thickness_mm: 5` explicit and `morph_target` pinned per cell. |
| **Morph gene measurement**: rounded-int CMA gene is a discontinuous categorical (σ0 0.25 flips the seed target 15.8 % of steps; uniform bounds give 50/25/25); target 2 uses `max(half_w, half_h)` → turns 2:1 targets into circles | Lane C [M] | Pin `morph_target` per cell (`search: false`): 1 for rectangular PA mouths, 3 as a second cell, 2 only circular-with-shrinkage. Keep `morph_fixed ≤ 0.1` / `allow_shrinkage: 0`. |
| `f11 = 7,914 / 5,653 / 3,957 Hz` for 1″/1.4″/2″; the objective has **no f11 treatment** (report-only); at an 8 kHz top, 2/12 screen points exceed a 1.4″ f11, **5/12** exceed a 2″ | `metrics/compute.py:129-130`, `report/html.py:272-275` [M] | Without `cov_band_hz`, 1.4″/2″ entries are judged on geometry their drivers cannot excite. |
| Driver hardware [W: Lane E with URLs]: 1″ min-crossover 1.0–2.2 kHz (BMS 5530ND 1.0 kHz is the best); "1.4 inch" is **two exits** (35 mm / 36 mm); exit half-angles **1″ 5–6°, 1.4″ 2–3°, 2″ 0–1.2°**; 300–400 Hz loading needs the two-way/annular family (BMS 4592/4594, Axi2050) — DE1050/ND4020Ti2 are 2″/4″-coil and still rated 800 Hz; K-law = λ/(2 sin θ/2) × 1.16–1.29; vendor "cutoff" ratings sit 1.3–2× below true pattern control; ATH 20 %-Re loading point ≈ perimeter **1.9–2.6 λ** | Lane E [W] | The draft briefs pin 5° on 1.4″ — too fast. A 1″ driver at 800 Hz is not credible. |
| One GPU, one solve at a time; Julia-host hygiene; failures not cached, `--budget` counts per invocation | AGENTS.md | Carried unchanged from v1. |

K-law: mouth `d = 25,400,000 mm·deg·Hz / (f0 · coverage_deg)` per plane (the repo's rule).

---

## 1. Phase 0 — fixes before ANY GPU time (½–1 day, CPU only)

| # | Fix | Files | Gate |
|---|---|---|---|
| 0.1 | **Rows mouth constants stop-parameterised**: `_ROWS_MOUTH_FC_INVARIANT` becomes per-family (lecleach ≈1.88e5, salmon ≈3.2e5), each re-measured at the **pinned campaign stop window**, with ONE rim definition (outer extent incl. 2·wall) | `config.py:859, 1002-1008` | salmon + lecleach seed mouths within 5 % of the brief under the pinned stop |
| 0.2 | **JMLC derivation rule**: per-axis fc (or the narrow axis), not the geometric mean; widen `g_fc_hz` floors per brief (B1 [430,520], B3a [268,320], B3b [310,340]) | `config.py:1007`, typology YAMLs | every brief derives a seed inside envelope, within 5 % of K-law |
| 0.2a | **Organic-rollback f0 re-derivation** (~1,022/975/857 Hz for 1.4″/1″/2″) | brief YAMLs | **gated on Phase B item 6** (the W90-vs-rim A/B) — do not freeze before it |
| 0.3 | **Native per-brief seeds/bounds in campaign copies**; prefer R-OSSE+morph as the native vehicle (0.4) | campaign YAMLs | seed fits envelope; `preview_shape` sanity; BEM verify seed for portrait targets (Phase B item 7) |
| 0.4 | **Per-brief r0 re-pin** (every pinned-family copy); **fix the ICW nested-key pin** | campaign YAMLs, `config.py:600` | `run --dry-run` succeeds on every cell; ICW honours the brief driver |
| 0.4a | **`wall_thickness_mm: 5` explicit** in every R-OSSE/ICW/morph copy (6 mm default was the real self-intersection cause) | campaign YAMLs | zero shell self-intersection refusals in the dry-run matrix |
| 0.4b | **Morph hygiene**: `morph_target` pinned `search:false` per cell (1 rect / 3 second cell / 2 circular-only); `morph_fixed ≤ 0.1` or `allow_shrinkage: 0` | campaign YAMLs | no campaign copy searches a categorical gene |
| 0.5 | **Matrix freeze AFTER the §7 D-11 owner ruling** (mouth-geometry convention) | this doc | owner answered; conditional cells resolved in/out |
| 0.5a | **CPU LHS mesh audit**: 16–32 points per scheduled cell (rows-weighted) through the real mesher, caps raised in memory — v1's bound-corner audit, restored at audited cost, before any GPU spend | probe harness (scratch) | invalid % recorded pre-T1 per cell; boxes widened only where a bound is physically unreachable |
| 0.6 | **`cov_band_hz`** implemented per the adjudicated minimal design: `targets/spec.py` field **after** `f0_hz` (positional `Target`), validate 0<lo<hi in band; `scalar_v2.py::_objective_v3` cov-block-only mask; extend the in-run memo key (`evaluate.py:660-667`) and GUI compare fingerprint (`gui/data.py:620-627`); frozen-§11 dated amendment; tests incl. absent→v2-identical | `targets/spec.py`, `scalar_v2.py`, `evaluate.py`, `gui/data.py`, `report/html.py:453` | **gated on D-3 owner sign-off**; full new-test suite green |
| 0.7 | **`final` grid floor**: drop 250/276 (**final-only** bottom clip to `band_lo`; screen/verify grids untouched) or record documented acceptance of unscored sub-band cost | `config.py:768-790` | point list printed in records |
| 0.8 | **Doc fixes**: `widened_to_closure` is actually K-law-driven (S1A:1257 false — the widening reached 396.9/352.8 mm, past closure); `n_in_band` renamed to its real meaning; Lane B's old-path VRAM tier ("6.8–9.3k = edge/OOM") superseded everywhere by the fused SAFE 12,000 | S1A doc, CONTINUITY | review |
| 0.9 | **Campaign config generator**: copies under `examples/typologies/campaign_2026-10-26/` with `cuda_fused: true`, caps 12,000/12,000/12000, `epw 6`, K-law-consistent seeds; **dry-run matrix green on every cell**; the B2′ compatibility column is re-derived by this gate (its v2 numbers are [E] until then) | new YAMLs | `hornlab-search run --config X --brief PATH --mode screen --dry-run` green cell-by-cell |
| 0.10 | **`span: half_xz` implementation** (rows-generator span option, `_GRID_SYMMETRY_AXES` entry + `'12'`, half-vs-full test) — this is D-9's home; asym_odd B3b and Phase B item 5 both wait on it | `design/generators/grid.py`, `mesh/sizing.py` | Phase B item 5 A/B ≤0.05 dB / ≤1°; ~1 day [E] |

Carried from v1 Phase A, narrowed: the uncommitted ATH lane still needs its hunk-by-hunk review and
commit-by-itself (R-1/R-2/R-3/R-6/R-9 unchanged; R-4 now has an evidence pass; R-5 recorded; R-8
resolved by D-4; R-7 becomes the funded `span: half_xz` implementation, see 0.10). `lecleach_f90`
stays **out** of the campaign briefs (needs an unvalidated 1.0 mm wall at 8 kHz) — an **owner default
pending confirmation** (printability of a 1.0 mm wall), not a settled fact.

---

## 2. Phase B — measure before spending (GPU, 3–4 h, one job at a time)

1. **Fused 8 kHz ladder** at 474 / 550 / 635 / 706 / 800 mm, **plus a 706×1058 rung (~17 k dofs)** —
   the single most consequential unknown. Report dofs, peak VRAM, s/freq, and whether 17 k sits inside
   or beyond the 15,984 fit point. **A memory-pressured completion counts as unusable, not ok**
   (the 15,984 precedent: 458.6 s/freq, 95 % VRAM).
2. **`epw 5` vs `epw 6`** on one small and one large stored seed; accept only inside 0.055 dB / ~1°.
3. **Fused route coverage**: one seed solve each — rows (`lecleach_rollback`), a half model
   (`salmon_saddle`), full ring (`lecleach_asym_odd`), and a generated FREEFORM (`ath_twinray_380`).
4. **s/candidate at 5 / 10 / 17 k dofs on fused.** This decides the §6 budget; nothing is committed
   before it.
5. **Half-model A/B** for `lecleach_asym_odd` (`'12'` vs `'1234'`) after the `span: half_xz`
   implementation lands: offline comparison ≤0.05 dB / ≤1°. Geometry is already proven mirror-exact
   (1.13e-13 mm, Lane A); this proves the implementation.
6. **W90-vs-rim GPU A/B** (Lane B §4.3): one B1-reseed vs one organic-reseed — settles the residual
   1.7× acoustic ambiguity in the rows constants before 0.2a freezes the organic f0s.
7. **Portrait-coverage BEM verify seed** (Lane C risk 1): one R-OSSE+morph seed on a portrait target —
   geometry fits the envelope but nominal H reaches only ~42°; coverage must be measured before
   portrait morph cells are trusted.

Exit: dofs→(VRAM, s/freq) fused curve incl. 17 k, epw verdict, half-model delta, W90-vs-rim verdict,
portrait-coverage feasibility, and a go/no-go + s/candidate for every brief class.

---

## 3. Briefs

All campaign briefs: `objective.version: 3`, `verify_points_per_octave: 6`, `epw 6` (mesh), caps
12,000, K-law `f0_hz`. Envelope W←`coverage_h`, H←`coverage_v` (`config.py:1046-1047`).

| ID | Coverage | Driver | f0 | Mouth W×H (K-law) | Envelope | Verdict |
|---|---|---|---|---|---|---|
| **B1** `hifi_90x60_850` | 90×60 | 1.4″, r0 **pinned per owner: 17.5 (18 Sound class) or 18.0 (B&C/BMS class)** — drafts' 17.78 matches neither real exit [W]; a0 **2.5°** | 850 | 332×498 | 360×520×400 | **KEEP.** Realistic (1.16–1.24× Keele; JBL M2 / ATH 1.4″ practice) [W]. Fix exit half-angle (5° → 2.5°). **One campaign-wide r0 pick (17.5 or 18.0) applies to every 1.4″ brief — B1/B2′/B3a/B3b — and re-derives `ath_core_14in` (its 9,851 [M at 17.78] becomes [E]).** |
| **B2′** `pa_60x40_1200` | 60×40 | 1.4″, r0 17.5/18.0, a0 2.5° | 1200 | 353×529 | 380×560×220 | **REPLACES v1 B2.** Matches real 60×40 horns (210–270 mm holding 60×40 to 1.2–1.6 kHz) [W]. All compatibility numbers in §4 for this brief are **[E] until re-derived by gate 0.9** — v2's measured values were taken at the old 529×794 mouth. |
| **B2-stress** (optional) | 60×40 | 1″ @800, 529×794 | 800 | 529×794 | 560×830×450 | Run only on explicit owner ask — 1″ drivers are rated 1.0–2.2 kHz minimum and no production horn is this size [W]. Label as a stress test, never ranked with B2′. |
| **B3b** `pa_90x60_600_load400` | 90×60 | 1.4″ **300 Hz-class** (BMS 4594ND: r0 18.0, a0 2°) or 2″ (BMS 4592: r0 25.4, a0 0°) | 600 | 470×706 | 500×740×600 | **PRIMARY low-reach brief.** `load 0.5`, **`z_min 0.7`**, loading claim evidenced at verify only. |
| **B3a** `pa_90x90_400` | 90×90 | **1.4″, 300 Hz-class** (BMS 4594ND: r0 18.0, a0 2°) for the search cells; a **B3a-2″ variant brief** (BMS 4592, r0 25.4, a0 0°) exists only if the fallback driver class is exercised [W] | 400 | 706×706 | 740×740×650 | **Fallback.** Loads to 400 but true 90×90 pattern holds only above ~480–500 Hz; the 4594-class is the 300 Hz-rated single-driver option [W]. §4's B3a seeds were measured at r0 17.78 → re-tagged [E] under the campaign r0. |
| Le Cleac'h native | 90×90 | 1″ | fc 1200 | 235×235 | family brief | KEEP with `dislope: 0`. |

**D-11 owner ruling required (blocks the matrix freeze).** Strict K-law on both axes of a 90×60 brief
*necessarily* produces a portrait mouth (332 W × 498 H): wider coverage needs the *smaller* mouth —
the labels are not "swapped", the geometry is what the rule yields. The owner chooses:

- **(a) Strict K-law both axes** → portrait boxes as tabulated, native/morph families need the
  measured morph route, and JMLC needs AR < 1 bounds (Lane A finding).
- **(b) Commercial convention** → wide box, K-law on the H axis only, V allowed to narrow (as all
  surveyed production 90×60 parts do [W]) → coverage assignments swap, iwata's AR [1.2, 2.8] bounds
  stay correct, and the portrait-coverage problem disappears.

Both mouth geometries will be shown side by side at the ruling; whichever is chosen, every per-brief
seed in 0.2/0.3 is regenerated under it.

Also carried from the lanes: **B1/B2′/B3a score `load 0`** — a waveguide objective on families whose
defining virtue is loading (JMLC, Salmon). Either add `load 0.3 / z_min 0.7` to those briefs, or the
evidence write-up states the asymmetry explicitly. Non-CD briefs (all JMLC/salmon cells) carry
**`dislope: 0`**. X-shape cells need **diagonal-pattern evidence** (a 45/135° balloon check at T3, or
an explicit "H/V-only" label in every leaderboard — an H/V-only brief is blind to the X's defining
feature [W: audiohorn cross-wavefront papers]).

---

## 4. Typology matrix (frozen only after D-11; **21–23 cells**, 24 max with conditional)

Values are measured seeds at 8 kHz, quarter domain, `epw 6`, caps raised **[M]**, except where marked
**[E]**. **R** run · **C** run-with-changes (listed) · **✗** do not run · **cond** conditional.

| Config | B1 | B2′ [E] | B3a | B3b | Native | Notes / caveat |
|---|---|---|---|---|---|---|
| `osse_baseline` | ✗ envel. (B-1 seed, ar) | ✗ | cond 8,453 | ✗ | — | B3a only after seed re-anchor; **osse+morph** B2 clean 5,100–8,885, B3b 8/18 LHS usable, B1 half envelope-fail, B3a EDGE 7,982–17,493 (straddles SAFE) |
| `rosse_baseline` **+morph** (primary native) | cond 3,557 | — [E, re-derived at 0.9] | yes 7,468 | yes 6,611 | — | 17/17 mesh-proof [M]; **portrait-coverage verify seed required (Phase B 7)**; wall 5 mm explicit; B1/B2′ seeds re-derive at 0.9 — the printed B-column numbers were old-mouth measurements |
| `icw_rollback` | ✗ (mouth 300) | ✗ | ✗ (needs R≈500 > hi 220) | ✗ | — | morph itself proven (6/6); the family's mouth ceiling is the blocker |
| `biradial_keele` | ✗ seed (closure W 368.6 > 360) | **[E]** | yes ~6,103 (11,966 tri measured at B3a) | **[E]** (~4,375) | — | only K-law-exact derivation; B1 needs env W ≥ 375 or L ≤ 185 |
| `hyb_osse_h_tractrix_v` | ✗ (162 vs 498) | ✗ | ✗ | ✗ | — | V mouth ceiling |
| `hyb_osse_h_hypex_v` | C v_rm 255/L 150 | C [E] | C v_rm 355/L 300 | C v_rm 353/L 210 | — | samples cleanly (26/26) |
| `qtw_waveguide` | ✗ | ✗ | ✗ | ✗ | — | mouth ceiling 0.32–0.57× requirement |
| `lecleach_rollback` | ✗ (round; can't hold 332×498) | ✗ | C fc 268/T1 → 694, **7,241** | C loading-only 2.9–4.5 k | R 931 | its natural home is B3a/loading briefs |
| `lecleach_toroidal` | ✗ | ✗ | C ~9–10 k [E] | C | C lip ≤14 | shipped lip 30 refuses at 235 mm |
| `lecleach_asym_odd` | ✗ (eps 0.2 = +5.7 %) | ✗ | ✗ (~28 k full / ~14 k half — still >12 k) | C fc 420/T.85/eps ≤.10 → 5–6 k, **half** | R **3,338** | needs `span: half_xz` (0.10+Phase B 5); never a B3a family |
| `lecleach_iwata_ar` | C **2,612** | C [E] | C AR 1.0 → ~7.2 k [E] | C **5,064** | C AR 1.0 | the flexible JMLC for the campaign |
| `salmon_elliptical` | C 2,590 | C [E] | C 6,848 | C 5,242 | R, f0 1.7× high (0.1/0.2a fix) | |
| `salmon_x_signed` | C 3,427 | C [E] | C 9,302 | C 6,744 | R | envelope-refusals 24–41 % even in recommended boxes; **diagonal evidence required** |
| `salmon_x_shape` | ✗ | ✗ | ✗ | ✗ | C (+0.22 seed, 1,778) | seed refused at 7.997 mm self-approach |
| `salmon_saddle` | ✗ | ✗ | ✗ (22.7 s/candidate) | ✗ | C stop 140 | mesh-cost outlier |
| `salmon_ripple12` | C 4,993 | ✗ | ✗ | ✗ | C **pin lobes 12** | free-lobes gene: 16/16 refused [M] |
| `spherical_salmon` | ✗ | ✗ | ✗ | ✗ | ✗ | axisym; no f0 rule |
| `ath_core` | ✗ | ✗ | ✗ | ✗ | R (own 2″ brief) | pinned 25.4; a hi 32 + aspect 1.0 cannot serve 90×60; morph w/h 380–430 |
| `ath_core_14in` (new copy) | — | — | yes **9,851 [M at r0 17.78 → [E] at the campaign r0]** (706×706×451) | — | — | r0 re-derives with the campaign r0 pick; a 42–48, L 320–380, morph 680–730; labelled as an adaptation of the published recipe |
| `ath_twinray_380` | ✗ seed ref. | ✗ | ✗ | ✗ | R (own brief) | L hi 240 caps mouth 494×399 — does not scale; mesh 8.8 s median, 28.2 max |
| `perturbed_osse_hv` | ✗ | ✗ | ✗ | ✗ | R (own 1″ hifi) | corner 5–45, u ±0.15 (24–41 % refusals above) |
| `freeform_sculpt` | ✗ | ✗ | ✗ | ✗ | C 90×90 cell | radius 265–355, z 350–450 for PA sizes |
| `freeform_hv` | ✗ | ✗ | ✗ | — | demo only | |
| `lecleach_f90` | ✗ | ✗ | ✗ | ✗ | **out** | needs unvalidated 1.0 mm wall at 8 kHz |

Count — **dispatch rule, reconciling the matrix with the budget:** the matrix above lists every cell
that *can* run (~31 campaign-brief + ~13 native-capable). The **scheduled** campaign applies a
**max-5-cells-per-brief** rule — priority order per brief: (1) rosse+morph, (2) one JMLC (`iwata_ar`),
(3) one salmon (`elliptical` or `x_signed`), (4) `biradial_keele` or `hyb_hypex`, (5) one exploratory
(`ripple12` / `osse+morph` / `ath_core_14in`, conditional) — plus **4 native controls** (lecleach
native, `asym_odd`, `ath_core`, `twinray`) = **24 scheduled cells**; the matrix remainder is a reserve
pool re-entering only if a priority cell dies in T0. v1's ~30 included six cells whose `cov` term is
unsatisfiable by construction (icw/tractrix/qtw/spherical mouth ceilings) and three with broken seeds.

**Do not rank across briefs, objectives, f0 policies or solve groups.** Every leaderboard is per brief.

---

## 5. Phase C — staged execution (one GPU job at a time)

Every campaign config: copy under `examples/typologies/campaign_2026-10-26/`, `cuda_fused: true`,
caps 12,000, `epw 6`, seeds from 0.2/0.3 under the D-11 ruling. Before every job: `gpu-clean`, check
`runs\.gpu.lock`, record the `nvidia-smi` baseline, close the GUI. Fresh run directory per cell; no
resumes across box changes; count evaluations from the ndjson, never from the flag.

| Tier | What | Budget | Exit |
|---|---|---|---|
| **T0 seed** | 1 seed solve per cell | 1 | Seed J, dofs, s/candidate. Kill any refused/saturated cell — with Phase 0 done this should be zero |
| **T1 screen** | CMA, `sigma0 0.15`, seed 1234 | `max(100, 12·dims)` (CORE-copy 180, perturbed 216) | J-vs-eval, invalid %, best 5 |
| **T2 deepen** | **top 2 per brief × 4 briefs = 8 cells**: 1 second seed (4321), **budget 20·dims** | ≤400 | **Indicative seed-to-seed spread** — a defensible "family A beats B" claim needs ≥3 seeds or pooled within-cell variance; T2's two seeds give the pooled estimate, and a third seed runs only on a contested leader cell |
| **T3 verify** | **top 2 per brief (8) + top 2 native designs (2) = 10 runs** on the 29-pt 300–8000 grid + balloon 1024; **X cells add the 45/135° diagonal check** | 10 runs | Ranking survival vs screen (treat as partially definitional, §0) |
| **T4 final** | best 2 per brief, final grid clipped 300–8000 (bottom per 0.7) | 2 runs | Owner-facing numbers, f11 and above-f11 disclosure |

---

## 6. Budget (adjudicated; do not commit until Phase B item 4)

| Tier | Cells | evals | s/candidate | GPU-h |
|---|---|---|---|---|
| T1 small (<5 k dofs) | 9 | 150 | 30 | 11 |
| T1 mid (5–10 k) | 15 | 150 | 60 [E] | 37.5 |
| T2 (revised: 8 cells) | 8 | 225 | 60 [E] | 30 |
| T3 verify | 10 runs | 29 freqs | ~6 s/freq + balloon | 1.5–2 |
| T4 final | 6 runs | 36 freqs | ~8 s/freq | 1 |
| mesh time | — | — | — | +2–5 % (TwinRay 8.8 s/candidate median [M]) |

Mid-case **~82 GPU-h [D]** (T1 ≈ 48.5), honest range **70–110** — the 60–75 s/candidate mid-tier
values and the conditional large cells are the uncertainty; Phase B item 4 collapses it. Running the
full ~31-cell campaign-brief matrix **without** the 5-per-brief rule instead costs ~95–110 h [D].
v1's T2 design (top 3 per brief, 2 seeds, 25·dims) recomputes to ~75 h alone → **110–125 h total,
confirmed [D]** — that is the concrete cost of the v1 estimate.

---

## 7. Decisions

| ID | Decision | Status / recommendation |
|---|---|---|
| D-1 | B3 shape | **B3b primary**, B3a fallback (searched on the 1.4″ 4594-class per §3; the 2″ variant brief only if that driver class is exercised); nothing above 15,984 dofs runs before Phase B 1 measures it |
| D-2 | `epw 5` for screens | Only inside the noise floor; else 6 everywhere |
| D-3 | `cov_band_hz` | **Yes** — owner sign-off + frozen-§11 amendment first (0.6) |
| D-4 | ATH entries | **Resolved**: `ath_core` native-only; `ath_core_14in` copy for B3a, labelled as an adaptation; TwinRay native-only |
| D-5 | TwinRay superellipse vs morph | **Resolved**: superellipse for the campaign; mesher-guard fork is Phase E |
| D-6 | Morph gene | **Resolved by measurement**: pin target per cell; never a categorical gene |
| D-7 | B2 replacement | **Recommended yes**: B2′ (1.4″ @1.2 k). Owner confirms; stress-B2 optional |
| D-8 | Native asymmetric mouth | **Resolved**: R-OSSE+morph route (17/17 proven); do NOT widen `aspect_ratio`; crossSections stays FREEFORM-generator-only |
| D-9 | `span: half_xz` funding | **Yes** — 2× on asym B3b/native; geometry already mirror-exact |
| D-10 | Load term on non-low briefs | Add `load 0.3 / z_min 0.7` to B1/B2′/B3a — or disclose the asymmetry |
| D-11 | **Mouth geometry convention (strict-K-law portrait vs commercial wide)** | **OWNER MUST RULE — blocks the matrix freeze and 0.2/0.3 regeneration** |

---

## 8. What we expect to learn (tuning output)

1. **Solver economics:** the fused dofs→(VRAM, s/freq) curve incl. the 17 k point; epw-5 verdict;
   the half-model saving on the implemented `'12'` route.
2. **Search economics:** J-vs-eval curves by dims → the budget-per-dims rule; seed spread from T2's
   two seeds per deepened cell (pooled within-cell variance) plus a third seed on any contested
   leader → the minimum meaningful J gap; invalid rates per config → box fixes.
3. **Objective:** screen→verify rank stability *given the definitional delta*; the measurable effect
   of `cov_band_hz`; whether the f0 mask keeps 300–500 Hz honest at verify.
4. **Shape:** does Morph beat the same base (osse+morph / rosse+morph A/B, now mesh-proven)? Does
   freeform beat OSSE at matched budget (answerable via the morph A/B cells)? Where do asymmetric
   JMLC and loading-scored briefs actually help?
5. **Product:** best 2 per brief at the final grid with f11/above-f11 disclosure; loading claims
   evidenced at verify with `z_min 0.7`.

---

## 9. Phase D — reporting

Unchanged from v1: `docs/evidence/CAMPAIGN_2026-10-26.md` with per-brief leaderboards, Phase B tables,
every refusal/OOM with its reproduction, the byte-check script for quoted numbers, CONTINUITY + ISSUES
in the same commit as every push. Add: the diagonal-evidence rows for X cells, the portrait-coverage
verify result, and the W90-vs-rim A/B verdict next to every rows-family claim.

---

## 10. Out of scope

Multi-entry horns (Synergy/MEH). Band-split ranking (gate failed). Exact CORE `a(φ)`, `Mesh.Roundover`,
rear enclosures. Main/PR merge (owner has not asked). Extending `_derive_generator_geometry` for
native families (per-brief campaign copies instead). Mesher-guard fork for TwinRay rectangle morph.

---

## 11. Change register vs v1 (adjudicated by oracle pass 1)

| v1 location | v1 claim | v2 verdict |
|---|---|---|
| §0 rows 1–2 | "300–500 Hz floor needs no contract change" | Half true: `band_lo` never clips grids; final solves 250–300 Hz unscored; screen/verify J are different functionals (0.7, §5 T3) |
| §0 row 5 | fused SAFE 12,000 | Kept; **15,984 is the highest verified fit** — 17 k unproven until Phase B 1 |
| §0 row 7 | asym half model "may be legal" | **Confirmed** geometrically (1.13e-13 mm), implementation funded (D-9); still never a B3a family |
| §0 row 3 (v1 §3) | campaign configs get a "K-law-consistent seed" | False for natives (no derivation) and clamped-below-floor for JMLC — replaced by 0.2/0.3 with per-brief seeds |
| §2.1 | 706×1058 "fits but above SAFE" | Backwards: 17 k is **above** the verified-fit point; measured first |
| §2.5 | 64 LHS + 2^k corners per config×brief | Too expensive for rows (0.5–22 s/candidate); 16–32 points |
| §3 B2 | 1″ @800, 529×794 | **Replaced** by B2′ (1.4″ @1.2 k); old mouth kept as labelled stress test only |
| §3 natives | ath_core/TwinRay retargeted | ath_core native-only + `ath_core_14in`; TwinRay cannot scale (L hi 240 → 494×399) |
| §4 | icw/tractrix/qtw/spherical ● | ✗ — mouth ceilings 0.32–0.57× the requirement |
| §4 | x_shape/saddle/ripple12 ● | ✗ or native-only with fixed seeds (self-approach 7.997; 14 k dofs; 16/16 lobes refused) |
| §4 | asym ○ B1 | ✗ (eps 0.2 = +5.7 % overshoot); asym is B3b/native with the half model |
| §4 | "~30 cells" | **24 scheduled** via the max-5-per-brief dispatch rule (the matrix holds ~44 runnable cells; the rest is a reserve pool) |
| §5 T2 | top 3/brief, 2 seeds, 25·dims, "noise floor" | top 2/brief × 4 = **8 cells**, 1 seed, 20·dims; **relabelled indicative spread** — family claims need ≥3 seeds or pooled variance |
| §5.1 | 35–50 GPU-h | ~82 mid-case, 70–110 range under the dispatch rule; full-matrix option 95–110; original design recomputes to 110–125 |
| §6 D-8 | fund crossSections route | **Replaced**: R-OSSE+morph (measured, 17/17); crossSections stays FREEFORM-only |
| §6 D-11 | "H/V labels may be swapped" | Reframed: strict K-law *necessarily* yields portrait; owner picks geometry (a) or (b) |
| Phase A R-4 | R-OSSE/ICW morph unproven | **PASSES**: 17/17 and 6/6 mesh-proven; real culprit was the silent 6 mm wall default |
| — | (new) | Diagonal-pattern evidence for X cells; portrait-coverage verify seed; W90-vs-rim A/B; stop-parameterised rows constants; morph hygiene rules; `z_min 0.7`; `n_in_band` naming; verify = 29 points |
| §0 fused row | "SAFE 12,000" without the 15,984 cost | 15,984 = memory-pressured completion (458.6 s/freq, 95 % VRAM); **12,000 is a throughput/headroom cap, not a fit cap** — Phase B item 1 must reject memory-pressured completions as unusable |
| §4/§6 count triple | 21–23 cells vs 8-cell T2 vs 50-run T3 disagreed | Reconciled: max-5-per-brief dispatch rule → **24 scheduled**; T2 = 8 cells; T3 = 10 runs; budget rebuilt (~82 h mid-case, 70–110) |
| §1 | v1's LHS/bound-corner audit had no home in v2 | Restored as **0.5a**: 16–32 CPU points per scheduled cell, invalid % recorded pre-T1 |
| §1 | `span: half_xz` referenced but unowned | Now **0.10** with an owner, files, and a gate (Phase B item 5) |
| §3/§4 | ath_core_14in pinned r0 17.78 vs the brief driver pin | Reconciled: one campaign-wide r0 pick (17.5/18.0); B3a searches at the 1.4″ 300 Hz-class driver; B3a-2″ is a variant brief; ath_core_14in's 9,851 re-tags [E] |
| §1 | f90 exclusion read as settled | Marked **owner default pending confirmation** (1.0 mm wall printability) |
---

## 12. Readiness review (senior verification, 2026-10-26 afternoon)

**Verdict: the plan is sound, but the campaign (T0–T4) is NOT ready to run. Phase B items 1–4 ARE
ready and can run tonight on shipped configs.** Nothing under `examples/typologies/campaign_2026-10-26/`
exists yet, no campaign brief exists in `examples/briefs/`, and the primary native vehicle
(R-OSSE+morph) depends on uncommitted code.

### 12.1 Claims re-checked against the tree (all hold)

| Claim | Check | Result |
|---|---|---|
| Screen 12 pts 500–8000; verify 29 pts from 300; final 36 pts from 250 | `FREQ_GRIDS` + `mode_freqs` evaluated with band_hi 8000, ppo 6 | **holds** (screen first cov point after f0 850 = 1065.04) |
| Fused 12,183 dofs = 4,913 MiB / 13.72 s/freq; 15,984 = 437 s assembly, 458.6 s/freq | `FUSED_CUDA_2026-10-24.md:311-312, 336-344` | **holds** |
| Fused 8,919 dofs 9.1 s/freq; 4,438 dofs 2.1 s/freq | same `:391, :442` | **holds** |
| Natives get no f0 derivation | `config.py:1016-1019` | **holds** |
| Driver pin only checks top-level `r0_mm` (ICW nested `icw_seed.r0_mm` missed) | `config.py:600` (`"r0_mm" in seed or "r0_mm" in bounds`) | **holds** |
| JMLC derives fc from the geometric-mean mouth with one 1.88e5 constant | `config.py:859, 1007-1012` | **holds**; recomputed fc 462 (B1) / 266 (B3a) / 326 (B3b) / 290 (old B2) — all below the shipped `g_fc_hz` floor 600 (`lecleach_rollback.yaml:37-39`) |
| `LOAD_THRESHOLD = 0.7` | `evaluate.py:273` | **holds** |
| GPU idle / no stale Julia / no lock | `nvidia-smi` 493 MiB, no `julia.exe`, no `runs\.gpu.lock` | clean at time of review |

Not re-derived here (accepted from the lane reports): the salmon 1.7× constant, the 17/17 morph mesh
proof, the LHS refusal rates, and the web driver data. They are inputs to Phase 0 gates that re-measure
them anyway.

### 12.2 Gaps fixed in this review

1. **Gate 0.0 (new, first): review + commit the ATH lane by itself.** `families.py` `_MORPH` on R-OSSE
   is uncommitted; every rosse+morph cell (priority 1 on every brief) needs it in a committed tree, or
   `config_sha`/provenance points at nothing. Stage only its paths (handoff list); CONTINUITY + ISSUES in
   the same commit.
2. **Gate 0.11 (new): overnight runner.** There is no tool that runs a list of `(config, brief, budget)`
   cells sequentially. Write `tools/run_campaign_night.ps1` (or .py): per cell → `gpu-clean`, lock check,
   baseline `nvidia-smi` logged, `search --config --brief --budget --mode screen`, eval count read from
   the ndjson, `gpu-clean`; one log per night; a failed cell logs and moves on (never retries in a loop).
   Machine: plugged in, sleep disabled for the run (desktop keep-awake), GUI closed.
3. **0.7 simplified:** keep the frozen final grid and record acceptance of the two unscored 250/276 Hz
   points (2 extra freqs × 2–6 runs is minutes). A final-only clip is a contract §8 change for no gain.
4. **D-1 vs §3 inconsistency** on the B3a driver fixed (§7 now matches §3).

### 12.3 Budget re-check (fused s/freq interpolated from the three measured points)

s/candidate ≈ 12 × s/freq + mesh + ~5 s. Interpolated **[D]**: ~3 k dofs ≈ 30 s; ~6 k ≈ 60 s;
~8.5 k ≈ 107 s. Classifying the 24 scheduled cells by their §4 dofs:

| Group | Cells | evals | s/cand | GPU-h |
|---|---|---|---|---|
| T1 B1 + B2′ (≤5 k) | 10 | 150 | 30 | 12.5 |
| T1 natives: lecleach / asym / twinray (≤4 k) | 3 | 150 | 30 | 3.8 |
| T1 native ath_core (~6.8 k at 8 kHz [E]) | 1 | 180 | 70 | 3.5 |
| T1 B3b (5–7 k) | 5 | 150 | 60 | 12.5 |
| T1 B3a (7–10 k) | 5 | 150 | 107 | 22.3 |
| T2 (2 small-brief pairs, B3b pair, B3a pair) | 8 | 225 | 30/60/107 | 28.4 |
| T0 + T3 + T4 + mesh overhead | — | — | — | ~4 |
| **Total** | | | | **~87 h [D]** |

That agrees with §6 (~82 h). The breakdown matters, though: **B3a costs ~36 h of the 87**. If Phase B 4
measures B3a at more than ~110 s per candidate, cut B3a to 3 cells before cutting anything else.

### 12.4 Overnight schedule (~11 h per night, one sequential runner per night)

| Night | Content | GPU-h | Gate before it |
|---|---|---|---|
| **N0 (can be tonight)** | Phase B 1 (fused ladder via `tools/measure_fused_ceiling.py`, incl. the 17 k rung), 2 (epw 5 vs 6), 3 (fused route coverage, scratch copies of shipped configs with `cuda_fused: true`), 4 (s/candidate at 5/10/17 k) | 3–4 | none — independent of D-11 and Phase 0 |
| *day* | Phase 0 (0.0–0.11), owner rulings D-3/D-7/D-11/r0, CPU dry-run matrix green, LHS audit | 0 | — |
| N1 | Phase B 5–7 (half-model A/B, W90-vs-rim, portrait verify seed) + T0 all 24 cells + T1 B1 (5 cells) | ~9 | Phase 0 done; matrix frozen |
| N2 | T1 B2′ (5) + 3 small natives | ~10 | N1 T0 clean |
| N3 | T1 B3b cells 1–4 | ~10 | — |
| N4 | T1 B3b cell 5 + ath_core native + B3a cell 1 | ~10.5 | Phase B 4 s/cand within ±25 % of §12.3 |
| N5 | T1 B3a cells 2–3 | ~9 | — |
| N6 | T1 B3a cells 4–5 | ~9 | — |
| N7 | T2: B1 pair + B2′ pair + one B3b cell | ~11 | T1 leaderboards reviewed |
| N8 | T2: second B3b cell + one B3a cell | ~10.5 | — |
| N9 | T2: second B3a cell + T3 verify (10) + T4 final | ~10 | — |

**≈ 9 nights plus N0.** Fast path, if the owner wants results sooner: skip T2 (−28 h) → 7 nights,
with seed spread then unknown (rankings become indicative only).
