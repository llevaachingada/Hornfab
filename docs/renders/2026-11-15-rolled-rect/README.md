# Rolled-rectangle gallery

Static, buildless comparison of three original geometry seeds. Acoustic performance is unmeasured; these images are geometry evidence only. Fine bands are screen-mesh artifacts, not a tooling surface.

From the repository root, with the project environment containing `meshio` and `PyYAML`:

```powershell
.\.venv\Scripts\python.exe tools/geometry/build_rolled_rect_page.py --renders scratch/2026-11-15_rolled_rect/final-renders --out docs/renders/2026-11-15-rolled-rect
```

The script reads source configurations, brief and quarter meshes from their repository paths; `--renders` and `--out` can point elsewhere. It copies the 15 images and derives bounding spans and node counts into `metrics.json`. The width and height mirror the positive quarter-mesh bounds; depth includes the mesh's rear extent. Seed DOFs correspond to the quarter-mesh node counts. The source mesh and render inputs are local scratch artifacts and must be retained to regenerate. No external assets or build step are needed to view the generated page.
