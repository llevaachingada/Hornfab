## v3 update (2026-11-16): adaptive discovery and search supervisor

**Use this v3 package in place of v2.** Remote GitHub `main` is now [`2c0e2928e932a47975fc284401eafa74ebfc5002`](https://github.com/llevaachingada/Hornfab/commit/2c0e2928e932a47975fc284401eafa74ebfc5002); older sections below name the earlier `913c934d` review snapshot and remain historical. Local state and active jobs must be checked before any action.

The owner's additional hypothesis is that a **data-driven search supervisor** could stop low-value arms, change the next queue item, decide whether to try a different family or optimizer, and flag experiments with restrictive bounds. This is a research option, **not a direction to automatically mutate live queues**. Start with [`09_OPTION_ADAPTIVE_SEARCH_SUPERVISOR.md`](09_OPTION_ADAPTIVE_SEARCH_SUPERVISOR.md); the existing cheap-agent delegation should include [`10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md`](10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md) as a shared workstream, *without creating another agent swarm*. Fable should consider the **whole discovery system** (geometry, physics, objective, data, search-policy, resource scheduling and human judgment) and may conclude an adaptive controller is premature.

New companion: [`11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL.md`](11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL.md). **No GPU use, tracked code edit, automatic widening, BO switching or live queue mutation is authorized by these files.**

# Hornfab: discovery architecture research handoff

**Prepared:** 2026-11-16. **Repository:** https://github.com/llevaachingada/Hornfab. **GitHub `main` reviewed:** [`913c934d783bed07a2d805d9732dfeedc11b48e4`](https://github.com/llevaachingada/Hornfab/commit/913c934d783bed07a2d805d9732dfeedc11b48e4). This is a remote snapshot, **not a verified snapshot of the user's local checkout, working tree, running queue, or installed dependencies**. Refresh those facts before acting.

## One-minute recommendation

The next high-value question is not “How do we add a universal typology?” It is **“What geometry representation, acoustic goals, and search organization produce the highest number and diversity of genuinely good horn designs per expensive acoustic solve?”** A master typology is one promising answer, not a foregone conclusion.

Use **cheap local research agents** to prepare a concise, source-backed dossier. Give **Fable** an open, adversarial *discovery pass* with the freedom to study alternative architectures and personally inspect decisive code. Fable may then request **narrow, evidence-producing tasks** from cheap agents, or proceed straight to a final plan if the evidence is already sufficient. Use cheap coding agents for implementation and have Fable review scientifically risky decisions at a few meaningful checkpoints.

This is **evidence preparation → Fable discovery/decision → optional targeted gap closure → final specification → cheap implementation → Fable verification**, not an endless Fable ↔ cheap-agent loop.

**Added optional hypothesis:** The owner's new proposal asks whether **acoustic discovery should extend beyond a product-size envelope**, retaining geometrically valid oversized designs for acoustics-versus-size analysis. This is now a **competing research option**, not a decision. See [`08_OPTION_EXPLORATORY_SIZE_AND_FEASIBILITY.md`](08_OPTION_EXPLORATORY_SIZE_AND_FEASIBILITY.md). Fable should compare its information gain with better geometry parameterization, target regions and quality-diversity before endorsing extra solves.

## What you do, exactly

1. **Read** [`06_REPO_FINDINGS_AND_SOURCE_MAP.md`](06_REPO_FINDINGS_AND_SOURCE_MAP.md) yourself if interested; it contains the preliminary review and links.
2. **Copy** [`01_CHEAP_AGENT_DISPATCH.md`](01_CHEAP_AGENT_DISPATCH.md) into the main local OpenCode agent. That prompt directs it to inspect the actual local checkout and use low-cost read-only subagents where available. You can run it as one agent if delegation is unavailable.
3. The agent creates a dossier in an ignored scratch directory, initially suggested as `scratch/fable_architecture/`. **Review `INDEX.md` and the blockers.** It must not claim results of tests that were not actually run.
4. **Send** [`03_FABLE_DISCOVERY.md`](03_FABLE_DISCOVERY.md) to Fable, pointing it at the generated `INDEX.md`. This is the important, deliberately broad pass.
5. If Fable requests new evidence, send [`04_TARGETED_RESEARCH_LOOP.md`](04_TARGETED_RESEARCH_LOOP.md) to a cheap agent with Fable's request. Otherwise skip this step.
6. **Send** [`05_FABLE_FINAL_SPEC.md`](05_FABLE_FINAL_SPEC.md) to Fable to produce a decision, a minimal discriminating prototype, and a staged implementation plan. Give the implementation tickets to cheaper agents using [`07_IMPLEMENT_AND_VALIDATE.md`](07_IMPLEMENT_AND_VALIDATE.md).

## Repositories, workspaces, and safety

- **Do not create a personal GitHub fork or another working copy solely for the research phase.** The repo's current `AGENTS.md` owner amendment specifies one consolidated local checkout at `C:\Users\hunte\Hrns\hornlab-search`, with no new worktrees/working copies unless the owner explicitly requests them. A future isolated implementation branch/worktree requires an explicit owner decision and coordination with the integrator, not a research-agent improvisation.
- Research agents are **read-only** with respect to tracked source, active configs, Git refs, jobs, and caches. They may write new dossier files to an **ignored** scratch directory, or to an external notes directory if the proposed scratch path is not ignored.
- **Do not run BEM/GPU solves, change solver pins, kill Julia hosts, alter a queue, regenerate tracked documentation, git reset/stash/clean, or modify the main codebase.** The research phase needs none of that.
- The final architecture is **not** constrained to use a single family, keep current YAML taxonomies, preserve current objectives, or prefer BoTorch. It **is** constrained to preserve scientific honesty: original results, attribution/provenance, true solve-versus-score identities, and the ability to reproduce older designs.
- The 600 mm home-width limit is an existing **owner design requirement**, not a mathematical law. Keep it for evaluating shippable home candidates unless the owner revises it. Offline exploratory over-envelope designs may be evaluated separately; do not quietly change existing historical briefs/cohorts.

## One thing to avoid

Do **not** paste entire 800,000-character continuity logs or every typology file into Fable. The dossier should be a **navigable index** of decisive findings with exact line/run references. Fable should open the original files when the conclusion depends on subtle code semantics.

## Documents in this package

| File | Purpose | Who uses it |
|---|---|---|
| `01_CHEAP_AGENT_DISPATCH.md` | Full ready-to-paste local research instruction | OpenCode/cheap parent agent |
| `02_EVIDENCE_FORMAT.md` | Consistent evidence ledger, output structure and quality gates | Cheap agents |
| `03_FABLE_DISCOVERY.md` | Broad, non-leading scientific architecture review | Fable, first pass |
| `04_TARGETED_RESEARCH_LOOP.md` | Close just the gaps Fable judges decision-critical | Cheap agent, if needed |
| `05_FABLE_FINAL_SPEC.md` | Architecture recommendation, minimal prototypes, formal design and tickets | Fable, second pass |
| `06_REPO_FINDINGS_AND_SOURCE_MAP.md` | Independent repository review and external research leads | Everyone; verify against live local tree |
| `08_OPTION_EXPLORATORY_SIZE_AND_FEASIBILITY.md` | Added optional decoupled acoustic discovery vs size-feasibility hypothesis; verified code paths, proposed cheap checks, critical unknowns | Cheap agents and Fable |
| `07_IMPLEMENT_AND_VALIDATE.md` | Cheap implementation, integration, independent Fable review | Implementer/integrator |

**Optionality matters:** If the preliminary dossier already answers Fable's questions, do *not* manufacture another research cycle. If Fable uncovers a mathematical question that only it can resolve, it should work the mathematics itself rather than reflexively delegating it.

## v3 additional documents

| File | Purpose |
|---|---|
| `09_OPTION_ADAPTIVE_SEARCH_SUPERVISOR.md` | Research-based new adaptive watchdog, optimizer portfolio and GPU allocation option; code source map and architectural alternatives |
| `10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md` | Focused read-only local evidence assignment integrated with the existing cheap-agent pass |
| `11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL.md` | Offline replay, shadow-mode and matched adaptive-policy validation standards |
