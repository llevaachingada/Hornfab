# JMLC-family variants — research basis for the photo-driven typologies (2026-10-25)

**Header note:** this file is the extended research basis for the five owner-photo families; `docs/plan/12_RESEARCH_BASIS.md`
is FROZEN and was not edited (INDEX line added by the orchestrator at commit time). It extends, and does not replace, the
verified T1 dossier `JMLC_LECLEACH_RESEARCH_2026-10-25.md`.

Labels: **[published]** = in a fetched primary/secondary source; **[verified]** = read this session; **[inferred]** = our
derivation, shown; **[photo-derived]** = vision-lane reading of the owner's photographs, no source; **[unverified-today]** =
source unreachable today, quoted from the repo or a search snippet.

## 1. Sources and fetch outcomes (2026-10-25)

| Source | What it gives us | Status / outcome |
|---|---|---|
| Fourcade 2015, *Calcul du Pavillon Le Cléac'h* (16 pp.) | T1 exact construction + reference case (already verified; see T1 dossier) | **FETCHED** (earlier session). Re-checked today: the text contains **no** "elliptique"/"Iwata"; it is axisymmetric only. **[verified absence]** |
| Le Cléac'h, ETF10 lecture (129-page PDF) | p.37 wavefront/duct table (planar/cylindrical/spherical-cap/toroidal); p.70 family list; p.82 method; pp.125–127 Min-Phase | **FETCHED** (earlier). Re-checked: zero "Iwata", one "elliptical" (p.54, reflectors), one "toroidal" (p.37, duct type). No variant math. |
| **Auto-Tech datasheets**: E-JMLC-300, IWATA-300, JMLC-350 (horns-diy.pl PDFs) | The only **dimensioned, measured** published numbers for these products | **FETCHED** (HTTP 200; PDFs read as page images). Manufacturer datasheets. |
| Auto-Tech product line (horns-diy.pl) | Confirms E-JMLC, IWATA, JMLC, MINPHASE, SPHERICAL, TRACTRIX as separate commercial families | **FETCHED** (line card + pages). |
| J.-M. Le Cléac'h, diyAudio 140190 | The two rules; quasi-Iwata T=0.5 + AR evolution; 3-D point clouds; included angles | **live forum BLOCKED** (Cloudflare); Internet Archive answered the first CDX query, then **went offline mid-session**. In-repo quotes only **[unverified-today]**. |
| diyAudio 166312 (Auto-Tech group buy), 43/70/73; audioasylum; homecinema-fr | Practitioner comparison: EJMLC sweet spot, HF dispersion, Iwata spacing, ringing | **search-result snippets only** (Brave), pages not fetched → **[unverified-today]**. |
| sphericalhorns.net JMLC calculator | Different discretization + disclaimer (already read) | **FETCHED** earlier; cross-check only. |
| Ferguson Hill (fergusonhill.co.uk; Hifi Pig; audioXpress; New Atlas) | The only audio "Ferguson": transparent acrylic front-loaded **parabolic** horns | **snippets only** → **[unverified-today]**; no geometry/roll math. |
| **"FH-N2"** | — | **NOT FOUND.** Bing + Brave (2026-10-25) return furniture/bookcases/Noctua only; no loudspeaker-horn hit in the searched indexes. **[open]** |
| "Ferguson" as a horn typology | — | **NOT FOUND** beyond Ferguson Hill. No builder/patent/paper with a toroidal profile in the searched indexes. **[open]** |
| Iwata / Tsutomu Iwata primary (patent/paper) | — | **NOT FOUND.** The name resolves only to the Auto-Tech product in the searched indexes. **[open]** |

## 2. Per-typology dossier

### 2.1 Elliptical JMLC (E-JMLC / "spade")

**(a) Construction math — none published.** Fourcade covers the axisymmetric case only ([verified] text search). Le Cléac'h's
own statement (in-repo §9b.0, forum **[unverified-today]**) is that non-axisymmetric versions were produced as 3-D point clouds /
spreadsheets (>100 MB), i.e. geometry, not a paper. The commercial form is Auto-Tech's **E-JMLC** family, and its datasheet is
the only published quantitative record:

> "E-JMLC-300 (Minimal frequency from 500 Hz) … Ø50.8 mm … 430 mm … 330 mm … 920 mm" — dimensions on the drawing: throat,
> depth, mouth height, mouth width. Measured: 10°-step polars (500 Hz–20 kHz) and a **horizontal** directivity sonogram
> (0 to −25 dB). [published, datasheet]

There is **no published `fc(φ)` law**. The repo's T3 law `1/fc(φ) = cos²φ/fc_h + sin²φ/fc_v` is therefore **un-attributed
practice**, not a citation — exactly as the WP9 grounding's labeled-experiment policy already treats it. A cosine-compliance
interpolation of cutoff is dimensionally sensible [inferred] but must not ship as "JMLC's formula".

*Numerical plausibility [inferred, our exact march]:* for a 2" throat, φ0 = 5°, T = 0.8, stop = 180°, the T1 mouth width is
inversely proportional to fc with **width·fc ≈ 187,200 mm·Hz** (fc 200/250/300 → 935/748/624 mm; spread < 0.1 %). The
datasheet's 920 × 330 mouth therefore corresponds to **fc_h ≈ 203 Hz, fc_v ≈ 567 Hz**. Those two meridians would be ~525 mm
and ~188 mm deep, so the single published 430 mm depth is neither: it is one dimensioned station of a saddle, not a
validation scalar. The photo's 36° included at 10 kHz is a *measured coverage*, not a cutoff.

**(b) Practitioner terms.** Wider horizontal sweet spot and roughly twice the HF dispersion of a round JMLC (forum snippets
**[unverified-today]**); "not necessarily directive below ~8 kHz but very directive above 8 kHz with a 2-inch driver"
(homecinema-fr snippet). Cost: two different flare scales in one body, a deep side roll (surface, thin outer gaps), and a mouth
that is hard to build. The side lobes are where the roll goes deepest — the "spade".

**(c) Knobs.** `fc_h`, `fc_v` (ratio 1.5–3.0), `T`, per-azimuth `stop` (same angle vs same `L0`), wall offset, and the choice
of interpolation law. **[inferred]**

**(d) Ranking/measurement.** 10° polars to ±80/90° and the horizontal sonogram; the sheet's 10 kHz included angles
(EJMLC 36° > Iwata 24° > JMLC 18°) rank the same way as the practitioner reports. **[photo-derived, unverified]**

### 2.2 Iwata / quasi-Iwata / "FH-N2"

**(a) Construction math — the original is closed; only the principle is published.** The commercial horn sold as
**IWATA-300** (Auto-Tech) publishes:

> "IWATA-300 (Minimal frequency from 450 Hz) … Ø50.8 mm … 450 mm … 320 mm … 590 mm" (throat, depth, mouth height, width),
> with 10°-step polars 200 Hz–20 kHz and a horizontal sonogram. [published, datasheet]

Le Cléac'h's "quasi-Iwata" is the only attributable description of a construction (in-repo §9b.0, forum): it keeps the
original Iwata's width/height-ratio evolution throat→mouth and **T = 0.5** **[unverified-today]**. Our T4
`AR(l) = AR_t + (AR_m − AR_t)(l/L0)^p` with an area-preserving stretch is **our reconstruction**, not Iwata's law.

*Numerical fingerprint [inferred, our march]:* the invariant is the **depth/width ratio**. IWATA-300 is 450/590 = **0.76**;
a T1 at T = 0.5 matched to 590 mm width (2" throat, φ0 5°, stop 180°) is 358/590 = **0.61**, and at T = 0.8 it is 326/590 =
0.55. Even allowing ~50 mm of the product depth for the throat adapter, its ratio is 0.68 — still well above the T1. So the
original Iwata is a **different, deeper flare**, not a stretched JMLC; JMLC's quasi-Iwata approximates the *look and ratio*,
not the profile.

**"FH-N2" is unresolved.** No audio source uses the string (Bing, Brave; 2026-10-25). The vision lane's dimensioned variant
(Ø25.4 mm throat; 245/290/185 mm) is therefore a **[photo-derived]** reference only; the lane did not record which callout is
width, height or depth, so do not hard-code that mapping. It is a small 1" horn with those three external callouts, which the
T3/T4 knobs can describe; **do not ship the name "FH-N2".**

**(b) Practitioner terms.** Iwata keeps most of the JMLC loading with closer driver spacing (forum snippet); a builder's
3D-printed Iwata-300 replica is reported to "ring like a bell" (diyAudio ATH-thread snippet). Quasi-Iwata trades some of the
JMLC mouth smoothness for the AR look.

**(c) Knobs.** `T = 0.5` (the one hard convention), `AR_t ≈ 1`, `AR_m = 1.8–2.8`, exponent `p = 0.5–2`, superellipse `n(l)`,
`stop`, throat adapter. **[inferred]**

**(d) Ranking/measurement.** 10° polars and horizontal sonogram (published); usable band from ~1.5× the model number
(300 → 450 Hz). The 24° at 10 kHz sits between the EJMLC and the JMLC. **[photo-derived]**

### 2.3 Ferguson / toroidal roll

**(a) Construction math — none.** No horn paper, patent, or builder's formula was found. The only audio "Ferguson" is
**Ferguson Hill** (UK): transparent acrylic, front-loaded, described as a "parabolic horn" (Hifi Pig) and as "the world's
first-ever front-loaded horn dipole loudspeaker" (audioXpress) — **snippets, [unverified-today]**. No profile equation or lip
radius is published. So "Ferguson" is a **product/shape reference, not a typology with math** [searched, none found].

The owner photo's fully-rolled toroidal lip is therefore best modelled as **T1 (verified meridian) + an explicit lip
structure**: either the natural curl continued to ~360°, or a torus of tube radius `r_lip` centred on the mouth rim. Our T7
("toroidal_rollback") is exactly this **[inferred]**, not a Ferguson reproduction.

*Numerical consistency [inferred, our march]:* the JMLC-350 product (below) has a Ø595 mouth while the T1 meridian at
fc 350 / T 0.8 / 2" throat / stop 360° is 536 mm wide; a lip tube of r ≈ 30 mm gives 536 + 60 = **596 mm** — the published
Ø595. This is *consistent with* (not proof of) T1 + a fat toroidal lip; the product's actual fc/T/stop are unpublished, so
treat it as a plausibility check.

**(b) Practitioner terms.** The roll removes the sharp mouth edge (smooth impedance, weak edge diffraction) and stiffens the
mouth, at the cost of a large surface and a thin cavity between roll and outer shell. The 110 mm span between the JMLC-350's
outermost stations (325→435 mm) gives the scale of the lip/adapter structure (station semantics are unlabelled).

**(c) Knobs.** `stop` (180–360°), `r_lip` (20–35 mm), lip centre offset, wall thickness, outer-shell gap.

**(d) Ranking/measurement.** No published numbers beyond the product dimensions; judge by mouth reflection/ripple and DI.

### 2.4 JMLC-350 uniform-roll (cross-ref T1)

Construction **[inferred]** = **`lecleach_exact` (verified, T1 dossier)** + the toroidal lip of 2.3. Published product
(Auto-Tech JMLC-350):

> "JMLC-350 (Minimal frequency from 520 Hz) … Ø595 mm … 435/382/372/325 mm … Ø25.4 / Ø35.8 / Ø38.1 / Ø50.8 mm" (mouth,
> four axial stations, throat-adapter options), 10° polars and sonogram to 20 kHz. [published, datasheet]

So the photos' "JMLC-350 with a uniform tube-rolled lip" is consistent with the verified construction **plus** a lip; the
model number is the design cutoff, the usable band starts at ~1.5× it (520 Hz). The four axial stations are not reproducible
from the meridian alone (the datasheet includes the throat adapter and the rolled ring, and their reference points are
unlabelled) — **do not use 435 mm as a pass/fail number**; the Ø595 diameter is the usable check.

### 2.5 Up/down-asymmetric saddle (photo 2 and the "end-hooks") — **[inferred]**

No published asymmetric-per-azimuth construction exists (searched: none). The construction class is ours:

- Let φ be the mouth-plane angle measured from the **horizontal** axis (+x), so a point is (r cos φ, r sin φ). Left-right
  mirror is x→−x, i.e. **φ→π−φ**; up/down mirror is y→−y, i.e. φ→−φ. The functions invariant under left-right mirror are
  **{cos 2kφ, sin(2k+1)φ}**.
- `cos 2φ`, `cos 4φ`: invariant under **both** mirrors → the existing quarter model stays valid (this is the EJMLC "deepest
  at the sides" term, max at φ = 0, π).
- `sin φ`, `sin 3φ`: left-right symmetric, **up/down antisymmetric** → **half model** (these are the end-hook /
  top-vs-bottom terms; `sin φ` is the vertical direction).
- A **vertical** mouth bend is `x += b·sin φ` (half model); a **lateral** bend/twist is `x += c·cos φ` (breaks left-right
  mirror → full model).

> Terminology note (C2): in this convention the **quarter**-symmetric set is the **even-order cosines**, while the
> **half-model** asymmetry is carried by **odd-order sines**. So "even harmonics" names the quarter terms, not the half-model
> terms; the φ origin and the basis must be pinned in the GRID row builder. (If φ is measured from the vertical instead, the
> roles swap — another reason to pin it.)

*Numerical example [inferred, our march]:* 1" throat, fc_h 800 / fc_v 1200 Hz, T 0.8, `stop(φ) = 180° + 20°·sin φ` gives a
~235 mm-wide mouth whose top is rolled to 200° and bottom to 160° around the 158 mm symmetric height; `cos 2φ` is the
side-depth term instead. Both keep left-right mirror exactly.

### 2.6 Best published parameter versions (what our defaults should imitate) — **[inferred from the line card]**

- **JMLC**: the 300–400 class for 2" drivers (JMLC-350: Ø595, 435 mm, full roll, min 520 Hz); the 600 class when a 1" build
  must be smaller. The line spans 200T/270/350/400/600/1000/1400/2000 — the model number is the design fc, and the 350/600
  accept 1"–2" adapters.
- **E-JMLC**: E-JMLC-300 (920 × 330 × 430, 2" throat) is the widest published; for a 1" brief use the 600+ class or scale the
  mouth to the envelope. Min frequency ≈ 1.5–1.7× the model number.
- **IWATA**: IWATA-300 (590 × 320 × 450, 2" throat, min 450 Hz) for 2"; IWATA-200/600 for smaller throats. T = 0.5, AR_m ≈
  1.8 (590/320), depth/width ≈ 0.76.
- **Ferguson / asymmetric**: no published parameter versions — photo-derived only.

## 3. Hybrid recipe and the knob surface for the GRID rows lane

Practitioner hybridisation, from the sources above plus the in-repo ETF Min-Phase evidence (pp.125–127): (i) **JMLC × OS**
(Gerstgrasser Min-Phase: an OS waveguide whose mouth curls early) — the in-repo construction is a valid template; (ii) **AR
stretch of a JMLC meridian** (quasi-Iwata, T = 0.5) — our reconstruction; (iii) **per-azimuth hybrids** (JMLC throat, different
mouth law per azimuth) — our class, no published formula. What practitioners tune is exactly `fc` (the model number), `T`
(0.5 or 0.8 dominant), the **roll/stop** (mouth diameter and how far it curls), the **aspect ratio** (elliptical/Iwata), and
the throat adapter; what they show is 10° polars and a sonogram to 20 kHz plus a "minimum frequency".

| Our knob (GRID rows) | Effect | Ships under |
|---|---|---|
| `fc_hz`, `T`, `stop_deg`, `dl_mm` | the verified T1 meridian | **verified-exact** (`lecleach_exact`) |
| `fc_h_hz`, `fc_v_hz` + law selector | per-azimuth cutoff; the saddle | **our reconstruction [inferred]** (no published law) |
| `stop0_deg` + `stop_cos2k`, `stop_sin2k1` | side depth (`cos 2φ`, quarter) / end-hooks (`sin φ`, half) | **hypothesis [inferred]** |
| `ar_t`, `ar_m`, `p`, `n_exp` | quasi-Iwata AR evolution and mouth squareness | **our reconstruction** of a published *principle* |
| `r_lip_mm`, `lip_offset_mm`, `stop ≥ 180` | toroidal roll | **inferred** geometric analogue (T7) |
| `bend_sin1_mm` (vertical) / `bend_cos1_mm` (lateral) | axial bend; the latter breaks LR mirror | **hypothesis**; lateral = full model |
| `half_model` (`quadrants="14"`, plane yz, x ≥ 0) | left-right mirror only; **2× the quarter dofs** | use for all five photos; full model only for `cos φ` / `sin 2φ` terms. Axis convention: "profileH is the horizontal meridian (x), profileV the vertical one (y)" (`registry.py:387`), so the left-right mirror is x = 0 → yz. |

Naming (R9 discipline): `lecleach_exact` (verified), `salmon_elliptical`, `iwata_ar`/`quasi_iwata`, `toroidal_rollback`,
`saddle_asym` — never "FH-N2", "Ferguson", or "EJMLC" as a verified name. Attribution is moot for the owner, but the *numbers*
are not: only the T1 meridian has a published reference case.

## 4. Validation plan (beyond the T1 table)

1. **Keep R9-J for `lecleach_exact`** (T1 dossier): mouth width ≤ 0.5 mm; L0/length ≤ 1 mm; S ≤ 2 %; throat angle ≤ 0.1°.
2. **Torus-lip invariant** (unit): outer mouth diameter = 2·(max y + r_lip) exactly; total depth = max x + lip_offset for a
   ring centred on the mouth plane. Check against the **JMLC-350 Ø595** (r_lip ≈ 30 mm on the fc 350 / T 0.8 / 2" meridian
   gives 596 mm, 0.2 %). Band: ±3 mm. Label: plausibility check, not a published profile.
3. **Aspect law** (unit): with `fc_h = fc_v` the elliptical rows equal the axisymmetric rows at every φ (≤ 1e-9 mm); the mouth
   axes satisfy `W·fc_h = H·fc_v` within ~2 % (the product is ~1.87 × 10⁵ mm·Hz at 2" throat, ~1.88–1.90 × 10⁵ at 1").
4. **Iwata fingerprint** (report-only): at matched mouth width the T1 is 0.80× (T = 0.5) or 0.72× (T = 0.8) the IWATA-300
   depth. A build that claims "Iwata" must therefore *not* pass a T1-depth test. This is a guard against mislabelling, not a
   validation.
5. **Asymmetry** (unit): `cos 2φ` terms leave left-right mirror at 1e-9 and keep top/bottom equal; `sin φ` terms leave
   left-right mirror at 1e-9 and make top≠bottom; `cos φ` fails the mirror check (full model expected). Half-model solve
   equals the full model on a coarse mesh (≤ 0.1 dB, report-only).
6. **1" brief ranges** (our march, stop 180°): fc 800/800 → 235 × 235 mm, 114 mm deep; 800/1200 → 235 × 158 mm, 114/58 mm;
   600/1000 → 312 × 189 mm, 178/79 mm. Envelope 520 × 420 × 260 mm fits fc ≥ 600 comfortably; use fc_h 600–1200,
   fc_v 800–1600, T 0.5–0.8, stop 120–240°, r_lip 6–12 mm. **[inferred]**
7. **Published tables are images, not columns**: the Auto-Tech polars/sonograms can be digitised later; do not claim a
   numerical match to them today. **[verified absence of text tables in the PDFs]**

## 5. Open items, corrections, honesty

- **C1 (2026-10-25):** the plan groups "Iwata/FH-N2" and "Ferguson/toroidal" as if both had published constructions. They do
  not: Iwata has a *principle* (AR evolution + T=0.5) and a commercial datasheet; "Ferguson" has neither, and "FH-N2" is an
  unattested string. Ship them as neutral reconstructions/hypotheses, not as named reproductions.
- **C2:** half-model vocabulary — see the terminology note in 2.5. In the horizontal-origin convention the quarter set is the
  even-order **cosines** and the half-model asymmetry is the odd-order **sines**; the work order's "even harmonics" therefore
  names the quarter terms. This is a correction to that wording, not to the photo reading.
- **Open [unverified-today]:** all diyAudio quotes and Ferguson Hill claims (forum Cloudflare-blocked; Internet Archive
  offline this session); the JMLC 3-D spreadsheets/point clouds (never public); AxialHorn internals (T1 dossier).
- **Open [searched, none found]:** no published per-azimuth `fc(φ)` law, no published asymmetric-stop law, no published
  torus-lip math, no primary Iwata source, no "FH-N2".
- **What would close them:** a copy of JMLC's elliptical point-cloud/spreadsheet, an Auto-Tech design note, or a builder's
  measured E-JMLC surface. Until then the labels in §3 stand.
