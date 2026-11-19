---
id: FAMILY-JMLC-IWATA
status: starter_draft
updated_at: 2026-11-16
families: [jmlc, lecleach, iwata, lecleach_swept_hv]
key_claims: [KH-001]
---

# Le Cléac'h / JMLC and Iwata: provisional family note

**This is an example of layout, not a verified complete family card.**

- **Physical emphasis:** loading, relatively smooth flare and off-axis narrowing; family-specific directivity curve rather than universal flat H/V.
- **Exact geometry source:** Fourcade JMLC construction and reference values. Fourcade fig. 7's 8 deg is the INCLUDED angle (phi0 = 4.0 deg half-angle; JMLC_LECLEACH_RESEARCH C1), pinned by `tests/test_design_generators_lecleach.py::test_r9j_fourcade_fig7_validation_table` (resolved 2026-11-19).
- **Derived variant:** `lecleach_swept_hv` is a new H/V 3D morph, not the exact Fourcade axisymmetric solution.
- **Model boundary:** a round ideal velocity source does not establish a real HF1440 exit/phase plug. Baffle/mounting changes radiation.
- **Scoring:** inspect v6 loading-smooth against v7 CD terms; never compare raw J scores across objective versions without physical normalization. Report actual current YAML rather than assuming this family is actively on v6.
- **Do not transfer:** Keele Bi-Radial sizing relation as a hard cutoff, or ATH R-OSSE `k` parameter to a different flare mathematical system.

Original sources: https://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf , https://rintelen.ch/download/JMMLC_horns_lecture_etf10.pdf .

Repository: `docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md`, `docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md`, `docs/research/typologies/LECLEACH_HV_ELLIPSOID_2026-11-16.md`.

## Detailed research

- [JMLC construction and limits](../../research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md).
- [Family variants](../../research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md).
- [Iwata / biradial distinctions](../../research/typologies/BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md).
- [Loading-smooth objective](../../research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md).
- [Derived H/V form](../../research/typologies/LECLEACH_HV_ELLIPSOID_2026-11-16.md).

Limitations: loading intent does not guarantee low ripple, full-band performance or
real-driver parity. Check the actual source, mounting, operating band and resolved
objective; Iwata and swept H/V variants are not interchangeable exact JMLC solutions.
