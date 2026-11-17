---
id: KH-001
short_title: Keele Bi-Radial mouth-size relation is empirical and scoped
status: source_verified
kind: empirical_design_heuristic
updated_at: 2026-11-16
sources:
  - SRC-KEELE-US4308932A
repo_dossiers:
  - docs/research/typologies/BIRADIAL_CROWE_SOURCES_2026-11-15.md
  - docs/research/typologies/HORN_WHITEPAPERS_2026-11-15.md
applies_when:
  families: [keele_biradial]
  contexts: [patent-inspired_preliminary_sizing]
  conditions: [full_angle_B_in_degrees, A_about_0_9_B, f_hz_positive]
does_not_apply_when:
  families: [jmlc, osse, rosse, tractrix, meh]
  contexts: [universal_hard_feasibility_gate, guarantee_of_solved_beamwidth]
evidence_level: primary_patent_and_repo_correction
supersedes: []
---

# KH-001: Keele mouth sizing is not universal

Integration note (2026-11-16): metadata such as `source_verified` is inherited from
the supplied kit, not reverified here. Formula units and angle conventions remain
subject to the editor note below. Follow the [source dossier](../../research/typologies/BIRADIAL_CROWE_SOURCES_2026-11-15.md)
and [white-paper bibliography](../../research/typologies/HORN_WHITEPAPERS_2026-11-15.md).

## Source-grounded claim

The JBL/Keele patent US4308932A uses a Bi-Radial sizing example with an angle `A` about 90% of intended coverage `B` and a corresponding empirical relation `W ≈ 25,000/(A × f)` with units matching the patent context. **This is a heuristic for the described design philosophy**, not a mathematical theorem applicable to every horn typology or a guarantee of final -6 dB beamwidth. The original patent's angle convention and constant must be read before implementing a formula.

## Assumptions, applicability, and limits

Useful as a *starting estimate* for a Keele-like Bi-Radial mouth shape. Not established for independent JMLC wavefront-normal walls, R-OSSE rollbacks, generic conical/exponential sections, or multiple-entry systems. Other geometries may share approximate aperture/diffraction behavior, but need their own derived or measured relation.

## Common incorrect transfer

WRONG: “At 700 Hz a 50° vertical horn requires 794 mm, therefore any smaller non-Keele horn is physically impossible and should be refused before BEM.”

CORRECT: Under this particular **heuristic**, the mouth estimate is ~794 mm for 50° when `A ≈ 0.9 × B`. A 480 mm height likely involves meaningful tradeoffs and warrants investigation, but only actual source/baffle/geometry simulation or measurement establishes the resulting directivity behavior. Keep product constraints separate from physical validity.

## References

- Original patent (full text/drawings): https://patents.google.com/patent/US4308932A/en
- Corrected source dossier, check *correction header*: `docs/research/typologies/BIRADIAL_CROWE_SOURCES_2026-11-15.md`
- Historically broader (potentially misleading) application: `docs/BRIEF_AND_SCORING_GUIDE_2026-10-25.md`

## Software consequence and test

A heuristic cannot be a universal hard rejection of physically valid JMLC, OSSE, R-OSSE or MEH designs. Regression: an otherwise valid non-Keele geometry outside this heuristic should be admitted or rejected only by *its own* documented geometry/compute/product policy. **Do not modify code as part of promoting this claim without separate authorization.**

## Editor note

Starter draft: integrator must verify original patent unit convention and add a current code location before declaring this claim promoted in the canonical library.
