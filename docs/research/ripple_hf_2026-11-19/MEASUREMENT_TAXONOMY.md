# Measurement taxonomy for horn ripple, directivity and HF coverage

Mandate item 2: separate the phenomena **before** writing any new weighted term. This document is
the gate for items 3–6: no term enters a score until the phenomenon it charges is named, is visible
in our own data, and is not already charged by an existing term.

Status: **taxonomy only — nothing here is a score term.** The one number implemented so far is
report-only (`hornlab_search/metrics/spectral.py`). Source table at the end; every claim carries
`[quoted]`, `[paraphrase]` or `[inferred]`.

## 1. What the objective charges today

| Term | Axis | Definition in code | What it cannot see |
|---|---|---|---|
| `rip` | **angle** at fixed frequency | `smoothness.ripple_detrended_db`: quartic detrend `n ~ a0 + a2·θ² + a4·θ⁴` over in-coverage angles, sample std of the residual; v7/v9 aggregate it per frequency and weight by frequency | structure along a **frequency** sweep at a fixed angle |
| `flat` | **frequency** on axis | `band_flatness_detrended_db`, straight line in `log2 f` | off-axis frequency structure |
| `flat_cv` | frequency, constant-velocity units, `F_X–3000 Hz` | v7 addition | anything above the LF band |
| `cov`, `dislope`, `distd`, `di` | beamwidth / DI trend | `metrics/beam_shape.py`, `di.py` | passes through a **narrow** notch whose beamwidth integral barely moves |
| `diag`, `pattern_quality` | lobes, islands, off-axis excess | `metrics/pattern_quality.py` | smooth-but-wrong spectral shape |
| `load`, `lfp50`, `rez_min_from_fx` | throat loading | `objective/scalar_v7._load_v7` | everything radiative |

So `rip` is an *angular* residual. A defect that is a function of frequency at one listening angle is
not charged by any weighted term. That is the measurement gap, stated precisely.

## 2. The phenomena, separated

Each row: what the phenomenon is, whether stored BEM data can show it, and the honest verdict.

| # | Phenomenon | Signature | In our stored data? | Verdict |
|---|---|---|---|---|
| P1 | **Angular ripple / lobing** | fixed frequency, level oscillates with angle | yes — 73-sample H/V cuts at 18 frequencies | already charged (`rip`, `diag`, `pattern_quality`) |
| P2 | **Fixed-angle spectral variation** | fixed angle, level deviates from a smooth trend along frequency | yes — 18 frequency samples per angle | **not charged**; implemented report-only |
| P3 | **DI / beamwidth instability** | DI vs `log f` non-monotonic, or beamwidth jumping between adjacent octaves | yes — `di_db`, `bw_h/v_deg` per frequency | partly charged (`dislope`, `cov`) |
| P4 | **Detached lobes** | a secondary lobe outside the main coverage region | yes — `n_multilobe`, `connected_main_lobe` | charged (`diag`) |
| P5 | **Modal interference / HOM** | pattern changes above the throat's first transverse-mode cut-on | yes, but **not separable** from geometry diffraction on one frequency sweep | not directly measurable; needs a mode-decomposition or controlled A/B (see §5) |
| P6 | **Throat / mouth reflection** | periodic ripple in complex `z_throat` and in level, period ≈ `c/2L_eff` | yes, complex `z_throat` stored — but 18 log-spaced points alias it | only gross reflections, and only with a dense grid (see `../TIME_DOMAIN_RINGING.md`) |
| P7 | **Real driver / wall resonance** | high-Q feature, wall vibration, phase-plug behaviour | **no** — rigid, lossless walls; uniform-velocity cap; driver internals unmodelled | out of scope for the BEM; belongs to measurement |

P5–P7 are the reason the handoff is right to call the B3 feature *undiagnosed* rather than a
resonance: the model can produce all three signatures and cannot, on one sweep, say which one it
produced.

## 3. The fixed-angle number: definition and its place in the literature

Definition used (`fixed_angle_residual_db`): normalise a fixed-angle cut to its 0° sample
(`n(f) = L(f,θ) − L(f,0)`, i.e. the direction-dependent level ratio), restrict to a band, and quote
the RMS deviation from a reference.

Two references, and they are not equivalent:

| Reference | Formula | Provenance |
|---|---|---|
| **band mean** (`reference="band_mean"`) | `rms(n − mean(n))` over the band | **standard practice**: IEC 60268-5 §20.6 defines frequency-response smoothness as the response referred to the mean level in the band over equal-log bands; Klippel AN 40 restates it [quoted] |
| **trend** (`reference="trend"`, default) | `rms(n − polyfit(log2 f))`, order 2 | **exploratory**: no standard prescribes a quadratic (or any) trend fit for a roughness residual. Use it to remove broad beam narrowing, and say so. |

The handoff's numbers (and the tool's default) are the trend variant. The band-mean variant is the
one we would defend to a reviewer; the trend variant is the one that removes a smooth narrowing.

**Precedent, and the part of the handoff that needs correcting.** Sridhar, Tylka & Choueiri define
constant directivity as "a frequency response at any off-axis position that is identical to its
on-axis frequency response, ignoring any difference in overall level", and their **metric 2**
(listening-window spectral distortion, `C_LW`) already charges a fixed-direction deviation of that
normalised ratio [quoted]. So the axis is *not* unclaimed in the literature — it is unmet in our
*objective*. What is genuinely uncovered even by their metric set is **common-mode ripple** (the same
spectral shape at every angle): it leaves the normalised ratio flat while the sound is still not
smooth. State that precisely instead of "nobody measures this".

**Naming.** Reuse existing names rather than inventing a score: **"off-axis frequency-response
smoothness, band-mean referenced"** (IEC/Klippel lineage) and **"off-axis trend residual"** for the
exploratory variant. Do not ship a coined acronym, and do not call either one "ripple" — `rip`
already owns that word in this repo.

**Which of the five published metrics we must not adopt as targets.** Metrics 1 (contour-line
Fourier), 4 (`σ_DI`) and 5 (NACC) penalise a *legitimately narrowing* horn by construction — the
paper says metric 4 "penalizes broadband spectral trends in directivity more severely than narrowband
deviations" and metric 1 is biased toward designs that are non-constant-directive but have wide
horizontal contour sections [quoted]. Our Le Cléac'h, Iwata and Klangfilm families are intentionally
non-CD (`docs/knowledge/typologies/lecleach_iwata.md`, `classical.md`). Any use of those three must
be per-family and opt-in, never a global gate.

## 4. Applicability to our families

`hornlab-acoustic-grounding` applies: **do not generalize across typologies.**

| Family | Fixed-angle band-mean smoothness applicable? | Caveat |
|---|---|---|
| OSSE / R-OSSE / ATH | yes | the brief's DI slope target defines expected narrowing; compare within family, never against a flat target |
| Le Cléac'h / Iwata | yes, **as a relative number only** | the family's raison d'être is progressive narrowing; a CD-shaped residual target would forbid the typology |
| Klangfilm / rolled / lame | yes | multiple construction variants share a name; group by config, not by family label |
| Multicell / MEH | **not yet** | cells couple in phase; a single-source exterior solve does not validate the system (`docs/knowledge/typologies/multicell.md`) |
| Conical / tractrix | yes, with a wide band | broad deviations are the design, not a defect |

## 5. What the model cannot see (and the one cut-on number worth quoting)

- Rigid, lossless walls; linear; **uniform normal velocity** on a spherical cap at the throat. No
  printed-wall vibration, no viscothermal loss, no phase-plug cavity, no non-linearity
  (`../TIME_DOMAIN_RINGING.md` §2).
- The throat's first transverse (non-planar) mode is the rigid-duct `(1,0)` mode: `k·a = 1.841`,
  so `f_c = 1.841 c / (2π a)`. With `c = 343 m/s` and `a = 17.9 mm` (35.8 mm throat) →
  **5.61 kHz**, equivalently `f_c ≈ 0.586 c / d` [inferred, standard result]. The handoff's "~5.6 kHz"
  is correct. Above it the real interface field is multimodal — Behler & Makarski measured and
  mode-decomposed a real driver/horn interface [paraphrase of S7 via S4]; Kolbrek describes mode
  coupling across a cross-section change [quoted]. Conclusion: **any 8–16 kHz improvement is a result
  about a uniform piston in a horn, not about a driver**.
- Sparse frequency sampling: an 18-point log grid (≈1/3 octave above 1 kHz) cannot resolve high-Q
  structure; the measurement standard's practice is ~1/9-octave resolution and "notches narrower
  than 1/9 octave will not be regarded" [quoted via Klippel/IEC]. A resonance narrower than the
  sample spacing is invisible **and** its absence from the grid is not evidence it is absent.

## 6. Rules this taxonomy imposes on the next step

1. Report both references, name which one a number is, and never compare a trend residual to `rip`.
2. Report the identity (`objective_version`, `config_name`, `design_hash`) with every number; never a
   pooled rank across versions or briefs.
3. Sensitivity first: detrend order, angle set, band edges. A conclusion that flips under order 1→3
   is not a finding.
4. Redundancy must be *measured*, not assumed: on the 24 SCOUT40 bests the rank correlation between
   `rip` and the `+35°` trend residual is ρ ≈ 0.885, so the new number is largely redundant there
   (see the evidence doc). Promotion to scoring needs a rank reversal, not a plausible story.
5. A promotion is a **new objective version** with its own identity and floor, never an edit to v7,
   v9 or v10, and never a retroactive re-score.
6. State per-family applicability (see §4) in any comparison table.

## 7. Sources

| id | citation | URL | verified |
|---|---|---|---|
| S1 | Sridhar, Tylka & Choueiri, "Generalized Metrics for Constant Directivity", *JAES* 67(9):666–678 (2019), DOI 10.17743/jaes.2019.0022 | <https://3d3a.princeton.edu/publications/generalized-metrics-constant-directivity> | abstract + formula excerpts; publisher PDF blocked |
| S2 | Kolbrek, "Boundary Element Method Simulations" (2012) | <https://kolbrek.hornspeakersystems.info/index.php/horns/bem> | full page |
| S3 | Kolbrek, "Modes in horns" (2011) | <https://kolbrek.hornspeakersystems.info/index.php/blog/modes-in-horns> | article text (index fetch) |
| S4 | Kolbrek, "Higher Order Modes" (2014) | <https://kolbrek.hornspeakersystems.info/index.php/blog/higher-order-modes> | full page |
| S5 | Batík, "OS-SE Waveguide", ATH | <https://at-horns.eu/osse.html> | full page |
| S6 | Batík, "ATH CORE" | <https://at-horns.eu/core.html> | full page |
| S7 | Behler & Makarski, "On the Velocity Distribution at the Interface of Horn Driver and Horn", AES 116th, Paper 6097 (2004) | <https://www.aes.org/e-lib/browse.cfm?elib=12743> | **title/venue only — paywalled**; substance via S4 |
| S8 | Klippel, "AN 40: Smoothness of Amplitude Response" | <https://www.klippel.de/fileadmin/klippel/Files/Know_How/Application_Notes/AN_40_Smoothness_of_Amplitude_Response.pdf> | text fetched |
| S9 | IEC 60268-5 (sound system equipment, loudspeakers) | paywalled | normative clauses quoted via S8/AN 35 |

Accessed 2026-11-19. Anything marked paywalled was not read in full and supports no stronger claim
than its abstract or a citing source's description.
