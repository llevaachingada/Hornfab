# Targeted cheap-agent response to Fable's research requests

**Use only if Fable's discovery pass identifies evidence that would materially change its architectural recommendation.** One focused research loop is the default; Fable can explicitly justify a second, but do not make repeated handoffs mandatory.

## Paste to a cheap local agent

> You are the evidence investigator for Hornfab. The scientific architect has written a bounded list of unresolved questions in `scratch/fable_architecture/FABLE_DISCOVERY.md` or the accompanying research request document. Read the current repo instructions first. Complete **only** the specific requests marked **decision-critical** and suitable for your tools. Do not make your own final architecture choice.
>
> For each request: quote the question, source scope, what you inspected, the precise evidence with path/line/run/commit identifiers, a clearly labeled result, counterevidence, and any uncertainty that remains. Reuse existing tools, data, tests and past reports before writing a new diagnostic. Optional CPU-only scratch experiments may be done if safe and bounded; report commands and outputs verbatim. Do not initiate GPU/BEM solves, alter active jobs, change tracked code/configs or spawn unbounded subagents.
>
> Put results in `scratch/fable_architecture/TARGETED_FINDINGS.md` and link full logs/data separately. Add a tiny summary to `INDEX.md`. If a question cannot be answered without a real GPU experiment, an implementation change or owner approval, write an exact experiment/decision proposal and **stop there**. Do not fake the result.
>
> After the bounded investigations, list which architectural decisions now have enough evidence and which remain uncertain. Preserve the original Fable request and prior dossier files unchanged.

**If the request concerns oversized acoustic discovery:** Use `08_OPTION_EXPLORATORY_SIZE_AND_FEASIBILITY.md` to frame it as an optional competing hypothesis. The targeted agent can check envelope false-positive rates, execution-path classifications, saved-run size distributions and mesh/DOF cost **without** performing new BEM solves. It should explicitly compare that option with the lower-cost alternative of correcting geometry prechecks inside the current envelope. Do not treat a request for evidence as permission to enlarge the home brief or spend GPU budget.

## What the next Fable turn should contain

Give Fable these three locations, not a huge pasted report: `INDEX.md`, `FABLE_DISCOVERY.md`, and `TARGETED_FINDINGS.md`. Ask it to decide whether evidence is sufficient and then use `05_FABLE_FINAL_SPEC.md`. If insufficient, Fable should explicitly describe the uncertainty and proceed with a reversible provisional choice where possible.

## v3 specialized research requests

When Fable identifies an adaptive-policy uncertainty, assign a **bounded** local task using `10_CHEAP_AGENT_SEARCH_SUPERVISOR_PASS.md`: historical watchdog early-stop replay, eligibility matrix from exact pin-matched BO cohorts, physical-vs-product-bound diagnosis, QD-vs-scalar progress analysis, or queue safety simulation. Demand observations with timestamps and exact run IDs, data-availability cutoff, negative evidence, and a decision that new evidence would change. Do not ask agents to run a new campaign, automatically widen bounds, alter jobs or claim the outcome of an unrun counterfactual.
