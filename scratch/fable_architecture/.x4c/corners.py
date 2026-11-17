"""X4 completion: box-corner and constraint-margin scan.

For each of the five `.x4` lanes, at the best stored design:
  * one-at-a-time box extremes (every searched knob at lo and at hi);
  * the all-lo and all-hi corners;
  * four directed constraint corners, chosen from the one-at-a-time results to push W, H,
    depth and the wall gap toward their limits.

Reported per build, sign convention positive = inside the limit:
  * envelope margin per axis (W <= 600 + 0.5, H <= 480 + 0.5, depth <= 480 + 15 mm);
  * wall-gap margin, gap - (2 t + 2) mm, where the grid route configures that limit; native
    lanes have no configured gap limit, so the measured gap is reported without a margin;
  * throat-radius margin, r(throat) - brief driver exit radius (18 mm).

Surfaces are the contract-v2 sampler (65 stations x 61 azimuths).  Writes
`.x4c/corners.json` and `.x4c/corners.txt`.
"""
import sys, json, pickle, pathlib, copy, warnings
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
ENV = {'W': (600.0, 0.5), 'H': (480.0, 0.5), 'D': (480.0, 15.0)}


def sample(pts):
    return N1.sample(np.asarray(pts, float), NPHI, NS)


def surfaces(family, params, cfg):
    """(inner, outer) sampled at 65 x 61, same routes as N1.build_one."""
    p = copy.deepcopy(params)
    if 'grid' not in p:
        inner, outer, mode, prov = N1.native(Design(family, p), cfg, 10.0)
        return sample(inner), (None if outer is None else sample(outer)), mode
    b = p['grid']
    rows = b.get('rows') or {}
    if rows.get('type') in ('klangfilm_lame', 'crowe_panel', 'rosse_rect', 'rolled_rect',
                            'rolled_rect_pucker', 'lecleach'):
        raise NotImplementedError('bridge lane not part of the five-lane corner scan')
    inner, _meta = grid.grid_points(b, b.get('knobs', {}), cfg.brief)
    t = float(b.get('wall_thickness_mm') or 0.0)
    outer = grid.grid_outer_points(inner, t) if t > 0 else None
    return sample(inner), (None if outer is None else sample(outer)), 'grid'


def set_param(params, k, v):
    p = copy.deepcopy(params)
    if 'grid' in p and k.startswith('g_') and k in (p['grid'].get('knobs') or {}):
        p['grid']['knobs'][k] = v
    else:
        p[k] = v
    return p


def knob_source(recipe):
    """The dict that holds the searched knob values for this recipe."""
    p = recipe['params']
    if isinstance(p.get('grid'), dict) and isinstance(p['grid'].get('knobs'), dict):
        return p['grid']['knobs']
    g = recipe.get('generator') or {}
    if isinstance(g.get('knobs'), dict) and g['knobs']:
        return g['knobs']
    return p


def build_params(recipe, cfg, changes):
    """Apply {knob: value} through the recipe's own construction route."""
    p = recipe['params']
    if isinstance(p.get('grid'), dict):
        q = copy.deepcopy(p)
        q['grid'].setdefault('knobs', {}).update(changes)
        return q
    g = recipe.get('generator') or {}
    if isinstance(g.get('knobs'), dict) and g['knobs']:
        knobs = copy.deepcopy(g['knobs'])
        knobs.update(changes)
        return materialize(cfg.generator, knobs, cfg.brief)
    q = copy.deepcopy(p)
    q.update(changes)
    return q


def metrics(inner, outer, cfg, t):
    pts = inner if outer is None else np.vstack([inner.reshape(-1, 3), outer.reshape(-1, 3)])
    W = 2.0 * float(np.max(np.abs(pts[:, 0])))
    H = 2.0 * float(np.max(np.abs(pts[:, 1])))
    D = float(np.ptp(pts[:, 2]))
    env = {'W_mm': W, 'H_mm': H, 'D_mm': D,
           'W_margin': ENV['W'][0] + ENV['W'][1] - W,
           'H_margin': ENV['H'][0] + ENV['H'][1] - H,
           'D_margin': ENV['D'][0] + ENV['D'][1] - D}
    try:
        gap = grid.min_self_approach_mm(inner, outer, limit_mm=2.0 * t + 2.0)
    except Exception:
        gap = None
    limit = 2.0 * t + 2.0
    throat = np.sqrt(inner[:, 0, 0] ** 2 + inner[:, 0, 1] ** 2)
    return env, gap, limit, dict(throat_min_mm=float(throat.min()),
                                 throat_max_mm=float(throat.max()),
                                 throat_margin_mm=float(throat.min() - 18.0))


def rms(a, b):
    d = a - b
    return float(np.sqrt(np.mean(np.sum(d * d, axis=2))))


def run():
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    out = {}
    for lane in LANES:
        z = np.load(ROOT / '.x4c/build' / (json.loads(
            (ROOT / '.x4c/build.json').read_text())[lane][0]['h'] + '.npz'))
        h = str(z['design_hash'])
        r = next(x for x in rows if x['ok'] and x['config'] == lane and x['h'] == h)
        cfg = load_config(pathlib.Path('runs') / r['run'] / 'config.yaml')
        recipe = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / h /
                             'design.json').read_text())
        params = recipe['params']
        ksrc = knob_source(recipe)
        t = float(recipe.get('params', {}).get('wall_thickness_mm')
                  or (params.get('grid') or {}).get('wall_thickness_mm') or 3.0)
        b = r['bounds']
        keys = [k for k, v in b.items() if isinstance(v, dict) and v.get('search', True)
                and isinstance(v.get('lo'), (int, float)) and isinstance(v.get('hi'), (int, float))
                and v['hi'] > v['lo'] and isinstance(ksrc.get(k), (int, float))]
        base_i, base_o, mode = surfaces(recipe['family'], params, cfg)
        basem, gap, limit, throat = metrics(base_i, base_o, cfg, t)
        res = dict(lane=lane, h=h, mode=mode, wall_thickness_mm=t, keys=keys,
                   base=dict(env=basem, gap_mm=gap, gap_limit_mm=limit, **throat),
                   one_at_a_time=[], all_lo=None, all_hi=None, directed=[],
                   errors=[])

        def record(tag, vals, inner, outer):
            env, g, lim, th = metrics(inner, outer, cfg, t)
            return dict(tag=tag, values=vals, rms_vs_base_mm=rms(inner, base_i),
                        env=env, gap_mm=g, gap_limit_mm=lim,
                        gap_margin=None if g is None else g - lim, **th)

        for k in keys:
            for end in ('lo', 'hi'):
                v = b[k][end]
                try:
                    ii, oo, _ = surfaces(recipe['family'],
                                         build_params(recipe, cfg, {k: v}), cfg)
                    res['one_at_a_time'].append(record('%s=%s' % (k, end), {k: v}, ii, oo))
                except Exception as e:
                    res['errors'].append(dict(tag='%s=%s' % (k, end), error=str(e)[:240]))
            print(lane, k, 'done', flush=True)

        for tag, end in (('all_lo', 'lo'), ('all_hi', 'hi')):
            changes = {k: b[k][end] for k in keys}
            try:
                ii, oo, _ = surfaces(recipe['family'], build_params(recipe, cfg, changes), cfg)
                res[tag] = record(tag, changes, ii, oo)
            except Exception as e:
                res['errors'].append(dict(tag=tag, error=str(e)[:240]))

        # directed corners: push one margin of interest toward/over its limit
        def ranked(direction):
            scored = []
            for rec in res['one_at_a_time']:
                k = next(iter(rec['values']))
                v = rec['values'][k]
                key = {'W': 'W_mm', 'H': 'H_mm', 'D': 'D_mm'}[direction]
                scored.append((rec['env'][key] - basem[key], k, v))
            scored.sort(reverse=True)
            return scored

        def gap_ranked():
            scored = []
            for rec in res['one_at_a_time']:
                if rec['gap_mm'] is None:
                    continue
                k = next(iter(rec['values']))
                scored.append((rec['gap_mm'] - (res['base']['gap_mm'] or 0.0),
                               k, rec['values'][k]))
            scored.sort()
            return scored

        directed = {'W': ranked('W')[:3], 'H': ranked('H')[:3], 'D': ranked('D')[:2],
                    'gap': gap_ranked()[:2]}
        for name, picks in directed.items():
            if not picks:
                continue
            vals = {k: v for _, k, v in picks}
            try:
                ii, oo, _ = surfaces(recipe['family'], build_params(recipe, cfg, vals), cfg)
                res['directed'].append(record('directed_' + name, vals, ii, oo))
            except Exception as e:
                res['errors'].append(dict(tag='directed_' + name, error=str(e)[:240]))
        out[lane] = res
        print(lane, 'base', basem, 'gap', gap, 'errors', len(res['errors']), flush=True)
    (ROOT / '.x4c/corners.json').write_text(json.dumps(out, indent=1))

    lines = []
    for lane, res in out.items():
        lines.append('=' * 78)
        lines.append('%s  best %s  route %s  t=%.1f mm' % (lane, res['h'], res['mode'],
                                                            res['wall_thickness_mm']))
        bm = res['base']
        lines.append('base: W %.2f (marg %+.2f)  H %.2f (%+.2f)  D %.2f (%+.2f)  '
                     'gap %s  throat %.2f-%.2f (marg %+.2f)'
                     % (bm['env']['W_mm'], bm['env']['W_margin'], bm['env']['H_mm'],
                        bm['env']['H_margin'], bm['env']['D_mm'], bm['env']['D_margin'],
                        ('%.2f (limit %.2f, marg %+.2f)' % (bm['gap_mm'], bm['gap_limit_mm'],
                                                           bm['gap_mm'] - bm['gap_limit_mm'])
                         if bm['gap_mm'] is not None else 'n/a'),
                        bm['throat_min_mm'], bm['throat_max_mm'], bm['throat_margin_mm']))
        allrec = res['one_at_a_time'] + [res['all_lo'], res['all_hi']] + res['directed']
        allrec = [x for x in allrec if x]
        for axis in ('W', 'H', 'D'):
            rec = min(allrec, key=lambda x: x['env'][axis + '_margin'])
            lines.append('  min %s margin %+.2f mm at %s (rms %.2f)' %
                         (axis, rec['env'][axis + '_margin'], rec['tag'], rec['rms_vs_base_mm']))
        gr = [x for x in allrec if x['gap_margin'] is not None]
        if gr:
            rec = min(gr, key=lambda x: x['gap_margin'])
            lines.append('  min gap margin %+.2f mm (%s, gap %.2f)' %
                         (rec['gap_margin'], rec['tag'], rec['gap_mm']))
        if res['errors']:
            lines.append('  refusals: ' + '; '.join('%s: %s' % (e['tag'], e['error'][:80])
                                                    for e in res['errors'][:8]))
    (ROOT / '.x4c/corners.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    run()
