# Saved CPU mesh audit

Run from the repository root with the project environment:

```powershell
.\.venv\Scripts\python.exe docs/research/typologies/dual_lame_2026-11-16/mesh_audit/audit_mesh.py docs/research/typologies/dual_lame_2026-11-16/mesh_audit/k01_geometry_only.msh docs/research/typologies/dual_lame_2026-11-16/mesh_audit/l01_geometry_only.msh
```

`audit.json` records this run, including SHA-256 digests of the inputs. The script reads Gmsh through meshio, assumes coordinates are metres, and uses 1e-9 m as the symmetry-plane tolerance. It neither modifies the meshes nor performs geometric intersection testing.

Both meshes have one edge-connected surface component, no zero-area or duplicate-node-set triangles, no edges incident to more than two triangles, and no same-direction shared edges. Their boundaries lie entirely on x=0 or y=0: 230 edges for K and 190 for L. This is consistent with an open quarter model, not a closed full surface. In both meshes the tag-2 source meets tag 1 along eight shared edges; the remaining source boundary edges lie on symmetry planes in this saved topology.

The tag-2 source spans 0 to 18 mm in both x and y, implying a 36 mm full diameter under quarter symmetry. Its non-axis perimeter samples have radii approximately 18 mm. The stored source surface areas are 252.891196 mm² (K) and 252.891035 mm² (L); fourfold areas are 1011.564785 and 1011.564140 mm². These are measured triangulated surface areas, not exact circular disk areas. The tag-2 surface is **not planar**: z ranges from 0 to 0.314191 mm in each mesh. This is a curved source cap and its range should not be described as a flat coupling plane.

These incidence checks do not prove absence of self-intersections, validate a closed mirrored volume, establish mesh convergence, or verify acoustic results. They apply only to the two hashed saved meshes.
