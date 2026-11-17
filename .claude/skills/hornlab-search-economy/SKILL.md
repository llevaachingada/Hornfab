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

Exit 1 on a hard fault (a searched seed value outside its bound, mesh-consistency error, config
error); `--strict` promotes warnings. Everything else is a report. The numbers come from the
config and the history, never from a fixed table, so there is nothing to update when a brief
changes.

## What the checks mean

1. **Seed in its own box.** A searched key outside `[lo, hi]` is clipped by
   `DesignSpace.normalize()` without failing the run, while eval 0 still scores the unclipped seed
   — the run starts somewhere the optimiser never revisits. Missing keys are filled with the bound
   midpoint (also silent). Move the seed inside, or widen the bound deliberately.
2. **Headroom.** If the seed equals the prior run's best — same design hash, or the same values on
   every knob the prior run searched with only new neutral DOF added — the run starts at the
   converged optimum. A new config that only adds the law amplitudes at 0 is a nested incumbent:
   its hash changes, its geometry and J do not. That is a re-test, not a search; give it a reason
   (a new DOF, a new brief) and a step small enough to refine. Otherwise it spends evals
   relearning that the optimum is the optimum.
3. **Resolution.** `sigma0` is in per-dimension box units. The tool reports the prior run's top-k
   spread, the recommended sigma, and the expected number of valid samples that land inside that
   spread (`chi-square_d`). Native families go through the production
   `search.warm_start.sigma_from_spread` path; generated families use an equivalent local fallback
   because `warmstart` cannot read their `params.<generator>.knobs` rows today. If the expectation
   is below the policy floor, the budget cannot find the region. Fix the step, the budget, or the
   box — in that order. A measured spread far below `sigma0` with best-at-eval-0 is the signature
   of this failure.

   **Measured backing (2026-11-17, `docs/evidence/SIGMA0_ANALYSIS_2026-11-17.md`).** sigma0 and
   bound width are ONE decision, not two. Controlled A/B on the same 12-key config: sigma0 0.25 on
   global generator bounds → 24/45 refusals, zero improvement, flat from eval 1; sigma0 0.10 on
   seed-centered ±30 % bounds → best J −56 % by eval 102, 9 refusals. Retrospective over ~80 recent
   runs: refusal storms track sigma0 × free-keys × bound width (sigma0 0.22–0.25 on wide boxes:
   25–48 % median refusal with flat tails), while sigma0 0.20 on modest boxes is quiet (1.2 %
   refusal) and refinement at 0.12 near a live basin gains 8 %. Starting points when the preflight
   sweep is unavailable — greenfield on global bounds with <6 keys: 0.15–0.20; seed-centered
   ±20–30 % bounds: 0.08–0.15; refinement at a converged incumbent: 0.05–0.12 and say so in the
   night plan. Never ship sigma0 ≥ 0.25 with >8 free keys or global bounds. A flat trace with
   ≥30 % refusals is the storm signature: stop the arm, sweep sigma0 with the preflight, relaunch —
   do not let budget burn out in refusals.
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

## Rules for a queue (write these into the plan before the run)

- Record the predicted best-at and first-improvement eval before launching; compare at readout.
- No treatment without a control in the same lane, same seed, same budget, same objective
  version and brief.
- State the expected refusal fraction and how it was measured (box sample or prior run).
- Put the owner's priority first; a cutoff must never leave a treatment without its control.
- Add `search.warm_start` whenever the seed came from a prior run of the same family:
  `{from_runs: [...], top_k: 10, sigma_from_spread: true}`. It sets the mean to the prior best and
  the step to the measured spread (clamped to `[0.05, sigma0]`); it never changes the solve hash.
- Do not edit a config a queued/running night uses; copy it (the night-queue skill's rule 6).

## Readout (after the run)

`tools/night_status.py --since-hours 24`, then `tools/analysis/convergence.py`,
`walls.py` and `seed_variance.py` on the run dirs. Report: best-at eval, first-improvement eval,
valid fraction by block, pinned dims, and whether the predicted headroom was real. A run whose
best is n=0 needs one of the six checks above named as the cause; "CMA failed" is not a diagnosis.

## Evidence behind this skill (2026-11-14, `sab_home_gpu_2026-11-14` + `sab_lecleach_cpu_2026-11-14`)

- [measured] H1 seeds 1234 and 5678 both scored 3.2325 at n=0 and never beat it (78 and 65 valid of
  100). That 3.2325 was itself found at n=191/254 in `51328c` and n=196/200 in `18985d`; H1 then
  got half the evals that took.
- [measured] sigma0=0.15 in 9-D: the nearest valid sample to the seed was 0.31 normalized (J 3.59),
  median distance ~1.0, median J ~6.2; sigma shrank only to 0.107 after 9 generations. No sample
  entered the basin.
- [measured] 22–36% of evals were refused `invalid_geometry` ("outside the brief envelope (width
  816 > 600.0 mm)") despite `infeasible_penalty: graded`; every refusal carried the flat 1000.
- [measured] The one arm with real headroom, C1 narrow, improved 2.1283 -> 1.9699 with the first
  gain at n=117 of 200 — at the end of its budget.
- [measured] L1 A/B: all arms improved from 1.6019 (~0.83–0.90) but no treatment beat control.
  Every winner pinned `g_stop_deg` at 120 (its lower bound) and `g_T` near 0.60, while the
  treatment moved `g_fc_hz`'s lower bound. `sab__lecleach_fc540_T_narrow.yaml` also has a seed outside its
  own box (`g_T 0.8` vs `0.687–0.777`), which `normalize()` clips.

The reusable lesson is not "use sigma=0.05" or "budget=200". It is: measure the spread, check the
seed, sample the box, then choose the step and the budget.
