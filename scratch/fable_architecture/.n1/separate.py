"""N1 step 4b, done properly: separate inner wall from outer shell and rim/closure by the
signed position across the wall, using the generator's inner and outer surfaces.

For each tag-1 mesh node:
  P_i = nearest point on the sampled inner surface; P_o = nearest point on the outer surface.
  dir = normalized local inner->outer direction (from the same (phi, station) correspondence).
  s = (node - P_i) . dir       (0 at the inner sheet, t at the outer sheet)
  inner-wall nodes: |s| <= 0.5 mm
  outer-shell nodes: |s - t| <= 0.5 mm
  rim or closure: everything else within 3 mm of both; farther than 3 mm from both: unassigned
Then report the 3-D distance from inner-wall nodes to the sampled inner surface (median, p99).
"""
import sys, json, pathlib, collections
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, 'scratch/fable_architecture/.n1')
sys.path.insert(0, '.')
import analyze as A

ROOT = pathlib.Path('scratch/fable_architecture')
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7']


def nearest_patch(pts, grid):
    """(distance, patch i, patch j, u, v, point) of the nearest bilinear patch."""
    nphi, ns = grid.shape[:2]
    a = grid[:-1, :-1].reshape(-1, 3)
    b = grid[1:, :-1].reshape(-1, 3) - a
    c = grid[:-1, 1:].reshape(-1, 3) - a
    d = grid[1:, 1:].reshape(-1, 3) - a - b - c
    centres = a + .5 * b + .5 * c + .25 * d
    D, inds = cKDTree(centres).query(pts, k=12)
    out_d = np.empty(len(pts)); out_i = np.empty(len(pts), int); out_j = np.empty(len(pts), int)
    out_u = np.empty(len(pts)); out_v = np.empty(len(pts)); out_p = np.empty((len(pts), 3))
    for start in range(0, len(pts), 1000):
        pp = pts[start:start + 1000, None, :]
        idx = inds[start:start + 1000]
        Am, B, C, Dm = a[idx], b[idx], c[idx], d[idx]
        u = np.full(idx.shape, .5); v = u.copy()
        for _ in range(16):
            res = Am + u[..., None] * B + v[..., None] * C + (u * v)[..., None] * Dm - pp
            du = B + v[..., None] * Dm
            dv = C + u[..., None] * Dm
            aa = np.sum(du * du, axis=-1); bb = np.sum(du * dv, axis=-1); cc = np.sum(dv * dv, axis=-1)
            rr = np.sum(du * res, axis=-1); ss = np.sum(dv * res, axis=-1)
            det = np.maximum(aa * cc - bb * bb, 1e-14)
            u = np.clip(u - (cc * rr - bb * ss) / det, 0, 1)
            v = np.clip(v - (aa * ss - bb * rr) / det, 0, 1)
        P = Am + u[..., None] * B + v[..., None] * C + (u * v)[..., None] * Dm
        err = np.linalg.norm(P - pp, axis=-1)
        k = np.argmin(err, axis=1)
        rr = np.arange(len(idx))
        flat = idx[rr, k]
        out_d[start:start + len(idx)] = err[rr, k]
        out_i[start:start + len(idx)] = flat // (ns - 1)
        out_j[start:start + len(idx)] = flat % (ns - 1)
        out_u[start:start + len(idx)] = u[rr, k]
        out_v[start:start + len(idx)] = v[rr, k]
        out_p[start:start + len(idx)] = P[rr, k]
    return out_d, out_i, out_j, out_u, out_v, out_p


def run():
    rows = {}
    for f in sorted((ROOT / '.n1/build1').glob('*.npz')):
        z = np.load(f)
        ln, h, run = str(z['lane']), str(z['design_hash']), str(z['run'])
        inner, outer, t = z['inner'], z['outer'], float(z['wall_thickness_mm'])
        xyz, t1, t2, ents = A.read_msh(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
        pts = xyz[t1]
        d_i, pi, pj, u, v, P = nearest_patch(pts, inner)
        d_o = A.patch_distance(pts, outer)
        # local inner->outer direction, bilinearly interpolated at the nearest patch
        dirs = outer - inner
        n = np.linalg.norm(dirs, axis=-1, keepdims=True)
        dirs = dirs / np.maximum(n, 1e-12)
        w = np.stack([(1 - u) * (1 - v), (1 - u) * v, u * (1 - v), u * v], axis=1)
        dd = np.stack([dirs[pi, pj], dirs[pi, pj + 1], dirs[pi + 1, pj], dirs[pi + 1, pj + 1]], axis=1)
        di = np.einsum('nk,nkc->nc', w, dd)
        di = di / np.maximum(np.linalg.norm(di, axis=1, keepdims=True), 1e-12)
        s = np.einsum('nc,nc->n', pts - P, di)
        near = np.minimum(d_i, d_o)
        unassigned = near > 3.0
        inner_core = (np.abs(s) <= 0.5) & ~unassigned
        outer_core = (np.abs(s - t) <= 0.5) & ~unassigned
        rim = ~inner_core & ~outer_core & ~unassigned
        q = np.quantile(d_i[inner_core], [.5, .99]) if inner_core.any() else [np.nan, np.nan]
        rec = dict(lane=ln, h=h, run=run, wall_t=t, n=len(pts),
                   n_inner=int(inner_core.sum()), n_outer=int(outer_core.sum()),
                   n_rim=int(rim.sum()), n_unassigned=int(unassigned.sum()),
                   inner_median_mm=float(q[0]), inner_p99_mm=float(q[1]),
                   inner_max_mm=float(d_i[inner_core].max()) if inner_core.any() else np.nan,
                   inner_gt1_count=int((d_i[inner_core] > 1.0).sum()),
                   pass_=bool(inner_core.any() and q[0] <= 0.3 and q[1] <= 1.0),
                   s_rim_range=[float(s[rim].min()), float(s[rim].max())] if rim.any() else None)
        rows.setdefault(ln, []).append(rec)
        print(json.dumps(rec, default=float), flush=True)
    json.dump(rows, open(ROOT / '.n1/separated.json', 'w'), indent=1, default=float)
    print('\nSUMMARY')
    for ln in LANES:
        d = rows[ln]
        print(ln, 'inner pass', sum(x['pass_'] for x in d), '/', len(d),
              'median-of-medians', round(float(np.median([x['inner_median_mm'] for x in d])), 4),
              'worst p99', round(float(np.max([x['inner_p99_mm'] for x in d])), 4),
              'rim nodes', [x['n_rim'] for x in d])


if __name__ == '__main__':
    run()
