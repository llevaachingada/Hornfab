# ARCHITECTURE_SYNTHESIS — final high-effort pass and decision record

> **Results update, 2026-11-16 23:15.** Experiments run after this was written did not support its
> two candidate spines. E1: response-level modelling showed no advantage over modelling the
> coverage-plus-DI proxy (10 versus 9.5 valid-design reveals in a fixed historical candidate pool;
> actual order was 29.75). This is not full-J or campaign-cost evidence. E2: the
> "construct, then correct" inverse step was worse than no change. E3: staged frequencies saved
> 0.1 %. Treat §3–§5 as hypotheses that were tested and mostly not confirmed. Current position and
> all results: `LOW_COST_AGENT_HANDOFF.md` §1 and §4. The plain-language guide in §8 remains a
> useful explanation of the ideas.

**Written:** 2026-11-16. **Code read at** `f0dd019`; **HEAD at close** `aa11b62`. No new evidence
was gathered for this pass; it re-reasons over `FABLE_OPTIONS_REVIEW.md` (measurements M1–M6) and
`FABLE_DISCOVERY.md`. Labels: **[measured]**, **[verified]**, **[dossier]**, **[inferred]**,
**[literature, from memory]**.

**This record supersedes §1 and §6 of `ARCHITECTURE_DECISION_RECORD.md` where they differ.**

---

## 1. Did I anchor on the canonical surface layer? Yes, partly.

The canonical surface is a *measurement instrument*. It lets geometry from different engines be
compared and fed to one model. It generates no candidates, predicts nothing, and chooses no
experiment. I promoted it because four directions depend on it and it is cheap, which is a
statement about build order, not about what makes Hornfab discover anything. Naming it "the
preferred architecture" was a category error. The question that should have been asked first is:
**what is the engine of discovery, and what is the scarce resource it spends?**

Reconsidered from that question, the measurements say three things I under-used:

1. **Discovery today is done by whoever writes the seed.** Lane rank after 16 rows predicts final
   rank at 0.90, and the campaign's best design appeared at attempt 55 of 2,853 **[measured, M6]**.
   This retrospective association does not establish that optimizers only polish or that the seed caused the outcome. The best lane's advantage is a human idea (an
   azimuthal wall-angle law giving independent H and V angles), not a search result.
2. **Each solve returns a response curve, and the search throws almost all of it away.** CMA-ES and
   the scalar GP see one number, J. But J = g(r(x)): r is the expensive response, g is the known,
   cheap scoring function. The response varies in about six independent ways **[M1]** and is
   predictable from geometry **[M4]**. An optimizer that models r uses roughly six pieces of
   information per solve where today's uses one.
3. **Frequency-grid sampling contributes to score variation; the total numerical and mesh error is not established.** The 0.17 J
   screen/verify gap comes from sampling a curve at different frequencies, on the same mesh
   **[measured]**. Response-level modelling does not by itself eliminate sampling or fidelity error.

---

## 2. Assumptions the reports did not question

| Assumption | Why it is doubtful | Opportunity |
|---|---|---|
| The thing optimized is a scalar J over a knob vector | J is a known function of a low-dimensional, predictable response | Composite, response-level optimization **[literature, from memory: Astudillo and Frazier 2019]** |
| Search runs forward: propose parameters, score them | The map from wall laws to beamwidth-versus-frequency is low-dimensional and locally near-monotone: each frequency is governed mostly by the part of the horn about a wavelength wide | Inverse design: construct from the target, then correct by root-finding. Root-finding in 6–8 dimensions needs far fewer solves than minimization |
| A BEM solve is atomic, so early stopping cannot apply (dossier E10) | Cost is per frequency (about 0.4 s to 45 s each **[dossier]**); frequencies are independent linear solves | Evaluate a few discriminating frequencies first and abandon hopeless candidates; choose *which* frequencies as part of the experiment |
| The lane (family × config) is the unit of exploration and allocation | Lanes are human seeds plus local polish; candidates from any generator cost milliseconds on CPU | Screen very large multi-generator candidate pools with a model; solve only the selected few |
| Data belongs to a brief | A response is a property of the geometry and source, not of the brief | One response database for all briefs; only the scoring and acquisition are brief-specific |
| Refusals are a search tax to be learned around | Some validity and envelope checks are computable on CPU, but their coverage and estimator fidelity are not established | Improve preflight and measure remaining refusals and false exclusions |
| Beamwidth and DI are the natural model outputs | Beamwidth is a threshold crossing and jumps when a lobe appears; pressure is smooth in geometry | Model the polar response in a smooth basis (angular harmonics by frequency) and derive beamwidth afterwards |
| Only far-field results are worth storing | Surface pressure from the same solve shows *where* on the wall each frequency's behaviour is set | Shape-sensitivity diagnostics, and a physical basis for deformation modules. Speculative; needs the solver to export it |
| A supervisor coordinates optimizers | With one model and one value-per-cost rule, "which family, which optimizer, which fidelity" are one decision | The supervisor shrinks to governance: budget, safety, approvals |

---

## 3. The strongest architecture: response-model-centred discovery

**Shape of the system.**

- **Candidate sources (keep every typology).** All existing generators, plus deformation modules
  applied to their outputs, emit candidates on CPU. Typologies are preserved exactly as generators.
- **Proposed pre-filter.** Test validity, envelope, throat fit and printability on sampled
  surfaces; completeness and false refusals require validation.
- **One forward model.** Geometry (canonical descriptors, wavelength-scaled) → response (a
  handful of smooth components), probabilistic, shared across engines, with a small per-lane
  residual where data is dense.
- **One acquisition.** For each candidate: expected gain under the *current* brief's scoring g
  applied to the predicted response, plus a value for information (model uncertainty or novelty in
  response space), divided by predicted solve cost. The same rule chooses family, modification,
  region, and how many frequencies to solve first.
- **Sequential evaluation.** Solve a few frequencies, update, continue or abandon.
- **Local polish as a proposer.** CMA-ES around incumbents stays, feeding candidates into the same
  pool; it is good at the last few percent and needs no model.
- **Governance outside the loop.** Budgets, protected owner-requested families, and every change of
  brief, envelope, bounds or fidelity policy remain human decisions.

**Central insight.** J = g(r(x)) with r low-dimensional and geometry-predictable, candidates and
validity nearly free, and solves the only scarce resource. So solves should be placed by a model of
r over everything that can be generated, not by local distributions inside hand-seeded lanes.

**What it unlocks that the current architecture cannot.**
- Exploration between and beyond lanes: the pool spans every engine and every module at once.
- Potentially fewer refusals or unnecessary frequency solves, if preflight and staging prove reliable.
- Every brief, and every future objective version, served by the same data and model.
- A direct answer to "what is achievable in this envelope": the image of the valid pool under the
  model, with uncertainty.
- Use of the low-dimensional structure without touching the typologies: the structure lives in the
  model's inputs and outputs and in the acquisition, not in the generators. For any family, the
  shape directions *outside* the span of its own knobs are exactly its candidate new modules.

**Where it fails, and the counterarguments.**
1. **Discovery lives where the model is weakest.** Held-out-engine skill is only 0.18–0.71
   **[measured]**. A model that cannot extrapolate will keep choosing near what it knows.
2. **It cannot invent a construction.** Screening existing generators finds combinations and gaps,
   not a new idea like the azimuthal wall law. New capability still has to come from new generators
   or modules; the model only decides where to spend solves among them.
3. **The last mile may be unpredictable.** The measured predictability is for smooth beamwidth and
   DI. Near the top, designs differ by ripple, flatness and loading terms of 0.1–0.4 J, which were
   not tested and may sit in the unpredictable residual. Then the model gets you to the good region
   (which seeds already do) and no further.
4. **The training data is biased.** Stored rows are CMA trajectories clustered round seeds. Skill
   measured on them may reflect cluster membership, not physics.
5. **A wrong model fails silently.** A local optimizer on real solves is at least honest.
6. **Humans plus CMA already reached the best in 55 attempts.** The gain here is unproven until a
   replay shows it (experiment E1).

**Is the canonical surface essential here?** Yes, as the input adapter and exact pre-filter:
without a common geometric input there is no cross-engine model and this architecture collapses to
today's per-lane searches. It is necessary plumbing, not the architecture.

---

## 4. The strongest genuinely different alternative: construct, then correct

**Shape of the system.**

- **Representation by acoustic intent.** A horn is defined by a small set of laws along the wall:
  wall-angle laws in H and V (which set beamwidth against frequency), an area law (which sets
  loading), a termination radius (which sets ripple), and a throat match. This is the area–aspect
  backbone of the options review, but driven by the target instead of searched blindly.
- **Constructor.** Given a brief's coverage corridor, build the first-order geometry directly from
  those laws, as constant-directivity horns have always been designed by hand.
- **Corrector.** Solve it, compare the response with the target in the low-dimensional response
  space, and update the laws with a Newton-type step using a Jacobian estimated from stored data
  and refined as solves arrive. This is space mapping, long used for expensive electromagnetic
  design with a cheap physics model alongside **[literature, from memory: Bandler et al.]**.

**Central insight.** With about eight shape unknowns and six response components, hitting a target
is a nearly square root-finding problem. Newton-type steps use every component of every solve and
converge in a handful of iterations when the map is locally near-linear. Minimizing a scalar in the
same space needs hundreds.

**What it unlocks.** A horn for a new brief in tens of solves; a systematic map of which coverage
corridors are reachable in a given envelope; shapes that belong to no family, because the laws are
free functions.

**Where it fails.**
- Where the map is not near-monotone: the diffraction-limited low end, and termination and ripple
  effects, which are resonant.
- For horns whose intent is not constant directivity. The repo's own rule forbids imposing that
  intent across typologies; Le Cléac'h or rolled horns would need their own intent laws.
- It abandons the typologies as generators and with them the engines' distinct response regions
  **[M2]** and published provenance.
- Local linearity and Jacobian conditioning are untested (experiment E2).

**Is the canonical surface essential here?** No. It is optional, useful only to import history as
Jacobian data and to compare results.

**How the two relate.** They are not exclusive. The constructor can be one more candidate source in
§3, and the corrector one more proposer. The real fork is which is the *spine*: a model choosing
among many generators' candidates, or a target-driven constructor with a corrector.

---

## 5. Decisive experiments

All three run on stored data first. Only E2's second stage needs solves and owner approval.

**E1. Does modelling the response beat modelling J? (zero GPU)**
Replay within lanes and across engines. From the designs already solved, let three selectors pick
the next design to "reveal" in turn: (a) a model of J on knobs; (b) a geometry → response model with
the known scoring applied to its prediction; (c) the actual CMA order. Count reveals needed to come
within one noise unit of the lane's best, and, with an engine held out, to find that engine's best
decile. *Decides:* the core of §3. If (b) is not at least twice as fast as (a) and (c) in the
median lane, the response-model spine is unsupported.

**E2. Is the response locally invertible? (zero GPU, then about 15 solves with approval)**
From stored data, fit local linear maps from shape modes to response components. Report local fit
quality, Jacobian condition number, and which response directions no geometry controls. Then, for
pairs of stored designs, predict the geometry change that turns one response into the other and
compare with the true difference. With approval: three targets, five Newton-type steps each.
*Decides:* §4. Good local linearity and convergence in about five steps make construct-then-correct
the spine, or at least the first proposer.

**E3. Can a candidate be judged from a few frequencies? (zero GPU plus a code read)**
Confirm in the solver wrapper that cost is per frequency and that frequencies can be solved
incrementally. Then replay stored 18-frequency responses: reveal frequencies in an informative
order, abandon a candidate when its best possible J cannot beat the incumbent by a margin, and
report compute saved against false abandonments. *Decides:* whether fidelity belongs inside the
acquisition. It is a throughput gain under either spine.

**Supporting, already briefed in `VALIDATION_EXPERIMENTS.md`:** X1 (surface round trip, the input
adapter), X2 (module authority, the source of new shapes), X3 (strict cross-engine transfer, the
model's extrapolation). X4 and X5 inform parameter spaces and governance, not the spine.

---

## 6. What must be designed now, and what must wait

**Settle now (cheap to decide, costly to retrofit):**
- The principle that models and selection work on responses, with scoring applied afterwards.
- A brief-independent response database joined to a canonical geometry record
  (`CANONICAL_SURFACE_CONTRACT.md`).
- Every generator can emit candidates and their surface on CPU without a solve.
- Validity and envelope are exact CPU filters, never learned penalties.
- The governance boundary: what any automated loop may never change.

**Leave undecided until the experiments report:**
- The spine: model-over-pool, construct-then-correct, or a hybrid.
- The source of new shapes: deformation modules, an intent-law backbone, or both.
- Model class, output basis (beamwidth components or angular harmonics), and uncertainty method.
- The acquisition's value function, in particular how much novelty is rewarded.
- Whether frequency-sequential evaluation and lane racing are worth building.
- Anything about class structure, file layout or task order.

---

## 7. Delegation and the reserved decision

**Safe to delegate to lower-thinking agents:** X1, X3, X4, X5 as briefed; E1 and E3 in full; E2's
stored-data stage; R1–R4 (already with another agent). Each has fixed data, a fixed method and
numeric pass or fail lines, so architectural intent cannot drift. Agents must not relax a
validation split, tune a threshold after seeing results, or turn a nomination by the surrogate into
a claim about acoustics.

**Reserved for a high-thinking model, after E1, E2 and X2 report:**
*Choose the spine and the generative strategy together.* That is one decision with four inputs:
does response-level selection beat scalar search (E1); is the response locally invertible (E2); do
modules have authority beyond existing knobs (X2); does the model extrapolate across engines (X3).
The same pass must define the acquisition's value function, because that is where the owner's
intent — corridor feasibility, novelty, robustness, a menu rather than a winner — becomes
mathematics, and it should interpret any transfer failure as either a descriptor problem (fixable)
or a physical limit (not).

---

## 8. Plain-language guide to each suggested change

This section is for whoever takes the work over. It explains each change in ordinary terms: what
happens today, what would change, a concrete example, what could go wrong, and which experiment
tests it. Full experiment briefs are in `VALIDATION_EXPERIMENTS.md`.

### 8.1 Terms used

| Term | Meaning |
|---|---|
| Solve | One boundary-element simulation of one horn. The expensive step: seconds to minutes of GPU time |
| Response | What a solve returns: sound level against angle at each frequency, plus throat impedance |
| Beamwidth | The angle over which level stays within 6 dB of on-axis, at one frequency |
| J (the score) | One number computed from the response by the objective. Lower is better |
| Brief | The design goal: target coverage, size limit, driver, crossover |
| Lane | One search configuration: one horn family with one set of knob ranges |
| Engine | The code that turns knobs into a horn shape (OSSE, point-grid, generated freeform, CAD) |
| Surrogate (model) | A fast statistical predictor trained on past solves |
| Candidate | A horn shape that has been generated but not yet solved |
| Acquisition | The rule that decides which candidate to solve next |

### 8.2 Change 1 — predict the response curves, not the score

- **Today.** Each optimizer is told one number per horn, J. The full response is stored, then
  ignored by the search.
- **Change.** Train the model to predict the response curves from the horn's geometry. Compute J
  afterwards by running the normal scoring on the predicted curves.
- **Example.** A horn has good horizontal coverage and poor loading. Today the optimizer learns
  "J = 5.3". With the change it learns "horizontal steady at 75°, vertical at 60°, throat
  resistance too low at 700 Hz", which tells it what to keep and what to fix.
- **Why it matters.** The response varies in about six independent ways (M1), so one solve teaches
  roughly six things, not one. And when the objective changes (v7 to v9, or the range scoring in
  `SCORING_RANGE_PROPOSAL.md`), nothing has to be relearned: only the final scoring step changes.
- **Could go wrong.** The fine details that separate the very best horns (ripple, small on-axis
  irregularities) may not be predictable.
- **Tested by.** E1, X3.

### 8.3 Change 2 — one pool of candidates from every horn type, checked on the CPU

- **Today.** Each lane runs its own search. A candidate that is too big or malformed is discovered
  as a refusal during the run and uses up an attempt (about 10 % of attempts).
- **Change.** Generate a large number of candidate shapes from *all* engines at once. Generating
  and checking a shape takes milliseconds on the CPU. Discard the invalid and oversized ones
  immediately. Only then decide which few to solve.
- **Example.** Generate 100,000 shapes across OSSE, rolled, biradial and Klangfilm families; 30,000
  fail the size or throat check and are dropped at no cost; the model ranks the remaining 70,000;
  50 are solved tonight.
- **Why it matters.** The search is no longer confined to the neighbourhood of hand-written
  starting points, and no solve budget is lost to refusals.
- **Could go wrong.** The model favours shapes similar to what it has seen, so the pool is wide but
  the choices stay conservative unless exploration is deliberately rewarded.
- **Tested by.** E1 (cross-engine half), X1 (can every engine emit a comparable shape description).

### 8.4 Change 3 — one rule decides where each solve goes

- **Today.** A person decides which lanes run, in what order, with which optimizer. A watchdog
  stops runs that look stuck.
- **Change.** For every candidate in the pool, estimate: how much better than the current best is
  it likely to be, how much would solving it teach the model, and how long would it take. Solve the
  candidates with the best value per second. Family, optimizer and region are no longer separate
  decisions; they fall out of this one ranking.
- **Example.** Two candidates: an OSSE variant predicted slightly better than the best so far, and
  a rolled horn in a region the model knows little about. The rule can prefer the second when the
  expected learning is worth more than a small gain.
- **Why it matters.** It replaces "supervisor switches between optimizers" with a single,
  explainable ranking. The human role becomes setting budgets and approving anything that changes
  the brief, the size limit or the search ranges.
- **Could go wrong.** If the model's uncertainty estimates are poor, "value of learning" is
  meaningless. A simple local optimizer on real solves is at least honest, so CMA-ES is kept as one
  of the sources of candidates.
- **Tested by.** E1, X5 (what past campaigns say about allocation).

### 8.5 Change 4 — solve a few frequencies first

- **Today.** Every candidate is solved at all 18 frequencies before anything is judged.
- **Change.** Solve four or five well-chosen frequencies first. If the horn is already clearly
  worse than the best so far, stop and move on.
- **Example.** After 400, 1,000, 2,500 and 6,000 Hz a candidate's vertical beamwidth is 110° where
  60° is the limit. No result at the other 14 frequencies can rescue it. About three quarters of
  its cost is saved.
- **Why it matters.** Most candidates are far from the best, so this could raise throughput
  several-fold.
- **Could go wrong.** The solver wrapper may not allow frequencies to be solved one at a time
  without overhead; this is unverified. Stopping early also means an incomplete stored response,
  which is less useful as training data.
- **Tested by.** E3.

### 8.6 Change 5 — a common description of shape (the canonical surface)

- **Today.** Each engine describes a horn by its own knobs. A rolled horn's knobs and an OSSE's
  knobs have nothing in common, so nothing learned from one transfers to the other.
- **Change.** After any engine builds a shape, sample its inner wall on a standard grid from throat
  to lip. Compute the same measurements for every horn: mouth size, depth, wall angle and section
  area along the wall, lip radius.
- **Example.** An OSSE and a biradial that happen to have the same mouth size and nearly the same
  wall angles get nearly the same description, and the model can use solves of one to predict the
  other.
- **Why it matters.** It is the input the model in Change 1 needs, and the place where size and
  validity are checked in Change 2. It is plumbing, not the engine of discovery.
- **Could go wrong.** Some shapes do not fit: multi-entry horns, CAD bodies, fine flutes. They stay
  outside.
- **Tested by.** X1. Contract in `CANONICAL_SURFACE_CONTRACT.md`.

### 8.7 Change 6 — new shapes by adding features to existing horns

- **Today.** A feature belongs to one engine. Independent horizontal and vertical wall angles exist
  only in OSSE; rolled lips only in the rows engine.
- **Change.** Define a small library of adjustments ("squeeze the vertical walls over the outer
  half", "flare the mouth", "roll the lip") that push the wall in or out smoothly and can be applied
  to any horn's sampled surface. With the adjustment set to zero, the original horn is unchanged.
- **Example.** Take the best biradial and apply 10 mm of vertical squeeze; the result is a shape no
  current engine can produce.
- **Why it matters.** This is where genuinely new geometry comes from. The model only chooses among
  candidates; something has to create candidates that did not exist before.
- **Could go wrong.** An adjustment may duplicate what an existing knob already does, or have too
  little effect to matter.
- **Tested by.** X2.

### 8.8 The alternative — build from the target, then correct

- **Idea.** Instead of searching, construct the horn directly from the wanted coverage, using wall
  angles for beamwidth, area growth for loading and lip radius for ripple. Solve it, see how the
  response differs from the target, and adjust the wall laws in proportion. Repeat a handful of
  times.
- **Example.** Target 70° horizontal. First build gives 76° above 3 kHz. Narrow the wall angle in
  the section of the horn that governs those frequencies; solve again; 71°.
- **Why it could win.** Correcting toward a target uses every part of the response and may converge
  in five to fifteen solves, where a search needs hundreds.
- **Why it might not.** It suits constant-directivity horns. Low-frequency behaviour is limited by
  size whatever the walls do, and ripple does not respond in a simple proportional way.
- **Tested by.** E2.

### 8.9 What stays exactly as it is

Every existing engine and family; the solver and mesher; the dataset identity system; the stored
runs; the 600 × 480 × 480 mm home brief; the rule that only the owner changes a brief, a size
limit, a search range, an objective version or the fidelity policy.

---

## 9. Main conclusion

The canonical surface layer survives, demoted: it is the essential input adapter for the preferred
architecture and optional for the alternative, and in neither is it the engine of discovery. The
engine I now recommend is **response-model-centred discovery**: model the response rather than J,
generate and validate candidates from every typology on CPU, and place each solve (and each
frequency) by one value-per-cost rule. The strongest different alternative is **construct, then
correct**: build from the acoustic target and converge by root-finding. Stored data can separate
them (E1, E2) before anything is built. My confidence that response-level modelling should replace
scalar-J modelling is high; my confidence that it yields *new* horns, rather than the same horns
sooner, is moderate, and depends on new candidate sources (X2) and on extrapolation (X3).
