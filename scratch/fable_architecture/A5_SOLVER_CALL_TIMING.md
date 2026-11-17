# A5 — solver call timing and what a staged solve would need

**Run:** 2026-11-16 23:35 ET, HEAD `207f97a`. Code read only; nothing executed against the solver.

## The 689 s versus 33 s record is a known batching cliff, already worked around

- `TOOLCHAIN.md:105-126` (measured 2026-10-12, RTX 4060 8 GB): one `solve_frequencies` call with
  12 frequencies on a 5,140-DOF quarter mesh took **688.9 s** (assembly 672 s); the same 12
  frequencies as **12 single-frequency calls took 33.3 s** (2.3–3.0 s each). At 2,369 DOF the
  12-frequency call took 5.0 s. The cliff appears above about 2.4k DOF and is attributed there to
  memory pressure in the multi-frequency path.
- Production already avoids it. `hornlab_search/solve/beat.py:599-612` (`frequency_groups`) and the
  constructor at `:636-646` set **one call per frequency by default on CUDA and Metal**, one batch
  on CPU (measured no cliff: 18.3 s versus 19.2 s). `HORNLAB_FREQ_BATCH_SIZE` is an opt-in override.
- So this is not an open defect. It is the reason the solve loop is per-frequency.

## Cost is close to proportional to frequency count on a warm worker

- Warm single-frequency cost: 0.4 s at 2,369 DOF, 2.8 s at 5,140, 7.5 s at 7,001, 45 s at 8,941
  (`TOOLCHAIN.md:126`). Assembly dominates each call (1.65 s of 3.21 s at 5,140 DOF, `:117`).
- Fixed costs outside the per-frequency loop: cold start and JIT (27 s first call), meshing (a few
  seconds of CPU), and worker recycling when `worker_restart_every` is set.
- Therefore solving k of n frequencies costs about k/n of the solve time once the worker is warm.

## What exists and what is missing for "solve a few frequencies first"

`beat.py:776-807` (`solve_raw`): the frequencies are already solved one call at a time in a Python
loop, each raw result appended to a list and stacked at the end. A wall-clock timeout is checked
between calls. What the loop does **not** do:

1. return or persist the partial list if it stops early (a timeout raises and discards it);
2. accept a caller-supplied order of frequencies distinct from the stored order;
3. accept a caller decision between calls (continue or stop);
4. mark a stored response as partial, or resume one later on the same mesh.

Everything downstream (`evaluate`, the response cache, metrics, the dataset record) assumes a
complete frequency set. The dataset identity keys the solve by its full frequency list, so a
partial response would need its own identity.

**Conclusion.** Staged evaluation is structurally cheap at the solver boundary (the loop is already
per-frequency) and structurally expensive downstream (partial responses are a new kind of record).
E3 found that a rigorous abandon rule saves almost nothing; unless a better rule is shown on stored
data first, this interface is not worth building.
