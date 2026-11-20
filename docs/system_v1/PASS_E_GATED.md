# Pass E: owner-gated work (not schedulable until the gate opens)

Each item starts only when its gate is answered **with values**, in writing, in
`readiness.yaml` decisions. Before E2/E4, run the `hornlab-acoustic-grounding` skill (and
`hornlab-typology-research` if a new acoustic priority is introduced): these are acoustic decisions.

| Item | Gate | Work | Lane shape |
|---|---|---|---|
| E1 First real calibration record | decision 3 values + source of `H_v(f)` | author `calibration/<id>.json` from the declared method (N2: loaded model or on-horn measurement, not an unloaded driver model, if the sum is to be called coupled); run `combine(calibration=...)` on #4/#5; crossover page sum turns on | 1 local lane + owner review |
| E2 System objective (optional) | owner wants one, after E1 | versioned `system/objective_v1.py`; never comparable to horn J; terms declared, weights in YAML | research lane first, then 1 code lane |
| E3 GUI solve button | decision 6 values + R11 real-BL lane | non-legacy `AuthorizationRecord` required; preview shows real argv; one job at a time | 1 cloud lane (UI) + 1 local lane (lane lock, acceptance) |
| E4 Observation standard | decision 5 values | commit `observation/<id>.json`; labels switch from "near-field cuts"; DI/power only if far-field claimed and the grid supports it | 1 lane |
| E5 Real geometry (WP7) | decisions 1-2 + 12PR300 drawings | parameterise `bl_panel_fit_*` by transducer shape; re-screen; taller-front staging; BL validate rc 0 | local, serial |
| E6 G7 false-negative audit | E5 or explicit owner waiver | sample rejected screen rows, stage/solve a few, report misses | local CPU |
| E7 Digital DSP realization | decision 4 | biquad realization + latency in `dsp.py` | 1 cloud lane |

**Never in this effort:** GPU system solves (unless the owner authorizes), new solver/mesher, summing
without a record, ranking system results against horn J.
