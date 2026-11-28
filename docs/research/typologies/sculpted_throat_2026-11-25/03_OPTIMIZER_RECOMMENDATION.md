# FAV-001 throat-sculpt optimizer recommendation

**Provisional.** The CPU pilot has checks pending. The geometry bank establishes the feasible examples. The acoustic readout establishes the direction and tradeoffs of the first two H-slot doses. [Matched pilot](../../../evidence/throat_sculpting_2026-11-25/MATCHED_ACOUSTIC_PILOT.md)

## Current decision

The H flare-delay slot changes horizontal coverage. A 10 mm delay brings 8 kHz H to about 79° and holds the sampled 4–8 kHz V widths within 40–60°. Its v11 score worsens by about 1.05 J against both controls. A 20 mm delay further reduces H error across 4–8 kHz, but V rises to 70.6° at 8 kHz and the score worsens by about 2.35 J. Both doses increase off-axis variation and the objective's load penalty. Keep these two doses out of a finalist set. The radial-only cases, the delay-and-pinch case, and the other slot doses still determine which operator warrants a search.

## Candidate search lane

Use four linear dimensions if a radial candidate improves J by at least 0.02 against each control and moves H toward 80° while holding the sampled 40–60° V corridor. Check raw diagonal error, DI spread, the weighted load term and the loaded-window normalized resistance before choosing the seed. Pin the parent recipe, source, area policy and all slot knobs while establishing the radial result. The parameter ranges below are starting widths for a local box around a qualifying mild H pinch. Choose the center and direction from the verified candidate and confirm the resulting box through the mesher.

| Search key | Proposed local bounds for a mild H-pinch winner | Evidence and purpose |
|---|---|---|
| `g_ts_c2` | around the winner ±0.06, clipped to the measured mild-pinch bracket −0.42 to −0.18 | Controls directional waist depth. Use the achieved waist from the mesh, since rise and the other harmonics shift it. |
| `g_ts_c4` | around the winner ±0.05, clipped to −0.10 to +0.10 | Controls diagonal intrusion separately from the primary pinch. Restrict the sign if the matched ±c4 arms show a clear diagonal cost. |
| `g_ts_rise_mm` | 8–16 mm for a winner on the 12 mm rise, with onset pinned to 0 | Moves the constriction axially. The 25 mm late arm is a separate bracket. |
| `g_ts_fall_mm` | 24–38 mm for a winner on the 30 mm fall | Controls recovery length while staying near the measured geometry. |

Keep `g_ts_area` fixed at the verified value for each lane. When area policy is itself in question, use two matched arms with the switch pinned separately. Hold `g_ts_c6` at the finalist value. For a V-pinch, late-pinch or combined winner, re-center the physical box on its verified geometry. Compare isolated slot and pinch results before adding `g_ts_slot_h_mm` as a fifth parameter. If every case loses to one of the controls by over 0.02 J or violates the V corridor, hold CMA release and use the measured H movers to motivate a lower-dose fixed-case test.

## Release checklist

```text
Model: GPT-6.2 Sol, medium reasoning. Scope: one local CMA lane following the matched pilot.
1. Read MATCHED_ACOUSTIC_PILOT.md and choose at most two candidates using both J deltas, 4–8 kHz H/V, raw diag/distd, and normalized throat resistance.
2. Obtain owner approval for GPU refinement. Once the owner's queued GPU work is complete, confirm the lane is free, set HORNLAB_GPU_LOCK=refuse, and run hornlab-search gpu-clean. Run the verify case set with B0s_station and the finalists at --epw 9. Keep the original brief and verify grid. If the winning operator has a materially different core extent, also verify a neutral geometry with its core extent.
3. Run a separate --fmax 12000 diagnostic on the same controls and surviving candidates. Review the extended-band beamwidth and resistance curves without comparing the extended-band score to the 8 kHz score.
4. Obtain the owner's approval for dispatch registration after the night's saved rows_bb_v1 designs have finished replay. Review dispatch_registration.patch, preserving file line endings and documenting the digest change. Registration is required before CLI CMA or production preflight can consume throat_sculpt_v1.
5. Put the verified seed inside the four-dimensional box and save a matched control configuration. Run .venv\Scripts\python.exe tools\search_preflight.py <candidate_config> --samples 64. For historical runs of the same geometry, bounds and objective, add --from-runs <run_dirs> to measure top-k normalized spread. Evaluate sigma0 0.05, 0.08 and 0.12 with the same bounds and usable history. Use the resulting spread, projected hit rate and mesh refusal mix to choose sigma0, targeting at least ~20% in-basin hits. Without compatible history, sigma0=0.08 is a trial value only, pending a short sweep. A fixed-case pilot is insufficient to estimate that probability.
6. Hold queue release until verification and shape preflight pass. Run matched short CMA starts before extending a promising seed, and compare exact verify grids with both controls. Use no Bayesian solves for this lane.
```

The pilot tool now accepts `--epw 9`. A mesh-only check on `B0s_station` gave 8,770 triangles at epw 6 and 19,453 at epw 9, both at 8 kHz. The throat resolution changed from 3.572917 mm to 2.381944 mm. The finer run writes `pilot_verify_epw9.json` and its own mesh directory. No finer-mesh or extended-band acoustic results exist yet.
