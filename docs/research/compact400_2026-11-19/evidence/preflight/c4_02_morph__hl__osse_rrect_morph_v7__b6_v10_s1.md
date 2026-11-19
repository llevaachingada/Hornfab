[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 426 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 426 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 426 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 1404 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 1404 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
































# hornlab-search preflight

### c4_02_morph__hl__osse_rrect_morph_v7__b6_v10_s1

`examples/typologies/compact400_2026-11-19/c4_02_morph__hl__osse_rrect_morph_v7__b6_v10_s1.yaml`

| item | value |
| --- | --- |
| family | OSSE |
| searched keys | L_mm, a0_deg, a_deg, az_a_cos_amp, az_a_cos_pow, az_s_cos2_amp, k, morph_corner_mm, morph_height_mm, morph_rate, morph_width_mm, n, q, s |
| seed in box | yes |
| seed key missing | none |
| seed headroom | not checked (no --from-runs) |
| history | no_history |
| sigma / hits | config 0.2; recommended n/a; spread n/a; expected hits n/a (min 3) |
| sampling | meshed (screen mesh + envelope); N=32; valid=30 refused=2; uniform box sample (an upper bound away from the seed; CMA concentrates near it) |
| refusals | valid fraction 0.9375; predicted valid evals 56.25; [invalid_geometry=2] |
| graded penalty | graded; sampled refusals 2; invalid_envelope 0 |

### WARN / HARD

- WARN `refusals` (examples/typologies/compact400_2026-11-19/c4_02_morph__hl__osse_rrect_morph_v7__b6_v10_s1.yaml): 2/32 sampled designs were refused [invalid_geometry=2]; valid fraction 0.9375, predicted valid evals 56.25 of 60; uniform box sample (an upper bound away from the seed; CMA concentrates near it); 2026-11-14 had 22-36% refusals
- WARN `graded_inert` (examples/typologies/compact400_2026-11-19/c4_02_morph__hl__osse_rrect_morph_v7__b6_v10_s1.yaml): infeasible_penalty 'graded' but none of the 2 sampled refusals is invalid_envelope; only pre-mesh generator estimates are graded, while these refusals get the flat PENALTY_INVALID (1000). Use search.infeasible_penalty: resample_strict with search.budget_counts: valid to replace refusals instead (2026-11-14 evidence)

### INFO

- `no_history` (examples/typologies/compact400_2026-11-19/c4_02_morph__hl__osse_rrect_morph_v7__b6_v10_s1.yaml): --from-runs absent: no prior-run history, seed-headroom/spread/expected-hits checks are informational only

Result: ok with 2 warning(s) (use --strict to refuse).
