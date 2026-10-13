---
title: "[Q] Collin: can build_point_grid be public API?"
labels: [question]
blocked_by: []
---

**For Collin (HornLab author).** Answerable in one line.

`hornlab_mesher.config_builder.build_point_grid(params)` returns flat phi-major lists (`inner_points` / `outer_points`, `grid_n_phi=64`, `grid_n_length=32`, 64x33x3 values, `full_circle=True`). `public-api.md` lists it only as a consumer-contract item, not as stable public API.

**Question:** can `build_point_grid` be promoted to the stable public API?

It would give phase 2 a structured angular x length input representation for free. See `docs/plan/README.md` ("Four things to know before you start it") and task 02's C4.
