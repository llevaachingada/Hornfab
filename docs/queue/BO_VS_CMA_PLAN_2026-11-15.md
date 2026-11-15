# BoTorch vs CMA-ES matched comparison + strict 80x60 track (prepared 2026-11-14, runs after the 14 Nov night)

Night file: `docs/queue/bo_vs_cma_2026-11-15.yaml` (lane gpu, ~14 h; passes `run_campaign_night.py --dry-run`).
Configs: `examples/typologies/bo_vs_cma_2026-11-15/`. New brief:
`examples/briefs/print_80x60_2026-11-13/room_80x60_700_hf1440_v7_cov.yaml`.
Code: branch `feat/study-budget-profiles` (worktree `C:\Users\hunte\Hrns\bobudget-wt`, uncommitted, **must be merged
before launch**).

## 1. Why

The 14 Nov BoTorch pilot ran on the home task (HOME_SEED5678: ext-throat, brief `room_80x60_700_hf1440_v7`,
objective v7). It trained on 64 rows of CMA run `18985d`. With 18 new screens it found design `c27e1bd3`: screen J
3.105, verify J 3.117. The best CMA J on the same task is 3.2325 (two seeds, not yet verified). The BoTorch design is
a different horn: throat extension 111 mm at 4.7° instead of 172 mm at 3.2°, with much better loading (load term
0.47 → 0.013).

That is one study with no matched control, so it is not yet evidence that BoTorch is the better optimizer. This
queue is the matched test.

## 2. BO vs CMA protocol (fixed before the run)

| | BoTorch arm (×3) | CMA arm (×3) |
|---|---|---|
| Task | HOME_SEED5678, objective v7 | the same task config, identical bounds/brief/mesh/solve (`p80x60__ext_throat_cmacmp_v7.yaml`) |
| Prior knowledge | run `18985d`, 185 valid rows, as training data (`study_cohort --run-id 18985d`; the pilot's own rows are excluded) | the same run, as x0 = its best design (J 3.2328) |
| New screens | 60 (`comparison-60` budget profile) | 60 (`--budget 60`) |
| Verify | 6 calls (4 finalists + 2 audits, protocol rule) | 6 calls (`verify --top 6`) |
| Seeds | policy / Sobol-pool seeds 31001, 31002, 31003 | CMA seeds 3101, 3102, 3103 |
| Order | pairs run back to back (BO then CMA), so slow drift on the machine hits both arms equally | |

**Decision rules:**

- **BoTorch wins** if its median best **verify** J over the 3 arms is lower than CMA's and the gap exceeds the larger
  of the two arms' seed spreads (max − min of best verify J).
- **Efficiency:** for each arm, count the screens needed to first reach J ≤ 3.2325 (the incumbent). Report the median
  per method. An arm that never reaches it counts as > 60.
- **Same basin or new:** report the normalised distance of each arm's best design from the incumbent. Both methods
  finding the 111 mm short-extension basin independently would confirm it is real.
- Screen J is reported but does not decide. One budget profile, one task and one lane, so no cross-lane mixing.

Not in scope: cold start (no prior) and multi-objective / Pareto. Both are follow-ups once this answers the
warm-start question.

## 3. Strict 80x60 track (owner: "explore both")

**Why the home horns came out ~66 × 69° (1-8 kHz mean H × V) instead of 80 × 60.**
- On 13 Nov the owner asked to treat 80 × 60 as inspiration and make consistency the priority, with decisions
  delegated. The home brief therefore relaxed `cov`: weight 1.0 → 0.6, tolerance 2.0 → 4.0 (recorded in the brief's
  header), and raised `dislope`, `flat_cv` and `diag`.
- Every searched family has ONE wall angle in all directions (`aspect_ratio` must stay 1 for round throat coupling).
  The high-frequency pattern is therefore close to round. The mouth morph shapes only the lower mids.
- Of 945 stored home designs, only 6 got near 80 × 60, and all scored badly (J ~18-21).

**This track:** the ext-throat horn plus a per-direction wall angle from the ATH CORE-style law's cosine term,
a(p) = a + c·|cos p|^k. `shape_check` confirms that p = 0 is horizontal. The seed is a 30° base + 10° cosine, which
gives a 40° horizontal half-angle (80°) and 30° vertical (60°). The throat stays round. Morph shrink is on: without
it the mouth overshoots the 600 mm width (657 mm); with it the mouth sits at the 500 × 660 target. The brief is
`..._v7_cov`, i.e. the home brief with `cov` back to weight 1.0 and tolerance 2.0. Two CMA seeds × 120 evals,
verify top 3.

**Comparing the two tracks:**
- J is not comparable across the two briefs. Re-score both tracks' winners under BOTH briefs offline.
- Run `tools/analysis/hifi_rescore.py --verify` on both. Compare the measured beamwidths and the seat-to-seat /
  in-room terms.
- 80 × 60 vs ~66 × 69 is then a listening-intent choice made with numbers, not one the score quietly made.

## 4. What changed in code (branch `feat/study-budget-profiles`)

- `hornlab_search/studies/package.py`: `BUDGET_PROFILES` = `baseline` (the frozen bo-study-v1.1 budget, still the
  default and the only one a profile-less package may carry) and `comparison-60` (60 screens / 6 verify / 66 total /
  300 attempts). A package names its profile explicitly, so the package id records the choice. Unknown profiles are
  refused. Baseline packages keep their exact historical body.
- `runner.py` / `service.py`: caps come from the package's profile (`budget_caps`). `cli.py package --budget-profile`.
- `tools/analysis/study_cohort.py --run-id` (repeatable): train on named runs only.
- `tools/bo_compare/prepare_study.py`: create → snapshot → training → analysis → proposal → package, one arm.
- Tests: `tests/test_studies_budget_profiles.py` (8 new), one new test in `tests/test_study_cohort_intake.py`. The
  studies, BO and cohort suites are green.
- Smoke test (no solves) on 14 Nov: the 185-row cohort was built (the 19 pilot rows excluded); one `comparison-60`
  package was prepared, with every step `ok` and preflight `ok`; `studies.cli run --dry-run` accepted it.

## 5. Launch (after the 14 Nov night finishes)

1. Confirm `sab_home_gpu_2026-11-14` has finished (`tools/night_status.py`), with no runner and no julia host.
2. Merge `feat/study-budget-profiles` into the main checkout. That commit carries the CONTINUITY and ISSUES entries.
   `feat/v7-flat-band` is independent and NOT needed here: this queue stays on objective v7 so it compares with all
   history.
3. Run `run_campaign_night.py --night docs\queue\bo_vs_cma_2026-11-15.yaml --dry-run`.
4. Copy the night file to `runs\nights\` and launch it detached with `queue.ps1` (as for the 14 Nov night).
5. Readout:
   - `tools/night_status.py`;
   - BO results under `runs\bo_vs_cma_2026-11-15\bo_s3100X\` and `runs\study-<package>\{screen,verify}`;
   - `tools/analysis/hifi_rescore.py --verify` on every arm;
   - the decision rules above.
