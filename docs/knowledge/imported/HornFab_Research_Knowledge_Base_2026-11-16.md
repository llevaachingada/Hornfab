---
title: "HornFab research knowledge base: horn geometry, acoustics, optimization and numerical methods"
project: "llevaachingada/Hornfab"
created: "2026-11-16"
purpose: "Searchable reference and evidence map for local software-development agents"
format_version: 1
status: "research synthesis; not a software implementation specification"
github_repo: "https://github.com/llevaachingada/Hornfab"
github_reference: "main as inspected 2026-11-16, git tree 2c0e2928e932a47975fc284401eafa74ebfc5002"
search_tags:
  - horn
  - waveguide
  - JMLC
  - LeCleach
  - Iwata
  - Keele
  - biradial
  - Crowe
  - OSSE
  - ROSSE
  - ATH
  - Tritonia
  - Klangfilm
  - Lame
  - MEH
  - Synergy
  - Solana
  - SAWMOD
  - BEM
  - FEM
  - GMRES
  - FMM
  - high-frequency
  - BoTorch
  - CMA-ES
  - TuRBO
  - Pareto
  - scoring
  - directivity
  - loading
  - driver
  - source
  - GUI
---

# HornFab: consolidated horn research and source library

**Research snapshot: 16 November 2026. Intended reader:** local OpenCode, Claude, Codex, Fable and research agents building `llevaachingada/Hornfab`. **Read this as an annotated, searchable evidence index, not as authorization to alter code, scoring or active GPU jobs.**

**Scope and disclosure.** Synthesized from the accessible Horns project-chat context, the attached research summaries, the live GitHub `main` repository and its research/evidence documents, and independently checked web sources. A few prior artifacts named in chat were only available as *links or summaries*, not original bytes; those are **not** claimed as read. Likewise, the available project-history context is extensive but does not prove that every historical chat was recoverable. GitHub is a moving target: re-check paths, commit identity and test output before implementing an older recommendation. The full text of a paywalled article is **not** included or implied to have been read merely because its abstract or DOI was checked.

## How an agent should use this file

1. Search for a term or tag: `JMLC`, `beamwidth target`, `di_slope_target`, `R-OSSE`, `ESP`, `FMM`, `Solana`, `BoTorch`, `out-of-envelope`, `phase plug`, etc.
2. Read the relevant **finding**, then the linked **primary paper / full PDF**, then the linked **HornFab research dossier**, then **current implementation and tests**.
3. Check evidence labels. Do not turn a proposed geometry knob, a paper's idealized result, an old agent claim or a historical benchmark into an established feature.
4. If making a code change, record which objective/brief/source/geometry/mesh/backend/frequency grid and commit were used. Preserve earlier observations.
5. Prefer a small controlled A/B with a physical acoustic observable over another speculative scorer or giant search.
6. Never mix objectives or compare their scalar `J` numbers as though they measure the same thing; compare physical metrics under common boundary conditions first.
7. Never infer full-band acoustic quality from a render, low-fidelity screen or ideal uniform-throat source.

### Evidence tags used

- **[P]** Primary publication, technical paper, patent, author script or direct manufacturer source, with explicit boundaries on what it proves.
- **[R]** Observed in HornFab repository files or recorded benchmarks on the inspected snapshot. Not independently rerun here.
- **[C]** Evidence or decision carried over from recoverable project discussions and the attached research documents. Check against current code.
- **[I]** Synthesis/inference/hypothesis; requires a test.
- **[X]** Contradicted, outdated, unsupported or important to correct.
- **[ACCESS]** Full text is paywalled/unavailable or an earlier artifact was only a pointer. Link is a landing page or an author's note, not an asserted freely accessible full PDF.

A short reading path for a new agent: [Horn white-paper bibliography](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/HORN_WHITEPAPERS_2026-11-15.md), [four-family acoustic design review](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md), [JMLC construction](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md), [objective glossary](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/LOADING_OBJECTIVES_RECONCILED_2026-11.md), [search-math dossier](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/SEARCH_MATH_DOSSIER_2026-11.md), and [high-frequency numerical work](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/senior_pass_2026-10-24/03_HIGH_FREQUENCY_12KHZ.md).

---

## 1. Research findings that should actually change HornFab decisions

### F01 [scoring][typology][critical] A horn's intended directivity behavior is part of the design brief, not an incidental label

**Result.** Traditional exponential, tractrix, Le Cléac'h/JMLC and some ES-style horns generally become more directional as frequency rises. CD-oriented OSSE, R-OSSE, Keele-inspired or tuned hybrid horns attempt flatter beamwidth/DI over some range. None should be penalized for failing an objective it did not intend to meet.

**Scoring truth [R]:** HornFab v7's basic `cov` term compares measured H/V -6 dB beamwidth to fixed target angles; its `di` term compares DI to a fixed target level; its `dislope` term compares measured DI slope to `target.di_slope_target`. Merely setting `di_slope_target` to a nonzero number **does not** make the `cov` beamwidth curve slope, and it need not resolve the fixed-`di` penalty. Inspect `hornlab_search/objective/scalar_v7.py`, `objective/terms.py`, the actual selected YAML and the *resolved per-row scoring target*. The historic `SCORING_NON_CD_SOURCES` report expressly warns that target values stored per row can override an offline brief.

**Action [I]:** Add an explicit `directivity_intent` and independently inspectable *target-vs-frequency* H/V beamwidth curves, DI trajectory, loading targets and non-CD acceptance zones in the GUI. Distinguish desired **sloped DI** from desired **sloped H/V beamwidth**. A schematic sloped line without a matching mathematical score is deceptive. Define and test target generation for each family. Keep historical v4/v6/v7 intact pending a versioned, verified migration.

Primary: [Gu, You & Shen 2025, rectangular horn optimization](https://doi.org/10.1121/10.0039253), [Sridhar et al. 2019, generalized directivity metrics, full PDF](https://oar.princeton.edu/bitstream/88435/pr12s1j/1/Generalized%20metrics%20for%20constant%20directivity.pdf), [Fourcade 2015 full PDF](https://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf). Repo: [non-CD target audit](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/SCORING_NON_CD_SOURCES_2026-11-15.md), [v6 loading objective](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md), [loading glossary](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/LOADING_OBJECTIVES_RECONCILED_2026-11.md).

### F02 [physical objective][critical] Loading onset, pattern-control onset and crossover are not synonyms

**Result [P].** A horn can have a useful real component of acoustic throat impedance below the frequency where its nominal coverage is stable, while the complete speaker's crossover depends on the adjacent woofer, filtering and spatial summation. Likewise, a published nominal driver minimum crossover is not evidence that an arbitrary horn can maintain the target beamwidth there.

**For the HF1440 home example [C/R]:** the 35.8 mm FaitalPRO exit and 0.7 kHz published minimum crossover support *considering* ~700 Hz, but do not prove satisfactory waveguide loading, directivity or distortion at 700 Hz. The 80° H × 50° V brief, 600 × 480 × 480 mm production envelope and 350–8000 Hz objective/screen band should be considered product/study assumptions, not a universal loudspeaker optimum. A 350 Hz lower scoring limit must not accidentally penalize expected sub-crossover roll-off in an on-axis term.

**Action.** Store separate `f_load`, `f_pattern_control`, `f_crossover_system`; label how each was inferred/solved/measured. Do not equate ATH's low-frequency throat-resistance markers with CD onset.

Sources: [ATH Extended-Throat technical note](https://at-horns.eu/exar-story.html), [FaitalPRO HF1440 product](https://faitalpro.com/en/products/HF_Drivers/product_details/index.php?id=502020185), [On-axis weighting audit](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/ONAXIS_WEIGHTING_2026-11-14.md).

### F03 [beamwidth][size] The 80 × 50 at 700 Hz envelope is a trade-off, not an established achievable ideal

**Result [R/P].** The repo's corrected approximate Keele Bi-Radial mouth-sizing heuristic is `W ≈ 25,000 / (0.9 · full_angle_deg · f_hz)` in metres. At 700 Hz it suggests about **496 mm for 80° H**, but **794 mm for 50° V**. The 480 mm V production limit may therefore constrain low-frequency vertical pattern control. This is a *patent-derived engineering heuristic*, not an immutable diffraction bound or a substitute for solving the actual three-dimensional source, baffle and enclosure.

**Action [I].** Run a bounded envelope-relaxed acoustic-discovery study and save the acoustics of physically valid oversized horns, then examine performance-versus-size Pareto trade-offs. Product/manufacturing fit remains a separate constraint. Do not reduce real meshes by assuming a larger horn can simply be uniformly shrunk around an unchanged 36 mm driver.

Sources: [Keele Bi-Radial patent US4308932A](https://patents.google.com/patent/US4308932A/en), [HornFab corrected biradial sources](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/BIRADIAL_CROWE_SOURCES_2026-11-15.md).

### F04 [constraints][optimizer] A search-space refusal is not an acoustic observation

**Result [R/C].** Geometry generation, `GeneratedSpace.design_from_knobs`, candidate-pool admission and `search/evaluate.py` historically refused certain out-of-envelope candidates before BEM. Such candidates may get a penalty around 1000, not an actual pressure/impedance measurement; BoTorch cannot learn the underlying acoustics of a rejected geometry from that pseudo-score.

**Action [I].** Distinguish `physical_invalid` (self-intersection, nonmanifold, impossible throat, impossible mesh), `computational_budget` (GPU/CPU memory and time cap), `product_envelope` and `parameter_domain`. Support distinct envelope policies for **exploration** versus **production**, with explicit admission accounting. Keep physical impossibilities hard. For normalized `X`, store the original physical parameters and bounds; never reinterpret historical `[0,1]^d` coordinates under new bounds.

Sources: [reviewed envelope audit in attached research], [candidate materialization](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/bo/data.py), [evaluator](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/search/evaluate.py), [early-rejection replay](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/EARLY_REJECTION_REPLAY.md).

### F05 [scoring][data] Scoring can change without re-solving existing physical responses

**Result [R].** The project stores acoustic response arrays and maintains solver caching separately from scoring. Its v6/v7 re-score tooling demonstrates objective changes without new BEM solves. The November 12 experimental v8 re-score reportedly processed 23,833 rows, but v8 was then unregistered/experimental and cannot be assumed current default.

**Critical qualification.** A new *target* can change frequency-dependent ripple and other derived metrics, so recompute target-dependent descriptors from raw response rather than merely multiplying old term values by new weights. Require data identity (geometry, source, physical boundary, solver hash, mesh hash, frequency grid, observation sampling) and immutable score provenance. A new band or spatial resolution may require actual new solves.

**Action.** Universal offline re-scoring, score tables keyed by objective and target, provenance checks, dataset/backups and replay equivalence tests should precede expensive campaigns. Do not overwrite historical rows.

Repo: [solve cache](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/solve/cache.py), [dataset identity](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/dataset/identity_v2.py), [rescore script](https://github.com/llevaachingada/Hornfab/blob/main/tools/rescore/rescore_v6_v7.py), [v8 proposal](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/OBJECTIVE_V8_PROPOSAL_2026-11-12.md), [preservation plan](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/NEXT_QUEUE_PLANNING_HANDOFF_2026-11-12.md).

### F06 [source][driver] An ideal uniform throat velocity is not a real compression driver

**Result [P].** At elevated frequencies the driver/phase-plug exit's actual velocity and modal distribution matters. Makarski and Behler specifically studied this issue. An ideal prescribed-velocity BEM can compare horns under a standardized source, but cannot by itself prove the response of an HF1440, HF1460, TAD, or real phase plug. A circular-duct first-mode cutoff estimate is only a mode cut-on estimate, not a universal real-driver hard failure frequency.

**Action [I].** Maintain separate evidence tiers: `ideal-source`, `driver-informed`, `full electroacoustic system`, `prototype measured`. Future study: modal-source basis or measured exit velocity + calibrated driver impedance; do not invent an exit half-angle from an unsupported datasheet. The HF1440's published “Combined Exit” with radial phase plug is not a published 2-degree exit geometry. Old configurations using 2° are modeling assumptions, not verified product geometry.

Sources: [Behler & Makarski 2004 AES paper](https://aes.org/publications/elibrary/elibrary-page/?id=12743), [2026 CutFEM compression driver article, open access](https://doi.org/10.1002/nme.70284), [throat coupling dossier](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/THROAT_COUPLING_2026-10-27.md).

### F07 [full balloon][metrics] Two cuts and an outermost -6 dB width are insufficient to judge a horn

**Result [R/P].** The repo's `metrics/polar.py` uses the outermost -6 dB crossings; disconnected lobes can masquerade as a wide main lobe, and “no crossing” sentinels require independent flags. H/V cuts cannot uniquely determine a full 4π directivity index. Distinct 3D patterns can share identical H/V beamwidth.

**Action.** Save main-lobe connectedness, sidelobe levels, 45° diagonals, contour area, angular ripple inside a listening window, full-balloon DI where actual spherical sampling exists, polar correlation, and properly labeled two-cut DI estimates. In the GUI, show beamwidth/isobars with the *resolved exact scoring targets* and confidence/coverage masks. Do not silently equate a predicted balloon interpolation with a solved balloon.

Sources: [Sridhar/Tylka/Choueiri full PDF](https://oar.princeton.edu/bitstream/88435/pr12s1j/1/Generalized%20metrics%20for%20constant%20directivity.pdf), [metrics implementation](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/metrics/polar.py), [HornFab scoring research](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/HORN_WHITEPAPERS_2026-11-15.md).

### F08 [mounting][baffle] Free-standing horns and cabinet-mounted horns are different acoustic experiments

**Result [P].** The 2024 JASA finite-enclosure multimodal study shows enclosure diffraction can change low-frequency beamwidth and sometimes extend CD bandwidth. An infinite baffle, thin flange, free-standing rolled mouth, and finite cabinet are different radiation boundary problems.

**Action.** Freeze mounting scenario for comparing candidate waveguides; test finalists in their intended baffle/box. Avoid pooling acoustics across incompatible physical setups. For finite cabinets include geometry, edge rounding, woofer spacing, crossover and polar handoff.

Sources: [Dong, Doc & Félix 2024, author-hosted full PDF](https://univ-lemans.hal.science/hal-04798282/document), [DOI](https://doi.org/10.1121/10.0025389), [ATH TwinRay edge-roundover study](https://at-horns.eu/img/twinray/bem/roundover-study.html).

### F09 [mesh][HF] More angles or additional polar samples do not fix an under-resolved boundary mesh

**Result.** Accurate far-field angles are relatively cheap *after* obtaining valid boundary pressures, but the BEM mesh still must resolve physical surface oscillations at the requested frequency. Increasing `f_max` increases necessary degrees of freedom and can sharply increase dense solver memory. Reducing the number of observation directions doesn't remove the BEM matrix cost. A partial sphere can diagnose particular cuts or regions but cannot supply a valid full-sphere power integral/DI without a validated reconstruction.

**Action.** Separate independent convergence axes: mesh EPW/local curvature, frequency density, boundary-condition/source model and observation sampling. Test denser **frequencies at fixed mesh** and finer **mesh at identical frequencies** to explain screen-to-verify ranking reversals. Use region/curvature-aware meshes, throat refinement, and explicit high-frequency acceptance gates.

Sources: [NumCalc open-access paper](https://doi.org/10.1016/j.enganabound.2024.01.008), [Mesh2HRTF](https://mesh2hrtf.org/), [HornFab high-frequency review](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/senior_pass_2026-10-24/03_HIGH_FREQUENCY_12KHZ.md), [mesh audit](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/REAR_DENSITY_MESH_AUDIT_2026-11-13.md).

### F10 [throughput][CUDA] Existing speed wins should be preserved; Bayesian search does not make a BEM solve faster

**Result [R].** On RTX 4060 8 GB, the November 12 *representative* fused-CUDA/12-frequency warm benchmark reported ~1.273 s at ~1k DOF, ~8.488 s at ~4k, ~25.0 s at ~8k. Frequency batching helped; the fused matrix assembly path dominated some measured scenarios. These are **specific benchmark cases**, not universal solves/hour for arbitrary horns. BoTorch changes the number/selection of geometries, not the numerical physics workload of one acoustic solve.

**Action [I].** Prioritize measured wall-clock outcomes: precompute or reuse mesh/solver context where correct, audit avoidable dense allocations, pipeline CPU mesh preparation with serial GPU operations without contention, use frequency batches and controlled rear coarsening. For much larger high-frequency meshes study matrix-free GMRES, Burton–Miller stabilization, FMM/ML-FMM, preconditioning and external reduced-order proposal models. Do not assume a blanket free 20 kHz solution.

Repo: [throughput ledger](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/THROUGHPUT_N1_2026-11-12.md), [speed adoption](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/SPEED_ADOPTION_2026-11-14.md), [matrix-free research](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md).

### F11 [multimodal][adjoint] Physics-informed proposal models are a real alternative to full BEM on every candidate

**Result [P].** Dong et al. (2020/2021), Gu et al. (2025), and older FEM/BEM adjoint optimization literature demonstrate efficient shape optimization for restricted horn classes. The 2025 rectangular-horn work explicitly combines efficiency, directivity and smoothness. Schmidt/Wadbro/Berggren (2016) optimized a 3D midrange horn using 1,762 shape variables in a large parallel computation.

**Boundary.** A 1D Webster model, short-cylinder axisymmetric multimodal method or simple modal reduced model will **not** automatically represent arbitrary Lamé/X-sculpted non-axisymmetric horns, full mouth diffraction, several coupled drivers or a real cabinet. Such a model is a *proposal/screening fidelity*, benchmarked against full BEM, not a magically equivalent full solve.

**Action [I].** Prototype a restricted-axisymmetric or rectangular multimodal physics surrogate, calibrate errors and rank agreement versus high-fidelity BEM, and only then consider differentiated multi-fidelity allocation/adjoint development.

Sources: [Dong 2020 PDF](https://asa.scitation.org/doi/pdf/10.1121/10.0001037), [Dong 2021](https://doi.org/10.1121/10.0003568), [Gu 2025](https://doi.org/10.1121/10.0039253), [Schmidt et al. 2016 full PDF](https://people.cs.umu.se/martinb/downloads/Papers/ScWaBe16.pdf).

### F12 [BoTorch][CMA] Compare optimizers at equal *verified* physical cost, with admission differences explicit

**Result [R].** A November 15 HornFab study reported median **verify J** 3.189 (BoTorch) vs 3.827 (CMA) with 3 seeds/arm, 60 new screen evaluations + 6 verifies per arm, on a warm-started OSSE extended-throat task. BoTorch used 185 prior observations and a pre-screened 4096-design pool, with 0–3 refusals vs 14–29 for CMA. This is a real *task-level* reported win, not proof that BoTorch generally beats CMA across typologies, dimensions and objective functions. Because admission filters differed, comparisons also measure candidate feasibility management.

**Action.** Paired seeds, common new BEM budget, separately report pre-screened/refused counts, fixed solver/fidelity/source, verified best-of-run, Pareto coverage and wall-clock cost. Compare CMA with warm starts/restarts/LQ, constrained BO, TuRBO and QD; avoid single-result marketing.

Sources: [HornFab BO vs CMA report](https://github.com/llevaachingada/Hornfab/blob/main/docs/status/2026-11-15-bo-vs-cma/README.md), [TuRBO paper](https://arxiv.org/abs/1910.01739), [BoTorch tutorial](https://botorch.org/docs/tutorials/turbo_1), [search-math dossier](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/SEARCH_MATH_DOSSIER_2026-11.md).

### F13 [Pareto][atlas] Preserve multiple excellent horns rather than collapsing everything into one J winner

**Result [P/R].** A horn with the best DI uniformity can be worse in loading, size, response roughness or sensitivity. CMA-ME/CMA-MAE and multi-objective BO provide different ways of collecting high-quality, diverse candidates. Current BoTorch Pareto code in HornFab was initially focused on **coverage error and ripple**; that is not automatically an acoustic-loading-versus-size frontier.

**Action.** Maintain common physical descriptors and explicit Pareto vectors: beamwidth shape, DI trajectory, loading onset, axial and windowed smoothness, crossover matching, product envelope, printability, solve cost and validated noise/resonance flags. Use comparable normalized metrics, not raw J from different objective families. Version both the Pareto definition and its reference point.

Sources: [BoTorch multiobjective docs](https://botorch.org/docs/multi_objective), [QD paper index](https://quality-diversity.github.io/papers.html), [BoTorch pareto module](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/bo/pareto.py).

### F14 [ATH][pucker] ATH Tritonia's azimuthal law is not an axial-only X-shaped ripple

**Result [P/R].** ATH Tritonia varies opening/termination **by polar angle around the throat**, then morphs the cross section. Historical HornFab “pucker” experiments that modulated only `z` are legitimate novel geometries but are **not** reconstructions of that published radial mechanism. Merely reversing the axial sign does not fix the distinction. X-shaped creases may be artifacts of a round-to-rectangle morph, and their acoustic benefit must be established by solved diagonal polars.

**Action.** Keep provenance between genuine radial ATH-inspired features, axial section relief, spiral ridges, visual bow-tie controls and rolled termination. Compare smooth parent, constrained sculpting-only stage and limited joint refinement. Test parameter activity and self-intersections before allocating GPU.

Sources: [ATH Tritonia](https://at-horns.eu/tritonia.html), [ATH OS-SE PDF](https://at-horns.eu/release/OS-SE%20Waveguide.pdf), [HornFab correction dossier](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md).

### F15 [JMLC][geometry] Exact Le Cléac'h construction and H/V Le Cléac'h-inspired surfaces are different objects

**Result [R].** The repo's Fourcade 2015 dossier uses his equations 10–27, corrects the **included throat exit angle versus half-angle** convention, and reports close reproduction of the published reference (400 Hz, T=0.8, 25.4 mm, 8° included). The later `lecleach_swept_hv` / Lamé variants evolve H/V dimensions independently and therefore represent *new derived 3D geometries*, not exact published JMLC solutions.

**Action.** Preserve an exact axisymmetric reference as a validation fixture, then evaluate H/V morph as a separately versioned derived family with 3D BEM. Never combine independent H and V one-dimensional predictions as though they were a 3D wavefront solution.

Sources: [Fourcade full PDF](https://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf), [JMLC study](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md), [dual Lamé gate](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/DUAL_LAME_INTEGRATION_2026-11-16.md).

### F16 [MEH][coupling] Multiple entry horns are *complete coupled systems*, not several ideal sources on one empty shell

**Result [R/C].** HornFab contains legitimate multiple-source exterior BEM and separate lumped network/driver elements, but prior MEH/Funktion-One review found missing physical details in some fast paths: actual mid-port aperture and length, front/rear chamber shapes and volumes, cone compliance and real-velocity modes, port interaction, cabinet backing and crossover. The Solana reconstruction's phase-1 waveguide-only BEM is a useful exterior reference but not a full JW Sound Solana speaker model.

**Action.** Record a fidelity ladder: isolated waveguide -> multiple imposed boundary velocities -> lumped coupled driver/port/chamber system -> interior FEM/exterior BEM/LEM multiphysics -> measured prototype. Validate port impedance, band overlap, mutual coupling, crossover notches and source movement. Do not claim a commercial replica from simplified source points.

Sources: [HornFab MEH dossier](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md), [Solana waveguide reconstruction](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/SOLANA_WAVEGUIDE_2026-11-01.md), [JW Sound Solana](https://www.jwsound.live/designs/solana-diy), [Boundary Lab](https://github.com/JWSound/boundary-lab).

### F17 [ESP][adapter] ATH's shaping plug is credible physics, but not yet a validated HF1440 upgrade

**Result [P].** ATH AP1 describes an external shaping plug dividing a compression-driver output into concentric channels, making path lengths similar and forming an approximately spherical exit wavefront. The documented demonstration has a 25.4 mm inlet, 75 mm length, two vanes/three channels, 33° exit angle and a 64 mm receiving horn throat. ATH later reported real-driver phase imperfections limited the promise of this concept and described improved outcomes from simpler extended-throat adapters.

**Action.** Compare baseline, simple conical extension, ring plug and ESP under identical source assumptions, with CAD-to-mesh manifold integrity, narrow-channel effects and finally actual driver measurements. Do not hard-code ESP as a universal improvement.

Sources: [ATH AP1 full 10-page PDF](https://at-horns.eu/release/Ath-AP1.pdf), [ATH Extended-Throat note](https://at-horns.eu/exar-story.html), [ATH segmentation method](https://at-horns.eu/seg-horn.html).

### F18 [GUI][data] Study analysis must preserve model-vs-measurement provenance and reuse CMA's successful result views

**Result [R].** HornFab GUI research defines Execute, Explain, Data and Decide phases: convergence, per-run and per-solve quality, objective/calibration, GP parameter relevance/uncertainty, trust region, Pareto, screen-vs-verify and 3D geometry. The current `bo/gui` code has evolved rapidly across branches; the November 16 cloud handoff reports completed slices that were **not necessarily merged into the local owner's branch**. A design plan is not evidence that the running GUI exposes a feature.

**Action.** Build a unified run/candidate identity so a BO observation opens the same 3D geometry, polar/beamwidth/isobar, impedance and verify panels as CMA. Add *BO-only* diagnostics (posterior predicted vs measured, credible intervals, acquisition, trust-region state, hyperparameters, training-cohort coverage, failed fits, eligibility, Pareto hypervolume). The browser must never invent/acoustically recompute scoring. Report whether a plot uses real solved pressure, interpolated balloon, proxy, GP posterior or synthetic fixture.

Repo: [BO GUI design](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/BO_GUI_DESIGN_2026-11-15.md), [cloud handoff](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/BO_GUI_CLOUD_HANDOFF_2026-11-16.md), [GUI data](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/gui/data_bo.py), [BO diagnostics](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/bo/diagnostics.py).

### F19 [printed horns][material] A numerical response is not the final printed product response

**Result [P/C].** Printed wall compliance, leakage, joint seams, thin sections, infill, surface finish, mounting, real driver source and measurement-window artifacts can move the response. A 2025 JASA study reported deviations in 3D-printed waveguide transfer-function measurements related to secondary sound paths, improved with a sand layer. This does not prove every print needs a sand fill, but makes wall/transmission checks a real validation requirement.

**Action.** Product finalists need a consistent print material/segmentation/joint process, structural checks, driver and woofer measurements, and a controlled baffled or free-standing setup.

Sources: [printed-waveguide transfer-function JASA paper](https://doi.org/10.1121/10.0035803), [ATH measurement gating note PDF](https://at-horns.eu/ext/Gating.pdf).

### F20 [method][research] Optimize the most informative new physical experiment, not the largest speculative queue

**Result [C/R].** Several past senior reviews independently favored a small matched family experiment with strict source/brief/mounting identity before another major 300–400 candidate queue. Useful baseline families: OSSE, R-OSSE, JMLC/loading, a simple hybrid and an independent biradial; isolate width/HV and throat effects. Existing prior data may eliminate some new solves.

**Action.** Match physical observations first, rank comparable **measured physics**, identify where screening is biased, update a versioned knowledge/score table, and authorize a new optimization budget only after demonstration of information gained per GPU-hour.

Sources: [research queue handoff](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/NEXT_QUEUE_PLANNING_HANDOFF_2026-11-12.md), [2025 rectangular horn objective study](https://doi.org/10.1121/10.0039253).

---

## 2. Horn typology atlas: what each family means and how HornFab should evaluate it

**Shared comparison measurements:** full H/V/45° normalized polar cuts, beamwidth-vs-frequency, DI/beam-shape curves (measured full balloon vs reconstructed explicitly tagged), normalized throat resistance and impedance ripple, on-axis/listening-window shape, low-frequency loading, mounting response, size, mesh fidelity, driver model and high-frequency behavior. Each family may have a different *design objective*, but its physical measurement vocabulary should be common.

| Typology / keyword | Characteristic physics or geometry | Appropriate design objective | Special failure mode / validation | Main source |
|---|---|---|---|---|
| **Keele CD / three-section** | Expanding throat + conical directional section + mouth bell, explicit CD goal | H/V near target above demonstrable pattern-onset frequency, smoothness/loading as constraints | Coverage target fails below mouth-controlled range; throat transitions and slot effects | [US4071112A](https://patents.google.com/patent/US4071112A/en) |
| **JBL Bi-Radial / Keele** | Independently shaped H/V wall pairs, classic gap/slot and mouth law | Separate H/V target bands and HF coverage plus loading | V-plane control can start later than H, severe gap/source boundary conditions | [US4308932A](https://patents.google.com/patent/US4308932A/en) |
| **OS / oblate spheroidal** | Smooth waveguide contour; separation/low HOM are design motivations | Consistent radiation and low diffraction with realistic baffle | Finite baffle and termination matter; mouth discontinuity | [Geddes overview PDF](https://web.archive.org/web/20211021013927/http://www.gedlee.com/Papers/What%20is%20a%20Waveguide.pdf) |
| **ATH OS-SE** | OS-derived curve with smooth superellipse termination and azimuth-specific parameters | CD or tunable smooth-directivity, low mouth diffraction, actual mounting | Baffle-dependent formula, not necessarily free-standing | [ATH OS-SE PDF](https://at-horns.eu/release/OS-SE%20Waveguide.pdf) |
| **ATH R-OSSE** | Parametric return/rollback contour; low-diffraction free-standing horn | Controlled and possibly rising DI depending on `k`, throat coupling and mouth transition | `r(z)` may be multivalued where rolled; correct parametric topology | [ATH R-OSSE PDF](https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf) |
| **ATH Tritonia / CORE / TwinRay** | Per-azimuth opening and termination, rectangular morph; diagonal changes | Smooth H/V and diagonal control under declared physical use | Never call axial ripple a Tritonia reconstruction; diagonal lobes | [Tritonia](https://at-horns.eu/tritonia.html) |
| **Le Cléac'h / JMLC** | Wavefront-normal/equidistant construction, rolled mouth and good loading; DI often rises | v6 loading-smooth or a dedicated sloped-directivity target, not forced v7 CD | Included vs half-angle, exact reference vs inspired H/V morph | [Fourcade full PDF](https://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf) |
| **Iwata / quasi-Iwata** | H/V-asymmetric traditional loading horn; historical geometry reconstructions vary | Natural beam narrowing with smooth loading and H/V-specific tolerances | Authentic reference geometry and construction ambiguity | [HornFab Iwata sources](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md) |
| **Exponential / tractrix** | Slow flare, efficient LF coupling, increasing HF beaming | Loading and smooth frequency response; intentionally rising DI | CD score inappropriate; mouth and throat reflection sensitivity | [Kolbrek horn overview](https://audioXpress.com/assets/upload/files/kolbrek2885.pdf) |
| **Crowe ES-600 / ES-inspired** | Author's ES flare and rolled mouth; HornFab analogues are original derivations | Measure natural narrowing, LF loading, smooth polar decay | Proprietary curve unavailable; visual bow-tie/270° wrap unproved as magic acoustic benefit | [Crowe ES-600](https://josephcrowe.com/blogs/news/es-600-biradial-horn) |
| **Klangfilm ellipse / Lamé rollback** | Curved/rolled historical styling, station-driven ellipse or superellipse | Loading, smooth DI slope, mouth diffraction; shape-discovery descriptors | Exact original math/visual parity still under study, avoid unmeasured claims | [dual Lamé integration](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/DUAL_LAME_INTEGRATION_2026-11-16.md) |
| **Freeform H/V transition hybrid** | Circular source → smoothly varying H/V profile → ellipse/superellipse mouth | Combined loading and well controlled coverage, smooth curvature | H/V independent 1D parent laws do not simply superpose acoustically | [Gu et al. 2025](https://doi.org/10.1121/10.0039253) |
| **Section pucker / ridges / X crease** | Local azimuthal/axial relief, unverified positive acoustic effect | First compare against smooth parent at equal bounds; penalize high-frequency artifacts | Nonmanifold shapes, excessive curvature/mesh DOF, diagonal diffraction | [section research](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/SECTION_PUCKER_RESEARCH_2026-11-15.md) |
| **ATH EXAR / extended throat** | Controlled-diameter throat adapter coupled to waveguide | LF resistance without worsening measured directivity in author's setup | Driver-specific interaction, possible higher-order modes and reflection | [Extended-Throat note](https://at-horns.eu/exar-story.html) |
| **Spherical-wave forming ESP** | Equal-length split channels, spherical output cap | HF wavefront control where driver exit source is known | Narrow channels, real-driver imperfections, loss and alignment | [ATH AP1 PDF](https://at-horns.eu/release/Ath-AP1.pdf) |
| **MEH / Danley / JW Solana / SAWMOD** | Multiple coupled driver entries on shared waveguide | Complete phase, crossover, impedance, coverage, distortion and output | Interior and port physics; source and rear compliance not just added polars | [HornFab mini-MEH](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md) |
| **Funktion-One-style cone horns** | Cone source and possibly phase-plug/bowl/port structure | Driver-coupled modal and system performance | Rigid-piston simplification, cone breakup and bowl volume | [HornFab cone horn research](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/CONE_MIDHORN_AXEHEAD_2026-10-28.md) |
| **Multicell** | Several channels or cell exits forming combined radiation | Band-limited coverage and coherent summation, sidelobe control | Path mismatch, grating/interference, coupled geometry cost | [HornFab multicell research](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/MULTICELL_HORN_RESEARCH_2026-10-25.md) |

### Typology-specific design principles worth retaining

**A. OSSE and R-OSSE.** Use the published azimuthal contour and termination mathematics as the parent. A rolled freestanding R-OSSE and a baffle-mounted OS-SE cannot share identical boundary assumptions. The R-OSSE shape parameter `k` can intentionally adjust DI slope. Do not automatically infer that all ATH-derived shapes are constant directivity.

**B. Le Cléac'h, Iwata and other loading-first families.** Preserve natural narrow-with-frequency behavior unless the product brief explicitly asks for CD. Include loading onset and impedance smoothness, explicit beamwidth slope/tolerance, and off-axis decay. The repository's v6 `loading_smooth` path was made for this distinction. Exact Fourcade geometry is a valuable regression control. `lecleach_swept_hv` is a derived H/V experiment, not a primary-source construction.

**C. Keele biradial and Crowe.** A patent-derived `W ~ K/(A F)` rule is a **first screening estimate**. Keele's patent also specifies geometry detail such as `A ~ 0.9 B`. Neither rule proves a horn will meet a requested pattern. Crowe designs are useful practical references, but proprietary “ES” geometry and 270° roll should not be reverse-engineered from photographs and then described as exact.

**D. Klangfilm/Lamé.** A classic ellipse (`p=2`) and superellipse (`p>2`) can have materially different cross-sectional area, corner curvature and wavefront behavior. A Lame exponent on a 2018 ellipse does not automatically reproduce a 2019 published or photographed revision. Use reference silhouette overlays, matched coordinate frames and exact shape validity. Stage visual design first, then sparse BEM seed solves; render appearance is not an acoustic result.

**E. Ridged or puckered mouth.** Distinguish radial/azimuth-dependent parameter law from axial `z` relief, spiral crest and cross-section morph artifact. A crease can give desired visual character but may create locally steep curvature, high-order modes and off-axis lobes. Compare smooth baseline -> perturbation-only -> joint optimization. Do not optimize all sculptural degrees of freedom before the base horn passes mesh and source tests.

**F. Multiple-entry.** Need separate driver impedance/mechanical/electrical variables, midport/waveguide geometries, cabinet compliance, coupling and crossover. Reusable exterior meshes alone are insufficient for a truthful full product replica.

---

## 3. Scoring and measurement contract for local agents

### 3.1 Terms to distinguish (search keywords)

| Concept | Required interpretation / common confusion |
|---|---|
| `cov` | Error in -6 dB beamwidth against target H/V angles. If targets are scalars in code, plot a flat scored beamwidth even when someone casually says “slope.” |
| `di_slope_target` | Target for derivative of DI (dB per decade), **not** beamwidth slope in degrees/octave. |
| `di` | DI level penalty, can oppose a nonzero DI slope if still treated as a constant target. |
| `distd` | DI *variation*, possibly a penalty even when a smooth rise is physically intended, depending on objective. |
| `diag` | Diagonal/off-axis behavior, important for noncircular mouths. |
| `flat`, `flat_cv` | On-axis spectral smoothness under different source normalizations and bands; inspect if below crossover is scored. |
| `load`, `load_near`, `z_smooth` | Different v4/v7 and v6 measurements of real normalized throat impedance. Never conflate. |
| `beamwidth_edges_deg` | Outermost crossing and crossing count; cannot guarantee a single connected lobe. |
| `ripple` | May depend on intended coverage window; must be recomputed when the target window changes. |
| `screen` | Early selection fidelity with limited mesh/frequencies. Not a full-range product verification. |
| `verify` | More rigorous numerical solve, but still not a real-driver or cabinet measurement unless modeled. |
| `J` | Objective-specific scalar, not an absolute horn-quality scale. |
| `full-sphere DI` | Requires correctly integrated spherical power over a resolved directional field. An estimate from two cuts must be labeled. |
| `frequency-band slope` | Quote units, e.g. dB/decade, dB/octave, degrees/octave, and specify fitted band. |

**Current code entry points:** [`objective/terms.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/objective/terms.py), [`objective/scalar_v6.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/objective/scalar_v6.py), [`objective/scalar_v7.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/objective/scalar_v7.py), [`metrics/polar.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/metrics/polar.py), [`metrics/di.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/metrics/di.py), [`targets/spec.py`](https://github.com/llevaachingada/Hornfab/blob/main/hornlab_search/targets/spec.py).

### 3.2 Proposed scored-target visual contract (not yet universally implemented)

A useful target-overlay payload should contain:
- `target_config_sha`, `objective_version`, `target_source`, `f0_hz`, `frequency_grid_hz`, `source_model`, `evaluation_band`, `fidelity`, and `units`.
- `beamwidth_h_target_deg[f]` and `beamwidth_v_target_deg[f]` with tolerance bands and onset/out-of-band flags.
- `di_target_db[f]` and `di_slope_target_db_per_decade` **separately** (or an explicit sloped DI curve if future scoring really uses one).
- `loading_min_re_z[f]`, optional `z_smooth` metric, and exclusion/passing flags.
- Measured H/V/diag from a named solved response, crossing counts, connected-lobe flags, uncertainty and mesh provenance.

UI failure test: change the **scoring target** and see whether the score and its plot both change. If only the picture changes or only the score changes, the UI is misleading.

### 3.3 Hi-fi vs PA vs no-EQ design choices

- **Active DSP home use:** broad smoothness across a listening window and directivity transition are generally more robust than absolute single-point axial flatness. Smooth common-to-all-angles spectral tilt can be equalized more easily than angular anomalies. Evaluate the woofer handoff and sound power.
- **Passive/no-EQ, tube or limited equalization:** sensitivity and raw response shape, impedance regularity and source loading are especially important.
- **Light PA:** coverage uniformity, directivity consistency, maximum output/thermal and nonlinear behavior, source constraints and sidelobes matter; a flat narrow-band pressure curve alone is insufficient.
- Treat these as engineering design priorities [I], not validated universal listener preference weights. Research that correlates loudspeaker listening ratings with full speaker response is not a measurement of the *isolated horn*.

Repository: [on-axis scoring audit](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/ONAXIS_WEIGHTING_2026-11-14.md), [screen re-ranking](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/HOME_OSSE_HIFI_RERANK_2026-11-16.md), [historical scoring dossier](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/SENIOR_PASS_SCORING_SEARCH_REALITY_2026-10-27.md).

---

## 4. Numerical acoustics and high-frequency strategy

### 4.1 Why consumer-hardware high frequency becomes hard

For dense BEM, an `N x N` complex matrix uses about `16 N²` bytes if stored as complex128, before extra operators, factorization workspace, kernel buffers, observation arrays and operating-system/GPU overhead. Approximate matrix only:
- N=8,000: 1.024 GB (~0.95 GiB).
- N=20,000: 6.4 GB (~5.96 GiB).
- N=34,000: 18.5 GB (~17.2 GiB).

These are **arithmetic examples**, not BEAT's complete allocation model. A 4060 8 GB cannot hold an unconstrained dense 34k x 34k complex128 matrix in VRAM. Frequency batching can reduce per-frequency overhead or improve throughput, but does not erase the dense-N² allocation bound. A bigger outward/returning horn surface increases element count even at the same frequency.

### 4.2 Numerical options ranked by evidence-readiness

| Technique | Why it could help | What it does *not* buy for free | Research |
|---|---|---|---|
| Fused CUDA assembly + batches | Already measured within HornFab; amortizes work per frequency | Not new physical accuracy | [throughput](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/THROUGHPUT_N1_2026-11-12.md) |
| Cached geometry/mesh context | Same geometry across frequencies/restarts allows preprocessing reuse | No reuse across changed shape/source without valid identity | [speed plan](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/SPEED_ADOPTION_2026-11-14.md) |
| CPU mesh prefetch / GPU pipeline | Overlap CPU prep with serialized GPU compute | Requires race- and cache-safe ownership | [throughput](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/THROUGHPUT_N1_2026-11-12.md) |
| Geometry-aware region meshing | Spend EPW in throat, high curvature, interfaces; reduce harmless rear shell | Must converge against a reference at each relevant frequency | [rear audit](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/REAR_DENSITY_MESH_AUDIT_2026-11-13.md) |
| Adaptive frequency grid | Detect missed resonances from cheap pilot and add targeted samples | Sparse solves don't guarantee unseen HF behavior | [fidelity study](https://github.com/llevaachingada/Hornfab/blob/main/tools/analysis/fidelity.py) |
| Multimodal horn/waveguide model | Lower-cost restricted-shape wave propagation, mode coupling and gradients | Not general 3D arbitrary-wavefront BEM | [Dong 2020](https://doi.org/10.1121/10.0001037) |
| Reduced-order / surrogate HF prediction | Use validated low/mid-frequency response and geometric descriptors to flag bad HF | Needs high-frequency labels and uncertainty checking; no guaranteed extrapolation | [HornFab BO study](https://github.com/llevaachingada/Hornfab/tree/main/docs/research/bo_study) |
| Matrix-free GMRES + preconditioning | Avoid direct dense solve/factorization, possible lower memory | Iteration may deteriorate with frequency/geometry | [HornFab study](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md) |
| ML-FMM / fast multipole | Accelerates far-field interaction and reduces dense-matrix requirement | Significant implementation complexity, especially high-frequency kernels | [NumCalc](https://doi.org/10.1016/j.enganabound.2024.01.008), [FMM3D](https://github.com/flatironinstitute/FMM3D) |
| Burton–Miller formulation | Helps exterior BEM avoid fictitious-frequency nonuniqueness | Does not eliminate mesh convergence and source errors | [Mesh2HRTF](https://mesh2hrtf.org/) |
| Far-field extraction/Huygens surface | Once boundary is solved, evaluate selected directions efficiently | Doesn't solve boundary field on an inadequately resolved mesh | [Boundary Lab model](https://github.com/JWSound/boundary-lab/blob/main/docs/Model%20Assumptions.md) |
| CPU high-resolution verification | Hardware fallback for larger matrices if RAM/time fit | Dense-N² memory still exists, no automatic speedup | [NumCalc](https://doi.org/10.1016/j.enganabound.2024.01.008) |

**Practical next experiment [I].** A fixed set of diverse real horns, 8–20 kHz in stages, mesh convergence in physically meaningful surface regions, pilot sparse frequencies + locally denser flagged bands, and comparison of fast 2-cut/partial balloon probes with a smaller set of full spherical verifications. Track whether the high-frequency screen predicts the bad cases and what that costs. Use the same model/output identity. Do *not* assert a “free 20 kHz” shortcut or replace the existing fused CUDA path until a validated faster method exists.

### 4.3 Crucial solver/model distinctions

1. **Exterior BEM** solves radiated sound from a known boundary/source. It generally requires a physically correct closed or open boundary formulation; arbitrary internal chambers/ports are not implied.
2. **Interior FEM** is needed for spatial modes in chambers and ports when 1D/lumped approximations are no longer adequate.
3. **Lumped electrical/mechanical/acoustic networks** model driver/back-volume/suspension/compliance/crossovers, if coupled and calibrated.
4. **Multi-source factorization reuse** is valuable when the matrix is unchanged and only the source vector changes. It does not imply distinct source models always share a physical solution.
5. **Source boundary conditions and convention** (`e^{+iωt}`, outward normal, velocity vs normal pressure gradient) must match between backends. Compare against analytic benchmarks and a second solver before claiming a hard HF result.
6. **Pressure normalization and angular averaging** must be explicit. Normalizing all directions by on-axis SPL can hide poor loading/sensitivity; H/V polars cannot establish full radiated sound power.

### 4.4 Research questions for fast HF classifiers

- Can a 2–8 kHz high-quality solve plus geometric curvature/area descriptors predict 8–16 kHz beamwidth collapse or off-axis lobing, with bounded false-negative rate?
- Does adaptive frequency sampling from a preliminary 9–13 frequency sweep catch most verified high-Q anomalies at materially reduced cost?
- What fraction of high-frequency error is mesh-vs-source-vs-physical geometry, tested independently?
- Which source/mesh model can provide cheap *relative* high-frequency ranking even if its absolute pressure is imperfect?
- Can matrix reuse across all 12+ frequencies be improved without accidentally reusing frequency-dependent physics?
- Would a trustworthy *subset of directions* detect bad horn design sufficiently for triage, while still reserving full balloon solves for DI and finalists?

All proposed, not established HornFab performance gains.

---

## 5. Optimization research and data-science infrastructure

### 5.1 What each optimizer should do

| Method | Strength in HornFab | Research limit |
|---|---|---|
| **CMA-ES** | Robust continuous search without a global smooth response model; restart/warm-start options | Flat penalties and narrow bounds can waste evaluations; doesn't quantify predictive uncertainty |
| **CMA-ME / MAP-Elites** | Diversity archive across H/V coverage, depth, mouth size, loading, etc. | Archive axes and fitness must be acoustically meaningful and measured consistently |
| **CMA-MAE** | Improved quality-diversity archive dynamics | Needs benchmarking and clear feasibility handling |
| **BoTorch scalar GP + qLogNEI** | Efficient local proposals from compatible solved history; acquisition reflects model uncertainty | Kernel assumptions, cohort contamination, overhead, poor extrapolation |
| **TuRBO** | Trust-region local refinement of good geometric basins | Can miss separate optima without restart/multiple-region strategy |
| **Constrained BO / SCBO** | Probabilistic expensive feasibility and cheap preflight integration | Physical-invalid vs product-size conditions must be distinguished |
| **Multi-objective BO** | Verified Pareto frontier for true acoustic trade-offs | 2-term coverage/ripple is not full system-optimal horn design |
| **Multi-fidelity BO** | Allocates screen/verify according to expected value of more information | If screen ranking is biased, it can amplify poor candidates |
| **Gradient/adjoint geometry optimization** | Large smooth parameter spaces with many stations/vertices | Different numerical solver project; gradient correctness and geometry validity critical |

### 5.2 Cohort requirements before training a GP or surrogate

At minimum: identical physical typology/parameterization version; source diameter, source mode and geometry; scored target and objective version; explicit frequency and angular grids; resolved solver/mesh/backend hashes; candidate eligibility; observed measurements vs surrogate predictions; constraints and price/compute. If transfer across typologies is desired, create a *purpose-built* shared physical-descriptor representation, not a blind union of unrelated normalized knobs. Use active parameter audits to remove no-op knobs and tests to ensure generated geometry changes with knobs.

Observed historical concerns included ~14–16% refusals in some campaigns, substantial seed variance, and screen-to-verify rank errors. They motivate constrained proposals and fidelity research, **not** a blanket claim that GP optimization has solved the underlying physics. [Search-math dossier](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/SEARCH_MATH_DOSSIER_2026-11.md).

### 5.3 Dataset as a scientific asset

Preserve raw pressure/complex response, impedance, mesh/source config, objective-independent descriptors and all candidate metadata. Rescoring targets is a cheap way to test research hypotheses across many historical geometries. Useful derived features include:
- Parametric flare rate and its derivatives, sectional area progression, principal curvature and its variation.
- Cross-section aspect and Lamé exponent over station; azimuthal relief and shape family.
- Size W/H/D, volume, surface area and projected aperture.
- Entrance wavefront/driver source descriptor and exact mounting.
- Beamwidth-vs-f curves, full angular smoothness, DI shape, windowed response, loading onset, crossover compatibility.
- Model numerical fidelity, convergence residual, compute cost and reason for refusal.

Keep descriptive acoustics separate from imposed penalties so future scoring studies cannot erase previous information.

### 5.4 Measurement and optimizer validation protocol

1. Freeze a physical common brief: driver, mounting, frequency band, observation geometry and target use.
2. Select 4+ families, with matched size/source constraints and a few physically meaningful seeds; use the archive if possible.
3. Run mesh-only validation, then CPU/GPU equivalence on a representative small subset.
4. Solve at screen settings and compare with matched frequency/mesh verify, isolating the cause of rank reversals.
5. Re-score full existing response data with alternative target curves and compare physical metrics.
6. Benchmark CMA restarts, BO/TuRBO and QD under matched **new real solves** and separately report total compute and model overhead.
7. Archive all observations, independent of whether they were selected or were under product envelope.
8. Prototype promising geometry in its real mounting and measure it against the predicted acoustic response.

### 5.5 GUI result schema for learning, not merely watching

For every candidate, expose a link to canonical run + geometry preview and mesh, plus:
- `proposed_by`: CMA/GP/TuRBO/Pareto/manual; acquisition ID, seed, trust region, candidate pool rank.
- `predicted`: estimated score and uncertainty, model version, calibration and train/held-out split.
- `observed`: screen J, verify J, objective version and physics metrics. Never equate `predicted` with `observed`.
- `constraints`: physical invalid / envelope / budget / source mismatch, all with actual values and thresholds.
- `comparisons`: verified Pareto status, prior best, screen-verify delta and similar historical neighbors.
- `viewers`: geometries in rotatable 3D, mesh fidelity, H/V/diagonal polar curves, isobars, beamwidth and full-balloon data where measured, throat impedance and response curves.

For BoTorch specifically add fit health, GP calibration, knob sensitivity, trust-region lengths/restarts, acquisition function and hypervolume trend. For CMA preserve native generation, sigma and covariance diagnostics. A shared candidate viewer should be engine-agnostic.

---

## 6. Corrections and unresolved claims: do not re-propagate

| Claim encountered in prior work | Status | Correct interpretation / next verification |
|---|---|---|
| “v7 is already scoring all non-CD horns against an actual sloped H/V beamwidth target.” | **[X] unsupported as a global statement** | Check resolved `cov`, `di`, `dislope` in YAML, code and dataset row. Nonzero DI slope alone is not H/V beamwidth slope. |
| “Any JMLC or Crowe result should have the same CD J as OSSE.” | **[X]** | Raw objective values differ by target/family; compare physical measurements or rescore under a deliberately common objective. |
| “ATH Tritonia is just a z-axis mouth pucker.” | **[X]** | Published variation is azimuthal/radial with morph law; z-only variants are original experiments. |
| “An H/V-shaped Le Cléac'h variant is an exact published Fourcade horn.” | **[X]** | Fourcade's canonical construction is axisymmetric; H/V Lamé morph is derived and must be 3D verified. |
| “Crowe ES-600 source curve can be reconstructed exactly from photos.” | **[X]** | Published visual dimensions and author descriptions do not define proprietary complete flare math. Label HornFab forms “inspired”. |
| “A 270° wrap has proven superior measured acoustics to every 130°/180° lip.” | **[X]** | Mouth smoothing is grounded; exact optimal wrap among these angles is not established by a controlled comparison. |
| “The waist/X-shaped mouth creases guarantee an acoustic benefit.” | **[X]** | May be a geometric byproduct or styling; measure full diagonal and sidelobes first. |
| “HF1440 has a 2° published acoustic exit angle.” | **[X]** | Older 2° is a source-model assumption; verify any actual driver physical contour, use round 35.8 mm exit at z=0. |
| “Every physically valid horn should be rejected for exceeding the 600×480×480 production box.” | **[X]** | Product constraint is distinct from discovery constraint; collect acoustics of promising oversize shapes within compute safety limits. |
| “BoTorch is intrinsically faster at BEM.” | **[X]** | It chooses different candidate shapes, not faster Helmholtz solves. |
| “The November 15 BO win proves universal dominance over CMA.” | **[X]** | Three-seed single-task warm-start benchmark with different rejection/admission policy; strong but limited result. |
| “A 5.5 or 8 kHz screen proves quality to 20 kHz.” | **[X]** | Requires high-frequency numerical and source/measurement verification or a validated learned screening bound. |
| “Two polars define 3D DI exactly.” | **[X]** | Full angular integral requires sufficient spherical field data. |
| “A run's image is enough to say a typology is implemented and acoustically ready.” | **[X]** | Geometry, solver, score, model source, local branch and numerical verification are separate gates. |
| “Main branch automatically contains every recent BO GUI feature.” | **[X]** | Branch handoff of Nov 16 explicitly discussed unmerged work; check actual owner branch and running GUI. |
| “An oversize/scoring penalty teaches BO the acoustics of that horn.” | **[X]** | A flat penalty is not a BEM observation. |
| “We can shrink an optimized 700 Hz horn and preserve the 700 Hz behavior around the same throat.” | **[X]** | Similarity scaling requires all geometry including source to scale; keeping HF1440 throat fixed breaks similarity. |

---


## 7. External source catalog: papers, full PDFs, patents and useful implementation references

**Source-access legend:** `PDF` means a directly linked PDF or an author/institution-hosted PDF URL, **not** necessarily that every server will allow automatic download. `OPEN` means an accessible public HTML/full-text source or open repository. `ABSTRACT/DOI` means a scholarly landing page with at least abstract/metadata; access to the complete manuscript might require a library or author copy. `PATENT` provides full patent text and drawings. `AUTHOR` denotes creator documentation or first-party measurements rather than independent peer review. Items listed as `PDF` were either investigated in the earlier HornFab source dossiers or directly checked in the current source pass; availability and content can change.

### 7A. Fundamental horn theory, directivity and acoustical geometry

| ID | Publication / source, access | Main contribution to HornFab | Direct source |
|---|---|---|---|
| **HT-01** | D. B. Keele, *What's So Sacred About Exponential Horns?* (AES 1975), OPEN/author index | Why traditional radial/exponential horns can narrow in midrange or beam at HF; foundation of controlled-directivity horn development | https://dbkeele.com/7-whats-so-sacred-about-exponential-horns/ |
| **HT-02** | D. B. Keele, *Optimum Horn Mouth Size* (AES 1973), ABSTRACT/author | The largest mouth is not automatically the most advantageous for mouth reflection, loading and the chosen cutoff | https://dbkeele.com/optimum-horn-mouth-size/ |
| **HT-03** | D. B. Keele / Electro-Voice, *Constant Directivity Loudspeaker Horn* US4071112A, PATENT | Three-section exponential throat, conical directional section and bell; matching surfaces and midband beamwidth compensation | https://patents.google.com/patent/US4071112A/en |
| **HT-04** | D. B. Keele / JBL, *Bi-Radial Horn* US4308932A, PATENT | H/V different curvature laws and mouth-sizing heuristic; useful reference for `biradial`, not a numerical truth guarantee | https://patents.google.com/patent/US4308932A/en |
| **HT-05** | E. R. Geddes, *What Is a Waveguide?*, PDF/archived | The theoretical distinction between waveguide solutions, classic horn assumptions, diffraction and high-order modes | https://web.archive.org/web/20211021013927/http://www.gedlee.com/Papers/What%20is%20a%20Waveguide.pdf |
| **HT-06** | E. Geddes, *Acoustic Waveguide Theory* (JAES 1989) and *Revisited* (JAES 1993), scholarly | Underlying separable-coordinate waveguide theory; check original journal library for complete text | https://aes.org/ |
| **HT-07** | E. Geddes, *Acoustic waveguide with improved performance* US7068805, PATENT | Driver-to-waveguide continuity, noncircular transition ideas and preventing diffraction from entrance discontinuities | https://patents.google.com/patent/US7068805 |
| **HT-08** | E. Geddes, *Audio Transducers*, Chapter 6, PDF | Horn, waveguide and high-order-mode explanations useful when deciding whether a shape or port introduces discontinuities | https://www.gedlee.com/downloads/AT/Chapter_6.pdf |
| **HT-09** | W. Kolbrek, *Horn Theory: An Introduction*, PDF/audioXpress | Practical distinction among conical, exponential and hyperbolic expansion, throat resistance and mouth reflection | https://audioXpress.com/assets/upload/files/kolbrek2885.pdf |
| **HT-10** | W. Kolbrek, *BEM Simulations: Horns*, OPEN | Practical sound source, boundary approximation and mesh/reference pitfalls; useful independent reference for HornFab | https://kolbrek.hornspeakersystems.info/index.php/horns/bem |
| **HT-11** | J. Fourcade, *Calcul du Pavillon Le Cléac'h* (2015), **PDF/FULL** | Explicit JMLC construction mathematics, numerical reference case, wall and wavefront geometry; mandatory canonical reference | https://unepassionaudiophile.fr/wp-content/uploads/2018/01/Pavillon-JMLC.pdf |
| **HT-12** | J.-M. Le Cléac'h, ETF lecture on horns (2010), **PDF/FULL** | Families of spherical/equidistant wavefront horns, theoretical geometry and historical context | https://rintelen.ch/download/JMMLC_horns_lecture_etf10.pdf |
| **HT-13** | J.-M. Le Cléac'h, *Horn Profiles*, PDF/archived | Profile concepts, loading vs wavefront and historical definitions for interpreting JMLC terminology | https://pearl-hifi.com/06_Lit_Archive/14_Books_Tech_Papers/LeCleac%27h_Jean-Michel/Horn_Profiles.pdf |
| **HT-14** | J. Sheerin, *LeCleac'h horn vs Conical Horn*, OPEN/practitioner | FEA comparison of polar response and transient energy; useful case study but dependent on chosen driver/geometry | https://jhsaudio.com/conical.html |
| **HT-15** | Sridhar, Tylka & Choueiri, *Generalized Metrics for Constant Directivity* (JAES 2019), **PDF/FULL** | Frequency invariance metrics beyond a single beamwidth; use to audit misleading “nice”-looking directivity plots | https://oar.princeton.edu/bitstream/88435/pr12s1j/1/Generalized%20metrics%20for%20constant%20directivity.pdf |
| **HT-16** | Sridhar et al. DOI, ABSTRACT/DOI | Persistent identifier for the same metric paper | https://doi.org/10.17743/jaes.2019.0022 |
| **HT-17** | Geddes/DIY forums, practitioner discussion | Real-world debate about HOM, abrupt throats and foam/mouth treatment; background rather than proof | https://www.diyaudio.com/community/threads/geddes-on-waveguides.103872 |

### 7B. ATH, modern waveguides, mouth shapes and adapters

| ID | Publication / source, access | Main contribution to HornFab | Direct source |
|---|---|---|---|
| **ATH-01** | M. Batík, *OS-SE Waveguide* (2020), **PDF/FULL** | Parent profile, smooth superellipse mouth termination, azimuthal law and morph variables; original formula | https://at-horns.eu/release/OS-SE%20Waveguide.pdf |
| **ATH-02** | M. Batík, *R-OSSE Waveguide*, rev. 7 (2022), **PDF/FULL** | Parametric rolled profile, free-standing termination, opening-angle and directivity-slope controls | https://at-horns.eu/release/R-OSSE%20Waveguide%20rev7.pdf |
| **ATH-03** | M. Batík, *Ath 4.8.2 User Guide*, **PDF/FULL** | Generator configuration, `Morph.*`, rounded rectangle, fixed portion, morph rate, shrink policy and termination settings | https://at-horns.eu/release/Ath-4.8.2-UserGuide.pdf |
| **ATH-04** | ATH *Tritonia*, AUTHOR/full page | The actual azimuth-dependent angle and termination script, morphology, diagrams and measurements | https://at-horns.eu/tritonia.html |
| **ATH-05** | ATH *Tritonia.txt* published source script, text | Literal angular-law example; prevents generic axial-ridge approximations being mislabeled Tritonia | https://at-horns.eu/ext/Tritonia.txt |
| **ATH-06** | ATH *CORE*, AUTHOR/full page/script | Published `ath_core` shape and morph inputs; good reconstruction regression seed | https://at-horns.eu/core.html |
| **ATH-07** | ATH *TwinRay*, AUTHOR/full page | Noncircular coverage, mouth/baffle design, diagonal response and practical surface engineering | https://at-horns.eu/twinray.html |
| **ATH-08** | ATH *TwinRay roundover study*, AUTHOR/images | Numerical comparison of enclosure edge fillets; do not confuse **cabinet-edge** with mouth-lip radius | https://at-horns.eu/img/twinray/bem/roundover-study.html |
| **ATH-09** | ATH *Extended Throat / EXAR Story*, AUTHOR | Testing extended throat coupling, increased low-frequency resistance and actual-driver caveats | https://at-horns.eu/exar-story.html |
| **ATH-10** | M. Batík, *AP1 Spherical Wave Former* (2021), **PDF/FULL** | Three-channel spherical-wave-forming adapter, design dimensions, numerical comparisons and author caveats | https://at-horns.eu/release/Ath-AP1.pdf |
| **ATH-11** | ATH *Segmentation of the Horn*, AUTHOR | Dividing large waveguides into printable/CAD pieces; mechanically relevant, not an acoustic optimization paper | https://at-horns.eu/seg-horn.html |
| **ATH-12** | ATH *Gating*, **PDF/FULL** | Measurement and time-windowing limits for comparing horn directivity/response | https://at-horns.eu/ext/Gating.pdf |
| **ATH-13** | Joseph Crowe, *ES-600 Bi-Radial Horn*, AUTHOR | Photographs, gross geometry, claimed mouth wrap, deployment details; **not** complete open-source flare equations | https://josephcrowe.com/blogs/news/es-600-biradial-horn |
| **ATH-14** | Joseph Crowe earlier ES-600 article, AUTHOR | Additional images, product history and designer reasoning; distinguish marketing from controlled measurement | https://croweaudio.blogspot.com/2019/11/es-600-biradial-horn.html |
| **ATH-15** | MTG *Waveguide Shootout*, OPEN/practitioner | Controlled-seeming practical baffle, microphone and off-axis artifact examples relevant to numerical-to-physical comparisons | https://www.mtg-designs.com/tips-tricks-tests/waveguide-shootout |

### 7C. Mathematical shape optimization, multimodal waveguides and model validation

| ID | Publication / source, access | Main contribution to HornFab | Direct source |
|---|---|---|---|
| **OP-01** | Gu, You & Shen, *Multimodal-based shape optimization of rectangular horns for improved radiation efficiency and directivity control* (JASA 2025), ABSTRACT/DOI | Strongest near-term hybrid-design experiment: objective terms for loading, smoothness and H/V directivity | https://doi.org/10.1121/10.0039253 |
| **OP-02** | Dong et al., *Shape optimization of acoustic horns using the multimodal method* (JASA 2020), PDF | Physics-informed modal formulation and shape gradients for a tractable class of horns; proposal-fidelity inspiration | https://asa.scitation.org/doi/pdf/10.1121/10.0001037 |
| **OP-03** | Dong et al., *Shape optimization of acoustic horns for improved directivity control and radiation efficiency based on multimodal method* (JASA 2021), ABSTRACT/DOI | Demonstrates compromise between loading and coverage with reduced formulation | https://doi.org/10.1121/10.0003568 |
| **OP-04** | Schmidt, Wadbro & Berggren, *Large-scale three-dimensional acoustic horn optimization* (2016), **PDF/FULL** | Thousands of geometry variables using gradient/adjoint methods, useful long-range challenge to pure population search | https://people.cs.umu.se/martinb/downloads/Papers/ScWaBe16.pdf |
| **OP-05** | Smolen & Halley, *An Approach for the Optimization of 3D Loudspeaker Horns* (JAES 2021), ABSTRACT/DOI | CAD + FEM/BEM + optimization with physical validation for non-axisymmetric horn | https://doi.org/10.17743/jaes.2020.0061 |
| **OP-06** | COMSOL, *Optimizing the Shape of a Horn*, OPEN model | Reproducible FEM formulation including radiation boundary, PML and shape objective; explicitly cautions against optimizing axial SPL alone | https://doc.comsol.com/6.3/doc/com.comsol.help.models.aco.horn_shape_optimization/horn_shape_optimization.html |
| **OP-07** | Udawalpola, Wadbro & Berggren, optimal horn mouth/adjoint BEM (2011), ABSTRACT/DOI | Mouth reflection and large-parameter shape sensitivity literature | https://doi.org/10.1002/nme.2982 |
| **OP-08** | Bängtsson, Noreland & Berggren, acoustic shape optimization (2003), ABSTRACT/DOI | Classical numerical optimization of horn-like acoustical shapes | https://doi.org/10.1016/S0045-7825(02)00656-4 |
| **OP-09** | Wadbro & Berggren, acoustical topology/shape optimization (2006), ABSTRACT/DOI | Alternative to a small fixed family of flare parameters; substantial solver change needed | https://doi.org/10.1016/j.cma.2006.05.005 |
| **OP-10** | Dong, Doc & Félix, *Influence of a finite loudspeaker enclosure on waveguide directivity* (JASA 2024), **PDF/FULL** / DOI | Finite-baffle effects on low-frequency beamwidth; blocks unfair free-standing-vs-mounted comparisons | https://univ-lemans.hal.science/hal-04798282/document |
| **OP-11** | Same finite-enclosure study, ABSTRACT/DOI | Persistent metadata for paper OP-10 | https://doi.org/10.1121/10.0025389 |
| **OP-12** | *Shape Optimization of Rectangular Horns Mounted in a Finite Loudspeaker Enclosure* (Applied Acoustics 2023), ABSTRACT/DOI | Joint horn/cabinet optimization and finite mounting context | https://doi.org/10.1016/j.apacoust.2023.109619 |
| **OP-13** | *Improving transfer function measurements for 3-D printed waveguides using a sand layer* (JASA 2025), ABSTRACT/DOI | Printed-wall transmission paths and repeatability, to test against solver assumptions | https://doi.org/10.1121/10.0035803 |
| **OP-14** | Newell & Holland, *Do all midrange horn loudspeakers have a recognisable characteristic sound?* (Reproduced Sound 2024), ABSTRACT/DOI | Limited perceptual research context; do not treat as quantified universal penalty weights | https://doi.org/10.25144/21421 |
| **OP-15** | Makarski & Behler, AES 2004 compression-driver exit source/velocity modeling, ABSTRACT/DOI | Why ideal uniform source BC may differ from measured compression-driver modes | https://aes.org/publications/elibrary/elibrary-page/?id=12743 |
| **OP-16** | CutFEM / compression-driver optimization (2026), OPEN/DOI | Recent numerical work on real compression-driver geometry/source coupling, separate from horn mouth optimization | https://doi.org/10.1002/nme.70284 |

### 7D. BEM, fast numerics, MEH and full loudspeaker modeling

| ID | Publication / source, access | Main contribution to HornFab | Direct source |
|---|---|---|---|
| **BE-01** | NumCalc (2024): open-source numerical acoustics with high-performance boundary solver, OPEN/DOI | ML-FMM/fast BEM strategies to study for >8–12 kHz memory limits | https://doi.org/10.1016/j.enganabound.2024.01.008 |
| **BE-02** | Mesh2HRTF, OPEN | Reproducible BEM machinery and numerical reference/verification ideas; different end use from horns | https://mesh2hrtf.org/ |
| **BE-03** | FMM3D, OPEN/code | High-performance fast multipole kernels, potential research building block; not a plug-in HornFab solver | https://github.com/flatironinstitute/FMM3D |
| **BE-04** | AKABAK 3 introduction, AUTHOR | Coupling lumped electrical/mechanical/acoustic networks to acoustic spatial boundary calculations | https://www.randteam.de/AKABAK3/AKABAK-Introduction.html |
| **BE-05** | Boundary Lab, OPEN/code | Contemporary coupled BEM/driver/multi-region loudspeaker examples and an external reference model to inspect | https://github.com/JWSound/boundary-lab |
| **BE-06** | JW Sound, *Solana DIY*, AUTHOR/guide link | Concrete MEH case with published driver/port/crossover structure; do not confuse exterior waveguide-only recon with complete speaker | https://www.jwsound.live/designs/solana-diy |
| **BE-07** | Danley, multiple-entry Synergy horn patent US8284976B2, PATENT | Shared-mouth, multi-source and path/port arrangement primary descriptions | https://patents.google.com/patent/US8284976B2 |
| **BE-08** | Synergy Calc v5, PDF/practitioner tool | Simple acoustic network/delay/crossover construction hints, useful preliminary model but not complete spatial solver | http://libinst.com/SynergyCalc/Synergy%20Calc%20V5.pdf |
| **BE-09** | MeHStudio, OPEN/code | Independent multiple-entry modeling code and its scope limits | https://github.com/mroushdy/MehStudio |
| **BE-10** | Boundary Lab / horn-simulation issue 78, OPEN/discussion | FEM spatial-resolution requirements and limitations of open-vs-closed BEM comparisons | https://github.com/timini/horn-simulation/issues/78 |

### 7E. Search, Bayesian optimization and quality-diversity research

| ID | Publication / source, access | Main contribution to HornFab | Direct source |
|---|---|---|---|
| **BO-01** | Eriksson et al., *Scalable Global Optimization via Local Bayesian Optimization* (TuRBO, NeurIPS 2019), **PDF/FULL** via arXiv | Local trust-region Gaussian-process candidate selection at moderate/high dimension | https://arxiv.org/pdf/1910.01739 |
| **BO-02** | BoTorch official TuRBO tutorial, OPEN/code | Practical integration and trust-region state formulation | https://botorch.org/docs/tutorials/turbo_1 |
| **BO-03** | BoTorch official constrained optimization tutorial, OPEN/code | Hard vs probabilistic expensive constraints, feasibility-aware acquisition | https://botorch.org/docs/tutorials/scalable_constrained_bo |
| **BO-04** | BoTorch official multi-objective optimization, OPEN/code | qLogNEHVI, Pareto hypervolume and multiple competing acoustic performance axes | https://botorch.org/docs/multi_objective |
| **BO-05** | BoTorch official multi-fidelity optimization tutorial, OPEN/code | Information gained from cheap screen and costly verification, with strong requirement for calibrated cross-fidelity agreement | https://botorch.org/docs/tutorials/multi_fidelity_bo |
| **BO-06** | Hansen, *The CMA Evolution Strategy: A Tutorial*, **PDF/FULL** via arXiv | CMA restart/covariance theory; correct comparator for GP optimization rather than naive CMA | https://arxiv.org/pdf/1604.00772 |
| **BO-07** | Quality Diversity research papers, OPEN | MAP-Elites, CMA-ME and related archive search to preserve alternative excellent horns | https://quality-diversity.github.io/papers.html |
| **BO-08** | SALib documentation, OPEN | Sobol/Morris screening and sensitivity assessments for deciding active horn knobs | https://salib.readthedocs.io/en/latest/ |

**Access discipline.** A publisher DOI is often the **most stable link** but is not equivalent to a downloadable full PDF. The catalog intentionally presents both DOI and direct paper links when an author or institution copy is known. If a PDF fails, record its failure and look for an authorized author's version; do not fabricate pages, figures or results from an abstract.

---

## 8. Internal HornFab document/source map for agents

This section is the **repository-native searchable reading index**. Links point to `main` paths present in the tree inspected on 2026-11-16. Some records document *historical proposals* or *branch-specific findings*; use their status and date rather than treating every proposal as production behavior.

### 8A. Four high-leverage foundational research dossiers

| Priority | Primary HornFab dossier | Why it is useful | Source |
|---|---|---|---|
| **A1** | *Horn design white papers and analysis practice* (Nov 15) | Cross-family bibliography, vetted CD vs non-CD evidence, source-critical notes, morphology and modeling best practices | [Full document](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/HORN_WHITEPAPERS_2026-11-15.md) |
| **A2** | *Le Cléac'h (JMLC) construction, implementation dossier* (Oct 25) | Exact Fourcade reference mathematics, included-angle correction, numerical test anchors | [Full document](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/JMLC_LECLEACH_RESEARCH_2026-10-25.md) |
| **A3** | *Search-Math Research Dossier* (Nov 12) | CMA, constraints, surrogate, warm starts, fidelity, quality-diversity and rigorous benchmarks | [Full document](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/SEARCH_MATH_DOSSIER_2026-11.md) |
| **A4** | *Mini multiple-entry horn research dossier* (Oct 29) | Driver/port/chamber/network requirements, 1D vs spatial solver, actual MEH physics and source citations | [Full document](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/MINI_MEH_RESEARCH_2026-10-29.md) |

*These are four especially useful **chosen anchor dossiers**, not a claim that they were the user's exact four unnamed research documents. The uploaded senior-review notes and other project research are also incorporated below.*

### 8B. Typology and physics research files

| Repo file, short path under `docs/research/` | Search tags | What the local agent should extract |
|---|---|---|
| [`typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/ATH_CORE_TWINRAY_MORPH_2026-10-25.md) | ATH, CORE, morph | Primary ATH math, target shape and generator mapping |
| [`typologies/ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/ROLLED_FAMILY_MASTER_RESEARCH_2026-11-15.md) | R-OSSE, radial, Tritonia, pucker | Critical axial-vs-radial misconception and verified configuration |
| [`typologies/ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/ROLLED_RECT_FAMILY_RESEARCH_2026-11-15.md) | Crowe, rollback, rectangular | The difference between visual analogues and proprietary published shapes; CPU geometry experiments |
| [`typologies/SECTION_PUCKER_RESEARCH_2026-11-15.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/SECTION_PUCKER_RESEARCH_2026-11-15.md) | X crease, ridge, pucker | Original perturbation experiment, not an exact ATH patent/formula |
| [`typologies/MOUTH_RIPPLE_SERRATION_RESEARCH_2026-10-25.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/MOUTH_RIPPLE_SERRATION_RESEARCH_2026-10-25.md) | ridges, pleats, mouth | Source distinction and mathematical variants |
| [`typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/JMLC_FAMILY_VARIANTS_RESEARCH_2026-10-25.md) | JMLC, LC, T | Reference JMLC variants and design-family limits |
| [`typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/LECLEACH_OBJECTIVE_V6_2026-11-05.md) | v6, loading_smooth | Why a load-first horn shouldn't be forced into CD scoring |
| [`typologies/LECLEACH_HV_ELLIPSOID_2026-11-16.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/LECLEACH_HV_ELLIPSOID_2026-11-16.md) | LC, HV, ellipsoid | Derived non-axisymmetric LC/Lamé geometry; verify validity and status |
| [`typologies/DUAL_LAME_INTEGRATION_2026-11-16.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/DUAL_LAME_INTEGRATION_2026-11-16.md) | Lamé, Klangfilm, Le Cléac'h | Current implementation gates and distinction between published parent and derived H/V shape |
| [`typologies/KLANGFILM_ELLIPSE_HANDOFF_2026-11-16.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/KLANGFILM_ELLIPSE_HANDOFF_2026-11-16.md) | Klangfilm, silhouette | Geometry status, reference-photo mismatch and unapproved acoustic stage |
| [`typologies/BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/BIRADIAL_IWATA_300_RESEARCH_2026-10-25.md) | Iwata, biradial | Historical patent/formula and specific dimension interpretation |
| [`typologies/BIRADIAL_CROWE_SOURCES_2026-11-15.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/BIRADIAL_CROWE_SOURCES_2026-11-15.md) | Keele, Crowe, lip, K-law | **Read correction header first**; updated mouth-size denominator and unproven wrap claims |
| [`typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/BIRADIAL_CROWE_STUDY_2026-11-15.md) | Crowe, 80x50, generation | Studies locked knobs, family geometry and objective fairness |
| [`typologies/SCORING_NON_CD_SOURCES_2026-11-15.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/SCORING_NON_CD_SOURCES_2026-11-15.md) | J, DI slope, CD, non-CD | **Read correction header first**; fixed-vs-sloped scoring mismatch |
| [`typologies/SOLANA_WAVEGUIDE_2026-11-01.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/SOLANA_WAVEGUIDE_2026-11-01.md) | Solana, JWSound, MEH | Explicit waveguide-only BEM limitations and later coupled system phase |
| [`typologies/SAWMOD_CONTROL_WAVEGUIDE_2026-11-01.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/SAWMOD_CONTROL_WAVEGUIDE_2026-11-01.md) | SAWMOD, control | No-knuckle exterior waveguide control versus full multiple-entry design |
| [`typologies/MULTICELL_HORN_RESEARCH_2026-10-25.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/MULTICELL_HORN_RESEARCH_2026-10-25.md) | multicell, phase | Multiple horn outlets, path mismatch and lobing |
| [`typologies/CONE_MIDHORN_AXEHEAD_2026-10-28.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/CONE_MIDHORN_AXEHEAD_2026-10-28.md) | cone, Funktion-One | Cone-driven horn source fidelity and geometry |
| [`THROAT_COUPLING_2026-10-27.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/THROAT_COUPLING_2026-10-27.md) | source, round throat | Driver exit and morph constraints; cautions against invented 20–30% fixed-length rules |
| [`ATH_SUPERFORMULA_AND_GSA_2026-10-25.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/ATH_SUPERFORMULA_AND_GSA_2026-10-25.md) | superformula, GSA | Search parameterization, theoretical constraints and alternate optimizer proposal |
| [`SIM_VS_REAL_HORN_2026-10-27.md`](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/SIM_VS_REAL_HORN_2026-10-27.md) | simulation, driver | Boundary/source realism and validating acoustic modeling assumptions |

### 8C. Search, scoring, datasets, benchmarking and GUI research files

| Repo document | Search tags | Why to read |
|---|---|---|
| [Loading objectives reconciled](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/LOADING_OBJECTIVES_RECONCILED_2026-11.md) | v4/v6/v7, impedance | Exact physics/normalizations and why the three “load” terms differ |
| [On-axis weighting and hi-fi rescoring](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/ONAXIS_WEIGHTING_2026-11-14.md) | DSP, flat, listening window | Unintended below-XO penalty, angular response and equalization |
| [Hi-fi offline rerank evidence](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/HOME_OSSE_HIFI_RERANK_2026-11-16.md) | offline score, DSP | How design rankings changed without new BEM |
| [Search-math dossier](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/SEARCH_MATH_DOSSIER_2026-11.md) | CMA, BO, invalid, uncertainty | Constraints, seed variance, surrogate, fidelity and QD |
| [Next queue planning handoff](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/NEXT_QUEUE_PLANNING_HANDOFF_2026-11-12.md) | queue, GPU, archive | Historical queue rationale and data reuse; status time-sensitive |
| [Objective v8 proposal](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/OBJECTIVE_V8_PROPOSAL_2026-11-12.md) | v8, scorer | Experimental objective and gates; do not assume enabled |
| [BO vs CMA Nov 15 benchmark](https://github.com/llevaachingada/Hornfab/blob/main/docs/status/2026-11-15-bo-vs-cma/README.md) | GP, qLogNEI, wall clock | Task-level predeclared benchmark and limitations |
| [BO GUI design/implementation log](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/BO_GUI_DESIGN_2026-11-15.md) | GUI, calibration, 3D | Execute/Explain/Decide/Data components, artifact contracts |
| [BO GUI cloud branch handoff](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/BO_GUI_CLOUD_HANDOFF_2026-11-16.md) | branch, GUI, diagnostics | Which features may be unmerged and why local UI can lag |
| [Matrix-free GPU GMRES / FMM review](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/MATRIX_FREE_GPU_GMRES_FMM_2026-10-29.md) | CUDA, HF, FMM | Non-dense high-frequency research feasibility |
| [Senior HF 12 kHz review](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/senior_pass_2026-10-24/03_HIGH_FREQUENCY_12KHZ.md) | EPW, 20kHz, memory | Existing numerical assumptions and solver alternatives |
| [Fused GPU throughput measurements](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/THROUGHPUT_N1_2026-11-12.md) | batch, VRAM, fused | Carefully measured per-size microbenchmarks |
| [Speed adoption record](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/SPEED_ADOPTION_2026-11-14.md) | solver, speed | What experiments/flags were or weren't adopted |
| [Rear-shell mesh density audit](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/REAR_DENSITY_MESH_AUDIT_2026-11-13.md) | rear density, fidelity | Mesh-only feasibility evidence; **not** proof of acoustic convergence |
| [BoTorch study design](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md) | Bayesian, study | Cohort/proposal/study scheduling contract |
| [Data GA research plan](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/DATA_GA_RESEARCH_PLAN_2026-11-12.md) | genetic, archive | Dataset-driven search alternatives and caution |
| [Parameter-domain audit](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/audit_2026-11-15/PARAMETER_DOMAINS.md) | bounds, live knobs | Which shape parameters are active vs frozen |
| [Typology geometry-capability audit](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/audit_2026-11-15/GEOMETRY_CAPABILITY.md) | CAD, GRID, native | Which families can actually materialize and be solved |
| [Parameter activity](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/bo_study_2026-11-12/b2/parameter_activity.md) | identifiability, knobs | Avoid optimizing no-op and confounded shape parameters |
| [Sensitivity study](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/bo_study_2026-11-12/m2/sensitivity.md) | sensitivity, BO | Which variables affect observed objective (within prior task scope) |
| [Source fidelity study](https://github.com/llevaachingada/Hornfab/blob/main/docs/evidence/bo_study_2026-11-12/s6/source_fidelity.md) | source, driver | Distinguish ideal-source assumptions and full real-driver claims |

### 8D. Critical implementation entry points

These are starting paths for the **local agent to inspect**, not claims that the current local branch matches `main`:

- `hornlab_search/targets/spec.py`: physical brief, band and directivity properties.
- `hornlab_search/objective/terms.py`, `scalar_v6.py`, `scalar_v7.py`: exact score math and term normalization.
- `hornlab_search/metrics/polar.py`, `metrics/di.py`: polar widths, DI and its estimated/actual status.
- `hornlab_search/design/generators/`: geometry construction and real shape parameter semantics, including `lecleach_swept_hv.py`, `klangfilm_lame_family.py`, `rolled_family.py`, `section_lame.py`.
- `hornlab_search/design/space.py`, `design/params/`: bounds, active knobs, native/generator mapping.
- `hornlab_search/mesh/build.py`, `mesh/grid.py`: geometric validity, mesh cache and discretization.
- `hornlab_search/search/evaluate.py`, `solve/cache.py`, `dataset/identity_v2.py`: real solver and provenance.
- `hornlab_search/bo/data.py`, `model.py`, `acquisition.py`, `turbo.py`, `pareto.py`, `diagnostics.py`: BO candidate eligibility, fit, acquisition and research diagnostics.
- `hornlab_search/gui/data.py`, `data_bo.py`, `server.py`: shared CMA/BO display, analysis data and run/candidate presentation.
- `tools/analysis/`: immutable offline experiment tools, scoring audit, geometry descriptors, sensitivity and fidelity.
- `docs/evidence/`: actual tests, measured benchmarks and historical campaign artifacts.

## 9. Source-provenance and historical-chat ingestion note

The research was also informed by these available user-provided Horns project summaries:

| User-supplied research snapshot | Material information captured | Access limit |
|---|---|---|
| `Research BoTorch Integration.txt` | Initial GP/TuRBO feasibility, objective/surrogate mismatch, study design and caveats | Full uploaded text inspected |
| `Senior Review Horn Optimization.txt` | Senior comparison of horn typologies, source/baffle/metrics and methodological priorities | Full uploaded text inspected |
| `Review Elliptical Horn Geometry.txt` | Bounds/envelope discovery and the subsequent 12 Klangfilm plus 10 Le Cléac'h seed/contact-sheet proposals | Full uploaded text inspected |
| `Compare Mesh Configurations.txt` | Report of a previous completed 40 KB local-agent engineering handoff | Snapshot only linked to the generated .md, whose original bytes were not provided here |
| `Prioritize Fable Tasks.txt` | Report of an 8-file Fable architecture handoff, recommendations on specialized vs universal families | Summary and artifact links only; original full ZIP not accessible from this snapshot |

**Important:** The summary “Fable” handoff explicitly warns a universal/master typology may be a huge inefficient search space and that categorical controls challenge the present BO adapter. The right architectural experiment is **not** to assume one geometry family must swallow every different acoustic topology. Compare specialized families with shared dataset/search/analysis, composable hybrid geometry, constrained freeform geometry, and quality-diversity search. Source: [typology search-layer gaps](https://github.com/llevaachingada/Hornfab/blob/main/docs/research/typologies/SEARCH_LAYER_GAPS.md).

**Missing-material policy:** If a future agent needs the old PDF named `hornlab-search(2).pdf`, the past 40 KB mesh handoff, the original Fable ZIP or unpublished local experiment files, it should locate their exact current bytes before making claims about their contents. A text summary and a link from a prior conversation are not a faithful replacement for the full artifact.

**Outside-source policy:** For any claim copied from this file, cite the original paper/patent and exact applicable HornFab code or experiment. If the model returns an opinion or synthetic proposed geometry, tag it `[I]` until a separate BEM experiment supports its acoustic performance.

---

## 10. Agent-ready research backlog, ranked by information value

| Priority | Question / small proof of concept | Why it matters | Required artifacts / acceptance |
|---|---|---|---|
| **P0** | Verify resolved scoring curve for every non-CD brief; render the *actual* H/V/DI targets the score uses | Correct false claims of sloped scoring that only alter one DI slope term | YAML + target JSON + exact objective breakdown + GUI overlay tests |
| **P0** | Establish a shared, provenance-safe acoustic comparison of OSSE, R-OSSE, JMLC, Keele biradial, Crowe-inspired, hybrid | Prevent J from a different task becoming a fake acoustic ranking | Same source, mounting, mesh convergence, full polars and impedance |
| **P0** | Separate geometry/budget/product-envelope refusals and audit BO adapter eligibility per typology | Recover discovery outside narrow product box | Admission report with refused reasons and actual physical dimensions |
| **P0** | Verify scoring replay and historical raw-cache preservation | Avoid wasting expensive 4060 BEM work | Bit-for-bit or tolerance-defined original score replay, immutable new score table, backup manifest |
| **P1** | Differentiate mesh-vs-frequency-grid error in 8/12/16/20 kHz pilot | Learn what truly causes bad HF finalists | Fixed-frequency mesh convergence and fixed-mesh frequency densification |
| **P1** | Compare high-frequency 2-cut/selected-angle sentinel vs solved full balloon | Cheaply reject awful HF while avoiding false confidence | Precision/recall with false-negative confidence and GPU-hour cost |
| **P1** | Test near-throat transition, aperture/shape change and realistic source variation | Avoid optimizing an ideal driver-exit artifact | Reference actual driver source or modal-projection boundary, independent verification |
| **P1** | Extend CMA and BoTorch run viewer to the same 3D/acoustical candidate inspection | Turn studies into interpretable searchable research | One canonical candidate/detail viewer and BO uncertainty/trust-region views |
| **P1** | Do paired three- or four-family comparison with small physical budget | Identify true cross-family acoustic trade-offs before huge search | Common beamwidth/DI, loading, geometry, source and compute report |
| **P2** | Prototype restricted multimodal/adjoint screening and uncertainty-driven multi-fidelity BO | Possible major reduction in verified cost for supported families | Out-of-sample rank agreement and fixed-cost HF improvement |
| **P2** | Model a full MEH subsystem with realistic port/chamber/source/crossover | Separate visual shared-aperture geometry from true coupled loudspeaker | Port transfer/impedance, rear volume, modal validation and measured reference |
| **P2** | Analyze acoustic geometry descriptors and QD Pareto archive across past solves | Generate transferable design insight rather than more per-family J | Versioned feature/label table, held-out tests and meaningful Pareto axes |

### Proposed canonical record template for any new research finding

```yaml
finding_id: HF-2026-###            # unique, immutable
claim: "Precise, falsifiable statement"
status: verified_repo | verified_primary | experimental | inferred | refuted
scope:
  typology: "osse / jmlc / meh / etc"
  source: "physical driver or ideal velocity boundary"
  geometry_version: "versioned generator identity"
  mounting: "free / baffle / finite enclosure"
  fidelity: "mesh hash, backend and frequency grid"
  objective: "version + resolved target hash"
primary_sources:
  - title: "Original study / paper / patent"
    url: "https://..."
    full_text: true              # only if verified
repo_sources:
  - path: "docs/research/..."
    commit_sha: "<actual reviewed commit>"
evidence:
  - run_id: "<real run ID>"
    data_path: "<real source of numerical output>"
    metric: "H/V -6 dB main-lobe connected beamwidth"
    units: "degrees"
limitations:
  - "What this result cannot establish"
next_test: "Smallest falsification / replication experiment"
```

### Final working rule

**Build a knowledge base of verified acoustic behavior and trustworthy geometry/solver identities, not merely a leaderboard of optimizer scores.** HornFab's biggest strategic opportunity is using its existing simulations as reusable physical measurements while testing genuine horn-design hypotheses under correct source, mounting, frequency and objective assumptions.
