# Senior review + solve campaign plan — 2026-10-26

Status: **PLAN, owner review pending.** Nothing here has run. It combines the two open handoffs
(ATH CORE / TwinRay Morph pass, uncommitted; the cap-500 brief set + measured VRAM ceiling at
`2d31f1e`) into one run across typologies × briefs, analysed **from 300–500 Hz up to at least
8 kHz**. Its goal is to tune the software (solver economics, search economics, objective,
search boxes), not to crown one horn.

---

## 0. Facts this plan rests on (checked in the tree today)

| Fact | Where | Consequence |
|---|---|---|
| Screen grid is frozen at **500–10 000 Hz, 12 pts**, top clipped to `band_hi_hz` | `config.py:26`, `mode_freqs` | Screens always start at 500 Hz. `band_hi 8000` gives 12 pts over 500–8000. |
| Verify grid is frozen at **300–16 000 Hz, 25 pts**, top clipped to `band_hi_hz`; `grid.verify_points_per_octave` adds HF points above 5 kHz | same | Verify gives the 300 Hz floor. **The owner's 300–500 Hz floor needs no contract change.** |
| One mesh per candidate, sized for the top frequency | `mesh_spec`, `sizing.res_mm_for` | LF points cost as much as the 8 kHz point. The top frequency sets VRAM. |
| Measured 8 kHz ceiling (**old solve path**): safe to ~474 mm / ~5,300 dofs | CONTINUITY 2026-10-26 | Measured without `cuda_fused`. |
| Fused CUDA: **fits 15,984 / fails 20,237, SAFE 12,000 dofs**; same mesh 2,217 vs 7,389 MiB, 9.1 vs 59.6 s/freq | CONTINUITY M2, `FUSED_CUDA_2026-10-24.md` | **This is what makes a 300–400 Hz horn analysable to 8 kHz.** The 8 kHz ladder has not been re-measured on the fused path. |
| **No typology config sets `cuda_fused`**; caps are 5000/7000/8900 | `examples/typologies/*.yaml` | A screen at 8 kHz on a mouth over ~460 mm is refused as `mesh_too_large`. Campaign copies need `cuda_fused: true` and caps of 12000. |
| `lecleach_asym_odd` is a full ring (`'1234'`, ~4× quarter dofs) | its header, line 15 | A `cos φ` term breaks the left-right mirror but **keeps up/down symmetry** (φ→−φ). A half model may be legal → 2× saving. *Verify, don't assume* (see R-7). |
| `salmon_saddle` is a half model (`'14'`) | its mesh block | 2× quarter dofs. |
| Objective v3 masks cov + dislope below `f0_hz` | handoff 2 §1 | A `band_lo` below f0 is analysed but not penalised. This is the honest way to show 300 Hz on a horn that only holds its pattern from 600 Hz. |
| No `target.cov_band_hz` yet | grep | cov is scored to 8 kHz, past f11 for 1.4"/2" drivers. See D-3. |
| Band-split gate **FAILED** (band-0 fidelity) | CONTINUITY M3 | Not used for ranking in this plan. It may be used as a timing experiment only. |

K-law: mouth `d = 25,400,000 / (f0 · coverage_deg)` mm. f11 = 100,250 / r0_mm (1" 7.9 kHz, 1.4" 5.6 kHz, 2" 3.9 kHz).

---

## 1. Phase A — senior code review (no GPU, ~½ day)

Review the uncommitted ATH lane **hunk by hunk**. Stage only its paths. `docs/ISSUES.md` carries another lane's hunk.

| ID | Item | Pass criterion |
|---|---|---|
| R-1 | `families.py` `_MORPH` on R-OSSE/ICW/FREEFORM; removed FREEFORM refusal | No path lets morph keys reach a family whose mesher branch ignores them silently |
| R-2 | `registry.materialize()` morph opt-in | Morph off produces a byte-identical params hash (existing test). Add one test showing that `mouth != ellipse` + morph is refused |
| R-3 | `morph_target` has no `choices` | Add a 0..3 choices guard in `families.validate`. A value of 4 must fail in our layer, not in the mesher |
| R-4 | **CPU mesh-only probes:** R-OSSE and ICW × morph target 1/2/3 × 3 shapes | Every combination meshes or fails with the mesher's own message. Record it in the evidence. Until this passes, R-OSSE/ICW morph stays out of campaigns |
| R-5 | TwinRay rectangle-morph failure | Confirm the cause is the convexity guard, not config (one probe on a circular FREEFORM base with the same rect target). Decision D-5 |
| R-6 | Contract addendum | Decide whether morph-on-all-families gets a dated note. `01_CONTRACTS.md` is frozen, so the note would go in CONTINUITY + `NOTES_FOR_SENIOR.md` |
| R-7 | `lecleach_asym_odd` half-model legality | Check the mesher's `'12'` convention (xz plane) against `cos φ` parity. If legal, mesh `'12'` vs `'1234'` on one seed and compare offline after one GPU pair (≤0.05 dB / ≤1° bar) |
| R-8 | Driver ties for `ath_core` (2") / `ath_twinray_380` (1.4") | Decision D-4 |
| R-9 | Offline gates | `compileall`, `gen_param_catalog --check`, offline suite (1606/0/0/0 expected), `families` on every campaign brief |

Then commit the ATH lane by itself, with CONTINUITY + ISSUES in the same commit (push rule).

---

## 2. Phase B — measure before spending (GPU, ~2–3 h, one job at a time)

1. **Fused 8 kHz ladder.** Reuse `%TEMP%\opencode\pass40\rung_test.py` with `cuda_fused=True`, at quarter mouths of 474 / 550 / 635 / 706 / 800 / 900 / 1058 mm. Record peak VRAM with the baseline, s/freq and dofs. **This sets the PA-LF brief (§3, B3).** Expected: about 700 mm square fits under 12k dofs, and 706×1058 lands at ~17k (fits but above SAFE). Measure it; do not quote these estimates.
2. **Fused 10 kHz probe** at 353 / 403 / 474 mm. This decides whether any brief gets a 10 kHz verify.
3. **epw 5 vs 6** on two stored seeds (one small, one large) at 8 kHz. If the delta is inside the noise floor (0.055 dB / ~1°), epw 5 cuts dofs ~30% for **screens only**. Verify stays at epw 6.
4. **Fused coverage across routes:** one fused seed solve each for a rows typology (`lecleach_rollback`), a half model (`salmon_saddle`), a full ring (`lecleach_asym_odd`) and a generated FREEFORM (`ath_twinray_380`). This shows fused works off the native-OSSE path.
5. **LHS / bound-corner mesh audit (CPU):** 64 LHS points + all 2^k corners (capped at 256) per campaign config, under each brief it will run. Report invalid %, the most frequent failure, and dofs at 8 kHz per point. Widen a box only where a bound is unreachable for a physical reason (`freeform_sculpt` `mouthAngleDeg` 12..35, OSSE `aspect_ratio` 0.45..2.0, both already diagnosed). Never widen a box to make results look good.

Exit: a table of dofs → (VRAM, s/freq) for fused at 8 kHz, invalid rates per config, and a go / no-go for each brief.

---

## 3. Briefs (three owner briefs plus family-native controls)

Every campaign brief: `band_lo_hz: 300`, `band_hi_hz: 8000` (10 000 only where B-2 says it fits), `objective.version: 3` with a K-law `f0_hz`, `grid.verify_points_per_octave: 6`. They go in `examples/briefs/user/` and are created in Phase C.

| ID | Class | Coverage | Driver exit | f0 | Mouth H×V (K-law) | Envelope | 8 kHz dof class | Notes |
|---|---|---|---|---|---|---|---|---|
| **B1 `hifi_90x60_850`** | Hi-fi 90×60 | 90×60 | 1.4" (17.78) | 850 | 332×498 | 360×520×400 | ~6k (fused) | Same physics as `cap500_90x60_850hz_1p4in`, band extended to 300–8000 |
| **B2 `pa_60x40_800`** | Narrower PA | 60×40 | 1" (12.7) | 800 | 529×794 | 540×810×420 | ~10k (fused) | `narrow_60x40_800hz_1in` with fused + 12k caps. The old path was expected to OOM; on fused it should fit. 1" f11 7.9 kHz keeps 8 kHz honest |
| **B3 `pa_lf_400`** | Low-reach PA | **90×60** if B-1 says 17k dofs is usable, else **90×90** | 1.4" (large-format driver, 1.4" exit) | 400 | 706×1058 (or 706×706) | +40 mm shell, depth ≤600 | 12–17k (fused) | Loads to ~400 Hz, analysed from 300. Fallback if neither fits at 8 kHz: 90×60 at f0 500 (564×847, ~11k) |

Family-native controls (they run on their own physics so a family is not penalised for what it isn't):

- `lecleach_90x90_1200hz_1in`, band raised to 300–8000. Le Cleac'h is not constant-directivity, so `dislope: 0`.
- `ath_core_2in` and `ath_twinray_380_14in`, band changed from 500–5500 to 300–8000, still objective v2 unless D-4 changes that. These answer "how good is the published recipe" separately from "how good is it on our brief".

**Do not rank across briefs, objectives, f0 policies or solve groups.** Every leaderboard is per brief.

---

## 4. Typology matrix

Owner emphasis: asymmetric Le Cleac'h, freeform, morph. Plus OSSE references so every brief has a known baseline.

| Group | Typology | Dims | Sym | B1 | B2 | B3 | Native brief | Why / caveat |
|---|---|---:|---|:-:|:-:|:-:|:-:|---|
| Reference | `osse_baseline` (copy: aspect 0.45–2.0, K-law seed) | 10 | q | ● | ● | ● | | Baseline on every brief |
| Reference | `rosse_baseline` | ~8 | q | ● | ● | ● | | Rollback reference |
| Morph | `ath_core` (native OSSE + searched Morph) | 15 | q | ● | ● | ○ | ● | Main morph test. On B3 only if bound audit passes at that size |
| Morph | `osse_baseline` + morph knobs (new copy) | 10+7 | q | ● | ● | | | Shows morph value on the same base — the cleanest A/B |
| Morph | `rosse_baseline` + morph | ~8+7 | q | ● | | | | Only if R-4 passes |
| Freeform | `ath_twinray_380` (generated FREEFORM, superellipse) | 12 | q | ● | ○ | | ● | ~16 s mesh per candidate, so budget by wall time |
| Freeform | `freeform_sculpt` (mouthAngleDeg 12..35 copy) | 11 | q | ● | ● | ● | | Control-point freeform |
| Freeform | `perturbed_osse_hv_fusedcuda` | 18 | q | ● | ● | | | Highest dims; needs a bigger budget |
| Freeform | `freeform_hv` | 3 | q | ● | ● | | | Cheap low-dimensional freeform control |
| Le Cleac'h asym | `lecleach_asym_odd` | ~4 | full (half if R-7) | ○ | | | ● | Full ring: about 4× dofs, so 8 kHz caps the mouth at ~350 mm even on fused → only the native brief and B1 at most |
| Le Cleac'h asym | `lecleach_iwata_ar` | ~5 | q | ● | ● | | ● | Area-preserving AR. Quarter, so cheap |
| Le Cleac'h | `lecleach_rollback`, `lecleach_toroidal` | 3–4 | q | ○ | | ● | ● | Rows march is slow. B3 is their natural home (low fc) |
| Asym rows | `salmon_saddle` (half) | ~6 | half | ● | ○ | | | Up/down asymmetric |
| Hybrid | `hyb_osse_h_tractrix_v`, `biradial_keele` | ~6 | q | ● | ● | ○ | | Classic PA shapes |

● = run, ○ = run if Phase B says it fits. About 30 cells.

---

## 5. Phase C — staged execution

Run one GPU job at a time. Before every job: `gpu-clean`, check that `runs\.gpu.lock` is free, record the baseline from `nvidia-smi`, and **close the GUI** (it holds 350–500 MB). Every campaign config is a copy under `examples/typologies/campaign_2026-10-26/` with `cuda_fused: true`, caps of 12000/12000/12000 (or the Phase B value), and a K-law-consistent seed checked with `preview_shape`. Use a fresh run directory per cell; no resumes across box changes.

| Tier | What | Budget per cell | Exit |
|---|---|---|---|
| **T0 seed** | 1 seed solve per cell | 1 | Seed J, dofs, s/candidate. Kill any cell whose seed is refused or saturated |
| **T1 screen** | CMA, `sigma0 0.15`, seed 1234 | `max(100, 12·dims)` (CORE 180, perturbed 216) | J vs eval curve, invalid %, best 5 |
| **T2 deepen** | Top 3 cells per brief: 2nd seed (4321) + `budget = 25·dims` | ≤400 | Seed-to-seed spread, which is the noise floor for "family A beats B" |
| **T3 verify** | Top 5 per cell from T1/T2 at the 25-pt 300–8000 grid + HF ppo 6, balloon 1024 | 5 runs | Ranking must survive verify (Spearman vs screen) |
| **T4 final** | The best 2 per brief at the final grid, top clipped at 8 kHz (10 kHz where B-2 allows) | 2 runs | Owner-facing numbers |

Remember: failures are not cached, and `--budget` counts per invocation. Count evaluations from the ndjson, not from the flag.

Rough wall time, to be replaced by the Phase B measurement: small quarter horns (~3–6k dofs) ~2 s/freq → ~30 s/candidate; B2/B3 (10–17k) ~6–10 s/freq → 75–120 s/candidate. T1 across ~30 cells ≈ **35–50 GPU-hours**. Run overnight in brief order B1 → B2 → B3.

---

## 6. Decisions the owner must make before Phase C

| ID | Decision | Recommendation |
|---|---|---|
| D-1 | B3 shape: 90×60 at 400 Hz (17k dofs, above SAFE) or 90×90 at 400 Hz | Let Phase B decide. Prefer 90×60 if it is stable over 3 repeat solves |
| D-2 | epw 5 for screens | Only if B-3 is inside the noise floor |
| D-3 | Add `target.cov_band_hz` before the campaign | **Yes.** Small change in `targets/spec.py` + `scalar_v2.py`. Score cov from f0 to ~f11 or 6 kHz and everything else to 8 kHz. Without it, 1.4"/2" drivers are judged on geometry they cannot excite |
| D-4 | ATH entries: driver ties, f0 + v3 | Tie them to their drivers in the catalog. On B1/B2 they run as configs retargeted to the brief driver, with that fact labelled |
| D-5 | TwinRay: accept superellipse or fund a mesher-guard fork | Accept for this campaign; a fork is Phase E |
| D-6 | Morph target/exponent: searched or staged | Stage it: run T1 with `morph_target` pinned to 1 and 3 as two cells, not one rounded integer gene |

---

## 7. What we expect to learn (the tuning output)

1. **Solver economics:** a fused dofs→VRAM/time curve at 8 kHz, new safe caps per mode, the epw 5 verdict, and the half-model saving for asymmetric Le Cleac'h.
2. **Search economics:** J-vs-evaluation curves by dimension count → a rule for budget per dimension. Seed spread → the minimum meaningful J gap. Invalid rate per config → box fixes.
3. **Objective:** screen→verify rank stability, the effect of `cov_band_hz`, and whether v3's f0 mask keeps 300–500 Hz honest.
4. **Shape:** does Morph beat the same base without Morph (A/B on `osse_baseline`)? Does freeform beat OSSE at a matched budget? Where do asymmetric Le Cleac'h shapes help, and at what cost?
5. **Product:** best 2 per brief at the final grid, with f11 and above-f11 disclosure.

## 8. Phase D — reporting

- `docs/evidence/CAMPAIGN_2026-10-26.md`: per-brief leaderboards, curves, the Phase B tables, every refusal and OOM listed with its reproduction.
- A byte-check script for quoted numbers (ATH handoff item 10).
- CONTINUITY + ISSUES updated in the same commit as every push.

## 9. Out of scope

Multi-entry horns (Synergy/MEH; deferred). Band-split ranking (gate failed). Exact CORE `a(φ)`, `Mesh.Roundover`, rear enclosure (Phase E). A main/PR merge (owner has not asked).
