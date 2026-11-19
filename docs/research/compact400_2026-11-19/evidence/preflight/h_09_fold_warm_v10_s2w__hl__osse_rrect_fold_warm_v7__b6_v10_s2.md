[hornlab-mesher] outer wall clearance wants 1.804 mm on 35 of 331 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall clearance wants 0.377 mm on 30 of 294 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
































# hornlab-search preflight

### h_09_fold_warm_v10_s2w__hl__osse_rrect_fold_warm_v7__b6_v10_s2

`examples/typologies/compact400_2026-11-19/h_09_fold_warm_v10_s2w__hl__osse_rrect_fold_warm_v7__b6_v10_s2.yaml`

| item | value |
| --- | --- |
| family | OSSE |
| searched keys | L_mm, a_deg, az_a_cos_amp, az_a_cos_pow, az_fold_h_deg, az_fold_h_width_deg, az_fold_v_deg, az_fold_v_width_deg, az_s_cos2_amp, k, morph_corner_mm, morph_height_mm, morph_rate, morph_width_mm, n, q, s |
| seed in box | yes |
| seed key missing | none |
| seed headroom | not checked (no --from-runs) |
| history | no_history |
| sigma / hits | config 0.15; recommended n/a; spread n/a; expected hits n/a (min 3) |
| sampling | meshed (screen mesh + envelope); N=32; valid=32 refused=0; uniform box sample (an upper bound away from the seed; CMA concentrates near it) |
| refusals | valid fraction 1; predicted valid evals 80; [none] |
| graded penalty | graded; sampled refusals 0; invalid_envelope 0 |

### WARN / HARD

No WARN/HARD findings.

### INFO

- `no_history` (examples/typologies/compact400_2026-11-19/h_09_fold_warm_v10_s2w__hl__osse_rrect_fold_warm_v7__b6_v10_s2.yaml): --from-runs absent: no prior-run history, seed-headroom/spread/expected-hits checks are informational only

Result: ok.
