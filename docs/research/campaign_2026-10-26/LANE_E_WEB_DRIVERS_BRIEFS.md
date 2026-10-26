# Outside web research — horn/driver briefs for the BEM design search campaign

Saved 2026-10-26 from Lane E (@librarian). Every claim below is from a manufacturer page or
published design page with its source URL; derived numbers are marked *(calc.)*. Driver exit
angles are the least-published parameter — treat angle rows as low-confidence.

## Scope/method note
All numbers come from manufacturer pages or published design pages. JBL 2446/2450 and JBL
PT/VTX datasheets could not be retrieved (site/login restrictions); no primary source for
"Salmon" X-shape horns was found.

## 1. Compression drivers

### 1-inch exit (r0 = 12.7 mm)

| Driver | Exit | VC / diaphragm | Min XO | Sens. | Power | Source |
|---|---|---|---|---|---|---|
| B&C DE250 | 25 mm | 44 mm polyimide | 1.6 kHz | 108.5 dB | 60/120 W | [S1] |
| BMS 5530ND | 25.4 mm | 44.4 mm polyester ring | 1.0 kHz (850 Hz with close spacing) | 113 dB | 80 W AES / 450 W pk | [S2] |
| 18 Sound ND1090 | 25 mm | 44 mm Ti-PEN | 1.6 kHz | 110 dB | 50/100 W | [S3] |
| Celestion CDX1-1745 | 25 mm | 44 mm PETP | 2.2 kHz | 110 dB | 40/80 W | [S4] |

All round-exit; none publishes exit taper. AudioHorn states the best 1-inch drivers reach a
~950–1000 Hz low limit [S5]. **A 1-inch driver is not credible on a 60×40 PA horn crossed at
800 Hz** — closest (BMS 5530ND) is rated 1 kHz; ND1090 1.6 kHz; CDX1-1745 2.2 kHz [S2–S4].
Displacement demand rises as 1/f²; 800 Hz needs ~4× the excursion of 1.6 kHz *(calc.)*.

### 1.4-inch exit

| Driver | Exit | VC / diaphragm | Min XO | Sens. | Power | Source |
|---|---|---|---|---|---|---|
| B&C DE800 | 36 mm | 75 mm Ti/composite | 1.2 kHz | 108 dB | 110/220 W | [S6] |
| 18 Sound ND1460 | 35 mm | 75 mm Ti | 0.8 kHz | 109 dB | 100/200 W | [S7] |
| 18 Sound ND1480 | 35 mm | 75 mm Ti | 0.8 kHz | 110 dB | 100/200 W | [S8] |
| BMS 4594ND | 36 mm | 3.5″ mid + 1.75″ HF | **300 Hz** | 118 dB (40×20 horn) | 150 W + 80 W | [S9] |

"1.4 inch" is **not one dimension**: 35 mm (17.5 mm radius, 18 Sound) vs 36 mm (18.0 mm,
B&C/BMS) [S6–S9]. The brief must state which.

**B&C naming corrections:** DE750 is a **2-inch exit** and DE950 is a **2-inch exit** (archived
pages) [S10, S11]; DE800/DE900 are the 1.4-inch models [S6]; DE900's archived page carries no
usable specs.

### 2-inch exit

| Driver | Exit | VC / diaphragm | Min XO | Sens. | Power | Source |
|---|---|---|---|---|---|---|
| B&C DE1050 | 50 mm | 100 mm Ti | 0.8 kHz | 109 dB | 140/280 W | [S12] |
| 18 Sound ND4020Ti2 | 51 mm | 100 mm Ti | 0.8 kHz | 113 dB | 160/320 W | [S13] |
| BMS 4592ND | 50.8 mm | 3.5″ + 1.75″ | **300 Hz** | 118 dB | 150 W + 80 W | [S14] |
| Celestion Axi2050 | 50 mm | 125 mm Ti | 300 Hz (300–20k band) | 108 dB | 150/300 W | [S15] |

Size alone does not buy low crossover: DE1050 and ND4020Ti2 are 4-inch-coil 2-inch drivers but
rated 800 Hz [S12, S13]. Only the two-way/annular designs (BMS 4592/4594, Axi2050) are rated to
300 Hz [S9, S14, S15]. A 300–400 Hz B3 is therefore a **driver-family** decision, not a generic
"large format" one.

### Exit angles (scarce; low confidence)
- AudioHorn (measures/uses these drivers): TAD TD-4002/4003 ≈ 4–4.5° **semi-angle** (8–9°
  included); JBL 2450SL **0° flare**; most "2-inch" drivers are actually 1.5-inch drivers with
  built-in adapters [S5].
- ATH throat angles: TwinRay 1-inch **12° total (6° half)**; 1.4-inch **4° total (2° half)**;
  2-inch and 1.5-inch **0°**; CORE 2-inch **a0 = 1.2°** [S16, S17]. ATH sells a 1-inch unit with
  **10° total (5° half)** [S16].

**What to pin:**
- **1-inch:** r0 = 12.7 mm, a0 = **5–6° half** (ATH uses 5° and 6°) [S16]. 5° acceptable; no wider.
- **1.4-inch:** r0 = 17.5 or 18.0 mm, a0 = **2–3° half**. A 5° half is too fast for the drivers
  ATH/AudioHorn target (ATH 2°, TAD class 4–4.5° semi-angle) [S5, S16].
- **2-inch:** r0 = 25.4 mm, a0 = **0–1.2° half** (JBL 2450SL 0°, ATH 0°, CORE 1.2°) [S5, S16, S17].

## 2. Are the briefs representative?

### Real horns (published data)

| Product | Coverage | Mouth W×H×D (mm) | Rated LF | Driver |
|---|---|---|---|---|
| B&C ME90 | 80×60 | 270×270×138 | 0.9 kHz | 1.4″ [S18] |
| 18 Sound XR1496C | 90×60 | 270×270×180 | 0.8 kHz; CD to 1.2 kHz | 1.4″ [S19] |
| 18 Sound XR1464C | 60×40 | 270×270×180 | 0.8 kHz; CD to 1.2 kHz | 1.4″ [S20] |
| 18 Sound XR1064 | 60×40 | 210×210×110 | 0.8 kHz; CD to 1.6 kHz | 1″ [S21] |
| B&C ME60 | 60×40 | 270×237×202 | 0.8 kHz | 2″ [S22] |
| B&C ME45 | 90×40 | 310×140×124 | 1 kHz | 1″ [S23] |
| JBL M2 | 120×100 | 508 mm-wide enclosure | 800 Hz XO | 1.5″ D2 [S28] |
| ATH TwinRay 36-04-266 | const-H, narrowing V | 266×212×130 | 20 % Re at 680 Hz | 1.4″ [S16] |
| ATH TwinRay 36-10-380 | const-H, narrowing V | 380×303×192 | 20 % Re at 580 Hz | 1.4″ [S16] |
| Azurahorn AH-550 | circular, fc-defined | Ø300×205 | fc 550 Hz | 1″ [S30] |
| Azurahorn AH-340 | circular, fc-defined | Ø600 (full rollback)×405 | fc 340 Hz | 2″ [S30] |
| Danley SH50 | 50×50 | 711×711×648 | 50 Hz–18 kHz | 1″+4×4″+2×12″ [S29] |

### The K-law, checked
`d = 25.4e6/(f·θ)` is algebraically **1.16–1.29× the λ/(2 sin(θ/2)) criterion** *(calc.)*: 1.16
at 90°, 1.23 at 60°, 1.27 at 40°. So it is a deliberately conservative mouth rule, not a physical
law. Manufacturer "cutoff" is a **loading** number; published **pattern-control** frequency is
higher and matches λ/(2 sin(θ/2)) in the horizontal plane:
- XR1064: 210 mm at 60° → 1.63 kHz predicted, **1.6 kHz published** [S21].
- XR1464C: 270 mm at 60° → 1.27 kHz predicted, **1.2 kHz published** [S20].
- XR1496C: 270 mm at 90° → 0.90 kHz H predicted, **1.2 kHz published** [S19].

Vertical dimensions in PA horns are routinely *smaller* than the rule (accepted vertical
narrowing). Conclusion: **the K-law is consistent with λ/(2 sin) plus ~20 % margin, but
manufacturers' "cutoff" ratings sit 1.3–2× below true pattern control.**

### B1 (90×60, 850 Hz, 1.4″, 332×498)
Keele requirement at 850 Hz: 285×403 mm; the brief is 1.16×/1.24× that *(calc.)* — **realistic
and slightly conservative**. JBL M2 holds 120×100 to 800 Hz in a 508 mm-wide box [S28]; ATH/
AudioHorn 1.4-inch designs work at 700–850 Hz [S16, S24]. A 498 mm-tall mouth is large
domestically but defensible; 180–240 mm depth matches ME90/XR1496C/TwinRay (130–180 mm) plus
margin.

### B2 (60×40, 800 Hz, 1″, 529×794)
Keele at 800 Hz: 429×627; the brief is 1.23×/1.27× — internally consistent. But **no real 60×40
PA horn is remotely this big**: 210×210 (1″) and 270×270 (1.4″), holding 60×40 only to 1.6/1.2
kHz [S20, S21]. B2 as drafted is a "true-pattern" horn, not a representative PA horn, at ~2.5–3.8×
the linear size of production parts — and the 1-inch/800 Hz pairing is not credible. A 1.4-inch
driver is the minimum for 800 Hz PA use.

### B3 (low reach)
- **Option A** (90×90, 400 Hz, 706 mm square): K-law exact (Keele 606) *(calc.)*; 706 mm =
  0.82 λ₄₀₀, so it **loads** to 400 but true 90×90 **pattern** holds only above ~480–500 Hz.
- **Option B** (90×60, 600 Hz, 471×706): K-law consistent; a 1.4-inch BMS 4594ND is rated 300 Hz
  [S9], so "loading to ~400" is achievable. For scale, a genuinely 400 Hz-capable 50×50 PA box is
  the 711 mm SH50 with **seven** transducers [S29]; a single-driver 400 Hz horn must be at least
  this large.

### Recommended final briefs

| | Coverage | f0 | Mouth W×H×D | Driver / r0 / a0 | Band |
|---|---|---|---|---|---|
| **B1 hi-fi** | 90×60 | 850 Hz | 332×498×200 | 1.4″, r0 18.0, a0 2.5° | 700–8000 |
| **B2 PA** | 60×40 | **1.2 kHz** | 280×400×170 | 1.4″, r0 17.5, a0 2.5° | 1.2k–8000 |
| **B2′ (if 800 Hz mandatory)** | 60×40 | 800 Hz | 430×630×260 | 1.4″ large-format or 2″ | 800–8000 |
| **B3 (recommended)** | 90×60 | 600 Hz | 470×700×320 | BMS 4594ND 1.4″ (r0 18, a0 2°) or 4592 2″ (r0 25.4, a0 0°) | 400–8000 |
| **B3-alt** | 90×90 | 450 Hz | 630×630×380 | 2″, r0 25.4, a0 0–1.2° | 400–8000 |

## 3. Typology fit
- **Le Cleac'h** — defined by **fc and T**, not coverage; Azurahorn's catalogue is
  160/204/340/425/550/1100/1200 Hz with Ø300 mm for 550 Hz and Ø600 mm for 340 Hz [S30, S31].
  Incompatible with "90×60 at 850" as a specification; fits B1 only as a low-cutoff hi-fi horn
  (cost: size + pattern control), and B3 only if coverage is subordinate to loading.
- **OSSE / R-OSSE / TwinRay (ATH)** — parametric, BEM-optimised, low diffraction; TwinRay
  deliberately gives constant H and **narrowing V** [S16]. Good for **B1**; wrong for **B2**
  (no true 40° V).
- **ATH CORE** — 2-inch, L = 260 mm, a0 = 1.2°, rounded-rect mouth morph [S17]. Natural fit for
  **B3** with a 2-inch driver.
- **X-Shape (AudioHorn)** — claims CD on both axes with diagonal ≈ horizontal, rectangular
  mouth; 1.4-inch versions recommended at 650–800 Hz XO [S24]. Fits **B1** and B3's 1.4-inch
  version. Numeric coverage angles not published (flag).
- **Keele-style biradial / CD PA** (ME90, XR series, BMS 2119/2236 horns) — the correct family
  for **B2** [S18–S22, S32].
- **Danley Synergy** — the real solution for a 400 Hz ~90×90 box, but multi-entry and outside a
  single-driver BEM search [S29].
- **Freeform/sculpted** — B1 aesthetics; expensive to parameterise and mesh.
- **"Salmon/X-shape rollback"** — no primary documentation found; AudioHorn X-Shape is the only
  verified "X-shape" (full round-over mouth return) [S24]. Flag as unverified.

## 4. Throat impedance / loading
Normalised throat impedance z = Z_throat/(ρc/S_throat); a plane wave gives Re(z) = 1. There is
**no industry threshold**. ATH's published convention: its "low-frequency point" is where **throat
acoustic resistance reaches 20 % of its asymptotic value** [S16]. A 0.5 target is a common rule of
thumb with no manufacturer publishing it — treat as convention, not standard (flag).

Empirically from ATH's own designs *(calc. from [S16])*: 266×212 mouth (perimeter 956 mm) → 20 %
at 680 Hz = 1.90 λ; 380×303 (1366 mm) → 580 Hz = 2.31 λ; 1-inch 266×212 → 920 Hz = 2.56 λ. So
**20 % loading occurs at perimeter ≈ 1.9–2.6 λ**. Le Cleac'h products land in the same range:
AH-550 Ø300 at 550 Hz = 1.51 λ; AH-425 Ø420 = 1.63 λ; AH-340 Ø600 at 340 Hz = 1.87 λ [S30] *(calc.)*.

Applying the scaling:
- **B1** perimeter 1660 mm → 20 % Re at ~450–500 Hz; ~50 % by 600–700 Hz → 850 Hz safely loaded.
- **B2** perimeter 2646 mm → 20 % at ~280–330 Hz → grossly over-loaded for an 800 Hz horn
  (further evidence of oversizing).
- **B3** 706 mm square, perimeter 2824 mm → 20 % at ~270 Hz, ~50 % around 370–400 Hz → the
  "loads to 400 Hz" claim is defensible but only just at the 50 % level; depth ≥ 350 mm and a
  300 Hz-rated driver required [S9].

Mouth size and cutoff decouple: use **perimeter ≈ 2 λ(f_20%)** for the loading target and
**d = λ/(2 sin(θ/2))** for the pattern target, then check the driver's rated XO is above f_20% [S16, S20, S21].

## Sources
- [S1] https://www.bcspeakers.com/en/products/hf-driver/1/8/DE250
- [S2] https://bmsspeakers.com/product/1-high-frequency-neodymium-compression-driver-5530nd/
- [S3] https://www.eighteensound.it/en/products/hf-driver/1-0/8/ND1090
- [S4] https://celestion.com/product/cdx1-1745/
- [S5] https://audiohorn.net/guide/compression-driver/
- [S6] https://www.bcspeakers.com/en/products/hf-driver/1-4/8/DE800
- [S7] https://www.eighteensound.it/en/products/hf-driver/1-4/8/ND1460
- [S8] https://www.eighteensound.it/en/products/hf-driver/1-4/8/ND1480
- [S9] https://bmsspeakers.com/product/1-4-coaxial-neodymium-compression-driver-4594nd/
- [S10] https://www.bcspeakers.com/en/products/hf-driver/1-4/8/DE750
- [S11] https://www.bcspeakers.com/en/products/hf-driver/2/8/DE950
- [S12] https://www.bcspeakers.com/en/products/hf-driver/2/8/DE1050
- [S13] https://www.eighteensound.it/en/products/hf-driver/2-0/8/nd4020ti2
- [S14] https://bmsspeakers.com/product/2-coaxial-neodymium-compression-driver/
- [S15] https://celestion.com/product/axi2050/
- [S16] https://at-horns.eu/twinray.html
- [S17] https://at-horns.eu/core.html
- [S18] https://www.bcspeakers.com/en/products/horn/1-4/8/ME90
- [S19] https://www.eighteensound.it/en/products/horn/1-4/0/XR1496C
- [S20] https://www.eighteensound.it/en/products/horn/1-4/0/XR1464C
- [S21] https://www.eighteensound.it/en/products/horn/1-0/0/XR1064
- [S22] https://www.bcspeakers.com/en/products/horn/2/0/ME60
- [S23] https://www.bcspeakers.com/en/products/horn/1/0/ME45
- [S24] https://audiohorn.net/x-shape-horn/
- [S25] https://audiohorn.net/test/compression-driver/1.4inch/
- [S26] https://audiohorn.net/sciences/horn-acoustic-loading/
- [S27] https://at-horns.eu/
- [S28] https://jblpro.com/en/products/m2
- [S29] https://www.danleysoundlabs.com/products/sh50/
- [S30] https://web.archive.org/web/20210211221930/http://www.azurahorn.com/azurahorn_horns.html
- [S31] https://web.archive.org/web/20210125032113/http://www.azurahorn.com/
- [S32] https://bmsspeakers.com/products/horns/

## Uncertainties
Driver exit angles are vendor/community statements, not datasheet values. B&C DE750/DE900/DE950
pages are archived with almost no specs. JBL 2446/2450 and JBL PT/VTX data were not retrievable.
X-Shape's numeric coverage and "Salmon" horns are unpublished/unverified. The 50 %-Re loading
threshold and all derived perimeter/λ scaling are engineering estimates, not quoted standards.