"""N1 inner-wall isolation by mesh topology.

A point-grid solid wall is one closed surface whose inner sheet, outer shell and closure faces
meet at sharp creases.  Cut every edge whose adjacent triangle normals differ by more than a
threshold, take the connected components, and identify the inner sheet as the component that is
closest to the sampled inner surface.  Then measure all its node distances to that surface.

This avoids the mouth-rim ambiguity of nearest-surface assignment (runbook 4b).
"""
import sys, json, pathlib, collections
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')
import analyze as A

ROOT = pathlib.Path('scratch/fable_architecture')
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7']


def parse(path):
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
    return pts, np.array(tris)


def components(T, pts, sharp_deg=50.0):
    n = len(T)
    p0, p1, p2 = pts[T[:, 0]], pts[T[:, 1]], pts[T[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    cr = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-12)
    edges = collections.defaultdict(list)
    for k in range(n):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((int(T[k, a]), int(T[k, b]))))].append(k)
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx
    cos_lim = np.cos(np.radians(sharp_deg))
    for e, fs in edges.items():
        if len(fs) != 2:
            continue
        i, j = fs
        if float(np.dot(cr[i], cr[j])) >= cos_lim:      # smooth enough: same sheet
            union(i, j)
    comp = collections.defaultdict(list)
    for k in range(n):
        comp[find(k)].append(k)
    return comp, cr


def run():
    res = {}
    for f in sorted((ROOT / '.n1/build1').glob('*.npz')):
        z = np.load(f); ln, h, run = str(z['lane']), str(z['design_hash']), str(z['run'])
        pts, T = parse(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
        inner = z['inner']
        comp, cr = components(T, pts)
        # component distance to the sampled inner surface (subsample large components for speed)
        info = []
        for key, faces in comp.items():
            nodes = sorted(set(T[faces].reshape(-1).tolist()))
            p = pts[nodes]
            sel = p if len(p) <= 800 else p[np.linspace(0, len(p) - 1, 800).astype(int)]
            d = A.patch_distance(sel, inner)
            area = 0.5 * np.linalg.norm(np.cross(pts[T[faces, 1]] - pts[T[faces, 0]],
                                                pts[T[faces, 2]] - pts[T[faces, 0]]), axis=1).sum()
            info.append(dict(faces=len(faces), nodes=len(nodes), area_cm2=round(float(area / 100), 2),
                             med_mm=float(np.median(d)), p90_mm=float(np.quantile(d, .9)),
                             node_ids=nodes))
        cands = [x for x in info if x['med_mm'] <= 0.5]
        chosen = max(cands, key=lambda x: x['nodes']) if cands else min(info, key=lambda x: x['med_mm'])
        nodes = chosen['node_ids']
        chosen = {k: v for k, v in chosen.items() if k != 'node_ids'}
        p = pts[nodes]
        d = A.patch_distance(p, inner)
        q = np.quantile(d, [.5, .99])
        rec = dict(lane=ln, h=h, run=run, n_components=len(comp), chosen=chosen,
                   n_nodes=len(nodes), median_mm=float(q[0]), p99_mm=float(q[1]),
                   max_mm=float(d.max()), gt1=int((d > 1.0).sum()),
                   pass_=bool(q[0] <= 0.3 and q[1] <= 1.0))
        res.setdefault(ln, []).append(rec)
        print(json.dumps(rec), flush=True)
    json.dump(res, open(ROOT / '.n1/components.json', 'w'), indent=1)
    print('\nSUMMARY')
    for ln in LANES:
        d = res[ln]
        print(ln, 'pass', sum(x['pass_'] for x in d), '/', len(d),
              'median-of-medians', round(float(np.median([x['median_mm'] for x in d])), 4),
              'worst p99', round(float(np.max([x['p99_mm'] for x in d])), 4),
              'components', [x['n_components'] for x in d])


if __name__ == '__main__':
    run()
