import sys, json, pathlib
import numpy as np
sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')
import analyze as A
from build import sample
from hornlab_search.config import load_config
from hornlab_search.design.generators import rolled_family
ROOT = pathlib.Path('scratch/fable_architecture')

for h, run in [('320c10cf1173', '20261116T015510Z-screen-e75ec8'),
               ('d99b73012d8e', '20261116T015510Z-screen-e75ec8')]:
    import pickle
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    r = next(x for x in rows if x['h'] == h and x['run'] == run)
    import json as J
    p = J.loads((pathlib.Path('runs') / run / 'designs' / h / 'design.json').read_text())['params']
    cfg = load_config(pathlib.Path('runs') / run / 'config.yaml')
    g = rolled_family.resolve_grid(p['grid'], cfg.brief)
    inner, outer = np.asarray(g['inner_points']), np.asarray(g['outer_points'])
    xyz, t1, t2, ents = A.read_msh(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
    pts = xyz[t1]
    print('\n==', h, 'native', inner.shape)
    for nm, ii, oo in (('native', inner, outer),
                       ('record31x65', sample(inner, 31, 65), sample(outer, 31, 65))):
        di = A.patch_distance(pts, ii); do = A.patch_distance(pts, oo)
        m = do - di
        core = (m > 0) & (np.minimum(di, do) <= 3) & ((di <= .5) | (m > .5))
        q = np.quantile(di[core], [.5, .9, .99])
        print(f'  {nm}: inner nodes {core.sum()}, q50/q90/q99 {np.round(q,3)}, gt1 {(di[core]>1).sum()}, '
              f'max {di[core].max():.3f}')
