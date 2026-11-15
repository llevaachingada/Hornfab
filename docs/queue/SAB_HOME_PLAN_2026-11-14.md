# Suggestion A/B + home ATH-law queue (2026-11-14)

Night files: `docs/queue/sab_home_gpu_2026-11-14.yaml` (GPU, ~14.5 h) and `docs/queue/sab_lecleach_cpu_2026-11-14.yaml`
(CPU lane, ~3-4 h, runs alongside). Configs: `examples/typologies/suggest_ab_2026-11-14/`. Helper:
`tools/night_queue/verify_night_jobs.py` (verifies runs created earlier in the same night).

It does three things:

1. Tests whether the 11 next-solve suggestions from the 12 Nov report (`runs/analysis/day_2026-11-12`) improve things.
   Each test is a matched A/B: same brief, lane, solver pin and CMA seeds, with only the suggested change different.
2. Moves the search to the home 80x60 / 700 Hz brief (`room_80x60_700_hf1440_v7`) with the ATH CORE-style
   per-direction law, the petal or "ripple" mouth.
3. Builds Bayesian-optimisation training data: one 500-row single-config cohort (H1, five seeds) and four 200-row
   core_law cohorts.

## What the data said before writing this queue

| Finding | Evidence | Consequence |
|---|---|---|
| The suggestions were learned on older briefs: `atlas__core_law` (v4, 2-in, 50x50), `lecleach_rollback` (v6, 1-in, 90x60) and `atlas__osse_ext_throat` (atlas brief). None is the home brief. | `REPORT.md` headers | Test them on their own briefs (C1, L1). Carry them to home only where the mechanism transfers. |
| On the home brief, `dislope` is not a bottleneck: top-decile 0.19 (ext-throat) and 4.8 (ATH-core) against tolerance 9. | term_balance on runs `51328c`, `db8e2f` | Items 8 and 9 are artifacts of the old objectives. No tolerance change for v7, and no GPU spent on it. |
| The home terms that bind are `flat_cv` + `cov` (ext-throat) and `diag` 28 % + `cov` (ATH-core). | same | Use the lever that moved `diag` before (next row). |
| The ATH CORE law moved the field in the rev2 ablation: `ath_a1_core` vs `ath_a0_control` gave diag 2.06 → 0.68, J 11.4 → 6.2, and was still accepted at verify. The cosine-only notch and the lip-ripple (S) family did not move it. | `QUEUE_PLAN_REV2_2026-11-13.md` execution record | "Ripples" here means the superformula petal law. Lip ripples are a recorded negative. |
| Home ext-throat seeds 1234 and 5678 both converged to J 3.2325 / 3.2328. | best.json of `51328c`, `18985d` | Good early sign of repeatability. That family without the law is converged, and this J is the incumbent the law must beat. |
| The incumbent's mouth is 593 mm wide against the 600 mm envelope. Its refusals are width and depth overshoots. | shape_check, refusal tallies | Any law that widens the diagonals must lower the base angle, or it is refused (graded). H2 has no such wall. |
| Refused designs cost ~0.3-1 s each. They waste evaluation slots, not GPU hours. | `seconds.total` of refused rows | Items 3 and 4 are about CMA efficiency. Wall time is a minor cost. |
| Narrowing the 9 OSSE knobs cuts a(p)-law-invalid designs only from ~20 % to ~18 % of the box (uniform sample of the validator). In g1, 62 of 106 mesh_too_large refusals were pre-mesh estimates against the old 12k cap, which is now 24k. | offline sample; g1 error tallies | C1 measures the refusal effect. It is not assumed. |
| `g_stop_deg` > 240 is refused by the rows generator (`ROWS_LECLEACH_STOP_RANGE = (90, 240)`). | direct generator call | Item 1b cannot be applied without a generator change, so it is not queued. |
| `g_fc_hz` 540 builds safely: mouth 345 mm, depth ≤ 211 mm, inside 520 x 420 x 260. At fc ≤ 540 with T 0.687 the march is invalid. | direct generator call (shape_check overrides the seed fc with its K-law derivation, so it cannot test this) | Item 1a is queued (L1). Caveat: objective v6 uses the design's own `g_fc_hz` as its loading corner, so part of any gain may come from the score's reference moving. Read the raw load and DI metrics too. |
| Verify costs ~7.5x a screen eval (g1c: 10 designs in 21.6 min). | gpu_day_2026-11-12_cont summary | Verify top 5 for core_law and top 2-3 per home seed. Top 5 of every home run would add ~3 h. |

## Suggestion → queue disposition

| # | Suggestion | What this queue does |
|---|---|---|
| 1 | Widen lecleach `g_fc_hz` 600→540, `g_stop_deg` 240→264 | fc: L1 arm `fc540` vs `ctrl`, 2 seeds, CPU lane. stop: not testable (generator limit). Recorded as blocked. |
| 2 | More evals for `atlas__core_law` | C1: both arms start at the g1 best (2b1810253691, J 2.1283), +200 evals × 2 seeds × 2 arms |
| 3 | 43 % of core_law refused | C1: caps 24k in both arms (mesh_too_large) plus the narrow arm (law/envelope). Readout: valid fraction per arm vs g1's 0.57. |
| 4 | 30 % of osse_ext_throat refused | Not re-run on the atlas brief. The home sibling refuses only 8-13 %, so it carries no GPU time. |
| 5 | Narrow 9 OSSE knobs | C1 narrow arm (exact report boxes). The same law-amplitude boxes are used in H1/H2. |
| 6 | Narrow lecleach `g_T` | L1 arm `fc540_T_narrow` |
| 7 | Verify the top 5+ and pick on verify J | `v_c1_top5` (top 5 per C1 run), `v_home_top` (top 2 per H1 seed, top 3 per H2 seed) |
| 8 | dislope holds core_law back | C1 rows give the dislope of the extended search. Not binding on the home brief (above). |
| 9 | di_rise holds lecleach back | L1 answers it: if the fc540 arms bring di_rise toward 4, the box was the limit. If not, the family or the tolerance is. |
| 10 | ext_throat settled early, split across seeds | Applied in H1: 5 seeds × 100 instead of one long run |
| 11 | Seed repeatability unknown | H1: five seeds, one config file (`--cma-seed`), one lane |

## Experiments

| Block | Config(s) | Seeds × budget | Est. | Question |
|---|---|---|---|---|
| H1 | `p80x60__ext_throat_corelaw_v7` | 1234, 5678, 9012, 3456, 7890 × 100 | ~6.2 h | Does the ATH petal law beat the home incumbent J 3.2325? It is nested: amplitudes 0 reproduce the incumbent. |
| H2 | `p80x60__ath_core14_corelaw_v7` | 1234, 5678 × 100 | ~2.6 h | Does the law fix `diag` on the 1.4-in ATH-core cell (incumbent 5.387) the way it did in the ablation? Morph shrinkage is on, so there is no envelope wall. |
| C1 | `sab__core_law_wide24k` vs `sab__core_law_narrow24k` | 2401, 2402 × 200 each | ~3.1 h | Does the narrowed box give more valid evals and lower J from the same start? |
| L1 | `sab__lecleach_ctrl` / `_fc540` / `_fc540_T_narrow` (CPU) | 2301, 2302 × 150 | ~3-4 h CPU | Does fc 540 lower J and di_rise? Does narrowing g_T add anything? |
| V | `v_c1_top5`, `v_home_top` | 20 + 16 designs | ~2.5 h | Screen-vs-verify bias and rank agreement, and the final pick on verify J |

H1 law design: superformula shape pinned at the g1 best (SF = 1.00 / 1.38 / 0.76 at 0 / 45 / 90 deg). The searched
amplitudes are `az_a_sf_amp` −10…35.42, `az_a_cos_amp` −29.05…7.65 and `az_s_cos2_amp` −0.255…0.5 (the report's
item-5 boxes). `a_deg` lo is 15 so the base can fall while the law adds angle. This is 9 searched knobs (6 + 3).

## Decision rules (fixed before the run)

- **Law helps the home horn (H1/H2).** Yes only if the median best J over seeds beats the incumbent by more than the
  seed spread, the best designs carry non-zero amplitudes, and the advantage holds at verify. If H1 seeds sit at
  amplitudes ≈ 0, record a negative for the ext-throat family.
- **Narrow box helps (C1).** Yes if the narrow arm's best J beats the wide arm's on both seeds at equal budget AND its
  valid fraction is higher. A gain on valid fraction alone means it is efficient but not better.
- **fc widen helps (L1).** Yes if both fc540 seeds beat both ctrl seeds AND raw `di_rise` / load metrics improve, not
  only J (because of the v6 fc-reference caveat).
- **Repeatability (item 11).** Run `tools/analysis/seed_variance.py --group h1=<5 run dirs>`. Report the best-J spread and
  the normalised design distance.
- **Pick.** The home winner is the lowest **verify** J across H1/H2. Screen J ranks candidates only.

## Readout after the night

1. `tools/night_status.py --since-hours 20` for each night's jobs, evals and best J.
2. Write an analysis spec `tools/analysis/specs/sab_2026-11-14.yaml`: convergence + walls + term_balance per run;
   seed_groups `h1` (5), `h2` (2); ab_compare C1 wide vs narrow per seed and L1 arms; fidelity on every verified run.
   Then `tools/analysis/report_day.py --spec … --out runs/analysis/sab_2026-11-14`.
3. Hi-fi check on the finalists: `tools/analysis/hifi_rescore.py --verify --run <each H1/H2 run> --out
   runs/analysis/sab_2026-11-14/hifi_verify`. This is the DSP-aware listening-window score at 6 points/octave
   (`docs/research/ONAXIS_WEIGHTING_2026-11-14.md`). Report it next to verify J for the pick.
4. BO cohort: the five H1 runs are one task identity (`_task_config` strips seed/budget). Feed them to the Bayesian
   study as one cohort of ~500 rows.

## Launch (owner machine; nothing else on the GPU)

Pre-flight per `.claude/skills/hornlab-night-queue`: no live runner, `nvidia-smi` baseline, `runs/.gpu.lock` free.
Copy both files to `runs/nights/`, then start the GPU lane and the CPU lane as two detached controllers:

```
copy docs\queue\sab_home_gpu_2026-11-14.yaml runs\nights\
copy docs\queue\sab_lecleach_cpu_2026-11-14.yaml runs\nights\
powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 -Script tools\night_queue\queue.ps1 -ScriptArgs "-Nights sab_home_gpu_2026-11-14 -Log runs\nights\queue_sab_home_gpu.log"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\night_queue\launch_detached.ps1 -Script tools\night_queue\queue.ps1 -ScriptArgs "-Nights sab_lecleach_cpu_2026-11-14 -Log runs\nights\queue_sab_lecleach_cpu.log"
```

Add `-Cutoff HH:MM` to the GPU controller to cap the day. The tail drops first: H2 seed 2, then the home verify.
Both night files pass `run_campaign_night.py --dry-run`.
