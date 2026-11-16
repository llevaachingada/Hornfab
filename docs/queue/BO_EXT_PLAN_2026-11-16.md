# TuRBO + Pareto BoTorch policies: integration plan and matched test (drafted 2026-11-14)

Status: **landed in canonical** (`e25da03` "feat(bo): turbo_pool_v1 trust-region policy + production
Pareto (qLogNEHVI) wiring"). Both policies are registered, production-executable
(`studies/production.py:50`), GUI-selectable, and covered by `tests/test_bo_turbo.py` /
`tests/test_bo_pareto.py` plus the production suites. This file is kept as the design record; the
"merges only after" note below is historical — the merge already happened, and the two nights it
waits on are still the gating events for any *new* study, not for the code.

## 1. Research basis

| Source | What we take |
|---|---|
| BoTorch TuRBO-1 tutorial (botorch.org/docs/tutorials/turbo_1) | Trust-region state: L₀ 0.8, L_min 0.5⁷, L_max 1.6; ×2 after 3 consecutive successes; ÷2 after ⌈max(4/q, d/q)⌉ failures (q = 1 here → max(4, d)); box scaled by GP lengthscales; qLogEI inside the box. |
| Eriksson et al. 2019, *Scalable Global Optimization via Local BO* (NeurIPS) | Global GP-BO over-explores; a local trust region that grows on success and shrinks on failure is better at refining a good basin. |
| Ament et al. 2023, *Unexpected Improvements to Expected Improvement* (NeurIPS spotlight) | Use the Log forms (qLogNEI, qLogNEHVI): same optima as classic EI/EHVI, far more reliable to optimise. We already do. |
| BoTorch multi-objective tutorials (qLogNEHVI) | For 2-3 objectives, NEHVI is the recommended acquisition. The reference point must be slightly worse than every observed value, and it is frozen. |
| Repo spec `docs/research/BAYESIAN_STUDY_ORCHESTRATOR_SPEC_2026-11-12.md` §3.5/§3.6 | Exactly the settings above, plus HornLab rules: refusals count as failures, infrastructure errors pause, no silent restart, frozen Pareto reference. |

## 2. How the three BoTorch modes fit together ("in concert")

```
 prior data ──► SCALAR BO (global, qLogNEI)  ── finds the best basins (done 15 Nov, 3 arms)
                    │ all measured rows
                    ▼
               TURBO (local box around the best, qLogNEI inside it) ── polishes the winner
                    │
 prior data ──► PARETO (qLogNEHVI on coverage error × ripple) ── a menu of trade-off horns, not one J
```

- **Scalar BO** answers "which region is best under J?". It stays the default.
- **TuRBO** takes over once a good basin is known. Its box shrinks as it converges and collapses when there is
  nothing left to gain. That collapse is a natural stop signal.
- **Pareto** asks a different question. It doesn't use J's weights; it maps the best achievable coverage-vs-ripple
  balances, so the listening choice is made by the owner rather than baked into the weights.

## 3. Matched test (night file `docs/queue/bo_ext_2026-11-16.yaml`, after the current two nights)

- Shared prior P2: every screen row on task HOME_SEED5678, i.e. run `18985d` + all BoTorch study screens (cohort
  `--run-id 20261114T043025Z-screen-18985d --run-id screen`). All arms see identical data.
- Arms, 60 screens + 6 verify each (`comparison-60`), interleaved:

| Arm | Policy | Seeds | Question |
|---|---|---|---|
| T | `turbo` | 51001, 51002 | Does a local trust region beat continuing global BO, from the same data? |
| S | `scalar` | 52001, 52002 | Control: global BO continued |
| P | `pareto` | 53001, 53002 | Which coverage/ripple trade-offs exist, and does the frontier beat what the scalar arms measured? |

**Decision rules (fixed before the run):**
- **TuRBO vs scalar:** median best verify J over seeds, with the gap required to exceed the seed spread (as in the
  BO-vs-CMA plan). Also report the screens needed to beat P2's best, and whether TuRBO collapsed (L < 0.5⁷) before
  60 screens. A collapse is a valid "converged" stop, and its unspent budget is reported.
- **Pareto:**
  - hypervolume of the measured nondominated set in the frozen reference box, against the hypervolume of the S-arm
    designs measured in the same box;
  - plus the frontier itself (coverage deg vs ripple dB) with each frontier design's J, hi-fi terms
    (`tools/analysis/hifi_rescore.py`) and beamwidths.
  - Success = new nondominated designs that the scalar arms did not find.
- About 14 h GPU (BoTorch arm ≈ 2-2.5 h including CPU refits and verify).

## 3b. Owner decision (2026-11-15): Pareto coverage objective stays plain

The Pareto metric policy now accepts objective-v7 briefs (`bo/metrics.py` `freeze_metric_policy`, distinct v7 metric
hash; v4 unchanged). Its coverage objective is the **plain coverage error** from the unchanged raw helper
(`scalar_v8.v8_raw_terms`, with the brief's narrow ratio / below-f0 / diagonal conventions). It deliberately does
**not** add v7's one-sided 8 kHz narrow-beam floor penalty. Owner confirmed "keep it plain": the frontier is a menu
of physical coverage-vs-ripple trade-offs. J (which keeps the 8 kHz floor) is still reported next to every
frontier design.

## 4. Not in scope (recorded)
- Multi-region TuRBO-m: a single region fits our 6-15 knobs.
- Constraint GPs for loading: margins exist in `bo/extensions.py` but are not wired in.
- Cost-aware ranking: needs 30+ timing rows per task.
- Multi-fidelity: the spec forbids a fake fidelity coordinate.
