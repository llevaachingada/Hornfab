---
title: "[Q] Collin: is a Robin/admittance BC planned for BEAT?"
labels: [question]
blocked_by: []
---

**For Collin (HornLab author).** Answerable in one line.

We checked both solvers for impedance (non-rigid wall) boundary conditions:

- `hornlab-beat-bem`: its `capability_report` says "exterior_robin: no admittance or impedance boundary condition is exposed".
- `hornlab-bempp-bem`: `SolveConfig.impedance_sources` (tag -> normalized admittance beta) with Robin BCs exists, but is not combinable with Burton-Miller.

**Question:** is a Robin/admittance BC planned for BEAT, and is bempp's `impedance_sources` the supported route in the meantime?

This gates the metamaterial / graded-admittance termination idea in our phase scope. See `docs/plan/README.md` ("Four things to know before you start it") and task 02's C3.
