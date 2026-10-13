---
title: "[Q] Collin: confirm BEAT driver excitation on tag 2"
labels: [question]
blocked_by: []
---

**For Collin (HornLab author).** Answerable in one line.

BEAT drives `velocity_sources={2: 1.0}` on tag 2 ("1 m/s normal velocity", q = i*rho*omega*v_n). On the test horn the physical tag areas are {1: wall 0.334 m^2, 2: source 0.000507 m^2}.

**Questions:**

1. Confirm tag 2 == `SD1D1001`, driven with uniform normal velocity.
2. Is a non-uniform or complex amplitude on the roadmap?

We record the excitation spec on every dataset row because phase 2 must encode frequency through the boundary source field. See `docs/plan/README.md` ("Four things to know before you start it") and task 02's C5.
