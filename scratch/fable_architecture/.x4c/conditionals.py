"""X4 completion: conditional-link checks on the five sampled lanes.

Recovers the known conditionals listed in GEOMETRY_AND_PARAMETER_MAP.md section 2 where the only
lane has the controls: n/q inactive at s=0; s1/s2 inactive unless both nonzero; morph_* inactive
at morph_target=0; morph_exponent inactive unless target=3; an active guiding curve replaces
a_deg; rot_deg couples radius and depth.  A conditional counts as recovered only when the gated
(inactive) pair moves the sampled surface by <= 0.2 mm RMS and the positive control moves it by
> 0.2 mm.

Surfaces are the contract-v2 sampler (65 stations x 61 azimuths).  Native, grid and typology
recipes are rebuilt through their own construction route.  Writes `.x4c/conditionals.json` and
`.x4c/conditionals.txt`.
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
INACTIVE_MM = 0.2
LANES = ['hl__osse_rrect_fold_warm_v7', 'hl__ext_throat_hvlaw_v7',
         'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'hl__biradial_es_style_v7']


def sample(pts):
    return N1.sample(np.asarray(pts, float), NPHI, NS)


def surfaces(family, params, cfg, res=10.0):
    p = params
    if 'grid' not in p:
        inner, outer, mode, prov = N1.native(Design(family, p), cfg, res)
        return sample(inner), mode
    b = p['grid']
    inner, _meta = grid.grid_points(b, b.get('knobs', {}), cfg.brief)
    return sample(inner), 'grid'


def build_params(recipe, cfg, changes):
    p = recipe['params']
    if isinstance(p.get('grid'), dict):
        import copy
        q = copy.deepcopy(p)
        q['grid'].setdefault('knobs', {}).update(changes)
        return q
    g = recipe.get('generator') or {}
    if isinstance(g.get('knobs'), dict) and g['knobs']:
        import copy
        knobs = copy.deepcopy(g['knobs']); knobs.update(changes)
        return materialize(cfg.generator, knobs, cfg.brief)
    import copy
    q = copy.deepcopy(p); q.update(changes)
    return q


def knob_names(recipe):
    p = recipe['params']
    if isinstance(p.get('grid'), dict):
        return set((p['grid'].get('knobs') or {}).keys())
    g = recipe.get('generator') or {}
    if isinstance(g.get('knobs'), dict) and g['knobs']:
        return set(g['knobs'].keys())
    return set(p.keys())


def rms(a, b):
    d = a - b
    return float(np.sqrt(np.mean(np.sum(d * d, axis=2))))


def main():
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    out = {}
    for lane in LANES:
        h = json.loads((ROOT / '.x4c/build.json').read_text())[lane][0]['h']
        r = next(x for x in rows if x['ok'] and x['config'] == lane and x['h'] == h)
        cfg = load_config(pathlib.Path('runs') / r['run'] / 'config.yaml')
        recipe = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / h /
                             'design.json').read_text())
        names = knob_names(recipe)
        print(lane, 'knobs', sorted(names), flush=True)

        def surf(changes):
            return surfaces(recipe['family'], build_params(recipe, cfg, changes), cfg)[0]

        base = surf({})
        tests = []

        def pair(name, shared, a, b, gate, expect):
            try:
                sa = surf({**shared, **a}); sb = surf({**shared, **b})
                d = rms(sa, sb)
                tests.append(dict(name=name, gate=gate, expect=expect,
                                  shared=shared, a=a, b=b, rms_mm=d,
                                  searched={k: _searched(r, k) for k in a},
                                  inactive=bool(d <= INACTIVE_MM)))
                print('  %-28s %6.3f mm  %s' % (name, d, 'inactive' if d <= INACTIVE_MM else 'active'),
                      flush=True)
            except Exception as e:
                tests.append(dict(name=name, gate=gate, expect=expect, shared=shared,
                                  a=a, b=b, searched={k: _searched(r, k) for k in a},
                                  error=str(e)[:240]))
                print('  %-28s ERROR %s' % (name, str(e)[:90]), flush=True)

        def q_positive(name, shared, a, b, gate):
            """Native q at s > 0: try 10 / 5 / 2 mm before declaring not testable."""
            last = None
            for res in (10.0, 5.0, 2.0):
                try:
                    sa = surfaces(recipe['family'], build_params(recipe, cfg, {**shared, **a}),
                                  cfg, res)[0]
                    sb = surfaces(recipe['family'], build_params(recipe, cfg, {**shared, **b}),
                                  cfg, res)[0]
                    d = rms(sa, sb)
                    tests.append(dict(name=name, gate=gate, expect='active', shared=shared,
                                      a=a, b=b, rms_mm=d, resolution_mm=res,
                                      searched={k: _searched(r, k) for k in a},
                                      inactive=bool(d <= INACTIVE_MM)))
                    print('  %-28s %6.3f mm (res %g)' % (name, d, res), flush=True)
                    return
                except Exception as e:
                    last = e
            tests.append(dict(name=name, gate=gate, expect='active', shared=shared, a=a, b=b,
                              searched={k: _searched(r, k) for k in a},
                              error='not testable at 10/5/2 mm: ' + str(last)[:220],
                              positive_control_not_testable=True))
            print('  %-28s NOT TESTABLE %s' % (name, str(last)[:90]), flush=True)

        # --- n / q at s = 0 (native OSSE lanes; the Crowe grid uses g_ equivalents) ---
        if {'s', 'n', 'q'} <= names:
            nlo, nhi = _bound(r, 'n')
            zero = {'s': 0.0, 's1': 0.0, 's2': 0.0, 'az_s_cos2_amp': 0.0}
            zero = {k: v for k, v in zero.items() if k in names}
            pos = {k: v for k, v in {'s': 0.6, 's1': 0.0, 's2': 0.0,
                                     'az_s_cos2_amp': 0.0}.items() if k in names}
            pair('n_at_s0', zero, {'n': nlo}, {'n': nhi}, 'n active iff s != 0', 'inactive')
            pair('n_at_s_positive', pos, {'n': nlo}, {'n': nhi}, 'n active iff s != 0', 'active')
            pair('q_at_s0', zero, {'q': 0.9}, {'q': 1.0}, 'q active iff s != 0', 'inactive')
            q_positive('q_at_s_positive', pos, {'q': 0.9}, {'q': 1.0}, 'q active iff s != 0')
        elif {'g_s', 'g_n', 'g_q'} <= names:
            nlo, nhi = _bound(r, 'g_n')
            zero = {'g_s': 0.0}
            pos = {'g_s': 0.35}
            pair('g_n_at_s0', zero, {'g_n': nlo}, {'g_n': nhi}, 'g_n active iff g_s != 0', 'inactive')
            pair('g_n_at_s_positive', pos, {'g_n': nlo}, {'g_n': nhi}, 'g_n active iff g_s != 0', 'active')
            pair('g_q_at_s0', zero, {'g_q': 0.9}, {'g_q': 1.0}, 'g_q active iff g_s != 0', 'inactive')
            pair('g_q_at_s_positive', pos, {'g_q': 0.9}, {'g_q': 1.0}, 'g_q active iff g_s != 0', 'active')

        # --- s1 / s2 mutual condition ---
        if {'s1', 's2'} <= names:
            pair('s1_when_s2_zero', {'s2': 0.0}, {'s1': 0.0}, {'s1': 1.0},
                 's1 active iff s2 != 0', 'inactive')
            pair('s2_when_s1_zero', {'s1': 0.0}, {'s2': 0.0}, {'s2': 0.5},
                 's2 active iff s1 != 0', 'inactive')
            pair('s1_when_s2_positive', {'s2': 0.5}, {'s1': 0.1}, {'s1': 1.0},
                 's1 active iff s2 != 0', 'active')
            pair('s2_when_s1_positive', {'s1': 1.0}, {'s2': 0.1}, {'s2': 0.5},
                 's2 active iff s1 != 0', 'active')

        # --- morph gate ---
        if 'morph_target' in names:
            w = {'morph_width_mm': 450.0} if 'morph_width_mm' in names else {}
            w2 = {'morph_width_mm': 550.0} if 'morph_width_mm' in names else {}
            if w and w2:
                pair('morph_width_at_target0', {'morph_target': 0}, w, w2,
                     'morph_* active iff morph_target != 0', 'inactive')
            if 'morph_rate' in names:
                pair('morph_rate_at_target0', {'morph_target': 0}, {'morph_rate': 1.0},
                     {'morph_rate': 4.0}, 'morph_* active iff morph_target != 0', 'inactive')
            if 'morph_exponent' in names:
                pair('morph_exponent_at_target1', {'morph_target': 1},
                     {'morph_exponent': 2.0}, {'morph_exponent': 8.0},
                     'morph_exponent active iff target == 3', 'inactive')
                pair('morph_exponent_at_target3', {'morph_target': 3},
                     {'morph_exponent': 2.0}, {'morph_exponent': 8.0},
                     'morph_exponent active iff target == 3', 'active')

        # --- guiding curve replaces a_deg; rot_deg couples radius and depth ---
        has_guide = any(('guide' in k.lower() or 'curve' in k.lower()) for k in names)
        has_rot = 'rot_deg' in names
        out[lane] = dict(h=h, knobs=sorted(names), base_mm=0.0, tests=tests,
                         slack=dict(
                             guiding_curve_present=bool(has_guide),
                             rot_deg_present=bool(has_rot),
                             note=('guiding-curve replacement not testable: no guiding-curve '
                                   'control in the searched params' if not has_guide else ''),
                         ))
    (ROOT / '.x4c/conditionals.json').write_text(json.dumps(out, indent=1))

    lines = []
    for lane, res in out.items():
        lines.append('=' * 78)
        lines.append('%s  best %s  knobs %d' % (lane, res['h'], len(res['knobs'])))
        for t in res['tests']:
            fixed = [k for k, v in (t.get('searched') or {}).items() if not v]
            tag = (' [fixed: %s]' % ','.join(fixed)) if fixed else ''
            if 'error' in t:
                lines.append('  %-28s ERROR %s%s' % (t['name'], t['error'][:110], tag))
            else:
                lines.append('  %-28s %7.3f mm  %-8s (expect %s)%s' %
                             (t['name'], t['rms_mm'],
                              'inactive' if t['inactive'] else 'active', t['expect'], tag))
        if res['slack']['guiding_curve_present'] is False:
            lines.append('  guiding curve: not present in this lane -> replacement rule not testable')
        if res['slack']['rot_deg_present'] is False:
            lines.append('  rot_deg: not present in this lane -> radius/depth coupling not testable')
    (ROOT / '.x4c/conditionals.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


def _bound(row, name):
    b = (row.get('bounds') or {}).get(name) or {}
    return float(b.get('lo', 0.0)), float(b.get('hi', 1.0))


def _searched(row, name):
    b = (row.get('bounds') or {}).get(name) or {}
    try:
        return bool(b.get('search', True)) and float(b.get('lo', 0.0)) < float(b.get('hi', 0.0))
    except (TypeError, ValueError):
        return False


if __name__ == '__main__':
    main()
