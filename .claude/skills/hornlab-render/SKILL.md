---
name: hornlab-render
description: Render hornlab-search horns as images in the owner's preferred layouts - design cards with views plus full-width horizontal and vertical dispersion maps, 3-view geometry sheets, contact sheets of many designs - from run dirs (best design), design dirs, or freshly meshed configs. Use when the owner asks to "render", "show", "compare visually", or wants winners/new shapes in the chat.
---

# hornlab render

Two steps, two environments (pyvista is not in the project venv):

1. **Views** (viz env; create once: `py -3.12 -m venv scratch\vizenv && scratch\vizenv\Scripts\pip install pyvista meshio`):
   ```
   scratch\vizenv\Scripts\python.exe tools/render/render_views.py --out scratch/r --views a,b,c,s [--color apricot] label=runs/<run_dir> other=scratch/m/<cfg>/mesh.msh
   ```
   Targets: a run dir (uses its best.json design), a design dir, or a `mesh.msh`. Views: `a` front 3/4, `b` behind
   (the underside/outer shell), `c` straight-on front (best for judging mouth shape), `s` side, `u` below.
   Quarter/half meshes are mirrored automatically. ~1-2 s per view; uses OpenGL briefly - fine next to a solve.
2. **Layouts** (project venv):
   ```
   .venv\Scripts\python.exe tools/render/compose.py --renders scratch/r --layout stack --views a,b --loudness --out scratch/r/cards
   .venv\Scripts\python.exe tools/render/compose.py --renders scratch/r --layout sheet --views c,a,b,s --title "..." --out scratch/r/sheet.png
   ```
   - `stack` = the owner's design card: two views on top, then horizontal and vertical dispersion FULL WIDTH,
     one above the other; title has J + brief; `--loudness` adds output gap at f0, loaded-from frequency and the
     driver-coupling check. Needs a solved design.
   - `card` = views on top, H and V maps side by side. `sheet` = one row per design, one column per view
     (unsolved geometry is fine - mesh first with `tools/shape_check.py --save-mesh`).

## Then

- Look at one output before sending (Read the PNG): check nothing is cropped or overexposed.
- Send with SendUserFile (`display: render`); state J only within a brief.
- Durable copies the owner may want later go in `docs/renders/<date>/` with a README line per image and an INDEX
  entry; `scratch/` is gitignored.

## Pitfalls

- Multi-subplot pyvista with `lighting="none"` washes out - render one view per plotter (what the tool does).
- Finding winners: `tools/night_status.py` lists the best design per brief with its run dir.
