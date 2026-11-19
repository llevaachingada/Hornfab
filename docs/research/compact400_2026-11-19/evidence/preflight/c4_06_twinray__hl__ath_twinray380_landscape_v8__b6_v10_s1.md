































# hornlab-search preflight

### c4_06_twinray__hl__ath_twinray380_landscape_v8__b6_v10_s1

`examples/typologies/compact400_2026-11-19/c4_06_twinray__hl__ath_twinray380_landscape_v8__b6_v10_s1.yaml`

| item | value |
| --- | --- |
| family | OSSE |
| searched keys | L_mm, a0_deg, a_deg, az_fold_v_deg, az_fold_v_width_deg, k, morph_corner_mm, morph_height_mm, morph_rate, morph_width_mm, n, q, s |
| seed in box | yes |
| seed key missing | none |
| seed headroom | not checked (no --from-runs) |
| history | no_history |
| sigma / hits | config 0.2; recommended n/a; spread n/a; expected hits n/a (min 3) |
| sampling | meshed (screen mesh + envelope); N=32; valid=32 refused=0; uniform box sample (an upper bound away from the seed; CMA concentrates near it) |
| refusals | valid fraction 1; predicted valid evals 60; [none] |
| graded penalty | resample_strict; sampled refusals 0; invalid_envelope 0 |

### WARN / HARD

No WARN/HARD findings.

### INFO

- `no_history` (examples/typologies/compact400_2026-11-19/c4_06_twinray__hl__ath_twinray380_landscape_v8__b6_v10_s1.yaml): --from-runs absent: no prior-run history, seed-headroom/spread/expected-hits checks are informational only

Result: ok.
