[hornlab-mesher] outer wall clearance wants 0.984 mm on 15 of 483 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
[hornlab-mesher] the interpolating surface fit could not mesh this geometry; falling back to the approximating fit, whose acoustic wall sits slightly inside the design. Set mesh.surface_fit explicitly to choose either one and see the failure.
[hornlab-mesher] outer wall clearance wants 0.984 mm on 15 of 483 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall clearance wants 2.635 mm on 21 of 364 rings, finer than the 3.573 mm this build requests anywhere; holding at 3.573 mm. The outer shell may still chord through its own wall there -- reduce the wall thickness or open the throat curvature. The acoustic (inner) surface is unaffected.

































# hornlab-search preflight

### h_10_ext_throat_v10_s2w__hl__ext_throat_hvlaw_v7__b6_v10_s2

`examples/typologies/compact400_2026-11-19/h_10_ext_throat_v10_s2w__hl__ext_throat_hvlaw_v7__b6_v10_s2.yaml`

| item | value |
| --- | --- |
| family | OSSE |
| searched keys | L_mm, a_deg, az_a_cos_amp, az_a_cos_pow, az_s_cos2_amp, s, throat_ext_angle_deg, throat_ext_length_mm |
| seed in box | yes |
| seed key missing | none |
| seed headroom | not checked (no --from-runs) |
| history | no_history |
| sigma / hits | config 0.15; recommended n/a; spread n/a; expected hits n/a (min 3) |
| sampling | meshed (screen mesh + envelope); N=32; valid=11 refused=21; uniform box sample (an upper bound away from the seed; CMA concentrates near it) |
| refusals | valid fraction 0.34375; predicted valid evals 27.5; [invalid_geometry=21] |
| graded penalty | graded; sampled refusals 21; invalid_envelope 0 |

### WARN / HARD

- WARN `refusals` (examples/typologies/compact400_2026-11-19/h_10_ext_throat_v10_s2w__hl__ext_throat_hvlaw_v7__b6_v10_s2.yaml): 21/32 sampled designs were refused [invalid_geometry=21]; valid fraction 0.34375, predicted valid evals 27.5 of 80; uniform box sample (an upper bound away from the seed; CMA concentrates near it); 2026-11-14 had 22-36% refusals
- WARN `graded_inert` (examples/typologies/compact400_2026-11-19/h_10_ext_throat_v10_s2w__hl__ext_throat_hvlaw_v7__b6_v10_s2.yaml): infeasible_penalty 'graded' but none of the 21 sampled refusals is invalid_envelope; only pre-mesh generator estimates are graded, while these refusals get the flat PENALTY_INVALID (1000). Use search.infeasible_penalty: resample_strict with search.budget_counts: valid to replace refusals instead (2026-11-14 evidence)

### INFO

- `no_history` (examples/typologies/compact400_2026-11-19/h_10_ext_throat_v10_s2w__hl__ext_throat_hvlaw_v7__b6_v10_s2.yaml): --from-runs absent: no prior-run history, seed-headroom/spread/expected-hits checks are informational only

Result: ok with 2 warning(s) (use --strict to refuse).
