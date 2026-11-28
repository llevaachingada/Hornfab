# Throat sculpt (directional throat constriction / angular slot)

- Status: navigation summary. **LABELED HYPOTHESIS** overlay (`throat_sculpt_v1`), 2026-11-25. Reference
  mechanism verified on CAD: ATH ST260-BLD (Batik) is an R-OSSE with a signed angular throat angle
  `a0 = 8 - 35 sin^4 p`; its wall enters the source disk to 0.38 r0 at z 25 mm on one axis while the
  orthogonal axis opens, at near-constant area for the first ~7 mm
  ([audit](../../research/typologies/sculpted_throat_2026-11-25/02_REFERENCE_AND_REPO_AUDIT.md)).
- Design principles: keep a round, driver-matched entrance (source circle and 2 deg tangent exact), then
  deform only the forward core of an `osse_rollback` parent: (A) an angular flare-onset delay (slot; never
  below r0) and/or (C) a signed even-cosine radial sculpt that may cross below r0 (true pinch), optionally at
  constant section area; the body, mouth and lip downstream are the parent's.
- Appropriate objectives: HF horizontal-vs-vertical coverage balance and diagonal behaviour on a CD brief;
  always read with loading (z_throat) and the full balloon, never H/V cuts alone.
- Limitations: BEM is linear and the source is an ideal uniform piston: no distortion / high-SPL claim from a
  narrow waist; the mesher refuses some V-delay slots (symmetry-plane topology guard); quarter span only;
  not yet in the CLI dispatch (staged patch; it moves the `rows_bb_v1` digest).
- Common incorrect assumptions: a "ridge" relative to an expanded wall is not a pinch (report `r_min / r0`);
  a slot (flare delay) is not a contraction; BLD's −28 deg source tangent cannot be matched to a real driver;
  the earlier 18 → 14.2 mm "pinch" was a source-cap artefact.
- Key sources: [handoff](../../research/typologies/sculpted_throat_2026-11-25/00_HANDOFF_2026-11-25.md),
  [source check](../../research/typologies/sculpted_throat_2026-11-25/01_SOURCE_VERIFICATION.md),
  [evidence](../../evidence/throat_sculpting_2026-11-25/README.md).

| Kind / `rows.type` | Adapter | Parent |
|---|---|---|
| `throat_sculpt_v1` | `throat_sculpt_family.py` (kernel `_throat_sculpt_v1.py`) | plain `osse_rollback` rows |

Knobs `g_ts_c2/c4/c6` (relative to r0), `g_ts_on_mm/rise_mm/fall_mm` (positive spans), `g_ts_area` (0/1),
`g_ts_slot_h_mm/v_mm/d_mm`, `g_ts_slot_pow`, `g_ts_slot_span_mm`; spec `rows.core_step_mm`.
