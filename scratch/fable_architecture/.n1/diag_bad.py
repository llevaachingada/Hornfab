import sys, pathlib
import numpy as np
sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')
import analyze as A
ROOT = pathlib.Path('scratch/fable_architecture')


def show(h, run, lane):
    z = np.load(ROOT / '.n1/build1' / (h + '.npz'))
    inner, outer = z['inner'], z['outer']
    xyz, t1, t2, ents = A.read_msh(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
    p = xyz[t1]
    di = A.patch_distance(p, inner); do = A.patch_distance(p, outer)
    m = do - di
    core = (m > 0) & (np.minimum(di, do) <= 3) & ((di <= .5) | (m > .5))
    bad = core & (di > 1.0)
    rho = np.hypot(p[:, 0], p[:, 1])
    zmax = inner[..., 2].max(); zmin = inner[..., 2].min()
    print(f'\n== {lane} {h}: inner nodes {core.sum()}, >1mm {bad.sum()}, '
          f'inner z {zmin:.1f}..{zmax:.1f}, lip rho max {np.hypot(inner[...,0],inner[...,1]).max():.1f}')
    print(' bad z q', np.round(np.quantile(p[bad, 2], [0, .1, .5, .9, 1]), 1))
    print(' bad rho q', np.round(np.quantile(rho[bad], [0, .1, .5, .9, 1]), 1))
    print(' bad di q', np.round(np.quantile(di[bad], [0, .5, 1]), 2),
          ' do q', np.round(np.quantile(do[bad], [0, .5, 1]), 2))
    for name, sel in (('z<10mm', p[bad, 2] < 10), ('z>0.85*zmax', p[bad, 2] > .85 * zmax)):
        print(f'  {name}: {sel.sum()}/{len(p[bad])}')
    # nearest tag-2 (source) node distance for the bad nodes
    if t2:
        src = xyz[t2]
        from scipy.spatial import cKDTree
        dsrc = cKDTree(src).query(p[bad])[0]
        print('  distance of bad nodes to tag-2 source nodes q', np.round(np.quantile(dsrc, [0, .5, 1]), 2))


show('9f7b158c831d', '20261116T065413Z-screen-a70423', 'crowe')
show('320c10cf1173', '20261116T015510Z-screen-e75ec8', 'rolled')
show('75ff51c58278', '20261115T143219Z-screen-d3a1bb', 'ext')
show('b9ea3ad77e3f', '20261116T205942Z-screen-8b22b5', 'klangfilm')
show('f9255dd45f77', '20261117T003115Z-screen-4f7cd5', 'ath')
