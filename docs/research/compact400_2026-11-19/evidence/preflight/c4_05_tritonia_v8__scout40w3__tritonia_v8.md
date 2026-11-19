[hornlab-mesher] outer wall clearance wants 0.711 mm on 77 of 234 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall clearance wants 1.228 mm on 47 of 271 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall clearance wants 2.799 mm on 20 of 265 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall clearance wants 1.555 mm on 37 of 278 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
































# hornlab-search preflight

### c4_05_tritonia_v8__scout40w3__tritonia_v8

`examples/typologies/compact400_2026-11-19/c4_05_tritonia_v8__scout40w3__tritonia_v8.yaml`

| item | value |
| --- | --- |
| family | OSSE |
| searched keys | L_mm, a0_deg, a_deg, az_a_cos_amp, az_fold_v_deg, az_fold_v_width_deg, k, morph_corner_mm, morph_height_mm, morph_rate, morph_width_mm, n, q, s |
| seed in box | yes |
| seed key missing | none |
| seed headroom | not checked (no --from-runs) |
| history | no_history |
| sigma / hits | config 0.2; recommended n/a; spread n/a; expected hits n/a (min 3) |
| sampling | meshed (screen mesh + envelope); N=32; valid=32 refused=0; uniform box sample (an upper bound away from the seed; CMA concentrates near it) |
| refusals | valid fraction 1; predicted valid evals 60; [none] |
| graded penalty | graded; sampled refusals 0; invalid_envelope 0 |

### WARN / HARD

No WARN/HARD findings.

### INFO

- `no_history` (examples/typologies/compact400_2026-11-19/c4_05_tritonia_v8__scout40w3__tritonia_v8.yaml): --from-runs absent: no prior-run history, seed-headroom/spread/expected-hits checks are informational only

Result: ok.
