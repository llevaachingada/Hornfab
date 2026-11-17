"""N1b surface build under contract v2.

Reuses .n1/build.py's routes. Differences:
  * record azimuth count 61 (v2 rule 1), 65 stations unchanged;
  * an un-sampled copy of the generator's native inner/outer points is stored, so the
    native floor (v2 rule 2) is measured against the generator's own resolution;
  * provenance gate (v2 rule 4): a stored implementation_sha256 must equal HEAD's value.
    The ten N1 Klangfilm designs fail it (e3a1f4a3 != HEAD ea5026); ten digest-verified
    replacements are selected by a fixed rule (run then design-hash order, first ten
    distinct with a stored mesh). The five other lanes store no digest; gate N/A.

Run: .venv/Scripts/python.exe scratch/fable_architecture/.n1b/build.py <outdir> [--limit N]
Read-only w.r.t. runs/; writes only under the given .n1b/ subfolder.
"""
import sys, json, pickle, pathlib, warnings
import numpy as np

sys.path.insert(0, 'scratch/fable_architecture/.n1'); sys.path.insert(0, '.')
warnings.filterwarnings('ignore')

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('n1_build', 'scratch/fable_architecture/.n1/build.py')
N1B = _ilu.module_from_spec(_spec); _spec.loader.exec_module(N1B)   # .n1 routes/sample/build_one
from hornlab_search.config import load_config
from tools.geometry import klangfilm_lame_cli

NPHI, NS = 61, 65
LANES = ['hl__ext_throat_hvlaw_v7', 'hl__ath_tritonia_landscape_v9', 'hl__crowe_x_osse_cd_v7',
         'rf__section_axial_home_v7', 'hl__klangfilm_lame_curved_v1', 'hl__biradial_es_style_v7',
         'hl__lecleach_hv_landscape_smooth_v7']
KL = 'hl__klangfilm_lame_curved_v1'
CUR_KLANG_DIGEST = klangfilm_lame_cli.implementation_digest()
ROOT = pathlib.Path('scratch/fable_architecture')


def digest_of(r):
    p = json.loads((pathlib.Path('runs') / r['run'] / 'designs' / r['h'] / 'design.json').read_text())['params']
    return ((p.get('grid') or {}).get('rows') or {}).get('implementation_sha256')


def selection():
    rows = pickle.load(open(ROOT / '.fable/rows.pkl', 'rb'))
    by = {}
    for f in sorted((ROOT / '.x1').glob('*.npz')):
        z = np.load(f)
        ln = str(z['lane'])
        if ln == KL:
            continue
        by.setdefault(ln, []).append((str(z['design_hash']), str(z['run'])))
    # provenance gate for Klangfilm: only designs whose stored digest HEAD reproduces
    verified = [r for r in rows if r['config'] == KL and r['ok'] and digest_of(r) == CUR_KLANG_DIGEST
                and (pathlib.Path('runs') / r['run'] / 'designs' / r['h'] / 'mesh.msh').is_file()]
    verified.sort(key=lambda r: (r['run'], r['h']))
    seen, kl = set(), []
    for r in verified:
        if r['h'] in seen:
            continue
        seen.add(r['h']); kl.append((r['h'], r['run']))
        if len(kl) == 10:
            break
    by[KL] = kl
    # lanes with no .x1 selection: first ten distinct valid designs by (run, hash) with a stored mesh
    for ln in LANES:
        if ln in by:
            continue
        pool = [r for r in rows if r['config'] == ln and r['ok']
                and (pathlib.Path('runs') / r['run'] / 'designs' / r['h'] / 'mesh.msh').is_file()]
        pool.sort(key=lambda r: (r['run'], r['h']))
        seen, sel = set(), []
        for r in pool:
            if r['h'] in seen:
                continue
            seen.add(r['h']); sel.append((r['h'], r['run']))
            if len(sel) == 10:
                break
        by[ln] = sel
    out = []
    for ln in LANES:
        seen = set()
        for h, run in by.get(ln, []):
            if h in seen:
                continue
            seen.add(h)
            r = next((x for x in rows if x['run'] == run and x['h'] == h), None)
            if r is not None:
                out.append((ln, r))
        print(ln, 'selected', len(seen), flush=True)
    print('klangfilm HEAD digest', CUR_KLANG_DIGEST, flush=True)
    print('klangfilm verified replacements', [(h, run) for h, run in kl], flush=True)
    excluded = sorted({r['h'] for r in rows if r['config'] == KL and r['ok'] and
                       digest_of(r) not in (None, CUR_KLANG_DIGEST)})
    print('klangfilm excluded by digest gate', len(excluded), 'designs', excluded[:15], flush=True)
    return out


def main():
    outdir = pathlib.Path(sys.argv[1])
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    outdir.mkdir(parents=True, exist_ok=True)
    sel = selection()
    if limit:
        # one per lane for a smoke test
        keep, lanes = [], set()
        for ln, r in sel:
            if ln not in lanes:
                lanes.add(ln); keep.append((ln, r))
            if len(keep) >= limit:
                break
        sel = keep
    for lane, r in sel:
        if (outdir / (r['h'] + '.npz')).is_file():
            continue
        cfg = load_config(pathlib.Path('runs') / r['run'] / 'config.yaml')
        try:
            inner, outer, mode, prov, t = N1B.build_one(lane, r, cfg, 10.0)
            ci = N1B.sample(inner, NPHI, NS)
            co = None if outer is None else N1B.sample(outer, NPHI, NS)
            np.savez_compressed(outdir / (r['h'] + '.npz'),
                                inner=ci, outer=(np.zeros((0, 0, 0)) if co is None else co),
                                inner_native=np.asarray(inner, float),
                                outer_native=(np.zeros((0, 0, 0)) if outer is None else np.asarray(outer, float)),
                                lane=lane, design_hash=r['h'], run=r['run'], mode=mode,
                                provenance=prov, wall_thickness_mm=t,
                                native_inner_shape=np.array(np.shape(inner)),
                                native_outer_shape=np.array((0, 0, 0) if outer is None else np.shape(outer)))
            print(lane, r['h'], mode, 'native', np.shape(inner),
                  'outer', None if outer is None else np.shape(outer), 'record 65x%d' % NPHI, flush=True)
        except Exception as e:
            import traceback; traceback.print_exc()
            print('FAILED', lane, r['h'], type(e).__name__, str(e)[:200], flush=True)


if __name__ == '__main__':
    main()
