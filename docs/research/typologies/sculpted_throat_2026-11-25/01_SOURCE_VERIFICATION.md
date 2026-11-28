# Source Verification — Sculpted-Throat Typology

> **Local correction 2026-11-25 (orchestrator):** this web pass could not open diyAudio, so it lists the ST260-BLD recipe as unverified. The author's own STL/STEP (at-horns.eu/ext, downloaded locally) was then sectioned: the transcribed R-OSSE recipe (`a0 = 8 - 35*sin(p)^4`, a 39.5, k 3, r 0.25, b 0.29, m 0.82, q 4.5) reproduces the CAD wall to 0.082 mm RMS over z 0-50 mm with no rotation. See `02_REFERENCE_AND_REPO_AUDIT.md` s2. The remaining forum-only items (M2-inspired slot, Tritonia-X, the p.775 debate) stay unverified.
**Date verified:** 2026-11-25  
**Verifier:** automated web-fetch + PDF read  
**Purpose:** handoff pre-flight for sculpted/non-round throat implementation research

---

## Access notes

- **diyAudio.com** — all pages return HTTP 200 with Cloudflare browser-challenge
  content (77 bytes, "Validating browser…"). No forum content is accessible via
  automated fetch. All diyAudio sources below are recorded as
  **inaccessible (Cloudflare 200/challenge) on 2026-11-25**.
- **web.archive.org** — permanently blocked by fetch proxy; not retried.
- **at-horns.eu** — main page HTTP 200; /documentation, /guide, /manual, /help all
  return 404.
- **audiohorn.net** — HTTP 200, full content returned.
- **patents.google.com** — HTTP 200, full content returned (claims partially
  summarised from truncated page; spec text verbatim).

---

## 1. ATH4 thread — ST260-BLD R-OSSE config

**URLs checked:**
- https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-549
- https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-545
- https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-525
- https://www.at-horns.eu/ (checked for ST260-BLD page and license)

**Access status:** inaccessible (Cloudflare 200/challenge) on 2026-11-25 for all
diyAudio pages. at-horns.eu homepage accessible but contains no mention of "ST260-BLD."

**Evidence label:** [unverified] for all claimed forum-thread values.

### R-OSSE paper reference example (verified source)

The R-OSSE paper (Marcel Batik, December 2022; at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf;
HTTP 200; PDF read on 2026-11-25) contains a "Practical design example" labelled as "an
approximation of a device that has been around for some time, known as 'ST260'":

| Parameter | Paper example (ST260 approx.) | Claimed ST260-BLD | Discrepancy |
|-----------|------------------------------|-------------------|-------------|
| R (mm)    | 130                          | 130               | none        |
| r0 (mm)   | 12.7                         | 12.7              | none        |
| a0 (deg)  | 7.5 (scalar)                 | 8 - 35\*sin(p)^4 (expression) | YES — paper shows scalar; claimed uses azimuth expression |
| a (deg)   | 39                           | 39.5              | minor       |
| k         | 1.8                          | 3                 | YES — substantial |
| r         | 0.3                          | 0.25              | minor       |
| b         | 0.3                          | 0.29              | minor       |
| m         | 0.8                          | 0.82              | minor       |
| q         | 3.7                          | 4.5               | YES — substantial |

**Evidence label for paper values:** [published] — R-OSSE Waveguide rev7.pdf, Marcel Batik,
December 2022, https://www.at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf

The paper's footnote identifies R=130, r0=12.7 as approximating "ST260", not "ST260-BLD".
The BLD suffix and the larger k/q values and the azimuth-expression a0 are forum-only claims
and are [unverified].

### License

- at-horns.eu homepage and ATH User Guide (Ath-4.8.2-UserGuide.pdf, HTTP 200, PDF read
  2026-11-25) state: "Freeware version for personal non-commercial use" and "free for
  non-commercial use." No CC BY-NC-SA 4.0 wording found in any accessible source.
- **Claimed CC BY-NC-SA 4.0:** [unverified] — not found on at-horns.eu.

### ">12 kHz" performance warning

Not found in any accessible source (forum pages inaccessible). [unverified]

### Orientation / p=0 convention

ATH User Guide §2.1.2 states: "p ... represents the angle around the horn (i.e. 0–360°)."
No explicit statement of which physical axis corresponds to p=0 was found in the User Guide
or R-OSSE paper. The diyAudio thread pages where orientation is documented are inaccessible.
[unverified] whether "pinch is on V or H axis."

### a0 as azimuth expression

ATH User Guide §4.1.1 (page 18) defines `Throat.Angle = 0` with type `ex`
(general mathematical expression). This confirms ATH supports a0 as a function of p.
Whether the R-OSSE formula itself is designed for a variable a0 is not stated in the paper;
the paper shows only scalar examples. Using a variable a0 is a software-level extension.
[published] for ATH's `ex` type; [unverified] for the specific ST260-BLD expression.

---

## 2. ATH4 p.332/p.326 — M2-inspired variable-slot config

**URLs checked:**
- https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-332
- https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-326

**Access status:** inaccessible (Cloudflare 200/challenge) on 2026-11-25.

**All claimed values** (diameter 36 mm, Length 150, k=0.9, s=0.9, q=0.996, corner 8 mm,
Slot.Length D(p)=45-42\*sin(2p)^4, Coverage.Angle 62-10\*sin(p)^2-10\*cos(2p)^4,
n=3+5\*sin(2p)^2) are **[unverified]**.

### ATH Slot.Length semantics (verified)

ATH User Guide §4.1.1 (page 18) defines:  
`Slot.Length = 0` — "Axial length of an initial straight waveguide segment [mm]."  
This is an initial straight tube added at r0 before the horn flare begins. It is not
carved from the nominal Length; it is added to the front of the device.
**[published]** — ATH 4.8.2 User Guide, Marcel Batik, https://at-horns.eu

---

## 3. ATH4 p.701 — Tritonia-X

**URL checked:**
- https://www.diyaudio.com/community/threads/acoustic-horn-design-the-easy-way-ath4.338806/page-701

**Access status:** inaccessible (Cloudflare 200/challenge) on 2026-11-25.

**Additional finding:** Fetching at-horns.eu/tritonia.html and related pages on 2026-11-25
revealed the official Tritonia product line consists of four variants: Tritonia-XS,
Tritonia-S, Tritonia-M, and Tritonia-F. No "Tritonia-X" variant exists in the official
product line. The "Tritonia-X" name appears to originate in a diyAudio forum post,
not in an at-horns.eu product page.

**All claimed values** (diameter 36, a0=0, Length 140, n=3.7, q=0.995, morph rate 3,
corner 4, target width 400, Slot D(p)=20\*sin(p)^4,
angle 38-20\*cos(2p)^5-25\*sin(p)^12, s=0.7+0.2\*cos(p)^2) are **[unverified]**.

**Note:** The official Tritonia-S definition file (at-horns.eu/ext/Tritonia.txt, accessed
2026-11-25) uses a Coverage.Angle expression of 48.5-7.0\*cos(2.0\*p)^5.0-16.0\*sin(p)^12.0,
which is structurally similar to the claimed Tritonia-X angle formula. The claimed Tritonia-X
parameters are likely a forum-shared user variant of the Tritonia-S configuration.

---

## 4. Beyond the Ariel p.775 — mabat vs NicoB on X-Shape throat

**URL checked:**
- https://www.diyaudio.com/community/threads/beyond-the-ariel.223988/page-775

**Access status:** inaccessible (Cloudflare 200/challenge) on 2026-11-25.

No accessible cached or archived version was found.

**Summary:** [unverified] — unable to retrieve posts ~#15481–15485. No neutral summary can
be provided without accessing the source. The names "mabat" and "NicoB" and the topic
of X-Shape horizontal throat narrowing vs diagonal behaviour were not found in any
accessible source.

---

## 5. AudioHorn — X-Shape product dimensions and MX-Shape modular throat

### 5a. X-Shape horn product table

**URL:** https://audiohorn.net/x-shape-horn/ — HTTP 200, full content retrieved 2026-11-25.

**Evidence label:** [published]

| Model | W x H x D (mm)  | Driver throat | Rec. crossover (Hz) | Round-over radius (mm) |
|-------|-----------------|---------------|---------------------|------------------------|
| X21   | 210 x 130 x 120 | 1"            | 1200–1400           | 25                     |
| X25   | 250 x 156 x 142 | 1"            | 1200–1250           | 25                     |
| X28   | 280 x 175 x 153 | 1"            | 1200–1250           | 25                     |
| X33   | 330 x 200 x 196 | 1"            | 1000–1150           | 30                     |
| X34   | 339 x 211 x 207 | 1.4"/1.5"     | 700–800             | 30                     |
| X40   | 408 x 248 x 230 | 1.4"/1.5"     | 650–750             | 40                     |

**Claimed values vs verified:**
- X21 210x130x120: CONFIRMED.
- X40 408x248x230: CONFIRMED.
- No "return radius" column appears on the page; the round-over values above are the
  baffle/edge round-over radius, not an internal return radius.
- Exit throat listed only as driver size (1" or 1.4"/1.5"), no exit dimension table found.

Additional note from page: "The diagonal measurement of the X-shape is as perfect as the
horizontal one" — this addresses cross-wavefront syndrome without attributing it to throat
geometry changes.

### 5b. MX-Shape modular throat

**URL:** https://audiohorn.net/horn/mx-shape/ — HTTP 200, full content retrieved 2026-11-25.

**Evidence label:** [published]

The MX-Shape uses a modular design where the throat module is manufactured separately from
the horn profile. The throat module is offered in PLA, PETG, or MJF (Multi Jet Fusion) for
1.4" or 1.5" driver exits. For OEM customers, only the throat (3D-printed) and a STEP profile
plan are supplied; the horn width can range from 30 cm to 200 cm. No fixed throat dimensions
(no entry/exit coordinates, no radius values) are stated on the page.

---

## 6. Patents

### 6a. US9924249B2 — Harman/Sprinkle (continuation)

**URL:** https://patents.google.com/patent/US9924249B2 — HTTP 200, 2026-11-25.  
**Title:** "Loudspeaker Horn"  
**Inventor:** Charles M. Sprinkle  **Assignee:** Harman International Industries, Inc.  
**Priority:** 2012-01-09  **Grant:** 2018-03-20  
**Evidence label:** [published]

Specification (verbatim text confirmed) describes a horn with a contoured surface bearing
"dimples" (protruding outward away from the axis, into the surface) and "protuberances"
(protruding inward toward the axis, outward from the surface) near the first axial end. These
create a throat depth that varies around the circumference: the longitudinal distance from the
entrance to the first axial end of the contoured surface is explicitly stated to vary — shorter
at 12/6 o'clock (dimple positions), longer at 9/3 o'clock (protuberance positions).

The specification states explicitly: "the cross sectional area of the throat may remain
substantially constant, contract, or any combination thereof" — contracting throat area is
permitted (spec, not a specific claim number; claims 1–10 address coverage-pattern independence
and surface irregularities generically in claims 6–7). Claims 11+ not fully retrieved;
the depth-variation feature may be claimed there.

The word "sculpted" does not appear. No Bezier or parametric curve language appears.

This patent is a continuation of US9386361B2 (filed 2016-02-22 from parent's 2013-01-08 filing).

### 6b. US9386361B2 — Harman/Sprinkle (parent)

**URL:** https://patents.google.com/patent/US9386361B2 — HTTP 200, 2026-11-25.  
**Title:** "Loudspeaker Horn"  **Assignee:** Harman International Industries, Inc.  
**Priority:** 2012-01-09  **Grant:** 2016-07-05  
**Evidence label:** [published]

Specification verbatim confirms (same description as 9924249):
- Throat depth varies around circumference (D12 < D9 in example).
- Inward protuberances and outward dimples both described by name.
- "The cross sectional area of the throat may remain substantially constant, contract, or
  any combination thereof" — contracting throat area explicitly permitted (spec text, not a
  numbered claim in claims 1–10 as retrieved).
- No Bezier curves or parametric throat formulas mentioned anywhere in the patent.
- Coverage pattern independence (from entrance and mouth shapes) is the primary claim concept.

US9924249B2 confirmed as a direct continuation of this patent.

### 6c. US11012773B2 — Bezzola/Samsung

**URL:** https://patents.google.com/patent/US11012773B2 — HTTP 200, 2026-11-25.  
**Title:** "Waveguide for smooth off-axis frequency response"  
**Inventor:** Andri Bezzola  **Assignee:** Samsung Electronics Co., Ltd.  
**Priority:** 2018-09-04  **Grant:** 2021-05-18  
**Evidence label:** [published]

The specification describes three cross-sectional profiles at distinct azimuthal planes:
- Profile 200: vertical direction
- Profile 210: horizontal direction
- Profile 220: 45-degree (oblique) direction

Each profile is defined by a cubic Bezier curve (curves 270, 280, 290 in Fig. 5B). Each
curve has five degrees of freedom: throat tangency angle, throat tangency strength, outer
radius at mouth, mouth tangency angle, mouth tangency strength. A single optimisation varies
these 13 parameters simultaneously (outer radius shared) to achieve smooth off-axis response.
The word "meridian" does not appear in the patent.

Claims 9 and 18 state the shape "is based on one or more cross sectional profiles defined by
one or more cubic Bezier curves" without specifying the three azimuthal angles explicitly.
No claim is written around specific azimuthal angles (0°, 45°, 90°) or the throat geometry
at named azimuths. The ridge/recess topology (four ridges, clover-like recesses) is claimed
in claims 7, 8.

---

## 7. ATH documentation — OSSE a0 sign convention and azimuth expression

**Sources consulted:**
- R-OSSE Waveguide rev7.pdf (Marcel Batik, December 2022; at-horns.eu; [published])
- ATH 4.8.2 User Guide (Marcel Batik; at-horns.eu; [published])
- at-horns.eu Tritonia product page (accessed 2026-11-25; [published])

### a0 sign convention

The R-OSSE paper parameter table defines:
- `a0` = "throat opening angle (\*0.5)" with unit degrees.
- The "\*0.5" annotation means a0 is the half-included angle (the full throat cone
  half-angle is a0, giving a total included angle of 2\*a0).
- In the paper's practical example a0 = 7.5 deg (positive scalar, full included = 15°).
- In the ATH User Guide, the equivalent is `Throat.Angle = 0` defined as "throat opening
  angle, where applicable. This value is half the included angle [deg]."
- Positive a0 opens the throat cone outward from the axis. a0 = 0 gives a cylindrical
  throat junction.

### a0 as azimuth expression (R-OSSE in ATH)

The ATH User Guide §4.1.1 defines `Throat.Angle` with type `ex` (general mathematical
expression), which the User Guide §2.1.2 states can use "a parameter p which represents
the angle around the horn (i.e. 0–360°)." Therefore, ATH accepts a variable Throat.Angle
as a function of p. Whether the R-OSSE formula itself is internally consistent when a0
varies around the circumference is not addressed in the R-OSSE paper (which shows only
scalar a0 examples). This is an ATH software feature, not a property of the R-OSSE
mathematical formula per se.

---

## Implications for implementation

- **R-OSSE reference example ≠ ST260-BLD.** The R-OSSE paper's ST260 approximation
  (k=1.8, q=3.7, a0=7.5 scalar) differs substantially from the claimed ST260-BLD
  (k=3, q=4.5, a0 expression). The BLD variant is forum-only and unverified.
- **a0 azimuth expression is ATH-software-level.** The R-OSSE formula has no intrinsic
  support for a variable a0; ATH exposes this via its `ex` parameter type. Implementers
  must decide whether to treat a0(p) as a sculpting mechanism applied before or during
  the R-OSSE profile computation.
- **Slot.Length is prepended, not carved.** An initial straight segment of Slot.Length mm
  is added before the horn flare; total device depth = Slot.Length + Length.
- **Tritonia-X is not an official at-horns.eu product.** It is a user-defined forum
  configuration, likely a variant of Tritonia-S. All Tritonia-X parameters are unverified.
- **X-Shape horizontal vs diagonal claim (item 4) cannot be neutrally summarised** without
  accessing the diyAudio thread.
- **Harman patents permit contracting throat area** explicitly in the specification
  (US9386361B2 / US9924249B2). No specific claim language was found restricting
  throat area monotonicity.
- **Bezzola/Samsung (US11012773B2) defines H, V, and 45° profiles each by a cubic Bezier**
  in the specification, but the claims are written broadly ("one or more" profiles/curves);
  the three-meridian structure is an embodiment detail, not a narrowly claimed element.
- **License for ATH/R-OSSE:** confirmed as "free for non-commercial use" only;
  CC BY-NC-SA 4.0 not found in any accessible source.

---

## Source status table

| # | Source | URL | Access date | Status |
|---|--------|-----|-------------|--------|
| 1a | ATH4 p.549 (ST260-BLD) | diyaudio.com/…/page-549 | 2026-11-25 | inaccessible (Cloudflare) |
| 1b | ATH4 p.545 (post #10888) | diyaudio.com/…/page-545 | 2026-11-25 | inaccessible (Cloudflare) |
| 1c | ATH4 p.525 | diyaudio.com/…/page-525 | 2026-11-25 | inaccessible (Cloudflare) |
| 1d | at-horns.eu homepage | at-horns.eu | 2026-11-25 | accessible; no ST260-BLD found |
| 1e | R-OSSE Waveguide rev7.pdf | at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf | 2026-11-25 | accessible [published] |
| 1f | ATH 4.8.2 User Guide | at-horns.eu/release/Ath-4.8.2-UserGuide.pdf | 2026-11-25 | accessible [published] |
| 2a | ATH4 p.332 (M2-slot) | diyaudio.com/…/page-332 | 2026-11-25 | inaccessible (Cloudflare) |
| 2b | ATH4 p.326 | diyaudio.com/…/page-326 | 2026-11-25 | inaccessible (Cloudflare) |
| 3  | ATH4 p.701 (Tritonia-X) | diyaudio.com/…/page-701 | 2026-11-25 | inaccessible (Cloudflare) |
| 4  | Beyond the Ariel p.775 | diyaudio.com/…/page-775 | 2026-11-25 | inaccessible (Cloudflare) |
| 5a | AudioHorn X-Shape | audiohorn.net/x-shape-horn/ | 2026-11-25 | accessible [published] |
| 5b | AudioHorn MX-Shape | audiohorn.net/horn/mx-shape/ | 2026-11-25 | accessible [published] |
| 6a | US9924249B2 | patents.google.com/patent/US9924249B2 | 2026-11-25 | accessible [published] |
| 6b | US9386361B2 | patents.google.com/patent/US9386361B2 | 2026-11-25 | accessible [published] |
| 6c | US11012773B2 | patents.google.com/patent/US11012773B2 | 2026-11-25 | accessible [published] |
| 7  | at-horns.eu Tritonia page | at-horns.eu/tritonia.html | 2026-11-25 | accessible [published] |
