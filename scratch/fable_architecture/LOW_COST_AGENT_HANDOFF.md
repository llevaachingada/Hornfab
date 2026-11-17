# MASTER HANDOFF — Hornfab architecture research (start here)

**Updated:** 2026-11-16 23:15 ET. **Repository:** `C:\Users\hunte\Hrns\hornlab-search`.
**HEAD:** `207f97a`. Code was read between `f0dd019` and `207f97a`.
**This file replaces the earlier low-cost-agent handoff.** It indexes every research document,
records every result so far, lists the research still needed, and defines what must be true before
a staged implementation plan is written. It is not that plan.

> **Folder status.** Another lane committed most of `scratch/fable_architecture/` at `207f97a`
> (63 files tracked). Files edited since then show as working-tree modifications; newer files are
> still git-ignored. **Do not commit, stage or revert anything here** unless the owner asks.

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
| "Construct, then correct" by proportional steps (synthesis §4) | Inverse step worse than no change (E2) | **Closed**, within the tested shape description |
| Solving a few frequencies first saves compute (synthesis §5) | 0.1 % saved with a rigorous bound (E3) | **Not demonstrated** |
| Geometry transfers across engines (options review M4) | Fails the strict success lines (X3) | **Weakened**; lane ordering still plausible |
| Lane racing saves compute (options review M6) | 0 % saving after corrections; halving would drop protected families (X5) | **Not supported** |
| Deformation modules give new control (options review G-D) | Undetermined (X2); earlier Klangfilm Stage A measured almost none | **Demoted** |
| Interpolating to a dense grid makes J stable (first-pass discovery) | Interpolation alone shifts J by sd 0.61 (R2); my number came from a harness with a DI error | **Wrong as stated** |
| Model-guided choice beats the order CMA-ES used | Both models about 3× fewer reveals than actual order (E1, proxy objective) | **Supported, with caveats** |
| Scoring definition changes which horns win | 3–4 of the top 20 survive a change to corridor scoring (R3, S1) | **Strongly supported** |

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

**Start here (in order):** this file; `UNIVERSAL_HORN_FAMILY.md` §1–§2 (the geometry idea in plain
language); `ARCHITECTURE_SYNTHESIS.md` §8 (plain-language guide and glossary).

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
| R3 | Does a corridor objective re-rank the top? | Complete | Top-20 overlap with v7: 4/20 for all three corridors. The three corridors pick the same 20 rows | The corridor *objective* is a first-order change; the vertical onset frequency barely matters. The shift is mixed with v9's different term set |
| R4 | Seed spread against gaps between configs | Complete | 6 configs qualify. Spread 0.14 (best lane) to 3.66 (Klangfilm). Median spread / median gap = 0.57 | Lane comparisons need matched-budget reruns before any family is judged |
| S1 | Ranges plus constancy on all stored designs | Complete | Stored v7 and v9-plus-constancy share 3/20 top designs. Robust to ±5° range shifts (15–20 of 20 retained) | Supports the scoring proposal. Weights and ranges are placeholders awaiting the owner |
| E1 | Response model against score model | Complete on a proxy | Median reveals: response 10, scalar 9.5, actual order 29.75. Cross-engine recall passes for two engines, zero for the third | No advantage for response-level modelling here. Either model about 3× better than the order actually used. Proxy objective (coverage plus DI), pool of already-visited designs |
| E2 | Local invertibility | Complete (stage one) | Local fit R² 0.56; inverse step worse than assuming no change; condition number median 49 | Proportional correction is not viable in the two-profile shape description |
| E3 | Judging from a few frequencies | Partial | Rigorous bound saves 0.1 % of frequency solves. The wrapper cannot return partial responses. One 12-frequency batch call took 689 s where 12 single calls took 33 s | Not demonstrated. The batch-timing anomaly is worth its own look (§6, A5) |
| X1 | Common shape description round trip | Partial | 50/60 designs sampled; Klangfilm recipes rejected by the current adapter (schema changed since they were run). Whole-surface modes: 8 → 1.4–2.3 mm, 16 → 0.3–0.7 mm | The earlier "8 modes, 1.2 mm" was for two profiles only. Old Klangfilm designs cannot currently be rebuilt: a reproducibility finding in itself |
| X2 | Deformation authority | Undetermined | Predictions out of the model's range; lip and diagonal not scoreable | Superseded by U3 |
| X3 | Strict cross-engine transfer | Partial | H-plane skill below 0.6 for every held-out engine; within-lane rank 0.49. Whole-surface inputs, wavelength scaling and augmentation not run | Transfer is weaker than the options review suggested |
| X4 | Parameter-space labels | Partial | Surface Jacobian full rank in two lanes; near-collinear pairs found (`a_deg`/`k`, `n`/`s`, `n`/`q`, `q`/`s`). No labels issued | Method works; blocked on X1 for generator lanes |
| X5 | Allocation replay, corrected | Complete with limits | 0 % saving against round robin; halving violates the protected-family rule. Default watchdog would have stopped the winning run at attempt 25. First-16-rows rank against final: 0.97 | No support for automatic racing. Watchdog stays a human-reviewed signal |
| U1–U3 | Layered backbone | **Not run** | — | The main open architecture question |
| P1 | Predictor replay for workflow hooks | **Not run** beyond `.fable/an7.py` | Predictor's picks beat random in 9 of 19 lanes | Unproven |

---

## 5. What is answered and what is open

**Answered well enough to plan on.**
- Scoring definition is the largest lever on which horn wins (R3, S1, first pass).
- v7's point target cannot be met in the 480 mm envelope at 700–1,100 Hz vertically; every lane
  shares that penalty (first pass, measured).
- A stable score needs about 22 frequencies or grid-independent term definitions (R2).
- Screen and "verify" use the same mesh; "verify" tests frequency sampling only (first pass, R1).
- Specialist engines reach different response regions; keep them (M2).
- Refusals cost about 10 % of attempts; a second-order issue (dossier).
- Seeds and starting points dominate lane outcomes (M6, R4, X5).
- No evidence supports automatic lane cutting or optimizer switching (X5).
- Proportional inverse design is not viable in the tested description (E2).
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
| A3 | **E1 follow-up.** Repeat with full J through the parity harness; with whole-surface descriptors from A1; and report where the response model's error sits (which terms) | Part 2, E1; `E1_RESPONSE_VS_SCORE.md` | A1 | A table that says which of the four explanations in §5 item 4 holds |
| A4 | **Grid-independent J.** In scratch only, redefine each v7 and v9 term as a weighted integral over log-frequency. Repeat R2's point-count table. Report which terms cause the 29 → 58 shift | `FREQUENCY_BUDGET.md` | Parity harness | Per-term table; point count needed for sd ≤ 0.10 under the new definitions |
| A5 | **Solver call timing.** Read `hornlab_search/solve/beat.py:599-807` and `TOOLCHAIN.md:105-132`; explain the 689 s batch against 33 s single-call record; state what a partial-response interface would require | `E3_FREQUENCY_STAGING.md` §A | — | One page with file references; no code change |
| A6 | **U2 and U3, CPU stages** | Part 3 | A2 | Validity tables and rendered overlays; the solve proposals written up |
| A7 | **X3 remaining parts**: whole-surface and wavelength-scaled inputs; loading, ripple and on-axis targets; similarity augmentation with leakage control; learning curves | Part 1, X3; `X3_TRANSFER.md` "missing work" | A1 | Three-scheme table against the stated pass lines |
| A8 | **X4 completion**: five lanes, box-corner checks, known-conditional recovery, labels | Part 1, X4 | A1 | Label table per lane; proposed fixes, links and widening proposals |
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
