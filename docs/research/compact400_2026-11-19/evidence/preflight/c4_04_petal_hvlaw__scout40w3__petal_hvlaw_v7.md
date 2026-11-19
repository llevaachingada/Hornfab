































# hornlab-search preflight

### c4_04_petal_hvlaw__scout40w3__petal_hvlaw_v7

`examples/typologies/compact400_2026-11-19/c4_04_petal_hvlaw__scout40w3__petal_hvlaw_v7.yaml`

| item | value |
| --- | --- |
| family | OSSE |
| searched keys | L_mm, a0_deg, a_deg, az_a_cos_amp, az_a_cos_pow, az_a_sf_amp, az_s_cos2_amp, k, morph_corner_mm, morph_height_mm, morph_width_mm, n, q, s |
| seed in box | yes |
| seed key missing | none |
| seed headroom | not checked (no --from-runs) |
| history | no_history |
| sigma / hits | config 0.2; recommended n/a; spread n/a; expected hits n/a (min 3) |
| sampling | meshed (screen mesh + envelope); N=32; valid=29 refused=3; uniform box sample (an upper bound away from the seed; CMA concentrates near it) |
| refusals | valid fraction 0.90625; predicted valid evals 54.375; [invalid_geometry=3] |
| graded penalty | graded; sampled refusals 3; invalid_envelope 0 |

### WARN / HARD

- WARN `refusals` (examples/typologies/compact400_2026-11-19/c4_04_petal_hvlaw__scout40w3__petal_hvlaw_v7.yaml): 3/32 sampled designs were refused [invalid_geometry=3]; valid fraction 0.90625, predicted valid evals 54.375 of 60; uniform box sample (an upper bound away from the seed; CMA concentrates near it); 2026-11-14 had 22-36% refusals
- WARN `graded_inert` (examples/typologies/compact400_2026-11-19/c4_04_petal_hvlaw__scout40w3__petal_hvlaw_v7.yaml): infeasible_penalty 'graded' but none of the 3 sampled refusals is invalid_envelope; only pre-mesh generator estimates are graded, while these refusals get the flat PENALTY_INVALID (1000). Use search.infeasible_penalty: resample_strict with search.budget_counts: valid to replace refusals instead (2026-11-14 evidence)

### INFO

- `no_history` (examples/typologies/compact400_2026-11-19/c4_04_petal_hvlaw__scout40w3__petal_hvlaw_v7.yaml): --from-runs absent: no prior-run history, seed-headroom/spread/expected-hits checks are informational only

Result: ok with 2 warning(s) (use --strict to refuse).
