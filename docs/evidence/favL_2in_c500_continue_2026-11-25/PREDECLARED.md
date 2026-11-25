# favL__2in_c500 continuation — predeclaration (2026-11-25)

Written before any solve. Owner request: open the knobs that are sitting on a wall, narrow the
knobs that are not moving J, continue the run for another 150 solves, and keep the result
cumulatively usable by the scalar BO and metric-aware BO pipelines.

## Parent run (the thing being continued)

| item | value |
|---|---|
| run | `runs/20261121T003823Z-screen-75c147` |
| config | `examples/typologies/favL_2026-11-20/favL__2in_c500.yaml` |
| brief | `compact500_xo900_80x50_hf2in_v11cd` (closed 500 x 500 x 500 mm) |
| mode / scorer | screen / objective v11 |
| budget | 80 valid (`budget_counts: valid`), 133 attempts |
| refusals | **53 x `invalid_envelope`** (estimated 0.0–7.9 % overshoot); `g_L_mm` 248.5–276.2 |
| best | **J 1.870458** at `n=119`, design `0ae816f04c06` |
| top-10 J | 1.8705–1.9890; the run was still improving at its budget end |

The parent's shape-parameter panel (owner screenshot) is the source of the influence column:
Spearman rho of knob value vs J (negative = larger is better), and how many of the top 6 sit
within 3 % of a bound.

## New identity (why 150 solves)

`envelope.enforce: false` + `max_utilization: 1.15` turns the 500 mm product box into a
575 x 575 x 575 mm candidate box; over-cap candidates are redrawn before meshing and every row
records `size_feasibility`. The acoustic target, weights, grids, driver, mesh and solve settings
are unchanged. **There is no soft size term in J** (2026-11-25 PREDECLARED, cd_bo_cohort): size
inside 1.0–1.15 is filtered post hoc / on the Pareto axis, not scored.

The brief hash therefore changes; the box changes too. Both are BO identity fields, so this is a
**new frozen identity**, not a pooled continuation of the old 80 rows. The metric-BO gate is
>= 100 usable screen rows per frozen identity (recommended ~150, hard cap 256). **150 valid rows
in one box + one brief + one backend/fidelity clears the gate on its own and stays under the
cap.** The old 80 rows stay archived under the closed identity; generated-space intake is
fail-closed on brief/box hash and must not merge them. 150 is the owner's number and the right
size for one identity.

## Bound decision (11 searched knobs; values from the parent run)

| knob | old box | best | rho | top-6 walls | new box | reason |
|---|---|---:|---:|---|---|---|
| `g_k` | 1.000–2.200 | 1.001 | +0.58 | 2/6 low | **0.850–1.350** | strongest lever; open the low wall, drop the unused top half |
| `g_a_v_deg` | 20–31 | 31.000 | −0.55 | 5/6 high | **27.5–34.5** | open the high wall by 3.5 deg; drop the low half |
| `g_s` | 0.200–0.380 | 0.340 | −0.54 | none | **0.300–0.400** | opens the high side slightly; keeps resolution |
| `g_throat_hv_ratio` | 1.000–4.000 | 1.121 | +0.22 | 3/6 low | **0.850–1.800** | open the low wall; drop the unused 1.8–4.0 tail |
| `g_wrap_deg` | 50–160 | 110.176 | −0.19 | none | **70–130** | narrow around the basin |
| `g_L_mm` | 190–290 | 252.147 | −0.17 | none | **230–275** | narrow; high L drove the envelope refusals |
| `g_r_lip_mm` | 8–30 | 17.794 | +0.14 | none | **13–23** | narrow |
| `g_a_h_deg` | 32–37 | 33.060 | +0.10 | none | **32.2–34.5** | narrow |
| `g_n` | 1.8–3.2 | 2.854 | −0.08 | none | **2.5–3.1** | narrow (inert) |
| `g_sf_ab` | 0.700–0.900 | 0.899 | +0.05 | 5/6 high | **0.860–0.910** | inert; tiny opening clears the wall instead of sitting on it |
| `g_sf_amt` | 0.120–0.380 | 0.235 | −0.01 | none | **0.190–0.260** | inert; tighten hard |

Fixed: `g_q` 0.996, `g_sf_m` 4.0, `g_sf_n1` 1.8, `g_sf_n2` 7.0, `g_sf_start` 0.25.

Every box was probed through the real generator with the open brief (`build.py`, `probe.json`).
The legal interval at the seed covered the whole scan for all 11 knobs; the final boxes are the
desired intervals unchanged. Uniform admission: **128/128** through `materialize` and
**128/128** through the canonical `DesignSpace` path.

## Warm start

`search.warm_start: {from_runs: [75c147], top_k: 10, sigma_from_spread: true,
allow_cross_brief: true}`.

- mean design: `0ae816f04c06` (the parent best), mean J 1.870458;
- measured top-10 median spread 0.2696 (normalized in the new box) → **sigma0 0.12**;
- 24 prior rows clip into the new box; the mean itself is inside.
- `allow_cross_brief` is deliberate: the only brief delta is the envelope policy, every parent
  accepted row is inside the open cap, and the acoustic J of a fixed design is unchanged. The
  warm start never changes the solve hash, and it does **not** merge BO identities.

## Gates already passed (CPU)

- `tools/shape_check.py`: **yes**, 4117 DOF / 24000 cap, mouth 491 x 436 mm, depth 255 mm,
  fits (exploration), round coupling matches the 25.4 mm exit.
- `tools/search_preflight.py --samples 64`: seed in box, 64/64 meshed samples valid, 0 refusals,
  predicted 150 valid, `resample_strict` (graded path is inert for this family; strict resample
  is the right budget mode).
- A/B vs the parent config: 11 changed bounds, 20+ added regions, 0/10 prior top-k in them
  (expected for a widening experiment).
- `ActiveProjection`: d=11, seed round-trip true.

The preflight's `no_headroom` warning is structural (the seed *is* the parent best). The
headroom argument is the newly reachable region (k < 1.0, a_v > 31, throat < 1.0, open cap),
the parent's late best (n=119), and the 0.12 step measured from the parent's own top-10 spread.

## Predictions (recorded before launch)

- First improvement over 1.870458 within the first **40 valid** evals; best-at by **n <= 150**.
- Refusal fraction **< 10 %** (parent 40 %; the open cap removes the envelope refusal class).
- The winning design is not pinned at a new wall; the three opened knobs move off their old
  walls. If a new wall pins, it is reported, not used to stop the run (watchdog pin_ignore).
- New best J **< 1.870**; if the tail is flat after ~100 valid the run still completes 150 valid
  because those rows are the BO training set.

## Watchdog / launch

Single job, one GPU lane, `HORNLAB_GPU_LOCK=refuse`. Watchdog: refusal storm only
(`min_attempts 40`, `refusal_max 0.40`); no-gain and stall rules **off** (BO rows are useful past
convergence); `pin_ignore` on all 11 knobs (the boxes are deliberate, so a pin is post-hoc
information). `timeout_s 14400`.

## Launched (addendum, 2026-11-25 15:47 EST / 20:47Z)

Inserted as the **first job** of the live `cd_bo_cohort_2026-11-25` night (owner choice) and the
night was resumed. Job `favl_c500_open115_150`, one GPU lane, `HORNLAB_GPU_LOCK=refuse`.
Run dir `runs/20261125T204727Z-screen-02b4bf`, pid 30908 at launch, VRAM baseline 1356 MiB.

First rows (screen, before this line was written):

| n | J | note |
|---:|---:|---|
| 0 | 1.870457 | seed = parent best `0ae816f04c06` (cache/replay exact) |
| 1 | 1.807058 | first improvement, 3.4 % |
| 4 | **1.691470** | current best, 9.6 % below the parent best |

The current best moved `g_s` 0.3397 -> 0.3684 and `g_wrap_deg` 110.2 -> 95.2; it has not yet
needed the opened `g_k` / `g_a_v` / `g_throat_hv_ratio` region. Those regions remain available
to the run (they are inside the frozen box).

**Cumulative-compatibility smoke test (partial data, CPU):**
`tools.analysis.study_cohort --config favL__2in_c500_open115.yaml --dataset dataset` returned
`exact_complete: 6`, exactly **one** dependency/grid/brief group, `metric_selection.d = 11`,
`n_available = n_compatible = n_unique = 6`, zero exclusions, six metric component names. Status
`needs_initial_data` only because `n_min = 24`; at 150 valid it clears the >= 100 gate and stays
under the 256 cap. Parent (closed-identity) rows are correctly **not** in this group.

The run continues unattended; after it finishes the next step is the strict metric-BO artifact +
frozen holdout for this new identity (same protocol as `r3_c500`).
