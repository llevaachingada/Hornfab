# Klangfilm–Lamé

- Status: navigation summary. Original derivation of Ahlswede's 2018 Klangfilm spherical-wave
  calculator (Kolbrek 2007 basis) with a Lamé (superellipse) section; **not** an exact
  reproduction of Ahlswede's unpublished 2019 calculator (`_klangfilm_lame_v1.py:1-21`). Three
  versioned kinds exist. Phase A (entrance tangents) and Phase B (monotone core + beak) are
  CPU geometry; the Phase A acoustic authority measured small.
- Design principles: a spherical-wave parent `R0 = c/(pi fc)`, cap height `h`, target curved area
  `S(h) = 2 pi R0 h` and wall `y = sqrt(2 R0 h - h^2)` sets the axial rollback. At each station a
  Lamé outline `|x/a|^p + |y/b|^p = 1` with `a = q b` is solved so the curved-cap area matches
  `S(h)`. `q` and `p` follow one C2 quintic gate from the round throat to the mouth. The rollback is
  the profile itself, not an added lip.
- Appropriate objectives: loading, the family's own narrowing directivity curve, response
  smoothness, and the physical envelope. It is a spherical-wave horn, **not** constant directivity;
  score it on a smooth/loading brief unless a labelled CD hybrid is being tested.
- Limitations: the curl radius is tied to `fc`; V is mouth/roll-on limited; the Phase A entrance
  offset has little acoustic authority; the Phase B core drops the returning lip; the source
  angle is an assumption, not an HF1440 datasheet value.
- Common incorrect assumptions: a Lamé/elliptical mouth does not imply CD; `end_frac` changes depth
  and wrap, not outer W/H; an added torus "lip radius" would leave the published method; do not
  transplant Crowe/Keele construction.
- Key sources and detailed research: [Klangfilm ellipse hand-off](../../research/typologies/KLANGFILM_ELLIPSE_HANDOFF_2026-11-16.md),
  [Klangfilm contract](../contracts/klangfilm_lame_hv.md),
  [directivity attribution](../../evidence/directivity_attribution_2026-11-24/README.md). Joint
  laws: [FAMILY_LAWS.md](../FAMILY_LAWS.md).

## Kinds / generators

| Kind / `rows.type` | Adapter | Kernel | Meaning |
|---|---|---|---|
| `klangfilm_lame_v1` | `klangfilm_lame_family.py` | `_klangfilm_lame_v1.py` | spherical-wave parent + Lamé section, curved-cap area lock |
| `klangfilm_lame_hv_cd` | `klangfilm_lame_hv_family.py` | `_klangfilm_lame_hv_v1.py` | Phase A: independent H/V entrance tangents on the round rim |
| `klangfilm_lame_hv_core` | `klangfilm_lame_hv_core_family.py` | `_klangfilm_lame_hv_core_v1.py` | Phase B: monotone integrated-slope H/V core + swept beak |

All are quarter span only.

## Knobs with legal ranges

`klangfilm_lame_v1` (module physical limits, `_klangfilm_lame_v1.py:36-38`, checked `:41-54`):

| Knob | Range |
|---|---|
| `fc_hz` | [150, 3000] |
| `aspect` (`q`) | [1, 4] |
| `lame_p` | [2, 8] |
| `end_frac` | [0.3, 1.9] |
| `rim_sweep_ratio` | [-0.6, 0.6] |
| `morph_frac` | [0.05, 0.9] |
| `source_blend_ratio` | [0, 2] |
| `entry_half_angle_deg` | [0, 20] |
| `wall_thickness_mm` | > 0 |
| `n_phi`, `n_s` | integers, `n_phi >= 7`, `n_s >= 24` |

Phase A adds (`_klangfilm_lame_hv_v1.py:67-69`): `cd_core_blend` [0, 1], `theta_h0_deg` /
`theta_v0_deg` [0, 25], `h_mid_gain_mm` / `v_mid_gain_mm` [-80, 80], `core_join_fraction` [0.05, 0.95].

Phase B adds (`_klangfilm_lame_hv_core_v1.py:73-81`): `cd_core_blend` [0, 1], `theta_h0/v0_deg`
[0, 25], `theta_h1/v1_deg` [5, 60], `core_length_mm` [30, 480], `lame_p_mouth` [2, 8],
`lame_start_frac` / `lame_end_frac` [0, 1], `beak_h_setback_mm` [0, 60],
`beak_v_projection_mm` [0, 45], `beak_diagonal_mm` [-20, 20], `beak_start_frac` [0.50, 0.99];
plus `lame_start_frac < lame_end_frac` and every `theta_* < 89°` (`:107-111`).

`size_policy` ∈ {`enforce`, `report_only`} (Phase A `:36`; Phase B `:37`).

## Joint validity laws (file:line)

- **Quarter symmetry only** — `klangfilm_lame_family.py:64-65`; Phase A
  `klangfilm_lame_hv_family.py:76-77`; Phase B `klangfilm_lame_hv_core_family.py:78-79`.
- **Driver** positive radius and exit angle in (0, 45) — `klangfilm_lame_family.py:46-55`
  (same in the Phase A/B adapters).
- **Saved-recipe schema + digest + driver** must match — `klangfilm_lame_family.py:66-71`;
  Phase A `:80-85`; Phase B `:82-87`.
- **Exact knob set** — `klangfilm_lame_family.py:72-75`; Phase A `:86-89`; Phase B `:88-91`.
- **Kernel physics**: `end_frac` must exceed the throat cap height (`_klangfilm_lame_v1.py:77-78`);
  a source blend longer than the forward-going part is refused (`:123-127`).
- **Phase A dormancy**: when `cd_core_blend` is fixed at 0, the Phase-A knobs
  (`g_theta_h0_deg`, `g_theta_v0_deg`, `g_h_mid_gain_mm`, `g_v_mid_gain_mm`,
  `g_core_join_fraction`) are inert and must be pinned; a blend box reaching 0 with a searched
  Phase-A knob is refused — `klangfilm_lame_hv_family.py:39-41`, `:165-176`.
- **Phase A forward invariants**: round throat `a(0)=b(0)=r0`, non-shrinking non-decreasing
  forward radii, finite — `_klangfilm_lame_hv_v1.py:169-181`; the core join must lie strictly
  inside `(0, z_turn)` (`:147-150`).
- **Phase B classes**: `cd_core_blend` must be **fixed**, because legacy (`0`) and `hv_core` (`1`)
  are incompatible classes — `klangfilm_lame_hv_core_family.py:168-171`. In legacy mode every
  `CORE_KEYS` key except the blend is inert (`_INERT_AT_ZERO`, `:40-41`, `:172-177`); in `hv_core`
  mode every parent key is inert (`_INERT_AT_ONE = _PARENT_KNOBS`, `:42`, `:173-177`).
- **Phase B geometry**: shared-z H/V meridians, monotone `tan theta > 0`
  (`_klangfilm_lame_hv_core_v1.py:120-126`, `:135-136`), the beak is exactly zero before
  `beak_start_frac` (`:149-159`), section exponent `p(z)=2` until `lame_start_frac`
  (`:141-146`).
- **Entry-angle dormancy**: `g_entry_half_angle_deg` is inert with zero source blend, so it may not
  be searched when `g_source_blend_ratio` can be 0 — `klangfilm_lame_family.py:140-142`.
- **`report_only` is a diagnostics lane**: it cannot be used with any searched bound —
  Phase A `klangfilm_lame_hv_family.py:178-182`; Phase B
  `klangfilm_lame_hv_core_family.py:178-180`.
- **Envelope** `max_mouth_w_mm`, `max_mouth_h_mm`, `max_depth_mm`; the area law is reported, not
  re-locked after the Phase A deformation (`meta.area_mode = deformed_after_cap_lock`) —
  `klangfilm_lame_hv_v1.py:229-236`.

## Inert knobs per mode

- `klangfilm_lame_hv_core`, blend fixed 0 (legacy): all Phase-B knobs except `cd_core_blend` inert.
- `klangfilm_lame_hv_core`, blend fixed 1 (`hv_core`): all parent keys inert.
- `klangfilm_lame_hv_cd`, blend 0: all Phase-A knobs inert.
- `klangfilm_lame_v1`: `entry_half_angle_deg` inert when `source_blend_ratio == 0`.
- Phase B beak knobs (`beak_h_setback_mm`, `beak_v_projection_mm`, `beak_diagonal_mm`) act only
  after `beak_start_frac` (mouth-only); `beak_start_frac` without any beak amount is refused
  (`grid.py` analogue; in the kernel `:149-159`).

## Implementation-digest files

- v1: `klangfilm_lame_family.py`, `_klangfilm_lame_v1.py`, `_lame_cap_v1.py`, `lame_shell.py`,
  plus numpy/scipy versions (`klangfilm_lame_family.py:36-43`).
- Phase A: `klangfilm_lame_hv_family.py`, `_klangfilm_lame_hv_v1.py`, `_klangfilm_lame_v1.py`,
  `_lame_cap_v1.py`, `lame_shell.py`, plus numpy/scipy (`:47-55`).
- Phase B: `klangfilm_lame_hv_core_family.py`, `_klangfilm_lame_hv_core_v1.py`,
  `_klangfilm_lame_v1.py`, `_lame_cap_v1.py`, `lame_shell.py`, plus numpy/scipy (`:49-57`).

## Best-known designs (from I3 evidence)

- `docs/evidence/klangfilm_hv_2026-11-16/` [current; Phase A negative-result] — Phase 1 7/7 OK;
  `B_o50` best B beats control by 0.251; Phase 3 best J **5.608**; Phase-A offsets moved pattern
  ≤ 2.74° in the wrong direction → Phase B core warranted.
- `docs/evidence/directivity_attribution_2026-11-24/` [current] — Lamé V4 anchor `0782945027ae`;
  `lame_morph_040` J 11.221 → **9.084**; `lame_hmid_m2` J **10.736** (clean H-only lever).
- `docs/evidence/cd_backbone_2026-11-25/` [current; Lamé arm negative] — Lamé control
  `lame_morph_040` J **9.0845**; every CD-backbone dose fails (2–4 kHz waistband and loading).
- `docs/evidence/klangfilm_hv_2026-11-16/PHASE_B_GEOMETRY.md` and
  [the Klangfilm contract](../contracts/klangfilm_lame_hv.md) record the Phase B geometry seeds
  (`_klangfilm_lame_hv_core_v1.py:286-298`).

## Open questions

- The CD backbone trades a 2–2.5 kHz waistband and low-end loading for HF width on this body; a
  different mouth/roll-on budget or depth is the next lever, not more backbone knobs.
- Phase A entrance tangent authority is small; the Phase B monotone core drops the returning lip.
- `R0`, curl radius and rollback are tied to `fc`; an independent lip radius would leave the
  published method.
- Frozen-copy docstring SHA256 values do not match the current tools files (line-ending
  normalised); the core/Phase-A copies differ only by docstring/imports
  (`docs/knowledge/contracts/klangfilm_lame_hv.md` §drift). Read the contract, not the docstring.
