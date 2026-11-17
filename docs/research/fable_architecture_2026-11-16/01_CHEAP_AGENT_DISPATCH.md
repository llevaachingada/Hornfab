## v3 mission expansion: search supervision and experimental resource allocation

Before dispatching, also read `09_OPTION_ADAPTIVE_SEARCH_SUPERVISOR.md` and `10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md` from this handoff package. The architecture decision now includes **whether and how to govern experiment progression**, not just geometry and acoustic scoring. Fold the detailed watchdog/optimizer/queue audit into the existing optimizer and constraint investigator responsibilities; **do not add four more agents or re-run investigations already documented**. Assign any leftover questions to the same low-cost parent. Deliver the five evidence artifacts named in `10_...` alongside the main INDEX, and record contrary evidence. Inspect local git state/current code (remote main advanced to `2c0e2928...`) before claiming what is live. **No automatic search, queue, domain, policy or GPU mutation**; hypothetical actions are research notes only.

# PASTE INTO OPENCODE / A LOW-COST LOCAL PARENT AGENT

## Mission

Prepare a rigorous, **read-only architectural evidence dossier** so a scarce, high-reasoning model (Fable) can make better decisions about Hornfab's future geometry and optimization system without wasting its attention on broad file discovery. **Do not design the final architecture.** The goal is to clarify the actual decision space, including alternatives to the owner's current ideas.

The open design question is: **What representation of horn designs, design goals, feasibility constraints, and search process will discover more acoustically excellent, diverse, feasible horns per unit of compute, while retaining the value of existing results?** Do not assume that a universal master typology, hybrid toggle system, Bayesian optimization, CMA-ES, or rewriting the existing software is best.

## Before touching anything

1. Read `AGENTS.md`, `CLAUDE.md`, `docs/INDEX.md`, `docs/CODE_MAP.md`, the **current** `docs/CONTINUITY.md` / `docs/ISSUES.md` headings, and applicable existing research/skills. Follow their newest owner amendments. Do not read giant historical files in full unless a specific question requires it.
2. Verify repository root, current local HEAD, branch, `git status --short`, active runner/queue state **read-only**. Record whether your checkout equals remote `main` (`913c934d...` was the snapshot reviewed by an outside advisor on Nov 16, 2026). You may not infer what is running from old documentation.
3. Do **not** fork, clone, create worktrees, switch branches, reset, clean, stash, commit, push, merge, edit tracked files, change solver pins, interrupt or start jobs, launch BEM/GPU solves, or modify production caches. In particular, avoid any commands that could clear Julia/CUDA workers during a live queue.
4. Create a notes directory *only if ignored*: test `git check-ignore scratch/fable_architecture/INDEX.md`; if not ignored, write an **external** notes directory and record its path. Preserve all other agents' work. Use `.venv\\Scripts\\python.exe` for approved, pure offline diagnostics, not bare Python.
5. Prefer existing run logs, source, test fixtures, analysis scripts and research papers. Any optional CPU-only experiment must be time/size bounded and write only in scratch; if not safe, report the proposed test without running it.

## Delegation strategy

Use **up to four small, independent, low-cost investigator agents** if your runtime supports them; otherwise complete the same tasks sequentially. Each has **read-only access** and a named output file. Ensure subagents are actually on a low-cost model: do not quietly inherit Fable/Opus pricing. No agent has authority to modify app code or run acoustic solves. Four independent analyses are generally better than a 12-agent swarm that repeats the same source exploration.

### Investigator A: shape languages, families, parameters

Read as needed: `hornlab_search/design/space.py`, `design/generated.py`, `design/families.py`, `design/generators/registry.py`, `design/generators/grid.py`, `design/generators/profiles.py`, `design/generators/rolled_family.py`, `design/params/*`, `hornlab_search/mesh/grid.py`, `examples/catalog.yaml`, representative `examples/typologies/**`, `docs/TYPOLOGY_PLAN.md`, and `docs/research/typologies/**`. Investigate which existing named configurations are distinct physical constructions, different presets, or merely different search boxes/briefs. Include native OSSE/R-OSSE/ICW, generated FREEFORM, grid/rows and analytic/CAD bridges, not just one family.

Inventory the **semantics and units** of parameter knobs and which are fixed, searched, derived, conditional, redundant, inactive, clipped or coupled. Check whether features that appear modular in YAML actually compose in the final *meshed* surface. Review `tools/analysis/parameter_activity.py`, `tools/analysis/geometry_effects.py`, `tools/analysis/geometry_descriptors.py`, `tools/analysis/links.py`, and `hornlab_search/search/links.py` before inventing anything new. Distinguish genuine geometric equivalence from two designs that merely resemble one another.

List **at least three alternative representations worth considering**, *without ranking yet*: e.g., retain specialized physics-based families but unify data/search; composable profile grammar with conditional parameters; shared physically constrained freeform surface; latent or descriptor-based shape search. Add other options if evidence supports them. Include tradeoffs and incompatibilities, particularly throats, asymmetric/swept surfaces, lip rollbacks, source mounting, and multi-entry horns. Output `GEOMETRY_AND_PARAMETER_MAP.md`.

### Investigator B: failure modes, constraints, and boundaries

Read `hornlab_search/search/evaluate.py`, `search/outcomes.py`, `search/cma.py`, `search/cma_me.py`, `hornlab_search/design/generated.py`, `mesh/*` and the actual validators referenced by failure strings. Use only extant run data and bounded offline scripts to quantify refusal categories across **representative recent and contrasting runs**: geometry, envelope, resource/dof, solver/infrastructure, scoring/metric. Report denominators correctly and individual causes, not merely “25% invalid.” Read `docs/status/2026-11-14/README.md`, `docs/queue/TRITONIA_V9_CMA_AUDIT_2026-11-16.md`, and present status reports.

For each frequent failed constraint, classify: hard mathematical impossibility, software/mesher limitation, symmetry convention, manufacturability issue, fixed owner requirement, arbitrarily tight search bound, or not yet known. Separate **cheap feasibility prediction** from **legitimate acoustic simulation**. Investigate existing flat/graded penalties, strict resampling, `search.links` limitations, and what the optimizers actually learn from failures. Do not advise blindly solving self-intersecting horns; do not label over-envelope but otherwise valid horns as acoustically poor. Output `FAILURE_AND_BOUNDARY_AUDIT.md` with before/after experiments proposed but not run.

**Additional bounded option to investigate (not assume):** Read `08_OPTION_EXPLORATORY_SIZE_AND_FEASIBILITY.md`. Determine whether oversized but mathematically sound candidates are discarded as product-envelope failures, and where in native/generated/GRID/CAD paths that happens. Trace generator → cheap envelope estimate → mesh → evaluator → BO pool; verify each failure status rather than lumping all as `invalid_geometry`. Compare the generic GRID estimator (`design/generators/grid.py::envelope_extents`) to axis-projected actual extents when an offline, safe, no-GPU test is possible. Measure refusal denominators and feasibility/cost predictions. Put a discrete section or `SIZE_FEASIBILITY_EVIDENCE.md` in the dossier. **Do not prescribe changing the production 600 mm brief, commit to a fixed exploratory size, or allocate GPU budget.**

### Investigator C: objectives, briefs, acoustic truth, data reuse

Read `hornlab_search/targets/spec.py`, `objective/scalar_v7.py` and its helper terms, `metrics/polar.py`, the home landscape brief YAML, `docs/queue/HOME_SCORE_AUDIT_2026-11-16.md`, `docs/evidence/HOME_OSSE_HIFI_RERANK_2026-11-16.md`, `tools/analysis/hifi_rescore.py`, the QD descriptor code, and relevant research. Examine whether “80H × 50V” acts as a precise target, how frequency, asymmetry, flat DI, lobes, narrowing floors and missing metrics affect ranking. Distinguish what the score really implements from what we believe makes a horn sound good.

Explore **design goals as a region/set**, e.g. acceptable H/V coverage bands and frequency-dependent behavior with smoothness or robust margins, versus exact targets; also consider Pareto menus, utility/preference learning, human selection, system/DSP-aware measures and staged rejection criteria. Do not simply recommend a wider tolerance or replacing one unvalidated metric with another. Identify what could be recomputed from preserved responses at **zero GPU cost**, and what genuinely requires additional angles, frequencies, source physics or full solves. Read `hornlab_search/dataset/identity_v2.py` and BO cohort data code for reuse semantics. Output `OPTIMIZATION_AND_BRIEF_AUDIT.md` (coordinate with investigator D for optimizer details).

### Investigator D: search algorithms, model compatibility, outside methods

Read `hornlab_search/bo/{encoding,data,cohort,model,policy,pareto,turbo}.py`, `studies/*`, `search/{cma,cma_me,nsga,warmstart}.py`, run/campaign docs and optimizer comparison protocol. Establish **implemented versus merely documented** features: scalar BO, TuRBO, Pareto, CMA, CMA-ME/MAP-Elites, validity handling and mixed/discrete optimization limitations; be precise about when a GP can share observations across shape families, source models, mesh/fidelity and score definitions.

Study primary documentation/papers on (a) conditional or mixed continuous/categorical search, (b) constrained black-box optimization, (c) quality-diversity and multiple locally optimal solutions, (d) parameterization and active subspaces or sensitivity, and (e) robust/multiobjective engineering design. Start with the links in `06_REPO_FINDINGS_AND_SOURCE_MAP.md` but challenge their applicability. Look for **negative results, model failure, scaling behavior and the cost of extra dimensions**. Do not assert “BoTorch learns from every refusal” if its training data excludes them. Output `EXTERNAL_EVIDENCE.md` and a short optimizer subsection for `OPTIMIZATION_AND_BRIEF_AUDIT.md`.

## The parent agent: consolidate and audit

1. Read all four investigator reports (or your own sequential outputs) and inspect their *decisive cited primary evidence*, especially where reports disagree.
2. Produce `EVIDENCE_LEDGER.md` with atomic, status-labeled findings following `02_EVIDENCE_FORMAT.md`.
3. Produce `SOURCE_INDEX.md` pointing to exact local paths and commit/ref; clearly mark old branch-only or historical claims.
4. Produce a **short, high-signal `INDEX.md`**: the question, live repo snapshot, top ~8–12 findings, important contradictions, three-to-five plausible architecture routes (without preselecting), unknowns worth Fable's thinking, and navigable pointers. Do not duplicate whole reports there.
4a. Explicitly include or rule out **separate over-envelope acoustic exploration** among the candidate strategies, with evidence of its benefit, numerical feasibility, and why Fable might instead reject it. Treat existing within-envelope baselines as controls; don't infer that unsolved oversized geometries would sound better.
5. Produce `OPEN_QUESTIONS.md`: questions sorted by whether the answer could change architecture, tests that a low-cost agent can do, and questions requiring original scientific/mathematical thought.
6. Check no tracked files changed from your own actions, without modifying or resetting anything. Report any pre-existing modified files honestly, rather than blaming or overwriting them.

## Completion standard

Stop with the dossier and a short message giving its directory and the `INDEX.md` path. **Do not start implementing the first architecture you think of.** The next model should be free to disagree with everyone, including the owner and this prompt.
