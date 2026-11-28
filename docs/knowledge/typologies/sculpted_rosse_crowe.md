# Sculpted R-OSSE meridians / Crowe-inspired sections

- Status: navigation summary. Three distinct, versioned constructions are grouped here because they
  share the "sculpt the meridian / section, then score" workflow. None is a published geometry:
  the sculpted R-OSSE family is a HornFab hypothesis around an independently checked published
  R-OSSE evaluator; the Crowe families are labelled reconstructions, **not** Crowe's proprietary ES
  equation.
- Design principles: (a) the sculpted family varies the native R-OSSE meridian parameters with
  physical azimuth, keeping one round entrance collar and a returned lip; (b) the Crowe section
  study rescales raster-measured H/V meridians and rebuilds an intersecting swept wall; (c) the
  Crowe V2A family separates a constrained area law from an aspect law, with a fixed section
  exponent and round throat.
- Appropriate objectives: coverage trajectory (H, V and diagonal), response smoothness, DI
  flatness, loading, and the physical envelope. The sculpted R-OSSE body is conical-ish and already
  carries a CD-style lever; the Crowe families were built to test vertical-control trade-offs, not
  to assert a CD result.
- Limitations: the sculpted R-OSSE pilot is a fixed 49 × 96 grid, fixed 3 mm shell and
  `report_only` size policy; the Crowe study is a reconstruction with a rebuilt exterior; the V2A
  family has four search dimensions and no returned lip; C2-class shells still need a fitted-surface
  audit; STEP/CAD export is not available.
- Common incorrect assumptions: a sculpted R-OSSE meridian is not the archived R-OSSE reference;
  a Crowe-like X/crease is not a CD guarantee; equal section area does not imply equal acoustics;
  do not treat the V2A `aspect_timing_u50` as a `z/L` station when it is an arc/forward fraction.
- Key sources and detailed research: [sculpted meridians checkpoint](../../evidence/sculpted_meridians_2026-11-20/README.md),
  [CROWE V2 research](../../research/typologies/CROWE_HV_AREA_ASPECT_RESEARCH_V2_2026-11-16.md),
  [V2A addendum](../../research/typologies/CROWE_V2A_THROAT_TRANSITION_ADDENDUM_2026-11-16.md),
  [Crowe sources](../../research/typologies/BIRADIAL_CROWE_SOURCES_2026-11-15.md). Joint laws:
  [FAMILY_LAWS.md](../FAMILY_LAWS.md).

## Kinds / generators

| Kind / generator | Module | Meaning |
|---|---|---|
| `sculpted_rosse_meridians_v1` | `sculpted_rosse_family.py` (+ `geometry/_sculpted_rosse_v1.py`) | per-azimuth native R-OSSE body + optional terminal finish |
| `crowe-section-study-v2` | `_crowe_section_v2.py` | section-constrained ES-600 reconstruction |
| `crowe_hv_area_aspect_v1` | `crowe_hv_area_aspect_v1.py` | forward area/aspect/section family, no returned lip |

## Knobs with legal ranges

Sculpted R-OSSE (`sculpted_rosse_family.py`):
- R knob set: `g_sweep`, `g_diagonal_delta_deg`, `g_aperture_scale` (`:18`).
- K knob set: `g_h_setback_mm`, `g_v_projection_mm` (`:19`).
- Exactly one of the two sets must be present, finite (`:55-56`).
- Fixed block: `span: quarter`, `size_policy: report_only`, `n_phi 49`, `n_s 96`,
  `wall_thickness_mm 3.0` (`:40-42`), source 18 mm radius / 2° / auto cap / H/V symmetry (`:62-68`).
- Kernel domain (`geometry/_sculpted_rosse_v1.py`): `n_phi >= 9`, `n_s >= 24`, increasing collar
  (`:92-93`); landscape `width > height > 2 r0` and `exponent` [2, 10] (`:94-95`); `k` [0.5, 10],
  `q` [1, 10], `tmax` [0.8, 1] (`:96-97`); driver `0 < angle < 45` (`:98-99`); interpolated
  opening angle [5, 75]°, apex shift [0.5, 0.99], apex radius [0.05, 2], bend [-0.1, 1]
  (`:106-111`); terminal start [0.5, 0.93] (`:66-67`).

Crowe section study (`_crowe_section_v2.py:22-40`): `width > height > 0`, `depth > 0`;
`h_depth_scale` [0.9, 1.1]; `crown_mm` [0, 0.2·height); `junction_power` [16, 48];
`0 < throat_blend_mm < 0.2·depth`; `wall_thickness_mm > 0`; `n_phi >= 25`, `n_s >= 48`.

Crowe V2A (`crowe_hv_area_aspect_v1.py`): exactly four search dimensions `height_v_active_mm`,
`L_forward_mm`, `area_mid_bias`, `aspect_timing_u50` (`:62-68`); fixed generator keys `n_anchors`
[9, 32], `wall_thickness_mm` [0.5, 12], `width_h_active_mm`, `p_mouth` [2, 5],
`throat_round_hold_mm` [0, 200] (`:71-89`); `area_mid_bias` [-0.15, 0.15],
`aspect_timing_u50` (0.15, 0.75) (`:83-89`, `:164`); `throat_round_hold_mm < L_forward_mm/2`
(`:167`); `m0` in [0, 2] (`:236-249`).

## Joint validity laws (file:line)

Sculpted R-OSSE:
- **Quarter, fixed grid, `report_only`, digest** — `sculpted_rosse_family.py:37-47`.
- **Knobs must be exactly one finite R or K set** — `:55-56`.
- **Source is exactly 18 mm / 2° / auto cap** — `:62-68`.
- **One forward apex, no secondary turn; no self-intersecting meridian; no degenerate/reversed
  wall cell; shell clearance** — `:111-129`.
- **Kernel invariants**: one forward branch and a returning lip; the returned lip may not overlap
  the entrance collar; positive finite radius — `_sculpted_rosse_v1.py:128-138`.

Crowe section study:
- **Landscape dimensions and the reconstruction's hard limits** — `_crowe_section_v2.py:22-40`.
- **H section behind the V forward extremum; single-peaked H sweep; shared return domain** —
  `:60-77`.

Crowe V2A:
- **Exactly four search keys** — `crowe_hv_area_aspect_v1.py:530-540`.
- **Throat is exactly round at z=0; `a(0)=b(0)=r0`, `p(0)=2`; source tangent** — see the
  construction contract in the V2A addendum §C.
- **`aspect_timing_u50` in (0, 1); `throat_round_hold_mm < L_forward_mm/2`** — `:164`, `:167`.

## Inert knobs per mode

- Sculpted: the R and K knob sets are mutually exclusive (`:55`); `n_phi`, `n_s`, `wall_thickness_mm`
  and the source are fixed, not searchable; the K knobs are irrelevant in R mode and vice versa
  (`:95-108`).
- Sculpted finish: `start_arc` fixed in [0.5, 0.93]; a zero finish is the identity
  (`_sculpted_rosse_v1.py:66-73`).
- Crowe V2A: `width_h_active_mm`, `p_mouth`, `throat_round_hold_mm` are fixed generator-block values,
  not search dimensions (`:62-80`); only `area_mid_bias` and `aspect_timing_u50` are continuous
  search controls beside the two size/length controls.

## Implementation-digest files

- Sculpted: `sculpted_rosse_family.py`, `geometry/_sculpted_rosse_v1.py`, `lame_shell.py`,
  `hornlab_mesher/profile_formulas.py` (`sculpted_rosse_family.py:26-34`).
- Crowe section: `_crowe_section_v2.py` plus `data/crowe_section_reference_v1.yaml`
  (`_crowe_section_v2.py:14-15`).
- Crowe V2A: its own module plus numpy/scipy versions (`crowe_hv_area_aspect_v1.py:101-108`).

## Best-known designs (from I3 evidence)

- `docs/evidence/sculpted_xo900_v11_2026-11-21/` [current] — matched 51-frequency verify cohort:
  R3 J **2.694** (H/V RMS 4.47/4.10°), R2 **3.106**, K1 3.153, K2 3.097; controls 2.9–3.4.
- `docs/evidence/sculpted_meridians_2026-11-20/` [current; geometry checkpoint only] — nine
  derivatives + two byte-matched controls; R0 exact archived R-OSSE replay; no acoustic ranking.
- `docs/evidence/home_xo900_2026-11-20/` [current] — saved-response ranking of FAV-001,
  extended-throat OSSE, OSSE morph/fold-warm, ATH CORE petal; R2/R3 and K1/K2 contrast authority.
- `docs/evidence/home_crowe_v9_offline_2026-11-17/` [current] — five not-queued v9 Crowe scenarios;
  slope-0 best J 0.940, others ~9.3–9.96; cross-brief rank refused.
- `docs/evidence/crowe_v2a_geometry_truth/` [current; geometry only] — 12 admitted four-DOF cases;
  no invalid corner dropped, no outcome claimed.

## Open questions

- C2-class sculpted shells still need a fitted-surface audit; STEP/CAD export is refused on the GRID
  route.
- The sculpted acoustic comparison is a single-seed matched cohort; no CMA campaign admitted.
- The Crowe V2A four-DOF family is a geometry/diagnostics lane, not solved as a search.
- The native R-OSSE evaluator is an installed mesher dependency; the sculpted family is a
  hypothesis around it, not the archived reference.
