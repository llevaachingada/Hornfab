"""Read-only audit of Gmsh surface triangles. Coordinates assumed metres.

Usage: python audit_mesh.py mesh.msh [mesh.msh ...] > audit.json
Reports incidence and orientation, not geometric intersection or mesh quality certification.
"""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import meshio
import numpy as np


def audit(path):
    path = Path(path)
    mesh = meshio.read(path)
    points = np.asarray(mesh.points, dtype=float)
    triangles = mesh.cells_dict['triangle']
    tags = mesh.cell_data_dict['gmsh:physical']['triangle']
    if len(triangles) != len(tags):
        raise ValueError('physical tags do not align with triangles')
    source = triangles[tags == 2]
    if not len(source):
        raise ValueError('no physical tag 2 triangles')
    xyz = points[triangles]
    cross = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
    areas = np.linalg.norm(cross, axis=1)*0.5
    edges = defaultdict(list)
    for i, tri in enumerate(triangles):
        for a, b in zip(tri, np.roll(tri, -1)):
            a, b = int(a), int(b)
            edges[tuple(sorted((a, b)))].append((i, a, b))
    boundary = [e for e, faces in edges.items() if len(faces) == 1]
    nonmanifold = [e for e, faces in edges.items() if len(faces) > 2]
    bad_winding = [e for e, f in edges.items() if len(f) == 2 and f[0][1:] == f[1][1:]]
    # Triangle components connected via full edges, even for nonmanifold edges.
    parent = list(range(len(triangles)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for faces in edges.values():
        anchor = root(faces[0][0])
        for f in faces[1:]:
            parent[root(f[0])] = anchor
    components = sorted(Counter(root(i) for i in range(len(triangles))).values(), reverse=True)
    tol = 1e-9
    on_x = sum(np.all(np.abs(points[list(e), 0]) < tol) for e in boundary)
    on_y = sum(np.all(np.abs(points[list(e), 1]) < tol) for e in boundary)
    on_both = sum(np.all(np.abs(points[list(e), :2]) < tol) for e in boundary)
    src_nodes = points[np.unique(source)]
    src_edges = defaultdict(int)
    for t in source:
        for a, b in zip(t, np.roll(t, -1)):
            src_edges[tuple(sorted((int(a), int(b))))] += 1
    rim = np.unique([v for edge, n in src_edges.items() if n == 1 for v in edge])
    rim_pts = points[rim]
    radial = np.hypot(rim_pts[:, 0], rim_pts[:, 1])
    # Radial range on source perimeter includes the two symmetry-plane straight edges.
    curved_rim = rim_pts[(np.abs(rim_pts[:, 0]) > tol) & (np.abs(rim_pts[:, 1]) > tol)]
    curved_radii = np.hypot(curved_rim[:, 0], curved_rim[:, 1]) * 1000
    source_area = float(areas[tags == 2].sum() * 1e6)
    interface = Counter(tuple(sorted((int(tags[f[0][0]]), int(tags[f[1][0]])))) for f in edges.values() if len(f) == 2)
    return {'file': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'coordinate_units': 'metres (converted to mm below)', 'points': len(points),
            'triangles': len(triangles), 'triangles_by_physical_tag': dict(Counter(map(int, tags))),
            'zero_area_triangles': int(np.count_nonzero(areas <= 1e-20)),
            'duplicate_triangle_node_sets': len(triangles)-len({tuple(sorted(map(int,t))) for t in triangles}),
            'edge_connected_triangle_components': components, 'boundary_edges': len(boundary),
            'boundary_edges_on_x_zero': int(on_x), 'boundary_edges_on_y_zero': int(on_y),
            'boundary_edges_on_both_planes': int(on_both), 'boundary_edges_off_both_planes': int(len(boundary)-on_x-on_y+on_both),
            'nonmanifold_edges': len(nonmanifold), 'two_face_inconsistent_orientation_edges': len(bad_winding),
            'two_face_edges_by_tag_pair': {f'{a}-{b}': n for (a,b), n in sorted(interface.items())},
            'source': {'tag': 2, 'node_count': len(src_nodes), 'triangle_count': len(source),
                       'x_range_mm': (src_nodes[:,0].min()*1000, src_nodes[:,0].max()*1000),
                       'y_range_mm': (src_nodes[:,1].min()*1000, src_nodes[:,1].max()*1000),
                       'z_range_mm': (src_nodes[:,2].min()*1000, src_nodes[:,2].max()*1000),
                       'area_mm2_as_stored': source_area, 'area_mm2_fourfold': source_area*4,
                       'source_boundary_edges': sum(n == 1 for n in src_edges.values()),
                       'source_boundary_nodes_including_symmetry_radii': len(rim),
                       'curved_rim_nonaxis_radius_mm_range': [float(curved_radii.min()), float(curved_radii.max())] if len(curved_radii) else None},
            'scope': 'Surface incidence and source measurements only; no geometric intersection test, volume closure or acoustic validation.'}

if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    print(json.dumps([audit(p) for p in sys.argv[1:]], indent=2, allow_nan=False))
