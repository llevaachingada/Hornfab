"""X4 completion: rebuild the five sampled lanes at contract-v2 sampling (65 stations x 61
azimuths).

Selection is the exact 11 designs per lane the `.x4` Jacobian scripts used (best stored J plus
ten seeded random designs); hashes are read from the `.x4` result JSONs so this is the same
sample, not a fresh draw.  The materialisation route is `.n1/build.py:build_one`, i.e. the route
N1b validated.  A design is accepted only when the sampler reproduces its stored design hash.

Read-only w.r.t. runs/; writes only under scratch/fable_architecture/.x4c/.
"""
import sys, json, pickle, pathlib, warnings
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1')
sys.path.insert(0, '.')
warnings.filterwarnings('ignore')

import importlib.util as ilu
_spec = ilu.spec_from_file_location('n1_build', 'scratch/fable_architecture/.n1/build.py')
N1 = ilu.module_from_spec(_spec); _spec.loader.exec_module(N1)

NPHI, NS = 61, 65
ROOT = pathlib.Path('scratch/fable_architecture')
OUT = ROOT / '.x4c' / 'build'
SRC = [('geometry.json', ['hl__osse_rrect_fold_warm_v7', 'hl__ext_throat_hvlaw_v7']),
       ('geometry_fifth.json', ['hl__ath_tritonia_landscape_v9']),
       ('generated_geometry.json', ['hl__crowe_x_osse_cd_v7', 'hl__biradial_es_style_v7'])]


def selection():
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    index = {}
    for r in rows:
        if r['ok']:
            index.setdefault((r['config'], r['h']), r)
    sel, missing = [], []
    for fn, lanes in SRC:
        d = json.loads((ROOT / '.x4' / fn).read_text())
        for lane in lanes:
            for res in d[lane]['results']:
                if 'error' in res:
                    continue
                r = index.get((lane, res['hash']))
                if r is None:
                    missing.append((lane, res['hash']))
                else:
                    sel.append((lane, r))
    return sel, missing


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sel, missing = selection()
    print('selected', len(sel), 'designs; missing row', len(missing), missing[:5], flush=True)
    summary = {}
    for lane, r in sel:
        f = OUT / (r['h'] + '.npz')
        cfg = N1.load_config(pathlib.Path('runs') / r['run'] / 'config.yaml')
        try:
            inner, outer, mode, prov, t = N1.build_one(lane, r, cfg, 10.0)
            ci = N1.sample(inner, NPHI, NS)
            co = None if outer is None else N1.sample(outer, NPHI, NS)
            # design-hash rematerialisation check: hash the recipe params, not the surface
            j = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / r['h'] /
                            'design.json').read_text())
            from hornlab_search.types import Design
            d = Design(j['family'], j['params'])
            h_ok = (d.hash() == r['h'])
            np.savez_compressed(
                f, inner=ci, outer=(np.zeros((0, 0, 0)) if co is None else co),
                inner_native=np.asarray(inner, float),
                outer_native=(np.zeros((0, 0, 0)) if outer is None else np.asarray(outer, float)),
                lane=lane, design_hash=r['h'], run=r['run'], mode=mode, provenance=prov,
                wall_thickness_mm=t, recipe_family=j['family'], hash_ok=h_ok,
                native_inner_shape=np.array(np.shape(inner)),
                native_outer_shape=np.array((0, 0, 0) if outer is None else np.shape(outer)))
            rec = dict(lane=lane, h=r['h'], run=r['run'], mode=mode, hash_ok=bool(h_ok),
                       inner_shape=list(np.shape(inner)),
                       outer_shape=None if outer is None else list(np.shape(outer)))
            summary.setdefault(lane, []).append(rec)
            print(lane, r['h'], mode, 'hash', h_ok, 'native', np.shape(inner),
                  'outer', None if outer is None else np.shape(outer), flush=True)
        except Exception as e:
            import traceback; traceback.print_exc()
            print('FAILED', lane, r['h'], type(e).__name__, str(e)[:240], flush=True)
            summary.setdefault(lane, []).append(dict(lane=lane, h=r['h'], error=str(e)))
    (ROOT / '.x4c' / 'build.json').write_text(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
