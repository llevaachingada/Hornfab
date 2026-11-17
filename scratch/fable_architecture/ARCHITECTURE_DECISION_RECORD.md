# ARCHITECTURE_DECISION_RECORD — Hornfab discovery architecture

**Status:** leading hypothesis, not an authorized final architecture. **Written:** 2026-11-16.
**Code read at:** `main` @ `f0dd019`. **HEAD when this record was closed:** `aa11b62`
(= `origin/main`); the diff between the two was not reviewed. **Upstream reasoning:**
`FABLE_OPTIONS_REVIEW.md` (options, mathematics, measurements M1–M6) and `FABLE_DISCOVERY.md`
(scoring and fidelity findings). Read those only if a decision below needs its derivation.

**Superseded in part.** `ARCHITECTURE_SYNTHESIS.md` (written after this record) demotes the
canonical surface layer from "preferred architecture" to an input adapter, and names
response-model-centred discovery as the preferred engine with "construct, then correct" as the
alternative. Where §1 and §6 below differ from the synthesis, the synthesis wins. Decisions D1–D10
in §2 stand.

Evidence labels: **[measured]** computed from stored runs or meshes; **[verified]** read in code;
**[inferred]** my reasoning; **[literature]** published, untested here.

---

## 1. Recommendation

**Preferred architecture: specialist engines kept as they are, joined by a read-only canonical
surface layer, with three things built on that layer in this order of confidence:**

1. family-agnostic geometry analysis (descriptors, constraints, parameter sensitivity);
2. a response-level, cross-family surrogate used as a prior and for lane selection;
3. composable deformation modules applied to existing families to add H/V directivity control.

**Strongest alternative:** a shared area–aspect–section backbone (one parametric family replacing
the lanes, option G-B in the review), possibly searched in a learned mode space (G-E).

**Why the preferred option over the alternative.**
- The engines reach different acoustic regions: 41–54 % of each engine group's sane designs have no
  near neighbour from another group **[measured, M2]**. Replacing them risks losing that.
- They nevertheless share a low-dimensional shape space: 8 modes plus depth reproduce the H and V
  wall profiles of all 35 lanes to 1.2 mm RMS **[measured, M3]**, and simple geometry numbers predict
  an unseen lane's beamwidth curves to about 4° **[measured, M4]**. So a shared *analysis* language
  works without a shared *generator*.
- The mesher already accepts an arbitrary point-grid surface **[verified,
  `hornlab_mesher/geometry.py:214`]**, so the layer needs no new solver or mesher capability.
- The layer is CPU-only, read-only and reversible; a backbone is a rewrite whose results cannot be
  compared with history unless it reproduces existing designs, which is untested.

---

## 2. Decisions I am confident enough to settle now

| # | Decision | Basis |
|---|---|---|
| D1 | Do not build a universal geometry engine or full grammar now. Keep the existing engines. | M2; cost; grammar needs mixed-variable search the BO encoding refuses **[verified]** |
| D2 | Introduce a canonical surface as an *analysis* object only. It does not replace generators, mesher or dataset identity. | §1; contract in `CANONICAL_SURFACE_CONTRACT.md` |
| D3 | Multi-entry and CAD bodies stay on their own route. Share reporting and main-flare descriptors, not a search space or surrogate. | Topology and source model differ **[verified, dossier]** |
| D4 | Surrogates should model response curves (beamwidth, DI, impedance), not J. | Survives objective changes (v7 → v9); J is recomputed from curves **[inferred]** |
| D5 | Cross-family sharing happens through geometry computed on the surface, never through raw knob vectors. | Knob spaces are incomparable **[verified]**; M4 |
| D6 | No automatic change of brief, envelope, objective version, source model, fidelity or search bounds, under any supervisor. Propose only. | Owner constraints; review §4.3 |
| D7 | The 600 × 480 × 480 home brief is unchanged. Size questions are priced by similarity rescoring first. | Owner decision; free and exact for the scaled shape **[measured]** |
| D8 | Constrained freeform surfaces and learned neural shape embeddings are out of scope until an adjoint solver or roughly ten times more data exists. | 30–100 dims without gradients; 10⁴–10⁵ examples needed **[literature]** |
| D9 | A supervisor acts on J only after J has a published noise floor. Until then the watchdog is a safety net. | Screen/verify gap 0.17 J among the best designs **[measured]** |
| D10 | Owner-requested families are never cut by an allocation policy; they sit on a protected list. | Standing owner instruction |

---

## 3. Decisions that need experimental evidence

| # | Open decision | Experiment | What would settle it |
|---|---|---|---|
| O1 | Can every non-CAD engine emit the canonical surface without losing geometry or source information? | X1 | Deviation and metadata checks in the X1 brief |
| O2 | Deformation modules (keep families) versus a backbone (replace them) for H/V control | X2, then X1 part C | Module authority ≥ 3° on at least two base engines keeps modules; otherwise the backbone moves up |
| O3 | Is cross-family transfer real, or sibling-lane leakage? | X3 | Held-out-engine skill thresholds in the X3 brief |
| O4 | Which knobs to fix, link or free in future searches | X4 | Agreement between geometric and acoustic evidence |
| O5 | Whether lane racing or any portfolio policy saves compute | X5 | Savings that survive seed-leakage and censoring corrections |
| O6 | Whether a single surrogate should choose the next solve across lanes | X3 then X5 part D | A surrogate calibrated on J, not only coverage |

---

## 4. What would overturn the preferred architecture

- **X1 fails:** two or more engines cannot be sampled to within tolerance, or the surface loses
  source or shell information that changes the acoustics. Then the layer is not a common language
  and the choice falls back to per-family tooling.
- **X3 fails under held-out-engine validation:** transfer was sibling leakage. The layer still
  serves validity and sensitivity, but the surrogate, lane selection and unified acquisition lose
  their basis.
- **X2 shows modules lack authority while a backbone reproduces existing designs (X1 part C):**
  the strongest alternative becomes the preferred architecture.
- **Scoring dependency:** if mesh-convergence error (R1, with another agent) is larger than the
  frequency-sampling error, the stored responses are less trustworthy as training data and every
  surrogate result here needs re-checking at higher fidelity.
- **M2 turns out to be a size artefact:** if the engines differ in response only because their
  designs differ in size, the case for keeping specialist engines weakens. X3 part D checks this.

---

## 5. Options left open, not rejected

| Option | Reopen when |
|---|---|
| Area–aspect backbone (G-B) | X1 part C reproduces the best designs to about 1 mm, or X2 shows modules are weak |
| Learned mode-space search (G-E) | Same as above, plus a whole-surface (not two-plane) mode fit |
| Hierarchical grammar (G-C) | A mixed-variable optimizer exists and cross-engine combinations (X2 part C) prove valuable |
| Proposer portfolio on a shared log (S-E) | A surrogate is validated on J and the study-package model can host multiple proposers |
| Multi-task GP across lanes | The simple "shared model plus per-lane residual" leaves structure unexplained |
| Size-indexed archive and out-of-envelope probes | The surrogate points to a specific region and the owner approves an exploratory brief |
| Adjoint-based freeform optimization | Someone takes on an adjoint for the solver fork |

---

## 6. Final assessment of each alternative set

**Geometry (six).** Canonical layer: adopt as enabler. Deformation modules: preferred route to new
shapes, pending X2. Backbone: strongest alternative, pending X1 part C. Mode space: promising
reduction, pending whole-surface evidence. Grammar: defer. Freeform: out of scope.

**Supervisor (five).** Rule table in noise units: adopt once the noise floor exists. Lane racing:
plausible, pending X5; the first replay overstated it because a sibling lane was seeded with the
best design. Extreme-value bandit: little to learn from with 2–3 seeds; low priority. One surrogate
choosing across lanes: the most interesting long-term design, pending X3. Proposer portfolio:
keep open.

**Transfer.** Near-term and recommended: response-level surrogate on surface descriptors; shared
model plus per-lane residual; similarity augmentation, validated carefully because scaled copies of
one design are correlated, not independent; seeding by descriptor match. Mid-term: multi-task GP,
one-dimensional horn-equation features for loading. Speculative: learned embeddings.

**Parameter spaces.** Adopt: geometric identifiability from the surface Jacobian, and bounds
expressed as constraints on the surface. Adopt with care: importance from surrogates, used to
propose fixes and links, never to delete a knob silently. Later: searching in physically meaningful
controls, which becomes natural only if a backbone is adopted.

---

## 7. Dependencies recorded, not investigated further here

- Scoring noise, mesh-fidelity error, grid-invariant J, corridor objective: requests R1–R4 in
  `FABLE_RESEARCH_REQUESTS.md`, being run by another agent.
- Refusal taxonomy defects (post-mesh envelope coded as geometry; prefixed generator errors):
  `FAILURE_AND_BOUNDARY_AUDIT.md` §1. The canonical layer's signed margins depend on a fix.
- Owner decision on the acceptable coverage corridor for the home brief.
