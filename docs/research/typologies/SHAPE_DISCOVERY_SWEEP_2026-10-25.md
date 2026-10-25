# SHAPE DISCOVERY SWEEP - 2026-10-25

Broad shape-discovery lane for hornlab-search. Read-only recon of the repo plus a web
sweep from four distinguished starting points treated as SEPARATE lineages (Iwata,
Altec sectoral/biradial, JBL Bi-Radial, Joseph Crowe), then a hunt for shapes the repo
has no typology for: asymmetric, organic, rippled/corrugated/lobed, multi-direction
gradient.

Status labels used throughout (embedded protocol):
`primary (author)` / `primary (author, forum)` / `primary (manufacturer)` /
`secondary, peer-reviewed` / `secondary, used only as a cross-check` / `marketing` /
`secondary (practitioner reports)`.

Claim markers: `[verified]` (read at source this session), `[inferred]` (reasoned
extrapolation, not at source), `[measured]` (a number someone measured, quoted),
`[unverified]` (asserted by a source I could not machine-read this session), or a URL.

SCOPE NOTE / HONEST LIMITATION. General web search was largely unusable from this
lane: DuckDuckGo served a CAPTCHA, Bing returned degraded/irrelevant result sets that
ignored quoted terms, Brave answered HTTP 429, Mojeek required JS, Marginalia
rate-limited, and diyAudio answered HTTP 403. Everything below therefore comes from
(a) author/manufacturer pages fetched directly, (b) one archived manufacturer white
paper and one archived magazine article read as text, (c) Wikipedia used as a
cross-check with its own primary references, and (d) the repo's prior survey docs.
The diyAudio ATH thread (338806), thread 354772, and the older horn threads were NOT
read this session. Where a candidate's evidence is only "prior repo survey", that is
labelled. This does not weaken the repo inventory verdicts; it does limit the
practitioner-feedback section (4).

---

## 0. Inventory before fetch (cite-and-skip verdicts)

Greps only: `docs/`, `design/`, `examples/`, `hornlab_search/design/`.

| Family / shape | Repo state | Where | Verdict for this lane |
|---|---|---|---|
| OSSE / R-OSSE | Generator family + examples + sec. 4/sec. 11 research | `design/families.py` (`_OSSE`, `_ROSSE`), `examples/osse_baseline.yaml`, `examples/rosse_baseline.yaml`, `docs/plan/12_RESEARCH_BASIS.md` sec. 4, sec. 11 | CITE-AND-SKIP. Do not re-research the profile. NOTE: the R-OSSE paper is strictly axisymmetric, `a` is a scalar "nominal coverage angle" [verified, PDF read]; the repo does not have per-azimuth `a`. |
| ICW + rollback | Fully supported | `design/families.py` `_ICW`, `examples/icw_*.yaml` | CITE-AND-SKIP. |
| FREEFORM (H/V profiles, per-station cross sections, superellipse/superformula) | Fully supported | `_FREEFORM`, `examples/freeform_*.yaml`, `mesh/` | CITE-AND-SKIP. This is the catch-all route for any smooth two-plane shape. |
| Gielis superformula guiding curve | Supported (`gcurve` keys) | `_OSSE`/`_GV`, sec. 11 | CITE-AND-SKIP. |
| Le Cleac'h (verified Fourcade construction) + rows | Supported | `profiles.lecleach_exact`, `ROWS_TYPES` `lecleach`, `examples/typologies/lecleach_*.yaml` | CITE-AND-SKIP. |
| Salmon family rows (`salmon_axisym`, `salmon_elliptical`, `x_shape`, `saddle`) | Supported, labelled hypothesis experiments | `ROWS_TYPES`, `examples/typologies/salmon_*.yaml` | CITE-AND-SKIP. |
| `iwata_ar` | PARTIAL: our area-preserving AR stretch of the verified Le Cleac'h meridian, T pinned 0.5 | `grid.py` `_rows_iwata_ar_knobs`, `examples/typologies/lecleach_iwata_ar.yaml` | PARTIAL. What is missing for a full IWATA typology: (i) the real IWATA-300 flare law (never published; depth/width 0.76 vs our reconstruction); (ii) any primary Iwata source (patent/paper) - the prior lane already searched and found none. See R9 flags. |
| `toroidal_rollback`, `multicell`/septa, splice/blend | Supported | `ROWS_TYPES`, `tools/cad/multicell.py`, `examples/typologies/*` | CITE-AND-SKIP. Multicell machinery is the reuse path for any internal-vane proposal. |
| G8 even-cosine radius field `a_k(s) cos(2k phi)` | Supported | `grid.py` lines 3-34, 408-417 | PARTIAL COVER for "lobed": smooth low-order lobes (k=1..K) exist. NOT covered: sharp-valley petals, mouth-localised ripples, ripple in `s`, odd-k lobes. |
| G9 per-azimuth mouth rollback `dz_mouth(phi) * w_mouth(s)` | Supported | `grid.py` line 10, 501 | PARTIAL COVER for "wavy mouth". |
| Per-azimuth stop/cutoff harmonics `cos(2k phi)`, `sin((2k+1) phi)` + axial bend `sin(phi)` | Supported (half/quarter model rules) | `grid.py` 833, 944-951, 1363-1375 | COVERED as a *termination* law, not as a *wall-angle* law. |
| Odd `cos(phi)` term | Explicitly REFUSED | `grid.py` lines 119-130 ("a `cos(phi)` (odd cosine) term is NOT invariant under `phi -> pi - phi` ... is REFUSED") | ABSENT BY DESIGN. This is the exact hook for single-sided asymmetry. |
| Diffraction slot (any family) | Absent | no slot/stage concept in `profiles.py`; `slot_length_mm` in OSSE is a throat adapter parameter, not a JBL-style diffraction slot | ABSENT. |
| Internal vanes / septa beyond multicell | Absent except multicell CAD | `tools/cad/multicell.py` | ABSENT as a general axis (Mantaray/sectoral/Lens reuse this route). |
| Acoustic lens (perforated/slant/serpentine) | Absent | not present | ABSENT. |
| Twist / helical azimuth offset | Absent | radius field is `r(phi, s)` with no `phi0(s)` | ABSENT. |
| Ripple along `s` (corrugation rings) | Absent | FREEFORM profile points could approximate a smooth bump, but no ripple law and no dedicated kind | ABSENT. |

Cite-and-skip (do not re-research as new): OSSE/R-OSSE, ICW+rollback, FREEFORM H/V +
superellipse/superformula, Gielis guiding curve, Le Cleac'h salmon, salmon family rows,
`iwata_ar` grid rows (partial), `toroidal_rollback`, multicell/septa, splice/blend.

---

## 1. Discovery source table

| Source | What it gives us | Status |
|---|---|---|
| Batik, ATH Tritonia page, https://at-horns.eu/tritonia.html | Explicit azimuth-dependent coverage law `alpha(theta)=48.5-7cos^5(2theta)-16sin^12(theta)`, `s(theta)=0.7+0.2cos^2(theta)`, k=1,n=3.7,q=0.995; the "accidental twisted wall" story; Tritonia-F 422x364 mm, 100 deg, 800 Hz-16 kHz; OS-SE + rounded-rectangle morph | `primary (author)` |
| Batik, ATH CORE page, https://at-horns.eu/core.html | Full CC-BY-4.0 Ath script: `a=5+35*sf(4,12,15,16,1,0.618,p)-15*cos(p)^10`, `n=6+1.5cos^2(p)`, `q=0.996`, `s=0.6+0.23cos^2(p)`, `s1=1.14`, `s2=0.025`, L=260, r0=25, a0=1.2, roundover 42 mm | `primary (author)` |
| Batik, ATH TwinRay page, https://at-horns.eu/twinray.html | H constant-directivity + deliberately narrowing V beamwidth; 266x212x130 mm, LF point 680 Hz; enclosure-optimised BEM | `primary (author)` |
| Batik, R-OSSE paper rev7, https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf | The formula and parameter table; explicit statement that `a` is one scalar half-angle and the device is axisymmetric. Confirms the CORE/Tritonia azimuth laws are script-level, not paper-level | `primary (author)` |
| Batik, ATH Gen2 / A460D / Opus 12 V-ERS pages | State of the ATH art: rising-DI free-standing R-OSSE, replaceable throats, extended throat, ESP spherical-wave plug; constant-DI target (A460D) | `primary (author)` |
| JBL Pro, "Progressive Transition Waveguides" / "Image Control Waveguide", https://jblpro.com/en/innovation-directivity | PT: "a single mathematically-continuous surface ... from transducer throat to waveguide mouth", "No traditional diffraction slot", square/rectangular flange, compact vs optimised/rotatable families. Image Control: patent-pending, M2/3-series, no dimensions | `primary (manufacturer)` (marketing-adjacent technical page) |
| Murray (Peavey), "The Quadratic-Throat Waveguide: A White Paper On An Invention By Charles E. Hughes", archived PDF | Independent descriptions of EV CD, Mantaray, Bi-Radial; QT construction (arc angle = half dispersion angle; circular-to-rectangle, no flare-rate breaks); measured 3-4 dB better 2nd harmonic, ~9 dB better 3rd; foam mouth edge | `primary (manufacturer)` |
| Augspurger, "Acoustical Lens", Audio magazine article, https://www.tnt-audio.com/clinica/acoustic_lens.pdf | Two lens classes (obstacle array = perforated plates; path-length refractor = serpentine/slant plate); JBL uses perforated plate; ~90 deg solid angle; <1% loss; plate spacing <= 0.5 in for 10 kHz; 400 Hz-15 kHz | `secondary (practitioner/engineering article)` |
| Wikipedia "Horn loudspeaker", https://en.wikipedia.org/wiki/Horn_loudspeaker | Radial/sectoral/diffraction definitions; Altec sectoral = radial + mouth vanes; JBL "Smith" diffraction horn; Mantaray construction; Bi-Radial construction; Twin Bessel; HCD (Cinanni); QT; OSWG; CD-EQ 6 dB/oct | `secondary, used only as a cross-check` (article cites Henricksen, Peavey white paper, Eargle) |
| Wikipedia "D. B. Keele Jr.", https://en.wikipedia.org/wiki/D._B._Keele_Jr. | "several patents of Bi-radial horns from companies like JBL, and Electrovoice" | `secondary, used only as a cross-check` |
| Lansing Heritage Altec "Sectoral Horns Circa 1968" and MR931 pages, http://www.lansingheritage.org/html/altec/specs/components/sectoral.htm | Primary-scanned Altec literature exists (4 pages + 4 pages), but only as page images; no text layer read this session | `primary (manufacturer)`, `[unverified]` (scan not machine-read) |
| Technical Audio Altec MR42 Mantaray PDF | Scanned PDF; not machine-read this session | `primary (manufacturer)`, `[unverified]` |
| Joseph Crowe product + article index, https://josephcrowe.com/sitemap_products_1.xml , https://josephcrowe.com/products/es-800-bi-radial-wood-horn , .../es-1200-bi-radial-wood-horn | Catalogue breadth: ES-250/450/600/800/1200/1600/2000 biradial and ES circular horns, E-250 dual-planar, E-800, Sabourin front horn, Co-entrant No.1416, shallow horn No.1928, ultra-wide No.2275, lenses No.1896/2258/2332, Azurahorn AH-1100, Yuichi A-290 CAD, AMT/dome waveguides. "ES (Exponential Spiral) flare geometry", "wrap-around horn mouth"; NO formula, NO coverage numbers | `primary (designer, commercial page)` |
| Prior repo survey `docs/research/senior_pass_2026-10-24/appendix_A_typology_survey_raw.md` | Roster + source links for Mantaray, PT, QT, lens, serration, fins, stepped horn; explicitly corrections-gated | `secondary, used only as a cross-check` |
| Repo Iwata research `docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md` | IWATA-300 dimensions (590x320x450, 2" throat, 450 Hz), T=0.5 principle, AR evolution, R9 rename gate already raised | `secondary, used only as a cross-check` (in-repo primary quotes) |
| "SIBINIC" | No page at at-horns.eu (`/sibinic.html` 404, no archive snapshot, not in any sitemap, zero GitHub code hits, not on the index page). No construction, no name match | NOT FOUND -> R9 |

---

## 2. Candidate catalog, grouped by tag

Each entry: name AS ATTRIBUTED by the source; geometric essence; good at / measured;
weaknesses; tags; expressibility hook into our surface; R9 risk.

### 2.1 Asymmetric (left/right or up/down, or non-mirror-symmetric)

**A1. "Twisted wall" waveguide (the Tritonia ancestor)** - attributed by Batik as an
accidental, now-lost shape produced by a bug in the design software.
Sources: https://at-horns.eu/tritonia.html (`primary (author)`).
Essence: the wall surface is sheared so the cross-section rotates about the axis as you
move down the horn; the mouth diagonal is no longer a mirror plane. Batik: "the walls of
a tested waveguide ... got a bit twisted. Checking the acoustic performance out of
curiosity, it was virtually perfect!"; the shape was abandoned because "there's no way
something ugly could sound really good", and "the original shape ... seems lost
forever". [verified]
Good at: author reports it was better than a large number of tested shapes, including
"far more exotic" ones; the final Tritonia had to *recover* that performance without the
twist. [verified author claim, no numbers]
Weaknesses: no formula, no dimensions, no polars; cannot be reproduced; the author
removed it for aesthetics, so no long-term reliability data.
Tags: asymmetric, organic.
Hook: add a length-dependent azimuth offset to the radius field,
`r(phi, s) = base(phi - phi0(s), s)` with `phi0(s) = twist_deg * (s/L)^p`. This is a
single new knob pair in the GRID radius-field evaluation; it breaks every mirror plane,
so the model must be full 360 deg (4x the quarter-model mesh).
R9: do NOT ship as "Tritonia" or "the Batik twist" (the shape is lost). Run as LABELED
HYPOTHESIS, attribution open, described as "author-reported twisted-wall experiment".

**A2. Single-sided / offset-coverage horn (odd-cosine azimuth term)** - no product name
found; the degree of freedom is named here only descriptively.
Sources: the repo's own refusal rule (`grid.py` 119-130) `[verified]`; Batik's rationale
for asymmetric mouths ("one has to make the mouth less symmetric - elliptical or
rectangular ... to eliminate the on-axis problems associated with most round
waveguides") https://at-horns.eu/tritonia.html `primary (author)`.
Essence: horizontal coverage differs left vs right (or the mouth is laterally offset),
so the horn aims energy at an asymmetric audience area; the surface is not invariant
under `phi -> pi - phi`.
Good at: [inferred] rooms/placements where the listening area is off-axis; the
Tritonia rationale is direct author evidence that *mouth asymmetry* fixes on-axis
problems, but that was elliptical/rectangular (still mirror-symmetric), not
single-sided.
Weaknesses: breaks the quarter/half symmetry basis; no published construction; risk of
steering the image.
Tags: asymmetric, multi-direction.
Hook: allow the first odd term `eps(s) cos(phi)` in the G8 radius field (or per-half
`a_h_left != a_h_right`). Full model only.
R9: LABELED EXPERIMENT; no name to protect.

**A3. JBL Bi-Radial "butt-cheeks" 2344A** - JBL trade name.
Sources: https://en.wikipedia.org/wiki/Horn_loudspeaker (Bi-Radial section) `secondary,
used only as a cross-check`; Peavey white paper (Bi-Radial description) `primary
(manufacturer)`.
Essence: a JBL-style diffraction slot feeding a bell whose horizontal and vertical
expansions are each radial (exponentially curved sides derived from two radial
formulas), with two different apparent apices. The 2344A is 100x100 deg, 1 kHz-12.5 kHz.
[unverified for the 100x100 number, tertiary]
Good at: constant beamwidth in both planes; no abrupt flare-rate breaks (the explicit
improvement over Mantaray's planar two-stage bell).
Weaknesses: astigmatic (ellipsoidal) wavefront because the apparent apices differ ->
only properly arrayable in one plane; the slot itself remains a diffraction/reflection
source.
Tags: none of the four (slot family).
Hook: two-stage per-plane surface with a prescribed slot station; could be a `rows` kind
with a station table (z, half-width, half-height, slot exit).
R9: name is a live trademark; describe generically as "slot-loaded dual-radial" if we
ever ship a preset.

**A4. Altec sectoral 511B / 811B (and the MR931)** - Altec's own term is "sectoral"
(not "biradial"); "Bi-Radial" is JBL/Keele.
Sources: Lansing Heritage 1968 sectoral brochure (scanned) `primary (manufacturer)`,
`[unverified]`; Peavey white paper: "Altec 'Sectoral' horns are popular examples of
radial horns" `primary (manufacturer)`; Wikipedia: radial horns + vanes in the mouth
for pattern control `secondary, used only as a cross-check`.
Essence: a radial flare (an exponential cross-section rotated about the axis) closed by
two straight side walls at the horizontal coverage angle, plus vanes in the mouth.
Good at: pattern control across most of the passband; simple, cheap sheet-metal
construction; the sectoral family is the canonical "constant-ish coverage" vintage horn.
Weaknesses: the exponential vertical component still beams at HF; vanes add internal
diffraction; no constant-directivity guarantee.
Tags: none (vane/radial family).
Hook: vane = internal septum -> reuse the multicell CAD/septa route, not the radius
field. The radial flare itself is `profiles.exponential` revolved.
R9: SAFE name (Altec); do not assert 511B=500 Hz / 811B=800 Hz / 90x40 without reading
the scan.

### 2.2 Organic

**O1. ATH Tritonia (rounded-rectangle morph of an azimuth-modulated OS-SE)** -
Batik's name.
Sources: https://at-horns.eu/tritonia.html `primary (author)`.
Essence: OS-SE profile with `alpha(theta)` and `s(theta)` azimuth laws, then morphed to a
rounded rectangle; the morph "seems to mimic the 'twisting' action by adding another,
slightly shifted diagonal"; mouth aspect ~0.86.
Good at: 100 deg nominal, "fairly constant from 800 Hz to 16 kHz" (Tritonia-F), stable
pattern "without flipping", no diffraction slots, exceptional throat impedance.
Weaknesses: originally infinite-baffle-optimised (needs a small/rounded baffle);
morphing costs some of the OS-SE purity; the azimuth law is "purely empirical" by the
author's own words.
Tags: organic, multi-direction-gradient, lobed.
Hook: see S1 (per-azimuth profile parameters).
R9: SAFE to attribute (CC-BY-4.0 author page with formulas). Do not call it "SIBINIC".

**O2. ATH CORE (superformula-modulated OS-SE)** - Batik's name.
Sources: https://at-horns.eu/core.html `primary (author)`.
Essence: 4-fold superformula term in the wall angle plus `cos^10` narrowing, `n` and `s`
varying with `cos^2(p)`, extended throat, 42 mm roundover, rounded-rect mouth.
Good at: "extremely low diffraction in the direct sound ... achieved by using the
smoothest profiles in every section"; designed for large-format drivers; fully
customisable script.
Weaknesses: author says he has not tried many variations; the formula is empirical; the
`cos^10` term is a strong horizontal narrowing that will interact with mouth size.
Tags: organic, multi-direction-gradient, lobed.
Hook: same as O1; the `sf(4,...)` term is a compact parameterisation of a 4-lobe
gradient.
R9: SAFE (CC-BY-4.0, explicit authorship).

**O3. Joseph Crowe "ES (Exponential Spiral)" flare + wrap-around mouth** - Crowe's trade
name.
Sources: https://josephcrowe.com/products/es-800-bi-radial-wood-horn ,
https://josephcrowe.com/products/es-1200-bi-radial-wood-horn ,
https://josephcrowe.com/sitemap_products_1.xml `primary (designer, commercial page)`.
Essence: ES-800 is 300x152x140 mm, 1" throat, loading to 800 Hz; ES-1200 is
222x120x95 mm, loading to 1200 Hz; both "bi-radial" with "wrap-around horn mouth" and an
"ES (Exponential Spiral) flare". No curve math, no coverage angles, no polars in text.
Good at: claimed "zero horn coloration", "extremely well behaved off-axis coverage right
up to 20 kHz", wide off-axis coverage for small rooms; CNC hardwood.
Weaknesses: no published construction; trade name; "wrap-around" mouth is visually
organic but dimensionally undocumented; the ES-1200 only works with two named drivers
per the page (rear-chamber tuning).
Tags: organic (wrap-around mouth), possibly gradient (spiral flare - unverified).
Hook: if "exponential spiral" means the flare line spirals in the mouth plane, that is a
2D mouth-outline spiral, not a wall law; treat as a mouth-outline generator on top of a
radial flare. Unknown until a drawing is obtained.
R9: "ES" and "Exponential Spiral" are Crowe's commercial names with no published
construction -> DO NOT SHIP UNDER THAT NAME. A generic "wrap-around lip" variant is
fine, attributed to "commercial practice (Crowe), construction unpublished".

**O4. JBL Image Control Waveguide (M2 / 3-series)** - JBL name.
Source: https://jblpro.com/en/innovation-directivity `primary (manufacturer)`
(marketing-adjacent).
Essence: a single blended waveguide with a central "nose" and side cheeks; patent
pending; "precisely controls ... in the vertical and horizontal planes"; developed with
FEA. No dimensions, no formula.
Good at: broad sweet spot, uniform directivity, smooth HF/woofer blend (manufacturer
claims only).
Weaknesses: geometry unpublished; cannot be parameterised from public sources.
Tags: organic.
Hook: none trustworthy; would be a reverse-engineered shape, not a typology.
R9: DO NOT SHIP UNDER THAT NAME.

### 2.3 Rippled / corrugated / lobed

**R1. G8 even-cosine lobed cross-section** - already ours (not a discovery).
Source: `grid.py` `a_k(s) cos(2k phi)` `[verified]`.
Verdict: PARTIAL COVER. Smooth lobes exist. Missing: sharp-valley petals (superformula
with low n), odd lobe counts, and any lobe *phase* rotation.

**R2. Mouth-edge serration / scalloped mouth (N-lobe ripple localised at the mouth)** -
no single attributed published construction; the prior repo survey lists it with a
diyAudio source `[unverified]`.
Sources: prior survey `docs/research/senior_pass_2026-10-24/appendix_A_typology_survey_raw.md`
`secondary, used only as a cross-check`; Batik's statement that a less symmetric mouth
removes on-axis problems `primary (author)` (indirect).
Essence: a periodic radial modulation of the mouth lip, `r += A * w(s) * cos(k phi)`,
optionally with alternating axial depth (square serration), so edge diffraction is
spread over angles instead of summing coherently on axis.
Good at: [inferred] on-axis ripple/diffraction smoothing; used in production monitors as
a moulded lip feature; cheap to print.
Weaknesses: if the lobe period approaches a wavelength the serration itself diffracts;
adds a new HF loss mechanism; no controlled study found.
Tags: rippled, lobed.
Hook: mouth-localised `cos(k phi)` term on top of the existing radius field (the G9
window `w_mouth(s)` already exists). Even k keeps quarter symmetry; odd k needs a half
or full model.
R9: LABELED EXPERIMENT; no name asserted.

**R3. Corrugated / scalar horn (microwave-antenna lineage)** - "corrugated horn",
"scalar feed horn".
Sources: no audio primary reached this session; the technique is standard in microwave
antenna texts (e.g. Clarricoats & Olver, *Corrugated Horns for Microwave Antennas*,
1984) `[unverified]` (not read); no audio paper found. `[inferred]` audio relevance.
Essence: a series of circumferential slots/rings (typically quarter-wave deep) on the
horn wall that impose a soft (balanced hybrid) boundary condition, giving symmetric
patterns and low cross-polarisation.
Good at: [inferred] pattern symmetry and sidelobe suppression in EM; a plausible
HOM/diffraction-control mechanism in audio, but no measured audio result was found.
Weaknesses: quarter-wave depth is frequency-specific -> narrow band for audio; adds
resonant cavities; manufacturing cost.
Tags: rippled/corrugated.
Hook: `r(s)` plus a periodic axial ripple, `r += A * sin(2 pi s / period)`, with
`period ~ c/(4 f0)`; or a stepped-impedance series. No frequency-independent story.
R9: DO NOT ATTRIBUTE TO ANY AUDIO DESIGNER. If attempted, "labeled experiment inspired
by microwave corrugated horns".

**R4. Stepped discrete-impedance horn** - prior survey candidate, no audio primary.
Source: prior survey `secondary, used only as a cross-check`.
Essence: piecewise radius steps, each acting as a local impedance discontinuity, claimed
to cancel HOMs.
Verdict: NOT SHORTLISTED; no audio measurement found, and the step is a diffraction
source by construction.

**R5. Twin Bessel secondary flare (Ramsa / Panasonic)** - Ramsa's name.
Source: https://en.wikipedia.org/wiki/Horn_loudspeaker (Twin Bessel) `secondary, used
only as a cross-check`.
Essence: Mantaray/Bi-Radial-like two-stage bell whose secondary flare rate is set by a
"dual series Bessel expansion formula".
Good at: [unverified] CD behaviour of the era.
Weaknesses: no formula reachable; historical, low relevance.
Tags: none.
R9: DO NOT SHIP UNDER THAT NAME without the Ramsa/JBL literature.

**R6. HCD - Hybrid Constant Directivity (Dario Cinanni)** - published family.
Source: https://en.wikipedia.org/wiki/Horn_loudspeaker (HCD section) `secondary, used
only as a cross-check`; primary is Voice Coil Dec 2019 + AES 148th Convention 2020
(not reached).
Essence: an algorithm that converts *any* expansion (exponential, hyperbolic, tractrix,
spherical, ...) into a constant-directivity horn; progressive CD along the mouth major
axis, circular-mouth-equivalent contour along the minor axis; claimed lower reflections
than multiflare CD horns.
Good at: keeps the original expansion's acoustic load while adding CD; low distortion at
high SPL (author claims).
Weaknesses: primary paywalled/unreached; "progressive" CD is not constant CD; mouth-ratio
dependent.
Tags: multi-direction-gradient.
Hook: a mouth-ratio-driven per-azimuth effective flare law -> same machinery as S1.
R9: name is published; do not implement until the AES paper is read.

### 2.4 Multi-direction gradient

**G1. ATH Tritonia azimuth coverage law** - see O1. The clearest documented
"wall angle varies with azimuth" construction.
**G2. ATH CORE superformula azimuth law** - see O2.
**G3. ATH TwinRay (H constant, V narrowing)** - Batik's name.
Source: https://at-horns.eu/twinray.html `primary (author)`.
Essence: R-OSSE + extended throat, enclosure-optimised; "constant directivity through
the midrange in the horizontal plane, and a gradually narrowing beamwidth in the
vertical plane"; 266x212x130 mm, LF point 680 Hz.
Good at: H stability + deliberate V narrowing for a home room; compact; good loading.
Weaknesses: by design not constant in V; the HF units trade vertical lobing at the
crossover.
Tags: multi-direction-gradient, asymmetric (H vs V behaviour).
Hook: our H/V profiles already allow different H and V expansions; what is missing is a
*named, documented* law plus the acceptance that V narrows with frequency.
R9: SAFE (author page, no formula published beyond the R-OSSE parameters).
**G4. JBL Progressive Transition (PT)** - JBL name.
Source: https://jblpro.com/en/innovation-directivity `primary (manufacturer)`.
Essence: one mathematically continuous surface from throat to a square/rectangular
flange, no traditional diffraction slot; compact family trades vertical pattern control
for depth; optimised family is rotatable.
Good at: "balanced frequency response, pattern control, and distortion"; rotatable for
vertical/horizontal use; low distortion (manufacturer).
Weaknesses: marketing-level description; no formula; compact family explicitly has
weaker vertical control.
Tags: none of the four strongly (smooth gradient of aspect ratio).
Hook: FREEFORM already morphs cross-sections round -> rounded rectangle; a PT preset is
mostly configuration, not new math.
R9: SAFE to describe; do not claim to reproduce "PT" without JBL data.
**G5. Quadratic-Throat Waveguide (Hughes / Peavey)** - patented/invented name.
Sources: Peavey white paper (read as text) `primary (manufacturer)`.
Essence: conical bell + circular-arc throat; the arc runs from the throat perimeter,
tangent to the straight wall, and its included angle equals ONE-HALF the dispersion
angle in that plane; the circular throat evolves into a rectangle via elliptical
fillets, so the wavefront stays normal to the walls; no secondary flange - a foam ring
at the mouth does the edge-diffraction job.
Good at: no astigmatism (both apparent apices moved to the throat centre); no flare-rate
breaks; 2nd harmonic 3-4 dB lower, 3rd harmonic ~9 dB lower than a standard CD horn;
vertical beamwidth better across the band except ~1 kHz and ~2 kHz; arrayable.
Weaknesses: quadratic area law is only in the throat; foam is a wear/consistency item;
loading is lower than a true horn (author's own "waveguide" framing).
Tags: none (throat-gradient law).
R9: SAFE name (published white paper + AES paper); the exact quadratic coefficients are
NOT in the white paper ("not within the scope") - so implement the *arc rule* and a
generic quadratic, not a claimed replica.
**G6. Acoustic lens (obstacle array / path-length refractor)** - generic device class,
JBL/Altec practice.
Source: Augspurger article `secondary (practitioner/engineering article)`.
Essence: a refractive device at the horn mouth. Two families: (i) obstacle array -
perforated plates/discs slow part of the wavefront (effective refractive index > 1);
(ii) path-length refractor - serpentine or slant plates force a detour. In the top view
the device is a diverging cylindrical lens: disperses in one plane, concentrates in the
other.
Good at: independent H/V control; ~90 deg solid angle from a perforated stack; <1% loss;
uniform 400 Hz-15 kHz in good designs; no tonal coloration claimed.
Weaknesses: band-limited (plate spacing must be << lambda; <= 0.5 in for 10 kHz);
astigmatic by design; multi-passage geometry is expensive to mesh and manufacture.
Tags: multi-direction-gradient, rippled (slat/plate arrays).
R9: SAFE generic name; JBL's specific lens part numbers should not be used.
**G7. Renkus-Heinz "Complex Conic" / CoEntrant** - manufacturer names.
Source: https://en.wikipedia.org/wiki/Horn_loudspeaker (multiple-entry section)
`secondary, used only as a cross-check`.
Essence: multiple drivers enter one horn at different axial stations through a "complex
conic" waveguide; pattern control through crossover.
Good at: point-source behaviour through crossover (manufacturer claim).
Weaknesses: driver-loading topology, not a wall-shape typology; the repo's owner already
scoped Synergy/MEH out.
Tags: none.
Verdict: roster only, not shortlisted.

### 2.5 Lineages that are named but not new-shape candidates

- **Iwata (Auto-Tech IWATA-300 / IWATA-200 / IWATA-600)**: 590x320x450 mm, 2" throat,
  450 Hz, depth/width 0.76; principle = width/height-ratio evolution + T=0.5 (Le Cleac'h's
  "quasi-Iwata"). No primary Iwata patent/paper has been found by either lane.
  Repo has `iwata_ar` (our AR stretch of a Le Cleac'h meridian). Missing: the real flare
  law. R9: RENAME-GATE (already recorded in the repo).
- **Yuichi A-290 biradial** (Japanese biradial; Crowe sells a CAD model and a
  smooth-transition throat adapter): no construction read; roster only.
- **TAD TH-4001 / TH-4003 biradial**: roster only, no source read.
- **JBL 2350 / 2360 / 2380 / 2385 (Bi-Radial), 2397 (Smith diffraction), 2405H (slot
  UHF), 2402 (bullet/ring-radiator tweeter)**: 2402 is NOT a biradial horn (integral
  bullet phase plug); 2405 is the diffraction slot UHF. Roster only.
- **Altec 1505 / 1504 multicell; MR42/64/94 Mantaray; MR931**: multicell already covered
  in repo; Mantaray = vertical diffraction slot + planar two-stage bell, ellipsoidal
  wavefront, arrayable in one plane (Peavey white paper, `primary (manufacturer)`).
- **EV CD horn (Keele 1975)**: hyperbolic/exponential throat + conical vertically flared
  radial bell + second flange; straight sidewalls in two sections; the first CD horn.
  Roster.
- **Community SQ90 flat-front radial**: one line in Wikipedia; roster.
- **Danley Paraline / Synergy**: prior survey; owner-scoped out. Roster only.
- **Crowe catalogue (types, as requested)**: ES biradial (250/450/600/800/1200/1600/
  2000), ES circular, E-250 dual-planar, E-800, Sabourin front horn, Co-entrant No.1416,
  shallow horn No.1928, ultra-wide No.2275, back-loaded horns, lenses No.1896/2258/2332,
  Azurahorn AH-1100, Yuichi A-290, AMT/dome waveguides. He does not publish formulas for
  any of them.

---

## 3. White-paper pass (shortlisted candidates)

### 3.1 S1 - Azimuth-modulated wall-angle OS-SE (Tritonia / ATH CORE laws)

**Sources.** Tritonia page (author, formulas); CORE page (author, full CC-BY script);
R-OSSE paper rev7 (author, axisymmetric baseline). All `primary (author)`.

**Construction.** Start from the R-OSSE/OS-SE meridian, but let the profile parameters
be functions of the azimuth `p` (Ath's angular variable), then evaluate one meridian per
azimuth and loft:

Tritonia (original, 1.4" version) [verified]:
```
alpha(theta) = 48.5 - 7*cos(2*theta)^5 - 16*sin(theta)^12     [deg]
s(theta)     = 0.7 + 0.2*cos(theta)^2
k = 1, n = 3.7, q = 0.995
```
ATH CORE (2" version) [verified]:
```
L = 260 mm, r0 = 25.0 mm, a0 = 1.2 deg
a(p) = 5 + 35*sf(4,12,15,16,1,0.618,p) - 15*cos(p)^10         [deg]
n(p) = 6.0 + 1.5*cos(p)^2
q = 0.996
s(p) = 0.6 + 0.23*cos(p)^2
s1 = 1.14, s2 = 0.025        (throat extension)
mouth morph: rounded rectangle, corner radius 16.5 mm, rate 3.0
mouth roundover radius 42 mm
```
`sf(m,n1,n2,n3,a,b,p)` is the Gielis superformula [verified, CORE page]. The Tritonia
used the same idea plus a morph to a rounded rectangle; the author says the final shape
is "simply symmetrical in the horizontal and in the vertical planes", i.e. the
azimuth law is even in `p` (mirror-safe), unlike the lost twisted ancestor.

**What it is good at (author claims + numbers).**
- Tritonia-F: 422x364 mm, nominal 100 deg, "fairly constant from 800 Hz to 16 kHz"
  [verified author].
- Tritonia: "no diffraction slots in the throat and so the acoustic impedance remains
  exceptionally clean through the whole band" [verified].
- CORE: "extremely low diffraction in the direct sound", BEM plots shown [verified
  author; not independently measured].
- The morph "seems to mimic the 'twisting' action by adding another, slightly shifted
  diagonal" and yields a stable pattern "without flipping" at mouth aspect ~0.86
  [verified].

**Weaknesses / design issues.**
- The azimuth laws are "purely empirical" (author's word) and have no derivation; the
  superformula term is a curve-fit, not a wavefront condition.
- A per-azimuth wall angle breaks the assumption that one meridian + a cross-section
  field describes the surface; the mesh must be lofted from N meridians, so mesh cost
  and self-intersection risk rise with lobe amplitude.
- `cos(p)^10` and `sin(theta)^12` are stiff; small parameter changes can produce a
  near-discontinuous derivative at the axes.
- Infinite-baffle vs free-standing matters: Tritonia was originally IB-optimised.

**Optimization knobs + typical ranges.**
`a_base` 30-55 deg; `lobe_amp` 0-15 deg; fold order `m` 2 or 4; `lobe_sharp`
(`n1,n2,n3` or a `cos^q` exponent) 4-16; `cos_pow` 4-10; per-azimuth `n` 2.5-6.5 and
`s` 0.5-1.0; mouth corner radius 10-30 mm; roundover 20-60 mm; `s1` 0.5-1.5, `s2`
0.01-0.05. Ranges beyond the two documented scripts are `[inferred]`.

**How practitioners rank it.** Batik's own ranking is BEM polar smoothness + absence of
on-axis ripple; the community metric in the ATH threads is "does the polar map stay
clean on the diagonal" (thread not read this session - `[unverified]`). Our layer can
score it with existing polar/DI/ripple terms; no new metric needed.

### 3.2 S2 - Helical twist `phi0(s)`

**Sources.** Tritonia page (author's account of the accidental twisted wall)
`primary (author)`. No formula, no dimensions.

**Construction.** Rotate the cross-section about the axis as a function of arc length:
```
r(phi, s) = r_base(phi - phi0(s), s)
phi0(s)   = twist_deg * (s/L)^twist_pow
```
`twist_deg > 0` gives a right-hand helix. Preserves local cross-section shape and local
wall angle exactly; changes only how they are stacked. Because the radius is sampled on
a fixed azimuth grid, the surface is a sheared loft, not a new profile.

**What it is good at.** Author report only: the accidental twisted version was "virtually
perfect" acoustically and better than "a quite large number of different shapes ...
from simpler to even far more exotic"; the final Tritonia was an attempt to recover that
performance in a symmetric shape [verified author claim, no numbers].

**Weaknesses.** No published polars; the shape is lost; a twist breaks left/right and
up/down symmetry, so every symmetry-based shortcut (quarter model, symmetry checks,
mirror-safe G8/G9) is invalid; the mouth outline rotates, which changes the baffle
interface.

**Knobs.** `twist_deg` -20..+20 deg `[inferred]`, `twist_pow` 0.5-3, optional
`twist_sign_flip` (S-shaped twist) 0/1.

**Measurement.** Diagonal polars become the informative cut; existing `bw_v`, DI and
ripple terms still apply; a new "mirror residual" metric is needed to quantify the
asymmetry (cheap: sample the surface and compare `r(phi)` vs `r(pi-phi)`).

### 3.3 S3 - Single-sided (odd-cosine) asymmetry

**Sources.** Repo symmetry basis (`grid.py` 119-130) `[verified]`; Tritonia page
(author's rationale for non-round mouths) `primary (author)`.

**Construction.** Add the first odd term to the radius field:
```
r(phi, s) = r_even(phi, s) * (1 + eps(s) * cos(phi))
eps(s)    = eps_m * (s/L)^eps_p
```
or, equivalently, let the horizontal half-angle differ by side:
`a_h(+x side) != a_h(-x side)`. The mouth centre shifts laterally; the throat stays
centred. Full 360 deg model only.

**What it is good at.** [inferred] aiming a wide horizontal pattern at an asymmetric
seating area; author evidence that non-round mouths remove on-axis artefacts (but for
mirror-symmetric ellipse/rectangle, not this).

**Weaknesses.** No published construction; image shift; breaks the quarter/half model
and the C2 symmetry contract; may interact badly with the G9 rollback.

**Knobs.** `eps_m` 0-0.3 `[inferred]`, `eps_p` 1-3, plus optional separate
`a_h_left`/`a_h_right`.

**Measurement.** L/R polar overlay and "coverage centroid" vs angle; energy balance
between the two sides.

### 3.4 S4 - Quadratic-Throat Waveguide (Hughes / Peavey)

**Source.** Peavey white paper (read as text)
https://excelsior-audio.com/Publications/QTWaveguide/QTWaveguide_WhitePaper.pdf
`primary (manufacturer)`.

**Construction (as described).**
1. Choose a conical bell with straight sidewalls at the design dispersion angles in H
   and V (e.g. 60x40).
2. Move the forward apparent apex back to the throat centre, so both planes share one
   apex (this is the anti-astigmatism step).
3. Mate the circular throat to the straight walls with a circular arc: the arc is
   tangent to the sidewall at one end and parallel to the horn axis at the throat
   perimeter; the arc's included angle equals ONE-HALF the dispersion angle in that
   plane.
4. The circular throat evolves into a rectangle via elliptical fillets where the final
   corners will be; the wider-angle dimension reaches its straight wall nearer the
   throat than the narrower one.
5. No secondary flange: a foam ring at the mouth edge handles midrange beaming.
The throat's area expansion is "in the form of a quadratic equation" - the coefficients
are explicitly NOT in the white paper (they are in Hughes' AES paper).

**Numbers.** Second harmonic "almost uniformly 3 to 4 dB better"; third harmonic
"averaged about 9 dB better" than a standard constant-coverage horn, same driver and
throat; slightly more output 600-900 Hz, 1.5-2.2 kHz, 7-10 kHz; vertical beamwidth
better across the band except ~1 kHz and ~2 kHz [measured, manufacturer].

**Weaknesses.** Lower loading than a true horn (author calls it a waveguide); foam is a
consumable; the quadratic coefficients are not public; the "no secondary flange" trick
depends on the foam.

**Knobs.** `coverage_h` 40-90 deg, `coverage_v` 20-60 deg, `throat_r` 12.7-25.4 mm,
`arc_ratio` (arc angle / half-angle) pinned at 1.0 documented, 0.6-1.4 `[inferred]`,
`foam_width_mm` 0-40, `foam_depth_mm` 0-20.

**Practitioner ranking.** The white paper is the ranking: A/B vs a "standard
constant-coverage horn" on response, H/V beamwidth, 2nd/3rd harmonic. No independent
community data read.

### 3.5 S5 - Acoustic lens (obstacle array / path-length refractor)

**Source.** Augspurger, "Acoustical Lens" (Audio magazine), read as text
https://www.tnt-audio.com/clinica/acoustic_lens.pdf
`secondary (practitioner/engineering article)`; JBL use confirmed in the same article.

**Construction.**
- Obstacle array: stack of perforated plates/discs at the horn mouth. Each obstacle
  slows the local wavefront (effective refractive index > 1); a concave stack diverges.
- Path-length refractor: serpentine (sound winds back and forth) or slant-plate (straight
  but oblique passages) plates. From the top the stack is a diverging cylindrical lens:
  disperses horizontally, keeps vertical concentration.
- Plate spacing must be small vs wavelength; the article's rule is <= 0.5 in for use to
  10 kHz.

**Numbers.** Perforated assembly gives a smooth pattern over ~90 deg solid angle;
"less than 1% of the energy passing through the device is lost" in a well-designed lens;
horn-lens combinations have maintained uniform dispersion 400 Hz to >15 kHz; a large
perforated unit is roughly an f/0.5, 150 mm focal-length optical equivalent
[measured/claimed, practitioner article].

**Weaknesses.** Band-limited by plate spacing; astigmatic by design (that is the point);
internal multi-passage geometry is expensive for BEM (thin gaps, many surfaces - the
same class of problem as multicell septa); manufacturing tolerance matters.

**Knobs.** `lens_type` {perforated, slant, serpentine}, `plate_gap_mm` 6-20,
`plate_count` 3-12, `slant_deg` 10-45, `lens_depth_mm` 10-80, `coverage_target` H/V.

**Practitioner ranking.** Historically judged by measured polar uniformity and A/B
"no coloration" listening; the article is the only source read.

### 3.6 S6 - Slot-loaded dual-radial (JBL Bi-Radial lineage)

**Sources.** Peavey white paper (Bi-Radial construction + failure modes)
`primary (manufacturer)`; Wikipedia (2344A 100x100, 1 kHz-12.5 kHz; Mantaray/Bi-Radial
history) `secondary, used only as a cross-check`; JBL PT page (the modern no-slot
alternative) `primary (manufacturer)`.

**Construction.** A narrow vertical diffraction slot at the end of a slow exponential
"tail" fills a two-stage bell. In the Bi-Radial the bell's H and V flares are each
radial (exponentially curved sides from two radial formulas), replacing the Mantaray's
planar flanges; the abrupt flare-rate breaks are removed but the slot and the two
different apparent apices remain.

**Numbers.** 2344A: 100x100 deg, 1 kHz-12.5 kHz `[unverified, tertiary]`; 2380A: 90x40,
2" throat `[unverified]`; 2350/2360/2385 exist `[unverified]`. Mantaray: adequate
loading for an 800 Hz crossover (white paper) `[verified]`.

**Weaknesses.** Ellipsoidal (astigmatic) wavefront; arrayable properly in only one
plane; slot diffraction/reflection; needs CD equalisation (~6 dB/oct, knee 2-4 kHz)
`[verified, Wikipedia cross-check]`.

**Knobs.** `slot_height_mm` 8-30, `slot_width_mm` 20-80, `slot_depth_mm` 20-120,
`bell_h_deg` 60-100, `bell_v_deg` 40-60, `radial_exponent` 0.5-2, `stage_split` 0.3-0.7.
All `[inferred]` except the qualitative construction.

**R9.** "Bi-Radial" is a JBL trademark and "Mantaray" an Altec trademark; ship generic
names ("slot-loaded dual-radial", "vertical-slot CD horn").

### 3.7 S7 - Mouth ripple / serration (N-lobe)

**Sources.** No primary construction. Indirect author evidence (Tritonia: non-round
mouth removes on-axis problems) `primary (author)`; prior survey lists serration with a
diyAudio source `secondary, used only as a cross-check` `[unverified]`.

**Construction.** `r(phi,s) = r_base(phi,s) * (1 + A * w(s) * cos(k*phi))`, with
`w(s)` the existing G9 smoothstep mouth window, `k` even to keep quarter symmetry, or a
square-wave/stepped version for a harder serration. Optionally add an axial depth term
so the lip alternates in and out (`dz_mouth(phi)`, already present as G9).

**What it is good at.** [inferred] decorrelating mouth-edge diffraction so the on-axis
ripple does not sum coherently; cosmetic/organic differentiation.

**Weaknesses.** No measured audio study found; the ripple is a diffraction source at HF
if the lobe period approaches a wavelength; reduces effective mouth area.

**Knobs.** `lobe_count` 6-24, `ripple_amp_mm` 0.5-6, `ripple_start` 0.7-0.95 (fraction
of s), `ripple_shape` {cosine, square}, `ripple_depth_mm` 0-10.

**Measurement.** On-axis ripple and 1/12-octave smoothing; polar map at the lobe
frequency; compare against unrippled baseline at matched mouth area.

---

## 4. Practitioner feedback

This section is deliberately thin: diyAudio was HTTP 403 for this lane and no forum
thread could be read. What is genuinely available:

| Shape | Report | Status |
|---|---|---|
| Twisted wall (S2) | Batik: accidental twist "virtually perfect"; better than a large number of tested shapes; abandoned for looks; original lost | `primary (author)` [verified] |
| Tritonia (S1) | Batik: final shape recovers the twist's performance without twisting; pattern stable "without flipping"; no diffraction slot | `primary (author)` [verified] |
| ATH CORE (S1) | Batik: "extremely low diffraction in the direct sound"; he has not tried many variants and invites others | `primary (author)` [verified] |
| TwinRay (G3) | Batik: H constant, V narrowing; deliberately not a multi-seat cinema horn; HF add-on units worsen vertical lobing at crossover | `primary (author)` [verified] |
| QT (S4) | Peavey: 3-4 dB 2nd harmonic, ~9 dB 3rd harmonic better; vertical beamwidth better except 1-2 kHz | `primary (manufacturer)` [measured] |
| Acoustic lens (S5) | Augspurger: no tonal coloration; <1% loss; 90 deg solid angle; plate-spacing rule | `secondary (practitioner/engineering article)` |
| Iwata / quasi-Iwata | Prior repo lane: builders report Iwata keeps most JMLC loading with closer driver spacing; a 3D-printed IWATA-300 replica is reported to "ring like a bell" (diyAudio ATH thread snippet, not re-read) | `secondary (practitioner reports)` `[unverified-today]` |
| ES / Crowe horns | Crowe: "zero horn coloration", "well behaved off-axis to 20 kHz", wide coverage; no independent reports read | `primary (designer, commercial page)` (testimonial-grade) |
| Bi-Radial / Mantaray | White paper is explicit that both are astigmatic and only one-plane arrayable; CD EQ needed | `primary (manufacturer)` + `secondary, used only as a cross-check` |

Open: the ATH diyAudio thread (338806) and thread 354772 contain the real build/measure
feedback for every S1/S2/S3 candidate and were not reachable. A follow-up lane with a
browser-capable fetch or an archived dump should mine them before any S1/S2 shape is
promoted from experiment to typology.

---

## 5. SHORTLIST - top 7 (ranked by evidence x novelty x cost)

Cost convention: `small` = config + <100 LOC; `medium` = 100-300 LOC + tests;
`large` = new mesh/CAD route (>300 LOC, new failure modes).

| # | Name as attributed | Tags | Source | Cost | Why it earns the slot |
|---|---|---|---|---|---|
| 1 | ATH CORE / Tritonia azimuth-modulated OS-SE (Batik) | gradient, lobed, organic | `primary (author)` | medium: per-azimuth profile parameters + loft (~200 LOC + config), reuses R-OSSE math | The only *documented, formula-level* wall-angle-vs-azimuth law in the whole sweep; two independent author designs (2-fold and 4-fold); directly fills the repo's biggest expressiveness hole (a(phi)); safe attribution (CC-BY). |
| 2 | Twisted wall / helical `phi0(s)` (Batik's lost ancestor) | asymmetric, organic | `primary (author)` (report only) | small-medium: `phi0(s)` in the radius field (~60 LOC) but forces full-360 models (4x mesh cost) | The strongest author claim of acoustic superiority for a genuinely asymmetric/organic shape anywhere in the sweep; a new geometric degree of freedom (shear/stacking) that no current family or row can express; trivially cheap to parameterise. |
| 3 | Single-sided / odd-cosine asymmetric flare (no attributed name) | asymmetric, multi-direction | repo symmetry rule + author rationale | small: relax the odd-term refusal + guard (~40-80 LOC, full model) | The repo currently *refuses* this class by construction; it is the natural next step beyond H/V asymmetry (left/right), and is cheap. Evidence for benefit is indirect, so it must ship as a labeled experiment. |
| 4 | Quadratic-Throat Waveguide (Hughes / Peavey) | throat-gradient, no-slot | `primary (manufacturer)` white paper | small: new march law (arc throat + conical bell, ~100 LOC + config + tests) | Best evidence-per-LOC on the list: explicit construction rule, explicit measured distortion wins, and it fills the "no diffraction slot + no astigmatism" gap that our OSSE/R-OSSE cannot express. |
| 5 | Acoustic lens (obstacle array / path-length refractor) | gradient, rippled (slats) | `secondary (practitioner/engineering article)` + JBL practice | large: internal multi-passage bodies, multicell-class meshing | The most distinct device class we do not have at all: independent H/V control by refraction rather than wall shape. Expensive, so it should be a deliberate owner-approved build, not an automatic add. |
| 6 | Slot-loaded dual-radial (JBL Bi-Radial lineage) | slot, dual-radial | `primary (manufacturer)` + `secondary` cross-check | medium-large: slot + two-stage bell station table (~250-350 LOC) | The owner explicitly asked for JBL biradial as a lineage, and the repo has no diffraction slot of any kind; the white paper also gives us the failure modes to score against (astigmatism, one-plane arrayability). |
| 7 | Mouth ripple / serration (N-lobe) | rippled, lobed | author rationale + prior survey | small: mouth-localised `cos(k phi)` + existing G9 window (~50 LOC) | Closes the "rippled" bucket cheaply; even lobe counts keep quarter symmetry; explicitly a labeled experiment because no measured study was found. |

Deferred / not shortlisted, with reasons:

- **HCD (Cinanni)** - genuinely interesting progressive-CD law, but the AES/Voice Coil
  primary is paywalled and unreached; do not implement from a Wikipedia summary (R9).
- **Twin Bessel, ES/"Exponential Spiral", Image Control, PT** - named constructions
  with no public math. PT is mostly expressible already (FREEFORM morph), so it is a
  preset candidate, not a new typology.
- **Corrugated/scalar horn, stepped horn** - no audio primary or measurement; high risk
  of shipping an EM analogy with no acoustic payoff.
- **Mantaray / sectoral-with-vanes** - valuable lineage, but the vane machinery is the
  multicell route we already own; not a new *search* surface. Revisit after the
  deferred WP14 multicell physics is resolved.

---

## 6. R9 risk flags (name gates)

| Name | Risk | Ruling |
|---|---|---|
| `SIBINIC` | No page, no archive snapshot, no sitemap entry, no GitHub code hit, no index-page mention; the name does not resolve to any construction | **DO NOT SHIP UNDER THAT NAME.** If the owner saw it in a live conversation/thread, the construction must be produced before use. Best available reconciliation: Batik's actual asymmetric multi-direction designs are Tritonia and ATH CORE (documented, formula-level). |
| `Iwata` / `IWATA-300` / `quasi-Iwata` | Product datasheet + Le Cleac'h's second-hand principle only; no Iwata patent/paper found by either lane; our `iwata_ar` AR law is ours | **RENAME-GATE** (already in repo). Ship as `lecleach_ar` / "AR-evolution reconstruction"; never as "Iwata". |
| `Tritonia` / `ATH CORE` | Safe to attribute to Batik (author pages, CC-BY-4.0), but the azimuth laws are empirical and the *twisted* ancestor is not Tritonia | Attribute S1 to Batik by name; ship S2 as a labeled experiment with no product name. |
| `Bi-Radial`, `Mantaray`, `Progressive Transition`, `Image Control`, `CoEntrant`, `Complex Conic` | Live trademarks; constructions partly unpublished | Use generic descriptors in code/config; cite the manufacturer in the dossier. |
| `ES` / `Exponential Spiral` (Crowe) | Trade name, no published construction | **DO NOT SHIP UNDER THAT NAME.** Generic "wrap-around lip" only. |
| `Quadratic-Throat Waveguide` | Published white paper + AES paper, but coefficients withheld in the white paper | Implement the documented *arc rule* + a generic quadratic; do not claim an exact replica. |
| `HCD`, `Twin Bessel` | Named published families, primaries unreached | Roster only until the paper is read. |
| "Geddes quadratic-lobed / multi-lobed" | Owner-directed but no such construction was found in any reachable source; the Geddes material that *is* verifiable is the oblate-spheroid waveguide, already covered as OSSE | **UNRESOLVED ATTRIBUTION.** Do not create a "Geddes lobed" typology. Ask the owner for the source. |
| Corrugated / scalar horn | No audio attribution found | Labeled experiment only; no designer's name. |

---

## 7. Open items for the owner

1. **SIBINIC provenance.** Please point at where you saw it (thread URL, post number, or
   a screenshot). Nothing reachable matches the name. If it was a chat/LLM suggestion,
   we should drop it and use the Tritonia/CORE laws as the real asymmetric-gradient
   starting point.
2. **Geddes "quadratic-lobed / multi-lobed".** Same request: a citation. Everything I
   can verify under Geddes is OS/OSWG (already OSSE). I did not invent a typology for
   it.
3. **diyAudio access.** The practitioner pass is the weakest part of this dossier
   because 338806/354772 returned 403. If the owner can supply an archived copy or a
   logged-in fetch, S1/S2/S7 should be re-ranked on real build reports.
4. **Iwata primary source.** Both lanes have now failed to find one. Decide whether to
   keep searching (Japanese-language sources, Auto-Tech archives) or permanently
   rename the row.
5. **Altec/JBL scanned literature.** The 1968 sectoral brochure, MR931 sheet and MR42
   Mantaray sheet are scanned images. If exact 511B/811B/2380A numbers are needed for
   the appendix, someone must OCR them or buy the prints; this lane will not assert
   them.
6. **Bi-Radial slot work is a solver question.** A slot means a non-monotone per-plane
   surface and thin-gap meshing - the same class of problem that deferred WP14. Do not
   schedule S6 before the multicell physics is resumed, unless the owner wants it as a
   CAD-only category first (like WP14's STEP route).
7. **Lens cost.** S5 is the only entry that needs a genuinely new mesh route. If the
   answer is "not now", the cheap subset is a *CAD-only* lens library (perforated plate
   stack) with no BEM, which still gives the search layer a new shape family to show.

---

## Appendix A - URLs actually read this session

Author / manufacturer primaries:

- https://at-horns.eu/tritonia.html
- https://at-horns.eu/core.html
- https://at-horns.eu/twinray.html
- https://at-horns.eu/gen2.html
- https://at-horns.eu/A460D.html
- https://at-horns.eu/opus12-vers.html
- https://at-horns.eu/index.html
- https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf (text extracted)
- https://jblpro.com/en/innovation-directivity
- https://excelsior-audio.com/Publications/QTWaveguide/QTWaveguide_WhitePaper.pdf
  (text extracted; also archived at
  https://web.archive.org/web/20160303231128/http://peavey.com/media/pdf/aa/qwp1.pdf ,
  which returned 503 this session)
- https://josephcrowe.com/products/es-800-bi-radial-wood-horn
- https://josephcrowe.com/products/es-1200-bi-radial-wood-horn
- https://josephcrowe.com/sitemap_products_1.xml
- https://josephcrowe.com/sitemap_articles_1.xml

Secondary / cross-checks:

- https://www.tnt-audio.com/clinica/acoustic_lens.pdf (text extracted)
- https://en.wikipedia.org/wiki/Horn_loudspeaker
- https://en.wikipedia.org/wiki/D._B._Keele_Jr.
- http://www.lansingheritage.org/html/altec/specs/components/sectoral.htm (image-only)
- http://www.lansingheritage.org/html/altec/specs/components/mr931.htm (image-only)
- https://www.technicalaudio.com/pdf/Altec_Lansing/Altec_MR42_Mantaray_Constant_Directivity_Horn.pdf
  (image-only)
- https://www.technicalaudio.com/pdf/JBL/ (index unreachable)

Repo files consulted:

- `docs/plan/12_RESEARCH_BASIS.md` (grep only: sections 4, 9, 11)
- `docs/research/typologies/SEARCH_LAYER_GAPS.md`
- `docs/research/typologies/MESHER_TYPOLOGIES.md`
- `docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md`
- `docs/research/senior_pass_2026-10-24/appendix_A_typology_survey_raw.md`
- `hornlab_search/design/generators/grid.py`
- `hornlab_search/design/generators/profiles.py`
- `examples/typologies/*.yaml` (listing + `lecleach_iwata_ar.yaml`)
- `docs/CODE_MAP.md`
