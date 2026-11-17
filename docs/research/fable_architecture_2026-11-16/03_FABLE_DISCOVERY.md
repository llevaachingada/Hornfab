## v3 additional discovery question: should Hornfab have an adaptive search supervisor?

Review `09_OPTION_ADAPTIVE_SEARCH_SUPERVISOR.md`, `10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md` and cheap-agent findings. The owner's broader hypothesis is that a hardened workflow could stop/advance low-value runs and propose optimizer, bounds, family and fidelity changes so expensive BEM time yields more real learning. Treat a *watchdog* (safe execution), an *optimizer* (its own convergence/restart logic), and a *scientific campaign supervisor* (choice of next experiment) as different layers. Do not assume a fixed automatic CMA→BoTorch switching rule is best. Examine alternative resource-allocation architectures: minimal human advisory, shadow-mode policy, bounded automated between-job scheduler, optimizer portfolios/racing/bandits, feasibility-aware/multi-fidelity experiment design, or postponement pending scoring/source validity.

**Core adversarial question:** Would a supervisor create verified value, or learn misleading preferences because BoTorch inherits CMA data and because objective/failure/screen-versus-verify conventions drift? Consider matched prior cohorts, per-GPU-hour costs, QD value, physical versus artificial bounds, hard admission, early-stop censoring, and run IDs. Your first pass may ask cheap agents for precise historical replay or cohort-eligibility evidence, but avoid an open-ended loop. Retain your freedom to propose an architecture other than any listed option. No automatic queue/config/domain changes are authorized.

# PASTE INTO FABLE: BROAD DISCOVERY PASS

## Role and mission

You are the independent scientific and computational architect of **Hornfab**, a research-grade horn-loudspeaker design and optimization project. The owner suspects the current software has accumulated overly narrow typology lanes, awkward or inactive shape knobs, over-restrictive geometry bounds, and exact acoustic briefs that exclude equally good but slightly different coverage patterns. These are **hypotheses for investigation**, not decisions to validate.

Your real task: **decide what kind of design-and-optimization system would best discover genuinely excellent, varied, physically valid horns with the least expensive acoustic simulation effort, while preserving existing research and enabling future scientific progress.** Think like an acoustician, numerical optimizer, geometry researcher and principal software architect. You may conclude that maintaining several specialized families is better than a universal family, that search methodology should be reorganized before geometry, or that the dominant problem lies elsewhere. Question both the owner's and previous agents' assumptions.

## Starting context, not a cage

Read the **locally generated** `scratch/fable_architecture/INDEX.md` and `SOURCE_INDEX.md` first. Open decisive underlying code, run records and original research directly; the cheap-agent dossier is neither a substitute for verification nor an instruction hierarchy. Use the repo's actual `AGENTS.md`, `CLAUDE.md` and newest owner amendments. The earlier independent source map is `06_REPO_FINDINGS_AND_SOURCE_MAP.md`, initially reflecting remote main commit `913c934d...`; this package adds a v3 supplement at `2c0e2928...` as of Nov 16. The local tree may be newer/different.

Current stack includes multiple native/generator/row-based horn shape paths, CMA-ES, CMA-ME, BoTorch scalar/TuRBO/Pareto, a single NVIDIA 4060 laptop GPU with an 8 GB memory budget, idealized driver-source boundaries and expensive GPU BEM. Optimizations have yielded good numerical results but concerning geometry failures, restricted parameters, objective disagreements and screen-versus-verify differences. Existing solves should be treated as valuable data, but **their acoustic fields and provenance determine what is actually reusable**.

## First examine the landscape of solutions

Give serious consideration to genuinely different approaches, including ones **not** proposed by the owner:

- Retain specialist analytical horn families and unify *only* search, comparison, data, and a common geometry/result interface.
- Build a **composable conditional geometry grammar**: parent profile, independent H/V law, mouth and throat, optional folds/ridges/rollback, transition elements, with meaningful active controls.
- Use a **single smooth constrained freeform surface/low-dimensional basis**, possibly initialized by published shapes, with stronger geometric constraints and learned shape descriptors.
- Use **hierarchical search or automatic family/model selection**, with categorical outer decisions and continuous inner searches; evaluate whether mixed-variable BO is viable at this GPU budget or whether QD/evolutionary search is preferable.
- Optimize **a set of acceptable acoustic outcomes** rather than one specific H/V target: goal regions, Pareto frontiers, robust worst-case and frequency-resolved requirements, human choice or room/system-aware utility. Distinguish objective, constraints, descriptors, and final engineering preferences.
- Consider **decoupling exploratory acoustic discovery from final product-size feasibility**. The owner supplied a plausible critique that 600 × 480 × 480 mm home-envelope enforcement currently prunes some otherwise valid shapes before a solve, and that acoustic-performance-versus-size optimization might teach us something important. Read `08_OPTION_EXPLORATORY_SIZE_AND_FEASIBILITY.md` and verify code/evidence. Compare (i) fixing conservative false refusals within the existing brief, (ii) separate, size-relaxed discovery, (iii) size-aware multiobjective or quality-diversity search, and (iv) no extra solves/offline rescoring. This is **an optional hypothesis**, not a mandate to relax the existing home product constraint or to favor bigger horns.
- Use **physics-informed multi-stage or multi-fidelity evaluation**, shape screening and reusable response data to improve sample efficiency, if that solves a more fundamental bottleneck.
- Consider intentionally **not** unifying architectures whose physical source conditions, throat topology, non-star-shaped geometry, multiple entrances or numerical solver assumptions differ substantially.

Do **not** treat this list as exhaustive, a required feature checklist, or a prescription to build all of it. Propose stronger alternatives if warranted. Distinguish near-term highest-value simplifications from speculative research projects.

## Key scientific questions

1. What are the true independent, acoustically important degrees of freedom? Which present parameters are redundant, inactive, ill-conditioned, or force strong but unnatural couplings? Can a parameterization *construct valid shapes by design* rather than relying on a huge post hoc refusal rate?
2. What makes two candidate horns **equivalent enough** to share an optimization model? When is a name/knob vector misleading, and when are canonical geometry descriptors or surface embeddings more appropriate? What hard physical identities must remain separate?
3. Can a broader design space be searched economically? Compare continuous, hierarchical mixed-variable, grammar/evolutionary, local BO, quality-diversity and staged strategies, with actual data requirements and failure modes. Avoid treating the presence of an API as proof of reliable performance.
4. How should truly impossible/non-meshable geometry, a legitimate shape beyond a packaging envelope, and solvable but unpromising acoustic behavior be distinguished? Can feasible-region boundary information be captured without inventing acoustic scores?
4a. Is it scientifically worth solving geometrically valid shapes outside the product envelope, or would this mostly trade increased BEM cost for unhelpful size? Determine whether product limits should be separate from acoustics in discovery, and how geometry validity, size estimates, mesh resources, and optimizer learning should remain distinct. Preserve existing product briefs while testing the idea, if warranted.
5. How do we express a **family of acoustically excellent outcomes** without accidentally rewarding narrowing, lobes, uncontrolled vertical coverage, high-frequency breakup, or wild pattern changes across frequency? How do we quantify tradeoffs with loading, sound power, on-axis response, DSP, room and driver/source uncertainty?
6. What is the smallest credible experiment, using saved response data or CPU geometry work first, that could discriminate between competing architectures? What observations would falsify your favorite design?
7. What important questions are **missing from the owner's framing**? Look for a deeper bottleneck that could render a large geometry refactor premature.

## Output: a broad *decision review* with an adaptive stop

Write `scratch/fable_architecture/FABLE_DISCOVERY.md` containing:

1. **Short verdict:** what is the most consequential problem and why, with uncertainty.
2. **Option comparison:** at least three materially different candidate architectures, benefits/risks, dependency on actual code, probable dimensionality and solver cost, reusable data and likely failure points. Include a reason not to choose each option.
3. **Disconfirming evidence:** what facts argue against your initial favorite; any unsupported premise.
4. **Top uncertainties ranked by decision value**, not by how much reading they would entail.
5. **Do one of the following at your discretion:**
   - **A: Enough evidence.** Declare yourself ready for final specification. Skip additional delegation and explain why.
   - **B: Evidence could change the choice.** Write `FABLE_RESEARCH_REQUESTS.md` with **at most a handful of very precise, bounded requests** for cheap agents: source/data scope, methods, exact output, decision affected, and stop condition. Only request the experiments necessary to choose among architectures.
   - **C: A core mathematical issue needs your reasoning.** Analyze/derive that issue yourself and note what was established. You may propose a tiny **non-production CPU proof of concept** if it gives more information than further writing, but do not alter tracked files or run a GPU solve.
6. A provisional recommendation, clearly conditional where it should be, and a one-paragraph plan for next phase.

**Do not launch production implementation yet.** Do not run GPU/BEM solves, disrupt active work, edit tracked code, mutate Git state or silently loosen existing physical/scientific requirements. You may challenge an owner constraint in your recommendation, but do not change it without approval.

**Think broadly first; choose narrowly only after comparing alternatives.** Spend your expensive reasoning on the decisions, mathematical structure and evidence interpretation. Do not spend it summarizing entire repository files.
