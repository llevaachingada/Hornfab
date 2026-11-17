import sys, json, pathlib, pickle
import numpy as np
sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')
import analyze as A
from build import sample, build_one
from component_check import parse, components
from hornlab_search.config import load_config
ROOT = pathlib.Path('scratch/fable_architecture')
rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))


def chosen_nodes(pts, T, inner):
    comp, cr = components(T, pts)
    best = None
    for key, faces in comp.items():
        nodes = sorted(set(T[faces].reshape(-1).tolist()))
        p = pts[nodes]
        sel = p if len(p) <= 800 else p[np.linspace(0, len(p) - 1, 800).astype(int)]
        d = A.patch_distance(sel, inner)
        md = float(np.median(d))
        if best is None or (md <= 0.5 and len(nodes) > best[0]) or (md > 0.5 and best[0] == -1):
            best = (len(nodes) if md <= 0.5 else -1, nodes)
    return best[1]


def q(pts, inner):
    d = A.patch_distance(pts, inner)
    return np.round(np.quantile(d, [.5, .99]), 3).tolist(), int((d > 1).sum()), round(float(d.max()), 2)


print('CROWE 9f7b158c831d')
h, run = '9f7b158c831d', '20261116T065413Z-screen-a70423'
r = next(x for x in rows if x['h'] == h and x['run'] == run)
cfg = load_config(pathlib.Path('runs') / run / 'config.yaml')
inner, outer, mode, prov, t = build_one('hl__crowe_x_osse_cd_v7', r, cfg, 10)
pts, T = parse(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
nodes = chosen_nodes(pts, T, sample(inner, 31, 65))
p = pts[nodes]
print(' inner component nodes', len(nodes))
for nm, g in (('native 25x41', inner), ('record 31x65', sample(inner, 31, 65)),
              ('dense 61x129 linear', sample(inner, 61, 129)),
              ('31 azimuth x native stations', sample(inner, 31, inner.shape[1])),
              ('native azimuth x 65 stations', sample(inner, inner.shape[0], 65))):
    print(' ', nm, g.shape, q(p, g))

print('\nROLLED 320c10cf1173')
h, run = '320c10cf1173', '20261116T015510Z-screen-e75ec8'
r = next(x for x in rows if x['h'] == h and x['run'] == run)
cfg = load_config(pathlib.Path('runs') / run / 'config.yaml')
inner, outer, mode, prov, t = build_one('rf__section_axial_home_v7', r, cfg, 10)
pts, T = parse(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
nodes = chosen_nodes(pts, T, sample(inner, 31, 65))
p = pts[nodes]
print(' inner component nodes', len(nodes))
for nm, g in (('native 49x97', inner), ('record 31x65', sample(inner, 31, 65)),
              ('49 azimuth x 65 st', sample(inner, inner.shape[0], 65)),
              ('31 azimuth x 97 st', sample(inner, 31, inner.shape[1])),
              ('61 azimuth x 97 st', sample(inner, 61, inner.shape[1])),
              ('61x129', sample(inner, 61, 129))):
    print(' ', nm, g.shape, q(p, g))

print('\nKLANGFLM b9ea3ad77e3f')
h, run = 'b9ea3ad77e3f', '20261116T205942Z-screen-8b22b5'
r = next(x for x in rows if x['h'] == h and x['run'] == run)
cfg = load_config(pathlib.Path('runs') / run / 'config.yaml')
inner, outer, mode, prov, t = build_one('hl__klangfilm_lame_curved_v1', r, cfg, 10)
pts, T = parse(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
nodes = chosen_nodes(pts, T, sample(inner, 31, 65))
p = pts[nodes]
print(' inner component nodes', len(nodes))
for nm, g in (('native 19x65', inner), ('record 31x65', sample(inner, 31, 65)),
              ('61x129', sample(inner, 61, 129))):
    print(' ', nm, g.shape, q(p, g))
