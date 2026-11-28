---
name: hornlab-search-economy
description: Prove a hornlab-search run has somewhere to go before spending GPU time, and explain a run whose best J is its seed. Use when authoring or editing a search config's bounds/sigma0/budget, restarting from a prior best, building an A/B or seed-variance night, queueing configs after a report, or reading a run/night where the best eval is n=0. Covers converged incumbents, step size vs basin, refusal budget, inert graded penalties, and A/B attribution. Not for solver/mesh mechanics (hornlab-gpu-job) or geometry-only checks (hornlab-shape-check).
---

# hornlab search economy

A run can only improve on its start point. Before GPU time, prove three things: (1) the start is
not already the converged optimum, (2) the sampler can reach the region where a better design
lives, (3) enough valid evaluations survive refusals to try. `tools/search_preflight.py` computes
all three from the config and the prior runs; run it before writing the night file.

## The gate

```powershell
# new config, no history yet: seed-in-box + declared search settings only
.venv\Scripts\python.exe tools/search_preflight.py <config>

# before committing a night (history + a real box sample):
.venv\Scripts\python.exe tools/search_preflight.py <config> `
    --from-runs runs\<prior-run> [runs\<prior-run-2>] --samples 64

# an A/B pair: does the treatment move a dimension that binds?
.venv\Scripts\python.exe tools/search_preflight.py <arm> `
    --ab <control> --from-runs runs\<prior-run>
```

Exit 1 on a hard fault (seed outside its bound, mesh-consistency error, config error); `--strict` promotes warnings.
Everything else is a report computed from the config and history, never a fixed table.

## What the checks mean

1. **Seed in its own box.** A searched key outside `[lo, hi]` is clipped by
   `DesignSpace.normalize()` without failing the run, while eval 0 still scores the unclipped seed
   — the run starts somewhere the optimiser never revisits. Missing keys are filled with the bound
   midpoint (also silent). Move the seed inside, or widen the bound deliberately.
2. **Headroom.** If the seed equals the prior run's best — same design hash, or same values on every knob with
   only new neutral DOF added — the run starts at the converged optimum. A config that only adds law amplitudes
   at 0 is a nested incumbent: its hash changes, its geometry and J do not. That is a re-test, not a search; give
   it a reason (a new DOF, a new brief) and a step small enough to refine. Otherwise it relearns the optimum.
3. **Resolution.** `sigma0` is in per-dimension box units. The tool reports the prior run's top-k
   spread, the recommended sigma, and the expected number of valid samples that land inside that
   spread (`chi-square_d`). Native families go through the production
   `search.warm_start.sigma_from_spread` path (`hornlab_search/search/warmstart.py`); generated families use an equivalent local fallback
   because `warmstart` cannot read their `params.<generator>.knobs` rows today. If the expectation
   is below the policy floor, the budget cannot find the region. Fix the step, the budget, or the
   box — in that order. A measured spread far below `sigma0` with best-at-eval-0 is the signature
   of this failure.

   **Measured backing (2026-11-17, `docs/evidence/SIGMA0_ANALYSIS_2026-11-17.md`).** sigma0 and bound width
   are ONE decision. Controlled A/B (12 keys): sigma0 0.25 on global bounds → 24/45 refusals, zero gain;
   sigma0 0.10 on seed-centred ±30 % bounds → best J −56 % by eval 102, 9 refusals. Retrospective (~80 runs):
   refusal storms track sigma0 × free-keys × box width. Starting points until the preflight sweep runs:
   greenfield/global/<6 keys 0.15–0.20; ±20–30 % seed-centred 0.08–0.15; refinement 0.05–0.12. Never ship
   sigma0 ≥ 0.25 on >8 free keys or global bounds; a flat trace with ≥30 % refusals is the storm signature.
4. **Economy.** With `--samples N` the tool samples the box **uniformly** through the real
   generator/mesher and reports the valid fraction and refusal kinds *before* the queue. CMA
   concentrates near the seed, so read the uniform number as a bound — it over-represents the far
   corners (H1: 4/4 uniform refusals against 22-36% in the actual run) — but never assume the
   plan's predicted refusal rate. Measure, then fold the fraction into expected hits.
5. **Penalty path.** `infeasible_penalty: graded` only grades `invalid_envelope`, which the
   generator emits from its pre-mesh estimate. Native families discover envelope overshoot after
   meshing (`invalid_geometry`), so they receive the flat 1000 penalty and CMA gets no gradient.
   When the report says graded is inert, either use `infeasible_penalty: resample_strict` +
   `budget_counts: valid`, or accept the flat wall and budget for it.
6. **Attribution (A/B).** `--ab` diffs the two configs' bounds; with history it reports the prior
   top-k's **binding keys** (keys pinned at a bound) and whether the treatment moves them, plus
   which changed keys are inactive. A treatment that leaves a binding key untouched cannot relieve
   the constraint — the L1 case: every winner pinned `g_stop_deg` at 120, while the treatment moved
   `g_fc_hz`'s lower bound. An added region with no prior top-k rows is expected for a widening
   experiment (INFO), not a defect; confirm the treatment run samples it. A negative is only a
   negative when the treatment dimension was active, the added region was actually sampled, and
   the control had headroom; otherwise it is an untested hypothesis.

## BO identity and starts (metric-BO)

- **Identity = brief + bounds** (+ objective/scorer version). `ActiveProjection.identity(space)` encodes one
  `DesignSpace`; the box identity is `bo.metric_identity.bounds_identity` — a sha256 of per-key physical bounds
  and transforms (`hornlab_search/bo/metric_identity.py:159-161`) — and the score identity is objective version
  + brief hash (`:200-236`). A different brief or a changed bound is a **different identity**: rows do not pool
  and J is not comparable.
- **One box per family so runs pool.** Repeat runs of a family must reuse byte-identical searched bounds; the
  two rolled campaigns share one identity and pool to 200 rows (`docs/evidence/cd_bo_cohort_2026-11-25/PREDECLARED.md:18-22`);
  `check_explore.py:24-30` prints distinct boxes per family.
- **>=100 usable rows per identity; aim for >=5 groups (independent runs).** `tools/bo_compare/prepare_study.py`
  refuses below `--min-rows` (default 100: `:76`, `:165-167`). The A/B verdict rule becomes a real verdict only at
  >=5 runs, else "indicative" (`tools/analysis/_common.py:1053-1061`), so spread rows over >=5 runs, not one long one.
- **Snap exploration starts; the seed hash must round-trip.** Sobol/scrambled starts are full float precision, but
  the space rounds knobs on denormalize, so an unsnapped start is "not representable" and `ActiveProjection`
  raises `HashMismatchError`. Snap each start `denormalize(normalize_design(seed, verify_round_trip=False))` and keep
  it only if `snapped.hash() == space.seed.hash()` (`docs/evidence/cd_bo_cohort_2026-11-25/snap_starts.py:20-28`;
  `check_explore.py:21-25` asserts it, and `bo/encoding.py:264-274` is the same check inside `normalize_design`).
- **Explore first.** A CMA exploration cohort makes the valid rows BO needs; open no BO arm until the cohort clears
  the row/group floor. Never widen a queued config's bounds to "add data" — that is a new identity and splits the pool.

## Rules for a queue (write these into the plan before the run)

- Record the predicted best-at and first-improvement eval before launching; compare at readout.
- No treatment without a control in the same lane, same seed, same budget, same objective
  version and brief.
- State the expected refusal fraction and how it was measured (box sample or prior run).
- Put the owner's priority first; a cutoff must never leave a treatment without its control.
- Add `search.warm_start` when the seed came from a prior run of the same family:
  `{from_runs: [...], top_k: 10, sigma_from_spread: true}` — mean = prior best, step = measured spread (clamped
  to `[0.05, sigma0]`); it never changes the solve hash.
- Do not edit a config a queued/running night uses; copy it (the night-queue skill's rule 6).

## Readout (after the run)

`tools/night_status.py --since-hours 24`, then `tools/analysis/convergence.py`, `walls.py` and
`seed_variance.py` on the run dirs. Report: best-at eval, first-improvement eval, valid fraction by block, pinned
dims, and whether predicted headroom was real. A best of n=0 needs one of the six checks named as the cause.

## Evidence behind this skill (2026-11-14, `sab_home_gpu_2026-11-14` + `sab_lecleach_cpu_2026-11-14`)

- [measured] H1 seeds both scored 3.2325 at n=0 and never beat it (a value finding took 191–254 evals elsewhere).
- [measured] sigma0=0.15 in 9-D: nearest valid sample 0.31 normalized; sigma shrank only to 0.107 after 9 generations — no basin entry.
- [measured] 22–36 % refused `invalid_geometry` despite graded penalty; the only arm with real headroom improved at n=117 of 200.
- [measured] L1 A/B: no treatment beat control; every winner pinned `g_stop_deg` at 120 while the treatment moved `g_fc_hz`.
- Lesson: measure the spread, check the seed, sample the box, then choose step and budget — not a fixed sigma or budget.
