# SIGMA0 ANALYSIS 2026-11-17 — step size vs outcome, our data + official CMA-ES guidance

**Status:** measured analysis + sourced guidance. Motivation: the Klangfilm b3_soft run
`20261117T070714Z-screen-2dabac` wasted 45 GPU evals with zero improvement, then the same config
with a retuned sigma0/bounds (`20261117T071329Z-screen-e4f90d`) cut J 56 % in 102 evals. This doc
answers: was sigma0 a hidden failure mode in other recent runs, and what does the official record say?

Nothing in `search/cma.py` is changed here. sigma0 remains a config knob; the fix is guidance +
the preflight gate, not a hardcoded default.

## 1. Our sigma0 semantics (from the code, one line)

`hornlab_search/search/cma.py` L3: *"Unit box [0,1]^k, x0 = normalized seed, sigma0 from the config,
bounds are clipped inside `DesignSpace.denormalize`"*. So **sigma0 is in [0,1]-normalized units per
bounded knob**: a sigma0 of 0.12 means the CMA sample std is 12 % of each knob's bound span (roughly;
C adapts it). pycma supplies no default (`self.sigma0 = None` — sigma0 must be chosen deliberately).

## 2. Official CMA-ES guidance (sourced)

- **pycma canonical statement** (`cma/evolution_strategy.py` docstring): variables should be scaled so
  a single std is useful and *"the optimum is expected to lie within about `x0 ± 3·sigma0`"*; to
  improve a known solution use a *"much smaller sigma0"*. Hansen's Practical Hints
  (cma-es.github.io): for **local improvement of a given solution** choose *"rather small σ0 (say in
  [0.001, 0.1], given the x-values 'live' in [0,10])"* — i.e. ≤ 0.1 half-widths of the box; for global
  search set σ0 so the target is *"expected not to be (far) outside of x0 ± 2σ0"* per coordinate.
- **Tutorial** (arXiv 1604.00772 §1, §5): `x ~ m + σ·N(0,C)`; σ is the overall step-size in the
  optimizer's own coordinate units; CMA-ES is scale-invariant, so normalization determines meaning.
  Repair-bounded sampling (§B.5) risks *"divergence or too fast convergence of the step-size"*.
- **Small budgets** (Loshchilov/IPOP summary via Hansen): *"a relatively small initial step-size can
  significantly outperform the usual default choice"* on multi-modal objectives; IPOP/BIPOP restarts
  burn budget we do not have (60–130 evals ≈ 5–13 generations, so C stays near I and **sigma0, not
  CMA's self-adaptation, decides whether the basin is ever sampled**).

## 3. Controlled A/B tonight (same config; only sigma0 + bound width changed)

Config: `examples/typologies/klangfilm_hv_2026-11-16/configs/b3_soft.yaml` (12 searchable core knobs,
seed = B3 soft, brief `room_landscape_80x50_700_hf1440_v7_smooth`, budget 100 valid).

### Arm 1 — sigma0 0.25, global bounds (`20261117T070714Z-screen-2dabac`)

```
20261117T070714Z-screen-2dabac   12   0.25    45     24    0    6.401    6.401    0.0%   44
```
45 valid rows, **24 of 45 at the J=1000 refusal sentinel**, never improved the seed, flat from
eval 1. Bounds were the full generator ranges (thetas 0–25/5–60°, core 30–480 mm, beak 0–60 mm).

### Arm 2 — sigma0 0.10, seed-centered ±30 % bounds (`20261117T071329Z-screen-e4f90d`)

```
20261117T071329Z-screen-e4f90d   12   0.10   102      9    0    6.401    2.819   56.0%   10
```
First 10 J: `6.40, 6.18, 5.87, 6.70, 6.32, 4.91, 6.01, 7.97, 6.54, 6.95` — eval 6 already beat the
seed by 23 %; final best **2.819 (−56 %)**, 9 refusals, still improving near budget end.

Same GPU, same brief, same seed: **sigma0 × bound-width is the only difference.**

## 4. Retrospective over recent runs (2026-11-15 → 11-17, runs with ≥15 valid rows)

Full table: `scratch/sigma_out2.txt` (analysis script `scratch/sigma_analysis.py`).

```
--- by sigma0 ---
 sigma runs  median beat%  median refuse%  median flat tail
  0.10    1         56.0%            8.8%               10
  0.12    2          8.1%            5.9%               27
  0.15   15          2.7%            2.1%                7
  0.18    1         11.8%            9.8%               47
  0.20   40         16.6%            1.2%               11
  0.22    2          1.7%           47.8%               45
  0.25   19         13.9%           24.6%               12
```

Reading it honestly (the buckets are confounded by seed quality — beat% alone misleads):
- **Refusal storms track sigma0 × key count × bound width, not sigma0 alone.** 0.22 arms (47.8 %
  median refusal, flat tails 32–45) and tonight's 0.25 on 12 wide keys (53 % refusal) are the storms.
  0.25 on few keys with modest bounds (the 11-16 evening block, 5 keys) improved 22–53 % and refused
  4–16 %. sigma0 0.20 is the quiet workhorse (1.2 % median refusal).
- **The opposite failure mode exists and is not sigma0's fault:** the four corelaw cohort screens
  (`cdbc27`, `0c9c90`, `e0be04` at 0.15/6 keys; `2f40b6` at 0.15/9 keys) seeded at the converged
  incumbent J 3.233 and went flat for 59–100 of 60–101 evals. A converged incumbent with a small
  budget has almost nowhere to go; that is the `hornlab-search-economy` "best J is its seed" case,
  a restart-attribution question, not a step-size bug.
- **Refinement runs did fine at 0.12** (`ffe3dc` +7.8 % at 84 evals, `15f0e4` +8.1 % at 51, near-zero
  refusals) — small sigma0 is right when the seed is already near-basin.
- Prior measured precedent, same lesson (CONTINUITY 2026-11-16, `hl__rosse_rect_cd_v7_r120.yaml`
  header): preflight at sigma0 0.20 → 0.61 expected in-basin hits of 120; sigma0 0.12 → ~21.

## 5. Conclusion — guidance for agents (no hardcoding)

1. **sigma0 is normalized per-knob units of the bound span** — a config-level decision coupled to
   bound width and free-key count. There is no universal number.
2. **Run `tools/search_preflight.py` before queueing any non-trivial search** (already the
   `hornlab-search-economy` skill's job): pick sigma0 so expected in-basin hits are ≈ ≥20 % of
   budget, using its sigma sweep. For the r120 preflight that moved 0.20 → 0.12; for tonight's b3 it
   would have moved 0.25 → ~0.10 before 45 GPU evals were spent.
3. **Stage-based starting points** (preflight governs):
   - greenfield/low-seed exploration on global bounds, ≥8 free keys: 0.15–0.20 and accept refusals;
   - seed-centered ±20–30 % bounds (the usual warm case): **0.08–0.15**;
   - refinement at a converged incumbent: 0.05–0.12, and only with restart-attribution honestly
     framed ("flat = converged" is a result, not a failure).
4. **A flat trace with ≥30 % refusals is a step-size/bounds storm signature** — stop the arm, run the
   preflight sweep, relaunch; do not let the watchdog/budget burn out the refusing arm.
5. Research-basis citation lives here (`docs/evidence/`); `docs/plan/12_RESEARCH_BASIS.md` is frozen
   and was NOT edited.
