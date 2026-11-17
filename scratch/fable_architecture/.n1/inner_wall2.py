"""N1 final inner-wall isolation.

Adds to the nearest-surface rule a surface-boundary test: a node that projects past the first
or last station along the wall tangent is a rear-closure or mouth-rim node, not inner wall.
Reports per design; also a native-resolution sensitivity for the rolled lane (49x97 vs the
contract-minimum 31x65 record).
"""
import sys, json, pathlib
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')
import analyze as A
from separate import nearest_patch

ROOT = pathlib.Path('scratch/fable_architecture')
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7']


def classify(pts, inner, outer):
    nphi, ns = inner.shape[:2]
    d_i, pi, pj, u, v, P = nearest_patch(pts, inner)
    d_o = A.patch_distance(pts, outer)
    a = inner[:-1, :-1]
    B = inner[1:, :-1] - a
    C = inner[:-1, 1:] - a
    D = inner[1:, 1:] - a - B - C
    r = pts - P
    ts = C[pi, pj] + u[:, None] * D[pi, pj]
    ts = ts / np.maximum(np.linalg.norm(ts, axis=1, keepdims=True), 1e-12)
    along = np.einsum('nc,nc->n', r, ts)
    rn = np.linalg.norm(r, axis=1)
    beyond_lip = (pj == ns - 2) & (v > 0.99) & (along > 0.3 * rn)
    before_throat = (pj == 0) & (v < 0.01) & (along < -0.3 * rn)
    boundary = beyond_lip | before_throat
    near = np.minimum(d_i, d_o)
    unassigned = near > 3.0
    margin = d_o - d_i
    inner_core = (margin > 0) & (~unassigned) & (~boundary) & ((d_i <= 0.5) | (margin > 0.5))
    q = np.quantile(d_i[inner_core], [.5, .99]) if inner_core.any() else [np.nan, np.nan]
    return dict(n=len(pts), n_inner=int(inner_core.sum()),
                n_boundary=int(boundary.sum()), n_unassigned=int(unassigned.sum()),
                median_mm=float(q[0]), p99_mm=float(q[1]),
                max_mm=float(d_i[inner_core].max()) if inner_core.any() else np.nan,
                gt1=int((d_i[inner_core] > 1.0).sum()),
                pass_=bool(inner_core.any() and q[0] <= 0.3 and q[1] <= 1.0))


def run():
    res = {}
    for f in sorted((ROOT / '.n1/build1').glob('*.npz')):
        z = np.load(f); ln, h, run = str(z['lane']), str(z['design_hash']), str(z['run'])
        xyz, t1, t2, ents = A.read_msh(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
        rec = classify(xyz[t1], z['inner'], z['outer'])
        rec.update(lane=ln, h=h, run=run)
        res.setdefault(ln, []).append(rec)
        print(json.dumps(rec), flush=True)
    json.dump(res, open(ROOT / '.n1/inner_wall_final.json', 'w'), indent=1)
    print('\nSUMMARY  (contract-minimum record 65 stations x 31 azimuths)')
    for ln in LANES:
        d = res[ln]
        print(ln, 'pass', sum(x['pass_'] for x in d), '/', len(d),
              'median-of-medians', round(float(np.median([x['median_mm'] for x in d])), 4),
              'worst p99', round(float(np.max([x['p99_mm'] for x in d])), 4),
              'worst max', round(float(np.max([x['max_mm'] for x in d])), 4))

    # native-resolution sensitivity, rolled lane
    print('\nROLLED native 49x97 vs record 31x65')
    import pickle, json as J
    from build import sample, build_one
    from hornlab_search.config import load_config
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    for rec in res['rf__section_axial_home_v7']:
        h, run = rec['h'], rec['run']
        r = next(x for x in rows if x['h'] == h and x['run'] == run)
        cfg = load_config(pathlib.Path('runs') / run / 'config.yaml')
        inner, outer, mode, prov, t = build_one('rf__section_axial_home_v7', r, cfg, 10)
        xyz, t1, t2, ents = A.read_msh(pathlib.Path('runs') / run / 'designs' / h / 'mesh.msh')
        nat = classify(xyz[t1], np.asarray(inner), np.asarray(outer))
        rec['native'] = nat
        print(h, 'native p99', round(nat['p99_mm'], 3), 'pass', nat['pass_'],
              '| record p99', round(rec['p99_mm'], 3), 'pass', rec['pass_'], flush=True)
    json.dump(res, open(ROOT / '.n1/inner_wall_final.json', 'w'), indent=1)


if __name__ == '__main__':
    run()
