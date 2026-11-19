# Compact-horn / woofer-crossover candidate register — 2026-11-19

CPU-only scout pass (C-SCOUT-2026-11-19). No GPU solve, no search, no queue, no git mutation.
Machine-readable twin: [`candidate_register.json`](candidate_register.json). Mesh evidence:
[`mesh_preflight.md`](mesh_preflight.md). Next-step ask and the Pareto shortlist:
[`solver_proposal.md`](solver_proposal.md).

**Provenance.** Repo `C:/Users/hunte/Hrns/hornlab-search`, HEAD `277fa9386e2e4e27a6500ace6e8116657553b991`;
the runs below were produced by `hornlab_search` library sha `138d88a2163c` (recorded in each `run.json`).
Fable v2 is integrated locally at commit `627b880` (unpushed). Upstream `main` is still `138d88a`, so
**PR #75 is NOT merged**; `gh` could not resolve the repo from this session, so PR metadata is
**UNVERIFIED**.

**`config_sha`** is the real loader value:
`hornlab_search.search.rundir.config_sha(load_config(path).raw)` — not a hand hash. All ten values in
the JSON were re-checked against the loader after writing and match.

**Identities (never cross-ranked).** `home-v7` and `smooth-v7` are objective v7 with different briefs;
`v10` is objective v10; `v10_slope5` does not appear in this slate. Floors: **v7 stored-grid 0.3105 J,
v10 0.4677 J** (`docs/evidence/b1_mesh_2026-11-18/README.md`, `docs/CODE_MAP.md` L282).

**How geometry was measured.** "Inner mouth" = the widest inner aperture
(`2*max|inner x|`, `2*max|inner y|`) rebuilt from the **saved best design's** own grid params, never
from the YAML seed. "Outer/build bbox" = the saved `search.ndjson` `bbox_m`, mirrored about the
symmetry planes, in mm. "Depth incl lip" = the bbox z-span, which includes the returned lip
(negative z). Where a seed and a best differ, both are shown — `shape_check` on the seed is *not*
the best (A1's seed is 545 x 360 x 353 mm; its best is 567.9 x 379.3 x 322.3 mm).

**Driver fit.** 10-inch = 210.5 mm moving diameter, derived from Faital 10PR300 `sd_cm2: 348`
(`examples/drivers/faital_10pr300.yaml`) with the `motor_map` convention `d = 2*sqrt(Sd/pi)`.
12-inch = 260.5 mm is the 12PR300 Sd-derived value quoted in
`SENIOR_REVIEW_HANDOFF_2026-11-19` R2 (there is **no** 12PR300 YAML in `examples/drivers`).
Both are **moving** diameters: the frame radius is `NOT_YET_AVAILABLE`, so the spacing below is a
**lower bound**, not a frame-clearance verdict. Panel fit
(`woofer_seed.bl_panel_fit_feasible`) needs a real `C.BoxPoint`; this slate defines no cabinet, so
panel fit is `NOT_YET_AVAILABLE` for every row.

**Crossover screen (slate-only, not a design law).** "feasible" = measured V beamwidth at that XO
<= 80 deg **and** zero loading penalty (`lfp20_hz <= XO/1.6`, `objective/scalar_v7._load`) **and**
centre spacing <= 1.0 lambda for a 10-inch driver; "marginal" = exactly one miss; "not feasible" =
two or more misses, or V > 100 deg. lambda(900) = 381.1 mm, lambda(1200) = 285.8 mm. The V/H numbers
are the screen balloon at 10 m / 73 angles, **not** an installed polar — every installed claim is
`NOT_YET_AVAILABLE` (no BL case id exists for any row).

---

## 1. Summary table

| ID | Source config | sha | J (identity) | valid | inner mouth W x H (mm) | outer bbox W x H x D (mm) | 850/950/1100/1250 XO | 10 in spacing lambda900/1200 |
|---|---|---|---|---|---|---|---|---|
| A1 | `scout40w2_.../scout40w3__petal_hvlaw_v7.yaml` | `2e79402be1ec` | **4.16163 (home-v7)** | 40 | 567.9 x 379.3 | 567.9 x 379.3 x 322.3 | marg / marg / feas / feas | 0.78 / 1.04 |
| A2 | `scout40w2_.../scout40w3__tritonia_v9.yaml` | `1c07945ab727` | 5.00322 (home-v7) | 30 | 587.5 x 461.0 | 590.0 x 464.4 x 346.9 | marg / feas / feas / feas | 0.89 / 1.19 |
| A3 | `scout40w2_.../scout40w3__tritonia_v8.yaml` | `55a3166ff16b` | 4.89113 (home-v7) | 30 | 589.5 x 373.6 | 592.0 x 377.8 x 305.3 | no / marg / marg / marg | 0.78 / 1.04 |
| A4 | `ath_twinray_380.yaml` | `1673ccbc240c` | **NOT_YET_AVAILABLE** (reference only) | — | 380.0 x 303.3 | 381.0 x 304.3 x 187.5 | unknown x4 | 0.68 / 0.91 |
| A5 | `rolled_family_.../rf__rect_radial_wide_v7.yaml` | `e53a0c3ebe76` | 32.7379 (home-v7, aborted) | 2 | 503.3 x 278.9 | 535.7 x 294.7 x 235.1 | no x4 | 0.68 / 0.90 |
| C1 | `scout40_.../scout40__crowe_v2a_c1.yaml` | `806e6474b008` | 7.06855 (v10 rescore) / 4.87875 (smooth-v7) | 40 | 580.0 x 300.5 | 580.0 x 301.1 x 328.2 | no / marg / marg / marg | 0.68 / 0.91 |
| C2 | `scout40w2_.../scout40w3__crowe_x_square_v7.yaml` | `37b03559e9db` | 7.59825 (home-v7) | 10 | 461.1 x 460.0 | 461.4 x 460.5 x 231.4 | no / marg / marg / marg | 0.89 / 1.18 |
| K1 | `scout40w_.../scout40w2__klangfilm_b3_soft.yaml` | `7fb61f64dcc8` | 3.74283 (v10 rescore) / 2.80022 (smooth-v7) | 40 | 486.8 x 287.2 (v10 best) | 486.85 x 287.17 x 285.4 | no / no / marg / marg | 0.65 / 0.86 |
| K2 | `fable_v2_.../hl__klangfilm_lame_c200_vbeak_v10_v1.yaml` | `d4421ce593df` | 8.39100 (v10) | 30 | 585.1 x 249.7 | 585.1 x 249.7 x 195.8 | no x4 | 0.61 / 0.82 |
| R1 | `fable_v2_.../hl__rolled_rect_record_vbeak_v10_v1.yaml` | `8e86f248fb42` | 15.31965 (v10) | 30 | 542.0 x 297.4 | 542.0 x 297.4 x 238.2 | no x4 | 0.67 / 0.90 |

"marg" = marginal, "feas" = feasible, "no" = not feasible; definitions above.

---

## 2. Row detail

### A1 — petal H/V-law OSSE (`2e79402be1ec`)
- **Route/source.** Native OSSE profile, no typology generator: per-direction `a(phi)` wall law
  (`az_a_cos_amp` 13.65 deg, `az_a_cos_pow` 1.26) + superellipse mouth morph (540 x 400, corner 15,
  exponent 4.5, rate 3.46) + petal creases. HF1440 1.4-inch, 18.0 mm exit radius, 2.0 deg exit angle:
  **HF1440 modelled: yes**.
- **Best saved** `20261119T155454Z-screen-d1a61d`, design `74d8eed97268`, J **4.161632688418152**
  (**home-v7**), 40 valid / 54 attempts, status finished (budget), 4702 dof. Terms: load 0, dislope
  0.729, flat 0.493, flat_cv 0.184, diag 0.597, lfp20 425.9 Hz.
- **Recent runs.** W2 `20261119T143027Z-screen-401992` 4.1960 (30 valid) -> W3 `...d1a61d` 4.16163
  (40). Gain 0.0344 < 0.3105 floor -> **TIE**.
- **Morphology tags.** per-direction-wall-law | petal-crease | superellipse-mouth | landscape-wide.
- **Crossover.** V 88.8 / 80.2 / 69.4 / 61.7 deg at 850/950/1100/1250; H 65.8 / 63.0 / 60.6 / 62.1
  deg. Loading zero-penalty at all four (lfp20 425.9 <= 531 at 850). 850 and 950 are marginal only
  because V has not yet converged; 1100 and 1250 are the honest operating points. **Unknown:** no
  woofer, cabinet or installed/exterior solve.
- **Driver fit.** 10 in spacing 297.9 mm = 0.78 lambda(900) / 1.04 lambda(1200); 12 in 322.9 mm =
  0.85 / 1.13. A 10-inch sits inside one lambda at 900 Hz; at 1200 Hz it is 4 % over. Panel fit
  `NOT_YET_AVAILABLE`.
- **Further GPU?** No unconditional. The W3 is a tie; the cheap next step is a **CPU v10 rescore**
  of the 41 stored rows. A matched v10 continuation is only justified if that lands within 0.4677 J
  of the v10 leader (1.4214).

### A2 — tritonia v9 OSSE (`1c07945ab727`)
- **Route/source.** Native OSSE, per-direction law with `az_fold_v` (no crease), tall 461 mm mouth.
  HF1440 modelled: yes.
- **Best saved** `20261119T153950Z-screen-5d766f`, design `3ea64988763d`, J **5.003223187167279**
  (home-v7), 30 valid / 36 attempts, watchdog exit 75, 5931 dof. Terms: load 1.118, dislope 0.337,
  flat 0.530, flat_cv 0.651, diag 0.511, lfp20 552.0.
- **Recent runs.** W2 `20261119T141723Z-screen-433f54` 4.8785 -> W3 `...5d766f` 5.0032 = **0.1247
  WORSE** (below floor).
- **Tags.** per-direction-wall-law | az-fold-V | superellipse-mouth | tall-mouth.
- **Crossover.** V 69.0 / 62.8 / 56.3 / 55.8 deg; H 59.0 / 60.6 / 63.7 / 69.7 deg. Loading
  zero-penalty at 950+; a small penalty at 850 (552 > 531). 950-1250 read as the clean range.
  **Unknown:** the 461 mm tall mouth is the least cabinet-friendly OSSE shape here.
- **Driver fit.** 10 in 340.4 mm = 0.89 / 1.19 lambda; 12 in 365.4 mm = 0.96 / 1.28. Exceeds one
  lambda at 1200 Hz for both.
- **Further GPU?** No — the W3 regressed; no new DOF or box is proposed.

### A3 — tritonia v8 OSSE (`55a3166ff16b`)
- **Route/source.** Same per-direction OSSE law with `az_fold_v`, `n` widened to 4..10. HF1440 yes.
- **Best saved** `20261119T152446Z-screen-d98c8d`, design `cded84a911d2`, J **4.891129482719315**
  (home-v7), 30 valid, watchdog exit 75, 4874 dof. Terms: **load 1.593** (32 % of J), flat 0.606,
  flat_cv 0.625, diag 0.278, lfp20 596.9.
- **Recent runs.** W2 `20261119T140149Z-screen-f8fffb` 5.3728 -> W3 `...d98c8d` 4.8911 =
  **+0.4817, above the 0.3105 floor: REAL**. It ties A2 (0.11 J apart, inside the floor) despite A2
  having the better loading.
- **Tags.** per-direction-wall-law | az-fold-V | superellipse-mouth | compact-depth.
- **Crossover.** V 83.1 / 75.0 / 65.0 / 57.8 deg; H 60.7 / 68.1 / **76.0** / **77.0** deg. Loading
  zero-penalty at 1100+ (596.9 is 3 Hz over the 950 limit). The blocker is H ballooning at
  1.1-1.25 kHz, not loading.
- **Driver fit.** 10 in 297.1 mm = 0.78 / 1.04; 12 in 322.1 mm = 0.85 / 1.13.
- **Further GPU?** No — the gain is banked and the residual cost (load 1.59 + flat 0.61) is not
  DI-slope- or crossover-relevant.

### A4 — ATH TwinRay 380 published reconstruction (`1673ccbc240c`) — REFERENCE ONLY
- **Route/source.** `name: typology`, OSSE `profile_h/profile_v`, 16 anchors, superellipse mouth,
  **no returned lip**. Driver is the published 1.4-inch member: 17.78 mm exit radius, 5.0 deg exit
  angle (half of the published 10 deg total throat angle): **HF1440 modelled: no**.
- **Geometry** `[measured]` from a geometry-only rebuild of the config seed (no saved run for this
  file): inner 380.0 x 303.3, outer 381.0 x 304.3 x 187.5 mm. `shape_check` seed row: 380 x 303 x 197,
  1987 / 5000 dof.
- **Best saved: `NOT_YET_AVAILABLE`.** The only runs on this geometry are v3/v4 campaign copies
  (`20261027T001227Z-screen-fb6598` J 13.0670 v3; `20261027T045503Z-screen-971583` J 9.6040 v4;
  `20261029T013620Z-verify-3f4992` J 11.3653 v4). None is comparable to v7/v10.
- **Derived-lane context (a DIFFERENT config, `3b51e02f2bd8`).** The home-landscape derivative
  `hl__ath_twinray380_landscape_v8` carries the v10 number the parent quotes: run
  `20261117T001240Z-screen-7b664f`, design `85c59331e4a3`, **J_v10 1.7726** (stored v7 7.1256,
  5667 dof). That design is **not** this file's shape: L 311.6 mm, morph mouth 535 x 440, outer bbox
  537.0 x 442.4 x 411.8 mm. PRIORITY10 `20261119T175926Z-screen-8454e6` (design `bff6107b01a1`,
  2.5748, 31 valid) is a **reproduction from the lane seed**, not a continuation.
- **The LF point is not a crossover.** 680 Hz (36-04-266) / 580 Hz (36-10-380) is a
  20 %-throat-resistance definition, **not** a safe crossover.
- **Tags.** published-dimension-reconstruction | osse-linear | superellipse-mouth | no-returned-lip.
- **Crossover.** `unknown` at all four XOs for *this* config. The derivative measures V 71.6 / 64.6 /
  56.5 / 53.4 deg and H 60.3 / 56.4 / 52.0 / 51.1 deg, the only crossover-friendly V knee in the
  whole slate — but it belongs to the derivative, not to A4.
- **Driver fit.** 10 in 260.4 mm = 0.68 / 0.91; 12 in 285.4 mm = 0.75 / 1.00. The most compact row.
- **Further GPU?** No. The config's default 200-eval campaign is **not authorized**; reference only.

### A5 — rolled-rect radial relief (`e53a0c3ebe76`)
- **Route/source.** `name: grid`, rows `rolled_family_rect_v1` **mode radial**: the H/V wall centres
  pull inward (12/16 mm seeded) so the diagonal stays put and becomes a **ridge**; this is the
  ATH-like radial mechanism, explicitly *not* the axial pucker (SPIRAL_PUCKER_VS_RADIAL_RIDGE
  2026-11-15, finding 4). 3 mm wall. HF1440 yes.
- **Geometry** `[from-yaml]` (current implementation, config seed): inner 503.3 x 278.9, outer
  535.7 x 294.7 x 235.1 mm. `shape_check` seed: 541 x 299 x 241, 5096 / 6000 dof.
- **Best saved** `20261116T005943Z-screen-20db0d`, design `a4614c3dfdc4`, J **32.73792820123102**
  (home-v7) but only **2 valid of 48** — the run is aborted and `run.json` still says `running`.
  Saved bbox 541.3 x 298.6 x 238.1 mm, 4992 dof. Terms are the seed's: dislope 12.22, diag 9.95,
  flat 0.816.
- **Recipe drift (real finding).** The saved recipe no longer replays: `rows_grid_points` raises
  `GeneratorError: rolled-family schema or implementation differs from saved recipe` (the 2026-11-15
  implementation predates the current `rolled_family`). The config sha matches its run
  (`e53a0c3ebe76`), so the YAML is unchanged — it is the generator implementation that moved.
- **Tags.** radial-inward-relief | diagonal-ridge | spiral-base | non-CD-narrowing.
- **Crossover.** V 154.9 / 145.9 / 134.2 / 124.9 deg — not feasible at any of the four; but these
  are the aborted run's 2-eval best, i.e. essentially the seed, not a converged design.
- **Driver fit.** 10 in 257.6 mm = 0.68 / 0.90; 12 in 282.6 mm = 0.74 / 0.99.
- **Further GPU?** No. This cell has never had a real campaign; any ask is a *first* run, and the
  archived recipe no longer rebuilds. Re-emit the rows from the current generator first.

### C1 — CROWE V2A four-DOF (`806e6474b008`)
- **Route/source.** Generator `crowe_hv_area_aspect_v1`: forward area/aspect superellipse, four DOF
  (`L_forward_mm`, `area_mid_bias`, `aspect_timing_u50`, `height_v_active_mm`). Best: L 325.20,
  area bias -0.1495, u50 0.6422, height 300.50. No returned lip, no X-crease. HF1440 yes.
- **Best saved** `20261119T043506Z-screen-54878f`, design `febde0373489`: **smooth-v7 J
  4.8787457418045195**, 40 valid, 3331 dof; **v10 rescore J 7.068547250549901** (score_id
  `c4af7b6b...`, `mixed_identity: false`, 40/40 exact_complete; v10 seed design `1c206df9912f` =
  10.4104). Terms v7: load 0, dislope 0.435, flat 0.420, flat_cv 0.225, diag 1.723.
- **Tags.** area-aspect-superellipse | no-returned-lip | flat-panel-crowe | H-dominant-mouth.
- **Crossover.** V 103.7 / 93.3 / 80.1 / 70.3 deg; H 74.2 / 87.9 / **100.4** / 93.6 deg. Loading
  zero-penalty at all four (lfp20 362). The H flare balloons exactly across 0.9-1.1 kHz.
- **Driver fit.** 10 in 258.8 mm = 0.68 / 0.91; 12 in 283.8 mm = 0.74 / 0.99.
- **Further GPU?** No — the CPU v10 rescore already ranks it 5.65 J behind, far outside the 0.4677
  floor.

### C2 — Crowe-X square (`37b03559e9db`)
- **Route/source.** `name: grid`, rows `osse_rollback`, square 461 x 460 mouth. HF1440 yes.
- **Best saved** `20261119T161820Z-screen-9fda2a`, design `be9ab290d3cf`, J **7.598245619219523**
  (home-v7), **10 valid / 26 attempts** (16 `invalid_envelope`), watchdog, 3829 dof. Terms:
  **load 2.975** (39 % of J), flat 1.109, flat_cv 0.598.
- **Recent runs.** W2 `20261119T144903Z-screen-0ec862` 7.6183 (16 valid) -> W3 `...9fda2a` 7.5982 =
  0.0201, **TIE**.
- **Tags.** square-mouth | H-V-symmetric | osse-rollback | no-crease.
- **Crossover.** V 78.3 / 72.7 / 68.1 / 72.9 deg, effectively equal to H. Loading zero-penalty only
  at 1250 (lfp20 708.4 <= 781); penalised at 850-1100. The most uniform H/V of the ten but it sits
  above the 40-60 deg corridor.
- **Driver fit.** 10 in 338.5 mm = 0.89 / 1.18; 12 in 363.5 mm = 0.95 / 1.27.
- **Further GPU?** No — tie, load-dominated, and the box refuses 16 of 26 draws.

### K1 — Klangfilm Lame `b3_soft` (`7fb61f64dcc8`)
- **Route/source.** `name: grid`, rows `klangfilm_lame_hv_core` — the **frozen** Klangfilm Lame core
  kernel (one area law, held aspect, beak). HF1440 yes.
- **Best saved (identity split).** Run `20261119T073330Z-screen-723756`: v7 best design
  `ee85bcd2ad67` J **2.800217399969265** (smooth-v7, 40 valid, 523.5 x 311.0 x 307.4 mm); v10
  rescore best design **`3545b3e078ac` J 3.742832424084881** (score_id `bf1a9c81...`, 41/41,
  `mixed_identity: false`). The v10 best is a *different, smaller* design: inner 486.8 x 287.2,
  outer 486.85 x 287.17 x 285.4 mm, 2960 dof.
- **Warm chain.** `20261119T051630Z-screen-ce7a3f` 3.5400 (65 valid) -> `20261119T063219Z-screen-8deb7b`
  2.8412 (32) -> `20261119T073330Z-screen-723756` 2.8002 (40).
- **Tags.** klangfilm-lame-hump | hv-core-area-law | returned-lip-beak | frozen-family-kernel.
- **Crossover (v10 best).** V 104.9 / 95.3 / 82.5 / 70.9 deg; H 71.8 / 67.2 / 65.8 / 79.1 deg.
  Loading zero-penalty at all four (lfp20 434.8). Usable only from ~1.25 kHz; the V knee is the known
  Lame limit and the frozen kernel cannot raise V without narrowing H.
- **Driver fit (v10 best).** 10 in 246.6 mm = 0.65 / 0.86; 12 in 271.6 mm = 0.71 / 0.95 — the most
  spacing-friendly non-reference row.
- **Further GPU?** No — the CPU rescore already gives the v10 rank; the lane is 2.32 J off.

### K2 — Klangfilm c200 record + V-beak (`d4421ce593df`)
- **Route/source.** `name: grid`, rows `canonical_record_v2` on the c200 host; the two searched
  freedoms are **record-level** `vertical_timing` (vt 200.7 mm, hold 0.0019) and `vertical_beak`
  (D 1.77 mm, start 0.633) — the V lips move forward along the axis, the side walls stay put.
  HF1440 yes.
- **Control gate.** `hl__klangfilm_lame_c200_record_control_smooth.yaml` (`e4a84ddb505e`) replays
  the parent: `20261119T165650Z-screen-f30e50`, design `3c4aa3350077`, J 7.44663 v7 vs the parent
  7.4458 — the record route replays acoustically.
- **Best saved** `20261119T165732Z-screen-3ebb94`, design `2edf3ea06d10`, J **8.391004491167408**
  (v10), 30 valid, seed v10 8.4198 -> gain 0.029 (far below 0.4677), 4808 dof. Terms: **dislope
  6.334** + **diag 7.409** dominate; load 0.717.
- **Tags.** record-level-V-timing | V-lip-beak | single-area-law | klangfilm-c200-record.
- **Crossover.** V 163.9 / 144.9 / 123.9 / 118.1 deg; H 96.0 / 92.0 / 87.3 / 84.7 deg. Not feasible
  at any of the four by this screen.
- **Driver fit.** 10 in 233.1 mm = 0.61 / 0.82; 12 in 258.1 mm = 0.68 / 0.90.
- **Further GPU?** No. Measured construction/score mismatch: `dislope` is 75 % of J and the beak
  moves the V plane, not the DI slope. A rescue needs a DI-slope-relevant freedom and a senior
  decision.

### R1 — rolled-rect record + V-beak (`8e86f248fb42`)
- **Route/source.** `name: grid`, rows `canonical_record_v2` on the rolled-rect h12 host, same two
  record freedoms (vt 276.1 mm, hold 0.0063, beak D 6.06 mm). HF1440 yes.
- **Best saved** `20261119T170937Z-screen-ba0f14`, design `d16ae26ca974`, J
  **15.319650131463584** (v10), 30 valid, seed 15.547 -> 0.227 (below floor), 4906 dof.
  Terms: dislope 10.92, diag 17.31, flat 0.853, flat_cv 0.843.
- **Optional whole-family sibling.** `hl__rolled_rect_hybrid_vbeak_v10_v1`
  (`18d3919e93bc`) `20261119T172313Z-screen-081506`, design `96790c88352e`, J
  **9.305393254014847** (v10), 30 valid, seed 15.549 -> **-6.24 J (real, > floor)**; dislope 7.322,
  cov_profile 0.631, flat_cv 0.410. Geometry: inner 575.6 x 344.0, outer 575.7 x 344.0 x 242.3 mm.
  It is still **7.88 J behind** the v10 leader.
- **Same-family other-identity cells** (home-v7, **never** ranked against either v10 number):
  `scout40__rf_rect_axial_cap225` (`2caade374a6c`) `20261119T092938Z-screen-2de348` J 19.7214
  (40 valid); `scout40__rf_rect_axial_control270` (`7b53a3f95cb6`)
  `20261119T094135Z-screen-382cb5` J 19.7063 (40 valid).
- **Tags.** record-level-V-timing | V-lip-beak | rolled-rect-host | returned-lip-fold.
- **Crossover.** V 142.9 / 135.1 / 124.9 / 116.1 deg (hybrid 128.4 / 121.7 / 112.1 / 101.3 deg);
  H 110.7-134.6 deg. Not feasible at any of the four.
- **Driver fit.** 10 in 256.9 mm = 0.67 / 0.90; 12 in 281.9 mm = 0.74 / 0.99.
- **Further GPU?** No — both record-lane mechanisms are measured DI-slope-blind, and the family
  hybrid that *does* move dislope is still 7.9 J off.

---

## 3. What this register cannot say

- **No installed/exterior BEM for any row.** No BL case id is cited, so every claim about an
  assembled horn+woofer, baffle, or cabinet is `NOT_YET_AVAILABLE`. The horn channel in the available
  system cases is an ideal normal-velocity source, not a compression driver
  (`SENIOR_REVIEW_HANDOFF_2026-11-19` section 4, risk R1).
- **No driver frame geometry.** Panel fit and real centre spacing need a maker drawing; the spacing
  above is a moving-diameter lower bound.
- **No 900-1100 Hz scoring exists.** Every lane was scored with the v7 or v10 target, whose V target
  starts at 1 kHz and whose F_X is 700 Hz. Crossover feasibility above is a *screen of stored
  metrics*, not a design objective. See `solver_proposal.md` section 4 for whether a separate brief
  identity is justified.
- **A5 has no valid modern measurement,** and its archived recipe no longer replays.
- **A4's own config has no v7/v10 J,** and the 1.7726 figure belongs to a different derived config.
- **Pareto shortlist** (5 mechanisms, one exploratory) is in `solver_proposal.md` section 5.

---

## 4. Parent amendment (2026-11-19, local orchestrator, [measured])

The CPU v10 gate named as the blocker in solver_proposal.md section 1 is now **resolved**. Runs
re-scored with 	ools/analysis/rescore_identity.py against the shipped v10 brief, all with
mixed_identity: false and only exact_complete rows, into
uns/analysis/v10_priority10_2026-11-19/:

| Row | run | scored/rows | best J (v10) | design | note |
|---|---|---|---|---|---|
| A1 petal (W3) | 20261119T155454Z-screen-d1a61d | 41/55 | **1.9858** | 74d8eed97268 | the same design the proposal would warm-start from |
| A3 tritonia v8 (W3) | 20261119T152446Z-screen-d98c8d | 30/31 | **2.7734** | 295be5854c2 | |
| A2 tritonia v9 (W3) | 20261119T153950Z-screen-5d766f | 30/37 | **2.8813** | 5487ba86a54b | |
| C2 crowe_x_square (W3) | 20261119T161820Z-screen-9fda2a | 10/27 | **4.8193** | e9ab290d3cf | only 10 valid at read time |
| K1 b3_soft | (already in row) | 41 | 3.7428 | 3545b3e078ac | |
| C1 crowe v2a | (already in row) | 40 | 7.0685 | ebde0373489 | |

**Gate decision.** The proposal required the A1 v10 rescore to land within 0.4677 J of the v10 leader
1.4214. It lands at 1.9858 — **0.564 J away, i.e. 0.10 J outside the declared floor**. Therefore the
conditional A1 screen is **not authorised by its own gate**; it stays unspent unless the owner
overrides. For completeness, the v10 slate order is: fold 1.5433 (s1) / 1.4214 (published) < morph
1.5769 / 1.4305 < ext-throat 1.7919 / 1.5710 < **A1 1.9858** < A3 2.7734 < A2 2.8813 < K1 3.5988 < C2
4.8193 (10 valid) < C1 7.0685 < K2 8.3910 < R1 15.320.

No GPU time was spent on any row for this amendment; it is CPU replay only.

## 5. Parent amendment 2 (2026-11-19, local orchestrator, [measured])

Three corrections/supersessions recorded after the owner-decision pass (owner chose "author the
crossover-aware identity first" and "real 10-inch geometry + panel fit first"; no GPU was
authorised or spent).

1. **Frame radius is NO LONGER `NOT_YET_AVAILABLE`.** `frame_od_mm: 261` and `cutout_mm: 232` are
   `[measured]` in `examples/systems/driver_geometry/faitalpro_10pr300.yaml`, so 10-inch frame
   radius = **130.5 mm**. The spacing table above is therefore a conservative lower bound; with
   frame + 10 mm clearance, centre spacing = 130.5 + H/2 + 10 mm (d/λ at 900/1100/1250 Hz in
   `driver_10inch_fit.md`). **Verdict: the real 10PR300 is LEGAL on the recorded 371.2 mm BL front
   only with the 45 cm² port** (required 157.095 mm vs available 175.105 mm, +18.0 mm); the real
   12PR300 stays illegal (−32.0 mm) and the 170 cm² port fails even the 10-inch (−53.4 mm). Port
   area, not driver choice, is the binding lever. Still missing: cone depth, surround width,
   dust-cap diameter, mounting depth — all `NOT_YET_AVAILABLE`; BL still stages its demo cone
   without a maker drawing. Details: `driver_10inch_fit.md`.
2. **A5 re-emit (recipe-drift resolution).** The 2026-11-15 archived recipe is refused by design
   (`rolled_family.py:97-99` schema/digest gate). Current-generator re-emit
   `examples/typologies/compact_2026-11-19/rf__rect_radial_wide_v8_currentgen.yaml` (only `name`
   changed) materialises **541.397 × 298.591 × 238.118 mm** vs the archived saved-mesh
   **541.3 × 298.6 × 238.1 mm** — identical within 0.1 mm on every axis, so the drift is
   **provenance-only, not geometric**. `shape_check` PASS (5096/6000 dof, fits, round driver
   coupling); `search_preflight` ok, no WARN/HARD; `rows_grid_points` round-trip OK. The A5 cell
   now has a scoreable config; still no solved run (`NOT_YET_AVAILABLE`).
3. **The crossover-aware identity now exists and ranks the slate.** Brief
   `examples/briefs/compact_2026-11-19/compact_xo900_1250_hf1440_v10xo.yaml` (objective v10 scalar
   reused unchanged; F_X 850 Hz; H 65-100 / V 40-75 anchored 850-1250; band 350-8000 retained).
   **Floor 0.2783 J** (top-28-pair protocol, 257 pairs; the same command reproduces v10's
   0.4677 exactly). CPU replay ordering: **fold_warm 1.0624 < A3 1.6028 ≈ A1 1.6578 ≈ A2 1.7074 <
   C2 2.4680 < K1 3.4445** (all `exact_complete`, `mixed_identity: false`, SCREEN_MAGNITUDE only,
   no installed/exterior BEM). Read: even under the crossover-aware identity the compact petal/
   tritonia candidates do **not** beat fold_warm (0.540 J, a real separation); A1/A3/A2 tie inside
   the new floor. Full readout: `compact_xo900_identity.md`.
