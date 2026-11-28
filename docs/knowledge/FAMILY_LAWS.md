# FAMILY_LAWS — joint validity laws across generator families

One place for the rules that decide whether a design is legal, and *why* they exist. A law is only
listed here if it is enforced in code; the `file:line` is the enforcement site. Every law carries a
rationale status:

- **documented** — a dossier/contract/skill states the reason (link given).
- **undocumented (code only, commit X)** — the rule exists only in code; the commit is the one that
  introduced the rule (or the last change to the enforcing file). These are candidates for a
  rationale, not for silent change.

This page is a reference, not a licence to change a bound. A relaxed or new law needs a new
versioned kind; the 10 %/15 % rolled limits in particular are owned by a separate geometry task
(see the handoff §6, decision 5).

Related cards: [rolled](typologies/rolled.md), [Klangfilm–Lamé](typologies/klangfilm_lame.md),
[sculpted R-OSSE / Crowe](typologies/sculpted_rosse_crowe.md), [CD backbone](typologies/cd_backbone.md),
[rim beak](typologies/rim_beak.md), [favL / osse_rollback](typologies/favl_canonical.md).

---

## 1. Rolled family validate path

File: `hornlab_search/design/generators/rolled_family.py` (last changed `c9423c81`, 2026-11-17).
The research rationale for the family is
[ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md](../research/typologies/ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md)
("Unified mapping and activity contract", lines 39–51) and
[ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md](../research/typologies/ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md).

| Law | `file:line` | Rationale |
|---|---|---|
| Driver: `exit_radius_mm > 0`, `exit_angle_deg` in (0, 45) | `rolled_family.py:59-61` | documented — construction assumes a round driver; rect study §Original construction |
| Quarter symmetry only | `rolled_family.py:92-93` | documented — MASTER "structural sampling, family and mode are fixed" (`:46-47`) |
| Explicit `mode` in `smooth/radial/axial/hybrid` | `rolled_family.py:94-96` | documented — MASTER "A categorical base/mode lives in the recipe, not a numeric optimization dimension" (`:27-28`) |
| Saved schema/digest and driver must match the recipe | `rolled_family.py:97-102` | documented — MASTER "Cold replay ... requires an exact recipe hash match" (`:48`) |
| Exact knob set (no unknown/omitted knob) | `rolled_family.py:112-119` | documented — MASTER "Only meaningful keys enter each optimization" (`:45`) |
| Relief window: `.15 <= relief_start_s < relief_peak_s < relief_end_s <= .96` (or `0 <= hv_onset_frac < peak < end <= .96`) | `rolled_family.py:128-132` | documented — MASTER "Quintic onset/peak/end windows keep the source and returned attachment intact" (`:34-35`) |
| **Inward relief `0 <= inward <= 0.15*height_mm`** | `rolled_family.py:133-135` | **undocumented (code only, commit `c2c91905`)** — no recorded rationale; do not relax here |
| **Axial relief `abs(axial) <= 0.10*depth_mm`** | `rolled_family.py:136-138` | **undocumented (code only, commit `c2c91905`)** — no recorded rationale; do not relax here |
| Mode inactivity: `smooth` forbids both; `axial` forbids radial; `radial` forbids axial | `rolled_family.py:139-142` | documented — MASTER "Inactive mode amplitudes are zero and fixed" (`:45-46`) |
| Window cannot be dormant (`hv_onset_frac`/`section_exp_ramp` need relief or a non-neutral ratio) | `rolled_family.py:143-145` | documented — MASTER "placement keys are fixed when strength can be zero" (`:45-47`) |
| Source contour is the exact round driver: radius, advancing z, tangent | `rolled_family.py:180-193` | documented — MASTER "protected source tangent" (`:34-36`) |
| Relief onset must not intersect the source matching region | `rolled_family.py:214-215` | documented — MASTER "keep the source ... intact" (`:34-35`) |
| Relief must be zero at the exterior-body attachment normal | `rolled_family.py:217-218` | documented — MASTER "returned attachment intact" (`:34-35`) |
| Inward relief must not reach the horn centerline | `rolled_family.py:225-226` | documented — MASTER "A positive radius" (`:34-35`) |
| No constriction before the mouth roll | `rolled_family.py:238-243` | documented — MASTER "monotone initial expansion" (`:35`) |
| Finite, nondegenerate sheets and shell clearance | `rolled_family.py:246-252` | documented — MASTER "nondegenerate sheets, self-clearance" (`:35-36`) |
| Envelope `max_mouth_w_mm`, `max_mouth_h_mm`, `max_depth_mm` | `rolled_family.py:253-258` | documented — MASTER "full-body envelope" (`:36`) |

### Rolled search contract (`validate_search_config`)

File: `rolled_family.py:284-330`.

| Law | `file:line` | Rationale |
|---|---|---|
| Every knob needs an explicit matching bound | `rolled_family.py:291-292` | documented — MASTER "Only meaningful keys enter each optimization" (`:45`) |
| Seed inside its bounds | `rolled_family.py:295-297` | documented — MASTER "Seeds must be present, finite and inside bounds" (`:47-48`) |
| A fixed bound must equal its seed | `rolled_family.py:298-299` | documented — same (`:47-48`) |
| No log bounds (linear physical bounds) | `rolled_family.py:300-301` | undocumented (code only, commit `c9423c81`) — convention |
| **Every bound endpoint is re-validated against the seed's other values** | `rolled_family.py:303-304` | documented — MASTER "A box is a sampled feasibility region, not proof that every candidate will mesh" (`:36-37`) |
| Inactive mode amplitudes pinned to 0 | `rolled_family.py:306-310` | documented — MASTER "Inactive mode amplitudes are zero and fixed" (`:45-46`) |
| **Independent relief position bounds must not overlap** (`start_hi < peak_lo`, `peak_hi < end_lo`) | `rolled_family.py:311-314` | documented — MASTER "ordered window bounds cannot overlap" (`:46-47`) |
| **Window position is non-dormant**: a searched position needs a strength box away from 0 (or `throat_hv_ratio` excluding 1) | `rolled_family.py:315-323` | documented — MASTER "placement keys are fixed when strength can be zero" (`:46-47`) |
| **`width_lo > height_hi`** (landscape only) | `rolled_family.py:324-325` | documented — rect study "Landscape proportions"; `_rolled_rect_v1.py:42-43` |
| `height_lo > 2 * driver exit radius` | `rolled_family.py:326-327` | documented — rect study "mouth must exceed the driver exit"; `_rolled_rect_v1.py:73-74` |
| For `rolled_family_rect_v1`: **`throat_turn_deg_hi < rect_turn_deg_lo`** | `rolled_family.py:328-330` | documented — rect construction `0 < throat_turn_deg < rect_turn_deg < 90` (`_rolled_rect_v1.py:48-49`) |

---

## 2. `_rolled_rect_v1.py` kernel limits

File: `hornlab_search/design/generators/_rolled_rect_v1.py` (last changed `c2c91905`, 2026-11-15).
Rationale: [ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md](../research/typologies/ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md)
§"Original, testable construction" and §"Parameters, starting ranges".

| Law | `file:line` | Rationale |
|---|---|---|
| `width_mm`, `height_mm`, `depth_mm`, `decay`, `wall_thickness_mm` > 0 | `_rolled_rect_v1.py:39-41` | documented — construction study |
| `width_mm > height_mm` | `_rolled_rect_v1.py:42-43` | documented — "Landscape proportions" |
| `depth_h_ratio` ∈ [0.5, 1.2] | `_rolled_rect_v1.py:44-45` | documented — depth-split refined range (study "H / V depth ratio") |
| `rect_exponent` ∈ [2, 16] | `_rolled_rect_v1.py:46-47` | documented — "Rectangular exponent 8–16" (code widens to 2) |
| `0 < throat_turn_deg < rect_turn_deg < 90` | `_rolled_rect_v1.py:48-49` | documented — construction step 2 |
| `terminal_deg` ∈ (180, 280] | `_rolled_rect_v1.py:50-51` | documented — "Terminal contour parameter 240–275" |
| `throat_turn_deg < pucker_start_deg < 180` | `_rolled_rect_v1.py:52-53` | documented — pucker window begins after the throat turn |
| `max(|pucker_h_mm|,|pucker_v_mm|) <= 0.15*depth_mm` | `_rolled_rect_v1.py:54-55` | undocumented (code only, commit `c2c91905`) |
| `n_phi >= 25`, `n_s >= 32`, integers | `_rolled_rect_v1.py:56-58` | undocumented (code only, commit `c2c91905`) |
| `surface_at`: `0 < exit_angle_deg < 45`; `height_mm/2 > exit_radius_mm` | `_rolled_rect_v1.py:61-74` | documented — construction step 2 (round throat) |

The `rolled_family` adapter neutralises the pucker slots (`pucker_*` pinned to 0,
`pucker_start_deg = rect_turn_deg`; `rolled_family.py:44`, `:69`), so the pucker limit applies to
the bare kernel, not the family.

---

## 3. Klangfilm–Lamé inert knobs and limits

Rationale: [docs/knowledge/contracts/klangfilm_lame_hv.md](contracts/klangfilm_lame_hv.md) and
[KLANGFILM_ELLIPSE_HANDOFF_2026-11-16.md](../research/typologies/KLANGFILM_ELLIPSE_HANDOFF_2026-11-16.md).

| Law | `file:line` | Rationale |
|---|---|---|
| **`hv_core` mode `cd_core_blend` must be fixed** (legacy and `hv_core` are incompatible classes) | `klangfilm_lame_hv_core_family.py:168-171` | documented — module docstring "The classes are incompatible" (`_klangfilm_lame_hv_core_v1.py:13-15`) |
| Legacy (`blend 0`): every `CORE_KEYS` key except the blend is inert and pinned | `klangfilm_lame_hv_core_family.py:40-41`, `:172-177` | documented — module docstring; contract §KL-HV-B |
| `hv_core` (`blend 1`): every parent key is inert and pinned | `klangfilm_lame_hv_core_family.py:42`, `:173-177` | documented — "silent no-op genes are exactly what the 2026-11-16 handoff forbids" (`:14-15`) |
| Phase A: blend 0 ⇒ `theta_h0/v0`, `h/v_mid_gain`, `core_join_fraction` inert | `klangfilm_lame_hv_family.py:39-41`, `:165-176` | documented — Phase A docstring ("no knob without a no-op") |
| Phase A: a blend box reaching 0 with a searched Phase-A knob is refused | `klangfilm_lame_hv_family.py:173-176` | documented — same |
| `entry_half_angle_deg` is inert with zero source blend | `klangfilm_lame_family.py:140-142` | documented — `_klangfilm_lame_v1.py:16-17` ("default 0 = OFF ... Not searched") |
| v1 physical bounds (`fc_hz` 150–3000, `aspect` 1–4, `lame_p` 2–8, `end_frac` 0.3–1.9, `rim_sweep_ratio` ±0.6, `morph_frac` 0.05–0.9, `source_blend_ratio` 0–2, `entry_half_angle_deg` 0–20) | `_klangfilm_lame_v1.py:36-38` | undocumented (code only, commit `2c0e2928`) — narrower search boxes live in YAML |
| v1 `wall_thickness_mm > 0`, `n_phi >= 7`, `n_s >= 24` | `_klangfilm_lame_v1.py:50-54` | undocumented (code only, commit `2c0e2928`) |
| Phase A `_CORE_BOUNDS` (`cd_core_blend` 0–1, `theta_*` 0–25, mid gains ±80, join 0.05–0.95) | `_klangfilm_lame_hv_v1.py:67-69` | undocumented (code only, commit `3ef7aee0`) |
| Phase B `_CORE_BOUNDS` (blend 0–1, `theta_*0` 0–25, `theta_*1` 5–60, core 30–480, `lame_p_mouth` 2–8, start/end 0–1, beak setbacks 0–60 / 0–45 / ±20, start 0.50–0.99) | `_klangfilm_lame_hv_core_v1.py:73-81` | undocumented (code only, commit `3ef7aee0`) |
| Phase B `lame_start_frac < lame_end_frac`; every `theta_* < 89°` | `_klangfilm_lame_hv_core_v1.py:107-111` | documented — module docstring ("core stays monotone") |
| `report_only` cannot be combined with a searched bound | `klangfilm_lame_hv_family.py:178-182`; `klangfilm_lame_hv_core_family.py:178-180` | documented — `size_policy` docstring (`klangfilm_lame_hv_family.py:32-36`) |
| Phase A forward invariants: round throat, non-shrinking non-decreasing radii, join inside `(0, z_turn)` | `_klangfilm_lame_hv_v1.py:147-150`, `:169-181` | documented — module docstring |

---

## 4. OSSE throat-coupling locks

File anchor: `hornlab_search/design/throat_hv.py` (shared block), `hornlab_search/design/families.py`
(OSSE validation), and `grid.py` (`osse_rollback` / `rows`). Rationale:
[THROAT_HV_CONTROL_AUDIT_2026-11-18.md](THROAT_HV_CONTROL_AUDIT_2026-11-18.md) row 18,
[KH-003](claims/KH-003_throat_hv_options_literature.md), and
[hornlab-shape-check](../../.claude/skills/hornlab-shape-check/SKILL.md) (lines 37–40).

| Law | `file:line` | Rationale |
|---|---|---|
| **Round coupling: `aspect_ratio: 1` and (R-OSSE) `exponent: 2`** — these reshape the throat itself (e.g. 24×36 mm on a 36 mm driver), so they are *throat locks*, not shape controls | key defs `families.py:65-66`; key semantics `knobs_native.py:279-319`; policy `.claude/skills/hornlab-shape-check/SKILL.md:37-40` | documented — owner rule ("round at the coupling plane is the safe default"), audit row 18. **Not code-enforced**: no validator refuses a non-round coupling; it is a guidance lock |
| **`throat_hv_ratio` couples the two planes**: `rho**(±cos2p/2)` ⇒ `k_H = rho^(1/2)`, `k_V = rho^(-1/2)`; rho = 1 is neutral at every azimuth | `design/throat_hv.py:9-13`, `:30`, `:80-85`; OSSE mapping `families.py:654-666` | documented — KH-003 "a throat-coupling rule, not a [free H/V control]"; audit row 18; FAV split-plane §2 |
| Native OSSE: `throat_hv_ratio` needs a plain numeric `k` (it builds the k(p) expression) | `families.py:642-646` | documented — `throat_hv.py` docstring |
| Native OSSE: `hv_onset_frac`/`section_exp_ramp` are aliases of `morph_fixed`/`morph_rate`; give one, and they need `morph_target` | `families.py:647-651` | documented — alias contract (`throat_hv.py:15-18`) |
| `osse_rollback`: `k_v` (split-plane) and `throat_hv_ratio ≠ 1` are two per-azimuth k laws; use one | `grid.py:2145-2148` | documented — FAV split-plane §5 ("two k laws") |
| `osse_rollback`: `k_v_log` needs `k_v` | `grid.py:2143-2144` | documented — FAV split-plane §6 (SplitCore) |
| `osse_rollback`: `hv_onset_frac`/`section_exp_ramp` need `sf_m` and `sf_amt > 0`; `hv_onset_frac` replaces `sf_start` | `grid.py:2163-2175` | documented — code comment "an inactive conditional knob must not be searched" |
| Shared block ranges: `throat_hv_ratio` [0.25, 4.0], `hv_onset_frac` [0, 0.9], `section_exp_ramp` [0.5, 8] | `design/throat_hv.py:30-32` | undocumented (code only, commit `c9423c81`) — child of KH-002/KH-003 research |

**`r_lip_mm` (rows, including `osse_rollback`):** the code bound is **0–100 mm**
(`grid.py:172`, `:1085-1093`), documented in
[crowe_v2a_and_crowe_x_osse.md](contracts/crowe_v2a_and_crowe_x_osse.md) ("Module cap
`ROWS_MAX_R_LIP_MM=100`"). The narrower **0–2.1 mm** figure in the 2026-11-25 handoff is a
*probe-observed* geometry limit at the 80×50 open-115 Le Cleac'h/bake cohort, recorded only as an
evidence comment — `docs/evidence/cd_bo_cohort_2026-11-25/build_v4.py:55` ("r_lip legal only
0-2.1 mm here (probe)"). It is **undocumented (evidence only)**: no code bound of 2.1 mm exists.

---

## 5. CD backbone limits

File: `hornlab_search/design/generators/_cd_backbone_v1.py` (last changed `4be90852`, 2026-11-25).
Rationale: [RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md](../research/typologies/RETURNED_LIP_CD_BACKBONE_RESEARCH_2026-11-25.md),
§3(d) "Knobs and ranges (first pass)" and §3(a) construction math.

| Law | `file:line` | Rationale |
|---|---|---|
| `bb_h`, `bb_v` ∈ [0, 1] | `_cd_backbone_v1.py:32` | documented in principle — dossier §3(d) gives `lam_H` 0–1 but `lam_V` **0–0.5**; code allows 1 (see discrepancy below) |
| `bb_throat_frac` ∈ [0.05, 0.30] | `_cd_backbone_v1.py:33` | partly documented — dossier §3(d) first pass is 0.10–0.20; code is wider |
| `bb_rollin_frac` ∈ [0.15, 0.45] | `_cd_backbone_v1.py:33` | partly documented — dossier first pass is 0.25–0.35; code is wider |
| `bb_throat_frac + bb_rollin_frac <= 0.80` (`MAX_BODY_SUM`) | `_cd_backbone_v1.py:34`, `:55-56` | undocumented (code only, commit `4be90852`) |
| Neutral rule: both amplitudes 0 ⇒ parent object unchanged | `_cd_backbone_v1.py:59-60`; `cd_backbone_family.py:132-133`; `cd_backbone_rows_family.py:14-17`, `:152-153` | documented — dossier §3(a) "lam = 0 returns the row unchanged" |
| Monotone pre-roll, no constriction, no axis crossing, forward station fixed | `_cd_backbone_v1.py:130-149` | documented — dossier §3(a) checkable properties and §4 validation ladder |
| Backbone law at every searched endpoint | `cd_backbone_family.py:197-209`; `cd_backbone_rows_family.py:180-192` | documented — research economy: a box is not a feasibility proof |
| Shape dormancy (a searched throat/roll-in needs a strength box away from 0) | `cd_backbone_family.py:210-213`; `cd_backbone_rows_family.py:193-196` | documented — dossier §3(d) "theta_c is solved, not searched" logic |
| Quarter symmetry only | `cd_backbone_family.py:103-104`; `cd_backbone_rows_family.py:68-69` | documented — parent families are quarter |
| `rows_bb_v1` parents limited to `lecleach`, `lecleach_ar`, `iwata_ar`, `salmon_elliptical`, `lecleach_mod`, `toroidal_rollback` | `cd_backbone_rows_family.py:33-35` | documented — dossier §5 table |
| `rows_bb_v1` is a labelled CD hybrid; never the parent typology | `cd_backbone_rows_family.py:5-12`, `:36-37` | documented — knowledge-card rule; dossier §5 |

---

## 6. Rim beak limits

File: `hornlab_search/design/generators/_rim_beak_v1.py` (last changed `bee579a2`, 2026-11-25) and
`rim_beak_family.py`. Rationale: the kernel docstring (`_rim_beak_v1.py:1-17`) and
[FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md](../research/typologies/FAV_SPLIT_PLANE_PROPOSALS_2026-11-20.md)
§8 (the `osse_rollback` beak prototype). No acoustic evidence exists.

| Law | `file:line` | Rationale |
|---|---|---|
| `rb_h_mm`, `rb_v_mm` ∈ [-60, 60] | `_rim_beak_v1.py:27` | undocumented (code only, commit `bee579a2`) — labelled hypothesis |
| `rb_d_mm` ∈ [-30, 30] | `_rim_beak_v1.py:27-28` | undocumented (code only, commit `bee579a2`) |
| `rb_start_frac` ∈ [0.30, 0.90] | `_rim_beak_v1.py:28` | undocumented (code only, commit `bee579a2`) |
| Neutral: all three amplitudes 0 ⇒ parent object unchanged | `_rim_beak_v1.py:49-50`; `rim_beak_family.py:121-122` | documented — kernel docstring "All amplitudes zero returns the input array unchanged" |
| Pre-roll must advance; forward station must not move; finite output | `_rim_beak_v1.py:73-85`, `:88-89` | documented — kernel docstring ("Refused: a pre-roll that stops advancing axially, a forward station that moves, nonfinite output") |
| `rb_start_frac` dormant when every amplitude is pinned at zero | `rim_beak_family.py:183-184` | undocumented (code only, commit `bee579a2`) |
| Backbone parent required (`rows_bb_v1` or `rolled_family_rect_bb_v1`); quarter only | `rim_beak_family.py:30`, `:77-81` | documented — family docstring ("Parents: rows_bb_v1 ... and rolled_family_rect_bb_v1") |

---

## 7. Cross-family invariants

| Invariant | Where | Rationale |
|---|---|---|
| Quarter model for the newer adapted families | `rolled_family.py:92`; `klangfilm_lame_family.py:64`; `klangfilm_lame_hv_family.py:76`; `klangfilm_lame_hv_core_family.py:78`; `cd_backbone_family.py:103`; `cd_backbone_rows_family.py:68`; `rim_beak_family.py:77` | documented per family |
| Round driver at the coupling plane | rolled `:180-193`; Klangfilm `_klangfilm_lame_v1.py:131`; Crowe V2A `crowe_hv_area_aspect_v1.py:27` (`A(0)=pi r0^2`) and `:348` (`exponent: 2.0` at the throat station); OSSE lock §4 above | mixed: code (rolled/Klangfilm/Crowe) + documented policy (OSSE) |
| Envelope check on the actual shell extents | `rolled_family.py:253-258`; `klangfilm_lame_family.py:100-105`; `klangfilm_lame_hv_family.py:119-125`; `cd_backbone_family.py:156-163`; `rim_beak_family.py:139-140` | documented — handoff + brief envelope policy |
| `size_policy: report_only` is diagnostics only; cannot be searched | `klangfilm_lame_hv_family.py:178-182`; `klangfilm_lame_hv_core_family.py:178-180`; sculpted is fixed `report_only` (`sculpted_rosse_family.py:40-42`) | documented — each module's `size_policy` docstring |
| Editing any digest-bound file orphans saved recipes | `rolled_family.py:32-39`; `klangfilm_lame_family.py:36-43`; `klangfilm_lame_hv_family.py:47-55`; `klangfilm_lame_hv_core_family.py:49-57`; `sculpted_rosse_family.py:26-34`; `cd_backbone_family.py:50-59`; `cd_backbone_rows_family.py:47-61`; `rim_beak_family.py:41-48` | documented — handoff §1 lesson 3; `hornlab-generator-family` skill (W5) |

`osse_rollback` is the exception: it lives inside the shared `grid.py` with no separate
`implementation_digest()` (see [favl_canonical.md](typologies/favl_canonical.md)).
