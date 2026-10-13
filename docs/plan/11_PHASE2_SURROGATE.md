# 11 PHASE 2: THE SURROGATE

**Not part of the Wave 0 to 3 build. Do not start until CP-7 passes and the dataset has a few thousand records.**

This file exists during phase 1 so that phase 1 builds what phase 2 needs. Section 11 at the bottom is the contract back to phase 1: eight things that must be in place before any of this is reachable. All eight are in the phase-1 task files.

`12_RESEARCH_BASIS.md` section 10 carries the verified literature survey behind this file.

---

## 1. What Collin proposed, precisely

> *"It would be cool to set up an NN based approximation of the system (if possible) that would allow for parallel solving of linear algebra rather than solving differential equations (even if simplified as he described). If the approx is good enough, it could make using genetic much much more efficient."*

**One framing correction.** BEM already converted the differential equation into linear algebra. The solver's time goes into assembling a dense `N x N` complex matrix and running GMRES on it, 51 to 119 iterations per frequency. The network replaces **that linear system**, one layer deeper than described.

**The efficiency argument is right, and quantified:**

| Method | Evaluations wanted | At 4 s per BEM solve | At ~4 ms inference |
|---|---|---|---|
| CMA-ES, 10 dims | 200 to 500 | 15 to 35 min | seconds |
| **NSGA-II, 100 pop x 100 gen** | **10,000** | **11 hours** | **40 seconds** |
| A real Pareto study, several runs | 50,000+ | 2.5 days | 3 minutes |

That is why phase 1 uses CMA-ES and ships NSGA-II as a stub. The algorithm choice is a consequence of the cost per evaluation, and the surrogate is what changes it.

**"Parallel" is right in a precise sense.** One BEM solve fills the card: the operator is `8 * N_dof^2` bytes, 0.5 to 4.6 GB of an 8 GB card, so the GPU does one at a time. Inference is batched by the thousand. The RTX 4070 is a mediocre dense-BEM device and a good inference device.

---

## 2. The accuracy reality check, which decides the plan

Read this before choosing an architecture.

| Verified result | Setting | Error |
|---|---|---|
| B-FNO | 2D and 3D exterior **scattering**, geometry varying | 0.01% to 0.05% rRMSE |
| CLBO (Khan & Yao) | **3D resonant acoustics**, boundary velocity to field | **18.4% relative field error** |
| Plain FNO, per MscaleFNO's benchmarks | 1D oscillatory and Helmholtz | O(1) at a single frequency; 0.7 at Helmholtz L=10 |
| AES 3D loudspeaker FNO **[unverified]** | 3D radiation in air, loudspeaker-like | **0.87 dB at 500 Hz, 5.35 dB at 4 kHz** |

Our metric tolerances are **0.3 dB on DI and 2 degrees on beamwidth**, and the noise floor we are trying to establish is around **0.1 dB**.

**A 5 dB field surrogate cannot rank horn designs.** It could not even resolve the 2.63 dB irreducible diffraction floor the earlier tiling study measured. B-FNO's headline 0.01% is on *scattering*, where the incident field dominates and the scattered part is a correction; radiation is the harder regime and its own authors left it to future work.

Three independent verified sources agree on the direction: accuracy degrades with frequency, and 3D oscillatory acoustics is not yet at design-ranking accuracy. **This is not a reason to abandon the idea. It is the reason the metric surrogate comes first and the field surrogate is staged behind a gate.**

---

## 3. Four architectures, and which to build

| | **A. Metric surrogate** | **B. Learned DtN backend** | **C. Field surrogate (DB-FNO)** | **D. MAD-BNO data synthesis** |
|---|---|---|---|---|
| Maps | design vector to metric curves | boundary Dirichlet to Neumann, on a mesh | boundary geometry to boundary solution | same as B, trained without BEM |
| Replaces | the whole chain | **only the matrix solve** | the whole chain | the training data |
| Smoothness | smooth; spectral bias is not the issue | oscillatory | oscillatory | oscillatory |
| Data | 2,000 to 5,000 records | boundary traces, thousands | 3,000 to 25,600, plus traces | **none**, synthesized from `G(r) = e^(ikr)/4*pi*r` |
| Model | MLP, under 1M params | operator net | FNO, tens of millions | operator net |
| Fails | loudly, against held-out BEM | **loudly**: boundary integral and metrics stay exact | quietly | unknown |
| Integration | new evaluator passed to `search_pareto` | **a fourth `Backend`, nothing else changes** | new evaluator | training script only |
| Delivers | **Collin's stated goal: efficient GA** | a drop-in fast solver | geometry generalization, true inversion | removes the data bottleneck |
| Risk | low | medium | **high** | unknown, unvalidated for our case |
| Build order | **first** | **second** | third | investigate alongside second |

### Why B deserves to be second, not last

Collin's words were *"an approximation of the system that would allow for parallel solving of linear algebra."* A learned Dirichlet-Neumann map is, almost literally, that: same mesh, same boundary integral, same metrics, **only the matrix solve is learned.** MAD-BNO is the published method of that exact shape.

It is also the safest thing to integrate, for a structural reason worth stating plainly. In architectures A, C and D the network's output *is* the answer, so an error in it is an error in the result. In B the network's output is an intermediate, and the exact boundary integral and the exact metric code sit downstream of it. A bad prediction produces a polar that visibly violates physics rather than a plausible wrong number. **It fails loudly**, and in a project whose stated main hazard is confident wrong answers, that is worth a great deal.

It slots in behind `solve/base.py`'s `Backend` protocol as a fourth implementation. Nothing else in `hornlab-search` changes. That is what the protocol was for.

### Why not start with C

Section 2. Also: neither B-FNO nor DB-FNO nor MAD-BNO released code, so C is a from-scratch implementation of a method whose 3D accuracy on radiation is, at best, reported in one paper we could not read.

### Why D is a research question, not a plan item

MAD-BNO is verified to exist and is validated on **2D interior** Laplace, Poisson and Helmholtz. Its abstract page states no error figures, says nothing about exterior domains, and says nothing about varying geometry. Generating artificial data from fundamental solutions for an exterior problem is plausible, since placing sources inside the body is the classical method of fundamental solutions. **But a boundary-to-boundary map on a fixed geometry is a solver, not a design surrogate**, and geometry generalization is unaddressed in the paper. Investigate it as a reading task and a small pulsating-sphere experiment before it is allowed to displace any data collection.

---

## 4. Stage A: the metric surrogate

```
hornlab_search/surrogate/
  features.py   design vector -> model input
  model.py      the MLP, plus a frozen save/load format
  train.py      train, validate, report the gates
  predict.py    a surrogate evaluator with evaluate()'s signature
  gates.py      the acceptance tests, run on every trained model
```

**Input:** the normalized design vector from `DesignSpace.normalize`, already `[0,1]^k` and alphabetically ordered. Add nothing derived at first; a more elaborate encoding has to beat this baseline.

**Output:** per-frequency metric curves on a fixed grid, which is why `to_training_arrays` filters by frequency grid:

```
bw_h_deg, bw_v_deg, di_db, ripple_h_db, ripple_v_db, on_axis_db     each (nf,)
```

**Predict the metrics, not the objective.** Objective weights change constantly; metrics do not. A surrogate trained on the objective is obsolete the moment someone edits a weight, and nothing in this project is edited more often.

**Model:** MLP, `k` in, 3 or 4 hidden layers of 256 to 512, `6 * nf` out, GELU, layer norm, Huber loss on z-scored targets, plus a sigmoid classifier head on `ok`. Hold out 15%, stratified so held-out designs are not near neighbours of training designs. About a hundred lines with `torch`, the `surrogate` optional dependency, not installed in phase 1.

### The gates

Run on a held-out set of at least 500 BEM-solved designs. **Rank correlation, not RMSE:** a search needs to know which candidate is better, not what its exact beamwidth is.

| Gate | Threshold | Why |
|---|---|---|
| Spearman rank correlation, surrogate objective vs true | **> 0.90** | the search must order candidates correctly |
| Overlap, surrogate top-20 vs true top-20 | **>= 12 of 20** | the shortlist handed to real BEM must contain the real winners |
| MAE, beamwidth | **< 2 deg** | below the CP-7c discretization error, so the surrogate is not the limiting factor |
| MAE, DI | **< 0.3 dB** | same |
| Invalid designs correctly predicted invalid | **> 0.85** | so the search does not spend budget on geometry that cannot be meshed |
| **Monotonic consistency** | no sign flips on 50 one-parameter sweeps | a surrogate that says lengthening the horn narrows *and* widens the pattern is not modelling anything |

**If the rank-correlation gate fails, the surrogate is not used.** Report the number, collect more data or improve the encoding. A surrogate that fails its gate and is used anyway produces a search that confidently optimizes the model's errors.

### The free physics test, taken from CLBO

CLBO is **linear in the excitation by construction**, and reports a superposition error of 1.31e-7. Acoustics at our amplitudes is linear, so this is a property we know for free and should test for rather than hope for:

```
predict(u)       vs  measured
predict(2u)      ==  2 * predict(u)          exactly, in linear pressure
predict(u1+u2)   ==  predict(u1) + predict(u2)
predict(0)       ==  0
```

Any surrogate failing these is broken regardless of its RMSE. For Stage A, where drive level is not an input, the equivalent check is that the predicted *normalized* polar is invariant to a drive-level change. For Stages B and C it is the exact test above, and it is the single cheapest correctness check available.

**[inferred]** Better still, enforce it architecturally rather than testing for it. A model that is linear in the drive by construction spends no capacity learning a property we already know, should need less data for the same accuracy, and gets multi-driver superposition exactly right for free, which is precisely what the multi-channel and per-cell-FIR-steering fork needs.

### Active learning is mandatory

A surrogate-driven search that never checks itself optimizes the surrogate's errors. The ISMO loop:

```
1. Train on everything in the dataset.
2. Run NSGA-II on the surrogate. 10,000 evaluations in under a minute.
3. Take the top 30 of the predicted front, plus 10 sampled where the
   surrogate's ensemble variance is highest.
4. Solve all 40 with real BEM. They enter the dataset like any other record.
5. Report: how many of the 40 were actually good, and the surrogate's rank
   correlation ON THOSE 40 specifically.
6. Retrain. Repeat.
```

Step 5 is the honest part and must appear in every report. **If the surrogate's top 30 are not better than 30 random designs, the loop is not working and more iterations will not fix it.**

B-FNO's authors report errors growing near resonance. Our objective cares most about exactly the frequencies where a surrogate is least accurate. That is the specific reason active learning is not optional here.

---

## 5. Stage B: the learned Dirichlet-Neumann backend

The lowest-risk way to deliver what Collin described.

```python
class LearnedDtNBackend:
    """A fourth Backend. Same protocol as beat.py and bempp.py.

    solve():
      1. read the mesh and its structured surface grid
      2. build the prescribed source field on tag 2 (SD1D1001) for each
         frequency, per section 6
      3. network: boundary Dirichlet data -> boundary Neumann data
      4. EXACT boundary integral -> pressure at the observation points
      5. return a Response, identical in shape to the BEM backends
    """
```

Step 4 is exact and **is not learned.** `hornlab_bempp_bem.evaluate_exterior_from_traces` already does it; phase 1's task 05 exposes it for this reason.

Why this is the testable integration:

- Every downstream check still applies unchanged: the analytic pulsating sphere, the symmetry test, the metric closed-form tests, the DI-versus-beamwidth cross-check. A learned backend that passes CP-7a through CP-7e is a learned backend you can trust.
- It can be benchmarked directly against `beat_cuda` on the same mesh, which is what CP-7b already does for two solvers. Adding a third is one config value.
- It degrades visibly. The boundary integral will not turn a wrong boundary solution into a plausible polar.

Its training data is boundary traces, which is why trace capture moves into the phase-1 contract.

---

## 6. Frequency encoding: the one thing to get right

B-FNO's **verified** finding: frequency is encoded **implicitly through the incident pressure field on the boundary**, not as a scalar channel, and the scalar-channel version performed worse.

Our analogue is the **prescribed source field on the driver tag**. For a velocity-driven throat, that is the complex normal velocity distribution on tag 2 (`SD1D1001`) at each frequency. The model sees that field as an input channel; it never sees a number called "frequency".

This has a consequence for phase 1: **we must record what the source field was.** A dataset that records only the frequency list cannot be used to train a model with this encoding, and the records cannot be repaired after the fact. `01_CONTRACTS.md` section 13 now carries an `excitation` block on every row for exactly this reason.

If the driver is later modelled with a real impedance rather than a uniform velocity, the source field becomes frequency-dependent in a physically meaningful way, which is what DB-FNO's reported frequency-dependent-boundary-condition handling is for.

---

## 7. The input representation, probably already solved

FNO needs a **structured grid** with meaningful periodicity. An unstructured triangle soup does not have one, and that is the usual reason neural operators on arbitrary 3D surfaces are hard. B-FNO handled it by reshaping boundary data into 2D arrays by hand, for example 61x80 and 144x114, then lifting to a latent dimension of 64.

**`hornlab_mesher` already builds on a structured point grid.** Its config exposes `angular_segments` (default 64) and `length_segments` (default 32) as the sampling of the fitted surface, plus `preserve_grid`, and its internal modules are named `profiles.build_point_grid` and `geometry.PointGridHornGeometry`.

**[inferred]** That is an `angular x length` tensor on the horn boundary, with the **azimuthal axis naturally periodic**, which is exactly what a Fourier layer assumes. If that grid is reachable through the mesher's API, the hardest data-engineering problem in building an acoustic neural operator is already solved by the geometry layer we were going to use anyway.

Task 02 now checks this. If it is accessible, the input representation is settled. If it is not, it is a feature request to Collin, not a research problem.

---

## 8. Stage C: the field surrogate, the research arm

Only after Stage A works, Stage B is benchmarked, and the dataset is large. This is where the publishable novelty is, because B-FNO's authors state in print that **radiation problems are future work**, and DB-FNO reportedly addresses them.

**The highest-value single literature action in the project is reading DB-FNO properly.** It either narrows that gap or confirms it, and it is one paper. ScienceDirect and SSRN both refused automated fetch, so this needs institutional access or an email to the authors.

Expect 10,000 to 25,000 records, tens of millions of parameters, and spectral bias as the central difficulty, worse near resonance. If high-frequency accuracy is the blocker, **MscaleFNO's parallel-rescaled-subnetwork trick is the first thing to try**: it is MIT-licensed real code, and it reduced plain-FNO error by factors of 20 to 10,000 on 1D oscillatory problems. Porting a 1D method to 3D is work, but it is engineering work against a published, coded method.

Build on `neuraloperator` (MIT, ~4k stars, `pip install neuraloperator`). It provides FNO and Tucker-factorized TFNO, whose README claims 10% of a dense FNO's parameters. **Do not reimplement an FNO.** Neither B-FNO, DB-FNO nor MAD-BNO released code, so the generic library plus the papers' architectural decisions is the route.

---

## 9. Stage D: inversion, which is the actual goal

A trained surrogate is **differentiable by construction.**

Phase 1 asks: *given this geometry, what is the response?* Then it searches. Inversion asks: *given this response, what geometry produces it?* Freeze the weights, make the design vector the variable, descend on `|predicted - target|` with respect to the input. Milliseconds per start, so run a thousand starts and collect every distinct basin.

```python
def invert(model, target_curves, n_starts=1000, steps=300) -> list[Design]:
    """Candidate designs, deduplicated, each with its predicted residual AND
    its distance to the nearest training point. Verify every one with real BEM."""
```

**It is not a faster search. It is a different operation.** A search samples and keeps the best thing it happened to try. Inversion solves for the input directly, and because it is cheap it returns the whole set of distinct geometries producing a given response. Two very different horns with the same polar is a genuinely interesting result and only inversion finds it.

Three caveats that are not negotiable:

1. The surrogate is valid only where it has data. **Report the distance to the nearest training point for every inverted candidate** and treat a far one as a hypothesis.
2. The problem is ill-posed by design, so the residual alone does not rank candidates. Add a manufacturability or size term.
3. **Every inverted design is verified with real BEM.** Always. An unverified inverted design is a picture, not a result.

The precedent is verified: arXiv 2302.01934 does exactly this, a modified FNO surrogate for EM scattering driving gradient-based nanophotonic inverse design.

---

## 10. The verification checklist

Answer each before the corresponding stage is built. Adapted from the survey, with the items its own evidence does not support removed and four added.

| # | Question | Why it matters | How |
|---|---|---|---|
| 1 | **Is DB-FNO's radiation result real, and at what accuracy?** | It is the only reported 3D acoustic radiation operator result. It either narrows our novelty gap or confirms it. | Get the J. Sound Vib. paper through institutional access, or email Li, Ye and Liu. Record the rRMSE, the cases, and whether geometry varied. |
| 2 | **Is any of this code available?** | Avoid reimplementing. | B-FNO, DB-FNO and MAD-BNO show no public repos. Check the HKUST thesis repository; email the authors. `neuraloperator` and `yyc-rgb/MscaleFNO` are MIT and real. |
| 3 | **Is the mesher's structured point grid reachable?** | Decides the entire input representation. Section 7. | Task 02 discovery item. One question to Collin if the API does not expose it. |
| 4 | **Can `surface_traces` be captured, and at what disk cost per design?** | Every boundary method needs them, and they cannot be recovered later. | Task 02 capability check C2b; task 07 measures the disk. |
| 5 | **What is the driver's prescribed source field as a function of frequency?** | It is the frequency-encoding channel. Section 6. | Read how `SD1D1001` excitation is defined. Decide uniform velocity versus an impedance-derived distribution, and record it on every row. |
| 6 | **Does MAD-BNO generalize across geometries?** | A fixed-geometry DtN map is a solver, not a design surrogate. | Read the paper in full. Then the cheap experiment: a pulsating sphere at three radii, trained MAD-style, tested on a fourth. |
| 7 | **Does a surrogate obey superposition?** | Free exact test, catches a broken model that RMSE passes. | Section 4. Run it on every trained model, every stage. |
| 8 | **Does the surrogate generalize across geometry families?** | Train on OSSE, test on R-OSSE or ICW. B-FNO varied geometry; ours must too. | Requires multi-family sampling in the dataset, which task 07 now specifies. |
| 9 | **What is the real training-data generation cost on this hardware?** | The 11-hour estimate rests on 4 s per screening solve. | Task 02's M3. Measure, do not assume. |
| 10 | **What does the boundary integral recovery cost relative to inference?** | If recovery dominates, a learned DtN map buys less than it appears to. | Benchmark `evaluate_exterior_from_traces` on a known case. |
| 11 | **Does the surrogate need the interior FEM region?** | The throat may need coupled FEM-BEM. | Determine whether we stay exterior-only. Phase 1 is exterior-only, so this only arises with MEH. |
| 12 | **What is inference latency on this GPU?** | The 4.2 ms figure is someone else's hardware. | Benchmark after training. |

---

## 11. The contract back to phase 1

Eight things phase 1 must deliver. **All eight are already in the phase-1 task files.** Nothing here requires changing phase 1 later.

| # | What | Where in phase 1 |
|---|---|---|
| 1 | A dataset of (design, response) pairs written from run one, failures included | task 07, Wave 1 |
| 2 | A frozen, retrainable record schema with `lib_shas` on every row | `01` section 13 |
| 3 | `to_training_arrays`, with frequency-grid filtering | task 07 |
| 4 | **Boundary trace capture** on a sampled fraction of designs | `01`, task 02 C2b, task 05, task 07 |
| 5 | **The excitation spec recorded on every row** | `01` section 13 |
| 6 | **Trace-to-field recovery exposed as a function** | task 05 |
| 7 | A `Backend` protocol a learned solver can implement | task 05 `solve/base.py` |
| 8 | `search_pareto(cfg, run_dir, evaluator)` taking the evaluator as an argument | task 08 `search/nsga.py` |
| 9 | **Multi-family dataset sampling**, so generalization is testable | task 07 |

### The one-sentence answer for Collin

Yes, and there are two versions: the small one is an MLP from the design vector to the metric curves, gated on rank correlation rather than RMSE, which makes NSGA-II affordable and is what you actually asked for; the closer-to-your-description one is a learned boundary Dirichlet-to-Neumann map that replaces only the matrix solve and keeps the exact boundary integral downstream, which drops in as a fourth solver backend and fails loudly instead of quietly. The search we are building generates the training data for both as a byproduct.

---

## 12. Forks within phase 2

| Fork | Difficulty | Value | Notes |
|---|---|---|---|
| **Enforce complex-linearity in the drive architecturally** | low | **high** | From CLBO, which reports superposition error of 1.31e-7 by construction. Free correctness, less data needed, and exact multi-driver superposition, which the per-cell-steering fork needs. |
| **Uncertainty estimates** | low | **high** | An ensemble of 5 MLPs or MC dropout. Required for the variance-sampling step of active learning, and it tells you when an inverted design is a hallucination. |
| Classifier head on validity | low | high | The dataset already records failures, which is why task 07 insists on it. Saves a large fraction of a search's budget. |
| **Multi-fidelity surrogate** | medium | high | Train on cheap `screen` labels, correct with scarce `verify` labels. Task 08's multi-fidelity-promotion fork generates exactly this pairing for free. |
| Rayleigh pre-screen as a physics prior input | medium | high | A surrogate given a physically informed prior needs far less data than one learning from scratch. |
| **MscaleFNO's rescaled sub-networks** | medium | high if Stage C stalls | MIT code, real, but 1D only in the paper. The first thing to try if high-frequency accuracy is the blocker. |
| TFNO Tucker factorization | low | medium | In `neuraloperator` already; claimed 10% of a dense FNO's parameters. Matters on an 8 GB card. |
| SDF or point-cloud geometry encoding | high | **high** | What lets one model generalize across families instead of one per family. The route to searching shapes rather than parameter sets. |
| B-FNO or DB-FNO on boundary traces | high | **the publishable part** | Radiation rather than scattering is unclaimed in print. Needs Stage C's data and item 1 of the checklist answered first. |
| MAD-style synthetic training data | high | unknown, potentially large | Removes the data bottleneck if it works for exterior radiation with varying geometry. Neither is demonstrated. Investigate, do not plan around. |
| Diffusion or VAE generative inverse design | high | unknown | Works in photonics. Premature until a model passes its gates. |

---

## Sources

B-FNO, Engineering with Computers 41(4):2393-2410: https://link.springer.com/article/10.1007/s00366-024-02103-x
DB-FNO, Journal of Sound and Vibration: https://www.sciencedirect.com/science/article/abs/pii/S0022460X26003792
DB-FNO preprint on SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5572813
MAD-BNO: https://arxiv.org/abs/2601.11222
MscaleFNO paper: https://arxiv.org/abs/2412.20183
MscaleFNO code, MIT: https://github.com/yyc-rgb/MscaleFNO
Quadrature-aware complex-linear neural operator (CLBO): https://arxiv.org/abs/2607.04407
neuraloperator library, MIT: https://github.com/neuraloperator/neuraloperator
Neural operator surrogate for free-form electromagnetic inverse design: https://arxiv.org/abs/2302.01934
Data driven surrogate modeling of horn antennas: https://onlinelibrary.wiley.com/doi/abs/10.1002/mop.33702
Neural-operator surrogates for outdoor acoustics, JASA: https://pubs.aip.org/asa/jasa/article/160/3/2653/3405543/Neural-operator-surrogates-for-outdoor-acoustics
