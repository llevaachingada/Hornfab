# Salmon / X-horn expansion - research dossier (2026-10-25)

**Lane:** salmon/X expansion (read-only recon of the repo + one dossier write).
**Protocol:** embedded `hornlab-typology-research` rules (source hierarchy, source-table
status vocabulary, R9 rename gate, no silent fixes). The repo inventory was already done;
the verdicts in section 0 are trusted and are not re-researched.

**Scope.** (A) The Salmon lineage OUTSIDE the repo: who published what, and what is
actually documented versus what the repo reconstructed. (B) The "X horn" referent outside
the repo. (C) Expansion candidates that fit the existing search layer, each as a concrete
searchable-knob concept with ranges, R9 status, and an implementation shape.

**Labels.** [verified] = read at the source or in the repo this session. [inferred] = our
derivation, with the derivation shown. [measured] = a number computed this session from repo
code or from published numbers (the call or arithmetic is named). [unverified] = asserted by
a source that could not be machine-read this session. Units are mm, Hz, deg. This file is
ASCII by contract: "phi" for the azimuth, "deg" for degrees, "->" for arrows.

**Bottom line.**

1. The Salmon family is verified: **Vincent Salmon, JASA 17(3), 1946, two companion
   papers**. The T parameter is his. Harry Olson's 1947 textbook is the codifier, not the
   originator; his 1940 first edition has no hyperbolic-horn section and never mentions
   Salmon. This corrects the common "Olson hyperbolic horn" shorthand.
2. **"X-Shape" has a commercial referent: AudioHorn (France)**. It publishes dimensions,
   prices and polar images, but no geometry and no formula. Its own definition of the X is
   the *diagonal* transition ("Cross Wavefront Syndrome"), not a cross-shaped mouth. The
   repo's `salmon_x_shape` remains **ours [inferred]** and must not be presented as a
   reproduction of that product.
3. The existing rows contract already expresses more "X" than the shipped configs show.
   The `g_stop_cos2k` list is a **signed** diagonal term, so both readings of an X are
   reachable today: diagonal-out (X / corner-out) and diagonal-in (cardinal-lobe / plus).
   Measured below. The one-sided `g_x_amp` knob is the only thing hiding it.
4. The cheapest real family expansion is the **unused upper half of the T axis (T > 1)**
   plus a length-derived `hypex_angle`. The expensive gaps are cross-section control on the
   rows route (lobes, true superellipse corners) and any full-360 asymmetry.

---

## 0. Cite-and-skip inventory (repo verdicts)

Repo state is cited to the file and line read this session. The broad discovery lane's
dossier (`SHAPE_DISCOVERY_SWEEP_2026-10-25.md`) owns ATH/Tritonia/twist/serration/QT/lens/
biradial-slot; this lane cites it and does not redo it.

| Area | Repo state (file:line) | Verdict for this lane |
|---|---|---|
| Plane-wave Salmon (`hypex`) | `profiles.py:119-157`; `registry.py:140-141`; `examples/typologies/hypex.yaml` | COVERED. Fixed size (`L_mm`, `rm_mm`), T in [0,1], no angle-terminated variant. This lane adds the lineage and the T>1 / angle notes only. |
| Spherical-wavefront Salmon | `profiles.py:687-885`; `registry.py:166-175`; `examples/typologies/spherical_salmon.yaml` | COVERED (axisymmetric, FREEFORM stop < 90). The core refuses exactly 180 deg (cap-area asymptote). |
| Salmon rows | `grid.py:129-130`, `1506-1709`, `1930-1995`; `salmon_elliptical.yaml` | COVERED: per-azimuth `fc` law, rollback, quarter/half, torus lip, harmonic stop, x_shape, saddle. `salmon_axisym` is a kind with no shipped config. |
| C2 symmetry basis and span rules | `grid.py:116-128`, `1308-1360`; `WP9_WP9B_GROUNDING` 2.4; `JMLC_FAMILY_VARIANTS` 2.5 | BINDING. `cos(2k phi)` quarter-safe; `sin((2k+1) phi)` and the axial bend half-only; an odd cosine is refused. |
| x_shape / plan T5 | `grid.py:1046-1074`; `salmon_x_shape.yaml`; `WP9_WP9B_GROUNDING` 2.4 | COVERED as a labeled hypothesis. `x_amp` is one-sided [0, 0.4]; `x_fc` is gated on `x_amp > 0`. |
| Saddle / T5b | `salmon_saddle.yaml`; `JMLC_FAMILY_VARIANTS` 2.5 | COVERED (explicit half span, fixed a2 + b1). |
| Le Cleac'h exact + JMLC variants | `JMLC_LECLEACH_RESEARCH`; `JMLC_FAMILY_VARIANTS`; `lecleach_*.yaml` | CITE-AND-SKIP. |
| Biradial / Iwata 300 | `BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md` (parallel lane, untracked) | CITE-AND-SKIP. One stale line is flagged in C-4. |
| Broad shape sweep | `SHAPE_DISCOVERY_SWEEP_2026-10-25.md` | CITE-AND-SKIP. Overlaps are named in section 3. |
| Non-rows GRID shape field (G8/G9/pnorm) | `grid.py:398-543`; `examples/typologies/grid_ellipse_mod.yaml` | COVERED, but it cannot be combined with rollback salmon rows (measured in 3.4). |
| P-M4-2 infeasible stops near 180 | `docs/ISSUES.md:97` (pointer drift from :91) | OPEN. Sharpened in C-5: the [120,240] "window" constant is unused. |

### What salmon / x can express today (verified unless marked)

CAN:

- Axisymmetric plane-wave Salmon: `hypex`, T in [0,1], T=0 catenoidal, T=1 exponential,
  fixed mouth radius and length. [verified, `profiles.py:119-157`]
- Axisymmetric spherical Salmon: `spherical_salmon` with `fc_hz`, `T >= 0` (no upper bound
  in the code), stop < 90 on FREEFORM; `salmon_axisym` rows with rollback stop up to 360
  (refusing exactly 180). [verified, `profiles.py:725-736`, `grid.py:712-716`]
- Elliptical / H-V Salmon: `salmon_elliptical` rows with
  `1/fc(phi) = cos^2(phi)/fc_h + sin^2(phi)/fc_v`, one march per azimuth, quarter or half
  span. [verified, `grid.py:1686-1695`]
- Stop harmonics: `a2 cos 2phi`, `a4 cos 4phi` (quarter-safe), `b1 sin phi`, `b3 sin 3phi`
  (half only), plus an axial bend `bend sin(phi)` applied with a smoothstep window; at most
  2 terms per list. [verified, `grid.py:1308-1360`, `1196-1213`]
- The X modulation: `stop(phi) = stop0 (1 + x_amp cos 4(phi - 45 deg))`, `x_amp` in
  [0, 0.4], `fc` scaled by `1 - x_fc cos 4(phi - 45 deg)` when `x_amp > 0`. [verified,
  `grid.py:1046-1074`]
- A torus lip on every salmon row (`g_r_lip_mm`, 0-100 mm). Not used by the shipped salmon
  configs. [verified, `grid.py:685-688`, `727-736`]
- A saddle (top != bottom) through `b1` on a half span; an X through `a4` on a quarter span.
  [verified]
- Splice a salmon meridian with another parent (axisymmetric, no rollback): measured
  feasible in 3.5. [measured]

CANNOT (without new code):

- Any `fc` modulation beyond the 2-parameter `cos^2/sin^2` law. There is no `c2/c4` term for
  `fc`. [verified, `grid.py:958-971`, `1686-1692`]
- Any `T` variation with azimuth: one T per configuration. [verified, `_rows_shape_knobs`]
- Any cross-section shape independent of the march: no superellipse exponent, no G8 radius
  lobe, no mouth serration on the rows route. The rows spec refuses foreign keys, and
  `_radius_field` is not used by rows. [verified, `grid.py:645-670`, `1659-1709`]
- A signed `g_x_amp`: the knob is [0, 0.4]. The equivalent negative `a4` IS reachable through
  `g_stop_cos2k` (measured in 3.1), but typing a negative `g_x_amp` is refused. [verified,
  `grid.py:717-722`, `1064-1067`]
- Diagonal-pair asymmetry (45/225 vs 135/315 deg) or an arbitrary X rotation: both break the
  C2 mirror basis; the rows route builds quarter/half models only and refuses a full
  circle. [verified, `grid.py:116-128`, `479-484`]
- Single-sided / odd-cosine asymmetry (left-right break): refused by design. [verified; the
  broad sweep's S3/A2 is the route to relax it]
- A stop exactly at 180 deg. [verified, `profiles.py:733-736`]
- A search window that keeps stops away from 180: the shipped configs bound
  [120, 240] but the code accepts any stop in (0, 360) except exactly 180; the constant
  `ROWS_SALMON_MOD_STOP_RANGE = (120, 240)` is defined and never used. [verified,
  `grid.py:162`, grep]

---

## 1. Salmon lineage: what is actually documented

### 1.1 Source table

| Source | What it gives us | Status |
|---|---|---|
| **V. Salmon, "A New Family of Horns", J. Acoust. Soc. Am. 17(3), 212-218 (1946)**, DOI 10.1121/1.1916317. Crossref record: author Vincent Salmon, Jensen Radio Manufacturing Company, Chicago. | The two-parameter family, with the exponential as the central member. Abstract (OpenAlex reconstruction): "A new family of horns is synthesized in which the exponential forms a central member. This permits the effect of perturbations from the exponential contour to be estimated. From other members of the new family unique impedance characteristics are obtained..." This is the paper Olson footnotes for the T family. | **primary (author)** [bibliographic record and abstract verified via Crossref/OpenAlex; full text closed access] |
| **V. Salmon, "Generalized Plane Wave Horn Theory", JASA 17(3), 199-211 (1946)**, DOI 10.1121/1.1916316. | The companion theory paper: the plane-wave (Webster) family and its perturbation treatment. This is the paper that makes "Salmon family" a theory, not just a profile list. | **primary (author)** [bibliographic record verified] |
| **V. Salmon, "A New Family of Horns", JASA 14, 128 (1942)**, DOI 10.1121/1.1902323. | The first located public statement of the family, four years before the full paper (a one-page abstract record; the "meeting abstract" reading is [inferred] from the page range). | **primary (author)** [bibliographic record verified] |
| **V. Salmon, "Generalized Plane Wave Horn Theory", JASA 12, 473 (1941)**, DOI 10.1121/1.1902224. | Earlier abstract of the theory paper (Jensen Radio Manufacturing Co.). | **primary (author)** [bibliographic record verified] |
| **V. Salmon, "Some Measurements on a Hyperbolic Horn", JASA 10, 256 (1939)**, DOI 10.1121/1.1902097. Affiliation MIT. | Shows the hyperbolic horn was measured before the 1946 family paper; the family did not appear from nowhere. | **primary (author)** [bibliographic record verified; abstract-level] |
| **J. E. Freehafer, "The Acoustical Impedance of an Infinite Hyperbolic Horn", JASA (1940)**, DOI 10.1121/1.1916061. MIT. | The exact infinite hyperbolic-horn impedance, including the statement that the hyperboloid-of-one-sheet form admits an exact solution without the plane-wave assumption. This is the mathematical backing of the hyperbolic member, independent of Salmon. | **secondary, peer-reviewed** [abstract verified via OpenAlex] |
| **H. F. Olson, *Elements of Acoustical Engineering*, 1st ed., D. Van Nostrand, 1940.** | Negative evidence: the full OCR text (archive.org `Olson_-_Elements_of_Acoustical_Engineering_1940`) contains **zero** occurrences of "Salmon" and **zero** of "hyperbolic"; its horn chapter covers parabolic, conical and exponential only. | **secondary, used only as a cross-check** [verified by full-text grep this session] |
| **H. F. Olson, *Elements of Acoustical Engineering*, 2nd ed., D. Van Nostrand, 1947, section 6.19 "Infinite Hyperbolic Horn", pp. 99-100.** | The codifying textbook statement: `S = S0 (cosh a + T sinh a)^2`, "where T = family parameter, in the hyperbolic horn T < 1", `a = x/x0` dimensionless axial distance; the worked example uses T = .5. Footnote: "Salmon, V., Jour. Acous. Soc. Amer., Vol. 17, No. 3, p. 212, 1946." | **secondary, used only as a cross-check** [verified by full-text read this session] |
| **L. L. Beranek and A. R. Mellow, *Acoustics: Sound Fields and Transducers*, ch. 9 "Horn loudspeakers" (2012)**, DOI 10.1016/B978-0-12-391421-7.00009-9. | A modern textbook chapter that cites Salmon 1946b (per the OpenAlex citation index). Confirms the family is standard textbook material, not a fringe claim. | **secondary, used only as a cross-check** [citation link verified; chapter not read] |
| **J.-M. Le Cleac'h, ETF 2010 lecture, p. 37 (in-repo fetch)** | The isophase surfaces are parallel and perpendicular to the horn wall; the wavefront-type table (planar, cylindrical, spherical cap, toroidal) that makes the "Salmon law on spherical caps" construction possible. | **primary (author)** [fetched in an earlier session; quoted in `JMLC_LECLEACH_RESEARCH` 1] |
| **Y. Fourcade, *Calcul du Pavillon Le Cleac'h* (2015)** | The exact axisymmetric iterative construction that applies the Salmon area law to spherical caps; reference case in `JMLC_LECLEACH_RESEARCH` 2.3. | **primary (author)** [verified in the earlier lane; R9-J passed] |
| **B. Kolbrek, "Horn Theory: An Introduction, Part 2", audioXpress (2008)** | The principle (equidistant wavefronts normal to the wall + the Salmon law). | **secondary** [not fetched today: the current audioXpress URL returns 404; in-repo quote only, `[unverified-today]`] |
| **AudioHorn, "Next-Gen Bi-radial Horn" product page** (https://audiohorn.net/next-gen-bi-radial-horn/) | A current commercial horn that states it "follows the Hypex formula surface law" (hyperbolic expansion). Evidence that the family is still in commercial use, not only in textbooks. | **marketing** [verified page text 2026-10-25] |

### 1.2 Lineage verdict (who published what)

- **The family is Salmon's.** The canonical pair is JASA 17(3), 1946: the theory paper
  (pp. 199-211) and the family paper (pp. 212-218). The 1942 abstract is the first located
  public statement; the 1939 measurements and the 1938 field/impedance work (OpenAlex
  records "The sound field and radiation impedance of a hyperbolic horn", no DOI) are the
  precursors. [verified bibliographic records]
- **Freehafer (1940) supplied the exact hyperbolic-horn impedance**, not the family. He is
  a separate MIT line, not a co-author. [verified abstract]
- **Olson did not originate it.** The 1940 first edition has no hyperbolic horn and no
  Salmon; the 1947 second edition adds section 6.19 with the T family and a footnote to
  Salmon 1946. Olson is the **codifier and popularizer**, and the reason "hyperbolic horn"
  and "T" became standard vocabulary. [verified full-text comparison]
- **Le Cleac'h applied the Salmon area law to spherical wavefronts**; Fourcade (2015) made
  that application exact. Salmon's own 1946 papers are plane-wave (Webster) theory; the
  spherical-cap application is the later French line. This distinction matters for the
  attribution wording (C-2). [verified]
- **"Hypex" is not a Salmon or Olson word.** It appears **zero** times in both Olson
  editions (full-text grep). It is a modern modeling-tool contraction of
  "hyperbolic-exponential". The repo's use is fine as an internal kind name, but it is not a
  published typology name and should not be attributed to Salmon. [verified negative]

### 1.3 Conventions and the 180 deg asymptote (important for expansion)

- Olson writes `S = S0 (cosh a + T sinh a)^2` with `a = x/x0`. The repo's
  `spherical_salmon` writes `A(s) = A0 (cosh(s/x0) + T sinh(s/x0))^2` with
  `x0 = c/(2 pi fc)` (`profiles.py:740-745`), which is the same form. The in-repo raw
  appendix A has an `m/2` variant (`S = S0 (cosh(m z/2) + T sinh(m z/2))^2`); that is a
  different convention for `m`, not a contradiction. Use the `x0` form when comparing to
  Olson. [verified]
- **The 180 deg asymptote is a property of the spherical-cap mapping, not of Salmon's area
  law.** The plane-wave `A(s)` is finite and monotone for every `s`. The refusal comes from
  `A_cap = 2 pi (r/sin theta)^2 (1 - cos theta)`, which diverges as `theta -> 180` at fixed
  `r` (`profiles.py:747-748`, `733-736`). Consequently:
  - a *cylindrical* or *toroidal* wavefront application would not have the same asymptote
    (an arc length stays finite at 180 deg), which is one reason the cylindrical-Salmon
    idea (3.6) is interesting;
  - the search axis that matters is the *diagonal stop* in a modulated row, not only the
    base stop. See 3.1 for the measured discontinuity. [inferred from the formula, verified
    in code]

---

## 2. X-horn precedent: what exists outside the repo

### 2.1 The commercial referent: AudioHorn "X-Shape" (France)

Everything in this section is from pages read 2026-10-25 [verified as page text]. Product
performance claims are **marketing** unless a line says otherwise; only the dimensions and
the existence of the products are treated as facts.

The only commercial audio use of the exact string "X-Shape" found this session is AudioHorn
(https://audiohorn.net/x-shape-horn/). It is a family, not a single horn:

| Model | Throat | W x H x D (mm) | W/H | D/W | Recommended crossover (Hz) |
|---|---|---|---|---|---|
| X-Shape 21 | 1 in | 210 x 130 x 120 | 1.62 | 0.57 | 1200 / 1400 |
| X-Shape 25 | 1 in | 250 x 156 x 142 | 1.60 | 0.57 | 1200 / 1250 |
| X-Shape 28 | 1 in | 280 x 175 x 153 | 1.60 | 0.55 | 1200 / 1250 |
| X-Shape 33 | 1 in | 330 x 200 x 196 | 1.65 | 0.59 | 1000 / 1150 |
| X-Shape 34 | 1.4 / 1.5 in | 339 x 211 x 207 | 1.61 | 0.61 | 700 / 800 |
| X-Shape 40 | 1.4 / 1.5 in | 408 x 248 x 230 | 1.65 | 0.56 | 650 / 750 |

Dimensions and crossovers are **[marketing]** (manufacturer product page, read 2026-10-25);
the ratios are [measured] arithmetic on those numbers. Related products on the same site:
RX-Shape (free-standing), MX-Shape (modular), X-AMT (a different, AMT-specific product),
OS-FEA, Next-Gen Bi-radial. The existence of RX/MX/X-AMT means "X" is used as a brand
prefix, not a single geometry [inferred from the product line].

**What AudioHorn says the X is** (https://audiohorn.net/sciences/cross-wavefront-syndrome/,
read 2026-10-25): a round waveguide that transitions too quickly to a square/rectangular
mouth makes the wavefront "form a cross shape" at the diagonals ("cross syndrome"). Their
fix is an FEA-designed *diagonal profile* so the wavefront stays round/elliptical; the claim
is that "the diagonal measurement of the X-shape is as perfect as the horizontal one." The
X-Shape page also recommends a full roundover and states the profile "ends at 180 deg."
[verified page text; **marketing** claims, no measurements supplied as numbers]

**What is NOT published:** any equation, profile table, point cloud, or patent for the
X-Shape. The product page gives dimensions, prices, polar *images* and SPL *images*, not a
construction. A Google Patents query was unavailable (HTTP 503); no patent was found in the
reachable indexes. This is an **absence of evidence**, not proof that no patent exists
[unverified absence]. The repo's earlier verdict ("audiohorn.net publishes no geometry; the
modulation is OUR hypothesis") stands.

### 2.2 Other X / cross / lobe precedents

- **No published audio horn with a cross-shaped (X) mouth outline was found.** The broad
  sweep also found no measured audio study for mouth serration/lobes
  (`SHAPE_DISCOVERY_SWEEP` 2.3 R2, 3.7 S7). This is the honest absence.
- **The closest published cross-section precedent is in radio astronomy, not audio:** the
  quad-ridge flared horn (four ridges, a cross-like section; e.g. Flygare and Pantaleev,
  "Dielectrically Loaded Quad-Ridge Flared Horn...", IEEE Trans. Antennas Propag. 2020, DOI
  10.1109/TAP.2019.2940529). It is a *feed* with four ridges, not an X-shaped mouth, and it
  is not evidence for an acoustic benefit. Cite it only as an adjacent cross-section
  precedent. [secondary, peer-reviewed; bibliographic record verified]
- **Corrugated / scalar feed horns** are the other cross-section-control lineage (ring
  slots). The sweep already covers them as a labeled experiment; no audio primary was
  found (R3). Do not duplicate.
- **The repo's own x_shape** is the third "X": a low-order diagonal modulation that, at the
  shipped seed, puts the *terminal rim* radius on the diagonals at 221.9 mm versus 111.9 mm
  (H) and 81.6 mm (V) [measured]. That is a four-lobed X rim. A true rounded rectangle is
  not a single cosine; it needs a superellipse/higher-order shape (3.4). [inferred]

### 2.3 Verdict

- "X Horns" most likely means the AudioHorn X-Shape family: a rectangular-mouth horn with a
  smoothed **diagonal flare**, whose geometry is unpublished. The name is a **rename-gate**
  referent, not a construction source.
- The repo's `salmon_x_shape` is **ours [inferred]**, and it is a *different* diagonal
  treatment (a low-order stop modulation that produces a lobed/X rim). It should keep its
  neutral name and its hypothesis label. If the owner wants the commercial association
  documented, cite AudioHorn as a **marketing referent** in the config header, never as the
  construction.
- A cross-shaped *cross-section* (quad-ridge analogue) has no audio precedent found; if
  pursued, it is a new labeled device, not an "X horn" reproduction.

---

## 3. Expansion candidates

Cost convention (same as the broad sweep): **XS** = config only or < 25 LOC; **S** = < 100
LOC + tests; **M** = 100-300 LOC + tests. LOC are estimates, not commitments.

The candidates are grouped by the three independent "directions" of the salmon/X knob space:
**depth** (where the row stops), **shape** (the cross-section radius at a station), and
**loading** (the local flare rate / cutoff). The current shipped surface has good depth
control and almost no shape or loading control.

### 3.1 X-shape v2 - signed, decoupled, and already half-implemented

**Tags:** asymmetric (quarter-safe), multi-direction-gradient, X.

**What it is.** Generalize the existing T5 law to

```
stop(phi) = stop0 * (1 + x_amp * cos 4(phi - 45 deg))
fc(phi)   = [1 / (cos^2(phi)/fc_h + sin^2(phi)/fc_v)] * (1 - x_fc * cos 4(phi - 45 deg))
```

with `x_amp` and `x_fc` **signed and independent** (today `x_fc` is applied only when
`x_amp > 0`, `grid.py:1071`).

**The key measured fact.** The list contract already contains the same term. Since
`cos 4(phi - 45 deg) = -cos 4phi`, the x_shape law is exactly the list harmonic with
`a4 = -x_amp`, **provided `g_x_amp` is left at 0** (the two factors compose
multiplicatively when both are set). Therefore:

- `g_x_amp: 0` with `g_stop_cos2k: [0.0, -0.25]` reproduces `g_x_amp: +0.25` (to numerical
  noise);
- `g_x_amp: 0` with `g_stop_cos2k: [0.0, +0.25]` is the **opposite sign**, reachable today
  with no code.

Measured at the `salmon_x_shape.yaml` seed (stop 130, fc_h 800, fc_v 1100, T 0.8, quarter
15 rows) [measured 2026-10-25, `G.rows_grid_points`]:

| Knobs | Terminal r at phi=0 / 45 / 90 (mm) | Terminal axial x at 0 / 45 / 90 (mm) | Mouth W x H (mm) | Depth (mm) |
|---|---|---|---|---|
| Current `g_x_amp 0.25` | 111.85 / **221.87** / 81.59 | 104.24 / 38.37 / 62.69 | 348.8 x 322.8 | 136.3 |
| `g_x_amp 0`, `g_stop_cos2k [0, +0.25]` | **218.37** / 111.09 / **159.00** | 36.71 / 103.14 / 11.48 | 436.7 x 318.0 | 129.8 |

So the current sign is **diagonal-out** (X / corner-out). The opposite sign is
**diagonal-in** (cardinal lobes / plus). Both keep the left-right and up-down mirrors exactly
(cos 4phi is doubly even), so both stay on the quarter model.

**Knobs and ranges (proposal).**

- `g_x_amp`: **[-0.35, +0.35]** (today [0, 0.35] in the config, ceiling 0.4 in the code).
  Sign: positive = diagonal rim out (X); negative = diagonal in (plus).
- `g_x_fc`: **[-0.30, +0.30]**, applied whenever nonzero (decouple from `x_amp`). Sign has
  the same geometric sense as `x_amp`.
- Optional `g_x_amp2` (cos 8phi) for a flatter-sided rounded rectangle; quarter-safe, but it
  is a new scalar knob (not one of the 2 list terms), so it needs its own code path.

**The 180 deg trap (measured/derived).** At stop0 = 130, the diagonal stop is
`130 (1 + x_amp)`. The critical value is `x_amp = 180/130 - 1 = 0.384615...`; the code
refuses exactly 180 (`grid.py:1679-1684`). A sweep at 0.35 / 0.3846 / 0.40 measured
W x H = 370.3 x 345.2 / 378.3 x 352.7 / 381.9 x 356.0, all accepted [measured]. Just below
and just above the critical value the diagonal row sits on opposite sides of the cap-area
singularity, so the geometry is not smooth in `x_amp` there [inferred from the formula], a
discontinuity for CMA. Keep search bounds on one side of `180/stop0 - 1`, or parameterize
the diagonal stop directly (3.2). This is P-M4-2 in a new guise.

**R9.** No published geometry; **ours [inferred]**, labeled hypothesis. AudioHorn is a
marketing referent only. Do not use "AudioHorn X-Shape" as a construction name.

**Implementation shape.** Rides the existing `salmon_elliptical` rows kind as a v2 config.
The `a4` depth direction is **config-only today** (0 LOC): a v2 YAML with
`g_stop_cos2k: [0.0, -0.35]` reproduces the strong X, and `[0.0, +0.35]` gives the plus.
For the knob UX, accept a signed `g_x_amp` and decouple `x_fc`: ~15-25 LOC in
`_rows_shape_knobs` and `x_shape_modulation`, plus 3-4 tests (sign symmetry, P2 at x_amp=0,
the 180 guard). **Cost: XS.**

**Evidence.** AudioHorn X-Shape dimensions and diagonal claim [marketing]; the measured
sign behavior above; `WP9_WP9B_GROUNDING` 2.4 and P2/P3 properties.

### 3.2 Salmon family completion - T > 1, T-gradient, and a length-derived hypex

**Tags:** classical family extension (no new shape class).

**2a. T > 1 on the plane-wave hypex.** `hypex` currently refuses T > 1
(`profiles.py:131-132`), but the family formula is valid for any T >= 0. T > 1 is the other
side of the exponential: it raises the asymptotic coefficient and steepens the early flare,
though the asymptotic rate is still e^a (the literature's "hyper-exponential" label is
loose). Olson names T < 1 "hyperbolic" and uses T = .5; he does not forbid T > 1. Label
T > 1 **[inferred]** from the formula, not as an Olson quote. Implementation: relax the
bound to [0, 2] (~5 LOC) + a test at T = 1.5. **Cost: XS.**

**2b. The spherical Salmon already has T > 1; only its config is narrow.** The generator
accepts any T >= 0. Measured at fc 800, stop 80, r0 12.7, theta0 5 [measured, `_salmon_march`]:

| T | March length (mm) | Mouth r (mm) |
|---|---|---|
| 1.0 | 120.99 | 103.37 |
| 1.4 | 107.53 | 102.36 |
| 2.0 | 90.39 | 100.18 |

So a wider T bound on `spherical_salmon.yaml` (0.3-2.0) is config-only and gives a real
short/fast family member at nearly the same mouth. **Cost: XS (config + one test).**

**2c. T-gradient Salmon (ours).** Let T vary along the march, e.g.
`T(s) = T_throat + (T_mouth - T_throat) (s/L)^q`, and keep the same area law. This blends an
exponential-like throat with a catenoidal-like mouth (or the reverse) continuously, without a
splice. It is not Salmon's constant-T family, so it is a labeled extension **[inferred]**.
Knobs: `T_throat` 0-1.5, `T_mouth` 0-1.5, `q` 0.5-3. Implementation: the area function
becomes `T(s)` in `salmon_march_core` (~30 LOC) + registry/rows knob (~15 LOC) + tests.
**Cost: S.** The closest published ideas are two-stage/multiflare horns (the sweep's biradial
and PT/QT lineages), but no published T(s) law exists; keep it an experiment.

**2d. `hypex_angle` (length-derived).** Today `hypex` is fixed-size (`L_mm`, `rm_mm`); every
other length-derived horn is parameterized by a stop angle. Add a variant that solves
`arctan(dr/dz) = tan(stop)` for the terminal z, with the mouth radius derived:
`r(z) = r0 (cosh(mz) + T sinh(mz))`, `m = 2 pi fc / c`, and brentq on z. This makes the
plane-wave Salmon comparable to tractrix/Le Cleac'h and gives the search a natural
mouth-size/depth trade. ~40-50 LOC in `profiles.py` + a registry branch + tests.
**Cost: S.** R9: the parent law is Salmon 1946 / Olson 1947; the angle parameterization is
ours [inferred] (the same move the repo already made for tractrix and Le Cleac'h).

**Whole package cost: S (~100 LOC + 2 configs).** This is the highest R9-quality expansion:
the family itself is published, and the knobs are the family parameter.

### 3.3 `fc` harmonics - the missing loading direction

**Tags:** asymmetric, multi-direction-gradient, X.

**What it is.** Keep the T3 law and add a harmonic factor:

```
1/fc(phi) = cos^2(phi)/fc_h + sin^2(phi)/fc_v
fc(phi)  *= 1 + sum_k c_2k cos(2k phi) + sum_k d_(2k+1) sin((2k+1) phi)
```

(or add the harmonic to `1/fc`, which is the physically smoother form; either is a labeled
choice). Knobs:

- `g_fc_cos2k`: `[c2, c4]`, each in [-0.30, +0.30]; quarter-safe. `c4` = diagonal loading
  (the X direction); `c2` = H/V trim.
- `g_fc_sin2k1`: `[d1, d3]`, each in [-0.30, +0.30]; **half span only** (up/down).
- Same 2-term cap as the stop list; raising it to 3 adds cos 6phi / sin 5phi, both still in
  the C2 basis.

**Why it is different from stop modulation.** `stop` changes the terminal angle, so it
changes depth and radius together. `fc` changes the local flare rate, so the same mouth
radius is reached in a different length and with a different wall-angle history. That is the
"loading" axis of an X horn and it is currently absent. [inferred; no published per-azimuth
fc law exists: `JMLC_FAMILY_VARIANTS` 2.1 and 5 say the T3 law itself is unattributed
practice]

**R9.** **Ours [inferred]**, an extension of an already-labeled reconstruction. No published
per-azimuth `fc(phi)` law; do not attribute it to JMLC/Le Cleac'h. [verified absence in the
repo's prior search; no new primary found this session]

**Implementation shape.** A new knob pair on the salmon rows route, reusing the
`rows_task_harmonics` validation pattern: validation (~25 LOC), a `rows_fc_harmonics` law
(~15 LOC), apply before the march (~5 LOC), meta (~5 LOC), tests (~30 LOC). Then a v2 config
(`salmon_fclobe.yaml`) with `fc_h`/`fc_v` plus fixed or searched `c4`. **Cost: M (~80 LOC +
config).**

**Evidence.** The small-signal geometry is measurable (per-row mouth radius and depth); the
acoustic benefit is a hypothesis (the diagonal-loading claim comes from AudioHorn
[marketing], not from a measured study). Score it with the diagonal objective in 3.9.

### 3.4 Rows-route shape modulation (G8 on rows) - corner fill, lobes, superellipse-ish

**Tags:** organic, rippled, lobed, multi-direction-gradient, X.

**What it is.** Multiply each row's radius by a mouth-localized even-cosine series:

```
r_row(s, phi) = r_row(s) * (1 + sum_k a_k * w(s) * cos(2k phi))
w(s) = smoothstep((s - s0)/(1 - s0))  or  (s)^q
```

This is the rows-route version of the existing non-rows G8 field (`grid.py:398-419`,
`490-511`). It gives, with one knob pair:

- `a2 < 0` (cos 4phi, negative at the diagonals): **corner-out / superellipse-ish** mouth
  (a rounded rectangle approximation);
- `a2 > 0`: **X-pinch / star** (diagonals pulled in);
- `a3` (cos 6phi): a **6-lobe** organic mouth; higher even k gives more lobes;
- `q` and `s0`: how localized the shape change is (mouth-only vs full wall).

Sign note: this is a **radius** multiplier, so its sense is the reverse of the **stop** term
in 3.1. There, a longer stop gives a larger terminal radius in this range (measured), so
`a4 < 0` is the X; here, a negative `a2` directly enlarges the diagonal radius, so `a2 < 0`
is the corner-out/superellipse side. Do not copy the sign between the two laws without
checking which quantity is being multiplied.

Proposed ranges: `a2` in [-0.20, +0.20], `a3` in [-0.10, +0.10], `s0` in [0.60, 0.95],
`q` in [1, 4]. Even k only (quarter-safe); odd k would need a half/full model.

**Why not config-only.** The rows route assembles points directly from the per-azimuth
marches and never calls `_radius_field`. The non-rows route *can* combine a Salmon meridian
with `pnorm`/G8, but it cuts both meridians to a common depth, which truncates the
longer-flaring plane. Measured with two Salmon meridians (fc 800 / 900, T 0.8, stop 80)
[measured]: H's natural mouth is r = 103.75 at z = 128.60; V's natural mouth is r = 92.31 at
z = 107.37; the non-rows grid cuts both at 107.37 and sees H at r = 60.80, so the
"superellipse" is built from a truncated H mouth (60.80 x 92.31), not the intended
103.75 x 92.31. The rows route exists to avoid exactly this. [measured, `G._meridians` +
`G.grid_points`]

**Exactness caveat.** A post-hoc radius multiplier changes the cross-section but no longer
follows the Salmon area law exactly (the *meridian* does; the cross-section stretch does
not). Label it as a shape experiment. If exact area-law fidelity is required, use 3.4b.

**3.4b Exact superellipse outline (inverse stop).** Instead of a post-hoc multiplier, solve
each row's `stop` so its terminal radius equals a target superellipse outline
`r_m(phi) = r_h r_v / (|r_v cos phi|^p + |r_h sin phi|^p)^(1/p)` (p in [2, 16]). Each row
remains a Salmon march; the stop is the free variable. Cost: ~150-200 LOC (a brentq per row,
feasibility guards, monotonicity checks), and it interacts with the 180 asymptote. This is
the most faithful "superellipse-cross Salmon", but it is a bigger build. **Cost: M-L.**

**R9.** G8 is an in-repo plan item, not a published construction. No published audio lobed
mouth was found; the broad sweep's S7/R2 and its R9 note already say this. **Labeled
experiment**; no product name. Overlap: the sweep's S7 estimates ~50 LOC for the *non-rows*
radius field; the rows variant is the same idea plus ~30 LOC of rows plumbing. Do not double
count it in a combined roadmap.

**Evidence.** The non-rows G8 already ships (`grid_ellipse_mod.yaml`, k up to 16, a1/a2
pinned); the shape family is real in the code. Acoustic benefit is a hypothesis. The
practitioner-facing rationale is the AudioHorn "diagonal smoothing" claim [marketing] and
the general mouth-diffraction argument in the sweep. **Cost: M (~80 LOC + config).**

### 3.5 Salmon splice hybrids (v2 config, measured feasible today)

**Tags:** multi-law hybrid, organic.

**What it is.** Use the existing C1 meridian splice (`profiles.py:463-520`,
`registry.py:154-165`) with a Salmon parent and a classical/OSSE mouth:

```
profile_h:
  type: splice
  first:  {type: spherical_salmon}   # throat side
  second: {type: tractrix}           # mouth side (or osse)
```

Knobs: `h_first_fc_hz`, `h_first_T`, `h_first_max_wall_deg`, `h_second_fc_hz` (tractrix) or
the OSSE knobs, and `h_zs_frac` in [0.2, 0.8].

**Measured feasibility** (2026-10-25, `registry.build_meridian`, r0 12.7, theta0 5,
L 190, zs 0.5, salmon fc 800 / T 0.8 / max_wall 80, tractrix fc 750): builds, length
109.05 mm, mouth r 72.74 mm, terminal wall angle 88.0 deg. **0 LOC.** [measured]

**Why it matters.** It is a genuinely new salmon-family typology with a published parent on
each side (Salmon 1946; Voigt tractrix, in-repo) and a labeled splice construction (WP9 G2).
It tests whether a Salmon throat + tractrix mouth beats either parent on loading/rollback
without a rollback grid. Limitations: axisymmetric only (`profile_v: same`), and the
FREEFORM route requires stop < 90, so no rollback; the splice requires both parents to have
strictly increasing r and z.

**R9.** Parents are published; the splice is the in-repo labeled construction; the *hybrid*
is **ours [inferred]**. No name gate beyond the parents.

**Implementation shape.** A v2 config + a catalog line + a test that the splice builds and
that the joint is C1. **Cost: XS (0 LOC + config).**

### 3.6 Cylindrical-wavefront Salmon (new march law) - a real family expansion

**Tags:** multi-direction-gradient, new family member.

**What it is.** Keep the Salmon area law but apply it to **cylindrical** wavefronts (arcs
normal to the wall) instead of spherical caps. The 2D cap "area" per unit width is an arc
length, so the march is a 2D problem; the resulting device is a line-source horn with
constant vertical behavior and a Salmon flare in the horizontal plane. Le Cleac'h's
wavefront-type table (p. 37, in-repo) lists cylindrical as a legal isophase type; no
published cylindrical-Salmon construction was found. [verified absence in the reachable
indexes; author table in-repo]

**Why it is interesting.** The 180 deg cap-area asymptote disappears (an arc length at
180 deg is finite), so the cylindrical member can terminate at 180 cleanly, which is exactly
the AudioHorn roundover target [marketing]. It is also the natural "family completion" on
the wavefront axis, parallel to the T-axis completion in 3.2.

**Cost.** A new march law: ~150-250 LOC (2D geometry, area law, stop/refusal rules, a
mapping into the rows or a new 2D generator) plus a throat adapter question (the driver
throat is circular; a line-source throat is a slot). **Cost: L.** Do not schedule it before
the owner decides whether a slot/line-source device is in scope; the sweep already defers
slot work to the multicell solver question.

### 3.7 Full-model rows (for diagonal-pair asymmetry / arbitrary X rotation)

**What it is.** The C2 basis says the invariant functions under the left-right mirror are
`cos(2k phi)` and `sin((2k+1) phi)`. A term that distinguishes the 45/225 diagonal from the
135/315 diagonal (or rotates the X by an arbitrary angle) is **not** in that basis: it
breaks the left-right mirror. Reaching it needs a full 360 model (or at least a model with
no mirror planes), which the rows route explicitly refuses (`grid.py:479-484`).

**Verdict.** Architecturally blocked, not a knob. Cost: a new `span: full` path + quadrants
handling + ~4x the dofs (the 5,000 screen cap becomes the binding constraint). **Cost: L.**
Only pursue if the owner specifically wants a one-sided/asymmetric horn; the broad sweep's
S2/S3 already own that class. Mentioned here so the boundary is explicit: do not promise
"per-quadrant fc" or "rotated X" as a small change.

### 3.8 Mouth ripple / serration on rows (defer to the broad sweep)

The broad sweep owns the mouth-ripple idea (S7/R2, ~50 LOC on the non-rows radius field).
The rows route cannot use that field; the delta for a rows variant is the same math plus the
rows plumbing (~30 LOC), i.e. it is a sub-case of 3.4. **Do not list it twice.** If the
owner wants serration specifically (sharp valleys, square wave), 3.4's `q`/`s0` window plus a
square-wave option covers it; a sharp-valley superformula is a larger change.

### 3.9 Companion: a diagonal-consistency objective term

**Tags:** objective, no geometry.

The X-Shape claim is "the diagonal is as good as the horizontal"
[marketing]. The repo scores H/V coverage, ripple and DI but has no diagonal term; the
existing `cuts_estimate` DI is explicitly wrong for lobed/diagonal-misbehaving patterns
(`metrics/di.py:61`, `01_CONTRACTS.md:485`). Add a report-only (then weighted) term that
compares the 45/135 deg cuts to the mean of the H/V cuts over the band, using the balloon
already computed. ~40-80 LOC in `metrics/` + `objective/terms.py` + tests; no new solves.
**Cost: S-M.** R9: **ours [inferred]**; the claim it tests is marketing. This is the cheapest
way to make an X-shape search *mean* something, and it guards the "lobed" failure mode the
contracts already warn about.

---

## 4. Ranked top 5 recommendations

| # | Candidate | Cost (1 line) | Why it earns the slot |
|---|---|---|---|
| 1 | **X-shape v2** (signed `x_amp`, decoupled `x_fc`, v2 configs) | **XS**: 0 LOC for the a4 depth sign today via `g_stop_cos2k`; ~20 LOC + tests for the signed/decoupled knob UX | Answers "more X horns" immediately, uses the existing quarter-safe basis, and the measured sign sweep shows the two readings of an X are already in the architecture. Fixes the one-sided-knob trap. |
| 2 | **Salmon family completion** (T > 1, T-gradient, `hypex_angle`) | **S**: ~100 LOC + 2 configs (T>1 is ~5 LOC; `hypex_angle` ~50; T(s) ~45) | Highest R9 quality: the family is published (Salmon 1946, Olson 1947), the T axis is half unused, and the spherical route already accepts T = 2 (measured). No new shape class, no new failure mode. |
| 3 | **`fc` harmonics** (`g_fc_cos2k` / `g_fc_sin2k1`) | **M**: ~80 LOC + config | Supplies the missing "loading" direction of the X knob space. The repo already labels the T3 law as unattributed practice, so the extension stays honestly labeled. |
| 4 | **Rows G8 shape modulation** (corner fill, lobes, superellipse-ish) | **M**: ~80 LOC + config (rows variant of the sweep's S7; +~30 over S7) | The only way to get a real cross-section shape on a *rollback* salmon row. The non-rows route truncates the longer plane (measured), so this is not redundant with G8. Labeled experiment; exact version (3.4b) is a later M-L. |
| 5 | **Salmon -> tractrix/OSSE splice** | **XS**: config + test, 0 LOC (measured feasible) | A new named-by-construction salmon typology for free. Tests whether a Salmon throat + classical mouth beats either parent, without a rollback grid. |

**Companion (outside the top 5, recommended in the same pass):** the diagonal-consistency
objective (3.9, S-M). It is the only candidate that measures the thing the X-Shape marketing
claims, and it is independent of geometry.

---

## 5. Dated corrections and discrepancies

Corrections are dated and never applied silently. Repo edits outside this file were not
made (lane contract).

| ID | Date | Claim found | Evidence | Impact / action |
|---|---|---|---|---|
| **C-1** | 2026-10-25 | `appendix_A_typology_survey_raw.md:287` says "The hyperbolic (Salmon/Frehaufer) horn corresponds to T<0 (not commonly used in audio)." | Olson 1947 section 6.19: "T = family parameter, **in the hyperbolic horn T < 1**", with T = .5 as the worked example; T = 0 is the catenoidal special case, T = 1 the exponential. Salmon 1946b: the exponential is the **central member**. | **Documentation error**, no code impact (the code's [0,1] covers the hyperbolic member plus its exponential boundary). Also "Frehaufer" is a misspelling of **Freehafer** (J.E. Freehafer, 1940). Route to the Report 2 section 7 corrections table via the orchestrator; do not edit the raw appendix. |
| **C-2** | 2026-10-25 | Wording in several places ("Salmon 1946 applied to wavefront areas") can be read as Salmon applying the law to spherical wavefront areas. The wording appears in `WP9_WP9B_GROUNDING` 2.3 and in `02_TYPOLOGIES_AND_MULTICELL.md` section 3 ("Salmon 1946; JMLC applies it to wavefront areas" is the correct form there). | Salmon 1946a/b are plane-wave (Webster) theory; the abstract speaks of perturbations from the exponential contour. The spherical-cap application is Le Cleac'h's, made exact by Fourcade 2015. | **Wording correction** in docstrings/comments only (`profiles.py:691-693`, `:856-865` say "Salmon area law on spherical caps", which is acceptable; "Salmon 1946 applied to wavefront areas" is the misleading form). No code change. |
| **C-3** | 2026-10-25 | "Hypex" is used as if it were the published family name. | Zero occurrences of "hypex" in Olson 1940 and Olson 1947 (full-text grep). It is a modern tool contraction of "hyperbolic-exponential". | **Terminology note**, no action. Keep `hypex` as an internal kind name; do not attribute the word to Salmon or Olson. |
| **C-4** | 2026-10-25 | `BIRADIAL_IWATA_300_RESEARCH` 1.3 / C2 says "there is no `salmon_x_shape` or `salmon_saddle` kind" and "their catalog entries were removed (M4_SMOKE:198)". | `ROWS_TYPES` indeed has no such *kinds*, but the **configs** exist and the **catalog entries exist**: `examples/catalog.yaml:179-186` (salmon_elliptical, salmon_x_shape) and `:229-233` (salmon_saddle). `M4_SMOKE_2026-10-25.md:198` refers to `lecleach_saddle` / `lecleach_ar_wide` being consolidated, not the salmon configs. | **Cross-lane documentation discrepancy** (not a fetch correction). The biradial conclusion is unaffected; its C2 sentence should be corrected by its own lane or the orchestrator. Do not edit that file from this lane. |
| **C-5** | 2026-10-25 | P-M4-2 (ISSUES:97) says the rows stop bounds [120, 240] include infeasible stops near 180. | The code accepts any stop in (0, 360) except exactly 180 (`grid.py:712-716`, `1679-1684`); the constant `ROWS_SALMON_MOD_STOP_RANGE = (120.0, 240.0)` is defined at `grid.py:162` and **never referenced** (grep). So the "window" is a comment, not a guard. The x_amp axis is cut at `180/stop0 - 1` (0.3846 at the seed; measured). | **Sharpens P-M4-2.** Options: use the constant as a hard guard, reject a band around 180 (e.g. +/-2 deg), or parameterize the diagonal stop directly. Owner gate; do not widen/narrow bounds silently. |
| **C-6** | 2026-10-25 | `salmon_x_shape.yaml` seed note says "D ~ 140 mm, W/H 355/329 mm". | Measured at the current code: W 348.8, H 322.8, D 136.3 mm [measured]. | **Stale seed comment** (~2%), no behavior impact (the YAML is the source of truth). Update the comment in a later docs pass; not this lane. |

Also, a pointer drift not worth a correction row: the work order cites `ISSUES.md:91`; P-M4-2
is currently at `docs/ISSUES.md:97` (the file was edited above it). [verified]

---

## 6. Open items for the owner

1. **Which "X" do you mean?** Three readings, three different targets:
   (a) AudioHorn's X-Shape (rectangular mouth, smoothed diagonal, unpublished) - a
   marketing referent; (b) a literal X/star rim (the repo's current measured behavior);
   (c) a cross-shaped *cross-section* (quad-ridge analogue, no audio precedent found). The
   knob signs in 3.1 cover (a) and (b); (c) is a different device.
2. **P-M4-2 decision.** Do we (i) enforce the existing [120,240] window, (ii) add a guard
   band around 180, or (iii) replace `stop_deg` with a "distance from the asymptote"
   parameterization? The x_amp discontinuity at `180/stop0 - 1` makes this urgent before any
   X-shape campaign.
3. **Full-360 rows.** Diagonal-pair asymmetry, arbitrary X rotation, and single-sided
   flares all need a full model. Do we want that pass (L cost, 4x dofs), or do we stay in
   the quarter/half architecture and accept the C2 limits?
4. **Exact superellipse vs post-hoc shape.** Is area-law fidelity a ship bar for the
   organic/X family? If yes, 3.4b (inverse stop, M-L) is the honest route; if not, 3.4
   (post-hoc multiplier, M) is enough and should be labeled as such.
5. **Naming.** Keep `salmon_x_shape` neutral (recommended), or document AudioHorn as a
   marketing referent in the config header? Do not ship "AudioHorn X-Shape" as a typology.
6. **Diagonal objective.** Is the diagonal-consistency term (3.9) a priority? Without it,
   the X-shape search optimizes H/V and cannot see the claim it is supposed to deliver.
7. **Housekeeping for the orchestrator:** add the INDEX line for this file; reconcile the
   Report 2 section 7 corrections with C-1/C-2; reconcile the biradial lane's C2 (C-4).
8. **Broad-sweep overlap:** 3.4 and 3.8 overlap `SHAPE_DISCOVERY_SWEEP` S7/R2. If that lane
   lands the non-rows serration first, 3.4 becomes a rows-route extension (+~30 LOC), not a
   separate candidate.

---

## 7. References (URLs and DOIs read or verified this session)

Repo files read (all [verified]):

- `hornlab_search/design/generators/profiles.py` (hypex 119-157; spherical_salmon 681-885;
  splice 463-520).
- `hornlab_search/design/generators/grid.py` (rows contract 82-218; C2 116-128; shape knobs
  678-724; fc law 958-971; x_shape 1046-1074; harmonics 1308-1382; marches 1506-1709;
  assembly 1167-1226; meta 1930-1995; non-rows field 398-543; validation 2111-2156).
- `hornlab_search/design/generators/registry.py` (TYPES 53-54; MOUTHS 56; splice 154-165;
  spherical_salmon 166-175).
- `hornlab_search/design/generated.py` (GeneratedSpace, generator knobs).
- `examples/typologies/salmon_elliptical.yaml`, `salmon_saddle.yaml`, `salmon_x_shape.yaml`,
  `spherical_salmon.yaml`, `hypex.yaml`, `lecleach_iwata_ar.yaml`, `grid_ellipse_mod.yaml`,
  `splice_osse_tractrix.yaml`.
- `examples/catalog.yaml:179-186, 229-233`.
- `tests/test_design_generators_salmon.py`; `tests/test_design_generators_grid_rows.py`.
- `docs/ISSUES.md:97` (P-M4-2); `docs/evidence/M4_SMOKE_2026-10-25.md:198`.
- In-repo dossiers cited, not restated: `WP9_WP9B_GROUNDING_2026-10-25.md`,
  `JMLC_LECLEACH_RESEARCH_2026-10-25.md`, `JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md`,
  `SHAPE_DISCOVERY_SWEEP_2026-10-25.md`, `BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md`
  (untracked parallel lane), `MESHER_TYPOLOGIES.md`.

External:

- Crossref, "A New Family of Horns", DOI 10.1121/1.1916317 (JASA 17(3):212-218, 1946),
  https://api.crossref.org/works/doi:10.1121/1.1916317
- Crossref, "Generalized Plane Wave Horn Theory", DOI 10.1121/1.1916316 (JASA 17(3):199-211,
  1946).
- Crossref, "A New Family of Horns" abstract, DOI 10.1121/1.1902323 (JASA 14:128, 1942).
- Crossref, "Generalized Plane Wave Horn Theory" abstract, DOI 10.1121/1.1902224 (JASA
  12:473, 1941).
- Crossref, "Some Measurements on a Hyperbolic Horn", DOI 10.1121/1.1902097 (JASA 10:256,
  1939).
- OpenAlex, "The Acoustical Impedance of an Infinite Hyperbolic Horn", DOI
  10.1121/1.1916061 (JASA, 1940), https://api.openalex.org/works/doi:10.1121/1.1916061
- OpenAlex record for Salmon 1946b (citation count and citing works):
  https://api.openalex.org/works/doi:10.1121/1.1916317
- H. F. Olson, *Elements of Acoustical Engineering*, 1st ed. (1940), full text:
  https://archive.org/download/Olson_-_Elements_of_Acoustical_Engineering_1940/Olson_-_Elements_of_Acoustical_Engineering_1940_djvu.txt
- H. F. Olson, *Elements of Acoustical Engineering*, 2nd ed. (1947), section 6.19, full
  text: https://archive.org/download/in.ernet.dli.2015.239408/2015.239408.Elements-Of_djvu.txt
- AudioHorn X-Shape: https://audiohorn.net/x-shape-horn/
- AudioHorn, "Cross wavefront syndrome: Diagonal matter":
  https://audiohorn.net/sciences/cross-wavefront-syndrome/
- AudioHorn Next-Gen Bi-radial (states "Hypex formula surface law"):
  https://audiohorn.net/next-gen-bi-radial-horn/
- Flygare and Pantaleev, "Dielectrically Loaded Quad-Ridge Flared Horn...", IEEE TAP 2020,
  DOI 10.1109/TAP.2019.2940529.
- Beranek and Mellow, *Acoustics: Sound Fields and Transducers*, ch. 9 (2012), DOI
  10.1016/B978-0-12-391421-7.00009-9 (citation link verified only; chapter not read).

Not reachable today (recorded for honesty): audioXpress "Horn Theory: An Introduction, Part
2" (404); Google Patents (503); general web search (DuckDuckGo CAPTCHA, Bing degraded,
Mojeek 403, Marginalia rate-limited). The broad sweep records the same limitation. No claim
above depends on an unreachable page; the Kolbrek row is marked [unverified-today].
