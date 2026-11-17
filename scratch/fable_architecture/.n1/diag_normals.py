import sys, json, pathlib, collections
import numpy as np
sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')
import analyze as A
from separate import nearest_patch
from normal_check import inner_air_normals, mesh_normals, ROOT


def diag(h, run, title):
    z = np.load(ROOT / '.n1/build1' / (h + '.npz'))
    inner = z['inner']
    pts, T, nm, vol = mesh_normals(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
    ids = sorted(set(T.reshape(-1).tolist()))
    p = pts[ids]; n = nm[ids]
    d, pi, pj, u, v, P = nearest_patch(p, inner)
    pn = inner_air_normals(inner)
    w = np.stack([(1 - u) * (1 - v), (1 - u) * v, u * (1 - v), u * v], axis=1)
    cand = np.stack([pn[pi, pj], pn[pi, pj + 1], pn[pi + 1, pj], pn[pi + 1, pj + 1]], axis=1)
    na = np.einsum('nk,nkc->nc', w, cand)
    na = na / np.maximum(np.linalg.norm(na, axis=1, keepdims=True), 1e-12)
    dot = np.einsum('nc,nc->n', n, na)
    print('\n==', title, h, 'nodes', len(p))
    print(' dot percentiles', np.quantile(dot, [0, .1, .5, .9, 1]).round(3))
    for lo, hi in ((0.9, 1.1), (0.5, 0.9), (-0.5, 0.5), (-1.1, -0.5)):
        m = (dot >= lo) & (dot < hi)
        if m.any():
            print(f'  dot {lo}..{hi}: n {m.sum():4d}  dist q50/q90/q99 {np.quantile(d[m],[.5,.9,.99]).round(3)}  z q50 {np.quantile(p[m,2],.5).round(1)}')
    bad = (dot > 0.5) & (d > 1.0)
    if bad.any():
        print('  inner-classified >1mm:', bad.sum(), 'z', np.round(np.quantile(p[bad, 2], [0, .5, 1]), 1),
              'rho', np.round(np.quantile(np.hypot(p[bad, 0], p[bad, 1]), [0, .5, 1]), 1),
              'dot', np.round(np.quantile(dot[bad], [0, .5, 1]), 2))


diag('e52435b09614', '20261116T065413Z-screen-a70423', 'crowe')
diag('e94b7d4a783d', '20261116T205942Z-screen-8b22b5', 'klangfilm')
diag('fb3d83637f1c', '20261116T015510Z-screen-e75ec8', 'rolled')
