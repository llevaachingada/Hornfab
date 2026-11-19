# Q3 — more solves + never-run typologies (2026-11-19, local orchestrator)

Night `q3_more_solves_2026-11-19`, 6/6 jobs, ~45 min GPU. Queue: `docs/queue/q3_more_solves_2026-11-19.yaml`
(+ admission). Launched detached at 15:20 local on a FREE GPU lane with a 19:00 cutoff; done by 16:05.
Read from `runs/nights/q3_more_solves_2026-11-19/summary.jsonl` and each job log.

## Why these six (all measured before launch)

- **Continuations with measured headroom** (best design in the final evals): same config, larger
  budget — the CMA trajectory replays deterministically and the identical design/mesh/solve triples are
  **solve-cache hits**, so only new evals cost GPU. fold_warm s1 (best at n=40/45), ext_throat s1
  (36/38), crowe v2a v10 (38/41).
- **Typologies with zero current-sha runs**, verified live by shape_check + preflight: a NEW config for
  rows type `lecleach_ar` (never configured anywhere), the never-run `hl__lecleach_hv_landscape_smooth_v7`
  (its A/B control), and the never-run `hl__crowe_es_biradial_rr_v7`.

## Results

| job | best J | valid | time | stop | verdict |
|---|---|---|---|---|---|
| q3__fold_warm_v10_cont | 1.5433 (unchanged) | 46 | 61 s | watchdog **bound-pinned**: 3/6 of the top 6 at the HIGH limit of `L_mm` [228.7, 271.9] | box-limited, not budget-limited |
| q3__ext_throat_v10_cont | 1.7919 (unchanged) | 32 | 61 s | watchdog **bound-pinned**: 5/6 of the top 6 at the LOW limit of `az_a_cos_pow` [1, 6] | box-limited |
| q3__crowe_v2a_v10_cont | **6.4779** (was 6.7324, −0.255) | 117 | 29 min | watchdog **stalled** (<0.5 % over 40 valid) | real gain but **below the v10 floor 0.4677 = tie**; basin exhausted |
| q3__lecleach_ar_landscape (NEW rows type) | 8.0791 | 15 | 151 s | watchdog **refusal storm 44 %** | box corners illegal; unjudged |
| q3__lecleach_hv_landscape (A/B control) | **7.8865** | 66 | 5 min | ok | best Le Cleac'h result to date (scout40 lecleach: 8.037, same brief) |
| q3__crowe_es_biradial | 9.2355 | 37 | 8 min | ok | first-ever solve of this construction; poor first showing |

Cache evidence: the two 61 s continuation runs replayed the whole prior trajectory as cache hits
("budget 160 **new** evaluations" — only ~1-9 fresh solves each), which is why six jobs cost ~45 min.

## What was learned

1. **The v10 leaders are box-limited, not budget-limited.** fold_warm's top designs press the high end
   of `L_mm`; ext_throat's press the low end of `az_a_cos_pow`. The measured next step for a v10 s2 is
   therefore: warm-start at the published best designs (§9f of PRIORITY10) **and widen these two knobs** —
   more evals at the current boxes are provably wasted (61 s proved it).
2. **Crowe v2a v10 is closed.** 117 evals, best 6.4779, stalled <0.5 %; the gain over the 41-eval run is
   below the floor. No further continuation is justified without a new freedom.
3. **The Le Cléac'h H/V pair (per-plane marches) beats the family's previous best** (7.8865 vs 8.037 on
   the same smooth-v7 identity) — a small move, likely a tie by the v7 stored-grid floor 0.3105, but the
   lane is cheap and complete.
4. **`lecleach_ar` (new rows type) is storm-limited in its authored box**: 44 % refusals in 27 attempts.
   The seed builds and solves (588 × 397 × 271 mm, 2953 dofs), so the mechanism is meshable; the corners
   of `AR_m` [1, 2.2] × `stop_deg` [165, 230] are not. A narrower box (e.g. `AR_m ≤ 1.8`, `stop ≤ 215`)
   is the fix to author before judging this typology. The preflight's uniform box sampling (79 % valid)
   under-predicted the storm — CMA concentrates elsewhere.
5. **Crowe ES biradial** exists as a live typology-generator construction (500 × 253 × 204 mm, 2103
   dofs) and now has a first measurement: 9.2355 home-v7, 37 valid. Not promising as-is; kept as the
   only solved instance of that generator.

## The under-explored map (measured, for the next "queue more" ask)

From a coverage scan of 408 example configs against 702 current runs (config_sha matching):

- **28 of 48** `home_landscape_2026-11-15` configs have never run; 3 of those are **dead** (their rows
  types `klangfilm_ellipse`, `rolled_rect_pucker`, `rosse_rect` no longer exist in the generator).
- Rows types with **no config and no solve anywhere**: `salmon_axisym` (axisymmetric — cannot reach a
  landscape mouth), `lecleach_mod` (half-span harmonic law, 2× dofs), `lecleach_ar` (now configured;
  storm-limited).
- **Zero-run but loadable families**: `crowe_hv_area_aspect_2026-11-16` (4 configs), `dual_lame_2026-11-16`
  (2), `atlas_v2`, `data_2026-10-29_v5`, and the root typologies (tractrix, conical, hypex, solana_*, meh)
  which exist only under objective v1–v5.
- The October sculpture families (quatrefoil, chanterelle, petal_os, ripple, cone_plughorn) are
  **portrait/square by construction** (fc_h > fc_v or a_h = a_v) — on the landscape corridor a run would
  measure the brief mismatch, not the typology. They need their own square/tall brief identity plus a
  measured frequency floor before any fair ranking.

## Next best measured action

1. **v10 s2 (small, decisive):** widen `L_mm` to [228.7, 300] (fold) and `az_a_cos_pow` to [0.5, 6]
   (ext-throat), warm-start each at its published best design, 120 valid. That is the first move that
   can actually beat 1.4214 / 1.5710.
2. **Fix the `lecleach_ar` box** (narrow AR/stop), re-preflight with the storm-aware expectation, rerun 40.
3. Leave crowe v2a closed; leave Crowe ES biradial parked with its one data point.
