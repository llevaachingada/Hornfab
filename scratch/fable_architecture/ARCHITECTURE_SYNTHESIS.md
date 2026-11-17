# ARCHITECTURE_SYNTHESIS — final high-effort pass and decision record

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
   The optimizers polish; they do not discover. The best lane's advantage is a human idea (an
   azimuthal wall-angle law giving independent H and V angles), not a search result.
2. **Each solve returns a response curve, and the search throws almost all of it away.** CMA-ES and
   the scalar GP see one number, J. But J = g(r(x)): r is the expensive response, g is the known,
   cheap scoring function. The response varies in about six independent ways **[M1]** and is
   predictable from geometry **[M4]**. An optimizer that models r uses roughly six pieces of
   information per solve where today's uses one.
3. **The solver is deterministic; the "noise" is made by scalarizing on a sparse grid.** The 0.17 J
   screen/verify gap comes from sampling a curve at different frequencies, on the same mesh
   **[measured]**. Working at response level sidesteps most of it.

---

## 2. Assumptions the reports did not question

| Assumption | Why it is doubtful | Opportunity |
|---|---|---|
| The thing optimized is a scalar J over a knob vector | J is a known function of a low-dimensional, predictable response | Composite, response-level optimization **[literature, from memory: Astudillo and Frazier 2019]** |
| Search runs forward: propose parameters, score them | The map from wall laws to beamwidth-versus-frequency is low-dimensional and locally near-monotone: each frequency is governed mostly by the part of the horn about a wavelength wide | Inverse design: construct from the target, then correct by root-finding. Root-finding in 6–8 dimensions needs far fewer solves than minimization |
| A BEM solve is atomic, so early stopping cannot apply (dossier E10) | Cost is per frequency (about 0.4 s to 45 s each **[dossier]**); frequencies are independent linear solves | Evaluate a few discriminating frequencies first and abandon hopeless candidates; choose *which* frequencies as part of the experiment |
| The lane (family × config) is the unit of exploration and allocation | Lanes are human seeds plus local polish; candidates from any generator cost milliseconds on CPU | Screen very large multi-generator candidate pools with a model; solve only the selected few |
| Data belongs to a brief | A response is a property of the geometry and source, not of the brief | One response database for all briefs; only the scoring and acquisition are brief-specific |
| Refusals are a search tax to be learned around | Validity and envelope are exactly computable on CPU before any solve | Filter the pool exactly; no refusal ever consumes budget or needs a feasibility model |
| Beamwidth and DI are the natural model outputs | Beamwidth is a threshold crossing and jumps when a lobe appears; pressure is smooth in geometry | Model the polar response in a smooth basis (angular harmonics by frequency) and derive beamwidth afterwards |
| Only far-field results are worth storing | Surface pressure from the same solve shows *where* on the wall each frequency's behaviour is set | Shape-sensitivity diagnostics, and a physical basis for deformation modules. Speculative; needs the solver to export it |
| A supervisor coordinates optimizers | With one model and one value-per-cost rule, "which family, which optimizer, which fidelity" are one decision | The supervisor shrinks to governance: budget, safety, approvals |

---

## 3. The strongest architecture: response-model-centred discovery

**Shape of the system.**

- **Candidate sources (keep every typology).** All existing generators, plus deformation modules
  applied to their outputs, emit candidates on CPU. Typologies are preserved exactly as generators.
- **Exact pre-filter.** Validity, envelope, throat fit and printability are computed on the sampled
  surface. Invalid candidates are never solved.
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
- No compute lost to refusals or to candidates that a few frequencies show are hopeless.
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

## 8. Main conclusion

The canonical surface layer survives, demoted: it is the essential input adapter for the preferred
architecture and optional for the alternative, and in neither is it the engine of discovery. The
engine I now recommend is **response-model-centred discovery**: model the response rather than J,
generate and validate candidates from every typology on CPU, and place each solve (and each
frequency) by one value-per-cost rule. The strongest different alternative is **construct, then
correct**: build from the acoustic target and converge by root-finding. Stored data can separate
them (E1, E2) before anything is built. My confidence that response-level modelling should replace
scalar-J modelling is high; my confidence that it yields *new* horns, rather than the same horns
sooner, is moderate, and depends on new candidate sources (X2) and on extrapolation (X3).
