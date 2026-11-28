# Rim beak (freestanding mouth)

- Status: navigation summary. **LABELED HYPOTHESIS**, no published construction. Owner request
  2026-11-25: bring back the pulled-back / pushed-forward "beak" mouths for horns that hang
  freestanding (`rim_beak_family.py:1-13`). No acoustic evidence exists yet.
- Design principles: move each row's late body, roll-on station, return and rim along the horn axis
  by an azimuth-dependent amount, so the mouth stops being a single plane: H lips ahead of or
  behind V lips, plus a 45° scoop. The throat, source and early wall are untouched; the lip/return
  moves rigidly so its shape and curl are kept (`_rim_beak_v1.py:1-17`).
- Appropriate objectives: a controlled mouth-plane tilt / phase and diffraction experiment on a
  freestanding body: off-axis smoothness, near-field and horizontal/vertical plane phase, and a
  matched balloon comparison. Not a coverage-width lever by itself.
- Limitations: freestanding only (every solve is a freestanding model, not a baffle); no
  BEM evidence at this date; H and V beak offsets trade against the look and against the mouth's
  projected silhouette; a beak that reverses the pre-roll or moves the forward station is refused.
- Common incorrect assumptions: a beak is not the same as `rolled_terminal_family`'s C-return; a
  beak is not a CD lever; a symmetric axial shift of the whole rim is not a beak (the point is the
  azimuth-dependent differential).
- Key sources and detailed research: [FAV split-plane proposals §8](../../research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md)
  (the `osse_rollback` ridge+beak prototype it grew from), [returned-lip CD backbone dossier](../../research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md)
  (parents). Joint laws: [FAMILY_LAWS.md](../FAMILY_LAWS.md).

## Kinds / generators

| Kind / `rows.type` | Adapter | Parent |
|---|---|---|
| `beak_v1` | `rim_beak_family.py` | `rows_bb_v1` or `rolled_family_rect_bb_v1` |

Kernel: `_rim_beak_v1.py` (`SCHEMA = "rim-beak-v1"`). Quarter span only. The parent's saved recipe
(including its own schema and digest) is carried verbatim under `rows.parent_rows`, so the parent
identity is part of this design's hash (`rim_beak_family.py:4-12`).

## Knobs with legal ranges

`_rim_beak_v1.py:26-29`:

| Knob | Range | Meaning |
|---|---|---|
| `rb_h_mm` | [-60, 60] | H lips toward/away from the listener (+ = toward) |
| `rb_v_mm` | [-60, 60] | V lips toward/away |
| `rb_d_mm` | [-30, 30] | 45° diagonal scoop |
| `rb_start_frac` | [0.30, 0.90] | arc fraction where the C2 gate opens |

Config keys are `g_`-prefixed. The axial offset is
`A(psi) = rb_h cos²psi + rb_v sin²psi + rb_d sin²(2psi)`; the gate is 1 from the forward station
onward (`_rim_beak_v1.py:8-11`, `:53-55`).

## Joint validity laws (file:line)

- **Quarter symmetry only; parent type must be a supported backbone kind; parent rows required** —
  `rim_beak_family.py:77-81`.
- **Saved-recipe schema + digest** — `rim_beak_family.py:87-93`.
- **Knobs required; exactly the four `RB_KEYS`** — `rim_beak_family.py:51-60`.
- **Rim-beak law at every searched endpoint** — `rim_beak_family.py:170-182`.
- **Dormancy**: `g_rb_start_frac` is dormant when every beak amplitude is pinned at zero —
  `rim_beak_family.py:183-184`.
- **Neutral rule**: `rb_h == rb_v == rb_d == 0` returns the parent's resolved result object
  unchanged (bit-for-bit; for a `rows_bb_v1` parent that means no `outer_points` and the same
  verify mesh) — `rim_beak_family.py:8-12`, `:121-122`.
- **Kernel geometry**: a row needs a measurable pre-roll (`f >= 3`); the pre-roll must keep
  advancing axially; the forward station must not move; nonfinite output refused —
  `_rim_beak_v1.py:73-85`, `:88-89`.
- **Shell**: finite/nondegenerate inner and outer surfaces and `check_self_approach` on the
  re-offset shell — `rim_beak_family.py:132-138`; envelope through the shared `_extents` /
  `_envelope` helpers — `:139-140`.

## Inert knobs per mode

- All three amplitudes inert at `rb_h == rb_v == rb_d == 0`; the parent object is returned
  (`_rim_beak_v1.py:49-50`).
- `rb_start_frac` inert when all amplitudes are pinned at zero (`rim_beak_family.py:183-184`).
- Parent-mode knobs are inherited from the parent; the parent's own contract is validated on the
  parent-only bound subset (`rim_beak_family.py:169`).
- For a `rows_bb_v1` parent, the neutral parent result carries no `outer_points`, so the shell is
  offset by the shared `grid_build` path exactly as for the bare rows recipe.

## Implementation-digest files

`rim_beak_family.implementation_digest()` hashes `rim_beak_family.py` and `_rim_beak_v1.py` plus
`"beak_v1;parents=rows_bb_v1,rolled_family_rect_bb_v1"` (`rim_beak_family.py:41-48`). The parent
recipe's own schema/digest is carried inside `rows.parent_rows`, so it is part of the saved recipe
even though it is not folded into this module's `implementation_sha256` string.

## Best-known designs (from I3 evidence)

- None measured. There is no `docs/evidence/rim_beak*` folder and no I3 row. The `cd_bo_cohort_2026-11-25`
  folder contains `lcl_beak_*` and `iwar_beak`/`sculpted_beak` cohorts built for a 100-valid CMA
  night (`docs/evidence/cd_bo_cohort_2026-11-25/` [current; no results yet]); the earlier
  `osse_rollback` ridge+beak singles (`favRB`, FAV split-plane §8) have no evidence folder either.
- The parent backbone designs that a beak sits on are in
  [cd_backbone.md](cd_backbone.md) and [favl_canonical.md](favl_canonical.md).

## Open questions

- No BEM has been run for `beak_v1`; the sign convention (`+` = toward the listener) and the
  acoustic effect of a differential mouth plane are unmeasured.
- Interaction with the CD backbone: a V beak and the V roll-on budget may compete.
- The look/silhouette trade-off is an owner decision; the module is freestanding-only.
- The module's digest does not include the parent digest string; the parent identity is preserved
  only through `rows.parent_rows`. Confirm this is sufficient for the intended provenance before a
  published cohort.
