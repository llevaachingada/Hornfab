---
name: hornlab-shape-check
description: Design or edit a horn geometry variant in hornlab-search (new config, new knob values, a new hybrid or generator option) and prove it meshes before any GPU time - dof cap, brief envelope, round driver coupling, quarter/half symmetry - plus the fast tuning loop for mouth size and depth. Use whenever the owner asks for a new shape, a variant "like this one", a different coverage or size, or before queueing configs for a night.
---

# hornlab shape check

## The check (always, before queueing)

```
.venv\Scripts\python.exe tools/shape_check.py examples/typologies/<folder>/*.yaml [--save-mesh scratch/m]
```
CPU-only (gmsh); safe during a GPU night. Per config: generator refusal, dofs vs the screen cap, mouth W x H and
depth vs the brief envelope, and the driver coupling plane (mesh tag 2) vs the brief exit diameter. `--save-mesh`
keeps `mesh.msh` for the hornlab-render skill. Exit 1 if anything fails.

## Fast tuning loop (seconds, no gmsh) for rows generators

```python
from hornlab_search.design.generators import grid
pts, meta = grid.rows_grid_points(SPEC, knobs, {"driver": {"exit_radius_mm": 18.0, "exit_angle_deg": 2.0}})
meta["mouth_w_mm"], meta["mouth_h_mm"], meta["x_span_mm"]
```
Sweep a few knob sets in one script, pick the one that lands on the K-law mouth (`25,400,000 / (f0 * coverage)`
mm per axis) inside the envelope, then run `shape_check.py` on the written config.

## Pitfalls that cost iterations (2026-10-28)

- **Write configs with a Python file + `yaml.safe_dump`, not shell heredocs** with nested quotes (bash eval broke
  on triple quotes; single quotes inside a YAML single-quoted description broke the load).
- **Span and mesh quadrants must agree**: rows `span: quarter` <-> `mesh.quadrants: '1'`; `span: half` <-> `'14'`.
  A 4-fold-symmetric shape is a quarter model (half the dofs). The mesher refuses a mismatch - fix the config.
- **Round coupling**: OSSE/R-OSSE `aspect_ratio` and the R-OSSE cross-section `exponent` reshape the throat itself
  (24x36 mm on a 36 mm driver). Lock `aspect_ratio: 1` (and `exponent: 2` for R-OSSE) and shape the mouth with the
  morph / superformula, whose windows open after the throat. Owner rule: round at the coupling plane is the safe
  default for prints; the effect of non-round coupling is unmeasured (memory note).
- **Envelope**: measure with the bbox (it includes the shell); X/star lobes push the diagonal extent past the
  axis width - check W, not just the axis radius.
- **Dof cap 12,000** at screen: curled lips (rollback past 180 deg) add a lot of surface; shrink ~5-10 % (raise fc
  or shorten L) rather than raise the cap toward the card's ~14k limit.
- **Constant directivity vs looks**: Salmon / Le Cleac'h rows are loading profiles and narrow at high frequency
  (670 stored designs: ~111 -> 70 -> 43 deg). For even coverage use `rows: {type: osse_rollback}` (OS throat +
  flutes + curled lip + superformula + a_fold/a_union petals). OS loading is set by `r0/tan(a)` (cone rule): a
  1.4" exit at 45 deg cannot load at 400-600 Hz; extra depth helps via OS `k` (slower throat), not narrower walls.
- **Generator changes are additive**: new knobs default to today's geometry and are listed in the kind's
  defaults so design hashes do not move; run `tests/test_design_generators_grid*.py tests/test_mesh_build_grid*.py
  tests/test_param_catalog.py` (CPU) after any edit to `design/generators/grid.py`.
- Brief changes for one experiment: copy the brief (`<name>_deep_v4.yaml`), never edit one a night uses.
- New typology / shape law: CLAUDE.md "Research grounding" applies (hornlab-typology-research); label
  experiments "LABELED HYPOTHESIS-SHAPE EXPERIMENT", no published names.

## Hand-off

Queue with the hornlab-night-queue skill; render with hornlab-render (`--save-mesh` output works directly).
