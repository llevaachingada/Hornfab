# Orchestrator verification notes — SOLVE_CAMPAIGN_PLAN_2026-10-26 hardening

All findings below are [measured] by direct CLI/code execution on the working tree unless marked
otherwise. Scratch: `_orch/` dry-run artifacts. Interpreter: repo venv.

## LANES RETURNED (updated as they land)

### Lane B — Salmon/X-shape rows (DONE; full report scratchpad/audit_salmon/REPORT.md)
- **Shared invariant is wrong for salmon** [measured]: the repo's `_ROWS_MOUTH_FC_INVARIANT = 1.88e5`
  (config.py:859) matches the EXACT/Fourcade march (1.47e5@90°, 1.71e5@120°, ~1.87e5 above 150°) and
  Lane A's lecleach measurements — but the SALMON rows march satisfies mouth×fc ≈ 3.23e5 at stop 150
  (2.57e5@120, 3.65e5@170). So the derivation applied to salmon targets lands seeds ~1.7× too big in
  mouth / f0 ~1.7× too high. This is a per-family constant bug, not two lanes disagreeing:
  Lane A's 1.88e5 = lecleach; Lane B's 3.23e5 = salmon rows at stop 150.
- **All four campaign briefs derive the SAME square seed on the salmon route** (fc_h=fc_v=600, both
  axes clamped low) → the H/V aspect mechanism is destroyed at seed. fc lo 600 blocks B2 V-40 (392),
  B3b V-60 (441), B3a both (441); fc hi 1200 blocks the organic 1"/1.4" rim shrink (~1,450/1,370 needed).
- **stop_hi 240 is 43% duplicated** (190≡170, 230≡130, 240≡120 [measured]) with depth explosion near
  180 (179.9 → L=913 mm). Recommend hi ≤ 170.
- **ripple free-lobes is a trap**: 16/16 LHS refused (non-integer + ph sample guard) — pin lobes 12,
  search amp [2,6]/start [0.75,0.92]. 12-lobe arc ~70 mm vs 7.15 mm mesh res (visible).
- **x_amp bound ±0.4 is unusable**: |x_amp| > 180/stop−1 crosses 180° → 5-15 s meshes, envelope fails.
  Campaign ±0.18 @stop150 / ±0.28 @stop130. x_signed has high envelope-refusal rates (24-41% even in
  recommended boxes) [measured].
- **CD brief fairness**: B1/B2/B3a use load 0 on a loading family — only B3b scores loading.
  X-horn's defining diagonal behaviour is INVISIBLE to an H/V-only brief; needs a 45/135° diagonal
  term + diagonal envelope check (AudioHorn: "diagonal measurement ... as perfect as the horizontal
  one" [S: audiohorn.net/x-shape-horn, cross-wavefront-syndrome]). Commercial X-shape rims
  271-380×10³ mm·Hz and JMLC-350 = 309×10³ (595 mm × 520 Hz) [web-fetched] — consistent with
  Lane B's rows number, NOT with 1.88e5.
- Compatibility (recommended seeds, dofs @8k): elliptical RUN all four (2,590-6,848; B2/B3a "edge");
  x_signed RUN-CHG B1/B2/B3b (3,427-8,544); x_shape/saddle/ripple12 NO on B1/B2/B3a/B3b
  (saddle B3a = 28k tris/14k dofs/22.7 s); spherical NO (axisym, fc floor).
- Physical floors (not bounds): fc_min·r0 = K(T) (1": fc400 only at T=1); self-approach 2t+2 = 8 mm
  knife-edge (x_shape seed refused at 7.997). Salmon is a LOADING family — fc-defined briefs or
  B3b-style loading briefs; CD coverage briefs distort it.

### Lane A — Le Cleac'h family (DONE; full report scratchpad/audit_lecleach/REPORT.md, 34.5 KB)
- **The f0 derivation itself over-constrains JMLC**: it derives ONE fc from the geometric mean of the
  K-law mouth (the `g_fc_hz` rule at config.py:1007), then clamps to shipped bounds [600,1200]
  (rollback/toroidal/asym) or [800,1200] (iwata). All four briefs derive BELOW those floors
  (B1 462, B2 290, B3a 266, B3b 326) → every shipped JMLC seed is silently a 313 mm round horn, not
  the brief's mouth. [measured] Fix: widen g_fc_hz floors per brief (B1 [430,520], B2 [268,295] @1.4",
  B3a [268,320], B3b [310,340]) — or use per-axis fc_h/fc_v / the narrow axis instead of the
  geometric mean (the geo-mean fc rule is a repo invention, Lane A risk #6).
- **H/V orientation conflict (Lane A risk #1, needs owner ruling)**: the campaign briefs are TALL
  (H>W, AR 0.667: 332x498, 529x794, 470x706). Every commercial JMLC/IWATA is WIDE (AR 1.84-2.79), and
  iwata_ar's shipped AR bounds [1.2,2.8] block B1/B2/B3b outright. Either the briefs swap H/V vs the
  repo's convention (`config.py:1046-1047` defines W←coverage_h) or JMLC must search AR<1. Confirm
  before campaign; Lane D measured the same 0.667 requirement from the brief side.
- **JMLC fc is a loading corner, not a pattern corner**: measured W·fc ≈ 1.88e5 mm·Hz at stop ≥170
  (mouth ≈ 0.55 λ at fc); pattern control starts ~1.8× fc. Vendor "min frequency" ≈ 1.5× model
  number (JMLC-350→520 Hz, JMLC-400→600, JMLC-600→900, JMLC-200T→300, IWATA-300→450) [web-fetched,
  Auto-Tech datasheets + sphericalhorns calculator + Fourcade 2015 PDF]. So a 90x60-at-850 coverage
  brief mis-specifies the family; loading-scored briefs (B3b-style) or fc-defined briefs are its
  natural home → **dislope must be 0 on every JMLC brief; cov 0.3-0.5; load 0.5 / z_min 0.5-0.7**.
- **Half-model verdict for lecleach_asym_odd**: geometrically LEGAL (r* = 1+eps·w(s)·cosφ is exactly
  even in φ; measured up/down mirror error 1.13e-13 mm; both seam rows lie on y=0) but
  implementation-ILLEGAL today: `lecleach_asym` refuses `span: half`, and `_GRID_SYMMETRY_AXES` has no
  '12'. Needs `span: half_xz` + '12' + one half-vs-full test. Saves 2x on B3b/native; does NOT rescue
  B3a-asym (~28k → ~14k dofs, still >12k — asym stays OFF B3a at 8 kHz).
- **Asym dofs are brutal at 8 kHz**: full-ring asym at 620 mm = 22,444 dofs [measured]; ~28k at 694.
  Asym is a B1-at-most/B3b-with-half-model family, not a B3 family.
- Measured campaign-ready seeds: B1 iwata_ar → 331×495×223, 2,612 dofs; B2 iwata_ar **1.4" only** →
  525×786×421, 6,378; B3a rollback 268/T1/170 → 694×694×472, 7,241 (90° held to ~407 Hz); B3b iwata_ar
  → 467×699×355, 5,064 (1.3% over the 5k cap; raise cap); native rollback → 931 dofs.
- Failure regions [measured]: 1" fc≤350 any T refused; 1.4" T=0.5 refuses fc<~480; rollback native
  LHS 23.5% mesh-refused; rollback B3b 52.9% envelope-over at fc below the 500 mm rule.
- Confirms my F7 cosφ symmetry reasoning with measurement (1.1e-13 mm mirror error).

### Lane C — ATH / Morph / FREEFORM (DONE; full report scratchpad/audit_ath/REPORT.md)
- **R-OSSE + pinned native morph is the ANSWER to B-3** [measured]: with `wall_thickness_mm: 5` explicit,
  R-OSSE+morph seeds reach all four briefs: B1 3,557 / B2 9,687 / B3a 7,468 / B3b 6,611 dofs,
  17/17 meshes passed (targets 1/2/3, R 155 and R 397, wall 5.0 and 2.5, incl. 529x794). The base
  rosse config omits wall thickness → the mesher's 6 mm default caused the earlier self-intersection
  failures, NOT the morph. ICW morph also mesh-proven 6/6 at 529x794 (cosmetic outer-wall warning
  only). **R-4 gate PASSES.**
- `ath_core` cannot serve 90x60 (r0 25.4 pin refuses B1-B3b; a_deg hi 32, aspect pinned 1.0). A patched
  `ath_core_14in` (r0 17.78, a 42-48, L 320-380, morph 680-730) serves B3a: 9,851 dofs, 706x706x451
  [measured]. `ath_twinray_380` cannot scale: L hi 240 caps the mouth at 494x399 → own brief only;
  mesh 3.4-28.2 s/candidate [measured].
- `perturbed_osse_hv`: corner hi 60 → 24-41% mesh refusals (corner 5-45, u ±0.15); own 1in hifi only.
  `freeform_sculpt`: radius hi 200 / mouthAngle hi 70 blocks narrow patterns; 90x90 cell only.
- **Morph gene verdict [measured]**: rounded-int CMA gene is a discontinuous categorical (sigma0 0.25
  flips seed target 15.8% of steps; uniform bounds 50/25/25). **Pin target per cell** (`search: false`):
  target 1 for rectangular PA mouths, 3 as a second cell, 2 only circular-with-shrinkage. Target 2 uses
  max(half_w, half_h) → turns 2:1 targets into circles of the long dimension.
- **B1 portrait over-constrains single-`a` OSSE/R-OSSE** (matches Lane A H/V + Lane D B-3): nominal H
  ~42 deg on B1. Needs FREEFORM per-plane depth or an envelope change; one BEM verify seed before the
  campaign (coverage unproven on portrait morph targets).
- OSSE+morph: B2 clean (5,100-8,885), B3b usable (8/18 LHS), B1 half envelope-fail, B3a EDGE
  (7,982-17,493 — straddles the 12k safe line). Morph shrink with `fixed > 0` breaches the envelope
  upstream (B3b widths 554-857 from a 490 target) → fixed 0-0.1 or allow_shrinkage 0.
- Risks: missing wall_thickness silently becomes 6 mm (set 5 in R-OSSE/ICW copies); the f0 derivation
  leaves L fixed (not an envelope solver — derive L or flag unreachable mouths at L hi).

### Lane D — reference/hybrid + objective mechanics (DONE; full report scratchpad/audit_ref/REPORT.md)
- **aspect_ratio is WHOLE-HORN W/H, throat included** (`families.py:66`; `profile_sampling.py:481-487,860`).
  Shipped box [1.0,2.0] forces W>H; B1/B2/B3b need W/H = 0.667 → **structurally impossible for native
  OSSE/R-OSSE/ICW; only B3a (square) compatible**. Lowering ar below 1 shrinks the throat to ~11.9 mm
  (wrong fix; FREEFORM's `crossSections circle→ellipse` route is the correct construction).
- **Native seeds measured under briefs** (no derivation, confirms F1): osse 802×642×266 mm over B1/B3a/B3b
  (overshoot 1.23/0.08/0.60); rosse 412×310 under B2; icw 300×300 everywhere.
- **ICW's driver pin is silently MISSED**: r0 nested at `icw_seed.r0_mm` so `config.py:600` pin check never
  fires → ICW ignores the brief's driver entirely (a fairness bug, the inverse of F2's hard refusal).
- **Only biradial_keele derives K-law-exact seeds** (B2/B3a/B3b measured 529.2×793.8 / 705.6×705.6 /
  470.6×705.6, 0 overshoot). B1×biradial is a HARD REFUSAL at seed load (closure needs W 368.6 > 360
  envelope). Fix: envelope W ≥ 375 or L ≤ 185.
- **`widened_to_closure` is misnamed** — under B2/B3a/B3b the widening is K-law-driven (v_rm 230→396.9,
  h_rm 210→352.8) [measured]; S1A doc line 1257's claim is false.
- **z IS reported on fused CUDA** (`impedance_for_radiators` BeatEngineDriver.jl:1311-1336,2042 emitted
  :2138; `solve/beat.py:321-333`) → B3b's load term is NOT a silent no-op on the fused path (upgrades my
  F4 caveat). BUT `z_min 0.5` is below the repo's own "loaded" threshold 0.7 (`evaluate.py:273`) → raise
  to 0.7 and use verify-only evidence; the load mean over the full band also dilutes "loads to 400 Hz".
- **Screen↔verify J not a clean delta** [measured demo]: sub-500 ripple affects verify J by −6.90 and
  screen J by 0.0000 (screen never solves below 500; `on_axis` ref is the band mean,
  `metrics/compute.py:104-115`). Verify grid is effectively 29 pts with ppo 6 (not 25): incl. 300/344/394/452.
- **n_in_band is actually the cov-score count** (`scalar_v2.py:377`; screen 9 / verify 21 for B1); B1's
  first cov-scored point is 1065 Hz, not 850 (the mask acts on grid points).
- **f11 = 7,914 / 5,653 / 3,957 Hz** for 1/1.4/2 in; objective has NO f11 treatment (report-only);
  at 8 kHz, 2/12 screen points are unusable for 1.4", 5/12 for 2". `cov_band_hz` fixes it via
  `min(f11, band_hi)`.
- **cov_band_hz minimal design** (from Lane D, no implementation): `targets/spec.py` add
  `cov_band_hz: tuple|None = None` after f0_hz (positional-consumption constraint: `report/html.py:453`);
  validate 0<lo<hi inside band; `scalar_v2.py::_objective_v3` build `cov_score = score & (f in cov_band)`
  for the cov block only; provenance: config_sha covers it, solve-cache unaffected, but the in-run/resume
  memo key (`evaluate.py:660-667`) and GUI compare fingerprint (`gui/data.py:620-627`) need extension;
  CONTRACTS §11 is frozen → dated owner amendment; test list included.
- **Compatibility matrix (Lane D, dofs @8 kHz quarter epw6)**: biradial_keele ✓ B2 (~5,000) ✓ B3a
  (~6,103) ✓ B3b (~4,375) but ✗ B1; rosse ✓ B2 (9,710); osse ✓ B3a (8,453) only; icw/hyb_tractrix/qtw
  ✗ everywhere (mouth ceiling 0.32-0.57× of requirement); hyb_hypex ✓ all four with widened v_rm/L.
  **Probe failure rates are NOT the blocker** — hypex/qtw/icw sample cleanly but can never reach the
  required mouth: `cov` unsatisfiable by construction.
- Recommended epw 6 for the fused campaign (biradial was 8; halves dofs).

## F1 — Native families get NO f0 seed derivation (measured)
`config.py::_derive_generator_geometry` (L878-1022) only handles `generator` blocks of kind
`typology` and `grid`. Native families (OSSE/R-OSSE/ICW/FREEFORM) land in the else branch:
"no generator block (formula/native family): feasibility recorded; derivation lands with the
baseline-settings pass".

**Measured:** `osse_baseline` (caps raised to 12000, same seed otherwise) dry-runs under B1 and
B3a produce the IDENTICAL mesh: 15,524 tris / 7,921 dofs, bbox (0.4011, 0.3209, 0.26) m. The
horn does not respond to the brief at all.

Consequences for the plan:
- B1 ~6k dofs claim is wrong for the shipped osse_baseline seed: measured 7,921 dofs, bbox
  401x321 mm wide — OUTSIDE B1's 360x520 envelope.
- B3a (needs ~706 mm) same 401 mm seed — the seed doesn't even point at the brief.
- Campaign must hand-author per-brief seeds/bounds for every native config (osse/rosse/icw/
  ath_core/freeform), or extend the derivation. Plan does not mention this.

## F2 — Driver-pin refusals block cross-driver cells (measured)
`config.py::539` `_PIN_FAMILIES = ("OSSE", "R-OSSE", "ICW")`; `_force_pin` (L543+) raises
ConfigError when a pinned bounds.r0_mm disagrees with the brief driver by >0.01 mm.

**Measured refusals:**
- `osse_baseline` (pinned 17.78) + B2 brief (12.7) -> run FAILED ConfigError.
- `ath_core` (pinned 25.4) + B1 (17.78) -> run FAILED ConfigError.
- `rosse_baseline` (pinned 12.7) + B1 (17.78) -> run FAILED ConfigError.

So the plan's matrix cells like `osse_baseline ● B2`, `ath_core ● B1/B2`, `rosse_baseline ● B1`
are infeasible as written. Fix: per-brief campaign copies must re-pin r0 to the brief's driver
(the error message itself says "rescale the horn explicitly or drop the pin"). Rows/salmon and
generator typologies are not affected (r0 arrives via the config's own generator args).

## F3 — band_lo_hz is inert for the frequency grids (measured)
`config.py::768-780 mode_freqs` clips ONLY the top: `hi = min(FREQ_GRIDS[mode][1], band_hi_hz)`.
`band_lo_hz` never clips the bottom; it is used only in the objective band mask
(`scalar_v2.py:299`: `band = (f >= band_lo_hz) & (f <= band_hi_hz)`).

Measured grids at band_hi 8000 (points listed from the repo's own geom):
- screen: 12 pts, 500 → 8000: 500, 643, 828, 1065, 1370, 1763, 2269, 2919, 3756, 4832, 6218, 8000.
- verify: 25 pts, 300 → 8000: 300, 344, 394, 452, 519, 595, 682, 782, 896, 1028, 1178, 1351,
  1549, 1776, 2037, 2335, 2678, 3070, 3520, 4037, 4628, 5307, 6085, 6977, 8000 (+ ppo-6 tail
  between 5k and 8k per HF_VERIFY_LO_HZ).
- final: 36 pts, 250 → 8000 (250, 276, 305, 337, 372, 410, 453, 500, ...). FINAL STARTS AT 250 Hz
  — below the declared 300 Hz floor (scored no: band mask excludes 250/276; solved yes).

Below-f0 point counts [measured] (screen/verify/final): f0=850 -> 3/8/13; 800 -> 2/8/12;
600 -> 1/6/9; 400 -> 0/3/5.

Hardening implications:
- Screen J and verify J are different functionals (different frequency sets, screen never
  samples below 500). The plan's "ranking must survive verify (Spearman vs screen)" gate is
  comparing two different score definitions; treat rank shifts as partly definitional.
- "300-8000 analysed" is only true in verify. Final mode solves 250-300 Hz (unscored).
- band_lo does nothing else; any plan text implying a 300 Hz screen floor is wrong.

## F4 — v3 masking confirmed, with a B3b caveat (measured from code)
`objective/scalar_v2.py::_objective_v3`: f0 = target.f0_hz (falls back to band_lo); cov + dislope
score only `f >= f0` (L309-332); rip/di/flat/load score the full band (L357-358). Confirms the
plan's line 23.
- `load` term (`terms.py::92-98`): `mean_f(max(0, z_min - Re z_throat))`; skipped (0.0) when
  Response reports no z (`z_throat is None`). So B3b (load 0.5, z_min 0.5) is a NO-OP if the
  fused path doesn't populate `resp.z_throat`. `metrics/compute.py:118` builds z_real from
  `resp.z_throat`; whether `beat_cuda` fused returns it must be verified before B3b counts.
- z normalization: `rho*c` specific impedance (plane wave = 1) — `metrics/impedance.py`.

## F5 — B2/B3 dof estimates vs measured fit ceiling
Measured fused CUDA: fits 15,984 / fails 20,237 dofs; SAFE 12,000 (CONTINUITY). The old-path
8 kHz ladder: 474 mm -> 10,402 tris (~5,300 dofs). Plan's estimates (~10k B2, ~17k B3 706x1058)
are consistent with area scaling from that ladder, BUT 17k is ABOVE the highest verified-fit
point (15,984): the plan line 53 "706×1058 lands at ~17k (fits but above SAFE)" presents
"fits" as known — it is NOT measured on fused. Phase B must treat >15,984 as unproven.

Measured local data point: the 401 mm osse_baseline seed at 8 kHz costs 15,524 tris / 7,921 dofs
on the old path (dry-run). Scaling to B2 (~529x794) ~2x area vs 401-mean-~350? — consistent with
plan's ~10k.

## F6 — GPU-hour budget is internally inconsistent
Plan's own numbers: B2/B3 candidates 75-120 s/candidate at 10-17k dofs; T1 = max(100, 12·dims)
evals (~120-216, avg ~150). ~20 of ~30 cells are B2/B3-sized. 20 cells × 150 × ~95 s =
~79 GPU-h for T1 alone [derived from plan's own inputs]; plus T2 (top-3 × 25·dims), T3 (45
verify runs), T4 (6 runs). Total is plausibly 100-130 GPU-h, not 35-50. The 35-50 h figure only
holds if every cell behaves like the small-tier (~30 s/candidate) case. Resolve by measuring
fused s/candidate at 10k and 17k dofs in Phase B before committing.

## F7 — lecleach_asym_odd half model '12' looks legal (geometry argument)
Quadrant map [measured]: `QUADRANT_FACTOR {"1234":1,"12":2,"14":2,"1":4}`,
`SYMMETRY_PLANE {"12":"xz","14":"yz"}` (mesh/sizing.py:16-17). The asym term is
r(phi,s) *= 1 + eps_m·w(s)·cos(phi) with w(s) a smoothstep in arc fraction independent of phi.
cos(phi) is even in phi, so the surface is mirror-symmetric across the xz plane (the '12'
plane) and C1 at the seam (dr/dphi = -eps·w·sin(phi) matches across phi=±90°). The asymmetry
is x->-x only. A '12' half model with span: half + odd n_phi should be legal -> 2x dof saving.
Still needs the repo-convention check (Lane A) + one CPU mesh comparison; verdict from Lane A
supersedes this reasoning if it finds a phi-convention mismatch.

## F8 — Campaign brief drafts cross-checked (measured against K-law)
- B1 332x498 @850 (0.276λ/0.414λ) inside envelope 360x520 [consistent].
- B2 529x794 @800 (0.316λ/0.474λ) inside envelope 560x830 [consistent].
- B3a 706x706 @400 90x90 (0.38λ) inside envelope 740x740x650 [consistent].
- B3b f0 600 90x60: K-law 470.4x705.6; envelope 500x740x600 OK. weights.load 0.5, z_min 0.5
  present in the draft. NOTE: all four drafts carry `di_slope_target: 0.0` — for B3b/Le Cleac'h
  the "is dislope 0?" question is live (Lane A) and for non-CD families dislope weight 0.5
  against a flat-DI target may distort the search.
- All drafts: `objective.version: 3`, band 300-8000, verify ppo 6, cov 1.0 rip 1.0 di 0.3
  dislope 0.5 flat 0.5.

## F9 — Lane E web-research highlights (from scratchpad/research_web/REPORT.md, all with URLs)
- B2 as drafted is NOT credible: real 60x40 PA horns are 210x210 (1") to 270x270 holding 60x40
  only to 1.2-1.6 kHz; a 1-inch driver at 800 Hz is not credible (BMS 5530ND rated 1.0 kHz
  minimum); recommend B2 at f0 1.2 kHz or 1.4"/2" driver.
- "1.4 inch" is not one dimension (35 mm vs 36 mm); exit half-angles: 1in 5-6°, 1.4in 2-3°,
  2in 0-1.2°. The drafts pin 5 deg for 1.4" — too fast per AudioHorn/ATH practice.
- 300-400 Hz loading needs a two-way/annular driver family (BMS 4592/4594, Axi2050), not just
  large diaphragm (DE1050/ND4020Ti2 rated 800 Hz).
- K-law = λ/(2 sin(θ/2)) × 1.16-1.29; manufacturers' "cutoff" ratings sit 1.3-2x below true
  pattern control. Loading point (ATH 20% Re convention) ≈ perimeter 1.9-2.6 λ.
- Le Cleac'h is fc-defined, not coverage-defined — "honestly which briefs" leans to B1-as-hi-fi
  and B3-loading; dislope 0 is defensible.

## Open items waiting on lanes
- Lane A: half-model verdict + lecleach bounds + whether dislope 0 recommended.
- Lane B: salmon rows bounds + mesh time; whether CD coverage brief is fair for X-shapes.
- Lane C: R-OSSE/ICW morph mesh-proof verdict; morph gene design.
- Lane D: Part 2 mechanics (a-e) with file:line; cov_band_hz design; z reporting by fused path
  (cross-checks F4).
- Oracle (parked until all others return): rank/statistics validity, comparability, risk list.