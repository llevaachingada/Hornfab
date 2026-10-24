# Senior investigative pass, 2026-10-24

Research and code audit of hornlab-search: objective and physics assumptions, parameters, new typologies including
multi-cell, and reaching 12 kHz. Read-only on the code: nothing in `hornlab_search/` or `examples/` was changed.
Two Sonnet agents did the literature surveys (appendices); the code audit, measurements and synthesis are Opus.

| Report | Read it for |
|---|---|
| [01_AUDIT_BUGS_AND_ASSUMPTIONS.md](01_AUDIT_BUGS_AND_ASSUMPTIONS.md) | what is wrong or biased today, with evidence and fixes |
| [02_TYPOLOGIES_AND_MULTICELL.md](02_TYPOLOGIES_AND_MULTICELL.md) | new shape families, the point-grid door, multi-cell modelling, novel ideas |
| [03_HIGH_FREQUENCY_12KHZ.md](03_HIGH_FREQUENCY_12KHZ.md) | what fits on the 4060 now, the memory model, CPU/axisymmetric/fork routes |
| [04_IMPLEMENTATION_PLAN.md](04_IMPLEMENTATION_PLAN.md) | work packages for an implementing agent: steps, tests, acceptance, guardrails |
| [appendix_A_typology_survey_raw.md](appendix_A_typology_survey_raw.md) | literature survey: typologies (sources), with corrections header |
| [appendix_B_methods_survey_raw.md](appendix_B_methods_survey_raw.md) | literature survey: BEM/GPU, drivers, optimizers, metrics (sources), with corrections header |
| [evidence/](evidence/) | the scripts behind every [measured] number (no solver needed) |

## Top findings

1. **The objective mostly measures the wrong things.** The ripple term has a floor of about 3.8 for a *perfect*
   smooth beam (it scores the taper); about a third of the flatness term is the unit-acceleration source's
   −2 to −3.6 dB/oct tilt; the DI target is a constant 2.5 dB below any real beam. Fixing these (objective v2,
   opt-in) can be validated **offline over all stored records**, because full polars and balloons are saved.
2. **Fairness bug:** briefs pin the driver exit only for generator typologies. Native OSSE/R-OSSE search a0 in
   2–30° (R-OSSE winners: 8–12° on a 5° driver), and `osse_baseline` is a 1.4" throat.
3. **12 kHz already fits for 1" brief-sized horns, including a 12 kHz *search*** (3.5k–4.7k dofs at epw 6). Large
   horns hit a measured ~80·N² byte CUDA footprint (~9k dofs); the fused assembly (P1), now done in **our fork**
   (owner decision 2026-10-24, `docs/FORKS.md`, plan WP15), gives ~20k.
   Axisymmetric BEM (m = 0) makes 20 kHz trivial for axi families.
4. **The mesher's `PointGridHornGeometry` is a public door to arbitrary single-duct shapes** (twist, Fourier
   cross-sections, scalloped mouths, φ-varying terminations, cabinet mounting) with no mesher code from us.
5. **Multi-cell is feasible** via CAD → STEP → Magnus's STEP import, with finite-thickness septa, CPU near-correction
   for validation, and the free-septum-on-symmetry-plane trick. **Synergy/multi-entry (MEH) horns are out of scope by
   owner decision.**
