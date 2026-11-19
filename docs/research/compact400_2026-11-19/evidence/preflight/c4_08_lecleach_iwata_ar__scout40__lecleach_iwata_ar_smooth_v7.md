





















# hornlab-search preflight

### c4_08_lecleach_iwata_ar__scout40__lecleach_iwata_ar_smooth_v7

`examples/typologies/compact400_2026-11-19/c4_08_lecleach_iwata_ar__scout40__lecleach_iwata_ar_smooth_v7.yaml`

| item | value |
| --- | --- |
| family | FREEFORM (generator: grid) |
| searched keys | g_T, g_ar_m, g_ar_p, g_fc_hz, g_stop_deg |
| seed in box | yes |
| seed key missing | none |
| seed headroom | not checked (no --from-runs) |
| history | no_history |
| sigma / hits | config 0.2; recommended n/a; spread n/a; expected hits n/a (min 3) |
| sampling | meshed (screen mesh + envelope); N=32; valid=22 refused=10; uniform box sample (an upper bound away from the seed; CMA concentrates near it) |
| refusals | valid fraction 0.6875; predicted valid evals 41.25; [invalid_envelope=10] |
| graded penalty | graded; sampled refusals 10; invalid_envelope 10 |

### WARN / HARD

- WARN `refusals` (examples/typologies/compact400_2026-11-19/c4_08_lecleach_iwata_ar__scout40__lecleach_iwata_ar_smooth_v7.yaml): 10/32 sampled designs were refused [invalid_envelope=10]; valid fraction 0.6875, predicted valid evals 41.25 of 60; uniform box sample (an upper bound away from the seed; CMA concentrates near it); 2026-11-14 had 22-36% refusals

### INFO

- `no_history` (examples/typologies/compact400_2026-11-19/c4_08_lecleach_iwata_ar__scout40__lecleach_iwata_ar_smooth_v7.yaml): --from-runs absent: no prior-run history, seed-headroom/spread/expected-hits checks are informational only

Result: ok with 1 warning(s) (use --strict to refuse).
