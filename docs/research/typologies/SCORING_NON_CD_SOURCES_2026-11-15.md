<!-- Copied 2026-11-15 from a Sonnet research subagent (study BIRADIAL_CROWE_STUDY_2026-11-15.md). CAVEATS: the
     "Harman preferred 1-3 dB/oct DI slope" figure is [inferred] - the agent could not reach the Olive/Toole primaries
     (403/404); verify before relying on it. The study used di_slope_target 5.0 dB/decade (not the 6.0 suggested here).
     Offline rescores must override the ROW target (di_slope_target is stored per row), not only the brief. -->
# Is the v7 CD target fair for exponential / Crowe ES-style horns?

**Date:** 2026-11-15  
**Repo context:** `hornlab-search` / home hi-fi brief `room_landscape_80x50_700_hf1440_v7`  
**Question:** We score exponential / Crowe ES-style / rolled-mouth horns against a constant-directivity target; they aren't CD horns, so is the target realistic or fair?

---

## 1. What the v7 objective actually encodes as the "target"

Exact term definitions from `hornlab_search/objective/scalar_v7.py` and `hornlab_search/objective/terms.py`, weights and tolerances from `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml`:

| Key | Raw definition | Weight | Tolerance | Encodes... |
|-----|---------------|--------|-----------|-----------|
| `cov` | mean freq( (bw_H − 80°)² + cov_v_weight·(bw_V − 50°)² ) / 100, narrow-side ×2, 8 kHz floor, scored ≥ 700 Hz | 1.0 | 3.0 | **Coverage held constant at 80×50 across the entire band** |
| `dislope` | (polyfit slope of DI vs log10 f − `di_slope_target`)² ; `di_slope_target = 0.0` | 1.0 | 9.0 | **DI slope = 0 dB/decade (constant DI)** |
| `di` | mean freq( (DI − target_di_db(80°,50°))² ) / 10 ; `target_di_db` ≈ 10.1 dB | 0.3 | 0.4 | **DI = 10.1 dB constantly** |
| `distd` | std of DI over scored band | 0.5 | 2.0 | DI steadiness (smooth rise accepted; jagged DI penalised) |
| `diag` | 45° diagonal bw² errors / 100 vs round reference | 1.0 | 2.0 | Diagonal pattern vs H/V planes |
| `rip` | mean H+V in-coverage polar ripple | 1.0 | 1.0 | Ragged patterns regardless of typology |
| `flat` | std of on-axis SPL ≥ 700 Hz (scored band) | 0.5 | 1.5 dB | On-axis roughness |
| `flat_cv` | std of residual of on-axis + 20log f vs log f, 700–3000 Hz | 1.0 | 1.5 dB | Constant-velocity flatness |
| `load` | log2(LFP20 × 1.6 / 700) + max(0, 0.5 − Re_z_min) | 1.0 | 0.3 | Loading at and above the XO |

Three terms (`cov`, `dislope`, `di`) explicitly assume constant-directivity behaviour. The other six (`distd`, `diag`, `rip`, `flat`, `flat_cv`, `load`) are typology-agnostic quality indicators.

**Example scores (normalised, brief home landscape v7):**
- CD OSSE horn: J = 3.1 (cov 0.77, dislope 0.02, di 1.81)
- Crowe ES-600-style exponential: J = 22.8 (cov 5.3, dislope 8.7, di 6.0, diag 5.0)
- Crowe H beamwidth: 90°→46° at 1.5→16 kHz; V 137°→41°; DI 2→16 dB over same range.

---

## 2. What listening research says about DI for home use

### Olive preference model (Olive 2004 AES 116th Conv., Parts I–II; cited in repo `docs/research/ONAXIS_WEIGHTING_2026-11-14.md`) [verified—formula reproduced in repo doc]

```
Pref = 12.69 − 2.49·NBD_ON − 2.99·NBD_PIR − 4.31·LFX + 2.32·SM_PIR
```

`SM_PIR` is the smoothness of the Predicted In-Room Response (CTA-2034: 12 % LW + 44 % ER + 44 % SP). It rewards smooth DI; it does **not** demand zero slope. `NBD` (narrow-band deviation) measures local roughness, not overall tilt. The model says:

- **Smooth, gradually rising DI improves `SM_PIR`.** A smoothly rising DI makes the in-room response taper gently with frequency instead of being flat or jagged, and this is preferred.
- **Off-axis behaviour outweighs on-axis by ~3:1** (ER + SP carry 88 % of PIR). The single on-axis line v7 scores via `flat`/`flat_cv` captures ~12 % of the driver that determines preference.
- **DSP can fix broad on-axis tilt but not seat-to-seat variation.** Crowe's smooth polar pattern means low `seat_spread` even if the DI is rising; that is what matters most for the DSP home system. [verified—from hifi_rescore analysis in repo docs]

### Typical DI slope for well-rated speakers [inferred from Olive/Toole/Harman research; not fetched from primary source this session]

Published Harman listening-test data (Toole *Sound Reproduction*, 3rd ed.; Olive 2015, 70-speaker study) shows:

- Preferred speakers: **DI rising ~1–3 dB/octave** (≈3–10 dB/decade) across 1–10 kHz.
- ~2 dB/oct (~6–7 dB/decade): typical of well-regarded coaxial and CD waveguide designs.
- 4–5 dB/oct or steeper: associated with lower preference; not categorically bad if smooth, but the in-room tilt can exceed what DSP EQ is applied to.
- **Smoothness matters more than the absolute slope.** Sudden DI jumps at the crossover region are penalised more than a steeper-but-uniform slope. [inferred—consistent with published Harman research; numeric thresholds are model knowledge, not independently fetched today]

### What the Crowe ES horn's DI slope actually is

From the problem statement: DI rises 2→16 dB, 1.5→16 kHz.

- 14 dB over log2(16/1.5) = **3.4 octaves → 4.1 dB/octave**
- 14 dB over log10(16/1.5) = 1.03 decades → **~13.6 dB/decade**

4.1 dB/octave is at the upper edge of the preferred range (1–3 dB/oct is Harman ideal; 4–5 is their "steeper than ideal" zone). It is **not beyond the pale for a horn speaker in a DSP system**, but it is steeper than a typical passive HF stand-mount.

However, the dislope raw term is `(13.6 − 0.0)² = 184.9`, normalised by 9.0 → **20.5 units**. The brief example shows normalised 8.7, implying slope ≈ sqrt(8.7 × 9) ≈ **8.9 dB/decade ≈ 2.7 dB/octave** — squarely within the Harman preferred range. Yet the horn scores 8.7 normalised units on dislope and contributes 8.7 to J.

**Conclusion:** `dislope` with `di_slope_target = 0.0` penalises Harman-preferred slopes of 2–3 dB/octave by 8–9 normalised units. That is not a property of the horn being bad; it is a consequence of the target being wrong for this class.

---

## 3. What Crowe ES / Le Cléac'h / exponential-horn designers claim and measure

### Joseph Crowe ES-600 (josephcrowe.com; repo `docs/research/CROWE_X_HORN_HANDOFF_2026-11-15.md`) [primary — from published spec sheet; measurements section unverified today as josephcrowe.com returned 404 during this session]

- 417 W × 203 H × 198 D mm; 1.4" throat; 600 Hz–20 kHz rated; "ES flare" = exponential, 270° wrap-around mouth.
- Measured with Faital HF1460 (1.4"): loading from ~500 Hz; 0°/15° nearly identical, 30° −2 to 3 dB, 45° −4 to 10 dB above 2 kHz; treble falls ~6 dB/oct from 5–10 kHz. Very low distortion. [verified — from josephcrowe.com spec page as reported in handoff doc]
- **The Crowe design goal is loading quality and low coloration, not flat beamwidth.** The mouth rollback reduces diffraction and mouth reflection (JMLC/ETF2010 argument). DI rising with frequency is accepted; polar smoothness (no lobes, no sudden narrowings) is the differentiator.

### Le Cléac'h / JMLC family (repo `docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md`, sourced from JMLC ETF 2010 lecture and Fourcade 2015 exact equations) [primary/secondary — in-repo research]

- "Good horn = less reflected/diffracted energy + HOMs." DI rises by design; equidistant wavefronts produce a smooth, monotonically narrowing beam.
- **JMLC advocates explicitly do NOT target flat beamwidth.** The loading corner `fc` governs the impedance; the pattern starts to control at ~1.5–1.8 × fc. Below that frequency the pattern is physics, not a failure.
- Published virtue: **smooth rising DI + good resistive loading**; not constant-directivity plateau.

### Existing in-repo v6 objective for loading horns [verified — from `LECLEACH_OBJECTIVE_V6_2026-11-05.md`]

The repo already has a worked-out alternative objective (v6, `loading_smooth`) for this class:
- `cov_pat`: coverage only scored ≥ `f_pattern = 1.6 × fc`, not over the whole band.
- `di_rise`: replaces `dislope`; targets **+5 dB/decade** (mid of +4..+6 class range) instead of 0.0. `std(DI_slope − 5)^2 / 4.0`.
- `load_near`: integral-style loading penalty concentrated near the loading corner, not diluted by HF.
- `distd`: retained; a smooth rise should have low distd.
- Legacy CD keys `cov`/`load`/`dislope`/`di` are absent from the v6 weighted set.

---

## 4. Term-by-term assessment: what over-penalises, what is fair

### Terms that unfairly penalise a smoothly narrowing horn

**`dislope` (normalised 8.7 for the Crowe example) — UNFAIR AS CONFIGURED**

Target 0.0 dB/decade encodes the CD assumption. A Crowe-style horn rising ~2.7 dB/oct (8.9 dB/decade) scores 8.7 normalised units not because it is bad — this slope is within the Harman preferred band — but because the target is wrong. The quadratic form `(slope − 0)²` means that every dB of slope adds to J without bound, with no allowed window.

Fix: change `di_slope_target` to ~6 dB/decade (the midpoint of the typical 1–3 dB/oct range, in dB/decade). A Crowe at 8.9 dB/decade would then score `(8.9 − 6)² / 9 = 0.93 units` instead of 8.7. Alternatively, use a deadband: add a tolerance window `max(0, |slope − target| − window)²`, e.g. slope between 0 and 10 dB/decade incurs zero penalty.

Concrete tolerance: `di_slope_target = 6.0` with the existing tolerance 9.0 is a one-line brief change (no code change). It yields zero penalty at 6 dB/decade, 1 unit at 9 dB/decade, and 1 unit at 3 dB/decade (symmetric), covering the Harman preferred range with ≤1 unit penalty.

**`cov` (normalised 5.3 for the Crowe) — UNFAIR AS CONFIGURED for the full band; fair at HF only**

The Crowe starts at 90° H (above the 80° target) and narrows to 46° (34° below target). With `cov_narrow_ratio = 2.0`, the HF narrowing (the horn's natural behaviour from the cutoff frequency upward) is counted twice. The brief frequency-weights 2.5–5.5 kHz at 2×, so the narrowing in the presence band is penalised 4× relative to a symmetric miss.

Fix options:
(a) **Narrow-ratio 1.0 for loading horns** (symmetric penalty): removes the factor-of-2 on the HF half. This is a brief parameter change (`cov_narrow_ratio: 1.0`).
(b) **Wider coverage tolerance**: tolerance 3.0 → 10.0 reduces cov from 5.3 to 1.6 without changing the math.
(c) **Score cov only above `1.6 × f0`** (the v6 `cov_pat` approach): this is a code-level change, as v7 doesn't have this option.
(d) **Coverage band target**: allow, say, 50°–90° H without penalty. This requires a code change (a one-sided window instead of a point target).

Recommended minimum: set `cov_narrow_ratio: 1.0` and widen tolerance to 8–10 for a fair exponential-horn brief. Keeps cov as a signal (a horn that narrows to 20° H is genuinely wrong for home use) while not 2×-penalising the half that is simply physics.

**`di` (normalised 6.0 for the Crowe) — UNFAIR AS CONFIGURED**

Targets 10.1 dB constantly, but the Crowe rises from 2→16 dB. At low frequencies (900 Hz, say, DI ≈ 4 dB) the term adds `(4 − 10.1)² / 10 = 3.72` per frequency point; at high frequencies (12 kHz, DI ≈ 15 dB) it adds `(15 − 10.1)² / 10 = 2.40`. Every frequency is penalised, not because the horn is bad but because the formula's target is wrong for a rising-DI design.

Fix: for loading/exponential briefs, set `di` weight to 0.0. The `distd` term already captures DI irregularity more cleanly (a smooth rise has low distd). The absolute DI level need only be considered at the crossover frequency (DI continuity with the woofer), which is better captured by an XO-specific term or by the `hifi_rescore` `xo_spread` metric.

### Terms that are FAIR regardless of typology

**`distd`** — Std of DI over the band. A smooth, monotonically rising DI has LOW distd; a horn with lobes, dips, or abrupt narrowings has HIGH distd. This is exactly the right penalty: it distinguishes "smooth rise" (good loading horn) from "jagged DI" (bad horn of any class). Keep at current weight 0.5.

**`rip`** — Angular ripple inside the coverage window. Fair: penalises ragged off-axis patterns regardless of whether the coverage is constant or narrowing. Keep.

**`flat` and `flat_cv`** — On-axis roughness; independent of beamwidth shape. Fair. The `flat_band: scored` opt-in (already in the landscape brief) correctly starts scoring at the 700 Hz XO.

**`load`** — Loading penalty (LFP20, Re_z_min). Fair and especially important for exponential horns: their claimed virtue is good loading, so a loading horn that doesn't load well should score poorly.

**`diag`** — Diagonal beamwidth vs round reference. Mostly fair; penalises asymmetric patterns. For a Crowe-style horn the diagonal should ideally track between H and V, so a high diag score (5.0 normalised in the example) suggests the horn narrows more in one plane than the other — a real quality concern worth penalising.

---

## 5. Recommended fair scoring approach (concrete, with tolerances)

### For comparing CD and non-CD horns in the same run (a "typology-agnostic" brief)

| Term | Change | Rationale | Numeric |
|------|--------|-----------|---------|
| `dislope` | Change `di_slope_target` from 0.0 to **6.0 dB/decade** | Centres the target in the Harman preferred 1–3 dB/oct zone | `di_slope_target: 6.0`; keep tolerance 9 |
| `cov` | Change `cov_narrow_ratio` from 2.0 to **1.0** | Removes the asymmetric double-penalty for HF narrowing | `cov_narrow_ratio: 1.0` |
| `cov` tolerance | Widen from 3.0 to **8.0** | Allows the 1.5×-fc natural narrowing without dominating J | `tolerances: cov: 8.0` |
| `di` | Set weight to **0.0** | The DI absolute level is determined by the flare, not a free parameter | `weights: di: 0.0` |
| `distd` | Raise weight from 0.5 to **1.0** | Becomes the primary DI quality term when di is off | `weights: distd: 1.0` |
| `load` | Keep at weight 1.0 | Loading horns should load; this is fair and important | — |
| `rip`, `flat`, `flat_cv`, `diag` | Keep | Typology-agnostic; remain valid | — |

Expected effect on the Crowe example (rough, not re-scored):
- dislope: 8.7 → ~0.9 units (slope 8.9, target 6.0, raw (8.9−6)²=8.4, norm 8.4/9=0.9)
- cov: 5.3 → ~2.6 units (halved by ratio change, slightly widened tolerance)
- di: 6.0 → 0 (removed)
- J roughly: ~22.8 − 8.7 − (5.3−2.6) − 6.0 + 0.9 = ~11.1 (ballpark; ignores coupling)

Under this scoring, the Crowe ES-style horn would rank ~J 10–12 — competitive with the CD OSSE J 3.1 at the low end, appropriate for a horn that is genuinely a different tradeoff (better loading, smoother deep-polar, narrower HF), not categorically inferior.

### Keep strict (do not loosen for any horn class)

1. **`load`**: The loading horizon (LFP20) must cross the lfp_re_z threshold before 1.6 × f0 (1120 Hz). A loading horn that only loads well above 1.4 kHz for a 700 Hz crossover has the wrong loading geometry. Tolerance 0.3 is appropriate.

2. **DI continuity at the 700 Hz crossover** (the `xo_spread` term from `hifi_rescore.py`): the horn's DI at 700 Hz must be close to the woofer's DI at 700 Hz (typically 4–7 dB for a 10–12" direct-radiator at that frequency). An exponential horn with DI = 2 dB at 700 Hz (much below the woofer DI) would create a bright, forward on-axis lobe in the crossover region: a real flaw. This is not currently a scored term in v7 but is computed by `hifi_rescore.py`; consider adding it as a gate or term for any horn-type brief.

3. **`rip`**: Angular ripple tolerance 1.0 dB is strict but fair. A smoothly narrowing horn should have smooth off-axis response; diffraction ripple or HOM breakup shows up as rip regardless of whether the horn is CD or exponential.

4. **`flat` / `flat_cv`**: On-axis roughness tolerance 1.5 dB. Even in a DSP system, fine roughness from diffraction or HOMs that varies by angle cannot be EQ'd and should be penalised.

5. **`diag`**: Tolerance 2.0, weight 1.0. An exponential horn must keep the diagonal plane consistent with H and V; large diag scores indicate the kind of petal/lobe patterns that are audible and not EQ-able.

---

## 6. What to keep from v7 without change

The brief's `flat_band: scored` and `cov_v_weight: 0.5` are already well-tuned:
- `flat_band: scored` correctly avoids penalising the horn's natural roll-off below the 700 Hz XO.
- `cov_v_weight: 0.5` reflects the owner's stated preference that vertical dispersion matters less.

The `diag` term (weight 1.0, tolerance 2.0) correctly reads asymmetric / crease patterns that H/V-only `cov` and `rip` miss. For Crowe-style designs where the diagonal crease is deliberate, `diag` measures whether the crease is symmetric and matches the H/V planes — a legitimate quality check.

The existing v6 objective (`objective.version: 6`, `loading_smooth`) in `hornlab_search/objective/scalar_v6.py` already implements most of the above for the JMLC/Le Cléac'h class. For Crowe ES-style cells being compared against CD OSSE cells, the fastest path is a modified v7 brief with the five parameter changes in §5, leaving code unchanged.

---

## Sources

| Source | Label |
|--------|-------|
| Olive, "A Multiple Regression Model for Predicting Loudspeaker Preference", AES 116th Conv. 2004 — formula cited in `docs/research/ONAXIS_WEIGHTING_2026-11-14.md` | [verified—formula reproduced in repo doc; AES site behind paywall] |
| Toole & Olive, "Modification of Timbre by Resonances", JAES 36(3) 1988 — audibility of broad vs narrow resonances | [verified—cited in ONAXIS_WEIGHTING doc] |
| Harman/Olive 2015 70-speaker study: DI slope 1–3 dB/oct for preferred speakers; smoothness > constancy | [inferred—from trained model knowledge; web sources unavailable this session due to HTTP 403/404] |
| CTA-2034 PIR = 12 % LW + 44 % ER + 44 % SP — cited in ONAXIS_WEIGHTING doc | [verified—formula in repo doc] |
| Crowe ES-600 measured with Faital HF1460: loading from ~500 Hz, 6 dB/oct treble roll, low distortion; 417 × 203 × 198 mm, 270° mouth wrap — from josephcrowe.com spec page | [verified—from repo `CROWE_X_HORN_HANDOFF_2026-11-15.md`; josephcrowe.com returned 404 for measurement report page this session] |
| Le Cléac'h ETF 2010 lecture — smooth rising DI, loading corner as `fc`, pattern starts 1.5–1.8×fc | [primary—cited and summarised in `docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md`] |
| Fourcade, "Calcul du Pavillon Le Cléac'h", 2015 — exact construction equations | [primary/secondary—cited in JMLC research doc] |
| v6 objective design doc (`LECLEACH_OBJECTIVE_V6_2026-11-05.md`) — `di_rise` targeting +5 dB/decade, v6 term table | [measured/in-repo] |
| `docs/research/ONAXIS_WEIGHTING_2026-11-14.md` — hifi_rescore analysis: DSP score Spearman +0.99 vs v7; seat_spread vs XO_spread data | [measured—in-repo offline analysis over 870 designs] |
| `docs/research/V4_SCORING_REVIEW_2026-10-27.md` — dislope vs distd independence (Spearman −0.37 to +0.90 by family) | [measured—in-repo] |
| `hornlab_search/objective/scalar_v7.py`, `scalar_v4.py`, `terms.py`, `examples/briefs/home_landscape_2026-11-15/room_landscape_80x50_700_hf1440_v7.yaml` — exact term definitions and brief parameters | [verified—from code read this session] |
