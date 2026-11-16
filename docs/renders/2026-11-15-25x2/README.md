# 25 × 2 pilot — section home pucker vs square X (2026-11-15)

Four screen searches, 25 evaluations each, seeds 1234 and 5678, same home brief
(`room_landscape_80x50_700_hf1440_v7`) and screen mesh policy. No GPU runs were active when
the queue started; `bo_cov_pilot_2026-11-16` had finished and released the lock.

`best_designs.png` — front views of the four best designs. The labels carry J and the key
best parameters.

| Cell | Seed | Best J | Seed J | Run dir |
|---|---:|---:|---:|---|
| `rf__section_axial_home_v7` | 1234 | 17.3982 | 17.9511 | `runs/20261116T015510Z-screen-e75ec8` |
| `rf__section_axial_home_v7` | 5678 | 17.3970 | 17.9511 | `runs/20261116T020629Z-screen-0d29d7` |
| `hl__crowe_x_square_v7` | 1234 | 8.8171 | 9.2356 | `runs/20261116T021728Z-screen-3943f0` |
| `hl__crowe_x_square_v7` | 5678 | 8.2046 | 9.2356 | `runs/20261116T022328Z-screen-87354c` |

Interpretation:

- The section home search wants **width at the envelope**, **junction at its lower bound**,
  crown 33–36, and the **vertical pucker near zero** (0.37–3.35 mm). The horizontal pucker
  stays at 6.8–8.4 mm. The pucker is secondary; mouth width and junction/crown are the useful
  dimensions.
- The square X search wants a **gentler X** than the 0.60 visual seed: `sf_amt` 0.42–0.47.
  It is also **9.2 J better** than the section pucker (8.2–8.8 vs 17.4), so the square-X
  family is the better acoustic path as well as the closer reference look.
- Square-X refusals: 12 invalid_envelope (seed 1234) and 8 (seed 5678). The box can exceed
  the 600 × 480 envelope; tighten the width/height coupling before a larger search.
- 25 evaluations is a pilot for 8 active dimensions. A real comparison needs 60–96 per arm.

The durable queue script is `docs/queue/radial_25x2_2026-11-15.ps1` (same as the local
`runs/2026-11-15_25x2/run_25x2.ps1`). Logs are in `runs/2026-11-15_25x2/`. No new solve was
merged into any older campaign.
