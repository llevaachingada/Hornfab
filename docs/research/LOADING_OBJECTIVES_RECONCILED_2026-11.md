# Loading objectives reconciled: v4 `load`, v6 `load_near`/`z_smooth`, v7 `load` — one glossary, one decided split

2026-11-12, lane L3 (scoring truth). Purpose: every loading-ish term that exists in
`hornlab_search/objective/` today, defined exactly from the code (file:line), in plain language,
then what the two research reports said, the **decided** recommendation, and the diff an owner
would have to approve to ever merge the versions. Read-only research; no term definition changed.

The three terms share one physical quantity — the normalised specific throat resistance
`Re(z_throat) = Re(Z)/rho·c`, stored per solved frequency as `metrics.z_throat_real` — and differ
in WHERE and HOW they charge a deficit against it.

---

## 1. Exact definitions (from the code, file:line)

### 1.1 v4 `load` — `hornlab_search/objective/terms.py::load_term` (terms.py:92-98)

```
load_term(z_real, target) -> mean_f( maximum(0, target.z_min - Re z) )      # raw
```

Normalized by the brief's `load` tolerance and weighted by the brief's `load` weight
(`terms.py:22-30` contract order, `DEFAULT_WEIGHTS["load"] = 0.0`; the v4 normalisation
`term / tol` lives in `objective/scalar_v4.py`, reused by v7 at `scalar_v7.py:499`).

Plain description:
- Over every in-band solved frequency, take how far `Re z` sits BELOW the target's `z_min`
  threshold (a one-sided hinge; above the threshold costs nothing).
- Average those deficits over the whole band (plain mean, or the target's `freq_weights`),
  so a deep sub-cutoff dead zone is diluted by every well-loaded HF point.
- If the solve carried no throat impedance at all, the term is skipped (0.0); if every in-band
  sample is NaN it returns `NAN_TERM_FILL = 30.0` (`terms.py:38-46, 92-98`).

### 1.2 v6 `load_near` — `hornlab_search/objective/scalar_v6.py::load_near_term` (scalar_v6.py:201-226)

```
window = band ∩ [band_lo, f_load_hi],  f_load_hi = max(F_X_eff, load_alpha · fc_hz)   # fc default 1.0
hinge = freq-weighted mean over the window of max(0, z_min - Re z)          # missing z → NAN_TERM_FILL
soft  = max(0, (f_loaded - f0)/f0) when scalars carry f_loaded_hz/f_load_hz, else 0
load_near_raw = hinge + soft
```

`fc_hz` is resolved `objective.fc_hz → metrics.scalars['fc_hz'|'g_fc_hz'] → target.f0 → band_lo`
(`resolve_fc_hz`, scalar_v6.py:165-179); `F_X_eff = target.f0_effective_hz()`
(scalar_v6.py:204-205).

Plain description:
- Scores the loading deficit ONLY near the loading corner: the mean hinge is computed on
  `[band_lo, max(f0, alpha·fc)]`, so a dead low end can no longer hide among loaded HF points —
  the integral-style aggregator `docs/research/SIM_VS_REAL_HORN_2026-10-27.md` §3 asked for.
- Adds a soft penalty for HOW FAR above `f0` the throat first stays loaded
  (`max(0, (f_loaded - f0)/f0)`), taken from the solve's `f_loaded_hz` scalar when present
  (it is not in the dataset rows, so it contributes 0 there).
- No `Re z` plateau criterion and no crossover-frequency term: what is averaged is exactly the
  same hinge deficit as v4, only over a corner-limited window.

### 1.3 v6 `z_smooth` — `hornlab_search/objective/scalar_v6.py::_z_smooth_term` (scalar_v6.py:229-238)

```
z_smooth_raw = std( Re z )  over  band ∩ (f >= f0_effective), finite samples, need >= 2
```

Plain description:
- Measures the WIGGLE of the throat resistance above the loading corner: the population standard
  deviation of `Re z` over the in-band, at-or-above-f0 solved samples.
- It is a mouth-reflectance proxy: a rolled-back / low-reflectance mouth (Le Cléac'th's virtue)
  shows as a smooth, slow rise in `Re z`, while a hard mouth edge bounces standing waves into it.
- Fewer than two finite samples returns `NAN_TERM_FILL`; none at all → 0.0; the term has no
  hinge — it charges ripple even when the horn is fully loaded (that is the point).

### 1.4 v7 `load` (combined C1) — `hornlab_search/objective/scalar_v7.py::_load_v7` (scalar_v7.py:289-326)

```
F_X = target.f0_effective_hz()
loaded window = [F_X, min(band_hi, f11)],  f11 resolved (owner 2026-10-29 precedence,
scalar_v7.py:268-286): target.loaded_hi_hz → DRIVER-EXIT cross-mode
BESSEL_J1P_11·c/(2π·a) from target.driver_exit_radius_mm (scalar_v7.py:257-265)
→ metrics.scalars['f11_hz'] (main throat) → none (window ends at band_hi)

LFP20 = first ascending log2-f crossing of Re z through lfp_re_z (0.20), linear in z between
        the bracketing solved samples (_first_crossing_hz, scalar_v7.py:214-239)
LFP50 = the same crossing through 0.50 (scalar_v7.py:314, diagnostic only at scalar_v7.py:82)
lfp_pen = max(0, log2(LFP20 · lfp_crossover_ratio / F_X))                    # ratio default 1.6
rez_pen = max(0, loaded_re_z - min Re z over the loaded window)              # loaded_re_z 0.50
load_raw = lfp_pen + rez_pen
```

Plain description:
- First asks WHEN the throat starts loading: `LFP20` is the lowest frequency where `Re z`
  crosses 0.20 from below; the design is penalised in octaves while `LFP20 × 1.6` sits above the
  band's control corner `F_X` — i.e. you pay for reaching the crossover with an unloaded throat.
- Then asks HOW WELL it stays loaded: `min(Re z)` over `[F_X, min(band_hi, f11)]` must reach the
  0.50 plateau, the deficit charged linearly — the same hinge idea as v4/v6 but with the mean
  replaced by the MINIMUM, so no in-band dip can be averaged away, and the window stops at the
  driver-exit cross-mode `f11` (above it the uniform-velocity source is an idealised rigid cap).
- Unmeasurable states (no z, no sample in the loaded window, no crossing below the highest
  solved frequency, non-finite result) return `NAN_TERM_FILL`, never NaN/inf
  (scalar_v7.py:294, 309-310, 319-320, 324); `LFP20` at the grid start is an explicit upper
  bound (scalar_v7.py:230-231). This is also the `gate_loading` definition in
  `tools/rescore/gate_audit.py:302-374` — gate and objective agree.

---

## 2. What the research said

### 2.1 `docs/research/SIM_VS_REAL_HORN_2026-10-27.md`

- §1: ideal-source BEM is a good **relative-ranking tool for pattern shape above cutoff**;
  it cannot predict level, efficiency, LF loading, cutoff peaks or distortion, and on-axis
  normalisation hides exactly that gap.
- §3: the shape of v4 `load` (one-sided hinge) is right, but the **band-mean aggregation dilutes
  a deep sub-cutoff deficit** among many loaded points; the recommendation was an integral /
  max / sub-f0-integral form scored near the corner, plus a per-class weight table
  (CD 0.3-0.5 @ z_min 0.5; PA-to-500 Hz 0.8-1.0 @ 0.7; low-reach 1.0 @ 0.7-0.8) — and it noted
  output power ∝ `Re(Z_throat)`, so an unloaded J-winner is quiet and distorting regardless of
  how good its normalised polars look.
- §6: "P12a re-score cached responses with `load` on ... Zero GPU" is ranked FIRST of the changes
  before more large campaigns — which is what tonight's re-score (L3.2) executes under both
  v6 and v7.

### 2.2 `docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md`

- §0: ship `objective.version: 6` (`loading_smooth`) as a **separate** scorer for loading /
  rollback horns; briefs opt in; Keele/OSSE stay on v4; **do not compare raw J across v4 and v6
  briefs** (different term definitions and tolerances).
- §2: the corrected claims: flat `cov` + `dislope→0` remapping is the wrong MATH for class B
  (band-mean `load` was ~2 % of J on the class-B seed; for JMLC `f0` is the loading CORNER, not
  a Keele pattern-control frequency; a *smooth rising* DI ≈ +5 dB/decade is the family's
  published virtue, not a CD plateau).
- §3.2: `load_near` is defined as the integral-style corner-limited mean plus the soft
  `f_loaded` hinge (tolerance 0.25, weight 1.0) and `z_smooth` as the mouth-reflectance proxy
  (`std(Re z)`, weight 0.8, tolerance 0.15) — matching §1.2/§1.3 above; legacy CD keys
  (`cov`, `load`, `dislope`, `di`) are intentionally NOT in the v6 weighted set.

---

## 3. Decided recommendation (written down, as directed)

**Keep the split: v6 for the Le Cléac'h / rollback (loading/class-B) family, v7 for CD briefs.
Do NOT create a v8 tonight.**

Rationale in five lines:

1. v6 and v7 answer different physical questions. v6 scores near-corner loading + impedance
   smoothness + a natural DI rise for horns whose band edge IS the loading corner
   (f0 = fc, pattern from ~1.6·fc). v7 scores a CD/PA brief: constant beamwidth coverage with an
   8 kHz floor, LFP-based loading reach, and constant-velocity on-axis flatness — the Keele/OSSE
   class where flat DI and flat bandwidth are the goal.
2. The v6 brief vocabulary (`load_near`, `z_smooth`, `cov_pat`, `di_rise`) and the v7 vocabulary
   (`load`, `flat_cv`, C3 floor, C5 asymmetric V) already ship, are validated, and are
   brief-gated (`objective.version` selects the scorer; nothing auto-switches). Merging them
   into one scorer would silently change every existing brief's J — exactly what the v6 dossier
   forbids.
3. Tonight's offline re-score (`docs/evidence/RESCORE_V6_V7_2026-11-12.md`) is the evidence that
   the two rank the same stored designs differently (Kendall tau per class is in that doc) —
   which argues for keeping each scorer with its class, not for a merge.
4. A v8 would be a THIRD definition of "loading" on day zero of reconciliation; that is scope
   creep without a named physical question.
5. If a merge is ever wanted, it is an owner decision (§4).

---

## 4. What an owner would need to approve to merge v6 and v7 later

Each row is a real behavioural difference between `objective_v6` and `objective_v7`; a merged
objective must pick one per row (or make it a brief knob, which then needs its own tolerance
review):

| # | Difference | v6 stance (scalar_v6.py) | v7 stance (scalar_v7.py) |
|---|---|---|---|
| 1 | Loading aggregator | Corner-windowed MEAN of the `z_min` hinge on `[band_lo, max(f0, α·fc)]`, plus soft `(f_loaded-f0)/f0` hinge (201-226) | Octave penalty on the LFP20 crossover (`log2(LFP20·1.6/F_X)`) PLUS a MIN-based plateau deficit `max(0, 0.5 − min Re z)` over `[F_X, f11]` (289-326) |
| 2 | Frequency anchor | `fc_hz` resolution chain with `load_alpha` / `pattern_beta` multipliers (165-179) | `F_X = f0_effective_hz()` only; `f11` precedence for the upper bound (268-286) |
| 3 | Impedance smoothness | First-class term `z_smooth` = `std(Re z)` on `f ≥ f0` (229-238) | Absent (no analogue; C2 `flat_cv` smooths the on-axis level, not the impedance) |
| 4 | Coverage scoring | `cov_pat` scored only above `pattern_beta·fc`, one-sided below-f0 default (`cov_narrow_ratio` default 1.0) | v4 coverage + 8 kHz one-sided floor (bw8k_floor 0.75) + optional asymmetric V; `cov_narrow_ratio` default 2.0 (`cov_below_f0` default `mask`) |
| 5 | DI treatment | `di_rise` = slope-error on a natural +5 dB/dec rise (265-271); CD keys `di`/`dislope` dropped | v4 `di` + `dislope` kept (tolerance per brief, e.g. 36.0); `distd` std-DI live |
| 6 | Term key set | `load_near, z_smooth, flat, rip, cov_pat, di_rise, distd, diag` (34) | `cov, rip, di, dislope, flat, load, distd, diag, flat_cv` (79-83) |
| 7 | On-axis flatness | `flat` only (detrended or std) via v2 helpers (298-304) | `flat` + `flat_cv` (unit-velocity band `F_X..3000 Hz`, linear detrend vs log2 f; 332-354) |
| 8 | Loading thresholds | `z_min` from the target; no separate plateau/LFP levels | `loaded_re_z` 0.50, `lfp_re_z` 0.20, `lfp_crossover_ratio` 1.6 as brief constants (105-108) |
| 9 | Gate mapping | No direct gate equivalent (gates are v4/v7-shaped; `gate_loading` matches v7) | `gate_loading` in `tools/rescore/gate_audit.py:302-374` IS v7's C1 |
| 10 | Brief constants | `load_alpha`, `pattern_beta`, `fc_hz`, `cov_below_f0 one_sided` default (61-79) | `bw8k_floor`, `cov_below_f0 mask` default, C5 V-half-angles (408-465) |

A merge must also decide the J-comparability rule (v6 dossier: never compare raw J across
versions) and re-run this reconciliation's re-score for the merged scorer.

---

## 5. Pointers

- Implementation: `hornlab_search/objective/terms.py` (v4), `hornlab_search/objective/scalar_v6.py`,
  `hornlab_search/objective/scalar_v7.py`.
- Gates: `tools/rescore/gate_audit.py`.
- Evidence for tonight's rank disagreement: `docs/evidence/RESCORE_V6_V7_2026-11-12.md`
  (and `scratch/rescore_2026-11-12/` in the L3 worktree).
- Driver-model report-only check (sensitivity prediction status): same evidence doc, §driver.
