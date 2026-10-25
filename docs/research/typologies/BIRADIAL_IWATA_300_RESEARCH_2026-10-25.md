# Biradial horns + Iwata 300 - research dossier (2026-10-25)

Lane: `hornlab-typology-research` Phase A, biradial/Iwata line. Read-only recon of the repo; all
external claims carry a label or a URL. Date: 2026-10-25.

Labels used below:

- **[verified]** - read in a fetched source this session (or re-derived arithmetically and shown).
- **[inferred]** - our derivation from fetched material, with the derivation shown.
- **[measured]** - a number this session computed from published numbers (the arithmetic is printed).
- **[unverified]** - source unreachable today, or a single unconfirmed report.
- **[unverified-today]** - quoted from repo memory; the live source was blocked this session.

Units: mm, Hz, degrees. "Included angle" means the full wall-to-wall angle (double the half-angle),
matching the patent's own usage.

---

## 1. Inventory: what the repo already claims about biradial and Iwata

Grep scope: `docs/`, `design/`, `examples/` (case-insensitive), plus `hornlab_search/` for the rows
kinds. Findings, with file:line.

### 1.1 "biradial" / "bi-radial" - one paragraph in the senior pass, nothing else

| file:line | What it says | Verdict |
|---|---|---|
| `docs/research/senior_pass_2026-10-24/appendix_A_typology_survey_raw.md:152` | "D.B. Keele Jr. introduced the constant-directivity (CD) horn concept while at Electro-Voice (1975 AES paper ...), later developing the BiRadial(R) for JBL." Source cited: Wikipedia (D.B. Keele Jr.). | **Attribution is already right, but the source is tertiary and there is no construction.** Also the parenthetical "(1975 AES paper)" attaches the CD paper to the BiRadial work; the patent (found today) is 1980. |
| `.../appendix_A_typology_survey_raw.md:162` | Mantaray (Altec) "uses a diffraction slot on the H-axis only ... Provides more symmetric H x V coverage than EV's original biradial". | Secondary comparison; no geometry. |
| `.../appendix_A_typology_survey_raw.md:436` | Source-table row "Keele CB horn / Biradial - Wikipedia". | Confirms the repo only had a tertiary source. |

There is **no** biradial construction, math, knob set, reference case or measurement basis anywhere in
the repo. This dossier is the gap-fill.

### 1.2 "Iwata" - substantial coverage, but only as a *principle* + one datasheet

| file:line | What it says | Verdict |
|---|---|---|
| `docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md:61-92` | Section 2.2 "Iwata / quasi-Iwata / FH-N2": IWATA-300 datasheet numbers (50.8 throat, 450 deep, 320 high, 590 wide, min 450 Hz); Le Cleac'h's quasi-Iwata principle (AR evolution + T=0.5) **[unverified-today]**; our T4 reconstruction `AR(l) = AR_t + (AR_m - AR_t)(l/L0)^p`; depth/width fingerprint 0.76 vs 0.61/0.55 for T1. | **Cite this, do not redo it.** It is the repo's canonical Iwata record. |
| `.../JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md:25` | "Iwata / Tsutomu Iwata primary (patent/paper) - NOT FOUND." | Still true today (see section 10); we add no primary. |
| `.../JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md:196-198` | Iwata fingerprint: a T1 at matched width is 0.80x (T=0.5) / 0.72x (T=0.8) the IWATA-300 depth; a build claiming "Iwata" must not pass a T1-depth test. | Good anti-mislabelling guard; reuse. |
| `.../JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md:210-219` | C1 correction: "Iwata has a *principle* ... and a commercial datasheet", not a published construction. | Binding for any Iwata work. |
| `docs/research/typologies/WP9_WP9B_GROUNDING_2026-10-25.md:83` | Iwata-style AR law is a labeled reconstruction, not the blocked exact construction. | Consistent. |
| `docs/INDEX.md:44` | Index line pointing at the JMLC-variants dossier, including IWATA-300. | Discovery path for the owner. |

### 1.3 The shipped code surface (no biradial; `iwata_ar` exists)

| file:line | Fact |
|---|---|
| `hornlab_search/design/generators/grid.py:129` | `ROWS_TYPES = ("salmon_elliptical", "salmon_axisym", "lecleach", "iwata_ar", "toroidal_rollback", "lecleach_mod", "lecleach_ar")`. **Seven kinds. There is no `salmon_x_shape` or `salmon_saddle` kind here** - the lane brief's list is stale on that point (their catalog entries were removed: `docs/evidence/M4_SMOKE_2026-10-25.md:198`). |
| `grid.py:103` | `iwata_ar` = "verified march + AR stretch `ar_m` / `ar_p` (T pinned 0.5 in config)". |
| `grid.py:201` | `iwata_ar` task knobs `g_ar_m` / `g_ar_p` over the AR profile helper. |
| `grid.py:1385-1416` | `_rows_iwata_ar_knobs`: accepts only `g_fc_hz`, `g_T`, `g_stop_deg`, `g_ar_m` in (0,4], `g_ar_p` in (0,8]; `stop_deg` in [90, 240]; no throat-angle, no per-plane split, no junction. |
| `grid.py:1578-1597`, `1872-1873`, `2133-2134` | The three `iwata_ar` code paths (build, metadata, validation). |
| `grid.py:201` + `IWATA_AR_LABEL` (near `:205`) | The label is explicit: "our reconstruction of the published principle (AR evolution + T=0.5); no published construction for this class exists". Keep that wording. |
| `hornlab_search/design/generators/profiles.py:463` | `splice(first, second, zs_frac)`: C1 splice of two meridians, radius-matched at the joint, with a Hermite bridge over 10 % if the wall-angle gap exceeds the tolerance. **This is the closest existing law, but it enforces continuity at the joint - the biradial joint is deliberately a discontinuous/step throat (the gap), so this splice is the wrong semantics for the published junction.** |
| `profiles.py:687` | `salmon_march_core` (spherical-wavefront march) - the reusable per-plane march. |
| `profiles.py:242` | `lecleach_exact` (verified Fourcade). |
| `examples/typologies/lecleach_iwata_ar.yaml:29-35` | The only shipped Iwata-named config; `type: iwata_ar`. |
| `examples/catalog.yaml:223-236` | Catalog note: "the area-preserving AR stretch (H != V) over the verified ..." - i.e. the repo's Iwata *is* an H/V asymmetry exercise, not a series-segment horn. |
| `docs/CODE_MAP.md:20,47` | Rows kinds list; matches `grid.py:129`. |
| `docs/ISSUES.md:92` | Legacy `lecleach_mod`/`lecleach_ar` rows remain unlisted/unconfigured; cleanup candidate. |

### 1.4 "Crowe"

`rg -i crowe docs design examples` returns **one** hit, and it is spurious: a base64 image blob inside
`docs/evidence/runs/20261013T121958Z-screen-9e5a5c/report_cp8b.html`. There is **no** Crowe claim,
citation or config in the repo. Everything in section 11 is new.

### 1.5 Bottom line of the inventory

- **Biradial: gap.** Attributed once, to the right person (Keele/JBL), from Wikipedia; no construction,
  no numbers, no knobs. This dossier supplies them from the patent.
- **Iwata: covered as a principle + datasheet**, in `JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md`
  sections 2.2/3/4. Do not duplicate work; the new material here is the Crowe/marketplace check and the
  R9 disposition (section 10).
- **Crowe: gap (zero repo coverage).**

---

## 2. SOURCE TABLE (9b.0 style)

| Source | What it gives us | Status |
|---|---|---|
| **US4308932A**, "Loudspeaker horn", D. Broadus Keele Jr., assignee James B. Lansing Sound (JBL), filed 1980-05-06, granted 1982-01-05. https://patents.google.com/patent/US4308932A/en | **The biradial construction**: two separately contoured sidewall pairs at 90 deg, power-series profile `y = a + b x + c x^n`, flare exponent n, differing flare angles producing a **non-congruent back end (gap)** joined to the circular throat by an **exponential-area connecting section**; one pair generated as a **surface of revolution**. Also the only **numeric reference case** (80 x 36 deg, 780 x 780 mm mouth, L 815.1, throat 48.8, gap 18.0, n_v 4.0, n_h 5.5, 516 mm throat-to-gap, 299.1 mm gap-to-mouth). | **primary (author)** |
| **D.B. Keele, "What's So Sacred About Exponential Horns?"**, AES Convention 51, Paper 1038, 1975-05-06; abstract page https://dbkeele.com/7-whats-so-sacred-about-exponential-horns/ | The CD-horn problem statement (multicell and radial/sectoral lobing; radial narrows vertically with frequency) and the **two-section** principle: "optimally joins a modified conical horn with an exponential throat section". This is the *ancestor* idea, not the biradial patent. | **primary (author)** |
| **dbkeele.com biography page**, https://dbkeele.com/ | "He also holds **two patents** on JBL's 'Bi-Radial' series of constant directivity horns" (1977-1984 at JBL); primary designer of EV's HR series. | **primary (author)** |
| **JBL Japan, "ITS JBL vol.07"**, https://jp.jbl.com/itsjbl/vol-07.html | Manufacturer history: Keele's CD horn 1974; "the Bi-Radial horn" completed by Keele **at JBL in 1980** as an evolution of the CD horn. | **marketing** (manufacturer's own history page; corroborates the patent's date/attribution only) |
| **JBL 2370 spec page**, https://audio-heritage.jp/JBL/unit/2370.html | Bi-Radial product data: FRP; **vertical coverage deliberately narrows with frequency** by making the vertical dimension small, while horizontal holds ~630 Hz-16 kHz. Used as a cross-check on the patent's claims. | **secondary, used only as a cross-check** |
| **JBL 2385 spec page**, https://audio-heritage.jp/JBL/unit/2385.html | 2385 = 2380 with a narrower horizontal angle, ~2 dB more output, same throat/length/mouth. Product-line cross-check. | **secondary, used only as a cross-check** |
| **Auto-Tech IWATA-300 product page + datasheet PDF**, https://horns-diy.pl/horns/iwata/iwata-300/ (PDF: https://horns-diy.pl/wp-content/uploads/2015/07/IWATA-3001.pdf) | The **only dimensioned record** of the product: 50.8 mm throat, 590 W x 320 H x 450 D, "minimal frequency from 450 Hz"; 2" driver family; 10-deg polars + horizontal sonogram in the PDF. No construction text. | **marketing** (manufacturer datasheet; treated as the reference numbers, not as a design) |
| **Auto-Tech IWATA family page**, https://horns-diy.pl/horns/iwata/ | Confirms IWATA-200/300/600/1200 as a separate commercial family; no origin/designer/geometry. | **marketing** |
| **Joseph Crowe, ES-600 Bi-Radial No.1978 product page**, https://josephcrowe.com/products/es-600-bi-radial-wood-horn-no-1978 | Published product numbers: **416 W x 203 H x 198 D**, 1.40" throat (adaptable to 1"), 600 Hz-20 kHz, "ES (Exponential Spiral)" flare, "wrap-around horn mouth". | **primary (author)** (he is the designer; the page is also commercial) |
| **Joseph Crowe, "ES-600 Biradial Horn" article**, https://josephcrowe.com/blogs/news/es-600-biradial-horn | Claims: **270-deg wrap-around mouth** ("a first for any biradial that I know of"), reduces edge diffraction and mouth resonance; H/W follow the "golden ratio"; passive network claimed mandatory. | **primary (author)** |
| **Joseph Crowe, "ES-290 Biradial polar off-axis"**, https://josephcrowe.com/blogs/news/es-290-biradial-polar-off-axis | His measurement claims: 5 cm throat; +10 dB 400-800 Hz, +7 dB 1.6 kHz, +5 dB 3 kHz loading; "near constant directivity 500 Hz-7 kHz"; "**90 degree listening window from 300 Hz-7 kHz**" to 90 deg off-axis; ranks ES-290 against "the classic Yuichi A-290 Biradial". | **primary (author)** (self-measured, no independent replication) |
| **Joseph Crowe, "ES-1200 Biradial Wood Horn"**, https://josephcrowe.com/blogs/news/es-1200-biradial-wood-horn | Model-number = loading cutoff ("loads down to 1200 Hz"); publishes **horizontal and vertical** polar maps (ARTA, 12 dB smoothing) and waterfall/CSD; notes small vertical irregularities ~17 kHz. | **primary (author)** |
| **Crowe sitemaps** (products, articles), https://josephcrowe.com/sitemap_products_1.xml and https://josephcrowe.com/sitemap_articles_1.xml | Complete catalogue evidence: **27 biradial product/CAD slugs** (ES-250/290/450/600/800/1200/1600/2000, E-800, Yuichi A-290 CAD), and **no Iwata product and no Iwata article**. | **primary (author)** (negative evidence) |
| **Thomas Mayer (VinylSavor), "Horns for Sale"**, http://vinylsavor.blogspot.com/2014/07/horns-for-sale.html | Practitioner: cast-aluminium IWATA horns for 2" drivers; "**might benefit from some dampening on the outside to reduce the ringing of the metal**"; used naked without issues; "the Iwatas can be used down to 300 Hz". | **secondary (practitioner reports)** |
| **tamochan exblog, "Biradial horn JBL 2380A"**, https://tamochan.exblog.jp/12730925/ | Practitioner definition: "the top, bottom, left and right walls are all curved surfaces" (JP: jouge-sayuu no hekimen ga subete kyokumen); mating the curved surfaces is difficult, a hard class to build in wood. | **secondary (practitioner reports)** |
| **audioasylumtrader listing** "Custom made IWATA, TAD, Biradial horns", http://www.audioasylumtrader.com/ca/listing/Speakers-Horns-Parts-Stands/Tractrix-JMLC-Iwata-TAD/Horn/Custom-made-IWATA-TAD-Biradial-horns/81971 | Marketplace usage that bundles "Iwata" and "Biradial" in one listing title. **Not a construction claim.** | **marketing** (classified ad) |
| **audioG listing, "Iwata 300 Horner Autotech"**, https://www.audiog.com/en/item.aspx?item=20127 | Dealer description: "based on a modified Iwata geometry"; "a hybrid of Tractrix and Le Cleac'h profiles"; 630 x 340 x 480 mm external; recommended crossover 500-700 Hz. | **marketing** (dealer, not the manufacturer; numbers differ from the datasheet) |
| **Marcel Batik (mabat), "EXAR Waveguides - Segmentizing a horn"**, https://at-horns.eu/seg-horn.html | The only **published analytic method for stacking segments along a horn**: sector transform with a meander weighting, junction/edge conditions, worked example (R-OSSE R=200, r0=12.7, a=35 deg, theta_S=60 deg, t0=0.8, kappa=4, zeta=0.75, t_m ~ 0.32). **This is a segmentizing method, not a biradial construction** - cite only as the available segment-junction math. | **primary (author)** |
| **diyAudio threads** (140190 JMLC; 166312 Auto-Tech group buy; 230122 Iwata A-190E; "waveguides and horns") | Practitioner detail and Le Cleac'h's own quasi-Iwata wording. | **primary (author, forum)** / **secondary (practitioner reports)** - **NOT REACHED TODAY** (Cloudflare "Validating browser" on live pages and on r.jina.ai). In-repo quotes only: **[unverified-today]**. |
| **Stereophile photopost "Philmundi Iwata horn conceptor"**, https://www.stereophile.com/content/philmundi-iwata-horn-conceptor-0 | Image caption only ("Philmundi Iwata horn conceptor", 2008); body/nav only on fetch. No attribution or geometry. | **marketing** (show/photo post; 403 direct, nav-only via proxy) |

Search infrastructure that failed today, recorded for the next lane: DuckDuckGo (CAPTCHA 410b), Mojeek
(JS challenge), Google Patents full-text phrase search (returns unrelated 1980s patents for "Bi-Radial";
use assignee/inventor queries instead), Justia (403), Bing (keyword noise for "Iwata"), diyAudio
(Cloudflare). Brave (`search.brave.com`) worked and is the source of the Japanese leads.

---

## 3. What "biradial" actually means - three usages, one primary

The word is overloaded. Separate them before any code is named.

1. **JBL/Keele Bi-Radial (1980) - the only construction with a primary source.** Two sidewall pairs at
   90 deg, each with its **own contour and flare rate**; when the flare angles differ the two pairs cannot
   share a throat, so a **gap** is formed and an **exponential connecting section** joins it to the
   circular throat. One pair is a **surface of revolution**. [verified, US4308932A]
   Note: the patent text does **not** use the word "Bi-Radial"; the name is the JBL product line
   (Keele bio page; JBL Japan history). The construction is what the name refers to. [verified]
2. **Crowe "ES Biradial" (2019-) - a designer's own family, geometry unpublished.** H/V asymmetric,
   golden-ratio-ish mouth, **270-deg wrapped mouth**, ES = "Exponential Spiral". He positions it against
   "the classic Yuichi A-290 Biradial". No expansion law, no per-plane angles, no CAD numbers published;
   "a future white paper" is promised in the ES-600 article. [verified claims; geometry unverified]
3. **Marketplace "biradial" - a shape label.** Selenium HM1725 "1-inch Bi-Radial Horn 60x40"; Audio
   Asylum Trader bundling "IWATA, TAD, Biradial"; Japanese hobby usage for JBL 2345/2370/2380/2385
   (katakana "bairajiaru hoon" = biradial horn). No construction. [marketing]

The owner's working description - "two radially flared segments stacked in series along the axis, each
with its own expansion rate/angle" - is **half right for (1)**: there is a genuine two-section series
junction (throat -> gap -> mouth), and the sections have different laws (exponential area vs
power-series contour). But "radially flared" describes only one of the two wall pairs; the other is a
power-series contour, and the two pairs are not two meridians of a common axis. That distinction is the
main technical finding of this dossier (section 4.4). [inferred from the patent]

Attribution history, for the record: Keele did the CD horn at Electro-Voice (1974-75) and the Bi-Radial
at JBL (1977-84; patent filed 1980). Community Professional / Electro-Voice "biradial" claims were **not**
found; EV's line is the HR/CD series, Altec's is the Mantaray. [verified: dbkeele.com bio; JBL Japan;
repo appendix A:152]

---

## 4. (a) Construction math

### 4.1 The published algorithm (US4308932A)

Inputs: horizontal coverage `B_h`, vertical coverage `B_v` (degrees), low-frequency limit `F` (Hz),
throat diameter `G` (mm), flare exponents `n_h`, `n_v`.

1. **Throat included angle** per plane: `A = 0.9 * B`. The patent: "empirically determined to be on the
   order of ninety percent of beamwidth". [verified]
2. **Mouth dimension** `W = K / (A * F)` with `K ~ 25,000 m-deg-Hz`. [verified]
3. **Straight-sidewall mouth dimension** `W' = W / 1.5`, "found empirically to optimize coverage".
   [verified]
4. **Wall contour** (each pair): `y = a + b x + c x^n`, where
   `a = G/2`, `b = tan(A/2)`, `x` is distance along the acoustic axis, `y` the displacement from it.
   Constraint: `y(L) = W/2` fixes `c` (EQU2 in the patent, present only as an image placeholder).
   `n` is the flare-rate factor: **4 to 6 preferred**, claim 14 allows **2 to 8**; "larger n with larger
   coverage angle"; "the flare rates for the two pairs of sidewalls may differ substantially".
   [verified text; EQU2 not machine-readable]
5. **Horn length** `L` from `W'` and the geometry of the included angle (EQU1, image placeholder).
   [verified text; EQU1 not machine-readable]
6. **Two-plane assembly**: the pair with the **larger** flare angle (the H pair in the example) has its
   back end at the **gap**; the pair with the smaller flare angle reaches the throat. Because the two
   mouths must join, the two back ends are **not congruent**: the H pair's back end is joined to the
   circular throat by a **connecting section** whose cross-sectional area "continuously diverges",
   "monotonically increases", and "in the exemplary embodiment ... with an exponential increase in area".
   [verified, claims 1-3, 8, 10-11]
7. **Surface of revolution**: the H pair plus connector is generated by sweeping the contour around a
   vertex (rotation centre) at radius `R`, then the V pair is overlaid and sectioned out; "the sidewalls
   16a-b and 26a-b are formed by the surface of revolution itself". [verified]
8. **Mouth**: square in the example; "substantially rectangular" otherwise, "defined by the selected
   beamwidth and low-frequency limits". [verified]
9. **Fundamental limit stated by the patent**: "a horn can only offer directivity control down to
   frequencies at which the wavelength is comparable to horn mouth size." [verified]

### 4.2 Reference case, exactly as printed

| Quantity | Value |
|---|---|
| Horizontal coverage `A_h` | 80 deg |
| Vertical coverage `A_v` | 36 deg |
| Mouth height `W_v` | 780 mm |
| Mouth width `W_h` | 780 mm |
| Length `L` | 815.1 mm |
| Throat diameter `G` | 48.8 mm |
| Gap width | 18.0 mm |
| Vertical flare exponent `N_v` | 4.0 |
| Horizontal flare exponent `N_h` | 5.5 |
| Radius origin | at `x = 125.0` mm |
| Gap-to-mouth distance | 299.1 mm |
| Throat-to-gap distance | 516 mm |

Source: US4308932A, design-example column. [verified, re-fetched and quoted twice]

### 4.3 Numeric checks we ran on the reference case

All arithmetic run with `.venv\Scripts\python.exe`; results printed.

| Check | Result | Label |
|---|---|---|
| Segment lengths sum to L | `299.1 + 516.0 = 815.1` exact | **[verified]** |
| `W = K/(A F)` at H = 80 deg, F = 400 Hz | `25,000/(80*400) = 0.78125 m = 781.25 mm`, i.e. the printed 780 mm (implies the example used **F = 400 Hz**, though F is not printed) | **[measured]** |
| Same rule at V = 36 deg | `25,000/(36*400) = 1736 mm`, **not** 780 mm | **[measured] - the sizing rule is not applied to the vertical plane in the example** |
| Throat area | `pi*48.8^2/4 = 1870.4 mm^2` | **[measured]** |
| Gap area must exceed throat area (monotonic divergence) | gap height must exceed `1870.4/18.0 = 103.9 mm` | **[inferred from claim 3; measured]** |
| Gap height from the V contour at x = 516 | `y = 24.4 + tan(18deg)*516 + c*516^4 = 208.2 mm` -> height 416.4 mm (with `c` fitted to the V mouth); the simpler tangent estimate gives `48.8 + 2*516*tan(18deg) = 384.1 mm` | **[inferred; measured]** |
| **Gap aspect ratio** | `18.0 x ~416 mm` -> **~23:1** (or ~21:1 on the tangent estimate); gap area ~3.7x throat area | **[inferred; measured]** |
| Naive per-plane Eq.1 march, H: `a = 24.4`, `b = tan(40deg) = 0.8391`, `n = 5.5`, `y(815.1) = 390` | requires `c = -3.10e-14`; end slope `-1.309` (wall angle **-52.6 deg**) -> the wall turns inward. **A monotonic outward H flare with these printed numbers is impossible under Eq.1 in the axial frame.** | **[measured] - proves the H pair is not an axial meridian** |
| Same march, V: `b = tan(18deg) = 0.3249`, `n = 4.0` | `c = +2.28e-10`; end slope `0.819` (39.3 deg) -> monotonic outward, fine | **[measured]** |

Two consequences, both load-bearing:

- **The published table is not a self-validating numerical gate for Eq.1.** Use it as a *topology* gate
  (two different throat widths, an 18 mm gap, the 516/299.1 split) plus the two scalar checks that do
  hold (length sum; W rule at 80 deg / 400 Hz). [inferred]
- **The H pair lives in a swept/rotated frame** (surface of revolution), so "two meridians + AR stretch"
  cannot reproduce the published horn. This is exactly why the repo's existing `iwata_ar` (AR stretch of
  a single meridian) is not a biradial. [inferred, from the measured failure above]

### 4.4 Minimal validation set for a biradial implementation

Pass/fail, in order:

1. **Topology**: two wall pairs at 90 deg; back-end widths differ (`G_v != gap_w`); connector area
   monotonic from throat to gap. [verified source]
2. **Junction**: gap width 18.0 mm at the reference case; gap-to-mouth 299.1 mm; throat-to-gap 516.0 mm;
   total 815.1 mm (+/- 1 mm). [verified]
3. **Sizing rule**: `W_h = K/(A_h F)` reproduces 780 mm at 80 deg / 400 Hz within 1 mm. [measured]
4. **Mouth**: 780 x 780 mm at the reference case (+/- 3 mm). [verified]
5. **Documented failure mode to assert against**: a single-meridian march cannot satisfy (2)+(4) on the
   H plane (section 4.3). A test that "passes" by using one meridian for both planes is mislabelled.

Do **not** gate on EQU1/EQU2 until the patent PDF's equation images are read; they are placeholders in
the HTML edition. [verified absence]

---

## 5. (b) Strengths, in the designers' own terms

- **Pattern control / constant directivity.** The patent's stated purpose is "directional characteristics
  which are substantially constant with frequency" and "a constant acoustic load to the driver"; measured
  polars are shown at 800 Hz, 2.5 kHz and 12.5 kHz for H (dashed) and V (solid). [verified]
- **Separate H and V design freedom.** Because the two pairs carry independent `n` and `A`, a 90 x 40 or
  60 x 40 pattern is set by geometry rather than by a compromise profile. This is the "bi" in biradial.
  [verified: claim 2, "representative of coverage angle ... and flare rate"]
- **Mouth reflection / edge behaviour (modern practitioners).** Crowe's claimed benefit is the **270-deg
  wrap-around mouth**, which he says reduces edge diffraction and "minimizes acoustical resonance to very
  low levels"; the ES-290 article argues that clean off-axis response is evidence of "very little stored
  energy". [primary (author), self-measured; not independently replicated]
- **Loading.** Crowe's ES-290-on-a-5 cm-full-range measurement claims +10 dB at 400-800 Hz, +7 dB at
  1.6 kHz, +5 dB at 3 kHz versus the same driver unhorned. [primary (author), self-measured]
- **Buildability (relative).** A biradial is two families of curved walls with a common mouth - no
  multicell cells, no diffraction lens. The Japanese practitioner note calls it hard to mate but not
  exotic. [secondary (practitioner reports)]

## 6. (c) Weaknesses / design issues

1. **The gap is a thin, tall slot.** At the published reference case it is 18 mm wide by ~400 mm tall
   (~21-23:1). That is a high-aspect-ratio duct at the highest-pressure point of the horn: strong
   diffraction, transverse modes across the short dimension, and a local particle-velocity maximum.
   [inferred from the printed table + Eq.1; measured]
2. **Junction behaviour is not a smooth splice.** The two wall pairs are *deliberately non-congruent* at
   the back; the connector's job is to absorb the mismatch. Any implementation that radius-matches the
   junction (e.g. `profiles.splice`) has modelled a different horn. Expect a reflection/ripple signature
   at the gap that a smooth splice would not show. [inferred; supported by the patent's own framing]
3. **Foldback / wrap limits.** The patent's contours are monotonic (`n` 4-6, `c` fixed by the mouth); no
   lip curl is specified. Crowe's 270-deg wrap is his own extension, and it creates the usual costs: a
   large outer surface, a thin cavity between roll and shell, and a mouth that is hard to build.
   [verified: patent has no lip; Crowe claim is author-only]
4. **Mouth-size vs band feasibility.** The patent itself states the limit: directivity control only down
   to where the wavelength is comparable to mouth size, and `W = K/(A F)` makes that explicit - a 90 deg
   pattern at 400 Hz needs a ~700 mm mouth. Crowe's own line trades size for cutoff (ES-600 = 416 mm wide
   at 600 Hz; ES-1200 smaller still), so below ~600 Hz the mouth is sub-wavefront and pattern control must
   degrade. [verified patent statement; inferred for the product line]
5. **Vertical beaming above the design band.** JBL's own 2370 note says the vertical coverage is designed
   to **narrow with frequency** (small vertical dimension), while horizontal stays wide to 16 kHz. That is
   a design choice, but it means "biradial" does not imply symmetric CD at HF.
   [secondary, used only as a cross-check]
6. **The published example is internally inconsistent** (section 4.3: W rule fails on V; Eq.1 fails on H
   in the axial frame). Anyone validating against it must use the topology + the two scalar checks, not a
   single "does it match the patent" scalar. [measured]
7. **Name/geometry drift.** "Biradial" is used for JBL's slot-loaded two-plane horn, Crowe's wrapped ES
   horn, Yuichi A-290 derivatives and generic 60x40 PA horns. Shipping one implementation under the bare
   name will over-claim. [verified across the source table]

## 7. (d) Optimization knobs and typical ranges (anchored, not invented)

All ranges below are **[inferred]** unless a row says otherwise; each is anchored to a named published
example. Do not widen them without a new anchor.

| Knob | Symbol / unit | Anchor(s) | Suggested range |
|---|---|---|---|
| Horizontal coverage | `B_h` deg | patent typical set 40/60/90; example 80; Selenium HM1725 60; JBL 2370 90 (product) | **40-90** [anchored] |
| Vertical coverage | `B_v` deg | patent typical 20/40; example 36; Selenium 40 | **20-40** [anchored] |
| Throat included angle | `A = 0.9 B` deg | patent rule | derived, not free |
| Flare exponent H | `n_h` | patent 4-6 preferred, 2-8 allowed; example 5.5 | **4.0-6.0** (hold 2-8 as a labeled extension) [anchored] |
| Flare exponent V | `n_v` | example 4.0 | **4.0-5.0** [anchored] |
| Low-frequency limit | `F` Hz | patent "typically 400"; product cutoffs 290/300/450/600/1200 | **290-1200** across classes; **400-800** for a 2" mid/high horn [anchored] |
| Throat diameter | `G` mm | 25.4 (1"), 35.6 (1.4"), 48.8/50.8 (2") | **25.4 / 35.6 / 50.8** discrete [anchored] |
| Gap width | `w_g` mm | 18.0 at G = 48.8 (ratio 0.369) | **0.30-0.40 G** [inferred from one anchor] |
| Gap position | `x_g` mm / fraction of L | 516 / 815.1 = **0.633** | **0.55-0.70 L** [inferred from one anchor] |
| Mouth aspect | `W/H` | 1.00 (patent example); 1.84 (IWATA-300 590/320); 2.05 (ES-600 416/203) | **1.0-2.1** [anchored] |
| Depth / width | `D/W` | 1.045 (patent 815/780); 0.763 (IWATA-300 450/590); 0.476 (ES-600 198/416) | **0.48-1.05** [anchored] |
| Mouth wrap | deg | 0 (patent); 270 (Crowe claim) | **0 or 180-270** [inferred; Crowe is the only anchor] |
| Revolution vertex | `x_v` mm | example 125.0 (0.153 L) | **0.10-0.25 L** [inferred from one anchor] |
| Connector law | - | exponential area (patent); monotonic required | exponential first, power-law as a labeled variant [verified] |

Derived ratios that are useful as knob defaults: `w_g/G = 0.369`, `x_g/L = 0.633`,
`x_v/L = 0.153`, all from the single published example. Treat them as *one* data point, not a trend.

## 8. (e) How practitioners rank and measure them - which objectives are honest

Published measurement practice, in order of evidential value:

1. **Two-plane polar families, 10-deg steps, 200 Hz-20 kHz** (Auto-Tech datasheets) and **horizontal +
   vertical polar maps + waterfall/CSD** (Crowe, ARTA 12 dB smoothing). [verified]
2. **On/off-axis similarity** as the quality proxy: Crowe explicitly argues that consistent off-axis
   response relative to on-axis indicates low stored energy, and uses it to rank ES against Yuichi.
   [primary (author), claim]
3. **Loading gain vs the same driver unhorned** (+10/+7/+5 dB in the ES-290 case) and **low-frequency
   extension** ("loads down to N Hz", model number = cutoff). [primary (author)]
4. **DI / balloon** is the honest scalar for the *design intent* (constant directivity), but none of the
   fetched sources publishes a DI curve; they publish polars and sonograms. Do not claim a DI match.
   [verified absence]
5. **CSD / waterfall** is published by Crowe; the patent shows only three polar frequencies. [verified]

Honest objectives for the search layer, therefore: (i) beamwidth flatness over the design band in **both**
planes; (ii) on/off-axis magnitude similarity; (iii) DI slope (mildly rising preferred, per the repo's
existing Geddes note); (iv) mouth-reflection/ripple proxy from the throat impedance; (v) CSD decay. Do
**not** rank on "matches the patent" (section 4.3) or on a nominal coverage number alone.

## 9. (f) Experiential characteristics (designers and users)

- **Smoothness vs honk.** Crowe: the wrap mouth removes "edge diffraction off the horn mouth" and pushes
  resonance "to very low levels"; he also insists the ES-600 "cannot" be run active without his passive
  network, which damps 1 kHz-region resonances - an admission that the horn has audible resonances to
  manage. [primary (author)]
- **Beaming.** ES-290: wide to ~7 kHz, then "quickly narrows down to a 50 degree coverage window" above
  10 kHz with the substitute driver; ES-1200: small vertical irregularities ~17 kHz. [primary (author)]
- **Metallic ringing.** Thomas Mayer on cast-aluminium Iwatas: "might benefit from some dampening on the
  outside to reduce the ringing of the metal", though he used them naked "without any issues".
  [secondary (practitioner reports)]
- **Placement forgiveness.** No fetched source makes a placement claim for biradials specifically. The
  pattern-control argument implies a narrower sweet spot than a wide radial, but that is
  **[inferred]**, not reported. Do not put a placement claim in a brief without a measurement.
- **Build difficulty.** All four walls curved, mating them is hard, a difficult wood-horn class.
  [secondary (practitioner reports)]
- **Iwata specifically.** "Keeps most of the JMLC loading with closer driver spacing"; a 3D-printed
  Iwata-300 replica is reported to "ring like a bell". [unverified-today; in-repo quotes only]

## 10. Iwata 300: what is actually established (and the R9 stop)

**Established, with numbers.** Auto-Tech IWATA-300: 2" (50.8 mm) throat, 590 W x 320 H x 450 D mm,
"minimal frequency from 450 Hz", 2" driver family (TAD TD-4001, JBL 2446, Radian 950, BMS 4590 per the
dealer text), 10-deg polars + horizontal sonogram in the datasheet. [marketing; numbers reused as the
reference set]

**Cross-checks.** `W/H = 590/320 = 1.844`; `D/W = 450/590 = 0.763`; the usable band starts at
`450/300 = 1.5x` the model number. [measured]

**Not established.** No designer name, no patent, no paper, no construction, no per-plane flare angles, no
gap/junction, no per-segment expansion rates. The 2026-10-25 searches (Brave, Bing, Google Patents,
Auto-Tech site, dealer pages, Stereophile) produced **no primary source**; the repo already recorded the
same negative (`JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md:25`). The only "Iwata is biradial" statements
are marketplace labels (Audio Asylum Trader listing; Japanese hobby usage) and a dealer's "hybrid of
Tractrix and Le Cleac'h" prose, which is not a construction. [verified absence; marketing labels]

**R9 disposition: STOP this line under the name "Iwata".** Do not ship an "Iwata 300" construction, and
do not call a two-segment biradial an Iwata. What may ship is (i) an **IWATA-300 reference config** as a
*shape/ratio target* driven by the existing `iwata_ar` (AR evolution + T=0.5), explicitly labelled "our
reconstruction of a published principle, not the product", and (ii) report-only fingerprints (depth/width
0.76; AR 1.84). This matches the repo's existing C1 correction. [binding]

**Open avenue (recorded, not attempted):** a Japanese-language primary (MJ Audio / Musen to Jikken
era design article, or an Auto-Tech design note). Without it, the name stays unattributed.

## 11. Joseph Crowe: what he sells and what he claims

**Catalogue (verified via sitemaps + collection page, 2026-10-25).** 27 biradial product/CAD slugs in the
ES series (ES-250, ES-290, ES-450, ES-600, ES-800, ES-1200, ES-1600, ES-2000), plus E-800 for Altec 604
and a "Custom Yuichi A-290 Biradial" CAD model. The "Biradial Horns" collection page itself has **no
definition** of the term. [verified]

**There is no Iwata product and no Iwata article.** The task brief's premise ("Crowe sells Iwata 300 horn
kits") is **not supported** by the 2026-10-25 catalogue or article sitemap. This is correction **C1**
below. His Iwata-adjacent item is the **Yuichi A-290** CAD model, a different horn. [verified negative]

**Published numbers he does give** (his design, his claims):

| Model | W x H x D (mm) | Throat | Cutoff | Other |
|---|---|---|---|---|
| ES-600 No.1978 | 416 x 203 x 198 | 1.40" (1" via adapter) | 600 Hz | 270-deg wrap mouth; golden-ratio claim; "throat bump" for cutoff resonance |
| ES-1200 | not published | - | 1200 Hz | H+V polar maps, waterfall; vertical ripples ~17 kHz |
| ES-290 | not published (article: "effectively double the size of the ES-600", ~832 x 406 x 396 [inferred]) | 5 cm | 290 Hz | 90-deg window 300 Hz-7 kHz claimed with a 5 cm full-range driver |

**What he measures.** ARTA frequency response, burst decay/waterfall, horizontal and vertical polar maps
(12 dB smoothing), on/off-axis comparison, loading gain vs unhorned, GedLee Gm elsewhere on the site.
[verified]

**What he does *not* publish.** The ES expansion law, the per-plane flare angles, the mouth profile
equation, any CAD dimensions beyond the three external numbers, or any third-party verification. The
ES-600 article promises "a future white paper". [verified absence]

**Status of his claims.** Primary for what he designed and measured; **marketing-adjacent** for
"outperformed basically any horn type" and "best sounding horns that I make"; **not** a construction
source. Do not implement "ES" from his pages.

## 12. Mapping onto the repo search layer (CANDIDATES ONLY - no code designed here)

The repo has two relevant surfaces:

- **`profiles.py` march laws**: `conical`, `exponential`, `hypex`, `tractrix`, `lecleach_exact`,
  `spherical_wave`, `splice` (C1, radius-matched + Hermite bridge), `throat_blend` (OS throat), and
  `salmon_march_core`/`spherical_salmon`. A biradial needs a **contour** law (`y = a + bx + cx^n`), not an
  area-law march, plus a **non-continuous** junction.
- **`grid.py` rows**: 7 kinds (`salmon_axisym`, `salmon_elliptical`, `lecleach`, `iwata_ar`,
  `toroidal_rollback`, `lecleach_mod`, `lecleach_ar`), one radius field `r(phi, s)` with harmonic stop/bend
  modulation. A biradial is **two wall families with different laws and a non-congruent throat**, which
  the current single-field rows contract does not express.

What is missing, concretely:

1. **A contour family**: `y = a + b x + c x^n` with `a = G/2`, `b = tan(A/2)`, `c` solved from the mouth,
   `n` a knob. Nothing in `profiles.py` produces this (the nearest, `conical`, is `n = 1`; `exponential`
   is an area law). ~80-120 LOC + tests.
2. **A slot junction**: a connector from a circle (`G`) to a high-aspect rectangle (`w_g x h_g`) with a
   monotonic/exponential area law, and an explicit C0 step at the gap. `splice` is the wrong tool
   (it forces C1 and radius matching). ~100-150 LOC.
3. **Two-family assembly**: one pair as a swept surface of revolution (vertex `x_v`, radius `R`), the
   other as a power-series contour, sectioned at the mouth. This is a new topology for the rows lane
   (which assumes one `r(phi, s)` field). ~250-400 LOC + symmetry/mesh tests.
4. **A reference-case regression** on the patent table (topology + the two scalar checks in 4.4).

Do **not** try to express a biradial as `iwata_ar` with a bigger `ar_m`: the AR stretch preserves area on
a single meridian and has no gap, no connector, and no swept plane. That is the exact mislabelling the R9
gate exists to prevent.

## 13. R9 gate and risk flags

| # | Flag | Consequence |
|---|---|---|
| R9-1 | **"Biradial" as a published typology: PASS** - primary construction + numbers (US4308932A) reached and read. | A biradial implementation may ship **if** named for the source, e.g. `biradial_keele_1980`, and cites this dossier. |
| R9-2 | **"Iwata 300" as a construction: STOP.** No primary source reachable 2026-10-25; only a manufacturer datasheet (4 dimensions + cutoff) and marketplace "biradial" labels. | Ship only `iwata_ar` reconstructions labelled "principle, not product"; never "Iwata 300" as a reproduced horn. |
| R9-3 | **"Crowe ES biradial": STOP as a construction.** Self-published geometry claims, no law, no dimensions beyond three externals, no independent measurement. | At most a labeled shape-target regression; do not name a generator `es_biradial`. |
| R9-4 | **The patent's own numeric example is not a single-scalar gate** (W rule fails on V; Eq.1 fails on H in the axial frame). | Validation must be topology + the two checks in 4.4; do not "tune until 780/815.1 matches" on one meridian. |
| R9-5 | **`EQU1`/`EQU2` are image placeholders in the HTML patent.** | `L` and `c` are not independently derivable from the fetched text. Either read the PDF images or treat them as free parameters fixed by the printed example. |
| R9-6 | **Second Keele JBL patent not located.** Bio says two; assignee query returns only US4308932A. | Do not claim "the two Bi-Radial patents" in code comments; cite the one we read. |

## 14. Open items for the owner

1. **Decide the name.** `biradial_keele_1980` (faithful, complex) vs a neutral `two_plane_slot_horn`
   (honest, less marketable). The patent is public domain, so attribution is not a legal issue - only an
   R9 honesty issue.
2. **Choose the ambition**: (a) a 2-D contour + slot junction march (cheap, captures the profile, not the
   swept plane), (b) the full two-family rows kind (expensive, faithful), or (c) report-only fingerprints
   first (cheapest).
3. **Get the patent PDF** (`https://patents.google.com/patent/US4308932A/en` -> PDF link) to read EQU1/EQU2
   and confirm the gap-height/aspect inference.
4. **Get a JBL 2370/2380A/2385 spec sheet** (coverage, dimensions, throat) as an independent second
   reference case; the Japanese archive already gives the qualitative vertical-beaming behaviour.
5. **Iwata**: is a Japanese-magazine primary worth chasing, or does the owner accept "principle only"?
   Until then, no Iwata-named construction.
6. **Crowe**: the promised ES white paper is the only thing that could turn his claims into a
   construction. Track it; do not reconstruct from photos.
7. **diyAudio** (140190, 166312, 230122): blocked this session. A later lane with a working proxy could
   recover Le Cleac'h's exact quasi-Iwata wording and the Iwata build reports.

## 15. Corrections (dated, append-only)

- **C1 (2026-10-25):** the lane brief states "Joseph Crowe sells Iwata 300 horn kits". **False as of
  2026-10-25**: no Iwata product or article in his product/article sitemaps; the closest items are the
  ES biradial series and a Yuichi A-290 CAD model. Recorded, not silently dropped.
- **C2 (2026-10-25):** the lane brief lists grid rows kinds including `salmon_x_shape` and
  `salmon_saddle`. `grid.py:129` does **not** include them (7 kinds; their catalog entries were removed
  per `docs/evidence/M4_SMOKE_2026-10-25.md:198`). The brief's list is stale; this does not change the
  biradial conclusion.
- **C3 (2026-10-25):** repo `appendix_A_typology_survey_raw.md:152` ties the Bi-Radial to the 1975 AES
  paper. Correct attribution: CD horn = EV 1974-75; Bi-Radial = JBL, patent filed 1980, granted 1982.
  Cite `US4308932A` rather than the Wikipedia line.
- **C4 (2026-10-25):** "biradial = two radially flared segments in series" is only partially right. The
  series junction is real (throat -> gap -> mouth), but one wall pair is a **surface of revolution** and
  the other a **power-series contour**; it is not two meridians of one axis (section 4.3, measured).
