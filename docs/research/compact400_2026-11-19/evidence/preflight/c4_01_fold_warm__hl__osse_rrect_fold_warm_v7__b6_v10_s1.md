[hornlab-mesher] outer wall clearance wants 2.919 mm on 18 of 282 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall clearance wants 3.287 mm on 8 of 265 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
































# hornlab-search preflight

### c4_01_fold_warm__hl__osse_rrect_fold_warm_v7__b6_v10_s1

`examples/typologies/compact400_2026-11-19/c4_01_fold_warm__hl__osse_rrect_fold_warm_v7__b6_v10_s1.yaml`

| item | value |
| --- | --- |
| family | OSSE |
| searched keys | L_mm, a_deg, az_a_cos_amp, az_a_cos_pow, az_fold_h_deg, az_fold_h_width_deg, az_fold_v_deg, az_fold_v_width_deg, az_s_cos2_amp, k, morph_corner_mm, morph_height_mm, morph_rate, morph_width_mm, n, q, s |
| seed in box | yes |
| seed key missing | none |
| seed headroom | not checked (no --from-runs) |
| history | no_history |
| sigma / hits | config 0.2; recommended n/a; spread n/a; expected hits n/a (min 3) |
| sampling | meshed (screen mesh + envelope); N=32; valid=31 refused=1; uniform box sample (an upper bound away from the seed; CMA concentrates near it) |
| refusals | valid fraction 0.96875; predicted valid evals 58.125; [invalid_geometry=1] |
| graded penalty | graded; sampled refusals 1; invalid_envelope 0 |

### WARN / HARD

- WARN `refusals` (examples/typologies/compact400_2026-11-19/c4_01_fold_warm__hl__osse_rrect_fold_warm_v7__b6_v10_s1.yaml): 1/32 sampled designs were refused [invalid_geometry=1]; valid fraction 0.96875, predicted valid evals 58.125 of 60; uniform box sample (an upper bound away from the seed; CMA concentrates near it); 2026-11-14 had 22-36% refusals
- WARN `graded_inert` (examples/typologies/compact400_2026-11-19/c4_01_fold_warm__hl__osse_rrect_fold_warm_v7__b6_v10_s1.yaml): infeasible_penalty 'graded' but none of the 1 sampled refusals is invalid_envelope; only pre-mesh generator estimates are graded, while these refusals get the flat PENALTY_INVALID (1000). Use search.infeasible_penalty: resample_strict with search.budget_counts: valid to replace refusals instead (2026-11-14 evidence)

### INFO

- `no_history` (examples/typologies/compact400_2026-11-19/c4_01_fold_warm__hl__osse_rrect_fold_warm_v7__b6_v10_s1.yaml): --from-runs absent: no prior-run history, seed-headroom/spread/expected-hits checks are informational only

Result: ok with 2 warning(s) (use --strict to refuse).
