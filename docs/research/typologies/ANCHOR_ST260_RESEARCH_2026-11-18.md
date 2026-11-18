# Physical anchor pick: R-OSSE "ST260" (Fable D6 step 1, cloud senior 2026-11-18)

Protocol: `hornlab-typology-research` (minimum viable dossier: one primary source with the
construction, one numerical reference case, the comparison rule). Research only. No solve.
Labels: [primary] [verified] [inferred] [unverified] [disputed].

**Network limit of this pass:** `at-horns.eu` and diyAudio could not be fetched from the cloud
container (proxy refused). Everything below that depends on those pages is either cited from the
repo's own 2026-11-16 fetch or from search-result text, and is labelled so. The local agent closes
the gaps in section 6 before any GPU time.

## 1. Choice and why

| Candidate | Published geometry? | Measured polars? | Verdict |
|---|---|---|---|
| **ATH / R-OSSE "ST260"** (1-inch, round, 260 mm) | **Yes**: full parameter set in R-OSSE rev7 "practical design example" [primary, fetched 2026-11-16 by the repo dossier]; STEP/STL + ABEC project on the ST260 page [search-result text, unverified here] | ST260 page links **user builds with acoustic measurements** on diyAudio [search-result text, unverified here]. Batik's own ST260 polar map is BEM, not measured | **Pick.** Only candidate with both halves published. Round, so H = V is a free self-check, and the mesher already has the R-OSSE family |
| Geddes OS waveguides (NS15, Summa) | **No** exact dimensions published; Geddes's chapter 6 shows generic OS examples only [search result: gedlee.com Chapter_6.pdf] | product polars exist, but for an unknown exact profile | Reject: geometry would be a reconstruction, which defeats an anchor |
| ATH CORE / Tritonia (configs published) | Yes (scripts) [repo dossier] | no measured set found in this pass | Fallback if no usable ST260 measurement exists |
| ATHEX 460-36 | ASC geometry downloadable | measured *frequency responses* only, as figures, no polars [search-result text] | Reject for D6 (no polars) |

## 2. Source table

| Source | What it gives us | Status |
|---|---|---|
| Batik, *R-OSSE Acoustic Waveguide* rev7, Dec 2022, https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf | the R-OSSE formula and the practical example R 130, r0 12.7, a0 7.5°, a 39°, k 1.8, r 0.3, b 0.3, m 0.8, q 3.7 | primary (author); values via `docs/research/ATH_PUBLISHED_SEEDS_80x60_2026-11-16.md` Design G; re-read pending |
| ST260 sample waveguide page, https://www.at-horns.eu/ST260.html | STEP, STL, ABEC project, BEM results; links to user builds with measurements | primary (author) for files; [unverified here] |
| diyAudio build threads linked from the ST260 page | measured polars of printed ST260s | secondary (practitioner reports); **not yet identified** |
| `docs/research/SIM_VS_REAL_HORN_2026-10-27.md` | why an anchor is needed; BEM predicts pattern above cutoff, not level or loading | repo research |

## 3. Construction and reference case

R-OSSE profile (rev7) as implemented by the pinned mesher's R-OSSE family; the config is
`examples/typologies/anchor_2026-11-18/anchor__rosse_st260_v1.yaml` (all bounds pinned; it loads
and validates in the cloud [verified]; it has NOT been meshed: no gmsh here).

Checkable properties before any solve (local agent, `hornlab-shape-check`):
1. mouth diameter 260 mm ± 1 mm and depth ≈ 80 mm (dossier figure) [reference case];
2. throat radius 12.7 mm, wall tangent at the throat vs the nominal a0 7.5° (the 2026-11-15
   audit flags nominal-vs-actual tangent on R-OSSE: `audit_2026-11-15/READINESS.md`);
3. if the ST260 STEP/STL is downloadable, the meshed meridian vs the STL meridian ≤ 0.5 mm RMS.
   This is the strongest check: it proves we built the horn that was measured.

## 4. Predeclared pass rule (written before any number exists)

Compared quantities, sim vs the chosen measurement, both on 1/3-octave band centres 1-8 kHz:

| Quantity | Pass | Notes |
|---|---|---|
| -6 dB beamwidth (H; V too if measured) | within **±5°** per band; within **±3°** in 2-5 kHz (presence band) | same edge definition both sides (outermost -6 dB crossing, normalised to on-axis) |
| DI | within **±1 dB** per band | same method both sides: if only H/V polars are measured, both sides use the cuts estimate; a balloon sim vs cuts measurement is not a comparison |
| Band limits | 1 kHz (gating / room) to 8 kHz | the 1-inch exit's first cross-mode f11 ≈ 1.84 c / (2π a) ≈ 7.9 kHz [inferred, a = 12.7 mm]; ideal-source BEM is not expected to hold above it |

Verdict: **pass** if every band meets the rule; **partial** if only the presence band fails or only
one band misses by ≤ 2° / 0.5 dB beyond the limit; **fail** otherwise. A fail does not change any
score; it is evidence for the owner's stage-2b scoring question (which score predicts a real
horn better).

Measurement admissibility (decided now, not after looking): use one measurement set whose
mounting we can model (free-standing, or a rectangular box with stated dimensions), with stated
distance and gating, polar step ≤ 10°. If no linked build meets this, ST260 is **not** an
anchor (stop condition, R9 pattern) and the fallback in section 1 is tried.

## 5. Cost and order

1-2 solves (screen, then verify), owner-gated (D6 step 1). A round 260 mm, 1-inch horn at epw 6
is small (the R-OSSE baseline quarter meshes are a few thousand DOF) [inferred]; shape_check gives
the real number. Order: after the owner's B1 decision; it does not depend on B1.

## 6. Open items for the local agent (in order)

1. Re-read rev7's example and the ST260 page; correct the config values if any differ (tmax,
   exponent and wall thickness are our assumptions).
2. Pick the measurement set from the ST260 page links that meets section 4's admissibility; record
   URL, driver, mounting, distance, gating, and save the polar data (or digitise the plot) under
   `docs/evidence/anchor_st260_<date>/measured/`.
3. `.venv\Scripts\python.exe tools\shape_check.py examples\typologies\anchor_2026-11-18\anchor__rosse_st260_v1.yaml`
   and the section-3 property checks. If the measured build had a box, add the matching
   `brief.mounting` block first (that is a new config version, `_v2`).
4. Only then ask the owner for the 1-2 GPU slots.
