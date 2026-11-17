"""N1 inner-wall isolation, final: nearest-surface assignment (runbook 4b) plus a rim exclusion.

Runbook 4b assigns each tag-1 node to the nearer of the sampled inner and outer surfaces and
drops nodes >3 mm from both.  At a mouth rim the two sheets meet, so rim nodes can be ~t/2 from
both and are assigned arbitrarily.  Rim/closure nodes are identified here by a small margin:
a node is inner-wall only if it is nearer the inner surface AND either lies on the inner sheet
(d_i <= 0.5 mm) or is separated from the outer surface by > 0.5 mm.  Farther than 3 mm from both:
unassigned.  Everything else is rim/closure and is counted, not scored.
"""
import sys, json, pathlib, collections
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1')
sys.path.insert(0, '.')
import analyze as A

ROOT = pathlib.Path('scratch/fable_architecture')
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7']


def run():
    res = {}
    for f in sorted((ROOT / '.n1/build1').glob('*.npz')):
        z = np.load(f); ln, h, run = str(z['lane']), str(z['design_hash']), str(z['run'])
        inner, outer = z['inner'], z['outer']
        assert outer.size, h
        xyz, t1, t2, ents = A.read_msh(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
        pts = xyz[t1]
        d_i = A.patch_distance(pts, inner)
        d_o = A.patch_distance(pts, outer)
        near = np.minimum(d_i, d_o)
        unassigned = near > 3.0
        margin = d_o - d_i
        inner_core = (margin > 0.0) & (~unassigned) & ((d_i <= 0.5) | (margin > 0.5))
        outer_core = (margin <= 0.0) & (~unassigned) & ((d_o <= 0.5) | (-margin > 0.5))
        rim = ~inner_core & ~outer_core & ~unassigned
        q = np.quantile(d_i[inner_core], [.5, .99]) if inner_core.any() else [np.nan, np.nan]
        rec = dict(lane=ln, h=h, run=run, n=len(pts),
                   n_inner=int(inner_core.sum()), n_outer=int(outer_core.sum()),
                   n_rim=int(rim.sum()), n_unassigned=int(unassigned.sum()),
                   median_mm=float(q[0]), p99_mm=float(q[1]),
                   max_mm=float(d_i[inner_core].max()) if inner_core.any() else np.nan,
                   gt1=int((d_i[inner_core] > 1.0).sum()),
                   pass_=bool(inner_core.any() and q[0] <= 0.3 and q[1] <= 1.0))
        res.setdefault(ln, []).append(rec)
        print(json.dumps(rec), flush=True)
    json.dump(res, open(ROOT / '.n1/inner_wall.json', 'w'), indent=1)
    print('\nSUMMARY  (inner-wall nodes; median <= 0.3 mm, p99 <= 1.0 mm)')
    for ln in LANES:
        d = res[ln]
        print(ln, 'pass', sum(x['pass_'] for x in d), '/', len(d),
              'median-of-medians', round(float(np.median([x['median_mm'] for x in d])), 4),
              'worst p99', round(float(np.max([x['p99_mm'] for x in d])), 4),
              'worst max', round(float(np.max([x['max_mm'] for x in d])), 4),
              'inner/outer/rim/unassigned', [tuple(x[k] for k in ('n_inner', 'n_outer', 'n_rim', 'n_unassigned')) for x in d])


if __name__ == '__main__':
    run()
