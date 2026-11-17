"""N1 inner-wall isolation by mesh surface normal (independent of outer sampling).

A closed solid wall has two sheets.  The solid's outward normal on the acoustic (inner) sheet
points into the air (toward smaller radius); on the exterior it points away.  Rim/closure faces
are perpendicular.  Classify each tag-1 node by dot(mesh normal, air-side normal of the nearest
sampled inner patch) and report the distance from inner-sheet nodes to the sampled inner surface.
"""
import sys, json, pathlib, collections
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, 'scratch/fable_architecture/.n1')
sys.path.insert(0, '.')
import analyze as A
from separate import nearest_patch

ROOT = pathlib.Path('scratch/fable_architecture')
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7']


def mesh_normals(path):
    txt = open(path).read()
    a = txt.index('$Nodes') + 7; b = txt.index('$EndNodes')
    blk = txt[a:b].strip().split('\n')
    nd = np.array(' '.join(blk[1:]).split(), float).reshape(-1, 4)
    ids = nd[:, 0].astype(int); pts = nd[:, 1:] * 1000
    ix = {int(i): k for k, i in enumerate(ids)}
    e0 = txt.index('$Elements') + 10; e1 = txt.index('$EndElements')
    tris = []
    for line in txt[e0:e1].split('\n')[1:]:
        p = line.split()
        if len(p) >= 8 and p[1] == '2' and p[3] == '1':
            tris.append([ix[int(x)] for x in p[-3:]])
    T = np.array(tris)
    p0, p1, p2 = pts[T[:, 0]], pts[T[:, 1]], pts[T[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    signed = np.einsum('ij,ij->i', p0, cr).sum() / 6
    if signed < 0:
        cr = -cr
    ntri = np.linalg.norm(cr, axis=1)
    nsum = np.zeros_like(pts)
    for k in range(3):
        np.add.at(nsum, T[:, k], cr)
    nn = np.linalg.norm(nsum, axis=1)
    nsum = nsum / np.maximum(nn, 1e-12)[:, None]
    return pts, T, nsum, float(signed)


def inner_air_normals(inner):
    """Vertex normals of the sampled inner sheet, oriented toward the axis (air side)."""
    tphi = np.gradient(inner, axis=0)
    ts = np.gradient(inner, axis=1)
    n = np.cross(tphi, ts)
    rho = np.hypot(inner[..., 0], inner[..., 1])
    rad = np.stack([inner[..., 0], inner[..., 1], np.zeros_like(rho)], axis=-1)
    rad = rad / np.maximum(rho, 1e-12)[..., None]
    dot = np.sum(n * rad, axis=-1)
    n = np.where((dot > 0)[..., None], -n, n)
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)


def run():
    res = {}
    for f in sorted((ROOT / '.n1/build1').glob('*.npz')):
        z = np.load(f); ln, h, run = str(z['lane']), str(z['design_hash']), str(z['run'])
        inner = z['inner']
        pts, T, nm, signed = mesh_normals(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
        # tag-1 node ids = nodes referenced by tag-1 triangles
        ids = sorted(set(T.reshape(-1).tolist()))
        p = pts[ids]; n = nm[ids]
        d, pi, pj, u, v, P = nearest_patch(p, inner)
        pn = inner_air_normals(inner)
        w = np.stack([(1 - u) * (1 - v), (1 - u) * v, u * (1 - v), u * v], axis=1)
        cand = np.stack([pn[pi, pj], pn[pi, pj + 1], pn[pi + 1, pj], pn[pi + 1, pj + 1]], axis=1)
        na = np.einsum('nk,nkc->nc', w, cand)
        na = na / np.maximum(np.linalg.norm(na, axis=1, keepdims=True), 1e-12)
        dot = np.einsum('nc,nc->n', n, na)
        core = (dot > 0.5) & (d <= 3.0)
        q = np.quantile(d[core], [.5, .99]) if core.any() else [np.nan, np.nan]
        rec = dict(lane=ln, h=h, run=run, n=len(ids), n_inner=int(core.sum()),
                   n_other=int((~core).sum()), median_mm=float(q[0]), p99_mm=float(q[1]),
                   max_mm=float(d[core].max()) if core.any() else np.nan,
                   gt1=int((d[core] > 1.0).sum()),
                   pass_=bool(core.any() and q[0] <= 0.3 and q[1] <= 1.0),
                   signed_mesh_volume_mm3=round(signed, 1))
        res.setdefault(ln, []).append(rec)
        print(json.dumps(rec), flush=True)
    json.dump(res, open(ROOT / '.n1/normal_separation.json', 'w'), indent=1)
    print('\nSUMMARY')
    for ln in LANES:
        d = res[ln]
        print(ln, 'pass', sum(x['pass_'] for x in d), '/', len(d),
              'median-of-medians', round(float(np.median([x['median_mm'] for x in d])), 4),
              'worst p99', round(float(np.max([x['p99_mm'] for x in d])), 4),
              'inner nodes', [x['n_inner'] for x in d])


if __name__ == '__main__':
    run()
