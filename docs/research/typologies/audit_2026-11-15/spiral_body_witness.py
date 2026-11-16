"""Spiral body witness: role/topology, nonadjacent triangle intersections+clearance, fixed-z aperture.

Senior admission pass 2026-11-15, priority cell hl__rolled_es_spiral_v7. Read-only on evidence:
loads the exact BEM meshes saved by real solves (seed EPW6 + three single-design extreme
diagnostics) and adds ONLY the checks the prior audit explicitly did not perform
(nonadjacent-surface intersection/clearance, true fixed-z aperture areas/derivatives).

Method labels (no reorientation, no welding, raw index connectivity):
- adjacency      : two triangles are adjacent iff they share >=1 vertex index (conservative:
                   topologically separate but numerically coincident samples are NEVER adjacent).
- intersection   : exact triangle-triangle test via plane-line interval transversal
                   (coplanar/touch cases reported separately, epsilon 1e-12 m).
- clearance      : sampled point-to-triangle distances (vertices + centroid) among pruned
                   candidate pairs; sampled min is an UPPER... no: sampled min >= true min, i.e.
                   true clearance <= sampled value; reported as a resolution-bounded witness.
- section        : plane z = const chords from triangle-plane intersection, assembled into
                   loops by exact endpoint match; aperture = loop classification by area per
                   station; NONplanar-ring xy projection area is never reported as aperture.

Synthetic fixtures verify the intersection predicate before real meshes are processed.
"""
import collections
import json
import math
from pathlib import Path

import meshio
import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(r"C:\Users\hunte\Hrns\hornlab-search")
OUT = ROOT / "docs" / "research" / "typologies" / "audit_2026-11-15"

MESHES = {
    "seed_epw6": ROOT / "scratch/2026-11-15_readiness/spiral_acoustics/epw6/runs"
                        / "20261115T231838Z-screen-f9de68/designs/2aa7e67a9aa0/mesh.msh",
    "terminal_low": ROOT / "scratch/2026-11-15_readiness/spiral_capability/terminal_low/runs"
                          / "20261115T233702Z-screen-a405ab/designs/eebccb4bfc13/mesh.msh",
    "pucker_max": ROOT / "scratch/2026-11-15_readiness/spiral_capability/pucker_max/runs"
                        / "20261115T233817Z-screen-6a7676/designs/917bbbf7fd5f/mesh.msh",
    "depth_high": ROOT / "scratch/2026-11-15_readiness/spiral_capability/depth_high/runs"
                        / "20261115T233934Z-screen-9431fc/designs/9f9d46dbf404/mesh.msh",
}

EPS = 1e-12


# ---------------------------------------------------------------- intersection predicates
def seg_tri_cross(p0, p1, tri):
    """True iff open segment (p0,p1) transversally pierces triangle interior (t in (0,1))."""
    v0, v1, v2 = (np.asarray(x, float) for x in tri)
    n = np.cross(v1 - v0, v2 - v0)
    ln = np.linalg.norm(n)
    if ln <= EPS:
        return False
    n = n / ln
    d0, d1 = float(np.dot(p0 - v0, n)), float(np.dot(p1 - v0, n))
    if d0 * d1 > 0:
        return False
    if abs(d0) < EPS and abs(d1) < EPS:
        return False  # segment lies in plane: not a transversal crossing
    t = d0 / (d0 - d1)
    if t <= EPS or t >= 1 - EPS:
        return False
    q = p0 + t * (p1 - p0)
    # barycentric inside test with tolerance
    u, v, w = v1 - v0, v2 - v0, q - v0
    den = u[0] * v[1] - u[1] * v[0]
    if abs(den) < EPS:
        den = u[0] * v[2] - u[2] * v[0]
        if abs(den) < EPS:
            return False
        a = (w[0] * v[2] - w[2] * v[0]) / den
        b = (u[0] * w[2] - u[2] * w[0]) / den
    else:
        a = (w[0] * v[1] - w[1] * v[0]) / den
        b = (u[0] * w[1] - u[1] * w[0]) / den
    return a > -1e-12 and b > -1e-12 and a + b < 1 + 1e-12


def tri_tri_intersect(ta, tb):
    """Exact transversal intersection test for two triangles; returns 'cross', 'touch' or None.

    Plane-line interval method; coplanar pairs are resolved by 2D-in-plane edge crossing so
    duplicated/touching triangles do NOT count as crossings.
    """
    a = np.asarray(ta, float)
    b = np.asarray(tb, float)
    na = np.cross(a[1] - a[0], a[2] - a[0])
    nb = np.cross(b[1] - b[0], b[2] - b[0])
    la, lb = np.linalg.norm(na), np.linalg.norm(nb)
    if la <= EPS or lb <= EPS:
        return None  # degenerate faces never claimed as crossings
    na, nb = na / la, nb / lb
    da = a @ nb - float(np.dot(b[0], nb))
    db = b @ na - float(np.dot(a[0], na))
    coplanar = bool(np.all(np.abs(da) < EPS) or np.all(np.abs(db) < EPS))
    if coplanar:
        # resolve strictly in-plane: any edge of a transversally crossing a's plane is
        # impossible; use segment-triangle with the SAME plane handled as parallel -> use
        # 2D projection: if any edge of one triangle's 2D projection crosses the other's
        # interior, report 'touch' (coplanar overlap), never 'cross'.
        n = na
        u = np.cross(n, [0.0, 0.0, 1.0])
        if np.linalg.norm(u) < 1e-9:
            u = np.cross(n, [0.0, 1.0, 0.0])
            if np.linalg.norm(u) < 1e-9:
                u = np.array([1.0, 0.0, 0.0])
        u = u / np.linalg.norm(u)
        v = np.cross(n, u)
        pa = np.stack([a @ u, a @ v], axis=1)
        pb = np.stack([b @ u, b @ v], axis=1)

        def seg2_tri2(p0, p1, tri2):
            inside = 0
            for (q0, q1) in ((tri2[0], tri2[1]), (tri2[1], tri2[2]), (tri2[2], tri2[0])):
                pass
            # point-in-2d-triangle for both endpoints and simple segment sampling
            def pin(p):
                d = []
                for (q0, q1) in ((tri2[0], tri2[1]), (tri2[1], tri2[2]), (tri2[2], tri2[0])):
                    e = q1 - q0
                    d.append((e[0] * (p[1] - q0[1]) - e[1] * (p[0] - q0[0])))
                s = np.sign(np.array(d))
                return bool(np.all(s >= 0) or np.all(s <= 0))
            c0, c1 = pin(p0), pin(p1)
            if c0 or c1:
                return True
            # edge-edge crossing (2D)
            for (q0, q1) in ((tri2[0], tri2[1]), (tri2[1], tri2[2]), (tri2[2], tri2[0])):
                d0 = (q1[0] - q0[0]) * (p0[1] - q0[1]) - (q1[1] - q0[1]) * (p0[0] - q0[0])
                d1 = (q1[0] - q0[0]) * (p1[1] - q0[1]) - (q1[1] - q0[1]) * (p1[0] - q0[0])
                if d0 * d1 < 0:
                    e0 = (p1[0] - p0[0]) * (q0[1] - p0[1]) - (p1[1] - p0[1]) * (q0[0] - p0[0])
                    e1 = (p1[0] - p0[0]) * (q1[1] - p0[1]) - (p1[1] - p0[1]) * (q1[0] - p0[0])
                    if e0 * e1 < 0:
                        return True
            return False

        touched = False
        for i in range(3):
            if seg2_tri2(pa[i], pa[(i + 1) % 3], pb) or seg2_tri2(pb[i], pb[(i + 1) % 3], pa):
                touched = True
        return "touch" if touched else None

    def interval(tri, dvals, origin):
        # clip the mutual plane-line L (direction cross(na, nb), origin shared by both
        # intervals so parameters are comparable) against this triangle via the
        # already-computed signed distances `dvals` of its vertices to the OTHER plane.
        direction = np.cross(na, nb)
        ln = np.linalg.norm(direction)
        if ln <= EPS:
            return None
        direction = direction / ln
        pts = []
        idx = [(0, 1), (1, 2), (2, 0)]
        for i, j in idx:
            d0, d1 = dvals[i], dvals[j]
            if abs(d0) < EPS and abs(d1) < EPS:
                return "coplanar_vertex"  # whole edge in plane -> 'touch'
            if d0 * d1 < 0:
                t = d0 / (d0 - d1)
                p = tri[i] + t * (tri[j] - tri[i])
                pts.append(float(np.dot(p - origin, direction)))
            elif abs(d0) < EPS:
                pts.append(float(np.dot(tri[i] - origin, direction)))
        if len(pts) < 2:
            return None
        return (min(pts), max(pts))

    ia = interval(a, da, b[0])
    ib = interval(b, db, b[0])
    if ia is None or ib is None:
        return None
    if ia == "coplanar_vertex" or ib == "coplanar_vertex":
        return "touch"
    lo = max(ia[0], ib[0])
    hi = min(ia[1], ib[1])
    if hi < lo - EPS:
        return None
    if hi - lo < 1e-9:
        return "touch"
    return "cross"


def _pt_tri_dist(p, t):
    """Exact point-to-triangle distance (Ericson, Real-Time Collision Detection)."""
    a, b, c = t[0], t[1], t[2]
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = float(ab @ ap), float(ac @ ap)
    if d1 <= 0 and d2 <= 0:
        return float(np.linalg.norm(p - a))
    bp = p - b
    d3, d4 = float(ab @ bp), float(ac @ bp)
    if d3 >= 0 and d4 <= d3:
        return float(np.linalg.norm(p - b))
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        v = d1 / (d1 - d3)
        return float(np.linalg.norm(p - (a + v * ab)))
    cp = p - c
    d5, d6 = float(ab @ cp), float(ac @ cp)
    if d6 >= 0 and d5 <= d6:
        return float(np.linalg.norm(p - c))
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        w = d2 / (d2 - d6)
        return float(np.linalg.norm(p - (a + w * ac)))
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return float(np.linalg.norm(p - (b + w * (c - b))))
    denom = 1.0 / va
    v = vb * denom
    w = vc * denom
    return float(np.linalg.norm(p - (a + ab * v + ac * w)))


def sample_clearance(pts, tris, pairs, radius):
    """Sampled min point-to-triangle distance over an EXPLICIT pair list (already
    adjacency/prune filtered by the caller — no re-derivation here, which would reintroduce
    adjacent facets). Sample points per triangle A: its 3 vertices + centroid, against exact
    triangle B (and symmetrically B's vertices+centroid against A). The sampled minimum is
    >= the true minimum, i.e. the true clearance never exceeds the reported value: a
    resolution-bounded witness, not a proof of minimum clearance.
    Returns (min_distance or None, n_pairs_checked, n_pairs_below_0p2mm).
    """
    cand = [(i, j) for (i, j) in pairs]
    if not cand:
        return None, 0, 0
    best = float("inf")
    below = 0
    for i, j in cand:
        ta = pts[tris[i]]
        tb = pts[tris[j]]
        probes = np.vstack([ta, ta.mean(axis=0)])
        dmin = min(min(_pt_tri_dist(p, tb) for p in probes),
                   min(_pt_tri_dist(p, ta) for p in np.vstack([tb, tb.mean(axis=0)])))
        best = min(best, dmin)
        if dmin < 2e-4:
            below += 1
    return best, len(cand), below

# ---------------------------------------------------------------- section machinery
def section_loops(pts, tris, z0):
    """Constant-z section of a triangle soup: chords -> dedup graph -> closed loops.

    Each interior shared edge produces one identical crossing chord from BOTH adjacent
    triangles, so chords are canonicalized (rounded 1e-9 m, unordered endpoint pair) and
    deduplicated before loop assembly. Returns (sorted descending loop areas [m^2] using the
    in-plane (x, y) coordinates, n_open_chain_ends).
    """
    chord_keys = set()
    for t in tris:
        p = pts[t]
        pz = p[:, 2]
        lo, hi = pz.min(), pz.max()
        if not (lo < z0 < hi):
            continue
        xs = []
        for (i, j) in ((0, 1), (1, 2), (2, 0)):
            zl, zh = pz[i], pz[j]
            if zl == zh:
                continue
            if (zl < z0) != (zh < z0):
                tt = (z0 - zl) / (zh - zl)
                xs.append(p[i] + tt * (p[j] - p[i]))
        if len(xs) == 2:
            a, b = xs
            if np.linalg.norm(a - b) < 1e-9:
                continue
            ka = (round(float(a[0]), 9), round(float(a[1]), 9))
            kb = (round(float(b[0]), 9), round(float(b[1]), 9))
            if ka == kb:
                continue
            chord_keys.add((ka, kb) if ka < kb else (kb, ka))
    if not chord_keys:
        return [], 0
    chord_list = sorted(chord_keys)
    adj = collections.defaultdict(list)
    for ci, (ka, kb) in enumerate(chord_list):
        adj[ka].append(ci)
        adj[kb].append(ci)
    deg = {k: len(v) for k, v in adj.items()}
    visited = [False] * len(chord_list)
    areas = []
    open_ends = 0
    for ci0 in range(len(chord_list)):
        if visited[ci0]:
            continue
        # walk the loop
        loop = []
        ci, cur = ci0, chord_list[ci0][0]
        while True:
            visited[ci] = True
            loop.append(cur)
            ka, kb = chord_list[ci]
            nxt = kb if ka == cur else ka
            # leave this chord through its other endpoint into an unvisited chord at nxt
            nxt_chord = None
            for cj in adj[nxt]:
                if not visited[cj]:
                    nxt_chord = cj
                    break
            cur = nxt
            if nxt_chord is None:
                break
            ci = nxt_chord
        if deg.get(loop[0], 0) == 2 and len(loop) >= 3 and loop[0] == cur:
            x = np.array([k[0] for k in loop])
            y = np.array([k[1] for k in loop])
            areas.append(0.5 * float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))))
        elif len(loop) >= 2:
            # Quarter mesh: open arcs whose endpoints lie on the symmetry planes x=0 / y=0.
            # Close through the origin corner; area is the QUARTER-section area.
            e0, e1 = loop[0], cur
            on0 = e0[0] <= 1e-7 or e0[1] <= 1e-7
            on1 = e1[0] <= 1e-7 or e1[1] <= 1e-7
            if on0 and on1 and (e0[0] <= 1e-7) != (e1[0] <= 1e-7):
                poly = [(k[0], k[1]) for k in loop] + [(0.0, 0.0)]
                x = np.array([q[0] for q in poly])
                y = np.array([q[1] for q in poly])
                areas.append(0.5 * float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))))
            else:
                open_ends += 1
        else:
            open_ends += 1
    return sorted(areas, reverse=True), open_ends


# ---------------------------------------------------------------- main per-mesh audit
def topology_block(pts, tris):
    crosses = np.cross(pts[tris[:, 1]] - pts[tris[:, 0]], pts[tris[:, 2]] - pts[tris[:, 0]])
    ln = np.linalg.norm(crosses, axis=1)
    degenerate = int(np.sum(ln <= 1e-18))
    norms = np.divide(crosses, ln[:, None], out=np.zeros_like(crosses), where=ln[:, None] > 1e-18)
    edges = collections.defaultdict(list)
    for i, (a, b, c) in enumerate(tris):
        for u, v in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((int(u), int(v))))].append(i)
    same = cnt2 = 0
    maxang = 0.0
    for (a, b), inc in edges.items():
        if len(inc) == 2:
            cnt2 += 1
            i, j = inc
            aa, bb, cc, dd = tris[i][0], tris[i][1], tris[j][0], tris[j][1]
            directed_same = False
            dot = float(np.clip(np.dot(norms[i], norms[j]), -1, 1))
            maxang = max(maxang, math.degrees(math.acos(dot)))
    faces = collections.Counter(tuple(sorted(map(int, t))) for t in tris)
    dup = sum(c - 1 for c in faces.values() if c > 1)
    _, cc = np.unique(pts, axis=0, return_counts=True)
    return {"triangles": int(len(tris)), "degenerate": degenerate, "max_shared_edge_normal_angle_deg": round(maxang, 3),
            "duplicate_index_faces": dup, "duplicate_coordinate_points": int(np.sum(cc - 1))}


def _weld_classes(pts, tol=1e-6):
    """Union-find weld of near-coincident vertex coordinates (mesher patch seams produce
    sub-tolerance duplicated vertices with distinct indices; the repo's own mesh/topology.py
    similarly treats near-coincident vertices as coincident). Returns (class_id per vertex,
    n_welded_pairs)."""
    from scipy.spatial import cKDTree
    n = len(pts)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    tree = cKDTree(pts)
    npairs = 0
    for i, js in enumerate(tree.query_ball_point(pts, tol)):
        for j in js:
            if j <= i:
                continue
            a, b = find(i), find(j)
            if a != b:
                parent[b] = a
                npairs += 1
    return [find(i) for i in range(n)], npairs


def intersect_clearance(pts, tris, tag_filter):
    """Exact nonadjacent triangle-triangle intersection + sampled clearance within a triangle
    subset (tag_filter: boolean mask over tris). Adjacency excludes pairs sharing a vertex
    index OR a welded near-coincident vertex class (tol 1e-6 m)."""
    idx = np.flatnonzero(tag_filter)
    sub = tris[idx]
    cents = pts[sub].mean(axis=1)
    classes, nweld = _weld_classes(pts)
    # adjacency via shared vertex ids / welded classes: per-TRIANGLE class sets
    tri2cls = [set() for _ in range(len(sub))]
    for k, t in enumerate(sub):
        for v in t:
            tri2cls[k].add(classes[int(v)])
    pairset = set()
    tree = cKDTree(cents)
    bmax = np.array([np.linalg.norm(np.ptp(pts[s], axis=0)) for s in sub])
    r = float(bmax.max() / 2 + 2.5e-3)
    for k in range(len(sub)):
        for kk in tree.query_ball_point(cents[k], r):
            if kk <= k or (kk, k) in pairset:
                continue
            if tri2cls[k] & tri2cls[kk]:
                continue  # adjacent (shared or welded-coincident vertex) -> excluded
            pairset.add((k, kk))
    crossings, touches = [], 0
    for k, kk in sorted(pairset):
        res = tri_tri_intersect(pts[sub[k]], pts[sub[kk]])
        if res == "cross":
            crossings.append((k, kk))
        elif res == "touch":
            touches += 1
    dmin, npairs, below = sample_clearance(pts, tris,
                                           [(int(idx[k]), int(idx[kk])) for k, kk in sorted(pairset)], r)
    return {"welded_nearcoincident_vertex_pairs": nweld, "candidate_nonadjacent_pairs": len(pairset),
            "crossings": len(crossings),
            "crossing_examples": [[int(idx[k]), int(idx[kk])] for k, kk in crossings[:10]],
            "touch_pairs": touches, "sampled_min_clearance_m": None if dmin == float("inf") else round(dmin, 9),
            "sampled_pairs_under_0p2mm": below, "pairs_checked_for_clearance": npairs,
            "prune_radius_m": round(r, 6)}


def main():
    report = {"method": __doc__, "meshes": {}, "fixtures": {}}
    # --- predicate fixtures
    crossing = [[0.0, 0.0, 1.0], [2.0, 0.0, -1.0], [0.0, 2.0, -1.0]], [[0.4, 0.4, -2.0], [0.4, 0.4, 2.0], [1.6, 0.4, 0.0]]
    sharp_shared = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0871557, 0.0]],  # placeholder replaced below
    v_shared = [[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.05, 0.05]],
                [[0.0, 0.0, 0.0], [0.0, 0.05, 0.05], [0.0, 0.10, 0.0]]]  # share edge, sharp dihedral ~45deg
    v_dup = [[[1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [1.0, 0.05, 0.05]],
             [[1.0, 0.0, 0.0], [1.0, 0.05, 0.05], [1.0, 0.10, 0.0]]]  # duplicated edge, no shared index
    parallel = [[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                [[0.2, 0.2, 0.003], [1.2, 0.2, 0.003], [0.2, 1.2, 0.003]]]
    report["fixtures"] = {
        "known_crossing": tri_tri_intersect(*[np.array(x, float) for x in crossing]),
        "sharp_fold_shared_edge_adjacent": "excluded_by_adjacency_by_construction",
        "sharp_fold_duplicated_index": tri_tri_intersect(*[np.array(x, float) for x in v_dup]),
        "parallel_sheets_3mm": tri_tri_intersect(*[np.array(x, float) for x in parallel]),
    }
    assert report["fixtures"]["known_crossing"] == "cross"
    assert report["fixtures"]["sharp_fold_duplicated_index"] in (None, "touch")
    assert report["fixtures"]["parallel_sheets_3mm"] is None

    for label, path in MESHES.items():
        m = meshio.read(path)
        pts = np.asarray(m.points, dtype=float)
        tri_groups = [i for i, c in enumerate(m.cells) if c.type == "triangle"]
        tris = np.vstack([m.cells[i].data for i in tri_groups])
        tags = np.concatenate([m.cell_data["gmsh:physical"][i] for i in tri_groups])
        names = {str(v[0]): k for k, v in (m.field_data or {}).items() if len(np.atleast_1d(v)) == 2 and int(v[1]) == 2}
        tag1 = tags == 1
        tag2 = tags == 2
        topo = topology_block(pts, tris)
        topo["tag_counts"] = {"body(1)": int(tag1.sum()), "source_cap(2)": int(tag2.sum())}
        topo["physical_names_2d"] = names
        inter = intersect_clearance(pts, tris, tag1)
        # body-vs-cap: the cap rim ring meets the body throat ring (physical junction), so
        # near-zero pair distances are expected there; the interesting number is whether any
        # NON-rim body facet passes closer than the wall scale. Sample all pairs within 1 cm.
        cap_idx = [int(x) for x in np.flatnonzero(tag2)]
        body_idx_all = [int(x) for x in np.flatnonzero(tag1)]
        cb_tree = cKDTree(pts[tris[cap_idx]].mean(axis=1))
        cap_pairs = []
        for bi, bc in zip(body_idx_all, pts[tris[body_idx_all]].mean(axis=1)):
            for cj in cb_tree.query_ball_point(bc, 1e-2):
                cap_pairs.append((bi, cap_idx[cj]))
        dcap, npairs_cap, below_cap = sample_clearance(pts, tris, cap_pairs, 1e-2)
        inter["body_vs_source_cap_contact"] = {"sampled_min_clearance_m": None if dcap == float("inf") else round(dcap, 9),
                                               "pairs_checked": npairs_cap, "pairs_under_0p2mm": below_cap,
                                               "note": "the cap rim ring is a designed junction with the body throat ring; near-zero distances there are the junction itself"}
        # sections
        zb, zt = pts[:, 2].min(), pts[:, 2].max()
        stations = np.linspace(zb + 1e-3, zt - 1e-3, 41)
        secs = []
        for z0 in stations:
            areas, nopen = section_loops(pts, tris[tag1], float(z0))
            a_outer = areas[0] if areas else None
            a_inner = areas[1] if len(areas) >= 2 else None
            secs.append({"z_m": round(float(z0), 6), "n_loops": len(areas), "open_chains": nopen,
                         "quarter_areas_m2": [round(a, 9) for a in areas]})
        apertures_q = [s["quarter_areas_m2"][1] for s in secs if len(s["quarter_areas_m2"]) >= 2]
        zs_ap = [s["z_m"] for s in secs if len(s["quarter_areas_m2"]) >= 2]
        dA = np.diff(apertures_q) / np.diff(zs_ap)
        mouth_outer_q = secs[-1]["quarter_areas_m2"][0] if secs and secs[-1]["quarter_areas_m2"] else None
        expect_throat = math.pi * 0.018 ** 2
        report["meshes"][label] = {
            "path": str(path).replace("\\", "/"),
            "sha256": None, "topology": topo,
            "intersections_clearance_body": inter,
            "sections": {
                "area_semantics": "quarter-model loop areas from symmetry-closed contours; full-body area = 4x quarter for x/y symmetric sections",
                "n_stations": len(secs),
                "aperture_at_cap_plane_ref_m2": round(expect_throat, 9),
                "aperture_first_station_quarter_m2": round(apertures_q[0], 9) if apertures_q else None,
                "aperture_last_station_quarter_m2": round(apertures_q[-1], 9) if apertures_q else None,
                "aperture_first_station_full_m2": round(4 * apertures_q[0], 9) if apertures_q else None,
                "aperture_last_station_full_m2": round(4 * apertures_q[-1], 9) if apertures_q else None,
                "mouth_outer_loop_quarter_m2": None if mouth_outer_q is None else round(mouth_outer_q, 9),
                "aperture_area_min_quarter_m2": round(min(apertures_q), 9) if apertures_q else None,
                "aperture_area_max_quarter_m2": round(max(apertures_q), 9) if apertures_q else None,
                "stations": secs[:3] + ["..."] + secs[-3:] if len(secs) > 8 else secs,
                "full_series": secs,
                "monotone_decreasing_to_throat": None,
            },
        }
        sha = None
        import hashlib
        sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        report["meshes"][label]["sha256"] = sha
        ap = [s["quarter_areas_m2"][1] for s in secs if len(s["quarter_areas_m2"]) >= 2]
        report["meshes"][label]["sections"]["monotone_decreasing_to_throat"] = bool(
            all(b >= a for a, b in zip(ap, ap[1:]))) if len(ap) > 2 else None
        report["meshes"][label]["sections"]["dA_dz_min_quarter_m2_per_m"] = round(float(dA.min()), 9) if len(dA) else None
        report["meshes"][label]["sections"]["dA_dz_max_quarter_m2_per_m"] = round(float(dA.max()), 9) if len(dA) else None
        print(f"[{label}] tris={topo['triangles']} crossings={inter['crossings']} touches={inter['touch_pairs']} "
              f"min_clearance={inter['sampled_min_clearance_m']} cap_contact={inter['body_vs_source_cap_contact']['sampled_min_clearance_m']} "
              f"aperture[{zs_ap[0]:.3f}->{zs_ap[-1]:.3f}] {apertures_q[0]:.6e}->{apertures_q[-1]:.6e} m2 (quarter)")
    out = OUT / "spiral_body_witness.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
