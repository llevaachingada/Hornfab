## v3 conditional implementation path for adaptive supervision

Only if Fable's completed architecture decision supports it: begin with read-only historical replay and an **advisory, non-actuating shadow supervisor**, preferably reusing `tools/run_campaign_night.py` and `tools/analysis/optimizer_switch.py` rather than adding a competing runner. Only consider between-job automatic proposals and queue edits after owner-approved versioned policy, admission checks, exact rollback/audit, tests, and honest controlled validation. The existing 30-second watchdog remains responsible for defined safety/stop semantics. Do not bypass optimizer-internal convergence/restart rules, automatically train BO on invalid rows, or rewrite in-flight pinned studies. Implement and test the cases in `11_ACCEPTANCE_AND_EXPERIMENT_PROTOCOL.md`; **no execution privileges** are granted by this packet.

# IMPLEMENTATION DISPATCH AND SCIENTIFIC REVIEW

Use **only after Fable has selected a direction and defined an experiment/tickets**. This is an implementation workflow, not a license to merge unreviewed changes.

## To the cheap implementation parent agent

> Read the exact Fable decision, math/interface spec, minimum experiment and implementation tickets under `scratch/fable_architecture/`. Read current `AGENTS.md`, `CLAUDE.md`, `docs/CONTINUITY.md`, `docs/ISSUES.md`, `docs/FORKS.md` and the relevant research skill before editing any source. Verify `HEAD`, active jobs, git status and ownership. **Do not** assume the GitHub snapshot reviewed by the researcher matches the local checkout.
>
> Present a **safe integration plan** to the owner/integrator before starting changes. The repo's current owner amendment requires one consolidated checkout and only the parent integrator may perform Git mutations. Do not create worktrees, branches, forks or parallel working copies without explicit approval. If a live night/study is running, do not change its pinned execution code/config. Coordinate file ownership; use disjoint paths for any permitted concurrent implementation.
>
> Implement **one ticket or minimal experiment at a time**. Preserve existing production paths and semantics by default; use feature flags or versioned new interfaces when appropriate. Do not rewrite established BEM, mesher, score, data identity or valid published-horn shape equations merely to simplify the code. Changes to external mesher/solver packages go through pinned forks and their test ladder. Protect old solve/metric/score/study identity and full replay.
>
> For each ticket supply a short `TICKET_##_REPORT.md`: exact commit/branch, code changes, formal constraints and edge cases, tests with **raw command/output**, regressions, changed semantics, unimplemented aspects and negative findings. No claim of better acoustics or search performance without a fair independent measurement. Unless explicitly authorized, do not run GPU BEM, kill existing hosts or modify queues.
>
> Stop on conceptual conflicts instead of inventing an answer contrary to the spec. Give Fable a concise technical issue with exact tests/evidence if a mathematical design is ambiguous. Do not treat a green unit suite as proof of correct acoustics.

## Fable verification prompt (use at decision milestones, not every commit)

> Independently assess the implementation of `FABLE_DECISION.md` / `FABLE_MATH_AND_INTERFACES.md` against the merged code and the integrator's ticket reports. Do not trust the implementer's summary. Check the **mathematics, geometric admissibility, source and symmetry assumptions, parameter identifiability, constraint semantics, acoustic scoring behavior, data/cohort/score identity, and equality of historical designs**. Compare old-versus-new control results, not only new tests. Identify exact flaws and the smallest corrective tickets. Classify results as proven by CPU, independently validated BEM, or still hypothetical. Only recommend more GPU solves if they can materially change the architecture choice and have a controlled protocol. Do not overwrite other agents' work.

**If Fable chooses the optional size-discovery path:** Keep original production brief/cohort hashes untouched, version the new exploratory policy/brief, test generator + prefilter + final-mesh semantics and optimizer admission consistently, verify false-positive/false-negative envelope decisions against real surface extrema including diagonals, preserve measurement/score/study identity, and never convert unmeshed refused designs into acoustic training labels. No oversized GPU campaign without explicit owner authorization and resource validation.

## Practical acceptance metrics, to customize rather than blindly enforce

- **Valid surface yield**, measured on comparable candidate samples, split by reason and using an honest denominator.
- **Discovery efficiency**: independently verified improvements, viable distinct solutions, and time/cost per verified acceptable design, not just minimum screen J.
- **Coverage diversity** of high-quality *verified* designs across the user's permitted acoustic region, without rewarding dirty polar lobes or inconsistent frequency behavior.
- **Physical equivalence/reproducibility**: published reference shapes and preexisting saved-design surfaces maintain expected construction; new shapes have explicit units, symmetry, source and mesh conventions.
- **Data reuse correctness**: old responses survive and can be re-scored when physically supported; incompatible modes, changed physical assumptions and unavailable frequencies do not silently mix.
- **Model generalization**: held-out geometry groups, several seeds, and cold/warm-start controls where feasible; don't compare a pre-trained BO agent against a zero-data CMA search as an equal-information test.
- **Adversarial failure cases**: clipped controls, degenerate shapes, non-round driver joins, folded/rolled lips, envelope overshoots, underresolved mesh and high-frequency lobes.

## Default implementation order

Fable should choose the order. A sensible provisional sequence if its science supports it is: independent characterization and tests → candidate shape/feasibility prototype → offline objective/region/QD comparison using preserved responses → bounded single-family pilot → selected cross-family/generalization pilot → integration and GUI. **No project-wide refactor first.**
