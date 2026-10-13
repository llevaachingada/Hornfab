---
title: "[Q] Collin: surface_traces ordering and bempp field recovery"
labels: [question]
blocked_by: []
---

**For Collin (HornLab author).** Answerable in one line.

With `SolveConfig.surface_traces=True`, BEAT returns:

- `surface_pressure_complex`: shape (F, n_vertices), complex128
- `surface_neumann_complex`: shape (F, n_triangles), complex128

Measured about 111 KB per frequency at 2,369 dofs.

**Questions:**

1. Is the vertex/triangle ordering guaranteed to match the `.msh` node and element order?
2. Does `bempp.evaluate_exterior_from_traces` accept BEAT's traces directly?

We use these for exact trace-to-field recovery and for the phase-2 surrogate dataset. See `docs/plan/README.md` ("Four things to know before you start it") and task 02's C2b.
