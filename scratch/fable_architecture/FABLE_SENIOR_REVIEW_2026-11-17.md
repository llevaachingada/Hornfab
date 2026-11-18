# FABLE_SENIOR_REVIEW_2026-11-17 - senior verdict on the lane review, and the reserved decisions

> **AUTHOR AND STATUS.** Written by the **senior (high-thinking) reviewer pass**, picking up for
> Fable as handoff §8 and the N4 rule require. Not written by the owner. Repository HEAD at
> review: `1d6ebc8` (branch `ccr-260b4b76-fi6b8j`, equal to `origin/main`). Read-only with respect
> to code, configs, queues, `runs/` and `examples/`: no solve, no mesh build, no pytest, no
> process control. This document **takes the decisions reserved to the senior reviewer**
> (generator direction, search design, the staged plan) and **packages the owner's decisions**;
> it does not take owner decisions. No pass line, threshold, split, frozen contract or brief is
> changed. The architecture and staged plan that follow from these decisions are in
> `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md`.
>
> **Precedence from now on:** this file, then `ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md`, then
> `LOW_COST_AGENT_HANDOFF.md`, then the chain the handoff lists. Result files (R, S, E, X, N, A, P,
> U) still outrank every position document on matters of fact.

Evidence labels: **[measured]** a result file or run artifact; **[verified]** read in code at
`1d6ebc8`; **[inferred]** senior reasoning; **[owner]** an owner statement found in the repo.

---

## 0. Bottom line

1. **The lane review is confirmed in substance.** Its subtraction is right: the unified backbone,
   the response-model spine, construct-then-correct, frequency staging, lane racing and the
   predictor hooks all failed their own predeclared lines. What survives is the canonical record
   (as a measurement and history layer) and the scoring change.
2. **Generator decision (reserved, now taken): plural generators, one description.** No unified
   backbone and no new common carrier. The specialist generators stay the only things that make
   horns. The canonical surface record is the single shared *description* used to compare,
   gate, rebuild and test them.
3. **New shape freedoms are tested before anyone builds them.** The U3 freedoms are first
   measured as edits to the canonical record of a good design, meshed through the existing
   point-grid route. Only a freedom that clears the predeclared ≥3° authority rule gets built,
   and it is built *inside the specialist whose construction carries it* (the Klangfilm H/V core
   is the template), not as a module bolted onto every family.
4. **Search stays inside lanes.** CMA-ES builds rows, BoTorch works within a lane once it has
   them, history seeds new runs. No cross-family model, no automatic policy switching.
5. **Five corrections to the record** (§2), two of which change how the owner's scoring decision
   is framed: "80×50 is physically unreachable" is a measured observation on sampled designs, not
   physics; and constancy is a declared constant-directivity intent that must never be applied to
   a lane by family name.
6. **The whole validation programme costs about 35-40 GPU solves plus the owner's matched reruns.**
   That is less than one overnight optimizer arm. Stage 0 needs no GPU and no owner decision.

---

## 1. Verdict on the lane review, item by item

| # | Lane review position (`LANE_REVIEW_FOR_FABLE_2026-11-17.md`) | Senior verdict | Why |
|---|---|---|---|
| 1 | Unified layered backbone falsified at its own gate (U1: 0/5 ≤ 0.5 mm, 5/5 > 2 mm) | **Confirm, with scope** | `U1_LAYERED_REPRODUCTION.md` [measured]. What failed is the *compact common carrier* (3 ribs, one superellipse exponent, parametric depth; ψ splines worse). What passed is the *dense record* (65×61, `X1B_CONTRACT_V2.md`). The history-bridge role therefore belongs to the record, and the unification argument is gone |
| 2 | Response-model spine not supported at full J | **Confirm** | `E1_FOLLOWUP_WHOLE_SURFACE.md`: score 18.5, curve head 24.0, term head 18.25 reveals; Parts A/B/C fail |
| 3 | Construct-then-correct closed | **Confirm, scoped** | `E2_INVERTIBILITY.md`: closed for historical-geometry recovery in the two-profile description. Physical response correction is untested and not worth a test now |
| 4 | Frequency staging, lane racing not demonstrated | **Confirm** | `E3_FREQUENCY_STAGING.md` (0.124 %), `X5_ALLOCATION.md` (degenerate replay; halving drops a protected family 20/20) |
| 5 | Predictor hooks A/B/C fail; 0 strict unbiased designs anywhere | **Confirm the verdict, amend the scope** | `P1_PREDICTOR_REPLAY.md` [measured] on 8 home-brief BoTorch study lanes. "Anywhere" is too broad: the 2026-10 atlas cohorts (722-1,726 attempts per run, `docs/CONTINUITY.md` 02:5x correction) were not checked. This does not reopen the predictor; it corrects the claim |
| 6 | Canonical record validated | **Confirm, and rule on X1 bookkeeping** | X1 is **accepted for geometry** (T1, T2 under v2, T5 pass on six lanes; 55/55 in `X4_COMPLETION.md`) and **open for metadata** (T4 cannot complete because fields exist in no recipe). T4 becomes a stage-0 schema work item, not a reason to doubt the record |
| 7 | Scoring (ranges plus constancy) is the best-supported change | **Confirm, amend two framings** | See §2 C-1 and C-2. Also: the noise floor depends on the score identity and frequency count (C-3), so "below ~0.13 J is not a decision" holds only for v9 at 18 solved frequencies |
| 8 | Generator fallback: U3 freedoms as per-lane modules on existing families | **Amend** | Test before build (decision SD-2). Building modules on every family before knowing which freedom moves the beam repeats the Stage A mistake (additive Klangfilm changes moved ≤ 2.74°) |
| 9 | Optional U1-bis falsification test before solve money | **Overrule (defer)** | Its payoff has shrunk: the reasons to unify (one model over one space, cross-family transfer) are already dead. A richer section law fitted after seeing failure is a curve fit unless the parameter count is capped in advance. Reopen condition in SD-3 |
| 10 | U2 closed; B3 and B5 withdrawn | **Confirm** | No unified space exists to traverse |
| 11 | Do not wire any predictor hook | **Confirm** | P1, X3 (`X3_REMAINING.md`: prior worth about 8 local solves; transfer decays .695 → .575) |
| 12 | Watchdog stays a reviewed safety net; no automatic switching | **Confirm** | `WATCHDOG_REPLAY.md` (would have stopped the winning run at attempt 25), `SWITCH_ADMISSION_MATRIX.md` |
| 13 | Stage-0 truth fixes list | **Confirm, all still live at HEAD** | Re-read at `1d6ebc8` [verified]: `search/evaluate.py:1562` prefix test still `startswith("invalid_envelope")`; `search/links.py:36-37` still raises for a generator block; `bo/cohort.py:96` still `!= 4`; `grid.envelope_extents` (`grid.py:2989`) still conservative max-radius; `objective/replay.py:140` dispatches only up to v7 and regenerates metrics with plain `compute_metrics` (`:694`), the DI parity hazard |
| 14 | Process-integrity register | **Confirm and adopt** | This file is the single supersession note for the briefs it overtakes (§5) |
| 15 | Staging outline (stages 0-8) | **Adopt with changes** | Reordered and made gate-driven in the plan document: the record-route equivalence check is new, B1 is decoupled from the owner's scoring choice, and stage 4 is "test then build" |

---

## 2. Corrections to the record

**C-1. "The 80×50 point is partly unreachable in 600×480: a physics fact" is overstated.**
What is measured: in every sampled v7 home-landscape design, vertical beamwidth at 700-1,100 Hz
stayed at or above 66° against the 50° target (`FABLE_DISCOVERY.md` F2, `OPTIMIZATION_AND_BRIEF_AUDIT.md`).
What is not established: that no design in the envelope can do better. The Keele mouth relation
is a scoped Bi-Radial sizing heuristic, not a universal limit (`docs/knowledge/claims/KH-001_keele_mouth_heuristic.md`);
`SCORING_RANGE_PROPOSAL.md` §8 and handoff §5 already say the same. The consequence for scoring is
unchanged: a point target there charges every sampled design a near-constant cost that does not
discriminate between them. But the owner's C1 choice should be framed as "what do you want to
pay for", not "what physics allows". The Klangfilm Phase B arms reached about 103-110° V at
700-1,200 Hz from 143° (`docs/evidence/klangfilm_hv_2026-11-16/AB_REPORT_B.md`), which shows the
low band does move with construction; it does not show 50° is reachable.

**C-2. Constancy is a declared constant-directivity intent, never a family default.**
The owner locked "no classification by family name" for v9
(`docs/research/typologies/NON_CD_OBJECTIVE_PROFILE_RFC_2026-11-16.md`, Amendment A) [owner]. A
strict constancy term is a CD priority; the knowledge hub forbids silently imposing CD scoring on
intentionally non-CD horns (Klangfilm, Le Cléac'h, rolled forms on the smooth brief). So:
constancy is something a **brief declares** (strict, slope-limited, or absent), absent by
default. S1 applied strict constancy to the smooth-brief cohort too; that was a placeholder
replay, not a design to carry forward.

**C-3. The noise floor belongs to a score identity and a frequency count.**
`N3_GRID_INDEPENDENCE_V9.md` [measured]: residual from 18 versus 29 solved frequencies is sd 0.113
J at the top for v9, but **0.205** for v9 plus strict constancy, and v9 plus constancy needs 116
dense scoring points where v9 alone converges at 58. Constancy is about 55 % of the augmented
score. Any "differences below X are ties" rule must name the identity it applies to.

**C-4. Missing evidence: the corpus never absorbed the Klangfilm Phase B result.**
Stage A (throat offsets, additive) moved the beam ≤ 2.74°. Phase B (the H/V monotone *core*, a
construction-level change) moved mean -6 dB beamwidth by 25-40° V and up to 34° H in at least one
band on all four arms (`AB_REPORT_B.md`, axis-authority table) [measured]; all four still failed
that report's own optimisation gate, and the follow-up `b3_soft` search went from its seed J 6.401
to 2.819 once σ0 and bounds were fixed (`docs/CONTINUITY.md`, 2026-11-17 latest) [measured].
Phase B replaced the whole core law, so it is an existence proof, not a single-freedom authority
test like U3. It is still the strongest evidence in the repo on the geometry question: **freedoms
that matter live in the construction, not in add-on deformations.** It supports SD-2.

**C-5. Four reports the handoff cites are not in the repository.**
`A4_GRID_INDEPENDENT_SCORE.md`, `A5_SOLVER_CALL_TIMING.md`, `A9_CORRIDOR_VS_TERM_SET.md` and
`X1_ADDENDUM_KLANGFILM_PROVENANCE.md` (and the `.a4/`, `.a9/` script folders) are absent from every
commit on `origin/main` [verified, `git log --all`]. Their headlines survive only in
`LOW_COST_AGENT_HANDOFF.md` §10. They are probably untracked on the Windows checkout. **Owner
action:** commit them, or the A4/A9 numbers this review relies on stay unreproducible from git.

---

## 3. The reserved decisions (taken)

### SD-1. Generator direction: plural generators, one description

- **Decision.** No unified backbone, no common carrier, no "master family". The existing
  specialist constructions (OSSE, R-OSSE, ICW, FREEFORM, the point-grid/rows builders, the Crowe,
  Klangfilm and Le Cléac'h families, CAD) remain the only generators.
- **The canonical surface record (contract v2) is the single shared description.** It is what
  every non-CAD design can be turned into without meshing, what the envelope and validity gate
  reads, what history rebuilds are checked against, and what new freedoms are prototyped on.
- **Why.** U1 [measured] falsified the compact carrier at its own predeclared line; the dense
  record passed. `UNIVERSAL_HORN_FAMILY.md` §7 predeclared this exact outcome: "the backbone
  becomes a new family beside the others and loses the argument about history and unification."
  Its other two reasons (one model over one space; families connected) depended on results that
  also failed (E1, X3, P1) or cannot now run (U2).
- **What this does not say.** It does not say a layered law is useless inside one family. Crowe's
  area/aspect/section generator and the Klangfilm H/V core are layered constructions, and they are
  where the measured authority came from (C-4).

### SD-2. New freedoms: test on the record first, then build inside one specialist

- **Decision.** The four U3 freedom types (vertical flare timing, termination split, section
  steering, diagonal pull) are first built as **record-space edits** (a displacement field on
  (s, φ), contract §10) of one good design, meshed through the existing point-grid route
  (`hornlab_mesher.geometry.PointGridHornGeometry`, `mesh/grid_build.py`), and solved in a paired
  control-versus-variant test (B2). The predeclared U3 rule applies unchanged: a freedom has
  authority if it moves the intended plane's mean beamwidth by ≥ 3° in one of the bands 0.7-1.1,
  1.1-2.5, 2.5-5.5 kHz while the other plane moves less than half as much.
- **New precondition (record-route equivalence).** Before any variant is read, the *unmodified*
  record of the host design is meshed and solved through the point-grid route and compared with
  the host's stored response. If the record route does not reproduce the original (predeclared:
  mean beamwidth within 1° per band in both planes and ΔJ within the stage-2 noise floor), the
  variant results are not interpretable and B2 stops. This is also the first acoustic check the
  canonical record has ever had; X1 was geometry only.
- **Host design.** The U3 brief predeclared the best `hl__ext_throat_hvlaw_v7` design. That lane
  carries owner *drop* evidence (`A11_PROTECTED_AND_LINEAGE.md`), but U3 uses it as a test
  article, not as a lane to continue, and its record is the cleanest measured (p99 0.108 mm). The
  CPU stage also builds the variants on the best `hl__biradial_es_style_v7` design (owner
  requested, p99 0.101 mm) and the owner picks the solved host with both validity tables in hand.
- **Building a freedom that passes.** It goes into the specialist generator whose own coordinates
  express it, as a new knob behind a new config version, after the `hornlab-typology-research`
  gate (CLAUDE.md "Research grounding"). Never retrofitted onto stored designs. A freedom that
  fails is recorded as inert for that host and envelope.
- **If all four are inert.** That is `UNIVERSAL_HORN_FAMILY.md` §7's third bullet: the binding
  limit in this envelope is size and diffraction, not vocabulary. It would move effort from
  geometry to the owner's envelope and intent decisions.

### SD-3. U1-bis is deferred, with a reopen condition

Reopen only if B2 shows at least two freedoms with authority **and** implementing them family by
family would cost more than a shared carrier. If reopened: predeclare the parameter cap (≤ 14
dimensions, `UNIVERSAL_HORN_FAMILY.md` §2.5's own claim), keep the 0.5 mm worst-point line on the
same five lanes, and treat failure as permanent.

### SD-4. U2 is closed; B3 and B5 are withdrawn

### SD-5. Model layer: none beyond BoTorch within a lane

No cross-family predictor, no response-curve spine, no lane-ordering model. History enters a new
run as a seed (already standard: 16 of 75 runs, `A11_PROTECTED_AND_LINEAGE.md`) and as BoTorch
training rows within its own lane once rescored under the run's score identity. Reopen only if an
unbiased pool exists (B4, or a check of the atlas cohorts) **and** a section-aware descriptor
lifts held-out-engine H-plane skill above 0.6 (`X3_REMAINING.md`).

### SD-6. Supervision: safety net only

The watchdog stays a human-reviewed signal. No automatic change of policy, brief, envelope,
objective, fidelity or bounds (ADR D6, still valid). Rules in noise units become admissible only
after stage 2 publishes a floor for the identity in use (ADR D9). Protected families are never
stopped or cut by automation (ADR D10).

### SD-7. B1 is decoupled from the owner's scoring choice

B1 (mesh fidelity at the top) selects the ten designs as the union of the top five under stored
v7 and the top five under the v9 corridor placeholder, deduplicated and topped up from v7. The
solves store full responses, so any score chosen later is free to apply. B1 can run whenever the
GPU is free, without waiting for C1-C4.

### SD-8. The staged plan is written

`ARCHITECTURE_AND_STAGED_PLAN_2026-11-17.md`. It replaces the outline in handoff §7 and the lane
review's §6.

---

## 4. Owner decisions, packaged

Per the owner's standing instruction (recorded in `OWNER_DECISIONS_2026-11-17.md`), **no
recommendation is made on C1-C4**; each card says what the choice changes. The no-solve items and
the budget order carry a recommendation, because they are engineering choices.

### 4.1 Scoring intent for the home brief (C1-C4): what each choice changes

| Decision | Options | What it changes in the plan | Blocks |
|---|---|---|---|
| **C1 Coverage target** | (a) keep v7 point 80×50; (b) v9 `mode: target` (point, per-frequency, already registered); (c) v9 `mode: corridor`, H 60-90 / V 40-60 (brief comment) or narrower; V onset 700, 1,000 or 1,250 Hz | (a): no stage-1 brief work; rankings stay as today. (b)/(c): a new home brief file per choice; history rescored for free. `A9` [handoff §10 only, C-5]: the corridor, not the term set, changes which family leads | Stage 1 brief values, stage 6 lane comparison |
| **C2 Constancy** | strict level; slope-limited (needs a slope bound); none | Strict or slope-limited: a new opt-in term (WP 1.1) and 116 dense scoring points instead of 58 (C-3); none: v9 as registered. S1: strict and slope-limited share 18/20 top designs | WP 1.1, noise-floor identity |
| **C3 Dead bands** | adopt S1 placeholders; set per term; none | Changes term tolerances in the new brief only. Keep at least ripple and constancy as true less-is-better terms or the objective can go flat (`SCORING_RANGE_PROPOSAL.md` L123-131) | Stage 1 brief values |
| **C3b Ripple window** (handoff §10) | listening window; corridor width (v9 default) | v9 corridor ripple uses the corridor width; S1 used 20°. Changes the secondary-term ranking within a family | Stage 1 brief values |
| **C4 Deliverable** | one winner; short menu | Winner: one verified finalist per campaign. Menu: a finalist set spread across the corridor and size, each verified; the report layer (WP 7.4) builds it | Stage 7 report format |

**Framing note for C1 (from C-1):** the low-band vertical shortfall is measured on sampled designs,
not proven physics. A corridor or a later V onset changes what the score pays for; it does not
assert the 50° target is impossible.

**Framing note for C2 (from C-2):** whichever choice is made applies to briefs that declare CD
intent. The smooth / non-CD briefs keep their own declaration; constancy is never inferred from
a family.

### 4.2 Decisions with a recommendation

| Decision | Recommendation | Reason |
|---|---|---|
| **Provenance rule** (no solve) | Gate rebuilds on the **geometry**, not the code: store `kernel_sha256` (informational) and a **record digest** of the generated surface at a fixed sampling; a rebuild passes if the regenerated record matches within 1e-6 mm (digest equality is the fast path). Required on every new recipe; legacy recipes get a one-time backfill where they rebuild | ROSSE (`a10e784`): a validator-only change locked 11 good designs out under a code-hash gate. Lecleach (`d6c9abd`) and the Klangfilm `e3a1f4a3…` set changed geometry with no digest to catch it. An output check catches both and ignores harmless code edits |
| **Envelope convention** (no solve) | Record **both** boxes on every design: the acoustic box (what is meshed and stored as `bbox_m`, inner sheet plus rear closure) and the build box (acoustic box plus declared wall/shell). The brief names which one its 600×480×480 gate applies to | 0 of 309 stored biradial designs sit within 3.5 mm of the limit (`X1B_CONTRACT_V2.md`), so this is a definition to settle, not a performance lever. The physical product is the build box; the solver identity is the acoustic box |
| **C5 Protected list** | Confirm `A11_PROTECTED_AND_LINEAGE.md`'s 17 lanes; decide the 4 "no evidence" lanes explicitly (2 carry drop evidence) | Automation needs a data file, not prose (WP 7.2) |
| **C6 Solve budget, in this order** | (1) B1, 20 solves; (2) record-route equivalence, 2 solves; (3) B2, 12-16 solves on one host; (4) B6, owner's choice, after the stage-1 brief exists; B4 not now | Each step makes the next one interpretable: B1 sets the mesh part of the floor, the equivalence check validates the record route, B2 then measures freedoms on a trusted route. Total about 34-38 solves plus B6 |
| **Commit the missing reports** (C-5) | Commit A4, A5, A9, X1 addendum and their script folders from the Windows checkout | Reproducibility of numbers the plan uses |
| **Preflight σ0 gate** (already open in `NOTES_FOR_SENIOR.md`) | Make the σ0/bound-width preflight a warning by default and `--strict` for unattended nights | The `b3_soft` A/B (45 evals, zero gain at σ0 0.25; 6.40 → 2.82 at σ0 0.10 with seed-centred bounds) is the largest measured search-economy effect in the repo |

---

## 5. Supersession register (the single note for overtaken briefs and positions)

| Document | Section | Status after this review |
|---|---|---|
| `UNIVERSAL_HORN_FAMILY.md` | §7 choice D (layered backbone) | **Superseded** by SD-1. §2 (layers, wall angle) remains useful vocabulary for within-family constructions |
| `VALIDATION_EXPERIMENTS.md` | U1 | Complete, failed (5 lanes, 65×61; lane note records the 4-lane/65×31 drift) |
| `VALIDATION_EXPERIMENTS.md` | U2 | **Closed** (SD-4) |
| `VALIDATION_EXPERIMENTS.md` | U3 | **Re-based** by SD-2: record-space edits, record-route equivalence precondition, two candidate hosts, owner picks one |
| `ARCHITECTURE_DECISION_RECORD.md` | §1, §3, §6 | Superseded. D1-D10 in §2 remain valid (D4 "surrogates model response curves" is moot: no surrogate is built) |
| `ARCHITECTURE_SYNTHESIS.md` | response spine, construct-then-correct, staging | Superseded (E1, A3, E2, E3) |
| `PREDICTOR_AND_WORKFLOW.md` | all hooks | Parked (SD-5) |
| `LOW_COST_AGENT_HANDOFF.md` | §1 "current position" items 1 and 3; §7 outline | Superseded by SD-1, SD-5 and the plan document. §2 rules stay binding for scratch research |
| `LANE_REVIEW_FOR_FABLE_2026-11-17.md` | §2.1, §6 | Amended per §1 rows 8, 9, 15 |
| `OWNER_DECISIONS_2026-11-17.md` | C1 "physics argument" wording | Corrected by C-1 |
| `X1_ACCEPTANCE_TABLE.md` | verdict | Ruled: accepted for geometry, open for metadata (§1 row 6) |

---

## 6. Kill, keep, park

**Killed (do not reopen without new evidence):** compact unified backbone as the generator;
response-curve spine; construct-then-correct; frequency staging as a compute saver; lane racing
and halving; predictor hooks A-C; additive deformation modules as the composability route; the
"8 modes ≈ 1.2 mm whole surface" reading.

**Kept and built:** specialist generators; canonical record v2 as the shared description;
versioned, brief-declared scoring (v9 plus an opt-in constancy term if C2 wants one); dense-grid
score identity; published noise floor per identity; fidelity ladder; BoTorch within lanes with
CMA-ES building rows; seeding from stored bests; watchdog as safety net; protected list as data;
provenance by geometry digest.

**Parked with reopen conditions:** U1-bis (SD-3); predictor (SD-5); supervisor rules in noise
units (after stage 2); quality-diversity-first (needs a goal-distance descriptor and evidence that
archived elites verify); oversize exploration (needs an owner-approved exploratory brief;
`OPEN_QUESTIONS.md` Q6); constrained freeform / adjoint (ADR D8).

---

## 7. What would change these decisions

| Result | Changes |
|---|---|
| B1 shows mesh error at the top comparable to the gaps between leading designs | Every ranking is re-examined; finalists move to the 2× DOF level by default (handoff §8 trigger) |
| Record-route equivalence fails | B2 stops; the record stays a geometry layer only; freedoms must be prototyped inside a generator instead (slower, per family) |
| B2: two or more freedoms with authority across constructions | SD-3 reopen condition is evaluated |
| B2: all freedoms inert | Effort moves from geometry to envelope and intent (owner decisions on size and target) |
| T4 shows the GRID extent estimate refuses designs the mesh would fit | Fix the estimator before any envelope discussion (`OPEN_QUESTIONS.md` Q1) |
| An unbiased pool exists (atlas check or B4) and a section-aware descriptor passes H ≥ 0.6 held-out | SD-5 reopen |
