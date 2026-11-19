[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 81 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 81 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 81 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 308 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 308 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] the interpolating surface fit could not mesh this geometry; falling back to the approximating fit, whose acoustic wall sits slightly inside the design. Set mesh.surface_fit explicitly to choose either one and see the failure.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 83 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 83 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 83 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 308 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 308 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] the interpolating surface fit could not mesh this geometry; falling back to the approximating fit, whose acoustic wall sits slightly inside the design. Set mesh.surface_fit explicitly to choose either one and see the failure.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 76 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 76 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 76 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 285 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
[hornlab-mesher] outer wall self-intersects: OSSE generated outer offset grid has a normal flip near azimuth row 0, axial interval 285 Reduce the wall thickness or open the local curvature; the acoustic (inner) surface is unaffected.
































# hornlab-search preflight

### c4_07_ath_core_14in__atlas__ath_core

`examples/typologies/compact400_2026-11-19/c4_07_ath_core_14in__atlas__ath_core.yaml`

| item | value |
| --- | --- |
| family | OSSE |
| searched keys | L_mm, a_deg, k, morph_corner_mm, morph_exponent, morph_fixed, morph_height_mm, morph_rate, morph_width_mm, n, q, s, s1, s2 |
| seed in box | yes |
| seed key missing | none |
| seed headroom | not checked (no --from-runs) |
| history | no_history |
| sigma / hits | config 0.2; recommended n/a; spread n/a; expected hits n/a (min 3) |
| sampling | meshed (screen mesh + envelope); N=32; valid=17 refused=15; uniform box sample (an upper bound away from the seed; CMA concentrates near it) |
| refusals | valid fraction 0.53125; predicted valid evals 31.875; [invalid_geometry=13, mesh_too_large=2] |
| graded penalty | resample_strict; sampled refusals 15; invalid_envelope 0 |

### WARN / HARD

- WARN `refusals` (examples/typologies/compact400_2026-11-19/c4_07_ath_core_14in__atlas__ath_core.yaml): 15/32 sampled designs were refused [invalid_geometry=13, mesh_too_large=2]; valid fraction 0.53125, predicted valid evals 31.875 of 60; uniform box sample (an upper bound away from the seed; CMA concentrates near it); 2026-11-14 had 22-36% refusals

### INFO

- `no_history` (examples/typologies/compact400_2026-11-19/c4_07_ath_core_14in__atlas__ath_core.yaml): --from-runs absent: no prior-run history, seed-headroom/spread/expected-hits checks are informational only

Result: ok with 1 warning(s) (use --strict to refuse).
