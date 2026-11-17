"""X4 completion: full-range box-corner movement per searched knob.

The `.x4` Jacobian used a 1 %-of-range step; that is a step size, not the full effect of a bound.
This script builds the best design with each searched knob at its lo and at its hi (contract-v2
65 x 61 surface) and reports RMS(lo, hi) in mm.  A knob is `inactive here` only when that
full-range movement is <= 0.2 mm at every sampled design knobs' bounds; `borderline` marks
0.2-0.5 mm, which is where the 1 %-step evidence and the bound evidence disagree.

Also reports the signed envelope margin at each extreme so a corner that leaves the envelope is
visible.  Writes `.x4c/range_movement.json` and `.x4c/range_movement.txt`.
"""
import sys, json, pickle, pathlib, warnings
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1')
sys.path.insert(0, '.')
warnings.filterwarnings('ignore')

import importlib.util as ilu
_s = ilu.spec_from_file_location('n1_build', 'scratch/fable_architecture/.n1/build.py')
N1 = ilu.module_from_spec(_s); _s.loader.exec_module(N1)
from hornlab_search.config import load_config
from hornlab_search.types import Design
from hornlab_search.design.generators import grid
from hornlab_search.design.generated import materialize

ROOT = pathlib.Path('scratch/fable_architecture')
NPHI, NS = 61, 65
LANES = ['hl__osse_rrect_fold_warm_v7', 'hl__ext_throat_hvlaw_v7',
         'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'hl__biradial_es_style_v7']
LIM = dict(W=600.5, H=480.5, D=495.0)


def sample(pts):
    return N1.sample(np.asarray(pts, float), NPHI, NS)


def surfaces(family, params, cfg):
    p = params
    if 'grid' not in p:
        inner, outer, mode, prov = N1.native(Design(family, p), cfg, 10.0)
        return sample(inner), mode
    b = p['grid']
    inner, _meta = grid.grid_points(b, b.get('knobs', {}), cfg.brief)
    return sample(inner), 'grid'


def build_params(recipe, cfg, changes):
    import copy
    p = recipe['params']
    if isinstance(p.get('grid'), dict):
        q = copy.deepcopy(p); q['grid'].setdefault('knobs', {}).update(changes); return q
    g = recipe.get('generator') or {}
    if isinstance(g.get('knobs'), dict) and g['knobs']:
        knobs = copy.deepcopy(g['knobs']); knobs.update(changes)
        return materialize(cfg.generator, knobs, cfg.brief)
    q = copy.deepcopy(p); q.update(changes); return q


def knob_source(recipe):
    p = recipe['params']
    if isinstance(p.get('grid'), dict) and isinstance(p['grid'].get('knobs'), dict):
        return p['grid']['knobs']
    g = recipe.get('generator') or {}
    if isinstance(g.get('knobs'), dict) and g['knobs']:
        return g['knobs']
    return p


def rms(a, b):
    d = a - b
    return float(np.sqrt(np.mean(np.sum(d * d, axis=2))))


def env(inner):
    # outer is not needed for a first-order margin; use the inner sheet and say so
    p = np.asarray(inner, float)
    return dict(W_margin=LIM['W'] - 2 * float(np.max(np.abs(p[:, :, 0]))),
                H_margin=LIM['H'] - 2 * float(np.max(np.abs(p[:, :, 1]))),
                D_margin=LIM['D'] - float(np.ptp(p[:, :, 2])))


def main():
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    out = {}
    for lane in LANES:
        h = json.loads((ROOT / '.x4c/build.json').read_text())[lane][0]['h']
        r = next(x for x in rows if x['ok'] and x['config'] == lane and x['h'] == h)
        cfg = load_config(pathlib.Path('runs') / r['run'] / 'config.yaml')
        recipe = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / h /
                             'design.json').read_text())
        ksrc = knob_source(recipe)
        b = r['bounds']
        keys = [k for k, v in b.items() if isinstance(v, dict) and v.get('search', True)
                and isinstance(v.get('lo'), (int, float)) and isinstance(v.get('hi'), (int, float))
                and v['hi'] > v['lo'] and isinstance(ksrc.get(k), (int, float))]
        recs = []
        for k in keys:
            try:
                lo_i, _ = surfaces(recipe['family'],
                                   build_params(recipe, cfg, {k: b[k]['lo']}), cfg)
                hi_i, _ = surfaces(recipe['family'],
                                   build_params(recipe, cfg, {k: b[k]['hi']}), cfg)
                recs.append(dict(knob=k, lo=b[k]['lo'], hi=b[k]['hi'],
                                 rms_full_range_mm=rms(lo_i, hi_i),
                                 lo_env=env(lo_i), hi_env=env(hi_i)))
            except Exception as e:
                recs.append(dict(knob=k, lo=b[k]['lo'], hi=b[k]['hi'],
                                 error='%s: %s' % (type(e).__name__, str(e)[:200])))
        out[lane] = recs
        print(lane, 'done', len(recs), flush=True)
    (ROOT / '.x4c/range_movement.json').write_text(json.dumps(out, indent=1))

    lines = []
    for lane, recs in out.items():
        lines.append('=' * 78)
        lines.append('%s  full-range RMS(lo, hi) at the best design' % lane)
        for rec in recs:
            if 'error' in rec:
                lines.append('  %-28s ERROR %s' % (rec['knob'], rec['error'][:90]))
                continue
            tag = ('inactive' if rec['rms_full_range_mm'] <= 0.2 else
                   'borderline' if rec['rms_full_range_mm'] <= 0.5 else 'active')
            wm = min(rec['lo_env']['W_margin'], rec['hi_env']['W_margin'])
            hm = min(rec['lo_env']['H_margin'], rec['hi_env']['H_margin'])
            dm = min(rec['lo_env']['D_margin'], rec['hi_env']['D_margin'])
            lines.append('  %-28s %8.3f mm  %-10s  worst corner margins W %+.1f H %+.1f D %+.1f' %
                         (rec['knob'], rec['rms_full_range_mm'], tag, wm, hm, dm))
    (ROOT / '.x4c/range_movement.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
