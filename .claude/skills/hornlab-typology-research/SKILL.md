---
name: hornlab-typology-research
description: The knowledge-grounding protocol for horn-design work in hornlab-search — adding or tweaking a typology, generator, grid/point-grid shape law, mounting, multicell/septa geometry, a brief for a new typology, or objective/directivity terms that encode a NEW acoustic priority — requires outside research on the typology itself (primary white papers; construction math + a numerical reference case; strengths/weaknesses/design issues; optimization knobs + ranges; how practitioners rank/measure them; designer/user experiential reports) assembled into a sourced, corrected, validation-ready dossier, OR a citation of the existing senior-pass dossier when the research is already done; only then code. Use ONLY for such design-grounding work — routine config/mechanics/adapter plumbing/GPU/evidence jobs have other skills.
---

# hornlab typology research

Law: hard rule 2 (no new solvers/meshers), rule 3 (real keys/units), and the R9 gate pattern. R9 itself is
Le Cléac'h-specific (docs/TYPOLOGY_PLAN.md s2 row R9; acceptance s9 V6: match the published reference within
1 mm at the mouth or ship disabled); its general form is the rename gate (senior_pass 02 s3 + 04 WP9 step 3:
ship under a neutral name until the construction matches a published table). This skill extends that pattern
to every typology. It is the research discipline those gates imply, not new policy.

## 1. When this fires (and when NOT)

- FIRES: a plan WP that adds/tweaks typologies, generators, grid/point-grid shape laws, mounting, or briefs for a
  new typology; changing objective/directivity terms in a way that encodes a NEW acoustic priority; ANY moment a
  construction's source validity is unclear.
- FIRES (light): an owner question about what a horn type does — the §2 inventory + a sourced answer; a full
  dossier only if the answer feeds implementation.
- DOES NOT fire: routine config keys with landed semantics; GPU/job mechanics (hornlab-gpu-job); evidence
  assembly (hornlab-evidence); orchestration/handoffs; the GRID/point-grid ADAPTER mechanics (WP10 steps 1–5:
  plumbing grounded in senior_pass 02 s4 + the NOTES_FOR_SENIOR curl probe) — a NEW φ-dependent shape law still
  fires. A bounds tweak to an EXISTING typology needs no dossier: re-check the range against the dossier's (d)
  knob ranges + (c) size/band feasibility; only a range that leaves documented territory, or a knob whose
  physical meaning changes, re-opens the full protocol.

## 2. First: the repo already knows things (inventory before fetching)

- docs/research/typologies/MESHER_TYPOLOGIES.md + SEARCH_LAYER_GAPS.md; senior_pass 02 (typology catalogue +
  the s7 corrections-table pattern); senior_pass 04 (work packages — WP9b 9b.0–9b.5 is the exemplar family
  dossier); appendices A/B WITH their corrections headers; TYPOLOGY_PLAN.md; NOTES_FOR_SENIOR probe blocks
  (e.g. the point-grid curl verdict). Write down: established facts / open gaps / which claims the repo has NOT
  validated. OUTCOME: if the research already exists (WP9b for the organic family; appendix A + 02 s7 for
  breadth), the deliverable is a CITATION of it — fetch only for the gaps.

## 3. Outside research (librarian lane or webfetch directly)

- Source hierarchy (the 9b.0 model): author primaries (papers, author forum posts, published reference
  cases) > peer-reviewed secondary > calculators/tools with disclaimers > marketing (last resort, labeled).
- Assemble a per-typology DOSSIER with sections: (a) construction math (formulas + a REFERENCE CASE with
  numbers for validation); (b) strengths (designer terms: mouth reflection, control, loading); (c)
  weaknesses/design issues (foldback limits, thin-gap singularities, mouth-size vs band feasibility); (d)
  optimization knobs + typical ranges; (e) how practitioners rank/measure them (what objectives are honest);
  (f) experiential characteristics from designers/users (smoothness, honk, beaming, forgiveness of placement).
- The dossier opens with a 9b.0-style source table (| Source | What it gives us | Status |), Status from the
  9b.0 vocabulary: primary (author) / primary (author, forum) / secondary, peer-reviewed / secondary, used only
  as a cross-check / marketing. Every load-bearing claim carries the Report-1 label set ([measured]/[verified]/
  [inferred]/[unverified]) or its source URL (appendix B convention). The author's own forum posts are
  "primary (author, forum)"; other designers'/users' experience is testimony, not peer review — label it
  "secondary (practitioner reports)".

## 4. Corrections

- Never edit a raw/verbatim source (the appendices stay byte-for-byte). Corrections are dated tables in the
  CONSUMING doc (the senior_pass 02 s7 pattern), with a header note on the raw source pointing to them. New
  research contradicting a LANDED claim: a dated correction block in the dossier + the affected validation test
  updated citing the new source (rule 7 still binds: never loosen to pass).

## 5. Validation: math -> testable properties BEFORE code

- Every load-bearing physical claim becomes a checkable property (reference-table compare like the Fourcade
  tables, unit properties like the existing generator tests, mesher-fidelity vs the formula ≤ 0.2 mm).
  Construction math with no checkable property = not validated = blocked by the R9/rename-gate pattern.

## 6. Deliverable

- docs/research/typologies/<typology>_RESEARCH_<date>.md (+ docs/INDEX.md line in the same commit; CODE_MAP only
  if tooling ships): the dossier. The typology PR/commit references it; the validation tests cite its reference
  case. Minimum viable dossier: one primary source with the construction + one numerical reference case or
  cross-check + the knob ranges. 9b.0–9b.5 is the ceiling (a whole family), not the floor.

## 7. Stop conditions

- A typology ATTRIBUTED to a published construction whose primary source cannot be reached → do not ship it under
  that name; record the attempt + stop that line (R9). Our OWN hypothesis shapes may still run as labeled
  experiments (the x_shape/T5 precedent: "no published geometry; ours [inferred]"), with the attribution left
  as an open item. Two unresolved source conflicts → NOTES_FOR_SENIOR.md + stop that line (the rule-8 pattern).