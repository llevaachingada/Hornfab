# Improving FAV-001's throat loading without losing its directivity

2026-11-20 evening, owner request: *"keep the characteristics we like about this … but improve the throat
loading, maybe without compromising other things, even if that requires a way of describing the geometry or
adding a parameter or two"*, then *"also consider a two inch compression driver size"*.
Companion to `CROWE_X_FAVORITE_RESEARCH.md` (FAV-001 = `4140768780f0`).
Labels: [measured] [derived] [proxy] (plane-wave Webster, `cpu/levers2.py`, trends only).

## 1. What OS `k` actually damaged [measured]

The k = 2/3/4 hold-mouth solves (`runs/20261120T2021*`, `…202233Z…`) are **identical to FAV-001 below
~2.3 kHz**: beamwidth, polar ripple and DI agree to ±1° / ±0.1 dB from 828 Hz to 2.27 kHz. All the cost is
**high-frequency beaming**:

| 8 kHz | FAV-001 (k 1) | k 2 | k 3 | k 4 |
|---|---|---|---|---|
| H beamwidth | 69° | 61° | 55° | 52° |
| V beamwidth | 57° | 52° | 48° | 46° |
| DI | 12.5 dB | 13.6 | 14.3 | 14.8 |
| H polar ripple | 2.8 dB | 3.5 | 4.0 | 4.3 |

Mechanism [derived]: k > 1 uses the OS profile of a larger virtual throat (Batík; see the main dossier).
The wall leaves the 18 mm exit almost cylindrically and turns later. At short wavelengths the wavefront
stays near-planar through that neck and does not fill the later wall angle. That is the classic HF
narrowing of exponential/tractrix-style throats; the OS profile (k 1, matched a0) avoids it. The scales
conflict: loading at 700 Hz depends on the first ~λ/2π ≈ 80 mm, which is exactly where 3–8 kHz coverage is set.
Any slow-start throat on the 1.4" exit trades HF coverage for loading. This explains the 1:1 trade
measured in the k-attribution and k-home runs.

Two consequences:
- The **V** narrowing is not harm. FAV-001's V is 57° against a 50° target, so slowing the throat in V
  only moves V toward target.
- The **H** narrowing is the harm (69° against 80°). Keep the horizontal plane's OS law pure.

## 2. Levers, ranked

### 2.1 2-inch exit (r0 25.4 mm), same OS law, k 1: best lever [proxy, then GPU]
The cone/OS loading corner scales with the throat radius (virtual apex distance ∝ r0/tan a). The profile
law is unchanged, so no slow-start neck is added. [practitioner] Geddes: larger compression-driver throats
lower the falloff when the waveguide is true CD (main dossier, Sources).

| proxy, mouth held 587 mm | load term | LFP20 / LFP50 | Re z 682 / 782 / 1028 Hz |
|---|---|---|---|
| FAV-001, 1.4" | 2.88 | 674 / 1144 | 0.21 / 0.36 / 0.30 |
| **same knobs, 2"** | **1.44** | 581 / 668 | 0.55 / 0.68 / 0.62 |
| 2" + V-only k 2 | 1.21 | 563 / 648 | 0.65 / 0.85 / 0.74 |

Risks to measure:
- A 50.8 mm near-flat source is larger relative to HF wavelengths (ka ≈ 3.7 at 8 kHz), so HF narrowing may come back by a different route.
- The ideal uniform-velocity cap is idealised above the 2" exit's first cross-mode, **3.96 kHz** (vs 5.6 kHz for 1.4"), and real 2" drivers' top-octave/phase-plug behaviour is not modeled.
- The exit angle stays 2° (assumed; no specific driver chosen).
- New briefs `examples/briefs/hf2in_2026-11-20/` (home 700 Hz and compact500 XO900): only the driver radius and `loaded_hi_hz` (3957 Hz) change. **Own J identities.**

### 2.2 V-only (asymmetric) k: existing knob, no code change
`g_throat_hv_ratio` (ρ) is already implemented for `osse_rollback`. It is owner-approved (2026-11-18),
grounded in Batík 2020 §5 ("profile parameters may vary around the device"), `docs/knowledge/claims/KH-003_*`
and `docs/knowledge/THROAT_HV_CONTROL_AUDIT_2026-11-18.md`. It gives k(φ) = k·ρ^(−cos 2φ / 2). With **k = √K, ρ = K: k_H = 1 exactly,
k_V = K.** [proxy] The gain is modest on its own (load term 2.88 → 2.40 at k_V 3, 2.25 at k_V 4), because the
H plane carries most of the area growth. The V mouth also shrinks (450 → 407 mm at k_V 3), so a_v must rise to
compensate (the lanes allow a_v up to 31–32°). Its value is as a **companion** to 2.1 and as the clean test of
"is V-only HF narrowing harmless for J".

### 2.3 Rejected or deferred
- **Global k > 1:** measured. It beams at HF (§1).
- **ATH throat extension / slot** (`throatExtLength`, `slotLength` exist in the mesher, not in `osse_rollback`):
  it is a cylindrical/conical neck, the same HF-beaming mechanism as k, plus a diffraction step. Not worth a new knob.
- **Designing a throat resonance** to satisfy LFP20 (how the competitors score `load` ≈ 0): rejected. It is
  stored energy that the one-sided v11 term fails to charge (main dossier §3, §8.1).
- **Lower crossover:** not a geometry lever. The XO900 identities (`fav8__x900_*`) answer it.
- **New knob, "throat-local k"** (k blended back to 1 within ~40–80 mm, restoring the k = 1 asymptote): not
  built. §1's scale argument predicts it buys little loading at 700 Hz before it causes the same HF beaming.
  Revisit only if the 2" lanes disappoint.

## 3. Queued, at the FRONT of the live night `fav8_2026-11-20`

Inserted after the running `fav8__k1_cd_polish` (configs `examples/typologies/favL_2026-11-20/`, writer
`cpu/write_favL.py`; shape_check 6/6 fit, round coupling matches each exit; preflight no HARD, valid
fraction 38–46 % after tightening the boxes):

| job | brief identity | what |
|---|---|---|
| `favL1__2in_single` | 2" home 700 | FAV-001 knobs exactly on a 2" exit: **the clean driver-size attribution** |
| `favL1__kv3_single` | 1.4" home 700 (= FAV-001's) | FAV-001 + k_H 1 / k_V 3 (L 260.4), comparable with FAV-001's 4.996 |
| `favL1__2in_kv2_single` | 2" home 700 | 2" + k_V 2 |
| `favL__2in_home` | 2" home 700 | CMA 80 valid, k [1, 1.6], ρ [1, 4], seeded at FAV-001 |
| `favL__kv_home` | 1.4" home 700 | CMA 80 valid, k [1, 2], ρ [1, 4] (k_H ≈ 1, k_V up to ~4) |
| `favL__2in_c500` | 2" compact500 XO900 | CMA 80 valid, seeded at `746d33134776` with k 1.2 |
| `favL_verify_top3` | each lane's own | verify top 3 of the three lanes |

**Success test:** a design whose 8 kHz H beamwidth stays ≥ ~66° and whose CD-matrix "non-load" stays within
~10 % of FAV-001's 2.352 while `load` falls under ~1.5. Rank J only within an identity. Across the 1.4"/2"
identities, compare the physical numbers (Re z, LFP50, beamwidths, CD-matrix values), not J.

## 4. Single-solve results, 17:51–17:54 [measured, screen]

| design | identity | J | load | non-load | off-axis | DI std (w) | LFP20 / LFP50 | 8 kHz H / V | DI 8 kHz |
|---|---|---|---|---|---|---|---|---|---|
| FAV-001 | 1.4" home | 4.996 | 2.645 | 2.352 | 0.543 | 0.319 | 674 / 995 | 69 / 57 | 12.5 |
| `favL1__kv3` (k_H 1, k_V 3) | 1.4" home | **4.657** | 1.951 | 2.706 | **0.574** | 0.426 | 631 / 868 | **70** / 51 | 12.9 |
| `favL1__2in` (FAV knobs, 2") | 2" home | 3.378 | **0.696** | 2.682 | 0.934 | 0.429 | 506 / 717 | 63 / 54 | 13.2 |
| `favL1__2in_kv2` | 2" home | 3.737 | 0.000 | 3.737 | 1.362 | 0.618 | 424 / 671 | 60 / 43 | 14.5 |
| ref: `favk__k2` (global k 2) | 1.4" home | 4.800 | 1.508 | 3.292 | 1.142 | 0.519 | 595 / 832 | 61 / 52 | 13.6 |
| ref: `fav8__k1_cd_polish` best non-load `392276e62470` | 1.4" home | 4.852 | 2.652 | **2.199** | **0.408** | **0.258** | — | — | — |

Read:
- **V-only k works as designed.** H at 8 kHz stays 70°, off-axis smoothness is essentially unchanged
  (0.543 → 0.574), V moves toward its 50° target (57 → 51°), and J improves 0.34 on FAV-001's own
  scale. That beats the global k 2 (4.800) at less than half its directivity cost.
- **The 2" exit** cuts load 74 % (2.645 → 0.696) at a moderate HF cost (8 kHz H 69 → 63°, off-axis 0.54 → 0.93).
- **Both together overshoot:** V collapses to 43° and DI std doubles.
- `fav8__k1_cd_polish` found the first k = 1 design that beats FAV-001 on every CD-matrix term (longer
  lip wrap 105°, depth 274 mm). Its loading is unchanged.
- Next best combination to test: k1_cd_polish geometry (`392276e62470`) + V-only k ~3. The CMA lane
  `favL__kv_home` explores that region from FAV-001.
