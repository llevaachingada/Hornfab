# E3 — frequency staging: conservative partial replay

Recorded 2026-11-16 at repository HEAD `207f97a29e2f2f31a366da95e882f9b48761ab00`. Read-only: no solves, process control, tracked-file, queue or run changes. Detailed E3 brief was added concurrently and used. This is **not a complete E3 test**: the bound is conservative, frequency order has not been optimized per lane, and real elapsed savings are unmeasured.

## A. What the wrapper supports

`hornlab_search/solve/beat.py:599` partitions requested frequencies, and `:783–807` calls `solve_frequencies` on each group and stacks the responses. CUDA/Metal default to one call per frequency; CPU defaults to one batch (`:616–658`). The loop does not expose intermediate responses to the caller or permit an objective-driven stop; returning, persisting, combining and resuming incomplete responses would need interface work. Separate subset requests on the same mesh are conceptually possible, but transparent incremental cache reuse and no repeated setup are not established: cache keys identify the full solve (`hornlab_search/solve/cache.py:1–3,78–79`) and `SolveSpec` serializes the frequency list (`hornlab_search/types.py:96–104`). There is existing band splitting and response stacking in `search/evaluate.py:1196–1276`, but that does not establish a staged stopping interface.

Cost is not universally proportional to frequency count. `TOOLCHAIN.md:105–132` reports a warm 5,140-DOF 12-frequency batch at 688.9 s versus 33.3 s for 12 single-frequency calls, 2.3–3.0 s each; the 2,369-DOF warm single call is 1.42 s versus 27.2 s cold. Mesh setup and worker/JIT overhead exist, and earlier measurements are hardware and workload specific. Frequency calls saved cannot be equated with wall-clock savings.

## B–C. Replay of a conservative actual-J lower bound

The replay covers 3,414 valid 18-frequency stored designs across 35 config/brief lanes, sorted by recorded `created` time; ties preserve archive order. The first design in each lane is fully revealed. At every subsequent reveal, the incumbent is only the best **fully revealed** prior candidate in that lane. Fixed frequency order chooses the grid points nearest crossover, geometric mid-band, high band edge and low band edge (deduplicated), then remaining points in grid order. Stop when the lower bound exceeds incumbent plus the specified margin. No learned order or look-ahead is used.

The lower bound is the sum of already observed v7 horizontal and vertical coverage-error contributions, using the full-grid frequency weights, masks, full-grid denominators, narrow-side ratio, vertical-plane weight, configured coverage weight and tolerance. The 8 kHz floor and all other terms are bounded below by zero. That includes the non-additive DI slope and variability, flatness, loading crossing, ripple and diagonal terms: **zero is conservative, not their exact conditional optimum**. The calculation assumes nonnegative v7 term weights and nonnegative terms and symmetric V. The script checks configured weights and every stored weighted term, checks that the weighted terms reproduce each stored J, and checks the coverage bound against every stored J; no included record failed or was skipped. Those empirical checks do not constitute a proof for every conceivable future response, scoring branch or invalid solve. Each omitted term can be strictly positive even under an optimal completion, so this rule leaves useful information on the table.

| Margin (J) | Frequencies saved of 61,452 | Saved | Incomplete training rows | Wrongly abandoned final lane top decile |
|---:|---:|---:|---:|---:|
| 0.5 | 76 | 0.124% | 26 | 0 |
| 1.0 | 54 | 0.088% | 22 | 0 |
| 2.0 | 30 | 0.049% | 14 | 0 |

At margin 0.5 the four chronological lane quartiles comprise 866 / 850 / 856 / 842 designs, and save 10 / 14 / 41 / 11 frequency calls, respectively. For margins 1 and 2 the corresponding calls saved are 6 / 11 / 28 / 9 and 1 / 6 / 17 / 6. Percentiles define the final top decile in each complete historical lane, including ties. Stopped rows would be incomplete training examples; no estimates fill in their missing responses.

## Verdict and limits

The success threshold of 40% is **not demonstrated** by this conservative rule. The <20% failure threshold **cannot be concluded for frequency staging in general**, because tighter rigorous bounds, other fixed or lane-specific frequency orders and a prospective implementation have not been evaluated. The requested in-sample per-lane separation-maximizing order was omitted; it would also be optimistic without a held-out evaluation. The brief asks for the best achievable J under partial observations: no exact minimization over response completions was performed, and no claim is made that zero-valued residual terms can jointly be attained. Future work needs rigorous conditional lower bounds and validates them across scoring branches, then a time-respecting held-out choice of frequency order. Frequency-count savings are not wall-clock savings.

Reproduce: `.venv/Scripts/python.exe scratch/fable_architecture/.e3/lane_replay.py`; per-lane results in `.e3/lanes.json`. `.e3/replay.py` is an abandoned diagnostic on study pairs and was not used in the table.
