# FABLE_OPTIONS_REVIEW — expanded architectural options for Hornfab

> **Results update, 2026-11-16 23:15.** Later experiments qualify three of the measurements here.
> M3 ("8 modes, 1.2 mm") holds for two wall profiles only; on whole surfaces 8 modes give
> 1.4–2.3 mm and 16 give 0.3–0.7 mm (X1). M4 (transfer) fails the strict held-out-engine pass
> lines (X3). M6 (racing) shows no saving once seeded lanes are merged (X5). The preference for
> deformation modules (G-D) is withdrawn in `UNIVERSAL_HORN_FAMILY.md`. Current position:
> `LOW_COST_AGENT_HANDOFF.md`.

**Date:** 2026-11-16 (late). **Tree:** `main` @ `f0dd019`. **Mode:** read-only discovery. No solve,
mesher run, queue or tracked-file change. New files are this document and five analysis scripts in
the git-ignored `scratch/fable_architecture/.fable/`.

**Scope.** This is the broader comparison requested after the first pass: geometry representation,
adaptive campaign management, intelligent parameter spaces, transfer of acoustic knowledge, and
exploration beyond the envelope. It is not a scoring audit and not an implementation specification.
The scoring findings from `FABLE_DISCOVERY.md` are carried as prerequisites in §8; their remaining
statistical tests (R1–R4) are with another agent and are not repeated here.

Labels: **[measured]** computed here from stored runs and meshes; **[verified]** read in code;
**[dossier]** from the evidence dossier; **[literature]** published method, not tested on Hornfab;
**[proposal]** my design idea, untested.

---

## 1. Six new measurements that shape the comparison

All from the 3,414 valid rows on the home landscape brief (35 lanes, 2026-11-15..17) and their
stored meshes. Scripts: `.fable/an1.py` … `an5.py`.

| # | Finding | Number | What it bears on |
|---|---|---|---|
| M1 | The achieved response space is low-dimensional. Principal components of the H beamwidth, V beamwidth and DI curves (600–8,000 Hz) | 6 components carry 95 % of the variance; the first (71 %) is low-frequency beamwidth, mostly vertical | How many acoustically meaningful degrees of freedom exist |
| M2 | Engine groups reach different response regions. Share of acoustically sane rows (J < 12) lying far from every other group's rows | OSSE 41 %, point-grid 54 %, generated-freeform 44 % | Whether specialist engines add real diversity |
| M3 | A shared shape basis describes every lane. Shape modes of the H and V inner-wall profiles read from the meshes of 1,715 designs | 8 modes plus depth reproduce all lanes to 1.2 mm RMS (95th percentile 2.4 mm); modes learned without a lane describe that lane to a median 0.9 mm | Feasibility of a shared geometric backbone |
| M4 | Geometry transfers across lanes. A plain tree model on 27 family-agnostic geometry numbers predicts the beamwidth curves of a lane it has never seen | Error 4.0–4.5° against 11–14° naive; skill R² 0.75 (H) and 0.87 (V); it ranks unseen lanes by coverage error at rank correlation 0.90–0.96 | Transfer learning, lane selection before any solve |
| M5 | Within a lane, few knobs matter and models are learnable. Tree models on raw knobs, 12 lanes with ≥ 100 rows | Cross-validated rank correlation on J 0.74–0.95; 2–7 of 5–18 knobs carry 90 % of importance; seven lanes have a top-decile knob pinned at a bound | Parameter importance, bounds |
| M6 | Lane quality shows early, and most compute came after the answer. On the 27 constant-directivity lanes | Best-of-first-16-rows predicts final lane rank at 0.90; the campaign's best J (3.10) was reached at attempt 55 of 2,853 | Value and shape of a supervisor |

**Caveats that apply throughout.** Several lanes are siblings (a v7 and v8 of the same
construction), so "never seen" overstates independence; the stricter leave-one-engine-out test in
§5 is weaker. M3 and M4 use only the H and V wall profiles at 12 depth stations: they do not capture
section shape between the planes, lip detail or throat detail. M4 was tested on beamwidth and
coverage error, not on loading, ripple or flatness. M6's later attempts were deliberate exploration
of other families, not failed attempts to beat the leader.

---

## 2. A fact that reframes the geometry question

The mesher already accepts an arbitrary surface. `PointGridHornGeometry` takes
`inner_points[n_phi, n_s+1, 3]` in millimetres, with optional outer shell, symmetry planes and a
source cap **[verified, `hornlab_mesher/geometry.py:214`]**. Rows, rolled and Klangfilm families
already use it, including surfaces that fold back on themselves.

So every horn except the CAD multi-entry bodies can be written as one object:

> **S(s, φ) → (x, y, z)**, with s ∈ [0, 1] along the wall from throat to lip (arc length, not depth),
> φ the azimuth, and the throat ring S(0, φ) fixed to the driver exit.

Using arc length rather than depth for s is what lets rollback and re-entrant lips live in the same
representation. The architectural question is therefore not "which engine", but **what
parameterizes S, and what is computed on S**. Today nothing is computed on S across families: the
canonical sampler refuses point-grid and CAD designs, the nine-number descriptor refuses grid, and
BO's geometry adapter supports native families and one rolled recipe only **[dossier, verified]**.

---

## 3. Direction 1 — geometry representation and composability

### 3.1 Six candidate architectures

**G-A. Specialist families plus a canonical surface layer (no new shapes).**
Keep every generator. Add one function per engine that returns S on a standard grid, and compute
everything else on S: descriptors, envelope, self-approach, curvature, area law A(s), aspect R(s),
wall-angle laws θ_H(s), θ_V(s).
*Idea:* families stay as parameterizations; S is the shared language.
*Unlocks:* one validity and envelope test for all routes; cross-family descriptors (M4);
parameter-activity analysis by geometry (§5); BO eligibility for grid families.
*Limits:* discovers nothing new by itself. Cost is small: mostly adapters, CPU only.

**G-B. Shared parametric backbone (area–aspect–section coordinates).**
One closed form for the section and three one-dimensional laws along s:

- section: r(s, φ) = [ |cos φ / a(s)|^p(s) + |sin φ / b(s)|^p(s) ]^(−1/p(s)) · (1 + Σ_k c_k(s) cos 2kφ)
- size and split: a = √(A·R / C(p)), b = √(A / (R·C(p))), where A(s) is section area, R(s) is the
  H/V aspect and C(p) the superellipse area constant (the inversion CROWE v1 already uses)
- A(s) from a wall-angle law, θ(s) = θ₀ + ∫ positive increments, so the wall cannot fold by
  construction; R(s) and p(s) as monotone or bounded splines with C² gates at the throat
- termination: an arc of radius ρ and wrap angle ω continued in arc length from s = 1.

*Idea:* separate the two things horn theory separates. Area growth governs loading (the
one-dimensional horn equation depends only on A(s)); aspect and wall angle govern the directivity
split. Coverage becomes a direct control instead of a consequence.
*Unlocks:* independent H and V flare with any section evolution and any termination in one space;
valid-by-construction shapes; about 10–14 dimensions for everything.
*Limits:* superellipse-plus-harmonics sections cannot make creases, petals with sharp folds or
diagonal X-folds exactly; published families are reproduced approximately, so their provenance is
"inspired by", not "is". Medium cost. Failure mode: a backbone that is nearly, but not quite, each
family, so results cannot be compared with history.

**G-C. Hierarchical geometry grammar.**
A typed tree: `Throat ∘ Body(law) ∘ Section(law) ∘ Azimuth(mod) ∘ Termination ∘ Mount`, each node a
module with declared units, an `active_when` predicate, and junction conditions (C¹ or C² in s).
Body laws are the existing meridian generators; operators are the existing splice, blend and
perturb.
*Idea:* composition is function composition on S; the catalogue becomes data.
*Unlocks:* combinations that are impossible today because features are tied to engines:
azimuthal wall-angle law (OSSE only), rollback (rows only), intermediate section stations (native
freeform only, generators emit exactly two), ripple and lip (osse_rollback only).
*Limits:* the search space is a tree with categorical choices. Mixed-variable optimization needs
either an outer bandit over structures with inner continuous search, or a mixed surrogate; BO's
encoding refuses categoricals today **[verified]**. Silent no-op knobs are the classic failure.
High cost. It does not reduce dimension; it organizes it.

**G-D. Feature modules as deformations of any base (my preferred way to get composability).**
S = S_base + Σ_i w_i · D_i(s, φ) · n̂(s, φ), where S_base is any existing family at its published
parameters, n̂ is the surface normal and each D_i is a smooth, local, named bump: "vertical squeeze
from s₁ to s₂", "mouth flare", "waist pinch", "diagonal fold", "lip roll". This is free-form
deformation and Hicks–Henne bumps from aerodynamic shape optimization, applied to S
**[literature]**.
*Idea:* w = 0 reproduces the published family exactly, so provenance and history are preserved;
the same module works on every family; each module has one or two knobs with a physical meaning.
*Unlocks:* H/V authority on families that lack it; controlled hybrids; an "authority test" per
module (how many degrees does one unit of w move the beam) that is comparable across families.
*Limits:* deformations can self-intersect or pinch the throat, so validity must be checked on S
(needs G-A); a library of bumps is a design choice. Low-to-medium cost.

**G-E. Learned shape basis ("mode space").**
S − S̄ = Σ_k z_k · Φ_k, with modes Φ_k learned from the designs already solved. M3 shows 8 modes
for the two principal wall profiles reach 1.2 mm; M4's companion test shows 5 modes plus depth carry
all of the response this descriptor can predict.
*Idea:* search directly in z. Families become regions of one space; the box is the convex hull of
what has been built, widened deliberately.
*Unlocks:* one continuous, low-dimensional space for BO across all families; interpolation between
families; a natural novelty measure (distance from existing data).
*Limits:* linear modes can only produce blends of what exists, so it is poor at genuinely new
topology; decoding needs a section law between the planes (G-B's formula can supply it);
interpolated shapes may be unprintable. Speculative until the round-trip test in §3.3 passes.

**G-F. Constrained freeform surface.**
A tensor-product B-spline control net over (s, φ) with constraints (throat ring, envelope, minimum
gap, convexity where wanted). Published horn optimization does exactly this with gradients: the
Umeå group optimized boundary parameterizations and curvature for efficiency and directivity using
adjoint sensitivities **[literature]**; COMSOL ships a horn shape-optimization example.
*Limits for Hornfab:* 30–100 control values and no gradients. BEAT has no adjoint, and
derivative-free search at that dimension needs thousands of solves. It becomes viable only with an
adjoint solver (a fork-level research project) or after reduction to modes (G-E).

### 3.2 Capability comparison

| Capability | G-A layer | G-B backbone | G-C grammar | G-D modules | G-E modes | G-F freeform |
|---|---|---|---|---|---|---|
| Independent H/V flare | reports it | native | by module | by module | if in data | native |
| Evolving cross-section | reports it | p(s), R(s), harmonics | section stack | bumps | limited | native |
| Rollback, re-entrant lip | handled (arc-length s) | termination arc | termination node | lip module | weak | native |
| Azimuthal shaping, folds | reports it | smooth harmonics only | yes | yes | weak | yes |
| Throat coupling | check | fixed ring + C² gate | throat node | protected zone | fixed | constraint |
| Non-star-shaped | yes | yes | yes | yes | no | yes |
| Multi-entry | no | no | topology node, CAD | no | no | no |
| Typical search dimension | unchanged | 10–14 | 10–25 + categoricals | base + 2–6 | 6–10 | 30–100 |
| Valid by construction | no (checks) | largely | no | no | no | no |
| Keeps published provenance | yes | no | yes | yes | no | no |
| New shapes | none | many | many | some | blends | most |
| Works with current BO | after adapter | yes | no (categorical) | yes | yes | no |

**Multi-entry horns should not be unified.** Ports change topology and the source model. Keep the
CAD route; share only descriptors of the main flare and the reporting layer.

### 3.3 Discriminating experiments (CPU first)

- **X1, round trip (CPU only).** Take the 20 best designs from five lanes. Fit G-B and G-E to each
  canonical surface; report surface deviation over the whole grid, not just two planes. Pass:
  median below 1 mm and no design above 3 mm. This decides whether a backbone can inherit history.
- **X2, module authority (zero GPU, then at most 12 solves with approval).** Use the M4 surrogate to
  predict how far each G-D module moves H and V beamwidth per unit weight on three base families;
  keep modules predicted to exceed 3°, then confirm with a handful of solves under the same
  pre-declared 3° rule the Klangfilm study used.
- **X3, cross-engine combination (CPU only).** Build three shapes no engine can make today (OSSE
  throat with azimuthal wall law plus rolled lip; rolled body with a mid-station section change;
  biradial with vertical squeeze) as point grids and run mesh-only validity. Pass: they mesh inside
  the envelope and DOF cap.

---

## 4. Direction 2 — adaptive optimization and campaign management

### 4.1 What a supervisor has to recognize, stated so it can be computed

| Condition | Signal | Notes |
|---|---|---|
| Stagnation | Best-so-far gain over the last window, in units of the measured scoring noise; plus CMA step size relative to the box | Today's 0.5 % rule is below noise |
| Convergence | Step size collapsed **and** surrogate's best expected improvement below the noise | Distinguishes "done" from "stuck" |
| Bound saturation | Top-decile mass within 3 % of a bound **and** the surrogate still improving outward | M5 finds seven lanes pinned; geometry tells whether the bound is physical (§5) |
| Insufficient exploration | Step size collapses before about 10·d valid rows; large surrogate uncertainty inside the box | |
| Repeated invalid geometry | Refusal rate by class, with a signed margin computed on S | Needs the refusal taxonomy fix |
| Poor information gain | Change in the surrogate's held-out error, or in its predicted optimum, per solve | Sees value when J is flat, including for QD |

### 4.2 Five supervisor architectures

**S-A. Rule table over the signals above.** Transparent and cheap; brittle; needs thresholds in
noise units. This is the watchdog made honest.

**S-B. Racing across lanes (successive halving).** Give each lane a small budget, keep the better
half, double. *Why it fits:* M6 shows lane rank after 16 rows predicts final rank at 0.90. In
replay, halving reached the campaign best while consuming 1,363 attempts where the actual campaign
used 2,853. *Limits:* a lane that improves late is dropped. The replay also flatters racing: the
best lane's own first 16 rows were poor (6.6), and the best J appears early in the replay only
because a sibling lane (v8) was seeded with the v7 optimum. Read the saving as an upper bound. An
exploration floor and a protected list are required.

**S-C. Bandit over lanes and optimizers.** The reward is the best value found, not the average, so
the right family is the max-K-armed ("extreme") bandit, not ordinary UCB **[literature]**. Arms are
non-stationary and few; with 2–3 seeds it has little to learn from. In replay a simple UCB matched
round-robin and did not beat it.

**S-D. One surrogate over all lanes; the acquisition chooses.** Model the response from canonical
geometry (M4), compute expected improvement per second of solve time for candidates from every
lane, and solve the best. *Idea:* this dissolves "when to switch optimizer or family" into one
decision made per solve; cost-aware acquisition is standard **[literature]**. *Evidence:* a model
trained on other lanes ranks unseen lanes at 0.90–0.96 (M4), and inside a new lane its prior is
worth about 12–16 local solves (rank correlation 0.62 with zero local rows against 0.56 at 8 and
0.64 at 16 local rows) **[measured]**. *Limits:* that evidence is for coverage error only; a
tree model is not a calibrated uncertainty model; sibling lanes inflate the number.

**S-E. Proposer portfolio on a shared log (my suggested answer to "no state migration").**
Treat CMA-ES, TuRBO, scalar BO and a QD emitter as *proposers* that each suggest candidates; one
shared evaluation log feeds all of them; a common scorer (the surrogate from S-D, or simple
credit assignment as in GP-Hedge **[literature]**) picks which proposal to solve. CMA-ES accepts
externally evaluated points by injection, and the BO stack already refits from the log. *Idea:* no
optimizer is ever "switched off"; they compete per solve, so there is nothing to migrate.
*Limits:* CMA's adaptation is disturbed by injected points; the prepared-package model
(`manual_change_invalidates`) assumes one frozen policy per study **[dossier]** and would need a
new study type. Medium-to-high cost.

Constrained and trust-region methods fit inside S-D or S-E rather than replacing them: SCBO
(trust-region BO with constraint models) **[literature]** becomes usable once refusals carry a
signed margin computed on S instead of a binary flag; CMA-MAE **[literature]** is the better QD
emitter if a menu is wanted.

### 4.3 What can be automated safely

| Action | Automation |
|---|---|
| Stop for process, VRAM or solver health | Automatic (exists) |
| Stop a lane for refusals or stall, in noise units, by refusal class | Automatic after the scoring prerequisites; archive-aware for QD |
| Reorder or skip *pending, pre-approved* jobs between jobs | Automatic within a declared budget, with an append-only reason log |
| Choose the next candidate among lanes already approved (S-D, S-E) | Automatic inside a study the owner approved |
| Restart or reseed within the same box and brief | Automatic, counted against the same budget |
| Widen a search bound | Propose only; needs a new versioned config and approval |
| Change brief, envelope, objective version, source model, fidelity | Never automatic |
| Start a new family, or an out-of-envelope probe | Propose only |
| Declare a winner | Never automatic; finalists go to re-solve and the owner |

### 4.4 Discriminating experiments

- **X4, replay with censoring (zero GPU).** Extend the M6 replay to all briefs, with matched
  budgets and each policy's losses reported (lanes it killed that later improved). Pass for
  building S-B: at least 30 % fewer attempts to reach within one noise unit of the best, with no
  eventual top-three lane dropped.
- **X5, shadow acquisition (zero GPU).** For each historical night, let S-D rank the candidates
  that were actually solved that night using only earlier data; measure whether its top quartile
  contained the night's best. This tests the surrogate as a decision-maker without running anything.
- **X6, shadow nights.** Run the chosen supervisor read-only beside real nights for a pre-declared
  period and score its recommendations afterwards.

---

## 5. Direction 3 — intelligent parameter spaces

**P-A. Geometric identifiability (new, cheap, exact).** For any lane, perturb each knob and sample
S: the Jacobian J_ij = ∂S_i/∂θ_j. Its singular values say everything the hand-written activity
tables try to say: a zero column is an inactive knob; collinear columns are coupled or redundant
knobs; the rank is the true geometric dimension; the leading singular vectors are the natural
combined controls. This works for generator and grid families where today's analyzer is
native-only **[dossier]**, and it needs no solve.

**P-B. Acoustic importance from data.** M5 already shows it is learnable: 2–7 knobs carry 90 % of
the importance. Sobol indices and active subspaces can be computed on the *surrogate* rather than
on BEM, which removes the dossier's objection that active subspaces need solver gradients. Sparse
BO priors (SAASBO, BAxUS) **[literature]** are the model-side version for 15–30 knobs.

**P-C. Physically meaningful controls with an inner inverse.** Search in a handful of quantities
defined on S (mouth width and height, depth, H and V wall angle at mid-length, area-growth rate
near the throat, lip radius, section exponent) and let a cheap CPU inner solve find the family
knobs that realize them. M1 and M3 say 6–8 such quantities span what the data contains. *Limits:*
the inverse is many-to-one; the choice among equivalents must be regularized.

**P-D. Bounds from constraints instead of boxes.** Replace hand-set per-typology boxes with
constraints evaluated on S (envelope, throat fit, wall gap, monotone area, minimum curvature
radius) and let the optimizer run in a generous box with those constraints. Pinned elites then
split cleanly into "pinned at a real constraint" and "pinned at an arbitrary box edge"; only the
second kind generates a widening proposal.

*Comparison.* P-A and P-D need only the canonical layer and are the highest value per effort. P-B
needs about 100 rows per lane (most active lanes have them). P-C is the most ambitious and overlaps
with G-B and G-E: if a backbone is adopted, its parameters *are* the meaningful controls.

- **X7 (CPU only).** Run P-A on five lanes; compare its inactive and coupled sets with the existing
  activity ledger and with M5's importance ranking. Pass: it recovers the known no-ops and finds
  at least one undocumented coupling or dead knob.
- **X8 (zero GPU).** Fit P-B on the first half of each lane's rows; check it predicts which knobs
  matter and which bounds pin in the second half.

---

## 6. Direction 4 — transfer learning and reusable acoustic knowledge

### 6.1 What the stored data already supports **[measured]**

| Test | Result |
|---|---|
| Leave one lane out, size only (depth, half-width, half-height) | bw_h error 6.5° (naive 11.0), bw_v 6.0° (naive 14.1) |
| Leave one lane out, size plus H/V wall profiles | bw_h 4.5°, bw_v 4.0°, DI 0.4 dB (naive 1.2) |
| Leave one *engine group* out | Skill R² 0.18–0.53 on bw_h, 0.51–0.71 on bw_v: positive but much weaker |
| Rank designs inside an unseen lane by coverage error | Median rank correlation 0.77 |
| Rank unseen lanes against each other | 0.90 (median) and 0.96 (best decile); 6 of the true top 8 identified |

### 6.2 Techniques, by maturity

**Near-term (weeks, existing data):**
- **Model responses, not J.** Train on beamwidth, DI and impedance curves (or their six principal
  components, M1). Such a surrogate survives every objective change, v7 to v9 included, because J
  is recomputed from predicted curves. Today every surrogate is tied to one objective version.
- **Canonical-geometry surrogate as a prior.** f_lane(x) = g(descriptors of S(x)) + δ_lane(x): the
  shared model g supplies the mean, a small per-lane GP learns the residual. This is the simplest
  form of transfer and needs no multi-task kernel.
- **Similarity augmentation (exact physics).** A solve of a horn at scale 1 is also an exact solve
  of the same shape at scale s over frequencies divided by s. Every stored response therefore
  yields a one-parameter family of training rows for free, and gives the surrogate real coverage in
  size. I have not seen this used in the repo.
- **Seeding by descriptor match.** Start a new family's search from the stored designs nearest in
  descriptor space to the best known responses, instead of from a hand-picked seed. M6 shows seeds
  dominate lane outcomes.

**Mid-term (needs development and validation):**
- **Multi-task GP across lanes** (intrinsic coregionalization) **[literature]**; worth trying only
  if the residual model above leaves structure behind.
- **Physics-informed low-fidelity features.** The one-dimensional horn equation gives throat
  impedance from A(s) alone at negligible cost, a natural low-fidelity partner for the loading
  term; an axisymmetric equivalent solve is a second rung. Combine by co-kriging or simply as input
  features.
- **Better descriptors.** Whole-surface (not two-plane) descriptors, lip and section features,
  wavelength-scaled inputs. The weak engine-holdout result says this is where the next gain is.

**Speculative (research projects):**
- Learned shape embeddings (autoencoders, signed-distance networks, graph or operator networks).
  These need 10⁴–10⁵ examples; Hornfab has a few thousand per brief. Revisit if the dataset grows
  tenfold or similarity augmentation proves to substitute for real solves.

- **X9 (zero GPU).** Redo the M4 tests with whole-surface descriptors, wavelength scaling and
  similarity-augmented rows; add loading and ripple as targets. Pass: engine-holdout skill R² above
  0.6 on both planes.
- **X10 (zero GPU).** Learning curves with and without the prior, extended to J under one fixed
  objective. Pass: the prior saves at least 15 solves per new lane at equal ranking quality.

---

## 7. Direction 5 — exploration beyond the existing envelope

Four things are currently folded into one refusal and should be modelled separately on S:
geometric validity (hard), manufacturability (wall gap, curvature, overhang: constraint functions),
product envelope (a per-brief filter, 600 × 480 × 480 here and unchanged), and acoustic merit.

| Option | Idea | Fit |
|---|---|---|
| E-A. Hard filter (today) | Envelope refuses before solving | Simple; teaches nothing about the boundary |
| E-B. Similarity scan | Rescore stored responses at scaled size (first pass, §5.3) | Free, exact for the scaled shape; the scaled throat no longer matches the driver |
| E-C. Size as a second objective | Pareto front of acoustic error against volume or height | Honest trade-off; needs roughly twice the rows of a scalar search |
| E-D. Small size-indexed archive | Quality-diversity over a coarse grid of mouth width × height (about 5 × 4 cells) | Feasible at 200 solves, unlike today's 324-cell beamwidth archive (10 cells filled) |
| E-E. Targeted probes | Solve a few out-of-envelope shapes where the surrogate predicts the largest gain or is most uncertain, under a new versioned exploratory brief | Most information per solve; needs approval and a DOF ceiling |
| E-F. Novelty search in response space | Reward distance from existing responses (M2 space) subject to validity | Finds genuinely new behaviour; may find useless behaviour |

M1's first component and the first-pass similarity result say the same thing: size mainly buys
low-frequency control, especially vertical. That is a known direction, so the scientific value of
going bigger is modest; the value is in pricing the trade for the owner. E-B then E-D inside the
envelope, with E-E only if the surrogate points somewhere specific, is the economical order.

- **X11 (zero GPU).** Parity-exact similarity scan over all rows, reported as "best achievable
  coverage against height" with the throat caveat stated. Decides whether E-E is worth proposing.

---

## 8. Synthesis: what precedes, complements and follows

**The broader comparison changes my first-pass conclusion in one important way.** The piece with the
most leverage is a **canonical surface layer** (G-A): one sampler from every engine to S, with
descriptors, constraints and Jacobians computed there. It is small, CPU-only, does not disturb any
family, and it is the precondition for four of the five directions: feature modules and backbones
(§3), refusal margins and unified acquisition (§4), geometric identifiability and constraint bounds
(§5), and transfer (§6). I underweighted it before because the dossier framed geometry as "which
representation wins"; the data says the families are worth keeping (M2) *and* that they live in a
shared low-dimensional shape space (M3, M4).

| Stage | Item | Why here |
|---|---|---|
| **Precede** | Scoring prerequisites: grid-invariant J, published noise floor, mesh-error check, corridor decision (R1–R4, with the other agent) | Any A/B of a new geometry and any supervisor acting on J is unreadable without them |
| **Precede** | Refusal taxonomy and envelope classification fixes | Supervisor and constraint models need honest classes |
| **In parallel now** | Canonical surface layer (G-A) with whole-surface descriptors | Independent of scoring; everything else builds on it |
| **In parallel now** | Response-level transfer surrogate with similarity augmentation (§6) | Models curves, not J, so it does not wait for the scoring work |
| **In parallel now** | Geometric identifiability and constraint-based bounds (P-A, P-D) | CPU only; cleans the parameter spaces of existing lanes |
| **Complement** | Lane racing with an exploration floor, first in replay then in shadow (S-B, X4, X6) | Cheap, supported by M6; safe because it only reorders approved jobs |
| **Complement** | Feature modules for H/V authority on the best engines (G-D, X2) | Smallest step that produces shapes Hornfab cannot make today while keeping provenance |
| **Follow** | Unified acquisition or proposer portfolio (S-D, S-E) | Needs a surrogate that is calibrated and tested on J, not just coverage |
| **Follow** | Backbone or mode-space search (G-B, G-E) | Only if the round-trip test X1 passes; otherwise stay with modules |
| **Follow** | Size archive and targeted out-of-envelope probes (E-D, E-E) | After the surrogate can say where to probe |
| **Not now** | Full grammar (G-C), freeform (G-F), learned embeddings | Cost or data requirements exceed the evidence for them |

**Where I am still uncertain.**
- Whether G-D modules have enough authority to close the H/V gap, or whether a backbone (G-B) is
  needed. X2 decides.
- Whether the transfer result survives stricter holdouts and extends to loading and ripple. X9
  decides; the engine-holdout number is the honest warning.
- Whether racing would have dropped a lane the owner cares about. Memory says owner-requested
  families are to be fixed, not cut, so racing must respect a protected list.
- I did not select a single winner on purpose: G-A is an enabler, not a destination, and the choice
  among G-B, G-D and G-E should wait for X1 and X2.

**Experiments at a glance**

| ID | Question | Cost |
|---|---|---|
| X1 | Can a backbone or mode space reproduce existing best designs? | CPU |
| X2 | Do deformation modules move the beam by ≥ 3°? | Zero GPU, then ≤ 12 solves with approval |
| X3 | Do cross-engine combinations mesh? | CPU (mesh only) |
| X4 | Does racing save compute without dropping winners? | Zero GPU |
| X5 | Would a unified surrogate have picked each night's best? | Zero GPU |
| X6 | Shadow supervisor beside real nights | Zero GPU |
| X7 | Does the surface Jacobian find dead and coupled knobs? | CPU |
| X8 | Does first-half importance predict second-half? | Zero GPU |
| X9 | Does transfer hold across engines, and for loading and ripple? | Zero GPU |
| X10 | How many solves does the prior save in a new lane? | Zero GPU |
| X11 | Achievable coverage against height by similarity | Zero GPU |

---

## Sources

- Udawalpola and Berggren, optimization of an acoustic horn for efficiency and directivity; Umeå
  horn shape and topology optimization programme:
  <https://webapps.cs.umu.se/uminf/reports/2010/001/part1.pdf>,
  <https://people.cs.umu.se/martinb/downloads/Papers/KaWaBe12M.pdf>,
  <https://portal.mardi4nfdi.de/wiki/Publication:381891>
- COMSOL horn shape-optimization example:
  <https://doc.comsol.com/6.4/doc/com.comsol.help.models.aco.horn_shape_optimization/models.aco.horn_shape_optimization.pdf>
- Eriksson and Poloczek, Scalable Constrained Bayesian Optimization:
  <https://proceedings.mlr.press/v130/eriksson21a.html>, <https://arxiv.org/abs/2002.08526>
- Fontaine and Nikolaidis, CMA-MAE: <https://arxiv.org/abs/2205.10752>,
  <https://github.com/icaros-usc/cma_mae>
- TuRBO, Hyperband, multi-task BO, active subspaces, pyribs and COCO are cited with identifiers in
  the dossier's `EXTERNAL_EVIDENCE.md` (E5, E9–E12, E4).
- SAASBO, BAxUS, GP-Hedge, max-K-armed bandits, Hicks–Henne bumps and free-form deformation are
  cited from memory as established methods; I did not re-fetch them in this pass.
