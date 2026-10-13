---
title: "[04] Design space and mesh"
labels: [wave-1]
blocked_by: []
---

**Plan file:** [`docs/plan/04_TASK_DESIGN_MESH.md`](../../docs/plan/04_TASK_DESIGN_MESH.md)
**Wave:** 1
**Branch:** `task/04-design-mesh`

## Owned files
Create and edit ONLY these (from the task file's "Owner of:" line):

`hornlab_search/design/space.py`, `families.py`, `custom.py`, `mesh/sizing.py`, `mesh/build.py`, `tests/test_design_*.py`, `tests/test_mesh_*.py`

## Checkpoint
**CP-2**: all 22 tests pass, tests 15 and 18 actually raise, and the bounding box in the pasted `.msh` header is unmistakably in metres.

Paste the full checkpoint output in the PR.

## Blocked by
none

## Dispatch
Use the verbatim template in [`docs/plan/00_ORCHESTRATOR.md`](../../docs/plan/00_ORCHESTRATOR.md) ("Dispatch prompt template"), with `<path>` = `docs/plan`, `<repo>` = the repo root, and `[YOUR TASK FILE]` = the plan file above. Do not paraphrase it.

## Wave 0 findings that affect this task
- **dof caps.** The plan's caps (8000/16000/24000) are NOT safe on the 8 GB RTX 4060 Laptop; see TOOLCHAIN.md for the measured caps. Measured dof/triangle: 0.500 full-domain, ~0.51 quarter.
- **Symmetry.** Quarter vs full symmetry agree to 0.04-0.06 dB up to 4 kHz on a resolved mesh.
