# MASTER HANDOFF — Hornfab architecture research (start here)

**Refreshed:** 2026-11-16, at observed HEAD `01560e5`. **Repository:** `C:\Users\hunte\Hrns\hornlab-search`.
**Evidence snapshot:** code was originally read between `f0dd019` and `207f97a`; the corpus was committed at `01560e5`. Individual reports retain their own snapshot and current status.
**This file replaces the earlier low-cost-agent handoff.** It indexes every research document,
records every result so far, lists the research still needed, and defines what must be true before
a staged implementation plan is written. It is not that plan.

> **Folder status.** The corpus and its reproduction artifacts were force-added in `207f97a` and `01560e5`; 221 paths were tracked at this refresh. Concurrent report edits are present. Reproduction scripts can overwrite tracked artifacts: preserve them before rerunning. Do not commit, stage or revert anything unless the owner asks.

---

## 1. Where things stand, in one page

**The goal.** Find the system design that discovers more excellent, varied, valid horns per
expensive solve, including shapes Hornfab cannot make today.

**Current architectural position (provisional).**
1. *Generator:* a **layered backbone on shared wall-length stations**, each layer (throat,
   expansion, H/V split, section, termination) taking either a simple generic law or an existing
   family's own mathematics. Untested; experiments U1–U3 decide. Source: `UNIVERSAL_HORN_FAMILY.md`.
2. *Scoring:* move the home brief to **acceptance ranges plus a constancy term**, scored on enough
   frequencies to be stable. Best-supported finding of the whole effort.
   Source: `SCORING_RANGE_PROPOSAL.md`, `S1_RANGE_SCORING.md`.
3. *Search:* keep **BoTorch within a lane that has rows**; use a cross-family predictor only for
   **ordering lanes**, and only as a proposal the owner approves. Source: `PREDICTOR_AND_WORKFLOW.md`.
4. *Common shape description (canonical surface):* needed plumbing for comparing families and
   importing history; not the engine of discovery. Source: `CANONICAL_SURFACE_CONTRACT.md`.

**What the first round of experiments did to earlier claims.** Several of my hypotheses did not
survive. Read §4 before trusting any earlier document.

| Earlier claim | Result | Standing |
|---|---|---|
| Modelling response curves beats modelling the score (synthesis §3) | Replay: 10 versus 9.5 reveals, no advantage (E1) | **Not supported** |
| "Construct, then correct" by proportional steps (synthesis §4) | Inverse step worse than no change (E2) | **Closed by the brief’s decision rule**, for historical geometry recovery in the tested representation; physical response correction remains untested |
| Solving a few frequencies first saves compute (synthesis §5) | 0.1 % saved with a rigorous bound (E3) | **Not demonstrated** |
| Geometry transfers across engines (options review M4) | The tested two-profile model misses the strict success lines (X3) | **Weakened**; lane ordering still plausible |
| Lane racing saves compute (options review M6) | 0 % saving in a non-discriminating availability replay; halving would drop protected families (X5) | **Not supported** |
| Deformation modules give new control (options review G-D) | Undetermined (X2); earlier Klangfilm Stage A measured almost none | **Demoted** |
| Interpolating to a dense grid makes J stable (first-pass discovery) | Interpolation alone shifts J by sd 0.61 (R2); my number came from a harness with a DI error | **Wrong as stated** |
| Model-guided choice beats the order CMA-ES used | Both models about 3× fewer reveals than actual order (E1, proxy objective) | **Retrospective proxy replay only** |
| Scoring definition changes which horns win | 3–4 of the top 20 observations survive combined scoring changes (R3, S1); term sets also changed | **Strongly supported for these replays; corridor effect not isolated** |

**Document precedence when they disagree:** this file → `UNIVERSAL_HORN_FAMILY.md` →
`ARCHITECTURE_SYNTHESIS.md` → `ARCHITECTURE_DECISION_RECORD.md` → `FABLE_OPTIONS_REVIEW.md` →
`FABLE_DISCOVERY.md`. Result files (R, S, E, X) outrank all of them on matters of fact.

---

## 2. Rules for every agent

- **Read-only.** No GPU or BEM solve, no solving CLI command, no pytest, no git mutation, no
  process control. A live solve queue may be running.
- No edits to source, configs, queues, `runs/` or `examples/`. Write only under
  `scratch/fable_architecture/`, scripts in a dot-folder named after the task (`.u1/`, `.x3/`).
- Interpreter `.venv\Scripts\python.exe`. CPU only. Mesh builds only where a brief allows.
- **Replay rule (mandatory).** Stored DI is the sin(θ)-weighted balloon DI from
  `search/evaluate.metrics_from_response`. Regenerating metrics with plain `compute_metrics` is
  wrong by up to 8 dB DI and 7.2 J. Use the parity-exact harness
  `.tmp/fable_replay_harness.py` (matches stored J exactly on 116 rows). `objective/replay.py`
  does not dispatch objective v9; call the v9 scorer as `.s1/replay.py` does.
- **Sibling rule.** Lanes that are versions, brief twins or seeded copies of one construction must
  be held out together. Map and seed checks: `.e2/sibling_seeds.txt`, `.x3/strict.py`.
- Do not loosen a validation split, change a pass line after seeing results, or describe a model's
  prediction as an acoustic result.
- Anything marked "owner approval required" is a proposal. Write it up; do not run it.
- Owner-requested horn families are never recommended for cutting.
- Report what failed and what is unknown. "Partial" is an acceptable status; a quiet substitute
  experiment is not.

---

## 3. Document map

**Start here (in order):** this file, especially §9 for continuation; `UNIVERSAL_HORN_FAMILY.md`
§1–§2 and §8 (geometry and its decision gates); `SCORING_RANGE_PROPOSAL.md` §8 (scoring
continuation); and `PREDICTOR_AND_WORKFLOW.md` §11 (search and predictor continuation).
`ARCHITECTURE_SYNTHESIS.md` §8 supplies a plain-language glossary, subject to later results.

| Group | File | What it is |
|---|---|---|
| Position | `UNIVERSAL_HORN_FAMILY.md` | Layered backbone: concept, five example horns, acoustic critique, U1–U3 |
| Position | `ARCHITECTURE_SYNTHESIS.md` | Response-model spine and its alternative; partly overtaken by E1–E3 |
| Position | `ARCHITECTURE_DECISION_RECORD.md` | Settled decisions D1–D10 (still valid); open decisions |
| Position | `FABLE_OPTIONS_REVIEW.md` | Wide comparison of options; measurements M1–M6 |
| Position | `FABLE_DISCOVERY.md` | First pass: scoring and fidelity findings |
| Proposal | `SCORING_RANGE_PROPOSAL.md` | Ranges plus constancy scoring |
| Proposal | `PREDICTOR_AND_WORKFLOW.md` | The predictor and five workflow hooks |
| Contract | `CANONICAL_SURFACE_CONTRACT.md` | Common shape description |
| Briefs | `VALIDATION_EXPERIMENTS.md` | Part 1: X1–X5. Part 2: E1–E3. Part 3: U1–U3 |
| Briefs | `FABLE_RESEARCH_REQUESTS.md` | R1–R4 |
| Results | `MESH_FIDELITY_PAIRS.md`, `FREQUENCY_BUDGET.md`, `CORRIDOR_RERANK.md`, `SEED_SPREAD.md` | R1–R4 |
| Results | `S1_RANGE_SCORING.md` | S1 |
| Results | `E1_RESPONSE_VS_SCORE.md`, `E2_INVERTIBILITY.md` (and the earlier `E2_LOCAL_INVERTIBILITY.md`), `E3_FREQUENCY_STAGING.md` | E1–E3 |
| Results | `X1_ROUND_TRIP.md` … `X5_ALLOCATION.md` | X1–X5 |
| Dossier | `INDEX.md` and the 14 files it lists | Original evidence dossier (code audit, failures, optimizers, watchdog) |
| Repo research | `docs/plan/12_RESEARCH_BASIS.md`, `docs/knowledge/README.md`, `docs/research/typologies/` | The acoustics library; read before any geometry or scoring change |

**Data and scripts.** `.fable/rows.pkl` (3,802 attempts on the home landscape brief; rebuild with
`.fable/load.py`); `.fable/desc.npz` (27 shape numbers for 1,715 designs); `.fable/an1`–`an7.py`
(measurements M1–M6 and the predictor replays); `.e1/descriptors.pkl` (descriptors for 3,410
designs); `.x1/*.npz` (50 sampled surfaces); `.tmp/fable_replay_harness.py` (parity-exact replay).

---

## 4. Results so far

| ID | Question | Status | Headline | Meaning |
|---|---|---|---|---|
| R1 | Is mesh error smaller than frequency-sampling error? | Complete, under-sampled | 327 pairs; only 2 with J < 5 (ΔJ +0.16, +0.01). Among the 30 shown: mean −0.10, sd 0.44. Pairs with about 2× DOF moved ≤ 0.04 | Looks small; not settled for the best designs. Needs a few paired solves (§6, B1) |
| R2 | How many frequencies does a stable J need? | Complete | Parity exact. About 22 points reach sd ≈ 0.10 against a dense baseline; 18 → 0.13; 12 → 0.31. Interpolating 29 → 58 points *alone* shifts J by sd 0.61. Rational pressure interpolation is unusable | J depends on the grid by construction. Interpolation is not a fix; the terms themselves need a grid-independent definition |
| R3 | Does a corridor objective re-rank the top? | Complete | Top-20 overlap with v7: 4/20 for all three corridors. The three corridors pick the same 20 rows | Combined v7-to-v9 changes substantially re-rank this set; the corridor's separate contribution is not identified |
| R4 | Seed spread against gaps between configs | Complete | 6 configs qualify. Spread 0.14 (best lane) to 3.66 (Klangfilm). Median spread / median gap = 0.57 | Lane comparisons need matched-budget reruns before any family is judged |
| S1 | Ranges plus constancy on stored attempts | Complete | Within each original-objective cohort, stored v7 and v9-plus-constancy share 3/20 top observations. Combined-cohort sensitivity retains 15–20 of the base top 20 | Supports investigating the scoring proposal. Weights and ranges are placeholders; the new score's noise floor is unknown |
| E1 | Response model against score model | Complete on a proxy | Median reveals: response 10, scalar 9.5, actual order 29.75. Cross-engine recall passes for two engines, zero for the third | No advantage for response-level modelling here. The observed reveal-count comparison is retrospective, on a coverage-plus-DI proxy and an already-visited pool; it does not establish prospective campaign savings |
| E2 | Local invertibility | Complete (stage one) | Local fit R² 0.56; inverse step worse than assuming no change; condition number median 49 | The historical-geometry recovery rule fails in the two-profile description; an alternate valid geometry could still reach the target response |
| E3 | Judging from a few frequencies | Partial | The tested conservative bound saves 0.1 % of frequency solves on stored rows. The wrapper cannot return partial responses. One 12-frequency batch call took 689 s where 12 single calls took 33 s | Not demonstrated. The batch-timing anomaly is worth its own look (§6, A5) |
| X1 | Common shape description round trip | Partial | 50/60 designs sampled; Klangfilm recipes rejected by the current adapter. A legacy kernel generated candidate grids, but provenance and mesh agreement remain unverified. Exploratory in-sample modes: 8 → 1.4–2.3 mm, 16 → 0.3–0.7 mm | The earlier "8 modes, 1.2 mm" was for two profiles only. Historical reconstruction is unresolved, not proven impossible |
| X2 | Deformation authority | Undetermined | Predictions out of the model's range; lip and diagonal not scoreable | U3 tests a related but different structural-freedom question; neither establishes acoustic authority |
| X3 | Strict cross-engine transfer | Partial | H-plane skill below 0.6 for every held-out engine; within-lane rank 0.49. Additional loading, ripple and on-axis targets and training-only similarity augmentation were tested; augmentation improved paired skills but did not meet the H-plane line. Whole-surface and explicit wavelength-scaled inputs remain open | Transfer is weaker than the options review suggested |
| X4 | Parameter-space labels | Partial | Five lanes sampled with provisional surface Jacobians (three native, two generated); three other generated recipes failed rematerialization. Conditional and acoustic checks are partial; no classifications established | Sampler fidelity, corner and margin checks, conditional coverage and label-agreement gates remain incomplete |
| X5 | Allocation replay, corrected | Complete with limits | 0 % saving against round robin in a degenerate replay: the winner was the only observed available arm before the target; halving violates the protected-family rule. Default watchdog would have stopped the winning run at attempt 25. First-16-rows rank against final: 0.97 | No policy comparison or GPU-time saving established. Watchdog stays a human-reviewed signal |
| U1–U3 | Layered backbone | **Not run** | — | The main open architecture question |
| P1 | Predictor replay for workflow hooks | **Not run** beyond `.fable/an7.py` | Predictor's picks beat random in 9 of 19 lanes | Unproven |

---

## 5. What is answered and what is open

**Answered well enough to plan on.**
- Changing the score substantially re-ranks the stored top designs (R3, S1); the corridor effect is not isolated from other term changes.
- The sampled v7 designs share a vertical point-target penalty at 700–1,100 Hz; this is not proof that every possible design in the envelope must do so.
- In R2’s sampled replay, about 22 frequencies reached sd ≈ 0.10 against its dense baseline; grid-independent term definitions are untested.
- Screen and "verify" use the same mesh; "verify" tests frequency sampling only (first pass, R1).
- Specialist engines reach different response regions; keep them (M2).
- Refusals cost about 10 % of attempts; a second-order issue (dossier).
- Seeds and starting points materially affect the observed lane comparisons (M6, R4, X5); their relative causal importance is not established.
- No evidence supports automatic lane cutting or optimizer switching (X5).
- The tested minimum-norm inverse fails the retrospective historical-geometry recovery rule (E2); response-target convergence remains untested.
- The repo already contains three partial backbones (`UNIVERSAL_HORN_FAMILY.md` §0).

**Open, and decisive.**
1. Can a layered backbone reproduce existing horns, are families connected inside it, and do its
   new freedoms move the beam? (U1, U2, U3)
2. Is mesh error small for the *best* designs? (B1; needs solves)
3. Which acceptance ranges, vertical onset, and "constant or gently narrowing" does the owner want?
4. Why did response-level modelling show no advantage: the proxy objective, the visited-design
   pool, the two-profile inputs, or a real absence of benefit? (A3)
5. Does any predictor choose better designs than random from an *unbiased* pool? (P1 step 7; B4)

---

## 6. Research still needed

### A. Zero-GPU and CPU work (can start now, in this order)

| # | Task | Brief | Needs | Done when |
|---|---|---|---|---|
| A1 | **Finish X1.** Resolve Klangfilm recipe provenance (which historical adapter rebuilds the stored designs, verified against the stored mesh); run contract tests 1–5 properly; recover every exact metadata field | `VALIDATION_EXPERIMENTS.md` X1; `X1_ROUND_TRIP.md` "continue by" list | — | Six-lane table with pass or fail per test, and a stated tolerance |
| A2 | **U1, layered reproduction** | Part 3, U1 | A1 samplers | Deviation table, own-law and generic-law, four lanes |
| A3 | **E1 follow-up.** Repeat with full J through the parity harness; with whole-surface descriptors from A1; and report where the response model's error sits (which terms) | Part 2, E1; `E1_RESPONSE_VS_SCORE.md` | A1 | A comparison of the four explanations in §5 item 4, stating where evidence cannot distinguish them |
| A4 | **Grid-independent J.** In scratch only, redefine each v7 and v9 term as a weighted integral over log-frequency. Repeat R2's point-count table. Report which terms cause the 29 → 58 shift | `FREQUENCY_BUDGET.md` | Parity harness | Per-term table; point count needed for sd ≤ 0.10 under the new definitions |
| A5 | **Solver call timing.** Read `hornlab_search/solve/beat.py:599-807` and `TOOLCHAIN.md:105-132`; investigate the cause of the 689 s batch against 33 s single-call record (assembly accounts for 672.4 s; root cause remains unknown); state what a partial-response interface would require | `E3_FREQUENCY_STAGING.md` §A | — | One page with file references; no code change |
| A6 | **U2 and U3, CPU stages** | Part 3 | A2 | Validity tables and rendered overlays; the solve proposals written up |
| A7 | **X3 remaining parts**: whole-surface and explicit wavelength-scaled inputs, sibling lineage and within-lane learning curves / solve-value estimation. Loading, ripple and on-axis targets and controlled augmentation have partial results; see the revised ledger | Part 1, X3; `X3_TRANSFER.md` "missing work" | A1 | Three-scheme table against the stated pass lines |
| A8 | **X4 completion**: validate the five sampled lanes and sampler, resolve failed rematerializations, complete corner and margin checks, conditionals and label-agreement gates | Part 1, X4 | A1 | Label table per lane; proposed fixes, links and widening proposals |
| A9 | **Separate corridor from term set.** Rescore all rows under v9 with a point target and under v9 with the corridor, same terms otherwise | `CORRIDOR_RERANK.md` reading | Parity harness | Top-20 and top-100 overlaps for the two cases |
| A10 | **P1, predictor replay**, including the unbiased-pool step | `PREDICTOR_AND_WORKFLOW.md` §10 | A1 | One table per hook; count of unbiased designs per lane |
| A11 | **Protected-family and lineage inventory**: which lanes the owner requested, and each run's starting-point ancestry | `X5_ALLOCATION.md` "unfinished" | — | A list the owner can confirm |

A1 unblocks A2, A3, A7, A8 and A10; it is the first job. A4, A5, A9 and A11 are independent and
can run alongside.

### B. Work that needs solves (owner approval required; do not run)

Collect these into one request to the owner once section A has reported. Screen-solve counts are
estimates.

| # | Purpose | Solves | Decides |
|---|---|---|---|
| B1 | Mesh fidelity for the best designs: the ten best landscape designs at the screen DOF cap and at twice it, same 22+ frequencies | 20 | Whether rankings at the top are trustworthy (R1 could not say) |
| B2 | U3: structural freedoms, control plus seven variants and repeats | 12–16 | Whether the backbone's new reach is acoustically real |
| B3 | U2: two valid paths between families, eleven shapes each | 22 | Whether one search space can replace lanes |
| B4 | Predictor on an unbiased pool: two lanes, top 10 picks and 10 random each | 40 | Whether workflow hooks B and C are worth wiring |
| B5 | U1 confirmation: four rebuilt surfaces | 4 | Whether history transfers to the backbone |
| B6 | Matched-budget lane reruns for the four leading constructions under the new scoring | owner's choice | Fair family comparison (R4) |

Suggested priority if the budget is small: B1, B2, B5, then B3.

### C. Decisions only the owner can make

1. Acceptance ranges for horizontal and vertical coverage, and the frequency from which vertical
   is scored.
2. Whether "constant" means flat, or a gentle steady narrowing is acceptable (and how steep).
3. Which other terms become "free below a limit" (ripple, DI roughness, flatness) and the limits.
4. Whether the deliverable is one winner or a short menu.
5. The list of protected families.
6. Approval and budget for section B.

---

## 7. Readiness for the implementation plan

A staged implementation plan should be written by a high-thinking model **after** the following
are in hand. Until then, writing it would mean planning around unknowns.

| Must be known | From |
|---|---|
| The scoring the plan optimizes for | Owner decisions C1–C4; A4; A9 |
| A stated noise floor and frequency count under that scoring | A4; B1 |
| Whether the layered backbone inherits history | A2 (U1); B5 |
| Whether families are connected in it | A6 (U2); B3 |
| Whether its new freedoms matter acoustically | B2 (U3) |
| Whether a cross-family model earns a place | A3; A7; A10; B4 |
| Which knobs are dead, coupled or wrongly bounded | A8 |
| What an allocation policy may and may not do | A11; `X5_ALLOCATION.md` |

**Minimum set to start planning:** owner decisions C1–C4, plus A1, A2, A4 and A6. The plan can
then be staged so that later stages are conditional on B-results.

### Outline the plan will need to cover (headings only; not the plan)

| Stage | Scope | Depends on |
|---|---|---|
| 0. Truth fixes | Refusal classes; envelope classification; one parity-exact replay path including v9; rebuildability of historical recipes (the Klangfilm adapter finding) | Dossier; R2 harness; X1 |
| 1. Scoring and intent | Ranges plus constancy as a versioned objective; grid-independent terms; published noise floor; per-plane vertical onset; diagonal scoring | C1–C4; A4; A9; S1 |
| 2. Fidelity ladder | What "screen", "verify" and "finalist" mean; frequency count; mesh level; finalist re-solve | R1; R2; B1; A5 |
| 3. Common shape description | The canonical surface contract as a read-only layer; exact CPU validity and envelope margins | A1; contract |
| 4. Generator | Layered backbone with pluggable specialist laws, staged a few knobs at a time; or, if U1–U3 fail, shared layers added to existing families | A2; A6; B2; B3; B5 |
| 5. Parameter spaces | Fix, link and re-bound from evidence; constraints in place of arbitrary boxes | A8 |
| 6. Search | BoTorch within lanes; seeding from the best stored designs; cross-family prior only if it passes | A3; A7; A10; B4 |
| 7. Campaign management | Noise-aware watchdog as a reviewed signal; lane ordering as a proposal; protected families; no automatic changes to brief, bounds or fidelity | X5; A11 |
| 8. Excluded topologies | Multi-entry, multicell, phase plugs: shared data and reporting only | `UNIVERSAL_HORN_FAMILY.md` §5.4 |

Stages 0–2 are supported by evidence already in hand and do not depend on the generator question.

---

## 8. When to bring a high-thinking model back

- **To write the staged plan:** when the minimum set in §7 is complete.
- **Earlier**, if A2 shows the layered form cannot reproduce existing horns (the generator
  direction then needs rethinking), or if B1 shows mesh error at the top comparable to the gaps
  between designs (every ranking then needs re-examination).
- **Reserved decision:** generator direction (layered backbone, shared layers on existing
  families, or neither) together with the search design that goes with it.

---

## 9. Continuation guide: how the evidence fits together

This section explains the decisions behind the task table. It does not change a brief's methods,
thresholds, or approval boundaries. Before starting, check the actual repository and running-work
state: the HEAD and counts above describe a snapshot, not a live inventory. Treat source documents
and experiment outputs as evidence of what was measured at that snapshot. Recheck owning code when
the current result depends on implementation details.

### 9.1 The central decision is not yet an implementation choice

The proposed layered generator has to do three different things: reproduce the geometry already
solved (U1), provide valid paths between meaningfully different constructions (U2), and create
freedoms that change the acoustic response (U3). Success at one is not success at the others.
For example, a close surface fit does not establish source or shell equivalence, a valid geometric
path does not show a useful acoustic path, and a surrogate's predicted 3° change is not a BEM
measurement. Keep the published specialist engines and owner-requested families available while
these are unresolved; U1–U3 do not authorize replacing or dropping them.

Existing implementations already contain useful pieces: the generic GRID radius field, the Crowe
area/aspect/section generator, and the Klangfilm H/V slope-law core. `UNIVERSAL_HORN_FAMILY.md`
explains why a shared station structure matters and why independent ribs can create poor surfaces.
The proposal is to test whether their ideas can coexist in a carrier, not to assume these pieces
are already interchangeable. Include rollback, throat extensions and diagonal/corner shape in the
comparison; two H/V profiles alone cannot establish whole-surface equivalence.

**Decision interpretation:**

| Evidence obtained | What it supports | What remains open |
|---|---|---|
| X1 contract tests pass | A comparable sampled representation for the tested routes | It is not proof that a backbone generates the same shapes or that the surfaces sound alike |
| U1 passes on its own-law reconstruction | The proposed carrier can reproduce the tested sampled surfaces to the stated tolerance | Source, mesh, and response equivalence still need their stated checks; other families remain untested |
| U2 passes geometric checks | The tested interpolated paths are geometrically feasible under the specified checks | An acoustically useful path still requires the separately approved solves |
| U3 CPU variants pass | The candidate controls produce valid geometric changes | Authority means measured beam change under the stated BEM criterion, not model nomination |
| A pass line fails | Reconsider the specific carrier, path or control that failed | Do not silently alter the threshold or remove an owner-requested family |

### 9.2 Why X1 is the first dependency

X1 is an instrument-calibration problem. Its experimental grids cover 50 designs from five
routes, but the five contract acceptance checks and full metadata recovery are not established.
Historic Klangfilm recipes are not reconstructed by the current adapter; a legacy kernel produced
candidate surfaces, but its saved implementation digest and agreement to the historic build remain
unverified. This is evidence of a reconstruction gap, not proof the geometry is unrecoverable.

The existing mesh physical wall tag can include inner wall, shell and closure on the same entity.
A distance from every tagged node to the inner surface therefore cannot by itself prove that the
inner sampler fails. Separate the surface roles with defensible provenance or report that test as
unresolved; do not relabel a shell mismatch as inner-wall error. Likewise, the rolled samples'
depth discrepancy needs the actual shell/closure/source bounding convention checked before its
cause is asserted. Test refinement, mesh agreement, full envelope, exact metadata and determinism
individually against `CANONICAL_SURFACE_CONTRACT.md` §8; record the denominator and the precise
reason for every refusal. Do not use the 50 in-sample PCA fits as a substitute for any of those
tests.

For a reconstruction, keep the original recipe, run configuration, brief and source settings tied
to the sampled surface. Preserve the throat/driver, symmetry, termination, mounting and outer
shell information specified by the contract; a plausible wall shape alone is insufficient. A
historical adapter may be read from repository history, but do not change the current worktree or
execute arbitrary historical code without inspecting it. Write any temporary sampler and outputs
only in the task's scratch subdirectory; avoid overwriting the tracked research artifacts.

### 9.3 What the scoring evidence actually allows

S1 compared stored v7 against a proposed v9 corridor plus constancy score using the saved
response data. In each original-objective cohort, 3 of the top 20 observations overlapped; the
separate R3 comparison found 4 of 20. These are observations in a biased historical pool, and the
v7 and v9 comparisons changed multiple terms. They show that the *combined scoring choices* matter,
not that the corridor alone caused the change. S1's ranges, constancy divider, slope limit and
dead bands were exploratory; its response regeneration also required a stored-DI correction.
The owner's accepted ranges and interpretation of constancy are still open.

R2's roughly 22-frequency result is an sd of 0.104 J against one interpolated dense baseline,
for its tested data and score. It is not a proven universal count or a noise floor for a new
objective. R1 has only two low-J pairs and those are equal-DOF pairs; it does not establish
convergence at the top. Before trusting small rank differences, A4 must separate interpolation,
grid definitions and individual score terms; A9 must compare point and corridor coverage while
holding the v9 term set and all other relevant conditions fixed. A same-score mesh comparison for
the best designs remains the owner-approval B1 proposal. See `SCORING_RANGE_PROPOSAL.md`,
`FREQUENCY_BUDGET.md`, `CORRIDOR_RERANK.md`, and `MESH_FIDELITY_PAIRS.md` for datasets and limits.

### 9.4 Search results: avoid turning a retrospective advantage into a guarantee

E1's response and scalar selectors used a coverage-plus-DI proxy and selected from already-solved
historical designs. The response model did not beat the scalar model under the stated median
speed criterion; both appeared faster than historical order on that proxy, but the candidate pool,
initial eight reveals, cached/refused attempts and original optimizer's adaptive generation limit
what that comparison means. Full J, whole-surface inputs and a fresh candidate pool remain open.

X3's strict held-out-engine tests found weak H-plane transfer and uneven loading and ripple
prediction; training-only similarity augmentation improved its paired baseline but did not meet
the H-plane success line. Maintain the exact design-hash and sibling-group split boundaries when
extending it. X5's policies tie at the target because, under its conservative observed-availability
convention, only the eventual winner was available before the target was reached. This neither
proves racing cannot work in other campaigns nor justifies automatic family elimination. The
watchdog result is a counterfactual using default rules, not proof those rules were active in each
historical job. See the individual E1, X3 and X5 reports for their complete limitations.

### 9.5 Parallel work, dependencies and handoff quality

The sequence in §6 is a dependency graph, not a requirement to idle while one task runs. X1/A1 is
the critical path for U1/A2 and validated whole-surface extensions. A4 (grid-independent score),
A5 (solver-call code and timing analysis), A9 (same-term corridor comparison) and A11 (lineage and
protected-family inventory) can proceed independently in separate scratch directories. U2/U3
depend on a credible U1 representation; their acoustic stages are proposals requiring the owner's
approval. P1's unbiased-pool comparison also needs its documented independent data and must not be
presented as complete merely because a retrospective ranking looks promising.

For every continuation result, record the observed HEAD and timestamp, exact inputs and selection,
source or script path, split and grouping, denominators, comparator, units and preset threshold.
List failed reconstructions and missing outputs separately from failed acceptance tests. Name the
report and reproducible command, identify whether an output is measured, model-predicted or an
inference, and state the next action the result enables. When existing scripts write tracked
artifacts, inspect their output paths first and direct new outputs to a separate scratch location;
do not overwrite another session's evidence. Rerun only checks allowed by §2 and the task brief.

---

## 10. Results added 2026-11-16 23:40 (A4, A5, A9, X1 addendum)

> **NOTE ON THE TABLE BELOW (2026-11-17, added by the lower-cost continuation lane agent).** The
> runbook instructs every task to append one row to this table. All rows below the original four
> (A4, A5, A9, X1 addendum) were appended by **lower-cost lane agents** — **not by Fable (the
> senior/high-thinking reviewer) and not by the owner** — and each row is a lane task result, not a
> gated decision: none changes a pass line, threshold, split, frozen contract, or brief. The
> senior reviewer's decisions remain in §11 and the documents it wrote.

These complete four items from §6 and qualify some statements above. Where this section and an
earlier one differ, this section is newer.

| ID | Status | Headline | Report |
|---|---|---|---|
| **A4** grid-independent score | Complete for v7 on the 58 study pairs | Scoring on a uniform dense log-frequency grid converges (58 → 116 points changes J by sd 0.045; 0.016 among the best 28). No new term definitions are needed. The sd 0.61 "29 → 58" shift is a change of definition, not noise. Residual error from having 18 solved frequencies: sd 0.13 and rank correlation 0.88 among the best 28 (stored grids: 0.17 and 0.81), carried by on-axis flatness and loading terms | `A4_GRID_INDEPENDENT_SCORE.md` |
| **A5** solver call timing | Complete (code read) | The 689 s versus 33 s record is a known multi-frequency batching cliff; production already solves one frequency per call on CUDA. Staged evaluation is cheap at the solver loop and costly downstream (partial responses are a new record type). Not worth building on present evidence | `A5_SOLVER_CALL_TIMING.md` |
| **A9** corridor versus term set | Complete | Term-set change alone keeps 6 of the top 20 but leaves lane order unchanged. Corridor coverage alone keeps 11 of 20 and changes the leading lane (`ext_throat_hvlaw` first → fourth; `osse_rrect` lanes lead). Corridor mode cuts the ripple term to about 3 % of its point-mode value | `A9_CORRIDOR_VS_TERM_SET.md` |
| **X1 addendum** Klangfilm provenance | Resolved | The stored Klangfilm digest is reproduced exactly by the legacy bridge's digest function at HEAD `207f97a`. Stored designs are rebuildable with verified provenance through `tools/geometry/klangfilm_lame.py`; the current adapter refuses them only because it accepts a newer schema | `X1_ADDENDUM_KLANGFILM_PROVENANCE.md` |
| **N1** finish X1: five contract tests on six lanes | Complete; **stop condition met** | 60 designs (10 per lane). Determinism 60/60; refinement 30/30 on the three testable lanes (worst 0.198 mm). Inner-wall agreement at the contract-minimum 65×31 record: ext-throat 10/10 (p99 0.158), ATH morph 10/10 (0.850), biradial 10/10 (0.142); **rolled 0/10 (1.696; 49 azimuths passes, p99 0.36–0.59)**, **Crowe 0/10 (1.870; native-point floor ~1.07, mesher fit)**, Klangfilm 9/10 (one design 1.457; saved digest `e3a1f4a3…` ≠ current `ea5026…`). Envelope W/H fails on biradial (+1.9…+3.5) and partly on ext/Crowe; every depth deficit is the rear closure at z=−t. Two or more lanes fail Test 2, so N2–N5 were not run | `X1_CONTRACT_TESTS.md` |
| **N1b** contract v2 Test 2 and Test 3 | Complete; **no hand-back** | 65 stations × 61 azimuths; native floor measured per lane. All six contract lanes pass v2 rule 2, 10/10 each, medians ≤0.14 mm: ext 0.108 (floor 0.068), ATH 0.247 (0.048), Crowe 1.353 (1.160, thr 1.451), rolled 0.856 (0.555), Klangfilm 1.155 (1.116), biradial 0.101 (0.047). 61 azimuths removes N1's rolled and Crowe failures. Provenance: 72 Klangfilm designs (all `e3a1f4a3…`, incl. N1's ten) are not reproducible at HEAD and were excluded; ten digest-verified replacements pass 10/10; rolled's 51 recipes match HEAD; Crowe/native lanes store no digest. Envelope: stored box = mesh box in 70/70; every depth deficit is the rear closure exactly; biradial's +1.9…+3.5 mm is the generator's outward `outer_points` shell, which is not in the meshed box (meshed box = inner-sheet box in 10/10); **0 of 309 stored biradial designs within 3.5 mm of 600 W / 480 H**. Lecleach (added for N4) is not rebuildable at HEAD: `d6c9abd` changed its H/V realization after both stored runs, and its recipes store no digest | `X1B_CONTRACT_V2.md` |
| **N4** U1 layered reproduction | Complete; **failure line met; handed back** | Best valid design of five lanes (rolled substitutes for lecleach). Three ribs + one superellipse per station, exact ψ (rib identity ≤6e-14 mm). Own-rib worst: ext 48.26, biradial 3.43, Crowe 29.90, rolled 48.25, Klangfilm 3.88 mm → **0/5 at ≤0.5 mm, 5/5 above 2 mm**. Cause: the 45° radius forces a near-rectangular exponent that overshoots 30–60° by up to 48 mm; the section is not in the superellipse family (36–46/65 stations clipped at p=16 on three lanes). Extra azimuth ribs with a Pchip blend: 5 → 1.00–27.08, 9 → 0.25–11.43 (only ext reaches 0.5), 17 → 0.12–3.36. ψ splines through 4/6/8 values are worse (8.97–208.11 mm): ψ turns too fast at the lip. Mesh difference is 1–2 orders smaller, so not the cause. U2/U3 not run | `U1_LAYERED_REPRODUCTION.md` |
| **N2** protected families and run lineage | Complete | 21 lanes: **17 carry owner-request evidence** (4 of them family-level only), **4 no evidence found**. Of the four, ext-throat H/V-law and OSSE rounded-rect carry owner *drop* evidence, not a request; no family is recommended for cutting. Lineage: **75/75 runs classified, 0 unknown** — 58 hand-written seed, 16 best design of an earlier run, 1 warm start (ATH v9, from 12eb61+570bc6); **15 of 17** parented runs are seeded within 0.17 J (exceptions: fold-added 0a228d +0.30 J, H-only A/B de1861 +0.26 J). Strict 1e-6 seed matching is too tight for recorded seeds; five documented seeds needed config comments and would otherwise be unknown. dd15d8's seeded verdict is cross-brief (mechanical, not acoustic continuity) | `A11_PROTECTED_AND_LINEAGE.md` |
| **N3** grid independence under v9 | Complete | 58 study pairs. J_v9 on a uniform dense log grid converges by 58 points: 58→116 sd 0.032 (all) / 0.019 (best 28), rank 0.999/0.997; 116→232 0.012/0.008. Residual from 18 vs 29 solved frequencies: sd 0.193 all / **0.113 at the top**, rank 0.953 — A4's v7 size. Adding strict constancy changes the requirement: J_v9+constancy is **not** converged at 58 (sd 0.175 all / 0.055 top) and needs 116 (0.058 / 0.014); residual 0.370 / 0.205. Constancy is ~55 % of the augmented level (mean cost 6.09 all, 3.22–3.45 top) and J-independent. Residual carried by `flat_cv`, `load`, `flat` — same as A4; `rip` does not. v9 best-28 overlaps A4's v7 criterion set 25/28; A4's set reproduced 28/28 at 0.00 J. Corridor and weights are placeholders | `N3_GRID_INDEPENDENCE_V9.md` |
| **A10** P1 predictor replay | Complete; **unbiased-pool stop fired; hooks A, B, skip fail** | Strict unbiased designs: **0 of 8 study lanes** (every solved row is CMA/BoTorch-visited); 6 of 8 stay under 30 even on the cadence upper bound, so the fair-pool replay was **not run** and no optimizer-visited substitute is reported. Biased replay (19 lanes, sibling + engine holdout, all valid rows): **A** rank corr vs lanes' best full J **0.733** (line ≥0.8; 1 of 5 true top-five lanes recovered) — the cov+DI comparator gives 0.944 but is diagnostic only. **B** predictor pick beats the first solve 11/19 (line 13/19), same as one random design. **C** predictor top 8/16/32 beat first rows 14/16/13 but random from the same pool beats them 18/17/14 and beats the predictor 10/12/10 — the pool, not the predictor. Skip test **8.9 %** of skipped designs in the true top 10 % (line <2 %). an7 reproduced exactly (0.55/0.43/0.30; 12/19, 9/19) | `P1_PREDICTOR_REPLAY.md` |
| **A3** E1 follow-up with full J and whole-surface descriptors | Complete; **E1's "no advantage" holds at full J; the proxy objective is the identified cause of the old picture** | 10 lanes × 10 starts, E1's protocol unchanged; parity gate 0.0 J / 0.0 term on 2,595 CD rows and E1 reproduced exactly under its own proxy truth. Full-J median reveals: score 18.5, score-on-descriptors 18.25, E1 curve head 24.0, all-nine-term head 18.25, actual history 87.25, random 55.25. **Part A not met** (needs ≤ half), **Part B not met** (+1 % curve, +62 % term), **Part C not met** (OSSE 3.1 %/1.0 %, GRID 78.8 %/52.3 %, GEN-FF 3.2 %/0 %), so E1's failure criterion is now fully met. The same curve selector needs 10.0 reveals on the cov+DI proxy vs 24.0 on full J; proxy-best is outside the full-J top decile in 4/10 lanes. Term error shares: `diag` 0.287, `dislope` 0.228, `cov` 0.211, `load` 0.105, `flat_cv` 0.061. Whole-surface descriptors built (A3-WS-v1, 404 numbers, 60 records) but under-powered at 10 designs/lane; pool vs real absence cannot be separated without new solves | `E1_FOLLOWUP_WHOLE_SURFACE.md` |
| **A8** X4 completion | Complete; **sampler/lane validation passes; ROSSE resolved as digest drift** | Five `.x4` lanes, 11 designs each: 55/55 design hashes reproduced and 55/55 pass v2 rule 2 at 65 × 61 (Crowe worst p99 1.646 mm vs threshold 1.712; medians ≤0.051), including the native rounded-rectangle lane N1b never covered. Labels: family 100 % on all five; typology 100 % on three, 96.5–98.0 % on Crowe (193/200) and biradial (301/307) — all 13 disagreements are verify-mode records whose provenance omits the generator block. Envelope binds (sampled ext-throat W +1.13 mm, ATH H +1.35 mm inside; one-knob corners cross on ext/ATH/Crowe); wall gap does not (+4.10 mm minimum). Rematerialisations: crowe_panel 11/11, Klangfilm 9/11 verified plus 10/10 verified replacements, **`rosse_rect` resolved** — `9b040e37…` vs HEAD `601056d0…` is a validator-only change in `a10e784` (`b` floor 0.0→−0.10); with only the persisted-digest check bypassed in memory, 11/11 rebuild, stored-mesh p99 0.468–0.918 mm (native floor 0.343–0.721, all pass), W/H exact, depth = rear closure. **Unresolved: lecleach only**, plus 2/11 of the old Klangfilm sample. Part B/D gates not testable/not run; the full 2^k corner scan is not testable | `X4_COMPLETION.md` |
| **A7** X3 remaining parts | Complete; **both-plane line not met; prior worth ≈8 local solves, not 15** | Scheme 3 (held-out engine), 1,715 designs / 35 lanes / 3 engines. WL-1 (`x·2πf/c`, c = 343 m/s) lane H/V/DI .785/.880/.809, engine .336/.668/.515; per engine GEN-FF .582/.690/.434, GRID .288/.628/.527, OSSE .425/.770/.499 → **V ≥.6 in 3/3, H ≥.6 in 0/3**, so the both-plane line fails; the within-lane rank line also fails on scheme 3 (.489/.500 vs .6). WL-1 beats its row-matched frequency-conditioned control on GEN-FF/GRID (+.09/+.03 H, +.09/+.17 DI) with one OSSE H regression (−.03); the no-frequency-information control collapses to −.38…−2.51. Whole-surface descriptors (227 features, 60 N1b-passing designs, 6 lanes) do not beat the matched baseline and are underpowered — the 27-number profile baseline also collapses on the same 60 (H −.06 vs .75 on 1,715) and no lane can supply 30 held-out designs. Learning curve: sibling-holdout prior alone .621 within-lane rank; local-only reaches .618 at 48; per lane the prior is matched by 8 solves in 13/23 and ≥16 in 10/23 (7 of the 13 have a negative prior); marginal solve value +.019 rank (8→16), +.006 (16→32), ~0 after 32; transfer decays .695→.575 across chronological quarters. Two cross-group lineage links found outside the fixed sibling map (fold_warm←morph, 3×klangfilm_hv←klangfilm_lame) | `X3_REMAINING.md` |
| **LANE-REVIEW** corpus review handed to the senior reviewer | Complete — **handed back; generator decision reserved to the senior reviewer** | All 54 documents digested (spine read directly; four read-only digest lanes). Verdict: the unified backbone is **falsified at its own predeclared gate** (U1: 0/5 lanes ≤0.5 mm, 5/5 >2 mm), the response-model spine is **not supported at full J** (E1+A3), construct-then-correct **closed** (E2), staging and racing **not demonstrated**, predictor hooks A/B/C **fail** with 0 unbiased designs anywhere; the canonical record is **validated** (6/6 lanes at 65×61; 55/55 in A8) and ranges+constancy scoring is the **best-supported change**. Recommendation (for senior confirmation, not a gated decision): the §7 stage-4 fallback — shared layers as per-lane modules on existing families; U2 closed; U3 re-based on lanes; optional predeclared U1-bis falsification test (CPU-only, not run). Process-integrity and overtaken-claims registers included. **No code implemented; no pass line changed** | `LANE_REVIEW_FOR_FABLE_2026-11-17.md`, `X1_ACCEPTANCE_TABLE.md`, `OWNER_DECISIONS_2026-11-17.md` |

**Consequences for the task list in §6.**
- A4, A5 and A9 are done. A4 must be repeated under whatever objective the owner chooses; the
  method is `.a4/a4.py`.
- A1 (finish X1): Klangfilm is unblocked. Remaining: contract tests 1–5 on all six routes, with
  inner and shell mesh surfaces separated.
- A11 (protected-family and lineage inventory) is not started.
- E3's staged-frequency idea: closed unless a better abandon rule is first shown on stored data.

**Consequences for the plan outline in §7.**
- Stage 1 (scoring) can now state a measured proposal: score on a uniform dense log grid
  (about 116 points) from at least 22 solved frequencies. Dense scores are a new score identity
  and are not comparable with stored J.
- The owner's scoring decision splits into two independent parts: the coverage target, which
  decides the leading family, and the secondary terms and ripple window, which decide the design
  within it. Add to the owner's decisions in §6 C: whether ripple should be measured across the
  listening window or only inside the corridor width.
- Stage 0 (truth fixes) should include a rule for recipes written by older adapters or bridge
  tools, so that history stays rebuildable.

## 11. Decision after N1 (2026-11-17, high-thinking reviewer)

N1 met its stop condition at the contract's minimum sampling. The causes are measured and are
instrument settings: 3° azimuth sampling is too coarse for rolled relief (passes at 49 azimuths),
the Crowe corner sits at the mesher's own fit error (about 1.1 mm), and one Klangfilm design has an
unverified digest. **The canonical surface idea is not overturned.** The contract is amended
(`CANONICAL_SURFACE_CONTRACT.md` §12, contract v2) and the runbook has an addendum with task N1b.
N2 and N3 were never dependent on N1 and should run now.

New findings worth carrying into the plan:
- For cornered sections the solved mesh departs from the designed surface by about 1 mm. The mesh
  is what was solved; the generator is what was designed.
- Sampled and stored bounding boxes differ by up to 3.5 mm on the biradial lane, while the envelope
  check uses a 0.5 mm tolerance. Designs near the size limit may be judged differently before and
  after meshing.
