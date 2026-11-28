# Rolled family (rolled rectangle / Crowe-section relief)

- Status: navigation summary. Original HornFab construction, CPU geometry plus simulated BEM;
  **not** a reproduction of Crowe's proprietary ES equation or of Batík Tritonia (labelled in
  `_rolled_rect_v1.py:122`). Axial and inward relief are separate named mechanisms.
- Design principles: a shrinking-curvature spiral reference contour drives a superelliptic
  cross-section from a round throat to a landscape rectangular mouth, continues through a real
  returned mouth, and optionally adds an inward radial or a signed axial relief inside a quintic
  window. A categorical base plus `mode` selects which relief is live.
- Appropriate objectives: H/V and diagonal coverage trajectory, response smoothness, loading,
  and the physical envelope for the actual freestanding body. It is not constant directivity by
  construction; measured 6–8 kHz H follows the early wall angle (see evidence below), so score it
  on the brief it was built for and against its own control.
- Limitations: in the default path relief is inactive in the first ~15 % of stations
  (`relief_start_s >= .15`); the optional `hv_onset_frac` block can start it earlier but still after
  the source matching region, so there is no true near-throat H/V relief. The shell is a
  meridian-offset approximation; there is no published parent for the relief terms (LABELED
  HYBRID); one shared H/V window (no per-plane window yet).
- Common incorrect assumptions: an axial z cosine is not Batík's radial ATH mechanism; a high
  rectangular exponent is not a CD guarantee; a paragraph number in the superformula does not
  set directivity; do not transfer Keele mouth sizing to this family.
- Key sources and detailed research: [master research](../../research/typologies/ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md),
  [rect construction study](../../research/typologies/ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md),
  [section/pucker contract](../contracts/rolled_section_pucker.md). Joint laws:
  [FAMILY_LAWS.md](../FAMILY_LAWS.md).

## Kinds / generators

`hornlab_search/design/generators/rolled_family.py`:

| Kind | Parent kernel | Meaning |
|---|---|---|
| `rolled_family_rect_v1` | `_rolled_rect_v1.py` | spiral rolled rectangle (pucker slots are neutralised) |
| `rolled_family_section_v1` | `_crowe_section_v2.py` | section-constrained ES-600 study (Crowe-inspired reconstruction) |

`MODES = ('smooth', 'radial', 'axial', 'hybrid')` (`rolled_family.py:19`). Quarter span only.
Related CD variant `rolled_family_rect_cd_v1` lives in `rolled_cd_family.py` (not this card).

## Knobs with legal ranges

Parent limits (checked by each kernel's `validate_shape`, `_rolled_rect_v1.py:39-58`):

| Knob | Legal range |
|---|---|
| `width_mm` | > 0, and `width_mm > height_mm` |
| `height_mm` | > 0 (family also `height_lo > 2*driver exit radius`, see law below) |
| `depth_mm` | > 0 |
| `depth_h_ratio` | [0.5, 1.2] |
| `decay` | > 0 |
| `rect_exponent` | [2, 16] |
| `throat_turn_deg`, `rect_turn_deg` | `0 < throat_turn_deg < rect_turn_deg < 90` |
| `terminal_deg` | (180, 280] |
| `pucker_start_deg` | `throat_turn_deg < pucker_start_deg < 180` (neutralised in the family) |
| `pucker_h_mm`, `pucker_v_mm` | `max(|.|) <= 0.15*depth_mm` (dropped from the family keys) |
| `wall_thickness_mm` | > 0 |
| `n_phi`, `n_s` | integers, `n_phi >= 25`, `n_s >= 32` |

Family relief keys (`rolled_family.py:21-22`): `inward_h_mm`, `inward_v_mm`, `axial_h_mm`,
`axial_v_mm`, `relief_start_s`, `relief_peak_s`, `relief_end_s`. Optional shared near-throat block
`g_throat_hv_ratio`, `g_hv_onset_frac`, `g_section_exp_ramp` (`design/throat_hv.py:29-32`;
`throat_hv_ratio` [0.25, 4.0], `hv_onset_frac` [0, 0.9], `section_exp_ramp` [0.5, 8]).
Driver: `exit_radius_mm > 0`, `exit_angle_deg` in (0, 45) (`rolled_family.py:59-61`).

## Joint validity laws (file:line)

- **Axial relief ≤ 10 % of depth; inward relief ≥ 0 and ≤ 15 % of height** —
  `hornlab_search/design/generators/rolled_family.py:133-138`. Rationale undocumented; see
  [FAMILY_LAWS.md](../FAMILY_LAWS.md).
- **Relief window**: with no onset block, `.15 <= relief_start_s < relief_peak_s < relief_end_s <= .96`;
  with `hv_onset_frac`, `0 <= hv_onset_frac < relief_peak_s < relief_end_s <= .96` —
  `rolled_family.py:128-132`.
- **`hv_onset_frac` and `g_relief_start_s` are mutually exclusive** — `rolled_family.py:109-110`;
  `g_relief_start_s` is removed from the expected set when the onset is given (`:116`).
- **Knob set must equal the exact expected set** — `rolled_family.py:112-119`.
- **Mode amplitudes**: `smooth` forbids both; `axial` forbids radial; `radial` forbids axial —
  `rolled_family.py:139-142`.
- **Window cannot be dormant**: `hv_onset_frac`/`section_exp_ramp` need a nonzero relief amplitude
  or a non-neutral `throat_hv_ratio` — `rolled_family.py:143-145`.
- **Source match**: the actual continuous base (not just driver metadata) must be a circle of the
  driver radius, advance in z, and have tangent `tan(exit_angle)` —
  `rolled_family.py:180-193`.
- **Relief onset must not intersect the source matching region** — `rolled_family.py:214-215`.
- **Relief must be zero at the exterior-body attachment normal** (`w[-2:] == 0`) —
  `rolled_family.py:217-218`.
- **Inward relief must not reach the centerline** — `rolled_family.py:225-226`.
- **No constriction before the mouth roll** — `rolled_family.py:238-243`.
- **Finite / nondegenerate sheets and shell clearance** — `rolled_family.py:246-252`.
- **Envelope** `max_mouth_w_mm`, `max_mouth_h_mm`, `max_depth_mm` — `rolled_family.py:253-258`.
- **Search contract** (`validate_search_config`, `rolled_family.py:284-330`):
  - every knob needs an explicit matching bound (`:291-292`);
  - seed inside its bounds (`:295-297`); a fixed bound must equal its seed (`:298-299`); no log
    bounds (`:300-301`);
  - **every bound endpoint is re-validated against the seed's other values** (`:303-304`);
  - inactive mode amplitudes must be pinned to 0 (`:306-310`);
  - **independent relief position bounds must not overlap**: `start_hi < peak_lo` and
    `peak_hi < end_lo` (`:311-314`);
  - **position cannot be dormant**: a searched window position needs a strength box away from 0
    (or a throat ratio excluding 1) (`:315-323`);
  - **`width_lo > height_hi`** (no non-landscape shape) (`:324-325`);
  - **`height_lo > 2*driver exit radius`** (`:326-327`);
  - for `rolled_family_rect_v1`: **`throat_turn_deg_hi < rect_turn_deg_lo`** (`:328-330`).

## Inert knobs per mode

- `smooth`: `inward_h/v_mm` and `axial_h/v_mm` must be 0 (`rolled_family.py:139-142`); in search
  they must be fixed at 0 (`:306-310`).
- `axial`: inward amplitudes must be 0.
- `radial`: axial amplitudes must be 0.
- `hybrid`: both are live.
- `pucker_h_mm`, `pucker_v_mm`, `pucker_start_deg` are derived neutral legacy slots, dropped from
  the family's `shape_keys` and pinned (`rolled_family.py:44`, `:69`).
- `g_relief_start_s` is inert/replaced when `g_hv_onset_frac` is present (`:109-116`).

## Implementation-digest files

`rolled_family.implementation_digest()` hashes `rolled_family.py`, `_rolled_rect_v1.py`,
`_crowe_section_v2.py` and the Crowe reference YAML (`rolled_family.py:32-39`). Editing any of
these orphans saved recipes; put new behaviour in a new module and register it byte-wise (CRLF) in
the dispatch lists.

## Best-known designs (from I3 evidence)

- `docs/evidence/cd_backbone_2026-11-25/` [current] — rolled CD-backbone hybrids on anchor
  `fa5b207bca6d`: neutral control J 8.121 → `bb_h` 0.5 J **5.407** (H 65.7° at 8 kHz); second body
  `20874108fe25` J 7.683 → **4.562** at `bb_h` 0.65/throat 0.25.
- `docs/evidence/directivity_attribution_2026-11-24/` [current] — rolled anchor J 8.121;
  `rolled_h10_early` J **6.533**, 8 kHz H 63.1°; `rolled_h20_early` J 6.001, 8 kHz H 70.5°.
- `docs/evidence/klangfilm_hv_2026-11-16/` [current / partly negative-result] — throat-H/V
  Phase 1 7/7 OK, best J **5.608**; the Phase-A offsets moved pattern ≤ 2.74° in the wrong
  direction.
- `docs/evidence/directivity_attribution_2026-11-24/` documents the mechanism: 6–8 kHz H tracks
  the wall angle at ~20–40 % of the pre-roll arc.

## Open questions

- The 10 % axial / 15 % inward limits have no recorded rationale (commit `c2c91905`); do not
  relax them here — a separate geometry task owns any versioned relaxed kind.
- In the default path relief is inactive below ~15 % of stations; the `hv_onset_frac` block can
  start earlier but not inside the source matching region, so this family has no true near-throat
  H/V control (`THROAT_HV_CONTROL_AUDIT_2026-11-18.md` row 14).
- The CD/terminal variants share one H/V window; per-plane windows need a versioned kernel.
- V is mouth-limited; no backbone or relief dose fixes low-band V.
