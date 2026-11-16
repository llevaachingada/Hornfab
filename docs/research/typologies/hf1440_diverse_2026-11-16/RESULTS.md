# Supplied HF1440 gallery — CPU evidence, 2026-11-16

The supplied Python block was extracted without changes to `tools/geometry/hf1440_seed_gallery.py`. Its mathematical self-test passed. No GPU or acoustic solve was run. The gallery generated six K open-surface previews and their sheet; its `PASS` denotes only its sampled inner-surface envelope check, not a valid shell or acoustic result.

The supplied gallery's direct J generation rejected all six because it passes the config's `seed_policy` key to the stricter current grid API. It nevertheless wrote six pinned J YAMLs. Running those exact YAMLs through the current repository shape check in `screen` mode produced:

| Seed | Result | DOFs / cap | W × H × D mm | Note |
|---|---|---:|---|
| J0 | pass | 1746 / 24000 | 390 × 334 × 239 | envelope fits; round source matches modeled exit |
| J1 | pass | 1575 / 24000 | 409 × 273 × 234 | same |
| J2 | pass | 1708 / 24000 | 494 × 267 × 230 | same |
| J3 | rejected | — | — | `stop_deg=87.0` outside iwata_ar's [90, 240] |
| J4 | pass | 1776 / 24000 | 474 × 306 × 219 | same |
| J5 | pass | 2003 / 24000 | 465 × 327 × 272 | same |

These are mesher/screen results only, not high-frequency, source-slope, manufacturing or acoustic certification. J0–J5 are the existing repository `iwata_ar` generator: Fourcade discrete parent with elliptical aspect reconstruction and flat-section area preservation, not exact published Iwata. The separate experimental L family adds Lamé sections, a quintic morph, sweep, optional lip and warp; J does not use those extensions.

The six new K preview seeds are independent of the existing K solver family. They use physical sweep in mm with a gate over the final 45% of sampled arc, versus the existing K `rim_sweep_ratio` times maximum horizontal semi-width gated over the pre-shoulder arc. Their aspect and exponent progression is tied to parent cap height through the shoulder; existing K has its own `morph_frac` gate and holds after the shoulder. Both are curved-cap ratio-locked research constructions but are not parameter-equivalent. The previews have no outer wall, source patch, BEM tags or certified shell and must not be sent to a solver.

The generated J YAMLs now use a repository-relative brief path and are pinned for preflight; they are not a search campaign. Shape check was rerun after that path change, with the same five passes and J3 refusal; individual terminal output is retained as `J*_shape_check.txt`. `INDEX.csv` preserves the unmodified gallery's direct J failures, not the separate successful shape-check results above.

A separate `tools/geometry/hf1440_j_contact_sheet.py` produces `01_IWATA_EXISTING_CODE.png` from the pinned YAMLs: it removes `seed_policy` only from an in-memory copy passed to the current grid API, leaving the supplied generator unmodified. It shows five open inner surfaces and J3's rejection. Sheet dimensions are sampled inner-surface bounds, while the screen table above uses meshed envelope dimensions; the depth difference includes the wall. OBJ previews remain open and are not BEM meshes.
