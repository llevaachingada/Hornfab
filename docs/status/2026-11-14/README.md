# HornLab status brief — 14 Nov 2026

For the collaborator, before pulling. It covers the 12 Nov day report (`runs/analysis/day_2026-11-12`, four searches)
and everything that landed on `main` from 12 to 14 Nov (265 commits, through `878d381`). J is the objective score;
**lower is better**, and J is only comparable inside one objective version.

**Best viewed as the live page: https://llevaachingada.github.io/Hornfab/status/2026-11-14/**
(same content with live charts, light/dark, phone-friendly; source: [`index.html`](index.html)).
The charts below are static renders of that page.

## The short version

| | |
|---|---|
| **−25 to −28 %** | wall time per candidate with solver fork `38e5b1f`; same physics (max diff 4.4e-5 dB) |
| **12k → 24k** | DOF cap on the four live configs; measured fit at 5.8 GiB, zero spill |
| **25 %** | of the 12 Nov evaluation budget never reached the solver (694 of 2,728) |
| **+29 %** | median verify J over screen J; the screen's top-5 ranking agrees only at ρ 0.50 |

The pipeline is fast and provenanced: the speed program finished (E0–E9) with a 400/400-eval production night at the
new solver pin. The open questions are about the *search*, not the solver: too much budget is lost to invalid
geometry, one FREEFORM family is pressed against two bounds, the screen score is optimistic, and seed repeatability is
still unmeasured.

## What changed, 12–14 Nov

![Commits per day by type](img/commits.png)

- **Bayesian studies, integrated and live-piloted** (`878d381`, `5e86c8b`, 14 Nov). Scalar v4/v7 study worker, CLI
  and Studies GUI actions; immutable study packages. Pilot: 18 screen + 6 verify calls, 24/24 exact replays,
  116 study tests pass. CMA-ES stays the default.
- **Owner decisions** (`5e86c8b`). DOF cap 12,000 → 24,000 on live configs only; frequency batch-12 for
  verify/final-style heavy runs only; a +50-eval night closes the BO training cohort to ≥ 250 rows.
- **Decision-first analysis GUI** (`7e119ec`). Report opens with next-solve actions; verdict-first run page;
  Boundary Lab isobars (rainbow 3 dB bands, hairline contours) and a new Globe (polar sonogram) view.
- **Speed program E0–E9 complete** (`0658c7c`, `db9e3bb`, 13–14 Nov). Solver fork `38e5b1f` adopted on a
  pre-declared A/B: whole-candidate wall ratio 0.753 (OSSE) / 0.720 (ATH), identical solve hashes. Feasibility
  model re-based on measured anchors. E9 production night: 400/400 evals, no spill.
- **CI repaired, tests 3× faster** (`815014c`, `2510bc3`, `1a6af93`). Eight red clusters fixed with no tolerance
  changed; offline suite 18.2 → 5.9 min (xdist, 6 workers); GPU lane exercises the fused-CUDA path.
- **S7/S8 analysis panels** (`dc64fd7`, `1671dee`). Geometry descriptors, hypothesis cards, equal-cost QD/Pareto
  and advisory surrogate validation render in `#/analysis`.
- **Run data re-published** (13 Nov). 12.82 GB, 8 tars, every SHA-256 matched on Hugging Face.

### Solver fork 38e5b1f

G2 A/B, fused CUDA, quarter-model DOF, three reps each. Pin A is the old `0850ef39`.

![VRAM and seconds per frequency, old vs new solver](img/speed.png)

## What to change before the next run (from the 12 Nov report)

1. **Do first —** widen 2 FREEFORM limits on `lecleach_rollback`: `g_fc_hz` lower 600 → 540 Hz, `g_stop_deg` upper
   240° → 264° (87 % of the top decile sit at each). Check physical safety first.
2. **Do first —** give `atlas__core_law` (OSSE) more evaluations: still improving (+7.8 % in the last 20 %).
3. Stop spending 43 % of `atlas__core_law`'s budget on refused designs (327 invalid geometry, 106 mesh too large).
4. Stop spending 30 % of `atlas__osse_ext_throat`'s budget on refused designs (61 invalid geometry).
5. Narrow 9 OSSE knobs to where the best 10 % live (e.g. `L_mm` 104…520 → 187…453).
6. Narrow `g_T` on `lecleach_rollback`: 0.300…1.00 → 0.687…0.777.
7. Verify the screen's top 5+, not just #1, and pick on verify J.
8. `dislope` holds `atlas__core_law` back (30 % of J, best 10 % at 1.5× tolerance).
9. `di_rise` holds `lecleach_rollback` back (76 % of J, best 10 % at 2.9× tolerance).
10. `atlas__osse_ext_throat` settled early (within 1 % after 45 of 139 evals): split budget across seeds.
11. Seed repeatability is unknown: run five seeds of one brief, one lane, one identical config.

## How each search went

Every dot is one solved design (log J); the line is best-so-far; ticks under the axis are evaluations refused before
the solver (red = invalid geometry, amber = mesh too large); the bar is where the budget went.

![Convergence of the four runs](img/runs.png)

## Inside one CMA-ES run

`lecleach_rollback`, FREEFORM, 3 knobs, objective v6. λ = 7, μ = 3, 28 generations, 196 evaluations.

```
m ← m + c_m·σ·Σ w_i y_{i:λ}      x_k ~ m + σ·N(0, C)      C ← (1−c1−cμ)C + c1·pc·pcᵀ + cμ·Σ w_i y_i y_iᵀ
```

| | |
|---|---|
| ![Fitness per generation](img/cma_fit.png) | ![Step size and axis ratio](img/cma_sigma.png) |
| ![Search width per knob](img/cma_std.png) | ![Distribution mean](img/cma_mean.png) |
| ![Samples in the knob plane](img/cma_scatter.png) | ![Learned covariance](img/cma_cov.png) |
| ![Distribution of J](img/cma_hist.png) | ![Recombination weights](img/cma_weights.png) |

## MAP-Elites archives (CMA-ME)

The OSSE runs use CMA-ME: CMA-ES emitters filling an 18 × 18 grid of mean horizontal × vertical beamwidth. Each filled
cell keeps its best design.

![MAP-Elites archives](img/archives.png)

## What the score is made of

![Objective balance vs tolerance](img/terms.png)

## Where the best designs live

![Search box: current vs proposed ranges](img/walls.png)

## Which knobs move the score

| | |
|---|---|
| ![OSSE sensitivity](img/sens_osse.png) | ![L_mm against J](img/sens_L.png) |

![FREEFORM sensitivity](img/sens_freeform.png)

Link candidate among the best 57 `atlas__core_law` designs: `az_a_sf_amp ≈ −0.613 · a_deg + 24.12`
(ρ −0.65, R² 0.43) — below the 0.8 bar, a hint only.

## Can we trust a screen score?

![Screen vs verify J](img/fidelity.png)

All 12 verified designs scored worse than their screen score (median +29.2 %); Spearman ρ 0.66 overall, 0.50 among
the screen's top 5.

## Best designs, measured response

![Beamwidth and DI of each run's best design](img/beamwidth.png)

## Pulling our state

```bash
git clone https://github.com/llevaachingada/Hornfab.git hornlab-search
cd hornlab-search && git checkout main && git pull    # expect 878d381 or later
```

Run data (optional, ~13 GB, public): `docs/COLLABORATOR_PULL_RUNBOOK_2026-11-02.md`. Then `hornlab-search gui` and
open `http://127.0.0.1:8765/#/analysis/day_2026-11-12`.

The solver pin changed to `38e5b1f`: re-install the pinned fork per `TOOLCHAIN.md` before solving. Cached results
from the old pin are invalidated once (expected); every row carries its own `lib_shas`.

## Open issues

| Item | State | What closes it |
|---|---|---|
| Seed repeatability | not computed | Five seeds of one brief, one lane, identical config (v6 group refused: task config hash mismatch) |
| Full test suite | 3840 pass · 3 fail | Pre-mesh refusal timing guard 104.4 ms vs 100 ms under load; quiet-host rerun, no threshold loosened |
| Bayesian vs CMA | pilot only | Matched CMA comparison and Pareto runs; CMA stays default |
| Data re-pack | partial | HF snapshot cut ~04:55Z 13 Nov (1,501 of 1,726 g9 rows) |
| Heavy-run batching | measure first | Batch-12 win measured at screen scale; first heavy run under the memory watchdog |
| Non-round throats | A/B running | Round coupling is the print default; non-round effect unmeasured |

---
Built from `runs/analysis/day_2026-11-12`, the four runs' `search.ndjson`, the CMA-ES logs of
`20261112T144510Z-screen-00cf9c`, and `docs/CONTINUITY.md` through `878d381`. A snapshot; the live GUI is the source
of truth.
