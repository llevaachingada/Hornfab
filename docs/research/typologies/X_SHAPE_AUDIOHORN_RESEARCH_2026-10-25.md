# AUDIOHORN X-SHAPE + "NEXT-GEN BI-RADIAL" RESEARCH (2026-10-25)

Owner directive 2026-10-25: research `https://audiohorn.net/x-shape-horn/` and similar typologies for
the **rectangular-mouth-with-clean-diagonal** reading of the "X horn" (the diagonal response should be
as good as the horizontal). This dossier extends `SALMON_X_HORN_EXPANSION_2026-10-25.md` s3 (which
found the family as a marketing referent only) with the maker's OWN pages, fetched in full this session.
Lane note: the dispatched librarian lane (lib-4) died on the provider outage; the orchestrator recovered
it by fetching the primaries directly. Append-only; corrections go in a dated table at the end.

## 0. Context (cite-and-skip)

The repo's `salmon_x_shape` builds the literal X/star rim (diagonal-out sign) today; a parallel code
lane (C2, owner-approved) adds the signed knob so the diagonal-in sign is selectable. Neither is this
reading. Here "X" = AudioHorn's trademarked product family: a rectangular-ish mouth whose SMOOTHED
DIAGONAL TRANSITIONS keep the diagonal polar clean. What follows is everything the maker publishes.

## 1. Source table

| Source | What it gives us | Status |
|---|---|---|
| audiohorn.net/x-shape-horn/ (fetched 2026-10-25, full text) | Per-model dims (cm), crossovers, round-over radii, drivers; polar/SPL images incl. a DIAGONAL polar for X40; the verbatim claim | primary (maker page with measurements); performance wording without numbers = marketing |
| audiohorn.net/sciences/cross-wavefront-syndrome/ (fetched 2026-10-25) | The mechanism story: why round-to-rect transitions diffract along the diagonals; their FEA "specific diagonal profile" fix; measurement-hygiene warnings | primary (maker explication; no formulas - their mechanism claims are engineering narrative) |
| audiohorn.net/next-gen-bi-radial-horn/ (fetched 2026-10-25) | Their biradial design story: "follows the Hypex formula surface law" + in-house FEA + FractFins throat-adapter tech; specs 48-60 cm wide, 90 deg H / 50 deg V, 500-700 Hz crossing; comparator polars (Arai A290/A480, TAD TH-4001) | primary (maker page); the competitor polar comparisons = marketing-flavored |
| SALMON_X_HORN_EXPANSION_2026-10-25.md s3 | Prior sweep verdict (marketing referent only) | in-repo, cross-check |
| Creative Commons badge on their measurement images (CC BY-NC-SA 4.0) | License for reuse of their figures | verified (page badge) |

## 2. AudioHorn X-Shape published numbers (per model, from the product page)

All printed as "Width / Height / Deep", plus recommended crossover (x-over Hz) and ideal round-over
radius. Walls: 6 mm printed (PETG/PLA), single piece (except X40). "All measurements are real ones,
performed with the ideal roundover return indicated for each horn, taken at 1/24 resolution in a
half-space presentation (+/-90 deg)." (verbatim)

| Model | W x H x D (cm) | W/H | D/W | Rec. crossover (Hz) | Recommended drivers |
|---|---|---|---|---|---|
| X-Shape 21 (1") | 21 x 13 x 12 | 1.615 | 0.571 | 1200/1400 | 18Sound ND1TP/1095N/1090; BMS 5530 |
| X-Shape 25 (1") | 25 x 15.6 x 14.2 | 1.603 | 0.568 | 1200/1250 | same 1" set |
| X-Shape 28 (1") | 28 x 17.5 x 15.3 | 1.600 | 0.546 | 1200/1250 | Wavecor WF275, 10-12" woofers |
| X-Shape 33 (1") | 33 x 20 x 19.6 | 1.650 | 0.594 | 1000/1150 | 18Sound 12LW1400, 12-14" |
| X-Shape 34 (1.4/1.5") | 33.9 x 21.1 x 20.7 | 1.607 | 0.611 | 700/800 | 18Sound NSD1460/1480; Faital HF1440/1460 |
| X-Shape 40 (1.4/1.5") | 40.8 x 24.8 x 23 | 1.645 | 0.564 | 650/750 | TAD 4002Z, JBL 2450SL, 15" woofers |

Observed regularities [verified from the table]: W/H is a nearly constant **1.60-1.65** across the whole
family and D/W sits in **0.55-0.61** - the family is a scaled series, not separate designs. Recommended
round-over radius scales with size (25 mm at X21/X25 -> 40 mm at X40) and the round-over kit is presented
as load-bearing for performance ("The full round-over fluid return is the most important point of
midrange narrowing and beaming removing, the horn allow it by a direct ending at 180 deg" - verbatim).

The published verbatim performance claim: **"The diagonal measurement of the X-shape is as perfect as
the horizontal one."** A diagonal polar map image IS published (X40 at least; also X25 diagonal in the
Syndrome page). No numeric diagonal table is published; the polars are images. Their polar claim of
constant directivity "on both axis" and "vertical constant directivity" is marketing wording unless read
off the images [unverified - images not machine-readable this session].

## 3. The "Cross Wavefront Syndrome" story (their mechanism, in our terms)

Their claims, near-verbatim, de-jargoned for our use:

- A wavefront keeps ~90 deg incidence to its edges; **round-to-rectangular transitions that are too
  abrupt cause an expansion-rate discontinuity at the edges, and the diffraction shows up primarily
  along the DIAGONALS** - a cross-shaped secondary wavefront ("Cross Syndrome").
- Their X-Shape fix: "Using advanced Finite Element Analysis (FEA), a specific diagonal profile is
  designed to ensure the wavefront maintains its integrity, even along these critical axes" - i.e. the
  diagonal is a DESIGNED SURFACE REGION, not a fillet afterthought. Also the product page: "Our gradual
  horn expansion prevents abrupt geometry changes, minimizing excitation of HOMs".
- Crucially, they say the MOUTH IS NOT THE CAUSE: "A proper wavefront should be round or elliptical,
  not cross shaped. **The horn mouth is not in cause, it's the overall profile.**" - the whole flare must
  evolve round -> (ellipse stage) -> rectangular, gradually; the diagonal shaping lives along the LENGTH.

R9 read: **no construction geometry is published** (no wall laws, no profile tables, no corner-radius
rules as a function of coverage). "FEA" is a method claim, not a recipe. Therefore nothing about an
implementation may ship under the name "X-Shape" (trademarked, and unverifiable); an implementation is
OUR labeled experiment per the x_shape/T5 precedent, e.g. a neutral name like
`rect_smooth_diagonal` / `salmon_x_shape` reading (a).

## 4. Their measurement-hygiene warnings - direct diagnostics value for our objective/reports

Four of their warnings map one-to-one onto things our stack can and should verify (all [verified, their
words], the mapping ours):

1. **Measure the diagonals**: "A horizontal polar is done at a 0 deg vertical position, and a vertical
   polar ... valid on two 2D planes." Symptom class is INVISIBLE in H/V cuts alone. Our equivalent: the
   balloon already stores 45/135-deg great-circle cuts - a **diagonal-consistency objective term**
   (compare |balloon| at 45/135 vs H/V per freq) is implementable WITHOUT new solves (lib-3 companion
   candidate; now justified by the maker's own argument - this is the cheapest high-value follow-up).
2. **Half-space vs full-space scale**: a "half-space" polar (180 deg displayed) over 360 deg data makes
   polars look better than they are. Our balloons are full-domain; our report polars should be checked
   for the same trap when comparing with maker-style images.
3. **Solid color bands of 2-3 dB hide problems**; gradient scales required. Our report heatmap palette
   (turbo-style gradient) is already the recommended form; the beamwidth/DI tables are numeric - fine.
4. **Polar maps starting at 0 dB (or +6..-3 flat) obscure the response.** Our report normalizes on-axis
   and starts negative - consistent with their advice.

Their honest note worth copying into our lexicon: SPL dips at 13-14 kHz on their plots are DIAPHRAGM
BREAKUP, "not the horn" - i.e. they attribute driver artifacts correctly; our f11 = 7,914 Hz caveat does
the same job for us (2" refs; 1" is above our bands).

## 5. The "Next-Gen Bi-Radial" (FractFins) page - context for our biradial lane

Their current biradial product line, verbatim-supported facts:

- "This horn follows the **Hypex formula surface law** and was developed using in-house FEA" + a
  "slight, smooth constriction in the throat adapter" extends CD control higher, removing the need for
  a super-tweeter. Fin tech "FractFins" tunes "energy in the initial degrees of high frequencies".
- Specs: width 48-60 cm, total length 30-36 cm by width, throat 1" or 1.4"/1.5", **90 deg horizontal
  coverage, 50 deg vertical** ("Vertical Polar (50 deg coverage at 5 kHz)"), "Effective crossing area
  500/700 Hz depending to size".
- Their diagnosis of CLASSIC biradials (Arai A290/A480, TAD TH-4001): "throat and fin reflections",
  "well-known midrange narrowing and beaming ... primarily due to the lack of full return and outdated
  fin management" - i.e. classic biradial pathology = beaming from the aperture + fin diffraction.
- No wall-law formulas published (the "Hypex surface law" sentence is attribution-wording on their own
  FEA-tuned design; the K-law cross-check is ours below).

**Cross-check against OUR K-law (ours, [inferred but consistent])**: a 90 deg horn from a 600 mm-wide
mouth starts controlling at f0 = 25400/(0.6*90) = 471 Hz; their stated 500-700 Hz effective crossing and
48-60 cm widths sit exactly on that line. Same check for X-Shape 40: 408 mm wide, 750 Hz crossover
-> 25400/(0.408*90) = 692 Hz for 90 deg; their 650/750 recommendation is again consistent. This is a
cheap sanity anchor for C1's biradial reference checks (independent of the Keele patent's own numbers).

## 6. Implementation shape for OUR stack (knob concept, ours-[inferred])

Reading (a) - rect mouth, smoothed diagonal - in our vocabulary:

1. **The load-bearing insight is "the mouth is not in cause, it's the overall profile"**: the shape is
   a gradual round -> ellipse -> rectangle morph with the diagonals smoothed along the LENGTH, not a
   mouth trim. In-repo, the natural home is the **morph machinery** (mesher keys: morph_target,
   morph_width_mm, morph_height_mm, morph_corner_mm, morph_rate; MOUTHS superellipse exponent + aspect)
   driven per-station on the grid route or a plain OSSE/FREEFORM generator config.
2. Cheapest v1: a CONFIG-ONLY candidate - OSSE or R-OSSE body + superellipse/rounded-rectangle mouth
   morph searched (morph_corner_mm + mouth exponent + W/H 1.6-1.65 + D/W ~0.55-0.61 from the family
   table as anchors) + the diagonal-consistency objective term. No new geometry code needed to try the
   class; a dedicated rows treatment (an explicit per-azimuth corner-radius law) is the v2 if the config
   route cannot express the diagonal plateau.
3. R9 label: ship as OUR experiment ("rect mouth, smoothed diagonal; [inferred]; inspired by the
   published AudioHorn family measurements; no published construction; not the AudioHorn product").

## 7. Corrections

None this session (no prior in-repo claim about AudioHorn specifics beyond the salmon dossier's
"marketing referent only" verdict, which this dossier confirms and enriches).

## 8. Open items for the owner

1. Whether to implement reading (a) as the cheap config-only route (item 6.2) NOW, together with the
   diagonal term, or wait for the signed-x v1 results (the C2 lane) before naming the rect-mouth class.
2. The diagonal-consistency objective term (lib-3 companion + this dossier item 4.1): add to objective
   v3 lane (recommended; no new solves).
3. Attribution/license: their images are CC BY-NC-SA 4.0 - cite only, never embed.
4. Their biradial page's "Hypex formula surface law" attribution is THEIR wording on THEIR design; our
   biradial work stays gated on the Keele patent (US4308932A) + the K-law consistency check above.

## 9. The FULL AudioHorn typology family (second pass 2026-10-25, owner directive: "fully research")

Six more pages fetched in full this pass (all "primary (maker page)" with their measurement-image
sets; performance wording without numbers stays "marketing"). Per-product record:

- **RX-Shape** (/horn/rx-shape/): "the rounded free-standing evolution of the X-Shape concept";
  "All measurements are identical to the corresponding X-Shape equivalent models, performed with the
  ideal simulated return". Models: RX25 = 30.7 x 21.3 x 14.2 cm, X/O 1200 Hz, cabinet 32 cm + 4 mm
  roundover; RX28 = 33.7 x 23 x 15.3 cm, X/O 1100/1200; RX34 = 41.6 x 29 x 20.7 cm, X/O 750 Hz.
  [measured from the table] W/H = 1.441/1.465/1.434 - the FREE-STANDING (rounded-footprint) series
  narrows the W/H aspect vs the baffle-mounted X series (1.60-1.65). Cabinet-width rule published:
  "A cabinet that is too wide will interfere with the natural directivity of the woofer" - the
  baffle IS part of the radiation boundary (our WP12 mounting story, maker-confirmed).
- **MX-Shape** (/horn/mx-shape/): modular big horn on "X-Shape technology"; widths 30-200 cm from a
  digital plan (STEP profile plan sold at 180 EUR - the maker DOES sell geometry files, unfetched);
  published coverage MENU: 90x60, 80x60, 80x50, 70x50, 60x40; 50 cm version measured 300 Hz-20 kHz
  (ND3T); comparative claims vs JBL 2360A/2365A and Manta-Ray ("midrange narrowing ... midrange
  beaming ... diffractions (dark red) from 1 to 15 kHz ... All theses defaults aren't present on
  MX-Shape") - comparative-marketing wording, no numbers.
- **OS-FEA** (/oblate-spheroid-horn/): "an optimized elliptical or round FEA Oblate Spheroid
  profile, **based on the Geddes formulation**, ... designed to free-standing usage"; "OS horns are
  inherently less efficient than the X-Shape family. If loading is the priority, consider the
  [RX-Shape]". - confirms OUR OSSE baseline positioning and gives the maker's own loading ranking
  (X > OS), consistent with our waveguide-loading research basis.
- **X-AMT** (/amt-waveguide/): Mundorf AMT U-series waveguide; the measured 17.1 cm version's
  SPL/polars published (images); "The SPL is linear, and allow a easy crowwover even in passive
  filtering" [sic]; no coverage angle, no prices, no construction.
- **PureShape** (/tweeter-waveguide/): dome-tweeter (SB26ADC / Bliesma T34B) waveguide,
  "Convex wavefront with **cut circular-to-rectangular transition**", coverage 90 x 70; widths
  18/22/24 cm; "All measurements are real ones ... with the ideal 25mm roundover return, taken at
  1/24 resolution"; published EQ recipe (+7 dB @ 3 kHz, +4 dB @ 7.5 kHz high shelves) and loading
  claim (+10 dB sensitivity at LF vs direct radiation); H3 distortion charts; FEA-optimized
  free-standing variant. [Note] "cut circular-to-rectangular transition" is the X-technology AT
  DOME-TWEETER SCALE - the family recipe is the same across sizes/sources, described differently.
- **ADAPT** (/technologies/adapt/): "Acoustic Constant Directivity Adapted to Psychoacoustic
  Technology" - the maker's name for the design philosophy: CD via FEA "throughout the entire horn
  profile, starting from the throat" + Toole-inspired psychoacoustics + critical-distance reasoning
  (listening zone 50/50-60/40). No formulas. It is the marketing/philosophy layer over the same
  "gradual full-profile transition" recipe.

### What the second pass adds to the X verdict

1. **Still no construction.** Across ALL family pages there is no wall law, no corner-radius rule,
   no morph-rate formula - "FEA" and "cut circular-to-rectangular transition" are method words. The
   published record: per-model dimensions + polar/EQ/distortion IMAGES + crossover/roundover
   recommendations. R9 verdict unchanged: the name stays theirs; an implementation ships as OUR
   labeled experiment (item 6.3 above).
2. **The family constants are now better anchored**: X series W/H 1.60-1.65 (baffle-mounted),
   RX series W/H ~1.44 (free-standing rounded footprint), D/W 0.55-0.61, roundover 25-40 mm,
   crossovers 1400 (X21) down to 650/750 Hz (X40/RX34); PureShape 90x70 at dome scale; MX menu of
   five coverage pairs. These anchor knob ranges for our rect-diagonal experiment.
3. **The diagonal is their headline and they published a diagonal polar** (X-Shape X40 + the
   Syndrome page's X25 diagonal) - the ONE measurement series that would let us compare our own
   rect-diagonal experiment against theirs qualitatively (images, machine-readable only by eye).
4. **Their baffle/cabinet-width rule** (RX page) is maker-confirmed evidence for treating the
   mounting boundary as part of the directivity system - relevant to our WP12 mounting research.

## 10. The remaining X decision (owner)

What is now research-complete and cheap: implement reading (a) as the config-only experiment
(item 6.2): an OSSE/R-OSSE/FREEFORM body + the rounded-rectangle/superellipse mouth machinery
searched within the family-anchored ranges + the **diagonal-consistency objective term** (45/135 vs
H/V from the already-stored balloon; no new solves; maker-justified by their own measurement-hygiene
section). This can ride objective v3 (S1 lane) or ship with plain v2 scoring first.

## Sources (complete family list, all fetched 2026-10-25)

- https://audiohorn.net/x-shape-horn/ + /sciences/cross-wavefront-syndrome/ + /next-gen-bi-radial-horn/
- https://audiohorn.net/horn/rx-shape/ + /horn/mx-shape/ + /oblate-spheroid-horn/
- https://audiohorn.net/amt-waveguide/ + /tweeter-waveguide/ + /technologies/adapt/
- CC BY-NC-SA 4.0 badge on their measurement images (cite only, never embed)
- In-repo companions: SALMON_X_HORN_EXPANSION_2026-10-25.md; SHAPE_DISCOVERY_SWEEP_2026-10-25.md;
  docs/plan/12_RESEARCH_BASIS.md s13.3

## 9. Full AudioHorn family sweep (added 2026-10-25, second owner directive: "fully research
these kinds of typologies")

Every remaining product/tech page of the X family, fetched in full this session. All quotes verbatim
unless marked. Statuses: "primary (maker)" for their own published pages (with the marketing caveat
where claims carry no measurements); images are CC BY-NC-SA 4.0.

### 9.1 RX-Shape (free-standing round-mouth variant) - audiohorn.net/horn/rx-shape/

- "RX-Shape horns are the rounded free-standing evolution of the X-Shape concept... retain all the
  acoustic qualities, loading behavior, and constant directivity performance of the X-Shape".
- **"All measurements are identical to the corresponding X-Shape equivalent models" [verified
  wording]** - i.e. the MAKER treats the rounded (non-rect) variant as acoustically INTERCHANGEABLE
  with the X-Shape. Published models: RX25 = 30.7 x 21.3 x 14.2 cm, crossover 1200 Hz; RX28 = 33.7
  x 23 x 15.3, 1100/1200 Hz; RX34 = 41.6 x 29 x 20.7, 750 Hz (1.4"/1.5" drivers). Note the RX dims
  are LARGER than the same-number X (X25 was 25 x 15.6 x 14.2): the free-standing round shape
  encloses more area.
- Implementation-relevant story: "use the specified width of the supporting cabinet... A cabinet
  that is too wide will interfere with the natural directivity of the woofer" - the CABINET width
  is treated as part of the mouth's boundary condition (our WP12/enclosure mounting adjacent).

### 9.2 MX-Shape (modular big horns) - audiohorn.net/horn/mx-shape/

- "modular approach based on X-Shape technology"; "customization of the horn width (30cm to 200cm)
  without affecting price"; throat modules 1.4"/1.5" (PLA or MJF); wood profile built by them.
- Published coverage MENU (the only place the X family states coverage angles): **90*60, 80*60,
  80*50, 70*50, 60*40** [primary (maker)].
- Sold artifacts: STEP profile plan EUR 180 (OEM) - the geometry IS their saleable artifact; we
  did not buy/inspect it.
- Measurement (50 cm version, 18Sound ND3T, 300 Hz-20 kHz): horizontal + vertical polars + DI image;
  their JBL 2360A comparison claims midrange narrowing/beaming + 1-15 kHz "dark red" diffraction
  on the 2360 "not present on MX-Shape" [marketing-grade comparison; images not machine-readable].

### 9.3 OS-FEA (Geddes-lineage OS waveguide) - audiohorn.net/oblate-spheroid-horn/

- "an optimized elliptical or round FEA Oblate Spheroid profile, **based on the Geddes
  formulation**, with customizable coverage and size" [primary (maker), wording].
- "OS horns are inherently less efficient than the X-Shape family. If loading is the priority,
  consider the RX-Shape" - the maker's own ranking of the OS class vs their X family.
- Relevance to us: this is an independent maker's COMMERCIAL claim that the Geddes OS waveguide
  (the OSSE lineage's origin) loads worse than their rect-transition family - consistent with our
  own search-layer finding that mouth/loading terms need care, but marketing-level.

### 9.4 X-AMT (Mundorf AMT U-series waveguide) - audiohorn.net/amt-waveguide/

- "The Constant Directivity Waveguide for AMT": baffle-mounted, M4, 4 mm corner radii; measured
  version 17.1 cm on Mundorf AMTU80W1.1 ("The SPL is linear..."); NO coverage angles, prices or
  geometry published on the page; the "X" here reads as branding continuity with X-Shape [primary
  (maker); construction absent].

### 9.5 PureShape (dome-tweeter waveguide) - audiohorn.net/tweeter-waveguide/

- "It uses a **brand-new cut circular-to-rectangular transition**, achieving constant directivity:
  **90 deg horizontal x 70 deg vertical**" [primary (maker)] - THE X-technology's transition rule,
  stated almost as explicitly as the family gets: a gradual circular-to-rectangular CUT. Drivers:
  SB26ADC / Bliesma T34B; widths 18/22/24 cm (+23 cm T34B version); 25 mm roundover recommended;
  polar plots (horizontal + vertical per width) published as images; EQ recipe +7 dB @ 3 kHz /
  +4 dB @ 7.5 kHz (Q 0.707) documented; FEA-optimized free-standing variant offered.
- The 90x70 coverage with W/H ~ 1.29-ish aspect (H unpublished) is the family's tweeter-scale
  datapoint: the X-Shape compression-driver line is W/H ~ 1.6-1.65 at 90x60 - consistent with
  mouth aspect tracking the K-law coverage ratio (90/60 = 1.5; their 1.6 adds rounding).
- "For bigger sizes X-Shape Horn with Compression Drivers are advised" - the dome/AMT scales are
  the same family tech at smaller sizes.

### 9.6 ADAPT (their design philosophy) - audiohorn.net/technologies/adapt/

- "ADAPT... Acoustic Constant Directivity Adapted to Psychoacoustic Technology": consistent directivity
  "without relying on unintended diffraction"; psychoacoustic framing "inspired by the research of
  Dr. Floyd E. Toole"; "advanced computer simulations (FEA) and meticulously designed fluid dynamics,
  ADAPT achieves flawless and consistent wavefront control across all frequencies throughout the
  entire horn profile, starting from the throat"; the full roundover return "completely eliminated"
  midrange narrowing/beaming [primary (maker), marketing-level; NO formulas, NO numbers].

### 9.7 The consolidated X-family reading (what "these kinds of typologies" actually are)

Across nine pages, the family recipe is consistent and now well-sampled:

1. A **gradual, full-profile circular -> ellipse -> rectangular transition** ("Cut" transition;
   "The horn mouth is not in cause, it's the overall profile"), shaped by in-house FEA; the mouth's
   corners and the DIAGONALS are tuned surfaces, not fillets.
2. **Mouth aspect tracks coverage** across their published scales (X-Shape 1.60-1.65 W/H; PureShape
   90x70 at dome scale; MX coverage menu).
3. **The roundover/mounting boundary is part of the design** (25 mm+ returns; cabinet width
   coupling) - directly adjacent to our WP12 enclosure-mounting knobs.
4. **Diagonal measurement is their headline checkable claim**; they publish diagonal polars (X40,
   X25) and warn the cross-syndrome is INVISIBLE in H/V polars - which is exactly our
   diagonal-consistency objective term justification (lib-3 companion + this dossier's item 4.1).
5. Still ZERO published construction (no wall laws, no coefficients, no STEP content). R9 verdict
   unchanged: nothing ships under their product names; the honest implementation is OUR
   labeled experiment ("rect mouth, smoothed diagonal; [inferred]; measured referents =
   the published AudioHorn family polar images").

### 9.8 What we can build from this sweep (knob/term candidates, refreshed)

1. **rect_smooth_diagonal v1 (ours, labeled)**: OS-SE or R-OSSE body + a gradual
   superellipse/rounded-rect mouth morph with the mesher's OWN morph keys (morph_target/
   morph_corner_mm/morph_rate exist; MESHER_TYPOLOGIES s-recorded) + MOUTHS superellipse exponent.
   Anchors: W/H 1.60-1.65, D/W 0.55-0.61, coverage 90x60 (X-Shape 90*60-class), mouth "cut"
   gradualness as the searched knob. Config-first (the cheap subset from the sweep dossier's 3.4).
2. **The diagonal-consistency objective term** (45/135-balloon vs H/V): now backed by the maker's
   own measurement-hygiene argument (9.4); implementable in objective v3 WITHOUT new solves.
3. **Cabinet/boundary coupling** (WP12 adjacent, later): their RX cabinet-width recommendation is
   the same physics our enclosure mounting models - note only, owner-gated GUI work.

## 10. Corrections (append-only)

None this session - the expansion added coverage, it did not contradict section 6.2's cheap-route
reading. One sharpening (this replaces "the diagonal knob" uncertainty in section 6): the family
texts pin the mechanism to the FULL-PROFILE gradual transition (not a mouth-trim), so the v1 route
in 9.8.1 (config + existing morph keys) is the correct first build.