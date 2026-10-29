# Cone mid horn + axe head (2026-10-28)

Built by `tools/cad/plughorn.py` from Funktion-One's own 3D models (Evo 7SH and Evo 2SH DWG, owner-supplied,
converted with the ODA File Converter, read with `tools/cad/sat_dump.py`). Renders are the BEM meshes
(`tools/shape_check.py --save-mesh`) with the true CAD edges (`tools/render/cad_edges.py` + `render_lines.py`).

- `cone_plughorn_sheet.png` - both horns: front, 3/4, section.
- `*_vs_f1_cad.png` - our edges (red) over Funktion-One's CAD edges (black) in three views: the horn interior and
  axe head coincide; the outside is deliberately simplified (convex shell + driver bowl).
- `morph_knobs.png` - what the morph knobs do (seed = Evo 7SH CAD; wider walls; compression 7; short blade; big roll-out; 12-inch cone).
