# X5 — corrected historical allocation replay

## Refresh at corpus HEAD `01560e5`

The historical snapshot and results below were not rerun or extended at this refresh. The [validation brief](VALIDATION_EXPERIMENTS.md) requires a leakage-corrected replay and integrated watchdog policy; neither is established here, so the table cannot certify an automation policy or compare GPU time. Attempt counts include cached rows and do not measure physical solves, elapsed time or GPU cost. The first-observed-time release convention is an assumption about availability, not proof of when a candidate configuration could first have been proposed.

The corpus, including the replay scripts, snapshot and output JSON, was committed in `01560e5`. The reproduction commands below **overwrite tracked output files**; use a separate safe copy or explicitly preserve and compare the current artifacts when independently reproducing them. No replay, queue, solver or configuration was changed in this refresh.

**2026-11-16, HEAD `207f97a29e2f2f31a366da95e882f9b48761ab00`.** CPU-only inspection of the existing `rows.pkl` snapshot; no solves or changes to queues, configs or runs. This replay does **not** establish that lane racing saves attempts. The eventual-best arm was the only observed config available until CD attempt 202; it reached the eventual-best-plus-one-noise-unit target at attempt 55. Thus no time-respecting selector has another observed arm to choose before the target. The policy comparison is degenerate at the stated target, and the full corrected replay is incomplete for the reasons below.

## Lineage and data

The snapshot contains 75 runs: 51 constant-directivity (CD), 24 smooth; CD has 2,853 attempts, including 49 cached rows. Different briefs are not raced. The per-run [lineage ledger](.x5/lineage.md) records first-row evidence, earlier matching best run and any declared warm start. No match is labelled **unknown**, not assumed to be a hand-written seed. Three cross-config seed continuations are supported by first-row parameters matching a previously observed best and by scores within 0.17 J:

| Child | Parent | Evidence |
|---|---|---|
| `hl__ext_throat_hvlaw_v8` | `hl__ext_throat_hvlaw_v7` | First J 3.102809 vs prior best 3.102805; numeric parameters match. |
| `hl__osse_rrect_morph_v8` | `hl__osse_rrect_morph_v7` | First J 3.991712 vs prior best 3.991794; numeric parameters match. |
| `hl__ath_tritonia_landscape_v9` | `hl__ath_tritonia_landscape_v8` | First J 5.687295 vs prior best 5.691901; numeric parameters match; config also declares a warm start from two v8 runs. |

These child lanes were merged into their parents in time order, leaving 24 CD arms. Other runs in the ledger either match an earlier best in the same lane or have no parent established; their true origins require further provenance work. A parameter match is evidence of continuity, not proof of author intent. First-observed row time is used as a conservative lower bound on availability: an earlier config-creation time is not reliably recoverable from these artifacts. Within a merged arm, each later run becomes eligible at its own first-observed time.

Target: eventual CD best **3.102805 + 0.17 = 3.272805**. The 0.17 J spread is the specified screen/verify estimate, not a validated universal noise floor. To enforce the availability bound, simulated pulls consume successive historical CD attempt-time slots; a next run can be pulled only after its first observed timestamp. This is a counterfactual scheduling convention, not a wall-clock reconstruction: altered solve durations and future generated designs are unknown.

## Policy replay and sensitivity

Round robin chooses the least-pulled eligible arm. The max-seeking bandit initializes each eligible arm with eight pulls, then uses the original log-best bonus. Halving compares currently eligible arms at 16-pull or 32-pull floors and doubles the threshold; a lone eligible arm cannot be eliminated against a future arm. This is an asynchronous historical-pool approximation, not a production policy. Every original-order policy hits at **55**; all reach in a median **37.5** attempts over the same 20 within-run shuffles (range 1–100, interquartile range 20–78). The randomization is a sensitivity check on order luck, not a physically realizable CMA trajectory.

| Policy | Original attempts to target | Median shuffled attempts | Original attempts used to exhaustion | Eventual top-three arms dropped | Owner-requested lower-bound arms dropped |
|---|---:|---:|---:|---|---|
| Historical actual order | 55 | Not applicable | 2,853 | Not applicable | Not applicable |
| Round robin | 55 | 37.5 | 2,853 | 0 | 0 |
| Halving, 16-pull first floor | 55 | 37.5 | 2,569 | 0 | 1 |
| Halving, 32-pull floor | 55 | 37.5 | 2,569 | 0 | 1 |
| Max-seeking bandit | 55 | 37.5 | 2,853 | 0 | 0 |

The dropped protected arm is biradial, directly identified as a desired new cell in `docs/queue/HOME_18H_PLAN_2026-11-16.md`. The protected set in the script is a **lower bound**, not a complete inventory of owner instructions; all protected families must remain protected. Both halving variants drop that arm in all 20 shuffles, so neither satisfies the no-owner-requested-drop requirement. No top-three arm was dropped in these particular runs. Counts after reaching the target are exploratory and should not be interpreted as a complete counterfactual campaign.

## Censoring ledger

Original-order halving variants produce the same dropped arms. Values are screen J; rows after a simulated stop were not observed by that policy.

| Arm | Pulls at stop | Best observed then | Eventual historical best | Later gain |
|---|---:|---:|---:|---:|
| `hl__biradial_es_style_v7` | 268 | 6.4823 | 6.4468 | 0.0355 |
| `hl__rosse_rect_cd_v7` | 119 | 4.8915 | 4.5626 | 0.3289 |
| `hl__crowe_x_osse_cd_v7` | 171 | 5.3442 | 5.3442 | 0 |

Round robin and bandit do not eliminate arms in this approximation. The full per-policy and per-shuffle ledger, including positions and censored remaining counts, is in `.x5/allocation.json`.

The default watchdog's pure verdict function was also applied counterfactually to each CD run prefix, using default settings and each stored run's bounds: 40/51 first triggers, 29 with historical continuation. In **9 runs** the later historical best improved by more than 0.17 J. In particular, default watchdog would trigger on the winning `20261115T143219Z-screen-d3a1bb` at attempt 25 on refusal rate, before its 3.102805 result. This is a counterfactual application of the current rule, not a claim that it actually watched those runs. Actual per-job overrides, 30-second polling, resume boundaries and whether the job was watched are not reconstructed for all runs; see `WATCHDOG_REPLAY.md` for documented examples. `.x5/watchdog.json` records every run and first verdict. A fully integrated watchdog allocation curve is **not established**.

## Early-rank association

Across 22 merged arms with a finite first-n best, Spearman correlations of first 8 / 16 / 32 attempts against eventual arm best are **0.897 / 0.970 / 0.958**. Arms with fewer than n rows or no finite early score were excluded. This is association on a small, clustered, historically selected and incompletely lineage-resolved set, not evidence that early elimination is safe. A geometry-only prediction of full J is unavailable; X3's coverage prediction is not substituted.

## Verdict and unfinished requirements

- Observed savings against round robin at the specified target: **0%** for all tested policies in the median shuffle, below the 15% failure line. Because the target is reached before a competing config is observed, this is a non-discriminating comparison and does not prove that adaptive allocation is ineffective in other campaigns.
- Both tested halving variants violate the explicitly required protected-family condition. The known owner-requested family list in this reconstruction is incomplete, and no family is recommended for cutting.
- The merged child trajectories remain historical, including a v9 warm start trained from earlier rows. The replay does not fully re-create the warm-start training set under each counterfactual selection or invalidate a child when a parent observation was withheld. Consequently it **does not establish** the full seed-leakage-corrected policy, especially after the target; no result here is grounds for automated allocation.
- Actual per-job watchdog overrides and resume history were not fully joined; the separate default-rule prefix audit is not the requested fully integrated watchdog policy. Config creation timestamps, lineage of unmatched seeds, a complete protected-family inventory, and unobserved outcomes after stopped runs remain unknown.
- Evidence supports retaining the existing watchdog as a human-reviewed safety signal, subject to the documented false-stop examples; it does not support automatic family cuts, changes to bounds, briefs or fidelity, or deploying a racing policy. A matched prospective test would require owner approval and was not run.

Reproduction: `.venv/Scripts/python.exe scratch/fable_architecture/.x5/lineage.py`, then `allocation.py`, `watchdog.py`, and `report_lineage.py`. The scripts only read stored records and write under `.x5/`.
