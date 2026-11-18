# Acoustic knowledge hub

This is the canonical **navigation and applicability guidance** for acoustic, geometry,
scoring and optimization decisions. It does not replace frozen contracts or establish
that a research proposal is implemented. Read the relevant family card and its linked
research before changing a physical assumption or target.

**Never generalize acoustic formulas, heuristics, design targets or assumptions across
horn typologies without checking applicability.** Keele mouth sizing is a scoped
Bi-Radial heuristic, not a universal geometric limit. JMLC, OSSE, biradial and MEH have
different constructions and constraints. Do not silently impose constant-directivity
scoring on intentionally non-CD horns. Check the actual brief, objective version and
resolved targets; a DI slope target does not itself define sloping beamwidth targets.

## Reading path

1. Choose a compact family reference below; follow its detailed dossier and corrections.
2. Consult the [source catalog](SOURCES.md), [source metadata](sources.yaml), and
   [Keele applicability claim](claims/KH-001_keele_mouth_heuristic.md).
3. Check current code/config and relevant measured evidence for an implementation decision.
   Research labels describe their original evidence, not a new verification by this cleanup.

| Family | Compact reference |
|---|---|
| JMLC / Le Cleac'h / Iwata | [Family card](typologies/lecleach_iwata.md) |
| OSSE / R-OSSE / ATH | [Family card](typologies/osse_ath.md) |
| Keele / biradial | [Family card](typologies/biradial.md) |
| Conical / exponential / tractrix | [Family card](typologies/classical.md) |
| Salmon / X-shape | [Family card](typologies/salmon.md) |
| Multicell | [Family card](typologies/multicell.md) |
| MEH / multiple-entry | [Family card](typologies/meh.md) |
| Derived morphs / rolled and experimental forms | [Family card](typologies/experimental_morphs.md) |

Hybrid and new-law **construction contracts** (draft, 2026-11-18): [contracts/](contracts/README.md).

## Authority and history

- [Research basis](../plan/12_RESEARCH_BASIS.md): existing plan basis, preserved in place.
- [Detailed typology research](../research/typologies/),
  [senior-pass guide](../research/senior_pass_2026-10-24/README.md), and
  [full docs index](../INDEX.md): historical dossiers, corrections, proposals and evidence.
  Read status/correction headers; historical guidance is not blanket current policy.
- [Imported 2026-11-16 compilation](imported/HornFab_Research_Knowledge_Base_2026-11-16.md):
  supplied synthesis preserved verbatim, including source links and uncertainty labels.
  Its proposed actions, old code references and verification statements are historical
  source material, not new implementation requirements or newly checked findings.
- [Master plan: acoustic truth, typology and optimization (2026-11-17)](../research/HORNFAB_ACOUSTIC_TRUTH_MASTER_PLAN_2026-11-17.md):
  prioritized WP0–WP6 implementation handoff (owner-supplied proposal). Distinct from the
  implemented v9 code and the still-open FABLE scoring menu; WP5/WP6 remain owner-gated.
- [Claim template](templates/claim.md) and [family template](templates/typology.md):
  optional small notes for genuinely new knowledge; link existing research rather than copy it.

## Agent workflows

Use `hornlab-acoustic-grounding` for a short applicability check. Use the existing
`hornlab-typology-research` only when its new construction/objective scope applies;
reuse existing dossiers and fetch only missing evidence. No full audit is required
for ordinary library maintenance. Claude and OpenCode use the canonical skill at
`.claude/skills/hornlab-acoustic-grounding/SKILL.md`; Codex has a thin entrypoint in
`.agents/skills/`. OpenCode fixer/designer grants include the grounding skill.
