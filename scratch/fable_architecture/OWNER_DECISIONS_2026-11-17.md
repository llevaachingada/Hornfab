# OWNER_DECISIONS — decision menu prepared for the owner

> **AUTHOR AND STATUS — READ FIRST.** Prepared by the **lower-cost continuation lane agent** —
> **not by Fable (the senior/high-thinking reviewer) and not by the owner** — as an options menu.
> **No recommendation is made on C1–C4**, per the owner's instruction; each option carries its
> evidence and nothing else. Section-B solve counts are estimates carried from
> `LOW_COST_AGENT_HANDOFF.md` §6 and `VALIDATION_EXPERIMENTS.md`; **nothing here approves or runs a
> solve**. The two no-solve items are **proposals**, not decisions. Every decision here remains
> open until the owner (and, for the generator direction and the staged plan, the senior reviewer)
> takes it.

> **SENIOR ADDENDUM (2026-11-17).** `FABLE_SENIOR_REVIEW_2026-11-17.md` §2 C-1 corrects the C1
> framing below: the low-band vertical shortfall is measured on sampled designs, and the Keele
> relation is a scoped Bi-Radial heuristic (`docs/knowledge/claims/KH-001_keele_mouth_heuristic.md`),
> so "the physics argument" should read "a heuristic consistent with the measurement". §4 of that
> file repackages C1-C6 with what each choice changes in the plan and adds recommendations for the
> no-solve items and the solve order (C1-C4 still carry no recommendation).

## C1 — Coverage target: point or corridor?

| Option | What it means | Evidence for and against |
|---|---|---|
| **Point 80×50** (today's v7 target) | `cov` measures `bw(f)−80` and `bw(f)−50` at every scored frequency | Current production objective. Against: the 80×50 point is partly unreachable in the 600×480 envelope — V beamwidth at 700–1,100 Hz never drops below 66° (`FABLE_DISCOVERY.md` F2); `OPTIMIZATION_AND_BRIEF_AUDIT.md` shows v7 scores that unreachable point at every frequency, so the term penalizes all designs; `A9` shows the point target picks a different leading family than the corridor |
| **Corridor H 60–90° / V 40–60°, onset 700 Hz** | Any level inside the range is acceptable; hard edges penalize outside | `A9`: corridor coverage changes which family leads (`ext_throat_hvlaw` 1st → 4th; `osse_rrect_fold_warm` leads) and cuts the ripple term to ~3 % of its point-mode value — that last fact is a design consequence to weigh, not a defect. `R3`: onset 700/1,000/1,250 is insensitive in the top-20 selection |
| **Corridor, onset 1,000 Hz** | Vertical scoring starts at 1 kHz | Same evidence as above; matches the Keele aperture heuristic (~1 kHz for 480 mm height at 50°) — the physics argument for not demanding 50° at 700 Hz |
| **Corridor, onset 1,250 Hz** | Later vertical onset | `R3` shows it changes little (top-20 identical across onsets) |

Also open within C1: whether the deliverable counts coverage at the low-frequency end at all, and
whether H and V use the same band definition.

## C2 — "Constant": what functional?

| Option | Definition | Evidence |
|---|---|---|
| **Strict level constancy** | `cost = mean over f of (bw(f) − c*)²/100`, `c*` = own mean clamped into the corridor | `SCORING_RANGE_PROPOSAL.md` formula; `S1`: strict vs slope-limited top-20 overlap 18/20 — the choice barely changes rankings |
| **Slope-limited constancy** | Fit a line in log-frequency, slope clipped (±5 deg/decade), intercept clamped into the corridor | Same S1 evidence; allows a gentle steady narrowing if the owner wants that look |
| **No constancy term** | v9 corridor only | Simpler; but `SCORING_RANGE_PROPOSAL.md` documents 129 designs swinging >10° and 38 >15° inside the range — the variation the term exists to penalize |

## C3 — Free-limit dead bands (which terms stop counting below a threshold)

Placeholder limits used in S1 (not approved): ripple 1.0 dB, DI roughness 0.5 dB, on-axis flatness
1.0 dB, DI slope 0 to +3 dB/decade; H 60–80° / V 40–60° handled by the corridor. Options: adopt the
placeholders; adjust per term; or none. Consideration from `SCORING_RANGE_PROPOSAL.md` L123–131:
all-range scoring can flatten the objective surface — keeping **ripple and constancy as true
less-is-better terms** avoids a plateau; dead-banding everything risks it.

## C4 — Deliverable: one winner or a menu?

| Option | Consequence |
|---|---|
| **One winner** | Single campaign target; simpler scoring |
| **Short menu** | Fits the corridor design (a horn may sit anywhere in the range) and the Pareto reading of trade-offs (`OPTIMIZER_AND_SWITCH_SECTION.md`: the Pareto frontier is a menu of physical trade-offs, not an acoustic optimum) |

## C5 — Protected families

`A11_PROTECTED_AND_LINEAGE.md` (lower-cost lane measurement) lists 21 lanes: **17 carry
owner-request evidence** (4 of them family-level only: rolled ES spiral, section-axial-home,
Crowe-X square, Crowe-X OSSE CD), **4 have no request found** — `hl__ext_throat_hvlaw_v7/v8` and
`hl__osse_rrect_morph_v7/v8` carry owner *drop* evidence rather than requests; `sp__*` (section
pucker pilot) and `rf__rect_radial_wide_v7` have none found. Owner action: confirm or correct the
table; note the Klangfilm H/V row rests on a session note plus the owner-supplied calculator, not a
quoted file line.

## C6 — Budget for section B (proposals; nothing run)

| Item | Solves | Decides | Status |
|---|---|---|---|
| B1 mesh fidelity at the top | 20 | Whether rankings at the top are trustworthy (R1 has only 2 low-J pairs) | Proposed |
| B2 U3 structural freedoms as per-lane variants | 12–16 | Whether the freedoms move the beam (≥3° intended-plane rule predeclared) | Proposed; CPU validity stage precedes |
| B6 matched-budget lane reruns under the new scoring | owner's choice | Fair family comparison (R4 spread ≈ 0.57 of config gaps; the BO-vs-CMA record is unequal-information) | Proposed |
| B4 predictor on an unbiased pool | 40 | Whether hooks B/C are worth wiring | Optional; only after B1/B2/B6 if the model layer is still wanted |
| B3 U2 paths | 22 | — | **Withdrawn** (U2 closed by the U1 verdict) |
| B5 backbone confirmation | 4 | — | **Withdrawn** (moot unless the optional U1-bis falsification test passes) |

## Two no-solve decisions (proposals)

1. **Provenance digest rule.** Require `implementation_sha256` on every recipe, split
   kernel-vs-validator (or hash the generated point grid). Demonstrated need: Klangfilm
   `e3a1f4a3…` (72 designs unrebuildable), lecleach (`d6c9abd`, no digest), ROSSE (`a10e784`
   validator-only change locked 11 designs out of their own adapter until bypassed in memory).
2. **Envelope convention.** Define the brief envelope against the **mesh-built inner-sheet box**
   (what stored `bbox_m` equals in 70/70 measured records) and keep the generator's outward
   `outer_points` array as a trim envelope; or define it against the outer shell and accept that
   sampled and meshed boxes will differ by 1.9–3.5 mm on biradial-like lanes.

## Stage-0 code truths (owner's lane; nothing implemented by this agent)

Post-mesh envelope violations coded as `invalid_geometry` and the `invalid_envelope` prefix
mapping bug; `search.links` refuses generator-block families (the cheap coupling fix is blocked by
code); conservative GRID extent with realised false refusals unmeasured; v4-only cohort gate vs
production v7; `flat` ddof=2 vs `flat_cv` ddof=0 undocumented; `mode` enclosure-overwrite hazard;
`budget_counts` doc/code mismatch; night-runner restart idempotency (finished jobs can re-run) and
watchdog `best_J: null` in all 38 stops (recompute from `search.ndjson`).
