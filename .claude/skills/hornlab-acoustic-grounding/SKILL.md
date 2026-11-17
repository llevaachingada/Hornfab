---
name: hornlab-acoustic-grounding
description: "Check typology applicability before acoustic, geometry, source/mounting, scoring or optimization decisions in HornFab. Reuse the knowledge hub and existing evidence; catch cross-family formula and non-CD target mistakes. Skip unrelated UI, spelling and routine tooling."
---

# Acoustic grounding

Read `docs/knowledge/README.md`, the relevant family card, and its existing dossier
and correction header. This is a lightweight applicability check, not a mandate
for new research, a full audit, extra GPU work or a new dossier.

1. Identify the actual family/construction, intended behavior and affected decision.
2. Check the source claim's family, source/driver model, mounting, band, units and
   angle conventions. Distinguish physical laws, empirical heuristics, geometry
   constructions, numerical assumptions and chosen scoring targets.
3. Never generalize formulas, heuristics, targets or assumptions across typologies
   without checking applicability. Keele mouth sizing is not a universal geometric
   limit. Do not silently impose CD scoring on intentionally non-CD horns. A DI
   slope target alone does not create frequency-dependent beamwidth targets.
4. For implementation decisions, inspect the actual current config/code and relevant
   evidence. Preserve uncertainty/access labels; inherited verification is not a new
   check. An ideal source, successful mesh or low screen J does not establish
   real-driver or converged full-band performance. Never rank raw J across objectives.
5. Cite the reused dossier and state any material applicability gap briefly in the
   task result. Consult original sources only as needed for a consequential unresolved
   claim. Record durable corrections without deleting historical research.

For new/changed construction laws, typologies, mounting concepts or acoustic objective
priorities, also use `.claude/skills/hornlab-typology-research/SKILL.md`. That skill owns
source tables/reference cases; do not duplicate its protocol here. Reuse completed
research before fetching missing evidence. Existing evidence, shape and GPU skills
retain their separate roles; this skill never authorizes solves or code changes.
