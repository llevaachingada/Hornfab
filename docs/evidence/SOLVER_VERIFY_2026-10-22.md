# Solver verification on the GPU box, 2026-10-22 (main at e37a14b)

GPU hygiene before and after each step (julia 0, VRAM 565–581 MiB).

| Check | Command | Result |
|---|---|---|
| GPU-marked tests | `pytest -m "slow or gpu or crosscheck"` | **18 passed, 0 failed, exit 0** (14:32–14:38). Includes the measured symmetry-flag test: a quarter mesh solved WITHOUT the symmetry flag is off by up to 29.9 dB, so the flag/quadrant pairing test is live |
| Analytic pulsating sphere | `selftest --analytic` | **PASS**: R(ka) spread 0.020 dB (limit 0.5 dB), omnidirectional, 2 m → 4 m spreading, convergence monotone |
| Independent solver | `selftest --crosscheck` | beat_cuda (2396 dofs, 5.7 s) vs bempp_cpu (same mesh, 132 s): max normalized difference **0.039 dB** (500–3845 Hz; frozen CP-7b rule < 0.2 dB) |

Conclusion: the GPU BEM path is verified against an exact solution and against an independent CPU BEM on the
same mesh. Any later anomaly in a search is a geometry/objective question, not a solver one.
