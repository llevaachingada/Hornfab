# Typology correctness review (cloud Fable senior, 2026-11-19)

Scope: every horn typology / family / generator the code can build (45 entries inventoried), checked
for (1) a published source for what it claims to be, (2) a numeric test against that source, (3)
honest labelling where it is our construction, (4) acoustic-practice misuse across typologies
(CLAUDE.md: Keele sizing is not a universal limit; no CD scoring on non-CD horns). CPU, read-only
except the fixes listed in §4. Inventory method: repo sweep of `hornlab_search/design/**`,
`docs/knowledge/**`, `docs/research/typologies/**`, `examples/**`, `tests/**`; spot-verified here.

## 1. Verdict in one table

| Grade | Meaning | Typologies |
|---|---|---|
| **A: published + numeric test** | Reproduces a published number in a test | Le Cléac'h / JMLC march (Fourcade fig. 7: width 467.30 mm exact, length 321.79 vs 321.35 mm, 2φ1 8.552 vs 8.55°); Keele Bi-Radial sizing (US4308932A); ATH CORE a/n/s table; Tritonia law; ATH twin-ray published mouth; toroidal JMLC350 vs datasheet 595 mm; **R-OSSE** (mesher formula refit to the ST260 device STL at 0.08 mm RMS, anchor README) |
| **B: textbook, analytic tests only** | Classical law, identities tested, no external numeric | conical, exponential, Salmon hypex (T family), tractrix, spherical_wave (JMLC T=1), OS-SE/OSSE (Batik PDF read; throat slope tested, no profile table) |
| **C: our construction, labelled honestly** | Reconstruction or hypothesis, says so | lecleach_ar / iwata_ar, crowe_hv_area_aspect_v1, Klangfilm-Lamé family (v1, hv_cd, hv_core), klangfilm_ellipse tool, spherical_salmon, splice, blend, throat_blend, section_pucker, rolled family, ripple knobs, plughorn, MEH, multicell, Solana/SAWMOD reconstructions, lecleach_swept_hv prototype, canonical_record_v2 container |
| **D: problem found** | Label or status wrong, or claim untested | see §2 |

**Bottom line:** no typology encodes a wrong published formula in code. Every formula correction the
research found (Keele A = 0.9B, Le Cléac'h included-vs-half angle, Salmon T sign, Keele's inconsistent
worked example) is already in code and pinned by a test. The problems are labelling, status
bookkeeping and two untested claims.

## 2. Problems found

| # | Problem | Severity | Action |
|---|---|---|---|
| D1 | Le Cléac'h **H/V pair** labelled "published ellipsoidal-wavefront construction" in code (`grid.py` `ROWS_HV_SECTION_LABEL`), test header and the `hl__lecleach_hv_landscape_smooth_v7` description; the senior review (2026-11-18) and `contracts/lecleach_iwata_hv.md` say [reconstruction]: H/V meridians are not the Fourcade marches (axial coordinate up to ~92 mm H / 69 mm V off), the article's wavefront transform is not used | R9 gate (name without reference) | **FIXED here** (label, docstrings, YAML description, test header). Metadata only: seed design hash unchanged (`7fb9d2951deb`), lecleach suites pass |
| D2 | Le Cléac'h card still listed "verify included vs half-angle" as open; WP9 dossier still says "exit half-angle 8°" | stale doc | **FIXED here** (card closed with the test reference; WP9 dossier correction note) |
| D3 | `lecleach` R9 status conflict: WP9 dossier records it BLOCKED pending an owner ruling; code calls it live; the Fourcade fig. 7 test passes | bookkeeping | **Owner:** close the R9 gate for the plain JMLC march as passed (the test is the R9 evidence). The H/V pair stays [reconstruction] |
| D4 | Klangfilm workbook "0.001 mm port match" exists only in the dossier/contract; the xlsm is not in the repo and no test pins it | untested claim | Owner box: commit 3-5 reference rows exported from the workbook as a CSV and add one test; until then call it [author-reported] |
| D5 | `spherical_salmon` does not reproduce Fourcade (width 471.31 vs 467.30 mm, 0.9%); rename gate still open | label gate | Already neutral-named; owner closes the rename gate as "neutral name, not JMLC" (no code change) |
| D6 | ICW and FREEFORM have no card; they are mesher primitives with no published-construction claim | gap, low | One-line card each: "neutral mesher primitive, no published claim; R9 not applicable" (knowledge-track owner) |
| D7 | `lecleach_mod` and `lecleach_ar` rows kinds have no config, card or dedicated dossier; `ROWS_SALMON_MOD_STOP_RANGE` is never referenced (SALMON C-5) | dead surface | Local lane: retire or document; do not queue them without a card |
| D8 | Two Keele constants (25,000 patent in `profiles.py`, 25,400 settled KEELE_K) | none | Deliberate and documented in code ("never silently interchanged"); 1.6 % apart. No action |
| D9 | `docs/knowledge/SOURCES.md` notes that `verified_on` in sources.yaml is the author's assertion; KH-001 says "source_verified" | wording | Knowledge track: say "author-verified" unless re-fetched |

Not reproduced: the inventory flagged a Crowe-X header saying `g_L_mm` widened to 320 against bounds of
285; no "320" exists in the current `hl__crowe_x_square_v*` configs, so nothing to fix (R13 keeps 285).

## 3. Acoustic-practice cross-checks (are typologies used the way real horns work?)

| Check | Result | Basis |
|---|---|---|
| Keele mouth rule imposed on non-CD horns? | **No.** In metrics it is a design check, "never constraints" (`metrics/compute.py:65`). In config it only seeds mouth knobs when the BRIEF carries `f0_hz` (a coverage-to-f0 goal), clamp-only, with an explicit opt-out | [code-verified] `config.py:1913-1935, 2075-2100` |
| CD scoring forced on non-CD typologies? | **No.** Smooth/non-CD briefs exist (`*_v7_smooth`), and constancy is a brief-declared term, never inferred from family (senior review C-2) | [code-verified + primary] |
| Keele Bi-Radial worked example | The published example is internally inconsistent (W rule fails on V; Eq. 1 turns the H wall inward, −52.6°). Code refuses the inward-turn case instead of shipping it | `test_documented_h_plane_failure_mode_is_refused_not_shipped` [verified] |
| Multicell treated as independent beams? | **No.** Card and dossier say cells interact (phase); thin-septa near-correction is landed | `docs/knowledge/typologies/multicell.md` [primary] |
| MEH validated by a single-source exterior solve? | **No.** Card says that does not validate a multiple-entry horn | `docs/knowledge/typologies/meh.md` [primary] |
| Exponential HF horns as CD devices? | Not claimed; Keele AES 1038 (exponential cannot hold CD) is cited | classical card [primary] |
| Throat H/V block per family | Labelled per family (OS-SE published; others LABELED HYBRID; R-OSSE not adopted) | `contracts/throat_hv_block.md` [primary] |

## 4. Changes made with this review

- `hornlab_search/design/generators/grid.py`: H/V pair label and two comments say "reconstruction of
  the published … principle".
- `examples/typologies/home_landscape_2026-11-15/hl__lecleach_hv_landscape_smooth_v7.yaml`: description.
- `tests/test_design_generators_lecleach_hv.py`: header comment.
- `docs/knowledge/typologies/lecleach_iwata.md`: included-angle question closed.
- `docs/research/typologies/WP9_WP9B_GROUNDING_2026-10-25.md`: half-angle correction note.

Not touched (other owners): knowledge-track cards for ICW/FREEFORM, KH-001 wording, dead rows kinds,
Klangfilm workbook fixture.

## 5. What would raise the B grades to A (cheap, CPU)

- OS-SE: one closed-form OS profile table (Geddes `r(z) = sqrt(r0² + 2 r0 z tan α0 + z² tan² α)`)
  checked against the mesher's OSSE meridian at α0 = 0 (needs the mesher: owner box).
- Tractrix / exponential / hypex: one Kolbrek or Olson worked example per law as a table test.
